"""Explicit ASSUMED documentary fixtures, never default real observations."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
C=json.loads((ROOT/'verification/r4_cycle_contract/contract.json').read_text())
s=importlib.util.spec_from_file_location('identity_logic',ROOT/'verification/r4_cycle_contract/permission_examples.py');L=importlib.util.module_from_spec(s);s.loader.exec_module(L)

def evidence(ctx,action,guard,value='TRUE',phase=None):
 t=L.spec(C,action)
 return dict({k:ctx[k] for k in C['evidence_policy']['scope_fields']+['operation_id']},action=action,guard=guard,
  phase=phase or ('COMPLETION' if guard in t['completion_guards'] else 'ENTRY'),value=value,
  revisions=deepcopy(ctx['revisions']),evidence_id='ASSUMED-'+ctx['operation_id']+'-'+guard,
  source='Explicit logical fixture, not REV',method='ASSUMED_DOCUMENT_WITNESS',valid_for_operation_interval=True)

def fresh(action,state=None,**overrides):
 t=L.spec(C,action);state=state or t['from_states'][0]
 x=dict(scenario_id='ASSUMED',variant='A' if state.startswith('A_') else 'B',mode=(t.get('allowed_modes') or C['state_modes'][state])[0],
  subject_id='material-X',batch_id='batch-X',cycle_epoch='epoch-X',basis_id='ASSUMED_BASIS',basis_revision='basis-r1',operation_id='request-X',state=state,
  revisions={d:0 for d in C['evidence_policy']['domains']},material_assessment='ASSUMED_IDENTIFIED',inventory_refs=['material-X'],pending_observations=[])
 x.update(overrides);x=L.initialize_history(x,'ASSUMED-history',dict(value='TRUE',evidence_id='initial-history-audit',source='Explicit hypothetical new history'))
 x['evidence']={g:evidence(x,action,g) for g in t['required_guards']};return x

def retarget(ctx,action,operation_id,**changes):
 x=deepcopy(ctx);x.update(changes);x['operation_id']=operation_id
 x['evidence']={g:evidence(x,action,g) for g in L.spec(C,action)['required_guards']};return x

def failed_material(subject='material-X',batch='batch-X'):
 x=fresh('A-RECEIVE',subject_id=subject,batch_id=batch,cycle_epoch='epoch-'+batch,operation_id='loss-'+subject)
 x['evidence']['LEDGER_VALID']['value']='FALSE';x,r=L.decide(C,'A-RECEIVE',x)
 assert r['permission_outcome']=='BLOCKED';return x

def one(ctx,guard,subject=None,operation=None):
 xs=[f for f in L.open_faults(ctx,guard) if (subject is None or f['origin']['scope']['subject_id']==subject) and (operation is None or f['origin']['operation_id']==operation)]
 assert len(xs)==1,(guard,subject,operation,len(xs));return xs[0]['fault_id']

def query(ctx,fid,operation,action=None):
 f=ctx['faults'][fid];g=f['origin']['guard'];action=action or ('RECONCILE_HISTORY' if g in ['DEPENDENCY_VALID','EVENT_FRESH'] else 'REASSESS_MATERIAL')
 changes={k:v for k,v in f['origin']['scope'].items() if k!='subject_kind'}
 return retarget(ctx,action,operation,**changes)

def proof(ctx,action,fid,value='TRUE',ack_request=False):
 f=ctx['faults'][fid];g=f['origin']['guard'];p=evidence(ctx,action,g,value,'RECOVERY_RESULT')
 p.update(fault_id=fid,target_scope=L.scope(C,g,ctx),origin_revisions=deepcopy(f['origin']['revisions']))
 if ack_request:p.update(resolution_kind='DENIED_REQUEST_ACKNOWLEDGED',denied_operation_id=f['origin']['operation_id'],rejection_record_ids=sorted(ctx['rejected_operations'][f['origin']['operation_id']]))
 return p
