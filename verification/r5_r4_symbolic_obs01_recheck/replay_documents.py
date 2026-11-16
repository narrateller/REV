"""Supplemental deterministic document replay and author negative control.

No numerical/physical evaluation. Historical author inputs are never overwritten.
"""
from pathlib import Path
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
NEW='beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe'
OLD='b840dfd5444da2bf62483b7f4a6069d2bb255b71'
PKG='verification/r4_force_geometry/symbolic_20261116/'
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main(output,artifacts_dir=None):
    if output.exists():raise SystemExit('fresh output required')
    artifacts_dir=HERE if artifacts_dir is None else artifacts_dir
    artifacts_dir.mkdir(parents=True,exist_ok=True)
    names=git('ls-tree','-r','--name-only',NEW,'verification/r4_force_geometry').decode().splitlines()
    before={p:sha((ROOT/p).read_bytes()) for p in names}
    renderer=module('exact_corrected_renderer',ROOT/(PKG+'render_tables.py'))
    matches=[]
    with tempfile.TemporaryDirectory(prefix='r5-obs01-render-') as tmp:
        renderer.HERE=Path(tmp);renderer.main()
        for file in sorted(Path(tmp).iterdir()):
            assert file.read_bytes()==git('show',NEW+':'+PKG+file.name)
            matches.append(dict(file=file.name,result='MATCH',sha256=sha(file.read_bytes())))
    assert len(matches)==7
    positive=artifacts_dir/'author_positive.json'
    if positive.exists():raise SystemExit('fresh author positive output required')
    command=[sys.executable,str(ROOT/(PKG+'verify_symbolic.py')),'--output',str(positive)]
    result=subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
    (artifacts_dir/'author_positive.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0
    assert json.loads(positive.read_text())['counts']=={'PASS':1341}
    negative=artifacts_dir/'author_negative_old.json'
    if negative.exists():raise SystemExit('fresh author negative output required')
    verifier=module('corrected_verifier_on_old_tables',ROOT/(PKG+'verify_symbolic.py'))
    with tempfile.TemporaryDirectory(prefix='r5-obs01-negative-') as tmp:
        verifier.HERE=Path(tmp)
        for item in matches:
            name=item['file'];(Path(tmp)/name).write_bytes(git('show',OLD+':'+PKG+name))
        (Path(tmp)/'verify_symbolic.py').write_bytes((ROOT/(PKG+'verify_symbolic.py')).read_bytes())
        saved=sys.argv;stream=io.StringIO()
        try:
            sys.argv=['verify_symbolic.py','--output',str(negative)]
            with contextlib.redirect_stdout(stream):code=verifier.main()
        finally:sys.argv=saved
    (artifacts_dir/'author_negative_old.log').write_text(stream.getvalue())
    counts=json.loads(negative.read_text())['counts']
    assert code==1 and counts=={'PASS':1337,'FAIL':8}
    after={p:sha((ROOT/p).read_bytes()) for p in names}
    assert after==before
    output.write_text(json.dumps(dict(target_C=NEW,renderer_matches=matches,
         author_positive={'command':command,'exit_code':result.returncode,'counts':{'PASS':1341}},
         author_negative={'method':'corrected verifier main with HERE redirected to immutable old tables; session environment unchanged',
                          'exit_code':code,'counts':counts,'expected_failure':True},
         unchanged_author_files=after,physics_numerical_calculations='NOT_RUN',author_only_preflight='NOT_RUN'),indent=2)+'\n')
    print('MATCH 7 rendered documents; positive 1341 PASS; old negative 1337 PASS/8 FAIL (expected); author files unchanged')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    p.add_argument('--artifacts-dir',type=Path,help='fresh directory for supplemental author evidence')
    args=p.parse_args();main(args.output,args.artifacts_dir)
