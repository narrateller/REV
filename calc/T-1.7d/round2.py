"""Compare the second-round screens and generate the outlet engineering package."""
import sys

from round2_interfaces import hydraulics, support
from study import (FEA, ROOT, Slice, assess, case_setup, design_outputs,
                   fea_summary, fkm_parameters, load_inputs, read_json, slice_fea, write_json)

TRIAL = dict(thickness_mm=54.,travel_mm=100.,wing_mm=6.,runout_length_mm=11.,runout_depth_mm=.10)
AXIAL_ALLOWANCE_MM = 1.
OPTIONS = dict(gate_speed_m_s=1.,gate_accel_m_s2=40.,gate_lp=True,lp_flow_L_min=180.)
SCREEN_CASES = (
    (38,105,14,.15),(38,120,14,.15),(42,104,14,.15),(44,100,14,.15),
    (44,105,14,.15),(47,105,14,.15),(48,106,10,.11),(50,104,14,.15),
    (50,110,12,.12),(52,110,12,.12),(51,115,12,.12),(55,105,14,.15),
    (57,110,12,.12),(51,104,11,.10),(52,100,11,.10),(53,99,11,.10),(54,100,11,.10),(55,96,11,.10),(44,105,9,.07),(44,105,14,.25),(44,105,17,.25),
)


def slice_case(thickness_mm, travel_mm, relief_length_mm, relief_depth_mm):
    label = f'r2_{thickness_mm}_{travel_mm}_{relief_length_mm}_{round(relief_depth_mm*100)}'
    return Slice(label,thickness_mm,travel_mm,relief_depth_mm,relief_length_mm)


def compare_layouts(inputs):
    comparison=[]
    for thickness,travel,length,depth in SCREEN_CASES:
        case=slice_case(thickness,travel,length,depth)
        file=FEA/f'{case.label}_slice_0.json'
        if '--r2-slices' in sys.argv:
            slice_fea(0,case)
        setup=case_setup(inputs,thickness,travel,0.,axial_allowance_mm=AXIAL_ALLOWANCE_MM, gate_accel_m_s2=OPTIONS['gate_accel_m_s2'],
                         gate_speed_m_s=OPTIONS['gate_speed_m_s'])
        cycle,_=calculate_cycle(setup,OPTIONS,detailed=False)
        result=dict(thickness_mm=thickness, gate_stroke_mm=travel, available_lower_land_mm=travel-65,
                    lower_land_runout_mm=[length,depth], delta_main_mm=setup['geometry']['main_stroke_increment_mm'],
                    no_ribs_mass_kg=setup['mass']['nominal_kg'],gate_cycle_screen_s=cycle['gate_cycle_s'],
                    gate_rms_screen_kW=cycle['gate_rms_kW'])
        if file.exists():
            data=read_json(file)
            result.update(fea_file=str(file.relative_to(ROOT).as_posix()),
                          static_contact_MPa=data['loads']['static']['contact_pressure_MPa'],
                          cycling_contact_MPa=data['loads']['fatigue']['contact_pressure_MPa'],
                          FKM=data['r2_regions']['blade'])
        comparison.append(result)
    return comparison


def calculate_cycle(setup, settings, *, detailed=True):
    return assess(setup['geometry'],setup['moving_mass_kg'],detailed=detailed,
                  gate_bore_mm=setup['gate_bore_mm'],rapid_mass_increment_kg=setup['rapid_mass_increment_kg'],
                  **settings)


def compare_cycles(setup):
    levers=(
        ('reference_speed_0p6', {}),
        ('speed_to_1', dict(gate_speed_m_s=1.)),
        ('acceleration_to_40', dict(gate_speed_m_s=1.,gate_accel_m_s2=40.)),
        ('lp_close_220', OPTIONS | {'lp_flow_L_min':220.}),
        ('lp_close_180', OPTIONS),
        ('gate_pump_priority', OPTIONS | {'gate_close_oil_priority':True}),
        ('earlier_close_screen', OPTIONS | {'gate_close_punch_inset_mm':5.}),
        ('gate_loss_sensitivity', OPTIONS | {'gate_losses_bar':(5.,5.,4.)}),
        ('max_residual_product', OPTIONS | {'residual_product_N':201000.}),
    )
    rows={}
    for label,params in levers:
        result,_=calculate_cycle(setup,params)
        if rows:
            baseline=rows['reference_speed_0p6']
            result['delta_gate_from_baseline_s']=result['gate_cycle_s']-baseline['gate_cycle_s']
            result['delta_pessimistic_from_baseline_s']=result['pessimistic']['cycle_s']-baseline['pessimistic']['cycle_s']
        rows[label]=result
    return rows


