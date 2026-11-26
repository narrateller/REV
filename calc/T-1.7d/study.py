"""Compare the T-1.7d outlet levers and build one provisional engineering package."""
from copy import deepcopy
from dataclasses import asdict
import json
from math import pi
from pathlib import Path
import sys

import yaml

from cylinders import cylinder_delta, opening
from layout import layout
from mass_budget import plate_kg, update_budget

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FEA = HERE/'fea'
sys.path[:0] = [str(HERE/'cycle'),str(FEA)]
from contact_hex_slice import Slice, solve as slice_fea
from evaluate import assess, gate_module
from frame_fea import fkm_parameters


TRIAL = dict(thickness_mm=44.,travel_mm=87.,wing_mm=12.,runout_length_mm=14.,runout_depth_mm=.15)
CASES = (
    Slice('baseline'),
    *(Slice(f'thick{t}',float(t)) for t in (45,55,60,65)),
    Slice('wide95',travel_mm=95.),
    Slice('wide95_ease',travel_mm=95.,relief_depth_mm=.15,relief_length_mm=14.),
    Slice('wide95_ease2',travel_mm=95.,relief_depth_mm=.30,relief_length_mm=22.),
    Slice('step',38.,95.,.15,14.,16.),
    Slice('combined',44.,88.,.15,14.,12.),
    Slice('wide95_thick55',55.,95.,.15,14.),
    Slice('cycle_limit_slice',44.,87.,.15,14.),
    Slice('lower_cycle',42.,85.,.15,14.),
)
RISK = {
    'baseline':'Перемычка под камерой 10,5 мм, опирание до окна.',
    'thickness':'Увеличивает перебег. Ширина нижнего пятна остаётся ограниченной закрытым окном.',
    'span':'Исторический боковой пролёт 258 мм. Проход ограничивает внутреннюю ширину опор 158 мм; рост хода шибера расширяет нижнюю полосу.',
    'bearing':'Сбег уменьшает пик ценой переноса реакции от контура. Упрочнение не зачислено в прочность сердцевины.',
    'step':'Уступ служит экраном. Требуются направляющие, подход инструмента и проверка напряжения в переходе.',
    'combined':'Цикл близок к пределу. Открыты контактные кромки, допуск хвоста, монтаж направляющих.',
    'material':'Свойства только для гарантированного размера поковки с контролем зоны отбора.',
}

GROUP = {
    'baseline':'baseline','wide95':'span','wide95_ease':'bearing','wide95_ease2':'bearing',
    'step':'step','combined':'combined','wide95_thick55':'combined','cycle_limit_slice':'combined','lower_cycle':'combined',
}


def read_yaml(path):
    return yaml.safe_load((ROOT/path).read_text(encoding='utf-8-sig'))


def read_json(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))


def write_yaml(path, data, comment=''):
    (ROOT/path).write_text(comment+yaml.safe_dump(data,allow_unicode=True,sort_keys=False),
                           encoding='utf-8',newline='\n')


def write_json(path, data):
    (ROOT/path).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',
                           encoding='utf-8',newline='\n')


def cylinders_for(geometry, diameter_mm, cylinders):
    main_add_mm = geometry['main_stroke_increment_mm']
    gate_add_mm = geometry['gate_working_travel_mm']-75.
    changes, details = [], []
    for ident in ('CY-MAIN','CY-RAPID','CY-GATE'):
        row = cylinders[ident]
        addition_mm = main_add_mm if ident!='CY-GATE' else gate_add_mm
        settings = dict(bore_mm=diameter_mm) if ident=='CY-GATE' else {}
        delta, proof = cylinder_delta(row,addition_mm,addition_mm,addition_mm,**settings)
        if set(delta)-{'id'}:
            changes.append(delta)
            details.append(dict(id=ident,**proof))
    return changes, details


