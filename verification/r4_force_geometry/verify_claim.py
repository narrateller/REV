"""Validate the unaccepted R4 proposal and preserved immutable input package."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    claim = json.loads((HERE / 'claim.json').read_text())
    raw = (HERE / 'input_manifest.json').read_bytes()
    manifest = json.loads(raw)
    checks = []

    def check(name, ok, evidence):
        checks.append({'check': name, 'passed': bool(ok), 'evidence': evidence})
        if not ok:
            raise ValueError(name)

    check('unaccepted_proposal', claim['status'] == 'PROPOSED_PENDING_MAIN'
          and claim['owner_session'] == 'NONE'
          and all(claim[k] is None for k in ('lease_expires_at',
                  'claim_acceptance_commit', 'claim_acceptance_PR', 'heartbeat_utc')),
          'Known candidate identity does not create owner, lease, heartbeat or acceptance')
    report_raw = (ROOT / claim['executor_report']).read_bytes()
    report = json.loads(report_raw)
    check('actual_candidate_report', str(uuid.UUID(claim['session_id'])) == claim['session_id']
          == claim['proposed_owner_session'] == report['session_id']
          and report['read_head'] == 'd84adaab398ffee4fe15ab87c9899ffa8beb22e8'
          and hashlib.sha256(report_raw).hexdigest() == claim['executor_report_sha256']
          and claim['model_label'] == report['model_label']
          and claim['exact_runtime_model_id'] is report['exact_runtime_model_id'] is None
          and report['coordinator_independently_retested_capabilities'] is False,
          'Actual existing session/model/tools are recorded as a user-forwarded R4 report')
    check('role_still_unconfirmed', claim['role_assignment_confirmed'] is False
          and report['role_assignment_confirmed'] is False
          and claim['assignment_utc'] is None
          and claim['start_gate'] == 'BLOCKED_PENDING_MAIN_ACCEPTANCE_AND_R4_ROLE_CONFIRMATION',
          'No user role confirmation or execution permission is inferred from identity')
    old_claim = json.loads((HERE / 'claim_history/20261116T174400Z/claim.json').read_text())
    check('identity_update_without_lease_renewal', claim['proposal_revision'] == 2
          and old_claim['proposed_owner_session'] == 'r4-force-geometry-20261116'
          and claim['proposed_at_utc'] == old_claim['proposed_at_utc']
          and claim['proposed_lease_expires_at'] == old_claim['proposed_lease_expires_at']
          and (HERE / 'claim_history/20261116T174400Z/claim.json').read_bytes()
          == git('show', 'd84adaab398ffee4fe15ab87c9899ffa8beb22e8:verification/r4_force_geometry/claim.json'),
          'Revision 1 preserved exactly; only candidate identity is clarified')
    check('no_engineering', claim['execution_status'] == 'NOT_STARTED'
          and claim['engineering_geometry'] == 'NOT_STARTED'
          and claim['native_CAD_CAE'] == claim['physical_trials'] == 'NOT_RUN',
          'Only a coordinator proposal was prepared')
    check('no_old_claim_extension', claim['old_claims_extended'] is False
          and claim['self_acceptance_permitted'] is False, 'No takeover/self-acceptance')
    start = datetime.fromisoformat(claim['proposed_at_utc'].replace('Z', '+00:00'))
    expiry = datetime.fromisoformat(claim['proposed_lease_expires_at'].replace('Z', '+00:00'))
    check('new_proposed_24h', expiry - start == timedelta(hours=24)
          and claim['proposed_lease_duration_hours'] == 24, 'Coordination metadata, not a live lease')
    check('proposal_current_at_validation', datetime.now(timezone.utc) < expiry, expiry.isoformat())
    check('manifest_binding', hashlib.sha256(raw).hexdigest() == claim['input_manifest_sha256']
          and len(manifest['inputs']) == 54
          and len({x['path'] for x in manifest['inputs']}) == 54
          and len(manifest['protected_trees']) == 12,
          claim['input_manifest_sha256'])
    base = manifest['base_main']
    check('ordinary_PR48_merge', git('show', '-s', '--format=%P', base).decode().strip().split()
          == ['1dce280bf4c6a790ef0ace10a757fe0a72148b5f', manifest['integrated_head']], base)
    check('merge_tree_exact', git('rev-parse', base + '^{tree}')
          == git('rev-parse', manifest['integrated_head'] + '^{tree}'), 'No merge content changes')
    for key in ('R3_C', 'R3_H', 'R5_C', 'R5_H', 'R1_C', 'R1_H'):
        result = subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', manifest[key], base])
        check('history:' + key, result.returncode == 0, manifest[key])
    for item in manifest['inputs']:
        path = item['path']
        stored = git('show', item['commit'] + ':' + path)
        check('pinned:' + path, hashlib.sha256(stored).hexdigest() == item['sha256']
              and (ROOT / path).read_bytes() == stored
              and git('rev-parse', item['commit'] + ':' + path).decode().strip() == item['git_blob'],
              item['sha256'])
    for path, expected in manifest['protected_trees'].items():
        result = subprocess.run(['git', '-C', str(ROOT), 'diff', '--quiet', base, '--', path])
        check('protected:' + path, result.returncode == 0
              and git('rev-parse', base + ':' + path).decode().strip() == expected, expected)
    bindings = json.loads((ROOT / 'verification/r4_cycle_interfaces/proposal/baseline_bindings.json').read_text())
    snapshot = json.loads((ROOT / 'verification/r3_force_path/analysis/baseline_snapshot.json').read_text())
    check('44_full_bindings', len(bindings['rows']) == 44 and bindings == snapshot,
          'All fields, ordered rows and source values preserved')
    merge = json.loads((HERE / 'pr48_merge_result.json').read_text())
    check('GitHub_merge_receipt', merge['merged'] is True and merge['sha'] == base, merge)
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'task_id': claim['task_id'], 'base_main': base, 'checks': checks,
              'passed': len(checks), 'failed': 0, 'engineering_execution': 'NOT_STARTED',
              'claim_accepted': False, 'physical_trials': 'NOT_RUN'}
    (HERE / 'claim_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS {len(checks)} claim/input checks; 54 pinned files, 44 bindings; engineering NOT_STARTED')


if __name__ == '__main__':
    main()
