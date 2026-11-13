"""Independent OUTPUT audit: symbolic consistency and isolated document mutations.
Not a controller; no permission for machinery and no CAD collision verdict.
"""
import copy,csv,hashlib,itertools,json,subprocess,sys,tempfile,shutil,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'verification/r4_cycle_interfaces/proposal'
C=json.loads((ROOT/'verification/r4_cycle_contract/contract.json').read_text());F={a['id']:a for a in C['transitions']}
D=json.loads((P/'permissions.json').read_text());A={a['id']:a for a in D['actions']}
checks=[];findings=[]
def check(id,ok,detail=None):checks.append(dict(id=id,passed=bool(ok),detail=detail))
def issue(id,detail):findings.append(dict(id=id,detail=detail))
# Exact authoritative bindings, including uses in every action and resource phase ref.
B=json.loads((P/'baseline_bindings.json').read_text())['rows'];orig=json.loads((ROOT/'verification/r4_calculated_layout/source_bindings.json').read_text())['rows']
check('44-exact-source-rows',len(B)==44 and B==orig)
lookup={(r['scenario'],r['proposed_cad_field']):r for r in B}
for r in B:
 src=json.loads((ROOT/r['source']).read_text());hit=[x for x in src['inputs']+src['outputs'] if x['id']==r['parameter_id'] and x['revision']==r['revision']]
 check('binding:'+r['scenario']+':'+r['proposed_cad_field'],len(hit)==1 and all(hit[0][k]==r[k] for k in ['value','unit','engineering_sha256']))
for a in A.values():
 scenario='BASE_'+a['variant']
 for ref in a['source_bindings']:
  r=lookup[(scenario,ref['proposed_cad_field'])];check('action-ref:'+a['id']+':'+ref['proposed_cad_field'],all(ref[k]==r[k] for k in ['parameter_id','revision','source']))
 for ref in a['resources']['source_main_axis_phase_refs']:
  r=lookup[(scenario,ref['proposed_cad_field'])];check('phase-ref:'+a['id']+':'+ref['proposed_cad_field'],all(ref[k]==r[k] for k in ['parameter_id','revision','source','value','unit']))
 if a['id'] in F:
  f=F[a['id']];check('inherited:'+a['id'],a['entry_guards']==f['entry_guards'] and a['completion_guards']==f['completion_guards'] and a['material_from']==f['from_states'] and a['material_to']==f['to_state'] and a['mode']==f['allowed_modes'])
 if 'parent_action_choices' in a:
  for mode in a['mode']:
   usable=[parent for parent in a['parent_action_choices'] if mode in A[parent]['mode']]
   check('mode-parent:'+a['id']+':'+mode,bool(usable),dict(declared_mode=mode,parents=a['parent_action_choices'],eligible_parents=usable))
   if not usable:issue('R5-CI-B01',dict(action=a['id'],mode=mode,problem='Declared mode has no legal bound parent'))
# Proof of incompatible current-pose requirements under completion-after-return interpretation.
for v in ['A','B']:
 ret=A[v+'-MECH-DOSER-RETURN']
 for parent in ret['parent_action_choices']:
  required=set(ret['extra_completion_guards'])|set(A[parent]['extra_completion_guards'])
  valid=[]
  for pose in ['D0','D1']:
   values={'D_HOME_CURRENT':pose=='D0','D_DELIVERY_CURRENT':pose=='D1'}
   if all(values.get(g,True) for g in required):valid.append(pose)
  check('load-return-current-completion:'+parent,bool(valid),dict(required=sorted(required),satisfying_doser_poses=valid,interpretation='Parent completion applied at end of included DOSER-RETURN; early parent commit + new poststep needs explicit alternative contract'))
  if not valid:issue('R5-CI-B01',dict(parent=parent,problem='No final pose satisfies current D1 parent completion and current D0 return completion; commit boundary/history witness unspecified'))