def case_setup(inputs, thickness_mm, travel_mm, wing_mm, shoulder='side', axial_allowance_mm=0., gate_accel_m_s2=20., gate_speed_m_s=.60):
    frame, upstream, product, recovery, cylinders, opening_data, mass_data = inputs
    geometry = layout(frame,upstream,product,recovery,thickness_mm,travel_mm,axial_allowance_mm)
    plate_mass_kg = plate_kg(thickness_mm,travel_mm,wing_mm,shoulder)
    rapid_mass_add_kg = (pi/4*(200.**2+2*50.**2)*geometry['main_stroke_increment_mm']*7.85e-6)
    gate_rod_add_kg = pi/4*45.**2*(travel_mm-75.)*7.85e-6
    moving_mass_kg = 45.+plate_mass_kg-plate_kg(38.,75.)+gate_rod_add_kg
    main_area_mm2 = cylinders['CY-MAIN']['cap_area_mm2']
    checks = {}
    bore_mm = 80
    while True:
        check = opening(bore_mm,45.,moving_mass_kg,opening_data,main_area_mm2,
                        accel_m_s2=gate_accel_m_s2, speed_m_s=gate_speed_m_s)
        checks[bore_mm] = check
        if check['safety_factor']>=2.:
            break
        bore_mm += 1
    changes, details = cylinders_for(geometry,bore_mm,cylinders)
    mass = update_budget(mass_data,geometry,plate_mass_kg,details)
    return dict(geometry=geometry,plate_mass_kg=plate_mass_kg,moving_mass_kg=moving_mass_kg,
                rapid_mass_increment_kg=rapid_mass_add_kg,gate_bore_mm=bore_mm,opening=checks,
                cylinder_delta_rows=changes,cylinder_sizing=details,mass=mass)


def diagnostic_summary(case):
    path = FEA/f'{case.label}_slice_0.json'
    if not path.exists():
        return None
    solved = read_json(path)
    factor = min(p['static_factor'] for p in solved['regions'].values())
    fatigue = min(p['fatigue_factor'] for p in solved['regions'].values())
    rp_ratio = .875 if case.thickness_mm+case.wing_thickness_mm>60. else 1.
    allowable, _, _, _ = fkm_parameters(900. if rp_ratio<1. else 1000.,6.3,False,forging=True)
    standard_allowable, _, _, _ = fkm_parameters(1000.,6.3,False,forging=True)
    if rp_ratio<1.:
        # Rescale the plate only. Recompute the positive-mean slope separately
        # in the source screen for the limiting 65 mm section where needed.
        factor = min(factor, rp_ratio*solved['regions']['blade']['static_factor'])
        fatigue = min(fatigue, allowable/standard_allowable*solved['regions']['blade']['fatigue_factor'])
    return dict(static_factor=factor,fatigue_factor_n_sigma_1=fatigue,
                contact_pressure_MPa=solved['loads']['static']['contact_pressure_MPa'],
                FEA_path=str(path.relative_to(ROOT)).replace('\\','/'))


def compare(inputs, baseline):
    table = []
    for case in CASES:
        setup = case_setup(inputs,case.thickness_mm,case.travel_mm,case.wing_thickness_mm,'central_bound')
        detailed = case.label in ('lower_cycle','wide95_thick55')
        summary,_ = assess(setup['geometry'],setup['moving_mass_kg'],detailed=detailed,
                           gate_bore_mm=setup['gate_bore_mm'],
                           rapid_mass_increment_kg=setup['rapid_mass_increment_kg'])
        groups = 'thickness' if case.label.startswith('thick') else GROUP[case.label]
        row = dict(**asdict(case),lever=groups,risk=RISK[groups],
                   main_add_mm=setup['geometry']['main_stroke_increment_mm'],
                   lower_land_available_mm=setup['geometry']['closed_window_ligament_to_chamber_mm']-.5,
                   mass_delta_kg=setup['mass']['delta_kg'],cycle_delta_s=summary['gate_cycle_s']-baseline['gate_cycle_s'],
                   gate_cycle_s=summary['gate_cycle_s'],gate_status=summary['gate_status'],screen=diagnostic_summary(case))
        if detailed:
            row.update(realistic_cycle_s=summary['realistic'].get('cycle_s'),
                       pessimistic_cycle_s=summary['pessimistic'].get('cycle_s'))
        table.append(row)
    screened_baseline = table[0]['screen']
    if screened_baseline:
        for row in table:
            if row['screen']:
                row['static_factor_delta'] = row['screen']['static_factor']-screened_baseline['static_factor']
                row['fatigue_factor_delta'] = row['screen']['fatigue_factor_n_sigma_1']-screened_baseline['fatigue_factor_n_sigma_1']
                row['contact_pressure_delta_MPa'] = row['screen']['contact_pressure_MPa']-screened_baseline['contact_pressure_MPa']
    rm0 = fkm_parameters(1000.,6.3,False,forging=True)[0]
    rm1 = fkm_parameters(900.,6.3,False,forging=True)[0]
    table.append(dict(label='42CrMo4_QT',lever='material',risk=RISK['material'],main_add_mm=0.,
                      mass_delta_kg=0.,cycle_delta_s=0.,static_factor_multiplier=650./800.,
                      FKM_design_amplitude_multiplier=rm1/rm0,bearing_screen_MPa=390.))
    return table


