"""T-1.6 AX charge replay on the X-1 trace, inherited through T-2.6."""

from bisect import bisect_right
from math import fsum, inf, sqrt


def pilot_leaks(run, cfg, switch_s):
    command = {row["command"]: row["time_s"] for row in run["switches"]}
    motion = run["motion_events"]
    bounds = {name: (command[name], motion[name]["end_s"]) for name in
              ("pre_down", "prefill", "gate_open", "eject", "return", "gate_close", "pre_up")}
    bounds.update({name: run["stage_events"][name] for name in ("hold", "unload", "feed")})
    bounds.update({name: (motion[name]["start_s"], motion[name]["end_s"]) for name in ("regen", "press")})
    bounds["closed_ports"] = command["regen"], motion["regen"]["start_s"]
    bounds["handover_regen_press"] = command["press"], motion["press"]["start_s"]
    cycle_s = run["cycle_s"]
    windows = [(start, end, cfg["rail_connections"][name]) for name, (start, end) in bounds.items()]
    windows.extend((start, min(start + switch_s, cycle_s), ("XN",)) for start in command.values())
    edges = sorted({0., cycle_s, *(x for start, end, _ in windows for x in (start, end))})
    # Catalogue leakage at 100 bar, scaled by pressure and the hot allowance
    # as in pilot_replay. Active rails are a union during overlapped commands.
    p_scale = sqrt(cfg["high_bar"] / 100)
    hot_scale = cfg["high_bar"] / 100 * cfg["hot_leak_factor"]
    rates = cfg["leak_L_min_at_100_bar"]
    leaks = []
    for start, end in zip(edges, edges[1:]):
        middle = (start + end) / 2
        rails = {rail for lo, hi, active in windows if lo <= middle < hi for rail in active}
        rate_L_min = p_scale * fsum(rate for rail, rate in rates if rail in rails) * hot_scale / p_scale
        leaks.append((end, rate_L_min))
    return leaks


def shaft_balance(run, cfg, switch_s, handover_s, combined_limit_kW, tolerance, extra_shift_L):
    """Allocate PX/PXA charging and take the worst RMS over the 200-cycle replay."""
    leaks = pilot_leaks(run, cfg, switch_s)
    ends, rates = zip(*leaks)
    cycle_s = run["cycle_s"] + handover_s
    shift_L = cfg["valve_shift_budget_L"] + cfg["dfe1z_shift_budget_L"] + extra_shift_L
    shift_L_min = shift_L * 60 / cycle_s
    extra_leak_L = (max(rates) + shift_L_min) * handover_s / 60
    gross_L_min = [disp * cfg["tandem_rpm"] / 1000 for disp in cfg["tandem_displacement_cm3_rev"]]
    flow_L_min = [q * cfg["vol_efficiency"] for q in gross_L_min]
    incremental_kW = [q * cfg["max_load_bar"] / (600 * cfg["mech_efficiency"])
                      - cfg["standby_kW"] * q / fsum(gross_L_min) for q in gross_L_min]
    accumulator_bar_abs = cfg["precharge_bar"] + 1
    n = cfg["polytropic_exponent"]
    gas_at_low_L = cfg["gas_volume_L"] * (accumulator_bar_abs / (cfg["low_bar"] + 1))**(1 / n)
    volume_L = gas_at_low_L - cfg["gas_volume_L"] * (accumulator_bar_abs / (cfg["high_bar"] + 1))**(1 / n)

    blocks = []
    rows = run["power_steps"]
    rows_per_block = max(1, round(cfg["reservation_window_s"] / run["dt_s"]))
    for index in range(0, len(rows), rows_per_block):
        block = rows[index:index + rows_per_block]
        duration_s = fsum(row[1] for row in block)
        peak_kW = max(row[5] for row in block)
        leak_L = fsum(dt * (rates[min(bisect_right(ends, time + dt / 2), len(rates) - 1)]
                             + shift_L_min) / 60 for time, dt, *_ in block)
        available = next(stages for stages in ((0, 1), (1,), (0,), ())
                         if not stages or peak_kW + fsum(incremental_kW[i] for i in stages)
                         + cfg["reserved_shaft_margin_kW"] <= combined_limit_kW)
        # The pilot power is constant within a block, so pre-integrate the
        # base power and its square once for the entire periodic replay.
        blocks.append((duration_s, peak_kW, leak_L, available,
                       fsum(row[1] * row[4] for row in block), fsum(row[1] * row[6] for row in block)))

    inventory_L = volume_L
    previous = ()
    lowest_L = inf
    peak_kW = combined_limit_kW if handover_s else 0.
    worst_kW2_s, worst_kJ = -1., 0.
    for _ in range(200):
        energy_kJ = integral_kW2_s = 0.
        for duration_s, base_peak, leak_L, available, base_kJ, base_kW2_s in blocks:
            active = available if volume_L - inventory_L >= cfg["charge_headroom_L"] else ()
            load_kW = fsum(incremental_kW[i] for i in active)
            charge_s = duration_s if active == previous else max(0., duration_s - cfg["valve_response_s"])
            delivery_L = charge_s * fsum(flow_L_min[i] for i in active) / 60
            lowest_L = min(lowest_L, inventory_L - leak_L)
            inventory_L += min(delivery_L, volume_L - inventory_L + leak_L) - leak_L
            previous = active
            energy_kJ += base_kJ + duration_s * load_kW
            integral_kW2_s += base_kW2_s + 2 * base_kJ * load_kW + duration_s * load_kW**2
            peak_kW = max(peak_kW, base_peak + load_kW)
        inventory_L -= extra_leak_L
        lowest_L = min(lowest_L, inventory_L)
        if integral_kW2_s > worst_kW2_s:
            worst_kW2_s, worst_kJ = integral_kW2_s, energy_kJ

    minimum_inventory_L = lowest_L - shift_L
    gas_at_depletion_L = min(cfg["gas_volume_L"], gas_at_low_L - minimum_inventory_L)
    min_pilot_bar = accumulator_bar_abs * (cfg["gas_volume_L"] / gas_at_depletion_L)**n - 1
    energy_kJ = (worst_kJ + handover_s * combined_limit_kW) * tolerance
    square_kW2_s = (worst_kW2_s + handover_s * combined_limit_kW**2) * tolerance**2
    return dict(cycle_s=cycle_s, shaft_energy_kJ=energy_kJ, average_kW=energy_kJ / cycle_s,
                rms_kW=sqrt(square_kW2_s / cycle_s), peak_kW=peak_kW * tolerance,
                integral_P2_kW2_s=square_kW2_s, minimum_pilot_bar=min_pilot_bar)

