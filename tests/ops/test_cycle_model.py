"""Physical G-CYCLE contract, conservation and physical sensitivity checks."""

import builtins
from copy import deepcopy
import json
from pathlib import Path

import pytest

from ops.gates import calc_gates as calc
from ops.gates.cycle_model.qualification import input_violations
from ops.gates.gate_report import InputError, load_yaml, read_criteria

ROOT = Path(__file__).resolve().parents[2]
CRITERIA = ROOT / "ops/criteria/design_criteria.yaml"
PARAMS = {
    "T-2.2d": ROOT / "design/params.t22d.yaml",
    "A": ROOT / "calc/T-2.6/params/params.t26a.yaml",
}
GLOBAL_TIMES = {
    ("process", "feed_s"), ("process", "hold_s"), ("process", "unload_s"),
    ("process", "valve_switch_s"), ("process", "handover_interlock_s"),
    ("pump", "destroke_s"), ("pump", "onstroke_s"), ("pump", "control_delay_s"),
    ("mp", "changeover_allowance_s"), ("pilot", "reservation_window_s"),
    ("pilot", "valve_response_s"), ("pilot", "idle_charge_reserve_s"),
}


def read_params(path):
    params = load_yaml(path.read_bytes(), path)
    calc.validate_params(params)
    return params


@pytest.fixture(scope="module")
def criteria():
    return read_criteria(CRITERIA.read_bytes())["criteria"]


@pytest.fixture(scope="module")
def calibration():
    return json.loads((ROOT / "ops/calibration/cycle_t04.json").read_bytes())


@pytest.fixture(scope="module")
def nominal(criteria):
    cases = {name: read_params(path) for name, path in PARAMS.items()}
    # The calculation has all its inputs in memory by this point.
    def deny_calc(original):
        def checked(file, *args, **kwargs):
            if isinstance(file, (str, Path)):
                assert not Path(file).resolve().is_relative_to(ROOT / "calc"), file
            return original(file, *args, **kwargs)
        return checked

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, "open", deny_calc(Path.open))
        patch.setattr(builtins, "open", deny_calc(builtins.open))
        gates = {name: calc.evaluate_cycle(params, criteria) for name, params in cases.items()}
    return cases, gates


@pytest.mark.parametrize("name", list(PARAMS))
def test_reference_contract(nominal, calibration, name):
    _, gates = nominal
    gate = gates[name]
    details = gate["details"]
    ref = calibration["nominal"][name]["ref"]
    assert details["method"] == "reference_model"
    assert details["legacy_cycle_ignored"]
    assert details["checks"]["cycle_model_inputs_qualified"]
    assert details["cycle_model_input_violations"] == []
    assert 0 <= gate["value"] - ref["cycle_s"] <= .10
    assert details["total_motor_energy_kJ"] >= ref["shaft_energy_kJ"] - .10
    assert details["rms_power_kW"] >= ref["rms_kW"] - .01
    assert details["peak_drive_power_kW"] == pytest.approx(ref["peak_kW"])
    assert details["total_motor_energy_kJ"] == pytest.approx(details["average_power_kW"] * gate["value"])
    assert details["squared_power_time_kW2_s"] == pytest.approx(details["rms_power_kW"]**2 * gate["value"])
    assert details["integration"]["adjacent_delta_s"] <= .005
    assert details["checks"]["sequence_interlocks"]
    assert details["checks"]["actuator_travel_limits"]
    assert details["checks"]["actuators_return_to_start"]
    assert details["checks"]["accumulator_pressure_covered"]


def test_reference_dispatch_can_omit_legacy_cycle(nominal, criteria, monkeypatch):
    cases, gates = nominal
    params = deepcopy(cases["A"])
    before = params.pop("cycle")
    calc.validate_params(params)
    monkeypatch.setattr(calc, "evaluate_legacy_cycle", lambda *_: pytest.fail("unexpected legacy dispatch"))
    # The adapter exports a fresh report from physical results even when a
    # completely different legacy cycle is present alongside the model.
    recorded = gates["A"]["details"]
    adapter_fields = {"method", "legacy_cycle_ignored", "checks", "warnings", "cycle_model_input_violations"}
    output = {k: v for k, v in recorded.items() if k not in adapter_fields}
    monkeypatch.setattr(calc, "run_reference_cycle", lambda *_: output)
    assert calc.evaluate_cycle(params, criteria)["value"] == gates["A"]["value"]
    assert not calc.evaluate_cycle(params, criteria)["details"]["legacy_cycle_ignored"]
    params["cycle"] = [before[-1]]
    assert calc.evaluate_cycle(params, criteria)["value"] == gates["A"]["value"]


def physical_keys(value, path=()):
    if isinstance(value, dict):
        for name, child in value.items():
            yield (*path, name)
            yield from physical_keys(child, (*path, name))
    elif isinstance(value, list):
        for child in value:
            yield from physical_keys(child, path)


def test_params_only_accept_physical_inputs():
    paths = [*PARAMS.values(), *sorted((ROOT / "ops/calibration/cycle_t04").glob("*.params.yaml"))]
    assert len(paths) >= 10
    for path in paths:
        model = read_params(path)["cycle_model"]
        for key_path in physical_keys(model):
            field = key_path[-1]
            if field.endswith("_s") and not field.endswith("_mm2_s"):
                assert key_path in GLOBAL_TIMES
            assert not any(word in field for word in
                           ("duration", "start_delay", "command_time", "speed_mm", "speed_m_s",
                            "energy", "phase_table", "motion_events", "start_s", "end_s"))
    params = read_params(PARAMS["A"])
    for bad_field in ("press_duration_s", "press_speed_mm_s", "press_start_s", "press_pressure_bar", "energy_kJ"):
        params["cycle_model"]["process"][bad_field] = 1.
        with pytest.raises(InputError, match=bad_field):
            calc.validate_params(params)
        del params["cycle_model"]["process"][bad_field]


