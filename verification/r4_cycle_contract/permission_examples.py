"""Documentary permission/history examples; no physical or material engine.

Immutable fault origins, explicit fault-ID recovery, cumulative rejected IDs.
All TRUE observations in tests are ASSUMED, never actual REV measurements.
"""
from copy import deepcopy
import hashlib
import json

HISTORY_SCHEMA = 'rev-permission-history/1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def spec(contract, action):
    return next(t for t in contract['transitions'] + contract['recovery_actions'] if t['id'] == action)


def conjunction(values, state_allowed=True):
    if not state_allowed or 'FALSE' in values:
        return 'BLOCKED'
    return 'INDETERMINATE' if 'UNKNOWN' in values else 'ALLOWED_ASSUMED'


def initialize_history(context, history_id, initial_audit):
    """Explicit new-history audit, never a reset/import of existing history."""
    if context.get('faults') or any(k in context for k in ['history_schema','rejected_operations','rejected_operation_ids']):
        raise ValueError('preserve/restore existing history instead of initializing it')
    out = deepcopy(context)
    out.update(history_schema=HISTORY_SCHEMA, history_id=history_id,
               history_confirmed=bool(isinstance(initial_audit,dict) and initial_audit.get('value') == 'TRUE' and initial_audit.get('evidence_id') and initial_audit.get('source')),
               initial_history_audit=deepcopy(initial_audit), faults={}, rejected_operation_ids=[],
               rejected_operations={}, completed_operations={}, authorized_entries={}, unresolved_dependencies=[])
    return out


def history_valid(context):
    if context.get('history_schema') != HISTORY_SCHEMA or context.get('history_confirmed') is not True or not context.get('history_id'):
        return False
    ids, records = context.get('rejected_operation_ids'), context.get('rejected_operations')
    if not isinstance(ids,list) or not all(isinstance(x,str) and x for x in ids) or len(ids) != len(set(ids)) or not isinstance(records,dict) or set(ids) != set(records):
        return False
    if not isinstance(context.get('faults'),dict):
        return False
    for op,events in records.items():
        if not isinstance(events,dict) or not events or any(not isinstance(r,dict) or r.get('operation_id')!=op or rid!='R-'+digest(r) or r.get('outcome') not in {'BLOCKED','INDETERMINATE'} for rid,r in events.items()):
            return False
    return all(isinstance(f,dict) and isinstance(f.get('origin'),dict) and isinstance(f['origin'].get('scope'),dict) and isinstance(f['origin'].get('revisions'),dict) and isinstance(f['origin'].get('cause_fault_ids'),list) and f.get('fault_id') == fid == 'F-'+digest(f['origin']) and f.get('status') in {'OPEN','RESOLVED'} for fid,f in context['faults'].items())


def scope(contract, guard, context):
    definition = next(g for g in contract['guards'] if g['id'] == guard)
    result=dict({k:context.get(k) for k in contract['fault_policy']['identity_fields']}, subject_kind=definition['fault_subject_kind'])
    if definition['fault_subject_kind']!='MATERIAL':
        # Declared non-applicability by guard type, never unknown == unknown.
        result['basis_id']=result['basis_revision']='NOT_APPLICABLE_BY_GUARD_SCOPE'
    return result


def open_faults(context, guard=None):
    return [f for f in context.get('faults',{}).values() if isinstance(f,dict) and f.get('status') == 'OPEN' and (guard is None or f['origin']['guard'] == guard)]


def latch(contract, context, guard, reason, record=None, kind='CONDITION', causes=(), truth='FALSE'):
    definition = next(g for g in contract['guards'] if g['id'] == guard)
    origin = dict(guard=guard,reason=reason,kind=kind,truth=truth,scope=scope(contract,guard,context),
                  operation_id=context.get('operation_id'),evidence_id=(record or {}).get('evidence_id'),evidence=deepcopy(record),
                  revisions={d:context.get('revisions',{}).get(d) for d in definition['evidence_domains']},cause_fault_ids=sorted(set(causes)))
    fid = 'F-'+digest(origin)
    context.setdefault('faults',{}).setdefault(fid,dict(fault_id=fid,origin=origin,status='OPEN',expected_revisions=deepcopy(origin['revisions']),revision_history=[],resolution_attempts=[],resolution=None))
    return fid


