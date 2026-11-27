"""Build serial G-CYCLE inputs from static hydraulic and mechanical bounds."""

from copy import deepcopy
from math import floor, fsum

from make_params_t14b import close_projected_coordinates, equivalent_rod_mm, motion_rows, swept_bands
from x1_calc import Accumulator, area_m2, motions


ORDER = ("pre_down", "prefill", "regen", "press", "hold", "unload", "gate_open", "eject",
         "return", "gate_close", "pre_up", "feed")
PAUSES = ("hold", "unload", "feed")


def project(params_v1, model, cylinder, settings, bulk_kg_m3, feed_s, gate, study, pump_guard, shaft_factor):
    """Project displacement/load laws without using simulated trajectories or timing."""
    params = deepcopy(params_v1)
    drive = params["drive"]
    pump = settings["pump"]
    peak_kW = study.limit_kW * shaft_factor
    relief_work_bar = study.criteria["C-HYD-01"]["max_working_bar"]
    lp = Accumulator(shell_L=settings["accumulator_shell_L"], **settings["accumulator_kwargs"])
    charge_bar = lp.high_bar + settings["charge_drop_bar"]
    delivery_bar = lp.low_bar - settings["charge_drop_bar"]
    available_L = 1000 * (lp.oil_at_m3(lp.high_bar) - lp.oil_at_m3(lp.low_bar))
    # Bound useful high-pressure flow with the catalogue reading uncertainties
    # and the allowed hot deadhead loss. Reserving the full errors here avoids
    # relying on a linear reduction of those errors at partial swash.
    q_max_L_min = min(settings["max_L_min"], pump.capacity_L_min(charge_bar))
    def guarded_flow_L_min(bar):
        point = pump.section(pump.names[0], bar)
        reserve_kW = pump_guard["curve_shaft_uncertainty_kW"] + pump_guard["hot_deadhead_reserve_kW"]
        power_limited_flow_L_min = (pump.limit_kW - pump.loss_kW - point.deadhead_kW - reserve_kW
                                    ) / point.incremental_kW_per_L_min
        return min(q_max_L_min, point.flow_L_min, power_limited_flow_L_min) - pump_guard["curve_delivery_uncertainty_L_min"]

    pressure_grid_bar = range(int(charge_bar), int(relief_work_bar) + 1)
    effective_eta, limiting_bar = min((bar * guarded_flow_L_min(bar) / (600 * peak_kW), bar)
                                     for bar in pressure_grid_bar)
    drive.update(eta=floor(1000 * effective_eta) / 1000, peak_kW=peak_kW,
                 pump_max_flow_L_min=q_max_L_min,
                 idle_kW=pump.operating_point(pump.standby_bar, 0.)[1] * shaft_factor)
    # Schema v1 has one rail. The optional MP vessel is tested in the reference;
    # the gate credits only the installed LP rail and its guaranteed delivery.
    drive["accumulator"].update(usable_oil_L=available_L, max_flow_L_min=lp.delivery_L_min,
                                min_delivery_pressure_bar=delivery_bar, charge_pressure_bar=charge_bar)
    sequence = motions(model, cylinder, bulk_kg_m3, settings["prefill"])
    bands = {name: swept_bands(motion, {}, delivery_bar, pump.standby_bar)
             for name, motion in sequence.items()}

    def volume_m3(name):
        return sequence[name].entry_compress_m3 + fsum(band[4] for band in bands[name])

    rod_mm = equivalent_rod_mm(cylinder.cap_m2, volume_m3("press"),
                               fsum(volume_m3(key) for key in ("prefill", "regen", "eject")),
                               volume_m3("return"))
    rod_m2 = area_m2(rod_mm)
    equivalent_main_areas = dict(prefill=rod_m2, regen=rod_m2, press=cylinder.cap_m2,
                                 eject=rod_m2, **{"return": cylinder.cap_m2 - rod_m2})
    terminal_bar = sequence["press"].pressure_bar(sequence["press"].stroke_m)
    roof_delta_mm = round(model.transfer_m * 1000 - 15)
    params["main_cylinder"].update(rod_mm=rod_mm, stroke_mm=cylinder.stroke_mm, p_work_bar=terminal_bar,
                                   working_range_mm=params["main_cylinder"]["working_range_mm"] + roof_delta_mm)
    params["chamber"]["ejection_overtravel_mm"] += roof_delta_mm
    params["chamber"]["length_mm"] += roof_delta_mm
    cycle = []
    pause_s = dict(hold=settings["hold_s"], unload=settings["unload_s"], feed=feed_s)
    if settings.get("pilot_idle_s"):
        pause_s["pilot_reserve"] = settings["pilot_idle_s"]
    # A stationary swash going to full delivery has half a ramp of missing
    # volume. Keep it separate from the fixed gate valve window. The valve
    # window can absorb a part of the overall command-to-delivery allowance.
    onstroke_deficit_s = .5 / pump.slew(pump.standby_bar, True)
    switch_s = settings["switch_s"]
    handover_s = (study.interlocks["switching_windows"]["handover_regen_press"]["modeled_switch_budget_s"]
                  - study.reference_sources["engineering_inputs"]["valve_allowance_s"])
    for name in (*ORDER, *(name for name in pause_s if name not in PAUSES)):
        if name in pause_s:
            cycle.append(dict(name=name, actuator="none", dwell_s=pause_s[name]))
            continue
        motion = sequence[name]
        rows, _ = motion_rows(motion, bands[name], equivalent_main_areas.get(name, motion.flow_area_m2), {},
                              use_boost=name in settings["boost_branches"])
        if motion.entry_compress_m3:
            rows[0]["name"] = f"{name} port compression"
        rows[0]["start_delay_s"] = max(0., switch_s + onstroke_deficit_s
                                       + (handover_s if name == "press" else 0.) - gate.SWITCH_S)
        cycle.extend(rows)

    close_projected_coordinates(cycle)
    params["cycle"] = cycle
    params["description"] = (f"T-2.6 round 2, X={model.transfer_m * 1000:.0f} mm, A4VSO180 DFE1Z. "
                             "Static pressure and displacement bands. Serial commands with 100 ms valve waits. "
                             "Main rod and phase strokes are hydraulic equivalents, not geometry.")
    gate.validate_params(params)
    return params, dict(eta=drive["eta"], pump_max_flow_L_min=q_max_L_min, lp_usable_oil_L=available_L,
                        eta_limiting_pressure_bar=limiting_bar,
                        guarded_delivery_at_limiting_pressure_L_min=guarded_flow_L_min(limiting_bar),
                        onstroke_deficit_s=onstroke_deficit_s,
                        main_oil_L_by_motion={key: 1000 * volume_m3(key) for key in equivalent_main_areas},
                        boost_bands_by_motion={key: sum(band[0][1] for band in bands[key])
                                               for key in sequence if key in settings["boost_branches"]})


def gate_phases(gate_result):
    timings = {}
    for name in ORDER:
        rows = [row for row in gate_result["details"]["phases"] if row["name"].split()[0] == name
                or (name == "regen" and row["name"] == "closed ports oil compression")]
        timings[name] = rows[-1]["end_s"] - rows[0]["command_start_s"]
    return timings


def phase_table(result, run, handover_s, v1, round1):
    commands = {row["command"]: row["time_s"] for row in run["switches"]}
    current = gate_phases(result)
    table = {}
    for name in ORDER:
        if name in PAUSES:
            start_s, end_s = run["stage_events"][name]
        else:
            start_s, end_s = commands[name], run["motion_events"][name]["end_s"]
        reference_s = end_s - start_s + (handover_s if name == "press" else 0.)
        table[name] = dict(reference_s=reference_s, v1_s=v1[name], round1_s=round1[name], round2_s=current[name])
    return table
