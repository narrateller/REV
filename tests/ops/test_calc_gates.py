"""Contract, calibration and threshold tests for the Python gates."""

import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from ops.gates import calc_gates as calc
from ops.gates import scope_gate as scope
from ops.gates.gate_report import InputError, load_yaml, read_criteria


ROOT = Path(__file__).resolve().parents[2]
CRITERIA = ROOT / "ops/criteria/design_criteria.yaml"
EXAMPLE = ROOT / "design/params.example.yaml"
M1 = ROOT / "design/params.m1.yaml"
LEGACY = ROOT / "ops/calibration/w02_04_params.yaml"


@pytest.fixture
def criteria():
    return read_criteria(CRITERIA.read_bytes())["criteria"]


@pytest.fixture
def params():
    return load_yaml(EXAMPLE.read_bytes(), EXAMPLE)


def run_calc(tmp_path, path, *args, cwd=ROOT):
    out = tmp_path / "gate_report.json"
    process = subprocess.run(
        [sys.executable, "-B", str(ROOT / "ops/gates/calc_gates.py"), "--params", str(path),
         "--criteria", str(CRITERIA), "--out", str(out), *args],
        cwd=cwd, check=False, capture_output=True, text=True,
    )
    return process.returncode, json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path, expected, code", [(EXAMPLE, "PASS", 0), (LEGACY, "FAIL", 1)])
def test_calibration_cli(tmp_path, path, expected, code):
    exit_code, report = run_calc(tmp_path, path)
    assert exit_code == code
    assert report["schema"] == "rev.gate_report/1"
    assert report["tool"] == "calc_gates"
    assert report["criteria_version"] == read_criteria(CRITERIA.read_bytes())["version"]
    assert report["criteria_sha256"] == hashlib.sha256(CRITERIA.read_bytes()).hexdigest()
    assert report["overall"] == expected
    assert [row["id"] for row in report["gates"]] == list(calc.GATES)
    assert all(gate["status"] == expected for gate in report["gates"])
    if path == LEGACY:
        face, dose, cycle = (gate["details"] for gate in report["gates"])
        assert face["punch_pressure_MPa"] == pytest.approx(22.7, rel=0.01)
        assert face["chamber_pressure_MPa"] == pytest.approx(1.5e6 / (311 * 231))
        assert not face["checks"]["chamber_section_matches_product"]
        assert not dose["checks"]["stroke_overshoot_limit"]
        assert cycle["total_oil_L"] == pytest.approx(179.0, rel=0.01)
        assert cycle["main_full_stroke_round_trip_oil_L"] == pytest.approx(208.3, rel=0.01)
        assert cycle["cycle_s"] > 30
        assert cycle["failures"] == ["нет фазы прессования"]
    else:
        assert report["gates"][2]["details"]["switch_count"] == 10


def test_m1_cli_from_another_working_directory(tmp_path):
    code, report = run_calc(tmp_path, M1, cwd=tmp_path)
    assert code == 0
    assert [gate["status"] for gate in report["gates"]] == ["PASS", "PASS", "PASS"]
    _, dose, cycle = report["gates"]
    assert dose["threshold"]["min_stroke_mm"] == pytest.approx(210, abs=0.1)
    assert dose["value"] == 230
    assert cycle["value"] == pytest.approx(5.87, abs=0.01)
    assert cycle["details"]["switch_count"] == 9


def test_gate_selection(tmp_path):
    code, report = run_calc(tmp_path, EXAMPLE, "--gates", "G-CYCLE,G-PFACE")
    assert code == 0
    assert [gate["id"] for gate in report["gates"]] == ["G-CYCLE", "G-PFACE"]
    code, report = run_calc(tmp_path, EXAMPLE, "--gates", "G-UNKNOWN")
    assert (code, report["overall"], report["gates"][0]["status"]) == (2, "FAIL", "ERROR")


@pytest.mark.parametrize("key, limit, check", [
    ("p_work_bar", 300, "working_pressure_limit"), ("p_relief_bar", 315, "relief_pressure_limit"),
])
def test_pface_hydraulic_limits(params, criteria, key, limit, check):
    params["main_cylinder"][key] = limit
    assert calc.evaluate_pface(params, criteria)["status"] == "PASS"
    params["main_cylinder"][key] += 0.001
    gate = calc.evaluate_pface(params, criteria)
    assert gate["status"] == "FAIL"
    assert not gate["details"]["checks"][check]


def test_pface_section_tolerance_per_dimension(params, criteria):
    params["chamber"]["section_mm"] = [151, 59]
    assert calc.evaluate_pface(params, criteria)["status"] == "PASS"
    params["chamber"]["section_mm"] = [152, 9000 / 152]  # Equal area, incorrect section.
    assert calc.evaluate_pface(params, criteria)["status"] == "FAIL"


def test_pface_pressure_limits(params, criteria):
    cylinder = params["main_cylinder"]
    cylinder["nominal_force_N"] = 166.7 * 150 * 60
    assert calc.evaluate_pface(params, criteria)["status"] == "PASS"
    cylinder["nominal_force_N"] -= 0.1
    assert not calc.evaluate_pface(params, criteria)["details"]["checks"]["minimum_face_pressure"]


def test_pface_force_limit(params, criteria):
    cylinder = params["main_cylinder"]
    cylinder["nominal_force_N"] = 1.5e6
    params["chamber"]["section_mm"] = [149, 60]
    cylinder["bore_mm"] = math.sqrt(4 * 1.5e6 / (math.pi * 0.1 * cylinder["p_work_bar"] * cylinder["eta"]))
    assert calc.evaluate_pface(params, criteria)["status"] == "PASS"
    cylinder["bore_mm"] -= 0.01
    assert not calc.evaluate_pface(params, criteria)["details"]["checks"]["minimum_force_at_work_pressure"]


def test_pface_relief_pressure_reported_without_face_limit(params, criteria):
    details = calc.evaluate_pface(params, criteria)["details"]
    force_N = details["force_at_p_work_N"] * details["p_relief_bar"] / details["p_work_bar"]
    assert details["force_at_p_relief_N"] == pytest.approx(force_N)
    assert details["chamber_pressure_at_p_relief_MPa"] == pytest.approx(force_N / (150 * 60))
    assert details["punch_pressure_at_p_relief_MPa"] == pytest.approx(force_N / (149.8 * 59.8))


