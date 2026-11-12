import unittest
from service_fixtures import *


class CompleteServiceSemantics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load(INPUT);cls.scenes=read_packed(OUT/'service_scenes.json.gz');cls.evaluator=Evaluator(cls.data)
        cls.cases=counterexamples(cls.data,cls.scenes,cls.evaluator)
    def test_five_independent_counterexamples_and_compounds(self):
        for name,s,want in self.cases:
            with self.subTest(case=name):
                r=evaluate_scene(s,self.data,self.evaluator)
                self.assertEqual(r['geometric_path_outcome'],want)
                self.assertFalse(r['limited_geometry_success']);self.assertFalse(r['matches_test_expectation'])
                self.assertEqual(r['overall_service_outcome'],want)
                if want=='BLOCKED':self.assertTrue(r['proven_collisions'])
                else:self.assertTrue(r['unknown_mandatory_conditions'])
    def test_l_path_preserved_and_physical_feasibility_unknown(self):
        for v in 'AB':
            s=next(s for s in self.scenes if s['variant']==v and s['case']=='service_fp_doser_retract_lift');r=evaluate_scene(s,self.data,self.evaluator)
            self.assertTrue(r['limited_geometry_success']);self.assertTrue(r['matches_test_expectation'])
            self.assertEqual(r['geometric_path_outcome'],'CONFIRMED_NO_POSITIVE_VOLUME')
            self.assertEqual(r['overall_service_outcome'],'INDETERMINATE');self.assertEqual(r['physical_feasibility'],'INDETERMINATE')
    def test_expected_negative_is_not_successful_path(self):
        for v in 'AB':
            s=next(s for s in self.scenes if s['variant']==v and s['case']=='service_doser_slide');r=evaluate_scene(s,self.data,self.evaluator)
            self.assertTrue(r['matches_test_expectation']);self.assertFalse(r['limited_geometry_success'])
            self.assertEqual(r['overall_service_outcome'],'BLOCKED');self.assertEqual({tuple(x['pair']) for x in r['proven_collisions']},LEGACY)
    def test_missing_mandatory_phase_cannot_succeed(self):
        s=copy.deepcopy(next(s for s in self.scenes if s['case']=='service_fp_motor'));s['stages']=s['stages'][:-1];r=evaluate_scene(s,self.data,self.evaluator)
        self.assertFalse(r['limited_geometry_success']);self.assertFalse(r['matches_test_expectation']);self.assertTrue(r['unknown_mandatory_conditions'])
    def test_confirmed_collision_dominates_unknown(self):
        for name,s,want in self.cases:
            if name.startswith('compound_') and want=='BLOCKED':
                r=evaluate_scene(s,self.data,self.evaluator);self.assertTrue(r['proven_collisions']);self.assertTrue(r['unknown_mandatory_conditions']);self.assertEqual(r['overall_service_outcome'],'BLOCKED')


if __name__=='__main__':unittest.main()
