"""R1 routing and preservation checks; does not close OBS-01 or impersonate R5."""
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import copy
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = 'f731910273b47f46c6d45114cecd76de6fa8adf9'
OLD = 'b840dfd5444da2bf62483b7f4a6069d2bb255b71'
C = 'beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe'
H = '47db9013c3cf3756987cdb480850cc0487c59b1e'
R1 = 'aaaaf5285b8066722e81cf0127d5a2572369d068'
R5 = '4aa23509b45efc2c2c166935102ca5caa76f55e2'
COMMON = '9433ef749df14a3bbf8ea32331e2f895fd5bf7aa'
OWNER = '6afb4750-7918-8191-8569-77b5b0c41050'
P = 'verification/r4_force_geometry/symbolic_20261116/'
FIX = 'verification/r4_force_geometry/obs01_correction/'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


@lru_cache(None)
def blob(commit, path):
    return git('show', commit + ':' + path)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    checks = []

    def check(name, ok, evidence):
        checks.append(dict(id=name, status='PASS' if ok else 'FAIL', evidence=evidence))
        if not ok:
            raise AssertionError(name)

    def js(path, commit=None):
        return json.loads(blob(commit, path) if commit else (ROOT / path).read_bytes())

    check('main', git('rev-parse', 'origin/main').decode().strip() == BASE, BASE)
    check('claim_accepted_ancestry', git('merge-base', BASE,
          'cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9').decode().strip()
          == 'cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9', 'Accepted PR49')
    check('C_parent', git('rev-parse', C + '^').decode().strip() == COMMON, COMMON)
    check('H_parent', git('rev-parse', H + '^').decode().strip() == C, C)
    check('H_scope', set(git('diff', '--name-only', C, H).decode().splitlines()) == {
          'STATE.md', 'NEXT_MODEL.md', 'handoffs/T-r4-force-geometry-01/' + OWNER + '.md',
          FIX + 'ci_C.json', FIX + 'ci_C_test_summary.txt', FIX + 'recheck_request.json',
          FIX + 'recheck_request.md'}, 'H adds metadata, request and C CI receipt')
    request = js(FIX + 'recheck_request.json')
    check('exact_request_OPEN', request['target_C'] == C and request['original_R4_C'] == OLD
          and request['original_review_C'] == R5 and request['reviewer_session'] is None
          and request['review_execution'] == 'NOT_RUN' and request['observation_status'] == 'OPEN',
          'Request is not completed independent review')
    check('excluded_authors', set(request['excluded_author_sessions']) == {
          OWNER, 'r1-pr48-integration-20261116'}, request['excluded_author_sessions'])
    claim = js('verification/r4_force_geometry/claim.json')
    for name, obj in [('current', claim), ('main', js('verification/r4_force_geometry/claim.json', BASE))]:
        check('owner_lease:' + name, obj['status'] == 'ACCEPTED_MAIN'
              and obj['owner_session'] == obj['session_id'] == OWNER
              and obj['lease_expires_at'] == obj['proposed_lease_expires_at'] == '2026-11-17T17:44:00Z',
              'Original owner/deadline preserved')
    now = datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(claim['lease_expires_at'].replace('Z', '+00:00'))
    check('lease_live_at_coordination', now < deadline, now.isoformat())
    for event in ('heartbeat_start.json', 'heartbeat_end.json', 'heartbeat_precommit.json'):
        obj = js(FIX + event)
        check('author_event:' + event, datetime.fromisoformat(obj['recorded_at_utc']) < deadline
              and obj['lease_expires_at'] == claim['lease_expires_at'] and not obj['lease_extended'],
              obj['recorded_at_utc'])
    old = js(P + 'interfaces.json', OLD); new = js(P + 'interfaces.json', C)
    expected = copy.deepcopy(old); removed = []
    for row in expected['rows']:
        if row['row_key'].endswith('/datum_motion'):
            foreign = 'CI-X_B_GATHER' if row['variant'].startswith('A') else 'CI-X_COLUMN_GATHER'
            own = 'CI-X_COLUMN_GATHER' if row['variant'].startswith('A') else 'CI-X_B_GATHER'
            before = row['source_references']
            after = [r for r in before if not (r['source'] == 'CI' and r['source_id'] == foreign)]
            check('one_removal:' + row['row_key'], len(before) - len(after) == 1
                  and any(r['source'] == 'CI' and r['source_id'] == own for r in after),
                  {'remove': foreign, 'retain': own})
            row['source_references'] = after; removed.append(row['row_key'])
    check('exact_document_delta', new == expected and len(removed) == 4,
          'Whole JSON equals original with exactly four selected references removed')
    check('52_rows', len(new['rows']) == 52 and Counter(r['variant'] for r in new['rows'])
          == {'A-V1': 13, 'A-V2': 13, 'B-V1': 13, 'B-V2': 13}, 'Cardinality preserved')
    for name in ('source_catalog.json', 'symbolic_dependencies.json', 'state_dependencies.json',
                 'state_dependencies.md', 'unknown_index.json'):
        check('unchanged_output:' + name, blob(C, P + name) == blob(OLD, P + name), sha(blob(C, P + name)))
    for item in js(FIX + 'archive_manifest.json'):
        check('archive:' + item['path'], (ROOT / item['archive_path']).read_bytes()
              == blob(OLD, item['path']) and sha(blob(OLD, item['path'])) == item['sha256'], item['archive_path'])
    for item in js(FIX + 'validation.json')['file_sha256']:
        check('author_manifest:' + item['path'], sha(blob(C, item['path'])) == item['sha256'], item['sha256'])
    for folder, source in [('verification/r4_force_geometry', H),
                           ('verification/r5_r4_force_geometry_symbolic_review', R5),
                           ('verification/r1_r5_symbolic_observation', R1)]:
        files = git('ls-tree', '-r', '--name-only', source, folder).decode().splitlines()
        check('frozen_package:' + folder, bool(files) and all((ROOT / p).read_bytes() == blob(source, p)
              for p in files), len(files))
    journal = 'reviews/cross_check_log.md'
    old_journal = blob(R5, journal); base_journal = blob(BASE, journal)
    original_record = old_journal[len(base_journal):]
    normalized = base_journal + original_record.replace(b'validity: CURRENT\n', b'validity: STALE\n', 1)
    check('original_review_archived', old_journal.startswith(base_journal)
          and (HERE / 'original_review_record.md').read_bytes() == original_record,
          'Exact historical record and four FAIL retained')
    check('review_staleness_only', original_record.count(b'validity: CURRENT\n') == 1
          and (ROOT / journal).read_bytes() == normalized,
          'Only CURRENT -> STALE, required by changed reviewed artifacts; verdict/checks/finding unchanged')
    report = js('verification/r5_r4_force_geometry_symbolic_review/independent_after_record.json')
    check('historical_four_FAIL', report['target_C'] == OLD
          and dict(Counter(x['result'] for x in report['checks'])) == report['counts'] == {'PASS': 2422, 'FAIL': 4},
          'Historical failures retained; no review of new C declared')
    manifest = js('verification/r4_force_geometry/input_manifest.json')
    check('manifest_54_12', len(manifest['inputs']) == 54 and len(manifest['protected_trees']) == 12,
          'Pinned source manifest')
    for item in manifest['inputs']:
        raw = blob(item['commit'], item['path'])
        check('input:' + item['path'], sha(raw) == item['sha256']
              and blob(C, item['path']) == raw and (ROOT / item['path']).read_bytes() == raw, item['sha256'])
    protected = []
    for path, tree in manifest['protected_trees'].items():
        check('source_tree:' + path, git('rev-parse', C + ':' + path).decode().strip() == tree,
              'Exact tree on R4 target, before R5 journal append in coordinator branch')
        for p in git('ls-tree', '-r', '--name-only', C, path).decode().splitlines():
            raw = blob(C, p); current = (ROOT / p).read_bytes()
            if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                okay = sha(current) == re.search(rb'oid sha256:([a-f0-9]{64})', raw).group(1).decode()
            else:
                okay = current == raw if p != journal else current == normalized and current.startswith(raw)
            check('protected:' + p, okay, sha(current)); protected.append(p)
    states = js(P + 'state_dependencies.json')['rows']
    check('42_unsolved_states', len(states) == 42 and [r['source_state'] for r in states]
          == js('verification/r3_force_path/analysis/state_matrix.json')
          and all(r['actual_solution'] == 'NOT_RUN' and r['actual_force'] is None
                  and r['actual_moment'] is None and r['actual_capacity_margin'] is None for r in states),
          'Source states preserved, no physical solution')
    unknowns = js(P + 'unknown_index.json')
    check('84_RAW_null', len(unknowns) == 84 and all(x['value'] is None
          and x['source_lifecycle'] == 'RAW' for x in unknowns), 'No parameter promotion')
    check('44_bindings', len(js('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows']) == 44,
          'Full pinned bytes checked above')
    check('audit_456_NOT_RUN', all(x['status'] == 'NOT_RUN' for x in
          js('verification/r4_force_geometry/input_audit.json')['items'] if x['section'] in (4, 5, 6)), 'Physical audit incomplete')
    for path in ('STATE.md', 'NEXT_MODEL.md', 'ISSUES_AND_TASKS.md'):
        common = blob(COMMON, path); ours = blob(R1, path); theirs = blob(H, path)
        check('history:' + path, ours.endswith(common) and theirs.endswith(common)
              and (ROOT / path).read_bytes().endswith(theirs[:-len(common)] + ours),
              'Both source prefixes, one exact common history')
    author = json.loads((HERE / 'author_checker_replay.json').read_text())
    render = json.loads((HERE / 'renderer_replay.json').read_text())
    check('author_reproduction', author['counts'] == {'PASS': 1341}, 'Supplemental R1 reproduction, not independent R5')
    check('renderer_reproduction', len(render['files']) == 7 and all(x['MATCH'] for x in render['files'])
          and not render['author_files_overwritten'], 'Outputs only in temporary directory')
    result = dict(checked_at_utc=now.isoformat(), target_C=C, request_H=H, checks=checks,
                  counts={'PASS': len(checks), 'FAIL': 0}, protected_materialized_files=len(protected),
                  observation='R5-SYM-OBS-01 OPEN', independent_recheck='NOT_RUN',
                  R4_session_preflight_replayed=False, R5_session_impersonated=False,
                  numerical_physical_work='NOT_RUN', main_merge=False)
    (HERE / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('counts', 'protected_materialized_files', 'observation', 'independent_recheck')}))


if __name__ == '__main__':
    main()
