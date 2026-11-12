#!/usr/bin/env python3
"""Readonly documentary checks under ARB-R1-CC-01, never physical validation."""
from copy import deepcopy
import itertools,json,subprocess,sys,tempfile
from pathlib import Path
from fixtures import C,L,ROOT,evidence,fresh,retarget,failed_material,one,query,proof
HERE=Path(__file__).resolve().parent
OLD='4f31ed624336e1101b0ba04857f4316c73e4d375'
REVIEW='c56e494a2e89ffa65b5876bfce6a4d6b4ae62f1b'

def baseline():
 with tempfile.TemporaryDirectory(prefix='rev-cc-rejection-baseline-') as tmp:
  dest=Path(tmp)
  files=subprocess.check_output(['git','ls-tree','-r','--name-only',OLD,'--','verification/r4_cycle_contract'],cwd=ROOT,text=True).splitlines()
  files+=['verification/r5_r4_cycle_contract_review/independent_results.json','verification/r5_r4_cycle_contract_recheck/independent_probe.py']
  for name in files:
   commit=REVIEW if '/r5_r4_cycle_contract_recheck/' in name else OLD
   p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT))
  r=subprocess.run([sys.executable,'-B',str(dest/files[-1])],capture_output=True,text=True)
  assert r.returncode==0,r.stderr
  assert json.loads(r.stdout)==json.loads((ROOT/'verification/r1_cc_arbitration/reproduced_results.json').read_text())
  print(r.stdout,end='')

