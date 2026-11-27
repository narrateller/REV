"""Generate the T-2.5c ledger, calculations, metrics and report from pinned inputs."""

import json
from math import fsum, isclose
from pathlib import Path

import yaml

import cartridges
import motor
import relief
import report
import tank


ROOT = Path(__file__).resolve().parents[2]
CALC = Path("calc/T-2.5c")
STATION = Path("design/hydraulics/station.t25c.yaml")
PARAMS = "calc/T-2.6/params/params.t26a.yaml"
GATES = "gates.t25c.json"


def read_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_text(path, contents):
    (ROOT / path).write_text(contents, encoding="utf-8", newline="\n")


def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def measure(key, label, previous, finding, saving_kg=0):
    return {"id": key, "measure": label, "status": "зачтено" if saving_kg else "не зачтено",
            "credited_delta_kg": -saving_kg if saving_kg else 0,
            "credited_saving_kg": saving_kg, "potential_delta_kg": previous["t25_potential_delta_kg"],
            "ledger_ids": previous["ledger_ids"], "reason": finding["reason"], "source_ids": finding["source_ids"]}


def cooling_check(spec, station, power_limit_kW, circuit, baseline_inputs):
    cooling = station["cooling"]
    oil = cooling["oil_pressure"]
    power_kW = oil["pc_motor_kW"]
    flow_L_min = baseline_inputs["oil_flow_L_min"]
    efficiency = baseline_inputs["pc_efficiency_floor"]
    factor_kW_per_bar = flow_L_min / (600 * efficiency)
    installed_kW = cooling["installed_base_kW"]
    installed_with_air_kW = cooling["installed_with_air_option_kW"]
    assert installed_kW <= installed_with_air_kW <= power_limit_kW
    cb_trial_bar = spec["candidate_CB_crack_bar"]
    return spec | {
        "model": cooling["selected"]["model"],
        "installed_kW": installed_kW, "installed_with_air_option_kW": installed_with_air_kW,
        "installed_limit_kW": power_limit_kW, "pc_motor_kW": power_kW,
        "pc_flow_L_min": flow_L_min, "pc_estimated_efficiency": efficiency,
        "pc_branch_design_dp_limit_bar": oil["limit_dp_bar"],
        "pc_required_shaft_kW": [dp * factor_kW_per_bar for dp in spec["pc_branch_dp_bar"]],
        "pc_cold_shaft_kW": spec["pc_cold_dp_bar"] * factor_kW_per_bar,
        "pc_shaft_kW_at_candidate_CB_bar": cb_trial_bar * factor_kW_per_bar,
        "pc_max_dp_bar_for_motor_at_nominal_flow": power_kW / factor_kW_per_bar,
        "pc_min_efficiency_at_candidate_CB_bar": flow_L_min * cb_trial_bar / (600 * power_kW),
        "existing_CB_crack_bar": circuit["elements"]["CB"]["setpoint"]["crack_bar"],
        "candidate_CB_qualified": False,
        "source_ids": ["baseline", "baseline_review", "baseline_inputs", "circuit", "bowman_profile", "bowman_manual"],
    }


def apply_motor_row(rows, selected, references, credited):
    """Apply each approved mass change once, preserving the original row IDs and order."""
    by_id = {row["id"]: row for row in rows}
    assert len(by_id) == len(rows)
    changed_rows = [row_id for item in credited for row_id in item["ledger_ids"]]
    assert len(set(changed_rows)) == len(changed_rows)
    assert changed_rows in ([], ["T25-M1"])
    if not selected:
        assert not changed_rows
        return rows
    assert changed_rows == ["T25-M1"]
    motor_row = by_id["T25-M1"]
    return [row if row is not motor_row else row | {
        "part": f"{selected['model']} {selected['order_number']} IM B5",
        "mass_kg": selected["exact_mass_kg"],
        "source": references["abb_bdk"]["url"],
        "basis": "Масса нетто точного артикула IM3001. Колокол и муфта учтены в T16-06.",
    } for row in rows]


def range_kg(variants, key):
    values = [variant[key] for variant in variants.values()]
    return [min(values), max(values)]


