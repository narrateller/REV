"""Arithmetic regression checks; these do not validate material or equipment."""
import copy
import json
import math
from pathlib import Path
import sys
import unittest
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from rev_parametric import solve,unit
from repo_support import flatten


class ParametricSizingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry=flatten(yaml.safe_load((ROOT/'params/registry.yaml').read_text()))
        case=json.loads((ROOT/'verification/r3_parametric_sizing/cases.json').read_text())[0]
        cls.base={name:registry[k]['value'] for name,k in case['parameters'].items()}

    def calc(self,variant='A',**overrides):
        p=dict(self.base);p.update(overrides);return solve(p,variant)

    def test_mass_and_chamber_geometry_independent_balance(self):
        o,_=self.calc()
        self.assertAlmostEqual(o['area'],.009)
        self.assertAlmostEqual(o['chamber_volume'],.83/160)
        self.assertAlmostEqual(o['chamber_length'],.83/(160*.009))
        self.assertAlmostEqual(o['approach_stroke']+o['work_stroke'],o['chamber_length']-.11)
        self.assertAlmostEqual(o['mass_residual'],0.)

    def test_both_chambers_and_seal_in_force_balance(self):
        o,_=self.calc();ab=o['bore_area'];aa=o['annulus_area'];p=self.base
        self.assertAlmostEqual(o['force_extension_capacity'],p['supply_work']*ab-p['back_forward']*aa-p['seal'])
        self.assertGreaterEqual(o['force_extension_capacity']+1e-7,o['force_work_peak'])
        self.assertGreaterEqual(o['force_return_capacity']+1e-7,o['force_return_required'])
        self.assertAlmostEqual(o['rod']/o['bore'],.6)
        self.assertAlmostEqual(o['force_work_peak'],166713050*.009+32000)

    def test_reverse_requirement_can_govern_bore(self):
        o,_=self.calc(return_load=3e6)
        self.assertAlmostEqual(o['force_return_capacity'],3e6+self.base['guide'],places=6)
        self.assertGreater(o['force_extension_capacity'],o['force_work_peak'])

    def test_increasing_opposing_pressure_never_increases_capacity_for_fixed_bore(self):
        low,_=self.calc();high,_=self.calc(back_forward=5e6)
        self.assertGreater(high['bore'],low['bore'])

    def test_power_and_energy_exact_balance_each_phase(self):
        o,_=self.calc()
        for name,t in [('approach',1),('work',2),('eject',1),('return',2)]:
            self.assertAlmostEqual(o[name+'_supply_energy'],o[name+'_supply_power']*t)
            self.assertAlmostEqual(o[name+'_supply_energy'],sum(o[name+'_'+s] for s in ('load_work','seal_loss','back_loss','valve_loss')),places=7)
        self.assertAlmostEqual(o['hydraulic_energy_residual'],0.,places=7)
        self.assertAlmostEqual(o['electric_energy_residual'],0.,places=7)
        self.assertGreater(o['electric_energy'],o['hydraulic_energy'])

    def test_work_integrates_linear_stress_instead_of_peak_times_stroke(self):
        o,_=self.calc()
        expected=(166713050*.009/2+32000)*o['work_stroke']
        self.assertAlmostEqual(o['work_load_work'],expected)
        self.assertLess(o['work_load_work'],o['force_work_peak']*o['work_stroke'])

    def test_halving_motion_times_doubles_power_not_energy(self):
        a,_=self.calc();b,_=self.calc(t_approach=.5,t_work=1.,t_eject=.5,t_return=1.)
        self.assertAlmostEqual(b['hydraulic_power_peak'],2*a['hydraulic_power_peak'])
        self.assertAlmostEqual(b['electric_energy'],a['electric_energy'])
        self.assertAlmostEqual(b['flow_peak'],2*a['flow_peak'])

    def test_density_changes_volume_and_stroke_not_load_sizing(self):
        a,_=self.calc();b,_=self.calc(rho=100.)
        self.assertAlmostEqual(b['chamber_volume'],2*a['chamber_volume'])
        self.assertAlmostEqual(b['bore'],a['bore'])
        self.assertGreater(b['work_stroke'],a['work_stroke'])

    def test_zero_return_pressure_limit_matches_textbook_area(self):
        o,_=self.calc(variant='B',back_forward=0.,back_return=0.,guide=0.,seal=0.,eject_load_b=0.,return_load=0.)
        self.assertAlmostEqual(o['bore'],math.sqrt(4*166713050*.009/(math.pi*30e6)))

    def test_B_unknown_unloading_never_returns_permission(self):
        o,flags=self.calc(variant='B')
        self.assertIsNone(flags['B_residual_stop_force']);self.assertIsNone(flags['B_allowed_open_reaction'])
        self.assertEqual(flags['B_open_permission'],'INDETERMINATE')
        self.assertEqual(flags['whole_cycle_feasibility'],'INDETERMINATE')
        self.assertGreater(o['B_stop_peak_reaction'],0.)

    def test_A_hold_failure_and_short_ejection_stay_visible(self):
        o,flags=self.calc(channel_hold=1.,eject_travel=.01)
        self.assertEqual(flags['A_hold_arithmetic'],'INSUFFICIENT')
        self.assertEqual(flags['ejection_geometry_arithmetic'],'SHORT_TRAVEL')
        self.assertLess(o['eject_geometry_margin'],0.)

    def test_leakage_hold_is_energy_not_mechanical_motion(self):
        a,_=self.calc();b,_=self.calc(leak_hold=1e-5)
        self.assertAlmostEqual(b['hydraulic_energy']-a['hydraulic_energy'],300.)
        self.assertAlmostEqual(b['load_work_total'],a['load_work_total'])
        self.assertAlmostEqual(b['hydraulic_energy_residual'],0.,places=7)

    def test_prescribed_time_violates_assumed_power_and_time_bound(self):
        o,flags=self.calc()
        self.assertEqual(flags['power_budget_arithmetic'],'EXCEEDS_ASSUMED_LIMIT')
        self.assertGreater(o['cycle_budget_power_limited'],o['cycle_budget'])

    def test_invalid_domains_fail_instead_of_clamping_or_nan(self):
        bad=[dict(rho=0),dict(phi=1.1),dict(kappa=1),dict(kappa=True),dict(t_work=0),dict(eta_pump=1.1),
             dict(sigma_start=1e9),dict(back_forward=1e9),dict(back_return=1e9),dict(mass=None),
             dict(mass=float('nan')),dict(rho=1e9),dict(guide=-1.)]
        for overrides in bad:
            with self.subTest(overrides=overrides),self.assertRaises(ValueError):self.calc(**overrides)

    def test_output_units(self):
        for name,u in {'A_hold_margin':'N','B_stop_peak_reaction':'N','electric_power_margin':'W',
                       'cycle_budget_power_limited':'s','work_minimum_time_power':'s','work_mean_chamber_pressure':'Pa',
                       'return_flow_return':'m^3/s','mass_residual':'kg','work_load_work':'J'}.items():
            self.assertEqual(unit(name),u)
