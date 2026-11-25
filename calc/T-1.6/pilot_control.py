"""Pilot charge scheduled in windows with measured shaft capacity."""
from bisect import bisect_right
from math import fsum, sqrt


def pilot_replay(run, pilot, demand, cfg, extra_s, limit_kW):
    """Evaluate an AX controller with a whole-block torque reservation."""
    total_s = run["cycle_s"] + extra_s
    block_s = cfg["reservation_window_s"]
    switching_s = cfg["valve_response_s"]
    steps = run["power_steps"]
    leaks = demand["pilot_leak_intervals_s_and_L_min"]
    leak_ends = [stop for _, stop, _ in leaks]
    # Use the linear pressure bound and a separate hot leakage margin.
    hot_scale = cfg["max_pilot_bar"] / 100 * cfg["hot_leak_factor"]
    cold_scale = sqrt(cfg["max_pilot_bar"] / 100)
    max_leak = max(rate for _, _, rate in leaks) * hot_scale / cold_scale
    shift_L = cfg["actuation_and_aux_bound_L_per_cycle"]
    average_shift_L_min = shift_L * 60 / total_s
    draw_L = 0.0
    blocks = []
    rows_per_block = max(1, round(block_s / run["dt_s"]))
    for index in range(0, len(steps), rows_per_block):
        block = steps[index:index + rows_per_block]
        duration_s = fsum(step[1] for step in block)
        peak_kW = max(step[5] for step in block)
        leak_L = fsum(step[1] * (leaks[min(bisect_right(leak_ends, step[0] + step[1]/2),
                                          len(leaks)-1)][2] * hot_scale / cold_scale
                                 + average_shift_L_min) / 60 for step in block)
        draw_L += leak_L
        blocks.append((duration_s, peak_kW, leak_L, block))

    incremental = {tag: kw - pilot["stage_standby_bound_kW"][tag]
                   for tag, kw in pilot["stage_shaft_bound_kW"].items()}
    options = [("PX", "PXA"), ("PXA",), ("PX",), ()]
    volume_L = pilot["acc_available_150_to_120_L"]
    state_L = volume_L
    headroom_L = cfg["charge_headroom_L"]
    temperature_factor = run["shaft_peak_with_tolerance_kW"] / run["peak_shaft_kW"]
    extra_leak_L = (max_leak + average_shift_L_min) * extra_s / 60
    previous = ()
    for _ in range(40):
        initial_L = state_L
        peak_kW = 0.0
        energy_kJ = 0.0
        square_kW2_s = 0.0
        extra_shaft_kJ = 0.0
        potential_L = 0.0
        delivery_L = 0.0
        minimum_L = state_L
        stage_times_s = dict.fromkeys(incremental, 0.0)
        loads_kW = []
        previous_available = ()
        for dt, base_peak, leak_L, block in blocks:
            available = next(option for option in options
                             if not option or base_peak + fsum(incremental[x] for x in option)
                             + cfg["reserved_shaft_margin_kW"] <= limit_kW)
            usable_s = max(0., dt - switching_s)
            potential_s = dt if available == previous_available else usable_s
            potential_L += potential_s * fsum(pilot["stage_minimum_delivery_L_min"][x] for x in available) / 60
            previous_available = available
            active = available if volume_L - state_L >= headroom_L else ()
            load_kW = fsum(incremental[x] for x in active)
            loads_kW.extend([load_kW] * len(block))
            delivery_this_L = (dt if active == previous else usable_s) * fsum(
                pilot["stage_minimum_delivery_L_min"][x] for x in active) / 60
            # Account for worst drain before crediting the delayed recharge.
            minimum_L = min(minimum_L, state_L - leak_L)
            actual_delivery_L = min(delivery_this_L, volume_L - state_L + leak_L)
            state_L += actual_delivery_L - leak_L
            delivery_L += actual_delivery_L
            previous = active
            for x in active:
                stage_times_s[x] += dt
            extra_shaft_kJ += load_kW * dt
            energy_kJ += fsum(step[1] * (step[4] + load_kW) for step in block)
            square_kW2_s += fsum(step[1] * (step[6] + 2 * step[4] * load_kW + load_kW**2)
                                 for step in block)
            peak_kW = max(peak_kW, base_peak + load_kW)
        state_L -= extra_leak_L
        minimum_L = min(state_L, minimum_L)

    run["pilot_loads_kW"] = loads_kW

    # The modeled handover allowance uses the full main shaft bound.
    # Keep the whole actuation budget in reserve for a worst-timed packet.
    net_minimum_L = minimum_L - shift_L
    gas_precharge_bar_abs = pilot["precharge_bar"] + 1
    gas_at_min_pressure_L = pilot["effective_gas_volume_L"] * (
        gas_precharge_bar_abs / (pilot["operating_min_bar"] + 1))**(1 / 1.4)
    gas_at_depletion_L = min(pilot["effective_gas_volume_L"], gas_at_min_pressure_L - net_minimum_L)
    min_pressure_bar = gas_precharge_bar_abs * (pilot["effective_gas_volume_L"] / gas_at_depletion_L)**1.4 - 1
    return {
        "minimum_pilot_pressure_bar": min_pressure_bar,
        "required_hot_oil_L_per_cycle": draw_L + extra_leak_L,
        "actual_delivery_L_per_cycle": delivery_L,
        "available_charge_L_per_cycle": potential_L,
        "capacity_margin_L_per_cycle": potential_L - draw_L - extra_leak_L,
        "last_cycle_inventory_change_L": state_L - initial_L,
        "ax_usable_minimum_L": net_minimum_L,
        "maximum_hot_connected_leak_L_min": max_leak,
        "charge_stage_s": stage_times_s,
        "pilot_heat_kW": pilot["standby_shaft_bound_kW"] + extra_shaft_kJ / total_s,
        "pilot_incremental_shaft_kJ": extra_shaft_kJ,
        "average_shaft_kW": (energy_kJ + extra_s * limit_kW) / total_s * temperature_factor,
        "rms_shaft_kW": sqrt((square_kW2_s + extra_s * limit_kW**2) / total_s) * temperature_factor,
        "peak_shaft_kW": max(peak_kW, limit_kW if extra_s else 0.) * temperature_factor,
        "hot_balance_pass": potential_L >= draw_L + extra_leak_L and net_minimum_L > 0,
    }
