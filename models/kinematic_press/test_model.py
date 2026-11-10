import unittest
from fractions import Fraction as F
from model import box, overlap_time, check, evaluate_phases

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
        c={'id':'x','variant':'A','phase':'A-PRESS','units':{'length':'m','time':'s'},'contact':'touch_is_collision','time':[0,1], 'bodies':[{'min':[0,0,None],'max':[1,1,None],'delta':[0,0,0]},{'min':[0,0,0],'max':[1,1,1],'delta':[0,0,0]}]}
        self.assertEqual(check(c)['collision_status'],'INDETERMINATE')
    def test_ejection_list_is_invalid_without_changing_collision(self):
        c={'id':'x','variant':'A','phase':'A-PRESS','units':{'length':'m','time':'s'},'contact':'touch_is_collision','time':[0,1], 'bodies':[{'min':[0,0,0],'max':[1,1,1],'delta':[0,0,0]},{'min':[3,0,0],'max':[4,1,1],'delta':[0,0,0]}], 'ejection':[]}
        result=check(c)
        self.assertEqual(result['ejection_status'],'INVALID_INPUT')
        self.assertEqual(result['collision_status'],'NO_COLLISION')
        self.assertIn('object',result['ejection_error'])
    def test_phase_coverage_distinguishes_missing_pair(self):
        plan={'phases':{'A-PRESS':{'required_pairs':[['punch','feeder'],['punch','gate']],'note':'x'}}}
        inputs={'units':{'length':'m','time':'s'},'contact':'touch_is_collision','phases':{'A-PRESS':{'time':[0,1], 'bodies':{'punch':{'min':[0,0,0],'max':[1,1,1],'delta':[0,0,0]},'feeder':{'min':[3,0,0],'max':[4,1,1],'delta':[0,0,0]}}}}}
        phase=evaluate_phases(plan,inputs)['A-PRESS']
        self.assertEqual(phase['checked_pairs'][0]['collision_status'],'NO_COLLISION')
        self.assertEqual(phase['unchecked_pairs'][0]['bodies'],['punch','gate'])
        self.assertEqual(phase['unchecked_pairs'][0]['collision_status'],'INDETERMINATE')
if __name__=='__main__': unittest.main()
