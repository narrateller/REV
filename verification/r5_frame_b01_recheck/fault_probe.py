"""Independent faults against SAVED package; no generator is invoked.
Usage: fault_probe.py CHECKOUT ORIGINAL_GIT_ROOT OUTPUT_JSON
Every injected file (including refreshed hashes) is restored by harness only.
"""
import copy,hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(sys.argv[1]).resolve();source=Path(sys.argv[2]).resolve();dest=Path(sys.argv[3]);assert not dest.is_relative_to(R)
P='cad/build/frame_mount/';M=P+'publication_manifest.json';records=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((R/n).read_text())
def snapshot():return {str(p.relative_to(R)):{'sha256':digest(p),'mtime_ns':p.stat().st_mtime_ns,'size':p.stat().st_size} for p in R.rglob('*') if p.is_file() and not {'.git','.venv','__pycache__'}&set(p.parts)}
backups={}
def remember(n):
 if n not in backups:
  p=R/n;backups[n]=(p.read_bytes(),p.stat()) if p.exists() else None
 return R/n
def put(n,b):remember(n).write_bytes(b)
def js(n,d):put(n,(json.dumps(d,indent=2)+'\n').encode())
def update_publication():
 m=read(M)
 for n in m['sha256']:m['sha256'][n]=digest(R/n)
 js(M,m)
def update_run_artifacts():
 run=read(P+'run.json')
 for n in run['artifacts']:run['artifacts'][n]=digest(R/P/n)
 js(P+'run.json',run)
def restore():
 for n,state in backups.items():
  p=R/n
  if state is None:
   if p.exists():p.unlink()
  else:
   data,st=state;p.write_bytes(data);os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns))
 backups.clear()
def invoke(tag,expect=1,require_reason=None):
 before=snapshot();p=subprocess.run(['/usr/bin/python3','-B','cad/frame_mount/verify_output.py'],cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},text=True,capture_output=True);after=snapshot()
 changes={n:{'before':before.get(n),'after':after.get(n)} for n in before.keys()|after.keys() if before.get(n)!=after.get(n)}
 payload=json.loads(p.stdout);reason=payload.get('reason','');ok=p.returncode==expect and not changes and (payload.get('status')==('PASS' if expect==0 else 'FAIL')) and (expect==0 or bool(reason)) and (not require_reason or require_reason in reason)
 records.append({'case':tag,'command':p.args,'exit_code':p.returncode,'stdout':payload,'stderr':p.stderr,'snapshot_files':len(before),'file_changes':changes,'pass':ok})
 dest.write_text(json.dumps({'cases':records,'count':len(records),'passed':sum(r['pass'] for r in records)},indent=2)+'\n')
 print(tag,p.returncode,ok,reason,flush=True)
 try:assert ok,(tag,p.stdout,changes)
 finally:restore()
# No generation before any of these checks.
invoke('saved_fixture_baseline',0)
for name in ('A/layout_A.FCStd','B/layout_B.step','B/isometric.png','geometry_evidence.json','inventory/inventory.json','generation.json'):
 for kind in ('missing','corrupt'):
  target=P+name;remember(target)
  if kind=='missing':(R/target).unlink()
  else:put(target,b'R5 independent damaged artifact\x00')
  invoke(kind+'_'+name)
remember(M).unlink();invoke('missing_publication_manifest')
put(M,b'{invalid JSON');invoke('corrupt_publication_manifest')
js(M,{'schema_version':1,'sha256':{}});invoke('stale_schema1_manifest')
x=read(M);x['sha256']={};js(M,x);invoke('incomplete_manifest_catalog')
put(P+'unrecorded_R5.json',b'{"extra":true}\n');invoke('extra_unrecorded_artifact')
# Valid native file from prior release, not corrupt bytes.
pointer=subprocess.check_output(['git','show','5198e0184b35978701ed1ce762d9e4fcd44997b3:'+P+'A/layout_A.FCStd'],cwd=source,text=True);oid=next(l.split(':')[1] for l in pointer.splitlines() if l.startswith('oid sha256:'));old=source/'.git/lfs/objects'/oid[:2]/oid[2:4]/oid;assert old.exists();put(P+'A/layout_A.FCStd',old.read_bytes());invoke('stale_valid_FCStd')
old_report=subprocess.check_output(['git','show','5198e0184b35978701ed1ce762d9e4fcd44997b3:'+P+'assessment.md'],cwd=source);put(P+'assessment.md',old_report);invoke('stale_valid_assessment')
x=read('cad/frame_mount/inputs.assumed.json');x['input_revision']=6;js('cad/frame_mount/inputs.assumed.json',x);invoke('stale_valid_input')
remember(P+'A/layout_A.step').unlink();put(P+'inventory/inventory.json',b'{}');invoke('compound_missing_STEP_corrupt_inventory')
remember('verification/r4_frame_mount/final_checks.json').unlink();invoke('missing_historical_final_checks')
# Refresh public hashes to reach semantic assertions, instead of accepting a
# hash-mismatch-only rejection as evidence of the native/schema checks.
x=read(P+'geometry_evidence.json');x['before_after_native'].pop();js(P+'geometry_evidence.json',x);update_publication();invoke('resealed_missing_18th_pair')
x=read(P+'inventory/inventory.json');n=next(i for i,r in enumerate(x['rows']) if r['classification']=='NATIVE_PENETRATION');x['rows'].pop(n);x['summary']['NATIVE_PENETRATION']-=1;js(P+'inventory/inventory.json',x);update_run_artifacts();update_publication();invoke('resealed_hidden_OPEN_penetration')
# Independent CylinderRemoval height substitution with refreshed exports/run/pub hashes.
sys.path.append('/usr/lib/freecad-python3/lib');import FreeCAD as App
App.ParamGet('User parameter:BaseApp/Preferences/Document').SetInt('CountBackupFiles',0)
for v in 'AB':
 target=P+v+'/layout_'+v+'.FCStd';remember(target);d=App.openDocument(str(R/target));q=d.getObject('CylinderRemoval');q.setExpression('Height',None);q.Height=q.Height.Value+1.;d.recompute();d.save();App.closeDocument(d.Name)
 mf=P+v+'/manifest.json';x=read(mf);x['exports']['layout_'+v+'.FCStd']=digest(R/target);js(mf,x);update_run_artifacts();update_publication();invoke('resealed_native_query_height_'+v,require_reason='native CAD validation')
# Full valid A native substituted for B, with refreshed file hashes.
put(P+'B/layout_B.FCStd',(R/(P+'A/layout_A.FCStd')).read_bytes());x=read(P+'B/manifest.json');x['exports']['layout_B.FCStd']=digest(R/(P+'B/layout_B.FCStd'));js(P+'B/manifest.json',x);update_run_artifacts();update_publication();invoke('resealed_A_native_in_B',require_reason='native CAD validation')
invoke('explicit_fixture_restore_baseline',0)
print('all independent faults rejected without writes')
