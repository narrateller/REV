"""R1 closure disposition/integration checks, not independent re-review of own target."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,re,os,tempfile,yaml
ROOT=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent;MAIN='b8485a93b7ced741261e7979f9438bad8590d368';TARGET='45d5964786e608cdfcc656819fd6df8c77e495fe';REQUEST='2b99776187345729f1c3e177d0e5ed83e1239b07';RH='fd5eb9181eaee98a66c0bc3472a85ed88744c710';RID='REV-R5-G1-DOC-TRACE-RECHECK-01-001';SID='6afb300b-1540-8191-a5c4-be1a684c20e0';R5='6afb0a73-b16c-8191-a539-9a6685e89034'
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
 check('actual_R1',os.getenv('CODEX_SESSION_ID')==SID,SID);check('main',run('gh','api','repos/narrateller/REV/git/ref/heads/main','--jq','.object.sha')==MAIN,MAIN)
 pr=json.loads(run('gh','api','repos/narrateller/REV/pulls/57'));check('PR57_original_head_open',pr['state']=='open' and not pr['merged'] and pr['head']['sha']==REQUEST and pr['auto_merge'] is None,pr['head']['sha'])
 opens=json.loads(run('gh','api','repos/narrateller/REV/pulls?state=open&per_page=100'));check('no_competing_open_PR',all(x['number']==57 for x in opens),[x['number'] for x in opens])
 claims=[]
 for p in run('git','ls-tree','-r','--name-only',MAIN,'coordination/claims').splitlines():
  d=read(p);claims.append(d);check('frozen_claim:'+p,(ROOT/p).read_bytes()==blob(MAIN,p),sha(blob(MAIN,p)))
 for owner in [SID,R5]:
  rows=[x for x in claims if x.get('owner_session')==owner and x.get('status')=='ACCEPTED_MAIN'];check('one_live_original_claim:'+owner,len(rows)==1 and now<datetime.fromisoformat(rows[0]['lease_expires_at']) and rows[0]['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00',owner)
 ap='coordination/scope_amendments/T-r5-g1-supplement-output-review-01/DOC01-TRACE02-REVISION-01.json';am=read(ap)
 check('scope_immutable_and_exact',(ROOT/ap).read_bytes()==blob(MAIN,ap) and am['target_C']==TARGET and am['request_H']==REQUEST and am['owner_session']==R5 and am['base_claim_sha256']==sha((ROOT/am['base_claim']).read_bytes()),am['base_claim_sha256'])
 journal=(ROOT/'reviews/cross_check_log.md').read_bytes();check('R5_journal_exact',journal==blob(RH,'reviews/cross_check_log.md') and journal.startswith(blob(MAIN,'reviews/cross_check_log.md')),'Only exact R5 append beyond main')
 act=next(yaml.safe_load(x) for x in re.findall(r'```yaml\n(.*?)```',journal.decode(),re.S) if 'review_id: '+RID in x);check('current_exact_R5_act',act['reviewed_commit']==TARGET and act['reviewer']['session_id']==R5 and act['verdict']=='WARNING' and act['validity']=='CURRENT',dict(review=RID,target=TARGET))
 for key in ['R5-G1-DOC-01','R5-G1-TRACE-02']:
  d=act['observation_decisions'][key];check('closure:'+key,d['status']=='CLOSED_DOCUMENTARY_EXACT_C' and d['exact_C']==TARGET and not d['failing_guards'],d['basis'])
 for key in ['R5-TZ-B01','R5-TZ-B02','R5-TZ-B03','SOURCE-POWER','SOURCE-PRESSURE-UNIT','SOURCE-MOISTURE-BASIS']:check('remaining_OPEN:'+key,next(x for x in act['findings'] if x['id']==key)['status']=='OPEN','Not closed by documentary notes')
 results=read('verification/r5_doc_trace_recheck_20261117/independent_results.json');check('R5_counts',results['counts']=={'PASS':3804} and not results['failures'] and results['target_C']==TARGET,'Own R5 evidence,not author332/old4117')
 for key,n in [('card_assessments',22),('metrology_assessments',22),('channel_assessments',12),('hazard_assessments',20),('assurance_assessments',4),('route_assessments',2),('semantic_policy_cases',8)]:check('R5_coverage:'+key,len(results[key])==n,n)
 identity=read('verification/r5_doc_trace_recheck_20261117/identity.json');check('independence',identity['actual_session_id']==R5 and not identity['target_coauthor'] and identity['upstream_disclosure'] and R5 not in identity['target_author_sessions'],'Not target author;upstream disclosed')
 for p in run('git','ls-tree','-r','--name-only',RH,'verification/r5_doc_trace_recheck_20261117','handoffs/T-r5-g1-supplement-output-review-01').splitlines():check('R5_evidence:'+p,(ROOT/p).read_bytes()==blob(RH,p),sha(blob(RH,p)))
 for x in read('verification/r5_doc_trace_recheck_20261117/validation.json')['own_evidence_sha256']:check('R5_seal:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
 for m in ['verification/r1_g1_observation_revision_20261117/review_target_manifest.json','verification/r1_g1_criteria_plan_20261117/review_target_manifest.json','verification/r1_requirements_draft_20261117/review_target_manifest.json']:
  for x in read(m)['artifacts']:check('target_seal:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
 for x in read('verification/r1_g1_observation_revision_20261117/input_manifest.json')['inputs']:check('input22:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
 bundle=read('verification/r1_g1_observation_revision_20261117/active_bundle.json');check('resolver17',len(bundle['artifacts'])==17,'Explicit names/paths/SHA')
 for x in bundle['artifacts']:check('resolver:'+x['logical_name'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
 old=read('verification/r4_force_geometry/input_manifest.json')
 for x in old['inputs']:check('old54:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
 for folder in old['protected_trees']:check('protected_tree:'+folder,not run('git','diff',RH if folder=='reviews' else MAIN,'--name-only','--',folder),'R5 append only;other trees unchanged')
 for p,n,key in [('verification/r4_cycle_interfaces/proposal/baseline_bindings.json',44,'rows'),('verification/r4_force_geometry/symbolic_20261116/interfaces.json',52,'rows'),('verification/r4_force_geometry/symbolic_20261116/unknown_index.json',84,None),('verification/r3_force_path/analysis/state_matrix.json',42,None)]:
  d=read(p);check('full_objects:'+p,len(d[key] if key else d)==n and (ROOT/p).read_bytes()==blob(MAIN,p)==blob(TARGET,p),n)
 lfs=run('git','lfs','ls-files','-l').splitlines();check('59_LFS',len(lfs)==59,len(lfs))
 for s in lfs:
  oid,_,p=s.split(' ',2);check('LFS:'+p,sha((ROOT/p).read_bytes())==oid,oid)
 dec=next(yaml.safe_load(x) for x in re.findall(r'```yaml\n(.*?)```',(ROOT/'decisions/R1-DOC-TRACE-RECHECK-ACCEPTANCE.md').read_text(),re.S));check('narrow_decision',dec['gate'] is None and dec['status']=='APPROVED_WITH_LIMITATIONS' and not dec['requirements_approved'] and not dec['source_states_solved'] and dec['G1']=='OPEN','No TZ/G1/engineering approval')
 check('old_author_OPEN_retained',all(x['status']=='OPEN' for x in read('verification/r1_g1_observation_revision_20261117/observation_status.json')['rows']),'Immutable pre-review author snapshot not rewritten')
 replay=[];rel=Path('verification/r1_g1_observation_revision_20261117')
 with tempfile.TemporaryDirectory(prefix='rev-r1-recheck-integration-') as tmp:
  subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/rel/'render_revision.py'),'--output-dir',tmp],check=True,capture_output=True)
  for x in read(str(rel/'reproducibility.json'))['outputs']:
   p=x['path'];same=(Path(tmp)/p).read_bytes()==(ROOT/p).read_bytes();check('reproduce:'+p,same,x['sha256']);replay.append(dict(path=p,result='MATCH',sha256=x['sha256']))
 (P/'renderer_replay.json').write_text(json.dumps(dict(scope='R1 integration reproduction only,not new independent review',outputs=replay),ensure_ascii=False,indent=2)+'\n')
 r=dict(checked_at_utc=now.isoformat(),main=MAIN,target_C=TARGET,R5_H=RH,counts={'PASS':len(checks),'FAIL':0},checks=checks,scope='R1 closure disposition/authority/preservation/reproduction only',independent_R5_counts={'PASS':3804,'FAIL':0},requirements_approved=False,source_states_solved=False,engineering_started=False,PR57_merged=False)
 (P/'integration_checks.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r['counts']))
if __name__=='__main__':main()
