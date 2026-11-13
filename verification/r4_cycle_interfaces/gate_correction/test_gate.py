"""Functional deny dominance, addressed sources and all assessment exits."""
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
P = ROOT/'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0, str(ROOT/'verification/r5_ci_snapshots_recheck'))
from fixtures import C, L, fixture, proof, ev, prepare, rekey
sys.path.insert(0, str(P))
import recovery_snapshots as R
import semantic_minimum as S

ROWS = []
EXITS = set()
WHOLE = [('null',None),('array',[]),('text','proof'),('false',False),('true',True),
         ('zero',0),('number',1),('float',0.0),('empty-object',{})]


def causal(status='OPEN'):
    x,p = fixture(0)
    parent = L.latch(C,x,'FEED_CLEAR','ASSUMED-parent',truth='FALSE')
    target = L.latch(C,x,'B_RESET_CONFIRMED','ASSUMED-addressed-target',causes=[parent])
    if status == 'MISSING': del x['faults'][parent]
    else: x['faults'][parent]['status'] = status
    return x,proof(x,target),parent


def changed_dispatch(p,defect):
    p = copy.deepcopy(p)
    field,kind = defect.split(':')
    if kind == 'missing': p.pop(field)
    else: p[field] = 'FOREIGN'
    return p


class GateComposition(unittest.TestCase):
    def case(self,name,x,p,gate,value='UNKNOWN',causal_value=None,contract=C):
        before = copy.deepcopy((x,p,contract));digest = L.digest([x,p,contract])
        returned = []
        def trace(frame,event,arg):
            if event == 'return' and frame.f_code.co_filename == R.__file__ and frame.f_code.co_name == 'assess':
                EXITS.add(frame.f_lineno)
                returned.append(frame.f_lineno)
            return trace
        old = sys.gettrace();sys.settrace(trace)
        try: a = S.recovery_assessment(p,x,contract)
        finally: sys.settrace(old)
        self.assertEqual(a['action_gate'],gate,(name,a))
        self.assertEqual(a['recovery_value'],value,(name,a))
        if causal_value is not None: self.assertEqual(a['causal_value'],causal_value,(name,a))
        self.assertEqual((x,p,contract),before,name)
        self.assertEqual(L.digest([x,p,contract]),digest,name)
        self.assertIs(a['physical_permission'],False)
        if type(p) is not dict or type(p.get('fault_id')) is not str:
            self.assertNotIn('target_fault_id',a,name)
        ROWS.append(dict(id=name,expected_gate=gate,expected_value=value,assessment=a,
                         assessment_return_line=returned[-1],
                         input_sha256_before=digest,input_sha256_after=L.digest([x,p,contract]),
                         input_history_proof_rejected_IDs_unchanged=True,matched=True))
        return a

    def test_whole_proof_shapes_cross_own_truths(self):
        for kind in ['record','latched','state']:
            for truth in ['TRUE','FALSE','UNKNOWN']:
                for label,p in WHOLE:
                    x,_ = fixture(0)
                    if kind == 'record': x['evidence']['RESOURCES_READY']['value'] = truth
                    elif kind == 'latched' and truth != 'TRUE':
                        L.latch(C,x,'RESOURCES_READY','ASSUMED-resource',truth=truth)
                    elif kind == 'state' and truth != 'TRUE': x['state'] = 'B_RAW_LOADED' if truth == 'FALSE' else None
                    self.case('whole:'+kind+':'+truth+':'+label,x,copy.deepcopy(p),
                              'BLOCKED' if truth == 'FALSE' else 'INDETERMINATE',causal_value='UNKNOWN')

    def test_two_own_conditions_preserve_independent_false(self):
        for resource,method in [('FALSE','UNKNOWN'),('UNKNOWN','FALSE'),('FALSE','FALSE'),('TRUE','UNKNOWN'),('UNKNOWN','UNKNOWN')]:
            for label,p in WHOLE:
                x,_ = fixture(0);x['evidence']['RESOURCES_READY']['value']=resource;x['evidence']['METHOD_SUPPORTED']['value']=method
                self.case('two-own:'+resource+':'+method+':'+label,x,copy.deepcopy(p),
                          'BLOCKED' if 'FALSE' in [resource,method] else 'INDETERMINATE')
        x,_=fixture(0);L.latch(C,x,'RESOURCES_READY','ASSUMED-latched-resource',truth='FALSE');x['evidence']['METHOD_SUPPORTED']['revisions']={}
        self.case('latched-resource-plus-malformed-other-entry',x,None,'BLOCKED')

    def test_dispatch_omissions_and_causal_statuses(self):
        for status in ['OPEN','RESOLVED','UNKNOWN','MISSING']:
            for defect in ['action:missing','action:foreign','guard:missing','guard:foreign']:
                x,p,_=causal(status);q=changed_dispatch(p,defect)
                a=self.case('causal:'+status+':'+defect,x,q,'BLOCKED' if status=='OPEN' else 'INDETERMINATE',
                            causal_value={'OPEN':'FALSE','RESOLVED':'TRUE'}.get(status,'UNKNOWN'))
                self.assertEqual(a['policy_result'],'NOT_EVALUATED')
            x,p,_=causal(status)
            self.case('causal:'+status+':valid-proof',x,p,
                      {'OPEN':'BLOCKED','RESOLVED':'ALLOWED_ASSUMED'}.get(status,'INDETERMINATE'),
                      value={'OPEN':'FALSE','RESOLVED':'TRUE'}.get(status,'UNKNOWN'))

    def test_missing_unknown_and_foreign_target_never_scan_for_one(self):
        for defect in ['missing','null','array','number','text','unknown','foreign-existing']:
            x,p,parent=causal();q=changed_dispatch(p,'action:missing')
            if defect=='missing':q.pop('fault_id')
            else:q['fault_id']={'null':None,'array':[],'number':0,'text':'not-an-id','unknown':'F-'+'0'*64,'foreign-existing':parent}[defect]
            a=self.case('no-invented-target:'+defect,x,q,'INDETERMINATE',causal_value='UNKNOWN')
            self.assertNotIn('target_fault_id',a)
        for label,p in WHOLE:
            x,_,_=causal()
            self.case('known-other-causal-without-address:'+label,x,copy.deepcopy(p),'INDETERMINATE',causal_value='UNKNOWN')

    def test_snapshot_failure_and_field_order_do_not_erase_denial(self):
        for denial in ['none','resource','causal']:
            for defect in ['proof-origin','proof-result','expected','attempts']:
                for reverse in [False,True]:
                    x,p,_=causal() if denial=='causal' else (*fixture(0),None)
                    if denial=='resource':x['evidence']['RESOURCES_READY']['value']='FALSE'
                    if defect=='proof-origin':p['origin_revisions']={}
                    elif defect=='proof-result':p['revisions']={}
                    elif defect=='expected':x['faults'][p['fault_id']]['expected_revisions']={}
                    else:x['faults'][p['fault_id']].pop('resolution_attempts')
                    if reverse:p=dict(reversed(list(p.items())));x=dict(reversed(list(x.items())))
                    self.case('snapshot:'+denial+':'+defect+':'+str(reverse),x,p,
                              'INDETERMINATE' if denial=='none' else 'BLOCKED')

    def test_source_confidence_and_snapshot_gaps_are_separate(self):
        x,p=fixture(0);x['state']='UNSUPPORTED_STATE'
        self.case('unknown-state-is-not-proven-wrong-state',x,None,'INDETERMINATE')
        x,p=fixture(0);x['mode']=None
        self.case('unknown-mode-is-not-proven-wrong-mode',x,None,'INDETERMINATE')
        x,p=fixture(0);L.latch(C,x,'RESOURCES_READY','ASSUMED-resource',truth='FALSE');x['history_confirmed']=False
        self.case('unconfirmed-latched-fault',x,None,'INDETERMINATE')
        x,p=fixture(0);x['state']='B_RAW_LOADED';x['history_confirmed']=False
        self.case('unconfirmed-state-context',x,None,'INDETERMINATE')
        x,p,parent=causal();x['faults'][parent]['origin']['revisions']={};rekey(x,p)
        self.case('parent-origin-gap-keeps-recorded-prohibition',x,changed_dispatch(p,'action:missing'),'BLOCKED',causal_value='FALSE')
        x,p,parent=causal();x['faults'][p['fault_id']]['origin']['revisions']={};rekey(x,p)
        self.case('target-origin-gap-keeps-recorded-causal-link',x,changed_dispatch(p,'guard:missing'),'BLOCKED',causal_value='FALSE')

    def test_independent_record_and_rejection_sources_keep_their_reliability(self):
        x,p=fixture(0);parent=L.latch(C,x,'RESOURCES_READY','ASSUMED-damaged-latch',truth='FALSE')
        x['faults'][parent]['origin']['revisions']={};rekey(x,p)
        x['history_confirmed']=False
        x['evidence']['RESOURCES_READY']['value']='FALSE'
        a=self.case('current-false-survives-damaged-latch',x,None,'BLOCKED')
        self.assertEqual(a['entry_sources']['RESOURCES_READY'],'FROZEN_CURRENT_EVIDENCE')
        for confirmed in [True,False]:
            x,p=fixture(0);x['operation_id']=x['rejected_operation_ids'][0];x['history_confirmed']=confirmed
            self.case('rejected-operation-history:'+str(confirmed),x,None,'BLOCKED' if confirmed else 'INDETERMINATE')
        fixed,guards,action,helper=R.definitions(C)
        for known in [False,True]:
            x,p=fixture(0)
            if known:x['evidence']['RESOURCES_READY']['value']='FALSE'
            with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'history_valid',side_effect=TypeError('injected history failure')):
                self.case('history-exception:'+str(known),x,None,'BLOCKED' if known else 'INDETERMINATE')

    def test_fault_operation_metadata_is_scoped_by_guard(self):
        x,p=fixture(0);own=L.latch(C,x,'RESOURCES_READY','ASSUMED-old-resource',truth='FALSE')
        x['faults'][own]['origin']['operation_id']=None;rekey(x,p)
        self.case('resource-fault-does-not-require-old-operation',x,None,'BLOCKED')
        x,p,parent=causal();x['faults'][parent]['origin']['operation_id']=None;rekey(x,p)
        self.case('addressed-parent-does-not-require-old-operation',x,changed_dispatch(p,'action:missing'),'BLOCKED',causal_value='FALSE')
        x,p=fixture(0);own=L.latch(C,x,'EVENT_FRESH','ASSUMED-unknown-event',truth='FALSE')
        x['faults'][own]['origin']['operation_id']=None;rekey(x,p);x['operation_id']=None
        self.case('unknown-current-operation-is-not-an-addressed-freshness-denial',x,None,'INDETERMINATE')

    def test_schema_and_exception_exits_share_composition(self):
        for x in [None,[],False,0,'context']:
            self.case('invalid-context:'+repr(x),x,None,'INDETERMINATE')
        x,p=fixture(0);x['evidence']['RESOURCES_READY']['value']='FALSE';bad=copy.deepcopy(C);bad['scope']='FOREIGN'
        self.case('unsupported-fixed-contract',x,p,'INDETERMINATE',contract=bad)
        for exc in [ValueError('unsupported'),OSError('unavailable'),KeyError('absent'),StopIteration()]:
            with patch.object(R,'definitions',side_effect=exc):
                self.case('unavailable-definitions:'+type(exc).__name__,x,p,'INDETERMINATE')
        fixed,guards,action,helper=R.definitions(C);original=helper.evidence_value
        def failed_entry(contract,act,g,context,record,phase):
            if g=='RESOURCES_READY':raise TypeError('injected entry failure')
            return original(contract,act,g,context,record,phase)
        for known in [False,True]:
            x,p=fixture(0)
            if known:x['evidence']['METHOD_SUPPORTED']['value']='FALSE'
            with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'evidence_value',side_effect=failed_entry):
                self.case('entry-exception-with-independent-false:'+str(known),x,None,'BLOCKED' if known else 'INDETERMINATE')
        for denial in ['none','resource','causal']:
            x,p,_=causal() if denial=='causal' else (*fixture(0),None)
            if denial=='resource':x['evidence']['RESOURCES_READY']['value']='FALSE'
            with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'recover',side_effect=KeyError('injected policy failure')):
                a=self.case('policy-exception:'+denial,x,p,'INDETERMINATE' if denial=='none' else 'BLOCKED')
            self.assertEqual(a['compatibility_domain'],'OUT_OF_DOMAIN')

    def test_positive_minimal_domains_and_unrelated_fault_retention(self):
        for start in [0,1,2**63]:
            x,p=fixture(start);x['revisions'].pop('FEED');x['revisions'].pop('RETENTION')
            self.case('positive-unused-domains-absent:'+str(start),x,p,'ALLOWED_ASSUMED','TRUE','TRUE')
        x,p=fixture(0);target=p['fault_id'];L.latch(C,x,'FEED_CLEAR','ASSUMED-unrelated-feed',truth='FALSE')
        self.case('positive-unrelated-open-fault',x,p,'ALLOWED_ASSUMED','TRUE','TRUE')
        out,status=L.recover(C,'RESTORE_B_CLOSURE',x,target,p);self.assertEqual(status,'ALLOWED_ASSUMED')
        self.assertTrue(L.open_faults(out,'FEED_CLEAR'))
        ordinary=prepare(out,'B-COMPACT','ordinary-after-recovery');ordinary['state']='B_BATCH_SELECTED'
        self.assertEqual(L.evaluate(C,'B-COMPACT',ordinary,'ENTRY')['permission_outcome'],'BLOCKED')

    def test_zz_all_assessment_return_paths_are_exercised(self):
        tree=ast.parse(Path(R.__file__).read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='assess')
        class Returns(ast.NodeVisitor):
            def __init__(self):self.lines=set()
            def visit_FunctionDef(self,node):pass
            def visit_Return(self,node):
                if not isinstance(node.value,ast.Call) or not isinstance(node.value.func,ast.Name) or node.value.func.id!='finish':
                    raise AssertionError('Assessment exit bypasses final composition at '+str(node.lineno))
                self.lines.add(node.lineno)
        visitor=Returns()
        for node in fn.body:visitor.visit(node)
        self.assertEqual(EXITS,visitor.lines)
        self.assertEqual(len(EXITS),8)

    @classmethod
    def tearDownClass(cls):
        target=os.environ.get('REV_GATE_CAPTURE')
        if target:Path(target).write_text(json.dumps(dict(cases=ROWS,count=len(ROWS),all_matched=all(r['matched'] for r in ROWS),
            assessment_return_lines=sorted(EXITS),all_8_return_paths_exercised=len(EXITS)==8),indent=2)+'\n')


if __name__=='__main__':unittest.main()
