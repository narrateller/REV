"""Render the decision package in UTF-8 with numbers from the generated ledgers."""

from html import escape


def number(value, places=2):
    return f"{value:.{places}f}".replace(".", ",")


def span(values, places=2):
    return "–".join(number(value, places) for value in values)


def render(data):
    m = data["metrics"]
    h = data["heat"]
    t = data["tank"]
    c = data["cooling_selection"]
    ledger = data["station_mass"]
    machine = data["machine_mass"]
    sources = data["sources"]
    g = data["gates"]
    p = t["structure"]
    nominal = h["cases"]["nominal"]["reference"]
    adverse = h["cases"]["adverse"]["reference"]
    brook = h["motor_trials"]["brook"]
    abb = h["motor_trials"]["abb"]

    def links(*ids):
        return ", ".join(f"[{tag}]({escape(sources[tag]['url'], quote=False).replace(chr(63), '&#63;')})" for tag in ids)

    def n(value, places=2):
        return number(value, places)

    def motor_line(name, candidate):
        a, b = candidate["nominal"], candidate["adverse"]
        cells = (name, f"{a['rpm']} / {b['rpm']}", f"{n(a['slip_fraction']*100, 2)} / {n(b['slip_fraction']*100, 2)}",
                 f"{n(a['cycle_s'], 6)} / {n(b['cycle_s'], 6)}",
                 f"{n(a['rms_kW'], 6)} / {n(b['rms_kW'], 6)}",
                 f"{n(a['peak_Nm'], 1)} / {n(b['peak_Nm'], 1)}",
                 n(a["pullout_Nm"], 1))
        return "| " + " | ".join(cells) + " |"

    def trial(fragment):
        return next(row for row in c["alternatives"] if fragment in row["model"])

    tf = next(row["evidence"] for row in data["measures"] if row["measure"].startswith("Два Goetze"))
    water = next(row["evidence"] for row in data["measures"] if row["measure"].startswith("Parker PWO"))
    scenarios = m["machine_A_after_groups_kg_range"]
    short_checks = {
        "brook": ("207 кг семейства, фланец IEC 200", "Время цикла, паспорт B5 и колокол."),
        "abb": ("246 кг семейства, цикл при 400 В", "RMS. Масса B5/B35 открыта. Вне суммы B."),
        "pwo": ("79 кВт при ΔT 40 K, 150 л/мин масла", "Тепло и обвязка на фактической воде. Для автономного контура добавить насос, охладитель, бак и заполнение."),
        "t21_mass": ("Сравнение насосов по T‑2.1", "Другой регулятор. Нужны цикл и масса обвязки."),
        "parker_accumulator": ("20 л, 330 бар, G2, 49 кг", "17,8 вместо 18,4 л газа. Проверить цикл, SAF и крепление."),
        "tank_structure": ("Лист, нагрузки и масса", "Эскиз, швы, герметичность, опоры, габарит."),
        "iso4413": ("Уровень, всас, нагрев, каталоги", "Подтвердить всас и деаэрацию на геометрии."),
    }
    t16_checks = {
        "t26_inventory": ("Сверены арматура и порты", "Нужны эскиз, потери, масло и масса. Исключить корпуса RPIC."),
        "bell": ("Две RHS и четыре накладки", "Опоры, подъём и соосность при листе 3 мм."),
        "sun": ("125–270 л/мин при номинале до 380", "Внешний слив, противодавление, пик 315 бар."),
        "goetze": ("Резьбовые DN65 по 8,9 кг. Пересчёт с воды", "Сброс HLP46, выходное давление и импульс в TET."),
        "decisions": ("Старая геометрия T‑1.6", "Силовая часть заморожена по D‑OP‑19."),
    }
    lines = [
        "# T‑2.5. Облегчение гидростанции, круг 2",
        "",
        f"**{m['status']} по массе.** Выпущена ведомость эталонной станции T‑2.6 схемы A массой **{n(m['station_t25_kg'])} кг**. Зачтено **{n(m['reduction_kg'])} кг** из требуемых 170 кг. Подпор TF **0,60 ± 0,05 бар**, 80 л геометрически и 55 л масла, азот отделён мембраной. Расчётный запас масла TF {n(t['TF']['initial_margin_L'])} л. {links('t26', 't26_replay', 'decisions')}.",
        "",
        "## База массы",
        "",
        f"Ведомость карточки {n(ledger['T16_kg'])} + {n(ledger['T26_delta_kg'])} = {n(m['station_card_base_kg'])} кг. Привод A4VSO и DFE1Z добавляет 19,00 кг к станции и уже входит в машину 4942,65 кг. База машины до силовых поправок с T‑2.6 {n(machine['machine_reference_plus_hydraulics_kg'])} кг. В строку T‑1.6 «ГА обоих контуров» перешли LP 3047174 по 49 кг и прежний пилотный 3047166 по 15 кг. Схема T‑1.6 уже назначала AX 3047170. Приняты LP 63 кг по карточке артикула и AX 31 кг. Обе базы увеличены на +14 и +16 кг, итого **+30,00 кг**. Общая таблица HYDAC для LP показывает 49 кг, поэтому нужен паспорт поставки. SAL/SAX 24,8 кг за пару относятся к коллекторной строке. {links('legacy_accumulators', 'ax_lp', 'modern_accumulators', 't26_inventory', 't21_mass')}.",
        "",
        "## Привод и охлаждение",
        "",
        "У обоих кандидатов алюминиевый корпус, 30 кВт S1 и IE3 при 50 Гц. Неблагоприятный случай T‑2.6 добавляет 15 об/мин скольжения. Момент рассчитан при пике 38,31 кВт. Пределы 5,904 / 6,193 с и 29,987 кВт RMS применены до округления.",
        "",
        "| Мотор | об/мин | Скольжение, % | Цикл, с | RMS, кВт | Пик, Н·м | Опрокид., Н·м |",
        "|---|---:|---:|---:|---:|---:|---:|",
        motor_line("Brook", brook),
        motor_line("ABB при 400 В", abb),
        "",
        f"Brook превышает оба предела времени, ABB превышает номинальный RMS. Для Brook Ø300 / PCD 350 и вал Ø55×110 совпадают с OMEC B5. Колокол сопрягает их с ISO 3019‑2 NG180, посадка Ø160. Каталог Brook подтверждает 207 кг для семейства, публичный артикул 4P указан как B3. Заказные массы B5/B35, вылеты и комплектовочные чертежи открыты. В протоколе ABB 1481 об/мин приведены при 380 В. Сравнение выполнено для 400 В. {links('brook', 'brook_mount', 'omec', 'a4vso', 'bell', 'abb', 'abb_family')}.",
        "",
        f"На валу эталона {n(nominal['average_kW'], 3)} / {n(adverse['average_kW'], 3)} кВт в среднем. Тепло по статьям T‑1.6 **{n(m['heat_nominal_kW'])} / {n(m['heat_adverse_kW'])} кВт**. При 40 °C воздуха, 55 °C масла и 180 л/мин два ASA0567AA47 дают **{n(m['cooling_dirty_kW'])} кВт** после двух поправок по 15 % при требовании **{n(m['cooling_required_kW'])} кВт**. Установлено {n(m['installed_kW'], 3)} кВт, запас вентиляторов {n(c['allowed_fan_increase_kW'], 3)} кВт.",
        "",
        f"Мера по охлаждению **0 кг**. При той же точке ASA0927 даёт {n(trial('ASA0927')['heat_point']['dirty_kW'])} кВт, два Parker 058‑8 дают до {n(trial('2 × Parker')['heat_point']['dirty_kW'])} кВт, HYDAC AC‑LN10L до {n(trial('AC-LN10L')['heat_point']['dirty_kW'])} кВт по верхней оценке. Более мощные Emmegi HPA Larger и Parker 112‑8 превышают лимит вентиляторов. Также проверены Emmegi HPA Compact, KTR и AKG. Один ASA0927 занимает 1170×1100×664 мм вместо 920×860×543 мм на модуль, оба используют ASA NG40. Parker 058‑8 имеет G2 и глубину 652 мм, HYDAC 10L имеет G1½ и глубину 766 мм. Полная таблица с расходами, допусками и массами в results.json. {links('thermal_method', 'asa_ports', 'parker_lac', 'hydac_cooling', 'emmegi', 'akg', 'ktr_cooling')}.",
        "",
        "## T0 и квалификация мер",
        "",
        f"По шагам штатной траектории T‑2.6 с моделью стопа минимальный уровень с резервом **{n(t['stop']['min_running_L'])} л**. После закрытия TF/BAL, сброса LP и AX и снятия упругого объёма MA/MB верхняя оценка **{n(t['stop']['max_stopped_L'])} л** при LT 205 л. Ход после снятия питания оценён с торможением штатной рампой. Скорости разряда, выбег и волна уровня требуют стенда.",
        "",
        f"Минимум номинальной заправки по LT {n(t['level_minimum_initial_L'])} л, по 30 с деаэрации при общем пути возврата и охладителя {n(t['deaeration']['level_with_shared_path_L'])} л, по заглублению условного всаса DN100 {n(t['suction']['provisional_required_oil_L'])} л. Определяет **{t['determining_screen']}**. Верхняя уставка после стопа ограничивает заправку {n(t['stop']['max_nominal_initial_at_high_trip_L'])} л. При принятых условиях диапазон отсутствует. До квалификации в ведомости 190 л для T0 объёмом 252 л. Для A4VSO требуется ≥0,8 бар абс. на S, бюджет потерь {n(t['suction']['available_loss_at_zero_flange_elevation_bar'], 3)} бар при фланце на высоте дна. Нужны фактические высоты, потери на холодном масле и подтверждение путей деаэрации. При +40 °C прогрев без охладителя до 55 °C занимает {n(t['thermal']['heating_to_limit_without_cooling_s']/60, 1)} мин, с загрязнёнными матрицами за 10 мин рост {n(t['thermal']['rise_after_10_min_dirty_K'], 1)} К. {links('interlocks', 'iso4413', 'parker_diffuser', 'suction_screen', 'a4vso')}.",
        "",
        f"Эскиз стенок T0 из S235JR даёт {n(p['static']['bending_MPa'], 1)} МПа гидростатически и {n(p['flooded_transport']['bending_MPa'], 1)} МПа при транспортной огибающей заполненного бака. Дно и крышка 4 мм, четыре ребра 30×3 мм и существующие перегородки. Нагрузки идут в раму, расчётное натяжение стропа {n(p['lift']['sling_tension_N']/1000, 1)} кН. Для бака как основания нужны жёсткость, опоры и соосность. {links('tank_structure', 'transport', 'lifting')}.",
        "",
        "## Меры и масса машины",
        "",
        "| Группа | Мера | Δм, кг | Проверка | Риск или условие | Источник |",
        "|:---:|---|---:|---|---|---|",
        "| A | Зачтённые меры | 0,00 | Подтверждённые замены отсутствуют. | — | Ведомость |",
    ]
    for row in data["measures"]:
        delta = "н/о" if row["delta_kg"] is None else n(row["delta_kg"])
        if row["group"] == "C" and row["measure"].startswith("Parker PWO"):
            delta += " + m"
        first, second, *_ = row["source_ids"]
        check, risk = t16_checks[second] if first == "t16" else short_checks[first]
        lines.append(f"| {row['group']} | {row['measure']} | {delta} | {check} | {risk} | {links(first, second)} |")
    lines.extend([
        "",
        f"Для пары Goetze оценка при 2,09 бар на входе и 0,2 бар на выходе составляет {n(tf['two_valves_at_2p09_bar_L_min'], 0)} л/мин. Консервативный сценарий TF по потоку MF T‑2.6 даёт {n(tf['conservative_T26_cap_feed_L_min'], 0)} л/мин. Для 642 производитель требует свободный сброс. У RPIC для суммы надбавки расхода и противодавления остаётся 15–17 бар до 315 бар. **m** в строке PWO — ещё не определённая масса штуцеров, арматуры и воды в аппарате. Уже включено {n(water['water_pipes_wet_kg'])} кг мокрых магистралей. Подача от площадки оценивается от {n(water['minimum_water_flow_at_10_K_L_min'], 1)} л/мин при нагреве воды на 10 К. {links('goetze_install', 'sun', 'pwo_selection', 'water_tube')}.",
        "",
        f"Суммы по группам, кг **A {n(m['group_reduction_kg']['A'])}**, **B {n(m['group_reduction_kg']['B'])}**, **C до {n(m['group_reduction_kg']['C'])} − m**. Сценарий C включает старую оценку крышки вне станции. T‑2.2i считает нижнюю границу машины оптимистичной из-за полной замены передней щеки. {links('t22i_review')}.",
        "",
        "| Сценарий | Экономия, кг | Машина по базе карточки, кг | Машина с поправкой ГА, кг |",
        "|---|---:|---:|---:|",
    ])
    for tag, label in (("A", "A"), ("A_B", "A+B"), ("A_B_C", "A+B+C")):
        adjustment = " + m" if tag == "A_B_C" else ""
        saved = " − m" if tag == "A_B_C" else ""
        scenario = scenarios[tag]
        lines.append(f"| {label} | {n(m['cumulative_reduction_kg'][tag])}{saved} | "
                     f"{span(scenario['machine_A_kg_range'])}{adjustment} | "
                     f"{span(scenario['machine_A_corrected_kg_range'])}{adjustment} |")
    lines.extend([
        "",
        "## Гейты и проект D‑GK",
        "",
        f"G‑PFACE **{g['G-PFACE']['status']}**, {n(g['G-PFACE']['value'])} МПа. G‑DOSE **{g['G-DOSE']['status']}**, {n(g['G-DOSE']['value'], 0)} мм. G‑CYCLE {g['G-CYCLE']['status']}, {n(g['G-CYCLE']['value'], 3)} с, справочно по D‑GK‑13 и D‑OP‑16. Эталон {n(m['cycle_nominal_s'], 3)} / {n(m['cycle_adverse_s'], 3)} с, RMS {n(m['rms_kW'], 3)} кВт. [Гейты](gates.t25.json).",
        "",
        f"**Проект D‑GK.** Принять ведомость T‑2.5 с TF 80/55 л и 0,60 ± 0,05 бар. Зафиксировать STOP по облегчению. Станция {n(m['station_t25_kg'])} кг, снижение A {n(m['reduction_kg'])} кг. Передать оператору сценарии PWO, PV180 и задней крышки с указанными границами. Сохранить ограничения D‑OP‑09, D‑OP‑16 и D‑OP‑19 до отдельного решения.",
        "",
    ])
    return "\n".join(lines)
