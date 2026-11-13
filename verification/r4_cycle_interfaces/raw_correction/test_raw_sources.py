"""Independent frozen raw oracle, damaged journal and no new permissions."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'verification/r5_ci_snapshots_recheck'))
from fixtures import C,L,G,A,fixture,proof,prepare,rekey
sys.path.insert(0,str(ROOT/'verification/r4_cycle_interfaces/proposal'))
import recovery_snapshots as R
import semantic_minimum as S

ROWS=[]
GUARDS=['RESOURCES_READY','METHOD_SUPPORTED']


def damaged(x,kind='missing-guard',position='last',reader_guard=None):
    old=L.latch(C,x,'FEED_CLEAR','ASSUMED-foreign-journal',truth='UNKNOWN')
    f=x['faults'].pop(old)
    if kind=='missing-guard':f['origin'].pop('guard')
    elif kind=='null-origin':f['origin']=None
    elif kind=='array-origin':f['origin']=[]
    elif kind=='empty-origin':f['origin']={}
    elif kind=='missing-truth':f['origin']['guard']=reader_guard;f['origin'].pop('truth')
    key='F-'+L.digest(f['origin']);f['fault_id']=key
    items=list(x['faults'].items());index=0 if position=='first' else len(items)//2 if position=='middle' else len(items)
    items.insert(index,(key,f));x['faults']=dict(items)
    return key


def requested(p,shape):
    p=copy.deepcopy(p)
    if shape=='null':return None
    if shape=='unknown-target':p['fault_id']='F-'+'0'*64
    elif shape=='unsupported-dispatch':p.pop('guard')
    elif shape=='snapshot-rejection':p['origin_revisions']={}
    return p


def pending(x):
    x['pending_observations']=[dict(event_id='ASSUMED-pending',value='UNKNOWN',source='synthetic readonly observation')]


class IndependentRawSources(unittest.TestCase):
    def case(self,name,x,p,g,gate,raw=None,raw_status=None,journal_status=None,value='UNKNOWN'):
        before=copy.deepcopy((x,p,C));text=json.dumps([x,p,C],ensure_ascii=False);digest=L.digest([x,p,C])
        a=S.recovery_assessment(p,x,C)
        self.assertEqual(a['action_gate'],gate,(name,a));self.assertEqual(a['recovery_value'],value,(name,a))
        r=a.get('raw_evidence',{}).get(g,{})
        j=a.get('journal_evidence',{}).get(g,{})
        if raw is not None:self.assertEqual(r['value'],raw,(name,a))
        if raw_status:self.assertEqual(r['status'],raw_status,(name,a))
        if journal_status:self.assertEqual(j['status'],journal_status,(name,a))
        if r.get('value')=='FALSE':
            self.assertEqual(r['status'],'VALIDATED');self.assertEqual(r['reason'],'CURRENT_ASSUMED_RECORD')
        self.assertEqual((x,p,C),before,name);self.assertEqual(json.dumps([x,p,C],ensure_ascii=False),text,name)
        self.assertEqual(L.digest([x,p,C]),digest,name);self.assertIs(a['physical_permission'],False)
        if type(p) is not dict or 'fault_id' not in p:self.assertNotIn('target_fault_id',a)
        ROWS.append(dict(id=name,guard=g,expected_gate=gate,actual_gate=a['action_gate'],expected_scoped=value,
                         scoped=a['recovery_value'],raw=r,journal=j,own_value=a.get('entry_values',{}).get(g),
                         own_source=a.get('entry_sources',{}).get(g),
                         validation_codes=sorted({v['code'] for v in a['validation']['reasons']}),
                         input_sha256_before=digest,input_sha256_after=L.digest([x,p,C]),
                         caller_origin_expected_history_rejected_pending_unchanged=True,matched=True))
        return a

    def test_eight_variations_and_TRUE_UNKNOWN_controls(self):
        for g in GUARDS:
            for shape in ['null','unknown-target','unsupported-dispatch','snapshot-rejection']:
                for truth in ['FALSE','TRUE','UNKNOWN']:
                    x,p=fixture(0);pending(x);damaged(x);x['evidence'][g]['value']=truth
                    self.assertEqual(L._raw_value(C,'RESTORE_B_CLOSURE',g,x,x['evidence'][g],'ENTRY')[0],truth)
                    a=self.case('eight:'+g+':'+shape+':'+truth,x,requested(p,shape),g,
                                'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',truth,'VALIDATED','EXCEPTION')
                    self.assertEqual(a['entry_values'][g],'FALSE' if truth=='FALSE' else 'UNKNOWN')
                    self.assertEqual(a['journal_evidence'][g]['value'],'UNKNOWN')

    def test_every_own_guard_has_independent_raw_validation(self):
        for g in A['entry_guards']:
            for truth in ['FALSE','TRUE','UNKNOWN']:
                x,p=fixture(0);pending(x);damaged(x);x['evidence'][g]['value']=truth
                self.case('every-guard:'+g+':'+truth,x,None,g,'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',truth,'VALIDATED','EXCEPTION')

    def test_journal_damage_positions_and_types(self):
        for g in GUARDS:
            for kind in ['missing-guard','null-origin','array-origin','empty-origin','missing-truth']:
                for position in ['first','middle','last']:
                    for truth in ['FALSE','TRUE','UNKNOWN']:
                        x,p=fixture(0);pending(x);damaged(x,kind,position,g);x['evidence'][g]['value']=truth
                        self.case('damage:'+g+':'+kind+':'+position+':'+truth,x,None,g,
                                  'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',truth,'VALIDATED','EXCEPTION')

    def test_stale_foreign_and_invalid_records_are_not_FALSE(self):
        for g in GUARDS:
            defects=[]
            for field in C['evidence_policy']['scope_fields']+['operation_id']:
                defects.append((field+':foreign',lambda x,r,f=field:r.__setitem__(f,'FOREIGN')))
                defects.append((field+':missing',lambda x,r,f=field:r.pop(f)))
            for field in ['action','guard','phase']:
                defects.append((field+':foreign',lambda x,r,f=field:r.__setitem__(f,'FOREIGN')))
                defects.append((field+':missing',lambda x,r,f=field:r.pop(f)))
            for field in ['evidence_id','method','source']:
                for label,v in [('empty',''),('null',None),('bool',False),('array',[])]:
                    defects.append((field+':'+label,lambda x,r,f=field,v=v:r.__setitem__(f,copy.deepcopy(v))))
                defects.append((field+':missing',lambda x,r,f=field:r.pop(f)))
            for label,v in [('false',False),('number',1),('text','TRUE'),('null',None)]:
                defects.append(('interval:'+label,lambda x,r,v=v:r.__setitem__('valid_for_operation_interval',v)))
            defects.append(('interval:missing',lambda x,r:r.pop('valid_for_operation_interval')))
            for label,v in [('empty',{}),('null',None),('array',[])]:
                defects.append(('revision-map:'+label,lambda x,r,v=v:r.__setitem__('revisions',copy.deepcopy(v))))
            for d in G[g]['evidence_domains']:
                for label,v in [('stale',1),('bool',False),('float',0.0),('text','0'),('null',None),('negative',-1)]:
                    defects.append(('record-revision:'+d+':'+label,lambda x,r,d=d,v=v:r['revisions'].__setitem__(d,v)))
                defects.append(('record-revision:'+d+':missing',lambda x,r,d=d:r['revisions'].pop(d)))
                for label,v in [('stale',1),('bool',False),('float',0.0)]:
                    defects.append(('current-revision:'+d+':'+label,lambda x,r,d=d,v=v:x['revisions'].__setitem__(d,v)))
                defects.append(('current-revision:'+d+':missing',lambda x,r,d=d:x['revisions'].pop(d)))
            for label,v in [('bool',False),('number',0),('null',None),('foreign','false')]:
                defects.append(('literal-value:'+label,lambda x,r,v=v:r.__setitem__('value',v)))
            for name,mutate in defects:
                for truth in ['FALSE','TRUE','UNKNOWN']:
                    for other_false in [False,True]:
                        x,p=fixture(0);pending(x);damaged(x);record=x['evidence'][g];record['value']=truth;mutate(x,record)
                        other=next(v for v in GUARDS if v!=g)
                        if other_false:x['evidence'][other]['value']='FALSE'
                        oracle=L._raw_value(C,'RESTORE_B_CLOSURE',g,x,record,'ENTRY')
                        self.assertEqual(oracle[0],'UNKNOWN',name)
                        if other_false:self.assertEqual(L._raw_value(C,'RESTORE_B_CLOSURE',other,x,x['evidence'][other],'ENTRY')[0],'FALSE')
                        self.case('unconfirmed:'+g+':'+name+':'+truth+':other='+str(other_false),x,None,g,
                                  'BLOCKED' if other_false else 'INDETERMINATE','UNKNOWN','UNCONFIRMED','EXCEPTION')

    def test_two_independent_current_conditions(self):
        for resource in ['TRUE','FALSE','UNKNOWN']:
            for method in ['TRUE','FALSE','UNKNOWN']:
                for shape in ['null','unknown-target','unsupported-dispatch','snapshot-rejection']:
                    x,p=fixture(0);pending(x);damaged(x);x['evidence']['RESOURCES_READY']['value']=resource;x['evidence']['METHOD_SUPPORTED']['value']=method
                    a=self.case('two:'+resource+':'+method+':'+shape,x,requested(p,shape),'RESOURCES_READY',
                                'BLOCKED' if 'FALSE' in [resource,method] else 'INDETERMINATE',resource,'VALIDATED','EXCEPTION')
                    self.assertEqual(a['raw_evidence']['METHOD_SUPPORTED']['value'],method)

    def test_valid_proof_with_unknown_journal_never_delegates_success(self):
        fixed,guards,action,helper=R.definitions(C)
        for g in GUARDS:
            for truth in ['TRUE','FALSE','UNKNOWN']:
                x,p=fixture(0);pending(x);damaged(x);x['evidence'][g]['value']=truth
                with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'recover',wraps=helper.recover) as recover:
                    a=self.case('valid-proof-with-broken-journal:'+g+':'+truth,x,p,g,
                                'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',truth,'VALIDATED','EXCEPTION')
                    recover.assert_not_called()
                self.assertEqual(a['policy_result'],'NOT_EVALUATED')
                self.assertEqual(a['entry_values'][g],'FALSE' if truth=='FALSE' else 'UNKNOWN')

    def test_raw_reader_exceptions_do_not_invent_FALSE(self):
        fixed,guards,action,helper=R.definitions(C);original=helper._raw_value
        for g in GUARDS:
            for cls in [KeyError,TypeError,AttributeError,ValueError,StopIteration]:
                for other_false in [False,True]:
                    x,p=fixture(0);pending(x);damaged(x);x['evidence'][g]['value']='FALSE'
                    if other_false:x['evidence'][next(v for v in GUARDS if v!=g)]['value']='FALSE'
                    def unavailable(c,a,guard,context,record,phase):
                        if guard==g:raise cls('injected raw unavailability')
                        return original(c,a,guard,context,record,phase)
                    with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'_raw_value',side_effect=unavailable):
                        self.case('raw-exception:'+g+':'+cls.__name__+':other='+str(other_false),x,None,g,
                                  'BLOCKED' if other_false else 'INDETERMINATE','UNKNOWN','EXCEPTION','EXCEPTION')
        x,p=fixture(0);pending(x);L.latch(C,x,'RESOURCES_READY','ASSUMED-confirmed-resource',truth='FALSE')
        def unavailable_resource(c,a,g,context,record,phase):
            if g=='RESOURCES_READY':raise TypeError('injected raw failure')
            return original(c,a,g,context,record,phase)
        with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'_raw_value',side_effect=unavailable_resource):
            self.case('journal-FALSE-survives-raw-failure',x,None,'RESOURCES_READY','BLOCKED','UNKNOWN','EXCEPTION','EVALUATED')

    def test_state_causal_and_context_sources(self):
        x,p=fixture(0);damaged(x);x['state']=next(s for s in C['state_modes'] if s not in A['from_states'])
        self.case('state-FALSE-independent-of-journal-error',x,None,'RESOURCES_READY','BLOCKED','TRUE','VALIDATED','EXCEPTION')
        x,p=fixture(0);parent=L.latch(C,x,'FEED_CLEAR','ASSUMED-parent',truth='FALSE');target=L.latch(C,x,'B_RESET_CONFIRMED','ASSUMED-target',causes=[parent]);p=proof(x,target);damaged(x);p.pop('action')
        a=self.case('addressed-causal-FALSE-independent-of-reader',x,p,'RESOURCES_READY','BLOCKED','TRUE','VALIDATED','EXCEPTION');self.assertEqual(a['causal_value'],'FALSE')
        for value in ['TRUE','FALSE','UNKNOWN']:
            x,p=fixture(0);x['faults']=None;x['evidence']['RESOURCES_READY']['value']=value
            self.case('journal-container-unavailable:'+value,x,None,'RESOURCES_READY','BLOCKED' if value=='FALSE' else 'INDETERMINATE',value,'VALIDATED','EXCEPTION')
        for field,bad in [('evidence',None),('evidence',[]),('revisions',None),('revisions',[])]:
            x,p=fixture(0);damaged(x);x[field]=bad
            self.case('context-damage:'+field+':'+repr(bad),x,None,'RESOURCES_READY','INDETERMINATE','UNKNOWN','UNCONFIRMED','EXCEPTION')
        for x in [None,[],False,0,'context']:
            self.case('context-not-object:'+repr(x),x,None,'RESOURCES_READY','INDETERMINATE')

    def test_positive_recovery_and_unrelated_fault_work_prohibition(self):
        for n in [0,1,2**63]:
            x,p=fixture(n);pending(x);x['revisions'].pop('FEED');x['revisions'].pop('RETENTION')
            self.case('positive-minimal:'+str(n),x,p,'RESOURCES_READY','ALLOWED_ASSUMED','TRUE','VALIDATED','EVALUATED','TRUE')
        x,p=fixture(0);pending(x);target=p['fault_id'];L.latch(C,x,'FEED_CLEAR','ASSUMED-unrelated-feed',truth='FALSE')
        self.case('positive-unrelated-fault-retained',x,p,'RESOURCES_READY','ALLOWED_ASSUMED','TRUE','VALIDATED','EVALUATED','TRUE')
        out,gate=L.recover(C,'RESTORE_B_CLOSURE',x,target,p);self.assertEqual(gate,'ALLOWED_ASSUMED');self.assertTrue(L.open_faults(out,'FEED_CLEAR'))
        work=prepare(out,'B-COMPACT','ASSUMED-ordinary-work');work['state']='B_BATCH_SELECTED'
        self.assertEqual(L.evaluate(C,'B-COMPACT',work,'ENTRY')['permission_outcome'],'BLOCKED')

    @classmethod
    def tearDownClass(cls):
        target=os.environ.get('REV_RAW_CAPTURE')
        if target:Path(target).write_text(json.dumps(dict(cases=ROWS,count=len(ROWS),all_matched=all(r['matched'] for r in ROWS),
            oracle='Pinned frozen _raw_value plus R1 two-source truth table; current literal FALSE is insufficient'),indent=2)+'\n')


if __name__=='__main__':unittest.main()
