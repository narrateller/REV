"""Generate the D-GK-23 hydraulic revision from the preserved T-2.9 files."""
import re

from build_scheme import DESIGN, HERE, read, write


PARAMS = HERE / "params/params.t29b.yaml"
REMOVED_ELEMENTS = ("LG", "XGLG", "GHC", "LGC", "RVGH")
REMOVED_LINES = ("LG0", "XLG", "GH")
STEEL_TRACT = ("P0", "HP", "MH", "MA", "MB", "MRA", "D1", "D2", "D3")
TEMPERATURE_MODES = {
    "sensor_valid": "oil_tt_valid",
    "full_speed_conditions": ["oil_tt_valid", "oil_rapid_min_C >= 30"],
    "enter_full_speed": ["oil_tt_valid", "oil_rapid_min_C >= 31"],
    "falling_below_30": "revoke_full_speed_and_limit_flow",
    "invalid_signal": "inhibit_rapid_approach",
    "initial_mode": "warmup",
    "warmup_max_ZSF_L_min": 1005,
    "applies_to": ["prefill", "eject"],
}
GATE_CAP_POLICY = {
    "true_pressure_max_bar": 3,
    "independent_upper_bound_guards": ["cap1_bar <= 3", "cap2_bar <= 3"],
    "gate_load_model_bound_bar": 5.0,
    "model_margin_bar": 2.0,
}


def params_text(K_Pa):
    base = (HERE / "params/params.t29.yaml").read_text(encoding="utf-8")
    replacements = {
        "routes: [pre_up, pre_down, gate_open, gate_close, eject]":
            "routes: [pre_up, pre_down, eject]  # D-GK-23: шибер от P1 через VG, без ГА НД",
        "bulk_modulus_Pa: 1400000000":
            f"bulk_modulus_Pa: {K_Pa:d}  # Эффективный масло + сталь; oil_modulus.py, sources.yaml",
        "gate_release_cap_bar: 5.0  # T-1.6 interlocks, 3 bar instrument threshold plus up to 2 bar error":
            "gate_release_cap_bar: 5.0  # Консервативная нагрузка модели: 3 бар действительного давления + 2 бар запаса",
    }
    for old, new in replacements.items():
        if base.count(old) != 1:
            raise ValueError(f"Expected exactly one T-2.9 field: {old}")
        base = base.replace(old, new)
    return base


def change_K(base, K_Pa):
    text, count = re.subn(r"(bulk_modulus_Pa: )\d+", lambda match: f"{match[1]}{K_Pa}", base)
    if count != 1:
        raise ValueError("Expected exactly one bulk-modulus field")
    return text


def rapid_mode(previous_mode, oil_rapid_min_C, tt_valid):
    """Reference evaluation of the speed-permission latch on each control scan."""
    if not tt_valid:
        return "inhibited"
    if oil_rapid_min_C >= 31 or previous_mode == "full_speed" and oil_rapid_min_C >= 30:
        return "full_speed"
    return "warmup"


