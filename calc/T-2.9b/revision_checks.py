"""Check the new switch permissions and the topology without the LG branch."""
from revision import REMOVED_ELEMENTS, REMOVED_LINES, STEEL_TRACT


CASES = (
    ("TT_full_before_30", "interlocks", ("rapid_approach_temperature_modes", "full_speed_conditions"),
     ["oil_tt_valid", "oil_rapid_min_C >= 29"], True),
    ("TT_no_hysteresis", "interlocks", ("rapid_approach_temperature_modes", "enter_full_speed"),
     ["oil_tt_valid", "oil_rapid_min_C >= 30"], True),
    ("TT_invalid_allows_rapid", "interlocks", ("rapid_approach_temperature_modes", "invalid_signal"),
     "keep_previous_mode", True),
    ("TT_no_live_cancel", "interlocks", ("rapid_approach_temperature_modes", "falling_below_30"),
     "keep_previous_mode", True),
    ("TT_warmup_flow_too_high", "interlocks", ("rapid_approach_temperature_modes", "warmup_max_ZSF_L_min"),
     1100, True),
    ("TT_prefill_unlinked", "interlocks", ("phases", "prefill", "temperature_mode"), None, True),
    ("TT_eject_loses_validity", "interlocks", ("phases", "eject", "additional_conditions"),
     ("drop", "oil_tt_valid"), True),
    ("P1_pre_up_low_setting", "circuit", ("elements", "P1", "pre_up_pressure_min_bar"), 44, True),
    ("P1_pre_up_low_live_bound", "interlocks", ("phases", "pre_up", "unlock_pressure", "header_min_bar"), 44, True),
    ("P1_pre_up_drop_live_proof", "interlocks", ("phases", "pre_up", "unlock_pressure", "live_conditions"), [], True),
    ("P1_pre_up_drop_entry_proof", "interlocks", ("phases", "pre_up", "entry_conditions"),
     ("drop", "header_bar >= 45"), True),
    ("VG_open_misconnected_to_LP", "circuit", ("elements", "VG", "ports", "P"), "LP", True),
    ("VG_close_LP_added", "interlocks", ("phases", "gate_close", "optional_lp"),
     {"commands": {}, "routes": []}, True),
    ("TF_wrong_length", "circuit", ("lines", "PF", "max_length_m"), 0.7, True),
    ("TF_flexible", "circuit", ("design_limits", "tf_to_zsf_A", "flexible_hose_allowed"), True, True),
    ("main_pockets_flexible", "circuit", ("design_limits", "main_compressible_tract", "material"), "hose", True),
    ("cap_pressure_bound_weakened", "interlocks", ("gate_cap_pressure", "true_pressure_max_bar"), 5, True),
)


def errors(circuit, logic, params):
    defects = []
    design = circuit["design_limits"]
    elements = circuit["elements"]
    phases = logic["phases"]
    flexible = {line for item in circuit["flexible_sections"] for line in item["lines"]}
    if (set(REMOVED_ELEMENTS) & elements.keys() or set(REMOVED_LINES) & (circuit["lines"].keys() | flexible)
            or elements["VG"]["ports"]["P"] != "HP"):
        defects.append("VG must be supplied from HP with LG and its lines removed")
    expected_routes = {"gate_open": "B", "gate_close": "A"}
    for phase, port in expected_routes.items():
        config = phases[phase]
        if ("optional_lp" in config or [f"ALP.A", f"CYG.{port}"] not in config.get("forbidden_routes", [])
                or ["P1.P", f"CYG.{port}", ["VG"]] not in config["routes"]):
            defects.append(f"{phase}: require P1 through VG and exclude the LP route")
    if set(expected_routes) & set(params["cycle_model"]["lp"]["routes"]):
        defects.append("Frozen cycle input may not route LP to VG")

    tt = logic.get("rapid_approach_temperature_modes", {})
    if (tt != design.get("rapid_approach_temperature_modes")
            or tt.get("sensor_valid") != "oil_tt_valid"
            or tt.get("full_speed_conditions") != ["oil_tt_valid", "oil_rapid_min_C >= 30"]
            or tt.get("enter_full_speed") != ["oil_tt_valid", "oil_rapid_min_C >= 31"]
            or tt.get("initial_mode") != "warmup"
            or tt.get("falling_below_30") != "revoke_full_speed_and_limit_flow"
            or tt.get("invalid_signal") != "inhibit_rapid_approach"
            or not 0 < tt.get("warmup_max_ZSF_L_min", 0) <= 1005
            or tt.get("applies_to") != ["prefill", "eject"]):
        defects.append("TT requires valid live input, 31/30 °C hysteresis and 1005 L/min warmup cap")
    for phase in ("prefill", "eject"):
        if (phases[phase].get("temperature_mode") != "rapid_approach_temperature_modes"
                or "oil_tt_valid" not in phases[phase]["additional_conditions"]):
            defects.append(f"{phase}: TT mode and live validity required")
    if (elements.get("TT_VALID", {}).get("sensor") != "oil_tt_valid"
            or elements.get("TT_MIN", {}).get("sensor") != "oil_rapid_min_C"):
        defects.append("TT validity diagnostic missing")

    unlock = phases["pre_up"]["unlock_pressure"]
    if (min(unlock.get("header_min_bar", 0), elements["P1"].get("pre_up_pressure_min_bar", 0),
            design.get("pre_up_P1_min_bar", 0)) < 45
            or "header_bar >= 45" not in phases["pre_up"]["entry_conditions"]
            or "header_bar >= 45" not in unlock.get("live_conditions", [])
            or unlock.get("controls_until") != "both_nose_clear_proven"):
        defects.append("pre_up: verified P1 pressure of at least 45 bar until nose is clear")

    limits = design.get("tf_to_zsf_A", {})
    pipe = circuit["lines"]["PF"]
    if (limits.get("material") != "steel" or limits.get("flexible_hose_allowed") is not False
            or not 0 < max(limits.get("max_length_m", 1), pipe.get("max_length_m", 1)) <= .5
            or "EN 10305-4" not in pipe.get("construction", "")):
        defects.append("TF to ZSF.A: steel pipe of at most 0.5 m required")
    main = design.get("main_compressible_tract", {})
    if (main.get("material") != "steel" or main.get("flexible_hose_allowed") is not False
            or set(main.get("lines", [])) != set(STEEL_TRACT)
            or set(main.get("pockets", [])) != {"MC", "MF", "ZSF"}):
        defects.append("Main pressure lines and MF/MC/ZSF cavities must be rigid steel")

    cap = logic.get("gate_cap_pressure", {})
    model_bar = params["cycle_model"]["process"]["gate_release_cap_bar"]
    if (cap.get("true_pressure_max_bar") != 3 or cap.get("model_margin_bar") != 2
            or cap.get("gate_load_model_bound_bar") != model_bar or model_bar != 5
            or set(cap.get("independent_upper_bound_guards", [])) != {"cap1_bar <= 3", "cap2_bar <= 3"}):
        defects.append("Gate: require two live upper-bound readings ≤3 bar and keep 5 bar load estimate")
    return defects

