"""Re-evaluate T-1.6 heat terms on the saved T-2.6 reference operating points."""

import json
from dataclasses import replace
from math import fsum, isclose, pi
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[2]


def interpolate(flow_L_min, points):
    (low_flow, low), (high_flow, high) = points
    assert low_flow <= flow_L_min <= high_flow
    return low + (flow_L_min - low_flow) * (high - low) / (high_flow - low_flow)


def losses(reference, trace, pilot_standby_kW, release_kJ, circulation_kW, allowance_kW):
    shaft = reference["reference"]
    cycle_s = shaft["cycle_s"]
    pump_kJ = trace["shaft_energy_kJ"]
    pilot_extra_kJ = shaft["pilot"]["pilot_incremental_shaft_kJ"]
    energy = trace["energy"]
    pilot_standby_kJ = pilot_standby_kW * cycle_s
    # T-2.6 has no separate zero-swash loss integral. Retain the combined residual.
    pump_loss_kJ = pump_kJ - energy["header_kJ"] - energy["bypass_kJ"] - pilot_standby_kJ
    assert pump_loss_kJ >= 0
    terms = {
        "pump_zero_stroke_internal_losses_and_coupling": pump_loss_kJ,
        "pilot_charge_leakage_and_return": pilot_standby_kJ + pilot_extra_kJ,
        "decompression": release_kJ,
        "normal_spill_and_transition_bypass": energy["bypass_kJ"],
        "working_line_and_valve_drops": energy["valves_kJ"] + energy["sharing_kJ"],
        "accumulator_paths": energy["charge_kJ"] - energy["boost_kJ"],
        "cylinder_friction_and_braking": energy["cylinder_friction_kJ"] + trace["damping_heat_kJ"],
        "prefill_and_rapid_float": energy["prefill_float_kJ"],
        "shaft_tolerance_and_extra_handover": shaft["shaft_energy_kJ"] - pump_kJ - pilot_extra_kJ,
        "cooling_circulation": circulation_kW * cycle_s,
        "inherited_worst_duty_allowance": allowance_kW * cycle_s,
    }
    assert isclose(terms["pilot_charge_leakage_and_return"] / cycle_s,
                   shaft["pilot"]["pilot_heat_kW"], abs_tol=1e-9)
    assert isclose(terms["accumulator_paths"], reference["accumulators"]["lp"]["charge_and_delivery_loss_kJ"],
                   abs_tol=1e-9)
    return {name: value / cycle_s for name, value in terms.items()}


