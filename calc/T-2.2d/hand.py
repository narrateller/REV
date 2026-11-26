"""Four-post bayonet screen in N, mm and MPa with integral, unthreaded feet."""

from itertools import product
from math import asin, fsum, hypot, log10, pi, radians, sqrt

from mass import STEEL_KG_MM3, ledger


E_MPa = 210_000.
NU = .30
G_MPa = E_MPa / (2 * (1 + NU))
E_STAR_MPa = E_MPa / (2 * (1 - NU**2))
RELIEF_RATIO = 315 / 300
SIDE_SHARE = .64
TOOTH_SHARE = 1.20 / 3
ENGAGEMENT_DEG = 55.
ROTATION_DEG = 60.
EDGE_R_MM = 5.
ROOT_R_MM = 15.
CROWN_MM = .10
CONTACT_SCREEN_MPa = 480.
CAST_SCREEN_MPa = 390.
RUNNING_CLEARANCE_MM = 3.
SEATING_TRAVEL_MM = .02


def strength(stress_315_MPa, material, *, compressive_mean=False):
    Rp02_MPa, Rm_MPa, cast = material
    roughness = 1 - (.20 if cast else .22) * log10(6.3) * log10(2 * Rm_MPa / 400)
    sensitivity = .00035 * Rm_MPa + (.05 if cast else -.1)
    amplitude_MPa = stress_315_MPa / (2 * RELIEF_RATIO)
    allowable_MPa = (.34 if cast else .40) * Rm_MPa * roughness * 10**(-1 / 15) / (1.5 * (1.25 if cast else 1))
    demand_MPa = amplitude_MPa if compressive_mean else amplitude_MPa * (1 + sensitivity)
    return dict(stress_315_MPa=stress_315_MPa, Rp02_MPa=Rp02_MPa, Rm_MPa=Rm_MPa,
                static_factor=Rp02_MPa / stress_315_MPa, FKM=allowable_MPa / demand_MPa,
                allowable_amplitude_MPa=allowable_MPa, equivalent_amplitude_MPa=demand_MPa)


def section(force_315_N, span_mm, load_width_mm, axial_width_mm, depth_mm, skin_mm, web_width_mm):
    inner_h_mm = depth_mm - 2 * skin_mm
    web_area_mm2 = web_width_mm * inner_h_mm
    area_mm2 = 2 * skin_mm * axial_width_mm + web_area_mm2
    inertia_mm4 = (axial_width_mm * depth_mm**3 - (axial_width_mm - web_width_mm) * inner_h_mm**3) / 12
    moment_Nmm = force_315_N * (2 * span_mm - load_width_mm) / 8
    bending_MPa = (2 * SIDE_SHARE) * moment_Nmm * depth_mm / (2 * inertia_mm4)
    shear_MPa = 1.5 * SIDE_SHARE * force_315_N / web_area_mm2
    bend_mm = (force_315_N * (8 * span_mm**3 - 4 * span_mm * load_width_mm**2 + load_width_mm**3)
               / (384 * E_MPa * inertia_mm4))
    shear_mm = force_315_N * (2 * span_mm - load_width_mm) / (8 * G_MPa * web_area_mm2)
    return dict(stress_315_MPa=hypot(bending_MPa, sqrt(3) * shear_MPa),
                area_mm2=area_mm2, I_mm4=inertia_mm4, flexure_300_mm=bend_mm / RELIEF_RATIO,
                shear_300_mm=shear_mm / RELIEF_RATIO)


def hertz(force_N, length_mm, gross_width_mm):
    radius_mm = gross_width_mm**2 / (8 * CROWN_MM) + CROWN_MM / 2
    half_width_mm = sqrt(4 * force_N * radius_mm / (pi * length_mm * E_STAR_MPa))
    available_half_width_mm = gross_width_mm / 2 - EDGE_R_MM
    fraction = min(1., available_half_width_mm / half_width_mm)
    integral_mm = half_width_mm * (asin(fraction) + fraction * sqrt(1 - fraction**2))
    return dict(peak_MPa=force_N / (length_mm * integral_mm), half_width_mm=half_width_mm,
                crown_radius_mm=radius_mm, footprint_clipped=fraction < 1.,
                net_mean_MPa=force_N / (length_mm * 2 * available_half_width_mm))


