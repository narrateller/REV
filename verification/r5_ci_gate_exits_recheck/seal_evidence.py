"""Seal/check all review evidence bytes, excluding this self-referential manifest."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent
files={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.rglob('*')) if p.is_file() and p.name!='evidence_manifest.json' and '__pycache__' not in p.parts}
if '--check' in sys.argv:
 d=json.loads((H/'evidence_manifest.json').read_text());assert d['files_sha256']==files;print('Review evidence SHA256 manifest MATCH:',len(files),'files')
else:
 d=dict(reviewed_C='3060dbf561f95e4384fbfd13a9cc5569690515e5',handoff_H='98861219f0adda96af0aca0a3a35078aec022eb9',R1='60eeddce71c9440a2fa08f7acbe6f1121c974b29',session_id='r5-ci-gate-exits-20261113',files_sha256=files,self_excluded='evidence_manifest.json')
 (H/'evidence_manifest.json').write_text(json.dumps(d,indent=2)+'\n');print('Sealed',len(files),'review evidence files')
