"""Minimal independent current-FALSE witness; no injection or source mutation."""
from pathlib import Path
import copy,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent;CANDIDATE='3060dbf561f95e4384fbfd13a9cc5569690515e5'
sys.path.insert(0,str(ROOT/'verification/r5_ci_snapshots_recheck'));from fixtures import C,L,fixture
P=ROOT/'verification/r4_cycle_interfaces/proposal';sys.path.insert(0,str(P));import semantic_minimum as S
assert (P/'recovery_snapshots.py').read_bytes()==subprocess.check_output(['git','show',CANDIDATE+':verification/r4_cycle_interfaces/proposal/recovery_snapshots.py'],cwd=ROOT)
x,p=fixture(0);old=L.latch(C,x,'FEED_CLEAR','R5-malformed-unrelated-journal',truth='UNKNOWN');f=x['faults'].pop(old);f['origin'].pop('guard');fid='F-'+L.digest(f['origin']);f['fault_id']=fid;x['faults'][fid]=f
x['evidence']['RESOURCES_READY']['value']='FALSE';p=None;before=copy.deepcopy((x,p));digest=L.digest([x,p]);assert L.history_valid(x)
raw,reason=L._raw_value(C,'RESTORE_B_CLOSURE','RESOURCES_READY',x,x['evidence']['RESOURCES_READY'],'ENTRY');assert raw=='FALSE'
a=S.recovery_assessment(p,x,C);assert (x,p)==before and L.digest([x,p])==digest
out=dict(C=CANDIDATE,session_id='r5-ci-gate-exits-20261113',expected_action_gate='BLOCKED',actual_action_gate=a['action_gate'],scoped=a['recovery_value'],matched=a['action_gate']=='BLOCKED',independent_frozen_raw_value=raw,independent_frozen_raw_reason=reason,history_valid=True,malformed_fault_id=fid,malformed_fault_digest_valid=fid=='F-'+L.digest(f['origin']),caller_proof_unchanged=True,input_sha256=digest,context=x,proof=p,assessment=a)
(H/'minimal_journal_witness.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['context','proof','assessment']},indent=2))
