"""Reproduce the T-2.2d screen and recalculate the T-2.2e sensitivity cases."""

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import json
from math import fsum, hypot, pi
from pathlib import Path
import sys

import yaml

import mass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / "calc/T-2.2d"

FIT_GAP_MM = {"front": .004, "rear": .002}
FOOT_RELIEF_MM = 1.
FOOT_THICKNESS_MM = 28.
EDGE_R_MM = 5.
ROOT_R_MM = 15.
PULSATING_ANALOGY_MPa = {"hardened_steel": 100., "cast_steel": 80.}
PAD_PROJECTION_MM = 8.
PAD_INNER_RELIEF_MM = 4.
ROTOR_INNER_RELIEF_MM = 5.
FOOT_CROWN_MM = .10
FLOOR_BAND_X_MM = (115., 235.)
FLOOR_BAND_EXTRA_MM = 12.
POWER_BRANCH_KG = {"bayonet_diaphragm_accumulator": 3.3, "bayonet_cylinder_and_valves_allowance": 3.0}


def load_prior(name):
    spec = spec_from_file_location(f"prior_{name}", PRIOR / f"{name}.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# T-2.2d hand imports its sibling "mass". Restore the normal module afterwards.
sys.modules["mass"] = load_prior("mass")
try:
    prior = load_prior("hand")
finally:
    sys.modules["mass"] = mass


def input_data():
    saved = json.loads((PRIOR / "results.json").read_text(encoding="utf-8"))
    roof = next(row for row in saved["candidates"] if row["roof_mm"] == 15)
    gate = yaml.safe_load((ROOT / "design/slide_gate.t17d.yaml").read_text(encoding="utf-8"))
    gate["face_x_mm"] += 15
    gate["side_rib_max_front_projection_x_mm"] += 15
    return saved, roof, gate


def foot_check(force_N, moment_Nmm, shank_r_mm, foot_r_mm):
    inner_r_mm = shank_r_mm + ROOT_R_MM + FOOT_RELIEF_MM + EDGE_R_MM
    outer_r_mm = foot_r_mm - EDGE_R_MM
    area_mm2 = mass.annulus_mm2(inner_r_mm, outer_r_mm)
    inertia_mm4 = pi * (outer_r_mm**4 - inner_r_mm**4) / 4
    mean_MPa = force_N / area_mm2
    bending_MPa = moment_Nmm * outer_r_mm / inertia_mm4
    return dict(active_inner_r_mm=inner_r_mm, active_outer_r_mm=outer_r_mm, area_mm2=area_mm2,
                pressure_mean_MPa=mean_MPa, pressure_max_MPa=mean_MPa + bending_MPa,
                pressure_min_MPa=mean_MPa - bending_MPa)


def support_checks(support, station, label):
    force_N = support["force_315_N"]
    force_300_N = force_N / prior.RELIEF_RATIO
    compliance_mm_N = fsum(check["compliance_mm_N"] for check in support["teeth"].values())
    gap_mm = FIT_GAP_MM[label]
    extra_load_N = gap_mm / compliance_mm_N
    max_force_N = min(force_300_N, (force_300_N + 2 * extra_load_N) / 3)
    r_min_mm = station["shank_r_mm"] + ROTOR_INNER_RELIEF_MM + EDGE_R_MM
    r_max_mm = station["head_r_mm"] - EDGE_R_MM
    radial_width_mm = r_max_mm - r_min_mm
    gross_length_mm = (r_min_mm + r_max_mm) / 2 * prior.radians(prior.ENGAGEMENT_DEG)
    contact_300 = prior.hertz(force_300_N * prior.TOOTH_SHARE, radial_width_mm, gross_length_mm)
    contact_315 = prior.hertz(force_N * prior.TOOTH_SHARE, radial_width_mm, gross_length_mm)
    foot = foot_check(force_N, support["tooth_moment_Nm"] * 1000, station["shank_r_mm"], station["foot_r_mm"])
    foot_mean_300_MPa = foot["pressure_mean_MPa"] / prior.RELIEF_RATIO

    def analogy(mean_MPa, bound_MPa):
        return dict(cycles_project=10_000_000, nominal_pressure_300_MPa=mean_MPa,
                    nominal_pressure_analogy_MPa=bound_MPa, analogy_margin=bound_MPa / mean_MPa,
                    status="BENCH_TEST_REQUIRED")

    return support | dict(
        foot_bearing=foot, worst_fit_gap_mm=gap_mm, tooth_share_at_300_from_linear_branches=max_force_N / force_300_N,
        load_to_close_last_tooth_N=extra_load_N, tooth_design_share=prior.TOOTH_SHARE,
        raised_pad_contact_300=contact_300, raised_pad_contact_315=contact_315,
        active_tooth_inner_mm=r_min_mm, active_tooth_outer_mm=r_max_mm,
        integral_contact_screen_MPa=.60 * support["teeth"]["fixed_tooth"]["Rp02_MPa"],
        fatigue_analogy=dict(
            tooth=analogy(contact_300["net_mean_MPa"], PULSATING_ANALOGY_MPa["hardened_steel"]),
            foot=analogy(foot_mean_300_MPa, PULSATING_ANALOGY_MPa["cast_steel"])),
        foot_compression_allowance_300_mm=foot["pressure_max_MPa"] / prior.RELIEF_RATIO
        * (foot["active_outer_r_mm"] - foot["active_inner_r_mm"]) / prior.E_STAR_MPa,
    )


def variant(baseline, roof, label, shoe_web_mm, floor_web_mm, front_foot_mm, rear_foot_mm,
            shoe_skin_mm=14., floor_skin_mm=14., floor_band_mm=0.):
    row = deepcopy(baseline)
    row["label"] = label
    rows_kg = row["mass"]["chamber_rows_kg"]
    stations = row["stations"]
    supports = row["support_checks"]
    for name, foot_mm in (("front", front_foot_mm), ("rear", rear_foot_mm)):
        station = stations[name]
        rows_kg[f"{name}_integral_feet_two"] += (
            2 * FOOT_THICKNESS_MM * mass.STEEL_KG_MM3 * mass.annulus_mm2(station["foot_r_mm"], foot_mm))
        station["foot_r_mm"] = foot_mm
        supports[name] = support_checks(supports[name], station, name)

    span_mm = row["effective_span_mm"]
    average_span_mm = sum(v["y_mm"] for v in stations.values())
    loading = roof["load"]["315_bar"]
    shoe_N = loading["peak"]["shoe_force_N"]
    floor_N = max(r["shoe_force_N"] + r["roof_force_N"] for r in loading["grid"])
    shoe = prior.section(shoe_N, span_mm, 150., 200., row["shoe_h_mm"], shoe_skin_mm, 4 * shoe_web_mm)
    floor = prior.section(floor_N, span_mm, 150., 280., row["floor_h_mm"], floor_skin_mm, 4 * floor_web_mm)
    rows_kg.update(
        moving_crosshead=(shoe["area_mm2"] * average_span_mm + 200 * 150 * 35) * mass.STEEL_KG_MM3,
        bottom_cast_box=floor["area_mm2"] * (average_span_mm + 44.) * mass.STEEL_KG_MM3,
        bottom_end_diaphragms=2 * (280. - 4 * floor_web_mm) * 16. *
        (row["floor_h_mm"] - 2 * floor_skin_mm) * mass.STEEL_KG_MM3,
    )
    row.update(shoe_four_webs_each_mm=shoe_web_mm, floor_four_webs_each_mm=floor_web_mm,
               shoe_skin_mm=shoe_skin_mm, floor_skin_mm=floor_skin_mm)
    row["strength_sections"].update(shoe=prior.strength(shoe["stress_315_MPa"], (500., 750., False)),
                                    floor=prior.strength(floor["stress_315_MPa"], (650., 800., True)))
    row["floor_local_band"] = dict(x_interval_mm=list(FLOOR_BAND_X_MM), width_mm=150., extra_mm=floor_band_mm)
    if floor_band_mm:
        rows_kg["cast_floor_thickening"] = ((FLOOR_BAND_X_MM[1] - FLOOR_BAND_X_MM[0])
                                             * 150. * floor_band_mm * mass.STEEL_KG_MM3)
    rows_kg.update(POWER_BRANCH_KG)
    row["mass"] = mass.ledger(rows_kg, roof["gate_shift"])
    row["delta_height_300_mm"].update(shoe=shoe["flexure_300_mm"] + shoe["shear_300_mm"],
                                      floor=floor["flexure_300_mm"] + floor["shear_300_mm"])
    delta = row["delta_height_300_mm"]
    delta["foot_seat_allowance"] = max(s["foot_compression_allowance_300_mm"] for s in supports.values())
    row["height_300_mm"] = delta["floor"] + max(
        delta["roof"], delta["shoe"] + delta["posts_teeth_contact"] + delta["seating"]
        + delta["foot_seat_allowance"])
    row["static_factor"] = min(s["static_factor"] for s in row["strength_sections"].values())
    row["FKM"] = min(s["FKM"] for s in row["strength_sections"].values())
    row["contact_pass"] = all(
        0 <= s["foot_bearing"]["pressure_min_MPa"] <= s["foot_bearing"]["pressure_max_MPa"] <= 390.
        and s["raised_pad_contact_315"]["peak_MPa"] <= s["integral_contact_screen_MPa"]
        for s in supports.values())
    row["passes_hand_screen"] = (row["static_factor"] >= 1.5 and row["FKM"] >= 1.10
                                 and row["height_300_mm"] <= .6
                                 and row["mass"]["delta_chamber_kg"] <= 70.)
    return row


def calculate():
    saved, roof, gate = input_data()
    baseline = None
    wider = None
    for row in prior.candidates(roof, roof["gate_shift"], gate):
        dm_kg = row["mass"]["delta_chamber_kg"]
        if row["FKM"] >= 1.10 and dm_kg <= 60.:
            if baseline is None or row["height_300_mm"] < baseline["height_300_mm"]:
                baseline = row
        front, rear = row["stations"]["front"], row["stations"]["rear"]
        dimensions = (front["x_mm"], front["shank_r_mm"], front["head_r_mm"], front["tooth_height_mm"],
                      rear["x_mm"], rear["shank_r_mm"], row["shoe_h_mm"], row["floor_h_mm"],
                      row["face_skin_mm"], row["shoe_four_webs_each_mm"], row["floor_four_webs_each_mm"])
        if dimensions == (194., 35., 67., 70., 38., 23., 185., 225., 14., 18., 23.):
            wider = row
    assert baseline == saved["hand"]["minimum_height_with_FKM"], "T-2.2d baseline does not reproduce"
    assert wider is not None
    variants = [
        variant(baseline, roof, "feet_R15", 18., 23., 70., 56.),
        variant(baseline, roof, "narrower_floor", 18., 22., 70., 56.),
        variant(baseline, roof, "lighter_floor", 18., 21., 70., 56.),
        variant(baseline, roof, "lighter_shoe", 17., 23., 70., 56.),
        variant(baseline, roof, "heavier_shoe", 19., 23., 70., 56.),
        variant(baseline, roof, "heavier_floor", 18., 24., 70., 56.),
        variant(baseline, roof, "thicker_shoe_skin", 18., 23., 70., 56., shoe_skin_mm=16.),
        variant(baseline, roof, "combined", 17., 22., 70., 56.),
        variant(wider, roof, "wider_front_teeth", 17., 22., 70., 56.),
        variant(wider, roof, "floor_band", 17., 22., 70., 56., floor_band_mm=FLOOR_BAND_EXTRA_MM),
    ]
    passing = [row for row in variants if row["passes_hand_screen"]]
    selected = min(passing, key=lambda row: (not row["contact_pass"], not row["floor_local_band"]["extra_mm"],
                                                   row["mass"]["delta_chamber_kg"]), default=None)
    if selected:
        for station in selected["stations"].values():
            dx_mm = max(0., gate["side_rib_max_front_projection_x_mm"] - station["x_mm"])
            dy_mm = max(0., station["y_mm"] - gate["plate_outline_mm_R"][0] / 2)
            assert abs(hypot(dx_mm, dy_mm) - station["outer_envelope_r_mm"]
                       - station["gate_swept_clearance_mm"]) < 1e-9
    return dict(baseline=baseline, variants=variants, selected=selected), roof, saved


if __name__ == "__main__":
    hand, _, _ = calculate()
    for case in (hand["baseline"], *hand["variants"]):
        print(case.get("label", "T-2.2d"), *(f"{value:.4f}" for value in (
            case["mass"]["delta_chamber_kg"], case["height_300_mm"], case["FKM"],
            case["static_factor"], case["support_checks"]["front"].get("foot_bearing", {}).get(
                "pressure_max_MPa", case["support_checks"]["front"]["bearing_foot_MPa"]))))
