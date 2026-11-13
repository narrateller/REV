"""Independent fixed raw oracle and R1 source-isolation expectations.
Malformed OPEN journal tags use fixed guard definitions, never tag equality
alone or legacy success as an oracle. Exit0 captures findings, not acceptance.
"""
from pathlib import Path
from collections import Counter
import ast,copy,hashlib,json,sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'verification/r5_ci_snapshots_recheck'));from fixtures import C,L,G,A,E,ENTRY,fixture,proof,prepare
sys.path.insert(0,str(ROOT/'verification/r4_cycle_interfaces/proposal'));import recovery_snapshots as R;import semantic_minimum as S
rows=[];exits=set();source=Path(R.__file__).read_text();fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='assess')
class Returns(ast.NodeVisitor):
 def __init__(self):self.lines=set()
 def visit_FunctionDef(self,n):pass
 def visit_Return(self,n):
  assert isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='finish';self.lines.add(n.lineno)
v=Returns()
for n in fn.body:v.visit(n)
assert len(v.lines)==8

def run(id,x,p,gate,scoped='UNKNOWN',g=None,raw=None,group='normal',detail=None,contract=C):
 before=copy.deepcopy((x,p,contract));text=json.dumps([x,p,contract],ensure_ascii=False);digest=L.digest([x,p,contract]);returns=[]
 def trace(f,event,arg):
  if event=='return' and f.f_code.co_filename==R.__file__ and f.f_code.co_name=='assess':returns.append(f.f_lineno)
  return trace
 old=sys.gettrace();sys.settrace(trace)
 try:a=S.recovery_assessment(p,x,contract)
 finally:sys.settrace(old)
 assert len(returns)==1;exits.add(returns[0])
 unchanged=(x,p,contract)==before and json.dumps([x,p,contract],ensure_ascii=False)==text and L.digest([x,p,contract])==digest;assert unchanged
 assertions=dict(gate=a['action_gate']==gate,scoped=(a['recovery_value']!='TRUE' if scoped=='NON_TRUE' else a['recovery_value']==scoped),readonly=unchanged,physical_permission_false=a['physical_permission'] is False)
 if g and raw is not None:assertions['independent_raw']=a['raw_evidence'][g]['value']==raw
 if type(p)is not dict or 'fault_id' not in p:assertions['no_target_substitution']='target_fault_id' not in a
 row=dict(id=id,group=group,expected_gate=gate,expected_scoped=scoped,assessment=a,return_line=returns[0],assertions=assertions,matched=all(assertions.values()),input_sha256_before=digest,input_sha256_after=L.digest([x,p,contract]),ordered_input_sha256=hashlib.sha256(text.encode()).hexdigest(),independent_evidence=detail)
 if not row['matched']:row.update(context=x,proof=p)
 rows.append(row);return a

