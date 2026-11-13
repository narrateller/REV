"""R4 documentary regressions for R5-CI-B01/B02/B03; no physical assertions."""
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / 'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0, str(P))
from document_semantics import FILL_SCOPE, FILL_REVISIONS, FEEDER_GUARDS, fill_value, conjunction, entry_outcome

C = json.loads((ROOT / 'verification/r4_cycle_contract/contract.json').read_text())
D = json.loads((P / 'permissions.json').read_text())
A = {a['id']: a for a in D['actions']}
spec = importlib.util.spec_from_file_location('frozen_history', ROOT / 'verification/r4_cycle_contract/permission_examples.py')
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)


def hashes(folder):
    return {str(f.relative_to(folder)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in folder.rglob('*') if f.is_file() and '__pycache__' not in f.parts}


def run(*args):
    return subprocess.run([sys.executable, '-B', *map(str, args)], capture_output=True, text=True, cwd=ROOT)


class ExportSemantics(unittest.TestCase):
    def test_fresh_exports_repeat_and_readonly(self):
        before = hashes(P)
        with tempfile.TemporaryDirectory() as tmp:
            dirs = [Path(tmp) / 'one', Path(tmp) / 'two']
            for out in dirs:
                result = run(P / 'render_schemes.py', '--output-dir', out)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(hashes(dirs[0]), hashes(dirs[1]))
            self.assertEqual(hashes(dirs[0]), hashes(P / 'exports'))
        results = [run(P / 'check_package.py') for _ in range(2)]
        self.assertTrue(all(r.returncode == 0 for r in results), [r.stdout for r in results])
        self.assertEqual(results[0].stdout, results[1].stdout)
        self.assertEqual(before, hashes(P))

    def test_reexported_semantic_mutations_are_rejected_without_writes(self):
        cases = ['unknown_pose', 'work_starts_at_P0', 'drop_isolation_guard',
                 'cross_scenario_work_binding', 'wrong_parent_mode', 'unsupported_startup_mode',
                 'cross_scenario_phase_ref', 'dropped_phase_ref', 'wrong_phase_value',
                 'wrong_pose_source', 'missing_dose_scope', 'dropped_fill_confirm',
                 'dropped_fill_before_isolate', 'dropped_committed_load', 'dropped_fill_before_return',
                 'parent_still_requires_D1', 'bad_sequence_order', 'recovery_dependency_deadlock',
                 'recovery_clears_other_faults', 'drop_recovery_sweep', 'reduced_rod',
                 'reduced_work_force', 'shortened_work_stroke', 'csv_guard_corruption',
                 'svg_semantic_corruption', 'md_mode_corruption', 'cyclic_guard_dependency', 'bad_commit_successor']
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix='r4-reexport-') as tmp:
                dest = Path(tmp);pack = dest / 'proposal'
                shutil.copytree(P, pack)
                for name in ['claim.json', 'input_manifest.json']:
                    shutil.copy(P.parent / name, dest / name)
                data = deepcopy(D);acts = {a['id']: a for a in data['actions']}
                work = acts['A-MECH-WORK']
                if case == 'unknown_pose': work['poses']['punch'] = 'UNDEFINED_POSE→P2'
                elif case == 'work_starts_at_P0':
                    work['poses']['punch'] = 'P0→P2';work['pose_endpoints']['punch']['start'] = ['P0']
                elif case == 'drop_isolation_guard': work['extra_entry_guards'].remove('G_ISOLATED_CURRENT')
                elif case == 'cross_scenario_work_binding':
                    r = next(r for r in acts['A-COMPACT']['source_bindings'] if r['proposed_cad_field'] == 'stroke.work')
                    r.update(parameter_id='R3_BASE_B_WORK_STROKE', source='verification/r3_parametric_sizing/results/BASE_B.json')
                elif case == 'wrong_parent_mode':
                    acts['B-MECH-WORK']['parent_action_choices'] = ['A-COMPACT']
                    acts['B-MECH-WORK']['current_parent_guards'] = {'A-COMPACT': []}
                elif case == 'unsupported_startup_mode': work['mode'].append('A_STARTUP')
                elif case in ['cross_scenario_phase_ref', 'wrong_phase_value', 'dropped_phase_ref']:
                    refs = work['resources']['source_main_axis_phase_refs']
                    if case == 'dropped_phase_ref': refs.pop()
                    elif case == 'wrong_phase_value': refs[0]['value'] *= 0.5
                    else: refs[0]['source'] = 'verification/r3_power_reconcile/results/BASE_B.json'
                elif case == 'missing_dose_scope': work = acts['A-MECH-FILL-CONFIRM'];work['fill_binding']['scope_fields'].remove('dose_id')
                elif case == 'dropped_fill_confirm': acts['A-MECH-FILL-CONFIRM']['extra_completion_guards'].remove('FILL_COMPLETE')
                elif case == 'dropped_fill_before_isolate': acts['A-MECH-FEED-ISOLATE']['extra_entry_guards'].remove('FILL_COMPLETE')
                elif case == 'dropped_committed_load': acts['A-MECH-FEED-ISOLATE']['extra_entry_guards'].remove('LOAD_COMMITTED_CURRENT')
                elif case == 'dropped_fill_before_return': acts['A-MECH-DOSER-RETURN']['extra_entry_guards'].remove('FILL_COMPLETE')
                elif case == 'parent_still_requires_D1': acts['A-LOAD-START']['extra_completion_guards'].append('D_DELIVERY_CURRENT')
                elif case == 'recovery_dependency_deadlock': acts['B-MECH-STOP-CLOSE']['entry_guards'].append('DEPENDENCY_VALID')
                elif case == 'recovery_clears_other_faults': acts['B-MECH-RELOCK']['recovery_binding']['clears_faults_automatically'] = True
                elif case == 'drop_recovery_sweep': acts['B-MECH-STOP-CLOSE']['extra_entry_guards'].remove('RESET_SWEEP_CLEAR')
                (pack / 'permissions.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
                if case in ['wrong_pose_source', 'bad_sequence_order']:
                    name = 'poses.json' if case == 'wrong_pose_source' else 'cycle_protocol.json'
                    obj = json.loads((pack / name).read_text())
                    if case == 'wrong_pose_source': obj['source_refs'][0]['source'] = 'wrong.json'
                    else: obj['load_sequences'][0]['stages'][1:3] = reversed(obj['load_sequences'][0]['stages'][1:3])
                    (pack / name).write_text(json.dumps(obj))
                if case in ['cyclic_guard_dependency', 'bad_commit_successor']:
                    name = 'mechanical_guards.json' if case == 'cyclic_guard_dependency' else 'cycle_protocol.json'
                    obj = json.loads((pack / name).read_text())
                    if case == 'cyclic_guard_dependency':obj['guard_dependencies']['G_ISOLATED_CURRENT'].append('G_ISOLATED_CURRENT')
                    else:obj['fill']['commit_successor']['increment'] = 0
                    (pack / name).write_text(json.dumps(obj))
                if case in ['reduced_rod', 'reduced_work_force', 'shortened_work_stroke']:
                    obj = json.loads((pack / 'baseline_bindings.json').read_text())
                    field = {'reduced_rod':'cylinder.rod_diameter', 'reduced_work_force':'load.work_peak', 'shortened_work_stroke':'stroke.work'}[case]
                    next(r for r in obj['rows'] if r['scenario'] == 'BASE_A' and r['proposed_cad_field'] == field)['value'] *= 0.5
                    (pack / 'baseline_bindings.json').write_text(json.dumps(obj))
                result = run(pack / 'render_schemes.py', '--output-dir', pack / 'exports')
                self.assertEqual(result.returncode, 0, result.stderr)
                if case in ['csv_guard_corruption', 'svg_semantic_corruption', 'md_mode_corruption']:
                    name, old, new = {'csv_guard_corruption':('positions_permissions.csv','G_ISOLATED_CURRENT','G_OPEN_CURRENT'),
                        'svg_semantic_corruption':('interface_A.svg','FILL_COMPLETE','COMMAND_COMPLETE'),
                        'md_mode_corruption':('positions_permissions.md','A_STEADY','A_STARTUP')}[case]
                    target = pack / 'exports' / name
                    target.write_text(target.read_text().replace(old, new, 1))
                    manifest = json.loads((pack / 'exports/exports_manifest.json').read_text())
                    manifest['exports_sha256'][name] = hashlib.sha256(target.read_bytes()).hexdigest()
                    (pack / 'exports/exports_manifest.json').write_text(json.dumps(manifest))
                before = hashes(pack)
                result = run(P / 'check_package.py', '--package', pack)
                self.assertNotEqual(result.returncode, 0, case + ':' + result.stdout)
                report = json.loads(result.stdout)
                self.assertEqual(report['document_checks'], 'MISMATCH')
                self.assertTrue(report['reason'].startswith(('semantic:', 'all44_exact_source_rows')), report)
                self.assertEqual(hashes(pack), before)


class FillProtocol(unittest.TestCase):
    def fixture(self, action='A-REFILL', mode='A_STARTUP', dose='dose-2'):
        ctx = {key:'synthetic-' + key for key in FILL_SCOPE}
        ctx.update(variant=action[0], mode=mode, load_action=action, dose_id=dose,
                   revisions={k: 0 for k in FILL_REVISIONS})
        receipt = dict(deepcopy(ctx), value='TRUE', invalidated=False, confirmation_kind='OBSERVED_TRANSFER_COMPLETE',
                       transfer_pose='D1', dose_delivered='TRUE', evidence_id='synthetic-receipt', source='synthetic only',
                       method='ASSUMED_FIXTURE', valid_for_consumer_interval=True)
        return ctx, receipt

    def test_all_load_modes_D0_D1_confirmation_D0_commit_then_isolate(self):
        for name in ['A-LOAD-START','A-LOAD-STEADY','A-REFILL','B-LOAD','B-REFILL']:
            for mode in A[name]['mode']:
                with self.subTest(action=name, mode=mode):
                    ctx, receipt = self.fixture(name, mode)
                    self.assertEqual(fill_value(receipt, ctx), 'TRUE')
                    # Completion in D0 needs the historical D1 receipt, not current D1.
                    guards = {'CONTINUOUS_MECHANISM':'TRUE', 'D_HOME_CURRENT':'TRUE', 'FILL_COMPLETE':fill_value(receipt,ctx), 'DOSE_DELIVERED':'TRUE'}
                    self.assertEqual(conjunction(guards[g] for g in A[name]['completion_guards'] + A[name]['extra_completion_guards']), 'ALLOWED_ASSUMED')
                    self.assertEqual(fill_value(receipt,ctx,True), 'UNKNOWN')
                    origin = deepcopy(ctx['revisions'])
                    for field in ['material','feed']:ctx['revisions'][field] += 1
                    ctx['load_commit'] = dict({k:ctx[k] for k in FILL_SCOPE}, revisions=deepcopy(ctx['revisions']),
                        origin_revisions=origin, changed_domains=['material','feed'],
                        value='TRUE', boundary='AFTER_DOSER_RETURN', receipt_id=receipt['evidence_id'], current_doser='D0')
                    self.assertEqual(fill_value(receipt,ctx,True), 'TRUE')
                    stale = deepcopy(ctx);stale['revisions']['resource'] += 1
                    self.assertEqual(fill_value(receipt,stale,True), 'UNKNOWN')
                    borrowed = deepcopy(ctx);borrowed['load_commit']['load_operation_id'] = 'other-load'
                    self.assertEqual(fill_value(receipt,borrowed,True), 'UNKNOWN')
                    isolate = A[name[0] + '-MECH-FEED-ISOLATE']
                    values = {g:'TRUE' for g in isolate['entry_guards'] + isolate['extra_entry_guards']}
                    parent = name[0] + ('-GATHER' if mode in ['A_STARTUP','B_REPEAT'] else '-COMPACT')
                    values.update({g:'TRUE' for g in isolate['current_parent_guards'][parent]})
                    values.update({g:'TRUE' for g in FEEDER_GUARDS})
                    values['FILL_COMPLETE'] = fill_value(receipt,ctx,True)
                    self.assertEqual(entry_outcome(isolate, values, parent), 'ALLOWED_ASSUMED')
                    values['D_PATH_CLEAR'] = 'FALSE'
                    self.assertEqual(entry_outcome(isolate, values, parent), 'BLOCKED')

    def test_address_revision_and_refill_receipt_reuse(self):
        ctx, receipt = self.fixture()
        for key in FILL_SCOPE:
            wrong = deepcopy(ctx);wrong[key] += '-different'
            self.assertEqual(fill_value(receipt, wrong), 'UNKNOWN', key)
        for key in FILL_REVISIONS:
            wrong = deepcopy(ctx);wrong['revisions'][key] += 1
            self.assertEqual(fill_value(receipt, wrong), 'UNKNOWN', key)
        for key, value in [('method','COMMAND'), ('confirmation_kind','TIMER_EXPIRED'), ('dose_delivered','UNKNOWN'),
                           ('valid_for_consumer_interval',False), ('transfer_pose','D0')]:
            wrong = deepcopy(receipt);wrong[key] = value
            self.assertEqual(fill_value(wrong,ctx), 'UNKNOWN', key)
        wrong_mode, wrong_receipt = self.fixture('A-REFILL','A_STEADY')
        self.assertEqual(fill_value(wrong_receipt,wrong_mode), 'UNKNOWN')
        # Same batch/retained material with a new dose still requires a new receipt.
        again = deepcopy(ctx);again['dose_id'] = 'dose-3';again['load_operation_id'] = 'new-refill'
        self.assertEqual(fill_value(receipt,again), 'UNKNOWN')
        invalid = deepcopy(receipt);invalid['invalidated'] = True
        self.assertEqual(fill_value(invalid,ctx), 'FALSE')

    def test_false_unknown_truth_table(self):
        for fill, safe, isolated in itertools.product(['TRUE','FALSE','UNKNOWN'], repeat=3):
            expected = 'BLOCKED' if 'FALSE' in [fill,safe,isolated] else ('INDETERMINATE' if 'UNKNOWN' in [fill,safe,isolated] else 'ALLOWED_ASSUMED')
            self.assertEqual(conjunction([fill,safe,isolated]), expected)
        ctx, receipt = self.fixture();receipt['value'] = 'FALSE'
        self.assertEqual(conjunction([fill_value(receipt,ctx), 'UNKNOWN']), 'BLOCKED')
        self.assertEqual(conjunction([fill_value(None,ctx), 'TRUE']), 'INDETERMINATE')


def evidence(ctx, action, guard, phase=None):
    t = L.spec(C, action)
    return dict({k:ctx[k] for k in C['evidence_policy']['scope_fields'] + ['operation_id']},
        value='TRUE', action=action, guard=guard, phase=phase or ('COMPLETION' if guard in t['completion_guards'] else 'ENTRY'),
        evidence_id='ASSUMED-' + action + '-' + guard, method='ASSUMED_FIXTURE', source='synthetic documentary test only',
        valid_for_operation_interval=True, revisions=deepcopy(ctx['revisions']))


def prepare(ctx, action, operation):
    ctx = deepcopy(ctx);ctx['operation_id'] = operation
    ctx['evidence'] = {g:evidence(ctx,action,g) for g in L.spec(C,action)['required_guards']}
    return ctx


def fault_context():
    ctx = dict(scenario_id='SYNTHETIC-B', variant='B', mode='B_REPEAT', state='B_RECEIVED_RESIDUAL',
        subject_id='closure-subject', batch_id='same-batch', cycle_epoch='same-epoch', basis_id='basis', basis_revision='r1',
        operation_id='denied-next', revisions={d:0 for d in C['evidence_policy']['domains']},
        inventory_refs=['retained-residue'], pending_observations=[])
    ctx = L.initialize_history(ctx,'test-history',dict(value='TRUE',evidence_id='ASSUMED-start',source='synthetic audit'))
    ctx = prepare(ctx,'B-NEXT','denied-next');ctx['evidence']['B_RESET_CONFIRMED']['value'] = 'FALSE'
    ctx, outcome = L.decide(C,'B-NEXT',ctx)
    assert outcome['permission_outcome'] == 'BLOCKED'
    return ctx


def recover_one(ctx, action, fault_id, operation):
    ctx = prepare(ctx,action,operation);fault = ctx['faults'][fault_id];guard = fault['origin']['guard']
    proof = evidence(ctx, action, guard, 'RECOVERY_RESULT')
    proof.update(fault_id=fault_id, target_scope=deepcopy(fault['origin']['scope']),
                 origin_revisions=deepcopy(fault['origin']['revisions']), revisions=deepcopy(fault['expected_revisions']))
    return L.recover(C,action,ctx,fault_id,proof)


class RecoveryProtocol(unittest.TestCase):
    def test_fault_closure_targeted_recovery_then_separate_history_and_new_next(self):
        ctx = fault_context();rejected = deepcopy(ctx['rejected_operations'])
        ctx = prepare(ctx,'B-RESET','new-restore')
        self.assertEqual(L.evaluate(C,'B-RESET',ctx,'ENTRY')['permission_outcome'], 'ALLOWED_ASSUMED')
        self.assertEqual(L.evidence_value(C,'B-RESET','DEPENDENCY_VALID',ctx,None,'ENTRY')[0], 'FALSE')
        for child in ['B-MECH-STOP-CLOSE','B-MECH-RELOCK']:
            a = A[child];values = {g:'TRUE' for g in a['entry_guards'] + a['extra_entry_guards'] + a['current_parent_guards']['B-RESET']}
            values['DEPENDENCY_VALID'] = 'FALSE'
            self.assertEqual(entry_outcome(a,values,'B-RESET'), 'ALLOWED_ASSUMED')
            for g in ['RESET_SWEEP_CLEAR','RESOURCES_READY','LEDGER_VALID','MATERIAL_HELD_CURRENT','RECOVERY_SCOPE_VALID']:
                for value, expected in [('FALSE','BLOCKED'),('UNKNOWN','INDETERMINATE')]:
                    wrong = dict(values);wrong[g] = value
                    self.assertEqual(entry_outcome(a,wrong,'B-RESET'), expected, (child,g,value))
        closure = L.open_faults(ctx,'B_RESET_CONFIRMED')[0]['fault_id']
        ctx, result = recover_one(ctx,'RESTORE_B_CLOSURE',closure,'addressed-closure-result')
        self.assertEqual(result,'ALLOWED_ASSUMED')
        # Closure evidence cannot implicitly clear the independent history fault.
        self.assertTrue(L.open_faults(ctx,'DEPENDENCY_VALID'))
        before_reconcile = prepare(ctx,'B-NEXT','fresh-but-unreconciled')
        self.assertEqual(L.evaluate(C,'B-NEXT',before_reconcile)['permission_outcome'], 'BLOCKED')
        ctx = prepare(ctx,'B-RESET','commit-restored-closure')
        ctx, result = L.decide(C,'B-RESET',ctx)
        self.assertEqual(result['permission_outcome'],'ALLOWED_ASSUMED')
        for i, fault in enumerate(L.open_faults(ctx,'DEPENDENCY_VALID')):
            ctx, result = recover_one(ctx,'RECONCILE_HISTORY',fault['fault_id'],'history-' + str(i))
            self.assertEqual(result,'ALLOWED_ASSUMED')
        ctx = prepare(ctx,'B-NEXT','new-next-after-reconciliation')
        self.assertEqual(L.evaluate(C,'B-NEXT',ctx)['permission_outcome'], 'ALLOWED_ASSUMED')
        self.assertEqual(ctx['rejected_operations'], rejected)
        self.assertEqual(ctx['inventory_refs'], ['retained-residue'])
        ctx = prepare(ctx,'B-NEXT','denied-next')
        self.assertEqual(L.evaluate(C,'B-NEXT',ctx)['permission_outcome'], 'BLOCKED')

    def test_unrelated_resource_and_material_faults_survive_closure_recovery(self):
        for guard in ['RESOURCES_READY','LEDGER_VALID']:
            with self.subTest(guard=guard):
                ctx = fault_context()
                ctx = prepare(ctx,'B-RETURN','denied-return-' + guard);ctx['evidence'][guard]['value'] = 'FALSE'
                ctx, result = L.decide(C,'B-RETURN',ctx)
                self.assertEqual(result['permission_outcome'],'BLOCKED')
                closure = L.open_faults(ctx,'B_RESET_CONFIRMED')[0]['fault_id']
                ctx, result = recover_one(ctx,'REASSESS_B_CLOSURE',closure,'audit-closure-' + guard)
                self.assertEqual(result,'ALLOWED_ASSUMED')
                self.assertTrue(L.open_faults(ctx,guard))
                deps = L.open_faults(ctx,'DEPENDENCY_VALID')
                blocked = []
                for i, dep in enumerate(deps):
                    _, result = recover_one(ctx,'RECONCILE_HISTORY',dep['fault_id'],'try-history-' + str(i))
                    blocked.append(result)
                self.assertIn('BLOCKED',blocked)
                fresh = prepare(ctx,'B-COMPACT','ordinary-work-' + guard);fresh['state'] = 'B_BATCH_SELECTED'
                self.assertEqual(L.evaluate(C,'B-COMPACT',fresh,'ENTRY')['permission_outcome'],'BLOCKED')


if __name__ == '__main__':
    unittest.main()
