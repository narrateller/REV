"""Replay R5 in isolation; baseline runner keeps its original source pin."""
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
import copy,json,sys
root=Path.cwd();sys.path.insert(0,str(root/'verification/r5_ci_snapshots_recheck'))
from fixtures import C,L
sys.path.insert(0,str(root/'verification/r4_cycle_interfaces/proposal'))
import semantic_minimum as S
h=root/'verification/r5_ci_gate_exits_recheck';old=json.loads((h/'minimal_journal_witness.json').read_text())
x=copy.deepcopy(old['context']);p=copy.deepcopy(old['proof']);before=L.digest([x,p])
raw,reason=L._raw_value(C,'RESTORE_B_CLOSURE','RESOURCES_READY',x,x['evidence']['RESOURCES_READY'],'ENTRY')
assert raw=='FALSE' and reason=='CURRENT_ASSUMED_RECORD' and before==old['input_sha256']
a=S.recovery_assessment(p,x,C);assert before==L.digest([x,p])
result=dict(role='AUTHOR_REPLAY_CURRENT_SOURCE',expected_action_gate='BLOCKED',actual_action_gate=a['action_gate'],scoped=a['recovery_value'],matched=a['action_gate']=='BLOCKED' and a['recovery_value']=='UNKNOWN',independent_frozen_raw_value=raw,independent_frozen_raw_reason=reason,input_sha256=before,caller_proof_unchanged=True,assessment=a)
(h/'minimal_journal_witness.json').write_text(json.dumps(result,indent=2)+'\\n')
'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--prior',action='store_true')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    tag='baseline' if args.baseline else 'corrected'
    with tempfile.TemporaryDirectory(prefix='rev-raw-replay-') as temp:
        clone=Path(temp)/'repo'
        shutil.copytree(ROOT,clone,ignore=shutil.ignore_patterns('.git','.venv','scratch','__pycache__','.pytest_cache'))
        (clone/'.git').symlink_to(ROOT/'.git',target_is_directory=True)
        folder=clone/'verification/r5_ci_gate_exits_recheck'
        commands=[[sys.executable,'-B',str(folder/'independent_probe.py')],
                  [sys.executable,'-B',str(folder/'reproduce_journal.py')] if args.baseline
                  else [sys.executable,'-B','-c',MINIMAL_READER]]
        for i,command in enumerate(commands):
            r=subprocess.run(command,cwd=clone,text=True,capture_output=True)
            (out/(tag+'_'+str(i)+'.log')).write_text(r.stdout+r.stderr)
            assert r.returncode==0,r.stderr
        matrix=json.loads((folder/'independent_results.json').read_text())
        minimal=json.loads((folder/'minimal_journal_witness.json').read_text())
        assert matrix['count']==231 and matrix['matches']==(223 if args.baseline else 231)
        assert minimal['matched'] is (not args.baseline)
        for src,dst in [('independent_results.json','matrix'),('minimal_journal_witness.json','minimal')]:
            shutil.copyfile(folder/src,out/(tag+'_'+dst+'.json'))
        if args.prior:
            r=subprocess.run([sys.executable,'-B',str(folder/'repeat_prior.py')],cwd=clone,text=True,capture_output=True)
            (out/'prior.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
            for name in ['authority_and_prior.json','prior_295_new_inputs.json','nineteen.json','minimal_pair_replay.json']:
                if (folder/name).exists():shutil.copyfile(folder/name,out/('replayed_'+name))
        capture=dict(role='AUTHOR_REPLAY_NOT_INDEPENDENT_RECHECK',mode=tag,
                     source_sha256={name:hashlib.sha256((clone/'verification/r4_cycle_interfaces/proposal'/name).read_bytes()).hexdigest() for name in ['recovery_snapshots.py','semantic_minimum.py','metadata_types.py']},
                     historical_R5_identity='Unchanged raw matrix retains original C/session literals; source hashes identify this replay',
                     cases=231,matches=matrix['matches'],failed_ids=[r['id'] for r in matrix['failed']],
                     minimal_matches=int(minimal['matched']),original_R5_evidence='UNCHANGED')
        (out/(tag+'_capture.json')).write_text(json.dumps(capture,indent=2)+'\n');print(json.dumps(capture,indent=2))


if __name__=='__main__':main()
