#!/usr/bin/env python3
"""Verify lossless operator rotation. This does not verify engineering results."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = "baselines/operator-fork-20261118"
RETIREMENTS = "coordination/completions/operator-fork-20261118/retirements.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(root, path):
    return json.loads((root / path).read_text(encoding="utf-8"))


def blob(root, record, path_key="path"):
    path = record[path_key]
    data = (root / path).read_bytes()
    require(hashlib.sha256(data).hexdigest() == record["sha256"], f"Hash mismatch: {path}")
    if "size_bytes" in record:
        require(len(data) == record["size_bytes"], f"Size mismatch: {path}")
    return data


def git_blob(root, commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=root)


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
            f"Expected UTC timestamp: {value}")
    return parsed


def claims(root, retired_ids, require_empty=False):
    """Live-clock lease checks remain the actor's preflight, never a time-dependent CI."""
    files = sorted((root / "coordination/claims").rglob("*.json"))
    require(not require_empty or not files, "Rotation must leave no active claim files")
    tasks, owners = set(), set()
    active = 0
    for path in files:
        claim = json.loads(path.read_text(encoding="utf-8"))
        status = claim["status"]
        owner = claim["owner_session"]
        require(claim["role"] in {"R1", "R2", "R3", "R4", "R5"}, f"Invalid role: {path}")
        task = load(root, f"coordination/tasks/{claim['task_id']}/task.json")
        require(task["role"] == claim["role"], f"Task role mismatch: {path}")
        if status == "OPEN":
            require(task["status"] == "READY", f"Open claim requires a READY task: {path}")
            require(all(claim[field] is None for field in (
                "owner_session", "model_label", "proposed_at_utc", "lease_expires_at",
            )), f"Open claim must be unowned and have no lease: {path}")
            continue
        require(owner not in retired_ids, f"Retired session claim: {path}")
        require(status in {"PROPOSED", "ACCEPTED_MAIN"}, f"Archive completed claim: {path}")
        require(owner and owner != "NONE", f"Missing actual owner: {path}")
        require(utc(claim["lease_expires_at"]) > utc(claim["proposed_at_utc"]),
                f"Invalid proposed lease: {path}")
        active += 1
        if status == "ACCEPTED_MAIN":
            require(claim["task_id"] not in tasks, f"Concurrent task owner: {path}")
            require(owner not in owners, f"One session holds multiple tasks: {path}")
            tasks.add(claim["task_id"])
            owners.add(owner)
    return active


def verify(root, check_git=False, require_empty=False):
    rotation = load(root, f"{BASE}/rotation_manifest.json")
    archive = load(root, rotation["context_archive_manifest"])
    count = 0
    for item in archive["snapshots"]:
        data = blob(root, item, "archive_path")
        if check_git and item.get("source_commit"):
            require(data == git_blob(root, item["source_commit"], item["source_path"]),
                    f"Archive differs from original Git blob: {item['archive_path']}")
        count += 1
    retired = load(root, RETIREMENTS)
    for entry in retired["records"]:
        require(entry["effective_owner"] == "NONE" and entry["effective_lease"] is None
                and not entry["lease_renewed"], "Legacy ownership not released")
        for variant in entry["variants"]:
            data = blob(root, variant)
            if check_git:
                require(data == git_blob(root, variant["commit"], entry["original_path"]),
                        f"Ledger differs from original Git blob: {variant['path']}")
            count += 1
        if entry["canonical_claim_archive"]:
            blob(root, entry["canonical_claim_archive"])
            count += 1
    active = claims(root, set(retired["retired_session_ids"]), require_empty)
    baseline = load(root, f"{BASE}/manifest.json")
    require(not baseline["parameter_maturity_promoted"]
            and not baseline["physical_validation_confirmed"], "Baseline is not physical certification")
    for item in baseline["r2_exports"]:
        data = blob(root, item)
        if check_git:
            require(data == git_blob(root, item["source_commit"], item["source_path"]),
                    f"Scoped R2 export differs from original Git blob: {item['path']}")
        count += 1
    if check_git:
        # Frozen trees are checked at the migration merge, not at future engineering heads.
        for directory, tree in baseline["pre_fork_engineering_trees"].items():
            actual = subprocess.check_output(["git", "rev-parse",
                f"{rotation['PR60_merge']}:{directory}"], cwd=root, text=True).strip()
            require(actual == tree, f"Migration changed engineering tree: {directory}")
    catalog = load(root, f"{BASE}/state_catalog_index.json")
    cases = catalog["cases"]
    require(len(cases) == 42 and len({c["case_id"] for c in cases}) == 42,
            "Expected 42 unique source cases, not calculation results")
    require(all(c["status_at_fork"] == "NOT_RUN" for c in cases), "False calculated state at fork")
    if check_git:
        source = git_blob(root, catalog["source_commit"], catalog["source_path"])
        require(hashlib.sha256(source).hexdigest() == catalog["source_sha256"], "Case source hash mismatch")
        require([c["source_state"] for c in cases] == json.loads(source), "Source states changed")
    for path in ("STATE.md", "ISSUES_AND_TASKS.md", "NEXT_MODEL.md"):
        require((root / path).stat().st_size <= rotation["context_budget_bytes_per_file"],
                f"Context budget exceeded: {path}")
    for role in rotation["roles"]:
        require((root / "roles" / role / "README.md").is_file(), f"Missing role onboarding: {role}")
    for task in load(root, rotation["task_index"])["tasks"]:
        definition = load(root, task["path"])
        require(definition["task_id"] == task["task_id"]
                and definition["role"] == task["role"], f"Task index mismatch: {task['task_id']}")
    authority = load(root, rotation["authority"])
    require(authority["accepted_exact_commit"] == baseline["accepted_renderer_commit"], "Wrong accepted C")
    require(authority["closure_type"] == "CLOSED_DOCUMENTARY_BY_OPERATOR_AUTHORIZATION",
            "Do not replace operator waiver with independent R5 PASS")
    require((root / rotation["operator_memo"]).is_file(), "Missing operator decision")
    return {"scope": "OPERATOR_ROTATION_AND_BASELINE_INTEGRITY_ONLY", "result": "PASS",
            "byte_exact_records": count, "archive_snapshots": len(archive["snapshots"]),
            "active_new_claims": active, "legacy_owners": 0,
            "engineering_acceptance": "NOT_EVALUATED", "42_states_at_fork": "NOT_RUN"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--require-empty-claims", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(Path(__file__).resolve().parent, args.check_git, args.require_empty_claims)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
