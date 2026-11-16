"""Verify immutable review target and handoff facts; never an independent R5 review."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
C = 'b840dfd5444da2bf62483b7f4a6069d2bb255b71'
H = '9433ef749df14a3bbf8ea32331e2f895fd5bf7aa'
BASE = 'f731910273b47f46c6d45114cecd76de6fa8adf9'
OWNER = '6afb4750-7918-8191-8569-77b5b0c41050'
PREFIX = 'verification/r4_force_geometry/symbolic_20261116/'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    checks = []

    def check(name, ok, evidence):
        checks.append({'check': name, 'passed': bool(ok), 'evidence': evidence})
        if not ok:
            raise ValueError(name)

    def js(path):
        return json.loads((ROOT / path).read_text())

    check('main_exact', git('rev-parse', 'origin/main').decode().strip() == BASE, BASE)
    check('C_has_accepted_main', git('merge-base', C, BASE).decode().strip() == BASE, C)
    check('H_direct_child', git('show', '-s', '--format=%P', H).decode().strip() == C, H)
    paths = git('diff', '--name-only', C, H).decode().splitlines()
    check('H_scope', set(paths) == {'STATE.md', 'NEXT_MODEL.md',
          'handoffs/T-r4-force-geometry-01/' + OWNER + '.md',
          PREFIX + 'review_request.md', PREFIX + 'review_request.json'}, paths)
    request = js(PREFIX + 'review_request.json')
    check('review_target', request['target_C'] == C
          and request['reviewer_session'] is None and request['review_execution'] == 'NOT_RUN'
          and request['reviewer_claim_created'] is False, 'Request is not an assignment or completed review')
    check('reviewer_independence', set(request['excluded_author_sessions'])
          == {OWNER, 'r1-pr48-integration-20261116'} and request['author_sessions'] == [OWNER],
          request['excluded_author_sessions'])
    claim = js('verification/r4_force_geometry/claim.json')
    check('owner_and_deadline', claim['status'] == 'ACCEPTED_MAIN'
          and claim['owner_session'] == claim['session_id'] == OWNER
          and claim['lease_expires_at'] == claim['proposed_lease_expires_at'] == '2026-11-17T17:44:00Z'
          and datetime.now(timezone.utc) < datetime.fromisoformat(claim['lease_expires_at'].replace('Z', '+00:00')),
          'No claim takeover or renewal')
    document = js(PREFIX + 'interfaces.json')
    check('52_rows_four_variants', len(document['rows']) == 52
          and Counter(r['variant'] for r in document['rows'])
          == {'A-V1': 13, 'A-V2': 13, 'B-V1': 13, 'B-V2': 13}, 'Structural coverage, not semantic R5 acceptance')
    check('author_and_scope', document['author_sessions'] == [OWNER]
          and document['no_new_quantitative_assumptions'] is True, document['scope'])
    states = js(PREFIX + 'state_dependencies.json')['rows']
    original = js('verification/r3_force_path/analysis/state_matrix.json')
    check('42_source_states_exact', len(states) == 42
          and [r['source_state'] for r in states] == original
          and all(r['actual_solution'] == 'NOT_RUN' and r['actual_force'] is None
                  and r['actual_moment'] is None and r['actual_capacity_margin'] is None for r in states),
          'No solved states or numeric physical claims')
    unknowns = js(PREFIX + 'unknown_index.json')
    check('84_nulls', len(unknowns) == 84 and all(x['value'] is None
          and x['source_lifecycle'] == 'RAW' for x in unknowns), 'Source index, no registry promotion')
    audit = js('verification/r4_force_geometry/input_audit.json')
    check('audit_NOT_RUN_preserved', audit['counts']
          == {'PASS': 4, 'FAIL': 0, 'NOT_APPLICABLE': 0, 'NOT_RUN': 3}
          and audit['verdict'] == 'WARNING', 'No physical readiness inferred')
    v = js(PREFIX + 'validation.json')
    for item in v['file_sha256']:
        p = item['path']
        raw = git('show', C + ':' + p)
        current = (ROOT / p).read_bytes()
        preserved = current.endswith(raw) if p == 'ISSUES_AND_TASKS.md' else current == raw
        check('release_hash:' + p, hashlib.sha256(raw).hexdigest() == item['sha256']
              and preserved and git('show', H + ':' + p) == raw, item['sha256'])
    frozen = git('ls-tree', '-r', '--name-only', C, 'verification/r4_force_geometry').decode().splitlines()
    check('C_package_unchanged', all((ROOT / p).read_bytes() == git('show', C + ':' + p) for p in frozen), len(frozen))
    for folder in ('preflight_start', 'preflight_final'):
        pre = js(PREFIX + folder + '/preflight.json')
        check('saved_R4_preflight:' + folder, pre['counts'] == {'PASS': 138}
              and all(x['status'] == 'PASS' for x in pre['checks']), 'Historical R4 run, not coordinator session replay')
    replay = json.loads((HERE / 'author_checks_replay.json').read_text())
    check('author_checker_replay', replay['counts'] == {'PASS': 1274}
          and all(x['status'] == 'PASS' for x in replay['checks']), 'Reproduction is not independent R5')
    render = json.loads((HERE / 'renderer_replay.json').read_text())
    check('renderer_readonly', len(render['files']) == 7
          and all(x['MATCH'] for x in render['files']) and render['author_files_overwritten'] is False,
          'Only output HERE redirected; immutable input ROOT unchanged')
    manifest_raw = (ROOT / 'verification/r4_force_geometry/input_manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    check('manifest', len(manifest['inputs']) == 54 and len(manifest['protected_trees']) == 12
          and hashlib.sha256(manifest_raw).hexdigest() == claim['input_manifest_sha256'], claim['input_manifest_sha256'])
    for item in manifest['inputs']:
        p = item['path']
        raw = git('show', item['commit'] + ':' + p)
        check('pinned:' + p, hashlib.sha256(raw).hexdigest() == item['sha256']
              and (ROOT / p).read_bytes() == raw and git('show', BASE + ':' + p) == raw, item['sha256'])
    for p, expected in manifest['protected_trees'].items():
        check('protected:' + p, git('rev-parse', BASE + ':' + p).decode().strip() == expected
              and subprocess.run(['git', '-C', str(ROOT), 'diff', '--quiet', BASE, '--', p]).returncode == 0, expected)
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'target_C': C,
              'request_H': H, 'main': BASE, 'checks': checks, 'passed': len(checks), 'failed': 0,
              'independent_R5_review': 'NOT_RUN', 'reviewer_assigned': False,
              'R4_session_preflight_replayed': False, 'numeric_physical_evaluation': 'NOT_RUN'}
    (HERE / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS {len(checks)} coordinator handoff checks; R5 review remains NOT_RUN')


if __name__ == '__main__':
    main()
