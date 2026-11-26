"""VDI 2230-1:2015 elastic assessment of the ZSF NG100 connection."""
from itertools import product
from math import hypot, log10, pi, sin, sqrt

from scipy.integrate import quad


D_MM, P_MM = 27.0, 3.0
D2_MM = D_MM - 0.649519 * P_MM
D3_MM = D_MM - 1.226869 * P_MM
E_MPA, RP_MPA, PROOF_MPA, RM_MAX_MPA = 210000., 940., 830., 1200.
BEARING_MM, CLEARANCE_MM, GRIP_MM = 39., 30., 135.


def area_mm2(outer_mm, inner_mm=0.):
    return pi / 4 * (outer_mm**2 - inner_mm**2)


AS_MM2 = area_mm2(D_MM - 0.938194 * P_MM)


def thread_arm_mm(mu):
    return P_MM / (2 * pi) + mu * D2_MM / sqrt(3)


def equivalent_MPa(force_N, thread_torque_Nmm, shank_mm):
    return max(hypot(force_N / section_mm2, sqrt(3) * 16 * thread_torque_Nmm / (pi * root_mm**3))
               for section_mm2, root_mm in ((AS_MM2, D3_MM), (area_mm2(shank_mm), shank_mm)))


def transition_half_length_mm(shank_mm):
    h_mm = (D_MM-shank_mm)/2
    return sqrt(FILLET_MM*h_mm-h_mm**2/4)


def transition_radius_mm(x_mm, shank_mm):
    s_mm = transition_half_length_mm(shank_mm)
    if x_mm <= s_mm:
        return shank_mm/2+FILLET_MM-sqrt(FILLET_MM**2-x_mm**2)
    dx_mm = 2*s_mm-x_mm
    return D_MM/2-FILLET_MM+sqrt(FILLET_MM**2-dx_mm**2)


def compliance_mm_N(shank_mm, cone_limit_mm):
    half_transition_mm = transition_half_length_mm(shank_mm)
    neck_straight_mm = GRIP_MM-.5*D_MM-4*half_transition_mm
    taper_inverse_area_per_mm = quad(
        lambda x_mm: 1/(pi*transition_radius_mm(x_mm,shank_mm)**2), 0., 2*half_transition_mm)[0]
    bolt = (neck_straight_mm/area_mm2(shank_mm)+2*taper_inverse_area_per_mm
            +.4*D_MM/area_mm2(D_MM)+D_MM/area_mm2(D3_MM))/E_MPA
    half_grip_mm = GRIP_MM / 2
    cone_slope = 2 / sqrt(3)
    cone_mm = min(half_grip_mm, (cone_limit_mm - BEARING_MM) / cone_slope)
    plate = 2 / E_MPA * (quad(lambda z_mm: 1 / area_mm2(BEARING_MM + cone_slope * z_mm, CLEARANCE_MM),
                              0, cone_mm)[0]
                         + (half_grip_mm - cone_mm) / area_mm2(cone_limit_mm, CLEARANCE_MM))
    return bolt, plate


def transient():
    """Rigid line, instantaneous fill-flow arrest. MD and MF bypass ZSF on return."""
    rho_kg_m3, bulk_Pa, flow_L_min, pipe_mm = 870., 1.4e9, 1293., 130.
    flow_m3_s = flow_L_min / 60_000
    fluid_m_s = flow_m3_s / (area_mm2(pipe_mm) * 1e-6)
    wave_m_s = sqrt(bulk_Pa / rho_kg_m3)
    rise_bar = rho_kg_m3 * wave_m_s * fluid_m_s / 1e5
    return dict(instantaneous_stop_flow_at_port_A_rating_L_min=flow_L_min*(16.-0.45)/rise_bar,
                fill_flow_L_min=flow_L_min, fill_line_ID_mm=pipe_mm, fluid_speed_m_s=fluid_m_s,
                wave_speed_m_s=wave_m_s, fill_stop_rise_bar=rise_bar, fill_stop_gauge_bar=rise_bar+0.45,
                steady_momentum_N=rho_kg_m3*flow_m3_s*fluid_m_s,
                opening_delta_poppet_force_N=0.012*7313, port_A_rating_bar=16.,
                measured_history_available=False)



