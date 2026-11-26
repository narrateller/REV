"""Phase energy ledger and T-1.6 cooler, evaluated at 55 °C oil / 40 °C air."""
from math import fsum

from drive import decompression, linear_value, source_data


def cooler(station_sources, sources, required_heat_kW, installed_total_kW):
    config = station_sources["revision"]["cooling"]
    catalogue = station_sources["catalogs"]["ASA0567"]
    count = config["modules"]
    flow_L_min = config["circuit_flow_L_min"]
    min_branch_L_min = config["target_min_flow_per_module_L_min"]
    max_branch_L_min = flow_L_min - min_branch_L_min
    (q0, k0), (q1, k1) = catalogue["performance_points_L_min_kW_K"]
    assert q0 <= min_branch_L_min <= max_branch_L_min <= q1
    specific_kW_K = count * k0 + (k1 - k0) * (flow_L_min - count * q0) / (q1 - q0)
    delta_K = config["oil_inlet_limit_C"] - config["ambient_C"]
    catalogue_kW = specific_kW_K * delta_K
    clean_kW = catalogue_kW * (1 - catalogue["tolerance_fraction"])
    dirty_kW = clean_kW * (1 - config["fouling_fraction"])
    (q0, dp0), (q1, dp1) = catalogue["dp_points_L_min_bar"]
    branch_bar = dp0 + (dp1 - dp0) * (max_branch_L_min - q0) / (q1 - q0)
    circulation_shaft_kW = (flow_L_min * (branch_bar + config["common_drop_budget_bar"])
                            / (600 * config["pump_efficiency_floor"]))
    sizing_floor_kW = max(config["minimum_point_kW"], config["heat_factor"] * required_heat_kW)
    installed_circulation_kW = config["circulation_motor_kW"]
    single = sources["catalogs"]["asa0927_single"]
    single_options = []
    for single_flow_L_min in (flow_L_min, 250):
        specific_single_kW_K = linear_value(single_flow_L_min, single["flow_L_min_kW_K"])
        single_dirty_kW = (specific_single_kW_K * delta_K * (1 - catalogue["tolerance_fraction"])
                           * (1 - config["fouling_fraction"]))
        single_dp_bar = linear_value(single_flow_L_min, single["flow_L_min_pressure_drop_bar"])
        single_circulation_kW = (single_flow_L_min * (single_dp_bar + config["common_drop_budget_bar"])
                                 / (600 * config["pump_efficiency_floor"]))
        minimum_installed_kW = installed_total_kW - installed_circulation_kW + single_circulation_kW
        single_options.append(dict(model="ASA0927AA6A", flow_L_min=single_flow_L_min,
                                   fouled_capacity_kW=single_dirty_kW, mass_kg=single["mass_kg"],
                                   min_installed_lower_bound_kW=minimum_installed_kW,
                                   circulation_shaft_kW=single_circulation_kW,
                                   D_OP_09_point_pass=single_dirty_kW >= config["minimum_point_kW"]))
    return dict(
        single_cooler_screen=single_options,
        model="2 × ASA0567AA47", ambient_C=config["ambient_C"], oil_inlet_C=config["oil_inlet_limit_C"],
        total_flow_L_min=flow_L_min, branch_flow_range_L_min=[min_branch_L_min, max_branch_L_min],
        nominal_catalogue_capacity_kW=catalogue_kW, tolerance_derated_clean_kW=clean_kW,
        fouling_fraction=config["fouling_fraction"], fouled_capacity_kW=dirty_kW,
        fouled_capacity_78_L_min_each_kW=2 * 1.19 * delta_K * (1 - catalogue["tolerance_fraction"])
        * (1 - config["fouling_fraction"]),
        remaining_reserve_fraction=dirty_kW / required_heat_kW - 1,
        minimum_point_kW=config["minimum_point_kW"], inherited_T16_sizing_floor_kW=sizing_floor_kW,
        margin_over_T16_sizing_kW=dirty_kW - sizing_floor_kW,
        fan_installed_kW=count * catalogue["fan_kW"],
        circulation_shaft_kW=circulation_shaft_kW,
        circulation_installed_kW=installed_circulation_kW,
        circulation_pass=circulation_shaft_kW <= installed_circulation_kW,
        required_T21_pass=dirty_kW >= max(config["minimum_point_kW"], 1.15 * required_heat_kW),
        inherited_T16_sizing_pass=dirty_kW >= sizing_floor_kW,
    )