@pytest.mark.parametrize("edge, outside_mm", [("min_stroke_mm", -0.01), ("max_stroke_mm", 0.01)])
def test_dose_stroke_limits(params, criteria, edge, outside_mm):
    threshold = calc.evaluate_dose(params, criteria)["threshold"]
    params["main_cylinder"]["stroke_mm"] = threshold[edge]
    assert calc.evaluate_dose(params, criteria)["status"] == "PASS"
    params["main_cylinder"]["stroke_mm"] += outside_mm
    assert calc.evaluate_dose(params, criteria)["status"] == "FAIL"


def test_dose_approach_and_overtravel_define_checked_stroke(params, criteria):
    chamber = params["chamber"]
    chamber.update(approach_stroke_mm=120, in_die_density_kg_m3=1100)
    gate = calc.evaluate_dose(params, criteria)
    details = gate["details"]
    compressed_mm = 0.83e9 / (1100 * 150 * 60)
    fill_mm = 0.83e9 / (420 * 150 * 60)
    minimum_mm = 120 + fill_mm + chamber["ejection_overtravel_mm"]
    assert details["compression_stroke_mm"] == pytest.approx(fill_mm - compressed_mm)
    assert details["ejection_stroke_mm"] == pytest.approx(compressed_mm + chamber["ejection_overtravel_mm"])
    assert gate["threshold"]["min_stroke_mm"] == pytest.approx(minimum_mm)
    assert details["minimum_stroke_mm"] == pytest.approx(minimum_mm)
    assert details["minimum_stroke_ratio"] == pytest.approx(320 / minimum_mm)
    assert not details["checks"]["stroke_at_least_required"]
    assert gate["status"] == "FAIL"


def test_dose_missing_approach_warns(params, criteria):
    chamber = params["chamber"]
    del chamber["approach_stroke_mm"], chamber["in_die_density_kg_m3"]
    params["main_cylinder"]["stroke_mm"] = 250
    gate = calc.evaluate_dose(params, criteria)
    details = gate["details"]
    assert gate["status"] == "WARN"
    assert "chamber.approach_stroke_mm" in details["warnings"][0]
    assert details["approach_stroke_mm"] == 0
    assert details["in_die_density_source"] == "product.density_kg_m3"
    chamber["approach_stroke_mm"] = 0
    assert calc.evaluate_dose(params, criteria)["status"] == "PASS"


@pytest.mark.parametrize("density", [90, 160])
def test_dose_volume_at_each_end(params, criteria, density):
    precomp = params["precompaction"]
    precomp["loose_fill_length_mm"] = 1e9 * params["raw"]["dose_kg"] / (density * math.prod(precomp["section_mm"]))

    def fits():
        gate = calc.evaluate_dose(params, criteria)
        return next(sample["fits"] for sample in gate["details"]["loose_dose_samples"]
                    if sample["density_kg_m3"] == density)

    assert fits()
    precomp["loose_fill_length_mm"] -= 0.01
    assert not fits()


@pytest.mark.parametrize("key, value, check", [
    ("dose_kg", 0.829, "minimum_dose"),
    ("bulk_density_kg_m3", [90.001, 160], "bulk_density_covers_reference"),
    ("bulk_density_kg_m3", [90, 159.999], "bulk_density_covers_reference"),
])
def test_dose_reference_mass_and_densities(params, criteria, key, value, check):
    assert calc.evaluate_dose(params, criteria)["status"] == "PASS"
    params["raw"][key] = value
    assert not calc.evaluate_dose(params, criteria)["details"]["checks"][check]


def phase(name, direction, stroke_mm, pressure_bar, **kwargs):
    data = dict(name=name, actuator="main_cylinder", direction=direction, stroke_mm=stroke_mm,
                pressure_bar=pressure_bar, speed_mm_s="pump", regeneration=False, dwell_s=0)
    return data | kwargs


def test_cycle_time_and_pressure_boundaries(params, criteria):
    params["cycle"] = [phase("hold", "extend", 0, 300, dwell_s=5.9, press=True)]
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "PASS"
    assert gate["details"]["peak_drive_power_kW"] == 0
    params["cycle"][0]["dwell_s"] += 0.001
    assert not calc.evaluate_cycle(params, criteria)["details"]["checks"]["cycle_time_limit"]
    params["cycle"][0]["pressure_bar"] += 0.001
    assert not calc.evaluate_cycle(params, criteria)["details"]["checks"]["working_pressure_limit"]


def test_cycle_average_power_boundary(params, criteria):
    params["cycle"] = [phase("out", "extend", 50, 300, press=True), phase("back", "retract", 50, 300)]
    energy_kJ = calc.evaluate_cycle(params, criteria)["details"]["total_motor_energy_kJ"]
    params["drive"]["peak_kW"] = 30 * energy_kJ / (energy_kJ - 30 * 0.2)
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["details"]["average_power_kW"] == pytest.approx(30)
    assert gate["details"]["checks"]["average_power_limit"]
    assert gate["details"]["checks"]["peak_drive_power_limit"]
    assert gate["status"] == "FAIL"
    params["drive"]["peak_kW"] += 0.001
    assert not calc.evaluate_cycle(params, criteria)["details"]["checks"]["average_power_limit"]


@pytest.mark.parametrize("grouped", [False, True], ids=["serial", "grouped"])
def test_peak_rating_increases_flow_and_rms_includes_idle(params, criteria, grouped):
    params["cycle"] = [
        phase("press", "extend", 10, 290, dwell_s=0.25, press=True),
        phase("back", "retract", 10, 0),
    ]
    if grouped:
        params["cycle"][0]["group"] = "press"
    nominal = calc.evaluate_cycle(params, criteria)
    params["drive"].update(peak_kW=40, idle_kW=4)
    calc.validate_params(params)
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "PASS"
    assert gate["value"] < nominal["value"]
    details = gate["details"]
    press, _ = details["phases"]
    assert press["pump_limit_L_min"] == pytest.approx(600 * 40 * 0.9 / 290)
    assert press["motion_s"] == pytest.approx(nominal["details"]["phases"][0]["motion_s"] * 30 / 40)
    idle_s = 0.25 + 2 * calc.SWITCH_S
    assert details["idle_time_s"] == pytest.approx(idle_s)
    assert details["average_power_kW"] == pytest.approx((40 * press["motion_s"] + 4 * idle_s) / gate["value"])
    assert details["rms_power_kW"] == pytest.approx(
        math.sqrt((40**2 * press["motion_s"] + 4**2 * idle_s) / gate["value"])
    )
    assert details["peak_drive_power_kW"] == pytest.approx(40)


