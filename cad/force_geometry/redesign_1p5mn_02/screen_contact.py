"""Replay the R3 receiver failure and screen the revised B receiver."""

import argparse
from itertools import product
from math import fsum, hypot, isclose, pi, sqrt
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RESULT = ROOT / "cad/source/force_geometry/redesign_1p5mn_02"
TASK = ROOT / "coordination/tasks/T-R4-REDESIGN-1.5MN-02"
REGISTRY = ROOT / "params/r4_b_receiver_02.json"
BASE = ROOT / "cad/force_geometry/redesign_1p5mn"
R3 = ROOT / "cae/cases/T-R3-FORCE-CALC-02"
VARIANTS = ("B-V1", "B-V2")
KEYS = "B_CLOSED_LOCK_BACKED_STOP"
SEAT = "B_CLOSED_STOP_SEAT"

sys.path.insert(0, str(R3))
from contacts import clipped, contact, integrate, rectangle, solve
sys.path.append(str(BASE))
from calculate import ENVELOPE, encode, read, section


def require(condition, message):
    if not condition:
        raise ValueError(message)


def support_faces(inner, outer, height, edge):
    inner, outer, height = inner + edge, outer - edge, height - 2 * edge
    return rectangle(-outer, -inner, height), rectangle(inner, outer, height)


def contact_faces(design, edge, seat=False):
    if seat:
        return support_faces(design["seat_inner_y"], design["gate_width"] / 2, design["gate_height"], edge)
    inner = design["key_inner_y"]
    return support_faces(inner, inner + design["key_width"], design["key_height"], edge)


def geometry():
    baseline = read(BASE / "design.json")
    dataset = read(REGISTRY)
    design = {**baseline, "revision": dataset["revision"],
              "receiver": {**baseline["receiver"], **dataset["geometry"]},
              "structure": {**baseline["structure"], **dataset["structure_overrides"]}}
    return baseline, design, dataset


def nominal(rectangles, offsets, force):
    rows = []
    for ey, ez in offsets:
        parts = contact(rectangles, ey, ez, force)
        rows.append({"eccentricity_yz_mm": [ey, ez], "pads_negative_positive_y": parts,
                     "peak_MPa": max(part["peak_MPa"] for part in parts)})
    return rows


