"""Sections, bearing strips and chamber opening screens in N, mm, MPa."""

from itertools import product
from math import pi, sqrt

from layout import (CROWN_MM, EDGE_R_MM, FLOOR_SKIN_DEPTH_MM, KEY_CAM, KEY_CLOSED_Y_MM,
                    LOCK_LOWER_Y_MM, LOCK_UPPER_Y_MM, ROOT_R_MM, SEAT_ALLOWANCE_MM,
                    SHOE_ABS_Y_MAX_MM, STATIONS, WEAR_LAND_DEPTH_MM, REAR_FLOOR_DEPTH_MM, Layout, interface)
from loads import (PROOF_SKEW_X_MM, SKEW_FRACTION, final_envelopes, janssen, main_cylinder_force_N,
                   read_json, transition_cases)
from mass import DENSITY_KG_MM3, budget
from prior.hand import CAST, E_MPa, E_STAR_MPa, G_MPa, axial_bridges, beam, distribute, extrema, strength

FORGED_BLOCK = (700., 900., False)
FORGED_SHOE = (700., 900., False)
FORGED_KEY = (800., 1000., False)
PRESSURE_RATIO = 315 / 300
SHEAR_FACTOR = 5 / 6
SHORTEST_LOADED_MM = 40. / 1.23


def nominal(normal_MPa, shear_MPa, material, bending_MPa=0.):
    return strength(bending_MPa, shear_MPa, material, normal_MPa=normal_MPa)


def ring_hand(layout, load):
    """Closed ring per 1 mm along X, screened with pin ends for flexure."""
    p_MPa = load["roof"]["inlet_MPa"]
    force_N = 150. * p_MPa
    wall_mm = layout.roof_wall_mm
    span_mm = 150. + wall_mm
    material = CAST if layout.material == "cast" else FORGED_BLOCK
    roof = beam(force_N, span_mm, 150., 1., layout.roof_band_mm)
    floor = beam(force_N, span_mm, 150., 1., layout.floor_band_mm)
    side_MPa = SKEW_FRACTION * force_N / wall_mm
    full_span_mm = 60. + (layout.roof_band_mm + layout.floor_band_mm) / 2
    side_stretch_mm = side_MPa * full_span_mm / E_MPa
    shoulder_mm = side_MPa * 28. / E_MPa
    fixed_mm = sum(b["fixed_bend_mm"] + b["centroid_shear_mm"] for b in (roof, floor))
    flexure_mm = sum(b["bend_mm"] + b["shear_mm"] for b in (roof, floor))
    sections = {
        "roof_band": nominal(0., roof["shear_MPa"], material, roof["bend_MPa"]),
        "floor_band": nominal(0., floor["shear_MPa"], material, floor["bend_MPa"]),
        "sidewall": nominal(side_MPa, 0., material),
    }
    return {
        "sections": sections, "sidewall_membrane_315_MPa": side_MPa,
        "pressure_315_MPa": p_MPa, "transverse_centroid_span_mm": span_mm,
        "fixed_ends_opening_300_mm": fixed_mm / PRESSURE_RATIO,
        "wall_extension_300_mm": side_stretch_mm / PRESSURE_RATIO,
        "support_and_seating_300_mm": shoulder_mm / PRESSURE_RATIO + SEAT_ALLOWANCE_MM,
        "with_attachments_300_mm": (flexure_mm + side_stretch_mm + shoulder_mm) / PRESSURE_RATIO
                                   + SEAT_ALLOWANCE_MM,
    }


def centre(interval_mm):
    return sum(interval_mm) / 2


def length(interval_mm):
    return interval_mm[1] - interval_mm[0]


def crowned_strip(force_315_N, key_width_mm, interval_mm, material, mean_allow_MPa):
    gross_y_mm = length(interval_mm)
    net_x_mm = key_width_mm - 2 * EDGE_R_MM
    net_y_mm = gross_y_mm - 2 * EDGE_R_MM
    net_area_mm2 = net_x_mm * net_y_mm
    radius_mm = gross_y_mm ** 2 / (8 * CROWN_MM) + CROWN_MM / 2
    half_width_mm = sqrt(4 * force_315_N * radius_mm / (pi * net_x_mm * E_STAR_MPa))
    hertz_peak_MPa = 2 * force_315_N / (pi * half_width_mm * net_x_mm)
    peak_MPa = max(hertz_peak_MPa, 4 / pi * force_315_N / net_area_mm2)
    return {"reaction_315_N": force_315_N,
            "strip_y_mm": [interval_mm[0] + EDGE_R_MM, interval_mm[1] - EDGE_R_MM],
            "net_area_mm2": net_area_mm2, "mean_300_MPa": force_315_N / PRESSURE_RATIO / net_area_mm2,
            "mean_screen_MPa": mean_allow_MPa, "peak_315_MPa": peak_MPa, "static_screen_MPa": .6 * material[0],
            "hertz_half_width_mm": half_width_mm, "finite_width_limits_hertz": half_width_mm > net_y_mm / 2}


