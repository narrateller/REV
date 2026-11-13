"""Isolated author replay; keep all historical R5 scripts and source pins intact."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
MINIMAL_READER='''
from pathlib import Path
import copy,json,sys
root=Path.cwd();sys.path.insert(0,str(root/'verification/r5_ci_snapshots_recheck'))
from fixtures import C,L
sys.path.insert(0,str(root/'verification/r4_cycle_interfaces/proposal'))
import semantic_minimum as S
h=root/'verification/r5_ci_raw_sources_recheck';old=json.loads((h/'minimal_guard_tag_witness.json').read_text());rows=[]
for r in old['cases']:
 x=copy.deepcopy(r['context']);p=copy.deepcopy(r['proof']);before=L.digest([x,p]);assert before==r['input_sha256']
 a=S.recovery_assessment(p,x,C);assert before==L.digest([x,p])
 expected='ALLOWED_ASSUMED' if r['id']=='known-FEED' else 'INDETERMINATE'
 scoped='TRUE' if r['id']=='known-FEED' else 'UNKNOWN'
 rows.append(dict(id=r['id'],expected_gate=expected,actual_gate=a['action_gate'],expected_scoped=scoped,actual_scoped=a['recovery_value'],matched=a['action_gate']==expected and a['recovery_value']==scoped,input_sha256=before,caller_proof_unchanged=True,assessment=a))
(h/'minimal_guard_tag_witness.json').write_text(json.dumps(dict(role='AUTHOR_REPLAY_CURRENT_SOURCE',cases=rows,matches=sum(r['matched'] for r in rows)),indent=2)+'\\n')
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');parser.add_argument('--prior',action='store_true');parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);tag='baseline' if args.baseline else 'corrected'
    with tempfile.TemporaryDirectory(prefix='rev-open-journal-') as tmp:
        clone=Path(tmp)/'repo';shutil.copytree(ROOT,clone,ignore=shutil.ignore_patterns('.git','.venv','scratch','__pycache__','.pytest_cache'));(clone/'.git').symlink_to(ROOT/'.git',target_is_directory=True)
        folder=clone/'verification/r5_ci_raw_sources_recheck'
        commands=[[sys.executable,'-B',str(folder/'independent_probe.py')],
                  [sys.executable,'-B',str(folder/'reproduce_guard_tag.py')] if args.baseline else [sys.executable,'-B','-c',MINIMAL_READER]]
        for i,cmd in enumerate(commands):
            r=subprocess.run(cmd,cwd=clone,text=True,capture_output=True);(out/(tag+'_'+str(i)+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
        matrix=json.loads((folder/'independent_results.json').read_text());minimal=json.loads((folder/'minimal_guard_tag_witness.json').read_text())
        assert matrix['count']==732 and matrix['matches']==(696 if args.baseline else 732)
        assert minimal['matches']==(2 if args.baseline else 3)
        for src,dst in [('independent_results.json','matrix'),('minimal_guard_tag_witness.json','minimal')]:shutil.copyfile(folder/src,out/(tag+'_'+dst+'.json'))
        if args.prior:
            r=subprocess.run([sys.executable,'-B',str(folder/'repeat_prior.py')],cwd=clone,text=True,capture_output=True);(out/'prior.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
            for name in ['authority_and_prior.json','prior_295_new_inputs.json','prior_231_new_inputs.json','nineteen.json','eight_variations.json']:
                if (folder/name).exists():shutil.copyfile(folder/name,out/('replayed_'+name))
        capture=dict(role='AUTHOR_REPLAY_NOT_INDEPENDENT_RECHECK',mode=tag,source_sha256={name:hashlib.sha256((clone/'verification/r4_cycle_interfaces/proposal'/name).read_bytes()).hexdigest() for name in ['recovery_snapshots.py','semantic_minimum.py','metadata_types.py']+([] if args.baseline else ['journal_admission.py'])},historical_identity='Raw R5 matrix retains old C/session constants; hashes identify this actual source',cases=732,matches=matrix['matches'],failed_ids=[r['id'] for r in matrix['failed']],minimal_matches=minimal['matches'],original_R5_evidence='UNCHANGED')
        (out/(tag+'_capture.json')).write_text(json.dumps(capture,indent=2)+'\n');print(json.dumps(capture,indent=2))


if __name__=='__main__':main()
