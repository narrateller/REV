"""Render the review from the T-1.7b result bundle."""
from frame_analytic import ROOT
from frame_fea import HERE
from study import read_json


def fmt(x, digits=2):
    return "—" if x is None else f"{x:.{digits}f}".replace(".", ",")


def last(rows):
    return rows[-1] if rows else {}


def short_source(row):
    name = row["node"]
    if name=="Силовая рама":
        return "T‑1.7 OCC, новые упоры 7,4 вместо 44,0"
    if name=="Плита шибера":
        return "T‑1.7 и расчёт объёма пластины, тыла и крепежа"
    if name in {"Подача и бункер","Ограждения","Электрика"}:
        return "T‑1.6, оценочная строка"
    return "T‑1.6 mass.machine_rows"


def to_report(result):
    a, b, mass = result["A"], result["B"], result["machine_mass"]
    direct = a["integrated_direct"]
    retained = a["retained_pressure_boundary"]
    zones = last(a["integrated_direct_FEA"]).get("regions",{})
    cast,seat,entry,outer = (zones.get(k,{}) for k in
        ("cast_global","barrel_seat_R8","prefill_inner_R6","prefill_outer_R6"))
    cover = last(retained["rear_cover_FEA"]).get("regions",{}).get("cover_global",{})
    gate = last(b["integral_FEA"])
    blade = gate.get("components",{}).get("blade",{})
    split = last(b["separate_moving_shoe_FEA"]).get("components",{}).get("plate",{})
    gap_mm = max((row["max_separation_mm"] for row in gate.get("loaded_shoe_rail_gap_samples",[])),default=None)
    density = b["length_and_density_sensitivity"] or {}
    cycle = b["cycle"]
    limits = result["C_CLR_01"]
    pad = b["fall_path_T17"]
    conv = b["integral_FEA_convergence"]
    change = conv.get("max_change_fraction")
    change = None if change is None else 100*change
    x_rows = " / ".join(fmt(x["cycle_T17b_s"],3) for x in cycle.get("cycle_comparison",[])
                        if x.get("shaft_setting_kW")==36.)
    contact = gate.get("static_contact",{})
    slope = last(b["tapered_pad_sensitivity_FEA"])
    table = "\n".join(f'| {r["node"]} | {fmt(r["T17_kg"],1)} | {fmt(r["T17b_kg"],1)} | {short_source(r)} |'
                      for r in mass["machine_rows"])
    return f"""# T‑1.7b — силовой путь и резерв массы

**Рекомендация для D1 — отдельный ГЦ, приёмку отложить.** Расчётная масса машины {fmt(mass["machine_T17b_kg"],1)} кг. Номинальный остаток до 5 000 кг — {fmt(mass["margin_to_5000_kg"],1)} кг. До цели 4 850 кг нужно снять {fmt(-mass["margin_to_4850_kg"],1)} кг. Цель **FAIL**. Приёмку ограничивают усталость и контакт шибера, а также локальная проверка крышки ГЦ. Три гейта на исходных параметрах **PASS**.

## A. Задняя крышка и траверса

| Исполнение | Машина, кг | Статика 315 бар | Усталость 0–300 бар, 10⁷ | Сервис штока / поршня | Изготовление и риск |
|---|---:|---|---|---|---|
| Отдельный ГЦ и литая траверса | {fmt(mass["machine_T17b_kg"],1)} | T‑1.6 1,63. Экран с сохранением преднатяга {fmt(cover.get("fixed_preload_load_to_yield_factor"))} у M27 | Рама T‑1.7 1,029, задняя крышка {fmt(cover.get("fatigue_factor"))}. Ресурс ГЦ открыт | 4 / 8 ч, ГЦ снимается модулем | Литьё и поковки отдельно. Требуется проверка крепления ZSF |
| Литая крышка‑траверса | {fmt(mass["direct_integrated_machine_kg"],1)} | {fmt(cast.get("fixed_preload_load_to_yield_factor"))} в симметричной модели | {fmt(cast.get("fatigue_factor"))} у M27, R8 посадки {fmt(seat.get("fatigue_factor"))}, кромки порта R6 {fmt(entry.get("fatigue_factor"))} / {fmt(outer.get("fatigue_factor"))}. **FAIL** | 5 / 10 ч, ремонт посадки ≈16 ч | Оснастка сложнее, дефект мокрой посадки затрагивает раму |
| Литая траверса с кованым стаканом | {fmt(mass["integrated_cup_machine_kg"],1)} | Экран гладкой стенки / горловины {fmt(direct["cup"]["wall_nominal_vm_at_315_bar_MPa"],0)} / {fmt(direct["cup"]["neck_nominal_vm_at_315_bar_MPa"],0)} МПа. Дно открыто | Кромки, преднатяг и контакт открыты | 5 / 10 ч, замена стакана ≈12 ч | Поковка и два сопрягаемых диаметра повышают цену |

В копии T‑1.7 проём Ø360 заменён посадкой Ø352 глубиной 106 мм с R8 и осевым каналом Ø124 с R6. Добавлены глухие отверстия M27 глубиной 55 мм по монтажному интерфейсу RE 20478. На трёх сетках максимум изменения контролей {fmt(100*a["integrated_mesh_convergence"]["max_change_fraction"])} %, сходимость {a["integrated_mesh_convergence"]["status"]}. Сохранены FKM k_D = 15, n_σ по градиенту, M_σ, j = 1,5, j_G = 1,25 для литья и база VDI 2230 T‑1.7. Реакция ZSF приложена к кольцевому пятну. Статические числа крышек — множители внешней нагрузки до текучести при сохранённом преднатяге. Реальные опоры, затяжку M27 и отдельные отборы давления требуется проверить в сборке.

Удаление крышки даёт {fmt(direct["removed_forged_rear_cover_kg"],1)} кг, заполнение торца добавляет {fmt(direct["integrated_cast_head_kg"]-direct["current_cast_head_kg"],1)} кг, удлинение колонн на 275 мм — {fmt(direct["added_columns_kg"],1)} кг. Посадочная плоскость ZSF остаётся на исходной координате. Гайки колонн выступают за неё на 106 мм, модуль без ZSF и ограждений растёт с 1 564 до {fmt(direct.get("integrated_module_excluding_ZSF_and_guards_mm",direct["direct_candidate_frame_column_length_mm"]),0)} мм. C‑ENV‑01 требует полной компоновки 2 100 × 1 900 × 2 200 мм. Стакан {fmt(direct["cup"]["integral_cup_and_neck_kg"],1)} кг замещает объём литья, крепёж и уплотнение оценены в 3 кг.

При 1 293 л/мин DN124 даёт 1,784 м/с, штоковая сторона — 1,344 м/с. ZSF NG100, случай 2, даёт 1 600 л/мин при Δp ≈0,30 бар. В интеграции ZSF садится сзади, MA и два отдельных отбора давления идут через задний распределительный блок. Объём и перепад блока требуют проверки. [RE 20478, стр. 6, 14, 16–17](https://hyquip.co.uk/modules/teapotknowledgehub/uploads/re_20478_202012-6641ce6d93d31.pdf)

Сервисные часы — оценка двух слесарей с готовой оснасткой. После разгрузки, слива и отсоединения штока снять переднюю крышку. Для поршневого пакета извлечь шток с поршнем направляемой тележкой. Отдельный ГЦ поднимают талью на стенд, интегральный требует поддержки гильзы и оснастки внутри рамы. Растачивать Ø352 и привалочную плоскость в одной установке. Хонингование Ø280 выполняется на съёмной гильзе. Доводка глухой посадки в отливке ≈578 кг требует проверки базирования и перебега инструмента. UT EN 12680‑2 уровень 2, MT EN 1369 SM1, Rz 6,3 в критических зонах. Пропитка устраняет проницаемость квалифицированных микропор после НК с повторной гидропробой. [Fermat](https://www.fermatmachinery.com/machines/wft-13-15) · [Sunnen](https://www.sunnen.com/products/hta-tube-honing-machine) · [Trelleborg](https://www.trelleborg.com/en/seals/products-and-solutions/static-seals/back-up-ring) · [Henkel](https://dm.henkel-dam.com/is/content/henkel/sell-sheet-sealing-vacuum-impregnation-cast-metal-parts)

## B. Шибер, упоры и торец камеры

T‑1.2b считает плиту на верхней и нижней полосах с пролётом 72 мм. T‑1.7 оставляет 176 мм между боковыми упорами. По центрам пятен пролёт 258 мм. При 1,94 МН момент {fmt(b["base_screen"]["bend_moment_Nmm"]/1e6,1)} МН·мм даёт в 38‑мм пластине ≈{fmt(b["base_screen"]["bare_plate_bending_MPa"],0)} МПа даже при ширине 180 мм. Эквивалентное напряжение от среза ≈{fmt(b["base_screen"]["bare_plate_equivalent_shear_MPa"],0)} МПа. Среднее смятие вставки 55 мм по 2 × 82 × 180 мм составляет {fmt(pad["mean_pressure_MPa"],1)} МПа. Отдельный подвижный башмак даёт локальные запасы плиты {fmt(split.get("static_factor"))} / {fmt(split.get("fatigue_factor"))}.

Испытан путь «брикет → 38‑мм передняя часть цельного шибера → тыльное утолщение до 196 мм → два коротких упора длиной 32 мм → вставка → камера». Шибер {fmt(b["integral_geometry_and_mass"]["part_mass_kg"],1)} кг поднимается на 75 мм, до контура брикета остаётся 6 мм по высоте. В модели сохранены окно 150 × 200 мм, рабочая плоскость шибера, зона падения 190 мм и перебег. Полное перемещение в направляющих и допуски требуют компоновочной проверки.

CalculiX *CONTACT PAIR, μ = 0,15, 1,94 МН и 0–1,70 МН. На последней сетке запасы шибера {fmt(blade.get("static_factor"))} / {fmt(blade.get("fatigue_factor"))}, пик контактного давления {fmt(contact.get("pressure_max_MPa"),0)} МПа, отрыв до {fmt(gap_mm,3)} мм. Уклон пятна в пробном расчёте дал {fmt(slope.get("static_contact",{}).get("pressure_max_MPa"),0)} МПа, выше экрана смятия 420 МПа. На {len(b["integral_FEA"])} сетках сходимость {conv["status"]}, максимальное изменение {fmt(change)} %. Закрепление приложено к задним плоскостям упоров. Перенос неравномерных реакций во вставку и литой R20 открыт. При 1,70 МН осевой уход {fmt(density.get("maximum_axial_motion_mm"),3)} мм снижает оценку плотности на {fmt(density.get("constant_stroke_change_percent_at_69_mm"))} % при фиксированном ходе для 69‑мм брикета.

Обе направляющие траверсы базировать и штифтовать по обработанному модулю камеры. Плечо 77 мм от сечения конца штока до пуансона. Для T‑1.7 поперечная SRSS {fmt(limits["T17_chamber_guides_SRSS_mm"],3)} мм, при независимых базах рамы с плечом 352 мм — {fmt(limits["T17_frame_guides_SRSS_mm"],3)} мм при пределе 0,15 мм. После изменения опорных реакций C‑CLR‑01 открыт.

Подвижная группа {fmt(cycle.get("moving_mass_kg"),1)} кг. Для Ø80/45, 0,6 м/с, рамп 20 м/с² максимумы усилий открытия / закрытия {fmt(cycle.get("opening_force_with_gravity_and_inertia_N",0)/1000,1)} / {fmt(cycle.get("closing_force_with_gravity_and_inertia_N",0)/1000,1)} кН, расходы {fmt(cycle.get("opening_supply_L_min"),0)} / {fmt(cycle.get("closing_supply_L_min"),0)} л/мин. Копия T‑1.4b с массой и весом дала {x_rows} с при уставке 36 кВт (D‑GK‑02) и 90 / 160 кг/м³, Δцикл = 0,000 с. Упругая характеристика шибера в цикл не введена. Гейты на params.t14b дали 168,889 МПа, 289 мм и 5,753 с.

## Масса, кг

| Узел | T‑1.7 | T‑1.7b | Источник |
|---|---:|---:|---|
{table}
| **Итого** | **{fmt(mass["machine_T17_kg"],1)}** | **{fmt(mass["machine_T17b_kg"],1)}** | mass_budget.py |
| Неопределённость | | станция ±{fmt(mass["uncertainty_kg"]["station_plus_minus"],1)}, литьё +20…40, оценочные строки 345 | M3 ГК, ошибка оценочных строк неизвестна |

Верх станции и литья даёт {fmt(mass["uncertainty_kg"]["named_upper_excluding_estimate_line_error"],1)} кг до расхождения по оценочным статьям. Цели 4 750 кг и C‑MASS‑01 4 000 кг **FAIL**.

**Проект D‑GK‑03.** Сохранить архитектуру колонной рамы T‑1.7 с отдельным главным ГЦ T‑1.6 и базами направляющих на модуле камеры. Допуск к выпуску связать с подтверждением силового пути шибера, крепления ZSF и массы ≤5 000 кг с учётом неопределённости. Цель 4 850 кг остаётся открытой. Интегральную крышку‑траверсу завершить как сравнительное исследование.

**G‑FEA и стенд.** Замкнуть контакт шибера, упоров и вставки с реальными направляющими и преднатягом. Подтвердить сходимость, прочность и C‑CLR‑01, завершить расчёт крепления ZSF и ресурса обоих торцов и тяг ГЦ. На стенде измерить нагрузку, прогиб, пятна и отрыв, свободную выдачу, Δцикл, герметичность и время обслуживания. [Результаты](calc/T-1.7b/results.json) · [Источники](calc/T-1.7b/sources.yaml) · [Самопроверка](self_check.json)
"""


if __name__=="__main__":
    (ROOT/"report.md").write_text(to_report(read_json(HERE/"results.json")),encoding="utf-8",newline="\n")

