"""Independent bounded audit and coherent mutations; no PLC/W02/CAD acceptance.
Expected rules come from fixed reviewed inputs and explicit independent obligations,
never from the mutable --package or its exports. Exit 0 captures all findings.
"""
from pathlib import Path
from collections import Counter
import copy,csv,hashlib,importlib.util,json,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0,str(P));import semantic_minimum as S
N=json.loads((P.parent/'semantics_v1/minimum.json').read_text());D=json.loads((P/'permissions.json').read_text());POSE=json.loads((P/'poses.json').read_text());A={a['id']:a for a in D['actions']}
def blob(c,p):return json.loads(subprocess.check_output(['git','show',c+':'+p],cwd=ROOT))
BASE='144941cbfc67002cbe81765e38c80e237473deff';FROZEN='0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed';DEC='5fe510bbc55a052c360ab39a2491a061584b8fb7'
B={a['id']:a for a in blob(BASE,'verification/r4_cycle_interfaces/proposal/permissions.json')['actions']};C=blob(FROZEN,'verification/r4_cycle_contract/contract.json');F={a['id']:a for a in C['transitions']}
checks=[];mutations=[]
def check(id,expected,actual,**detail):checks.append(dict(id=id,expected=expected,actual=actual,matches=expected==actual,**copy.deepcopy(detail)))
# Independently specified critical conditions/results from R1 clauses 1,3,4,5.
REQ={
 'FEED-OPEN':('G_PATH_CLEAR D_HOME_CURRENT P_FEED_CLEAR MATERIAL_HELD_CURRENT CAPACITY_CURRENT','G_OPEN_CURRENT'),
 'FEED-RESET':('G_PATH_CLEAR D_HOME_CURRENT P_FEED_CLEAR MATERIAL_HELD_CURRENT CAPACITY_CURRENT','G_OPEN_CURRENT'),
 'DOSE-DELIVER':('D_HOME_CURRENT D_PATH_CLEAR G_OPEN_CURRENT P_FEED_CLEAR CAPACITY_CURRENT','D_DELIVERY_CURRENT'),
 'FILL-CONFIRM':('D_DELIVERY_CURRENT D_PATH_CLEAR G_OPEN_CURRENT P_FEED_CLEAR','D_DELIVERY_CURRENT FILL_COMPLETE'),
 'DOSER-RETURN':('D_DELIVERY_CURRENT D_PATH_CLEAR FILL_COMPLETE G_OPEN_CURRENT P_FEED_CLEAR','D_HOME_CURRENT P_FEED_CLEAR'),
 'FEED-ISOLATE':('D_HOME_CURRENT G_PATH_CLEAR P_FEED_CLEAR FEEDER_SAFE FILL_COMPLETE LOAD_COMMITTED_CURRENT','G_ISOLATED_CURRENT'),
 'APPROACH':('P_HOME_CURRENT P_PATH_CLEAR D_HOME_CURRENT G_ISOLATED_CURRENT REACTION_CURRENT REAR_FORCE_INTERFACE','CONTINUOUS_MECHANISM'),
 'WORK':('P_PATH_CLEAR D_HOME_CURRENT G_ISOLATED_CURRENT REACTION_CURRENT REAR_FORCE_INTERFACE','CONTINUOUS_MECHANISM'),
 'HOLD-UNLOAD':('D_HOME_CURRENT G_ISOLATED_CURRENT MATERIAL_HELD_CURRENT REACTION_CURRENT','CONTINUOUS_MECHANISM'),
 'UNLOCK':('B_UNLOADED B_OPEN_SEQUENCE_VALID P_PATH_CLEAR D_HOME_CURRENT G_ISOLATED_CURRENT','LOCK_CLEAR'),
 'STOP-OPEN':('B_UNLOADED B_OPEN_SEQUENCE_VALID LOCK_CLEAR P_PATH_CLEAR','STOP_OPEN'),
 'STOP-CLOSE':('RECOVERY_SCOPE_VALID RESET_SWEEP_CLEAR RESTORE_SEQUENCE_DEFINED RECEIPT_VALID P_PATH_CLEAR D_HOME_CURRENT G_ISOLATED_CURRENT','STOP_CLOSED_CURRENT'),
 'RELOCK':('RECOVERY_SCOPE_VALID RESET_SWEEP_CLEAR RESTORE_SEQUENCE_DEFINED RECEIPT_VALID P_PATH_CLEAR STOP_CLOSED_CURRENT','STOP_CLOSED_CURRENT LOCK_CLOSED_CURRENT B_STOP_LOCK_CLOSED')}
