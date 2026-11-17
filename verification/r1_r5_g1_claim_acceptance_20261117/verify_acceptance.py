"""R1 authority/preservation checks only. Does not review PR55 output quality."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).resolve().parent
BASE='043271b57aa3d49b6d9b45da03496ea11dad41b1'
OLD='1c374da4bb7a67b0106efa82d3f145729bc11bc7'
TARGET='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c'
REQUEST='e6ebf7f4df1dbbaa127eaa3c3d00576c1e611658'
SID='6afb300b-1540-8191-a5c4-be1a684c20e0'
R5='6afb0a73-b16c-8191-a539-9a6685e89034'
TASK='T-r5-g1-supplement-output-review-01'
def run(*args):return subprocess.check_output(args,cwd=ROOT,text=True).strip()
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def read(p):return json.loads((ROOT/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 checks=[]
 def check(i,ok,detail):
  checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=detail))
 now=datetime.now(timezone.utc)
 mainsha=run('gh','api','repos/narrateller/REV/git/ref/heads/main','--jq','.object.sha')
 check('main',mainsha==BASE,mainsha)
 check('actual_R1',os.environ.get('CODEX_SESSION_ID')==SID,os.environ.get('CODEX_SESSION_ID'))
 pr56=json.loads(run('gh','api','repos/narrateller/REV/pulls/56'))
 pr55=json.loads(run('gh','api','repos/narrateller/REV/pulls/55'))
 check('PR56_original_head',pr56['head']['sha']==OLD and pr56['base']['sha']==BASE and pr56['state']=='open' and not pr56['merged'],pr56['head']['sha'])
 check('PR55_unchanged_unmerged',pr55['head']['sha']==REQUEST and pr55['state']=='open' and not pr55['merged'] and pr55['auto_merge'] is None,pr55['head']['sha'])
 opens=json.loads(run('gh','api','repos/narrateller/REV/pulls?state=open&per_page=100'))
 competition=[p['number'] for p in opens if p['number'] not in [55,56] and (TASK in p['title'] or 'PR55' in p['title'])]
 check('no_competing_open_claim',not competition,competition)
 proposalpath='coordination/proposals/'+TASK+'.json';claimpath='coordination/claims/'+TASK+'.json'
 proposal=read(proposalpath);claim=read(claimpath)
 check('proposal_byte_unchanged',(ROOT/proposalpath).read_bytes()==blob(OLD,proposalpath),sha(blob(OLD,proposalpath)))
 check('named_owner',claim['owner_session']==R5==proposal['proposed_owner_session'] and claim['accepted_by_session']==SID,R5)
 check('original_deadline',claim['lease_expires_at']==proposal['requested_lease_expires_at'] and now<datetime.fromisoformat(claim['lease_expires_at']),claim['lease_expires_at'])
 check('R5_heartbeat_not_fabricated',claim['heartbeat_utc']==proposal['heartbeat_utc'],claim['heartbeat_utc'])
 oldpaths=run('git','ls-tree','-r','--name-only',BASE,'coordination/claims').splitlines()
 oldclaims=[json.loads(blob(BASE,p)) for p in oldpaths]
 check('no_accepted_R5_conflict',not any(x.get('task_id')==TASK or (x.get('owner_session')==R5 and x.get('status')=='ACCEPTED_MAIN') for x in oldclaims),[x['task_id'] for x in oldclaims])
 for p in oldpaths:check('old_ledger:'+p,(ROOT/p).read_bytes()==blob(BASE,p),sha(blob(BASE,p)))
 r1=next(x for x in oldclaims if x['task_id']=='T-r1-requirements-draft-01')
 check('R1_active',r1['owner_session']==SID and r1['status']=='ACCEPTED_MAIN' and now<datetime.fromisoformat(r1['lease_expires_at']),r1['lease_expires_at'])
 check('intake_released',next(x for x in oldclaims if x['task_id']=='T-r1-force-inputs-intake-01')['owner_session']=='NONE','No task overlap within same session')
 identity=read('verification/r5_g1_supplement_claim_20261117/identity.json')
 check('R5_independence_disclosed',identity['actual_session_id']==R5 and not identity['target_coauthor'] and identity['upstream_authorship_disclosure'],identity['upstream_authorship_disclosure'])
 manifest=json.loads(blob(TARGET,'verification/r1_g1_criteria_plan_20261117/review_target_manifest.json'))
 check('target_not_R5_authored',R5 not in manifest['target_author_sessions'],manifest['target_author_sessions'])
 for item in manifest['artifacts']:
  p=item['path'];check('target_seal:'+p,sha(blob(TARGET,p))==item['sha256'] and blob(TARGET,p)==blob(REQUEST,p),item['sha256'])
 inputs=json.loads(blob(TARGET,'verification/r1_g1_criteria_plan_20261117/input_manifest.json'))
 for item in inputs['inputs']:
  p=item['path'];check('input_pin:'+p,run('git','rev-parse',item['commit']+':'+p)==item['git_blob'] and sha((ROOT/p).read_bytes())==item['materialized_sha256'],item['materialized_sha256'])
 frozen=read('verification/r1_requirements_draft_20261117/review_target_manifest.json')
 for item in frozen['artifacts']:check('rev8_seal:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 old=read('verification/r4_force_geometry/input_manifest.json')
 for item in old['inputs']:check('old_pin:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 for folder in old['protected_trees']:check('main_tree_unchanged:'+folder,run('git','diff',BASE,'--name-only','--',folder)=='',BASE)
 for p in run('git','ls-tree','-r','--name-only',OLD,'verification/r5_g1_supplement_claim_20261117','handoffs/'+TASK).splitlines():check('R5_evidence:'+p,(ROOT/p).read_bytes()==blob(OLD,p),sha(blob(OLD,p)))
 for p,n,key in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json',44,'rows'),('verification/r4_force_geometry/symbolic_20261116/interfaces.json',52,'rows'),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',84,None),('verification/r3_force_path/analysis/state_matrix.json',42,None)]:
  d=read(p);check('preserved_count:'+p,len(d[key] if key else d)==n and (ROOT/p).read_bytes()==blob(BASE,p)==blob(TARGET,p),n)
 check('documentary_only',claim['review_execution']=='NOT_RUN' and claim['review_verdict'] is None and not claim['engineering_authorized'] and not claim['source_states_solved'] and not claim['requirements_approved'] and claim['G1']=='OPEN' and claim['physical_READY']=='NO_GO','No output quality verdict assigned by claim acceptance')
 result=dict(observed_at_utc=now.isoformat(),scope='R1 authority/preservation only; not independent OUTPUT review',base_main=BASE,PR56_original_head=OLD,target_C=TARGET,request_H=REQUEST,counts={s:sum(c['status']==s for c in checks) for s in ['PASS','FAIL']},checks=checks,PR55_output_review='NOT_RUN',PR55_merged=False,engineering_started=False,deadline=claim['lease_expires_at'])
 (P/'preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result['counts']));return bool(result['counts']['FAIL'])
if __name__=='__main__':raise SystemExit(main())
