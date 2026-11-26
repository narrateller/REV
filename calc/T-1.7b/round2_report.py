"""Render the round-2 decision and evidence in a short report."""
from pathlib import Path

from frame_analytic import ROOT
from study import read_json
from frame_fea import HERE


SECTION_A = """## A. Сравнение задней крышки и траверсы, круг 1

| Исполнение | Машина, кг | Статика 315 бар | Усталость 0–300 бар, 10⁷ | Сервис штока / поршня | Изготовление и риск |
|---|---:|---|---|---|---|
| Отдельный ГЦ и литая траверса | 4965,5 | T‑1.6 — 1,63. Экран с сохранением преднатяга у M27 — 1,39 | Рама T‑1.7 — 1,029, задняя крышка — 1,17. Ресурс ГЦ открыт | 4 / 8 ч, ГЦ снимается модулем | Литьё и поковки отдельно. Требуется проверка крепления ZSF |
| Литая крышка‑траверса | 4906,2 | 1,95 в симметричной модели | **FAIL** — 0,56 у M27, 0,88 у R8, 6,23 / 0,74 у кромок порта R6 | 5 / 10 ч, ремонт посадки ≈16 ч | Оснастка сложнее, дефект мокрой посадки затрагивает раму |
| Литая траверса с кованым стаканом | 4909,2 | Экран гладкой стенки / горловины 149 / 137 МПа. Дно открыто | Кромки, преднатяг и контакт открыты | 5 / 10 ч, замена стакана ≈12 ч | Поковка и два сопрягаемых диаметра повышают цену |

**Проект D‑GK‑03.** Сохранить колонную раму T‑1.7 с отдельным главным ГЦ T‑1.6 и базами направляющих на модуле камеры. До выпуска подтвердить силовой путь шибера, крепление ZSF и массу ≤5 000 кг с учётом неопределённости. Интегральную крышку‑траверсу завершить как сравнительное исследование. Массы в таблице взяты из круга 1."""


def num(x, digits=2):
    return f"{x:.{digits}f}".replace(".",",")