def main():
    source_data = read_yaml(CALC / "sources.yaml")
    references = source_data["references"]
    station = read_yaml(references["baseline"]["url"])
    baseline_metrics = read_json(references["baseline_metrics"]["url"])
    baseline_config = read_yaml(references["baseline_inputs"]["url"])["inputs"]
    criteria = read_yaml(references["criteria"]["url"])["criteria"]
    circuit = read_yaml(references["circuit"]["url"])
    params = read_yaml(PARAMS)
    pump = params["cycle_model"]["pump"]
    reference_gate = read_json(GATES)
    assert Path(reference_gate["input"].replace("\\", "/")).as_posix() == PARAMS
    gate_by_id = {gate["id"]: gate for gate in reference_gate["gates"]}
    assert reference_gate["overall"] == "PASS" and set(gate_by_id) == {"G-PFACE", "G-DOSE", "G-CYCLE"}
    assert all(gate["status"] == "PASS" for gate in gate_by_id.values())
    assert pump["motor_rpm"] == pump["rated_motor_rpm"] == 1480
    assert gate_by_id["G-CYCLE"]["details"]["method"] == "reference_model"
    weg_gate = next(gate for gate in read_json(references["weg_gate"]["url"])["gates"] if gate["id"] == "G-CYCLE")
    power = criteria["C-PWR-01"]
    motors = motor.qualify(source_data["motor"], gate_by_id["G-CYCLE"], weg_gate,
                           pump["rated_motor_rpm"], power["max_rms_kW"])
    selected = motors["selected"]
    baseline_motor = motors["baseline"]
    active_motor = selected or baseline_motor
    rows = station["mass_rows"]
    baseline_station_kg = fsum(row["mass_kg"] for row in rows)
    base_by_id = {row["id"]: row for row in rows}
    for baseline_kg in (station["mass_kg"], baseline_metrics["station_t25b_kg"], 1686.19):
        assert isclose(baseline_station_kg, baseline_kg, abs_tol=0.01, rel_tol=0)
    assert base_by_id["T25-M1"]["mass_kg"] == baseline_motor["exact_mass_kg"]
    previous = {tuple(item["ledger_ids"]): item for item in station["measures"]}
    t0, tf = (station["reservoirs"][key] for key in ("T0", "TF"))
    tf_check = relief.qualify(source_data["tf"], circuit, previous[("T16-15", "T16-18")],
                             t0["density_kg_m3"], tf["nominal_gauge_bar"])
    db_check = cartridges.qualify(source_data["cartridges"], circuit, previous[("T16-08",)],
                                source_data["tank"]["density_kg_m3"], criteria["C-HYD-01"])
    motor_saving_kg = -selected["mass_difference_kg"] if selected else 0
    drive_kg = active_motor["exact_mass_kg"] + base_by_id["T25-P1"]["mass_kg"] + base_by_id["T25-P1_DFE1Z"]["mass_kg"]
    tank_check = tank.qualify(source_data["tank"], t0, previous[("T16-02",)]["evidence"],
                              baseline_station_kg - motor_saving_kg, drive_kg, pump["rated_motor_rpm"])
    assert not any(item["credited"] for item in (tf_check, db_check, *tank_check.values()))
    motor_finding = selected or {"reason": "Ни один кандидат не квалифицирован.",
                                "source_ids": ["omec", "abb_bdk", "weg", "brook", "omega"]}
    measures = [
        measure("motor", "Мотор Al IM B5", previous[("T25-M1",)], motor_finding, motor_saving_kg),
        measure("tf", "Предохранитель TF", previous[("T16-15", "T16-18")], tf_check),
        measure("db", "Шесть DB30 → картриджи", previous[("T16-08",)], db_check),
        measure("tank_walls", "Стенки T0 3 мм и рёбра", previous[("T16-02",)], tank_check["walls"]),
        measure("tank_base", "T0 как основание", previous[("T16-06",)], tank_check["base"]),
    ]
    assert len({row_id for item in measures for row_id in item["ledger_ids"]}) == sum(
        len(item["ledger_ids"]) for item in measures
    )
    assert all(source_id in references for item in measures for source_id in item["source_ids"])
    credited = [item for item in measures if item["credited_saving_kg"]]
    pending = [item for item in measures if not item["credited_saving_kg"]]
    total_credited_kg = fsum(item["credited_saving_kg"] for item in credited)
    station_rows = apply_motor_row(rows, selected, references, credited)
    station_kg = fsum(row["mass_kg"] for row in station_rows)
    assert isclose(station_kg, baseline_station_kg - total_credited_kg, abs_tol=1e-8)

    historical_potential_kg = -fsum(item["potential_delta_kg"] for item in measures)
    selected_motor_potential_kg = total_credited_kg - fsum(item["potential_delta_kg"] for item in pending)
    mass_limit_kg = criteria["C-MASS-01"]["max_kg"]
    comparison_kg = 5080
    variants = {}
    for key, base in baseline_metrics["machine_A_variants"].items():
        before_kg = base["t25b_kg"]
        assert isclose(before_kg, station["base_reconciliation"]["machine_A_variants"][key]["t25b_kg"], abs_tol=0.01)
        after_kg = before_kg - total_credited_kg
        variants[key] = base | {
            "t25c_kg": after_kg, "outside_station_kg": before_kg - baseline_station_kg,
            "missing_to_5000_kg": max(after_kg - mass_limit_kg, 0),
            "missing_to_5080_kg": max(after_kg - comparison_kg, 0),
            "all_measures_t25b_potentials_kg": before_kg - historical_potential_kg,
            "all_measures_with_qualified_motor_kg": before_kg - selected_motor_potential_kg,
        }
        assert isclose(after_kg, variants[key]["outside_station_kg"] + station_kg, abs_tol=1e-8)
    assert [round(value, 2) for value in sorted(v["t25b_kg"] for v in variants.values())] == [5158.90, 5167.80, 5202.25]
    machine_range_kg = range_kg(variants, "t25c_kg")
    mass_acceptance = machine_range_kg[-1] <= mass_limit_kg
    cooling = cooling_check(source_data["cooling"], station, power["max_installed_kW"], circuit, baseline_config)
    cycle = motor.cycle_result(gate_by_id["G-CYCLE"])
    metrics = {
        "status": "PASS" if mass_acceptance else "STOP_MASS", "mass_acceptance": mass_acceptance,
        "station_t25b_kg": baseline_station_kg, "station_t25c_kg": station_kg,
        "credited_measures_kg": total_credited_kg, "credited_measures": credited, "not_credited_measures": pending,
        "machine_A_kg_range": machine_range_kg,
        "missing_to_5000_kg": range_kg(variants, "missing_to_5000_kg")[-1],
        "missing_to_5080_kg": range_kg(variants, "missing_to_5080_kg")[-1],
        "machine_A_all_measures_kg_range": range_kg(variants, "all_measures_t25b_potentials_kg"),
        "machine_A_all_measures_with_qualified_motor_kg_range": range_kg(variants, "all_measures_with_qualified_motor_kg"),
        "all_measures_t25b_potential_saving_kg": historical_potential_kg,
        "all_measures_with_qualified_motor_potential_saving_kg": selected_motor_potential_kg,
        "machine_A_variants": variants,
        "motor_model": active_motor["model"], "motor_order_number": active_motor.get("order_number"),
        "motor_kg": active_motor["exact_mass_kg"], "motor_rated_rpm": active_motor["rated_rpm"],
        "cycle_gate_s": cycle["cycle_s"], "rms_kW": cycle["rms_kW"],
        "tf_capacity_L_min": tf_check["retained"]["qualified_capacity_L_min"],
        "tf_capacity_screen_L_min": tf_check["retained"]["screen"]["corrected_L_min"],
        "tf_required_L_min": tf_check["required_L_min"],
        "installed_kW": cooling["installed_kW"], "installed_with_air_option_kW": cooling["installed_with_air_option_kW"],
        "pc_branch_dp_bar": cooling["pc_branch_dp_bar"],
    }
    for gate_id in station["cycle"]:
        gate = gate_by_id[gate_id]
        station["cycle"][gate_id].update(status=gate["status"], value=gate["value"])
    station["cycle"]["G-CYCLE"].update(rms_kW=cycle["rms_kW"], input=PARAMS, gate_report=GATES)
    if selected:
        station["hydraulics"]["main_drive"].update(
            motor=f"{selected['model']} IM B5", motor_order_number=selected["order_number"],
            rated_rpm=selected["rated_rpm"], rated_torque_Nm=selected["rated_Nm"],
            motor_breakdown_Nm=selected["breakdown_Nm"], rated_current_400V_A=selected["current_400V_A"],
            efficiency_pct=selected["efficiency_pct"], supply_V=400, reference_model_rpm=pump["motor_rpm"],
            motor_source=references["abb_bdk"]["url"],
        )
    qualification = {"motor": motors, "tf": tf_check, "db": db_check, "tank": tank_check, "cooling_KD": cooling}
    station.update(task="T-2.5c", status=metrics["status"], mass_acceptance=mass_acceptance,
                   mass_kg=station_kg, mass_rows=station_rows, credited_reduction_kg=total_credited_kg,
                   measures=measures, qualification=qualification, qualification_sources=references)
    station["mass_reconciliation_t25c"] = {
        "baseline_station_kg": baseline_station_kg, "mass_limit_kg": mass_limit_kg,
        "baseline_credited_reduction_kg": baseline_metrics["station_t25_kg"] - baseline_station_kg,
        "machine_A_variants": variants,
    }
    station["open_items"].append("В КД подтвердить монтажный зазор к клеммной коробке ABB и настройку тепловой защиты по 55,1 А.")
    station["open_items"].append("CB 1,5 бар при 180 л/мин требует 0,625 кВт по принятому КПД. Уставку уточнить по характеристике PC и фактическому расходу ветвей.")
    results = {"metrics": metrics, "measures": measures, "qualification": qualification, "mass_rows": station_rows,
               "gates": station["cycle"], "sources": references}

    write_json(CALC / "results.json", results)
    write_json("metrics.json", metrics)
    write_text(STATION, yaml.safe_dump(station, allow_unicode=True, sort_keys=False, width=120))
    write_text("report.md", report.render(results))


if __name__ == "__main__":
    main()
