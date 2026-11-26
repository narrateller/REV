"""Assemble round-2 evidence and release-status handover."""
import argparse
from pathlib import Path

from frame_analytic import CYCLIC_N, DEFLECTION_LIMIT_mm, ROOT, STATIC_N, T12B
from frame_fea import FEA, HERE, write_json
from gate_contact import screening
from mass_budget import blocked_round2_budget
from round2_contact import CROWN_DEPTH_mm, CROWN_WIDTH_mm, HEIGHT_mm, THICK_mm, WIDTH_mm
from round2_screens import gate_geometry, opening, zsf_joint
from study import convergence, read_json, read_yaml, write_yaml


def round2_results():
    original_frame = read_json(ROOT/'calc/T-1.7/results.json')['variants']['cast']
    original_study = read_json(HERE/'round1_results.json')
    b1 = original_study['B']
    geometry = gate_geometry()
    cycle = read_json(HERE/'cycle_comparison_r2.json')
    cycle_side = read_json(HERE/'cycle_comparison_r2_side.json')
    short = [read_json(p) for p in sorted(FEA.glob('r2_seat_crown_*.json'))]
    flat = [read_json(p) for p in sorted(FEA.glob('r2_seat_flat_*.json'))]
    finest = short[-1] if short else None
    cover = [read_json(p) for p in sorted(FEA.glob('retained_rear_cap_*.json'))]
    cast_R20_ref = read_json(FEA/'cast_chamber_4.json')['regions']['outlet_traverse_R20']
    cover_convergence = convergence(cover,'regions',('static_MPa','range_MPa','fatigue_factor',
                                                      'fixed_preload_load_to_yield_factor'))
    contact_convergence = convergence(short,'regions',('static_mises_MPa','fatigue_factor'))
    if len(short)>=3:
        peaks = [row['loads']['static']['contact']['pressure_peak_MPa'] for row in short[-3:]]
        changes = [abs(a-b)/abs(b) if b else 1. for a,b in zip(peaks,peaks[1:])]
        contact_convergence.update(contact_pressure_values_MPa=peaks,contact_pressure_changes_fraction=changes,
                                   max_change_fraction=max(contact_convergence['max_change_fraction'],*changes))
        contact_convergence['status'] = 'PASS' if contact_convergence['max_change_fraction']<.05 else 'FAIL'
    contact_pressure_limit_MPa = .6*800.
    short_proofs = {'C_STR_01':'OPEN', 'C_FAT_01':'OPEN', 'contact':'OPEN'}
    if finest:
        short_proofs['C_STR_01'] = 'PASS_LOCAL' if all(r['static_factor']>=1.5 for r in finest['regions'].values()) else 'FAIL_LOCAL'
        short_proofs['C_FAT_01'] = 'PASS_LOCAL' if all(r['fatigue_factor']>=1. for r in finest['regions'].values()) else 'FAIL_LOCAL'
        pressure_MPa = finest['loads']['static']['contact']['pressure_peak_MPa']
        short_proofs['contact'] = 'OPEN' if pressure_MPa<=0. else 'PASS_LOCAL' if pressure_MPa<=contact_pressure_limit_MPa else 'FAIL_LOCAL'
    axial_mm = finest['loads']['fatigue']['blade_axial_displacement_max_mm'] if finest else None
    length_mm = T12B['nominal_product']['in_die_length_mm']
    return {
        'task':'T-1.7b','round':2,'result_status':'STOP_NO_ACCEPTABLE_GATE',
        'A':{'selected':'separate_CY_MAIN_T16_and_cast_T17_frame','decision_project':'D-GK-03',
             'comparison_archive':'round1_results.json'},
        'B':{'selected':None, 'short_span_geometry':geometry,
             'required_force_static_N':STATIC_N,'force_fatigue_range_N':[0.,CYCLIC_N],'fatigue_cycles':10000000,
             'short_span_FEA':short,'short_span_flat_FEA':flat,'short_span_convergence':contact_convergence,
             'short_span_proofs':short_proofs,'bearing_pressure_limit_MPa':contact_pressure_limit_MPa,
             'baseline_side_supports':{'geometry_and_mass':b1['integral_geometry_and_mass'],
                                      'bare_plate_screen':screening(),'FEA':b1['integral_FEA'][-1],
                                      'mesh_convergence':b1['integral_FEA_convergence'],
                                      'cycle_round1_without_extra_drag':b1['cycle'],
                                      'cycle_with_extra_drag':cycle_side},
             'drive_opening_screen':opening(cycle['moving_mass_kg']),
             'side_support_drive_opening_screen':opening(b1['cycle']['moving_mass_kg']),
             'cycle_sensitivity':cycle,'max_cycle_delta_s':max(abs(row['delta_cycle_s']) for row in cycle['cycle_comparison']),
             'local_axial_displacement_fatigue_mm':axial_mm,
             'local_in_die_density_loss_relative':axial_mm/(length_mm+axial_mm) if axial_mm is not None else None,
             'nominal_in_die_length_T12b_mm':length_mm,
             'actual_insert_and_cast_R20_transfer':'BLOCKED_NO_FEASIBLE_PHYSICAL_LOAD_PATH',
             'T17_cast_R20_reference':cast_R20_ref},
        'C_CLR_01':{'status':'OPEN', 'inherited_reference':original_study['C_CLR_01'],
                    'limit_mm':DEFLECTION_LIMIT_mm,
                    'guide_bases':'Both guide sets located and dowelled to the machined chamber module. Shortest guide-to-punch lever 77 mm.'},
        'R2_3':{'ZSF_NG100':zsf_joint(),'retained_rear_cover_meshes':cover,
                'cover_convergence':cover_convergence,'cover_G_FEA_required':True},
        'machine_mass':blocked_round2_budget(original_frame,geometry),
    }


