"""Round-two interlock and pressure-path checks on the functional model."""
from collections import defaultdict
from copy import deepcopy

from build_scheme import CLEAR, NOSE, PRESS, RAPID

FLOAT_PHASES = ("closed_ports", "regen", "press")
HANDOVER = "handover_regen_press"
CAP_SAFE = {"cap1_bar <= 3", "cap2_bar <= 3"}
NOSE_GUARD = {"gate_closed", *NOSE}
SAFE_DEFAULTS = {
    "ZU": "open", "ZUP": "vent", "ME1": "open", "ME2": "open",
    "MEB1": "open", "MEB2": "open", "MEB": "open",
    "SAL": "bleed", "SAX": "bleed", "XV": "open", "XVA": "open", "MF": "closed", "MBT": "closed",
}
FAULT_ROUTES = (
    ("P1.P", "T0.U", ("ZU",)), ("ZU.X", "T0.DZ", ("ZUP",)),
    ("CYM.A", "T0.EA", ("ME1", "OE1")), ("CYM.A", "T0.EB", ("ME2", "OE2")),
    ("CYM.A", "T0.EA", ("MEB1",)), ("CYM.A", "T0.EB", ("MEB2",)),
    ("CYM.B", "T0.ER", ("MEB",)), ("ALP.A", "T0.T", ("SAL", "F2")),
    ("AX.A", "T0.T", ("SAX", "F2")), ("PX.P", "T0.T", ("XV", "F2")),
    ("PXA.P", "T0.T", ("XVA", "F2")),
)
RELIEFS = {
    "CYM.A": "RVM", "CYM.B": "RVB", "CYR1.A": "RRA", "CYR1.B": "RRB",
    "CYR2.A": "RRA", "CYR2.B": "RRB", "PCY.A": "RVA", "PCY.B": "RVP",
    "CYG.A": "RGA", "CYG.B": "RGB", "MR.A": "RMR", "MP.A": "RMH",
    "PL1.T": "RPH", "VR.P": "RHR", "TF.A": "RTF",
}
SINKS = ("T0.T", "T0.E", "T0.RF", "T0.EM", "T0.ER", "T0.EP", "T0.EQ", "T0.ET")


def conditions(config, *fields):
    return {guard for field in fields for guard in config.get(field, [])}


