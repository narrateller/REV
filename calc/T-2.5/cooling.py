"""Screen oil-to-air coolers on the common T-2.6 cooling point."""

from math import isclose

from heat import interpolate


def calculate(heat, sources, cooling_row_kg, hardware_kg):
    flow_L_min = heat["flow_L_min"]
    delta_K = heat["oil_limit_C"] - heat["air_C"]
    fouling = heat["fouling_fraction"]
    installed_without_fans_kW = heat["installed_kW"] - heat["fan_kW"]
    base_port = "2 × ASA Connector NG40"
    trials = []

    def add(model, source, mass_kg, fans_kW, coefficient_kW_K, dimensions_mm, ports,
            tolerance=0.15, *, flows_L_min=None, coefficient_basis="Считывание кривой в указанной точке.",
            additional_source=None, auxiliary_note=None):
        raw_kW = delta_K * coefficient_kW_K
        dirty_kW = raw_kW * (1 - tolerance) * (1 - fouling)
        installed_kW = installed_without_fans_kW + fans_kW
        trial = dict(model=model, source=sources[source]["url"], curve_source=sources.get(additional_source, {}).get("url"),
                     heat_point=dict(oil_flow_L_min=flows_L_min or [flow_L_min], oil_inlet_C=heat["oil_limit_C"],
                                     air_inlet_C=heat["air_C"], raw_kW=raw_kW, tolerance_fraction=tolerance,
                                     fouling_fraction=fouling, dirty_kW=dirty_kW,
                                     coefficient_kW_K=coefficient_kW_K, coefficient_basis=coefficient_basis),
                     mass_modules_kg=mass_kg, mass_with_equal_hardware_kg=mass_kg + hardware_kg,
                     bare_mass_below_reference=mass_kg < cooling_row_kg,
                     fan_kW=fans_kW, installed_kW=installed_kW, per_module_W_H_D_mm=dimensions_mm, ports=ports,
                     fails=[], auxiliary_note=auxiliary_note)
        if dirty_kW < heat["cooling_required_kW"]:
            trial["fails"].append("тепло")
        if installed_kW > heat["installed_limit_kW"]:
            trial["fails"].append("мощность")
        if mass_kg + hardware_kg >= cooling_row_kg:
            trial["fails"].append("масса")
        trials.append(trial)

    asa = sources["asa_0927"]
    add("ASA0927AA6A", "asa_0927", max(asa["mass_kg_range"]), asa["fan_kW"],
        interpolate(flow_L_min, asa["performance_points_L_min_kW_K"]), [1170, 1100, 664], base_port,
        additional_source="asa_ports", auxiliary_note="140,5 кг на странице ASA и 156,4 кг в таблице. Принята большая масса.")
    add("ASA0727AA6A", "asa_ports", 134.6, 1.5, 2.1, [1012, 960, 640], base_port,
        coefficient_basis="Округлённая вверх оценка кривой ASA 0727 1,5 кВт при 180 л/мин.")
    # Pareto candidates among the low-fan-power LACs, including parallel arrangements.
    add("Parker LAC 078-8", "parker_lac", 136, 1.1, 1.8, [1022, 1052, 713], "G2", 0.10,
        coefficient_basis="График 180 л/мин, округлено вверх примерно до 1,8 кВт/К.")
    add("Parker LAC 056-6", "parker_lac", 75, 1.5, 2.0, [868, 898, 668], "G1¼", 0.10,
        coefficient_basis="Верхняя оценка при 180 л/мин по кривой LAC 56-6 семейства 50 Гц.",
        additional_source="parker_lac_curves", auxiliary_note="Коллектор потребуется переразвести для одной ветви.")
    add("2 × Parker LAC 058-8", "parker_lac", 160, 1.5, 2 * 1.1, [868, 898, 652], "G2", 0.10,
        flows_L_min=[90, 90], coefficient_basis="Верхнее считывание 1,1 кВт/К на аппарат при 90 л/мин.")
    add("Parker LAC 112-8", "parker_lac", 168, 2.2, 2.65, [1185, 1215, 805], "G2", 0.10,
        coefficient_basis="Приблизительное считывание при 180 л/мин. Отсев по мощности.")
    add("HYDAC AC-LN10L, 50 Гц, 1,1 кВт", "hydac_cooling", 129, 1.1, 82.9 / 40,
        [930, 1030, 766], "G1½", 0.05, additional_source="hydac_cooling_current",
        coefficient_basis="Верхняя оценка для 180 л/мин по максимуму во всём диапазоне 50–360 л/мин версии B.")
    add("2 × HYDAC AC-LN8L", "hydac_cooling", 144, 1.5, 2 * 40.2 / 40,
        [705, 725, 596], "G1¼", 0.05, flows_L_min=[90, 90], additional_source="hydac_cooling_current",
        coefficient_basis="Верхняя оценка по максимуму каждого аппарата на 200 л/мин.")
    add("KTR OAC1000-03-8", "ktr_cooling", 154, 1.5, 1.60, [995, 1270, None], "G3",
        coefficient_basis="Считывание T-1.5 по графику 750 об/мин на 180 л/мин как верхняя оценка исполнения 700 об/мин.")
    add("Emmegi HPA 52 245203", "emmegi_standard", 95, 1.1,
        interpolate(flow_L_min, [[140, 1.35], [210, 1.50]]), [725, 940, 623], "G1½", 0.05)
    add("2 × Emmegi HPA 42 Compact 2K4203", "emmegi_compact", 118, 1.58, 2 * 1.05,
        [606, 920, 415], "G1¼", flows_L_min=[90, 90],
        coefficient_basis="Округлённая вверх оценка кривой при 90 л/мин на аппарат.")
    add("2 × Emmegi HPA 50 Compact 2K5003", "emmegi_compact", 164, 1.16,
        2 * interpolate(90, [[80, 1.03], [280, 1.48]]), [725, 940, 443], "G1½",
        flows_L_min=[90, 90], coefficient_basis="Скрининг по хорде между опубликованными точками 80 и 280 л/мин. Для зачёта при равных ветвях нужно 1,22 кВт/К на аппарат при 90 л/мин.",
        auxiliary_note="Паспортная нижняя граница 80 л/мин. Действующий разброс 78–102 выходит за неё. Необходимы подбор и подтверждение новой балансировки.")
    add("2 × Emmegi HPA 50 2P Compact 2K8703", "emmegi_compact", 164, 1.16,
        2 * interpolate(90, [[80, 1.05], [100, 1.17]]), [725, 940, 443], "G1¼", flows_L_min=[90, 90],
        auxiliary_note="При 90 л/мин Δp каждой матрицы около 1,15 бар уже при 30 мм²/с.")
    add("Emmegi HPA 42/2 Compact 2K4303", "emmegi_compact", 123, 1.58, 2.1,
        [1165, 920, 415], "G1½", coefficient_basis="Верхнее округление кривой на 180 л/мин.")
    add("Emmegi HPA 50/2 Compact 2K8803", "emmegi_compact", 176, 1.16, 2.3,
        [1430, 940, 440], "G1½", coefficient_basis="Считывание в районе 180 л/мин. Отсев по сухой массе.")
    add("Emmegi HPA 135 Larger", "emmegi", 126, 3.0, 1.8,
        [1025, 900, 780], "SAE 3″ / M54×2", 0.05)
    add("Emmegi HPA 180 Larger", "emmegi", 200, 7.5, 2.85,
        [1025, 1173, 790], "SAE 3″ / M54×2", 0.05)
    add("AKG T8 5208.203.0000", "akg", 89, 1.1, 1.75,
        [722, 960, 590], "G1¼", coefficient_basis="Верхнее считывание кривой T8 при 180 л/мин.")
    add("AKG T8S 5208.231.0000", "akg", 89, 2.2, 2.1,
        [722, 960, 590], "G1¼", coefficient_basis="Верхнее считывание кривой T8S при 180 л/мин.")
    add("AKG T9L 5209.223.0000", "akg", 190, 1.5, 2.1,
        [995, 1352, 650], "G1½", coefficient_basis="Верхнее считывание кривой T9L при 180 л/мин. Отсев по массе.")

    assert isclose(2 * 82.7 + hardware_kg, cooling_row_kg)
    viable = [row for row in trials if not row["fails"]]
    return dict(
        baseline=dict(model="2 × ASA0567AA47", per_module_W_H_D_mm=[920, 860, 543],
                      port=base_port, mass_modules_kg=2 * 82.7, hardware_kg=hardware_kg,
                      fitted_mass_kg=cooling_row_kg, maximum_branch_drop_bar=0.58,
                      total_flow_L_min=flow_L_min, fan_kW=heat["fan_kW"], source=sources["asa_ports"]["url"]),
        station_hardware_assumption="Для сравнения массы оставлен существующий резерв крепежа, веточной КИП и матов 8 кг.",
        branch_changes_require_confirmation="При одном аппарате проверить новый коллектор, отсутствие воздушной рециркуляции и 180 л/мин при Δp всей ветви ≤ 1,25 бар. Для двух — баланс потоков и запас по месту.",
        allowed_fan_increase_kW=heat["fan_limit_kW"] - heat["fan_kW"],
        minimum_coefficient_kW_K_with_15pct_tolerance=heat["cooling_required_kW"] / (delta_K * (1 - fouling) * 0.85),
        alternatives=trials, thermal_mass_power_candidates=[row["model"] for row in viable],
        recommended="2 × ASA0567AA47 с параллельными ветвями",
        reduction_kg=0.0,
    )
