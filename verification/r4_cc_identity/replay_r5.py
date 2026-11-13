"""R4 fixture-ABI replay of the 45 R5 expectations; NOT independent review.
Original source c56e494, SHA256 65355bbd6b8eae92a89611bb22b7da6d36cb3e18da3eaaa7429df47c3a8f4910.
Only fixture/history and explicit fault-ID representation adapted; expected outcomes unchanged.
Independent R5 expectations for scopes, latches and recovery. No physical model.

Exit zero means evidence was captured; known counterexample mismatches remain
failures of the reviewed permission contract, not successful permission tests.
"""
from copy import deepcopy
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'verification/r4_cycle_contract'
c=json.loads((SRC/'contract.json').read_text());ts={t['id']:t for t in c['transitions']}
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
logic=module('reviewed_permissions',SRC/'permission_examples.py');checker=module('reviewed_documents',SRC/'check_documents.py')
old=json.loads((ROOT/'verification/r5_r4_cycle_contract_review/independent_results.json').read_text())
def truth(values):
 bounds={'TRUE':(1,1),'FALSE':(0,0),'UNKNOWN':(0,1)};xs=[bounds[x] for x in values]
 lo=min(x[0] for x in xs);hi=min(x[1] for x in xs)
 return 'ALLOWED_ASSUMED' if lo else 'BLOCKED' if not hi else 'INDETERMINATE'
original=[]
for case in old['independent_cases']:
 t=ts[case['action']];g={k:case['context_overrides'].get(k,'TRUE') for k in t['required_guards']}
 expected='BLOCKED' if case['before'] not in t['from_states'] else truth(g.values())
 assert expected==case['expected_correct']
 actual=checker.classify(t,case['before'],g);assert actual==expected
 original.append({'id':case['id'],'expected_correct':expected,'actual':actual,'old_actual':case['actual'],'matches':True})
bindings=[]
for t in c['transitions']:
 assert set(t['required_guards'])==set(t['entry_guards'])|set(t['completion_guards'])
 for binding in t.get('ready_bindings',[]):
  state,target=binding['from_state'],binding['target']
  ready=c['ready_targets'][target]
  assert state in ready['from_states'] and set(ready['required_guards'])<=set(t['entry_guards'])
  bindings.append({'action':t['id'],'from_state':state,'target':target,'entry_contains_target':True})

def spec(a):return next(x for x in c['transitions']+c['recovery_actions'] if x['id']==a)
def evidence(ctx,a,g,value='TRUE',phase=None):
 t=spec(a);return dict({k:ctx[k] for k in c['evidence_policy']['scope_fields']+['operation_id']},
  action=a,guard=g,phase=phase or ('COMPLETION' if g in t['completion_guards'] else 'ENTRY'),value=value,
  evidence_id='R5-'+a+'-'+g,source='independent explicitly ASSUMED document fixture',method='R5_TEST_ONLY',
  valid_for_operation_interval=True,revisions=deepcopy(ctx['revisions']),target_scope=logic.scope(c,g,ctx))
def fixture(a,state=None):
 t=spec(a);state=state or t['from_states'][0]
 x=dict(scenario_id='independent-case',variant='A' if state.startswith('A_') else 'B',
  mode=(t.get('allowed_modes') or c['state_modes'][state])[0],cycle_epoch='batch-1',subject_id='material-1',
  operation_id='request-1',state=state,revisions={d:0 for d in c['evidence_policy']['domains']},
  evidence={},faults={},inventory_refs=['material-1'],material_assessment='ASSUMED_IDENTIFIED',pending_observations=[])
 x.update(batch_id='batch-1',basis_id='ASSUMED_SYMBOLIC_BASIS',basis_revision='basis-r1')
 x=logic.initialize_history(x,'R5-fixture-history',dict(value='TRUE',evidence_id='ASSUMED-initial-audit',source='explicit documentary fixture'))
 x['evidence']={g:evidence(x,a,g) for g in t['required_guards']};return x
def retarget(ctx,a,op,**scope):
 out=deepcopy(ctx);out.update(scope);out['operation_id']=op
 out['evidence']={g:evidence(out,a,g) for g in spec(a)['required_guards']};return out
cases=[]
def evaluate(name,a,ctx,expected,stage='COMMIT'):
 r=logic.evaluate(c,a,ctx,stage)
 cases.append({'id':name,'action':a,'stage':stage,'expected_correct':expected,'actual':r['permission_outcome'],
  'matches':r['permission_outcome']==expected,'context':deepcopy(ctx),'result':r})
 return r
