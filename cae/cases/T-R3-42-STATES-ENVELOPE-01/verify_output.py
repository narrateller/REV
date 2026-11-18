#!/usr/bin/env python3
"""Replay the finite load envelope and verify saved evidence."""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import product
import json
from math import pi, sqrt
from pathlib import Path
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
INPUT = PACKAGE.parent / "design_boundary_phase_load_envelope"
MANIFEST = PACKAGE / "manifest.json"
ZERO = [0, 0, 0]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_bytes())


def wrench(loads):
    """Sum forces and r cross F about the R4 origin."""
    forces = [0.0] * 3
    moments = [0.0] * 3
    for (x, y, z), (fx, fy, fz) in loads.values():
        forces[0] += fx
        forces[1] += fy
        forces[2] += fz
        moments[0] += y * fz - z * fy
        moments[1] += z * fx - x * fz
        moments[2] += x * fy - y * fx
    require(max(map(abs, forces)) < 1e-8, f"Force balance failed: {forces}")
    require(max(map(abs, moments)) < 1e-8, f"Moment balance failed: {moments}")
    return {"force_N": forces, "moment_Nm": moments}


def euler(force, length, area, inertia, k, elastic, reference):
    effective_length = k * length
    critical = pi * pi * elastic * inertia / (effective_length * effective_length)
    critical_stress = critical / area
    return dict(P_cr_N=critical, KL_over_radius=effective_length / sqrt(inertia / area),
                load_over_P_cr=force / critical, P_cr_over_A_Pa=critical_stress,
                P_cr_over_A_over_reference=critical_stress / reference,
                interpretation=("COMPARISON_ONLY_CRITICAL_STRESS_AT_OR_ABOVE_REFERENCE_YIELD"
                                if critical_stress >= reference else "IDEAL_ELASTIC_COMPARISON"))


def held(case_id, sample, force, q, path, span, actuator_y, reaction_y, reaction_z,
         dimensions, settings):
    width = dimensions["chamber_width"]
    height = dimensions["chamber_height"]
    diameter = dimensions["rod_diameter"]
    elastic = settings["comparison_material"]["young_modulus_Pa"]
    reference = settings["comparison_material"]["reference_yield_Pa"]
    my = -force * reaction_z
    mz = force * (reaction_y - actuator_y)
    ry, rz = -mz / span, my / span
    moving = {
        "actuator": ([q, actuator_y, 0], [force, 0, 0]),
        path: ([q, reaction_y, reaction_z], [-force, 0, 0]),
        "G-": ([q - span / 2, 0, 0], [0, -ry, -rz]),
        "G+": ([q + span / 2, 0, 0], [0, ry, rz]),
    }
    frame = {name: (position, [-value for value in vector])
             for name, (position, vector) in moving.items()}
    area_rod = pi * diameter * diameter / 4
    inertia_rod = area_rod * diameter * diameter / 16
    area_carrier = width * height
    iy = area_carrier * height * height / 12
    iz = area_carrier * width * width / 12
    normal = -force
    rod_stress = normal / area_rod
    corners = [
        dict(y_m=y, z_m=z, sigma_x_Pa=normal / area_carrier + my * z / iy - mz * y / iz)
        for y, z in product((-width / 2, width / 2), (-height / 2, height / 2))
    ]
    carrier_stress = max(abs(corner["sigma_x_Pa"]) for corner in corners)
    rod_length = diameter + q
    carrier_length = dimensions["chamber_length"] + q
    stability = {"status": "NOT_APPLICABLE", "reason": "AXIAL_TENSION"}
    if normal < 0:
        stability = {"status": "CALCULATED_ASSUMED", "modes": {
            name: {boundary: euler(force, length, area, inertia, k, elastic, reference)
                   for boundary, k in settings["buckling_comparisons"].items()}
            for name, length, area, inertia in (
                ("rod", rod_length, area_rod, inertia_rod),
                ("carrier_y", carrier_length, area_carrier, iy),
                ("carrier_z", carrier_length, area_carrier, iz),
            )
        }}
    return dict(case_id=case_id, sample=sample, F_x_N=force, q_m=q, axial_path=path,
                span_m=span, actuator_y_m=actuator_y, reaction_y_m=reaction_y,
                reaction_z_m=reaction_z, status="CALCULATED_ASSUMED",
                section_4=dict(moving=moving, frame=frame, moving_balance=wrench(moving),
                               frame_balance=wrench(frame), M_y_Nm=my, M_z_Nm=mz,
                               guide_resultant_N=sqrt(ry * ry + rz * rz),
                               open_stop_and_lock_axial_N=0 if path == "B_OPEN_BENCH_FIXTURE" else None),
                section_5=dict(N_N=normal, rod_sigma_x_Pa=rod_stress, rod_max_abs_Pa=abs(rod_stress),
                               rod_over_reference=abs(rod_stress) / reference, carrier_corners=corners,
                               carrier_max_abs_Pa=carrier_stress, carrier_over_reference=carrier_stress / reference),
                section_6=stability)


