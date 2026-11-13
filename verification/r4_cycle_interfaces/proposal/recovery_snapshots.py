"""Scoped admission before the unchanged frozen recovery policy.

Maps are validated, never completed or repaired. This module is documentary;
no proposed state returned by frozen recover is applied to the caller.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from metadata_types import metadata_equal, revision, revision_map

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / 'verification/r4_cycle_contract/contract.json'
HELPER = ROOT / 'verification/r4_cycle_contract/permission_examples.py'
CONTRACT_SHA = '5ea62e56fd2d95a7e87df81187e8e0a93a93891513b12c8e10b1a5911f84377c'
HELPER_SHA = 'e4bce420b1cec04e65600d5caf979287797d255d5a718b769f7490d50b4e8ac3'
ACTION = 'RESTORE_B_CLOSURE'
TARGET = 'B_RESET_CONFIRMED'


def definitions(contract):
    data = CONTRACT.read_bytes()
    if hashlib.sha256(data).hexdigest() != CONTRACT_SHA or hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA:
        raise ValueError('FIXED_DEFINITION_OR_HELPER_CHANGED')
    fixed = json.loads(data)
    if not metadata_equal(contract, fixed): raise ValueError('FIXED_CONTRACT_MISMATCH')
    guards = {g['id']: g for g in fixed['guards']}
    action = next(a for a in fixed['recovery_actions'] if a['id'] == ACTION)
    if TARGET not in action['may_reestablish'] or guards[TARGET]['evidence_domains'] != ['B_CLOSURE']:
        raise ValueError('UNSUPPORTED_FIXED_TARGET')
    for guard in action['entry_guards']:
        if guard not in guards: raise ValueError('MISSING_ENTRY_DEFINITION:' + guard)
    spec = importlib.util.spec_from_file_location('snapshot_frozen_helper', HELPER)
    helper = importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    return fixed, guards, action, helper


def assess(request, context, contract):
    result = {'validation': {'status': 'REJECTED', 'reasons': []},
              'compatibility_domain': 'OUT_OF_DOMAIN', 'policy_result': 'NOT_EVALUATED',
              'recovery_value': 'UNKNOWN', 'entry_gate': 'INDETERMINATE',
              'causal_value': 'UNKNOWN', 'action_gate': 'INDETERMINATE', 'physical_permission': False}
    reasons = result['validation']['reasons']
    def fail(path, code, **detail): reasons.append({'path': path, 'code': code, **detail})

    def finish():
        # Available before schema/definition dispatch; every assessment exit
        # composes the independent facts collected so far, including UNKNOWN.
        values = [result['recovery_value'], result['causal_value'],
                  {'BLOCKED': 'FALSE', 'INDETERMINATE': 'UNKNOWN', 'ALLOWED_ASSUMED': 'TRUE'}[result['entry_gate']]]
        result['action_gate'] = ('BLOCKED' if 'FALSE' in values else
                                 'INDETERMINATE' if 'UNKNOWN' in values else 'ALLOWED_ASSUMED')
        return result

    try: fixed, guards, action, helper = definitions(contract)
    except (ValueError, OSError, KeyError, StopIteration) as exc:
        result['validation']['status'] = 'UNSUPPORTED';fail('contract', str(exc));return finish()
    known = set(fixed['evidence_policy']['domains'])
    required = set(guards[TARGET]['evidence_domains'])
    entry_domains = set().union(*(set(guards[g]['evidence_domains']) for g in action['entry_guards']))
    result['required_result_domains'] = sorted(required)
    result['required_context_domains'] = sorted(required | entry_domains)
    result['permitted_extra_domains'] = sorted(known)
    if type(context) is not dict:
        fail('context', 'CONTEXT_MUST_BE_OBJECT');return finish()
    faults = context.get('faults')
    evidence = context.get('evidence')
    fid = request.get('fault_id') if type(request) is dict else None
    fault = faults.get(fid) if type(faults) is dict and type(fid) is str else None
    try: history_valid = helper.history_valid(context)
    except (KeyError, TypeError, AttributeError, ValueError): history_valid = False

    def addressed(key, item):
        """Trust immutable identity/links, independently of mutable result maps."""
        if type(key) is not str or not re.fullmatch(r'F-[0-9a-f]{64}', key) or type(item) is not dict: return False
        orig = item.get('origin')
        if type(orig) is not dict or type(orig.get('guard')) is not str: return False
        definition = guards.get(orig['guard'])
        if definition is None: return False
        scope = orig.get('scope');fields = set(fixed['fault_policy']['identity_fields']) | {'subject_kind'}
        parents = orig.get('cause_fault_ids')
        # This checks the address of a recorded prohibition. Snapshot admission
        # below can reject recovery success; gaps in those result prerequisites
        # cannot erase an already confirmed OPEN fault or its causal links.
        return (item.get('fault_id') == key == 'F-' + helper.digest(orig)
                and type(scope) is dict and set(scope) == fields
                and all(type(v) is str and v for v in scope.values())
                and scope['subject_kind'] == definition['fault_subject_kind']
                and type(parents) is list and all(type(p) is str and re.fullmatch(r'F-[0-9a-f]{64}', p) for p in parents))

    # ENTRY/state facts are evaluated independently of target-proof admission.
    # Per-guard failures remain visible even if another guard's input is malformed.
    entry_values = {}
    entry_reasons = {}
    entry_sources = {}
    for g in action['entry_guards']:
        record = evidence.get(g) if type(evidence) is dict else None
        source = 'FROZEN_CURRENT_EVIDENCE'
        try:
            value, reason = helper.evidence_value(fixed, ACTION, g, context, record, 'ENTRY')
            if reason == 'PERMANENTLY_REJECTED_OPERATION_ID' and not history_valid:
                value, reason, source = 'UNKNOWN', 'UNCONFIRMED_REJECTION_HISTORY', 'UNCONFIRMED_HISTORY'
            elif reason == 'UNRESOLVED_ADDRESSED_FAULT':
                own = helper.open_faults(context, g)
                if g == 'EVENT_FRESH':
                    current_op = context.get('operation_id')
                    own = [f for f in own if type(current_op) is str and current_op and f['origin'].get('operation_id') == current_op]
                confirmed = [f for f in own if history_valid and addressed(f.get('fault_id'), f)]
                if value == 'FALSE' and any(f['origin'].get('truth') == 'FALSE' for f in confirmed):
                    source = 'CONFIRMED_ADDRESSED_OWN_FAULT'
                else:
                    value, source = 'UNKNOWN', 'UNCONFIRMED_OR_UNKNOWN_OWN_FAULT'
                    # A damaged journal cannot erase an independent current
                    # FALSE record. This tightening is outside domain admission.
                    raw, raw_reason = helper._raw_value(fixed, ACTION, g, context, record, 'ENTRY')
                    if raw == 'FALSE' and len(confirmed) != len(own):
                        value, reason, source = raw, raw_reason, 'FROZEN_CURRENT_EVIDENCE'
        except (KeyError, TypeError, AttributeError, ValueError):
            value, reason = 'UNKNOWN', 'MALFORMED_ENTRY_INPUT'
            source = 'UNCONFIRMED_INPUT'
            fail('context.entry.' + g, reason)
        entry_values[g] = value;entry_reasons[g] = reason;entry_sources[g] = source
    state, mode, op = (context.get(k) for k in ['state', 'mode', 'operation_id'])
    identities_typed = all(type(v) is str and v for v in [state, mode, op])
    state_value = 'UNKNOWN'
    known_modes = {m for modes in fixed['state_modes'].values() for m in modes}
    if history_valid and type(state) is str and state in fixed['state_modes']:
        if state not in action['from_states']: state_value = 'FALSE'
        elif type(mode) is str and mode in known_modes:
            state_value = 'TRUE' if mode in fixed['state_modes'][state] else 'FALSE'
    denied, completed = context.get('rejected_operation_ids'), context.get('completed_operations')
    freshness = ('TRUE' if op not in denied and op not in completed else 'FALSE') if history_valid and type(op) is str and op and type(denied) is list and type(completed) is dict else 'UNKNOWN'
    result['entry_gate'] = helper.conjunction(list(entry_values.values()) + ['TRUE' if history_valid else 'UNKNOWN', freshness, state_value])
    result['entry_values'] = entry_values;result['entry_reasons'] = entry_reasons
    result['entry_sources'] = entry_sources;result['state_value'] = state_value
    result['history_confirmed'] = history_valid;result['causal_sources'] = {}

    # The explicit target and its immutable causal links do not depend on
    # proof.action/guard dispatch or on mutable proof/expected result snapshots.
    if history_valid and addressed(fid, fault) and fault['origin']['guard'] == TARGET:
        result['target_fault_id'] = fid
        values = []
        for parent in fault['origin']['cause_fault_ids']:
            item = faults.get(parent)
            status = item.get('status') if addressed(parent, item) else None
            value = {'OPEN': 'FALSE', 'RESOLVED': 'TRUE'}.get(status, 'UNKNOWN')
            result['causal_sources'][parent] = {'value': value, 'status': status,
                                                'source': 'CONFIRMED_ADDRESSED_HISTORY' if status else 'UNCONFIRMED_ADDRESS'}
            values.append(value)
        result['causal_value'] = {'BLOCKED': 'FALSE', 'INDETERMINATE': 'UNKNOWN', 'ALLOWED_ASSUMED': 'TRUE'}[helper.conjunction(values)]

    if not history_valid: fail('context.history', 'UNCONFIRMED_OR_INVALID_HISTORY')
    if not identities_typed: fail('context.identity', 'INVALID_STATE_MODE_OR_OPERATION_TYPE')
    if state_value == 'UNKNOWN': fail('context.state_mode', 'UNCONFIRMED_STATE_OR_MODE')
    if type(completed) is not dict: fail('context.completed_operations', 'INVALID_OPERATION_HISTORY')
    if 'recovered_evidence' in context and type(context['recovered_evidence']) is not dict:
        fail('context.recovered_evidence', 'INVALID_RECOVERY_HISTORY')
    if type(request) is not dict:
        fail('proof', 'PROOF_MUST_BE_OBJECT');return finish()
    if type(fid) is not str or not re.fullmatch(r'F-[0-9a-f]{64}', fid) or type(fault) is not dict:
        fail('proof.fault_id', 'UNKNOWN_OR_INVALID_TARGET');return finish()
    origin = fault.get('origin')
    if type(origin) is not dict or origin.get('guard') != TARGET or request.get('action') != ACTION or request.get('guard') != TARGET:
        result['validation']['status'] = 'UNSUPPORTED';fail('target', 'UNSUPPORTED_GUARD_ACTION_PAIR');return finish()
    if type(fault.get('resolution_attempts')) is not list:
        fail('faults.' + fid + '.resolution_attempts', 'INVALID_RESOLUTION_HISTORY')

    def check_map(value, expected, exact, path):
        if not revision_map(value): fail(path, 'INVALID_INTEGER_SNAPSHOT');return False
        keys = set(value);missing = expected - keys;extra = keys - (expected if exact else known)
        if missing: fail(path, 'MISSING_REQUIRED_DOMAINS', missing=sorted(missing))
        if extra: fail(path, 'UNPERMITTED_EXTRA_DOMAINS', extra=sorted(extra))
        return not missing and not extra

    def check_fault(key, item):
        if type(item) is not dict or type(item.get('origin')) is not dict:
            fail('faults.' + key, 'MISSING_CAUSAL_OR_ENTRY_FAULT');return
        orig = item['origin'];guard = orig.get('guard')
        definition = guards.get(guard) if type(guard) is str else None
        if definition is None: fail('faults.' + key, 'UNKNOWN_GUARD_DEFINITION');return
        domains = set(definition['evidence_domains'])
        prefix = 'faults.' + key
        o = check_map(orig.get('revisions'), domains, True, prefix + '.origin.revisions')
        e = check_map(item.get('expected_revisions'), domains, True, prefix + '.expected_revisions')
        scope = orig.get('scope');fields = set(fixed['fault_policy']['identity_fields']) | {'subject_kind'}
        if (type(scope) is not dict or set(scope) != fields or any(type(v) is not str or not v for v in scope.values())
                or scope.get('subject_kind') != definition['fault_subject_kind']): fail(prefix + '.origin.scope', 'INCOMPLETE_OR_WRONG_GUARD_SCOPE')
        history = item.get('revision_history')
        if type(history) is not list: fail(prefix + '.revision_history', 'MISSING_REVISION_HISTORY');return
        if not (o and e): return
        # Fold an already complete immutable origin locally; never repair input.
        running = dict(orig['revisions'])
        for i, event in enumerate(history):
            path = prefix + '.revision_history.' + str(i)
            if (type(event) is not dict or set(event) != {'domain', 'from_revision', 'to_revision'}
                    or type(event.get('domain')) is not str or event['domain'] not in domains or not revision(event.get('from_revision'), 0)
                    or not revision(event.get('to_revision'), 0)):
                fail(path, 'INVALID_HISTORY_EVENT');return
            domain = event['domain']
            if event['from_revision'] != running[domain] or event['to_revision'] != event['from_revision'] + 1:
                fail(path, 'UNCONFIRMED_REVISION_ADVANCE');return
            running[domain] = event['to_revision']
        if not metadata_equal(running, item['expected_revisions']): fail(prefix + '.expected_revisions', 'EXPECTED_NOT_JUSTIFIED_BY_HISTORY')

    # Validate target, its causal ancestors and faults actually used by ENTRY.
    used = [fid] + [k for k,f in faults.items() if type(f) is dict and f.get('status') == 'OPEN'
                    and type(f.get('origin')) is dict and f['origin'].get('guard') in action['entry_guards']
                    and (f['origin']['guard'] != 'EVENT_FRESH' or f['origin'].get('operation_id') == op)]
    seen = set()
    while used:
        key = used.pop()
        if type(key) is not str:
            fail('faults', 'INVALID_FAULT_KEY');continue
        if key in seen: continue
        seen.add(key);item = faults.get(key);check_fault(key, item)
        if type(item) is dict and type(item.get('origin')) is dict:
            parents = item['origin'].get('cause_fault_ids')
            if type(parents) is not list or any(type(k) is not str for k in parents): fail('faults.' + key, 'INVALID_CAUSAL_IDENTITIES')
            else: used.extend(parents)
    check_map(request.get('origin_revisions'), required, True, 'proof.origin_revisions')
    check_map(request.get('revisions'), required, False, 'proof.revisions')
    check_map(context.get('revisions'), required | entry_domains, False, 'context.revisions')
    for g in action['entry_guards']:
        rec = evidence.get(g) if type(evidence) is dict else None
        if type(rec) is not dict: fail('context.evidence.' + g, 'MISSING_ENTRY_EVIDENCE')
        else: check_map(rec.get('revisions'), set(guards[g]['evidence_domains']), False, 'context.evidence.' + g + '.revisions')
    if reasons: return finish()

    result['compatibility_domain'] = 'IN_DOMAIN'
    agreed = (metadata_equal(request['origin_revisions'], origin['revisions'])
              and all(request['revisions'][d] == fault['expected_revisions'][d] == context['revisions'][d] for d in required))
    result['validation']['status'] = 'VALID' if agreed else 'UNCONFIRMED'
    if not agreed: fail('proof.revision_bindings', 'STALE_OR_WRONG_SCOPED_REVISION')
    # Only admitted domain/type/history inputs reach this frozen policy call.
    try: _, policy = helper.recover(fixed, ACTION, context, fid, request)
    except (KeyError, TypeError, AttributeError, ValueError, StopIteration) as exc:
        result['validation']['status'] = 'REJECTED';result['compatibility_domain'] = 'OUT_OF_DOMAIN'
        fail('policy', 'MALFORMED_POLICY_INPUT', exception=type(exc).__name__);return finish()
    result['policy_result'] = policy
    result['recovery_value'] = {'ALLOWED_ASSUMED': 'TRUE', 'BLOCKED': 'FALSE', 'INDETERMINATE': 'UNKNOWN'}[policy] if agreed else 'UNKNOWN'
    return finish()