def rotor(force_N, g, share):
    theta = radians(ENGAGEMENT_DEG)
    shank_r_mm, head_r_mm, collar_r_mm, foot_r_mm, height_mm = (
        g[name] for name in ("shank_r_mm", "head_r_mm", "collar_r_mm", "foot_r_mm", "tooth_height_mm"))
    pitch_r_mm = (shank_r_mm + head_r_mm) / 2
    tooth_N = force_N * share
    contact_length_mm = head_r_mm - shank_r_mm - 2 * EDGE_R_MM
    # Moving sleeve is open to the post head OD in the pass-through sectors.
    # Reserve 1 mm radial insertion clearance, then remove both R5 seat edges.
    shank_area_mm2 = pi * shank_r_mm**2
    shank_I_mm4 = pi * shank_r_mm**4 / 4
    # One sector takes share, the other two take equal fractions. The
    # remaining first moment is resisted by the guide, shank and foot.
    tooth_eccentricity_mm = pitch_r_mm * (3 * share - 1) / 2
    tooth_moment_Nmm = force_N * tooth_eccentricity_mm

    def bearing(inner_mm, outer_mm):
        area_mm2 = pi * (outer_mm**2 - inner_mm**2)
        I_mm4 = pi / 4 * (outer_mm**4 - inner_mm**4)
        p_MPa = force_N / area_mm2
        bending_MPa = tooth_moment_Nmm * outer_mm / I_mm4
        return p_MPa + bending_MPa, p_MPa - bending_MPa

    shoulder_max_MPa, shoulder_min_MPa = bearing(head_r_mm + 1 + EDGE_R_MM, collar_r_mm - EDGE_R_MM)
    foot_max_MPa, foot_min_MPa = bearing(shank_r_mm + EDGE_R_MM, foot_r_mm - EDGE_R_MM)
    arm_mm = (head_r_mm - shank_r_mm) / 2
    teeth = {}
    for name, root_r_mm in (("fixed_tooth", shank_r_mm), ("rotating_tooth", head_r_mm)):
        b_mm = root_r_mm * theta
        bending_MPa = 6 * tooth_N * arm_mm / (b_mm * height_mm**2)
        shear_MPa = 1.5 * tooth_N / (b_mm * height_mm)
        compliance_mm_N = (arm_mm**3 / (3 * E_MPa * b_mm * height_mm**3 / 12)
                           + arm_mm / ((5 / 6) * G_MPa * b_mm * height_mm))
        teeth[name] = strength(hypot(bending_MPa, sqrt(3) * shear_MPa), (700., 900., False)) | dict(
            compliance_mm_N=compliance_mm_N)
    pair_mm_N = fsum(t["compliance_mm_N"] for t in teeth.values())
    at_300 = hertz(tooth_N / RELIEF_RATIO, contact_length_mm, pitch_r_mm * theta)
    contact = hertz(tooth_N, contact_length_mm, pitch_r_mm * theta)
    pad_compression_mm = at_300["peak_MPa"] * contact_length_mm / E_STAR_MPa
    foot_stress_MPa = sqrt(3) * force_N / (2 * pi * shank_r_mm * (28. - EDGE_R_MM))
    post_stress_MPa = force_N / shank_area_mm2 + tooth_moment_Nmm * shank_r_mm / shank_I_mm4
    return dict(force_315_N=force_N, tooth_force_315_N=tooth_N, tooth_pitch_r_mm=pitch_r_mm,
                tooth_eccentricity_mm=tooth_eccentricity_mm, tooth_moment_Nm=tooth_moment_Nmm / 1000,
                contact=contact, teeth=teeth, bearing_shoulder_MPa=shoulder_max_MPa,
                bearing_foot_MPa=foot_max_MPa, bearing_shoulder_min_MPa=shoulder_min_MPa,
                bearing_foot_min_MPa=foot_min_MPa, foot=strength(foot_stress_MPa, (700., 900., False)),
                post=strength(post_stress_MPa, (700., 900., False)),
                post_extension_300_mm=force_N * g["post_length_mm"] / (RELIEF_RATIO * E_MPa * shank_area_mm2),
                tooth_branches_300_mm=tooth_N * pair_mm_N / RELIEF_RATIO,
                pad_compression_300_mm=pad_compression_mm,
                gap_difference_for_120pct_mm=.10 * force_N * pair_mm_N / RELIEF_RATIO)


