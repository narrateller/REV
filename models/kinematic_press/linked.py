"""Synthetic linked-ejection scene. No values in this module describe REV."""
import copy
import itertools
from fractions import Fraction as F
import model

SCENE=('punch','product','feeder','gate','channel_wall','guide_wall','frame_wall','output_obstacle','stop','lock')

def contact(punch, product, patch=((0,1),(0,1))):
    """Exact interface x+: coincidence + positive specified common yz patch, no interpenetration."""
    try:
        p0,p1,pd=model.box(punch); b0,b1,bd=model.box(product)
        if not isinstance(patch,(list,tuple)) or len(patch)!=2: raise KeyError('contact patch')
        bounds=[tuple(model.q(x) for x in pair) for pair in patch]
        if any(len(pair)!=2 or pair[0]>=pair[1] for pair in bounds): raise ValueError('invalid patch')
        if p1[0]!=b0[0] or pd!=bd:
            return {'status':'BLOCKED','reason':'face coincidence and synchronized translation violated'}
        for axis,(lo,hi) in zip((1,2),bounds):
            if not (p0[axis] <= lo < hi <= p1[axis] and b0[axis] <= lo < hi <= b1[axis]):
                return {'status':'BLOCKED','reason':'contact patch is not contained in both faces'}
        return {'status':'VALID','evidence':'coincident x faces and common positive yz patch over full interval; identical translation', 'patch_yz':[[str(x) for x in a] for a in bounds]}
    except (KeyError,ValueError,TypeError,ZeroDivisionError,IndexError) as exc:
        return {'status':'INDETERMINATE','reason':str(exc)}

def matrix(variant,phase,bodies,scene=SCENE,patch=((0,1),(0,1)),time=(0,1)):
    rows=[]
    for a,b in itertools.combinations(scene,2):
        if {a,b}=={'punch','product'}:
            result=contact(bodies.get('punch'),bodies.get('product'),patch)
            rows.append({'pair':[a,b],'classification':'CONTACT_INTERFACE','interface':result})
        elif variant=='B' and {a,b}=={'stop','lock'}:
            try:
                stop=model.box(bodies.get('stop')); lock=model.box(bodies.get('lock'))
                valid=stop[1][0]==lock[0][0] and stop[2][0]==lock[2][0]
                interface={'status':'VALID' if valid else 'BLOCKED','evidence':'opposed x faces remain coincident; no x penetration; yz engagement varies with position'}
            except (KeyError,ValueError,TypeError): interface={'status':'INDETERMINATE','reason':'stop/lock interface geometry missing'}
            rows.append({'pair':[a,b],'classification':'CONTACT_INTERFACE','interface':interface})
        else:
            case={'id':phase+':'+a+'/'+b,'variant':variant,'phase':phase,'names':[a,b],
                  'motion_type':'linear','units':{'length':'m','time':'s'},'contact':'touch_is_collision',
                  'time':list(time),'bodies':[bodies.get(a),bodies.get(b)]}
            r=model.check(case)
            rows.append({'pair':[a,b],'classification':'CHECK','result':r})
    collisions=[r for r in rows if r['classification']=='CHECK' and r['result']['collision_status']=='COLLISION']
    invalid=[r for r in rows if (r['classification']=='CHECK' and r['result']['collision_status']=='INVALID_INPUT') or (r['classification']=='CONTACT_INTERFACE' and r['interface']['status']=='BLOCKED')]
    unknown=[r for r in rows if (r['classification']=='CHECK' and r['result']['collision_status']=='INDETERMINATE') or (r['classification']=='CONTACT_INTERFACE' and r['interface']['status']=='INDETERMINATE')]
    return {'scene':list(scene),'pairs':rows,'collision_status':'COLLISION' if collisions else 'INDETERMINATE' if unknown or invalid else 'NO_COLLISION',
            'complete':not unknown and not invalid,'interface_invalid':bool(invalid),'unknown_count':len(unknown),'collisions':[r['pair'] for r in collisions]}

def make_box(x0,x1,y0,y1,z0=0,z1=1,delta=(0,0,0)):
    return {'min':[x0,y0,z0],'max':[x1,y1,z1],'delta':list(delta)}

