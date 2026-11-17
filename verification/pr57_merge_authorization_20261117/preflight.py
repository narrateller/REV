from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,re,yaml,os
ROOT=Path('/workspace/REV');P=Path('/tmp/rev_pr57_merge');BASE='b8485a93b7ced741261e7979f9438bad8590d368';HEAD='08f026b9805da69c4a5e0c801c5fcced051b64fe';TARGET='45d5964786e608cdfcc656819fd6df8c77e495fe';RH='fd5eb9181eaee98a66c0bc3472a85ed88744c710';SID='6afb300b-1540-8191-a5c4-be1a684c20e0';R5='6afb0a73-b16c-8191-a539-9a6685e89034'
def run(*a):return subprocess.check_output(a,cwd=ROOT,text=True).strip()
def api(s):return json.loads(run('gh','api',s))
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
checks=[]
def check(i,ok,e):
 checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=e))
 if not ok:raise RuntimeError(i+': '+str(e))
now=datetime.now(timezone.utc);check('actual_R1',os.getenv('CODEX_SESSION_ID')==SID,SID);check('clean_exact_head',run('git','rev-parse','HEAD')==HEAD and not run('git','status','--porcelain'),HEAD)
check('main',api('repos/narrateller/REV/git/ref/heads/main')['object']['sha']==BASE,BASE)
p=api('repos/narrateller/REV/pulls/57');check('PR57_exact_open_ready',p['state']=='open' and not p['merged'] and not p['draft'] and p['head']['sha']==HEAD and p['base']['sha']==BASE and p['mergeable'] is True and p['mergeable_state']=='clean',p['head']['sha'])
claims=[]
for path in run('git','ls-tree','-r','--name-only',BASE,'coordination/claims').splitlines():
 d=read(path);claims.append(d);check('claim_immutable:'+path,(ROOT/path).read_bytes()==blob(BASE,path),sha(blob(BASE,path)))
