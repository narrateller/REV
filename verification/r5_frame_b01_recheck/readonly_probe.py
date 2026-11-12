"""Two saved-package checks, including all repository file bytes/mtime/size.
Output must be outside the checked root to avoid harness writes in snapshots.
"""
import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]).resolve();assert not dest.is_relative_to(R)
def snapshot():
 return {str(p.relative_to(R)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in R.rglob('*') if p.is_file() and not {'.git','.venv','__pycache__'}&set(p.parts)}
before=snapshot();prev=before;runs=[]
for _ in range(2):
 p=subprocess.run(['/usr/bin/python3','-B','cad/frame_mount/verify_output.py'],cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True);after=snapshot();delta={k:{'before':prev.get(k),'after':after.get(k)} for k in set(prev)|set(after) if prev.get(k)!=after.get(k)}
 runs.append({'command':p.args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'file_changes':delta});prev=after
r={'snapshot_file_count':len(before),'snapshot_before':before,'snapshot_after':prev,'runs':runs,'same_result':all(runs[0][k]==runs[1][k] for k in ('exit_code','stdout','stderr')),'unchanged':prev==before and all(not x['file_changes'] for x in runs)};dest.write_text(json.dumps(r,indent=2)+'\n');print(r['snapshot_file_count'],r['same_result'],r['unchanged'],[x['exit_code'] for x in runs]);sys.exit(not(r['same_result'] and r['unchanged'] and all(x['exit_code']==0 for x in runs)))