def test_cycle_fails_only_rms_when_average_and_peak_meet_limits(params, criteria):
    params["drive"]["peak_kW"] = 40
    params["cycle"] = [phase("press", "extend", 40, 300, press=True), phase("back", "retract", 40, 300)]
    phases = calc.evaluate_cycle(params, criteria)["details"]["phases"]
    motion_s = math.fsum(row["motion_s"] for row in phases)
    params["cycle"][0]["dwell_s"] = motion_s / 2 - 2 * calc.SWITCH_S
    gate = calc.evaluate_cycle(params, criteria)
    details = gate["details"]
    assert gate["status"] == "FAIL"
    assert details["average_power_kW"] == pytest.approx(40 * 2 / 3)
    assert details["rms_power_kW"] == pytest.approx(40 * math.sqrt(2 / 3))
    assert {key for key, passed in details["checks"].items() if not passed} == {"rms_power_limit"}


def test_legacy_power_criteria_keep_nominal_peak_and_skip_rms_check(params, criteria):
    power = criteria["C-PWR-01"]
    del power["max_peak_kW"], power["max_rms_kW"]
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "PASS"
    assert gate["threshold"]["max_peak_drive_power_kW"] == 30
    assert "rms_power_limit" not in gate["details"]["checks"]
    assert "max_rms_power_kW" not in gate["threshold"]
    params["drive"]["peak_kW"] = 31
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    assert gate["details"]["peak_drive_power_kW"] == pytest.approx(31)
    assert not gate["details"]["checks"]["peak_drive_power_limit"]


def test_cycle_press_force_boundary_and_missing_phase(params, criteria):
    cylinder = params["main_cylinder"]
    cylinder["n"] = 2
    force_N = criteria["C-PFACE-01"]["nominal_force_min_N"]
    pressure_bar = 10 * force_N / (calc.piston_area_mm2(cylinder) * cylinder["eta"])
    press = phase("press", "extend", 10, pressure_bar, press=True)
    params["cycle"] = [press, phase("back", "retract", 10, 0)]
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "PASS"
    assert gate["details"]["phases"][0]["force_N"] == pytest.approx(force_N)
    press["pressure_bar"] -= 0.001
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    assert not gate["details"]["checks"]["press_force_minimum"]
    del press["press"]
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    assert gate["details"]["failures"] == ["нет фазы прессования"]


@pytest.mark.parametrize("configuration", [
    {"direction": "retract"}, {"regeneration": True}, {"actuator": "precompaction"},
])
def test_cycle_press_requires_main_piston_extension(params, criteria, configuration):
    params["cycle"] = [phase("press", "extend", 0, 290, dwell_s=1, press=True) | configuration]
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    assert not gate["details"]["checks"]["press_configuration_valid"]


def test_cycle_peak_and_installed_power_boundaries(params, criteria):
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "PASS"
    assert gate["details"]["peak_drive_power_kW"] == pytest.approx(30)
    assert gate["details"]["peak_hydraulic_power_kW"] == pytest.approx(30)
    params["drive"]["motor_kW"] += 0.001
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    assert {key for key, passed in gate["details"]["checks"].items() if not passed} == {"motor_rating_limit"}
    params["drive"]["motor_kW"] = 30
    params["drive"]["installed_kW"] = 34.2
    assert calc.evaluate_cycle(params, criteria)["status"] == "PASS"
    params["drive"]["installed_kW"] += 0.001
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    assert not gate["details"]["checks"]["installed_power_limit"]
    del params["drive"]["installed_kW"]
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "WARN"
    assert gate["details"]["warnings"] == ["установленная мощность не задана"]


def test_cycle_validates_declared_and_actual_peak_independently(params, criteria):
    params["cycle"] = [phase("hold", "extend", 0, 290, dwell_s=0.1, press=True)]
    params["drive"]["peak_kW"] = 40.001
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    assert {key for key, passed in gate["details"]["checks"].items() if not passed} == {"peak_rating_limit"}

    params["cycle"] = [phase("press", "extend", 10, 290, press=True), phase("back", "retract", 10, 0)]
    params["drive"].update(peak_kW=40, idle_kW=40.001)
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    assert gate["details"]["peak_drive_power_kW"] == pytest.approx(40.001)
    assert gate["details"]["checks"]["peak_rating_limit"]
    assert not gate["details"]["checks"]["peak_drive_power_limit"]


@pytest.mark.parametrize("field, value", [("peak_kW", 0), ("idle_kW", -1), ("idle_kW", True)])
def test_drive_power_schema_bounds(params, field, value):
    params["drive"][field] = value
    with pytest.raises(InputError, match=rf"drive\.{field}"):
        calc.validate_params(params)


def test_cycle_requested_speed_overloads_30_kW_drive(tmp_path, criteria):
    text = EXAMPLE.read_text(encoding="utf-8")
    path = tmp_path / "overload.yaml"
    path.write_text(text.replace("pressure_bar: 290, speed_mm_s: pump", "pressure_bar: 290, speed_mm_s: 40"),
                    encoding="utf-8")
    code, report = run_calc(tmp_path, path, "--gates", "G-CYCLE")
    gate, = report["gates"]
    assert (code, gate["status"]) == (1, "FAIL")
    details = gate["details"]
    press = next(row for row in details["phases"] if row["press"])
    expected_flow_L_min = 60 * math.pi / 4 * 270**2 * 40 / 1e6
    assert press["required_flow_L_min"] == pytest.approx(expected_flow_L_min)
    assert press["available_flow_L_min"] == pytest.approx(600 * 30 * 0.9 / 290)
    assert details["peak_drive_power_kW"] == pytest.approx(30)
    assert details["checks"]["cycle_time_limit"]
    assert not details["checks"]["requested_speeds_met"]
    assert details["checks"]["peak_drive_power_limit"]
    assert details["checks"]["peak_rating_limit"]

    power = criteria["C-PWR-01"]
    del power["max_peak_kW"], power["max_rms_kW"]
    legacy = calc.evaluate_cycle(load_yaml(path.read_bytes(), path), criteria)["details"]
    assert legacy["peak_drive_power_kW"] == pytest.approx(290 * expected_flow_L_min / (600 * 0.9))
    assert not legacy["checks"]["peak_drive_power_limit"]
    assert not legacy["checks"]["pump_power_within_motor_rating"]


@pytest.mark.parametrize("previous_change", [None, {"regeneration": True}, {"dwell_s": 0.1},
                                              {"direction": "retract"}, {"actuator": "precompaction"}])
