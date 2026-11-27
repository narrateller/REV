"""Render the UTF-8 engineering review from the calculation results."""


def num(value, places=2):
    return f"{value:.{places}f}".replace(".", ",")


def write_report(path, data):
    variants = data["variants"]
    key, nose, clevis = (variants[name] for name in ("key_x192", "nose_x225", "clevis_x182"))
    ring = data["ring"]
    rails = ring["axial_stops"]
    a, b = ring["width_trials"]
    slotted = b["analyses"]["final_slotted"]
    collar = ring["gate_end_collar"]
    light = nose["mass"]["with_collar_and_gross_old_front_removal"]
    full = nose["mass"]["with_end_collar"]
    short = data["shortened_nose_sweep"]["best_stem_load"]
    short_drive = short["drive"]
    volume = data["mass_volume_diagnostic"][-1]["front_removed_kg"]
    baseline = data["T-2.2h_replay"]["moments_and_resultants"]["rows"]
    force_errors = " / ".join(num(x["force_error_fraction"] * 100, 1) for x in baseline)
    moment_errors = " / ".join(num(x["moment_error_over_governing_fraction"] * 100, 1) for x in baseline)

    def line(name, row, stress, source):
        reaction = row["front"]
        return (f"| {name} | {num(stress['static_factor_nominal'])} | "
                f"{num(stress['FKM_corrected'], 3)} | {num(reaction['land_mean_bearing_300_MPa'], 1)} | "
                f"{num(row['opening']['opening_300_mm'], 3)} | "
                f"{num(row['mass']['without_end_collar']['delta_rows'][0]['mass_kg'], 2)} | {source} |")

    rows = "\n".join((
        line("Засов X 192", key, key["front"]["key"], "Изгиб, сдвиг, постель"),
        line("Нос X 225", nose, nose["front"]["key"], "Зацепление в кольце"),
        line("Щека вилки X 182", clevis, clevis["front"]["cast_nominal"], "Две рабочие грани"),
        f"| Кольцо с гнездом, постель 180 | {num(slotted['static_factor'])} | "
        f"{num(slotted['FKM_corrected'], 3)} | — | — | — | Замкнутая рама |",
        f"| Торец T‑2.2h | 2,01 | 0,852 | — | — | — | Архивная субмодель |",
        f"| Бандаж | {num(collar['nominal_collar_static'])} | {num(collar['collar_nominal_FKM_cold'],3)} | "
        f"{num(collar['proof_fit_pressure_MPa'], 1)} при 315 бар | — | "
        f"+{num(collar['collar_gross_kg']+collar['rounding_fill_gross_kg'], 2)} | Ламе, круговой эквивалент |",
        f"| Осевые опоры | — | — | {num(rails['mean_300_MPa'],1)} | — | "
        f"+{num(rails['mass_delta_kg'])} | Реакция и площадь |",
    ))
    text = f"""# T‑2.2i · силовой путь схемы A

**STOP по ручному отбору.** Из трёх опор ближе всего к цели нос на входе кольца. Для окна ручная оценка даёт Δh {num(nose['opening']['opening_300_mm'],3)} мм при пределе 0,6 мм, для самого носа FKM {num(nose['front']['key']['FKM_corrected'])}. У кольца с гнездом FKM {num(a['analyses']['final_slotted']['FKM_corrected'],3)}–{num(slotted['FKM_corrected'],3)} при окончательном сжатии. Запас массы и усилие отпирания требуют подтверждения. Прочностная контактная FEA T‑2.2i не запускалась по стоп-условию карточки.

## Нагрузки и опоры

Сохранены K 0,35–0,60, μ 0,20–0,30, длина брикета под полной нагрузкой до 89,4 мм, уставка дозы 0,853 кг при ±5 %, окно 150 × 200 и канал 150 × 60 мм. Огибающая даёт 1 282 кН на крышу и 963 кН осевого трения в разных случаях. Башмак получает до 171 кН вверх на переходе к окончательному сжатию. Отдельно удержаны подпрессовка 171 кН вниз через привод и дно и перенос дозы 35,25 кН вдоль X. Продольный контрольный перекос X = 165,2 мм взят с полной силой из T‑2.2h. Поперечные отклонения ±29,96 мм для башмака и ±27,72 мм для крыши сохранены. [Janssen](https://arxiv.org/abs/cond-mat/0511618) · [T‑2.2h](ops/reports/T-2.2h/GK_review.md)

Опоры отнесены к X = 55 мм сзади и X = 192, 225 либо 182 мм спереди. По равновесию на передние опоры приходится до 172,0 / 138,6 / 185,5 кН соответственно при 315 бар. При перекосе максимальная нагрузка одной передней стороны 110,1 / 88,9 / 119,0 кН. Минимальная реакция одной задней стороны −4,0 / +0,11 / −11,0 кН. Две схемы с отрицательной реакцией требуют опирания на нижнюю пятку при смене знака. У носа знак сохраняется во всех случаях огибающей. RUF и WEIMA подтверждают последовательность подпрессовки в отдельной камере и главного сжатия в матрице. Конкретные размеры опор рассчитаны для REV. [RUF](https://www.ruf-briquetter.com/briquetting/the-briquetting-process-explained/) · [WEIMA, патент](https://patents.google.com/patent/US9144950B2/en)

| Деталь | Статика 315 бар | FKM 0–300 бар | Контакт, МПа | Δh окна, мм | Δмасса, кг | Источник |
|---|---:|---:|---:|---:|---:|---|
{rows}

Строки опор и кольца с гнездом получены ручным расчётом. Для FKM и перемещений принята поправка 1,23 по T‑2.2h. Контактные давления усреднены по рабочей площади при 300 бар, кроме указанного давления посадки. Δмасса в первых трёх строках относится к подвижной паре. Для засовов X 192 щека до X = 225,8 мм пересекает крышу на 20,8 мм. У вилки при вылете до X = 202 мм остаются 3 мм до крыши, но опорная грань даёт 135 МПа при экране 80 МПа и FKM щеки ниже 1,15. Нос входит на X = 205…245 мм, оставляя 5 мм до стыка секций. До шиберных крыльев по X остаётся 44 мм, до гладкой колонны по Y 103 мм. Допуски, предельные позы и сервисная сборка открыты. [Размеры](design/chamber_roof.t22i.yaml) · [Контактный экран Schaeffler, с. 478](https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/catalogue_1/downloads_6/stt_de_de.pdf)

При сокращении зацепления носа до 37 мм и хода задних засовов до 31 мм лучший ход носа 41,8 мм даёт 69,0 МПа на постели. При остатке 2 кН и ходе штока 12 мм за 0,08 с требуется **{num(short_drive['front_and_rear_stem_force_N_by_assumed_mu']['0.15']/1000)} кН** при μ = 0,15 и {num(short_drive['front_and_rear_stem_force_N_by_assumed_mu']['0.3']/1000)} кН при μ = 0,30 против **{num(short_drive['stem_force_limit_N']/1000)} кН** T‑2.6. Для того же движения нужен подтверждённый остаток до {num(short_drive['residual_capacity_N_by_assumed_mu']['0.15']/1000)} / {num(short_drive['residual_capacity_N_by_assumed_mu']['0.3']/1000)} кН соответственно. Влияние на эталонный цикл 5,904 с остаётся открытым. [Привод T‑2.6](calc/T-2.6/cycle/drive.py)

## Кольцо, торец и масса

При e = 27,72 мм средняя треть требует постель ≥ 166,32 мм. Проверены ширины 170 и 180 мм с рабочей гранью 150 мм. При передаче дополнительной реакции башмака ручной FKM кольца с гнездом на переходе {num(b['analyses']['transition_slotted']['FKM_corrected'])} для 180 мм. Определяет окончательное сжатие, в котором основная нагрузка приходится на кольцо. Δh под крышей 0,323 мм относится к постелям T‑2.2h. Осевые упоры 2 × (31 × 220) мм² дают {num(rails['mean_300_MPa'],1)} МПа среднего контакта при экране 80 МПа и увеличивают пару в верхней половине до {num(rails['upper_thrust_couple_315_Nmm']/1e6,1)} кН·м. Проверка края контакта и связи с траверсой остаётся открытой.

Для торца расчёт Ламе на X = 260…288 мм требует порядка {num(collar['required_bore_compression_MPa'],0)} МПа сжатия кромки и {num(collar['cold_radial_interference_mm'],3)} мм радиального натяга. При перепаде 60 К в сценарии чувствительности остаётся {num(collar['slip_sensitivity'][-1]['effective_radial_interference_mm'],3)} мм и {num(collar['slip_sensitivity'][-1]['fit_pressure_MPa'],1)} МПа. Чтобы передать всё осевое трение посадкой, в этом приближении нужен μ ≥ {num(collar['slip_sensitivity'][-1]['minimum_mu_if_holding_full_axial_reaction'],3)}, поэтому в эскизе осевую силу передают упоры. Круговой эквивалент даёт FKM кромки около 1,00 при 60 К и FKM бандажа из таблицы без краевых эффектов. Навивка или стяжки требуют приблизительно {num(collar['ideal_half_split_force_N']/1000,0)} кН на сторону в эквиваленте. Для стяжек открыты ресурс отверстий и резьбы, для навивки — опирание по контуру. Без натяга изменение формы должно дать снижение эквивалентной амплитуды около {num(100*collar['range_reduction_needed_without_preload_fraction'],1)} % при прежнем отношении среднего напряжения к амплитуде. Свойства поковки 800/1000 МПа требуют сертификата на определяющее сечение ≤ 60 мм. [Ламе и посадки](https://doi.org/10.3390/app112311428) · [FKM и среднее напряжение](https://doi.org/10.1016/j.ijfatigue.2024.108165) · [Источники](calc/T-2.2i/sources.yaml)

Ведомость с бандажом и H2 18 кг даёт {num(full['machine_before_station_kg'])} кг, или облегчение {num(full['station_reduction_kg'])} кг. Снятие всей прежней передней щеки и косынки — {num(volume)} кг по расчёту объёма Gmsh. С этим полным кредитом требуется снять **{num(light['station_reduction_kg'])} кг**. Остаётся {num(light['mass_margin_kg'])} кг под новые направляющие, сопряжения и подтверждённую передачу нагрузки к дну. Ведомость содержит исходные строки машины, гидравлику T‑2.6 +76,23 кг и каждую прибавку или вычет. [Ведомость](calc/T-2.2i/results.json)

## Проверки и проект D‑GK

G‑PFACE PASS при 168,89 МПа. G‑DOSE PASS при ходе 396 мм. G‑CYCLE 8,719 с справочно по D‑GK‑13 / D‑OP‑16. Пересчёт архивных трёх сечений T‑2.2h даёт ошибки по силе {force_errors} % и по абсолютным моментам относительно определяющих 16,18 кН·м {moment_errors} %. Для T‑2.2i сравнение с FEA, контактная сходимость, раскрытие с контактами и статика с натягом остаются открытыми. [Гейты](gates.t22i.json) · [Самопроверка](self_check.json)

**Проект D‑GK.** Зафиксировать STOP ручного отбора T‑2.2i. Нос снижает плечо нагрузки, а кольцо с его гнездом остаётся ниже порога FKM. Вынести на решение ГК и оператора продолжение с переработкой вкладыша и осевого пути кольца и проверкой остатка при отпирании либо возврат к схеме после результатов T‑2.7. Рабочая огибающая действует до измерений.
"""
    path.write_text(text, encoding="utf-8", newline="\n")
    written = path.read_text(encoding="utf-8")
    assert written == text and "?" not in written and "\ufffd" not in written

