"""Verify immutable Git objects and working bytes, including candidate-vs-handoff."""
from pathlib import Path
import hashlib,json,subprocess,datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
C='8b72716021b0c3a64972033d09fe5e80945eb98e';H='fa4c59702e338e6b6d1e322b0698137a233ad011';D='a85e69f3a495176c614202a518be6784be8f3b31';BASE='962a2a9e0d12d8b4ccf7edd27be6163124ad52a3'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(ref,name):return git('show',ref+':'+name)
def sha(b):return hashlib.sha256(b).hexdigest()
def tree(ref,path):return git('rev-parse',ref+':'+path).decode().strip()
def main():
 declared=json.loads(blob(C,'verification/r4_cycle_interfaces/journal_correction/preservation.json'))
 groups={}
 for category in ['protected_files_sha256','preserved_trees_sha256','payload_and_exports_byte_identical']:
  rows=[]
  for path,expected in declared[category].items():
   raw=[blob(ref,path) for ref in [BASE,C,H]];assert len(set(raw))==1,path
   def content_sha(b):
    return b.decode().split('oid sha256:')[1].splitlines()[0] if b.startswith(b'version https://git-lfs.github.com/spec/v1\n') else sha(b)
   values={ref:content_sha(b) for ref,b in zip([BASE,C,H],raw)};values['working']=sha((ROOT/path).read_bytes())
   assert set(values.values())=={expected},(path,values,expected)
   rows.append(dict(path=path,sha256=expected))
  groups[category]=rows
 roots=['cad','models','scripts','tests','params','evidence','drives','calculations','verification/r4_cycle_interfaces/semantics_v1']
 roots=[r for r in roots if subprocess.run(['git','cat-file','-e',C+':'+r],cwd=ROOT,capture_output=True).returncode==0]
 trees={path:{ref:tree(ref,path) for ref in ([BASE,C,H] if path.endswith('semantics_v1') else ['144941cbfc67002cbe81765e38c80e237473deff',C,H])} for path in roots}
 assert all(len(set(v.values()))==1 for v in trees.values())
 package=git('ls-tree','-r','--name-only',C,'verification/r4_cycle_interfaces').decode().splitlines()
 assert all(blob(C,p)==blob(H,p)==(ROOT/p).read_bytes() for p in package)
 ancestry={ref:subprocess.run(['git','merge-base','--is-ancestor',ref,H],cwd=ROOT).returncode==0 for ref in [C,D,'4e52c3953c989c1077107d1d4f4da6d39d923d85','18e5af1dae177cdfcb24951d3b36c2fd43395421','88a34f8b7d2d6dbf236101f207e206efb0e3c747','0ff3c8f4502ea29c712bf1f41e223f172c5a21c7','3d317b32596884cc60d9d42675924b88fcb29bf0','5fb731182a2bdf6b11246558eca58962e48568d9','13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2']}
 assert all(ancestry.values())
 # Verify the entire seven original independent review packages at the input H.
 review_roots=['verification/r5_cycle_interfaces_output','verification/r5_cycle_interfaces_recheck','verification/r5_ci_semantic_minimum_recheck','verification/r5_ci_strict_types_recheck','verification/r5_ci_snapshots_recheck','verification/r5_ci_gate_exits_recheck','verification/r5_ci_raw_sources_recheck']
 history={}
 for path in review_roots:
  files=git('ls-tree','-r','--name-only',H,path).decode().splitlines();assert files,path
  history[path]={p:sha(blob(H,p)) for p in files}
  assert all(sha((ROOT/p).read_bytes())==digest for p,digest in history[path].items())
 claim=json.loads(blob(C,'verification/r4_cycle_interfaces/claim.json'))
 data=dict(reviewed_C=C,handoff_H=H,R1=D,checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),groups=groups,protected_trees=trees,all_interface_files_C_H_working_equal=len(package),ancestry=ancestry,seven_review_packages=history,interface_rejection_history_preserved=7,material_rejection_history_preserved=2,claim_owner=claim['owner_session'],claim_lease_expires_at=claim['lease_expires_at'],claim_NOT_extended=True,source_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/'verification/r4_cycle_interfaces/proposal').glob('*.py')},physical_READY='NO_GO',W02='NO_GO',PLC='NO_GO',G1='OPEN')
 (OUT/'preservation.json').write_text(json.dumps(data,indent=2)+'\n');print('Preserved:',{k:len(v) for k,v in groups.items()},'package:',len(package),'review packages:',len(history))
if __name__=='__main__':main()
