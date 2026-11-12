"""Strict, fail-closed lifecycle for the limited translational research path.

Only REMOVE is implemented. Unsupported events are audited, never applied.
Event metadata are assertions, not proof of exit or receipt.
"""
import copy
from collections import Counter
from fractions import Fraction


def q(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('exact integer or rational string required')
    return Fraction(value)


def apply_boundary_events(before, proposed_after, time, events, conditions=None):
    """Return effective state and evidence; never remove on failed/unknown proof.

    before is the advanced state at this boundary. conditions is independently
    computed path evidence, not supplied by the event itself. Consistent CREATE
    and SPLIT remain unsupported. Unexplained registry changes are defects.
    """
    boundary=q(time); conditions=conditions or {}; rows=[]
    counts=Counter()
    for e in events:
        if isinstance(e,dict):
            for name in [e.get('id')]+(e.get('children',[]) if isinstance(e.get('children'),list) else []):
                if isinstance(name,str):counts[name]+=1
    removed=set(before)-set(proposed_after);created=set(proposed_after)-set(before)
    allowed=set();unknown_removed=set();unknown_created=set()
    for index,e in enumerate(events):
        row={'index':index,'event':copy.deepcopy(e),'status':'INVALID_INPUT','applied':False,'reasons':[]}
        rows.append(row)
        try:
            if not isinstance(e,dict):raise ValueError('event must be an object')
            kind=e.get('type');name=e.get('id')
            if not isinstance(kind,str) or not kind:raise ValueError('event type missing')
            if not isinstance(name,str) or not name:raise ValueError('event ID missing')
            if q(e.get('time'))!=boundary:raise ValueError('event is not at this boundary')
            if counts[name]>1:raise ValueError('duplicate/conflicting event claim for ID')
            if kind=='CREATE':
                if name not in created:raise ValueError('CREATE disagrees with registry delta')
                unknown_created.add(name);row.update(status='INDETERMINATE',reasons=['CREATE unsupported; no body created'])
                continue
            if kind=='SPLIT':
                children=e.get('children')
                if not isinstance(children,list) or not children or any(not isinstance(c,str) or not c for c in children):raise ValueError('SPLIT children missing/invalid')
                if len(set(children))!=len(children) or name in children or any(counts[c]>1 for c in children):raise ValueError('duplicate/conflicting SPLIT IDs')
                if name not in removed or not set(children).issubset(created):raise ValueError('SPLIT disagrees with registry delta')
                unknown_removed.add(name);unknown_created.update(children)
                row.update(status='INDETERMINATE',reasons=['SPLIT unsupported; source retained, children not created'])
                continue
            if kind!='REMOVE':
                if name not in before and name not in proposed_after:raise ValueError('unsupported event references unknown registry ID')
                row.update(status='INDETERMINATE',reasons=['unsupported event type; no effect applied'])
                continue
            if name not in removed:raise ValueError('REMOVE disagrees with registry delta')
            declared=None if e.get('exit_boundary') is None else q(e['exit_boundary'])
            claimed_rear=None if e.get('final_rear') is None else q(e['final_rear'])
            context=conditions.get(name,{})
            exit_x=None if context.get('exit_boundary') is None else q(context['exit_boundary'])
            b=before[name]
            # Unknown geometry/motion cannot justify disappearance.
            if b.get('motion')!='linear' or any(b.get(k) is None or len(b[k])!=3 or None in b[k] for k in ('lo','hi','delta')):
                unknown_removed.add(name);row.update(status='INDETERMINATE',reasons=['exit geometry/motion unknown']);continue
            lo,hi,delta=([q(x) for x in b[k]] for k in ('lo','hi','delta'))
            if any(a>=z for a,z in zip(lo,hi)):raise ValueError('invalid exit geometry')
            if any(delta):raise ValueError('boundary state must be advanced')
            if claimed_rear is not None and claimed_rear!=lo[0]:raise ValueError('claimed rear disagrees with actual geometry')
            if exit_x is not None and declared is not None and exit_x!=declared:raise ValueError('claimed exit differs from trusted path condition')
            limit=exit_x if exit_x is not None else declared
            row['proof']={'actual_rear':str(lo[0]),'exit_boundary':str(limit) if limit is not None else None,'scope':'limited path only'}
            defects=[];unknown=[]
            if limit is not None and lo[0]<limit:defects.append('premature REMOVE: product has not fully exited')
            if exit_x is None:unknown.append('trusted exit boundary missing')
            receipt=context.get('receiving_yz')
            if receipt is None:unknown.append('conditional receiving envelope missing')
            else:
                if len(receipt)!=2 or any(len(axis)!=2 for axis in receipt):raise ValueError('invalid receiving envelope')
                for axis,extent in zip((1,2),receipt):
                    low,high=map(q,extent)
                    if low>=high:raise ValueError('invalid receiving extent')
                    if lo[axis]<low or hi[axis]>high:defects.append('product outside conditional receiving envelope')
            if context.get('required_link')=='LINK_ABSENT':defects.append('required link absent')
            elif context.get('required_link')!='LINK_CONFIRMED':unknown.append('required link not confirmed')
            if context.get('path_collision')=='COLLISION':defects.append('proven path collision')
            elif context.get('path_collision')!='NO_COLLISION':unknown.append('path clearance not confirmed')
            row['blocking_defects']=defects;row['unknown']=unknown
            if defects:row.update(status='BLOCKED',reasons=defects+unknown)
            elif unknown:unknown_removed.add(name);row.update(status='INDETERMINATE',reasons=unknown)
            else:allowed.add(name);row.update(status='VALIDATED_REMOVE',applied=True)
        except (KeyError,TypeError,ValueError,ZeroDivisionError) as exc:row['reasons'].append(str(exc))
    registry_defects=[]
    if removed-allowed-unknown_removed:registry_defects.append({'unjustified_disappearance':sorted(removed-allowed-unknown_removed)})
    if created-unknown_created:registry_defects.append({'unjustified_creation':sorted(created-unknown_created)})
    states=[r['status'] for r in rows]
    status='INVALID_INPUT' if 'INVALID_INPUT' in states else 'BLOCKED' if registry_defects or 'BLOCKED' in states else 'INDETERMINATE' if 'INDETERMINATE' in states else 'VALID'
    # Existing states may advance, but failed/unsupported removals retain bodies.
    effective={name:copy.deepcopy(proposed_after.get(name,b)) for name,b in before.items() if name not in allowed}
    return effective,{'status':status,'events':rows,'registry_defects':registry_defects,'retained_ids':sorted(removed-allowed),'effective_next_registry':sorted(effective)}
