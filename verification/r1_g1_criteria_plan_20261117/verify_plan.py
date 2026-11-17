"""Author consistency for the proposed supplement; no criterion/test is executed."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,re,subprocess,tempfile,yaml
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;REL='verification/r1_g1_criteria_plan_20261117/'
SID='6afb300b-1540-8191-a5c4-be1a684c20e0';MAIN='043271b57aa3d49b6d9b45da03496ea11dad41b1';OLD='c50a5eaf8f99b6aacfea7d2d63ca1c049fbdffff'
OUTPUTS=[REL+f for f in ['criterion_cards.json','metrology_plan.json','evaluation_rules.json','evidence_schema.json','hazard_to_evidence.json','normative_applicability_plan.json','source_actions.json','criterion_cards.md','metrology_plan.md','safety_plan.md','normative_plan.md','source_actions.md','execution_board.md']]

def main():
 checks=[]
 def read(p):return json.loads((ROOT/p).read_bytes())
 def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
 def sha(b):return hashlib.sha256(b).hexdigest()
 def check(n,ok,e):
  checks.append(dict(id=n,status='PASS' if ok else 'FAIL',evidence=e))
  if not ok:raise AssertionError(n)
 check('actual_R1',os.environ.get('CODEX_SESSION_ID')==SID,SID)
 check('main',git('rev-parse','origin/main').decode().strip()==MAIN,MAIN)
 claim=read('coordination/claims/T-r1-requirements-draft-01.json')
 check('accepted_live_claim',claim['owner_session']==SID and claim['status']=='ACCEPTED_MAIN' and claim['lease_expires_at']=='2026-11-18T01:58:30.990734+00:00' and datetime.now(timezone.utc)<datetime.fromisoformat(claim['lease_expires_at']),claim['lease_expires_at'])
 check('claim_byte_unchanged',(ROOT/'coordination/claims/T-r1-requirements-draft-01.json').read_bytes()==git('show',MAIN+':coordination/claims/T-r1-requirements-draft-01.json'),'No new claim or renewal')
 audit=read(REL+'input_audit.json');check('input_audit',audit['verdict']=='WARNING_DOCUMENTARY_ONLY' and audit['counts']=={'PASS':4,'NOT_RUN':3} and not audit['independent_review'] and all(i['status']=='NOT_RUN' for i in audit['items'] if i['section'] in [4,5,6]),'Documentation only')
 for i in read(REL+'input_manifest.json')['inputs']:check('input:'+i['path'],sha((ROOT/i['path']).read_bytes())==i['materialized_sha256'],i['materialized_sha256'])
 for item in read('verification/r1_requirements_draft_20261117/review_target_manifest.json')['artifacts']:check('rev8_frozen:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 check('review_journal_preserved',(ROOT/'reviews/cross_check_log.md').read_bytes()==git('show',MAIN+':reviews/cross_check_log.md'),'Old WARNING/REJECT/STALE/counters unchanged; no self-review appended')
 cards=read(REL+'criterion_cards.json');rows=cards['rows'];ids={f'REQ-REV-{n:02d}' for n in range(1,23)}
 check('22_cards',len(rows)==22 and {x['requirement_id'] for x in rows}==ids and len({x['card_id'] for x in rows})==22,'Exact22 coverage')
 source={x['id']:x for x in read('verification/r1_requirements_draft_20261117/draft_requirements.json')['requirements']}
 disp={x['field_id']:x for x in read('verification/r1_requirements_draft_20261117/source_disposition.json')['rows']}
 for c in rows:
  check('card_fields:'+c['requirement_id'],all(c[x] for x in ['observation','proposed_future_pass_predicate','mandatory_evidence_fields','measurement_channel_ids','G1_definition_needed','later_result_stage']),c['proposed_future_pass_predicate'])
  check('card_ownership:'+c['requirement_id'],c['documentary_owner_session']==SID and c['documentary_owner_role']=='R1' and c['engineering_owner_session'] is None and c['engineering_due_utc'] is None,'Actual R1 documentary ownership; no other session assigned')
  check('card_no_promotion:'+c['requirement_id'],c['threshold_value'] is None and c['tolerance'] is None and c['uncertainty_acceptance_limit'] is None and c['range'] is None and c['threshold_unknown_reason'] and not c['active_parameter_refs'] and c['physical_validation_status']=='NOT_RUN' and not c['G1_closed'],'No invented limit/measurement/result')
  check('card_frozen_trace:'+c['requirement_id'],[x['id'] for x in c['source_field_refs']]==source[c['requirement_id']]['source_field_ids'] and c['validation_id']==source[c['requirement_id']]['validation_id'],'Frozen rev8 identifiers retained')
  for ref in c['source_field_refs']:check('qualified_source:'+c['requirement_id']+':'+ref['id'],ref['disposition']==disp[ref['id']]['disposition'] and not ref['usable_as_approved_criterion'] and ref['revision']==1,'Context/open-source/proposal does not become approved criterion')
 check('objective_criteria_distinguished',all(c['criterion_kind']=='OBJECTIVE_COMPLETENESS' for c in rows if c['requirement_id'] in ['REQ-REV-18','REQ-REV-19','REQ-REV-20','REQ-REV-21']),'Documentary completeness does not need invented numeric limit')
 met=read(REL+'metrology_plan.json');check('22_metrology_rows',len(met['rows'])==22 and {m['requirement_id'] for m in met['rows']}==ids,'All VAL mapped')
 channels={x['channel_id']:x for x in met['channels']};check('11_channel_classes',len(channels)==11,'Proposed method classes, not chosen hardware')
 for m in met['rows']:
  check('method_plan:'+m['requirement_id'],set(m['channel_ids'])<=set(channels) and bool(m['channel_ids']) and m['criterion_card_id']==next(c['card_id'] for c in rows if c['requirement_id']==m['requirement_id']) and m['execution_status']=='NOT_RUN' and not m['execution_permission'] and m['actual_records']==[] and all(m[x] is None for x in ['method_revision','instrument_model','range','resolution','uncertainty_limit','sample_count']),'No default method/count/precision or execution')
 for channel in channels.values():
  check('metrology_unknowns:'+channel['channel_id'],channel['verification_status']=='NOT_RUN' and not channel['uncertainty_budget_evaluated'] and channel['calibration_evidence'] is None and all(t['value'] is None and t['unknown_reason'] for t in channel['uncertainty_budget_terms']),'Calibration/uncertainty not claimed')
 rules=read(REL+'evaluation_rules.json');check('decision_policy',rules['current_execution']=='NOT_RUN' and any('never substitute zero or PASS' in x['future_status'] for x in rules['rules']) and any(x['future_status'].startswith('FAIL') for x in rules['rules']) and 'known violation' in rules['unsolicited_observations_policy'],'Missing criteria cannot yield PASS; known violations retained')
 schema=read(REL+'evidence_schema.json');check('no_fake_data',schema['actual_records']==[] and schema['template']['measured_value'] is None and schema['template']['uncertainty'] is None and schema['template']['quality_flag']=='NOT_MEASURED' and schema['all_VAL_TEST_status']=='NOT_RUN' and schema['cardinality'].startswith('many-to-many'),'Template is not a result')
 hazards=read(REL+'hazard_to_evidence.json')['rows'];check('20_hazards',len(hazards)==20 and {h['hazard_id'] for h in hazards}=={f'H{i:02d}' for i in range(1,21)},'H01-H20 preserved')
 original={}
 for line in (ROOT/'verification/r3_press_safety/preliminary_hazards.md').read_text().splitlines():
  if re.match(r'^\| H\d\d \|',line):
   cell=[c.strip() for c in line.strip('|').split('|')];original[cell[0]]=cell[1:]
 for h in hazards:check('hazard:'+h['hazard_id'],h['source_cells']==original[h['hazard_id']] and set(h['requirement_ids'])<=ids and h['risk_level'] is None and h['safety_performance_level'] is None and not h['safe_state_verified'] and not h['completeness_proven'] and h['verification_status']=='NOT_RUN' and h['engineering_owner_session'] is None,h['proposed_safety_requirement'])
 norms=read(REL+'normative_applicability_plan.json')['rows'];check('six_candidates',len(norms)==6 and {n['candidate_id'] for n in norms}=={f'N{i:02d}' for i in range(1,7)},'Historical candidate identities, no new law selection')
 for n in norms:check('normative:'+n['candidate_id'],n['REV_applicability'] is None and n['current_consolidated_edition'] is None and n['jurisdiction'] is None and not n['new_legal_conclusion'] and not n['new_full_text_review'] and n['competent_reviewer_session'] is None and n['status']=='CANDIDATE_UNRESOLVED',n['applicability_unknown_reason'])
 acts=read(REL+'source_actions.json')['rows'];check('three_source_actions',{x['issue_id'] for x in acts}=={'SOURCE-POWER','SOURCE-PRESSURE-UNIT','SOURCE-MOISTURE-BASIS'} and len(acts)==3,'Exact questions and closure evidence')
 for x in acts:check('source_action:'+x['issue_id'],x['status']=='OPEN' and x['documentary_owner_session']==SID and x['exact_question'] and x['required_closure_evidence'] and x['REV_value'] is None and not x['external_contact_sent'] and not x['issue_resolved'] and not x['numeric_engineering_use'],'No contact, assumption, repaired unit or budget')
 search=read(REL+'source_text_search.json');check('source_search_scope',len(search['sources'])==4 and not search['source_issues_resolved'] and not search['engineering_values_adopted'] and not search['new_numerical_or_physical_calculations'],'Bounded text search, not full source recertification')
 for x in search['sources']:check('source_bytes:'+x['source'],sha((ROOT/x['path']).read_bytes())==x['sha256'] and x['returncode']==0 and 'absence' in x['scope'],x['sha256'])
 check('ARS_no_text_disclosed',next(x for x in search['sources'] if x['source']=='ARS')['pdf_pages_with_extracted_text']==0,'Search absence cannot prove absence in scan')
 raw=yaml.safe_load((ROOT/'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml').read_text());params=[p for d in raw['domains'].values() for p in d.values()]
 check('40_RAW',len(params)==40 and all(p['lifecycle']=='RAW' and p['verifier'] is None and p['calculation'] is None for p in params),'No maturity promotion')
 old=read('verification/r4_force_geometry/input_manifest.json')
 for i in old['inputs']:check('old_pin:'+i['path'],sha((ROOT/i['path']).read_bytes())==i['sha256'],i['sha256'])
 for folder in old['protected_trees']:check('protected_tree:'+folder,git('diff',OLD,'--name-only','--',folder).strip()==b'' and git('ls-files','--others','--exclude-standard','--',folder).strip()==b'',folder)
 check('84_52_42_44',len(read('verification/r4_force_geometry/symbolic_20261116/unknown_index.json'))==84 and len(read('verification/r4_force_geometry/symbolic_20261116/interfaces.json')['rows'])==52 and len(read('verification/r3_force_path/analysis/state_matrix.json'))==42 and len(read('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows'])==44,'Whole original data retained, no new result')
 for file in ['criterion_cards.json','metrology_plan.json','evaluation_rules.json','evidence_schema.json','hazard_to_evidence.json','normative_applicability_plan.json','source_actions.json']:
  d=read(REL+file);check('scope:'+file,d['new_review']=='NOT_RUN' and not d['requirements_approved'] and not d['source_states_solved'] and not d['engineering_calculations_run'] and not d['physical_tests_run'] and d['G1']=='OPEN','R5 rev8 review does not cover new supplement')
 replay=[]
 with tempfile.TemporaryDirectory(prefix='rev-g1-render-') as tmp:
  p=subprocess.run([str(ROOT/'.venv/bin/python'),str(HERE/'build_plan.py'),'--output-dir',tmp],capture_output=True,text=True,check=True)
  for file in OUTPUTS:
   expected=(ROOT/file).read_bytes();actual=(Path(tmp)/file).read_bytes();check('reproduce:'+file,actual==expected,sha(expected));replay.append(dict(path=file,sha256=sha(expected),result='MATCH'))
  probe=Path(tmp)/'source-search.json';subprocess.run([str(ROOT/'.venv/bin/python'),str(HERE/'search_sources.py'),'--output',str(probe)],capture_output=True,text=True,check=True)
  again=json.loads(probe.read_text());check('source_search_reproducible',{k:v for k,v in again.items() if k!='checked_at_utc'}=={k:v for k,v in search.items() if k!='checked_at_utc'},'Same source text/search data excluding observation UTC')
 (HERE/'reproducibility.json').write_text(json.dumps(dict(renderer_returncode=p.returncode,outputs=replay,source_search='MATCH except checked_at_utc; no new source interpretation',scope='Document reproduction only'),ensure_ascii=False,indent=2)+'\n')
 allowed={'STATE.md','NEXT_MODEL.md','ISSUES_AND_TASKS.md','coordination/tasks/T-r1-requirements-draft-01/task.json','handoffs/T-r1-requirements-draft-01/'+SID+'.md'}
 changed=git('diff',OLD,'--name-only').decode().splitlines();check('existing_change_scope',all(f in allowed or f.startswith(REL) for f in changed),changed)
 untracked=git('ls-files','--others','--exclude-standard').decode().splitlines();check('new_file_scope',all(f.startswith(REL) for f in untracked),untracked)
 result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),base_main=MAIN,working_base=OLD,counts={'PASS':len(checks),'FAIL':0},checks=checks,scope='Author documentary consistency/coverage/frozen data/reproduction only',new_independent_review='NOT_RUN',source_states_solved=False,engineering_started=False)
 (HERE/'author_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result['counts']))
if __name__=='__main__':main()