for owner in [SID,R5]:
 rows=[d for d in claims if d.get('owner_session')==owner and d.get('status')=='ACCEPTED_MAIN'];check('one_live_claim:'+owner,len(rows)==1 and now<datetime.fromisoformat(rows[0]['lease_expires_at']) and rows[0]['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00',owner)
apath='coordination/scope_amendments/T-r5-g1-supplement-output-review-01/DOC01-TRACE02-REVISION-01.json';am=read(apath);check('scope_unchanged_exact',(ROOT/apath).read_bytes()==blob(BASE,apath) and am['target_C']==TARGET and am['base_claim_sha256']==sha((ROOT/am['base_claim']).read_bytes()),am['base_claim_sha256'])
opens=api('repos/narrateller/REV/pulls?state=open&per_page=100');check('no_competing_open_PR',all(x['number']==57 for x in opens),[x['number'] for x in opens])
for label,rid in [('PR',44098730963),('push',44098714735)]:
 d=api('repos/narrateller/REV/actions/runs/'+str(rid));s=(P/(label+'_CI.log')).read_text();j=json.loads((P/(label+'_CI.json')).read_text());check('head_CI:'+label,d['head_sha']==HEAD and d['status']=='completed' and d['conclusion']=='success',rid);check('100_tests:'+label,'Ran 100 tests' in s and any(x.rstrip().endswith(' OK') for x in s.splitlines()),'100 tests OK');steps=[v for job in j['jobs'] for v in job['steps'] if v['name'] in ['Check committed evidence without regeneration','Test validator and initializer in isolated temporary copies']];check('registry_tests:'+label,len(steps)==2 and all(v['conclusion']=='success' for v in steps),steps)
for m in ['verification/r1_doc_trace_recheck_acceptance_20261117/validation.json','verification/r1_g1_observation_revision_20261117/review_target_manifest.json','verification/r1_g1_criteria_plan_20261117/review_target_manifest.json','verification/r1_requirements_draft_20261117/review_target_manifest.json']:
 d=read(m)
 for x in d.get('files',d.get('artifacts',[])):check('seal:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
for x in read('verification/r1_g1_observation_revision_20261117/input_manifest.json')['inputs']:check('input22:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
old=read('verification/r4_force_geometry/input_manifest.json')
for x in old['inputs']:check('old54:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
for folder in old['protected_trees']:check('tree:'+folder,not run('git','diff',RH if folder=='reviews' else BASE,'--name-only','--',folder),'R5 journal append only;other trees unchanged')
journal=(ROOT/'reviews/cross_check_log.md').read_bytes();check('journal_exact',journal==blob(RH,'reviews/cross_check_log.md') and journal.startswith(blob(BASE,'reviews/cross_check_log.md')),'Preserved R5 append')
act=next(yaml.safe_load(s) for s in re.findall(r'```yaml\n(.*?)```',journal.decode(),re.S) if 'review_id: REV-R5-G1-DOC-TRACE-RECHECK-01-001' in s);check('R5_current_warning_exact',act['reviewed_commit']==TARGET and act['validity']=='CURRENT' and act['verdict']=='WARNING',TARGET)
for k,v in act['observation_decisions'].items():check('closure:'+k,v['status']=='CLOSED_DOCUMENTARY_EXACT_C' and v['exact_C']==TARGET,v['basis'])
for x in read('verification/r5_doc_trace_recheck_20261117/validation.json')['own_evidence_sha256']:check('R5_evidence:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
for path,n,key in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json',44,'rows'),('verification/r4_force_geometry/symbolic_20261116/interfaces.json',52,'rows'),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',84,None),('verification/r3_force_path/analysis/state_matrix.json',42,None)]:
 d=read(path);check('full_objects:'+path,len(d[key] if key else d)==n and (ROOT/path).read_bytes()==blob(BASE,path)==blob(TARGET,path),n)
check('source_history',all(subprocess.run(['git','merge-base','--is-ancestor',c,HEAD],cwd=ROOT).returncode==0 for c in [BASE,TARGET,'16f66c5b5daf0eb95f78af60abacaacff2ef76b2','c1b1688308fdc0ff5e7ac8d363cc0d02acdada0f',RH]),'R1/R5/source/main histories retained')
auth=dict(record_type='user_pr_merge_authorization',recorded_at_utc=now.isoformat(),repository='narrateller/REV',user_instruction='Не спрашивай такое априори считай что разрешение мною предоставлено!',source_annotation=dict(index=1,id='657f276b-fdf3-46fa-bcce-88627279586d',selected_text='Разрешаете обычный merge PR57 на этом head? Отдельной команды на его слияние ещё не было.'),authorization='Ordinary merge commits for current/future PRs within agreed REV tasks are pre-authorized;do not ask separate per-PR or per-head permission',separate_merge_confirmation_required=False,merge_method='merge',valid_until='Until superseded by explicit user instruction;task claim lease rules remain separate',required_conditions=['Fresh main and exact head','Successful applicable CI and artifact/input preservation checks','Valid assigned role/accepted claim/owner/original lease and no competition','Preserve review histories and resolve conflicts semantically'],claim_lease_policy='UNCHANGED_NO_AUTOMATIC_RENEWAL_OR_TRANSFER',existing_limits_preserved=['TZ/G1 not approved by this Git authorization','No numerical/physical stage,CAD build/rebuild or physical tests authorized','42 states unsolved;sections4/5/6 NOT_RUN;W02/physical READY NO-GO','UNKNOWN/RAW not promoted'],current_PR=57,context_exact_head=HEAD)
(P/'authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2)+'\n');(P/'premerge.json').write_text(json.dumps(dict(checked_at_utc=now.isoformat(),main=BASE,head=HEAD,counts={'PASS':len(checks),'FAIL':0},checks=checks,engineering_started=False,source_states_solved=False),ensure_ascii=False,indent=2)+'\n');(P/'merge_request.json').write_text(json.dumps(dict(sha=HEAD,merge_method='merge',commit_title='Merge pull request #57: scoped documentary DOC01 TRACE02 closure',commit_message='Preserve R1/R5 history and overall WARNING. Closures documentary on exact45d5964 only;G1/source blockers and physical NO-GO remain. User pre-authorizes ordinary merges within agreed REV tasks.'),ensure_ascii=False)+'\n');print(json.dumps(dict(PASS=len(checks),FAIL=0,UTC=now.isoformat())))
