"""Qualification screens and the mass contribution of each station measure."""

from math import fsum, pi, sqrt


def calculate(t16, t16_inputs, t21, selected, sources, tank, cooling, heat, circuit, station):
    previous = t16["mass"]["round1_uncredited_options"]
    catalog = t16_inputs["revision"]["mass"]
    options = []

    def add(name, group, savings_kg, rows, checked, pending, source_ids, *, subtotal=True, evidence=None):
        options.append(dict(measure=name, group=group, delta_kg=None if savings_kg is None else -savings_kg,
                            counted_in_group_subtotal=subtotal, ledger_ids=rows, checked=checked,
                            pending=pending, source_ids=source_ids, evidence=evidence))

    motor = sources["brook"]
    trials = heat["motor_trials"]
    baseline_motor_kg = station["baseline_motor_kg"]
    add("Brook Crompton JP-DA200LA, заказное IM B5", "B", baseline_motor_kg - motor["family_reference_mass_kg"],
        ["T25-M1"], "IE3, Al, 30 кВт S1, 400 В 50 Гц. По B5 совпадают центрирование Ø300, PCD 350 и вал Ø55×110.",
        "Цикл превышает предел. Оценка Δм по 207 кг семейства, нужен паспорт 4P IM B5, масса и комплектовочный чертёж с колоколом и полумуфтой.",
        ["brook", "brook_mount", "omec", "bell", "a4vso"], evidence=dict(
            replay=trials["brook"], family_mass_kg=motor["family_reference_mass_kg"],
            exact_mounted_motor_kg=motor["mounted_B5_B35_mass_kg"],
            motor_B5_flange_OD_mm=motor["B5_flange_OD_mm"], motor_B5_PCD_mm=motor["B5_flange_PCD_mm"],
            motor_B5_register_mm=motor["B5_flange_register_mm"], motor_B5_clearance_mm=motor["B5_flange_bolt_clearance_mm"],
            OMEC_B5_clearance_mm=19, motor_shaft_D_L_mm=motor["shaft_D_L_mm"],
            pump_counter_side="RE 92050, NG180, ISO 3019-2, посадка Ø160, 4 отверстия по Ø200. Подтвердить выбранный код вала P Ø50×80 или Z, вылеты и допустимую соосность муфты.",
            installation_type="B5 для сохранения текущих опор. B35 возможен после проверки лап и плоскости опирания."))

    add("ABB M3AA 200MLA 4, альтернативный мотор", "B",
        baseline_motor_kg - sources["abb"]["family_reference_mass_kg"], ["T25-M1"],
        "400 В, 50 Гц, 1484 об/мин по типовому протоколу, 30 кВт S1 IE3.",
        "RMS выше предела. 246 кг по таблице семейства. Подтвердить массу B5/B35 и чертёж. Альтернатива Brook вне суммы B.",
        ["abb", "abb_family", "bell"], subtotal=False, evidence=trials["abb"])

    tf = catalog["TF_pair"]
    tf_old = previous["TF_oil_relief_pair"]
    tf_required_L_min = max(tf_old["required_L_min"], selected["valves"]["MF"]["flow_L_min"])
    fluid_kg_m3 = tank["density_kg_m3"]
    q_m3_s = tf_required_L_min / 60000
    header_velocity_m_s = q_m3_s / (pi / 4 * (tf["header_shell_ID_mm"] / 1000)**2)
    dyn_bar = fluid_kg_m3 * header_velocity_m_s**2 / 2e5
    tf_at_design_q_L_min = tf_old["two_valves_flow_bound_L_min"] * sqrt(
        (circuit["elements"]["RTF"]["setpoint"]["max_inlet_at_design_flow_bar"] - tf["backpressure_bar"]) /
        (tf_old["inlet_pressure_bar"] - tf["backpressure_bar"]))
    add("Два Goetze 642 DN65 FKM вместо RTF", "B", -tf_old["delta_kg"],
        ["T16-15", "T16-18"],
        "2 × 8,9 кг для резьбовой версии. Каталог 51,8 м³/ч воды на клапан при уставке 2 бар и +10 %. Пересчёт на HLP46 и общий слив выполнен.",
        "Подтвердить HLP46 во всём диапазоне температур, режим 0,2 бар на выходе, открытие пары на импульсе и сброс в отдельный TET. Пересчитать массу при фланцевом исполнении.",
        ["t16", "goetze", "goetze_install", "t26"], evidence=dict(
            original_requirement_L_min=tf_old["required_L_min"], conservative_T26_cap_feed_L_min=tf_required_L_min,
            two_valves_at_2p09_bar_L_min=tf_old["two_valves_flow_bound_L_min"],
            extrapolated_two_valves_at_3_bar_L_min=tf_at_design_q_L_min,
            one_valve_catalog_water_m3_h=tf["reference_water_flow_m3_h"], temperature_viscosity_screen_factor=tf["liquid_viscosity_factor"],
            total_backpressure_budget_bar=tf["backpressure_bar"], common_header_ID_mm=tf["header_shell_ID_mm"],
            common_header_velocity_m_s=header_velocity_m_s, common_header_dynamic_head_bar=dyn_bar,
            max_total_K_at_zero_static_head=tf["backpressure_bar"] / dyn_bar,
            catalogue_outlet_condition="Свободный сброс по руководству. Допуск 0,2 бар должен подтвердить поставщик."))

    db = previous["DB_to_cartridges"]
    db_flow_L_min = catalog["cartridges"]["cartridge_RPIC_max_L_min"]
    db_rows = []
    for tag, flow_L_min in db["design_flows_L_min"].items():
        valve = circuit["elements"][tag]
        crack = valve["setpoint"].get("initial_crack_target_bar", 300)
        budget_bar = valve["setpoint"]["max_inlet_at_design_flow_bar"] - crack
        db_rows.append(dict(id=tag, required_L_min=flow_L_min, passes_catalog_max_flow=flow_L_min <= db_flow_L_min,
                            return_net=valve["ports"]["T"], existing_external_pilot_return_net=valve["ports"]["Y"],
                            assumed_crack_bar=crack, allowed_flow_override_plus_backpressure_bar=budget_bar))
    add("Шесть DB30 → Sun RPIC", "B", -db["delta_kg"], ["T16-08"],
        "125–270 л/мин против 380 л/мин по каталогу, рабочий предел 350 бар. Противодавление порта 2 прибавляется 1:1.",
        "Нужны Δp(Q) и противодавление каждой ветви на горячем/холодном масле, сверка наружного пилотного слива DB, динамические пики ≤315 бар. Ведомость плит общих блоков должна исключить эти шесть корпусов.",
        ["t16", "sun", "circuit"], evidence=dict(catalog_max_L_min=db_flow_L_min, catalog_max_bar=350,
                                                tank_backpressure_per_bar=1, ports=db_rows,
                                                local_housing_kg_each=db["local_housing_kg_each"]))

    acc = sources["parker_accumulator"]
    lp = selected["accumulators"]["lp"]
    lp_tag = "T25-ALP"
    lp_dry_kg = station["accumulators"]["LP_design_kg"]
    usable_L = lp["useful_volume_L"] * acc["effective_gas_volume_L"] / lp["effective_gas_volume_L"]
    add("LP Parker EHV 20-330/90-A25HC-200", "B", lp_dry_kg - acc["mass_kg"], [lp_tag],
        "330 бар, номинальные 20 л, G2, 49 кг. При фиксированных уставках расчётный полезный объём уменьшается.",
        "Подтвердить SAF32E, подвес и штуцер. Перезапуск цикла с 17,8 л газа, проверка давления и расхода на сбросе. Для AX в этой линейке экономии нет.",
        ["parker_accumulator", "ax_lp", "t26"], evidence=dict(
            reference_gas_L=lp["effective_gas_volume_L"], candidate_gas_L=acc["effective_gas_volume_L"],
            reference_usable_L=lp["useful_volume_L"], candidate_usable_L=usable_L,
            nominal_peak_deficit_L=lp["peak_deficit_L"],
            adverse_peak_deficit_L=heat["cases"]["adverse"]["accumulators"]["lp"]["peak_deficit_L"]))

    full_bath_kg = next(row["mass_kg"] for row in station["T16_rows"] if row["id"] == "T16-02")
    add("T0, стенки 3 мм и четыре ребра", "B", full_bath_kg - tank["structure"]["proposed_shell_kg"],
        ["T16-02"], "S235JR, дно и крышка 4 мм, внутренние перегородки сохранены. Скрининг стенки и нагрузок рамы.",
        "Нужны размерный эскиз, герметичность, проверка переменной нагрузки швов, креплений к раме и ванны при перевозке.",
        ["tank_structure", "lifting", "transport", "t16_inputs"], evidence=tank["structure"])
    add("T0 как основание, две поперечины", "B", -previous["tank_as_base"]["delta_kg"], ["T16-06"],
        "Оценка RHS и четырёх накладок T-1.6.",
        "При совместном применении с тонкими стенками проверить единый расчёт опор, вибрации, прогиб, подъём и предельную соосность муфты.",
        ["t16", "bell"], evidence=previous["tank_as_base"])
    add("Общие блоки", "B", None, ["T16-08", "T26-MF_housing", "T26-regen_housings"],
        "Раздельные клапаны и их наружные порты видны по ведомости.",
        "Размерный эскиз и масса; посадки, каналы, потери, масло и 315 бар. Отдельные корпуса шести RPIC исключить из расчёта общей плиты.",
        ["t16", "t26_inventory", "circuit"], subtotal=False)
    add("Объём T0 и воздушные охладители", "B", 0, ["T16-03", "T25-E1_E2", "T25-E_hardware"],
        "Расчётный уровень, всас, нагрев и каталог охладителей проверены. В исполнении 190 л и пара ASA0567AA47.",
        "Всас и деаэрацию квалифицировать на фактической геометрии. Подходящий более лёгкий охладитель среди проверенных вариантов не подтверждён.",
        ["iso4413", "asa_0567", "parker_lac", "hydac_cooling", "emmegi", "akg"],
        evidence=dict(tank_screen_L=tank["sizing_screen_minimum_initial_L"], cooler_reduction_kg=cooling["reduction_kg"]))

    # Machine boundary for the optional supplied-water example. Include full wet
    # line mass, and keep unselected components as an explicit mass penalty.
    pwo = sources["pwo"]
    run_m = 2
    tube_OD_mm, tube_wall_mm = 33.7, 2.6
    tube_ID_mm = tube_OD_mm - 2 * tube_wall_mm
    tube_fluid_area_mm2 = pi / 4 * tube_ID_mm**2
    tube_metal_area_mm2 = pi / 4 * tube_OD_mm**2 - tube_fluid_area_mm2
    tube_dry_kg = tube_metal_area_mm2 * 1e-6 * run_m * t16_inputs["project"]["steel_density_kg_m3"]
    tube_water_L = tube_fluid_area_mm2 * 1e-3 * run_m
    tube_wet_kg = tube_dry_kg + tube_water_L
    water_flow_L_min = heat["cooling_required_kW"] * 60 / (4.18 * 10)
    cooler_raw_kg = cooling["baseline"]["mass_modules_kg"]
    add("Parker PWO B25TH×50 и вода от площадки", "C", cooler_raw_kg - pwo["bare_mass_kg"] - tube_wet_kg,
        ["T25-E1_E2"], "79 кВт в каталожной точке ΔT 40 K при 150 л/мин масла. Вычтена масса аппарата и 2 м мокрых водяных линий.",
        "Недостающая масса включает воду в аппарате, фитинги, крепёж и арматуру. При автономном контуре добавить насос, сухую градирню, бак и всё заполнение. Нужны вода и график при 55 °C и 180 л/мин.",
        ["pwo", "pwo_selection", "water_tube", "water_properties", "decisions"], evidence=dict(
            boundary="Площадка подаёт и принимает воду; внешнее хозяйство вне контура массы машины.",
            bare_heat_exchanger_kg=pwo["bare_mass_kg"], retained_mount_and_instrument_allowance_kg=cooling["baseline"]["hardware_kg"],
            water_pipe_length_m=run_m, pipe_OD_mm=tube_OD_mm, pipe_wall_mm=tube_wall_mm,
            water_pipe_dry_kg=tube_dry_kg, water_inside_pipes_L=tube_water_L, water_pipes_wet_kg=tube_wet_kg,
            minimum_water_flow_at_10_K_L_min=water_flow_L_min, remaining_water_circuit_mass_kg=None,
            subtotal_direction="верхняя оценка экономии, вычесть положительную недостающую массу",
        ))

    candidates = t21["candidates"]
    pv180 = candidates["PV180_FDV"]["summary"]["mass"]
    a4 = candidates[t21["selected"]]["summary"]["mass"]
    add("Возврат к Parker PV180 FDV", "C",
        a4["power_unit_motor_and_pump_kg"] - pv180["power_unit_motor_and_pump_kg"], ["T25-P1"],
        "Сравнены мотор и насос по T-2.1. Отдельный резерв DFE1Z в сумме оставлен.",
        "Требуется решение по регулятору и отдельный цикл с реальной настройкой; масса окончательной обвязки открыта.",
        ["t21_mass", "decisions"])
    add("Интегрированная задняя крышка", "C", -previous["integrated_rear_cover"]["delta_kg"], ["машина, силовая часть"],
        "Оценка T-1.6 для прежней геометрии.",
        "Решение оператора по D-OP-19 и новая проверка силовой части, герметичности, усталости и обслуживаемости.",
        ["t16", "decisions"])

    options.sort(key=lambda row: (row["delta_kg"] is None, row["delta_kg"] or 0))
    for group in ("A", "B", "C"):
        ids = [tag for row in options if row["group"] == group and row["counted_in_group_subtotal"]
               and row["delta_kg"] for tag in row["ledger_ids"]]
        assert len(ids) == len(set(ids))
    totals_kg = dict.fromkeys(("A", "B", "C"), 0.0)
    for group in totals_kg:
        totals_kg[group] = -fsum(row["delta_kg"] for row in options if row["group"] == group
                                 and row["counted_in_group_subtotal"] and row["delta_kg"] is not None) or 0.0
    return options, totals_kg

