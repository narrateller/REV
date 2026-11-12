"""Fresh complete service evaluation, independent of saved derived statuses.

Geometry proves only the declared linear/bounding-volume model. Physical
feasibility and unapproved contacts/fixtures remain INDETERMINATE.
"""
import hashlib,collections
from common import *
from assess import classify,validated_body


def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def protocols(data,v):
    z=F(0);lift=config(data,'service_lift')
    def step(names,axis,delta):return [(n,tuple(delta if i==axis else z for i in range(3))) for n in names]
    result={}
    def add(case,label,motions,legacy=False):result[case]={'label':label,'motions':motions,'legacy':legacy}
    add('service_gate','gate',[step(['gate_service_cap'],2,config(data,'service_cap_z')),step(['inlet_gate'],1,config(data,'service_gate_y')),step(['inlet_gate'],1,-config(data,'service_gate_y')),step(['gate_service_cap'],2,-config(data,'service_cap_z'))])
    for name in ['cylinder_barrel','rod','doser_slide']+(['clamp_L'] if v=='A' else ['lock','end_stop']):add('service_'+name,name,[step([name],2,lift),step([name],2,-lift)],name=='doser_slide')
    if v=='B':add('service_portal','portal',[step(['stop_support','stop_support_L','stop_support_bridge'],2,lift),step(['stop_support','stop_support_L','stop_support_bridge'],2,-lift)])
    add('service_cylinder_module','cylinder_module',[step(['cylinder_barrel','rod'],2,lift),step(['cylinder_barrel','rod'],2,-lift)])
    for name,motions in plans(data).items():add('service_fp_'+name,'FP-'+name,motions)
    return result


def expected_stages(data,v,protocol):
    current=checked.bodies(data,v);t=F(0);result=[]
    for i,moves in enumerate([[]]+protocol['motions']+[[]]):
        state=copy.deepcopy(current)
        for n,d in moves:state[n]['delta']=list(map(str,d))
        result.append({'phase':v+'-SERVICE-'+protocol['label']+'-'+str(i),'time':[str(t),str(t+config(data,'phase_duration'))],'state':state})
        current=checked.advance(state);t+=config(data,'phase_duration')
    return result


def body_key(b):
    return (b.get('motion'),*(None if b.get(k) is None else tuple(b[k]) for k in ('lo','hi','delta')),b.get('exact_box'),b.get('group'),b.get('rigid_group'))


def is_moving(b):
    try:return b.get('motion')!='linear' or b.get('delta') is None or any(checked.engine.q(x)!=0 for x in b['delta'])
    except (TypeError,KeyError,ValueError,ZeroDivisionError,AttributeError):return True


class Evaluator:
    def __init__(self,data,models=None):
        self.data=data;self.raw_cache={};self.proof_cache={};self.class_cache={};self.native=None;self.models=models
        self.kinds={c['id']:c['kind'] for c in data['components']}
    def raw(self,v,pair,state,time):
        key=(v,tuple(pair),body_key(state[pair[0]]),body_key(state[pair[1]]),tuple(time))
        if key not in self.raw_cache:self.raw_cache[key]=checked.evaluate_pair(state[pair[0]],state[pair[1]],*pair,time,v)
        return self.raw_cache[key]
    def proof(self,a,b):
        key=(body_key(a),body_key(b))
        if key not in self.proof_cache:
            try:self.proof_cache[key]=strict_interval(a,b)
            except (ValueError,KeyError,TypeError,ZeroDivisionError,NotImplementedError) as e:self.proof_cache[key]={'status':'INDETERMINATE','reason':str(e) or repr(e)}
        return self.proof_cache[key]
    def classification(self,scene,stage,pair):
        key=(scene['variant'],tuple(pair),body_key(stage['state'][pair[0]]),body_key(stage['state'][pair[1]]),tuple(stage['time']))
        if key in self.class_cache:return {'variant':scene['variant'],'case':scene['case'],'phase':stage['phase'],**self.class_cache[key]}
        raw=self.raw(scene['variant'],pair,stage['state'],stage['time']);r=classify(raw,stage['state'],stage['time'],scene['variant'])
        def witness(t):
            if self.native is None:self.native=NativeWitness(self.models)
            return self.native.at(scene['variant'],pair,stage['state'],t,stage['time'])
        if r['class'] in ('INDETERMINATE','ENVELOPE_INTERSECTION') and any(not stage['state'][n]['exact_box'] for n in pair):
            w=witness(stage['time'][0]);r['native_witness']=w
            if w.get('common_volume_mm3',0)>1e-5:r['class']='NATIVE_PENETRATION_WITNESS';r['native_solids']='PROVEN_PENETRATION_AT_WITNESS'
        if tuple(sorted(pair)) in {tuple(sorted(p)) for p in TARGETS}:
            t=next((x['witness_time'] for x in r.get('regions',[]) if x['kind']=='PENETRATION'),stage['time'][0]);r['native_target_witness']=witness(t)
        self.class_cache[key]=r
        return {'variant':scene['variant'],'case':scene['case'],'phase':stage['phase'],**r}
    def close(self):
        if self.native:self.native.close()


