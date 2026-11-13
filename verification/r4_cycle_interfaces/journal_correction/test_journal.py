"""Fixed-definition namespace, bounded fields, graph direction and deny dominance."""
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


def foreign(x,position='last'):
    key=L.latch(C,x,'FEED_CLEAR','ASSUMED-known-foreign:'+str(len(x['faults'])),truth='UNKNOWN')
    f=x['faults'].pop(key);items=list(x['faults'].items());i=0 if position=='first' else len(items)//2 if position=='middle' else len(items)
    items.insert(i,(key,f));x['faults']=dict(items);return key


def change(x,key,fn,coherent=True):
    items=list(x['faults'].items());index=next(i for i,(k,_) in enumerate(items) if k==key)
    f=items[index][1];fn(f)
    new='F-'+L.digest(f.get('origin')) if coherent else key
    if coherent:f['fault_id']=new
    items[index]=(new,f);x['faults']=dict(items)
    return new


class JournalAdmission(unittest.TestCase):
    def case(self,name,x,p,gate,scope='UNKNOWN',admitted='UNKNOWN',record=None,classification=None):
        x['pending_observations']=[dict(event_id='ASSUMED-pending',value='UNKNOWN')]
        before=copy.deepcopy((x,p,C));serialized=json.dumps([x,p,C],ensure_ascii=False);digest=L.digest([x,p,C])
        a=S.recovery_assessment(p,x,C);j=a['journal_admission']
        self.assertEqual(a['action_gate'],gate,(name,a));self.assertEqual(a['recovery_value'],scope,(name,a))
        self.assertEqual(j['value'],admitted,(name,a));self.assertEqual(j['records_seen'],len(x['faults']),(name,a))
        row=next((r for r in j['records'] if r['fault_id']==record),None) if record else None
        if classification:self.assertEqual(row['classification'],classification,(name,a))
        if admitted=='UNKNOWN':
            self.assertEqual(a['compatibility_domain'],'OUT_OF_DOMAIN');self.assertEqual(a['policy_result'],'NOT_EVALUATED')
            self.assertNotEqual(a['recovery_value'],'TRUE')
            self.assertTrue(all(r['value']!='TRUE' for r in a['journal_evidence'].values()))
        self.assertIs(a['physical_permission'],False)
        self.assertEqual((x,p,C),before);self.assertEqual(json.dumps([x,p,C],ensure_ascii=False),serialized);self.assertEqual(L.digest([x,p,C]),digest)
        ROWS.append(dict(id=name,expected_gate=gate,gate=a['action_gate'],scoped=a['recovery_value'],admission=j['value'],
                         records_seen=j['records_seen'],open_seen=j['open_seen'],unclassifiable=j['unclassifiable'],
                         observed_record=row,admission_reasons=j['reasons'],input_sha256_before=digest,input_sha256_after=L.digest([x,p,C]),
                         ordered_input_sha256_before=__import__('hashlib').sha256(serialized.encode()).hexdigest(),
                         caller_origin_expected_history_rejected_pending_unchanged=True,matched=True))
        return a

    def test_guard_types_positions_and_raw_truths(self):
        tags=[('missing','MISSING'),('null',None),('false',False),('true',True),('integer',0),('one',1),('float',0.0),('array',[]),('object',{}),('empty',''),('unknown','FUTURE_GUARD')]
        for label,tag in tags:
            for position in ['first','middle','last']:
                for truth in ['TRUE','FALSE','UNKNOWN']:
                    x,p=fixture(0);key=foreign(x,position)
                    key=change(x,key,lambda f:f['origin'].pop('guard') if label=='missing' else f['origin'].__setitem__('guard',copy.deepcopy(tag)))
                    x['evidence']['RESOURCES_READY']['value']=truth
                    self.case('tag:'+label+':'+position+':'+truth,x,p,'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',record=key,classification='UNCLASSIFIABLE')

    def test_every_fixed_guard_is_recognized_before_action_filtering(self):
        for g in G:
            x,p=fixture(0);key=L.latch(C,x,g,'ASSUMED-namespace-coverage:'+g,truth='UNKNOWN')
            own=g in A['entry_guards']
            a=self.case('fixed-namespace:'+g,x,p,'INDETERMINATE' if own else 'ALLOWED_ASSUMED',
                        'UNKNOWN' if own else 'TRUE','TRUE',record=key,
                        classification='APPLICABLE' if own or g in A.get('may_reestablish',[]) else 'NOT_APPLICABLE')
            self.assertEqual({r['guard'] for r in a['journal_admission']['records'] if r['status']=='OPEN'} <= set(G),True)

    def test_bounded_scope_revision_causal_and_status_fields(self):
        defects=[]
        for label,value in [('missing',None),('null',None),('bool',False),('integer',0),('array',[]),('object',{}),('empty',''),('unknown','FUTURE_STATUS')]:
            defects.append(('status:'+label,lambda f,v=value,l=label:f.pop('status') if l=='missing' else f.__setitem__('status',copy.deepcopy(v))))
        for label,value in [('missing',None),('null',None),('array',[]),('empty',{})]:
            defects.append(('scope:'+label,lambda f,v=value,l=label:f['origin'].pop('scope') if l=='missing' else f['origin'].__setitem__('scope',copy.deepcopy(v))))
        for field in C['fault_policy']['identity_fields']+['subject_kind']:
            defects.append(('scope:'+field+':missing',lambda f,k=field:f['origin']['scope'].pop(k)))
            for label,value in [('null',None),('bool',False),('empty','')]:
                defects.append(('scope:'+field+':'+label,lambda f,k=field,v=value:f['origin']['scope'].__setitem__(k,v)))
        for field,value in [('subject_kind','OTHER_KIND'),('mode','FUTURE_MODE'),('variant','OTHER_VARIANT'),('basis_id','undeclared-basis')]:
            defects.append(('scope:'+field+':unsupported',lambda f,k=field,v=value:f['origin']['scope'].__setitem__(k,v)))
        for name in ['origin','expected']:
            for label,value in [('missing',None),('empty',{}),('null',None),('array',[])]:
                def m(f,n=name,l=label,v=value):
                    obj,key=(f['origin'],'revisions') if n=='origin' else (f,'expected_revisions')
                    if l=='missing':obj.pop(key)
                    else:obj[key]=copy.deepcopy(v)
                defects.append((name+'-snapshot:'+label,m))
            for label,value in [('bool',False),('float',0.0),('text','0'),('negative',-1),('unconfirmed-int',1)]:
                def m(f,n=name,v=value):
                    obj=f['origin']['revisions'] if n=='origin' else f['expected_revisions'];obj['FEED']=v
                defects.append((name+'-counter:'+label,m))
            def extra(f,n=name):
                obj=f['origin']['revisions'] if n=='origin' else f['expected_revisions'];obj['B_CLOSURE']=0
            defects.append((name+'-extra-domain',extra))
        for label,value in [('missing',None),('null',None),('array',{}),('unknown-link',['F-'+'0'*64]),('bad-id',['not-an-id']),('typed-id',[False]),('duplicate',None)]:
            def m(f,l=label,v=value):
                if l=='missing':f['origin'].pop('cause_fault_ids')
                elif l=='duplicate':f['origin']['cause_fault_ids']=['F-'+'0'*64]*2
                else:f['origin']['cause_fault_ids']=copy.deepcopy(v)
            defects.append(('causal:'+label,m))
        for label,value in [('null',None),('bool',False),('unknown','false')]:defects.append(('truth:'+label,lambda f,v=value:f['origin'].__setitem__('truth',v)))
        for label,value in [('missing',None),('null',None),('object',{}),('bad-event',[dict(domain='FEED',from_revision=False,to_revision=1)])]:
            defects.append(('history:'+label,lambda f,l=label,v=value:f.pop('revision_history') if l=='missing' else f.__setitem__('revision_history',copy.deepcopy(v))))
        for name,fn in defects:
            for truth in ['TRUE','FALSE','UNKNOWN']:
                x,p=fixture(0);key=foreign(x);key=change(x,key,fn);x['evidence']['RESOURCES_READY']['value']=truth
                self.case('schema:'+name+':'+truth,x,p,'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',record=key,classification='UNCLASSIFIABLE')

    def test_mixed_known_unknown_records_are_fully_scanned(self):
        for position in ['first','middle','last']:
            for truth in ['TRUE','FALSE','UNKNOWN']:
                x,p=fixture(0);good=foreign(x);bad=foreign(x,position)
                # A separate reason produces a distinct immutable record.
                bad=change(x,bad,lambda f:(f['origin'].__setitem__('guard',None),f['origin'].__setitem__('reason','ASSUMED-unknown-1')))
                second=L.latch(C,x,'FEED_CLEAR','ASSUMED-unknown-2',truth='UNKNOWN');second=change(x,second,lambda f:f['origin'].__setitem__('guard','FUTURE_GUARD'))
                x['evidence']['METHOD_SUPPORTED']['value']=truth
                a=self.case('mixed:'+position+':'+truth,x,p,'BLOCKED' if truth=='FALSE' else 'INDETERMINATE')
                self.assertGreaterEqual(a['journal_admission']['unclassifiable'],2)
                self.assertEqual(next(r for r in a['journal_admission']['records'] if r['fault_id']==good)['classification'],'NOT_APPLICABLE')

    def test_graph_direction_known_FEED_and_historical_scope(self):
        x,p=fixture(0);key=foreign(x)
        a=self.case('known-FEED-control',x,p,'ALLOWED_ASSUMED','TRUE','TRUE',key,'NOT_APPLICABLE')
        self.assertTrue(all(r['classification']!='UNCLASSIFIABLE' for r in a['journal_admission']['records']))
        out,gate=L.recover(C,'RESTORE_B_CLOSURE',x,p['fault_id'],p);self.assertEqual(gate,'ALLOWED_ASSUMED');self.assertTrue(L.open_faults(out,'FEED_CLEAR'))
        work=prepare(out,'B-COMPACT','ASSUMED-work');work['state']='B_BATCH_SELECTED';self.assertEqual(L.evaluate(C,'B-COMPACT',work,'ENTRY')['permission_outcome'],'BLOCKED')
        x,p=fixture(0);key=foreign(x);key=change(x,key,lambda f:f['origin'].__setitem__('cause_fault_ids',[p['fault_id']]))
        self.case('downstream-FEED-does-not-deadlock-target',x,p,'ALLOWED_ASSUMED','TRUE','TRUE',key,'NOT_APPLICABLE')
        x,p=fixture(0);key=foreign(x);target=L.latch(C,x,'B_RESET_CONFIRMED','ASSUMED-target-with-feed-parent',causes=[key]);p=proof(x,target)
        self.case('upstream-FEED-is-addressed-causal',x,p,'BLOCKED','FALSE','TRUE',key,'APPLICABLE')
        x,p=fixture(0);key=foreign(x)
        def past(f):
            f['origin']['scope'].update(variant='A',mode='A_STARTUP',batch_id='past-batch')
            f['origin']['revisions']={k:9 for k in G['FEED_CLEAR']['evidence_domains']};f['expected_revisions']=copy.deepcopy(f['origin']['revisions'])
            f['origin']['evidence']={'old':True,'phase':'PAST_UNKNOWN'}
        key=change(x,key,past);x['revisions'].pop('FEED');x['revisions'].pop('RETENTION')
        self.case('historical-known-FEED-not-reevaluated-in-current-scope',x,p,'ALLOWED_ASSUMED','TRUE','TRUE',key,'NOT_APPLICABLE')

    def test_resolved_policy_and_operation_specific_scope(self):
        x,p=fixture(0);key=foreign(x);key=change(x,key,lambda f:(f.__setitem__('status','RESOLVED'),f['origin'].__setitem__('guard',None)))
        self.case('confirmed-RESOLVED-not-an-OPEN-latch',x,p,'ALLOWED_ASSUMED','TRUE','TRUE',key,'NOT_OPEN')
        x,p=fixture(0);op=x['operation_id'];x['operation_id']='ASSUMED-older-request';key=L.latch(C,x,'EVENT_FRESH','ASSUMED-old-request',truth='FALSE');x['operation_id']=op
        key=change(x,key,lambda f:f['origin'].__setitem__('revisions',{}))
        self.case('known-other-operation-does-not-require-unconsumed-snapshot',x,p,'ALLOWED_ASSUMED','TRUE','TRUE',key,'NOT_APPLICABLE')

    def test_unknown_journal_keeps_known_own_state_and_causal_FALSE(self):
        for kind in ['raw','latch','state','causal']:
            x,p=fixture(0)
            if kind=='raw':x['evidence']['RESOURCES_READY']['value']='FALSE'
            elif kind=='latch':L.latch(C,x,'RESOURCES_READY','ASSUMED-owned-failure',truth='FALSE')
            elif kind=='state':x['state']=next(s for s in C['state_modes'] if s not in A['from_states'])
            else:
                parent=foreign(x);target=L.latch(C,x,'B_RESET_CONFIRMED','ASSUMED-causal-target',causes=[parent]);p=proof(x,target)
            key=L.latch(C,x,'FEED_CLEAR','ASSUMED-unclassifiable',truth='UNKNOWN');key=change(x,key,lambda f:f['origin'].__setitem__('guard',None))
            self.case('known-FALSE-survives:'+kind,x,p,'BLOCKED')

    def test_classifier_failure_is_UNKNOWN_without_permission_or_blanket_denial(self):
        for truth in ['TRUE','FALSE','UNKNOWN']:
            x,p=fixture(0);x['evidence']['RESOURCES_READY']['value']=truth
            with patch.object(R,'classify',side_effect=KeyError('injected classifier unavailable')):
                before=L.digest([x,p,C]);a=S.recovery_assessment(p,x,C);self.assertEqual(L.digest([x,p,C]),before)
            self.assertEqual(a['action_gate'],'BLOCKED' if truth=='FALSE' else 'INDETERMINATE')
            self.assertEqual(a['recovery_value'],'UNKNOWN');self.assertEqual(a['journal_admission']['value'],'UNKNOWN')
        x,p=fixture(0);key=foreign(x);key=change(x,key,lambda f:f['origin'].__setitem__('guard',None))
        fixed,guards,action,helper=R.definitions(C)
        with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'recover',wraps=helper.recover) as recover:
            self.case('unclassifiable-journal-never-delegates-positive',x,p,'INDETERMINATE');recover.assert_not_called()

    @classmethod
    def tearDownClass(cls):
        target=os.environ.get('REV_JOURNAL_CAPTURE')
        if target:Path(target).write_text(json.dumps(dict(cases=ROWS,count=len(ROWS),all_matched=all(r['matched'] for r in ROWS),
            oracle='Fixed definitions, explicit schema/graph obligations, R1 admission and independent FALSE truth table'),indent=2)+'\n')


if __name__=='__main__':unittest.main()
