#!/usr/bin/env python3
"""Synthetic-only continuous collision checking for linearly translated AABBs."""
import argparse
import copy
import itertools
import hashlib
import json
import sys
from fractions import Fraction as F
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PHASES = {'A': ['A-READY','A-FILL','A-ISOLATE','A-PRESS','A-RETURN','A-OUT'],
          'B': ['B-READY','B-FILL','B-PRESS','B-UNLOAD','B-OPEN','B-EJECT','B-RESET']}

def q(x):
    if isinstance(x, bool) or not isinstance(x, (int, str)):
        raise ValueError('coordinates must be exact integer or rational strings')
    return F(x)

def box(b):
    if not isinstance(b, dict) or any(b.get(k) is None for k in ('min','max','delta')):
        raise KeyError('body min/max/delta including z and motion')
    if any(not isinstance(b[k], list) or len(b[k]) != 3 or None in b[k] for k in ('min','max','delta')):
        raise KeyError('three explicit coordinates for min/max/delta')
    lo, hi, d = ([q(x) for x in b[k]] for k in ('min','max','delta'))
    if any(a >= z for a,z in zip(lo,hi)):
        raise ValueError('body must have strictly positive extent')
    return lo, hi, d

def interval(a,b):
    # a+b*t >= 0 on [0,1], closed, exact arithmetic
    if b == 0:
        return (F(0),F(1)) if a >= 0 else None
    k = -a/b
    if b > 0: return (max(F(0),k),F(1)) if k <= 1 else None
    return (F(0),min(F(1),k)) if k >= 0 else None

def overlap_time(a,b, axes=range(3)):
    low, high = F(0), F(1)
    for i in axes:
        for c,v in ((b[1][i]-a[0][i],b[2][i]-a[2][i]),
                    (a[1][i]-b[0][i],a[2][i]-b[2][i])):
            cut = interval(c,v)
            if cut is None: return None
            low,high = max(low,cut[0]),min(high,cut[1])
            if low > high: return None
    return low,high

def path_cross(a,b):
    # Segment intersections of centre paths in XY; time parameters independent.
    p=[(a[0][i]+a[1][i])/2 for i in range(2)]
    r=a[2][:2]; v=[(b[0][i]+b[1][i])/2 for i in range(2)]; s=b[2][:2]
    cross=lambda x,y:x[0]*y[1]-x[1]*y[0]
    diff=[v[i]-p[i] for i in range(2)]; den=cross(r,s)
    if den:
        t,u=cross(diff,s)/den,cross(diff,r)/den
        return 0 <= t <= 1 and 0 <= u <= 1
    # Parallel/collinear diagnostics deliberately conservative when ambiguous.
    return None

def check(case):
    result={'id':case.get('id'), 'variant':case.get('variant'), 'phase':case.get('phase'),
            'bodies':case.get('names'), 'interval':case.get('time'),
            'collision_status':'INDETERMINATE','ejection_status':'INDETERMINATE',
            'missing':[], 'projection_overlap':None,'trajectory_intersection_xy':None,
            'scope':'axis-aligned boxes, linear translation; touching is collision',
            'method':'exact rational intersection of six linear inequalities over entire interval'}
    try:
        if case.get('variant') not in PHASES or case.get('phase') not in PHASES[case['variant']]:
            raise ValueError('unknown variant or phase')
        if case.get('motion_type') != 'linear': raise KeyError('explicit supported linear synchronized motion')
        if case.get('units') != {'length':'m','time':'s'} or case.get('contact') != 'touch_is_collision':
            raise KeyError('explicit units and contact policy')
        time=case.get('time')
        if time is None or len(time)!=2 or None in time: raise KeyError('time interval')
        if q(time[0]) >= q(time[1]): raise ValueError('time interval must increase')
        if case.get('bodies') is None: raise KeyError('explicit bodies and trajectories')
        a,b=map(box,case['bodies'])
        hit=overlap_time(a,b)
        projection=overlap_time(a,b,range(2))
        result['projection_overlap']=projection is not None
        result['trajectory_intersection_xy']=path_cross(a,b)
        result['collision_status']='COLLISION' if hit else 'NO_COLLISION'
        result['evidence']={'contact_interval_normalized': [str(x) for x in hit] if hit else None,
                            'proof': 'intersection of closed inequality intervals' if hit else 'inequality intervals have empty intersection'}
    except KeyError as exc:
        result['missing'].append(str(exc))
    except (ValueError,TypeError,IndexError,ZeroDivisionError) as exc:
        result['collision_status']='INVALID_INPUT'; result['error']=str(exc)
    eject=case.get('ejection')
    if eject is not None:
        try:
            if not isinstance(eject, dict): raise ValueError('ejection must be an object')
            if any(eject.get(k) is None for k in ('product_rear','exit_boundary','available_stroke')):
                raise KeyError('product_rear, exit_boundary, available_stroke')
            rear, boundary, stroke = (q(eject[k]) for k in ('product_rear','exit_boundary','available_stroke'))
            if stroke < 0 or boundary < rear: raise ValueError('invalid ejection geometry or negative stroke')
            if case.get('bodies') is None: raise KeyError('product geometry')
            product=box(case['bodies'][0]); actual_rear=product[0][0]; actual_stroke=product[2][0]
            if rear != actual_rear or stroke != actual_stroke: raise ValueError('scalar ejection input conflicts with product geometry or motion')
            result['ejection_status']='INDETERMINATE' if rear+stroke >= boundary else 'INSUFFICIENT_STROKE'
            result['ejection_evidence']={'final_rear':str(rear+stroke),'exit_boundary':str(boundary), 'direction':'+x', 'limitation':'scalar result cannot prove punch/product contact'}
        except KeyError as exc: result['missing'].append(str(exc))
        except (ValueError,TypeError,ZeroDivisionError) as exc:
            result['ejection_status']='INVALID_INPUT'; result['ejection_error']=str(exc)
    return result

