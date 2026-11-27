"""Generate the reproducible T-2.5 baseline, decision record and metrics."""

import json
from math import fsum, isclose
from pathlib import Path
import subprocess
import sys

import yaml

from inventory import calculate as inventory
from report import render
from tank import calculate as tank_screen
from cooling import calculate as cooling_screen
from inventory import installed_rows
from measures import calculate as qualification


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def read_yaml(relative_path):
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def write_text(path, text):
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def machine_ledger(station, criteria):
    t17c = read_json("calc/T-1.7c/results.json")["mass"]
    t17d = read_json("calc/T-1.7d/results.json")["working_trial"]["mass"]
    rear = read_yaml("design/main_cylinder_rear.t22.yaml")["mass"]
    rear_ledger = read_json("calc/T-2.2/results.json")["mass"]
    variants = read_json("calc/T-2.2i/results.json")["variants"]["nose_x225"]["mass"]
    station_before_T21_kg, = [row["mass_kg"] for row in t17c["baseline_rows"]
                              if row["node"] == "Гидростанция в сборе"]
    assert isclose(station_before_T21_kg, station["T16_kg"], abs_tol=1e-9)
    assert isclose(t17c["nominal_kg"], t17d["baseline_kg"], abs_tol=1e-9)
    assert isclose(t17d["baseline_kg"] + fsum(row["delta_kg"] for row in t17d["delta_rows"]),
                   t17d["nominal_kg"], abs_tol=1e-9)
    drive = station["reference_mass_checks"]
    assert isclose(rear_ledger["baseline_T21_kg"], drive["T21_machine_reference_kg"], abs_tol=1e-9)
    assert isclose(rear_ledger["nominal_AB_kg"], rear["nominal_machine_AB_kg"], abs_tol=1e-9)
    drive_delta_kg = drive["A4VSO_package_delta_vs_T16_kg"]
    station_in_machine_kg = station_before_T21_kg + drive_delta_kg
    station_after_T26_kg = station["station_base_kg"] + drive_delta_kg
    ledgers = {}
    for name, variant in variants.items():
        fixed = {row["part"]: row["mass_kg"] for row in variant["fixed_machine_rows"]}
        assert isclose(fixed["baseline"], rear["nominal_machine_AB_kg"], abs_tol=0.01)
        assert isclose(fixed["hydraulics_delta"], station["T26_delta_kg"], abs_tol=1e-9)
        structural_delta_kg = fsum(row["mass_kg"] for row in (*variant["reference_chamber_rows"], *variant["delta_rows"])) + fsum(
            value for part, value in fixed.items() if part not in ("baseline", "hydraulics_delta"))
        machine_kg = fixed["baseline"] - station_in_machine_kg + station_after_T26_kg + structural_delta_kg
        assert isclose(machine_kg, variant["machine_before_station_kg"], abs_tol=1e-9)
        ledgers[name] = dict(machine_before_lightening_kg=machine_kg, structural_and_H2_delta_kg=structural_delta_kg,
                             needed_to_machine_limit_kg=machine_kg - criteria["C-MASS-01"]["max_kg"],
                             reference_difference_kg=machine_kg - variant["machine_before_station_kg"])
    return dict(machine_reference_kg=fixed["baseline"], station_booked_in_machine_reference_kg=station_in_machine_kg,
                station_booked_in_machine_with_T26_delta_kg=station_after_T26_kg,
                machine_reference_plus_hydraulics_kg=fixed["baseline"] + station["T26_delta_kg"],
                exact_machine_reference_kg=rear["nominal_machine_AB_kg"],
                T17c_machine_kg=t17c["nominal_kg"], T17d_machine_kg=t17d["nominal_kg"],
                machine_A_kg_range=[min(v["machine_before_lightening_kg"] for v in ledgers.values()),
                                    max(v["machine_before_lightening_kg"] for v in ledgers.values())],
                A_variants=ledgers)



