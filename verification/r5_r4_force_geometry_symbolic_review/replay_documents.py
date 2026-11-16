"""Read-only documentary replay; never runs an engineering solver/preflight.

Renderer HERE is redirected to a fresh temporary directory on each call.
Only this review's output is saved; author evidence is never overwritten.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
PKG='verification/r4_force_geometry/symbolic_20261116/'
C='b840dfd5444da2bf62483b7f4a6069d2bb255b71'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def main(output):
    if output.exists():raise SystemExit('fresh output required')
    before={p:sha((ROOT/p).read_bytes()) for p in git('ls-tree','-r','--name-only',C,PKG).decode().splitlines()}
    script=ROOT/(PKG+'render_tables.py')
    assert script.read_bytes()==git('show',C+':'+PKG+'render_tables.py')
    spec=importlib.util.spec_from_file_location('reviewed_document_renderer',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    comparisons=[]
    for attempt in (1,2):
        with tempfile.TemporaryDirectory(prefix='r5-symbolic-docs-') as tmp:
            module.HERE=Path(tmp)
            module.main()
            for p in sorted(Path(tmp).iterdir()):
                expected=git('show',C+':'+PKG+p.name)
                assert p.read_bytes()==expected,p.name
                comparisons.append(dict(attempt=attempt,file=p.name,sha256=sha(expected),result='MATCH'))
    assert len(comparisons)==14
    after={p:sha((ROOT/p).read_bytes()) for p in before}
    assert after==before,'author evidence changed'
    output.write_text(json.dumps(dict(target_C=C,method='exact renderer with HERE redirected twice; byte comparison to immutable C',
       comparisons=comparisons,author_file_hashes=after,unchanged_author_files=len(after),
       engineering_calculations='NOT_RUN',R4_preflight='NOT_RUN',session_impersonation=False),indent=2)+'\n')
    print('MATCH 7 documentary artifacts twice; author files unchanged:',len(after))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);main(p.parse_args().output)