def fea_summary():
    names = {'surface_contact':'cycle_limit','node_contact':'cycle_node','direct_contact':'cycle_direct',
             'seat_tie_screen':'cycle_tied','rigid_back_screen':'rigid','one_way_cast':'one_way_cast'}
    output = {}
    for key, prefix in names.items():
        files = sorted(FEA.glob(f'{prefix}_[0-2].json'))
        if files:
            results = [read_json(path) for path in files]
            output[key] = dict(files=[path.name for path in files],finest=results[-1],convergence_max=None)
            if all('FKM_factor' in r for r in results[-1]['regions'].values()) and len(results)==3:
                seq = []
                for row in results:
                    seq.append([row['loads']['static'][pair]['peak_MPa'] for pair in ('blade_seat','seat_cast')]+
                               [r[k] for r in row['regions'].values() for k in ('static_factor','FKM_factor')])
                output[key]['convergence_max'] = max(abs(x-y)/abs(y) for a,b in zip(seq,seq[1:])
                                                     for x,y in zip(a,b,strict=True) if y)
            if key=='one_way_cast' and len(results)==3:
                seq = [[r[k] for r in row['regions'].values() for k in ('static_factor','fatigue_factor')] +
                       [row['clearance']['combined_screen_mm']] for row in results]
                output[key]['convergence_max'] = max(abs(x-y)/abs(y) for a,b in zip(seq,seq[1:])
                                                     for x,y in zip(a,b,strict=True) if y)
    for label in ('wide95_thick55','cycle_limit_slice'):
        files=sorted(FEA.glob(f'{label}_slice_[0-2].json'))
        if len(files)!=3:
            continue
        results=[read_json(path) for path in files]
        samples=[[row['loads']['static']['contact_pressure_MPa']]+
                 [part[key] for part in row['regions'].values() for key in ('static_factor','fatigue_factor')]
                 for row in results]
        error = max(abs(x-y)/abs(y) for a,b in zip(samples,samples[1:])
                    for x,y in zip(a,b,strict=True) if y)
        output[label+'_diagnostic'] = dict(files=[file.name for file in files],finest=results[-1],
                                           convergence_max=error)
    return output


