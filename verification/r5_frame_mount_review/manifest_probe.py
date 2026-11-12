"""Reproduce verifier self-invalidation after a build over published outputs.
The copy has been rebuilt by README commands. Restore only the exact previous
publication manifest captured by that build, then verify twice. No code, CAD,
geometry input or run.json is modified.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
source=Path(sys.argv[1]).resolve();root=Path(sys.argv[2]).resolve();dest=Path(sys.argv[3]);out=root/'cad/build/frame_mount';manifest=out/'publication_manifest.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run=json.loads((out/'run.json').read_text());original=source/'cad/build/frame_mount/publication_manifest.json';expected=run['artifacts']['publication_manifest.json'];assert sha(original)==expected
# Exact state immediately before first successful verifier in the replay.
manifest.write_bytes(original.read_bytes())
paths=[root/'cad/frame_mount/verify_output.py',out/'run.json']+[p for v in 'AB' for p in (out/v).iterdir() if p.suffix in ('.FCStd','.step','.png')]
before={str(p.relative_to(root)):sha(p) for p in paths};records=[]
for _ in range(2):
 p=subprocess.run(['/usr/bin/python3','cad/frame_mount/verify_output.py'],cwd=root,text=True,capture_output=True)
 records.append({'command':p.args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'final_checks':json.loads((root/'verification/r4_frame_mount/final_checks.json').read_text()),'manifest_sha256':sha(manifest)})
after={str(p.relative_to(root)):sha(p) for p in paths}
r={'expected_manifest_in_run':expected,'restored_manifest_source':str(original),'code_and_CAD_hashes_before':before,'code_and_CAD_hashes_after':after,'commands':records,'observed_self_invalidation':records[0]['exit_code']==0 and records[1]['exit_code']==1 and "('artifact', 'publication_manifest.json')" in records[1]['stderr'] and before==after}
dest.write_text(json.dumps(r,indent=2)+'\n');print('self invalidation reproduced:',r['observed_self_invalidation']);sys.exit(not r['observed_self_invalidation'])