def station_geometry(x_mm, y_mm, gate, shank_r_mm, head_r_mm, collar_r_mm, tooth_height_mm):
    guard_r_mm = collar_r_mm + 7.
    gate_face_x_mm = gate["face_x_mm"]
    gate_upstream_x_mm = gate_face_x_mm - 6.
    gate_half_width_mm = gate["plate_outline_mm_R"][0] / 2
    # Conservative rectangular plan intersection envelops the tapered ribs
    # and all vertical positions of the 54 mm gate including the 6 mm ribs.
    y_mm = max(y_mm, 75. + RUNNING_CLEARANCE_MM + head_r_mm)
    dx_mm = max(0., gate_upstream_x_mm - x_mm)
    required_radius_mm = guard_r_mm + RUNNING_CLEARANCE_MM
    if dx_mm < required_radius_mm:
        y_mm = max(y_mm, gate_half_width_mm + sqrt(required_radius_mm**2 - dx_mm**2))
    clearance_mm = hypot(dx_mm, max(0., y_mm - gate_half_width_mm)) - guard_r_mm
    return dict(x_mm=x_mm, y_mm=y_mm, shank_r_mm=shank_r_mm, head_r_mm=head_r_mm,
                collar_r_mm=collar_r_mm, foot_r_mm=min(collar_r_mm, shank_r_mm + 26.),
                outer_envelope_r_mm=guard_r_mm, tooth_height_mm=tooth_height_mm, post_length_mm=155.,
                foot_bearing_z_mm=-65., working_tooth_z_mm=90., gate_swept_clearance_mm=clearance_mm)


def part_volumes(stations):
    def annulus(r_outer_mm, r_inner_mm):
        return pi * (r_outer_mm**2 - r_inner_mm**2)

    fractions = 3 * ENGAGEMENT_DEG / 360
    rows_mm3 = {}
    inertia_kg_m2 = 0.
    for label, g in stations.items():
        shank, head, collar, foot, h = (g[k] for k in (
            "shank_r_mm", "head_r_mm", "collar_r_mm", "foot_r_mm", "tooth_height_mm"))
        lobes_mm3 = 2 * fractions * annulus(head, shank) * h
        sleeve_mm3 = 2 * annulus(collar, head + 1) * h
        rows_mm3.update({f"{label}_shanks_two": 2 * pi * shank**2 * (g["post_length_mm"] + h),
                         f"{label}_integral_feet_two": 2 * annulus(foot, shank) * 28,
                         f"{label}_fixed_teeth": lobes_mm3,
                         f"{label}_rotating_teeth": lobes_mm3,
                         f"{label}_rotating_sleeves": sleeve_mm3,
                         f"{label}_carrier_lands": 2 * annulus(collar + 7, head + 1) * 22})
        inertia_kg_m2 += STEEL_KG_MM3 * (lobes_mm3 * (shank**2 + head**2)
                                       + sleeve_mm3 * ((head + 1)**2 + collar**2)) / 2e6
    return rows_mm3, inertia_kg_m2


def drive_screen(inertia_kg_m2, design_N, centroid_pitch_r_mm):
    angle_rad = radians(ROTATION_DEG)
    stroke_mm, eta = 12., .60
    unloaded_guide_N = 3000.
    reflected_torque_Nm = stroke_mm / 1000 * eta / angle_rad
    rows = []
    for duration_s in (.04, .06, .08):
        accel_rad_s2 = 4 * angle_rad / duration_s**2
        inertial_N = inertia_kg_m2 * accel_rad_s2 / reflected_torque_Nm
        rows.append(dict(duration_s=duration_s, ideal_inertial_stem_force_N=inertial_N,
                         unloaded_stem_force_N=inertial_N + unloaded_guide_N,
                         triangular_peak_stem_speed_mm_s=2 * stroke_mm / duration_s))
    torque_per_N = .15 * centroid_pitch_r_mm / 1000
    return dict(rows=rows, stroke_mm=stroke_mm, rotation_deg=ROTATION_DEG,
                combined_rotor_inertia_kg_m2=inertia_kg_m2,
                transmission_eta_assumed=eta, unloaded_guide_force_assumed_N=unloaded_guide_N,
                loaded_friction_torque_Nm=design_N * torque_per_N,
                loaded_quasistatic_unlock_stem_force_N=design_N * torque_per_N / reflected_torque_Nm,
                added_static_stem_force_per_kN_residual_N=1000 * torque_per_N / reflected_torque_Nm)


