"""Independent R5 documentary oracle. Never imports an author's checker/renderer.

Uses immutable exact-C objects plus R5's separately written semantic expectations.
PASS guards establish the stated invariants, not completeness or machine safety.
Open semantic observations are separate and determine the WARNING verdict.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse
import hashlib
import json
import re
import subprocess
from semantic_expectations import SCOPE, METHODS, ROW_FOLLOWUP

ROOT=Path(__file__).resolve().parents[2]
C='7e2d5ecff42fe1d09b461e05375924cb644c27c9'
H='7e4ce7aad8396493da6e2284d29441b46b4abb80'
BASE='65dcc7b6f861b5d5c5bee1428a8a4da1b6248ff3'
P='verification/r1_g1_definition_register_20261117/'
OLD='verification/r1_g1_observation_revision_20261117/'
REV8='verification/r1_requirements_draft_20261117/'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(c,p):return git('show',c+':'+p)
def jd(p,c=C):return json.loads(blob(c,p))
def sha(b):return hashlib.sha256(b).hexdigest()
def material(b):
    m=re.match(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})',b)
    return m[1].decode() if m else sha(b)
def tree(c):
    return {s.split('\t',1)[1]:s.split('\t',1)[0].split()[2] for s in git('ls-tree','-r',c).decode().splitlines()}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    checks=[]
    def ck(i,ok,observed,expected):checks.append(dict(id=i,result='PASS' if ok else 'FAIL',observed=observed,expected=expected))
    definitions=jd(P+'definition_register.json');methods=jd(P+'method_catalog.json');sources=jd(P+'source_applicability.json');decisions=jd(P+'decision_register.json')
    reqs=jd(REV8+'draft_requirements.json')['requirements'];cards=jd(OLD+'criterion_cards.json')['rows'];met=jd(OLD+'metrology_plan.json')
    rows=definitions['rows'];dms=methods['rows']
    ck('universe',len(rows)==len(dms)==len(reqs)==len(cards)==22 and len(SCOPE)==len(METHODS)==len(ROW_FOLLOWUP)==22,[len(rows),len(dms),sum(len(x) for x in SCOPE.values())],'22 REQ/VAL,22 DM,144 independently read scope items')
    scope_assess=[];row_assess=[];method_assess=[]
    for n,(row,dm,req,card) in enumerate(zip(rows,dms,reqs,cards),1):
        tag=f'{n:02d}';reqid='REQ-REV-'+tag;valid='VAL-REV-'+tag
        ck('link:'+tag,row['requirement_id']==dm['requirement_id']==req['id']==card['requirement_id']==reqid and row['validation_id']==dm['validation_id']==card['validation_id']==valid and row['requirement_text']==req['proposed_requirement'],reqid,'Exact frozen REQ/VAL/text')
        ck('refs:'+tag,row['frozen_requirement_ref']==dict(commit='8d1b45afa84eca078a8de0a9822d6925dd87745b',path=REV8+'draft_requirements.json',selector=reqid) and row['predecessor_card_ref']==dict(commit='45d5964786e608cdfcc656819fd6df8c77e495fe',path=OLD+'criterion_cards.json',selector='CRIT-'+reqid),[row['frozen_requirement_ref'],row['predecessor_card_ref']],'Exact predecessor locators; old acts do not transfer')
        inherited={'mode':'mode','criterion_kind':'criterion_kind','future_conformity_predicate_ref':'proposed_future_pass_predicate','future_evidence_fields':'mandatory_evidence_fields','channel_ids':'measurement_channel_ids','source_field_refs':'source_field_refs','qualitative_refs':'qualitative_refs'}
        ck('retained:'+tag,all(row[k]==card[v] for k,v in inherited.items()),list(inherited),'Whole inherited objects equal corrected predecessor, not just counts')
        items=row['proposed_enumerated_scope'];expected=SCOPE[n]
        ck('scope-count:'+tag,len(items)==len(expected),len(items),len(expected))
        for index,(item,(needle,rationale)) in enumerate(zip(items,expected)):
            ident=f'DEF-{tag}-{chr(65+index)}'
            ck('scope:'+ident,item['scope_item_id']==ident and needle.casefold() in item['description'].casefold() and item['status']=='PROPOSED_NOT_APPROVED' and item['future_disposition'] is None and bool(item['unknown_reason']),item,'Independently read subject category, proposed and undispositioned')
            scope_assess.append(dict(id=ident,description=item['description'],assessment=rationale,status='USEFUL_PROPOSED_CATEGORY_NOT_EXHAUSTIVENESS_OR_CONFORMITY_PROOF'))
        num=row['numeric_criterion'];ck('unknown:'+tag,all(num[k] is None for k in ['value','unit','tolerance','uncertainty_acceptance_limit']) and num['approved_parameter_refs']==[] and bool(num['unknown_reason']) and row['criterion_approval']==row['method_approval']=='NOT_APPROVED' and row['future_result_status']=='NOT_RUN' and row['actual_evidence_records']==[],num,'No invented zero,limit,unit,tolerance,uncertainty or actual evidence')
        ck('owner:'+tag,row['assigned_engineering_owner_session'] is None and row['engineering_owner_unknown_reason'] and row['documentary_owner_session']=='6afb300b-1540-8191-a5c4-be1a684c20e0' and row['decision_approver']=='USER_SEPARATE_APPROVAL_REQUIRED',row['suggested_engineering_functions'],'Suggested function is not appointed competent session; separate user authority')
        profile='DOCUMENTARY_AUDIT' if n in [18,19,20,21] else 'MIXED_OR_NUMERIC_REQUIRES_SUBCLAIM_SELECTION'
        ck('DOC-profile:'+tag,row['evidence_profile']==profile,[profile,row['channel_ids']],'Pure scope audit separated from measured/modelled claims; applicable metrology retained')
        needle,assessment=METHODS[n-1]
        ck('DM:'+tag,dm['method_id']==row['definition_method_id']=='DM-'+tag and dm['revision_label']=='DRAFT-01' and dm['method_type']=='PROPOSED_DOCUMENTARY_DEFINITION_AUDIT' and needle.casefold() in dm['procedure'].casefold() and dm['input_scope_items']==[i['scope_item_id'] for i in items] and dm['common_protocol']=='DOC-DEFINITION-AUDIT-01' and dm['authority_status']=='PROPOSED_NOT_APPROVED' and dm['future_physical_method_revision'] is None and bool(dm['future_physical_method_unknown_reason']) and dm['actual_results']==[],dm['procedure'],'Definition audit distinct from selected/authorized future machine method')
        ck('DM-record:'+tag,set(dm['output_record_fields'])=={'scope_item_id','definition_revision','source_locator','criterion_ref','method_ref','owner_ref','disposition','reason','reviewer','remaining_gap'},dm['output_record_fields'],'Item-level trace/decision/reviewer/gap retained')
        row_assess.append(dict(requirement_id=reqid,validation_id=valid,object=row['object'],mode=row['mode'],observations_read=row['observations_to_define'],open_decisions_read=row['open_definition_decisions'],scope_items=len(items),assessment='Useful preliminary definition inventory; neither complete approved requirement nor performed validation.',mandatory_followup=ROW_FOLLOWUP[n-1],observations=['R5-DEF-OBS-01'] if n==2 else ['R5-DEF-OBS-01','R5-DEF-OBS-02'] if n==3 else []))
        method_assess.append(dict(method_id=dm['method_id'],procedure=dm['procedure'],assessment=assessment,not_machine_verification=True,execution='NOT_RUN'))
    common=methods['common_protocol'];text=json.dumps(common)
    ck('common-protocol',common['id']=='DOC-DEFINITION-AUDIT-01' and common['revision_label']=='DRAFT-01' and len(common['steps'])==5 and common['execution_status']=='NOT_RUN' and common['approval_status']=='NOT_APPROVED' and all(x in text for x in ['silence or absence is UNRESOLVED','mixed/numeric','calibration','uncertainty','no auto G1 closure','independently reviewed']),common,'No silence/absence=PASS or numeric-metrology exemption')
    policies=[
        dict(case='Unlisted mandatory property',assessment='The common rule cannot establish completeness until the property universe/crosswalk is complete; OBS-01 remains open.'),
        dict(case='No product after incomplete discharge',assessment='Retain cycle/outcome/missing reason; absence of a measurement cannot erase a failed record. DM03 needs clarification (OBS-02).'),
        dict(case='Measured or model-derived subclaim in DOCUMENT row',assessment='Pure categorical audit assurance does not waive units, calibration, timebase, uncertainty or provenance of numeric subclaims.'),
        dict(case='JUSTIFIED_EXCLUSION',assessment='Prospective disposition only; independent review and actual approval authority required. No reviewer may silently waive mandatory user functions.'),
        dict(case='Model reaction or dwell timer',assessment='A prediction is not a confirmed actual reaction; dwell is not proof of unloading/no motion.'),
        dict(case='G1 completeness review',assessment='Requires definition/method/owner/risk/coverage decisions, not completed future G2-G4 calculations, CAD or tests as documentary prerequisites.')]
    frozen=jd(REV8+'source_disposition.json','8d1b45afa84eca078a8de0a9822d6925dd87745b')['rows']
    source_assess=[]
    proposals={'BPR_AMBIENT_MIN','BPR_AMBIENT_MAX','BPR_SUPPLY_VOLTAGE','BPR_SUPPLY_FREQUENCY','BPR_SUPPLY_CURRENT','BPR_BRIQUETTE_SIDE_1','BPR_BRIQUETTE_SIDE_2','BPR_BRIQUETTE_LENGTH_MIN','BPR_BRIQUETTE_LENGTH_MAX','BPR_THROUGHPUT_UPPER'}
    issues={'BPR_MOISTURE_MIN','BPR_MOISTURE_MAX','BPR_INSTALLED_POWER','BPR_MAIN_MOTOR_POWER','BPR_INFEED_MOTORS_POWER','BPR_COOLING_POWER','BPR_COMPACTION_PRESSURE_LITERAL'}
    for r,old in zip(sources['rows'],frozen):
        ident=r['field_id'];expected='TARGET_PROPOSAL' if ident in proposals else 'OPEN_SOURCE_ISSUE' if ident in issues else 'REFERENCE_CONTEXT'
        if 'MOISTURE' in ident:assessment='Keep donor-specific window and unknown wet/dry basis/method. BP500 primary intent; E55/WEIMA are context, never merged or averaged.'
        elif 'POWER' in ident:assessment='Keep total and component declarations separate; contradiction OPEN, no own power sum/budget.'
        elif 'PRESSURE_LITERAL' in ident:assessment='Literal mass/force unit unresolved; no assumed kgf, SI value or derived force.'
        elif 'HYDRAULIC_PRESSURE' in ident:assessment='Hydraulic maximum is not material stress or actual duty-case spectrum.'
        elif 'THROUGHPUT' in ident:assessment='Conditional up-to/material/settings-dependent count rate; no guaranteed minimum or computed mass rate.'
        elif 'BRIQUETTE' in ident:assessment='Source product size/mass context, not stroke/cavity/dose or measured REV product; own criterion/conditioning/method unknown.'
        elif 'AMBIENT' in ident:assessment='Indoor reference proposal, not measured site qualification or a material moisture criterion.'
        elif 'SUPPLY' in ident:assessment='Proposed site connection execution, not actual consumption, protection design or readiness.'
        elif 'BUNKER' in ident:assessment='Listed opening/height/volume context; no inferred axes, dose, flow or own layout.'
        elif 'MACHINE' in ident or 'TABLE_DIM' in ident:assessment='Reference installed size/mass/configuration, not hard site envelope, CoG, moving mass or support reaction.'
        else:assessment='Reference count/speed/filter/volume/execution; no REV COTS, architecture or BOM selection. Preserve Hz versus angular velocity and listed configuration.'
        ck('SOURCE:'+ident,r==old and r['disposition']==expected and r['candidate_lifecycle']=='RAW' and r['REV_realized_value'] is None and r['realized_unknown_reason'] and not r['parameter_promotion'] and not r['numerical_engineering_use'] and bool(r['source_locator']) and bool(r['reason']),r,'Full frozen row and qualifiers unchanged; independently assessed disposition '+expected)
        source_assess.append(dict(field_id=ident,unit=r['unit'],disposition=expected,assessment=assessment,source_locator=r['source_locator'],no_new_PDF_certification=True))
    ck('SOURCE40',len(sources['rows'])==len(frozen)==40 and Counter(r['disposition'] for r in sources['rows'])==dict(TARGET_PROPOSAL=10,REFERENCE_CONTEXT=23,OPEN_SOURCE_ISSUE=7) and not sources['dispositions_changed'] and not sources['active_registry_modified'],dict(Counter(r['disposition'] for r in sources['rows'])),'10 proposals/23 context/7 issues; all RAW')
    decision_reasons={
        'B01':'Own defined quantity/limit/tolerance/mode or objective completeness and competent owners required; null not zero.',
        'B02':'Controlled methods, scope/coverage, missing/stop rules and applicable metrology need independent program review.',
        'B03':'Actual safety-state/retention/isolation/recovery and normative scope need justified definitions; no assigned PL/SIL.',
        'SOURCE-POWER':'Primary contradiction unresolved; justified exclusion/own criterion needs independent review and user decision.',
        'SOURCE-PRESSURE-UNIT':'Physical quantity/unit/point/conditions unresolved; do not convert guessed kgf.',
        'SOURCE-MOISTURE-BASIS':'Wet/dry basis/method unresolved; comparator windows noninterchangeable.',
        'OPERATING-COUNTRY':'Pending existing user question; no fabricated answer or repeated questionnaire. RF manufacture is not operation jurisdiction.',
        'ENGINEERING-OWNERS':'Actual competent session appointments remain missing; R1 is documentary coordinator only.',
        'G1-FULL-REVIEW':'New whole-package sufficiency and separate user approval remain required; predecessor acts only cover exact predecessors.'}
    decision_assess=[]
    ck('decision-universe',{r['issue_id'] for r in decisions['rows']}==set(decision_reasons),[r['issue_id'] for r in decisions['rows']],list(decision_reasons))
    for r in decisions['rows']:
        ck('DECISION:'+r['issue_id'],r['status']=='OPEN' and r['assigned_engineering_owner_session'] is None and r['due_utc'] is None and r['closure_evidence']==[] and r['blocks_G1'] and not r['closed_by_this_package'],r,'Still open, no owner/deadline/closure invented')
        decision_assess.append(dict(id=r['issue_id'],assessment=decision_reasons[r['issue_id']],closure_needed=r['closure_needed'],status='OPEN'))
    ck('country-primary',decisions['BP500_primary'] and decisions['operating_country'] is None and decisions['operating_country_unknown_reason'] and not decisions['existing_reference_conflicts_closed'] and not decisions['TZ_approved'] and decisions['W02']==decisions['physical_READY']=='NO_GO',decisions['other_press_policy'],'BP500 primary; others relevance only; country unknown; conflicts and readiness not closed')
    force=jd(OLD+'force_evidence_plan.json');haz=jd(OLD+'hazard_to_evidence.json')
    ck('TRACE-new-DM09',all(t in dms[8]['procedure'] for t in ['H01','REQ09','VAL09','MET09','FORCE_REACTION']) and 'H01' in dms[15]['procedure'] and 'FORCE_REACTION' in rows[8]['channel_ids'],[dms[8]['procedure'],dms[15]['procedure']],'Direct lifting/structural trace retained, REQ16/17 not replaced')
    ck('TRACE-preserved-plans',len(haz['rows'])==20 and jd(OLD+'force_evidence_plan.json')==jd(OLD+'force_evidence_plan.json',BASE) and met==jd(OLD+'metrology_plan.json',BASE),[len(haz['rows']),len(met['rows'])],'Corrected hazard/metrology/provenance plans byte/whole-object preserved; no reaction calculation')
    doc=next(r for r in met['channels'] if r['channel_id']=='DOCUMENT')
    ck('DOC-no-numeric-waiver',doc['numeric_uncertainty_applicability']['status']=='NOT_APPLICABLE' and 'mixed' in doc['numeric_uncertainty_applicability']['reason'] and doc['field_applicability']['method_revision']['status']=='APPLICABLE_UNKNOWN' and len(doc['procedural_assurance_criteria'])==4 and all(r['status']=='NOT_RUN' and r['actual_evidence']==[] for r in doc['procedural_assurance_criteria']),doc['procedural_assurance_criteria'],'Categorical assurance has four explicit dimensions; no approved audit method or numeric-metrology waiver')
    ck('TRACE-own-inputs-unknown',force['selected_method_route'] is None and force['actual_load_cases']==[] and force['actual_records']==[] and force['engineering_owner_session'] is None and all(r['value'] is None and r['source_record'] is None and r['source_commit'] is None and r['source_sha256'] is None and r['unknown_reason'] for r in force['input_definitions']) and all(not r['execution_permission'] and r['execution_status']=='NOT_RUN' for r in force['route_specs']),force['selection_unknown_reason'],'Ten own mass/CoG/interface/support/pose/load/material/geometry/rigging/limit inputs unknown; routes unselected/unexecuted')
    ck('TRACE-frame-sign-quality',all(t in force['provenance_required_fields'] for t in ['source_commit','source_sha256','frame_origin_axes_units_signs','point_or_interface_id','quality_and_uncertainty_basis','independent_validation_scope']) and any(r['evidence_kind']=='MODEL_PREDICTION_NOT_ACTUAL_REACTION_CONFIRMATION' for r in force['route_specs']),force['provenance_required_fields'],'Exact input/output provenance and frame/sign/quality/validation; model prediction not actual reaction')
    manifest=jd(P+'input_manifest.json');oldmanifest=jd('verification/r4_force_geometry/input_manifest.json')
    ck('pins-trees-counts',len(manifest['inputs'])==92 and len(manifest['protected_trees'])==12 and len(oldmanifest['inputs'])==54 and len(oldmanifest['protected_trees'])==12,[len(manifest['inputs']),len(oldmanifest['inputs'])],'92new/54old inputs;12 protected trees each')
    for r in manifest['inputs']:
        ck('PIN:'+r['path'],material(blob(r['commit'],r['path']))==r['sha256'] and git('rev-parse',r['commit']+':'+r['path']).decode().strip()==r['git_blob'] and material(blob(C,r['path']))==r['sha256'],r['sha256'],'Exact source pin and target material')
    for r in oldmanifest['inputs']:
        src=blob(r['commit'],r['path']);dst=blob(C,r['path']);ok=dst.startswith(src) if r['path']=='reviews/cross_check_log.md' else material(dst)==r['sha256']
        ck('OLDPIN:'+r['path'],material(src)==r['sha256'] and ok,r['sha256'],'Original source SHA and current preservation (journal legal append only)')
    for path,oid in manifest['protected_trees'].items():
        ck('TREE:'+path,git('rev-parse',C+':'+path).decode().strip()==oid==git('rev-parse',BASE+':'+path).decode().strip(),oid,'Current main tree pinned unchanged in exact target')
        changed=git('diff',C,'--name-only','--',path).decode().splitlines()
        ck('WORKTREE:'+path,set(changed)<={'reviews/cross_check_log.md'} and (ROOT/'reviews/cross_check_log.md').read_bytes().startswith(blob(C,'reviews/cross_check_log.md')),changed,'Only own lawful journal append after exact target prefix')
    for path,oid in oldmanifest['protected_trees'].items():
        if path!='reviews':ck('OLDTREE:'+path,git('rev-parse',C+':'+path).decode().strip()==oid,oid,'Old protected tree unchanged')
        else:
            for sub,oldoid in tree(oid).items():
                olddata=git('cat-file','blob',oldoid);newdata=blob(C,'reviews/'+sub)
                ck('OLDREVIEWS:'+sub,newdata.startswith(olddata) if sub=='cross_check_log.md' else newdata==olddata,oldoid,'Old journal exact prefix, other old review files unchanged')
    targets=[('45d5964786e608cdfcc656819fd6df8c77e495fe',OLD,25),('fe10c0bc7242fe9d2df3e571c80b4e687f731d7c','verification/r1_g1_criteria_plan_20261117/',26),('8d1b45afa84eca078a8de0a9822d6925dd87745b',REV8,25),(C,P,22)]
    for commit,prefix,count in targets:
        target=jd(prefix+'review_target_manifest.json',commit)
        ck('MANIFEST-count:'+prefix,len(target['artifacts'])==count,len(target['artifacts']),count)
        for r in target['artifacts']:
            p=r['path'];ck('SEALED:'+p,material(blob(commit,p))==r['sha256']==material(blob(C,p))==sha((ROOT/p).read_bytes()),r['sha256'],'Old/new target content preserved in C and material worktree')
        ck('MANIFEST-preserved:'+prefix,blob(C,prefix+'review_target_manifest.json')==blob(commit,prefix+'review_target_manifest.json'),sha(blob(C,prefix+'review_target_manifest.json')),'Target manifest itself unchanged')
    tc,tb=tree(C),tree(BASE)
    allowed={'STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','coordination/tasks/T-r1-requirements-draft-01/task.json','handoffs/T-r1-requirements-draft-01/6afb300b-1540-8191-a5c4-be1a684c20e0.md'}
    preserved=[];lfs=[]
    for path,oid in tb.items():
        if path in allowed:continue
        ck('BASEFILE:'+path,tc.get(path)==oid,tc.get(path),'Every nonoperational baseline object unchanged');preserved.append(path)
        data=git('cat-file','blob',oid)
        if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
            actual=sha((ROOT/path).read_bytes());ck('LFS:'+path,actual==material(data),actual,material(data));lfs.append(dict(path=path,sha256=actual,git_lfs_oid=material(data)))
    for path,key,count in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json','rows',44),('verification/r4_force_geometry/symbolic_20261116/interfaces.json','rows',52),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',None,84),('verification/r3_force_path/analysis/state_matrix.json',None,42)]:
        d=jd(path);items=d[key] if key else d;ck('COUNT:'+path,len(items)==count and blob(C,path)==blob(BASE,path),len(items),'Whole unchanged object with '+str(count)+' rows')
    unknown=jd('verification/r4_force_geometry/symbolic_20261116/unknown_index.json');ck('RAW84',all(r['status']=='UNKNOWN' and r['source_lifecycle']=='RAW' and r['value'] is None and r['source_unknown_reason'] for r in unknown),84,'All84 UNKNOWN/RAW/null remain')
    gaps=jd(REV8+'open_gaps.json');ck('gaps15',len(gaps['rows'])==15 and not gaps['engineering_owners_assigned'] and all(r['status']=='OPEN' and r['value'] is None and r['assigned_owner_session'] is None and r['due_at_utc'] is None and r['unknown_reason'] for r in gaps['rows']),15,'All15 additional gaps OPEN/null; no owner/deadline invented')
    hist=jd('verification/r5_r4_force_geometry_symbolic_review/independent_after_record.json');closure=jd('verification/r5_r4_symbolic_obs01_recheck/independent_final.json')
    ck('history-four-fail',hist['counts']=={'PASS':2422,'FAIL':4},hist['counts'],'Original record unchanged, not rerun/recertified')
    ck('history-OBS01',closure['target_C']=='beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe' and closure['OBS01']=='CLOSED_DOCUMENTARY_EXACT_C',closure['OBS01'],'Exact predecessor closure retained only')
    journal=blob(C,'reviews/cross_check_log.md').decode()
    for t in ['material_contract_consecutive_rejections: 2','REJECT_WITH_BLOCKER','validity: STALE','R5-TZ-B01','R5-TZ-B02','R5-TZ-B03']:ck('history:'+t,t in journal,t,'No history/counter reset')
    for name,d in [('definition_register',definitions),('method_catalog',methods),('source_applicability',sources),('decision_register',decisions)]:
        ck('BOUNDARY:'+name,d['status']=='DRAFT_NOT_APPROVED' and d['independent_output_review']=='NOT_RUN' and d['G1']=='OPEN' and all(d[k] is False for k in ['requirements_approved','engineering_started','source_states_solved','physical_tests_run','execution_permission']),name,'Source remains unapproved/unexecuted; own act separate')
    findings=[dict(id='R5-DEF-OBS-01',status='OPEN',blocking_preliminary_DRAFT=False,blocks_scope_completeness=True,refs=['VAL-REV-02','VAL-REV-03','DEF-REQ-REV-02','DEF-REQ-REV-03','DM-02','DM-03'],description='Retained VAL02 includes density and MATERIAL channel bulk density; VAL03 includes product mass/residue and MASS evidence. Enumerated DEF02/03 scope does not explicitly identify density/product-mass coverage or a controlled crosswalk. No actual evidence was deleted. Residue is also retained under REQ22; duplication is not required.',required_action='Explicitly map each retained quantity to a controlled definition scope item/cross-reference, or justify any exclusion through independent review and actual user authority. No new numerical threshold/calculation is requested.'),dict(id='R5-DEF-OBS-02',status='OPEN',blocking_preliminary_DRAFT=False,blocks_method_approval=True,refs=['DM-03','DEF-01-E','DEF-04-D','REQ-REV-22'],description='DM03 phrase «предусмотреть отсутствие результата при неполной выдаче» is ambiguous. Absence of product/measurement must not mean omission of failed/incomplete cycle or disposition record. Other retained scopes/schema preserve those records; no actual data loss demonstrated.',required_action='Clarify retained cycle/product outcome, quality/missing reason and failed/incomplete disposition even when product/measurement is absent; link the full-series accounting schema before method/program approval.')]
    for section in ['4','5','6']:checks.append(dict(id='PHYSICAL-SECTION-'+section,result='NOT_RUN',observed='No numerical/physical execution;42 states unsolved',expected='Separate real inputs and authorization required'))
    result=dict(reviewed_commit=C,request_H=H,actual_session_id=SESSION,checked_at_utc=datetime.now(timezone.utc).isoformat(),counts=dict(Counter(r['result'] for r in checks)),scope_assessments=scope_assess,row_assessments=row_assess,method_assessments=method_assess,common_protocol_assessment='Useful proposed item-level definition audit; unresolved universe/criteria/methods/owners cannot produce G1. Review/user authority required for exclusions.',semantic_policy_cases=policies,semantic_cases_are='Documentary reasoning, not machine calculation or tests of an implemented conformity evaluator',source_assessments=source_assess,decision_assessments=decision_assess,findings=findings,preserved_baseline_files=preserved,hydrated_LFS=lfs,checks=checks,failures=[r for r in checks if r['result']=='FAIL'],overall_verdict='WARNING',preliminary_DRAFT_usable=True,G1_sufficient=False,author296_or_prior_reviews_as_new_proof=False,physical_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'},G1='OPEN',W02='NO_GO',physical_READY='NO_GO',source_states_solved=False)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(counts=result['counts'],scope=len(scope_assess),rows=len(row_assess),methods=len(method_assess),sources=len(source_assess),decisions=len(decision_assess),baseline_files=len(preserved),LFS=len(lfs),failures=result['failures']),ensure_ascii=False));return bool(result['failures'])
if __name__=='__main__':raise SystemExit(main())
