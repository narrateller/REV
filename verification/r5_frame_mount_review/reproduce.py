"""Run declared commands in the isolated materialized checkout; retain all exits."""
import json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);output=Path(sys.argv[2]);output.mkdir(parents=True,exist_ok=True);records=[]
commands=[['/usr/bin/python3','-m','unittest','discover','-s',d,'-p','test_*.py'] for d in ('cad/layout','models/rev_linked_scene','models/kinematic_press','cad/layout_correction','cad/frame_mount')]
commands += [['/usr/bin/python3','cad/frame_mount/'+p+'.py'] for p in ('run','geometry_evidence','figures','report','verify_output')]
for i,c in enumerate(commands):
 p=subprocess.run(c,cwd=root,text=True,capture_output=True)
 (output/('%02d.log'%i)).write_text(p.stdout+'\nSTDERR:\n'+p.stderr)
 records.append({'command':c,'cwd':str(root),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 (output/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(i,c,p.returncode,flush=True)
 if p.returncode:break
sys.exit(any(r['exit_code'] for r in records))