@pytest.mark.parametrize("scope, key, factor, increment, lower_s, upper_s", [
    ("main_cylinder", "stroke_mm", 1.10, 0, .08, .8),
    ("pump", "delivery_fraction", .90, 0, .03, .9),
    ("pump", "main_shaft_limit_kW", 1, -2, .03, .9),
    ("process", "valve_switch_s", 1, .02, .08, .35),
])
def test_physical_mutations_increase_cycle(nominal, criteria, scope, key, factor, increment, lower_s, upper_s):
    cases, gates = nominal
    mutated = deepcopy(cases["A"])
    row = mutated[scope] if scope == "main_cylinder" else mutated["cycle_model"][scope]
    row[key] = factor * row[key] + increment
    calc.validate_params(mutated)
    changed = calc.evaluate_cycle(mutated, criteria)
    assert changed["details"]["feasible"]
    assert lower_s <= changed["value"] - gates["A"]["value"] <= upper_s
    if key == "stroke_mm":
        assert not changed["details"]["checks"]["actuator_travel_limits"]


@pytest.mark.parametrize("section, changes, direction", [
    ("process", {"valve_switch_s": .03}, ">="),
    ("process", {"hold_s": .10, "unload_s": .10}, ">="),
    ("process", {"hold_s": .05}, ">="),
    ("oil", {"bulk_modulus_Pa": 2.8e9}, "<="),
    ("mechanics", {"cam_resistance_N": 31672.44772222222 / 2, "pre_return_resistance_N": 6182.73192948 / 2,
                   "die_ejection_N": 50_000}, ">="),
    ("material", {"scale_MPa": 56.89401598364152 / 2, "lateral_K": .225, "wall_mu": .125}, ">="),
    ("outlet", {"crumbs_N": 2500}, ">="),
    ("lp", {"delivery_L_min": 360}, "<="),
    ("valves", {"main_metering_L_min": 886.6831105491832 * 1.3}, "<="),
    ("valves", {"line_loss_bar": [2, 1.5, 2]}, ">="),
    ("pump", {"delivery_fraction": 1.1, "regulator_fraction": 1.1}, "<="),
    ("pump", {"motor_rpm": 1490, "main_shaft_limit_kW": 37}, "<="),
    ("pump", {"rated_motor_rpm": 1490, "nominal_regulator_kW": 34}, "<="),
])
def test_unqualified_reference_inputs_fail(criteria, monkeypatch, section, changes, direction):
    params = read_params(PARAMS["A"])
    params["cycle_model"][section].update(changes)
    calc.validate_params(params)
    monkeypatch.setattr(calc, "run_reference_cycle", lambda *_: pytest.fail("unqualified model was simulated"))
    gate = calc.evaluate_cycle(params, criteria)
    details = gate["details"]
    assert gate["status"] == "FAIL"
    assert gate["value"] is None
    assert not details["checks"]["cycle_model_inputs_qualified"]
    violations = details["cycle_model_input_violations"]
    assert {row["field"].split("[")[0] for row in violations} == {
        f"cycle_model.{section}.{key}" for key in changes
    }
    assert all(row["operator"] == direction and row["source"] and row["field"] in row["message"]
               for row in violations)
    if "main_metering_L_min" in changes:
        assert violations[0]["actual"] == pytest.approx(.24 * 1.3)
        assert "m/s" in violations[0]["message"]


def test_metering_limits_use_geometry_and_regeneration():
    params = read_params(PARAMS["A"])
    params["drive"]["slide_gate_cylinder"]["bore_mm"] = 80
    assert [row["field"] for row in input_violations(params)] == ["cycle_model.valves.gate_metering_L_min"]
    params = read_params(PARAMS["T-2.2d"])
    params["cycle_model"]["rapid_pair"]["rapid_regeneration"] = True
    assert [row["field"] for row in input_violations(params)] == ["cycle_model.valves.rapid_feed_metering_L_min"]


def test_pump_curve_checks_intermediate_knots_and_absorbed_power():
    params = read_params(PARAMS["A"])
    curve = params["cycle_model"]["pump"]["curve"]
    curve.insert(2, [75, 267, 36, 3.5])
    curve[3][3] = 3.9
    assert [row["field"] for row in input_violations(params)] == [
        "cycle_model.pump.curve@75bar.full_flow_L_min", "cycle_model.pump.curve@100bar.zero_swash_kW",
    ]
    curve[2][1] = 266
    curve[3][3] = 4.1
    assert input_violations(params) == []


def test_conservative_inputs_and_holdouts_are_qualified(criteria, nominal):
    cases, _ = nominal
    params = deepcopy(cases["A"])
    params["cycle_model"]["process"]["valve_switch_s"] = .085
    gate = calc.evaluate_cycle(params, criteria)
    assert gate["details"]["checks"]["cycle_model_inputs_qualified"]
    assert gate["details"]["cycle_model_input_violations"] == []
    paths = sorted((ROOT / "ops/calibration/cycle_t04").glob("*.params.yaml"))
    assert len(paths) >= 8
    for path in paths:
        assert input_violations(read_params(path)) == [], path


def test_reference_rejects_required_pressure_above_criterion(criteria):
    params = read_params(PARAMS["A"])
    limits = deepcopy(criteria)
    limits["C-HYD-01"]["max_working_bar"] = 200.
    gate = calc.evaluate_cycle(params, limits)
    assert gate["status"] == "FAIL"
    assert gate["value"] is None
    details = gate["details"]
    assert details["limit_working_bar"] == 200.
    assert details["required_peak_working_bar"] > 200.
    assert not details["checks"]["working_pressure_limit"]
