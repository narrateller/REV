"""Documentary evidence logic only: no physics, movement or mass computation.

Records and revisions below are symbolic interface examples, not sensor input
handling or an implementation of the REV controller/material engine.
"""
from copy import deepcopy


def spec(contract, action):
    return next(t for t in contract['transitions'] + contract['recovery_actions'] if t['id'] == action)


def conjunction(values, state_allowed=True):
    if not state_allowed or 'FALSE' in values:
        return 'BLOCKED'
    return 'INDETERMINATE' if 'UNKNOWN' in values else 'ALLOWED_ASSUMED'


def active_fault(guard, fault, context):
    # Rejection of an invalid request is permanent for that operation ID. It
    # does not make every new, uniquely identified recovery query invalid.
    if guard == 'EVENT_FRESH' and isinstance(fault, dict):
        return fault.get('operation_id') == context.get('operation_id')
    return True


def latch(context, guard, reason):
    context.setdefault('faults', {})[guard] = (
        dict(operation_id=context.get('operation_id'),reason=reason)
        if guard == 'EVENT_FRESH' else reason
    )


def evidence_value(contract, action, guard, context, record, phase, ignore_fault=False):
    if guard in context.get('faults', {}) and active_fault(guard, context['faults'][guard], context) and not ignore_fault:
        return 'FALSE', 'UNRESOLVED_KNOWN_FAILURE'
    if not isinstance(record, dict):
        return 'UNKNOWN', 'MISSING_EVIDENCE'
    if record.get('value') not in {'TRUE', 'FALSE', 'UNKNOWN'}:
        return 'UNKNOWN', 'INVALID_TRUTH_VALUE'
    for field in contract['evidence_policy']['scope_fields'] + ['operation_id']:
        if not isinstance(context.get(field), str) or not context[field] or record.get(field) != context[field]:
            return 'UNKNOWN', 'SCOPE_MISMATCH:' + field
    if record.get('action') != action or record.get('phase') != phase:
        return 'UNKNOWN', 'WRONG_ACTION_OR_PHASE'
    if not all(isinstance(record.get(k), str) and record[k] for k in ['evidence_id','method','source']):
        return 'UNKNOWN', 'MISSING_PROVENANCE'
    definition = next(g for g in contract['guards'] if g['id'] == guard)
    for domain in definition['evidence_domains']:
        current = context.get('revisions', {}).get(domain)
        proven = record.get('revisions', {}).get(domain)
        if type(current) is not int or type(proven) is not int or current < 0 or proven != current:
            return 'UNKNOWN', 'STALE_SUBJECT:' + domain
    if record.get('valid_for_operation_interval') is not True:
        return 'UNKNOWN', 'INTERVAL_NOT_COVERED'
    return record['value'], 'CURRENT_ASSUMED_RECORD'


def evaluate(contract, action, context, stage='COMMIT'):
    if stage not in {'ENTRY', 'COMMIT'}:
        raise ValueError('unsupported documentary evaluation stage')
    t = spec(contract, action)
    required = t['entry_guards'] if stage == 'ENTRY' else t['required_guards']
    values, reasons = {}, {}
    for guard in required:
        phase = 'COMPLETION' if guard in t['completion_guards'] else 'ENTRY'
        values[guard], reasons[guard] = evidence_value(contract, action, guard, context, context.get('evidence', {}).get(guard), phase)
    state = context.get('state')
    state_allowed = state in t['from_states']
    state_allowed = state_allowed and context.get('mode') in contract['state_modes'].get(state, [])
    if 'allowed_modes' in t:
        state_allowed = state_allowed and context.get('mode') in t['allowed_modes']
    if t.get('variant') in {'A','B'}:
        state_allowed = state_allowed and context.get('variant') == t['variant']
    outcome = conjunction(list(values.values()), state_allowed)
    assessment = context.get('material_assessment', 'UNCONFIRMED')
    if any(values.get(g) in {'FALSE', 'UNKNOWN'} for g in ['INVENTORY_KNOWN', 'RETAINED_STABLE', 'STARTUP_INVENTORY_PRESERVED', 'LEDGER_VALID']):
        assessment = 'UNCONFIRMED'
    next_state = context.get('state')
    # Audit requests / ENTRY never advance a material phase or establish a goal.
    if outcome == 'ALLOWED_ASSUMED' and stage == 'COMMIT' and 'to_state' in t:
        next_state = t['to_state']
    return dict(command_execution='COMPLETED_DOCUMENT_EVALUATION',permission_outcome=outcome,stage=stage,action=action,values=values,reasons=reasons,next_state=next_state,material_assessment=assessment,physical_permission=False)


