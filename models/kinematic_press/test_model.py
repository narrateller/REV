import unittest
import json
from pathlib import Path
from fractions import Fraction as F
from model import box, overlap_time, check, evaluate_phases, transition, verify_a_out, motion_restrictions, GUARDS

def body(lo, hi, delta):
    return box({'min':lo,'max':hi,'delta':delta})

class ContinuousChecks(unittest.TestCase):
    def test_equal_velocity_separated(self):
        a=body([0,0,0],[1,1,1],[2,0,0]); b=body([2,0,0],[3,1,1],[2,0,0])
        self.assertIsNone(overlap_time(a,b))
    def test_endpoint_touch_is_collision(self):
        a=body([0,0,0],[1,1,1],[1,0,0]); b=body([2,0,0],[3,1,1],[0,0,0])
        self.assertEqual(overlap_time(a,b), (F(1),F(1)))
    def test_intermediate_collision_exact_interval(self):
        a=body([0,0,0],[1,1,1],[4,0,0]); b=body([2,0,0],[3,1,1],[0,0,0])
        self.assertEqual(overlap_time(a,b), (F(1,4),F(3,4)))
    def test_unknown_z_not_zero(self):
        c={'id':'x','variant':'A','phase':'A-PRESS','motion_type':'linear','units':{'length':'m','time':'s'},'contact':'touch_is_collision','time':[0,1], 'bodies':[{'min':[0,0,None],'max':[1,1,None],'delta':[0,0,0]},{'min':[0,0,0],'max':[1,1,1],'delta':[0,0,0]}]}
        self.assertEqual(check(c)['collision_status'],'INDETERMINATE')
    def test_ejection_list_is_invalid_without_changing_collision(self):
        c={'id':'x','variant':'A','phase':'A-PRESS','motion_type':'linear','units':{'length':'m','time':'s'},'contact':'touch_is_collision','time':[0,1], 'bodies':[{'min':[0,0,0],'max':[1,1,1],'delta':[0,0,0]},{'min':[3,0,0],'max':[4,1,1],'delta':[0,0,0]}], 'ejection':[]}
        result=check(c)
        self.assertEqual(result['ejection_status'],'INVALID_INPUT')
        self.assertEqual(result['collision_status'],'NO_COLLISION')
        self.assertIn('object',result['ejection_error'])
    def test_phase_coverage_distinguishes_missing_pair(self):
        plan={'phases':{'A-PRESS':{'required_pairs':[['punch','feeder'],['punch','gate']],'note':'x'}}}
        inputs={'units':{'length':'m','time':'s'},'contact':'touch_is_collision','phases':{'A-PRESS':{'time':[0,1], 'motion_type':'linear', 'bodies':{'punch':{'min':[0,0,0],'max':[1,1,1],'delta':[0,0,0]},'feeder':{'min':[3,0,0],'max':[4,1,1],'delta':[0,0,0]}}}}}
        phase=evaluate_phases(plan,inputs)['A-PRESS']
        self.assertEqual(phase['checked_pairs'][0]['collision_status'],'NO_COLLISION')
        self.assertEqual(phase['unchecked_pairs'][0]['bodies'],['punch','gate'])
        self.assertEqual(phase['unchecked_pairs'][0]['collision_status'],'INDETERMINATE')
    def test_transition_guards_order_continuity_and_unknown(self):
        inputs=json.loads((Path(__file__).parent/'phase_inputs_synthetic.json').read_text())
        plan=json.loads((Path(__file__).parent/'phase_plan.json').read_text())
        coverage=evaluate_phases(plan,inputs)
        a=inputs['phases']['B-UNLOAD']; b=inputs['phases']['B-OPEN']
        args=(a['bodies'],b['bodies'])
        def t(prev,nxt,guards,after=None,cov=None):
            return transition(prev,nxt,args[0],after or args[1],guards,cov or coverage['B-UNLOAD'],a['time'],b['time'])['status']
        self.assertEqual(t('B-UNLOAD','B-OPEN',{'unloading_confirmed':True}),'ALLOWED')
        self.assertEqual(t('B-UNLOAD','B-OPEN',{}),'INDETERMINATE')
        self.assertEqual(t('B-UNLOAD','B-OPEN',{'unloading_confirmed':False}),'BLOCKED')
        self.assertEqual(t('B-PRESS','B-OPEN',{'unloading_confirmed':True}),'BLOCKED')
        changed=json.loads(json.dumps(args[1])); changed['punch']['min'][0]+=1; changed['punch']['max'][0]+=1
        self.assertEqual(t('B-UNLOAD','B-OPEN',{'unloading_confirmed':True},changed),'BLOCKED')
        incomplete={'checked_pairs':[],'unchecked_pairs':[{}]}
        self.assertEqual(t('B-UNLOAD','B-OPEN',{'unloading_confirmed':True},cov=incomplete),'INDETERMINATE')
    def test_a_out_overlay_and_unsupported_motion(self):
        inputs=json.loads((Path(__file__).parent/'phase_inputs_synthetic.json').read_text())
        plan=json.loads((Path(__file__).parent/'phase_plan.json').read_text())
        press=inputs['phases']['A-PRESS']; out=inputs['phases']['A-OUT']
        self.assertEqual(verify_a_out(press,out),'CONSISTENT')
        out['time']=[20,21]
        self.assertEqual(verify_a_out(press,out),'BLOCKED')
        inputs['phases']['B-OPEN']['motion_type']='rotating'
        self.assertFalse(evaluate_phases(plan,inputs)['B-OPEN']['checked_pairs'])
    def test_forbidden_simultaneous_reset_and_feeder_during_press(self):
        inputs=json.loads((Path(__file__).parent/'phase_inputs_synthetic.json').read_text())
        reset=inputs['phases']['B-RESET']; reset['bodies']['stop']['delta']=[1,0,0]
        self.assertEqual(motion_restrictions('B-RESET',reset)['status'],'BLOCKED')
        press=inputs['phases']['B-PRESS']; press['bodies']['feeder']['delta']=[1,0,0]
        self.assertEqual(motion_restrictions('B-PRESS',press)['status'],'BLOCKED')
if __name__=='__main__': unittest.main()
