"""R1 scope-authority/preservation checks; never review target quality or extend leases."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,os
ROOT=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent;MAIN='e8f1d6bf41c0cfd2dcc4d3a673e642ecfb53588a';SID='6afb300b-1540-8191-a5c4-be1a684c20e0';TASK='T-r5-g1-supplement-output-review-01';R5='6afb0a73-b16c-8191-a539-9a6685e89034'
def run(*a):return subprocess.check_output(a,cwd=ROOT,text=True).strip()
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def main():
 checks=[]
 def check(i,ok,v):
  checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=v))
  if not ok:raise RuntimeError(i+': '+str(v))
 now=datetime.now(timezone.utc);apath='coordination/scope_amendments/'+TASK+'/DOC01-TRACE02-REVISION-01.json';am=read(apath);C=am['target_C'];H=am['request_H']
 check('actual_R1',os.getenv('CODEX_SESSION_ID')==SID,SID)
 check('fresh_main',run('gh','api','repos/narrateller/REV/git/ref/heads/main','--jq','.object.sha')==MAIN,MAIN)
 claims=[]
 for path in run('git','ls-tree','-r','--name-only',MAIN,'coordination/claims').splitlines():
  d=read(path);claims.append(d);check('claim_immutable:'+path,(ROOT/path).read_bytes()==blob(MAIN,path),sha(blob(MAIN,path)))
 base=read(am['base_claim']);check('base_sha',sha((ROOT/am['base_claim']).read_bytes())==am['base_claim_sha256']==sha((P/'base_claim_before.json').read_bytes()),am['base_claim_sha256'])
 check('same_task_owner_deadline',am['task_id']==base['task_id']==TASK and am['owner_session']==base['owner_session']==R5 and am['lease_expires_at']==base['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and now<datetime.fromisoformat(am['lease_expires_at']),dict(owner=R5,deadline=am['lease_expires_at']))
 check('no_new_task_lease_role',not any(am[k] for k in ['new_role','new_task','new_lease','lease_extension','lease_transfer']),am['activation_predicate'])
 for owner in [SID,R5]:check('one_owned_task:'+owner,sum(d.get('owner_session')==owner and d.get('status')=='ACCEPTED_MAIN' for d in claims)==1,owner)
 r1=next(d for d in claims if d.get('owner_session')==SID);check('R1_live',now<datetime.fromisoformat(r1['lease_expires_at']),r1['lease_expires_at'])
 check('new_scope_not_already_in_main',apath not in run('git','ls-tree','-r','--name-only',MAIN,'coordination/scope_amendments').splitlines(),apath)
 check('target_H_parent',run('git','rev-parse',H+'^')==C,C)
 mpath=am['target_manifest_git_locator'].split(':',1)[1];manifestbytes=blob(C,mpath);manifest=json.loads(manifestbytes)
 check('exact_target_manifest',sha(manifestbytes)==am['target_manifest_sha256'],am['target_manifest_sha256'])
 check('R5_not_target_author',R5 not in manifest['target_author_sessions'] and manifest['target_author_sessions']==[SID],manifest['target_author_sessions'])
 for row in manifest['artifacts']:check('target_seal:'+row['path'],sha(blob(C,row['path']))==row['sha256'] and blob(C,row['path'])==blob(H,row['path']),row['sha256'])
 for label,c in [('C',C),('H',H)]:check('remote_target_'+label,run('gh','api','repos/narrateller/REV/commits/'+c,'--jq','.sha')==c,c)
 pr=json.loads(run('gh','api','repos/narrateller/REV/pulls/'+str(am['source_PR'])));check('target_PR_open_exact',pr['state']=='open' and not pr['merged'] and pr['head']['sha']==H and pr['auto_merge'] is None,H)
 check('new_outputs_absent',not (ROOT/'verification/r1_g1_observation_revision_20261117').exists(),'Coordination branch has no new substantive outputs')
 opens=json.loads(run('gh','api','repos/narrateller/REV/pulls?state=open&per_page=100'));comp=[p['number'] for p in opens if p['number']!=am['source_PR'] and ('DOC01-TRACE02' in p['title'] or TASK in p['title']) and p['head']['sha']!=run('git','rev-parse','HEAD')];check('no_visible_competing_scope',not comp,comp)
 for f in ['verification/r1_g1_criteria_plan_20261117/review_target_manifest.json','verification/r1_requirements_draft_20261117/review_target_manifest.json']:
  for row in read(f)['artifacts']:check('predecessor_seal:'+row['path'],sha((ROOT/row['path']).read_bytes())==row['sha256'],row['sha256'])
 for folder in read('verification/r4_force_geometry/input_manifest.json')['protected_trees']:check('protected_tree:'+folder,not run('git','diff',MAIN,'--name-only','--',folder),'No engineering/review target modifications')
 old=read(str(P.relative_to(ROOT)/'R5_task_before_scope.json'));task=read('coordination/tasks/'+TASK+'/task.json');check('task_scope_selection',task['owner_session']==old['owner_session']==R5 and task['lease_expires_at']==old['lease_expires_at'] and task['target_C']==C and task['scope_amendment']==apath and task['output_review']=='NOT_RUN' and task['review_verdict'] is None,'New target from explicit amendment only;no old verdict reused')
 check('scope_documentary_only',not am['requirements_approved'] and not am['engineering_authorized'] and not am['source_states_solved'] and not am['target_outputs_merged_by_this_change'] and am['new_independent_review']=='NOT_RUN' and am['G1']=='OPEN','No program/G1/physics approval')
 result=dict(checked_at_utc=now.isoformat(),base_main=MAIN,scope_amendment=apath,target_C=C,request_H=H,source_PR=am['source_PR'],counts={'PASS':len(checks),'FAIL':0},checks=checks,scope='R1 authority/preservation checks only;not independent output review',new_independent_review='NOT_RUN',engineering_started=False)
 (P/'preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result['counts']))
if __name__=='__main__':main()
