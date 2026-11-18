#!/usr/bin/env python3
"""Replay the design envelope and verify the per-state R3 result and status register."""

import argparse
from collections import Counter
from hashlib import sha256
from itertools import groupby
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CASE = Path("cae/cases/T-R3-42-STATES-01")
ENVELOPE = Path("cae/cases/design_boundary_phase_load_envelope")
SCREENING = Path("cae/cases/T-R3-CAE-456-01")
MANIFEST = CASE / "envelope_assumed_manifest.json"
REPORT = CASE / "envelope_assumed.json"
REGISTER = Path("params/r3_42_states_envelope_status.json")
SOURCE = "ENVELOPE_ASSUMED"
CALCULATED = "CALCULATED_ASSUMED"


def read_json(path):
    return json.loads((ROOT / path).read_bytes())


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def unknown(reason):
    return {"status": "UNKNOWN", "value": None, "reason": reason}


def support_extrema(held):
    guide = max(held, key=lambda row: row["section_4"]["guide_resultant_N"])
    axial = max(held, key=lambda row: abs(row["F_x_N"]))
    support = guide["section_4"]
    return {
        "status": CALCULATED,
        "guide_resultant_N": support["guide_resultant_N"],
        "guide_row": guide["row"],
        "guide_on_moving_N": {end: support["moving"][end][1] for end in ("G-", "G+")},
        "axial_row": axial["row"],
        "axial_path": axial["axial_path"],
        "axial_on_moving_N": axial["section_4"]["moving"][axial["axial_path"]][1],
    }


def strength_extrema(held, reference):
    elements = {}
    for element in ("rod", "carrier"):
        key = f"{element}_max_abs_Pa"
        governing = max(held, key=lambda row: row["section_5"][key])
        stress = governing["section_5"][key]
        elements[element] = {
            "row": governing["row"],
            "max_abs_stress_Pa": stress,
            "reference_yield_over_max_abs_stress": reference / stress,
            "exceeds_reference_yield": stress > reference,
        }
    return {"status": CALCULATED, "elements": elements}


def stability_extrema(held):
    compression = [row for row in held if row["section_5"]["N_N"] < 0]
    if not compression:
        return {
            "status": "NOT_APPLICABLE",
            "value": None,
            "reason": "В огибающей этого случая нет сжатия. Сопоставление с нагрузкой Эйлера применимо к сжатию.",
        }

    result = {}
    for element, restraints in compression[0]["section_6"]["modes"].items():
        result[element] = {}
        for restraint in restraints:
            modes = [
                (row["row"], row["section_6"]["modes"][element][restraint])
                for row in compression
            ]
            minimum_row, minimum = min(modes, key=lambda pair: pair[1]["P_cr_N"])
            governing_row, governing = max(modes, key=lambda pair: pair[1]["load_over_P_cr"])
            result[element][restraint] = {
                "minimum_P_cr_row": minimum_row,
                "minimum_P_cr_N": minimum["P_cr_N"],
                "governing_row": governing_row,
                **governing,
            }
    return {"status": CALCULATED, "modes": result}


def physical_blockers(upstream):
    return {
        "input_status": "BLOCKED_INPUTS",
        "execution": "NOT_RUN",
        **upstream,
        "fatigue": unknown(
            "Требуются история диапазонов и средних напряжений, число циклов, "
            "данные S–N материала и соединений и критерий повреждения."
        ),
        "dynamics": unknown(
            "Требуются масса и инерция, жёсткости и демпфирование опор и соединений, "
            "истории нагрузок и движения по времени."
        ),
    }


