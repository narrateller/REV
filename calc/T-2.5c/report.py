"""Render the concise Russian qualification report from the calculation results."""


VARIANTS = {
    "with_collar_and_gross_old_front_removal": "С буртом и полным вычетом старого переднего узла",
    "without_end_collar": "Без торцевого бурта",
    "with_end_collar": "С торцевым буртом",
}


def number(value, digits=2):
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def interval(values, digits=2):
    return "–".join(number(value, digits) for value in values)


def render(results):
    m = results["metrics"]
    q = results["qualification"]
    source = results["sources"]
    tf = q["tf"]
    pc = q["cooling_KD"]
    tank = q["tank"]["walls"]

    def link(source_id, label):
        return f"[{label}]({source[source_id]['url']})"

    lines = [
        "# T-2.5c. Квалификация облегчения гидростанции",
        "",
        f"**{m['status']}.** Станция {number(m['station_t25c_kg'])} кг, зачтено {number(m['credited_measures_kg'])} кг. "
        f"Верхняя масса схемы A {number(m['machine_A_kg_range'][-1])} кг, до 5000 кг не хватает "
        f"{number(m['missing_to_5000_kg'])} кг. D-OP-21 оставляет предел 5000 кг. Дальнейший пересчёт силовой части зависит от испытания сырья по D-OP-19.",
        "",
        "## Ведомость и масса машины",
        "",
        f"Сумма исходных строк {number(m['station_t25b_kg'])} кг. В ведомости изменена строка T25-M1. "
        "Массу машины рассчитали вычитанием зачтённой экономии из каждого варианта T-2.2i в T-2.5b. "
        "Сборки колокола и муфты учтены в T16-06, Parker LP учтён в базе T-2.5b. "
        "[Ведомость T-2.5c](design/hydraulics/station.t25c.yaml), " + link("baseline_metrics", "массы базы"),
        "",
        "| Вариант схемы A | База, кг | Итог, кг | До 5000, кг | До 5080, кг | Все потенциалы T-2.5b, кг | Все меры с ABB, кг |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in VARIANTS.items():
        row = m["machine_A_variants"][key]
        values = [row[col] for col in ("t25b_kg", "t25c_kg", "missing_to_5000_kg", "missing_to_5080_kg",
                                      "all_measures_t25b_potentials_kg", "all_measures_with_qualified_motor_kg")]
        lines.append("| " + " | ".join([label, *(number(value) for value in values)]) + " |")
    lines += [
        "",
        f"Сумма исходных потенциалов {number(m['all_measures_t25b_potential_saving_kg'])} кг включает 71 кг для мотора из T-2.5b. "
        f"С паспортной экономией ABB и теми же остальными потенциалами получается {number(m['all_measures_with_qualified_motor_potential_saving_kg'])} кг. "
        "Оба столбца со всеми мерами условные.",
        "",
        "| Мера | Решение | Зачтённая Δм, кг | Потенциальная Δм T-2.5b, кг | Основание |",
        "|---|---|---:|---:|---|",
    ]
    evidence = {
        "motor": link("abb_bdk", "Лист ABB") + ", [G-CYCLE](gates.t25c.json)",
        "tf": link("goetze_642", "Goetze 642") + ", " + link("goetze_455", "Goetze 455") + ", " + link("leser_engineering", "расчёт жидкости"),
        "db": link("sun_rpic", "Sun RPIC") + ", " + link("parker_r4v_service", "Parker R4V") + ", " + link("db30", "RE 25802"),
        "tank_walls": link("leissa", "NASA SP-160") + ", " + link("earlier_tank", "расчёт T-2.5"),
        "tank_base": "[Входы расчёта](calc/T-2.5c/sources.yaml), " + link("couplings", "допуски муфт SGE"),
    }
    for row in results["measures"]:
        lines.append("| " + " | ".join([row["measure"], row["status"], number(row["credited_delta_kg"]),
                                         number(row["potential_delta_kg"]), evidence[row["id"]]]) + " |")
    lines += [
        "",
        "## Мотор и цикл",
        "",
        "| Мотор, артикул и монтаж | Масса, кг | n ном., об/мин | M ном., Н·м | M опр., Н·м | η, % | I при 400 В, А |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in [q["motor"]["baseline"], *q["motor"]["candidates"]]:
        mass = number(item["exact_mass_kg"], 0)
        if "family_mass_kg" in item:
            mass = f"{number(item['family_mass_kg'], 0)} (семейство)"
        label = item["model"]
        if "order_number" in item:
            label += f" {item['order_number']}, {item['mount']}"
        lines.append("| " + " | ".join([
            label, mass, number(item["rated_rpm"], 0), number(item["rated_Nm"]), number(item["breakdown_Nm"], 1),
            number(item["efficiency_pct"], 1), number(item["current_400V_A"]),
        ]) + " |")
    lines += [
        "",
        "ABB 30 кВт S1, IE3, 400 В 50 Гц, 4 полюса, Al. FF350 Ø400/350/300 и вал Ø55×110 с шпонкой 16 мм подходят к колоколу и полумуфте IEC 200. "
        "Паспортные 1481 об/мин допускают эталон с 1480 об/мин по карточке. В КД проверить зазор к клеммной коробке и настройку тепловой защиты по 55,1 А. "
        + link("abb_bdk", "Лист ABB") + ", [Каталожные таблицы](calc/T-2.5c/sources.yaml), " + link("bell_dims", "колокол"),
        "",
        f"G-PFACE {number(results['gates']['G-PFACE']['value'])} МПа, G-DOSE {results['gates']['G-DOSE']['value']} мм, "
        f"G-CYCLE {number(m['cycle_gate_s'], 3)} с и {number(m['rms_kW'], 3)} кВт RMS. Все три PASS на params.t26a.yaml, "
        "метод цикла `reference_model`. WEG 1475 об/мин дал 5,90625 с и 30,075 кВт RMS в прогоне ГК T-2.5b. "
        "Для Brook отсутствует масса артикула B5. У Omega 1500 об/мин — синхронная частота, а геометрия установки лап B35 требует проверки. "
        "[Прогон](gates.t25c.json), " + link("weg", "WEG") + ", " + link("weg_gate", "прогон ГК") + ", "
        + link("brook", "Brook") + ", " + link("brook_b5", "артикул B5") + ", " + link("omega", "Omega"),
        "",
        "## TF, DB и бак",
        "",
        f"**TF.** При 1,9 бар +10 % и 0,2 бар на сливе, HLP46 580 мм²/с при 0 °C, пара 642 DN65 даёт "
        f"{number(tf['goetze_642_pair_screen_L_min'], 0)} л/мин, тройка {number(tf['goetze_642_triple_screen_L_min'], 0)} л/мин, "
        f"штатный 455 DN65/100 {number(m['tf_capacity_screen_L_min'], 0)} л/мин. Требуется {number(tf['required_L_min'])} л/мин. "
        f"Три 851 DN50 дают {number(tf['goetze_851_triple_screen_L_min'], 0)} л/мин. Это оценки по перепаду и вязкости. "
        "Три фланцевых 642 весят 36 кг без коллектора и опор. У 455 исходная заявка 1293 л/мин. "
        "Допуск противодавления до 30 % уставки относится к 455 с металлическим сильфоном. Для квалификации нужны точное исполнение и характеристика TET. "
        "У LESER открыты исполнение и обвязка при 1,9 бар. Подпор 0,60 ± 0,05 бар, расчётное давление TF 3 бар. "
        + link("leser_engineering", "LESER, формулы жидкости и Kv") + ", [Паспорт Shell HLP46](calc/T-2.5c/sources.yaml), "
        + link("goetze_642", "Goetze 642") + ", " + link("goetze_851", "Goetze 851") + ", "
        + link("goetze_455_install", "монтаж 455") + ", " + link("leser_441", "LESER 441"),
        "",
        "**DB.** У Sun RPIC 350 бар, 380 л/мин и T-16A. Противодавление на выпуске прибавляется к уставке 1:1. "
        "Бюджет роста давления на расходе при проектном противодавлении 5–12 бар. Кривая Parker R4V06 с Y1 относится к корпусному исполнению. "
        "Rexroth DBC30-2-5X/350Y имеет внешнюю линию Y и чертёж полости. Для обоих открыты P(Q) установленного картриджа и масса блока. "
        "Испытание пиков ≤315 бар остаётся задачей образца по D-OP-11. "
        + link("sun_rpic", "Sun RPIC") + ", " + link("parker_r4v_tuv", "кривые Parker") + ", " + link("db30", "RE 25802"),
        "",
        f"**T0.** Для стенок 3 мм получено {number(tank['nominal_hydrostatics']['bending_MPa'], 1)} МПа в статике и "
        f"{number(tank['flooded_transport']['bending_MPa'], 1)} МПа с прогибом {number(tank['flooded_transport']['deflection_mm'], 2)} мм "
        "в расчётном сценарии залитого бака при перевозке 0,8g вперёд и 0,5g поперёк. Сухие частоты рассчитаны для шарнирных пластин. "
        "Проверка отстройки от 24,7 и 49,3 Гц требует залитой сборки. Открыты швы, проушины, опоры, компоновка рёбер, прогиб плиты "
        "под приводом и допуск соосности точной муфты. Ведомость содержит бак 190 л, 900×700×400 мм, стенки 4 мм и самостоятельную раму. "
        + link("leissa", "Leissa, NASA SP-160") + ", [Входы перевозки](calc/T-2.5c/sources.yaml), " + link("couplings", "MP Filtri SGE"),
        "",
        "## Открытые пункты КД по охлаждению",
        "",
        f"Bowman GL180-1428-3. При 180 л/мин, 42–45 °C и Δp {interval(pc['pc_branch_dp_bar'])} бар вал PC требует "
        f"{interval(pc['pc_required_shaft_kW'], 3)} кВт при принятом КПД {number(pc['pc_estimated_efficiency'])}. "
        f"CB 1,5 бар даёт {number(pc['pc_shaft_kW_at_candidate_CB_bar'], 3)} кВт при том же расходе ещё до запаса на открытие. "
        f"Для 0,55 кВт расчётная граница {number(pc['pc_max_dp_bar_for_motor_at_nominal_flow'])} бар, проектная 1,25 бар. "
        "Нужны карта PC и измерение Δp и расхода по ветвям при холодном пуске и регулировании. Установленная мощность "
        f"{number(m['installed_kW'], 3)} кВт, с воздушной опцией {number(m['installed_with_air_option_kW'], 3)} кВт при пределе 34,2 кВт. "
        + link("baseline_review", "разбор T-2.5b") + ", " + link("baseline_inputs", "расчётные входы PC"),
        "",
        "**Запрос Bowman для КД.** Просим подтвердить наружную площадь теплообмена 2,1 м², тепловую мощность и Δp воды при 150 л/мин и до 30 °C, "
        "тепловую мощность и Δp масла при 180 л/мин HLP46 и 42, 45 и 55 °C, рекомендуемую минимальную температуру пуска и диапазон скорости воды. "
        "Для пучка CuNi 90/10 просим предельные pH, хлориды, NH₃ и сульфиды с единицами и условиями отбора пробы. "
        + link("bowman_profile", "Профиль GL") + ", " + link("bowman_manual", "руководство Bowman"),
        "",
        "## Проект строки D-GK",
        "",
        f"> T-2.5c STOP_MASS. ABB 3GAA202410-BDK IM B5 −{number(m['credited_measures_kg'], 0)} кг. "
        f"Станция {number(m['station_t25c_kg'])} кг, машина A {interval(m['machine_A_kg_range'])} кг. "
        f"До 5000 кг по верхней границе {number(m['missing_to_5000_kg'])} кг. "
        f"G-CYCLE {number(m['cycle_gate_s'], 3)} с и RMS {number(m['rms_kW'], 3)} кВт, reference_model. "
        "TF, DB и меры по баку остаются открытыми. Подтверждение TF на 1588,64 л/мин и ветви PC остаётся в КД. "
        "Вопрос массы возвращается к результату испытания сырья по D-OP-19 и D-OP-21.",
        "",
    ]
    return "\n".join(lines)
