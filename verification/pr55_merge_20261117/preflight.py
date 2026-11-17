from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,os,re,yaml
ROOT=Path('/workspace/REV');P=Path('/tmp/rev_pr55_merge')
BASE='98d1494334ad5161ea8f56226c770dc762fb59d3';HEAD='ff688c1d50fa0fb2f2cb6f7343846c551b10d473';TARGET='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c';R5H='32c40d7ab5cc377ecc170aec0fc045b66bcb40f2';SID='6afb300b-1540-8191-a5c4-be1a684c20e0';R5='6afb0a73-b16c-8191-a539-9a6685e89034'
def run(*a):return subprocess.check_output(a,cwd=ROOT,text=True).strip()
def api(p):return json.loads(run('gh','api',p))
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def read(p):return json.loads((ROOT/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
checks=[]
def check(i,ok,v):
 checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=v))
 if not ok:raise RuntimeError(i+': '+str(v))
now=datetime.now(timezone.utc)
check('actual_R1',os.getenv('CODEX_SESSION_ID')==SID,os.getenv('CODEX_SESSION_ID'))
check('clean_exact_checkout',run('git','rev-parse','HEAD')==HEAD and not run('git','status','--porcelain'),HEAD)
check('fresh_main',api('repos/narrateller/REV/git/ref/heads/main')['object']['sha']==BASE,BASE)
p=api('repos/narrateller/REV/pulls/55');check('PR55_exact_open_ready',p['state']=='open' and not p['merged'] and not p['draft'] and p['head']['sha']==HEAD and p['base']['sha']==BASE and p['mergeable'] is True and p['mergeable_state']=='clean' and p['auto_merge'] is None,dict(head=p['head']['sha'],base=p['base']['sha'],mergeable_state=p['mergeable_state']))
claimpaths=run('git','ls-tree','-r','--name-only',BASE,'coordination/claims').splitlines();claims=[json.loads(blob(BASE,x)) for x in claimpaths]
for owner,task in [(SID,'T-r1-requirements-draft-01'),(R5,'T-r5-g1-supplement-output-review-01')]:
 d=next(x for x in claims if x['task_id']==task)
 check('live_claim:'+task,d['status']=='ACCEPTED_MAIN' and d['owner_session']==owner and d['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and now<datetime.fromisoformat(d['lease_expires_at']),dict(owner=owner,now=now.isoformat(),deadline=d['lease_expires_at']))
 check('one_owned_task:'+owner,sum(x.get('owner_session')==owner and x.get('status')=='ACCEPTED_MAIN' for x in claims)==1,owner)
for path in claimpaths:check('claim_immutable:'+path,(ROOT/path).read_bytes()==blob(BASE,path)==blob(HEAD,path),sha(blob(BASE,path)))
check('intake_released',next(x for x in claims if x['task_id']=='T-r1-force-inputs-intake-01')['owner_session']=='NONE','Earlier intake remains released')
opens=api('repos/narrateller/REV/pulls?state=open&per_page=100');check('competition',all(x['number']==55 for x in opens),[x['number'] for x in opens])
for label,rid in [('PR',44066704720),('push',44066694376)]:
 d=api('repos/narrateller/REV/actions/runs/'+str(rid));s=(P/(label+'_CI.log')).read_text();j=json.loads((P/(label+'_CI.json')).read_text())
 check('head_CI:'+label,d['head_sha']==HEAD and d['status']=='completed' and d['conclusion']=='success',dict(run=rid,conclusion=d['conclusion']))
 check('100_tests:'+label,'Ran 100 tests' in s and any(x.rstrip().endswith(' OK') for x in s.splitlines()),'100 tests OK')
 steps=[x for job in j['jobs'] for x in job['steps'] if x['name'] in ['Check committed evidence without regeneration','Test validator and initializer in isolated temporary copies']]
 check('registry_tests_steps:'+label,len(steps)==2 and all(x['conclusion']=='success' for x in steps),steps)
main_ci=api('repos/narrateller/REV/actions/runs/44049371735');check('existing_main_CI',main_ci['head_sha']==BASE and main_ci['status']=='completed' and main_ci['conclusion']=='success','44049371735 SUCCESS')
for m in ['verification/r1_g1_supplement_acceptance_20261117/validation.json','verification/r1_g1_criteria_plan_20261117/review_target_manifest.json','verification/r1_requirements_draft_20261117/review_target_manifest.json']:
 d=read(m)
 for item in d.get('files',d.get('artifacts',[])):check('seal:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
for item in read('verification/r1_g1_criteria_plan_20261117/input_manifest.json')['inputs']:check('input31:'+item['path'],run('git','rev-parse',item['commit']+':'+item['path'])==item['git_blob'] and sha((ROOT/item['path']).read_bytes())==item['materialized_sha256'],item['materialized_sha256'])
old=read('verification/r4_force_geometry/input_manifest.json')
for item in old['inputs']:check('input54:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
for folder in old['protected_trees']:check('tree:'+folder,not run('git','diff',R5H if folder=='reviews' else BASE,'--name-only','--',folder),'R5 journal append preserved; other protected trees unchanged')
for p,n,key in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json',44,'rows'),('verification/r4_force_geometry/symbolic_20261116/interfaces.json',52,'rows'),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',84,None),('verification/r3_force_path/analysis/state_matrix.json',42,None)]:
 d=read(p);check('full_object:'+p,len(d[key] if key else d)==n and (ROOT/p).read_bytes()==blob(BASE,p)==blob(TARGET,p),n)
journal=(ROOT/'reviews/cross_check_log.md').read_bytes();check('R5_journal_unchanged',journal==blob(R5H,'reviews/cross_check_log.md') and journal.startswith(blob(BASE,'reviews/cross_check_log.md')),'Exact immutable R5 append')
act=next(yaml.safe_load(s) for s in re.findall(r'```yaml\n(.*?)```',journal.decode(),re.S) if 'review_id: REV-R5-G1-SUPPLEMENT-OUTPUT-01-001' in s);check('R5_review_exact_warning',act['reviewed_commit']==TARGET and act['verdict']=='WARNING' and act['validity']=='CURRENT' and act['reviewer']['session_id']==R5,TARGET)
for item in read('verification/r5_g1_supplement_review/validation.json')['own_evidence_sha256']:check('R5_evidence:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
obs=read('verification/r1_g1_supplement_acceptance_20261117/observation_disposition.json')['rows'];check('two_obs_OPEN',{x['id'] for x in obs}=={'R5-G1-DOC-01','R5-G1-TRACE-02'} and all(x['status']=='OPEN' and not x['closed'] for x in obs),'No automatic closure')
dec=next(yaml.safe_load(s) for s in re.findall(r'```yaml\n(.*?)```',(ROOT/'decisions/R1-G1-SUPPLEMENT-DOCUMENTARY-ACCEPTANCE.md').read_text(),re.S));check('no_G1_TZ_approval',dec['gate'] is None and not dec['requirements_approved'] and not dec['source_states_solved'] and dec['G1']=='OPEN' and dec['physical_READY']=='NO_GO','Preliminary documentary acceptance only')
ancestors=['98d1494334ad5161ea8f56226c770dc762fb59d3','ef743d993e3a30f6a414718c7634fb4265b6fe73','1f9206312f3429c2c357b836fce11bb3d70ff74c',R5H,TARGET,'c4d511a4fe31d846b5b46f0b816d343d8de6276d','93b4aead4983f88919d8e8b4165e29d7f3246600','aadc08a70fbaee16b7ba4c16463bab97275926bb','db6b9774649f99ad1b157cba2a9c7cdeec570302','6ef3afc123004c43e007dc477241edfed8efabbb','beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe','3784efa32ca26547f2581101474d6188f000c348']
for c in ancestors:check('ancestry:'+c,subprocess.run(['git','merge-base','--is-ancestor',c,HEAD],cwd=ROOT).returncode==0,c)
result=dict(observed_at_utc=now.isoformat(),main=BASE,exact_head=HEAD,checks=checks,counts={'PASS':len(checks),'FAIL':0},deadline='2026-11-18T01:58:30.990734+00:00',source_states_solved=False,requirements_approved=False,engineering_started=False,G1='OPEN',W02='NO_GO',physical_READY='NO_GO')
(P/'premerge.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(P/'authorization.json').write_text(json.dumps(dict(user_instruction='делай',context='Explicit yes to R1 question authorizing ordinary merge PR55 exact head '+HEAD,recorded_at_utc=now.isoformat(),authorized_head=HEAD,merge_method='merge',scope='Integrate preliminary documentary WARNING package;no TZ/G1/engineering authority'),ensure_ascii=False,indent=2)+'\n')
(P/'merge_request.json').write_text(json.dumps(dict(sha=HEAD,merge_method='merge',commit_title='Merge pull request #55: preliminary G1 supplement with WARNING',commit_message='Preserve R1/R5 histories and evidence. Documentary preliminary acceptance only; DOC01/TRACE02 and B01/B02/B03/source issues OPEN. G1 OPEN,42 states unsolved;no numerical,physical or CAD rebuild authority.'),ensure_ascii=False)+'\n')
print(json.dumps(result['counts']),now.isoformat())