def safety_checks(circuit, interlocks, make_graph, find_route):
    elements = circuit["elements"]
    phases = interlocks["phases"]
    common = interlocks["defaults"]["common_commands"]
    windows = interlocks.get("switching_windows", {})
    handover = windows.get(HANDOVER, {})
    errors = []
    guarded_pressure = {}

    def require(ok, message):
        if not ok:
            errors.append(message)

    def graph(commands):
        return make_graph(elements, commands, errors)

    def path(links, start, end, *via):
        try:
            return find_route(elements, links, (start, end), via) is not None
        except (AttributeError, KeyError, ValueError):
            return False

    def proof_routes(name, commands):
        links = graph(commands)
        for start, end, via in FAULT_ROUTES:
            require(path(links, start, end, *via), f"{name}: missing safe route {start} → {end} via {via}")
        require(not path(links, "CYM.A", "TF.A") and not path(links, "CYM.B", "TF.A"),
                f"{name}: fault releases stored pressure into TF")

    for tag, state in SAFE_DEFAULTS.items():
        item = elements.get(tag, {})
        require(item.get("default_state") == state, f"deenergized {tag}: expected {state}")
        if tag in ("SAL", "SAX"):
            require(item.get("electrical_bleed") == "normally_open", f"{tag}: specify NO electric release")
    require(elements.get("ZU", {}).get("source") == "LC_MON"
            and elements.get("ZU", {}).get("monitoring") in elements
            and elements.get("ZUP", {}).get("default_state") == "vent",
            "ZU: independent monitored seat and spring-return pilot vent required")
    for tag, feedback in [("MF", "mf_locked"), ("MBT", "mbt_locked")]:
        item = elements.get(tag, {})
        require(item.get("closing_variant") == "WK"
                and elements.get(item.get("monitoring"), {}).get("sensor") == feedback,
                f"{tag}: monitored WK lock required")
    safety_channels = interlocks.get("safety_outputs", {}).get("channels", {})
    require(safety_channels.get(1, {}).get("output") == "M1"
            and safety_channels.get(1, {}).get("feedback") == "m1_off_confirmed"
            and safety_channels.get(2, {}).get("output") == "ZUP"
            and safety_channels.get(2, {}).get("feedback") == "zu_closed",
            "pump stop: independent motor and ZU controls with feedback required")
    proof_routes("deenergized", {})
    for fault in ("stop", "nose_loss"):
        config = interlocks.get("faults", {}).get(fault, {})
        commands = config.get("commands", {})
        require(config.get("lock_release_commands") == [], f"{fault}: remove both WK enables")
        for pump in ("P1", "PX", "PXA"):
            require(commands.get(pump) == "off", f"{fault}: remove power from {pump}")
        for tag, state in SAFE_DEFAULTS.items():
            require(commands.get(tag) == state, f"{fault}: missing explicit safe command {tag}={state}")
        proof_routes(fault, commands)

    def guards_for(config):
        return conditions(config, "conditions", "common_conditions", "additional_conditions")

    for name, needed in {
        "gate_open": CAP_SAFE, "press": NOSE_GUARD | {"zsf_closed", "mf_locked", "mbt_locked"},
        "regen": NOSE_GUARD | {"mf_locked", "mbt_locked"}, "hold": NOSE_GUARD | {"mf_locked", "mbt_locked"},
    }.items():
        require(needed <= guards_for(phases.get(name, {})), f"{name}: missing safety conditions {sorted(needed)}")
    require(CAP_SAFE | {"main_b_bar <= 3"} <= conditions(phases.get("return", {}), "entry_conditions"),
            "return: safe cap channels and rod pressure required before opening")
    for name, config in phases.items():
        require({"tank_level_ok", "oil_C <= 55", "zu_closed"} <= guards_for(config),
                f"{name}: reservoir and ZU interlocks required")
        commands = common | config.get("commands", {})
        if commands.get("MF") == "open" or commands.get("MBT") == "open":
            require(CAP_SAFE | {"main_b_bar <= 3"} <= conditions(config, "entry_conditions")
                    and "prefill_bar < 1.2" in guards_for(config)
                    and set(config.get("lock_release_commands", [])) ==
                    {tag for tag in ("MF","MBT") if commands.get(tag) == "open"},
                    f"{name}: low-pressure TF opening interlock missing")
        if name in {"closed_ports", "regen", "press", "hold"}:
            require({"mf_locked", "mbt_locked"} <= guards_for(config)
                    and commands.get("XGF") == commands.get("XGFR") == "open"
                    and not config.get("lock_release_commands"),
                    f"{name}: WK locks on TF supply ports must be piloted closed")
        require(not (commands.get("MR") == "open" and commands.get("MT") == "open"),
                f"{name}: MR and MT overlap outside timed handover")

    windows_with_overlap = [name for name, cfg in windows.items()
                            if all(cfg.get("commands", {}).get(tag) == "open" for tag in ("MR", "MT"))]
    ctl = handover.get("commands", {})
    timeout = handover.get("timeout_s", 0)
    overlap = handover.get("max_edge_overlap_s", 0)
    modeled = handover.get("modeled_switch_budget_s", 0)
    require(windows_with_overlap == [HANDOVER] and handover.get("from") == "regen"
            and handover.get("to") == "press" and 0 < overlap < timeout <= modeled <= .1
            and ctl.get("MP") == "closed" and handover.get("on_loss") == "stop"
            and {"mp_closed", "main_b_bar <= 145"} <= conditions(handover, "continuation_conditions")
            and {"mr_edge_pct <= 0", "mt_edge_pct >= 5"} <= conditions(handover, "exit_conditions"),
            "handover: exclusive timed edge overlap with pump isolated and rod pressure monitored")
    require({"mr_edge_pct <= 0", "mt_edge_pct >= 5"} <= guards_for(phases.get("press", {})),
            "press: verify both edges before resuming MP")
    require(path(graph(common | ctl), "CYM.B", "T0.T", "MT", "F2"),
            "handover: MT must open to tank before MR closes")
    require(not path(graph(common | ctl), "P1.P", "CYM.A"), "handover: power feed still reaches MA")

    for name, config in [(phase, phases.get(phase, {})) for phase in FLOAT_PHASES] + [(HANDOVER, handover)]:
        commands = common | config.get("commands", {})
        links = graph(commands)
        active_guards = guards_for(config) | conditions(config, "continuation_conditions")
        require(commands.get("VR", elements.get("VR", {}).get("default_state")) == "center"
                and {"float_a_open", "float_b_open"} <= active_guards,
                f"{name}: VR at center and both float positions required")
        for cyl in ("CYR1", "CYR2"):
            for port in ("A", "B"):
                chamber = f"{cyl}.{port}"
                require(path(links, chamber, "T0.RF", f"RF{port}")
                        and path(links, "T0.RF", chamber, f"RC{port}")
                        and not path(links, "P1.P", chamber) and not path(links, "ALP.A", chamber),
                        f"{name}: {chamber} must float and refill from tank without pump/LP feed")
    for name in ("prefill", "eject", "return"):
        config = phases.get(name, {})
        links = graph(common | config.get("commands", {}))
        for port in ("A", "B"):
            require(not path(links, f"CYR1.{port}", "T0.RF", f"RF{port}"),
                    f"{name}: rapid work port {port} still in float")

    hold = graph(common | phases.get("hold", {}).get("commands", {}))
    press = graph(common | phases.get("press", {}).get("commands", {}))
    regen = graph(common | phases.get("regen", {}).get("commands", {}))
    require(path(regen, "CYM.B", "CYM.A", "MR", "MRC")
            and not path(hold, "CYM.A", "MR.A") and not path(press, "CYM.A", "MR.A"),
            "MR: port A exposed to high cap pressure or loss of seat separation")
    require(all(not path(links, start, "TF.A") for links in (hold, press)
                for start in ("CYM.A", "CYM.B", "P1.P")),
            "TF: supply or work chamber reaches TF during high pressure")
    relief_branch = interlocks.get("operating_branches", {}).get("relief_tank_oil", {})
    require(relief_branch.get("actuation") == "mechanical", "TF: oil relief must be mechanical")
    require(path(graph({"RTF": "relief"}), "TF.A", "T0.ET", "RTF")
            and elements.get("RTF", {}).get("setpoint", {}).get("max_inlet_at_design_flow_bar", float("inf")) <= 3,
            "TF: missing independent oil side relief to tank")

    all_closed = {tag: "closed" for tag, element in elements.items()
                  if element["type"] in {"proportional_2_2", "poppet_2_2", "load_hold"}}
    for pocket, valve in RELIEFS.items():
        rated = elements.get(valve, {}).get("setpoint", {}).get("max_inlet_at_design_flow_bar", float("inf"))
        limit = 3 if pocket == "TF.A" else 315
        links = graph(all_closed | ({valve: "relief"} if valve in elements else {}))
        require(rated <= limit and any(path(links, pocket, sink, valve) for sink in SINKS),
                f"{pocket}: trapped volume without independent pressure relief via {valve}")

    window = phases.get("pre_up", {}).get("movement_window", {})
    clear = set(CLEAR)
    require(window.get("position_sensor") == "shoe_mm" and window.get("origin") == "latch_at_motion_command"
            and window.get("direction") == "decreasing" and window.get("release_travel_mm") == 12
            and 0 < window.get("timeout_s", 0) <= .25 and clear <= set(window.get("require_by_deadline", []))
            and not (clear & conditions(phases.get("pre_up", {}), "entry_conditions", "continuation_conditions", "conditions")),
            "pre_up: nose clearance must be proved after command by the travel/deadline")

    main = elements.get("CYM", {})
    bore, rod = main.get("bore_mm", 0), main.get("rod_mm", 0)
    if not 0 < rod < bore:
        errors.append("CYM: invalid piston/rod geometry")
    else:
        cap_to_annulus = bore**2 / (bore**2 - rod**2)
        guarded_pressure = {"cap_to_annulus_ratio": cap_to_annulus,
                            "trapped_rod_at_300_bar_bar": cap_to_annulus * 300,
                            "trapped_rod_at_120_bar_bar": cap_to_annulus * 120}
        for name, config in phases.items():
            commands = common | config.get("commands", {})
            if commands.get("MP") != "open":
                continue
            links = graph(commands)
            normal_rod_outlet = path(links, "CYM.B", "T0.T", "MT") or path(links, "CYM.B", "CYM.A", "MR", "MRC")
            if not normal_rod_outlet:
                require(name == "closed_ports" and cap_to_annulus * 120 <= 315
                        and {"header_bar < 120", "main_b_bar <= 145"} <= guards_for(config)
                        and 0 < config.get("timeout_s", 0) <= .1,
                        f"{name}: rod pressure can intensify with cap feed and blocked rod port")
    return errors, guarded_pressure


