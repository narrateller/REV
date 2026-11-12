"""Read-only author-package checks, provenance and captured commands for this review."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'verification/r3_parametric_sizing'
EXPECTED=json.loads((SOURCE/'sha256.json').read_text())
paths=sorted(set(EXPECTED)|{'verification/r3_parametric_sizing/sha256.json','verification/r3_parametric_sizing/review_request.md'})
def snapshot():
    return {p:{'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),
               'size':(ROOT/p).stat().st_size,'mtime_ns':(ROOT/p).stat().st_mtime_ns} for p in paths}
before=snapshot()
assert all(before[p]['sha256']==h for p,h in EXPECTED.items())
source_checks=[]
preflight=json.loads((SOURCE/'preflight.json').read_text())
names=['r2_design_basis.txt','r2_input_audit.txt','r2_registry.yaml','r2_script.txt','r5_review.txt']
for record,name in zip(preflight['inputs'],names):
    blob=subprocess.check_output(['git','show',record['commit']+':'+record['path']],cwd=ROOT)
    saved=(SOURCE/'inputs'/name).read_bytes()
    assert blob==saved and hashlib.sha256(blob).hexdigest()==record['sha256']
    source_checks.append({**record,'saved':str((SOURCE/'inputs'/name).relative_to(ROOT)),'byte_identity':'PASS'})
commands=[
 ['.venv/bin/python','-B','scripts/rev_parametric.py'],
 ['.venv/bin/python','-B','scripts/rev_parametric.py'],
 ['.venv/bin/python','-B','-m','unittest','discover','-s','tests','-p','test_rev_parametric.py','-v'],
 ['.venv/bin/python','-B','-m','unittest','discover','-s','tests','-v'],
 ['.venv/bin/python','-B','scripts/check_registry.py','--check-git'],
 ['git','diff','--check'],
 ['gh','pr','view','39','--json','number,title,headRefName,headRefOid,baseRefName,state,body,url'],
 ['gh','pr','view','38','--json','number,state,mergeCommit,mergedAt,headRefOid,url'],
 ['git','ls-remote','origin','refs/heads/main'],
]
results=[]
for i,cmd in enumerate(commands):
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    log=f'command_{i+1:02}.log'
    (HERE/log).write_text('$ '+' '.join(cmd)+'\nexit='+str(run.returncode)+'\nSTDOUT\n'+run.stdout+'\nSTDERR\n'+run.stderr)
    results.append({'argv':cmd,'exit':run.returncode,'log':log})
    assert run.returncode==0, (cmd,run.stderr)
after=snapshot()
assert before==after
assert (HERE/'command_01.log').read_text()==(HERE/'command_02.log').read_text()
objects=[]
for obj in ['8a1ad4199fea09d1157972d7aa28eaad1e8e0337','f806995ff6cc6e322c902039e14d103f10875cc1',
            '4fd6f32b4df3186a805ac7e654be6c4c9e1c6a50','81e5dba4bb47cf8a552b3eb55733454ac4f9742d',
            '5fdc50bbc8e83241ad2f8754860a503f5de9f418','8867521a83bd4608886d81678683ea89cce7e4a3']:
    objects.append({'sha':obj,'type':subprocess.check_output(['git','cat-file','-t',obj],cwd=ROOT,text=True).strip()})
diff=subprocess.check_output(['git','diff','--name-only',objects[0]['sha'],objects[1]['sha']],cwd=ROOT,text=True).splitlines()
record={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'session_id':os.getenv('CODEX_SESSION_ID'),'runtime_session_id':os.getenv('CODEX_CAAS_SESSION_ID'),
        'python':sys.version,'platform':platform.platform(),'objects':objects,'handoff_diff_paths':diff,
        'source_inputs':source_checks,'author_hashes_verified':len(EXPECTED),
        'protected_files':len(paths),'before':before,'after':after,
        'unchanged_sha_size_mtime':True,'two_readonly_outputs_identical':True,'commands':results}
(HERE/'reproduction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ('observed_at_utc','session_id','author_hashes_verified','protected_files','unchanged_sha_size_mtime','two_readonly_outputs_identical')},ensure_ascii=False))
