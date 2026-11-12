"""Repeat original R5 sequence with corrected expectations: build -> verify twice.
Generation 1 has already been explicitly run in CHECKOUT (stdout supplied).
Then generation 2 and two verifiers, with native/evidence preservation checks.
"""
import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(sys.argv[1]).resolve();source=Path(sys.argv[2]).resolve();dest=Path(sys.argv[3]);records=[];rounds=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {str(p.relative_to(R)):{'sha256':sha(p),'mtime_ns':p.stat().st_mtime_ns,'size':p.stat().st_size} for p in R.rglob('*') if p.is_file() and not {'.git','.venv','__pycache__'}&set(p.parts)}
def call(script):
 p=subprocess.run(['/usr/bin/python3','-B','cad/frame_mount/'+script+'.py'],cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True)
 records.append({'command':p.args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode==0,(script,p.stdout,p.stderr);return p
baseline=json.loads((source/'verification/r4_frame_fix/preservation.json').read_text())
def semantic():
 evidence={p:sha(R/p) for p in baseline['sha256']};assert evidence==baseline['sha256']
 native={}
 for v in 'AB':
  m=json.loads((R/f'cad/build/frame_mount/{v}/manifest.json').read_text());assert m['objects']==baseline['manifest_objects'][v]
  native[v]={k:m[k] for k in ('objects','input_sha256','reopen_recompute','edit_probe','spreadsheet_parameters','query_volumes')}
 return {'evidence_sha256':evidence,'native_semantics':native}
for i in (1,2):
 if i==2:call('generate')
 run=json.loads((R/'cad/build/frame_mount/run.json').read_text());forbidden={'publication_manifest.json','generation.json','geometry_evidence.json','inequality_rows.json.gz','figure_manifest.json','assessment.md','changes.json'}
 assert not forbidden&set(run['artifacts']),forbidden&set(run['artifacts'])
 before=snapshot();a=call('verify_output');middle=snapshot();b=call('verify_output');after=snapshot();assert a.stdout==b.stdout and a.stderr==b.stderr and before==middle==after
 rounds.append({'generation':i,'same_verifier_results':True,'all_files_bytes_mtime_unchanged':True,'snapshot_files':len(before),'manifest_sha256':sha(R/'cad/build/frame_mount/publication_manifest.json'),'run_owned_artifact_paths':list(run['artifacts']),'semantic':semantic()})
 dest.write_text(json.dumps({'rounds':rounds,'commands':records},indent=2)+'\n')
assert rounds[0]['semantic']==rounds[1]['semantic']
print('PASS: original R5 build/repeat-verifier counterexample corrected, 2 generations/4 readonly checks, deterministic evidence/native geometry preserved')