def mutation_specs(params):
    """Mutation definitions retained from T-1.6, with equivalent scheme-A guards."""
    close_mm, _ = gate_coordinates(params)
    legacy = (
        ("remove_float_valve", "circuit", ("elements", "RFA"), None),
        ("reverse_makeup_check", "circuit", ("elements", "RCB", "states", "check"), ["B>A"]),
        ("reverse_regen_seat", "circuit", ("elements", "MRC", "states", "check"), ["B>A"]),
        ("connect_cap_to_MR_A", "circuit", ("elements", "MR", "ports", "A"), "MA"),
        ("close_unpowered_unloader", "circuit", ("elements", "ZU", "default_state"), "closed"),
        ("close_unpowered_cap_dump", "circuit", ("elements", "ME2", "default_state"), "closed"),
        ("trap_unpowered_low_pressure_acc", "circuit", ("elements", "SAL", "default_state"), "service"),
        ("trap_unpowered_pilot_acc", "circuit", ("elements", "SAX", "default_state"), "service"),
        ("remove_rod_fault_dump", "circuit", ("elements", "MEB"), None),
        ("remove_rod_relief", "circuit", ("elements", "RVB"), None),
        ("enable_MF_in_press", "interlocks", ("phases", "press", "lock_release_commands"), ["MF"]),
        ("remove_oil_relief", "circuit", ("elements", "RTF"), None),
        ("remove_press_nose_and_gate", "interlocks", ("phases", "press", "additional_conditions"), ["zsf_closed", "mf_locked", "mbt_locked", "dumps_ready"]),
        ("remove_gate_cap_safe", "interlocks", ("phases", "gate_open", "additional_conditions"), []),
        ("remove_return_cap_safe", "interlocks", ("phases", "return", "entry_conditions"), ["main_b_bar <= 3"]),
        ("remove_MBT_pressure_guard", "interlocks", ("phases", "eject", "entry_conditions"), sorted(CAP_SAFE)),
        ("press_MR_and_MT_overlap", "interlocks", ("phases", "press", "commands", "MR"), "open"),
        ("press_rod_ports_blocked", "interlocks", ("phases", "press", "commands", "MT"), "closed"),
        ("remove_handover_overlap_opening", "interlocks", ("switching_windows", HANDOVER, "commands", "MT"), "closed"),
        ("block_nose_before_it_moves", "interlocks", ("phases", "pre_up", "continuation_conditions"), CLEAR),
        ("unknown_guard_sensor", "interlocks", ("phases", "press", "conditions"), ["absent_sensor"]),
        ("underrated_cap_relief", "circuit", ("elements", "RVM", "p_rated_bar"), 250),
        ("energize_MP_in_overlap", "interlocks", ("switching_windows", HANDOVER, "commands", "MP"), "open"),
        ("wrong_ZSF_installation", "circuit", ("elements", "ZSF", "mounting_case"), 4),
        ("remove_eject_gate_permission", "interlocks", ("mechanical_permissions", "eject"), None),
        ("remove_gate_close_ram_permission", "interlocks", ("mechanical_permissions", "gate_close"), None),
        ("remove_feed_nose_permissions", "interlocks", ("mechanical_permissions", "feed"), None),
        ("remove_eject_gate_condition", "interlocks", ("phases", "eject", "conditions"), []),
        ("increase_gate_close_ram_limit", "interlocks", ("phases", "gate_close", "conditions"), [f"ram_mm <= {close_mm + 1:g}"]),
        ("remove_feed_nose2_condition", "interlocks", ("phases", "feed", "conditions"),
         ["gate_closed", "ram_mm <= 1", "shoe_mm <= 1", CLEAR[0], "doser_ready"]),
        ("common_ZUP_drain", "circuit", ("elements", "ZUP", "ports", "T"), "DR"),
        ("unpowered_MD_opens", "circuit", ("elements", "MD", "default_state"), "open"),
        ("hold_loses_rapid_float", "interlocks", ("phases", "hold", "commands", "RFB"), "closed"),
    )
    protections = tuple(
        (f"{'_'.join(path)}:{guard}", "interlocks", path, ("drop", guard), True)
        for path, guards in required_guards(params).items() for guard in guards
    )
    extra = (
        ("merge_nose_channels", "circuit", ("elements", "ZA2", "sensor"), NOSE[0], True),
        ("miswire_2nd_MF_B", "circuit", ("elements", "MF", "ports", "B2"), "MB", True),
        ("remove_nose_trip", "interlocks", ("faults", "nose_loss", "sensors"), [NOSE[0]], True),
        ("lose_unlock_source", "interlocks", ("phases", "pre_up", "unlock_pressure", "source"), "LP", True),
        ("lower_unlock_pressure", "interlocks", ("phases", "pre_up", "unlock_pressure", "minimum_net_equivalent_bar"), 34, True),
        ("return_regen_active", "interlocks", ("phases", "return", "commands", "RG"), "open", True),
        ("lose_air_branch_flow", "interlocks", ("operating_branches", "cool_air", "conditions"), ["cool_flow_ok"], True),
        ("switch_cooling_during_motion", "interlocks", ("cooling_changeover", "conditions"), [], True),
        ("unlock_sensor_missing_proof", "interlocks", ("phases", "pre_up", "movement_window", "require_by_deadline"), [CLEAR[0]], True),
        ("cool_bypass_feeds_flowmeter", "circuit", ("elements", "CB", "ports", "T"), "CF", True),
        ("increase_shoe_relief", "circuit", ("elements", "RVA", "setpoint", "max_inlet_at_design_flow_bar"), 145, True),
        ("disable_dfe_relief", "interlocks", ("operating_branches", "relief_dfe_Z"), None, True),
        ("allow_flexible_main_pressure_line", "circuit", ("lines", "HP", "construction"), "flexible hose", True),
    )
    return tuple((*case, False) for case in legacy) + protections + extra


