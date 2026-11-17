"""R5 documentary oracle, exact Git inputs; no author verifier/model/calculation.

The explicit semantic expectations below were composed by R5 after reading all
REQ/VAL and RAW applicability rows. Token checks make that reading reproducible;
they are necessary guards, not a proof of complete or approved requirements.
Run from any directory; only --output files under the R5 folder are written.
"""
from pathlib import Path
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REL = 'verification/r1_requirements_draft_20261117/'
C = '8d1b45afa84eca078a8de0a9822d6925dd87745b'
H = '87f2f5889f9ba74e8eef3a3a040d936d13e0a011'
BASE = 'bec317a4483e7f69c2af0aa1c52ef091bdef57b4'
SOURCE = 'f2cbd96bb78c915dca74cb4eb29daffbb52ee172'
SESSION = '6afb0a73-b16c-8191-a539-9a6685e89034'
AUTHOR = '6afb300b-1540-8191-a5c4-be1a684c20e0'

# ID -> independently assessed intent, distinctive textual guards, and the
# unresolved inputs preventing an executable acceptance criterion.
REQ = [
 (1, 'Four machine functions plus RF manufacture are identifiable; F05 integration must observe both good and unejected outputs.', ['F-REV-01','годных/невыданных','заранее'], 'Function subcriteria, comparable conditions and completeness of the future program.'),
 (2, 'BP500 design feedstock intent is separate from real lot qualification and historical construction wood.', ['влажностной базе','не считается','партии'], 'Wet/dry basis, methods, actual composition/fraction/density/contamination limits.'),
 (3, 'Product forming, post-hold state and complete ejection are distinct; dose mass cannot establish product quality.', ['03a','03b','Масса дозы','после выдержки'], 'Product tolerances, hold conditions/time, defects and allowable residual criterion.'),
 (4, 'Conditional up-to output is a comparison reference; no guaranteed minimum or mass-rate multiplication is justified.', ['Up-to','материалом','настройками','фиксированная масса'], 'Comparable window, material/settings, good output, rejects/downtime/energy criteria.'),
 (5, 'Transitions distinguish command, permission and observation; feed presence does not prove a full dose.', ['Каждый будущий переход','наличие материала','тайм-ауты'], 'State coverage, valid signals, thresholds/timeouts, actual cycle and parallelism.'),
 (6, 'Feed/press interfaces and responsibility are required; source hopper capacity is not a completed dose.', ['ответственность','объём полной дозы','потока'], 'Preparation/cleaning boundary, real flow, buffering and interface specification.'),
 (7, 'Site adapts to the eventual press; electrical source candidates are not own demand or ready site.', ['пуском','конфликт мощностей','SOURCE-POWER'], 'Own operating/start duty, protection and tolerances; reconcile source power before numeric use.'),
 (8, 'Own hydraulic architecture and phase contacts are needed; oil and material pressure/forces are distinct.', ['давление масла','воздействие на материал','ambiguous pressure','собственной схемой'], 'Actual phase forces/contacts/areas/losses/ranges and literal pressure interpretation.'),
 (9, 'Strength, stiffness, stability and life require case-specific loads, joints, supports and criteria.', ['устойчивости','опорами','Общая масса','ресурс'], 'Real geometry, material grades, boundaries/joints, loads, tolerances and life criteria.'),
 (10, 'Hazard identification is required before protective-function adequacy can be judged.', ['Каждая установленная опасность','выключателя','критерий'], 'Hazard modes/zones, safety-function scope/performance and competent applicability review.'),
 (11, 'Failure recovery and safe unloading need own residual-energy evidence; donor dwell proves nothing about zero reaction.', ['остаточная энергия','запреты рестарта','нулевой реакции'], 'Safe-state definition, residual forces/energy, timings, setpoints and authorized program.'),
 (12, 'Measurement validity is explicit; missing/invalid signals cannot confirm no motion or full dose.', ['SIGNAL_LOSS/INVALID','NO_MOTION_CONFIRMED','Уровень бункера'], 'Channels, sensitivity, valid F window, calibration/synchronization and thresholds; OBS04 OPEN.'),
 (13, 'Indoor environment and raw-material moisture are distinct; other moisture windows do not replace BP500.', ['Температура K','не усредняются','Метод влажности'], 'Own exposures/environment, wet/dry measurement method, uncertainty and tolerances.'),
 (14, 'Real dust/contaminants/coatings/glue require qualification and risk measures; ARS nonmetal context is no safety evidence.', ['пыль','неметаллическое сырьё ARS','не подтверждают безопасность'], 'Actual hazard properties/composition, methods, allowable limits and mitigation evidence.'),
 (15, 'Access, isolation, residual energy and completion are specified as future service duties, not demonstrated maintainability.', ['изоляция','остаточная энергия','не становится ресурсом'], 'Actual accesses, operations/isolation, compatibility and service intervals.'),
 (16, 'Own envelope, mass/CoG and reactions must be established; source ordering does not assign axes or moving mass.', ['реакции N','не назначают оси','движущейся'], 'Own dimensions/axes/masses, foundation/reactions, transport/service clearances.'),
 (17, 'RF manufacture is a project feasibility requirement; brochure components/brands do not lock BOM or layout.', ['CANDIDATE','APPROVED_FOR_LAYOUT','изготовителей'], 'Vendor capabilities, materials/routes, component execution, interfaces and tolerances.'),
 (18, 'Normative applicability is a project duty regarding machine/interfaces, separate from product commercialization.', ['коммерциализации','компетентная проверка','юрисдикция'], 'Machine classification/jurisdiction and applicable normative documents/revisions; no invented levels.'),
 (19, 'Reproducible package/provenance is an auditable project duty; integrity CI is not engineering acceptance.', ['CI целостности','автора','Manifest'], 'Future delivery composition, acceptance criteria and applicable engineering evidence.'),
 (20, 'Program review precedes separate execution authorization; G1 itself is not evidence of future results.', ['независимый review программы','отдельному разрешению','G1 не является'], 'Methods/revisions/metrology/uncertainty, sample sizes and thresholds in independently reviewed program.'),
 (21, 'New requirements provenance distinguishes old source review from this output review and preserves user direction.', ['источник → предложение → решение → проверка','новый DRAFT review','BP500-ANALOG не используется'], 'Physical applicability of donor declarations remains unconfirmed; decision/provenance chain must stay explicit.'),
 (22, 'Many-to-many lineage retains splits/refills/changeover, failed cycles, residuals/losses and unknown fractions.', ['Many-to-many','несвязанная запись/потеря','Масса дозы'], 'Actual full-series records, measured fractions/masses, completeness criteria and executable log schema.')
]

