"""Hand checks on the opening actuator and plate thickness (FEA remains independent)."""
from math import log10,pi


def gate_screen(geometry,upstream,historical,main,gate_mass_kg):
    thickness_mm=geometry['closed_gate_thickness_mm']
    width_mm,loaded_height_mm=upstream['main_section_mm']
    steel=historical['local_comparison_only']
    # Optimistic simple strip with supports at the opening edges. Broad lands
    # and edge runout determine the actual support and are checked separately.
    span_mm=geometry['passage_inlet_mm'][1]
    moment_arm_mm=(2*span_mm-loaded_height_mm)/8
    bending_per_N=6*moment_arm_mm/(width_mm*thickness_mm**2)
    rm_MPa,rp_MPa=steel['Rm_min_MPa'],steel['Rp02_min_MPa']
    kR=1-.22*log10(6.3)*log10(2*rm_MPa/400)
    allowable_MPa=.40*rm_MPa*kR*10**(-1/15)/1.5
    slope=.00035*rm_MPa-.1
    static_N=historical['force_static_N']
    fatigue_N=historical['fatigue_force_range_N'][1]
    fatigue_factor=allowable_MPa/((1+slope)*bending_per_N*fatigue_N/2)
    opening=historical['opening_force_screen']
    error_bar=opening['pressure_main_after_decompression_bar']
    hydro_N=.1*error_bar*main['cap_area_mm2']
    mu=opening['friction_coefficient']
    base_drag_N=opening['noncontact_drag_N']
    idle_drag_N=base_drag_N+gate_mass_kg*(9.81+20.)
    available_N=opening['opening_drive_available_N']
    product_N=opening['provisional_product_normal_force_N']
    opening_N=idle_drag_N+mu*(hydro_N+product_N)
    return dict(plate_thickness_mm=thickness_mm,optimistic_strip_span_mm=span_mm,
                static_force_N=static_N,fatigue_force_N=fatigue_N,fatigue_cycles=historical['cycles'],
                fkm_k_D=15.,fkm_j=1.5,fkm_j_G_cast=1.25,moving_mass_screen_kg=gate_mass_kg,
                static_bending_screen_factor=rp_MPa/(bending_per_N*static_N),fatigue_bending_screen_factor=fatigue_factor,
                required_thickness_hand_screen_mm=thickness_mm/fatigue_factor**.5,contact_steel_pair_mu=mu,
                bearing_pressure_screen_MPa=steel['pressure_screen_MPa'],opening_force_N=opening_N,
                opening_available_N=available_N,opening_force_factor=available_N/opening_N,
                opening_main_hydraulic_residual_N=hydro_N,opening_product_residual_screen_N=product_N,
                opening_max_residual_product_for_factor_2_N=(available_N/2-idle_drag_N)/mu-hydro_N,
                noncontact_gate_drag_N=base_drag_N,
                permissive_indicated_pressure_bar_each_channel=opening['T16_dual_channel_gate_open_pressure_permissive_bar'])
