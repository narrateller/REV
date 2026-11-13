"""Reproduce documentary evidence; exit 0 is capture completion, not acceptance."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,tempfile,re
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces/proposal'
C='ed8272ce6ebc2047bb0d896db5951d02c42d5208';H='c18cb1e28a6358a2a7836809f461a3d594853796'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
commands=[[sys.executable,'-B',str(P/'check_package.py')],[sys.executable,'-B',str(P/'check_exports_reproduction.py')],[sys.executable,'-B',str(HERE/'independent_probe.py')],['git','diff','--check'],['git','lfs','fsck']]
records=[]
for i,argv in enumerate(commands,1):
 r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True);(HERE/f'command_{i:02}.stdout').write_text(r.stdout);(HERE/f'command_{i:02}.stderr').write_text(r.stderr)
 records.append(dict(argv=argv,cwd=str(ROOT),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=r.returncode,stdout=f'command_{i:02}.stdout',stderr=f'command_{i:02}.stderr'))
 assert r.returncode==0,(argv,r.stderr)
 if i==1:assert json.loads(r.stdout)==json.loads((HERE/'author_documents.json').read_text())
 if i==2:
  normalize=lambda text:json.loads(re.sub(r'/tmp/rev-ci-doc-[^/]+/', '/tmp/rev-ci-doc-SESSION/', text))
  assert normalize(r.stdout)==normalize((HERE/'author_export_regressions.json').read_text())
 if i==3:assert json.loads(r.stdout)==json.loads((HERE/'independent_results.json').read_text())
(HERE/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
audit=json.loads((P/'input_audit.json').read_text());files=audit['protected_files_sha256']
assert len(files)==612 and all(sha((ROOT/p).read_bytes())==h for p,h in files.items())
trees={}
for p,h in audit['protected_trees'].items():
 trees[p]={rev:git('rev-parse',rev+':'+p).decode().strip() for rev in [audit['base_main'],C,H]};assert all(x==h for x in trees[p].values());assert not git('diff',C,'--',p)
for r in audit['frozen_packages']:
 assert git('rev-parse',r['commit']+':'+r['path']).decode().strip()==git('rev-parse',C+':'+r['path']).decode().strip()==r['git_tree'];assert not git('diff',C,'--',r['path'])
for r in audit['input_blobs']:assert sha(git('show',r['commit']+':'+r['path']))==r['sha256']
identity=[]
for p in git('ls-tree','-r','--name-only',C,'--','verification/r4_cycle_interfaces').decode().splitlines():
 b=git('show',C+':'+p);assert git('show',H+':'+p)==b and (ROOT/p).read_bytes()==b;identity.append(dict(path=p,sha256=sha(b)))
before=json.loads((HERE/'before.json').read_text());changes=[];metadata=[]
for p,h in before.items():
 b=(ROOT/p).read_bytes()
 if sha(b)!=h:
  if p in ['STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','reviews/cross_check_log.md'] and git('show',H+':'+p) in b:metadata.append(p)
  else:changes.append(p)
assert not changes,changes
(HERE/'preservation.json').write_text(json.dumps(dict(candidate_C=C,handoff_H=H,baseline_files=len(before),unchanged_files=len(before)-len(metadata),review_metadata_additions=metadata,unexpected_changes=changes,protected_612_files='MATCH',protected_trees=trees,frozen_packages=audit['frozen_packages'],input_blobs=audit['input_blobs'],identity=identity,consecutive_rejections=2,geometry='NOT_RUN',physical_READY='NO_GO',G1='OPEN'),ensure_ascii=False,indent=2)+'\n')
print('Evidence captured. Read independent_results.json failed checks; no acceptance implied.')
