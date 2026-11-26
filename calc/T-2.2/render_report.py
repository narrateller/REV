"""Render the concise round-2 handover from the calculation summary."""


def render_report(out):
    zsf,cap,mass = (out[key] for key in ("zsf","cover","mass"))
    dsmall,dbig = zsf["pressure_diameter_cases"]
    stud,tool = zsf["proposal"],zsf["tool"]
    strength,mesh = cap["latest_strength"],cap["convergence"]
    mat = cap["material"]
    lengths = mass["geometry"]
    bmass = mass["B"]
    ref = cap["reference"]["regions"]["cover_global"]
    mesh_rows = "\n".join(f"| {row['mesh_level']} | {row['mesh_near_mm']:.2f} | {row['elements']:,} | "
                          f"{row['regions']['global']['static_VM_MPa']:.2f} | "
                          f"{row['regions']['global']['unclamped_VM_MPa']:.2f} | "
                          f"{row['regions']['global']['fkm_factor']:.3f} |"
                          for row in cap["levels"])
    if mesh["status"]=="EVALUATED_THREE_LATEST":
        fixed = mesh["fixed_points"]
        controlling, worst_point = max(fixed.items(), key=lambda item: max(item[1]["successive_changes_fraction"]))
        gci = worst_point["GCI21_fraction"]
        if gci is None:
            gci_note = (f"Для {controlling} порядок по Ричардсону не определён, "
                        f"оценочный индекс при p=2 и Fs=3 равен {100*worst_point['indicative_2nd_order_index_fraction']:.2f} %.")
        else:
            gci_note = (f"Для {controlling} наблюдаемый порядок {worst_point['observed_order']:.2f}, "
                        f"GCI мелкой сетки {100*gci:.2f} %, отношение индексов "
                        f"{worst_point['asymptotic_ratio']:.2f}.")
        mesh_note = (f"По трём последним уровням {mesh['levels']} изменение в фиксированных точках "
                     f"{100*mesh['max_fixed_point_change_fraction']:.2f} %, по региональным пикам "
                     f"{100*mesh['max_regional_change_fraction']:.2f} %. {gci_note}")
    else:
        mesh_note = "Для проверки сходимости в трёх последовательных сетках нужны дополнительные результаты."
    balance = 100*cap["max_force_balance_residual_fraction"]
    pressure_error = 100*max(abs(row["projected_pressure_resultant_error_fraction"]) for row in cap["levels"])
    gates = ", ".join(f"{name} {row['status']}" for name,row in out["gates"].items())
    perf = out["gates"]["G-CYCLE"]["value"]
    transient = zsf["transient"]
    return f"""# T-2.2 · Круг 2 · ZSF NG100 и задняя крышка CY-MAIN

**Статус HOLD.** Для выпуска КД нужны подтверждение Rexroth, действительный профиль сбега и опоры натяжителя, квалификация поковки и сопряжений крышки. В таблице приведены расчётные запасы на 315 бар и при 10⁷ циклов 0–300 бар.

| Узел | Было | Стало | Запас статика / ресурс | Δмасса, кг | Источник |
|---|---|---|---|---:|---|
| A · ZSF NG100 | 8 × M27×180 10.9, экран сборки 955 МПа при пределе 846 МПа | 8 шпилек M27 10.9, шейка Ø23,5, R14, резьба SG, гидронатяжение | При Ø188 {dbig['static_factor_nominal']:.3f} по сечению и {dbig['static_factor_shoulder']:.3f} в галтели / {dbig['thread_1e7_factor']:.3f} по виткам, {dbig['shoulder_FKM_factor']:.3f} в галтели | {mass['A']['delta_A_kg']:+.2f} | [VDI и FKM](calc/T-2.2/vdi2230.py), [RE 20478, стр. 9, 14, 17](https://boschrexroth-russia.ru/image/catalog/docs/RE20478_2020-12.pdf) |
| B · Задняя крышка | Ø520 × 132, 42CrMo4+QT. Фиксированный преднатяг {ref['fixed_preload_load_to_yield_factor']:.2f}, FKM {ref['fatigue_factor']:.2f} | recessed_taps Ø520 × 144, поковка 34CrNiMo6+QT | {strength['static_yield_factor']:.3f} по пику с преднатягом, {strength['fixed_preload_load_to_yield_factor']:.3f} при фиксированном преднатяге, {strength['static_yield_factor_without_preload']:.3f} без преднатяга / {strength['fkm_factor']:.3f} | {bmass['delta_B_kg']:+.2f} | [FEA](calc/T-2.2/cap_fea), [сводка](calc/T-2.2/results.json) |
| C · Камера | Круг 1, 1,22 / 1,285 МН при 300 / 315 бар, статика 0,28–0,46, сходимость 33 % | Передано в T-2.2b по D-GK-07 | HOLD_G_FEA | — | [Архив круга 1](calc/T-2.2/lateral_fea) |

## A · Шпильки ZSF

Глубина глухого отверстия 55 мм, вход заглублён на 10 мм. Ввинчивание 42 ± 0,5 мм даёт минимум 25,5 мм эффективного зацепления с учётом 2P. Запас срыва к разрыву свободной резьбы {zsf['engagement'][0]['strip_to_full_thread_rupture_factor']:.3f} при табличном Rm 800 и {zsf['engagement'][1]['strip_to_full_thread_rupture_factor']:.3f} при заданном Rm 850. Шейка Ø23,5, галтель R≥14 мм, обе резьбы накатать после ТО, дно впадины R≥0,375 мм, Rz≤3,2 на переходах. Для сбега FKM при условном Kt=1,50 даёт {dbig['runout_FKM_factor_conditional']:.3f}. При этом экран статики сбега {dbig['runout_static_factor_at_assumed_Kt']:.3f}. Порог по локальной статике Kt≤{dbig['runout_Kt_limit_static']:.3f}. Нужен профиль изготовителя с проверкой сбега. [VDI 2230, стр. 92–100](https://www.normsplash.com/Samples/DIN/131389157/VDI-2230-Part-1-2015-en-de-2.pdf) · [Концентрация в галтели, табл. 3](https://nao3886noda.sakura.ne.jp/thesis/pdf/773.pdf)

| Диаметр, мм | Максимум номинального VM, МПа | Запас к Rp0,2 / галтель | SG после проектного делителя 1,35 / исходный | Прижим мин., кН на шпильку | pG фланца требуется, МПа |
|---:|---:|---:|---:|---:|---:|
| 138,5 | {max(r['service_VM_MPa'] for r in dsmall['rows']):.1f} | {dsmall['static_factor_nominal']:.3f} / {dsmall['static_factor_shoulder']:.3f} | {dsmall['thread_1e7_factor']:.3f} / {dsmall['thread_SG_raw_factor']:.3f} | {dsmall['residual_clamp_min_N']/1000:.1f} | {dsmall['pG_valve_required_MPa']:.1f} |
| 188 | {max(r['service_VM_MPa'] for r in dbig['rows']):.1f} | {dbig['static_factor_nominal']:.3f} / {dbig['static_factor_shoulder']:.3f} | {dbig['thread_1e7_factor']:.3f} / {dbig['thread_SG_raw_factor']:.3f} | {dbig['residual_clamp_min_N']/1000:.1f} | {dbig['pG_valve_required_MPa']:.1f} |

При l/d=5 формула Boltight даёт 1,21. Принято 1,25 до измерения на пакете. Натяжение {stud['tension_target_N']/1000:.2f} кН с диапазоном {stud['tension_qualification_range_N'][0]/1000:.2f}–{stud['tension_qualification_range_N'][1]/1000:.2f} кН. Остаточный преднатяг 157,5–172,5 кН, αA={stud['alpha_A']:.3f}. При натяжении VM {stud['stud_VM_at_tension_MPa']:.1f} МПа, в гладкой галтели {stud['shoulder_stress_at_tension_MPa']:.1f} МПа при сборочном пределе 846 МПа. Шайба Ø50/28 × 4 даёт до {dbig['contact_under_nut_max_MPa']:.1f} МПа под гайкой. Прижим указан после осадки 0,04 мм, доступный резерв должен покрывать прижим уплотнения и температурные потери. Изгиб клапана и шпилек требует проверки на многовинтовом стыке. [Каталог Boltight, §2.4, §4.1, §4.4](https://www.nord-lock.com/globalassets/mediavalet/web-assets/downloads/tensioning-pdfs/boltight---tsr-user-manual---hs-operations.pdf) · [Данные для смятия](calc/T-2.2/sources.yaml)

Шаг {tool['fastener_chord_mm']:.2f} мм, инструмент TSR+1 M27 Ø87 мм, соседний зазор {tool['two_adjacent_tools_nominal_gap_mm']:.2f} мм. Выступ {stud['stand_proud_above_nut_mm']:.0f} мм над гайкой и {tool['stud_above_bearing_seat_mm']:.1f} мм над опорой. Для Ø87 при зазоре 2 мм корпус в том же осевом сечении должен укладываться в радиус {tool['central_clear_radius_at_full_tool_OD_with_2mm_gap_mm']:.1f} мм. При совпадении с каталожным Ø212 пересечение {abs(tool['nominal_gap_against_body_D2_if_same_height_mm']):.1f} мм. Действительный зазор, площадь опоры моста натяжителя, допускаемое pG фланца и замена R913059494 требуют подтверждения Rexroth. [Размерная схема](design/main_cylinder_rear.t22.yaml)

Пассивное открытие при ∆p≈0,12 бар даёт около 88 Н на тарелке, импульс установившегося потока около 30 Н. MD снимает B-давление до возврата через MF. Экран мгновенной остановки потока даёт {transient['fill_stop_gauge_bar']:.2f} бар на A при каталожном пределе 16 бар. Отдельная осевая реакция {transient['separate_axial_reaction_screen_N']/1000:.1f} кН учтена как возможное отрицательное приращение в нижней точке цикла шпилек. В схеме RTF рассчитан на 3 бар при номинальном расходе. Отклик RTF и пик давления A/B проверяются осциллограммой или расчётом перехода с реальным закрытием. [Гидросхема T-1.6](design/hydraulics/T-1.6_circuit.yaml) · [Исходные данные](calc/T-2.2/sources.yaml)

## B · Крышка, сходимость и монтаж

Тепловая оценка эквивалентного круга {mat['equivalent_diameter_screen_mm']:.1f} мм. Приложение A.2.2 требует согласовать определяющее сечение для диска с кузницей. Для диапазона 160–250 мм Rp0,2≥600 МПа, Rm 800–950 МПа. Закупка требует 650/850 МПа на тангенциальной пробе T/4, глубина 36 мм. В опыте Lucefin с кованым кругом Ø520 получено 828/930 МПа на глубине 25 мм и 750/900 МПа на 1/3 радиуса. Для диска применимость подтверждается пробой после ТО. При Rp=600 / 650 МПа запасы по пику с преднатягом {strength['static_yield_factor_Rp600']:.3f} / {strength['static_yield_factor']:.3f}, на увеличение рабочей нагрузки при фиксированном преднатяге {strength['fixed_preload_load_to_yield_factor_Rp600']:.3f} / {strength['fixed_preload_load_to_yield_factor']:.3f}. [EN 10083-1, прил. A](https://qilusteelgroup.com/wp-content/uploads/2024/02/DIN-EN10083-1.pdf) · [EN 10083-3, табл. 8](https://asremavad.com/wp-content/uploads/2019/06/DIN-EN-10083-3-2007.pdf) · [Lucefin](https://www.lucefin.com/oaleekso/files_mf/152353526334CrNiMo6.pdf)

| Уровень | h лок., мм | C3D10 | VM с преднатягом, МПа | VM без преднатяга, МПа | FKM |
|---:|---:|---:|---:|---:|---:|
{mesh_rows}

{mesh_note} Невязка реакций ≤{balance:.5f} % от нагрузки 315 бар. Исходная квадратура давления отличается до {pressure_error:.3f} %, результирующая приведена к аналитической проекции Ø280. Упругий сектор 22,5° учитывает давление, ZSF Ø188 при верхней оценке доли 0,31, предварительное обжатие и жёсткости M36/гильзы до передней траверсы. Верхний преднатяг ZSF модели 198 кН на шпильку. FKM использует Rm=850 МПа, jG=1,0, jD=1,5, kD=15, среднее напряжение и градиент. Заглубление резьбы 10 мм, восемь MA Ø44, эквивалентное сечение Ø{cap['MA_equivalent_ID_mm']:.2f} и перемычка MA–M36 {cap['MA_nominal_ligament_at_M36_mm']:.2f} мм. Остались коллектор MA, каналы PTA/PTB, контактные зоны и допуски. [Узловые результаты и GCI](calc/T-2.2/results.json) · [Методика GCI](https://www.asme.org/wwwasmeorg/media/resourcefiles/shop/journals/jfenumaccuracy.pdf)

Толщина добавлена назад от передней опоры. Корпус ГЦ {lengths['cylinder_body_before_after_mm'][0]:.0f} → {lengths['cylinder_body_before_after_mm'][1]:.0f} мм, 16 стяжек M36 +12 мм ({bmass['delta_M36_cylinder_ties_kg']:+.2f} кг), крышка {bmass['delta_cover_kg']:+.2f} кг. Длина силовой рамы {lengths['structural_frame_axial_before_after_mm'][0]:.0f} мм, гладкий пролёт четырёх колонн {lengths['four_column_smooth_span_before_after_mm'][0]:.0f} мм, Δмасса колонн 0. Модуль без ZSF/ограждения {lengths['structural_module_axial_excluding_ZSF_and_guards_before_after_mm'][0]:.0f} → {lengths['structural_module_axial_excluding_ZSF_and_guards_before_after_mm'][1]:.0f} мм. Габарит гайки и инструмента рамы в прежнем экране имеет нижнюю оценку {lengths['minimum_nut_clearance_lower_bound_mm']:.1f} и {lengths['minimum_column_tool_clearance_lower_bound_mm']:.1f} мм соответственно. Эскизная длина шпильки добавляет местный задний выступ {lengths['additional_projection_of_stud_beyond_catalogue_H1_mm']:.1f} мм относительно H1. Ø280/200 и ходы 281/306 мм сохранены. [Размеры T-1.7d](design/frame.t17d.yaml) · [Привязки](design/main_cylinder_rear.t22.yaml)

Масса машины {mass['baseline_T21_kg']:.2f} {mass['A']['delta_A_kg']:+.2f} {mass['B']['delta_B_kg']:+.2f} = **{mass['nominal_AB_kg']:.2f} кг**. До лимита 5000 кг остаётся **{mass['nominal_reserve_for_T22b_kg']:.2f} кг** для T-2.2b и уточнения коллектора MA, опор и масла. {gates}, расчётное время {perf:.3f} с. [Гейты](gates.t22.json) · [Самопроверка](self_check.json)
"""
