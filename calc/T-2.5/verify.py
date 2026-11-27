"""Run the T-2.5 gates and check two complete independent builds."""

from hashlib import sha256
from math import fsum, isclose
import subprocess
import sys

from mass import HERE, ROOT, read_json, read_yaml, write_json


def checksum(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def verify():
    criteria_path = "ops/criteria/design_criteria.yaml"
    gate_path = "ops/gates/calc_gates.py"
    params_path = "calc/T-2.6/params/params.t26a.yaml"
    protected = [criteria_path, "DECISIONS.md", "TASK.md", params_path,
                 "calc/T-2.6/results.json", "calc/T-2.6/inventory.csv", "calc/T-1.6/results.json",
                 "calc/T-2.2i/results.json", "design/hydraulics/T-1.6_circuit.yaml",
                 "design/hydraulics/T-1.6_interlocks.yaml",
                 *(path.relative_to(ROOT).as_posix() for path in sorted((ROOT / "ops/gates").glob("*.py")))]
    protected_before = {path: checksum(path) for path in protected}
    command = [sys.executable, "-X", "utf8", "-B", gate_path, "--params", params_path,
               "--criteria", criteria_path, "--out", str(ROOT / "gates.t25.json")]
    process = subprocess.run(command, cwd=ROOT, check=False)
    gates = read_json("gates.t25.json")
    statuses = {row["id"]: row["status"] for row in gates["gates"]}
    assert statuses == {"G-PFACE": "PASS", "G-DOSE": "PASS", "G-CYCLE": "FAIL"}
    assert process.returncode == 1
    assert gates["criteria_sha256"] == protected_before[criteria_path]

    outputs = ("calc/T-2.5/results.json", "design/hydraulics/station.t25.yaml", "metrics.json", "report.md")
    build = [sys.executable, "-X", "utf8", "-B", str(HERE / "mass.py")]
    subprocess.run(build, cwd=ROOT, check=True)
    first = {path: checksum(path) for path in outputs}
    subprocess.run(build, cwd=ROOT, check=True)
    assert first == {path: checksum(path) for path in outputs}
    assert protected_before == {path: checksum(path) for path in protected}

    result = read_json(outputs[0])
    station = read_yaml(outputs[1])
    metrics = read_json(outputs[2])
    report = (ROOT / outputs[3]).read_text(encoding="utf-8")
    assert "?" not in report and "\ufffd" not in report and "гидростанции" in report
    assert len(report.splitlines()) <= 65
    mass = result["station_mass"]
    rows = station["mass_rows"]
    assert len({row["id"] for row in rows}) == len(rows)
    assert all(row["source"] for row in rows)
    assert isclose(fsum(row["mass_kg"] for row in rows), metrics["station_t25_kg"], abs_tol=1e-9)
    assert isclose(metrics["station_base_kg"] - metrics["station_t25_kg"], metrics["reduction_kg"], abs_tol=1e-9)
    assert all(abs(row["reference_difference_kg"]) <= .01 for row in result["machine_mass"]["A_variants"].values())
    assert all(isclose(new - old, 30, abs_tol=1e-9) for new, old in zip(
        metrics["machine_A_corrected_kg_range"], metrics["machine_A_kg_range"]))
    assert station["status"] == metrics["status"] == "STOP"
    assert station["recommended_execution"] and metrics["reduction_kg"] == metrics["group_reduction_kg"]["A"]
    assert all(isclose(value, -fsum(row["delta_kg"] for row in result["measures"]
                                   if row["group"] == group and row["counted_in_group_subtotal"]
                                   and row["delta_kg"] is not None))
               for group, value in metrics["group_reduction_kg"].items())

    heat = result["heat"]
    assert heat["cooling_dirty_kW"] >= heat["proportional_sensitivity_required_kW"]
    assert heat["installed_kW"] <= heat["installed_limit_kW"]
    assert not result["cooling_selection"]["thermal_mass_power_candidates"]
    assert all(not row["cycle_power_pass"] for row in heat["motor_trials"].values())
    assert all(row["nominal"]["pullout_to_peak_ratio"] > 1 and row["adverse"]["pullout_to_peak_ratio"] > 1
               for row in heat["motor_trials"].values())
    assert tuple(round(metrics[key], 3) for key in ("cycle_nominal_s", "cycle_adverse_s", "rms_kW")) == (
        5.904, 6.193, 29.987)
    tank = result["tank"]
    assert tank["sizing_screen_minimum_initial_L"] >= tank["nominal_oil_L"] and not tank["reduced_oil_approved"]
    assert all(case["stop_trigger_samples"] > 1000 for case in tank["stop"]["cases"].values())
    tf = station["reservoirs"]["TF"]
    assert tf["gross_L"] == 80 and tf["initial_oil_L"] == 55
    assert isclose(tf["nominal_gauge_bar"], .6) and isclose(tf["regulation_half_band_bar"], .05)
    assert isclose(tf["min_gauge_bar"], .55) and isclose(tf["max_gauge_bar"], .65)
    assert all(source["url"] for source in result["sources"].values())

    result_files = list(HERE.rglob("*"))
    assert all(path == HERE / "cycle" for path in result_files if path.is_dir())
    bytes_used = sum(path.stat().st_size for path in result_files if path.is_file())
    assert 0 < bytes_used <= 5_000_000
    write_json("self_check.json", dict(
        task="T-2.5", round=2, status=metrics["status"], python=sys.version.split()[0],
        gates=dict(command=command, exit_code=process.returncode, overall=gates["overall"], statuses=statuses,
                   required_gate_outcome="PASS", G_CYCLE_role="advisory_D-GK-13_D-OP-16"),
        checks=dict(
            build_command=build, build_runs=2, two_runs_identical_sha256=first, protected_inputs_unchanged=True,
            installed_rows_reconciled="PASS", same_GA_correction_in_station_and_machine="PASS",
            mass_acceptance="FAIL_BELOW_170_KG", group_totals_without_double_counting="PASS",
            reference_nominal_and_adverse_replay="PASS", T26_TF_setpoint_and_fill="PASS",
            motor_catalogue_cases_replayed="PASS", proposed_motor_substitutions="GROUP_B_LIMIT_EXCEEDED",
            inherited_cooling_at_40_air_55_oil="PASS", replacement_coolers="NONE_QUALIFIED",
            installed_power_limit="PASS", tank_trajectory_and_minimum_screen="RUN",
            physical_stop_deaeration_suction_qualification="OPEN",
            tank_support_and_envelope="UNVERIFIED", fixture_CAD="NOT_RUN_NONDIMENSIONED_BASE",
            report_utf8_and_no_question_marks="PASS", report_lines=len(report.splitlines()),
            calculation_tree_bytes=bytes_used, calculation_tree_has_no_temp_directories=True)))


if __name__ == "__main__":
    verify()
