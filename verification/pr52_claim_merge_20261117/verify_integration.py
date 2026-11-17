"""Check PR52 claim metadata and preserve the exact independently reviewed inputs.

This is an integration check, not an independent engineering/source review.
Run before merge; postmerge facts are captured separately from GitHub/Git.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = '3353de6c9fc699fbd565f1ce63cebedad3137a12'
OLD = '49f0045e504863b335869748b7f9385c001469ca'
TARGET = 'f2cbd96bb78c915dca74cb4eb29daffbb52ee172'
SESSION = '6afb300b-1540-8191-a5c4-be1a684c20e0'
DEADLINE = '2026-11-17T23:16:47.225017Z'
LEDGER = 'coordination/claims/T-r1-force-inputs-intake-01.json'
SUMMARY = {'STATE.md', 'NEXT_MODEL.md', 'ISSUES_AND_TASKS.md',
           'handoffs/T-r1-force-inputs-intake-01/'+SESSION+'.md'}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    checks = []
    def check(name, condition, evidence):
        checks.append(dict(id=name, result='PASS' if condition else 'FAIL', evidence=evidence))
        if not condition:
            raise AssertionError(name)
    def read(path):
        return json.loads((ROOT/path).read_bytes())
    def digest(raw):
        return hashlib.sha256(raw).hexdigest()
    def unchanged(path, commit):
        raw = git('show', commit+':'+path)
        current = (ROOT/path).read_bytes()
        if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            return digest(current) == re.search(rb'oid sha256:([a-f0-9]{64})', raw).group(1).decode()
        return current == raw

    now = datetime.now(timezone.utc)
    check('actual_session', os.environ.get('CODEX_SESSION_ID') == SESSION, SESSION)
    check('base_before_merge', git('rev-parse', 'origin/main').decode().strip() == BASE, BASE)
    claim = read(LEDGER)
    check('user_authority', claim['acceptance_authority'] == 'USER_EXPLICIT_INSTRUCTION'
          and 'Прими claim' in read(claim['authorization'])['user_message_verbatim'], 'User decision recorded')
    check('owner', claim['owner_session'] == claim['session_id'] == SESSION and claim['role'] == 'R1', SESSION)
    check('original_deadline_live', claim['lease_expires_at'] == DEADLINE
          and not claim['lease_extension'] and now < datetime.fromisoformat(DEADLINE.replace('Z', '+00:00')), DEADLINE)
    check('activation_is_main_inclusion', claim['status'] == 'ACCEPTED_MAIN'
          and 'remote main contains this exact record' in claim['activation_predicate'], 'Branch file is not a lock')
    check('scope', claim['engineering_execution'] == 'NOT_STARTED'
          and claim['input_audit_456'] == 'NOT_RUN' and claim['enforcement'] == 'PROCEDURAL', claim['scope'])
    proposal = claim['proposal_path']
    check('reviewed_claim_unchanged', unchanged(proposal, TARGET)
          and digest((ROOT/proposal).read_bytes()) == claim['proposal_sha256'], proposal)
    old_claim = read(proposal)
    check('historical_proposal_retained', old_claim['owner_session'] == 'NONE'
          and old_claim['lease_expires_at'] is None and old_claim['proposed_lease_expires_at'] == DEADLINE,
          'Separate live ownership record preserves exact source snapshot')
    competition = read('verification/pr52_claim_merge_20261117/competition.json')
    check('competition', competition['main'] == BASE and not competition['competing_accepted_owner_found']
          and competition['main_intake_accepted_record'] is None, competition['scope'])
    check('source_preflight', read('verification/pr52_claim_merge_20261117/source_preservation_preflight.json')['counts']
          == {'PASS': 1163, 'FAIL': 0}, 'Fresh author integration preservation check, not R5 replay')
    for run in ('43987417563', '43987409150'):
        ci = read('verification/pr52_claim_merge_20261117/original_head_CI_'+run+'.json')
        check('original_head_CI:'+run, ci['head_sha'] == OLD and ci['status'] == 'completed'
              and ci['conclusion'] == 'success', ci['html_url'])
    for path in git('ls-tree', '-r', '--name-only', TARGET, 'verification/r1_force_inputs_intake').decode().splitlines():
        check('original_packet:'+path, unchanged(path, TARGET), path)
    for item in read('verification/r5_reference_intake_review/validation.json')['package_files']:
        check('R5_seal:'+item['path'], digest((ROOT/item['path']).read_bytes()) == item['sha256'], item['sha256'])
    journal = 'reviews/cross_check_log.md'
    check('journal_unchanged', unchanged(journal, OLD), 'CURRENT exact-C review unchanged; historical REJECT/STALE retained')
    records = [yaml.safe_load(b) for b in re.findall(r'^```yaml\s*\n(.*?)^```\s*$',
               (ROOT/journal).read_text(), re.M | re.S)]
    act = next(r for r in records if isinstance(r, dict)
               and r.get('review_id') == 'REV-R5-REFERENCE-INTAKE-REVIEW-01-001')
    check('current_exact_review', act['reviewed_commit'] == TARGET and act['validity'] == 'CURRENT'
          and act['verdict'] == 'WARNING' and act['claim_effective'] is False,
          'Review described the source proposal; current ownership is separately authorized')
    for item in act['artifacts']:
        check('reviewed_artifact:'+item['path'], digest((ROOT/item['path']).read_bytes()) == item['sha256'], item['sha256'])
    changed = set(git('diff', OLD, '--name-only').decode().splitlines())
    check('changed_existing_scope', changed <= SUMMARY | {LEDGER}
          | {p for p in changed if p.startswith('verification/pr52_claim_merge_20261117/')}, sorted(changed))
    for path in SUMMARY & changed:
        raw = git('show', OLD+':'+path)
        check('history_retained:'+path, (ROOT/path).read_bytes().endswith(raw), 'New prefix only')
    for path in ('params/registry.yaml', 'requirements/system_requirements.md', 'requirements/verification_matrix.md',
                 'verification/r4_force_geometry/claim.json',
                 'verification/r4_cycle_interfaces/proposal/baseline_bindings.json'):
        check('unchanged:'+path, unchanged(path, OLD), path)
    untracked = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
    check('new_file_scope', all(p == LEDGER or p.startswith('verification/pr52_claim_merge_20261117/')
                               for p in untracked), untracked)
    result = dict(checked_at_utc=now.isoformat(), base_main=BASE, original_head=OLD,
                  counts={'PASS': len(checks), 'FAIL': 0}, checks=checks,
                  activation='Not effective until serialized remote main inclusion; original deadline unchanged',
                  new_independent_review=False, engineering_started=False)
    (HERE/'integration_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
