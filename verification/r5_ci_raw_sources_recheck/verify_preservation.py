from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces/proposal'
C='b89854ad709bcb5c2991376bed41bf2f73acef82';H='ce1ad73aae7a5700203103c14290375cc519662b';BASE='144941cbfc67002cbe81765e38c80e237473deff';DEC='3aa5ee100f57aa75315d429afef38f8a982b1afc'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
audit=json.loads((P/'input_audit.json').read_text())
assert all(sha((ROOT/p).read_bytes())==h for p,h in audit['protected_files_sha256'].items())
trees={}
for p,h in audit['protected_trees'].items():
 trees[p]={rev:git('rev-parse',rev+':'+p).decode().strip() for rev in [BASE,C,H]};assert all(v==h for v in trees[p].values());assert not git('diff',C,'--',p)
for r in audit['input_blobs']:assert sha(git('show',r['commit']+':'+r['path']))==r['sha256']
for r in audit['frozen_packages']:
 assert git('rev-parse',r['commit']+':'+r['path']).decode().strip()==git('rev-parse',C+':'+r['path']).decode().strip()==r['git_tree'];assert not git('diff',C,'--',r['path'])
for p,rev in [('verification/r5_cycle_interfaces_output','13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2'),('verification/r5_cycle_interfaces_recheck','5fb731182a2bdf6b11246558eca58962e48568d9'),('verification/r1_ci_journal_arbitration',DEC),('verification/r5_ci_gate_exits_recheck','18e5af1dae177cdfcb24951d3b36c2fd43395421'),('verification/r5_ci_snapshots_recheck','88a34f8b7d2d6dbf236101f207e206efb0e3c747'),('verification/r5_ci_strict_types_recheck','0ff3c8f4502ea29c712bf1f41e223f172c5a21c7'),('verification/r5_ci_semantic_minimum_recheck','3d317b32596884cc60d9d42675924b88fcb29bf0')]:assert git('rev-parse',rev+':'+p)==git('rev-parse',C+':'+p) and not git('diff',C,'--',p)
assert git('show',DEC+':decisions/ARB-R1-CI-SEMANTICS-05.md')==(ROOT/'decisions/ARB-R1-CI-SEMANTICS-05.md').read_bytes()
identity=[]
for p in git('ls-tree','-r','--name-only',C,'--','verification/r4_cycle_interfaces').decode().splitlines():
 b=git('show',C+':'+p);assert b==git('show',H+':'+p)==(ROOT/p).read_bytes();identity.append(dict(path=p,sha256=sha(b)))
assert git('rev-parse',C+':verification/r4_cycle_interfaces/semantics_v1')==git('rev-parse','bd7ce8a623d6a4ecdff1f106868a4c7086a8a27f:verification/r4_cycle_interfaces/semantics_v1')
assert len(json.loads((P/'baseline_bindings.json').read_text())['rows'])==44
source_force={}
for p in ['baseline_bindings.json','baseline_bindings.md','force_variants.json','force_variants.md']+['exports/force_'+v+'.svg' for v in ['A-V1','A-V2','B-V1','B-V2']]:
 b=(P/p).read_bytes();assert b==git('show',BASE+':verification/r4_cycle_interfaces/proposal/'+p);source_force[p]=sha(b)
meta=[];bad=[];before=json.loads((HERE/'before.json').read_text())
for p,h in before.items():
 b=(ROOT/p).read_bytes()
 if sha(b)!=h:
  if p in ['STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','reviews/cross_check_log.md'] and git('show',H+':'+p) in b:meta.append(p)
  else:bad.append(p)
assert not bad,bad
for rev in [DEC,BASE,C,'5fb731182a2bdf6b11246558eca58962e48568d9']:assert subprocess.run(['git','merge-base','--is-ancestor',rev,H],cwd=ROOT).returncode==0
(HERE/'preservation.json').write_text(json.dumps(dict(C=C,H=H,decision=DEC,baseline_files=len(before),unchanged_files=len(before)-len(meta),review_metadata_additions=meta,unexpected_changes=bad,protected_files=len(audit['protected_files_sha256']),protected_trees=trees,frozen_packages=audit['frozen_packages'],input_blobs=audit['input_blobs'],identity=identity,source_force_files=source_force,original_reviews_R1_unchanged=True),ensure_ascii=False,indent=2)+'\n')
print('Source/helper/calculations/CAD/reviews/minimum preserved.')
