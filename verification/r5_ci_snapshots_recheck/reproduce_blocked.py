"""Replay the two minimal immutable JSON witnesses, without changing state.
Exit zero captures the result; matched=false documents the reviewed defect.
"""
from pathlib import Path
import copy,hashlib,json,subprocess,sys
from fixtures import ROOT,C,L
H=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces/proposal';CANDIDATE='e30b4b7caf3040905cc23c79ca696af2871c958a'
sys.path.insert(0,str(P));import semantic_minimum as S
for name in ['semantic_minimum.py','recovery_snapshots.py','metadata_types.py']:
 p=P/name;assert p.read_bytes()==subprocess.check_output(['git','show',CANDIDATE+':'+str(p.relative_to(ROOT))],cwd=ROOT)
data=json.loads((H/'minimal_witnesses.json').read_text());rows=[]
for r in data['witnesses']:
 x=copy.deepcopy(r['context']);p=copy.deepcopy(r['proof']);before=L.digest([x,p])
 if p is None:assert L.evaluate(C,'RESTORE_B_CLOSURE',x,'ENTRY')['permission_outcome']=='BLOCKED'
 else:
  parents=x['faults'][p['fault_id']]['origin']['cause_fault_ids'];assert parents and any(x['faults'][f]['status']=='OPEN' for f in parents)
 a=S.recovery_assessment(p,x,C);_,legacy=L.recover(C,'RESTORE_B_CLOSURE',x,p['fault_id'] if type(p)is dict else 'F-'+'0'*64,p)
 assert legacy=='BLOCKED' and L.digest([x,p])==before and a['recovery_value']!='TRUE'
 rows.append(dict(id=r['id'],expected_action_gate='BLOCKED',actual_action_gate=a['action_gate'],scoped_value=a['recovery_value'],frozen_gate=legacy,matched=a['action_gate']=='BLOCKED',input_unchanged=True,caller_and_proof_sha256=before,assessment=a))
result=dict(C=CANDIDATE,session_id='r5-ci-snapshots-20261113',cases=rows,matched=sum(r['matched'] for r in rows))
(H/'minimal_replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
