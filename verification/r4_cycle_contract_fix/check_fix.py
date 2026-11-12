#!/usr/bin/env python3
"""Readonly documentary regressions; stdout is a report, nonzero on mismatch.

--baseline reproduces the unchanged independent probe against the old immutable
document blobs in a temporary directory. Its zero exit records OLD failures.
"""
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SRC=ROOT/'verification/r4_cycle_contract'
OLD='3cf32daef67a91f393b808adb0dc07ba4c73cac2'
REVIEW='d99afb4c3231d641d4a4921f39987264ce5ffc23'


def module(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def baseline():
    with tempfile.TemporaryDirectory(prefix='rev-cycle-old-docs-') as tmp:
        root=Path(tmp)
        files=['verification/r4_cycle_contract/'+n for n in ['contract.json','check_documents.py','transition_examples.json','sequence_examples.json','resources.json']]
        files+=['verification/r5_r4_cycle_contract_review/independent_probe.py']
        for path in files:
            commit=REVIEW if 'independent_probe.py' in path else OLD
            dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT))
        r=subprocess.run([sys.executable,'-B',str(root/files[-1])],capture_output=True,text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        expected=json.loads((ROOT/'verification/r5_r4_cycle_contract_review/independent_results.json').read_text())
        assert json.loads(r.stdout)==expected
        print(r.stdout,end='')


def main():
    if sys.argv[1:]==['--baseline']:
        baseline();return
    if sys.argv[1:]: raise ValueError('only --baseline or no arguments supported')
    c=json.loads((SRC/'contract.json').read_text())
    audit=json.loads((HERE/'input_audit.json').read_text())
    actual_tree=subprocess.check_output(['git','rev-parse','HEAD:verification/r5_r4_cycle_contract_review'],cwd=ROOT,text=True).strip()
    assert actual_tree==audit['review_tree']
    assert not subprocess.check_output(['git','diff',REVIEW,'--','verification/r5_r4_cycle_contract_review'],cwd=ROOT)
    ts={t['id']:t for t in c['transitions']}
    original=json.loads(subprocess.check_output(['git','show',OLD+':verification/r4_cycle_contract/contract.json'],cwd=ROOT))
    for t in original['transitions']:
        assert set(t['required_guards']) <= set(ts[t['id']]['required_guards']), 'Original condition removed: '+t['id']
    author=module('document_checker',SRC/'check_documents.py')
    logic=module('permission_examples',SRC/'permission_examples.py')
    old=json.loads((ROOT/'verification/r5_r4_cycle_contract_review/independent_results.json').read_text())
    cases=[]
    for case in old['independent_cases']:
        t=ts[case['action']]
        guards={g:case['context_overrides'].get(g,'TRUE') for g in t['required_guards']}
        actual=author.classify(t,case['before'],guards)
        cases.append(dict(id=case['id'],action=case['action'],before=case['before'],guard_values=guards,old_actual=case['actual'],expected=case['expected_correct'],actual=actual,matches=actual==case['expected_correct']))
    combinations=[]
    for tid,fields in [('A-EJECT',['RECEIVER_DEFINED','RESOURCES_READY','PARTITION_DEFINED']),('B-COMPACT',['B_RESET_CONFIRMED','RESOURCES_READY']),('A-STARTUP-RETURN-A_COLUMN_ESTABLISHED',['RETAINED_STABLE','A_REACTION_DEFINED'])]:
        t=ts[tid]
        for values in itertools.product(['TRUE','FALSE','UNKNOWN'],repeat=len(fields)):
            overrides=dict(zip(fields,values));gs={g:overrides.get(g,'TRUE') for g in t['required_guards']}
            expected='BLOCKED' if 'FALSE' in values else 'INDETERMINATE' if 'UNKNOWN' in values else 'ALLOWED_ASSUMED'
            actual=author.classify(t,t['from_states'][0],gs)
            combinations.append(dict(action=tid,overrides=overrides,expected=expected,actual=actual,matches=expected==actual))

    # Explicitly ASSUMED fixture construction, never a default for real evidence.
    def record(ctx,action,guard,value='TRUE',phase=None):
        t=logic.spec(c,action)
        return dict({k:ctx[k] for k in c['evidence_policy']['scope_fields']+['operation_id']},action=action,phase=phase or ('COMPLETION' if guard in t['completion_guards'] else 'ENTRY'),value=value,revisions=deepcopy(ctx['revisions']),evidence_id='ASSUMED-'+action+'-'+guard,method='ASSUMED_DOCUMENT_WITNESS',source='explicit logical fixture, not REV',valid_for_operation_interval=True)
    def context(action,state=None):
        t=logic.spec(c,action);state=state or t['from_states'][0]
        mode=(t.get('allowed_modes') or c['state_modes'][state])[0]
        ctx=dict(scenario_id='ASSUMED_CASE',variant='A' if state.startswith('A_') else 'B',mode=mode,cycle_epoch='epoch-test',subject_id='identified-material-set',operation_id='operation-test',state=state,revisions={d:0 for d in c['evidence_policy']['domains']},evidence={},faults={},material_assessment='ASSUMED_IDENTIFIED',inventory_refs=['retained-before'],pending_observations=[])
        ctx['evidence']={g:record(ctx,action,g) for g in t['required_guards']}
        return ctx
    evidence_cases=[]
    def expect(name,action,ctx,expected,stage='COMMIT'):
        got=logic.evaluate(c,action,ctx,stage)
        evidence_cases.append(dict(id=name,action=action,stage=stage,expected=expected,actual=got['permission_outcome'],matches=got['permission_outcome']==expected,result=got))
        return got
    a='A-EJECT'
    expect('fresh-complete-assumed-action',a,context(a),'ALLOWED_ASSUMED')
    for field in c['evidence_policy']['scope_fields']+['operation_id']:
        ctx=context(a);ctx[field]='different-context'
        expect('stale-scope-'+field,a,ctx,'INDETERMINATE' if field not in ['variant','mode'] else 'BLOCKED')
    for field,value in [('action','A-READY-EJECT'),('phase','COMPLETION'),('method',''),('evidence_id',''),('valid_for_operation_interval',False)]:
        ctx=context(a);ctx['evidence']['RECEIVER_DEFINED'][field]=value
        expect('invalid-evidence-'+field,a,ctx,'INDETERMINATE')
    ctx=context(a);ctx['evidence']['RECEIVER_DEFINED']['valid_for_operation_interval']='False'
    expect('truthy-string-is-not-interval-proof',a,ctx,'INDETERMINATE')
    ctx=context(a);ctx['evidence']['RECEIVER_DEFINED']['revisions']['EXIT_RECEIVER']=False
    expect('boolean-is-not-a-subject-revision',a,ctx,'INDETERMINATE')
    ctx=context(a);ctx['evidence']['RECEIVER_DEFINED']['revisions']['EXIT_RECEIVER']=0.0
    expect('float-is-not-an-exact-revision-id',a,ctx,'INDETERMINATE')
    ctx=context(a);ctx['operation_id']='';ctx['evidence']={g:dict(v,operation_id='') for g,v in ctx['evidence'].items()}
    expect('empty-operation-id-is-not-current-proof',a,ctx,'INDETERMINATE')
    ctx=context(a);ctx['evidence'].pop('RECEIVER_DEFINED')
    expect('missing-receiver-proof',a,ctx,'INDETERMINATE')
    ctx=logic.change_subject(c,context(a),'EXIT_RECEIVER')
    expect('READY-becomes-stale-after-receiver-change',a,ctx,'INDETERMINATE')
    ctx=logic.change_subject(c,context(a),'HYDRAULIC')
    expect('resource-generation-change',a,ctx,'INDETERMINATE')
    ctx=logic.change_subject(c,context(a),'RESOURCES')
    expect('nonhydraulic-consumer-change-invalidates-resource-proof',a,ctx,'INDETERMINATE')
    ctx=context(a);ctx['evidence']['RESOURCES_READY']['value']='FALSE'
    ctx=logic.change_subject(c,ctx,'HYDRAULIC','EXIT_RECEIVER')
    expect('validated-failure-does-not-age-into-unknown',a,ctx,'BLOCKED')
    invalid=context('B-LOAD');invalid['evidence']['EVENT_FRESH']['value']='FALSE'
    invalid=logic.propagate(c,invalid,logic.evaluate(c,'B-LOAD',invalid))
    query=context('REASSESS_MATERIAL','B_ACCEPTABLE_INITIAL');query['operation_id']='new-recovery-query'
    query['evidence']={g:dict(r,operation_id=query['operation_id']) for g,r in query['evidence'].items()}
    query['faults']=invalid['faults']
    expect('rejected-operation-does-not-deadlock-fresh-audit','REASSESS_MATERIAL',query,'ALLOWED_ASSUMED','ENTRY')
    ctx=context(a);ctx['faults']['RESOURCES_READY']='known unavailable';ctx=logic.change_subject(c,ctx,'HYDRAULIC','EXIT_RECEIVER')
    expect('known-resource-failure-dominates-stale-receiver',a,ctx,'BLOCKED')
    ctx=context('B-COMPACT');ctx['evidence']['B_RESET_CONFIRMED']['value']='UNKNOWN'
    r=expect('unknown-B-closure-blocks-dependent-press','B-COMPACT',ctx,'INDETERMINATE')
    blocked=logic.propagate(c,ctx,r)
    assert blocked['state']==ctx['state']
    assert blocked['inventory_refs']==ctx['inventory_refs']
    assert blocked['evidence']['DEPENDENCY_VALID']['value']=='UNKNOWN'
    ctx=context('A-STARTUP-RETURN-A_COLUMN_ESTABLISHED');ctx['evidence']['RETAINED_STABLE']['value']='FALSE'
    r=expect('lost-retention-invalidates-assessment','A-STARTUP-RETURN-A_COLUMN_ESTABLISHED',ctx,'BLOCKED')
    blocked=logic.propagate(c,ctx,r)
    assert blocked['material_assessment']=='UNCONFIRMED' and blocked['inventory_refs']==ctx['inventory_refs']
    # A caller cannot bypass a failed predecessor with a different action label.
    follow=context('A-LOAD-STEADY');follow['faults']=blocked['faults']
    expect('failure-propagates-to-steady-refill','A-LOAD-STEADY',follow,'BLOCKED')
    follow=context('B-COMPACT');follow['evidence']['DEPENDENCY_VALID']['value']='UNKNOWN'
    expect('unresolved-unknown-predecessor-does-not-advance','B-COMPACT',follow,'INDETERMINATE')
    ctx=context('B-COMPACT');ctx['evidence']['COMPACTION_CRITERION']['value']='UNKNOWN'
    start=expect('press-start-without-claiming-finished-product','B-COMPACT',ctx,'ALLOWED_ASSUMED','ENTRY')
    assert start['next_state']=='B_BATCH_SELECTED'
    expect('no-product-commit-before-completion-proof','B-COMPACT',ctx,'INDETERMINATE')
    ctx=context('A-LOAD-START');r=expect('commit-invalidates-material-proofs','A-LOAD-START',ctx,'ALLOWED_ASSUMED')
    after=logic.propagate(c,ctx,r)
    assert after['revisions']['MATERIAL']>ctx['revisions']['MATERIAL']
    assert logic.evidence_value(c,'A-LOAD-START','DOSE_DELIVERED',after,ctx['evidence']['DOSE_DELIVERED'],'COMPLETION')[0]=='UNKNOWN'
    # Recovery is not gated by the desired closure or by global READY.
    ctx=context('RESTORE_B_CLOSURE','B_RECEIVED_RESIDUAL');ctx['evidence']['B_RESET_CONFIRMED']['value']='UNKNOWN';ctx['faults']['B_RESET_CONFIRMED']='not restored'
    expect('reset-start-does-not-require-its-own-goal','RESTORE_B_CLOSURE',ctx,'ALLOWED_ASSUMED','ENTRY')
    expect('reset-completion-requires-new-closure-proof','RESTORE_B_CLOSURE',ctx,'BLOCKED')
    ctx['evidence']['RESET_SWEEP_CLEAR']['value']='FALSE';ctx['evidence']['RESOURCES_READY']['value']='UNKNOWN'
    expect('reset-own-clear-failure-dominates-resource-unknown','RESTORE_B_CLOSURE',ctx,'BLOCKED','ENTRY')
    for name,changes,expected in [
        ('receipt-unknown',{'RECEIPT_VALID':'UNKNOWN'},'INDETERMINATE'),
        ('continuity-failure-resource-unknown',{'CONTINUITY_CONFIRMED':'FALSE','RESOURCES_READY':'UNKNOWN'},'BLOCKED'),
        ('ledger-unknown',{'LEDGER_VALID':'UNKNOWN'},'INDETERMINATE'),
        ('basis-conflict',{'BASIS_DEFINED':'FALSE'},'BLOCKED'),
    ]:
        ctx=context('RESTORE_B_CLOSURE','B_RECEIVED_RESIDUAL')
        for guard,value in changes.items():ctx['evidence'][guard]['value']=value
        expect('reset-preserves-own-'+name,'RESTORE_B_CLOSURE',ctx,expected,'ENTRY')
    ctx=context('RECHECK_RECEIVER','A_SEGMENT_READY');ctx['faults']['RECEIVER_DEFINED']='receiver unavailable'
    expect('query-receiver-while-normal-eject-blocked','RECHECK_RECEIVER',ctx,'ALLOWED_ASSUMED','ENTRY')
    fresh=record(ctx,'RECHECK_RECEIVER','RECEIVER_DEFINED',phase='RECOVERY_RESULT')
    for name,rec,expected in [('new-scoped-evidence',fresh,'ALLOWED_ASSUMED'),('unknown-result',dict(fresh,value='UNKNOWN'),'INDETERMINATE'),('wrong-epoch-result',dict(fresh,cycle_epoch='old'),'INDETERMINATE')]:
        after,actual=logic.recover(c,'RECHECK_RECEIVER',ctx,'RECEIVER_DEFINED',rec)
        evidence_cases.append(dict(id='recovery-'+name,expected=expected,actual=actual,matches=actual==expected))
        assert after['state']==ctx['state']
        assert ('RECEIVER_DEFINED' in after['faults'])==(expected!='ALLOWED_ASSUMED')
    ctx=context('RECHECK_RESOURCE','A_SEGMENT_READY');fresh=record(ctx,'RECHECK_RESOURCE','RESOURCES_READY',value='FALSE',phase='RECOVERY_RESULT')
    after,actual=logic.recover(c,'RECHECK_RESOURCE',ctx,'RESOURCES_READY',fresh)
    assert actual=='BLOCKED' and 'RESOURCES_READY' in after['faults']
    evidence_cases.append(dict(id='failed-recovery-latches-new-defect',expected='BLOCKED',actual=actual,matches=actual=='BLOCKED'))
    ctx=context('RECONCILE_HISTORY','B_BATCH_SELECTED');ctx['faults']={'B_RESET_CONFIRMED':'not restored','DEPENDENCY_VALID':'press failed'}
    fresh=record(ctx,'RECONCILE_HISTORY','DEPENDENCY_VALID',phase='RECOVERY_RESULT')
    after,actual=logic.recover(c,'RECONCILE_HISTORY',ctx,'DEPENDENCY_VALID',fresh)
    assert 'B_RESET_CONFIRMED' in after['faults']
    evidence_cases.append(dict(id='history-audit-cannot-erase-open-closure-fault',expected='BLOCKED',actual=actual,matches=actual=='BLOCKED'))
    # Conditional recovery route exists without requiring normal global READY.
    q=context('REASSESS_B_CLOSURE','B_RECEIVED_RESIDUAL')
    q['faults']={'B_RESET_CONFIRMED':'unconfirmed restoration','DEPENDENCY_VALID':'failed predecessor'}
    proof=record(q,'REASSESS_B_CLOSURE','B_RESET_CONFIRMED',phase='RECOVERY_RESULT')
    restored,actual=logic.recover(c,'REASSESS_B_CLOSURE',q,'B_RESET_CONFIRMED',proof)
    assert actual=='ALLOWED_ASSUMED' and 'B_RESET_CONFIRMED' not in restored['faults'] and 'DEPENDENCY_VALID' in restored['faults']
    q=context('RECONCILE_HISTORY','B_RECEIVED_RESIDUAL');q['faults']=restored['faults']
    proof=record(q,'RECONCILE_HISTORY','DEPENDENCY_VALID',phase='RECOVERY_RESULT')
    reconciled,actual=logic.recover(c,'RECONCILE_HISTORY',q,'DEPENDENCY_VALID',proof)
    assert actual=='ALLOWED_ASSUMED' and not reconciled['faults']
    q=context('B-NEXT');q['faults']=reconciled['faults']
    expect('scoped-recovery-and-inventory-audit-enable-next-step','B-NEXT',q,'ALLOWED_ASSUMED')
    # Unexpected facts remain in a reconciliation queue without granting a step.
    ctx=context('B-LOAD');ctx['evidence']['RESOURCES_READY']['value']='UNKNOWN'
    r=expect('unready-loading-permission','B-LOAD',ctx,'INDETERMINATE')
    fact=dict(event_id='observed-dose',kind='DELIVER_DOSE',entity_id='actual-intake',dose_id='dose-observed',mass_record=dict(value=None,unit='kg',basis_id=None,status='UNKNOWN',unknown_reason='unmeasured intake'))
    after,obs=logic.record_fact(c,ctx,fact,r['permission_outcome'])
    assert after['pending_observations']==[fact] and after['inventory_refs']==ctx['inventory_refs'] and after['state']==ctx['state']
    duplicate,obs=logic.record_fact(c,after,fact,r['permission_outcome'])
    assert len(duplicate['pending_observations'])==1
    conflict,obs=logic.record_fact(c,duplicate,dict(fact,entity_id='conflicting-intake'),'BLOCKED')
    assert len(conflict['pending_observations'])==2 and 'EVENT_FRESH' in conflict['faults']
    for name in ['unexpected-intake-is-recorded-not-permitted','duplicate-observation-no-second-entry','conflicting-fact-preserved-as-fault']:
        evidence_cases.append(dict(id=name,expected='PRESERVE_FACT_NO_PROCESS_PERMISSION',actual='PRESERVE_FACT_NO_PROCESS_PERMISSION',matches=True))
    ctx=context('RESTORE_B_CLOSURE','B_RECEIVED_RESIDUAL')
    after,_=logic.record_fact(c,ctx,fact,'INDETERMINATE')
    expect('unexpected-intake-invalidates-old-reset-clear','RESTORE_B_CLOSURE',after,'INDETERMINATE','ENTRY')
    for t in c['transitions']:
        if t['event'] in {'DELIVER_DOSE','GATHER_PARTIAL','COMPACT','START_EJECTION','RETURN_TOOLS','RESET_B'}:
            for value,expected in [('UNKNOWN','INDETERMINATE'),('FALSE','BLOCKED')]:
                ctx=context(t['id']);ctx['evidence']['RESOURCES_READY']['value']=value
                expect(t['id']+'-resource-'+value,t['id'],ctx,expected,'ENTRY')

    mismatches=[r for r in cases+combinations+evidence_cases if not r['matches']]
    report=dict(scope='DOCUMENTARY_PERMISSION_REGRESSIONS_ONLY',command_execution='COMPLETED',original_R5_case_count=len(cases),baseline_mismatches=old['independent_correct_outcome_mismatches'],remaining_R5_mismatches=sum(not r['matches'] for r in cases),R5_cases=cases,combinations=combinations,evidence_propagation_recovery_cases=evidence_cases,total_checks=len(cases)+len(combinations)+len(evidence_cases),mismatches=mismatches,expected_outcome_matches=not mismatches,independent_RECHECK='NOT_RUN',physical_workability='INDETERMINATE',geometry_and_calculation='NOT_CHANGED_NOT_REBUILT',G1='OPEN')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if mismatches:sys.exit(1)


if __name__=='__main__':
    main()
