"""NEW analysis layer for independent review; checked tool files are not edited.

Uses the frozen tool's event partitions. Strict AABB overlap is classified
exactly over each region; native samples are witnesses, not full BRep coverage.
"""
import copy,gzip,json,sys,io
from functools import lru_cache
from pathlib import Path
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'cad/layout'))
import check_layout as checked
from layout_common import load,config,bounds,selected

TARGETS=[('inlet_gate','pocket_R'),('inlet_gate','pocket_R_lower'),('lock','guard_right'),('lock','stop_support'),('lock','stop_support_L'),('end_stop','guard_right'),('end_stop','stop_support'),('end_stop','stop_support_L')]

@lru_cache(maxsize=8192)
def _linear_body(motion,lo,hi,delta):
    return checked.engine.body({'motion':motion,'lo':lo,'hi':hi,'delta':delta})


def validated_body(body):
    vectors=[None if body.get(k) is None else tuple(body[k]) for k in ('lo','hi','delta')]
    return _linear_body(body.get('motion'),*vectors)


def box_at(body,time,interval):
    try:
        lo,hi,delta=validated_body(body);start,end=map(checked.engine.q,interval);at=checked.engine.q(str(time))
        if not start<end or not start<=at<=end:return None
        u=(at-start)/(end-start)
        return ([x+u*d for x,d in zip(lo,delta)],[x+u*d for x,d in zip(hi,delta)])
    except (KeyError,TypeError,ValueError,ZeroDivisionError,NotImplementedError):return None


def support_failure(row,state,interval):
    """Applicability and complete evidence are prerequisites even for CLEAR."""
    try:
        start,end=map(checked.engine.q,interval)
        if not start<end:raise ValueError('invalid interval')
        if len(row['pair'])!=2:raise ValueError('invalid pair')
        for name in row['pair']:
            b=state[name]
            if not isinstance(b.get('exact_box'),bool):raise ValueError('shape/bounding method not declared '+name)
            try:validated_body(b)
            except (KeyError,TypeError,ValueError,ZeroDivisionError,NotImplementedError) as exc:raise ValueError(name+': '+str(exc)) from exc
        evidence=row['evidence']
        if evidence.get('input_status')!='SUPPORTED':raise ValueError('raw method/input status '+str(evidence.get('input_status')))
        regions=evidence.get('segments')
        if not regions:raise ValueError('empty interval evidence')
        cursor=start;point=True
        for r in regions:
            left,right=checked.engine.q(r['from']),checked.engine.q(r['to'])
            if r['collision_status'] not in ('CLEAR','COLLISION','ALLOWED_CONTACT'):raise ValueError('unknown/invalid interval evidence')
            if point:
                if r['interval']!='point' or left!=cursor or right!=cursor:raise ValueError('missing point boundary or evidence gap')
            else:
                if r['interval']!='open' or left!=cursor or not left<right<=end:raise ValueError('missing open interval or evidence gap')
                cursor=right
            point=not point
        if point or cursor!=end:raise ValueError('interval coverage incomplete')
        if row['status']=='CLEAR' and any(r['collision_status']!='CLEAR' for r in regions):raise ValueError('raw CLEAR contradicts interval evidence')
        if row['status']=='INVALID_INPUT':raise ValueError('raw INVALID_INPUT')
        return None
    except (KeyError,TypeError,ValueError,ZeroDivisionError,NotImplementedError) as exc:return str(exc)


def overlap(a,b):
    lengths=[min(a[1][i],b[1][i])-max(a[0][i],b[0][i]) for i in range(3)]
    if any(x<0 for x in lengths):return 'CLEAR',F(0),[]
    if all(x>0 for x in lengths):return 'PENETRATION',lengths[0]*lengths[1]*lengths[2],[]
    zeros=[i for i,x in enumerate(lengths) if x==0];area=F(1)
    for i,x in enumerate(lengths):
        if i not in zeros:area*=x
    return 'TOUCH',area if len(zeros)==1 else F(0),zeros