def calculate():
    sources = read_yaml("calc/T-2.5/sources.yaml")["sources"]
    criteria = read_yaml(sources["criteria"]["url"])["criteria"]
    t16 = read_json(sources["t16"]["url"])
    t26 = read_json(sources["t26"]["url"])
    t21 = read_json(sources["t21_mass"]["url"])
    selected = t26["variants"][t26["selected"]]
    circuit = read_yaml(sources["circuit"]["url"])
    interlocks = read_yaml(sources["interlocks"]["url"])
    t16_inputs = read_yaml(sources["t16_inputs"]["url"])
    motor_pump_inputs = read_yaml("calc/T-2.1/sources.yaml")
    project = t16_inputs["project"]
    station = inventory(ROOT, t16, selected)
    mass21 = t21["candidates"][t21["selected"]]["summary"]["mass"]
    drive_delta_kg = mass21["station_kg"] - mass21["reproduced_T16_station_kg"]
    parts26 = selected["mass"]["purchased_and_custom_rows"]
    pilot_legacy = read_yaml(sources["legacy_accumulators"]["url"])["catalogs"]["hydac_sb330"]
    ga_base_kg = next(row["mass_kg"] for row in station["T16_rows"] if row["id"] == "T16-04")
    lp_kg, ax_kg = (parts26[tag]["dry_kg"] for tag in ("GA_LP", "AX"))
    assert all(parts26[tag]["delta_kg"] == 0 for tag in ("GA_LP", "AX"))
    assert isclose(pilot_legacy["mass_kg"] + pilot_legacy["pilot_mass_kg"], ga_base_kg)
    station["accumulators"] = dict(
        T16_booked_LP_kg=pilot_legacy["mass_kg"], T16_booked_AX_kg=pilot_legacy["pilot_mass_kg"],
        T16_kg=ga_base_kg, T16_LP_part_no="3047174", T16_booked_AX_part_no="3047166",
        T16_circuit_AX_part_no="3047170", LP_design_kg=lp_kg, AX_design_kg=ax_kg,
        LP_catalogue_weight_disagreement_kg=lp_kg - pilot_legacy["mass_kg"],
        AX_legacy_to_actual_kg=ax_kg - pilot_legacy["pilot_mass_kg"],
        total_correction_kg=lp_kg + ax_kg - ga_base_kg,
        LP_design_part_no="3047174", AX_design_part_no="3047170",
        SAL_and_SAX_dry_kg=parts26["SAL_SAX"]["dry_kg"], SAL_SAX_booked_in="T16-08",
        source_legacy=sources["legacy_accumulators"]["url"],
        source_T26=sources["t26_inventory"]["url"],
        source_LP_part=sources["ax_lp"]["lp_url"],
        source_HYDAC_catalogue=sources["modern_accumulators"]["url"],
    )
    ga_correction_kg = station["accumulators"]["total_correction_kg"]
    station["reference_mass_checks"] = dict(
        A4VSO_package_delta_vs_T16_kg=drive_delta_kg, A4VSO_source=sources["t21_mass"]["url"],
        T21_machine_reference_kg=mass21["estimated_machine_with_station_delta_kg"],
        A4VSO_package_included_in_4942p65_kg=True,
    )
    machine = machine_ledger(station, criteria)
    station["card_station_base_kg"] = station["station_base_kg"]
    station["station_base_kg"] += drive_delta_kg + ga_correction_kg
    machine["station_booked_in_machine_with_GA_correction_kg"] = station["station_base_kg"]
    machine["machine_reference_plus_hydraulics_and_GA_kg"] = (
        machine["machine_reference_plus_hydraulics_kg"] + ga_correction_kg)
    machine["machine_A_corrected_kg_range"] = [value + ga_correction_kg for value in machine["machine_A_kg_range"]]
    for variant in machine["A_variants"].values():
        variant["machine_with_GA_correction_kg"] = variant["machine_before_lightening_kg"] + ga_correction_kg
    station["baseline_motor_kg"] = motor_pump_inputs["catalogs"]["motor"]["mass_kg"]
    station["installed_rows"] = installed_rows(station, parts26, t16_inputs, motor_pump_inputs, sources)
    assert isclose(fsum(row["mass_kg"] for row in station["installed_rows"]), station["station_base_kg"], abs_tol=1e-9)

    completed = subprocess.run([sys.executable, "-X", "utf8", "-B", str(HERE / "heat.py")],
                               cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8")
    heat = json.loads(completed.stdout)
    cooling_row_kg = next(row["mass_kg"] for row in station["T16_rows"] if row["id"] == "T16-05")
    cooler_hardware_kg = t16_inputs["revision"]["cooling"]["air_screen_and_mount_allowance_kg"]
    cooling = cooling_screen(heat, sources, cooling_row_kg, cooler_hardware_kg)
    tank = tank_screen(project, circuit, interlocks, selected, heat, sources, t16_inputs, station["station_base_kg"])
    measures, group_totals_kg = qualification(t16, t16_inputs, t21, selected, sources, tank, cooling, heat, circuit, station)
    cumulative_kg = dict(A=group_totals_kg["A"], A_B=group_totals_kg["A"] + group_totals_kg["B"],
                         A_B_C=fsum(group_totals_kg.values()))
    machine_scenarios = {
        key: {basis: [value - reduction for value in machine[basis]]
              for basis in ("machine_A_kg_range", "machine_A_corrected_kg_range")}
        for key, reduction in cumulative_kg.items()
    }
    reference = {tag: point["reference"] for tag, point in heat["cases"].items()}
    status = "STOP" if cumulative_kg["A"] < 170 else "PASS"
    station_t25_kg = station["station_base_kg"] - cumulative_kg["A"]
    metrics = dict(
        task="T-2.5", round=2, status=status, stop_reason="MASS_REDUCTION_BELOW_170_KG" if status == "STOP" else None,
        station_base_kg=station["station_base_kg"], station_card_base_kg=station["card_station_base_kg"],
        station_t25_kg=station_t25_kg, reduction_kg=cumulative_kg["A"],
        mass_acceptance_minimum_kg=170, mass_reduction_target_kg=230,
        group_reduction_kg=group_totals_kg, cumulative_reduction_kg=cumulative_kg,
        groups_B_and_C_basis="Известные оценки. C — верхняя оценка экономии при внешней воде, без остаточной массы арматуры и воды.",
        accumulators_correction_kg=ga_correction_kg,
        machine_A_kg_range=machine["machine_A_kg_range"],
        machine_A_corrected_kg_range=machine["machine_A_corrected_kg_range"],
        machine_A_after_groups_kg_range=machine_scenarios,
        heat_nominal_kW=heat["cases"]["nominal"]["heat_kW"], heat_adverse_kW=heat["cases"]["adverse"]["heat_kW"],
        cooling_required_kW=heat["cooling_required_kW"], cooling_dirty_kW=heat["cooling_dirty_kW"],
        cooling_reduction_kg=cooling["reduction_kg"], installed_kW=heat["installed_kW"],
        oil_volume_L=tank["nominal_oil_L"], T0_sizing_screen_minimum_L=tank["sizing_screen_minimum_initial_L"],
        TF_gross_L=tank["TF"]["gross_L"], TF_oil_L=tank["TF"]["initial_oil_L"],
        TF_nominal_gauge_bar=tank["TF"]["nominal_gauge_bar"], TF_half_band_bar=tank["TF"]["regulation_half_band_bar"],
        cycle_nominal_s=reference["nominal"]["cycle_s"], cycle_adverse_s=reference["adverse"]["cycle_s"],
        rms_kW=reference["nominal"]["rms_kW"], rms_adverse_kW=reference["adverse"]["rms_kW"],
        peak_kW=reference["nominal"]["peak_kW"],
    )
    return dict(task="T-2.5", metrics=metrics, station_mass=station, machine_mass=machine,
                tank=tank, heat=heat, cooling_selection=cooling, measures=measures,
                reference_model=t26["selected"], sources=sources)


def station_execution(result):
    metrics = result["metrics"]
    sources = result["sources"]
    tank_fields = ("nominal_oil_L", "density_kg_m3", "tank_dims_mm", "gross_L", "low_trip_L", "high_trip_L",
                   "sizing_screen_minimum_initial_L", "determining_screen", "suction", "deaeration", "thermal")
    heat_fields = ("air_C", "oil_limit_C", "flow_L_min", "branch_flow_L_min_range",
                   "fouling_fraction", "catalog_tolerance_fraction", "fan_kW", "circulation_kW",
                   "installed_kW", "worst_heat_kW", "heat_factor", "cooling_required_kW", "cooling_dirty_kW")
    return dict(
        schema_version=1, task="T-2.5", round=2, status=metrics["status"],
        recommended_execution="Эталонная станция T-2.6 схемы A с уточнённой ведомостью",
        mass_acceptance=False, mass_kg=metrics["station_t25_kg"], credited_reduction_kg=metrics["reduction_kg"],
        mass_rows=result["station_mass"]["installed_rows"],
        base_reconciliation=dict(
            T16_kg=result["station_mass"]["T16_kg"], T26_delta_kg=result["station_mass"]["T26_delta_kg"],
            T21_drive_delta_kg=result["station_mass"]["reference_mass_checks"]["A4VSO_package_delta_vs_T16_kg"],
            T16_GA_correction=result["station_mass"]["accumulators"],
            machine_mass_after_group_A_kg_range=metrics["machine_A_after_groups_kg_range"]["A"]["machine_A_corrected_kg_range"]),
        hydraulics=dict(
            reference_configuration=result["reference_model"], reference_cycle_source=sources["t26"]["url"],
            circuit_source=sources["circuit"]["url"], interlocks_source=sources["interlocks"]["url"],
            main_drive=dict(
                motor="OMEC OMT3-IE3-200L-4 IM B5", rated_kW=30, duty="S1",
                frequency_Hz=50, rated_rpm=1480, IP="IP55", IE="IE3", cooling="IC411",
                motor_source=sources["omec"]["url"], pump="Bosch Rexroth A4VSO 180 /30",
                regulator="DFE1Z, внешний пилот", pump_source=sources["a4vso"]["url"],
                main_pump_suction_port="SAE J518 3″",
                mount="IEC 200 B5 Ø400 / PCD350 / посадка Ø300, вал Ø55×110. Колокол к ISO 3019-2 NG180.",
            ),
            rapid_regeneration=dict(
                MF="2WRCE NG50 Double-B, два канала B", MBT="2WRCE NG40",
                bridge="LC25/LFA25 RB→RA, отсечка RB→бак", LP_delivery="LR/LRC → RA на выбросе",
                main_filling="ZSF NG100, свободное наполнение при прямом ходе. MF в TF на возврате.",
                stop="Снятие момента P1, ZU открыт, MF/MBT закрыты, SAL/SAX в сброс, BAL закрыт.",
                main_working_limit_bar=300, relief_limit_bar=315),
            accumulators=dict(
                LP=dict(model="HYDAC SB330 3047174", nominal_L=20, effective_gas_L=18.4, precharge_bar=28,
                        operating_bar_range=[38, 52], relief_bar=60, vessel_rated_bar=330, safety_block="SAL SAF32E Y"),
                AX=dict(model="HYDAC SB330 3047170", nominal_L=10, effective_gas_L=9.3, precharge_bar=100,
                        operating_bar_range=[120, 150], relief_bar=160, vessel_rated_bar=330, safety_block="SAX SAF32E Y"))),
        reservoirs=dict(
            T0={key: result["tank"][key] for key in tank_fields} | dict(
                shell_sheet_mm=4, source=sources["t16_inputs"]["url"],
                support="Рама 2×900 + 4×700, RHS 80×40×4. Отдельные опоры, подуровневые возвраты и перегородка."),
            TF=result["tank"]["TF"] | dict(
                vessel_basis="Мембранный, через двухсторонний регулятор N₂. Сохраняются LSF, PTF, BAL и штатный RTF.",
                relief="Goetze 455 DN65/100 F, 1,9 бар, отдельная линия TET, предел бака 3 бар.",
                source=sources["t26_replay"]["url"])),
        cooling=result["cooling_selection"]["baseline"] | {key: result["heat"][key] for key in heat_fields} | dict(
            circuit="Отдельная циркуляция PC 0,55 кВт, E1/E2 параллельно, FT1/FT2 и CD; предельный Δp ветви 1,25 бар.",
            physical_cooler_location="Унаследованная компоновка, совместный габарит с воздуховодом и зазорами подлежит проверке."),
        cycle=dict(nominal_s=metrics["cycle_nominal_s"], adverse_s=metrics["cycle_adverse_s"],
                   nominal_rms_kW=metrics["rms_kW"], adverse_rms_kW=metrics["rms_adverse_kW"], peak_kW=metrics["peak_kW"]),
        balance_of_measures=dict(A_credited_kg=metrics["group_reduction_kg"]["A"],
                                 B_conditional_kg=metrics["group_reduction_kg"]["B"],
                                 C_operator_upper_savings_kg=metrics["group_reduction_kg"]["C"]),
        open_items=[
            "Подтвердить растарировку T0, раздельные пути деаэрации, заглубление и давление на фланце S насоса.",
            "На безопасной остановке измерить ход, время разряда SAL/SAX, порядок WK и волну уровня.",
            "Подтвердить паспорт TF 80 л и совместимость корпуса MF Double-B, арматуры, колокола и опор.",
            "Взвесить станцию и проверить габарит, крепления и доступ на стадии компоновки."
        ],
    )


def main():
    result = calculate()
    gates = read_json("gates.t25.json")
    result["gates"] = {row["id"]: dict(status=row["status"], value=row["value"], unit=row["unit"])
                       for row in gates["gates"]}
    write_json("calc/T-2.5/results.json", result)
    write_json("metrics.json", result["metrics"])
    write_text("design/hydraulics/station.t25.yaml", yaml.safe_dump(station_execution(result), allow_unicode=True, sort_keys=False))
    write_text("report.md", render(result))
    assert "?" not in (ROOT / "report.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    main()
