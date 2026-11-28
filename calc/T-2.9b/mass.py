"""Generate the revision ledger and retain separate allowances for unresolved items."""
import csv
from math import fsum, pi

from build_scheme import DESIGN, ROOT, HERE, read, write


def calculate(pc, power):
    station = read(DESIGN / "station.t25c.yaml")
    src = read(HERE / "sources.yaml")
    configs = src["mass_t29b_inputs"]
    urls = src["sources"]
    catalogs = src["catalogs"]
    pc_config = src["pc_t29b_inputs"]
    mass_rows = {item["id"]: item for item in station["mass_rows"]}
    original_station_kg = fsum(item["mass_kg"] for item in mass_rows.values())
    assert abs(original_station_kg - station["mass_kg"]) < 1e-8

    def change(tag, before, after, old_kg, new_kg, source, basis, power_delta_kW=0):
        return {"tag": tag, "before": before, "after": after, "base_kg": old_kg, "revision_kg": new_kg,
                "delta_kg": round(new_kg-old_kg, 6), "installed_delta_kW": power_delta_kW,
                "source": source, "basis": basis}

    old_pc_kg = src["pc_catalogue_inputs"]["kf125_pump_mass_kg"]
    old_motor_kg = configs["inherited_PC_motor_proxy_kg"]
    mass_rows["T16-09"]["mass_kg"] -= old_pc_kg + old_motor_kg
    mass_rows["T16-09"]["basis"] += (
        " Остаток прежнего резерва после аналитического выделения KF125 и двигателя. "
        "Происхождение массы PC 0,55 кВт в исторической сборке подлежит сверке."
    )
    mass_rows["T25B-LP"]["effective_shell_L"] = 17.8
    mass_rows["T25-P1"]["through_drive"] = "U04 (масса дельты открыта)"
    additions = [
        change("PC", "KF125", pc_config["pump_model"], old_pc_kg, pc_config["pump_mass_kg"],
               urls["pc_kf180"]["url"], "С. 23, масса корпуса с портом SAE без D-клапана. Кандидат."),
        change("MPC", "0,55 кВт, вес из прокси ABB", pc_config["motor_model"], old_motor_kg,
               pc_config["motor_mass_kg"], urls["pc_abb_ie3_6p"]["url"],
               "С. 91, 6 полюсов IE3. Базовая строка T16-09, прокси в sources.yaml.", 0.95),
        change("PC-VFD", "Нет отдельной строки", configs["vfd_model"], 0, configs["vfd_mass_kg"],
               urls["pc_vfd"]["url"], "Масса ПЧ. Потери и снабжение энкодером в КД."),
        change("RGC", "Нет отдельной строки", "CXHAXAN", 0, configs["CXHA_kg"],
               catalogs["SUN_CXHA"]["url"], "Каталожная масса вставки."),
        change("RGC-BODY", "Нет отдельной строки", "IAX/S, T-16A G1, 350 бар", 0, configs["RGC_body_kg"],
               urls["rgc_body"]["url"], "Каталожная масса корпуса-кандидата. Сверить потери при 222 л/мин."),
        change("XZD", "Внешний пилот без отдельной строки", "PRFB-CBN", 0, configs["PRFB_kg"],
               catalogs["SUN_PRFB"]["url"], "Масса вставки T-2A."),
        change("PTZ", "Нет отдельной строки", "ifm PT5402", 0, configs["PTZ_kg"],
               urls["ptz_ifm"]["url"], "Масса датчика-кандидата без переходника."),
        change("RVZ", "Нет отдельной строки", "Sun RDBA, пружина D", 0, configs["RVZ_kg"],
               urls["rvz_sun"]["url"], "Масса вставки-кандидата. Настройка P–Q ≤ 50 бар и корпус открыты."),
    ]
    for item in additions:
        station["mass_rows"].append(
            {"id": f"T29B-{item['tag']}", "part": item["after"], "mass_kg": item["revision_kg"],
             "source": item["source"], "basis": item["basis"]}
        )

    removals = [
        ("LG", 15.6, "check_circuit: подача VG от P1"),
        ("GHC", .42, "HP подаёт к VG напрямую"),
        ("LGC", .42, "ветка LP→VG снята"),
        ("XGLG", None, "пилот LG снят"),
        ("RVGH", None, "карман GH за отсечкой снят"),
        ("LG block and lines", None, "LG0, XLG, GH и их отдельный блок сняты"),
    ]
    removed = [{"tag": tag, "mass_t29_kg": value, "source": "calc/T-2.9/circuit_changes.csv",
                "basis": reason} for tag, value, reason in removals]

    open_rows = []
    for item in configs["pending"]:
        row = dict(item)
        if "solid_block_mm" in row:
            x, y, z = row["solid_block_mm"]
            row["forecast_extra_kg_upper"] = round(x * y * z * configs["steel_density_kg_m3"] * 1e-9, 3)
        if "solid_cylinder_mm" in row:
            OD_mm, length_mm = row["solid_cylinder_mm"]
            row["forecast_extra_kg_upper"] = round(pi / 4 * OD_mm**2 * length_mm
                                                   * configs["steel_density_kg_m3"] * 1e-9, 3)
        open_rows.append(row)
    additional_screen_kg = fsum(item["forecast_extra_kg_upper"] for item in open_rows)
    mass_kg = fsum(item["mass_kg"] for item in station["mass_rows"])
    delta_kg = mass_kg - original_station_kg
    assert abs(delta_kg - fsum(item["delta_kg"] for item in additions)) < 1e-8
    variants = station["mass_reconciliation_t25c"]["machine_A_variants"]
    limit_kg = station["mass_reconciliation_t25c"]["mass_limit_kg"]
    machines = {
        name: {"t25c_kg": row["t25c_kg"], "t29b_kg": row["outside_station_kg"] + mass_kg,
               "over_5000_kg": row["outside_station_kg"] + mass_kg - limit_kg,
               "upper_with_project_allowances_kg": row["outside_station_kg"] + mass_kg + additional_screen_kg}
        for name, row in variants.items()
    }
    with (ROOT / "calc/T-2.6/inventory.csv").open(encoding="utf-8-sig", newline="") as stream:
        pf = next(item for item in csv.DictReader(stream, delimiter=";") if item["id"] == "cap_fill_pipe")
    pf_saving_kg = .5 * (float(pf["dry_kg"]) + float(pf["oil_kg"]))
    alternative_delta_kg = delta_kg - (
        pc["preferred_candidate"]["pump_and_motor_mass_kg"] - configs["alternate_KF112_and_motor_kg"]
    )
    mass = {
        "station_t25c_kg": original_station_kg,
        "station_kg": mass_kg, "station_delta_vs_t25c_kg": delta_kg,
        "station_upper_with_project_allowances_kg": mass_kg + additional_screen_kg,
        "station_delta_limit_kg": 10, "station_delta_pass": delta_kg <= 10,
        "mass_revision_vs_t25c": additions, "removed_vs_t29": removed,
        "mass_unresolved_extra_upper_kg": additional_screen_kg, "unresolved_mass_rows": open_rows,
        "machine_A_variants": machines, "machine_limit_kg": limit_kg,
        "machine_A_kg_range": [min(row["t29b_kg"] for row in machines.values()),
                               max(row["t29b_kg"] for row in machines.values())],
        "alternatives": {
            "TF_prelength_saving_if_inherited_1m_verified_kg": pf_saving_kg,
            "KF180_delta_after_unbooked_PF_saving_kg": delta_kg - pf_saving_kg,
            "KF112_with_1p5kW_delta_if_qualified_kg": alternative_delta_kg,
        },
    }
    station.update(task="T-2.9b", status="HOLD_PC_AND_MASS", mass_acceptance="STOP_MASS",
                   mass_kg=mass_kg, mass_is_provisional=True, mass_reconciliation_t29b=mass)
    station["credited_reduction_kg"] -= delta_kg
    station["cooling"].update(
        installed_base_kW=power["installed_kW"],
        installed_with_air_option_kW=power["installed_with_air_option_kW"],
        pc_candidate=pc["preferred_candidate"],
        pc_status=pc["status"],
        installed_power_breakdown=power["base_rows"],
    )
    cooling = station["cooling"]
    cooling["historical_oil_pressure_t25c"] = cooling["oil_pressure"]
    candidate = pc["preferred_candidate"]
    cooling["oil_pressure"] = {
        "status": pc["status"], "pc_motor_kW": candidate["motor_kW"],
        "max_hot_dp_bar": candidate["dp_hot_bar_max"],
        "shaft_required_kW_upper": candidate["shaft_kW_hot_max_bound"],
        "cb_setpoint_bar": None, "cb_candidate_target_bar": candidate["cb_crack_target_bar"],
        "operating_points": candidate["hot_operating_points"],
    }
    return station, mass


def generate(pc, power, gate_row):
    station, mass = calculate(pc, power)
    station["cycle"] = gate_row
    write(DESIGN / "station.t29b.yaml", station)
    return mass