check('authority-source-commits',dict(accepted_B01_B02=BASE,frozen_material=FROZEN,R1_arbitration=DEC),N['source_commits'])
check('closed-53-actions',set(B)==set(N['actions'])==set(A),True);check('84-modes',84,sum(len(a['modes']) for a in N['actions'].values()))
coverage=json.loads((P.parent/'semantics_v1/coverage.json').read_text());rows={(r['action'],r['mode']):r for r in coverage['rows']}
with (P.parent/'semantics_v1/coverage.csv').open() as f:csvrows=list(csv.DictReader(f))
check('coverage-json-csv',coverage['rows'],csvrows)
for name,old in B.items():
 r=N['actions'][name];mech='-MECH-' in name
 expected_entry=set(old['entry_guards']+old['extra_entry_guards'])
 expected_result=set(old['completion_guards']+old['extra_completion_guards'])
 if mech:
  family=name.split('-MECH-')[1];entry,result=REQ[family];expected_entry|=set(entry.split());expected_result|=set(result.split())
  if family not in ['STOP-CLOSE','RELOCK']:expected_entry.add('DEPENDENCY_VALID')
 check('rule-entry:'+name,True,expected_entry<=set(r['entry_minimum']))
 check('rule-result:'+name,True,expected_result<=set(r['completion_exact']))
 check('rule-topology:'+name,True,all(r[k]==old[v] for k,v in [('variant','variant'),('material_from','material_from'),('material_to','material_to'),('poses','poses'),('pose_endpoints','pose_endpoints')]))
 check('rule-parents:'+name,old.get('parent_action_choices',[]),r['parents']);check('rule-modes:'+name,old['mode'],r['modes'])
 guard_outputs={o['guard'] for o in r['outputs'] if o['kind']=='GUARD_CONFIRMATION'}
 check('rule-output-guards:'+name,set(r['completion_exact']),guard_outputs)
 check('rule-unknown-results:'+name,True,all(o['actual']=='UNKNOWN' for o in r['outputs']))
 for body,end in old['pose_endpoints'].items():
  matches=[o for o in r['outputs'] if o.get('body')==body]
  check('rule-pose-output:'+name+':'+body,True,len(matches)==1 and matches[0]['poses']==end['end'])
 for mode in old['mode']:
  row=rows[(name,mode)];check('coverage84:'+name+':'+mode,True,json.loads(row['entry_minimum'])==r['entry_minimum'] and json.loads(row['outputs'])==r['outputs'] and json.loads(row['parents'])==[par for par in old.get('parent_action_choices',[]) if mode in B[par]['mode']] and row['from']==json.dumps(old['material_from']) and row['to']==old['material_to'])
# Own polynomial oracle, references from immutable authoritative 44 source rows, not current AST.
source_rows=blob(BASE,'verification/r4_cycle_interfaces/proposal/baseline_bindings.json')['rows'];refs={(r['scenario'],r['proposed_cad_field'].split('.')[-1]):{k:r[k] for k in ['scenario','proposed_cad_field','parameter_id','revision','source','unit']} for r in source_rows if r['proposed_cad_field'].startswith('stroke.')}
def strict(a,b):return json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)
def poly(node,scenario):
 op=node['op']
 if op=='symbol':return Counter({('symbol',node['id']):1})
 if op=='phase_stroke':
  assert strict(node['source_ref'],refs[(scenario,node['phase'])]);return Counter({('stroke',scenario,node['phase']):1})
 if op=='sum':
  out=Counter()
  for t in node['terms']:
   for k,v in poly(t,scenario).items():out[k]+=v
  return +out if all(v>=0 for v in out.values()) else Counter({k:v for k,v in out.items() if v})
 if op=='neg':return Counter({k:-v for k,v in poly(node['operand'],scenario).items()})
 raise ValueError(op)