def _raw_value(contract, action, guard, context, record, phase):
    if not isinstance(record,dict) or not isinstance(record.get('value'),str) or record['value'] not in {'TRUE','FALSE','UNKNOWN'}:
        return 'UNKNOWN','MISSING_OR_INVALID_EVIDENCE'
    for key in contract['evidence_policy']['scope_fields']+['operation_id']:
        if not isinstance(context.get(key),str) or not context[key] or record.get(key) != context[key]:
            return 'UNKNOWN','SCOPE_MISMATCH:'+key
    if record.get('action') != action or record.get('phase') != phase:
        return 'UNKNOWN','WRONG_ACTION_OR_PHASE'
    if record.get('guard') != guard:
        return 'UNKNOWN','WRONG_GUARD_EVIDENCE'
    if not all(isinstance(record.get(k),str) and record[k] for k in ['evidence_id','method','source']):
        return 'UNKNOWN','MISSING_PROVENANCE'
    if not isinstance(record.get('revisions'),dict) or not isinstance(context.get('revisions'),dict):
        return 'UNKNOWN','MISSING_REVISIONS'
    definition = next(g for g in contract['guards'] if g['id'] == guard)
    for domain in definition['evidence_domains']:
        current,proven = context.get('revisions',{}).get(domain),record.get('revisions',{}).get(domain)
        if type(current) is not int or type(proven) is not int or current < 0 or proven != current:
            return 'UNKNOWN','STALE_SUBJECT:'+domain
    if record.get('valid_for_operation_interval') is not True:
        return 'UNKNOWN','INTERVAL_NOT_COVERED'
    return record['value'],'CURRENT_ASSUMED_RECORD'


def evidence_value(contract, action, guard, context, record, phase, ignore_fault=False):
    if guard == 'EVENT_FRESH' and context.get('operation_id') in context.get('rejected_operation_ids',[]):
        return 'FALSE','PERMANENTLY_REJECTED_OPERATION_ID'
    if not ignore_fault:
        faults = open_faults(context,guard)
        if guard == 'EVENT_FRESH':
            faults = [f for f in faults if f['origin']['operation_id'] == context.get('operation_id')]
        if faults:
            return ('FALSE' if any(f['origin']['truth'] == 'FALSE' for f in faults) else 'UNKNOWN'),'UNRESOLVED_ADDRESSED_FAULT'
    return _raw_value(contract,action,guard,context,record,phase)


def evaluate(contract, action, context, stage='COMMIT'):
    if stage not in {'ENTRY','COMMIT'}:
        raise ValueError('unsupported documentary stage')
    t=spec(contract,action);required=t['entry_guards'] if stage=='ENTRY' else t['required_guards']
    values,reasons,new_failures,blocking={},{},{},[]
    for guard in required:
        phase='COMPLETION' if guard in t['completion_guards'] else 'ENTRY';record=context.get('evidence',{}).get(guard)
        values[guard],reasons[guard]=evidence_value(contract,action,guard,context,record,phase)
        raw,_=_raw_value(contract,action,guard,context,record,phase)
        if raw=='FALSE':new_failures[guard]=deepcopy(record)
        blocking.extend(f['fault_id'] for f in open_faults(context,guard) if guard!='EVENT_FRESH' or f['origin']['operation_id']==context.get('operation_id'))
    history=history_valid(context);gates=list(values.values())+['TRUE' if history else 'UNKNOWN']
    if context.get('operation_id') in context.get('rejected_operation_ids',[]) or context.get('operation_id') in context.get('completed_operations',{}):gates.append('FALSE')
    state=context.get('state');allowed=state in t['from_states'] and context.get('mode') in contract['state_modes'].get(state,[])
    allowed=allowed and ('allowed_modes' not in t or context.get('mode') in t['allowed_modes'])
    allowed=allowed and (t.get('variant') not in {'A','B'} or context.get('variant')==t['variant'])
    outcome=conjunction(gates,allowed);assessment=context.get('material_assessment','UNCONFIRMED')
    if any(values.get(g) in {'FALSE','UNKNOWN'} for g in ['INVENTORY_KNOWN','RETAINED_STABLE','STARTUP_INVENTORY_PRESERVED','LEDGER_VALID']):assessment='UNCONFIRMED'
    next_state=t.get('to_state',state) if stage=='COMMIT' and outcome=='ALLOWED_ASSUMED' else state
    return dict(command_execution='COMPLETED_DOCUMENT_EVALUATION',permission_outcome=outcome,stage=stage,action=action,values=values,reasons=reasons,input_context_hash=digest(context),
                blocking_fault_ids=sorted(set(blocking)),new_failure_evidence=new_failures,history_confirmed=history,next_state=next_state,material_assessment=assessment,physical_permission=False)


def _reject(context, action, stage, outcome, reason):
    op=context.get('operation_id')
    if not isinstance(op,str) or not op:
        context['history_confirmed']=False;return
    item=dict(operation_id=op,action=action,stage=stage,outcome=outcome,reason=reason,scope={k:context.get(k) for k in ['scenario_id','variant','mode','subject_id','batch_id','cycle_epoch','basis_id','basis_revision']})
    rid='R-'+digest(item);context.setdefault('rejected_operations',{}).setdefault(op,{}).setdefault(rid,item)
    context['rejected_operation_ids']=sorted(set(context.get('rejected_operation_ids',[]))|set(context['rejected_operations']))


