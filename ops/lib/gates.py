import json
import re
import shutil
import sys

from ops.lib.config import EFFORT_RANK, RunnerError, in_scope
from ops.lib.io import read_json, write_json
from ops.lib.process import run_logged
from ops.lib.workspace import contained_path


GEOM_GATES = {"G-ENV", "G-MASS", "G-COLL", "G-FEED", "G-CLEAR"}
CALC_GATES = {"G-PFACE", "G-DOSE", "G-CYCLE"}
FAILURES = {"FAIL", "ERROR"}
STATUSES = {"PASS", "WARN", "NOT_AVAILABLE", *FAILURES}


def entry(gate, status, reason, **details):
    return {
        "id": gate, "status": status, "value": None, "threshold": None, "unit": "",
        "criteria_ids": [], "details": {"reason": reason, **details},
    }


def overall(rows):
    statuses = {row["status"] for row in rows}
    if statuses & FAILURES:
        return "FAIL"
    return "WARN" if "WARN" in statuses else "PASS"


def validate_report(report, tool, requested, returncode):
    if (
        not isinstance(report, dict)
        or report.get("schema") != "rev.gate_report/1"
        or report.get("tool") != tool
        or not isinstance(report.get("tool_version"), str)
        or not isinstance(report.get("input"), str)
        or type(report.get("criteria_version")) is not int
        or not re.fullmatch(r"[a-fA-F0-9]{64}", str(report.get("criteria_sha256")))
        or not isinstance(report.get("gates"), list)
    ):
        raise ValueError("invalid rev.gate_report/1 header")
    rows = {}
    for row in report["gates"]:
        if (
            not isinstance(row, dict)
            or not {"id", "status", "value", "threshold", "unit", "criteria_ids", "details"} <= row.keys()
            or not isinstance(row["id"], str)
            or row["id"] in rows
            or row["status"] not in STATUSES
            or not isinstance(row["unit"], str)
            or not isinstance(row["criteria_ids"], list)
            or not all(isinstance(item, str) for item in row["criteria_ids"])
            or not isinstance(row["details"], dict)
        ):
            raise ValueError("invalid or duplicate gate result")
        rows[row["id"]] = row
    if rows.keys() != set(requested):
        raise ValueError(f"expected gates {', '.join(requested)}, got {', '.join(rows)}")
    expected = overall(rows.values())
    expected_exit = 2 if any(row["status"] == "ERROR" for row in rows.values()) else int(expected == "FAIL")
    if report.get("overall") != expected or returncode != expected_exit:
        raise ValueError(f"inconsistent gate overall or exit code (exit {returncode})")
    return rows


def _invoke(root, run_dir, tool, ids, build):
    script = root / "ops" / "gates" / f"{tool}.py"
    if not script.is_file():
        return {gate: entry(gate, "NOT_AVAILABLE", f"{tool}.py is absent") for gate in ids}
    output = run_dir / f"{tool}.gate_report.json"
    try:
        argv, env = build(script.relative_to(root), output)
        result = run_logged(argv, root, env, run_dir / f"{tool}.log", timeout_s=None)
        if not output.is_file():
            raise ValueError(f"exited with code {result.returncode} without a gate report; see {tool}.log")
        return validate_report(read_json(output), tool, ids, result.returncode)
    except (OSError, ValueError, TypeError, RunnerError) as error:
        return {gate: entry(gate, "ERROR", f"{tool}: {error}") for gate in ids}


def run_gates(root, worktree, card_path, card, run_dir, changes, task_intact, meta, scope_meta, env):
    criteria = root / "ops" / "criteria" / "design_criteria.yaml"
    python = env.get("REV_PYTHON") or sys.executable

    def scope(script, output):
        return [
            python, script, "--worktree", worktree, "--task", card_path,
            "--base", "main", "--meta", scope_meta, "--out", output,
        ], env

    scope_result = _invoke(root, run_dir, "scope_gate", ["G-SCOPE"], scope)["G-SCOPE"]
    unauthorized = sorted(path for path in changes if not in_scope(path, card))
    if not task_intact and "TASK.md" not in unauthorized:
        unauthorized.append("TASK.md")
    policy_errors = []
    if EFFORT_RANK.get(meta["reasoning_effort"], 0) < EFFORT_RANK[meta["requested_reasoning_effort"]]:
        policy_errors.append(f"observed reasoning effort {meta['reasoning_effort']!r} is below policy")
    if meta["model"] != meta["requested_model"]:
        policy_errors.append(f"observed model {meta['model']!r} differs from profile")
    if unauthorized or policy_errors:
        scope_result = entry(
            "G-SCOPE", "FAIL", "runner scope validation failed", unauthorized_paths=unauthorized,
            policy_errors=policy_errors, external_gate=scope_result,
        )
    else:
        scope_result["details"]["runner_scope"] = "PASS"
    results = {"G-SCOPE": scope_result}

    inputs = card.gate_inputs

    def actual(name):
        return contained_path(worktree, inputs[name])

    calc_ids = [gate for gate in card.gates if gate in CALC_GATES]
    if calc_ids and "params" in inputs:
        def calc(script, output):
            return [
                python, script, "--params", actual("params"),
                "--criteria", criteria, "--gates", ",".join(calc_ids), "--out", output,
            ], env

        results.update(_invoke(root, run_dir, "calc_gates", calc_ids, calc))
    else:
        results.update((gate, entry(gate, "NOT_AVAILABLE", "card requires gate_inputs.params")) for gate in calc_ids)

    geom_ids = [gate for gate in card.gates if gate in GEOM_GATES]
    if geom_ids and {"model", "roles"} <= inputs.keys():
        def geometry(script, output):
            freecad = env.get("REV_FREECADCMD") or shutil.which("freecadcmd.exe", path=env.get("PATH"))
            if not freecad:
                raise RunnerError("freecadcmd.exe was not found on PATH")
            options = {
                "model": str(actual("model")),
                "roles": str(actual("roles")),
                "criteria": str(criteria), "gates": geom_ids, "out": str(output),
            }
            if "poses" in inputs:
                options["poses"] = str(actual("poses"))
            return [freecad, script], dict(env, REV_GATE_ARGS=json.dumps(options, ensure_ascii=False))

        results.update(_invoke(root, run_dir, "geom_gates", geom_ids, geometry))
    else:
        results.update(
            (gate, entry(gate, "NOT_AVAILABLE", "card requires gate_inputs.model and gate_inputs.roles"))
            for gate in geom_ids
        )

    rows = [
        results[gate] if gate in results else entry(gate, "NOT_AVAILABLE", "no gate CLI is defined")
        for gate in card.gates
    ]
    write_json(run_dir / "gates.json", {"overall": overall(rows), "gates": rows})
    return rows
