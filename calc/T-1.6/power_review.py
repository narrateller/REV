"""Screen the five requested power changes against the copied V2 trace."""
from copy import deepcopy
from math import fsum, pi, sqrt

from cycle_screen import cycle_screen
from drive import PV180Drive, source_data
from heat_balance import evaluate_heat
from round2_screens import screen


def replay_fixed_trace(trace, summary, limit_kW, reductions_kW):
    """Keep the cycle and pilot delivery schedule, subtract a shaft-power sensitivity."""
    steps = trace["power_steps"]
    additions = trace["pilot_loads_kW"]
    handover_s = summary["extra_handover_budget_s"]
    total_s = summary["cycle_s"]
    tolerance = trace["shaft_peak_with_tolerance_kW"] / trace["peak_shaft_kW"]
    mean_kJ = fsum(dt * (base + pilot - reduction) for (_, dt, _, _, base, _, _), pilot, reduction
                    in zip(steps, additions, reductions_kW))
    square = fsum(dt * (base_square + 2 * base * (pilot - reduction) + (pilot - reduction)**2)
                  for (_, dt, _, _, base, _, base_square), pilot, reduction
                  in zip(steps, additions, reductions_kW))
    return {
        "rms_kW": sqrt((square + handover_s * limit_kW**2) / total_s) * tolerance,
        "mean_kW": (mean_kJ + handover_s * limit_kW) / total_s * tolerance,
        "shaft_saving_kW": fsum(row[1] * reduction for row, reduction in zip(steps, reductions_kW)) / total_s,
        "uncredited_cycle_change_s": 0.0,
    }


def contiguous_idle_windows(trace, idle_kW):
    windows = []
    start_s = None
    for time_s, dt_s, stage, header_bar, _, peak_kW, _ in trace["power_steps"]:
        if stage == "neutral" and header_bar == 0 and peak_kW <= idle_kW + 1e-8:
            if start_s is None:
                start_s = time_s
            end_s = time_s + dt_s
        elif start_s is not None:
            windows.append((start_s, end_s))
            start_s = None
    if start_s is not None:
        windows.append((start_s, end_s))
    return windows


