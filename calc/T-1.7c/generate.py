"""Write the review snapshots and machine-readable headline results."""

import yaml

from study import HERE, ROOT, read_json, write_json

FEA = HERE/'fea'


def write_yaml(name,data):
    (ROOT/name).write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False),
                           encoding='utf-8',newline='\n')


def meshes(pattern):
    return [read_json(str(path.relative_to(ROOT))) for path in sorted(FEA.glob(pattern))]


def convergence(series):
    if len(series)!=3:
        return None
    return max(abs(a-b)/abs(b)
               for earlier,later in zip(series,series[1:])
               for a,b in zip(earlier,later,strict=True) if b)


def fea_status():
    penalty=meshes('penalty_[0-2].json')
    mortar=meshes('mortar_[0-2].json')
    local=meshes('local_[0-2].json')
    diagnostic=meshes('hex_slice_[0-2].json')
    coupled=mortar if len(mortar)>len(penalty) else penalty
    series=coupled or local or diagnostic
    finest=series[-1] if series else None
    status={'C_STR_01':'OPEN','C_FAT_01':'OPEN','C_CLR_01':'OPEN',
            'contact_pressure':'OPEN','casting_R20_actual_reactions':'OPEN','three_mesh_convergence':'OPEN'}
    full_convergence=None
    if coupled:
        def compared(row):
            return [row['loads']['static']['max_contact_MPa'],
                    *[r[key] for r in row['regions'].values() for key in ('static_factor','fatigue_factor')]]
        full_convergence=convergence([compared(row) for row in coupled])
        blade,seat=(finest['regions'][key] for key in ('blade','seat'))
        status.update(C_STR_01='FAIL' if min(blade['static_factor'],seat['static_factor'])<1.5 else 'OPEN',
                      C_FAT_01='FAIL' if min(blade['fatigue_factor'],seat['fatigue_factor'])<1. else 'OPEN',
                      contact_pressure='FAIL' if finest['loads']['static']['max_contact_MPa']>finest['bearing_screen_MPa'] else 'OPEN',
                      three_mesh_convergence=('PASS' if full_convergence<.05 else 'FAIL')
                      if full_convergence is not None else 'OPEN')
    elif local:
        blade,seat=(finest['regions'][key] for key in ('blade','seat'))
        pressure=finest['loads']['static']
        status.update(C_STR_01='FAIL_SCREEN' if min(blade['static_factor'],seat['static_factor'])<1.5 else 'OPEN',
                      C_FAT_01='FAIL_SCREEN' if min(blade['fatigue_factor'],seat['fatigue_factor'])<1. else 'OPEN',
                      contact_pressure='FAIL_SCREEN' if pressure['max_contact_MPa']>pressure['bearing_screen_MPa'] else 'OPEN')
    diagnostic_convergence=convergence([
        [row['regions']['blade']['static_factor'],row['regions']['blade']['fatigue_factor'],
         row['loads']['static']['contact_pressure_MPa']] for row in diagnostic
    ])
    return dict(status='ASSEMBLY_PROOF_OPEN',criteria=status,coupled_completed_levels=len(coupled),
                local_completed_levels=len(local),slice_completed_levels=len(diagnostic),
                coupled_max_relative_change=full_convergence,slice_max_relative_change=diagnostic_convergence,
                latest=finest,latest_scope=('full_assembly' if coupled else 'recessed_seat_rigid_backing' if local
                                           else 'plane_strain_slice' if diagnostic else 'hand_screen_only'),
                full_model='calc/T-1.7c/fea/contact.py',rigid_backing_model='calc/T-1.7c/fea/contact_local.py',
                diagnostic_model='calc/T-1.7c/fea/contact_hex_slice.py',
                execution_record='calc/T-1.7c/fea/execution.json',
                solver={'gmsh':'4.15.0','calculix':'2.22','contact_mu':.15,'precision_replay_target':1e-6})


