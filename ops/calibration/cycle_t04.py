"""Replay G-CYCLE on T-2.6 physical input variants and compare to saved results."""

import argparse
from copy import deepcopy
from itertools import combinations
import json
from math import pi
from pathlib import Path
import sys
from time import perf_counter

import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from ops.gates.calc_gates import evaluate_cycle, validate_params
from ops.gates.gate_report import load_yaml, read_criteria


A_KEY = "A_combined_NG50_33p25_kW_50ms_AX"
BASE_PATH = ROOT / "design/params.t22d.yaml"
A_PATH = ROOT / "calc/T-2.6/params/params.t26a.yaml"
CRITERIA_PATH = ROOT / "ops/criteria/design_criteria.yaml"
HOLDOUT_DIR = HERE / "cycle_t04"
OUT_PATH = HERE / "cycle_t04.json"
REFERENCE_PATH = ROOT / "calc/T-2.6/results.json"
POWER_FIELDS = dict(cycle_s="cycle_s", shaft_energy_kJ="total_motor_energy_kJ",
                    rms_kW="rms_power_kW", peak_kW="peak_drive_power_kW")
LP_RETURN = ["return", "pre_up", "pre_down", "gate_open", "gate_close"]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def physical_holdouts():
    """The only case switches are T-2.6 Scenario and OperatingPoint inputs."""
    origin = load_yaml(A_PATH.read_bytes(), A_PATH)
    rapid = origin["cycle_model"]["rapid_pair"]
    cap_flow_per_m_s = 60000 * rapid["count"] * pi * (rapid["bore_mm"] / 2000)**2
    rod_flow_per_m_s = 60000 * rapid["count"] * pi * (rapid["rod_mm"] / 2000)**2
    s26 = load_yaml((ROOT / "calc/T-2.6/sources.yaml").read_bytes(), "T-2.6/sources.yaml")
    inherited = load_yaml((ROOT / "calc/T-2.6/cycle/sources.yaml").read_bytes(), "T-2.6/cycle/sources.yaml")
    nominal_early = inherited["engineering_inputs"]
    cats = s26["catalogs"]
    adverse = s26["round2"]["adverse"]
    mp_source = s26["study"]["mp"]
    rephased_ax_s = s26["study"]["ax_idle_reserve_s"]
    default_regulator_kW = origin["cycle_model"]["pump"]["nominal_regulator_kW"]

    rapid_metering = {
        "feed": ("rapid_approach_m_s", cap_flow_per_m_s, "поршней 2 × Ø90 мм (без регенерации)"),
        "out": ("rapid_eject_m_s", cap_flow_per_m_s, "поршней 2 × Ø90 мм"),
        "back": ("rapid_return_m_s", cap_flow_per_m_s - rod_flow_per_m_s, "колец 2 × Ø90/50 мм"),
    }

    def variant(*, metering=(), **changes):
        values = {"pump.main_shaft_limit_kW": default_regulator_kW, **changes}
        settings = {key: (value, "T-2.6/run.py Scenario and T-2.6/sources.yaml") for key, value in values.items()}
        for route in metering:
            key, flow_per_m_s, area_note = rapid_metering[route]
            speed_m_s = nominal_early[key]
            note = (f"Ограничение скорости {speed_m_s:.2f} м/с × площадь {area_note} "
                    f"({flow_per_m_s / 60000:.8f} м²); calc/T-2.6/cycle/sources.yaml engineering_inputs.{key}.")
            settings[f"valves.rapid_{route}_metering_L_min"] = (flow_per_m_s * speed_m_s, note)
        return settings

    no_rapid_regen = {
        "rapid_pair.rapid_regeneration": False,
        "rapid_pair.regen_pilot_shift_L": 0.,
        "rapid_pair.switch_force_N": nominal_early["prefill_fast_to_regen_force_N"],
        "valves.main_regen_changeover_bar": nominal_early["regen_switch_bar"],
    }
    legacy_mf_L_min = cats["wrce"]["mf_NG50_single_B_L_min"]
    unmodified_pilot = {
        "pilot.reservation_window_s": .16,
        "pilot.idle_charge_reserve_s": 0.,
    }
    mp = {key: mp_source[key] for key in ("precharge_bar", "low_bar", "high_bar", "delivery_L_min", "cycle_budget_L")}
    mp.update(shell_L=cats["mp"]["shell_L"], exponent=nominal_early["accumulator_polytropic_exponent"],
              routes=["prefill", "return"], changeover_allowance_s=mp_source["tail_changeover_allowance_s"],
              pilot_shift_L=4 * cats["regen"]["lc25_E_pilot_mL"] / 1000)
    cases = {
        "A_existing": variant(metering=("feed", "out", "back"), **no_rapid_regen, **unmodified_pilot, **{
            "rapid_pair.vr_exhaust_curve": False,
            "valves.mf_rated_L_min": legacy_mf_L_min, "lp.routes": LP_RETURN,
        }),
        "A_prefill_and_LP": variant(metering=("feed",), **no_rapid_regen, **unmodified_pilot),
        "A_combined_no_pilot_reserve": variant(**{"pilot.idle_charge_reserve_s": 0.}),
        "A_combined_NG50_33_kW": variant(**{"pump.main_shaft_limit_kW": 33., "pilot.idle_charge_reserve_s": .110}),
        "A_combined_and_MP": variant(mp=mp, **{"pilot.idle_charge_reserve_s": rephased_ax_s}),
        "A_combined_NG63": variant(**{
            "pilot.idle_charge_reserve_s": rephased_ax_s,
            "valves.mf_rated_L_min": cats["wrce"]["mf_NG63_single_B_L_min"],
            "valves.mf_extra_pilot_shift_L": 2 * (cats["wrce"]["mf_NG63_pilot_mL"] - cats["wrce"]["mf_NG50_pilot_mL"]) / 1000,
        }),
    }
    sensitivity = {
        "DFE1_minus_5_percent": {"pump.regulator_fraction": adverse["regulator_fraction"]},
        "valves_85_ms": {"process.valve_switch_s": adverse["valve_s"][1]},
        "combined": {
            "pump.regulator_fraction": adverse["regulator_fraction"], "pump.motor_rpm": adverse["rpm"][0],
            "process.valve_switch_s": adverse["valve_s"][1], "process.unload_s": adverse["unload_s"],
            "oil.temperature_C": s26["round2"]["oil"]["hot_C"],
        },
        "legacy_0p45_bar_derated": {
            "tank.gauge_bar": s26["round2"]["suction"]["legacy_tank_gauge_bar"], "tank.band_bar": 0.,
            "tank.enforce_saturation_reserve": True,
        },
    }
    cases.update({name: {path: (value, "T-2.6/run.py OperatingPoint and T-2.6/sources.yaml")
                         for path, value in changes.items()} for name, changes in sensitivity.items()})
    return cases


