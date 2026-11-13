"""Anchored documentary minimum, independent of mutable package/export hashes.

Only a document gate and synthetic reference predicates. No PLC/W02 execution.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
from metadata_types import validate_metadata, metadata_equal

ROOT = Path(__file__).resolve().parents[3]
MINIMUM = ROOT / 'verification/r4_cycle_interfaces/semantics_v1/minimum.json'
MINIMUM_SHA256 = 'b1c13c18c408120ae66d4995eac706e8dbf5842f35976494efb682c74e64d3df'
DECISION = '5fe510bbc55a052c360ab39a2491a061584b8fb7'


class SemanticFailure(ValueError):
    kind = 'SEMANTIC_MISMATCH'
    def __init__(self, reason): super().__init__('semantic:' + reason)


class InputFailure(SemanticFailure): kind = 'INPUT_ERROR'
class Unsupported(SemanticFailure): kind = 'UNSUPPORTED'


def minimum():
    content = MINIMUM.read_bytes()
    if hashlib.sha256(content).hexdigest() != MINIMUM_SHA256:
        raise Unsupported('unrecognized_minimum_revision')
    result = json.loads(content);validate_metadata(result, 'minimum')
    return result


def load(folder, name):
    try:
        result = json.loads((Path(folder) / name).read_text());validate_metadata(result, name)
        return result
    except (OSError, ValueError) as exc: raise InputFailure(name + ':' + str(exc)) from exc


def metadata():
    n = minimum()
    return {'schema': n['schema'], 'revision': n['revision'], 'sha256': MINIMUM_SHA256,
            'decision_commit': DECISION}


def _merge(left, right, sign=1):
    if not isinstance(left, Counter) or not isinstance(right, Counter):
        raise Unsupported('nonlinear_or_interval_arithmetic')
    out = left.copy()
    for key, value in right.items(): out[key] += sign * value
    return Counter({k: v for k, v in out.items() if v})


class Expressions:
    def __init__(self, norm, poses):
        self.norm = norm
        self.poses = poses
        self.refs = {}
        self.symbols = set()
        def collect(node):
            if node['op'] == 'phase_stroke':
                self.refs[(node['source_ref']['scenario'], node['phase'])] = node['source_ref']
            elif node['op'] == 'symbol': self.symbols.add(node['id'])
            elif node['op'] == 'sum':
                for term in node['terms']: collect(term)
            elif node['op'] == 'neg': collect(node['operand'])
        for rule in norm['poses'].values():
            for form in rule['forms'].values(): collect(form['expression'])

    def pose(self, name, scenario, trail):
        if name in trail: raise SemanticFailure('cyclic_pose_formula:' + name)
        try: node = self.poses[name]['coordinate_forms'][scenario]['expression']
        except KeyError as exc: raise Unsupported('pose_scenario:' + name + ':' + scenario) from exc
        return self.node(node, scenario, trail | {name})

    def node(self, node, scenario, trail=frozenset()):
        if not isinstance(node, dict) or not isinstance(node.get('op'), str): raise InputFailure('expression_node')
        op = node['op']
        fields = {'symbol': {'op', 'id'}, 'phase_stroke': {'op', 'phase', 'source_ref'},
                  'sum': {'op', 'terms'}, 'neg': {'op', 'operand'}, 'interval': {'op', 'ends'},
                  'pose': {'op', 'id'}, 'unknown': {'op', 'id', 'reason'}}
        if op not in fields or set(node) != fields[op]: raise Unsupported('expression_operation_or_field:' + op)
        if op == 'symbol':
            if node['id'] not in self.symbols: raise Unsupported('expression_symbol:' + str(node['id']))
            return Counter({('symbol', node['id']): 1})
        if op == 'phase_stroke':
            expected = self.refs.get((scenario, node['phase']))
            if expected is None: raise Unsupported('expression_phase:' + str(node['phase']))
            validate_metadata(node['source_ref'], 'AST/source_ref')
            if not metadata_equal(node['source_ref'], expected): raise SemanticFailure('typed_phase_source:' + scenario + ':' + node['phase'])
            return Counter({('stroke', scenario, node['phase']): 1})
        if op == 'sum':
            if not isinstance(node['terms'], list) or not node['terms']: raise InputFailure('empty_sum')
            result = Counter()
            for term in node['terms']: result = _merge(result, self.node(term, scenario, trail))
            return result
        if op == 'neg': return _merge(Counter(), self.node(node['operand'], scenario, trail), -1)
        if op == 'pose': return self.pose(node['id'], scenario, trail)
        if op == 'interval':
            if not isinstance(node['ends'], list) or len(node['ends']) != 2: raise InputFailure('interval_endpoints')
            return ('INTERVAL', *(self.node(term, scenario, trail) for term in node['ends']))
        if node['reason'] != 'MECHANISM_UNDEFINED': raise Unsupported('unknown_coordinate_reason')
        return ('UNKNOWN', node['id'])

    def text(self, text, scenario, pose):
        if not isinstance(text, str) or not text: raise InputFailure('formula_text:' + pose)
        if text == 'UNKNOWN': return ('UNKNOWN', pose)
        try: expr = ast.parse(text, mode='eval').body
        except SyntaxError as exc: raise Unsupported('formula_syntax:' + pose) from exc
        def visit(node):
            if isinstance(node, ast.Name):
                if node.id in self.norm['poses']: return self.pose(node.id, scenario, {pose})
                if node.id.startswith('S_') and (scenario, node.id[2:]) in self.refs:
                    return Counter({('stroke', scenario, node.id[2:]): 1})
                if node.id in self.symbols: return Counter({('symbol', node.id): 1})
                raise Unsupported('formula_symbol:' + node.id)
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
                return _merge(visit(node.left), visit(node.right), -1 if isinstance(node.op, ast.Sub) else 1)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
                return _merge(Counter(), visit(node.operand), -1 if isinstance(node.op, ast.USub) else 1)
            if isinstance(node, ast.List) and len(node.elts) == 2: return ('INTERVAL', *(visit(x) for x in node.elts))
            raise Unsupported('formula_construct:' + type(node).__name__)
        return visit(expr)


def inspect_minimum(folder):
    n = minimum();p = load(folder, 'permissions.json');poses = load(folder, 'poses.json')
    checks = []
    def need(label, condition):
        if not condition: raise SemanticFailure('minimum:' + label)
        checks.append({'id': 'minimum:' + label, 'matched': True})
    need('authority', metadata_equal(p.get('normative_minimum'), poses.get('normative_minimum')) and metadata_equal(p.get('normative_minimum'), metadata()))
    if not metadata_equal(p.get('schema'), n['payload_schemas']['permissions']) or not metadata_equal(poses.get('schema'), n['payload_schemas']['poses']):
        raise Unsupported('payload_schema')
    if set(p) - set(n['permission_fields']) or set(poses) - set(n['pose_fields']): raise Unsupported('payload_top_fields')
    if poses.get('coordinate_base') is None: raise InputFailure('coordinate_base')
    need('coordinate_base', poses['coordinate_base'] == n['coordinate_base'])
    actions = p.get('actions')
    if not isinstance(actions, list) or any(not isinstance(a, dict) for a in actions): raise InputFailure('actions')
    acts = {a['id']: a for a in actions}
    need('closed_action_set', len(acts) == len(actions) and set(acts) == set(n['actions']))
    for name, a in acts.items():
        rule = n['actions'][name]
        if not isinstance(a.get('mode'), list) or any(not isinstance(m, str) for m in a['mode']): raise InputFailure('mode_type:' + name)
        unknown = set(a) - set(rule['allowed_fields'])
        if unknown: raise Unsupported('action_fields:' + name + ':' + ','.join(sorted(unknown)))
        if set(a['mode']) - set(rule['modes']): raise Unsupported('action_mode:' + name)
        need('all_modes:' + name, set(a['mode']) == set(rule['modes']))
        need('identity:' + name, a['variant'] == rule['variant'] and a['material_from'] == rule['material_from'] and a['material_to'] == rule['material_to'])
        need('poses:' + name, a['poses'] == rule['poses'] and a['pose_endpoints'] == rule['pose_endpoints'])
        need('parents:' + name, a.get('parent_action_choices', []) == rule['parents'] and a.get('mode_parent_bindings', {}) == rule['mode_parents'] and a.get('current_parent_guards', {}) == rule['parent_guards'])
        need('entry:' + name, set(rule['entry_minimum']) <= set(a['entry_guards'] + a['extra_entry_guards']))
        need('completion:' + name, set(rule['completion_exact']) == set(a['completion_guards'] + a['extra_completion_guards']))
        need('outputs:' + name, metadata_equal(a.get('outputs'), rule['outputs']))
        need('result_boundary:' + name, a.get('result_boundary') == rule['result_boundary'])
        need('parent_lifecycle:' + name, a.get('parent_lifecycle') == rule['parent_lifecycle'])
        need('pose_constraints:' + name, metadata_equal(a.get('pose_constraints'), rule['pose_constraints']))
        need('phase_pose_bindings:' + name, metadata_equal(a.get('phase_pose_bindings'), rule['phase_pose_bindings']))
        need('rule_ref:' + name, a.get('norm_rule') == 'rev-cyc-semantic-minimum/1:' + name)
        for mode in rule['modes']:
            need('coverage:' + name + ':' + mode, True)
        if name in ['B-MECH-STOP-CLOSE', 'B-MECH-RELOCK']:
            need('recovery_binding:' + name, metadata_equal(a.get('recovery_binding'), n['recovery_binding']))
    known = {r['id']: r for r in poses['poses']}
    need('closed_pose_set', len(known) == len(poses['poses']) and set(known) == set(n['poses']))
    ex = Expressions(n, known)
    pose_fields = {'id', 'body', 'coordinate', 'meaning', 'status', 'value', 'tolerance', 'unknown_reason', 'coordinate_forms', 'display_formula'}
    for name, actual in known.items():
        rule = n['poses'][name]
        if set(actual) - pose_fields: raise Unsupported('pose_fields:' + name)
        need('pose_body:' + name, actual['body'] == rule['body'])
        forms = actual.get('coordinate_forms')
        if not isinstance(forms, dict): raise InputFailure('coordinate_forms:' + name)
        need('pose_scenarios:' + name, set(forms) == set(rule['forms']))
        for scenario, expected in rule['forms'].items():
            form = forms[scenario]
            if not isinstance(form, dict) or any(form.get(k) is None for k in ['kind', 'unit', 'axis', 'frame', 'expression']): raise InputFailure('coordinate_type_or_base:' + name)
            if set(form) != set(expected): raise Unsupported('coordinate_fields:' + name)
            need('coordinate_type:' + name + ':' + scenario, all(form[k] == expected[k] for k in ['kind', 'unit', 'axis', 'frame']))
            wanted = ex.node(expected['expression'], scenario, {name})
            need('typed_formula:' + name + ':' + scenario, ex.node(form['expression'], scenario, {name}) == wanted)
            need('coordinate_formula:' + name + ':' + scenario, ex.text(actual['coordinate'], scenario, name) == wanted)
            need('display_formula:' + name + ':' + scenario, ex.text(actual.get('display_formula'), scenario, name) == wanted)
    return checks


def recovery_value(request, context, contract):
    """Read-only test of a concrete recovery result using frozen helper policy.

    Contract binding declarations are not concrete fault targets and cannot be
    used as successful recovery requests. This function clears no state/fault.
    """
    return recovery_assessment(request, context, contract)['recovery_value']


def recovery_assessment(request, context, contract):
    """Admission, scoped policy and composite action gate, all read-only."""
    from recovery_snapshots import assess
    return assess(request, context, contract)
