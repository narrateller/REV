"""Replay and verify the W02 iteration 02 engineering package."""

import argparse
from collections import Counter
import json
import re

from model import (
    Iteration02, KEYS, SEAT, PACKAGE, PARENT, ROOT, check_analytical_limits,
    check_inputs, check_row, close, read, require,
)
from force_calc import ASSUMED, BLOCKED, ENVELOPE, FREE, PARAMS, W02, case_samples, drives, pressure_samples, round_values, single_branch
from verify_output import CATALOG, digest, encode, extrema_for, git

HERE = PACKAGE.relative_to(ROOT).as_posix()
TASK = PACKAGE.name
TASK_FILE = f"coordination/tasks/{TASK}/task.json"
CLAIM = f"coordination/claims/{TASK}.json"
REV_NATIVE = "cad/source/force_geometry/redesign_1p5mn_02"


def verify_inputs(model, git_mode):
    audit = read(f"{HERE}/input_manifest.json")
    task = read(TASK_FILE)
    pins = audit["input_sha256"]
    require(all(pins[p] == h for p, h in task["inputs"].items()), "Task input hashes differ")
    for path, expected in pins.items():
        data = (ROOT / path).read_bytes()
        require(digest(data) == expected, f"Input SHA-256 differs: {path}")
        if git_mode:
            blob = git(audit["source_main_sha"], path)
            if blob.startswith(b"version https://git-lfs.github.com/spec/v1"):
                oid = re.search(rb"^oid sha256:([a-f0-9]{64})\r?$", blob, re.M)
                size = re.search(rb"^size (\d+)\r?$", blob, re.M)
                require(oid and size and oid[1].decode() == expected and int(size[1]) == len(data), f"LFS: {path}")
            else:
                require(blob == data, f"Git blob differs: {path}")
    if git_mode:
        claim = json.loads(git(audit["claim_main_sha"], CLAIM))
        author = audit["author_sessions"][0]
        require(claim["status"] == "ACCEPTED_MAIN" and claim["owner_session"] == author["CODEX_SESSION_ID"]
                and claim["model_label"] == author["model_label"] and claim["source_main_sha"] == audit["source_main_sha"],
                "Claim invalid")
    base = W02()
    check_inputs(base, git_mode)
    check_analytical_limits(base)
    manifest = read(f"{REV_NATIVE}/manifest.json")
    require(task["geometry_manifest"] == f"{REV_NATIVE}/manifest.json"
            and task["r4_result_commit_sha"] == read("coordination/completions/T-R4-REDESIGN-1.5MN-02/completion.json")[
                "result_commit_sha"] and model.dataset["revision"] == manifest["revision"] == 2
            and set(model.overlay["applies_to"]) == set(manifest["variants"]) == {"B-V1", "B-V2"}, "B overlay mismatch")
    for asset in manifest["variants"].values():
        require(pins[f"{REV_NATIVE}/{asset['path']}"] == asset["sha256"], "Revision 02 FCStd hash differs")
    for path, faces in model.faces.items():
        force = 1e6
        width = faces[1][1][0] - faces[1][0][0]
        height = faces[1][2][1] - faces[1][1][1]
        data = model.receiver(path, force, 0, 0)
        close(data["peak_MPa"], force / (2 * width * height), "Revision 02 centric contact")
        for part in data["parts_negative_positive_y"]:
            close(part["force_N"], force / 2, "Revision 02 centric reaction")


def strength_minimum(rows, components):
    return min((row["section_4_strength"][name]["factor"], i, name)
               for i, row in enumerate(rows, 1) if row["status"] != FREE
               for name in components if row["section_4_strength"][name]["factor"] is not None)


def guide_summary(rows):
    return {variant: {sample: {
        mode: min((round_values(row[f"rails_{mode}"]["chamber_clearance_remaining_mm"]), i)
                  for i, row in enumerate(rows, 1) if row["variant"] == variant and row["sample"] == sample)
        for mode in ("PIN_PIN", "FIXED_FIXED")}
        for sample in sorted({row["sample"] for row in rows})}
        for variant in sorted({row["variant"] for row in rows})}