# Conservative research motion restrictions; permission is not a safety certification.
MUST_STAY={'A-FILL':['punch'], 'A-PRESS':['feeder','gate'], 'B-FILL':['punch'],
           'B-PRESS':['feeder','gate','stop','lock'], 'B-OPEN':['punch'],
           'B-EJECT':['feeder','gate','stop','lock']}
NEVER_SIMULTANEOUS={'B-OPEN':[('stop','lock')], 'B-RESET':[('stop','punch')]}
def motion_restrictions(phase, supplied):
    bodies=supplied.get('bodies') or {}; missing=[]; violations=[]
    if supplied.get('motion_type')!='linear': return {'status':'INDETERMINATE','reasons':['unknown motion law']}
    def moving(name):
        try: return any(x != 0 for x in box(bodies.get(name))[2])
        except (KeyError,ValueError,TypeError,ZeroDivisionError): missing.append('motion unknown: '+name); return None
    for name in MUST_STAY.get(phase,[]):
        if moving(name): violations.append(name+' must remain stationary')
    for left,right in NEVER_SIMULTANEOUS.get(phase,[]):
        a,b=moving(left),moving(right)
        if a and b: violations.append(left+' and '+right+' move simultaneously')
    return {'status':'BLOCKED' if violations else 'INDETERMINATE' if missing else 'CLEAR','reasons':violations+missing}

def evaluate_phases(plan, inputs):
    """Evaluate every declared required pair independently; never infer missing motion."""
    coverage={}
    for phase,definition in plan['phases'].items():
        variant=phase[0]
        supplied=inputs.get('phases',{}).get(phase,{})
        bodies=supplied.get('bodies') or {}
        checked=[]; unchecked=[]
        scene=plan.get('scene_bodies')
        pairs=list(itertools.combinations(scene,2)) if scene is not None else definition['required_pairs']
        for left,right in pairs:
            case={'id':phase+':'+left+'/'+right,'variant':variant,'phase':phase,
                  'names':[left,right], 'units':inputs.get('units'), 'contact':inputs.get('contact'), 'motion_type':supplied.get('motion_type'),
                  'time':supplied.get('time'), 'bodies':[bodies.get(left),bodies.get(right)]}
            result=check(case)
            if supplied.get('motion_type') != 'linear':
                result['collision_status']='INDETERMINATE'
                result['missing'].append('supported linear motion law and synchronization')
            if result['collision_status'] in ('COLLISION','NO_COLLISION'):
                checked.append(result)
            else:
                unchecked.append(result)
        coverage[phase]={'checked_pairs':checked,'unchecked_pairs':unchecked,
                         'note':definition['note'], 'motion_restrictions':motion_restrictions(phase,supplied), 'physical_interlocks':'UNKNOWN'}
    return coverage

