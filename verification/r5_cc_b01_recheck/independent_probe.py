"""Independent R5 stateful oracle. Explicit ASSUMED fixtures, no physical tests.
Only the candidate helper and JSON are imported; author fixture/replay code is not.
"""
import copy, importlib.util, itertools, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
C=json.loads((ROOT/'verification/r4_cycle_contract/contract.json').read_text())
s=importlib.util.spec_from_file_location('candidate',ROOT/'verification/r4_cycle_contract/permission_examples.py')
L=importlib.util.module_from_spec(s);s.loader.exec_module(L)
S={t['id']:t for t in C['transitions']+C['recovery_actions']}
cases=[]
def log(name,expected,actual,**evidence):
 cases.append(dict(id=name,expected=expected,actual=actual,matches=expected==actual,**copy.deepcopy(evidence)))
def witness(x,a,g,value='TRUE',phase=None):
 return dict(scenario_id=x['scenario_id'],variant=x['variant'],mode=x['mode'],cycle_epoch=x['cycle_epoch'],subject_id=x['subject_id'],operation_id=x['operation_id'],action=a,guard=g,phase=phase or ('COMPLETION' if g in S[a]['completion_guards'] else 'ENTRY'),value=value,revisions=copy.deepcopy(x['revisions']),evidence_id='R5-independent:'+x['operation_id']+':'+g,method='EXPLICIT_ASSUMPTION',source='R5 independent synthetic input',valid_for_operation_interval=True)
def view(x,a,op,**changes):
 x=copy.deepcopy(x);x.update(changes);x['operation_id']=op;x['evidence']={g:witness(x,a,g) for g in S[a]['required_guards']};return x
def fresh(a,op='seed'):
 state=S[a]['from_states'][0]
 x=dict(scenario_id='R5-INDEPENDENT',variant='A' if state.startswith('A_') else 'B',mode=(S[a].get('allowed_modes') or C['state_modes'][state])[0],state=state,subject_id='X',batch_id='batch-X',cycle_epoch='epoch-X',basis_id='symbolic-mass-basis',basis_revision='r1',revisions={d:0 for d in C['evidence_policy']['domains']},inventory_refs=['X','Y'],pending_observations=[],material_assessment='ASSUMED_IDENTIFIED')
 x=L.initialize_history(x,'R5-independent-history',dict(value='TRUE',evidence_id='R5-initial-audit',source='explicit synthetic history audit'))
 return view(x,a,op)
def assess(name,x,a,expected,stage='COMMIT'):
 y,r=L.decide(C,a,x,stage);log(name,expected,r['permission_outcome'],before=x,after=y,result=r);return y
def ids(x,g):return [k for k,v in x['faults'].items() if v['status']=='OPEN' and v['origin']['guard']==g]
def audit_view(x,fid,op,a):
 orig=x['faults'][fid]['origin']['scope'];fields={k:v for k,v in orig.items() if k!='subject_kind'}
 return view(x,a,op,**fields)
def proof(x,fid,a):
 f=x['faults'][fid];p=witness(x,a,f['origin']['guard'],phase='RECOVERY_RESULT')
 p.update(fault_id=fid,target_scope=copy.deepcopy(f['origin']['scope']),origin_revisions=copy.deepcopy(f['origin']['revisions']))
 return p
def recover(name,x,fid,a,op,expected='ALLOWED_ASSUMED',mutate=None):
 q=audit_view(x,fid,op,a);p=proof(q,fid,a)
 if mutate:mutate(q,p)
 y,r=L.recover(C,a,q,fid,p);log(name,expected,r,before=q,proof=p,after=y);return y
