"""Author replay in an isolated copy; original R5 evidence is never overwritten.

--baseline is for the unchanged e30b4b7 implementation. The R5 minimal runner
pins that source, so corrected replay evaluates its immutable JSON inputs with
a separate reader instead of weakening the historical runner's source check.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
MINIMAL_READER = '''
from pathlib import Path
import copy,importlib.util,json,sys
root=Path.cwd();p=root/'verification/r4_cycle_interfaces/proposal';sys.path.insert(0,str(p))
import semantic_minimum as S
c=json.loads((root/'verification/r4_cycle_contract/contract.json').read_text())
spec=importlib.util.spec_from_file_location('replay_frozen',root/'verification/r4_cycle_contract/permission_examples.py')
l=importlib.util.module_from_spec(spec);spec.loader.exec_module(l)
h=root/'verification/r5_ci_snapshots_recheck';data=json.loads((h/'minimal_witnesses.json').read_text());rows=[]
for r in data['witnesses']:
 x=copy.deepcopy(r['context']);proof=copy.deepcopy(r['proof']);before=l.digest([x,proof])
 a=S.recovery_assessment(proof,x,c)
 _,legacy=l.recover(c,'RESTORE_B_CLOSURE',x,proof.get('fault_id') if type(proof) is dict else None,proof)
 assert before==l.digest([x,proof]) and legacy=='BLOCKED'
 rows.append(dict(id=r['id'],assessment=a,frozen_gate=legacy,original_unchanged=True,matched=a['action_gate']=='BLOCKED' and a['recovery_value']=='UNKNOWN'))
(h/'minimal_replay.json').write_text(json.dumps(dict(cases=rows,matched=sum(r['matched'] for r in rows),role='AUTHOR_REPLAY_CURRENT_SOURCE'),indent=2)+'\\n')
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--prior', action='store_true', help='Also replay the retained 654/765/7 probes in the isolated copy')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve();out.mkdir(parents=True, exist_ok=True)
    tag = 'baseline' if args.baseline else 'corrected'
    with tempfile.TemporaryDirectory(prefix='rev-gate-replay-') as temp:
        clone = Path(temp)/'repo'
        shutil.copytree(ROOT, clone, ignore=shutil.ignore_patterns('.git', '.venv', 'scratch', '__pycache__', '.pytest_cache'))
        (clone/'.git').symlink_to(ROOT/'.git', target_is_directory=True)
        folder = clone/'verification/r5_ci_snapshots_recheck'
        commands = [[sys.executable, '-B', str(folder/'independent_probe.py')],
                    [sys.executable, '-B', str(folder/'reproduce_blocked.py')] if args.baseline
                    else [sys.executable, '-B', '-c', MINIMAL_READER]]
        for number, command in enumerate(commands):
            run = subprocess.run(command, cwd=clone, text=True, capture_output=True)
            (out/(tag+'_'+str(number)+'.log')).write_text(run.stdout+run.stderr)
            assert run.returncode == 0, run.stderr
        matrix = json.loads((folder/'independent_results.json').read_text())
        minimal = json.loads((folder/'minimal_replay.json').read_text())
        assert matrix['count'] == 295 and matrix['matches'] == (276 if args.baseline else 295)
        assert minimal['matched'] == (0 if args.baseline else 2)
        for source, dest in [('independent_results.json', 'matrix'), ('minimal_replay.json', 'minimal')]:
            shutil.copyfile(folder/source, out/(tag+'_'+dest+'.json'))
        if args.prior:
            run = subprocess.run([sys.executable, '-B', str(folder/'repeat_prior.py')], cwd=clone, text=True, capture_output=True)
            (out/'prior.log').write_text(run.stdout+run.stderr)
            assert run.returncode == 0, run.stderr
            for name in ['authority_and_prior.json', 'r5_cycle_interfaces_recheck_new_inputs.json',
                         'r5_ci_semantic_minimum_recheck_new_inputs.json', 'prior_incomplete_new_inputs.json']:
                shutil.copyfile(folder/name, out/('replayed_'+name))
        source_hashes = {name:hashlib.sha256((clone/'verification/r4_cycle_interfaces/proposal'/name).read_bytes()).hexdigest()
                         for name in ['recovery_snapshots.py', 'semantic_minimum.py', 'metadata_types.py']}
        capture = dict(role='AUTHOR_REPLAY_NOT_INDEPENDENT_RECHECK', mode=tag, source_sha256=source_hashes,
                       historical_R5_identity='Unchanged matrix output contains historical C/session constants',
                       matrix_cases=295, matrix_matches=matrix['matches'], failed_ids=[r['id'] for r in matrix['failed']],
                       minimal_cases=2, minimal_matches=minimal['matched'], original_R5_evidence='UNCHANGED')
        (out/(tag+'_capture.json')).write_text(json.dumps(capture, indent=2)+'\n')
        print(json.dumps(capture, indent=2))


if __name__ == '__main__': main()