def sensitivity(rectangles, offsets, force, stiffness, fit, clearance_points=()):
    # In this basis a unit total load is solved over unit-scale coordinates.
    # Each pad contributes k_i times the positive part of (rigid approach - its own face error).
    scale = max(abs(x) for rect in rectangles for point in rect for x in point)
    pads = [tuple((y / scale, z / scale) for y, z in rect) for rect in rectangles]
    load_scale = force / scale**2
    displacement_scale = load_scale / stiffness
    center_error = fit["plane_center_gap_deviation"]
    tilt_error = fit["plane_tilt_gap_at_each_edge"]
    stiffness_pairs = list(product(fit["stiffness_scale_samples"], repeat=2))
    gap_cases = []
    for signs in product((-1, 1), repeat=6):
        gaps = []
        for i, rect in enumerate(rectangles):
            sy, sz, sg = signs[3 * i:3 * i + 3]
            y_mid = (rect[0][0] + rect[1][0]) / 2
            y_half = (rect[1][0] - rect[0][0]) / 2
            z_half = rect[2][1]
            dy, dz = sy * tilt_error / y_half, sz * tilt_error / z_half
            gaps.append(((sg * center_error - dy * y_mid) / displacement_scale,
                         dy * scale / displacement_scale, dz * scale / displacement_scale))
        gap_cases.append((signs, gaps))
    worst_by_offset = []
    worst_approach = None
    peak_balance = [0.0, 0.0, 0.0]
    for ey, ez in offsets:
        target = (1.0, ey / scale, ez / scale)
        worst = {"peak_MPa": 0}
        for scales, (signs, gaps) in product(stiffness_pairs, gap_cases):
            u = (1.0, 0.0, 0.0)
            for _ in range(50):
                relative = [tuple(x - g for x, g in zip(u, gap)) for gap in gaps]
                parts = [integrate(clipped(rect, rel)) for rect, rel in zip(pads, relative)]
                actual = [fsum(k * fsum(a * b for a, b in zip(part[i], rel))
                               for k, part, rel in zip(scales, parts, relative)) for i in range(3)]
                correction = [t - a for t, a in zip(target, actual)]
                if max(map(abs, correction)) < 1e-12:
                    break
                tangent = [[fsum(k * part[i][j] for k, part in zip(scales, parts))
                            for j in range(3)] for i in range(3)]
                u = tuple(a + b for a, b in zip(u, solve(tangent, correction)))
            else:
                raise ValueError(f"Receiver fit case failed to converge at {ey}, {ez}")
            for i, error in enumerate(correction):
                peak_balance[i] = max(peak_balance[i], abs(error) * force * (scale if i else 1))
            pressures = [load_scale * k * max(0, max(a + b * y + c * z for y, z in rect))
                         for k, rect, (a, b, c) in zip(scales, pads, relative)]
            state = {"eccentricity_yz_mm": [ey, ez], "stiffness_scales": scales,
                     "gap_signs_y_z_center_negative_then_positive": signs}
            if max(pressures) > worst["peak_MPa"] + 1e-9:
                reactions = [k * force * fsum(a * b for a, b in zip(part[0], rel))
                             for k, part, rel in zip(scales, parts, relative)]
                worst = {**state, "peak_MPa": max(pressures), "peak_by_pad_MPa": pressures,
                         "reaction_by_pad_N": reactions,
                         "active_area_by_pad_mm2": [part[0][0] * scale**2 for part in parts]}
            if clearance_points:
                a, b, c = u
                approach = displacement_scale * max(a + (b * y + c * z) / scale for y, z in clearance_points)
                if worst_approach is None or approach > worst_approach["approach_mm"] + 1e-10:
                    worst_approach = {**state, "approach_mm": approach}
        worst_by_offset.append(worst)
    require(peak_balance[0] < 1e-4 and max(peak_balance[1:]) < 0.01, "Contact equilibrium residual exceeded")
    return {"sample_count": len(offsets) * len(stiffness_pairs) * len(gap_cases),
            "nominal_stiffness_MPa_per_mm": stiffness, "worst_by_eccentricity": worst_by_offset,
            "max_force_and_first_moment_residuals_N_Nmm": [
                round(peak_balance[0], 9), *(round(error, 5) for error in peak_balance[1:])],
            "worst_approach_at_seat_mm": worst_approach}


def strength(normal, shear, limit):
    equivalent = hypot(normal, sqrt(3) * shear)
    return {"normal_MPa": normal, "shear_MPa": shear, "von_mises_MPa": equivalent,
            "conditional_limit_MPa": limit, "factor": limit / equivalent}


