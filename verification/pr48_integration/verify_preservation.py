"""Read-only integration checks; writes evidence only into this R1 package."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = '1dce280bf4c6a790ef0ace10a757fe0a72148b5f'
C3 = '93b4aead4983f88919d8e8b4165e29d7f3246600'
H3 = 'aadc08a70fbaee16b7ba4c16463bab97275926bb'
C5 = 'db6b9774649f99ad1b157cba2a9c7cdeec570302'
H5 = '6ef3afc123004c43e007dc477241edfed8efabbb'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(commit, path):
    return git('show', f'{commit}:{path}')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    checks = []

    def check(name, ok, evidence):
        checks.append({'check': name, 'passed': bool(ok), 'evidence': evidence})
        if not ok:
            raise ValueError(name)

    for ancestor, descendant in ((BASE, C3), (C3, H3), (H3, C5), (C5, H5)):
        result = subprocess.run(['git', '-C', str(ROOT), 'merge-base',
                                 '--is-ancestor', ancestor, descendant])
        check('ancestry:' + ancestor, result.returncode == 0, descendant)
    for c, h, capsule in ((C3, H3, 'handoffs/T-r3-force-path-01/r3-force-path-20261114.md'),
                          (C5, H5, 'handoffs/T-r5-force-path-output-review/r5-force-path-output-20261116.md')):
        paths = git('diff', '--name-only', c, h).decode().splitlines()
        check('handoff_scope:' + h, set(paths) == {'STATE.md', 'NEXT_MODEL.md', capsule}, paths)
    pre = json.loads(blob(C3, 'verification/r3_force_path/analysis/preflight.json'))
    for item in pre['inputs']:
        p = item['path']
        observed = {x: sha(blob(x, p)) for x in (item['commit'], BASE, C3, H3, C5, H5)}
        observed['worktree'] = sha((ROOT / p).read_bytes())
        check('pinned:' + p, all(x == item['sha256'] for x in observed.values()), observed)
    for p, expected in pre['protected_trees'].items():
        historic = {x: git('rev-parse', x + ':' + p).decode().strip() for x in (BASE, C3, H3)}
        check('historic_tree:' + p, all(x == expected for x in historic.values()), historic)
        paths = git('ls-tree', '-r', '--name-only', BASE, p).decode().splitlines()
        for path in paths:
            old = blob(BASE, path)
            new = (ROOT / path).read_bytes()
            if path == 'reviews/cross_check_log.md':
                check('old_review_history', new.startswith(old), {'old_sha256': sha(old)})
            else:
                pointer = re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\r?\noid sha256:([a-f0-9]{64})\r?\nsize ([0-9]+)\r?\n?', old)
                expected_hash = pointer[1].decode() if pointer else sha(old)
                check('protected_file:' + path, sha(new) == expected_hash, expected_hash)
    for commit, directory in ((C3, 'verification/r3_force_path'),
                               (C5, 'verification/r5_force_path_output_review')):
        paths = git('ls-tree', '-r', '--name-only', commit, directory).decode().splitlines()
        check('package:' + directory,
              all((ROOT / p).read_bytes() == blob(commit, p) for p in paths), len(paths))
    for commit, capsule in ((H3, 'handoffs/T-r3-force-path-01/r3-force-path-20261114.md'),
                            (H5, 'handoffs/T-r5-force-path-output-review/r5-force-path-output-20261116.md')):
        check('capsule:' + capsule, (ROOT / capsule).read_bytes() == blob(commit, capsule), sha(blob(commit, capsule)))
    original = json.loads(blob(BASE, 'verification/r4_cycle_interfaces/proposal/baseline_bindings.json'))
    baseline = json.loads((ROOT / 'verification/r3_force_path/analysis/baseline_snapshot.json').read_bytes())
    check('44_full_bindings', len(original['rows']) == 44 and original == baseline, 'all fields and ordered rows')
    journal = (ROOT / 'reviews/cross_check_log.md').read_bytes()
    check('R5_journal_exact', journal == blob(C5, 'reviews/cross_check_log.md'), sha(journal))
    for path in ('STATE.md', 'NEXT_MODEL.md', 'ISSUES_AND_TASKS.md'):
        check('global_history_suffix:' + path,
              (ROOT / path).read_bytes().endswith(blob(H5, path)),
              'Complete R5 H history preserved after any new R1 summary')
    matrix = json.loads((ROOT / 'verification/r3_force_path/analysis/state_matrix.json').read_bytes())
    check('state_matrix_exact', matrix == json.loads(blob(C3, 'verification/r3_force_path/analysis/state_matrix.json')),
          '42 conditions preserved; no claim of numerical solution')
    output = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'base_main': BASE,
              'R3_C': C3, 'R3_H': H3, 'R5_C': C5, 'R5_H': H5,
              'checks': checks, 'passed': len(checks), 'failed': 0,
              'CAD_rebuild': 'NOT_RUN', 'physical_tests': 'NOT_RUN',
              'strength_stability_actual_reactions': 'NOT_CONFIRMED'}
    (HERE / 'preservation.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS {len(checks)} preservation checks; 44 bindings; immutable R3/R5 packages')


if __name__ == '__main__':
    main()
