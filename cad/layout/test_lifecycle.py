"""R5 counterexamples with corrected expectations, not the old probe assertions."""
import copy,unittest
from layout_lifecycle import apply_boundary_events
from check_layout import assess_continuity,continuity_status


def box(x=0):return {'lo':[str(x),'0','0'],'hi':[str(x+1),'1','1'],'delta':['0','0','0'],'motion':'linear','exact_box':True}


def removal():return {'type':'REMOVE','id':'product_B','time':'1','final_rear':'2','exit_boundary':'2'}


def context():return {'product_B':{'exit_boundary':'2','receiving_yz':[['0','1'],['0','1']],'required_link':'LINK_CONFIRMED','path_collision':'NO_COLLISION'}}


def cases():
    p='product_B';valid={p:box(2)};inside={p:box(0)};r=removal();early={**r,'final_rear':'0'}
    create={'type':'CREATE','id':'ghost','time':'1'};split={'type':'SPLIT','id':p,'children':['piece1','piece2'],'time':'1'}
    rows=[
      ('R5_PREMATURE_REMOVE',inside,{},[early],None,'BLOCKED',[p]),
      ('R5_IGNORED_GHOST_CREATE',inside,inside,[create],None,'INVALID_INPUT',[p]),
      ('R5_CONSISTENT_UNSUPPORTED_CREATE',{}, {'ghost':box()},[create],None,'INDETERMINATE',[]),
      ('SPLIT_UNSUPPORTED',inside,{'piece1':box(),'piece2':box(1)},[split],None,'INDETERMINATE',[p]),
      ('SPLIT_INCONSISTENT',inside,inside,[split],None,'INVALID_INPUT',[p]),
      ('VALID_REMOVE',valid,{},[r],context(),'VALID',[]),
      ('REMOVE_NO_TRUSTED_CONTEXT',valid,{},[r],None,'INDETERMINATE',[p]),
      ('REMOVE_BAD_TIME',valid,{},[{**r,'time':'1/2'}],context(),'INVALID_INPUT',[p]),
      ('REMOVE_EQUIVALENT_TIME',valid,{},[{**r,'time':'2/2'}],context(),'VALID',[]),
      ('DUPLICATE_REMOVE',valid,{},[r,r],context(),'INVALID_INPUT',[p]),
      ('DUPLICATE_CREATE',{}, {'ghost':box()},[create,create],None,'INVALID_INPUT',[]),
      ('EXTRANEOUS_REMOVE',valid,valid,[{**r,'id':'ghost'}],context(),'INVALID_INPUT',[p]),
      ('UNSUPPORTED_EVENT_TYPE',valid,valid,[{**r,'type':'HIDE'}],context(),'INDETERMINATE',[p]),
      ('UNSUPPORTED_UNKNOWN_ID',valid,valid,[{**r,'type':'HIDE','id':'ghost'}],context(),'INVALID_INPUT',[p]),
      ('MISSING_EVENT_TYPE',valid,valid,[{'id':p,'time':'1'}],None,'INVALID_INPUT',[p]),
      ('FORGED_REAR',inside,{},[r],context(),'INVALID_INPUT',[p]),
      ('FORGED_EXIT',inside,{},[{**early,'exit_boundary':'0'}],context(),'INVALID_INPUT',[p]),
      ('UNEXPLAINED_DISAPPEARANCE',inside,{},[],None,'BLOCKED',[p]),
      ('UNEXPLAINED_CREATION',{}, {'ghost':box()},[],None,'BLOCKED',[]),
      ('PREMATURE_AND_UNKNOWN_CREATE',inside,{'ghost':box()},[early,create],context(),'BLOCKED',[p]),
      ('PROVEN_REMOVE_AND_UNKNOWN_CREATE',valid,{'ghost':box()},[r,create],context(),'INDETERMINATE',[]),
    ]
    for value in (1.0,True,'NaN','1/0',None):rows.append(('INVALID_TIME_'+repr(value),valid,{},[{**r,'time':value}],context(),'INVALID_INPUT',[p]))
    for key,value,want in [('required_link','LINK_ABSENT','BLOCKED'),('required_link','LINK_INDETERMINATE','INDETERMINATE'),('path_collision','COLLISION','BLOCKED'),('path_collision','INDETERMINATE','INDETERMINATE')]:
        c=context();c[p][key]=value;rows.append((key+'_'+value,valid,{},[r],c,want,[p]))
    c=context();c[p]['receiving_yz'][0]=['1/2','1'];rows.append(('OUTSIDE_RECEIPT',valid,{},[r],c,'BLOCKED',[p]))
    unknown={p:box(2)};unknown[p]['delta']=None
    rows.append(('MALFORMED_METADATA_WITH_UNKNOWN_MOTION',unknown,{},[{**r,'final_rear':True}],context(),'INVALID_INPUT',[p]))
    rows.append(('UNKNOWN_MOTION',unknown,{},[r],context(),'INDETERMINATE',[p]))
    return rows


