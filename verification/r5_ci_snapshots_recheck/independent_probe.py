"""Fixed-definition domain oracle, scoped policy and composite-denial witnesses.
Expectations are independent of candidate maps/admission output. Exit 0 captures
all findings (including failures); no state returned by helper is applied.
"""
from pathlib import Path
import copy,hashlib,json,sys
from fixtures import ROOT,C,L,G,A,E,U,ENTRY,fixture,proof,rekey,prepare,ev
P=ROOT/'verification/r4_cycle_interfaces/proposal';H=Path(__file__).resolve().parent
sys.path.insert(0,str(P));import semantic_minimum as S
rows=[]
BAD=[('null',None),('bool-true',True),('bool-false',False),('float-zero',0.0),('float-one',1.0),('text','0'),('array',[]),('object',{}),('negative',-1)]
def put(v,path,value,missing=False):
 for k in path[:-1]:v=v[k]
 if missing:v.pop(path[-1],None)
 else:v[path[-1]]=copy.deepcopy(value)
def run(id,x,p,value,domain,gate,group):
 before=copy.deepcopy((x,p));digest=L.digest([x,p]);a=S.recovery_assessment(p,x,C)
 actual_value=S.recovery_value(p,x,C);assert actual_value==a['recovery_value']
 unchanged=(x,p)==before and digest==L.digest([x,p]);assert unchanged
 frozen=None;out=None;legacy_error=None
 try:out,frozen=L.recover(C,'RESTORE_B_CLOSURE',x,p.get('fault_id') if type(p)is dict else 'F-'+'0'*64,p)
 except (ValueError,KeyError,TypeError,AttributeError) as exc:legacy_error=type(exc).__name__
 fid=p.get('fault_id') if type(p)is dict else None
 retained=out is None or set(x['rejected_operation_ids'])<=set(out['rejected_operation_ids']);assert retained
 assertions={'scoped':a['recovery_value']==value,'domain':a['compatibility_domain']==domain,'gate':a['action_gate']==gate,'readonly':unchanged,'rejected_IDs':retained,'physical_permission_false':a['physical_permission'] is False}
 # Compare equal result levels only within fixed schema domain. Malformed inputs
 # are never silently treated as compatible because legacy happened to allow.
 compatibility=None
 if domain=='IN_DOMAIN':
  compatibility=(frozen==a['action_gate'] and legacy_error is None)
  assertions['in_domain_composite_matches_frozen']=compatibility
  if a['validation']['status']=='VALID':assertions['in_domain_scoped_matches_frozen']=a['recovery_value']=={'ALLOWED_ASSUMED':'TRUE','BLOCKED':'FALSE','INDETERMINATE':'UNKNOWN'}[frozen]
 else:
  assertions['outside_has_explicit_reason']=bool(a['validation']['reasons'])
  assertions['outside_no_TRUE']=a['recovery_value']!='TRUE'
  assertions['outside_not_delegated']=a['policy_result']=='NOT_EVALUATED'
 matched=all(assertions.values())
 record=dict(id=id,group=group,expected=dict(value=value,domain=domain,gate=gate),assessment=a,frozen_policy=frozen,legacy_error=legacy_error,compatibility=compatibility,caller_and_proof_sha256_before=digest,caller_and_proof_sha256_after=L.digest([x,p]),rejected_IDs_retained=retained,caller_fault_status=x['faults'].get(fid,{}).get('status'),returned_fault_status=out['faults'].get(fid,{}).get('status') if out else None,assertions=assertions,matched=matched)
 if not matched:record.update(context=x,proof=p)
 rows.append(record)
# Required sets from immutable definitions. The target E has one domain; its
# partial map is empty. ENTRY/current multi-domain partials retain other keys.
for n in [0,1,2**63]:
 x,p=fixture(n);run('integer:'+str(n),x,p,'TRUE','IN_DOMAIN','ALLOWED_ASSUMED','positive')
