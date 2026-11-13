"""Run the unchanged independent OUTPUT probe on its exact old document inputs.
A temporary file copy uses the existing object DB read-only; no Git worktree.
"""
import io,json,os,shutil,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OLD='ed8272ce6ebc2047bb0d896db5951d02c42d5208';REVIEW='13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
with tempfile.TemporaryDirectory(prefix='r5-ci-old-') as tmp:
 t=Path(tmp)
 paths=git('ls-tree','-r','--name-only',OLD,'--','verification/r4_cycle_interfaces').decode().splitlines()
 probe='verification/r5_cycle_interfaces_output/independent_probe.py';paths.append(probe)
 for name in paths:
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(git('show',(REVIEW if name==probe else OLD)+':'+name))
 audit=json.loads((t/'verification/r4_cycle_interfaces/proposal/input_audit.json').read_text())
 extras=list(audit['protected_files_sha256'])+['verification/r4_calculated_layout/source_bindings.json']
 for name in extras:
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
 env=os.environ.copy();env['GIT_DIR']=git('rev-parse','--absolute-git-dir').decode().strip();env['GIT_WORK_TREE']=str(t)
 r=subprocess.run([sys.executable,'-B',str(t/probe)],cwd=t,env=env,capture_output=True,text=True)
 assert r.returncode==0,r.stderr
 actual=json.loads(r.stdout);reference=json.loads(git('show',REVIEW+':verification/r5_cycle_interfaces_output/independent_results.json'))
 assert actual==reference,'Historical JSON differs'
 print(r.stdout,end='')
