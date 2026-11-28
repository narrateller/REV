"""Screen the inherited KF125/GL180 branch against the T-2.9 stop condition."""
import json
from math import log10
from pathlib import Path
import sys

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
T25B = ROOT / "calc/T-2.5b"
sys.path.insert(0, str(T25B))
import cooler


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def viscosity_mm2_s(temperature_C, table):
    # D341 Walther form. Anchor the cold result at the additional SDS point.
    indices = (0, 1) if temperature_C <= table[1][0] else (1, 2)
    points = [(log10(table[i][0] + 273.15), log10(log10(table[i][1] + 0.7)))
              for i in indices]
    ordinate = cooler.interpolate(log10(temperature_C + 273.15), points)
    return 10 ** (10 ** ordinate) - 0.7


def pump_at_34_mm2_s(row, dp_bar):
    rpm, q2_L_min, p2_kW, q4_L_min, p4_kW = row
    q_L_min = cooler.interpolate(dp_bar, ((2, q2_L_min), (4, q4_L_min))) if dp_bar >= 2 else None
    power_kW = p2_kW + (p4_kW - p2_kW) * (dp_bar - 2) / 2
    return {
        "speed_rpm": rpm, "flow_L_min": q_L_min, "shaft_kW": power_kW,
        "pressure_bar": dp_bar, "below_catalogue_pressure_range": dp_bar < 2,
    }


def dirty_duty_kW(inputs, heat_curve, q_L_min):
    bracket = next((a, b) for a, b in zip(heat_curve, heat_curve[1:])
                   if a[0] <= q_L_min <= b[0])
    clean_kW = cooler.interpolate(q_L_min, bracket)
    cat = inputs["catalog_bowman"]
    catalogue_delta_K = cat["catalogue_hot_inlet_C"] - cat["catalogue_cold_inlet_C"]
    site_delta_K = inputs["oil_inlet_C"] - inputs["water_inlet_C"]
    project_factor_kW_K = clean_kW / catalogue_delta_K * inputs["catalog_factor"] * inputs["fouling_factor"]
    tema = cooler.dirty_conductance(inputs | {"oil_flow_L_min": q_L_min}, cat["tube_area_m2"],
                                    clean_kW, catalogue_delta_K, inputs["oil_cp_kJ_kg_K"])
    return min(project_factor_kW_K, *(row["dirty_kW_K"] for row in tema.values())) * site_delta_K


