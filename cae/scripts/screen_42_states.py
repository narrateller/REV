#!/usr/bin/env python3
"""Replay the approved R3 envelope and verify the 42 individual case logs."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
TASK = "T-R3-42-STATES-01"
PACKAGE = Path("cae/cases") / TASK
ENVELOPE = Path("cae/cases/design_boundary_phase_load_envelope")
REPLAY = Path("cae/cases/T-R3-CAE-456-01")
TASK_PATH = Path("coordination/tasks") / TASK / "task.json"
INPUT_MANIFEST = TASK_PATH.with_name("input_manifest_assumed_screening.json")
RESULTS = PACKAGE / "results"
MANIFEST = RESULTS / "manifest.json"
PARAM_STATUS = Path("params") / f"{TASK}-status.json"
DRIVE_DEMAND = Path("drives") / f"{TASK}-envelope-demand.json"
SCRIPT = Path(__file__).resolve().relative_to(ROOT)
CALCULATED = "CALCULATED_ASSUMED"
BLOCKED = "BLOCKED_INPUTS"
RELEASED = "NO_STATIC_EQUILIBRIUM"
NA = "NOT_APPLICABLE"
JOINT_REASON = (
    "The envelope and COTS catalog specify no joint capacity. Actual joint load distribution, "
    "fastener/weld/contact geometry, materials, engagement, preload and applicable allowables are unknown."
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def encode(data, *, compact=False):
    options = {"separators": (",", ":")} if compact else {"indent": 2}
    return (json.dumps(data, ensure_ascii=False, allow_nan=False, **options) + "\n").encode()


def verify_inputs(audit, check_git):
    for name, expected_hash in audit["inputs_sha256"].items():
        path = Path(name)
        if check_git or path == TASK_PATH:
            data = subprocess.check_output(
                ["git", "show", f"{audit['source_main_sha']}:{name}"], cwd=ROOT,
            )
            if path != TASK_PATH:
                require((ROOT / path).read_bytes() == data, f"Working-tree input differs: {name}")
        else:
            data = (ROOT / path).read_bytes()
        require(sha256(data).hexdigest() == expected_hash, f"Input hash differs: {name}")


def unknown(reason):
    return {"status": "UNKNOWN", "value": None, "reason": reason}


def check_connections(row, reactions):
    if row["status"] == RELEASED:
        return {"demand_status": RELEASED, "demand": None, "reason": row["reason"]}
    if row["sample"] == "ZERO":
        return {"demand_status": NA, "demand": None, "reason": "ZERO_WITH_NO_ACTIVE_AXIAL_PATH"}

    moving, frame = reactions["moving"], reactions["frame"]
    path = row["axial_path"]
    require(moving.keys() == frame.keys() == {"actuator", "G-", "G+", path},
            f"Unexpected connection paths at row {row['row']}")
    for name, (point, vector) in moving.items():
        opposite_point, opposite_vector = frame[name]
        require(point == opposite_point and vector == [-value for value in opposite_vector],
                f"Connection action/reaction differs at row {row['row']}: {name}")
    require(frame[path][1] == [row["F_x_N"], 0, 0] and frame["actuator"][1] == [-row["F_x_N"], 0, 0],
            f"Axial load path differs at row {row['row']}")
    is_open = path == "B_OPEN_BENCH_FIXTURE"
    open_reaction = reactions["open_stop_and_lock_axial_N"]
    require(open_reaction == (0 if is_open else None), f"Open stop demand differs at row {row['row']}")
    return {
        "demand_status": CALCULATED,
        "demand": {
            "cylinder_frame_axial_N": frame["actuator"][1][0],
            "guide_frame_resultant_per_section_N": reactions["guide_resultant_N"],
            "axial_path": path,
            "axial_path_force_N": frame[path][1][0],
            "open_stop_and_lock_axial_N": open_reaction,
            "application_points_and_signed_vectors": "support_reactions.frame",
        },
    }


def extend_sample(source, reference_yield):
    reactions, strength, stability = (source[f"section_{n}"] for n in (4, 5, 6))
    reason = source.get("reason")
    if strength is None:
        strength = {"status": RELEASED, "result": None, "reason": reason}
        stability = {"status": RELEASED, "result": None, "reason": reason}
    else:
        strength["status"] = CALCULATED
        for part in ("rod", "carrier"):
            stress = strength[f"{part}_max_abs_Pa"]
            strength[f"{part}_safety_factor"] = reference_yield / stress if stress else None
        if source["sample"] == "ZERO":
            strength["safety_factor_null_reason"] = "ZERO_STRESS_DENOMINATOR"
        for boundaries in stability.get("modes", {}).values():
            for result in boundaries.values():
                result["safety_factor"] = result["P_cr_N"] / abs(strength["N_N"])

    result = {key: value for key, value in source.items() if key not in {"section_4", "section_5", "section_6"}}
    result["record"] = "sample"
    result["support_reactions"] = reactions
    result["section_4_strength"] = strength
    result["section_5_stability"] = stability
    result["section_6_connections"] = dict(
        check_connections(result, reactions), capacity_check_status=BLOCKED, safety_factor=None,
        safety_factor_reason="JOINT_CAPACITY_UNKNOWN",
    )
    return result


def case_extrema(rows):
    minima, drive_peaks = {}, {}
    force_residual = moment_residual = 0.0

    def record_min(name, value, row, **details):
        if name not in minima or value < minima[name]["value"]:
            minima[name] = {"value": value, "row": row, **details}

    for row in rows:
        connection = row["section_6_connections"]
        if connection["demand_status"] != CALCULATED:
            continue
        reactions = row["support_reactions"]
        for body in ("moving_balance", "frame_balance"):
            force_residual = max(force_residual, *map(abs, reactions[body]["force_N"]))
            moment_residual = max(moment_residual, *map(abs, reactions[body]["moment_Nm"]))
        strength = row["section_4_strength"]
        for part in ("rod", "carrier"):
            record_min(f"strength/{part}", strength[f"{part}_safety_factor"], row["row"])
        for mode, boundaries in row["section_5_stability"].get("modes", {}).items():
            for boundary, result in boundaries.items():
                record_min(f"stability/{mode}/{boundary}", result["safety_factor"], row["row"],
                           interpretation=result["interpretation"])
        demand = connection["demand"]
        path, force = demand["axial_path"], demand["axial_path_force_N"]
        peak = drive_peaks.setdefault(path, {})
        sign = "compression_Fx" if force > 0 else "tension_Fx"
        if sign not in peak or abs(force) > abs(peak[sign]["axial_path_force_N"]):
            peak[sign] = {"row": row["row"], "axial_path_force_N": force,
                          "cylinder_frame_axial_N": demand["cylinder_frame_axial_N"]}

    require(force_residual < 1e-8 and moment_residual < 1e-8, "Free-body residual exceeds limit")
    return minima, drive_peaks, {"max_abs_force_component_N": force_residual,
                                 "max_abs_moment_component_Nm": moment_residual}


def build(audit):
    envelope = read(ENVELOPE / "envelope.json")
    assumptions = read(ENVELOPE / "assumptions.json")
    physical_audit = read(PACKAGE / "case_audit.json")
    prior = read(REPLAY / "summary.json")
    rows = defaultdict(list)
    reference_yield = assumptions["comparison_material"]["reference_yield_Pa"]
    for number, line in enumerate((ROOT / REPLAY / "samples.jsonl").read_bytes().splitlines(), start=1):
        row = json.loads(line)
        require(row["row"] == number, f"Sample sequence differs at row {number}")
        rows[row["case_id"]].append(extend_sample(row, reference_yield))

    physical = {case["case_id"]: case for case in physical_audit["cases"]}
    require(rows.keys() == envelope["cases"].keys() == prior["cases"].keys() == physical.keys()
            and len(rows) == len(physical_audit["cases"]) == 42, "Unexpected catalog coverage")

    shared = {"task_id": TASK, "scope": envelope["scope"], "status": CALCULATED,
              "physical_input_status": BLOCKED, "physical_execution": "NOT_RUN"}
    outputs, index, parameter_cases, drive_cases = {}, {}, {}, {}
    totals, global_minima = Counter(), {}
    for case_id, inputs in envelope["cases"].items():
        physical_case = physical[case_id]
        variant = inputs["variant"]
        model_case = prior["cases"][case_id]
        group = rows[case_id]
        counts = Counter(row["status"] for row in group)
        row_numbers = [row["row"] for row in group]
        first, last = model_case["row_range_inclusive"]
        require(row_numbers == list(range(first, last + 1)) and counts == model_case["counts"]
                and sum(row["sample"] == "ZERO" for row in group) == 1
                and any(row["section_6_connections"]["demand_status"] == CALCULATED for row in group),
                f"Sample coverage differs: {case_id}")
        totals.update(counts)
        minima, drive_peaks, balance = case_extrema(group)
        stability_status = CALCULATED if any(name.startswith("stability/") for name in minima) else NA
        status = {"support_reactions": CALCULATED, "section_4_strength": CALCULATED,
                  "section_5_stability": stability_status, "section_6_connection_demands": CALCULATED,
                  "section_6_connection_capacity": BLOCKED}
        for name, result in minima.items():
            if name not in global_minima or result["value"] < global_minima[name]["value"]:
                global_minima[name] = {"case_id": case_id, **result}

        path = RESULTS / f"{case_id}.jsonl"
        physical_inputs = model_case["physical"]
        header = dict(
            shared, record="case", case_id=case_id, variant=variant, phase=inputs["phase"],
            units={"length": "m", "force": "N", "moment": "N*m", "stress": "Pa", "safety_factor": "1"},
            frame=physical_case["source_frame"], sign=physical_case["sign"],
            input_manifest=INPUT_MANIFEST.as_posix(), calculation_manifest=MANIFEST.as_posix(),
            source_main_sha=audit["source_main_sha"],
            input_sha256={name: audit["inputs_sha256"][name] for name in (
                (ENVELOPE / "envelope.json").as_posix(), (ENVELOPE / "assumptions.json").as_posix(),
                (PACKAGE / "case_audit.json").as_posix(),
            )},
            envelope_inputs=inputs, variant_inputs=envelope["variants"][variant],
            comparison_material=assumptions["comparison_material"],
            buckling_comparisons=assumptions["buckling_comparisons"],
            boundary_conditions={
                "guides": "G-/G+ rigid in Y/Z, free in X, no local moment",
                "held_axial_paths": {name: assumptions["held_axial_paths"][name] for name in drive_peaks},
                "released": "Axial DOF free, no axial support; nonzero Fx has no static equilibrium",
            },
            section_statuses=status, minimum_safety_factors=minima, numerical_balance=balance,
            sample_counts=dict(counts), section_6_capacity=unknown(JOINT_REASON),
            physical={
                "phase_load": physical_inputs["phase_load"],
                "boundary_conditions": physical_inputs["boundary_conditions"],
                "support_reactions": physical_inputs["section_4"],
                "section_4_strength": physical_inputs["section_5"],
                "section_5_stability": physical_inputs["section_6"],
                "section_6_connections": unknown(JOINT_REASON),
                "tests": {section: "NOT_RUN" for section in (
                    "support_reactions", "section_4_strength", "section_5_stability", "section_6_connections",
                )},
            },
        )
        outputs[path] = b"".join(encode(entry, compact=True) for entry in [header, *group])
        parameter_cases[case_id] = {"status": CALCULATED, "sections": status, "result": path.as_posix()}
        index[case_id] = dict(parameter_cases[case_id], variant=variant, phase=inputs["phase"],
                              sample_counts=dict(counts), row_range_inclusive=[first, last],
                              numerical_balance=balance, minimum_safety_factors=minima)
        drive_cases[case_id] = {"variant": variant, "phase": inputs["phase"], "result": path.as_posix(),
                                "peak_held_axial_demands_by_path": drive_peaks}

    require(totals == prior["counts"], "Total sample counts differ from the replayed envelope")
    outputs[RESULTS / "index.json"] = encode(dict(shared, case_count=len(index), sample_counts=dict(totals),
        zero_control_count=len(index), source_replay_checks=prior["checks"],
        minimum_safety_factors=global_minima, cases=index))
    outputs[PARAM_STATUS] = encode(dict(shared, evidence=MANIFEST.as_posix(), cases=parameter_cases))
    outputs[DRIVE_DEMAND] = encode(dict(shared, units={"force": "N"},
        sign="Forces on the frame at the chosen path and actuator mount. Positive Fx denotes rod compression.",
        capacity_check_status=BLOCKED, joint_capacity=unknown(JOINT_REASON), cases=drive_cases))
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true", help="Check claimed inputs against their pinned Git blobs")
    parser.add_argument("--write", action="store_true", help="Regenerate the per-case logs and their indexes")
    args = parser.parse_args()
    try:
        audit = read(INPUT_MANIFEST)
        verify_inputs(audit, args.check_git)
        command = [sys.executable, str(REPLAY / "verify_output.py")]
        if args.check_git:
            command.append("--check-git")
        subprocess.run(command, cwd=ROOT, check=True)
        outputs = build(audit)
        originals = set((ROOT / RESULTS).glob("S42-*.jsonl"))
        expected = {ROOT / path for path in outputs if path.suffix == ".jsonl"}
        require(originals <= expected, "Unexpected case log in output directory")
        manifest = {"task_id": TASK, "scope": audit["scope"], "status": CALCULATED,
                    "source_main_sha": audit["source_main_sha"], "author_sessions": audit["author_sessions"],
                    "CODEX_SESSION_ID": audit["author_sessions"][0],
                    "model_label": audit["model_label"],
                    "operator_provided_model_label": audit["operator_provided_model_label"],
                    "input_manifest": INPUT_MANIFEST.as_posix(),
                    "input_manifest_sha256": sha256((ROOT / INPUT_MANIFEST).read_bytes()).hexdigest(),
                    "assumptions": assumptions_metadata(), "generation_environment": audit["audit_environment"],
                    "generation_command": f"python {SCRIPT.as_posix()} --check-git --write",
                    "verification_command": f"python {SCRIPT.as_posix()} --check-git",
                    "sources_sha256": {SCRIPT.as_posix(): sha256((ROOT / SCRIPT).read_bytes()).hexdigest()},
                    "outputs_sha256": {path.as_posix(): sha256(data).hexdigest() for path, data in outputs.items()}}
        outputs[MANIFEST] = encode(manifest)
        if args.write:
            (ROOT / RESULTS).mkdir(exist_ok=True)
            for path, data in outputs.items():
                (ROOT / path).write_bytes(data)
        else:
            for path, data in outputs.items():
                require((ROOT / path).read_bytes() == data, f"Replay differs: {path.as_posix()}")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: 42 case logs, free-body balances, safety factors, connection demands and physical blockers")


def assumptions_metadata():
    return {
        "approved_design_envelope": (ENVELOPE / "README.md").as_posix(),
        "registered_settings": (ENVELOPE / "assumptions.json").as_posix(),
        "physical_blockers": (ENVELOPE / "blockers.md").as_posix(),
        "section_numbering": "Deliverable §§4/5/6 = strength/stability/connections. Source §§4/5/6 = reactions/strength/stability.",
        "strength_safety_factor": "comparison yield / maximum absolute stress of idealized section",
        "stability_safety_factor": "Euler critical load / magnitude of compressive axial force, with the source applicability flag",
        "connection_demand": "Ideal resultants on frame at the modeled application points; open stop and lock carry zero in the open-fixture branch.",
        "connection_capacity": JOINT_REASON,
        "limitations": "Discrete static calculation, ideal load paths and solid sections. No physical test, mesh or time integration.",
    }


if __name__ == "__main__":
    main()
