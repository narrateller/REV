"""Write the short review in UTF-8 from the deterministic T-2.2g package."""

from loads import ROOT
from run import read


def n(value, digits=2):
    return f"{value:.{digits}f}".replace(".",",")


def main():
    data=read(ROOT/"calc/T-2.2g/results.json")
    m=read(ROOT/"metrics.json")
    f=data["fea"]
    mass=data["mass_close_to_strength_limit"]
    cast=data["cast_best"]
    reinforced=data["mass_with_window_reinforcement"]
    rows=f["ring"]["ring_three_meshes"]
    long=rows[-1]["cases"]["long_skew"]
    con=f["ring_convergence"]
    seat=f["cassette"]
    braced=f["ring"]["ring_screen_saddles"][-1]["cases"]["long_skew"]
    front=f["window"]["window_reinforced"][-1]["regional_check"]["front_reaction"]
    lock=data["hand"]["lock"]["stations"]["front"]["contacts"]
    cam=data["hand"]["lock"]["cam_screen"]
    cas=f"{n(m['cassette_peak_315_MPa'][0],1)} / {n(m['cassette_peak_315_MPa'][1],1)}"
    sdf = "–".join(n(x,1) for x in mass["station_reduction_kg"])
    sdf_win = "–".join(n(x,1) for x in reinforced["station_reduction_kg"])
    forces=" / ".join(n(float(m[k])/1000,1) for k in ("prepress_300_force_N","prepress_315_force_N"))
    mass_range="–".join(n(x,1) for x in mass["machine_with_H2_kg"])
    mesh = " / ".join(n(r["mesh_mm"],0) for r in rows)
    fkms = " / ".join(n(r["cases"]["long_skew"]["fatigue"]["FKM"],3) for r in rows)
    windows = " / ".join(n(m[key],3) for key in ("open_window_FEA_opening_300_mm","open_window_reinforced_FEA_opening_300_mm"))
    saddle_arms_kg=8*70**2*54*7.85e-6
    key_contact=f["key_contact"]
    key_note="Локальный контакт замка остаётся открытым."
    if key_contact and key_contact.get("rows"):
        peak_row=key_contact["rows"][-1]
        ceiling=key_contact["target_forces_N"][-1]
        drift=100.*abs(peak_row["shoe_force_N"]-ceiling)/ceiling
        key_note=f"На последней ступени калибровки засова ошибка усилия {n(drift,1)} %."
    if f["key_proof"]:
        local = f["key_proof"]["rows"][-1]
        local_force = n(local["shoe_force_N"]/1000,1)
        max_peak = n(max(v["peak_MPa"] for v in local["contact"].values()),1)
        key_note += f" Отдельная проба при {local_force} кН дала пиковое давление {max_peak} МПа."
    completed_cassette_levels=len(f["cassette_meshes"])
    c_convergence=max(x for x in f["cassette_peak_relative_changes"].values() if x is not None)
    cassette_mesh_note=f"На {completed_cassette_levels} сетках расхождение пиков до {n(c_convergence*100,1)} %."
    if len(f["cassette_meshes"])<3:
        cassette_mesh_note += " На третьей сетке CCX прервал расчёт."
    gate_pressure=n(seat["loads"]["fatigue"]["blade_seat"]["face_strip_means"]["lower"]["mean_MPa"],1)
    block=(
f"""# T-2.2g · силовая часть схемы A

**STOP по FEA.** В рассмотренных исполнениях крыша и опора башмака не прошли силовую квалификацию в пределах +60 кг. У крыши R30 на самой мелкой сетке статика **{n(m['roof_FEA_static_factor'])} < 1,50**, FKM **{n(m['roof_FEA_FKM'],3)} < 1,0**. Раскрытие под крышей **{n(m['roof_FEA_opening_300_mm'],3)} мм**, под башмаком **{windows} мм** для исходного и усиленного корпусов соответственно. Предел 0,60 мм. [Результаты](calc/T-2.2g/results.json) · [Эскизные параметры](design/chamber_roof.t22g.yaml)

## Нагрузка и отбор

Под крышей длиной 90 мм помещается 89,4 мм под нагрузкой. Janssen посчитан при K = 0,35–0,60 и μ = 0,20–0,30 с блокировкой уставки дозы 0,853 кг при ±5 %. На башмак приходится {forces} кН при 300 / 315 бар. Перенос требует {n(m['dose_transfer_force_N']/1000)} кН, из них 23,25 кН трения и 12,0 кН на входе. Осевой центроид смещается по мере переноса. Для крыши добавлен поперечный эксцентриситет 27,72 мм. Максимум давления в начале зоны {n(m['roof_pressure_max_MPa'],1)} МПа при расчётном пределе ГЦ T-2.6. Реакция короткого брикета на шибере до {n(m['gate_thrust_315_N']/1000,1)} кН. [Модель нагрузок](calc/T-2.2g/loads.py) · [Janssen](https://arxiv.org/abs/cond-mat/0511618)

Для кованого кольца с поясами 120 мм и боковиной 56 мм ручной отбор дал статику {n(m['hand_static_factor'])}, FKM {n(m['hand_FKM'],3)}, раскрытие {n(m['hand_opening_300_mm'],3)} мм и Δ массы +{n(m['hand_delta_node_kg'])} кг. В ручном переборе литья со стенкой от 64 мм лучший FKM {n(cast['FKM'],3)} при jG = 1,25, боковине {n(cast['roof_wall_mm'],0)} мм, поясах {n(cast['roof_band_mm'],0)} мм и Δ массы +{n(cast['delta_chamber_kg'],1)} кг. Для поковки jG = 1,0, свойства 700/900 МПа относятся к плоскому определяющему сечению до 100 мм. Замок состоит из двух пар поперечных засовов с разнесёнными полосами против опрокидывания и нижним упором задней станции. Кулачок 12 мм перемещает засовы на 54 мм. Оценка усилия штока {n(cam['stem_force_screen_N']/1000,1)} кН при остатке 2 кН укладывается в {n(cam['prior_T26_stem_force_N']/1000,1)} кН модели T-2.6. [Допущения и материалы](calc/T-2.2g/sources.yaml) · [Каталог поковок](https://www.stahlwerk-augustfehn.de/wp-content/uploads/2024/01/34CrNiMo6-Technisches-Datenblatt_-1.6582-neu.pdf)

| Деталь | Статика | FKM | Контакт, МПа | Δh при 300 бар, мм | Масса | Источник результата |
|---|---:|---:|---:|---:|---:|---|
| Крыша, боковины, днище R30 | {n(m['roof_FEA_static_factor'])} | {n(m['roof_FEA_FKM'],3)} | — | {n(m['roof_FEA_opening_300_mm'],3)} | {n(rows[-1]['ring_mass_kg'],1)} кг | C3D10, {mesh} мм |
| Усиленный литой корпус под башмаком | {n(front['cast_cheek']['static_factor'])} | {n(front['cast_cheek']['FKM'],3)} | — | {n(m['open_window_reinforced_FEA_opening_300_mm'],3)} в сборке | +{n((reinforced['chamber_kg']-mass['chamber_kg']),1)} кг к исходному корпусу | C3D10 окна, 18 мм |
| Башмак и передний засов | {n(front['shoe']['static_factor'])} башмак | {n(front['shoe']['FKM'],3)} башмак | {n(lock['upper_forged_land']['mean_300_MPa'],1)} среднее на верхнем упоре | входит в раскрытие окна | засовы и вкладыши в ведомости | C3D10 башмака, засов по балке |
| Шибер / кассета / торец | {n(seat['strength']['blade']['static_factor'])} по плите | {n(seat['strength']['blade']['FKM'],3)} по плите | {cas} пики при экранах 480 / 390 | — | перенос, Δ 0 кг | контакт C3D10 T-1.7d при новом усилии |

## Проверки и пределы модели

- Крыша R30, C3D10 на трёх сетках и ступени 0 → 100 → 200 → 300 → 315 бар. FKM по сеткам {fkms}. Баланс ≤ {n(100*long['maximum_balance_fraction'],6)} %. Изменение раскрытия {n(100*con['opening_relative_change'],2)} %, напряжения в управляющей фиксированной точке {n(100*con['invariant_gauge_relative_change'],2)} % при пределе 5 %. Мембранная проверка по X = 228 / 250 / 270 мм расходится с ручной на {(' / '.join(n(100*v['error_relative'],1) for v in long['membrane_sections_315']))} %. Расчёт показывает перераспределение усилия вдоль короткой крыши. Пружины передают податливость колонн и результат осевого трения. Общая контактная модель крыши, её плеч и траверсы остаётся открытой. [Сетки и контрольные точки](calc/T-2.2g/fea/ring_three_meshes.json)
- Варианты с R1, R15, R22, вкладышами и пятью слоями по 18 мм не дали суммарного прохода. Добавленные поперечные опоры довели статику до {n(braced['min_static_factor'])}, FKM до {n(braced['fatigue']['FKM'],3)} в пробе. Восемь стержней 70 × 70 × 54 мм из этой пробы добавляют {n(saddle_arms_kg,1)} кг без концов. В окне податливость щёк, засовов и пола подняла Δh выше ручной оценки. {key_note} Для закалённой пары аналог Schaeffler даёт 100 МПа, для незакалённой нижняя граница 70 МПа. [Серия FEA](calc/T-2.2g/fea) · [FKM, 7-е издание](https://www.vdmashop.de/en/Analytical-Strength-Assessment-7th.-Ed.-2020-EN/107457) · [Schaeffler, с. 478](https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/catalogue_1/downloads_6/stt_de_de.pdf)
- Полосы кассеты заданы по четырём областям пятна. При 300 бар среднее на нижней полосе плита–кассета {gate_pressure} МПа. Зона контакта и жёсткость торца проверены на исходной геометрии T-1.7d. Экраны 480 / 390 МПа взяты по D-GK-05. {cassette_mesh_note} Упрощённая оценка повторного контакта по шпонке не заменяет испытание пары на ресурс. [Контакт кассеты]({seat['file']})
- Шибер смещён до X = 295 мм, толщина 54 мм и ход 100 мм. Рёбра заходят до X = 289 мм. Разгрузка по их профилю даёт номинально ≥ 0,65 мм осевого зазора. Ход ГЦ установленный / рабочий 396 / 371 мм, перебег 166–176 мм. Для эскиза замка парковочный зазор до башмака 4 мм. Усиленная крыша шириной 358 мм пересекает переднюю щёку в эскизе. Для стыка требуется собственное сопряжение. RUF и WEIMA подтверждают разделение стадий подпрессовки и сжатия в матрице. [Интерфейсы](design/chamber_roof.t22g.yaml) · [RUF](https://www.ruf-briquetter.com/briquetting/the-briquetting-process-explained/) · [WEIMA](https://weima.com/us/briquetting-machines/th-1500/)

## Масса и решение

Расчёт для усиленной крыши и исходного окна, кг. База 4 942,65 − камера 180,22 + узел {n(mass['chamber_kg'])} + четыре колонны 10,88 + ГЦ 67,31 + быстрые цилиндры 12,11 + перенос шибера и кассеты 0,00 + гидравлика T-2.6 76,23 + H2 5–18. Итого **{mass_range} кг**. До 5 000 кг нужно снять **{sdf} кг** со станции против ≈145 кг. Усиление окна даёт требуемое снятие {sdf_win} кг, а Δ узла +{n(reinforced['delta_chamber_kg'],1)} кг. Порядок оценки — 1,7 массы BP500 при исходной базе REV 4 942,65 кг. [Построчная ведомость](calc/T-2.2g/results.json)

G-PFACE и G-DOSE прошли при 168,89 МПа и ходе 396 мм. Цикл D-OP-16 по эталону T-2.6 номинально {n(m['reference_nominal_cycle_s'],3)} с, неблагоприятно {n(m['reference_adverse_cycle_s'],3)} с. Проекция G-CYCLE 8,719 с приведена справочно. [Отчёт гейтов](gates.t22g.json)

**Проект D-GK.** Зафиксировать STOP T-2.2g по ресурсу крыши и раскрытию окна. Сохранить принятые размеры технологического контура и гидравлику. Для продолжения требуется решение ГК и оператора по переработке силового пути крыши и передней опоры башмака в действующем бюджете массы.
""")
    path=ROOT/"report.md"
    path.write_text(block,encoding="utf-8",newline="\n")
    retrieved=path.read_text(encoding="utf-8")
    assert retrieved==block and "?" not in retrieved and "\ufffd" not in retrieved


if __name__=="__main__":
    main()

