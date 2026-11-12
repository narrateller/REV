"""R5 readonly package/integrity reproduction. No solvers, CAD or physical tests."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SRC=ROOT/'verification/r4_cycle_contract'
C='3cf32daef67a91f393b808adb0dc07ba4c73cac2';H='bd7d3bf8f02f4504ec04114ada7cccbd64e11af5'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
pre=json.loads((SRC/'preflight.json').read_text());audit=json.loads((SRC/'input_acceptance.json').read_text())
old=json.loads((SRC/'integrity_checks.json').read_text())['files']
assert all(sha(ROOT/p)==v['sha256'] for p,v in old.items())
blobs=[]
for src in pre['sources']:
 data=git('show',src['commit']+':'+src['path']);assert hashlib.sha256(data).hexdigest()==src['sha256']
 if src['in_current_main_worktree']:assert (ROOT/src['path']).read_bytes()==data
 blobs.append({'commit':src['commit'],'path':src['path'],'sha256':src['sha256']})
trees=[]
for path,expected in pre['protected_main_git_trees'].items():
 actual={rev:git('rev-parse',rev+':'+path).decode().strip() for rev in (audit['main'],C,H)}
 assert all(v==expected for v in actual.values());assert not git('diff',audit['main'],'--',path)
 assert not git('ls-files','--others','--exclude-standard','--',path)
 trees.append({'path':path,'expected':expected,'actual':actual,'working_diff':'EMPTY'})
candidate={path:git('rev-parse',pre['protected_unmerged_CAD_commit']+':'+path).decode().strip() for path in pre['protected_unmerged_CAD_git_trees']}
assert candidate==pre['protected_unmerged_CAD_git_trees']
paths=set(old)|{str(p.relative_to(ROOT)) for p in SRC.rglob('*') if p.is_file()}
def snap():return {p:{'sha256':sha(ROOT/p),'size':(ROOT/p).stat().st_size,'mtime_ns':(ROOT/p).stat().st_mtime_ns} for p in sorted(paths)}
before=snap();commands=[
 ['python3','-B','verification/r4_cycle_contract/check_documents.py'],
 ['python3','-B','verification/r4_cycle_contract/check_documents.py'],
 ['.venv/bin/python','-B','scripts/check_registry.py','--check-git'],
 ['git','diff','--check'],
 ['gh','pr','view','43','--json','state,mergeCommit,mergedAt,headRefOid,url'],
 ['git','ls-remote','origin','refs/heads/main']]
checks=[]
for i,cmd in enumerate(commands,1):
 p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);name=f'command_{i:02}.log'
 (HERE/name).write_text('$ '+' '.join(cmd)+'\nexit='+str(p.returncode)+'\nSTDOUT\n'+p.stdout+'\nSTDERR\n'+p.stderr)
 checks.append({'argv':cmd,'exit':p.returncode,'log':name});assert p.returncode==0,(cmd,p.stderr)
after=snap();assert before==after;assert (HERE/'command_01.log').read_text()==(HERE/'command_02.log').read_text()
for a,b in ((audit['claim_record_commit'],audit['main']),(audit['main'],C),(C,H)):
 assert subprocess.run(['git','merge-base','--is-ancestor',a,b],cwd=ROOT).returncode==0
record={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'session_id':os.getenv('CODEX_SESSION_ID'),'runtime_session_id':os.getenv('CODEX_CAAS_SESSION_ID'),
 'reviewed_C':C,'handoff_H':H,'python':sys.version,'input_blobs':blobs,'protected_main_trees':trees,'unmerged_CAD_commit':pre['protected_unmerged_CAD_commit'],'unmerged_CAD_trees':candidate,
 'author_508_hashes_match':True,'protected_files':len(paths),'before':before,'after':after,'unchanged_sha_size_mtime':True,'two_checker_outputs_identical':True,'commands':checks}
(HERE/'reproduction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('before','after','commands','input_blobs','protected_main_trees')},ensure_ascii=False))