def calculate(case_id, case, variant, settings):
    poses = case["pose_samples_q_m"]
    if case["phase"] in {"return_full", "return_full_open"}:
        poses = poses[::-1]
    samples = variant["assumed_samples_m"]
    result = []
    for sample in case["axial_samples"]:
        name, force = sample["sample"], sample["F_x_N"]
        if name == "ZERO":
            result.append(dict(case_id=case_id, sample=name, F_x_N=0, q_m=poses[0],
                               status="CALCULATED_ASSUMED", axial_path="RELEASED",
                               section_4=dict(axial_dof="FREE", guide_reaction_N=ZERO,
                                              axial_reaction_N=0, force_residual_N=ZERO, moment_residual_Nm=ZERO),
                               section_5=dict(rod_max_abs_Pa=0, carrier_max_abs_Pa=0),
                               section_6=dict(status="NOT_APPLICABLE", reason="ZERO_AXIAL_LOAD")))
            continue
        for q, path, span, ya, ey, ez in product(
            poses, sample["held_axial_paths"], samples["guide_span"], samples["actuator_y"],
            samples["reaction_y"], samples["reaction_z"],
        ):
            result.append(held(case_id, name, force, q, path, span, ya, ey, ez,
                               variant["reference_dimensions_m"], settings))
        for q, ya in product(poses, samples["actuator_y"]):
            result.append(dict(case_id=case_id, sample=name, F_x_N=force, q_m=q,
                               actuator_y_m=ya, axial_path="RELEASED", axial_residual_N=force,
                               status="NO_STATIC_EQUILIBRIUM", section_4=None,
                               section_5=None, section_6=None,
                               reason="NONZERO_AXIAL_FORCE_WITHOUT_AXIAL_SUPPORT"))
    require(sum(row["sample"] == "ZERO" for row in result) == 1, f"Missing ZERO: {case_id}")
    return result


def extrema(rows):
    peaks = {}

    def record(metric, value, row):
        if metric not in peaks or value > peaks[metric]["value"]:
            peaks[metric] = {"value": value, "row": row["row"]}

    for row in rows:
        if "moving" not in (row["section_4"] or {}):
            continue
        support = row["section_4"]
        record("guide_resultant_N", support["guide_resultant_N"], row)
        record("abs_guide_y_N", abs(support["moving"]["G+"][1][1]), row)
        record("abs_guide_z_N", abs(support["moving"]["G+"][1][2]), row)
        record("abs_axial_path_N", abs(row["F_x_N"]), row)
        record("rod_abs_stress_Pa", row["section_5"]["rod_max_abs_Pa"], row)
        record("carrier_abs_stress_Pa", row["section_5"]["carrier_max_abs_Pa"], row)
        for section, modes in row["section_6"].get("modes", {}).items():
            for boundary, mode in modes.items():
                record(f"{section}/{boundary}/load_over_P_cr", mode["load_over_P_cr"], row)
    return peaks


def build():
    envelope = load(INPUT / "envelope.json")
    settings = load(INPUT / "assumptions.json")
    rows, cases = [], {}
    for case_id, case in envelope["cases"].items():
        variant = envelope["variants"][case["variant"]]
        group = calculate(case_id, case, variant, settings)
        for number, row in enumerate(group, start=len(rows) + 1):
            row["row"] = number
        cases[case_id] = dict(variant=case["variant"], phase=case["phase"],
                              status="CALCULATED_ASSUMED", lifecycle="ASSUMED",
                              physical_input_status=case["physical_input_status"],
                              physical_execution=case["physical_execution"],
                              row_range_inclusive=[group[0]["row"], group[-1]["row"]],
                              counts=Counter(row["status"] for row in group), peaks=extrema(group))
        rows.extend(group)
    require(len(cases) == 42, "Case coverage must be 42")
    summary = dict(scope=envelope["scope"], case_count=len(cases),
                   counts=Counter(row["status"] for row in rows), peaks=extrema(rows), cases=cases)
    return {
        "samples.jsonl": "".join(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                                 for row in rows).encode(),
        "summary.json": (json.dumps(summary, indent=2, allow_nan=False) + "\n").encode(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        subprocess.run([sys.executable, str(INPUT / "verify_output.py")]
                       + (["--check-git"] if args.check_git else []), cwd=ROOT, check=True)
        outputs = build()
        manifest = load(MANIFEST)
        for name, expected in manifest["inputs_sha256"].items():
            data = (ROOT / name).read_bytes()
            require(sha256(data).hexdigest() == expected, f"Input hash mismatch: {name}")
            if args.check_git:
                original = subprocess.check_output(
                    ["git", "show", f"{manifest['input_commit']}:{name}"], cwd=ROOT)
                require(original == data, f"Input differs from pinned Git blob: {name}")
        for name, data in outputs.items():
            path = PACKAGE / name
            if args.write:
                path.write_bytes(data)
            else:
                require(path.read_bytes() == data, f"Replay mismatch: {name}")
                require(sha256(data).hexdigest() == manifest["outputs_sha256"][name],
                        f"Output hash mismatch: {name}")
        print("PASS: 42 case IDs, both free-body balances, and deterministic §§4/5/6 replay")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
