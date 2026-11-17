"""Verify ordinary PR55 merge and receipt preservation; no engineering calculations."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,os
ROOT=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent
M='e8f1d6bf41c0cfd2dcc4d3a673e642ecfb53588a';H='ff688c1d50fa0fb2f2cb6f7343846c551b10d473';B='98d1494334ad5161ea8f56226c770dc762fb59d3';SID='6afb300b-1540-8191-a5c4-be1a684c20e0'
def run(*a):return subprocess.check_output(a,cwd=ROOT,text=True).strip()
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def main():
 checks=[]
 def check(i,ok,e):
  checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=e))
  if not ok:raise RuntimeError(i+': '+str(e))
 now=datetime.now(timezone.utc)
 check('actual_R1',os.getenv('CODEX_SESSION_ID')==SID,os.getenv('CODEX_SESSION_ID'))
 check('remote_main_exact',run('gh','api','repos/narrateller/REV/git/ref/heads/main','--jq','.object.sha')==M,M)
 check('two_parents',run('git','show','-s','--format=%P',M).split()==[B,H],[B,H])
 check('tree_equals_exact_head',run('git','rev-parse',M+'^{tree}')==run('git','rev-parse',H+'^{tree}'),run('git','rev-parse',M+'^{tree}'))
 pr=json.loads(run('gh','api','repos/narrateller/REV/pulls/55'));check('PR55_merged_exact',pr['merged'] and pr['merge_commit_sha']==M and pr['head']['sha']==H,dict(merged_at=pr['merged_at'],head=pr['head']['sha'],merge=pr['merge_commit_sha']))
 for c in [B,H,'ef743d993e3a30f6a414718c7634fb4265b6fe73','fe10c0bc7242fe9d2df3e571c80b4e687f731d7c','e6ebf7f4df1dbbaa127eaa3c3d00576c1e611658','1f9206312f3429c2c357b836fce11bb3d70ff74c','32c40d7ab5cc377ecc170aec0fc045b66bcb40f2','c4d511a4fe31d846b5b46f0b816d343d8de6276d','93b4aead4983f88919d8e8b4165e29d7f3246600','aadc08a70fbaee16b7ba4c16463bab97275926bb','db6b9774649f99ad1b157cba2a9c7cdeec570302','6ef3afc123004c43e007dc477241edfed8efabbb']:
  check('ancestry:'+c,subprocess.run(['git','merge-base','--is-ancestor',c,M],cwd=ROOT).returncode==0,c)
 claims=[]
 for path in run('git','ls-tree','-r','--name-only',M,'coordination/claims').splitlines():
  d=read(path);claims.append(d);check('claim_unchanged:'+path,(ROOT/path).read_bytes()==blob(B,path)==blob(M,path),sha(blob(M,path)))
 for owner in [SID,'6afb0a73-b16c-8191-a539-9a6685e89034']:
  rows=[x for x in claims if x.get('owner_session')==owner and x.get('status')=='ACCEPTED_MAIN'];check('one_live_claim:'+owner,len(rows)==1 and now<datetime.fromisoformat(rows[0]['lease_expires_at']) and rows[0]['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00',owner)
 for manifest in ['verification/r1_g1_criteria_plan_20261117/review_target_manifest.json','verification/r1_requirements_draft_20261117/review_target_manifest.json']:
  for item in read(manifest)['artifacts']:check('target_seal:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 for p in run('git','ls-tree','-r','--name-only',M,'verification/r5_g1_supplement_review').splitlines():check('R5_evidence:'+p,(ROOT/p).read_bytes()==blob(M,p),sha(blob(M,p)))
 for folder in read('verification/r4_force_geometry/input_manifest.json')['protected_trees']:check('protected_tree:'+folder,not run('git','diff',M,'--name-only','--',folder),'Unchanged from actual merged main')
 for path,n,key in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json',44,'rows'),('verification/r4_force_geometry/symbolic_20261116/interfaces.json',52,'rows'),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',84,None),('verification/r3_force_path/analysis/state_matrix.json',42,None)]:
  d=read(path);check('full_objects:'+path,len(d[key] if key else d)==n and (ROOT/path).read_bytes()==blob(M,path)==blob(B,path),n)
 task=read('coordination/tasks/T-r1-requirements-draft-01/task.json');old=read(str(P.relative_to(ROOT)/'task_before_receipt.json'))
 check('task_original_archived',(P/'task_before_receipt.json').read_bytes()==blob(M,'coordination/tasks/T-r1-requirements-draft-01/task.json'),'Exact original operational snapshot retained')
 check('task_change_limited',all(task[k]==v for k,v in old.items() if k not in ['status','active_supplement']) and task['active_supplement']['integrated_merge_sha']==M and not task['requirements_approved'],'Status/integration facts only,owner/deadline unchanged')
 obs=read('verification/r1_g1_supplement_acceptance_20261117/observation_disposition.json')['rows'];check('observations_OPEN',len(obs)==2 and all(x['status']=='OPEN' and not x['closed'] for x in obs),'DOC01/TRACE02 remain OPEN')
 changed=run('git','diff',M,'--name-only').splitlines();allowed={'ISSUES_AND_TASKS.md','coordination/tasks/T-r1-requirements-draft-01/task.json','STATE.md','NEXT_MODEL.md','handoffs/T-r1-requirements-draft-01/'+SID+'.md'}
 check('tracked_change_scope',all(p in allowed for p in changed),changed)
 new=run('git','ls-files','--others','--exclude-standard').splitlines();check('new_file_scope',all(p.startswith('verification/pr55_merge_20261117/') for p in new),new)
 out=dict(checked_at_utc=now.isoformat(),merge_sha=M,exact_merged_head=H,counts={'PASS':len(checks),'FAIL':0},checks=checks,scope='Postmerge receipt authority/preservation only',requirements_approved=False,source_states_solved=False,engineering_started=False,G1='OPEN',W02='NO_GO',physical_READY='NO_GO')
 (P/'receipt_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['counts']))
if __name__=='__main__':main()