def recovery(name,a,ctx,g,proof,expected,retain_fault=None):
 candidates=logic.open_faults(ctx,g)
 assert len(candidates)==1,('ambiguous test fixture target',g)
 fid=candidates[0]['fault_id']
 proof=dict(proof,fault_id=fid,origin_revisions=deepcopy(candidates[0]['origin']['revisions']))
 after,status=logic.recover(c,a,ctx,fid,proof)
 matches=status==expected and (retain_fault is None or bool(logic.open_faults(after,retain_fault)))
 cases.append({'id':name,'action':a,'guard':g,'expected_correct':expected,'actual':status,'matches':matches,
  'context':deepcopy(ctx),'proof':proof,'fault_expected_retained':retain_fault,'faults_after':deepcopy(after['faults']),
  'inventory_refs_after':after.get('inventory_refs'),'state_after':after['state']})
 return after,status

a='A-EJECT'
evaluate('fresh_action_baseline',a,fixture(a),'ALLOWED_ASSUMED')
for field in ('cycle_epoch','subject_id','operation_id','scenario_id'):
 x=fixture(a);x[field]='different-'+field
 evaluate('stale_proof_after_'+field,a,x,'INDETERMINATE')
for field,value in [('variant','B'),('mode','A_STARTUP')]:
 x=fixture(a);x[field]=value;evaluate('incompatible_'+field,a,x,'BLOCKED')
x=fixture(a);x['state']='A_EXITING';evaluate('material_state_changed',a,x,'BLOCKED')
for domain in ('MATERIAL','AXIS','EXIT_RECEIVER','RESOURCES','HYDRAULIC'):
 x=logic.change_subject(c,fixture(a),domain);evaluate('stale_after_'+domain,a,x,'INDETERMINATE')
x=fixture(a);x['evidence']['RECEIVER_DEFINED']['value']='FALSE';x['evidence']['RESOURCES_READY']['value']='UNKNOWN'
evaluate('receiver_lost_and_resource_unknown',a,x,'BLOCKED')
x=logic.change_subject(c,x,'EXIT_RECEIVER','RESOURCES');evaluate('known_receiver_failure_survives_expiration',a,x,'BLOCKED')
x=fixture(a);x['evidence']['RECEIVER_DEFINED']['action']='A-READY-EJECT'
evaluate('READY_record_is_not_action_permission',a,x,'INDETERMINATE')
x=fixture('B-COMPACT');x['evidence']['COMPACTION_CRITERION']['value']='UNKNOWN'
evaluate('press_start_does_not_require_finished_product','B-COMPACT',x,'ALLOWED_ASSUMED','ENTRY')
evaluate('no_product_commit_without_completion','B-COMPACT',x,'INDETERMINATE')
x=fixture('A-STARTUP-RETURN-A_COLUMN_ESTABLISHED');x['evidence']['RETAINED_STABLE']['value']='UNKNOWN'
r=evaluate('startup_retention_unknown','A-STARTUP-RETURN-A_COLUMN_ESTABLISHED',x,'INDETERMINATE')
after=logic.propagate(c,x,r);assert after['material_assessment']=='UNCONFIRMED' and after['inventory_refs']==x['inventory_refs']
x=fixture('B-RESET');x['evidence']['B_RESET_CONFIRMED']['value']='UNKNOWN'
x['evidence']['B_RESET_CONFIRMED']['component_observations']={'stop_closed':'TRUE','lock_restored':'UNKNOWN'}
evaluate('partial_B_reset_can_start_by_own_conditions','B-RESET',x,'ALLOWED_ASSUMED','ENTRY')
r=evaluate('partial_B_reset_cannot_commit','B-RESET',x,'INDETERMINATE')
pending=logic.propagate(c,x,r)
q=retarget(pending,'B-NEXT','after-partial-reset');q['evidence']['DEPENDENCY_VALID']['value']='UNKNOWN';q['evidence']['B_RESET_CONFIRMED']['value']='UNKNOWN'
evaluate('partial_reset_does_not_enable_next_inventory','B-NEXT',q,'INDETERMINATE')
q=fixture('RESTORE_B_CLOSURE');q['evidence']['RESET_SWEEP_CLEAR']['value']='FALSE';q['evidence']['RESOURCES_READY']['value']='UNKNOWN'
evaluate('reset_clear_false_dominates_unknown_resource','RESTORE_B_CLOSURE',q,'BLOCKED','ENTRY')

