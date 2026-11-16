"""Independent targeted documentary recheck, immutable old/new C comparison.

No old oracle mutation, author preflight, physical or numerical evaluation.
Exit 0 requires all recheck assertions plus the expected four old negative cases.
"""
from pathlib import Path
import argparse
import functools
import hashlib
import json
import re
import subprocess
import datetime
import difflib
import yaml

ROOT=Path(__file__).resolve().parents[2]
OLD='b840dfd5444da2bf62483b7f4a6069d2bb255b71'
NEW='beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe'
NH='47db9013c3cf3756987cdb480850cc0487c59b1e'
COORD='1d5e2a8ed3c9be340897d6485c7a4383edf62152'
REVIEW='4aa23509b45efc2c2c166935102ca5caa76f55e2'
BASE='f731910273b47f46c6d45114cecd76de6fa8adf9'
PKG='verification/r4_force_geometry/symbolic_20261116/'
FIX='verification/r4_force_geometry/obs01_correction/'
PRIOR='verification/r5_r4_force_geometry_symbolic_review/'
SESSION='6afb0a73-b16c-8191-a539-9a6685e89034'

def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
@functools.lru_cache(None)
def blob(c,p):return git('show',c+':'+p)
def js(c,p):return json.loads(blob(c,p))
def sha(x):return hashlib.sha256(x).hexdigest()

