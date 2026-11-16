"""Coordinator checks of exact R4 audit evidence, not an R4-session replay."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
C = '45caac78f00ab1535387bb5ed8d7f17caf9afc1f'
H = 'd94096faa3ce9904c9a86b6d38ad1d5863e0f6e9'
BASE = 'f731910273b47f46c6d45114cecd76de6fa8adf9'
OWNER = '6afb4750-7918-8191-8569-77b5b0c41050'


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

    check('current_main', git('rev-parse', 'origin/main').decode().strip() == BASE, BASE)
    check('C_based_on_main', git('merge-base', BASE, C).decode().strip() == BASE, C)
    check('H_immediate_parent', git('show', '-s', '--format=%P', H).decode().strip() == C, H)
    changed = git('diff', '--name-only', C, H).decode().splitlines()
    check('H_scope', set(changed) == {'STATE.md', 'NEXT_MODEL.md',
          'handoffs/T-r4-force-geometry-01/' + OWNER + '.md'}, changed)
    prefix = 'verification/r4_force_geometry/'
    claim = js(prefix + 'claim.json')
    accepted = json.loads(git('show', BASE + ':' + prefix + 'claim.json'))
    for name, data in (('main', accepted), ('R4', claim)):
        check('owner:' + name, data['owner_session'] == data['session_id'] == OWNER
              and data['status'] == 'ACCEPTED_MAIN' and data['role_assignment_confirmed'] is True,
              OWNER)
        check('deadline:' + name, data['lease_expires_at'] == data['proposed_lease_expires_at']
              == '2026-11-17T17:44:00Z' and datetime.now(timezone.utc)
              < datetime.fromisoformat(data['lease_expires_at'].replace('Z', '+00:00')),
              data['lease_expires_at'])
    check('scope_unchanged', all(claim[k] == accepted[k] for k in
          ('scope', 'exclusions', 'input_manifest_sha256', 'claim_acceptance_commit', 'claim_acceptance_PR')),
          'No new assignment, lease or scope')
    audit = js(prefix + 'input_audit.json')
    statuses = Counter(x['status'] for x in audit['items'])
    check('audit_counts', len(audit['items']) == 7 and statuses == Counter(audit['counts'])
          and audit['counts'] == {'PASS': 4, 'NOT_RUN': 3, 'FAIL': 0, 'NOT_APPLICABLE': 0},
          dict(statuses))
    check('audit_sections', {x['section']: x['status'] for x in audit['items']}
          == {1: 'PASS', 2: 'PASS', 3: 'PASS', 4: 'NOT_RUN', 5: 'NOT_RUN', 6: 'NOT_RUN', 7: 'PASS'},
          'Physical recalculation, geometry and cycle remain NOT_RUN')
    check('audit_scope', audit['verdict'] == 'WARNING'
          and audit['independent_review_of_this_audit'] == 'NOT_RUN'
          and audit['author_sessions'] == [OWNER]
          and audit['engineering_geometry'] == audit['engineering_calculations'] == 'NOT_STARTED'
          and audit['physical_trials'] == 'NOT_RUN', 'No engineering or independent-review promotion')
    check('claim_audit_link', claim['input_audit'] == 'COMPLETED_WARNING_4_PASS_3_NOT_RUN'
          and claim['engineering_geometry'] == 'NOT_STARTED', claim['start_gate'])
    evidence = js(prefix + 'preflight_20261116/validation.json')
    for item in evidence['file_sha256']:
        path = item['path']
        raw = git('show', C + ':' + path)
        current = (ROOT / path).read_bytes()
        preserved = current.endswith(raw) if path == 'ISSUES_AND_TASKS.md' else current == raw
        check('R4_evidence:' + path, hashlib.sha256(raw).hexdigest() == item['sha256']
              and preserved and git('show', H + ':' + path) == raw,
              item['sha256'])
    for folder in ('checks', 'final_checks'):
        pf = js(prefix + 'preflight_20261116/' + folder + '/preflight.json')
        check('saved_preflight:' + folder, pf['counts'] == {'PASS': 138}
              and len(pf['checks']) == 138 and all(x['status'] == 'PASS' for x in pf['checks']),
              'R4 historical run verified from saved bytes; not rerun as R4 by coordinator')
    check('saved_registry_exit', evidence['registry_status']['returncode'] == 0
          and evidence['precommit_registry']['returncode'] == 0, 'R4 recorded underlying returncodes')
    heartbeat = js(prefix + 'preflight_20261116/heartbeat_end.json')
    check('executor_heartbeat', heartbeat['session_id'] == OWNER
          and heartbeat['recorded_at_utc'] == claim['heartbeat_utc']
          and heartbeat['lease_extended'] is False
          and heartbeat['engineering_geometry'] == 'NOT_STARTED', claim['heartbeat_utc'])
    manifest_raw = (ROOT / prefix / 'input_manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    check('manifest', len(manifest['inputs']) == 54 and len(manifest['protected_trees']) == 12
          and hashlib.sha256(manifest_raw).hexdigest() == claim['input_manifest_sha256'],
          claim['input_manifest_sha256'])
    for item in manifest['inputs']:
        path = item['path']
        raw = git('show', item['commit'] + ':' + path)
        check('pinned:' + path, hashlib.sha256(raw).hexdigest() == item['sha256']
              and git('rev-parse', item['commit'] + ':' + path).decode().strip() == item['git_blob']
              and git('show', BASE + ':' + path) == raw and (ROOT / path).read_bytes() == raw,
              item['sha256'])
    for path, expected in manifest['protected_trees'].items():
        check('protected:' + path, git('rev-parse', BASE + ':' + path).decode().strip() == expected
              and subprocess.run(['git', '-C', str(ROOT), 'diff', '--quiet', BASE, '--', path]).returncode == 0,
              expected)
    bindings = js('verification/r4_cycle_interfaces/proposal/baseline_bindings.json')
    check('44_bindings', len(bindings['rows']) == 44 and bindings
          == js('verification/r3_force_path/analysis/baseline_snapshot.json'), 'All fields and ordered rows')
    for directory in ('verification/r4_force_geometry',):
        paths = git('ls-tree', '-r', '--name-only', C, directory).decode().splitlines()
        check('R4_package_exact', all((ROOT / p).read_bytes() == git('show', C + ':' + p) for p in paths),
              len(paths))
    prs = json.loads(subprocess.check_output(['gh', 'pr', 'list', '--repo', 'narrateller/REV',
        '--state', 'open', '--limit', '100', '--json', 'number,title,headRefName,headRefOid']))
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'R4_C': C, 'R4_H': H,
              'main': BASE, 'checks': checks, 'passed': len(checks), 'failed': 0,
              'R4_preflight_replayed_as_R4': False, 'independent_engineering_review': 'NOT_RUN',
              'current_open_PRs': prs, 'engineering_geometry': 'NOT_STARTED',
              'next_scope': 'Existing WARNING documentary/symbolic only; no numerical/physical conclusions'}
    (HERE / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS {len(checks)} coordinator evidence/input checks; audit WARNING, 4 PASS/3 NOT_RUN preserved')


if __name__ == '__main__':
    main()
