#!/usr/bin/env python3
"""Replay the approved envelope and verify this task's numerical evidence."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
REPLAY = PACKAGE.parent / "T-R3-42-STATES-ENVELOPE-01"
ENVELOPE = PACKAGE.parent / "design_boundary_phase_load_envelope"
PHYSICAL = PACKAGE.parent / "T-R3-42-STATES-01"
MANIFEST = PACKAGE / "manifest.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def read_inputs(manifest, check_git):
    source = manifest["source_main_sha"]
    if check_git:
        task = manifest["task_definition_at_claim"]
        pinned = subprocess.check_output(["git", "show", f"{source}:{task['path']}"], cwd=ROOT)
        require(sha256(pinned).hexdigest() == task["sha256"], "Claimed task definition differs")
    for name, digest in manifest["inputs_sha256"].items():
        data = (ROOT / name).read_bytes()
        require(sha256(data).hexdigest() == digest, f"Input SHA256 differs: {name}")
        if check_git:
            pinned = subprocess.check_output(["git", "show", f"{source}:{name}"], cwd=ROOT)
            require(data == pinned, f"Input differs from {source}: {name}")

    envelope = json.loads((ENVELOPE / "envelope.json").read_bytes())
    assumptions = json.loads((ENVELOPE / "assumptions.json").read_bytes())
    audit = json.loads((PHYSICAL / "case_audit.json").read_bytes())
    reconciliation = json.loads((PHYSICAL / "r4_reconciliation.json").read_bytes())
    physical = {case["case_id"]: case for case in audit["cases"]}
    r4 = reconciliation["cases"]
    require(envelope["scope"] == "ASSUMED_STATIC_SCREENING"
            and assumptions["lifecycle"] == "ASSUMED", "Unexpected input scope")
    require(len(physical) == len(audit["cases"]) == 42
            and envelope["cases"].keys() == physical.keys() == r4.keys(), "Case coverage differs")
    for case_id, case in envelope["cases"].items():
        source_case, r4_case = physical[case_id], r4[case_id]
        require(case["envelope_input_status"] == "READY_ASSUMED"
                and case["r4_interface_ids"] == source_case["interface_ids"]
                and case["physical_input_status"] == source_case["status"] == r4_case["status"]
                == "BLOCKED_INPUTS"
                and case["physical_execution"] == source_case["actual_result"]["execution"]
                == r4_case["execution"] == "NOT_RUN", f"Input audit differs: {case_id}")
        require(source_case["phase_load"]["value"] is None
                and source_case["boundary_conditions"]["value"] is None,
                f"Unknown physical inputs replaced: {case_id}")
    return envelope, r4


def check_rows(rows, envelope):
    counts = Counter()
    by_span = defaultdict(list)
    by_pose = defaultdict(dict)
    max_force = max_moment = 0.0

    for row in rows:
        case = envelope["cases"][row["case_id"]]
        support, stress, stability = (row[f"section_{n}"] for n in (4, 5, 6))
        force = row["F_x_N"]
        if row["sample"] == "ZERO":
            require(force == support["axial_reaction_N"] == stress["rod_max_abs_Pa"]
                    == stress["carrier_max_abs_Pa"] == 0
                    and support["guide_reaction_N"] == [0, 0, 0]
                    and support["axial_dof"] == "FREE"
                    and stability["reason"] == "ZERO_AXIAL_LOAD", f"ZERO case: {row['row']}")
            counts["ZERO"] += 1
            continue
        if row["status"] == "NO_STATIC_EQUILIBRIUM":
            require(force != 0 and row["axial_path"] == "RELEASED"
                    and row["axial_residual_N"] == force and row["reason"]
                    and support is stress is stability is None, f"Released path: {row['row']}")
            counts["released"] += 1
            continue

        counts["held"] += 1
        for body in ("moving_balance", "frame_balance"):
            max_force = max(max_force, *map(abs, support[body]["force_N"]))
            max_moment = max(max_moment, *map(abs, support[body]["moment_Nm"]))
        key = tuple(row[x] for x in ("case_id", "sample", "q_m", "axial_path",
                                     "actuator_y_m", "reaction_y_m", "reaction_z_m"))
        by_span[key].append((row["span_m"], support["guide_resultant_N"]))
        if row["actuator_y_m"] == row["reaction_y_m"] and row["reaction_z_m"] == 0:
            require(support["guide_resultant_N"] == support["M_y_Nm"] == support["M_z_Nm"] == 0
                    and len({corner["sigma_x_Pa"] for corner in stress["carrier_corners"]}) == 1,
                    f"Centered load: {row['row']}")
            counts["centered"] += 1
        if force < 0:
            require(stability == {"status": "NOT_APPLICABLE", "reason": "AXIAL_TENSION"},
                    f"Tension case: {row['row']}")
            counts["tension"] += 1
            continue
        variant = case["variant"]
        dimensions = envelope["variants"][variant]["reference_dimensions_m"]
        for mode, boundaries in stability["modes"].items():
            pin, free = (boundaries[bc]["P_cr_N"] for bc in ("PIN_PIN", "FIXED_FREE"))
            require(isclose(pin, 4 * free, rel_tol=1e-12), f"Euler K relation: {row['row']}")
            counts["Euler_K_pairs"] += 1
            base = dimensions["rod_diameter" if mode == "rod" else "chamber_length"]
            by_pose[variant, mode, base][row["q_m"]] = pin

    require(max_force < 1e-8 and max_moment < 1e-8, "Free-body residual above tolerance")
    for key, pair in by_span.items():
        (short_span, short_reaction), (long_span, long_reaction) = sorted(pair)
        require(isclose(long_span, 2 * short_span, rel_tol=1e-12)
                and isclose(short_reaction, 2 * long_reaction, rel_tol=1e-12),
                f"Guide span relation: {key}")
        counts["guide_span_pairs"] += 1
    for (_, _, base), poses in by_pose.items():
        origin = min(poses)
        for q, critical in sorted(poses.items())[1:]:
            expected = poses[origin] * ((base + origin) / (base + q)) ** 2
            require(isclose(critical, expected, rel_tol=1e-12), f"Euler pose relation: {q}")
            counts["Euler_pose_pairs"] += 1
    return {"status": "PASS", "counts": dict(counts), "max_force_residual_N": max_force,
            "max_moment_residual_Nm": max_moment, "balance_abs_tol_SI": 1e-8,
            "sensitivity_rel_tol": 1e-12,
            "mesh_time_step_convergence": {"status": "NOT_APPLICABLE",
                                           "reason": "Algebraic static model"}}


def unknown(reason):
    return {"status": "UNKNOWN", "value": None, "reason": reason}


def make_outputs(envelope, reconciled):
    # The preceding upstream replay has checked these bytes against a fresh solve.
    samples = (REPLAY / "samples.jsonl").read_bytes()
    summary = json.loads((REPLAY / "summary.json").read_bytes())
    summary["checks"] = check_rows([json.loads(line) for line in samples.splitlines()], envelope)
    for case_id, item in summary["cases"].items():
        case, r4 = envelope["cases"][case_id], reconciled[case_id]
        item["r4_interface_ids"] = case["r4_interface_ids"]
        item["physical"] = {
            "phase_load": unknown(r4["phase_load_blocker"]),
            "boundary_conditions": unknown(". ".join(r4["required_inputs"])),
            "section_4": unknown("Требуются фактические силы, координаты, жёсткости и активные контакты опор."),
            "section_5": unknown("Требуются фактические нагрузки, сечения, материалы и свойства соединений."),
            "section_6": unknown("Требуются фактические усилия, свободные длины, жёсткости и закрепления."),
        }
    return {"samples.jsonl": samples, "summary.json": encoded(summary)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--write", action="store_true", help="Save replayed task outputs")
    args = parser.parse_args()
    try:
        manifest = json.loads(MANIFEST.read_bytes())
        envelope, reconciliation = read_inputs(manifest, args.check_git)
        command = [sys.executable, str(REPLAY / "verify_output.py")]
        if args.check_git:
            command.append("--check-git")
        subprocess.run(command, cwd=ROOT, check=True)
        outputs = make_outputs(envelope, reconciliation)
        digests = {name: sha256(data).hexdigest() for name, data in outputs.items()}
        for name in ("README.md", "verify_output.py"):
            digests[name] = sha256((PACKAGE / name).read_bytes()).hexdigest()
        if args.write:
            for name, data in outputs.items():
                (PACKAGE / name).write_bytes(data)
            manifest["outputs_sha256"] = digests
            MANIFEST.write_bytes(encoded(manifest))
        else:
            require(digests == manifest["outputs_sha256"], "Package output hashes differ")
            for name, data in outputs.items():
                require((PACKAGE / name).read_bytes() == data, f"Replay differs: {name}")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: T-R3-CAE-456-01, 42 cases, balance and sensitivity checks, physical UNKNOWNs")


if __name__ == "__main__":
    main()