# Recovery dependency: exact parent can enter without DEPENDENCY_VALID, children cannot.
# Reproduce the dependency using the unchanged checked helper, not a fabricated fault bit.
loader=importlib.util.spec_from_file_location('frozen_permissions',ROOT/'verification/r4_cycle_contract/permission_examples.py')
L=importlib.util.module_from_spec(loader);loader.loader.exec_module(L)
x=dict(scenario_id='R5-CI-RECOVERY',variant='B',mode='B_REPEAT',state=F['B-NEXT']['from_states'][0],subject_id='batch-object',batch_id='batch',cycle_epoch='epoch',basis_id='basis',basis_revision='r1',operation_id='failed-next',revisions={d:0 for d in C['evidence_policy']['domains']},inventory_refs=['batch-object'],pending_observations=[])
x=L.initialize_history(x,'R5-CI-HISTORY',dict(value='TRUE',evidence_id='ASSUMED-initial',source='independent hypothetical audited history'))
def evidence(ctx,action,guard):
 return dict({k:ctx[k] for k in C['evidence_policy']['scope_fields']+['operation_id']},value='TRUE',action=action,guard=guard,phase='COMPLETION' if guard in F[action]['completion_guards'] else 'ENTRY',evidence_id='R5-'+action+'-'+guard,method='ASSUMED_FIXTURE',source='independent documentary evidence',valid_for_operation_interval=True,revisions=copy.deepcopy(ctx['revisions']))
x['evidence']={g:evidence(x,'B-NEXT',g) for g in F['B-NEXT']['required_guards']};x['evidence']['B_RESET_CONFIRMED']['value']='FALSE'
x,denied=L.decide(C,'B-NEXT',x);assert denied['permission_outcome']=='BLOCKED'
x['operation_id']='unique-restore';x['state']=F['B-RESET']['from_states'][0];x['evidence']={g:evidence(x,'B-RESET',g) for g in F['B-RESET']['required_guards']}
parent_native=L.evaluate(C,'B-RESET',x,'ENTRY')
dependency_truth,dependency_reason=L.evidence_value(C,'B-RESET','DEPENDENCY_VALID',x,None,'ENTRY')
recovery_chain=dict(failed_next=denied,parent_entry=parent_native,dependency_truth=dependency_truth,dependency_reason=dependency_reason,latched_faults=x['faults'])
assert parent_native['permission_outcome']=='ALLOWED_ASSUMED' and dependency_truth=='FALSE'

parent=A['B-RESET'];pguards=set(parent['entry_guards']+parent['extra_entry_guards'])
for child in ['B-MECH-STOP-CLOSE','B-MECH-RELOCK']:
 own=set(A[child]['entry_guards']+A[child]['extra_entry_guards']+A[child]['current_parent_guards']['B-RESET'])
 vals={g:'TRUE' for g in pguards|own};vals['DEPENDENCY_VALID']='FALSE'
 parent_allowed=all(vals[g]=='TRUE' for g in pguards);child_allowed=all(vals[g]=='TRUE' for g in own)
 check('restore-parent-vs-child:'+child,not parent_allowed or child_allowed,dict(parent_start_allowed_assumed=parent_allowed,child_start_allowed_assumed=child_allowed,dependency_value='FALSE',scope='Candidate mechanical predicates remain symbolic; frozen helper reproduces latched dependency and permitted parent ENTRY',frozen_helper_chain=recovery_chain))
 if parent_allowed and not child_allowed:issue('R5-CI-B02',dict(child=child,problem='Generic DEPENDENCY_VALID makes reset substep stricter than reset recovery parent; no targeted recovery binding provided'))
