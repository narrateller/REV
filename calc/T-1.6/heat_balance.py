"""Heat load and cooler selection at the oil inlet and ambient design point."""
from math import fsum


def heat_sources(run, pilot_heat_kW, extra_handover_s, decompression_energy_kJ, circulation_kW):
    duration_s = run["cycle_s"] + extra_handover_s
    energy = run["energy"]
    pilot_kJ = pilot_heat_kW * duration_s
    pump_residual_kJ = (run["shaft_energy_kJ"] - energy["header_kJ"] - energy["bypass_kJ"]
                        - pilot_kJ)
    # A zero-stroke map includes leakage/friction at zero delivery. Loaded
    # conditions may dissipate less than its extrapolated integral.
    zero_stroke_kJ = min(pump_residual_kJ, run["pump_loss_energies_kJ"]["zero_stroke"])
    losses_kJ = {
        "pump_zero_stroke_and_FDV": zero_stroke_kJ,
        "pump_internal_leakage_displacement_and_coupling": pump_residual_kJ - zero_stroke_kJ,
        "pilot_charge_leakage_and_return": pilot_kJ,
        "decompression": decompression_energy_kJ,
        "normal_spill_and_transition_bypass": energy["bypass_kJ"],
        "working_line_and_valve_drops": energy["valves_kJ"] + energy["sharing_kJ"],
        "accumulator_paths": energy["charge_kJ"] - energy["boost_kJ"],
        "cylinder_friction_and_braking": energy["cylinder_friction_kJ"] + run["damping_heat_kJ"],
        "prefill_and_rapid_float": energy["prefill_float_kJ"],
        "cooling_circulation": circulation_kW * duration_s,
        "shaft_tolerance_and_extra_handover": (
            (run["shaft_average_with_tolerance_kW"] - run["average_shaft_kW"]) * run["cycle_s"]
            + extra_handover_s * run["shaft_peak_with_tolerance_kW"]),
    }
    return {name: value / duration_s for name, value in losses_kJ.items()}