def propagate(contract, context, result):
    if result.get('input_context_hash') != digest(context):
        raise ValueError('evaluation belongs to another context; use atomic decide')
    out=deepcopy(context);out['material_assessment']=result['material_assessment']
    if result['permission_outcome']=='ALLOWED_ASSUMED':
        if result['stage']=='ENTRY':out.setdefault('authorized_entries',{})[out['operation_id']]=dict(action=result['action'])
        else:
            out['state']=result['next_state'];out.setdefault('completed_operations',{})[out['operation_id']]=dict(action=result['action'])
            for domain in spec(contract,result['action']).get('invalidates_on_commit',[]):out=change_subject(contract,out,domain)
        return out
    causes=set(result['blocking_fault_ids'])
    for guard,record in result['new_failure_evidence'].items():causes.add(latch(contract,out,guard,'CONFIRMED_CONDITION_FALSE',record))
    _reject(out,result['action'],result['stage'],result['permission_outcome'],'REQUEST_NOT_GRANTED')
    if result['action'] not in {r['id'] for r in contract['recovery_actions']}:
        summary=dict(evidence_id='decision-'+digest(result),action=result['action'],phase=result['stage'],outcome=result['permission_outcome'],input_context_hash=result['input_context_hash'])
        dep=latch(contract,out,'DEPENDENCY_VALID','UNRESOLVED_MANDATORY_STEP',summary,kind='DEPENDENCY',causes=causes,truth='FALSE' if result['permission_outcome']=='BLOCKED' else 'UNKNOWN')
        if dep not in out.setdefault('unresolved_dependencies',[]):out['unresolved_dependencies'].append(dep)
    if out['material_assessment']=='UNCONFIRMED':
        for guard in ['INVENTORY_KNOWN','COLUMN_CRITERION','PARTITION_DEFINED']:
            if guard in out.get('evidence',{}):out['evidence'][guard]['value']='UNKNOWN'
    return out


def decide(contract, action, context, stage='COMMIT'):
    result=evaluate(contract,action,context,stage)
    return propagate(contract,context,result),result


def change_subject(contract, context, *domains):
    out=deepcopy(context)
    for guard,record in context.get('evidence',{}).items():
        if not isinstance(record,dict):continue
        try:t=spec(contract,record.get('action'))
        except StopIteration:continue
        if guard not in t['required_guards']:continue
        phase='COMPLETION' if guard in t['completion_guards'] else 'ENTRY'
        value,_=_raw_value(contract,t['id'],guard,context,record,phase)
        if value=='FALSE':latch(contract,out,guard,'CONFIRMED_CONDITION_FALSE',record)
    for domain in domains:
        old=out['revisions'][domain];out['revisions'][domain]+=1
        for fault in open_faults(out):
            if scope(contract,fault['origin']['guard'],context)==fault['origin']['scope'] and fault['expected_revisions'].get(domain)==old:
                fault['expected_revisions'][domain]=old+1
                fault['revision_history'].append(dict(domain=domain,from_revision=old,to_revision=old+1))
    return out


