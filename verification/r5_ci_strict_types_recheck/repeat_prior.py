"""Re-execute prior independent probes using new inputs in isolated tracked copies."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
N='verification/r4_cycle_interfaces/semantics_v1'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def hashes(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
original={p:hashes(ROOT/p) for p in ['verification/r5_cycle_interfaces_recheck','verification/r5_ci_semantic_minimum_recheck']}
with tempfile.TemporaryDirectory(prefix='r5-types-prior-') as tmp:
 t=Path(tmp);env=os.environ.copy();env.update(GIT_DIR=git('rev-parse','--absolute-git-dir').decode().strip(),GIT_WORK_TREE=str(t))
 for name in git('ls-files').decode().splitlines():
  dest=t/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
 build=t/N/'build_minimum.py';r=subprocess.run([sys.executable,'-B',str(build)],cwd=t,env=env,capture_output=True,text=True)
 assert r.returncode==0,r.stderr
 assert (t/N/'minimum.json').read_bytes()==(ROOT/N/'minimum.json').read_bytes()
 results=[]
 for name,expected in [('r5_cycle_interfaces_recheck',654),('r5_ci_semantic_minimum_recheck',765)]:
  probe=t/'verification'/name/'independent_probe.py'
  r=subprocess.run([sys.executable,'-B',str(probe)],cwd=t,env=env,capture_output=True,text=True)
  assert r.returncode==0,r.stderr
  d=json.loads(r.stdout);assert d['total_checks']==expected and not d['failed'],d['failed']
  count=d.get('passed',d.get('matches'));assert count==expected
  (HERE/(name+'_new_inputs.json')).write_text(r.stdout)
  results.append(dict(script=str(probe.relative_to(t)),source_sha256=hashlib.sha256(probe.read_bytes()).hexdigest(),checks=expected,matches=count,exit_code=r.returncode))
  if name=='r5_ci_semantic_minimum_recheck':
   shutil.copytree(probe.parent/'mutations',HERE/'prior_minimum_mutations',dirs_exist_ok=True)
 assert original=={p:hashes(ROOT/p) for p in original}
 (HERE/'authority_and_prior.json').write_text(json.dumps(dict(actual_C='fa0626372c03d11655624bb454458f82c30117f7',minimum_reproduced=True,minimum_sha256=hashlib.sha256((ROOT/N/'minimum.json').read_bytes()).hexdigest(),prior_probes=results,original_reviews_unchanged=True,note='Raw probes retain their historical hardcoded reviewed_C labels; actual new inputs are this C, materialized in temp, with no reuse.'),indent=2)+'\n')
print('minimum reproduced; prior 654/654 and 765/765; original evidence unchanged')
