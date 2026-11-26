"""Reproduce the D-GK-09 load check before selecting the roof."""

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from itertools import product
import json
from math import exp, expm1, prod
from pathlib import Path
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
K_GRID = (0.35, 0.45, 0.60)
MU_GRID = (0.20, 0.25, 0.30)
FORCES_N = {"nominal": 1_520_000, "300_bar": 1_700_000, "315_bar": 1_785_000}
D_GK_09_LOADED_LIMIT_MM = 89.4
STOP_LIMIT_N = 1_150_000


def read_yaml(relative_path):
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def read_geometry():
    spec = spec_from_file_location("t12_geometry", ROOT / "calc/T-1.2/geometry.py")
    module = module_from_spec(spec)
    previous_setting = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous_setting
    return module


def shoe_load(force_N, K, mu, width_mm, area_mm2, perimeter_mm, length_mm, gate_x_mm, window_x_mm):
    punch_x_mm = gate_x_mm - length_mm
    start_mm = max(punch_x_mm, window_x_mm[0])
    end_mm = min(gate_x_mm, window_x_mm[1])
    if start_mm >= end_mm:
        raise ValueError("Briquette and shoe do not overlap")

    decay_per_mm = K * mu * perimeter_mm / area_mm2
    face_MPa = force_N / area_mm2
    radial_start_MPa = K * face_MPa * exp(-decay_per_mm * (start_mm - punch_x_mm))
    contact_length_mm = end_mm - start_mm
    shoe_force_N = width_mm * radial_start_MPa * -expm1(-decay_per_mm * contact_length_mm) / decay_per_mm
    centroid_x_mm = (start_mm + 1 / decay_per_mm
                     - contact_length_mm / expm1(decay_per_mm * contact_length_mm))

    gate_reaction_N = force_N * exp(-decay_per_mm * length_mm)
    wall_friction_N = force_N - gate_reaction_N
    # Subtract axial friction upstream and downstream of the shoe from the
    # global friction balance, then isolate the top wall's normal reaction.
    start_axial_N = force_N * exp(-decay_per_mm * (start_mm - punch_x_mm))
    end_axial_N = force_N * exp(-decay_per_mm * (end_mm - punch_x_mm))
    roof_axial_friction_N = end_axial_N - gate_reaction_N
    shoe_axial_friction_N = wall_friction_N - (force_N - start_axial_N) - roof_axial_friction_N
    balance_shoe_force_N = shoe_axial_friction_N * width_mm / (mu * perimeter_mm)
    return {
        "face_MPa": face_MPa,
        "decay_per_mm": decay_per_mm,
        "shoe_contact_x_mm": [start_mm, end_mm],
        "radial_start_MPa": radial_start_MPa,
        "radial_end_MPa": K * end_axial_N / area_mm2,
        "centroid_x_mm": centroid_x_mm,
        "moment_about_shoe_axis_Nm": shoe_force_N * (centroid_x_mm - sum(window_x_mm) / 2) / 1000,
        "shoe_force_N": shoe_force_N,
        "gate_reaction_N": gate_reaction_N,
        "wall_friction_N": wall_friction_N,
        "roof_force_N": roof_axial_friction_N * width_mm / (mu * perimeter_mm),
        "balance_shoe_force_N": balance_shoe_force_N,
        "balance_abs_error_N": abs(shoe_force_N - balance_shoe_force_N),
    }


def accepted_load():
    return json.loads((HERE / "round1_load.json").read_text(encoding="utf-8"))


def roof_envelope(roof_mm, accepted):
    section_mm = accepted["section_mm"]
    gate_x_mm = accepted["closed_gate_inner_face_x_mm"] + roof_mm
    cases = {}
    for label, case in accepted["cases"].items():
        rows = [dict(K=row["K"], mu=row["mu"], **shoe_load(
            case["punch_force_N"], row["K"], row["mu"], section_mm[0], accepted["area_mm2"],
            accepted["perimeter_mm"], accepted["loaded_limit_mm"], gate_x_mm, accepted["window_x_mm"]))
            for row in case["grid"]]
        cases[label] = dict(grid=rows, peak=max(rows, key=lambda row: row["shoe_force_N"]))
    return cases


