"""Reproduce the topology comparison in N, mm, MPa and s."""

import json
from math import asin, atan, cos, degrees, exp, log, log10, pi, radians, sin, sqrt, tan
from pathlib import Path

import yaml

import mass


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E_MPa = 210_000.0
NU = 0.30
G_MPa = E_MPa / (2 * (1 + NU))
E_STAR_MPa = E_MPa / (2 * (1 - NU**2))
RELIEF_RATIO = 315 / 300
HEEL_RADIUS_MM = 5.0
CROWN_MM = 0.10
ASYMMETRIC_SHARE = 0.64
FORGED_600 = (600, 800, False)
FORGED_700 = (700, 900, False)
FORGED_800 = (800, 1000, False)
CAST = (650, 800, True)
COLUMNS = (500, 750, False)
FRONT = dict(x_mm=158., seat_length_mm=346., shank_r_mm=40., head_r_mm=68.,
             sleeve_r_mm=87., tooth_height_mm=95., foot_r_mm=63., seat_z_mm=-88.,
             ring_bottom_locked_z_mm=163.)
REAR = dict(x_mm=14., seat_length_mm=226., shank_r_mm=31., head_r_mm=52.,
            sleeve_r_mm=64., tooth_height_mm=70., foot_r_mm=50., seat_z_mm=-88.,
            ring_bottom_locked_z_mm=68.)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def pressure_integrals(case):
    press = case["press"]
    start_mm, end_mm = press["contact_x_mm"]
    length_mm = end_mm - start_mm
    decay_per_mm = case["attenuation_per_mm"]
    pressure_MPa = press["radial_at_contact_start_MPa"]
    if length_mm == 0:
        return None
    integral_mm = (1 - exp(-decay_per_mm * length_mm)) / decay_per_mm
    moment_mm2 = (1 - (1 + decay_per_mm * length_mm) * exp(-decay_per_mm * length_mm)) / decay_per_mm**2
    force_300_N = pressure_MPa * 150 * integral_mm
    centroid_x_mm = start_mm + moment_mm2 / integral_mm
    assert abs(force_300_N - press["force_N"]) < 1e-5
    assert abs(centroid_x_mm - press["centroid_x_mm"]) < 1e-8
    return dict(force_300_N=force_300_N, force_315_N=force_300_N * RELIEF_RATIO,
                centroid_x_mm=centroid_x_mm, start_x_mm=start_mm, end_x_mm=end_mm,
                initial_pressure_300_MPa=pressure_MPa, decay_per_mm=decay_per_mm)


def section_check(stress_315_MPa, material, *, fatigue_envelope=True, compression=False):
    rp_MPa, rm_MPa, cast = material
    kr = 1 - (.20 if cast else .22) * log10(6.3) * log10(2 * rm_MPa / 400)
    mean_factor = .00035 * rm_MPa + (.05 if cast else -.1)
    jg = 1.25 if cast else 1.
    fatigue_strength_MPa = ((.34 if cast else .40) * rm_MPa * kr * 10**(-1/15)) / (1.5 * jg)
    fatigue_demand_MPa = stress_315_MPa / (2 * RELIEF_RATIO) * (1. + (0. if compression else mean_factor))
    return dict(stress_315_MPa=stress_315_MPa, Rp02_MPa=rp_MPa, Rm_MPa=rm_MPa,
                static_factor=rp_MPa / stress_315_MPa, fatigue_factor_n_sigma_1=(
                    fatigue_strength_MPa / fatigue_demand_MPa if fatigue_envelope else None),
                fatigue_strength_MPa=fatigue_strength_MPa, fatigue_demand_MPa=fatigue_demand_MPa,
                M_sigma=mean_factor, j_G=jg)


def strengths(sections):
    return (
        min(row["static_factor"] for row in sections.values()),
        min((row["fatigue_factor_n_sigma_1"] for row in sections.values()
             if row["fatigue_factor_n_sigma_1"] is not None), default=None),
    )


def beam_midspan(force_N, span_mm, load_width_mm, breadth_mm, depth_mm):
    """Simply supported beam, centered uniformly loaded strip, shear by virtual work."""
    inertia_mm4 = breadth_mm * depth_mm**3 / 12
    max_moment_Nmm = force_N * (2 * span_mm - load_width_mm) / 8
    bending_mm = force_N * (8 * span_mm**3 - 4 * span_mm * load_width_mm**2 + load_width_mm**3) / (384 * E_MPa * inertia_mm4)
    shear_mm = force_N * (2 * span_mm - load_width_mm) / (8 * (5/6) * G_MPa * breadth_mm * depth_mm)
    return dict(stress_MPa=max_moment_Nmm * depth_mm / (2 * inertia_mm4),
                bending_mm=bending_mm, shear_mm=shear_mm)