def fkm_record(row):
    return {name:result for name,result in row['regions'].items() if isinstance(result,dict)}


def mesh_relative_change(rows, key_paths):
    def value(row,path):
        for key in path:
            row=row[key]
        return row

    if len(rows)!=3:
        return None
    return max(abs(value(a,path)-value(b,path))/abs(value(b,path))
               for a,b in zip(rows,rows[1:]) for path in key_paths if value(b,path))


def r2_fea():
    trials={}
    for label in ('r2_rigid','r2_cast','r2_mortar','r2_penalty','r2_aligned_node','r2_aligned_node54','r2_aligned_surface'):
        files=sorted(FEA.glob(f'{label}_[0-5].json'))
        failures=[p.name for p in sorted(FEA.glob(f'{label}_*_failure.json'))]
        if not files and not failures:
            continue
        results=[read_json(f) for f in files]
        levels=[int(p.stem.rsplit('_',1)[-1]) for p in files]
        summary=dict(files=[p.name for p in files]+failures, failures=failures,
                     finest=results[-1] if results else None, convergence_max=None)
        if results:
            paths=[('regions',name,k) for name in fkm_record(results[-1])
                   for k in ('static_factor','fatigue_factor')]
            if label in ('r2_aligned_node','r2_aligned_node54','r2_aligned_surface','r2_penalty','r2_mortar'):
                paths.extend(('loads',step,pair,'peak_MPa') for step in ('static','fatigue')
                             for pair in ('blade_seat','seat_cast'))
                paths.append(('clearance','combined_screen_mm'))
            elif label=='r2_rigid':
                paths.extend(('loads',step,'max_contact_MPa') for step in ('static','fatigue'))
            recent_levels=levels[-3:]
            if len(recent_levels)==3 and recent_levels[-1]-recent_levels[0]==2:
                recent=results[-3:]
                by_metric={'.'.join(path):mesh_relative_change(recent,[path]) for path in paths}
                summary.update(convergence_levels=recent_levels,convergence_by_metric=by_metric,
                               convergence_max=max(by_metric.values()))
            if label=='r2_aligned_node54':
                summary['first_levels_relative_contact_change']=[
                    abs(b['loads']['static']['blade_seat']['peak_MPa']-a['loads']['static']['blade_seat']['peak_MPa'])/
                    abs(b['loads']['static']['blade_seat']['peak_MPa']) for a,b in zip(results,results[1:])]
                results[-1]['clearance']['scope'] = 'Fit of chamber-module datums and insert. Minimum preload imposed at frame cut. Guide tolerances and guide compliance are outside this elastic screen.'
        trials[label]=summary
    return trials


def update_mass(mass, bearing):
    rows=[
        dict(item='Масса заготовки сменной кассеты вместо вставки T-1.7c',
             delta_kg=bearing['calculated_blank_mass_kg']-bearing['baseline_insert_mass_kg'],
             uncertainty_kg=[0.,0.], source='Контур кассеты и окно по round2_interfaces.py; без вычета сбегов.'),
        dict(item='Прижимы и упоры сменной кассеты',delta_kg=bearing['retention_mass_allowance_kg'],
             uncertainty_kg=[-.5,2.],source='Резерв массы, уточнить после разработки прижимов.'),
        dict(item='Увеличенные порты, линия ГА НД к A, демпфирование, датчик хвоста',delta_kg=10.,
             uncertainty_kg=[-5.,10.],source='Эскизная прибавка, резерв на арматуру, масло в линиях и крепления.'),
    ]
    for row in rows:
        mass['delta_rows'].append(row)
        mass['delta_kg']+=row['delta_kg']
        mass['nominal_kg']+=row['delta_kg']
        mass['lower_kg']+=row['delta_kg']+row['uncertainty_kg'][0]
        mass['upper_kg']+=row['delta_kg']+row['uncertainty_kg'][1]
    mass.update(margin_to_4850_kg=4850.-mass['nominal_kg'],margin_to_5000_kg=5000.-mass['nominal_kg'],
                upper_margin_to_5000_kg=5000.-mass['upper_kg'])