def initial():
    return {'punch':make_box(-1,0,0,1),'product':make_box(0,1,0,1),
            'feeder':make_box(0,1,4,5),'gate':make_box(0,1,7,8),
            'channel_wall':make_box(-2,4,-2,-1),'guide_wall':make_box(-2,4,-4,-3),
            'frame_wall':make_box(-2,4,-6,-5),'output_obstacle':make_box(0,1,20,21),
            'stop':make_box(0,1,12,13),'lock':make_box(0,1,16,17)}

def advance(bodies):
    out=copy.deepcopy(bodies)
    for body in out.values():
        lo,hi,d=model.box(body)
        body['min']=[str(lo[i]+d[i]) for i in range(3)]; body['max']=[str(hi[i]+d[i]) for i in range(3)];body['delta']=[0,0,0]
    return out

def run(variant,outcome):
    if variant not in ('A','B') or outcome not in ('sufficient','short','collision','unknown'):
        raise ValueError('unsupported synthetic scenario')
    bodies=initial()
    if variant=='B':
        bodies['stop']=make_box(2,3,0,1); bodies['lock']=make_box(3,4,0,1)
    baseline=copy.deepcopy(bodies); stages=[]; t=0; product_removed=False
    guards={'unloading_confirmed':'SYNTHETIC_ASSUMPTION','column_retention':'SYNTHETIC_ASSUMPTION'}
    def stage(name,movements,missing_product=False):
        nonlocal bodies,t
        stage_bodies=copy.deepcopy(bodies)
        for name_,delta in movements.items(): stage_bodies[name_]['delta']=list(delta)
        if missing_product: stage_bodies['product']['delta']=None
        declared_scene=tuple(name for name in SCENE if not (product_removed and name=='product'))
        p=matrix(variant,name,stage_bodies,declared_scene,time=(t,t+1))
        stages.append({'phase':name,'time':[t,t+1],'bodies':stage_bodies,'matrix':p})
        if not missing_product: bodies=advance(stage_bodies)
        t+=1
        return p
    if variant=='B':
        stage('B-UNLOAD',{}); stage('B-OPEN',{'lock':(0,2,0)});stage('B-OPEN',{'stop':(0,2,0)})
    if outcome=='collision': bodies['output_obstacle']=make_box('3/2','7/4',0,1)
    before=copy.deepcopy(bodies); travel=1 if outcome=='short' else 2
    phase='A-PRESS' if variant=='A' else 'B-EJECT'
    movement={'punch':(travel,0,0),'product':(travel,0,0)}
    mat=stage(phase,movement,missing_product=(outcome=='unknown'))
    interface=contact(stages[-1]['bodies']['punch'],stages[-1]['bodies']['product'])
    if interface['status']=='INDETERMINATE': ejection='INDETERMINATE'; rear=None
    elif interface['status']!='VALID': ejection='BLOCKED';rear=None
    else:
        lo,_,d=model.box(stages[-1]['bodies']['product']); rear=lo[0]+d[0]
        ejection='SUFFICIENT_STROKE' if rear>=2 else 'INSUFFICIENT_STROKE'
    prior_blocked=any(x['matrix']['collision_status']=='COLLISION' or x['matrix']['interface_invalid'] for x in stages)
    prior_unknown=any(not x['matrix']['complete'] for x in stages)
    eligible=ejection=='SUFFICIENT_STROKE' and not prior_blocked and not prior_unknown
    lifecycle={'event':'NOT_REMOVED','reason':'full unobstructed linked ejection is not established'}
    readiness={'status':'BLOCKED' if outcome in ('short','collision') else 'INDETERMINATE','reason':'product remains or linked ejection unknown'}
    continuity=[]
    if eligible:
        removed=copy.deepcopy(bodies['product']); del bodies['product']; product_removed=True
        lifecycle={'event':'REMOVE_AFTER_CONFIRMED_SYNTHETIC_EJECTION','removed_body':removed,'time':t}
        stage('A-RETURN' if variant=='A' else 'B-RESET',{'punch':(-travel,0,0)})
        if variant=='B': stage('B-RESET',{'stop':(0,-2,0)});stage('B-RESET',{'lock':(0,-2,0)})
        # Actual return of every retained body to the starting READY geometry.
        mismatches=[]
        for name,b in bodies.items():
            current=model.box(b); expected=model.box(baseline[name])
            if current[:2]!=expected[:2]: mismatches.append(name)
        bad_return=[row['phase'] for row in stages if row['matrix']['collision_status']!='NO_COLLISION' or not row['matrix']['complete']]
        # Explicit free loading and output query volumes, not solids.
        zones=[]
        for zone_name,zone in [('output',make_box(5,6,0,1)),('loading',make_box(0,1,2,3))]:
            for name,b in bodies.items():
                r=model.check({'id':'ready-zone','variant':variant,'phase':'A-READY' if variant=='A' else 'B-READY','motion_type':'linear','units':{'length':'m','time':'s'},'contact':'touch_is_collision','time':[0,1],'bodies':[zone,b]})
                if r['collision_status']!='NO_COLLISION': zones.append(zone_name+':'+name)
        # Independent synthetic READY specification, never derived from the last phase.
        ready_spec={'punch':([-1,0,0],[0,1,1]),'feeder':([0,4,0],[1,5,1]),'gate':([0,7,0],[1,8,1])}
        ready_mismatches=[]
        for name,(want_lo,want_hi) in ready_spec.items():
            lo,hi,delta=model.box(bodies[name])
            if lo!=list(map(F,want_lo)) or hi!=list(map(F,want_hi)) or any(delta): ready_mismatches.append(name)
        closure=True
        if variant=='B':
            st=model.box(bodies['stop']); lk=model.box(bodies['lock'])
            closure=(st[0][0]==2 and st[0][1]<=0 and st[1][1]>=1 and st[0][2]<=0 and st[1][2]>=1 and st[1][0]==lk[0][0] and st[0][1:]==lk[0][1:] and st[1][1:]==lk[1][1:])
        readiness={'status':'READY' if not mismatches and not ready_mismatches and not bad_return and not zones and closure else 'BLOCKED','position_mismatches':mismatches,'independent_ready_mismatches':ready_mismatches,'independent_ready_spec':ready_spec,'collision_or_unknown_stages':bad_return,'occupied_zones':zones,'punch_feeder_gate_restored':not any(x in mismatches for x in ('punch','feeder','gate')),'stop_lock_restored_and_geometrically_engaged':closure,'column_condition':'synthetic empty after verified removal; physical holding UNKNOWN','lock_capacity':'UNKNOWN'}
    for i in range(1,len(stages)):
        prev=stages[i-1]; nxt=stages[i]; old=advance(prev['bodies'])
        removed_here=set(old)-set(nxt['bodies']); permitted=removed_here=={'product'} and lifecycle['event'].startswith('REMOVE_') and prev['time'][1]==lifecycle['time']
        bad=[]
        unknown=[]
        for name in set(old)&set(nxt['bodies']):
            try:
                a=model.box(old[name]);b=model.box(nxt['bodies'][name])
                if a[:2]!=b[:2]: bad.append(name)
            except (KeyError,ValueError,TypeError): unknown.append(name)
        continuity.append({'from':prev['phase'],'to':nxt['phase'],'time_contiguous':prev['time'][1]==nxt['time'][0], 'mismatches':bad, 'unknown':unknown, 'removed':sorted(removed_here),'lifecycle_valid':not removed_here or permitted})
    contact_interval=None
    for row in mat['pairs']:
        if set(row['pair'])=={'product','output_obstacle'} and row.get('result',{}).get('collision_status')=='COLLISION':contact_interval=row['result']['evidence']['contact_interval_normalized']
    return {'id':'SYN-LINKED-EJECTION','variant':variant,'outcome':outcome,'assumptions':guards,'initial_scene':baseline,'ejection_start':before,'contact':interface,'ejection_status':ejection,'product_final_rear':str(rear) if rear is not None else None,
            'collision_status':mat['collision_status'],'collision_interval_product_obstacle':contact_interval,'transition':'ALLOWED' if eligible else 'BLOCKED' if prior_blocked or ejection in ('BLOCKED','INSUFFICIENT_STROKE') else 'INDETERMINATE','ready':readiness,'lifecycle':lifecycle,'continuity':continuity,'a_out':'SAME_INTERVAL_AS_A_PRESS' if variant=='A' else 'NOT_APPLICABLE','stages':stages}