def wedge(force_N, angle_deg=4.):
    """Raise or release a single ramp with a flat sliding guide (two work pairs)."""
    angle = radians(angle_deg)
    rows = []
    for mu in (.10, .15):
        phi = atan(mu)
        rows.append(dict(mu=mu, angle_deg=angle_deg,
                         friction_angle_one_pair_deg=degrees(phi),
                         self_lock_angle_two_pairs_deg=2 * degrees(phi),
                         insert_N=force_N * (tan(angle + phi) + mu),
                         withdraw_N=force_N * (tan(phi - angle) + mu),
                         flat_block_withdraw_N=2 * mu * force_N))
    return rows


def hertz_line(force_N, length_mm, crown_gross_width_mm):
    """Line-contact screening with pressure renormalized when R5 clips the footprint."""
    radius_mm = crown_gross_width_mm**2 / (8 * CROWN_MM) + CROWN_MM / 2
    half_width_mm = sqrt(4 * force_N * radius_mm / (pi * length_mm * E_STAR_MPa))
    truncated_fraction = min(1., (crown_gross_width_mm / 2 - HEEL_RADIUS_MM) / half_width_mm)
    profile_integral_mm = half_width_mm * (
        asin(truncated_fraction) + truncated_fraction * sqrt(1 - truncated_fraction**2))
    return dict(pressure_MPa=force_N / (length_mm * profile_integral_mm),
                half_width_mm=half_width_mm, crown_radius_mm=radius_mm,
                footprint_clipped=truncated_fraction < 1.)


def press_pressure(force_N, width_mm, length_mm, eccentricity_mm=0.):
    e_mm = abs(eccentricity_mm)
    if e_mm >= width_mm / 2:
        return None
    if e_mm <= width_mm / 6:
        return force_N / (width_mm * length_mm) * (1 + 6 * e_mm / width_mm)
    return 2 * force_N / (3 * (width_mm / 2 - e_mm) * length_mm)


def selected_baseline():
    full = read_json(ROOT / "calc/T-2.1/results.json")
    rows = full["candidates"][full["selected"]]
    return rows