def test_cycle_continuation_requires_uninterrupted_configuration(params, previous_change):
    start = phase("start", "extend", 10, 50)
    continuation = phase("continue", "extend", 10, 100, continues=True)
    params["cycle"] = [start | previous_change, continuation] if previous_change is not None else [continuation]
    with pytest.raises(InputError, match="continues: expected uninterrupted travel"):
        calc.validate_params(params)


def test_cycle_missing_installed_power_cli_warns(tmp_path):
    filtered = tmp_path / "params.yaml"
    text = EXAMPLE.read_text(encoding="utf-8")
    filtered.write_text(text.replace("  installed_kW: 34\n", ""), encoding="utf-8")
    exit_code, report = run_calc(tmp_path, filtered)
    assert exit_code == 0
    assert report["overall"] == report["gates"][2]["status"] == "WARN"


def test_cycle_accumulator_boost_does_not_count_as_drive_peak(params, criteria):
    params["drive"]["accumulator"] = {
        "usable_oil_L": 0.5, "max_flow_L_min": 80, "min_delivery_pressure_bar": 290,
        "charge_pressure_bar": 300, "round_trip_eta": 0.8,
    }
    params["cycle"] = [
        phase("press", "extend", 10, 290, press=True, use_accumulator=True),
        phase("back", "retract", 10, 10),
    ]
    gate = calc.evaluate_cycle(params, criteria)
    details = gate["details"]
    out, _, recharge = details["phases"]
    assert gate["status"] == "PASS"
    assert out["peak_drive_power_kW"] == pytest.approx(30)
    assert out["peak_hydraulic_power_kW"] == pytest.approx(30 + 290 * 80 / (600 * 0.9))
    assert recharge["peak_drive_power_kW"] == pytest.approx(30)
    assert details["peak_hydraulic_power_kW"] > 30
    assert details["checks"]["peak_rating_limit"]


def test_cycle_required_speed_accounts_for_sustained_accumulator_delivery(params, criteria):
    accumulator = {"usable_oil_L": 0.5, "max_flow_L_min": 100, "min_delivery_pressure_bar": 290,
                   "charge_pressure_bar": 300, "round_trip_eta": 0.8}
    params["drive"]["accumulator"] = accumulator
    press = phase("press", "extend", 10, 290, speed_mm_s=40, press=True, use_accumulator=True)
    params["cycle"] = [press, phase("back", "retract", 10, 10)]
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "PASS"
    assert gate["details"]["phases"][0]["peak_drive_power_kW"] == pytest.approx(30)
    accumulator["usable_oil_L"] = 0.25
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "FAIL"
    row = gate["details"]["phases"][0]
    assert row["available_flow_L_min"] == pytest.approx(row["pump_limit_L_min"] + 60 * 0.25 / (10 / 40))
    assert row["peak_drive_power_kW"] == pytest.approx(30)
    assert row["required_pump_flow_L_min"] > row["pump_limit_L_min"]
    assert not row["requested_speed_met"]


def test_cycle_regeneration_force_and_speed(params, criteria):
    extend = phase("out", "extend", 10, 0, regeneration=True, speed_mm_s=40)
    del extend["pressure_bar"]
    extend["force_N"] = 100_000
    params["cycle"] = [extend, phase("back", "retract", 10, 0)]
    row, back = calc.evaluate_cycle(params, criteria)["details"]["phases"]
    cylinder = params["main_cylinder"]
    rod_area_mm2 = math.pi * cylinder["rod_mm"] ** 2 / 4
    assert row["area_mm2"] == pytest.approx(rod_area_mm2)
    assert row["pressure_bar"] == pytest.approx(10 * extend["force_N"] / (rod_area_mm2 * cylinder["eta"]))
    assert row["motion_s"] == pytest.approx(0.25)
    assert row["area_mm2"] + back["area_mm2"] == pytest.approx(calc.piston_area_mm2(cylinder))
    extend["speed_mm_s"] = 10_000
    assert not calc.evaluate_cycle(params, criteria)["details"]["checks"]["requested_speeds_met"]


def test_accumulator_volume_recharge_and_pressure(params, criteria):
    acc = {"usable_oil_L": 0.25, "max_flow_L_min": 100, "min_delivery_pressure_bar": 250,
           "charge_pressure_bar": 290, "round_trip_eta": 0.8}
    params["drive"]["accumulator"] = acc
    params["cycle"] = [phase("out", "extend", 60, 250, use_accumulator=True),
                       phase("back", "retract", 60, 10, use_accumulator=True)]
    out, back, recharge = calc.evaluate_cycle(params, criteria)["details"]["phases"]
    assert out["accumulator_oil_L"] == pytest.approx(0.25)
    assert out["motion_s"] == pytest.approx(60 * (out["oil_L"] - 0.25) / out["pump_limit_L_min"])
    assert back["accumulator_oil_L"] == 0
    assert recharge["pump_oil_L"] == pytest.approx(0.25 / 0.8)
    assert recharge["motor_energy_kJ"] == pytest.approx(0.25 * 290 / (10 * 0.8 * 0.9))
    assert recharge["switch_s"] == 0.1
    acc["min_delivery_pressure_bar"] -= 0.001
    assert not calc.evaluate_cycle(params, criteria)["details"]["checks"]["accumulator_pressure_covered"]


@pytest.mark.parametrize("filename, statuses, values", [
    ("params.m1.yaml", ("PASS", "PASS", "PASS"), (168.88888888888889, 230, 5.872055963129407)),
    ("params.t12.yaml", ("PASS", "PASS", "FAIL"), (168.88888888888889, 230, 7.724224421093544)),
    ("params.t12b.yaml", ("PASS", "PASS", "FAIL"), (168.88888888888889, 289, 7.969673072562054)),
])
def test_legacy_calc_gate_values_match_main(criteria, filename, statuses, values):
    path = ROOT / "design" / filename
    params = load_yaml(path.read_bytes(), path)
    calc.validate_params(params)
    for evaluate, status, value in zip(calc.GATES.values(), statuses, values, strict=True):
        result = evaluate(params, criteria)
        assert result["status"] == status
        assert result["value"] == pytest.approx(value, rel=0, abs=1e-9)


