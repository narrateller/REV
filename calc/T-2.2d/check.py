"""Rebuild twice and check load, reference replay, gate output, and stop disposition."""

from hashlib import sha256
from math import exp, fsum
from subprocess import run
import sys

import yaml

from load import accepted_load
from run import HERE, ROOT, read_json, write_json


GATES = {"G-PFACE", "G-DOSE", "G-CYCLE"}
BUILD_OUTPUTS = ("calc/T-2.2d/results.json", "design/params.t22d.yaml", "design/prepress_lock.t22d.yaml",
                 "metrics.json", "calc/T-2.2d/fea/status.json")


def invoke(*arguments):
    return run([sys.executable, "-B", *map(str, arguments)], cwd=ROOT, check=True)


def artifact(relative_path):
    path = ROOT / relative_path
    fallback = path.with_suffix(path.suffix + ".r2")
    if fallback.is_file() and (not path.is_file() or fallback.stat().st_mtime_ns > path.stat().st_mtime_ns):
        return fallback
    return path


def snapshot():
    return {name: (artifact(name).relative_to(ROOT).as_posix(), sha256(artifact(name).read_bytes()).hexdigest())
            for name in BUILD_OUTPUTS}


def load_checks(result):
    accepted = accepted_load()
    subdivisions = 4096
    errors = []
    balances_N = []
    for candidate in result["candidates"]:
        for case, load in candidate["load"].items():
            assert len(load["grid"]) == 9
            assert load["peak"] == max(load["grid"], key=lambda row: row["shoe_force_N"])
            for row in load["grid"]:
                x0_mm, x1_mm = row["shoe_contact_x_mm"]
                dx_mm = (x1_mm - x0_mm) / subdivisions
                integral_N = accepted["section_mm"][0] * dx_mm * fsum(
                    row["radial_start_MPa"] * exp(-row["decay_per_mm"] * dx_mm * (index + .5))
                    for index in range(subdivisions))
                errors.append(abs(integral_N / row["shoe_force_N"] - 1))
                balances_N.append(row["balance_abs_error_N"])
                assert abs(row["shoe_force_N"] + row["roof_force_N"]
                           - next(record["shoe_force_N"] for record in accepted["cases"][case]["grid"]
                                  if (record["K"], record["mu"]) == (row["K"], row["mu"]))) < 1e-6
    assert max(errors) < 1e-8 and max(balances_N) < 1e-6
    dose_limit_kg = min(case["conservative_dose"]["dose_limit_kg"] for case in accepted["cases"].values())
    assert result["dose_setpoint_limit_kg"] * (1 + accepted["dose_upper_tolerance_fraction"]) <= dose_limit_kg
    return dict(status="PASS", grid_rows=len(errors), quadrature_cells=subdivisions,
                max_relative_quadrature_error=max(errors), max_balance_error_N=max(balances_N))


def check_layout(result):
    selected_mm = result["selected_roof_mm"]
    assert selected_mm == max(row["roof_mm"] for row in result["candidates"] if row["passes_selection"])
    base = result["baseline"]["layout"]
    for row in result["candidates"]:
        x_mm = row["roof_mm"]
        layout = row["layout"]
        for key in ("gate_face_x_mm", "punch_face_nominal_eject_end_x_mm", "punch_face_maximum_eject_end_x_mm",
                    "main_installed_stroke_mm", "punch_face_clear_for_gate_close_x_mm"):
            assert layout[key] - base[key] == x_mm
        assert layout["punch_face_nominal_eject_end_x_mm"] - layout["gate_face_x_mm"] == layout["overtravel_nominal_mm"]
        for profile in ("realistic", "pessimistic"):
            reference = row["reference"][profile]
            assert reference["feasible"] and reference["convergence_pass"]
            assert abs(reference["main_travel_mm"] - layout["punch_face_nominal_eject_end_x_mm"]) < 1e-7
    manual = result["hand"]
    assert manual["candidates_within_60_kg"] > 0
    assert manual["minimum_height"]["height_300_mm"] > .5 and manual["selected"] is None
    assert result["status"] == "STOP_HAND_SCREEN"
    for station in manual["best"]["stations"].values():
        assert station["gate_swept_clearance_mm"] >= 3 - 1e-9
    return dict(status="PASS", selected_roof_mm=selected_mm, manual_stop_confirmed=True,
                scope="Exact replay of imported T-2.1 baseline and consistency of the candidate coordinates")


