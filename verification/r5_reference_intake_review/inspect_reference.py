"""R5 documentary oracle: primary visual notes + exact unit translations.

No force/throughput/mass-rate/life model. Expected printed data come from the
reviewer's independently rendered PDF observations, not R1 build_packet.FIELDS.
The visual observations are a separate manual review step, not an OCR assertion.
"""
from pathlib import Path
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
import argparse
import datetime
import functools
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import shutil
import yaml

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
C='f2cbd96bb78c915dca74cb4eb29daffbb52ee172'
BASE='3353de6c9fc699fbd565f1ce63cebedad3137a12'
PKG='verification/r1_force_inputs_intake/'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'
getcontext().prec=50
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
@functools.lru_cache(None)
def blob(c,p):return git('show',c+':'+p)
def js(p,c=C):return json.loads(blob(c,p))
def sha(b):return hashlib.sha256(b).hexdigest()
def flatten(d):return {k:v for x in d['domains'].values() for k,v in x.items()}
def materialized_matches(raw,current):
    if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        return sha(current)==re.search(rb'oid sha256:([a-f0-9]{64})',raw).group(1).decode()
    return raw==current

def run(output):
    if output.exists():raise SystemExit('fresh output required')
    checks=[]
    def check(name,ok,expected,observed):
        checks.append(dict(id=name,result='PASS' if ok else 'FAIL',expected=expected,observed=observed))
        if not ok:raise AssertionError(name)
    claim=js(PKG+'claim.json')
    check('independence',SESSION!=claim['proposed_owner_session'] and claim['proposal_author_session']!=SESSION,
          'not R1 intake author; upstream R5 disclosure in identity.json',claim['proposed_owner_session'])
    check('preclaim_only',claim['status']=='PROPOSED_PENDING_MAIN' and claim['owner_session']=='NONE' and
          all(claim[k] is None for k in ('session_id','lease_expires_at','heartbeat_utc','claim_acceptance_commit')),
          'draft does not establish effective claim or extend old leases',claim)
    parent=git('rev-parse',C+'^').decode().strip()
    check('prior_receipt_parent',parent==js(PKG+'input_manifest.json')['prior_receipt_H'],
          'intake follows the prior merge receipt H, not directly main',parent)
    changed=git('diff','--name-status',parent,C).decode().splitlines()
    check('target_change_scope',all(line.startswith('A\t'+PKG) or line=='M\tISSUES_AND_TASKS.md' for line in changed),
          'only new intake files and tracker prefix; no protected baseline edits',changed)
    sources=js(PKG+'source_manifest.json')['sources']
    check('four_PDF',set(sources)=={'BP500','E55','WEIMA','ARS'},'four primary local PDFs',list(sources))
    for name,source in sources.items():
        path=source['path'];raw=(ROOT/path).read_bytes()
        check('PDF:'+name,sha(raw)==source['sha256'] and all(materialized_matches(blob(c,path),raw) for c in (BASE,C)),
              'full PDF SHA256 and Git LFS OID match',source)
    visual=json.loads((HERE/'visual_transcription.json').read_text())
    facts=js(PKG+'reference_facts.json')['source_fields'];byid={f['id']:f for f in facts}
    check('40_visual_fields',len(facts)==40 and set(byid)=={f['id'] for f in visual['fields']},'40 independent visual transcription matches',40)
    raw=yaml.safe_load(blob(C,PKG+'reference_candidate/params/registry.yaml'));candidate=flatten(raw)
    active=flatten(yaml.safe_load(blob(C,'params/registry.yaml')))
    check('candidate_is_scoped',len(candidate)==40 and not set(candidate)&set(active),'new RAW ids separate from active registry',len(candidate))
    conversions=[]
    exact_factors={'%':F(1,100),'mm':F(1,1000),'L':F(1,1000),'kW':F(1000),'bar':F(100000),
                   'um':F(1,1000000),'V':F(1),'Hz':F(1),'A':F(1),'kg':F(1),'count':F(1),
                   'rpm':F(1,60),'units/h':F(1,3600)}
    si_units={'%':'1','mm':'m','L':'m^3','kW':'W','bar':'Pa','um':'m','V':'V','Hz':'Hz','A':'A','kg':'kg','count':'1','rpm':'Hz','units/h':'1/s','degC':'K','kg/cm^2':'Pa'}
    for observed in visual['fields']:
        k=observed['id'];f=byid[k];p=candidate[k]
        check('visual:'+k,all(f[x]==observed[x] for x in ('source','pdf_page','printed_value','printed_unit')),
              'printed original PDF value/unit/page independently read',observed)
        check('RAW:'+k,p['value']==f['candidate_value_SI'] and p['unit']==f['unit'] and p['lifecycle']=='RAW' and
              p['calculation'] is None and p['verifier'] is None and p['tolerance'] is None and p['uncertainty'] is None
              and p['baseline_id'] is None and p['depends_on']==[] and p['scope']=='REV_REFERENCE_INTAKE_CANDIDATE_ONLY',
              'only RAW source declaration, no design calculation, acceptance or invented tolerance',f['application'])
        check('provenance:'+k,p['provenance']['source_sha256']==sources[f['source']]['sha256'] and
              p['provenance']['printed_value']==observed['printed_value'] and p['provenance']['printed_unit']==observed['printed_unit'],
              'literal and PDF hash retained in candidate',p['provenance'])
        u=observed['printed_unit'];v=observed['printed_value']
        if u=='kg/cm^2':
            expected=None;ok=p['value'] is None and bool(p['unknown_reason'])
        else:
            expected=F(str(v))+F('273.15') if u=='degC' else F(str(v))*exact_factors[u]
            exact_decimal=D(expected.numerator)/D(expected.denominator)
            ok=abs(D(str(p['value']))-exact_decimal)<=D('1e-15')*max(D(1),abs(exact_decimal))
        check('units:'+k,ok and p['unit']==si_units[u],'exact unit-definition translation; no engineering model',
              {'exact_rational':None if expected is None else str(expected),'stored_SI':p['value'],'SI_unit':p['unit']})
        conversions.append({'id':k,'printed':str(v)+' '+u,'exact_SI':None if expected is None else str(expected),
                            'SI_unit':p['unit'],'result':'UNKNOWN_UNIT_RETAINED' if expected is None else 'PASS'})
    policy=js(PKG+'reference_policy.json')
    issues={x['id']:x for x in policy['open_source_issues']}
    check('policy_primary',policy['primary_reference']=='BP500' and not policy['architectures_selected'] and
          not policy['brands_and_counts_locked'] and not policy['active_registry_modified'] and
          policy['candidate_engineering_use']=='BLOCKED_PENDING_SCOPE_AND_APPLICABLE_AUDIT',
          'primary target policy does not approve REV architecture or calculations',policy['candidate_engineering_use'])
    check('source_power_open',issues['SOURCE-POWER']['status']=='OPEN' and byid['BPR_INSTALLED_POWER']['printed_value']==34.2
          and [byid[k]['printed_value'] for k in ('BPR_MAIN_MOTOR_POWER','BPR_INFEED_MOTORS_POWER','BPR_COOLING_POWER')]==[30,2.6,1.5],
          'declared total and component rows preserved; no silent repair or new budget','34.2 versus listed 30 / 2.6 / 1.5 kW')
    check('pressure_ambiguity',issues['SOURCE-PRESSURE-UNIT']['status']=='OPEN' and candidate['BPR_COMPACTION_PRESSURE_LITERAL']['value'] is None,
          'kg/cm² not treated as kgf/cm²; no force inferred','literal1700 retained, SI null')
    check('moisture_bases',issues['SOURCE-MOISTURE-BASIS']['status']=='UNKNOWN' and all(
          'Wet/dry basis' in f['limitations'] for f in facts if 'MOISTURE' in f['id']),
          'no invented wet/dry basis or material-law conversion','separate BP5006-14 E558-14 WEIMA8-20 source windows')
    check('supplement_windows',all(f['application']=='SUPPLEMENT_ONLY_NOT_REV_ENVELOPE' for f in facts if f['source']!='BP500'),
          'supplement ranges do not enlarge or average BP500 envelope','source applications isolated')
    check('throughput_qualifier','Up to/material-dependent' in byid['BPR_THROUGHPUT_UPPER']['limitations']
          and byid['BPR_THROUGHPUT_UPPER']['application']=='PRIMARY_UP_TO_CLAIM_NOT_GUARANTEED_MINIMUM'
          and byid['BPR_REFERENCE_BRIQUETTE_MASS']['application']=='PRIMARY_REFERENCE_PRODUCT_NOT_FIXED_ALL_SETTINGS',
          'up-to, variable mass/settings, no guaranteed REV mass-rate','600 units/h converted only to1/6s^-1')
    supplements=js(PKG+'supplemental_references.json')
    check('eight_bounded_borrowings',len(supplements)==8 and all(not x['REV_parameters_assigned'] and
          x['application']=='DOCUMENTED_PATTERN_ONLY' and x['limit'] for x in supplements),
          'source-specific principle only, not an actual REV sensor/contact/PLC',len(supplements))
    index=js('verification/r4_force_geometry/symbolic_20261116/unknown_index.json')
    interfaces=js('verification/r4_force_geometry/symbolic_20261116/interfaces.json')['rows']
    states=js('verification/r4_force_geometry/symbolic_20261116/state_dependencies.json')['rows']
    intake=js(PKG+'intake_register.json');groups=intake['groups']
    check('index_provenance',intake['source_index_sha256']==sha(blob(C,'verification/r4_force_geometry/symbolic_20261116/unknown_index.json')),
          'intake links the exact full original RAW index',intake['source_index_sha256'])
    check('no_promised_completion',intake['technical_completion_percent'] is None and intake['calendar_completion_date'] is None,
          'no invented completion percentage or delivery date','both null')
    embedded=[x for g in groups for x in g['source_unknowns']]
    check('84_exact_records',len(embedded)==84 and len({x['source']['source_id'] for x in embedded})==84 and
          {x['source']['source_id']:x for x in embedded}=={x['source']['source_id']:x for x in index},
          'each complete original RAW/null record once',84)
    check('21_groups',len(groups)==21 and len({g['category'] for g in groups})==21,'21 distinct input groups',21)
    graph=[];all_rows=set();all_states=set()
    for g in groups:
        rowkeys={r for x in g['source_unknowns'] for r in x['interface_rows']}
        statekeys={s['source_state']['variant']+'/'+s['source_state']['state'] for s in states if rowkeys&set(s['interface_row_keys'])}
        check('group:'+g['category'],g['assigned_owner_session'] is None and g['due_at_utc'] is None and
              g['owner_status']=='NOT_ASSIGNED' and g['due_status']=='UNKNOWN' and g['value'] is None and
              not g['physical_value_known'] and not g['physical_input_received'] and set(g['interface_row_keys'])==rowkeys and
              set(g['functional_recipients'])=={r for x in g['source_unknowns'] for r in x['functional_data_recipients']} and
              all(x['source']['source_id'].split('_',3)[3]==g['category'] for x in g['source_unknowns']),
              'unknown values; functional proposal not assigned owner/date; correct category and row links',
              {'lead_function':g['proposed_lead_function'],'row_count':len(rowkeys),'linked_states':len(statekeys)})
        graph.append({'group':g['id'],'source_ids':[x['source']['source_id'] for x in g['source_unknowns']],
                      'interface_rows':sorted(rowkeys),'state_keys_via_interfaces':sorted(statekeys),'states_solved':False})
        all_rows|=rowkeys;all_states|=statekeys
    check('52_rows_trace',all_rows=={r['row_key'] for r in interfaces} and len(all_rows)==52,'all52 interfaces traced by source-ID graph',52)
    check('42_states_trace',len(all_states)==42 and len(states)==42 and all(s['actual_solution']=='NOT_RUN' for s in states),
          '42 original states traced via interfaces, not solved',42)
    check('8_extra_gaps',all(x['value'] is None and x['assigned_owner_session'] is None and x['due_at_utc'] is None
          and x['due_status']=='UNKNOWN' for x in js(PKG+'additional_gaps.json')),'extra gaps do not create sessions/deadlines','UNKNOWN retained')
    # Pinned source inputs and complete unchanged old project packages.
    m=js(PKG+'input_manifest.json')
    for item in m['inputs']:
        p=item['path'];cur=(ROOT/p).read_bytes()
        check('intake_pin:'+p,sha(cur)==item['materialized_sha256'] and materialized_matches(blob(item['commit'],p),cur)
              and materialized_matches(blob(C,p),cur),'26 exact pinned source inputs including full materialized PDFs',item['materialized_sha256'])
    old_manifest=js('verification/r4_force_geometry/input_manifest.json')
    for item in old_manifest['inputs']:
        p=item['path'];check('old_pin:'+p,sha(blob(C,p))==item['sha256'] and blob(C,p)==blob(item['commit'],p),
                           '54 original pins unchanged',item['sha256'])
    folders=list(old_manifest['protected_trees'])+['sources','process','requirements','verification/r3_force_path',
       'verification/r4_force_geometry','verification/r5_force_path_output_review','verification/r5_r4_force_geometry_symbolic_review',
       'verification/r5_r4_symbolic_obs01_recheck']
    preserved={}
    for folder in folders:
        for p in git('ls-tree','-r','--name-only',BASE,folder).decode().splitlines():
            if p in preserved:continue
            stored=blob(BASE,p);target=blob(C,p)
            cur=(ROOT/p).read_bytes()
            # Current reviewer appends its own record; immutable target must match base.
            okay=target==stored and (cur.startswith(stored) if p=='reviews/cross_check_log.md' else materialized_matches(stored,cur))
            check('preserved:'+p,okay,'baseline/C/worktree unchanged, journal append only',sha(target));preserved[p]=sha(target)
    bindings=js('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows']
    check('44_bindings',len(bindings)==44,'44 complete source bindings unchanged',44)
    journal=blob(C,'reviews/cross_check_log.md').decode();records=[]
    for block in re.findall(r'^```yaml\s*\n(.*?)^```\s*$',journal,re.M|re.S):
        x=yaml.safe_load(block)
        if isinstance(x,dict) and x.get('record_type')=='review':records.append(x)
    old=next(x for x in records if x['review_id']=='REV-R5-R4-FORCE-GEOMETRY-SYMBOLIC-OUTPUT-01-001')
    closure=next(x for x in records if x['review_id']=='REV-R5-R4-SYM-OBS01-RECHECK-01-001')
    check('OBS01_history',old['validity']=='STALE' and closure['OBS01_status']=='CLOSED' and
          closure['reviewed_commit']=='beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe',
          'old stale history and exact-C closure preserved','no extension of closure scope')
    # Official schema check in a temporary minimal context, never active promotion.
    sys.path.insert(0,str(ROOT/'scripts'));from check_registry import validate
    with tempfile.TemporaryDirectory(prefix='r5-reference-RAW-schema-') as tmp:
        td=Path(tmp);(td/'reviews').mkdir();(td/'reviews/cross_check_log.md').write_text('')
        (td/'drives').mkdir();(td/'drives/cots_catalog.yaml').write_text("schema_version: '1.1'\ncomponents: {}\n")
        for name in {e for p in candidate.values() for e in p['evidence']}:
            out=td/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,out)
        errors=validate(raw,td,check_git=False)
        check('official_RAW_schema',not errors,'isolated RAW schema, not source/engineering validation',errors)
    result=dict(target_C=C,actual_session_id=SESSION,checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
          counts={'PASS':len(checks),'FAIL':0},checks=checks,unit_translations=conversions,group_traceability=graph,
          preserved_file_count=len(preserved),coverage={'PDF':4,'source_fields':40,'supplements':8,'RAW_ids':84,'groups':21,'interfaces':52,'states_not_solved':42},
          limitations='Visual judgment is in visual_transcription.json; program compares that independent transcription and source definitions. No engineering-model calculations.',
          claim_effective=False,overall_verdict='WARNING_DOCUMENTARY_REFERENCE_ONLY',input_audit_456='NOT_RUN',G1='OPEN',physical_READY='NO_GO')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'counts':result['counts'],'coverage':result['coverage'],'preserved_files':len(preserved)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output)
