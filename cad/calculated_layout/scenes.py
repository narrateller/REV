"""R3-time-linked diagnostic trajectories. Never authorize physical movement."""
import collections,itertools
from bridge import *

def pair_matrix(evaluator,v,state,time):
    if getattr(evaluator,'plan_only',False):return []
    return [evaluator.raw(v,p,state,time) for p in itertools.combinations(sorted(state),2)]

def work_scene(data,v,case,evaluator):
    values,records=source_values(v);g={k:F(x) for k,x in data['exact_geometry'].items()};name='product_'+v
    current=checked.bodies(data,v);initial=copy.deepcopy(current);stages=[];t=F(0)
    if case=='collision':
        x=F(data['r3_nominal_exit']);b=current[name];th=config(data,'obstacle_thickness')
        current['research_obstacle']={'lo':[str(x),b['lo'][1],b['lo'][2]],'hi':[str(x+th),b['hi'][1],b['hi'][2]],'delta':['0','0','0'],'motion':'linear','exact_box':True,'group':'obstacle','rigid_group':'fixture_only'}
        initial=copy.deepcopy(current)
    def stage(label,dt,moves=None,unknown=False):
        nonlocal t,current
        state=copy.deepcopy(current)
        for n,delta in (moves or {}).items():state[n]['delta']=list(map(str,delta))
        if unknown:state[name]['delta']=None
        time=[str(t),str(t+dt)];rows=pair_matrix(evaluator,v,state,time)
        stages.append({'phase':v+'-'+label,'time':time,'state':state,'pairs':rows,'counts':checked.summarize(rows),'permission':'CONDITIONAL_DIAGNOSTIC_ONLY_NOT_PHYSICAL_AUTHORIZATION'})
        current=checked.advance(state);t+=dt
    z=F(0);fixture=config(data,'phase_duration');doser=config(data,'doser_fill_y');gate=config(data,'gate_isolate_y')
    def axis(dx,product=False):return {n:(dx,z,z) for n in (['punch','rod',name] if product else ['punch','rod'])}
    def time(phase):return values['R3P_BASE_'+v+'_'+phase+'_TIME']
    stage('READY',fixture);stage('FILL',fixture,{'doser_slide':(z,doser,z)});stage('ISOLATE',fixture,{'doser_slide':(z,-doser,z),'inlet_gate':(z,gate,z)})
    budget_start=t
    stage('APPROACH',time('APPROACH'),axis(g['APPROACH_STROKE']))
    stage('WORK',time('WORK'),axis(g['WORK_STROKE'],True))
    stage('HOLD',values['R3_IN_T_HOLD'])
    if v=='A':stage('AUX',values['R3_IN_T_AUX_A'])
    else:
        stage('UNLOAD',values['R3_IN_T_UNLOAD_B'])
        dt=values['R3_IN_T_OPEN_B']/2
        stage('OPEN-LOCK',dt,{'lock':(z,config(data,'open_lock_y'),z)})
        stage('OPEN-STOP',dt,{'end_stop':(z,config(data,'open_stop_y'),z)})
    eject=g['EJECT_STROKE']/2 if case=='short' else g['EJECT_STROKE']
    stage('EJECT',time('EJECT'),axis(eject,True),case=='unknown');active=stages[-1]
    # No premature REMOVE: actual preserved CAD output has not been reached.
    rear=None if case=='unknown' else F(current[name]['lo'][0]);link=checked.evaluate_pair(active['state']['punch'],active['state'][name],'punch',name,active['time'],v)['evidence']['link']
    stage('RETURN',time('RETURN'),axis(-(g['APPROACH_STROKE']+g['WORK_STROKE']+eject)))
    budget_end=t
    if v=='B':
        stage('RESET-STOP',fixture,{'end_stop':(z,-config(data,'open_stop_y'),z)})
        stage('RESET-LOCK',fixture,{'lock':(z,-config(data,'open_lock_y'),z)})
    stage('RESET-INLET',fixture,{'inlet_gate':(z,-gate,z)});stage('READY-PROBE',fixture)
    continuity=checked.assess_continuity(stages,[]);restored=all(current[n]['lo']==initial[n]['lo'] and current[n]['hi']==initial[n]['hi'] for n in current if n!=name)
    return {'variant':v,'case':case,'stages':stages,'lifecycle':[],'continuity':continuity,'continuity_status':checked.continuity_status(continuity),'positions_restored':restored,'product_removed':False,'product_retained_reason':'actual preserved output not reached / no validated external receiving event','ejection_phase':v+'-EJECT','required_link':link,'product_rear_after_eject':str(rear) if rear is not None else None,'r3_nominal_exit':data['r3_nominal_exit'],'actual_CAD_exit':str(config(data,'exit_'+v)),'nominal_axial_geometry':'INDETERMINATE' if rear is None else 'GEOMETRY_SUFFICIENT' if rear>=F(data['r3_nominal_exit']) else 'SHORT_STROKE','actual_output_geometry':'INDETERMINATE' if rear is None else 'GEOMETRY_SUFFICIENT' if rear>=config(data,'exit_'+v) else 'SHORT_STROKE','fixed_budget_interval':[str(budget_start),str(budget_end)],'fixed_budget_duration':str(budget_end-budget_start),'registered_fixed_budget_cycle':str(values['R3P_BASE_'+v+'_FIXED_BUDGET_CYCLE']),'full_diagnostic_duration':str(t),'nominal_return':'RESTORED_TOOLS_ONLY' if restored else 'NOT_RESTORED','READY':'NOT_CONFIRMED','B_open_permission':'INDETERMINATE' if v=='B' else 'NOT_APPLICABLE','physical_feasibility':'INDETERMINATE','scope':'rigid preformed-product surrogate, no real compression, no controller or physical transition permission'}

