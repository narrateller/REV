"""Check source traceability/coverage and absence of assigned engineering values.

This validates documentary consistency, not formulas/physics or the geometry.
Outputs new evidence; use a fresh --output for each run.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from repo_support import flatten  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise SystemExit('Use a fresh --output; historical results are not overwritten')
    checks = []

    def check(name, ok, evidence):
        checks.append({'check': name, 'status': 'PASS' if ok else 'FAIL', 'evidence': evidence})

    def read(name):
        return json.loads((HERE / name).read_text())

    def blob(commit, path):
        return subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + path])

    try:
        sources = read('source_catalog.json')
        for key, src in sources.items():
            raw = blob(src['commit'], src['path'])
            check('source:' + key, hashlib.sha256(raw).hexdigest() == src['sha256'], src)
        check('authority_exact_C', sources['R1']['commit'] == '80f1028c25d1c4344c0115b7908e02346d895701', sources['R1'])
        audit = 'verification/r4_force_geometry/input_audit.json'
        check('original_audit_not_rewritten', (ROOT / audit).read_bytes()
              == blob('45caac78f00ab1535387bb5ed8d7f17caf9afc1f', audit), '§4/5/6 remain NOT_RUN')
        document = read('interfaces.json')
        rows = document['rows']
        variants = json.loads((ROOT / sources['VAR']['path']).read_text())['variants']
        variant_ids = {x['id'] for x in variants}
        bindings = json.loads((ROOT / sources['BIND']['path']).read_text())['rows']
        scoped = flatten(yaml.safe_load((ROOT / sources['RAW']['path']).read_text()))
        active = flatten(yaml.safe_load((ROOT / sources['REG']['path']).read_text()))
        ci = {x['id'] for x in json.loads((ROOT / sources['CI']['path']).read_text())['unknowns']}
        check('four_source_variants', {r['variant'] for r in rows} == variant_ids
              == {'A-V1', 'A-V2', 'B-V1', 'B-V2'}, sorted(variant_ids))
        check('no_duplicate_interface_rows', len({r['row_key'] for r in rows}) == len(rows), len(rows))
        check('scope_no_new_assumptions', document['no_new_quantitative_assumptions'] is True
              and document['author_sessions'] == ['6afb4750-7918-8191-8569-77b5b0c41050'], document['scope'])
        consumed_bindings, consumed_raw = set(), set()
        row_keys = {r['row_key'] for r in rows}
        formulas = read('symbolic_dependencies.json')
        for row in rows:
            label = row['row_key']
            check('unknowns:' + label, bool(row['unknown_arguments'])
                  and all(x['status'] == 'UNKNOWN' and x['value'] is None for x in row['unknown_arguments'])
                  and row['actual_geometry'] == 'UNKNOWN' and row['physical_evaluation'] == 'NOT_RUN',
                  'No numeric dimensions/materials/load/slice properties assigned')
            check('trace_and_recipients:' + label, bool(row['source_references'])
                  and bool(row['functional_data_recipients']) and bool(row['next_check'])
                  and 'UNKNOWN' in row['connection_DOF_contact_sides'], row['functional_data_recipients'])
            for ref in row['source_references']:
                src = sources[ref['source']]
                ok = ref['commit'] == src['commit'] and ref['path'] == src['path']
                pid = ref['source_id']
                if ref['source'] in ('RAW', 'REG'):
                    params = scoped if ref['source'] == 'RAW' else active
                    ok = ok and pid in params and params[pid]['revision'] == ref['revision']
                elif ref['source'] == 'CI':
                    ok = ok and pid in ci and ref['revision'] is None
                elif ref['source'] == 'VAR':
                    ok = ok and pid == row['variant'] and pid in variant_ids and ref['revision'] is None
                elif ref['source'] == 'BIND':
                    ok = ok and any(x['scenario'] == 'BASE_' + row['variant'][0]
                                    and x['parameter_id'] == pid and x['revision'] == ref['revision'] for x in bindings)
                else:
                    ok = ok and ref['revision'] is None
                check('reference:' + label + ':' + ref['source'] + ':' + str(pid), ok, ref)
            for dependency in row['symbolic_dependency_refs']:
                check('formula_conditions:' + label + ':' + dependency,
                      dependency in formulas and bool(formulas[dependency]['conditions'])
                      and bool(formulas[dependency]['missing']), dependency)
            for raw_id in row['source_raw_ids']:
                check('source_RAW:' + label + ':' + raw_id,
                      scoped[raw_id]['lifecycle'] == 'RAW' and scoped[raw_id]['value'] is None,
                      'Existing RAW only; no maturity/value update')
                consumed_raw.add(raw_id)
            consumed_bindings.update(('BASE_' + row['variant'][0], f) for f in row['source_binding_fields'])
        check('all_44_bindings_referenced', consumed_bindings
              == {(x['scenario'], x['proposed_cad_field']) for x in bindings}, len(consumed_bindings))
        original_raw = {k for k, v in scoped.items() if k.startswith('R3F_') and v['lifecycle'] == 'RAW'}
        check('all_84_RAW_referenced', consumed_raw == original_raw and len(original_raw) == 84, len(consumed_raw))
        for name, formula in formulas.items():
            source = sources[formula['source']['source']]
            text = blob(source['commit'], source['path']).decode()
            check('formula_is_source_quote:' + name, formula['expression'] in text
                  and ('companion_expression' not in formula or formula['companion_expression'] in text),
                  formula['source'])
        source_states = json.loads((ROOT / sources['STATE']['path']).read_text())
        mapped = read('state_dependencies.json')['rows']
        check('42_source_states_exact', len(mapped) == 42
              and [r['source_state'] for r in mapped] == source_states, 'All source fields/ordering preserved')
        for row in mapped:
            key = row['source_state']['variant'] + '/' + row['source_state']['state']
            check('state_not_solved:' + key,
                  row['actual_solution'] == 'NOT_RUN'
                  and row['actual_force'] is row['actual_moment'] is row['actual_capacity_margin'] is None
                  and set(row['interface_row_keys']) <= row_keys
                  and all(x.startswith(row['source_state']['variant'] + '/') for x in row['interface_row_keys'])
                  and bool(row['contact_and_load_requirement']), row['source_state']['source_reference'])
        index = read('unknown_index.json')
        check('unknown_index_is_source_only', len(index) == 84
              and {x['source']['source_id'] for x in index} == original_raw
              and all(x['value'] is None and x['source_lifecycle'] == 'RAW'
                      and x['interface_rows'] for x in index), 'Index is not a new registry')
    except Exception as exc:
        check('exception', False, str(exc))
    counts = dict(Counter(c['status'] for c in checks))
    args.output.write_text(json.dumps({'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Documentary traceability/coverage only; not independent R5 or engineering verification',
        'checked_file_sha256': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
            for name in ('source_catalog.json', 'interfaces.json', 'interfaces.md',
                         'symbolic_dependencies.json', 'state_dependencies.json',
                         'state_dependencies.md', 'unknown_index.json', 'verify_symbolic.py')},
        'counts': counts, 'checks': checks, 'physics_geometry_calculations': 'NOT_RUN'},
        ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(counts))
    return int(counts.get('FAIL', 0) != 0)


if __name__ == '__main__':
    raise SystemExit(main())
