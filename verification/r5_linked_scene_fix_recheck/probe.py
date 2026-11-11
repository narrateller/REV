"""Independent regression probes. PYTHONPATH must reference reviewed C's engine."""
import json
from engine import boundary, pair


def box(lo, hi, delta=(0, 0, 0)):
    return {'lo': list(lo), 'hi': list(hi), 'delta': list(delta), 'motion': 'linear'}


def phase(name, interval, bodies):
    return {'phase': name, 'time': interval, 'registry': sorted(bodies), 'bodies': bodies}


def check(name, actual, expected, predicate):
    ok = bool(predicate(actual))
    print(json.dumps({'case': name, 'passed': ok, 'expected': expected, 'actual': actual}, ensure_ascii=False))
    return ok


cube = box([0, 0, 0], [1, 1, 1]); ok = []
before = phase('before', [0, 1], {'residue_1': cube})
after = phase('after', [1, 2], {'product_new': cube})
x = boundary(before, after, [{'type': 'CREATE', 'id': 'product_new', 'time': 1}])
ok.append(check('B01_residue_lost_with_create', x, 'DISCONTINUITY, unexplained residue, CREATE INDETERMINATE', lambda r: r['status'] == 'DISCONTINUITY' and r['unexplained_removed'] == ['residue_1'] and r['event_results'][0]['status'] == 'INDETERMINATE'))
after_same = phase('after', [1, 2], {'residue_1': cube})
x = boundary(before, after_same, [{'type': 'CREATE', 'id': 'other', 'time': 1}])
ok.append(check('B02_inconsistent_create', x, 'INVALID_INPUT, not CONTINUOUS or VALID', lambda r: r['status'] == 'INVALID_INPUT' and not r['lifecycle_valid']))
rule = {'allowed_time': [0, 1], 'patch_yz': [[0, 2], [0, 2]], 'direction': 'either'}
a = box([-1, 0, 0], [0, 1, 1]); b = box([0, 1, 0], [1, 2, 1])
x = pair(a, b, [0, 1], rule, [0, 1])
ok.append(check('B03_edge_zero_area_y', x, 'no ALLOWED_CONTACT or LINK_CONFIRMED', lambda r: r['link'] != 'LINK_CONFIRMED' and all(s['collision_status'] != 'ALLOWED_CONTACT' for s in r['segments'])))
b = box([0, 0, 1], [1, 1, 2]); x = pair(a, b, [0, 1], rule, [0, 1])
ok.append(check('B03_edge_zero_area_z', x, 'no ALLOWED_CONTACT or LINK_CONFIRMED', lambda r: r['link'] != 'LINK_CONFIRMED' and all(s['collision_status'] != 'ALLOWED_CONTACT' for s in r['segments'])))
b = box([0, '999/1000', 0], [1, 2, 1]); x = pair(a, b, [0, 1], rule, [0, 1])
ok.append(check('B03_small_positive_patch', x, 'ALLOWED_CONTACT and LINK_CONFIRMED', lambda r: r['link'] == 'LINK_CONFIRMED' and all(s['collision_status'] == 'ALLOWED_CONTACT' for s in r['segments'])))
x = boundary(phase('before', [0, '1'], {'residue_1': cube}), after_same, [])
ok.append(check('W01_equal_rational_times', x, 'CONTINUOUS for 1 and "1"', lambda r: r['status'] == 'CONTINUOUS' and r['time_contiguous']))
x = boundary(phase('before', [0, '2/2'], {'residue_1': cube}), phase('after', [1, 2], {}), [{'type': 'REMOVE', 'id': 'residue_1', 'time': '3/3', 'boundary': 0, 'geometry': cube}])
ok.append(check('W01_event_equal_rational_time', x, 'CONTINUOUS with VALID REMOVE at same exact time', lambda r: r['status'] == 'CONTINUOUS' and r['event_results'][0]['status'] == 'VALID'))
x = boundary(phase('before', [0, 1], {}), phase('after', [1, 2], {'new': cube}), [{'type': 'CREATE', 'id': 'new', 'time': 1}])
ok.append(check('unsupported_create', x, 'INDETERMINATE', lambda r: r['status'] == 'INDETERMINATE'))
x = boundary(phase('before', [0, 1], {'product': cube}), phase('after', [1, 2], {'fragment': cube}), [{'type': 'SPLIT', 'id': 'product', 'targets': ['fragment'], 'time': 1}])
ok.append(check('unsupported_split', x, 'INDETERMINATE', lambda r: r['status'] == 'INDETERMINATE'))
before_split = phase('before', [0, 1], {'product': cube, 'residue_1': cube})
after_split = phase('after', [1, 2], {'fragment': cube})
x = boundary(before_split, after_split, [{'type': 'SPLIT', 'id': 'product', 'targets': ['fragment'], 'time': 1}])
ok.append(check('B01_residue_lost_with_split', x, 'DISCONTINUITY plus SPLIT INDETERMINATE', lambda r: r['status'] == 'DISCONTINUITY' and r['unexplained_removed'] == ['residue_1'] and r['event_results'][0]['status'] == 'INDETERMINATE'))
x = boundary(phase('before', [0, 1], {}), phase('after', [1, 2], {'new': cube}), [{'type': 'CREATE', 'id': 'new', 'time': 1}, {'type': 'CREATE', 'id': 'new', 'time': 1}])
ok.append(check('B02_duplicate_create', x, 'INVALID_INPUT for duplicate plus unsupported event retained', lambda r: r['status'] == 'INVALID_INPUT' and len(r['event_results']) == 2 and r['event_results'][0]['status'] == 'INDETERMINATE' and r['event_results'][1]['status'] == 'INVALID_INPUT'))
if not all(ok): raise SystemExit(1)
