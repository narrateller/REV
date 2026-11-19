"""Replay W02 iteration 03 against the geometry pinned by its task."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import runpy
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
TASK = PACKAGE.name
HERE = PACKAGE.relative_to(ROOT).as_posix()
TASK_FILE = f"coordination/tasks/{TASK}/task.json"
PREVIOUS = PACKAGE.with_name("T-R3-FORCE-CALC-03")


def read(path):
    return json.loads((ROOT / path).read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git_blob(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def verify_input_pins(check_git):
    audit = read(f"{HERE}/input_manifest.json")
    task = read(TASK_FILE)
    pins = audit["input_sha256"]
    require(all(pins.get(path) == digest for path, digest in task["inputs"].items()), "Task input pins")
    for path, digest in pins.items():
        data = (ROOT / path).read_bytes()
        require(sha256(data).hexdigest() == digest, f"Input SHA-256: {path}")
        if check_git:
            blob = git_blob(audit["source_main_sha"], path)
            expected = data
            if blob.startswith(b"version https://git-lfs.github.com/spec/v1"):
                expected = (f"version https://git-lfs.github.com/spec/v1\noid sha256:{digest}\n"
                            f"size {len(data)}\n").encode()
            require(blob == expected, f"Source Git blob: {path}")
    if check_git:
        claim = json.loads(git_blob(audit["claim_main_sha"], f"coordination/claims/{TASK}.json"))
        author = audit["author_sessions"][0]
        require(claim["status"] == "ACCEPTED_MAIN" and claim["source_main_sha"] == audit["source_main_sha"]
                and claim["owner_session"] == author["CODEX_SESSION_ID"] and claim["model_label"] == author["model_label"],
                "Accepted claim")
        for path in audit["r4_artifact_paths"]:
            require(git_blob(audit["r4_result_commit_sha"], path) == git_blob(audit["source_main_sha"], path),
                    f"Delivered R4 Git object: {path}")
    return task


def calculate(task, check_git):
    sys.path.insert(0, str(PREVIOUS))
    replay = runpy.run_path(str(PREVIOUS / "verify_output.py"))
    model = replay["Iteration02"]()
    replay["verify_inputs"](model, check_git)
    index, files = replay["generate"](model)
    criteria = task["acceptance_thresholds"]
    nominal = criteria["nominal_cylinder_pressure_max_bar"]
    maximum = criteria["maximum_cylinder_pressure_bar"]
    require(model.l["supply_bar"][1] == nominal
            and model.l["min_strength_factor"] == criteria["rod_strength_factor_min"]
            == criteria["traverse_strength_factor_min"] == criteria["b_receiver_key_contact_factor_min"]
            and model.l["max_euler_utilization"] == criteria["compression_over_euler_exclusive_max"]
            and criteria["b_receiver_key_contact_pressure_bar"] == nominal
            and criteria["out_of_stroke_points_max"] == criteria["residual_guide_clearance_exclusive_min_mm"] == 0,
            "Task and solver acceptance thresholds")
    bounds = [json.loads(line) for line in files["results/pressure_bounds.jsonl"].splitlines()]
    closures = {}
    for bc in ("PIN_PIN", "FIXED_FIXED"):
        counts = Counter((row["variant"], row["sample"]) for row in bounds
                         if row[f"rails_{bc}"]["chamber_clearance_remaining_mm"] <= 0)
        closures[bc] = [{"variant": variant, "sample": sample, "count": count}
                        for (variant, sample), count in sorted(counts.items())]
    for reverse in index["single_branch_reverse"].values():
        reverse["peak_annulus_bar"] = round(reverse["peak_supply_bar_stroke_yz_branch"][0]
                                            - model.l["supply_drop_bar"], 9)
        reverse["within_maximum_bar"] = reverse["peak_annulus_bar"] <= maximum
    index.update(
        task_id=TASK, calculation_iteration=3, geometry_revision_B=2,
        pressure_limits_bar={"nominal_port": nominal, "maximum_port_subject_to_rating": maximum},
        nonpositive_guide_clearance_counts=closures,
        maximum_pressure_rating={"status": "BLOCKED_INPUTS", "value": None,
                                 "reason": "No supplier rating or allowable duration for the maximum pressure."},
        achievable_branch_mismatch_bar={"status": "BLOCKED_INPUTS", "value": None,
                                        "reason": "Hydraulic circuit, relief settings and isolation logic unavailable."},
        post_contact_reactions={"status": "BLOCKED_INPUTS", "value": None,
                                "reason": "Installed supports and punch/chamber contact compliance unavailable."},
    )
    files["results/index.json"] = replay["encode"](index)
    return index, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--audit", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check-git", action="store_true")
    args = parser.parse_args()
    task = verify_input_pins(args.audit or args.write or args.check_git)
    if args.audit:
        print("PASS input pins, current claim and R4 Git objects")
        return
    index, files = calculate(task, args.check_git or args.write)
    sources = ("verify_output.py", "README.md", "input_audit.md", "input_manifest.json",
               "engineering_failure_note.md" if index["engineering_status"] == "FAILED" else "engineering_verdict.md")
    manifest = {
        "task_id": TASK, "scope": index["scope"], "engineering_status": index["engineering_status"],
        "command": f"python {HERE}/verify_output.py --check-git",
        "sha256": {f"{HERE}/{name}": sha256(data).hexdigest()
                   for name, data in sorted({**files, **{p: (PACKAGE / p).read_bytes() for p in sources}}.items())},
    }
    files["output_manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    for name, data in files.items():
        path = PACKAGE / name
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        require(path.read_bytes() == data, f"Replay mismatch: {name}")
    if args.check_git:
        for name in (*sources, *files):
            require(git_blob("", f"{HERE}/{name}") == (PACKAGE / name).read_bytes(), f"Index mismatch: {name}")
    require({path.relative_to(PACKAGE).as_posix() for path in (PACKAGE / "results").iterdir()}
            == {name for name in files if name.startswith("results/")}, "Unexpected result files")
    print(f"PASS replay: {index['case_count']} IDs, {index['pressure_bound_samples']} pressure bounds, "
          f"engineering {index['engineering_status']}, physical {index['physical_case_status']}")


if __name__ == "__main__":
    main()
