"""Render the Russian review from checked numerical results, in UTF-8."""
from run import HERE, ROOT, TABLE_NAMES, read_json

LABELS = {
    "integral_baseline": "Исходные места стоек, цельные кольца",
    "deep_front_stiff": "Развитые передние диафрагмы",
    "near_plane_rings": "Опорные плоскости приближены к обшивкам",
    "through_ring_light": "Сквозные кольцевые стенки",
    "closed_flanks_light": "Замкнутые боковины",
    "closed_flanks_shoe_priority": "Перенос массы из днища в башмак",
    "closed_flanks_front": "Усиление передних опор",
    "closed_flanks_stiff": "Усиленные башмак и днище",
    "closed_flanks_upper_boundary": "Самый тяжёлый расчётный вариант",
    "through_ring_upper_boundary": "Утяжелённые короба со сквозными кольцами",
}


def f(value, digits=3):
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def percent(value, digits=2):
    return "—" if value is None else f(value * 100, digits) + " %"


def contact_paragraph(contact):
    lines = []
    for tag, title in (("front", "Передняя опора"), ("rear", "Задняя опора")):
        s = contact[tag]
        if not s["meshes_complete"]:
            lines.append(f"{title}. Полных серий 0 → 315 бар нет. Ступени и причины остановки сохранены в протоколах.")
            continue
        p = s["proof_gauges"]
        gauges = s["spreads_fraction"]
        working = s["working_gauges"]
        shares = s["current_load_fraction_by_tooth"]
        meshes = " / ".join(f(row["mesh_mm"], 1) for row in s["proof_gauges_by_mesh"])
        heel_mean = (p["heel_band"] or {}).get("pressure_mean_MPa")
        lines.append(
            f"{title}. Полоса / точка зуба **{f(p['highest_tooth_band_mean_MPa'], 1)} / "
            f"{f(p['tooth_point_MPa'], 1)} МПа**, пяты **{f(heel_mean, 1)} / "
            f"{f(p['heel_point_MPa'], 1)} МПа**. Разброс полосы и точки зуба "
            f"{percent(gauges['highest_tooth_band_mean_MPa'], 1)} / {percent(gauges['tooth_point_MPa'], 1)}, "
            f"пяты {percent(gauges['heel_band_mean_MPa'], 1)} / {percent(gauges['heel_point_MPa'], 1)}. "
            f"Отклонение точки зуба от пика Герца {percent(p['tooth_point_to_hand_Hertz_difference_fraction'], 1)}. "
            f"На 300 и 315 бар максимальная ошибка целевой силы {percent(s.get('maximum_target_mismatch_300_315_fraction'), 3)}, "
            f"баланса реакций {percent(s.get('maximum_balance_fraction'), 3)}. "
            f"Полные серии на сетках {meshes} мм. На ступени 300 бар средние по полосам "
            f"{f(working['highest_tooth_band_mean_MPa'], 1)} / "
            f"{f((working['heel_band'] or {}).get('pressure_mean_MPa'), 1)} МПа. "
            f"Расчётная доля наиболее нагруженного зуба {percent(max(shares.values(), default=None), 1)}.")
    return "\n\n".join(lines)


