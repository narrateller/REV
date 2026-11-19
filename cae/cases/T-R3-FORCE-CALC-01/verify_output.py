#!/usr/bin/env python3
"""Reproduce or verify the T-R3-FORCE-CALC-01 calculation package."""
import argparse
from hashlib import sha256
import json
from math import isclose, pi
import re
import subprocess
import sys

from force_calc import (
    ASSUMED, DRIVE_RESULT, ENVELOPE, FREE, LOCK, NO_EQUILIBRIUM, OPEN, PACKAGE,
    PARAMS, ROOT, SEAT, TASK, build, read_json, require,
)

HERE = PACKAGE.relative_to(ROOT).as_posix()
GIT_LFS = b"version https://git-lfs.github.com/spec/v1"


def digest(data):
    return sha256(data).hexdigest()


def git_blob(ref):
    return subprocess.check_output(["git", "show", ref], cwd=ROOT)


def check_source(manifest, check_git):
    definition = manifest["task_definition"]
    pinned_task = git_blob(f"{manifest['source_main_sha']}:{definition['path']}")
    require(digest(pinned_task) == definition["sha256"], "Task definition changed at claim base")
    task = json.loads(pinned_task)
    entries = manifest["input_sha256"]
    require(all(entries.get(path) == expected for path, expected in task["input_sha256"].items()),
            "Task input pins missing")
    claim = json.loads(git_blob(f"{manifest['claim_main_sha']}:coordination/claims/{TASK}.json"))
    require(claim["owner_session"] in manifest["author_sessions"]
            and claim["status"] == "ACCEPTED_MAIN"
            and claim["model_label"] == manifest["model_label"]
            and claim["source_main_sha"] == manifest["source_main_sha"],
            "Input manifest owner differs from accepted claim")
    for path, expected in entries.items():
        data = (ROOT / path).read_bytes()
        require(digest(data) == expected, f"Input SHA256 mismatch: {path}")
        if check_git:
            pinned = git_blob(f"{manifest['source_main_sha']}:{path}")
            if pinned.startswith(GIT_LFS):
                oid = re.search(rb"^oid sha256:([a-f0-9]{64})\r?$", pinned, re.M)
                size = re.search(rb"^size (\d+)\r?$", pinned, re.M)
                require(oid and size and oid[1].decode() == expected and int(size[1]) == len(data),
                        f"Materialized asset differs from Git LFS pin: {path}")
            else:
                require(pinned == data, f"Input differs from base commit: {path}")


def close(actual, expected, label):
    require(isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-8), label)


