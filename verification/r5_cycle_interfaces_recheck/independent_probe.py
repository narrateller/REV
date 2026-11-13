"""Independent documentary RECHECK, no physical controller or CAD acceptance.
Exit 0 captures findings; inspect expected/actual, especially negative mutations.
"""
from pathlib import Path
import copy,hashlib,importlib.util,itertools,json,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0,str(P));import document_semantics as S
D=json.loads((P/'permissions.json').read_text());A={a['id']:a for a in D['actions']};protocol=json.loads((P/'cycle_protocol.json').read_text())
C=json.loads((ROOT/'verification/r4_cycle_contract/contract.json').read_text())
s=importlib.util.spec_from_file_location('frozen',ROOT/'verification/r4_cycle_contract/permission_examples.py');L=importlib.util.module_from_spec(s);s.loader.exec_module(L)
checks=[];replay=[];traces=[];mutants=[]
def check(id,expected,actual,**detail):checks.append(dict(id=id,expected=expected,actual=actual,matches=expected==actual,**copy.deepcopy(detail)))
def receipt_fixture(load,mode):
 x={k:'R5-'+k for k in S.FILL_SCOPE};x.update(variant=load[0],mode=mode,load_action=load,revisions={k:0 for k in S.FILL_REVISIONS},inventory_refs=['retained-entity'],pending_observations=[dict(event_id='unknown-mass',mass_record=None)])
 r={k:x[k] for k in S.FILL_SCOPE};r.update(revisions=copy.deepcopy(x['revisions']),value='TRUE',invalidated=False,confirmation_kind='OBSERVED_TRANSFER_COMPLETE',transfer_pose='D1',dose_delivered='TRUE',evidence_id='R5-addressed-fill',source='independent hypothetical transfer',method='ASSUMED_FIXTURE',valid_for_consumer_interval=True)
 return x,r
def values(a,parent=None):
 gs=set(a['entry_guards']+a['extra_entry_guards']);gs.update(a.get('current_parent_guards',{}).get(parent,[]));gs.update(S.FEEDER_GUARDS if 'FEEDER_SAFE' in gs else [])
 return {g:'TRUE' for g in gs}
def committed(x,r):
 y=copy.deepcopy(x);origin=copy.deepcopy(y['revisions'])
 for k in ['material','feed']:y['revisions'][k]+=1
 y['load_commit']=dict({k:y[k] for k in S.FILL_SCOPE},origin_revisions=origin,revisions=copy.deepcopy(y['revisions']),value='TRUE',boundary='AFTER_DOSER_RETURN',receipt_id=r['evidence_id'],current_doser='D0',changed_domains=['material','feed'])
 return y
# Map every one of the previous 17 findings to the corrected criterion, not its old failing assertion.
old=json.loads((ROOT/'verification/r5_cycle_interfaces_output/independent_results.json').read_text())
for item in old['failed']:
 id=item['id'];ok=False;detail={}
 if id.startswith('mode-parent:'):
  name,mode=id[len('mode-parent:'):].rsplit(':',1);ok=mode not in A[name]['mode'] or any(mode in A[p]['mode'] for p in A[name]['parent_action_choices'])
 elif id.startswith('load-return-current-completion:'):
  name=id.split(':',1)[1];gs=set(A[name]['extra_completion_guards']);ok={'D_HOME_CURRENT','FILL_COMPLETE'}<=gs and 'D_DELIVERY_CURRENT' not in gs and A[name]['commit_boundary']=='AFTER_DOSER_RETURN'
 elif id.startswith('restore-parent-vs-child:'):
  name=id.split(':',1)[1];gs=set(A[name]['entry_guards']+A[name]['extra_entry_guards']);v=values(A[name],'B-RESET');v['DEPENDENCY_VALID']='FALSE';ok='DEPENDENCY_VALID' not in gs and S.entry_outcome(A[name],v,'B-RESET')=='ALLOWED_ASSUMED'
 elif id.startswith('addressed-fill-complete-before-isolation:'):
  v=id.rsplit(':',1)[1];a=A[v+'-MECH-FEED-ISOLATE'];ok={'FILL_COMPLETE','LOAD_COMMITTED_CURRENT','FEEDER_SAFE'}<=set(a['extra_entry_guards']) and a['fill_binding']['role']=='CONSUME_COMMITTED'
 elif id.startswith('semantic-mutation:'):continue # recorded after actual isolated replay below
 replay.append(dict(original_id=id,corrected=ok));check('replay17:'+id,True,ok)