def allowed_interfaces():
    rows={}
    def add(a,b,axis,reason):rows[tuple(sorted((a,b)))]=(axis,reason)
    for wall in ('pocket_rear','pocket_front','gate_house_rear','gate_house_front'):add('inlet_gate',wall,0,'conditional tangential guide face')
    add('inlet_gate','gate_support',2,'conditional lower guide face')
    for wall in ('gate_house_rear','gate_house_front','gate_house_top'):add('gate_service_cap',wall,1,'closed bay cap / tangential service withdrawal')
    for wall in ('gate_house_rear','gate_house_front'):add(wall,'gate_house_top',0,'fixed butt joint of enclosure')
    for wall in ('gate_house_rear','gate_house_front'):add(wall,'gate_support',2,'fixed lower enclosure joint')
    add('pocket_R_lower','gate_support',1,'fixed continuation below gate slot')
    add('pocket_R','gate_house_top',1,'fixed upper continuation of gate slot')
    add('stop_support_bridge','output_support',2,'conditional zero-volume base support; strength UNKNOWN')
    add('lock','end_stop',0,'conditional closed axial reaction face / tangential release')
    for post in ('stop_support','stop_support_L'):
        add('lock',post,0,'conditional axial reaction face / tangential withdrawal')
        add(post,'stop_support_bridge',2,'fixed portal column/bridge joint')
    for rail in ('side_rail_L','side_rail_R'):add('stop_support_bridge',rail,1,'portal reaction into frame / conditional service slide')
    return rows
POLICY=allowed_interfaces()


def classify(row,state,interval,variant):
    reason=support_failure(row,state,interval)
    if reason is not None:return {'pair':row.get('pair'),'raw_status':row.get('status'),'class':'INDETERMINATE','reason':reason,'exact_box_sign_coverage':'NOT_ESTABLISHED','raw_evidence':row.get('evidence')}
    a,b=row['pair'];ba,bb=state[a],state[b];evidence=[];has_unknown=False;positive=False;touch=False;allowed=True
    if row['status']=='CLEAR':return {'pair':row['pair'],'raw_status':'CLEAR','class':'CLEAR','basis':'complete separation already proved by frozen tool; no pair excluded'}
    envelope=ba.get('group')=='routes' or bb.get('group')=='routes'
    if not ba['exact_box'] or not bb['exact_box']:
        shadow=copy.deepcopy(state);shadow[a]['exact_box']=True;shadow[b]['exact_box']=True
        box_result=classify(row,shadow,interval,variant)
        if box_result['class'] in ('PENETRATION','ENVELOPE_INTERSECTION'):
            box_result.update({'class':'ENVELOPE_INTERSECTION','native_solids':'INDETERMINATE','basis':'strict overlap of conservative bounds; no full-stroke solid penetration proof'})
            return box_result
        return {'pair':row['pair'],'raw_status':row['status'],'class':'INDETERMINATE','basis':'curved geometry/trajectory not confirmed, native witnesses separately'}
    for region in row['evidence']['segments']:
        if region['collision_status']=='INVALID_INPUT':has_unknown=True;continue
        time=F(region['from']) if region['interval']=='point' else (F(region['from'])+F(region['to']))/2
        aa,bc=box_at(ba,time,interval),box_at(bb,time,interval)
        if aa is None or bc is None:has_unknown=True;continue
        status,measure,zeros=overlap(aa,bc)
        if status=='CLEAR':continue
        positive|=status=='PENETRATION';touch|=status=='TOUCH'
        rule=POLICY.get(tuple(sorted((a,b))))
        permitted=status=='TOUCH' and measure>0 and ((rule is not None and zeros==[rule[0]]) or row['evidence'].get('link')=='LINK_CONFIRMED')
        allowed&=permitted
        evidence.append({'region':[region['from'],region['to'],region['interval']],'witness_time':str(time),'kind':status,'positive_overlap_m3':str(measure) if status=='PENETRATION' else '0','touch_face_area_m2':str(measure) if status=='TOUCH' else None,'touch_axes':zeros,'conditional_touch_policy':rule[1] if permitted and rule else 'checked punch/product contact' if permitted else None})
    status='ENVELOPE_INTERSECTION' if positive and envelope else 'PENETRATION' if positive else 'INDETERMINATE' if has_unknown else 'ALLOWED_SYNTHETIC_TOUCH' if touch and allowed else 'INDETERMINATE' if touch else 'CLEAR'
    return {'pair':row['pair'],'raw_status':row['status'],'class':status,'exact_box_sign_coverage':'complete checked event partition' if not has_unknown else 'incomplete','regions':evidence}