# All 40 expected decisions and REQ links explicitly enumerated by R5.
# Numeric values are deliberately not converted or used in an engineering model.
FIELD_GROUPS = [
 ('BPR_MOISTURE_MIN BPR_MOISTURE_MAX', 'OPEN_SOURCE_ISSUE', [2,13], 'Wet/dry basis and method unresolved; BP500 target intention cannot establish numeric acceptance.'),
 ('BPR_AMBIENT_MIN BPR_AMBIENT_MAX', 'TARGET_PROPOSAL', [13], 'Indoor ambient bounds may propose a future operating domain, with own tolerances/exposures still unknown.'),
 ('BPR_SUPPLY_VOLTAGE BPR_SUPPLY_FREQUENCY BPR_SUPPLY_CURRENT', 'TARGET_PROPOSAL', [7], 'Connection interface reference is relevant to an adapted site, not actual demand/protection or site readiness.'),
 ('BPR_MOTOR_COUNT BPR_MAIN_MOTOR_PHASES BPR_MAIN_MOTOR_SPEED', 'REFERENCE_CONTEXT', [7,8,17], 'Donor motor implementation cannot choose own architecture, BOM or selected component.'),
 ('BPR_INSTALLED_POWER BPR_MAIN_MOTOR_POWER BPR_INFEED_MOTORS_POWER BPR_COOLING_POWER', 'OPEN_SOURCE_ISSUE', [7,8], 'Conflicting source total and component declarations remain separate; own power budget cannot be inferred.'),
 ('BPR_CYLINDER_COUNT BPR_PUMP_COUNT BPR_OIL_TANK_VOLUME BPR_FILTER_COUNT BPR_FILTER_FROM', 'REFERENCE_CONTEXT', [8,15,17], 'Donor configuration informs interfaces/service but neither capacity nor counts select own COTS.'),
 ('BPR_HYDRAULIC_PRESSURE_MAX', 'REFERENCE_CONTEXT', [8,9], 'Oil maximum is not material stress, actual actuator force or all 42-state load spectrum.'),
 ('BPR_BUNKER_OPENING_1 BPR_BUNKER_OPENING_2 BPR_BUNKER_VOLUME', 'REFERENCE_CONTEXT', [1,6,16], 'Source feed opening/capacity informs boundary comparison, not full dose, flow, axes or REV geometry.'),
 ('BPR_BUNKER_HEIGHT', 'REFERENCE_CONTEXT', [6,15,16], 'Height refers to the loading opening, not total hopper height; own access/ergonomics remain undefined.'),
 ('BPR_BRIQUETTE_SIDE_1 BPR_BRIQUETTE_SIDE_2 BPR_BRIQUETTE_LENGTH_MIN BPR_BRIQUETTE_LENGTH_MAX', 'TARGET_PROPOSAL', [3], 'Adjustable finished-product reference geometry can guide a proposal, not cavity/stroke or approved quality limits.'),
 ('BPR_COMPACTION_PRESSURE_LITERAL', 'OPEN_SOURCE_ISSUE', [3,8], 'Literal source pressure unit is unresolved; SI stays null, no kgf assumption or force inference.'),
 ('BPR_THROUGHPUT_UPPER', 'TARGET_PROPOSAL', [4], 'Up-to/material/settings conditioned output is a comparison ceiling declaration, never guaranteed REV minimum.'),
 ('BPR_REFERENCE_BRIQUETTE_MASS', 'REFERENCE_CONTEXT', [4], 'Mass belongs to source throughput conditions; not universal product or dose mass and no derived mass-rate.'),
 ('BPR_MACHINE_DIM_1 BPR_MACHINE_DIM_2 BPR_MACHINE_DIM_3 BPR_WITH_TABLE_DIM_1', 'REFERENCE_CONTEXT', [16], 'Listed envelope and table configuration are comparison context; no inferred axes or hard site limits.'),
 ('BPR_MACHINE_MASS', 'REFERENCE_CONTEXT', [9,16], 'Gross installed mass is not moving mass, CoG, reaction or structural proof.'),
 ('SUPR_E55_MOISTURE_MIN SUPR_E55_MOISTURE_MAX SUPR_WEIMA_MOISTURE_MIN SUPR_WEIMA_MOISTURE_MAX', 'REFERENCE_CONTEXT', [2,13], 'Separate material-dependent comparator windows cannot replace or average BP500; their basis also unknown.')
]