def test_group_shares_pump_in_yaml_order_at_highest_active_pressure(params, criteria):
    params["drive"]["pump_max_flow_L_min"] = 600
    cylinders = calc.actuators(params)
    phases = []
    for actuator, pressure_bar in [("main_cylinder", 10), ("precompaction", 54)]:
        # Each movement requests 200 L/min for 0.2 s. Together they get 300 L/min.
        speed_mm_s = 200e6 / (60 * calc.piston_area_mm2(cylinders[actuator]))
        phases.append(phase(actuator, "extend", speed_mm_s * 0.2, pressure_bar,
                            actuator=actuator, speed_mm_s=speed_mm_s))
    params["cycle"] = phases
    serial = calc.evaluate_cycle(params, criteria)
    for movement in phases:
        movement["group"] = "advance"
    calc.validate_params(params)
    grouped = calc.evaluate_cycle(params, criteria)
    details = grouped["details"]
    first, second = details["phases"]
    assert calc.SWITCH_S + 0.2 < grouped["value"] < serial["value"]
    assert grouped["value"] == pytest.approx(0.4)
    assert first["motion_s"] == pytest.approx(0.2)
    assert second["motion_s"] == pytest.approx(0.3)
    assert details["switch_count"] == 1
    assert first["motor_energy_kJ"] == pytest.approx(calc.pump_energy_kJ(first["oil_L"], 54, 0.9))
    assert details["peak_drive_power_kW"] == pytest.approx(30)
    assert details["checks"]["peak_rating_limit"]
    assert details["rms_power_kW"] == pytest.approx(math.sqrt((30**2 * 0.2 + 20**2 * 0.1) / 0.4))
    assert not details["checks"]["requested_speeds_met"]
    assert not details["checks"]["actuators_return_to_start"]

    # The pump can sustain both requested speeds at 10 bar.
    phases[1]["pressure_bar"] = 10
    details = calc.evaluate_cycle(params, criteria)["details"]
    assert details["cycle_s"] == pytest.approx(calc.SWITCH_S + 0.2)
    assert details["checks"]["requested_speeds_met"]


def test_group_delays_are_from_group_start_and_dwell_can_overlap(params, criteria):
    params["cycle"] = [
        {"name": "feed", "actuator": "none", "stroke_mm": 0, "dwell_s": 0.2},
        phase("out", "extend", 4, 290, group="trip", speed_mm_s=10),
        phase("delayed", "extend", 8, 10, actuator="precompaction", group="trip",
              speed_mm_s=40, start_delay_s=0.15),
        {"name": "dwell", "actuator": "none", "dwell_s": 0.48, "start_delay_s": 0.02,
         "group": "trip", "overlap_allowed": True},
        phase("back", "retract", 4, 10, group="trip_again", max_speed_mm_s=1000),
        phase("reset", "retract", 8, 10, actuator="precompaction", group="trip_again", max_speed_mm_s=1000),
    ]
    calc.validate_params(params)
    details = calc.evaluate_cycle(params, criteria)["details"]
    feed, first, delayed, dwell, back, _ = details["phases"]
    assert feed["switch_s"] == feed["pump_oil_L"] == 0
    assert delayed["start_delay_reference"] == "group_start_s"
    assert delayed["group_start_s"] == pytest.approx(0.2)
    assert first["motion_start_s"] == pytest.approx(0.3)
    assert delayed["command_start_s"] == pytest.approx(0.35)
    assert delayed["motion_start_s"] == pytest.approx(0.45)
    assert delayed["switch_s"] == calc.SWITCH_S
    assert dwell["command_start_s"] == pytest.approx(0.22)
    assert dwell["end_s"] == back["group_start_s"] == pytest.approx(0.7)
    assert dwell["overlap_time_s"] == pytest.approx(0.4)  # The two moving intervals overlap one another.
    assert details["warnings"] == ["группа 'trip': фаза 'dwell' с overlap_allowed перекрывает движение на 0.4 с"]
    assert details["switch_count"] == 3
    assert details["checks"]["actuators_return_to_start"]


@pytest.mark.parametrize("other", [
    phase("travel", "extend", 1, 10, actuator="precompaction", group="press"),
    {"name": "hold", "actuator": "none", "dwell_s": 0.1, "group": "press", "overlap_allowed": True},
])
def test_press_phase_cannot_share_group(params, criteria, other):
    params["cycle"] = [phase("press", "extend", 4, 290, group="press", press=True), other]
    calc.validate_params(params)
    with pytest.raises(InputError, match="press phase must be alone in group 'press'"):
        calc.evaluate_cycle(params, criteria)


def test_none_phase_sharing_group_requires_explicit_permission(params, criteria):
    idle = {"name": "feed", "actuator": "none", "dwell_s": 0.15, "group": "return"}
    params["cycle"] = [
        phase("press", "extend", 4, 290, press=True),
        phase("back", "retract", 4, 10, group="return", speed_mm_s=20),
        idle,
    ]
    calc.validate_params(params)
    with pytest.raises(InputError, match="feed: actuator none.*requires overlap_allowed: true"):
        calc.evaluate_cycle(params, criteria)

    idle["overlap_allowed"] = True
    calc.validate_params(params)
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "WARN"
    assert gate["details"]["phases"][-1]["overlap_time_s"] == pytest.approx(0.05)


def test_two_uncapped_movements_in_group_warn(params, criteria):
    main_return = phase("back", "retract", 4, 10, group="return")
    params["cycle"] = [
        phase("press", "extend", 4, 290, press=True),
        phase("pre", "extend", 4, 20, actuator="precompaction"),
        main_return,
        phase("reset", "retract", 4, 10, actuator="precompaction", group="return"),
    ]
    calc.validate_params(params)
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["status"] == "WARN"
    warning, = gate["details"]["warnings"]
    assert "'return'" in warning
    assert "pump без max_speed_mm_s (back, reset)" in warning
    main_return["max_speed_mm_s"] = 1000
    calc.validate_params(params)
    assert calc.evaluate_cycle(params, criteria)["status"] == "PASS"


@pytest.mark.parametrize("fields", [
    {"stroke_mm": 1}, {"force_N": 0}, {"dwell_s": 0}, {"start_delay_s": -0.01}, {"max_speed_mm_s": 10},
    {"overlap_allowed": "true"},
])
def test_nonhydraulic_phase_rejects_invalid_fields(params, fields):
    params["cycle"] = [{"name": "feed", "actuator": "none", "dwell_s": 0.2} | fields]
    with pytest.raises(InputError, match=r"cycle\[0\]"):
        calc.validate_params(params)