def damage(x,kind,position):
 old=L.latch(C,x,'FEED_CLEAR','R5-independent-open-record',truth='UNKNOWN');f=x['faults'].pop(old)
 if kind=='missing-guard':f['origin'].pop('guard')
 elif kind=='null-origin':f['origin']=None
 elif kind=='array-origin':f['origin']=[]
 elif kind=='empty-origin':f['origin']={}
 elif kind=='missing-origin':f.pop('origin')
 else:
  tags={'null-guard':None,'bool-guard':False,'integer-guard':0,'array-guard':[],'object-guard':{},'unknown-guard':'R5_UNSUPPORTED_GUARD'}
  f['origin']['guard']=copy.deepcopy(tags[kind]);assert not(type(tags[kind])is str and tags[kind] in G)
 key='F-'+L.digest(f.get('origin'));f['fault_id']=key
 items=list(x['faults'].items());i={'first':0,'middle':len(items)//2,'last':len(items)}[position];items.insert(i,(key,f));x['faults']=dict(items)
 return key

def req(p,shape):
 q=copy.deepcopy(p)
 if shape=='null':return None
 if shape=='unknown-target':q['fault_id']='F-'+'0'*64
 elif shape=='dispatch':q.pop('guard')
 elif shape=='snapshot':q['origin_revisions']={}
 return q
# Original minimal input: no weakening of its old-source runner pin.
original=json.loads((ROOT/'verification/r5_ci_gate_exits_recheck/minimal_journal_witness.json').read_text());x=copy.deepcopy(original['context']);p=copy.deepcopy(original['proof']);assert L.digest([x,p])==original['input_sha256'];run('old-minimal-same-input',x,p,'BLOCKED',g='RESOURCES_READY',raw='FALSE',group='old-minimal',detail=dict(original_input_sha256=original['input_sha256']))

# Genuine reader errors, all proof paths, three journal positions and raw truths.
for g in ['RESOURCES_READY','METHOD_SUPPORTED']:
 for kind in ['missing-guard','null-origin','array-origin','empty-origin','missing-origin']:
  for position in ['first','middle','last']:
   for truth in ['TRUE','FALSE','UNKNOWN']:
    for shape in ['null','unknown-target','dispatch','snapshot','valid']:
     x,p=fixture(0);x['pending_observations']=[dict(event_id='R5-pending',value='UNKNOWN')];key=damage(x,kind,position);x['evidence'][g]['value']=truth
     oracle=L._raw_value(C,'RESTORE_B_CLOSURE',g,x,x['evidence'][g],'ENTRY');assert oracle[0]==truth
     run('reader-error:'+g+':'+kind+':'+position+':'+truth+':'+shape,x,req(p,shape),'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',g=g,raw=truth,group='reader-errors',detail=dict(raw_value=oracle[0],raw_reason=oracle[1],malformed_fault_id=key))
# Independent semantic mutation: missing guard and guard=null/unsupported tag
# carry the same inability to classify an OPEN record. A coherent hash cannot
# make an unknown guard part of the pinned definition set or establish absence
# of mandatory latches. Known unrelated supported FEED remains a positive control.
for g in ['RESOURCES_READY','METHOD_SUPPORTED']:
 for kind in ['null-guard','bool-guard','integer-guard','array-guard','object-guard','unknown-guard']:
  for position in ['first','middle','last']:
   for truth in ['TRUE','FALSE','UNKNOWN']:
    x,p=fixture(0);key=damage(x,kind,position);x['evidence'][g]['value']=truth;f=x['faults'][key]
    assert L.history_valid(x) and key=='F-'+L.digest(f['origin'])
    oracle=L._raw_value(C,'RESTORE_B_CLOSURE',g,x,x['evidence'][g],'ENTRY');assert oracle[0]==truth
    run('unknown-open-tag:'+g+':'+kind+':'+position+':'+truth,x,p,'BLOCKED' if truth=='FALSE' else 'INDETERMINATE','NON_TRUE' if truth=='FALSE' else 'UNKNOWN',g,truth,'semantic-journal-tags',dict(guard_is_fixed_supported=False,history_valid=True,canonical_fault_id=key,raw_value=oracle[0],raw_reason=oracle[1]))
# Invalid literal FALSE must not dominate; other independently valid FALSE must.
for g in ['RESOURCES_READY','METHOD_SUPPORTED']:
 for defect in ['stale','foreign-scope','wrong-action','wrong-guard','wrong-phase','missing-revision','float-revision','bool-current','missing-source','empty-method','missing-id','bad-interval','missing-value','null-record']:
  for other_false in [False,True]:
   x,p=fixture(0);damage(x,'missing-guard','middle');r=x['evidence'][g];r['value']='FALSE';domain=G[g]['evidence_domains'][0]
   if defect=='stale':r['revisions'][domain]+=1
   elif defect=='foreign-scope':r['subject_id']='FOREIGN'
   elif defect=='wrong-action':r['action']='OTHER_ACTION'
   elif defect=='wrong-guard':r['guard']='OTHER_GUARD'
   elif defect=='wrong-phase':r['phase']='COMMIT'
   elif defect=='missing-revision':r['revisions'].pop(domain)
   elif defect=='float-revision':r['revisions'][domain]=0.0
   elif defect=='bool-current':x['revisions'][domain]=False
   elif defect=='missing-source':r.pop('source')
   elif defect=='empty-method':r['method']=''
   elif defect=='missing-id':r.pop('evidence_id')
   elif defect=='bad-interval':r['valid_for_operation_interval']=0
   elif defect=='missing-value':r.pop('value')
   else:x['evidence'][g]=None;r=None
   oracle=L._raw_value(C,'RESTORE_B_CLOSURE',g,x,r,'ENTRY');assert oracle[0]=='UNKNOWN'
   other='METHOD_SUPPORTED' if g=='RESOURCES_READY' else 'RESOURCES_READY'
   if other_false:
    x['evidence'][other]['value']='FALSE';assert L._raw_value(C,'RESTORE_B_CLOSURE',other,x,x['evidence'][other],'ENTRY')[0]=='FALSE'
   run('invalid-raw:'+g+':'+defect+':other='+str(other_false),x,None,'BLOCKED' if other_false else 'INDETERMINATE',g=g,raw='UNKNOWN',group='invalid-controls',detail=dict(oracle_value=oracle[0],oracle_reason=oracle[1]))
# Independent own combinations: no source result is inferred from candidate gate.
for a in ['TRUE','FALSE','UNKNOWN']:
 for b in ['TRUE','FALSE','UNKNOWN']:
  for position in ['first','middle','last']:
   x,p=fixture(0);damage(x,'missing-guard',position);x['evidence']['RESOURCES_READY']['value']=a;x['evidence']['METHOD_SUPPORTED']['value']=b
   run('two-own:'+a+':'+b+':'+position,x,p,'BLOCKED' if 'FALSE' in [a,b] else 'INDETERMINATE',group='two-own')
# Exceptional source unavailability is injected in memory only; original fixed
# files stay unchanged. Raw absence never invents FALSE; independent sources win.
for failing in ['raw','journal','both']:
 for cls in [KeyError,TypeError,AttributeError,ValueError,StopIteration]:
  for known in ['none','other-raw','latched-same','state','causal']:
   x,p=fixture(0);g='RESOURCES_READY'
   if known=='other-raw':x['evidence']['METHOD_SUPPORTED']['value']='FALSE'
   elif known=='latched-same':L.latch(C,x,g,'R5-independent-latch',truth='FALSE')
   elif known=='state':x['state']=next(s for s in C['state_modes'] if s not in A['from_states'])
   elif known=='causal':
    parent=L.latch(C,x,'FEED_CLEAR','R5-independent-cause',truth='FALSE');target=L.latch(C,x,'B_RESET_CONFIRMED','R5-addressed-cause',causes=[parent]);p=proof(x,target)
   fixed,guards,action,helper=R.definitions(C);rawfun=helper._raw_value;journalfun=helper.evidence_value
   def rawfn(c,a,guard,context,record,phase):
    if guard==g and failing in ['raw','both']:raise cls('R5-independent-raw-unavailable')
    return rawfun(c,a,guard,context,record,phase)
   def journalfn(c,a,guard,context,record,phase):
    if guard==g and failing in ['journal','both']:raise cls('R5-independent-journal-unavailable')
    return journalfun(c,a,guard,context,record,phase)
   # A latched-same proof is available only if journal reader itself is available.
   has_false=known in ['other-raw','state','causal'] or known=='latched-same' and failing=='raw'
   # Suppress success with malformed proof while preserving an explicit causal ID.
   q=copy.deepcopy(p);q.pop('action')
   with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'_raw_value',side_effect=rawfn),patch.object(helper,'evidence_value',side_effect=journalfn):
    run('source-exception:'+failing+':'+cls.__name__+':'+known,x,q,'BLOCKED' if has_false else 'INDETERMINATE',group='injected-source-errors')
