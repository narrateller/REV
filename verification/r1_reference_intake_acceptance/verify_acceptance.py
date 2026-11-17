"""R1 documentary acceptance/preservation, not a new independent R5 review."""
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = '3353de6c9fc699fbd565f1ce63cebedad3137a12'
TARGET = 'f2cbd96bb78c915dca74cb4eb29daffbb52ee172'
OLD_H = '411bb36f9559d80caec4e2f870e8120148d9c6a9'
C5 = '853a72b63fd8c89a3fa54ac1f309f24e7104f1c4'
H5 = 'c086c2a497614c193373d58c1b854078cd7accd0'
P = 'verification/r1_force_inputs_intake/'
R = 'verification/r5_reference_intake_review/'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


@lru_cache(None)
def blob(commit, path):
    return git('show', commit+':'+path)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def matches(raw, current):
    if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        return sha(current)==re.search(rb'oid sha256:([a-f0-9]{64})',raw).group(1).decode()
    return raw==current


def main():
    checks=[]

    def check(name,okay,evidence):
        checks.append(dict(id=name,status='PASS' if okay else 'FAIL',evidence=evidence))
        if not okay:raise AssertionError(name)

    def js(path,commit=None):
        return json.loads(blob(commit,path) if commit else (ROOT/path).read_bytes())

    check('main',git('rev-parse','origin/main').decode().strip()==BASE,BASE)
    check('common_source',git('merge-base',OLD_H,H5).decode().strip()==TARGET,TARGET)
    check('R5_H_child',git('rev-parse',H5+'^').decode().strip()==C5,C5)
    check('R5_H_scope',set(git('diff','--name-only',C5,H5).decode().splitlines())=={
          'STATE.md','NEXT_MODEL.md','handoffs/T-r5-reference-intake-review-01/6afb0a73-b16c-8191-a539-9a6685e89034.md'},'H metadata only')
    ident=js(R+'identity.json')
    check('reported_independence',ident['target_C']==TARGET and not ident['target_coauthor']
          and ident['actual_session_id']=='6afb0a73-b16c-8191-a539-9a6685e89034'
          and ident['target_author_session']=='6afb300b-1540-8191-a5c4-be1a684c20e0'
          and 'db6b977' in ident['upstream_authorship_disclosure'],'Disclosure retained; upstream correctness not re-certified')
    review=js(R+'independent_final.json')
    check('exact_1250',review['target_C']==TARGET and {k:sum(x['result']==k for x in review['checks'])
          for k in ('PASS','FAIL')}==review['counts']=={'PASS':1250,'FAIL':0},'Saved R5 evidence, not R1 replay')
    check('scope_limits',review['overall_verdict']=='WARNING_DOCUMENTARY_REFERENCE_ONLY'
          and review['input_audit_456']=='NOT_RUN' and review['G1']=='OPEN' and review['physical_READY']=='NO_GO'
          and review['claim_effective'] is False,'Preliminary documentary sufficiency only')
    for p in git('ls-tree','-r','--name-only',TARGET,P).decode().splitlines():
        check('target_exact:'+p,matches(blob(TARGET,p),(ROOT/p).read_bytes()),sha((ROOT/p).read_bytes()))
    for item in js(R+'validation.json')['package_files']:
        current=(ROOT/item['path']).read_bytes()
        check('R5_seal:'+item['path'],sha(current)==item['sha256']
              and matches(blob(C5,item['path']),current),item['sha256'])
    for p in git('ls-tree','-r','--name-only',C5,R).decode().splitlines():
        check('R5_package:'+p,matches(blob(C5,p),(ROOT/p).read_bytes()),sha((ROOT/p).read_bytes()))
    claim=js(P+'claim.json')
    check('claim_still_proposed',claim['status']=='PROPOSED_PENDING_MAIN' and claim['owner_session']=='NONE'
          and claim['lease_expires_at'] is None and claim['heartbeat_utc'] is None
          and claim['proposed_owner_session']=='6afb300b-1540-8191-a5c4-be1a684c20e0',
          'Review is not sequential main acceptance')
    now=datetime.now(timezone.utc)
    check('proposal_deadline_live',claim['proposed_lease_expires_at']=='2026-11-17T23:16:47.225017Z'
          and now<datetime.fromisoformat(claim['proposed_lease_expires_at'].replace('Z','+00:00')),
          'No extension; proposed deadline is not effective lease')
    candidate=yaml.safe_load((ROOT/P/'reference_candidate/params/registry.yaml').read_text())
    params={k:v for d in candidate['domains'].values() for k,v in d.items()}
    check('40_still_RAW',len(params)==40 and all(x['lifecycle']=='RAW' and x['verifier'] is None
          and x['calculation'] is None for x in params.values()),'No active promotion or new physics')
    journal='reviews/cross_check_log.md';current=(ROOT/journal).read_bytes()
    check('review_journal_exact',current==blob(C5,journal) and current.startswith(blob(TARGET,journal)),
          'New R5 act appended; all old records retained')
    records=[yaml.safe_load(b) for b in re.findall(r'^```yaml\s*\n(.*?)^```\s*$',current.decode(),re.M|re.S)]
    records={r['review_id']:r for r in records if isinstance(r,dict) and r.get('record_type')=='review'}
    act=records['REV-R5-REFERENCE-INTAKE-REVIEW-01-001']
    check('current_WARNING_record',act['reviewed_commit']==TARGET and act['validity']=='CURRENT'
          and act['verdict']=='WARNING' and act['claim_effective'] is False,'No gate/claim acceptance')
    for item in act['artifacts']:
        cur=(ROOT/item['path']).read_bytes()
        check('reviewed_artifact:'+item['path'],sha(cur)==item['sha256']
              and matches(blob(TARGET,item['path']),cur),item['sha256'])
    note=js(R+'qualitative_assessments.json')['additional_ARS_material_note']
    check('ARS_context_preserved','sawdust' in note and 'not exclusively metallic' in note,note)
    policy=js(P+'reference_policy.json')
    check('open_issues_not_closed',all(x['status']=='OPEN' for x in policy['open_source_issues']
          if x['id'] in ('SOURCE-POWER','SOURCE-PRESSURE-UNIT')),'Moisture basis/qualifiers retained in source policy')
    for item in js(P+'input_manifest.json')['inputs']:
        check('intake_pin:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['materialized_sha256']
              and matches(blob(item['commit'],item['path']),(ROOT/item['path']).read_bytes()),item['materialized_sha256'])
    old_manifest=js('verification/r4_force_geometry/input_manifest.json')
    for item in old_manifest['inputs']:
        check('old_pin:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256']
              and matches(blob(item['commit'],item['path']),(ROOT/item['path']).read_bytes()),item['sha256'])
    preserved=[]
    folders=list(old_manifest['protected_trees'])+['sources','process','requirements','verification/r4_force_geometry',
             'verification/r3_force_path','verification/r5_r4_force_geometry_symbolic_review',
             'verification/r5_r4_symbolic_obs01_recheck']
    for folder in folders:
        for p in git('ls-tree','-r','--name-only',BASE,folder).decode().splitlines():
            if p in preserved:continue
            raw=blob(BASE,p);cur=(ROOT/p).read_bytes()
            okay=(cur==blob(C5,p) and cur.startswith(raw)) if p==journal else matches(raw,cur)
            check('preserved:'+p,okay,sha(cur));preserved.append(p)
    check('84_52_42_44',len(js('verification/r4_force_geometry/symbolic_20261116/unknown_index.json'))==84
          and len(js('verification/r4_force_geometry/symbolic_20261116/interfaces.json')['rows'])==52
          and len(js('verification/r3_force_path/analysis/state_matrix.json'))==42
          and len(js('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows'])==44,
          'Whole source bytes pinned; states not solved')
    for p in ('STATE.md','NEXT_MODEL.md'):
        base=blob(TARGET,p);ours=blob(OLD_H,p);theirs=blob(H5,p)
        merged=theirs[:-len(base)]+ours
        cur=(ROOT/p).read_bytes()
        check('both_histories:'+p,ours.endswith(base) and theirs.endswith(base) and cur.endswith(merged),
              'Both handoff prefixes and common history preserved')
        check('new_summary_refs:'+p,not re.search(rb'\[([A-Z][A-Z0-9_-]*)@(\d+)\]',cur[:-len(merged)]),
              'C substitution is metadata only')
    result=dict(checked_at_utc=now.isoformat(),main=BASE,target_C=TARGET,R5_C=C5,R5_H=H5,checks=checks,
                counts={'PASS':len(checks),'FAIL':0},preserved_baseline_files=len(preserved),
                R5_source_review='WARNING_DOCUMENTARY_REFERENCE_ONLY',new_independent_R1_review=False,
                claim_effective=False,active_registry_promoted=False,engineering_started=False,main_merged=False)
    (HERE/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('counts','preserved_baseline_files','R5_source_review','claim_effective')}))


if __name__=='__main__':main()
