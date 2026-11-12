"""Release catalog and hash verification. Only explicit generation writes.

Dependency order: sources -> build/evidence reports -> generation record ->
publication manifest -> verifier stdout. No verifier report is in this DAG.
"""
import hashlib,json
from pathlib import Path

FOLDERS=('cad/frame_mount','cad/build/frame_mount','verification/r4_frame_mount')
MANIFEST='cad/build/frame_mount/publication_manifest.json'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def catalog(root):
    root=Path(root)
    return {p.relative_to(root).as_posix():p for folder in FOLDERS for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.relative_to(root).as_posix()!=MANIFEST}


def write_manifest(root):
    """Explicit generator only; verification must never call this function."""
    root=Path(root);files=catalog(root)
    payload={'schema_version':2,'scope':'saved sources, inputs, CAD and evidence; this manifest excluded; verifier emits stdout only','sha256':{p:digest(path) for p,path in sorted(files.items())}}
    (root/MANIFEST).write_text(json.dumps(payload,indent=2)+'\n')
    return payload


def verify_manifest(root):
    root=Path(root);payload=json.loads((root/MANIFEST).read_text())
    if payload.get('schema_version')!=2:raise ValueError('publication manifest schema missing/stale; explicit generation required')
    recorded=payload['sha256'];actual=catalog(root)
    if set(recorded)!=set(actual):raise ValueError('publication catalog mismatch: missing='+str(sorted(set(recorded)-set(actual)))+'; unrecorded='+str(sorted(set(actual)-set(recorded))))
    for name,path in sorted(actual.items()):
        if digest(path)!=recorded[name]:raise ValueError('publication hash mismatch: '+name)
    return {'status':'PASS','files_checked':len(actual)}
