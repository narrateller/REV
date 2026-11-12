"""Independent semantic counterexamples for the saved FP service verifier.
No code/input/native CAD changes; stale service evidence is rehashed by harness.
A corrected verifier must reject each changed path, even with a valid manifest.
"""
import copy,gzip,hashlib,json,os,subprocess,sys
from fractions import Fraction as F
from pathlib import Path
R=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]);sys.path.insert(0,str(R/'cad/layout_correction'));from assess import checked
P=R/'cad/build/feed_power';record=json.loads((P/'publication_manifest.json').read_text());original=(P/'service_scenes.json.gz').read_bytes();old_manifest=(P/'publication_manifest.json').read_bytes();services=json.loads(gzip.decompress(original));original_extra=(P/'work_and_extra.json.gz').read_bytes();extra_scenes=json.loads(gzip.decompress(original_extra));results=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snap():return {str(p.relative_to(R)):(sha(p),p.stat().st_mtime_ns,p.stat().st_size) for p in R.rglob('*') if p.is_file() and not {'.git','.venv','__pycache__'}&set(p.parts)}
def run(tag,scene,details):
 payload=[scene if (s['variant'],s['case'])==(scene['variant'],scene['case']) else s for s in services]
 (P/'service_scenes.json.gz').write_bytes(gzip.compress(json.dumps(payload,sort_keys=True,separators=(',',':')).encode(),mtime=0))
 extra_payload=[scene if (s['variant'],s['case'])==(scene['variant'],scene['case']) else s for s in extra_scenes]
 (P/'work_and_extra.json.gz').write_bytes(gzip.compress(json.dumps(extra_payload,sort_keys=True,separators=(',',':')).encode(),mtime=0))
 m=copy.deepcopy(record);m['sha256']['cad/build/feed_power/work_and_extra.json.gz']=sha(P/'work_and_extra.json.gz');m['sha256']['cad/build/feed_power/service_scenes.json.gz']=sha(P/'service_scenes.json.gz');(P/'publication_manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 before=snap();p=subprocess.run(['/usr/bin/python3','-B','cad/feed_power/verify_output.py'],cwd=R,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});after=snap()
 results.append({'id':tag,'expected_verifier_exit':1,'actual_verifier_exit':p.returncode,'stdout':json.loads(p.stdout),'stderr':p.stderr,'verifier_writes':before!=after,'details':details,'defect_reproduced':p.returncode==0 and before==after})
 dest.write_text(json.dumps({'cases':results},indent=2)+'\n');print(tag,p.returncode,results[-1]['defect_reproduced'],flush=True)
 (P/'service_scenes.json.gz').write_bytes(original);(P/'work_and_extra.json.gz').write_bytes(original_extra);(P/'publication_manifest.json').write_bytes(old_manifest)

def replaced_motion(base,motions):
 s=copy.deepcopy(base);current=copy.deepcopy(s['stages'][0]['state'])
 for i,stage in enumerate(s['stages']):
  state=copy.deepcopy(current)
  for b in state.values():b['delta']=['0','0','0']
  if 0<i<len(s['stages'])-1:
   for name,delta in motions[i-1]:state[name]['delta']=list(map(str,delta))
  stage['state']=state;stage['pairs']=checked.matrix(state,stage['time'],s['variant']);stage['counts']=checked.summarize(stage['pairs']);current=checked.advance(state)
 s['continuity']=checked.assess_continuity(s['stages'],[]);s['continuity_status']=checked.continuity_status(s['continuity']);s['positions_restored']=all(current[n]['lo']==s['stages'][0]['state'][n]['lo'] and current[n]['hi']==s['stages'][0]['state'][n]['hi'] for n in current);assert s['continuity_status']=='CONTINUOUS' and s['positions_restored'];return s
# Generate direct native witnesses independently from actual saved FCStd.
sys.path.append('/usr/lib/freecad-python3/lib');import FreeCAD as App

def penetration_witnesses(s,pairs=None):
 d=App.openDocument(str(P/s['variant']/('layout_'+s['variant']+'.FCStd')));obs={o.Name:o for o in d.Objects if hasattr(o,'ResearchStatus')};found=[]
 for st in s['stages']:
  state=st['state']
  for a,b in (pairs or (('doser_slide','hopper_R'),('doser_slide','hopper_floor_right'),('doser_slide','receiving_rim_right'))):
   if all(x=='0' for x in state[a]['delta']):continue
   expr=[];events={F(0),F(1)}
   for i in range(3):
    for c,v in [(F(state[a]['hi'][i])-F(state[b]['lo'][i]),F(state[a]['delta'][i])-F(state[b]['delta'][i])),(F(state[b]['hi'][i])-F(state[a]['lo'][i]),F(state[b]['delta'][i])-F(state[a]['delta'][i]))]:
     expr.append((c,v))
     if v and 0<=-c/v<=1:events.add(-c/v)
   events=sorted(events);u=next((t for t in events+[(x+y)/2 for x,y in zip(events,events[1:])] if all(c+v*t>0 for c,v in expr)),None)
   if u is None:continue
   shapes=[]
   for n in (a,b):
    shape=obs[n].Shape.copy();bb=shape.optimalBoundingBox(False,False);pos=[F(x)+u*F(v) for x,v in zip(state[n]['lo'],state[n]['delta'])];shape.translate(App.Vector(*[float(p)*1000-q for p,q in zip(pos,(bb.XMin,bb.YMin,bb.ZMin))]));shapes.append(shape)
   volume=shapes[0].common(shapes[1]).Volume;assert volume>1e-5;found.append({'phase':st['phase'],'pair':[a,b],'u':str(u),'native_common_mm3':volume})
 App.closeDocument(d.Name);return found
for v in 'AB':
 base=next(s for s in services if s['variant']==v and s['case']=='service_fp_doser_retract_lift');lift=F(base['stages'][2]['state']['doser_slide']['delta'][2]);s=replaced_motion(base,[[('doser_slide',(0,0,0))],[('doser_slide',(0,0,lift))],[('doser_slide',(0,0,-lift))],[('doser_slide',(0,0,0))]])
 witnesses=penetration_witnesses(s);assert len(witnesses)==6
 run(v+'_new_service_with_retract_omitted',s,{'actual_path':'zero Y, UP, DOWN, zero Y; still continuous/restored','actual_pairs_recomputed_by_frozen_matrix':True,'native_penetrations':witnesses,'stale_interval_and_assessment':'unchanged; a verifier must detect the inconsistency'})
base=next(s for s in services if s['variant']=='A' and s['case']=='service_fp_doser_retract_lift');side=F(base['stages'][1]['state']['doser_slide']['delta'][1]);lift=F(base['stages'][2]['state']['doser_slide']['delta'][2]);s=replaced_motion(base,[[('doser_slide',(0,0,lift))],[('doser_slide',(0,side,0))],[('doser_slide',(0,0,-lift))],[('doser_slide',(0,-side,0))]])
run('A_lift_before_retract',s,{'actual_path':'UP, Y, DOWN, return Y','native_penetrations':penetration_witnesses(s)})
base=next(s for s in services if s['variant']=='A' and s['case']=='service_fp_powerpack_module');lift=F(base['stages'][1]['state']['hydraulic_tank']['delta'][2]);names=('hydraulic_tank','pump_motor','motor_mount_rear');s=replaced_motion(base,[[(n,(0,0,lift)) for n in names],[(n,(0,0,-lift)) for n in names]])
run('A_powerpack_module_missing_moving_front_plate',s,{'actual_composition':list(names),'omitted_from_motion':'motor_mount_front','native_penetrations':penetration_witnesses(s,[('hydraulic_tank','motor_mount_front')])})
s=copy.deepcopy(next(s for s in services if s['variant']=='A' and s['case']=='service_fp_motor'));s['stages'][1]['state']['pump_motor']['motion']='rotation';st=s['stages'][1];st['pairs']=checked.matrix(st['state'],st['time'],'A');st['counts']=checked.summarize(st['pairs'])
try:checked.engine.body(s['stages'][1]['state']['pump_motor']);support='SUPPORTED'
except (NotImplementedError,KeyError,ValueError) as e:support='INDETERMINATE: '+str(e)
run('A_unsupported_motor_motion',s,{'frozen_body_support':support,'expected':'reject successful service verification; preserve unsupported motion as INDETERMINATE'})
print('semantic counterexamples completed')