def calculate():
    sys.path.insert(0, str(Path(__file__).with_name("cycle")))
    from run import HydraulicStudy, OperatingPoint, Scenario, read_json, read_yaml
    from drive import decompression

    from tank import oil_trajectory

    t26 = read_json("calc/T-2.6/results.json")
    t16 = read_json("calc/T-1.6/results.json")
    cfg16 = read_yaml("calc/T-1.6/sources.yaml")
    sources = yaml.safe_load(Path(__file__).with_name("sources.yaml").read_text(encoding="utf-8"))["sources"]
    selected = t26["variants"][t26["selected"]]
    scenario = Scenario(**selected["configuration"])
    study = HydraulicStudy()
    cfg = cfg16["revision"]["cooling"]
    cat = cfg16["catalogs"]["ASA0567"]
    allowance_kW = t16["heat_balance"]["T16_nominal_sources_kW"]["inherited_worst_duty_allowance"]
    cases = {}
    trajectories = {}
    cylinders = read_yaml("design/cylinders.t16.yaml")["cylinders"]
    points = {}
    reference_keys = ("reference", "operating_point", "accumulators")
    fault = cfg16["project"]["round2"]
    relief_bar = read_yaml("ops/criteria/design_criteria.yaml")["criteria"]["C-HYD-01"]["max_relief_bar"]
    compliance_L_per_L = fault["fault_compliance_multiplier"] * relief_bar * 1e5 / fault["fault_oil_bulk_modulus_Pa"]
    for case, saved in (("nominal", selected), ("adverse", t26["selected_sensitivity"]["combined"])):
        point = OperatingPoint(**{key: saved["operating_point"][key] for key in OperatingPoint.__dataclass_fields__})
        points[case] = point
        row, _, trace = study.replay(scenario, operating_point=point)
        for metric in ("cycle_s", "average_kW", "rms_kW", "shaft_energy_kJ"):
            assert isclose(row["reference"][metric], saved["reference"][metric], abs_tol=1e-9)
        assert row["prefill"] == {key: value for key, value in saved["prefill"].items()
                                  if not key.startswith("legacy_")}
        active_study, model, cylinder, *_ = study.configuration(scenario, operating_point=point)
        release = decompression(trace, model, cylinder, active_study.reference_sources)
        terms_kW = losses(row, trace, active_study.pilot["standby_shaft_bound_kW"],
                          release["effective_release_energy_kJ"], cfg["circulation_motor_kW"], allowance_kW)
        mean_delivery_L_min = fsum(step[1] * step[8] for step in trace["power_steps"]) / row["reference_cycle_s"]
        cases[case] = {key: row[key] for key in reference_keys} | dict(
            sources_kW=terms_kW, heat_kW=fsum(terms_kW.values()), decompression=release,
            main_delivery_mean_L_min=mean_delivery_L_min,
            main_delivery_peak_L_min=max(step[8] for step in trace["power_steps"]))
        trajectories[case] = oil_trajectory(trace, row, cylinders, study.sources, compliance_L_per_L)

    motor_trials = {}
    motor_limits = dict(cycle_nominal_s=5.904, cycle_adverse_s=6.193, rms_nominal_kW=29.987)
    speed_drop_rpm = points["nominal"].rpm - points["adverse"].rpm
    for tag in ("brook", "abb"):
        catalog = sources[tag]
        sync_rpm = 120 * catalog["frequency_Hz"] / catalog["poles"]
        trial = dict(limits=motor_limits, sync_rpm=sync_rpm, adverse_incremental_speed_drop_rpm=speed_drop_rpm)
        for name, drop_rpm in (("nominal", 0), ("adverse", speed_drop_rpm)):
            rpm = catalog["rated_rpm"] - drop_rpm
            result, _, _ = study.replay(scenario, operating_point=replace(points[name], rpm=rpm))
            shaft = result["reference"]
            peak_Nm = 1000 * shaft["peak_kW"] / (rpm * pi / 30)
            pullout_Nm = catalog["rated_Nm"] * catalog["pullout_ratio"]
            trial[name] = dict(rpm=rpm, slip_fraction=(sync_rpm - rpm) / sync_rpm,
                               cycle_s=shaft["cycle_s"], rms_kW=shaft["rms_kW"], average_kW=shaft["average_kW"],
                               peak_kW=shaft["peak_kW"], peak_Nm=peak_Nm, pullout_Nm=pullout_Nm,
                               pullout_to_peak_ratio=pullout_Nm / peak_Nm, integration=result["steps"])
        trial["cycle_power_pass"] = (
            trial["nominal"]["cycle_s"] <= motor_limits["cycle_nominal_s"]
            and trial["nominal"]["rms_kW"] <= motor_limits["rms_nominal_kW"]
            and trial["adverse"]["cycle_s"] <= motor_limits["cycle_adverse_s"])
        motor_trials[tag] = trial

    delta_K = cfg["oil_inlet_limit_C"] - cfg["ambient_C"]
    flow_L_min = cfg["circuit_flow_L_min"]
    branch_low_L_min = cfg["target_min_flow_per_module_L_min"]
    branch_high_L_min = flow_L_min - branch_low_L_min
    points = cat["performance_points_L_min_kW_K"]
    raw_kW = delta_K * fsum(interpolate(flow, points) for flow in (branch_low_L_min, branch_high_L_min))
    derating = (1 - cat["tolerance_fraction"]) * (1 - cfg["fouling_fraction"])
    dirty_kW = raw_kW * derating
    prior_cooling = t16["heat_balance"]["cooling"]
    assert isclose(dirty_kW, prior_cooling["dirty_capacity_kW"], abs_tol=1e-9)
    worst_heat_kW = max(case["heat_kW"] for case in cases.values())
    required_kW = max(26.43, cfg["minimum_point_kW"], cfg["heat_factor"] * worst_heat_kW)
    # Sensitivity with original loss fractions and only a changed shaft power.
    fixed_kW = cfg["circulation_motor_kW"] + allowance_kW
    for case, row in cases.items():
        origin_shaft_kW = t16["cycle"][f"revision_{case}"]["average_shaft_kW"]
        origin_heat_kW = t16["heat_balance"][f"{case}_heat_kW"]
        row["T16_proportional_sensitivity_heat_kW"] = fixed_kW + (origin_heat_kW - fixed_kW) * (
            row["reference"]["average_kW"] / origin_shaft_kW)
    sensitivity_required_kW = max(required_kW, cfg["heat_factor"] * max(
        row["T16_proportional_sensitivity_heat_kW"] for row in cases.values()))
    candidate = sources["asa_0927"]
    candidate_kW = interpolate(flow_L_min, candidate["performance_points_L_min_kW_K"]) * delta_K * derating
    installed_kW = selected["mass"]["installed_kW"]
    installed_limit_kW = read_yaml("ops/criteria/design_criteria.yaml")["criteria"]["C-PWR-01"]["max_installed_kW"]
    return dict(cases=cases, trajectories=trajectories, motor_trials=motor_trials,
                heat_factor=cfg["heat_factor"], worst_heat_kW=worst_heat_kW,
                cooling_required_kW=required_kW, proportional_sensitivity_required_kW=sensitivity_required_kW,
                cooling_dirty_kW=dirty_kW, cooling_margin_kW=dirty_kW - required_kW,
                cooling_sensitivity_margin_kW=dirty_kW - sensitivity_required_kW,
                cooling_raw_kW=raw_kW, air_C=cfg["ambient_C"], oil_limit_C=cfg["oil_inlet_limit_C"],
                fouling_fraction=cfg["fouling_fraction"], catalog_tolerance_fraction=cat["tolerance_fraction"],
                flow_L_min=flow_L_min, branch_flow_L_min_range=[branch_low_L_min, branch_high_L_min],
                installed_kW=installed_kW, fan_kW=cfg["modules"] * cat["fan_kW"],
                fan_limit_kW=installed_limit_kW - (installed_kW - cfg["modules"] * cat["fan_kW"]),
                installed_limit_kW=installed_limit_kW, circulation_kW=cfg["circulation_motor_kW"],
                cooler_candidate_asa0927_dirty_at_base_flow_kW=candidate_kW,
                dirty_capacity_kW_per_K=dirty_kW / delta_K,
                cooler_source=sources["asa_0567"]["url"], thermal_method=sources["thermal_method"]["url"])


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=True, allow_nan=False))