def run(output):
    if output.exists():raise SystemExit('fresh output required')
    checks=[]
    def check(name,okay,expected,observed):
        checks.append(dict(id=name,result='PASS' if okay else 'FAIL',expected=expected,observed=observed))
        if not okay:raise AssertionError(name)
    req=js(NH,FIX+'recheck_request.json')
    check('independence',SESSION not in req['author_sessions']+req['excluded_author_sessions'],
          'same original R5; not a correction/coordination author',req['excluded_author_sessions'])
    check('exact_target',req['target_C']==NEW,'immutable target is corrected C',req['target_C'])
    check('H_parent',git('rev-parse',NH+'^').decode().strip()==NEW,'new request H child of new C',NH)
    git('merge-base','--is-ancestor','cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9',BASE)
    git('merge-base','--is-ancestor',BASE,NEW)
    old=js(OLD,PKG+'interfaces.json');new=js(NEW,PKG+'interfaces.json')
    a,b=old['rows'],new['rows']
    check('52_rows_order',[r['row_key'] for r in a]==[r['row_key'] for r in b] and len(a)==52,
          '52 unchanged row keys/order',len(b))
    check('document_metadata',{k:v for k,v in old.items() if k!='rows'}=={k:v for k,v in new.items() if k!='rows'},
          'scope/author/provenance unchanged','metadata equal')
    corrected=[];negative=[];expected=json.loads(json.dumps(old))
    for before,after,exp in zip(a,b,expected['rows']):
        key=before['row_key']
        if key.endswith('/datum_motion'):
            family=key.split('-')[0]
            foreign='CI-X_B_GATHER' if family=='A' else 'CI-X_COLUMN_GATHER'
            own='CI-X_COLUMN_GATHER' if family=='A' else 'CI-X_B_GATHER'
            refs=before['source_references'];newrefs=after['source_references']
            removed=[x for x in refs if x['source']=='CI' and x['source_id']==foreign]
            exp['source_references']=[x for x in refs if x not in removed]
            oldbad=any(x['source']=='CI' and x['source_id']==foreign for x in refs)
            newbad=any(x['source']=='CI' and x['source_id']==foreign for x in newrefs)
            check(key+':one_removed',len(removed)==1 and len(refs)-len(newrefs)==1,'exactly one selected ref removed',removed)
            check(key+':foreign_absent',not newbad,'foreign family not row-local prerequisite',foreign)
            check(key+':own_retained',sum(x['source']=='CI' and x['source_id']==own for x in newrefs)==1,
                  'own family gather preserved once',own)
            check(key+':refs_order_values',newrefs==exp['source_references'],'ordered original list minus selected ref',len(newrefs))
            check(key+':other_fields',{k:v for k,v in before.items() if k!='source_references'}=={
                  k:v for k,v in after.items() if k!='source_references'},'all other fields unchanged','exact equality')
            check(key+':negative_control',oldbad and not newbad,'old fails same applicability predicate; new passes',{'old':'FAIL_EXPECTED','new':'PASS'})
            corrected.append(dict(row_key=key,removed=foreign,retained=own,result='PASS'))
            negative.append(dict(row_key=key,foreign_id=foreign,old_outcome='FAIL_EXPECTED',new_outcome='PASS'))
        else:check(key+':unchanged',before==after,'one of 48 unaffected complete rows','exact equality')
    check('four_fixes',len(corrected)==4,'all four rows addressed',corrected)
    check('whole_json_bytes',(json.dumps(expected,ensure_ascii=False,indent=2)+'\n').encode()==blob(NEW,PKG+'interfaces.json'),
          'no unrelated JSON values/order/format changes',sha(blob(NEW,PKG+'interfaces.json')))
    lines=blob(OLD,PKG+'interfaces.md').decode().splitlines(keepends=True)
    for item in corrected:
        indices=[i for i,s in enumerate(lines) if item['row_key']+':' in s]
        check(item['row_key']+':md_locator',len(indices)==1,'one rendered row',indices)
        i=indices[0];fragment='; CI:'+item['removed']
        check(item['row_key']+':md_removal',lines[i].count(fragment)==1,'same exact source reference rendered once',fragment)
        lines[i]=lines[i].replace(fragment,'',1)
    check('whole_md_bytes',''.join(lines).encode()==blob(NEW,PKG+'interfaces.md'),
          'four same removals only in readable table',sha(blob(NEW,PKG+'interfaces.md')))
    renderer_old=blob(OLD,PKG+'render_tables.py')
    anchor=b"            refs += [ref('CI', 'unknowns[id=' + x + ']', x) for x in ci_ids]"
    addition=(b"            if key == 'datum_motion':\n"
              b"                foreign_gather = 'CI-X_B_GATHER' if family == 'A' else 'CI-X_COLUMN_GATHER'\n"
              b"                ci_ids = [x for x in ci_ids if x != foreign_gather]\n")
    check('generator_delta_only',renderer_old.count(anchor)==1 and renderer_old.replace(anchor,addition+anchor)==blob(NEW,PKG+'render_tables.py'),
          'only scoped gather filter, original generator otherwise identical','3-line addition')
    edits=difflib.SequenceMatcher(None,blob(OLD,PKG+'verify_symbolic.py').splitlines(),
                                 blob(NEW,PKG+'verify_symbolic.py').splitlines()).get_opcodes()
    check('verifier_assertions_retained',all(tag in ('equal','insert') for tag,*rest in edits),
          'author verifier only adds checks; no original condition removed or weakened',edits)
    modified={'README.md','interfaces.json','interfaces.md','render_tables.py','verify_symbolic.py'}
    for p in git('ls-tree','-r','--name-only',OLD,PKG).decode().splitlines():
        if p[len(PKG):] not in modified:
            check('historical_symbolic:'+p,blob(OLD,p)==blob(NEW,p),'all other symbolic files/evidence unchanged',sha(blob(NEW,p)))
    for name in ('source_catalog.json','symbolic_dependencies.json','state_dependencies.json','state_dependencies.md','unknown_index.json'):
        check('unchanged:'+name,blob(OLD,PKG+name)==blob(NEW,PKG+name),'other dependencies unchanged',sha(blob(NEW,PKG+name)))
    ci_path='verification/r4_cycle_interfaces/proposal/unknown_inputs.json'
    ci=js(NEW,ci_path)['unknowns']
    check('master_ci',blob(OLD,ci_path)==blob(NEW,ci_path) and {'CI-X_COLUMN_GATHER','CI-X_B_GATHER'}<={x['id'] for x in ci},
          'both IDs remain in untouched master catalog','both preserved')
    mapped=js(NEW,PKG+'state_dependencies.json')['rows']
    states=js(NEW,'verification/r3_force_path/analysis/state_matrix.json')
    check('42_not_solved',len(mapped)==42 and [x['source_state'] for x in mapped]==states and all(
          x['actual_solution']=='NOT_RUN' and all(x[k] is None for k in ('actual_force','actual_moment','actual_capacity_margin')) for x in mapped),
          '42 whole source states, no solution','exact source equality and null/NOT_RUN')
    check('84_raw_index',len(js(NEW,PKG+'unknown_index.json'))==84 and all(
          x['value'] is None and x['source_lifecycle']=='RAW' for x in js(NEW,PKG+'unknown_index.json')),
          '84 existing RAW/null unchanged',84)
    bind_path='verification/r4_cycle_interfaces/proposal/baseline_bindings.json'
    check('44_full_bindings',blob(OLD,bind_path)==blob(NEW,bind_path) and len(js(NEW,bind_path)['rows'])==44,
          'complete rows, loads/strokes/fixed-budget/source fields unchanged',sha(blob(NEW,bind_path)))
    manifest=js(NEW,'verification/r4_force_geometry/input_manifest.json')
    check('54_count',len(manifest['inputs'])==54,'54 pinned inputs',54)
    for item in manifest['inputs']:
        p=item['path'];raw=blob(item['commit'],p)
        check('pinned:'+p,sha(raw)==item['sha256'] and all(blob(x,p)==raw for x in (OLD,NEW,NH,COORD)),
              'immutable source and old/new/H/coord input identical',item['sha256'])
    for path,tree in manifest['protected_trees'].items():
        check('tree:'+path,all(git('rev-parse',c+':'+path).decode().strip()==tree for c in (OLD,NEW,NH)),
              '12 source tree identities at R4 targets unchanged',tree)
    changed=git('diff','--name-only','9433ef749df14a3bbf8ea32331e2f895fd5bf7aa',NEW).decode().splitlines()
    declared=js(NEW,FIX+'change_manifest.json')['changed_paths']
    check('all_changes_declared',set(changed)==set(declared),'complete changed path manifest',changed)
    oldclaim=js(OLD,'verification/r4_force_geometry/claim.json');claim=js(NEW,'verification/r4_force_geometry/claim.json')
    allowed={'task_status','heartbeat_utc','updated_at_utc','executor_heartbeat_status','preflight',
             'correction_authority_C','OBS_01_status','OBS_01_author_correction','OBS_01_independent_recheck'}
    delta={k for k in set(oldclaim)|set(claim) if oldclaim.get(k)!=claim.get(k)}
    check('claim_delta',delta==allowed,'only disclosed service-summary fields',sorted(delta))
    check('owner_lease_scope',claim['owner_session']=='6afb4750-7918-8191-8569-77b5b0c41050' and
          claim['lease_expires_at']==oldclaim['lease_expires_at']=='2026-11-17T17:44:00Z' and
          claim['scope']==oldclaim['scope'] and claim['exclusions']==oldclaim['exclusions'] and claim['OBS_01_status']=='OPEN',
          'same R4 owner/deadline/authority, not self-closed',claim['lease_expires_at'])
    accepted=[]
    for p in git('ls-tree','-r','--name-only',BASE,'verification').decode().splitlines():
        if p.endswith('/claim.json'):
            candidate=js(BASE,p)
            if candidate.get('task_id')=='T-r4-force-geometry-01' and candidate.get('status')=='ACCEPTED_MAIN':
                accepted.append({'path':p,'owner':candidate.get('owner_session'),'lease':candidate.get('lease_expires_at')})
    check('accepted_main_owner',len(accepted)==1 and accepted[0]['owner']==claim['owner_session']
          and accepted[0]['lease']==claim['lease_expires_at'],
          'one observable accepted main owner at fetched unchanged main; no competing accepted claim',accepted)
    deadline=datetime.datetime.fromisoformat(claim['lease_expires_at'].replace('Z','+00:00'))
    for name in ('heartbeat_start.json','heartbeat_end.json','heartbeat_precommit.json'):
        event=js(NEW,FIX+name)
        check('author_time:'+name,datetime.datetime.fromisoformat(event['recorded_at_utc'])<deadline and not event['lease_extended'],
              'actual author event before original deadline',event)
    for item in js(NEW,FIX+'archive_manifest.json'):
        raw=blob(OLD,item['path'])
        check('archive:'+item['path'],sha(raw)==item['sha256'] and blob(NEW,item['archive_path'])==raw,
              'archived old artifacts exactly old C',item['archive_path'])
    for p in git('ls-tree','-r','--name-only',REVIEW,PRIOR).decode().splitlines():
        check('old_reviewer:'+p,blob(COORD,p)==blob(REVIEW,p) and (ROOT/p).read_bytes()==blob(REVIEW,p),
              'original oracle/act/2422 PASS and 4 FAIL not modified',sha(blob(REVIEW,p)))
    original_journal=blob(REVIEW,'reviews/cross_check_log.md')
    old_target_journal=blob(OLD,'reviews/cross_check_log.md')
    archive=blob(COORD,'verification/r1_r5_obs01_recheck/original_review_record.md')
    check('old_record_archived',original_journal.endswith(archive) and original_journal[:-len(archive)]==old_target_journal,
          'old complete record archived verbatim; old prefix unchanged',sha(archive))
    check('validity_occurs_once',archive.count(b'\nvalidity: CURRENT\n')==1,'only selected record validity normalized',1)
    stale_journal=original_journal[:-len(archive)]+archive.replace(b'\nvalidity: CURRENT\n',b'\nvalidity: STALE\n',1)
    check('coord_stale_only',blob(COORD,'reviews/cross_check_log.md')==stale_journal,
          'only CURRENT->STALE; verdict/checks/finding unchanged',sha(stale_journal))
    check('R4_reviews_untouched',blob(NEW,'reviews/cross_check_log.md')==old_target_journal,
          'R4 did not merge/change reviewer journal','old R4 review prefix identical')
    firstlog=blob(COORD,'verification/r1_r5_obs01_recheck/registry_initial.log').decode()
    status=js(COORD,'verification/r1_r5_obs01_recheck/registry_initial_status.json')
    check('initial_failure_preserved',status['returncode']==1 and 'Artifact hash mismatch' in firstlog,
          'historical FAIL retained, not relabeled PASS',firstlog.strip())
    old_evidence=js(REVIEW,PRIOR+'independent.json')
    original_fails=[x['id'].split(':')[0] for x in old_evidence['checks'] if x['result']=='FAIL']
    check('old_four_independent_FAIL',old_evidence['counts']=={'PASS':2422,'FAIL':4} and set(original_fails)=={x['row_key'] for x in negative},
          'own negative control identifies same four old rows',original_fails)
    author_negative=js(NEW,FIX+'negative_original_tables.json')
    fail_checks=[x['check'] for x in author_negative['checks'] if x['status']=='FAIL']
    expected_fail_checks={prefix+x['row_key'] for x in negative for prefix in ('OBS01_foreign_absent:','OBS01_only_one_ref_removed:')}
    check('author_negative_explained',set(fail_checks)==expected_fail_checks and author_negative['counts']=={'PASS':1337,'FAIL':8},
          'two failed author predicates per same four rows; not eight independent defects',fail_checks)
    audit=js(NEW,'verification/r4_force_geometry/input_audit.json')
    check('audit_456',blob(NEW,'verification/r4_force_geometry/input_audit.json')==blob(OLD,'verification/r4_force_geometry/input_audit.json')
          and all(x['status']=='NOT_RUN' for x in audit['items'] if x['section'] in (4,5,6)),
          'same input audit, §4/5/6 NOT_RUN','unchanged')
    # Current execution folder is the coordination branch, never a moved target.
    for p in git('ls-tree','-r','--name-only',NEW,'verification/r4_force_geometry').decode().splitlines():
        check('current_target_file:'+p,(ROOT/p).read_bytes()==blob(NEW,p),
              'actual replay inputs are immutable new target bytes',sha(blob(NEW,p)))
    result=dict(target_C=NEW,request_H=NH,branch_base_H=COORD,original_C=OLD,original_review_C=REVIEW,
                actual_session_id=SESSION,checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                method='Independent exact ordered-delta and preservation oracle; no imported author verifier or prior oracle.',
                counts={'PASS':len(checks),'FAIL':0},row_results=corrected,old_negative_control=negative,
                checks=checks,OBS01='CLOSED_DOCUMENTARY_EXACT_C',overall_scope='WARNING_DOCUMENTARY_SYMBOLIC_ONLY',
                physical_numerical_calculations='NOT_RUN',input_audit_456='NOT_RUN',G1='OPEN',physical_READY='NO_GO')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'counts':result['counts'],'four_fixes':'PASS','negative_old':'4 FAIL_EXPECTED','OBS01':result['OBS01']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output)
