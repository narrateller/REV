"""Independent run of candidate assertions in disposable exact-C materialization."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,time,os
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
C='8b72716021b0c3a64972033d09fe5e80945eb98e'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 with tempfile.TemporaryDirectory(prefix='r5-open-journal-') as tmp:
  t=Path(tmp)/'repo';t.mkdir()
  archive=subprocess.run(['git','archive',C],cwd=ROOT,capture_output=True,check=True)
  subprocess.run(['tar','-x','-C',str(t)],input=archive.stdout,check=True)
  (t/'.git').symlink_to(ROOT/'.git',target_is_directory=True)
  env=os.environ.copy();env['GIT_INDEX_FILE']=str(Path(tmp)/'exact-C.index')
  subprocess.run(['git','read-tree',C],cwd=ROOT,env=env,check=True)
  tracked=subprocess.check_output(['git','ls-files','-z'],cwd=t,env=env).split(b'\0')[:-1]
  assert all((t/os.fsdecode(name)).is_file() for name in tracked)
  if '--verify-materialization' in sys.argv:
   print('Exact-C materialization and isolated index:',len(tracked),'files');return
  commands=json.loads((OUT/'commands.json').read_text())['commands'] if '--retry-failed' in sys.argv else []
  def run(label,args):
   start=time.time();r=subprocess.run([sys.executable,'-B',*args],cwd=t,env=env,capture_output=True,text=True)
   (OUT/(label+'.stdout')).write_text(r.stdout);(OUT/(label+'.stderr')).write_text(r.stderr)
   commands.append(dict(label=label,argv=args,cwd='DISPOSABLE_EXACT_C',exit_code=r.returncode,seconds=round(time.time()-start,3),stdout_sha256=sha(OUT/(label+'.stdout')),stderr_sha256=sha(OUT/(label+'.stderr'))))
   (OUT/'commands.json').write_text(json.dumps(dict(reviewed_C=C,materialized_git_index=C,commands=commands),indent=2)+'\n')
   print(label,r.returncode,flush=True)
   return r
  for name in ([] if '--retry-failed' in sys.argv else ['journal_correction','raw_correction','gate_correction','snapshot_correction','type_correction','semantic_iteration','correction']):
   run(name,['-m','unittest','discover','-s','verification/r4_cycle_interfaces/'+name,'-p','test_*.py','-v'])
  if '--retry-failed' in sys.argv:
   for item in list(commands):
    if item['exit_code']:run(item['label']+'_retry',item['argv'])
  if '--retry-failed' not in sys.argv:run('package',['verification/r4_cycle_interfaces/proposal/check_package.py'])
  if '--retry-failed' not in sys.argv:run('exports',['verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py'])
  if '--retry-failed' not in sys.argv:run('replay',['verification/r4_cycle_interfaces/journal_correction/replay_r5.py','--prior','--output-dir',str(OUT/'replay')])
  old=json.loads((t/'verification/r5_ci_raw_sources_recheck/independent_results.json').read_text())
  new=json.loads((OUT/'replay/corrected_matrix.json').read_text()); idx={r['id']:r for r in new['cases']};rows=[]
  for r in old['failed']:
   n=idx[r['id']];assert n['input_sha256_before']==r['input_sha256_before'] and n['ordered_input_sha256']==r['ordered_input_sha256']
   rows.append(dict(id=r['id'],typed_input_sha256=n['input_sha256_before'],ordered_input_sha256=n['ordered_input_sha256'],old_gate=r['assessment']['action_gate'],new_gate=n['assessment']['action_gate'],new_recovery=n['assessment']['recovery_value'],admission=n['assessment']['journal_admission']['value'],matched=n['matched']))
  assert len(rows)==36 and all(r['matched'] and r['new_gate']=='INDETERMINATE' and r['new_recovery']=='UNKNOWN' and r['admission']=='UNKNOWN' for r in rows)
  (OUT/'thirtysix.json').write_text(json.dumps(dict(reviewed_C=C,count=len(rows),ordered_inputs=len({r['ordered_input_sha256'] for r in rows}),canonical_inputs=len({r['typed_input_sha256'] for r in rows}),cases=rows),indent=2)+'\n')
  assert all(r['exit_code']==0 or any(n['label']==r['label']+'_retry' and n['exit_code']==0 for n in commands) for r in commands)
if __name__=='__main__':main()
