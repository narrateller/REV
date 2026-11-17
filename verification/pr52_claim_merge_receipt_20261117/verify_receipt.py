"""Verify actual PR52 integration receipt and task preparation; no engineering review."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,hashlib,re,yaml
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SESSION='6afb300b-1540-8191-a5c4-be1a684c20e0'

def main():
 checks=[]
 def check(name,condition,evidence):
  checks.append(dict(id=name,status='PASS' if condition else 'FAIL',evidence=evidence))
  if not condition:raise AssertionError(name)
 def read(path):return json.loads((ROOT/path).read_bytes())
 def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
 def sha(raw):return hashlib.sha256(raw).hexdigest()
 post=json.loads((HERE/'postmerge.json').read_text());merge=post['merge_sha'];pre=json.loads((HERE/'premerge.json').read_text())
 check('remote_main',git('rev-parse','origin/main').decode().strip()==merge,merge)
 check('normal_merge',git('show','-s','--format=%P',merge).decode().split()==[pre['expected_main'],pre['expected_head']],post['parents'])
 check('tree_equals_head',git('rev-parse',merge+'^{tree}')==git('rev-parse',pre['expected_head']+'^{tree}'),'Exact delivered tree')
 for s in post['source_ancestry_PASS']:
  check('ancestor:'+s,subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',s,merge]).returncode==0,s)
 ledger='coordination/claims/T-r1-force-inputs-intake-01.json';claim=read(ledger)
 check('ledger_in_main',(ROOT/ledger).read_bytes()==git('show',merge+':'+ledger),'Exact separate ownership record accepted')
 check('owner',post['claim_effective'] and claim['owner_session']==SESSION and len([x for x in [post['accepted_owner']] if x['owner_session']==SESSION])==1,post['accepted_owner'])
 check('lease_live_unchanged',claim['lease_expires_at']=='2026-11-17T23:16:47.225017Z' and not claim['lease_extension'] and datetime.now(timezone.utc)<datetime.fromisoformat(claim['lease_expires_at'].replace('Z','+00:00')),claim['lease_expires_at'])
 proposal='verification/r1_force_inputs_intake/claim.json';source='f2cbd96bb78c915dca74cb4eb29daffbb52ee172'
 for path in git('ls-tree','-r','--name-only',source,'verification/r1_force_inputs_intake').decode().splitlines():
  check('reviewed_packet:'+path,git('rev-parse',merge+':'+path)==git('rev-parse',source+':'+path),path)
 check('historical_proposal',read(proposal)['owner_session']=='NONE' and read(proposal)['lease_expires_at'] is None,'Snapshot differs intentionally from separate live ledger')
 for item in read('verification/r5_reference_intake_review/validation.json')['package_files']:
  check('R5_evidence:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 ci=json.loads((HERE/'main_CI.json').read_text())
 check('main_CI',ci['head_sha']==merge and ci['status']=='completed' and ci['conclusion']=='success',ci['html_url'])
 for name in ['CI_43990503134.json','CI_43990494133.json']:
  d=json.loads((HERE/name).read_text());check('exact_head_CI:'+name,d['head_sha']==pre['expected_head'] and d['conclusion']=='success',d['html_url'])
 nextpath='coordination/tasks/T-r1-requirements-draft-01/';task=read(nextpath+'task.json')
 check('next_task_only',task['owner_session']=='NONE' and task['lease_expires_at'] is None and task['claim_status']=='NOT_ACCEPTED' and not task['execution_authorized'] and not task['engineering_started'],task['status'])
 for item in read(nextpath+'task_input_manifest.json')['inputs']:
  check('next_task_pin:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'] and git('rev-parse',merge+':'+item['path']).decode().strip()==item['git_blob'],item['sha256'])
 for path in ['requirements/system_requirements.md','requirements/verification_matrix.md','params/registry.yaml','reviews/cross_check_log.md','verification/r4_force_geometry/claim.json']:
  check('unmodified:'+path,(ROOT/path).read_bytes()==git('show',merge+':'+path),path)
 req=(ROOT/'requirements/system_requirements.md').read_text();val=(ROOT/'requirements/verification_matrix.md').read_text()
 check('22_requirements_preserved',{f'REQ-REV-{i:02d}' for i in range(1,23)} <=set(re.findall(r'REQ-REV-\d+',req)),'Future revision has not begun')
 check('22_validation_rows_preserved',{f'VAL-REV-{i:02d}' for i in range(1,23)}<=set(re.findall(r'VAL-REV-\d+',val)),'NOT_RUN retained')
 cand=yaml.safe_load((ROOT/'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml').read_text())
 params=[v for d in cand['domains'].values() for v in d.values()]
 check('40_RAW',len(params)==40 and all(x['lifecycle']=='RAW' and x['verifier'] is None and x['calculation'] is None for x in params),'No active promotion')
 check('84_52_42_44',len(read('verification/r4_force_geometry/symbolic_20261116/unknown_index.json'))==84 and len(read('verification/r4_force_geometry/symbolic_20261116/interfaces.json')['rows'])==52 and len(read('verification/r3_force_path/analysis/state_matrix.json'))==42 and len(read('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows'])==44,'Full frozen objects preserved; 42 states not solved')
 check('no_engineering',not post['engineering_started'] and post['input_audit_456']=='NOT_RUN' and post['G1']=='OPEN' and post['physical_READY']=='NO_GO','Numerical/physical/CAD stage excluded')
 changed=git('diff',merge,'--name-only').decode().splitlines()
 summary={'ISSUES_AND_TASKS.md','STATE.md','NEXT_MODEL.md','handoffs/T-r1-force-inputs-intake-01/'+SESSION+'.md'}
 check('existing_changes_scope',set(changed)<=summary,changed)
 for path in changed:check('history:'+path,(ROOT/path).read_bytes().endswith(git('show',merge+':'+path)),'New prefix only')
 untracked=git('ls-files','--others','--exclude-standard').decode().splitlines()
 check('new_files_scope',all(p.startswith(('verification/pr52_claim_merge_receipt_20261117/','coordination/tasks/T-r1-requirements-draft-01/','handoffs/T-r1-requirements-draft-01/')) for p in untracked),untracked)
 result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),merge_sha=merge,counts={'PASS':len(checks),'FAIL':0},checks=checks,source_states_solved=False,engineering_started=False,next_task_claim_accepted=False,independent_engineering_review=False)
 (HERE/'postmerge_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result['counts']))
if __name__=='__main__':main()
