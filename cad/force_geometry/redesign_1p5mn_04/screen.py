"""Conditional W02 iteration 04 replay using the pinned R3 load model."""

from itertools import product
from math import pi
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "cad/source/force_geometry/redesign_1p5mn_04"
TASK = ROOT / "coordination/tasks/T-R4-REDESIGN-1.5MN-03"
DATA = ROOT / "params/r4_w02_iteration_04.json"
R3 = ROOT / "cae/cases/T-R3-FORCE-CALC-04"
R3_PREVIOUS = R3.with_name("T-R3-FORCE-CALC-03")
sys.path.insert(0, str(R3_PREVIOUS))
previous = runpy.run_path(str(R3_PREVIOUS / "model.py"))
Iteration02 = previous["Iteration02"]
from force_calc import case_samples, circle, pressure_samples, single_branch
from screen_contact import ENVELOPE, contact_faces, encode, geometry, read, require
from calculate import sizing


def revised_geometry():
    baseline, design, receiver = geometry()
    inputs = read(DATA)
    for name in ("cylinder", "structure", "receiver", "limits"):
        design[name].update(inputs[name])
    design["unknowns"].update(inputs["unknowns"])
    design["revision"] = inputs["revision"]
    receiver["fit"].update(inputs["fit"])
    return baseline, design, receiver


class Iteration04(Iteration02):
    def __init__(self):
        super().__init__()
        _, design, self.dataset = revised_geometry()
        self.c, self.s, self.b = (design[key] for key in ("cylinder", "structure", "receiver"))
        self.l = design["limits"]
        self.grav = self.l["assumed_guide_gravity_per_station_N"]
        self.b_die_entry_x = self.s["die_entry_B_x"]
        self.fit = self.dataset["fit"]
        self.faces = {path: contact_faces(self.b, self.fit["per_edge_contact_exclusion"],
                                          path == previous["SEAT"]) for path in self.faces}
        axis = self.c["axis_offset"]
        self.layout = {name: {"cylinder_axis_yz_mm": points} for name, points in
                       {"V1": [[0, -axis], [0, axis]], "V2": [[-axis, 0], [axis, 0]]}.items()}
        self.cap, self.rod = circle(self.c["bore"]), circle(self.c["rod"])
        self.annulus = self.cap - self.rod
        self.rail_length = self.s["front_head_x"] - self.s["headThickness"]
        self.pad_face = self.s["guide_half_opening"]
        self.r4 = sizing(design, read(ENVELOPE))


def extrema(rows, fit):
    gaps = [
        (row[f"rails_{support}"]["chamber_clearance_remaining_mm"] - fit, index, support,
         row.get("variant"), row.get("sample"), row["stroke_mm"], row["eccentricity_yz_mm"])
        for index, row in enumerate(rows, 1) for support in ("PIN_PIN", "FIXED_FIXED")
    ]
    strength = min((entry["factor"], key, index)
                   for index, row in enumerate(rows, 1)
                   for key, entry in row["section_4_strength"].items()
                   if entry["factor"] is not None)
    euler = max((entry["compression_over_euler"], key, index)
                for index, row in enumerate(rows, 1)
                for key, entries in row["section_5_stability"].items() for entry in entries)
    return {"rows": len(rows), "minimum_residual_gap": min(gaps), "minimum_strength": strength,
            "maximum_euler": euler}


def reverse_fixture_samples(model, cases):
    """Check the same independent reverse fixture under static and sliding bounds."""
    for case_id, case in cases.items():
        variant = case["variant"]
        for axial in case["axial_samples"]:
            if axial["sample"] != "REVERSE_WORK":
                continue
            force = axial["F_x_N"]
            for q, (ey, ez), branch, moving in product(
                    case["pose_samples_q_m"], model.offsets, (0, 1), (False, True)):
                stroke = model.c["rear_reserve"] + 1000 * q
                rods = (force, 0) if branch == 0 else (0, force)
                row = model.sample(variant, "INDEPENDENT_BENCH_FIXTURE", stroke, force, ey, ez, rods, moving)
                yield {**row, "sample": "REVERSE_SLIDING" if moving else "REVERSE_STATIC",
                       "variant": variant, "case_id": case_id, "branch": branch + 1}


def reinforced_strength(model):
    s, c = model.s, model.c
    checks = {key: value["factor"] for key, value in model.r4["strength"].items()}
    width, height = s["punch_reinforced_yz"]
    diameter = s["punch_collar_tie_diameter"]
    bolt_area = circle(diameter) * s["punch_collar_tie_count"]
    bolt_inertia = pi * diameter**4 / 64 * s["punch_collar_tie_count"]
    y, z = s["punch_collar_tie_offsets_yz"]
    area = width * height - bolt_area
    wz = (height * width**3 / 12 - bolt_inertia - bolt_area * y**2) / (width / 2)
    wy = (width * height**3 / 12 - bolt_inertia - bolt_area * z**2) / (height / 2)
    limit_force = c["quantity"] * model.cap * model.l["supply_bar"][1] / 10
    ey, ez = model.l["external_longitudinal_load_eccentricity_yz_mm"]
    checks["punch_at_collar_bolt_holes"] = model.yield_limit("quenched_alloy") / (
        limit_force * (1 / area + ey / wz + ez / wy))
    sw, sh = s["punch_shoulder_yz"]
    checks["crosshead_collar_seat"] = model.yield_limit("head") * (sw * sh - width * height) / limit_force
    return checks

