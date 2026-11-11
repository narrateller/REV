"""Independent counterexamples: run with Python path pointing at reviewed engine."""
import json
from engine import pair, boundary


def box(lo, hi, delta=(0, 0, 0)):
    return {'lo': list(lo), 'hi': list(hi), 'delta': list(delta), 'motion': 'linear'}


def phase(name, time, bodies):
    return {'phase': name, 'time': time, 'registry': sorted(bodies), 'bodies': bodies}


cube = box([0, 0, 0], [1, 1, 1])
previous = phase('before', [0, 1], {'residue_1': cube})
following = phase('after', [1, 2], {'product_new': cube})
unknown_create = [{'type': 'CREATE', 'id': 'product_new', 'time': 1}]
result = boundary(previous, following, unknown_create)
assert result['status'] == 'INDETERMINATE' and result['lifecycle_status'] == 'INDETERMINATE'
print(json.dumps({'case': 'unexplained_residue_disappearance_plus_unsupported_create', 'result': result, 'expected': 'DISCONTINUITY retained independently of unsupported CREATE'}, ensure_ascii=False))

same = phase('after', [1, 2], {'residue_1': cube})
event = [{'type': 'CREATE', 'id': 'other', 'time': 1}]
result = boundary(previous, same, event)
assert result['status'] == 'CONTINUOUS'
print(json.dumps({'case': 'unsupported_create_event_without_registry_change', 'result': result, 'expected': 'INDETERMINATE for unsupported CREATE or INVALID_INPUT for inconsistent event, not CONTINUOUS'}, ensure_ascii=False))

rule = {'allowed_time': [0, 1], 'patch_yz': [[0, 2], [0, 1]], 'direction': 'either'}
a = box([-1, 0, 0], [0, 1, 1])
b = box([0, 1, 0], [1, 2, 1])
result = pair(a, b, [0, 1], rule, [0, 1])
assert result['link'] == 'LINK_CONFIRMED' and all(s['collision_status'] == 'ALLOWED_CONTACT' for s in result['segments'])
print(json.dumps({'case': 'zero_area_edge_contact', 'result': result, 'expected': 'not LINK_CONFIRMED under README positive-yz-patch requirement'}, ensure_ascii=False))

previous = phase('before', [0, '1'], {'residue_1': cube})
following = phase('after', [1, 2], {'residue_1': cube})
result = boundary(previous, following, [])
assert result['status'] == 'DISCONTINUITY'
print(json.dumps({'case': 'same_exact_time_mixed_integer_string', 'result': result, 'expected': 'CONTINUOUS for equal rational times 1 and "1"'}, ensure_ascii=False))

empty = phase('before', [0, 1], {})
added = phase('after', [1, 2], {'product_new': cube})
result = boundary(empty, added, [{'type': 'CREATE', 'id': 'product_new', 'time': 1}])
assert result['status'] == 'INDETERMINATE'
print(json.dumps({'case': 'ordinary_unsupported_create', 'result': result, 'expected': 'INDETERMINATE'}, ensure_ascii=False))

split_before = phase('before', [0, 1], {'product': cube})
split_after = phase('after', [1, 2], {'fragment_1': cube})
result = boundary(split_before, split_after, [{'type': 'SPLIT', 'id': 'product', 'time': 1}])
assert result['status'] == 'INDETERMINATE'
print(json.dumps({'case': 'ordinary_unsupported_split', 'result': result, 'expected': 'INDETERMINATE'}, ensure_ascii=False))
