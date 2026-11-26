"""Traceable geometry, opening-force and VDI 2230 screens for round 2."""
from math import pi, radians, sqrt, tan

from frame_analytic import (
    ADAPTER_mm, BRIQUETTE_PATH_HEIGHT_mm, BRIQUETTE_PATH_WIDTH_mm, CYCLES, CYLINDER,
    DISCHARGE_BAY_mm, E_MPa, RHO_kg_mm3, STATIC_N, T12B, chamber_bearing,
)
from round2_contact import HEIGHT_mm, THICK_mm, WIDTH_mm
from frame_fea import fkm_parameters


def area_mm2(d_mm, bore_mm=0.):
    return pi*(d_mm**2-bore_mm**2)/4


def gate_geometry():
    ref = T12B['axis_A']
    close_mm = ref['closed_gate_inner_face_x_mm']
    rear_mm = ref['gate_outer_x_mm']
    insert_mm = rear_mm+DISCHARGE_BAY_mm
    bearing = chamber_bearing()
    tail_mm = rear_mm+bearing['minimum_ejected_tail_to_gate_clearance_mm']
    opening_mm = T12B['gate']['gate_opening_travel_mm']
    front_lower_land_mm = rear_mm+ADAPTER_mm
    removed_kg = 220.*150.*THICK_mm*RHO_kg_mm3
    plate_kg = WIDTH_mm*HEIGHT_mm*THICK_mm*RHO_kg_mm3
    port_mm2 = 176.*74.-(4.-pi)*20.**2
    nominal_bearing_mm2 = WIDTH_mm*HEIGHT_mm-port_mm2
    # First screen the top and bottom straight strips even with the full
    # 220 mm width and no crowning. Real corner side lands can take load.
    top_bottom_mm2 = WIDTH_mm*(HEIGHT_mm-74.)
    strip = T12B['gate']['reserve_300_bar']
    T12_bending_MPa = strip['bending_MPa']
    allow_MPa, _, _, M = fkm_parameters(1000.,6.3,False,forging=True)
    T12_strip_factor = allow_MPa/((1.+M)*T12_bending_MPa/2)
    return {
        'gate_face_x_mm':close_mm,'gate_back_x_mm':rear_mm,'installed_insert_front_x_mm':insert_mm,
        'open_drop_bay_required_mm':DISCHARGE_BAY_mm, 'tail_at_minimum_clearance_x_mm':tail_mm,
        'head_max_x_mm':bearing['maximum_leading_edge_from_punch_home_mm'],
        'tail_clearance_original_mm':tail_mm-rear_mm,'head_clearance_original_mm':bearing['discharge_axial_clearance_mm'],
        'local_insert_depth_mm':ADAPTER_mm,'local_insert_lower_land_end_x_mm':front_lower_land_mm,
        'drop_bay_with_local_insert_mm':insert_mm-front_lower_land_mm,
        'tail_clearance_over_local_insert_mm':tail_mm-front_lower_land_mm,
        'direct_gate_shift_to_installed_insert_mm':insert_mm-rear_mm,
        'minimum_nominal_punch_travel_if_moved_mm':ref['main_required_travel_mm']+DISCHARGE_BAY_mm,
        'maximum_working_punch_travel_if_moved_mm':ref['max_operating_travel_mm']+DISCHARGE_BAY_mm,
        'installed_punch_travel_mm':ref['main_installed_stroke_mm'],
        'opening_working_mm':opening_mm,'opening_installed_mm':T12B['gate']['gate_installed_stroke_mm'],
        'local_blade_open_lower_edge_mm':opening_mm-HEIGHT_mm/2,
        'local_blade_open_margin_mm':opening_mm-HEIGHT_mm/2-BRIQUETTE_PATH_HEIGHT_mm/2,
        'rectangular_clear_passage_mm':[BRIQUETTE_PATH_WIDTH_mm,BRIQUETTE_PATH_HEIGHT_mm],
        'R20_nominal_passage_margin_mm':bearing['aperture_corner_reserve_mm'],
        'overtravel_nominal_mm':T12B['gate']['nominal_overtravel_mm'],
        'overtravel_maximum_mm':T12B['gate']['max_overtravel_mm'],
        'local_blade_envelope_mass_kg':plate_kg,'baseline_blade_envelope_mass_kg':removed_kg,
        'local_blade_envelope_mass_delta_kg':plate_kg-removed_kg,
        'two_straight_lands_upper_area_mm2':top_bottom_mm2,
        'two_straight_lands_mean_if_carry_full_force_MPa':STATIC_N/top_bottom_mm2,
        'whole_perimeter_nominal_area_mm2':nominal_bearing_mm2,
        'whole_perimeter_mean_if_fully_seated_MPa':STATIC_N/nominal_bearing_mm2,
        'T12_strip_bending_at_1p7_MN_MPa':T12_bending_MPa,
        'T12_strip_shear_equivalent_at_1p7_MN_MPa':strip['shear_von_mises_MPa'],
        'T12_strip_bending_at_1p94_MN_MPa':T12_bending_MPa*STATIC_N/strip['load_N'],
        'T12_strip_shear_equivalent_at_1p94_MN_MPa':strip['shear_von_mises_MPa']*STATIC_N/strip['load_N'],
        'T12_strip_FKM_factor_without_gradient_credit':T12_strip_factor,
        'T12_strip_thickness_for_FKM_1_mm':THICK_mm/sqrt(T12_strip_factor),
        'max_blade_thickness_at_original_tail_before_intrusion_mm':tail_mm-close_mm,
        'status':'FAIL_GEOMETRY',
    }