def apply_changes(params, changes):
    expected = deepcopy(params)
    for field, (value, _) in changes.items():
        path = field.split(".")
        parent = expected["cycle_model"]
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = value
    return expected


def render_variants():
    """Copy A verbatim, replacing only changed physical settings and their source notes."""
    source = A_PATH.read_text(encoding="utf-8")
    model = next(node for key, node in yaml.compose(source).value if key.value == "cycle_model")
    model_lines = {}
    for key, node in model.value:
        if isinstance(node, yaml.MappingNode):
            model_lines.update({f"{key.value}.{field.value}": field.start_mark.line for field, _ in node.value})
        else:
            model_lines[key.value] = key.start_mark.line
    original = load_yaml(A_PATH.read_bytes(), A_PATH)
    HOLDOUT_DIR.mkdir(exist_ok=True)
    for name, changes in physical_holdouts().items():
        lines = source.splitlines()
        for field, (value, note) in changes.items():
            key = field.rsplit(".", 1)[-1]
            i = model_lines[field]
            indent = len(lines[i]) - len(lines[i].lstrip())
            text = yaml.safe_dump(value, default_flow_style=True, width=1000, sort_keys=False).splitlines()[0]
            lines[i] = f"{' ' * indent}{key}: {text}  # {note}"
        content = ("\n".join(lines) + "\n").encode("utf-8")
        output = HOLDOUT_DIR / f"{name}.params.yaml"
        assert load_yaml(content, output) == apply_changes(original, changes)
        output.write_bytes(content)


