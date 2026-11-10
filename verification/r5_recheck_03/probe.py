"""Independent review probes; does not modify author inputs or saved model outputs."""
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'models/kinematic_press'
spec=importlib.util.spec_from_file_location('reviewed_model',P/'model.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
plan=json.loads((P/'phase_plan.json').read_text()); inputs=json.loads((P/'phase_inputs_synthetic.json').read_text())
coverage=m.evaluate_phases(plan,inputs)
out={'reviewed_commit':'36cda8132dcf9dbb7193b01e98bdfff2ba5e2a7b','coverage':{p:{'checked':len(c['checked_pairs']),'unchecked':len(c['unchecked_pairs'])} for p,c in coverage.items()}}
# An omitted, physically relevant solid wall can intersect the punch while all listed pairs pass.
changed=copy.deepcopy(inputs); phase=changed['phases']['B-EJECT']; phase['bodies']['channel_wall']=copy.deepcopy(phase['bodies']['punch']); phase['bodies']['channel_wall']['delta']=[0,0,0]
c=m.evaluate_phases(plan,changed)['B-EJECT']
out['omitted_punch_channel']={'all_declared_clear':all(x['collision_status']=='NO_COLLISION' for x in c['checked_pairs']), 'unchecked':len(c['unchecked_pairs']), 'direct_contact_interval':[str(x) for x in m.overlap_time(m.box(phase['bodies']['punch']),m.box(phase['bodies']['channel_wall']))]}
# Identity of overlay does not establish punch/product kinematic coupling.
a=copy.deepcopy(inputs['phases']['A-PRESS']); a['bodies']['product']['delta']=[0,0,0]
out['stationary_product_overlay']=m.verify_a_out(a,copy.deepcopy(a))
# A successful scalar claim can be independent of a stationary product and punch.
case=copy.deepcopy(next(c for c in json.loads((P/'fixtures.json').read_text())['cases'] if c['id']=='R5-B-EJECT-SUFFICIENT'))
out['sufficient_fixture_bodies']=case['bodies']
for b in case['bodies']: b['delta']=[0,0,0]
r=m.check(case); out['stationary_ejection']={k:r[k] for k in ['collision_status','ejection_status','ejection_evidence']}
# Compare actual last boundary against initial READY, with contiguous second-cycle time.
out['actual_cycle_closure']={}
for variant,last in [('A','A-RETURN'),('B','B-RESET')]:
 before=inputs['phases'][last]; ready=inputs['phases'][variant+'-READY']; end=before['time'][1]
 out['actual_cycle_closure'][variant]=m.transition(last,variant+'-READY',before['bodies'],ready['bodies'],{k:True for k in m.GUARDS[variant+'-READY']},coverage[last],before['time'],[end,end+1])
# Direct verification of every adjacent original boundary, independent of transition status.
out['adjacent_boundary_mismatches']=[]
for seq in [['A-READY','A-FILL','A-ISOLATE','A-PRESS','A-RETURN'],['B-READY','B-FILL','B-PRESS','B-UNLOAD','B-OPEN','B-EJECT','B-RESET']]:
 for left,right in zip(seq,seq[1:]):
  a,b=inputs['phases'][left],inputs['phases'][right]
  for name in a['bodies']:
   lo,hi,d=m.box(a['bodies'][name]); nl,nh,_=m.box(b['bodies'][name])
   if any(lo[i]+d[i]!=nl[i] or hi[i]+d[i]!=nh[i] for i in range(3)): out['adjacent_boundary_mismatches'].append([left,right,name])
print(json.dumps(out,ensure_ascii=False,indent=2))
assert out['omitted_punch_channel']['all_declared_clear']
assert out['stationary_product_overlay']=='CONSISTENT'
assert out['stationary_ejection']['ejection_status']=='SUFFICIENT_STROKE'
assert not out['adjacent_boundary_mismatches']
