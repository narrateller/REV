"""Replay the already-read documentary builder in temporary HERE, never in R1.

No R1-only verifier or identity spoofing. No machine-model evaluation.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
REL='verification/r1_force_inputs_intake/'
C='f2cbd96bb78c915dca74cb4eb29daffbb52ee172'
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def sha(b):return hashlib.sha256(b).hexdigest()
def main(output):
    if output.exists():raise SystemExit('fresh output required')
    script=ROOT/(REL+'build_packet.py')
    assert script.read_bytes()==git('show',C+':'+REL+'build_packet.py')
    spec=importlib.util.spec_from_file_location('reviewed_documentary_builder',script)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    names=git('ls-tree','-r','--name-only',C,REL).decode().splitlines()
    before={p:sha((ROOT/p).read_bytes()) for p in names};files=[]
    with tempfile.TemporaryDirectory(prefix='r5-ref-builder-') as tmp:
        m.HERE=Path(tmp);m.main()
        for file in sorted(Path(tmp).rglob('*')):
            if not file.is_file():continue
            name=file.relative_to(tmp).as_posix();expected=git('show',C+':'+REL+name)
            assert file.read_bytes()==expected,name
            files.append(dict(path=name,result='MATCH',sha256=sha(expected)))
    assert len(files)==8
    after={p:sha((ROOT/p).read_bytes()) for p in names};assert after==before
    output.write_text(json.dumps(dict(target_C=C,files=files,author_files_unchanged=after,
                      method='Temporary HERE; source transcription and unit formatting only',
                      author_only_verifier='NOT_RUN',session_impersonation=False,engineering_models='NOT_RUN'),indent=2)+'\n')
    print('MATCH 8 documentary files;',len(after),'R1 files unchanged')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);main(p.parse_args().output)