def screening():
    baseline, design, dataset = geometry()
    c, s, b, m, limits = (design[name] for name in ("cylinder", "structure", "receiver", "materials", "limits"))
    fit = dataset["fit"]
    criteria = read(TASK / "task.json")["acceptance_criteria"]["min_b_key_contact_safety_factor"]
    require(criteria["operator"] == ">=" and criteria["pressure_bar"] == limits["supply_bar"][1],
            "Task pressure boundary differs from the R3 design")
    factor, pressure = criteria["value"], criteria["pressure_bar"]
    limit = min(m[dataset["material_refs"][part]]["assumed_minimum_yield_MPa"]
                for part in ("ReceiverGate", "ReceiverLock", "LockBacking", "ReceiverSeat", "ReactionFrameHead"))
    diameter = c["bore"]
    force = c["quantity"] * pi * diameter**2 / 4 * pressure / 10
    ey, ez = limits["external_longitudinal_load_eccentricity_yz_mm"]
    offsets = tuple(product((-ey, 0, ey), (-ez, 0, ez)))
    reference = read(R3 / "results/index.json")["receiver_extrema"]
    axial_fit = fit["running_gap_stack_per_interface"]
    key_gaps = (b["gate_to_key_axial_gap"], b["key_to_backing_axial_gap"])
    seat_gap = b["gate_to_seat_axial_gap"] - sum(key_gaps) - 3 * axial_fit
    require(isclose(seat_gap, fit["minimum_keys_only_seat_gap_after_take_up"]), "Inconsistent seat gap stack")
    face_margin = fit["per_edge_contact_exclusion"] - b["key_edge_chamfer"] - fit["installed_key_registration_yz"]
    key_stack = s["headThickness"] + b["reaction_head_boss_projection"] + s["front_head_x"] - (
        s["chamber_entry_x"] + s["chamber_length"])
    paths = {}
    for path, seat in ((KEYS, False), (SEAT, True)):
        previous = nominal(contact_faces(baseline["receiver"], 0, seat), offsets, force)
        old_peak = max(row["peak_MPa"] for row in previous)
        require(isclose(old_peak, reference[path]["pressure_bound"]["peak_MPa"], rel_tol=5e-9),
                f"{path} baseline did not reproduce the R3 pressure bound")
        rects = contact_faces(b, fit["per_edge_contact_exclusion"], seat)
        proposed = nominal(contact_faces(b, 0 if seat else b["key_edge_chamfer"], seat), offsets, force)
        peak = max(row["peak_MPa"] for row in proposed)
        obstacles = () if seat else tuple(point for rect in contact_faces(b, 0, True) for point in rect)
        sweep = sensitivity(rects, offsets, force, m["E_MPa"] / key_stack, fit, obstacles)
        worst = max(sweep["worst_by_eccentricity"], key=lambda row: row["peak_MPa"])
        h, t = b["gate_height"], b["gate_thickness"]
        outer_y = max(abs(y) for rect in rects for y, _ in rect) + fit["per_edge_contact_exclusion"]
        gate_bending = force * outer_y / (2 * section(h, t)) + force * ez / section(t, h)
        gate_limit = m[dataset["material_refs"]["ReceiverGate"]]["assumed_minimum_yield_MPa"]
        gate = strength(gate_bending, 1.5 * force / (h * t), gate_limit)
        paths[path] = {
            "baseline_peak_MPa": old_peak, "baseline_factor": limit / old_peak,
            "R3_pressure_bound_row": reference[path]["pressure_bound"]["row"],
            "nominal_peak_MPa": peak, "nominal_factor": limit / peak, "nominal_by_eccentricity": proposed,
            "effective_pads_yz_mm": rects, "fit_sensitivity": sweep,
            "sensitivity_peak_MPa": worst["peak_MPa"], "sensitivity_factor": limit / worst["peak_MPa"],
            "conservative_peak_through_projected_stack_MPa": worst["peak_MPa"], "gate_section": gate,
        }
    head_moment = force * (s["tie_axis_offset"] / 2 + ey + ez)
    width, thickness = s["head_effective_bending_width"], s["headThickness"]
    head = strength(head_moment / section(width, thickness), 1.5 * force / (width * thickness), limit)
    key = paths[KEYS]
    seat_remaining = seat_gap - key["fit_sensitivity"]["worst_approach_at_seat_mm"]["approach_mm"]
    return {
        "scope": "CALCULATED_ASSUMED",
        "cap_port_pressure_bar": pressure, "return_port_pressure_bar": 0,
        "compression_along_positive_x_N": force, "parent_material_contact_comparison_MPa": limit,
        "required_factor": factor, "paths": paths,
        "reaction_head_gross_strip_without_boss_credit": head,
        "minimum_unloaded_key_running_gap_per_face_mm": min(key_gaps) - axial_fit,
        "effective_key_face_registration_margin_mm": face_margin,
        "minimum_seat_clearance_in_key_load_sweep_mm": seat_remaining,
        "checks": {
            "R3_key_failure_reproduced": key["baseline_factor"] < factor,
            "keys_and_backing_pass": key["sensitivity_factor"] >= factor,
            "independent_seat_passes": paths[SEAT]["sensitivity_factor"] >= factor,
            "seats_stay_open_in_key_load_sweep": seat_remaining > 0,
            "key_running_gap_and_effective_face_survive_fit": min(key_gaps) > axial_fit and face_margin > 0,
            "gate_and_head_gross_sections_pass": min(head["factor"], *(p["gate_section"]["factor"]
                                                                    for p in paths.values())) >= factor,
        },
        "physical_state_evaluation": "BLOCKED_INPUTS",
        "physical_sections_4_5_6": "NOT_RUN",
        "physical_unknowns": dataset["physical_unknowns"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RESULT / "screening.json")
    args = parser.parse_args()
    report = screening()
    require(all(report["checks"].values()), f"Screen failed: {report['checks']}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(encode(report), encoding="utf-8", newline="\n")
    key = report["paths"][KEYS]
    print(f"PASS: key contact factor {key['baseline_factor']:.3f} -> {key['nominal_factor']:.3f}; "
          f"minimum on fit/stiffness sweep {key['sensitivity_factor']:.3f}")


if __name__ == "__main__":
    main()