def evaluate_heat(data, prior, old_run, nominal_run, adverse_run, cycle, cylinder_results):
    cfg = data["revision"]["cooling"]
    original = prior["cooling"]
    release_kJ = cylinder_results["cycles"]["physical_36_kW"]["decompression"]["effective_release_energy_kJ"]
    old_summary = cycle["round2_nominal"]
    nominal = cycle["revision_nominal"]
    adverse = cycle["revision_adverse"]
    old = heat_sources(old_run, prior["round2"]["pilot"]["heat_bound_kW"],
                       old_summary["extra_handover_budget_s"], release_kJ, original["installed_kW"]["cooler_circulation"])
    # Preserve the inherited worst-duty allowance. Apply only the deltas
    # measured on the copied V2 traces.
    inherited_allowance_kW = original["heat_load_kW"] - fsum(old.values())
    old["inherited_worst_duty_allowance"] = inherited_allowance_kW

    def updated(run, summary):
        pilot = summary["pilot"]
        result = heat_sources(run, data["project"]["round2"]["pilot_tandem_unloaded_shaft_bound_kW"],
                              summary["extra_handover_budget_s"], release_kJ, cfg["circulation_motor_kW"])
        result["pilot_charge_leakage_and_return"] = pilot["pilot_heat_kW"]
        # The main trace already includes tolerance on the unloaded tandem.
        result["shaft_tolerance_and_extra_handover"] += pilot["pilot_incremental_shaft_kJ"] / summary["cycle_s"] * (
            summary["peak_shaft_kW"] / 36 - 1)
        result["inherited_worst_duty_allowance"] = inherited_allowance_kW
        return result

    proposed = updated(nominal_run, nominal)
    adverse_sources = updated(adverse_run, adverse)
    nominal_heat_kW = fsum(proposed.values())
    adverse_heat_kW = fsum(adverse_sources.values())
    maximum_heat_kW = max(nominal_heat_kW, adverse_heat_kW)
    cat = data["catalogs"]["ASA0567"]
    supply_flow = cfg["circuit_flow_L_min"]
    min_flow = cfg["target_min_flow_per_module_L_min"]
    worst_flow = supply_flow - min_flow
    count = cfg["modules"]
    if count != 2 or supply_flow < count * min_flow or min_flow < cat["performance_flow_L_min"]:
        raise ValueError("cooler branch flows do not support the catalogue point")
    delta_K = cfg["oil_inlet_limit_C"] - cfg["ambient_C"]
    catalog_flow, catalog_thermal = cat["performance_points_L_min_kW_K"]
    if not catalog_flow[0] <= min_flow <= worst_flow <= catalog_thermal[0]:
        raise ValueError("branch flows outside the cooler performance interval")
    slope_kW_K_per_L_min = ((catalog_thermal[1] - catalog_flow[1])
                             / (catalog_thermal[0] - catalog_flow[0]))
    # Both branches stay on the same interpolated segment. Their sum depends
    # on the total flow and is invariant under the allowed flow imbalance.
    total_coefficient_kW_K = (count * catalog_flow[1]
                              + slope_kW_K_per_L_min * (supply_flow - count * catalog_flow[0]))
    raw_kW = total_coefficient_kW_K * delta_K
    low_point_only_kW = count * catalog_flow[1] * delta_K
    lower_kW = raw_kW * (1 - cat["tolerance_fraction"])
    dirty_kW = lower_kW * (1 - cfg["fouling_fraction"])
    required_kW = max(cfg["minimum_point_kW"], cfg["heat_factor"] * maximum_heat_kW)
    low, high = cat["dp_points_L_min_bar"]
    if not low[0] <= worst_flow <= high[0]:
        raise ValueError("matrix pressure-drop point outside published interval")
    matrix_bar = low[1] + (high[1] - low[1]) * (worst_flow - low[0]) / (high[0] - low[0])
    total_drop_bar = matrix_bar + cfg["common_drop_budget_bar"]
    shaft_kW = supply_flow * total_drop_bar / (600 * cfg["pump_efficiency_floor"])
    installed = original["installed_kW"] | {
        "cooler_fan": count * cat["fan_kW"], "cooler_circulation": cfg["circulation_motor_kW"],
    }
    installed_kW = fsum(installed.values())
    point_only_dirty_kW = low_point_only_kW * (1 - cat["tolerance_fraction"]) * (1 - cfg["fouling_fraction"])
    return {
        "T15_sources_kW": old, "T16_nominal_sources_kW": proposed, "T16_adverse_sources_kW": adverse_sources,
        "delta_nominal_sources_kW": {name: proposed[name] - old[name] for name in old},
        "T15_design_heat_kW": fsum(old.values()), "nominal_heat_kW": nominal_heat_kW,
        "adverse_heat_kW": adverse_heat_kW, "review_design_heat_kW": maximum_heat_kW,
        "target_heat_kW": 19, "heat_target_pass": maximum_heat_kW <= 19,
        "cooling": {
            "model": "2 × ASA0567AA47", "inlet_oil_C": cfg["oil_inlet_limit_C"], "inlet_air_C": cfg["ambient_C"],
            "circulation_flow_L_min": supply_flow, "min_branch_flow_L_min": min_flow,
            "maximum_branch_flow_L_min": worst_flow, "nominal_catalog_capacity_kW": raw_kW,
            "derated_clean_capacity_kW": lower_kW, "dirty_capacity_kW": dirty_kW,
            "dirty_capacity_using_78_L_min_point_only_kW": point_only_dirty_kW,
            "margin_over_target_kW": dirty_kW - required_kW,
            "thermal_interpolation": cat["performance_points_L_min_kW_K"],
            "body_stack_width_depth_height_mm": [cat["body_width_mm"], cat["body_depth_mm"],
                count * cat["body_height_mm"] + cfg["vertical_separation_mm"]],
            "target_capacity_kW": required_kW, "dust_derating_fraction": cfg["fouling_fraction"],
            "oil_to_air_capacity_pass": dirty_kW >= required_kW,
            "temperature_at_worst_duty_C": cfg["ambient_C"] + maximum_heat_kW / (dirty_kW / delta_K),
            "matrix_drop_worst_branch_bar": matrix_bar, "total_circuit_drop_bar": total_drop_bar,
            "pump_required_shaft_kW": shaft_kW, "pump_size_pass": shaft_kW <= cfg["circulation_motor_kW"],
            "installed_breakdown_kW": installed, "installed_total_kW": installed_kW,
            "installed_pass": installed_kW <= original["installed_limit_kW"],
            "air_service": "Individual removable dust mats, differential pressure and opening for fin cleaning. Verify at end-of-life mat condition with isolated exhaust streams.",
            "water_option": cfg["option"],
        },
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    result = json.loads(Path(__file__).with_name("results.json").read_text(encoding="utf-8"))
    if "heat_balance" not in result:
        raise SystemExit("Run mass_budget.py to calculate the cycle and thermal balance.")
    print(json.dumps(result["heat_balance"], ensure_ascii=False, indent=2))
