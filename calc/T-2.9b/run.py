"""Rebuild the station revision, scan the frozen cycle gate and generate the report."""
import csv
import json

from build_scheme import DESIGN, HERE, ROOT, read
from check_circuit import CIRCUIT, INTERLOCKS, evaluate
from draw_circuit import render
from hoses import cycle_row, gate
import mass
import oil_modulus
import pc_select
import power_balance
from report import render_report
from revision import PARAMS, params_text, write_scheme


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def revisions(ledger, oil):
    items = [
        (item["tag"], item["before"], item["after"], item["delta_kg"], item["installed_delta_kW"],
         item["source"], item["basis"]) for item in ledger["mass_revision_vs_t25c"]
    ]
    items += [
        (item["tag"], "Арматура T-2.9", "Исключена", -item["mass_t29_kg"] if item["mass_t29_kg"] else None,
         0, item["source"], item["basis"]) for item in ledger["removed_vs_t29"]
    ]
    items += [
        ("VG", "P от GH", "P от HP", 0, 0, "DECISIONS.md#D-GK-23", "Шибер только от P1."),
        ("LG0, XLG, GH", "Карманы и линии LG", "Исключены", None, 0, "DECISIONS.md#D-GK-23",
         "Масса см. отдельный блок LG."),
        ("ALP", "Parker EHV 49 кг, 17,8 л", "Та же паспортная строка; LP отключён от шибера", 0, 0,
         "calc/T-2.9b/sources.yaml#parker_lp", "MSG10-4082/UK с. 5."),
        ("CB", "Уставка открыта", "Цель 1,70 бар, допуск 1,65–1,75 бар", None, 0,
         "calc/T-2.9b/pc_select.py", "Кандидат. Требуется перепад ≤2 бар при полном расходе."),
        ("TT, TT_VALID, TT_MIN", "Температура охлаждения", "Гистерезис 31/30 °C и диагностика", 0, 0,
         "DECISIONS.md#D-GK-23", "Ограничение потока ZSF 1005 л/мин в прогреве."),
        ("P1 / pre_up", "35 бар приведённого", "P1 ≥45 бар и 35 бар приведённого", 0, 0,
         "calc/T-2.9b/unlock.py", "Контроль до освобождения носа."),
        ("TF → ZSF.A / PF", "Цель 0,5 м", "Сталь ≤0,5 м", 0, 0, "DECISIONS.md#D-GK-23",
         "Требование к компоновке по кавитации и всплескам. Масса до проверки компоновки."),
        ("P1 → MA → CYM", "Жёсткие трубы в описании", "Тракт и карманы MF/MC/ZSF только сталь", 0, 0,
         "DECISIONS.md#D-GK-23", "Податливость масляного столба."),
        ("params.lp.routes", "pre_up, pre_down, gate_open, gate_close, eject", "pre_up, pre_down, eject", 0, 0,
         "calc/T-2.9/results.json#mass_alternative_disable_LP_on_slide_gate", "Маршруты D-GK-23."),
        ("params.oil.bulk_modulus_Pa", "1,40 ГПа", f"{oil['params_K_Pa'] / 1e9:.3f} ГПа, масло + сталь",
         0, 0, "calc/T-2.9b/oil_modulus.py", "Предел квалификации при достаточном K_eff."),
        ("params.gate_release_cap_bar", "5 бар, 3 + погрешность", "5 бар, 3 действительных + 2 запаса", 0, 0,
         "ops/gates/cycle_model/inputs.py", "Число в расчёте нагрузки VG; 3 бар по двум верхним оценкам датчиков."),
    ]
    with (HERE / "circuit_changes.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(("element", "before", "after", "delta_station_kg", "delta_installed_kW", "source", "basis"))
        writer.writerows(items)
    return items


def run():
    pc = pc_select.calculate()
    oil = oil_modulus.calculate()
    power = power_balance.calculate(pc["preferred_candidate"]["motor_kW"])
    PARAMS.write_text(params_text(oil["params_K_Pa"]), encoding="utf-8", newline="\n")
    circuit, logic = write_scheme(pc)
    checked = evaluate(CIRCUIT, INTERLOCKS)
    if not checked["passed"]:
        raise RuntimeError(json.dumps({key: value for key, value in checked.items()
                                       if key.endswith("errors")}, ensure_ascii=False))
    (DESIGN / "T-2.9b_circuit.svg").write_text(render(circuit), encoding="utf-8", newline="\n")
    nominal_gates = gate(PARAMS, ROOT / "gates.t29b.json")
    nominal = cycle_row(nominal_gates, oil["params_K_Pa"])
    gate_status = {item["id"]: item["status"] for item in nominal_gates["gates"]}
    scan = oil_modulus.scan()
    write_json(HERE / "k_scan.json", scan)
    matching_scan = [row for row in scan["k_scan"] if row["K_Pa"] == oil["params_K_Pa"]]
    if matching_scan and matching_scan != [nominal]:
        raise RuntimeError("Nominal gate and K scan differ at the same K")
    ledger = mass.generate(pc, power, nominal | {"gate_input": str(PARAMS.relative_to(ROOT).as_posix()),
                                                "gate_status": gate_status})
    blockers = [pc["status"]]
    if not nominal["card_pass"] or set(gate_status.values()) != {"PASS"}:
        blockers.append("STOP_CYCLE")
    if oil["K_eff_Pa"] < scan["k_threshold_t29b_Pa"] or oil["temperatures"][50]["K_oil_Pa"] < 1.42e9:
        blockers.append("STOP_K")
    if not ledger["station_delta_pass"]:
        blockers.append("STOP_MASS")
    if not power["power_budget_pass"]:
        blockers.append("STOP_POWER")
    deltas = revisions(ledger, oil)
    result = {
        "task": "T-2.9b", "status": "HOLD_PC_AND_MASS", "blockers": blockers,
        "gate_nominal": nominal, "gate_status": gate_status, "circuit": checked,
        "pc": pc, "oil_modulus": oil, "power": power, "mass": ledger,
        "circuit_revision": deltas, "geometry_interlocks": logic["geometry"], **scan,
    }
    write_json(HERE / "results.json", result)
    candidate = pc["preferred_candidate"]
    metrics = {
        "status": result["status"], "blockers": blockers, "gate_status": gate_status,
        "pc_model": candidate["model"], "pc_selection_status": pc["status"],
        "pc_motor_kW": candidate["motor_kW"], "pc_shaft_kW_hot_max": candidate["shaft_kW_hot_max_bound"],
        "pc_shaft_kW_cold_start": candidate["start"]["shaft_kW_bound_at_first_pc_start"],
        "pc_shaft_basis": "Conditional upper bound if total pump Δp≤2 bar at 950 rpm, PC off during initial warmup.",
        "pc_flow_L_min": candidate["flow_screen_min_L_min"],
        "cb_setpoint_bar": None, "cb_candidate_setpoint_bar": candidate["cb_crack_target_bar"],
        "q_dirty_kW": candidate["q_dirty_kW"], "pc_flow_and_heat_basis": "Screening with 55 °C HLP46 flow loss estimated.",
        "installed_kW": power["installed_kW"], "installed_with_air_option_kW": power["installed_with_air_option_kW"],
        "reserve_breakdown": power["reserve_breakdown"],
        "k_oil_source_Pa": oil["temperatures"][50]["K_oil_Pa"],
        "k_oil_55C_Pa": oil["temperatures"][55]["K_oil_Pa"], "k_eff_Pa": oil["K_eff_Pa"], **scan,
        "cycle_gate_s": nominal["cycle_s"], "rms_kW": nominal["rms_kW"],
        "circuit_defects": checked["defects"], "mutations_total": checked["mutations"]["total"],
        "mutations_rejected": checked["mutations"]["rejected"],
        **{key: ledger[key] for key in (
            "station_kg", "station_delta_vs_t25c_kg", "station_upper_with_project_allowances_kg",
            "machine_A_kg_range", "machine_A_variants", "unresolved_mass_rows")},
    }
    write_json(ROOT / "metrics.json", metrics)
    render_report(result, nominal_gates)
    return result


if __name__ == "__main__":
    data = run()
    print(data["status"], data["blockers"])