def scene_geometric_status(counts):
    if any(counts.get(k,0) for k in ('PENETRATION','NATIVE_PENETRATION_WITNESS')):return 'BLOCKED'
    if any(counts.get(k,0) for k in ('INDETERMINATE','ENVELOPE_INTERSECTION')):return 'INDETERMINATE'
    return 'CLEAR_IN_SUPPORTED_METHOD'


def service_scenes(data,variant):
    results=[];z=F(0);lift=config(data,'service_lift')
    plans=[('gate',[[('gate_service_cap',(z,z,config(data,'service_cap_z')))], [('inlet_gate',(z,config(data,'service_gate_y'),z))], [('inlet_gate',(z,-config(data,'service_gate_y'),z))], [('gate_service_cap',(z,z,-config(data,'service_cap_z')))]])]
    names=['cylinder_barrel','rod','doser_slide']+(['clamp_L'] if variant=='A' else ['lock','end_stop'])
    for name in names:plans.append((name,[[(name,(z,z,lift))],[(name,(z,z,-lift))]]))
    if variant=='B':plans.append(('portal',[[ (n,(z,z,lift)) for n in ('stop_support','stop_support_L','stop_support_bridge') ],[ (n,(z,z,-lift)) for n in ('stop_support','stop_support_L','stop_support_bridge') ]]))
    for label,motions in plans:
        initial=checked.bodies(data,variant);current=copy.deepcopy(initial);stages=[];t=F(0)
        for index,moves in enumerate([[]]+motions+[[]]):
            state=copy.deepcopy(current)
            for name,delta in moves:state[name]['delta']=[str(x) for x in delta]
            interval=[str(t),str(t+config(data,'phase_duration'))];pairs=checked.matrix(state,interval,variant)
            stages.append({'phase':variant+'-SERVICE-'+label+'-'+str(index),'time':interval,'state':state,'pairs':pairs,'counts':checked.summarize(pairs)})
            current=checked.advance(state);t+=config(data,'phase_duration')
        continuity=checked.assess_continuity(stages,[])
        restored=all(current[n]['lo']==initial[n]['lo'] and current[n]['hi']==initial[n]['hi'] for n in current)
        results.append({'variant':variant,'case':'service_'+label,'stages':stages,'continuity':continuity,'continuity_status':checked.continuity_status(continuity),'positions_restored':restored,'physical_isolation_and_lifting':'UNKNOWN'})
    return results