# All five parent actions / six modes; own sequential/composite fixtures.
for load in S.LOADS:
 for mode in A[load]['mode']:
  x,r=receipt_fixture(load,mode);tag=load+':'+mode;before=copy.deepcopy((x,r))
  check('fill-current:'+tag,'TRUE',S.fill_value(r,x))
  comp=set(A[load]['completion_guards']+A[load]['extra_completion_guards'])
  early={g:'TRUE' for g in comp};early['D_HOME_CURRENT']='FALSE';early['FILL_COMPLETE']=S.fill_value(r,x)
  check('cannot-commit-in-D1:'+tag,'BLOCKED',S.conjunction(early[g] for g in comp))
  ret=A[load[0]+'-MECH-DOSER-RETURN'];v=values(ret,load);v['FILL_COMPLETE']=S.fill_value(None,x)
  check('return-before-confirmation:'+tag,'INDETERMINATE',S.entry_outcome(ret,v,load))
  v['FILL_COMPLETE']=S.fill_value(r,x);check('confirmed-return:'+tag,'ALLOWED_ASSUMED',S.entry_outcome(ret,v,load))
  early['D_HOME_CURRENT']='TRUE';check('commit-after-return:'+tag,'ALLOWED_ASSUMED',S.conjunction(early[g] for g in comp))
  check('isolation-before-commit:'+tag,'UNKNOWN',S.fill_value(r,x,True))
  y=committed(x,r);check('committed-successor:'+tag,'TRUE',S.fill_value(r,y,True))
  check('receipt-not-rewritten:'+tag,before[1],r);check('inventory-preserved:'+tag,x['inventory_refs'],y['inventory_refs'])
  for field in S.FILL_SCOPE:
   for value in [None,'foreign-'+field]:
    wrong=copy.deepcopy(x);wrong[field]=value;check('wrong-address:'+tag+':'+field+':'+str(value),'UNKNOWN',S.fill_value(r,wrong))
  for field in S.FILL_REVISIONS:
   wrong=copy.deepcopy(y);wrong['revisions'][field]+=1;check('postcommit-stale:'+tag+':'+field,'UNKNOWN',S.fill_value(r,wrong,True))
  for field in ['method','source','evidence_id','revisions','dose_id']:
   bad=copy.deepcopy(r);bad.pop(field);check('incomplete-receipt:'+tag+':'+field,'UNKNOWN',S.fill_value(bad,x))
  for field,badvalue in [('confirmation_kind','COMMAND_FINISHED'),('confirmation_kind','TIMER_EXPIRED'),('dose_delivered','UNKNOWN'),('transfer_pose','D0'),('valid_for_consumer_interval',False)]:
   bad=copy.deepcopy(r);bad[field]=badvalue;check('not-observation:'+tag+':'+field+':'+str(badvalue),'UNKNOWN',S.fill_value(bad,x))
  for key in ['dose_id','load_operation_id','transfer_operation_id']:
   nxt=copy.deepcopy(y);nxt[key]='new-refill-'+key;check('old-receipt-new-refill:'+tag+':'+key,'UNKNOWN',S.fill_value(r,nxt,True))
  for field,val in [('boundary','BEFORE_RETURN'),('current_doser','D1'),('receipt_id','different'),('value','UNKNOWN')]:
   bad=copy.deepcopy(y);bad['load_commit'][field]=val;check('bad-commit:'+tag+':'+field,'UNKNOWN',S.fill_value(r,bad,True))
  for f,safe,resource in itertools.product(['TRUE','FALSE','UNKNOWN'],repeat=3):
   v=values(ret,load);v.update(FILL_COMPLETE=f,D_PATH_CLEAR=safe,RESOURCES_READY=resource)
   expected='BLOCKED' if 'FALSE' in [f,safe,resource] else 'INDETERMINATE' if 'UNKNOWN' in [f,safe,resource] else 'ALLOWED_ASSUMED'
   check('return-composite:'+tag+':'+''.join(a[0] for a in [f,safe,resource]),expected,S.entry_outcome(ret,v,load))
  invalid=copy.deepcopy(r);invalid['invalidated']=True;check('revoked-after-D0:'+tag,'FALSE',S.fill_value(invalid,x))
  traces.append(dict(load=load,mode=mode,stage_order=next(t['stages'] for t in protocol['load_sequences'] if t['parent']==load),receipt=r,committed_context=y))
