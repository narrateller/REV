"""W02 static load screening in N, mm, MPa and bar."""

import json
from math import hypot, pi, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RESULT = ROOT / "cad/source/force_geometry/redesign_1p5mn"
ENVELOPE = ROOT / "cae/cases/design_boundary_phase_load_envelope/envelope.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def encode(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def area(diameter):
    return pi * diameter**2 / 4


def inertia(diameter):
    return pi * diameter**4 / 64


def section(width, depth):
    return width * depth**2 / 6


def sizing(design, envelope):
    c, s, b, limits, m = (design[k] for k in ("cylinder", "structure", "receiver", "limits", "materials"))
    low, high = limits["supply_bar"]
    friction = limits["guide_sliding_friction_limit"]
    ey, ez = limits["external_longitudinal_load_eccentricity_yz_mm"]
    eccentricity = ey + ez
    span = s["guide_bogie_span"]
    gravity = limits["assumed_guide_gravity_per_station_N"]
    opposing_MPa = limits["opposing_port_bar"] / 10
    drop = limits["supply_drop_bar"]
    efficiency = 1 - limits["cylinder_loss_fraction"]
    cap, rod = area(c["bore"]), area(c["rod"])
    annulus = cap - rod

    def guide_drag(force):
        return 2 * friction * (force * eccentricity / span + gravity)

    def hydraulic_pair(bore, diameter, count, demand):
        forward = count * area(bore)
        reverse = forward - count * area(diameter)
        directions = {}
        for name, active, opposing in (("WORK", forward, reverse), ("REVERSE_WORK", reverse, forward)):
            def available(pressure):
                return ((pressure - drop) / 10 * active * efficiency - opposing_MPa * opposing
                        - guide_drag(demand))
            directions[name] = {
                "active_area_mm2": active,
                "opposing_area_mm2": opposing,
                "available_at_250_N": available(low),
                "available_at_315_N": available(high),
                "supply_needed_bar": drop + 10 * (demand + guide_drag(demand) + opposing_MPa * opposing)
                / (efficiency * active),
            }
        return directions

    samples = envelope["cases"]
    peak = max(abs(sample["F_x_N"]) for row in samples.values() for sample in row["axial_samples"])
    work_end = max(row["relative_pose_m"]["work_end"] for row in envelope["variants"].values()) * 1000
    q_values = [q * 1000 for row in samples.values() for q in row["pose_samples_q_m"]]
    outside = sum(not 0 <= c["rear_reserve"] + q <= c["stroke"] for q in q_values)
    phases = {}
    for key, row in samples.items():
        pressures = []
        for entry in row["axial_samples"]:
            f = entry["F_x_N"]
            if f:
                active, opposing = (cap, annulus) if f > 0 else (annulus, cap)
                needed = drop + 10 * (abs(f) + guide_drag(abs(f)) + opposing_MPa * c["quantity"] * opposing) / (
                    efficiency * c["quantity"] * active)
            else:
                needed = 0
            pressures.append({**entry, "supply_needed_bar": needed, "margin_to_250_bar": low - needed})
        phases[key] = {
            "variant": row["variant"], "phase": row["phase"],
            "stroke_samples_mm": [c["rear_reserve"] + 1000 * q for q in row["pose_samples_q_m"]],
            "axial_samples": pressures,
        }

    # Parallel valve ports at the limiting pressure. Also bound a trapped opposing-pressure fault.
    one_push, one_pull = cap * high / 10, annulus * high / 10
    force = c["quantity"] * one_push
    cases = {
        "SYMMETRIC_MAX": (force, force * eccentricity),
        "ONE_CYLINDER_MAX": (one_push, one_push * (c["axis_offset"] + eccentricity)),
        "OPPOSING_PORT_FAULT": (one_push - one_pull,
                               (one_push + one_pull) * c["axis_offset"] + (one_push - one_pull) * eccentricity),
    }
    governing_guide_case = max(cases, key=lambda key: cases[key][1])
    guide_reaction = max(moment / span + gravity for _, moment in cases.values())
    guide_proof = guide_reaction * limits["guide_branch_proof_load_multiplier"]
    frame_span = s["front_head_x"] - s["headThickness"]
    strength = {}
    buckling = {}

    def stress(name, normal, shear, material):
        yield_stress = m[material]["assumed_minimum_yield_MPa"]
        vm = hypot(normal, sqrt(3) * shear)
        strength[name] = {"normal_MPa": normal, "shear_MPa": shear, "von_mises_MPa": vm,
                          "assumed_yield_MPa": yield_stress, "factor": yield_stress / vm}

    def beam(name, force_N, moment, width, depth, material):
        stress(name, moment / section(width, depth), 1.5 * force_N / (width * depth), material)

    def euler(name, load, second_moment, length, k):
        critical = pi**2 * m["E_MPa"] * second_moment / (k * length)**2
        buckling[name] = {"compression_N": load, "I_mm4": second_moment, "free_length_mm": length,
                          "K": k, "critical_load_N": critical, "utilization": load / critical}

    head_moment = max(p * (2 * s["tie_axis_offset"]) / 4 + moment for p, moment in cases.values())
    beam("front_and_rear_head_net_strip", force, head_moment, s["head_effective_bending_width"],
         s["headThickness"], "head")
    crosshead_moment = max(p * (2 * c["axis_offset"]) / 4 + moment for p, moment in cases.values())
    beam("moving_crosshead_net_strip", force, crosshead_moment, s["crosshead_effective_bending_width"],
         s["crosshead_thickness"], "head")
    tie_load = max(p / 4 + moment / (4 * s["tie_axis_offset"]) for p, moment in cases.values())
    stress("each_frame_tie", tie_load / s["tie_square"]**2, 0, "structure")
    stress("frame_tie_stud_root", tie_load / area(s["tie_stud_root"]), 0, "quenched_alloy")
    stress("frame_tie_thread_strip", 0, tie_load / (0.5 * pi * s["tie_stud_root"] * s["tie_engagement"]),
           "quenched_alloy")
    nut_area = s["tie_nut_across_envelope"]**2 - area(s["tie_stud_nominal_diameter"])
    stress("head_under_tie_nut", tie_load / nut_area, 0, "head")
    stress("head_under_tie_shoulder", tie_load / (s["tie_square"]**2 - area(s["tie_stud_nominal_diameter"])),
           0, "head")
    euler("frame_tie_pin_pin", tie_load, s["tie_square"]**4 / 12, frame_span, 1)

    pin = c["pin_diameter"]
    ear, eye, gap = c["clevis_ear_thickness"], c["rod_eye_width"], c["clevis_side_gap"]
    pin_span = eye + 2 * gap + ear
    ligament = c["eye_radius"] - pin / 2
    stress("pin_bending_double_shear", one_push * pin_span / (4 * (2 * inertia(pin) / pin)),
           one_push / (2 * area(pin)), "pins_and_rod")
    stress("rod_and_rear_eye_bearing", one_push / (pin * eye), 0, "pins_and_rod")
    stress("rod_and_rear_eye_tearout", 0, one_push / (2 * ligament * eye), "pins_and_rod")
    stress("clevis_ear_bearing", one_push / (2 * pin * ear), 0, "structure")
    stress("clevis_ear_double_tearout", 0, one_push / (4 * 50 * ear), "structure")
    stress("clevis_ear_net_section", one_push / (2 * (c["clevis_ear_width"] - pin) * ear), 0, "structure")
    stress("qualified_full_penetration_clevis_roots", one_push / (2 * c["clevis_ear_width"] * ear), 0, "joint")
    stress("rod_body", one_push / rod, 0, "pins_and_rod")
    # Gland-to-pin at mechanical end. K=2 also covers ideal loss of lateral restraint at the rod eye.
    free_rod = c["rod_pin_x_at_zero"] + c["stroke"] - c["barrel_end_x"]
    euler("rod_fixed_free", one_push, inertia(c["rod"]), free_rod, 2)

    rail_w, rail_h = s["guide_beam_width"], s["guide_beam_radial_depth"]
    beam("guide_beam", guide_proof, guide_proof * frame_span / 4, rail_w, rail_h, "structure")
    arm_lever = s["guide_rear_station_x_at_zero"] + span - (s["crosshead_rear_x"] + s["crosshead_thickness"])
    beam("moving_guide_arm", guide_proof, guide_proof * arm_lever,
         s["guide_arm_width"], s["guide_arm_radial_depth"], "structure")
    end_pin = s["guide_beam_end_pin_diameter"]
    count = s["guide_beam_end_pin_count"]
    stress("guide_beam_end_dowels", 0, guide_proof / (count * area(end_pin)), "pins_and_rod")
    stress("guide_beam_end_dowel_bearing", guide_proof / (count * end_pin * s["guide_beam_end_pin_engagement"]),
           0, "head")
    stress("pad_positive_location_fasteners", 0, guide_proof * limits["guide_fastener_friction_coefficient"]
           / (s["guide_pad_fasteners"] * area(s["guide_pad_fastener_root"])), "bolt")
    contact = guide_proof / (s["guide_pad_width"] * s["guide_pad_length"])
    contact_limit = m["guide_pad"]["assumed_maximum_contact_pressure_MPa"]
    strength["replaceable_guide_pads"] = {"contact_MPa": contact, "assumed_limit_MPa": contact_limit,
                                          "factor": contact_limit / contact}

    punch_w, punch_h = s["punch_yz"]
    collar_w, collar_h = s["punch_shoulder_yz"]
    stress("punch_combined", force * (1 / (punch_w * punch_h) + ey / section(punch_h, punch_w)
                                    + ez / section(punch_w, punch_h)), 0, "quenched_alloy")
    bolt_count = s["punch_collar_tie_count"]
    hole = s["punch_collar_tie_diameter"]
    bolt_y, bolt_z = s["punch_collar_tie_offsets_yz"]
    net_area = punch_w * punch_h - bolt_count * area(hole)
    net_z = (punch_h * punch_w**3 / 12 - bolt_count * (inertia(hole) + area(hole) * bolt_y**2)) / (punch_w / 2)
    net_y = (punch_w * punch_h**3 / 12 - bolt_count * (inertia(hole) + area(hole) * bolt_z**2)) / (punch_h / 2)
    stress("punch_at_collar_bolt_holes", force * (1 / net_area + ey / net_z + ez / net_y), 0,
           "quenched_alloy")
    stress("crosshead_collar_seat", force / (collar_w * collar_h - punch_w * punch_h), 0, "head")
    stress("reversible_punch_collar_ties", 1.3 * force / (
        s["punch_collar_tie_count"] * area(s["punch_collar_tie_root"])), 0, "bolt")
    stress("punch_collar_thread_strip", 0, 1.3 * force / (
        s["punch_collar_tie_count"] * 0.5 * pi * s["punch_collar_tie_root"] * s["punch_bolt_engagement"]),
           "quenched_alloy")
    euler("punch_fixed_free", force, punch_w * punch_h**3 / 12,
          s["punch_face_x"] - (s["crosshead_rear_x"] + s["crosshead_thickness"]), 2)

    chamber_w, chamber_h = s["chamber_outer_yz"]
    chamber_clearance = 2 * s["chamber_radial_clearance"]
    chamber_gap_area = (punch_w + chamber_clearance) * (punch_h + chamber_clearance)
    stress("A_die_axial_backing_net_area", force / (chamber_w * chamber_h - chamber_gap_area), 0, "head")
    stress("B_die_axial_backing_net_area", force / (2 * b["key_inner_y"] * chamber_h - chamber_gap_area),
           0, "head")
    gate_half = b["gate_width"] / 2
    seat_width = gate_half - b["seat_inner_y"]
    seat_span = 2 * (b["seat_inner_y"] + seat_width / 2)
    key_span = 2 * (b["key_inner_y"] + b["key_width"] / 2)
    for name, support_span, contact_area in (
        ("B_CLOSED_STOP_SEAT", seat_span, seat_width * b["gate_height"]),
        ("B_CLOSED_LOCK_BACKED_STOP", key_span, b["key_width"] * b["key_height"]),
    ):
        # For a point load inside the span the center case bounds the transverse bending moment.
        gate_stress = (force * support_span / (4 * section(b["gate_height"], b["gate_thickness"]))
                       + force * ez / section(b["gate_thickness"], b["gate_height"]))
        stress(f"{name}_gate", gate_stress, 1.5 * force / (b["gate_height"] * b["gate_thickness"]),
               "quenched_alloy")
        heavy_side = force * (0.5 + ey / support_span)
        stress(f"{name}_contact_and_backing", heavy_side / contact_area, 0, "head")

    stroke = {
        "mechanical_range_mm": [0, c["stroke"]], "q_range_mm": [min(q_values), max(q_values)],
        "operating_range_mm": [c["rear_reserve"] + min(q_values), c["rear_reserve"] + max(q_values)],
        "rear_reserve_mm": c["rear_reserve"] + min(q_values),
        "front_reserve_mm": c["stroke"] - c["rear_reserve"] - max(q_values),
        "source_pose_points": len(q_values), "points_outside_stroke": outside,
        "B_closed_work_limit_stroke_mm": c["rear_reserve"] + work_end,
    }
    selected = hydraulic_pair(c["bore"], c["rod"], c["quantity"], peak)
    min_strength_case = min(strength, key=lambda key: strength[key]["factor"])
    max_euler_case = max(buckling, key=lambda key: buckling[key]["utilization"])
    return {
        "scope": design["scope"], "physical_status": "BLOCKED_INPUTS",
        "envelope_demand_absolute_peak_N": peak,
        "hydraulics": {
            "per_cylinder_cap_area_mm2": cap, "per_cylinder_rod_area_mm2": rod,
            "per_cylinder_annulus_mm2": annulus, "selected": selected,
            "single_320_160": hydraulic_pair(320, 160, 1, peak),
            "single_280_140": hydraulic_pair(280, 140, 1, peak),
            "full_stroke_volume_L": {"cap": c["quantity"] * cap * c["stroke"] / 1e6,
                                     "annulus": c["quantity"] * annulus * c["stroke"] / 1e6},
        },
        "pressure_load_cases": {key: {"axial_N": p, "guide_moment_bound_Nmm": moment}
                                for key, (p, moment) in cases.items()},
        "guide_governing_case": governing_guide_case, "guide_station_reaction_bound_N": guide_reaction,
        "guide_station_screening_load_N": guide_proof,
        "guide_beam_elastic_midspan_deflection_mm_at_screening_load": guide_proof * frame_span**3 /
        (48 * m["E_MPa"] * rail_w * rail_h**3 / 12),
        "stroke": stroke, "source_phases_hydraulics_only": phases,
        "strength": strength, "stability": buckling,
        "checks": {
            "full_envelope_both_directions_at_minimum_supply": all(
                value["available_at_250_N"] >= peak for value in selected.values()),
            "all_nonzero_phase_samples_at_or_below_315_bar": all(
                entry["supply_needed_bar"] <= high for row in phases.values() for entry in row["axial_samples"]),
            "stroke_and_reserves": c["stroke"] >= 700 and outside == 0 and
            min(stroke["rear_reserve_mm"], stroke["front_reserve_mm"]) > 0,
            "strength_screening": strength[min_strength_case]["factor"] >= limits["min_strength_factor"],
            "stability_screening": buckling[max_euler_case]["utilization"] < limits["max_euler_utilization"],
        },
        "governing_strength": min_strength_case, "governing_stability": max_euler_case,
        "remaining_inputs": design["unknowns"],
    }


if __name__ == "__main__":
    report = sizing(read(HERE / "design.json"), read(ENVELOPE))
    RESULT.mkdir(parents=True, exist_ok=True)
    (RESULT / "screening.json").write_text(encode(report), encoding="utf-8", newline="\n")
    print(encode({key: report[key] for key in ("checks", "governing_strength", "governing_stability")}))
    raise SystemExit(0 if all(report["checks"].values()) else 1)