def mutate(circuit, interlocks, spec):
    _, kind, keys, new, _ = spec
    model, logic = deepcopy(circuit), deepcopy(interlocks)
    node = model if kind == "circuit" else logic
    for key in keys[:-1]:
        node = node[key]
    if new is None:
        del node[keys[-1]]
    elif isinstance(new, tuple) and new[0] == "drop":
        node[keys[-1]] = [guard for guard in node[keys[-1]] if guard != new[1]]
    else:
        node[keys[-1]] = new
    return model, logic


def mutation_suite(circuit, interlocks, check, specs):
    """Evaluate disposable in-memory variants through the same acceptance checker."""
    output = []
    for spec in specs:
        model, logic = mutate(circuit, interlocks, spec)
        result = check(model, logic)
        reasons = (result["safety_errors"] + result["route_errors"] + result["errors"]
                   + result["rating_errors"] + result["unknown_sensor_references"])
        output.append({"name": spec[0], "status": "PASS" if result["passed"] else "FAIL",
                       "new": spec[-1], "diagnostics": reasons[:5]})
    return output



def gate_coordinates(params):
    mech = params["cycle_model"]["mechanics"]
    face_mm = params["chamber"]["approach_stroke_mm"] + mech["feed_length_mm"] + mech["roof_mm"]
    return face_mm - mech["gate_close_inset_mm"], face_mm


