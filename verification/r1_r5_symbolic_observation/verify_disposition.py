"""R1 documentary acceptance checks; no reviewer/session replay or physical work."""
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = 'f731910273b47f46c6d45114cecd76de6fa8adf9'
C4 = 'b840dfd5444da2bf62483b7f4a6069d2bb255b71'
H4 = '9433ef749df14a3bbf8ea32331e2f895fd5bf7aa'
C5 = '4aa23509b45efc2c2c166935102ca5caa76f55e2'
H5 = '92230cef87b71aa7e2d51fe6f21c11360331dd37'
OWNER = '6afb4750-7918-8191-8569-77b5b0c41050'
REVIEWER = '6afb0a73-b16c-8191-a539-9a6685e89034'
P4 = 'verification/r4_force_geometry/symbolic_20261116/'
P5 = 'verification/r5_r4_force_geometry_symbolic_review/'


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

    check('main_exact', git('rev-parse', 'origin/main').decode().strip() == BASE, BASE)
    check('accepted_ancestry', git('merge-base', BASE,
          'cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9').decode().strip()
          == 'cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9', 'PR49 accepted')
    check('R4_inherited', git('merge-base', C4, H5).decode().strip() == C4, H5)
    check('R4_request_inherited', git('merge-base', H4, H5).decode().strip() == H4, H4)
    check('R5_H_child', git('rev-parse', H5 + '^').decode().strip() == C5, C5)
    check('R5_H_scope', set(git('diff', '--name-only', C5, H5).decode().splitlines()) == {
          'STATE.md', 'NEXT_MODEL.md', 'handoffs/T-r5-r4-force-geometry-symbolic-review-01/'
          + REVIEWER + '.md'}, 'handoff only')
    for name in ('claim.json', 'claim.md', 'input_audit.json', 'input_audit.md'):
        p = 'verification/r4_force_geometry/' + name
        check('R4_ownership_audit_frozen:' + name,
              (ROOT / p).read_bytes() == blob(C4, p), sha(blob(C4, p)))
    claim = js('verification/r4_force_geometry/claim.json')
    canonical = js('verification/r4_force_geometry/claim.json', BASE)
    for name, c in [('main', canonical), ('R4', claim)]:
        check('owner_lease:' + name, c['status'] == 'ACCEPTED_MAIN'
              and c['owner_session'] == c['session_id'] == OWNER
              and c['lease_expires_at'] == c['proposed_lease_expires_at']
              == '2026-11-17T17:44:00Z', 'No extension or takeover')
    now = datetime.now(timezone.utc)
    check('lease_live_at_coordination', now < datetime.fromisoformat(
          claim['lease_expires_at'].replace('Z', '+00:00')), now.isoformat())
    ident = js(P5 + 'identity.json')
    check('reviewer_disclosure', ident['actual_session_id'] == REVIEWER
          and REVIEWER != OWNER and not ident['target_coauthor']
          and ident['target_C'] == C4 and ident['request_H'] == H4
          and 'db6b9774649f99ad1b157cba2a9c7cdeec570302' in ident['upstream_authorship_disclosure'],
          'Reported independence scoped to R4 target; upstream authorship disclosed')
    expected = {v + '/datum_motion:family_reference_qualified'
                for v in ('A-V1', 'A-V2', 'B-V1', 'B-V2')}
    for name in ('independent.json', 'independent_after_record.json'):
        report = js(P5 + name)
        check('R5_target:' + name, report['target_C'] == C4 and report['request_H'] == H4,
              'Immutable reviewed target')
        check('R5_counts:' + name, dict(Counter(c['result'] for c in report['checks']))
              == report['counts'] == {'PASS': 2422, 'FAIL': 4}, 'Four FAIL are retained')
        check('R5_exact_FAIL_set:' + name,
              {c['id'] for c in report['checks'] if c['result'] == 'FAIL'} == expected,
              sorted(expected))
        check('R5_OPEN_P2:' + name, len(report['findings']) == 4 and all(
              f['id'] == 'R5-SYM-OBS-01' and f['priority'] == 'P2' and f['blocking'] is False
              for f in report['findings']), 'One four-row documentary observation')
        check('R5_limits:' + name, report['verdict'] == 'WARNING'
              and report['input_audit_456'] == 'NOT_RUN' and report['physical_READY'] == 'NO_GO'
              and report['G1'] == 'OPEN', 'No physical acceptance')
    validation = js(P5 + 'validation.json')
    for item in validation['package_files']:
        p = item['path']
        check('R5_evidence_hash:' + p, sha(blob(C5, p)) == item['sha256']
              and (ROOT / p).read_bytes() == blob(C5, p), item['sha256'])
    for folder in ('verification/r4_force_geometry', P5.rstrip('/'),
                   'verification/r3_force_path', 'verification/r5_force_path_output_review'):
        paths = git('ls-tree', '-r', '--name-only', H5, folder).decode().splitlines()
        check('source_package:' + folder, bool(paths) and all(
              (ROOT / p).read_bytes() == blob(H5, p) for p in paths), len(paths))
    manifest = js('verification/r4_force_geometry/input_manifest.json')
    check('manifest_counts', len(manifest['inputs']) == 54
          and len(manifest['protected_trees']) == 12, '54 files / 12 source trees')
    for item in manifest['inputs']:
        p = item['path']; raw = blob(item['commit'], p)
        check('pinned:' + p, sha(raw) == item['sha256']
              and (ROOT / p).read_bytes() == raw and blob(BASE, p) == raw, item['sha256'])
    protected = []
    for p, tree in manifest['protected_trees'].items():
        check('source_tree:' + p, git('rev-parse', BASE + ':' + p).decode().strip() == tree,
              'Original pinned source tree; new review append checked separately')
        for f in git('ls-tree', '-r', '--name-only', BASE, p).decode().splitlines():
            raw = blob(BASE, f); current = (ROOT / f).read_bytes()
            if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                okay = sha(current) == re.search(rb'oid sha256:([a-f0-9]{64})', raw).group(1).decode()
            elif f == 'reviews/cross_check_log.md':
                okay = current == blob(C5, f) and current.startswith(raw)
            else:
                okay = current == raw
            check('protected:' + f, okay, sha(current)); protected.append(f)
    rows = js(P4 + 'interfaces.json')['rows']
    check('52_rows', len(rows) == 52 and Counter(r['variant'] for r in rows)
          == {'A-V1': 13, 'A-V2': 13, 'B-V1': 13, 'B-V2': 13}, 'No author correction performed')
    for row in rows:
        if row['row_key'].endswith('/datum_motion'):
            family = row['variant'][0]
            foreign = 'CI-X_B_GATHER' if family == 'A' else 'CI-X_COLUMN_GATHER'
            own = 'CI-X_COLUMN_GATHER' if family == 'A' else 'CI-X_B_GATHER'
            refs = {r['source_id'] for r in row['source_references'] if r['source'] == 'CI'}
            check('observation_reproduced:' + row['row_key'], foreign in refs and own in refs,
                  {'remove': foreign, 'retain': own, 'status': 'OPEN'})
    states = js(P4 + 'state_dependencies.json')['rows']
    check('42_unsolved_states', len(states) == 42 and [r['source_state'] for r in states]
          == js('verification/r3_force_path/analysis/state_matrix.json') and all(
              r['actual_solution'] == 'NOT_RUN' and r['actual_force'] is None
              and r['actual_moment'] is None and r['actual_capacity_margin'] is None for r in states),
          'States compared, not solved')
    unknowns = js(P4 + 'unknown_index.json')
    check('84_RAW_null', len(unknowns) == 84 and all(x['value'] is None
          and x['source_lifecycle'] == 'RAW' for x in unknowns), 'No new engineering assignments')
    bindings = js('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows']
    check('44_full_bindings', len(bindings) == 44, 'Full source bytes pinned above')
    for p in ('STATE.md', 'NEXT_MODEL.md', 'ISSUES_AND_TASKS.md',
              'handoffs/T-r4-force-geometry-01/r1-pr48-integration-20261116.md'):
        current = (ROOT / p).read_bytes(); old = blob(H5, p)
        prefix = current[:-len(old)] if current.endswith(old) else b''
        check('history_suffix:' + p, current.endswith(old) and bool(prefix), 'New summary prepended')
        check('summary_no_parameter_refs:' + p,
              not re.search(rb'\[([A-Z][A-Z0-9_-]*)@(\d+)\]', prefix),
              'C reference substitution cannot alter registry parameter references')
    result = dict(checked_at_utc=now.isoformat(), main=BASE, R4_C=C4, R4_H=H4,
                  R5_C=C5, R5_H=H5, checks=checks, counts={'PASS': len(checks), 'FAIL': 0},
                  preserved_materialized_files=len(protected), R5_counts={'PASS': 2422, 'FAIL': 4},
                  observation='R5-SYM-OBS-01 OPEN/P2', new_R5_review=False,
                  R5_session_oracle_replayed=False, R4_session_preflight_replayed=False,
                  numeric_physical_work='NOT_RUN', main_merge=False)
    (HERE / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('counts', 'preserved_materialized_files', 'R5_counts', 'observation')}))


if __name__ == '__main__':
    main()