def key_hand(layout, station, side_force_N):
    """Vertical eccentric force between the near upper and far lower supports."""
    shoe_face = (KEY_CLOSED_Y_MM[0], SHOE_ABS_Y_MAX_MM)
    y_load_mm = centre(shoe_face)
    y_upper_mm = centre(LOCK_UPPER_Y_MM)
    y_lower_mm = centre(LOCK_LOWER_Y_MM)
    overhang_mm = y_upper_mm - y_load_mm
    separation_mm = y_lower_mm - y_upper_mm
    opposite_N = side_force_N * overhang_mm / separation_mm
    cap_N = side_force_N + opposite_N
    width_mm = station["key_width_mm"]
    net_width_mm = width_mm - 2 * EDGE_R_MM
    depth_mm = station["key_depth_mm"]
    leg_mm = station["leg_width_mm"]
    cap_mm = station["cap_depth_mm"]
    return_depth_mm = station["return_depth_mm"]
    inertia_mm4 = net_width_mm * depth_mm**3 / 12
    area_mm2 = net_width_mm * depth_mm
    cap_b_mm = length(LOCK_UPPER_Y_MM)
    cap = beam(cap_N, width_mm + leg_mm + 1.6, net_width_mm, cap_b_mm, cap_mm, skew=.5)
    key_bend_MPa = side_force_N * overhang_mm * depth_mm / (2 * inertia_mm4)
    key_shear_MPa = 1.5 * max(side_force_N, opposite_N) / area_mm2
    cheek_normal_MPa = cap_N / (2 * leg_mm * cap_b_mm)
    return_arm_mm = y_lower_mm - LOCK_UPPER_Y_MM[1]
    return_width_mm = width_mm + 2 * leg_mm
    return_bending_MPa = 6 * opposite_N * return_arm_mm / (return_width_mm * return_depth_mm**2)
    return_shear_MPa = 1.5 * opposite_N / (return_width_mm * return_depth_mm)
    return_mm = opposite_N * return_arm_mm**3 / (3 * E_MPa * return_width_mm * return_depth_mm**3 / 12)
    return_mm += opposite_N * return_arm_mm / (SHEAR_FACTOR * G_MPa * return_width_mm * return_depth_mm)
    elastic_key_mm = (side_force_N * overhang_mm ** 2 * (overhang_mm + separation_mm) / (3 * E_MPa * inertia_mm4)
                      + (side_force_N * overhang_mm + opposite_N * separation_mm) /
                      (SHEAR_FACTOR * G_MPa * area_mm2))
    cheek_extension_mm = cheek_normal_MPa * (60 + layout.shoe_depth_mm + depth_mm + WEAR_LAND_DEPTH_MM) / E_MPa
    contacts = {
        "shoe": crowned_strip(side_force_N, width_mm, shoe_face, FORGED_SHOE, 100.),
        "upper_forged_land": crowned_strip(cap_N, width_mm, LOCK_UPPER_Y_MM, FORGED_KEY, 100.),
        "lower_forged_land": crowned_strip(opposite_N, width_mm, LOCK_LOWER_Y_MM, FORGED_KEY, 100.),
        "upper_land_to_cast": crowned_strip(cap_N, width_mm + 2 * leg_mm,
                                            LOCK_UPPER_Y_MM, CAST, 80.),
        "lower_land_to_cast": crowned_strip(opposite_N, width_mm + 2 * leg_mm,
                                            LOCK_LOWER_Y_MM, CAST, 80.),
    }
    seating_mm = 2 * SEAT_ALLOWANCE_MM + max(
        c["mean_300_MPa"] * WEAR_LAND_DEPTH_MM / E_MPa for c in contacts.values())
    return {
        "sections": {"key": nominal(0., key_shear_MPa, FORGED_KEY, key_bend_MPa),
                     "cap": nominal(0., cap["shear_MPa"], CAST, cap["bend_MPa"]),
                     "cheek_legs": nominal(cheek_normal_MPa, 0., CAST),
                     "return_shelf": nominal(0., return_shear_MPa, CAST, return_bending_MPa)},
        "opening_300_mm": (elastic_key_mm + cheek_extension_mm + cap["bend_mm"] + cap["shear_mm"] + return_mm)
                          / PRESSURE_RATIO + seating_mm,
        "pin_ended_key_315_mm": elastic_key_mm, "cap_reaction_315_N": cap_N,
        "lower_guide_reaction_315_N": opposite_N, "contacts": contacts,
    }