# Full two-entity sequences, both insertion and recovery orders; inspect every prefix.
for insertion in itertools.permutations(['X','Y']):
 for order in itertools.permutations(['X','Y']):
  tag=''.join(insertion)+'-'+''.join(order);x=fresh('A-RECEIVE');fids={}
  for subject in insertion:
   q=view(x,'A-RECEIVE','denied-'+subject,subject_id=subject,batch_id='batch-'+subject,cycle_epoch='epoch-'+subject)
   q['evidence']['LEDGER_VALID']['value']='FALSE';x=assess(tag+'-loss-'+subject,q,'A-RECEIVE','BLOCKED')
   fids[subject]=next(k for k in ids(x,'LEDGER_VALID') if x['faults'][k]['origin']['scope']['subject_id']==subject)
  log(tag+'-two-independent-faults',2,len(ids(x,'LEDGER_VALID')))
  origins={k:copy.deepcopy(v['origin']) for k,v in x['faults'].items()};rejects=set(x['rejected_operation_ids'])
  for i,subject in enumerate(order):
   x=recover(tag+'-resolve-'+subject,x,fids[subject],'REASSESS_MATERIAL','audit-'+subject)
   log(tag+'-remaining-'+subject,1-i,len(ids(x,'LEDGER_VALID')))
   if i==0:
    dep=next(k for k in ids(x,'DEPENDENCY_VALID') if fids[order[1]] in x['faults'][k]['origin']['cause_fault_ids'])
    x=recover(tag+'-premature-history',x,dep,'RECONCILE_HISTORY','early-history','BLOCKED')
   assess(tag+'-READY-before-history-'+subject,view(x,'A-READY-EJECT','try-ready-'+subject,state='A_SEGMENT_READY'),'A-READY-EJECT','BLOCKED')
  for i,dep in enumerate(ids(x,'DEPENDENCY_VALID')):
   x=recover(tag+'-history-'+str(i),x,dep,'RECONCILE_HISTORY','history-'+str(i))
  log(tag+'-immutable-origins',origins,{k:x['faults'][k]['origin'] for k in origins})
  log(tag+'-rejections-retained',True,rejects<=set(x['rejected_operation_ids']))
  assess(tag+'-ready-restored',view(x,'A-READY-EJECT','ready-fresh',state='A_SEGMENT_READY'),'A-READY-EJECT','ALLOWED_ASSUMED')
  q=view(x,'A-EJECT','still-no-receiver',state='A_SEGMENT_READY');q['evidence']['RECEIVER_DEFINED']['value']='UNKNOWN'
  assess(tag+'-fresh-conditions-still-needed',q,'A-EJECT','INDETERMINATE')
# Wrong/incomplete/stale proofs; each failed request is followed by a new valid ID.
x=fresh('A-RECEIVE','material-loss');x['evidence']['LEDGER_VALID']['value']='FALSE';x=assess('seed-loss',x,'A-RECEIVE','BLOCKED');fid=ids(x,'LEDGER_VALID')[0]
for field in C['fault_policy']['identity_fields']+['subject_kind']:
 for bad in [None,'foreign']:
  y=recover('target-'+field+'-'+str(bad),x,fid,'REASSESS_MATERIAL','bad-'+field+str(bad),'INDETERMINATE',lambda q,p:p['target_scope'].__setitem__(field,bad))
  log('fault-remains-'+field+str(bad),'OPEN',y['faults'][fid]['status'])
  recover('new-unique-after-'+field+str(bad),y,fid,'REASSESS_MATERIAL','good-'+field+str(bad))
for field in ['fault_id','source','method','evidence_id','origin_revisions','revisions','valid_for_operation_interval']:
 y=recover('missing-'+field,x,fid,'REASSESS_MATERIAL','missing-'+field,'INDETERMINATE',lambda q,p:p.pop(field))
 log('missing-retains-'+field,'OPEN',y['faults'][fid]['status'])
for domain in x['faults'][fid]['origin']['revisions']:
 y=recover('stale-'+domain,x,fid,'REASSESS_MATERIAL','stale-'+domain,'INDETERMINATE',lambda q,p:p['revisions'].__setitem__(domain,p['revisions'][domain]+1))
 log('stale-retains-'+domain,'OPEN',y['faults'][fid]['status'])
# Cumulative rejected IDs, changed subjects/epochs, roundtrip and recovery.
x=fresh('REASSESS_MATERIAL')
for n in ['A','B','C']:
 q=view(x,'REASSESS_MATERIAL',n);q['evidence']['AUDIT_CHANNEL_READY']['value']='UNKNOWN'
 x=assess('reject-chain-'+n,q,'REASSESS_MATERIAL','INDETERMINATE','ENTRY')
for n,subject,epoch in itertools.product(['A','B','C'],['X','Y'],['epoch-X','epoch-new']):
 assess('replay-'+n+subject+epoch,view(x,'REASSESS_MATERIAL',n,subject_id=subject,cycle_epoch=epoch),'REASSESS_MATERIAL','BLOCKED','ENTRY')
