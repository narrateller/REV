"""Fixed-contract oracle for all OPEN records. Candidate classifier is observed only.
No candidate fixture, guard list, or classification result supplies expectations.
"""
from pathlib import Path
from collections import Counter
import copy,hashlib,itertools,json,sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'verification/r5_ci_snapshots_recheck'))
from fixtures import C,L,G,A,fixture,proof,prepare
sys.path.insert(0,str(ROOT/'verification/r4_cycle_interfaces/proposal'))
import semantic_minimum as S
import recovery_snapshots as R
ROWS=[]
def run(name,x,p,admission,gate,scope=None,invalid=None):
 x['pending_observations']=[{'event_id':'R5-independent-pending','value':'UNKNOWN'}]
 original=copy.deepcopy((x,p,C));serialized=json.dumps([x,p,C],ensure_ascii=False);before=L.digest([x,p,C])
 a=S.recovery_assessment(p,x,C);j=a.get('journal_admission',{})
 tests={'admission':j.get('value')==admission,'gate':a['action_gate']==gate,'readonly':original==(x,p,C) and serialized==json.dumps([x,p,C],ensure_ascii=False) and before==L.digest([x,p,C]),'physical_permission_false':a['physical_permission'] is False,'all_records_visited':j.get('records_seen')==len(x['faults'])}
 if scope is not None:tests['scoped']=a['recovery_value']==scope
 if admission=='UNKNOWN':tests.update(outside=a['compatibility_domain']=='OUT_OF_DOMAIN',no_policy=a['policy_result']=='NOT_EVALUATED',no_recovery=a['recovery_value']!='TRUE',no_positive_journal=all(r['value']!='TRUE' for r in a['journal_evidence'].values()))
 if invalid:tests['invalid_record_classified']=any(r['fault_id']==invalid and r['classification']=='UNCLASSIFIABLE' and r['reasons'] for r in j['records'])
 row=dict(id=name,expected=dict(admission=admission,gate=gate,scoped=scope),actual=dict(admission=j.get('value'),gate=a['action_gate'],scoped=a['recovery_value']),checks=tests,matched=all(tests.values()),typed_input_sha256=before,ordered_input_sha256=hashlib.sha256(serialized.encode()).hexdigest(),records_seen=j.get('records_seen'),unclassifiable=j.get('unclassifiable'))
 if not row['matched']:row.update(context=x,proof=p,assessment=a)
 ROWS.append(row)
 return a

def added(x,g,reason):return L.latch(C,x,g,reason,truth='UNKNOWN')
def mutate(x,key,fn):
 items=list(x['faults'].items());i=next(i for i,(k,_) in enumerate(items) if k==key);f=items[i][1];fn(f)
 new='F-'+L.digest(f.get('origin'));f['fault_id']=new;items[i]=(new,f);x['faults']=dict(items);return new