def check_numerics(cases, summary, drives):
    envelope = read_json(f"{ENVELOPE}/envelope.json")
    for case_id, result in cases.items():
        reference = envelope["cases"][case_id]
        q_count = len(reference["pose_samples_q_m"])
        nonzero = [sample for sample in reference["axial_samples"] if sample["F_x_N"]]
        held_count = 18 * q_count * sum(len(sample["held_axial_paths"]) for sample in nonzero)
        rows = result["samples"]
        require(len(rows) == 1 + len(nonzero) * q_count + held_count, f"{case_id}: missed sample")
        require(result["physical_input_status"] == "BLOCKED_INPUTS"
                and all(value["value"] is None for value in result["physical"].values()),
                f"{case_id}: unexpected physical result")
        for row in rows:
            force = row["F_x_N"]
            if row["path"] == FREE:
                require((force == 0 and row["status"] == ASSUMED) or
                        (row["status"] == NO_EQUILIBRIUM and row["unbalanced_F_x_N"] == force),
                        f"{case_id}: released branch balance")
                continue
            statics = row["statics"]
            for body in ("moving_balance", "frame_balance"):
                require(max(map(abs, statics[body]["force_N"] + statics[body]["moment_Nm"])) < 1e-8,
                        f"{case_id}: numerical equilibrium residual")
            span = row["guide_span_X_m"]
            _, my, mz = statics["applied_pair_moment_Nm"]
            close((span * statics["guide_station_resultant_N"]) ** 2, my ** 2 + mz ** 2,
                  f"{case_id}: guide reaction couple")
            demand = row["section_6_connection_demands"]
            close(demand["reaction_branch_axial_N_on_frame"], force, f"{case_id}: axial reaction")
            stop = demand["B_alternative_paths"]
            if row["path"] == OPEN:
                require(all(value == 0 for value in stop.values()), f"{case_id}: open stop loaded")
            if row["path"] in {SEAT, LOCK}:
                require(stop["stop_face_N"] == force and stop["seat_path_N"] + stop["lock_path_N"] == force,
                        f"{case_id}: closed stop load")
            stability = row["section_5_stability"]
            if force > 0:
                modes = stability["modes"]
                for boundary in modes.values():
                    close(boundary["PIN_PIN"]["P_cr_N"], 4 * boundary["FIXED_FREE"]["P_cr_N"],
                          f"{case_id}: Euler end-condition sensitivity")
            else:
                require(stability["status"] == "NOT_APPLICABLE", f"{case_id}: Euler in tension")

    require(summary["physical_case_count"] == 0 and len(cases) == len(drives["phase_comparisons"]) == 42,
            "Physical and screening scopes or drive coverage differ")
    for geometry in summary["geometry"].values():
        observations = geometry["cad_observations"]
        require(observations["length_unit"] == "mm" and
                observations["axes_xyz"]["CylinderBody"] == [0, 0, 1],
                "CAD discrepancy must remain visible")
    cylinder = drives["ideal_cylinder"]
    inputs = drives["candidate_inputs"]
    close(cylinder["max_extension_N"], pi * inputs["bore_m"] ** 2 / 4 * cylinder["pressure_limit_Pa"],
          "Ideal extension force scale")
    close(cylinder["max_retraction_N_abs"], cylinder["max_extension_N"]
          - pi * inputs["rod_m"] ** 2 / 4 * cylinder["pressure_limit_Pa"], "Ideal retraction force scale")
    for case in drives["phase_comparisons"].values():
        for sample in case["samples"]:
            expected = "EXCEEDS_IDEAL_LIMIT" if abs(sample["F_x_N"]) >= 1e6 else "WITHIN_IDEAL_LIMIT"
            require(sample["force_comparison"] == expected, "Candidate phase force verdict")
            traversal = sample["traversal_comparison"]
            if traversal["status"] == ASSUMED:
                close(traversal["constant_force_work_J"],
                      abs(sample["F_x_N"]) * traversal["constant_force_excursion_m"],
                      "Phase work integral at constant load")


def encode(value, pretty=True):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode()


def output_files(cases, summary, drives):
    result = {f"{HERE}/summary.json": encode(summary), DRIVE_RESULT: encode(drives)}
    for case_id, case in cases.items():
        metadata = encode({key: value for key, value in case.items() if key != "samples"})
        samples = b",\n".join(encode(row, pretty=False).rstrip(b"\n") for row in case["samples"])
        result[f"{HERE}/results/{case_id}.json"] = metadata[:-3] + b',\n  "samples": [\n' + samples + b"\n  ]\n}\n"
    tracked_only = [PARAMS, f"{HERE}/README.md", f"{HERE}/input_audit.md",
                    f"{HERE}/input_manifest.json", f"{HERE}/force_calc.py", f"{HERE}/verify_output.py"]
    manifest = {
        "task_id": TASK, "scope": ASSUMED,
        "output_sha256": {path: digest(data) for path, data in result.items()},
        "package_sha256": {path: digest((ROOT / path).read_bytes()) for path in tracked_only},
    }
    return result, tracked_only, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check-git", action="store_true")
    args = parser.parse_args()
    check_source(read_json(f"{HERE}/input_manifest.json"), args.check_git)
    cases, summary, drives = build()
    check_numerics(cases, summary, drives)
    outputs, tracked_only, manifest = output_files(cases, summary, drives)
    outputs[f"{HERE}/output_manifest.json"] = encode(manifest)
    for name, data in outputs.items():
        file = ROOT / name
        if args.write:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        require(file.read_bytes() == data, f"Replay mismatch: {name}")
    require({path.stem for path in (PACKAGE / "results").glob("*.json")} == set(cases),
            "Unexpected saved case result")
    if args.check_git:
        for path in [*outputs, *tracked_only]:
            require(git_blob(f":{path}") == (ROOT / path).read_bytes(),
                    f"Calculation package differs from Git index: {path}")
    print(json.dumps({"result": "PASS", "scope": ASSUMED, "case_count": len(cases),
                      "sample_status_counts": summary["sample_status_counts"],
                      "physical_case_count": summary["physical_case_count"]}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
