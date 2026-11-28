"""Сформировать отчёт STOP из двух сверенных прогонов диагностики."""
import argparse
import hashlib
import json

from stop_check import HERE, ROOT, json_write


def render(results, repeat_sha256):
    feed_report = results["feed_fixture_gate_report"]
    feed, = feed_report["gates"]
    oil = results["oil_diagnostics"]
    columns = results["column_compliance"]
    ma = results["cover_MA_M36_ligament"]
    buffer = results["TF_buffer_limit"]
    scans = results["cap_dead_scan"]
    cover_only = next(row for row in scans if row["case"] == "fixed_cover_only")
    with_columns = next(row for row in scans if row["case"] == "cover_and_smooth_columns_only")
    mass = results["ledger_reference"]
    method_values = oil["fixed_cover_by_element_L"]
    oil_rows = "\n".join(
        f"| {name} | {before:.3f} | {fixed} |" for name, before, fixed in (
            ("P0/HP", oil["T29b_reference_by_element"][0]["volume_L"], "—"),
            ("MH", oil["T29b_reference_by_element"][1]["volume_L"], "—"),
            ("MF со стороны MA", oil["T29b_reference_by_element"][2]["volume_L"], "—"),
            ("MC со стороны MB при регенерации", oil["T29b_reference_by_element"][3]["volume_L"], "—"),
            ("MA, радиальные сверления", oil["T29b_reference_by_element"][4]["volume_L"],
             f"{method_values['MA_radial_drillings']:.3f}"),
            ("Осевой канал ZSF в крышке", oil["T29b_reference_by_element"][5]["volume_L"],
             f"{method_values['ZSF_axial_bore_in_cover']:.3f}"),
            ("Сумма", oil["T29b_total_L"], f"{oil['fixed_cover_L']:.3f}"),
        )
    )
    scan_rows = "\n".join(
        f"| {row['cap_dead_L']:.4f} | {row['cycle_s']:.4f} | {row['rms_kW']:.3f} | "
        f"{row['TF_required_oil_L']:.3f} | {row['gates']['G-CYCLE']} |"
        for row in scans
    )
    report = f"""# T-2.3 — STOP. Мастер-компоновка схемы A

## Приёмочные блокеры

**G-FEED.** В критерии v4 C-FEEDPATH-01 отсутствует `min_window_area_mm2`. Код G-FEED 1.2.0 возвращает WARN при выполнении остальных проверок и FAIL при дефекте геометрии. В FreeCAD {feed_report['freecad_version']} тестовый путь с площадью контакта **{feed['value']:.0f} мм²** и с бункером, и с вкладышем дал WARN «порог окна не задан». Тело пути связное, пересечений нет. Размер 200 × 150 мм взят из замороженного окна T-2.2i. Для обязательного PASS нужно решение ГК по численному порогу. [Критерии](ops/criteria/design_criteria.yaml) · [Гейт](ops/gates/geom_gates.py) · [Тест](calc/T-2.3/results.json)

**G-CYCLE.** При неизменной ветви наполнения штатный гейт требует запас TF ≥ 1,5 · (вытеснение поршня + cap_dead_L) + вытеснение штока. При Ø280/200 мм и ходе 396 мм это **{buffer['max_cap_dead_L']:.4f} л максимум для cap_dead_L** при имеющихся {buffer['available_oil_L']:.0f} л масла TF. На внешний объём и податливость остаётся {buffer['max_external_and_compliance_allowance_L']:.4f} л после базовых 0,8 л. Одни каналы крышки дают {oil['fixed_cover_L']:.4f} л. При `cap_dead_L = {cover_only['cap_dead_L']:.4f}` л гейт требует {cover_only['TF_required_oil_L']:.3f} л в TF и возвращает FAIL по `fill_routes_admissible`. Это происходит ещё до податливости и добавления труб. Укорочение PF не снимает этот отказ при предписанном изменении только `cap_dead_L`. [Модель наполнения](ops/gates/cycle_model/inputs.py) · [Вход T-2.9b](calc/T-2.9b/params/params.t29b.yaml)

**MA ↔ M36.** В крышке Ø520 × 144 мм оси сверлений MA Ø44 расположены в {ma['from_barrel_seat_mm']:.0f} мм от посадки гильзы. Между MA и сквозными отверстиями Ø{ma['M36_hole_ID_mm']} на PCD {ma['M36_PCD_mm']} мм остаётся {ma['nominal_mm']:.3f} мм при требовании D-GK-08 ≥ {ma['required_mm']} мм. Недобор {ma['nominal_shortfall_mm']:.3f} мм присутствует во всех позах. При пересечении окружности PCD трассой Ø44 внутри крышки даже максимальное расстояние до ближайшей крепёжной оси даёт перемычку не более {ma['bolt_circle_upper_bound_mm']:.3f} мм. Требуется утверждённая геометрия коллектора MA с повторной проверкой зоны. [Действующая крышка](design/main_cylinder_rear.t22.yaml) · [H2](ops/reports/T-2.2/GK_review.md) · [D-GK-08](DECISIONS.md)

## Диагностические объёмы и скан

| Элемент | T-2.9b, л | Проверено T-2.3 только в крышке, л |
|---|---:|---:|
{oil_rows}

Аналитическое сечение с обрезкой по Ø520 и раздельные объёмы BRep FreeCAD дают {oil['fixed_cover_L']:.6f} и {oil['fixed_cover_cad_L']:.6f} л. Расхождение {oil['delta_pct']:.6f} %. Использованы номинальные цилиндрические каналы без учёта галтелей. Объём крышки выше цели 2,5 л. Полный V_out и длина PF требуют фактической трассировки. PF находится по низкой стороне от седла ZSF. В фазе прессования MC связан со штоковой полостью MB. Перечень T-2.9b включает MC для регенерации. [Схема](design/hydraulics/T-2.9b_circuit.yaml) · [Блокировки](design/hydraulics/T-2.9b_interlocks.yaml) · [Перечень T-2.9b](calc/T-2.9b/oil_modulus.py)

Гладкие участки 4 × Ø70 × 485 мм, E = 210 ГПа, дали удлинение {columns['smooth_columns_displacement_mm']:.3f} мм при {columns['pressure_bar']} бар и {columns['force_N']/1e6:.3f} МН. Эквивалент податливости гладких участков при K_eff 1,434 ГПа — {columns['smooth_columns_equivalent_L']:.4f} л. Ведомость T-2.6 задаёт 0,8 л как объём полости. Множитель податливости T-2.6 применён отдельно в модели декомпрессии, поэтому вычет из 0,8 л не сделан. Прогиб крышки и плит остаётся открытым. Раздача гильзы уже учитывалась в оценке K_eff T-2.9b. [Геометрия колонн](design/chamber_roof.t22i.yaml) · [T-2.6](calc/T-2.6/sources.yaml) · [Декомпрессия](calc/T-2.6/cycle/drive.py)

| cap_dead_L, л | Цикл, с | RMS, кВт | Требуется масла в TF, л | G-CYCLE |
|---:|---:|---:|---:|:---|
{scan_rows}

В строках {cover_only['cap_dead_L']:.4f} и {with_columns['cap_dead_L']:.4f} л учтены соответственно крышка и крышка с гладкими участками колонн. Это диагностика `reference_model` с единственным изменением `cap_dead_L`. G-PFACE и G-DOSE прошли во всех пяти точках. При 7,6 л гейт также фиксирует превышение 6,0 с. Полного значения `V_факт` до компоновки нет.

## Состояние сдачи

По действующей ведомости D-GK-24 исполнение с бандажом имеет {mass['machine_with_end_collar_kg']:.2f} кг, включая станцию {mass['station_kg']:.2f} кг и {mass['outside_station_kg']:.2f} кг вне станции. Сверка массы тел, габарит, позы и зазоры машины остаются открытыми. Мастер-файл, FCStd машины, итоговые параметры и приёмочные гейты машины не сформированы по стоп-условию AGENTS.md. Два прогона диагностики дали побайтно одинаковый `results.json`. [Источники](calc/T-2.3/sources.yaml) · [Проверки](self_check.json)

**Проект строки D-GK** — T-2.3 STOP. Для возобновления утвердить численный порог площади G-FEED, согласовать учёт физического объёма и эквивалентной податливости в проверке запаса масла TF и закрыть интерфейс коллектора MA с перемычкой ≥ 10 мм по D-GK-08.
"""
    assert "?" not in report
    (ROOT / "report.md").write_text(report, encoding="utf-8", newline="\n")
    status_keys = ["G-ENV", "G-MASS", "G-COLL", "G-FEED", "G-CLEAR", "G-PFACE", "G-DOSE", "G-CYCLE"]
    actual_fields = """
envelope_mm envelope_per_pose_mm mass_skeleton_kg mass_delta_pct credited_reductions_kg
bodies_count coll_max_mm3 feed_window_mm2 clear_max_mm hopper_opening_height_mm
V_out_L V_out_L_method2 V_out_by_element_L V_comp_L cap_dead_L TF_to_ZSF_A_m
cycle_gate_s rms_kW interfaces_count min_moving_clearance_mm
""".split()
    json_write(ROOT / "metrics.json", {
        "task": "T-2.3", "status": "STOP",
        **dict.fromkeys(actual_fields),
        "mass_ledger_kg": mass["machine_with_end_collar_kg"],
        "cap_dead_scan": scans,
        "diagnostics": {
            "feed_fixture_window_mm2": feed["value"],
            "G-FEED_fixture": feed["status"], "feed_gate_min_window_area_mm2": None,
            "cover_MA_M36_ligament": ma, "oil": oil, "columns": columns, "TF_buffer_limit": buffer,
        },
    })
    baseline = results["T29b_base_gate_report"]
    json_write(ROOT / "self_check.json", {
        "task": "T-2.3", "status": "STOP",
        "gate_status_machine": dict.fromkeys(status_keys, "NOT_RUN"),
        "diagnostics": {
            "geom_gates_unchanged_criteria": {feed["id"]: feed["status"]},
            "geom_fixture_passed_test": True, "freecad": feed_report["freecad_version"],
            "calc_gates_t29b_baseline": {gate["id"]: gate["status"] for gate in baseline["gates"]},
            "calc_gates_sensitivity": scans,
            "only_cap_dead_L_changed_in_sensitivity": True,
            "fixed_cover_methods_delta_pct": oil["delta_pct"],
            "fixed_cover_simpson_refinement_abs_tol_L": 1e-8,
            "analytical_TF_volume_check_matches_gate": True,
            "criteria_sha256": baseline["criteria_sha256"],
            "report_has_no_question_mark": True,
        },
        "repeat": {"runs": 2, "identical": True, "results_sha256": repeat_sha256},
        "reason": "G-FEED без численного порога и G-CYCLE по запасу TF при обязательном учёте объёма крышки",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repeat_sha256", help="Совпавший SHA-256 двух файлов results.json")
    args = parser.parse_args()
    data = (HERE / "results.json").read_bytes()
    assert hashlib.sha256(data).hexdigest() == args.repeat_sha256.lower()
    render(json.loads(data), args.repeat_sha256.lower())
