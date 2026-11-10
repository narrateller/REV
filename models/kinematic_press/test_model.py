import unittest
from fractions import Fraction as F
from model import box, overlap_time, check

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
if __name__=='__main__': unittest.main()
