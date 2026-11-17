"""R5 independent documentary oracle for exact PR55 C.

No author verifier import, no machine model, no parameter promotion. Explicit
semantic expectations were composed after reading all cards/plans/hazards/norms.
Assertions support the per-item human/model judgments; counts alone prove neither
complete G1 requirements nor physical validity.
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
REL='verification/r1_g1_criteria_plan_20261117/'
C='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c'
H='e6ebf7f4df1dbbaa127eaa3c3d00576c1e611658'
MAIN='98d1494334ad5161ea8f56226c770dc762fb59d3'
BASE='043271b57aa3d49b6d9b45da03496ea11dad41b1'
OLD='c50a5eaf8f99b6aacfea7d2d63ca1c049fbdffff'
REV8='8d1b45afa84eca078a8de0a9822d6925dd87745b'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'
AUTHOR='6afb300b-1540-8191-a5c4-be1a684c20e0'

# Each tuple: critical predicate fragment, independent criterion judgment,
# independent metrology judgment, mandatory definitions before acceptance.
ASSESS=[
 ('FUNCTION_SUBCRITERIA','F01-to-F04 transfer and every outcome are observable; generic ALL requires enumerated subcriteria.','Integration needs synchronized event/material/time/product mass evidence, including bad and unejected results.','Functional subcriteria, good-output definition and complete-series accounting.'),
 ('MATERIAL_SPEC','Actual lot qualification is distinct from feedstock origin and BP500 design intent.','Sampling, material basis and mass channels are relevant; representativeness dominates the future property evidence.','Wet/dry basis, preparation/sampling, contamination limits and actual material specification.'),
 ('EJECTION_COMPLETE','Post-hold product condition and whole ejection are separate obligations; no dose-product equivalence.','Geometry/mass/time/event distinguish conditioning and exit boundary; repeatability and defect policy still needed.','Tolerances, hold state/time, defect limits, full-ejection/residue and repeatability rules.'),
 ('OUTPUT_CRITERION','Own output direction/limit is not inferred from a conditional source up-to declaration.','Time/event/electrical/mass channels allow explicit rejects, stops and energy within a comparable window.','Comparable material/settings/window and approved output/reject/downtime/energy decision rules.'),
 ('TRANSITIONS','Commands, observed states, inhibits and fault responses require a defined transition universe.','Events/motion/time support transition and fault traces; command feedback alone cannot prove position.','Modes/transitions, observation validity, thresholds/timeouts and allowable parallelism.'),
 ('BOUNDARY_SPEC','T/U transfer responsibility and buffer specification are distinct from hopper presence or a full dose.','Material/event/motion support boundary revision, buffer and transfers; physical conditioning remains unknown.','Supply boundary, preparation/conditioning/buffer and assigned interface responsibility.'),
 ('RESOURCE_SPEC','Connection and phase demand remain own-design matters; source power conflict stays open.','Electrical/time/event strategy separates start, work and pause; protection specifications are evidence, not assumed site readiness.','Own startup/operating limits and source-power disposition; instruments/transient coverage.'),
 ('SYNCHRONIZED_DATA','Pressure reference/physical role and actual contact state must be identified; no force from literal source unit.','Pressure/motion/flow/time/environment are plausible classes; explicitly define fluid versus ambient temperature and dynamic alignment.','Pressure reference/unit, fluid measurement points, phase/contact definitions, ranges and dynamics.'),
 ('APPROVED_CASES','Case-specific inputs/supports/materials and verified limits are prerequisites; a case ID is not structural proof.','Document/motion suit a future analysis review, but sources or channels establishing actual loads/reactions must be added to the executable plan.','Case universe, loads/reactions, geometry/joints/materials, model applicability/convergence and limit criteria.'),
 ('HAZARDOUS_ACCESS','Risk functions require a bounded access-scenario universe; no PL/SIL or adequacy is assigned.','Event/motion/time can support authorized scenario checks after risk criteria and safe stops are defined.','Hazard/access completeness, safety-function scope/performance and test coverage.'),
 ('SAFE_STATE','Unloading, retention and restart inhibit require independent grounds per failure; dwell is no zero-reaction evidence.','Event/pressure/motion/time must distinguish observed pressure from retained loads/energy.','Safe-state/energy/retention definitions, failure set, timings and restart authorization.'),
 ('VALID_OBSERVATION','Validity/inference basis is required; invalid/lost signals remain records rather than no-motion evidence.','Event/motion/time strategy addresses calibration, quality and alignment; detector sensitivity/window remains open.','Valid F basis/sensitivity, diagnostics, synchronization and decision thresholds; OBS04 remains open.'),
 ('EACH_MET_SEPARATELY','Indoor environment and raw-material moisture basis must be decided separately.','Environment/material channels are appropriate; neither an unmeasured site nor comparator moisture windows qualify REV.','Environmental exposure/tolerances and separate material moisture method/basis.'),
 ('CHARACTERIZED_HAZARDS','Actual dust/coating/contaminant properties precede hazard-control claims; anecdote is insufficient.','Material/environment/document methods need competent hazard characterization and applicable exposure definitions.','Composition/dust properties, methods, limits and control-effectiveness criteria.'),
 ('ISOLATION','All energies, retention and reaccumulation must be addressed before service access.','Document/event/pressure/motion classes support future isolation procedures; power-off alone does not establish safe retention.','Energy inventory/boundaries, operation sequence, retention and reaccumulation checks.'),
 ('INSTALLATION','Own envelope/mass/CoG/support and lifting evidence must come from design, not operator drawings or donor gross mass.','Geometry/mass/document strategy is useful; physical reaction/lifting evidence needs a defined future method.','Own mounting/lifting/service specification, reaction basis, clearances and handling criteria.'),
 ('MANUFACTURING','Manufacturability and COTS interface evidence remain own-design duties; no brochure brand becomes selected BOM.','Document/geometry suit routes/vendor capability/interface review with execution/tolerance-specific sources.','Actual supplier capabilities, routes/materials/tolerances and selected component execution.'),
 ('APPLICABILITY_DECISION','Objective completeness means justified scope decisions from current primary sources, not a numeric threshold or legal approval here.','Document audit requires competent source/revision/scope review; physical calibration may be inapplicable with justification.','Jurisdiction/classification/supply parties/exclusions and current source/amendments/competent decisions.'),
 ('REPRODUCTION_EVIDENCE','Package completeness is an objective itemized-scope audit; integrity CI is not physical acceptance.','Document channel should use explicit completeness/revision/source assurance criteria rather than invented numerical uncertainty.','Accepted deliverable inventory, reproduction scope and discrepancy/completeness decision policy.'),
 ('BEFORE_EXECUTION','Independent program review precedes separate execution authority; G1 is not a future test result.','Document method is suitable for program definition/review; sample size, metrology, stop rules and missing-data rules remain to specify.','Program coverage/methods/uncertainty/series/stop rules, independent review and separate execution authorization.'),
 ('TRACEABLE_SOURCE','Source-to-decision provenance and maturity boundaries are objective completeness duties; old act does not cover this supplement.','Document audit needs exact versions/locators/decision scope and stale-impact policy, not fabricated physical accuracy.','Complete provenance and independent authority for any later target/parameter adoption.'),
 ('MISSING_FRACTIONS_NOT_INVENTED','Full many-to-many events retain residues/losses and missing fractions; numerical mass evidence is future mixed content.','Event/mass/document strategy needs executable graph/identity/unit/quality and loss-completeness rules.','Split/merge/refill/changeover schema, measured fractions/masses and completeness rules; no default equal split.')
]
CHANNEL_EXPECT=[
 'EVENT MATERIAL TIME MASS','MATERIAL MASS','GEOMETRY MASS TIME EVENT','EVENT TIME ELECTRICAL MASS',
 'EVENT MOTION TIME','MATERIAL EVENT MOTION','ELECTRICAL TIME EVENT','PRESSURE MOTION FLOW TIME ENVIRONMENT',
 'DOCUMENT MOTION','EVENT MOTION TIME','EVENT PRESSURE MOTION TIME','EVENT MOTION TIME','ENVIRONMENT MATERIAL',
 'MATERIAL ENVIRONMENT DOCUMENT','DOCUMENT EVENT PRESSURE MOTION','GEOMETRY MASS DOCUMENT','DOCUMENT GEOMETRY',
 'DOCUMENT','DOCUMENT','DOCUMENT','DOCUMENT','EVENT MASS DOCUMENT'
]
HAZARDS=[
 ([16,17],'Lifting/installation needs own stability and attachment evidence; consider a direct REQ09 structural-case link before final closure.','Подъём/устойчивость'),
 ([1,6,10,15],'Feed/setup access requires risk-based prevention of hazardous movement, not a reference switch.','доступ'),
 ([3,5,10,11],'Conflicting stroke/access scenarios require actual position/isolation evidence independent of a command.','команда не подтверждает'),
 ([3,5,9,11],'A retention and reverse-column hazard needs own material/contact/force basis.','не доказывает удержание'),
 ([3,6,11,12],'Incomplete A output must keep unsafe continuation/intervention inhibited.','неполной выдаче'),
 ([8,9,11,15],'B residual-load release requires separate unloading and retention evidence; low pressure/timer is insufficient.','низкое давление/таймер'),
 ([3,5,11,12],'B open/eject/reset must account for residue/free volume and actual closure.','OPEN/EJECT/RESET'),
 ([7,8,11,15],'Hydraulic rupture/leak/retained energy includes hold failure after loss of power.','обесточивание само по себе'),
 ([5,7,10,11],'Power return must not itself grant motion; shock/isolation and restart scenarios remain to define.','Возврат питания'),
 ([5,6,12,22],'Lost/stuck/late F/L observations cannot establish valid flow or no motion.','SIGNAL_LOSS/INVALID'),
 ([10,11,15],'Jam/service access includes neighbouring starts and falling components; all sources must be isolated.','всех источников'),
 ([2,13,14,18],'Dust/material exposures need properties and competent classification; dust existence alone assigns no explosive zone.','не назначает взрывоопасную'),
 ([1,5,6,11],'T transfer and neighbouring control/energy boundary belong to stop and reaccumulation scenarios.','соседние энергии'),
 ([13,15,16],'Storage/corrosion/leak can defeat retention; own storage and inspection plan is required.','хранения'),
 ([11,15,16,18],'Decommissioning needs complete energy/suspended-part/adjacent-line boundaries.','Демонтаж'),
 ([14,15,18],'Oil/dust/coating waste hazards require composition/handling and competent review.','Состав и обращение'),
 ([5,9,11,12],'A lock-position indication is separate from unloading evidence and cannot alone authorize opening.','Разделить наблюдение замка'),
 ([8,11,15],'Valve/leak failure direction and retention remain unknown; power-off is not universal safety.','power-off'),
 ([9,15,16],'Gravitational retention is independent of measured hydraulic pressure.','Гравитационная энергия'),
 ([5,6,11,15],'Reaccumulation and neighbouring sources must be checked after isolation.','повторное накопление')
]
NORM_ASSESS=[
 'N01 general machine regulation: historical first five pages are limited evidence; current text/amendments, lifecycle scope, exclusions and parties remain undecided.',
 'N02 low-voltage candidate: source voltage scope/exclusions require actual electrical characteristics and jurisdiction; no current applicability follows from old pages.',
 'N03 explosive-atmosphere candidate: dust properties and area/equipment classification must precede applicability; existence of dust is insufficient.',
 'N04 EMC candidate: own technical means, interference/sensitivity, market and exclusions are needed; historical pages are not current legal review.',
 'N05 pressure-equipment candidate: historical first decision page and whole-file download do not constitute reading the regulation or classification rules.',
 'N06 ISO12100 candidate: old card/abstract/status is not the paid full text, a chosen risk method, national adoption or present applicability.'
]
SOURCE_ASSESS={
 'SOURCE-POWER':('BPR_INSTALLED_POWER BPR_MAIN_MOTOR_POWER BPR_INFEED_MOTORS_POWER BPR_COOLING_POWER','Ask configuration/options/duty/table revision and preserve conflicting declarations; absent reply cannot generate own reconciled budget.'),
 'SOURCE-PRESSURE-UNIT':('BPR_COMPACTION_PRESSURE_LITERAL BPR_HYDRAULIC_PRESSURE_MAX','Require primary unit/quantity/point/conditions; literal source and hydraulic maximum do not define material pressure or force.'),
 'SOURCE-MOISTURE-BASIS':('BPR_MOISTURE_MIN BPR_MOISTURE_MAX','Require primary wet/dry basis, preparation/method and scope; comparator windows remain separate; real lots qualify later.')
}

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(c,p):return git('show',f'{c}:{p}')
def jd(p,c=C):return json.loads(blob(c,p))
def sha(b):return hashlib.sha256(b).hexdigest()
def tree(c):return {p:m.split()[2] for line in git('ls-tree','-rz','--full-tree',c).decode().split('\0') if line for m,p in [line.split('\t',1)]}
def refs(nums,p='REQ'):return [f'{p}-REV-{n:02d}' for n in nums]
def materialized_digest(data):return re.search(rb'oid sha256:([0-9a-f]{64})',data).group(1).decode() if data.startswith(b'version https://git-lfs.github.com/spec/v1') else sha(data)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=HERE/'independent_results.json');a=ap.parse_args();checks=[]
    def check(i,ok,actual,expected):checks.append(dict(id=i,result='PASS' if ok else 'FAIL',observed=actual,expected=expected))
    tc,tb,to=tree(C),tree(BASE),tree(OLD)
    check('request-H-parent',git('rev-parse',H+'^').decode().strip()==C,H,'H directly follows exact target C')
    claimp='coordination/claims/T-r5-g1-supplement-output-review-01.json';claim=jd(claimp,MAIN);now=datetime.now(timezone.utc)
    check('accepted-owner-scope-time',claim['status']=='ACCEPTED_MAIN' and claim['owner_session']==SESSION and claim['target_C']==C and claim['request_H']==H and claim['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and now<datetime.fromisoformat(claim['lease_expires_at']),dict(owner=claim['owner_session'],deadline=claim['lease_expires_at'],UTC=now.isoformat()),'Accepted actual owner/exact scope/live original deadline')
    check('accepted-ledger-unmodified',(ROOT/claimp).read_bytes()==blob(MAIN,claimp),sha((ROOT/claimp).read_bytes()),sha(blob(MAIN,claimp)))
    artifacts=jd(REL+'review_target_manifest.json')['artifacts']
    check('new-target26',len(artifacts)==26,len(artifacts),26)
    for r in artifacts:check('target:'+r['path'],sha(blob(C,r['path']))==r['sha256'] and (ROOT/r['path']).read_bytes()==blob(C,r['path']),sha(blob(C,r['path'])),r['sha256'])
    pins=[]
    for path,n in [(REL+'input_manifest.json',31),('verification/r4_force_geometry/input_manifest.json',54)]:
        rows=jd(path)['inputs'];check('input-count:'+path,len(rows)==n,len(rows),n)
        for row in rows:
            b=blob(row['commit'],row['path']);expected=row.get('materialized_sha256',row.get('sha256'));digest=materialized_digest(b)
            check('pin:'+path+':'+row['path'],digest==expected and git('rev-parse',row['commit']+':'+row['path']).decode().strip()==row['git_blob'] and materialized_digest(blob(C,row['path']))==expected,digest,expected)
            pins.append(dict(path=row['path'],commit=row['commit'],sha256=digest,manifest=path))
    frozen=jd('verification/r1_requirements_draft_20261117/review_target_manifest.json')['artifacts']
    check('old-target25',len(frozen)==25,len(frozen),25)
    for r in frozen:check('rev8-target:'+r['path'],sha(blob(C,r['path']))==r['sha256'] and (ROOT/r['path']).read_bytes()==blob(C,r['path']),sha(blob(C,r['path'])),r['sha256'])
    oldjournal=blob(C,'reviews/cross_check_log.md').decode();blocks=re.findall(r'```yaml\n(.*?)```',oldjournal,re.S);oldreview=next(yaml.safe_load(b) for b in blocks if 'review_id: REV-R5-REQUIREMENTS-REV8-OUTPUT-01-001' in b)
    check('old-formal26',len(oldreview['artifacts'])==26,len(oldreview['artifacts']),26)
    for r in oldreview['artifacts']:check('old-formal:'+r['path'],sha(blob(C,r['path']))==r['sha256'],sha(blob(C,r['path'])),r['sha256'])
    protected=jd('verification/r4_force_geometry/input_manifest.json')['protected_trees'];check('12-protected',len(protected)==12,len(protected),12)
    for path in protected:
        check('protected-tree:'+path,git('rev-parse',C+':'+path)==git('rev-parse',OLD+':'+path),git('rev-parse',C+':'+path).decode().strip(),'Same full tree as authorized working input c50a; historical old tree IDs are not silently rewritten')
        changed=git('diff',C,'--name-only','--',path).decode().splitlines()
        check('working-protected-tree:'+path,set(changed)<={'reviews/cross_check_log.md'} and (ROOT/'reviews/cross_check_log.md').read_bytes().startswith(blob(C,'reviews/cross_check_log.md')),changed,'No current protected changes except own append after exact original review history')
    hydrated_lfs=[]
    for path in tc:
        b=blob(C,path)
        if b.startswith(b'version https://git-lfs.github.com/spec/v1'):
            oid=materialized_digest(b);actual=sha((ROOT/path).read_bytes())
            check('hydrated-LFS:'+path,actual==oid,actual,oid)
            hydrated_lfs.append(dict(path=path,sha256=actual,git_lfs_oid=oid))
    allowed={'ISSUES_AND_TASKS.md','STATE.md','NEXT_MODEL.md','coordination/tasks/T-r1-requirements-draft-01/task.json',f'handoffs/T-r1-requirements-draft-01/{AUTHOR}.md'}
    preserve=[]
    for path,oid in tb.items():
        if path in allowed:continue
        good=tc.get(path)==oid;check('base-preserve:'+path,good,tc.get(path),oid);preserve.append(dict(path=path,git_blob=oid,unchanged=good))
    check('source-journal-unchanged',blob(C,'reviews/cross_check_log.md')==blob(BASE,'reviews/cross_check_log.md') and (ROOT/'reviews/cross_check_log.md').read_bytes().startswith(blob(C,'reviews/cross_check_log.md')),'Exact original journal kept as prefix','No history/old findings edited')
    fullsets=[('verification/r4_cycle_interfaces/proposal/baseline_bindings.json','rows',44),('verification/r4_force_geometry/symbolic_20261116/interfaces.json','rows',52),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',None,84),('verification/r3_force_path/analysis/state_matrix.json',None,42)]
    for p,k,n in fullsets:
        d=jd(p);rows=d[k] if k else d;check('full-set:'+p,len(rows)==n and blob(C,p)==blob(BASE,p) and (ROOT/p).read_bytes()==blob(C,p),dict(count=len(rows),sha256=sha(blob(C,p))),f'{n} complete objects preserved, not solved/physically verified')
    u=jd(fullsets[2][0]);check('84-RAW-null',all(x['status']=='UNKNOWN' and x['source_lifecycle']=='RAW' and x['value'] is None and x['source_unknown_reason'] for x in u),len(u),'All84 UNKNOWN/RAW/null with reasons')
    gaps=jd('verification/r1_requirements_draft_20261117/open_gaps.json')['rows'];check('15-gaps-OPEN',len(gaps)==15 and all(x['status']=='OPEN' and x['value'] is None for x in gaps),len(gaps),'15 original gaps remain OPEN/null')
    history=jd('verification/r5_r4_force_geometry_symbolic_review/independent_after_record.json');closure=jd('verification/r5_r4_symbolic_obs01_recheck/independent_final.json')
    check('four-old-FAIL',history['counts']=={'PASS':2422,'FAIL':4},history['counts'],'Preservation only, no independent re-attestation of own old review')
    check('OBS01-closure-narrow',closure['OBS01']=='CLOSED_DOCUMENTARY_EXACT_C' and closure['target_C']=='beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe',dict(status=closure['OBS01'],C=closure['target_C']),'Existing exact-C documentary closure only')
    for token in ['material_contract_consecutive_rejections: 2','REJECT_WITH_BLOCKER','validity: STALE','R5-TZ-B01','R5-TZ-B02','R5-TZ-B03']:check('history:'+token,token in oldjournal,token,'Old history preserved')
    reqs={r['id']:r for r in jd('verification/r1_requirements_draft_20261117/draft_requirements.json')['requirements']};cards=jd(REL+'criterion_cards.json');met=jd(REL+'metrology_plan.json');cr=cards['rows'];mr=met['rows']
    check('new-target-author',cards['author_sessions']==[AUTHOR] and SESSION not in cards['author_sessions'],cards['author_sessions'],'No target coauthorship; upstream disclosed')
    check('22-card-IDs',[r['requirement_id'] for r in cr]==refs(range(1,23)),[r['requirement_id'] for r in cr],'All22 ordered original IDs')
    check('22-metrology-IDs',[r['validation_id'] for r in mr]==refs(range(1,23),'VAL'),[r['validation_id'] for r in mr],'All22 original VAL paired with cards')
    dispositions={r['field_id']:r for r in jd('verification/r1_requirements_draft_20261117/source_disposition.json')['rows']}
    assessments=[]
    for n,(crit,mp,expected) in enumerate(zip(cr,mr,ASSESS),1):
        token,judgment,metjudgment,missing=expected;rid=refs([n])[0];vid=refs([n],'VAL')[0];old=reqs[rid]
        check(rid+':criterion-meaning',token in crit['proposed_future_pass_predicate'] and bool(crit['observation']) and bool(crit['G1_definition_needed']),dict(observation=crit['observation'],predicate=crit['proposed_future_pass_predicate']),'Distinct future requirement, not a result; own semantic judgment in assessment')
        check(rid+':lineage',crit['validation_id']==vid and crit['frozen_requirement_commit']==REV8 and crit['mode']==old['mode'] and mp['criterion_card_id']==crit['card_id'],dict(VAL=crit['validation_id'],revision=crit['frozen_requirement_commit']),'Exact frozen rev8 and same REQ/VAL/mode')
        objective=n in [18,19,20,21]
        check(rid+':criterion-class',crit['criterion_kind']==('OBJECTIVE_COMPLETENESS' if objective else 'NUMERIC_OR_MIXED') and ('NOT_APPLICABLE' in crit['numeric_limit_applicability'] if objective else 'REQUIRES_APPROVED' in crit['numeric_limit_applicability']),dict(kind=crit['criterion_kind'],applicability=crit['numeric_limit_applicability']),'Objective completeness needs an enumerated scope/method, no invented numeric threshold')
        for key in ['threshold_value','tolerance','uncertainty_acceptance_limit','range','engineering_owner_session','engineering_due_utc']:check(rid+':null:'+key,crit[key] is None,crit[key],'UNKNOWN/not assigned, never zero/default')
        check(rid+':owners-status',crit['documentary_owner_session']==AUTHOR and crit['physical_validation_status']=='NOT_RUN' and crit['G1_closed'] is False and crit['active_parameter_refs']==[],dict(docowner=crit['documentary_owner_session'],status=crit['physical_validation_status']),'Document author is not engineering owner; no validation/parameter promotion')
        check(rid+':source-links',[x['id'] for x in crit['source_field_refs']]==old['source_field_ids'] and crit['qualitative_refs']==old['qualitative_reference_ids'],dict(fields=[x['id'] for x in crit['source_field_refs']],qual=crit['qualitative_refs']),'Frozen40/16 applicability links retained')
        for ref in crit['source_field_refs']:check(rid+':RAW:'+ref['id'],ref['revision']==1 and ref['disposition']==dispositions[ref['id']]['disposition'] and ref['usable_as_approved_criterion'] is False,ref,'Qualified scoped RAW reference, not a limit')
        channels=CHANNEL_EXPECT[n-1].split();check(rid+':metrology-channels',set(mp['channel_ids'])==set(channels)==set(crit['measurement_channel_ids']),mp['channel_ids'],channels)
        check(rid+':metrology-evidence',mp['evidence_fields']==crit['mandatory_evidence_fields'] and mp['method_strategy']==old['future_method'] and bool(mp['evidence_fields']),mp['evidence_fields'],'Future evidence and method align with actual observation')
        for key in ['method_revision','instrument_model','range','resolution','uncertainty_limit','sample_count','engineering_owner_session']:check(rid+':method-null:'+key,mp[key] is None,mp[key],'No invented method/device/range/accuracy/series/owner')
        check(rid+':method-not-run',mp['status']=='DRAFT_PROGRAM_NOT_AUTHORIZED' and mp['execution_status']=='NOT_RUN' and mp['execution_permission'] is False and mp['actual_records']==[],mp['execution_status'],'No authorized execution or fake records')
        check(rid+':context',set(mp['required_context'])=={'approved_program_revision','approved_criterion_refs','material_and_settings_revision','system_boundary','instrument_and_calibration_refs','timebase_and_alignment','missing_data_rules','safe_execution_authorization'},mp['required_context'],'Program/criterion/material/boundary/calibration/time/missing data/safety context retained')
        assessments.append(dict(requirement_id=rid,validation_id=vid,criterion_kind=crit['criterion_kind'],criterion_assessment=judgment,metrology_assessment=metjudgment,mandatory_G1_or_program_definitions=missing,preliminary_documentary_fitness='USEFUL_WITH_OPEN_DEFINITIONS',criterion_approval='NOT_APPROVED',physical_validation='NOT_RUN'))
    channel_assess=[];channels=met['channels'];wanted={'MATERIAL','GEOMETRY','MASS','TIME','PRESSURE','FLOW','ELECTRICAL','MOTION','ENVIRONMENT','EVENT','DOCUMENT'}
    check('11-channel-classes',len(channels)==11 and {r['channel_id'] for r in channels}==wanted,[r['channel_id'] for r in channels],sorted(wanted))
    for r in channels:
        check('channel:'+r['channel_id'],r['uncertainty_budget_evaluated'] is False and r['verification_status']=='NOT_RUN' and r['calibration_evidence'] is None and all(x['value'] is None and x['unknown_reason'] for x in r['uncertainty_budget_terms']),r['uncertainty_budget_terms'],'Terms are unevaluated; DOCUMENT assurance terms are not numerical metrology')
        for q in r['quantities']:check('unit:'+r['channel_id']+':'+q['name'],(q['unit'] is not None and q['unit_status']=='PROPOSED_SI_UNIT') or (q['unit'] is None and q['unit_status'] in ['METHOD_NOT_DEFINED','NOT_APPLICABLE_CATEGORICAL']),q,'SI label or explicitly categorical/undefined, never invented unit')
        channel_assess.append(dict(channel_id=r['channel_id'],method_scope=r['proposed_method_class'],own_assessment='Relevant proposed method class; specify applicable calibration/range/dynamics and evaluate terms before execution.' if r['channel_id']!='DOCUMENT' else 'Objective documentary assurance is relevant; generic future-calibration wording must be specialized or marked inapplicable, not treated as a numerical uncertainty budget.',actual_budget='NOT_EVALUATED'))
    hazards=jd(REL+'hazard_to_evidence.json')['rows'];sourcehazards={}
    for line in blob(C,'verification/r3_press_safety/preliminary_hazards.md').decode().splitlines():
        if re.match(r'^\| H\d\d \|',line):
            cells=[x.strip() for x in line.strip('|').split('|')];sourcehazards[cells[0]]=cells[1:]
    check('20-hazard-set',len(hazards)==20 and {r['hazard_id'] for r in hazards}==set(sourcehazards),[r['hazard_id'] for r in hazards],'All H01-H20, no source-cell loss')
    hazard_assess=[]
    for n,(r,(nums,judgment,token)) in enumerate(zip(hazards,HAZARDS),1):
        hid=f'H{n:02d}';check(hid+':original',r['hazard_id']==hid and r['source_cells']==sourcehazards[hid],r['source_cells'],'Complete original cells unchanged')
        check(hid+':meaning-links',r['requirement_ids']==refs(nums) and r['validation_ids']==refs(nums,'VAL') and token in r['proposed_safety_requirement'],dict(REQ=r['requirement_ids'],rule=r['proposed_safety_requirement']),'Scenario-specific relevant REQ/VAL/constraint')
        check(hid+':unproven',r['risk_level'] is None and r['safety_performance_level'] is None and r['safe_state_verified'] is False and r['completeness_proven'] is False and r['verification_status']=='NOT_RUN' and r['engineering_owner_session'] is None,r['acceptance_evidence'],'No PL/SIL/risk/safe-state/completeness/engineering assignment asserted')
        hazard_assess.append(dict(hazard_id=hid,own_assessment=judgment,fitness='RELEVANT_DOCUMENTARY_MAPPING_ONLY',physical_effectiveness='NOT_RUN'))
    norms=jd(REL+'normative_applicability_plan.json')['rows'];sourcenorms={}
    for line in blob(C,'verification/r3_normative_scope/source_registry.md').decode().splitlines():
        if re.match(r'^\| N\d\d \|',line):
            cells=[x.strip() for x in line.strip('|').split('|')];sourcenorms[cells[0]]=cells[1:]
    check('6-normative-set',len(norms)==6 and {r['candidate_id'] for r in norms}==set(sourcenorms),[r['candidate_id'] for r in norms],'N01-N06 retained, not chosen applicable standards')
    norm_assess=[]
    for n,r in enumerate(norms,1):
        nid=f'N{n:02d}';check(nid+':history',[r['historical_identification'],r['historical_read_scope'],r['historical_direction']]==sourcenorms[nid],[r['historical_read_scope'],r['historical_direction']],'Full historical identity/read scope/direction preserved verbatim')
        check(nid+':no-new-law',r['new_full_text_review'] is False and r['new_legal_conclusion'] is False and all(r[k] is None for k in ['current_consolidated_edition','jurisdiction','REV_applicability','competent_reviewer_session']) and r['status']=='CANDIDATE_UNRESOLVED',r['applicability_unknown_reason'],'No consolidated-current-text/legal/applicability claim')
        norm_assess.append(dict(candidate_id=nid,own_assessment=NORM_ASSESS[n-1],new_legal_review='NOT_RUN',REV_applicability=None))
    actions=jd(REL+'source_actions.json')['rows'];check('3-source-actions',{r['issue_id'] for r in actions}==set(SOURCE_ASSESS) and len(actions)==3,[r['issue_id'] for r in actions],sorted(SOURCE_ASSESS));source_assess=[]
    for r in actions:
        expected,judgment=SOURCE_ASSESS[r['issue_id']];check(r['issue_id']+':scope',r['field_ids']==expected.split() and r['status']=='OPEN' and r['issue_resolved'] is False and r['external_contact_sent'] is False and r['numeric_engineering_use'] is False and r['REV_value'] is None,r['exact_question'],'Exact documentary question, unresolved/uncontacted/no numeric adoption')
        check(r['issue_id']+':decision-options',len(r['decision_options'])==2 and 'Keep OPEN/UNKNOWN' in r['no_reply_policy'] and 'independent review' in r['decision_options'][1] and 'решение пользователя' in r['decision_options'][1],r['decision_options'],'Primary clarification or separately reviewed/user-decided revision are proposals, not decisions')
        source_assess.append(dict(issue_id=r['issue_id'],own_assessment=judgment,closure_evidence_assessment='Primary scope/edition/method plus independent exact-source review or justified exclusion/revision; no reply remains OPEN.',status='OPEN'))
    rules=jd(REL+'evaluation_rules.json');statuses=[r['future_status'] for r in rules['rules']]
    check('evaluation-order',statuses[0]=='NOT_RUN' and statuses[1].startswith('FAIL') and statuses[2].startswith('INDETERMINATE') and statuses[3].startswith('PASS'),statuses,'Authorization first; known valid violations retained; missing/invalid prevents PASS; complete evidence only')
    check('unsolicited-not-deleted','known violation' in rules['unsolicited_observations_policy'] and 'no retrospective execution authorization' in rules['unsolicited_observations_policy'],rules['unsolicited_observations_policy'],'Unauthorized observations/violations retained separately, not erased by NOT_RUN')
    schema=jd(REL+'evidence_schema.json');check('schema-not-result',schema['record_type']=='FUTURE_EVIDENCE_TEMPLATE_NOT_A_RESULT' and schema['actual_records']==[] and schema['all_VAL_TEST_status']=='NOT_RUN' and schema['template']['measured_value'] is None and schema['template']['quality_flag']=='NOT_MEASURED',schema['template'],'Template has no actual evidence/result')
    check('schema-trace-quality',all(k in schema['required_fields'] for k in ['criterion_revision','program_revision','commit','material_revision','method_revision','calibration_ref','timebase_ref','uncertainty','quality_flag','unknown_reason','raw_data_sha256','authorization_ref']) and set(schema['quality_states'])=={'VALID','INVALID','NOT_MEASURED','SIGNAL_LOSS'} and 'many-to-many' in schema['cardinality'],schema['cardinality'],'Version/calibration/time/quality/unknown/raw/authorization and graph lineage retained')
    raw=yaml.safe_load(blob(C,'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml'));params=[p for d in raw['domains'].values() for p in d.values()];check('40-RAW-unpromoted',len(params)==40 and all(p['lifecycle']=='RAW' and p['calculation'] is None and p['verifier'] is None for p in params),len(params),'Frozen scoped40 RAW, no engineering values/promotions')
    for file in ['criterion_cards.json','metrology_plan.json','hazard_to_evidence.json','normative_applicability_plan.json','source_actions.json','evaluation_rules.json','evidence_schema.json']:
        d=jd(REL+file);check('boundary:'+file,d['new_review']=='NOT_RUN' and not d['requirements_approved'] and not d['source_states_solved'] and not d['engineering_calculations_run'] and not d['physical_tests_run'] and d['G1']=='OPEN','DRAFT boundary present','No claimed new review/approval/engineering/test results')
    search=jd(REL+'source_text_search.json');check('search-scope',len(search['sources'])==4 and not search['source_issues_resolved'] and not search['engineering_values_adopted'] and not search['new_numerical_or_physical_calculations'],[r['source'] for r in search['sources']],'Bounded documentary search only')
    lfs=[]
    for r in search['sources']:
        digest=sha((ROOT/r['path']).read_bytes());check('PDF:'+r['source'],digest==r['sha256'] and r['returncode']==0 and 'absence of a match is not proof of absence' in r['scope'],dict(hash=digest,text_pages=r['pdf_pages_with_extracted_text']),'Original bytes accessible; absence scoped to extraction/pattern/language only');lfs.append(dict(path=r['path'],sha256=digest))
    check('ARS-empty-text-disclosed',next(r for r in search['sources'] if r['source']=='ARS')['pdf_pages_with_extracted_text']==0,'No ARS page has non-whitespace extracted text; form-feed bytes do not supply readable text','Cannot prove absence of definitions in scan')
    check('replays-separate',json.loads((HERE/'renderer_replay.json').read_text())['renderer']['all13_match'] and json.loads((HERE/'renderer_replay.json').read_text())['source_search']['match_excluding_checked_at_utc'],'13 outputs/search replay match','Reproducibility only, not semantic acceptance or author395 replay')
    failures=[r for r in checks if r['result']=='FAIL']
    result=dict(target_C=C,request_H=H,accepted_main=MAIN,actual_session_id=SESSION,checked_at_utc=now.isoformat(),scope='Independent new supplement semantic assessment and documentary preservation only',counts=dict(Counter(r['result'] for r in checks)),requirement_and_metrology_assessments=assessments,channel_assessments=channel_assess,hazard_assessments=hazard_assess,normative_assessments=norm_assess,source_action_assessments=source_assess,mandatory_G1_blockers=['B01: enumerate/approve quantities, limits/tolerances or objective completeness universe and actual owners','B02: executable justified program/method/metrology/uncertainty/series/quality and completeness rules, separate review/authorization','B03: own risk/safe-state/performance/normative-scope definitions; no current physical adequacy','Source power/literal pressure/moisture basis unresolved; primary clarification or independently justified/user-decided exclusion/revision'],nonblocking_documentary_observations=[dict(id='R5-G1-DOC-01',scope='Before program approval',observation='DOCUMENT channel uses generic calibration/uncertainty terminology for reviewer competence/source completeness. Specialize assurance criteria and justified not-applicable fields; do not invent a numerical budget.',preliminary_DRAFT_blocker=False),dict(id='R5-G1-TRACE-02',scope='Before complete safety/program mapping approval',observation='Consider direct REQ09 structural-case trace for H01 lifting/stability, and define actual load/reaction evidence in MET09; current table does not prove complete coverage.',preliminary_DRAFT_blocker=False)],input_pin_checks=pins,preserved_base_files=preserve,primary_source_hashes=lfs,hydrated_LFS=hydrated_lfs,checks=checks,failures=failures,author395_or_prior3890_as_new_review=False,upstream_acts_recertified=False,physical_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'},G1='OPEN',W02='NO_GO',physical_READY='NO_GO',requirements_approved=False,source_states_solved=False)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(counts=result['counts'],REQ_MET=len(assessments),channels=len(channel_assess),hazards=len(hazard_assess),norms=len(norm_assess),source_actions=len(source_assess),preserved_base_files=len(preserve),failures=failures),ensure_ascii=False));return bool(failures)

if __name__=='__main__':raise SystemExit(main())
