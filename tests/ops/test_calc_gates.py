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
LEGACY = ROOT / "ops/calibration/w02_04_params.yaml"


@pytest.fixture
def criteria():
    return read_criteria(CRITERIA.read_bytes())["criteria"]


@pytest.fixture
def params():
    return load_yaml(EXAMPLE.read_bytes(), EXAMPLE)


def run_calc(tmp_path, path, *args):
    out = tmp_path / "gate_report.json"
    process = subprocess.run(
        [sys.executable, "-B", str(ROOT / "ops/gates/calc_gates.py"), "--params", str(path),
         "--criteria", str(CRITERIA), "--out", str(out), *args],
        check=False, capture_output=True, text=True,
    )
    return process.returncode, json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path, expected, code", [(EXAMPLE, "PASS", 0), (LEGACY, "FAIL", 1)])
def test_calibration_cli(tmp_path, path, expected, code):
    exit_code, report = run_calc(tmp_path, path)
    assert exit_code == code
    assert report["schema"] == "rev.gate_report/1"
    assert report["tool"] == "calc_gates"
    assert report["criteria_version"] == 1
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


def test_dose_minimum_stroke_is_informational(params, criteria):
    chamber = params["chamber"]
    chamber.update(approach_stroke_mm=120, in_die_density_kg_m3=1100)
    gate = calc.evaluate_dose(params, criteria)
    details = gate["details"]
    compressed_mm = 0.83e9 / (1100 * 150 * 60)
    fill_mm = 0.83e9 / (420 * 150 * 60)
    minimum_mm = 120 + fill_mm - compressed_mm + 93
    assert details["compression_stroke_mm"] == pytest.approx(fill_mm - compressed_mm)
    assert details["minimum_stroke_mm"] == pytest.approx(minimum_mm)
    assert details["minimum_stroke_ratio"] == pytest.approx(320 / minimum_mm)
    assert details["stroke_ratio"] == pytest.approx(320 / (fill_mm + 93))
    assert gate["status"] == "PASS"
    del chamber["approach_stroke_mm"], chamber["in_die_density_kg_m3"]
    details = calc.evaluate_dose(params, criteria)["details"]
    assert details["approach_stroke_mm"] == 0
    assert details["in_die_density_source"] == "product.density_kg_m3"


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
    params["drive"]["motor_kW"] = 30 * energy_kJ / (energy_kJ - 30 * 0.2)
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["details"]["average_power_kW"] == pytest.approx(30)
    assert gate["details"]["checks"]["average_power_limit"]
    assert not gate["details"]["checks"]["peak_drive_power_limit"]
    assert gate["status"] == "FAIL"
    params["drive"]["motor_kW"] += 0.001
    assert not calc.evaluate_cycle(params, criteria)["details"]["checks"]["average_power_limit"]


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
    assert not gate["details"]["checks"]["peak_drive_power_limit"]
    assert gate["details"]["checks"]["average_power_limit"]
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
    assert details["checks"]["pump_power_within_motor_rating"]


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
