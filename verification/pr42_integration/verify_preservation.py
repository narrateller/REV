"""Check PR42's frozen result, review history and integration-only scope.

--record writes only this preparation's preservation manifest; no model is run.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
C = '43f03359fabe2b664935b17f9ac7851504093ece'
R5 = 'e69a8afbe4df3d53c4cc8b5883319e00eb8130af'
MAIN = '65dca013833b64b446157c6faf4042643d909451'
CLAIM = '7ec621cb8aa306192536df8598e390daf8726b1d'
LEASE = '2026-11-13T16:08:52Z'
REVIEW_ID = 'REV-R5-R3-CYCLE-TRACE-01-001'
SCOPES = ['params', 'scripts', 'tests', 'cad', 'evidence', 'sources']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files_at(commit, path):
    return git('ls-tree', '-r', '--name-only', commit, '--', path).decode().splitlines()


def frozen_tree(commit, path):
    records = {}
    for name in files_at(commit, path):
        original = git('show', commit + ':' + name)
        assert (ROOT / name).read_bytes() == original, name
        records[name] = {'commit': commit, 'sha256': sha(original)}
    return records


def collect():
    subprocess.run(['git', 'merge-base', '--is-ancestor', CLAIM, MAIN], cwd=ROOT, check=True)
    claim_text = git('show', MAIN + ':verification/r3_cycle_trace/task.md')
    assert b'proposed_owner_session r3-sizing-20261112' in claim_text
    assert ('proposed_lease_expires_at ' + LEASE).encode() in claim_text
    subprocess.run(['git', 'merge-base', '--is-ancestor', C, R5], cwd=ROOT, check=True)
    subprocess.run(['git', 'merge-base', '--is-ancestor', R5, 'HEAD'], cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--quiet', MAIN, '--', *SCOPES], cwd=ROOT, check=True)
    package = frozen_tree(C, 'verification/r3_cycle_trace')
    review = frozen_tree(R5, 'verification/r5_r3_cycle_trace_review')
    assert len(package) == 27 and len(review) == 23
    index = git('show', R5 + ':reviews/cross_check_log.md')
    assert (ROOT / 'reviews/cross_check_log.md').read_bytes() == index
    section = index.decode().split('## ' + REVIEW_ID, 1)[1]
    record = yaml.safe_load(re.search(r'```yaml\n(.*?)\n```', section, re.S).group(1))
    assert record['reviewed_commit'] == C
    assert record['verdict'] == 'WARNING' and record['validity'] == 'CURRENT'
    reviewed = {}
    for item in record['artifacts']:
        assert sha((ROOT / item['path']).read_bytes()) == item['sha256'], item['path']
        reviewed[item['path']] = item['sha256']
    old = json.loads((ROOT / 'verification/r3_cycle_trace/result_preservation.json').read_text())
    for key in ('protected_calculation_files', 'preserved_R5_files'):
        for name, item in old[key].items():
            assert sha((ROOT / name).read_bytes()) == item['sha256'], name
    return {
        'main': MAIN, 'claim_commit': CLAIM, 'claim_acceptance': 'ACCEPTED_MAIN_PR41',
        'owner_session': 'r3-sizing-20261112', 'role': 'R3',
        'main_claim_text_sha256': sha(claim_text),
        'owner_basis': 'Claim accepted through PR41 ancestry and user confirmation; '
                       'raw PROPOSED/NONE text is historical proposal, normalized in branch task log',
        'lease_expires_at': LEASE, 'lease_extended': False,
        'checked_result_C': C, 'R5_act_C': R5, 'review_id': REVIEW_ID,
        'R5_verdict': 'ACCEPT_WITH_WARNING', 'index_verdict_preserved': 'WARNING',
        'R5_index_sha256': sha(index), 'R5_index_unchanged': True,
        'result_package': package, 'R5_review_files': review,
        'all_reviewed_artifacts': reviewed,
        'calculation_files': old['protected_calculation_files'],
        'historic_R5_files': old['preserved_R5_files'],
        'unchanged_tracked_scopes_against_main': SCOPES,
        'CAD_review': 'NOT_AVAILABLE', 'general_rebuild': 'NOT_READY',
        'whole_cycle': 'INDETERMINATE', 'B_opening': 'INDETERMINATE',
        'CYC_01_to_09': 'OPEN', 'R5_CYCLE_W01_W02': 'OPEN',
        'G1': 'OPEN', 'physical_tests': 'NOT_RUN',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    data = collect()
    target = HERE / 'preservation.json'
    if args.record:
        now = datetime.now(timezone.utc)
        assert now < datetime.fromisoformat(LEASE.replace('Z', '+00:00'))
        assert git('rev-parse', 'origin/main').decode().strip() == MAIN
        data['observed_at_utc'] = now.isoformat()
        data['lease_valid_at_observation'] = True
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    else:
        saved = json.loads(target.read_text())
        observed = datetime.fromisoformat(saved.pop('observed_at_utc'))
        assert saved.pop('lease_valid_at_observation') is True
        assert observed < datetime.fromisoformat(LEASE.replace('Z', '+00:00'))
        assert saved == data, 'Preservation manifest differs'
    print('PASS: 27 result files, 23 R5 review files, review index, all reviewed artifacts, '
          '88 calculation and 45 historical R5 files unchanged; protected scopes unchanged')


if __name__ == '__main__':
    main()
