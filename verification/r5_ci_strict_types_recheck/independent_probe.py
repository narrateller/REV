"""Independent strict-type mutations and same-input recovery comparison.
Expectations: R1 ARB-R1-CI-SEMANTICS-02 exact JSON types and frozen policy,
not the mutated payload, author fixture, renderer, or current type predicates.
Exit zero means evidence capture completed; inspect failed and diagnostics.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0,str(P));import semantic_minimum as S
C=json.loads((ROOT/'verification/r4_cycle_contract/contract.json').read_text())
sp=importlib.util.spec_from_file_location('r5_frozen',ROOT/'verification/r4_cycle_contract/permission_examples.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L)
BAD=[('bool-true',True),('bool-false',False),('float-one',1.0),('float-zero',0.0),('string','1'),('null',None),('array',[]),('object',{}),('missing','__ABSENT__'),('negative',-1)]
checks=[];exports=[];diff=[]
def check(id,expected,actual,**extra):checks.append(dict(id=id,expected=expected,actual=actual,matched=expected==actual,**extra))
def sha(b):return hashlib.sha256(b).hexdigest()
def hashes(p):return {str(f.relative_to(p)):sha(f.read_bytes()) for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
def get(d,path):
 for k in path:d=d[k]
 return d
def put(d,path,v):
 a=get(d,path[:-1]);k=path[-1]
 if v=='__ABSENT__':a.pop(k)
 else:a[k]=copy.deepcopy(v)
D=json.loads((P/'permissions.json').read_text());poses=json.loads((P/'poses.json').read_text())
def ai(name):return next(i for i,a in enumerate(D['actions']) if a['id']==name)
def pi(name):return next(i for i,a in enumerate(poses['poses']) if a['id']==name)
# Other stages than the six original examples; all structural revision/provenance classes.
locations=[]
for action in ['A-GATHER','B-LOAD']:
 locations.append(('permissions.json',['actions',ai(action),'source_bindings',-1,'revision'],action+':binding'))
for action in ['A-EJECT','B-MECH-APPROACH']:
 locations.append(('permissions.json',['actions',ai(action),'resources','source_main_axis_phase_refs',-1,'revision'],action+':phase-ref'))
for action in ['A-RETURN','B-COMPACT']:
 locations.append(('permissions.json',['actions',ai(action),'phase_pose_bindings',0,'stroke_source','revision'],action+':phase-pose'))
for pose,scenario,term in [('P1','BASE_A',1),('P2','BASE_B',2),('P_RETURN_END','BASE_A',4)]:
 path=['poses',pi(pose),'coordinate_forms',scenario,'expression','terms',term]
 if 'operand' in get(poses,path):path+=['operand']
 locations.append(('poses.json',path+['source_ref','revision'],pose+':'+scenario+':AST'))
for scenario in ['BASE_A','BASE_B']:
 idx=next(i for i,r in enumerate(poses['source_refs']) if r['scenario']==scenario)
 locations.append(('poses.json',['source_refs',idx,'revision'],scenario+':pose-source'))
locations += [('baseline_bindings.json',['rows',-1,'revision'],'catalog'),('permissions.json',['normative_minimum','revision'],'permission-authority'),('poses.json',['normative_minimum','revision'],'pose-authority'),('exports/exports_manifest.json',['normative_minimum','revision'],'manifest-authority')]
(HERE/'mutations').mkdir(exist_ok=True)
def exported(id,edits,positive=False):
 with tempfile.TemporaryDirectory(prefix='r5-strict-type-') as tmp:
  dest=Path(tmp);pack=dest/'proposal';shutil.copytree(P,pack)
  for f in ['claim.json','input_manifest.json']:shutil.copy(P.parent/f,dest/f)
  def edit(file,path,val):
   f=pack/file;d=json.loads(f.read_text());put(d,path,val);f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
  for file,path,val in edits:
   if not file.startswith('exports/'):edit(file,path,val)
  r=subprocess.run([sys.executable,'-B',str(pack/'render_schemes.py'),'--output-dir',str(pack/'exports')],capture_output=True,text=True)
  assert r.returncode==0,(id,r.stderr)
  for file,path,val in edits:
   if file.startswith('exports/'):edit(file,path,val)
  before=hashes(pack);m=json.loads((pack/'exports/exports_manifest.json').read_text())
  fresh=all(before[f]==v for f,v in m['sources_sha256'].items()) and all(before['exports/'+f]==v for f,v in m['exports_sha256'].items());assert fresh
  r=subprocess.run([sys.executable,'-B',str(P/'check_package.py'),'--package',str(pack)],capture_output=True,text=True);d=json.loads(r.stdout)
  unchanged=before==hashes(pack);assert unchanged
  filename=id.replace(':','_')+'.json';(HERE/'mutations'/filename).write_text(r.stdout)
  expected='MATCH' if positive else 'REJECTED';actual='MATCH' if r.returncode==0 else 'REJECTED'
  check('export:'+id,expected,actual)
  exports.append(dict(id=id,edits=edits,expected=expected,actual=actual,exit_code=r.returncode,semantic_outcome=d.get('semantic_outcome'),fresh_source_export_hashes=fresh,checker_writes=not unchanged,evidence='mutations/'+filename,manifest_sha256=before['exports/exports_manifest.json']))
for file,path,tag in locations:
 for name,v in BAD+[('zero',0),('integer-wrong-value',2),('integer-large',2**63)]:exported(tag+':'+name,[(file,path,v)])
 # Positive original integer revision is a fixed source identity, not arbitrary source version 2.
 exported(tag+':integer-one',[(file,path,1)],True)
# Coherently corrupt independent structural classes together, not only one leaf.
for name,val in [('compound-bool',True),('compound-float',1.0),('compound-null',None)]:
 exported(name,[(f,p,val) for f,p,t in locations if not f.startswith('exports/')])
# Formula algebra and physical numeric values must retain their own semantics.
exported('equivalent-formula',[('poses.json',['poses',pi('P3'),'coordinate'],'(S_eject + x_P0) + (S_work + S_approach)')],True)
row=json.loads((P/'baseline_bindings.json').read_text())['rows'][0]
exported('physical-int-float',[('baseline_bindings.json',['rows',0,'value'],float(row['value']))],True)
# Self-contained synthetic history and proof, independent of author test helpers.
def ev(x,a,g,phase=None):
 t=L.spec(C,a)
 return dict({k:x[k] for k in C['evidence_policy']['scope_fields']+['operation_id']},action=a,guard=g,phase=phase or ('COMPLETION' if g in t['completion_guards'] else 'ENTRY'),value='TRUE',revisions=copy.deepcopy(x['revisions']),evidence_id='R5-'+a+g,method='ASSUMED_FIXTURE',source='independent synthetic evidence only',valid_for_operation_interval=True)
def prepare(x,a,op):
 x=copy.deepcopy(x);x['operation_id']=op;x['evidence']={g:ev(x,a,g) for g in L.spec(C,a)['required_guards']};return x
def fixture(n):
 x=dict(scenario_id='R5-TYPE-MATRIX',variant='B',mode='B_REPEAT',state='B_RECEIVED_RESIDUAL',subject_id='closure',batch_id='batch',cycle_epoch='epoch',basis_id='basis',basis_revision='r1',operation_id='denied-A',revisions={k:n for k in C['evidence_policy']['domains']},inventory_refs=['retained'],pending_observations=[])
 x=L.initialize_history(x,'R5-type-history',dict(value='TRUE',evidence_id='initial',source='hypothetical audit'))
 x=prepare(x,'B-NEXT','denied-A');x['evidence']['B_RESET_CONFIRMED']['value']='FALSE';x,_=L.decide(C,'B-NEXT',x)
 x=prepare(x,'RESTORE_B_CLOSURE','unique-recovery')
 f=L.open_faults(x,'B_RESET_CONFIRMED')[0];p=ev(x,'RESTORE_B_CLOSURE','B_RESET_CONFIRMED','RECOVERY_RESULT');p.update(fault_id=f['fault_id'],target_scope=copy.deepcopy(f['origin']['scope']),origin_revisions=copy.deepcopy(f['origin']['revisions']),revisions=copy.deepcopy(f['expected_revisions']))
 return x,p
mapping={'ALLOWED_ASSUMED':'TRUE','BLOCKED':'FALSE','INDETERMINATE':'UNKNOWN'}
def compare(id,x,p,admit=False):
 before=copy.deepcopy((x,p));truth=S.recovery_value(p,x,C);fid=p['fault_id'];out,status=L.recover(C,'RESTORE_B_CLOSURE',x,fid,p)
 unchanged=(x,p)==before;retained=set(x['rejected_operation_ids'])<=set(out['rejected_operation_ids']);status_fault=out['faults'][fid]['status']
 check('recovery-admission:'+id,admit,truth=='TRUE');check('recovery-frozen-admission:'+id,admit,status=='ALLOWED_ASSUMED')
 check('readonly:'+id,True,unchanged);check('rejected-IDs:'+id,True,retained);check('fault-status:'+id,'RESOLVED' if admit else 'OPEN',status_fault)
 # Record exact diagnostic agreement independently of non-admission criteria.
 check('policy-classification:'+id,mapping[status],truth)
 diff.append(dict(id=id,predicate=truth,frozen_outcome=status,fault_status=status_fault,readonly=unchanged,rejected_IDs_retained=retained,classification_equal=truth==mapping[status],proof=p,context=x))
for n in [0,1,2**63]:
 x,p=fixture(n);compare('valid-integer-'+str(n),x,p,True)
x,p=fixture(0)
for field in ['origin_revisions','revisions']:
 for domain in p[field]:
  for name,v in BAD+[('stale-positive',1)]:
   q=copy.deepcopy(p);put(q,[field,domain],v);compare(field+':'+domain+':'+name,x,q)
 for name,v in [('null',None),('array',[]),('string','0'),('missing','__ABSENT__'),('empty-map',{})]:
  q=copy.deepcopy(p);put(q,[field],v);compare(field+':'+name,x,q)
# Current context and fault expected snapshots, including all runtime domains.
for domain in x['revisions']:
 for name,v in BAD+[('stale-positive',1)]:
  y=copy.deepcopy(x);put(y,['revisions',domain],v);compare('context:'+domain+':'+name,y,p)
for domain in x['faults'][p['fault_id']]['expected_revisions']:
 for name,v in BAD+[('stale-positive',1)]:
  y=copy.deepcopy(x);put(y,['faults',p['fault_id'],'expected_revisions',domain],v);compare('expected:'+domain+':'+name,y,p)
# Immutable-origin corruption with coherent new fault digest; no accidental invalid-history shortcut.
for domain in x['faults'][p['fault_id']]['origin']['revisions']:
 for name,v in BAD:
  y=copy.deepcopy(x);q=copy.deepcopy(p);old=q['fault_id'];f=y['faults'].pop(old);put(f,['origin','revisions',domain],v);new='F-'+L.digest(f['origin']);f['fault_id']=new;y['faults'][new]=f;q['fault_id']=new
  # Rehash causal dependency chain in topological order, retaining immutable rejected records.
  renames={old:new}
  for fid,other in list(y['faults'].items()):
   if any(c in renames for c in other['origin']['cause_fault_ids']):
    del y['faults'][fid];other['origin']['cause_fault_ids']=[renames.get(c,c) for c in other['origin']['cause_fault_ids']];nf='F-'+L.digest(other['origin']);other['fault_id']=nf;y['faults'][nf]=other;renames[fid]=nf
  y['unresolved_dependencies']=[renames.get(f,f) for f in y['unresolved_dependencies']]
  assert L.history_valid(y)
  compare('immutable-origin:'+domain+':'+name,y,q)
for field in ['subject_id','cycle_epoch']:
 y=copy.deepcopy(x);y[field]+='-foreign';compare('foreign-context:'+field,y,p)
for field,v in [('target_scope',None),('target_scope',{}),('phase','ENTRY'),('value','FALSE'),('value','UNKNOWN')]:
 q=copy.deepcopy(p);q[field]=v;compare('proof:'+field+':'+str(v),x,q)
# Compound/sequential: a second resource denial plus malformed origin; fault must stay blocked.
y=prepare(x,'B-RETURN','denied-B');y['evidence']['RESOURCES_READY']['value']='FALSE';y,_=L.decide(C,'B-RETURN',y);y=prepare(y,'RESTORE_B_CLOSURE','fresh-after-two-denials')
for name,v in [('valid',0),('bool',False),('float',0.0),('null',None),('missing','__ABSENT__')]:
 q=copy.deepcopy(p);q.update({k:y[k] for k in C['evidence_policy']['scope_fields']+['operation_id']});q['revisions']=copy.deepcopy(y['revisions'])
 for domain in list(q['origin_revisions']):put(q,['origin_revisions',domain],v)
 compare('two-denials:'+name,y,q)
 # Gate remains BLOCKED for real own conditions even when predicate diagnostic is UNKNOWN.
 values={g:'TRUE' for g in D['actions'][ai('B-MECH-RELOCK')]['entry_guards']+D['actions'][ai('B-MECH-RELOCK')]['extra_entry_guards']};values['RESOURCES_READY']='FALSE';values['RECOVERY_SCOPE_VALID']=S.recovery_value(q,y,C)
 import document_semantics as DS
 check('compound-final-gate:'+name,'BLOCKED',DS.entry_outcome(D['actions'][ai('B-MECH-RELOCK')],values,None))
result=dict(session_id='r5-ci-strict-types-20261113',reviewed_C='fa0626372c03d11655624bb454458f82c30117f7',total_checks=len(checks),matches=sum(c['matched'] for c in checks),failed=[c for c in checks if not c['matched']],export_cases=exports,recovery_cases=diff,checks=checks,W02='OPEN_NOT_IMPLEMENTED',physical_READY='NO_GO',G1='OPEN')
(HERE/'independent_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['total_checks','matches','failed']},ensure_ascii=False,indent=2))