def evaluate_power(data, original, prior, baseline, cycle, traces, interlocks, circuit, trial_losses, main):
    cfg = data["review_round_2"]["power"]
    catalogs = data["catalogs"]
    limit_kW = circuit["elements"]["EC1"]["setpoint"]["shaft_kW"]
    old_trace, nominal_trace, adverse_trace = traces
    nominal, adverse = cycle["revision_nominal"], cycle["revision_adverse"]
    installed_kW = baseline["cooling"]["installed_total_kW"]
    heat_kW = baseline["review_design_heat_kW"]
    rms_kW = nominal["rms_shaft_kW"]
    nominal_time_s = nominal["with_T13_physical_allowance_s"]
    adverse_time_s = adverse["with_T13_physical_allowance_s"]
    model = PV180Drive(source_data())
    standby = model.section("PV180", model.standby_bar).deadhead_kW
    opened = model.section("PV180", cfg["standby_hypothetical_bar"]).deadhead_kW
    pilot_standby_kW = data["project"]["round2"]["pilot_tandem_unloaded_shaft_bound_kW"]
    idle_kW = standby + model.loss_kW + pilot_standby_kW
    windows = contiguous_idle_windows(nominal_trace, idle_kW)
    durations_s = [end - start for start, end in windows]

    def fixed_variant(neutral_reduction_kW, pilot_fraction=0):
        reductions_kW = [
            (neutral_reduction_kW if stage == "neutral" and header_bar == 0 and peak_kW <= idle_kW + 1e-8
             else 0.0) + (inc_kW + pilot_standby_kW) * pilot_fraction
            for (_, _, stage, header_bar, _, peak_kW, _), inc_kW
            in zip(nominal_trace["power_steps"], nominal_trace["pilot_loads_kW"])
        ]
        ans = replay_fixed_trace(nominal_trace, nominal, limit_kW, reductions_kW)
        ans["delta_rms_kW"] = ans["rms_kW"] - rms_kW
        return ans

    verify = fixed_variant(0)
    if abs(verify["rms_kW"] - rms_kW) > 1e-10:
        raise ValueError("Round 2 fixed-trace replay disagrees with Round 1 pilot")
    pilot_cfg = data["project"]["round2"]
    eta = pilot_cfg["pilot_eta_v_floor"] * pilot_cfg["pilot_eta_mechanical_floor"]
    ax_supply_bar = data["revision"]["pilot"]["max_pilot_bar"]
    fdv_cost_in_ax_kW = cfg["external_FDV_static_flow_L_min"] * ax_supply_bar / (600 * eta)
    a = fixed_variant(standby - opened - fdv_cost_in_ax_kW)
    a.update(delta_heat_kW=-a["shaft_saving_kW"], additional_installed_kW=0,
             external_FDV_static_from_AX_kW=fdv_cost_in_ax_kW,
             external_supply_bar=cfg["external_FDV_supply_bar"],
             reason="Internal FDV requires 15 bar. External-feed optimistic estimate excludes flushing, dynamic servo demand and changes to the approved AX supply.")
    c = fixed_variant(standby)
    p1 = catalogs["PV"]
    motor = catalogs["motor"]
    inertia = p1["inertia_kg_m2"] + motor["inertia_kg_m2"]
    omega_rad_s = model.rpm * 2 * pi / 60
    max_motor_torque_N_m = motor["rated_torque_N_m"] * motor["breakdown_rated_ratio"]
    zero_to_speed_min_s = inertia * omega_rad_s / max_motor_torque_N_m
    PGP_min_rev_min = catalogs["pilot_separate_D1"]["min_rev_min_at_max_pressure"]
    # A retained tandem needs speed too. 500 rpm is only the PGP511
    # catalogue minimum at max pressure, not a validated hot-pilot point.
    vfd_rpm = PGP_min_rev_min
    vfd = fixed_variant(standby * (1 - vfd_rpm / model.rpm))
    vfd_cat = catalogs["VFD_D1"]
    vfd.update(delta_heat_kW=-vfd["shaft_saving_kW"],
               rated_motor_kW=vfd_cat["rated_motor_kW"], installed_total_kW=installed_kW,
               input_budget_with_max_converter_loss_kW=installed_kW + vfd_cat["max_cabinet_loss_kW"],
               converter_heat_in_cabinet_kW=vfd_cat["max_cabinet_loss_kW"],
               additional_hardware_kg=vfd_cat["mass_kg"], price_BRL=vfd_cat["observed_price_BRL"],
               idle_speed_rev_min=vfd_rpm,
               minimum_ideal_acceleration_s=inertia * (model.rpm - vfd_rpm) * 2 * pi / 60 / max_motor_torque_N_m,
               reason="D1 only. Linear speed scaling, instant ramp and unchanged pilot charge in sensitivity. Verify torque/current duty, hot speed/flow and cabinet losses.")
    c.update(delta_heat_kW=-c["shaft_saving_kW"], additional_installed_kW=0,
             neutral_time_s=fsum(durations_s), neutral_window_lengths_s=durations_s,
             PV180_FDV_verified_response_s=None, zero_to_speed_ideal_min_s=zero_to_speed_min_s,
             windows_above_two_ideal_ramps=sum(dt > 2 * zero_to_speed_min_s for dt in durations_s),
             reason="Upper bound at instantaneous lossless decoupling, same pilot. The existing ZN already unloads neutral; stopping the motor also stops PX/PXA and needs a restart.")
    isolated = fixed_variant(0, pilot_fraction=1)
    pump_cat = catalogs["pilot_separate_D1"]
    Q_geom_L_min = cfg["pilot_independent_geometric_cm3_rev"] * pump_cat["motor_rev_min"] / 1000
    Q_min_L_min = Q_geom_L_min * pilot_cfg["pilot_eta_v_floor"]
    minimum_oil_L = nominal["pilot"]["required_hot_oil_L_per_cycle"]
    demand_average_L_min = minimum_oil_L * 60 / nominal["cycle_s"]
    on_shaft_kW = Q_geom_L_min * pilot_cfg["pilot_max_load_bar"] / (600 * pilot_cfg["pilot_eta_mechanical_floor"])
    isolated_pilot_kW = (pilot_standby_kW
                         + (on_shaft_kW - pilot_standby_kW) * demand_average_L_min / Q_min_L_min)
    isolated.update(
        delta_heat_kW=isolated_pilot_kW - nominal["pilot"]["pilot_heat_kW"],
        pump_flow_floor_L_min=Q_min_L_min, required_average_flow_L_min=demand_average_L_min,
        pump_on_shaft_kW=on_shaft_kW, pilot_average_heat_kW=isolated_pilot_kW,
        installed_total_kW=installed_kW + cfg["pilot_independent_motor_kW"],
        pump_plus_motor_kg=pump_cat["pump_mass_kg"] + pump_cat["motor_mass_kg"],
        previous_tandem_and_feedback_allowance_kg=pilot_cfg[
            "safety_hardware_mass_budget_kg"]["pilot_tandem_and_feedback"],
        reason="4 kW motor exceeds installed limit. Motor and gear pump dry masses exclude coupling and bed; replicate cyclic demand and AX transient safety before changing topology.",
    )

    def scenario(losses, efficient_pilot=False):
        trial = deepcopy(data)
        trial["revision"]["main_manifold"]["loss_budgets_bar"] = losses
        if efficient_pilot:
            efficiency = cfg["pilot_efficiency_sensitivity"]
            trial["project"]["round2"].update(pilot_eta_v_floor=efficiency["eta_v"],
                                             pilot_eta_mechanical_floor=efficiency["eta_mechanical"])
        trial_checks = screen(circuit, trial, main["cap_dead_L"])
        n, nt, w, wt = cycle_screen(trial, original, trial_checks, interlocks, circuit, trial_only=True)
        result = evaluate_heat(trial, prior, old_trace, nt, wt,
                               cycle | {"revision_nominal": n, "revision_adverse": w}, original)
        return {
            "rms_kW": n["rms_shaft_kW"], "delta_rms_kW": n["rms_shaft_kW"] - rms_kW,
            "heat_kW": result["review_design_heat_kW"], "delta_heat_kW": result["review_design_heat_kW"] - heat_kW,
            "nominal_cycle_s": n["with_T13_physical_allowance_s"],
            "adverse_cycle_s": w["with_T13_physical_allowance_s"],
            "delta_nominal_s": n["with_T13_physical_allowance_s"] - nominal_time_s,
            "delta_adverse_s": w["with_T13_physical_allowance_s"] - adverse_time_s,
            "pilot_nominal": n["pilot"], "pilot_adverse": w["pilot"],
            "proof_status": "sensitivity; hot efficiencies and loss budgets require evidence",
        }

    b = scenario(data["revision"]["main_manifold"]["loss_budgets_bar"], efficient_pilot=True)
    d = scenario(trial_losses)
    both = scenario(trial_losses, efficient_pilot=True)
    prices = {key: hours * cfg["hydraulic_cost_rate_EUR_h"] for key, hours in cfg["estimated_hours"].items()}
    return {
        "external_FDV": a, "separate_pilot": isolated, "tandem_efficiency_sensitivity": b,
        "unload_restart": c, "shared_blocks": d, "shared_blocks_and_better_tandem": both, "VFD_D1": vfd,
        "labor_cost_estimate_EUR": prices,
        "requested_rms_margin_kW": rms_kW - 29,
        "requested_heat_margin_kW": heat_kW - 19,
        "fixed_trace_cycle_note": "Zero change by construction in each ideal fixed trace; restart time and pilot capacity are separate qualification requirements.",
    }