def render_design(root, result):
    b, budget = result['B'],result['machine_mass']
    frame = read_yaml(ROOT/'design/frame.t17.yaml')
    frame.update(task='T-1.7b',round=2,status='held_for_gate_load_path',
                 main_cylinder_architecture='separate_main_cylinder_T16')
    frame['interfaces']['slide_gate_study'] = 'design/slide_gate.t17b.yaml'
    frame['interfaces']['guide_reference_plane'] = result['C_CLR_01']['guide_bases']
    frame['results'] = {
        'inherited_T17_reference':frame['results'],'selected_R2_machine_mass_kg':None,
        'revised_reaction_and_clearance_status':result['C_CLR_01']['status'],
        'force_transfer_into_actual_cast_R20':b['actual_insert_and_cast_R20_transfer'],
    }
    frame['D1_checks'] = [
        'Resolve lower bearing versus open drop bay with the chief engineer before updating the transmitting structure.',
        'Check new contact force and moments at the actual insert and cast R20 with the T-1.7 preload bases.',
        'Check module guide deflections by one-axis SRSS and retain the 77 mm guide-to-punch lever.',
        'Close the separate rear cover and ZSF flange by assembly FEA and transient testing.',
    ]
    write_yaml(root/'design/frame.t17b.yaml',frame)
    slide = {
        'schema_version':2,'task':'T-1.7b','round':2,'status':result['result_status'],'selected':None,
        'baseline_frame':'design/frame.t17b.yaml','window_mm':[150,200],
        'kept_interface':{key:b['short_span_geometry'][key] for key in (
            'gate_face_x_mm','gate_back_x_mm','installed_insert_front_x_mm','open_drop_bay_required_mm',
            'opening_working_mm','opening_installed_mm','rectangular_clear_passage_mm',
            'overtravel_nominal_mm','overtravel_maximum_mm')},
        'force_static_N':b['required_force_static_N'],'fatigue_force_range_N':b['force_fatigue_range_N'],
        'cycles':b['fatigue_cycles'], 'contact_friction_coefficient':.15,
        'local_comparison_only':{
            'geometry':b['short_span_geometry'],'blade_dimensions_mm':[WIDTH_mm,HEIGHT_mm,THICK_mm],
            'insert_dimensions_mm':[340.,180.,55.],'outlet_mm':[176.,74.,20.],
            'blade_and_insert_grade':'34CrNiMo6+QT','Rp02_min_MPa':800.,'Rm_min_MPa':1000.,
            'edge_relief_mm':[CROWN_WIDTH_mm,CROWN_DEPTH_mm],
            'proof':b['short_span_proofs'],'pressure_screen_MPa':b['bearing_pressure_limit_MPa'],
        },
        'side_support_baseline':{
            'part_and_rails':b['baseline_side_supports']['geometry_and_mass'],
            'rail_bearing_dimensions_mm':[82.,180.],'rail_count':2,'clear_rail_gap_mm':176.,
            'mean_insert_bearing_at_1p94_MN_MPa':STATIC_N/(2.*82.*180.),
            'local_strength_status':'FAIL_FATIGUE',
        },
        'opening_force_screen':b['drive_opening_screen'],
        'cylinder_reference':'design/cylinders.t16.yaml CY-GATE',
        'cylinder_filled_mass_kg':23.04,
        'actual_insert_and_cast_transfer':b['actual_insert_and_cast_R20_transfer'],
        'reference_machine_mass_kg':budget['machine_T17b_carried_reference_kg'],
    }
    write_yaml(root/'design/slide_gate.t17b.yaml',slide)


