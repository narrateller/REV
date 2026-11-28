"""Generate the T-2.9 scheme, calculations and operator handoff."""
import argparse
import csv
import json
from pathlib import Path

import hoses
import mass
import transient
import unlock
from build_scheme import DESIGN, ROOT, HERE, circuit_model, interlock_model, read, write
from check_circuit import CIRCUIT, INTERLOCKS, evaluate
from draw_circuit import render
from report import render_report

import pc_branch
import pc_options
import cavitation


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def changes(circuit, ledger):
    old = read(DESIGN / "T-1.6_circuit.yaml")["elements"]
    new = circuit["elements"]
    sources = (read(ROOT / "calc/T-1.6/sources.yaml")["catalogs"]
               | read(HERE / "sources.yaml")["catalogs"])
    mass_rows = {entry["item"]: entry for entry in ledger["mass_delta"]}
    purposes = {"station": "Привод T-2.6 / T-2.5c", "main": "Геометрия схемы A",
                "fill": "Расход и защита TF", "rapid": "Регенерация и плавание быстрых",
                "pre": "Два канала носа и ограничения башмака", "gate": "Приоритет шибера",
                "lp": "Подача ГА НД T-2.6 и Parker", "pilot": "Внешний пилот T-2.6",
                "cool": "Базовое охлаждение Bowman", "water": "Контроль воды площадки",
                "air": "Сменная воздушная опция"}
    rows = []
    for tag in sorted(old.keys() | new.keys()):
        previous = old.get(tag, {})
        next_item = new.get(tag, {})
        if previous == next_item:
            continue
        fields = sorted(k for k in previous.keys() | next_item.keys()
                        if previous.get(k) != next_item.get(k))
        src = sources.get(next_item.get("source") or previous.get("source"), {})
        mass_row = mass_rows.get(tag)
        rows.append({
            "element": tag, "before": previous.get("series", "—"),
            "after": next_item.get("series", "—"), "fields": fields,
            "section": (next_item or previous)["section"],
            "station_delta_kg": mass_row["delta_kg"] if mass_row else None,
            "source": src.get("url", "design/hydraulics/station.t25c.yaml"),
            "reason": purposes[(next_item or previous)["section"]],
        })
    with (HERE / "circuit_changes.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["element", "before", "after", "changed_fields", "delta_station_kg", "source", "reason"])
        for row in rows:
            writer.writerow([row["element"], row["before"], row["after"], ", ".join(row["fields"]),
                             row["station_delta_kg"], row["source"], row["reason"]])
    return rows


def run(reuse_scan=False):
    hoses.build_params()
    params = read(hoses.PARAMS)
    circuit = circuit_model()
    interlocks = interlock_model(params)
    write(CIRCUIT, circuit)
    write(INTERLOCKS, interlocks)
    checked = evaluate(CIRCUIT, INTERLOCKS)
    if not checked["passed"]:
        raise RuntimeError("Circuit check failed: " + json.dumps({
            key: value for key, value in checked.items()
            if key.endswith("errors") or key == "unknown_sensor_references"}, ensure_ascii=False))
    (DESIGN / "T-2.9_circuit.svg").write_text(render(circuit), encoding="utf-8", newline="\n")
    gates = hoses.gate(hoses.PARAMS, ROOT / "gates.t29.json")
    nominal = hoses.cycle_row(gates, params["cycle_model"]["oil"]["bulk_modulus_Pa"])
    scan_path = HERE / "k_scan.json"
    sensitivity = json.loads(scan_path.read_text(encoding="utf-8")) if reuse_scan else hoses.scan()
    write_json(scan_path, sensitivity)
    if next(row for row in sensitivity["k_scan"] if row["K_Pa"] == nominal["K_Pa"]) != nominal:
        raise RuntimeError("The K scan does not match the current nominal LP model")
    sources = read(HERE / "sources.yaml")["screen_inputs"]
    pc = pc_branch.analyse(sources, read(ROOT / "calc/T-2.5b/sources.yaml")["inputs"],
                           read(DESIGN / "station.t25c.yaml"), read(DESIGN / "T-1.6_circuit.yaml"))
    options = pc_options.calculate(pc)
    tank = transient.calculate()
    suction = cavitation.calculate(run_gate=True)
    effective_K = hoses.hose_inventory(sensitivity["hose_K_threshold_Pa"])
    mechanical = unlock.calculate()
    ledger = mass.calculate(circuit)
    revision = changes(circuit, ledger)
    alternative = hoses.no_gate_boost_check()
    blockers = []
    if (tank["zsf_port_A_peak_bar"]["emergency_fast_edge_1ms"] > tank["zsf_port_A_allowed_bar"]
            or suction["air_release_margin_bar"] < 0):
        blockers.append("STOP_ZSF")
    if ledger["station_mass_delta_kg"] > 10:
        blockers.append("STOP_MASS")
    if not nominal["card_pass"]:
        blockers.append("STOP_CYCLE")
    blockers.append("STOP_PC")
    results = {
        "task": "T-2.9", "status": blockers[0], "blockers": blockers,
        "circuit": checked, "circuit_revision": revision, "gate_nominal": nominal,
        "gate_status": {item["id"]: item["status"] for item in gates["gates"]},
        "pc_branch": pc, "pc_operator_comparison": options,
        "transient": tank, "cavitation": suction, "hoses": effective_K, "unlock": mechanical,
        "mass": ledger, "mass_alternative_disable_LP_on_slide_gate": alternative,
        "geometry_interlocks": interlocks["geometry"], **sensitivity,
    }
    write_json(HERE / "results.json", results)
    mutations = checked["mutations"]
    metrics = {
        "status": results["status"], "blockers": blockers,
        "circuit_defects": checked["defects"], "mutations_total": mutations["total"],
        "mutations_rejected": mutations["rejected"], "new_interlocks": mutations["new_interlocks"],
        "zsf_port_A_peak_bar": tank["zsf_port_A_peak_bar"],
        "zsf_port_A_allowed_bar": tank["zsf_port_A_allowed_bar"],
        "tf_peak_bar": tank["tf_exhaust_conservative_combined_bar"],
        "tf_vessel_peak_bar": tank["tf_peak_bar"], "tf_relief_bar": tank["tf_relief_bar"],
        "cap_min_abs_bar": suction["cap_min_abs_bar"], "air_release_margin_bar": suction["air_release_margin_bar"],
        "pc_dp_bar_42_45C": {row["temperature_C"]: {
            "clean": row["clean_dp_bar"], "dirty_scenario": row["dirty_scenario_dp_bar"]}
            for row in pc["operating_points"] if row["temperature_C"] in (42, 45)},
        "pc_shaft_kW_max": None,
        "pc_KF125_catalogue_kW_at_2bar": next(
            row["shaft_kW"] for row in pc["catalogue_and_extrapolated_points_at_34_mm2_s"]
            if row["speed_rpm"] == 1450 and row["pressure_bar"] == 2),
        "cb_setpoint_bar": None, "installed_kW": pc["installed_base_kW"],
        "installed_with_air_option_kW": pc["installed_with_air_option_kW"],
        "pc_options": options["pc_options"], "hose_K_eff_Pa": effective_K["main_hose_K_eff_Pa"],
        "cycle_gate_s": nominal["cycle_s"], "rms_kW": nominal["rms_kW"],
        "unlock_force_kN": mechanical["unlock_force_kN"],
        "station_mass_delta_kg": ledger["station_mass_delta_kg"], "station_kg": ledger["station_kg"],
        "machine_A_kg_range": ledger["machine_A_kg_range"], **sensitivity,
    }
    write_json(ROOT / "metrics.json", metrics)
    render_report(results)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-scan", action="store_true")
    data = run(parser.parse_args().reuse_scan)
    print(data["status"], data["gate_nominal"], data["blockers"])
