#!/usr/bin/env python3
"""Verify the W02 routing audit from the task's completion checkout."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
CASE_AUDIT = "cae/cases/T-R3-42-STATES-01/case_audit.json"
CAD_MANIFEST = "cad/build/w02_rebuild_20261119/manifest.json"
DRAWINGS_COMPLETION = "coordination/completions/T-R4-DRAWINGS-01/completion.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def git_blob(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def check_hash(record, data):
    require(sha256(data).hexdigest() == record["sha256"], f"Hash mismatch: {record['path']}")


def verify():
    completion = read(PACKAGE / "completion.json")
    release = read(PACKAGE / "claim_release.json")
    audit = read(completion["case_audit"]["path"])
    index = read("coordination/task_index.json")
    source = completion["source_main_sha"]

    for record in [completion["input_manifest"], *audit["evidence"],
                   *(task["claim_release"] for task in completion["closed_tasks_excluded"])]:
        require(record["commit"] == source, f"Unexpected input commit: {record['path']}")
        check_hash(record, git_blob(source, record["path"]))
    for record in [completion["accepted_claim"], completion["case_audit"],
                   release["completion"], *completion["outputs"]]:
        check_hash(record, (ROOT / record["path"]).read_bytes())

    accepted = (ROOT / completion["accepted_claim"]["path"]).read_bytes()
    require(accepted == git_blob(release["claim_main_sha"], release["original_claim_path"]),
            "Archived claim differs from the original main claim")
    require(release["claim_main_sha"] == completion["claim_main_sha"]
            and release["accepted_claim"] == completion["accepted_claim"]
            and json.loads(accepted)["owner_session"] == release["owner_session"] == completion["CODEX_SESSION_ID"]
            and release["status"] == "RELEASED" and release["effective_owner_session"] is None
            and release["effective_lease_expires_at"] is None
            and not (ROOT / release["original_claim_path"]).exists(), "Claim release mismatch")

    drawings = json.loads(git_blob(source, DRAWINGS_COMPLETION))["input_audit"]
    gaps = audit["missing_inputs"]
    require(len(gaps) == 8 and gaps.keys() == {entry["id"] for entry in drawings["blocked_inputs"]},
            "Drawings input coverage mismatch")
    for identifier, gap in gaps.items():
        require(gap["status"] == "UNKNOWN" and gap["value"] is None
                and all(gap[key] for key in ("reason", "audit_role", "source_owner", "available_sources",
                                             "required_source", "acceptance")),
                f"Incomplete evidence routing for {identifier}")

    r3_cases = json.loads(git_blob(source, CASE_AUDIT))["cases"]
    cad_cases = json.loads(git_blob(source, CAD_MANIFEST))["cases"]
    cases = audit["cases"]
    require(cases.keys() == {row["case_id"] for row in r3_cases} == cad_cases.keys()
            and len(cases) == completion["physical_state_count"] == 42, "Case count mismatch")
    for r3 in r3_cases:
        case_id = r3["case_id"]
        case = cases[case_id]
        cad = cad_cases[case_id]
        require(case["variant"] == r3["variant"] == cad["variant"]
                and case["phase"] == r3["phase"] == cad["state"]
                and case["physical_input_status"] == r3["status"] == cad["geometry_for_load_case"] == "BLOCKED_INPUTS"
                and case["physical_execution"] == r3["actual_result"]["execution"] == cad["physical_evaluation"] == "NOT_RUN"
                and case["phase_load"] == {"status": "UNKNOWN", "value": None, "reason": r3["phase_load"]["missing_input"]}
                and case["phase_boundary_conditions"] == {"status": "UNKNOWN", "value": None,
                                                         "reason": cad["contact_and_load_requirement"]}
                and set(case["common_missing_inputs"]) == {"PHASE_LOADS", "42_STATES_GEOMETRY", "REV_CONNECTION_CAPACITY"},
                f"Physical disposition mismatch: {case_id}")
    require(audit["case_counts"] == {"BLOCKED_INPUTS": 42, "NOT_RUN": 42}
            and audit["physical_sections_4_5_6"] == completion["physical_sections_4_5_6"] == "NOT_RUN",
            "Physical totals mismatch")

    indexed = {task["task_id"]: task for task in index["tasks"]}
    task = indexed[completion["task_id"]]
    require(task["status"] == read(task["path"])["status"] == "COMPLETED"
            and task["claim_release_status"] == "RELEASED"
            and index["next_dispatch"] == completion["next_dispatch"]
            and index["next_dispatch"]["task_id"] is None
            and index["next_dispatch"]["status"] == "BLOCKED_INPUTS"
            and not any(row["status"] == "READY" for row in indexed.values())
            and not any("routing_blocker" in row for row in indexed.values() if row["status"] == "COMPLETED"),
            "Dispatch state mismatch")
    for closed in completion["closed_tasks_excluded"]:
        task = indexed[closed["task_id"]]
        require(task["status"] == "COMPLETED"
                and read(task["claim_release"])["status"] == "RELEASED",
                f"Previously closed task reopened: {task['task_id']}")

    print("PASS: 42 blocked physical cases, 8 input groups, task queue and claim release")


if __name__ == "__main__":
    verify()