QUAL = [
 ('BPR-FEEDSTOCK',[2,14,22], 'Dry biomass design intent does not qualify a real lot or authorize tests.'),
 ('BPR-SITE',[7,13,16], 'Indoor integrated-source arrangement informs an adaptable site, not a measured ready installation.'),
 ('BPR-OIL',[8,15], 'Fluid/monitoring/thermal functions are relevant; actual material/seal/component compatibility is unproven.'),
 ('BPR-CONTROLS',[5,12], 'PLC/HMI functions are examples; named brands do not select own PLC or prove READY.'),
 ('BPR-INFEED',[1,2,6,10,12], 'Feed/level/pause/interlock patterns are relevant; neither full dose nor safe start is thereby proven.'),
 ('BPR-WEAR',[3,9,15,17], 'Wear treatment and adjustability inform service/product concerns; no grade, depth, life or REV measuring algorithm follows.'),
 ('BPR-COMPLETION',[4,15,16], 'Output/access/completeness informs boundary/service; source arrangement proves neither ejection nor support reactions.'),
 ('BPR-WARRANTY',[9,15], 'Commercial warranty/service context supplies no fatigue cycles, design life or confirmed reliability.'),
 ('SREF-E55-HOLD',[3,5,9,11], 'Retention during plunger return is relevant to load path/reset; own hold contact/reaction still needed.'),
 ('SREF-E55-FEED',[2,5,6,8], 'Feed box/unit offers a sequencing pattern; no cylinder, tank volume or throughput may transfer.'),
 ('SREF-E55-MATERIAL',[2,14], 'Wood/metal-exclusion context cannot expand REV feedstock to polymers or certify construction-mixture properties.'),
 ('SREF-WEIMA-MATERIAL',[2,13,14], 'Material/moisture sensitivity is relevant; comparator window remains separate from primary BP500.'),
 ('SREF-WEIMA-LEVEL',[1,5,12], 'Availability signal is not completed dose; wiring/setpoints and movement permissions do not transfer.'),
 ('SREF-ARS-BRANCH',[5,8,12], 'Pressure/position branches inform comparison only; ARS also covers nonmetals, yet its forces/friction/density are not REV.'),
 ('SREF-ARS-OPEN',[3,5,11], 'Donor dwell/open/eject ordering does not prove residual unload or safe opening of REV.'),
 ('SREF-ARS-RESET',[5,11,12], 'Eject also rejoins retract/reset; own contacts/sensors/state reset and collision clearance remain unknown.')
]

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def blob(c,p): return git('show',f'{c}:{p}')
def jd(p,c=C): return json.loads(blob(c,p))
def sha(b): return hashlib.sha256(b).hexdigest()
def tree(c):
    return {p: meta.split()[2] for line in git('ls-tree','-rz','--full-tree',c).decode().split('\0') if line for meta,p in [line.split('\t',1)]}
