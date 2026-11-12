"""Conditional-budget/API regression tests; synthetic values are not equipment data."""
import json,sys,math
from pathlib import Path
import unittest
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from repo_support import flatten
from rev_power_reconcile import reconcile,assess_hold,PHASES
from rev_parametric import solve


class PowerReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=flatten(yaml.safe_load((ROOT/'params/registry.yaml').read_text()))
        cls.cases=json.loads((ROOT/'verification/r3_parametric_sizing/cases.json').read_text())
        cls.alloc={k:cls.registry[v]['value'] for k,v in json.loads((ROOT/'verification/r3_power_reconcile/allocation.json').read_text()).items()}
        cls.base={n:cls.registry[k]['value'] for n,k in cls.cases[0]['parameters'].items()}

    def test_all_eight_originals_stay_incompatible_and_targets_preserved(self):
        for c in self.cases:
            p={n:self.registry[k]['value'] for n,k in c['parameters'].items()};before=dict(p)
            out,flags=reconcile(p,c['variant'],self.alloc);old,_=solve(p,c['variant'])
            self.assertEqual(p,before);self.assertEqual(out['fixed_times_cycle'],old['cycle_budget'])
            self.assertEqual(flags['original_scenario'],'INCOMPATIBLE_WITH_ORIGINAL_BUDGET')
            self.assertGreater(out['fixed_times_required_peak_bound'],p['electric_limit'])
            self.assertGreater(out['fixed_budget_cycle'],old['cycle_budget'])
            self.assertLess(out['fixed_budget_mass_rate'],out['fixed_times_mass_rate'])
            self.assertEqual(flags['actual_whole_machine_feasibility'],'INDETERMINATE')
            if c['variant']=='B':self.assertEqual(flags['B_open_permission'],'INDETERMINATE')

    def test_fixed_budget_phase_limits_and_integrals(self):
        p=self.base;o,_=reconcile(p,'A',self.alloc);old,_=solve(p,'A');eta=p['eta_pump']*p['eta_motor']
        for name in PHASES:
            with self.subTest(phase=name):
                supply=p['supply_return'] if name=='return' else p['supply_eject'] if name=='eject' else p['supply_work']
                expected=(p['electric_limit']-self.alloc['motion_extra_cap'])*eta/supply
                self.assertAlmostEqual(o[name+'_qin_limit'],expected)
                self.assertLessEqual(o[name+'_qin'],expected)
                self.assertLessEqual(o[name+'_power_total_bound'],p['electric_limit']+1e-8)
                self.assertAlmostEqual(o[name+'_qin']*o[name+'_time'],old[name+'_flow_supply']*p['t_'+name])
                self.assertAlmostEqual(o[name+'_qout']*o[name+'_time'],old[name+'_flow_return']*p['t_'+name])
                self.assertGreaterEqual(o[name+'_time'],p['t_'+name])
        self.assertAlmostEqual(o['return_qout']/o['return_qin'],1/(1-p['kappa']**2))

    def test_unknown_hold_and_other_power_never_become_zero_actual_totals(self):
        o,f=reconcile(self.base,'A',self.alloc)
        for key in ('actual_hold_power','actual_motion_extra_power','actual_pause_power','actual_fixed_budget_energy','actual_fixed_budget_average','actual_fixed_times_energy','actual_fixed_times_average'):
            self.assertIsNone(f[key])
        self.assertEqual(f['hold_adequacy'],'INDETERMINATE')
        self.assertEqual(f['fixed_budget_status'],'CONDITIONAL_ON_UNVERIFIED_POWER_ENVELOPES')
        self.assertGreater(o['fixed_budget_energy_bound'],o['known_motion_energy'])

    def test_explicitly_known_components_close_energy_and_average(self):
        o,f=reconcile(self.base,'A',self.alloc,hold_power=4000,motion_extra=2000,pause_power=1000)
        motion_t=sum(o[n+'_time'] for n in PHASES)
        expected=o['known_motion_energy']+2000*motion_t+4000*self.base['t_hold']+1000*self.base['t_aux_a']
        self.assertAlmostEqual(f['actual_fixed_budget_energy'],expected)
        self.assertAlmostEqual(f['actual_fixed_budget_average'],expected/o['fixed_budget_cycle'])
        self.assertLessEqual(expected,o['fixed_budget_energy_bound'])

    def test_R5_W01_hold_deficit_not_repaired_by_long_motion_times(self):
        p=dict(self.base);p.update({k:1000. for k in ('t_approach','t_work','t_eject','t_return')})
        hold=assess_hold(p['supply_work'],p['eta_pump'],p['eta_motor'],mode='pressure_regulated',leakage=.001,pump_flow=.001,standby=0.,aux=0.,budget=p['electric_limit'])
        self.assertAlmostEqual(hold['electric_power'],30000/.765)
        self.assertEqual(hold['budget_status'],'EXCEEDS_BUDGET')
        o,f=reconcile(p,'A',self.alloc,hold_power=hold['electric_power'])
        self.assertEqual(f['fixed_budget_status'],'BLOCKED');self.assertIsNone(o['fixed_budget_cycle'])
        self.assertIsNone(o['fixed_budget_mass_rate']);self.assertIsNone(o['fixed_budget_energy_bound'])
        self.assertIn('HOLD_POWER_EXCEEDS_BUDGET',f['blockers'])
        self.assertEqual(f['hold_adequacy'],'INSUFFICIENT_POWER')

    def test_zero_leakage_does_not_make_running_pump_power_zero(self):
        h=assess_hold(30e6,.85,.9,mode='pressure_regulated',leakage=0.,pump_flow=.001,standby=500.,aux=1000.,budget=30000.)
        self.assertGreater(h['electric_power'],40000.)
        self.assertEqual(h['budget_status'],'EXCEEDS_BUDGET')

    def test_missing_mode_or_standby_is_unknown_not_zero(self):
        for overrides in [dict(),dict(mode='pressure_regulated',leakage=0.,pump_flow=0.,aux=0.)]:
            h=assess_hold(30e6,.85,.9,**overrides)
            self.assertIsNone(h['electric_power']);self.assertEqual(h['budget_status'],'INDETERMINATE')

    def test_isolation_and_unloading_need_pressure_maintenance(self):
        h=assess_hold(30e6,.85,.9,mode='isolated_unloaded',leakage=.001,pump_flow=.001,unload_pressure=1e6,standby=500.,aux=1000.)
        self.assertIsNone(h['electric_power']);self.assertEqual(h['status'],'PRESSURE_MAINTENANCE_NOT_ESTABLISHED')
        h=assess_hold(30e6,.85,.9,mode='isolated_unloaded',leakage=0.,pump_flow=.001,unload_pressure=1e6,standby=500.,aux=1000.)
        self.assertAlmostEqual(h['electric_power'],1e3/.765+1500.)

    def test_no_motion_allocation_never_produces_finite_schedule(self):
        a=dict(self.alloc,motion_extra_cap=self.base['electric_limit'])
        o,f=reconcile(self.base,'A',a)
        self.assertEqual(f['fixed_budget_status'],'BLOCKED');self.assertIsNone(o['fixed_budget_cycle'])
        self.assertIsNone(o['work_time']);self.assertIsNone(o['work_qin'])

    def test_hold_envelope_itself_can_violate_budget(self):
        o,f=reconcile(self.base,'B',dict(self.alloc,hold_total_cap=40000.))
        self.assertEqual(f['fixed_budget_status'],'BLOCKED');self.assertIsNone(o['fixed_budget_cycle'])
        self.assertIn('HOLD_ENVELOPE_EXCEEDS_BUDGET',f['blockers'])
        self.assertEqual(f['B_open_permission'],'INDETERMINATE')

    def test_broken_envelope_is_not_reported_as_a_valid_supply_bound(self):
        o,f=reconcile(self.base,'A',self.alloc,hold_power=6000.)
        self.assertEqual(f['fixed_times_status'],'BLOCKED_ENVELOPE_MISMATCH')
        self.assertIsNone(o['fixed_times_required_peak_bound']);self.assertIsNone(o['fixed_times_energy_bound'])

    def test_actual_total_peak_is_not_product_of_unrelated_phase_maxima(self):
        o,_=reconcile(self.base,'A',self.alloc)
        expected=max(o[n+'_fixed_times_power_bound'] for n in PHASES)
        self.assertEqual(o['fixed_times_required_peak_bound'],expected)
        old,_=solve(self.base,'A')
        wrong=self.base['supply_work']*old['flow_peak']/(.85*.9)+self.alloc['motion_extra_cap']
        self.assertNotAlmostEqual(expected,wrong)

    def test_invalid_power_inputs_rejected(self):
        for x in [-1.,float('nan'),True]:
            with self.subTest(x=x),self.assertRaises(ValueError):reconcile(self.base,'A',dict(self.alloc,hold_total_cap=x))
        with self.assertRaises(ValueError):assess_hold(30e6,1.2,.9)