def recover(contract, action, context, fault_id, record):
    """The fourth argument is a fault ID, never a guard-name lookup."""
    out,request=decide(contract,action,context,'ENTRY')
    if request['permission_outcome']!='ALLOWED_ASSUMED':return out,request['permission_outcome']
    t=spec(contract,action);fault=out.get('faults',{}).get(fault_id);value,reason='UNKNOWN','UNKNOWN_FAULT_ID'
    if isinstance(fault,dict) and fault.get('status')=='OPEN':
        guard=fault['origin']['guard']
        if guard not in t.get('may_reestablish',[])+t.get('may_acknowledge',[]):value,reason='FALSE','WRONG_RECOVERY_ACTION'
        elif any(out['faults'].get(parent,{}).get('status')!='RESOLVED' for parent in fault['origin']['cause_fault_ids']):value,reason='FALSE','UNRESOLVED_CAUSAL_FAULT'
        else:
            target=record.get('target_scope',{}) if isinstance(record,dict) else {};original=fault['origin']['scope']
            fields=contract['fault_policy']['identity_fields']+['subject_kind']
            complete=all(isinstance(original.get(k),str) and original[k] for k in fields) and all(type(v) is int and v>=0 for v in fault['origin']['revisions'].values())
            if not complete:reason='UNKNOWN_ORIGINAL_FAULT_ADDRESS'
            elif not isinstance(record,dict) or record.get('fault_id')!=fault_id or target!=original or scope(contract,guard,context)!=original:reason='WRONG_OR_UNKNOWN_TARGET_SCOPE'
            elif not isinstance(record.get('origin_revisions'),dict) or set(record['origin_revisions'])!=set(fault['origin']['revisions']) or any(type(record['origin_revisions'][d]) is not int or record['origin_revisions'][d]!=v for d,v in fault['origin']['revisions'].items()):reason='WRONG_OR_UNKNOWN_ORIGIN_REVISION'
            elif not isinstance(record.get('revisions'),dict) or any(type(record['revisions'].get(d)) is not int or record['revisions'][d]!=v or context.get('revisions',{}).get(d)!=v for d,v in fault['expected_revisions'].items()):reason='WRONG_OR_UNCONFIRMED_TARGET_REVISION'
            else:
                value,reason=_raw_value(contract,action,guard,context,record,'RECOVERY_RESULT')
                if guard=='EVENT_FRESH' and (record.get('resolution_kind')!='DENIED_REQUEST_ACKNOWLEDGED' or record.get('denied_operation_id')!=fault['origin']['operation_id'] or record.get('rejection_record_ids')!=sorted(out.get('rejected_operations',{}).get(fault['origin']['operation_id'],{}))):
                    value,reason='UNKNOWN','REJECTION_NOT_ADDRESSED'
        fault['resolution_attempts'].append(dict(operation_id=context.get('operation_id'),evidence_id=record.get('evidence_id') if isinstance(record,dict) else None,proof=deepcopy(record),value=value,reason=reason))
    if value!='TRUE':
        outcome='BLOCKED' if value=='FALSE' else 'INDETERMINATE';_reject(out,action,'RECOVERY_RESULT',outcome,reason);return out,outcome
    fault['status']='RESOLVED';fault['resolution']=deepcopy(record)
    out.setdefault('recovered_evidence',{})[fault_id]=deepcopy(record)
    out.setdefault('completed_operations',{})[out['operation_id']]=dict(action=action,fault_id=fault_id)
    return out,'ALLOWED_ASSUMED'


def record_fact(contract, context, observation, permission_outcome):
    out=deepcopy(context);facts=out.setdefault('pending_observations',[]);same=[f for f in facts if f.get('event_id')==observation.get('event_id')]
    if same and any(f!=observation for f in same):
        facts.append(deepcopy(observation));latch(contract,out,'EVENT_FRESH','CONFLICTING_OBSERVATION_ID',observation);latch(contract,out,'LEDGER_VALID','CONFLICTING_MATERIAL_IDENTITY',observation)
        status='RECORDED_CONFLICT_REQUIRES_RECONCILIATION'
    elif same:status='DUPLICATE_REFERENCE_NO_SECOND_ACCOUNTING_ENTRY'
    else:facts.append(deepcopy(observation));status='RECORDED_PENDING_RECONCILIATION'
    out['material_assessment']='UNCONFIRMED'
    if not same or status=='RECORDED_CONFLICT_REQUIRES_RECONCILIATION':out=change_subject(contract,out,'MATERIAL','FEED','EVIDENCE')
    for guard in ['INVENTORY_KNOWN','LEDGER_VALID','DEPENDENCY_VALID']:
        if guard in out.get('evidence',{}):out['evidence'][guard]['value']='UNKNOWN'
    if permission_outcome!='ALLOWED_ASSUMED':
        _reject(out,'OBSERVED_AFTER_UNGRANTED_REQUEST','OBSERVATION',permission_outcome,'FACT_DOES_NOT_GRANT_REQUEST')
        dep=latch(contract,out,'DEPENDENCY_VALID','OBSERVED_UNAUTHORIZED_EVENT',observation,kind='DEPENDENCY',causes=[f['fault_id'] for f in open_faults(out,'LEDGER_VALID')],truth='FALSE' if permission_outcome=='BLOCKED' else 'UNKNOWN')
        if dep not in out.setdefault('unresolved_dependencies',[]):out['unresolved_dependencies'].append(dep)
    return out,dict(observation_status=status,process_permission='NOT_GRANTED_BY_OBSERVATION',physical_permission=False)


def export_context(context):
    payload=deepcopy(context);return dict(schema=HISTORY_SCHEMA,payload=payload,sha256=digest(payload))


def restore_context(snapshot, expected_sha256=None):
    out=deepcopy(snapshot.get('payload',{}))
    trusted=snapshot.get('schema')==HISTORY_SCHEMA and isinstance(expected_sha256,str) and expected_sha256==snapshot.get('sha256')==digest(out)
    if not trusted or not history_valid(out):out['history_confirmed']=False
    out['history_restore_status']='CONFIRMED_HASH_ANCHOR' if trusted and history_valid(out) else 'UNCONFIRMED_HISTORY'
    return out
