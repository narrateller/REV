"""Documentary packet consistency, exact unit conversions and frozen-source checks.

Not independent source transcription review, engineering calculation or claim acceptance.
"""
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = '3353de6c9fc699fbd565f1ce63cebedad3137a12'
PREV = '43c80ad7cda15caf166080e1f81dd7a83a87d1e2'
SESSION = '6afb300b-1540-8191-a5c4-be1a684c20e0'


@lru_cache(None)
def blob(commit, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit+':'+path])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    checks = []

    def check(name, okay, evidence):
        checks.append(dict(id=name, status='PASS' if okay else 'FAIL', evidence=evidence))
        if not okay:
            raise AssertionError(name)

    def js(name):
        return json.loads((HERE/name).read_text())

    claim = js('claim.json')
    check('actual_R1_identity', os.environ.get('CODEX_SESSION_ID') == SESSION
          and claim['proposed_owner_session'] == SESSION, 'Own R1 identity only; no author/reviewer spoofing')
    check('claim_pending', claim['status'] == 'PROPOSED_PENDING_MAIN' and claim['owner_session'] == 'NONE'
          and all(claim[k] is None for k in ('session_id','lease_expires_at','heartbeat_utc','claim_acceptance_commit')),
          'Branch proposal is not an effective main claim')
    check('proposal_live_not_extended', datetime.now(timezone.utc) < datetime.fromisoformat(
          claim['proposed_lease_expires_at'].replace('Z','+00:00')), claim['proposed_lease_expires_at'])
    check('base_main', subprocess.check_output(['git','rev-parse','origin/main']).decode().strip() == BASE, BASE)
    manifest = js('source_manifest.json')['sources']
    check('four_sources', set(manifest) == {'BP500','E55','WEIMA','ARS'}, 'Primary plus three supplementary sources')
    for name, src in manifest.items():
        stored=blob(BASE,src['path']);current=(ROOT/src['path']).read_bytes()
        if stored.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            source_equal=sha(current)==re.search(rb'oid sha256:([a-f0-9]{64})',stored).group(1).decode()
        else:
            source_equal=current==stored
        check('source:'+name, sha(current)==src['sha256'] and source_equal, src['pages_read'])
    policy = js('reference_policy.json')
    check('user_policy', policy['primary_reference']=='BP500'
          and set(policy['supplementary_references']) == {'WEIMA','E55','ARS'}
          and policy['site_policy'].startswith('SITE_WILL_ADAPT') and not policy['architectures_selected']
          and not policy['active_registry_modified'], 'User policy received; no architecture/active baseline promotion')
    raw = yaml.safe_load((HERE/'reference_candidate/params/registry.yaml').read_text())
    candidate = {k:v for domain in raw['domains'].values() for k,v in domain.items()}
    facts = js('reference_facts.json')['source_fields']
    check('candidate_40_only', len(candidate)==40 and {f['id'] for f in facts} == set(candidate), 'Scoped registry only')
    factors={'%':Decimal('0.01'),'mm':Decimal('0.001'),'L':Decimal('0.001'),
             'kW':Decimal('1000'),'bar':Decimal('100000'),'um':Decimal('0.000001'),
             'V':Decimal('1'),'Hz':Decimal('1'),'A':Decimal('1'),'kg':Decimal('1'),'count':Decimal('1')}
    for f in facts:
        p = candidate[f['id']]
        check('RAW:'+f['id'], p['lifecycle']=='RAW' and p['validity']=='CURRENT' and p['verifier'] is None
              and p['calculation'] is None and p['tolerance'] is None and p['uncertainty'] is None
              and p['value']==f['candidate_value_SI'], f['application'])
        unit=f['printed_unit'];source=Decimal(str(f['printed_value']))
        if unit=='kg/cm^2':
            okay=p['value'] is None and bool(p['unknown_reason'])
        else:
            expected=(source+Decimal('273.15') if unit=='degC' else source/Decimal('60') if unit=='rpm'
                      else source/Decimal('3600') if unit=='units/h' else source*factors[unit])
            okay=abs(Decimal(str(p['value']))-expected) <= Decimal('1e-15')*max(abs(expected),Decimal('1'))
        check('unit_conversion:'+f['id'],okay,{'printed':f['printed_value'],'unit':unit,'SI':p['value']})
    check('supplement_not_override', all(f['application']=='SUPPLEMENT_ONLY_NOT_REV_ENVELOPE'
          for f in facts if f['source']!='BP500'), 'Material windows remain distinct')
    check('source_issues_preserved', {x['id'] for x in policy['open_source_issues']}
          == {'SOURCE-POWER','SOURCE-PRESSURE-UNIT','SOURCE-MOISTURE-BASIS','SOURCE-UP-TO'}, 'No silent data repair')
    supplements=js('supplemental_references.json')
    check('eight_relevant_records',len(supplements)==8 and all(x['application']=='DOCUMENTED_PATTERN_ONLY'
          and not x['REV_parameters_assigned'] and bool(x['limit']) for x in supplements), 'No borrowed machine settings')
    intake=js('intake_register.json');groups=intake['groups']
    old=json.loads(blob(BASE,'verification/r4_force_geometry/symbolic_20261116/unknown_index.json'))
    flattened=[x for g in groups for x in g['source_unknowns']]
    check('all_84_source_records',len(groups)==21 and len(flattened)==84
          and {x['source']['source_id']:x for x in flattened}=={x['source']['source_id']:x for x in old},
          'Every full source record is preserved exactly once')
    for g in groups:
        check('unassigned:'+g['id'], g['assigned_owner_session'] is None and g['due_at_utc'] is None
              and g['due_status']=='UNKNOWN' and g['value'] is None and not g['physical_input_received'],
              g['status'])
    # Exercise the unmodified project validator on a minimal isolated RAW registry.
    # This checks the candidate schema without adding IDs to the active registry.
    sys.path.insert(0,str(ROOT/'scripts'))
    import check_registry
    with tempfile.TemporaryDirectory(prefix='REV-intake-candidate-schema-') as td:
        tr=Path(td)
        (tr/'reviews').mkdir();(tr/'reviews/cross_check_log.md').write_text('')
        (tr/'drives').mkdir();(tr/'drives/cots_catalog.yaml').write_text("schema_version: '1.1'\ncomponents: {}\n")
        for path in {x for p in candidate.values() for x in p['evidence']}:
            dest=tr/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,dest)
        errors=check_registry.validate(raw,tr,check_git=False)
        check('candidate_official_schema',not errors,{'errors':errors,'scope':'Isolated RAW schema only, no source/physical review'})
    original_manifest=json.loads(blob(BASE,'verification/r4_force_geometry/input_manifest.json'))
    for x in original_manifest['inputs']:
        check('pinned:'+x['path'],(ROOT/x['path']).read_bytes()==blob(x['commit'],x['path'])
              and sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
    protected=[]
    for folder in list(original_manifest['protected_trees'])+['sources','process','requirements',
            'verification/r4_force_geometry','verification/r3_force_path',
            'verification/r5_r4_force_geometry_symbolic_review','verification/r5_r4_symbolic_obs01_recheck']:
        for path in subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,folder]).decode().splitlines():
            if path in protected:continue
            stored=blob(BASE,path);cur=(ROOT/path).read_bytes()
            if stored.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                okay=sha(cur)==re.search(rb'oid sha256:([a-f0-9]{64})',stored).group(1).decode()
            else:okay=cur==stored
            check('preserved:'+path,okay,sha(cur));protected.append(path)
    bindings=json.loads(blob(BASE,'verification/r4_cycle_interfaces/proposal/baseline_bindings.json'))['rows']
    states=json.loads(blob(BASE,'verification/r3_force_path/analysis/state_matrix.json'))
    check('44_bindings_42_unsolved',len(bindings)==44 and len(states)==42
          and all(x['result']=='UNKNOWN' and x['actual_force_N'] is None for x in states), 'No new solved cases')
    for path in ('STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md'):
        cur=(ROOT/path).read_bytes();old=blob(PREV,path)
        check('history_suffix:'+path,cur.endswith(old),'Prior receipt and all earlier history retained')
        prefix=cur[:-len(old)]
        check('new_prefix_no_active_refs:'+path,not re.search(rb'\[([A-Z][A-Z0-9_-]*)@(\d+)\]',prefix),
              'New numeric IDs are explicitly scoped candidates')
    report=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),base=BASE,checks=checks,
                counts={'PASS':len(checks),'FAIL':0},preserved_files=len(protected),
                candidate_source_review='NOT_RUN',claim_effective=False,
                numerical_machine_models='NOT_RUN',physical_trials='NOT_RUN',active_registry_modified=False)
    (HERE/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('counts','preserved_files','candidate_source_review','claim_effective')}))


if __name__=='__main__':
    main()
