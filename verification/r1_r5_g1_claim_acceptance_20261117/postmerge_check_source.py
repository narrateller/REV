from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib
ROOT=Path('/workspace/REV');TMP=Path('/tmp/rev_pr56_merge')
def run(*args):return subprocess.check_output(args,cwd=ROOT,text=True).strip()
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def api(p):return json.loads(run('gh','api',p))
C=Path('/tmp/rev_r5_claim_accept_C.txt').read_text().strip();BASE='043271b57aa3d49b6d9b45da03496ea11dad41b1'
merge=json.loads((TMP/'merge_response.json').read_text());assert merge['merged'];M=merge['sha']
run('git','fetch','origin','main');checks=[]
def check(i,ok,detail):
 checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=detail))
 if not ok:raise RuntimeError(i+': '+str(detail))
check('remote_main_exact',api('repos/narrateller/REV/git/ref/heads/main')['object']['sha']==M,M)
parents=run('git','show','-s','--format=%P',M).split();check('two_parents',parents==[BASE,C],parents)
tree=run('git','rev-parse',M+'^{tree}');check('tree_equal_exact_head',tree==run('git','rev-parse',C+'^{tree}'),tree)
for c in [C,'91b95034950e7b92eeb021035ff63dbe577c05f2','7ecdb2fefa96c0c72bf2bf009f354d705371aa28','1c374da4bb7a67b0106efa82d3f145729bc11bc7']:
 check('ancestry:'+c,subprocess.run(['git','merge-base','--is-ancestor',c,M],cwd=ROOT).returncode==0,c)
paths=run('git','ls-tree','-r','--name-only',M,'coordination/claims').splitlines();claims=[json.loads(blob(M,p)) for p in paths]
R5='6afb0a73-b16c-8191-a539-9a6685e89034';SID='6afb300b-1540-8191-a5c4-be1a684c20e0';TASK='T-r5-g1-supplement-output-review-01'
claim=next(c for c in claims if c['task_id']==TASK);now=datetime.now(timezone.utc)
check('accepted_R5_owner',claim['status']=='ACCEPTED_MAIN' and claim['owner_session']==R5,R5)
check('deadline_live_original',claim['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and now<datetime.fromisoformat(claim['lease_expires_at']),dict(now=now.isoformat(),deadline=claim['lease_expires_at']))
for owner in [R5,SID]:check('one_accepted_task:'+owner,sum(c.get('status')=='ACCEPTED_MAIN' and c.get('owner_session')==owner for c in claims)==1,owner)
for p in run('git','ls-tree','-r','--name-only',BASE,'coordination/claims').splitlines():check('old_claim_unchanged:'+p,blob(BASE,p)==blob(M,p),hashlib.sha256(blob(BASE,p)).hexdigest())
for p in ['coordination/proposals/'+TASK+'.json','coordination/claims/'+TASK+'.json']:check('claim_proposal_sealed:'+p,blob(C,p)==blob(M,p),hashlib.sha256(blob(M,p)).hexdigest())
old=json.loads(blob(BASE,'verification/r4_force_geometry/input_manifest.json'))
for folder in old['protected_trees']:check('protected_tree:'+folder,run('git','rev-parse',BASE+':'+folder)==run('git','rev-parse',M+':'+folder),folder)
p=api('repos/narrateller/REV/pulls/56');check('PR56_merged_exact',p['merged'] and p['merge_commit_sha']==M and p['head']['sha']==C,dict(head=p['head']['sha'],merge=p['merge_commit_sha']))
p55=api('repos/narrateller/REV/pulls/55');check('PR55_unmerged',p55['state']=='open' and not p55['merged'] and p55['head']['sha']=='e6ebf7f4df1dbbaa127eaa3c3d00576c1e611658' and p55['auto_merge'] is None,p55['head']['sha'])
check('PR55_target_not_merged',subprocess.run(['git','merge-base','--is-ancestor','fe10c0bc7242fe9d2df3e571c80b4e687f731d7c',M],cwd=ROOT).returncode==1,'Only claim accepted')
receipt=dict(observed_at_utc=now.isoformat(),PR=56,merge_sha=M,parents=parents,tree=tree,exact_merged_head=C,counts={'PASS':len(checks),'FAIL':0},checks=checks,R5_claim='ACCEPTED_MAIN_EFFECTIVE_WHILE_ORIGINAL_LEASE_LIVE',owner_session=R5,deadline=claim['lease_expires_at'],PR55_output_review='NOT_RUN',PR55_merged=False,engineering_started=False,source_states_solved=False,G1='OPEN',W02='NO_GO',physical_READY='NO_GO')
(TMP/'postmerge.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print('Merge',M,'postmerge',receipt['counts'])
print(run('gh','run','list','--repo','narrateller/REV','--commit',M,'--json','databaseId,headSha,event,status,conclusion,url','--limit','10'))
