"""Explicit synthetic scenes; none of these numbers are REV parameters."""
import copy
from fractions import Fraction as F
from engine import evaluate_phase, body, boundary, pair

COMMON=['punch','doser','inlet_gate','chamber_top','chamber_bottom','chamber_left','chamber_right','frame_mount']
EXTRAS={'A':['channel_top','channel_bottom','channel_left','channel_right','clamp'], 'B':['end_stop','lock']}

def box(lo,hi,delta=(0,0,0)): return {'lo':list(lo),'hi':list(hi),'delta':list(delta),'motion':'linear'}

def decide(collision,linked,geometry,broken=False,uncertain=False,input_status='SUPPORTED'):
    if collision=='COLLISION' or linked=='LINK_ABSENT' or geometry=='SHORT_STROKE' or broken or input_status=='INVALID_INPUT': return 'BLOCKED'
    if collision=='INDETERMINATE' or linked=='LINK_INDETERMINATE' or uncertain or input_status!='SUPPORTED': return 'INDETERMINATE'
    return 'ALLOWED'

def run(variant,outcome,config):
    product='product_'+variant; names=COMMON+EXTRAS[variant]+[product,'out_obstacle']
    bodies={'punch':box([-1,0,0],[0,1,1]),product:box([0,0,0],[1,1,1])}
    for i,name in enumerate(n for n in names if n not in ('punch',product,'out_obstacle')):
        bodies[name]=box([0,10+3*i,0],[1,11+3*i,1])
    if variant=='B':
        bodies['end_stop']=box([2,0,0],[3,1,1]);bodies['lock']=box([3,0,0],[4,1,1])
    bodies['out_obstacle']=box(['3/2',0,0],['7/4',1,1]) if outcome=='collision' else box([0,100,0],[1,101,1])
    baseline=copy.deepcopy(bodies); stages=[]; continuity=[]; events=[]; clock=0
    def stage(name,moves=None,required=False,unknown=False):
        nonlocal bodies,clock
        current=copy.deepcopy(bodies)
        for key,d in (moves or {}).items(): current[key]['delta']=list(d)
        if unknown: current[product]['motion']=None
        ids=sorted(current)
        contacts={}
        if product in ids:
            rule={'ordered':['punch',product], 'allowed_time':[clock,clock+1], 'patch_yz':config['contact_patch_yz'], 'direction':'either'}
            if required: rule['link_required']=True; rule['link_window']=[clock,clock+1]
            contacts['|'.join(sorted(['punch',product]))]=rule
        if variant=='B':
            contacts['|'.join(sorted(['end_stop','lock']))]={'ordered':['end_stop','lock'],'allowed_time':[clock,clock+1],'patch_yz':[[0,3],[0,1]],'direction':'either'}
        phase={'phase':name,'time':[clock,clock+1],'registry':ids,'bodies':current,'contacts':contacts}
        report=evaluate_phase(phase);stages.append({'input':phase,'output':report})
        if not unknown:
            for key,b in current.items():
                lo,hi,d=body(b)
                bodies[key]=box([str(lo[i]+d[i]) for i in range(3)],[str(hi[i]+d[i]) for i in range(3)])
        clock+=1
    if variant=='A':
        for name in ('A-READY','A-FILL','A-ISOLATE'): stage(name)
    else:
        for name in ('B-READY','B-FILL','B-PRESS','B-UNLOAD'): stage(name)
        stage('B-OPEN-LOCK',{'lock':(0,2,0)});stage('B-OPEN-STOP',{'end_stop':(0,2,0)})
    travel=config['short_travel'] if outcome=='short' else config['full_travel']
    moving='A-PRESS-OUT' if variant=='A' else 'B-EJECT'
    stage(moving,{'punch':(travel,0,0),product:(travel,0,0)},required=True,unknown=outcome=='unknown')
    all_rows=[p for stage_data in stages for p in stage_data['output']['pairs']]
    statuses=[segment['collision_status'] for p in all_rows for segment in p['segments']]
    collision='COLLISION' if 'COLLISION' in statuses else 'INDETERMINATE' if any(x in statuses for x in ('INDETERMINATE','INVALID_INPUT')) or any(p['input_status']!='SUPPORTED' for p in all_rows) else 'NO_COLLISION'
    linked=next(p['link'] for p in stages[-1]['output']['pairs'] if {p['body_a'],p['body_b']}=={'punch',product})
    rear=None if outcome=='unknown' else body(bodies[product])[0][0]
    geometry='INDETERMINATE' if rear is None or linked=='LINK_INDETERMINATE' else 'GEOMETRY_SUFFICIENT' if rear>=F(config['exit_boundary']) else 'SHORT_STROKE'
    prior_boundaries=[boundary(a['input'],b['input'],events) for a,b in zip(stages,stages[1:])]
    allowed=collision=='NO_COLLISION' and linked=='LINK_CONFIRMED' and geometry=='GEOMETRY_SUFFICIENT' and all(x['status']=='CONTINUOUS' for x in prior_boundaries)
    if allowed:
        events.append({'type':'REMOVE','id':product,'time':clock,'reason':'entire synthetic product beyond x boundary and in specified receiving zone', 'rear':str(rear),'boundary':str(config['exit_boundary']),'receiving_zone':'x>=2, 0<=y,z<=1','geometry':copy.deepcopy(bodies[product])})
        del bodies[product]
        stage('A-RETURN' if variant=='A' else 'B-RESET-PUNCH',{'punch':(-travel,0,0)})
        if variant=='B':
            stage('B-RESET-STOP',{'end_stop':(0,-2,0)});stage('B-RESET-LOCK',{'lock':(0,-2,0)})
    for before,after in zip(stages,stages[1:]):
        continuity.append(boundary(before['input'],after['input'],events))
    statuses=[seg['collision_status'] for st in stages for p in st['output']['pairs'] for seg in p['segments']]
    collision='COLLISION' if 'COLLISION' in statuses else 'INDETERMINATE' if any(x in statuses for x in ('INDETERMINATE','INVALID_INPUT')) or any(p['input_status']!='SUPPORTED' for st in stages for p in st['output']['pairs']) else 'NO_COLLISION'
    broken=any(c['status']=='DISCONTINUITY' for c in continuity)
    uncertain=any(c['status']=='INDETERMINATE' for c in continuity)
    restored=all(body(bodies[k])[:2]==body(baseline[k])[:2] for k in bodies)
    # C, W_in and G_out are query regions, never scene bodies.
    occupancy=[]
    for region,query in [('W_in',box([0,2,0],[1,3,1])),('G_out',box([5,0,0],[6,1,1]))]:
        for key,solid in bodies.items():
            rows=pair(query,solid,[0,1])['segments']
            if any(r['collision_status']!='CLEAR' for r in rows):occupancy.append(region+':'+key)
    closure=True
    if variant=='B':
        stoplo,stophi,_=body(bodies['end_stop']);locklo,lockhi,_=body(bodies['lock'])
        closure=(stoplo[0]==F(config['exit_boundary']) and stophi[0]==locklo[0] and stoplo[1:]==locklo[1:] and stophi[1:]==lockhi[1:])
    restored=restored and not occupancy and closure

    pair_inputs=[p['input_status'] for st in stages for p in st['output']['pairs']]
    input_status='INVALID_INPUT' if 'INVALID_INPUT' in pair_inputs else 'INDETERMINATE' if 'INDETERMINATE' in pair_inputs else 'SUPPORTED'
    transition=decide(collision,linked,geometry,broken,uncertain,input_status)
    ready='READY' if allowed and restored and transition=='ALLOWED' else 'BLOCKED' if transition=='BLOCKED' else 'INDETERMINATE'
    return {'variant':variant,'case':outcome,'input_status':input_status,'continuity_status':'DISCONTINUITY' if broken else 'INDETERMINATE' if uncertain else 'CONTINUOUS','geometry':geometry,'collision':collision,'link':linked,'transition':transition,'ready':ready,'stages':stages,'continuity':continuity,'events':events,'ready_region_occupancy':occupancy,'synthetic_stop_lock_geometry':closure,'physical':{'holding':'UNKNOWN','unloading':'UNKNOWN','ejection':'UNKNOWN','safety':'UNKNOWN'},'synthetic_assumptions':['ASSUMED_UNLOAD'] if variant=='B' else ['ASSUMED_HOLDING'], 'optional_absence':{'fragment_1':'absent by explicit synthetic fixture','residue_1':'absent by explicit synthetic fixture'},'limitations':['the declared synthetic scene is not REV','no force or granular material model']}
