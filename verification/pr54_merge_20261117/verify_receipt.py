"""Check the actual PR54 merge receipt and frozen documentary scope, not physics."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,yaml
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
SID='6afb300b-1540-8191-a5c4-be1a684c20e0'

def main():
 checks=[]
 def read(p):return json.loads((ROOT/p).read_bytes())
 def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
 def sha(b):return hashlib.sha256(b).hexdigest()
 def check(n,ok,e):
  checks.append(dict(id=n,status='PASS' if ok else 'FAIL',evidence=e))
  if not ok:raise AssertionError(n)
 post=json.loads((HERE/'postmerge.json').read_text());pre=json.loads((HERE/'premerge.json').read_text());merge=post['merge_sha'];head=pre['exact_head']
 check('remote_main',git('rev-parse','origin/main').decode().strip()==merge,merge)
 check('merge_parents',git('show','-s','--format=%P',merge).decode().split()==[pre['base_main'],head],post['parents'])
 check('tree_equals_exact_head',git('rev-parse',merge+'^{tree}')==git('rev-parse',head+'^{tree}'),'Ordinary merge preserves delivered tree')
 for s in pre['source_ancestry_PASS']:check('ancestor:'+s,subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',s,merge]).returncode==0,s)
 claimpath='coordination/claims/T-r1-requirements-draft-01.json';claim=read(claimpath)
 check('claim_unchanged',(ROOT/claimpath).read_bytes()==git('show',pre['base_main']+':'+claimpath)==git('show',merge+':'+claimpath),'No renewal/transfer/takeover')
 check('owner_and_original_lease',claim['owner_session']==SID and claim['status']=='ACCEPTED_MAIN' and claim['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and datetime.now(timezone.utc)<datetime.fromisoformat(claim['lease_expires_at']),claim['lease_expires_at'])
 claims=[json.loads(git('show',merge+':'+p)) for p in git('ls-tree','-r','--name-only',merge,'coordination/claims').decode().splitlines()]
 check('single_owner_claim',[c['task_id'] for c in claims if c['owner_session']==SID and c['status']=='ACCEPTED_MAIN']==['T-r1-requirements-draft-01'],'Intake remains released/NONE')
 current=read('verification/r1_requirements_draft_20261117/review_target_manifest.json')
 for item in current['artifacts']:check('target:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'] and (ROOT/item['path']).read_bytes()==git('show',merge+':'+item['path']),item['sha256'])
 journal='reviews/cross_check_log.md';text=(ROOT/journal).read_text();records=[yaml.safe_load(b) for b in re.findall(r'^```yaml\s*\n(.*?)^```\s*$',text,re.M|re.S)]
 record=next(r for r in records if isinstance(r,dict) and r.get('review_id')=='REV-R5-REQUIREMENTS-REV8-OUTPUT-01-001')
 check('CURRENT_exact_WARNING',record['reviewed_commit']=='8d1b45afa84eca078a8de0a9822d6925dd87745b' and record['validity']=='CURRENT' and record['verdict']=='WARNING' and not record['requirements_approved'] and record['G1']=='OPEN','New review integrated without broadening')
 for item in record['artifacts']:check('reviewed:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 check('review_journal_unchanged',(ROOT/journal).read_bytes()==git('show',merge+':'+journal),'R5/old REJECT/STALE/counters unchanged by receipt')
 for item in read('verification/r5_requirements_rev8_review/validation.json')['own_evidence_sha256']:check('R5_seal:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 decisionpath='decisions/R1-REQUIREMENTS-REV8-DRAFT-ACCEPTANCE.md';decision=(ROOT/decisionpath).read_text();r=next(yaml.safe_load(b) for b in re.findall(r'^```yaml\s*\n(.*?)^```\s*$',decision,re.M|re.S))
 check('R1_decision_preserved',(ROOT/decisionpath).read_bytes()==git('show',head+':'+decisionpath) and r['gate'] is None and r['status']=='APPROVED_WITH_LIMITATIONS' and not r['requirements_approved'] and r['G1']=='OPEN','Preliminary documentary acceptance only')
 oldmanifest=read('verification/r4_force_geometry/input_manifest.json')
 for item in oldmanifest['inputs']:check('old_pin:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 for folder in oldmanifest['protected_trees']:check('protected_tree:'+folder,git('diff',merge,'--name-only','--',folder).strip()==b'',folder)
 check('44_52_42_84_15',len(read('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows'])==44 and len(read('verification/r4_force_geometry/symbolic_20261116/interfaces.json')['rows'])==52 and len(read('verification/r3_force_path/analysis/state_matrix.json'))==42 and len(read('verification/r4_force_geometry/symbolic_20261116/unknown_index.json'))==84 and len(read('verification/r1_requirements_draft_20261117/open_gaps.json')['rows'])==15,'Full frozen objects retained; states not solved')
 for p in ['verification/r4_cycle_interfaces/proposal/baseline_bindings.json','verification/r4_force_geometry/symbolic_20261116/interfaces.json','verification/r3_force_path/analysis/state_matrix.json','verification/r4_force_geometry/symbolic_20261116/unknown_index.json','verification/r1_requirements_draft_20261117/open_gaps.json','params/registry.yaml']:
  check('baseline:'+p,(ROOT/p).read_bytes()==git('show',head+':'+p),sha((ROOT/p).read_bytes()))
 ci=json.loads((HERE/'main_CI.json').read_text());check('main_CI',ci['head_sha']==merge and ci['status']=='completed' and ci['conclusion']=='success',ci['html_url'])
 for name in ['CI_44031076521.json','CI_44031066257.json']:
  c=json.loads((HERE/name).read_text());check('head_CI:'+name,c['head_sha']==head and c['conclusion']=='success',c['html_url'])
 task=read('coordination/tasks/T-r1-requirements-draft-01/task.json');oldtask=json.loads((HERE/'task_before_receipt.json').read_text())
 check('task_operational_only',task['owner_session']==oldtask['owner_session']==SID and task['lease_expires_at']==oldtask['lease_expires_at']==claim['lease_expires_at'] and task['integrated_merge_sha']==merge and not task['requirements_approved'] and not task['engineering_started'],'Only integration status/receipt metadata changed')
 check('limits',not post['requirements_approved'] and not post['architecture_selected'] and not post['source_states_solved'] and post['physical_sections']=={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'} and post['G1']=='OPEN' and post['physical_READY']=='NO_GO','No TZ/G1 approval or numerical/physical/CAD stage')
 allowed={'STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','coordination/tasks/T-r1-requirements-draft-01/task.json','handoffs/T-r1-requirements-draft-01/'+SID+'.md'}
 changed=git('diff',merge,'--name-only').decode().splitlines();check('existing_changes_scope',set(changed)<=allowed,changed)
 for p in set(changed)-{'coordination/tasks/T-r1-requirements-draft-01/task.json'}:check('history:'+p,(ROOT/p).read_bytes().endswith(git('show',merge+':'+p)),'New summary prefix only')
 unknown=git('ls-files','--others','--exclude-standard').decode().splitlines();check('new_files_scope',all(p.startswith('verification/pr54_merge_20261117/') for p in unknown),unknown)
 out=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),merge_sha=merge,counts={'PASS':len(checks),'FAIL':0},checks=checks,scope='Actual ordinary merge/claim/history/documentary receipt consistency only; not engineering validation',requirements_approved=False,source_states_solved=False,engineering_started=False,G1='OPEN',physical_READY='NO_GO')
 (HERE/'postmerge_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['counts']))
if __name__=='__main__':main()