# Round 2, with the physical package specified separately from the old torque trial.
NECK_MM = 23.5
FILLET_MM = 14.
PRELOAD_N = (157500., 172500.)
TRANSFER = 1.25
PENETRATION_MM = 42.
PENETRATION_TOL_MM = .5
RECESS_MM = 10.
NUT_THICK_MM = 23.8
WASHER_THICK_MM = 4.
WASHER_OD_MM = 50.
WASHER_ID_MM = 28.
PROTRUSION_MM = 33.
TOOL_OD_MM = 87.
FLANGE_WASHER_EFFECTIVE_OD_MM = 45.
NUT_PROOF_N = 486500.
RP_COVER_TABLE_MPA = 600.
RM_COVER_TABLE_MPA = 800.
RM_COVER_SPEC_MPA = 850.
RM_STUD_MIN_MPA = 1040.


def thread_strip_round2(rm_cover_MPa):
    # VDI pp. 98?100. Use explicit conservative dimensional bounds for 6g/6H
    # to establish inspection limits, and the lower shear ratio 0.65 for QT.
    d_min_mm, D2_max_mm, d2_min_mm, D1_max_mm = 26.5, 25.30, 24.80, 24.0
    inside_per_mm = pi*d_min_mm/P_MM*(P_MM/2+(d_min_mm-D2_max_mm)/sqrt(3))
    outside_per_mm = pi*D1_max_mm/P_MM*(P_MM/2+(d2_min_mm-D1_max_mm)/sqrt(3))
    ratio = rm_cover_MPa*inside_per_mm/(RM_MAX_MPA*outside_per_mm)
    # Check C1 at s/d = 1.4 until the effective collar has been confirmed.
    s_over_d = 1.4
    c1 = 3.8*s_over_d-s_over_d**2-2.61
    x = max(.4, ratio)
    c3 = .897 if x >= 1 else .728 + 1.769*x - 2.896*x**2 + 1.296*x**3
    strength_N_per_mm = .65*rm_cover_MPa*inside_per_mm*c1*c3
    effective_mm = PENETRATION_MM-PENETRATION_TOL_MM-RECESS_MM-2*P_MM
    max_bolt_breaking_N = RM_MAX_MPA*AS_MM2
    return dict(
        cover_Rm_MPa=rm_cover_MPa, d_min_mm=d_min_mm, D2_max_mm=D2_max_mm,
        d2_min_mm=d2_min_mm, D1_max_mm=D1_max_mm, s_over_d=s_over_d,
        C1=c1, C3=c3, strength_ratio=ratio, effective_engagement_mm=effective_mm,
        total_penetration_required_mm=RECESS_MM+2*P_MM+max_bolt_breaking_N/strength_N_per_mm,
        strip_load_N=strength_N_per_mm*effective_mm,
        strip_to_full_thread_rupture_factor=strength_N_per_mm*effective_mm/max_bolt_breaking_N,
    )


def fkm_shaft(force_mean_N, force_amplitude_N, force_peak_N, diameter_mm, kt):
    """FKM local stress screen, with unit notch support and no residual stress credit."""
    roughness_Rz_um = 3.2
    rm_MPa = RM_STUD_MIN_MPA
    kR = 1-.22*log10(roughness_Rz_um)*log10(2*rm_MPa/400)
    M_sigma = .00035*rm_MPa-.1
    allowable_MPa = .45*rm_MPa*kR*10**(-1/15)/1.5
    stress_area_mm2 = area_mm2(diameter_mm)
    sigma_a_nom_MPa = force_amplitude_N/stress_area_mm2
    sigma_m_nom_MPa = force_mean_N/stress_area_mm2
    equivalent_nom_MPa = sigma_a_nom_MPa + M_sigma*sigma_m_nom_MPa
    return dict(
        Kt=kt, kR=kR, M_sigma=M_sigma, n_sigma=1., Rz_um=roughness_Rz_um,
        allowable_amplitude_MPa=allowable_MPa,
        local_amplitude_MPa=kt*sigma_a_nom_MPa, local_mean_MPa=kt*sigma_m_nom_MPa,
        static_elastic_factor=RP_MPA*stress_area_mm2/(kt*force_peak_N),
        fatigue_factor=allowable_MPa/(kt*equivalent_nom_MPa),
        Kt_limit_for_fatigue=allowable_MPa/equivalent_nom_MPa,
        Kt_limit_for_static=RP_MPA*stress_area_mm2/(1.5*force_peak_N),
    )