def shoe_hand(layout):
    x_rear_mm, x_front_mm = (s["x_mm"] for s in STATIONS.values())
    load = extrema(transition_cases(), x_rear_mm, x_front_mm)
    shoe_peak_N = load["shoe_max"]["shoe"]["force_N"]
    x_proof = distribute(shoe_peak_N, PROOF_SKEW_X_MM, x_rear_mm, x_front_mm)
    sections, stations = {}, {}
    for idx, (name, station) in enumerate(STATIONS.items()):
        info = load[name]
        force_N = max(info["force_315_N"], abs(info["min_reaction_N"]), abs(x_proof[idx]))
        side_N = force_N * SKEW_FRACTION
        key = key_hand(layout, station, side_N)
        effective_x_mm = station["key_width_mm"] - 2 * EDGE_R_MM + ROOT_R_MM
        span_mm = 2 * centre((KEY_CLOSED_Y_MM[0], SHOE_ABS_Y_MAX_MM))
        shoe = beam(force_N, span_mm, 150., effective_x_mm, layout.shoe_depth_mm)
        floor_depth_mm = REAR_FLOOR_DEPTH_MM if name == "rear" else FLOOR_SKIN_DEPTH_MM
        floor = beam(force_N, span_mm, 150., effective_x_mm, floor_depth_mm)
        local = key["sections"] | {"shoe": nominal(0., shoe["shear_MPa"], FORGED_SHOE, shoe["bend_MPa"]),
                                   "floor": nominal(0., floor["shear_MPa"], CAST, floor["bend_MPa"])}
        pin_ended_mm = sum(b["bend_mm"] + b["shear_mm"] for b in (shoe, floor)) / PRESSURE_RATIO
        fixed_ended_mm = sum(b["fixed_bend_mm"] + b["centroid_shear_mm"] for b in (shoe, floor)) / PRESSURE_RATIO
        stations[name] = key | {"force_315_N": force_N, "peak_side_315_N": side_N,
                                "minimum_signed_reaction_315_N": info["min_reaction_N"],
                                "local_sections": local, "fixed_ends_opening_300_mm": fixed_ended_mm,
                                "with_attachments_300_mm": pin_ended_mm + key["opening_300_mm"],
                                "governing_load_case": info["case"]}
        sections.update({f"{name}_{k}": v for k, v in local.items()})
    bridge = axial_bridges(90., {"station_x_mm": {k: s["x_mm"] for k, s in STATIONS.items()},
                               "shoe_depth_mm": layout.shoe_depth_mm, "floor_depth_mm": REAR_FLOOR_DEPTH_MM,
                               "longitudinal_floor_band_y_mm": 150.})
    bridge_mm = sum(b["displacement_bound_mm"] for b in bridge.values())
    sections.update({f"longitudinal_{k}": v["strength"] for k, v in bridge.items()})
    return {"stations": stations, "sections": sections, "axial_bridge": bridge,
            "with_attachments_300_mm": max(s["with_attachments_300_mm"] for s in stations.values()) + bridge_mm,
            "fixed_ends_opening_300_mm": max(s["fixed_ends_opening_300_mm"] for s in stations.values())}



