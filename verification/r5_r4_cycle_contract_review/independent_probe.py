"""R5 independent document logic/ledger probes, not a physical or lifecycle engine.

Expected outcomes use three-valued interval conjunction and stated material
invariants. Captured mismatches are failures of the reviewed contract, even when
this experiment runner itself exits zero. Atoms are synthetic accounting tokens.
"""
import collections,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'verification/r4_cycle_contract'
c=json.loads((SRC/'contract.json').read_text());ts={t['id']:t for t in c['transitions']}
spec=importlib.util.spec_from_file_location('author_document_checker',SRC/'check_documents.py')
author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)

def reference(before,allowed,values):
    intervals={'TRUE':(1,1),'FALSE':(0,0),'UNKNOWN':(0,1)}
    conditions=[intervals[v] for v in values]+[(int(before in allowed),int(before in allowed))]
    low=min(v[0] for v in conditions);high=min(v[1] for v in conditions)
    return 'ALLOWED_ASSUMED' if low==1 else 'BLOCKED' if high==0 else 'INDETERMINATE'

examples=[];counts=collections.Counter()
for e in json.loads((SRC/'transition_examples.json').read_text()):
    t=ts[e['transition']];expected=reference(e['before'],t['from_states'],e['guard_values'].values())
    assert expected==e['expected'],e['id']
    actual=author.classify(t,e['before'],e['guard_values']);assert actual==expected
    assert e['after']==(t['to_state'] if expected=='ALLOWED_ASSUMED' else e['before'])
    assert not e['physical_permission'];counts[actual]+=1
    examples.append({'id':e['id'],'independent':expected,'actual':actual,'state_effect_matches':True})
traces=[]
for s in json.loads((SRC/'sequence_examples.json').read_text()):
    state=s['initial_state'];events=[]
    for step in s['steps']:
        t=ts[step['transition']];assert step['before']==state
        expected=reference(state,t['from_states'],step['guard_values'].values())
        assert expected=='ALLOWED_ASSUMED' and step['after']==t['to_state']
        events.append(step['step_id']);state=step['after']
    assert len(events)==len(set(events)) and state==s['final_state'] and not s['physical_permission']
    traces.append({'id':s['id'],'steps':len(events),'initial':s['initial_state'],'final':state,
                   'state_and_written_guard_consistency':'PASS','linked_READY_or_material_ledger_proven':False,
                   'scope':'Author trace has state/guard assignments and textual inventory_effect only; no entity-level mass journal is executed.'})

new=[]
def inspect(name,action,overrides,expected=None,ready=None,before=None,extra_required=(),reason=''):
    t=ts[action];state=before or t['from_states'][0]
    required=set(t['required_guards'])|set(extra_required)
    if ready:required.update(ts[ready]['required_guards'])
    context={g:'TRUE' for g in required|set(overrides)};context.update(overrides)
    correct=reference(state,t['from_states'],[context[g] for g in required])
    if expected:assert correct==expected,(name,correct,expected)
    actual=author.classify(t,state,{g:context[g] for g in t['required_guards']})
    ready_result=None
    if ready:
        rt=ts[ready];ready_result=author.classify(rt,state,{g:context[g] for g in rt['required_guards']})
    new.append({'id':name,'action':action,'ready_target_transition':ready,'before':state,
                'context_overrides':overrides,'action_guard_values':{g:context[g] for g in t['required_guards']},
                'omitted_required_conditions':sorted(required-set(t['required_guards'])),
                'expected_correct':correct,'actual':actual,'matches_expected':correct==actual,
                'READY_outcome_same_context':ready_result,'reason':reason})

# Actual material predicates are derived from independent finite-set accounting.
def valid_partition(parent,outgoing,retained):
    return not (outgoing&retained) and outgoing|retained==parent
def inventory_valid(expected,active_entities):
    atoms=[a for e in active_entities for a in e]
    return set(atoms)==expected and len(atoms)==len(set(atoms))
