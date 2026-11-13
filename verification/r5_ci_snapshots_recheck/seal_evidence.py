"""Seal/check all review evidence bytes, excluding this self-referential manifest."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent
files={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.rglob('*')) if p.is_file() and p.name!='evidence_manifest.json' and '__pycache__' not in p.parts}
if '--check' in sys.argv:
 d=json.loads((H/'evidence_manifest.json').read_text());assert d['files_sha256']==files;print('Review evidence SHA256 manifest MATCH:',len(files),'files')
else:
 d=dict(reviewed_C='e30b4b7caf3040905cc23c79ca696af2871c958a',handoff_H='ff050572f88f108c2092827e98cd4d98bd874737',R1='39826eb2f5dbd1f83d81882022e6f59313ebe5d5',session_id='r5-ci-snapshots-20261113',files_sha256=files,self_excluded='evidence_manifest.json')
 (H/'evidence_manifest.json').write_text(json.dumps(d,indent=2)+'\n');print('Sealed',len(files),'review evidence files')
