"""Produce the short Russian handover from the machine-readable calculations."""


def ru(value, digits=2):
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def series(values, digits):
    return " / ".join(ru(value,digits) for value in values)


def render(data,m):
    mass=data["mass"]
    d=data["dimensions"]
    f=data["FEA"]
    ax=data["axial_stop"][-1]
    ref=data["reference_window_mass_trial"]
    hand=m["hand_candidate_FKM"]
    proof=f["roof"][-1]["integrated_sections_315"] if f["roof"] else []
    lever_errors=[100*r["moment_error_fraction"] for r in proof]
    n_errors=[100*r["normal_error_fraction"] for r in proof]
    mass_delta=mass["delta_chamber_kg"]
    shell_ms=[r["size_mm"] for r in f["roof"]]
    win_ms=[r["size_mm"] for r in f["window"]]
    end_ms=[r["mesh_mm"] for r in f["end"]]
    end_margin=m["roof_diagnostic_local_end_FKM"]
    cheek_convergence=f["convergence"]["window_FKM"]
    cheek_converged=cheek_convergence is not None and cheek_convergence < .05
    sources="calc/T-2.2h/sources.yaml"
    lines=[
        "# T-2.2h · силовая часть схемы A",
        "",
        f"**STOP.** В диагностических моделях кольцо и щека окна не набрали FKM 1,0, "
        f"раскрытие окна составило {ru(m['window_diagnostic_opening_mm'],3)} мм при пределе 0,6 мм. "
        f"Машина с пробным узлом и H2 18 кг требует снять "
        f"**{ru(m['required_station_reduction_H2_max_kg'],1)} кг** при потолке 230 кг. "
        f"[Числа и расчётные случаи](calc/T-2.2h/results.json) · [Геометрия опыта](design/chamber_roof.t22h.yaml)",
        "",
        "## Нагрузка и конструкция",
        "",
        f"При сечении 150 × 60 мм и крыше X = 205…295 мм расчёт Janssen сохраняет огибающую "
        f"K 0,35–0,60 и μ 0,20–0,30, длину под нагрузкой до 89,4 мм и блокировку дозы 0,853 кг при ±5 %. "
        f"Башмак воспринимает {ru(m['shoe_300_bar_N']/1000,1)} / {ru(m['shoe_315_bar_N']/1000,1)} кН "
        f"при 300 / 315 бар, перенос дозы требует {ru(m['dose_transfer_N']/1000,2)} кН. "
        f"При K 0,6 / μ 0,20 крыша получает 1 282 кН, осевое трение 718 кН. "
        f"В полном K/μ переборе трение достигает {ru(m['wall_friction_315_bar_max_N']/1000,0)} кН при μ 0,30. "
        f"Разделение стадий соответствует описаниям RUF и WEIMA. "
        f"[Janssen](https://arxiv.org/abs/cond-mat/0511618) · [RUF](https://www.ruf-briquetter.com/briquetting/the-briquetting-process-explained/) "
        f"· [WEIMA](https://weima.com/en/weimapedia/) · [Источники коэффициентов]({sources})",
        "",
        f"Ручной отбор учитывает изгиб в жёстких углах, продольную силу и сдвиг. "
        f"Напряжение по толщине угла и Kt получены по Винклеру–Баху, совместность рамы замкнута "
        f"методом минимума дополнительной энергии. Поковка из двух плоских секций 45 мм с R37 "
        f"даёт FKM {ru(hand,3)} при идеальном разгружении кольца по X и массе "
        f"кольца с вкладышем {ru(m['trial_ring_and_liner_kg'],1)} кг. "
        f"При лимите {ru(m['maximum_trial_ring_and_liner_kg'],1)} кг для проверенного корпуса "
        f"лучшее FKM в переборе литья и поковок {ru(m['hand_best_in_trial_budget_FKM'],3)} при цели 1,15. "
        f"Для 800/1000 МПа требуется плоское определяющее сечение перед ТО не более 60 мм "
        f"и сертификат 3.1. [USBR EM 14, уравнения 1–4](https://www.usbr.gov/tsc/techreferences/hydraulics_lab/pubs/EM/EM14.pdf) "
        f"· [Августфен, 34CrNiMo6+QT](https://www.stahlwerk-augustfehn.de/wp-content/uploads/2024/01/34CrNiMo6-Technisches-Datenblatt_-1.6582-neu.pdf)",
        "",
        f"Сменный вкладыш 12 мм имеет ширину 150 мм, подложка доводит его до Z = ±56 мм. "
        f"У тракции на всей ширине положительная квадратичная эпюра с плечом 27,72 мм. "
        f"Для постели шириной не менее 180 мм плечо попадает в среднюю треть, но такой вариант "
        f"дал FKM {ru(data['hand_mass_constrained_search'][3]['FKM'],3)} в бюджете. Для пробной постели 150 мм "
        f"контактное раскрытие требует проверки, поскольку 27,72 > 25 мм. "
        f"Осевой путь опыта проходит через две опоры за габаритом шибера до X = 349 мм. "
        f"Верхняя половина передаёт пару {ru(ax['upper_half_couple_Nmm']/1e6,1)} кН·м при max трении. "
        f"Перенос трения с рабочей грани на постель в FEA меняет плечо ещё на 26 мм для пояса и 37 мм для боковой стенки. "
        f"Для экрана 80 МПа нужна площадь наиболее нагруженной опоры ≥ {ru(ax['required_area_per_rail_at_cyclic_screen_mm2'],0)} мм² "
        f"при имеющихся {ru(ax['rail_net_area_each_mm2'],0)} мм². "
        f"Радиальный вкладыш, стык секций и контакт с траверсой представлены упрощённо. "
        f"[Осевая посадка, SKF](https://www.skf.com/group/products/super-precision-bearings/principles/bearing-selection-process/bearing-interfaces/axial-location-of-bearing-rings)",
        "",
        "## Численная проверка",
        "",
        "| Деталь | Статика при 315 бар | FKM 0–300 бар | Контакт при 300 бар, МПа | Δh при 300 бар, мм | Δмасса к T-2.2g, кг | Источник |",
        "|---|---:|---:|---:|---:|---:|---|",
        f"| Кольцо в X = 230…270 | {ru(m['roof_diagnostic_mid_static'],3)} | {ru(m['roof_diagnostic_mid_FKM'],3)} "
        f"| — | {ru(m['roof_diagnostic_backing_opening_mm'],3)} по постелям | +{ru(m['trial_ring_and_liner_kg']-87.1112175779499,1)} | C3D10 {series(shell_ms,0)} мм |",
        f"| Торец кольца | {ru(m['roof_diagnostic_local_end_static'],3)} | {ru(end_margin,3)} "
        f"| — | — | в массе кольца | Субмодель C3D10 {series(end_ms,0)} мм |",
        f"| Осевые опоры | — | — | {ru(m['axial_rail_nominal_max_mean_at_300_bar_MPa'],1)} среднее при экране 80 | "
        f"— | +{ru(mass['chamber_rows']['axial_rails']['mass_kg'],2)} | Площадь и равновесие |",
        f"| Щека и окно | {ru(m['window_diagnostic_cheek_static'],3)} | {ru(m['window_diagnostic_cheek_FKM'],3)} | "
        f"{ru(f['window'][-1]['max_upper_land_mean_300_MPa'],1) if f['window'] else '—'} верхний упор при экране 70 | "
        f"{ru(m['window_diagnostic_opening_mm'],3)} | +{ru(mass['chamber_rows']['open_casting']['mass_kg']-89.5126718289058,1)} | C3D10 {series(win_ms,0)} мм |",
        "",
        f"Последнее изменение FKM и раскрытия кольца составляет "
        f"{ru(100*f['convergence']['roof_FKM'] if f['convergence']['roof_FKM'] is not None else None,2)} / "
        f"{ru(100*f['convergence']['roof_opening'] if f['convergence']['roof_opening'] is not None else None,2)} %. "
        f"В субмодели перемещения переданы с сечения X = 255 мм. "
        f"Последнее изменение FKM у торца составляет "
        f"{ru(100*f['convergence']['local_end_FKM'] if f['convergence']['local_end_FKM'] is not None else None,2)} %. "
        f"В трёх поперечных сечениях ошибки ручной рамы по силе составили "
        f"{series(n_errors,1)} %, по моменту {series(lever_errors,1)} %. "
        f"Сопоставление моментов не прошло допуск ±15 %. [Отчёты решателей](calc/T-2.2h/fea)",
        "",
        f"В окне последнее изменение FKM и Δh составляет "
        f"{ru(100*f['convergence']['window_FKM'] if f['convergence']['window_FKM'] is not None else None,2)} / "
        f"{ru(100*f['convergence']['window_opening'] if f['convergence']['window_opening'] is not None else None,2)} %. "
        f"Сходимость ресурса щеки {"подтверждена" if cheek_converged else "не подтверждена"}. "
        f"У обрезки X = 200…205 мм FKM по тем же сеткам составляет "
        f"{series([r['FKM'] for r in f['window_cut_edge']],3)}. Последнее изменение "
        f"{ru(100*f['convergence']['window_cut_edge_FKM'] if f['convergence']['window_cut_edge_FKM'] is not None else None,2)} %. "
        f"Изгиб и сдвиг засовов учтены через приведённые жёсткости. "
        f"При изменении жёсткости в 0,5 и 2 раза максимальное раскрытие равно "
        f"{series([r['opening_with_seating_300_mm'] for r in f['window_key_sensitivity']],3)} мм. "
        f"Знак реакции заднего упора нарушается в одной принятой схеме перекоса. "
        f"Нужна контактная модель посадок, в том числе в области кромки X ≈ 205 мм. "
        f"[Контактный экран Schaeffler, с. 478](https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/catalogue_1/downloads_6/stt_de_de.pdf)",
        "",
        "## Сопряжения, масса и решение",
        "",
        f"Сдвиг передней щеки до X = 148 мм даёт её крайнюю точку X = "
        f"{ru(d['lock_x_max_mm'],1)} мм и зазор до крыши {ru(d['lock_cut_to_roof_clearance_mm'],1)} мм. "
        f"Парковочный зазор до крыла башмака 4 мм. Осевые опоры начинаются при |Y| = 172 мм "
        f"за шибером ±130 мм, от кармана 340,2 мм остаётся {ru(d['axial_rail_to_gate_housing_pocket_half_width_mm'],1)} мм. "
        f"Кольцо разнесено с колоннами на {ru(d['roof_to_column_axial_zone_transverse_clearance_mm'],0)} мм по Y "
        f"в общей осевой зоне. Для крыльев шибера предусмотрен профиль разгрузки. "
        f"Размеры номинальные. Допуски стыков, остаточные перемещения в работе и сервисная сборка открыты. "
        f"Установленный и рабочий ходы ГЦ 396 / 371 мм. [Размеры и границы](design/chamber_roof.t22h.yaml)",
        "",
        f"Ведомость при H2 18 кг, кг. 4 942,65 − 180,22 + {ru(mass['chamber_kg'],2)} узел "
        f"(Δ {ru(mass_delta,2)}) + 10,88 колонны + 67,31 ГЦ + 12,11 быстрые цилиндры + 76,23 гидравлика "
        f"+ 18,00 H2 = {ru(m['mass_machine_H2_max_before_station_kg'],2)} кг. "
        f"Даже подстановка массы прежнего усиленного окна даёт {ru(ref['station_reduction_kg'][-1],1)} кг "
        f"облегчения с новыми засовами и осевыми опорами. Снятие металла под разгрузку крыльев "
        f"даёт максимум {ru(mass['gate_relief_mass_credit_bound_kg'],1)} кг по охватывающим объёмам. "
        f"Кольцо с вкладышем весит 126,24 кг, корпус под башмаком около 95,4 кг. "
        f"Массы исполнения, прошедшего все проверки, пока нет. "
        f"[Ведомость с источником каждой строки](calc/T-2.2h/results.json)",
        "",
        f"G-PFACE PASS при 168,89 МПа, G-DOSE PASS при 396 мм. "
        f"G-CYCLE {ru(m['gate_cycle_s'],3)} с приведён справочно, цикл по эталону T-2.6 "
        f"{ru(m['ejection_cycle_reference_s'],3)} с, неблагоприятный случай {ru(data['cycle']['adverse_s'],3)} с. "
        f"[Гейты](gates.t22h.json) · [T-2.6, разбор ГК](ops/reports/T-2.6/GK_review.md)",
        "",
        "**Проект D-GK.** Зафиксировать STOP T-2.2h по усталости кольца и щеки, раскрытию окна "
        "и расчётной массе. Передать ГК выбор между переработкой силового пути переднего опирания "
        "башмака и пересмотром бюджета станции оператором. Для дальнейшей квалификации требуются "
        "расчёт действительного осевого стыка с контактами и проверка нагрузок на сырье.",
        "",
    ]
    return "\n".join(lines)

