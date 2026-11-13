"""Evidence capture and immutable-input audit; exit 0 does not imply acceptance."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces/proposal'
C='144941cbfc67002cbe81765e38c80e237473deff';H='7ee1c8f16eca515a3e21f64177152b4e7b93ce92';OLD='ed8272ce6ebc2047bb0d896db5951d02c42d5208';R5='13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
commands=[[sys.executable,'-B',str(HERE/'historical_replay.py')],[sys.executable,'-B',str(P/'check_package.py')],[sys.executable,'-B',str(P/'check_exports_reproduction.py')],[sys.executable,'-B','-m','unittest','discover','-s','verification/r4_cycle_interfaces/correction','-p','test_*.py','-v'],[sys.executable,'-B',str(HERE/'independent_probe.py')],['git','diff','--check'],['git','lfs','fsck']]
records=[]
for i,argv in enumerate(commands,1):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
 (HERE/f'command_{i:02}.stdout').write_text(r.stdout);(HERE/f'command_{i:02}.stderr').write_text(r.stderr)
 records.append(dict(argv=argv,cwd=str(ROOT),started_at_utc=start,exit_code=r.returncode,stdout=f'command_{i:02}.stdout',stderr=f'command_{i:02}.stderr'));(HERE/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
 assert r.returncode==0,(argv,r.stderr)
 if i==1:assert json.loads(r.stdout)==json.loads((HERE/'historical_baseline.json').read_text())
 if i==2:assert json.loads(r.stdout)==json.loads((HERE/'author_documents.json').read_text())
 if i==3:
  norm=lambda text:json.loads(re.sub(r'/tmp/rev-ci-doc-[^/]+/','/tmp/rev-ci-doc-SESSION/',text))
  assert norm(r.stdout)==norm((HERE/'author_exports.json').read_text())
 if i==4:assert re.search(r'Ran 7 tests',r.stderr) and r.stderr.rstrip().endswith('OK')
 if i==5:assert json.loads(r.stdout)==json.loads((HERE/'independent_results.json').read_text())
audit=json.loads((P/'input_audit.json').read_text());assert all(sha((ROOT/p).read_bytes())==h for p,h in audit['protected_files_sha256'].items())
trees={}
for p,h in audit['protected_trees'].items():
 trees[p]={rev:git('rev-parse',rev+':'+p).decode().strip() for rev in [audit['base_main'],OLD,C,H]};assert all(v==h for v in trees[p].values());assert not git('diff',C,'--',p)
for r in audit['input_blobs']:assert sha(git('show',r['commit']+':'+r['path']))==r['sha256']
for r in audit['frozen_packages']:
 assert git('rev-parse',r['commit']+':'+r['path']).decode().strip()==git('rev-parse',C+':'+r['path']).decode().strip()==r['git_tree'];assert not git('diff',C,'--',r['path'])
assert git('rev-parse',R5+':verification/r5_cycle_interfaces_output')==git('rev-parse',C+':verification/r5_cycle_interfaces_output')
identity=[]
for p in git('ls-tree','-r','--name-only',C,'--','verification/r4_cycle_interfaces').decode().splitlines():
 b=git('show',C+':'+p);assert b==git('show',H+':'+p)==(ROOT/p).read_bytes();identity.append(dict(path=p,sha256=sha(b)))
frozen=json.loads((ROOT/'verification/r4_cycle_interfaces/correction/preservation.json').read_text())['byte_identical_proposal_files']
for p,h in frozen.items():assert sha((P/p).read_bytes())==h and (P/p).read_bytes()==git('show',OLD+':verification/r4_cycle_interfaces/proposal/'+p)
for commit in [R5,C,OLD]:assert subprocess.run(['git','merge-base','--is-ancestor',commit,H],cwd=ROOT).returncode==0
before=json.loads((HERE/'before.json').read_text());changed=[];meta=[]
for p,h in before.items():
 b=(ROOT/p).read_bytes()
 if sha(b)!=h:
  if p in ['STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','reviews/cross_check_log.md'] and git('show',H+':'+p) in b:meta.append(p)
  else:changed.append(p)
assert not changed,changed
(HERE/'preservation.json').write_text(json.dumps(dict(reviewed_C=C,handoff_H=H,baseline_files=len(before),unchanged_files=len(before)-len(meta),review_metadata_additions=meta,unexpected_changes=changed,protected_files=len(audit['protected_files_sha256']),protected_trees=trees,frozen_packages=audit['frozen_packages'],input_blobs=audit['input_blobs'],identity=identity,source_and_force_files_identical=frozen,old_review_tree_unchanged=True,material_contract_rejections=2),ensure_ascii=False,indent=2)+'\n')
print('Evidence captured; 17 historical findings corrected; six new semantic mutation failures remain. Not acceptance.')