def place(x,key,pos):
 f=x['faults'].pop(key);items=list(x['faults'].items());i={'first':0,'middle':len(items)//2,'last':len(items)}[pos];items.insert(i,(key,f));x['faults']=dict(items)

def mfield(obj,key):
 return lambda f:f[obj].pop(key)

# Known fixed namespace and non-applicable records: no blanket BLOCKED.
for g in G:
 x,p=fixture(0);key=added(x,g,'R5-known-'+g)
 own=g in A['entry_guards']
 a=run('namespace:'+g,x,p,'TRUE','INDETERMINATE' if own else 'ALLOWED_ASSUMED','UNKNOWN' if own else 'TRUE')
 row=next(r for r in a['journal_admission']['records'] if r['fault_id']==key)
 expected='APPLICABLE' if own or g in A['may_reestablish'] else 'NOT_APPLICABLE'
 ROWS[-1]['checks']['fixed_roles']=row['classification']==expected
 ROWS[-1]['matched']=all(ROWS[-1]['checks'].values())

# Each guard: mandatory classification fields and its OWN domains from fixed C.
for g,definition in G.items():
 domains=definition['evidence_domains'];mutations=[]
 for field in C['fault_policy']['identity_fields']+['subject_kind']:
  mutations.append(('scope-missing:'+field,lambda f,k=field:f['origin']['scope'].pop(k)))
 for val in [None,False,0,[],{},'', 'R5_NOT_IN_FIXED_NAMESPACE']:
  mutations.append(('guard:'+repr(val),lambda f,v=val:f['origin'].__setitem__('guard',copy.deepcopy(v))))
 mutations.append(('guard:missing',lambda f:f['origin'].pop('guard')))
 for obj in ['origin','expected']:
  for d in domains:
   def missing(f,o=obj,d=d):
    (f['origin']['revisions'] if o=='origin' else f['expected_revisions']).pop(d)
   mutations.append((obj+':missing:'+d,missing))
  for val in [None,False,0.0,-1,'0']:
   def badcounter(f,o=obj,v=val,d=domains[0]):
    (f['origin']['revisions'] if o=='origin' else f['expected_revisions'])[d]=v
   mutations.append((obj+':counter:'+repr(val),badcounter))
 for name,fn in [('status:unknown',lambda f:f.__setitem__('status','R5_UNKNOWN_STATUS')),('truth:missing',lambda f:f['origin'].pop('truth')),('history:missing',lambda f:f.pop('revision_history')),('causal:missing',lambda f:f['origin'].pop('cause_fault_ids')),('causal:unknown',lambda f:f['origin'].__setitem__('cause_fault_ids',['F-'+'f'*64]))]:mutations.append((name,fn))
 for name,fn in mutations:
  for truth in ['TRUE','FALSE','UNKNOWN']:
   x,p=fixture(0);good=added(x,'FEED_CLEAR','R5-independent-known-feed');key=added(x,g,'R5-independent-mutant:'+g+name);key=mutate(x,key,fn)
   x['evidence']['RESOURCES_READY']['value']=truth
   # `_raw_value` is fixed and independent of candidate journal reader.
   assert L._raw_value(C,A['id'],'RESOURCES_READY',x,x['evidence']['RESOURCES_READY'],'ENTRY')[0]==truth
   run('all-guards:'+g+':'+name+':'+truth,x,p,'UNKNOWN','BLOCKED' if truth=='FALSE' else 'INDETERMINATE','UNKNOWN',key)

# Positional combinations: known supported entries and two independent unknowns;
# all 120 permutations and all raw truth combinations of two own guards.
for order in itertools.permutations(range(5)):
 for raw1,raw2 in [('TRUE','TRUE'),('TRUE','UNKNOWN'),('UNKNOWN','TRUE'),('FALSE','TRUE'),('TRUE','FALSE'),('FALSE','UNKNOWN'),('UNKNOWN','FALSE'),('UNKNOWN','UNKNOWN'),('FALSE','FALSE')]:
  x,p=fixture(0);good=added(x,'FEED_CLEAR','R5-combination-known');bad1=added(x,'FEED_CLEAR','R5-combination-null');bad1=mutate(x,bad1,lambda f:f['origin'].__setitem__('guard',None));bad2=added(x,'TOOLS_HOME','R5-combination-unknown');bad2=mutate(x,bad2,lambda f:f['origin'].__setitem__('guard','R5_UNDECLARED'))
  items=list(x['faults'].items());assert len(items)==5;x['faults']={items[i][0]:items[i][1] for i in order}
  x['evidence']['RESOURCES_READY']['value']=raw1;x['evidence']['METHOD_SUPPORTED']['value']=raw2
  run('permutation:'+''.join(map(str,order))+':'+raw1+':'+raw2,x,p,'UNKNOWN','BLOCKED' if 'FALSE' in (raw1,raw2) else 'INDETERMINATE','UNKNOWN',bad1)

# FEED guard with complete but historical scope/revisions remains admissible:
# no current physical reproof for unrelated history.
for position in ['first','middle','last']:
 for value in ['TRUE','FALSE','UNKNOWN']:
  x,p=fixture(0);key=added(x,'FEED_CLEAR','R5-foreign-historical')
  def historical(f):
   f['origin']['truth']=value;f['origin']['scope'].update(subject_id='R5-historical-other-subject',batch_id='R5-historical-batch',cycle_epoch='R5-older-epoch')
   for d in G['FEED_CLEAR']['evidence_domains']:f['origin']['revisions'][d]=100;f['expected_revisions'][d]=100
  key=mutate(x,key,historical);place(x,key,position)
  run('known-FEED-history:'+position+':'+value,x,p,'TRUE','ALLOWED_ASSUMED','TRUE')

# Apply a complete, justified historical advance, including large exact counters.
for start in [0,1,10**30]:
 x,p=fixture(start);run('positive-addressed:'+str(start),x,p,'TRUE','ALLOWED_ASSUMED','TRUE')
 x=L.change_subject(C,x,'B_CLOSURE');p=proof(x,p['fault_id']);run('advance-with-stale-entry:'+str(start),x,p,'TRUE','INDETERMINATE','UNKNOWN')
 x=prepare(x,A['id'],x['operation_id']);p=proof(x,p['fault_id']);run('positive-addressed-advance:'+str(start),x,p,'TRUE','ALLOWED_ASSUMED','TRUE')

# Checked history policy intentionally leaves unrelated RESOLVED records opaque;
# OPEN unknowns must still be scanned after them and after a valid target.
for place_bad in ['first','middle','last']:
 x,p=fixture(0);key=added(x,'FEED_CLEAR','R5-resolved-history');x['faults'][key]['status']='RESOLVED'
 key=mutate(x,key,lambda f:f['origin'].__setitem__('guard',None))
 run('resolved-unconsumed-history:'+place_bad,x,p,'TRUE','ALLOWED_ASSUMED','TRUE')
 bad=added(x,'FEED_CLEAR','R5-open-after-resolved');bad=mutate(x,bad,lambda f:f['origin'].__setitem__('guard',None));place(x,bad,place_bad)
 run('resolved-does-not-hide-OPEN:'+place_bad,x,p,'UNKNOWN','INDETERMINATE','UNKNOWN',bad)

# Independent TRUE/FALSE state, own latch and addressed causal dominance.
for kind in ['raw','state','own','causal']:
 for position in ['first','middle','last']:
  x,p=fixture(0)
  if kind=='raw':x['evidence']['RESOURCES_READY']['value']='FALSE'
  elif kind=='state':x['state']=next(s for s in C['state_modes'] if s not in A['from_states'])
  elif kind=='own':L.latch(C,x,'METHOD_SUPPORTED','R5-known-own-prohibition',truth='FALSE')
  else:
   parent=L.latch(C,x,'FEED_CLEAR','R5-addressed-causal',truth='FALSE');target=L.latch(C,x,'B_RESET_CONFIRMED','R5-causal-target',causes=[parent]);p=proof(x,target)
  bad=added(x,'FEED_CLEAR','R5-incomplete-classification');bad=mutate(x,bad,lambda f:f['origin']['scope'].pop('subject_kind'));place(x,bad,position)
  run('known-FALSE:'+kind+':'+position,x,p,'UNKNOWN','BLOCKED','UNKNOWN',bad)

summary=dict(reviewed_C='8b72716021b0c3a64972033d09fe5e80945eb98e',session_id='r5-ci-open-journal-20261113',fixed_contract='0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed',count=len(ROWS),matches=sum(r['matched'] for r in ROWS),groups=dict(Counter(r['id'].split(':')[0] for r in ROWS)),failures=[r for r in ROWS if not r['matched']],cases=ROWS)
(OUT/'independent_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['cases','failures']},indent=2));print('failed IDs:',[r['id'] for r in summary['failures']])
if summary['failures']:sys.exit(1)
