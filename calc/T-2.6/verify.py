"""Reproduce the round-2 files and run the unmodified project gates."""

from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCTS = ("calc/T-2.6/results.json", "design/params.t26_base.yaml", "design/params.t26a.yaml",
            "metrics.json", "calc/T-2.6/inventory.csv")
GATES = (("design/params.t26_base.yaml", "gates.t26.json"),
         ("design/params.t26a.yaml", "calc/T-2.6/gates.t26a.json"))
CRITERIA = "ops/criteria/design_criteria.yaml"
TEST_EXPRESSION = "(test_cycle or test_dose or test_pressure_bands or test_continues_across_group) and not w02"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def python(*args, check=True):
    cli = [sys.executable, "-B", *args]
    completed = subprocess.run(cli, cwd=ROOT, check=check)
    return subprocess.list2cmdline(cli), completed.returncode


def gate_check(params, output, expected):
    command, exit_code = python("ops/gates/calc_gates.py", "--params", params, "--criteria", CRITERIA,
                                "--out", output, check=False)
    document = read_json(output)
    summary = {}
    for row in document["gates"]:
        summary[row["id"]] = {key: row[key] for key in ("status", "value", "unit")}
        summary[row["id"]]["failed_checks"] = [key for key, passed in row["details"]["checks"].items() if not passed]
        assert row["status"] == expected[row["id"]]["status"]
        assert abs(row["value"] - expected[row["id"]]["value"]) < 1e-9
    assert document["criteria_version"] == 4
    assert summary["G-PFACE"]["status"] == summary["G-DOSE"]["status"] == "PASS"
    assert exit_code == int(document["overall"] == "FAIL")
    return dict(command=command, exit_code=exit_code, status=document["overall"], gates=summary)


def test_calculations(result, gate_outputs):
    selected = result["variants"][result["selected"]]
    assert result["base"]["selection_checks"]["conservative_time_energy_rms"]
    assert result["status"] == "STOP_CYCLE" and selected["reference_operating_point_qualifies"]
    assert all(not row["selection_pass"] for row in result["variants"].values())
    assert result["scheme_A"]["nominal_added_main_stroke_mm"] == 75
    assert result["scheme_A"]["shoe_300_bar_N"] <= 163000
    assert all(row["selection_checks"]["conservative_time_energy_rms"]
               for row in (selected, *result["selected_sensitivity"].values()))
    assert selected["prefill"]["atmospheric_saturation_screen_pass"]
    assert selected["prefill"]["initial_oil_margin_L"] > 0
    for key in ("base", "A"):
        scenario = result["base"] if key == "base" else selected
        phases = next(row["details"]["phases"] for row in gate_outputs[key]["gates"] if row["id"] == "G-CYCLE")
        phases = [p for p in phases if p["actuator"] != "accumulator"]
        assert all(p["command_start_s"] + 1e-9 >= q["end_s"] for q, p in zip(phases, phases[1:]))
        assert all(p["valve_wait_s"] == .1 for p in phases if p["actuator"] != "none" and not p["continues"])
        assert any(p.get("press") and abs(p["pump_rate_L_min"] - p["pump_limit_L_min"]) < 1e-8 for p in phases)
        shaft = scenario["reference"]
        assert abs(shaft["rms_kW"] ** 2 * scenario["reference_cycle_s"] - shaft["integral_P2_kW2_s"]) < 1e-8
        for balance in scenario["accumulators"].values():
            assert abs(balance["volume_balance_L"]) < 1e-5
            assert abs(balance["gas_balance_kJ"]) < .005


def main():
    protected_paths = ("DECISIONS.md", "ops/gates/calc_gates.py", CRITERIA, "design/params.t22d.yaml",
                       "design/hydraulics/T-1.6_circuit.yaml", "design/hydraulics/T-1.6_interlocks.yaml")
    protected = {path: digest(path) for path in protected_paths}
    command, _ = python("calc/T-2.6/run.py")
    before = {path: digest(path) for path in PRODUCTS}
    python("calc/T-2.6/run.py")
    assert before == {path: digest(path) for path in PRODUCTS}
    result = read_json(PRODUCTS[0])
    expected = (result["base"], result["variants"][result["selected"]])
    gate_checks = {output: gate_check(params, output, row["gates"])
                   for (params, output), row in zip(GATES, expected, strict=True)}
    test_calculations(result, dict(zip(("base", "A"), (read_json(output) for _, output in GATES), strict=True)))
    with TemporaryDirectory(prefix="gate-tests-", dir=HERE) as temporary:
        path = Path(temporary).resolve()
        assert path.parent == HERE
        test_command, code = python("-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/ops/test_calc_gates.py",
                                     "-k", TEST_EXPRESSION, "--basetemp", str(path / "pytest"))
    assert not path.exists()
    for path in HERE.rglob("*.py"):
        compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
    package_bytes = sum(path.stat().st_size for path in HERE.rglob("*") if path.is_file())
    assert package_bytes <= 5_000_000
    assert not list(HERE.rglob("__pycache__"))
    assert protected == {path: digest(path) for path in protected_paths}
    report = (ROOT / "report.md").read_bytes().decode("utf-8")
    assert report.startswith("**STOP") and "неблагоприят" in report and "схем" in report and "\ufffd" not in report
    data = dict(task="T-2.6", round=2, status="CHECKS_COMPLETED", engineering_status=result["status"],
                python_version=platform.python_version(), gate_checks=gate_checks,
                reproducibility=dict(command=command, runs=2, byte_identical=True, sha256=before),
                tests=dict(command=test_command, exit_code=code,
                           verified=["G-CYCLE timing, shaft energy and RMS conservatism",
                                     "sequential commands and 100 ms gate waits", "pump limit active during press",
                                     "shaft moments and accumulator mass/energy closure", "suction and reservoir screens",
                                     "geometry and service shoe force", "no changes to protected input files during rerun"]),
                package_bytes=package_bytes, utf8_report_read=True, temporary_directories_removed=True,
                output_suffixes_used=False)
    (ROOT / "self_check.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
