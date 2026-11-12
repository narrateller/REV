"""Independent R5 expectations for C=66924ae. Not the old bug-preserving probe.
Usage: /usr/bin/python3 probe.py ROOT OUTPUT_JSON
Synthetic mutations are verifier fixtures, never product design inputs.
"""
import copy,gzip,itertools,json,sys
from pathlib import Path
from fractions import Fraction as Q
root=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root/'cad/layout_correction'))
from assess import checked,classify,box_at,scene_geometric_status
from outcomes import assess_scene,evaluate_suite
from verify_cycles import verify_cycles
from layout_common import load
D=load(root/'cad/layout_correction/inputs.assumed.json')
S=json.loads(gzip.decompress((root/'cad/build/layout_correction/raw_checked_tool/all_pairs.json.gz').read_bytes()))
rows=[]
def box(x,motion='linear'):
 return {'lo':[str(x),'0','0'],'hi':[str(x+1),'1','1'],'delta':['0','0','0'],'motion':motion,'exact_box':True,'group':'fixture'}
def save_class(tag,state,row=None,interval=None):
 interval=interval or ['2','5'];a,b=list(state)[:2]
 if row is None:row=checked.evaluate_pair(state[a],state[b],a,b,interval,'A')
 r=classify(row,state,interval,'A')
 ok=r['class']=='INDETERMINATE' and bool(r.get('reason')) and r.get('exact_box_sign_coverage')=='NOT_ESTABLISHED' and r.get('raw_evidence')==row.get('evidence')
 rows.append({'id':tag,'expected':'INDETERMINATE with reason; coverage NOT_ESTABLISHED; preserve raw evidence','actual':r,'pass':ok})
for motion in ('rotation','spline','nonlinear',None):
 for x in (0,1,7):
  state={'moving':box(0,motion),'wall':box(x)}
  save_class('B01_'+str(motion)+'_'+str(x),state)
  assert box_at(state['moving'],'3',['2','5']) is None
for kind in ('unknown_delta','bad_extent','missing_terminal_point','gap','unknown_evidence','contradictory_CLEAR','missing_pair_body','invalid_interval'):
 state={'moving':box(0),'wall':box(7)};r=checked.evaluate_pair(*state.values(),'moving','wall',['2','5'],'A');interval=['2','5']
 if kind=='unknown_delta':state['moving']['delta']=None
 if kind=='bad_extent':state['moving']['hi'][0]='-2'
 if kind=='missing_terminal_point':r['evidence']['segments'].pop()
 if kind=='gap':r['evidence']['segments'][1]['from']='3'
 if kind=='unknown_evidence':r['evidence']['segments'][1]['collision_status']='INDETERMINATE'
 if kind=='contradictory_CLEAR':r['evidence']['segments'][0]['collision_status']='COLLISION'
 if kind=='missing_pair_body':del state['wall']
 if kind=='invalid_interval':interval=['5','2']
 # Explicit names allow testing a missing body without constructing a new raw pair.
 if kind=='missing_pair_body':
  out=classify(r,state,interval,'A');rows.append({'id':'B01_'+kind,'actual':out,'pass':out['class']=='INDETERMINATE' and bool(out.get('reason'))})
 else:save_class('B01_'+kind,state,r,interval)
state={'a':box(0),'b':box(0),'unknown':box(7,'rotation')};counts={};details=[]
for a,b in itertools.combinations(state,2):
 r=classify(checked.evaluate_pair(state[a],state[b],a,b,['0','1'],'B'),state,['0','1'],'B');details.append(r);counts[r['class']]=counts.get(r['class'],0)+1
rows.append({'id':'B01_known_penetration_and_unknown','actual':{'status':scene_geometric_status(counts),'counts':counts,'pairs':details},'pass':scene_geometric_status(counts)=='BLOCKED' and counts.get('PENETRATION')==1 and counts.get('INDETERMINATE')==2})
# Positive and negative cases are evaluated separately from command success.
suite=evaluate_suite(S,D);ver=verify_cycles(S,D)
rows.append({'id':'eight_baseline','actual':{'suite_status':suite['status'],'scene_results':[ {k:r[k] for k in ('variant','case','geometric_scene_outcome','limited_cycle_success','matches_expectation')} for r in suite['scene_results']],'verifier_cases':len(ver)},'pass':suite['status']=='PASS' and len(ver)==8 and sum(r['limited_cycle_success'] for r in suite['scene_results'])==2})

