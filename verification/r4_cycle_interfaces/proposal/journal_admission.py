"""Bounded classification of a frozen permission journal, never journal repair.

Only structural/semantic admission is assessed here. Applicable records do not
automatically mean FALSE, and admitted history does not grant a recovery.
"""
import re

from metadata_types import metadata_equal, revision, revision_map


def classify(context, fixed, guards, action, target_id, helper, history_valid):
    result = {'value': 'UNKNOWN', 'records': [], 'reasons': [], 'records_seen': 0,
              'open_seen': 0, 'resolved_seen': 0, 'unclassifiable': 0}
    faults = context.get('faults')
    if type(faults) is not dict:
        result['reasons'].append({'path': 'faults', 'code': 'JOURNAL_MUST_BE_OBJECT'})
        return result
    if not history_valid:
        result['reasons'].append({'path': 'history', 'code': 'UNCONFIRMED_FROZEN_HISTORY'})

    def fid(value):
        return type(value) is str and re.fullmatch(r'F-[0-9a-f]{64}', value) is not None

    def canonical(key):
        item = faults.get(key) if type(key) is str else None
        if not fid(key) or type(item) is not dict or type(item.get('origin')) is not dict: return False
        if type(item.get('status')) is not str or item['status'] not in ('OPEN', 'RESOLVED'): return False
        try: return item.get('fault_id') == key == 'F-' + helper.digest(item['origin'])
        except (TypeError, ValueError, KeyError, AttributeError): return False

    # Iterative graph walks cover finite existing nodes/links; no guessed IDs,
    # recursive material execution, or re-evaluation of historical observations.
    graph_errors = set()
    def walk(root):
        seen, active, done = set(), set(), set()
        stack = [(root, False)]
        while stack:
            key, leaving = stack.pop()
            if leaving:
                active.discard(key);done.add(key);continue
            if key in active:
                graph_errors.add((str(key), 'CAUSAL_CYCLE'));continue
            if key in done: continue
            if not canonical(key):
                graph_errors.add((str(key), 'UNCONFIRMED_CAUSAL_ADDRESS'));continue
            seen.add(key);active.add(key);stack.append((key, True))
            parents = faults[key]['origin'].get('cause_fault_ids')
            if type(parents) is not list or not all(fid(p) for p in parents):
                graph_errors.add((key, 'INVALID_CAUSAL_IDENTITIES'));continue
            if len(set(parents)) != len(parents): graph_errors.add((key, 'DUPLICATE_CAUSAL_ID'))
            stack.extend((p, False) for p in reversed(parents))
        return seen

    result_guards = set(action.get('may_reestablish', []) + action.get('may_acknowledge', []))
    ancestors = set()
    if canonical(target_id) and faults[target_id]['origin'].get('guard') in tuple(result_guards):
        ancestors = walk(target_id) - {target_id}
    for key, item in faults.items():
        if type(item) is dict and item.get('status') == 'OPEN': walk(key)

    fields = set(fixed['fault_policy']['identity_fields']) | {'subject_kind'}
    modes = {m for allowed in fixed['state_modes'].values() for m in allowed}
    variants = {t['variant'] for t in fixed['transitions'] if t.get('variant')}
    for key, item in faults.items():
        row = {'fault_id': key if type(key) is str else repr(key), 'classification': 'UNCLASSIFIABLE',
               'roles': [], 'reasons': []}
        result['records'].append(row);result['records_seen'] += 1
        def reject(path, code): row['reasons'].append({'path': path, 'code': code})
        if type(item) is not dict:
            reject('record', 'FAULT_MUST_BE_OBJECT');continue
        status = item.get('status');row['status'] = status if type(status) is str else None
        if type(status) is not str or status not in ('OPEN', 'RESOLVED'):
            reject('status', 'UNSUPPORTED_FAULT_STATUS');continue
        if not canonical(key): reject('identity', 'NONCANONICAL_FAULT_ID')
        if status == 'RESOLVED':
            result['resolved_seen'] += 1
            if not row['reasons'] and history_valid: row['classification'] = 'NOT_OPEN'
            continue
        result['open_seen'] += 1
        origin = item.get('origin')
        if type(origin) is not dict:
            reject('origin', 'ORIGIN_MUST_BE_OBJECT');continue
        guard = origin.get('guard')
        if type(guard) is not str or not guard:
            reject('origin.guard', 'INVALID_GUARD_TYPE_OR_EMPTY');continue
        if guard not in guards:
            reject('origin.guard', 'UNSUPPORTED_FIXED_GUARD');continue
        row['guard'] = guard;definition = guards[guard];domains = set(definition['evidence_domains'])
        scope = origin.get('scope')
        if (type(scope) is not dict or set(scope) != fields
                or any(type(v) is not str or not v for v in scope.values())):
            reject('origin.scope', 'INCOMPLETE_OR_INVALID_IDENTITY_SCOPE')
        else:
            if scope['subject_kind'] != definition['fault_subject_kind']: reject('origin.scope.subject_kind', 'WRONG_GUARD_SCOPE_KIND')
            if scope['variant'] not in variants or scope['mode'] not in modes: reject('origin.scope', 'UNSUPPORTED_VARIANT_OR_MODE')
            if definition['fault_subject_kind'] != 'MATERIAL':
                declared = helper.scope(fixed, guard, {})
                if any(scope[k] != declared[k] for k in ['basis_id', 'basis_revision']): reject('origin.scope', 'WRONG_NONMATERIAL_BASIS_SCOPE')
        if type(origin.get('truth')) is not str or origin['truth'] not in ('TRUE', 'FALSE', 'UNKNOWN'):
            reject('origin.truth', 'UNSUPPORTED_LATCH_TRUTH')
        parents = origin.get('cause_fault_ids')
        if type(parents) is not list or not all(fid(p) for p in parents):
            reject('origin.cause_fault_ids', 'INVALID_CAUSAL_IDENTITIES')
        elif len(set(parents)) != len(parents) or any(not canonical(p) for p in parents):
            reject('origin.cause_fault_ids', 'UNCONFIRMED_CAUSAL_ADDRESSES')

        old_event = False
        if guard == 'EVENT_FRESH':
            original_op, current_op = origin.get('operation_id'), context.get('operation_id')
            if any(type(op) is not str or not op for op in [original_op, current_op]): reject('origin.operation_id', 'UNKNOWN_OPERATION_APPLICABILITY')
            else: old_event = original_op != current_op and key not in ancestors
        roles = []
        if guard in action['entry_guards'] and not old_event: roles.append('OWN_ENTRY')
        if guard in result_guards: roles.append('RECOVERY_RESULT')
        if key in ancestors: roles.append('ADDRESSED_CAUSAL')
        row['roles'] = roles
        row['applicability_basis'] = 'OTHER_OPERATION' if old_event else 'FIXED_ACTION_AND_ADDRESSED_GRAPH'
        row['snapshot_scope'] = 'UNCONSUMED_OTHER_OPERATION' if old_event else 'COMPLETE_GUARD_DOMAINS'
        maps_valid = True
        for name, value in [('origin.revisions', origin.get('revisions')), ('expected_revisions', item.get('expected_revisions'))]:
            if not revision_map(value) or (set(value) - domains if old_event else set(value) != domains):
                reject(name, 'INVALID_OR_INCOMPLETE_GUARD_SNAPSHOT');maps_valid = False
        history = item.get('revision_history')
        if type(history) is not list:
            reject('revision_history', 'MISSING_OR_INVALID_REVISION_HISTORY')
        elif maps_valid:
            running = dict(origin['revisions'])
            for event in history:
                if (type(event) is not dict or set(event) != {'domain', 'from_revision', 'to_revision'}
                        or type(event.get('domain')) is not str or event['domain'] not in domains
                        or not revision(event.get('from_revision'), 0) or not revision(event.get('to_revision'), 0)
                        or event['to_revision'] != event['from_revision'] + 1):
                    reject('revision_history', 'INVALID_REVISION_EVENT');break
                if not old_event:
                    if running[event['domain']] != event['from_revision']:
                        reject('revision_history', 'UNCONFIRMED_REVISION_ADVANCE');break
                    running[event['domain']] = event['to_revision']
            if not old_event and not metadata_equal(running, item['expected_revisions']): reject('expected_revisions', 'EXPECTED_NOT_JUSTIFIED_BY_HISTORY')
        if not row['reasons'] and history_valid:
            row['classification'] = 'APPLICABLE' if roles else 'NOT_APPLICABLE'

    for path, code in sorted(graph_errors): result['reasons'].append({'path': path, 'code': code})
    result['unclassifiable'] = sum(r['classification'] == 'UNCLASSIFIABLE' for r in result['records'])
    if history_valid and not result['unclassifiable'] and not result['reasons']: result['value'] = 'TRUE'
    return result
