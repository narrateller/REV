"""Verify the pinned iteration 04 inputs and replay the R3 evidence."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import runpy
import subprocess
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TASK = HERE.name
CATALOG = "baselines/operator-fork-20261118/state_catalog_index.json"
SCREEN = "cad/force_geometry/redesign_1p5mn_04"
REASON = (
    "Missing phase-specific material loads and reverse retention, installed alignment "
    "and support/contact stiffness, actual cylinder and joint ratings, control and "
    "hydraulic switching constraints, and verified material/joint properties."
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def load(path):
    return json.loads(path.read_bytes())


def sha(data):
    return sha256(data).hexdigest()


def audit(source, task):
    pin = task["r4_result_commit_sha"]
    require(git(source, "rev-parse", "HEAD").decode().strip() == pin, "Wrong R4 source HEAD")
    require(not git(source, "status", "--porcelain", "--untracked-files=no"), "Dirty R4 inputs")
    for revision, entries in task["input_git_blob_sha256"].items():
        for name, expected in entries.items():
            require(sha(git(ROOT, "show", f"{revision}:{name}")) == expected, f"Input blob hash: {name}")
    for name, expected in task["r4_lfs_object_sha256"].items():
        path = source / name
        require(sha(path.read_bytes()) == expected, f"Native object hash: {name}")
        with ZipFile(path) as archive:
            require(archive.testzip() is None and "Document.xml" in archive.namelist(), name)
    subprocess.run([sys.executable, str(source / SCREEN / "verify_output.py"), "--check-git"],
                   cwd=source, check=True)


def peaked(rows, score, key=max):
    row = key(rows, key=score)
    return {"value": score(row), "mode": row["mode"], "sample": row["sample"],
            "stroke_mm": row["stroke_mm"], "eccentricity_yz_mm": row["eccentricity_yz_mm"]}


def summarize(model, case, samples):
    rows = [row for row in samples if row["status"] == "CALCULATED_ASSUMED"]
    released = [row for row in samples if row["status"] == "NO_STATIC_EQUILIBRIUM"]
    require(len(rows) + len(released) == len(samples), "Unexpected sample status")
    force = max(rows, key=lambda row: abs(row["force_N"]))
    connections = ("pin_and_mount_reaction_N", "axial_reaction_on_frame_N",
                   "axial_path_reactions_N", "guide_pad_columns", "branch_forces_N")
    contacts = [row for row in rows if row["section_6_receiver"] is not None]
    strength = {}
    for name in sorted({name for row in rows for name in row["section_4_strength"]}):
        applicable = [row for row in rows
                      if row["section_4_strength"].get(name, {}).get("factor") is not None]
        if applicable:
            strength[name] = peaked(applicable, lambda row: row["section_4_strength"][name]["factor"], min)
    return {
        "variant": case["variant"], "phase": case["phase"],
        "status": "BLOCKED_INPUTS",
        "physical": {"value": None, "reason": REASON},
        "physical_sections_4_5_6": "NOT_RUN",
        "conditional": {
            "status": "CALCULATED_ASSUMED",
            "interface_ids": case["r4_interface_ids"],
            "count_by_mode": dict(sorted(Counter(row["mode"] for row in samples).items())),
            "peak_axial_sample": {name: force[name] for name in
                                  ("sample", "mode", "path", "stroke_mm", "force_N",
                                   "eccentricity_yz_mm", *connections)},
            "no_static_equilibrium": released,
            "peak_force_balance_residual_N": max(round(abs(value), 5) for row in rows for value in row["moving_balance"][0]),
            "peak_moment_balance_residual_Nmm": max(round(abs(value), 3) for row in rows for value in row["moving_balance"][1]),
            "minimum_strength_factors": strength,
            "maximum_compression_over_euler": peaked(
                rows, lambda row: max(item["compression_over_euler"]
                                      for group in row["section_5_stability"].values() for item in group)),
            "minimum_pin_pin_residual_clearance_mm": peaked(
                rows, lambda row: row["rails_PIN_PIN"]["chamber_clearance_remaining_mm"]
                - model.fit["punch_chamber_radial_fit_budget_mm"], min),
            "receiver_contacts_by_path": {
                path: next(row["section_6_receiver"] for row in contacts if row["path"] == path)
                for path in sorted({row["path"] for row in contacts})
            },
        },
    }


def replay(source, task):
    screen = runpy.run_path(str(source / SCREEN / "screen.py"))
    model = screen["Iteration04"]()
    envelope = load(screen["ENVELOPE"])["cases"]
    catalog = load(ROOT / CATALOG)["cases"]
    require(len(catalog) == len(envelope) == 42, "Case count")
    require({row["case_id"] for row in catalog} == envelope.keys(), "Case IDs")
    cases = {}
    rods, traverses = [], []
    outside = 0
    for row in catalog:
        key = row["case_id"]
        case = envelope[key]
        require(case["variant"] == row["source_state"]["variant"]
                and case["phase"] == row["source_state"]["state"], f"Case mapping: {key}")
        require(case["physical_input_status"] == "BLOCKED_INPUTS", f"Physical input status: {key}")
        samples = list(screen["case_samples"](model, case))
        cases[key] = summarize(model, case, samples)
        outside += sum(not 0 <= sample["stroke_mm"] <= model.c["stroke"] for sample in samples)

    report = screen["report"]()
    released = sum(len(case["conditional"]["no_static_equilibrium"]) for case in cases.values())
    require(released == report["axially_released_unbalanced_samples"], "Released sample count")
    for row in screen["pressure_samples"](model):
        strengths = row["section_4_strength"]
        rods.extend(strengths[key]["factor"] for key in ("rod_1", "rod_2")
                    if strengths[key]["factor"] is not None)
        if strengths["crosshead_strip"]["factor"] is not None:
            traverses.append(strengths["crosshead_strip"]["factor"])
    receiver = report["receiver"]["paths"]["B_CLOSED_LOCK_BACKED_STOP"]
    limits = task["prior_r3_acceptance_thresholds"]
    checks = report["checks"] | {
        "all_sampled_strokes": outside == limits["out_of_stroke_points_max"],
        "rod_pressure_envelope": min(rods) >= limits["rod_strength_factor_min"],
        "traverse_pressure_envelope": min(traverses) >= limits["traverse_strength_factor_min"],
    }
    verdict = {
        "task_id": TASK, "engineering_status": "FAILED",
        "physical_input_status": "BLOCKED_INPUTS", "physical_case_count": 0,
        "physical_sections_4_5_6": "NOT_RUN",
        "reason": REASON,
        "conditional_checks": checks,
        "conditional_metrics": {
            "working_supply_bar": report["peak_working_supply_bar"],
            "single_branch_reverse_supply_bar": report["peak_reverse_supply_bar"],
            "single_branch_reverse_port_bar": report["peak_reverse_port_bar"],
            "forward_force_at_250_bar_N": report["available_forward_at_250_bar_N"],
            "stroke": report["stroke"],
            "sample_rows_out_of_stroke": outside,
            "rod_minimum_factor_pressure_envelope": min(rods),
            "traverse_minimum_factor_pressure_envelope": min(traverses),
            "traverse_net_section_factor": report["gross_strength_factors"]["moving_crosshead_net_strip"],
            "minimum_residual_clearance_mm": min(
                report[key]["minimum_residual_gap"][0]
                for key in ("pressure_bound", "working", "single_branch_fixture")),
            "maximum_compression_over_euler": max(
                report[key]["maximum_euler"][0]
                for key in ("pressure_bound", "working", "single_branch_fixture")),
            "B_key_peak_MPa": receiver["peak_MPa"],
            "B_key_comparison_limit_MPa": receiver["comparison_limit_MPa"],
            "B_key_contact_factor": receiver["factor"],
            "B_key_loading_port_bar": report["receiver"]["cap_bar"],
            "iteration_03_reproduced": report["baseline_iteration_03"],
            "unbalanced_axially_released_samples": released,
            "conditional_case_samples": report["working"]["rows"],
        },
    }
    return {"task_id": TASK, "source_commit": task["r4_result_commit_sha"],
            "physical_case_count": 0, "cases": cases}, verdict


def encoded(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--write", action="store_true")
    options.add_argument("--check-git", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    task = load(ROOT / f"coordination/tasks/{TASK}/task.json")
    if args.check_git:
        manifest = load(HERE / "output_manifest.json")
        require(manifest["source_commit"] == task["r4_result_commit_sha"], "Manifest source")
        entry = manifest["input_manifest"]
        require(sha((ROOT / entry["path"]).read_bytes()) == entry["sha256"], "Task manifest hash")
        for name, expected in manifest["sha256"].items():
            require(sha((HERE / name).read_bytes()) == expected, f"Output hash: {name}")
    audit(source, task)
    index, verdict = replay(source, task)
    paths = {
        "results/index.json": index,
        "engineering_verdict.json": verdict,
    }
    compare = runpy.run_path(str(source / Path(SCREEN).with_name("redesign_1p5mn") / "verify_output.py"))["compare"]
    for name, result in paths.items():
        path = HERE / name
        if args.write:
            path.write_bytes(encoded(result))
        else:
            compare(load(path), json.loads(encoded(result)), name)
            require(git(ROOT, "show", f"HEAD:{path.relative_to(ROOT).as_posix()}") == path.read_bytes(),
                    f"Git evidence mismatch: {name}")
    print("PASS: pinned R4 inputs, four FCStd files and replay of 42 conditional case IDs")


if __name__ == "__main__":
    main()