def build(source_sha):
    upstream = read_json(SCREENING / "summary.json")
    material = read_json(ENVELOPE / "assumptions.json")["comparison_material"]
    samples = SCREENING / "samples.jsonl"
    with (ROOT / samples).open(encoding="utf-8") as stream:
        rows = map(json.loads, stream)
        groups = [(case_id, list(group)) for case_id, group in groupby(rows, lambda row: row["case_id"])]
    if len(groups) != 42 or [case_id for case_id, _ in groups] != list(upstream["cases"]):
        raise ValueError("Expected one group for each of the 42 audited cases")

    cases = {}
    for case_id, group in groups:
        original = upstream["cases"][case_id]
        held = [row for row in group if row["status"] == CALCULATED and row["sample"] != "ZERO"]
        counts = Counter(row["status"] for row in group)
        row_range = [group[0]["row"], group[-1]["row"]]
        if not held or counts != original["counts"] or row_range != original["row_range_inclusive"]:
            raise ValueError(f"Case coverage or row references differ: {case_id}")
        cases[case_id] = {
            "variant": original["variant"],
            "phase": original["phase"],
            "r4_interface_ids": original["r4_interface_ids"],
            "status": CALCULATED,
            "sample_rows_inclusive": row_range,
            "sample_counts": dict(counts),
            "section_4_supports": support_extrema(held),
            "section_5_strength": strength_extrema(held, material["reference_yield_Pa"]),
            "section_6_stability": stability_extrema(held),
            "physical": physical_blockers(original["physical"]),
        }

    status = {
        "task_id": "T-R3-42-STATES-01",
        "source": SOURCE,
        "source_sha": source_sha,
        "input_lifecycle": "ASSUMED",
        "scope": upstream["scope"],
        "case_count": len(cases),
        "supports_calculated_assumed": len(cases),
        "strength_calculated_assumed": len(cases),
        "stability_calculated_assumed": sum(
            case["section_6_stability"]["status"] == CALCULATED for case in cases.values()
        ),
        "stability_not_applicable_without_compression": [
            case_id for case_id, case in cases.items()
            if case["section_6_stability"]["status"] == "NOT_APPLICABLE"
        ],
        "sample_counts": upstream["counts"],
        "physical": {
            "status": "BLOCKED_INPUTS",
            "execution": "NOT_RUN",
            "case_count": len(cases),
            "fatigue": "BLOCKED_INPUTS",
            "dynamics": "BLOCKED_INPUTS",
        },
        "report": REPORT.as_posix(),
        "input_manifest": MANIFEST.as_posix(),
    }
    report = {
        **status,
        "frame": {"X": "к выходу", "Y": "к боковому приводу V2", "Z": "вверх"},
        "sign": {"F_x_positive": "сжатие штока", "N_N": "-F_x_N"},
        "units": {"length": "m", "force": "N", "moment": "N m", "stress": "Pa", "ratio": "1"},
        "assumptions": (ENVELOPE / "assumptions.json").as_posix(),
        "boundary_conditions": (ENVELOPE / "README.md").as_posix(),
        "load_cases": (ENVELOPE / "envelope.json").as_posix(),
        "samples": samples.as_posix(),
        "row_reference": "line_number_starting_at_1",
        "comparison_material": material,
        "upstream_checks": upstream["checks"],
        "cases": cases,
    }
    return {REPORT: encoded(report), REGISTER: encoded(status)}


def verify_inputs(manifest, check_git):
    if check_git:
        task = manifest["task_at_source"]
        definition = subprocess.check_output(
            ["git", "show", f"{manifest['source_sha']}:{task['path']}"], cwd=ROOT
        )
        if sha256(definition).hexdigest() != task["sha256"]:
            raise ValueError("Task definition at source differs")
    for name, expected in manifest["inputs_sha256"].items():
        path = ROOT / name
        data = path.read_bytes()
        if check_git:
            pinned = subprocess.check_output(
                ["git", "show", f"{manifest['source_sha']}:{name}"], cwd=ROOT
            )
            if data != pinned:
                raise ValueError(f"Input differs from source commit: {name}")
        if sha256(data).hexdigest() != expected:
            raise ValueError(f"Pinned input differs: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--write", action="store_true", help="Regenerate the report and status register")
    args = parser.parse_args()
    try:
        manifest = read_json(MANIFEST)
        verify_inputs(manifest, args.check_git)
        replay = [sys.executable, str(ROOT / SCREENING / "verify_output.py")]
        if args.check_git:
            replay.append("--check-git")
        subprocess.run(replay, cwd=ROOT, check=True)
        outputs = build(manifest["source_sha"])
        for name, data in outputs.items():
            path = ROOT / name
            if args.write:
                path.write_bytes(data)
            elif path.read_bytes() != data or sha256(data).hexdigest() != manifest["outputs_sha256"][name.as_posix()]:
                raise ValueError(f"Report replay or SHA256 differs: {name}")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: T-R3-42-STATES-01, 42 ENVELOPE_ASSUMED cases and scoped status register")


if __name__ == "__main__":
    main()