def propagate(contract, context, result):
    """Failed request has no planned material effects; remember its evidence gaps."""
    out = deepcopy(context)
    out['material_assessment'] = result['material_assessment']
    if result['permission_outcome'] == 'ALLOWED_ASSUMED':
        out['state'] = result['next_state']
        if result['stage'] == 'COMMIT':
            for domain in spec(contract, result['action']).get('invalidates_on_commit', []):
                out['revisions'][domain] += 1
        return out
    out.setdefault('unresolved_dependencies', []).append(dict(action=result['action'],outcome=result['permission_outcome']))
    for guard, value in result['values'].items():
        if value == 'FALSE':
            latch(out, guard, result['reasons'][guard])
    dep = out.setdefault('evidence', {}).get('DEPENDENCY_VALID')
    if dep:
        dep['value'] = 'UNKNOWN'
    if result['permission_outcome'] == 'BLOCKED':
        out.setdefault('faults', {})['DEPENDENCY_VALID'] = 'FAILED_MANDATORY_PREDECESSOR'
    if out['material_assessment'] == 'UNCONFIRMED':
        for guard in ['INVENTORY_KNOWN','COLUMN_CRITERION','PARTITION_DEFINED']:
            if guard in out.get('evidence', {}):
                out['evidence'][guard]['value'] = 'UNKNOWN'
    return out


def change_subject(contract, context, *domains):
    """Observed subject change invalidates old TRUE; latches are not erased."""
    out = deepcopy(context)
    # A validated known failure is not erased merely because its old positive
    # evidence generation is about to expire. No failed action is required first.
    for guard, record in context.get('evidence', {}).items():
        if not isinstance(record, dict):
            continue
        try:
            t = spec(contract, record.get('action'))
        except StopIteration:
            continue
        if guard not in t['required_guards']:
            continue
        phase = 'COMPLETION' if guard in t['completion_guards'] else 'ENTRY'
        value, _ = evidence_value(contract, t['id'], guard, context, record, phase)
        if value == 'FALSE':
            latch(out, guard, 'OBSERVED_KNOWN_FAILURE_BEFORE_SUBJECT_CHANGE')
    for domain in domains:
        out['revisions'][domain] += 1
    return out


def recover(contract, action, context, guard, record):
    t = spec(contract, action)
    request = evaluate(contract, action, context, 'ENTRY')
    out = deepcopy(context)
    if guard not in t.get('may_reestablish', []):
        raise ValueError('recovery cannot clear this condition')
    if request['permission_outcome'] != 'ALLOWED_ASSUMED':
        return out, request['permission_outcome']
    value, _ = evidence_value(contract, action, guard, context, record, 'RECOVERY_RESULT', ignore_fault=True)
    if guard == 'DEPENDENCY_VALID' and any(g != 'DEPENDENCY_VALID' and active_fault(g,f,out) for g,f in out.get('faults', {}).items()):
        value = 'FALSE'
    if value != 'TRUE':
        # UNKNOWN/stale result does not clear any existing confirmed defect.
        if value == 'FALSE':
            out.setdefault('faults', {})[guard] = 'CONFIRMED_FAILED_RECOVERY_RESULT'
        return out, 'BLOCKED' if value == 'FALSE' else 'INDETERMINATE'
    out.get('faults', {}).pop(guard, None)
    out.setdefault('recovered_evidence', {})[guard] = deepcopy(record)
    if guard == 'DEPENDENCY_VALID':
        out['unresolved_dependencies'] = []
    # No promotion of material state or copying goal TRUE into every action.
    # A subsequent action needs its own correctly scoped current evidence.
    return out, 'ALLOWED_ASSUMED'


def record_fact(contract, context, observation, permission_outcome):
    """Preserve unexpected material observations even after denied permission."""
    out = deepcopy(context)
    facts = out.setdefault('pending_observations', [])
    same_id = [f for f in facts if f.get('event_id') == observation.get('event_id')]
    if same_id and any(f != observation for f in same_id):
        facts.append(deepcopy(observation))
        latch(out, 'EVENT_FRESH', 'CONFLICTING_OBSERVATION_ID')
        latch(out, 'LEDGER_VALID', 'CONFLICTING_MATERIAL_IDENTITY_REQUIRES_RECONCILIATION')
        status = 'RECORDED_CONFLICT_REQUIRES_RECONCILIATION'
    elif same_id:
        status = 'DUPLICATE_REFERENCE_NO_SECOND_ACCOUNTING_ENTRY'
    else:
        facts.append(deepcopy(observation))
        status = 'RECORDED_PENDING_RECONCILIATION'
    out['material_assessment'] = 'UNCONFIRMED'
    if not same_id or status == 'RECORDED_CONFLICT_REQUIRES_RECONCILIATION':
        out = change_subject(contract, out, 'MATERIAL','FEED','EVIDENCE')
    for guard in ['INVENTORY_KNOWN','LEDGER_VALID','DEPENDENCY_VALID']:
        if guard in out.get('evidence', {}):
            out['evidence'][guard]['value'] = 'UNKNOWN'
    if permission_outcome == 'BLOCKED':
        out.setdefault('faults', {})['DEPENDENCY_VALID'] = 'OBSERVED_UNAUTHORIZED_EVENT'
    return out, dict(observation_status=status,process_permission='NOT_GRANTED_BY_OBSERVATION',physical_permission=False)