def opening(moving_mass_kg):
    p_main_cap_bar = 5.
    p_T16_permissive_bar = 3.
    p_gate_back_bar = 5.
    p_gate_supply_bar = 300.
    efficiency = .92
    speed_m_s = .6
    acceleration_m_s2 = 20.
    friction = .15
    main_hydraulic_N = .1*p_main_cap_bar*CYLINDER['cap_area_mm2']
    # T-1.2b describes 100 kN after opening as ejection drag. It supplies
    # springback lengths, but no closed-gate unloading force-displacement law.
    product_screen_N = 100000.
    annulus_mm2, cap_mm2 = area_mm2(80.,45.),area_mm2(80.)
    available_N = .1*(p_gate_supply_bar*annulus_mm2*efficiency-p_gate_back_bar*cap_mm2)
    inertia_gravity_N = moving_mass_kg*(9.81+acceleration_m_s2)
    existing_drag_N = 10000.
    opening_N = existing_drag_N + inertia_gravity_N + friction*(main_hydraulic_N+product_screen_N)
    return {
        'pressure_main_after_decompression_bar':p_main_cap_bar,'max_main_hydraulic_normal_force_N':main_hydraulic_N,
        'T16_dual_channel_gate_open_pressure_permissive_bar':p_T16_permissive_bar,
        'max_main_normal_force_at_T16_permissive_N':.1*p_T16_permissive_bar*CYLINDER['cap_area_mm2'],
        'provisional_product_normal_force_N':product_screen_N,'product_force_basis':'T-1.2b ejection drag magnitude, sensitivity only',
        'friction_coefficient':friction,'contact_friction_hydraulic_only_N':friction*main_hydraulic_N,
        'extra_opening_drag_N':friction*(main_hydraulic_N+product_screen_N),'noncontact_drag_N':existing_drag_N,
        'moving_mass_kg':moving_mass_kg,'gravity_and_inertia_N':inertia_gravity_N,'opening_force_screen_N':opening_N,
        'opening_drive_available_N':available_N,'opening_screen_factor':available_N/opening_N,
        'maximum_product_normal_N_for_factor_2':(available_N/2-existing_drag_N-inertia_gravity_N)/friction-main_hydraulic_N,
        'drive_eta':efficiency,'assumed_gate_return_pressure_bar':p_gate_back_bar,
        'supply_pressure_for_factor_2_bar':10*(2*opening_N+.1*p_gate_back_bar*cap_mm2)/(annulus_mm2*efficiency),
        'bore_rod_mm':[80.,45.], 'gate_open_flow_L_min':.06*speed_m_s*annulus_mm2,
        'gate_close_flow_L_min':.06*speed_m_s*cap_mm2,'ramp_s':speed_m_s/acceleration_m_s2,
        'ramp_distance_mm':500*speed_m_s**2/acceleration_m_s2,'speed_m_s':speed_m_s,
        'status':'SCREEN_PASS_BRIQUETTE_UNLOAD_FORCE_UNVERIFIED' if available_N>=2*opening_N else 'FAIL_SCREEN',
    }