def compare_case(path, reference, criteria, *, phases=False):
    params = load_yaml(path.read_bytes(), path)
    validate_params(params)
    start = perf_counter()
    gate = evaluate_cycle(params, criteria)
    elapsed_s = perf_counter() - start
    details = gate["details"]
    assert details["checks"]["cycle_model_inputs_qualified"], (path, details["cycle_model_input_violations"])
    assert details["method"] == "reference_model" and details["feasible"], (path, gate)
    measured = {key: details[name] for key, name in POWER_FIELDS.items()}
    known = {key: reference["reference"][key] for key in POWER_FIELDS}
    row = dict(params=path.relative_to(ROOT).as_posix(), gate_status=gate["status"], gate=measured, ref=known,
               delta={key: measured[key] - known[key] for key in POWER_FIELDS},
               integration_delta_s=details["integration"]["adjacent_delta_s"])
    if phases:
        reference_events = reference["motion_events"]
        row["motion_elapsed_delta_s"] = {
            name: (event["end_s"] - event["start_s"])
            - (reference_events[name]["end_s"] - reference_events[name]["start_s"])
            for name, event in details["phases"].items()
        }
        row["grids"] = details["integration"]["grids"]
    return row, elapsed_s


def compare():
    criteria = read_criteria(CRITERIA_PATH.read_bytes())["criteria"]
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    nominal, holdout, runtime = {}, {}, {}
    for name, path, ref in (("T-2.2d", BASE_PATH, reference["base"]),
                            ("A", A_PATH, reference["variants"][A_KEY])):
        nominal[name], runtime[name] = compare_case(path, ref, criteria, phases=True)
    origin = load_yaml(A_PATH.read_bytes(), A_PATH)
    for name, changes in physical_holdouts().items():
        path = HOLDOUT_DIR / f"{name}.params.yaml"
        if load_yaml(path.read_bytes(), path) != apply_changes(origin, changes):
            raise ValueError(f"{path}: differs from A beyond the declared physical changes")
        section = "variants" if name.startswith("A_") else "selected_sensitivity"
        holdout[name], runtime[name] = compare_case(path, reference[section][name], criteria)
    order_errors = [
        [left, right] for (left, a), (right, b) in combinations(holdout.items(), 2)
        if abs(a["ref"]["cycle_s"] - b["ref"]["cycle_s"]) > .03
        and ((a["ref"]["cycle_s"] - b["ref"]["cycle_s"])
             * (a["gate"]["cycle_s"] - b["gate"]["cycle_s"])) <= 0.
    ]
    cycle_deltas = [row["delta"]["cycle_s"] for row in holdout.values()]
    checks = dict(
        nominal=all(0 <= row["delta"]["cycle_s"] <= .10 and row["delta"]["shaft_energy_kJ"] >= -.10
                    and row["delta"]["rms_kW"] >= -.01 for row in nominal.values()),
        holdout_bounds=len(holdout) >= 8 and all(-.02 <= delta <= .15 for delta in cycle_deltas),
        holdout_order=not order_errors,
        grids=all(row["integration_delta_s"] <= .005 for row in (nominal | holdout).values()),
    )
    result = dict(schema="rev.cycle_calibration/1", nominal=nominal, holdout=holdout, checks=checks,
                  holdout_summary=dict(n=len(holdout), min_delta_s=min(cycle_deltas), max_delta_s=max(cycle_deltas),
                                       order_errors=order_errors))
    return result, runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-params", action="store_true", help="Rebuild control inputs from A and design sources")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)
    if args.write_params:
        render_variants()
    data, runtime = compare()
    write_json(args.out, data)
    print(json.dumps(dict(checks=data["checks"], runtime_s=runtime), indent=2))
    return int(not all(data["checks"].values()) or max(runtime.values()) > 60)


if __name__ == "__main__":
    raise SystemExit(main())