def dose_limits(material, geometry, face_MPa, length_mm, bulk_density_limits, dose_tolerance_fraction):
    """Invert at fixed length, retaining the T-1.1 constitutive envelope."""
    volume_m3 = prod(material.main_section_mm) * length_mm * 1e-9
    rows = []
    for bulk_kg_m3, case in product(bulk_density_limits, geometry.CASES):
        def pressure_at_density(rho_kg_m3):
            return material.face_MPa(rho_kg_m3, bulk_kg_m3, case,
                                     dose_kg=rho_kg_m3 * volume_m3, wall_case="grid")

        rho_kg_m3 = geometry.inverse_increasing(
            pressure_at_density, face_MPa, bulk_kg_m3, material.curve["density_domain_kg_m3"][1])
        dose_limit_kg = rho_kg_m3 * volume_m3
        reconstructed_rho_kg_m3 = material.loaded_density_kg_m3(
            face_MPa, bulk_kg_m3, case, dose_kg=dose_limit_kg, wall_case="grid")
        rows.append({
            "bulk_kg_m3": bulk_kg_m3,
            "constitutive_case": case,
            "loaded_density_kg_m3": rho_kg_m3,
            "dose_limit_kg": dose_limit_kg,
            "dose_setpoint_limit_kg": dose_limit_kg / (1 + dose_tolerance_fraction),
            "released_length_mm": dose_limit_kg / (reconstructed_rho_kg_m3 * volume_m3)
            * length_mm * material.axial_ratio(case),
        })
    return rows


def calculate():
    geometry = read_geometry()
    curve = read_yaml("calc/T-1.1/curve.yaml")
    criteria = read_yaml("ops/criteria/design_criteria.yaml")["criteria"]
    params = read_yaml("design/params.t21.yaml")
    axis = json.loads((ROOT / "calc/T-1.2b/results.json").read_text(encoding="utf-8"))["axis_A"]
    width_mm, height_mm = section_mm = params["chamber"]["section_mm"]
    area_mm2 = width_mm * height_mm
    perimeter_mm = 2 * (width_mm + height_mm)
    window_x_mm = [axis["window_start_x_mm"], axis["window_end_x_mm"]]
    gate_x_mm = axis["closed_gate_inner_face_x_mm"]
    released_limit_mm = criteria["C-PROD-02"]["range_mm"][1]
    recovery_fractions = set(curve["springback"].values())
    if len(recovery_fractions) != 1:
        raise ValueError("A common load length requires equal springback in the constitutive branches")
    recovery_fraction, = recovery_fractions
    recovery_limit_mm = released_limit_mm / (1 + recovery_fraction)
    length_mm = min(D_GK_09_LOADED_LIMIT_MM, recovery_limit_mm)
    dose_tolerance_fraction = geometry.DOSE_TOLERANCE_FRACTION

    cases = {}
    for label, force_N in FORCES_N.items():
        grid = []
        for K, mu in product(K_GRID, MU_GRID):
            # Change the actual wall transfer while retaining the original base
            # transfer used by T-1.2 to interpret the measured density envelope.
            grid_curve = deepcopy(curve)
            grid_curve["K"]["grid"] = K
            grid_curve["mu"]["grid"] = mu
            material = geometry.Material(grid_curve, params["raw"]["dose_kg"], section_mm)
            load = shoe_load(force_N, K, mu, width_mm, area_mm2, perimeter_mm, length_mm, gate_x_mm, window_x_mm)
            doses = dose_limits(material, geometry, load["face_MPa"], length_mm,
                                criteria["C-RAW-01"]["bulk_density_kg_m3"], dose_tolerance_fraction)
            grid.append({"K": K, "mu": mu, **load, "dose_limits": doses})
        peak = max(grid, key=lambda row: row["shoe_force_N"])
        conservative_dose = min(
            ({"K": row["K"], "mu": row["mu"], **dose} for row in grid for dose in row["dose_limits"]),
            key=lambda dose: dose["dose_limit_kg"],
        )
        cases[label] = {
            "punch_force_N": force_N,
            "peak": {key: value for key, value in peak.items() if key != "dose_limits"},
            "conservative_dose": conservative_dose,
            "grid": grid,
        }

    exceedance_N = cases["300_bar"]["peak"]["shoe_force_N"] - STOP_LIMIT_N
    return {
        "task": "T-2.2d",
        "roof_mm": 0,
        "section_mm": section_mm,
        "area_mm2": area_mm2,
        "perimeter_mm": perimeter_mm,
        "window_x_mm": window_x_mm,
        "closed_gate_inner_face_x_mm": gate_x_mm,
        "axial_springback_fraction": recovery_fraction,
        "released_limit_mm": released_limit_mm,
        "recovery_based_loaded_limit_mm": recovery_limit_mm,
        "loaded_limit_mm": length_mm,
        "dose_upper_tolerance_fraction": dose_tolerance_fraction,
        "stop_limit_N": STOP_LIMIT_N,
        "stop_exceedance_N": exceedance_N,
        "stop_required": exceedance_N > 0,
        "cases": cases,
    }


def main():
    result = calculate()
    (HERE / "round1_load_replay.json").write_text(
        json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    peak_N = result["cases"]["300_bar"]["peak"]["shoe_force_N"]
    status = "STOP" if result["stop_required"] else "PASS"
    print(f"{status}: {peak_N:.3f} N at 300 bar, limit {STOP_LIMIT_N} N")


if __name__ == "__main__":
    main()
