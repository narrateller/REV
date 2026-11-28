"""Write the two-round T-2.9 handoff in UTF-8."""
from build_scheme import ROOT, HERE, read


def render_report(result):
    pc0 = result["pc_branch"]
    pc = result["pc_operator_comparison"]
    t = result["transient"]
    cav = result["cavitation"]
    mitigation = cav["mitigations"]
    cold = mitigation["cold_flow_derate_gate"]
    hot = next(row for row in cav["full_speed_results"]
               if row["length_m"] == .5 and row["temperature_C"] == 55 and row["tf_gauge_bar"] == .55)
    u = result["unlock"]
    m = result["mass"]
    gate = result["gate_nominal"]
    alternatives = result["mass_alternative_disable_LP_on_slide_gate"]
    mutations = result["circuit"]["mutations"]
    src = read(HERE / "sources.yaml")
    sources = src["catalogs"] | src["sources"]

    def cite(label, key):
        return f'[{label}]({sources[key]["url"]})'

    def fmt(number, decimals=3):
        return f"{number:.{decimals}f}".replace(".", ",") if number is not None else "открыто"

    def pair(numbers, decimals=3):
        return " / ".join(fmt(value, decimals) for value in numbers)

    roof = result["geometry_interlocks"]
    peaks = t["zsf_port_A_peak_bar"]
    v5 = t["zsf_stop_by_length"]
    base_mass = m["station_base_kg"]
    steady = pc0["operating_points"]
    ptable = " · ".join(
        f'{q["temperature_C"]} °C {pair([q["clean_dp_bar"], q["dirty_scenario_dp_bar"]])}'
        for q in steady)
    hydro_min, hydro_max = pc["hydraulic_kW_all_cases_range"]
    p_best_min, p_best_max = pc["shaft_optimistic_comparison_using_best_tabulated_efficiency_kW"]
    lines = [
        "# T-2.9 · Гидросхема A · круги 1 и 2",
        "",
        f'**{result["status"]} / STOP_MASS.** PC остаётся у оператора. '
        f'G-PFACE, G-DOSE и G-CYCLE — PASS на Parker EHV. Цикл {fmt(gate["cycle_s"])} с, '
        f'RMS {fmt(gate["rms_kW"])} кВт, reference_model. Функциональная схема прошла проверку с 0 дефектов и '
        f'{mutations["rejected"]}/{mutations["total"]} отвергнутыми мутациями '
        f'(33 унаследованных и {mutations["new_interlocks"]} новых). Допуск быстрого хода зависит от испытаний ниже.',
        "",
        "## Схема и блокировки",
        "",
        f'Крыша 90 мм. Перенос дозы 35,25 кН в быстром подводе при x=5…95 мм. '
        f'Нос контролируют два независимых AZ16 с разными мишенями. Прессование при закрытых шибере и ZSF, '
        f'подтверждённых MF/MBT и обоих каналах носа. Выталкивание при открытом шибере. '
        f'Закрытие шибера при x≤{roof["gate_close_x_mm"]:.0f} мм, начало отпирания при x≥{roof["gate_face_x_mm"]:.0f} мм. '
        'Подпрессовка и отпирание при двух каналах действительного pA ГЦ ≤3 бар. Порог реализуется с учётом погрешности. '
        'Открытие MF/MBT требует безопасных A/B на входе и живого PTF <1,2 бар. '
        f'Физическое время подтверждения проверяется в КД. {cite("AZ16", "nose_switch")}',
        "",
        "### Изменения к T-1.6",
        "",
        "Масса в таблице дана к T-2.5c. Поэлементная сверка полей и паспортов находится в [circuit_changes.csv](calc/T-2.9/circuit_changes.csv).",
        "",
        "| Элементы | Было | Стало | Δм, кг | Причина и источник |",
        "|---|---|---|---:|---|",
        f'| M1 | OMEC | ABB M3AA 200MLA 4, 400 В | 0 | D-GK-21, {cite("паспорт", "ABB_T25C")} |',
        f'| P1, EC1, PX/PXA | PV180 FDV, 36 кВт | A4VSO180 DFE1Z, 33,25 кВт, тандем U04 к сверке | открыто | Эталон, {cite("RE 92088", "DFE1Z")} |',
        f'| XZD, PTZ, RVZ | без линии Z | AX → 35 бар → Z, контроль и сброс ≤50 бар | +0,36 и открыто | {cite("Sun PRFB", "SUN_PRFB")} |',
        "| CYM, XM1 | ход 289 мм | Ø280/200 ×396 мм, координаты A | 0 | T-2.6, геометрия |",
        f'| ZSF, TF, NG1, RTF, PF, MA, MB, TET | 1293 л/мин, 65/42 л | 1552/1589 л/мин, 80/55 л, ID125, 0,60±0,05 бар, RTF 1,9 | 0 и открыто по газу | {cite("RE 20478", "zsf")}, {cite("455", "rtf_455")} |',
        f'| MF, MBT, MC, VR | MF 2700, 1293 л/мин, VR 270 | MF 2K7L Double-B 3900, MBT 1K8L, MC LC80/LFA80, VR 4WRLE25 329 | 0 | {cite("RE 29406", "wrce_step")}, {cite("RE 29123", "wrle_step")} |',
        f'| RG, RT, RGC, ZRG/ZRT | без регенерации быстрых | LC25/LFA25 + 4WE6, обратный CXHA и контроль кромок | +0,42 и открыто | T26-regen уже в базе, {cite("CXHA", "SUN_CXHA")} |',
        f'| ALP | HYDAC в T-1.6 | Parker EHV, 17,8 л, заряд LCH, защита SAL | 0 | 49 + 3 кг в T-2.5c, {cite("Parker, с. 5", "parker_lp")} |',
        "| LR, LRC, PRIO | LP на RB при возврате | LP на RA при выталкивании, возврат от P1/VR | 0 | Маршруты эталона T-2.6 |",
        f'| LG, XGLG, GHC, LGC, RVGH, VG | VG от HP | подпитка LP на шибер, развязка GH и термозащита | +16,44 и открыто | {cite("NG32", "wrce_step")}, {cite("CXHA", "SUN_CXHA")} |',
        f'| PCY, XB, ZA1/2, ZB1/2, PPA, RVA | кулачок и засовы | нос, два канала посадки и отхода, pA башмака ≤132 бар, RVA ≤139 бар при расходе | открыто по крепежу | D-GK-16, T-2.2i, {cite("AZ16", "nose_switch")} |',
        f'| PC, CB, TT, FT, ZCOOL | KF125, CB 3 бар, базовые E1/E2 | PC/CB открыты, TT на CP и контроль выбранной ветви | 0 | {cite("KRACHT", "kracht_kf")} |',
        f'| GL, WBR, WF, WV, WFT | без водяной ветви | GL180-1428-3, EV220B25, DN40 PN16, контроль воды | 0 | D-GK-20, {cite("Bowman", "bowman_gl")} |',
        "| WCP/WCF, ACP/ACF, CAPA/B, E1/E2, FT1/FT2 | постоянно E1/E2 | смена режима CP/CF на останове, FT1/2 в воздушном режиме | открыто сверх 9 | T25B-AO, боковая сервисная зона |",
        "",
        "## PC и охлаждение",
        "",
        f'Первый круг остановился на KF125. Карта 34 сСт даёт 181 л/мин и 1,70 кВт на валу при 2 бар. '
        f'Ветвь при 180 л/мин, Δp чистый / загрязнённый сценарий, бар — {ptable}. '
        f'Баланс 32,603 кВт = 30,000 M1 + 0,550 PC + 0,035 вода + 2,018 прочий унаследованный резерв. '
        'Воздушные вентиляторы добавляют 1,500 кВт. PX/PXA механически на M1. '
        f'Предел 34,2 кВт оставляет PC не более 0,647 кВт по установленной мощности с воздухом. {cite("Карта KF", "kracht_kf")}',
        "",
        "| Тип и карта | Q, л/мин | Δp CB, бар, идеальное окно | Вал горячий / холодный, кВт | IEC, кВт → без/с воздухом | Насос, кг / Δмасса узла* | Qгр, кВт |",
        "|---|---:|---:|---|---|---|---:|",
    ]
    for option in pc["pc_options"]:
        warm = [a["shaft_screen_kW"] for a in option["hot_points"] if a["shaft_screen_kW"] is not None]
        cold_power = [a["shaft_screen_kW"] for a in option["cold_bypass_points"] if a["shaft_screen_kW"] is not None]
        warm_text = f'{fmt(min(warm), 2)}–{fmt(max(warm), 2)}' if warm else "график грубый"
        cold_text = f'{fmt(min(cold_power), 2)}–{fmt(max(cold_power), 2)}' if cold_power else "момент открыт"
        if option["type"] == "vane":
            pressure_terms = [a["pressure_dependent_power_from_catalogue_slope_kW"]
                              for a in option["hot_points"] + option["cold_bypass_points"]]
            cold_text += f'; Δp-компонент {fmt(min(pressure_terms), 2)}–{fmt(max(pressure_terms), 2)}'
            cold_text = cold_text.replace(";", " ·")
        lines.append(
            f'| {cite(option["model"], option["source"])} | {fmt(option["nominal_flow_L_min"], 1)} | '
            f'{pair(option["crack_pressure_ideal_open_range_bar"], 2)} | {warm_text} / {cold_text} | '
            f'{fmt(option["illustrative_IEC_motor_kW"], 2)} → '
            f'{pair([option["installed_base_if_motor_kW"], option["installed_air_if_motor_kW"]])} | '
            f'{fmt(option["pump_mass_kg"], 1)} / {fmt(option["pump_and_motor_change_vs_baseline_proxy_kg"], 1)} | '
            f'{fmt(option["q_dirty_GL180_kW_at_55_oil_30_water"], 2)} |')
    lines += [
        "",
        f'* T16-09 объединяет PC с фильтрами и трубами. Δ к прокси KF125 22,2 кг + ABB 0,55 кВт 8,5 кг, без рам и ПЧ. '
        f'Числа KF/SMT ниже карты экстраполированы, Yuken при 20 сСт без разрешения холостого момента на 1–2 бар. '
        f'Прибавка к CB при полном расходе требует кривой. Q·Δp даёт {fmt(hydro_min)}–{fmt(hydro_max)} кВт. '
        f'Лучший КПД в сравниваемых паспортных точках {fmt(100 * pc["best_catalogue_efficiency_near_duty"], 1)} % '
        f'при 6 сСт и 5 бар, условно {fmt(p_best_min)}–{fmt(p_best_max)} кВт. '
        f'При 34/68 сСт лучший {fmt(100 * pc["best_catalogue_efficiency_HLP_viscosity_brackets"], 1)} %. '
        f'Установленные мощности вариантов справочные. {cite("Двигатели ABB", "pc_motors")}',
        "",
        'Bowman должен подтвердить площадь 2,1 м², воду 150 л/мин, Q и Δp на HLP46 при 42/45/55 °C, '
        'потери и допустимую вязкость при пуске, CuNi 90/10, NH₃, сульфиды, скорость в трубках и EV220B40 вместо 25. '
        'Qгр рассчитано при закрытом CB, воде 30 °C и масле 55 °C. Для воздуха необходимы FT1/FT2, каждый ≥78 л/мин. '
        f'{cite("Профиль GL", "bowman_gl")}',
        "",
        "## ZSF и TF",
        "",
        f'RE 20478 с. 6: «Maximum operating pressure … Port A … 16» бар, B/P 350 бар. С. 7 и 15 дают 1600 л/мин при '
        f'0,30 бар для случая 2, запас {fmt(cav["catalogue_flow_reserve_L_min"], 0)} л/мин. MOC, стальная 133×4, '
        f'K=1,4 ГПа, a={fmt(t["wave_m_s"], 0)} м/с, мембрана 25 л газа, n=1,4, '
        f'C={fmt(t["gas_compliance_L_per_bar_at_high"], 2)} л/бар. Штатный профиль v/a=84 мс. '
        'Аварийные ориентиры VR 36 мс, MF 18 мс по типовым ступеням. ME открывает независимый слив, '
        f'поэтому время фактического исчезновения потока через ZSF неизвестно. {cite("RE 20478", "zsf")} · '
        f'{cite("RE 29123", "wrle_step")} · {cite("RE 29406", "wrce_step")} · {cite("метод", "fluid_transients")}',
        "",
        "| L, м | Штатный | VR 36 мс | MF 18 мс | Кромка 5 мс | Кромка 1 мс |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for length, cases in v5.items():
        lines.append("| " + fmt(float(length), 2) + " | " + " | ".join(fmt(value, 2) for value in cases.values()) + " |")
    lines += [
        "",
        f'Пики в таблице избыточные, бар. При 0,5 м 2L/a=0,87 мс. На 2 м и 5 мс пик {fmt(v5["2.0"]["fast_edge_5ms"], 2)} бар. '
        f'Тракт 0,5 м даёт {fmt(peaks["emergency"], 2)} бар в расчёте первого пика при 5 мс, но отрицательное отражение выходит '
        f'из однофазной области. При 1 мс {fmt(peaks["emergency_fast_edge_1ms"], 2)} бар. Вариант 0,25 м снижает первый пик до '
        f'{fmt(v5["0.25"]["loss_of_control_1ms"], 2)} бар, требуется компоновка и проверка разрыва столба. '
        f'Мгновенная граница M5 {fmt(peaks["instantaneous"], 2)} бар с подпором. '
        f'Для резкой отсечки остаток Q≤{fmt(t["required_snap_downstream_flow_L_min_at_16bar"], 0)} л/мин либо исполнение '
        'A не менее 24 бар по первому пику. Нужна запись Q(t) и p(A) при снятии питания. Тип клапана в схеме сохранён.',
        "",
        f'В сосуде TF пик {fmt(t["tf_peak_bar"])} бар. Оценка 1,778 бар относится к ГЦ перед MF. '
        f'Её консервативная сумма с ростом TF — {fmt(t["tf_exhaust_conservative_combined_bar"])} < 1,9 < 3 бар. '
        f'Пропуск 455 по оценке T-2.5c {fmt(t["rtf_t25c_corrected_screen_L_min"], 0)} против 1589 л/мин. '
        f'Подтвердить ход и противодавление клапана. За полный ход пассивно запертый газ упал бы до '
        f'{fmt(t["sealed_full_stroke_end_abs_bar"])} бар абс. Нужна двусторонняя регулировка до 811 л/мин при TF. {cite("Goetze 455", "rtf_455")}',
        "",
        f'При нижнем уровне 0,4 м и TF 0,55 бар эталон даёт 1,040 бар абс. при L=1 м (+0,027), '
        f'без подпора 0,490. При 0,5 м и 55 °C расчёт даёт порт A {fmt(hot["zsf_port_A_abs_bar"])} → ГЦ '
        f'{fmt(hot["cap_abs_bar"])} бар абс. При 20 °C верхняя оценка Δp ZSF даёт ГЦ '
        f'{fmt(cav["cap_min_abs_bar"])} бар абс. ({fmt(cav["air_release_margin_bar"])}). '
        'α=0,077 для HLP46 при 20 °C. При равной температуре масла в T0 и линии условие Генри даёт 1,013 бар. '
        'Давление пара Shell <0,5 Па при 20 °C. При 55 °C проверена чувствительность к водяному пару, '
        'для точного давления пара масла данных нет. Сценарий 0 °C также не проходит в вязкой огибающей. '
        f'{cite("Эксперимент HLP46", "bunsen_hlp46")}',
        "",
        f'На полном расходе при 20 °C нужен подтверждённый Δp ZSF ≤{fmt(hot["maximum_allowed_zsf_dp_bar"])} бар. '
        f'Либо подпор ≥{fmt(mitigation["minimum_TF_gauge_bar_for_20C_full_rate"])} бар на нижней границе, что конфликтует с 1,9 бар. '
        f'Дерейт до {fmt(mitigation["cold_flow_derate"]["flow_L_min"], 0)} л/мин даёт +0,020 бар, но G-CYCLE '
        f'{fmt(cold["cycle_s"])} с / {fmt(cold["rms_kW"])} кВт при квалифицированной температуре модели, FAIL. '
        f'Прогрев примерно до {fmt(mitigation["minimum_preheat_temperature_C_for_0p02_bar_margin_screen"], 1)} °C — '
        'вариант для согласования, проверка отдельного режима и реальной вязкостной кривой обязательна.',
        "",
        "## LP, рукава и отпирание",
        "",
        "| Параметр | t26a | t29 | Причина |",
        "|---|---:|---:|---|",
        f'| cycle_model.lp.shell_L, л | 18,4 | 17,8 | Решение ГК, {cite("Parker MSG10-4082/UK, с. 5", "parker_lp")} |',
        "",
        'От P1 через P/MA до ГЦ и по силовым карманам MF/MC/ZSF — стальная труба EN 10305-4 или эквивалент. '
        'Подтвердить мёртвый объём 0,8 л и геометрию короткого PF. В декомпрессии P1 отделён MP/MHOLD. '
        'Вне сжатия остаются пилот DN10/19 (0,3–1,5 м), шибер DN25 (0,4–1 м), рабочие линии подвижного монтажа при необходимости '
        'DN38 (0,4–1 м), дренаж DN38 и CP/CF воздушной опции DN50. Для 575X каталог даёт объёмное расширение '
        f'и расчёт K участков в results.json. Для 797TC и 811HT нужна кривая точной сборки по ISO 6801. '
        f'{cite("CAT 4660, G-6", "hose_ve")} · {cite("797TC", "hose_797tc")}',
        "",
        f'Kэфф главного объёма 1,400 ГПа по модели. Первый PASS на сетке {fmt(result["hose_K_threshold_Pa"] / 1e9)} ГПа, '
        f'последний FAIL {fmt(result["highest_sampled_failing_K_Pa"] / 1e9)}. '
        'Сетка 0,02 ГПа и 0,002 в переходе, RMS местами немонотонен. Каждый результат ниже получен штатным гейтом.',
        "",
        "| K, ГПа | с | RMS, кВт | K, ГПа | с | RMS, кВт |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    scan = result["k_scan"]
    middle = (len(scan) + 1) // 2
    for i, first in enumerate(scan[:middle]):
        second = scan[middle + i] if middle + i < len(scan) else None
        value = [fmt(first["K_Pa"] / 1e9), fmt(first["cycle_s"]), fmt(first["rms_kW"])]
        value += ([fmt(second["K_Pa"] / 1e9), fmt(second["cycle_s"]), fmt(second["rms_kW"])]
                  if second else ["—", "—", "—"])
        lines.append("| " + " | ".join(value) + " |")
    lines += [
        "",
        f'15,59 кН — эквивалент прежнего кулачка из T-1.2b/T-2.2i. Для Ø125/56, η=0,92 это '
        f'{fmt(u["legacy_equivalent_net_bar"], 2)} бар эквивалентного перепада. LP при 38 бар даёт '
        f'{fmt(u["lp_only_breakaway_kN"], 2)} кН после потерь и веса/направляющих. P1 через PPB, A через PAT, '
        f'35 бар приведённого перепада на первых 12 мм дают {fmt(u["unlock_force_kN"], 2)} ≥ {fmt(u["unlock_required_kN"], 2)} кН. '
        f'При pA=3 бар это pB≥{fmt(u["rod_chamber_min_bar_with_assumed_return"], 2)} бар и напор ≥{fmt(u["header_min_bar_with_inlet_loss"], 2)} бар. '
        f'Нагрузка в номинальном гейте {fmt(u["gate_first_12_mm_load_kN"], 2)} кН вместе с фоном. '
        'Подтвердить доступный перепад, остаточную реакцию и фактический ход освобождения носа на сборке.',
        "",
        "## Масса и решение ГК",
        "",
        f'К учёту {fmt(base_mass, 2)} + {fmt(m["station_mass_delta_kg"], 2)} = {fmt(m["station_kg"], 2)} кг '
        f'по известным деталям. Машина A по трём вариантам — '
        f'{pair(sorted(a["t29_accounted_kg"] for a in m["machine_A_variants"].values()), 2)} кг. '
        f'Открытые строки и источники в station.t29.yaml. Сокращение PF могло бы дать '
        f'{fmt(m["potential_PF_dry_saving_kg_unbooked"], 2)} кг сухой трубы, оставив минимум '
        f'+{fmt(m["station_delta_after_unbooked_PF_saving_kg"], 2)} кг по этому сценарию. '
        f'Диагностика без LP на шибере даёт {fmt(alternatives["cycle_s"])} с / {fmt(alternatives["rms_kW"])} кВт, '
        f'{alternatives["gate_status"]}. Альтернатива сохраняет остальные LP-ветви и исключает аппаратный прирост LG. '
        f'Также возможен компактный блок с DFEJ после проверки потерь, ресурса и дозирования VG. {cite("DFEJ", "compact_gate_alternative")}',
        "",
        "**Проект D-GK.** T-2.9 — STOP_ZSF и STOP_MASS. PC/CB передать оператору. Принять расчётный LP Parker, "
        "жёсткий главный тракт и двухканальную логику носа на продолжение КД. Для выхода из стопа согласовать холодный режим и "
        "стендовый критерий p(A), уточнить короткую трассу TF и решить, разрешать ли вариант без LP на шибере.",
        "",
    ]
    output = "\n".join(lines)
    path = ROOT / "report.md"
    path.write_text(output, encoding="utf-8", newline="\n")
    check = path.read_text(encoding="utf-8")
    assert check == output and "?" not in check and "\ufffd" not in check
