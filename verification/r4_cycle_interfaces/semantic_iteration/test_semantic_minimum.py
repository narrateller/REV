"""Arbitration regression plan: stage families and coherent re-exported mutants."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / 'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0, str(P))
import semantic_minimum as S
N = S.minimum()
PAYLOAD = json.loads((P / 'permissions.json').read_text())
POSES = json.loads((P / 'poses.json').read_text())
RESULTS = []


def hashes(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class MinimumRegression(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        target = os.environ.get('REV_CI_CAPTURE')
        if target: write(Path(target), {'cases': RESULTS, 'count': len(RESULTS), 'all_matched': all(r['matched'] for r in RESULTS)})

    def case(self, name, change, expected='SEMANTIC_MISMATCH'):
        with tempfile.TemporaryDirectory(prefix='rev-b03-schema-') as temp:
            folder = Path(temp);pack = folder / 'proposal';shutil.copytree(P, pack)
            for f in ['claim.json', 'input_manifest.json']: shutil.copy(P.parent / f, folder / f)
            data = deepcopy(PAYLOAD);poses = deepcopy(POSES)
            change(data, poses)
            write(pack / 'permissions.json', data);write(pack / 'poses.json', poses)
            generated = subprocess.run([sys.executable, '-B', str(pack / 'render_schemes.py'), '--output-dir', str(pack / 'exports')], capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, (name, generated.stderr))
            manifest = json.loads((pack / 'exports/exports_manifest.json').read_text())
            before = hashes(pack)
            self.assertTrue(all(before[n] == h for n,h in manifest['sources_sha256'].items()))
            self.assertTrue(all(before['exports/' + n] == h for n,h in manifest['exports_sha256'].items()))
            run = subprocess.run([sys.executable, '-B', str(P / 'check_package.py'), '--package', str(pack)], capture_output=True, text=True)
            report = json.loads(run.stdout)
            unchanged = before == hashes(pack)
            observed = report.get('semantic_outcome')
            matched = observed == expected and (run.returncode == 0) == (expected == 'MATCH') and unchanged
            RESULTS.append({'id': name, 'expected': expected, 'observed': observed, 'exit_code': run.returncode,
                'matched': matched, 'coherent_reexport': True, 'hashes_fresh': True, 'checker_writes': not unchanged,
                'reason': report.get('reason'), 'verification_gate': report.get('verification_gate')})
            self.assertTrue(matched, RESULTS[-1])

    def test_six_R5_substitutions(self):
        def mutate(name):
            def apply(d,p):
                a = {r['id']: r for r in d['actions']}
                if name == 'P1-coordinate': next(r for r in p['poses'] if r['id'] == 'P1')['coordinate'] = 'x_P0 + S_eject'
                elif name == 'feed-open-without-path': a['A-MECH-FEED-OPEN']['extra_entry_guards'].remove('G_PATH_CLEAR')
                elif name == 'return-without-doser-path': a['A-MECH-DOSER-RETURN']['extra_entry_guards'].remove('D_PATH_CLEAR')
                elif name == 'confirm-without-current-D1':
                    for key in ['extra_entry_guards', 'extra_completion_guards']: a['A-MECH-FILL-CONFIRM'][key].remove('D_DELIVERY_CURRENT')
                elif name == 'recovery-any-fault': a['B-MECH-STOP-CLOSE']['recovery_binding']['target_fault_id'] = 'ANY_FAULT'
                elif name == 'relock-without-lock-result':
                    for g in ['LOCK_CLOSED_CURRENT','B_STOP_LOCK_CLOSED']: a['B-MECH-RELOCK']['extra_completion_guards'].remove(g)
            return apply
        for name in ['P1-coordinate','feed-open-without-path','return-without-doser-path','confirm-without-current-D1','recovery-any-fault','relock-without-lock-result']:
            with self.subTest(name=name): self.case('R5:' + name, mutate(name))

    def test_all_stage_modes_entry_and_terminal_outputs(self):
        for name, rule in N['actions'].items():
            for mode in rule['modes']:
                # Exercise every declared stage/mode, including different stages
                # in the same family, rather than only the six historical IDs.
                candidates = [g for g in rule['entry_minimum'] if 'PATH' in g or 'SWEEP' in g]
                guard = candidates[0] if candidates else rule['entry_minimum'][0]
                def drop_entry(d,p,name=name,guard=guard):
                    a = next(a for a in d['actions'] if a['id'] == name)
                    for field in ['entry_guards','extra_entry_guards']:
                        a[field] = [g for g in a[field] if g != guard]
                with self.subTest(stage=name, mode=mode, field='entry'): self.case('ENTRY:' + name + ':' + mode + ':' + guard, drop_entry)
                def drop_output(d,p,name=name):
                    next(a for a in d['actions'] if a['id'] == name)['outputs'].pop()
                with self.subTest(stage=name, mode=mode, field='output'): self.case('OUTPUT:' + name + ':' + mode, drop_output)
                if rule['parents']:
                    def wrong_mode_parent(d,p,name=name,mode=mode):
                        next(a for a in d['actions'] if a['id'] == name)['mode_parent_bindings'][mode] = []
                    with self.subTest(stage=name,mode=mode,field='parent'): self.case('MODE_PARENT:' + name + ':' + mode,wrong_mode_parent)
                if rule['completion_exact']:
                    guard = rule['completion_exact'][-1]
                    def drop_completion(d,p,name=name,guard=guard):
                        a = next(a for a in d['actions'] if a['id'] == name)
                        for field in ['completion_guards','extra_completion_guards']:
                            a[field] = [g for g in a[field] if g != guard]
                    with self.subTest(stage=name, mode=mode, field='completion'): self.case('COMMIT:' + name + ':' + mode + ':' + guard, drop_completion)

    def test_each_coordinate_operand_and_scenario_source(self):
        def leaves(node, path=()):
            if node['op'] in ['symbol','phase_stroke']: yield path
            elif node['op'] == 'sum':
                for i,term in enumerate(node['terms']): yield from leaves(term, path + ('terms',i))
            elif node['op'] == 'neg': yield from leaves(node['operand'], path + ('operand',))
        for pose in POSES['poses']:
            for scenario, form in pose['coordinate_forms'].items():
                for path in leaves(form['expression']):
                    def change(d,p,id=pose['id'],scenario=scenario,path=path):
                        node = next(r for r in p['poses'] if r['id'] == id)['coordinate_forms'][scenario]['expression']
                        for key in path: node = node[key]
                        if node['op'] == 'symbol': node['id'] = 'y_D0' if node['id'] != 'y_D0' else 'x_P0'
                        else:
                            phase = 'eject' if node['phase'] != 'eject' else 'work'
                            expr = S.Expressions(N, {r['id']:r for r in POSES['poses']})
                            node.update(phase=phase, source_ref=deepcopy(expr.refs[(scenario,phase)]))
                    with self.subTest(pose=pose['id'],scenario=scenario,operand=path): self.case('OPERAND:' + pose['id'] + ':' + scenario + ':' + str(path), change)
        for scenario in ['BASE_A','BASE_B']:
            for phase, pose in [('approach','P1'),('work','P2'),('eject','P3'),('return','P_RETURN_END')]:
                def foreign(d,p,scenario=scenario,phase=phase,pose=pose):
                    node = next(x for x in p['poses'] if x['id'] == pose)['coordinate_forms'][scenario]['expression']
                    def visit(n):
                        if n['op'] == 'phase_stroke' and n['phase'] == phase:
                            other = 'BASE_B' if scenario == 'BASE_A' else 'BASE_A'
                            n['source_ref'] = deepcopy(S.Expressions(N, {r['id']:r for r in POSES['poses']}).refs[(other,phase)])
                        for term in n.get('terms',[]): visit(term)
                        if 'operand' in n: visit(n['operand'])
                    visit(node)
                with self.subTest(scenario=scenario,phase=phase): self.case('CROSS_SCENARIO:' + scenario + ':' + phase, foreign)
        for name,rule in N['actions'].items():
            if not rule['phase_pose_bindings']: continue
            def change(d,p,name=name):
                a=next(r for r in d['actions'] if r['id']==name)
                a['phase_pose_bindings'][0]['scenario']='BASE_B' if a['variant']=='A' else 'BASE_A'
            with self.subTest(action=name):self.case('ACTION_PHASE_POSE_LINK:' + name,change)

    def test_formula_bases_normalization_and_unknown_support(self):
        def set_pose(field, value):
            def change(d,p): next(r for r in p['poses'] if r['id'] == 'P2')[field] = value
            return change
        self.case('formula_label_disagrees', set_pose('display_formula','P1 + S_eject'))
        self.case('equivalent_coordinate', set_pose('coordinate','S_work + (S_approach + x_P0)'), 'MATCH')
        self.case('unsupported_multiply', set_pose('coordinate','2 * x_P0'), 'UNSUPPORTED')
        self.case('unsupported_call', set_pose('display_formula','unknown(P1)'), 'UNSUPPORTED')
        for value,kind in [(None,'INPUT_ERROR'),('DOSER_DATUM','SEMANTIC_MISMATCH')]:
            def base(d,p,value=value): next(r for r in p['poses'] if r['id'] == 'P1')['coordinate_forms']['BASE_A']['frame'] = value
            self.case('bad_frame:' + str(value),base,kind)
        def no_base(d,p): p['coordinate_base'] = None
        self.case('null_global_base',no_base,'INPUT_ERROR')
        def coherent(d,p):
            r=next(x for x in p['poses'] if x['id']=='P1');r['coordinate']='x_P0 + S_eject';r['display_formula']='P0 + S_eject'
            expr=S.Expressions(N,{r['id']:r for r in POSES['poses']})
            for scenario, form in r['coordinate_forms'].items():form['expression']['terms'][1]={'op':'phase_stroke','phase':'eject','source_ref':deepcopy(expr.refs[(scenario,'eject')])}
        self.case('simultaneous_JSON_CSV_SVG_formula_and_hashes',coherent)
        def unsupported(d,p): d['actions'][0]['unmodeled_extension'] = 'UNKNOWN'
        self.case('unknown_action_field',unsupported,'UNSUPPORTED')
        def extra(d,p): d['actions'][0]['outputs'].append({'id':'PHYSICAL_READY','actual':'TRUE'})
        self.case('extra_output',extra)

    def test_recovery_binding_schema_all_targets_and_helpers(self):
        for action in ['B-MECH-STOP-CLOSE','B-MECH-RELOCK']:
            for field,value in [('target_fault_id',None),('target_fault_id','F-'+'f'*64),('target_fault_id','*'),
                                ('target_scope',None),('target_scope',{'binding':'foreign_fault.origin.scope'}),
                                ('target_guard','LEDGER_VALID'),('request_action','RECONCILE_HISTORY'),
                                ('result_type','COMMAND_COMPLETE')]:
                def change(d,p,action=action,field=field,value=value): next(r for r in d['actions'] if r['id']==action)['recovery_binding'][field] = value
                with self.subTest(action=action,field=field,value=value):self.case('RECOVERY_BINDING:' + action + ':' + field + ':' + str(value),change)

    def test_concrete_recovery_scope_uses_frozen_faults_without_clearing(self):
        sys.path.insert(0,str(P.parent/'correction'));import test_documentary as old
        ctx=old.prepare(old.fault_context(),'RESTORE_B_CLOSURE','fresh-exact-recovery')
        fault=old.L.open_faults(ctx,'B_RESET_CONFIRMED')[0]
        proof=old.evidence(ctx,'RESTORE_B_CLOSURE','B_RESET_CONFIRMED','RECOVERY_RESULT')
        proof.update(fault_id=fault['fault_id'],target_scope=deepcopy(fault['origin']['scope']),
                     origin_revisions=deepcopy(fault['origin']['revisions']),revisions=deepcopy(fault['expected_revisions']))
        before=deepcopy(ctx)
        self.assertEqual(S.recovery_value(proof,ctx,old.C),'TRUE')
        for field,value in [('fault_id',None),('fault_id','ANY_FAULT'),('fault_id','F-'+'0'*64),
                            ('target_scope',None),('origin_revisions',{}),('guard','LEDGER_VALID'),
                            ('action','RECONCILE_HISTORY'),('phase','ENTRY')]:
            bad=deepcopy(proof);bad[field]=value
            with self.subTest(field=field,value=value):self.assertIn(S.recovery_value(bad,ctx,old.C),['UNKNOWN','FALSE'])
        denied=deepcopy(ctx);denied['operation_id']='denied-next'
        self.assertEqual(S.recovery_value(proof,denied,old.C),'FALSE')
        self.assertEqual(ctx,before)
        self.assertTrue(old.L.open_faults(ctx,'DEPENDENCY_VALID'))


if __name__ == '__main__': unittest.main()
