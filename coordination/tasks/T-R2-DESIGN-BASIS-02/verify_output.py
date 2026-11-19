#!/usr/bin/env python3
"""Verify the pinned inputs and derived values in REV_DESIGN_BASIS r1."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys


PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
ENVELOPE = "cae/cases/design_boundary_phase_load_envelope/envelope.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_bytes())


def git_blob(path, commit):
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT
    )


def verify_file(record, check_git):
    path = record["path"]
    data = (ROOT / path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(digest == record["sha256"], f"SHA256 mismatch: {path}")
    if "size_bytes" in record:
        require(len(data) == record["size_bytes"], f"Size mismatch: {path}")
    if record.get("git_lfs"):
        require(data.startswith(b"%PDF-"), f"Materialize the LFS PDF: {path}")
    if check_git:
        git_data = git_blob(path, record.get("git_commit", "HEAD"))
        if record.get("git_lfs"):
            pointer = [
                "version https://git-lfs.github.com/spec/v1",
                f"oid sha256:{digest}",
                f"size {len(data)}",
            ]
            require(git_data.decode().splitlines() == pointer,
                    f"Git LFS pointer mismatch: {path}")
        else:
            require(data == git_data, f"Git blob mismatch: {path}")


def close(actual, expected, key):
    if isinstance(expected, dict):
        require(actual.keys() == expected.keys(), f"Fields differ: {key}")
        for field, value in expected.items():
            close(actual[field], value, f"{key}.{field}")
    elif isinstance(expected, list):
        require(len(actual) == len(expected), f"Range size differs: {key}")
        for index, (observed, value) in enumerate(zip(actual, expected)):
            close(observed, value, f"{key}[{index}]")
    else:
        require(math.isclose(actual, expected, rel_tol=1e-12),
                f"{key}: {actual} != {expected}")


def verify_calculations(parameters, extracts):
    def value(parameter):
        return parameters[f"DB-{parameter}"]["value"]

    pressure = 98_066.5 * extracts["BP-COMPACTION"]["value"]
    section = math.prod(value("U-SIZE")["transverse_Y_Z_m"])
    thickness = value("U-SIZE")["X_range_m"][1]
    thrust = pressure * section
    supply_pressure = value("HYD-REF")
    main_power = value("MAIN-POWER")
    published_rate = extracts["BP-RATE"]["value"]
    mass = published_rate["mass_each_kg"]
    rate = published_rate["pieces_per_s"]
    throughput = mass * rate
    rho_min, rho_max = value("T-BULK")
    hopper = value("T-HOPPER")
    density = value("U-DENSITY")
    supply = value("ELECTRICAL")
    expected = {
        "FACE-P": pressure,
        "FACE-F": thrust,
        "HYD-BORE-IDEAL": math.sqrt(4 * thrust / (math.pi * supply_pressure)),
        "THROUGHPUT": throughput,
        "CYCLE-TIME": 1 / rate,
        "T-DOSE": [mass / rho_max, mass / rho_min],
        "T-FLOW": [throughput / rho_max, throughput / rho_min],
        "T-HOPPER-MASS": [hopper * rho_min, hopper * rho_max],
        "U-SIZE-CHECK": {
            "X_at_density_m": mass / (density * section),
            "density_at_max_X_kg_m3": mass / (section * thickness),
            "mass_at_max_X_kg": density * section * thickness,
        },
        "HYD-IDEAL-FLOW": main_power / supply_pressure,
        "HYD-IDEAL-SPEED": main_power / thrust,
        "PEAK-TRAVEL": main_power / (rate * thrust),
        "APPARENT-POWER": (
            math.sqrt(3) * supply["line_voltage_V"] * supply["connection_A"]
        ),
        "ENERGY-QUOTIENT": value("INSTALLED-POWER") / throughput,
    }
    calculated = {key[3:] for key, record in parameters.items()
                  if record["status"] == "CALCULATED_ASSUMED"}
    require(calculated == expected.keys(), "Derived values differ from replay set")
    for parameter, result in expected.items():
        close(value(parameter), result, parameter)

    envelope = read_json(ROOT / ENVELOPE)
    load = value("ENVELOPE-V1")
    for name, variant in envelope["variants"].items():
        reference = variant["reference_force_N"]
        close(load[f"{name[0]}_work_N"], reference["WORK"], name)
        close(load["return_N"], reference["RETURN"], name)
    require(len(envelope["cases"]) == 42, "Physical catalogue size changed")
    require(load["reverse_work"] == "negative of WORK"
            and load["zero_N"] == 0 and load["F_x_positive"] == "rod compression",
            "Envelope sign convention changed")


def verify(check_git):
    manifest = read_json(PACKAGE / "input_manifest.json")
    outputs = read_json(PACKAGE / "output_manifest.json")
    registry = read_json(PACKAGE / "design_basis_registry.json")
    require(manifest["task_id"] == outputs["task_id"] == registry["task_id"]
            == PACKAGE.name, "Task identity mismatch")
    require(registry["revision"] == outputs["design_basis_revision"] == 1,
            "Unexpected design basis revision")
    require(manifest["status"] == "AUDITED_DESIGN_BASIS"
            and registry["physical_state_count"] == 42
            and registry["physical_input_status"] == "BLOCKED_INPUTS"
            and registry["physical_sections_4_5_6"] == "NOT_RUN",
            "Invalid scope or physical status")
    require(len(manifest["reference_pdfs"]) == 4, "Four source PDFs required")
    tracked = manifest["tracked_inputs"] + manifest["reference_pdfs"]
    for record in tracked + outputs["outputs"]:
        verify_file(record, check_git)
    if check_git:
        verify_file({
            "path": (PACKAGE / "output_manifest.json").relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256((PACKAGE / "output_manifest.json").read_bytes()).hexdigest(),
        }, True)

    source_ids = set(manifest["source_catalog"])
    extracts, entries = registry["reference_extracts"], registry["parameters"]
    all_ids = set(extracts) | set(entries)
    require(source_ids >= {"BP500", "ARS", "E55", "TH200", "GOST", "ISO2021"},
            "Source coverage incomplete")
    for key, record in extracts.items():
        source = record["source"]
        require(record["status"] == "RAW" and record["value"] is not None
                and record["as_printed"] and source["id"] in source_ids
                and source["locator"], f"Invalid print extract: {key}")
    for key, record in entries.items():
        require(record["revision"] == registry["revision"] and record["unit"],
                f"Missing units or revision: {key}")
        dependencies = set(record["depends_on"])
        require(dependencies <= all_ids and key not in dependencies,
                f"Invalid trace links: {key}")
        sources = record.get("source", [])
        require((dependencies or sources or record["status"] == "UNKNOWN")
                and all(s["id"] in source_ids and s["locator"] for s in sources),
                f"Missing source: {key}")
        if record["status"] == "UNKNOWN":
            require(record["value"] is None and record["reason"]
                    and record["readiness"] == "BLOCKED_INPUTS",
                    f"Unsupported physical value: {key}")
        else:
            require(record["status"] in {"ASSUMED", "CALCULATED_ASSUMED"}
                    and record["value"] is not None and record["readiness"] == "READY"
                    and record["uncertainty_reason"],
                    f"Unexpected maturity or unsupported value: {key}")
            require(all(entries[dep]["status"] != "UNKNOWN"
                        for dep in dependencies & entries.keys()),
                    f"Unresolved dependency promoted to READY: {key}")
    for role, handoff in registry["handoff"].items():
        for field, status in (("ready", "READY"), ("blocked_inputs", "BLOCKED_INPUTS"),
                              ("requires_R4", "BLOCKED_INPUTS")):
            require(all(entries[key]["readiness"] == status
                        for key in handoff.get(field, [])), f"Invalid {role} {field}")
    verify_calculations(entries, extracts)
    print(f"PASS REV_DESIGN_BASIS r1: {len(tracked)} pinned inputs, "
          f"{len(extracts)} reference entries, {len(entries)} basis entries, "
          f"{len(outputs['outputs'])} hashed outputs. Physical states BLOCKED_INPUTS.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    args = parser.parse_args()
    try:
        verify(args.check_git)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
