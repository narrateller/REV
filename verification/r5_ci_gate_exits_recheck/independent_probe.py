"""Independent truth/domain oracle, return tracing and real damaged-journal cases.
Code locations measure exit coverage only; outcome obligations come from R1
and fixed frozen definitions. Exit0 captures all mismatches, not acceptance.
"""
from pathlib import Path
import ast,copy,hashlib,json,sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'verification/r5_ci_snapshots_recheck'))
from fixtures import C,L,G,A,E,U,ENTRY,fixture,proof,prepare,ev,rekey
sys.path.insert(0,str(ROOT/'verification/r4_cycle_interfaces/proposal'));import semantic_minimum as S;import recovery_snapshots as R
rows=[];exits=set()
module=Path(R.__file__);source=module.read_text();tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='assess')
class ExitVisitor(ast.NodeVisitor):
 def __init__(self):self.lines=set()
 def visit_FunctionDef(self,node):pass
 def visit_Return(self,node):
  assert isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='finish'
  self.lines.add(node.lineno)
v=ExitVisitor()
for n in fn.body:v.visit(n)
assert len(v.lines)==8

def run(id,x,p,gate,value='UNKNOWN',causal=None,contract=C,group='normal',detail=None):
 before=copy.deepcopy((x,p,contract));digest=L.digest([x,p,contract]);returned=[]
 def trace(frame,event,arg):
  if event=='return' and frame.f_code.co_filename==R.__file__ and frame.f_code.co_name=='assess':returned.append(frame.f_lineno)
  return trace
 previous=sys.gettrace();sys.settrace(trace)
 try:a=S.recovery_assessment(p,x,contract)
 finally:sys.settrace(previous)
 assert len(returned)==1;exits.update(returned)
 unchanged=(x,p,contract)==before and digest==L.digest([x,p,contract]);assert unchanged
 assertions=dict(gate=a['action_gate']==gate,scoped=a['recovery_value']==value,readonly=unchanged,physical_permission_false=a['physical_permission'] is False)
 if causal is not None:assertions['causal']=a['causal_value']==causal
 if p is None or type(p)is not dict or type(p.get('fault_id'))is not str:assertions['no_invented_target']='target_fault_id' not in a
 record=dict(id=id,group=group,expected_gate=gate,expected_scoped=value,assessment=a,assessment_return_line=returned[0],assertions=assertions,matched=all(assertions.values()),input_sha256_before=digest,input_sha256_after=L.digest([x,p,contract]),independent_evidence=detail)
 if not record['matched']:record.update(context=x,proof=p)
 rows.append(record);return a

def causal_context(status='OPEN'):
 x,p=fixture(0);parent=L.latch(C,x,'FEED_CLEAR','R5-independent-cause',truth='FALSE');target=L.latch(C,x,'B_RESET_CONFIRMED','R5-explicit-target',causes=[parent])
 if status=='MISSING':del x['faults'][parent]
 else:x['faults'][parent]['status']=status
 return x,proof(x,target),parent

# Immutable original minimal inputs: replay without weakening historical runner's
# old-source pin; source and input identities remain separately recorded.
original=json.loads((ROOT/'verification/r5_ci_snapshots_recheck/minimal_witnesses.json').read_text())
for r in original['witnesses']:
 assert L.digest([r['context'],r['proof']])==r['caller_and_proof_sha256_before']
 run('original-minimal:'+r['id'],copy.deepcopy(r['context']),copy.deepcopy(r['proof']),'BLOCKED',group='original-minimal',detail=dict(original_input_sha256=r['caller_and_proof_sha256_before']))

shapes=[('null',None),('array',[]),('text','proof'),('false',False),('true',True),('zero',0),('float',1.5),('empty',{})]
# Own entry records use independently current scope/revisions and fixed guards.
for resource in ['TRUE','FALSE','UNKNOWN']:
 for method in ['TRUE','FALSE','UNKNOWN']:
  for name,q in shapes:
   x,p=fixture(0);x['evidence']['RESOURCES_READY']['value']=resource;x['evidence']['METHOD_SUPPORTED']['value']=method
   gate='BLOCKED' if 'FALSE' in [resource,method] else 'INDETERMINATE'
   run('two-own:'+resource+':'+method+':'+name,x,copy.deepcopy(q),gate,group='own-truths')