def stud_case(seal_mm, cone_limit_mm, distribution_factor, fill_force_N):
    bolt_mm_N, plate_mm_N = compliance_mm_N(NECK_MM, cone_limit_mm)
    phi = plate_mm_N/(bolt_mm_N+plate_mm_N)
    settlement_N = 0.04/(bolt_mm_N+plate_mm_N)
    force_min_N, force_max_N = PRELOAD_N
    press_area_mm2 = distribution_factor*area_mm2(seal_mm)/8
    FA_315_N = 31.5*press_area_mm2
    FA_300_N = 30.*press_area_mm2
    # Envelope negative fill reaction as a separate low-end excursion.
    FA_fill_N = distribution_factor*fill_force_N/8
    residual_N = force_min_N-settlement_N-(1-phi)*FA_315_N
    service_N = force_max_N+phi*FA_315_N
    cycle_mean_N = force_max_N+phi*(FA_300_N-FA_fill_N)/2
    cycle_amplitude_N = phi*(FA_300_N+FA_fill_N)/2
    thread_amplitude_MPa = cycle_amplitude_N/AS_MM2
    mean_ratio_high = cycle_mean_N/(AS_MM2*RP_MPA)
    mean_ratio_low = (cycle_mean_N-force_max_N+force_min_N-settlement_N)/(AS_MM2*RP_MPA)
    ASV_MPa = .85*(150/D_MM+45)
    ASG_MPa = (2-mean_ratio_high)*ASV_MPa
    # Table 3 of Noda et al., axial tension, 2h/D=0.10?0.20 and
    # 2r/D>=1.0. Use the upper 1.271 of the two tabulated numbers.
    fillet = fkm_shaft(cycle_mean_N, cycle_amplitude_N, service_N, NECK_MM, 1.271)
    # Illustrative smooth runout stress limit. The actual partly rolled helix
    # must be checked from the supplier profile. No credit for SG in this FKM screen.
    runout = fkm_shaft(cycle_mean_N, cycle_amplitude_N, service_N, D3_MM, 1.50)
    bearing_flange_MPa = service_N/area_mm2(FLANGE_WASHER_EFFECTIVE_OD_MM,CLEARANCE_MM)
    bearing_nut_MPa = service_N/area_mm2(38.,WASHER_ID_MM)
    return dict(
        pressure_diameter_mm=seal_mm, cone_limit_mm=cone_limit_mm,
        load_distribution_factor=distribution_factor, phi_n_1=phi,
        bolt_compliance_mm_N=bolt_mm_N, clamped_compliance_mm_N=plate_mm_N,
        preload_loss_settlement_N=settlement_N, external_at_315_bar_N=FA_315_N,
        external_at_300_bar_N=FA_300_N, fill_low_end_per_stud_N=FA_fill_N,
        service_force_N=service_N, service_VM_MPa=equivalent_MPa(service_N,0.,NECK_MM),
        service_static_factor_nominal=RP_MPA/equivalent_MPa(service_N,0.,NECK_MM),
        nut_proof_factor=NUT_PROOF_N/service_N,
        bearing_flange_MPa=bearing_flange_MPa, bearing_nut_to_washer_MPa=bearing_nut_MPa,
        bearing_washer_factor_for_pG850=850./bearing_nut_MPa,
        bearing_valve_pG_confirmed_MPa=None, residual_clamp_at_315_bar_N=residual_N,
        bearing_valve_if_stock_40mm_footprint_MPa=service_N/area_mm2(40.,CLEARANCE_MM),
        opening_factor=(force_min_N-settlement_N)/((1-phi)*FA_315_N),
        seal_seat_and_thermal_loss_budget_N=residual_N,
        mean_force_ratio_min=mean_ratio_low, mean_force_ratio_max=mean_ratio_high,
        thread_amplitude_MPa=thread_amplitude_MPa, sigma_ASV_MPa=ASV_MPa,
        sigma_ASG_MPa=ASG_MPa, thread_SV_raw_factor=ASV_MPa/thread_amplitude_MPa,
        thread_SG_raw_factor=ASG_MPa/thread_amplitude_MPa,
        thread_SG_factor_with_project_1p35=ASG_MPa/(1.35*thread_amplitude_MPa),
        shoulder_FKM=fillet, thread_runout_FKM_screen=runout,
    )


