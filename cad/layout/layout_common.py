"""Input handling for research-only REV layout. Lengths are SI metres."""
import hashlib,json
from pathlib import Path
from fractions import Fraction
ROOT=Path(__file__).resolve().parents[2]
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
    data=json.loads(Path(path).read_text());errors=[]
    if data.get('classification')!='ASSUMED_RESEARCH_ONLY_NOT_REV':errors.append('research classification missing')
    for key,p in data.get('parameters',{}).items():
        try:
            if not key.startswith('ASSUMED-LAYOUT-') or p['status']!='ASSUMED' or p['value'] is None or p['unit'] not in ('m','s'):raise ValueError('classification/value/unit')
            Fraction(p['value'])
            for field in ('revision','source','uncertainty','tolerance','purpose','scope','author_session'):
                if field not in p:raise ValueError('metadata '+field)
        except (KeyError,TypeError,ValueError,ZeroDivisionError) as e:errors.append('parameter '+key+': '+str(e))
    if any(data.get('real_REV',{}).get(k,'missing') is not None for k in ('dimensions','strokes','loads','feedstock')):errors.append('real REV values must remain UNKNOWN')
    components=data.get('components',[]);ids=[x.get('id') for x in components]
    if len(ids)!=len(set(ids)):errors.append('duplicate body ID')
    for c in components:
        try:
            if c['kind'] not in ('box','cylinder_x') or c['variant'] not in ('both','A','B'):raise ValueError('unsupported shape/variant')
            if len(c['position'])!=3:raise ValueError('position vector')
            refs=list(c['position'])
            if c['kind']=='box':
                if len(c['size'])!=3:raise ValueError('size vector')
                lengths=c['size']
            else:lengths=[c['radius'],c['length']]
            refs+=lengths
            if any(data['parameters'][r]['unit']!='m' for r in refs):raise ValueError('length unit must be m')
            if any(value(data,r)<=0 for r in lengths):raise ValueError('nonpositive extent')
        except (KeyError,TypeError,ValueError,ZeroDivisionError) as e:errors.append('component '+str(c.get('id'))+': '+str(e))
    for key,ref in data.get('config',{}).items():
        try:
            if data['parameters'][ref]['unit']!=('s' if key=='phase_duration' else 'm'):raise ValueError('unit')
            value(data,ref)
        except (KeyError,TypeError,ValueError,ZeroDivisionError) as e:errors.append('config '+key+': '+str(e))
    try:
        if config(data,'phase_duration')<=0:errors.append('nonpositive phase duration')
        if config(data,'tessellation')<=0:errors.append('nonpositive tessellation')
    except (KeyError,TypeError,ValueError,ZeroDivisionError) as e:errors.append('required config: '+str(e))
    if errors:raise ValueError('INVALID_INPUT: '+'; '.join(errors))
    return data

def value(data,ref):return Fraction(data['parameters'][ref]['value'])
def config(data,key):return value(data,data['config'][key])
def selected(data,variant):return [x for x in data['components'] if x['variant'] in ('both',variant)]
def bounds(data,c):
    lo=[value(data,k) for k in c['position']]
    if c['kind']=='box':return lo,[lo[i]+value(data,c['size'][i]) for i in range(3)]
    r=value(data,c['radius']);length=value(data,c['length']);return [lo[0],lo[1]-r,lo[2]-r],[lo[0]+length,lo[1]+r,lo[2]+r]