for truth in ['FALSE','UNKNOWN']:
 for name,q in shapes:
  x,p=fixture(0);L.latch(C,x,'RESOURCES_READY','R5-truth-latch',truth=truth)
  run('latched:'+truth+':'+name,x,copy.deepcopy(q),'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',group='own-truths')
# Non-current FALSE is not a proven current prohibition.
for defect in ['stale','wrong-phase','wrong-scope','no-interval','no-provenance','bool-revision']:
 x,p=fixture(0);r=x['evidence']['RESOURCES_READY'];r['value']='FALSE'
 if defect=='stale':r['revisions'][G['RESOURCES_READY']['evidence_domains'][0]]+=1
 elif defect=='wrong-phase':r['phase']='RECOVERY_RESULT'
 elif defect=='wrong-scope':r['subject_id']='foreign'
 elif defect=='no-interval':r['valid_for_operation_interval']=False
 elif defect=='no-provenance':r.pop('source')
 else:r['revisions'][G['RESOURCES_READY']['evidence_domains'][0]]=False
 assert L._raw_value(C,'RESTORE_B_CLOSURE','RESOURCES_READY',x,r,'ENTRY')[0]=='UNKNOWN'
 run('unproven-record:'+defect,x,None,'INDETERMINATE',group='confidence')
for defect in ['known-wrong-state','unknown-state','null-state','null-mode','unknown-mode','known-wrong-mode','unconfirmed-state','unconfirmed-latch','unconfirmed-with-current-FALSE']:
 x,p=fixture(0);gate='INDETERMINATE'
 if defect=='known-wrong-state':x['state']=next(s for s in sorted(C['state_modes']) if s not in A['from_states']);gate='BLOCKED'
 elif defect=='unknown-state':x['state']='NOT_A_FIXED_STATE'
 elif defect=='null-state':x['state']=None
 elif defect=='null-mode':x['mode']=None
 elif defect=='unknown-mode':x['mode']='NOT_A_FIXED_MODE'
 elif defect=='known-wrong-mode':x['mode']=next(m for modes in C['state_modes'].values() for m in modes if m not in C['state_modes'][x['state']]);gate='BLOCKED'
 elif defect=='unconfirmed-state':x['state']=next(s for s in sorted(C['state_modes']) if s not in A['from_states']);x['history_confirmed']=False
 elif defect=='unconfirmed-latch':L.latch(C,x,'RESOURCES_READY','R5-unconfirmed',truth='FALSE');x['history_confirmed']=False
 else:x['history_confirmed']=False;x['evidence']['RESOURCES_READY']['value']='FALSE';gate='BLOCKED'
 run('confidence:'+defect,x,None,gate,group='confidence')
# Causal facts require explicit confirmed target and canonical parent identity.
for status in ['OPEN','RESOLVED','UNKNOWN','MISSING']:
 for defect in ['missing-action','wrong-action','missing-guard','wrong-guard','origin-empty','current-empty','expected-empty','valid','unknown-target','missing-target','foreign-guard-target','noncanonical-target']:
  x,p,parent=causal_context(status);target=p['fault_id'];has_target=True
  if defect=='missing-action':p.pop('action')
  elif defect=='wrong-action':p['action']='ALIEN_ACTION'
  elif defect=='missing-guard':p.pop('guard')
  elif defect=='wrong-guard':p['guard']='ALIEN_GUARD'
  elif defect=='origin-empty':p['origin_revisions']={}
  elif defect=='current-empty':p['revisions']={}
  elif defect=='expected-empty':x['faults'][target]['expected_revisions']={}
  elif defect=='unknown-target':p['fault_id']='F-'+'0'*64;has_target=False
  elif defect=='missing-target':p.pop('fault_id');has_target=False
  elif defect=='foreign-guard-target':p['fault_id']=parent;has_target=False
  elif defect=='noncanonical-target':x['faults'][target]['origin']['reason']='altered-without-rehash';has_target=False
  proven=has_target and status=='OPEN'
  gate='BLOCKED' if proven else 'ALLOWED_ASSUMED' if defect=='valid' and status=='RESOLVED' else 'INDETERMINATE'
  value='FALSE' if proven and defect=='valid' else 'TRUE' if gate=='ALLOWED_ASSUMED' else 'UNKNOWN'
  expected_causal=('FALSE' if status=='OPEN' else 'TRUE' if status=='RESOLVED' else 'UNKNOWN') if has_target else 'UNKNOWN'
  a=run('causal:'+status+':'+defect,x,p,gate,value,expected_causal,group='causal')
  if not has_target:assert 'target_fault_id' not in a