# Frozen history integration: no generic history prerequisite for restoration; normal actions stay blocked.
def ev(x,action,g,phase=None):
 t=L.spec(C,action);return dict({k:x[k] for k in C['evidence_policy']['scope_fields']+['operation_id']},action=action,guard=g,phase=phase or ('COMPLETION' if g in t['completion_guards'] else 'ENTRY'),value='TRUE',revisions=copy.deepcopy(x['revisions']),evidence_id='R5-'+x['operation_id']+'-'+g,method='ASSUMED_FIXTURE',source='independent hypothetical witness',valid_for_operation_interval=True)
def prepare(x,a,op):
 y=copy.deepcopy(x);y['operation_id']=op;y['evidence']={g:ev(y,a,g) for g in L.spec(C,a)['required_guards']};return y
def failed():
 x=dict(scenario_id='R5-B',variant='B',mode='B_REPEAT',state='B_RECEIVED_RESIDUAL',subject_id='closure',batch_id='batch',cycle_epoch='epoch',basis_id='basis',basis_revision='r1',operation_id='denied',revisions={k:0 for k in C['evidence_policy']['domains']},inventory_refs=['retained'],pending_observations=[])
 x=L.initialize_history(x,'R5-audited-history',dict(value='TRUE',evidence_id='R5-initial',source='hypothetical audit'));x=prepare(x,'B-NEXT','denied');x['evidence']['B_RESET_CONFIRMED']['value']='FALSE';x,r=L.decide(C,'B-NEXT',x);assert r['permission_outcome']=='BLOCKED';return x
def recover(x,a,fid,op):
 y=prepare(x,a,op);f=y['faults'][fid];p=ev(y,a,f['origin']['guard'],'RECOVERY_RESULT');p.update(fault_id=fid,target_scope=copy.deepcopy(f['origin']['scope']),origin_revisions=copy.deepcopy(f['origin']['revisions']),revisions=copy.deepcopy(f['expected_revisions']));return L.recover(C,a,y,fid,p)
x=failed();old_ids=copy.deepcopy(x['rejected_operation_ids']);f=L.open_faults(x,'B_RESET_CONFIRMED')[0]['fault_id']
for name in S.RECOVERY:
 v=values(A[name],'B-RESET');v['DEPENDENCY_VALID']='FALSE';check('recovery-own-entry:'+name,'ALLOWED_ASSUMED',S.entry_outcome(A[name],v,'B-RESET'))
 for g in sorted(set(A[name]['entry_guards']+A[name]['extra_entry_guards'])):
  for truth in ['FALSE','UNKNOWN']:
   vv=dict(v);vv[g]=truth;check('recovery-guard:'+name+':'+g+':'+truth,'BLOCKED' if truth=='FALSE' else 'INDETERMINATE',S.entry_outcome(A[name],vv,'B-RESET'))
x,status=recover(x,'RESTORE_B_CLOSURE',f,'unique-closure');check('targeted-closure','ALLOWED_ASSUMED',status);check('history-not-cleared',True,bool(L.open_faults(x,'DEPENDENCY_VALID')))
check('NEXT-before-reconcile','BLOCKED',L.evaluate(C,'B-NEXT',prepare(x,'B-NEXT','fresh-before-history'))['permission_outcome'])
x,r=L.decide(C,'B-RESET',prepare(x,'B-RESET','reset-commit'));check('frozen-reset-commit','ALLOWED_ASSUMED',r['permission_outcome'])
for i,dep in enumerate(L.open_faults(x,'DEPENDENCY_VALID')):
 x,status=recover(x,'RECONCILE_HISTORY',dep['fault_id'],'history-'+str(i));check('separate-history:'+str(i),'ALLOWED_ASSUMED',status)
