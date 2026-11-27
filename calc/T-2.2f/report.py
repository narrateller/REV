"""Render the concise comparison from the numerical record."""

from pathlib import Path
import json
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0,str(HERE/"cycle"))
from compare import CandidateStudy, PUMP


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def n(value, digits=2):
    return f"{value:.{digits}f}".replace(".",",")


def signed(value):
    return f"{value:+.2f}".replace(".",",")


def price(row):
    value = row["price"]["minimum_sampled_mass_for_strength_height_kg"]
    return f"{signed(value)} кг" if value is not None else "в переборе не получена"


def station_range(row):
    lo,hi = row["required_station_reduction_kg"]
    return f"{n(lo,1)}–{n(hi,1)} кг"


def report(data, metrics, hybrid_ideal_s):
    row=metrics["candidates"]
    series=data["series"]
    records = (
        ("A_90","A · неподвижная крыша 90 мм","перенос дозы, цикл и масса рамы"),
        ("B_0","B · замкнутые карманы с четырьмя ригелями","передняя опора и площадь пятна"),
        ("C_0","C · кованое ярмо на траверсе","пролёт 540 мм и изгиб коллекторов"),
        ("D_30","D · крыша 30 мм и замок B","контакт и запас по циклу"),
    )
    lines = []
    for key,name,risk in records:
        q=row[key]
        lines.append("| {} | {} | {} | {} / {} | {} / {} | {} | {} / {} | {} / {} | {} |".format(
            name,n(q["static_factor"]),n(q["FKM"]),n(q["contact_peak_315_MPa"],0),
            n(q["contact_mean_300_MPa"],0),n(q["height_lower_bound_mm"],3),n(q["height_with_attachments_mm"],3),
            signed(q["chamber_delta_kg"]),n(q["G_CYCLE_s"],3),n(q["reference_cycle_s"],3),
            n(q["RMS_shaft_kW"],1),n(q["peak_shaft_kW"],1),risk))
    table = "\n".join(lines)
    A,B,C,D = (row[key] for key,_,_ in records)
    b=series["B_0"]["hand"]
    a_min = data["full_roof_optimistic_no_cam"]["G_CYCLE_s"]
    d_list = []
    for key in ("D_30","D_45","D_60","D_75","D_89"):
        d=row[key]
        d_list.append(f'{key[2:]} мм → {n(d["G_CYCLE_s"],3)} с, FKM {n(d["FKM"])}')
    d_series = " · ".join(d_list)
    b_need = B["price"]["required_gross_pad_y_nominal_mm"]
    c_need = C["price"]["required_gross_pad_y_nominal_mm"]
    b_park = B["price"]["parked_gross_pad_y_limit_mm"]
    c_park = C["price"]["parked_gross_pad_y_limit_mm"]
    b_width_add_mm = 4*max(0.,b_need-b_park)
    c_width_add_mm = 4*max(0.,c_need-c_park)
    b_skin_kg = b_width_add_mm*259*24*7.85e-6
    c_skin_kg = c_width_add_mm*259*24*7.85e-6
    count=sum(item["search_counts"]["configurations"] for item in series.values())
    b_front = b["load"]["front"]["force_315_N"]/1000
    lower = b["aft_lower_guide_315_N"]/1000
    b_center = b["geometry"]["station_x_mm"]["front"]
    a_struct = series["A_90"]["least_mass_if_all_structural"]
    a_mass_note = (f'Первый образец с проходом по силовой части даёт Δ узла {signed(a_struct["delta_chamber_kg"])} кг '
                   f'и облегчение до {n(a_struct["station_reduction_kg"][-1],1)} кг.' if a_struct else
                   "В сетке размеров силовая часть в сборе не прошла оба контактных экрана и ресурс одновременно.")
    mass_range = " · ".join(
        f'{label} {n(q["machine_with_H2_kg"][0],1)}–{n(q["machine_with_H2_kg"][-1],1)} кг'
        for label,q in zip(("A","B","C","D"),(A,B,C,D)))
    return f"""# T-2.2f — сравнение замков башмака подпрессовки

**STOP по ручному отбору.** В {f"{count:,}".replace(",", " ")} расчётных сочетаниях размеров четырёх схем совместного прохода по жёсткости, ресурсу, массе и циклу не получено. Действующие гейты на `design/params.t22d.yaml` дали PASS, G-PFACE 168,89 МПа, G-DOSE 321 мм, G-CYCLE {n(data["reference_T22d"]["G_CYCLE_s"],3)} с. Квалификация нового узла осталась открытой. [Гейты](gates.t22f.json) · [Расчёт](calc/T-2.2f/results.json)

## Сопоставление

Показаны варианты с наименьшим относительным дефицитом прочности, ресурса и жёсткости в доступном бюджете. Δh приведено при 300 бар как нижняя граница идеализированной балки и оценка с присоединениями. Контакт дан как пиковое / среднее давление при 315 / 300 бар. Экраны составляют 390 / 80 МПа для пары с литым основанием. Цикл дан как G-CYCLE / эталон A4VSO с переключениями T-1.6 и остаточной силой на шибере 100 кН. Пределы составляют 5,95 / 5,90 с. Мощность приведена по эталонному циклу. [Источники и допущения](calc/T-2.2f/sources.yaml)

| Кандидат | Статика | FKM | Контакт, МПа | Δh, мм | Δ узла, кг | Цикл, с | RMS / пик, кВт | Риск |
|---|---:|---:|---:|---:|---:|---:|---:|---|
{table}

Максимальный номинальный размах и допускаемый FKM при 0 → 300 бар, МПа — A {n(A["nominal_stress_range_MPa"],0)} / {n(A["FKM_allowable_stress_range_MPa"],0)}, B {n(B["nominal_stress_range_MPa"],0)} / {n(B["FKM_allowable_stress_range_MPa"],0)}, C {n(C["nominal_stress_range_MPa"],0)} / {n(C["FKM_allowable_stress_range_MPa"],0)}, D {n(D["nominal_stress_range_MPa"],0)} / {n(D["FKM_allowable_stress_range_MPa"],0)}. Для литья применено jG = 1,25. Для статики взята сила при 315 бар. Предельный контакт Schaeffler перенесён с пульсирующей шпонки как экран среднего давления. Для ресурса пары требуется испытание представительного контакта. [FKM](https://www.vdmashop.de/en/Analytical-Strength-Assessment-7th.-Ed.-2020-EN/107457) · [Schaeffler STT, с. 478](https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/catalogue_1/downloads_6/stt_de_en.pdf)

- **A.** При X = 90 мм полная длина 89,4 мм помещается под крышей. Максимум на башмаке возникает при переносе и начале сжатия и достигает {n(A["shoe_force_max_300_N"]/1000,0)} кН. Торцевую кассету можно обработать с двух торцов и установить на уступы траверсы. {a_mass_note} Даже при нулевом ходе кулачка с включённой регенерацией и ранним отпиранием G-CYCLE составляет {n(a_min,3)} с, превышение {n(a_min-5.95,3)} с. RUF и WEIMA подтверждают принцип раздельной подпрессовки и окончательной формовки в матрице. У HOLZMAG верхний плунжер остаётся стенкой при окончательном сжатии. [RUF](https://www.ruf-briquetter.com/briquetting/the-briquetting-process-explained/) · [WEIMA](https://weima.com/en/briquetting-machines/th-1500/) · [HOLZMAG](https://patents.google.com/patent/EP0246388A1/en)
- **B.** Без крыши сила D-GK-10 составляет {n(B["shoe_force_max_300_N"]/1000,0)} кН. Замкнутые щёки с поперечными ригелями и цельными перемычками передают вертикальную силу в нижний пояс камеры и далее через обработанные плечи посадки. Силу замыкают цельные детали. Сохранён ход кулачка 12 мм. В сравнении новых ригелей проверен ход до 70 мм, чтобы оценить выигрыш от увеличения пятна относительно прежнего хода 36 мм. При расчётном x = 165,2 мм передняя опора x = {n(b_center,1)} мм воспринимает до {n(b_front,0)} кН при 315 бар, задний нижний упор — до {n(lower,0)} кН противоположного знака. Фрезерование карманов и шлифование сменных ригелей требуют контроля плоскостности и доступа для смены. При неизменной ширине пятна по X нужен ригель шириной {n(b_need,0)} мм вместо предельных по парковке {n(b_park,0)} мм. Расширение одного лишь днища добавит ≥ {n(b_skin_kg,1)} кг при сохранении этого хода ригеля. Минимальная найденная прибавка по статике, FKM и Δh без учёта контакта — {price(B)}. [Аналог быстрого клинового запирания](https://patents.google.com/patent/DE3201025A1/en)
- **C.** Кованые поперечины и коллекторы замыкают нагрузку через плечи основной траверсы, минуя поперечный изгиб гладких колонн Ø70 мм из прежнего варианта. Плечи требуют обработки в сборе и контроля перекоса. Закрытая балка у передней опоры всё равно работает на заданном пролёте 540 мм. Для среднего контактного давления нужна ширина {n(c_need,0)} мм при парковочном пределе {n(c_park,0)} мм. Та же оценка добавки только к листу днища даёт ≥ {n(c_skin_kg,1)} кг, до учёта переделки траверсы. Минимальная найденная прибавка по статике, FKM и Δh без учёта контакта — {price(C)}. [Отказ T-2.2c](ops/reports/T-2.2c/GK_review.md)
- **D.** Крыша замыкает свою долю усилия в отдельном контуре через боковины и днище. Нагрузка замка идёт как в B. Собираются раздельно направляющие и сменные ригели, особенно у перехода башмак–крыша. При X = 30 мм Δ узла для прохода статики, FKM и Δh в переборе составляет {price(D)} без учёта контакта. G-CYCLE эскиза с ригелями выше лимита на {n(D["price"]["cycle_gap_task_s"],3)} с. При нулевом ходе кулачка и раннем отпирании расчёт даёт {n(hybrid_ideal_s,3)} с. По X получено {d_series}. [Размерные серии и строки массы](calc/T-2.2f/results.json)

## Границы расчёта и решение

Janssen считался по сетке K 0,35–0,60 × μ 0,20–0,30 при максимальной длине и блокировке дозы 0,853 кг. При перекосе использованы доли 64/36, для C пересчитанные по плечу 540 мм, и отдельный момент при x = 165,2 мм. В нижней границе заделаны повороты и использована полная ширина пояса. Оценка с присоединениями учитывает сдвиг, ограниченное распространение нагрузки по поясам, податливость боковин и плеч, посадку и осевое качание. В расчёте перебраны размеры эскизов с R5/R15. Натяг и контакт по кромкам, запас от разброса K и разгрузка для отпирания при ≤ 2 кН остаются открытыми. [Формулы](calc/T-2.2f/hand.py)

Перебег и установленный ход увеличены на X в отсчёте от исходного окна. Местный выход за новую плоскость шибера сохранён. Цикл использует кривые A4VSO180, ограничение подачи и возврат заряда HYDAC. При смешанных диапазонах давления в одной непрерывной фазе проекция для G-CYCLE v1 консервативно исключает подачу ГА на всю фазу. Это даёт больший штраф по времени, чем эталон с клапаном по фактическому давлению. Проверены подача ГА в быстрые ветви, повышенные уставки ГА, регенерация пары Ø90/50 и перенос команды отпирания за кромку окна. Отдельной задаче потребуются клапаны регенерации и байпас силового хода, проверка всасывания ZSF и переходных давлений, блокировка по усилию и положению ригелей. Для X ≥ 75 мм расчёт требует увеличения рабочего запаса буфера с 35 до 40 л. Повышенные уставки требуют проверки редуцирования и давления ветвей. [A4VSO RE 92050](https://rextonhydraulic.com/wp-content/uploads/2024/09/A4VSO-series-1x-and-30-Data-Sheet.pdf) · [HYDAC SB330](https://catalog.hydac.com/item/bladder-accumulators/type-sb-330-bladder-accumulator--standard/3047174) · [Sun Hydraulics](https://www.sunhydraulics.com/sites/default/files/media_library/tech_resources/us_assm_regen.pdf)

Масса считалась от 4 942,65 кг заменой строки 180,22 кг, с отдельным ростом массы четырёх колонн и цилиндров, гидравлики и H2 +5…18 кг. Требуемое облегчение станции при типовых эскизах и полном диапазоне H2 — A {station_range(A)}, B {station_range(B)}, C {station_range(C)}, D {station_range(D)}. Расчётная масса машины с H2 — {mass_range}. Проверка G-MASS требует ведомости CAD. [Ведомость](calc/T-2.2f/results.json) · [H2](ops/reports/T-2.2/GK_review.md)

**Проект записи D-GK.** Зафиксировать STOP T-2.2f по ручному отбору и оставить действующий эквивалент гейта T-2.2d. Для следующей итерации оператору определить, исследовать ли отдельную фазу переноса дозы под неподвижную матрицу или разрешить новую компоновку опор. Натурную проверку цикла запланировать на первом образце по D-OP-11. Объёмная FEA и выпуск параметров нового узла зависят от выбора исполнения. [Статус FEA](calc/T-2.2f/fea/status.json)
"""


if __name__ == "__main__":
    _, hybrid_ideal = CandidateStudy(30.,"regen_early",cam_m=0.).gate_for(PUMP)
    output=report(read(HERE/"results.json"),read(ROOT/"metrics.json"),hybrid_ideal["value"])
    (ROOT/"report.md").write_text(output,encoding="utf-8",newline="\n")