locations=['origin','expected','proof-origin','proof-current','current']
for location in locations:
 for shape in ['empty','missing','foreign-only','extra-known','extra-foreign','wrong-positive','stale','null','container']:
  x,p=fixture(0);fid=p['fault_id'];obj=x['faults'][fid]
  if location=='origin':base=obj['origin']['revisions']
  elif location=='expected':base=obj['expected_revisions']
  elif location=='proof-origin':base=p['origin_revisions']
  elif location=='proof-current':base=p['revisions']
  else:base=x['revisions']
  v=copy.deepcopy(base)
  if shape=='empty':v={}
  elif shape=='foreign-only':v={next(iter(U-E)):0}
  elif shape=='extra-known':
   if location=='current':v={d:base[d] for d in E|ENTRY};v[next(iter(sorted(U-(E|ENTRY))))]=7
   elif location=='proof-current':v={d:base[d] for d in E};v[next(iter(sorted(U-E)))]=7
   else:v[next(iter(sorted(U-E)))]=7
  elif shape=='extra-foreign':v['ALIEN']=0
  elif shape in ['wrong-positive','stale']:v[next(iter(E))]=2 if shape=='wrong-positive' else 1
  elif shape=='null':v=None
  elif shape=='container':v=[]
  if location=='origin':
   if shape in ['null','container']:
    # history_valid must reject malformed origin map; re-hash remains coherent.
    obj['origin']['revisions']=v;old=fid;new='F-'+L.digest(obj['origin']);obj['fault_id']=new;x['faults'].pop(old);x['faults'][new]=obj;p['fault_id']=new
   elif shape=='missing':
    obj['origin'].pop('revisions');old=fid;new='F-'+L.digest(obj['origin']);obj['fault_id']=new;x['faults'].pop(old);x['faults'][new]=obj;p['fault_id']=new
   else:obj['origin']['revisions']=v;p['origin_revisions']=copy.deepcopy(v);rekey(x,p)
  elif location=='expected':put(obj,['expected_revisions'],v,shape=='missing')
  elif location=='proof-origin':put(p,['origin_revisions'],v,shape=='missing')
  elif location=='proof-current':put(p,['revisions'],v,shape=='missing')
  else:put(x,['revisions'],v,shape=='missing')
  positive=shape=='extra-known' and location in ['proof-current','current']
  binding_wrong=shape in ['wrong-positive','stale'] and location in ['proof-origin','proof-current','current']
  run(location+':'+shape,x,p,'TRUE' if positive else 'UNKNOWN','IN_DOMAIN' if positive or binding_wrong else 'OUT_OF_DOMAIN','ALLOWED_ASSUMED' if positive else 'INDETERMINATE','maps')
 # Invalid values at every required domain of that map, preserving its structure.
 domains=E|ENTRY if location=='current' else E
 for d in sorted(domains):
  for label,val in BAD:
   x,p=fixture(0);fid=p['fault_id'];f=x['faults'][fid]
   if location=='origin':f['origin']['revisions'][d]=copy.deepcopy(val);p['origin_revisions'][d]=copy.deepcopy(val);rekey(x,p)
   elif location=='expected':f['expected_revisions'][d]=copy.deepcopy(val)
   elif location=='proof-origin':p['origin_revisions'][d]=copy.deepcopy(val)
   elif location=='proof-current':p['revisions'][d]=copy.deepcopy(val)
   else:x['revisions'][d]=copy.deepcopy(val)
   run(location+':'+d+':'+label,x,p,'UNKNOWN','OUT_OF_DOMAIN','INDETERMINATE','types')
# Context consumption is per guard, not a demand for global completeness.
for d in sorted(U-(E|ENTRY)):
 for shape in ['missing','changed']:
  x,p=fixture(0)
  if shape=='missing':x['revisions'].pop(d)
  else:x['revisions'][d]=2**63
  run('unused:'+d+':'+shape,x,p,'TRUE','IN_DOMAIN','ALLOWED_ASSUMED','unused')
for d in sorted(E|ENTRY):
 x,p=fixture(0);x['revisions'].pop(d);run('partial-current:'+d,x,p,'UNKNOWN','OUT_OF_DOMAIN','INDETERMINATE','partial')
