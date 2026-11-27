"""Self-contained G-CYCLE physical replay and numerical envelope."""

from math import fsum

from .hydraulics import motions, periodic_run
from .inputs import configure
from .pilot import shaft_balance


# Common X-1 meshes. Compare adjacent halvings and retain the upper envelope
# across the evaluated meshes. The cap bounds the work on ill-conditioned input.
STEPS_S = (0.000625, 0.0003125, 0.00015625, 0.000078125)
CONVERGENCE_S = 0.005


def sequence_checks(run):
    event = run["motion_events"]
    stage = run["stage_events"]
    cmd = {row["command"]: row["time_s"] for row in run["switches"]}
    pairs = [
        (cmd["gate_open"], stage["unload"][1]),
        (cmd["eject"], event["gate_open"]["end_s"]),
        (cmd["return"], event["eject"]["end_s"]),
        (cmd["gate_close"], event["return"]["gate_clear_s"]),
        (cmd["pre_up"], event["eject"]["unlock_clear_s"]),
        (stage["feed"][0], max(event[name]["end_s"] for name in ("return", "gate_close", "pre_up"))),
    ]
    return all(command + 1e-9 >= condition for command, condition in pairs)


def axis_travel(run, sequence):
    axes = {motion.actuator for motion in sequence.values()}
    # Every motion is monotone. Its last integrated displacement closes its
    # contribution to the axis position, with stationary pressure entry omitted.
    traces = run["motion_steps"]
    travel_mm = {}
    residual_mm = {}
    for axis in sorted(axes):
        forward_mm, backward_mm = [], []
        for name, motion in sequence.items():
            if motion.actuator == axis and name in traces:
                outputs = backward_mm if motion.mode == "retract" else forward_mm
                outputs.append(traces[name][-1][-1])
        travel_mm[axis] = max(fsum(forward_mm), fsum(backward_mm))
        residual_mm[axis] = fsum(forward_mm) - fsum(backward_mm)
    return travel_mm, residual_mm


def evaluate(params, max_working_bar):
    cfg = params["cycle_model"]
    model, cylinder, settings, fill = configure(params, max_working_bar)
    process, pump, pilot = (cfg[name] for name in ("process", "pump", "pilot"))
    sequence = motions(model, cylinder, process["bulk_density_kg_m3"], settings["prefill"])
    # T-1.6 handover adds the interlock-only portion of the nominal valve
    # budget. With a slower valve the same interlock overhead still applies.
    handover_s = process["handover_interlock_s"]
    tolerance = (1 + pump["torque_tolerance"]) * pump["speed_ceiling_rpm"] / pump["rated_motor_rpm"]
    extra_shift_L = (cfg["rapid_pair"]["regen_pilot_shift_L"]
                    + (cfg["mp"]["pilot_shift_L"] if cfg["mp"] else 0.)
                    + cfg["valves"]["mf_extra_pilot_shift_L"])
    runs, power = [], []
    delta_s = None
    for step_s in STEPS_S:
        try:
            run = periodic_run(model, cylinder, process["bulk_density_kg_m3"],
                               process["feed_s"], settings, step_s)
        except RuntimeError as exc:
            return dict(feasible=False, reason=str(exc), required_peak_working_bar=None)
        if not run["feasible"]:
            return run
        runs.append(run)
        power.append(shaft_balance(run, pilot, settings["switch_s"], handover_s,
                                   pump["combined_shaft_limit_kW"], tolerance, extra_shift_L))
        if len(runs) > 1:
            delta_s = abs(runs[-1]["cycle_s"] - runs[-2]["cycle_s"])
            if delta_s <= CONVERGENCE_S:
                break

    slowest = max(zip(runs, power), key=lambda pair: pair[1]["cycle_s"])[0]
    cycle_s = max(row["cycle_s"] for row in power)
    # Envelope average and RMS independently. Express the corresponding
    # first and second energy integrals over the reported conservative cycle.
    avg_kW = max(row["average_kW"] for row in power)
    rms_kW = max(row["rms_kW"] for row in power)
    peak_kW = max(row["peak_kW"] for row in power)
    pilot_bar = min(row["minimum_pilot_bar"] for row in power)
    phases = {name: event | {"travel_mm": slowest["motion_steps"][name][-1][-1]}
              for name, event in slowest["motion_events"].items()}
    travel_mm, residual_mm = axis_travel(slowest, sequence)
    return dict(
        feasible=True, cycle_s=cycle_s, average_power_kW=avg_kW, rms_power_kW=rms_kW,
        total_motor_energy_kJ=avg_kW * cycle_s, squared_power_time_kW2_s=rms_kW**2 * cycle_s,
        peak_drive_power_kW=peak_kW, max_pressure_bar=max(
            max(run["peak_working_bar"] for run in runs), pilot["max_load_bar"],
            cfg["lp"]["high_bar"] + cfg["lp"]["charge_drop_bar"],
            cfg["mp"]["high_bar"] + cfg["lp"]["charge_drop_bar"] if cfg["mp"] else 0.),
        peak_hydraulic_power_kW=max(row[3] * row[8] / 600 for run in runs for row in run["power_steps"]),
        minimum_pilot_bar=pilot_bar, minimum_pilot_setpoint_bar=pilot["low_bar"],
        nominal_press_supply_bar=slowest["nominal_setpoint_bar"],
        press_force_N=model.axial_force_N(model.press_end_m, process["bulk_density_kg_m3"]),
        press_configuration_valid=sequence["press"].mode == "extend",
        fill=fill, interlocks_met=all(sequence_checks(run) for run in runs),
        accumulator_pressure_covered=all(
            abs(run["net_lp_oil_balance_L"]) <= 1e-5
            and abs(run["mp_boost_L"] - run["mp_recharged_L"]) <= 1e-5
            and run["min_lp_gas_bar"] >= cfg["lp"]["low_bar"] - 1e-8 for run in runs),
        lp_assist_L=slowest["boost_L"], mp_assist_L=slowest["mp_boost_L"],
        switch_count=slowest["switch_count"], total_pump_oil_L=slowest["pump_oil_L"],
        phases=phases, stages=slowest["stage_events"], switches=slowest["switches"], handover_interlock_s=handover_s,
        actuator_travel_mm=travel_mm, actuator_residual_mm=residual_mm,
        integration=dict(adjacent_delta_s=delta_s, limit_s=CONVERGENCE_S, converged=delta_s <= CONVERGENCE_S,
                         grids=[{"step_s": run["dt_s"], **row} for run, row in zip(runs, power, strict=True)]),
    )

