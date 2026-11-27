"""Compare the exact motor orders against the drive and reference cycle."""


def cycle_result(gate):
    return {
        "status": gate["status"],
        "method": gate["details"]["method"],
        "cycle_s": gate["value"],
        "rms_kW": gate["details"]["rms_power_kW"],
    }


def qualify(spec, reference_gate, weg_gate, reference_rpm, max_rms_kW):
    base = spec["omec"].copy()
    base["breakdown_Nm"] = base["rated_Nm"] * base["breakdown_ratio"]
    reference = cycle_result(reference_gate)
    legacy_weg = cycle_result(weg_gate)
    candidates = []
    for item in spec["candidates"]:
        motor = item.copy()
        motor["breakdown_Nm"] = motor["rated_Nm"] * motor["breakdown_ratio"]
        motor["mass_difference_kg"] = (
            motor["exact_mass_kg"] - base["exact_mass_kg"] if motor["exact_mass_kg"] is not None else None
        )
        reasons = []
        if motor["rated_rpm"] is None:
            reasons.append("В паспорте указаны синхронные 1500 об/мин. Номинальные обороты при нагрузке не опубликованы, посадка лап IM B35 не квалифицирована.")
        elif motor["rated_rpm"] >= reference_rpm:
            motor["gate"] = reference
            motor["gate_source_id"] = "reference_gate"
            if reference["status"] != "PASS" or reference["method"] != "reference_model" or (
                reference["cycle_s"] > 5.910 or reference["rms_kW"] > max_rms_kW
            ):
                reasons.append("Эталонный цикл не проходит ограничения T-2.5c.")
        elif motor["order_number"] == "12840024":
            motor["gate"] = legacy_weg
            motor["gate_source_id"] = "weg_gate"
            reasons.append("Прежний G-CYCLE при 1475 об/мин дал 30,075 кВт RMS. Повтор прогона исключён карточкой.")
        else:
            reasons.append("Обороты ниже 1480. Для индивидуального прогона требуется точная масса исполнения.")
        if motor["exact_mass_kg"] is None:
            reasons.append("207 кг указаны в таблице семейства. Масса точного исполнения IM B5 отсутствует.")
        if motor["breakdown_Nm"] < base["breakdown_Nm"]:
            reasons.append("Момент опрокидывания ниже уровня OMEC.")
        if motor.get("rating") != {"power_kW": 30, "voltage_V": 400, "frequency_Hz": 50,
                                   "poles": 4, "IE": 3, "housing": "Al"} or motor.get("duty") != "S1":
            # Only the full qualification record carries a complete mounting and rating check.
            assert reasons, motor["order_number"]
        if not reasons:
            interface = spec["interface"]
            assert motor["mount"] == "IM B5 / IM3001"
            for key in ("flange_OD_PCD_register_mm", "shaft_D_L_mm", "shaft_key_mm", "flange_holes"):
                assert motor[key] == interface[key], motor["order_number"]
            assert motor["flange_hole_diameter_mm"] > interface["bolt_mm"]
            motor["mass_difference_kg"] += motor["bell_and_coupling_delta_kg"]
        motor["credited"] = not reasons and motor["mass_difference_kg"] < 0
        motor["reason"] = " ".join(reasons) or (
            "Паспорт IM B5, посадка FF350 и вал 55×110 совпадают с интерфейсом. "
            "Колокол и полумуфты сохраняются. G-CYCLE на модели 1480 об/мин проходит."
        )
        candidates.append(motor)
    selected = min((item for item in candidates if item["credited"]),
                   key=lambda item: item["mass_difference_kg"], default=None)
    return {"baseline": base, "interface": spec["interface"], "candidates": candidates,
            "selected": selected, "reference_pump_rpm": reference_rpm}
