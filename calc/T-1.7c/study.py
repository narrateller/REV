"""Round-two free-channel calculation and its T-1.4b hydraulic projection."""
import json
from dataclasses import replace
from math import sqrt
from pathlib import Path
import sys

import yaml

from layout import layout
from mass_budget import budget
from screens import gate_screen
from stack import from_reference

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0,str(HERE/'cycle'))
sys.path.insert(0,str(HERE/'fea'))

from contact import BLADE_MM, POCKET_MM, POCKET_R_MM, RELIEF_MM, RELIEF_DEPTH_MM
from drive import configuration, get_inputs, periodic_run, scenario, source_data
from make_params_t14b import gate_module, make_candidate
from x1_calc import BAR_PA, Cylinder, supply_bar

DT_S = .000625
FEED_S = .64
BULK_KG_M3 = 90.
LIMIT_KW = 36.


def read_yaml(name):
    return yaml.safe_load((ROOT/name).read_text(encoding='utf-8-sig'))


def read_json(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))


def write_json(name,data):
    (ROOT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
                           encoding='utf-8',newline='\n')


def compact_cycle(run):
    if not run['feasible']:
        return run
    events=run['motion_events']
    eject=events['eject']
    return dict(feasible=True,cycle_s=run['cycle_s'],eject_motion_s=eject['end_s']-eject['start_s'],
                eject_start_s=eject['start_s'], gate_open_end_s=events['gate_open']['end_s'],
                main_travel_mm=run['main_travel_mm'],peak_working_bar=run['peak_working_bar'],
                mean_shaft_kW=run['average_shaft_kW'],rms_shaft_kW=run['rms_shaft_kW'],peak_shaft_kW=run['peak_shaft_kW'])


def evaluated(model, main, settings, dt_s=DT_S):
    return compact_cycle(periodic_run(model,main,BULK_KG_M3,FEED_S,settings,dt_s))