# Address absent: unrelated OPEN targets and parents must not be substituted.
for name,q in shapes:
 x,p,parent=causal_context('OPEN');run('no-target-scan:'+name,x,copy.deepcopy(q),'INDETERMINATE',causal='UNKNOWN',group='target')
# Snapshot/schema exits with independent resource FALSE and no FALSE, plus key permutations.
for denial in [False,True]:
 for defect in ['origin-missing','current-empty','expected-null','context-partial','entry-partial','attempts-missing','history-gap']:
  for reverse in [False,True]:
   x,p=fixture(0)
   if denial:x['evidence']['METHOD_SUPPORTED']['value']='FALSE'
   if defect=='origin-missing':p.pop('origin_revisions')
   elif defect=='current-empty':p['revisions']={}
   elif defect=='expected-null':x['faults'][p['fault_id']]['expected_revisions']=None
   elif defect=='context-partial':x['revisions'].pop('AXIS')
   elif defect=='entry-partial':x['evidence']['RESET_SWEEP_CLEAR']['revisions'].pop('AXIS')
   elif defect=='attempts-missing':x['faults'][p['fault_id']].pop('resolution_attempts')
   else:x['faults'][p['fault_id']]['revision_history']=[dict(domain='B_CLOSURE',from_revision=0,to_revision=2)]
   if reverse:x=dict(reversed(list(x.items())));p=dict(reversed(list(p.items())))
   run('schema:'+str(denial)+':'+defect+':'+str(reverse),x,p,'BLOCKED' if denial else 'INDETERMINATE',group='schema')
# Actual malformed unrelated journal record: raw current evidence remains usable
# independently of a failing guard-wide fault scan. Guard omission has coherent
# F-digest and history_valid=True; it is not an invented raw FALSE.
for false_guard in ['RESOURCES_READY','METHOD_SUPPORTED']:
 for shape in ['none','unknown-target','unsupported-dispatch','snapshot-error']:
  for truth in ['FALSE','TRUE','UNKNOWN']:
   x,p=fixture(0);old=L.latch(C,x,'FEED_CLEAR','R5-malformed-unrelated-journal',truth='UNKNOWN');f=x['faults'].pop(old);f['origin'].pop('guard');new='F-'+L.digest(f['origin']);f['fault_id']=new;x['faults'][new]=f
   r=x['evidence'][false_guard];r['value']=truth;assert L.history_valid(x)
   independent=L._raw_value(C,'RESTORE_B_CLOSURE',false_guard,x,r,'ENTRY');assert independent[0]==truth
   if shape=='none':p=None
   elif shape=='unknown-target':p['fault_id']='F-'+'0'*64
   elif shape=='unsupported-dispatch':p.pop('guard')
   else:p['origin_revisions']={}
   run('damaged-other-journal:'+false_guard+':'+shape+':'+truth,x,p,'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',group='real-journal-exception',detail=dict(frozen_raw_value=independent[0],frozen_raw_reason=independent[1],history_valid=True,malformed_fault_id=new,guard=false_guard))
# Definitions/context exits have no supported independent source to establish FALSE.
for c in [None,[],0,False,'context']:
 run('context-unavailable:'+repr(c),c,None,'INDETERMINATE',group='unavailable')