# A complete legitimate recovery path with the original subject and current scope.
x=fixture('B-NEXT');x['evidence']['B_RESET_CONFIRMED']['value']='FALSE'
bad=logic.propagate(c,x,evaluate('unrestored_B_is_blocked','B-NEXT',x,'BLOCKED'))
q=retarget(bad,'REASSESS_B_CLOSURE','audit-closure')
evaluate('closure_audit_does_not_require_goal_TRUE','REASSESS_B_CLOSURE',q,'ALLOWED_ASSUMED','ENTRY')
unknown=evidence(q,'REASSESS_B_CLOSURE','B_RESET_CONFIRMED','UNKNOWN','RECOVERY_RESULT')
recovery('unknown_recovery_retains_closure_fault','REASSESS_B_CLOSURE',q,'B_RESET_CONFIRMED',unknown,'INDETERMINATE','B_RESET_CONFIRMED')
proof=evidence(q,'REASSESS_B_CLOSURE','B_RESET_CONFIRMED',phase='RECOVERY_RESULT')
restored,_=recovery('same_subject_closure_can_be_reestablished','REASSESS_B_CLOSURE',q,'B_RESET_CONFIRMED',proof,'ALLOWED_ASSUMED')
assert logic.open_faults(restored,'DEPENDENCY_VALID')
hist=retarget(restored,'RECONCILE_HISTORY','audit-history')
history_proof=evidence(hist,'RECONCILE_HISTORY','DEPENDENCY_VALID',phase='RECOVERY_RESULT')
closed,_=recovery('history_reconciles_after_cause_resolved','RECONCILE_HISTORY',hist,'DEPENDENCY_VALID',history_proof,'ALLOWED_ASSUMED')
next_ctx=retarget(closed,'B-NEXT','next-inventory')
evaluate('B_NEXT_after_complete_scoped_recovery','B-NEXT',next_ctx,'ALLOWED_ASSUMED')
next_ready=logic.propagate(c,next_ctx,logic.evaluate(c,'B-NEXT',next_ctx))
next_load=retarget(next_ready,'B-LOAD','next-load-resource-unknown')
next_load['evidence']['RESOURCES_READY']['value']='UNKNOWN'
evaluate('B_recovery_does_not_establish_unknown_next_resource','B-LOAD',next_load,'INDETERMINATE')
q=retarget(bad,'RECONCILE_HISTORY','premature-history')
recovery('history_does_not_clear_other_open_fault','RECONCILE_HISTORY',q,'DEPENDENCY_VALID',evidence(q,'RECONCILE_HISTORY','DEPENDENCY_VALID',phase='RECOVERY_RESULT'),'BLOCKED','B_RESET_CONFIRMED')
q=retarget(bad,'REASSESS_B_CLOSURE','unknown-audit-channel');q['evidence']['AUDIT_CHANNEL_READY']['value']='UNKNOWN'
evaluate('audit_channel_unknown_does_not_invent_recovery','REASSESS_B_CLOSURE',q,'INDETERMINATE','ENTRY')

# A proof for another identified material set must not resolve this lost mass.
x=fixture('A-RECEIVE');x['evidence']['LEDGER_VALID']['value']='FALSE'
lost=logic.propagate(c,x,evaluate('known_material_loss_latched','A-RECEIVE',x,'BLOCKED'))
q=retarget(lost,'REASSESS_MATERIAL','audit-unrelated',subject_id='unrelated-material-2',cycle_epoch='batch-2')
proof=evidence(q,'REASSESS_MATERIAL','LEDGER_VALID',phase='RECOVERY_RESULT')
unrelated,_=recovery('different_material_proof_cannot_clear_old_ledger_fault','REASSESS_MATERIAL',q,'LEDGER_VALID',proof,'INDETERMINATE','LEDGER_VALID')
q=retarget(unrelated,'RECONCILE_HISTORY','history-after-wrong-target')
recovery('history_must_retain_unresolved_original_material_fault','RECONCILE_HISTORY',q,'DEPENDENCY_VALID',evidence(q,'RECONCILE_HISTORY','DEPENDENCY_VALID',phase='RECOVERY_RESULT'),'BLOCKED','LEDGER_VALID')

