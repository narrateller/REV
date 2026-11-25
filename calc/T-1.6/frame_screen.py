"""Compare end traverses at the same force and life as T-1.5."""
from math import asin, atan2, hypot, pi, sqrt


def annulus_mm2(outer_mm, inner_mm=0):
    return pi * (outer_mm**2 - inner_mm**2) / 4


def column_screens(project, cfg, force_N, radial_eccentricity, rho_kg_mm3):
    setup = project["structure"]
    E_MPa = project["elastic_modulus_MPa"]
    original_phi = setup["column_joint_load_fraction"]
    original_root_mm = setup["column_thread_root_mm"]
    root_offset_mm = setup["column_diameter_mm"] - original_root_mm
    column_len_mm = setup["column_length_mm"]
    preload_N = setup["column_pretension_N_each"]
    scatter = cfg["preload_scatter_fraction"]
    screens = []
    for diameter_mm in cfg["column_diameters_mm"]:
        root_mm = diameter_mm - root_offset_mm
        root_mm2 = annulus_mm2(root_mm)
        # VDI 2230 spring model. Hold the clamped members' stiffness fixed
        # and scale the tie stiffness with the thread root area.
        kb_N_mm = E_MPa * root_mm2 / column_len_mm
        phi = 1 / (1 + (1 / original_phi - 1) * (original_root_mm / root_mm)**2)
        load_N = force_N / setup["column_count"] * (1 + radial_eccentricity)
        stress_range_MPa = phi * load_N / root_mm2
        max_N = preload_N * (1 + scatter) + phi * load_N
        screens.append({
            "OD_mm": diameter_mm, "thread_root_mm": root_mm,
            "mass_kg": setup["column_count"] * annulus_mm2(diameter_mm) * column_len_mm * rho_kg_mm3,
            "preload_N_each": preload_N, "load_fraction": phi, "maximum_tie_force_N": max_N,
            "worst_external_N_each": load_N, "nominal_thread_range_MPa": stress_range_MPa,
            "yield_factor": project["column_certified_yield_min_MPa"] * root_mm2 / max_N,
            "thread_fatigue_factor": setup["column_thread_fat_design_range_MPa"] / stress_range_MPa,
            "residual_clamp_N_each": preload_N * (1 - scatter) - (1 - phi) * load_N,
            "closed_joint_compliance_mm_N": phi / kb_N_mm,
        })
    return screens


