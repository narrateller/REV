"""Render the T-2.9b decision record in UTF-8."""
from build_scheme import HERE, ROOT, read


def fmt(number, decimals=3):
    return f"{number:.{decimals}f}".replace(".", ",")


def link(label, path):
    return f"[{label}]({path})"


def render_report(data, gate_data):
    pc = data["pc"]["preferred_candidate"]
    power, mass, oil = (data[key] for key in ("power", "mass", "oil_modulus"))
    gate, checked = data["gate_nominal"], data["circuit"]
    ref = {row["id"]: row for row in gate_data["gates"]}
    sources = read(HERE / "sources.yaml")["sources"]
    short_refs = {
        "PC": link("KRACHT, с. 23", sources["pc_kf180"]["url"]),
        "MPC": link("ABB, с. 91", sources["pc_abb_ie3_6p"]["url"]),
        "PC-VFD": link("ABB, с. 121", sources["pc_vfd"]["url"]),
        "RGC": link("Sun, с. 1", "https://www.wojanis.com/customer/docs/skudocs/cxhaxan.pdf"),
        "RGC-BODY": link("IAX/S", sources["rgc_body"]["url"]),
        "XZD": "Sun PRFB, с. 1",
        "PTZ": link("ifm, Mass", sources["ptz_ifm"]["url"]),
        "RVZ": link("Sun, с. 1–2", sources["rvz_sun"]["url"]),
        "LG": "T-2.9, ledger LR",
        "ALP": link("Parker, с. 5", sources["parker_lp"]["url"]),
    }
    init = pc["start"]
    kmin = data["k_threshold_t29b_Pa"]
    kfail = data["highest_sampled_failing_K_Pa"]
    lines = [
        "# T-2.9b · Гидросхема A",
        "",
        f"**STOP по PC и массе.** Кандидат KF180 с двигателем 1,5 кВт даёт расчётно "
        f"{fmt(pc['q_dirty_kW'], 2)} кВт на GL180. Нужны расход на HLP46 при 55 °C, характеристика CB с полным "
        f"перепуском и проверка пускового момента. Ведомость кандидата "
        f"**{fmt(mass['station_kg'], 2)} кг** ({fmt(mass['station_delta_vs_t25c_kg'], 2)} кг к T-2.5c при допуске +10 кг).",
        "",
        f"**Гейты без LG.** G-PFACE {fmt(ref['G-PFACE']['value'], 2)} МПа, G-DOSE {ref['G-DOSE']['value']:g} мм, "
        f"G-CYCLE {fmt(gate['cycle_s'], 6)} с / RMS {fmt(gate['rms_kW'], 3)} кВт. Все PASS, "
        f"метод reference_model. Проверка схемы {checked['defects']} дефектов, "
        f"{checked['mutations']['rejected']}/{checked['mutations']['total']} мутаций отклонено. "
        + link("Гейты", "gates.t29b.json"),
        "",
        "## PC, обход и баланс мощности",
        "",
        "| Кандидат | Положение в каталоге, расход и вал | Масса голого насоса, кг |",
        "|---|---|---:|",
        f"| KF180, 950 об/мин | 169 л/мин и 1,20 кВт при 2 бар, 34 сСт; с запасом 15 % 1,38 кВт. "
        f"{link('KRACHT, с. 18–20', sources['pc_kf180']['url'])} | 24,8 |",
        f"| KF112, 1450 об/мин | 161 л/мин и 1,40 кВт при 2 бар; с запасом 1,61 кВт. "
        f"При меньшем Δp запас возможен. Нужна карта при 1–2 бар. {link('KRACHT, с. 19–20', sources['kracht_kf']['url'])} | 16,0 |",
        f"| SMT16B PSP55-330L, 1450 об/мин | 166–170 л/мин и 1,94–2,57 кВт при 5 бар, 6–68 сСт. "
        f"Для рабочего Δp табличные данные требуют экстраполяции. {link('Parker, с. 23', sources['pc_screw']['url'])} | 15,5 |",
        f"| PV2R4-153, 1200 об/мин | ≈180 л/мин при малом Δp; кривая мощности не даёт точного холостого "
        f"момент на HLP46. {link('Yuken, с. 165, 175', sources['pc_vane']['url'])} | 68,5 |",
        "",
        "| Масло, °C | Δp при 180 л/мин, чистый / грязный, бар | Δp KF180, верхняя оценка чистый / грязный, бар |",
        "|---:|---:|---:|",
    ]
    points = pc["hot_operating_points"]
    for clean, dirty in zip(points[::2], points[1::2]):
        lines.append(f"| {clean['temperature_C']} | {fmt(clean['branch_dp_at_180_bar'])} / "
                     f"{fmt(dirty['branch_dp_at_180_bar'])} | {fmt(clean['branch_dp_upper_bar'])} / "
                     f"{fmt(dirty['branch_dp_upper_bar'])} |")
    lines += [
        "",
        f"KF180 и ABB M3AA 100LC 6 весят {fmt(pc['pump_and_motor_mass_kg'], 1)} кг без ПЧ и монтажа. "
        f"Оценка подачи при 55 °C {fmt(pc['flow_screen_min_L_min'], 1)} л/мин учитывает −5 % и утечки ∼1/ν. "
        f"В воздушной опции необходимо ≥78 л/мин в каждой ветви; допустимая разница от половины подачи "
        f"по оценке всего {fmt(pc['air_allowable_imbalance_from_equal_split_L_min'], 2)} л/мин. "
        f"Горячий расчётный Δp ниже цели CB 1,70 бар. На холодном масле 20 °C по Вальтеру 134 сСт; "
        f"PC обесточен до {init['pc_off_below_start_C']} °C ({fmt(init['first_pc_start_viscosity_mm2_s'], 1)} сСт), "
        f"выключение ниже {init['trip_below_C']} °C. Прямой старт при 20 °C и 2 бар даёт верхнюю оценку "
        f"{fmt(init['shaft_kW_screen_if_enabled_at_20_and_CB_at_2bar'], 2)} кВт. Прогрев на разгруженном P1. "
        "При разгоне ограничить Δp PC до 2 бар, включая CB, CD и всас. Массу и момент разгона ещё сверить "
        "на сборке; минимальная температура площадки не задана. "
        + link("Shell, SDS § 9.1 и источник 20 °C", "calc/T-2.9b/sources.yaml"),
        "",
        f"**Мощность:** 30,000 M1 + 1,500 PC + 0,035 вода + 2,018 = **{fmt(power['installed_kW'])} кВт** "
        f"в базе. 2 × 0,75 кВт дают **{fmt(power['installed_with_air_option_kW'])} кВт** с воздухом. "
        "Резерв 2,018 кВт включает дозатор 0,750 (T-1.6), RG/RT 0,060 и управление 0,024 (T-2.6), "
        "нераспределённый остаток ГК 1,184 (1,100 T-1.6 + 0,084 в базовом входе T-2.6). "
        "PX/PXA на валу M1. Отдельного нагревателя и вентилятора M1 в ведомости нет. Мощность ПЧ как привода PC "
        "учтена по номиналу двигателя; тепловыделение шкафа сверить отдельно. "
        + link("Построчный баланс", "calc/T-2.9b/power_balance.py"),
        "",
        "## K масла, сталь и порог",
        "",
        f"Изотермический секущий K = Δp / (1 − ρ₀/ρₚ) на 0–270 бар изб. по плотности HM 46 "
        f"{fmt(oil['temperatures'][50]['K_oil_Pa']/1e9)} / {fmt(oil['temperatures'][55]['K_oil_Pa']/1e9)} ГПа "
        "при 50/55 °C (55 °C интерполировано). Дегазация и доля растворённого воздуха в опыте не указаны. "
        f"При отсутствии свободного воздуха расчёт Ламе (Ø280/352, E = 210 ГПа, ν = 0,30, "
        f"0,8 л плюс трубы и карманы, конец прессования x = {fmt(oil['press_end_x_mm'], 1)} мм) "
        f"даёт нижнюю оценку по стенкам {fmt(oil['K_eff_Pa']/1e9)} ГПа. "
        f"При 0,1 % свободного воздуха оценка {fmt(oil['temperatures'][55]['air_sensitivity'][1]['K_eff_Pa']/1e9)} ГПа. "
        "Геометрия трасс оценочная. Для КД проверить податливость крышек и рамы и объёмы "
        "P1/MA и карманов MF/MC/ZSF, включая согласование с мёртвым объёмом гейта. "
        + link("Knežević, табл. 1, с. S1464", sources["hm46_density"]["url"]),
        "",
        "| K, ГПа | Цикл, с | RMS, кВт | Карточка / G-CYCLE |",
        "|---:|---:|---:|---|",
    ]
    for row in data["k_scan"]:
        K_Pa = row["K_Pa"]
        if (K_Pa >= 1_240_000_000 and K_Pa % 20_000_000 == 0) or K_Pa in {kmin, kfail,
                data["k_threshold_frozen_gate_Pa"], data["highest_sampled_failing_frozen_gate_K_Pa"]}:
            lines.append(f"| {fmt(K_Pa/1e9)} | {fmt(row['cycle_s'], 6)} | {fmt(row['rms_kW'])} | "
                         f"{'PASS' if row['card_pass'] else 'FAIL'} / {row['gate_status']} |")
    lines += [
        "",
        f"Порог на сетке 0,002 ГПа — {fmt(kmin/1e9)} ГПа. Первое превышение при {fmt(kfail/1e9)} ГПа "
        "относится к порогу карточки. Порог PASS штатного G-CYCLE с пределом 6,0 с составляет "
        f"{fmt(data['k_threshold_frozen_gate_Pa']/1e9)} ГПа. "
        + link("Все точки", "calc/T-2.9b/k_scan.json"),
        "",
        "## Ведомость и ревизия",
        "",
        f"Машина A по трём вариантам T-2.2i "
        f"{' / '.join(fmt(row['t29b_kg'], 2) for row in sorted(mass['machine_A_variants'].values(), key=lambda r: r['t29b_kg']))}"
        f" кг при 5000 кг. Незакрытые строки дают до {fmt(mass['mass_unresolved_extra_upper_kg'], 1)} кг "
        "дополнительных проектных допусков. Верхние оценки строк, включая U04, приведены в ведомости. "
        f"Укорочение PF при подтверждении исходного метра может дать {fmt(mass['alternatives']['TF_prelength_saving_if_inherited_1m_verified_kg'], 2)} кг. "
        f"При квалификации KF112 с 1,5 кВт дельта учтённых строк оценивается в "
        f"+{fmt(mass['alternatives']['KF112_with_1p5kW_delta_if_qualified_kg'], 2)} кг. "
        + link("Ведомость T-2.9b", "design/hydraulics/station.t29b.yaml"),
        "",
        "| Элемент | Было | Стало | Δм, кг | Δуст., кВт | Источник | Причина |",
        "|---|---|---|---:|---:|---|---|",
    ]

    short = {
        "PC": ("KF125", "KF180, кандидат", "Карта 2 бар"),
        "MPC": ("0,55 кВт, прокси", "ABB 1,5 кВт IE3", "D-OP-22"),
        "PC-VFD": ("Нет", "ABB ACS180", "950 об/мин"),
        "RGC": ("В расчёте T-2.9", "CXHAXAN в ведомости", "Регенерация"),
        "RGC-BODY": ("Открыт", "IAX/S, кандидат", "T-16A, 350 бар"),
        "XZD": ("В расчёте T-2.9", "PRFB-CBN в ведомости", "Пилот Z"),
        "PTZ": ("По ТЗ", "PT5402, кандидат", "Контроль Z"),
        "RVZ": ("По ТЗ", "RDBA, кандидат", "Защита Z"),
        "params.lp.routes": ("С шибером", "pre_up / pre_down / eject", "Решение ГК"),
        "params.oil.bulk_modulus_Pa": ("1,40 ГПа", "1,40 ГПа масло + сталь", "Ламе"),
        "params.gate_release_cap_bar": ("5 бар", "5 бар = 3 + запас 2", "Граница нагрузки VG"),
        "P1 / pre_up": ("35 бар приведённых", "P1 ≥45 бар при отпирании", "Запас усилия"),
    }
    for tag, before, after, kg, kW, source, basis in data["circuit_revision"]:
        before, after, reason = short.get(tag, (before, after, basis))
        source_label = short_refs.get(tag, link(source.rsplit("/", 1)[-1].split("#", 1)[0], source))
        kg_text = str(fmt(kg)) if kg is not None else "—"
        if tag in {"RGC", "XZD"}:
            kg_text = "0 к T-2.9"
        lines.append(f"| {tag} | {before} | {after} | {kg_text} | {fmt(kW)} | {source_label} | {reason} |")
    lines += [
        "",
        "Из набора T-2.9 снято 0 мутаций. Две независимые верхние оценки cap ≤3 бар, в модели 5 бар "
        "консервативно увеличивают нагрузку VG. При потере валидности TT быстрый подвод блокируется. "
        "Зачёт массы машины и выпуск КД зависят от испытаний сырья по D-OP-21. "
        + link("Все источники и места чтения", "calc/T-2.9b/sources.yaml"),
        "",
        "## Проект записи D-GK",
        "",
        f"| D-GK | T-2.9b STOP по PC и массе. Принять схему шибера от P1, ограничения TT/P1 и жёсткий тракт в T-2.3. "
        f"G-CYCLE {fmt(gate['cycle_s'], 3)} с, RMS {fmt(gate['rms_kW'])} кВт. Для PC квалифицировать CB, момент "
        "и расход при 55 °C; по массе проверить KF112 как альтернативу и согласовать дальнейшее ведение ведомости. | T-2.9b |",
    ]
    document = "\n".join(lines) + "\n"
    assert chr(63) not in document
    (ROOT / "report.md").write_text(document, encoding="utf-8", newline="\n")