def candidates(roof, shift, gate):
    load = roof["load"]["315_bar"]["grid"]
    shoe_peak = roof["load"]["315_bar"]["peak"]
    roof_peak_N = max(row["roof_force_N"] for row in load)
    shoe_peak_N = shoe_peak["shoe_force_N"]
    floor_peak_N = max(row["shoe_force_N"] + row["roof_force_N"] for row in load)
    roof_mm = roof["roof_mm"]
    roof_depth_mm = 115.
    # Solid machined cap integral with transverse wall shoulders. Screening
    # span is the open product width and takes no closed-frame restraint credit.
    roof_section = section(roof_peak_N, 150., 150., roof_mm, roof_depth_mm, 0., roof_mm)
    roof_check = strength(roof_section["stress_315_MPa"], (600., 800., False))
    for front_x_mm, rear_x_mm, post_r_mm, radial_mm, tooth_h_mm, rear_size_mm in product(
            (174., 184., 194.), (14., 38., 62.), (27., 31., 35.), (28., 32., 36.), (54., 62., 70.), (23., 27.)):
        head_r_mm = post_r_mm + radial_mm
        rear_head_r_mm = rear_size_mm + 26.
        stations = dict(front=station_geometry(front_x_mm, 136., gate, post_r_mm, head_r_mm, head_r_mm + 19., tooth_h_mm),
                        rear=station_geometry(rear_x_mm, 130., gate, rear_size_mm, rear_head_r_mm,
                                              rear_head_r_mm + 18., 50.))
        front, rear = stations["front"], stations["rear"]
        centre_spacing_mm = hypot(front_x_mm - rear_x_mm, front["y_mm"] - rear["y_mm"])
        if centre_spacing_mm < front["outer_envelope_r_mm"] + rear["outer_envelope_r_mm"] + RUNNING_CLEARANCE_MM:
            # Adjacent rotor envelopes occupy the same vertical levels.
            continue
        fraction = (shoe_peak["centroid_x_mm"] - rear_x_mm) / (front_x_mm - rear_x_mm)
        share_rows = [(row["centroid_x_mm"] - rear_x_mm) / (front_x_mm - rear_x_mm) for row in load]
        if min(share_rows) < 0 or max(share_rows) > 1:
            continue
        front_N = max(row["shoe_force_N"] * weight * SIDE_SHARE for row, weight in zip(load, share_rows))
        rear_N = max(row["shoe_force_N"] * (1 - weight) * SIDE_SHARE for row, weight in zip(load, share_rows))
        checks = {"front": rotor(front_N, front, TOOTH_SHARE), "rear": rotor(rear_N, rear, TOOTH_SHARE)}
        volumes_mm3, inertial = part_volumes(stations)
        chamfer_x_mm = (front_x_mm - rear_x_mm)
        avg_span_mm = front["y_mm"] + rear["y_mm"]
        span_mm = 2 * (rear["y_mm"] + fraction * (front["y_mm"] - rear["y_mm"]))
        def column_delta_mm(item):
            return fsum(item[key] for key in ("post_extension_300_mm", "tooth_branches_300_mm", "pad_compression_300_mm"))

        # The controlling side has the longest stand extensions. Use the
        # larger end value at the shoe, allowing for its fore/aft rotation.
        rotor_delta_mm = max(map(column_delta_mm, checks.values()))
        for shoe_h_mm, floor_h_mm, skin_mm, shoe_web_mm, floor_web_mm in product(
                (112., 136., 160., 185.), (125., 150., 175., 200., 225.), (14., 20.), (12., 18., 23.), (12., 18., 23.)):
            shoe_section = section(shoe_peak_N, span_mm, 150., 200., shoe_h_mm, skin_mm, 4 * shoe_web_mm)
            floor_section = section(floor_peak_N, span_mm, 150., 280., floor_h_mm, skin_mm, 4 * floor_web_mm)
            shoe_material = (500., 750., False) if shoe_h_mm > 160 else (600., 800., False)
            shoe_check = strength(shoe_section["stress_315_MPa"], shoe_material)
            floor_check = strength(floor_section["stress_315_MPa"], (650., 800., True))
            shoe_defl_mm = shoe_section["flexure_300_mm"] + shoe_section["shear_300_mm"]
            floor_defl_mm = floor_section["flexure_300_mm"] + floor_section["shear_300_mm"]
            roof_defl_mm = roof_section["flexure_300_mm"] + roof_section["shear_300_mm"]
            height_mm = floor_defl_mm + max(roof_defl_mm, shoe_defl_mm + rotor_delta_mm + SEATING_TRAVEL_MM)
            rows_kg = {name: vol * STEEL_KG_MM3 for name, vol in (volumes_mm3 | {
                "moving_crosshead": shoe_section["area_mm2"] * avg_span_mm + 200 * 150 * 35,
                "bottom_cast_box": floor_section["area_mm2"] * (avg_span_mm + 44.),
                "bottom_end_diaphragms": 2 * (280. - 4 * floor_web_mm) * 16. * (floor_h_mm - 2 * skin_mm),
                "side_walls_and_guides": 2 * (260 + roof_mm) * 38 * 60,
                "closed_roof_and_side_haunches": roof_mm * (226 * roof_depth_mm + 2 * 38 * 30),
            }).items()}
            rows_kg.update(inserts_and_retainers=5., synchronizer_and_guards=7., interfaces_and_local_ribs=10.)
            mass = ledger(rows_kg, shift)
            all_sections = {"shoe": shoe_check, "floor": floor_check, "roof": roof_check}
            for label, check in checks.items():
                all_sections[label + "_post"] = check["post"]
                all_sections[label + "_foot"] = check["foot"]
                all_sections.update({f"{label}_{name}": value for name, value in check["teeth"].items()})
            static = min(row["static_factor"] for row in all_sections.values())
            fatigue = min(row["FKM"] for row in all_sections.values())
            peak_contact_MPa = max(row["contact"]["peak_MPa"] for row in checks.values())
            backing_pass = all(0 <= row["bearing_shoulder_min_MPa"] <= row["bearing_shoulder_MPa"] <= CONTACT_SCREEN_MPa
                               and 0 <= row["bearing_foot_min_MPa"] <= row["bearing_foot_MPa"] <= CAST_SCREEN_MPa
                               for row in checks.values())
            yield dict(stations=stations, shoe_h_mm=shoe_h_mm, floor_h_mm=floor_h_mm,
                       shoe_face_to_box_mm=35., face_skin_mm=skin_mm, roof_depth_mm=roof_depth_mm,
                       shoe_four_webs_each_mm=shoe_web_mm, floor_four_webs_each_mm=floor_web_mm,
                       root_radius_mm=ROOT_R_MM, crown_mm=CROWN_MM,
                       axial_station_spacing_mm=chamfer_x_mm, horizontal_station_clearance_mm=centre_spacing_mm
                       - front["outer_envelope_r_mm"] - rear["outer_envelope_r_mm"],
                       effective_span_mm=span_mm, equivalent_span_assumption="Interpolation at axial load centroid",
                       mass=mass, support_checks=checks, strength_sections=all_sections,
                       static_factor=static, FKM=fatigue, contact_peak_MPa=peak_contact_MPa,
                       contact_screen_MPa=CONTACT_SCREEN_MPa, feet_contact_screen_MPa=CAST_SCREEN_MPa,
                       contact_pass=backing_pass and peak_contact_MPa <= CONTACT_SCREEN_MPa,
                       height_300_mm=height_mm, delta_height_300_mm=dict(shoe=shoe_defl_mm,
                           floor=floor_defl_mm, roof=roof_defl_mm, posts_teeth_contact=rotor_delta_mm,
                           seating=SEATING_TRAVEL_MM),
                       drive=drive_screen(inertial, shoe_peak_N, checks["front"]["tooth_pitch_r_mm"]))


