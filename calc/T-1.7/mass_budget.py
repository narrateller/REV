"""T-1.7 weighed line items and comparison with the inherited machine budget."""
from math import fsum, sqrt
import json

from frame_analytic import (
    BASE_RHS_LENGTH_mm, COLLAR_H_mm, COLUMN_D_mm, COLUMN_HOLE_mm, COLUMN_MID_D_mm, DISCHARGE_BAY_mm, NUT_BEAR_OD_mm, NUT_H_mm,
    COLUMN_OUTER_BLEND_mm, PAD_HEIGHT_mm, PAD_WIDTH_mm, RAIL_WIDTH_mm,
    NUT_S_mm, RHO_kg_mm3, ROOT, WASHER_H_mm, annulus_mm2, column, middle_span, round_transition,
)

TARGET_FRAME_kg = 1550.
STOP_FRAME_kg = 1650.
D1_MACHINE_kg = 4750.


def mechanical_mass(v, cylinder, chamber, insert):
    c = column(v)
    density = RHO_kg_mm3
    frame = []

    def add(name, count, volume_each_mm3, source):
        frame.append({"node": name, "quantity": count, "volume_each_mm3": volume_each_mm3,
                      "mass_kg": count * volume_each_mm3 * density, "source": source})

    add("Траверса ГЦ", 1, fsum(cylinder["OCC_volumes_mm3"]),
        "Gmsh OCC, вычет Ø360 и 16×Ø39, отверстия колонн и полости исполнения")
    add("Траверса камеры", 1, fsum(chamber["OCC_volumes_mm3"]),
        "Gmsh OCC, вычет выпускного проёма, отверстий колонн и полостей исполнения")
    add(f"Распределительная вставка {PAD_WIDTH_mm:g}×{PAD_HEIGHT_mm:g}", 1, fsum(insert["OCC_volumes_mm3"]),
        "Gmsh OCC, отдельная модель 34CrNiMo6+QT с выпускным проёмом")
    add("Боковой упор открытой зоны выдачи", 2, RAIL_WIDTH_mm*PAD_HEIGHT_mm*DISCHARGE_BAY_mm,
        "Пара упоров 34CrNiMo6+QT с чистым проходом 176 мм и открытым низом")
    span = middle_span()
    add(f"Колонна Ø{COLUMN_MID_D_mm:g}/Ø100", 4,
        annulus_mm2(COLUMN_D_mm)*(c["tie_length_mm"]-span["between_collars_mm"])+span["volume_mm3"],
        f"Ø{COLUMN_MID_D_mm:g} на пролёте, переходы R18, Ø100 на концах до вычета резьбы")
    outer_transition_mm3 = round_transition(COLUMN_D_mm/2,COLUMN_OUTER_BLEND_mm)[0]
    collar_extra_mm3 = outer_transition_mm3-annulus_mm2(COLUMN_D_mm)*COLUMN_OUTER_BLEND_mm
    add(f"Цельный бурт Ø176×{COLLAR_H_mm:g}", 8, annulus_mm2(NUT_BEAR_OD_mm,COLUMN_D_mm)*COLLAR_H_mm+collar_extra_mm3,
        f"Добавочный объём бурта и перехода R{COLUMN_OUTER_BLEND_mm:g} к резьбовой шейке")
    add("Гайка M100×6 SW145×80", 8,
        (sqrt(3)/2*NUT_S_mm**2-annulus_mm2(c["thread_root_mm"]))*NUT_H_mm,
        "Каталог Dorfmüller плюс геометрическая верхняя оценка без фасок")
    add("Опорное кольцо Ø176/104×12", 8,
        annulus_mm2(NUT_BEAR_OD_mm,COLUMN_HOLE_mm)*WASHER_H_mm,
        "Сплошная шайба проектного размера")
    rhs_mm2 = 120*80 - (120-16)*(80-16)
    add(f"Продольная опора RHS 120×80×8×{BASE_RHS_LENGTH_mm:g}", 2, rhs_mm2*BASE_RHS_LENGTH_mm,
        "Проектный объём основания, без вычета радиусов")
    add("Поперечная опора RHS 120×80×8×600", 2, rhs_mm2*600.,
        "Проектный объём основания, без вычета радиусов")
    add("Опорная лапа 180×150×30", 4, 180.*150.*30.,
        "Проектный объём лап, стержневой путь усилия прессования замкнут через колонны")
    add("Ребро опоры 150×150×16", 8, 150.*150.*16./2,
        "Проектный объём треугольных рёбер")
    add("Планка-направляющая 55×40×450", 2, 55.*40.*450.,
        "Проектный объём, устанавливается по согласованным базам модуля камеры")
    add("Опора направляющей 120×75×35", 4, 120.*75.*35.,
        "Проектный объём, без вычета расточек")
    add("Крепёж и регулировочные пластины", 1, 8/density,
        "Бюджет 8 кг для крепежа опор и направляющих, проверка по КД")
    return frame


def machine_mass(frame):
    previous = json.loads((ROOT/"calc/T-1.6/results.json").read_text(encoding="utf-8"))["mass"]
    rows = []
    frame_kg = fsum(r["mass_kg"] for r in frame)
    for item in previous["machine_rows"]:
        if item["node"] == "Силовая рама":
            rows.append({"node": item["node"], "mass_kg": frame_kg,
                         "source": "T-1.7 frame_rows, Gmsh OCC и параметрическая ведомость"})
        else:
            rows.append({"node": item["node"], "mass_kg": item["round2_kg"],
                         "source": "calc/T-1.6/results.json mass.machine_rows, " + item["source"]})
    machine_kg = fsum(item["mass_kg"] for item in rows)
    nonframe_kg = machine_kg-frame_kg
    previous_frame_kg = next(r["T15_kg"] for r in previous["machine_rows"]
                             if r["node"] == "Силовая рама")
    return {"frame_rows": frame, "machine_rows": rows,
            "station_rows_reference": "calc/T-1.6/results.json mass.station_rows",
            "frame_kg": frame_kg, "machine_kg": machine_kg, "machine_without_frame_kg": nonframe_kg,
            "frame_target_kg": TARGET_FRAME_kg, "frame_stop_limit_kg": STOP_FRAME_kg,
            "machine_target_C_MASS_01_kg": 4000, "machine_limit_C_MASS_01_kg": 5000,
            "machine_D1_target_kg": D1_MACHINE_kg,
            "frame_mass_to_reach_D1_target_kg": D1_MACHINE_kg-nonframe_kg,
            "frame_T15_kg": previous_frame_kg, "frame_delta_from_T15_kg": frame_kg-previous_frame_kg,
            "frame_target_pass": frame_kg <= TARGET_FRAME_kg,
            "frame_stop_mass_pass": frame_kg <= STOP_FRAME_kg,
            "machine_C_MASS_01_target_pass": machine_kg <= 4000,
            "machine_C_MASS_01_limit_pass": machine_kg <= 5000,
            "machine_D1_target_pass": machine_kg <= D1_MACHINE_kg}
