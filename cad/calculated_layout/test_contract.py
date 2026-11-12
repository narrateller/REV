"""Independent arithmetic/interface limits, not an approval of the press."""
import unittest
from bridge import *
from scenes import make_scenes
class PlanOnly:plan_only=True
class Contract(unittest.TestCase):
    def test_all_44_sources_are_current_and_unchanged(self):
        from pipeline import source_check
        self.assertEqual(source_check()['44_bindings'],'UNCHANGED')
    def test_camera_and_strokes_close_exactly(self):
        for v in VARS:
            _,_,g,_=geometry_values(v)
            self.assertEqual(g['CHAMBER_LENGTH'],F(83,144))
            self.assertEqual(g['APPROACH_STROKE']+g['WORK_STROKE']+F('0.11'),g['CHAMBER_LENGTH'])
            self.assertEqual(g['RETURN_STROKE'],g['APPROACH_STROKE']+g['WORK_STROKE']+g['EJECT_STROKE'])
    def test_diameter_is_not_outer_barrel(self):
        for v in VARS:
            d=load(input_path(v));c=next(c for c in d['components'] if c['id']=='cylinder_barrel')
            self.assertEqual(F(d['parameters'][c['radius']]['value']),F('.22'))
            self.assertNotEqual(F('.44'),source_values(v)[0]['R3_BASE_'+v+'_BORE'])
    def test_real_UNKNOWN_and_B_open_preserved(self):
        for v in VARS:
            d=load(input_path(v));self.assertTrue(all(d['real_REV'][k] is None for k in ('dimensions','strokes','loads','feedstock')))
            for s in make_scenes(d,v,PlanOnly())[:4]:
                self.assertEqual(s['physical_feasibility'],'INDETERMINATE')
                if v=='B':self.assertEqual(s['B_open_permission'],'INDETERMINATE')
    def test_no_premature_remove_on_actual_short_output(self):
        for v in VARS:
            for s in make_scenes(load(input_path(v)),v,PlanOnly())[:4]:
                self.assertEqual(s['lifecycle'],[]);self.assertFalse(s['product_removed']);self.assertEqual(s['READY'],'NOT_CONFIRMED')
                self.assertTrue(all('product_'+v in st['state'] for st in s['stages']))
    def test_nominal_vs_actual_output_is_not_conflated(self):
        for v in VARS:
            s=make_scenes(load(input_path(v)),v,PlanOnly())[0]
            self.assertEqual(s['nominal_axial_geometry'],'GEOMETRY_SUFFICIENT');self.assertEqual(s['actual_output_geometry'],'SHORT_STROKE')
    def test_all_four_cases_have_continuous_complete_timing(self):
        for v in VARS:
            for s in make_scenes(load(input_path(v)),v,PlanOnly())[:4]:
                self.assertEqual(s['continuity_status'],'INDETERMINATE' if s['case']=='unknown' else 'CONTINUOUS')
                for a,b in zip(s['stages'],s['stages'][1:]):self.assertEqual(F(a['time'][1]),F(b['time'][0]))
                self.assertAlmostEqual(float(F(s['fixed_budget_duration'])),float(F(s['registered_fixed_budget_cycle'])),places=11)
    def test_legacy_and_L_paths_both_remain_in_protocol(self):
        for v in VARS:
            names={s['case'] for s in make_scenes(load(input_path(v)),v,PlanOnly())}
            self.assertIn('service_doser_slide',names);self.assertIn('service_fp_doser_retract_lift',names)
if __name__=='__main__':unittest.main()
