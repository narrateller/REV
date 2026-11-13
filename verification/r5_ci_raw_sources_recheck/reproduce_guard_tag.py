"""Semantic journal-tag comparator: missing/null/known guard, coherent F-digest.
No injection, source mutation, repair or helper state applied to caller.
"""
from pathlib import Path
import copy,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent;CANDIDATE='b89854ad709bcb5c2991376bed41bf2f73acef82'
sys.path.insert(0,str(ROOT/'verification/r5_ci_snapshots_recheck'));from fixtures import C,L,G,fixture
P=ROOT/'verification/r4_cycle_interfaces/proposal';sys.path.insert(0,str(P));import semantic_minimum as S
assert (P/'recovery_snapshots.py').read_bytes()==subprocess.check_output(['git','show',CANDIDATE+':verification/r4_cycle_interfaces/proposal/recovery_snapshots.py'],cwd=ROOT)
rows=[]
for kind in ['missing','null','known-FEED']:
 x,p=fixture(0);old=L.latch(C,x,'FEED_CLEAR','R5-semantic-tag-comparator',truth='UNKNOWN');f=x['faults'].pop(old)
 if kind=='missing':f['origin'].pop('guard')
 elif kind=='null':f['origin']['guard']=None
 fid='F-'+L.digest(f['origin']);f['fault_id']=fid;x['faults'][fid]=f;before=copy.deepcopy((x,p));digest=L.digest([x,p])
 assert L.history_valid(x)
 raw={g:L._raw_value(C,'RESTORE_B_CLOSURE',g,x,x['evidence'][g],'ENTRY')[0] for g in next(a for a in C['recovery_actions'] if a['id']=='RESTORE_B_CLOSURE')['entry_guards']};assert set(raw.values())=={'TRUE'}
 a=S.recovery_assessment(p,x,C);assert (x,p)==before and L.digest([x,p])==digest
 known=type(f['origin'].get('guard'))is str and f['origin']['guard'] in G
 expected='ALLOWED_ASSUMED' if kind=='known-FEED' else 'INDETERMINATE'
 rows.append(dict(id=kind,expected_gate=expected,actual_gate=a['action_gate'],expected_scoped='TRUE' if known else 'UNKNOWN',actual_scoped=a['recovery_value'],matched=a['action_gate']==expected and a['recovery_value']==('TRUE' if known else 'UNKNOWN'),history_valid=True,canonical_fault_id=fid,guard_supported_by_fixed_definitions=known,raw_current=raw,caller_proof_unchanged=True,input_sha256=digest,context=x,proof=p,assessment=a))
result=dict(C=CANDIDATE,session_id='r5-ci-raw-sources-20261113',cases=rows,matches=sum(r['matched'] for r in rows),oracle='R1 raw TRUE cannot establish success under an unclassifiable OPEN journal record; known supported unrelated FEED is a positive control. Guard set from fixed frozen Git definitions.')
(H/'minimal_guard_tag_witness.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2));print([(r['id'],r['expected_gate'],r['actual_gate'],r['actual_scoped']) for r in rows])