def render(result, m0):
    b,m,r = result["B"],result["machine_mass"],result["R2_3"]
    geom,drive,cycle = b["short_span_geometry"],b["drive_opening_screen"],b["cycle_sensitivity"]
    meshes = b["short_span_FEA"]
    side = b["baseline_side_supports"]
    side_finest = side["FEA"]
    blade_1 = side_finest["components"]["blade"]
    pressure_1 = side_finest["static_contact"]["pressure_max_MPa"]
    p_side = b["side_support_drive_opening_screen"]
    delta_side_s = max(abs(x["delta_cycle_s"]) for x in side["cycle_with_extra_drag"]["cycle_comparison"])
    f2, fatigue2, pressure2 = ["открыто"]*3
    pressure_note = "Расчёт контактного образца не завершён."
    pressure_status = b["short_span_proofs"]["contact"].replace("_LOCAL","")
    mesh_note = f"{len(meshes)}/3 сеток"
    if meshes:
        best = meshes[-1]
        blade,seat,arc = (best["regions"][k] for k in ("blade","seat","seat_R20"))
        f2 = num(min(v["static_factor"] for v in best["regions"].values()))
        fatigue2 = num(min(v["fatigue_factor"] for v in best["regions"].values()))
        stat = best["loads"]["static"]
        q = stat["contact"]["pressure_peak_MPa"]
        pressure2 = num(q,0) if q>0. else "поле открыто"
        pressure_note = (
            f"CalculiX 2.22, *CONTACT PAIR с μ = 0,15, 34CrNiMo6+QT для плиты и вставки. "
            f"Плита C3D8I, вставка C3D10. Тыл закреплён. Напряжения и контактное давление приведены по упругой модели. Приложены 1,94 / 1,70 МН "
            f"с e = 10 мм по обеим осям. Сбег вдавания 0,06 мм на 3 мм по границам контакта. "
            f"На наиболее мелкой из рассчитанных сеток σeq плиты / вставки / её R20 = "
            f"{num(blade['static_mises_MPa'],0)} / {num(seat['static_mises_MPa'],0)} / "
            f"{num(arc['static_mises_MPa'],0)} МПа, усталостные запасы "
            f"{num(blade['fatigue_factor'])} / {num(seat['fatigue_factor'])} / {num(arc['fatigue_factor'])}. "
            f"Осевой уход при 1,70 МН {num(b['local_axial_displacement_fatigue_mm'],3)} мм, "
            f"уменьшение расчётной плотности в камере при фиксированном ходе "
            f"≈{num(100*b['local_in_die_density_loss_relative'])} % для длины 68,7 мм. "
            f"Отрыв на пятне до {num(stat['seat_blade_gap_max_mm'],3)} мм. Реакция за вставкой "
            f"{num(abs(stat['axial_reaction_N'])/1e6,4)} МН. "
            "FKM по T‑1.7 с k_D = 15, j = 1,5, n_σ = 1 консервативно для плиты, "
            "для вставки n_σ получен из поверхностного градиента.")
        h = " / ".join(num(row["h_contact_mm"],2) for row in meshes)
        conv = b["short_span_convergence"]
        mesh_note = f"{len(meshes)}/3, h {h} мм"
        if "max_change_fraction" in conv:
            peak_change = 100*max(conv["contact_pressure_changes_fraction"])
            pressure_note += (
                f"Пик смятия меняется до {num(peak_change,1)} % между соседними сетками. "
                "Наибольшее изменение огибающей ресурса относится к R20 вставки. ")
            mesh_note += f", Δmax {num(100*conv['max_change_fraction'],1)} %"
    zsf = r["ZSF_NG100"]
    cases = zsf["bolt_load_cases"]
    fz = [row["thread_fatigue_screen_factor"] for row in cases if row["case"]=="cycle_300"]
    shock_fz = [row["thread_fatigue_screen_factor"] for row in cases if row["case"]=="rapid_fill_stop"]
    clamp = min(row["residual_clamp_N"] for row in cases if row["case"]=="proof_315")
    bolt_margin = min(row["proof_load_margin_N"] for row in cases if row["case"]=="proof_315")
    cover_changes = r["cover_convergence"]["regions"]["cover_global"]
    cover = r["retained_rear_cover_meshes"][-1]["regions"]["cover_global"]
    converged_cover_pct = max(cover_changes["fatigue_factor"]["relative_successive_changes"])*100
    all_cover_pct = 100*r["cover_convergence"]["max_change_fraction"]
    masses = "\n".join(f"| {row['node']} | {num(row['T17_kg'],1)} | {num(row['T17b_kg'],1)} | {row['source'].split(", ",1)[0]} |"
                       for row in m["machine_rows"])

    rows = [
        "# T‑1.7b · Круг 2",
        "",
        "| Критерий | Круг 1 | Круг 2 | PASS/FAIL |",
        "|---|---|---|---|",
        f"| Статика шибера и опор ≥1,5 | {num(blade_1['static_factor'])}, локально | рамка {f2}, локально | FAIL узел B |",
        f"| Усталость шибера и опор ≥1,0, 10⁷ | {num(blade_1['fatigue_factor'])} | рамка {fatigue2}, локально | FAIL узел B |",
        f"| Контакт, ≤480 МПа для рамки, Δ <5 % | {num(pressure_1,0)} МПа, Δ 11,9 % | {pressure2} МПа, {mesh_note} | {pressure_status} давление, {b['short_span_convergence']['status']} сходимость |",
        f"| Выдача, ход 75 мм, зона 190 мм | 75 / 190 мм в эскизе | 75 / {num(geom['drop_bay_with_local_insert_mm'],0)} мм с нижней полкой | FAIL |",
        "| C‑CLR‑01 ≤0,15 мм | 0,043 мм на базе T‑1.7 | фактические реакции до торца открыты | OPEN |",
        f"| Δцикл ≤0,05 с | 0,000 с, модель массы | {num(b['max_cycle_delta_s'],3)} с при свободном ходе | PASS модели |",
        f"| Масса ≤4 850 кг | {num(m0['machine_T17b_kg'],1)} кг | {num(m['machine_T17b_carried_reference_kg'],1)} кг, база T‑1.7 | FAIL |",
        "| G‑PFACE / G‑DOSE / G‑CYCLE | PASS | 168,889 МПа / 289 мм / 5,753 с | PASS |",
        "",
        "**Стоп перед D1.** Нижняя опора рамки мешает выдаче. Боковые упоры с утолщённым шибером "
        "из круга 1 остаются сравнительной базой с недостаточным ресурсом. Для B требуется решение ГК.",
        "",
        SECTION_A,
        "",
        "## B. Силовой путь и открытие",
        "",
        "| Опирание | Масса, кг | Статика / ресурс | Открытие при μ=0,15 | Зазоры и цикл |",
        "|---|---|---|---|---|",
        f"| По периметру 176 × 74, R20, локальная модель | плита {num(geom['local_blade_envelope_mass_kg'],2)}, подвижная группа {num(cycle['moving_mass_kg'],1)}, вставка 20,95 | "
        f"статика {f2}, усталость {fatigue2}, контакт {pressure2} МПа | "
        f"{num(drive['opening_force_screen_N']/1000,1)} кН, запас {num(drive['opening_screen_factor'])} | "
        f"1 мм по высоте открытой плиты, 135 мм зоны падения, Δцикл до {num(b['max_cycle_delta_s'],3)} с при свободном ходе |",
        f"| Боковые упоры, тыл 196 мм | плита {num(side['geometry_and_mass']['part_mass_kg'],1)}, упоры 7,4, подвижная группа 74,7 | "
        f"{num(blade_1['static_mises_MPa'],0)} МПа, усталость {num(blade_1['fatigue_factor'])}, контакт {num(pressure_1,0)} МПа | "
        f"{num(p_side['opening_force_screen_N']/1000,1)} кН тем же экраном | 6 мм по высоте, зона 190 мм, Δцикл {num(delta_side_s,3)} с с добавочным трением |",
        "",
        "От базы пуансона плиту ставит окно 150 × 200 мм. Передняя грань на 205 мм, задняя на 243 мм, штатная вставка начинается на 433 мм. "
        "Прямой перенос шибера к вставке сдвигает плоскость прессования на 190 мм и требует минимум 454 мм хода против 289 мм установленных. "
        "При переносе вставки к шиберу нижняя полка занимает 243–298 мм. В худшем положении хвост брикета на 248,11 мм. "
        "Перекрытие 49,89 мм блокирует падение. Продление нижней полки до штатной вставки перекрывает всю зону. "
        "Штатный проём 164 × 62 мм проходит с остатком 0,20 мм в углу R20, перебег 59/69 мм, "
        "запасы до задней плоскости шибера и до вставки 5,11 и 5,67 мм.",
        "",
        "Две горизонтальные полосы по 6 мм даже на ширине 220 мм дали бы 735 МПа, если передать через них всю силу. "
        "Экран 480 МПа равен 0,6 Rp0,2 для сердцевины ≥800 МПа. Боковые участки включены в расчёт, "
        "их полное пятно даёт 311 МПа в среднем. На исходном боковом пролёте плита 38 мм даёт 2 049 МПа изгиба и 368 МПа эквивалентного среза при 1,94 МН. Поверхности скольжения требуют защищённой смазки и сменной ответной накладки. "
        "Индукционные дорожки 52–57 HRC достижимы по паспорту стали. Подбор пары, режим смазки и стойкость к задирам проверить с древесной пылью. "
        "[Паспорт 34CrNiMo6+QT, стр. 2](https://www.stahlwerk-augustfehn.de/wp-content/uploads/2024/01/34CrNiMo6-Technisches-Datenblatt_-1.6582-neu.pdf)",
        "",
        f"Полоса T‑1.2b при 1,70 МН даёт {num(geom['T12_strip_bending_at_1p7_MN_MPa'],0)} МПа изгиба и {num(geom['T12_strip_shear_equivalent_at_1p7_MN_MPa'],0)} МПа эквивалентного среза. "
        f"По изгибу и FKM без учёта градиента оценка толщины {num(geom['T12_strip_thickness_for_FKM_1_mm'],1)} мм, "
        f"а свободный ход хвоста при утолщении назад ограничивает толщину до {num(geom['max_blade_thickness_at_original_tail_before_intrusion_mm'],1)} мм. "
        + pressure_note + " Перенос реакций на штатную вставку и литой R20 открыт из‑за конфликта полки с выдачей. Запас литого R20 в T‑1.7 равен 1,04 при j_G = 1,25. "
        "C‑CLR‑01 сохранить по базе обеих направляющих на обработанном модуле камеры, со штифтами, плечом до пуансона 77 мм "
        "с независимым нагружением по x и y и расчётом SRSS для поперечных смещений. Унаследованные 0,043 мм относятся к нагрузкам T‑1.7.",
        "",
        f"При 5 бар в главной полости осевое усилие до 30,8 кН. Блокировка T‑1.6 требует ≤3 бар по обоим каналам.  В T‑1.2b есть размеры осевого восстановления и сопротивление выдаче "
        f"100 кН после открытия. Эту величину использовал как сценарий для неизвестной остаточной силы закрытого брикета. "
        f"С ней трение 19,6 кН, требуемое усилие {num(drive['opening_force_screen_N']/1000,1)} кН, располагаемое Ø80/45 "
        f"при 300 бар {num(drive['opening_drive_available_N']/1000,1)} кН при η=0,92 и противодавлении 5 бар. "
        f"Запас ≥2 до остаточной силы {num(drive['maximum_product_normal_N_for_factor_2']/1000,0)} кН. "
        "0,6 м/с, рампа 0,030 с и 9 мм, расходы 124/181 л/мин. На копии T‑1.4b при 36 кВт цикл 5,525 / 5,304 с "
        "для 90 / 160 кг/м³. Стенд должен измерить остаточную силу, ход и время открытия.",
        "",
        "## ZSF NG100 и задняя крышка",
        "",
        f"RE 20478 задаёт 8 × M27×180, 10.9‑flZn, 1150 Н·м ±10 %, μ = 0,09…0,14. "
        f"Экран VDI 2230 даёт {num(zsf['min_assembly_preload_N']/1000,0)}…{num(zsf['max_assembly_preload_N']/1000,0)} кН на винт. "
        f"При худшем сочетании затяжки σeq {num(zsf['assembly_vm_max_MPa'],0)} МПа против экрана 0,9Rp0,2 = 846 МПа. "
        f"При 315 бар остаточный прижим ≥{num(clamp/1000,0)} кН/винт, минимальный запас до пробной силы {num(bolt_margin/1000,0)} кН/винт. "
        f"При 0–300 бар из диапазона Φ = 0,186…0,347 и Ø138,5/188 мм получен усталостный запас {num(min(fz))}…{num(max(fz))}. "
        f"Быстрое отсечение потока 1293 л/мин в ID130 даёт идеальную добавку по Жуковскому {num(zsf['fill_shock_pressure_rise_bar'],1)} бар. "
        f"При таком одиночном импульсе запас винтов ≥{num(min(shock_fz,default=0.))} по осевому экрану. Для входа A с пределом 16 бар "
        "оценка быстрого закрытия требует измерения. Местный удар тарелки, диаметр по уплотнению, изгиб фланца, рабочая затяжка, "
        "срыв резьбы и одновременность с высоким давлением остаются на G‑FEA и стенд. "
        "[RE 20478, стр. 9, 14, 17](https://hyquip.co.uk/modules/teapotknowledgehub/uploads/re_20478_202012-6641ce6d93d31.pdf) · "
        "[VDI 2230‑1, §5.5.3](https://www.normsplash.com/Samples/DIN/131389157/VDI-2230-Part-1-2015-en-de-2.pdf)",
        "",
        f"Крышка ГЦ по трём сеткам круга 1. Глобальный усталостный запас {num(cover['fatigue_factor'])} изменился до "
        f"{num(converged_cover_pct,1)} % между последовательными сетками. Огибающая контролей меняется до {num(all_cover_pct,1)} %. "
        f"Статический множитель до текучести при сохранённом преднатяге {num(cover['fixed_preload_load_to_yield_factor'])} < 1,5. "
        "До G‑FEA требуются реальная затяжка ZSF, геометрия MA и отборов, уплотнение, податливость сопряжения и контакт.",
        "",
        "## Масса, кг",
        "",
        "| Узел | T‑1.7 | T‑1.7b, база к D1 | Источник |",
        "|---|---:|---:|---|",
        masses,
        f"| **Итого, номинал** | **{num(m['machine_T17_kg'],1)}** | **{num(m['machine_T17b_carried_reference_kg'],1)}** | T‑1.7, ведомость с открытым вопросом шибера |",
        "| Неопределённость | | станция ±82,8, припуски литья +20…40, оценочные строки 345 | M3 ГК T‑1.7 |",
        "",
        f"Номинальный остаток до 5 000 кг — {num(m['reference_margin_to_5000_kg'],1)} кг. Верхняя оценка "
        f"{num(m['named_uncertainty_kg']['reference_named_upper_without_unweighed_error'],1)} кг до ошибки строк на 345 кг. "
        f"Даже если убрать все боковые упоры и дать новой опоре нулевую массу, рамка с эскизной плитой даёт "
        f"≈{num(m['short_span_optimistic_mass_floor_kg'],1)} кг. Проектная масса исправленного узла открыта.",
        "",
        "**Вопрос к ГК.** Согласовать исследование убирающейся нижней опоры при сохранении 75/190 мм и перебега или пересмотр интерфейса выдачи. "
        "После выбора подтвердить контакт и усилия до литого R20, осевую податливость, C‑CLR‑01, ресурс скольжения и цикл. "
        "[Расчёты](calc/T-1.7b/results.json) · [Источники](calc/T-1.7b/sources.yaml) · [Самопроверка](self_check.json)",
        "",
    ]
    return "\n".join(rows)


if __name__=="__main__":
    m0 = read_json(HERE/"round1_results.json")["machine_mass"]
    report = render(read_json(HERE/"results.json"),m0)
    (ROOT/"report.md").write_text(report,encoding="utf-8",newline="\n")