def zsf_joint():
    # RE 20478, pp. 9 and 17. Bossard M27 table gives T/F for ISO 4762.
    # Reconstruct T/F = p/(2 pi) + mu (d2/sqrt(3) + D_Km/2).
    d_mm,p_mm,bolts = 27.,3.,8
    torque_Nm,scatter = 1150.,.10
    friction_bounds = (.09,.14)
    torque_arm_mm = (1674./342.-p_mm/(2*pi))/.14
    d2_mm,d3_mm = d_mm-.649519*p_mm,d_mm-1.226869*p_mm
    As_mm2 = area_mm2(d_mm-.938194*p_mm)
    min_N = 1000*torque_Nm*(1-scatter)/(p_mm/(2*pi)+friction_bounds[1]*torque_arm_mm)
    max_N = 1000*torque_Nm*(1+scatter)/(p_mm/(2*pi)+friction_bounds[0]*torque_arm_mm)
    torsion_Nmm = max_N*(p_mm/(2*pi)+friction_bounds[0]*d2_mm/sqrt(3))
    assembly_vm_MPa = sqrt((max_N/As_mm2)**2+3*(16*torsion_Nmm/(pi*d3_mm**3))**2)
    e_mm = 45.
    l_k_mm = 180.-e_mm
    bolt_mm_N = ((l_k_mm-.5*d_mm+.4*d_mm)/area_mm2(d_mm)
                 +(.5*d_mm+.5*d_mm)/area_mm2(d3_mm))/E_MPa
    settle_mm = .04
    d_bearing_mm,d_clearance_mm = 39.,30.
    # One cone in each half with use of an assumed limiting member diameter.
    # The small and large caps are sensitivity values for an unspecified flange stack.
    bounds = []
    for d_cap_mm in (45.,55.,70.):
        plate_mm_N = sum(1./(E_MPa*area_mm2(min(d_cap_mm,
                    d_bearing_mm+2*min(i+.5,l_k_mm-i-.5)*tan(radians(30))),d_clearance_mm))
                    for i in range(int(l_k_mm)))
        phi = plate_mm_N/(bolt_mm_N+plate_mm_N)
        embed_N = settle_mm/(bolt_mm_N+plate_mm_N)
        bounds.append({'cone_cap_diameter_mm':d_cap_mm,'clamp_compliance_mm_N':plate_mm_N,
                       'phi_assuming_n_1':phi,'settlement_loss_N':embed_N})
    vdi_allow_MPa = .85*(150/d_mm+45)
    j_fatigue = 1.35
    oil_bulk_Pa,rho_kg_m3,pipe_mm,flow_L_min = 1.4e9,870.,130.,1293.
    wave_speed_m_s = sqrt(oil_bulk_Pa/rho_kg_m3)
    oil_speed_m_s = (flow_L_min/60000)/(area_mm2(pipe_mm)*1e-6)
    fill_shock_bar = wave_speed_m_s*rho_kg_m3*oil_speed_m_s/1e5
    rows = []
    for diameter_mm in (138.5,188.):
        for label,p_bar in (('cycle_300',300.),('proof_315',315.),
                            ('rapid_fill_stop',.45+fill_shock_bar),('300_plus_shock_sensitivity',300.+fill_shock_bar)):
            axial_N = .1*p_bar*area_mm2(diameter_mm)
            Ap_N = axial_N/bolts
            for case in bounds:
                phi = case['phi_assuming_n_1']
                amp_MPa = phi*Ap_N/(2*As_mm2)
                residual_N = min_N-case['settlement_loss_N']-(1-phi)*Ap_N
                boltmax_N = max_N+phi*Ap_N
                rows.append({'case':label,'pressure_bar':p_bar,'effective_diameter_sensitivity_mm':diameter_mm,
                             'separation_force_total_N':axial_N,'separation_force_per_bolt_N':Ap_N,
                             'cone_cap_diameter_mm':case['cone_cap_diameter_mm'],'thread_amplitude_MPa':amp_MPa,
                             'thread_fatigue_screen_factor':vdi_allow_MPa/(j_fatigue*amp_MPa),
                             'mean_stress_over_yield_fraction':((min_N+max_N)/2-case['settlement_loss_N']
                                                                     +phi*Ap_N/2)/(As_mm2*940.),
                             'residual_clamp_N':residual_N,'max_static_bolt_force_N':boltmax_N,
                             'proof_load_margin_N':As_mm2*830.-boltmax_N})
    return {'status':'G_FEA_AND_TRANSIENT_TEST','fastener':'8 M27x180 ISO 4762 10.9-flZn R913059494',
            'torque_Nm':torque_Nm,'torque_tolerance_fraction':scatter,'friction_range':list(friction_bounds),
            'thread_stress_area_mm2':As_mm2,'min_assembly_preload_N':min_N,'max_assembly_preload_N':max_N,
            'assembly_vm_max_MPa':assembly_vm_MPa,'assembly_vm_limit_90pct_yield_MPa':.90*940.,
            'bolt_compliance_mm_N':bolt_mm_N,'assumed_grip_mm':l_k_mm,'assumed_effective_engagement_mm':e_mm,
            'embedment_mm':settle_mm,'cycles':CYCLES,'vdi_ASV_MPa':vdi_allow_MPa,'fatigue_divisor':j_fatigue,
            'clamp_sensitivities':bounds,'bolt_load_cases':rows,'fill_oil_velocity_m_s':oil_speed_m_s,
            'fill_shock_pressure_rise_bar':fill_shock_bar,'bulk_modulus_Pa':oil_bulk_Pa,'oil_density_kg_m3':rho_kg_m3,
            'unverified':['effective seal diameter and clamp stack','seating prying, flange bending and pipe loads',
                         'actual engaged threads and R11 strip check','local poppet impact and actual pressure trace']}