def required_guards(params):
    close_mm, face_mm = gate_coordinates(params)
    cap = sorted(CAP_SAFE)
    common = ["selected_cooling_ok", "dfe_z_bar >= 20", "dfe_z_bar <= 50"]
    guard_map = {
        ("guard_library", "press_chain"): PRESS,
        ("guard_library", "service"): ["selected_cooling_ok", "dfe_z_bar >= 20", "dfe_z_bar <= 50"],
        ("guard_library", "fill_chain"): ["prefill_bar >= 0.55", "prefill_bar < 1.2"],
        ("mechanical_permissions", "press", "conditions"): PRESS,
        ("mechanical_permissions", "pre_down", "conditions"): cap,
        ("mechanical_permissions", "pre_up", "conditions"): cap,
        ("phases", "prefill", "conditions"): [*NOSE, *RAPID, "rapid_hydraulics_proven"],
        ("phases", "eject", "conditions"): ["gate_open", "rapid_hydraulics_proven"],
        ("phases", "return", "conditions"): ["rapid_hydraulics_proven"],
        ("phases", "closed_ports", "conditions"): [*PRESS],
        ("phases", "press", "additional_conditions"): PRESS,
        ("phases", "regen", "additional_conditions"): PRESS,
        ("phases", "hold", "additional_conditions"): PRESS,
        ("phases", "unload", "conditions"): [*NOSE, "gate_closed"],
        ("phases", "gate_open", "conditions"): NOSE,
        ("phases", "pre_down", "conditions"): [*cap, "pre_a_bar <= 132"],
        ("phases", "pre_up", "conditions"): cap,
        ("phases", "pre_up", "entry_conditions"): [f"ram_mm >= {face_mm:g}", "gate_open", *cap],
        ("phases", "gate_close", "conditions"): [f"ram_mm <= {close_mm:g}"],
        ("phases", "pilot_reserve", "conditions"): ["gate_closed", "ram_mm <= 1", "shoe_mm <= 1", *CLEAR],
        ("switching_windows", HANDOVER, "additional_conditions"): PRESS,
        ("switching_windows", HANDOVER, "common_conditions"): common,
        ("operating_branches", "cool_water", "entry_conditions"): ["oil_C >= 45"],
        ("operating_branches", "cool_water", "continuation_conditions"): ["water_flow_ok"],
        ("operating_branches", "cool_water", "exit_conditions"): ["oil_C <= 42"],
        ("cooling_run_proof", "water", "oil_guards"): ["cool_flow_ok", "oil_C <= 55"],
        ("cooling_run_proof", "water", "on_demand_water_guards"): ["water_flow_ok"],
        ("cooling_run_proof", "air", "oil_guards"): [
            "cool_flow_ok", "cooler_1_flow_ok", "cooler_2_flow_ok", "oil_C <= 55"],
    }
    for name in ("pre_down", "prefill", "closed_ports", "regen", "press", "hold", "unload",
                 "gate_open", "eject", "return", "gate_close", "pre_up", "feed", "pilot_reserve"):
        guard_map[("phases", name, "common_conditions")] = common
    for name in ("prefill", "eject", "return"):
        guard_map[("phases", name, "additional_conditions")] = ["prefill_bar >= 0.55", "prefill_bar < 1.2"]
    return guard_map


