"""New revision adapter. All reviewed layout/frame modules remain unchanged."""
import copy,gzip,hashlib,io,itertools,json,os,sys
from fractions import Fraction as F
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
for folder in ('cad/layout','cad/layout_correction','cad/frame_mount'):sys.path.insert(0,str(ROOT/folder))
from assess import checked,NativeWitness,analyze,box_at,overlap,TARGETS
from layout_common import load,selected,bounds,config,digest
from outcomes import evaluate_suite
from verify_cycles import verify_cycles
from cad_validation import check_cad_adapter
from run import module_service,planar_contact_area
from inventory import inventory
from geometry_evidence import strict_interval

INPUT=ROOT/'cad/feed_power/inputs.assumed.json'
OUT=ROOT/'cad/build/feed_power'
AUDIT=ROOT/'verification/r4_feed_power'
LEGACY={tuple(sorted(('doser_slide',n))) for n in ('hopper_R','hopper_floor_right','receiving_rim_right')}
OLD_CRITICAL={'crossbar0','crossbar1','crossbar2','cylinder_mount_front','cylinder_mount_rear','cylinder_seat_L','cylinder_seat_R','cylinder_seat_bridge',*[f'upper_post_{s}{i}' for s in 'LR' for i in range(3)],'inlet_gate','gate_service_cap','gate_house_front','gate_house_rear','gate_house_top','pocket_R_lower','lock','end_stop','stop_support','stop_support_L','stop_support_bridge','guard_right'}


def critical_pair(pair,changed):
    # Moving services need coverage even when the moving shape itself did not
    # change. In particular, retain the blocked legacy doser UP inequalities.
    return bool(set(pair)&(changed|OLD_CRITICAL|{'doser_slide','pump_motor','hydraulic_tank'})) or tuple(pair) in LEGACY or tuple(pair) in {tuple(sorted(p)) for p in TARGETS}


def changed_bodies(data):
    old=load(ROOT/'cad/frame_mount/inputs.assumed.json');before={c['id']:c for c in old['components']}
    return {c['id'] for c in data['components'] if c['id'] not in before or bounds(data,c)!=bounds(old,before[c['id']])}


def mandatory_pair(scene,pair,changed):
    return scene['case'].startswith('service_') or critical_pair(pair,changed)