# Actual journal reader error plus valid state/explicit causal constraint.
for known in ['state','causal']:
 x,p=fixture(0)
 if known=='state':x['state']=next(s for s in C['state_modes'] if s not in A['from_states'])
 else:
  parent=L.latch(C,x,'FEED_CLEAR','R5-cause',truth='FALSE');target=L.latch(C,x,'B_RESET_CONFIRMED','R5-target',causes=[parent]);p=proof(x,target)
 damage(x,'missing-guard','first');q=copy.deepcopy(p);q.pop('action');run('journal-error-with-'+known,x,q,'BLOCKED',group='state-causal')
# All assessment exits, including unavailable source and policy exceptions.
for context in [None,[],0,'context']:
 run('unavailable-context:'+repr(context),context,None,'INDETERMINATE',group='exit-coverage')
x,p=fixture(0);bad=copy.deepcopy(C);bad['scope']='FOREIGN';run('unsupported-definitions',x,p,'INDETERMINATE',contract=bad,group='exit-coverage')
for known in [False,True]:
 x,p=fixture(0)
 if known:x['evidence']['RESOURCES_READY']['value']='FALSE'
 fixed,guards,action,helper=R.definitions(C)
 with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'recover',side_effect=ValueError('R5-policy-unavailable')):
  run('policy-unavailable:'+str(known),x,p,'BLOCKED' if known else 'INDETERMINATE',group='exit-coverage')