def semantic_errors(document):
 errors=set();acts={a['id']:a for a in document['actions']}
 known={x['id'] for x in json.loads((P/'poses.json').read_text())['poses']}|{'HOLD_CURRENT'}
 import re
 for a in acts.values():
  for body,path in a['poses'].items():
   for token in re.split(r'→|/',path):
    if token not in known:errors.add('unknown-pose:'+a['id']+':'+token)
  if a['id'].endswith('-MECH-WORK') and a['poses']['punch']!='P1→P2':errors.add('work-origin:'+a['id'])
  if a['id'].endswith(('-MECH-WORK','-MECH-APPROACH')) and 'G_ISOLATED_CURRENT' not in a['extra_entry_guards']:errors.add('missing-isolation:'+a['id'])
  for r in a['source_bindings']:
   b=lookup[('BASE_'+a['variant'],r['proposed_cad_field'])]
   if any(r[k]!=b[k] for k in ['source','parameter_id','revision']):errors.add('wrong-action-binding:'+a['id']+':'+r['proposed_cad_field'])
  for par in a.get('parent_action_choices',[]):
   if par not in acts or acts[par]['variant']!=a['variant'] or not set(a['mode'])&set(acts[par]['mode']):errors.add('wrong-parent:'+a['id']+':'+par)
 return errors
baseline_semantic_errors=semantic_errors(D)
check("original-pose-path-isolation-and-scenario-consistency",not baseline_semantic_errors,sorted(baseline_semantic_errors))

# Explicit aliases requested by review: names differ; audit semantics rather than demand spelling.
for v in ['A','B']:
 isolate=A[v+'-MECH-FEED-ISOLATE'];guards=set(isolate['entry_guards']+isolate['extra_entry_guards'])
 check('feeder-safe:'+v,'D_HOME_CURRENT' in guards and 'G_PATH_CLEAR' in guards and 'P_FEED_CLEAR' in guards)
 check('isolated-completion:'+v,'G_ISOLATED_CURRENT' in isolate['extra_completion_guards'])
 direct_fill='DOSE_DELIVERED' in guards or 'FILL_COMPLETE' in guards
 check('addressed-fill-complete-before-isolation:'+v,direct_fill,dict(explicit_fill_guard_present=direct_fill,predecessor_prose=isolate['predecessors'],warning='Prose requires completed transfer; no explicit same-batch delivery receipt in structured entry, G_PATH_CLEAR alone is not completion of dose'))
 if not direct_fill:issue('R5-CI-B01',dict(action=isolate['id'],problem='Add explicit addressed FILL_COMPLETE/history link, or formal derivation from completed parent with same batch/epoch'))
# Tri-valued oracle: invalid conditions cannot be hidden by other UNKNOWN.
def conjunction(vals):return 'BLOCKED' if 'FALSE' in vals else 'INDETERMINATE' if 'UNKNOWN' in vals else 'ALLOWED_ASSUMED'
truth=[]
for vals in itertools.product(['TRUE','FALSE','UNKNOWN'],repeat=3):
 truth.append(dict(FILL_COMPLETE=vals[0],FEEDER_SAFE=vals[1],ISOLATED=vals[2],expected=conjunction(vals)))