parent={'old1','old2','new1','new2'};out={'old1','new1'};ret={'old2','new2'}
assert valid_partition(parent,out,ret)
lost=ret-{'old2'};assert not inventory_valid(parent,[out,lost])
inspect('material_loss_and_unknown_receipt','A-RECEIVE',{'LEDGER_VALID':'FALSE','RECEIPT_VALID':'UNKNOWN'},expected='BLOCKED',reason='Known missing old2 atom, independently detected; UNKNOWN receipt cannot hide known ledger loss.')
inspect('unknown_loss_not_zero','B-NEXT',{'LEDGER_VALID':'UNKNOWN','INVENTORY_KNOWN':'UNKNOWN'},expected='INDETERMINATE',reason='Unmeasured loss/exchange/residue remains unknown, not a zero correction.')
assert not inventory_valid(parent,[parent,out,ret])
inspect('active_parent_plus_children_double_count','A-SEGMENT',{'LEDGER_VALID':'FALSE','PARTITION_DEFINED':'FALSE'},expected='BLOCKED',reason='Parent and its children counted together; independent atom multiplicity detects duplication.')
assert not valid_partition(parent,out,ret|{'old1'})
inspect('overlapping_partition_with_unknown_method','A-SEGMENT',{'PARTITION_DEFINED':'FALSE','LEDGER_VALID':'FALSE','METHOD_SUPPORTED':'UNKNOWN'},expected='BLOCKED',reason='Outgoing and retained share old1; known overlap dominates unknown method.')
inspect('missing_remainder_and_unknown_receiver','B-RECEIVE',{'LEDGER_VALID':'FALSE','PARTITION_DEFINED':'FALSE','RECEIVER_DEFINED':'UNKNOWN'},expected='BLOCKED',reason='Unaccounted remainder cannot disappear upon acceptance.')
inspect('basis_mismatch_and_unknown_receipt','B-RECEIVE',{'BASIS_DEFINED':'FALSE','RECEIPT_VALID':'UNKNOWN'},expected='BLOCKED',reason='Wet/dry basis without conversion/exchange data is a known incompatible comparison.')
inspect('whole_outside_but_receipt_unknown','A-RECEIVE',{'RECEIPT_VALID':'UNKNOWN'},expected='INDETERMINATE',reason='Pending is PRESS_ACCOUNT, geometry crossing does not transfer custody.')
inspect('partial_exit_and_unknown_receipt','B-CROSS',{'WHOLE_BEYOND_EXIT':'FALSE','METHOD_SUPPORTED':'UNKNOWN'},expected='BLOCKED',reason='Only leading edge crossed; no OUTSIDE_PENDING and no removal.')
inspect('premature_REMOVE_before_acceptance','A-REMOVE',{},before='A_OUTSIDE_PENDING',expected='BLOCKED',reason='An outside pending product is not received.')
inspect('received_but_model_interaction_unknown','B-REMOVE',{'NO_MODEL_INTERACTION':'UNKNOWN'},expected='INDETERMINATE',reason='ACK is insufficient to deactivate interacting geometry.')
inspect('valid_ACK_but_reset_collision_and_unknown_method','B-RESET',{'RESET_SWEEP_CLEAR':'FALSE','METHOD_SUPPORTED':'UNKNOWN'},expected='BLOCKED',reason='Received product or residue still intersects reset sweep.')
inspect('duplicate_ACK_plus_unknown_receiver','B-RECEIVE',{'EVENT_FRESH':'FALSE','RECEIVER_DEFINED':'UNKNOWN'},expected='BLOCKED',reason='Repeat transfer cannot debit PRESS_ACCOUNT twice.')
inspect('raw_material_cannot_be_ejected','B-EJECT',{},before='B_RAW_LOADED',expected='BLOCKED',reason='An untransformed batch cannot bypass COMPACT/B_EJECTABLE.')
inspect('tools_home_does_not_resolve_material','B-READY-LOAD',{'RESIDUE_ALLOWED':'UNKNOWN','INVENTORY_KNOWN':'UNKNOWN'},expected='INDETERMINATE',reason='TOOLS_HOME alone does not establish allowed residual inventory.')
inspect('known_bad_residue_and_unknown_resource','B-READY-LOAD',{'RESIDUE_ALLOWED':'FALSE','RESOURCES_READY':'UNKNOWN'},expected='BLOCKED',reason='Known material conflict dominates unknown resources.')
inspect('wrong_B_open_sequence_and_unknown_unload','B-OPEN-CONFIRM',{'B_OPEN_SEQUENCE_VALID':'FALSE','B_UNLOADED':'UNKNOWN'},expected='BLOCKED',reason='Known sequence conflict cannot be hidden behind unknown energy unloading.')