class NativeWitness:
    def __init__(self,models):
        sys.path.append('/usr/lib/freecad-python3/lib');import FreeCAD as App
        self.App=App;self.docs={};self.objects={};self.cache={}
        for v in 'AB':
            self.docs[v]=App.openDocument(str(Path(models)/v/f'layout_{v}.FCStd'));self.objects[v]={o.Name:o for o in self.docs[v].Objects if hasattr(o,'ResearchStatus')}
    def at(self,variant,pair,state,time,interval):
        if any(n not in self.objects[variant] for n in pair):return {'status':'INDETERMINATE','reason':'injected scenario body has no persisted native object'}
        positions=[box_at(state[n],time,interval) for n in pair]
        if any(p is None for p in positions):return {'status':'INDETERMINATE','reason':'native pose requires complete supported linear motion'}
        key=(variant,tuple(pair),tuple(tuple(p[0]) for p in positions))
        if key in self.cache:return self.cache[key]
        shapes=[]
        for n,p in zip(pair,positions):
            shape=self.objects[variant][n].Shape.copy();bb=shape.optimalBoundingBox(False,False)
            shape.translate(self.App.Vector(*[float(x)*1000-y for x,y in zip(p[0],(bb.XMin,bb.YMin,bb.ZMin))]));shapes.append(shape)
        common=shapes[0].common(shapes[1]);result={'status':'SAMPLED_NATIVE_WITNESS','time':str(time),'common_volume_mm3':common.Volume,'common_faces':len(common.Faces),'distance_mm':shapes[0].distToShape(shapes[1])[0]}
        self.cache[key]=result;return result
    def close(self):
        for doc in self.docs.values():self.App.closeDocument(doc.Name)


def function_witness(data,scenes,native):
    report={}
    for v in 'AB':
        cycle=next(s for s in scenes if s['variant']==v and s['case']=='sufficient');initial=cycle['stages'][0]['state'];closed=next(st for st in cycle['stages'] if st['phase'].endswith('PRESS-OUT') or st['phase']=='B-PRESS')['state']
        aperture_x=[F(initial['chamber_top_rear']['hi'][0]),F(initial['chamber_top_front']['lo'][0])];aperture_y=[F(initial['chamber_left']['hi'][1]),F(initial['chamber_right']['lo'][1])]
        gate=closed['inlet_gate'];open_gate=initial['inlet_gate']
        cover=F(gate['lo'][0])<=aperture_x[0] and F(gate['hi'][0])>=aperture_x[1] and F(gate['lo'][1])<=aperture_y[0] and F(gate['hi'][1])>=aperture_y[1]
        uncovered=F(open_gate['lo'][1])>=aperture_y[1]
        report[v]={'feed_aperture_xy_m':[[str(x) for x in aperture_x],[str(x) for x in aperture_y]],'open_gate_clears_aperture':uncovered,'closed_gate_covers_aperture':cover,'geometric_ejection':cycle['geometry'],'limited_path':cycle['path_transition'],'physical_feed_sealing_holding_forces':'UNKNOWN'}
        if v=='B':
            chain=[('end_stop','lock'),('lock','stop_support'),('lock','stop_support_L'),('stop_support','stop_support_bridge'),('stop_support_L','stop_support_bridge'),('stop_support_bridge','side_rail_L'),('stop_support_bridge','side_rail_R')];rows=[]
            for pair in chain:
                a,b=(box_at(initial[n],'0',['0','1']) for n in pair);status,area,axes=overlap(a,b);w=native.at(v,pair,initial,'0',['0','1'])
                rows.append({'pair':pair,'nominal_kind':status,'face_area_m2':str(area),'positive_area_contact':status=='TOUCH' and area>0,'native':w})
            report[v]['conditional_reaction_chain']=rows
    return report