def metrics(result):
    b,m,z = result['B'],result['machine_mass'],result['R2_3']
    geometry = b['short_span_geometry']
    finest = b['short_span_FEA'][-1] if b['short_span_FEA'] else None
    fy = z['retained_rear_cover_meshes'][-1]['regions']['cover_global']
    return {
        'task':'T-1.7b','round':2,'status':result['result_status'],
        'machine_mass_ref_kg':m['machine_T17b_carried_reference_kg'],'selected_machine_mass_kg':None,
        'machine_ref_margin_to_5000_kg':m['reference_margin_to_5000_kg'],
        'machine_ref_margin_to_4850_kg':m['reference_margin_to_4850_kg'],
        'machine_4850_status':m['target_4850_status'],'short_span_optimistic_mass_floor_kg':m['short_span_optimistic_mass_floor_kg'],
        'force_static_N':b['required_force_static_N'],'force_fatigue_N':b['force_fatigue_range_N'][1],
        'pressure_static_bar':315.,'pressure_fatigue_bar':300.,
        'interference_tail_mm':-geometry['tail_clearance_over_local_insert_mm'],
        'drop_bay_required_mm':geometry['open_drop_bay_required_mm'],
        'drop_bay_with_55mm_local_insert_mm':geometry['drop_bay_with_local_insert_mm'],
        'rho_sensitivity_fraction':b['local_in_die_density_loss_relative'],
        'short_span_static_factor_min':min(v['static_factor'] for v in finest['regions'].values()) if finest else None,
        'short_span_fatigue_factor_min':min(v['fatigue_factor'] for v in finest['regions'].values()) if finest else None,
        'short_span_contact_peak_MPa':finest['loads']['static']['contact']['pressure_peak_MPa'] if finest else None,
        'short_span_convergence_status':b['short_span_convergence']['status'],
        'measured_probes_mesh_count':len(b['short_span_FEA']),
        'local_axial_displacement_fatigue_mm':b['local_axial_displacement_fatigue_mm'],
        'opening_force_screen_N':b['drive_opening_screen']['opening_force_screen_N'],
        'opening_drive_available_N':b['drive_opening_screen']['opening_drive_available_N'],
        'opening_drive_factor_screen':b['drive_opening_screen']['opening_screen_factor'],
        'max_cycle_delta_s':b['max_cycle_delta_s'],
        'C_CLR_01_status':result['C_CLR_01']['status'],
        'retained_cover_fatigue_factor':fy['fatigue_factor'],'retained_cover_static_proof_factor':fy['fixed_preload_load_to_yield_factor'],
        'zsf_inst_stop_pressure_rise_bar':z['ZSF_NG100']['fill_shock_pressure_rise_bar'],
    }


def assemble(root=ROOT, results_path=HERE/'results.json'):
    result = round2_results()
    write_json(results_path,result)
    render_design(root,result)
    write_json(root/'metrics.json',metrics(result))
    return result


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT)
    args = parser.parse_args()
    assemble(args.out, HERE/'results.json' if args.out==ROOT else args.out/'results.json')
