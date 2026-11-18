"""Run or verify all assumed static screening combinations without rewriting inputs."""

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path
import subprocess
import sys

from screening import Sample, equilibrated, released, section_properties

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKAGE = HERE.relative_to(ROOT).as_posix()
TASK = HERE.name
INPUTS = "cae/cases/design_boundary_phase_load_envelope"
CLAIM_INPUT = f"coordination/tasks/{TASK}/input_manifest.json"
PHYSICAL_INPUT = "cae/cases/T-R3-42-STATES-01/r4_reconciliation.json"
OUTPUTS = ("results.jsonl", "summary.json")
SAMPLE_KEYS = ("guide_span", "actuator_y", "reaction_y", "reaction_z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def hash_file(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def load_inputs(check_git):
    recorded = json.loads((ROOT / CLAIM_INPUT).read_bytes())
    require(recorded["task_id"] == TASK and recorded["scope"] == "ASSUMED_STATIC_SCREENING",
            "Wrong task input manifest")
    paths = {item["path"]: item for item in recorded["inputs"]}
    task_record = f"coordination/tasks/{TASK}/task.json"
    for path, entry in paths.items():
        if path != task_record:
            require(hash_file(path) == entry["sha256"], f"Pinned input changed: {path}")
        if check_git:
            name = f"{recorded['source_main_sha']}:{path}"
            require(git("rev-parse", name).decode().strip() == entry["git_object"]
                    and sha256(git("show", name)).hexdigest() == entry["sha256"], f"Git blob differs: {path}")
    for entry in recorded["cad_lfs_inputs"]:
        require(hash_file(entry["path"]) == entry["sha256"], f"Materialized FCStd differs: {entry['path']}")
    if check_git:
        subprocess.run([sys.executable, f"{INPUTS}/verify_output.py", "--check-git"], cwd=ROOT, check=True)
    assumptions = json.loads((ROOT / INPUTS / "assumptions.json").read_bytes())
    envelope = json.loads((ROOT / INPUTS / "envelope.json").read_bytes())
    require(envelope["assumptions_sha256"] == paths[f"{INPUTS}/assumptions.json"]["sha256"],
            "Envelope and assumptions do not match")
    require(envelope["scope"] == recorded["scope"] and len(envelope["cases"]) == 42
            and assumptions["lifecycle"] == "ASSUMED", "Unexpected envelope scope or case coverage")
    return recorded, assumptions, envelope


def nominal_samples(case, geometry):
    grid = geometry["assumed_samples_m"]
    axes = (case["pose_samples_q_m"], *(grid[key] for key in SAMPLE_KEYS))
    for values in axes:
        require(values and len(values) == len(set(values)) and all(map(math.isfinite, values)),
                "Empty, duplicate or non-finite geometry samples")
    require(min(axes[0]) >= 0 and min(grid["guide_span"]) > 0, "Invalid relative pose or guide span")
    return [Sample(*values) for values in product(*axes)]


def case_combinations(case_id, case, geometry, assumptions, sections):
    variant = case["variant"]
    dimensions = geometry["reference_dimensions_m"]
    poses = nominal_samples(case, geometry)
    loads = case["axial_samples"]
    require(case["envelope_input_status"] == "READY_ASSUMED" and case["envelope_execution"] == "NOT_RUN"
            and case["physical_input_status"] == "BLOCKED_INPUTS" and case["physical_execution"] == "NOT_RUN",
            f"{case_id}: input lifecycle differs")
    require(len(loads) == len({row["sample"] for row in loads}), f"{case_id}: duplicate load labels")
    zero_loads = [row for row in loads if row["F_x_N"] == 0]
    require(len(zero_loads) == 1 and zero_loads[0] == {"sample": "ZERO", "F_x_N": 0, "held_axial_paths": []},
            f"{case_id}: invalid unloaded control")
    base = {"case_id": case_id, "variant": variant, "phase": case["phase"],
            "physical_status": case["physical_input_status"], "physical_execution": case["physical_execution"]}
    rows = [{
        **base, "id": f"{case_id}/ZERO", "branch": "UNLOADED_FREE_AXIAL_DOF", "load_sample": "ZERO",
        "F_x_N": 0, "geometry_m": asdict(poses[0]), "axial_path": None,
        **equilibrated(0, poses[0], None, variant, dimensions, sections, assumptions),
    }]
    held_index = 0
    paths = assumptions["held_axial_paths"]
    for load in loads:
        force = load["F_x_N"]
        label = load["sample"]
        if force == 0:
            continue
        load_paths = load["held_axial_paths"]
        require(math.isfinite(force) and load_paths and len(load_paths) == len(set(load_paths)),
                f"{case_id}/{label}: invalid force or path set")
        require(all(paths[path]["sign"] in {"EITHER", "COMPRESSION" if force > 0 else "TENSION"}
                    for path in load_paths), f"{case_id}/{label}: path has incompatible sign")
        for path, pose in product(load_paths, poses):
            held_index += 1
            rows.append({
                **base, "id": f"{case_id}/H{held_index:04d}", "branch": "HELD", "load_sample": label,
                "F_x_N": force, "geometry_m": asdict(pose), "axial_path": path,
                **equilibrated(force, pose, path, variant, dimensions, sections, assumptions),
            })
        rows.append({
            **base, "id": f"{case_id}/RELEASED-{label}", "branch": "AXIALLY_RELEASED", "load_sample": label,
            "F_x_N": force, "covered_geometry_samples": len(poses), "axial_path": None, **released(force),
        })
    count = len(poses) * sum(len(row["held_axial_paths"]) for row in loads)
    require(held_index == count and count > 0, f"{case_id}: not all held combinations executed")
    return rows


def measured_metrics(row):
    s4, s5, s6 = (row[key] for key in ("section_4", "section_5", "section_6"))
    guide = s4["mobile"]["G_plus_N"]
    my, mz = s4["applied_pair_moment_Nm"][1:]
    yield "guide_transverse_N", math.hypot(*guide[1:])
    yield "guide_abs_Y_N", abs(guide[1])
    yield "guide_abs_Z_N", abs(guide[2])
    yield "axial_branch_abs_N", abs(s4["mobile"]["axial_branch_x_N"])
    yield "abs_M_y_Nm", abs(my)
    yield "abs_M_z_Nm", abs(mz)
    for member in ("rod", "carrier"):
        yield f"{member}_abs_stress_Pa", s5[member]["max_abs_stress_Pa"]
        yield f"{member}_stress_over_reference_yield", s5[member]["abs_stress_over_reference_yield"]
    for element, comparison in s6["comparisons"].items():
        for condition, result in comparison.items():
            prefix = f"{element}/{condition}"
            yield f"{prefix}/compression_over_euler", result["compression_over_euler"]


def summarize(rows):
    metrics = {}
    branches = Counter()
    euler_flags = Counter()
    max_force = max_moment = 0.0
    for row in rows:
        branches[row["branch"]] += 1
        if row["status"] == "NO_STATIC_EQUILIBRIUM":
            continue
        for name, value in measured_metrics(row):
            record = metrics.get(name)
            if record is None or value > record["value"]:
                metrics[name] = {"value": value, "combination_id": row["id"], "exact_ties": 1}
            elif value == record["value"]:
                record["exact_ties"] += 1
        for body in ("mobile", "frame"):
            residual = row["section_4"][body]["residual"]
            max_force = max(max_force, *map(abs, residual["force_N"]))
            max_moment = max(max_moment, *map(abs, residual["moment_Nm_at_O"]))
        for comparison in row["section_6"]["comparisons"].values():
            euler_flags.update(result["elastic_check"] for result in comparison.values())
    return {
        "combination_counts": dict(branches),
        "governing_maxima": metrics,
        "largest_residual_component": {"force_N": max_force, "moment_Nm": max_moment},
        "euler_applicability_counts": dict(euler_flags),
    }


def sensitivity(rows, envelope):
    """Paired results for the two spans, free lengths and K values at work peaks."""
    report = {}
    for case_id, case in envelope["cases"].items():
        if case["phase"] not in {"work_peak", "work_peak_closed"}:
            continue
        candidates = [row for row in rows if row["case_id"] == case_id and row["branch"] == "HELD"]
        reference_path = candidates[0]["axial_path"]
        candidates = [row for row in candidates if row["axial_path"] == reference_path]
        grid = envelope["variants"][case["variant"]]["assumed_samples_m"]
        section = "carrier/y"
        lowest_q, highest_q = min(case["pose_samples_q_m"]), max(case["pose_samples_q_m"])
        short, long = min(grid["guide_span"]), max(grid["guide_span"])
        y, ey, ez = max(grid["actuator_y"]), min(grid["reaction_y"]), max(grid["reaction_z"])
        by_pose = {Sample(**row["geometry_m"]): row for row in candidates}
        start = by_pose[Sample(lowest_q, short, y, ey, ez)]
        end = by_pose[Sample(highest_q, short, y, ey, ez)]
        wider = by_pose[Sample(highest_q, long, y, ey, ez)]
        guide_short = math.hypot(*end["section_4"]["mobile"]["G_plus_N"][1:])
        guide_long = math.hypot(*wider["section_4"]["mobile"]["G_plus_N"][1:])
        euler_start = start["section_6"]["comparisons"][section]
        euler_end = end["section_6"]["comparisons"][section]
        length_ratio = end["section_6"]["free_length_m"]["carrier"] / start["section_6"]["free_length_m"]["carrier"]
        guide_ratio = guide_short / guide_long
        k_ratio = euler_end["FIXED_FREE"]["compression_over_euler"] / euler_end["PIN_PIN"]["compression_over_euler"]
        pose_ratio = euler_end["PIN_PIN"]["compression_over_euler"] / euler_start["PIN_PIN"]["compression_over_euler"]
        require(math.isclose(guide_ratio, long / short) and math.isclose(k_ratio, 4.0)
                and math.isclose(pose_ratio, length_ratio**2), f"Unexpected span/K/free-length sensitivity: {case_id}")
        report[case_id] = {
            "same_offsets_load_and_path": [start["id"], end["id"], wider["id"]],
            "short_over_long_span_guide_resultant": guide_ratio,
            "carrier_y_end_over_start_compression_over_euler": pose_ratio,
            "carrier_y_fixed_free_over_pin_pin_compression_over_euler": k_ratio,
        }
    require(len(report) == len(envelope["variants"]), "Missing one work-peak sensitivity comparison per variant")
    return report


def json_bytes(data, *, compact=False):
    options = {"separators": (",", ":")} if compact else {"indent": 2}
    return (json.dumps(data, ensure_ascii=False, allow_nan=False, **options) + "\n").encode()


def run(check_git):
    recorded, assumptions, envelope = load_inputs(check_git)
    physical = json.loads((ROOT / PHYSICAL_INPUT).read_bytes())["cases"]
    require(physical.keys() == envelope["cases"].keys(), "Physical blocker coverage differs")
    variants = envelope["variants"]
    sections = {name: section_properties(variant["reference_dimensions_m"]) for name, variant in variants.items()}
    results = []
    per_case = {}
    for case_id, case in envelope["cases"].items():
        name = case["variant"]
        original = physical[case_id]
        require((original["status"], original["execution"]) ==
                (case["physical_input_status"], case["physical_execution"]),
                f"{case_id}: physical status differs from pinned source")
        rows = case_combinations(case_id, case, variants[name], assumptions, sections[name])
        per_case[case_id] = {
            "variant": name, "phase": case["phase"], "r4_interface_ids": case["r4_interface_ids"],
            **summarize(rows), "status": "CALCULATED_ASSUMED",
            "physical_status": original["status"], "physical_execution": original["execution"],
            "physical_required_inputs": original["required_inputs"],
            "physical_phase_load_blocker": original["phase_load_blocker"],
        }
        results.extend(rows)

    require(len({row["id"] for row in results}) == len(results), "Duplicate result identifiers")
    scope = {
        "task_id": TASK, "author_sessions": [recorded["author_session"]],
        "scope": "ASSUMED_STATIC_SCREENING", "dispatch_main_sha": recorded["source_main_sha"],
        "r4_geometry_sha": envelope["r4_source_sha"],
    }
    summary = {
        **scope, "case_count": len(per_case), "physical_blocked_cases": len(per_case), "physical_calculated_cases": 0,
        "section_properties_si": sections,
        "all": summarize(results),
        "variants": {name: summarize(row for row in results if row["variant"] == name) for name in variants},
        "paired_sensitivity": sensitivity(results, envelope),
        "cases": per_case,
    }
    data = {
        OUTPUTS[0]: b"".join(json_bytes(row, compact=True) for row in results),
        OUTPUTS[1]: json_bytes(summary),
    }
    reproduction = f"python {PACKAGE}/verify_output.py --check-git"
    data["output_manifest.json"] = json_bytes({
        **scope,
        "input_manifest": {"path": CLAIM_INPUT, "sha256": hash_file(CLAIM_INPUT)},
        "upstream_verification": f"python {INPUTS}/verify_output.py --check-git",
        "reproduction": reproduction,
        "regeneration": reproduction + " --write",
        "tests": [f"python -m unittest discover -s {PACKAGE} -v",
                  "python -m unittest discover -s tests -v"],
        "validation": ["python verify_output.py --check-git", "python scripts/check_registry.py --check-git"],
        "runtime": "Python 3.12.14, Linux x86_64, standard library for the screening solver",
        "code": [{"path": f"{PACKAGE}/{name}", "sha256": hash_file(f"{PACKAGE}/{name}")}
                 for name in ("screening.py", "verify_output.py", "test_screening.py")],
        "outputs": [{"path": f"{PACKAGE}/{name}", "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
                    for name, raw in data.items()],
    })
    return data, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true", help="Verify Git inputs and replay the upstream envelope")
    parser.add_argument("--write", action="store_true", help="Regenerate only the three derived screening artifacts")
    args = parser.parse_args()
    data, summary = run(args.check_git)
    for name, raw in data.items():
        path = HERE / name
        if args.write:
            path.write_bytes(raw)
        else:
            require(path.read_bytes() == raw, f"Saved output differs: {path}")
    counts = summary["all"]["combination_counts"]
    print(f"PASS: {summary['case_count']} cases, {counts['HELD']} held combinations, "
          f"{counts['UNLOADED_FREE_AXIAL_DOF']} controls, {counts['AXIALLY_RELEASED']} released branches")


if __name__ == "__main__":
    main()
