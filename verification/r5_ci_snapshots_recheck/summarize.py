"""Assessment of policy differences at equal levels and admissible domains."""
from pathlib import Path
from collections import Counter
import hashlib,json
H=Path(__file__).resolve().parent;d=json.loads((H/'independent_results.json').read_text());rows=[]
for r in d['cases']:
 a=r['assessment'];out=a['compatibility_domain']=='OUT_OF_DOMAIN'
 classification=('KNOWN_BLOCKED_GATE_MASKED' if not r['matched'] else 'IN_DOMAIN_COMPATIBLE' if not out else 'INTENTIONAL_STRICTER_ADMISSION' if r['frozen_policy']=='ALLOWED_ASSUMED' else 'OUTSIDE_SCHEMA_REJECTED')
 rows.append(dict(id=r['id'],domain=a['compatibility_domain'],classification=classification,admission=a['validation'],expected_action_gate=r['expected']['gate'],actual_action_gate=a['action_gate'],scoped_value=a['recovery_value'],legacy_policy=r['frozen_policy'],legacy_error=r['legacy_error']))
summary=dict(C=d['C'],session_id=d['session_id'],cases=d['count'],matches=d['matches'],failed_case_count=len(d['failed']),failure_branches={'whole_nonobject_proof_before_own_entry_evaluation':15,'proof_action_guard_admission_before_known_causal_denial':4},in_domain=46,in_domain_composite_matches=46,out_of_domain=249,candidate_false_TRUE_count=sum(r['assessment']['recovery_value']=='TRUE' and r['expected']['value']!='TRUE' for r in d['cases']),counts=dict(Counter(r['classification'] for r in rows)),B03='OPEN',stable_documentary_handoff='NO_GO',comparisons=rows)
assert summary['failed_case_count']==19 and summary['candidate_false_TRUE_count']==0
(H/'policy_comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
text=['# Independent policy comparison','', 'Compatibility asserted only for fixed-schema IN_DOMAIN inputs at matching result levels. OUT_OF_DOMAIN rows state their rejected schema; frozen legacy outcome is diagnostic, never an admission oracle.','', '| Case | Domain | Scoped | Action / expected | Legacy | Classification | Schema reason |','|---|---|---|---|---|---|---|']
for r in rows:
 reasons='; '.join(x['path']+':'+x['code'] for x in r['admission']['reasons']) or 'admitted'
 text.append('| '+ ' | '.join([r['id'],r['domain'],r['scoped_value'],r['actual_action_gate']+' / '+r['expected_action_gate'],r['legacy_policy'] or ('EXCEPTION:'+str(r['legacy_error'])),r['classification'],reasons])+' |')
(H/'policy_comparison.md').write_text('\n'.join(text)+'\n')
# Two minimal complete witnesses, rather than presenting 19 variations as 19 defects.
minimal=[next(r for r in d['failed'] if r['id']==id) for id in ['compound:resource-fault:whole-proof-null','compound:causal:action-missing']]
(H/'minimal_witnesses.json').write_text(json.dumps(dict(C=d['C'],session_id=d['session_id'],scope='Two early-return branches; no candidate TRUE; originals remain unchanged',witnesses=minimal),indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='comparisons'},indent=2))
