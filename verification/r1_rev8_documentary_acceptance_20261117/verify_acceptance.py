"""R1 integration consistency for the exact external R5 act; no independent re-review."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import hashlib,json,os,re,subprocess,yaml
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
BASE='bec317a4483e7f69c2af0aa1c52ef091bdef57b4';OLD='87f2f5889f9ba74e8eef3a3a040d936d13e0a011'
TARGET='8d1b45afa84eca078a8de0a9822d6925dd87745b';C5='04502cfe2eb2eadae242690cfad8f414bd96bff2';H5='64ac3efbffcf77e50f2e867390cf141e580de644'
SID='6afb300b-1540-8191-a5c4-be1a684c20e0';RID='REV-R5-REQUIREMENTS-REV8-OUTPUT-01-001';R5='verification/r5_requirements_rev8_review/'

def main():
 checks=[]
 def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
 def read(p):return json.loads((ROOT/p).read_bytes())
 def sha(b):return hashlib.sha256(b).hexdigest()
 def check(n,ok,e):
  checks.append(dict(id=n,status='PASS' if ok else 'FAIL',evidence=e))
  if not ok:raise AssertionError(n)
 def raw(c,p):return git('show',c+':'+p)
 def records(text):return [yaml.safe_load(b) for b in re.findall(r'^```yaml\s*\n(.*?)^```\s*$',text,re.M|re.S)]
 check('actual_R1',os.environ.get('CODEX_SESSION_ID')==SID,SID)
 check('main',git('rev-parse','origin/main').decode().strip()==BASE,BASE)
 check('R5_exact_parents',git('rev-parse',C5+'^').decode().strip()==OLD and git('rev-parse',H5+'^').decode().strip()==C5,'Source H → R5 C → R5 H')
 claim=read('coordination/claims/T-r1-requirements-draft-01.json')
 check('claim_unchanged',(ROOT/'coordination/claims/T-r1-requirements-draft-01.json').read_bytes()==raw(BASE,'coordination/claims/T-r1-requirements-draft-01.json'),'No renewal/takeover')
 check('accepted_owner_live',claim['owner_session']==SID and claim['status']=='ACCEPTED_MAIN' and claim['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and datetime.now(timezone.utc)<datetime.fromisoformat(claim['lease_expires_at']),claim['lease_expires_at'])
 oldclaim=read('coordination/claims/T-r1-force-inputs-intake-01.json')
 check('intake_released',oldclaim['owner_session']=='NONE' and oldclaim['status']=='COMPLETED_DOCUMENTARY_RELEASED' and oldclaim['lease_expires_at']=='2026-11-17T23:16:47.225017Z','Original deadline preserved')
 ident=read(R5+'identity.json')
 check('external_independence',ident['actual_session_id']=='6afb0a73-b16c-8191-a539-9a6685e89034' and ident['target_C']==TARGET and ident['request_H']==OLD and ident['target_author_sessions']==[SID] and not ident['target_coauthor'] and '853a72b' in ident['upstream_authorship_disclosure'],'R5 disclosure retained; no recertification of prior own acts')
 result=read(R5+'independent_results.json')
 check('3890_saved_results',len(result['checks'])==3890 and Counter(x['result'] for x in result['checks'])=={'PASS':3890} and result['counts']=={'PASS':3890} and result['failures']==[],'Saved independent results, not R1 oracle replay')
 check('review_scope',result['target_C']==TARGET and result['request_H']==OLD and result['approval']=='NOT_APPROVED' and result['G1']=='OPEN' and result['physical_READY']=='NO_GO' and all(x=='NOT_RUN' for x in result['physical_sections'].values()),result['scope'])
 check('22_40_16_assessments',len(result['semantic_requirements'])==22 and len(result['field_applicability'])==40 and len(result['qualitative_applicability'])==16,'Individual R5 assessments present')
 for item in result['semantic_requirements']:
  check('R5_REQ:'+item['requirement_id'],bool(item['documentary_assessment']) and bool(item['mandatory_inputs_before_acceptance']) and item['physical_validation']=='NOT_RUN',item['approval_criterion'])
 for item in result['field_applicability']:
  check('R5_field:'+item['field_id'],bool(item['own_applicability_reason']) and item['REV_realized_value'] is None and item['engineering_adoption']=='NOT_APPROVED',item['independent_disposition'])
 for item in read('verification/r1_requirements_draft_20261117/review_target_manifest.json')['artifacts']:
  current=(ROOT/item['path']).read_bytes()
  check('target:'+item['path'],sha(current)==item['sha256'] and current==raw(TARGET,item['path']),item['sha256'])
 for item in read(R5+'validation.json')['own_evidence_sha256']:
  check('R5_seal:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'] and (ROOT/item['path']).read_bytes()==raw(C5,item['path']),item['sha256'])
 for p in git('ls-tree','-r','--name-only',H5,R5).decode().splitlines():check('R5_H_file:'+p,(ROOT/p).read_bytes()==raw(H5,p),'Exact reviewer history unchanged')
 capsule='handoffs/T-r5-requirements-rev8-output-review-01/6afb0a73-b16c-8191-a539-9a6685e89034.md'
 check('R5_capsule',(ROOT/capsule).read_bytes()==raw(H5,capsule) and C5 in (ROOT/capsule).read_text(),'Exact C/H handoff preserved')
 journal='reviews/cross_check_log.md';current=(ROOT/journal).read_bytes()
 check('journal_history',current==raw(C5,journal) and current.startswith(raw(OLD,journal)),'Only R5 act appended; old REJECT/STALE/counters unchanged')
 act=next(x for x in records(current.decode()) if isinstance(x,dict) and x.get('review_id')==RID)
 check('CURRENT_exact_WARNING',act['reviewed_commit']==TARGET and act['validity']=='CURRENT' and act['verdict']=='WARNING' and not act['requirements_approved'] and act['G1']=='OPEN' and not act['source_states_solved'] and not act['lease_extension'],'Narrow documentary scope')
 for item in act['artifacts']:check('reviewed_artifact:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 old_manifest=read('verification/r4_force_geometry/input_manifest.json')
 for item in old_manifest['inputs']:check('old_pin:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 changed_protected=git('diff',OLD,'--name-only','--',*old_manifest['protected_trees']).decode().splitlines()
 check('12_protected_trees',changed_protected==[journal],changed_protected)
 for item in result['lfs_files']:check('LFS_preserved:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256']==item['git_lfs_oid'],item['sha256'])
 for p in ['verification/r4_cycle_interfaces/proposal/baseline_bindings.json','verification/r4_force_geometry/symbolic_20261116/interfaces.json','verification/r3_force_path/analysis/state_matrix.json','verification/r4_force_geometry/symbolic_20261116/unknown_index.json','verification/r1_requirements_draft_20261117/open_gaps.json','params/registry.yaml']:
  check('whole_baseline:'+p,(ROOT/p).read_bytes()==raw(OLD,p),sha((ROOT/p).read_bytes()))
 check('44_52_42_84_15',len(read('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows'])==44 and len(read('verification/r4_force_geometry/symbolic_20261116/interfaces.json')['rows'])==52 and len(read('verification/r3_force_path/analysis/state_matrix.json'))==42 and len(read('verification/r4_force_geometry/symbolic_20261116/unknown_index.json'))==84 and len(read('verification/r1_requirements_draft_20261117/open_gaps.json')['rows'])==15,'Full objects preserved; states not solved')
 candidate=yaml.safe_load((ROOT/'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml').read_text());params=[p for d in candidate['domains'].values() for p in d.values()]
 check('RAW40_unchanged',len(params)==40 and all(p['lifecycle']=='RAW' and p['verifier'] is None and p['calculation'] is None for p in params) and (ROOT/'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml').read_bytes()==raw(OLD,'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml'),'No promotion/adoption')
 decision_path='decisions/R1-REQUIREMENTS-REV8-DRAFT-ACCEPTANCE.md';decision=next(x for x in records((ROOT/decision_path).read_text()) if isinstance(x,dict) and x.get('record_type')=='decision')
 check('R1_scope_limited',decision['gate'] is None and decision['status']=='APPROVED_WITH_LIMITATIONS' and decision['baseline_commit']==C5 and decision['reviewed_source_C']==TARGET and decision['review_ids']==[RID] and not decision['requirements_approved'] and not decision['architecture_selected'] and decision['G1']=='OPEN' and decision['physical_READY']=='NO_GO','R1 documentary disposition is not independent review or TZ approval')
 for item in decision['artifacts']:check('decision_evidence:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 task=read('coordination/tasks/T-r1-requirements-draft-01/task.json');prior=json.loads((HERE/'task_before_disposition.json').read_text())
 check('operational_task_only',task['owner_session']==prior['owner_session']==SID and task['lease_expires_at']==prior['lease_expires_at']==claim['lease_expires_at'] and task['output_review']=='WARNING_PRELIMINARY_DRAFT_ONLY' and not task['requirements_approved'] and not task['engineering_started'],'Operational disposition changes do not alter reviewed target')
 for p in ['STATE.md','NEXT_MODEL.md']:
  check('R5_history:'+p,(ROOT/p).read_bytes().endswith(raw(H5,p)),'R5 H prefix/history preserved verbatim; R1 summary may prepend')
 changed=git('diff',OLD,'--name-only').decode().splitlines()
 allowed={'STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md',journal,decision_path,'coordination/tasks/T-r1-requirements-draft-01/task.json','handoffs/T-r1-requirements-draft-01/'+SID+'.md',capsule}
 check('existing_change_scope',all(p in allowed or p.startswith((R5,'verification/r1_rev8_documentary_acceptance_20261117/')) for p in changed),changed)
 data=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),main=BASE,target_C=TARGET,original_PR54_head=OLD,R5_C=C5,R5_H=H5,counts={'PASS':len(checks),'FAIL':0},checks=checks,R5_independent_checks={'PASS':3890,'FAIL':0},new_independent_R1_review=False,requirements_approved=False,source_states_solved=False,main_merged=False,engineering_started=False)
 (HERE/'integration_checks.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print(json.dumps(data['counts']))
if __name__=='__main__':main()
