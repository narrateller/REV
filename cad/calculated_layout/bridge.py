"""Registered, explicit R3 -> research CAD bridge; never changes source inputs."""
import copy, hashlib, json, math, sys
from fractions import Fraction as F
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT/'cad/feed_power'))
from common import checked, load, selected, bounds, config, digest, packed, read_packed
from service_semantics import Evaluator, protocols, expected_stages, evaluate_scene
from assess import classify, box_at, NativeWitness
AUDIT = ROOT/'verification/r4_calculated_layout'
SOURCE = ROOT/'cad/calculated_layout'
OUT = ROOT/'cad/build/calculated_layout'
BASELINE = ROOT/'cad/feed_power/inputs.assumed.json'
VARS = ('A','B')

def save(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def source_values(v):
    values={};records={}
    for scope in ('r3_parametric_sizing','r3_power_reconcile'):
        path=ROOT/f'verification/{scope}/results/BASE_{v}.json'
        d=json.loads(path.read_text())
        for r in d['inputs']+d['outputs']:
            if r['id'] in records:assert records[r['id']]['value']==r['value']
            records[r['id']]={**r,'source':str(path.relative_to(ROOT))}
            values[r['id']]=F(str(r['value']))
    return values,records

def geometry_values(v):
    p,r=source_values(v);prefix='R3_BASE_'+v+'_'
    w=p['R3_IN_WIDTH'];h=p['R3_IN_HEIGHT'];length=p['R3_IN_PRODUCT_LENGTH']
    chamber=p['R3_IN_MASS']/(p['R3_IN_RHO']*p['R3_IN_PHI']*w*h)
    occupied=p['R3_IN_MASS']/(p['R3_IN_RHO']*w*h)
    exact={'CHAMBER_LENGTH':chamber,'OCCUPIED_LENGTH':occupied,'APPROACH_STROKE':chamber-occupied,'WORK_STROKE':occupied-length,'EJECT_STROKE':p[prefix+'EJECT_STROKE']}
    exact['RETURN_STROKE']=exact['APPROACH_STROKE']+exact['WORK_STROKE']+exact['EJECT_STROKE']
    residual=[]
    for key,x in exact.items():
        src=p[prefix+key];difference=x-src
        # ULP agreement is serialization arithmetic, never a design tolerance.
        assert abs(float(difference))<=32*math.ulp(float(src)),(key,x,src)
        residual.append({'id':prefix+key,'registered_float_decimal':str(src),'model_exact_rational':str(x),'difference_m':str(difference),'meaning':'same R3 formula evaluated in rational arithmetic; no physical tolerance/energy resizing'})
    return p,r,exact,residual

def input_path(v):return SOURCE/f'inputs.BASE_{v}.json'

def make_input(v):
    old=load(BASELINE);data=copy.deepcopy(old);p,records,exact,residual=geometry_values(v)
    width=p['R3_IN_WIDTH'];height=p['R3_IN_HEIGHT'];oldend=F('1.1');length=exact['CHAMBER_LENGTH'];shift=length-oldend
    width_scale=width/F('.4');height_scale=height/F('.4')
    changes=[];refs={};cell_formula={}
    recipe={'variant':v,'mode':'fixed-budget','camera_origin':['0','0','0'],'old_camera_end':str(oldend),'new_camera_end':str(length),'feeding_X':'inside [0,old camera end] affine to new chamber length; outside translated/unchanged','feeding_Y':'affine ratio new width / old cavity width about axis','feeding_Z':'piecewise old chamber outer top -> new outer top, old pocket/doser plane retained','downstream_X':'rigid translation by new chamber length minus old length; channel length retained','frame_and_powerpack':'unchanged; interfaces require recheck','punch':'old axial thickness retained; face width/height from source; initial front X=0','rod':'diameter from R3; exposed segment ends at punch rear; internal/closed length/COTS UNKNOWN'}
    def change(ref,x,why,formula=None):
        x=F(x);before=F(old['parameters'][ref]['value'])
        if x==before:return ref
        key='ASSUMED-LAYOUT-CL-'+v+'-'+ref.removeprefix('ASSUMED-LAYOUT-')
        if key in data['parameters']:assert F(data['parameters'][key]['value'])==x
        item=copy.deepcopy(old['parameters'][ref]);item.update(value=str(x),revision=1,status='ASSUMED',source='R3-linked conditional geometry; see derivation and source refs',scope=['BASE_'+v+' fixed-budget research only'],derivation=why,source_refs=['verification/r3_parametric_sizing/results/BASE_'+v+'.json','verification/r3_power_reconcile/results/BASE_'+v+'.json'],source_lifecycle='CALCULATED_FROM_ASSUMED' if formula else 'ASSUMED_RESEARCH_TRANSFORM',tolerance=None)
        data['parameters'][key]=item;refs[ref]=key
        if formula:cell_formula[key]=formula
        changes.append({'cad_parameter_id':key,'old_id':ref,'old_value':str(before),'new_value':str(x),'unit':item['unit'],'status':item['source_lifecycle'],'reason':why,'native_spreadsheet_formula':formula,'affected_nodes':[]})
        return key
    def xmap(x):return x if x<0 else x*length/oldend if x<=oldend else x+shift
    outer_top=F('.24')*height_scale
    def zfeed(x):
        return x*height_scale if x<=F('.24') else outer_top+(x-F('.24'))*(F('.62')-outer_top)/F('.38') if x<F('.62') else x
    def lit(x):
        # FreeCAD's expression number tokens have finite precision. Large
        # Fraction integer tokens can overflow/round before their division.
        # Preserve exact rationals in JSON; serialize one finite SI decimal.
        return f'({float(F(x))!r} * 1 m)'
    def xexpr(x):return lit(x) if x<0 else f'{lit(x)} * Sources.calc_xratio' if x<=oldend else f'({lit(x)} + Sources.calc_chamber - {lit(oldend)})'
    def zexpr(x):return f'{lit(x)} * Sources.calc_hratio' if x<=F('.24') else f'(Sources.calc_top + ({lit(x)} - {lit(F(".24"))}) * ({lit(F(".62"))} - Sources.calc_top) / {lit(F(".38"))})' if x<F('.62') else lit(x)
    def set_box(c,lo,hi,why,el=None,eh=None):
        el=el or [lit(x) for x in lo];eh=eh or [lit(x) for x in hi]
        for i in range(3):
            c['position'][i]=change(c['position'][i],lo[i],why,el[i]);c['size'][i]=change(c['size'][i],hi[i]-lo[i],why,f'({eh[i]} - {el[i]})')
    for c in data['components']:
        old_c=next(x for x in old['components'] if x['id']==c['id']);lo,hi=bounds(old,old_c);name=c['id']
        feeding=name.startswith(('pocket_','doser_','hopper_','receiving_','inlet_gate','gate_'))
        downstream=name.startswith(('channel_','clamp_','stop_support')) or name in ('end_stop','lock','output_support')
        if c['kind']=='box' and (feeding or name.startswith('chamber_')):
            nl=[xmap(lo[0]),lo[1]*width_scale,zfeed(lo[2]) if feeding else lo[2]*height_scale]
            nh=[xmap(hi[0]),hi[1]*width_scale,zfeed(hi[2]) if feeding else hi[2]*height_scale]
            el=[xexpr(lo[0]),f'{lit(lo[1])} * Sources.calc_wratio',zexpr(lo[2]) if feeding else f'{lit(lo[2])} * Sources.calc_hratio']
            eh=[xexpr(hi[0]),f'{lit(hi[1])} * Sources.calc_wratio',zexpr(hi[2]) if feeding else f'{lit(hi[2])} * Sources.calc_hratio']
            set_box(c,nl,nh,'Explicit research process-module transformation; R3 chamber width/height/length, previous feeder upper plane preserved',el,eh)
        elif c['kind']=='box' and downstream:
            nl=[lo[0]+shift,lo[1],lo[2]];nh=[hi[0]+shift,hi[1],hi[2]]
            if name.startswith('channel_'):
                nl[1]*=width_scale;nh[1]*=width_scale;nl[2]*=height_scale;nh[2]*=height_scale
            el=[f'({lit(lo[0])} + Sources.calc_chamber - {lit(oldend)})',lit(lo[1]),lit(lo[2])];eh=[f'({lit(hi[0])} + Sources.calc_chamber - {lit(oldend)})',lit(hi[1]),lit(hi[2])]
            if name.startswith('channel_'):
                for i,alias in [(1,'wratio'),(2,'hratio')]:el[i]=f'{lit(lo[i])} * Sources.calc_{alias}';eh[i]=f'{lit(hi[i])} * Sources.calc_{alias}'
            set_box(c,nl,nh,'Downstream reaction/output module translated with chamber end; A channel axial length unchanged, channel cross-section follows chamber',el,eh)
        if name=='punch':
            axial=hi[0]-lo[0];set_box(c,[-axial,-width/2,-height/2],[F(0),width/2,height/2],'Source loaded face; existing punch axial thickness retained, chamber-front datum X=0',[lit(-axial),'-Sources.calc_width/2','-Sources.calc_height/2'],[lit(0),'Sources.calc_width/2','Sources.calc_height/2'])
        if name.startswith('product_'):
            a=exact['APPROACH_STROKE'];pl=p['R3_IN_PRODUCT_LENGTH'];set_box(c,[a,-width/2,-height/2],[a+pl,width/2,height/2],'Already-compacted rigid product surrogate, not raw compression physics; source width/height/length',['Sources.calc_approach','-Sources.calc_width/2','-Sources.calc_height/2'],['(Sources.calc_approach + Sources.calc_product)','Sources.calc_width/2','Sources.calc_height/2'])
        if name=='rod':
            c['radius']=change(c['radius'],p['R3_BASE_'+v+'_ROD']/2,'R3 minimum rod diameter; real stroke/internal overlap/strength UNKNOWN','Sources.calc_rod/2')
            punch=next(x for x in old['components'] if x['id']=='punch');th=F(old['parameters'][punch['size'][0]]['value'])
            c['length']=change(c['length'],-th-lo[0],'Exposed rod meets punch rear at initial pose; barrel exterior/COTS left unchanged')
    for key in ['gate_isolate_y','doser_fill_y']:
        data['config'][key]=change(data['config'][key],config(old,key)*width_scale,'Working transverse feeder motion follows explicit feeder Y transform',f'{lit(config(old,key))} * Sources.calc_wratio')
    for k in ('travel_A','travel_B'):
        data['config'][k]=change(data['config'][k],exact['RETURN_STROKE'],'Full axial extent approach+work+eject, exact source formula','Sources.calc_return')
    for k in ('short_A','short_B'):
        data['config'][k]=change(data['config'][k],exact['EJECT_STROKE']/2,'Separate negative fixture: half the registered ejection stroke, not a proposed machine size','Sources.calc_eject/2')
    for k in ('exit_A','exit_B'):
        data['config'][k]=change(data['config'][k],config(old,k)+shift,'Preserved CAD output plane translated with chamber end; simplified R3 plane is reported separately',f'Sources.calc_chamber + {lit(config(old,k)-oldend)}')
    for c in data['components']:
        used=list(c['position'])+(c['size'] if c['kind']=='box' else [c['radius'],c['length']])
        for r in changes:
            if r['cad_parameter_id'] in used:r['affected_nodes'].append(c['id'])
    data.update(input_revision=1,revision_note='New independent R3-linked BASE_'+v+' fixed-budget package; prior FP rev8 unchanged',scenario_id='BASE_'+v,mode='fixed-budget',source_records=records,exact_geometry={k:str(x) for k,x in exact.items()},source_rounding_audit=residual,bridge_recipe=recipe,parameter_changes=changes,source_bindings=[r for r in json.loads((AUDIT/'source_bindings.json').read_text())['rows'] if r['scenario']=='BASE_'+v])
    data['regions']={'loading':'R3-linked throat; upstream feeder interfaces remain ASSUMED, check actual geometry','output':'R3 nominal exit and retained A channel end reported separately','service':'preserved declared protocols, fresh current-geometry checks; physical feasibility UNKNOWN'}
    data['r3_nominal_exit']=str(length+p['R3_IN_CLEARANCE'])
    return data

if __name__=='__main__':
    for v in VARS:
        d=make_input(v);save(input_path(v),d);load(input_path(v));print(v,len(d['parameter_changes']),'registered local CAD parameters before build')
