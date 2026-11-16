"""Conditional force-path arithmetic; never selects geometry or authorizes motion."""
from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import json
import math
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from repo_support import engineering_sha, flatten, parameter_ref  # noqa: E402

HERE = Path(__file__).resolve().parent
REL = HERE.relative_to(ROOT).as_posix()
SCRIPT = REL + '/compare.py'
SNAPSHOT = REL + '/params/registry.yaml'
SESSION = 'r3-force-path-20261114'
SCOPE = 'REV_R3_FORCE_PATH_CONDITIONAL_ARITHMETIC_ONLY'
FIELDS = {
    'chamber.width', 'chamber.height', 'product.length', 'chamber.length',
    'material.occupied_length', 'stroke.approach', 'stroke.work', 'stroke.eject',
    'stroke.return', 'cylinder.bore_min', 'cylinder.rod_diameter',
    'load.work_peak', 'load.return_required', 'time.cycle_budget',
    *(f'phase.{p}.{v}' for p in ('approach', 'work', 'eject', 'return')
      for v in ('time', 'speed')),
}
USED = ('chamber.width', 'chamber.height', 'cylinder.rod_diameter',
        'load.work_peak', 'load.return_required')
METRICS = (
    ('ROD_AREA', 'm2', 'pi*d^2/4'),
    ('ROD_WORK_STRESS', 'Pa', '-F_work/(pi*d^2/4)'),
    ('ROD_RETURN_STRESS', 'Pa', 'F_return/(pi*d^2/4)'),
    ('PUNCH_MEAN_WORK_PRESSURE', 'Pa', 'F_work/(width*height)'),
    ('IDEAL_WORK_N', 'N', '-F_work; compression, ideal serial chain only'),
    ('IDEAL_RETURN_N', 'N', 'F_return; tension, captured ideal serial chain only'),
    ('WORK_MZ_PER_E', 'N', '-F_work; Mz/e_y, cylinder applied couple'),
    ('RETURN_MZ_PER_E', 'N', 'F_return; Mz/e_y, cylinder applied couple'),
    ('WORK_R0_PER_E_OVER_A', 'N', '-F_work; ideal guide couple reaction'),
    ('WORK_R1_PER_E_OVER_A', 'N', 'F_work; ideal guide couple reaction'),
    ('RETURN_R0_PER_E_OVER_A', 'N', 'F_return; ideal guide couple reaction'),
    ('RETURN_R1_PER_E_OVER_A', 'N', '-F_return; ideal guide couple reaction'),
    ('EULER_BOUNDARY_COEFF', 'N', 'F_work/pi^2; EI/L_eff^2 at ideal eigenvalue equality, not allowable'),
)
GAPS = {
    'E_Y': ('m', 'Actual line-of-action offset, including V1 misalignment, is UNKNOWN'),
    'E_Z': ('m', 'Out-of-plane misalignment and its My component are UNKNOWN'),
    'GUIDE_SPAN': ('m', 'Guide coordinates and spacing are UNKNOWN'),
    'CARRIER_AREA': ('m2', 'Separate carrier section is UNKNOWN; hydraulic rod is not carrier'),
    'CARRIER_I': ('m4', 'Carrier section/axis second moment is UNKNOWN'),
    'CARRIER_W': ('m3', 'Carrier bending section modulus is UNKNOWN'),
    'CARRIER_J': ('m4', 'Carrier/portal torsion section properties are UNKNOWN'),
    'ELASTIC_MODULUS': ('Pa', 'Material and elastic modulus are UNKNOWN'),
    'CARRIER_FREE_LENGTH_MAX': ('m', 'L_free(q), guides and worst pose are UNKNOWN'),
    'ROD_FREE_LENGTH_MAX': ('m', 'Rod supports and exposed length over full travel are UNKNOWN'),
    'END_FACTOR': ('1', 'Effective restraint / Euler applicability is UNKNOWN'),
    'ALLOWABLE_STRESS': ('Pa', 'Applicable strength/fatigue criteria and factors are UNKNOWN'),
    'JOINT_RESISTANCE': ('N', 'Joint geometry/material/preload/contact and bilateral rating are UNKNOWN'),
    'JOINT_MOMENT_RESISTANCE': ('N*m', 'Local joint bending/torsion axes and resistance are UNKNOWN'),
    'SUPPORT_RESISTANCE': ('N', 'Cylinder/guide/reaction supports and local frame resistance are UNKNOWN'),
    'FRAME_STIFFNESS': ('N/m', 'Frame compliance and support compatibility are UNKNOWN'),
    'GUIDE_PRELOAD': ('N', 'Guide preload/clearance/contact distribution are UNKNOWN'),
    'FRICTION_FORCE': ('N', 'Guide and new connection friction are UNKNOWN, not zero'),
    'MOVING_MASS': ('kg', 'New carrier/portal mass and inertia are UNKNOWN'),
    'ACCELERATION': ('m/s2', 'Transient motion and emergency deceleration are UNKNOWN'),
    'REACTION_AVAILABLE': ('N', 'A startup/retention or B closed/unload/open reaction is UNKNOWN'),
}
STATES = {
    'A': ('startup_empty', 'gather_partial', 'approach', 'work_peak',
          'hold_unload', 'eject', 'return_full', 'refill', 'ready', 'jam_emergency'),
    'B': ('gather_partial', 'approach', 'work_peak_closed', 'hold_unload',
          'unlock', 'stop_open', 'eject_open', 'return_full_open',
          'close_relock_reset', 'ready', 'jam_emergency'),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def number(value, name, *, positive=False, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{name}: finite non-bool SI number required')
    if (positive and value <= 0) or (nonnegative and value < 0):
        raise ValueError(f'{name}: outside domain')
    return value


def eccentric_transfer(force_x, offset_y, span):
    """Only the isolated applied moment and ideal two-guide couple component.

    Force acts at (0,e,0), guides at x=0,a. Other transverse loads, preload,
    compliance and contact changes are excluded, not asserted absent on REV.
    Unknown e/a never becomes a centered or infinitely stiff actual support.
    """
    number(force_x, 'force_x')
    if offset_y is not None:
        number(offset_y, 'offset_y')
    if span is not None:
        number(span, 'span', positive=True)
    moment = None if offset_y is None else -force_x * offset_y
    r1 = None if moment is None or span is None else -moment / span
    return {'applied_Mz_Nm': moment,
            'guide_R0_N': None if r1 is None else -r1, 'guide_R1_N': r1}


def euler_capacity(elastic_modulus, second_moment, end_factor, free_length):
    args = (elastic_modulus, second_moment, end_factor, free_length)
    for key, value in zip(('E', 'I', 'K', 'L'), args):
        if value is not None:
            number(value, key, positive=True)
    if any(x is None for x in args):
        return None
    return math.pi ** 2 * elastic_modulus * second_moment / (end_factor * free_length) ** 2


def nominal_stress(axial_force, area):
    number(axial_force, 'axial_force')
    if area is None:
        return None
    return axial_force / number(area, 'area', positive=True)


def coefficients(values):
    for key in USED:
        number(values[key], key, positive=True)
    d = values['cylinder.rod_diameter']
    work, back = values['load.work_peak'], values['load.return_required']
    area = math.pi * d * d / 4
    vals = (area, nominal_stress(-work, area), nominal_stress(back, area),
            work / (values['chamber.width'] * values['chamber.height']),
            -work, back, -work, back, -work, work, back, -back,
            work / math.pi ** 2)
    return {name: {'value': number(value, name), 'unit': unit, 'expression': expr}
            for (name, unit, expr), value in zip(METRICS, vals)}


def validate_bindings(rows, params):
    if len(rows) != 44:
        raise ValueError('Exactly 44 source binding rows required')
    result = {}
    for scenario in ('BASE_A', 'BASE_B'):
        selected = [r for r in rows if r['scenario'] == scenario]
        if len(selected) != 22 or {r['proposed_cad_field'] for r in selected} != FIELDS:
            raise ValueError('Missing, duplicate or foreign binding field')
        result[scenario] = {}
        for row in selected:
            p = params[row['parameter_id']]
            if row['mode'] != 'fixed-budget' or row['validity'] != 'CURRENT':
                raise ValueError('Only CURRENT fixed-budget bindings allowed')
            if any(row[k] != p[k] for k in ('value', 'unit', 'revision', 'lifecycle', 'validity')):
                raise ValueError('Source value/unit/revision/status changed')
            if row['engineering_sha256'] != engineering_sha(p):
                raise ValueError('Source engineering definition changed')
            expected = ('N' if row['proposed_cad_field'].startswith('load.') else
                        'm/s' if row['proposed_cad_field'].endswith('.speed') else
                        's' if row['proposed_cad_field'].endswith('.time') or row['proposed_cad_field'] == 'time.cycle_budget'
                        else 'm')
            if row['unit'] != expected:
                raise ValueError('Binding dimension mismatch')
            number(row['value'], row['parameter_id'], positive=True)
            result[scenario][row['proposed_cad_field']] = row
    return result


def parameter(value, unit, meaning, dependencies, calculation=None, reason=None):
    state = 'RAW' if value is None else 'CALCULATED'
    return dict(revision=1, name=meaning, value=value, unit=unit, tolerance=None,
                uncertainty=None, unknown_reason=reason, lifecycle=state, validity='CURRENT',
                stale_reason=None, scope=SCOPE, meaning=meaning,
                provenance={'kind': 'CONDITIONAL_ANALYTICAL_CASE',
                            'source_ref': REL + '/input_audit.md', 'locator': meaning},
                author={'role': 'R3', 'session_id': SESSION}, author_sessions=[SESSION],
                verifier=None, depends_on=dependencies, calculation=calculation,
                evidence=[REL + '/input_audit.md'] + ([] if calculation is None else [calculation['output']]),
                baseline_id=None, history=[{'revision': 1, 'from': None, 'to': state,
                                           'actor': SESSION, 'reason': 'PR47 accepted; conditional case, not active project promotion'}])


def load_inputs():
    data = yaml.safe_load((ROOT / 'params/registry.yaml').read_text())
    preflight = json.loads((HERE / 'preflight.json').read_text())
    for item in preflight['inputs']:
        if digest((ROOT / item['path']).read_bytes()) != item['sha256']:
            raise ValueError('Pinned input changed: ' + item['path'])
    bindings = json.loads((ROOT / 'verification/r4_cycle_interfaces/proposal/baseline_bindings.json').read_text())
    variants = json.loads((ROOT / 'verification/r4_cycle_interfaces/proposal/force_variants.json').read_text())['variants']
    if {v['id'] for v in variants} != {'A-V1', 'A-V2', 'B-V1', 'B-V2'} or len(variants) != 4:
        raise ValueError('Four exact original force variants required')
    for source in {r['source'] for r in bindings['rows']}:
        saved = json.loads((ROOT / source).read_text())
        refs = {x['id']: x for x in saved['inputs'] + saved['outputs']}
        for row in bindings['rows']:
            if row['source'] == source:
                ref = refs[row['parameter_id']]
                if any(ref[k] != row[k] for k in ('value', 'unit', 'revision', 'engineering_sha256')):
                    raise ValueError('Binding differs from original calculation manifest')
    return data, bindings, variants


def payload():
    source_data, bindings, variants = load_inputs()
    original = flatten(source_data)
    selected = validate_bindings(bindings['rows'], original)
    registry = copy.deepcopy(source_data)
    # Standalone calculation snapshot with unchanged original definitions.
    # Never write the active params/registry.yaml.
    added = registry['domains'].setdefault('force_path_conditional_case', {})
    if added:
        raise ValueError('Conditional output namespace already occupied')
    per_scenario = {}
    for scenario, rows in selected.items():
        letter = scenario[-1]
        inputs = [dict(parameter_ref(rows[k]['parameter_id'], original[rows[k]['parameter_id']]),
                       value=rows[k]['value'], unit=rows[k]['unit']) for k in USED]
        metrics = coefficients({k: r['value'] for k, r in rows.items()})
        per_scenario[letter] = (inputs, metrics)
        for name, item in metrics.items():
            key = f'R3F_{letter}_{name}'
            calc = dict(script=SCRIPT, command='.venv/bin/python ' + SCRIPT,
                        expression=item['expression'], code_files=[SCRIPT, 'scripts/repo_support.py'],
                        output=f'{REL}/results_{letter}.json')
            added[key] = parameter(item['value'], item['unit'],
                                   letter + ': ' + name + '; ideal conditional coefficient only',
                                   [{k: v for k, v in r.items() if k not in ('value', 'unit')} for r in inputs], calc)
    for variant in variants:
        prefix = 'R3F_' + variant['id'].replace('-', '_') + '_'
        for name, (unit, reason) in GAPS.items():
            added[prefix + name] = parameter(None, unit, variant['id'] + ': ' + name, [], reason=reason)
    registry_bytes = yaml.safe_dump(registry, allow_unicode=True, sort_keys=False, width=110).encode()
    files = {SNAPSHOT: registry_bytes}
    input_bytes = (json.dumps(bindings, ensure_ascii=False, indent=2) + '\n').encode()
    files[REL + '/baseline_snapshot.json'] = input_bytes
    codes = [{'path': x, 'sha256': digest((ROOT / x).read_bytes())}
             for x in (SCRIPT, 'scripts/repo_support.py')]
    case_rows = []
    for letter, (inputs, metrics) in per_scenario.items():
        outputs = [dict(parameter_ref(f'R3F_{letter}_{name}', added[f'R3F_{letter}_{name}']),
                        value=item['value'], unit=item['unit']) for name, item in metrics.items()]
        manifest = dict(schema_version='1.1', scope=SCOPE, inputs=inputs, outputs=outputs,
                        registry_snapshot=SNAPSHOT, registry_sha256=digest(registry_bytes),
                        script_sha256=codes[0]['sha256'], code_files=codes,
                        artifacts=[{'path': REL + '/baseline_snapshot.json', 'sha256': digest(input_bytes)},
                                   {'path': REL + '/input_audit.md', 'sha256': digest((HERE / 'input_audit.md').read_bytes())}],
                        environment={'python': sys.version.split()[0], 'pyyaml': yaml.__version__},
                        assumptions=['same single cylinder; no ratio change',
                                     'ideal quasi-static serial force component, no proof of zero real friction/inertia',
                                     'guide coefficients: isolated two-guide moment couple only',
                                     'rod stress: nominal solid circular section, no thread/notch/bending allowance'],
                        variants=[letter + '-V1', letter + '-V2'],
                        actual_results={'offset_m': None, 'moment_Nm': None, 'guide_reactions_N': None,
                                        'carrier_stress_Pa': None, 'rod_total_stress_Pa': None,
                                        'buckling_capacity_N': None, 'strength_margin': None,
                                        'new_drive_force_N': None, 'whole_cycle_feasibility': 'UNKNOWN'},
                        physical_feasibility='INDETERMINATE', architecture_selected=False, G1='OPEN')
        files[f'{REL}/results_{letter}.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    for variant in variants:
        letter = variant['variant']
        for state in STATES[letter]:
            reference = ('WORK_PEAK' if state.startswith('work_peak') else
                         'RETURN_REQUIRED' if state.startswith('return_full') else None)
            case_rows.append(dict(variant=variant['id'], scenario='BASE_' + letter,
                                  mode='fixed-budget', state=state, source_reference=reference,
                                  pose_domain='Full source travel and interior poses; L_free(q)/e(q)/contacts UNKNOWN',
                                  actual_force_N=None, actual_moment_Nm=None,
                                  actual_joint_support_loads=None, reaction_available='UNKNOWN',
                                  result='UNKNOWN', source_strokes_unchanged=True,
                                  note=('A empty startup needs an independent reaction; column cannot be presumed' if state == 'startup_empty' else
                                        'Open stop is not the closed pressing reaction; receiver/retention UNKNOWN' if state in ('stop_open', 'eject_open', 'return_full_open') else
                                        'Source work/return values are ideal load cases, not actual loads in every phase')))
    files[REL + '/state_matrix.json'] = (json.dumps(case_rows, ensure_ascii=False, indent=2) + '\n').encode()
    table = ['# Условная арифметика — автоматически из исходных bindings', '',
             'Новые ID относятся только к analysis/params/registry.yaml. Активный реестр неизменён.', '',
             '| Расчётный ID (revision 1) | Значение SI | Единица | Выражение / область |',
             '|---|---:|---|---|']
    for letter, (_, metrics) in per_scenario.items():
        for name, item in metrics.items():
            table.append(f"| `R3F_{letter}_{name}` | {item['value']:.12g} | {item['unit']} | {item['expression']} |")
    files[REL + '/calculated.md'] = ('\n'.join(table) + '\n').encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Write only new analysis outputs under accepted current claim')
    parser.add_argument('--validate-case', action='store_true', help='Run existing registry validator on the separate case snapshot')
    args = parser.parse_args()
    files = payload()
    if args.write:
        claim = json.loads((HERE.parent / 'claim.json').read_text())
        until = datetime.datetime.fromisoformat(claim['lease_expires_at'])
        if (claim['status'] != 'ACCEPTED_MAIN' or claim['owner_session'] != SESSION
                or datetime.datetime.now(datetime.timezone.utc) >= until):
            raise ValueError('Accepted current author claim required for writing')
        accepted = claim['claim_acceptance_commit']
        subprocess.run(['git', 'merge-base', '--is-ancestor', accepted, 'origin/main'], cwd=ROOT, check=True)
        for name, raw in files.items():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        print(f'WROTE {len(files)} conditional analysis files; active registry/CAD unchanged')
    else:
        for name, expected in files.items():
            if (ROOT / name).read_bytes() != expected:
                raise ValueError('Reproduction differs: ' + name)
        print(f'MATCH {len(files)} conditional artifacts; unknown physical inputs remain UNKNOWN')
    if args.validate_case:
        from check_registry import UniqueLoader, validate
        data = yaml.load((ROOT / SNAPSHOT).read_text(), Loader=UniqueLoader)
        errors = validate(data, ROOT, check_git=True)
        for error in errors:
            print('FAIL:', error)
        if errors:
            return 1
        print('PASS: scoped case registry consistency; no active project promotion or engineering acceptance')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
