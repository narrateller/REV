"""Seal/check all review evidence bytes, excluding this self-referential manifest."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent
files={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.rglob('*')) if p.is_file() and p.name!='evidence_manifest.json' and '__pycache__' not in p.parts}
if '--check' in sys.argv:
 d=json.loads((H/'evidence_manifest.json').read_text());assert d['files_sha256']==files;print('Review evidence SHA256 manifest MATCH:',len(files),'files')
else:
 d=dict(reviewed_C='fa0626372c03d11655624bb454458f82c30117f7',handoff_H='ab0fb1900a2bbdfa81e284112b318320f3c5b480',R1='e0fea7bbf3bd32fda601bca2f7567f8e2c3342b3',session_id='r5-ci-strict-types-20261113',files_sha256=files,self_excluded='evidence_manifest.json')
 (H/'evidence_manifest.json').write_text(json.dumps(d,indent=2)+'\n');print('Sealed',len(files),'review evidence files')
