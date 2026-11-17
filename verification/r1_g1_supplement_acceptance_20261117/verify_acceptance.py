"""R1 integration authority/preservation checks; not independent review of own target."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess,tempfile,yaml
ROOT=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent
MAIN='98d1494334ad5161ea8f56226c770dc762fb59d3';OURS='c4d511a4fe31d846b5b46f0b816d343d8de6276d';TARGET='fe10c0bc7242fe9d2df3e571c80b4e687f731d7c';REQUEST='e6ebf7f4df1dbbaa127eaa3c3d00576c1e611658';RC='1f9206312f3429c2c357b836fce11bb3d70ff74c';RH='32c40d7ab5cc377ecc170aec0fc045b66bcb40f2';SID='6afb300b-1540-8191-a5c4-be1a684c20e0';R5='6afb0a73-b16c-8191-a539-9a6685e89034'
def run(*args):return subprocess.check_output(args,cwd=ROOT,text=True).strip()
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def main():
 checks=[]
 def check(i,ok,evidence):checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=evidence))
 now=datetime.now(timezone.utc)
 check('actual_R1',os.environ.get('CODEX_SESSION_ID')==SID,os.environ.get('CODEX_SESSION_ID'))
 check('remote_main',run('gh','api','repos/narrateller/REV/git/ref/heads/main','--jq','.object.sha')==MAIN,MAIN)
 pr=json.loads(run('gh','api','repos/narrateller/REV/pulls/55'));check('PR55_original_head_open',pr['state']=='open' and not pr['merged'] and pr['head']['sha']==REQUEST and pr['auto_merge'] is None,pr['head']['sha'])
 check('merge_parents',run('git','rev-parse','HEAD')==OURS and run('git','rev-parse','MERGE_HEAD')==RH,[OURS,RH])
 check('all_conflicts_resolved',not run('git','diff','--name-only','--diff-filter=U'),'Semantic prefix/history merge')
 for p,owner in [('coordination/claims/T-r1-requirements-draft-01.json',SID),('coordination/claims/T-r5-g1-supplement-output-review-01.json',R5)]:
  d=read(p);check('live_owner:'+p,d['status']=='ACCEPTED_MAIN' and d['owner_session']==owner and now<datetime.fromisoformat(d['lease_expires_at']),dict(owner=owner,deadline=d['lease_expires_at']))
  check('immutable_claim:'+p,(ROOT/p).read_bytes()==blob(MAIN,p),sha(blob(MAIN,p)))
 claims=[json.loads(blob(MAIN,p)) for p in run('git','ls-tree','-r','--name-only',MAIN,'coordination/claims').splitlines()]
 for owner in [SID,R5]:check('one_accepted_task:'+owner,sum(d.get('owner_session')==owner and d.get('status')=='ACCEPTED_MAIN' for d in claims)==1,owner)
 opens=json.loads(run('gh','api','repos/narrateller/REV/pulls?state=open&per_page=100'));check('no_competing_open_PR',all(p['number']==55 for p in opens),[p['number'] for p in opens])
 journal=(ROOT/'reviews/cross_check_log.md').read_bytes();check('R5_journal_exact',journal==blob(RH,'reviews/cross_check_log.md') and journal.startswith(blob(MAIN,'reviews/cross_check_log.md')),'Only immutable R5 append beyond main')
 act=next(yaml.safe_load(s) for s in re.findall(r'```yaml\n(.*?)```',journal.decode(),re.S) if 'review_id: REV-R5-G1-SUPPLEMENT-OUTPUT-01-001' in s)
 check('exact_R5_review',act['reviewed_commit']==TARGET and act['reviewer']['session_id']==R5 and act['verdict']=='WARNING' and act['validity']=='CURRENT',dict(reviewed_commit=act['reviewed_commit'],verdict=act['verdict']))
 identity=read('verification/r5_g1_supplement_review/identity.json');check('independence_disclosed',not identity['target_coauthor'] and R5 not in identity['target_author_sessions'] and identity['upstream_authorship_disclosure'],identity['upstream_authorship_disclosure'])
 result=read('verification/r5_g1_supplement_review/independent_results.json');check('R5_own4117',result['counts']=={'PASS':4117} and not result['failures'] and result['target_C']==TARGET,'R5 evidence only,not R1 independent checks')
 for k,n in [('requirement_and_metrology_assessments',22),('channel_assessments',11),('hazard_assessments',20),('normative_assessments',6),('source_action_assessments',3)]:check('R5_coverage:'+k,len(result[k])==n,n)
 for f in run('git','ls-tree','-r','--name-only',RH,'verification/r5_g1_supplement_review','handoffs/T-r5-g1-supplement-output-review-01').splitlines():check('R5_evidence:'+f,(ROOT/f).read_bytes()==blob(RH,f),sha(blob(RH,f)))
 for item in read('verification/r5_g1_supplement_review/validation.json')['own_evidence_sha256']:check('R5_seal:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 for m in ['verification/r1_g1_criteria_plan_20261117/review_target_manifest.json','verification/r1_requirements_draft_20261117/review_target_manifest.json']:
  for item in read(m)['artifacts']:check('frozen:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 for item in read('verification/r1_g1_criteria_plan_20261117/input_manifest.json')['inputs']:check('input31:'+item['path'],run('git','rev-parse',item['commit']+':'+item['path'])==item['git_blob'] and sha((ROOT/item['path']).read_bytes())==item['materialized_sha256'],item['materialized_sha256'])
 old=read('verification/r4_force_geometry/input_manifest.json')
 for item in old['inputs']:check('old54:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 for folder in old['protected_trees']:
  expected=RH if folder=='reviews' else MAIN
  check('protected_tree:'+folder,not run('git','diff',expected,'--name-only','--',folder),dict(expected=expected,scope='R5 append preserved for reviews; other trees unchanged from main'))
 for p,n,key in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json',44,'rows'),('verification/r4_force_geometry/symbolic_20261116/interfaces.json',52,'rows'),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',84,None),('verification/r3_force_path/analysis/state_matrix.json',42,None)]:
  d=read(p);check('full_object_preservation:'+p,len(d[key] if key else d)==n and (ROOT/p).read_bytes()==blob(MAIN,p)==blob(TARGET,p),n)
 candidate=yaml.safe_load((ROOT/'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml').read_text());params=[v for d in candidate['domains'].values() for v in d.values()];check('40_RAW',len(params)==40 and all(x['lifecycle']=='RAW' and x['verifier'] is None for x in params),'No maturity promotion')
 lfs=run('git','lfs','ls-files','-l').splitlines();check('59_LFS',len(lfs)==59,len(lfs))
 for line in lfs:
  oid,_,p=line.split(' ',2);check('LFS:'+p,sha((ROOT/p).read_bytes())==oid,oid)
 observations=read(str(P.relative_to(ROOT)/'observation_disposition.json'))['rows'];check('two_observations_OPEN',{x['id'] for x in observations}=={'R5-G1-DOC-01','R5-G1-TRACE-02'} and all(x['status']=='OPEN' and not x['closed'] and x['documentary_owner_session']==SID and x['new_independent_review']=='NOT_RUN' for x in observations),'Follow-up plan only,not target correction or review closure')
 dec=next(yaml.safe_load(s) for s in re.findall(r'```yaml\n(.*?)```',(ROOT/'decisions/R1-G1-SUPPLEMENT-DOCUMENTARY-ACCEPTANCE.md').read_text(),re.S));check('limited_decision',dec['gate'] is None and dec['status']=='APPROVED_WITH_LIMITATIONS' and not dec['requirements_approved'] and not dec['source_states_solved'] and dec['G1']=='OPEN','No gate/engineering approval')
 for p in ['STATE.md','NEXT_MODEL.md','handoffs/T-r1-requirements-draft-01/'+SID+'.md']:
  check('exact_R5_history:'+p,blob(RH,p) in (ROOT/p).read_bytes(),'Whole R5 handoff retained')
 replay=[]
 with tempfile.TemporaryDirectory(prefix='rev-r1-integration-replay-') as tmp:
  subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'verification/r1_g1_criteria_plan_20261117/build_plan.py'),'--output-dir',tmp],cwd=ROOT,check=True,capture_output=True)
  for item in read('verification/r1_g1_criteria_plan_20261117/reproducibility.json')['outputs']:
   p=item['path'];same=(Path(tmp)/p).read_bytes()==(ROOT/p).read_bytes();check('reproduce:'+p,same,item['sha256']);replay.append(dict(path=p,result='MATCH' if same else 'FAIL',sha256=sha((ROOT/p).read_bytes())))
 (P/'renderer_replay.json').write_text(json.dumps(dict(scope='R1 integration reproduction,not new independent review',outputs=replay),ensure_ascii=False,indent=2)+'\n')
 out=dict(checked_at_utc=now.isoformat(),scope='R1 authority/preservation/integration reproduction only',main=MAIN,R1_parent=OURS,R5_H=RH,target_C=TARGET,counts={s:sum(x['status']==s for x in checks) for s in ['PASS','FAIL']},checks=checks,R5_independent_counts={'PASS':4117,'FAIL':0},requirements_approved=False,source_states_solved=False,engineering_started=False,PR55_merged=False)
 (P/'integration_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['counts']));return bool(out['counts']['FAIL'])
if __name__=='__main__':raise SystemExit(main())