def evaluate_scene(scene,data,evaluator):
    v=scene.get('variant');case=scene.get('case');stages=scene.get('stages',[]);known=[];unknown=[];collisions=[];evidence_bad=[];phase_results=[];total=0
    specification=protocols(data,v).get(case) if v in ('A','B') else None
    expected=expected_stages(data,v,specification) if specification else []
    initial=checked.bodies(data,v) if v in ('A','B') else {};required=set(initial)
    if not specification:unknown.append({'reason':'no declared mandatory service protocol'})
    if len(stages)!=len(expected):unknown.append({'reason':'missing/extra mandatory path sections','expected':len(expected),'actual':len(stages)})
    for i,stage in enumerate(stages):
        phase=stage.get('phase');state=stage.get('state',{});interval=stage.get('time');valid_time=True
        try:
            start,end=map(checked.engine.q,interval)
            if start>=end:raise ValueError('nonpositive phase interval')
        except (ValueError,TypeError,KeyError,ZeroDivisionError) as e:valid_time=False;unknown.append({'phase':phase,'reason':'time not validated: '+str(e)})
        if set(state)!=required:unknown.append({'phase':phase,'reason':'mandatory registry incomplete/extra','missing':sorted(required-set(state)),'extra':sorted(set(state)-required)})
        methods={}
        for n,b in state.items():
            try:
                validated_body(b)
                if n not in evaluator.kinds or b.get('exact_box')!=(evaluator.kinds[n]=='box'):raise ValueError('shape method does not match registered native primitive')
                methods[n]=True
            except (ValueError,TypeError,KeyError,ZeroDivisionError,NotImplementedError) as e:
                methods[n]=False;unknown.append({'phase':phase,'body':n,'reason':'unsupported/unknown mandatory method: '+(str(e) or repr(e))})
        if i<len(expected):
            want=expected[i]
            if phase!=want['phase']:known.append({'phase':phase,'reason':'declared phase order/name mismatch','expected':want['phase']})
            if valid_time and [start,end]!=list(map(F,want['time'])):known.append({'phase':phase,'reason':'declared time schedule mismatch'})
            for n in required&set(state):
                for field in ('lo','hi','delta'):
                    try:
                        actual=list(map(checked.engine.q,state[n][field]));target=list(map(F,want['state'][n][field]))
                        if actual!=target:known.append({'phase':phase,'body':n,'reason':'declared pose/moving-component mismatch','field':field})
                    except (TypeError,KeyError,ValueError,ZeroDivisionError):unknown.append({'phase':phase,'body':n,'reason':'unknown mandatory '+field})
        expected_pairs=list(itertools.combinations(sorted(state),2));saved_pairs=[tuple(r.get('pair',[])) for r in stage.get('pairs',[])]
        if saved_pairs!=expected_pairs:evidence_bad.append({'phase':phase,'reason':'pair matrix coverage/order/duplicates incorrect'})
        supplied={tuple(r.get('pair',[])):r for r in stage.get('pairs',[])};matrix_hash=hashlib.sha256();proof_hash=hashlib.sha256();raw_counts=collections.Counter();pair_unknown=0;positive=0
        for pair in expected_pairs:
            total+=1
            try:
                raw=evaluator.raw(v,pair,state,interval) if valid_time else {'pair':list(pair),'status':'INDETERMINATE','reason':'phase time is not validated'}
            except (TypeError,KeyError,ValueError,ZeroDivisionError,NotImplementedError) as e:raw={'pair':list(pair),'status':'INDETERMINATE','reason':str(e)}
            raw_counts[raw['status']]+=1;matrix_hash.update(fingerprint(raw).encode())
            if supplied.get(pair)!=raw:evidence_bad.append({'phase':phase,'pair':pair,'reason':'saved pair evidence differs from fresh calculation'})
            proof=evaluator.proof(state[pair[0]],state[pair[1]]) if valid_time and all(methods[n] for n in pair) else {'status':'INDETERMINATE','reason':'mandatory method/time not established'}
            proof_hash.update(fingerprint({'pair':pair,**proof}).encode())
            if proof['status']=='POSITIVE_BOUND_OVERLAP':
                if all(evaluator.kinds.get(n)=='box' and state[n].get('group')!='routes' for n in pair):
                    collisions.append({'phase':phase,'pair':pair,**proof,'basis':'exact registered boxes over complete supported linear interval'});positive+=1
                else:pair_unknown+=1;unknown.append({'phase':phase,'pair':pair,'reason':'conservative curved/envelope overlap cannot establish solid clearance'})
            elif proof['status']=='INDETERMINATE':pair_unknown+=1
        if pair_unknown:unknown.append({'phase':phase,'reason':'unknown mandatory pair intervals','count':pair_unknown})
        if {k:raw_counts.get(k,0) for k in ('CLEAR','ALLOWED_CONTACT','COLLISION','INDETERMINATE','INVALID_INPUT')}!=stage.get('counts'):evidence_bad.append({'phase':phase,'reason':'saved stage counts differ from recomputed matrix'})
        phase_results.append({'phase':phase,'time':interval,'required_pairs':len(expected_pairs),'matrix_sha256':matrix_hash.hexdigest(),'interval_sha256':proof_hash.hexdigest(),'positive_box_pairs':positive,'unknown_pair_intervals':pair_unknown,'actual_moving_components':sorted(n for n,b in state.items() if is_moving(b))})
    # Recompute continuity/return; flags in the saved file are evidence to check,
    # never prerequisites that can replace the actual path calculation.
    continuity_bad=[];continuity_unknown=[]
    for a,b in zip(stages,stages[1:]):
        try:
            if checked.engine.q(a['time'][1])!=checked.engine.q(b['time'][0]):continuity_bad.append('phase time gap '+str(a['phase']))
        except (KeyError,TypeError,ValueError,ZeroDivisionError):continuity_unknown.append('unvalidated boundary time')
        for n in set(a.get('state',{}))&set(b.get('state',{})):
            try:
                for field in ('lo','hi'):
                    if any(checked.engine.q(x)+checked.engine.q(d)!=checked.engine.q(y) for x,d,y in zip(a['state'][n][field],a['state'][n]['delta'],b['state'][n][field])):continuity_bad.append(a['phase']+'/'+n)
            except (KeyError,TypeError,ValueError,ZeroDivisionError):continuity_unknown.append(a.get('phase','?')+'/'+n)
    continuity='BLOCKED' if continuity_bad else 'INDETERMINATE' if continuity_unknown else 'CONTINUOUS'
    restored=True;return_unknown=False
    if not stages:restored=False;return_unknown=True
    else:
        state=stages[-1].get('state',{})
        if set(state)!=required:restored=False;return_unknown=True
        for n in required&set(state):
            try:
                for field in ('lo','hi'):
                    if any(checked.engine.q(x)+checked.engine.q(d)!=F(y) for x,d,y in zip(state[n][field],state[n]['delta'],initial[n][field])):restored=False
            except (KeyError,ValueError,TypeError,ZeroDivisionError):restored=False;return_unknown=True
    if continuity_bad:known.append({'reason':'confirmed continuity defect','details':continuity_bad})
    if continuity_unknown:unknown.append({'reason':'continuity not established','details':continuity_unknown})
    if not restored:
        (unknown if return_unknown else known).append({'reason':'required nominal return UNKNOWN' if return_unknown else 'required nominal return not restored'})
    if scene.get('continuity_status')!=continuity or scene.get('positions_restored')!=restored:evidence_bad.append({'reason':'saved continuity/return flags differ from actual path'})
    try:
        fresh_continuity=checked.assess_continuity(stages,[])
        if scene.get('continuity')!=fresh_continuity:evidence_bad.append({'reason':'saved continuity evidence stale'})
    except (TypeError,ValueError,KeyError,ZeroDivisionError):unknown.append({'reason':'continuity evidence cannot be recomputed'})
    geometry='BLOCKED' if collisions else 'INDETERMINATE' if unknown else 'CONFIRMED_NO_POSITIVE_VOLUME'
    limited=geometry=='CONFIRMED_NO_POSITIVE_VOLUME' and not known and continuity=='CONTINUOUS' and restored and not evidence_bad
    outcome='BLOCKED' if collisions or known else 'INDETERMINATE' # physical mandatory conditions UNKNOWN in this model
    expected_collision_pairs=LEGACY if specification and specification['legacy'] else set()
    actual_collision_pairs={tuple(x['pair']) for x in collisions}
    matches=bool(specification) and not known and not unknown and not evidence_bad and continuity=='CONTINUOUS' and restored and (geometry=='BLOCKED' and actual_collision_pairs==expected_collision_pairs if expected_collision_pairs else limited)
    return {'variant':v,'case':case,'scope':'complete registered pair/phase geometric model only','geometric_path_outcome':geometry,'overall_service_outcome':outcome,'limited_geometry_success':bool(limited),'physical_feasibility':'INDETERMINATE','physical_reason':'real actuator, disconnection, contact/fixtures, loads and rigging UNKNOWN','required_pair_rows':total,'method_status':'INDETERMINATE' if unknown else 'SUPPORTED','plan_status':'BLOCKED' if known else 'INDETERMINATE' if unknown else 'CONFIRMED','continuity_status':continuity,'nominal_return':'RESTORED' if restored else 'INDETERMINATE' if return_unknown else 'NOT_RESTORED','proven_collisions':collisions,'unknown_mandatory_conditions':unknown,'protocol_defects':known,'saved_evidence_mismatches':evidence_bad,'phases':phase_results,'source_state_time_sha256':fingerprint([{'phase':s.get('phase'),'time':s.get('time'),'state':s.get('state')} for s in stages]),'matches_test_expectation':bool(matches),'negative_test_is_path_success':False}