def ids(nums,prefix='REQ'): return [f'{prefix}-REV-{i:02d}' for i in nums]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=OUT/'independent_results.json'); args=ap.parse_args()
    checks=[]
    def check(key,ok,observed,expected):
        checks.append(dict(id=key,result='PASS' if ok else 'FAIL',observed=observed,expected=expected))
    tc,th,tb=tree(C),tree(H),tree(BASE)
    check('H-parent',git('rev-parse',H+'^').decode().strip()==C,H,'Request H directly follows exact target C')
    check('base-ancestor',subprocess.run(['git','merge-base','--is-ancestor',BASE,C],cwd=ROOT).returncode==0,BASE,'Accepted main is ancestor of target')
    expected_h={'STATE.md','NEXT_MODEL.md',f'handoffs/T-r1-requirements-draft-01/{AUTHOR}.md',REL+'R5_review_command.md'}
    hchanges={p for p in set(tc)|set(th) if tc.get(p)!=th.get(p)}
    check('H-only-context',hchanges==expected_h,sorted(hchanges),sorted(expected_h))
    target_manifest=jd(REL+'review_target_manifest.json')
    for a in target_manifest['artifacts']:
        b=blob(C,a['path']); work=(ROOT/a['path']).read_bytes()
        check('target:'+a['path'],sha(b)==a['sha256'] and b==work and tc[a['path']]==th[a['path']],sha(b),a['sha256'])
    check('target-manifest-count',len(target_manifest['artifacts'])==25,len(target_manifest['artifacts']),25)
    pins=[]
    for mf,n in [(REL+'input_manifest.json',27),('verification/r4_force_geometry/input_manifest.json',54)]:
        rows=jd(mf)['inputs'];check('pin-count:'+mf,len(rows)==n,len(rows),n)
        for p in rows:
            old=blob(p['commit'],p['path']); actual=sha(old)
            # Exact documentary inputs can be archived when legitimately revised.
            archive=REL+'archive_rev7/'+Path(p['path']).name if p['path'] in ['requirements/system_requirements.md','requirements/verification_matrix.md'] else p['path']
            good=actual==p['sha256'] and git('rev-parse',p['commit']+':'+p['path']).decode().strip()==p['git_blob']
            preserved=blob(C,archive)==old
            check('pin:'+mf+':'+p['path'],good and preserved,dict(hash=actual,preserved_at=archive),p['sha256'])
            pins.append(dict(manifest=mf,path=p['path'],target_path=archive,sha256=actual,preserved=preserved))
    allowed={'ISSUES_AND_TASKS.md','coordination/tasks/T-r1-requirements-draft-01/task.json','requirements/system_requirements.md','requirements/verification_matrix.md'}
    preserve=[]
    for p,oid in tb.items():
        if p in allowed: continue
        match=tc.get(p)==oid
        check('base-preserved:'+p,match,tc.get(p),oid)
        preserve.append(dict(path=p,git_blob=oid,target_blob=tc.get(p),unchanged=match))
    changed_existing={p for p in tb if tc.get(p)!=tb[p]}
    check('authorized-existing-changes',changed_existing==allowed,sorted(changed_existing),sorted(allowed))
    added=set(tc)-set(tb)
    check('new-files-scope',all(p.startswith(REL) for p in added),len(added),'Only documentary R1 bundle added')
    lfs=[]
    for p in tb:
        if p in allowed:continue
        data=blob(C,p)
        if not data.startswith(b'version https://git-lfs.github.com/spec/v1\n'): continue
        oid=re.search(rb'oid sha256:([0-9a-f]{64})',data).group(1).decode()
        local=ROOT/p; present=local.is_file(); actual=sha(local.read_bytes()) if present else None
        check('LFS:'+p,actual==oid,actual,oid)
        lfs.append(dict(path=p,sha256=actual,git_lfs_oid=oid))
    arch=jd(REL+'archive_rev7/manifest.json')
    for a in arch['files']:
        check('archive:'+a['path'],blob(BASE,a['path'])==blob(C,a['archive_path']),sha(blob(C,a['archive_path'])),a['sha256'])
    d=jd(REL+'draft_requirements.json'); rr=d['requirements']
    check('independence-target',d['author_sessions']==[AUTHOR] and SESSION not in d['author_sessions'],d['author_sessions'],'R5 not target author; upstream participation disclosed separately')
    check('all-REQ-IDs',[r['id'] for r in rr]==ids(range(1,23)),[r['id'] for r in rr],ids(range(1,23)))
    for doc in ['system_requirements.md','verification_matrix.md']:
        old=blob(BASE,'requirements/'+doc).decode()
        pattern=r'REQ-REV-\d\d' if doc=='system_requirements.md' else r'VAL-REV-\d\d'
        check('rev7-IDs:'+doc,set(re.findall(pattern,old))==set(ids(range(1,23),'REQ' if doc.startswith('system') else 'VAL')),sorted(set(re.findall(pattern,old))),'All22 original IDs retained')
    req_assess=[]
    for n,judgment,tokens,missing in REQ:
        r=rr[n-1];rid=ids([n])[0]
        combined=' '.join(str(v) for v in r.values())
        for token in tokens:
            check(rid+':meaning:'+token,token in combined,token,'Required semantic distinction present in actual row')
        check(rid+':VAL-link',r['validation_id']==ids([n],'VAL')[0],r['validation_id'],ids([n],'VAL')[0])
        check(rid+':lineage',r['lineage']==dict(commit=BASE,document='requirements/system_requirements.md',revision=7,requirement_id=rid),r['lineage'],'Exact rev7 same-ID lineage')
        check(rid+':boundary',r['revision']==8 and r['status']=='DRAFT_NOT_APPROVED' and r['validation_status']=='NOT_RUN' and r['criterion_approved'] is False and r['architecture_selected'] is False and r['active_parameter_refs']==[] and r['assigned_engineering_owner_session'] is None, {k:r[k] for k in ['status','validation_status','criterion_approved','active_parameter_refs']},'DRAFT, no performed VAL/approved criterion/active refs/architecture/owner')
        kind='PROJECT_OR_TRACEABILITY' if n>=18 else 'MACHINE_OR_INTERFACE'
        check(rid+':kind',r['kind']==kind,r['kind'],kind)
        for key in ['mode','quantity_or_observation','future_criterion','future_method','expected_evidence','unknown_definition','responsible_functions']:
            check(rid+':defined:'+key,bool(r[key]),r[key],'Nonempty future definition; semantic sufficiency judged separately')
        # All rendered text/criteria must match assessed machine-readable row.
        reqmd=blob(C,'requirements/system_requirements.md').decode();valmd=blob(C,'requirements/verification_matrix.md').decode()
        check(rid+':rendered',r['proposed_requirement'] in reqmd and all(r[k] in valmd for k in ['quantity_or_observation','future_criterion','future_method','expected_evidence','unknown_definition']),r['id'],'Assessed wording appears without loss in both rendered documents')
        req_assess.append(dict(requirement_id=rid,validation_id=r['validation_id'],kind=kind,mode=r['mode'],documentary_assessment=judgment,preliminary_draft='SUITABLE_WITH_OPEN_INPUTS',approval_criterion='INCOMPLETE_NOT_APPROVED',mandatory_inputs_before_acceptance=missing,physical_validation='NOT_RUN'))
    expected={key:(decision,ids(nums),reason) for keys,decision,nums,reason in FIELD_GROUPS for key in keys.split()}
    sd=jd(REL+'source_disposition.json'); fields={r['field_id']:r for r in sd['rows']}
    facts={r['id']:r for r in jd('verification/r1_force_inputs_intake/reference_facts.json')['source_fields']}
    raw=yaml.safe_load(blob(C,'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml'))
    candidate={k:v for domain in raw['domains'].values() for k,v in domain.items()}
    check('40-exact-field-set',len(sd['rows'])==40 and set(fields)==set(expected)==set(facts)==set(candidate),sorted(fields),'All40 independently enumerated source fields, no omission/duplicate')
    field_assess=[]
    for key,(decision,links,reason) in expected.items():
        a=fields[key];f=facts[key];p=candidate[key]
        check(key+':applicability',a['disposition']==decision and a['requirement_ids']==links,dict(disposition=a['disposition'],links=a['requirement_ids']),dict(disposition=decision,links=links))
        check(key+':source-provenance',a['source']==f['source'] and a['pdf_page']==f['pdf_page'] and a['source_locator']==f['locator'] and a['unit']==f['unit'] and a['candidate_revision']==f['revision']==p['revision']==1,dict(source=a['source'],page=a['pdf_page'],unit=a['unit']),'Frozen field source/page/locator/unit/revision unchanged')
        check(key+':no-promotion',a['candidate_lifecycle']==p['lifecycle']=='RAW' and a['REV_realized_value'] is None and a['parameter_promotion'] is False and a['numerical_engineering_use'] is False and bool(a['realized_unknown_reason']),a['REV_realized_value'],'RAW only; actual REV value null with reason; engineering use false')
        proposal=dict(path='verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml',id=key,revision=1) if decision=='TARGET_PROPOSAL' else None
        check(key+':proposal-reference',a['target_proposal_reference']==proposal,a['target_proposal_reference'],proposal)
        field_assess.append(dict(field_id=key,independent_disposition=decision,requirement_ids=links,own_applicability_reason=reason,unit_preserved=a['unit'],source_locator=a['source_locator'],REV_realized_value=None,engineering_adoption='NOT_APPROVED'))
    counts=dict(Counter(x[0] for x in expected.values()))
    check('independent-disposition-counts',sd['counts']==counts,sd['counts'],counts)
    check('literal-pressure-null',facts['BPR_COMPACTION_PRESSURE_LITERAL']['candidate_value_SI'] is None and candidate['BPR_COMPACTION_PRESSURE_LITERAL']['value'] is None,candidate['BPR_COMPACTION_PRESSURE_LITERAL']['value'],'Unresolved literal unit stays null; no conversion calculated here')
    qa=jd(REL+'qualitative_applicability.json');qr={r['id']:r for r in qa['rows']}
    qsource={r['id']:r for r in jd('verification/r1_force_inputs_intake/qualitative_reference_facts.json')+jd('verification/r1_force_inputs_intake/supplemental_references.json')}
    check('16-qualitative-set',len(qa['rows'])==16 and set(qr)==set(qsource)=={x[0] for x in QUAL},sorted(qr),'All16 explicit primary/supplemental source references')
    qual_assess=[]
    for key,nums,reason in QUAL:
        a=qr[key];s=qsource[key]
        check(key+':applicability',a['requirement_ids']==ids(nums) and a['source']==s['source'] and a['pdf_page']==s['pdf_page'] and a['source_value_transfer'] is False,a,'Relevant links and source/page preserved, no source-value transfer')
        check(key+':limit-preserved',a['limit']==s.get('limit',s.get('adoption')) and a['relevance']==s.get('adoption',s.get('relevance')),a['limit'],'Source relevance and restrictions not weakened')
        qual_assess.append(dict(id=key,requirement_ids=ids(nums),own_assessment=reason,status='DOCUMENTARY_APPLICABILITY_ONLY'))
    check('ARS-nonmetal-and-reset','nonmetallic' in qa['ARS_material_context'] and 'eject' in qa['ARS_cycle_context'] and 'retract/reset' in qa['ARS_cycle_context'],qa,'Both nonmetal context and shared eject/retract reset retained')
    for r in rr:
        check(r['id']+':numeric-links',r['source_field_ids']==[a['field_id'] for a in sd['rows'] if r['id'] in a['requirement_ids']],r['source_field_ids'],'Exact inverse of reviewed RAW-to-REQ links')
        check(r['id']+':qualitative-links',r['qualitative_reference_ids']==[a['id'] for a in qa['rows'] if r['id'] in a['requirement_ids']],r['qualitative_reference_ids'],'Exact inverse of reviewed qualitative-to-REQ links')
    g=jd(REL+'open_gaps.json'); source_gaps=jd('verification/r1_force_inputs_intake/additional_gaps.json')
    wanted={x['id'] for x in source_gaps}|{'SOURCE-POWER','SOURCE-PRESSURE-UNIT','SOURCE-MOISTURE-BASIS','R5-TZ-B01','R5-TZ-B02','R5-TZ-B03','REQ-GAP-TOLERANCES'}
    check('15-open-gaps-set',len(g['rows'])==15 and {r['id'] for r in g['rows']}==wanted,[r['id'] for r in g['rows']],sorted(wanted))
    for r in g['rows']:
        check('gap:'+r['id'],r['status']=='OPEN' and r['value'] is None and r['assigned_owner_session'] is None and r['due_at_utc'] is None and bool(r['unknown_reason']),r,'OPEN/null, no actual assignee/date, explicit unknown reason')
    shape=[('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',None,84),('verification/r4_force_geometry/symbolic_20261116/interfaces.json','rows',52),('verification/r3_force_path/analysis/state_matrix.json',None,42),('verification/r4_cycle_interfaces/proposal/baseline_bindings.json','rows',44)]
    for path,key,n in shape:
        obj=jd(path);rows=obj[key] if key else obj
        check('full-objects:'+path,len(rows)==n and blob(C,path)==blob(BASE,path),dict(count=len(rows),sha256=sha(blob(C,path))),f'{n} full objects unchanged, not calculated or revalidated')
    unknowns=jd(shape[0][0])
    check('84-UNKNOWN-null-RAW',all(r['status']=='UNKNOWN' and r['source_lifecycle']=='RAW' and r['value'] is None and bool(r['source_unknown_reason']) for r in unknowns),len(unknowns),'All84 source unknown values remain null/RAW with reasons')
    old=jd('verification/r5_r4_force_geometry_symbolic_review/independent_after_record.json')
    closure=jd('verification/r5_r4_symbolic_obs01_recheck/independent_final.json')
    check('four-historical-FAIL-preserved',old['counts']=={'PASS':2422,'FAIL':4},old['counts'],'Own upstream evidence retained, not re-certified or reset by this review')
    check('OBS01-exact-closure-scope',closure['target_C']=='beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe' and closure['OBS01']=='CLOSED_DOCUMENTARY_EXACT_C' and len(closure['old_negative_control'])==4,dict(C=closure['target_C'],status=closure['OBS01']),'Existing closure only exact corrected R4 C; no physical or global closure')
    trace=jd(REL+'traceability_schema.json')
    check('trace-nodes',set(trace['nodes'])=={n+'_ID' for n in ['Batch','Stage','Sample','Dose','Cycle','Briquette','Residual','Loss']},trace['nodes'],'All8 lineage node kinds')
    check('trace-many-to-many',all(t in trace['cardinality'] for t in ['many-to-many','split','merge','refill','changeover']),trace['cardinality'],'Mixing/split/refill/changeover retained')
    check('trace-no-actual-records',trace['actual_records'] is None and trace['actual_records_status']=='NOT_RUN',trace['actual_records'],'No manufactured physical records')
    check('trace-null-not-default',any('unknown fractions' in x and 'zero/default equal' in x for x in trace['rules']) and any('residual/loss' in x for x in trace['rules']) and any('failed/incomplete' in x for x in trace['rules']),trace['rules'],'Unknown fractions, loss, residue and failed cycles retained')
    check('trace-signal-validity',any('SIGNAL_LOSS/INVALID is not NO_MOTION_CONFIRMED'==x for x in trace['rules']),trace['rules'],'Signal validity distinct from motion conclusion')
    reqtext=blob(C,'requirements/system_requirements.md').decode();vtext=blob(C,'requirements/verification_matrix.md').decode()
    sequence=['решение пользователя по G1','согласованная программа','независимое рассмотрение программы','отдельное разрешение выполнения','исходные записи/результаты','независимая оценка']
    sequence_text=vtext.split('## Порядок валидации и данные',1)[1]
    positions=[sequence_text.find(s) for s in sequence]
    check('validation-sequence',all(p>=0 for p in positions) and positions==sorted(positions),dict(zip(sequence,positions)),'G1 basis -> program -> independent program review -> separate execution authority -> results -> review')
    for token in ['SOURCE-POWER','SOURCE-PRESSURE-UNIT','NOT_EVALUATED','44 bindings','BPR_BUNKER_HEIGHT','неметаллическое','eject','retract/reset','R5-TZ-B01/B02/B03','42 состояния не рассчитаны','§4/5/6 NOT_RUN','G1 OPEN']:
        check('global-qualifier:'+token,token in reqtext,token,'Critical qualifier/limitation explicitly retained')
    check('all-VAL/TEST-not-run','Все VAL-REV-* и TEST-F-* — NOT_RUN' in vtext and d['source_states_solved'] is False and d['numerical_machine_models_run'] is False and d['G1']=='OPEN' and d['physical_READY']=='NO_GO',dict(G1=d['G1'],physical_READY=d['physical_READY']),'No engineered or physical acceptance implied')
    claimpath='coordination/claims/T-r1-requirements-draft-01.json';claim=jd(claimpath);intake=jd('coordination/claims/T-r1-force-inputs-intake-01.json')
    deadline=datetime.fromisoformat(claim['lease_expires_at']);proposal=datetime.fromisoformat(claim['proposed_at_utc']);now=datetime.now(timezone.utc)
    check('R1-accepted-main',blob(BASE,claimpath)==blob(C,claimpath) and claim['status']=='ACCEPTED_MAIN' and claim['owner_session']==AUTHOR,claim['status'],'Accepted PR53 main claim unchanged')
    check('R1-deadline',claim['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and (deadline-proposal).total_seconds()==86400 and now<deadline,dict(observed_at_utc=now.isoformat(),deadline=claim['lease_expires_at']),'Original24h deadline active, not extended')
    check('intake-released',intake['status']=='COMPLETED_DOCUMENTARY_RELEASED' and intake['owner_session']=='NONE' and intake['lease_active'] is False and intake['lease_extension'] is False,intake['status'],'Earlier intake released, original deadline unchanged')
    # Review history is preserved byte-for-byte above, including counters and old FAIL.
    history=blob(C,'reviews/cross_check_log.md').decode()
    for token in ['material_contract_consecutive_rejections: 2','REV-R5-R4-FORCE-GEOMETRY-SYMBOLIC-OUTPUT-01-001','REV-R5-R4-SYM-OBS01-RECHECK-01-001','REJECT_WITH_BLOCKER','R5-TZ-B01','R5-TZ-B02','R5-TZ-B03']:
        check('history:'+token,token in history,token,'Existing history retained without recertifying its own correctness')
    fail=[r for r in checks if r['result']=='FAIL']
    result=dict(target_C=C,request_H=H,base_main=BASE,actual_session_id=SESSION,recorded_at_utc=now.isoformat(),scope='Independent semantic assessment of preliminary DRAFT rev8 and documentary preservation; no physical/engineering calculations',not_independent_evidence=['author358 PASS','renderer replay','correctness of own upstream acts'],counts=dict(Counter(r['result'] for r in checks)),semantic_requirements=req_assess,field_applicability=field_assess,qualitative_applicability=qual_assess,pin_checks=pins,preserved_files=preserve,lfs_files=lfs,checks=checks,failures=fail,physical_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'},approval='NOT_APPROVED',G1='OPEN',W02='NO_GO',physical_READY='NO_GO')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(counts=result['counts'],requirements=len(req_assess),RAW_fields=len(field_assess),qualitative_refs=len(qual_assess),preserved_base_files=len(preserve),LFS=len(lfs),failures=fail),ensure_ascii=False))
    return bool(fail)

if __name__=='__main__':raise SystemExit(main())