# Rejected IDs form a set, not one replaceable slot. Both requests are actually
# rejected via the reviewed evaluator/propagator before attempting to reuse A.
x=fixture('REASSESS_MATERIAL');x['operation_id']='rejected-A';x['evidence']={g:evidence(x,'REASSESS_MATERIAL',g) for g in spec('REASSESS_MATERIAL')['required_guards']};x['evidence']['EVENT_FRESH']['value']='FALSE'
first=logic.propagate(c,x,evaluate('first_invalid_operation_ID','REASSESS_MATERIAL',x,'BLOCKED','ENTRY'))
y=retarget(first,'REASSESS_MATERIAL','rejected-B');y['evidence']['EVENT_FRESH']['value']='FALSE'
second=logic.propagate(c,y,evaluate('second_invalid_operation_ID','REASSESS_MATERIAL',y,'BLOCKED','ENTRY'))
z=retarget(second,'REASSESS_MATERIAL','rejected-A')
evaluate('earlier_rejected_ID_must_not_be_forgotten','REASSESS_MATERIAL',z,'BLOCKED','ENTRY')
fresh=retarget(second,'REASSESS_MATERIAL','genuinely-new-recovery-ID')
evaluate('new_unique_audit_ID_has_no_artificial_deadlock','REASSESS_MATERIAL',fresh,'ALLOWED_ASSUMED','ENTRY')

# Actual observation after a denied command is kept without permission or mass=0.
x=fixture('B-LOAD');x['evidence']['RESOURCES_READY']['value']='UNKNOWN'
r=evaluate('load_resource_unknown_before_observation','B-LOAD',x,'INDETERMINATE')
fact={'event_id':'observed-intake-1','kind':'DELIVER_DOSE','entity_id':'observed-material','dose_id':'dose-observed',
      'mass_record':{'value':None,'unit':'kg','basis_id':None,'status':'UNKNOWN','unknown_reason':'not measured'}}
recorded,obs=logic.record_fact(c,x,fact,r['permission_outcome'])
assert recorded['pending_observations']==[fact] and recorded['inventory_refs']==x['inventory_refs'] and recorded['state']==x['state']
assert obs['process_permission']=='NOT_GRANTED_BY_OBSERVATION'
cases.append({'id':'observation_preserved_without_mass_zero_or_permission','expected_correct':'PRESERVE_PENDING_FACT','actual':'PRESERVE_PENDING_FACT','matches':True,'observation':obs})
duplicates,_=logic.record_fact(c,recorded,fact,r['permission_outcome']);assert len(duplicates['pending_observations'])==1
conflict,_=logic.record_fact(c,duplicates,dict(fact,entity_id='other-material'),'BLOCKED')
assert len(conflict['pending_observations'])==2 and bool(logic.open_faults(conflict,'LEDGER_VALID'))
cases.append({'id':'duplicate_and_conflicting_observation_preserved','expected_correct':'NO_SECOND_ENTRY_AND_LATCH_CONFLICT','actual':'NO_SECOND_ENTRY_AND_LATCH_CONFLICT','matches':True})

x=fixture('A-EJECT');x['cycle_epoch']='new-batch-with-old-proofs'
x['evidence']['RECEIVER_DEFINED']=evidence(x,'A-EJECT','RECEIVER_DEFINED','FALSE')
evaluate('new_batch_stale_proofs_do_not_hide_current_receiver_prohibition','A-EJECT',x,'BLOCKED')
x=fixture('B-RESET');x['evidence']['B_RESET_CONFIRMED']['value']='UNKNOWN';x['evidence']['RESOURCES_READY']['value']='UNKNOWN'
evaluate('partial_B_reset_and_unknown_resource_cannot_start','B-RESET',x,'INDETERMINATE','ENTRY')
evaluate('partial_B_reset_and_unknown_resource_cannot_commit','B-RESET',x,'INDETERMINATE')

bad=[x for x in cases if not x['matches']]
assert not bad,[(x['id'],x['actual']) for x in bad] # Correct outcomes, never require old errors.
print(json.dumps({'scope':'AUTHOR_REPLAY_OF_FROZEN_R5_EXPECTATIONS_NOT_INDEPENDENT_RECHECK','original_26_cases':original,'original_26_matches':True,
 'READY_bindings_checked':bindings,'new_cases':cases,'new_case_count':len(cases),'mismatches':bad,'mismatch_count':len(bad),
 'expectation_comparison':'MATCH' if not bad else 'MISMATCH', 'independent_RECHECK':'NOT_RUN','physical_tests':'NOT_RUN','G1':'OPEN'},ensure_ascii=False,indent=2))