def main():
    before = snapshot()
    invoke("calc/T-2.2d/run.py")
    after = snapshot()
    assert before == after, (before, after)
    for name in ("design/params.t22d.yaml", "design/prepress_lock.t22d.yaml", "calc/T-2.2d/sources.yaml"):
        assert isinstance(yaml.safe_load(artifact(name).read_text(encoding="utf-8")), dict)
    result = read_json(after["calc/T-2.2d/results.json"][0])
    loads = load_checks(result)
    layout = check_layout(result)

    gate_path = ROOT / "gates.t22d.json"
    params_name = after["design/params.t22d.yaml"][0]
    gate_command = ("ops/gates/calc_gates.py", "--params", params_name,
                    "--criteria", "ops/criteria/design_criteria.yaml", "--out")
    try:
        with gate_path.open("ab"):
            pass
    except PermissionError:
        gate_path = gate_path.with_suffix(gate_path.suffix + ".r2")
    invoke(*gate_command, gate_path)
    gates_bytes = gate_path.read_bytes()
    invoke(*gate_command, gate_path)
    assert gates_bytes == gate_path.read_bytes()
    gates = read_json(gate_path.relative_to(ROOT))
    gate_summary = {row["id"]: {key: row[key] for key in ("status", "value", "unit")} for row in gates["gates"]}
    assert set(gate_summary) == GATES and gates["overall"] == "PASS"
    assert all(check["status"] == "PASS" for check in gate_summary.values())
    assert gate_summary["G-CYCLE"]["value"] <= result["gate_limit_s"]

    files = sorted(path for path in HERE.rglob("*") if path.is_file())
    total_bytes = sum(len(path.read_bytes()) for path in files)
    assert total_bytes <= 5_000_000 and not list(HERE.rglob("__pycache__"))
    assert all(path.stat().st_size <= 1_000_000 for path in files if path.parent.name == "fea")
    for name in ("report.md", "metrics.json", "gates.t22d.json", "design/prepress_lock.t22d.yaml"):
        assert artifact(name).read_text(encoding="utf-8")
    denials = {name: info[0] for name, info in after.items() if name != info[0]}
    for name in ("report.md", "gates.t22d.json"):
        actual_name = artifact(name).relative_to(ROOT).as_posix()
        if actual_name != name:
            denials[name] = actual_name
    # Determine the path up front to include any fallback in its own record.
    self_path = ROOT / "self_check.json"
    try:
        with self_path.open("ab"):
            pass
    except PermissionError:
        self_path = self_path.with_suffix(self_path.suffix + ".r2")
        denials["self_check.json"] = self_path.name
    write_json(self_path, dict(task="T-2.2d", round=2, status=result["status"], python_version=sys.version.split()[0],
                               deterministic_replay=dict(status="PASS", runs=2, byte_identical=True,
                                                         command=["REV_PYTHON", "-B", "calc/T-2.2d/run.py"], outputs=after),
                               shoe_load=loads, cycle_geometry=layout,
                               gates=dict(status="PASS", runs=2, byte_identical=True, criteria_version=gates["criteria_version"],
                                          command=["REV_PYTHON", "-B", *gate_command, str(gate_path)], values=gate_summary),
                               contact_FEA=dict(status="SKIPPED_HAND_STOP", meshes_run=0, replay_tolerance=1e-6),
                               VDI2230=dict(status="NOT_APPLICABLE_TO_SCREEN", threaded_load_path_count=0),
                               calc_size=dict(status="PASS", total_bytes=total_bytes, limit_bytes=5_000_000),
                               artifact_readability="PASS", temp_directories_created=[], write_denials=denials))


if __name__ == "__main__":
    main()