def calculate(roof, shift, gate):
    result = dict(checked_candidates=0, candidates_within_60_kg=0, candidates_within_40_kg=0,
                  candidates_meeting_height_and_FKM=0, minimum_mass=None, minimum_height=None,
                  minimum_height_within_40_kg=None, minimum_height_with_FKM=None,
                  maximum_FKM=None, best=None, selected=None)

    def delta_kg(row):
        return row["mass"]["delta_chamber_kg"]

    def worst_utilization(row):
        return max(1.1 / row["FKM"], row["height_300_mm"] / .5, 1.5 / row["static_factor"],
                   row["contact_peak_MPa"] / CONTACT_SCREEN_MPa), delta_kg(row)

    def record(label, row, key):
        if result[label] is None or key(row) < key(result[label]):
            result[label] = row

    for row in candidates(roof, shift, gate):
        result["checked_candidates"] += 1
        record("minimum_mass", row, delta_kg)
        if delta_kg(row) > 60.:
            continue
        result["candidates_within_60_kg"] += 1
        if delta_kg(row) <= 40.:
            result["candidates_within_40_kg"] += 1
            record("minimum_height_within_40_kg", row, lambda record: record["height_300_mm"])
        record("minimum_height", row, lambda record: record["height_300_mm"])
        record("maximum_FKM", row, lambda record: (-record["FKM"], record["height_300_mm"]))
        record("best", row, worst_utilization)
        if row["FKM"] < 1.1:
            continue
        record("minimum_height_with_FKM", row, lambda record: record["height_300_mm"])
        if row["height_300_mm"] > .5:
            continue
        result["candidates_meeting_height_and_FKM"] += 1
        if row["static_factor"] >= 1.5 and row["contact_pass"]:
            record("selected", row, delta_kg)
    return result | dict(passes=result["selected"] is not None)
