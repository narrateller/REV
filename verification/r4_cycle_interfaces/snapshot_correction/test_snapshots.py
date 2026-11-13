"""Fixed-domain admission, history and composite-gate regression matrix."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
P = ROOT/'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0,str(P))
import semantic_minimum as S
C=json.loads((ROOT/'verification/r4_cycle_contract/contract.json').read_text())
spec=importlib.util.spec_from_file_location('snapshot_test_frozen',ROOT/'verification/r4_cycle_contract/permission_examples.py')
L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
ROWS=[]


def ev(x,a,g,phase=None):
    t=L.spec(C,a)
    return dict({k:x[k] for k in C['evidence_policy']['scope_fields']+['operation_id']},action=a,guard=g,
        phase=phase or ('COMPLETION' if g in t['completion_guards'] else 'ENTRY'),value='TRUE',
        revisions=copy.deepcopy(x['revisions']),evidence_id='ASSUMED-'+a+g,method='ASSUMED_FIXTURE',
        source='synthetic snapshot test only',valid_for_operation_interval=True)


def prepare(x,a,op):
    x=copy.deepcopy(x);x['operation_id']=op;x['evidence']={g:ev(x,a,g) for g in L.spec(C,a)['required_guards']};return x


def proof(x,fid):
    f=x['faults'][fid];p=ev(x,'RESTORE_B_CLOSURE','B_RESET_CONFIRMED','RECOVERY_RESULT')
    p.update(fault_id=fid,target_scope=copy.deepcopy(f['origin']['scope']),origin_revisions=copy.deepcopy(f['origin']['revisions']),revisions=copy.deepcopy(f['expected_revisions']));return p


def fixture(n=0):
    x=dict(scenario_id='SNAPSHOT-TEST',variant='B',mode='B_REPEAT',state='B_RECEIVED_RESIDUAL',subject_id='closure',
        batch_id='batch',cycle_epoch='epoch',basis_id='basis',basis_revision='r1',operation_id='denied',
        revisions={d:n for d in C['evidence_policy']['domains']},inventory_refs=['retained'],pending_observations=[])
    x=L.initialize_history(x,'snapshot-history',dict(value='TRUE',evidence_id='ASSUMED-audit',source='synthetic audit'))
    x=prepare(x,'B-NEXT','denied');x['evidence']['B_RESET_CONFIRMED']['value']='FALSE';x,_=L.decide(C,'B-NEXT',x)
    x=prepare(x,'RESTORE_B_CLOSURE','fresh-recovery');fid=L.open_faults(x,'B_RESET_CONFIRMED')[0]['fault_id'];return x,proof(x,fid)


def readdress(x,p,revisions):
    """Negative fixture only: coherent digest cannot make an incomplete origin valid."""
    old=p['fault_id'];f=x['faults'].pop(old);f['origin']['revisions']=copy.deepcopy(revisions)
    new='F-'+L.digest(f['origin']);f['fault_id']=new;x['faults'][new]=f;p.update(fault_id=new,origin_revisions=copy.deepcopy(revisions));renames={old:new}
    for key,item in list(x['faults'].items()):
        if any(c in renames for c in item['origin']['cause_fault_ids']):
            del x['faults'][key];item['origin']['cause_fault_ids']=[renames.get(c,c) for c in item['origin']['cause_fault_ids']]
            fid='F-'+L.digest(item['origin']);item['fault_id']=fid;x['faults'][fid]=item;renames[key]=fid
    x['unresolved_dependencies']=[renames.get(c,c) for c in x['unresolved_dependencies']]
    assert L.history_valid(x)


class SnapshotAdmission(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        target=os.environ.get('REV_SNAPSHOT_CAPTURE')
        if target:Path(target).write_text(json.dumps({'cases':ROWS,'count':len(ROWS),'all_matched':all(r['matched'] for r in ROWS)},indent=2)+'\n')

    def case(self,name,x,p,value,domain=None,gate=None):
        before=copy.deepcopy((x,p));before_hash=L.digest([x,p]);a=S.recovery_assessment(p,x,C)
        self.assertEqual(a['recovery_value'],value,(name,a))
        if domain:self.assertEqual(a['compatibility_domain'],domain,(name,a))
        if gate:self.assertEqual(a['action_gate'],gate,(name,a))
        try:
            out,legacy=L.recover(C,'RESTORE_B_CLOSURE',x,p['fault_id'],p)
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            self.assertEqual(a['compatibility_domain'],'OUT_OF_DOMAIN',(name,a))
            out=None;legacy='EXCEPTION:'+type(exc).__name__
        self.assertEqual((x,p),before,name)
        self.assertEqual(L.digest([x,p]),before_hash,name)
        if out is not None:self.assertTrue(set(x['rejected_operation_ids'])<=set(out['rejected_operation_ids']))
        if a['compatibility_domain']=='IN_DOMAIN':
            self.assertEqual(a['action_gate'],legacy,(name,a,legacy))
            if a['validation']['status']=='VALID':
                self.assertEqual(a['recovery_value'],{'ALLOWED_ASSUMED':'TRUE','BLOCKED':'FALSE','INDETERMINATE':'UNKNOWN'}[legacy])
        else:self.assertNotEqual(a['recovery_value'],'TRUE')
        ROWS.append({'id':name,'expected_value':value,'assessment':a,'legacy_policy':legacy,
            'legacy_returned_fault_status':out['faults'][p['fault_id']]['status'] if out is not None else 'NO_RETURN',
            'caller_fault_status':x['faults'][p['fault_id']]['status'],'original_unchanged':True,
            'caller_and_proof_sha256_before':before_hash,'caller_and_proof_sha256_after':L.digest([x,p]),
            'rejected_IDs_retained':True,'classification':'COMPATIBLE_DOMAIN' if a['compatibility_domain']=='IN_DOMAIN' else 'INTENTIONAL_PREVALIDATION_LIMIT','matched':True})
        return a,out

    def test_seven_R5_incomplete_cases(self):
        for name in ['valid','empty-expected','empty-origin-matched-proof','foreign-domain-origin-matched-proof','empty-origin-and-expected','empty-origin-unmatched-proof','omitted-proof-origin-field']:
            x,p=fixture()
            if name=='empty-expected':x['faults'][p['fault_id']]['expected_revisions']={}
            if name in ['empty-origin-matched-proof','foreign-domain-origin-matched-proof','empty-origin-and-expected','empty-origin-unmatched-proof']:readdress(x,p,{'FEED':0} if name=='foreign-domain-origin-matched-proof' else {})
            if name=='empty-origin-and-expected':x['faults'][p['fault_id']]['expected_revisions']={}
            if name=='empty-origin-unmatched-proof':p['origin_revisions']={'B_CLOSURE':0}
            if name=='omitted-proof-origin-field':p.pop('origin_revisions')
            with self.subTest(name=name):self.case('R5:'+name,x,p,'TRUE' if name=='valid' else 'UNKNOWN','IN_DOMAIN' if name=='valid' else 'OUT_OF_DOMAIN')

    def test_maps_types_domains_and_explicit_extra_policy(self):
        for location in ['origin','expected','proof-origin','proof-current','context','entry']:
            for label,bad in [('empty',{}),('foreign-only',{'FEED':0}),('extra-known',{'B_CLOSURE':0,'RETENTION':0}),('extra-foreign',{'B_CLOSURE':0,'ALIEN':0}),('bool',{'B_CLOSURE':False}),('float',{'B_CLOSURE':0.0}),('negative',{'B_CLOSURE':-1}),('null',None),('array',[]),('string','0')]:
                x,p=fixture();fault=x['faults'][p['fault_id']]
                if location=='origin':
                    if type(bad) is not dict:continue
                    readdress(x,p,bad)
                elif location=='expected':fault['expected_revisions']=copy.deepcopy(bad)
                elif location=='proof-origin':p['origin_revisions']=copy.deepcopy(bad)
                elif location=='proof-current':p['revisions']=copy.deepcopy(bad)
                elif location=='context':x['revisions']=copy.deepcopy(bad)
                else:x['evidence']['RESET_SWEEP_CLEAR']['revisions']=copy.deepcopy(bad)
                positive=location=='proof-current' and label=='extra-known'
                with self.subTest(location=location,case=label):self.case(location+':'+label,x,p,'TRUE' if positive else 'UNKNOWN','IN_DOMAIN' if positive else 'OUT_OF_DOMAIN')
        for location in ['expected','proof-origin','proof-current','context']:
            x,p=fixture()
            if location=='expected':x['faults'][p['fault_id']].pop('expected_revisions')
            elif location=='context':x.pop('revisions')
            else:p.pop('origin_revisions' if location=='proof-origin' else 'revisions')
            self.case('missing:'+location,x,p,'UNKNOWN','OUT_OF_DOMAIN')

    def test_scoped_minimal_current_and_valid_advances(self):
        for n in [0,1,2**63]:
            x,p=fixture(n);self.case('positive-integer:'+str(n),x,p,'TRUE','IN_DOMAIN','ALLOWED_ASSUMED')
        for domain in ['FEED','RETENTION']:
            x,p=fixture();x['revisions'].pop(domain);self.case('unused-missing:'+domain,x,p,'TRUE','IN_DOMAIN')
            x,p=fixture();x['revisions'][domain]+=1;self.case('unused-changed:'+domain,x,p,'TRUE','IN_DOMAIN')
        x,p=fixture();required={'MATERIAL','AXIS','B_CLOSURE','EXIT_RECEIVER','HYDRAULIC','EVIDENCE','RESOURCES'}
        x['revisions']={d:x['revisions'][d] for d in required}
        for g,rec in x['evidence'].items():
            domains=next(r for r in C['guards'] if r['id']==g)['evidence_domains']
            rec['revisions']={d:rec['revisions'][d] for d in domains}
        self.case('minimum-scoped-context-and-entry',x,p,'TRUE','IN_DOMAIN')
        for advances in [1,2]:
            x,p=fixture();fid=p['fault_id']
            for _ in range(advances):x=L.change_subject(C,x,'B_CLOSURE')
            x=prepare(x,'RESTORE_B_CLOSURE','after-confirmed-advance');p=proof(x,fid)
            self.assertNotEqual(p['origin_revisions'],p['revisions'])
            self.case('confirmed-history:'+str(advances),x,p,'TRUE','IN_DOMAIN')
        for defect in ['no-history','gap','wrong-domain','wrong-type','missing-history']:
            x,p=fixture();fid=p['fault_id'];x=L.change_subject(C,x,'B_CLOSURE');x=prepare(x,'RESTORE_B_CLOSURE','bad-history');p=proof(x,fid);f=x['faults'][fid]
            if defect=='no-history':f['revision_history']=[]
            elif defect=='gap':f['revision_history'][0]['to_revision']=2
            elif defect=='wrong-domain':f['revision_history'][0]['domain']='FEED'
            elif defect=='wrong-type':f['revision_history'][0]['from_revision']=False
            else:f.pop('revision_history')
            self.case('unconfirmed-history:'+defect,x,p,'UNKNOWN','OUT_OF_DOMAIN')

    def test_partial_current_and_entry_requirements(self):
        for domain in ['B_CLOSURE','MATERIAL','AXIS','EXIT_RECEIVER','HYDRAULIC','EVIDENCE','RESOURCES']:
            x,p=fixture();x['revisions'].pop(domain)
            self.case('required-current-missing:'+domain,x,p,'UNKNOWN','OUT_OF_DOMAIN')
        x,p=fixture();x['evidence']['RESET_SWEEP_CLEAR']['revisions'].pop('AXIS')
        self.case('entry-partial-snapshot',x,p,'UNKNOWN','OUT_OF_DOMAIN')
        x,p=fixture();p['origin_revisions']['B_CLOSURE']=1
        self.case('stale-origin-binding',x,p,'UNKNOWN','IN_DOMAIN')
        x,p=fixture();p['revisions']['B_CLOSURE']=1
        self.case('stale-current-binding',x,p,'UNKNOWN','IN_DOMAIN')

    def test_invalid_proof_does_not_mask_resource_state_or_causal_denial(self):
        for denial in ['resource','state','causal']:
            x,p=fixture()
            if denial=='resource':x['evidence']['RESOURCES_READY']['value']='FALSE'
            elif denial=='state':x['state']='B_RAW_LOADED'
            else:
                rec=ev(x,'B-LOAD','FEED_CLEAR');rec['value']='FALSE'
                cause=L.latch(C,x,'FEED_CLEAR','ASSUMED_CAUSAL_DENIAL',rec)
                fid=L.latch(C,x,'B_RESET_CONFIRMED','ASSUMED_CAUSAL_CLOSURE',causes=[cause]);p=proof(x,fid)
            self.case('valid-proof-with-known-denial:'+denial,x,p,'FALSE','IN_DOMAIN','BLOCKED')
            p['origin_revisions']={}
            a,_=self.case('invalid-proof-with-known-denial:'+denial,x,p,'UNKNOWN','OUT_OF_DOMAIN','BLOCKED')
            self.assertEqual(a['policy_result'],'NOT_EVALUATED')

    def test_unrelated_fault_retained_and_normal_work_not_bypassed(self):
        x,p=fixture();fid=p['fault_id'];y=prepare(x,'B-LOAD','denied-feed');y['state']='B_ACCEPTABLE_INITIAL';y['evidence']['FEED_CLEAR']['value']='FALSE';x,_=L.decide(C,'B-LOAD',y)
        x['state']='B_RECEIVED_RESIDUAL';x=prepare(x,'RESTORE_B_CLOSURE','closure-only');p=proof(x,fid)
        _,out=self.case('closure-only-unrelated-feed-fault-retained',x,p,'TRUE','IN_DOMAIN')
        self.assertTrue(L.open_faults(out,'FEED_CLEAR'))
        ordinary=prepare(out,'B-COMPACT','ordinary-work');ordinary['state']='B_BATCH_SELECTED'
        self.assertEqual(L.evaluate(C,'B-COMPACT',ordinary,'ENTRY')['permission_outcome'],'BLOCKED')

    def test_consumed_entry_and_causal_fault_snapshots_use_their_own_domains(self):
        for relation,guard in [('entry','RESET_SWEEP_CLEAR'),('causal','FEED_CLEAR')]:
            for defect in ['valid','origin-empty','expected-empty','origin-bool','expected-float']:
                x,p=fixture();record=ev(x,'RESTORE_B_CLOSURE',guard);record['value']='FALSE'
                parent=L.latch(C,x,guard,'ASSUMED_USED_FAULT',record)
                if relation=='causal':
                    target=L.latch(C,x,'B_RESET_CONFIRMED','ASSUMED_USED_PARENT',causes=[parent]);p=proof(x,target)
                if defect.startswith('origin-'):
                    pointer={'fault_id':parent}
                    revisions={} if defect=='origin-empty' else {d:False for d in x['faults'][parent]['origin']['revisions']}
                    readdress(x,pointer,revisions)
                    if relation=='causal':
                        target=next(f['fault_id'] for f in x['faults'].values() if f['origin']['reason']=='ASSUMED_USED_PARENT')
                        p=proof(x,target)
                elif defect=='expected-empty':x['faults'][parent]['expected_revisions']={}
                elif defect=='expected-float':x['faults'][parent]['expected_revisions']={d:0.0 for d in x['faults'][parent]['expected_revisions']}
                valid=defect=='valid'
                a,_=self.case('used-'+relation+':'+defect,x,p,'FALSE' if valid else 'UNKNOWN','IN_DOMAIN' if valid else 'OUT_OF_DOMAIN','BLOCKED')
                if not valid:self.assertTrue(any(r['path'].startswith('faults.') for r in a['validation']['reasons']))

    def test_entry_snapshot_prevalidation_preserves_another_known_false(self):
        x,p=fixture();x['evidence']['RESOURCES_READY']['value']='FALSE'
        x['evidence']['RESET_SWEEP_CLEAR']['revisions']={}
        self.case('malformed-entry-with-known-resource-denial',x,p,'UNKNOWN','OUT_OF_DOMAIN','BLOCKED')

    def test_old_event_fault_is_not_a_consumed_entry_fault(self):
        for defect in ['origin-empty','expected-empty']:
            x,p=fixture();op=x['operation_id'];x['operation_id']='unrelated-old-operation'
            parent=L.latch(C,x,'EVENT_FRESH','ASSUMED_OLD_EVENT',truth='FALSE');x['operation_id']=op
            if defect=='origin-empty':readdress(x,{'fault_id':parent},{})
            else:x['faults'][parent]['expected_revisions']={}
            self.case('unconsumed-event-fault:'+defect,x,p,'TRUE','IN_DOMAIN','ALLOWED_ASSUMED')

    def test_malformed_consumed_structures_are_rejected_before_recovery(self):
        for defect in ['completed-history','recovered-history','attempt-history','entry-fault-guard','causal-record']:
            x,p=fixture()
            if defect=='completed-history':x['completed_operations']=None
            elif defect=='recovered-history':x['recovered_evidence']=None
            elif defect=='attempt-history':x['faults'][p['fault_id']].pop('resolution_attempts')
            elif defect=='entry-fault-guard':
                old=L.latch(C,x,'RESET_SWEEP_CLEAR','ASSUMED_MALFORMED_ENTRY')
                f=x['faults'].pop(old);f['origin'].pop('guard');new='F-'+L.digest(f['origin']);f['fault_id']=new;x['faults'][new]=f
            else:
                parent=L.latch(C,x,'FEED_CLEAR','ASSUMED_BAD_PARENT')
                target=L.latch(C,x,'B_RESET_CONFIRMED','ASSUMED_BAD_PARENT_TARGET',causes=[parent]);p=proof(x,target);x['faults'][parent]=None
            a,_=self.case('malformed-structure:'+defect,x,p,'UNKNOWN','OUT_OF_DOMAIN')
            self.assertEqual(a['policy_result'],'NOT_EVALUATED')

    def test_fixed_definitions_not_payload_maps_determine_domains(self):
        x,p=fixture();altered=copy.deepcopy(C);next(g for g in altered['guards'] if g['id']=='B_RESET_CONFIRMED')['evidence_domains']=[]
        a=S.recovery_assessment(p,x,altered);self.assertEqual(a['validation']['status'],'UNSUPPORTED');self.assertEqual(a['recovery_value'],'UNKNOWN')
        for field,value in [('guard','UNKNOWN_GUARD'),('action','UNKNOWN_ACTION'),('fault_id','F-'+'0'*64)]:
            q=copy.deepcopy(p);q[field]=value;a=S.recovery_assessment(q,x,C)
            self.assertNotEqual(a['recovery_value'],'TRUE');self.assertEqual(a['compatibility_domain'],'OUT_OF_DOMAIN')


if __name__=='__main__':unittest.main()