def report():
    model = Iteration04()
    baseline = Iteration02()
    cases = read(ENVELOPE)["cases"]
    criteria = read(TASK / "task.json")["acceptance_criteria"]
    bounds = list(pressure_samples(model))
    baseline_bounds = list(pressure_samples(baseline))
    baseline_gap = min(row["rails_PIN_PIN"]["chamber_clearance_remaining_mm"] for row in baseline_bounds)
    baseline_reverse = single_branch(baseline, cases)
    peak_previous_reverse = max(value["peak_supply_bar_stroke_yz_branch"][0]
                                for value in baseline_reverse.values()) - model.l["supply_drop_bar"]
    require(abs(baseline_gap + 2.141874) < 1e-6 and abs(peak_previous_reverse - 503.524) < 0.001,
            "The pinned R3 failure extrema did not reproduce")
    samples = [{**row, "variant": case["variant"], "case_id": case_id}
               for case_id, case in cases.items() for row in case_samples(model, case)]
    working = [row for row in samples if row["mode"] != "AXIAL_RELEASE"]
    fit = model.fit["punch_chamber_radial_fit_budget_mm"]
    pressure_bound = extrema(bounds, fit)
    working_bound = extrema(working, fit)
    gross_strength = reinforced_strength(model)
    reverse_rows = list(reverse_fixture_samples(model, cases))
    reverse_bound = extrema(reverse_rows, fit)
    peak_hold_port = max(port[0] for row in reverse_rows if row["sample"] == "REVERSE_STATIC"
                         for port in row["pressure_port_and_supply_bar"] if port[0])
    reverse = single_branch(model, cases)
    peak_reverse_supply = max(value["peak_supply_bar_stroke_yz_branch"][0] for value in reverse.values())
    peak_reverse_port = peak_reverse_supply - model.l["supply_drop_bar"]
    ref = model.fit_at_pressure_limit()
    available = model.r4["hydraulics"]["selected"]["WORK"]["available_at_250_N"]
    stroke = model.r4["stroke"]
    max_work_supply = max(port[1] for row in working for port in row["pressure_port_and_supply_bar"] if port[1])
    checks = {
        "residual_gap": min(bound["minimum_residual_gap"][0] for bound in (pressure_bound, working_bound, reverse_bound))
        >= criteria["minimum_residual_clearance_mm"],
        "single_branch_reverse": max(peak_reverse_supply, peak_hold_port)
        <= criteria["maximum_single_branch_reverse_pressure_bar"],
        "forward_force": available >= criteria["minimum_forward_force_mn"] * 1e6,
        "working_pressure": max_work_supply <= criteria["maximum_forward_working_pressure_bar"],
        "stroke": model.c["stroke"] >= criteria["minimum_mechanical_stroke_mm"]
        and all(0 <= model.c["rear_reserve"] + q * 1000 <= model.c["stroke"]
                for case in cases.values() for q in case["pose_samples_q_m"]),
        "strength": min(*(bound["minimum_strength"][0] for bound in (pressure_bound, working_bound, reverse_bound)),
                        *gross_strength.values())
        >= model.l["min_strength_factor"],
        "stability": max(*(bound["maximum_euler"][0] for bound in (pressure_bound, working_bound, reverse_bound)),
                   *(entry["utilization"] for entry in model.r4["stability"].values()))
        < model.l["max_euler_utilization"],
        "receiver": min(path["factor"] for path in ref["paths"].values()) >= model.l["min_strength_factor"]
        and min(ref[key] for key in ("remaining_seat_clearance_mm", "minimum_key_running_gap_mm",
                                     "effective_key_registration_margin_mm")) > 0,
    }
    return {"scope": "CALCULATED_ASSUMED", "physical_input_status": "BLOCKED_INPUTS",
            "baseline_iteration_03": {"gap_mm": baseline_gap, "reverse_port_bar": peak_previous_reverse},
            "gross_strength_factors": gross_strength, "working": working_bound, "pressure_bound": pressure_bound, "radial_fit_budget_mm": fit,
            "single_branch_reverse": reverse, "peak_reverse_supply_bar": peak_reverse_supply,
            "peak_reverse_port_bar": peak_reverse_port, "peak_static_hold_port_bar": peak_hold_port,
            "single_branch_fixture": reverse_bound, "covered_case_ids": sorted(cases),
            "axially_released_unbalanced_samples": len(samples) - len(working), "available_forward_at_250_bar_N": available,
            "peak_working_supply_bar": max_work_supply, "stroke": stroke, "receiver": ref,
            "checks": checks}


if __name__ == "__main__":
    result = report()
    (SOURCE / "screening.json").write_text(encode(result), encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in result.items() if key not in
                      ("single_branch_reverse", "receiver")}, indent=2))
    require(all(result["checks"].values()), "Conditional checks failed")