def generate():
    result=read_json('calc/T-1.7c/results.json')
    gates=read_json('gates.t17c.json')
    gate_rows={row['id']:{'status':row['status'],'value':row['value']} for row in gates['gates']}
    reference=result['reference_comparison']
    official_delta_s=gate_rows['G-CYCLE']['value']-reference['G_CYCLE_T14b_published_s']
    like_for_like_delta_s=gate_rows['G-CYCLE']['value']-reference['G_CYCLE_T14b_same_power_s']
    geometry=result['layout']
    mass=result['mass']
    opening=result['gate_opening']
    cases=result['free_channel_cases']
    upper=next(row for row in cases if (row['curve'],row['bound'])==('base','upper'))
    fea=fea_status()
    active_status='STOP_STRUCTURE_REQUIRES_PROOF'
    if mass['nominal_kg']>mass['limit_kg']:
        active_status='STOP_MASS'
    elif max(row['peak_with_inertia_bound_N'] for row in cases)>result['rapid_pair_available_N'] or (
            not upper['cycles'][-1]['feasible'] or upper['cycles'][-1]['cycle_s']>result['limit_cycle_s']):
        active_status='STOP_EJECTION'
    elif fea['criteria']['C_FAT_01']=='FAIL':
        active_status='STOP_GATE_FATIGUE'
    elif fea['criteria']['C_FAT_01']=='FAIL_SCREEN':
        active_status='STOP_GATE_FATIGUE_SCREEN'
    status=dict(task=result['task'],round=2,selected_variant=1,status=active_status,acceptance=fea['criteria'])
    outlet_acceptance={
        'rapid_ejection': 'PASS' if upper['peak_with_inertia_bound_N']<=result['rapid_pair_available_N'] else 'FAIL',
        'C_PERF_01': 'PASS' if upper['cycles'][-1]['feasible'] and upper['cycles'][-1]['cycle_s']<=result['limit_cycle_s'] else 'FAIL',
        'C_PROD_01_and_C_PROD_03': 'OPEN_STAND_MEASUREMENTS',
        'mass_4850_kg': 'PASS' if mass['nominal_kg']<=mass['target_kg'] else 'FAIL',
        'mass_5000_kg_nominal': 'PASS' if mass['nominal_kg']<=mass['limit_kg'] else 'FAIL',
        'mass_5000_kg_upper_estimate': 'PASS' if mass['upper_kg']<=mass['limit_kg'] else 'FAIL',
        'cycle_delta_from_published_0p15_s': 'PASS' if abs(official_delta_s)<=.15 else 'FAIL',
        'cycle_delta_same_power_0p15_s': 'PASS' if abs(like_for_like_delta_s)<=.15 else 'FAIL',
    }
    write_yaml('design/frame.t17c.yaml',{
        **status,'reference':'design/frame.t17.yaml',
        'geometry':geometry,'mass_budget':mass,
        'guide_reference':'Обработанные базы переднего модуля камеры, общий установочный комплект пуансона и вкладыша.',
        'clearance_limit_mm':.15,'reference_T17_deflection_mm':.043,
        'overall_machine_envelope_status':'OPEN_FRAME_MODULE_ONLY',
        'required_frame_proof':'Податливость баз с реакциями контакта, горловина расточки, R20, преднатяг и разброс колонн.',
    })
    write_yaml('design/slide_gate.t17c.yaml',{
        **status,'references':['design/slide_gate.t17b.yaml','design/cylinders.t16.yaml'],
        'face_x_mm':geometry['gate_face_x_mm'],'back_x_mm':geometry['gate_back_x_mm'],
        'thickness_mm':geometry['closed_gate_thickness_mm'],'plate_outline_mm_R':[260.,212.,5.],
        'plate_outline_center_y_mm':-18.,'window_width_height_R_mm':[158.,65.,3.],
        'window_center_y_closed_open_mm':[geometry['closed_window_center_y_mm'],geometry['open_window_center_y_mm']],
        'housing_pocket_width_height_R_mm':[340.2,180.2,12.],
        'opening_travel_mm':geometry['gate_working_travel_mm'],
        'overtravel_mm':[geometry['overtravel_nominal_mm'],geometry['overtravel_maximum_mm']],
        'minimum_relaxed_tail_clearance_mm':geometry['minimum_relaxed_tail_clearance_mm'],
        'material':'34CrNiMo6+QT, гарантированные 800/1000 МПа для плоского сечения 20–60 мм.',
        'lateral_guide':'Сменные боковые планки в оконном шибере и канале, согласованный размер под фактическую партию.',
        'seat_opening_and_hand_screen':opening,'fea_summary':'calc/T-1.7c/fea/status.json',
        'interlocks_reference':'design/hydraulics/T-1.6_interlocks.yaml',
    })
    write_json('metrics.json',{
        **status,'outlet_acceptance':outlet_acceptance,'gate_metal_thickness_mm':geometry['closed_gate_thickness_mm'],
        'max_gate_metal_thickness_with_existing_travel_mm':geometry['maximum_gate_thickness_preserving_5mm_axial_margin_mm'],
        'gate_screen_thickness_for_fatigue_factor_1_mm':opening['required_thickness_hand_screen_mm'],
        'minimum_relaxed_tail_clearance_mm':geometry['minimum_relaxed_tail_clearance_mm'],
        'channel_length_mm':geometry['channel_length_mm'],
        'channel_section_mm':geometry['passage_exit_mm'],
        'clearance_in_R20_mm':geometry['guide_corner_clearance_in_cast_R20_mm'],
        'eject_peak_force_N':upper['ejection_peak_N'],
        'eject_peak_force_with_inertia_bound_N':upper['peak_with_inertia_bound_N'],
        'rapid_pair_available_force_N':result['rapid_pair_available_N'],
        'rapid_required_pressure_bar':upper['rapid_required_bar'],
        'eject_time_s':upper['cycles'][-1]['eject_motion_s'],
        'cycle_upper_s':upper['cycles'][-1]['cycle_s'],
        'cycle_upper_pessimistic_s':result['upper_pessimistic_cycle']['cycle_s'],
        'effective_pressure_for_6s_MPa':result['pressure_sensitivity']['pressure_bracket_for_6s_MPa'],
        'mass_nominal_kg':mass['nominal_kg'],'mass_range_kg':[mass['lower_kg'],mass['upper_kg']],
        'max_residual_briquette_force_for_2x_gate_margin_N':opening['opening_max_residual_product_for_factor_2_N'],
        'gate_opening_force_N':opening['opening_force_N'],'gate_opening_factor':opening['opening_force_factor'],
        'gate_delta_same_power_s':like_for_like_delta_s,'gate_delta_published_s':official_delta_s,
        'gate_reference':reference,'gates':gate_rows,'fea':fea,
    })
    write_json('calc/T-1.7c/fea/status.json',fea)


if __name__=='__main__':
    generate()
