#!/usr/bin/env python3
"""Synthetic-only continuous collision checking for linearly translated AABBs."""
import argparse
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
            result['ejection_status']='SUFFICIENT_STROKE' if rear+stroke >= boundary else 'INSUFFICIENT_STROKE'
            result['ejection_evidence']={'final_rear':str(rear+stroke),'exit_boundary':str(boundary), 'direction':'+x'}
        except KeyError as exc: result['missing'].append(str(exc))
        except (ValueError,TypeError,ZeroDivisionError) as exc:
            result['ejection_status']='INVALID_INPUT'; result['ejection_error']=str(exc)
    return result

def evaluate_phases(plan, inputs):
    """Evaluate every declared required pair independently; never infer missing motion."""
    coverage={}
    for phase,definition in plan['phases'].items():
        variant=phase[0]
        supplied=inputs.get('phases',{}).get(phase,{})
        bodies=supplied.get('bodies') or {}
        checked=[]; unchecked=[]
        for left,right in definition['required_pairs']:
            case={'id':phase+':'+left+'/'+right,'variant':variant,'phase':phase,
                  'names':[left,right], 'units':inputs.get('units'), 'contact':inputs.get('contact'),
                  'time':supplied.get('time'), 'bodies':[bodies.get(left),bodies.get(right)]}
            result=check(case)
            if result['collision_status'] in ('COLLISION','NO_COLLISION'):
                checked.append(result)
            else:
                unchecked.append(result)
        coverage[phase]={'checked_pairs':checked,'unchecked_pairs':unchecked,
                         'note':definition['note'], 'physical_interlocks':'UNKNOWN'}
    return coverage

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
    report={'classification':'SYNTHETIC ONLY — NOT REV', 'brief_commit':'3aebae606011ded0f6d6e0a8d6ccc15094d88feb',
            'base_commit':'2f463babdc84382a0ab2502f4acfa7a2047087df', 'python':sys.version,
            'hashes':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__).resolve(),fixture.resolve(),HERE/'input_template.json',HERE/'input_audit.md',plan_path,phase_path,ROOT/'params/registry.yaml',ROOT/'models/first_digital_model_brief.md',ROOT/'controls/press_variant_state_tables.md']},
            'registry_snapshot':'registry_snapshot.yaml','requirements':['REQ/VAL-REV-05','REQ/VAL-REV-06','REQ/VAL-REV-09','REQ/VAL-REV-11','REQ/VAL-REV-12','REQ/VAL-REV-16'],
            'limitations':'Synthetic boxes only, no manufacturing, forces, process, real collision clearance or validation. Independent review pending.', 'phase_plan_scope':plan['scope'], 'synthetic_phase_coverage':evaluate_phases(plan,phase_inputs), 'rev_phase_coverage':evaluate_phases(plan,rev_inputs), 'force_paths':plan['force_paths'], 'results':results}
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
    return 1 if any(r['matches_expected'] is False for r in results) else 0
if __name__=='__main__': sys.exit(main())
