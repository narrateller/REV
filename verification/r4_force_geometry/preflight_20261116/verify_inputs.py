"""Read-only executor preflight; outputs checks, never geometry/calculations.

Run from /workspace/REV:
  .venv/bin/python verification/r4_force_geometry/preflight_20261116/verify_inputs.py
The output directory must be new (or empty); existing evidence is not overwritten.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = 'f731910273b47f46c6d45114cecd76de6fa8adf9'
OWNER = '6afb4750-7918-8191-8569-77b5b0c41050'
MERGE = 'cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9'
PR_HEAD = '70ab9a1926235170e449b85d558f135ddae90add'
TASK = 'T-r4-force-geometry-01'
DEADLINE = '2026-11-17T17:44:00Z'
sys.path.insert(0, str(ROOT / 'scripts'))
from repo_support import engineering_sha, flatten  # noqa: E402
import yaml  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=HERE / 'checks')
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit('Evidence output exists; use --output with a fresh directory')
    checks, commands = [], []

    def run(argv):
        r = subprocess.run(argv, cwd=ROOT, capture_output=True)
        commands.append({'argv': argv, 'returncode': r.returncode,
                         'checked_at_utc': datetime.now(timezone.utc).isoformat()})
        if r.returncode:
            raise RuntimeError(f'Command failed ({r.returncode}): {argv}')
        return r.stdout

    def git(*argv):
        return run(['git', *argv])

    def check(name, ok, evidence):
        checks.append({'check': name, 'status': 'PASS' if ok else 'FAIL',
                       'evidence': evidence})

    def save(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    started = datetime.now(timezone.utc).isoformat()
    try:
        observed = git('rev-parse', 'origin/main').decode().strip()
        check('fetched_main_is_audited_base', observed == BASE, observed)
        check('branch_contains_base', git('merge-base', BASE, 'HEAD').decode().strip() == BASE, BASE)
        check('actual_session', os.environ.get('CODEX_SESSION_ID') == OWNER, OWNER)
        claim = json.loads((ROOT / 'verification/r4_force_geometry/claim.json').read_text())
        accepted = json.loads(git('show', BASE + ':verification/r4_force_geometry/claim.json'))
        for name, x in [('accepted_main', accepted), ('working_claim', claim)]:
            check(name + ':identity', x['owner_session'] == x['session_id'] == OWNER
                  and x['task_id'] == TASK and x['role'] == 'R4'
                  and x['status'] == 'ACCEPTED_MAIN' and x['role_assignment_confirmed'] is True,
                  {'owner': x['owner_session'], 'status': x['status']})
            check(name + ':deadline', x['lease_expires_at'] == x['proposed_lease_expires_at']
                  == DEADLINE and datetime.now(timezone.utc)
                  < datetime.fromisoformat(DEADLINE.replace('Z', '+00:00')),
                  {'deadline': x['lease_expires_at'], 'old_claims_extended': x['old_claims_extended']})
        pr = json.loads(run(['gh', 'pr', 'view', '49', '--repo', 'narrateller/REV', '--json',
                             'number,url,state,headRefOid,headRefName,mergeCommit,mergedAt']))
        save('PR49.json', pr)
        receipt = json.loads((ROOT / accepted['acceptance_receipt']).read_text())
        auth = json.loads((ROOT / accepted['role_authorization']).read_text())
        parents = git('show', '-s', '--format=%P', MERGE).decode().strip().split()
        check('PR49_receipt_and_live_provider', pr['state'] == 'MERGED'
              and pr['mergeCommit']['oid'] == receipt['merge_commit_sha'] == MERGE
              and pr['headRefOid'] == receipt['reviewed_head'] == PR_HEAD
              and pr['mergedAt'] == receipt['merged_at'], pr)
        check('ordinary_PR49_merge', parents == [accepted['base_main'], PR_HEAD], parents)
        check('accepted_ancestry', git('merge-base', MERGE, BASE).decode().strip() == MERGE, BASE)
        check('merge_tree_matches_reviewed_head', git('rev-parse', MERGE + '^{tree}')
              == git('rev-parse', PR_HEAD + '^{tree}'), PR_HEAD)
        check('explicit_user_assignment', auth['session_id'] == OWNER and auth['role'] == 'R4'
              and auth['task_id'] == TASK and auth['role_assignment_confirmed'] is True
              and auth['deadline'] == DEADLINE and auth['lease_extension_authorized'] is False,
              accepted['role_authorization'])

        # Current accepted claims only: archived proposals are not competing owners.
        files = git('ls-tree', '-r', '--name-only', BASE).decode().splitlines()
        candidates = [p for p in files if p.endswith('/claim.json')
                      and not re.search(r'/(?:claim_history|archive|archives)/', p)]
        records = []
        for path in candidates:
            x = json.loads(git('show', BASE + ':' + path))
            if x.get('task_id') == TASK:
                records.append({'path': path, 'status': x.get('status'),
                                'owner': x.get('owner_session'), 'lease': x.get('lease_expires_at')})
        prs = json.loads(run(['gh', 'pr', 'list', '--repo', 'narrateller/REV', '--state', 'open',
                              '--limit', '100', '--json',
                              'number,title,headRefName,headRefOid,baseRefName']))
        save('competition.json', {'main': BASE, 'claims_scanned': candidates,
             'matching_current_records': records, 'open_PRs': prs,
             'scope': 'Accepted current main claims and live open PRs; unpublished work is unobservable.'})
        check('no_competing_accepted_owner', len(records) == 1
              and records[0]['owner'] == OWNER and records[0]['status'] == 'ACCEPTED_MAIN', records)
        check('no_open_competing_PR', len(prs) == 0, prs)
        tracker = git('show', BASE + ':ISSUES_AND_TASKS.md').decode().split('---', 1)[0]
        check('current_tracker_agrees', OWNER in tracker and 'ACCEPTED_MAIN' in tracker
              and DEADLINE in tracker and TASK in tracker, 'Current tracker section, historical sections excluded')

        raw = (ROOT / 'verification/r4_force_geometry/input_manifest.json').read_bytes()
        manifest = json.loads(raw)
        digest = hashlib.sha256(raw).hexdigest()
        check('manifest_hash', digest == claim['input_manifest_sha256']
              == accepted['input_manifest_sha256'], digest)
        check('manifest_cardinality', len(manifest['inputs']) == 54
              and len({x['path'] for x in manifest['inputs']}) == 54
              and len(manifest['protected_trees']) == 12, '54 files / 12 trees')
        for key in ('R3_C', 'R3_H', 'R5_C', 'R5_H', 'R1_C', 'R1_H'):
            sha = manifest[key]
            check('history:' + key, git('merge-base', sha, BASE).decode().strip() == sha, sha)
        for item in manifest['inputs']:
            path = item['path']
            pinned = git('show', item['commit'] + ':' + path)
            check('input:' + path, hashlib.sha256(pinned).hexdigest() == item['sha256']
                  and git('rev-parse', item['commit'] + ':' + path).decode().strip() == item['git_blob']
                  and git('show', BASE + ':' + path) == pinned
                  and (ROOT / path).read_bytes() == pinned, item)

        materialized = []
        blob_cache = {}
        for path, expected in manifest['protected_trees'].items():
            check('tree:' + path, git('rev-parse', BASE + ':' + path).decode().strip() == expected
                  and git('rev-parse', manifest['base_main'] + ':' + path).decode().strip() == expected,
                  expected)
            for entry in git('ls-tree', '-r', '-z', BASE, '--', path).split(b'\0'):
                if not entry:
                    continue
                meta, name = entry.split(b'\t', 1)
                mode, kind, blob = meta.decode().split()
                rel = name.decode()
                if kind != 'blob':
                    check('materialized:' + rel, False, 'Unsupported Git entry ' + kind)
                    continue
                if blob not in blob_cache:
                    blob_cache[blob] = git('cat-file', 'blob', blob)
                saved = blob_cache[blob]
                pointer = re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\n'
                                       rb'oid sha256:([a-f0-9]{64})\nsize ([0-9]+)\n', saved)
                expected_hash = (pointer[1].decode() if pointer else hashlib.sha256(saved).hexdigest())
                actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
                ok = actual == expected_hash
                if pointer:
                    ok = ok and (ROOT / rel).stat().st_size == int(pointer[2])
                materialized.append({'path': rel, 'git_blob': blob, 'LFS': bool(pointer),
                                     'sha256': actual, 'expected_sha256': expected_hash,
                                     'status': 'PASS' if ok else 'FAIL'})
        save('preservation.json', materialized)
        check('materialized_protected_files', bool(materialized)
              and all(x['status'] == 'PASS' for x in materialized),
              {'files': len(materialized), 'LFS': sum(x['LFS'] for x in materialized)})

        bindings = json.loads((ROOT / 'verification/r4_cycle_interfaces/proposal/baseline_bindings.json').read_text())
        snapshot = json.loads((ROOT / 'verification/r3_force_path/analysis/baseline_snapshot.json').read_text())
        check('44_full_bindings_snapshot', len(bindings['rows']) == 44 and bindings == snapshot
              and Counter(x['scenario'] for x in bindings['rows']) == {'BASE_A': 22, 'BASE_B': 22},
              'Ordered full rows, all fields; 22 BASE_A + 22 BASE_B')
        params = flatten(yaml.safe_load((ROOT / 'params/registry.yaml').read_text()))
        rows = []
        for row in bindings['rows']:
            p = params[row['parameter_id']]
            source = json.loads((ROOT / row['source']).read_text())
            refs = {x['id']: x for x in source['inputs'] + source['outputs']}
            ref = refs[row['parameter_id']]
            unit = ('N' if row['proposed_cad_field'].startswith('load.') else
                    'm/s' if row['proposed_cad_field'].endswith('.speed') else
                    's' if row['proposed_cad_field'].endswith('.time')
                    or row['proposed_cad_field'] == 'time.cycle_budget' else 'm')
            ok = (all(row[k] == p[k] for k in ('value', 'unit', 'revision', 'lifecycle', 'validity'))
                  and row['engineering_sha256'] == engineering_sha(p)
                  and all(row[k] == ref[k] for k in ('value', 'unit', 'revision', 'engineering_sha256'))
                  and row['mode'] == 'fixed-budget' and row['validity'] == 'CURRENT'
                  and row['cad_application'] == 'NOT_APPLIED' and row['unit'] == unit)
            rows.append({'binding': row, 'status': 'PASS' if ok else 'FAIL',
                         'registry_definition': p, 'source_reference': ref})
            check('binding:' + row['scenario'] + ':' + row['proposed_cad_field'], ok,
                  {'id': row['parameter_id'], 'revision': row['revision'], 'source': row['source']})
        check('no_duplicate_binding_fields', len({(r['scenario'], r['proposed_cad_field'])
              for r in bindings['rows']}) == 44, 'All 44 keys unique')
        save('bindings.json', rows)
        states = json.loads((ROOT / 'verification/r3_force_path/analysis/state_matrix.json').read_text())
        check('42_states_not_solved', len(states) == 42
              and all(x['result'] == 'UNKNOWN' and x['actual_force_N'] is None
                      and x['actual_moment_Nm'] is None and x['actual_joint_support_loads'] is None
                      for x in states), '42 conditional dependency rows; no numerical solutions')
        scoped = flatten(yaml.safe_load((ROOT / 'verification/r3_force_path/analysis/params/registry.yaml').read_text()))
        r3f = {k: v for k, v in scoped.items() if k.startswith('R3F_')}
        check('84_unknown_R3F_preserved', sum(v['value'] is None and v['lifecycle'] == 'RAW'
              for v in r3f.values()) == 84, 'No UNKNOWN-to-zero promotion')
    except Exception as exc:
        check('preflight_exception', False, str(exc))
    finally:
        counts = Counter(x['status'] for x in checks)
        save('preflight.json', {'task_id': TASK, 'session_id': OWNER, 'role': 'R4',
             'base_main': BASE, 'started_at_utc': started,
             'finished_at_utc': datetime.now(timezone.utc).isoformat(),
             'acceptance_commit': MERGE, 'reviewed_PR49_head': PR_HEAD,
             'lease_expires_at': DEADLINE, 'lease_extended': False,
             'checks': checks, 'counts': dict(counts),
             'engineering_geometry': 'NOT_STARTED', 'engineering_calculations': 'NOT_STARTED',
             'native_CAD_CAE': 'NOT_RUN', 'physical_trials': 'NOT_RUN'})
        save('commands.json', commands)
        print(json.dumps(dict(counts)))
    return int(counts['FAIL'] != 0)


if __name__ == '__main__':
    raise SystemExit(main())