# A-OUT is an overlay of A-PRESS, never an independent sequential stroke.
TRANSITIONS={'A': [('A-READY','A-FILL'),('A-FILL','A-ISOLATE'),('A-ISOLATE','A-PRESS'),('A-PRESS','A-RETURN'),('A-RETURN','A-READY')],
             'B': [('B-READY','B-FILL'),('B-FILL','B-PRESS'),('B-PRESS','B-UNLOAD'),('B-UNLOAD','B-OPEN'),('B-OPEN','B-EJECT'),('B-EJECT','B-RESET'),('B-RESET','B-READY')]}
GUARDS={'A-FILL':['loading_clear'], 'A-ISOLATE':['feed_finished'], 'A-PRESS':['gate_isolated','feeder_retracted','clamp_ready'], 'A-RETURN':['column_retention_confirmed'], 'A-READY':['punch_retracted'],
        'B-FILL':['stop_closed','lock_engaged'], 'B-PRESS':['gate_isolated','feeder_retracted','stop_closed','lock_engaged'], 'B-UNLOAD':['press_stopped'], 'B-OPEN':['unloading_confirmed'], 'B-EJECT':['stop_open','lock_retracted','gate_isolated','feeder_retracted'], 'B-RESET':['exit_clear'], 'B-READY':['stop_closed','lock_engaged','punch_retracted']}

def transition(previous, following, prev_bodies, next_bodies, guards, coverage=None, prev_time=None, next_time=None):
    """Check ordering, exact position continuity and explicitly supplied permissions."""
    if not isinstance(previous,str) or not isinstance(following,str) or not previous:
        return {'status':'INDETERMINATE','reasons':['missing phase']}
    if (previous,following) not in TRANSITIONS.get(previous[0],[]):
        return {'status':'BLOCKED','reasons':['invalid phase order']}
    reasons=[]; blocked=[]
    try:
        if prev_time is None or next_time is None or len(prev_time)!=2 or len(next_time)!=2: raise KeyError('explicit phase times')
        if q(prev_time[0]) >= q(prev_time[1]) or q(next_time[0]) >= q(next_time[1]): blocked.append('invalid time interval')
        elif q(prev_time[1]) != q(next_time[0]): blocked.append('incompatible phase times')
    except (KeyError,ValueError,TypeError,ZeroDivisionError): reasons.append('explicit valid phase times')
    if coverage is None or coverage.get('unchecked_pairs') or not coverage.get('checked_pairs'):
        reasons.append('pair coverage incomplete')
    elif any(pair.get('collision_status') != 'NO_COLLISION' for pair in coverage['checked_pairs']):
        blocked.append('pair collision or invalid result')
    if coverage is not None:
        rule=coverage.get('motion_restrictions',{}).get('status')
        if rule=='BLOCKED': blocked.append('prohibited motion')
        elif rule!='CLEAR': reasons.append('motion restrictions unknown')
    for name in GUARDS.get(following,[]):
        value=guards.get(name)
        if value is False: blocked.append('guard false: '+name)
        elif value is not True: reasons.append('guard unknown: '+name)
    if not isinstance(prev_bodies,dict) or not isinstance(next_bodies,dict) or not prev_bodies or set(prev_bodies)!=set(next_bodies):
        reasons.append('explicit matching boundary body set')
    else:
        for name in prev_bodies:
            try:
                a,ah,ad=box(prev_bodies[name]); b,bh,_=box(next_bodies[name])
                if any(a[i]+ad[i]!=b[i] or ah[i]+ad[i]!=bh[i] for i in range(3)):
                    blocked.append('incompatible boundary: '+name)
            except (KeyError,ValueError,TypeError,ZeroDivisionError): reasons.append('boundary unknown: '+name)
    return {'status':'BLOCKED' if blocked else 'INDETERMINATE' if reasons else 'ALLOWED', 'reasons':blocked+reasons}