def test_same_actuator_must_not_have_overlapping_travel(params, criteria):
    params["cycle"] = [
        phase("out", "extend", 10, 20, group="trip", speed_mm_s=20),
        phase("back", "retract", 10, 20, group="trip", start_delay_s=0.49),
    ]
    calc.validate_params(params)
    with pytest.raises(InputError, match="main_cylinder: overlapping travel in 'out' and 'back'"):
        calc.evaluate_cycle(params, criteria)
    params["cycle"][1]["start_delay_s"] = 0.5
    details = calc.evaluate_cycle(params, criteria)["details"]
    assert details["checks"]["actuators_return_to_start"]
    out, back = details["phases"]
    assert out["motion_end_s"] == pytest.approx(back["motion_start_s"])


def test_pressure_bands_continue_inside_group_and_same_label_can_recur(params, criteria):
    params["cycle"] = [
        phase("band 1", "extend", 10, 80, group="trip", speed_mm_s=50),
        phase("band 2", "extend", 10, 100, group="trip", speed_mm_s=50, continues=True),
        phase("pre", "extend", 10, 20, group="trip", actuator="precompaction", speed_mm_s=50),
        {"name": "pause", "actuator": "none", "dwell_s": 0.25},
        phase("back", "retract", 20, 20, group="trip"),
    ]
    calc.validate_params(params)
    details = calc.evaluate_cycle(params, criteria)["details"]
    first, second, pre, pause, back = details["phases"]
    assert pre["motion_start_s"] == first["motion_start_s"]
    assert second["motion_start_s"] == first["motion_end_s"]
    assert second["switch_s"] == 0
    assert back["group_start_s"] == pause["end_s"]
    assert back["group_start_s"] > first["group_end_s"]
    assert details["actuator_travel_mm"]["main_cylinder"] == 20


@pytest.mark.parametrize("gap_s", [0.5e-9, 2e-9], ids=["within-tolerance", "outside-tolerance"])
def test_continues_across_group_boundary_uses_absolute_tolerance(params, criteria, gap_s):
    params["cycle"] = [
        phase("pre", "extend", 10 + 50 * gap_s, 10, actuator="precompaction", speed_mm_s=50, group="start"),
        phase("band 1", "extend", 10, 10, speed_mm_s=50, group="start"),
        phase("band 2", "extend", 10, 20, speed_mm_s=50, continues=True, group="next"),
    ]
    calc.validate_params(params)
    if gap_s > 1e-9:
        with pytest.raises(InputError, match="previous travel must end at the group boundary"):
            calc.evaluate_cycle(params, criteria)
    else:
        _, first, second = calc.evaluate_cycle(params, criteria)["details"]["phases"]
        assert second["switch_s"] == 0
        assert second["motion_start_s"] - first["motion_end_s"] == pytest.approx(gap_s, abs=1e-12)


def test_group_accumulator_shares_delivery_and_recharges_during_dwell(params, criteria):
    drive = params["drive"]
    drive["pump_max_flow_L_min"] = 60
    drive["idle_kW"] = 2
    drive["accumulator"] = {"usable_oil_L": 0.3, "max_flow_L_min": 60, "min_delivery_pressure_bar": 60,
                            "charge_pressure_bar": 80, "round_trip_eta": 0.8, "recharge_when_idle": True}
    cylinders = calc.actuators(params)
    phases = []
    for actuator in ("main_cylinder", "precompaction"):
        area_mm2 = calc.piston_area_mm2(cylinders[actuator])
        # Two 0.4 L movements at 48 L/min each. Their total deficit is 36 L/min.
        phases.append(phase(actuator, "extend", 0.4e6 / area_mm2, 60, group="move", actuator=actuator,
                            speed_mm_s=48e6 / (60 * area_mm2), use_accumulator=True))
    params["cycle"] = phases + [{"name": "dwell", "actuator": "none", "dwell_s": 0.25}]
    calc.validate_params(params)
    details = calc.evaluate_cycle(params, criteria)["details"]
    first, second, dwell, idle, tail = details["phases"]
    assert first["accumulator_oil_L"] == pytest.approx(0.3)
    assert first["accumulator_rate_L_min"] == pytest.approx(36)
    assert second["accumulator_oil_L"] == 0
    assert first["motion_end_s"] == second["motion_end_s"] == pytest.approx(0.6)
    assert idle["motion_s"] == pytest.approx(dwell["dwell_s"])
    assert idle["pump_oil_L"] == pytest.approx(0.25)
    assert idle["time_s"] == 0
    assert tail["pump_oil_L"] == pytest.approx(0.3 / 0.8 - 0.25)
    assert tail["motor_energy_kJ"] == pytest.approx(calc.pump_energy_kJ(tail["pump_oil_L"], 80, 0.9))
    assert details["cycle_s"] == pytest.approx(1.075)
    assert details["checks"]["requested_speeds_met"]
    assert details["idle_time_s"] == pytest.approx(0.2)
    motion_power_kW = 60 * 60 / (600 * drive["eta"])
    charge_power_kW = 80 * 60 / (600 * drive["eta"])
    energy_kJ = motion_power_kW * 0.5 + charge_power_kW * 0.375 + 2 * 0.2
    integral_kW2_s = motion_power_kW**2 * 0.5 + charge_power_kW**2 * 0.375 + 2**2 * 0.2
    assert details["total_motor_energy_kJ"] == pytest.approx(energy_kJ)
    assert details["rms_power_kW"] == pytest.approx(math.sqrt(integral_kW2_s / 1.075))

    drive["accumulator"]["recharge_when_idle"] = False
    no_idle = calc.evaluate_cycle(params, criteria)["details"]
    assert no_idle["cycle_s"] == pytest.approx(details["cycle_s"] + 0.25)
    assert no_idle["total_pump_oil_L"] == pytest.approx(details["total_pump_oil_L"])

    drive["accumulator"]["recharge_when_idle"] = True
    params["cycle"][-1]["dwell_s"] = 0.5
    details = calc.evaluate_cycle(params, criteria)["details"]
    assert details["idle_time_s"] == pytest.approx(0.1 + 0.5 - 0.375)
    assert details["phases"][-1]["name"] == "Accumulator recharge during idle"
    assert details["rms_power_kW"] == pytest.approx(math.sqrt((integral_kW2_s + 2**2 * 0.025) / 1.1))