def full_width(load, baseline):
    # Ka = Kb, two side portals spanning x, with a single transverse moving key.
    # Key travels to +y. The 4 mm opening clearance is measured to the full shoe face.
    span_mm, key_y_mm = 348., 418.
    key_x_mm, key_z_mm, shoe_z_mm = 100., 150., 48.
    y_travel_mm = key_y_mm / 2 + 75. + 4.
    force_N = load["force_315_N"]
    side_N = ASYMMETRIC_SHARE * force_N
    key = beam_midspan(force_N, span_mm, 150., key_x_mm, key_z_mm)
    key_skew = 4 * ASYMMETRIC_SHARE * (1 - ASYMMETRIC_SHARE)
    # 1.0 is conservative for either side reaction distribution's span moment.
    portal = beam_midspan(side_N, 180., 100., 80., 66.)
    portal_leg_N = side_N * (load["centroid_x_mm"] - 55.) / 180.
    stresses = dict(key=section_check(key["stress_MPa"], FORGED_700),
                    roof=section_check(portal["stress_MPa"], CAST),
                    post=section_check(portal_leg_N / (68 * 80), CAST))
    centre_x_mm = 145.
    key_mean_contact_MPa = press_pressure(side_N, key_x_mm - 10, 80 - 10,
                                          load["centroid_x_mm"] - centre_x_mm)
    crown = hertz_line(side_N, key_x_mm - 10, 80.)
    key_contact_MPa = max(key_mean_contact_MPa, crown["pressure_MPa"])
    area_mm2 = 314 * 125 - 274 * 85
    floor_I_mm4 = (314 * 125**3 - 274 * 85**3) / 12
    floor_flexure_mm = force_N * (8 * span_mm**3 - 4 * span_mm * 150**2 + 150**3) / (384 * E_MPa * floor_I_mm4)
    # Only the two vertical webs carry the Timoshenko shear term.
    floor_shear_mm = force_N * (2 * span_mm - 150) / (8 * G_MPa * (area_mm2 - 2 * 314 * 20))
    post_mm = portal_leg_N * 192 / (E_MPa * 68 * 80)
    shoe_compression_mm = force_N * shoe_z_mm / (E_MPa * 150 * (key_x_mm - 10))
    height_mm = (key["bending_mm"] + key["shear_mm"] + portal["bending_mm"] + portal["shear_mm"] +
                 floor_flexure_mm + floor_shear_mm + post_mm + shoe_compression_mm) / RELIEF_RATIO + .02

    # Optimistic flow-only lower bound, with full 265 L/min at operating pressure.
    # A Ø40/22 actuator is sized for a controlled 0.14 s triangular move.
    drive_d_mm, drive_rod_mm, move_s = 40., 22., .14
    key_mass_kg = key_x_mm * key_y_mm * key_z_mm * mass.STEEL_KG_MM3
    peak_speed_m_s = 2 * y_travel_mm / (move_s * 1000)
    accel_m_s2 = 4 * y_travel_mm / (move_s**2 * 1000)
    req_N = key_mass_kg * accel_m_s2 + 2 * 600
    cap_mm2 = pi * drive_d_mm**2 / 4
    annular_mm2 = pi * (drive_d_mm**2 - drive_rod_mm**2) / 4
    minimum_flow_time_s = (cap_mm2 + annular_mm2) * y_travel_mm * 60 / (1e6 * 265)
    added_cam_replaced_s = 2 * (move_s - 12 / 300)
    static, fatigue = strengths(stresses)
    return dict(reason="Опора сплошного блока по двум замкнутым боковым порталам, без изгиба стяжек.",
                static_factor=static, fatigue_factor=fatigue, sections=stresses,
                upper_working_contact_MPa=key_contact_MPa, contact_screen_MPa=.60 * 800,
                upper_planar_contact_MPa=key_mean_contact_MPa, upper_hertz=crown,
                height_at_300_mm=height_mm, analytic_height_excludes="Local nonlinear indentation",
                key_asymmetry_moment_multiplier=key_skew, beta_block_withdraw=wedge(force_N),
                mass=mass.full_block(key_x_mm, key_y_mm, key_z_mm, shoe_z_mm),
                geometry=dict(key_xyz_mm=[key_x_mm, key_y_mm, key_z_mm], key_locked_x_mm=[95., 195.],
                              shoe_z_mm=shoe_z_mm, relocated_cylinder_x_mm=55., key_top_z_mm=198.,
                              lateral_support_centres_y_mm=[-174., 174.], stroke_y_mm=y_travel_mm),
                drive=dict(bore_rod_mm=[drive_d_mm, drive_rod_mm], move_s=move_s,
                           peak_speed_m_s=peak_speed_m_s, peak_acceleration_m_s2=accel_m_s2,
                           ideal_actuation_N=req_N, peak_flow_L_min=peak_speed_m_s * cap_mm2 * .06,
                           retract_required_bar=req_N / annular_mm2 * 10, optimistic_volume_limited_roundtrip_s=minimum_flow_time_s),
                reference_cycle_s=baseline["pessimistic_s"] + added_cam_replaced_s,
                estimated_gate_cycle_s=baseline["gate_s"] + added_cam_replaced_s,
                manufacturing="Closed cast portals with line-machined windows. Load pads ground separately. External park guide on one side.")


