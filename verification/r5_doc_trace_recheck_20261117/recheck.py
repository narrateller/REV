"""Independent exact-C documentary recheck; no author verifier or engineering run.

Explicit policy cases below are semantic analyses of the proposed contract, not
machine observations or tests of an implemented evidence evaluator.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse
import hashlib
import json
import re
import subprocess
import yaml

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
REL='verification/r1_g1_observation_revision_20261117/'
OLDREL='verification/r1_g1_criteria_plan_20261117/'
C='45d5964786e608cdfcc656819fd6df8c77e495fe'
H='2b99776187345729f1c3e177d0e5ed83e1239b07'
MAIN='b8485a93b7ced741261e7979f9438bad8590d368'
BASE='4bde3134e15b4d7c60ab382883ee6e1c40e7a91b'
PRE='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'
CLAIM='coordination/claims/T-r5-g1-supplement-output-review-01.json'
AMEND='coordination/scope_amendments/T-r5-g1-supplement-output-review-01/DOC01-TRACE02-REVISION-01.json'
NEW_NAMES={'criterion_cards.json','metrology_plan.json','hazard_to_evidence.json','evidence_schema.json','force_evidence_plan.json','criterion_cards.md','metrology_plan.md','safety_plan.md','document_assurance.md','evidence_schema.md','force_evidence_plan.md','execution_board.md'}
OLD_NAMES={'evaluation_rules.json','normative_applicability_plan.json','normative_plan.md','source_actions.json','source_actions.md'}
PURE={18,19,20,21}
LOAD_FIELDS={'load_input_provenance','frame_and_sign_conventions','load_or_reaction_method_route','validated_output_scope','uncertainty_or_model_error_basis'}
ASSURANCE={
 'scope completeness':({'approved_scope_revision','enumerated_scope_items','item_dispositions','justified_exclusions','missing_items'},'An itemized agreed universe and dispositions prevent a count or missing scope from being accepted as completeness.'),
 'source authority':({'primary_source_locator','edition_and_revision','authority_basis','applicability_scope','contradictions'},'Authority/edition/applicability must be justified and contradictory evidence retained; a source filename alone is insufficient.'),
 'revision control':({'commit','artifact_sha256','input_revision_refs','change_and_STALE_assessment'},'Exact content and impact/recheck trace prevent inheritance of an old PASS by changed evidence.'),
 'reviewer competence':({'actual_reviewer_session','relevant_competence_basis','target_coauthorship_disclosure','upstream_scope','review_authorization'},'Actual competence/independence/authority must be justified; model label and check counts certify neither.')
}

def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def blob(c,p):return git('show',f'{c}:{p}')
def jd(p,c=C):return json.loads(blob(c,p))
def sha(b):return hashlib.sha256(b).hexdigest()
def materialized(b):return re.search(rb'oid sha256:([0-9a-f]{64})',b).group(1).decode() if b.startswith(b'version https://git-lfs.github.com/spec/v1') else sha(b)
def tree(c):return {p:m.split()[2] for line in git('ls-tree','-rz','--full-tree',c).decode().split('\0') if line for m,p in [line.split('\t',1)]}
def diffkeys(a,b):return {k for k in set(a)|set(b) if k not in a or k not in b or a[k]!=b[k]}
def rid(n,p='REQ'):return f'{p}-REV-{n:02d}'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=HERE/'independent_results.json');arg=ap.parse_args();checks=[];now=datetime.now(timezone.utc)
    def check(i,ok,actual,expected):checks.append(dict(id=i,result='PASS' if ok else 'FAIL',observed=actual,expected=expected))
    claim=jd(CLAIM,MAIN);amend=jd(AMEND,MAIN)
    check('AUTH-accepted-exact-scope',amend['status']==claim['status']=='ACCEPTED_MAIN' and amend['owner_session']==claim['owner_session']==SESSION and amend['target_C']==C and amend['request_H']==H,dict(owner=claim['owner_session'],C=amend['target_C'],H=amend['request_H']),'Explicit accepted same-task amendment authorizes exact new target')
    check('AUTH-base-claim-hash',sha(blob(MAIN,CLAIM))==amend['base_claim_sha256'] and blob(MAIN,CLAIM)==blob(amend['base_claim_main'],CLAIM) and claim['target_C']==PRE,sha(blob(MAIN,CLAIM)),amend['base_claim_sha256'])
    check('AUTH-original-live-lease',claim['lease_expires_at']==amend['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and now<datetime.fromisoformat(claim['lease_expires_at']) and not amend['new_lease'] and not amend['lease_extension'],dict(deadline=claim['lease_expires_at'],UTC=now.isoformat()),'Original live deadline, no new/extended/transferred lease')
    for p in [CLAIM,AMEND]:check('AUTH-current-immutable:'+p,(ROOT/p).read_bytes()==blob(MAIN,p),sha((ROOT/p).read_bytes()),sha(blob(MAIN,p)))
    check('AUTH-request-parent',git('rev-parse',H+'^').decode().strip()==C,H,'Exact request H directly follows exact C')
    manifest_path=REL+'review_target_manifest.json';manifest=jd(manifest_path)
    check('AUTH-manifest',sha(blob(C,manifest_path))==amend['target_manifest_sha256'] and SESSION not in manifest['target_author_sessions'],dict(hash=sha(blob(C,manifest_path)),authors=manifest['target_author_sessions']),'Accepted exact manifest, reviewer not author')
    check('TARGET-25',len(manifest['artifacts'])==25,len(manifest['artifacts']),25)
    for a in manifest['artifacts']:check('TARGET:'+a['path'],sha(blob(C,a['path']))==a['sha256'] and (ROOT/a['path']).read_bytes()==blob(C,a['path']),sha(blob(C,a['path'])),a['sha256'])
    pins=jd(REL+'input_manifest.json')['inputs'];check('INPUT-22',len(pins)==22,len(pins),22)
    for p in pins:check('INPUT:'+p['path'],materialized(blob(p['commit'],p['path']))==p['sha256'] and git('rev-parse',p['commit']+':'+p['path']).decode().strip()==p['git_blob'],materialized(blob(p['commit'],p['path'])),p['sha256'])
    bundle=jd(REL+'active_bundle.json');entries=bundle['artifacts'];lookup={r['logical_name']:r for r in entries}
    check('RESOLVER-17-unique',len(entries)==len(lookup)==17 and set(lookup)==NEW_NAMES|OLD_NAMES,sorted(lookup),sorted(NEW_NAMES|OLD_NAMES))
    for name,row in lookup.items():
        expected=(REL if name in NEW_NAMES else OLDREL)+name
        check('RESOLVER:'+name,row['path']==expected and materialized(blob(C,expected))==row['sha256'] and (ROOT/expected).read_bytes()==blob(C,expected),row,'Exact independent logical-name/path/hash mapping')
        check('RESOLVER-origin:'+name,row['origin']==('AMENDED_DRAFT_OUTPUT' if name in NEW_NAMES else 'UNCHANGED_PREDECESSOR_SCOPE_ONLY') and (name in NEW_NAMES or row['source_commit']==PRE and blob(C,expected)==blob(PRE,expected)),row['origin'],'12 new outputs plus5 unchanged predecessor-scoped outputs; resolver is13th output')
    oldcards=jd(OLDREL+'criterion_cards.json',PRE)['rows'];cards=jd(REL+'criterion_cards.json')['rows'];oldmet=jd(OLDREL+'metrology_plan.json',PRE);met=jd(REL+'metrology_plan.json');oldhaz=jd(OLDREL+'hazard_to_evidence.json',PRE)['rows'];haz=jd(REL+'hazard_to_evidence.json')['rows'];channels={r['channel_id']:r for r in met['channels']};oldchannels={r['channel_id']:r for r in oldmet['channels']}
    check('ROWS-all-sets',len(cards)==22 and len(met['rows'])==22 and len(haz)==20 and len(channels)==12 and [r['requirement_id'] for r in cards]==[rid(n) for n in range(1,23)] and [r['validation_id'] for r in met['rows']]==[rid(n,'VAL') for n in range(1,23)],[len(cards),len(met['rows']),len(haz),len(channels)],'22cards/22metrology/20hazards/12channels, exact original IDs')
    card_assess=[];met_assess=[];unchanged_cards=[];unchanged_met=[]
    for n,(old,c,om,m) in enumerate(zip(oldcards,cards,oldmet['rows'],met['rows']),1):
        relevant=n in PURE or n==9
        if not relevant:
            check(f'CARD-exact-{n:02d}',c==old,c['requirement_id'],'Whole unchanged card object');unchanged_cards.append(n)
            cj='Entire predecessor card unchanged; no new criterion or physical assurance inferred.'
        elif n==9:
            check('TRACE-CARD09-delta',diffkeys(old,c)=={'measurement_channel_ids','mandatory_evidence_fields'} and c['measurement_channel_ids']==old['measurement_channel_ids']+['FORCE_REACTION'] and c['mandatory_evidence_fields'][:len(old['mandatory_evidence_fields'])]==old['mandatory_evidence_fields'] and set(c['mandatory_evidence_fields'])-set(old['mandatory_evidence_fields'])==LOAD_FIELDS,c['mandatory_evidence_fields'],'Preserve original criterion and add explicit load/method/frame/error provenance')
            cj='FORCE_REACTION and provenance fields close the report-name-only trace gap without defining numerical loads or verified results.'
        else:
            allowed={'field_applicability','objective_scope_revision','objective_scope_unknown_reason','range_unknown_reason'}
            check(f'DOC-CARD{n}-delta',diffkeys(old,c)==allowed and c['objective_scope_revision'] is None and bool(c['objective_scope_unknown_reason']),sorted(diffkeys(old,c)),sorted(allowed))
            check(f'DOC-CARD{n}-NA',set(c['field_applicability'])=={'threshold_value','tolerance','range','uncertainty_acceptance_limit'} and all(x['status']=='NOT_APPLICABLE' and x['reason'] for x in c['field_applicability'].values()),c['field_applicability'],'Field reasons limit N_A to pure categorical audit; objective scope still unknown')
            cj='Pure objective completeness needs no fabricated numerical threshold; enumerated scope remains explicitly UNKNOWN, not waived.'
        check(f'CARD-boundary-{n}',c['threshold_value'] is None and c['tolerance'] is None and c['range'] is None and c['engineering_owner_session'] is None and c['engineering_due_utc'] is None and c['physical_validation_status']=='NOT_RUN' and not c['G1_closed'] and c['active_parameter_refs']==[],c['physical_validation_status'],'No limits, engineering assignment, validation or promotion')
        card_assess.append(dict(requirement_id=rid(n),changed=relevant,own_assessment=cj,physical_result='NOT_RUN'))
        hasdoc='DOCUMENT' in om['channel_ids']
        if not hasdoc:
            check(f'MET-exact-{n:02d}',m==om,m['plan_id'],'Whole no-DOCUMENT row unchanged');unchanged_met.append(n);mj='No DOCUMENT component; entire numerical observation/method/context row unchanged.'
        else:
            check(f'DOC-MET{n}-boundary','only to document assurance' in m['applicability_boundary'] and 'other applicable channels retain unknown' in m['applicability_boundary'],m['applicability_boundary'],'No global N_A from DOCUMENT membership')
            if n in PURE:
                allowed={'documentary_assurance_ref','applicability_boundary','required_context','field_applicability','sample_count_unknown_reason','required_document_scope','document_scope_unknown_reason'}
                check(f'DOC-MET{n}-delta',diffkeys(om,m)==allowed,sorted(diffkeys(om,m)),sorted(allowed))
                check(f'DOC-MET{n}-method-scope',m['field_applicability']['method_revision']['status']=='APPLICABLE_UNKNOWN' and m['method_revision'] is None and m['required_document_scope'] is None and m['document_scope_unknown_reason'] and {'audit_method_revision','documentary_scope_revision','source_authority_basis','reviewer_competence_record','missing_data_rules'}<=set(m['required_context']),m['required_context'],'Method/scope/authority/competence remain applicable and unresolved')
                check(f'DOC-MET{n}-numerical-NA',all(m['field_applicability'][k]['status']=='NOT_APPLICABLE' and m['field_applicability'][k]['reason'] for k in ['instrument_model','range','resolution','uncertainty_limit','sample_count']),m['field_applicability'],'Only instrument/range/resolution/numeric uncertainty/measurement series waived for pure audit')
                mj='Pure audit context now uses controlled method, itemized scope, authority/competence and missing-item rules; numerical metrology is inapplicable only for this evidence kind.'
            else:
                allowed={'documentary_assurance_ref','applicability_boundary'}|({'channel_ids','evidence_fields','load_evidence_plan_ref'} if n==9 else set())
                check(f'DOC-MET{n}-mixed-delta',diffkeys(om,m)==allowed,sorted(diffkeys(om,m)),sorted(allowed))
                check(f'DOC-MET{n}-mixed-preserve',all(m[k]==om[k] for k in ['required_context','method_revision','instrument_model','range','resolution','uncertainty_limit','sample_count','sample_count_unknown_reason']) and 'field_applicability' not in m,m['required_context'],'Mixed numeric/calibration/time/uncertainty unknowns are not converted to N_A')
                mj='Mixed DOCUMENT assurance is local to document subclaims; all old measurement/calibration/time/uncertainty requirements remain.'
                if n==9:
                    check('TRACE-MET09-force',m['channel_ids']==om['channel_ids']+['FORCE_REACTION'] and m['load_evidence_plan_ref']==REL+'force_evidence_plan.json#LOAD-REACTION-PROVENANCE-01' and set(m['evidence_fields'])-set(om['evidence_fields'])==LOAD_FIELDS,m['evidence_fields'],'H01/REQ09/MET09 force provenance trace, no measured force')
                    mj+=' Force/reaction route and provenance are explicit future requirements.'
        check(f'MET-not-executed-{n}',not m['execution_permission'] and m['execution_status']=='NOT_RUN' and m['actual_records']==[] and m['engineering_owner_session'] is None,m['execution_status'],'No actual records or authorized method execution')
        met_assess.append(dict(plan_id=m['plan_id'],document_component=hasdoc,pure_audit=n in PURE,own_assessment=mj))
    check('CARD17-MET12-unchanged',len(unchanged_cards)==17 and len(unchanged_met)==12,dict(cards=unchanged_cards,metrology=unchanged_met),'17 other cards and12 no-DOCUMENT rows exact unchanged')
    doc=channels['DOCUMENT'];check('DOC-channel-assurance',doc['uncertainty_budget_terms']==[] and doc['evidence_kind']=='PROCEDURAL_DOCUMENTARY_ASSURANCE' and doc['field_applicability']['method_revision']['status']=='APPLICABLE_UNKNOWN' and doc['procedural_assurance_status']=='NOT_RUN',doc['proposed_method_class'],'Qualitative assurance separate from numerical uncertainty, controlled audit method still required')
    assurance_assess=[]
    for r in doc['procedural_assurance_criteria']:
        expected,reason=ASSURANCE[r['dimension']];check('DOC-assurance:'+r['dimension'],set(r['required_evidence_fields'])==expected and r['status']=='NOT_RUN' and r['actual_evidence']==[],r['required_evidence_fields'],sorted(expected));assurance_assess.append(dict(dimension=r['dimension'],own_assessment=reason))
    check('DOC-four-dimensions',{r['dimension'] for r in doc['procedural_assurance_criteria']}==set(ASSURANCE),[r['dimension'] for r in doc['procedural_assurance_criteria']],'Scope/authority/revision/competence, no evaluated numeric budget')
    for field in ['instrument_model','range','resolution','calibration_evidence','uncertainty_budget_terms','uncertainty_budget_evaluated']:check('DOC-field:'+field,doc['field_applicability'][field]['status']=='NOT_APPLICABLE' and bool(doc['field_applicability'][field]['reason']),doc['field_applicability'][field],'Field-specific reason for pure categorical audit')
    channel_assess=[]
    for cid,old in oldchannels.items():
        if cid!='DOCUMENT':check('CHANNEL-exact:'+cid,channels[cid]==old,cid,'Whole original non-DOCUMENT channel unchanged')
        channel_assess.append(dict(channel_id=cid,own_assessment='Procedural categorical assurance correctly specialized; no measured subclaim exemption.' if cid=='DOCUMENT' else 'Whole prior channel object preserved; no new exemption or measurement assurance.'))
    check('CHANNEL12-set',set(channels)==set(oldchannels)|{'FORCE_REACTION'},sorted(channels),'Old11 plus proposed FORCE_REACTION')
    force=jd(REL+'force_evidence_plan.json');fc=channels['FORCE_REACTION'];channel_assess.append(dict(channel_id='FORCE_REACTION',own_assessment='Plausible proposed evidence class, route UNKNOWN; direct measurement and model prediction have separate obligations, neither confirms actual reactions here.'))
    check('TRACE-forcechannel-unknown',fc['route_selection'] is None and fc['verification_status']=='NOT_RUN' and not fc['uncertainty_budget_evaluated'] and all(fc[k] is None for k in ['instrument_model','method_revision','range','resolution','calibration_evidence']) and {q['unit'] for q in fc['quantities']}=={'N','N*m'},fc['field_applicability_rule'],'Units only, no values/route/instrument/model selected; no blanket N_A')
    hazard_assess=[]
    for n,(old,h) in enumerate(zip(oldhaz,haz),1):
        if n!=1:
            check(f'HAZARD-exact-H{n:02d}',old==h,h['hazard_id'],'Whole other19 hazard objects unchanged');reason='Whole original scenario/links/evidence/UNKNOWN unchanged; no new safety validation.'
        else:
            allowed={'requirement_ids','validation_ids','metrology_plan_ids','load_evidence_plan_ref','acceptance_evidence'}
            check('TRACE-H01-delta',diffkeys(old,h)==allowed and h['source_cells']==old['source_cells'] and h['requirement_ids']==old['requirement_ids']+['REQ-REV-09'] and h['validation_ids']==old['validation_ids']+['VAL-REV-09'] and h['metrology_plan_ids']==['MET-VAL-REV-09','MET-VAL-REV-16','MET-VAL-REV-17'] and h['load_evidence_plan_ref']==met['rows'][8]['load_evidence_plan_ref'],h,'Preserve full source cells and REQ16/17; direct REQ09/VAL09/MET09/force-plan trace added')
            check('TRACE-H01-acceptance',h['acceptance_evidence'][:len(old['acceptance_evidence'])]==old['acceptance_evidence'] and set(h['acceptance_evidence'])-set(old['acceptance_evidence'])=={'own_lifting_load_case_definition','load_reaction_provenance_and_applicable_validation'},h['acceptance_evidence'],'Original evidence retained plus own load-case/provenance definition, no current case')
            reason='Direct lifting/stability structural-case trace now exists; preservation of original source/REQ16/17 avoids losing earlier handling obligations.'
        check(f'HAZARD-unproven-{n}',h['risk_level'] is None and h['safety_performance_level'] is None and not h['safe_state_verified'] and not h['completeness_proven'] and h['verification_status']=='NOT_RUN',h['verification_status'],'No PL/SIL/risk/effectiveness/real safe state proved')
        hazard_assess.append(dict(hazard_id=h['hazard_id'],own_assessment=reason))
    required_inputs={'assembly_mass','centre_of_gravity','lifting_interfaces','supports_and_restraints','pose_and_environment','load_directions_and_time','materials_and_connections','geometry_revision','rigging_definition','acceptance_limits'}
    check('TRACE-force-inputs',{r['id'] for r in force['input_definitions']}==required_inputs and all(all(r[k] is None for k in ['value','source_record','source_commit','source_sha256']) and r['unknown_reason'] for r in force['input_definitions']),force['input_definitions'],'All actual masses/CoG/interfaces/supports/materials/geometry/case/rigging/criteria UNKNOWN with reasons')
    provenance={'source_record_id','source_kind','author_or_operator','actual_scope_and_configuration','input_or_output_role','method_revision','source_commit','source_sha256','frame_origin_axes_units_signs','point_or_interface_id','timebase_and_alignment_if_dynamic','quality_and_uncertainty_basis','independent_validation_scope','authorization_ref'}
    check('TRACE-provenance',set(force['provenance_required_fields'])==provenance,force['provenance_required_fields'],'Origin/version/hash/configuration/point/frame/unit/sign/time/quality/error/validation/authority required')
    check('TRACE-plan-linked',force['requirement_ids']==['REQ-REV-09','REQ-REV-16','REQ-REV-17'] and force['metrology_plan_ids']==haz[0]['metrology_plan_ids'] and force['channel_id']=='FORCE_REACTION' and force['selected_method_route'] is None,force['metrology_plan_ids'],'Consistent H01/09/16/17 and force class; route not selected')
    routes={r['route_id']:r for r in force['route_specs']};check('TRACE-two-routes',set(routes)=={'DIRECT_MEASUREMENT','MODEL_PREDICTION'},list(routes),'Two alternatives, not two performed analyses')
    route_assess=[]
    for name,r in routes.items():
        check('TRACE-route-unknown:'+name,not r['execution_permission'] and r['execution_status']=='NOT_RUN' and all(x['value'] is None and x['unknown_reason'] for x in r['required'].values()),list(r['required']),'No approved method, selected inputs, execution or results')
        reason='Direct measurement needs identified calibrated channels, locations/axes/ranges/uncertainty/time/quality; all remain UNKNOWN.' if name=='DIRECT_MEASUREMENT' else 'Model prediction needs actual inputs/boundaries/code/solver/convergence/balances/discrepancy/independent validation; its prediction alone is not an actual reaction.'
        route_assess.append(dict(route=name,own_assessment=reason))
    check('TRACE-model-not-actual',routes['MODEL_PREDICTION']['evidence_kind']=='MODEL_PREDICTION_NOT_ACTUAL_REACTION_CONFIRMATION' and any('does not by itself confirm actual reactions' in s for s in force['interpretation_rules']),routes['MODEL_PREDICTION']['evidence_kind'],'Explicit prediction versus physical-confirmation boundary')
    check('TRACE-no-results',force['actual_load_cases']==[] and force['actual_records']==[] and force['engineering_owner_session'] is None and not force['execution_permission'] and force['execution_status']=='NOT_RUN' and all(r['value'] is None and r['unknown_reason'] for r in force['future_result_fields'].values()),force['future_result_fields'],'No added physical load case, result or engineering assignment')
    schema=jd(REL+'evidence_schema.json');profiles=schema['profiles'];common=set(schema['required_fields']);measurement={'material_revision','instrument_id','calibration_ref','timebase_ref','quantity','unit','measured_value','uncertainty'}
    check('SCHEMA-profile-set',set(profiles)=={'DOCUMENTARY_AUDIT','NUMERIC_MEASUREMENT','MIXED','MODEL_PREDICTION'},list(profiles),'Conditional actual evidence-kind selection')
    check('SCHEMA-method-common',{'method_revision','criterion_revision','program_revision','quality_flag','unknown_reason','raw_data_sha256','authorization_ref'}<=common,sorted(common),'Method/criterion/quality/authority are never globally N_A')
    check('SCHEMA-measurement-required',set(profiles['NUMERIC_MEASUREMENT']['required_fields'])==measurement,profiles['NUMERIC_MEASUREMENT'],'Numeric observations require all applicable measurement/calibration/uncertainty fields')
    check('SCHEMA-mixed-no-bypass',profiles['MIXED']['required_profiles']==['DOCUMENTARY_AUDIT','NUMERIC_MEASUREMENT'] and 'cannot waive calibration/uncertainty' in profiles['MIXED']['scope'] and 'actual evidence kind' in schema['profile_selection_rule'] and 'not just by REQ label' in schema['profile_selection_rule'],schema['profile_selection_rule'],'Measured subclaim cannot use pure audit exemption even under an objective REQ label')
    check('SCHEMA-model-input-calibration','measured inputs retain their own required calibration/uncertainty' in profiles['MODEL_PREDICTION']['scope'] and {'load_evidence_plan_ref','model_and_input_provenance','model_error_and_validation_scope'}==set(profiles['MODEL_PREDICTION']['required_fields']),profiles['MODEL_PREDICTION'],'Pure computational output can justify instrument N_A; measured input metrology remains applicable')
    check('SCHEMA-unknown-blocks','field/profile-specific reason' in schema['NA_rule'] and 'applicable unknown remains null' in schema['NA_rule'] and 'blocks dependent PASS' in schema['NA_rule'],schema['NA_rule'],'N_A not a substitute for unknown applicable data')
    check('SCHEMA-no-actual',schema['actual_records']==[] and schema['all_VAL_TEST_status']=='NOT_RUN' and schema['template']['measured_value'] is None and schema['template']['uncertainty'] is None and schema['template']['quality_flag']=='NOT_MEASURED',schema['template'],'Conditional template, no measured/model record fabricated')
    policy_cases=[
      dict(id='DOC-CASE-01',scenario='Pure categorical audit with missing controlled method.',own_conclusion='APPLICABLE_UNKNOWN; dependent PASS blocked, not N_A.',basis='Common method_revision plus DOCUMENT APPLICABLE_UNKNOWN.'),
      dict(id='DOC-CASE-02',scenario='Pure audit with no agreed enumerated scope.',own_conclusion='Scope UNKNOWN; completeness PASS unavailable, no numerical series invented.',basis='required_document_scope/objective_scope_revision null with reasons and itemized completeness rule.'),
      dict(id='DOC-CASE-03',scenario='An evidence item under REQ18 contains a real measured subclaim.',own_conclusion='Select NUMERIC_MEASUREMENT or MIXED by actual content; REQ label cannot waive metrology.',basis='Actual evidence-kind profile selector plus MIXED required components.'),
      dict(id='DOC-CASE-04',scenario='Mixed documentary and numerical item lacks calibration/uncertainty.',own_conclusion='Applicable numerical data remain UNKNOWN; DOCUMENT N_A cannot give PASS.',basis='Mixed required_profiles and unchanged numeric fields/context.'),
      dict(id='TRACE-CASE-05',scenario='A future computational force output has no actual validation.',own_conclusion='A model prediction does not confirm actual reactions; no current run/result exists.',basis='MODEL_PREDICTION_NOT_ACTUAL_REACTION_CONFIRMATION and empty results.'),
      dict(id='TRACE-CASE-06',scenario='A computational prediction depends on measured inputs without calibration.',own_conclusion='Input metrology remains required/UNKNOWN even when output instrument is legitimately N_A.',basis='MODEL_PREDICTION scope explicitly retains measured-input calibration/uncertainty.'),
      dict(id='TRACE-CASE-07',scenario='Only report filename, donor gross mass, literal pressure or command signal is supplied.',own_conclusion='Insufficient force/reaction/retention provenance; no route or actual reaction may be inferred.',basis='Explicit interpretation rules plus actual scope/hash/frame/point/time/quality required.'),
      dict(id='SCHEMA-CASE-08',scenario='Invalid observation or a known valid violation coexists with other unknowns.',own_conclusion='Retain invalid/unknown and valid violation separately; neither is silently converted into PASS.',basis='Unchanged evaluation_rules and force interpretation rule; no actual scenario executed.')
    ]
    check('TRACE-bad-shortcuts','report filename' in force['interpretation_rules'][0] and any('Brochure mass, literal pressure or command signal' in s for s in force['interpretation_rules']),force['interpretation_rules'],'No invalid source-to-reaction inference')
    # Preservation compares exact immutable predecessor inputs; own old judgments are not recertified.
    for path,n in [(OLDREL+'review_target_manifest.json',26),('verification/r1_requirements_draft_20261117/review_target_manifest.json',25)]:
        rows=jd(path)['artifacts'];check('PRESERVE-manifest-count:'+path,len(rows)==n,len(rows),n)
        for r in rows:check('PRESERVE-old-artifact:'+r['path'],sha(blob(C,r['path']))==r['sha256'] and (ROOT/r['path']).read_bytes()==blob(C,r['path']),sha(blob(C,r['path'])),r['sha256'])
    oldmanifest=jd('verification/r4_force_geometry/input_manifest.json');check('PRESERVE-54pins-12trees',len(oldmanifest['inputs'])==54 and len(oldmanifest['protected_trees'])==12,[len(oldmanifest['inputs']),len(oldmanifest['protected_trees'])],[54,12])
    for r in oldmanifest['inputs']:check('PRESERVE-old-pin:'+r['path'],materialized(blob(r['commit'],r['path']))==r['sha256'] and materialized(blob(C,r['path']))==r['sha256'],materialized(blob(C,r['path'])),r['sha256'])
    for path in oldmanifest['protected_trees']:
        check('PRESERVE-tree:'+path,git('rev-parse',C+':'+path)==git('rev-parse',BASE+':'+path),git('rev-parse',C+':'+path).decode().strip(),'Same entire protected tree as authorized working base, including historical review content')
        changed=git('diff',C,'--name-only','--',path).decode().splitlines();check('PRESERVE-current-tree:'+path,set(changed)<={'reviews/cross_check_log.md'} and (ROOT/'reviews/cross_check_log.md').read_bytes().startswith(blob(C,'reviews/cross_check_log.md')),changed,'No current protected change except own append after exact history prefix')
    tc,tb=tree(C),tree(BASE);allowed={'STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','coordination/tasks/T-r1-requirements-draft-01/task.json','handoffs/T-r1-requirements-draft-01/6afb300b-1540-8191-a5c4-be1a684c20e0.md'};preserved=[];lfs=[]
    for path,oid in tb.items():
        if path in allowed:continue
        check('PRESERVE-base-file:'+path,tc.get(path)==oid,tc.get(path),oid);preserved.append(dict(path=path,git_blob=oid,unchanged=tc.get(path)==oid))
    for path in tc:
        data=blob(C,path)
        if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
            digest=sha((ROOT/path).read_bytes());check('PRESERVE-LFS:'+path,digest==materialized(data),digest,materialized(data));lfs.append(dict(path=path,sha256=digest,git_lfs_oid=materialized(data)))
    for path,k,n in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json','rows',44),('verification/r4_force_geometry/symbolic_20261116/interfaces.json','rows',52),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',None,84),('verification/r3_force_path/analysis/state_matrix.json',None,42)]:
        d=jd(path);rows=d[k] if k else d;check('PRESERVE-full:'+path,len(rows)==n and blob(C,path)==blob(BASE,path) and (ROOT/path).read_bytes()==blob(C,path),dict(count=len(rows),sha256=sha(blob(C,path))),f'{n} full unchanged objects, not calculated/physically verified')
    unknown=jd('verification/r4_force_geometry/symbolic_20261116/unknown_index.json');check('PRESERVE84-RAW-null',all(x['status']=='UNKNOWN' and x['source_lifecycle']=='RAW' and x['value'] is None and x['source_unknown_reason'] for x in unknown),len(unknown),'84 unchanged UNKNOWN/RAW/null with reasons')
    gap=jd('verification/r1_requirements_draft_20261117/open_gaps.json')['rows'];check('PRESERVE15-gaps',len(gap)==15 and all(x['status']=='OPEN' and x['value'] is None for x in gap),len(gap),'All15 gaps remain OPEN/null')
    hist=jd('verification/r5_r4_force_geometry_symbolic_review/independent_after_record.json');closure=jd('verification/r5_r4_symbolic_obs01_recheck/independent_final.json');check('PRESERVE-history-fourFAIL',hist['counts']=={'PASS':2422,'FAIL':4},hist['counts'],'Original four FAIL preserved, no recertification/reset');check('PRESERVE-OBS01',closure['target_C']=='beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe' and closure['OBS01']=='CLOSED_DOCUMENTARY_EXACT_C',closure['OBS01'],'Old exact-C documentary closure only')
    journal=blob(C,'reviews/cross_check_log.md').decode()
    for t in ['material_contract_consecutive_rejections: 2','REJECT_WITH_BLOCKER','validity: STALE','R5-TZ-B01','R5-TZ-B02','R5-TZ-B03']:check('PRESERVE-history:'+t,t in journal,t,'Historical counters/findings not reset')
    raw=yaml.safe_load(blob(C,'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml'));params=[p for d in raw['domains'].values() for p in d.values()];check('PRESERVE40-RAW',len(params)==40 and all(p['lifecycle']=='RAW' and p['verifier'] is None and p['calculation'] is None for p in params),len(params),'No RAW promotion or engineering use')
    for name in ['criterion_cards.json','metrology_plan.json','hazard_to_evidence.json','evidence_schema.json','force_evidence_plan.json','active_bundle.json']:
        d=jd(REL+name);check('BOUNDARY:'+name,d['new_review']=='NOT_RUN' and d['G1']=='OPEN' and not d['requirements_approved'] and not d['source_states_solved'] and not d['engineering_calculations_run'] and not d['physical_tests_run'],d['predecessor_review_applicability_to_this_revision'],'Old act remains exact-predecessor-only, new revision has no automatic review/approval')
    check('REPLAY13',json.loads((HERE/'renderer_replay.json').read_text())['all13_match'],'13 documentary outputs MATCH','Reproducibility only; not author332 or predecessor4117 as new independent review')
    docfail=[x['id'] for x in checks if x['result']=='FAIL' and x['id'].startswith(('DOC-','SCHEMA-'))];tracefail=[x['id'] for x in checks if x['result']=='FAIL' and x['id'].startswith('TRACE-')];failures=[x for x in checks if x['result']=='FAIL']
    decisions={'R5-G1-DOC-01':dict(status='OPEN' if docfail else 'CLOSED_DOCUMENTARY_EXACT_C',exact_C=C,basis='Pure procedural assurance with applicable method/scope retained, mixed/measurement/model-input metrology not waived.',failing_guards=docfail),'R5-G1-TRACE-02':dict(status='OPEN' if tracefail else 'CLOSED_DOCUMENTARY_EXACT_C',exact_C=C,basis='Direct H01→REQ09/VAL09/MET09→FORCE_REACTION provenance with unselected measurement/model routes and no actual reaction claim.',failing_guards=tracefail)}
    result=dict(target_C=C,request_H=H,accepted_main=MAIN,actual_session_id=SESSION,checked_at_utc=now.isoformat(),scope='Independent DOC01/TRACE02 documentary correction recheck; no physical/numerical stage',counts=dict(Counter(x['result'] for x in checks)),observation_decisions=decisions,card_assessments=card_assess,metrology_assessments=met_assess,channel_assessments=channel_assess,hazard_assessments=hazard_assess,assurance_assessments=assurance_assess,route_assessments=route_assess,semantic_policy_cases=policy_cases,semantic_cases_are='Documentary reasoning only, not tests of an implemented evaluator or actual machine records',preserved_base_files=preserved,hydrated_LFS=lfs,checks=checks,failures=failures,predecessor_act_recertified=False,author332_or_old4117_as_new_review=False,overall_verdict='WARNING',B01_B02_B03='OPEN',source_power_pressure_moisture='OPEN',physical_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'},G1='OPEN',W02='NO_GO',physical_READY='NO_GO',source_states_solved=False)
    arg.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(counts=result['counts'],decisions=decisions,preserved_files=len(preserved),LFS=len(lfs),failures=failures),ensure_ascii=False));return bool(failures)

if __name__=='__main__':raise SystemExit(main())