for pose,phases in [('P1',['approach']),('P2',['approach','work']),('P3',['approach','work','eject']),('P_RETURN_END',['approach','work','eject','-return'])]:
 for scenario in ['BASE_A','BASE_B']:
  want=Counter({('symbol','x_P0'):1})
  for phase in phases:want[('stroke',scenario,phase.lstrip('-'))]+= -1 if phase.startswith('-') else 1
  check('independent-formula:'+pose+':'+scenario,want,poly(N['poses'][pose]['forms'][scenario]['expression'],scenario))
# Concrete recovery proof: test new reference wrapper against unchanged authoritative helper.
s=importlib.util.spec_from_file_location('frozen',ROOT/'verification/r4_cycle_contract/permission_examples.py');L=importlib.util.module_from_spec(s);s.loader.exec_module(L)
def ev(x,a,g,phase=None):
 t=L.spec(C,a);return dict({k:x[k] for k in C['evidence_policy']['scope_fields']+['operation_id']},action=a,guard=g,phase=phase or ('COMPLETION' if g in t['completion_guards'] else 'ENTRY'),value='TRUE',revisions=copy.deepcopy(x['revisions']),evidence_id='R5-'+a+g,method='ASSUMED_FIXTURE',source='independent hypothetical evidence',valid_for_operation_interval=True)
x=dict(scenario_id='R5-TYPED',variant='B',mode='B_REPEAT',state='B_RECEIVED_RESIDUAL',subject_id='closure',batch_id='batch',cycle_epoch='epoch',basis_id='basis',basis_revision='r1',operation_id='old-denied',revisions={k:0 for k in C['evidence_policy']['domains']},inventory_refs=['retained'],pending_observations=[])
x=L.initialize_history(x,'R5-history',dict(value='TRUE',evidence_id='initial',source='hypothetical audit'));x['evidence']={g:ev(x,'B-NEXT',g) for g in L.spec(C,'B-NEXT')['required_guards']};x['evidence']['B_RESET_CONFIRMED']['value']='FALSE';x,_=L.decide(C,'B-NEXT',x)
x['operation_id']='new-exact-recovery';x['evidence']={g:ev(x,'RESTORE_B_CLOSURE',g) for g in L.spec(C,'RESTORE_B_CLOSURE')['required_guards']};fault=L.open_faults(x,'B_RESET_CONFIRMED')[0];fid=fault['fault_id']
proof=ev(x,'RESTORE_B_CLOSURE','B_RESET_CONFIRMED','RECOVERY_RESULT');proof.update(fault_id=fid,target_scope=copy.deepcopy(fault['origin']['scope']),origin_revisions=copy.deepcopy(fault['origin']['revisions']),revisions=copy.deepcopy(fault['expected_revisions']))
check('valid-reference-proof','TRUE',S.recovery_value(proof,x,C))
proof_cases=[]
for name,val in [('boolean-False',False),('float-zero',0.0)]:
 p=copy.deepcopy(proof);p['origin_revisions']={k:val for k in p['origin_revisions']};before=copy.deepcopy(x);actual=S.recovery_value(p,x,C);after,status=L.recover(C,'RESTORE_B_CLOSURE',x,fid,p)
 check('typed-origin:'+name,'UNKNOWN',actual,frozen_outcome=status,proof=p,context=x)
 check('frozen-rejects:'+name,'INDETERMINATE',status);check('no-original-clear:'+name,before,x);check('frozen-fault-stays-open:'+name,'OPEN',after['faults'][fid]['status'])
 proof_cases.append(dict(id=name,expected='UNKNOWN',actual=actual,frozen_outcome=status,frozen_fault_status=after['faults'][fid]['status']))
# Every stage has its own ENTRY/output mutation; old six and new classes are explicit.
CASES=[]
for name,old in B.items():
 if '-MECH-' in name:
  wanted=REQ[name.split('-MECH-')[1]][0].split();guard=next((g for g in wanted if 'PATH' in g or 'SWEEP' in g),wanted[0])
 else:guard=F[name]['entry_guards'][0]
 CASES.extend([('entry:'+name,('drop-entry',name,guard)),('output:'+name,('drop-output',name,None))])