# Independent semantic rejection vs author's hash/export checks, all mutations exported coherently.
mutants=[]
with tempfile.TemporaryDirectory(prefix='r5-ci-output-') as tmp:
 tmp=Path(tmp)
 for name in ['unknown_pose','work_starts_at_P0','drop_isolation_guard','cross_scenario_work_binding','wrong_parent_mode','reduced_rod','reduced_work_force','shortened_work_stroke']:
  dest=tmp/name;pack=dest/'proposal';dest.mkdir();shutil.copy(P.parent/'claim.json',dest/'claim.json');shutil.copy(P.parent/'input_manifest.json',dest/'input_manifest.json');shutil.copytree(P,pack)
  d=copy.deepcopy(D);acts={a['id']:a for a in d['actions']}
  if name=='unknown_pose':acts['A-MECH-WORK']['poses']['punch']='UNDEFINED_POSE→P2'
  if name=='work_starts_at_P0':acts['A-MECH-WORK']['poses']['punch']='P0→P2'
  if name=='drop_isolation_guard':acts['A-MECH-WORK']['extra_entry_guards'].remove('G_ISOLATED_CURRENT')
  if name=='cross_scenario_work_binding':
   r=next(r for r in acts['A-COMPACT']['source_bindings'] if r['proposed_cad_field']=='stroke.work');r.update(parameter_id='R3_BASE_B_WORK_STROKE',source='verification/r3_parametric_sizing/results/BASE_B.json')
  if name=='wrong_parent_mode':acts['B-MECH-WORK']['parent_action_choices']=['A-COMPACT'];acts['B-MECH-WORK']['current_parent_guards']={'A-COMPACT':[]}
  (pack/'permissions.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
  modified_baseline=None
  if name in ['reduced_rod','reduced_work_force','shortened_work_stroke']:
   modified_baseline=json.loads((pack/'baseline_bindings.json').read_text())
   key={'reduced_rod':'cylinder.rod_diameter','reduced_work_force':'load.work_peak','shortened_work_stroke':'stroke.work'}[name]
   next(r for r in modified_baseline['rows'] if r['scenario']=='BASE_A' and r['proposed_cad_field']==key)['value']*=0.5
   (pack/'baseline_bindings.json').write_text(json.dumps(modified_baseline,ensure_ascii=False,indent=2)+'\n')
  generation=subprocess.run([sys.executable,'-B',str(pack/'render_schemes.py'),'--output-dir',str(pack/'exports')],capture_output=True,text=True);assert generation.returncode==0,generation.stderr
  before={str(p.relative_to(pack)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pack.rglob('*') if p.is_file()}
  r=subprocess.run([sys.executable,'-B',str(P/'check_package.py'),'--package',str(pack)],capture_output=True,text=True)
  after={str(p.relative_to(pack)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pack.rglob('*') if p.is_file()}
  assert before==after
  new_semantic_errors=sorted(semantic_errors(d)-baseline_semantic_errors)
  if modified_baseline is not None and modified_baseline['rows']!=orig:new_semantic_errors.append('authoritative-source-row-changed')
  semantic_rejected=bool(new_semantic_errors)
  assert semantic_rejected,(name,'Independent checker failed to detect mutation')
  mutants.append(dict(id=name,expected='DOCUMENT_MISMATCH_NONZERO',author_exit=r.returncode,author_report=json.loads(r.stdout),independent_semantic_rejection=semantic_rejected,independent_errors=new_semantic_errors,files_unchanged=before==after))
  check('semantic-mutation:'+name,r.returncode!=0,dict(author_accepts_inconsistent_document=r.returncode==0))
  if r.returncode==0:issue('R5-CI-B03',dict(mutation=name,problem='Coherent regenerated exports accepted by checker despite semantic inconsistency'))
with (P/'exports/positions_permissions.csv').open() as f:
 rows=list(csv.DictReader(f))
for row,a in zip(rows,D['actions']):
 errors=[]
 for key,actual in row.items():
  expected=a[key]
  if isinstance(expected,(dict,list)):actual=json.loads(actual)
  if actual!=expected:errors.append(key)
 check('full-csv-row:'+a['id'],not errors,errors)
# Numeric motion consistency independently from authoritative bindings; no numerical recalculation of physics.
for scenario in ['BASE_A','BASE_B']:
 q={r['proposed_cad_field']:r['value'] for r in B if r['scenario']==scenario}
 check('return-sum:'+scenario,abs(q['stroke.return']-sum(q['stroke.'+x] for x in ['approach','work','eject']))<1e-12)
 for phase in ['approach','work','eject','return']:
  check('stroke-time-speed:'+scenario+':'+phase,abs(q['stroke.'+phase]-q['phase.'+phase+'.time']*q['phase.'+phase+'.speed'])<1e-12)
result=dict(reviewed_C='ed8272ce6ebc2047bb0d896db5951d02c42d5208',session_id='r5-cyc0203-20261113',checks=checks,total_checks=len(checks),passed=sum(x['passed'] for x in checks),failed=[x for x in checks if not x['passed']],findings=findings,semantic_mutants=mutants,independent_truth_table=truth,geometry='NOT_RUN',physical_READY='NO_GO',W02='OPEN_NOT_IMPLEMENTED',G1='OPEN',execution_status='EVIDENCE_CAPTURED')
print(json.dumps(result,ensure_ascii=False,indent=2))
# Exit 0 captures findings; acceptance is explicitly not represented by process exit.