def design_outputs(frame, setup, cycle, candidate, proofs, status, trial=None, engineering=None):
    trial = TRIAL if trial is None else trial
    g = setup['geometry']
    thickness_mm = g['closed_gate_thickness_mm']
    t17c = read_yaml('design/slide_gate.t17c.yaml')
    f = deepcopy(frame)
    f.update(task='T-1.7d',status=status,stage='S1-str',trial_only=True)
    f.pop('round',None)
    f['columns']['smooth_span_mm'] = g['column_smooth_span_mm']
    f['interfaces']['inner_bearing_planes_spacing_mm'] = g['inner_bearing_spacing_mm']
    f['interfaces']['open_discharge_bay_mm'] = 0.
    for key in ('discharge_rails_clear_width_mm','discharge_rail_cross_section_mm','minimum_rectangular_outlet_mm'):
        f['interfaces'].pop(key,None)
    f['interfaces']['clear_channel_width_height_radius_mm'] = [158.,65.,3.]
    f['interfaces']['clear_channel_length_mm'] = 205.
    f['interfaces']['guide_reference_plane'] = 'Обработанные общие базы на модуле камеры. Плечо до пуансона 77 мм.'
    f['interfaces']['layout']['guide_station_at_installed_stroke_mm'] += g['main_stroke_increment_mm']
    f['interfaces']['layout']['punch_station_at_installed_stroke_mm'] += g['main_stroke_increment_mm']
    f['interfaces']['layout'].update(frame_axial_length_mm=g['frame_axial_length_mm'],
                                     rear_cylinder_projection_to_mount_mm=frame['interfaces']['layout']['rear_cylinder_projection_to_mount_mm']+
                                     g['main_stroke_increment_mm'],
                                     module_axial_excluding_ZSF_and_safety_guards_mm=g['module_envelope_xyz_mm'][0])
    f['geometry'] = g
    f['mass_budget'] = setup['mass']
    f.pop('results',None)
    f['checks'] = {key:{'files':result['files'],'convergence_max':result['convergence_max']}
                   for key,result in proofs.items()}
    t17c.update(task='T-1.7d',status=status,trial_only=True,face_x_mm=g['gate_face_x_mm'],
                back_x_mm=g['gate_back_x_mm'],thickness_mm=thickness_mm,
                plate_outline_mm_R=[260.,212.+trial['travel_mm']-75.,5.],
                plate_outline_center_y_mm=-18.-(trial['travel_mm']-75.)/2,
                window_center_y_closed_open_mm=[g['closed_window_center_y_mm'],g['open_window_center_y_mm']],
                opening_travel_mm=g['gate_working_travel_mm'],
                installed_gate_cylinder_stroke_mm=g['gate_working_travel_mm']+5.,
                swept_plate_vertical_limits_mm=[-124.-(trial['travel_mm']-75.),88.+trial['travel_mm']],
                side_rib_max_front_projection_x_mm=g['gate_face_x_mm']-trial['wing_mm'],
                overtravel_mm=[g['overtravel_nominal_mm'],g['overtravel_maximum_mm']],
                minimum_relaxed_tail_clearance_mm=g['minimum_relaxed_tail_clearance_mm'],
                gate_cylinder_bore_rod_mm=[setup['gate_bore_mm'],45.],
                gate_opening=setup['opening'],axial_wing_height_mm=trial['wing_mm'],
                axial_wing_start_abs_y_cross_mm=80.,axial_wing_full_abs_y_cross_mm=125.,
                insert_relief_length_mm=trial['runout_length_mm'],
                insert_relief_depth_mm=trial['runout_depth_mm'],
                insert_recess_mm=55.,channel_length_mm=205.,channel_section_mm_R=[158.,65.,3.],
                minimum_clearance_datum='Зазор рассчитан в номинальной геометрии. Допуски и динамика закрытия требуют проверки.',
                fea_summary='calc/T-1.7d/results.json / fea',
                risk='Боковые рёбра выступают к камере. Карманы от |y|=80 мм по всему рабочему ходу подлежат проверке.')
    for key in ('seat_opening_and_hand_screen','round','acceptance','selected_variant'):
        t17c.pop(key,None)
    if engineering:
        f['interfaces']['replaceable_bearing'] = engineering['bearing']
        t17c['bearing_pair'] = engineering['bearing']
        t17c['drive_requirements'] = engineering['hydraulic']
        t17c['minimum_clearance_datum'] = 'Зазор проверен с указанным расчётным бюджетом допусков. Бюджет подтверждается размерной цепью и стендом.'
        for row in setup['cylinder_delta_rows']:
            if row['id']=='CY-GATE':
                row['work_port_passage_ID_mm'] = engineering['hydraulic']['minimum_work_passage_ID_mm']
                row['end_cushion_requirements'] = engineering['hydraulic']['cushion']
    write_yaml('design/frame.t17d.yaml',f)
    write_yaml('design/slide_gate.t17d.yaml',t17c)
    write_yaml('design/cylinders.t17d.yaml',dict(task='T-1.7d',status=status,trial_only=True,
               inherit_unchanged_from='design/cylinders.t16.yaml',cylinders=setup['cylinder_delta_rows']))
    write_yaml('design/params.t17d.yaml',candidate,
               '# T-1.7d working trial, generated by calc/T-1.7d/study.py.\n'
               '# G-CYCLE virtual rod and movements preserve phase oil volumes.\n')


