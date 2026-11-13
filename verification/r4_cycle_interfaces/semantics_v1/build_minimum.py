"""Author the v1 document minimum from immutable reviewed inputs, never --package.

An explicit authoring operation; verification never runs this file or rewrites
rules. A new rule revision needs a recorded basis and independent RECHECK.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = '144941cbfc67002cbe81765e38c80e237473deff'
DECISION = '5fe510bbc55a052c360ab39a2491a061584b8fb7'
FROZEN = '0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed'
P = 'verification/r4_cycle_interfaces/proposal/'


def blob(commit, path):
    return json.loads(subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT))


# Independently stated stage-family rules, with shared invariants from the
# reviewed protocol. These are requirements, not guards discovered in --package.
COMMON = {'BASIS_DEFINED', 'CONTINUITY_CONFIRMED', 'EVENT_FRESH', 'FEEDBACK_VALID',
          'INVENTORY_KNOWN', 'LEDGER_VALID', 'METHOD_SUPPORTED', 'RECEIVER_DEFINED', 'RESOURCES_READY'}
FAMILY = {
 'FEED-OPEN': ('D_HOME_CURRENT G_PATH_CLEAR P_FEED_CLEAR MATERIAL_HELD_CURRENT CAPACITY_CURRENT AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM G_OPEN_CURRENT'),
 'FEED-RESET': ('D_HOME_CURRENT G_PATH_CLEAR P_FEED_CLEAR MATERIAL_HELD_CURRENT CAPACITY_CURRENT AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM G_OPEN_CURRENT'),
 'DOSE-DELIVER': ('D_HOME_CURRENT D_PATH_CLEAR G_OPEN_CURRENT P_FEED_CLEAR MATERIAL_HELD_CURRENT CAPACITY_CURRENT AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM D_DELIVERY_CURRENT'),
 'FILL-CONFIRM': ('D_DELIVERY_CURRENT D_PATH_CLEAR G_OPEN_CURRENT P_FEED_CLEAR MATERIAL_HELD_CURRENT CAPACITY_CURRENT AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM D_DELIVERY_CURRENT FILL_COMPLETE'),
 'DOSER-RETURN': ('D_DELIVERY_CURRENT D_PATH_CLEAR FILL_COMPLETE G_OPEN_CURRENT P_FEED_CLEAR MATERIAL_HELD_CURRENT AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM D_HOME_CURRENT P_FEED_CLEAR'),
 'FEED-ISOLATE': ('D_HOME_CURRENT G_PATH_CLEAR P_FEED_CLEAR MATERIAL_HELD_CURRENT AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM FEEDER_SAFE FILL_COMPLETE LOAD_COMMITTED_CURRENT', 'CONTINUOUS_MECHANISM G_ISOLATED_CURRENT'),
 'APPROACH': ('D_HOME_CURRENT G_ISOLATED_CURRENT P_HOME_CURRENT P_PATH_CLEAR REACTION_CURRENT REAR_FORCE_INTERFACE AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM'),
 'WORK': ('D_HOME_CURRENT G_ISOLATED_CURRENT P_PATH_CLEAR REACTION_CURRENT REAR_FORCE_INTERFACE AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM'),
 'HOLD-UNLOAD': ('D_HOME_CURRENT G_ISOLATED_CURRENT MATERIAL_HELD_CURRENT REACTION_CURRENT AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM'),
 'UNLOCK': ('D_HOME_CURRENT G_ISOLATED_CURRENT B_UNLOADED B_OPEN_SEQUENCE_VALID MATERIAL_HELD_CURRENT P_PATH_CLEAR RECEIVER_DEFINED AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM LOCK_CLEAR'),
 'STOP-OPEN': ('B_UNLOADED B_OPEN_SEQUENCE_VALID LOCK_CLEAR MATERIAL_HELD_CURRENT P_PATH_CLEAR RECEIVER_DEFINED AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM STOP_OPEN'),
 'STOP-CLOSE': ('D_HOME_CURRENT G_ISOLATED_CURRENT EXIT_NO_INTERACTION MATERIAL_HELD_CURRENT P_FEED_CLEAR P_PATH_CLEAR RECEIPT_VALID RECOVERY_SCOPE_VALID RESET_SWEEP_CLEAR RESTORE_SEQUENCE_DEFINED AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM STOP_CLOSED_CURRENT'),
 'RELOCK': ('D_HOME_CURRENT G_ISOLATED_CURRENT MATERIAL_HELD_CURRENT P_FEED_CLEAR P_PATH_CLEAR RECEIPT_VALID RECOVERY_SCOPE_VALID RESET_SWEEP_CLEAR RESTORE_SEQUENCE_DEFINED STOP_CLOSED_CURRENT AUX_RESOURCE_CURRENT CONTINUOUS_MECHANISM', 'CONTINUOUS_MECHANISM STOP_CLOSED_CURRENT LOCK_CLOSED_CURRENT B_STOP_LOCK_CLOSED'),
}


def output_contract(action, guards):
    outputs = [{'id': 'guard:' + g, 'kind': 'GUARD_CONFIRMATION', 'guard': g,
                'scope': 'EXACT_ACTION_OPERATION_SUBJECT_MODE_REVISIONS', 'actual': 'UNKNOWN'} for g in sorted(guards)]
    for body, endpoints in sorted(action['pose_endpoints'].items()):
        outputs.append({'id': 'pose:' + body,
                        'kind': 'PRESERVED_POSE' if endpoints['end'] == ['HOLD_CURRENT'] else 'CURRENT_POSE',
                        'body': body, 'poses': endpoints['end'], 'scope': 'SAME_BODY_CURRENT_COMPLETION', 'actual': 'UNKNOWN'})
    return outputs


def main():
    document = blob(BASE, P + 'permissions.json')
    frozen = blob(FROZEN, 'verification/r4_cycle_contract/contract.json')
    inherited = {t['id']: t for t in frozen['transitions']}
    rules = {}
    for a in document['actions']:
        mech = '-MECH-' in a['id']
        if mech:
            family = a['id'].split('-MECH-')[1]
            entry, result = (set(s.split()) for s in FAMILY[family])
            entry |= COMMON
            if family not in ['STOP-CLOSE', 'RELOCK']: entry.add('DEPENDENCY_VALID')
            # Mode-specific retention and closure requirements remain binding.
            entry |= set(a['entry_guards'] + a['extra_entry_guards'])
            if a['id'] == 'B-MECH-HOLD-UNLOAD': result.add('B_UNLOADED')
            basis = [{'commit': DECISION, 'path': 'decisions/ARB-R1-CI-SEMANTICS-01.md', 'clauses': [1, 3, 4, 5]},
                     {'commit': BASE, 'path': P + 'permissions.json', 'scope': 'Reviewed B01/B02 topology, modes and invariants'},
                     {'path': 'verification/r4_cycle_interfaces/semantics_v1/build_minimum.py', 'family': family}]
        else:
            entry = set(inherited[a['id']]['entry_guards'] + a['extra_entry_guards'])
            result = set(inherited[a['id']]['completion_guards'] + a['extra_completion_guards'])
            basis = [{'commit': FROZEN, 'path': 'verification/r4_cycle_contract/contract.json', 'transition': a['id']},
                     {'commit': BASE, 'path': P + 'permissions.json', 'scope': 'Accepted documentary B01/B02 extras'},
                     {'commit': DECISION, 'path': 'decisions/ARB-R1-CI-SEMANTICS-01.md', 'clauses': [1, 3, 4]}]
        rules[a['id']] = {'variant': a['variant'], 'modes': a['mode'], 'material_from': a['material_from'],
            'material_to': a['material_to'], 'poses': a['poses'], 'pose_endpoints': a['pose_endpoints'],
            'parents': a.get('parent_action_choices', []), 'mode_parents': a.get('mode_parent_bindings', {}),
            'parent_guards': a.get('current_parent_guards', {}), 'entry_minimum': sorted(entry),
            'completion_exact': sorted(result), 'outputs': output_contract(a, result),
            'result_boundary': 'LOCAL_ONLY_PARENT_NOT_COMMITTED' if mech else 'FULL_PARENT_COMMIT',
            'parent_lifecycle': 'PREREQUISITE_BEFORE_START' if mech and family in ['FEED-OPEN','FEED-RESET','FEED-ISOLATE'] else 'AUTHORIZED_PARENT_ACTIVE' if mech else 'NOT_SUBSTEP',
            'pose_constraints': [{'body': body, 'start': endpoints['start'], 'end': endpoints['end'],
                'same_selected_pose': '→' not in a['poses'][body],
                'full_path_obligation': '→' in a['poses'][body],
                'evidence_scope': 'EXACT_BODY_OPERATION_MODE_REVISIONS'} for body,endpoints in sorted(a['pose_endpoints'].items())],
            'sources': basis, 'allowed_fields': sorted(set(a) | {'outputs', 'norm_rule', 'result_boundary', 'pose_constraints', 'parent_lifecycle'})}

    bindings = blob(BASE, P + 'baseline_bindings.json')['rows']
    refs = {(r['scenario'], r['proposed_cad_field']): r for r in bindings}
    def symbol(name): return {'op': 'symbol', 'id': name}
    def stroke(scenario, phase):
        row = refs[(scenario, 'stroke.' + phase)]
        return {'op': 'phase_stroke', 'phase': phase, 'source_ref': {
            k: row[k] for k in ['scenario', 'proposed_cad_field', 'parameter_id', 'revision', 'source', 'unit']}}
    def add(*terms): return {'op': 'sum', 'terms': list(terms)}
    for name, rule in rules.items():
        v = rule['variant'];scenario = 'BASE_' + v
        phases = ['approach','work'] if name == v+'-COMPACT' else ['eject'] if name == v+'-EJECT' else ['return'] if name == v+'-RETURN' else ['approach'] if name.endswith('-MECH-APPROACH') else ['work'] if name.endswith('-MECH-WORK') else []
        links = []
        for phase in phases:
            start,end,formula = {'approach':('P0','P1','P1'), 'work':('P1','P2','P2'),
                'eject':('P2','P3','P3'), 'return':('P3','P0','P_RETURN_END')}[phase]
            links.append({'kind':'SOURCE_AXIAL_PHASE','body':'punch','scenario':scenario,'phase':phase,
                'from_pose':start,'to_pose':end,'end_expression_pose':formula,
                'stroke_source':stroke(scenario,phase)['source_ref'],
                'direction':'NEGATIVE' if phase=='return' else 'POSITIVE'})
        if not phases:
            for body,path in rule['poses'].items():
                if '→' in path:
                    links.append({'kind':'AUX_OR_PARTIAL_UNKNOWN','body':body,'scenario':scenario,
                        'from_pose':rule['pose_endpoints'][body]['start'], 'to_pose':rule['pose_endpoints'][body]['end'],
                        'phase':'UNRESOLVED','stroke_source':None,'permission':'NO_PHYSICAL_PERMISSION'})
        rule['phase_pose_bindings'] = links
        rule['allowed_fields'].append('phase_pose_bindings');rule['allowed_fields'].sort()
    pose_rules = {}
    original = blob(BASE, P + 'poses.json')['poses']
    # The complete return expression retains its own phase source, even though
    # its nominal destination is P0. No source stroke is shortened or recomputed.
    original.append({'id': 'P_RETURN_END', 'body': 'punch', 'coordinate': 'x_P0 + S_approach + S_work + S_eject - S_return'})
    for p in original:
        name = p['id'];body = p['body']
        scenarios = ['BASE_A'] if name == 'PG_A' else ['BASE_B'] if name == 'PG_B' else ['BASE_A', 'BASE_B']
        forms = {}
        for scenario in scenarios:
            if name in ['P1', 'P2', 'P3', 'P_RETURN_END']:
                phases = ['approach'] if name == 'P1' else ['approach', 'work'] if name == 'P2' else ['approach', 'work', 'eject']
                terms = [symbol('x_P0')] + [stroke(scenario, phase) for phase in phases]
                if name == 'P_RETURN_END': terms.append({'op': 'neg', 'operand': stroke(scenario, 'return')})
                expr = add(*terms)
            elif name == 'D1': expr = add(symbol('y_D0'), symbol('S_D'))
            elif name in ['D*', 'G*']: expr = {'op': 'interval', 'ends': [{'op': 'pose', 'id': name[0] + str(i)} for i in [0, 1]]}
            elif name.startswith(('STOP_', 'LOCK_')): expr = {'op': 'unknown', 'id': name, 'reason': 'MECHANISM_UNDEFINED'}
            else: expr = symbol(p['coordinate'])
            frame = {'punch': 'CHAMBER_O', 'doser_slide': 'DOSER_DATUM', 'inlet_gate': 'GATE_DATUM',
                     'end_stop': 'STOP_DATUM_UNDEFINED', 'lock': 'LOCK_DATUM_UNDEFINED'}[body]
            axis = 'x' if body == 'punch' else 'y' if body in ['doser_slide', 'inlet_gate'] else 'UNSPECIFIED'
            forms[scenario] = {'kind': 'INTERVAL' if name.endswith('*') else 'UNRESOLVED_POINT' if name.startswith(('STOP_', 'LOCK_')) else 'POINT',
                               'unit': 'm', 'axis': axis, 'frame': frame, 'expression': expr}
        pose_rules[name] = {'body': body, 'coordinate': p['coordinate'], 'forms': forms,
            'display_formula': {'P1': 'P0 + S_approach', 'P2': 'P1 + S_work', 'P3': 'P2 + S_eject',
                                'P_RETURN_END': 'P3 - S_return'}.get(name, p['coordinate']),
            'sources': [{'commit': DECISION, 'clause': 2}, {'commit': BASE, 'path': P + 'poses.json'},
                        {'commit': BASE, 'path': P + 'baseline_bindings.json'}]}
    policy = frozen['fault_policy']
    recovery = {'parent': 'B-RESET', 'request_action': 'RESTORE_B_CLOSURE', 'target_guard': 'B_RESET_CONFIRMED',
        'target_fault_id': {'binding': 'closure_fault.fault_id', 'type': 'FAULT_ID', 'required': True, 'wildcards_allowed': False},
        'target_scope': {'binding': 'closure_fault.origin.scope', 'match': 'EXACT_ORIGIN',
                         'identity_fields': policy['identity_fields'] + ['subject_kind']},
        'origin_revisions': {'binding': 'closure_fault.origin.revisions', 'match': 'EXACT_ORIGIN'},
        'revisions': {'binding': 'closure_fault.expected_revisions', 'match': 'EXACT_CURRENT_CONTEXT'},
        'result_type': 'RECOVERY_RESULT', 'history_reconcile': 'RECONCILE_HISTORY only after causal faults addressed separately',
        'clears_faults_automatically': False,
        'helper': {'commit': FROZEN, 'path': 'verification/r4_cycle_contract/permission_examples.py',
                   'contract': 'verification/r4_cycle_contract/contract.json'}}
    norm = {'schema': 'rev-cyc-semantic-minimum/1', 'revision': 1, 'decision_commit': DECISION,
        'payload_schemas': {'permissions': 3, 'poses': 2},
        'coordinate_base': blob(BASE, P + 'poses.json')['coordinate_base'],
        'permission_fields': sorted(set(document) | {'normative_minimum'}),
        'pose_fields': sorted(set(blob(BASE, P + 'poses.json')) | {'normative_minimum'}),
        'authority': 'Author v1 minimum under R1 arbitration; independent RECHECK required, not engineering approval',
        'scope': 'Closed set of 53 documentary actions, their declared A/B modes, four unchanged unselected force variants; no PLC/W02/CAD',
        'source_commits': {'accepted_B01_B02': BASE, 'frozen_material': FROZEN, 'R1_arbitration': DECISION},
        'actions': rules, 'poses': pose_rules, 'recovery_binding': recovery,
        'supported_expression_ops': ['symbol', 'phase_stroke', 'sum', 'neg', 'interval', 'pose', 'unknown'],
        'normalization': 'Commutative/associative signed sums, exact pose aliases; ordered intervals. No multiplication/calls or arbitrary symbolic simplification.',
        'unsupported_policy': 'Nonzero UNSUPPORTED; missing/invalid data INPUT_ERROR; supported contradiction SEMANTIC_MISMATCH'}
    content = json.dumps(norm, ensure_ascii=False, indent=2) + '\n'
    (HERE / 'minimum.json').write_text(content)
    print(hashlib.sha256(content.encode()).hexdigest())


if __name__ == '__main__': main()