def main():
 if sys.argv[1:]==['--baseline-second-rejection']:baseline();return
 if sys.argv[1:]:raise ValueError('unsupported option')
 replay=subprocess.run([sys.executable,'-B',str(HERE/'replay_r5.py')],cwd=ROOT,capture_output=True,text=True)
 assert replay.returncode==0,replay.stderr
 r5=json.loads(replay.stdout)
 cases=[]
 def record(id,expected,actual,**detail):
  cases.append(dict(id=id,expected=expected,actual=actual,matches=expected==actual,**detail))
 def check(id,action,ctx,expected,stage='COMMIT'):
  r=L.evaluate(C,action,ctx,stage);record(id,expected,r['permission_outcome'],result=r);return r
 # Independent records: both insertion orders and both recovery orders.
 for insertion in itertools.permutations(['X','Y']):
  for recovery_order in itertools.permutations(['X','Y']):
   ctx=failed_material('material-'+insertion[0],'batch-'+insertion[0])
   q=retarget(ctx,'A-RECEIVE','loss-material-'+insertion[1],subject_id='material-'+insertion[1],batch_id='batch-'+insertion[1],cycle_epoch='epoch-batch-'+insertion[1])
   q['evidence']['LEDGER_VALID']['value']='FALSE';ctx,_=L.decide(C,'A-RECEIVE',q)
   fids={s:one(ctx,'LEDGER_VALID','material-'+s) for s in ['X','Y']}
   assert len(L.open_faults(ctx,'LEDGER_VALID'))==2 and len(set(fids.values()))==2
   before=deepcopy(ctx);origins={fid:deepcopy(f['origin']) for fid,f in ctx['faults'].items()}
   order=''.join(insertion)+'-'+''.join(recovery_order)
   first,second=recovery_order
   q=query(ctx,fids[first],'audit-'+order+'-'+first)
   ctx,status=L.recover(C,'REASSESS_MATERIAL',q,fids[first],proof(q,'REASSESS_MATERIAL',fids[first]))
   record('independent-faults-partial-'+order,'ALLOWED_ASSUMED',status,before=before,after=deepcopy(ctx))
   assert ctx['faults'][fids[second]]['status']=='OPEN' and ctx['faults'][fids[first]]['status']=='RESOLVED'
   unresolved=[f for f in L.open_faults(ctx,'DEPENDENCY_VALID') if any(ctx['faults'][p]['status']=='OPEN' for p in f['origin']['cause_fault_ids'])]
   assert unresolved
   dep=unresolved[0]['fault_id'];q=query(ctx,dep,'premature-history-'+order)
   trial,status=L.recover(C,'RECONCILE_HISTORY',q,dep,proof(q,'RECONCILE_HISTORY',dep))
   record('partial-recovery-does-not-close-causal-history-'+order,'BLOCKED',status)
   assert trial['faults'][fids[second]]['status']=='OPEN'
   q=query(trial,fids[second],'audit-'+order+'-'+second)
   ctx,status=L.recover(C,'REASSESS_MATERIAL',q,fids[second],proof(q,'REASSESS_MATERIAL',fids[second]))
   record('second-addressed-recovery-'+order,'ALLOWED_ASSUMED',status)
   for dep in [f['fault_id'] for f in L.open_faults(ctx,'DEPENDENCY_VALID')]:
    q=query(ctx,dep,'history-'+dep)
    ctx,status=L.recover(C,'RECONCILE_HISTORY',q,dep,proof(q,'RECONCILE_HISTORY',dep))
    record('legitimate-history-'+order+'-'+dep,'ALLOWED_ASSUMED',status)
   assert all(ctx['faults'][fid]['origin']==origin for fid,origin in origins.items())
   assert set(before['rejected_operation_ids'])<=set(ctx['rejected_operation_ids'])
   check('fresh-action-after-addressed-recovery-'+order,'A-RECEIVE',retarget(ctx,'A-RECEIVE','new-action-'+order),'ALLOWED_ASSUMED')
 # Every address field and missing/foreign original evidence.
 original=failed_material();fid=one(original,'LEDGER_VALID');origin=deepcopy(original['faults'][fid]['origin'])
 for field in C['fault_policy']['identity_fields']+['subject_kind']:
  for value in [None,'unrelated-'+field]:
   q=query(original,fid,'bad-address-'+field+'-'+str(value));p=proof(q,'REASSESS_MATERIAL',fid);p['target_scope'][field]=value
   after,status=L.recover(C,'REASSESS_MATERIAL',q,fid,p)
   record('wrong-target-'+field+'-'+str(value),'INDETERMINATE',status)
   assert after['faults'][fid]['status']=='OPEN' and after['faults'][fid]['origin']==origin
 for field in ['subject_id','batch_id','cycle_epoch','basis_id','basis_revision']:
  q=query(original,fid,'wrong-view-'+field);q=retarget(q,'REASSESS_MATERIAL',q['operation_id'],**{field:'other'})
  after,status=L.recover(C,'REASSESS_MATERIAL',q,fid,proof(q,'REASSESS_MATERIAL',fid))
  record('fresh-proof-for-wrong-current-view-'+field,'INDETERMINATE',status)
  assert after['faults'][fid]['status']=='OPEN'
 for field in ['basis_id','basis_revision']:
  x=fresh('A-RECEIVE',**{field:None});x['evidence']['LEDGER_VALID']['value']='FALSE';x,_=L.decide(C,'A-RECEIVE',x);f=one(x,'LEDGER_VALID');q=query(x,f,'unknown-origin-'+field)
  after,status=L.recover(C,'REASSESS_MATERIAL',q,f,proof(q,'REASSESS_MATERIAL',f))
  record('unknown-origin-is-not-null-equality-'+field,'INDETERMINATE',status)
 for kind in ['UNKNOWN','FALSE','missing-fault-id','missing-method','stale-revision','wrong-origin-revision','float-origin-revision','bool-origin-revision','manual-revision-jump']:
  q=query(original,fid,'bad-proof-'+kind);p=proof(q,'REASSESS_MATERIAL',fid)
  if kind in ['UNKNOWN','FALSE']:p['value']=kind
  if kind=='missing-fault-id':p.pop('fault_id')
  if kind=='missing-method':p.pop('method')
  if kind=='stale-revision':p['revisions']['MATERIAL']+=1
  if kind=='wrong-origin-revision':p['origin_revisions']['MATERIAL']+=1
  if kind=='float-origin-revision':p['origin_revisions']['MATERIAL']=0.0
  if kind=='bool-origin-revision':p['origin_revisions']['MATERIAL']=False
  if kind=='manual-revision-jump':q['revisions']['MATERIAL']+=1;p=proof(q,'REASSESS_MATERIAL',fid)
  after,status=L.recover(C,'REASSESS_MATERIAL',q,fid,p)
  record('insufficient-proof-'+kind,'BLOCKED' if kind=='FALSE' else 'INDETERMINATE',status)
  assert after['faults'][fid]['status']=='OPEN'
 # Genuine scoped revision update keeps original identity but permits new proof.
 x=L.change_subject(C,original,'MATERIAL');assert x['faults'][fid]['origin']==origin
 q=query(x,fid,'correct-current-revision');after,status=L.recover(C,'REASSESS_MATERIAL',q,fid,proof(q,'REASSESS_MATERIAL',fid))
 record('correct-current-revision-addresses-old-origin','ALLOWED_ASSUMED',status,before=original,after=after)
 foreign=retarget(original,'REASSESS_MATERIAL','foreign-revision',subject_id='other');foreign=L.change_subject(C,foreign,'MATERIAL')
 assert foreign['faults'][fid]['expected_revisions']==original['faults'][fid]['expected_revisions']
 record('foreign-version-change-does-not-rewrite-old-fault','PRESERVED','PRESERVED')
 q=query(original,fid,'missing-explicit-address');p=proof(q,'REASSESS_MATERIAL',fid)
 after,status=L.recover(C,'REASSESS_MATERIAL',q,'LEDGER_VALID',p)
 record('guard-name-is-not-fault-address','INDETERMINATE',status)
 q=query(original,fid,'wrong-proof-guard');p=proof(q,'REASSESS_MATERIAL',fid);p['guard']='INVENTORY_KNOWN'
 after,status=L.recover(C,'REASSESS_MATERIAL',q,fid,p)
 record('wrong-guard-is-not-resolution-evidence','INDETERMINATE',status)
 x=fresh('A-RECEIVE');x['evidence']['LEDGER_VALID']['value']='FALSE';r=L.evaluate(C,'A-RECEIVE',x)
 foreign=retarget(x,'A-RECEIVE','another-request',subject_id='another-subject')
 try:L.propagate(C,foreign,r)
 except ValueError:record('old-evaluation-cannot-be-rebound-to-new-subject','CONTEXT_REJECTED','CONTEXT_REJECTED')
 else:record('old-evaluation-cannot-be-rebound-to-new-subject','CONTEXT_REJECTED','UNSAFE_REBINDING')
 # Complete rejection memory, including export/import and changes of view.
 for chain in [('A','B','A'),('A','B','C','A')]:
  x=fresh('REASSESS_MATERIAL')
  for name in chain[:-1]:
   q=retarget(x,'REASSESS_MATERIAL','rejected-'+name);q['evidence']['EVENT_FRESH']['value']='FALSE';x,r=L.decide(C,'REASSESS_MATERIAL',q,'ENTRY');assert r['permission_outcome']=='BLOCKED'
  before=deepcopy(x)
  for view in [{},{'subject_id':'other'},{'cycle_epoch':'other-epoch'},{'basis_id':'other-basis'}]:
   q=retarget(x,'REASSESS_MATERIAL','rejected-'+chain[-1],**view)
   check('rejection-memory-'+''.join(chain)+'-'+str(view),'REASSESS_MATERIAL',q,'BLOCKED','ENTRY')
  q=retarget(x,'REASSESS_MATERIAL','unique-'+''.join(chain));check('new-unique-audit-'+''.join(chain),'REASSESS_MATERIAL',q,'ALLOWED_ASSUMED','ENTRY')
  snap=L.export_context(x);restored=L.restore_context(json.loads(json.dumps(snap)),snap['sha256'])
  assert restored['rejected_operation_ids']==x['rejected_operation_ids'] and restored['faults']==x['faults']
  check('rejected-id-after-restoration-'+''.join(chain),'REASSESS_MATERIAL',retarget(restored,'REASSESS_MATERIAL','rejected-A'),'BLOCKED','ENTRY')
  unknown=L.restore_context(snap)
  check('untrusted-history-is-not-clean-'+''.join(chain),'REASSESS_MATERIAL',retarget(unknown,'REASSESS_MATERIAL','untrusted-new'),'INDETERMINATE','ENTRY')
  tampered=deepcopy(snap);tampered['payload']['rejected_operation_ids']=[];tampered['payload']['rejected_operations']={};tampered['sha256']=L.digest(tampered['payload'])
  unknown=L.restore_context(tampered,snap['sha256'])
  check('changed-history-with-updated-local-hash-'+''.join(chain),'REASSESS_MATERIAL',retarget(unknown,'REASSESS_MATERIAL','tampered-new'),'INDETERMINATE','ENTRY')
  record('all-rejected-ids-retained-'+''.join(chain),'PRESERVED','PRESERVED',before=before,after=restored)
 # Recovery of a separate material fault must not erase older rejected A/B/C.
 q=retarget(x,'A-RECEIVE','new-material-loss',state='A_OUTSIDE_PENDING',mode='A_STEADY');q['evidence']['LEDGER_VALID']['value']='FALSE';mixed,_=L.decide(C,'A-RECEIVE',q)
 material=one(mixed,'LEDGER_VALID');q=query(mixed,material,'unrelated-addressed-recovery')
 recovered,status=L.recover(C,'REASSESS_MATERIAL',q,material,proof(q,'REASSESS_MATERIAL',material))
 record('other-fault-recovery-is-addressed','ALLOWED_ASSUMED',status)
 assert set(mixed['rejected_operation_ids'])<=set(recovered['rejected_operation_ids'])
 for name in ['A','B','C']:
  check('old-ID-after-other-fault-recovery-'+name,'REASSESS_MATERIAL',retarget(recovered,'REASSESS_MATERIAL','rejected-'+name),'BLOCKED','ENTRY')
 # An invalid normal request can be reconciled, but its ID stays rejected forever.
 x=fresh('B-NEXT',operation_id='invalid-normal-A');x['evidence']['EVENT_FRESH']['value']='FALSE';x,_=L.decide(C,'B-NEXT',x)
 event=one(x,'EVENT_FRESH');dep=one(x,'DEPENDENCY_VALID');q=query(x,event,'unique-ack-request')
 x,status=L.recover(C,'RECONCILE_HISTORY',q,event,proof(q,'RECONCILE_HISTORY',event,ack_request=True))
 record('addressed-rejection-ack-does-not-deadlock-history','ALLOWED_ASSUMED',status)
 q=query(x,dep,'unique-history');x,status=L.recover(C,'RECONCILE_HISTORY',q,dep,proof(q,'RECONCILE_HISTORY',dep))
 record('history-after-addressed-rejection-ack','ALLOWED_ASSUMED',status)
 check('new-normal-request-after-reconciliation','B-NEXT',retarget(x,'B-NEXT','new-normal-B'),'ALLOWED_ASSUMED')
 check('old-normal-id-remains-forbidden-after-recovery','B-NEXT',retarget(x,'B-NEXT','invalid-normal-A'),'BLOCKED')
 # Unknown prerequisites and partial B restoration retain earlier strictness.
 for action,fields in [('A-EJECT',['RECEIVER_DEFINED','RESOURCES_READY','PARTITION_DEFINED']),('B-COMPACT',['B_RESET_CONFIRMED','RESOURCES_READY']),('A-STARTUP-RETURN-A_COLUMN_ESTABLISHED',['RETAINED_STABLE','A_REACTION_DEFINED'])]:
  for values in itertools.product(['TRUE','FALSE','UNKNOWN'],repeat=len(fields)):
   x=fresh(action)
   for g,v in zip(fields,values):x['evidence'][g]['value']=v
   expected='BLOCKED' if 'FALSE' in values else 'INDETERMINATE' if 'UNKNOWN' in values else 'ALLOWED_ASSUMED'
   check('composite-'+action+'-'+''.join(v[0] for v in values),action,x,expected)
 # No conditions removed from either earlier contract.
 for commit in ['3cf32daef67a91f393b808adb0dc07ba4c73cac2',OLD]:
  previous=json.loads(subprocess.check_output(['git','show',commit+':verification/r4_cycle_contract/contract.json'],cwd=ROOT))
  current={t['id']:t for t in C['transitions']}
  assert all(set(t['required_guards'])<=set(current[t['id']]['required_guards']) for t in previous['transitions'])
 # Both original review trees and R1 decision/evidence remain byte-identical.
 audit=json.loads((HERE/'input_audit.json').read_text())
 for path,tree in audit['review_trees'].items():
  assert subprocess.check_output(['git','rev-parse','HEAD:'+path],cwd=ROOT,text=True).strip()==tree
  assert not subprocess.check_output(['git','diff','HEAD','--',path],cwd=ROOT)
 assert (ROOT/'decisions/ARB-R1-CC-01.md').read_bytes()==subprocess.check_output(['git','show',audit['decision']+':decisions/ARB-R1-CC-01.md'],cwd=ROOT)
 assert subprocess.check_output(['git','rev-parse',audit['decision']+':verification/r1_cc_arbitration'],cwd=ROOT,text=True).strip()==audit['r1_evidence_tree']
 assert not subprocess.check_output(['git','diff',audit['decision'],'--','verification/r1_cc_arbitration'],cwd=ROOT)
 bad=[x for x in cases if not x['matches']]
 result=dict(scope='DOCUMENTARY_B01_CORRECTION_ONLY',command_execution='COMPLETED',decision=audit['decision'],consecutive_rejections=2,
  original_R5_cases=r5['original_26_cases'],recheck_R5_cases=r5['new_cases'],original_26_matches=r5['original_26_matches'],recheck_45_mismatches=r5['mismatch_count'],
  arbitration_cases=cases,arbitration_case_count=len(cases),mismatches=bad,expectations_match=not bad,total_checks=26+45+len(cases),
  original_required_guards='PRESERVED',independent_RECHECK='NOT_RUN',B01='OPEN',W02='OPEN_OUT_OF_SCOPE',physical_workability='INDETERMINATE',G1='OPEN')
 print(json.dumps(result,ensure_ascii=False,indent=2))
 if bad:sys.exit(1)

if __name__=='__main__':main()