def frame_screen(data, prior, criteria, main):
    project = data["project"]
    setup = project["structure"]
    cfg = data["review_round_2"]["frame"]
    force_N = setup["frame_load_N"]
    cycles = float(criteria["C-FAT-01"]["min_cycles"])
    static_limit = criteria["C-STR-01"]["min_safety_factor_yield"]
    gap = criteria["C-CLR-01"]
    side_budget_mm = gap["max_mm"] * gap["deflection_share_max"]
    rho_kg_mm3 = project["steel_density_kg_m3"] / 1e9
    E_MPa = project["elastic_modulus_MPa"]
    G_MPa = E_MPa / (2 * (1 + cfg["poisson"]))
    x_mm = setup["column_plate_support_span_mm"] / 2
    y_mm = cfg["transverse_span_mm"] / 2
    ex_mm, ey_mm = cfg["eccentricity_mm"]
    pitch_radius_mm = hypot(x_mm, y_mm)
    force_col_N = force_N / 4
    columns = column_screens(project, cfg, force_N, ex_mm / x_mm + ey_mm / y_mm, rho_kg_mm3)
    column = columns[0]
    worst_col_N = column["worst_external_N_each"]

    length_mm, width_mm, depth_mm = setup["column_plate_dims_mm"]
    plate_I_mm4 = setup["column_plate_effective_width_mm"] * depth_mm**3 / 12
    plate_Z_mm3 = plate_I_mm4 / (depth_mm / 2)
    plate_mass_kg = length_mm * width_mm * depth_mm * rho_kg_mm3
    solid = {
        "mass_per_end_kg": plate_mass_kg, "Z_per_mass_mm3_kg": plate_Z_mm3 / plate_mass_kg,
        "bending_range_MPa_T15_footprint": force_N * (4 * x_mm - main["bore_mm"]) / (8 * plate_Z_mm3),
        "center_to_columns_point_load_deflection_mm": force_N * (2 * x_mm)**3 / (48 * E_MPa * plate_I_mm4),
        "transverse_point_load_deflection_mm": force_N * (2 * y_mm)**3 / (48 * E_MPa * plate_I_mm4),
    }

    hub_R_mm = cfg["hub_OD_mm"] / 2
    arm_b_mm, arm_h_mm = cfg["arm_width_mm"], cfg["depth_mm"]
    tf_mm, tw_mm = cfg["flange_mm"], cfg["web_mm"]
    clear_h_mm = arm_h_mm - 2 * tf_mm
    web_A_mm2 = 2 * tw_mm * clear_h_mm
    arm_A_mm2 = 2 * arm_b_mm * tf_mm + web_A_mm2
    arm_I_mm4 = (arm_b_mm * arm_h_mm**3 - (arm_b_mm - 2 * tw_mm) * clear_h_mm**3) / 12
    arm_Z_mm3 = arm_I_mm4 / (arm_h_mm / 2)
    arm_half_mm = arm_b_mm / 2
    # Integrate the circular hub overlap across arm width. Arm material
    # inside the cylinder of the column seat is retained in the mass bound.
    hub_mean_mm = (arm_half_mm * sqrt(hub_R_mm**2 - arm_half_mm**2)
                   + hub_R_mm**2 * asin(arm_half_mm / hub_R_mm)) / arm_b_mm
    mass_arm_length_mm = pitch_radius_mm - hub_mean_mm
    one_arm_kg = mass_arm_length_mm * arm_A_mm2 * rho_kg_mm3
    pad_A_mm2 = annulus_mm2(cfg["pad_OD_mm"], cfg["column_clearance_ID_mm"])
    pad_kg = pad_A_mm2 * arm_h_mm * rho_kg_mm3
    fillets_kg = cfg["fillet_count_per_end"] * cfg["fillet_radius_mm"]**2 * arm_h_mm * rho_kg_mm3
    cast = data["catalogs"]["cast_frame_material"]
    fatigue_factor = project["project_fatigue_factor"]
    cast_range_MPa = (cfg["cast_basis_1e6_factor"] * cast["Rm_MPa"] * (1e6 / cycles)**(1 / cfg["cast_SN_slope"])
                      * cfg["cast_surface_factor"] / (cfg["casting_quality_factor"] * fatigue_factor))
    theta_rad = atan2(y_mm, x_mm)
    max_sector_rad = max(2 * theta_rad, pi - 2 * theta_rad)
    ends = {}
    for name, hub_ID_mm in cfg["bore_ID_mm"].items():
        mean_R_mm = (hub_R_mm + hub_ID_mm / 2) / 2
        ring_b_mm = hub_R_mm - hub_ID_mm / 2
        ring_I_mm4 = ring_b_mm * arm_h_mm**3 / 12
        ring_Z_mm3 = ring_I_mm4 / (arm_h_mm / 2)
        ring_span_mm = mean_R_mm * max_sector_rad
        # Replace the largest sector by a simply supported straight beam
        # with its sector load at midspan. Start arm cantilevers at mean radius.
        sector_N = 4 * worst_col_N * max_sector_rad / (2 * pi)
        arm_span_mm = pitch_radius_mm - mean_R_mm
        arm_bending_MPa = worst_col_N * arm_span_mm / arm_Z_mm3
        flange_Q_mm3 = arm_b_mm * tf_mm * (arm_h_mm - tf_mm) / 2
        neutral_Q_mm3 = flange_Q_mm3 + 2 * tw_mm * (clear_h_mm / 2)**2 / 2
        arm_shear_MPa = worst_col_N * neutral_Q_mm3 / (arm_I_mm4 * 2 * tw_mm)
        flange_shear_MPa = worst_col_N * flange_Q_mm3 / (arm_I_mm4 * 2 * tw_mm)
        # Near-face bearing is axisymmetric at the cylinder flange. On the
        # largest sector model its share as a uniform line load; retain
        # the concentrated case for the displacement and publish both stresses.
        ring_bending_point_MPa = sector_N * ring_span_mm / (4 * ring_Z_mm3)
        ring_bending_MPa = ring_bending_point_MPa / 2
        ring_shear_MPa = 1.5 * sector_N / (2 * ring_b_mm * arm_h_mm)
        arm_comp_mm_N = arm_span_mm**3 / (3 * E_MPa * arm_I_mm4) + arm_span_mm / (G_MPa * web_A_mm2)
        ring_comp_mm_N = (ring_span_mm**3 / (48 * E_MPa * ring_I_mm4)
                          + ring_span_mm / (4 * G_MPa * ring_b_mm * arm_h_mm))
        local_factor = cfg["local_stress_multiplier"]
        pad_contact_MPa = column["maximum_tie_force_N"] / pad_A_mm2
        pad_range_MPa = worst_col_N / pad_A_mm2
        arm_range_MPa = max(arm_bending_MPa, sqrt(3) * arm_shear_MPa,
                            hypot(arm_bending_MPa * clear_h_mm / arm_h_mm, sqrt(3) * flange_shear_MPa))
        # At a solid rectangular section the bending/free-surface and
        # shear/neutral-axis maxima occur at different fibers.
        range_MPa = local_factor * max(arm_range_MPa, ring_bending_point_MPa,
                                      sqrt(3) * ring_shear_MPa, pad_range_MPa)
        # No credit for the compressive mean stress at the nut seats.
        allowable_MPa = cast_range_MPa * (1 - range_MPa / (2 * cast["Rm_MPa"]))
        compliance_mm_N = arm_comp_mm_N + ring_comp_mm_N * sector_N / worst_col_N
        tilt_rad = force_col_N * compliance_mm_N * hypot(ex_mm / x_mm**2, ey_mm / y_mm**2)
        hub_kg = annulus_mm2(2 * hub_R_mm, hub_ID_mm) * arm_h_mm * rho_kg_mm3
        # Pad and fillet bounding volumes include overlaps.
        mass_kg = hub_kg + 4 * (one_arm_kg + pad_kg) + fillets_kg
        ends[name] = {
            "mass_kg": mass_kg, "hub_kg": hub_kg, "arm_kg_each": one_arm_kg,
            "pad_kg_each": pad_kg, "fillet_volume_allowance_kg": fillets_kg,
            "arm_Z_mm3": arm_Z_mm3, "ring_Z_mm3": ring_Z_mm3,
            "two_opposed_arms_Z_per_end_mass_mm3_kg": 2 * arm_Z_mm3 / mass_kg,
            "arm_bending_MPa": arm_bending_MPa, "arm_web_shear_MPa": arm_shear_MPa,
            "ring_bending_MPa": ring_bending_MPa, "ring_point_load_bending_MPa": ring_bending_point_MPa, "ring_shear_MPa": ring_shear_MPa,
            "local_equivalent_range_MPa": range_MPa, "fatigue_allowable_range_MPa": allowable_MPa,
            "yield_factor": cast["Rp02_MPa"] / max(range_MPa, pad_contact_MPa * local_factor),
            "fatigue_factor": allowable_MPa / range_MPa,
            "center_to_columns_deflection_mm": arm_comp_mm_N * worst_col_N + ring_comp_mm_N * sector_N,
            "eccentric_tilt_rad": tilt_rad,
        }
    column_tilt_rad = column["closed_joint_compliance_mm_N"] * force_col_N * hypot(
        ex_mm / x_mm**2, ey_mm / y_mm**2)
    lateral_mm = cfg["guide_to_load_mm"] * (sum(end["eccentric_tilt_rad"] for end in ends.values())
                                             + column_tilt_rad)
    original = prior["frame"]["column"]
    cast_mass_kg = sum(end["mass_kg"] for end in ends.values()) + column["mass_kg"] + original["bases_ribs_rings_kg"]
    cast_static = min(column["yield_factor"], *(end["yield_factor"] for end in ends.values()))
    cast_fatigue = min(column["thread_fatigue_factor"], *(end["fatigue_factor"] for end in ends.values()))

    weld = cfg["weld"]
    joint_range_MPa = max(end["arm_bending_MPa"] for end in ends.values())
    seam_range_MPa = joint_range_MPa * (arm_h_mm / 2 - tf_mm) / (arm_h_mm / 2)
    weld_Q_mm3 = arm_b_mm * tf_mm * (arm_h_mm - tf_mm) / 2
    weld_shear_MPa = worst_col_N * weld_Q_mm3 / (arm_I_mm4 * 4 * weld["throat_mm"])
    normal_scale = (2e6 / cycles)**(1 / 3) / fatigue_factor
    thickness_ratio = min(1., 25 / tf_mm)
    weld_fatigue = min(weld["FAT_long_MPa"] * normal_scale * thickness_ratio**weld["long_exponent"] / seam_range_MPa,
                       weld["FAT_transition_MPa"] * normal_scale * thickness_ratio**weld["transition_exponent"]
                       / joint_range_MPa,
                       weld["FAT_shear_MPa"] * (2e6 / cycles)**(1 / 5) / fatigue_factor / weld_shear_MPa)
    screen_pass = (cast_static >= static_limit and cast_fatigue >= 1 and lateral_mm <= side_budget_mm
                   and column["residual_clamp_N_each"] > 0)
    return {
        "load_N": force_N, "cycles": cycles, "solid": solid, "columns": columns,
        "frame_T15_kg": original["total_kg"], "unchanged_bases_ribs_rings_kg": original["bases_ribs_rings_kg"],
        "cast_ends": ends, "cast_frame_kg": cast_mass_kg, "cast_static_factor": cast_static,
        "cast_fatigue_factor": cast_fatigue, "column_tilt_rad": column_tilt_rad,
        "frame_lateral_error_mm": lateral_mm, "frame_lateral_budget_mm": side_budget_mm,
        "cast_screen_pass": screen_pass, "mass_target_kg": cfg["target_mass_kg"],
        "mass_target_pass": screen_pass and cast_mass_kg <= cfg["target_mass_kg"],
        "welded_box_screen": {
            "same_nominal_section_pair_kg": sum(end["mass_kg"] for end in ends.values()),
            "long_seam_range_MPa": seam_range_MPa, "throat_shear_range_MPa": weld_shear_MPa,
            "transverse_joint_range_MPa": joint_range_MPa, "fatigue_factor": weld_fatigue,
            "IIW_details": "323 (longitudinal), 412 transverse T-joint toe screened at FAT 71, throat shear FAT 80. Hub/pad joints still require proof.",
            "nominal_static_factor": min(weld["yield_MPa"] / max(end["local_equivalent_range_MPa"] for end in ends.values()),
                                         weld["yield_MPa"] * pad_A_mm2 / column["maximum_tie_force_N"]),
        },
        "G_FEA": cfg["G_FEA"],
    }