x,p=fixture(0);bad=copy.deepcopy(C);bad['scope']='FOREIGN';run('definitions-mismatch',x,p,'INDETERMINATE',contract=bad,group='unavailable')
# Fault injection measures exceptional exits only. Fixed files never change and
# no compatibility claim is made for artificially unavailable policy code.
for denial in ['none','resource','causal']:
 x,p,parent=causal_context('OPEN') if denial=='causal' else (*fixture(0),None)
 if denial=='resource':x['evidence']['RESOURCES_READY']['value']='FALSE'
 fixed,guards,action,helper=R.definitions(C)
 with patch.object(R,'definitions',return_value=(fixed,guards,action,helper)),patch.object(helper,'recover',side_effect=ValueError('R5-independent-policy-unavailable')):
  run('policy-exception:'+denial,x,p,'INDETERMINATE' if denial=='none' else 'BLOCKED',group='injected-policy-exception')
# Normal policy return with scoped UNKNOWN and independent FALSE, and success.
for known in ['none','resource','causal']:
 x,p,parent=causal_context('OPEN') if known=='causal' else (*fixture(0),None)
 if known=='resource':x['evidence']['RESOURCES_READY']['value']='FALSE'
 p['origin_revisions']['B_CLOSURE']+=1
 run('normal-policy-unknown:'+known,x,p,'INDETERMINATE' if known=='none' else 'BLOCKED',group='normal-policy')
for n in [0,1,2**63]:
 x,p=fixture(n);x['revisions']={d:n for d in E|ENTRY};p['revisions']={d:n for d in E}
 for g,r in x['evidence'].items():r['revisions']={d:n for d in G[g]['evidence_domains']}
 run('positive-minimal:'+str(n),x,p,'ALLOWED_ASSUMED','TRUE','TRUE',group='positive')
for advance in [1,3]:
 x,p=fixture(0);fid=p['fault_id']
 for _ in range(advance):x=L.change_subject(C,x,'B_CLOSURE')
 x=prepare(x,'RESTORE_B_CLOSURE','R5-confirmed-advance');p=proof(x,fid)
 run('positive-addressed-advance:'+str(advance),x,p,'ALLOWED_ASSUMED','TRUE','TRUE',group='positive')
x,p=fixture(0);fid=p['fault_id'];L.latch(C,x,'FEED_CLEAR','R5-unrelated-feed',truth='FALSE');run('positive-foreign-fault-retained',x,p,'ALLOWED_ASSUMED','TRUE','TRUE',group='positive')
out,status=L.recover(C,'RESTORE_B_CLOSURE',x,fid,p);assert status=='ALLOWED_ASSUMED' and L.open_faults(out,'FEED_CLEAR');work=prepare(out,'B-COMPACT','R5-next-work');work['state']='B_BATCH_SELECTED';assert L.evaluate(C,'B-COMPACT',work,'ENTRY')['permission_outcome']=='BLOCKED'
coverage=[dict(line=line,source=source.splitlines()[line-1].strip(),cases=sum(r['assessment_return_line']==line for r in rows),blocked=sum(r['assessment_return_line']==line and r['assessment']['action_gate']=='BLOCKED' for r in rows),indeterminate=sum(r['assessment_return_line']==line and r['assessment']['action_gate']=='INDETERMINATE' for r in rows),allowed=sum(r['assessment_return_line']==line and r['assessment']['action_gate']=='ALLOWED_ASSUMED' for r in rows)) for line in sorted(v.lines)]
assert exits==v.lines
result=dict(C='3060dbf561f95e4384fbfd13a9cc5569690515e5',session_id='r5-ci-gate-exits-20261113',count=len(rows),matches=sum(r['matched'] for r in rows),failed=[r for r in rows if not r['matched']],cases=rows,exit_coverage=coverage,source_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),all_eight_exits_exercised=exits==v.lines,all_exits_compose_finish=True,oracle='R1 truth table, own explicit fixture truths and fixed frozen definitions; raw evidence checked independently of fault scan; source lines used only for coverage')
(H/'minimal_pair_replay.json').write_text(json.dumps(dict(C=result['C'],session_id=result['session_id'],cases=[r for r in rows if r['group']=='original-minimal'],matches=sum(r['matched'] for r in rows if r['group']=='original-minimal'),original_input_digests_verified=True),indent=2)+'\n')
(H/'independent_results.json').write_text(json.dumps(result,indent=2)+'\n');(H/'exit_coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
print(json.dumps(dict(count=result['count'],matches=result['matches'],failed=[r['id'] for r in result['failed']],all_eight_exits_exercised=True),indent=2))
