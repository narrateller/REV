"""Strict test oracle for the limited cycle, separate from scene outcome.

A negative case may match its test expectation while its scene is BLOCKED or
INDETERMINATE. Neither means the whole press is READY.
"""
import itertools
from assess import checked,box_at
from layout_common import selected,config

FIELDS=('geometry','path_collision','required_link','path_transition','continuity_status','path_ready')
EXPECTED={
 'sufficient':('GEOMETRY_SUFFICIENT','NO_COLLISION','LINK_CONFIRMED','ALLOWED_FOR_PATH_SUBSET','CONTINUOUS','RESTORED_FOR_PATH_SUBSET'),
 'short':('SHORT_STROKE','NO_COLLISION','LINK_CONFIRMED','BLOCKED','CONTINUOUS','NOT_CONFIRMED'),
 'collision':('GEOMETRY_SUFFICIENT','COLLISION','LINK_CONFIRMED','BLOCKED','CONTINUOUS','NOT_CONFIRMED'),
 'unknown':('INDETERMINATE','INDETERMINATE','LINK_INDETERMINATE','INDETERMINATE','INDETERMINATE','NOT_CONFIRMED'),
}


def expected_phases(variant,case):
    names=[variant+'-'+p for p in ('READY','FILL','ISOLATE')]
    if variant=='B':names+=['B-'+p for p in ('PRESS','UNLOAD','OPEN-LOCK','OPEN-STOP')]
    names+=['A-PRESS-OUT' if variant=='A' else 'B-EJECT']
    if case=='sufficient':
        names+=[variant+'-RETURN']
        if variant=='B':names+=['B-RESET-STOP','B-RESET-LOCK']
        names+=[variant+'-RESET-INLET',variant+'-READY-RETURNED']
    return names


