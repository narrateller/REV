"""Shaft energy, squared power and volume/energy balance of accumulator rails."""

from collections import defaultdict
from math import fsum, sqrt

from pilot_control import pilot_replay
from round2_screens import pilot_cycle
from x1_calc import Accumulator


def shaft_tolerance(study, pump):
    return (1 + pump.tolerance) * (
        study.reference_sources["engineering_inputs"]["regulator_speed_ceiling_rpm"]
        / study.sources["catalogs"]["motor"]["rated_rpm"])


def shaft_balance(study, run, settings, handover_s, extra_pilot_L=0., reservation_s=None):
    tolerance = shaft_tolerance(study, settings["pump"])
    run["shaft_peak_with_tolerance_kW"] = run["peak_shaft_kW"] * tolerance
    run["pilot_available_intervals_s"] = {}
    demand = pilot_cycle(study.circuit, study.interlocks, study.sources16, run, study.pilot, settings["switch_s"])
    pilot_cfg = study.sources16["revision"]["pilot"].copy()
    pilot_cfg["actuation_and_aux_bound_L_per_cycle"] += (
        study.sources["engineering"]["dfe1z_extra_pilot_L_per_cycle"] + extra_pilot_L)
    if reservation_s is not None:
        pilot_cfg["reservation_window_s"] = reservation_s
    pilot = pilot_replay(run, study.pilot, demand, pilot_cfg, handover_s, study.limit_kW)
    shaft_kJ_by_phase = defaultdict(float)
    square_by_phase = defaultdict(float)
    charge_volume_L = defaultdict(float)
    charge_power_kJ = defaultdict(float)
    charge_peak_flow_L_min = defaultdict(float)
    for step, pilot_kW in zip(run["power_steps"], run["pilot_loads_kW"], strict=True):
        _, dt_s, stage, _, mean_kW, _, mean_square_kW2, _, pump_L_min, _ = step
        stage = stage.split("/")[0]
        shaft_kJ_by_phase[stage] += dt_s * (mean_kW + pilot_kW) * tolerance
        square_by_phase[stage] += dt_s * (mean_square_kW2 + 2 * mean_kW * pilot_kW + pilot_kW**2) * tolerance**2
        if stage in ("lp_charge", "mp_charge"):
            charge_volume_L[stage] += dt_s * pump_L_min / 60
            charge_power_kJ[stage] += dt_s * mean_kW * tolerance
            charge_peak_flow_L_min[stage] = max(charge_peak_flow_L_min[stage], pump_L_min)
    shaft_kJ_by_phase["handover"] = handover_s * study.limit_kW * tolerance
    square_by_phase["handover"] = handover_s * (study.limit_kW * tolerance)**2
    duration_s = run["cycle_s"] + handover_s
    shaft_kJ = fsum(shaft_kJ_by_phase.values())
    square_kW2_s = fsum(square_by_phase.values())
    assert abs(shaft_kJ / duration_s - pilot["average_shaft_kW"]) < 1e-8
    assert abs(sqrt(square_kW2_s / duration_s) - pilot["rms_shaft_kW"]) < 1e-8
    return dict(cycle_s=duration_s, shaft_energy_kJ=shaft_kJ, integral_P2_kW2_s=square_kW2_s,
                rms_kW=pilot["rms_shaft_kW"], peak_kW=pilot["peak_shaft_kW"],
                average_kW=pilot["average_shaft_kW"], shaft_tolerance_multiplier=tolerance,
                shaft_energy_kJ_by_header_phase=dict(shaft_kJ_by_phase),
                integral_P2_kW2_s_by_header_phase=dict(square_by_phase),
                pilot=pilot | dict(reservation_s=pilot_cfg["reservation_window_s"],
                                   total_shift_budget_L=pilot_cfg["actuation_and_aux_bound_L_per_cycle"]),
                charge=dict(volume_L=dict(charge_volume_L), shaft_kJ=dict(charge_power_kJ),
                            peak_flow_L_min=dict(charge_peak_flow_L_min)))


def gas_balance(run, settings, shaft):
    """Pressure is gauge. Gas energies exclude ambient-pressure displacement."""
    lp = Accumulator(shell_L=settings["accumulator_shell_L"], **settings["accumulator_kwargs"])
    try_mp = settings.get("mp_accumulator_kwargs")
    rails = {"lp": lp}
    if try_mp:
        rails["mp"] = Accumulator(**try_mp)
    trace = run["motion_steps"]
    energy = run["energy"]
    result = {}
    for name, accumulator in rails.items():
        is_lp = name == "lp"
        column = 4 if is_lp else 5
        oil_L_by_motion = {key: fsum(row[column] for row in motion) for key, motion in trace.items()}
        oil_L_by_motion = {key: value for key, value in oil_L_by_motion.items() if value > 1e-10}
        used_L = run["boost_L"] if is_lp else run["mp_boost_L"]
        recharged_L = run["recharged_L"] if is_lp else run["mp_recharged_L"]
        peak_deficit_L = run["peak_lp_deficit_L"] if is_lp else run["mp_peak_deficit_L"]
        initial_L = 1000 * accumulator.oil_at_m3(accumulator.high_bar)
        accumulator.oil_m3 -= peak_deficit_L / 1000
        pump_charge_kJ = energy["charge_kJ"] if is_lp else energy["mp_charge_kJ"]
        delivered_kJ = energy["boost_kJ"] if is_lp else energy["mp_delivery_kJ"]
        gas_in_kJ = energy[name + "_gas_in_kJ"]
        gas_out_kJ = energy[name + "_gas_out_kJ"]
        peak_flow_L_min = max((60 * row[column] / row[1] for motion in trace.values() for row in motion), default=0.)
        assert abs(recharged_L - used_L) < 1e-5
        assert abs(fsum(oil_L_by_motion.values()) - used_L) < 1e-8
        assert abs(shaft["charge"]["volume_L"].get(name + "_charge", 0.) - recharged_L) < 1e-8
        assert abs(gas_in_kJ - gas_out_kJ) < .005
        result[name] = dict(
            effective_gas_volume_L=accumulator.shell_L, precharge_bar=accumulator.precharge_bar,
            minimum_setpoint_bar=accumulator.low_bar, high_setpoint_bar=accumulator.high_bar,
            minimum_cycle_gas_bar=accumulator.pressure_bar, maximum_delivery_L_min=accumulator.delivery_L_min,
            useful_volume_L=initial_L - 1000 * accumulator.oil_at_m3(accumulator.low_bar),
            peak_deficit_L=peak_deficit_L, initial_oil_L=initial_L, delivered_L=used_L,
            recharged_L=recharged_L, volume_balance_L=recharged_L - used_L,
            delivered_L_by_motion=oil_L_by_motion, peak_actual_delivery_L_min=peak_flow_L_min,
            charge_s_by_window=run[name + "_charge_s_by_window"],
            peak_actual_charge_L_min=shaft["charge"]["peak_flow_L_min"].get(name + "_charge", 0.),
            shaft_charge_kJ=shaft["charge"]["shaft_kJ"].get(name + "_charge", 0.),
            hydraulic_charge_kJ=pump_charge_kJ, hydraulic_delivered_kJ=delivered_kJ,
            gas_stored_kJ=gas_in_kJ, gas_released_kJ=gas_out_kJ, gas_balance_kJ=gas_in_kJ - gas_out_kJ,
            charge_and_delivery_loss_kJ=pump_charge_kJ - delivered_kJ)
    return result