def analyse(config, inputs, station, circuit):
    pump_rows = config["kf125_at_34_mm2_s"]
    design_row = pump_rows[-1]
    table = config["tellus_viscosity_T_C_mm2_s"]
    heat_curve = config["gl180_heat_Q_L_min_kW"]
    shaft_limit_kW = inputs["pc_motor_kW"]
    nominal = cooler.calculate(inputs)
    q_nom_L_min = inputs["oil_flow_L_min"]
    # Fit one viscous component of the branch to the independent 20 °C review.
    # The review treats the T-2.5b nominal pressure as representative of about 57 °C.
    reference_C = config["t25b_nominal_dp_reference_oil_C"]
    ref_nu_mm2_s = viscosity_mm2_s(reference_C, table)
    p_nom_bar = nominal["oil_pressure"]["total_dp_bar"]
    p_cold_bar = config["cold_review_dp_bar_at_20C"]
    slope_bar_per_mm2_s = (p_cold_bar - p_nom_bar) / (viscosity_mm2_s(20, table) - ref_nu_mm2_s)
    pressure_rows = []
    for temperature_C in (20, 42, 45, 55):
        nu_mm2_s = viscosity_mm2_s(temperature_C, table)
        clean_bar = p_nom_bar + slope_bar_per_mm2_s * (nu_mm2_s - ref_nu_mm2_s)
        # Explicit sensitivity on published shell loss. No measured dirty curve.
        dirty_bar = clean_bar + nominal["oil_pressure"]["catalogue_cooler_dp_bar"] * (
            config["dirty_shell_dp_multiplier_scenario"] - 1)
        pressure_rows.append({
            "temperature_C": temperature_C, "viscosity_mm2_s": nu_mm2_s,
            "clean_dp_bar": clean_bar, "dirty_scenario_dp_bar": dirty_bar,
            "clean_legacy_efficiency_shaft_kW": q_nom_L_min * clean_bar / (600 * inputs["pc_efficiency_floor"]),
            "clean_KF125_34_mm2_s_pressure_only_kW": pump_at_34_mm2_s(design_row, clean_bar)["shaft_kW"],
            "dirty_KF125_34_mm2_s_pressure_only_kW": pump_at_34_mm2_s(design_row, dirty_bar)["shaft_kW"],
        })
    cb_rows = [{
        "crack_bar": cb_bar,
        "closed_at_42_to_55_clean_ideal": all(row["clean_dp_bar"] < cb_bar for row in pressure_rows[1:]),
        "closed_at_42_to_55_dirty_scenario_ideal": all(row["dirty_scenario_dp_bar"] < cb_bar for row in pressure_rows[1:]),
        "opens_at_20_clean_ideal": pressure_rows[0]["clean_dp_bar"] > cb_bar,
        "KF125_34_mm2_s_shaft_at_crack_kW": pump_at_34_mm2_s(design_row, cb_bar)["shaft_kW"],
    } for cb_bar in config["cb_setpoints_to_screen_bar"]]
    required_kW = nominal["heat"]["required_kW"]
    lower_L_min, upper_L_min = heat_curve[0][0], q_nom_L_min
    for _ in range(48):
        test_L_min = (lower_L_min + upper_L_min) / 2
        if dirty_duty_kW(inputs, heat_curve, test_L_min) < required_kW:
            lower_L_min = test_L_min
        else:
            upper_L_min = test_L_min
    pump_points = [pump_at_34_mm2_s(row, dp_bar) for row in pump_rows for dp_bar in (0, 2, 4)]
    zero_dp = pump_at_34_mm2_s(design_row, 0)
    zero_dp_speed_limit_rpm = shaft_limit_kW / zero_dp["shaft_kW"] * design_row[0]
    geom_displacement_cm3_rev = 125
    zero_dp_flow_limit_L_min = zero_dp_speed_limit_rpm * geom_displacement_cm3_rev / 1000
    min_air_L_min = sum(circuit["elements"][f"FT{i}"]["minimum_L_min"] for i in (1, 2))
    installed = station["cooling"]
    maximum_installed_kW = 34.2
    with_air_kW = installed["installed_with_air_option_kW"]
    return {
        "status": "STOP_PC",
        "shaft_limit_kW": shaft_limit_kW,
        "operating_points": pressure_rows,
        "cb_scenarios": cb_rows,
        "catalogue_and_extrapolated_points_at_34_mm2_s": pump_points,
        "zero_dp_flow_limit_L_min_extrapolated": zero_dp_flow_limit_L_min,
        "zero_dp_speed_limit_rpm_extrapolated": zero_dp_speed_limit_rpm,
        "q_dirty_reference_kW": nominal["heat"]["dirty_kW"],
        "q_dirty_at_120_L_min_kW": dirty_duty_kW(inputs, heat_curve, 120),
        "q_dirty_at_150_L_min_kW": dirty_duty_kW(inputs, heat_curve, 150),
        "q_dirty_required_kW": required_kW,
        "water_option_min_oil_L_min_screen": upper_L_min,
        "air_option_min_oil_L_min_legacy": min_air_L_min,
        "installed_limit_kW": maximum_installed_kW,
        "installed_base_kW": installed["installed_base_kW"],
        "installed_with_air_option_kW": with_air_kW,
        "pc_rating_limit_from_installed_budget_kW": maximum_installed_kW - with_air_kW + shaft_limit_kW,
        "installed_with_air_and_pc_0p75_kW": with_air_kW - shaft_limit_kW + 0.75,
        "installed_with_air_and_pc_2p2_kW": with_air_kW - shaft_limit_kW + 2.2,
        "KF125_motor_at_2bar_with_catalogue_margin_kW": design_row[2] * 1.15,
    }


def main():
    config = load_yaml(HERE / "sources.yaml")["screen_inputs"]
    inputs = load_yaml(T25B / "sources.yaml")["inputs"]
    station = load_yaml(ROOT / "design/hydraulics/station.t25c.yaml")
    circuit = load_yaml(ROOT / "design/hydraulics/T-1.6_circuit.yaml")
    results = analyse(config, inputs, station, circuit)
    (HERE / "results.json").write_text(json.dumps({"pc_branch": results}, ensure_ascii=False, indent=2,
                                                 allow_nan=False) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