def original_frame(load, baseline, frame):
    column_d_mm = frame["columns"]["smooth_span_diameter_mm"]
    span_mm = frame["columns"]["smooth_span_mm"]
    preload_N = frame["columns"]["preload_N_per_end"]
    inertia_mm4 = pi * column_d_mm**4 / 64
    preload_MPa = preload_N / (pi * column_d_mm**2 / 4)
    # Every existing column carries a quarter. Fixed ends are favorable.
    peak_column_N = load["force_315_N"] / 4
    bending_MPa = (peak_column_N * span_mm / 8) * column_d_mm / (2 * inertia_mm4)
    total_MPa = preload_MPa + bending_MPa
    fatigue = section_check(bending_MPa, COLUMNS)
    fatigue_amp_MPa = bending_MPa / (2 * RELIEF_RATIO)
    fatigue_mean_MPa = preload_MPa + fatigue_amp_MPa
    factor = fatigue["fatigue_strength_MPa"] / (fatigue_amp_MPa + fatigue["M_sigma"] * fatigue_mean_MPa)
    bridge = beam_midspan(load["force_315_N"], 240., 150., 105., 54.)
    bridge_strength = section_check(bridge["stress_MPa"], FORGED_800)
    pressure_MPa = press_pressure(ASYMMETRIC_SHARE * load["force_315_N"], 90., 60.)
    local_hertz_MPa = hertz_line(ASYMMETRIC_SHARE * load["force_315_N"], 90., 70.)["pressure_MPa"]
    bare_column_deflect_mm = peak_column_N / RELIEF_RATIO * span_mm**3 / (192 * E_MPa * inertia_mm4)
    return dict(reason="Проверка использования существующих колонн и траверс в качестве внешнего силового контура.",
                static_factor=min(500 / total_MPa, bridge_strength["static_factor"]),
                fatigue_factor=min(factor, bridge_strength["fatigue_factor_n_sigma_1"]),
                upper_working_contact_MPa=max(pressure_MPa, local_hertz_MPa), contact_screen_MPa=480.,
                height_at_300_mm=bare_column_deflect_mm + (bridge["bending_mm"] + bridge["shear_mm"]) / RELIEF_RATIO,
                column_only_height_at_300_mm=bare_column_deflect_mm, column_MPa=dict(preload=preload_MPa, bending=bending_MPa,
                                                                                   combined=total_MPa),
                bridge=bridge_strength, mass=mass.main_frame_block(),
                kinetics=dict(inherited_cam_stroke_mm=12., assumed_radial_key_stroke_mm=36.,
                              lock_time_lower_bound_s=12 / 300, unlock_time_lower_bound_s=12 / 300,
                              note="Optimistic reuse of T-2.1 cam timings; no credible unchanged frame interface."),
                reference_cycle_s=baseline["pessimistic_s"], estimated_gate_cycle_s=baseline["gate_s"],
                manufacturing="Bridge and pads mounted to column bosses. Existing axial qualification does not cover the transverse reaction.")


def closed_extension(upstream, baseline):
    # T-1.2b holds a 120 mm fully closed additional length. Its transfer peak is
    # sustained by the existing actuator; final compression is outside the window.
    peak_300_N = 292_000.
    transfer_315_N = peak_300_N * RELIEF_RATIO
    roof = beam_midspan(transfer_315_N, 190., 150., 110., 60.)
    section = section_check(roof["stress_MPa"], CAST)
    # Optimistic extra time for 120 mm in both directions on physical T-1.7d
    # main and rapid cylinders. Use minimum effective rapid area and maximum flow.
    main_rod_mm = 200.
    main_cap_mm2 = pi * 280**2 / 4
    main_annulus_mm2 = pi * (280**2 - main_rod_mm**2) / 4
    rapid_cylinders = yaml.safe_load((ROOT / "design/cylinders.t16.yaml").read_text(encoding="utf-8"))["cylinders"]
    rapid = next(row for row in rapid_cylinders if row["id"] == "CY-RAPID")
    rapid_bore_mm, rapid_rod_mm = rapid["bore_mm"], rapid["rod_mm"]
    rapid_out_mm2 = 2 * pi * rapid_bore_mm**2 / 4
    rapid_in_mm2 = 2 * pi * (rapid_bore_mm**2 - rapid_rod_mm**2) / 4
    forward_mm2 = min(main_annulus_mm2, rapid_out_mm2)
    return_mm2 = min(main_annulus_mm2, rapid_in_mm2)
    added_s = upstream["alternatives"]["B"]["cycle"]["0.64"]["cycle_s"] - upstream["alternatives"]["A"]["cycle"]["0.64"]["cycle_s"]
    ideal_rapid_added_s = (forward_mm2 + return_mm2) * 120 * 60 / (1e6 * 265)
    return dict(reason="Окончательное прессование целиком в закрытой зоне, нагрузка окна только при проталкивании.",
                static_factor=section["static_factor"], fatigue_factor=section["fatigue_factor_n_sigma_1"],
                height_at_300_mm=(roof["bending_mm"] + roof["shear_mm"]) / RELIEF_RATIO,
                upper_working_contact_MPa=transfer_315_N / (150 * 110), contact_screen_MPa=None,
                contact_note="Average material/roof pressure during transfer; no oscillating hardened lock pair.",
                roof=section, mass=mass.closed_zone(), added_main_stroke_mm=120., installed_main_stroke_mm=426.,
                peak_shoe_300_N=peak_300_N, available_shoe_hydraulic_at_transfer_N=331_000.,
                ideal_extra_rapid_oil_time_s=ideal_rapid_added_s, analogous_extra_time_s=added_s,
                reference_cycle_s=baseline["pessimistic_s"] + added_s,
                estimated_gate_cycle_s=baseline["gate_s"] + added_s,
                requires_main_frame_or_stroke_change=True, mechanical_drive=None,
                manufacturing="Longer chamber blank and longer manufactured baseline columns, main and rapid cylinders.")