@pytest.mark.parametrize("group", [{}, {"group": "press"}], ids=["serial", "grouped"])
@pytest.mark.parametrize("max_speed_mm_s", [5, 40], ids=["surplus-flow", "limited-flow"])
def test_phase_speed_cap_limits_motion_without_requesting_flow(params, criteria, group, max_speed_mm_s):
    stroke_mm, pressure_bar = 10, 290
    params["cycle"] = [
        phase("press", "extend", stroke_mm, pressure_bar, press=True, max_speed_mm_s=max_speed_mm_s, **group),
        phase("back", "retract", stroke_mm, 10),
    ]
    calc.validate_params(params)
    gate = calc.evaluate_cycle(params, criteria)
    details = gate["details"]
    row = details["phases"][0]
    pump_flow_L_min = calc.pump_flow_L_min(params["drive"], pressure_bar)
    pump_speed_mm_s = pump_flow_L_min * 1e6 / (60 * row["area_mm2"])
    actual_speed_mm_s = stroke_mm / row["motion_s"]
    assert actual_speed_mm_s == pytest.approx(min(pump_speed_mm_s, max_speed_mm_s))
    assert row["required_flow_L_min"] is None
    assert details["checks"]["requested_speeds_met"]
    assert gate["status"] == "PASS"


def test_phase_speed_cap_conflicts_with_numeric_speed(params):
    params["cycle"] = [phase("press", "extend", 10, 290, speed_mm_s=20, max_speed_mm_s=30)]
    with pytest.raises(InputError, match=r"cycle\[0\]\.max_speed_mm_s: requires speed_mm_s: pump"):
        calc.validate_params(params)


@pytest.mark.parametrize("max_speed_mm_s", [0, -1, "250", True, 1000.001])
def test_phase_speed_cap_requires_positive_number_at_most_1000(params, max_speed_mm_s):
    params["cycle"] = [phase("press", "extend", 10, 290, max_speed_mm_s=max_speed_mm_s)]
    with pytest.raises(InputError, match=r"cycle\[0\]\.max_speed_mm_s"):
        calc.validate_params(params)


@pytest.mark.parametrize("filename, feed_s, status, failed_checks", [
    ("x1_overlap", 0.50, "PASS", set()),
    ("t12b_overlap", 0.50, "FAIL", {"cycle_time_limit"}),
    ("t12b_overlap_feed064", 0.64, "FAIL", {"cycle_time_limit"}),
])
def test_overlap_calibration_matches_independent_trace(criteria, filename, feed_s, status, failed_checks):
    if filename == "x1_overlap":
        results = json.loads((ROOT / "calc/X-1/x1_results.json").read_bytes())
        reference = next(row for row in results["cycle_cases"] if row["overlap"] and row["accumulator"]
                         and row["pump_max_flow_L_min"] == 360 and row["feed_s"] == feed_s)
    else:
        results = json.loads((ROOT / "calc/T-1.2b/results.json").read_bytes())
        reference = results["alternatives"]["A"]["cycle"][f"{feed_s:.2f}"]
    path = ROOT / "ops/calibration" / f"{filename}.params.yaml"
    params = load_yaml(path.read_bytes(), path)
    calc.validate_params(params)
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["value"] == pytest.approx(reference["cycle_s"], rel=0, abs=0.15)
    assert gate["status"] == status
    details = gate["details"]
    assert {key for key, passed in details["checks"].items() if not passed} == failed_checks
    rows = {row["name"]: row for row in details["phases"]}
    assert rows["pre_up 1"]["motion_start_s"] < rows["return 1"]["motion_end_s"]
    assert rows["gate_close 1"]["motion_start_s"] < rows["return 1"]["motion_end_s"]


@pytest.mark.parametrize("old, new, field", [
    ("bore_mm: 270", "bore_m: 0.270", "main_cylinder.bore_mm"),
    ("p_work_bar: 290", "p_work_MPa: 29", "main_cylinder.p_work_bar"),
    ("dose_kg: 0.83", "dose_kg: '830 g'", "raw.dose_kg"),
    ("pump_max_flow_L_min: 520", "pump_max_flow_L_s: 8.67", "drive.pump_max_flow_L_min"),
    ("dwell_s: 0.15", "dwell_ms: 150", "dwell_s"),
    ("speed_mm_s: 250", "speed_mm_s: '15 m/min'", "speed_mm_s"),
    ("eta: 0.95", "eta: 95", "main_cylinder.eta"),
    ("dose_kg: 0.83", "dose_kg: .nan", "raw.dose_kg"),
    ("dose_kg: 0.83", "dose_kg: true", "raw.dose_kg"),
])
def test_incorrect_units_and_numbers_are_input_errors(tmp_path, old, new, field):
    path = tmp_path / "params.yaml"
    path.write_text(EXAMPLE.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
    code, report = run_calc(tmp_path, path)
    assert (code, report["overall"]) == (2, "FAIL")
    assert all(gate["status"] == "ERROR" and field in gate["details"]["error"] for gate in report["gates"])


def test_wrong_numeric_scale_fails_physical_limits(params, criteria):
    params["main_cylinder"]["p_work_bar"] = 29  # MPa value in a bar field.
    params["chamber"]["section_mm"] = [0.15, 0.06]  # Metres in a millimetre field.
    params["raw"]["dose_kg"] = 830  # Grams in a kilogram field.
    assert not calc.evaluate_pface(params, criteria)["details"]["checks"]["minimum_force_at_work_pressure"]
    assert not calc.evaluate_dose(params, criteria)["details"]["checks"]["loose_dose_fits"]


def test_phase_requires_exactly_one_load_input(params):
    params["cycle"][0]["force_N"] = 10
    with pytest.raises(InputError, match="exactly one of force_N and pressure_bar"):
        calc.validate_params(params)


@pytest.mark.parametrize("effort, status", [("high", "PASS"), ("LOW", "FAIL"), ("none", "FAIL"),
                                            ("  ", "FAIL"), (None, "FAIL")])
def test_scope_reasoning_effort(tmp_path, monkeypatch, effort, status):
    changes = dict(committed=[], staged=[], unstaged=[], untracked=["TASK.md", "report.md", "ops/gates/deep/check.py"])
    monkeypatch.setattr(scope, "worktree_changes", lambda *args: changes)
    monkeypatch.setattr(scope, "git", lambda *args: b"")
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({"reasoning_effort": effort}), encoding="utf-8")
    card = {"allowed_paths": ["ops/gates/**"], "allow_protected": ["ops/gates/**"]}
    gate = scope.evaluate_scope(tmp_path, card, "base", "fork", meta)
    assert gate["status"] == status
    assert gate["details"]["forbidden_paths"] == []
    assert scope.evaluate_scope(tmp_path, card, "base", "fork", None)["status"] == "WARN"