def scheme_a_errors(circuit, logic, params):
    errors = []
    for path, guards in required_guards(params).items():
        node = logic
        for key in path:
            node = node.get(key, {})
        if missing := set(guards) - set(node):
            errors.append(f"{'/'.join(path)}: missing {sorted(missing)}")
    elements = circuit["elements"]
    phases = logic["phases"]
    if [elements.get(tag, {}).get("sensor") for tag in ("ZA1", "ZA2")] != NOSE:
        errors.append("Nose: both independent seated sensors are required")
    fault = logic["faults"].get("nose_loss", {})
    if (set(fault.get("sensors", [])) != set(NOSE)
            or not {"closed_ports", "regen", HANDOVER, "press", "hold"} <= set(fault.get("applies", []))):
        errors.append("Nose: either channel must trip independent safety outputs")
    for phase in ("prefill", "closed_ports", "regen", "press", "hold", "unload", "gate_open"):
        if phases[phase].get("on_loss") != "nose_loss_if_nose_signal_else_stop":
            errors.append(f"{phase}: nose loss must trip")
    for phase in ("pre_down", "pre_up"):
        if phases[phase].get("on_loss") != "stop":
            errors.append(f"{phase}: unsafe cap pressure must stop motion")
    mf = elements.get("MF", {})
    if not (mf.get("dual_radial_B_ports") and mf["ports"].get("B") == mf["ports"].get("B2") == "MA"):
        errors.append("MF: both Double-B passages serve MA")
    unlock = phases["pre_up"].get("unlock_pressure", {})
    if unlock.get("source") != "P1" or unlock.get("minimum_net_equivalent_bar", 0) < 35:
        errors.append("pre_up: main pump and verified minimum unlock force required")
    if phases["return"].get("commands", {}).get("RG", "closed") != "closed":
        errors.append("return: rapid regeneration must be isolated")
    if "m1_off_confirmed" not in logic.get("cooling_changeover", {}).get("conditions", []):
        errors.append("Cooling: stopped machine needed for changeover")
    if not {"cooler_1_flow_ok", "cooler_2_flow_ok", "cool_flow_ok"} <= set(
            logic["operating_branches"].get("cool_air", {}).get("conditions", [])):
        errors.append("Cooling: require both FT1/FT2 and FT in air mode")
    if elements["CB"]["ports"].get("T") != "CT":
        errors.append("Cooling: bypass must not prove cooler flow through FT")
    for tag in ("P0", "HP", "MH", "MA", "MB", "MRA", "PF", "D1", "D2", "D3"):
        if "EN 10305-4" not in circuit["lines"].get(tag, {}).get("construction", ""):
            errors.append(f"{tag}: rigid steel construction required")
    if elements["RVA"]["setpoint"].get("max_inlet_at_design_flow_bar", float("inf")) > 139:
        errors.append("Shoe: independent branch relief must limit full-cap force to 171 kN")
    dfe_relief = logic["operating_branches"].get("relief_dfe_Z", {})
    if (dfe_relief.get("actuation") != "mechanical"
            or dfe_relief.get("commands", {}).get("RVZ") != "relief"
            or elements.get("RVZ", {}).get("setpoint", {}).get("max_inlet_at_design_flow_bar", float("inf")) > 50):
        errors.append("DFE1Z port Z: independent 50 bar relief required")
    return errors


