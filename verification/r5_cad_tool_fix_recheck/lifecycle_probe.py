import sys,json,copy
sys.path.insert(0,sys.argv[1]+'/cad/layout')
from layout_lifecycle import apply_boundary_events
from check_layout import assess_continuity,continuity_status

def body(x=0):return {'lo':[str(x),'0','0'],'hi':[str(x+1),'1','1'],'delta':['0','0','0'],'motion':'linear','exact_box':True}
p='product_B';inside={p:body()};exited={p:body(2)};evt={'type':'REMOVE','id':p,'time':'1','final_rear':'0','exit_boundary':'2'};context={p:{'exit_boundary':'2','receiving_yz':[['0','1'],['0','1']],'required_link':'LINK_CONFIRMED','path_collision':'NO_COLLISION'}}
rows=[]
def test(name,before,after,events,ctx,want,ids):
 effective,audit=apply_boundary_events(before,after,'1',events,ctx);okay=audit['status']==want and sorted(effective)==ids;rows.append({'id':name,'expected':want,'expected_registry':ids,'passed':okay,'actual':audit});assert okay,rows[-1]
test('original_premature_remove',inside,{},[evt],None,'BLOCKED',[p])
test('original_ghost_create',inside,inside,[{'type':'CREATE','id':'ghost','time':'1'}],None,'INVALID_INPUT',[p])
test('original_supported_shape_unsupported_create',{}, {'ghost':body()},[{'type':'CREATE','id':'ghost','time':'1'}],None,'INDETERMINATE',[])
test('premature_plus_unknown_create',inside,{'ghost':body()},[evt,{'type':'CREATE','id':'ghost','time':'1'}],context,'BLOCKED',[p])
test('residue_lost_plus_split',{'residue':body(),p:body()}, {'piece':body()},[{'type':'SPLIT','id':p,'time':'1','children':['piece']}],None,'BLOCKED',[p,'residue'])
valid={**evt,'final_rear':'2'}
test('valid_remove',exited,{},[valid],context,'VALID',[])
test('duplicate_mixed_representation_times',exited,{},[valid,{**valid,'time':'2/2'}],context,'INVALID_INPUT',[p])
test('unknown_link_plus_proven_path_collision',exited,{},[valid],{p:{**context[p],'required_link':'LINK_INDETERMINATE','path_collision':'COLLISION'}},'BLOCKED',[p])
test('forged_rear_and_unknown_create',inside,{'ghost':body()},[valid,{'type':'CREATE','id':'ghost','time':'1'}],context,'INVALID_INPUT',[p])
test('outside_receipt_plus_unknown_link',exited,{},[valid],{p:{**context[p],'receiving_yz':[['0','1/2'],['0','1']],'required_link':'LINK_INDETERMINATE'}},'BLOCKED',[p])
test('valid_remove_unknown_unrelated_event',exited,{},[valid,{'type':'FOLD','id':p,'time':'1'}],context,'INVALID_INPUT',[p])
# Unsupported event without conflicting ID retains the existing object.
test('unsupported_event',exited,exited,[{'type':'FOLD','id':p,'time':'1'}],context,'INDETERMINATE',[p])
for i,t in enumerate(('1/2','2',False,'NaN')):test('bad_time_'+str(i),exited,{},[{**valid,'time':t}],context,'INVALID_INPUT',[p])
checks=assess_continuity([{'phase':'EJECT','time':['0','1'],'state':inside},{'phase':'RESET','time':['1','2'],'state':{}}],[evt],context)
assert continuity_status(checks)=='BLOCKED' and checks[0]['lifecycle_audit']['retained_ids']==[p]
rows.append({'id':'original_continuity_counterexample','passed':True,'actual':checks})
for event in ({'type':'HIDE','id':p,'time':'3/2'}, {'type':'CREATE','id':'ghost','time':'1'},None):
 checks=assess_continuity([{'phase':'a','time':['0','1'],'state':inside},{'phase':'b','time':['1','2'],'state':inside}],[event],context);assert continuity_status(checks)=='BLOCKED';rows.append({'id':'extraneous_or_inconsistent_boundary_event','passed':True,'actual':checks})
print(json.dumps(rows,indent=2));open(sys.argv[2],'w').write(json.dumps(rows,indent=2)+'\n')
