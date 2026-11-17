from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
ROOT=Path('/workspace/REV');TMP=Path('/tmp/rev_pr56_merge');TMP.mkdir(exist_ok=True)
C=Path('/tmp/rev_r5_claim_accept_C.txt').read_text().strip()
BASE='043271b57aa3d49b6d9b45da03496ea11dad41b1'
TARGET='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c';REQUEST='e6ebf7f4df1dbbaa127eaa3c3d00576c1e611658'
def run(*args):return subprocess.check_output(args,cwd=ROOT,text=True).strip()
def api(s):return json.loads(run('gh','api',s))
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
checks=[]
def check(i,ok,detail):
 checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=detail))
 if not ok:raise RuntimeError(i+': '+str(detail))
now=datetime.now(timezone.utc)
check('actual_R1',os.getenv('CODEX_SESSION_ID')=='6afb300b-1540-8191-a5c4-be1a684c20e0',os.getenv('CODEX_SESSION_ID'))
check('main_unchanged',api('repos/narrateller/REV/git/ref/heads/main')['object']['sha']==BASE,BASE)
p=api('repos/narrateller/REV/pulls/56');check('exact_head',p['head']['sha']==C and p['base']['sha']==BASE and p['state']=='open' and not p['merged'] and not p['draft'],p['head']['sha'])
check('mergeable',p['mergeable'] is True and p['mergeable_state']=='clean',p['mergeable_state'])
p55=api('repos/narrateller/REV/pulls/55');check('PR55_not_merged',p55['head']['sha']==REQUEST and not p55['merged'] and p55['state']=='open' and p55['auto_merge'] is None,REQUEST)
proposal=json.loads(blob(C,'coordination/proposals/T-r5-g1-supplement-output-review-01.json'))
claimpath='coordination/claims/T-r5-g1-supplement-output-review-01.json';claim=json.loads(blob(C,claimpath))
check('claim_owner',claim['owner_session']==proposal['proposed_owner_session']=='6afb0a73-b16c-8191-a539-9a6685e89034',claim['owner_session'])
check('lease_live_original',claim['lease_expires_at']==proposal['requested_lease_expires_at'] and now<datetime.fromisoformat(claim['lease_expires_at']),dict(now=now.isoformat(),deadline=claim['lease_expires_at']))
check('target_exact',claim['target_C']==TARGET and claim['request_H']==REQUEST,TARGET)
for pth in run('git','ls-tree','-r','--name-only',BASE,'coordination/claims').splitlines():
 old=json.loads(blob(BASE,pth));check('old_claim_unchanged:'+pth,blob(BASE,pth)==blob(C,pth),sha(blob(BASE,pth)))
 check('no_conflicting_owner:'+pth,old.get('task_id')!=claim['task_id'] and not (old.get('status')=='ACCEPTED_MAIN' and old.get('owner_session')==claim['owner_session']),old['task_id'])
r1=json.loads(blob(BASE,'coordination/claims/T-r1-requirements-draft-01.json'));check('R1_lease_live',r1['owner_session']==os.getenv('CODEX_SESSION_ID') and now<datetime.fromisoformat(r1['lease_expires_at']),r1['lease_expires_at'])
opens=api('repos/narrateller/REV/pulls?state=open&per_page=100');conflicts=[x['number'] for x in opens if x['number'] not in [55,56] and (claim['task_id'] in x['title'] or 'PR55' in x['title'])];check('no_competing_PR',not conflicts,conflicts)
for item in json.loads(blob(C,'verification/r1_r5_g1_claim_acceptance_20261117/validation.json'))['files']:check('C_seal:'+item['path'],sha(blob(C,item['path']))==item['sha256'],item['sha256'])
for item in json.loads(blob(TARGET,'verification/r1_g1_criteria_plan_20261117/review_target_manifest.json'))['artifacts']:check('target_seal:'+item['path'],sha(blob(TARGET,item['path']))==item['sha256'] and blob(TARGET,item['path'])==blob(REQUEST,item['path']),item['sha256'])
for item in json.loads(blob(TARGET,'verification/r1_g1_criteria_plan_20261117/input_manifest.json'))['inputs']:check('input_pin:'+item['path'],run('git','rev-parse',item['commit']+':'+item['path'])==item['git_blob'] and sha((ROOT/item['path']).read_bytes())==item['materialized_sha256'],item['materialized_sha256'])
for rid in [44048437954,44048431253]:
 d=api('repos/narrateller/REV/actions/runs/'+str(rid));check('CI:'+str(rid),d['head_sha']==C and d['status']=='completed' and d['conclusion']=='success',d['conclusion'])
 text=(TMP/(str(rid)+'.log')).read_text();check('CI_100_tests:'+str(rid),'Ran 100 tests' in text and any(x.rstrip().endswith(' OK') for x in text.splitlines()),'100 tests OK')
 (TMP/(str(rid)+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
check('working_tree_clean',run('git','status','--porcelain')=='','clean')
receipt=dict(observed_at_utc=now.isoformat(),base_main=BASE,expected_head=C,target_C=TARGET,request_H=REQUEST,deadline=claim['lease_expires_at'],checks=checks,counts={'PASS':len(checks),'FAIL':0},PR55_output_review='NOT_RUN',engineering_started=False)
(TMP/'premerge.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
payload=dict(sha=C,merge_method='merge',commit_title='Merge pull request #56: accept R5 documentary review claim',commit_message='R1 accepts a separate claim for exact PR55 output review. Preserve proposal/history/original deadline. PR55 remains unmerged; output review NOT_RUN; engineering and physical stages not authorized.')
(TMP/'merge_request.json').write_text(json.dumps(payload,ensure_ascii=False)+'\n')
print('Premerge',receipt['counts'],'head',C,'deadline',claim['lease_expires_at'])
