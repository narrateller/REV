"""Check the atomic intake closure / requirements claim transition, not engineering."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = '5674ca6a6c4d8d98eaa9fab953691fd2ac61a2e7'
BASE = 'a63e27cf1e4579bfe8aa7b78f4dfcabbd6ef6dc3'
SID = '6afb300b-1540-8191-a5c4-be1a684c20e0'


def main():
    checks = []
    def read(path): return json.loads((ROOT/path).read_bytes())
    def git(*args): return subprocess.check_output(['git', '-C', str(ROOT), *args])
    def check(name, condition, evidence):
        checks.append(dict(id=name, status='PASS' if condition else 'FAIL', evidence=evidence))
        if not condition: raise AssertionError(name)
    def digest(raw): return hashlib.sha256(raw).hexdigest()
    oldpath = 'coordination/claims/T-r1-force-inputs-intake-01.json'
    newpath = 'coordination/claims/T-r1-requirements-draft-01.json'
    old = read(oldpath); new = read(newpath)
    check('actual_session', os.environ.get('CODEX_SESSION_ID') == SID, SID)
    check('base', git('rev-parse', 'origin/main').decode().strip() == BASE, BASE)
    check('old_record_archive', (HERE/'intake_accepted_ledger_before.json').read_bytes()
          == git('show', BASE+':'+oldpath), 'Original accepted ledger retained')
    check('old_deadline_unchanged', old['lease_expires_at'] == '2026-11-17T23:16:47.225017Z'
          and not old['lease_extension'], old['lease_expires_at'])
    check('old_owner_released', old['owner_session'] == 'NONE' and old['previous_owner_session'] == SID
          and old['status'] == 'COMPLETED_DOCUMENTARY_RELEASED' and not old['lease_active'], old['status'])
    completion = read(old['completion_record'])
    check('completion_scope', completion['status'] == 'DONE_DOCUMENTARY_SCOPE'
          and completion['acceptance'] == 'WARNING_DOCUMENTARY_REFERENCE_ONLY'
          and not completion['engineering_work_completed'] and not completion['source_states_solved'], completion['open_items'])
    check('new_owner', new['owner_session'] == new['session_id'] == SID and new['role'] == 'R1', SID)
    proposed = datetime.fromisoformat(new['proposed_at_utc'])
    expiry = datetime.fromisoformat(new['lease_expires_at'])
    check('new_24h_lease', expiry-proposed == timedelta(hours=24)
          and expiry != datetime.fromisoformat(old['lease_expires_at'].replace('Z', '+00:00'))
          and datetime.now(timezone.utc) < expiry, new['lease_expires_at'])
    check('same_main_transaction', new['predecessor_completion'] == old['completion_record']
          and 'atomically' in new['activation_predicate'] and new['acceptance_PR'] == 53,
          'Before merge only old main claim; after merge only new claim')
    check('user_authority', new['acceptance_authority'] == 'USER_EXPLICIT_INSTRUCTION'
          and read(new['authorization'])['new_claim_lease_hours'] == 24, new['authorization'])
    check('start_gate', new['documentary_execution'] == 'NOT_STARTED'
          and new['input_audit'] == 'NOT_RUN_PENDING_MAIN_ACCEPTANCE'
          and not new['numerical_physical_CAD_stage_authorized'], new['scope'])
    task = read('coordination/tasks/T-r1-requirements-draft-01/task.json')
    check('task_owner_gate', task['owner_session'] == SID and task['lease_expires_at'] == new['lease_expires_at']
          and task['documentary_execution'] == 'NOT_STARTED', task['execution_gate'])
    for item in read('coordination/tasks/T-r1-requirements-draft-01/task_input_manifest.json')['inputs']:
        check('pin:'+item['path'], digest((ROOT/item['path']).read_bytes()) == item['sha256'], item['sha256'])
    for item in read('verification/r5_reference_intake_review/validation.json')['package_files']:
        check('R5_seal:'+item['path'], digest((ROOT/item['path']).read_bytes()) == item['sha256'], item['sha256'])
    for path in git('ls-tree', '-r', '--name-only', 'f2cbd96bb78c915dca74cb4eb29daffbb52ee172',
                    'verification/r1_force_inputs_intake').decode().splitlines():
        check('source:'+path, git('rev-parse', OLD+':'+path)
              == git('rev-parse', 'f2cbd96bb78c915dca74cb4eb29daffbb52ee172:'+path), path)
    summary = {'ISSUES_AND_TASKS.md', 'STATE.md', 'NEXT_MODEL.md',
               'handoffs/T-r1-force-inputs-intake-01/'+SID+'.md',
               'handoffs/T-r1-requirements-draft-01/'+SID+'.md'}
    allowed = summary | {oldpath, newpath, 'coordination/tasks/T-r1-requirements-draft-01/task.json'}
    changed = git('diff', OLD, '--name-only').decode().splitlines()
    check('changed_existing_scope', all(p in allowed or p.startswith(('verification/r1_requirements_claim_20261117/',
          'coordination/completions/')) for p in changed), changed)
    for p in summary & set(changed):
        check('history:'+p, (ROOT/p).read_bytes().endswith(git('show', OLD+':'+p)), 'Prefix only')
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), base_main=BASE,
                  original_head=OLD, counts={'PASS': len(checks), 'FAIL': 0}, checks=checks,
                  main_transition_pending=True, overlapping_accepted_ownership=False,
                  draft_editing_started=False, engineering_started=False)
    (HERE/'transition_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result['counts']))


if __name__ == '__main__': main()
