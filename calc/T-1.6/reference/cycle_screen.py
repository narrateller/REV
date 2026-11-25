"""Run the T-1.5 reference and the T-1.6 motion/pilot envelope."""
from copy import deepcopy
from dataclasses import replace

from pilot_control import pilot_replay
from round2_screens import pilot_cycle

from drive import configuration, evaluated_run, get_inputs, source_data


def cycle_screen(data16, cylinder_reference, round2, interlocks, circuit, *, trial_only=False):
    project = data16["project"]
    settings_cfg = project["sensitivity"]
    reference_data = source_data()
    inputs = get_inputs()
    limit_kW = circuit["elements"]["EC1"]["setpoint"]["shaft_kW"]
    physical = cylinder_reference["cycles"]["physical_36_kW"]["cycle_with_reversal_clearance_upper_s"]
    physical_addition_s = physical - cylinder_reference["cycles"]["baseline_36_kW"]["cycle_s"]
    pilot = round2["pilot"]
    float_screen = round2["float"]

    def scenario(data, profile, revised):
        geom, cylinder, settings, _, _ = configuration(inputs, data=data, profile=profile, limit_kW=limit_kW)
        if profile == "pessimistic":
            geom = replace(geom, rapid_mass_kg=geom.rapid_mass_kg * 1.5, gate_mass_kg=geom.gate_mass_kg * 1.5)
        inlet, tank, regen = geom.losses_bar
        geom = replace(geom, losses_bar=(inlet, tank, regen + float_screen["regen_check_dp_bound_bar"]),
                       main_press_float_force_N=float_screen["max_rapid_pair_drag_N"])
        if revised:
            inlet, tank, regen = data16["revision"]["main_manifold"]["loss_budgets_bar"]
            geom = replace(geom, main_loss_budgets_bar=(inlet, tank, regen + float_screen["regen_check_dp_bound_bar"]))
        pump = settings["pump"]
        pump.record_power_steps = True
        pump.pilot_priority_bars = pilot["priority_bars"]
        base_loss_kW = pump.loss_kW
        fractions, instant = pump.fractions, pump.instant

        def update_pilot_loss(header_bar):
            power_kW = pilot["standby_shaft_bound_kW"] if revised else sum(
                pilot["stage_shaft_bound_kW"][name] if header_bar < cut_in
                else pilot["stage_standby_bound_kW"][name]
                for name, cut_in in pump.pilot_priority_bars.items())
            pump.loss_kW = base_loss_kW + power_kW

        def fractions_with_pilot(header_bar, demand, actual=()):
            update_pilot_loss(header_bar)
            return fractions(header_bar, demand, actual)

        def instant_with_pilot(header_bar, swash, connected):
            update_pilot_loss(header_bar)
            return instant(header_bar, swash, connected)

        pump.fractions = fractions_with_pilot
        pump.instant = instant_with_pilot
        dose_density_kg_m3 = 90
        trace = evaluated_run(geom, cylinder, settings, data, profile, dose_density_kg_m3,
                              settings_cfg["feed_s"], None, settings_cfg["dt_s"])
        switch_s = settings["switch_s"]
        handover_s = interlocks["switching_windows"]["handover_regen_press"]["modeled_switch_budget_s"]
        extra_s = max(0., handover_s - switch_s)
        total_s = trace["cycle_s"] + extra_s
        cam_s = next(row["time_s"] for row in trace["switches"] if row["command"] == "pre_up")
        summary = {
            "cycle_s": total_s, "with_T13_physical_allowance_s": total_s + physical_addition_s,
            "extra_handover_budget_s": extra_s, "peak_working_bar": trace["peak_working_bar"],
            "dt_s": trace["dt_s"], "convergence": trace["convergence"],
            "lp_charge_s_by_window": trace["lp_charge_s_by_window"],
            "pre_up_command_to_cam_exit_s": trace["motion_events"]["pre_up"]["marker_s"] - cam_s,
        }
        power_keys = ("average_shaft_kW", "rms_shaft_kW", "peak_shaft_kW")
        if revised:
            demand = pilot_cycle(circuit, interlocks, data16, trace, pilot, switch_s)
            replay = pilot_replay(trace, pilot, demand, data16["revision"]["pilot"], extra_s, limit_kW)
            summary.update({key: replay[key] for key in power_keys})
            summary["pilot"] = replay
        else:
            peak = trace["shaft_peak_with_tolerance_kW"]
            summary["peak_shaft_kW"] = peak
            for key, exponent in (("average", 1), ("rms", 2)):
                core = trace[f"shaft_{key}_with_tolerance_kW"]
                result = (core**exponent * trace["cycle_s"] + peak**exponent * extra_s) / total_s
                summary[f"{key}_shaft_kW"] = result ** (1 / exponent)
        return summary, trace

    adverse_data = deepcopy(reference_data)
    pump_curve = adverse_data["catalogs"]["parker_pvplus"]["models"]["PV180"]
    pump_curve["zero_stroke_power_kW_endpoints"] = [
        value * settings_cfg["deadhead_factor"] for value in pump_curve["zero_stroke_power_kW_endpoints"]]
    nominal, nominal_trace = scenario(reference_data, "realistic", revised=True)
    adverse, adverse_trace = scenario(adverse_data, "pessimistic", revised=True)
    if trial_only:
        return nominal, nominal_trace, adverse, adverse_trace
    old, old_trace = scenario(reference_data, "realistic", revised=False)
    return {
        "round2_nominal": old, "revision_nominal": nominal, "revision_adverse": adverse,
        "T13_physical_allowance_s": physical_addition_s,
        "delta_nominal_s": nominal["cycle_s"] - old["cycle_s"],
        "reference_dir": "calc/T-1.6/reference",
        "gate_equivalent": "design/params.t14b.yaml",
        "basis": "T-1.4b V2; 90 kg/m³; keep physical allowances. Adverse includes 1.5× moving mass, slower gate and 1.2× deadhead power.",
    }, old_trace, nominal_trace, adverse_trace
