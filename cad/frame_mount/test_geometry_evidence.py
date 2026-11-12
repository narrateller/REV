import copy, unittest
from geometry_evidence import strict_interval


class IntervalAuditRegression(unittest.TestCase):
    def body(self,lo,hi,delta=('0','0','0')):
        return {'lo':list(lo),'hi':list(hi),'delta':list(delta),'motion':'linear'}
    def test_midstroke_collision_not_hidden_by_clear_endpoints(self):
        a=self.body(('0','0','0'),('1','1','1'),('4','0','0'));b=self.body(('2','0','0'),('3','1','1'))
        self.assertEqual(strict_interval(a,b)['status'],'POSITIVE_BOUND_OVERLAP')
        self.assertEqual(strict_interval(a,b)['normalized_boundary_values'],['1/4','3/4'])
    def test_positive_face_edge_point_touches_are_zero_volume(self):
        a=self.body(('0','0','0'),('1','1','1'))
        for lo,hi in [(('1','0','0'),('2','1','1')),(('1','1','0'),('2','2','1')),(('1','1','1'),('2','2','2'))]:
            self.assertEqual(strict_interval(a,self.body(lo,hi))['status'],'NO_POSITIVE_VOLUME_ON_INTERVAL')
    def test_arbitrarily_small_positive_overlap_is_not_contact(self):
        a=self.body(('0','0','0'),('1','1','1'));b=self.body(('99999999999999999999/100000000000000000000','0','0'),('2','1','1'))
        self.assertEqual(strict_interval(a,b)['status'],'POSITIVE_BOUND_OVERLAP')
    def test_unsupported_motion_and_unknown_displacement_are_indeterminate(self):
        a=self.body(('0','0','0'),('1','1','1'));b=self.body(('10','0','0'),('11','1','1'))
        for kind in ('rotation','unknown'):
            c=copy.deepcopy(b);c['motion']=kind
            self.assertEqual(strict_interval(a,c)['status'],'INDETERMINATE')
        b['delta']=None;self.assertEqual(strict_interval(a,b)['status'],'INDETERMINATE')
    def test_return_uses_entire_reverse_interval(self):
        a=self.body(('4','0','0'),('5','1','1'),('-4','0','0'));b=self.body(('2','0','0'),('3','1','1'))
        self.assertEqual(strict_interval(a,b)['status'],'POSITIVE_BOUND_OVERLAP')


if __name__=='__main__':unittest.main()
