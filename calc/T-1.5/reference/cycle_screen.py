
"""Sensitivity adapter for the copied T-1.4b V2 simulator."""
from copy import deepcopy
from dataclasses import replace

from drive import configuration, evaluated_run, get_inputs, source_data


def cycle_screen(cfg, prior, round2, interlocks):
    inputs, data = get_inputs(), source_data()
    settings_cfg = cfg["sensitivity"]
    feed_s = settings_cfg["feed_s"]
    steps = settings_cfg["dt_s"]
    limits = {"limit_kW": 36}
    geometry, cylinder, base_settings, _, _ = configuration(inputs, data=data, **limits)
    increased = deepcopy(data)
    pump_curve = increased["catalogs"]["parker_pvplus"]["models"]["PV180"]
    pump_curve["zero_stroke_power_kW_endpoints"] = [
        kw * settings_cfg["deadhead_factor"] for kw in pump_curve["zero_stroke_power_kW_endpoints"]
    ]
    pess_geometry, _, pess_settings, _, _ = configuration(
        inputs, data=increased, profile="pessimistic", **limits,
    )
    physical_base = prior["cycles"]["physical_36_kW"]
    physical_addition_s = (
        physical_base["cycle_with_reversal_clearance_upper_s"]
        - prior["cycles"]["baseline_36_kW"]["cycle_s"]
    )

    def summarize(run):
        return {
            "cycle_s": run["cycle_s"],
            "with_T13_physical_allowance_s": run["cycle_s"] + physical_addition_s,
            "peak_shaft_kW": run["shaft_peak_with_tolerance_kW"],
            "rms_shaft_kW": run["shaft_rms_with_tolerance_kW"],
            "average_shaft_kW": run["shaft_average_with_tolerance_kW"],
            "peak_working_bar": run["peak_working_bar"],
            "dt_s": run["dt_s"],
            "convergence": run["convergence"],
        }

    def run(geom, settings, inputs_data, profile):
        return evaluated_run(geom, cylinder, settings, inputs_data, profile, 90, feed_s, None, steps)

    base = run(geometry, base_settings, data, "realistic")
    results = {}
    for scale in settings_cfg["rapid_and_gate_mass_factors"]:
        model = replace(pess_geometry, rapid_mass_kg=pess_geometry.rapid_mass_kg * scale,
                        gate_mass_kg=pess_geometry.gate_mass_kg * scale)
        record = run(model, pess_settings, increased, "pessimistic")
        results[f"mass_x{scale:g}"] = dict(summarize(record), mass_factor=scale,
                                          deadhead_factor=settings_cfg["deadhead_factor"],
                                          delta_to_reference_s=record["cycle_s"] - base["cycle_s"])

    # For the pilot takeoff screen, use a fixed additional demand above the
    # reduction valve's cut-in. A measured charge window can only reduce this.
    pump = base_settings["pump"]
    original_fractions = pump.fractions
    original_instant = pump.instant
    pilot_takeoff_L_min = settings_cfg["max_pilot_takeoff_L_min"]
    cutin_bar = settings_cfg["pilot_takeoff_cutin_bar"]

    def fractions(pressure_bar, requested_L_min, actual=()):
        demand = pilot_takeoff_L_min if pressure_bar >= cutin_bar else 0
        return original_fractions(pressure_bar, requested_L_min + demand, actual)

    def instant(pressure_bar, fractions, connected):
        flow, shaft, bypass = original_instant(pressure_bar, fractions, connected)
        use = min(flow, pilot_takeoff_L_min) if connected[0] and pressure_bar >= cutin_bar else 0
        return flow - use, shaft, bypass

    pump.fractions = fractions
    pump.instant = instant
    screening = run(geometry, base_settings, data, "pilot takeoff")
    def round2_run(model_input, model_settings, pump_data, profile):
        # Keep the combined shaft at 36 kW. Model PX unloaded in the high
        # pressure work zone. Idle AX recharge is bounded separately.
        settings = deepcopy(model_settings)
        tandem = settings["pump"]
        map_fractions = tandem.fractions
        map_instant = tandem.instant
        coupling_kW = tandem.loss_kW
        pilot = round2["pilot"]
        tandem.pilot_priority_bars = pilot["priority_bars"]

        def pilot_loss(header_bar):
            return sum(
                pilot["stage_shaft_bound_kW"][name] if header_bar < cut_in
                else pilot["stage_standby_bound_kW"][name]
                for name, cut_in in tandem.pilot_priority_bars.items()
            )

        def fractions(header_bar, demand, actual=()):
            tandem.loss_kW = coupling_kW + pilot_loss(header_bar)
            return map_fractions(header_bar, demand, actual)

        def instant(header_bar, fractions, connected):
            tandem.loss_kW = coupling_kW + pilot_loss(header_bar)
            return map_instant(header_bar, fractions, connected)

        tandem.fractions = fractions
        tandem.instant = instant
        float_bounds = round2["float"]
        inlet, tank, regen = model_input.losses_bar
        geom = replace(model_input, losses_bar=(inlet, tank, regen + float_bounds["regen_check_dp_bound_bar"]),
                       main_press_float_force_N=float_bounds["max_rapid_pair_drag_N"])
        actual = run(geom, settings, pump_data, profile)
        budget = interlocks["switching_windows"]["handover_regen_press"]["modeled_switch_budget_s"]
        additional_transition_s = max(0, budget - settings["switch_s"])
        summary = summarize(actual)
        total_s = actual["cycle_s"] + additional_transition_s
        summary.update(cycle_s=total_s,
                       with_T13_physical_allowance_s=total_s + physical_addition_s,
                       extra_handover_budget_s=additional_transition_s)
        summary["lp_charge_s_by_window"] = actual["lp_charge_s_by_window"]
        for key, original in [("average_shaft_kW", actual["shaft_average_with_tolerance_kW"]),
                              ("rms_shaft_kW", actual["shaft_rms_with_tolerance_kW"])]:
            exponent = 2 if key == "rms_shaft_kW" else 1
            bound_kW = actual["shaft_peak_with_tolerance_kW"]
            total = original**exponent * actual["cycle_s"] + bound_kW**exponent * additional_transition_s
            summary[key] = (total / total_s) ** (1 / exponent)
        cam_command_s = next(row["time_s"] for row in actual["switches"] if row["command"] == "pre_up")
        summary["pre_up_command_to_cam_exit_s"] = actual["motion_events"]["pre_up"]["marker_s"] - cam_command_s
        return summary, actual, settings["switch_s"]

    # The original takeoff screen monkey-patches its pump; use a clean copy
    # of the reference settings for the changed V2 design.
    _, _, clean_settings, _, _ = configuration(inputs, data=data, **limits)
    combined, nominal_run, switch_s = round2_run(geometry, clean_settings, data, "round 2")
    pess_model = replace(pess_geometry, rapid_mass_kg=pess_geometry.rapid_mass_kg * 1.5,
                         gate_mass_kg=pess_geometry.gate_mass_kg * 1.5)
    pess_screen, _, _ = round2_run(pess_model, pess_settings, increased, "round 2 adverse envelope")
    single_change_model = replace(geometry, main_press_float_force_N=round2["float"]["max_rapid_pair_drag_N"])
    _, _, single_change_settings, _, _ = configuration(inputs, data=data, **limits)
    float_only = run(single_change_model, single_change_settings, data, "rapid float branch only")
    combined["delta_to_reference_s"] = combined["cycle_s"] - base["cycle_s"]
    pess_screen["delta_to_previous_mass_x1p5_s"] = pess_screen["cycle_s"] - results["mass_x1.5"]["cycle_s"]
    return {
        "round2_nominal": combined,
        "rapid_float_only": dict(summarize(float_only), delta_s=float_only["cycle_s"] - base["cycle_s"]),
        "round2_adverse_envelope": pess_screen,
        "reference_36_kW": summarize(base),
        "combined_pessimistic": results,
        "pilot_takeoff_bound": dict(summarize(screening), takeoff_L_min=pilot_takeoff_L_min,
                                    cutin_bar=cutin_bar, delta_s=screening["cycle_s"] - base["cycle_s"]),
        "T13_nominal_physical_s": physical_base["cycle_with_reversal_clearance_upper_s"],
        "T13_pessimistic_reserve_high_s": prior["cycles"]["physical_36_kW_reserve_300_bar_high"][
            "cycle_with_reversal_clearance_upper_s"
        ],
        "T13_physical_allowance_s": physical_addition_s,
        "reference_dir": "calc/T-1.5/reference",
        "basis": "Gate-equivalent params.t14b remains in force. Sensitivity at nominal dose and 90 kg/m³. Only valve losses and pilot/main power allocation changed.",
    }, nominal_run, switch_s
