"""Compare PC catalogue data and bound the load on the preferred 1.5 kW candidate."""
import json
from math import pi

from pc_branch import HERE, ROOT, T25B, analyse, dirty_duty_kW, load_yaml, viscosity_mm2_s
from pc_options import calculate as previous_candidates, linear


def calculate():
    sources = load_yaml(HERE / "sources.yaml")
    screen = sources["screen_inputs"]
    kf = sources["pc_t29b_inputs"]
    heat = load_yaml(T25B / "sources.yaml")["inputs"]
    design = ROOT / "design/hydraulics"
    station = load_yaml(design / "station.t25c.yaml")
    legacy = analyse(screen, heat, station, load_yaml(design / "T-1.6_circuit.yaml"))
    comparison = previous_candidates(legacy)["pc_options"]
    viscosity_table = screen["tellus_viscosity_T_C_mm2_s"]
    heat_curve = screen["gl180_heat_Q_L_min_kW"]
    cold, hot_42 = legacy["operating_points"][:2]
    viscous_slope = (cold["clean_dp_bar"] - hot_42["clean_dp_bar"]) / (
        cold["viscosity_mm2_s"] - hot_42["viscosity_mm2_s"])
    dp_correction_dirty_bar = hot_42["dirty_scenario_dp_bar"] - hot_42["clean_dp_bar"]

    def clean_dp180_bar(nu_mm2_s):
        return hot_42["clean_dp_bar"] + viscous_slope * (nu_mm2_s - hot_42["viscosity_mm2_s"])

    q_theory_L_min = kf["displacement_cm3_rev"] * kf["speed_rpm"] / 1000
    slip_L_min = q_theory_L_min - kf["flow_2bar_L_min"]
    max_motor_kW = kf["motor_rated_torque_Nm"] * 2 * pi * kf["speed_rpm"] / 60_000
    hot_rows = []
    for row in legacy["operating_points"][1:]:
        temp_C = row["temperature_C"]
        nu_mm2_s = row["viscosity_mm2_s"]
        # Use the 2 bar leakage and never award a flow gain for a larger viscosity.
        delivery_L_min = q_theory_L_min - slip_L_min * max(1, 34 / nu_mm2_s)
        safe_delivery_L_min = delivery_L_min * (1 - kf["catalogue_flow_downside_fraction"])
        for condition, field in (("clean", "clean_dp_bar"), ("dirty", "dirty_scenario_dp_bar")):
            reference_bar = row[field]
            dp_upper_bar = reference_bar * q_theory_L_min / 180
            dp_nom_bar = reference_bar * delivery_L_min / 180
            estimate_kW = linear(dp_nom_bar, (2, kf["shaft_2bar_kW"]), (4, kf["shaft_4bar_kW"]))
            hot_rows.append({
                "temperature_C": temp_C, "oil_mm2_s": nu_mm2_s, "condition": condition,
                "branch_dp_at_180_bar": reference_bar, "branch_dp_upper_bar": dp_upper_bar,
                "nominal_flow_L_min": delivery_L_min, "flow_screen_min_L_min": safe_delivery_L_min,
                "shaft_kW_extrapolated": estimate_kW, "shaft_kW_bound_from_2bar": kf["shaft_2bar_kW"],
            })
    start_C = kf["pc_start_enable_C"]
    start_nu = viscosity_mm2_s(start_C, viscosity_table)
    start_hot_path_dp_bar = (clean_dp180_bar(start_nu) + dp_correction_dirty_bar) * q_theory_L_min / 180
    installed_with_margin_kW = kf["shaft_2bar_kW"] * (1 + kf["motor_margin_fraction"])
    margin_kW = max_motor_kW - installed_with_margin_kW
    min_crack_bar, max_crack_bar = kf["cb_crack_required_range_bar"]
    worst_dp_hot_bar = max(row["branch_dp_upper_bar"] for row in hot_rows)
    min_flow_L_min = min(row["flow_screen_min_L_min"] for row in hot_rows)
    required_air_min_L_min = legacy["air_option_min_oil_L_min_legacy"]
    air_cfg = sources["pc_t29b_inputs"]["air"]
    air_rows = []
    for row in legacy["operating_points"][1:]:
        nu = row["viscosity_mm2_s"]
        # Keep the published 34 cSt common budget and add the positive oil-temperature correction.
        common_bar = air_cfg["common_dp_bar"] * q_theory_L_min / 180 + max(
            0, viscous_slope * (nu - 34)) * q_theory_L_min / 180
        flow_most_L_min = q_theory_L_min - required_air_min_L_min / 2
        air_matrix_bar = linear(flow_most_L_min, *air_cfg["matrix_Q_L_min_dp_bar"]) * max(1, nu / 34)
        air_rows.append({
            "temperature_C": row["temperature_C"], "common_bar_screen": common_bar,
            "matrix_bar_screen": air_matrix_bar, "total_bar_screen": common_bar + air_matrix_bar,
        })

    # Conditional upper bound. A locked-out pump consumes no shaft power during preheating.
    bypass_speed_ramp = {
        "pc_off_below_start_C": start_C,
        "trip_below_C": kf["pc_stop_below_C"],
        "preheat_source": "M1/P1 unloaded recirculation, ZU open, press and cycle isolated",
        "shaft_kW_preheating_PC_off": 0,
        "first_pc_start_viscosity_mm2_s": start_nu,
        "branch_dirty_dp_at_first_start_bar": start_hot_path_dp_bar,
        "shaft_kW_bound_at_first_pc_start": kf["shaft_2bar_kW"],
        "suction_and_discharge_differential_limit_bar": 2,
        "required_cb_override_plus_suction_bar_max": 2 - max_crack_bar,
        "shaft_kW_screen_if_enabled_at_20_and_CB_at_2bar": (
            kf["shaft_2bar_kW"] + screen_cold_factor(sources) * q_theory_L_min),
    }
    q_dirty_kW = dirty_duty_kW(heat, heat_curve, min_flow_L_min)
    # No candidate is released absent proof of installation-specific start and flow.
    return {
        "status": "HOLD_PC",
        "selected": None,
        "preferred_candidate": {
            "model": kf["pump_model"], "motor": kf["motor_model"], "motor_kW": kf["motor_rated_kW"],
            "catalogue_source": sources["sources"]["pc_kf180"], "speed_rpm": kf["speed_rpm"],
            "flow_tabulated_L_min": kf["flow_2bar_L_min"], "flow_screen_min_L_min": min_flow_L_min,
            "shaft_kW_hot_max_bound": kf["shaft_2bar_kW"], "shaft_kW_with_manufacturer_margin": installed_with_margin_kW,
            "motor_kW_at_map_speed_from_rated_torque": max_motor_kW, "remaining_margin_kW": margin_kW,
            "dp_hot_bar_max": worst_dp_hot_bar, "q_dirty_kW": q_dirty_kW,
            "air_min_L_min_each": required_air_min_L_min / 2,
            "air_equal_split_at_min_screen_L_min": min_flow_L_min / 2,
            "air_allowable_imbalance_from_equal_split_L_min": min_flow_L_min / 2 - required_air_min_L_min / 2,
            "air_pressure_screen": air_rows, "hot_operating_points": hot_rows,
            "cb_crack_target_bar": (min_crack_bar + max_crack_bar) / 2,
            "cb_crack_required_range_bar": [min_crack_bar, max_crack_bar],
            "cb_closed_water_hot_in_static_screen": worst_dp_hot_bar < min_crack_bar,
            "cb_closed_air_hot_in_static_screen": max(row["total_bar_screen"] for row in air_rows) < min_crack_bar,
            "minimum_oil_delivery_L_min_required_water": legacy["water_option_min_oil_L_min_screen"],
            "pump_mass_kg": kf["pump_mass_kg"], "motor_mass_kg": kf["motor_mass_kg"],
            "pump_and_motor_mass_kg": kf["pump_mass_kg"] + kf["motor_mass_kg"],
            "start": bypass_speed_ramp,
            "conditions_to_verify": [
                "CB static opening band and full-flow override including suction and CD losses at 33–55 C",
                "Pump torque during acceleration through the speed ramp and maximum pump speed 950 rpm",
                "Catalog reduction below 30 mm²/s not quantified; verify delivered flow at 55 C",
                "Balance air split to the simultaneous FT1 and FT2 minima with CB closed",
                "Confirm circulation Δp and preheating rate on the installed skid",
            ],
        },
        "other_candidates": comparison,
        "ambient_20C_case_source": sources["sources"]["project_cooling_review"],
        "site_oil_minimum_start_C": None,
    }


def screen_cold_factor(sources):
    return sources["pc_catalogue_inputs"]["kf_cold_fv_upper_kW_per_L_min"]


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=False, indent=2))

