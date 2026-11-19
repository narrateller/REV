"""Replay the R2 input audit against the pinned Git revision."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import yaml

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from repo_support import finite, flatten, nonempty  # noqa: E402

ACTIVE = "params/registry.yaml"
SCOPED = "baselines/operator-fork-20261118/r2/params/registry.yaml"
STATE_STATUS = "params/T-R3-42-STATES-01-status.json"
CASE_AUDIT = "cae/cases/T-R3-42-STATES-01/case_audit.json"
PDF = "sources/raw/Target_object_BP500.pdf"
BROCHURE_HASH = "bf7276191a73b3d9a22ef516316bc59aac5d12fd708a7adc454bd6d9da4bec0c"
UNKNOWN_METADATA = "В источнике отсутствует численная оценка допуска/неопределённости."
SCOPED_SOURCES = {
    "verification/r2_bp500_design_basis/design_basis.md":
        "baselines/operator-fork-20261118/r2/verification/r2_bp500_design_basis/design_basis.md.source.txt",
    "scripts/bp500_basis.py": "baselines/operator-fork-20261118/r2/scripts/bp500_basis.py",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git_blob(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def check_inputs(manifest):
    base = manifest["source_main_sha"]
    inputs = {}
    for item in manifest["inputs"]:
        path = item["path"]
        blob = git_blob(base, path)
        require(sha256(blob).hexdigest() == item["sha256"], f"Input hash mismatch: {path}")
        inputs[path] = blob

    pointer = inputs[PDF].decode("ascii")
    require(f"oid sha256:{BROCHURE_HASH}" in pointer.splitlines(), "Wrong BP500 PDF pointer")
    require(sha256((ROOT / PDF).read_bytes()).hexdigest() == BROCHURE_HASH,
            "Wrong or unmaterialized BP500 PDF")
    return inputs


def audit_registry(path, blob, base, expected, detail_lifecycles):
    registry = yaml.safe_load(blob)
    parameters = flatten(registry)
    expected_statuses = Counter(expected)
    statuses = Counter(entry["lifecycle"] for entry in parameters.values())
    require(statuses == expected_statuses, f"Unexpected lifecycle counts in {path}: {statuses}")

    sources = {}
    details = {}
    for name, entry in sorted(parameters.items()):
        provenance = entry["provenance"]
        require(all(nonempty(text) for text in (
            entry["unit"], entry["scope"], entry["meaning"], provenance["kind"],
            provenance["source_ref"], provenance["locator"],
        )), f"Incomplete traceability for {path}:{name}")
        require(type(entry["revision"]) is int and entry["revision"] > 0,
                f"Missing revision for {path}:{name}")
        require(entry["tolerance"] is None and entry["uncertainty"] is None,
                f"Unexpected numerical tolerance or uncertainty for {path}:{name}")
        if entry["value"] is None:
            require(entry["lifecycle"] == "RAW" and nonempty(entry["unknown_reason"]),
                    f"Missing UNKNOWN reason for {path}:{name}")
        else:
            require(finite(entry["value"]) and entry["unknown_reason"] is None,
                    f"Invalid numeric value or UNKNOWN reason for {path}:{name}")

        source = provenance["source_ref"]
        if source not in sources:
            source_path = SCOPED_SOURCES.get(source, source) if path == SCOPED else source
            sources[source] = {
                "path_at_source_main": source_path,
                "git_blob_sha256": sha256(git_blob(base, source_path)).hexdigest(),
            }
        for dependency in entry["depends_on"]:
            dep_id = dependency["id"]
            require(dep_id in parameters and parameters[dep_id]["revision"] == dependency["revision"],
                    f"Unresolved dependency {dep_id} for {path}:{name}")
        if entry["lifecycle"] == "CALCULATED":
            require(entry["depends_on"] and nonempty(entry["calculation"]["expression"]),
                    f"Missing calculation traceability for {path}:{name}")

        if entry["lifecycle"] in detail_lifecycles:
            details[name] = {
                field: entry[field] for field in (
                    "revision", "value", "unit", "lifecycle", "scope", "meaning",
                    "tolerance", "uncertainty", "unknown_reason", "provenance", "depends_on",
                )
            }
            if entry["value"] is None:
                details[name]["status"] = "UNKNOWN"

    return {
        "path": path,
        "git_blob_sha256": sha256(blob).hexdigest(),
        "units_policy": registry["units_policy"],
        "counts": {**statuses, "total": len(parameters)},
        "domain_counts": {key: len(entries) for key, entries in registry["domains"].items()},
        "scope_counts": dict(sorted(Counter(entry["scope"] for entry in parameters.values()).items())),
        "unit_counts": dict(sorted(Counter(entry["unit"] for entry in parameters.values()).items())),
        "unknown_count": sum(entry["value"] is None for entry in parameters.values()),
        "null_tolerance_and_uncertainty_count": len(parameters),
        "null_tolerance_and_uncertainty_reason": UNKNOWN_METADATA,
        "provenance_sources": sources,
        "parameters": details,
    }


def audit_physical_cases(status, audit):
    expected_ids = {f"S42-{index:03d}" for index in range(1, 43)}
    require(set(status["cases"]) == expected_ids, "Incorrect R3 status case IDs")
    audit_ids = [row["case_id"] for row in audit["cases"]]
    require(len(audit_ids) == len(expected_ids) and set(audit_ids) == expected_ids,
            "Missing or duplicate R3 case in the physical audit")
    require(status["physical_input_status"] == "BLOCKED_INPUTS"
            and status["physical_execution"] == "NOT_RUN"
            and audit["counts"] == {"BLOCKED_INPUTS": 42},
            "Incorrect R3 physical audit totals")
    cases = {}
    for row in sorted(audit["cases"], key=lambda item: item["case_id"]):
        case_id = row["case_id"]
        load, boundary = row["phase_load"], row["boundary_conditions"]
        results = row["actual_result"]
        require(row["status"] == "BLOCKED_INPUTS" and results["execution"] == "NOT_RUN"
                and all(value is None for key, value in results.items() if key != "execution"),
                f"Unexpected physical result for {case_id}")
        require(load["status"] == boundary["status"] == "UNKNOWN"
                and load["value"] is None and boundary["value"] is None
                and nonempty(load["missing_input"]) and nonempty(boundary["phase_requirement"])
                and boundary["missing_inputs"], f"Incomplete input blocker for {case_id}")
        cases[case_id] = {
            **{key: row[key] for key in ("variant", "phase", "scenario", "mode", "units",
                                        "source_frame", "sign", "pose_domain", "interface_ids")},
            "physical_input_status": row["status"],
            "physical_execution": results["execution"],
            "conditional_screening_status": status["cases"][case_id]["status"],
            "phase_load": load,
            "boundary_conditions": boundary,
        }
    return {"source": CASE_AUDIT, "conditional_status_source": STATE_STATUS,
            "physical_status_counts": audit["counts"], "cases": cases}


def check_site_inputs(dataset, inputs):
    require(dataset["dataset_id"] == "REV_R2_BP500_SITE_INPUTS" and dataset["revision"] == 1,
            "Unexpected site input dataset identity")
    require(dataset["source_pdf_sha256"] == BROCHURE_HASH, "Incorrect site PDF hash")
    entries = dataset["parameters"]
    require({row["status"] for row in entries.values()} == {"RAW", "UNKNOWN"},
            "Incorrect site input status set")
    conversions = {
        ("mm", "m"): (0.001, 0),
        ("kg", "kg"): (1, 0),
        ("V", "V"): (1, 0),
        ("Hz", "Hz"): (1, 0),
        ("A", "A"): (1, 0),
        ("degC", "K"): (1, 273.15),
    }
    for name, row in entries.items():
        source = row["source"]
        require(source["path"] in inputs and nonempty(source["locator"]),
                f"Unpinned or incomplete source for {name}")
        require(nonempty(row["scope"]) and nonempty(row["unit"])
                and row["tolerance"] is None and row["uncertainty"] is None
                and nonempty(row["uncertainty_reason"]), f"Incomplete applicability for {name}")
        if row["status"] == "UNKNOWN":
            require(row["value"] is None and nonempty(row["unknown_reason"]),
                    f"Missing site input UNKNOWN reason for {name}")
            continue
        require(source["path"] == PDF and source["pdf_page"] in (3, 4),
                f"Unverified BP500 page for {name}")
        original = row["as_printed"]
        factor, offset = conversions[original["unit"], row["unit"]]
        values = row["value"] if isinstance(row["value"], list) else [row["value"]]
        printed = original["value"]
        printed = printed if isinstance(printed, list) else [printed]
        require(len(values) == len(printed) and all(
            finite(x) and finite(y) and abs(x - (y * factor + offset)) <= 1e-9
            for x, y in zip(values, printed)
        ), f"Invalid conversion for {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-git", action="store_true", help="verify committed audit and output hashes")
    mode.add_argument("--write", action="store_true", help="regenerate registry_audit.json")
    args = parser.parse_args()

    manifest = json.loads((PACKAGE / "input_manifest.json").read_bytes())
    inputs = check_inputs(manifest)
    base = manifest["source_main_sha"]
    audit = {
        "task_id": manifest["task_id"],
        "source_main_sha": base,
        "active_registry": audit_registry(ACTIVE, inputs[ACTIVE], base,
                                          {"CALCULATED": 1072, "ASSUMED": 47, "RAW": 25},
                                          {"ASSUMED", "RAW"}),
        "scoped_r2_registry": audit_registry(SCOPED, inputs[SCOPED], base,
                                             {"RAW": 41, "ASSUMED": 5, "CALCULATED": 9},
                                             {"RAW", "ASSUMED", "CALCULATED"}),
        "physical_states": audit_physical_cases(json.loads(inputs[STATE_STATUS]),
                                                json.loads(inputs[CASE_AUDIT])),
    }
    check_site_inputs(json.loads((PACKAGE / "site_inputs.json").read_bytes()), inputs)

    audit_path = PACKAGE / "registry_audit.json"
    if args.write:
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                              encoding="utf-8", newline="\n")
    else:
        require(json.loads(audit_path.read_bytes()) == audit, "Stored input audit differs from replay")
        output_path = PACKAGE / "output_manifest.json"
        output_bytes = output_path.read_bytes()
        require(output_bytes == git_blob("HEAD", output_path.relative_to(ROOT).as_posix()),
                "Output manifest differs from HEAD")
        outputs = json.loads(output_bytes)
        require(outputs["source_main_sha"] == base, "Output manifest has a different source revision")
        expected_paths = {PACKAGE.joinpath(name).relative_to(ROOT).as_posix() for name in (
            "README.md", "input_manifest.json", "registry_audit.json", "site_inputs.json", "verify_output.py",
        )}
        require(len(outputs["outputs"]) == len(expected_paths)
                and {item["path"] for item in outputs["outputs"]} == expected_paths,
                "Output manifest does not name the entire R2 package")
        for item in outputs["outputs"]:
            path = item["path"]
            blob = git_blob("HEAD", path)
            require(sha256(blob).hexdigest() == item["sha256"] and (ROOT / path).read_bytes() == blob,
                    f"Output hash mismatch: {path}")
    print("PASS R2 input audit: active 1144, scoped R2 55, physical BLOCKED_INPUTS 42")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(f"FAIL R2 input audit: {exc}")