def rotor_check(force_N, geom, tooth_share):
    shank_r_mm, head_r_mm, sleeve_r_mm, height_mm = (
        geom[name] for name in ("shank_r_mm", "head_r_mm", "sleeve_r_mm", "tooth_height_mm"))
    angle_rad = radians(55)
    mean_radius_mm = (shank_r_mm + head_r_mm) / 2
    contact_length_mm = head_r_mm - shank_r_mm - 2 * HEEL_RADIUS_MM
    peak_tooth_N = force_N * tooth_share
    hertz = hertz_line(peak_tooth_N, contact_length_mm, mean_radius_mm * angle_rad)
    area_mm2 = pi * shank_r_mm**2
    # Root checks at the smaller stationary tooth and larger rotating tooth.
    radial_arm_mm = (head_r_mm - shank_r_mm) / 2
    def tooth_stress(radius_mm):
        root_b_mm = radius_mm * angle_rad
        bending_MPa = 6 * peak_tooth_N * radial_arm_mm / (root_b_mm * height_mm**2)
        shear_MPa = 1.5 * peak_tooth_N / (root_b_mm * height_mm)
        return sqrt(bending_MPa**2 + 3 * shear_MPa**2)

    tooth = section_check(tooth_stress(shank_r_mm), FORGED_700)
    moving_tooth = section_check(tooth_stress(head_r_mm), FORGED_600)
    # The machining clearance is included before the fillet deductions.
    bearing_annulus_mm2 = mass.annulus_mm2(sleeve_r_mm - 5, head_r_mm + 1 + 5)
    seat_area_mm2 = mass.annulus_mm2(geom["foot_r_mm"] - 5, shank_r_mm + 5)
    post_elongation_mm = force_N * geom["seat_length_mm"] / (E_MPa * area_mm2 * RELIEF_RATIO)
    return dict(tooth=tooth, moving_tooth=moving_tooth, post=section_check(force_N / area_mm2, FORGED_700),
                force_N=force_N, peak_tooth_N=peak_tooth_N, hertz=hertz,
                pad_mean_MPa=peak_tooth_N / (contact_length_mm * (mean_radius_mm * angle_rad - 10)),
                shoulder_bearing_MPa=force_N / bearing_annulus_mm2,
                foot_bearing_MPa=force_N / seat_area_mm2,
                elongation_300_mm=post_elongation_mm,
                hertz_assumption="Finite uniform radial line, circumferential crown, no pad tilt.")


