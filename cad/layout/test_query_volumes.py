import unittest
from layout_common import ROOT,load
from cad_validation import check_cad_adapter
from query_volumes import expected_queries
from query_regressions import run_case


class QueryVolumeChecks(unittest.TestCase):
    def setUp(self):
        self.inputs=ROOT/'cad/layout/conditional_inputs.assumed.json';self.models=ROOT/'cad/build/research_layout'
    def test_all_native_query_geometries_are_reported(self):
        results=check_cad_adapter(load(self.inputs),self.models,self.inputs)
        for v in 'AB':
            self.assertEqual(results[v]['query_geometry_match'],'PASS');self.assertEqual(results[v]['query_count'],2)
            self.assertEqual({q['id'] for q in results[v]['query_volumes']},set(expected_queries(load(self.inputs),v)))
            self.assertTrue(all(q['native_shape_match']=='PASS' and q['dimensions']=='PASS' and q['local_and_global_placement']=='PASS' for q in results[v]['query_volumes']))
    def test_r5_q01_refreshed_hash_fails_api_and_cli(self):
        result=run_case(self.models,self.inputs,'A','CylinderRemoval','size_height',True)
        self.assertTrue(result['matches'],result);self.assertTrue(result['mutation']['hash_updated'])
    def test_doser_removed_and_hidden_in_manifest_fails(self):
        result=run_case(self.models,self.inputs,'B','DoserRemoval','delete_forged_manifest')
        self.assertTrue(result['matches'],result)
    def test_parent_movement_fails(self):
        result=run_case(self.models,self.inputs,'B','CylinderRemoval','group_move')
        self.assertTrue(result['matches'],result)


if __name__=='__main__':unittest.main()
