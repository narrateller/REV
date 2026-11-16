"""R1 integration preparation: immutable reviews and source preservation only."""
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import copy
import hashlib
import json
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = 'f731910273b47f46c6d45114cecd76de6fa8adf9'
C4 = 'beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe'
H4 = '47db9013c3cf3756987cdb480850cc0487c59b1e'
OLD = 'b840dfd5444da2bf62483b7f4a6069d2bb255b71'
C5 = '3784efa32ca26547f2581101474d6188f000c348'
H5 = 'fe156cb3fbbb11d86a2716db9adcc7f44057a042'
COORD = '1d5e2a8ed3c9be340897d6485c7a4383edf62152'
OWNER = '6afb4750-7918-8191-8569-77b5b0c41050'
REVIEWER = '6afb0a73-b16c-8191-a539-9a6685e89034'
P4 = 'verification/r4_force_geometry/symbolic_20261116/'
P5 = 'verification/r5_r4_symbolic_obs01_recheck/'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


@lru_cache(None)
def blob(commit, path):
    return git('show', commit + ':' + path)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    checks = []

    def check(name, okay, evidence):
        checks.append(dict(id=name, status='PASS' if okay else 'FAIL', evidence=evidence))
        if not okay:
            raise AssertionError(name)

    def js(path, commit=None):
        return json.loads(blob(commit, path) if commit else (ROOT / path).read_bytes())

    check('main_exact', git('rev-parse', 'origin/main').decode().strip() == BASE, BASE)
    for commit in (BASE, C4, H4, COORD, '4aa23509b45efc2c2c166935102ca5caa76f55e2',
                   '93b4aead4983f88919d8e8b4165e29d7f3246600', 'db6b9774649f99ad1b157cba2a9c7cdeec570302'):
        check('ancestry:' + commit, git('merge-base', commit, H5).decode().strip() == commit, H5)
    check('R5_H_child', git('rev-parse', H5 + '^').decode().strip() == C5, C5)
    check('R5_H_scope', set(git('diff', '--name-only', C5, H5).decode().splitlines()) == {
          'STATE.md', 'NEXT_MODEL.md', 'handoffs/T-r5-r4-symbolic-obs01-recheck-01/' + REVIEWER + '.md'},
          'H changes handoff metadata only')
    ident = js(P5 + 'identity.json')
    check('identity_disclosure', ident['actual_session_id'] == REVIEWER
          and ident['target_C'] == C4 and not ident['target_coauthor'] and not ident['correction_coauthor']
          and REVIEWER not in ident['excluded_authors']
          and 'db6b9774649f99ad1b157cba2a9c7cdeec570302' in ident['upstream_authorship_disclosure'],
          'Reported target independence retained; upstream self-authorship disclosed')
    evidence = js(P5 + 'independent_final.json')
    check('independent_388', evidence['target_C'] == C4 and evidence['request_H'] == H4
          and {k: sum(x['result'] == k for x in evidence['checks']) for k in ('PASS', 'FAIL')}
          == evidence['counts'] == {'PASS': 388, 'FAIL': 0}, 'Recorded independent act, not a new R1 review')
    check('four_row_results', {x['row_key'] for x in evidence['row_results']}
          == {v + '/datum_motion' for v in ('A-V1', 'A-V2', 'B-V1', 'B-V2')}
          and all(x['result'] == 'PASS' for x in evidence['row_results']), evidence['row_results'])
    check('limited_closure', evidence['OBS01'] == 'CLOSED_DOCUMENTARY_EXACT_C'
          and evidence['input_audit_456'] == 'NOT_RUN' and evidence['G1'] == 'OPEN'
          and evidence['physical_READY'] == 'NO_GO', 'No physical gate closure')
    for item in js(P5 + 'validation.json')['package_hashes']:
        check('R5_manifest:' + item['path'], sha(blob(C5, item['path'])) == item['sha256']
              and (ROOT / item['path']).read_bytes() == blob(C5, item['path']), item['sha256'])
    for folder, source in [('verification/r4_force_geometry', H4),
                           (P5.rstrip('/'), C5),
                           ('verification/r5_r4_force_geometry_symbolic_review',
                            '4aa23509b45efc2c2c166935102ca5caa76f55e2')]:
        paths = git('ls-tree', '-r', '--name-only', source, folder).decode().splitlines()
        check('frozen_package:' + folder, bool(paths) and all((ROOT / p).read_bytes() == blob(source, p)
              for p in paths), len(paths))
    claim = js('verification/r4_force_geometry/claim.json')
    for name, c in [('current', claim), ('main', js('verification/r4_force_geometry/claim.json', BASE))]:
        check('claim:' + name, c['status'] == 'ACCEPTED_MAIN' and c['owner_session'] == c['session_id'] == OWNER
              and c['lease_expires_at'] == c['proposed_lease_expires_at'] == '2026-11-17T17:44:00Z',
              'Original accepted owner and deadline, no extension')
    now = datetime.now(timezone.utc)
    check('live_lease_at_preparation', now < datetime.fromisoformat(claim['lease_expires_at'].replace('Z', '+00:00')),
          now.isoformat())
    check('claim_no_R1_heartbeat', (ROOT / 'verification/r4_force_geometry/claim.json').read_bytes()
          == blob(C4, 'verification/r4_force_geometry/claim.json'), claim['heartbeat_utc'])
    expected = copy.deepcopy(js(P4 + 'interfaces.json', OLD)); count = 0
    for row in expected['rows']:
        if row['row_key'].endswith('/datum_motion'):
            foreign = 'CI-X_B_GATHER' if row['variant'].startswith('A') else 'CI-X_COLUMN_GATHER'
            before = row['source_references']
            row['source_references'] = [x for x in before if not (x['source'] == 'CI' and x['source_id'] == foreign)]
            check('exact_one_removal:' + row['row_key'], len(before) - len(row['source_references']) == 1, foreign)
            count += 1
    check('whole_document_delta', js(P4 + 'interfaces.json') == expected and count == 4,
          'Four selected removals only; all other JSON fields and 48 rows preserved')
    check('52_rows', len(expected['rows']) == 52 and Counter(x['variant'] for x in expected['rows'])
          == {'A-V1': 13, 'A-V2': 13, 'B-V1': 13, 'B-V2': 13}, 'Documentary coverage only')
    journal = 'reviews/cross_check_log.md'; current = (ROOT / journal).read_bytes()
    check('review_history_exact', current == blob(C5, journal) and current.startswith(blob(COORD, journal)),
          'New independent act appended to intact normalized old history')
    records = [yaml.safe_load(x) for x in re.findall(r'^```yaml\s*\n(.*?)^```\s*$', current.decode(), re.M | re.S)]
    records = {x['review_id']: x for x in records if isinstance(x, dict) and x.get('record_type') == 'review'}
    old = records['REV-R5-R4-FORCE-GEOMETRY-SYMBOLIC-OUTPUT-01-001']
    new = records['REV-R5-R4-SYM-OBS01-RECHECK-01-001']
    check('old_STALE_untouched', old['validity'] == 'STALE' and old['verdict'] == 'WARNING'
          and old['findings'][0]['status'] == 'OPEN' and any(x['result'] == 'FAIL' for x in old['checks']),
          'Historical failure record and original verbatim archive retained')
    check('new_CURRENT_scope', new['validity'] == 'CURRENT' and new['reviewed_commit'] == C4
          and new['OBS01_status'] == 'CLOSED' and new['OBS01_verdict'] == 'PASS_DOCUMENTARY_EXACT_C'
          and new['verdict'] == 'WARNING' and new['source_states_solved'] is False
          and all(v == 'NOT_RUN' for v in new['input_audit_sections'].values()),
          'Closed observation, not full engineering acceptance')
    for item in new['artifacts']:
        check('reviewed_artifact:' + item['path'], sha(blob(C4, item['path'])) == item['sha256']
              and (ROOT / item['path']).read_bytes() == blob(C4, item['path']), item['sha256'])
    manifest = js('verification/r4_force_geometry/input_manifest.json')
    check('54_inputs_12_trees', len(manifest['inputs']) == 54 and len(manifest['protected_trees']) == 12,
          'Pinned original source identities')
    for item in manifest['inputs']:
        raw = blob(item['commit'], item['path'])
        check('pinned:' + item['path'], sha(raw) == item['sha256'] and (ROOT / item['path']).read_bytes() == raw
              and blob(BASE, item['path']) == raw, item['sha256'])
    protected = []
    for p, tree in manifest['protected_trees'].items():
        check('source_tree:' + p, git('rev-parse', C4 + ':' + p).decode().strip() == tree, tree)
        for f in git('ls-tree', '-r', '--name-only', C4, p).decode().splitlines():
            raw = blob(C4, f); cur = (ROOT / f).read_bytes()
            if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                okay = sha(cur) == re.search(rb'oid sha256:([a-f0-9]{64})', raw).group(1).decode()
            elif f == journal:
                okay = cur == blob(C5, f) and cur.startswith(raw)
            else:
                okay = cur == raw
            check('protected:' + f, okay, sha(cur)); protected.append(f)
    states = js(P4 + 'state_dependencies.json')['rows']
    check('42_unsolved_states', len(states) == 42 and [x['source_state'] for x in states]
          == js('verification/r3_force_path/analysis/state_matrix.json')
          and all(x['actual_solution'] == 'NOT_RUN' and x['actual_force'] is None
                  and x['actual_moment'] is None and x['actual_capacity_margin'] is None for x in states),
          'Full source objects, not solved states')
    unknowns = js(P4 + 'unknown_index.json')
    check('84_RAW_null', len(unknowns) == 84 and all(x['value'] is None and x['source_lifecycle'] == 'RAW'
          for x in unknowns), 'Unknown physical data remain unknown')
    check('44_full_bindings', len(js('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows']) == 44,
          'Whole file bytes checked by pinned source manifest')
    for p in ('STATE.md', 'NEXT_MODEL.md', 'ISSUES_AND_TASKS.md',
              'handoffs/T-r4-force-geometry-01/r1-pr48-integration-20261116.md'):
        cur = (ROOT / p).read_bytes(); old = blob(H5, p)
        check('summary_history:' + p, cur.endswith(old), 'Old source body unchanged')
        prefix = cur[:-len(old)]
        check('new_summary_no_parameter_refs:' + p,
              not re.search(rb'\[([A-Z][A-Z0-9_-]*)@(\d+)\]', prefix), 'Exact C substitution is metadata only')
    result = dict(checked_at_utc=now.isoformat(), main=BASE, reviewed_R4_C=C4, R5_C=C5, R5_H=H5,
                  checks=checks, counts={'PASS': len(checks), 'FAIL': 0}, protected_materialized_files=len(protected),
                  OBS01='CLOSED_DOCUMENTARY_EXACT_C', overall_scope='WARNING_DOCUMENTARY_SYMBOLIC_ONLY',
                  new_independent_R1_review=False, R4_claim_changed=False, physical_numerical_work='NOT_RUN',
                  main_merge=False)
    (HERE / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('counts', 'protected_materialized_files', 'OBS01', 'overall_scope')}))


if __name__ == '__main__':
    main()
