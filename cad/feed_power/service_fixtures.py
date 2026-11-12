"""Synthetic regression mutations of saved poses, not changes to CAD/REV data."""
from service_semantics import *


def refresh(scene,evaluator):
    s=copy.deepcopy(scene)
    for stage in s['stages']:
        stage['pairs']=[evaluator.raw(s['variant'],p,stage['state'],stage['time']) for p in itertools.combinations(sorted(stage['state']),2)]
        stage['counts']=checked.summarize(stage['pairs'])
    s['continuity']=checked.assess_continuity(s['stages'],[]);s['continuity_status']=checked.continuity_status(s['continuity'])
    end=checked.advance(s['stages'][-1]['state']);first=s['stages'][0]['state'];s['positions_restored']=set(end)==set(first) and all(end[n]['lo']==first[n]['lo'] and end[n]['hi']==first[n]['hi'] for n in first)
    return s


def replaced(base,motions,evaluator):
    s=copy.deepcopy(base);current=copy.deepcopy(s['stages'][0]['state'])
    for i,stage in enumerate(s['stages']):
        state=copy.deepcopy(current)
        for body in state.values():body['delta']=['0','0','0']
        if 0<i<len(s['stages'])-1:
            for name,delta in motions[i-1]:state[name]['delta']=list(map(str,delta))
        stage['state']=state;current=checked.advance(state)
    return refresh(s,evaluator)


def counterexamples(data,scenes,evaluator,compounds=True):
    def scene(v,case):return next(s for s in scenes if s['variant']==v and s['case']=='service_fp_'+case)
    lift=config(data,'service_lift');side=config(data,'doser_service_y');z=F(0);result=[]
    for v in 'AB':
        s=replaced(scene(v,'doser_retract_lift'),[[('doser_slide',(z,z,z))],[('doser_slide',(z,z,lift))],[('doser_slide',(z,z,-lift))],[('doser_slide',(z,z,z))]],evaluator)
        result.append((v+'_new_service_with_retract_omitted',s,'BLOCKED'))
    s=replaced(scene('A','doser_retract_lift'),[[('doser_slide',(z,z,lift))],[('doser_slide',(z,side,z))],[('doser_slide',(z,z,-lift))],[('doser_slide',(z,-side,z))]],evaluator);result.append(('A_lift_before_retract',s,'BLOCKED'))
    names=('hydraulic_tank','pump_motor','motor_mount_rear');s=replaced(scene('A','powerpack_module'),[[(n,(z,z,lift)) for n in names],[(n,(z,z,-lift)) for n in names]],evaluator);result.append(('A_powerpack_module_missing_moving_front_plate',s,'BLOCKED'))
    s=copy.deepcopy(scene('A','motor'));s['stages'][1]['state']['pump_motor']['motion']='rotation';result.append(('A_unsupported_motor_motion',refresh(s,evaluator),'INDETERMINATE'))
    if compounds:
        s=copy.deepcopy(result[3][1]);s['stages'][1]['state']['pump_motor']['motion']='rotation';result.append(('compound_rotation_and_stationary_front_plate',refresh(s,evaluator),'BLOCKED'))
        s=copy.deepcopy(result[0][1]);s['stages'][2]['state']['pump_motor']['delta']=None;result.append(('compound_unknown_delta_and_proven_doser_collision',refresh(s,evaluator),'BLOCKED'))
        s=copy.deepcopy(result[4][1]);s['stages'][1]['pairs']=s['stages'][1]['pairs'][:-1];result.append(('compound_unknown_method_and_missing_pair',s,'INDETERMINATE'))
        s=copy.deepcopy(scene('A','motor'));s['stages'][1]['state']['pump_motor']['delta']=None;result.append(('unknown_delta_without_proven_collision',refresh(s,evaluator),'INDETERMINATE'))
    return result