def test_scope_checks_each_diff_and_protected_hashes(tmp_path, monkeypatch):
    criteria = tmp_path / "ops/criteria/design_criteria.yaml"
    criteria.parent.mkdir(parents=True)
    criteria.write_bytes(b"changed")
    changes = {
        ("base...HEAD", "--"): b"outside/committed.py\0",
        ("--cached", "HEAD", "--"): b"outside/staged.py\0",
        ("--",): b"outside/unstaged.py\0",
    }

    def stub_git(_, command, *args):
        if command == "diff":
            assert args[:3] == ("--name-only", "--no-renames", "-z")
            return changes[args[3:]]
        if command == "ls-files":
            if "--others" in args:
                return b"outside/untracked.py\0design/params.yaml\0"
            return b"ops/criteria/design_criteria.yaml\0"
        if command == "ls-tree":
            assert "fork" in args
            return b"100644 blob object\tops/criteria/design_criteria.yaml\0"
        if command == "status":
            return b""
        assert (command, *args) == ("cat-file", "blob", "object")
        return b"original"

    monkeypatch.setattr(scope, "git", stub_git)
    gate = scope.evaluate_scope(tmp_path, {"allowed_paths": ["design/**"]}, "base", "fork", None)
    assert gate["status"] == "FAIL"
    assert gate["details"]["forbidden_paths"] == [f"outside/{kind}.py" for kind in
                                                 ("committed", "staged", "unstaged", "untracked")]
    hashes = gate["details"]["protected_hashes"]
    assert hashes == [{"path": "ops/criteria/design_criteria.yaml",
                       "base_sha256": hashlib.sha256(b"original").hexdigest(),
                       "worktree_sha256": hashlib.sha256(b"changed").hexdigest()}]
    card = {"allowed_paths": ["design/**", "ops/**", "outside/**"], "allow_protected": ["ops/**"]}
    gate = scope.evaluate_scope(tmp_path, card, "base", "fork", None)
    assert gate["status"] == "FAIL"
    assert gate["details"]["forbidden_paths"] == []
    assert gate["details"]["protected_hash_mismatches"] == ["ops/criteria/design_criteria.yaml"]


def test_scope_protects_gate_edits_even_if_restored_on_disk(tmp_path, monkeypatch):
    name = "ops/gates/gate.py"
    file = tmp_path / name
    file.parent.mkdir(parents=True)
    file.write_bytes(b"original")
    changes = dict(committed=[], staged=[name], unstaged=[name], untracked=[])
    monkeypatch.setattr(scope, "worktree_changes", lambda *args: changes)

    def stub_git(_, command, *args):
        return {
            "ls-tree": b"100644 blob object\tops/gates/gate.py\0",
            "cat-file": b"original",
        }.get(command, b"")

    monkeypatch.setattr(scope, "git", stub_git)
    card = {"allowed_paths": ["ops/**"]}
    gate = scope.evaluate_scope(tmp_path, card, "base", "fork", None)
    assert gate["status"] == "FAIL"
    assert gate["details"]["protected_hash_mismatches"] == []
    assert gate["details"]["protected_changes"] == [name]
    card["allow_protected"] = [name]
    assert scope.evaluate_scope(tmp_path, card, "base", "fork", None)["status"] == "WARN"
    card["allowed_paths"] = []
    assert scope.evaluate_scope(tmp_path, card, "base", "fork", None)["details"]["forbidden_paths"] == [name]


def test_scope_reports_ignored_files_and_warns_only_outside_allowlist(tmp_path, monkeypatch):
    junk = ["ops/gates/__pycache__/gate.cpython-313.pyc", "outside/.pytest_cache/tag", "outside/orphan.pyc"]
    allowed = "design/test data.txt"
    outside = "outside/nested/ignored.txt"
    meta = tmp_path / "meta.json"
    meta.write_text('{"reasoning_effort": "high"}', encoding="utf-8")

    def stub_git(_, command, *args):
        if command != "status":
            return b""
        assert {"--ignored", "--porcelain=v1", "--untracked-files=all", "-z"} <= set(args)
        paths = [*junk, allowed, outside]
        return b"?? TASK.md\0" + b"".join(f"!! {path}\0".encode() for path in paths)

    monkeypatch.setattr(scope, "git", stub_git)
    card = {"allowed_paths": ["design/**"]}
    gate = scope.evaluate_scope(tmp_path, card, "base", "fork", meta)
    assert gate["status"] == "WARN"
    assert gate["details"]["ignored_paths"] == sorted([*junk, allowed, outside])
    assert gate["details"]["ignored_outside_allowed"] == [outside]
    assert gate["details"]["protected_changes"] == []
    card["allowed_paths"].append("outside/**")
    assert scope.evaluate_scope(tmp_path, card, "base", "fork", meta)["status"] == "PASS"


def test_scope_ignored_criteria_still_protected(tmp_path, monkeypatch):
    name = "ops/criteria/hidden.yaml"
    file = tmp_path / name
    file.parent.mkdir(parents=True)
    file.write_bytes(b"new protected file")
    def stub_git(_, command, *args):
        return b"!! ops/criteria/hidden.yaml\0" if command == "status" else b""

    monkeypatch.setattr(scope, "git", stub_git)
    card = {"allowed_paths": ["ops/**"], "allow_protected": ["ops/**"]}
    gate = scope.evaluate_scope(tmp_path, card, "base", "fork", None)
    assert gate["status"] == "FAIL"
    assert gate["details"]["ignored_paths"] == [name]
    assert gate["details"]["protected_changes"] == [name]


@pytest.mark.parametrize("value", ["null", "ops/gates/**", "[../ops/gates/**]"])
def test_scope_rejects_invalid_protected_patterns(tmp_path, value):
    card = tmp_path / "card.yaml"
    card.write_text(f"allowed_paths: []\nallow_protected: {value}\n", encoding="utf-8")
    with pytest.raises(InputError, match="allow_protected"):
        scope.read_card(card)


def test_scope_slash_aware_pattern_matching():
    assert scope.matches(["ops", "gates", "gate.py"], ["ops", "gates", "*.py"])
    assert not scope.matches(["ops", "gates", "nested", "gate.py"], ["ops", "gates", "*.py"])
    assert scope.matches(["ops", "gates", "nested", "gate.py"], ["ops", "gates", "**"])
    assert not scope.matches(["ops", "gates-old", "gate.py"], ["ops", "gates", "**"])