def analyze(data,models,raw,out,cycle_suite=None):
    out=Path(out);scenes=json.loads(gzip.decompress(Path(raw).read_bytes()));scenes+=service_scenes(data,'A')+service_scenes(data,'B');native=NativeWitness(models)
    targets=[];summary=[];stream=gzip.GzipFile(filename=str(out/'classifications.jsonl.gz'),mode='wb',mtime=0)
    try:
        functions=function_witness(data,scenes,native)
        for scene in scenes:
            counts={};target_count=0;target_bad=0;moving_bad=[]
            for stage in scene['stages']:
                for row in stage['pairs']:
                    result=classify(row,stage['state'],stage['time'],scene['variant']);pair=row['pair']
                    # Curved overlap: a positive native witness proves penetration;
                    # absence at samples never proves full-stroke BRep separation.
                    if result['class'] in ('INDETERMINATE','ENVELOPE_INTERSECTION') and any(not stage['state'][n]['exact_box'] for n in pair):
                        w=native.at(scene['variant'],pair,stage['state'],stage['time'][0],stage['time']);result['native_witness']=w
                        if w.get('common_volume_mm3',0)>1e-5:result['class']='NATIVE_PENETRATION_WITNESS';result['native_solids']='PROVEN_PENETRATION_AT_WITNESS'
                    counts[result['class']]=counts.get(result['class'],0)+1
                    is_target=tuple(sorted(pair)) in {tuple(sorted(p)) for p in TARGETS}
                    if is_target:
                        target_count+=1;target_bad+=result['class'] in ('PENETRATION','ENVELOPE_INTERSECTION','NATIVE_PENETRATION_WITNESS')
                        time=next((r['witness_time'] for r in result.get('regions',[]) if r['kind']=='PENETRATION'),stage['time'][0]);result['native_target_witness']=native.at(scene['variant'],pair,stage['state'],time,stage['time'])
                        targets.append({'variant':scene['variant'],'case':scene['case'],'phase':stage['phase'],**result})
                    if scene['case'].startswith('service_') and any(any(F(d)!=0 for d in stage['state'][n]['delta']) for n in pair) and result['class'] in ('PENETRATION','ENVELOPE_INTERSECTION','NATIVE_PENETRATION_WITNESS'):
                        moving_bad.append({'phase':stage['phase'],'pair':pair,'class':result['class']})
                    stream.write((json.dumps({'variant':scene['variant'],'case':scene['case'],'phase':stage['phase'],**result},sort_keys=True,separators=(',',':'))+'\n').encode())
            summary.append({'variant':scene['variant'],'case':scene['case'],'counts':counts,'geometric_scene_outcome':scene_geometric_status(counts),'target_rows':target_count,'target_penetration_rows':target_bad,'service_moving_penetrations':moving_bad,'continuity_status':scene.get('continuity_status'),'positions_restored':scene.get('positions_restored'),'whole_press_READY':'INDETERMINATE'})
        stream.close()
        with gzip.GzipFile(filename=str(out/'service_scenes.json.gz'),mode='wb',mtime=0) as f:
            with io.TextIOWrapper(f,encoding='utf-8') as text:json.dump([s for s in scenes if s['case'].startswith('service_')],text,sort_keys=True,separators=(',',':'))
        result={'cycle_test_evaluation':{'status':cycle_suite['status'],'scene_results':cycle_suite['scene_results']} if cycle_suite else {'status':'NOT_EVALUATED'},'analysis_maturity':'NEW_ANALYSIS_REQUIRES_INDEPENDENT_REVIEW','frozen_tool':'de377f012da08f34796b2e59aee663ba0b2b3d2b','scenes':summary,'target_pairs':targets,'function_witnesses':functions,'touch_policy':[{ 'pair':list(k),'axis':v[0],'reason':v[1],'scope':'conditional exact synthetic face only, no physical approval'} for k,v in POLICY.items()],'limits':['raw checked statuses are retained, no core exclusions added','strict box-overlap sign proven on all event regions; native samples are only witnesses','edge/point/unclassified contacts INDETERMINATE','curved BRep continuity not proved by sampled witnesses','geometric feed aperture/closure/load-face continuity not physical performance or safety'],'whole_assembly_READY':'INDETERMINATE','raw_metadata_caveat':'source_commit_inputs and known_native_penetrations/tool_blockers strings in frozen check_layout are historical baseline metadata, not provenance or review of revised geometry; use this run manifest and new evidence'}
        (out/'assessment.json').write_text(json.dumps(result,indent=2)+'\n');return result
    finally:stream.close();native.close()
