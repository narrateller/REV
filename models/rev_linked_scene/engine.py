"""Exact event-partition checks for restricted synthetic AABB scenes only."""
from fractions import Fraction as F
from itertools import combinations


def q(x):
    if isinstance(x, bool) or not isinstance(x, (str, int)):
        raise ValueError('exact integer or rational string required')
    return F(x)


def body(b):
    if b is None or not isinstance(b, dict): raise KeyError('geometry or motion missing')
    if b.get('motion') is None: raise KeyError('motion missing')
    if b.get('motion') != 'linear': raise NotImplementedError('motion is not linear')
    if any(b.get(k) is None or len(b[k]) != 3 or None in b[k] for k in ('lo','hi','delta')):
        raise KeyError('incomplete AABB or trajectory')
    lo, hi, delta = ([q(x) for x in b[k]] for k in ('lo','hi','delta'))
    if any(a >= z for a,z in zip(lo,hi)): raise ValueError('invalid AABB extent')
    return lo,hi,delta


def pos(b,t):
    return ([b[0][i]+b[2][i]*t for i in range(3)], [b[1][i]+b[2][i]*t for i in range(3)])


def classify(a,b,t,contact_rule,absolute_t):
    al,ah=pos(a,t); bl,bh=pos(b,t)
    if any(ah[i]<bl[i] or bh[i]<al[i] for i in range(3)): return 'CLEAR'
    if all(ah[i]>bl[i] and bh[i]>al[i] for i in range(3)): return 'COLLISION'
    if contact_rule is None: return 'COLLISION'
    start,end=map(q,contact_rule['allowed_time'])
    if not start <= absolute_t <= end: return 'COLLISION'
    # Permitted interface: A +x face to B -x face; exact, positive yz patch.
    if ah[0]!=bl[0]: return 'COLLISION'
    patch=contact_rule['patch_yz']
    for i,extent in zip((1,2),patch):
        left,right=map(q,extent)
        contact_lo=max(al[i],bl[i]); contact_hi=min(ah[i],bh[i])
        # The actual contact, including patch edges, must be within the allowed patch.
        if not (left < right and left <= contact_lo < contact_hi <= right): return 'COLLISION'
    relative=a[2][0]-b[2][0]
    direction=contact_rule.get('direction')
    if direction=='nonseparating' and relative < 0: return 'COLLISION'
    if direction not in ('nonseparating','either'): raise KeyError('contact direction')
    return 'ALLOWED_CONTACT'


def pair(a,b,phase_time,rule=None,link_window=None,link_required=False):
    """Return exact point and open interval results; each root is its own boundary."""
    try:
        start,end=map(q,phase_time)
        if start>=end: raise ValueError('phase time must increase')
    except (TypeError,ValueError,ZeroDivisionError):
        return {'segments':[], 'link':'LINK_INDETERMINATE' if link_required or link_window is not None else 'NOT_REQUIRED','input_status':'INVALID_INPUT'}
    try:
        aa,bb=body(a),body(b)
        if rule and any(rule.get(k) is None for k in ('allowed_time','patch_yz','direction')): raise KeyError('contact rule incomplete')
        if rule:
            allowed_start,allowed_end=map(q,rule['allowed_time'])
            if allowed_start>allowed_end: raise ValueError('invalid allowed contact window')
            if len(rule['patch_yz'])!=2: raise ValueError('invalid contact patch')
            for bounds in rule['patch_yz']:
                lower,upper=map(q,bounds)
                if lower>=upper: raise ValueError('invalid contact patch extent')
        cuts={F(0),F(1)}
        # Every possible change of intersection or face coincidence is a root.
        for i in range(3):
            for x,v in ((aa[1][i]-bb[0][i],aa[2][i]-bb[2][i]),(bb[1][i]-aa[0][i],bb[2][i]-aa[2][i])):
                if v:
                    root=-x/v
                    if 0 <= root <= 1: cuts.add(root)
        if rule:
            for i,extent in zip((1,2),rule['patch_yz']):
                for bound in map(q,extent):
                    for face,vel in ((aa[0][i],aa[2][i]),(aa[1][i],aa[2][i]),(bb[0][i],bb[2][i]),(bb[1][i],bb[2][i])):
                        if vel:
                            root=(bound-face)/vel
                            if 0<=root<=1: cuts.add(root)
        for window in ([rule.get('allowed_time')] if rule else [])+([link_window] if link_window is not None else []):
            for t in map(q,window):
                u=(t-start)/(end-start)
                if 0 <= u <= 1: cuts.add(u)
        if link_window is not None:
            l,r=map(q,link_window)
            if not start<=l<=r<=end: raise ValueError('invalid required link window')
        cuts=sorted(cuts); regions=[]
        for i,t in enumerate(cuts):
            regions.append((t,t,'point',t))
            if i+1<len(cuts): regions.append((t,cuts[i+1],'open',(t+cuts[i+1])/2))
        rows=[]
        for lo,hi,kind,t in regions:
            absolute=start+(end-start)*t
            status=classify(aa,bb,t,rule,absolute)
            x,y=start+(end-start)*lo,start+(end-start)*hi
            rows.append({'from':str(x),'to':str(y),'interval':kind,'collision_status':status})
        if link_window is None: link='LINK_INDETERMINATE' if link_required else 'NOT_REQUIRED'
        else:
            l,r=map(q,link_window); relevant=[row for row in rows if (row['interval']=='point' and l<=q(row['from'])<=r) or (row['interval']=='open' and max(l,q(row['from'])) < min(r,q(row['to'])))]
            link='LINK_CONFIRMED' if relevant and all(x['collision_status']=='ALLOWED_CONTACT' for x in relevant) else 'LINK_ABSENT'
        return {'segments':rows,'link':link,'link_basis':'explicit continuous interval' if link_window is not None else 'required window unknown' if link_required else 'not required for this pair', 'input_status':'SUPPORTED'}
    except (KeyError,NotImplementedError) as exc:
        return {'segments':[{'from':str(start),'to':str(end),'interval':'closed','collision_status':'INDETERMINATE','reason':str(exc)}], 'link':'LINK_INDETERMINATE' if link_required or link_window is not None else 'NOT_REQUIRED','input_status':'INDETERMINATE'}
    except (TypeError,ValueError,ZeroDivisionError) as exc:
        return {'segments':[{'from':str(start),'to':str(end),'interval':'closed','collision_status':'INVALID_INPUT','reason':str(exc)}], 'link':'LINK_INDETERMINATE' if link_required or link_window is not None else 'NOT_REQUIRED','input_status':'INVALID_INPUT'}


