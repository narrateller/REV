#!/usr/bin/env python3
"""Reconcile the R3 audit against a pinned R4 geometry delivery."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from verify_output import HERE, ROOT, git, read_json, require, sha256

R4_TASK = "T-R4-FORCE-GEOMETRY-01"
R4_COMPLETION = f"coordination/completions/{R4_TASK}/completion.json"
R4_MANIFEST = Path("cad/source/force_geometry/manifest.json")
RESULT = HERE / "r4_reconciliation.json"
BINDINGS = "verification/r4_cycle_interfaces/proposal/baseline_bindings.json"


def exact_commit(commit):
    require(git("rev-parse", f"{commit}^{{commit}}").decode().strip() == commit,
            f"Full commit SHA required: {commit}")


def blob(commit, path):
    return git("show", f"{commit}:{path}")


def verify_delivery(geometry_sha, accepted_main_sha):
    exact_commit(geometry_sha)
    manifest_raw = blob(geometry_sha, R4_MANIFEST)
    completion_raw = blob(geometry_sha, R4_COMPLETION)
    completion = json.loads(completion_raw)
    require(completion["task_id"] == R4_TASK and completion["handoff_role"] == "R3"
            and completion["manifest"] == R4_MANIFEST.as_posix()
            and completion["manifest_sha256"] == sha256(manifest_raw), "R4 manifest does not match handoff")
    paths = [R4_MANIFEST, R4_COMPLETION]
    manifest = json.loads(manifest_raw)
    require(manifest["task_id"] == R4_TASK and manifest["author_sessions"] == completion["author_sessions"],
            "R4 task or author mismatch")
    for name, expected_hash in (manifest["input_sha256"] | manifest["tool_sha256"]).items():
        require(sha256(blob(geometry_sha, name)) == expected_hash, f"R4 input or tool hash changed: {name}")
        paths.append(name)
    expected_variants = {"A-V1", "A-V2", "B-V1", "B-V2"}
    require(set(manifest["variants"]) == expected_variants, "R4 variant coverage")
    for variant, native in manifest["variants"].items():
        require(native["path"] == f"{variant}.FCStd" and native["source_scenario"] == f"BASE_{variant[0]}",
                f"R4 variant or FCStd path mismatch: {variant}")
        path = R4_MANIFEST.parent / native["path"]
        raw = blob(geometry_sha, path)
        pointer = raw.startswith(b"version https://git-lfs.github.com/spec/v1\n")
        if pointer:
            require(f"oid sha256:{native['sha256']}\n".encode() in raw, f"Wrong LFS OID: {path}")
        else:
            require(sha256(raw) == native["sha256"], f"Wrong FCStd SHA-256: {path}")
        paths.append(path)
    if accepted_main_sha:
        exact_commit(accepted_main_sha)
        git("merge-base", "--is-ancestor", geometry_sha, accepted_main_sha)
        git("merge-base", "--is-ancestor", accepted_main_sha, "HEAD")
        for path in paths:
            require(blob(geometry_sha, path) == blob(accepted_main_sha, path), f"Accepted main differs: {path}")
        require(not git("ls-tree", "--name-only", accepted_main_sha, "--", f"coordination/claims/{R4_TASK}.json"),
                "R4 still has an active claim at the accepted main SHA")
    return manifest, sha256(manifest_raw)


def reconcile(geometry_sha, accepted_main_sha):
    manifest, manifest_sha = verify_delivery(geometry_sha, accepted_main_sha)
    audit = read_json(HERE / "case_audit.json")
    requests = read_json(HERE / "r4_interface_requests.json")
    bindings = read_json(BINDINGS)["rows"]
    expected = {
        letter: {item["proposed_cad_field"]: item for item in bindings if item["scenario"] == f"BASE_{letter}"}
        for letter in ("A", "B")
    }
    require(len(bindings) == 44 and manifest["original_bindings"] == expected,
            "R4 changed source bindings, including dimensions, rods, strokes or demands")
    expected_ids = {row["interface_id"] for row in requests["interfaces"]}
    require(set(manifest["interfaces"]) == expected_ids and len(expected_ids) == 52, "R4 interface coverage")
    for row in requests["interfaces"]:
        key = row["interface_id"]
        delivered = manifest["interfaces"][key]
        require(delivered["actual_geometry_status"] == "UNKNOWN"
                and delivered["actual_geometry_value"] is None
                and delivered["physical_evaluation"] == "NOT_RUN"
                and delivered["blockers"] == [item["argument"] for item in row["source_unknowns"]],
                f"{key}: geometry status or blockers changed; inspect the new evidence before using this verifier")
    require(len(audit["cases"]) == 42 and set(manifest["cases"]) == {row["case_id"] for row in audit["cases"]},
            "R4 case coverage")
    results = {}
    for row in audit["cases"]:
        case_id = row["case_id"]
        delivered = manifest["cases"][case_id]
        require((delivered["variant"], delivered["state"], delivered["interface_ids"]) ==
                (row["variant"], row["phase"], row["interface_ids"]), f"R4 case or interface changed: {case_id}")
        require(delivered["geometry_for_load_case"] == row["status"] == "BLOCKED_INPUTS"
                and delivered["physical_evaluation"] == row["actual_result"]["execution"] == "NOT_RUN"
                and delivered["required_inputs"] == row["boundary_conditions"]["missing_inputs"]
                and delivered["contact_and_load_requirement"] == row["boundary_conditions"]["phase_requirement"],
                f"{case_id}: case inputs require new review")
        results[case_id] = {
            "status": "BLOCKED_INPUTS",
            "execution": "NOT_RUN",
            "r4_geometry_status": delivered["geometry_for_load_case"],
            "required_inputs": delivered["required_inputs"],
            "phase_load_blocker": row["phase_load"]["missing_input"],
            "conditional_axial_check_repeated": row["conditional_check"] is not None,
        }
    subprocess.run(
        [sys.executable, str(HERE / "verify_output.py")],
        check=True, cwd=ROOT,
    )
    return {
        "geometry_sha": geometry_sha,
        "accepted_main_sha": accepted_main_sha,
        "geometry_manifest": R4_MANIFEST.as_posix(),
        "geometry_manifest_sha256": manifest_sha,
        "r3_audit_sha256": sha256((HERE / "case_audit.json").read_bytes()),
        "r3_r4_request_sha256": sha256((HERE / "r4_interface_requests.json").read_bytes()),
        "counts": {"case_ids": 42, "interface_ids": 52, "bindings": 44, "conditional_axial_checks_repeated": 8},
        "cases": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry-sha", help="Full SHA for a candidate or accepted R4 delivery")
    parser.add_argument("--accepted-main-sha", help="Full SHA of main after the R4 merge")
    parser.add_argument("--write", action="store_true", help="Write the verified, accepted handoff result")
    args = parser.parse_args()
    if args.accepted_main_sha and not args.geometry_sha:
        parser.error("--accepted-main-sha requires --geometry-sha")
    if args.write and not (args.geometry_sha and args.accepted_main_sha):
        parser.error("--write requires both exact SHAs")
    if args.geometry_sha:
        geometry_sha, accepted_main_sha = args.geometry_sha, args.accepted_main_sha
    else:
        saved = read_json(RESULT)
        geometry_sha, accepted_main_sha = saved["geometry_sha"], saved["accepted_main_sha"]
    result = reconcile(geometry_sha, accepted_main_sha)
    raw = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    if args.write:
        RESULT.write_bytes(raw)
    elif not args.geometry_sha:
        require(RESULT.read_bytes() == raw, "Saved R4 reconciliation differs")
    scope = "accepted main" if accepted_main_sha else "candidate"
    print(f"PASS: {scope} R4 manifest, 42 cases, 52 interfaces, 44 unchanged bindings")


if __name__ == "__main__":
    main()
