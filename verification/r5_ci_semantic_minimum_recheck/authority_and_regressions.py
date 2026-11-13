"""Read-only authority reproduction and unchanged prior probe in a temporary copy.
No Git worktree or tracked evidence update in the real checkout.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
N='verification/r4_cycle_interfaces/semantics_v1';P='verification/r4_cycle_interfaces/proposal'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
with tempfile.TemporaryDirectory(prefix='r5-min-authority-') as tmp:
 t=Path(tmp);build=t/N/'build_minimum.py';build.parent.mkdir(parents=True);shutil.copy(ROOT/N/'build_minimum.py',build)
 env=os.environ.copy();env['GIT_DIR']=git('rev-parse','--absolute-git-dir').decode().strip();env['GIT_WORK_TREE']=str(t)
 r=subprocess.run([sys.executable,'-B',str(build)],cwd=t,env=env,capture_output=True,text=True);assert r.returncode==0,r.stderr
 actual=(t/N/'minimum.json').read_bytes();expected=(ROOT/N/'minimum.json').read_bytes();assert actual==expected
 authority=dict(builder_source='build_minimum.py uses only fixed Git blobs, explicit FAMILY/COMMON rules; never current --package',builder_exit=0,minimum_sha256=hashlib.sha256(actual).hexdigest(),exact_reproduction=True,payload_writes=False)
 # Copy all selected tracked files with materialized LFS bytes; no .git or .venv.
 for name in git('ls-files').decode().splitlines():
  dest=t/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
 probe=t/'verification/r5_cycle_interfaces_recheck/independent_probe.py'
 before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'verification/r5_cycle_interfaces_recheck').rglob('*') if p.is_file()}
 r=subprocess.run([sys.executable,'-B',str(probe)],cwd=t,env=env,capture_output=True,text=True);assert r.returncode==0,r.stderr
 data=json.loads(r.stdout);assert data['total_checks']==654 and data['passed']==654 and not data['failed'] and data['historical_17_corrected']==17
 (HERE/'prior_probe_new_inputs.json').write_text(r.stdout)
 after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'verification/r5_cycle_interfaces_recheck').rglob('*') if p.is_file()};assert before==after
 authority.update(prior_probe_source_sha256=hashlib.sha256(probe.read_bytes()).hexdigest(),prior_probe_exit=r.returncode,prior_probe_counts=[654,654,0],note='reviewed_C=144941c in raw stdout is hardcoded in unchanged probe; actual inputs are copied bd7ce8a/H0e5197, identified by this capture and preservation manifest',original_review_tree_unchanged=True)
 (HERE/'authority.json').write_text(json.dumps(authority,indent=2)+'\n')
print('Minimum reproduced exactly; unchanged prior probe 654/654 on new input copy, original review evidence preserved.')