CASES += [(n,(n,None,None)) for n in ['P1-coordinate','feed-open-without-path','return-without-doser-path','confirm-without-current-D1','recovery-any-fault','relock-without-lock-result','coherent-P3','foreign-return-source','unsupported-formula','missing-frame','forged-minimum','equivalent-P2','B-work-bool-revision','A-return-float-revision','B-P3-bool-AST','A-phase-binding-bool']]
(HERE/'mutations').mkdir(exist_ok=True)
captured={}
if '--reuse-mutations' in sys.argv:
 saved=json.loads((HERE/'captured_mutations.json').read_text());assert saved['C']=='bd7ce8a623d6a4ecdff1f106868a4c7086a8a27f' and saved['normative_sha256']==hashlib.sha256((P.parent/'semantics_v1/minimum.json').read_bytes()).hexdigest() and saved['checker_sha256']==hashlib.sha256((P/'check_package.py').read_bytes()).hexdigest()
 captured={r['id']:r for r in saved['cases']}
with tempfile.TemporaryDirectory(prefix='r5-norm-mut-') as temp:
 for name,(kind,action,guard) in CASES:
  if captured:
   record=captured[name];j=json.loads((HERE/record['evidence']).read_text());assert j.get('semantic_outcome')==record['semantic_outcome'] and (record['exit_code']==0)==(record['actual']=='MATCH') and record['hashes_fresh'] and not record['checker_writes']
   for f in ['check_package.py','semantic_minimum.py','document_semantics.py','render_schemes.py']:assert record['source_and_export_sha256'][f]==hashlib.sha256((P/f).read_bytes()).hexdigest()
   mutations.append(record);check('mutation:'+name,record['expected'],record['actual'],semantic_outcome=j.get('semantic_outcome'),reason=j.get('reason'));continue
  dest=Path(temp)/name.replace(':','_');pack=dest/'proposal';shutil.copytree(P,pack)
  for f in ['claim.json','input_manifest.json']:shutil.copy(P.parent/f,dest/f)
  d=copy.deepcopy(D);p=copy.deepcopy(POSE);a={r['id']:r for r in d['actions']};poses={r['id']:r for r in p['poses']}
  if kind=='drop-entry':
   for k in ['entry_guards','extra_entry_guards']:a[action][k]=[g for g in a[action][k] if g!=guard]
  elif kind=='drop-output':a[action]['outputs'].pop()
  elif kind=='P1-coordinate':poses['P1']['coordinate']='x_P0 + S_eject'
  elif kind=='feed-open-without-path':a['A-MECH-FEED-OPEN']['extra_entry_guards'].remove('G_PATH_CLEAR')
  elif kind=='return-without-doser-path':a['A-MECH-DOSER-RETURN']['extra_entry_guards'].remove('D_PATH_CLEAR')
  elif kind=='confirm-without-current-D1':
   for k in ['extra_entry_guards','extra_completion_guards']:a['A-MECH-FILL-CONFIRM'][k].remove('D_DELIVERY_CURRENT')
  elif kind=='recovery-any-fault':a['B-MECH-STOP-CLOSE']['recovery_binding']['target_fault_id']='ANY_FAULT'
  elif kind=='relock-without-lock-result':
   for g in ['LOCK_CLOSED_CURRENT','B_STOP_LOCK_CLOSED']:a['B-MECH-RELOCK']['extra_completion_guards'].remove(g)
  elif kind=='coherent-P3':
   poses['P3'].update(coordinate='x_P0 + S_approach + S_eject',display_formula='P0 + S_approach + S_eject')
   for form in poses['P3']['coordinate_forms'].values():form['expression']['terms']=[t for t in form['expression']['terms'] if t.get('phase')!='work']
  elif kind=='foreign-return-source':
   node=poses['P_RETURN_END']['coordinate_forms']['BASE_B']['expression']['terms'][-1]['operand'];node['source_ref']=copy.deepcopy(refs[('BASE_A','return')])
  elif kind=='unsupported-formula':poses['P2']['coordinate']='sin(x_P0)'
  elif kind=='missing-frame':poses['D1']['coordinate_forms']['BASE_B']['frame']=None
  elif kind=='equivalent-P2':poses['P2']['coordinate']='S_work + (x_P0 + S_approach)'
  elif kind=='forged-minimum':
   a['B-MECH-FEED-RESET']['extra_entry_guards'].remove('G_PATH_CLEAR');fake=copy.deepcopy(N);fake['actions']['B-MECH-FEED-RESET']['entry_minimum'].remove('G_PATH_CLEAR');content=json.dumps(fake,sort_keys=True);(pack/'minimum.json').write_text(content)
   for obj in [d,p]:obj['normative_minimum']['sha256']=hashlib.sha256(content.encode()).hexdigest()
  elif kind=='B-work-bool-revision':a['B-MECH-WORK']['resources']['source_main_axis_phase_refs'][0]['revision']=True
  elif kind=='A-return-float-revision':a['A-RETURN']['resources']['source_main_axis_phase_refs'][0]['revision']=1.0
  elif kind=='B-P3-bool-AST':poses['P3']['coordinate_forms']['BASE_B']['expression']['terms'][-1]['source_ref']['revision']=True
  elif kind=='A-phase-binding-bool':a['A-MECH-APPROACH']['phase_pose_bindings'][0]['stroke_source']['revision']=True
  (pack/'permissions.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(pack/'poses.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
  r=subprocess.run([sys.executable,'-B',str(pack/'render_schemes.py'),'--output-dir',str(pack/'exports')],capture_output=True,text=True);assert r.returncode==0,(name,r.stderr)
  before={str(f.relative_to(pack)):hashlib.sha256(f.read_bytes()).hexdigest() for f in pack.rglob('*') if f.is_file()};manifest=json.loads((pack/'exports/exports_manifest.json').read_text())
  assert all(before[f]==h for f,h in manifest['sources_sha256'].items()) and all(before['exports/'+f]==h for f,h in manifest['exports_sha256'].items())
  r=subprocess.run([sys.executable,'-B',str(P/'check_package.py'),'--package',str(pack)],capture_output=True,text=True);j=json.loads(r.stdout)
  after={str(f.relative_to(pack)):hashlib.sha256(f.read_bytes()).hexdigest() for f in pack.rglob('*') if f.is_file()};assert before==after
  (HERE/'mutations'/(name.replace(':','_')+'.json')).write_text(r.stdout)
  expected='MATCH' if kind=='equivalent-P2' else 'REJECTED';actual='MATCH' if r.returncode==0 else 'REJECTED'
  check('mutation:'+name,expected,actual,semantic_outcome=j.get('semantic_outcome'),reason=j.get('reason'))
  mutations.append(dict(id=name,expected=expected,actual=actual,exit_code=r.returncode,semantic_outcome=j.get('semantic_outcome'),hashes_fresh=True,checker_writes=False,source_and_export_sha256=before,evidence='mutations/'+name.replace(':','_')+'.json'))
result=dict(session_id='r5-ci-minimum-20261113',reviewed_C='bd7ce8a623d6a4ecdff1f106868a4c7086a8a27f',norm_actions=53,norm_action_modes=84,norm_pose_rules=18,normative_sha256=hashlib.sha256((P.parent/'semantics_v1/minimum.json').read_bytes()).hexdigest(),total_checks=len(checks),matches=sum(c['matches'] for c in checks),failed=[c for c in checks if not c['matches']],checks=checks,concrete_recovery_cases=proof_cases,mutations=mutations,execution='EVIDENCE_CAPTURED_NOT_ACCEPTANCE',W02='OPEN_NOT_IMPLEMENTED',physical_READY='NO_GO',G1='OPEN')
# Counter keys are tuples: convert them for standalone JSON, preserving symbolic terms.
def serial(value):
 if isinstance(value,dict):return {str(k) if isinstance(k,tuple) else k:serial(v) for k,v in value.items()}
 if isinstance(value,list):return [serial(v) for v in value]
 if isinstance(value,set):return sorted(serial(v) for v in value)
 return value
print(json.dumps(serial(result),ensure_ascii=False,indent=2))