def study():
    transfer_nominal = 1.01+D_MM/GRIP_MM
    F_M_min_N,F_M_max_N = PRELOAD_N
    pull_range_N = [TRANSFER*F_M_min_N, TRANSFER*F_M_max_N]
    pull_peak_MPa = equivalent_MPa(pull_range_N[1],0.,NECK_MM)
    proposal = dict(
        count=8, thread="M27x3 6g/6H", property_class="10.9",
        machining="SG: roll both threads after QT; blend to neck before rolling.",
        neck_mm=NECK_MM, transition_min_radius_mm=FILLET_MM, Rz_um=3.2,
        nominal_bearing_to_cover_grip_mm=GRIP_MM, grip_to_d=GRIP_MM/D_MM,
        nominal_neck_model_length_mm=GRIP_MM-.5*D_MM,
        smooth_transition_length_each_mm=2*transition_half_length_mm(NECK_MM),
        rolled_root_radius_min_mm=.125*P_MM,
        depth_inserted_mm=PENETRATION_MM, penetration_tolerance_mm=PENETRATION_TOL_MM,
        tap_recess_mm=RECESS_MM, nominal_tap_cylindrical_depth_mm=43.,
        nut_height_mm=NUT_THICK_MM, nut_property_class=10,
        washer_OD_mm=WASHER_OD_MM, washer_ID_mm=WASHER_ID_MM,
        washer_thickness_mm=WASHER_THICK_MM,
        stand_proud_above_nut_mm=PROTRUSION_MM,
        stud_overall_mm=PENETRATION_MM+GRIP_MM+NUT_THICK_MM+PROTRUSION_MM,
        transfer_formula_estimate=transfer_nominal, transfer_factor=TRANSFER,
        tension_target_N=TRANSFER*(F_M_min_N+F_M_max_N)/2,
        tension_qualification_range_N=pull_range_N,
        preload_after_transfer_N=[F_M_min_N,F_M_max_N], alpha_A=F_M_max_N/F_M_min_N,
        stud_VM_at_tension_MPa=pull_peak_MPa, stud_VM_after_transfer_MPa=equivalent_MPa(F_M_max_N,0.,NECK_MM),
        shoulder_stress_at_tension_MPa=1.271*pull_peak_MPa,
        VDI_assembly_factor_to_0p9_Rp=.9*RP_MPA/(1.271*pull_peak_MPa),
        tensile_proof_factor_at_tension=PROOF_MPA/pull_peak_MPa,
        local_runout_stress_at_tension_screen_MPa=1.50*pull_range_N[1]/area_mm2(D3_MM),
        takeoff_proof_test_required_N=pull_range_N[-1],
        minimum_manual_pull_thread_above_nut_mm=27.,
        assembly_procedure="Tension in opposed sequence and repeat; control each residual stud force via calibrated elongation.",
    )
    gap_mm = 2*120*sin(pi/8)
    tool = dict(
        vendor="Nord-Lock Boltight TSR+1 M27",
        pitch_circle_mm=240., fastener_chord_mm=gap_mm, tool_OD_limit_mm=90., tool_OD_mm=TOOL_OD_MM,
        two_adjacent_tools_nominal_gap_mm=gap_mm-TOOL_OD_MM,
        hydraulic_area_mm2=1870., nominal_tool_pressure_bar=10*TRANSFER*(F_M_min_N+F_M_max_N)/2/1870., max_tool_load_N=280000., tool_load_factor=280000./pull_range_N[-1],
        puller_above_nut_min_mm=D_MM, puller_above_nut_design_mm=PROTRUSION_MM,
        stud_above_bearing_seat_mm=PROTRUSION_MM+NUT_THICK_MM,
        tool_min_stud_above_bearing_seat_mm=2*D_MM,
        tool_OD_start_above_nut_mm=None, tool_min_axial_service_space_from_bearing_mm=145.,
        central_clear_radius_at_full_tool_OD_with_2mm_gap_mm=120-TOOL_OD_MM/2-2.,
        nominal_gap_against_body_D2_if_same_height_mm=120-212./2-TOOL_OD_MM/2,
        bridge_area_required_if_pG300_mm2=pull_range_N[-1]/300.,
        catalogue_body_D2_mm=212., flange_support_map_confirmed=False,
    )
    fill = transient()
    fill_force_N = .1*fill["fill_stop_gauge_bar"]*area_mm2(fill["fill_line_ID_mm"])
    fill_force_N += fill["opening_delta_poppet_force_N"]+fill["steady_momentum_N"]
    fill["separate_axial_reaction_screen_N"] = fill_force_N
    fill["sum_with_315_bar"] = False
    diameters = []
    for seal_mm in (138.5, 188.):
        rows = [stud_case(seal_mm, cone_mm, spread, fill_force_N)
                for cone_mm,spread in product((45.,55.,70.),(1.,1.2))]
        diameters.append(dict(
            seal_diameter_mm=seal_mm, rows=rows,
            static_factor_nominal=min(r["service_static_factor_nominal"] for r in rows),
            static_factor_shoulder=min(r["shoulder_FKM"]["static_elastic_factor"] for r in rows),
            local_elastic_VM_budget_to_C_STR_01_MPa=RP_MPA/1.5-1.271*max(r["service_VM_MPa"] for r in rows),
            thread_1e7_factor=min(r["thread_SG_factor_with_project_1p35"] for r in rows),
            thread_SG_raw_factor=min(r["thread_SG_raw_factor"] for r in rows),
            sigma_ASV_MPa=rows[0]["sigma_ASV_MPa"],
            sigma_ASG_min_MPa=min(r["sigma_ASG_MPa"] for r in rows),
            thread_amplitude_max_MPa=max(r["thread_amplitude_MPa"] for r in rows),
            shoulder_FKM_factor=min(r["shoulder_FKM"]["fatigue_factor"] for r in rows),
            runout_FKM_factor_conditional=min(r["thread_runout_FKM_screen"]["fatigue_factor"] for r in rows),
            runout_Kt_limit_static=min(r["thread_runout_FKM_screen"]["Kt_limit_for_static"] for r in rows),
            runout_static_factor_at_assumed_Kt=min(r["thread_runout_FKM_screen"]["static_elastic_factor"] for r in rows),
            runout_Kt_limit_fatigue=min(r["thread_runout_FKM_screen"]["Kt_limit_for_fatigue"] for r in rows),
            residual_clamp_min_N=min(r["residual_clamp_at_315_bar_N"] for r in rows),
            opening_factor_min=min(r["opening_factor"] for r in rows),
            pG_valve_required_MPa=max(r["bearing_flange_MPa"] for r in rows),
            pG_valve_if_stock_40mm_footprint_MPa=max(r["bearing_valve_if_stock_40mm_footprint_MPa"] for r in rows),
            contact_under_nut_max_MPa=max(r["bearing_nut_to_washer_MPa"] for r in rows),
        ))
    # Independent replay of the catalogue maximum-torque / low-friction screen.
    mu = .09
    d_bearing_mean_mm = 2/3*(BEARING_MM**3-CLEARANCE_MM**3)/(BEARING_MM**2-CLEARANCE_MM**2)
    arm_mm = thread_arm_mm(mu)
    catalogue_upper_torque_Nmm = 1150.*1.10*1000.
    catalogue_preload_N = catalogue_upper_torque_Nmm/(arm_mm+mu*d_bearing_mean_mm/2)
    catalogue_VM_MPa = equivalent_MPa(catalogue_preload_N,catalogue_preload_N*arm_mm,D_MM)
    return dict(
        status="HOLD", proposal=proposal,
        reference_torque_screen=dict(predecessor_VM_MPa=955., replay_VM_MPa=catalogue_VM_MPa,
                                     maximum_assembly_VM_MPa=.9*RP_MPA), tool=tool, pressure_diameter_cases=diameters,
        engagement=[thread_strip_round2(rm) for rm in (RM_COVER_TABLE_MPA, RM_COVER_SPEC_MPA)],
        transient=fill,
        catalogue=dict(count=8, fastener="ISO 4762 M27x180 10.9-flZn", part="R913059494",
                       torque_Nm=1150, friction=[.09,.14], torque_tolerance_fraction=.10,
                       T2_min_mm=55, T1_mm=25, PCD_mm=240, bolt_hole_counterflange_mm=30,
                       contact_face_Rz_max_um=8, contact_face_flatness_mm_per_100_mm=.01,
                       drawing_page=9, counterflange_page=14, screws_page=17, D6_mm=138.5,
                       raised_face_OD_mm=188, B_port_pressure_rating_bar=350, A_port_pressure_rating_bar=16),
        r9_project_fatigue_divisor=1.35,
        holds=["Rexroth approval of studs in place of R913059494 and 315 bar with this counterflange",
               "Valve nut-seat pG and bridge footprint/height, individual local prying and runout profile",
               "Seal seating, thermal preload loss and transient at port A"],
    )