check('new-NEXT','ALLOWED_ASSUMED',L.evaluate(C,'B-NEXT',prepare(x,'B-NEXT','new-next'))['permission_outcome'])
check('old-ID-still-denied','BLOCKED',L.evaluate(C,'B-NEXT',prepare(x,'B-NEXT','denied'))['permission_outcome']);check('rejected-memory',old_ids,x['rejected_operation_ids']);check('retained-memory',['retained'],x['inventory_refs'])
for guard in ['LEDGER_VALID','RESOURCES_READY','RECEIVER_DEFINED']:
 x=failed();trigger='B-LOAD' if guard=='RECEIVER_DEFINED' else 'B-RETURN';y=prepare(x,trigger,'unrelated-'+guard);y['state']=L.spec(C,trigger)['from_states'][0];y['evidence'][guard]['value']='FALSE';x,_=L.decide(C,trigger,y)
 f=L.open_faults(x,'B_RESET_CONFIRMED')[0]['fault_id'];x,status=recover(x,'REASSESS_B_CLOSURE',f,'audit-'+guard);check('independent-closure-audit:'+guard,'ALLOWED_ASSUMED',status)
 check('foreign-fault-preserved:'+guard,True,bool(L.open_faults(x,guard)))
 y=prepare(x,'B-RESET','movement-'+guard);truth,_=L.evidence_value(C,'B-RESET',guard,y,y['evidence'].get(guard),'ENTRY')
 for name in S.RECOVERY:
  v=values(A[name],'B-RESET');v[guard]=truth;check('movement-blocked-by-live-fault:'+name+guard,'BLOCKED',S.entry_outcome(A[name],v,'B-RESET'))
 for normal,state in [('B-LOAD','B_ACCEPTABLE_INITIAL'),('B-COMPACT','B_BATCH_SELECTED')]:
  y=prepare(x,normal,'normal-'+normal+guard);y['state']=state;check('no-ordinary-bypass:'+normal+guard,'BLOCKED',L.evaluate(C,normal,y,'ENTRY')['permission_outcome'])
