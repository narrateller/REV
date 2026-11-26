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
def revision_machine_mass(base, gate, alternate):
    old_rows = base["mass"]["machine_rows"]
    reference_delta = gate["moving_mass_delta_kg"]
    rail_delta = gate["rail_pair_mass_kg"]-next(
        row["mass_kg"] for row in base["mass"]["frame_rows"] if row["node"].startswith("Боковой упор"))
    rows = []
    for row in old_rows:
        name,old_mass_kg = row["node"],row["mass_kg"]
        delta = reference_delta if name=="Плита шибера" else rail_delta if name=="Силовая рама" else 0.
        source = row["source"]
        if delta:
            source += " | T-1.7b gate_integral.mass, comparison against T-1.7 rows"
        rows.append({"node":name,"T17_kg":old_mass_kg,"T17b_kg":old_mass_kg+delta,"source":source})
    total_kg = fsum(row["T17b_kg"] for row in rows)
    station_kg = rows[0]["T17b_kg"]
    alternative_kg = alternate["nominal_machine_mass_delta_kg"]
    return {"machine_rows":rows,"machine_T17_kg":base["mass"]["machine_kg"],"machine_T17b_kg":total_kg,
            "direct_integrated_machine_kg":total_kg+alternative_kg if alternative_kg is not None else None,
            "integrated_cup_machine_kg":total_kg+alternative_kg+alternate["cup"]["net_hardware_allowance_kg"]
            if alternative_kg is not None else None,
            "uncertainty_kg":{"station_plus_minus":.05*station_kg,"casting_plus_range":[20.,40.],
                              "estimate_line_items_unweighed":345.,"estimate_items_error_bound":None,
                              "named_upper_excluding_estimate_line_error":total_kg+.05*station_kg+40.},
            "margin_to_5000_kg":5000.-total_kg,"margin_to_4850_kg":4850.-total_kg,
            "margin_to_4750_kg":4750.-total_kg,"status_limit_5000":"PASS" if total_kg<=5000 else "FAIL",
            "status_target_4850":"PASS" if total_kg<=4850 else "FAIL",
            "status_C_MASS_01_target_4000":"PASS" if total_kg<=4000 else "FAIL"}



def blocked_round2_budget(base, geometry):
    """Carry the T-1.7 rows into D1 while the physical gate path is unresolved."""
    rows = [{"node":r["node"],"T17_kg":r["mass_kg"],"T17b_kg":r["mass_kg"],"source":r["source"]}
            for r in base["mass"]["machine_rows"]]
    machine_kg = fsum(row["T17b_kg"] for row in rows)
    station_kg = next(row["T17b_kg"] for row in rows if row["node"].startswith("Гидростанция"))
    full_old_plate_kg = next(row["T17b_kg"] for row in rows if row["node"]=="Плита шибера")
    rail_kg = next(row["mass_kg"] for row in base["mass"]["frame_rows"] if row["node"].startswith("Боковой упор"))
    return {
        "status":"T17_REFERENCE_NO_RELEASED_R2_GATE", "machine_T17_kg":machine_kg,
        "machine_T17b_carried_reference_kg":machine_kg, "selected_R2_machine_mass_kg":None,
        "machine_rows":rows, "reference_margin_to_5000_kg":5000.-machine_kg,
        "reference_margin_to_4850_kg":4850.-machine_kg, "reference_limit_5000_status":"PASS" if machine_kg<=5000 else "FAIL",
        "target_4850_status":"FAIL" if machine_kg>4850 else "PASS",
        "named_uncertainty_kg":{"station_plus_minus":.05*station_kg,"cast_machining_allowance_plus":[20.,40.],
                                "unweighed_line_items_subtotal":345.,"unweighed_line_items_error_bound":None,
                                "reference_named_upper_without_unweighed_error":machine_kg+.05*station_kg+40.},
        "short_span_optimistic_mass_floor_kg":machine_kg-rail_kg-full_old_plate_kg+geometry["local_blade_envelope_mass_kg"],
        "short_span_mass_floor_basis":"Remove all side rails and the full 260 x 260 mm blade allowance, retain the 55 mm insert, add only the local blade envelope and zero other replacement hardware.",
    }
