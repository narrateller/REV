"""Document-only reference semantics. Never a machine controller or W02 engine."""
import csv
import json
import re
from pathlib import Path

LOADS = ['A-LOAD-START', 'A-LOAD-STEADY', 'A-REFILL', 'B-LOAD', 'B-REFILL']
LOAD_MODES = {'A-LOAD-START': ['A_STARTUP'], 'A-LOAD-STEADY': ['A_STEADY'],
              'A-REFILL': ['A_STARTUP'], 'B-LOAD': ['B_REPEAT', 'B_SINGLE'], 'B-REFILL': ['B_REPEAT']}
RECOVERY = ['B-MECH-STOP-CLOSE', 'B-MECH-RELOCK']
FILL_SCOPE = ['variant', 'mode', 'subject_id', 'dose_id', 'material_id', 'batch_id',
              'cycle_epoch', 'basis_id', 'basis_revision', 'load_action',
              'load_operation_id', 'transfer_operation_id']
FILL_REVISIONS = ['material', 'feed', 'inventory', 'geometry', 'resource', 'receiver', 'history']
BODY = {'doser': 'doser_slide', 'gate': 'inlet_gate', 'punch': 'punch',
        'end_stop': 'end_stop', 'lock': 'lock'}
FEEDER_GUARDS = {'D_HOME_CURRENT', 'D_PATH_CLEAR', 'MATERIAL_HELD_CURRENT',
                 'P_FEED_CLEAR', 'G_PATH_CLEAR'}


def read(folder, name):
    return json.loads((Path(folder) / name).read_text())


def conjunction(values):
    values = list(values)
    if 'FALSE' in values:
        return 'BLOCKED'
    return 'ALLOWED_ASSUMED' if all(v == 'TRUE' for v in values) else 'INDETERMINATE'


def fill_value(receipt, context, require_commit=False):
    """Compare a proposed historical transfer witness to its explicit consumer scope.

    Only synthetic documentary inputs are exercised here. Physical evidence remains
    UNKNOWN. Moving D back home does not require a historical witness to say D0.
    """
    if not isinstance(receipt, dict):
        return 'UNKNOWN'
    if receipt.get('value') == 'FALSE' or receipt.get('invalidated') is True:
        return 'FALSE'
    if receipt.get('value') != 'TRUE' or receipt.get('invalidated') is not False:
        return 'UNKNOWN'
    if (receipt.get('confirmation_kind') != 'OBSERVED_TRANSFER_COMPLETE'
            or receipt.get('transfer_pose') != 'D1'
            or receipt.get('dose_delivered') != 'TRUE'
            or receipt.get('valid_for_consumer_interval') is not True
            or receipt.get('method') not in {'OBSERVED_LEDGER_RECEIPT', 'ASSUMED_FIXTURE'}
            or not all(isinstance(receipt.get(k), str) and receipt[k]
                       for k in ['evidence_id', 'source', 'method'])):
        return 'UNKNOWN'
    for key in FILL_SCOPE:
        if not isinstance(context.get(key), str) or not context[key] or receipt.get(key) != context[key]:
            return 'UNKNOWN'
    if (context['load_action'] not in LOADS or context['mode'] not in LOAD_MODES[context['load_action']]
            or context['variant'] != context['load_action'][0]):
        return 'UNKNOWN'
    commit = context.get('load_commit', {}) if require_commit else None
    for key in FILL_REVISIONS:
        expected = (commit.get('origin_revisions', {}) if require_commit else context.get('revisions', {})).get(key)
        observed = receipt.get('revisions', {}).get(key)
        if type(expected) is not int or expected < 0 or type(observed) is not int or expected != observed:
            return 'UNKNOWN'
    if require_commit:
        if commit.get('value') == 'FALSE':
            return 'FALSE'
        if (commit.get('value') != 'TRUE' or commit.get('boundary') != 'AFTER_DOSER_RETURN'
                or commit.get('receipt_id') != receipt['evidence_id']
                or commit.get('current_doser') != 'D0'
                or any(commit.get(k) != context[k] for k in FILL_SCOPE)
                or commit.get('revisions') != context.get('revisions')
                or commit.get('changed_domains') != ['material', 'feed']):
            return 'UNKNOWN'
        for key in FILL_REVISIONS:
            current = context.get('revisions', {}).get(key)
            original = receipt.get('revisions', {}).get(key)
            # Exact successor produced by the frozen LOAD commit invalidation.
            if type(current) is not int or current != original + (1 if key in ['material', 'feed'] else 0):
                return 'UNKNOWN'
    return 'TRUE'