def rotary_bayonet(load, upstream, baseline):
    front_ratio = (load["centroid_x_mm"] - REAR["x_mm"]) / (FRONT["x_mm"] - REAR["x_mm"])
    front_force_N = load["force_315_N"] * ASYMMETRIC_SHARE * front_ratio
    rear_force_N = load["force_315_N"] * ASYMMETRIC_SHARE * (1 - front_ratio)
    front = rotor_check(front_force_N, FRONT, 1.2 / 3)
    rear = rotor_check(rear_force_N, REAR, 1.2 / 3)
    nominal = {"front": rotor_check(front_force_N, FRONT, 1/3), "rear": rotor_check(rear_force_N, REAR, 1/3)}
    earlier_profile = []
    for dose_name, scenarios in upstream["shoe_load"]["samples"].items():
        for level, cases in scenarios.items():
            for case_name, case in cases.items():
                p = pressure_integrals(case)
                if p is None or p["centroid_x_mm"] < FRONT["x_mm"]:
                    continue
                # With the rear support slack, the front three teeth take the
                # fore–aft moment. Rotate one of their centres toward the gate.
                e_mm = p["centroid_x_mm"] - FRONT["x_mm"]
                r_mm = (FRONT["shank_r_mm"] + FRONT["head_r_mm"]) / 2
                share = (1 + 2 * e_mm / r_mm) / 3
                available_front_shank_N = p["force_315_N"] * ASYMMETRIC_SHARE
                row = rotor_check(available_front_shank_N, FRONT, share * 1.2)
                earlier_profile.append(dict(label=[dose_name, level, case_name], e_mm=e_mm,
                                            front_peak_tooth_N=row["peak_tooth_N"],
                                            front_peak_contact_MPa=row["hertz"]["pressure_MPa"],
                                            tooth_fatigue_factor=row["tooth"]["fatigue_factor_n_sigma_1"]))

    side_y_mm = 136.
    shoe_arm_mm = side_y_mm - 75
    shoe_effective_width_mm, shoe_ligament_mm = 112., 135.
    shoe_I_mm4 = shoe_effective_width_mm * shoe_ligament_mm**3 / 12
    shoe_bend_MPa = front_force_N * shoe_arm_mm * shoe_ligament_mm / (2 * shoe_I_mm4)
    shoe_shear_MPa = 1.5 * front_force_N / (shoe_effective_width_mm * shoe_ligament_mm)
    shoe_check = section_check(sqrt(shoe_bend_MPa**2 + 3 * shoe_shear_MPa**2), FORGED_600)
    shoe_flexure_mm = front_force_N * shoe_arm_mm**3 / (3 * E_MPa * shoe_I_mm4)
    shoe_shear_mm = front_force_N * shoe_arm_mm / ((5/6) * G_MPa * shoe_effective_width_mm * shoe_ligament_mm)

    floor_height_mm, floor_width_mm, floor_wall_mm = 125., 284., 20.
    span_mm = 2 * side_y_mm
    force_N = load["force_315_N"]
    floor_I_mm4 = (floor_width_mm * floor_height_mm**3 -
                   (floor_width_mm - 2 * floor_wall_mm) * (floor_height_mm - 2 * floor_wall_mm)**3) / 12
    floor_bend_MPa = force_N * (2 * span_mm - 150) / 8 * floor_height_mm / (2 * floor_I_mm4)
    floor_shear_MPa = force_N / (2 * 2 * floor_wall_mm * (floor_height_mm - 2 * floor_wall_mm))
    floor_check = section_check(sqrt(floor_bend_MPa**2 + 3 * floor_shear_MPa**2), CAST)
    floor_flexure_mm = force_N * (8 * span_mm**3 - 4 * span_mm * 150**2 + 150**3) / (384 * E_MPa * floor_I_mm4)
    floor_shear_mm = force_N * (2 * span_mm - 150) / (8 * G_MPa * 2 * floor_wall_mm * (floor_height_mm - 2 * floor_wall_mm))
    hertz_local_mm = sum(2 * row["hertz"]["pressure_MPa"] * (row["hertz"]["half_width_mm"]**2) /
                        (E_STAR_MPa * row["hertz"]["crown_radius_mm"]) for row in (front,))
    height_mm = (front["elongation_300_mm"] + (floor_flexure_mm + floor_shear_mm + shoe_flexure_mm + shoe_shear_mm +
                                               hertz_local_mm) / RELIEF_RATIO + .02)

    package = mass.bayonet(FRONT, REAR, 165 / 360, floor_height_mm)
    r_outer_mm, r_inner_mm = FRONT["sleeve_r_mm"], FRONT["head_r_mm"] + 1
    front_rot_kgm2 = (package["rows_kg"]["front_collar_sleeves"] * (r_outer_mm**2 + r_inner_mm**2) +
                     package["rows_kg"]["front_collar_lobes"] * (FRONT["shank_r_mm"]**2 + FRONT["head_r_mm"]**2)) / 2e6
    r_outer_mm, r_inner_mm = REAR["sleeve_r_mm"], REAR["head_r_mm"] + 1
    rear_rot_kgm2 = (package["rows_kg"]["rear_collar_sleeves"] * (r_outer_mm**2 + r_inner_mm**2) +
                    package["rows_kg"]["rear_collar_lobes"] * (REAR["shank_r_mm"]**2 + REAR["head_r_mm"]**2)) / 2e6
    move_s = .08
    theta = pi / 3
    input_N = ((front_rot_kgm2 + rear_rot_kgm2) * 4 * theta / move_s**2) * theta / (.012 * .60)
    kinetic_corner_s = 2 * (move_s - 12 / 300)
    stresses = dict(front_post=front["post"], front_tooth=front["tooth"], front_moving_tooth=front["moving_tooth"],
                    rear_post=rear["post"], rear_tooth=rear["tooth"], rear_moving_tooth=rear["moving_tooth"],
                    shoe=shoe_check, box_floor=floor_check)
    static, fatigue = strengths(stresses)
    if earlier_profile:
        fatigue = min(fatigue, *(row["tooth_fatigue_factor"] for row in earlier_profile))
    return dict(reason="Четыре соосных байонетных опоры снимают эксцентричный изгиб в силовом крепеже.",
                static_factor=static, fatigue_factor=fatigue, sections=stresses,
                upper_working_contact_MPa=max(front["hertz"]["pressure_MPa"], rear["hertz"]["pressure_MPa"],
                                              *(row["front_peak_contact_MPa"] for row in earlier_profile)),
                contact_screen_MPa=.6 * 800., backing_contact_screens_MPa=dict(shoe=360., cast_foot=390.),
                height_at_300_mm=height_mm, mass=package,
                geometry=dict(front=FRONT, rear=REAR, y_mm=[-side_y_mm, side_y_mm],
                              tooth_sector_deg=55., unlocking_rotation_deg=60., root_radius_mm=15.,
                              edge_radius_mm=5., crown_mm=.10, floor_box_height_mm=floor_height_mm,
                              moving_y_outer_mm=side_y_mm+FRONT["sleeve_r_mm"]+7.),
                drive=dict(lock_time_s=move_s, unlock_time_s=move_s, rod_extra_stroke_mm=12.,
                           combined_rotor_inertia_kg_m2=front_rot_kgm2 + rear_rot_kgm2,
                           stem_inertia_force_N=input_N, unloaded_stem_guide_force_assumption_N=3000.,
                           peak_stem_speed_mm_s=2*12/move_s),
                reference_cycle_s=baseline["pessimistic_s"] + kinetic_corner_s,
                estimated_gate_cycle_s=baseline["gate_s"] + kinetic_corner_s,
                front=front, rear=rear, nominal_equal_sharing=nominal, other_eccentric_press_cases=earlier_profile,
                manufacturing="Three sectors per head, three per sleeve. Ground interchangeable pads. Lift-out post with an integral foot, no service-load thread.")