# Isolated coherent mutations; refresh all exports/manifest. Original package is never modified.
mutation_names=['unknown_pose','work_starts_at_P0','drop_isolation_guard','cross_scenario_work_binding','wrong_parent_mode','unsupported_mode','wrong_phase_ref','ordinary_no_dependency','P1-coordinate','feed-open-without-path','return-without-doser-path','confirm-without-current-D1','recovery-any-fault','relock-without-lock-result']
(HERE/'mutations').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='r5-ci-recheck-') as tmp:
 for name in mutation_names:
  dest=Path(tmp)/name;pack=dest/'proposal';shutil.copytree(P,pack)
  for n in ['claim.json','input_manifest.json']:shutil.copy(P.parent/n,dest/n)
  d=copy.deepcopy(D);acts={r['id']:r for r in d['actions']};changes={}
  if name=='unknown_pose':acts['A-MECH-WORK']['poses']['punch']='UNDEFINED_POSE→P2'
  if name=='work_starts_at_P0':acts['A-MECH-WORK']['poses']['punch']='P0→P2';acts['A-MECH-WORK']['pose_endpoints']['punch']['start']=['P0']
  if name=='drop_isolation_guard':acts['A-MECH-WORK']['extra_entry_guards'].remove('G_ISOLATED_CURRENT')
  if name=='cross_scenario_work_binding':
   r=next(r for r in acts['A-COMPACT']['source_bindings'] if r['proposed_cad_field']=='stroke.work');r.update(parameter_id='R3_BASE_B_WORK_STROKE',source='verification/r3_parametric_sizing/results/BASE_B.json')
  if name=='wrong_parent_mode':acts['B-MECH-WORK']['parent_action_choices']=['A-COMPACT'];acts['B-MECH-WORK']['current_parent_guards']={'A-COMPACT':[]}
  if name=='unsupported_mode':acts['A-MECH-WORK']['mode'].append('A_STARTUP')
  if name=='wrong_phase_ref':acts['A-MECH-WORK']['resources']['source_main_axis_phase_refs'][0]['source']='verification/r3_power_reconcile/results/BASE_B.json'
  if name=='ordinary_no_dependency':acts['A-MECH-WORK']['entry_guards'].remove('DEPENDENCY_VALID')
  if name=='P1-coordinate':
   p=json.loads((pack/'poses.json').read_text());r=next(r for r in p['poses'] if r['id']=='P1');changes['coordinate_before']=r['coordinate'];r['coordinate']='x_P0 + S_eject';changes['coordinate_after']=r['coordinate'];(pack/'poses.json').write_text(json.dumps(p))
  if name=='feed-open-without-path':acts['A-MECH-FEED-OPEN']['extra_entry_guards'].remove('G_PATH_CLEAR')
  if name=='return-without-doser-path':acts['A-MECH-DOSER-RETURN']['extra_entry_guards'].remove('D_PATH_CLEAR')
  if name=='confirm-without-current-D1':
   for k in ['extra_entry_guards','extra_completion_guards']:acts['A-MECH-FILL-CONFIRM'][k].remove('D_DELIVERY_CURRENT')
  if name=='recovery-any-fault':acts['B-MECH-STOP-CLOSE']['recovery_binding']['target_fault_id']='ANY_FAULT'
  if name=='relock-without-lock-result':
   for g in ['LOCK_CLOSED_CURRENT','B_STOP_LOCK_CLOSED']:acts['B-MECH-RELOCK']['extra_completion_guards'].remove(g)
  (pack/'permissions.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
  gen=subprocess.run([sys.executable,'-B',str(pack/'render_schemes.py'),'--output-dir',str(pack/'exports')],capture_output=True,text=True);assert gen.returncode==0,gen.stderr
  before={str(p.relative_to(pack)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pack.rglob('*') if p.is_file()}
  manifest=json.loads((pack/'exports/exports_manifest.json').read_text())
  assert all(before[n]==h for n,h in manifest['sources_sha256'].items())
  assert all(before['exports/'+n]==h for n,h in manifest['exports_sha256'].items())
  r=subprocess.run([sys.executable,'-B',str(P/'check_package.py'),'--package',str(pack)],capture_output=True,text=True);out=json.loads(r.stdout)
  after={str(p.relative_to(pack)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pack.rglob('*') if p.is_file()};assert before==after
  (HERE/'mutations'/(name+'.json')).write_text(r.stdout)
  record=dict(id=name,expected_exit='NONZERO_SEMANTIC_REJECTION',exit_code=r.returncode,document_checks=out['document_checks'],reason=out.get('reason'),coherent_export=True,source_and_exports_sha256=before,checker_writes=False,hash_manifest_consistent=True,changes=changes)
  assert r.returncode==0 or out.get('reason','').startswith('semantic:'),(name,out)
  mutants.append(record);check('mutation:'+name,True,r.returncode!=0,reason=out.get('reason'),evidence='mutations/'+name+'.json')
  if name in ['unknown_pose','work_starts_at_P0','drop_isolation_guard','cross_scenario_work_binding','wrong_parent_mode']:
   replay.append(dict(original_id='semantic-mutation:'+name,corrected=r.returncode!=0));check('replay17:semantic-mutation:'+name,True,r.returncode!=0)
assert len(replay)==17
out=dict(session_id='r5-ci-recheck-20261113',reviewed_C='144941cbfc67002cbe81765e38c80e237473deff',historical_17=replay,historical_17_corrected=sum(r['corrected'] for r in replay),checks=checks,total_checks=len(checks),passed=sum(r['matches'] for r in checks),failed=[r for r in checks if not r['matches']],sequential_traces=traces,mutations=mutants,geometry='NOT_RUN',physical_READY='NO_GO',W02='OPEN_NOT_IMPLEMENTED',G1='OPEN',execution='EVIDENCE_CAPTURED_NOT_ACCEPTANCE')
print(json.dumps(out,ensure_ascii=False,indent=2))