def trial(tag,scene,index):
 r=assess_scene(scene,D);payload=list(S);payload[index]=scene;rejected=False;why=None
 try:verify_cycles(payload,D)
 except (AssertionError,KeyError,ValueError,TypeError,ZeroDivisionError,NotImplementedError) as e:rejected=True;why=type(e).__name__+': '+str(e)
 rows.append({'id':tag,'expected':'both oracles reject successful sufficient','actual':{k:r[k] for k in ('recomputed','geometric_scene_outcome','limited_cycle_success','matches_expectation','mismatches','blocking_defects')},'verifier_rejects':rejected,'verifier_reason':why,'pass':not r['matches_expectation'] and not r['limited_cycle_success'] and rejected})
for v in 'AB':
 idx=next(i for i,s in enumerate(S) if s['variant']==v and s['case']=='sufficient');base=S[idx];p='product_'+v
 # All 31 nonempty subsets of the five summary conditions, individually and jointly.
 changes={'required_link':'LINK_ABSENT','path_transition':'BLOCKED','continuity_status':'INDETERMINATE','lifecycle':[],'path_ready':'NOT_CONFIRMED'}
 keys=list(changes)
 for bits in range(1,32):
  s=dict(base);lost=[k for i,k in enumerate(keys) if bits&(1<<i)]
  for k in lost:s[k]=changes[k]
  trial(v+'_lost_'+','.join(lost),s,idx)
 # Underlying evidence is changed while successful summary labels are deliberately retained.
 for kind in ('actual_unlinked','boundary_jump','time_gap','remove_early','remove_duplicate','remove_wrong_id','remove_false_rear','CREATE','SPLIT','missing_RETURN','missing_READY','false_READY_name','final_not_restored','pair_omitted','unsupported_return_motion','unlinked_missing_return_unknown'):
  s=copy.deepcopy(base);active=next(st for st in s['stages'] if st['phase'] in ('A-PRESS-OUT','B-EJECT'))
  if kind in ('actual_unlinked','unlinked_missing_return_unknown'):
   for st in s['stages']:
    if p in st['state']:
     for key in ('lo','hi'):st['state'][p][key][0]=str(Q(st['state'][p][key][0])+Q(1,100))
   s['lifecycle'][0]['final_rear']=str(Q(s['lifecycle'][0]['final_rear'])+Q(1,100))
  if kind=='boundary_jump':s['stages'][1]['state']['punch']['lo'][0]=str(Q(s['stages'][1]['state']['punch']['lo'][0])+Q(1,1000))
  if kind=='time_gap':s['stages'][1]['time'][0]='3/2'
  if kind=='remove_early':s['lifecycle'][0]['time']='1'
  if kind=='remove_duplicate':s['lifecycle'].append(copy.deepcopy(s['lifecycle'][0]))
  if kind=='remove_wrong_id':s['lifecycle'][0]['id']='punch'
  if kind=='remove_false_rear':s['lifecycle'][0]['final_rear']='0'
  if kind in ('CREATE','SPLIT'):s['lifecycle'].append({'type':kind,'id':p,'time':active['time'][1]})
  if kind=='missing_RETURN':s['stages']=[st for st in s['stages'] if st['phase']!=v+'-RETURN']
  if kind=='missing_READY':s['stages'].pop()
  if kind=='false_READY_name':s['stages'][-1]['phase']=v+'-READY'
  if kind=='final_not_restored':s['stages'][-1]['state']['punch']['lo'][0]='0'
  if kind=='pair_omitted':s['stages'][0]['pairs'].pop()
  if kind=='unsupported_return_motion':s['stages'][-2]['state']['punch']['motion']='rotation'
  if kind=='unlinked_missing_return_unknown':
   s['stages']=[st for st in s['stages'] if st['phase']!=v+'-RETURN'];s['continuity_status']='INDETERMINATE';s['lifecycle'].append({'type':'CREATE','id':'ghost','time':'0'})
  trial(v+'_'+kind,s,idx)
result={'code_sha':'66924aed1cb2d193b9883d2140d85560b1e4b0cb','count':len(rows),'passed':sum(bool(r['pass']) for r in rows),'failed':[r['id'] for r in rows if not r['pass']],'cases':rows}
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items() if k!='cases'})
sys.exit(bool(result['failed']))