def ledger(run, model, cylinder, drive_settings, pilot, design_inputs, handover_s, total_limit_kW, vfd=None):
    """Charge pressure storage at input and credit it at discharge to close the cycle."""
    tolerance = run["shaft_peak_with_tolerance_kW"] / run["peak_shaft_kW"]
    duration_s = run["cycle_s"] + handover_s
    by_phase = {phase: row.copy() for phase, row in run["phase_loss_kJ"].items()}
    oil_term = design_inputs["revision"]["cooling"]["circulation_motor_kW"]
    standby_pilot_kW = drive_settings["pump"].pilot_standby_kW
    vfd_delta_kJ = vfd["oil_energy_delta_kJ"] if vfd else 0.
    phase_windows = run["stage_events"]

    for step, pilot_kW in zip(run["power_steps"], run["pilot_loads_kW"]):
        time_s, dt_s, phase, pressure_bar, shaft_kW, _, _, bypass_kW, useful_L_min, _ = step
        if phase in ("neutral", "lp_charge"):
            midpoint_s = time_s + dt_s / 2
            interval = next((name for name in ("hold", "unload", "feed")
                             if phase_windows[name][0] <= midpoint_s < phase_windows[name][1]), "switches")
            phase = f"{interval}/{phase}"
        terms = by_phase.setdefault(phase, {})
        hydraulic_kW = pressure_bar * useful_L_min / 600
        values = dict(main_pump_and_coupling=(shaft_kW - standby_pilot_kW - hydraulic_kW - bypass_kW),
                      bypass=bypass_kW, pilot=pilot_kW + standby_pilot_kW,
                      shaft_tolerance=(shaft_kW + pilot_kW) * (tolerance - 1),
                      circulation=oil_term)
        for term, power_kW in values.items():
            terms[term] = terms.get(term, 0.) + dt_s * power_kW

    # Redistribute the original LP recharge source into the hold/unload/feed windows
    # where the pump recorded its pressure and delivery. Its total is conserved.
    recharge_kJ = by_phase.pop("lp_charge", {}).get("accumulator_charge", 0.)
    flow_energy = {}
    for step in run["power_steps"]:
        time_s, dt_s, phase, bar, _, _, _, _, flow_L_min, _ = step
        if phase == "lp_charge":
            midpoint_s = time_s + dt_s / 2
            interval = next((name for name in ("hold", "unload", "feed")
                             if phase_windows[name][0] <= midpoint_s < phase_windows[name][1]), "switches")
            tag = f"{interval}/lp_charge"
            flow_energy[tag] = flow_energy.get(tag, 0.) + bar * flow_L_min * dt_s / 600
    assert abs(fsum(flow_energy.values()) - recharge_kJ) < 1e-8
    for phase, energy_kJ in flow_energy.items():
        by_phase[phase]["accumulator_charge"] = energy_kJ

    for phase, energy_kJ in run["damping_by_motion_kJ"].items():
        by_phase[phase]["damping"] = energy_kJ
    release = decompression(run, model, cylinder, source_data())
    by_phase.setdefault("unload", {})["oil_and_structure_decompression"] = release["effective_release_energy_kJ"]
    by_phase["handover_allowance"] = {
        "shaft_upper_bound": handover_s * total_limit_kW * tolerance,
        "circulation": oil_term * handover_s,
    }
    inherited_heat_kW = design_inputs["inherited_worst_duty_allowance_kW"]
    by_phase["inherited_worst_duty_allowance"] = {"allowance": inherited_heat_kW * duration_s}
    if vfd:
        by_phase.setdefault("feed/neutral", {})["speed_reduction"] = vfd_delta_kJ
    phase_total_kW = {name: fsum(terms.values()) / duration_s for name, terms in by_phase.items()}
    e = run["energy"]
    expected_kW = (
        (pilot["average_shaft_kW"] * duration_s - e["header_kJ"] + e["charge_kJ"] - e["boost_kJ"]
         + e["valves_kJ"] + e["sharing_kJ"] + e["cylinder_friction_kJ"] + e["prefill_float_kJ"]
         + run["damping_heat_kJ"] + release["effective_release_energy_kJ"] + vfd_delta_kJ) / duration_s
        + inherited_heat_kW + oil_term
    )
    total_kW = fsum(phase_total_kW.values())
    assert abs(total_kW - expected_kW) < 1e-7, (total_kW, expected_kW)
    return dict(oil_heat_kW=total_kW, phase_energy_kJ=by_phase,
                phase_cycle_average_kW=phase_total_kW, duration_s=duration_s)