def revision_safety_checks(circuit, interlocks, params):
    """Check permissions and isolation on the paths affected by this revision."""
    errors = []
    elements = circuit["elements"]
    phases = interlocks["phases"]
    permissions = interlocks.get("mechanical_permissions", {})
    required = {
        "eject": {"gate_open"},
        "gate_close": {f"ram_mm <= {gate_coordinates(params)[0]:g}"},
        "feed": set(CLEAR),
    }
    for phase, conditions in required.items():
        declared = set(permissions.get(phase, {}).get("conditions", ()))
        active = set(phases[phase].get("conditions", ()))
        if not conditions <= declared & active or phases[phase].get("on_loss") != "stop":
            errors.append(f"{phase}: live mechanical permission and stop on loss required")
    for phase in ("press", "pre_down", "pre_up"):
        if permissions.get(phase, {}).get("enforcement") != "live_stop_on_loss":
            errors.append(f"{phase}: mechanical permission must be live")

    drain = elements["ZUP"]["ports"]["T"]
    endpoints = {(name, port) for name, element in elements.items()
                 for port, line in element["ports"].items() if line == drain}
    if (endpoints != {("ZUP", "T"), ("T0", "DZ")}
            or circuit["lines"].get(drain, {}).get("p_design_bar", float("inf")) > 2):
        errors.append("ZUP: exclusive drain to T0 at no more than 2 bar required")
    for name in ("MP", "MR", "MT", "MD"):
        if elements[name].get("default_state") != "closed":
            errors.append(f"{name}: closed when de-energized required")
    for phase in ("hold", "unload"):
        commands = phases[phase]["commands"]
        if any(commands.get(name) != value for name, value in
               {"VR": "center", "XGRF": "open", "RFA": "float", "RFB": "float"}.items()):
            errors.append(f"{phase}: keep both rapid cylinders floating")
    return errors
