"""Render the short qualification report from the issued calculation data."""
from hand import HERE, ROOT, json_read


def fmt(value, digits=2):
    return f"{value:.{digits}f}".replace(".", ",")


def render():
    r = json_read(HERE/"results.json")
    gates = {g["id"]:g["value"] for g in json_read(ROOT/"gates.t22b.json")["gates"]}
    cases = r["fea"]["cases"]
    levels = [cases[f"portal_{i}_64"] for i in range(3)]
    coarse, _, fine = levels
    conv = r["fea"]["convergence"]
    rows = r["mass"]["b"]["rows_kg"]
    base = r["mass"]
    mass = base["b"]
    optim = base["b_sensitivity"]
    hand = r["hand"]["b"]["0.64"]
    vdi = r["VDI_2230"]
    geo = r["kinematic_screen"]
    cf = fine["contact"]
    fastener_sections = vdi["R9"]["FEA_axial_and_bending_by_section"]
    limiting_stud, limiting_z, stud_fat = min(
        ((n,z,value) for n,probes in fastener_sections.items() for z,value in probes.items()),
        key=lambda result:result[2]["fatigue_factor"])
    stud_factor = stud_fat["fatigue_factor"]
    stud_static = min(value["service_static_factor"] for probes in fastener_sections.values()
                      for value in probes.values())
    upper_pad = vdi["R10"]
    bolt = vdi["R11"]
    geometry = lambda c, dim: c["paired_section_300_bar"][dim]["change_from_design_at_300_mm"]
    h, w = geometry(fine,"height"), geometry(fine,"width")
    p, pu = cf["RIGHTLOW"]["inboard_gauge_pressure_MPa"], cf["RIGHTFRONT"]["inboard_gauge_pressure_MPa"]
    avg = cf["RIGHTLOW"]["mean_pressure_active_area_MPa"]
    penalty = r["fea"]["penalty_sensitivity"].get("penalty_20000_portal_0_64")
    balance = max(max(c["global_force_balance_fraction"],c["shoe_force_balance_fraction"]) for c in cases.values())
    spring_force = max(c["stabilizer_load_fraction"] for c in cases.values())
    spring_energy = max(c["stabilizer_stored_energy_fraction"] for c in cases.values())
    preload = [abs(stud["force_N"][0])/1000 for case in cases.values() for stud in case["studs"].values()]
    joint = fine["tied_interface_traction"]["FRONTPOST2"][-1]
    assembled_H2 = [base["base_T22_round_2_kg"]+optim["package_without_unqualified_savings_delta_kg"]+h2
                    for h2 in base["outstanding_MA_delta_kg"]]
    lines = r["fea"]["effective_contact_lines_finest_64_36"]
    mck = fine["manual_FEA_sections"]["key"]
    mcy = fine["manual_FEA_sections"]["yoke"]
    text = f"""# T-2.2b · Круг 2

**HOLD для исполнения (б) с двумя торцевыми ярмами и четырьмя стяжками.** Расчёт достиг 315 бар на трёх сетках для 60/40 и 64/36. Исполнение выходит за экран смятия и допуск высоты брикета. Полное прилегание переднего стыка и ресурс резьбы не подтверждены. G-PFACE, G-DOSE и G-CYCLE прошли с результатами {fmt(gates['G-PFACE'])} МПа, {fmt(gates['G-DOSE'],0)} мм и {fmt(gates['G-CYCLE'],3)} с.

## Нагрузка и силовой путь

Профиль T-1.2b на x = 94,476…205 мм даёт {fmt(r['hand']['load']['force_300_N']/1000,1)} кН при 300 бар и {fmt(r['hand']['load']['force_315_N']/1000,1)} кН при 315 бар, центр x = {fmt(r['hand']['load']['centroid_x_mm'],3)} мм. Нагруженный засов при 315 бар воспринимает 771,1/822,5 кН для 60/40 и 64/36. По плечам 71/150 мм получается 365/389 кН. Для двух торцевых опор и осей стяжек y = ±189 мм наибольшая реакция равна {fmt(hand['actual_portal_far_high_tie_N']/1000,1)} кН на переднюю стяжку. Карманы (а) отклонены решением ГК по запасам 0,90 и 0,246 из круга 1. [Исходные нагрузки и ручной расчёт](calc/T-2.2b/hand.json).

| Геометрия | Статика / ресурс | Контакт, МПа | Вклад в размер при 300 бар | Δ узла, кг | Ход, мм | Риск |
|---|---|---|---|---:|---|---|
| (а) Замкнутые карманы, данные круга 1 | 0,90 / 0,246 | 1345 / 390, перемычка | 0,002 мм, балка башмака | +{fmt(base['a']['delta_kg'])} | 36 / 12 | Длинный доступ инструмента к перемычкам |
| (б) Ярма и стяжки | См. таблицу по деталям | {fmt(p,0)} / 360, заплечик | {fmt(h,3)} / {fmt(w,3)} мм по высоте / ширине | +{fmt(mass['delta_kg'])} | 36 / 12 | Прилегание, доступ натяжителя |

## D1 и D6 · Контакт, прочность и размер

Gmsh и CalculiX 2.22, C3D4, преднатяг {fmt(min(preload),0)}…{fmt(max(preload),0)} кН на стяжку и затем 100 → 200 → 300 → 315 бар. Посадки стойка–ярмо и гайка–ярмо связаны TIE, низ корпуса и стяжек закреплён на общем уровне. Рабочие пары башмак–засовы и засовы–ярма имеют μ = 0,15. У башмака и засовов R5, у корней стойки и заплечика R15, бочкообразность 0,10 мм. Ответная грань ярма плоская в расчёте. Корпусной канал смоделирован до x = 198 мм с сохранением равнодействующей и момента профиля. Максимальная невязка сил {fmt(100*balance,4)} % от нагрузки, сила пружин {fmt(100*spring_force,3)} %, запасённая энергия пружин {fmt(100*spring_energy,3)} % энергии твёрдых тел. [Постановка и сводки](calc/T-2.2b/fea/solve.py).

| Сетка, мм / элементов | Правый заплечик, среднее по активной площади, МПа | Давление во внутренних точках, МПа | Δ высоты / ширины при 300 бар, мм |
|---|---:|---:|---:|
"""
    for case in levels:
        contact = case["contact"]["RIGHTLOW"]
        text += (
            f"| {case['max_mesh_mm']:.0f} / {case['elements']} "
            f"| {fmt(contact['mean_pressure_active_area_MPa'],0)} "
            f"| {fmt(contact['inboard_gauge_pressure_MPa'],0)} "
            f"| {fmt(geometry(case,'height'),3)} / {fmt(geometry(case,'width'),3)} |\n"
        )
    text += f"""
Для 64/36 на мелкой сетке давление в пределах рабочей полосы {fmt(p,0)} МПа при экране 360 МПа. Среднее {fmt(avg,0)} МПа также выше экрана. Под передним ярмом {fmt(pu,0)} МПа при экране 420 МПа. Сходимость по контролируемым величинам дала максимумы {fmt(100*conv['0.6']['max_relative_change'],1)} и {fmt(100*conv['0.64']['max_relative_change'],1)} % против 5 %. В таблице приведены напряжения и запасы в фиксированных внутренних точках (для FKM nσ = 1). Поля и огибающие локальных пиков со значениями nσ по градиенту сохранены в результатах. В огибающей пиков предварительные минимумы составляют {fmt(fine['parts']['FRONT_YOKE']['static_factor'])} по статике у седла переднего ярма и {fmt(fine['parts']['HOUSING']['fatigue_factor'],3)} по FKM у корпуса. Сходимость 5 % нужна для квалификации этих запасов. Экран взят как 0,60 Rp0,2 более мягкой детали. [Материалы и коэффициенты](calc/T-2.2b/sources.yaml).
"""
    if penalty:
        text += f"""
При удвоении Kn с 10 000 до 20 000 МПа/мм на крупной сетке Δ высоты меняется с {fmt(geometry(coarse,'height'),3)} до {fmt(geometry(penalty,'height'),3)} мм, среднее давление с {fmt(coarse['contact']['RIGHTLOW']['mean_pressure_active_area_MPa'],0)} до {fmt(penalty['contact']['RIGHTLOW']['mean_pressure_active_area_MPa'],0)} МПа. Ошибка по высоте остаётся выше 1 мм. Парные точки по сечению на мелкой сетке дают {fmt(h,3)} и {fmt(w,3)} мм по высоте и ширине. Δ высоты включает посадку контактов и деформацию силового пути.
"""
    text += f"""
Ручное и КЭ-номинальное напряжения изгиба составили {fmt(mck['manual_nominal_MPa'],0)}/{fmt(mck['FEA_section_nominal_bending_MPa'],0)} МПа в засове и {fmt(mcy['manual_nominal_MPa'],0)}/{fmt(mcy['FEA_section_nominal_bending_MPa'],0)} МПа в переднем ярме. Ручной засов нагружен внешним профилем с центром x = 141,3 мм. У КЭ правый заплечик передаёт равнодействующую при x = {fmt(lines['RIGHTLOW']['x_mm'],1)} мм, а опоры засова действуют при x = {fmt(lines['RIGHTBACK']['x_mm'],1)} и {fmt(lines['RIGHTFRONT']['x_mm'],1)} мм. В ярме связанный стык передаёт момент, а опоры ручной балки шарнирные. Интегрирование напряжений засова ведётся по прямоугольному ядру сечения, за границами которого находятся скруглённые зоны. [Результанты и сечения](calc/T-2.2b/results.json).

| Деталь | Статика 315 бар, МПа / запас | Ресурс 10⁷ | Контакт или смятие, МПа | Вклад в Δмассу, кг | Источник |
|---|---:|---:|---|---:|---|
"""
    props = [
        ("Корпус","HOUSING","—","housing_minus_four_bores_kg"),
        ("Башмак и заплечики","SHOE",f"{fmt(p,0)} / 360, рабочая полоса","shoe_gross_kg"),
        ("Два засова, правый определяет","RIGHT",f"{fmt(p,0)} / 360 на заплечике","two_locks_gross_kg"),
        ("Два ярма, переднее определяет","FRONT_YOKE",f"{fmt(pu,0)} / 420 на засове","two_portal_yokes_minus_bores_kg"),
    ]
    for label, name, contact, key in props:
        s = fine["parts"][name]["inboard_gauges"]
        text += (f"| {label} | {fmt(s['static_MPa'],0)} / {fmt(s['static_factor'])} "
                 f"| {fmt(s['fatigue_factor_n_sigma_1'],3)} | {contact} | +{fmt(rows[key])} | КЭ, геометрия |\n")
    text += f"""| Четыре стяжки и верхние седла | Запас сечения {fmt(stud_static)} | Резьба {fmt(stud_factor,3)}, диагностически | {fmt(upper_pad['original_top_66mm_pressure_MPa'],0)} / 420 на седле | +{fmt(rows['four_studs_nuts_seats_kg'])} | VDI и КЭ-сечения |
| Привод засова | — | — | — | +{fmt(rows['retained_mechanism_allowance_kg'])} | Резерв механизма |
| Замещаемая камера | — | — | — | −{fmt(base['replaced_D1_row_kg'])} | T-1.7c, сводная строка |

## D2–D4 · Стяжка, седло, анкер

При разделяющей силе {fmt(hand['actual_portal_far_high_tie_N']/1000,0)} кН осевой остаток прижима положителен. С учётом эксцентриситета расчёт даёт минимум {fmt(vdi['R2']['minimum_manual_edge_pressure_MPa'],0)} МПа. На переднем нагруженном стыке КЭ с TIE удерживает {fmt(joint['integrated_tension_N']/1000)} кН в растяжении на {fmt(100*joint['tensile_area_fraction'],1)} % площадки. Для стыка с реальной контактной посадкой это признак частичного раскрытия. Диагностическая усталость стяжки {fmt(stud_factor,3)} с делителем 1,35 и {fmt(stud_factor*1.35,3)} без него ({limiting_stud}, z = {fmt(float(limiting_z),0)} мм). Изгиб оценён по разности моментов между состояниями 0 и 300 бар, совместно с осевым полуразмахом. Критерий ресурса для стяжки 1,0, цель квалификации 1,1.
"""
    front_factors = [entry["joints"][1]["fatigue_factor"] for entry in vdi["R3"]["sensitivity"]]
    limit_cases = " · ".join(f"{fmt(lo,3)}…{fmt(hi,3)}" for lo,hi in front_factors)
    text += f"""
Ручные границы ресурса передней шпильки для M39 SV, M39 SG, M39 SG с Ø30,68 R≥7,8, затем M42 и M45 с аналогичной шейкой составили {limit_cases}. У последней пары требуются гарантированные свойства. Нижняя гайка 60 мм под ключ, высота 44 мм, эффективное зацепление {fmt(bolt['candidate_effective_engagement_mm'],0)} мм. Минимальная полная длина {fmt(bolt['required_total_engagement_mm'])} мм. Экраны срыва внутренних и наружных витков дают {fmt(bolt['calculated_nut_internal_strip_N']/1e6)} и {fmt(bolt['calculated_stud_external_strip_N']/1e6)} МН при верхней силе разрыва свободной резьбы {fmt(bolt['thread_tensile_upper_acceptance_N']/1e6)} МН. Верхний Rm шпильки 1350 МПа задан как условие приёмки партии. Кромки седла, усталость сбега и доступ к анкеру остаются открытыми.

Плиты под верхнее и нижнее седла 65×54×14 и 74×54×14 мм дают {fmt(upper_pad['proposed_projected_average_MPa'],0)} МПа в среднем при экранах 420 и 390 МПа. Нужна проверка изгиба плиты и распределения давления. Для Boltight T23 огибающая Ø136×147 мм, каталожное расстояние до препятствия 200 мм, выступ от седла ≥78 мм. Нужна сплошная реакционная опора моста. Компактный Superbolt CY M39 имеет Ø72×57 мм и каталожный преднатяг 570 кН. Для него требуются подтверждение допустимой рабочей силы, опоры шайбы и доступа ключа. [R0–R13 и геометрия анкера](calc/T-2.2b/results.json), [каталожные данные и VDI](calc/T-2.2b/sources.yaml).

## D5–D6 · Масса и сопряжения

Машина {fmt(base['base_T22_round_2_kg'])} − {fmt(base['replaced_D1_row_kg'])} + {fmt(mass['assembly_kg'])} = **{fmt(mass['machine_nominal_kg'])} кг**, Δ узла **+{fmt(mass['delta_kg'])} кг** при цели +40. H2 T-2.2 даёт отдельно +5…18 кг, итог {fmt(mass['machine_with_H2_kg'][0])}…{fmt(mass['machine_with_H2_kg'][1])} кг. По D-OP-10 уменьшение массы гидростанции составляет {fmt(mass['hyd_station_reduction_for_limit_kg'][0])}…{fmt(mass['hyd_station_reduction_for_limit_kg'][1])} кг для этой комплектации. Плиты и нижние гайки дают ещё +{fmt(optim['additional_top_and_bottom_spreaders']['delta_kg']+optim['four_lower_high_nuts']['delta_kg'])} кг, машина с H2 в этой комплектации {fmt(assembled_H2[0])}…{fmt(assembled_H2[1])} кг. Снижение высоты заднего ярма до 112 мм даёт {fmt(optim['rear_yoke_112_mm']['delta_kg'])} кг и множитель напряжения 1,56. Осевые отверстия Ø30 мм в засовах дают {fmt(optim['two_30_mm_lock_bores']['delta_kg'])} кг и уменьшают площадь на сдвиг на 8,9 %. Шейки дают {fmt(optim['four_waists']['delta_kg'])} кг. Совмещение всех трёх мер даже при подтверждении их ресурса оставляет ориентир +{fmt(optim['package_if_all_savings_verified_delta_kg'])} кг. [Ведомость массы и чувствительность](calc/T-2.2b/mass.json).

Длина засова {fmt(geo['lock_full_length_mm'],0)} мм при общем осевом пролёте полос {fmt(geo['required_length_to_cover_both_yoke_strips_mm'],0)} мм. Параметры сопряжения 36/12 мм, Ø125/56, 150×60 мм и плечо от баз T-1.7 77 мм. При отводе номинальный просвет 1,00 мм, сумма назначенных допусков 0,44 мм, минимум **{fmt(geo['lock_post_worst_case_mm'])} мм** при пороге 0,50 мм. Огибающая даёт номинальные 2 мм до окна по x и 2 мм до верха хода шибера по z. Интегральная проверка креплений, выходов подачи и доступа к инструменту остаётся открытой. [Компоновка и размерная цепь](design/chamber_lateral.t22b.yaml).

## Проект уточнения D-GK-07 для ГК

Оставить торцевые ярма и четыре стяжки в статусе HOLD. Для повторной квалификации нужны перераспределение давления по рабочей полосе и снижение податливости силового пути, центрированный стык с положительным давлением по площади, квалифицированные седла и нижний анкер. Предельные опорные размеры, ход и базы указаны в YAML. Облегчение гидростанции ведётся по D-OP-10.
"""
    (ROOT/"report.md").write_text(text,encoding="utf-8",newline="\n")


if __name__ == "__main__":
    render()
