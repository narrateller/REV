"""Quantify the round-two hydraulic changes using project bounds and catalogues."""
from math import fsum, pi, sqrt


def area_m2(diameter_mm):
    return pi * (diameter_mm / 1000) ** 2 / 4


def aperture_flow_L_min(diameter_mm, cd, pressure_bar, density):
    return cd * area_m2(diameter_mm) * sqrt(2 * pressure_bar * 1e5 / density) * 60_000


def screen(circuit, data, main_cap_dead_L):
    project = data["project"]
    cfg = project["round2"]
    catalogs = data["catalogs"]
    el = circuit["elements"]
    density = project["oil_density_kg_m3"]
    oil_operating_bar = el["AX"]["setpoint"]["operating_max_bar"]
    oil_min_bar = el["AX"]["setpoint"]["operating_min_bar"]
    pilot_gas_bar = el["AX"]["setpoint"]["precharge_bar"] + 1
    theoretical = el["PX"]["displacement_cm3_rev"] * el["PX"]["speed_rev_min"] / 1000
    additional = el["PXA"]["displacement_cm3_rev"] * el["PXA"]["speed_rev_min"] / 1000
    gross_L_min = theoretical + additional
    eta_v = cfg["pilot_eta_v_floor"]
    eta_mech = cfg["pilot_eta_mechanical_floor"]
    pilot = {
        "theoretical_L_min": theoretical, "booster_theoretical_L_min": additional,
        "combined_theoretical_L_min": gross_L_min, "assumed_minimum_delivery_L_min": gross_L_min * eta_v,
        "standby_shaft_bound_kW": cfg["pilot_tandem_unloaded_shaft_bound_kW"],
        "priority_bars": {"PX": cfg["pilot_main_priority_cut_in_bar"], "PXA": cfg["pilot_booster_priority_cut_in_bar"]},
        "stage_minimum_delivery_L_min": {"PX": theoretical * eta_v, "PXA": additional * eta_v},
        "stage_shaft_bound_kW": {
            tag: flow * cfg["pilot_max_load_bar"] / (600 * eta_mech)
            for tag, flow in (("PX", theoretical), ("PXA", additional))
        },
        "stage_standby_bound_kW": {
            tag: cfg["pilot_tandem_unloaded_shaft_bound_kW"] * flow / gross_L_min
            for tag, flow in (("PX", theoretical), ("PXA", additional))
        },
        "shaft_bound_kW": gross_L_min * cfg["pilot_max_load_bar"] / (600 * eta_mech),
        "shaft_at_150_bar_bound_kW": gross_L_min * oil_operating_bar / (600 * eta_mech),
        "acc_available_150_to_120_L": cfg["pilot_high_side_volume_L"]
        * ((pilot_gas_bar / (oil_min_bar + 1)) ** (1 / 1.4)
           - (pilot_gas_bar / (oil_operating_bar + 1)) ** (1 / 1.4)),
        "group_assisted_supply": "PX and PXA on PV180 through shaft, AX bridges priority, XCH reserve",
    }

    bore_mm, rod_mm = el["CYM"]["bore_mm"], el["CYM"]["rod_mm"]
    rapid_a_m2 = 2 * area_m2(90)
    rapid_b_m2 = rapid_a_m2 - 2 * area_m2(50)
    v_m_s = cfg["float_max_speed_m_s"]
    suction_bar = cfg["float_suction_drop_bound_bar"]
    exhaust_bar = cfg["float_exhaust_drop_bound_bar"]
    float_force_N = (rapid_a_m2 * suction_bar + rapid_b_m2 * exhaust_bar) * 1e5
    cap_m2 = area_m2(bore_mm)
    annulus_m2 = cap_m2 - area_m2(rod_mm)
    float_screen = {
        "float_velocity_bound_m_s": v_m_s,
        "tank_makeup_A_L_min": v_m_s * rapid_a_m2 * 60_000,
        "tank_discharge_B_L_min": v_m_s * rapid_b_m2 * 60_000,
        "main_pump_float_L_min": 0,
        "min_A_absolute_bar": cfg["oil_ambient_absolute_bar"] - suction_bar,
        "max_rapid_pair_drag_N": float_force_N,
        "extra_direct_feed_bar": float_force_N / cap_m2 / 1e5,
        "regen_check_dp_bound_bar": cfg["regen_seat_dp_bound_bar"],
    }

    relief_bar = 315
    cd_min = cfg["fault_orifice_min_cd"]
    cd_max = cfg["fault_orifice_max_cd"]
    tol = cfg["fault_orifice_diameter_tolerance_mm"]
    valve_loss_bar = catalogs["SUN_NO"]["project_valve_dp_bound_at_265_L_min_bar"]
    outlet_bar = cfg["fault_return_at_flow_bar"]
    incoming_L_min = el["P1"]["Q_L_min"]
    local_sweep = []
    for tag, orifice in [("ME1", "OE1"), ("ME2", "OE2")]:
        nominal_mm = el[orifice]["DN_mm"]
        minimum_mm = nominal_mm - tol
        min_at_limit_flow_L_min = aperture_flow_L_min(
            minimum_mm, cd_min, relief_bar - outlet_bar - valve_loss_bar, density)
        max_at_limit_flow_L_min = aperture_flow_L_min(nominal_mm + tol, cd_max, relief_bar, density)
        orifice_dp_bar = (incoming_L_min / (60_000 * cd_min * area_m2(minimum_mm))) ** 2 * density / 2e5
        max_bar = orifice_dp_bar + outlet_bar + valve_loss_bar
        local_sweep.append({
            "valve": tag, "minimum_flow_at_315_bar_L_min": min_at_limit_flow_L_min,
            "maximum_flow_at_315_bar_L_min": max_at_limit_flow_L_min,
            "single_open_branch_at_full_pump_bar": max_bar,
            "static_screen_pass": max_bar <= relief_bar and max_at_limit_flow_L_min <= el[tag]["Q_L_min"],
        })
    oil_cap_m3 = cap_m2 * el["CYM"]["stroke_mm"] / 1000 + main_cap_dead_L / 1000
    compliance_m3_Pa = oil_cap_m3 / cfg["fault_oil_bulk_modulus_Pa"] * cfg["fault_compliance_multiplier"]
    initial_slope_bar_s = (incoming_L_min / 60_000) / compliance_m3_Pa / 1e5
    dumps = {
        "full_stroke_cap_with_dead_volume_L": oil_cap_m3 * 1000,
        "effective_volume_compliance_m3_Pa": compliance_m3_Pa,
        "closed_cap_full_pump_initial_pressure_slope_bar_s": initial_slope_bar_s,
        "closed_cap_300_to_315_bar_estimate_s": 15 / initial_slope_bar_s,
        "while_feed_continues": "Pressure can remain above safe opening setpoint. Keep gate inhibited until two independent cap readings permit release.",
        "branches": local_sweep,
        "pump_assumed_stuck_at_L_min": incoming_L_min,
        "fault_path_return_bound_bar": outlet_bar,
        "fault_valve_dp_bound_at_265_L_min_bar": valve_loss_bar,
        "valve_dp_and_transient_confirm_on_test": True,
        "active_delay_protection": ["RV0", "RVM", "RVB"],
        "low_pressure_tail_bleeds": ["MEB1", "MEB2"],
    }
    # Bound float drag and the regeneration seat drop over the full stroke.
    main_full_stroke_m = el["CYM"]["stroke_mm"] / 1000
    extra_work_kJ = main_full_stroke_m * (
        float_force_N + cfg["regen_seat_dp_bound_bar"] * annulus_m2 * 1e5
    ) / 1000
    oil_relief = el["RTF"]
    relief_point_bar = 1.1 * oil_relief["setpoint"]["crack_bar"]
    goetze = catalogs["GOETZE"]
    relief_oil_L_min = aperture_flow_L_min(
        goetze["orifice_mm"], goetze["liquid_discharge_coefficient"] * cfg["TF_relief_viscosity_derating_factor"],
        relief_point_bar - cfg["TF_relief_backpressure_max_bar"], density,
    )
    tf = {"rated_design_L_min": oil_relief["Q_L_min"], "estimated_flow_L_min": relief_oil_L_min,
          "blowoff_inlet_bar": relief_point_bar, "outlet_bar": cfg["TF_relief_backpressure_max_bar"],
          "static_screen_pass": relief_oil_L_min >= oil_relief["Q_L_min"]
          and relief_point_bar <= oil_relief["setpoint"]["max_inlet_at_design_flow_bar"]}
    return {"pilot": pilot, "float": float_screen, "emergency_dump": dumps, "TF_oil_relief": tf,
            "extra_fluid_work_bound_kJ_per_cycle": extra_work_kJ}


