"""Independent coherent omission/provenance witnesses; fixed B_RESET domain obligations.
Imports only own fixture function definitions with AST, never runs export matrix again.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;P=ROOT/'verification/r4_cycle_interfaces/proposal'
sys.path.insert(0,str(P));import semantic_minimum as S
C=json.loads((ROOT/'verification/r4_cycle_contract/contract.json').read_text())
sp=importlib.util.spec_from_file_location('r5_frozen_incomplete',ROOT/'verification/r4_cycle_contract/permission_examples.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L)
tree=ast.parse((HERE/'independent_probe.py').read_text());functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'ev','prepare','fixture'}];exec(compile(ast.Module(body=functions,type_ignores=[]),'own_fixture','exec'))
required=next(g for g in C['guards'] if g['id']=='B_RESET_CONFIRMED')['evidence_domains'];assert required==['B_CLOSURE']
def readdress(x,p,origin):
 old=p['fault_id'];f=x['faults'].pop(old);f['origin']['revisions']=copy.deepcopy(origin);new='F-'+L.digest(f['origin']);f['fault_id']=new;x['faults'][new]=f;p.update(fault_id=new,origin_revisions=copy.deepcopy(origin));renames={old:new}
 for fid,other in list(x['faults'].items()):
  if any(c in renames for c in other['origin']['cause_fault_ids']):
   del x['faults'][fid];other['origin']['cause_fault_ids']=[renames.get(c,c) for c in other['origin']['cause_fault_ids']];nf='F-'+L.digest(other['origin']);other['fault_id']=nf;x['faults'][nf]=other;renames[fid]=nf
 x['unresolved_dependencies']=[renames.get(f,f) for f in x['unresolved_dependencies']];assert L.history_valid(x)
rows=[]
for name in ['valid','empty-expected','empty-origin-matched-proof','foreign-domain-origin-matched-proof','empty-origin-and-expected','empty-origin-unmatched-proof','omitted-proof-origin-field']:
 x,p=fixture(0)
 if name=='empty-expected':x['faults'][p['fault_id']]['expected_revisions']={}
 if name in ['empty-origin-matched-proof','foreign-domain-origin-matched-proof','empty-origin-and-expected','empty-origin-unmatched-proof']:
  readdress(x,p,{'FEED':0} if name=='foreign-domain-origin-matched-proof' else {})
 if name=='empty-origin-and-expected':x['faults'][p['fault_id']]['expected_revisions']={}
 if name=='empty-origin-unmatched-proof':p['origin_revisions']={'B_CLOSURE':0}
 if name=='omitted-proof-origin-field':p.pop('origin_revisions')
 before=copy.deepcopy((x,p));v=S.recovery_value(p,x,C);out,status=L.recover(C,'RESTORE_B_CLOSURE',x,p['fault_id'],p)
 expected='TRUE' if name=='valid' else 'UNKNOWN'
 rows.append(dict(id=name,required_origin_domains=required,expected_predicate=expected,predicate=v,matched=v==expected,frozen_outcome=status,returned_fault_status=out['faults'][p['fault_id']]['status'],caller_fault_status=x['faults'][p['fault_id']]['status'],original_unchanged=(x,p)==before,rejected_IDs_retained=set(x['rejected_operation_ids'])<=set(out['rejected_operation_ids']),history_valid=L.history_valid(x),proof=p,context=x))
 assert (x,p)==before and rows[-1]['rejected_IDs_retained'] and rows[-1]['history_valid']
result=dict(session_id='r5-ci-strict-types-20261113',C='fa0626372c03d11655624bb454458f82c30117f7',oracle='Mandatory B_CLOSURE domain from frozen guard definition, R1 no absent/unsupported revision may establish success; coherent F-digest recomputed, no helper/code/norm modification',cases=rows,matches=sum(r['matched'] for r in rows),failures=[r['id'] for r in rows if not r['matched']])
(HERE/'incomplete_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['matches','failures']}))
for r in rows:print(r['id'],r['expected_predicate'],r['predicate'],r['frozen_outcome'],r['returned_fault_status'])