def observations():
    result=[]
    for name,before,after,events,conditions,want,registry in cases():
        effective,audit=apply_boundary_events(before,after,'1',events,conditions)
        result.append({'id':name,'expected_status':want,'observed_status':audit['status'],'expected_effective_registry':registry,'effective_registry':sorted(effective),'matches':audit['status']==want and sorted(effective)==registry,'audit':audit})
    return result


class LifecycleRegressions(unittest.TestCase):
    def test_r5_and_negative_events(self):
        for row in observations():
            with self.subTest(case=row['id']):self.assertTrue(row['matches'],row)
    def test_every_event_accounted_and_proof_preserved(self):
        rows={r['id']:r for r in observations()}
        r=rows['PREMATURE_AND_UNKNOWN_CREATE']['audit'];self.assertEqual(len(r['events']),2)
        self.assertEqual([e['status'] for e in r['events']],['BLOCKED','INDETERMINATE'])
        r=rows['PROVEN_REMOVE_AND_UNKNOWN_CREATE']['audit'];self.assertEqual([e['status'] for e in r['events']],['VALIDATED_REMOVE','INDETERMINATE'])
    def test_events_at_no_boundary_are_not_ignored(self):
        stages=[{'phase':'EJECT','time':['0','1'],'state':{'product_B':box()}},{'phase':'RESET','time':['1','2'],'state':{}}]
        for time in ('0','1/2','2','100',False,'broken'):
            with self.subTest(time=time):
                result=assess_continuity(stages,[{**removal(),'time':time}],context())
                self.assertEqual(continuity_status(result),'BLOCKED');self.assertTrue(any(c.get('event_index')==0 for c in result))
    def test_premature_removal_blocks_continuity_and_retains_product(self):
        stages=[{'phase':'EJECT','time':['0','1'],'state':{'product_B':box()}},{'phase':'RESET','time':['1','2'],'state':{}}]
        checks=assess_continuity(stages,[{**removal(),'final_rear':'0'}],context())
        self.assertEqual(continuity_status(checks),'BLOCKED');self.assertEqual(checks[0]['lifecycle_audit']['retained_ids'],['product_B'])
    def test_unsupported_consistent_transition_is_unknown(self):
        stages=[{'phase':'before','time':['0','1'],'state':{}},{'phase':'after','time':['1','2'],'state':{'fragment':box()}}]
        c=assess_continuity(stages,[{'type':'CREATE','id':'fragment','time':'1'}])
        self.assertEqual(continuity_status(c),'INDETERMINATE');self.assertEqual(c[0]['lifecycle_audit']['events'][0]['status'],'INDETERMINATE')
    def test_discontinuity_survives_unsupported_event(self):
        stages=[{'phase':'before','time':['0','1'],'state':{'product_B':box()}},{'phase':'after','time':['1','2'],'state':{'product_B':box(1),'ghost':box()}}]
        c=assess_continuity(stages,[{'type':'CREATE','id':'ghost','time':'1'}])
        self.assertEqual(continuity_status(c),'BLOCKED');self.assertEqual(c[0]['lifecycle_status'],'INDETERMINATE');self.assertEqual(c[0]['mismatches'],['product_B'])


if __name__=='__main__':unittest.main()