def main():
    results = read_json(HERE / "results.json")
    m = read_json(ROOT / "metrics.json")
    g = m["global_FEA"]
    h = results["fea"]["global_meshes"][-1]
    sig = g["governing_proof_stress"]
    case = h["layout"]
    trial_mass = results["mass"]["selected_trial"]
    masses = trial_mass["chamber_rows_kg"]
    pressure_steps = " → ".join(map(str, g["solver_pressure_steps_bar"]))
    sample_meshes = " / ".join(f(size, 1) for size in g["mesh_mm"])
    trim = results["mass"]["lightest_tested_reaching_delta_height_limit"]
    candidates = {r["case"]: r for r in results["fea"]["sensitivity"] if r["status"] == "SOLVED"}
    rows = []
    for name in TABLE_NAMES:
        if name in candidates:
            r = candidates[name]
            note = " · реакция обратного знака" if r["smallest_support_300_N"] < 0. else ""
            rows.append(f"| {LABELS[name]}{note} | +{f(r['delta_chamber_kg'], 2)} | "
                        f"{f(r['delta_height_300_mm'])} | {f(r['delta_height_at_x165_edge_300_mm'])} | "
                        f"{f(r['min_FKM_at_global_points'])} |")
    table = "\n".join(rows)
    max_mass = max(c["delta_chamber_kg"] for c in candidates.values())
    minimum = (f"Наименьшее испытанное исполнение с Δh ≤ 0,6 мм имеет Δ узла +{f(trim['delta_chamber_kg'], 2)} кг."
               if trim else f"Цель по раскрытию не достигнута и при утяжелении до +{f(max_mass, 2)} кг. "
                            "Минимальная масса, обеспечивающая цель, по этой серии не определена.")
    section_text = "\n".join(
        f"| {label} | {f(row['y_cut_mm'], 0)} | {percent(row['shear_error_fraction'])} | "
        f"{percent(row['moment_error_fraction'])} |"
        for label, row in (({"shoe_inboard": "Башмак, внутри крыла", "shoe_wing": "Башмак, крыло",
                            "floor_wing": "Днище, крыло"}[key], value)
                           for key, value in (g["manual_comparison_315_bar"] or {}).items())
    )
    local_text = contact_paragraph(m["local_FEA"])
    p300, p315 = h["steps"][-2:]
    x, y = p300["peak_opening_xy_mm"]
    geo = h["stations"]
    xf, xr = geo["front"]["x_mm"], geo["rear"]["x_mm"]
    front_fraction = (x - xr) / (xf - xr)
    seat_plane_mm = [0., 0.]
    for label, part in (("front", front_fraction), ("rear", 1 - front_fraction)):
        local_fraction = (1 + y / geo[label]["y_mm"]) / 2.
        for side, normalized_y in (("left", 1 - local_fraction), ("right", local_fraction)):
            uz = p300["support_steps"][f"{label}_{side}"]["seat_mean_Uz_mm"]
            for i, value in enumerate(uz):
                seat_plane_mm[i] += part * normalized_y * value
    deformation_components_mm = [
        p300["peak_opening_shoe_Uz_mm"] - seat_plane_mm[0],
        seat_plane_mm[1] - p300["peak_opening_floor_Uz_mm"],
        seat_plane_mm[0] - seat_plane_mm[1] + .020,
    ]
    assert abs(sum(deformation_components_mm) - m["trial_delta_height_300_mm"]) < 1e-7
    cast_FKM_eq = g["global_box_FKM_at_points"] * g["governing_working_stress"]["range_MPa"]
    parts = []
    for tag in ("shoe", "floor"):
        proof_vm = max(value["equivalent_MPa"] for key, value in p315["global_control_points"].items()
                       if key.startswith(tag + "_"))
        cycle_vm = max(value["range_MPa"] for key, value in p300["global_control_points"].items()
                       if key.startswith(tag + "_"))
        parts.append((650. / proof_vm, cast_FKM_eq / cycle_vm))
    text = f"""**СТОП T-2.2e, круг 2. При Δ узла +{f(m['trial_delta_chamber_kg'], 2)} кг расчётный перекос дал Δh {f(m['trial_delta_height_300_mm'])} мм при пределе 0,600 мм. Квалификация замка не пройдена.**

## Нагрузка и конструкция

D-GK-10 сохраняет 1,034 / 1,086 МН при 300 / 315 бар, крышу 15 мм, окно 150 × 200 мм и камеру 150 × 60 мм. При 300 бар продольный центроид x = {f(m['design_centroid_x_mm'])} мм и момент {f(m['moment_at_300_about_window_center_Nm']/1000, 2)} кН·м относительно x = 105 мм. Поперечный центроид {f(m['design_centroid_y_mm'])} мм сохранён из расчётного случая 64/36 первого круга. [D-GK-10](DECISIONS.md) · [Результаты](calc/T-2.2e/results.json)

В проверенном исполнении верхний и нижний короба, кольцевые стенки и диафрагмы образуют две цельные отливки. Передние диафрагмы башмака {f(case['top_front_webs_mm'][0], 0)} / {f(case['top_front_webs_mm'][1], 0)} мм, днища {f(case['base_front_webs_mm'][0], 0)} / {f(case['base_front_webs_mm'][1], 0)} мм. Задние диафрагмы {f(case['rear_web_mm'], 0)} мм. Верхняя посадка на z = {f(h['stations']['front']['sleeve_shoulder_z_mm'], 0)} мм, пята на z = {f(h['stations']['front']['foot_bearing_z_mm'], 0)} мм. В силовом пути сварных швов нет. Передняя опора x = {f(h['stations']['front']['x_mm'], 0)} мм, |y| = {f(h['stations']['front']['y_mm'])} мм, номинальный зазор до огибающей сдвинутого шибера {f(h['stations']['front']['gate_swept_clearance_mm'])} мм. Размерная цепь, литейные галтели и корпусные интерфейсы требуют проверки перед выпуском. [Схема и размеры](design/prepress_lock.t22e.yaml) · [Огибающая шибера](design/slide_gate.t17d.yaml)

| Исполнение | Δ узла, кг | max Δh, мм | Δh на x = 165,2 у нагруженного края, мм | FKM в точках |
|---|---:|---:|---:|---:|
{table}

Таблица показывает сетку отсева. {minimum} При зафиксированном продольном перекосе Δh у нагруженного края расчётного сечения на тонкой сетке составляет {f(m['delta_height_at_x165_edge_300_mm'])} мм с учётом 0,020 мм посадки. [Протоколы FEA](calc/T-2.2e/fea/README.md)

## FEA и контактный ресурс

Объёмные C3D10, сетки {sample_meshes} мм. Кольца, диафрагмы и крыша деформируются. В осевом направлении податливость стоек и зубьев передана секущими пружинами с распределением по площади седла. Ступени CCX {pressure_steps} бар. Разброс Δh {percent(g['max_delta_height_spread_fraction'])}, эквивалентного напряжения и его размаха в управляющих точках {percent(g['governing_proof_stress_spread_fraction'])} / {percent(g['governing_FKM_stress_spread_fraction'])}. Разброс огибающей по всем точкам {percent(g['proof_stress_mesh_envelope_spread_fraction'])} превышает допуск 5 %. Наибольший разброс отдельной точки {percent(g['max_point_stress_spread_fraction'])}. Максимальная невязка по осевой силе {percent(g['maximum_reaction_imbalance_fraction'], 5)}, по моментам {percent(g['maximum_moment_imbalance_fraction'], 5)}. При x, y, z = {', '.join(f(v, 1) for v in sig['point_mm'])} мм эквивалентное напряжение {f(sig['equivalent_MPa'], 1)} МПа. Статический коэффициент в проверенных объёмных точках {f(g['global_box_static_factor_at_points'])} при пороге 1,5. FKM {f(g['global_box_FKM_at_points'])} при пороге 1,0. Предел всей сборки не квалифицирован. [Исходные допущения и FKM](calc/T-2.2e/sources.yaml)

| Номинальное сечение | y, мм | Расхождение по сдвигу | Расхождение по изгибу |
|---|---:|---:|---:|
{section_text}

Локальные модели C3D10 с трением μ = 0,15, R5 и бочкообразностью 0,10 мм. Ведомые поверхности заданы гранями элементов при поиске «узел–поверхность». Давление оценивалось по заданной полосе и в точке внутри площадки. Положение отсечённого участка отливки задано плоскостью. Это проверка пары при идеализированной границе. В трёх уточнённых сериях контакт включён после разгруженной ступени. Пиковые кромочные значения оставлены диагностическими. [Руководство CalculiX 2.22, §6.7.6 и §7.22](https://www.dhondt.de/ccx_2.22.pdf)

{local_text}

Расчётные средние по полосам и значения в точках укладываются в статические экраны 420 МПа для зубьев и 390 МПа для пяты на литом седле. Разброс между сетками превышает 5 %. Для передней опоры рабочие средние по полосам превышают консервативные пульсирующие экраны 100 / 80 МПа по аналогу шпонок. Для 10⁷ циклов требуется стенд с парой 52–57 HRC, SHD ≥ 6 мм, сборочными зазорами ≤ 4 / 2 мкм и контролем доли зуба ≤ 40 %. Смазка и загрязнение должны соответствовать рабочим. [Schaeffler STT, с. 478](https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/catalogue_1/downloads_6/stt_de_en.pdf) · [Kovanen и др.](https://doi.org/10.1016/j.triboint.2025.111020)

| Деталь | Статика | Ресурс | Контакт | Δh, мм | Вклад в Δмассу, кг | Источник |
|---|---:|---:|---|---:|---:|---|
| Башмак, кольца и диафрагмы | {f(parts[0][0])} | {f(parts[0][1])} | Седло муфты | {f(deformation_components_mm[0])} | +{f(masses['moving_crosshead_including_ring_seats'], 2)} | Объёмная модель |
| Днище, кольца и крыша | {f(parts[1][0])} | {f(parts[1][1])} | Седло пяты | {f(deformation_components_mm[1])} | +{f(masses['bottom_box_including_ring_seats_and_roof'], 2)} | Объёмная модель |
| Стойки, зубья, муфты и пяты | Открыта | Открыт | Полосы и точки | {f(deformation_components_mm[2])} | +{f(sum(v for k,v in masses.items() if k.startswith(('front_', 'rear_'))), 2)} | Локальная FEA и секущие |
| Заменяемая камера | — | — | — | — | −180,22 | T-2.2d |

Вклады Δh отнесены к плоскости, интерполированной по движениям четырёх колец. Структурные коэффициенты в таблице относятся к заданным точкам коробов.

## Принятые цикл и масса

Гейты на принятом params.t22e.yaml повторно PASS. G-PFACE 168,889 МПа, G-DOSE 321 мм, G-CYCLE **{f(m['G_CYCLE_s'])} с**. Эталон **{f(m['reference_cycle_s'])} с**. Поворот общего привода на 60° занимает 80 мс, подтверждение 10 мс. Отпирание после разгрузки, выхода дозы из окна и подтверждения остаточной силы ≤ 2 кН. [Диаграмма](calc/T-2.2e/cycle/timeline.csv) · [Гейты](gates.t22e.json)

Пересчитана строка замещающего узла. Для расчётного исполнения 4942,65 − 180,22 + {f(trial_mass['chamber_kg'], 2)} + 15,05 = **{f(trial_mass['machine_kg'], 2)} кг**. С H2 диапазон **{f(m['trial_machine_with_H2_kg'][0], 2)}–{f(m['trial_machine_with_H2_kg'][1], 2)} кг**. Строка H2 +5…18 кг и принятый бюджет облегчения станции **31,50–44,50 кг**, с ориентиром решения ≥ 40 кг, сохранены из круга 1. [Ведомости и источники строк](calc/T-2.2e/results.json)

**Проект уточнения D-GK-10.** Квалификацию замка T-2.2e остановить. Принятые нагрузка, крыша, ограничение дозы и цикл сохраняются. Выпуск КД возможен после подтверждения реального силового пути, Δh при расчётном перекосе, статического запаса и FKM всего узла, ресурса контакта и компоновочных допусков. [Самопроверка](self_check.json)
"""
    (ROOT / "report.md").write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

