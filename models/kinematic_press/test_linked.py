import copy
import json
import unittest
from pathlib import Path
import linked
import model

class LinkedChecks(unittest.TestCase):
    def test_four_outcomes_both_variants(self):
        expected={'sufficient':('SUFFICIENT_STROKE','NO_COLLISION','ALLOWED','READY'), 'short':('INSUFFICIENT_STROKE','NO_COLLISION','BLOCKED','BLOCKED'), 'collision':('SUFFICIENT_STROKE','COLLISION','BLOCKED','BLOCKED'), 'unknown':('INDETERMINATE','INDETERMINATE','INDETERMINATE','INDETERMINATE')}
        for variant in 'AB':
            for mode,want in expected.items():
                with self.subTest(variant=variant,mode=mode):
                    r=linked.run(variant,mode)
                    self.assertEqual((r['ejection_status'],r['collision_status'],r['transition'],r['ready']['status']),want)
                    if mode=='collision': self.assertEqual(r['collision_interval_product_obstacle'],['1/4','7/8'])
                    if mode=='sufficient':
                        self.assertEqual(r['product_final_rear'],'2'); self.assertTrue(all(not x['mismatches'] and not x['unknown'] and x['time_contiguous'] and x['lifecycle_valid'] for x in r['continuity']))
                        self.assertEqual(r['lifecycle']['event'],'REMOVE_AFTER_CONFIRMED_SYNTHETIC_EJECTION')
    def test_ce01_stationary_product_does_not_succeed(self):
        cases=json.loads((Path(__file__).parent/'fixtures.json').read_text())['cases'];c=copy.deepcopy(next(x for x in cases if x['id']=='R5-B-EJECT-SUFFICIENT'))
        for body in c['bodies']: body['delta']=[0,0,0]
        self.assertEqual(model.check(c)['ejection_status'],'INVALID_INPUT')
        p=linked.initial(); phase={'time':[0,1], 'motion_type':'linear','bodies':p}
        self.assertNotEqual(model.verify_a_out(phase,copy.deepcopy(phase)),'CONSISTENT')
    def test_ce02_matrix_finds_punch_channel_wall(self):
        p=Path(__file__).parent; plan=json.loads((p/'phase_plan.json').read_text()); inputs=json.loads((p/'phase_inputs_synthetic.json').read_text())
        bodies=inputs['phases']['B-EJECT']['bodies']; bodies['channel_wall']=copy.deepcopy(bodies['punch']); bodies['channel_wall']['delta']=[0,0,0]
        coverage=model.evaluate_phases(plan,inputs)['B-EJECT']
        pair=next(x for x in coverage['checked_pairs'] if set(x['bodies'])=={'punch','channel_wall'})
        self.assertEqual(pair['collision_status'],'COLLISION'); self.assertEqual(pair['evidence']['contact_interval_normalized'],['0','1'])
        before=inputs['phases']['B-EJECT']; after=inputs['phases']['B-RESET']
        result=model.transition('B-EJECT','B-RESET',before['bodies'],after['bodies'],{'exit_clear':True},coverage,before['time'],after['time'])
        self.assertEqual(result['status'],'BLOCKED');self.assertIn('pair collision or invalid result',result['reasons'])
    def test_missing_contact_and_collision_coexist(self):
        b=linked.initial(); b['product']['delta']=None;b['output_obstacle']=copy.deepcopy(b['punch'])
        r=linked.matrix('B','B-EJECT',b)
        self.assertEqual(r['collision_status'],'COLLISION');self.assertGreater(r['unknown_count'],0);self.assertFalse(r['complete'])
    def test_bad_contact_and_false_ready(self):
        b=linked.initial();b['product']['delta']=[0,0,0];b['punch']['delta']=[1,0,0]
        self.assertEqual(linked.contact(b['punch'],b['product'])['status'],'BLOCKED')
        short=linked.run('B','short');self.assertNotEqual(short['ready']['status'],'READY')
    def test_missing_wall_is_unknown_and_all_pairs_are_generated(self):
        b=linked.initial(); del b['channel_wall']
        r=linked.matrix('A','A-PRESS',b)
        self.assertEqual(len(r['pairs']),len(linked.SCENE)*(len(linked.SCENE)-1)//2)
        self.assertFalse(r['complete'])
        self.assertIn(r['collision_status'],('INDETERMINATE','COLLISION'))
        pair=next(x for x in r['pairs'] if set(x['pair'])=={'punch','channel_wall'})
        self.assertEqual(pair['result']['collision_status'],'INDETERMINATE')
    def test_original_cycle_does_not_fabricate_ready(self):
        p=Path(__file__).parent; plan=json.loads((p/'phase_plan.json').read_text()); inputs=json.loads((p/'phase_inputs_synthetic.json').read_text())
        coverage=model.evaluate_phases(plan,inputs)
        for variant,last in [('A','A-RETURN'),('B','B-RESET')]:
            before=inputs['phases'][last]; ready=inputs['phases'][variant+'-READY']; end=before['time'][1]
            r=model.transition(last,variant+'-READY',before['bodies'],ready['bodies'],{k:True for k in model.GUARDS[variant+'-READY']},coverage[last],before['time'],[end,end+1])
            self.assertEqual(r['status'],'BLOCKED')
    def test_penetrating_stop_lock_is_not_excluded(self):
        b=linked.initial(); b['stop']=linked.make_box(2,3,0,1);b['lock']=linked.make_box('5/2','7/2',0,1)
        result=linked.matrix('B','B-READY',b)
        interface=next(x for x in result['pairs'] if set(x['pair'])=={'stop','lock'})
        self.assertEqual(interface['interface']['status'],'BLOCKED')
        self.assertTrue(result['interface_invalid'])
if __name__=='__main__': unittest.main()
