"""Readonly R5 reproduction; no solver/CAD/physical runs."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
C='4f31ed624336e1101b0ba04857f4316c73e4d375';H='ec4968f81ba8ec51c707689d804d7a588bddec35';R5='d99afb4c3231d641d4a4921f39987264ce5ffc23'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
SRC=ROOT/'verification/r4_cycle_contract';FIX=ROOT/'verification/r4_cycle_contract_fix'
pre=json.loads((SRC/'preflight.json').read_text());audit=json.loads((SRC/'input_acceptance.json').read_text())
watch=json.loads((FIX/'integrity_checks.json').read_text())['files']
assert all(sha(ROOT/p)==v['sha256'] for p,v in watch.items())
trees=[]
for p,h in pre['protected_main_git_trees'].items():
 actual={rev:git('rev-parse',rev+':'+p).decode().strip() for rev in (audit['main'],C,H)}
 assert all(v==h for v in actual.values()) and not git('diff',audit['main'],'--',p)
 assert not git('ls-files','--others','--exclude-standard','--',p)
 trees.append({'path':p,'expected':h,'actual':actual})
for p,h in pre['protected_unmerged_CAD_git_trees'].items():assert git('rev-parse',pre['protected_unmerged_CAD_commit']+':'+p).decode().strip()==h
source=[]
for s in pre['sources']:
 data=git('show',s['commit']+':'+s['path']);assert hashlib.sha256(data).hexdigest()==s['sha256'];source.append(s)
review_tree=git('rev-parse',R5+':verification/r5_r4_cycle_contract_review').decode().strip()
assert git('rev-parse',C+':verification/r5_r4_cycle_contract_review').decode().strip()==review_tree
assert not git('diff',R5,'--','verification/r5_r4_cycle_contract_review')
paths=set(watch)
for folder in (SRC,FIX):paths.update(str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
def snap():return {p:{'sha256':sha(ROOT/p),'size':(ROOT/p).stat().st_size,'mtime_ns':(ROOT/p).stat().st_mtime_ns} for p in sorted(paths)}
before=snap();commands=[
 ['python3','-B','verification/r4_cycle_contract_fix/check_fix.py','--baseline'],
 ['python3','-B','verification/r4_cycle_contract_fix/check_fix.py'],
 ['python3','-B','verification/r4_cycle_contract_fix/check_fix.py'],
 ['python3','-B','verification/r4_cycle_contract/check_documents.py'],
 ['python3','-B','verification/r4_cycle_contract/check_documents.py'],
 ['.venv/bin/python','-B','scripts/check_registry.py','--check-git'],
 ['git','diff','--check'],
 ['gh','pr','view','43','--json','state,mergeCommit,mergedAt,url'],
 ['git','ls-remote','origin','refs/heads/main']]
checks=[]
for i,cmd in enumerate(commands,1):
 r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);log=f'command_{i:02}.log'
 (HERE/log).write_text('$ '+' '.join(cmd)+'\nexit='+str(r.returncode)+'\nSTDOUT\n'+r.stdout+'\nSTDERR\n'+r.stderr)
 checks.append({'argv':cmd,'exit':r.returncode,'log':log});assert r.returncode==0,(cmd,r.stderr)
 if i==1:assert json.loads(r.stdout)==json.loads((ROOT/'verification/r5_r4_cycle_contract_review/independent_results.json').read_text())
 if i==2:assert json.loads(r.stdout)==json.loads((FIX/'results.json').read_text())
after=snap();assert before==after
for a,b in ((2,3),(4,5)):assert (HERE/f'command_{a:02}.log').read_text()==(HERE/f'command_{b:02}.log').read_text()
for a,b in ((R5,C),(C,H),(audit['claim_record_commit'],audit['main'])):assert subprocess.run(['git','merge-base','--is-ancestor',a,b],cwd=ROOT).returncode==0
record={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'session_id':os.getenv('CODEX_SESSION_ID'),'runtime_session_id':os.getenv('CODEX_CAAS_SESSION_ID'),'python':sys.version,
 'reviewed_C':C,'handoff_H':H,'previous_review_commit':R5,'previous_review_tree':review_tree,'previous_review_tree_unchanged':True,
 'protected_main_trees':trees,'protected_CAD_commit':pre['protected_unmerged_CAD_commit'],'protected_CAD_trees':pre['protected_unmerged_CAD_git_trees'],
 'input_blobs':source,'author_integrity_hashes_match':len(watch),'protected_files':len(paths),'before':before,'after':after,'unchanged_sha_size_mtime':True,'repeat_command_outputs_identical':True,'commands':checks}
(HERE/'reproduction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('before','after','commands','input_blobs','protected_main_trees')},ensure_ascii=False))