# Positive supported history and source baselines remain admissible.
for n in [0,1,2**63]:
 x,p=fixture(n);x['revisions']={d:n for d in E|ENTRY};p['revisions']={d:n for d in E}
 for g,r in x['evidence'].items():r['revisions']={d:n for d in G[g]['evidence_domains']}
 run('positive-minimal:'+str(n),x,p,'ALLOWED_ASSUMED','TRUE',group='positive')
x,p=fixture(0);target=p['fault_id'];L.latch(C,x,'FEED_CLEAR','R5-supported-foreign',truth='FALSE');run('supported-foreign-fault-positive-control',x,p,'ALLOWED_ASSUMED','TRUE',group='positive');out,status=L.recover(C,'RESTORE_B_CLOSURE',x,target,p);assert status=='ALLOWED_ASSUMED' and L.open_faults(out,'FEED_CLEAR');work=prepare(out,'B-COMPACT','R5-work');work['state']='B_BATCH_SELECTED';assert L.evaluate(C,'B-COMPACT',work,'ENTRY')['permission_outcome']=='BLOCKED'
for steps in [1,3]:
 x,p=fixture(0);target=p['fault_id']
 for _ in range(steps):x=L.change_subject(C,x,'B_CLOSURE')
 x=prepare(x,'RESTORE_B_CLOSURE','R5-after-advance');p=proof(x,target);run('confirmed-addressed-advance:'+str(steps),x,p,'ALLOWED_ASSUMED','TRUE',group='positive')
assert exits==v.lines
result=dict(C='b89854ad709bcb5c2991376bed41bf2f73acef82',session_id='r5-ci-raw-sources-20261113',count=len(rows),matches=sum(r['matched'] for r in rows),failed=[r for r in rows if not r['matched']],false_TRUE=[r['id'] for r in rows if r['assessment']['recovery_value']=='TRUE' and r['expected_scoped']!='TRUE'],cases=rows,groups=dict(Counter(r['group'] for r in rows)),all_eight_exits_exercised=True,return_lines=sorted(exits),oracle='Pinned frozen raw validation, fixed guard membership, and R1 two-source/composite criteria. Legacy successful scan is not an oracle for unsupported OPEN guard tags.')
(H/'independent_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['count','matches','false_TRUE','groups']},indent=2));print('failures',[(r['id'],[k for k,v in r['assertions'].items() if not v]) for r in result['failed']])