for g in A['entry_guards']:
 domains=set(G[g]['evidence_domains'])
 for d in sorted(domains):
  for defect in ['missing','wrong-int','bool','foreign']:
   x,p=fixture(0);r=x['evidence'][g]['revisions']
   if defect=='missing':r.pop(d)
   elif defect=='wrong-int':r[d]=1
   elif defect=='bool':r[d]=False
   else:r['ALIEN']=0
   run('entry:'+g+':'+d+':'+defect,x,p,'UNKNOWN','IN_DOMAIN' if defect=='wrong-int' else 'OUT_OF_DOMAIN','INDETERMINATE','entry-maps')
# Minimal maps remain valid; arbitrary allowed extra annotations do not prove any
# other guard. Compare helper at the same admitted scope.
x,p=fixture(0);x['revisions']={d:0 for d in E|ENTRY};p['revisions']={d:0 for d in E}
for g,r in x['evidence'].items():r['revisions']={d:0 for d in G[g]['evidence_domains']}
run('minimal-all-consumed',x,p,'TRUE','IN_DOMAIN','ALLOWED_ASSUMED','positive')
for advance in [1,2,5]:
 x,p=fixture(0);fid=p['fault_id']
 for _ in range(advance):x=L.change_subject(C,x,*sorted(E))
 x=prepare(x,'RESTORE_B_CLOSURE','fresh-after-advance');p=proof(x,fid);assert p['origin_revisions']!=p['revisions']
 run('history-confirmed:'+str(advance),x,p,'TRUE','IN_DOMAIN','ALLOWED_ASSUMED','history')
for bad in ['missing','empty','gap','reversed','foreign-domain','bool-from','float-to','extra-field','null','container']:
 x,p=fixture(0);fid=p['fault_id'];x=L.change_subject(C,x,*sorted(E));x=prepare(x,'RESTORE_B_CLOSURE','history-negative');p=proof(x,fid);f=x['faults'][fid]
 if bad=='missing':f.pop('revision_history')
 elif bad=='empty':f['revision_history']=[]
 elif bad=='gap':f['revision_history'][0]['to_revision']=2
 elif bad=='reversed':f['revision_history'][0].update(from_revision=1,to_revision=0)
 elif bad=='foreign-domain':f['revision_history'][0]['domain']='FEED'
 elif bad=='bool-from':f['revision_history'][0]['from_revision']=False
 elif bad=='float-to':f['revision_history'][0]['to_revision']=1.0
 elif bad=='extra-field':f['revision_history'][0]['unconfirmed']=True
 elif bad=='null':f['revision_history']=None
 else:f['revision_history']={}
 run('history-invalid:'+bad,x,p,'UNKNOWN','OUT_OF_DOMAIN','INDETERMINATE','history')
# Independent denials: own resource/state and known addressed causal ancestor.
def denied(kind):
 x,p=fixture(0)
 if kind=='resource-record':x['evidence']['RESOURCES_READY']['value']='FALSE'
 elif kind=='resource-fault':
  r=ev(x,'RESTORE_B_CLOSURE','RESOURCES_READY');r['value']='FALSE';L.latch(C,x,'RESOURCES_READY','R5-resource-fault',r)
 elif kind=='state':x['state']=next(s for s in sorted(C['state_modes']) if s not in A['from_states'])
 elif kind=='causal':
  r=ev(x,'RESTORE_B_CLOSURE','FEED_CLEAR');r['value']='FALSE';cause=L.latch(C,x,'FEED_CLEAR','R5-causal',r);fid=L.latch(C,x,'B_RESET_CONFIRMED','R5-causal-target',causes=[cause]);p=proof(x,fid)
 return x,p