def hydraulic_reference(load):
    area_mm2 = pi * 125**2 / 4
    oil_length_lower_bound_mm = 380.
    force_N = load["force_300_N"]
    return dict(locked_pressure_315_bar=load["force_315_N"] / area_mm2 * 10,
                ideal_oil_only_travel_300_mm=force_N * oil_length_lower_bound_mm / (1400 * area_mm2),
                full_extension_minimum_oil_length_mm=oil_length_lower_bound_mm,
                section_area_mm2=area_mm2, bore_mm=125., reference_oversized_bore_mm=255.,
                reference_oversized_cycle_s=9.850)


def run():
    upstream = read_json(ROOT / "calc/T-1.2b/results.json")
    load = pressure_integrals(upstream["shoe_load"]["samples"]["upper_dose"]["reserve"]["high"])
    frame = yaml.safe_load((ROOT / "design/frame.t17d.yaml").read_text(encoding="utf-8"))
    baseline = dict(realistic_s=5.520, pessimistic_s=5.884, gate_s=5.823772630624717,
                    source="ops/reports/T-2.1/report.md and calc/T-2.1/results.json")
    alternatives = dict(full_width_block=full_width(load, baseline), main_frame=original_frame(load, baseline, frame),
                        closed_extension=closed_extension(upstream, baseline), rotary_bayonet=rotary_bayonet(load, upstream, baseline))
    for data in alternatives.values():
        data["screen_pass"] = dict(static=data["static_factor"] >= 1.5,
                                  fatigue=data["fatigue_factor"] >= 1.,
                                  contact=(data["upper_working_contact_MPa"] <= data["contact_screen_MPa"]
                                           if data["contact_screen_MPa"] is not None else None),
                                  height=data["height_at_300_mm"] <= .5,
                                  delta_mass=data["mass"]["delta_kg"] <= 40.,
                                  reference_cycle=data["reference_cycle_s"] <= 6.,
                                  gate_cycle=data["estimated_gate_cycle_s"] <= 5.95)
    return dict(load=load, baseline=baseline, candidates=alternatives, hydraulic_reference=hydraulic_reference(load))


if __name__ == "__main__":
    write_json(HERE / "results.json", run())