def save(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')


def packed(path,data):
    with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as stream:
        stream.write(json.dumps(data,sort_keys=True,separators=(',',':')).encode())


def read_packed(path):return json.loads(gzip.decompress(Path(path).read_bytes()))


def freeze():
    f=json.loads((AUDIT/'frozen_tool.json').read_text())
    for name,sha in f['sha256'].items():
        if digest(ROOT/name)!=sha:raise ValueError('reviewed module changed '+name)
    return f


def plans(data):
    lift=config(data,'service_lift');side=config(data,'doser_service_y');park=config(data,'motor_park_y');module=('pump_motor','motor_mount_rear','motor_mount_front')
    def moves(names,axis,d):return [(n,tuple(d if i==axis else F(0) for i in range(3))) for n in names]
    return {
      'doser_retract_lift':[moves(['doser_slide'],1,side),moves(['doser_slide'],2,lift),moves(['doser_slide'],2,-lift),moves(['doser_slide'],1,-side)],
      'motor':[moves(['pump_motor'],2,lift),moves(['pump_motor'],2,-lift)],
      'powerpack_module':[moves(('hydraulic_tank',*module),2,lift),moves(('hydraulic_tank',*module),2,-lift)],
      'tank_after_motor_park':[moves(module,2,lift),moves(module,1,park),moves(['hydraulic_tank'],2,lift),moves(['hydraulic_tank'],2,-lift),moves(module,1,-park),moves(module,2,-lift)]}


def services(data,v):
    scenes=[]
    for label,motions in plans(data).items():
        initial=checked.bodies(data,v);current=copy.deepcopy(initial);stages=[];t=F(0)
        for i,move in enumerate([[]]+motions+[[]]):
            state=copy.deepcopy(current)
            for n,delta in move:state[n]['delta']=[str(x) for x in delta]
            interval=[str(t),str(t+config(data,'phase_duration'))];pairs=checked.matrix(state,interval,v)
            stages.append({'phase':v+'-SERVICE-FP-'+label+'-'+str(i),'state':state,'time':interval,'pairs':pairs,'counts':checked.summarize(pairs)})
            current=checked.advance(state);t+=config(data,'phase_duration')
        continuity=checked.assess_continuity(stages,[])
        restored=set(current)==set(initial) and all(current[n]['lo']==initial[n]['lo'] and current[n]['hi']==initial[n]['hi'] for n in initial)
        scenes.append({'variant':v,'case':'service_fp_'+label,'stages':stages,'continuity':continuity,'continuity_status':checked.continuity_status(continuity),'positions_restored':restored,'physical_actuator_rigging_and_access':'INDETERMINATE: real stroke, fixing, loads and rigging UNKNOWN'})
    return scenes


def manifest_catalog():
    files=[p for folder in (ROOT/'cad/feed_power',OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=OUT/'publication_manifest.json']
    files += [AUDIT/n for n in ('input_audit.md','input_manifest.json','before_inventory.json','frozen_tool.json')]
    return {str(p.relative_to(ROOT)):p for p in files}


def seal():save(OUT/'publication_manifest.json',{'schema_version':2,'scope':'FP sources, saved CAD/evidence and fixed audit inputs; verifier stdout excluded','sha256':{n:digest(p) for n,p in sorted(manifest_catalog().items())}})


def verify_manifest():
    record=json.loads((OUT/'publication_manifest.json').read_text());files=manifest_catalog()
    if record.get('schema_version')!=2 or set(record['sha256'])!=set(files):raise ValueError('publication schema/catalog mismatch')
    for n,p in files.items():
        if digest(p)!=record['sha256'][n]:raise ValueError('publication hash mismatch '+n)
    return len(files)


def geometry(data,scenes,evaluator=None):
    """All pair coverage; exact interval audit of every new/old critical pair."""
    changed=changed_bodies(data)
    target={tuple(sorted(p)) for p in TARGETS};rows=[];positive=[];counts={};total=0;previous=0
    for s in scenes:
        for st in s['stages']:
            expected=list(itertools.combinations(sorted(st['state']),2));assert [tuple(r['pair']) for r in st['pairs']]==expected,'matrix coverage'
            total+=len(expected)
            for pair in expected:
                if not mandatory_pair(s,pair,changed):continue
                proof=evaluator.proof(*(st['state'][n] for n in pair)) if evaluator else strict_interval(*(st['state'][n] for n in pair));counts[proof['status']]=counts.get(proof['status'],0)+1
                r={'variant':s['variant'],'case':s['case'],'phase':st['phase'],'pair':pair,**proof};rows.append(r)
                if pair in target:
                    previous+=1;assert proof['status']!='POSITIVE_BOUND_OVERLAP',('old target regression',r)
                if proof['status']=='POSITIVE_BOUND_OVERLAP':
                    positive.append(r)
                    assert s['case']=='service_doser_slide' and pair in LEGACY,('new positive critical overlap',r)
    packed(OUT/'interval_rows.json.gz',rows)
    assert {(r['variant'],tuple(r['pair'])) for r in positive}=={(v,p) for v in 'AB' for p in LEGACY},'legacy penetration evidence missing'
    result={'all_pair_rows':total,'audited_critical_rows':len(rows),'counts':counts,'changed_body_IDs':sorted(changed),'previous_target_rows':previous,'legacy_vertical_positive_rows':positive,'method':'unchanged reviewed exact affine interval solver; native matching independently required','whole_press_READY':'INDETERMINATE'}
    save(OUT/'interval_evidence.json',result);return result


def joint_pairs():
    rows=[]
    def add(a,b,why):rows.append({'pair':sorted((a,b)),'reason':why})
    for side,wall,floor in [('rear','pocket_rear','doser_floor_rear'),('front','pocket_front','doser_floor_front'),('L','pocket_L','doser_floor_left'),('R','pocket_R','doser_floor_right')]:add(wall,floor,'pocket collar upper face to doser ring lower face; real joint UNKNOWN')
    for end in ('rear','front'):
        add('doser_'+end,'hopper_floor_'+end,'side-wall top to hopper-floor underside')
        for tray in ('inner','outer'):add('doser_'+end,'doser_tray_'+tray,'continuous side support around open cap-service slot')
        add('doser_floor_'+end,'doser_'+end,'existing doser floor to extended side support')
    for floor in ('doser_floor_rear','doser_floor_front','doser_floor_right'):add(floor,'doser_tray_inner','outboard tray to existing ring')
    for side,end in [('L','rear'),('R','front')]:
        add('doser_guide_'+side+'_inner','doser_floor_'+end,'guide lower face to collar')
        for tray in ('inner','outer'):add('doser_guide_'+side+'_'+tray,'doser_tray_'+tray,'guide lower face to service tray')
    for end in ('rear','front'):
        add('pump_motor','motor_mount_'+end,'motor end face; flange/bolts/radial restraint UNKNOWN')
        add('hydraulic_tank','motor_mount_'+end,'mount base to tank top; real tank construction/load capacity UNKNOWN')
    for i in range(2):
        add('tank_arm_'+str(i),'hydraulic_tank','arm top to tank underside')
        add('tank_arm_'+str(i),'tank_mount_'+str(i),'arm fixed butt to frame bracket')
        add('tank_mount_'+str(i),'base_R','bracket fixed side face into base rail')
    return rows


def native_evidence(data,scenes):
    old=load(ROOT/'cad/frame_mount/inputs.assumed.json');old_scenes=read_packed(ROOT/'cad/build/frame_mount/raw_checked_tool/all_pairs.json.gz')+read_packed(ROOT/'cad/build/frame_mount/service_scenes.json.gz')
    lookup={(s['variant'],s['case'],st['phase']):st for s in scenes for st in s['stages']};old_lookup={(s['variant'],s['case'],st['phase']):st for s in old_scenes for st in s['stages']}
    before=NativeWitness(ROOT/'cad/build/frame_mount');after=NativeWitness(OUT);comparisons=[];joints=[]
    try:
        for r in json.loads((AUDIT/'before_inventory.json').read_text())['rows']:
            w=next(w for w in r['native_representatives'] if w.get('common_volume_mm3',0)>1e-5);key=(r['variant'],w['case'],w['phase']);left=old_lookup[key];right=lookup[key]
            a=before.at(r['variant'],r['pair'],left['state'],w['time'],left['time']);b=after.at(r['variant'],r['pair'],right['state'],w['time'],right['time'])
            legacy=tuple(r['pair']) in LEGACY
            assert a['common_volume_mm3']>1e-5
            assert (b['common_volume_mm3']>1e-5)==legacy,('incorrect before/after result',r,b)
            comparisons.append({'variant':r['variant'],'pair':r['pair'],'case':w['case'],'phase':w['phase'],'before':a,'after':b,'disposition':'LEGACY_VERTICAL_BLOCKED_NOT_RELABELED' if legacy else 'STATIC_PENETRATION_REMOVED'})
        for v in 'AB':
            state=checked.bodies(data,v)
            for item in joint_pairs():
                a,b=item['pair'];nominal,measure,axes=overlap(box_at(state[a],'0',['0','1']),box_at(state[b],'0',['0','1']));w=after.at(v,item['pair'],state,'0',['0','1']);area=planar_contact_area(after.objects[v][a].Shape,after.objects[v][b].Shape)
                assert nominal=='TOUCH' and measure>0 and w['common_volume_mm3']<=1e-5 and area>0,('joint missing',v,item,nominal,area,w)
                joints.append({'variant':v,**item,'nominal_face_area_m2':str(measure),'native_face_area_mm2':area,'native':w,'scope':'assembly-only conditional mating, not approved physical fixing'})
        save(OUT/'before_after_native.json',comparisons);save(OUT/'interfaces.json',joints)
        return comparisons,joints
    finally:before.close();after.close()