def evaluate_services(data,scenes,evaluator=None):
    evaluator=evaluator or Evaluator(data)
    results=[evaluate_scene(s,data,evaluator) for s in scenes]
    required={(v,c) for v in 'AB' for c in protocols(data,v)};seen=[(r['variant'],r['case']) for r in results];complete=len(seen)==len(set(seen)) and set(seen)==required
    return {'calculation_execution':'COMPLETED','test_evaluation':'PASS' if complete and all(r['matches_test_expectation'] for r in results) else 'FAIL','complete_required_service_set':complete,'service_scenes':results,'geometric_path_counts':dict(collections.Counter(r['geometric_path_outcome'] for r in results)),'overall_service_counts':dict(collections.Counter(r['overall_service_outcome'] for r in results)),'physical_feasibility':'INDETERMINATE','whole_press_READY':'INDETERMINATE','G1':'OPEN'}


def attach_assessment(assessment,semantics):
    result=copy.deepcopy(assessment);result['service_semantics']=semantics
    indexed={(r['variant'],r['case']):r for r in semantics['service_scenes']}
    for scene in result['scenes']:
        if (scene['variant'],scene['case']) in indexed:
            r=indexed[(scene['variant'],scene['case'])];scene['actual_service_geometric_outcome']=r['geometric_path_outcome'];scene['actual_service_outcome']=r['overall_service_outcome'];scene['limited_geometry_success']=r['limited_geometry_success'];scene['physical_feasibility']='INDETERMINATE'
    return result


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--scenes',type=Path,default=OUT/'service_scenes.json.gz');args=parser.parse_args();data=load(INPUT);evaluator=Evaluator(data,OUT)
    try:
        result=evaluate_services(data,read_packed(args.scenes),evaluator);print(json.dumps(result,indent=2));return 0 if result['test_evaluation']=='PASS' else 1
    finally:evaluator.close()


if __name__=='__main__':sys.exit(main())
