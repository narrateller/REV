"""Janssen wall tractions and the calibrated T-2.2f transition envelope."""

from functools import lru_cache
from itertools import product
from math import exp, expm1, pi
from pathlib import Path
import json

import yaml

from prior.hand import load_cases

ROOT = Path(__file__).resolve().parents[2]
WIDTH_MM, HEIGHT_MM = 150., 60.
AREA_MM2 = WIDTH_MM * HEIGHT_MM
PERIMETER_MM = 2 * (WIDTH_MM + HEIGHT_MM)
WINDOW_X_MM = (5., 205.)
ROOF_LENGTH_MM = 90.
GATE_X_MM = WINDOW_X_MM[1] + ROOF_LENGTH_MM
LOADED_LENGTH_MM = 89.4
DOSE_LIMIT_KG = 0.853
PRESSURES_BAR = (0, 100, 200, 300, 315)
K_GRID = (0.35, 0.45, 0.60)
MU_GRID = (0.20, 0.25, 0.30)
SKEW_FRACTION = 0.64
PROOF_SKEW_X_MM = 165.2
MAIN_PROJECT_315_N = 1_785_000.


def read_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def band(face_MPa, K, decay_mm_inv, start_mm, end_mm, punch_x_mm):
    if start_mm >= end_mm:
        return {"interval_x_mm": None, "integral_MPa_mm": 0., "centroid_x_mm": None}
    pressure_MPa = face_MPa * K * exp(-decay_mm_inv * (start_mm - punch_x_mm))
    length_mm = end_mm - start_mm
    integral_MPa_mm = pressure_MPa * -expm1(-decay_mm_inv * length_mm) / decay_mm_inv
    centroid_x_mm = start_mm + 1 / decay_mm_inv - length_mm / expm1(decay_mm_inv * length_mm)
    return {"interval_x_mm": [start_mm, end_mm], "inlet_MPa": pressure_MPa,
            "integral_MPa_mm": integral_MPa_mm, "centroid_x_mm": centroid_x_mm}


def janssen(main_force_N, K, mu, length_mm):
    punch_x_mm = GATE_X_MM - length_mm
    decay_mm_inv = K * mu * PERIMETER_MM / AREA_MM2
    face_MPa = main_force_N / AREA_MM2
    roof = band(face_MPa, K, decay_mm_inv, max(WINDOW_X_MM[1], punch_x_mm), GATE_X_MM, punch_x_mm)
    shoe = band(face_MPa, K, decay_mm_inv, max(WINDOW_X_MM[0], punch_x_mm), WINDOW_X_MM[1], punch_x_mm)
    channel = band(face_MPa, K, decay_mm_inv, punch_x_mm, GATE_X_MM, punch_x_mm)
    gate_force_N = main_force_N * exp(-decay_mm_inv * length_mm)
    traction_N = mu * PERIMETER_MM * channel["integral_MPa_mm"]
    return {
        "K": K, "mu": mu, "length_mm": length_mm, "punch_x_mm": punch_x_mm,
        "main_force_N": main_force_N, "face_MPa": face_MPa, "decay_mm_inv": decay_mm_inv,
        "gate_force_N": gate_force_N, "wall_friction_N": traction_N,
        "axial_balance_error_N": main_force_N - gate_force_N - traction_N,
        "roof": roof | {"normal_force_N": WIDTH_MM * roof["integral_MPa_mm"]},
        "shoe": shoe | {"normal_force_N": WIDTH_MM * shoe["integral_MPa_mm"]},
        "floor_normal_force_N": WIDTH_MM * channel["integral_MPa_mm"],
        "each_side_normal_force_N": HEIGHT_MM * channel["integral_MPa_mm"],
    }


@lru_cache(maxsize=1)
def transition_cases():
    # Six density curves in T-2.2f, normalized at the D-GK-10 endpoint.
    return load_cases(ROOF_LENGTH_MM)


def shoe_envelope():
    rows = transition_cases()
    case = max(rows, key=lambda row: row["shoe"]["force_N"])
    transfer = read_json("calc/T-2.6/results.json")["scheme_A"]
    return {
        "shoe_300_bar_N": case["shoe"]["force_N"] * 300 / 315,
        "shoe_315_bar_N": case["shoe"]["force_N"],
        "controlling_case": case,
        "transfer_axial_force_N": transfer["transfer_wall_friction_N"] + transfer["transfer_edge_force_N"],
        "transfer_axial_friction_N": transfer["transfer_wall_friction_N"],
        "transfer_axial_entry_N": transfer["transfer_edge_force_N"],
        "transfer_nominal_dose_kg": transfer["dose_kg"],
        "transfer_design_dose_setpoint_kg": DOSE_LIMIT_KG,
        "dose_tolerance_fraction": 0.05,
    }


@lru_cache(maxsize=8)
def main_cylinder_force_N(pressure_bar):
    params = read_yaml("calc/T-2.6/params/params.t26a.yaml")["main_cylinder"]
    return params["eta"] * pi / 4 * params["bore_mm"] ** 2 * pressure_bar / 10


def final_envelopes():
    return {
        str(pressure_bar): [
            janssen(force_315_N * pressure_bar / 315, K, mu, LOADED_LENGTH_MM)
            | {"basis": basis}
            for basis, force_315_N in (
                ("D-GK-10", MAIN_PROJECT_315_N), ("T-2.6_eta", main_cylinder_force_N(315)))
            for K, mu in product(K_GRID, MU_GRID)
        ] for pressure_bar in PRESSURES_BAR
    }
