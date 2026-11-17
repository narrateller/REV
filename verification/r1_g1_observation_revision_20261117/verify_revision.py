"""Author checks of documentary amendment boundaries, not independent closure."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,tempfile,os,copy
ROOT=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent;REL=P.relative_to(ROOT);OLD=Path('verification/r1_g1_criteria_plan_20261117');MAIN='e8f1d6bf41c0cfd2dcc4d3a673e642ecfb53588a';SID='6afb300b-1540-8191-a5c4-be1a684c20e0'
def read(p):return json.loads((ROOT/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def run(*a):return subprocess.check_output(a,cwd=ROOT,text=True).strip()
def main():
 checks=[]
 def check(i,ok,e):
  checks.append(dict(id=i,status='PASS' if ok else 'FAIL',evidence=e))
  if not ok:raise RuntimeError(i+': '+str(e))
 check('actual_R1',os.getenv('CODEX_SESSION_ID')==SID,SID)
 check('main',run('gh','api','repos/narrateller/REV/git/ref/heads/main','--jq','.object.sha')==MAIN,MAIN)
 claim=read('coordination/claims/T-r1-requirements-draft-01.json');check('live_original_claim',claim['owner_session']==SID and claim['status']=='ACCEPTED_MAIN' and datetime.now(timezone.utc)<datetime.fromisoformat(claim['lease_expires_at']) and claim['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00',claim['lease_expires_at'])
 for row in read(REL/'input_manifest.json')['inputs']:check('input:'+row['path'],sha((ROOT/row['path']).read_bytes())==row['sha256'],row['sha256'])
 for m in [OLD/'review_target_manifest.json',Path('verification/r1_requirements_draft_20261117/review_target_manifest.json')]:
  for x in read(m)['artifacts']:check('frozen:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
 oldmet=read(OLD/'metrology_plan.json');met=read(REL/'metrology_plan.json');cards=read(REL/'criterion_cards.json');oldcards=read(OLD/'criterion_cards.json');haz=read(REL/'hazard_to_evidence.json');oldhaz=read(OLD/'hazard_to_evidence.json');force=read(REL/'force_evidence_plan.json');schema=read(REL/'evidence_schema.json')
 check('22_22_20_12',len(cards['rows'])==22 and len(met['rows'])==22 and len(haz['rows'])==20 and len(met['channels'])==12,'No source state/criterion removed')
 pure={'REQ-REV-18','REQ-REV-19','REQ-REV-20','REQ-REV-21'}
 for before,after in zip(oldcards['rows'],cards['rows']):
  if before['requirement_id'] not in pure|{'REQ-REV-09'}:check('unchanged_card:'+before['card_id'],before==after,'Exact object equality')
  check('card_NO_values:'+after['card_id'],after['threshold_value'] is None and after['tolerance'] is None and after['uncertainty_acceptance_limit'] is None and after['range'] is None and after['physical_validation_status']=='NOT_RUN','No numeric criteria or results')
 for before,after in zip(oldmet['rows'],met['rows']):
  if 'DOCUMENT' not in before['channel_ids']:check('unchanged_metrology:'+before['plan_id'],before==after,'Exact object equality')
  elif before['requirement_id'] in pure:
   check('pure_document:'+after['plan_id'],after['field_applicability']['method_revision']['status']=='APPLICABLE_UNKNOWN' and after['field_applicability']['sample_count']['status']=='NOT_APPLICABLE' and after['required_document_scope'] is None and 'instrument_and_calibration_refs' not in after['required_context'],'No blanket N_A of missing method/scope')
  else:check('mixed_retains:'+after['plan_id'],after['required_context']==before['required_context'] and 'instrument_and_calibration_refs' in after['required_context'] and 'field_applicability' not in after,'Numeric unknowns not waived by DOCUMENT')
  check('met_not_run:'+after['plan_id'],after['actual_records']==[] and not after['execution_permission'] and after['execution_status']=='NOT_RUN' and after['engineering_owner_session'] is None,'No execution or new engineering owner')
 for channel in oldmet['channels']:
  current=next(x for x in met['channels'] if x['channel_id']==channel['channel_id'])
  if channel['channel_id']!='DOCUMENT':check('unchanged_channel:'+channel['channel_id'],current==channel,'Exact object equality')
 doc=next(x for x in met['channels'] if x['channel_id']=='DOCUMENT');check('DOC_assurance',doc['uncertainty_budget_terms']==[] and len(doc['procedural_assurance_criteria'])==4 and doc['procedural_assurance_status']=='NOT_RUN' and doc['field_applicability']['method_revision']['status']=='APPLICABLE_UNKNOWN','Qualitative assurance separated,not numerically calibrated')
 for row in doc['procedural_assurance_criteria']:check('assurance:'+row['dimension'],row['status']=='NOT_RUN' and not row['actual_evidence'] and row['required_evidence_fields'] and row['future_rule'],row['future_rule'])
 for before,after in zip(oldhaz['rows'],haz['rows']):
  if before['hazard_id']!='H01':check('unchanged_hazard:'+before['hazard_id'],before==after,'Exact object equality')
  else:check('H01_trace',after['source_cells']==before['source_cells'] and after['requirement_ids']==before['requirement_ids']+['REQ-REV-09'] and after['validation_ids']==before['validation_ids']+['VAL-REV-09'] and 'MET-VAL-REV-09' in after['metrology_plan_ids'] and all(x in after['acceptance_evidence'] for x in before['acceptance_evidence']),'Old source/refs preserved,explicit new trace')
  check('hazard_no_proof:'+after['hazard_id'],not after['safe_state_verified'] and not after['completeness_proven'] and after['risk_level'] is None and after['safety_performance_level'] is None,'No risk/PL/SIL/actual safe-state conclusion')
 check('MET09_FORCE','FORCE_REACTION' in next(x for x in met['rows'] if x['requirement_id']=='REQ-REV-09')['channel_ids'] and 'FORCE_REACTION' in next(x for x in cards['rows'] if x['requirement_id']=='REQ-REV-09')['measurement_channel_ids'],'Consistent criteria/program trace')
 check('force_future_only',force['selected_method_route'] is None and force['actual_records']==[] and force['actual_load_cases']==[] and not force['execution_permission'] and force['engineering_owner_session'] is None,'No cases/numbers/model/instrument executed or assigned')
 for row in force['input_definitions']:check('force_input:'+row['id'],row['value'] is None and row['source_record'] is None and row['unknown_reason'],'Actual input UNKNOWN')
 for row in force['route_specs']:check('force_route:'+row['route_id'],not row['execution_permission'] and row['execution_status']=='NOT_RUN' and all(x['value'] is None and x['unknown_reason'] for x in row['required'].values()),'Unselected future route only')
 check('schema_profiles',set(schema['profiles'])=={'DOCUMENTARY_AUDIT','NUMERIC_MEASUREMENT','MIXED','MODEL_PREDICTION'} and schema['actual_records']==[] and schema['all_VAL_TEST_status']=='NOT_RUN' and 'calibration_ref' in schema['profiles']['NUMERIC_MEASUREMENT']['required_fields'],'Pure audit profile cannot erase measured subclaims')
 for name in ['criterion_cards.json','metrology_plan.json','hazard_to_evidence.json','evidence_schema.json','force_evidence_plan.json','active_bundle.json']:
  d=read(REL/name);check('scope:'+name,d['new_review']=='NOT_RUN' and not d['requirements_approved'] and not d['engineering_calculations_run'] and not d['physical_tests_run'] and not d['source_states_solved'] and d['G1']=='OPEN','Old exact-C review not reused for new revision')
 bundle=read(REL/'active_bundle.json')
 for x in bundle['artifacts']:check('resolved_artifact:'+x['logical_name'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
 old=read('verification/r4_force_geometry/input_manifest.json')
 for x in old['inputs']:check('old54:'+x['path'],sha((ROOT/x['path']).read_bytes())==x['sha256'],x['sha256'])
 for p in old['protected_trees']:check('tree:'+p,not run('git','diff',MAIN,'--name-only','--',p),'No protected tree changes')
 replay=[]
 with tempfile.TemporaryDirectory(prefix='rev-observation-replay-') as tmp:
  subprocess.run([str(ROOT/'.venv/bin/python'),str(P/'render_revision.py'),'--output-dir',tmp],check=True,capture_output=True)
  for n in ['criterion_cards.json','metrology_plan.json','hazard_to_evidence.json','evidence_schema.json','force_evidence_plan.json','criterion_cards.md','metrology_plan.md','safety_plan.md','document_assurance.md','evidence_schema.md','force_evidence_plan.md','execution_board.md','active_bundle.json']:
   same=(Path(tmp)/REL/n).read_bytes()==(P/n).read_bytes();check('reproduce:'+n,same,sha((P/n).read_bytes()));replay.append(dict(path=str(REL/n),result='MATCH',sha256=sha((P/n).read_bytes())))
 (P/'reproducibility.json').write_text(json.dumps(dict(outputs=replay,scope='Documentary reproduction only'),ensure_ascii=False,indent=2)+'\n')
 result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),counts={'PASS':len(checks),'FAIL':0},checks=checks,scope='Author documentary correction/unchanged-scope/reproduction checks; not independent observation closure',new_independent_review='NOT_RUN',source_states_solved=False,engineering_started=False)
 (P/'author_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result['counts']))
if __name__=='__main__':main()
