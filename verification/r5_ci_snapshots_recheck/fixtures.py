"""Own synthetic fixtures reused from independent R5, pinned frozen definitions.
No current author fixture or payload contributes domain expectations.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
FROZEN='0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed'
def blob(p):return subprocess.check_output(['git','show',FROZEN+':'+p],cwd=ROOT)
CP='verification/r4_cycle_contract/contract.json';HP='verification/r4_cycle_contract/permission_examples.py'
assert (ROOT/CP).read_bytes()==blob(CP) and (ROOT/HP).read_bytes()==blob(HP)
C=json.loads(blob(CP));sp=importlib.util.spec_from_file_location('own_frozen',ROOT/HP);L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L)
source=ROOT/'verification/r5_ci_strict_types_recheck/independent_probe.py'
t=ast.parse(source.read_text());nodes=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'ev','prepare','fixture'}];exec(compile(ast.Module(body=nodes,type_ignores=[]),'prior_independent_fixture','exec'))
G={g['id']:g for g in C['guards']};A=next(a for a in C['recovery_actions'] if a['id']=='RESTORE_B_CLOSURE');E=set(G['B_RESET_CONFIRMED']['evidence_domains']);U=set(C['evidence_policy']['domains']);ENTRY=set().union(*(set(G[g]['evidence_domains']) for g in A['entry_guards']));assert E=={'B_CLOSURE'}
def proof(x,fid):
 f=x['faults'][fid];p=ev(x,'RESTORE_B_CLOSURE','B_RESET_CONFIRMED','RECOVERY_RESULT');p.update(fault_id=fid,target_scope=copy.deepcopy(f['origin']['scope']),origin_revisions=copy.deepcopy(f['origin']['revisions']),revisions=copy.deepcopy(f['expected_revisions']));return p
def rekey(x,p):
 """Coherent negative fixture only; no candidate repairs or caller changes."""
 renames={}
 for key,f in list(x['faults'].items()):
  f['origin']['cause_fault_ids']=[renames.get(k,k) for k in f['origin']['cause_fault_ids']]
  new='F-'+L.digest(f['origin'])
  if new!=key:del x['faults'][key];f['fault_id']=new;x['faults'][new]=f;renames[key]=new
 p['fault_id']=renames.get(p['fault_id'],p['fault_id']);x['unresolved_dependencies']=[renames.get(k,k) for k in x['unresolved_dependencies']]
 assert L.history_valid(x)