# The same world/context is used for READY and the following action; nothing is
# changed to make the operation legal. These cases expose missing preconditions.
inspect('A_eject_after_unknown_receiver_READY','A-EJECT',{'RECEIVER_DEFINED':'UNKNOWN'},ready='A-READY-EJECT',expected='INDETERMINATE',reason='ready_draft makes receiver mandatory; action omits it and does not require a valid READY result.')
inspect('A_eject_false_resource_unknown_receiver','A-EJECT',{'RESOURCES_READY':'FALSE','RECEIVER_DEFINED':'UNKNOWN'},ready='A-READY-EJECT',expected='BLOCKED',reason='Known unavailable resource plus unknown receiver must not allow next operation.')
inspect('B_press_reset_false_resources_unknown','B-COMPACT',{'B_RESET_CONFIRMED':'FALSE','RESOURCES_READY':'UNKNOWN'},ready='B-READY-PRESS',expected='BLOCKED',reason='B-READY-PRESS requires closed/restored stop/lock; B-COMPACT omits it.')
inspect('B_load_resources_unknown','B-LOAD',{'RESOURCES_READY':'UNKNOWN'},ready='B-READY-LOAD',expected='INDETERMINATE',reason='Unknown loading resource cannot be bypassed by a separate READY self-loop.')
inspect('B_refill_resources_unknown','B-REFILL',{'RESOURCES_READY':'UNKNOWN'},ready='B-READY-REFILL',expected='INDETERMINATE',reason='Repeated gather must retain the stated refill prerequisites.')
inspect('A_compact_resources_unknown','A-COMPACT',{'RESOURCES_READY':'UNKNOWN'},ready='A-READY-PRESS',expected='INDETERMINATE',reason='Unknown pressing resources are mandatory in the written READY target.')
inspect('A_start_partial_gather_resources_unknown','A-GATHER',{'RESOURCES_READY':'UNKNOWN'},ready='A-READY-START-PRESS-A_STARTUP_RAW',expected='INDETERMINATE',reason='Startup pressing/gather has a resource-dependent READY target.')
inspect('B_eject_receiver_unknown_resources_unknown','B-EJECT',{'RECEIVER_DEFINED':'UNKNOWN','RESOURCES_READY':'UNKNOWN'},ready='B-READY-EJECT',expected='INDETERMINATE',reason='B_EJECTABLE label does not establish receiver or resources.')
inspect('A_column_startup_return_retention_unknown','A-STARTUP-RETURN-A_COLUMN_ESTABLISHED',{'RETAINED_STABLE':'UNKNOWN'},extra_required=['RETAINED_STABLE'],expected='INDETERMINATE',reason='resources_draft requires startup return/refill retention; state label is not current holding evidence. No retention guard in this return.')
inspect('A_column_startup_return_retention_false','A-STARTUP-RETURN-A_COLUMN_ESTABLISHED',{'RETAINED_STABLE':'FALSE'},extra_required=['RETAINED_STABLE'],expected='BLOCKED',reason='Known lost retention cannot be hidden by keeping A_COLUMN_ESTABLISHED unchanged.')

# Independent conservation witnesses, not an execution of a missing author ledger.
witnesses=[]
for name,initial,doses,product,retained in [
 ('A_startup_to_variable_retained',set(),[{'a1','a2'},{'b1'},{'c1','c2'}],{'a1','b1','c1'},{'a2','c2'}),
 ('B_repeat_with_initial_residue',{'r'},[{'d1a','d1b'},{'d2'}],{'r','d1a','d2'},{'d1b'})]:
 total=initial|set().union(*doses)
 assert sum(len(d) for d in doses)+len(initial)==len(total)
 assert valid_partition(total,product,retained)
 assert inventory_valid(total,[product,retained])
 pending_press=product|retained;receiver=set();assert pending_press==total
 press=set(retained);receiver=set(product)
 assert press.isdisjoint(receiver) and press|receiver==total
 geometry_active=False
 assert press|receiver==total # REMOVE has no mass/custody effect.
 witnesses.append({'id':name,'initial_atoms':sorted(initial),'dose_atoms':[sorted(d) for d in doses],
                   'product_atoms':sorted(product),'retained_atoms':sorted(retained),'pending_subset_not_added_twice':True,
                   'post_ACK_press':sorted(press),'post_ACK_receiver':sorted(receiver),'post_REMOVE_total_atoms':len(total),
                   'mass_basis':'One synthetic token basis; NOT kg inputs of REV','scope':'Constructed possible symbolic witness; does not prove a real process or an implemented ledger.'})
resources=json.loads((SRC/'resources.json').read_text());slots=0
for row in resources:
 assert bool(row['consumers']) and bool(row['start_end'])
 assert (row['kind']=='RESOURCE_OVERLAY')==(row['source_row'] in ('A8','B8'))
 for v in row['quantities'].values():assert v['value'] is None and v['status']=='UNKNOWN' and v['unit'] and v['unknown_reason'];slots+=1
assert slots==240
mismatches=[x for x in new if not x['matches_expected']];assert len(mismatches)==10
print(json.dumps({'scope':'INDEPENDENT_DOCUMENT_REVIEW_NOT_PHYSICAL_VALIDATION','original_examples':examples,'original_outcomes':dict(counts),
 'sequences':traces,'independent_cases':new,'independent_correct_outcome_mismatches':len(mismatches),
 'symbolic_ledger_witnesses':witnesses,'resource_rows':len(resources),'resource_UNKNOWN_slots':slots,
 'verdict_for_binding_contract':'REJECT_WITH_BLOCKER','reason':'Unbound READY/operation prerequisites and startup retention omissions; valid invariant prose does not bind transition semantics.'},ensure_ascii=False,indent=2))