def main():
    gate, criteria, base, inputs=load_inputs()
    frame=inputs[0]
    setup=case_setup(inputs,TRIAL['thickness_mm'],TRIAL['travel_mm'],TRIAL['wing_mm'],
                     axial_allowance_mm=AXIAL_ALLOWANCE_MM, gate_accel_m_s2=OPTIONS['gate_accel_m_s2'],
                         gate_speed_m_s=OPTIONS['gate_speed_m_s'])
    cycle,candidate=calculate_cycle(setup,OPTIONS)
    candidate['description'] += ' Круг 2, сменная кассета и подача от ГА НД при закрытии.'
    lever_rows=compare_cycles(setup)
    residual_bracket=[]
    for force_N in (110000.,130000.):
        row,_=calculate_cycle(setup,OPTIONS | {'residual_product_N':force_N})
        residual_bracket.append(dict(residual_product_N=force_N,gate_cycle_s=row['gate_cycle_s'],
                                    pessimistic_cycle_s=row['pessimistic']['cycle_s'],
                                    gate_rms_kW=row['gate_rms_kW']))
    bearing=support(setup['geometry'],base['mass'])
    bearing['rear_edge_relief_length_depth_mm']=[3.,.035]
    bearing['static_bearing_screens_MPa']={'plate_seat':480.,'seat_cast':390.}
    bearing['qualified_pair_pressure_at_1e7_MPa']=None
    hydraulic=hydraulics(setup,OPTIONS,cycle,candidate)
    update_mass(setup['mass'],bearing)
    screens=compare_layouts(inputs)
    gates={key:{'status':row['status'],'value':row['value']}
           for key,func in gate.GATES.items() for row in [func(candidate,criteria)]}
    r2=r2_fea()
    volume=r2.get('r2_aligned_node54',{})
    volume_result=volume.get('finest')
    convergence=volume.get('convergence_max')
    converged=convergence is not None and convergence<.05
    def numerical_status(value, limit, at_least=True):
        if value is None:
            return 'OPEN'
        met=value>=limit if at_least else value<=limit
        return ('PASS' if converged else 'PROVISIONAL_PASS') if met else 'FAIL'
    structural={}
    if volume_result:
        regions=fkm_record(volume_result)
        blade=regions['blade']
        lower=min(volume_result['regions']['blade_lower_depth'],key=lambda row:row['fatigue_factor'])
        strength_MPa=fkm_parameters(1000.,6.3,False,forging=True)[0]
        tensile_mean_headroom_MPa=max(0.,strength_MPa*(1.-1./lower['fatigue_factor_T17'])/lower['M_sigma'])
        structural=dict(plate_hotspot=blade,
                        lower_land_governing_depth_mm=lower['depth_mm'],
                        lower_land_Rp02_required_MPa=1.5*lower['static_mises_MPa'],
                        lower_land_tensile_mean_headroom_MPa=tensile_mean_headroom_MPa,
                        static_factor=min(row['static_factor'] for row in regions.values()),
                        fatigue_factor=min(row['fatigue_factor'] for row in regions.values()),
                        cast_static_factor=regions['cast']['static_factor'],
                        cast_fatigue_factor=regions['cast']['fatigue_factor'],
                        R20_static_factor=regions['cast_R20']['static_factor'],
                        R20_fatigue_factor=regions['cast_R20']['fatigue_factor'],
                        guide_deformation_mm=volume_result['clearance']['combined_screen_mm'],
                        static_contact_blade_seat_MPa=volume_result['loads']['static']['blade_seat']['peak_MPa'],
                        cyclic_contact_blade_seat_MPa=volume_result['loads']['fatigue']['blade_seat']['peak_MPa'],
                        static_contact_seat_cast_MPa=volume_result['loads']['static']['seat_cast']['peak_MPa'],
                        cyclic_contact_seat_cast_MPa=volume_result['loads']['fatigue']['seat_cast']['peak_MPa'])
    status=('HOLD_R2_CONTACT_PAIR_QUALIFICATION' if converged else
            'HOLD_R2_CONTACT_QUALIFICATION_AND_CONVERGENCE')
    numerical_cycle_ok=gates['G-CYCLE']['status']=='PASS' and cycle['gate_cycle_s']<=5.95
    acceptance=dict(
                    C_STR_01=numerical_status(structural.get('static_factor'),1.5),
                    C_FAT_01=numerical_status(structural.get('fatigue_factor'),1.),
                    bearing_contact='OPEN_10E7_PAIR_LIMIT',
                    static_bearing_screen_blade_seat=numerical_status(structural.get('static_contact_blade_seat_MPa'),480.,False),
                    static_bearing_screen_seat_cast=numerical_status(structural.get('static_contact_seat_cast_MPa'),390.,False),
                    three_mesh_convergence='OPEN' if convergence is None else ('PASS' if converged else 'FAIL'),
                    R20_and_chamber_end=numerical_status(
                        min(structural['cast_fatigue_factor'],structural['R20_fatigue_factor']) if structural else None,1.),
                    C_CLR_01=numerical_status(structural.get('guide_deformation_mm'),.15,False),
                    G_CYCLE_R2='PASS' if numerical_cycle_ok else 'FAIL',
                    pessimistic_reference='PASS' if cycle['pessimistic']['cycle_s']<=6. else 'FAIL',
                    pessimistic_reference_at_201_kN='PASS' if lever_rows['max_residual_product']['pessimistic']['cycle_s']<=6. else 'FAIL')
    proofs={**fea_summary(),**r2}
    result=dict(task='T-1.7d',round=2,status=status,comparison=screens,cycle_levers=lever_rows,
                residual_bracket=residual_bracket,
                working_trial=dict(**setup,geometric_FEA_inputs=TRIAL,cycle=cycle,
                                   bearing=bearing,hydraulic=hydraulic,cycle_settings=OPTIONS),
                gates=gates,fea=proofs,structural=structural,acceptance=acceptance,solutions_qualified=0)
    write_json('calc/T-1.7d/results.json',result)
    design_outputs(frame,setup,cycle,candidate,proofs,status,TRIAL,{'bearing':bearing,'hydraulic':hydraulic})
    geom=setup['geometry']
    write_json('metrics.json',dict(task='T-1.7d',round=2,status=status,working_trial=True,static_force_N=1940000.,cyclic_peak_force_N=1700000.,
               target_cycles=10000000,plate_thickness_mm=geom['closed_gate_thickness_mm'],gate_stroke_mm=geom['gate_working_travel_mm'],
               main_stroke_increment_mm=geom['main_stroke_increment_mm'],
               installed_stroke_mm=geom['main_installed_stroke_mm'],
               overtravel_mm=[geom['overtravel_nominal_mm'],geom['overtravel_maximum_mm']],
               minimum_tail_clearance_mm=geom['minimum_relaxed_tail_clearance_after_allowance_mm'],
               channel_length_mm=geom['channel_length_mm'],lower_land_width_mm=bearing['lower_land_width_mm'],
               gate_actuator=setup['opening'][setup['gate_bore_mm']],gate_bore_mm=setup['gate_bore_mm'],
               nominal_mass_kg=setup['mass']['nominal_kg'],mass_range_kg=[setup['mass']['lower_kg'],setup['mass']['upper_kg']],
               cycle_s=cycle['gate_cycle_s'],reference_cycle_s=cycle['realistic']['cycle_s'],
               pessimistic_reference_cycle_s=cycle['pessimistic']['cycle_s'],
               gate_margin_to_5p95_s=5.95-cycle['gate_cycle_s'], cycle_margin_to_6_s=6.-cycle['gate_cycle_s'],
               pessimistic_margin_to_6_s=cycle['pessimistic_margin_s'],gates=gates,
               structural=structural,acceptance=acceptance,residual_bracket=residual_bracket,fea_runs={k:v['files'] for k,v in r2.items()}))
    if structural:
        from round2_report import write_report
        write_report(result)


if __name__=='__main__':
    main()