def verify_a_out(press,out):
    if not isinstance(press,dict) or not isinstance(out,dict): return 'INDETERMINATE'
    if not press.get('time') or not out.get('time') or not press.get('bodies') or not out.get('bodies'): return 'INDETERMINATE'
    if press.get('motion_type')!='linear' or out.get('motion_type')!='linear': return 'INDETERMINATE'
    if press['time']!=out['time'] or press['bodies']!=out['bodies']: return 'BLOCKED'
    try:
        from linked import contact
        result=contact(press['bodies'].get('punch'),press['bodies'].get('product'))
        if result['status']!='VALID': return result['status']
        if box(press['bodies']['product'])[2][0] <= 0: return 'BLOCKED'
        return 'CONSISTENT'
    except (KeyError, ValueError,TypeError): return 'INDETERMINATE'

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--fixtures',default=str(HERE/'fixtures.json')); parser.add_argument('--out',default=str(HERE/'results')); parser.add_argument('--phase-inputs',default=str(HERE/'phase_inputs_synthetic.json')); args=parser.parse_args()
    fixture=Path(args.fixtures); data=json.loads(fixture.read_text()); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    cases=data['cases']; results=[check(c) for c in cases]
    plan_path=HERE/'phase_plan.json'; phase_path=Path(args.phase_inputs).resolve()
    plan=json.loads(plan_path.read_text()); phase_inputs=json.loads(phase_path.read_text())
    rev_inputs=json.loads((HERE/'input_template.json').read_text())
    for c,r in zip(cases,results):
        r['expected']=c.get('expected',{}); r['matches_expected']=all(r.get(k)==v for k,v in r['expected'].items()) if r['expected'] else None
    synthetic_coverage=evaluate_phases(plan,phase_inputs)
    transition_results=[]
    phase_sequence={'A':['A-READY','A-FILL','A-ISOLATE','A-PRESS','A-RETURN'], 'B':['B-READY','B-FILL','B-PRESS','B-UNLOAD','B-OPEN','B-EJECT','B-RESET']}
    for variant,sequence in phase_sequence.items():
        for prev,nxt in zip(sequence,sequence[1:]):
            before=phase_inputs['phases'][prev]; after=phase_inputs['phases'][nxt]
            result=transition(prev,nxt,before['bodies'],after['bodies'],{key:True for key in GUARDS.get(nxt,[])},synthetic_coverage[prev],before['time'],after['time'])
            transition_results.append({'from':prev,'to':nxt,'synthetic_guards':'explicit test assumptions only',**result})
    aout=verify_a_out(phase_inputs['phases'].get('A-PRESS'),phase_inputs['phases'].get('A-OUT'))
    # Compare to the actual original READY; do not synthesize a new endpoint.
    legacy_closure=[]
    for variant,last in [('A','A-RETURN'),('B','B-RESET')]:
        before=phase_inputs['phases'][last]; next_phase=variant+'-READY'; after=phase_inputs['phases'][next_phase]
        end=before['time'][1]
        result=transition(last,next_phase,before['bodies'],after['bodies'],{key:True for key in GUARDS[next_phase]},synthetic_coverage[last],before['time'],[end,end+1])
        legacy_closure.append({'from':last,'to':next_phase,'meaning':'boundary only, not a READY proof',**result})
    # A free zone is a query volume, not an additional solid obstacle or physical component.
    zone_cases=[]
    for name,body in [('unoccupied',{'min':[3,0,0],'max':[4,1,1],'delta':[0,0,0]}),('occupied',{'min':[0,0,0],'max':[1,1,1],'delta':[0,0,0]})]:
        query={'id':'A-READY-loading-zone-'+name,'variant':'A','phase':'A-READY','motion_type':'linear','units':{'length':'m','time':'s'},'contact':'touch_is_collision','time':[0,1], 'bodies':[{'min':[0,0,0],'max':[1,1,1],'delta':[0,0,0]},body]}
        result=check(query); occupied=result['collision_status']=='COLLISION'
        zone_cases.append({'id':query['id'], 'query_volume_not_solid':True,'occupied':occupied,'expected':name=='occupied','matches_expected':occupied==(name=='occupied'),'evidence':result})
    transition_fixture=HERE/'transition_fixtures.json'
    transition_scenarios=[]
    for case in json.loads(transition_fixture.read_text())['cases']:
        before=copy.deepcopy(phase_inputs['phases'][case['previous']]); after=copy.deepcopy(phase_inputs['phases'][case['following']])
        if case['mutation']=='boundary_mismatch':
            after['bodies']['punch']['min'][0]+=1; after['bodies']['punch']['max'][0]+=1
        if case['mutation']=='unknown_sync': after['time']=None
        result=transition(case['previous'],case['following'],before['bodies'],after['bodies'],case['guards'],synthetic_coverage[case['previous']],before['time'],after['time'])
        transition_scenarios.append({'id':case['id'], 'expected':case['expected'], 'matches_expected':result['status']==case['expected'], **result})
    report={'classification':'SYNTHETIC ONLY — NOT REV', 'brief_commit':'3aebae606011ded0f6d6e0a8d6ccc15094d88feb',
            'base_commit':'2f463babdc84382a0ab2502f4acfa7a2047087df', 'r5_review_commit':'aadb63c7afb6d95e99867052b3baefba2d259c7d', 'python':sys.version,
            'hashes':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__).resolve(),HERE/'linked.py',fixture.resolve(),HERE/'input_template.json',HERE/'input_audit.md',plan_path,phase_path,HERE/'transition_fixtures.json',ROOT/'verification/r5_model_02/review.md',ROOT/'verification/r5_model_02/independent_check.py',ROOT/'params/registry.yaml',ROOT/'models/first_digital_model_brief.md',ROOT/'controls/press_variant_state_tables.md']},
            'registry_snapshot':'registry_snapshot.yaml','requirements':['REQ/VAL-REV-05','REQ/VAL-REV-06','REQ/VAL-REV-09','REQ/VAL-REV-11','REQ/VAL-REV-12','REQ/VAL-REV-16'],
            'limitations':'Synthetic boxes only, no manufacturing, forces, process, real collision clearance or validation. Independent review pending.', 'phase_plan_scope':plan['scope'], 'synthetic_phase_coverage':synthetic_coverage, 'synthetic_transitions':transition_results, 'legacy_actual_closure':legacy_closure, 'synthetic_transition_scenarios':transition_scenarios, 'synthetic_zone_queries':zone_cases, 'synthetic_a_out_relation':aout, 'rev_phase_coverage':evaluate_phases(plan,rev_inputs), 'force_paths':plan['force_paths'], 'results':results}
    force_svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="230" viewBox="0 0 1200 230">', '<rect width="100%" height="100%" fill="white"/>', '<text x="20" y="25" font-size="18">UNVERIFIED load-path topology — no forces, geometry or strength proven</text>']
    for i,(variant,details) in enumerate(plan['force_paths'].items()):
        y=65+i*80
        force_svg.append(f'<text x="20" y="{y}" font-size="15">Variant {variant}: {escape(" → ".join(details["path"]))}</text>')
        force_svg.append(f'<text x="40" y="{y+25}" font-size="13">UNKNOWN: {escape(", ".join(details["unknown"]))}</text>')
    force_svg.append('</svg>'); (out/'force_paths.svg').write_text('\n'.join(force_svg)+'\n')
    (out/'registry_snapshot.yaml').write_bytes((ROOT/'params/registry.yaml').read_bytes())
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    height=100+140*len(results)
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}">', '<rect width="100%" height="100%" fill="white"/>', '<text x="20" y="30" font-size="20">SYNTHETIC ONLY — XY start/end boxes; z and time in JSON</text>']
    for i,(r,c) in enumerate(zip(results,cases)):
        y=65+140*i
        label=f"{r['id']} {r['variant']}/{r['phase']} collision={r['collision_status']} ejection={r['ejection_status']}"
        lines.append(f'<text x="20" y="{y}" font-size="14">{escape(label)}</text>')
        try:
            aa,bb=map(box,c['bodies'])
            for body,color in ((aa,'#1368b3'),(bb,'#d64a2a')):
                lo,hi,d=body
                for step,style in ((0,'4,3'),(1,'none')):
                    x=float(lo[0]+step*d[0])*25+100
                    yy=y+75-float(hi[1]+step*d[1])*25
                    w=float(hi[0]-lo[0])*25; h=float(hi[1]-lo[1])*25
                    lines.append(f'<rect x="{x}" y="{yy}" width="{w}" height="{h}" fill="none" stroke="{color}" stroke-dasharray="{style}"/>')
            lines.append(f'<text x="370" y="{y+40}" font-size="12">Blue / red: bodies; dashed: start; solid: end. Not swept geometry.</text>')
        except (KeyError,ValueError,TypeError):
            lines.append(f'<text x="100" y="{y+40}" font-size="12">Geometry/motion incomplete or invalid; no drawing.</text>')
        lines.append(f'<line x1="20" y1="{y+95}" x2="950" y2="{y+95}" stroke="#aaa"/>')
    lines.append('</svg>'); (out/'synthetic_phases.svg').write_text('\n'.join(lines)+'\n')
    print(json.dumps([{'id':r['id'],'collision':r['collision_status'],'ejection':r['ejection_status'],'matches_expected':r['matches_expected']} for r in results],indent=2))
    return 1 if any(r['matches_expected'] is False for r in results) or any(r['status'] != 'ALLOWED' for r in transition_results)  or any(not case['matches_expected'] for case in transition_scenarios+zone_cases) else 0
if __name__=='__main__': sys.exit(main())