def key_cam_screen():
    key_y_mm = KEY_CLOSED_Y_MM[1]-KEY_CLOSED_Y_MM[0]
    key_mass_kg = 2*DENSITY_KG_MM3*key_y_mm*sum(
        s["key_width_mm"]*s["key_depth_mm"] for s in STATIONS.values())
    leg_stroke_m = KEY_CAM["key_stroke_mm"]/1000.
    move_s = KEY_CAM["motion_s"]
    inertia_N = key_mass_kg * 4*leg_stroke_m/move_s**2
    guide_N = 4*KEY_CAM["drag_N_per_key_assumed"]
    release_drag_N = 2*.15*KEY_CAM["residual_load_limit_N"]
    input_ratio = KEY_CAM["key_stroke_mm"]/KEY_CAM["input_stroke_mm"]
    required_N = input_ratio*(inertia_N+guide_N+release_drag_N)/KEY_CAM["efficiency_assumed"]
    previous = read_json("calc/T-2.2f/results.json")["series"]["A_90"]["hand"]["cam"]
    return KEY_CAM | dict(key_moving_mass_kg=key_mass_kg, inertia_N=inertia_N, drag_N=guide_N+release_drag_N,
                          stem_force_screen_N=required_N, prior_T26_stem_force_N=previous["stem_force_N"],
                          movement_peak_key_speed_mm_s=2*KEY_CAM["key_stroke_mm"]/move_s,
                          source="T-2.2f cam assumptions retained in calc/T-2.6/run.py")

def cassette_hand():
    """Legacy bearing with the short briquette producing maximum Janssen thrust."""
    load = janssen(main_cylinder_force_N(315), .35, .20, SHORTEST_LOADED_MM)
    force_N = load["gate_force_N"]
    width_mm, open_width_mm, open_height_mm = 260., 176., 74.
    x_side_mm = (width_mm - open_width_mm) / 2
    lower_net_mm = 35. - 2 * 3.
    upper_net_mm = 88. - open_height_mm / 2 - 2 * 3.
    areas = {"lower": (width_mm - 6.) * lower_net_mm, "upper": (width_mm - 6.) * upper_net_mm,
             "left": (x_side_mm - 6.) * open_height_mm, "right": (x_side_mm - 6.) * open_height_mm}
    ref = read_json("calc/T-1.7d/results.json")["fea"]["r2_aligned_node54"]["finest"]
    return {"max_axial_Janssen_315_N": force_N, "min_loaded_length_mm": SHORTEST_LOADED_MM,
            "net_load_band_area_mm2": areas, "nominal_uniform_300_MPa": force_N / PRESSURE_RATIO / sum(areas.values()),
            "analogue_mean_screen_MPa": 80., "requires_contact_model": True,
            "source": "calc/T-1.7d/results.json, fea.r2_aligned_node54.finest.loads",
            "legacy_cases": ref["loads"]}


def limits(sections):
    return {"static_factor": min(s["static_factor"] for s in sections.values()),
            "FKM": min(s["FKM"] for s in sections.values())}


def candidate(layout, roof_case):
    ring = ring_hand(layout, roof_case)
    lock = shoe_hand(layout)
    mass = budget(layout)
    checks = limits(ring["sections"] | lock["sections"])
    opening_mm = max(ring["with_attachments_300_mm"], lock["with_attachments_300_mm"])
    return {"layout": layout.data(), "ring": ring, "lock": lock, "mass": mass, "interfaces": interface(layout),
            "manual_margin": checks | {"opening_300_mm": opening_mm},
            "manual_screen": checks["FKM"] >= 1.10 and checks["static_factor"] >= 1.5
                             and opening_mm <= .6 and mass["delta_chamber_kg"] <= 60}


def choose():
    envelopes = final_envelopes()
    case = max(envelopes["315"], key=lambda c: (c["roof"]["inlet_MPa"], c["roof"]["normal_force_N"]))
    lock = shoe_hand(Layout("forged", 64., 135., 135.))
    table = []
    for material, wall_mm, depth_mm in product(("cast", "forged"), (56., 64., 72., 80., 88., 96., 104.),
                                              (120., 135., 150., 165., 180., 195., 210.)):
        if material == "cast" and wall_mm < 64.:
            continue
        layout = Layout(material, wall_mm, depth_mm, depth_mm)
        ring = ring_hand(layout, case)
        mass = budget(layout)
        checks = limits(ring["sections"] | lock["sections"])
        opening_mm = max(ring["with_attachments_300_mm"], lock["with_attachments_300_mm"])
        table.append((layout, checks | {"opening_300_mm": opening_mm, "chamber_kg": mass["chamber_kg"],
                       "delta_chamber_kg": mass["delta_chamber_kg"],
                       "station_reduction_H2_max_kg": mass["station_reduction_kg"][1]}))
    qualified = [
        (layout, row) for layout, row in table
        if row["FKM"] >= 1.10 and row["opening_300_mm"] <= .6 and row["delta_chamber_kg"] <= 60.
    ]
    selected_layout = min(qualified, key=lambda entry: entry[1]["chamber_kg"])[0] if qualified else None
    return selected_layout, case, [layout.data() | values for layout, values in table]