def calculation():
    inputs=get_inputs()
    upstream=inputs[0]
    curve=read_yaml('calc/T-1.1/curve.yaml')
    criteria=read_yaml('ops/criteria/design_criteria.yaml')['criteria']
    sources=read_yaml('calc/T-1.7c/sources.yaml')
    assumptions=sources['round_2_assumptions']
    frame=read_yaml('design/frame.t17.yaml')
    geom=layout(frame,upstream,criteria['C-PROD-01'],curve)
    mass=budget(frame,read_json('calc/T-1.7/results.json'),geom,
                {'seat_outline_mm_R':[*POCKET_MM,POCKET_R_MM],'blade_outline_mm_R':[*BLADE_MM,5.]})
    hyd=configuration(inputs,data=source_data(),limit_kW=LIMIT_KW)
    ref,main,settings,projection,charge=hyd
    historic=read_yaml('design/slide_gate.t17b.yaml')
    cylinders={row['id']:row for row in read_yaml('design/cylinders.t16.yaml')['cylinders']}
    gate=gate_screen(geom,upstream,historic,cylinders['CY-MAIN'],ref.gate_mass_kg)
    gate['edge_relief_width_mm'],gate['edge_relief_depth_mm']=RELIEF_MM,RELIEF_DEPTH_MM
    data=settings['prefill']
    rapid=Cylinder(data['bore_mm']*sqrt(data['count']),data['rod_mm']*sqrt(data['count']),main.stroke_mm,data['eta'])
    limit_bar=criteria['C-HYD-01']['max_working_bar']
    inlet_bar,tank_bar,_=ref.losses_bar
    rapid_N=rapid.eta*BAR_PA*((limit_bar-inlet_bar)*rapid.cap_m2-tank_bar*rapid.annulus_m2)
    guide_drag_N=1000*data['main_float_drag_kN']
    residual_friction_N=gate['contact_steel_pair_mu']*(
        gate['opening_main_hydraulic_residual_N']+gate['opening_product_residual_screen_N'])
    loaded_config=replace(ref,gate_open_residual_friction_N=residual_friction_N,gate_open_weight_N=9.81*ref.gate_mass_kg)
    tests=[]
    option={}
    for material_case in ('base','high'):
        source_model,_=scenario(inputs,case=material_case,gate_m_s=ref.gate_speed_m_s,losses_bar=ref.losses_bar)
        model=replace(loaded_config,case=material_case,in_die_kg_m3=source_model.in_die_kg_m3,
                      overtravel_m=source_model.overtravel_m)
        for side, i in (('lower',0),('upper',1)):
            mu=sources['friction_briquette_channel']['engineering_envelope']['mu'][i]
            crumbs_N=assumptions['debris_breakaway_allowance_N']['value'][i]
            normal_weight_ratio=assumptions['guide_normal_to_weight_screen']['value'][i]
            stack,density_kg_m3=from_reference(upstream,geom,model,mu,crumbs_N,material_case,normal_weight_ratio,'nominal')
            variant=replace(model,stack_force_N=stack.force_N)
            peak_N,at_mm=stack.peak(guide_drag_N)
            tests.append(dict(curve=material_case,bound=side,mu=mu,debris_N=crumbs_N,
                              residual_radial_pressure_MPa=stack.local_pressure_MPa,
                              closed_gate_stack_force_on_dose_N=0.,free_density_kg_m3=density_kg_m3,
                              predicted_relaxed_length_mm=stack.die_length_mm+stack.growth_mm,
                              axial_growth_mm=stack.growth_mm,
                              guide_force_from_weight_N=stack.gravity_force_N,transition_friction_N=stack.local_force_N,
                              max_added_resistance_upper_bound_N=stack.gravity_force_N+crumbs_N+stack.local_force_N,
                              ejection_peak_N=peak_N,ejection_peak_at_mm=at_mm,
                              peak_with_inertia_bound_N=peak_N+model.rapid_mass_kg*model.rapid_accel_m_s2,
                              rapid_required_bar=supply_bar(rapid,peak_N+model.rapid_mass_kg*model.rapid_accel_m_s2,
                                                            'extend',model.losses_bar),
                              engagement_mm=stack.engagement_mm,eject_travel_mm=stack.stroke_mm,
                              time_steps_s=[2*DT_S,DT_S],
                              cycles=[evaluated(variant,main,settings,2*DT_S),evaluated(variant,main,settings)]))
            if (material_case,side)==('base','upper'):
                option=dict(stack=stack,model=model,variant=variant)

    stack=option['stack']
    model=option['model']
    limit_cycle_s=criteria['C-PERF-01']['max_cycle_s']
    lo_MPa=0.
    hi_MPa=(rapid_N-guide_drag_N)/(stack.mu*stack.perimeter_mm*stack.length_mm)
    for _ in range(12):
        mid_MPa=(lo_MPa+hi_MPa)/2
        trial=replace(stack,effective_wall_pressure_MPa=mid_MPa)
        run=evaluated(replace(model,stack_force_N=trial.force_N),main,settings)
        if run['feasible'] and run['cycle_s']<=limit_cycle_s:
            lo_MPa=mid_MPa
        else:
            hi_MPa=mid_MPa
    sensitivity=dict(pressure_bracket_for_6s_MPa=[lo_MPa,hi_MPa],mu=stack.mu,occupied_wall_length_mm=stack.length_mm,
                     added_wall_friction_at_boundary_N=lo_MPa*stack.mu*stack.perimeter_mm*stack.length_mm)
    pess_ref,pess_main,pess_settings,*_=configuration(inputs,data=source_data(),profile='pessimistic',limit_kW=LIMIT_KW)
    pess=replace(pess_ref,gate_open_residual_friction_N=residual_friction_N,
                 gate_open_weight_N=loaded_config.gate_open_weight_N,stack_force_N=stack.force_N)
    pessimistic=evaluated(pess,pess_main,pess_settings)
    result=dict(task='T-1.7c',round=2,selected_variant=1,layout=geom,mass=mass,
                nominal_press_force_N=ref.nominal_N,nominal_press_face_MPa=ref.nominal_N/(ref.section_m2*1e6),
                free_channel_cases=tests,reference_bare_cycle=evaluated(ref,main,settings),
                upper_pessimistic_cycle=pessimistic,pressure_sensitivity=sensitivity,
                limit_cycle_s=limit_cycle_s,rapid_pair_available_N=rapid_N,guide_drag_N=guide_drag_N,
                gate_opening=gate,reference_gate_input='design/params.t14b.yaml',
                previous_comparison=assumptions['accepted_round_1_comparison'])
    gate_evaluator=gate_module()
    gate_criteria=gate_evaluator.read_criteria((ROOT/'ops/criteria/design_criteria.yaml').read_bytes())['criteria']
    published=read_yaml('design/params.t14b.yaml')
    published_kW=published['drive']['peak_kW']
    result['reference_comparison'] = {
        'G_CYCLE_T14b_published_kW':published_kW,
        'G_CYCLE_T14b_published_s':gate_evaluator.evaluate_cycle(published,gate_criteria)['value'],
        'G_CYCLE_T14b_same_power_kW':LIMIT_KW,
        'G_CYCLE_T14b_same_power_s':gate_evaluator.evaluate_cycle(make_candidate(inputs,hyd),gate_criteria)['value'],
    }
    operating=make_candidate(inputs,(option['variant'],main,settings,projection,charge))
    operating['description']=(
        'T-1.7c R2, свободный канал и оконный шибер. Base 90 кг/м³, 0,83 кг, подача 0,64 с, верхняя вилка. '
        'Координаты движения гидравлические, физический ход 289 мм. Рабочая уставка 36 кВт по D-GK-02.'
    )
    _, ref_main, ref_settings, ref_projection, ref_charge=configuration(inputs,data=source_data(),limit_kW=published_kW)
    comparison=make_candidate(inputs,(option['variant'],ref_main,ref_settings,ref_projection,ref_charge))
    normalized=gate_evaluator.evaluate_cycle(comparison,gate_criteria)
    result['reference_comparison']['normalized_t17c_at_published_power']={
        'shaft_kW':published_kW,'G_CYCLE_s':normalized['value'],'gate_result':normalized['status'],
        'shaft_rms_kW':normalized['details']['rms_power_kW'],
    }
    return result,operating


def main():
    result,operating=calculation()
    write_json('calc/T-1.7c/results.json',result)
    (ROOT/'design/params.t17c.yaml').write_text(
        '# Generated by calc/T-1.7c/study.py from the copied T-1.4b cycle projection.\n'
        +yaml.safe_dump(operating,allow_unicode=True,sort_keys=False),encoding='utf-8',newline='\n')


if __name__=='__main__':
    main()