def service_scene(data,v,case,spec,evaluator):
    stages=expected_stages(data,v,spec)
    for st in stages:
        st['pairs']=pair_matrix(evaluator,v,st['state'],st['time']);st['counts']=checked.summarize(st['pairs'])
    checks=checked.assess_continuity(stages,[])
    return {'variant':v,'case':case,'stages':stages,'continuity':checks,'continuity_status':checked.continuity_status(checks),'positions_restored':True,'physical_feasibility':'INDETERMINATE','time_scope':'inherited ASSUMED diagnostic service time, not a real service velocity'}

def make_scenes(data,v,evaluator):
    return [work_scene(data,v,c,evaluator) for c in ('sufficient','short','collision','unknown')]+[service_scene(data,v,c,s,evaluator) for c,s in protocols(data,v).items()]

def assess_scenes(data,v,scenes,evaluator,rows_path=None):
    import gzip,io
    stream=gzip.GzipFile(filename=str(rows_path),mode='wb',mtime=0) if rows_path else None
    results=[];inventory={};total=0;target_rows=[]
    targets={tuple(sorted(p)) for p in __import__('common').TARGETS}
    try:
        for scene in scenes:
            counts=collections.Counter();proofs=collections.Counter();positive=[];unknown=[];rows=0;links=[]
            for st in scene['stages']:
                assert [tuple(r['pair']) for r in st['pairs']]==list(itertools.combinations(sorted(st['state']),2))
                for raw in st['pairs']:
                    pair=tuple(raw['pair']);fresh=evaluator.raw(v,pair,st['state'],st['time']);assert fresh==raw,'saved raw evidence changed'
                    proof=evaluator.proof(*(st['state'][n] for n in pair));cls=copy.deepcopy(evaluator.classification(scene,st,pair))
                    # Frozen native cache keys are poses, not time labels. Reuse
                    # geometry, explicitly label this scene's requested time.
                    if 'native_witness' in cls:cls['native_witness']={**cls['native_witness'],'time':st['time'][0]}
                    if 'native_target_witness' in cls:cls['native_target_witness']={**cls['native_target_witness'],'time':next((r['witness_time'] for r in cls.get('regions',[]) if r['kind']=='PENETRATION'),st['time'][0])}
                    if proof['status']=='POSITIVE_BOUND_OVERLAP' and any(not st['state'][n]['exact_box'] for n in pair) and all(st['state'][n].get('group')!='routes' for n in pair):
                        if evaluator.native is None:evaluator.native=NativeWitness(evaluator.models)
                        a,b=map(F,st['time']);lo,hi=map(F,proof['normalized_boundary_values']);u=(max(F(0),lo)+min(F(1),hi))/2
                        when=str(a+(b-a)*u);witness={**evaluator.native.at(v,pair,st['state'],when,st['time']),'time':when};cls['supplementary_native_witness']=witness
                        if witness.get('common_volume_mm3',0)>1e-5:cls['class']='NATIVE_PENETRATION_WITNESS'
                    counts[cls['class']]+=1;proofs[proof['status']]+=1;rows+=1
                    record={'variant':v,'case':scene['case'],'phase':st['phase'],'time':st['time'],'pair':pair,'strict_interval':proof,'classification':cls}
                    if stream:stream.write((json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode())
                    if tuple(sorted(pair)) in targets:target_rows.append({'case':scene['case'],'phase':st['phase'],'pair':pair,'class':cls['class'],'interval':proof['status']})
                    if cls['class'] in ('PENETRATION','NATIVE_PENETRATION_WITNESS'):
                        positive.append({'phase':st['phase'],'pair':pair,'class':cls['class']})
                    if cls['class'] not in ('CLEAR','ALLOWED_SYNTHETIC_TOUCH'):
                        key=tuple(sorted(pair));entry=inventory.setdefault(key,{'pair':key,'classes':set(),'cases':set(),'phases':set(),'witnesses':[]})
                        entry['classes'].add(cls['class']);entry['cases'].add(scene['case']);entry['phases'].add(st['phase'])
                        if len(entry['witnesses'])<4:entry['witnesses'].append(record)
                    if set(pair)=={'punch','product_'+v} and st['phase'].endswith(('-WORK','-EJECT')):links.append({'phase':st['phase'],'link':raw['evidence']['link']})
            total+=rows
            outcome='BLOCKED' if positive else 'INDETERMINATE' if any(counts[k] for k in ('INDETERMINATE','ENVELOPE_INTERSECTION')) else 'CONFIRMED_NO_POSITIVE_VOLUME'
            base={k:x for k,x in scene.items() if k not in ('stages','continuity')};base.update(pair_rows=rows,class_counts=dict(counts),interval_counts=dict(proofs),geometric_scene_outcome=outcome,proven_positive_pairs=positive,required_links=links,physical_feasibility='INDETERMINATE',whole_press_READY='INDETERMINATE')
            if scene['case'].startswith('service_'):
                sem=evaluate_scene(scene,data,evaluator);base['fresh_service_semantics']=sem
                base['overall_service_outcome']='BLOCKED' if outcome=='BLOCKED' or sem['geometric_path_outcome']=='BLOCKED' else 'INDETERMINATE'
                base['limited_geometry_success']=outcome=='CONFIRMED_NO_POSITIVE_VOLUME' and sem['limited_geometry_success']
            else:
                base['limited_cycle_success']=False
                base['overall_cycle_outcome']='BLOCKED' if positive or scene['actual_output_geometry']=='SHORT_STROKE' else 'INDETERMINATE'
                base['test_expectation_match']=scene['required_link']==('LINK_INDETERMINATE' if scene['case']=='unknown' else 'LINK_CONFIRMED') and scene['nominal_axial_geometry']==('INDETERMINATE' if scene['case']=='unknown' else 'SHORT_STROKE' if scene['case']=='short' else 'GEOMETRY_SUFFICIENT')
                base['READY']='NOT_CONFIRMED'
            results.append(base)
    finally:
        if stream:stream.close()
    issues=[]
    for row in inventory.values():
        for k in ('classes','cases','phases'):row[k]=sorted(row[k])
        row['classification']='NATIVE_PENETRATION' if 'NATIVE_PENETRATION_WITNESS' in row['classes'] else 'EXACT_BOX_PENETRATION' if 'PENETRATION' in row['classes'] else 'CONDITIONAL_ENVELOPE_INTERSECTION' if 'ENVELOPE_INTERSECTION' in row['classes'] else 'INDETERMINATE'
        issues.append(row)
    return {'variant':v,'scenario':'BASE_'+v,'mode':'fixed-budget','execution':'COMPLETED','scene_results':results,'all_pair_rows':total,'issues':sorted(issues,key=lambda r:r['pair']),'previous_target_rows':target_rows,'physical_feasibility':'INDETERMINATE','B_open_permission':'INDETERMINATE' if v=='B' else 'NOT_APPLICABLE','whole_press_READY':'INDETERMINATE','G1':'OPEN'}
