import os,shutil,subprocess,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];dest=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='rev-fp-before-') as tmp:
 root=Path(tmp)/'REV';subprocess.run(['git','clone','--shared','--no-checkout',str(ROOT),str(root)],check=True,capture_output=True);subprocess.run(['git','checkout','2592b470940cea886e033a999c889c15a92889f6'],cwd=root,env={**os.environ,'GIT_LFS_SKIP_SMUDGE':'1'},check=True,capture_output=True);subprocess.run(['git','lfs','install','--local'],cwd=root,check=True,capture_output=True)
 for name in subprocess.check_output(['git','lfs','ls-files','-n'],cwd=ROOT,text=True).splitlines():shutil.copy2(ROOT/name,root/name)
 cmd=['/usr/bin/python3','-B',str(ROOT/'verification/r5_feed_power_review/service_counterexamples.py'),str(root),str(dest/'before_counterexamples.json')];p=subprocess.run(cmd,cwd=root,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});(dest/'before.log').write_text(p.stdout+'\nSTDERR:\n'+p.stderr);r=json.loads((dest/'before_counterexamples.json').read_text());assert p.returncode==0 and len(r['cases'])==5 and all(c['defect_reproduced'] for c in r['cases']);print('All five original R5 false PASS outcomes reproduced; geometry/input unchanged')