for kind in ['resource-record','resource-fault','state','causal']:
 for defect in ['valid','origin-empty','origin-missing','current-empty','expected-empty','action-missing','guard-missing','action-foreign','guard-foreign']:
  x,p=denied(kind)
  if defect=='origin-empty':p['origin_revisions']={}
  elif defect=='origin-missing':p.pop('origin_revisions')
  elif defect=='current-empty':p['revisions']={}
  elif defect=='expected-empty':x['faults'][p['fault_id']]['expected_revisions']={}
  elif defect=='action-missing':p.pop('action')
  elif defect=='guard-missing':p.pop('guard')
  elif defect=='action-foreign':p['action']='FOREIGN_ACTION'
  elif defect=='guard-foreign':p['guard']='FOREIGN_GUARD'
  run('compound:'+kind+':'+defect,x,p,'FALSE' if defect=='valid' else 'UNKNOWN','IN_DOMAIN' if defect=='valid' else 'OUT_OF_DOMAIN','BLOCKED','compound')
 # Whole-proof absence/container is independent of own ENTRY/state denial.
 if kind!='causal':
  for label,q in [('null',None),('array',[]),('text','proof'),('bool',False),('number',0)]:
   x,p=denied(kind);assert L.evaluate(C,'RESTORE_B_CLOSURE',x,'ENTRY')['permission_outcome']=='BLOCKED'
   run('compound:'+kind+':whole-proof-'+label,x,q,'UNKNOWN','OUT_OF_DOMAIN','BLOCKED','whole-proof')
# Valid and malformed proof with two independent own conditions; preserving one
# cannot be suppressed by malformed data supplied for another condition.
x,p=denied('resource-fault');x['evidence']['RESET_SWEEP_CLEAR']['revisions']={};p['origin_revisions']={}
run('compound:two-malformed-plus-latched-resource',x,p,'UNKNOWN','OUT_OF_DOMAIN','BLOCKED','compound')
# Wrong scope, stale proof and record value retain frozen rejection in-domain.
for field,value in [('subject_id','foreign-subject'),('cycle_epoch','foreign-epoch'),('target_scope',{}),('phase','ENTRY'),('value','FALSE'),('value','UNKNOWN')]:
 x,p=fixture(0);p[field]=value;run('in-domain-proof:'+field+':'+str(value),x,p,'FALSE' if value=='FALSE' else 'UNKNOWN','IN_DOMAIN','BLOCKED' if value=='FALSE' else 'INDETERMINATE','scope')
# A foreign FEED fault remains open while closure can recover; ordinary work is
# still blocked by that fault. Proposed helper copy used only as next synthetic input.
x,p=fixture(0);target=p['fault_id'];y=prepare(x,'B-LOAD','denied-feed');y['state']='B_ACCEPTABLE_INITIAL';y['evidence']['FEED_CLEAR']['value']='FALSE';x,_=L.decide(C,'B-LOAD',y);x['state']='B_RECEIVED_RESIDUAL';x=prepare(x,'RESTORE_B_CLOSURE','fresh-addressed-closure');p=proof(x,target)
run('sequential:closure-preserves-foreign-feed',x,p,'TRUE','IN_DOMAIN','ALLOWED_ASSUMED','sequence');out,status=L.recover(C,'RESTORE_B_CLOSURE',x,target,p);assert L.open_faults(out,'FEED_CLEAR');ordinary=prepare(out,'B-COMPACT','fresh-ordinary');ordinary['state']='B_BATCH_SELECTED';assert L.evaluate(C,'B-COMPACT',ordinary,'ENTRY')['permission_outcome']=='BLOCKED'
result=dict(C='e30b4b7caf3040905cc23c79ca696af2871c958a',session_id='r5-ci-snapshots-20261113',oracle=dict(frozen='0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed',target_domains=sorted(E),entry_domains=sorted(ENTRY),known_domains=sorted(U),source='Fixed contract guard/action definitions, never keys of candidate maps'),cases=rows,count=len(rows),matches=sum(r['matched'] for r in rows),failed=[r for r in rows if not r['matched']],scope='DOCUMENTARY_SYNTHETIC_ONLY',W02='NO_GO',physical_READY='NO_GO',G1='OPEN')
(H/'independent_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(count=result['count'],matches=result['matches'],failed=[(r['id'],[k for k,v in r['assertions'].items() if not v]) for r in result['failed']]),indent=2))