def pilot_cycle(circuit, interlocks, data, run, pilot, switch_s):
    """Estimate cyclic pilot draw using actual phase windows from the copied V2 model."""
    el = circuit["elements"]
    cfg = data["project"]["round2"]
    catalogs = data["catalogs"]
    cycle_s = run["cycle_s"]
    by_command = {item["command"]: item["time_s"] for item in run["switches"]}
    motion = run["motion_events"]
    bounds = {
        "pre_down": (by_command["pre_down"], motion["pre_down"]["end_s"]),
        "prefill": (by_command["prefill"], motion["prefill"]["end_s"]),
        "closed_ports": (by_command["regen"], motion["regen"]["start_s"]),
        "regen": (motion["regen"]["start_s"], motion["regen"]["end_s"]),
        "handover_regen_press": (by_command["press"], motion["press"]["start_s"]),
        "press": (motion["press"]["start_s"], motion["press"]["end_s"]),
        "hold": tuple(run["stage_events"]["hold"]),
        "unload": tuple(run["stage_events"]["unload"]),
        "gate_open": (by_command["gate_open"], motion["gate_open"]["end_s"]),
        "eject": (by_command["eject"], motion["eject"]["end_s"]),
        "return": (by_command["return"], motion["return"]["end_s"]),
        "gate_close": (by_command["gate_close"], motion["gate_close"]["end_s"]),
        "pre_up": (by_command["pre_up"], motion["pre_up"]["end_s"]),
        "feed": tuple(run["stage_events"]["feed"]),
    }
    intervals = []
    phases = interlocks["phases"] | interlocks["switching_windows"]
    for name, (start, end) in bounds.items():
        phase = phases[name]
        cmd = phase["commands"] | phase.get("optional_lp", {}).get("commands", {})
        rails = {el[tag]["ports"]["2"] for tag, state in cmd.items()
                 if tag.startswith("XG") and state == "open"}
        intervals.append((start, end, rails))
    intervals.extend((start, min(start + switch_s, cycle_s), {"XN"}) for start in by_command.values())

    # The catalogue leakage data are at 100 bar. Square-root pressure scaling
    # is a design estimate for the orifice-like leakage, with a separate factor.
    p_scale = sqrt(el["AX"]["setpoint"]["operating_max_bar"] / 100)
    wrce_max = catalogs["WRC"]["zero_flow_max_L_min_at_100bar"]
    wrce_avg = catalogs["WRC"]["zero_flow_avg_L_min_at_100bar"]
    wrle_max = catalogs["WRLE"]["pilot_stage_max_L_min_at_100bar"]
    gross_unsectioned = (16 * wrce_max + 2 * wrle_max) * p_scale
    devices = {
        name: (item["ports"]["X"], wrce_max if item["source"] == "WRC" else wrle_max)
        for name, item in el.items()
        if item["type"] in {"proportional_2_2", "directional_4_3"} and item["source"] in {"WRC", "WRLE"}
    }
    charge_intervals = run["pilot_available_intervals_s"]
    edges = sorted({0.0, cycle_s, *(x for start, end, _ in intervals for x in (start, end)),
                    *(x for group in charge_intervals.values() for span in group for x in span)})
    leaks = []
    for lo, hi in zip(edges, edges[1:]):
        middle = (lo + hi) / 2
        rails = set().union(*(rail for start, end, rail in intervals if start <= middle < end))
        rate = p_scale * fsum(leak for rail, leak in devices.values() if rail in rails)
        supply = fsum(pilot["stage_minimum_delivery_L_min"][tag]
                      for tag, spans in charge_intervals.items()
                      if any(start <= middle < end for start, end in spans))
        leaks.append((lo, hi, rate, supply))
    total_leak_L = fsum((hi - lo) * rate / 60 for lo, hi, rate, _ in leaks)
    linear_scaled_leak_L = total_leak_L * p_scale
    supply_L = fsum((hi - lo) * supply / 60 for lo, hi, _, supply in leaks)
    # The lumped shift budget also covers LC2A actuators and line refills.
    # Allocate the entire amount to the worst depletion interval as a bound.
    shift_L = cfg["pilot_max_admissible_switch_oil_L"]
    draw = 0
    worst_drop = 0
    for lo, hi, rate, supply in leaks * 2:
        draw = max(0, draw + (hi - lo) * (rate - supply) / 60)
        worst_drop = max(worst_drop, draw)
    thermal_oil_L = (total_leak_L + shift_L) / cfg["pilot_eta_v_floor"]
    load_time_s = thermal_oil_L * 60 / pilot["combined_theoretical_L_min"]
    max_charge_kW = (pilot["combined_theoretical_L_min"] * cfg["pilot_thermal_charge_max_bar"]
                     / (600 * cfg["pilot_eta_mechanical_floor"]))
    heat_bound_kW = (max_charge_kW * load_time_s + pilot["standby_shaft_bound_kW"] * (cycle_s - load_time_s)) / cycle_s
    return {
        "charge_available_s": {tag: fsum(end - start for start, end in spans)
                               for tag, spans in charge_intervals.items()},
        "heat_bound_kW": heat_bound_kW,
        "catalogue_at_100_bar": {
            "2WRCE_reference_count": 16, "2WRCE_installed_count": sum(el[id]["source"] == "WRC" for id in devices),
            "2WRCE_average_each_L_min": wrce_avg, "2WRCE_maximum_each_L_min": wrce_max,
            "4WRLE_count": 2, "4WRLE_pilot_only_maximum_each_L_min": wrle_max,
            "unsectioned_maximum_L_min": 16 * wrce_max + 2 * wrle_max,
        },
        "uncut_150_bar_maximum_L_min": gross_unsectioned,
        "maximum_connected_leak_L_min": max(rate for _, _, rate, _ in leaks),
        "cycle_leak_L": total_leak_L, "cycle_supply_L": supply_L,
        "net_per_cycle_with_linear_leak_scaling_L": supply_L - linear_scaled_leak_L - shift_L,
        "lumped_switch_and_aux_budget_L": shift_L, "net_per_cycle_L": supply_L - total_leak_L - shift_L,
        "estimated_pilot_drained_between_recharge_L": worst_drop + shift_L,
        "reserve_above_lumped_switch_oil_L": supply_L - total_leak_L - shift_L,
        "periodic_balance_screen_pass": supply_L >= total_leak_L + shift_L,
        "ax_depletion_screen_pass": worst_drop + shift_L < pilot["acc_available_150_to_120_L"],
        "phase_windows_s": bounds,
        "charge_test_pending": True,
    }

