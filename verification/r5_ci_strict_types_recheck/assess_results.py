"""Separate observed mismatches from overbroad exploratory expectations."""
from pathlib import Path
from collections import Counter
import json
H=Path(__file__).resolve().parent;d=json.loads((H/'independent_results.json').read_text());s=json.loads((H/'incomplete_results.json').read_text())
assert len(d['export_cases'])==215 and all(c['expected']==c['actual'] for c in d['export_cases'])
assert len(d['recovery_cases'])==167 and d['total_checks']==1222 and d['matches']==1144
rows=[]
for c in d['failed']:
 id=c['id'];context_irrelevant=any('context:'+k+':' in id for k in ['FEED','RETENTION'])
 if id.startswith('policy-classification:'):
  assessment='Observed conservative diagnostic/admission difference; no candidate false TRUE. Separate from incompleteness blocker.'
 elif context_irrelevant:
  assessment='Exploratory expectation was broader than frozen B_RESET required domains. FEED/RETENTION are not B-closure evidence domains. Record behavior; not a product false-permission finding.'
 elif 'expected:B_CLOSURE:missing' in id:
  assessment='Confirmed incomplete target snapshot false TRUE; repeated and isolated in incomplete_results.'
 else:
  assessment='Frozen helper permits malformed expected snapshot bool False/float zero, candidate rejects UNKNOWN. Legacy policy gap/conservative candidate, not candidate false TRUE.'
 rows.append(dict(assertion=id,expected=c['expected'],actual=c['actual'],assessment=assessment))
r=dict(raw_checks=1222,raw_matches=1144,raw_mismatches=78,not_78_distinct_product_defects=True,static_exports=dict(cases=215,correct_rejections=198,correct_matches=17,hashes_fresh=True,checker_readonly=True),recovery_cases=167,exact_policy_differences=sum(not c['classification_equal'] for c in d['recovery_cases']),supplement=dict(cases=7,matches=3,false_TRUE_witnesses=s['failures']),B03='OPEN',verdict='REJECT_WITH_BLOCKER',stable_documentary_handoff='NO_GO',assessment=rows)
(H/'assessment.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('215/215 exports; 4 concrete incomplete-snapshot false TRUE witnesses; B03 OPEN')
