#!/usr/bin/env python3
"""Run the synthetic scenarios and arbitration regressions, write reproducible JSON."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import linked
import model

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    plan=json.loads((HERE/'phase_plan.json').read_text())
    inputs=json.loads((HERE/'phase_inputs_synthetic.json').read_text())
    cases=json.loads((HERE/'fixtures.json').read_text())['cases']
    results=[linked.run(v,outcome) for v in 'AB' for outcome in ('sufficient','short','collision','unknown')]
    expected={'sufficient':['SUFFICIENT_STROKE','NO_COLLISION','ALLOWED','READY'], 'short':['INSUFFICIENT_STROKE','NO_COLLISION','BLOCKED','BLOCKED'], 'collision':['SUFFICIENT_STROKE','COLLISION','BLOCKED','BLOCKED'], 'unknown':['INDETERMINATE','INDETERMINATE','INDETERMINATE','INDETERMINATE']}
    for r in results:
        observed=[r['ejection_status'],r['collision_status'],r['transition'],r['ready']['status']]
        continuity=all(x['time_contiguous'] and not x['mismatches'] and not x['unknown'] and x['lifecycle_valid'] for x in r['continuity'])
        r['expected']=expected[r['outcome']];r['matches_expected']=observed==r['expected'] and (r['outcome']!='collision' or r['collision_interval_product_obstacle']==['1/4','7/8']) and (r['outcome']!='sufficient' or continuity)
    # R5 CE-01: independent scalar inconsistent with stationary product.
    c=copy.deepcopy(next(c for c in cases if c['id']=='R5-B-EJECT-SUFFICIENT'))
    for body in c['bodies']:body['delta']=[0,0,0]
    ce1=model.check(c); b=linked.initial(); a={'time':[0,1],'motion_type':'linear','bodies':b}
    overlay=model.verify_a_out(a,copy.deepcopy(a))
    # CE-02: only the wall is moved. Evaluate via the public phase coverage API.
    altered=copy.deepcopy(inputs); phase=altered['phases']['B-EJECT'];phase['bodies']['channel_wall']=copy.deepcopy(phase['bodies']['punch']);phase['bodies']['channel_wall']['delta']=[0,0,0]
    cover=model.evaluate_phases(plan,altered)['B-EJECT']
    found=next(x for x in cover['checked_pairs'] if set(x['bodies'])=={'punch','channel_wall'})
    before=altered['phases']['B-EJECT']; after=altered['phases']['B-RESET']
    dependent=model.transition('B-EJECT','B-RESET',before['bodies'],after['bodies'],{'exit_clear':True},cover,before['time'],after['time'])
    regressions={'CE-01':{'ejection_status':ce1['ejection_status'],'scalar_evidence':ce1.get('ejection_evidence'),'error':ce1.get('ejection_error'),'stationary_A_OUT':overlay,
                          'matches_expected':ce1['ejection_status']=='INVALID_INPUT' and overlay!='CONSISTENT'},
                 'CE-02':{'automatic_pair':found,'dependent_transition':dependent,'matches_expected':found['collision_status']=='COLLISION' and found['evidence']['contact_interval_normalized']==['0','1'] and dependent['status']=='BLOCKED' and 'pair collision or invalid result' in dependent['reasons']}}
    items=[HERE/'model.py',HERE/'linked.py',HERE/'run_linked.py',HERE/'test_model.py',HERE/'test_linked.py',HERE/'phase_plan.json',HERE/'phase_inputs_synthetic.json',HERE/'fixtures.json',HERE/'input_template.json',HERE/'input_audit.md',ROOT/'controls/press_variant_state_tables.md',ROOT/'models/first_digital_model_brief.md',ROOT/'verification/r5_recheck_03/review.md',ROOT/'params/registry.yaml',ROOT/'decisions/ARB-R1-RECHECK-03.md']
    output={'id':'SYN-LINKED-EJECTION','classification':'SYNTHETIC ONLY: not REV', 'arbitration_commit':'1283c9e6f3b14dbbe820dd06798399c611d34ce8','python':sys.version,'hashes':{str(p.relative_to(ROOT)):sha(p) for p in items}, 'registry_snapshot':'registry_snapshot.yaml','scenarios':results,'regressions':regressions,'limitations':['physical force, real product behaviour and safety NOT modelled','A empty column and B release are synthetic assumptions, not REV measurements','scene completeness and all interface rules require independent recheck']}
    out=HERE/'results'/'linked_report.json';out.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'scenarios':[{'variant':r['variant'],'outcome':r['outcome'],'matches_expected':r['matches_expected'],'collision':r['collision_status'],'ejection':r['ejection_status'],'transition':r['transition'],'ready':r['ready']['status']} for r in results],'regressions':{k:v['matches_expected'] for k,v in regressions.items()}},ensure_ascii=False,indent=2))
    return 0 if all(r['matches_expected'] for r in results) and all(v['matches_expected'] for v in regressions.values()) else 1
if __name__=='__main__': sys.exit(main())
