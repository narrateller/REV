"""Evaluate the documented group B proposals without changing the reference inputs."""
from copy import deepcopy
from math import sqrt


def calculate(previous, reference, inputs, params, circuit, cycle_gate, criteria, baseline_cycle):
    saved = {row["measure"]: row for row in previous["measures"] if row["group"] == "B"}
    brook = saved["Brook Crompton JP-DA200LA, заказное IM B5"]
    tf = saved["Два Goetze 642 DN65 FKM вместо RTF"]
    lp = saved["LP Parker EHV 20-330/90-A25HC-200"]
    db = saved["Шесть DB30 → Sun RPIC"]
    tank = saved["T0, стенки 3 мм и четыре ребра"]
    base = saved["T0 как основание, две поперечины"]
    weg = inputs["weg_candidate"]
    motor_params = deepcopy(params)
    motor_params["cycle_model"]["pump"].update(motor_rpm=weg["rated_rpm"], rated_motor_rpm=weg["rated_rpm"])
    motor_trial = cycle_gate(motor_params, criteria)
    motor_details = motor_trial["details"]
    assert motor_details["checks"]["cycle_model_inputs_qualified"]
    assert motor_trial["status"] == "FAIL" and not motor_details["checks"]["rms_power_limit"]
    lp_catalogue = inputs["lp_candidate"]
    new_params = deepcopy(params)
    new_params["cycle_model"]["lp"]["shell_L"] = lp_catalogue["effective_gas_L"]
    lp_trial = cycle_gate(new_params, criteria)
    replay = lp_trial["details"]
    lp_result = lp["evidence"]
    lp_cycle = new_params["cycle_model"]["lp"]
    usable_L = lp_catalogue["effective_gas_L"] * (
        ((lp_cycle["precharge_bar"] + 1) / (lp_cycle["low_bar"] + 1))**(1 / lp_cycle["exponent"])
        - ((lp_cycle["precharge_bar"] + 1) / (lp_cycle["high_bar"] + 1))**(1 / lp_cycle["exponent"])
    )
    assert abs(usable_L - lp_result["candidate_usable_L"]) < 1e-9
    reserve_kg = inputs["components"]["lp_mount_and_connection_reserve_kg"]
    gross_saving_kg = 63 - inputs["components"]["lp_catalog_kg"]
    max_deficit_L = max(lp_result["nominal_peak_deficit_L"], lp_result["adverse_peak_deficit_L"])
    lp_confirmed = (
        lp_catalogue["nominal_L"] == 20
        and lp_catalogue["working_rating_bar"] >= 330
        and lp_catalogue["max_catalogue_flow_L_min"] >= circuit["elements"]["ALP"]["Q_L_min"]
        and usable_L >= max_deficit_L
        and lp_trial["status"] == "PASS"
        and replay["cycle_s"] <= baseline_cycle["value"] + 1e-9
        and replay["rms_power_kW"] <= 30
    )

    selected = reference["variants"][reference["selected"]]
    max_feed_L_min = max(
        selected["prefill"]["cap_exhaust"]["flow_L_min"],
        reference["selected_sensitivity"]["combined"]["prefill"]["cap_exhaust"]["flow_L_min"],
    )
    tf_evidence = tf["evidence"]
    set_bar = circuit["elements"]["RTF"]["setpoint"]["crack_bar"]
    back_bar = tf_evidence["total_backpressure_budget_bar"]
    rating_inlet_bar = 2 * 1.10
    screen_inlet_bar = set_bar * 1.10
    pair_water_L_min = 2 * tf_evidence["one_valve_catalog_water_m3_h"] * 1000 / 60
    ideal_oil_L_min = pair_water_L_min * sqrt(
        (screen_inlet_bar - back_bar) / rating_inlet_bar
        * inputs["water_density_kg_m3"] / inputs["oil_density_kg_m3"]
    )
    viscosity_factor = tf_evidence["temperature_viscosity_screen_factor"]
    pair_oil_L_min = ideal_oil_L_min * viscosity_factor

    def entry(item, name, status, reason, source_ids, evidence, credited_saving_kg=0):
        return {
            "measure": name, "status": status, "reason": reason,
            "t25_potential_delta_kg": item["delta_kg"],
            "credited_saving_kg": credited_saving_kg, "ledger_ids": item["ledger_ids"],
            "source_ids": source_ids, "evidence": evidence,
        }

    return [
        entry(brook, "Мотор IM B5 из алюминиевого сплава", "не зачтено",
              "WEG 12840024, B5T, 208 кг, 1475 об/мин при 400 В. Цикл 5,90625 с, RMS 30,075 кВт превышает 30,0. "
              "Для Brook и Siemens точная масса IM B5 не подтверждена. Сохранён OMEC 1480 об/мин.",
              ["weg_passport", "weg_family", "bell_dimensions", "brook", "brook_mount", "siemens", "omec"],
              weg | {"potential_delta_kg": weg["dry_kg"] - 278,
                     "pullout_Nm": weg["full_load_Nm"] * weg["pullout_ratio"],
                     "nominal_interface_match": True, "assembly_fit_verified": False,
                     "gate_method": motor_details["method"], "gate_status": motor_trial["status"],
                     "cycle_s": motor_trial["value"], "rms_kW": motor_details["rms_power_kW"],
                     "failed_gate_checks": [key for key, passed in motor_details["checks"].items() if not passed],
                     "new_motor_parameters_used": False}),
        entry(tf, "TF, два Goetze 642 DN65 FKM", "не зачтено",
              "Расчётный расход пары при +10 % и противодавлении 0,2 бар меньше притока. "
              "Нужна характеристика HLP46 и общего слива на допустимом превышении. "
              "Оставлен исходный RTF. Его подтверждение на обновлённый приток остаётся открытым.",
              ["goetze", "t26", "circuit", "t25"],
              {"water_catalogue_pair_L_min": pair_water_L_min, "dry_pair_valves_kg": 2 * 8.9,
               "set_bar": set_bar, "screen_inlet_bar": screen_inlet_bar, "backpressure_bar": back_bar,
               "oil_viscosity_screen_factor_from_t25": viscosity_factor,
               "max_gross_TF_inlet_L_min": max_feed_L_min, "calculated_HLP46_pair_L_min": pair_oil_L_min,
               "required_capacity_factor_vs_ideal_oil": max_feed_L_min / ideal_oil_L_min,
               "retained_RTF_circuit_booked_flow_L_min": circuit["elements"]["RTF"]["Q_L_min"]}),
        entry(lp, "LP, " + lp_catalogue["model"], "зачтено" if lp_confirmed else "условно",
              "Точный артикул и масса подтверждены. Полезный объём превышает дефицит эталонных сценариев. "
              "Уставки и схема LP/SAF32E сохраняются. В зачёте учтено 3 кг на крепление и стыковку G2.",
              ["lp_parker", "lp_parker_fasttrack", "lp_hydac_63", "lp_hydac_49", "t25", "model"],
              lp_catalogue | {"old_kg": 63, "catalogue_dry_kg": inputs["components"]["lp_catalog_kg"],
                              "mount_and_connection_reserve_kg": reserve_kg, "vessel_saving_kg": gross_saving_kg,
                              "available_usable_L": usable_L, "max_deficit_L": max_deficit_L,
                              "sensitivity_cycle_s": replay["cycle_s"], "sensitivity_rms_kW": replay["rms_power_kW"],
                              "sensitivity_lp_assist_L": replay["lp_assist_L"],
                              "reference_parameters_changed": False},
              credited_saving_kg=gross_saving_kg - reserve_kg if lp_confirmed else 0),
        entry(db, "Шесть DB30 → Sun RPIC", "условно",
              "350 бар и 380 л/мин покрывают статические номиналы. Два порта RPIC не воспроизводят внешний Y→DR. "
              "Нужны точное исполнение с дренажем, подтверждение P(Q) при противодавлении и масса корпусов. "
              "Динамические пики ≤315 бар проверяются на первом образце.",
              ["circuit", "sun", "sun_drain", "decisions"],
              db["evidence"] | {"static_pressure_margin_bar": 350 - 315}),
        entry(tank, "T0, стенки 3 мм с рёбрами", "не зачтено",
              "Скрининг T-2.5 охватывает гидростатику, подъём и транспорт. Для облегчения требуются расчёт швов, "
              "креплений, совместной работы стенок и проверка соосности. Сохранена оболочка 4 мм.",
              ["tank_method", "t25", "baseline"], previous["tank"]["structure"]),
        entry(base, "T0 как основание станции", "не зачтено",
              "Требуется общий расчёт нагрузок на раму и привод, подъёма, транспорта и соосности. "
              "Сохранена самостоятельная рама.",
              ["tank_method", "t25", "baseline"], {}),
    ]