def generate(model):
    states = read(ENVELOPE)["cases"]
    catalog = read(CATALOG)["cases"]
    require(len(states) == len(catalog) == 42 and set(states) == {c["case_id"] for c in catalog}, "42-state coverage")
    files, samples, results = {}, [], {}
    index = {"task_id": TASK, "scope": ASSUMED, "physical_case_count": 0,
             "physical_case_status": BLOCKED, "physical_sections_4_5_6": "NOT_RUN", "cases": {}}
    closed_max = model.r4["stroke"]["B_closed_work_limit_stroke_mm"]
    geometry_limits = model.c["stroke"]
    pose_points = [model.c["rear_reserve"] + q * 1000 for case in states.values() for q in case["pose_samples_q_m"]]
    outside = sum(not 0 <= stroke <= geometry_limits for stroke in pose_points)
    physical_unknown = read(PARAMS)["physical_values"]
    for case_id, case in sorted(states.items()):
        rows = list(case_samples(model, case))
        results[case_id] = rows
        counts = Counter(row["mode"] for row in rows)
        nonzero = [item for item in case["axial_samples"] if item["F_x_N"]]
        poses = len(case["pose_samples_q_m"])
        held = sum(len(item["held_axial_paths"]) for item in nonzero) * poses * len(model.offsets)
        require(counts["STATIC_HOLD"] == counts["SLIDING_LIMIT"] == held
                and counts["AXIAL_RELEASE"] == poses * len(nonzero)
                and counts["ZERO_GRAVITY_ONLY"] == poses * (len(case["axial_samples"]) - len(nonzero)),
                f"Incomplete coverage: {case_id}")
        for row in rows:
            check_row(model, row)
            require(row["path"] not in (KEYS, SEAT) or row["stroke_mm"] <= closed_max + 1e-8, "B closed stroke")
        filename = f"results/{case_id}.jsonl"
        index["cases"][case_id] = {
            "variant": case["variant"], "phase": case["phase"], "status": ASSUMED,
            "physical": {"status": BLOCKED, **{k: physical_unknown[k] for k in ("value", "reason")}},
            "connection_capacity": {"value": None, "reason": "Supplier and installed joint capacity unavailable."},
            "pose_samples_q_m": case["pose_samples_q_m"], "interface_ids": case["r4_interface_ids"],
            "count_by_mode": dict(counts), "extrema": extrema_for(rows), "sample_file": filename,
        }
        files[filename] = b"".join(encode(row, True) for row in rows)
        samples.extend(rows)

    bounds = list(pressure_samples(model))
    for row in bounds:
        check_row(model, row, pressure_bound=True)
    limit = model.l["supply_bar"][1]
    require(max(p for row in bounds for ports in row["ports_cap_annulus_bar"] for p in ports) == limit,
            "Pressure-bound coverage")
    fit = model.fit_at_pressure_limit()
    for path in (KEYS, SEAT):
        jams = [row["section_6_receiver"] for row in bounds if row["path"] == path
                and row["sample"] == "SYMMETRIC_EXTENSION"]
        require(len(jams) == 2 * 2 * len(model.offsets), "315 bar receiver coverage")
        fit["paths"][path]["nominal_minimum_factor"] = min(row["factor"] for row in jams)
    require(all(0 <= row["stroke_mm"] <= geometry_limits for row in bounds), "Pressure-bound stroke")
    threshold = model.l["min_strength_factor"]
    normal, upper = (extrema_for(rows) for rows in (samples, bounds))
    reverse = single_branch(model, states)
    require(reverse, "Reverse cases missing")
    components = ("rod_1", "rod_2", "crosshead_strip")
    critical_normal, critical_bound = (strength_minimum(rows, components) for rows in (samples, bounds))
    working_port = max(port for row in samples if row["status"] != FREE
                       for port, _ in row["pressure_port_and_supply_bar"] if port is not None)
    criteria = {
        "coverage_42_ids": len(results) == 42,
        "working_port_within_315_bar": working_port <= limit,
        "working_supply_within_250_bar": normal["max_required_supply_bar_row_branch"][0] <= model.l["supply_bar"][0],
        "zero_source_points_outside_mechanical_stroke": outside == 0,
        "rod_and_crosshead_strength": min(critical_normal[0], critical_bound[0]) >= threshold,
        "other_screened_strength": min(normal["min_strength_factor_row_component"][0],
                                       upper["min_strength_factor_row_component"][0]) >= threshold,
        "compression_over_euler": max(normal["max_compression_over_euler_row_component_K"][0],
                                      upper["max_compression_over_euler_row_component_K"][0]) < model.l["max_euler_utilization"],
        "B_key_backing_contact_at_315_bar": fit["paths"][KEYS]["factor"] >= threshold,
        "B_seat_contact_at_315_bar": fit["paths"][SEAT]["factor"] >= threshold,
        "B_seat_open_when_keys_loaded": fit["remaining_seat_clearance_mm"] > 0,
        "B_key_running_gap_and_registration": min(fit["minimum_key_running_gap_mm"],
                                                   fit["effective_key_registration_margin_mm"]) > 0,
        "working_guide_clearance": normal["min_punch_chamber_gap_mm_row"][0] > 0,
        "pressure_bound_guide_clearance": upper["min_punch_chamber_gap_mm_row"][0] > 0,
        "single_branch_full_reverse": all(item["status"] == "WITHIN_PORT_LIMIT" for item in reverse.values()),
    }
    index.update(
        case_count=len(results), state_samples=dict(Counter(row["mode"] for row in samples)),
        source_pose_points=len(pose_points), source_stroke_range_mm=[min(pose_points), max(pose_points)],
        source_points_outside_stroke=outside, working_max_port_bar=working_port,
        normal_extrema=normal, pressure_bound_extrema=upper, pressure_bound_samples=len(bounds),
        critical_normal_factor_row_component=critical_normal, critical_bound_factor_row_component=critical_bound,
        pressure_bound_guide_min_mm_row_by_variant_and_mode=guide_summary(bounds),
        single_branch_reverse=reverse, contact_fit_at_315_bar_path="results/receiver_fit.json",
        row_references="1-based; normal cases concatenated by ID; pressure bounds in pressure_bounds.jsonl",
        criteria={key: "PASS" if condition else "FAIL" for key, condition in criteria.items()},
        engineering_status="PASS" if all(criteria.values()) else "FAILED",
    )
    files["results/index.json"] = encode(index)
    files["results/receiver_fit.json"] = encode(fit)
    files["results/pressure_bounds.jsonl"] = b"".join(encode(row, True) for row in bounds)
    files["results/phase_hydraulics.json"] = encode(drives(model, states, results))
    return index, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check-git", action="store_true")
    args = parser.parse_args()
    model = Iteration02()
    verify_inputs(model, args.check_git)
    index, files = generate(model)
    sources = ["README.md", "input_audit.md", "input_manifest.json", "model.py", "verify_output.py"]
    if index["engineering_status"] == "FAILED":
        sources.append("engineering_failure_note.md")
    for name in sources:
        files[name] = (PACKAGE / name).read_bytes()
    files["output_manifest.json"] = encode({
        "task_id": TASK, "scope": ASSUMED, "engineering_status": index["engineering_status"],
        "sha256": {f"{HERE}/{name}": digest(data) for name, data in sorted(files.items())},
        "command": f"python {HERE}/verify_output.py --check-git",
    })
    for name, data in files.items():
        path = PACKAGE / name
        if args.write and name not in sources:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        require(path.read_bytes() == data, f"Replay mismatch: {name}")
        if args.check_git:
            require(git("", f"{HERE}/{name}") == data, f"Index mismatch: {name}")
    require({p.relative_to(PACKAGE).as_posix() for p in (PACKAGE / "results").iterdir()}
            == {name for name in files if name.startswith("results/")}, "Unexpected result files")
    print(f"PASS replay: {index['case_count']} IDs, {index['pressure_bound_samples']} pressure bounds, "
          f"engineering {index['engineering_status']}")


if __name__ == "__main__":
    main()
