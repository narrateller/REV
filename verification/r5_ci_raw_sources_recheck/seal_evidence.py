"""Seal/check all review evidence bytes, excluding this self-referential manifest."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent
files={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.rglob('*')) if p.is_file() and p.name!='evidence_manifest.json' and '__pycache__' not in p.parts}
if '--check' in sys.argv:
 d=json.loads((H/'evidence_manifest.json').read_text());assert d['files_sha256']==files;print('Review evidence SHA256 manifest MATCH:',len(files),'files')
else:
 d=dict(reviewed_C='b89854ad709bcb5c2991376bed41bf2f73acef82',handoff_H='ce1ad73aae7a5700203103c14290375cc519662b',R1='3aa5ee100f57aa75315d429afef38f8a982b1afc',session_id='r5-ci-raw-sources-20261113',files_sha256=files,self_excluded='evidence_manifest.json')
 (H/'evidence_manifest.json').write_text(json.dumps(d,indent=2)+'\n');print('Sealed',len(files),'review evidence files')