def entry_outcome(action, values, parent=None):
    """Conjunction of listed symbolic conditions, with an explicit parent choice.

    No state is advanced, receipt created, or fault cleared by this helper.
    The frozen helper remains authoritative for addressed history/fault handling.
    """
    required = set(action['entry_guards'] + action['extra_entry_guards'])
    parents = action.get('parent_action_choices', [])
    if parents:
        if parent not in parents:
            return 'BLOCKED'
        required.update(action['current_parent_guards'][parent])
    if 'FEEDER_SAFE' in required:
        required.update(FEEDER_GUARDS)
    return conjunction(values.get(g, 'UNKNOWN') for g in required)


def inspect_semantics(folder, frozen):
    """Validate source semantics *before* trusting any freshly generated hashes."""
    folder = Path(folder)
    checks = []

    def need(name, ok):
        if not ok:
            raise ValueError('semantic:' + name)
        checks.append({'id': 'semantic:' + name, 'matched': True})

    document = read(folder, 'permissions.json')
    actions = document['actions']
    acts = {a['id']: a for a in actions}
    poses = read(folder, 'poses.json')
    known = {p['id']: p['body'] for p in poses['poses']}
    need('unique_pose_ids', len(known) == len(poses['poses']))
    guards = read(folder, 'mechanical_guards.json')
    need('no_actual_true_guards', all(g['actual'] == 'UNKNOWN' and g['value'] is None for g in guards['guards'].values()))
    guard_ids = set(guards['guards']) | {g['id'] for g in frozen['guards']}
    baseline = read(folder, 'baseline_bindings.json')['rows']
    refs = {(r['scenario'], r['proposed_cad_field']): r for r in baseline}
    need('unique_baseline_fields', len(refs) == 44)
    inherited = {a['id']: a for a in frozen['transitions']}
    for a in actions:
        name, variant = a['id'], a['variant']
        need('variant:' + name, variant in {'A', 'B'} and name.startswith(variant + '-'))
        allowed = {'A_STARTUP', 'A_STEADY'} if variant == 'A' else {'B_SINGLE', 'B_REPEAT'}
        need('mode:' + name, bool(a['mode']) and len(set(a['mode'])) == len(a['mode']) and set(a['mode']) <= allowed)
        endpoints = {}
        for body, path in a['poses'].items():
            tokens = re.split('→|/', path)
            need('poses:' + name + ':' + body, body in BODY and all(
                t == 'HOLD_CURRENT' or known.get(t) == BODY[body] for t in tokens))
            endpoints[body] = {'start': path.split('→')[0].split('/'), 'end': path.split('→')[-1].split('/')}
        need('pose_endpoints:' + name, a.get('pose_endpoints') == endpoints)
        for key in ['entry_guards', 'completion_guards', 'extra_entry_guards', 'extra_completion_guards']:
            need(key + ':' + name, len(set(a[key])) == len(a[key]) and set(a[key]) <= guard_ids)
        if 'fill_binding' in a:
            f = a['fill_binding']
            role = 'COMMIT' if name in LOADS else {'FEED-OPEN': 'PREPARE', 'FEED-RESET': 'PREPARE',
                'DOSE-DELIVER': 'PREPARE', 'FILL-CONFIRM': 'PRODUCE', 'DOSER-RETURN': 'CONSUME',
                'FEED-ISOLATE': 'CONSUME_COMMITTED'}[name.split('-MECH-')[1]]
            need('addressed_fill:' + name, f['scope_fields'] == FILL_SCOPE and f['revision_fields'] == FILL_REVISIONS
                 and f['producer'] == variant + '-MECH-FILL-CONFIRM' and f['receipt_pose'] == 'D1'
                 and f['role'] == role and f['load_commit_boundary'] == 'AFTER_DOSER_RETURN'
                 and f['load_actions'] == [p for p in LOADS if p.startswith(variant + '-')])
        # Every action must use its own complete, authoritative 22-row scenario.
        expected = {field: r for (scenario, field), r in refs.items() if scenario == 'BASE_' + variant}
        bound = a['source_bindings']
        need('action_ref_set:' + name, len(bound) == 22 and {r['proposed_cad_field'] for r in bound} == set(expected))
        for r in bound:
            b = expected[r['proposed_cad_field']]
            need('action_ref:' + name + ':' + r['proposed_cad_field'], all(r[k] == b[k] for k in ['parameter_id', 'revision', 'source']))
        phases = []
        if name.endswith('-COMPACT'): phases = ['approach', 'work']
        elif name.endswith('-EJECT'): phases = ['eject']
        elif name in [variant + '-RETURN']: phases = ['return']
        elif name.endswith('-MECH-APPROACH'): phases = ['approach']
        elif name.endswith('-MECH-WORK'): phases = ['work']
        phase_refs = a['resources']['source_main_axis_phase_refs']
        expected_fields = {'phase.' + p + '.' + k for p in phases for k in ['time', 'speed']}
        need('phase_ref_set:' + name, len(phase_refs) == len(expected_fields) and {r['proposed_cad_field'] for r in phase_refs} == expected_fields)
        for r in phase_refs:
            need('phase_ref:' + name + ':' + r['proposed_cad_field'], all(
                r[k] == expected[r['proposed_cad_field']][k] for k in ['parameter_id', 'revision', 'source', 'value', 'unit']))
        if '-MECH-' not in name:
            continue
        parents = a['parent_action_choices']
        need('parents:' + name, bool(parents) and len(parents) == len(set(parents)) and all(
            p in acts and acts[p]['variant'] == variant and p in inherited for p in parents))
        modes = {m: [p for p in parents if m in acts[p]['mode']] for m in a['mode']}
        need('mode_parent:' + name, all(modes.values()) and modes == a.get('mode_parent_bindings'))
        need('parent_guard_keys:' + name, set(a['current_parent_guards']) == set(parents))
        for p in parents:
            # Only start-only tool/pose evidence may become history, not invariants.
            expected_guards = set(inherited[p]['entry_guards']) - {'TOOLS_HOME', 'FEED_CLEAR', 'ISOLATION_CONFIRMED'}
            need('parent_invariants:' + name + ':' + p, set(a['current_parent_guards'][p]) == expected_guards)
        own = set(a['entry_guards'] + a['extra_entry_guards'])
        common = {'BASIS_DEFINED', 'CONTINUITY_CONFIRMED', 'EVENT_FRESH', 'FEEDBACK_VALID',
                  'INVENTORY_KNOWN', 'LEDGER_VALID', 'METHOD_SUPPORTED', 'RECEIVER_DEFINED', 'RESOURCES_READY'}
        need('own_invariants:' + name, common <= own)
        need('dependency_scope:' + name, ('DEPENDENCY_VALID' in own) == (name not in RECOVERY))
        suffix = name.split('-MECH-')[1]
        if suffix in {'FEED-OPEN', 'FEED-RESET', 'DOSE-DELIVER', 'FILL-CONFIRM', 'DOSER-RETURN', 'FEED-ISOLATE'}:
            dp, gp = {'FEED-OPEN': ('D0', 'G1→G0'), 'FEED-RESET': ('D0', 'G1→G0'),
                'DOSE-DELIVER': ('D0→D1', 'G0'), 'FILL-CONFIRM': ('D1', 'G0'),
                'DOSER-RETURN': ('D1→D0', 'G0'), 'FEED-ISOLATE': ('D0', 'G0→G1')}[suffix]
            need('feed_stage_poses:' + name, a['poses'] == {'doser': dp, 'gate': gp, 'punch': 'P0/PF'})
        if suffix in {'DOSE-DELIVER', 'FILL-CONFIRM', 'DOSER-RETURN', 'FEED-OPEN'}:
            expected_parents = [p for p in LOADS if p.startswith(variant + '-')]
        elif suffix == 'FEED-RESET':
            expected_parents = ['A-REFILL', 'A-LOAD-STEADY'] if variant == 'A' else ['B-REFILL', 'B-LOAD']
        else:
            expected_parents = {'APPROACH': [variant + '-COMPACT'], 'WORK': [variant + '-COMPACT'],
                'HOLD-UNLOAD': [variant + '-EJECT' if variant == 'A' else 'B-OPEN-CONFIRM'],
                'FEED-ISOLATE': [variant + '-GATHER', variant + '-COMPACT'],
                'UNLOCK': ['B-OPEN-CONFIRM'], 'STOP-OPEN': ['B-OPEN-CONFIRM'],
                'STOP-CLOSE': ['B-RESET'], 'RELOCK': ['B-RESET']}[suffix]
        need('parent_mapping:' + name, set(parents) == set(expected_parents))
        if suffix in {'APPROACH', 'WORK'}:
            need('isolated_motion:' + name, {'D_HOME_CURRENT', 'G_ISOLATED_CURRENT', 'P_PATH_CLEAR', 'REAR_FORCE_INTERFACE'} <= own)
            need('axial_continuity:' + name, a['poses']['punch'] == ('P0→P1' if suffix == 'APPROACH' else 'P1→P2'))
            need('axial_fixed_tools:' + name, a['poses']['doser'] == 'D0' and a['poses']['gate'] == 'G1')
        if suffix == 'FEED-ISOLATE':
            need('isolation_entry:' + name, FEEDER_GUARDS - {'D_PATH_CLEAR'} <= own and {'FEEDER_SAFE', 'FILL_COMPLETE', 'LOAD_COMMITTED_CURRENT'} <= own)
            need('isolation_result:' + name, 'G_ISOLATED_CURRENT' in a['extra_completion_guards'])
    need('all_pose_source_refs', len(poses['source_refs']) == 8 and {
        (r['scenario'], r['proposed_cad_field']) for r in poses['source_refs']
    } == {(s, 'stroke.' + phase) for s in ['BASE_A', 'BASE_B'] for phase in ['approach', 'work', 'eject', 'return']})
    for r in poses['source_refs']:
        b = refs[(r['scenario'], r['proposed_cad_field'])]
        need('pose_source:' + r['scenario'] + ':' + r['proposed_cad_field'], all(r[k] == b[k] for k in ['parameter_id', 'revision', 'source']))
    protocol = read(folder, 'cycle_protocol.json')
    need('fill_scope', protocol['fill']['scope_fields'] == FILL_SCOPE and protocol['fill']['revision_fields'] == FILL_REVISIONS
         and protocol['fill']['confirmation_kind'] == 'OBSERVED_TRANSFER_COMPLETE'
         and protocol['fill']['parent_commit_boundary'] == 'AFTER_DOSER_RETURN')
    need('commit_successor', protocol['fill']['commit_successor'] == {
        'origin_revisions': 'Exact receipt revisions before parent commit',
        'changed_domains': ['material', 'feed'], 'increment': 1,
        'other_revisions': 'UNCHANGED', 'scope': 'Same explicit receipt and LOAD operation only'})
    need('all_load_sequences', len(protocol['load_sequences']) == 5 and {s['parent'] for s in protocol['load_sequences']} == set(LOADS))
    for seq in protocol['load_sequences']:
        parent = acts[seq['parent']];v = parent['variant']
        need('frozen_load_successor:' + parent['id'], inherited[parent['id']]['invalidates_on_commit'] == ['MATERIAL', 'FEED'])
        need('load_commit:' + parent['id'], parent['poses']['doser'] == 'D0→D1→D0'
             and parent['commit_boundary'] == 'AFTER_DOSER_RETURN'
             and {'FILL_COMPLETE', 'D_HOME_CURRENT'} <= set(parent['extra_completion_guards'])
             and 'D_DELIVERY_CURRENT' not in parent['extra_completion_guards'])
        need('load_receipt_binding:' + parent['id'], parent.get('fill_binding', {}).get('role') == 'COMMIT')
        expected_stages = [v + '-MECH-' + s for s in ['FEED-OPEN', 'DOSE-DELIVER', 'FILL-CONFIRM', 'DOSER-RETURN']]
        need('stage_order:' + parent['id'], seq['stages'] == expected_stages and seq['commit_after'] == expected_stages[-1]
             and seq['modes'] == parent['mode'] and seq['next_isolation'] == v + '-MECH-FEED-ISOLATE' and seq['same_retained_inventory'] is True)
        for i, stage in enumerate(seq['stages']):
            a = acts[stage]
            need('stage_receipt_binding:' + stage, bool(a.get('fill_binding')))
            need('stage_parent:' + parent['id'] + ':' + stage, parent['id'] in a['parent_action_choices'] and set(parent['mode']) <= set(a['mode']))
            if i:
                prev = acts[seq['stages'][i - 1]]
                need('stage_continuity:' + parent['id'] + ':' + stage, all(
                    prev['pose_endpoints'][b]['end'] == a['pose_endpoints'][b]['start'] for b in ['doser', 'gate', 'punch']))
        wait, ret = acts[expected_stages[2]], acts[expected_stages[3]]
        need('isolation_receipt_binding:' + v, acts[v + '-MECH-FEED-ISOLATE'].get('fill_binding', {}).get('role') == 'CONSUME_COMMITTED')
        need('fill_before_return:' + parent['id'], 'FILL_COMPLETE' in wait['extra_completion_guards'] and 'FILL_COMPLETE' in ret['extra_entry_guards']
             and wait['poses']['doser'] == 'D1' and ret['poses']['doser'] == 'D1→D0'
             and all(acts[s].get('parent_commit_boundary') == 'AFTER_DOSER_RETURN' for s in expected_stages[1:]))
    need('feeder_guard_dependencies', set(guards['guard_dependencies']['FEEDER_SAFE']) == FEEDER_GUARDS)
    need('closure_guard_dependencies', set(guards['guard_dependencies']['B_STOP_LOCK_CLOSED']) == {'STOP_CLOSED_CURRENT', 'LOCK_CLOSED_CURRENT'})
    deps = guards['guard_dependencies']
    need('isolation_guard_dependencies', set(deps['G_ISOLATED_CURRENT']) == {'G_PATH_CLEAR', 'MATERIAL_HELD_CURRENT'})
    for guard, required in deps.items():
        need('dependency_refs:' + guard, guard in guard_ids and set(required) <= guard_ids)
        def acyclic(node, trail):
            return node not in trail and all(acyclic(child, trail | {node}) for child in deps.get(node, []))
        need('acyclic_guard:' + guard, acyclic(guard, set()))
    for name in RECOVERY:
        a = acts[name];binding = a['recovery_binding']
        need('targeted_recovery:' + name, binding['parent'] == 'B-RESET' and binding['request_action'] == 'RESTORE_B_CLOSURE'
             and binding['target_guard'] == 'B_RESET_CONFIRMED' and binding['clears_faults_automatically'] is False
             and set(protocol['recovery']['requires']) <= set(a['entry_guards'] + a['extra_entry_guards']))
        need('no_reset_completion_in_entry:' + name, not {'B_RESET_CONFIRMED', 'RESET_CURRENT', 'DEPENDENCY_VALID'} & set(a['entry_guards'] + a['extra_entry_guards']))
    need('stop_then_lock', acts[RECOVERY[0]]['poses']['end_stop'] == 'STOP_OPEN→STOP_CLOSED'
         and acts[RECOVERY[1]]['poses']['lock'] == 'LOCK_OPEN→LOCK_CLOSED'
         and 'STOP_CLOSED_CURRENT' in acts[RECOVERY[0]]['extra_completion_guards']
         and 'STOP_CLOSED_CURRENT' in acts[RECOVERY[1]]['extra_entry_guards'])
    need('separate_history_reconciliation', protocol['recovery']['history_action'] == 'RECONCILE_HISTORY'
         and protocol['recovery']['auto_clear_other_faults'] is False and protocol['recovery']['generic_dependency_required'] is False)
    # Compare the entire CSV/MD/SVG payload, not a subset of columns or manifest hashes.
    from render_schemes import documents
    exports = documents(folder)
    for name, content in exports.items():
        need('export_content:' + name, (folder / 'exports' / name).read_text() == content)
    with (folder / 'exports/positions_permissions.csv').open() as stream:
        reader = csv.DictReader(stream);rows = list(reader);columns = reader.fieldnames
    need('all_csv_columns', set(columns) == set().union(*(a.keys() for a in actions)))
    need('all_csv_rows', len(rows) == len(actions))
    for row, action in zip(rows, actions):
        need('full_csv:' + action['id'], all(
            (json.loads(row[k]) if isinstance(action.get(k), (dict, list)) or action.get(k) is None else row[k]) == action.get(k)
            for k in columns))
    return checks
