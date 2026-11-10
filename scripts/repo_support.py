"""Shared provenance helpers; hashes establish consistency, not authorship."""
import hashlib
import json
import math
from pathlib import Path
import re
import yaml

DOMAINS = ('brochure_boundary', 'process_medium', 'kinematics_and_drive',
           'aero_thermo_fluid', 'geometry_mass', 'strength_safety_factors')
REF_RE = re.compile(r'\[([A-Z][A-Z0-9_-]*)@(\d+)\]')
ID_RE = re.compile(r'^[A-Z][A-Z0-9_-]*$')
SHA_RE = re.compile(r'^[a-f0-9]{64}$')
COMMIT_RE = re.compile(r'^(?:[a-f0-9]{40}|[a-f0-9]{64})$')
ENGINEERING_FIELDS = ('revision', 'value', 'unit', 'tolerance', 'uncertainty',
                      'scope', 'meaning', 'provenance', 'depends_on', 'calculation')


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def nonempty(x):
    return isinstance(x, str) and bool(x.strip())


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def engineering_sha(p):
    raw = json.dumps({k: p.get(k) for k in ENGINEERING_FIELDS}, sort_keys=True,
                     ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def flatten(data):
    result = {}
    for entries in data['domains'].values():
        for key, p in entries.items():
            if key in result:
                raise ValueError(f'Duplicate parameter: {key}')
            result[key] = p
    return result


def inside_file(root, name):
    if not nonempty(name) or Path(name).is_absolute():
        raise ValueError(f'Expected relative path: {name!r}')
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError(f'Missing or external file: {name}')
    with p.open('rb') as f:
        first_line = f.readline(128).rstrip(b'\r\n')
        if first_line == b'version https://git-lfs.github.com/spec/v1':
            raise ValueError(f'LFS object not materialized: {name}')
    return p


def parameter_ref(key, p):
    return {'id': key, 'revision': p['revision'], 'engineering_sha256': engineering_sha(p)}


def valid_tolerance(tol, nominal=None):
    if tol is None:
        return True
    if not isinstance(tol, dict):
        return False
    kind = tol.get('kind')
    if kind in ('absolute', 'relative_percent'):
        good = set(tol) == {'kind', 'minus', 'plus'} and all(
            finite(tol.get(k)) and tol[k] >= 0 for k in ('minus', 'plus'))
        return good and (kind != 'relative_percent' or (finite(nominal) and nominal != 0))
    if kind in ('min_only', 'max_only'):
        k = 'min' if kind == 'min_only' else 'max'
        return set(tol) == {'kind', k} and finite(tol.get(k))
    if kind == 'fit':
        return (set(tol) == {'kind', 'designation', 'standard_ref', 'nominal_ref', 'limits_refs'}
                and all(nonempty(tol.get(k)) for k in ('designation', 'standard_ref', 'nominal_ref'))
                and isinstance(tol.get('limits_refs'), list) and len(tol['limits_refs']) >= 2
                and all(nonempty(x) for x in tol['limits_refs']))
    return False