def assess_scene(scene,data):
    v=scene.get('variant');case=scene.get('case');reported={k:scene.get(k) for k in FIELDS};defects=[];unknown=[];actual={};audit={}
    expected=dict(zip(FIELDS,EXPECTED[case]))
    try:
        stages=scene['stages'];product='product_'+v
        if not stages:raise ValueError('no stages')
        if [s['phase'] for s in stages]!=expected_phases(v,case):defects.append('required phase sequence incomplete/incorrect')
        initial=checked.bodies(data,v)
        if case=='collision':
            x=config(data,'obstacle_'+v);th=config(data,'obstacle_thickness');b=initial[product]
            initial['research_obstacle']={'lo':[str(x),b['lo'][1],b['lo'][2]],'hi':[str(x+th),b['hi'][1],b['hi'][2]],'delta':['0','0','0'],'motion':'linear','exact_box':True,'group':'obstacle','rigid_group':'obstacle'}
        if stages[0]['state']!=initial:defects.append('initial registry/geometry/motion differs from inputs')
        for stage in stages:
            ids=stage['state'];pairs=[tuple(sorted(r['pair'])) for r in stage['pairs']]
            if len(pairs)!=len(set(pairs)) or set(pairs)!=set(itertools.combinations(sorted(ids),2)):defects.append('pair coverage incomplete/duplicated '+stage['phase'])
            for name,b in ids.items():
                try:checked.engine.body(b)
                except (KeyError,NotImplementedError) as exc:unknown.append(name+': '+str(exc))
                except (ValueError,TypeError,ZeroDivisionError) as exc:defects.append(name+': '+str(exc))
        active=next(s for s in stages if s['phase']==('A-PRESS-OUT' if v=='A' else 'B-EJECT'))
        state=active['state'];interval=active['time']
        link=checked.evaluate_pair(state['punch'],state[product],'punch',product,interval,v)['evidence']['link']
        names={'punch',product,'research_obstacle'}|{n for n in state if n.startswith(('chamber_','channel_')) or n in ('lock','end_stop')}
        path=[checked.evaluate_pair(state[a],state[b],a,b,interval,v) for a,b in itertools.combinations(sorted(names&set(state)),2) if {'punch',product}&{a,b}]
        collision='COLLISION' if any(r['status']=='COLLISION' for r in path) else 'INDETERMINATE' if any(r['status'] in ('INVALID_INPUT','INDETERMINATE') for r in path) else 'NO_COLLISION'
        pos=box_at(state[product],interval[1],interval)
        geometry='INDETERMINATE' if pos is None else 'GEOMETRY_SUFFICIENT' if pos[0][0]>=config(data,'exit_'+v) else 'SHORT_STROKE'
        actual.update(geometry=geometry,path_collision=collision,required_link=link)
        contexts={product:{'exit_boundary':str(config(data,'exit_'+v)),'receiving_yz':[[initial[product]['lo'][i],initial[product]['hi'][i]] for i in (1,2)],'required_link':link,'path_collision':collision}}
        checks=checked.assess_continuity(stages,scene['lifecycle'],contexts);continuity=checked.continuity_status(checks)
        if scene.get('continuity')!=checks:defects.append('reported continuity evidence differs from recalculation')
        if continuity=='BLOCKED':defects.append('continuity/lifecycle defect')
        final=checked.advance(stages[-1]['state'])
        restored=set(final)==set(initial)-{product} and all(final[n]['lo']==initial[n]['lo'] and final[n]['hi']==initial[n]['hi'] and final[n]['delta']==['0','0','0'] for n in final)
        remove=scene['lifecycle'];proper_remove=len(remove)==1 and remove[0].get('type')=='REMOVE' and remove[0].get('id')==product and checked.engine.q(remove[0]['time'])==checked.engine.q(interval[1])
        if case!='sufficient' and remove:defects.append('unexpected lifecycle event in negative case')
        lifecycle_valid=all(c['lifecycle_valid'] for c in checks) and proper_remove
        cycle_conditions=geometry=='GEOMETRY_SUFFICIENT' and collision=='NO_COLLISION' and link=='LINK_CONFIRMED' and continuity=='CONTINUOUS' and not unknown
        transition='BLOCKED' if geometry=='SHORT_STROKE' or collision=='COLLISION' or link=='LINK_ABSENT' or defects else 'INDETERMINATE' if geometry=='INDETERMINATE' or collision=='INDETERMINATE' or link!='LINK_CONFIRMED' or continuity!='CONTINUOUS' or unknown else 'ALLOWED_FOR_PATH_SUBSET'
        ready='RESTORED_FOR_PATH_SUBSET' if cycle_conditions and restored and lifecycle_valid and stages[-1]['phase']==v+'-READY-RETURNED' and not defects else 'NOT_CONFIRMED'
        actual=dict(zip(FIELDS,(geometry,collision,link,transition,continuity,ready)))
        audit={'required_phases':[s['phase'] for s in stages],'restored_geometry_and_registry':restored,'validated_product_removal':lifecycle_valid,'continuity':checks,'input_method_status':'INVALID_INPUT' if defects else 'INDETERMINATE' if unknown else 'SUPPORTED','unknown':unknown}
    except (KeyError,TypeError,ValueError,ZeroDivisionError,StopIteration,NotImplementedError) as exc:defects.append(str(exc))
    unexpected_unknown=[x for x in unknown if case!='unknown' or not x.startswith('product_'+str(v)+':') or 'motion is not linear' in x]
    mismatches=[{'field':k,'expected':expected[k],'reported':reported[k],'recomputed':actual.get(k)} for k in FIELDS if reported[k]!=expected[k] or actual.get(k)!=expected[k]]
    success=not defects and not unknown and case=='sufficient' and not mismatches and audit.get('restored_geometry_and_registry') and audit.get('validated_product_removal')
    known_block=bool(defects) or actual.get('geometry')=='SHORT_STROKE' or actual.get('path_collision')=='COLLISION' or actual.get('required_link')=='LINK_ABSENT' or reported.get('path_transition')=='BLOCKED'
    scene_outcome='LIMITED_READY_CONFIRMED' if success else 'BLOCKED' if known_block else 'INDETERMINATE'
    return {'variant':v,'case':case,'scope':'limited path/cycle only','reported':reported,'recomputed':actual,'geometric_scene_outcome':scene_outcome,'limited_cycle_success':bool(success),'test_expectation':expected,'matches_expectation':not defects and not mismatches and not unexpected_unknown,'unexpected_unknown_inputs':unexpected_unknown,'mismatches':mismatches,'blocking_defects':defects,'audit':audit,'whole_assembly_READY':'INDETERMINATE'}


def evaluate_suite(scenes,data):
    results=[assess_scene(s,data) for s in scenes]
    ids=[(s['variant'],s['case']) for s in results];complete=len(ids)==8 and set(ids)=={(v,c) for v in 'AB' for c in EXPECTED}
    return {'status':'PASS' if complete and all(s['matches_expectation'] for s in results) else 'FAIL','complete_eight_cases':complete,'scene_results':results}