def evaluate_phase(scene):
    ids=sorted(scene['registry']); results=[]
    if len(ids)!=len(set(ids)): raise ValueError('duplicate scene ID')
    for a,b in combinations(ids,2):
        rule=scene.get('contacts',{}).get(a+'|'+b)
        first,second=(rule['ordered'] if rule else (a,b))
        result=pair(scene['bodies'].get(first),scene['bodies'].get(second),scene['time'],rule,rule.get('link_window') if rule else None,rule.get('link_required',False) if rule else False)
        results.append({'body_a':a,'body_b':b,'presence_interval':scene['time'],'category':'CONTACT' if rule else 'CHECK',**result})
    return {'phase':scene['phase'],'time':scene['time'],'declared_bodies':ids,'expected_pairs':len(ids)*(len(ids)-1)//2,'pairs':results}


def combine_link(pieces,window):
    """Conservatively combine separately assessed contiguous time pieces."""
    try:
        l,r=map(q,window)
        if l>r: raise ValueError('invalid link window')
        spans=sorted((q(piece['time'][0]),q(piece['time'][1]),piece['result']) for piece in pieces)
        cursor=l; absence=False; unknown=False; seen=False
        for start,end,result in spans:
            if end < l or start > r: continue
            seen=True
            if result.get('input_status')!='SUPPORTED' or not result.get('segments'): unknown=True
            if start > cursor: unknown=True
            cursor=max(cursor,min(end,r))
            for row in result['segments']:
                lo,hi=q(row['from']),q(row['to'])
                relevant=(row['interval']=='point' and l<=lo<=r) or (row['interval']=='open' and max(l,lo)<min(r,hi)) or (row['interval']=='closed' and max(l,lo)<=min(r,hi))
                if relevant and row['collision_status']=='CLEAR': absence=True
                if relevant and row['collision_status'] in ('INVALID_INPUT','INDETERMINATE'): unknown=True
                if relevant and row['collision_status']=='COLLISION': absence=True
        if not seen or cursor<r: unknown=True
        return 'LINK_ABSENT' if absence else 'LINK_INDETERMINATE' if unknown else 'LINK_CONFIRMED'
    except (KeyError,ValueError,TypeError,ZeroDivisionError): return 'LINK_INDETERMINATE'


def boundary(previous,following,events):
    """Validate every local event and preserve independent continuity evidence.

    CREATE and SPLIT remain unsupported when consistent; they cannot cover an
    unrelated disappearance. Callers pass only events for this boundary.
    """
    old_list=previous.get('registry',[]); new_list=following.get('registry',[])
    old=set(old_list); new=set(new_list); gone=sorted(old-new); added=sorted(new-old)
    bad=[]; unknown=[]; invalid=[]; event_results=[]; problems=[]; uncertain=[]
    if len(old)!=len(old_list) or len(new)!=len(new_list): problems.append('duplicate registry ID')
    try:
        p0,p1=map(q,previous['time']); n0,n1=map(q,following['time'])
        if p0>=p1 or n0>=n1: raise ValueError('phase interval must increase')
        time_ok=p1==n0
    except (KeyError,TypeError,ValueError,ZeroDivisionError):
        p1=None; time_ok=None; problems.append('invalid phase time')
    for key in sorted(old&new):
        try:
            lo,hi,d=body(previous['bodies'].get(key)); nlo,nhi,_=body(following['bodies'].get(key))
            if any(lo[i]+d[i]!=nlo[i] or hi[i]+d[i]!=nhi[i] for i in range(3)):bad.append(key)
        except (KeyError,NotImplementedError): unknown.append(key)
        except (ValueError,TypeError,ZeroDivisionError): invalid.append(key)
    if not isinstance(events,list): events=[];problems.append('events must be a list')
    seen=set(); removed_covered=set(); added_covered=set(); split_unmapped=False
    for index,event in enumerate(events):
        info={'index':index,'type':None,'id':None,'status':'INVALID_INPUT','reason':None}
        if not isinstance(event,dict):
            info['reason']='event must be an object'; problems.append(info['reason']);event_results.append(info);continue
        kind=event.get('type');key=event.get('id');info.update(type=kind,id=key)
        if kind not in ('CREATE','SPLIT','REMOVE') or not isinstance(key,str) or not key:
            info['reason']='invalid event type or ID'; problems.append(info['reason']);event_results.append(info);continue
        if key in seen:
            info['reason']='duplicate or conflicting event for ID'; problems.append(info['reason']);event_results.append(info);continue
        seen.add(key)
        try:
            if p1 is None or q(event['time'])!=p1: raise ValueError('event time is not this boundary')
        except (KeyError,TypeError,ValueError,ZeroDivisionError):
            info['reason']='invalid or mismatched event time'; problems.append(info['reason']);event_results.append(info);continue
        if kind=='CREATE':
            if key not in added:
                info['reason']='CREATE ID absent from added registry';problems.append(info['reason'])
            else:
                added_covered.add(key);info.update(status='INDETERMINATE',reason='CREATE not supported');uncertain.append('CREATE '+key)
        elif kind=='SPLIT':
            if key not in gone or not added:
                info['reason']='SPLIT source must disappear and targets must be added';problems.append(info['reason'])
            else:
                targets=event.get('targets')
                if targets is None:
                    removed_covered.add(key);split_unmapped=True;info.update(status='INDETERMINATE',reason='SPLIT targets and geometry unverified');uncertain.append('SPLIT '+key)
                elif not isinstance(targets,list) or not targets or any(not isinstance(x,str) for x in targets) or len(targets)!=len(set(targets)) or not set(targets).issubset(added) or added_covered.intersection(targets):
                    info['reason']='SPLIT targets inconsistent with registry';problems.append(info['reason'])
                else:
                    removed_covered.add(key);added_covered.update(targets);info.update(status='INDETERMINATE',reason='SPLIT geometry not supported');uncertain.append('SPLIT '+key)
        else:
            if key not in gone:
                info['reason']='REMOVE ID absent from removed registry';problems.append(info['reason'])
            else:
                try:
                    lo,hi,d=body(previous['bodies'][key]); boundary_x=q(event['boundary'])
                    expected=[lo[i]+d[i] for i in range(3)];expected_hi=[hi[i]+d[i] for i in range(3)]
                    event_lo,event_hi,_=body(event['geometry'])
                    if expected!=event_lo or expected_hi!=event_hi or expected[0]<boundary_x or expected[1]<0 or expected_hi[1]>1 or expected[2]<0 or expected_hi[2]>1: raise ValueError('REMOVE geometry or receiving region invalid')
                    removed_covered.add(key);info.update(status='VALID',reason='synthetic removal geometry verified')
                except (KeyError,NotImplementedError):
                    removed_covered.add(key);info.update(status='INDETERMINATE',reason='REMOVE data missing or unsupported');uncertain.append('REMOVE '+key)
                except (ValueError,TypeError,ZeroDivisionError):
                    info['reason']='invalid REMOVE geometry or boundary';problems.append(info['reason'])
        event_results.append(info)
    unexplained_removed=sorted(set(gone)-removed_covered)
    unexplained_added=sorted(set(added)-added_covered)
    if unexplained_added and split_unmapped:
        uncertain.append('SPLIT target mapping unknown'); unexplained_added=[]
    if unexplained_added: problems.append('added IDs lack CREATE or SPLIT')
    discontinuity=bool(bad or time_ok is False or unexplained_removed)
    if unexplained_removed: problems.append('removed IDs lack valid event')
    has_invalid=bool(problems or invalid)
    has_unknown=bool(unknown or uncertain)
    lifecycle_status='INVALID' if problems else 'INDETERMINATE' if uncertain else 'VALID'
    status='INVALID_INPUT' if time_ok is None else 'DISCONTINUITY' if discontinuity else 'INVALID_INPUT' if has_invalid else 'INDETERMINATE' if has_unknown else 'CONTINUOUS'
    return {'from':previous['phase'],'to':following['phase'],'time_contiguous':time_ok,'mismatches':bad,
            'unknown':unknown,'invalid':invalid,'removed':gone,'added':added,
            'unexplained_removed':unexplained_removed,'unexplained_added':unexplained_added,
            'event_results':event_results,'event_errors':problems,'event_uncertainties':uncertain,
            'lifecycle_valid':lifecycle_status=='VALID','lifecycle_status':lifecycle_status,'status':status}
