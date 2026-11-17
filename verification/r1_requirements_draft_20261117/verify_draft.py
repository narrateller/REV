"""Author checks for documentary coverage, frozen inputs and reproduction only."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from collections import Counter
import hashlib,json,os,re,subprocess,tempfile,yaml
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
SID='6afb300b-1540-8191-a5c4-be1a684c20e0'
OUTPUTS=['requirements/system_requirements.md','requirements/verification_matrix.md']+[
 'verification/r1_requirements_draft_20261117/'+f for f in ['draft_requirements.json','source_disposition.json','qualitative_applicability.json','open_gaps.json','traceability_schema.json','source_disposition.md','traceability.md','open_gaps.md']]

def main():
 checks=[]
 def read(p):return json.loads((ROOT/p).read_bytes())
 def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
 def sha(b):return hashlib.sha256(b).hexdigest()
 def check(name,ok,evidence):
  checks.append(dict(id=name,status='PASS' if ok else 'FAIL',evidence=evidence))
  if not ok:raise AssertionError(name)
 audit=read('verification/r1_requirements_draft_20261117/input_audit.json');base=audit['input_commit']
 check('actual_session',os.environ.get('CODEX_SESSION_ID')==SID,SID)
 check('actual_main',git('rev-parse','origin/main').decode().strip()==base,base)
 claim=json.loads(git('show',base+':coordination/claims/T-r1-requirements-draft-01.json'))
 old=json.loads(git('show',base+':coordination/claims/T-r1-force-inputs-intake-01.json'))
 check('accepted_claim',claim['owner_session']==SID and claim['status']=='ACCEPTED_MAIN' and old['owner_session']=='NONE' and old['status']=='COMPLETED_DOCUMENTARY_RELEASED','Atomic main ownership transition')
 check('new_lease_live',datetime.fromisoformat(claim['lease_expires_at'])-datetime.fromisoformat(claim['proposed_at_utc'])==timedelta(hours=24) and datetime.now(timezone.utc)<datetime.fromisoformat(claim['lease_expires_at']),claim['lease_expires_at'])
 check('input_audit',audit['verdict']=='WARNING_DOCUMENTARY_ONLY' and audit['counts']=={'PASS':4,'NOT_RUN':3} and not audit['independent_review'] and all(x['status']=='NOT_RUN' for x in audit['items'] if x['section'] in [4,5,6]),'Documentary scope, not physical validation')
 for item in read('verification/r1_requirements_draft_20261117/input_manifest.json')['inputs']:
  raw=git('show',base+':'+item['path']);check('input_pin:'+item['path'],sha(raw)==item['sha256'] and item['commit']==base,item['sha256'])
  if item['path'].startswith('requirements/'):
   archive=HERE/'archive_rev7'/Path(item['path']).name
   check('archive:'+item['path'],archive.read_bytes()==raw,'Exact rev7 preserved; current DRAFT intentionally changed')
  else:check('input_unchanged:'+item['path'],(ROOT/item['path']).read_bytes()==raw,item['sha256'])
 data=read('verification/r1_requirements_draft_20261117/draft_requirements.json');rows=data['requirements']
 ids={f'REQ-REV-{n:02d}' for n in range(1,23)};vals={f'VAL-REV-{n:02d}' for n in range(1,23)}
 check('22_exact_unique',len(rows)==22 and {r['id'] for r in rows}==ids and len({r['id'] for r in rows})==22,'No dropped/duplicated REQ')
 check('22_validation_pairs',{r['validation_id'] for r in rows}==vals and all(r['id'].split('-')[-1]==r['validation_id'].split('-')[-1] for r in rows),'One-to-one REQ/VAL')
 for r in rows:
  check('required_fields:'+r['id'],all(r.get(k) for k in ['proposed_requirement','mode','quantity_or_observation','future_criterion','future_method','expected_evidence','unknown_definition','responsible_functions','source_basis','lineage']),r['future_criterion'])
  check('unapproved_NOT_RUN:'+r['id'],r['status']=='DRAFT_NOT_APPROVED' and r['validation_status']=='NOT_RUN' and not r['criterion_approved'] and not r['active_parameter_refs'] and not r['architecture_selected'] and r['assigned_engineering_owner_session'] is None,'No engineering owner/approval/result manufactured')
 reqmd=(ROOT/'requirements/system_requirements.md').read_text();valmd=(ROOT/'requirements/verification_matrix.md').read_text()
 check('REQ_markdown_ids',set(re.findall(r'^\| (REQ-REV-\d+) \|',reqmd,re.M))==ids,'All REQ rows rendered')
 check('VAL_markdown_ids',set(re.findall(r'^\| (VAL-REV-\d+) / REQ-REV-\d+ \|',valmd,re.M))==vals,'All VAL rows rendered')
 disp=read('verification/r1_requirements_draft_20261117/source_disposition.json')['rows']
 facts=read('verification/r1_force_inputs_intake/reference_facts.json')['source_fields'];fact={x['id']:x for x in facts}
 check('40_exact_unique',len(disp)==40 and {x['field_id'] for x in disp}==set(fact) and len({x['field_id'] for x in disp})==40,'All source declarations dispositioned')
 check('dispositions',dict(Counter(x['disposition'] for x in disp))=={'OPEN_SOURCE_ISSUE':7,'TARGET_PROPOSAL':10,'REFERENCE_CONTEXT':23},'Proposals separated from context and open issues')
 for d in disp:
  f=fact[d['field_id']]
  check('field_trace:'+d['field_id'],d['source']==f['source'] and d['pdf_page']==f['pdf_page'] and d['source_locator']==f['locator'] and d['candidate_revision']==f['revision'] and d['unit']==f['unit'] and set(d['requirement_ids'])<=ids and bool(d['requirement_ids']),d['reason'])
  check('RAW_scope:'+d['field_id'],d['candidate_lifecycle']=='RAW' and not d['parameter_promotion'] and not d['numerical_engineering_use'] and d['REV_realized_value'] is None and bool(d['realized_unknown_reason']),'No new numeric physical input')
  for rid in d['requirement_ids']:check('reverse_edge:'+d['field_id']+':'+rid,d['field_id'] in next(x for x in rows if x['id']==rid)['source_field_ids'],'Bidirectional trace')
 byid={x['field_id']:x for x in disp}
 check('open_source_definitions',all(byid[x]['disposition']=='OPEN_SOURCE_ISSUE' for x in ['BPR_INSTALLED_POWER','BPR_COMPACTION_PRESSURE_LITERAL','BPR_MOISTURE_MIN','BPR_MOISTURE_MAX']),'Power/pressure/moisture unresolved')
 check('comparison_windows',all(x['disposition']=='REFERENCE_CONTEXT' for x in disp if x['field_id'].startswith('SUPR_')),'No averaging/override of BP500')
 check('mass_pressure_distinctions',byid['BPR_REFERENCE_BRIQUETTE_MASS']['disposition']=='REFERENCE_CONTEXT' and byid['BPR_MACHINE_MASS']['disposition']=='REFERENCE_CONTEXT' and byid['BPR_HYDRAULIC_PRESSURE_MAX']['disposition']=='REFERENCE_CONTEXT','No dose/moving-mass/material-pressure transfer')
 candidate=yaml.safe_load((ROOT/'verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml').read_text());params=[p for dom in candidate['domains'].values() for p in dom.values()]
 check('actual_RAW40',len(params)==40 and all(p['lifecycle']=='RAW' and p['verifier'] is None and p['calculation'] is None for p in params),'Frozen candidate values only')
 qual=read('verification/r1_requirements_draft_20261117/qualitative_applicability.json')
 check('16_qualitative',len(qual['rows'])==16 and len({q['id'] for q in qual['rows']})==16 and all(set(q['requirement_ids'])<=ids and not q['source_value_transfer'] for q in qual['rows']),'All qualitative/supplementary refs mapped')
 check('ARS_qualifiers','nonmetallic' in qual['ARS_material_context'] and 'eject' in qual['ARS_cycle_context'] and 'retract/reset' in qual['ARS_cycle_context'],'Material and flowchart qualifications retained')
 gaps=read('verification/r1_requirements_draft_20261117/open_gaps.json')['rows'];gids={g['id'] for g in gaps}
 check('prior_gaps_preserved',{g['id'] for g in read('verification/r1_force_inputs_intake/additional_gaps.json')}<=gids,'All eight reference gaps carried forward')
 check('blockers_open',{'R5-TZ-B01','R5-TZ-B02','R5-TZ-B03','SOURCE-POWER','SOURCE-PRESSURE-UNIT','SOURCE-MOISTURE-BASIS'}<=gids and all(g['status']=='OPEN' and g['value'] is None and g['assigned_owner_session'] is None and g['due_at_utc'] is None for g in gaps),'No false closure/owner/date/value')
 schema=read('verification/r1_requirements_draft_20261117/traceability_schema.json')
 check('many_to_many',schema['cardinality'].startswith('many-to-many') and schema['actual_records'] is None and schema['actual_records_status']=='NOT_RUN' and {'Batch_ID','Stage_ID','Sample_ID','Dose_ID','Cycle_ID','Briquette_ID','Residual_ID','Loss_ID'}==set(schema['nodes']),'Schema is not measured records')
 for p in ['params/registry.yaml','reviews/cross_check_log.md','verification/r4_cycle_interfaces/proposal/baseline_bindings.json','verification/r3_force_path/analysis/state_matrix.json','verification/r4_force_geometry/symbolic_20261116/unknown_index.json','verification/r4_force_geometry/symbolic_20261116/interfaces.json']:
  check('baseline_unchanged:'+p,(ROOT/p).read_bytes()==git('show',base+':'+p),sha((ROOT/p).read_bytes()))
 for item in read('verification/r5_reference_intake_review/validation.json')['package_files']:
  check('R5_seal:'+item['path'],sha((ROOT/item['path']).read_bytes())==item['sha256'],item['sha256'])
 for p in git('ls-tree','-r','--name-only','f2cbd96bb78c915dca74cb4eb29daffbb52ee172','verification/r1_force_inputs_intake').decode().splitlines():
  check('source_packet:'+p,git('rev-parse',base+':'+p)==git('rev-parse','f2cbd96bb78c915dca74cb4eb29daffbb52ee172:'+p),p)
 check('84_52_42_44',len(read('verification/r4_force_geometry/symbolic_20261116/unknown_index.json'))==84 and len(read('verification/r4_force_geometry/symbolic_20261116/interfaces.json')['rows'])==52 and len(read('verification/r3_force_path/analysis/state_matrix.json'))==42 and len(read('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows'])==44,'Whole objects unchanged; states not solved')
 check('no_engineering_results',not data['numerical_machine_models_run'] and not data['active_registry_modified'] and not data['source_states_solved'] and data['G1']=='OPEN' and data['physical_READY']=='NO_GO' and data['requirements_output_review']=='NOT_RUN','DRAFT only')
 with tempfile.TemporaryDirectory(prefix='rev-req-reproduce-') as tmp:
  r=subprocess.run([str(ROOT/'.venv/bin/python'),str(HERE/'build_draft.py'),'--output-dir',tmp],text=True,capture_output=True,check=True)
  replay=[]
  for p in OUTPUTS:
   expected=(ROOT/p).read_bytes();actual=(Path(tmp)/p).read_bytes();check('reproduce:'+p,actual==expected,sha(expected));replay.append(dict(path=p,sha256=sha(expected),result='MATCH'))
 (HERE/'reproducibility.json').write_text(json.dumps(dict(command='.venv/bin/python verification/r1_requirements_draft_20261117/build_draft.py --output-dir TEMP',returncode=r.returncode,outputs=replay,scope='Document rendering only, no engineering computation'),ensure_ascii=False,indent=2)+'\n')
 changed=git('diff',base,'--name-only').decode().splitlines()
 allowed={'requirements/system_requirements.md','requirements/verification_matrix.md','coordination/tasks/T-r1-requirements-draft-01/task.json','ISSUES_AND_TASKS.md','STATE.md','NEXT_MODEL.md','handoffs/T-r1-requirements-draft-01/'+SID+'.md'}
 check('existing_change_scope',set(changed)<=allowed,changed)
 unknown=git('ls-files','--others','--exclude-standard').decode().splitlines()
 check('new_file_scope',all(p.startswith('verification/r1_requirements_draft_20261117/') for p in unknown),unknown)
 result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),input_commit=base,counts={'PASS':len(checks),'FAIL':0},checks=checks,scope='Author documentary consistency and reproducibility only; not independent review or engineering validation',requirements_output_review='NOT_RUN',source_states_solved=False,engineering_started=False)
 (HERE/'author_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result['counts']))
if __name__=='__main__':main()
