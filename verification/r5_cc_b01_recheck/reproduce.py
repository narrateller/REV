"""Capture exact commands, outcomes and preservation; never regenerate input evidence."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
C='0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed';H='4c00bd1603e7ebb6afad80ca3c17b38f4b472670';D='616135755d1b6cbaa09ae9800bad5af8bbc28aed'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def hashbytes(b):return hashlib.sha256(b).hexdigest()
checks=[]
commands=[
 [sys.executable,'-B','verification/r4_cycle_contract_fix/check_fix.py','--baseline'],
 [sys.executable,'-B','verification/r4_cc_identity/verify.py','--baseline-second-rejection'],
 [sys.executable,'-B','verification/r4_cc_identity/verify.py'],
 [sys.executable,'-B','verification/r4_cycle_contract/check_documents.py'],
 [sys.executable,'-B','verification/r5_cc_b01_recheck/independent_probe.py'],
 [sys.executable,'-B','scripts/check_registry.py','--check-git'],
 ['git','diff','--check'],
 ['git','lfs','fsck']]
for i,argv in enumerate(commands,1) if "--preservation-only" not in sys.argv else []:
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
 (HERE/f'command_{i:02}.stdout').write_text(r.stdout);(HERE/f'command_{i:02}.stderr').write_text(r.stderr)
 checks.append(dict(argv=argv,cwd=str(ROOT),started_at_utc=start,exit_code=r.returncode,stdout=f'command_{i:02}.stdout',stderr=f'command_{i:02}.stderr'))
 (HERE/'commands.json').write_text(json.dumps(checks,indent=2)+'\n')
 assert r.returncode==0,(argv,r.stderr)
 if i==1:assert json.loads(r.stdout)==json.loads((ROOT/'verification/r5_r4_cycle_contract_review/independent_results.json').read_text())
 if i==2:assert json.loads(r.stdout)==json.loads((ROOT/'verification/r5_r4_cycle_contract_recheck/independent_results.json').read_text())
 if i==3:
  data=json.loads(r.stdout);assert data==json.loads((ROOT/'verification/r4_cc_identity/results.json').read_text());assert data['total_checks']==205 and not data['mismatches']
 if i==5:assert json.loads(r.stdout)==json.loads((HERE/'independent_results.json').read_text())
pre=json.loads((ROOT/'verification/r4_cycle_contract/preflight.json').read_text())
source=[]
for s in pre['sources']:
 b=git('show',s['commit']+':'+s['path']);assert hashbytes(b)==s['sha256']
 if s.get('in_current_main_worktree'):assert (ROOT/s['path']).read_bytes()==b
 source.append(s)
trees=[]
for p,expected in pre['protected_main_git_trees'].items():
 refs={rev:git('rev-parse',rev+':'+p).decode().strip() for rev in [pre['base_main'],C,H]}
 assert all(v==expected for v in refs.values());assert not git('diff',C,'--',p)
 trees.append(dict(path=p,expected=expected,actual=refs))
cad=pre['protected_unmerged_CAD_commit']
for p,expected in pre['protected_unmerged_CAD_git_trees'].items():assert git('rev-parse',cad+':'+p).decode().strip()==expected
ident=[]
for p in git('ls-tree','-r','--name-only',C,'--','verification/r4_cycle_contract','verification/r4_cc_identity','verification/r4_cycle_contract_fix').decode().splitlines():
 b=git('show',C+':'+p);assert git('show',H+':'+p)==b and (ROOT/p).read_bytes()==b;ident.append(dict(path=p,sha256=hashbytes(b)))
for sha in [D,'d99afb4c3231d641d4a4921f39987264ce5ffc23','c56e494a2e89ffa65b5876bfce6a4d6b4ae62f1b',C]:assert subprocess.run(['git','merge-base','--is-ancestor',sha,H],cwd=ROOT).returncode==0
old_trees={}
for p in ['verification/r5_r4_cycle_contract_review','verification/r5_r4_cycle_contract_recheck','verification/r1_cc_arbitration']:
 old_trees[p]=git('rev-parse',C+':'+p).decode().strip();assert git('rev-parse',H+':'+p).decode().strip()==old_trees[p];assert not git('diff',C,'--',p)
assert git('show',D+':decisions/ARB-R1-CC-01.md')==(ROOT/'decisions/ARB-R1-CC-01.md').read_bytes()
before=json.loads((HERE/'before.json').read_text());changed=[];metadata=[]
for p,v in before.items():
 b=(ROOT/p).read_bytes()
 if hashbytes(b)!=v['sha256'] or len(b)!=v['size']:
  if p in ['STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','reviews/cross_check_log.md'] and git('show',H+':'+p) in b:metadata.append(p)
  else:changed.append(p)
assert not changed,changed
result=dict(reviewed_C=C,handoff_H=H,decision=D,sources=source,protected_trees=trees,separate_CAD_commit=cad,separate_CAD_trees=pre['protected_unmerged_CAD_git_trees'],object_identity=ident,old_review_trees=old_trees,baseline_files=len(before),unchanged_files=len(before)-len(metadata),changed_files=changed,review_metadata_additions=metadata,consecutive_rejections=2,all_commands_exit_zero=True,physical_tests='NOT_RUN',G1='OPEN')
(HERE/'preservation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('Commands and preservation PASS')