log('all-rejected-ids',['A','B','C'],x['rejected_operation_ids'])
snapshot=L.export_context(x);restored=L.restore_context(json.loads(json.dumps(snapshot)),snapshot['sha256'])
log('roundtrip-ids',x['rejected_operation_ids'],restored['rejected_operation_ids'])
assess('roundtrip-replay',view(restored,'REASSESS_MATERIAL','A'),'REASSESS_MATERIAL','BLOCKED','ENTRY')
assess('roundtrip-unique',view(restored,'REASSESS_MATERIAL','D'),'REASSESS_MATERIAL','ALLOWED_ASSUMED','ENTRY')
assess('untrusted-history',view(L.restore_context(snapshot),'REASSESS_MATERIAL','D'),'REASSESS_MATERIAL','INDETERMINATE','ENTRY')
# Exhaustive FALSE/UNKNOWN conjunction and phase distinction, independently specified oracle.
for action,guards in [('A-EJECT',['RECEIVER_DEFINED','RESOURCES_READY','PARTITION_DEFINED']),('B-COMPACT',['B_RESET_CONFIRMED','RESOURCES_READY','COMPACTION_CRITERION']),('B-RESET',['RESTORE_SEQUENCE_DEFINED','RESOURCES_READY','B_RESET_CONFIRMED'])]:
 for stage in ['ENTRY','COMMIT']:
  for vals in itertools.product(['TRUE','FALSE','UNKNOWN'],repeat=3):
   q=fresh(action)
   for g,v in zip(guards,vals):q['evidence'][g]['value']=v
   relevant=[v for g,v in zip(guards,vals) if stage=='COMMIT' or g not in S[action]['completion_guards']]
   expected='BLOCKED' if 'FALSE' in relevant else 'INDETERMINATE' if 'UNKNOWN' in relevant else 'ALLOWED_ASSUMED'
   y=assess(action+'-'+stage+'-'+''.join(v[0] for v in vals),q,action,expected,stage)
   if stage=='ENTRY' or expected!='ALLOWED_ASSUMED':log('no-premature-state-'+cases[-1]['id'],q['state'],y['state'])
# Failed COMMIT consumes ID; fresh completion does not retroactively authorize it.
x=fresh('B-COMPACT','press');x['evidence']['COMPACTION_CRITERION']['value']='UNKNOWN'
x=assess('start-without-product',x,'B-COMPACT','ALLOWED_ASSUMED','ENTRY')
x=assess('no-completion-no-commit',x,'B-COMPACT','INDETERMINATE')
assess('replay-cannot-retroauthorize',view(x,'B-COMPACT','press'),'B-COMPACT','BLOCKED')
# Facts after denial: conservation of refs/unknown mass, no second accounting or grant.
x=fresh('B-LOAD','load-denied');x['evidence']['RESOURCES_READY']['value']='FALSE';x=assess('load-denied',x,'B-LOAD','BLOCKED')
ob=dict(event_id='dose-observed',subject_id='X',inventory_refs=['X','Y'],mass_record=None)
y,r=L.record_fact(C,x,ob,'BLOCKED')
log('fact-no-permission','NOT_GRANTED_BY_OBSERVATION',r['process_permission']);log('fact-state',x['state'],y['state']);log('fact-inventory',x['inventory_refs'],y['inventory_refs']);log('unknown-mass',None,y['pending_observations'][0]['mass_record'])
z,r=L.record_fact(C,y,ob,'BLOCKED');log('duplicate-no-second-record',y['pending_observations'],z['pending_observations'])
assess('fact-cannot-ready',view(z,'B-READY-LOAD','post-fact-ready'),'B-READY-LOAD','BLOCKED')
# Stale evaluation cannot commit after a new observed fact.
q=fresh('B-LOAD','changed-context');r=L.evaluate(C,'B-LOAD',q,'ENTRY');changed,_=L.record_fact(C,q,ob,'INDETERMINATE')
try:L.propagate(C,changed,r)
except ValueError:log('stale-evaluation-binding','REJECTED','REJECTED')
else:log('stale-evaluation-binding','REJECTED','ACCEPTED')
# Normative table rows and READY bindings compared mechanically to JSON.
text=(ROOT/'verification/r4_cycle_contract/action_conditions.md').read_text();rows={line.split('|')[1].strip():line.split('|') for line in text.splitlines() if line.startswith('| ')}
for a,t in S.items():
 if a not in rows:log('text-row-'+a,True,False);continue
 row=rows[a]
 if a not in {r['id'] for r in C['recovery_actions']}:
  for col,key in [(4,'entry_guards'),(5,'completion_guards')]:
   found={v.strip() for v in row[col].split(',') if v.strip() not in {'нет отдельной цели','нет',''}}
   log('text-json-'+a+'-'+key,set(t[key])==found,True)
 for binding in t.get('ready_bindings',[]):
  log('ready-subset-'+a,True,set(C['ready_targets'][binding['target']]['required_guards'])<=set(t['entry_guards']))
result=dict(reviewed_C='0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed',session_id='r5-cc-b01-20261112',count=len(cases),failures=[x for x in cases if not x['matches']],cases=cases,physical_tests='NOT_RUN',G1='OPEN')
print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(bool(result['failures']))
