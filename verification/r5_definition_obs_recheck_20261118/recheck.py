"""Independent exact-C documentary OBS01/02 delta recheck; no author imports.

The sole expected FAIL is the separately reported DM02/03 rendered revision
mismatch. It is not suppressed, and it does not undo the bounded semantic
corrections of the two original observations. Counts are not physical tests.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse
import hashlib
import json
import re
import subprocess
from semantic_expectations import ROW_ASSESSMENTS, MAPPING_EXPECTATIONS, SEMANTIC_CASES

ROOT=Path(__file__).resolve().parents[2]
C='97f58fd437947e26963bdbbc2f2d89df7438e8cc'
H='46cbf199c3d17049ac31aa337378f0b176e70a2e'
BASE='ad627d310ee9f49d730b71c84ab4af7c9c1ff0da'
PREV='7e2d5ecff42fe1d09b461e05375924cb644c27c9'
P='verification/r1_g1_definition_obs_revision_20261117/'
OLD='verification/r1_g1_definition_register_20261117/'
TRACE='verification/r1_g1_observation_revision_20261117/'
REV8='verification/r1_requirements_draft_20261117/'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def raw(c,p):return git('show',c+':'+p)
def jd(p,c=C):return json.loads(raw(c,p))
def sha(b):return hashlib.sha256(b).hexdigest()
def material(b):
    m=re.search(rb'oid sha256:([0-9a-f]{64})',b) if b.startswith(b'version https://git-lfs.github.com/spec/v1') else None
    return m[1].decode() if m else sha(b)
def tree(c):return {s.split('\t',1)[1]:s.split('\t',1)[0].split()[2] for s in git('ls-tree','-r',c).decode().splitlines()}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();checks=[]
    def ck(i,ok,observed,expected):checks.append(dict(id=i,result='PASS' if ok else 'FAIL',observed=observed,expected=expected))
    defs=jd(P+'definition_register.json');old=jd(OLD+'definition_register.json',PREV);methods=jd(P+'method_catalog.json');oldmethods=jd(OLD+'method_catalog.json',PREV)
    reqs=jd(REV8+'draft_requirements.json','8d1b45afa84eca078a8de0a9822d6925dd87745b')['requirements'];rows=defs['rows'];dm=methods['rows'];allitems={s['scope_item_id']:s for r in rows for s in r['proposed_enumerated_scope']}
    ck('22REQ-146unique',len(rows)==len(dm)==len(reqs)==len(ROW_ASSESSMENTS)==22 and len(allitems)==sum(len(r['proposed_enumerated_scope']) for r in rows)==146,[len(rows),len(dm),len(allitems)],'22 linked REQ/VAL and146 proposed unique items')
    row_assess=[];scope_assess=[];method_assess=[]
    changed_row_fields={'proposed_enumerated_scope','observations_to_define','open_definition_decisions','additional_definition_evidence_fields'}
    changed_method_fields={'revision_label','input_scope_items','procedure','quantity_crosswalk_ref','future_record_retention_ref','required_future_cycle_fields'}
    for i,(r,o,m,om,req,assessment) in enumerate(zip(rows,old['rows'],dm,oldmethods['rows'],reqs,ROW_ASSESSMENTS),1):
        rid=f'REQ-REV-{i:02d}';vid=f'VAL-REV-{i:02d}';changed=i in [2,3]
        ck('REQVAL:'+rid,r['requirement_id']==o['requirement_id']==m['requirement_id']==req['id']==rid and r['validation_id']==m['validation_id']==vid and r['requirement_text']==req['proposed_requirement'] and r['frozen_requirement_ref']['commit']=='8d1b45afa84eca078a8de0a9822d6925dd87745b',rid,'Exact frozen requirement/validation/text/ref,not revised user intent')
        if changed:
            ck('bounded-row:'+rid,{k:v for k,v in r.items() if k not in changed_row_fields}=={k:v for k,v in o.items() if k not in changed_row_fields} and r['proposed_enumerated_scope'][:-1]==o['proposed_enumerated_scope'] and r['observations_to_define'][:-1]==o['observations_to_define'] and r['open_definition_decisions'][:-1]==o['open_definition_decisions'],list(changed_row_fields),'Only identified documentary additions;old full scope/observations/gaps exact prefixes')
            ck('bounded-method:'+rid,{k:v for k,v in m.items() if k not in changed_method_fields}=={k:v for k,v in om.items() if k not in changed_method_fields} and m['revision_label']=='DRAFT-02',m['revision_label'],'OnlyDM02/03 identity/scope/procedure/crosswalk/retention fields changed')
        else:ck('20full-unchanged:'+rid,r==o and m==om,rid,'Whole row AND whole method unchanged,not count-only')
        ck('method-scope:'+rid,m['method_id']==r['definition_method_id']==f'DM-{i:02d}' and m['input_scope_items']==[s['scope_item_id'] for s in r['proposed_enumerated_scope']] and m['method_type']=='PROPOSED_DOCUMENTARY_DEFINITION_AUDIT' and m['future_physical_method_revision'] is None and m['future_physical_method_unknown_reason'] and m['actual_results']==[] and m['authority_status']=='PROPOSED_NOT_APPROVED',m['input_scope_items'],'Correct documentary method/scope;no selected/authorized physical method/result')
        n=r['numeric_criterion'];ck('unknown:'+rid,all(n[k] is None for k in ['value','unit','tolerance','uncertainty_acceptance_limit']) and n['unknown_reason'] and n['approved_parameter_refs']==[] and r['assigned_engineering_owner_session'] is None and r['engineering_owner_unknown_reason'] and r['criterion_approval']==r['method_approval']=='NOT_APPROVED' and r['future_result_status']=='NOT_RUN' and r['actual_evidence_records']==[] and r['decision_approver']=='USER_SEPARATE_APPROVAL_REQUIRED',n,'UNKNOWN/null not zero;no actual engineering owner,approval,result or promotion')
        ck('profile:'+rid,r['evidence_profile']==('DOCUMENTARY_AUDIT' if i in [18,19,20,21] else 'MIXED_OR_NUMERIC_REQUIRES_SUBCLAIM_SELECTION'),r['evidence_profile'],'Pure assurance distinguished from applicable measured/model-input metrology')
        for s in r['proposed_enumerated_scope']:
            ident=s['scope_item_id'];newitem=ident in ['DEF-02-G','DEF-03-F'];retained=any(s==x for x in o['proposed_enumerated_scope'])
            ck('scope:'+ident,s['status']=='PROPOSED_NOT_APPROVED' and s['future_disposition'] is None and s['unknown_reason'] and (newitem or retained),s,'Proposed category;all144 old full items preserved;two additions undispositioned')
            scope_assess.append(dict(id=ident,description=s['description'],retained_whole_prior_item=retained,subject_assessment=assessment[0],assessment_scope='New documentary delta/retained category and limits;not exhaustive approved scope or machine conformity'))
        row_assess.append(dict(requirement_id=rid,validation_id=vid,changed=changed,assessment=assessment[0],mandatory_followup=assessment[1],scope_count=len(r['proposed_enumerated_scope'])))
        method_assess.append(dict(method_id=m['method_id'],revision=m['revision_label'],procedure=m['procedure'],assessment=assessment[0],execution='NOT_RUN',future_physical_method_revision=None))
    mappings=jd(P+'quantity_crosswalk.json')['rows'];mapping_assess=[]
    ck('mapping-universe',{r['mapping_id'] for r in mappings}==set(MAPPING_EXPECTATIONS) and len(mappings)==4,[r['mapping_id'] for r in mappings],'Four independently identified physical quantity/object definitions')
    matrix=raw('8d1b45afa84eca078a8de0a9822d6925dd87745b','requirements/verification_matrix.md').decode();met=jd(TRACE+'metrology_plan.json','45d5964786e608cdfcc656819fd6df8c77e495fe');channels={r['channel_id']:r for r in met['channels']}
    for r in mappings:
        e=MAPPING_EXPECTATIONS[r['mapping_id']]
        ck('mapping-links:'+r['mapping_id'],r['requirement_id']==e['req'] and r['validation_id']==e['val'] and r['scope_item_ids']==e['scope'] and r['channel_id']==e['channel'] and all(x in allitems for x in r['scope_item_ids']) and e['val'] in matrix and r['frozen_requirement_commit']=='8d1b45afa84eca078a8de0a9822d6925dd87745b' and r['frozen_matrix_path']=='requirements/verification_matrix.md' and r['channel_commit']=='45d5964786e608cdfcc656819fd6df8c77e495fe' and r['channel_path']==TRACE+'metrology_plan.json',r,'Independent VAL/channel/scope/object crosswalk')
        ck('mapping-unknown:'+r['mapping_id'],all(r[k] is None for k in ['value','unit','tolerance','method_revision']) and r['unknown_reason'] and r['actual_records']==[] and r['status']=='PROPOSED_MAPPING_PENDING_INDEPENDENT_RECHECK',r['definition_needed'],'No unapproved values/units/limits/method/results supplied by new mapping')
        mapping_assess.append(dict(mapping_id=r['mapping_id'],assessment=e['meaning'],actual_records=[],future_definitions_still_unknown=True))
    ck('density-distinction','насыпная плотность' in str(channels['MATERIAL']['quantities']) and 'не объявляется автоматически равной' in mappings[0]['definition_needed'] and 'границу объёма' in mappings[1]['definition_needed'] and 'Не отождествлять виды плотности' in dm[1]['procedure'],[channels['MATERIAL']['quantities'],mappings[0]['definition_needed'],mappings[1]['definition_needed']],'General density and bulk density are distinct definitions;sample mass/volume conditions remain to determine')
    ck('mass-object-distinction','изделия/дозы/остатка' in channels['MASS']['subject'] and 'отделена от дозы' in mappings[2]['definition_needed'] and 'при применимости' in mappings[3]['definition_needed'] and 'DEF-22-G' in mappings[3]['scope_item_ids'],[mappings[2]['definition_needed'],mappings[3]['definition_needed']],'Product/residue/dose/press masses not substituted;qualitative residue observation distinct from applicable numeric residue mass')
    retention=jd(P+'record_retention_plan.json');schema=jd(TRACE+'evidence_schema.json','45d5964786e608cdfcc656819fd6df8c77e495fe');required={'cycle_id','outcome','quality_flag','missing_reason','disposition','raw_event_refs','series_accounting_refs'}
    ck('retention-fields',set(retention['required_future_fields'])==set(dm[2]['required_future_cycle_fields'])==required and dm[2]['future_record_retention_ref']=='record_retention_plan.json' and retention['applies_to_method']=='DM-03/DRAFT-02',retention['required_future_fields'],'Seven future retained attempt-record fields;method and plan exact version linked')
    ck('retention-meaning',all(s in dm[2]['procedure'] for s in ['каждого цикла','неуспешные и неполные','запись цикла и его исход не удаляются','Неизвестная масса остаётся UNKNOWN']) and 'предусмотреть отсутствие результата' not in dm[2]['procedure'] and all(s in str(retention['rules']) for s in ['every attempted cycle','never permits dropping','no fictitious object,zero mass','INVALID/SIGNAL_LOSS','Derived summaries','unfiltered ledger','base records remain available']),retention['rules'],'Product/measurement may be absent;attempt/outcome/quality/reason/disposition/raw/series records never erased,including after aggregation')
    ck('retention-schema',retention['field_mapping_to_retained_schema']['missing_reason']=='evidence_schema.required_fields.unknown_reason' and retention['field_mapping_to_retained_schema']['quality_flag']=='evidence_schema.required_fields.quality_flag' and {'unknown_reason','quality_flag'}<=set(schema['required_fields']) and {'DEF-01-E','DEF-04-D','REQ-REV-22','VAL-REV-22',TRACE+'evidence_schema.json'}<=set(retention['full_series_accounting_refs']) and retention['schema_commit']=='45d5964786e608cdfcc656819fd6df8c77e495fe',retention['field_mapping_to_retained_schema'],'Semantic mapping to retained field definitions and full-series graph;not an implemented/approved executable schema')
    ck('retention-not-executed',retention['authority_status']=='PROPOSED_NOT_APPROVED' and retention['execution_status']=='NOT_RUN' and retention['actual_records']==[] and retention['retention_duration'] is None and retention['retention_duration_unknown_reason'] and set(retention['proposed_outcomes'])=={'COMPLETED','FAILED','INCOMPLETE','UNRESOLVED'},retention['retention_duration_unknown_reason'],'No actual cycle/storage execution,retention period or deletion permission invented')
    common=methods['common_protocol'];ck('DOC-common',common==oldmethods['common_protocol'] and all(t in str(common) for t in ['silence or absence is UNRESOLVED','mixed/numeric','calibration','uncertainty','no auto G1 closure']) and schema['profiles']['DOCUMENTARY_AUDIT']['field_applicability']['unit']['status']=='NOT_APPLICABLE' and 'mixed' in schema['profiles']['DOCUMENTARY_AUDIT']['field_applicability']['unit']['reason'],common,'Pure audit allowance not a measured/model-input numeric-metrology waiver;scope/method/competence/approval still required')
    force=jd(TRACE+'force_evidence_plan.json');hazards=jd(TRACE+'hazard_to_evidence.json')
    ck('TRACE-retained',all(t in dm[8]['procedure'] for t in ['H01','REQ09/VAL09/MET09','FORCE_REACTION','REQ16/17']) and 'H01' in dm[15]['procedure'] and 'FORCE_REACTION' in rows[8]['channel_ids'] and len(hazards['rows'])==20 and force['selected_method_route'] is None and force['actual_load_cases']==force['actual_records']==[] and all(r['value'] is None and r['unknown_reason'] for r in force['input_definitions']) and all(t in force['provenance_required_fields'] for t in ['source_commit','source_sha256','frame_origin_axes_units_signs','quality_and_uncertainty_basis','independent_validation_scope']),[dm[8]['procedure'],dm[15]['procedure']],'H01/REQ09/16/17 and force/reaction provenance retained;no actual reactions or selected method route')
    sources=jd(P+'source_applicability.json');oldsource=jd(OLD+'source_applicability.json',PREV);frozen=jd(REV8+'source_disposition.json','8d1b45afa84eca078a8de0a9822d6925dd87745b');source_assess=[]
    ck('source40-all',len(sources['rows'])==40 and sources['rows']==oldsource['rows']==frozen['rows'] and Counter(r['disposition'] for r in sources['rows'])==dict(TARGET_PROPOSAL=10,REFERENCE_CONTEXT=23,OPEN_SOURCE_ISSUE=7) and not sources['active_registry_modified'] and not sources['dispositions_changed'],dict(Counter(r['disposition'] for r in sources['rows'])),'All40 full rows/qualifiers unchanged;10proposal23context7issue,no source numerical adoption')
    for r in sources['rows']:
        ident=r['field_id']
        if 'MOISTURE' in ident:meaning='BP500 primary material intent;wet/dry method/basis unknown,E55/WEIMA contexts not merged.'
        elif 'POWER' in ident:meaning='Total/components contradiction remains open;no arithmetic budget or invented reconciliation.'
        elif 'PRESSURE_LITERAL' in ident:meaning='Ambiguous literal unit unresolved;no kgf assumption or derived force.'
        elif 'THROUGHPUT' in ident:meaning='Conditional up-to/material/settings rate,not guaranteed minimum or mass-throughput calculation.'
        elif 'MASS' in ident:meaning='Reference mass is not dose/product/own moving mass,CoG or actual reaction.'
        elif 'DIM' in ident or 'BUNKER' in ident or 'BRIQUETTE' in ident:meaning='Listed geometry/capacity is reference scope;not assigned axes,stroke,dose or own CAD/tolerance.'
        else:meaning='Qualified donor configuration/environment/connection context only;no selected REV execution,measured value or source maturity promotion.'
        ck('source-RAW:'+ident,r['candidate_lifecycle']=='RAW' and r['REV_realized_value'] is None and r['realized_unknown_reason'] and not r['parameter_promotion'] and not r['numerical_engineering_use'],r['disposition'],'RAW/realized null/non-engineering scope retained')
        source_assess.append(dict(field_id=ident,disposition=r['disposition'],assessment=meaning,source_locator=r['source_locator'],new_primary_PDF_certification=False))
    decisions=jd(P+'decision_register.json');olddec=jd(OLD+'decision_register.json',PREV);issues={'B01','B02','B03','SOURCE-POWER','SOURCE-PRESSURE-UNIT','SOURCE-MOISTURE-BASIS','OPERATING-COUNTRY','ENGINEERING-OWNERS','G1-FULL-REVIEW'};decision_assess=[]
    ck('nine-decisions',decisions['rows']==olddec['rows'] and {r['issue_id'] for r in decisions['rows']}==issues and decisions['BP500_primary'] and decisions['operating_country'] is None and decisions['operating_country_unknown_reason'] and not decisions['TZ_approved'] and not decisions['existing_reference_conflicts_closed'],list(issues),'Nine full prior OPEN decisions retained;BP500 primary,country unknown,previous question not reasked')
    for r in decisions['rows']:
        ck('decision:'+r['issue_id'],r['status']=='OPEN' and r['assigned_engineering_owner_session'] is None and r['due_utc'] is None and r['closure_evidence']==[] and r['blocks_G1'] and not r['closed_by_this_package'],r['closure_needed'],'Still required for dependent definition/G1 approval;R1 documentary coordination not engineering appointment')
        decision_assess.append(dict(id=r['issue_id'],status='OPEN',required_followup=r['closure_needed'],assessment='Correction of two local observations does not supply this missing approval,input or competent owner.'))
    obs=jd(P+'observations.json');ck('author-no-closure',len(obs['rows'])==2 and all(r['status']=='OPEN_PENDING_INDEPENDENT_RECHECK' and not r['closed_by_R1'] for r in obs['rows']),obs,'Author did not close own correction or inherit old review for new C')
    for name in ['definition_register','method_catalog','source_applicability','decision_register','quantity_crosswalk','record_retention_plan']:
        d=jd(P+name+'.json');ck('boundary:'+name,d['independent_output_review']=='NOT_RUN' and d['G1']=='OPEN' and d['status']=='DRAFT_NOT_APPROVED' and all(d[k] is False for k in ['requirements_approved','engineering_started','source_states_solved','physical_tests_run','execution_permission']),d['revision_id'],'Target remains unapproved/unexecuted;own new act separate')
    # Replay can faithfully reproduce an incorrect version label. Check fidelity
    # against method JSON independently instead of counting MATCH as correctness.
    markdown=raw(C,P+'definition_register.md').decode();revision_mismatches=[]
    for r,m in zip(rows,dm):
        section=markdown.split('## '+r['requirement_id']+' / ',1)[1].split('\n## ',1)[0];match=re.search(r'Документальный метод: (DM-\d+) / (DRAFT-\d+)\.',section)
        if not match or match.groups()!=(m['method_id'],m['revision_label']):revision_mismatches.append(dict(requirement_id=r['requirement_id'],method_id=m['method_id'],JSON_revision=m['revision_label'],rendered_revision=match[2] if match else None))
    ck('rendered-method-revision-consistency',not revision_mismatches,revision_mismatches,'Each rendered DM revision equals JSON controlled method identity;known new OBS03 FAIL retained')
    # Preservation is evaluated against immutable pins/trees, not a changing HEAD
    # journal hash. Old review logs permit exact-prefix append, never rewriting.
    manifests=[(P+'input_manifest.json',53),(OLD+'input_manifest.json',92),('verification/r4_force_geometry/input_manifest.json',54)]
    for mp,count in manifests:
        im=jd(mp);ck('pin-count:'+mp,len(im['inputs'])==count,len(im['inputs']),count)
        for r in im['inputs']:
            data=raw(r['commit'],r['path']);current=raw(C,r['path']);preserved=current.startswith(data) if r['path']=='reviews/cross_check_log.md' else material(current)==r['sha256'];gitok='git_blob' not in r or git('rev-parse',r['commit']+':'+r['path']).decode().strip()==r['git_blob']
            ck('pin:'+mp+':'+r['path'],material(data)==r['sha256'] and gitok and preserved,r['sha256'],'Immutable recorded source commit SHA/blob;current unchanged except lawful exact-prefix journal append')
        for path,oid in im.get('protected_trees',{}).items():
            if path!='reviews':ck('tree:'+mp+':'+path,git('rev-parse',C+':'+path).decode().strip()==oid,oid,'Entire protected tree unchanged')
            else:
                for sub,blobid in tree(oid).items():
                    previous=git('cat-file','blob',blobid);current=raw(C,'reviews/'+sub)
                    ck('review-tree:'+mp+':'+sub,current.startswith(previous) if sub=='cross_check_log.md' else current==previous,blobid,'Old exact journal prefix and unchanged other review files;new tree pinned separately')
    for path in jd(P+'input_manifest.json')['protected_trees']:
        changed=git('diff',C,'--name-only','--',path).decode().splitlines();ck('work-protected:'+path,set(changed)<={'reviews/cross_check_log.md'} and (ROOT/'reviews/cross_check_log.md').read_bytes().startswith(raw(C,'reviews/cross_check_log.md')),changed,'Only own lawful review append after exact-C source prefix')
    for commit,prefix,count in [(C,P,28),(PREV,OLD,22),('45d5964786e608cdfcc656819fd6df8c77e495fe',TRACE,25),('fe10c0bc7242fe9d2df3e571c80b4e687f731d7c','verification/r1_g1_criteria_plan_20261117/',26),('8d1b45afa84eca078a8de0a9822d6925dd87745b',REV8,25)]:
        target=jd(prefix+'review_target_manifest.json',commit);ck('target-count:'+prefix,len(target['artifacts'])==count,len(target['artifacts']),count)
        for r in target['artifacts']:
            path=r['path'];ck('sealed:'+path,material(raw(commit,path))==r['sha256']==material(raw(C,path))==sha((ROOT/path).read_bytes()),r['sha256'],'Whole old/new target artifact unchanged in C and material worktree')
        ck('manifest:'+prefix,raw(C,prefix+'review_target_manifest.json')==raw(commit,prefix+'review_target_manifest.json'),prefix,'Exact manifest unchanged')
    baseline=tree(BASE);target=tree(C);allowed={'STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','coordination/tasks/T-r1-requirements-draft-01/task.json','handoffs/T-r1-requirements-draft-01/6afb300b-1540-8191-a5c4-be1a684c20e0.md'};preserved=[];lfs=[]
    for path,oid in baseline.items():
        if path in allowed:continue
        ck('basefile:'+path,target.get(path)==oid,target.get(path),'Every nonoperational old H file unchanged,including old own act/evidence');preserved.append(path);data=git('cat-file','blob',oid)
        if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
            digest=sha((ROOT/path).read_bytes());ck('LFS:'+path,digest==material(data),digest,material(data));lfs.append(dict(path=path,sha256=digest,git_lfs_oid=material(data)))
    for path,key,count in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json','rows',44),('verification/r4_force_geometry/symbolic_20261116/interfaces.json','rows',52),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',None,84),('verification/r3_force_path/analysis/state_matrix.json',None,42)]:
        d=jd(path);elements=d[key] if key else d;ck('whole-count:'+path,len(elements)==count and raw(C,path)==raw(BASE,path),len(elements),'Whole unchanged object,not recalculated/resolved states')
    unknown=jd('verification/r4_force_geometry/symbolic_20261116/unknown_index.json');ck('RAW84',all(r['value'] is None and r['status']=='UNKNOWN' and r['source_lifecycle']=='RAW' and r['source_unknown_reason'] for r in unknown),84,'All84 RAW-null/UNKNOWN with reasons retained')
    gaps=jd(REV8+'open_gaps.json');ck('gaps15',len(gaps['rows'])==15 and all(r['status']=='OPEN' and r['value'] is None and r['assigned_owner_session'] is None and r['due_at_utc'] is None for r in gaps['rows']),15,'Additional gaps remain OPEN/unknown,not appointments/deadlines')
    journal=raw(C,'reviews/cross_check_log.md').decode();historical=jd('verification/r5_r4_force_geometry_symbolic_review/independent_after_record.json');closure=jd('verification/r5_r4_symbolic_obs01_recheck/independent_final.json')
    ck('history-fourFAIL',historical['counts']=={'PASS':2422,'FAIL':4},historical['counts'],'Four old FAIL preserved,not rerun/recertified')
    ck('history-OBS01-exact',closure['OBS01']=='CLOSED_DOCUMENTARY_EXACT_C' and closure['target_C']=='beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe',closure['target_C'],'Old exact-C closure only')
    for t in ['material_contract_consecutive_rejections: 2','REJECT_WITH_BLOCKER','validity: STALE','R5-TZ-B01','R5-TZ-B02','R5-TZ-B03','review_id: REV-R5-G1-DEFINITION-OUTPUT-01-001']:ck('history:'+t,t in journal,t,'Original review/findings/counter history retained,not overwritten by recheck')
    original_checks=[x for x in checks if x['id'].startswith(('mapping-','density-','mass-object-','retention-'))];unexpected=[x for x in checks if x['result']=='FAIL' and x['id']!='rendered-method-revision-consistency'];closure_ok=not any(x['result']=='FAIL' for x in original_checks)
    decisions_obs={k:dict(status='CLOSED_DOCUMENTARY_EXACT_C' if closure_ok else 'OPEN',exact_C=C,basis=v) for k,v in [('R5-DEF-OBS-01','Four explicit quantity mappings and new DEF02G/03F preserve distinct density/mass objects and UNKNOWN definitions.'),('R5-DEF-OBS-02','DM03/retention proposal preserves every attempt/outcome/quality/reason/disposition/raw/series record,including absent product/measurement and derived subsets.')]}
    finding=dict(id='R5-DEF-OBS-03',status='OPEN',severity='DOCUMENTARY_VERSION_INCONSISTENCY',blocking_preliminary_DRAFT=False,blocks_controlled_method_identity=True,reviewed_commit=C,description='definition_register.md renders DM02 andDM03 asDRAFT-01 although method_catalog.json defines DRAFT-02. render_register.py hardcodes /DRAFT-01. Six MATCH reproduce this inconsistency;they do not validate revision fidelity.',evidence=revision_mismatches,required_action='Author must derive displayed DM revision from the matching method row,regenerate affected documentary outputs and request exact-C review of the correction. Do not change old snapshots or treat the current summary as an approved method.')
    for section in ['4','5','6']:checks.append(dict(id='physical-section-'+section,result='NOT_RUN',observed='No numerical/physical engineering/CAD/test execution;42states unsolved',expected='Actual inputs and separate authorization required'))
    result=dict(reviewed_commit=C,request_H=H,actual_session_id=SESSION,checked_at_utc=datetime.now(timezone.utc).isoformat(),counts=dict(Counter(x['result'] for x in checks)),observation_decisions=decisions_obs,new_findings=[finding] if revision_mismatches else [],row_assessments=row_assess,scope_assessments=scope_assess,method_assessments=method_assess,quantity_mapping_assessments=mapping_assess,semantic_cases=[dict(case=c,documentary_conclusion=v) for c,v in SEMANTIC_CASES],semantic_cases_are='Reasoning on a proposed documentary contract;not actual machine records or tests of an implemented evaluator',source_assessments=source_assess,decision_assessments=decision_assess,retention_assessment='Proposed full-attempt ledger with semantic field mapping;no executable schema,actual series,retention period or storage policy approved.',preserved_baseline_files=preserved,hydrated_LFS=lfs,checks=checks,failures=[x for x in checks if x['result']=='FAIL'],unexpected_failures=unexpected,author172_or_previous4171_as_new_proof=False,old_own_acts_recertified=False,overall_verdict='WARNING',preliminary_DRAFT_usable=True,G1_sufficient=False,physical_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'},G1='OPEN',W02='NO_GO',physical_READY='NO_GO',source_states_solved=False)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(counts=result['counts'],observations=decisions_obs,new_findings=result['new_findings'],baseline_files=len(preserved),LFS=len(lfs),unexpected_failures=unexpected),ensure_ascii=False));return bool(result['failures'])
if __name__=='__main__':raise SystemExit(main())