def scheme(pc=None):
    circuit = read(DESIGN / "T-2.9_circuit.yaml")
    logic = read(DESIGN / "T-2.9_interlocks.yaml")
    circuit["revision"] = "T-2.9b"
    circuit["status"] = "HOLD_PC_AND_MASS"
    for tag in REMOVED_ELEMENTS:
        del circuit["elements"][tag]
    for tag in REMOVED_LINES:
        del circuit["lines"][tag]
    for tags in circuit["functions"].values():
        tags[:] = [tag for tag in tags if tag not in REMOVED_ELEMENTS]
    circuit["flexible_sections"] = read(HERE / "sources.yaml")["flexible_sections"]
    elements = circuit["elements"]
    elements["VG"]["ports"]["P"] = "HP"
    elements["VG"]["note"] = "Открытие и закрытие от P1 по HP, без подпитки ГА НД (D-GK-23)."
    elements["P1"]["pre_up_pressure_min_bar"] = 45
    elements["P1"]["pre_up_note"] = "Держать P1 ≥ 45 бар до подтверждения освобождения носа на первых 12 мм."
    elements["TT"]["signal_policy"] = (
        "oil_C — рабочее показание TT для охлаждения. oil_rapid_min_C — нижняя оценка "
        "с учётом погрешности. oil_tt_valid — достоверность сигнала TT."
    )
    elements["TT_VALID"] = {
        **elements["TT"],
        "type": "controller",
        "label": "Диагностика достоверности TT",
        "sensor": "oil_tt_valid",
        "ports": {},
        "states": {},
        "source": "project",
        "manufacturer": "Проект REV",
        "series": "Диагностика аналогового входа TT",
        "p_design_bar": None,
        "p_rated_bar": None,
        "Q_L_min": 0,
    }
    elements["TT_MIN"] = {
        **elements["TT_VALID"],
        "label": "Нижняя оценка температуры по TT",
        "sensor": "oil_rapid_min_C",
        "series": "Оценка температуры с учётом погрешности TT",
    }
    circuit["design_limits"].update(
        tf_to_zsf_A={"max_length_m": 0.5, "material": "steel", "flexible_hose_allowed": False},
        main_compressible_tract={"lines": list(STEEL_TRACT), "pockets": ["MF", "MC", "ZSF"],
                                 "material": "steel", "flexible_hose_allowed": False},
        rapid_approach_temperature_modes=TEMPERATURE_MODES,
        pre_up_P1_min_bar=45,
    )
    circuit["lines"]["PF"]["max_length_m"] = 0.5
    circuit["open_items"]["KD"] = (
        "Масса обвязки, проходной привод тандема, давления RVA/RVZ, монтаж мишеней и подтверждение PL."
    )
    logic["reference"] = "calc/T-2.9b/params/params.t29b.yaml"
    logic["guard_policy"] = (
        "Оба канала cap*_bar показывают независимые верхние оценки действительного давления "
        "с учётом погрешности. Разрешение при обеих оценках ≤ 3 бар. В cycle_model 5 бар задаёт "
        "нагрузку на шибер с запасом 2 бар относительно 3 бар. Отказ фиксируется, сброс вручную."
    )
    logic["gate_cap_pressure"] = GATE_CAP_POLICY
    logic["rapid_approach_temperature_modes"] = TEMPERATURE_MODES
    for phase in TEMPERATURE_MODES["applies_to"]:
        logic["phases"][phase]["temperature_mode"] = "rapid_approach_temperature_modes"
        logic["phases"][phase]["additional_conditions"] = [
            *logic["phases"][phase]["additional_conditions"], "oil_tt_valid",
        ]
    logic["transitions"]["tail"] += " До команды PPB подтвердить P1 ≥ 45 бар."
    logic["commissioning_conditions"]["TT"] = (
        "Подтвердить диагностику TT, границы 31/30 °C и ограничение потока ZSF в прогреве. "
        "До готовности PC тепловой режим подлежит проверке отдельно."
    )
    for phase, port in (("gate_open", "B"), ("gate_close", "A")):
        config = logic["phases"][phase]
        del config["optional_lp"]
        config["forbidden_routes"] = [["ALP.A", f"CYG.{port}"]]
    del logic["operating_branches"]["relief_gate_inlet"]
    for fault in logic["faults"].values():
        for tag in ("LG", "XGLG"):
            fault["commands"].pop(tag, None)
    unlock = logic["phases"]["pre_up"]
    unlock["entry_conditions"].append("header_bar >= 45")
    unlock["unlock_pressure"].update(
        header_min_bar=45,
        controls_until="both_nose_clear_proven",
        live_conditions=["header_bar >= 45"],
        reference="calc/T-2.9b/unlock.py",
    )
    for tag in ("gate_open", "gate_close"):
        logic["phases"][tag]["notes"] = "P1→F1→HP→VG. Подтвердить декомпрессию HP после остановки с фактическим исполнением F1."
    if pc is None:
        from pc_select import calculate
        pc = calculate()
    candidate = pc["preferred_candidate"]
    circuit["open_items"]["PC"] = (
        "Кандидат 1,5 кВт. Подтвердить расход при 55 °C, баланс FT1/FT2, "
        "полный перепад насоса и пусковой момент с выбранным CB. Статус — проверка перед выпуском."
    )
    elements["PC"].update(
        label="Циркуляция · кандидат D-OP-22",
        series=candidate["model"],
        size="Размер 180, 950 об/мин",
        p_rated_bar=25,
        note="Кандидат с " + candidate["motor"] + ". Работа по выбранной ветви охлаждения.",
        Q_L_min=candidate["flow_tabulated_L_min"],
        selection_status=pc["status"],
        motor_kW=candidate["motor_kW"],
    )
    elements["CB"]["setpoint"].update(
        candidate_crack_target_bar=candidate["cb_crack_target_bar"],
        required_crack_range_bar=candidate["cb_crack_required_range_bar"],
        pc_shaft_proof_max_dp_bar=2.0,
        status="HOLD_UNTIL_CATALOGUE_AND_SKID_PROOF",
    )
    elements["CB"]["note"] = (
        "Ограничение Δp PC 2 бар включает всас, CB и CD при полном перепуске. "
        "Расчётное давление прочности линии 8 бар."
    )
    logic["pc_warmup_strategy"] = {
        "status": pc["status"],
        "entry_conditions": ["oil_tt_valid", f"oil_rapid_min_C >= {candidate['start']['pc_off_below_start_C']}"],
        "trip_conditions": [f"oil_rapid_min_C < {candidate['start']['trip_below_C']}", "invalid TT", "overspeed", "overload"],
        "preheat": "Прогрев от M1/P1 на разгрузке с открытым ZU. Силовые перемещения заблокированы.",
        "oil_flow_proof": "После пуска подтвердить общий поток. Для воздушного тракта одновременно FT1 и FT2.",
        "cb_design_requirement": "На разгоне и полном перепуске поддерживать фактический перепад PC ≤2 бар.",
        "proof_required": "Для допуска проверить CB и всю ветвь на стенде.",
    }
    return circuit, logic


def write_scheme(pc=None):
    circuit, logic = scheme(pc)
    write(DESIGN / "T-2.9b_circuit.yaml", circuit)
    write(DESIGN / "T-2.9b_interlocks.yaml", logic)
    return circuit, logic