def load_inputs():
    gate = gate_module()
    criteria = gate.read_criteria((ROOT/'ops/criteria/design_criteria.yaml').read_bytes())['criteria']
    frame = read_yaml('design/frame.t17.yaml')
    cylinders = {r['id']:r for r in read_yaml('design/cylinders.t16.yaml')['cylinders']}
    base = read_json('calc/T-1.7c/results.json')
    inputs = (frame,read_json('calc/T-1.2b/results.json'),criteria['C-PROD-01'],
              read_yaml('calc/T-1.1/curve.yaml'),cylinders,
              read_yaml('design/slide_gate.t17b.yaml')['opening_force_screen'],base['mass'])
    return gate, criteria, base, inputs


def main():
    if '--run-slices' in sys.argv:
        for case in CASES:
            for level in ((0,1,2) if case.label in ('wide95_thick55','cycle_limit_slice') else (0,)):
                slice_fea(level,case)
    gate, criteria, base, inputs = load_inputs()
    frame = inputs[0]
    baseline, _ = assess(base['layout'],45.,detailed=True)
    setup = case_setup(inputs,TRIAL['thickness_mm'],TRIAL['travel_mm'],TRIAL['wing_mm'])
    cycle,candidate = assess(setup['geometry'],setup['moving_mass_kg'],detailed=True,
                             gate_bore_mm=setup['gate_bore_mm'],rapid_mass_increment_kg=setup['rapid_mass_increment_kg'])
    gates = {key:{'status':row['status'],'value':row['value']}
             for key,func in gate.GATES.items() for row in [func(candidate,criteria)]}
    comparisons = compare(inputs,baseline)
    proofs = fea_summary()
    status = 'HOLD_NO_QUALIFIED_DESIGN'
    accepted = dict(C_STR_01='OPEN',C_FAT_01='OPEN',bearing_contact='FAIL_RIGID_BACK_SCREEN'
                    if 'rigid_back_screen' in proofs else 'OPEN',three_mesh_convergence='OPEN',
                    R20_and_chamber_end='OPEN',C_CLR_01='OPEN',
                    G_CYCLE=gates['G-CYCLE']['status'],reference_cycle='PASS',pessimistic_reference='FAIL')
    result = dict(task='T-1.7d',status=status,comparison=comparisons,baseline_cycle=baseline,
                  working_trial=dict(**setup,geometric_FEA_inputs=TRIAL,cycle=cycle),
                  gates=gates,fea=proofs,acceptance=accepted,solutions_qualified=0)
    write_json('calc/T-1.7d/results.json',result)
    design_outputs(frame,setup,cycle,candidate,proofs,status)
    geom = setup['geometry']
    write_json('metrics.json',dict(task='T-1.7d',status=status,working_trial=True,
               plate_thickness_mm=geom['closed_gate_thickness_mm'],
               main_stroke_increment_mm=geom['main_stroke_increment_mm'],
               installed_stroke_mm=geom['main_installed_stroke_mm'],
               overtravel_mm=[geom['overtravel_nominal_mm'],geom['overtravel_maximum_mm']],
               minimum_tail_clearance_mm=geom['minimum_relaxed_tail_clearance_mm'],
               channel_length_mm=geom['channel_length_mm'],gate_stroke_mm=geom['gate_working_travel_mm'],
               gate_actuator=setup['opening'][setup['gate_bore_mm']],gate_bore_mm=setup['gate_bore_mm'],
               nominal_mass_kg=setup['mass']['nominal_kg'],mass_range_kg=[setup['mass']['lower_kg'],setup['mass']['upper_kg']],
               cycle_s=cycle['gate_cycle_s'],reference_cycle_s=cycle['realistic']['cycle_s'],
               pessimistic_reference_cycle_s=cycle['pessimistic'].get('cycle_s'),
               cycle_margin_s=cycle['gate_margin_s'],reference_cycle_margin_s=cycle['reference_margin_s'],
               gates=gates,acceptance=accepted,
               rigid_screen=proofs.get('rigid_back_screen',{}).get('finest'),
               cast_transfer_screen=proofs.get('one_way_cast',{}).get('finest'),
               fea_files={name:details['files'] for name,details in proofs.items()}))


if __name__=='__main__':
    if '--round1' in sys.argv or '--run-slices' in sys.argv:
        main()
    else:
        from round2 import main as round2
        round2()

