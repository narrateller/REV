import unittest
from engine import pair, evaluate_phase, combine_link, boundary
from scenes import box,run,decide

class EventTests(unittest.TestCase):
    def setUp(self):
        self.p=box([-1,0,0],[0,1,1],[1,0,0])
        self.rule={'ordered':['punch','product'],'allowed_time':[0,1],'patch_yz':[[0,1],[0,1]],'direction':'either'}
    def test_approach_then_required_contact_at_boundary(self):
        product=box(['1/2',0,0],['3/2',1,1],[0,0,0])
        r=pair(self.p,product,[0,1],self.rule,['1/2','1/2'])
        self.assertIn('CLEAR',[x['collision_status'] for x in r['segments']])
        self.assertEqual(r['link'],'LINK_CONFIRMED')
        self.assertEqual(next(x for x in r['segments'] if x['from']=='1/2' and x['interval']=='point')['collision_status'],'ALLOWED_CONTACT')
        self.assertIn('COLLISION',[x['collision_status'] for x in r['segments']])
    def test_separated_required_contact_is_absent_without_collision(self):
        r=pair(self.p,box([5,0,0],[6,1,1]),[0,1],self.rule,[0,1])
        self.assertEqual(r['link'],'LINK_ABSENT');self.assertTrue(all(x['collision_status']=='CLEAR' for x in r['segments']))
    def test_contact_then_detachment(self):
        a=box([-1,0,0],[0,1,1]);b=box([0,0,0],[1,1,1],[1,0,0])
        r=pair(a,b,[0,1],self.rule,[0,1]);self.assertEqual(r['link'],'LINK_ABSENT')
        self.assertEqual(r['segments'][0]['collision_status'],'ALLOWED_CONTACT');self.assertIn('CLEAR',[x['collision_status'] for x in r['segments']])
    def test_unknown_and_invalid(self):
        missing=box([0,0,0],[1,1,1]);missing['motion']=None
        self.assertEqual(pair(self.p,missing,[0,1],self.rule,[0,1])['link'],'LINK_INDETERMINATE')
        malformed=box([1,0,0],[0,1,1]);self.assertEqual(pair(self.p,malformed,[0,1],self.rule,[0,1])['input_status'],'INVALID_INPUT')
    def test_prohibited_contact_and_unknown_do_not_hide_collision(self):
        scene={'phase':'x','time':[0,1],'registry':['a','b','c'],'bodies':{'a':box([0,0,0],[1,1,1]),'b':box([0,0,0],[1,1,1]),'c':None}}
        r=evaluate_phase(scene);self.assertEqual(len(r['pairs']),3)
        self.assertTrue(any(s['collision_status']=='COLLISION' for p in r['pairs'] for s in p['segments']))
        self.assertTrue(any(s['collision_status']=='INDETERMINATE' for p in r['pairs'] for s in p['segments']))
    def test_penetration_and_contact_time(self):
        a=box([-1,0,0],[0,1,1]);b=box([0,0,0],[1,1,1])
        rule=dict(self.rule,allowed_time=['1/2',1])
        r=pair(a,b,[0,1],rule,['1/2',1]);self.assertEqual(r['segments'][0]['collision_status'],'COLLISION')
        self.assertEqual(r['link'],'LINK_CONFIRMED')
    def test_unsupported_motion(self):
        x=box([0,0,0],[1,1,1]);x['motion']='rotate'
        self.assertEqual(pair(self.p,x,[0,1],self.rule,[0,1])['input_status'],'INDETERMINATE')
    def test_invalid_window(self):
        r=pair(self.p,box([0,0,0],[1,1,1]),[0,1],self.rule,[-1,1]);self.assertEqual(r['input_status'],'INVALID_INPUT')

    def test_piecewise_detachment_and_phase_boundary(self):
        punch=box([-1,0,0],[0,1,1]); product=box([0,0,0],[1,1,1])
        first=dict(self.rule,allowed_time=[0,1]);second=dict(self.rule,allowed_time=[1,2])
        r1=pair(punch,product,[0,1],first,[0,1])
        r2=pair(punch,box([0,0,0],[1,1,1],[1,0,0]),[1,2],second,[1,2])
        self.assertEqual(combine_link([{'time':[0,1],'result':r1},{'time':[1,2],'result':r2}],[0,2]),'LINK_ABSENT')
        self.assertEqual(r1['segments'][-1]['collision_status'],'ALLOWED_CONTACT')
        self.assertEqual(r2['segments'][0]['collision_status'],'ALLOWED_CONTACT')
    def test_link_gap_is_not_confirmed(self):
        punch=box([-1,0,0],[0,1,1]); product=box([0,0,0],[1,1,1])
        r=pair(punch,product,[0,1],self.rule,[0,1])
        self.assertEqual(combine_link([{'time':[0,1],'result':r}],[0,2]),'LINK_INDETERMINATE')
    def test_outside_patch_is_collision(self):
        p=box([-1,0,0],[0,2,1]); b=box([0,0,0],[1,2,1])
        self.assertTrue(all(x['collision_status']=='COLLISION' for x in pair(p,b,[0,1],self.rule,[0,1])['segments']))
    def test_all_eight_scene_outcomes_and_pair_counts(self):
        import json
        from pathlib import Path
        config=json.loads((Path(__file__).parent/'fixtures.json').read_text())
        for v in 'AB':
            for case,expected in config['expected'].items():
                with self.subTest(variant=v,case=case):
                    r=run(v,case,config)
                    self.assertEqual({k:r[k] for k in expected},expected)
                    for phase in r['stages']:
                        out=phase['output'];self.assertEqual(len(out['pairs']),out['expected_pairs'])
                    if case=='sufficient': self.assertTrue(r['events']);self.assertTrue(all(c['lifecycle_valid'] and not c['mismatches'] and not c['unknown'] and c['time_contiguous'] for c in r['continuity']))
                    else: self.assertFalse(r['events'])
    def test_unauthorized_disappearance_and_discontinuity(self):
        a={'phase':'A','time':[0,1],'registry':['residue_1'],'bodies':{'residue_1':box([0,0,0],[1,1,1])}}
        b={'phase':'B','time':[1,2],'registry':[],'bodies':{}}
        self.assertEqual(boundary(a,b,[])['status'],'DISCONTINUITY')
        b={'phase':'B','time':[2,3],'registry':['residue_1'],'bodies':a['bodies']}
        self.assertEqual(boundary(a,b,[])['status'],'DISCONTINUITY')
    def test_unsupported_creation_is_indeterminate(self):
        a={'phase':'A','time':[0,1],'registry':[],'bodies':{}}
        b={'phase':'B','time':[1,2],'registry':['fragment_1'],'bodies':{'fragment_1':box([0,0,0],[1,1,1])}}
        self.assertEqual(boundary(a,b,[{'type':'CREATE','id':'fragment_1','time':1}])['status'],'INDETERMINATE')
    def test_declared_channel_wall_b_eject_automatically_found(self):
        scene={'phase':'B-EJECT','time':[0,1],'registry':['punch','channel_wall'],'bodies':{'punch':box([0,0,0],[1,1,1],[1,0,0]),'channel_wall':box([0,0,0],[1,1,1])}}
        r=evaluate_phase(scene);self.assertEqual(r['expected_pairs'],1)
        self.assertEqual({r['pairs'][0]['body_a'],r['pairs'][0]['body_b']},{'punch','channel_wall'})
        self.assertTrue(any(x['collision_status']=='COLLISION' for x in r['pairs'][0]['segments']))
    def test_required_window_missing_is_unknown_without_erasing_contact(self):
        r=pair(box([-1,0,0],[0,1,1]),box([0,0,0],[1,1,1]),[0,1],self.rule,None,True)
        self.assertEqual(r['link'],'LINK_INDETERMINATE')
        self.assertTrue(all(x['collision_status']=='ALLOWED_CONTACT' for x in r['segments']))
    def test_forbidden_relative_separation_at_contact(self):
        rule=dict(self.rule,direction='nonseparating')
        r=pair(box([-1,0,0],[0,1,1]),box([0,0,0],[1,1,1],[1,0,0]),[0,1],rule,[0,1])
        self.assertEqual(r['segments'][0]['collision_status'],'COLLISION')
    def test_invalid_time_is_reported_not_raised(self):
        x=box([0,0,0],[1,1,1])
        for interval in ([1,0], [0], [None,1]):
            with self.subTest(interval=interval):
                self.assertEqual(pair(x,x,interval)['input_status'],'INVALID_INPUT')
    def test_absent_link_blocks_without_inventing_collision(self):
        self.assertEqual(decide('NO_COLLISION','LINK_ABSENT','GEOMETRY_SUFFICIENT'),'BLOCKED')
        self.assertEqual(decide('COLLISION','LINK_INDETERMINATE','INDETERMINATE'),'BLOCKED')
        self.assertEqual(decide('INDETERMINATE','LINK_INDETERMINATE','INDETERMINATE'),'INDETERMINATE')
    def test_reversed_contact_window_is_invalid(self):
        r=pair(box([-1,0,0],[0,1,1]),box([0,0,0],[1,1,1]),[0,1],dict(self.rule,allowed_time=[1,0]),[0,1])
        self.assertEqual(r['input_status'],'INVALID_INPUT')
    def test_approach_then_sustained_link_across_boundary(self):
        first_rule=dict(self.rule,allowed_time=[0,2])
        first=pair(box([-1,0,0],[0,1,1],['1/2',0,0]),box(['1/2',0,0],['3/2',1,1]),[0,1],first_rule)
        second=pair(box(['-1/2',0,0],['1/2',1,1],[1,0,0]),box(['1/2',0,0],['3/2',1,1],[1,0,0]),[1,2],first_rule,[1,2])
        self.assertEqual(first['segments'][0]['collision_status'],'CLEAR')
        self.assertEqual(first['segments'][-1]['collision_status'],'ALLOWED_CONTACT')
        self.assertEqual(combine_link([{'time':[0,1],'result':first},{'time':[1,2],'result':second}],[1,2]),'LINK_CONFIRMED')
    def test_invalid_piece_cannot_confirm_link(self):
        invalid={'input_status':'INVALID_INPUT','segments':[]}
        self.assertEqual(combine_link([{'time':[0,1],'result':invalid}],[0,1]),'LINK_INDETERMINATE')
    def test_invalid_boundary_geometry_is_invalid_input(self):
        a={'phase':'A','time':[0,1],'registry':['punch'],'bodies':{'punch':box([0,0,0],[1,1,1])}}
        b={'phase':'B','time':[1,2],'registry':['punch'],'bodies':{'punch':box([1,0,0],[0,1,1])}}
        self.assertEqual(boundary(a,b,[])['status'],'INVALID_INPUT')
if __name__=='__main__': unittest.main()
