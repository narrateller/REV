"""Reconcile the scheme-A component changes to the T-2.5c station ledger."""
import csv

from build_scheme import ROOT, DESIGN, read, write


def calculate(circuit):
    station = read(DESIGN / "station.t25c.yaml")
    config = read(ROOT / "calc/T-2.9/sources.yaml")
    e = circuit["elements"]
    catalogue = config["catalogs"]
    by_id = {item["id"]: item for item in station["mass_rows"]}
    with (ROOT / "calc/T-2.6/inventory.csv").open(encoding="utf-8-sig", newline="") as stream:
        inventory = {item["id"]: item for item in csv.DictReader(stream, delimiter=";")}

    def item(tag, old, new, delta_kg, url, note):
        return {"item": tag, "before": old, "after": new, "delta_kg": delta_kg,
                "source": url, "basis": note}

    rows = [
        item("LG", "нет отдельной ступени VG", e["LG"]["series"], float(inventory["LR"]["dry_kg"]),
             inventory["LR"]["source_url"], "Масса NG32; корпус и линия в отдельном открытом резерве."),
        *[item(tag, "нет", e[tag]["series"], .42, catalogue["SUN_CXHA"]["url"],
               "Масса вставки; корпус в открытом резерве.") for tag in ("RGC", "GHC", "LGC")],
        item("XZD", "ТЗ внешний пилот, без отдельной строки", e["XZD"]["series"], .36,
             catalogue["SUN_PRFB"]["url"], "Масса редуктора. Переходник в открытом резерве."),
        item("ALP", "Parker 49 + 3 кг", "Parker 49 + 3 кг, 17,8 л", 0.,
             by_id["T25B-LP"]["source"], "Решение ГК, корпус и присоединение прежние."),
        item("PC / CB", "резерв T16-09", "решение оператора", 0.,
             by_id["T16-09"]["source"], "Состав и установленная мощность в ведомости сохраняются."),
        item("WCP/WCF/ACP/ACF/CAPA/CAPB", "T25B-AO 9 кг", "CP/CF, отсечки и заглушки", None,
             by_id["T25B-AO"]["source"], "Сверить набор с резервом 9 кг; дополнительные кг вне резерва неизвестны."),
        item("PF", "номинально 1 м в T-2.6", "цель 0,5 м в T-2.3", 0.,
             inventory["cap_fill_pipe"]["source_url"], "Экономия сухой трубы показывается отдельно, компоновка не подтверждена."),
        item("P1 / PX / PXA", "T25-P1 102 кг без проходного привода + T16-20 23 кг", "A4VSO180 с U04, тандем",
             None, config["sources"]["a4vso_through"]["url"], "Взвесить сборку и исключить дублирование T25-P1_DFE1Z."),
        item("XGLG", "нет", e["XGLG"]["series"], None,
             read(ROOT / "calc/T-1.6/sources.yaml")["catalogs"]["VEI_NC"]["url"], "Точная сборка, пилот и присоединение к LG."),
        item("RVGH", "нет", e["RVGH"]["series"], None,
             catalogue["SUN_RBAA"]["url"], "Термозащита, настройка и корпус."),
        item("PTZ / RVZ", "без отдельной строки", "контроль и защита Z", None,
             catalogue["DFE1Z"]["url"], "Масса деталей и отдельной линии TZ после компоновки."),
        item("ZRG / ZRT", "T26-RA_RB_sensors контролируют давление", "контроль положения кромок",
             None, inventory["regen_valves"]["source_url"], "Подтвердить способ контроля и дельту."),
        item("ZA1/ZA2/ZB1/ZB2", "4 условных датчика засовов", "4 AZ16 на носе и его мишенях", None,
             config["sources"]["nose_switch"]["url"], "0,48 кг брутто датчиков без мишеней; сравнить монтаж на машине."),
        item("RVA", "DB30, 315 бар в ветви A", "требуется 139 бар при полном расходе", 0.,
             read(ROOT / "calc/T-1.6/sources.yaml")["catalogs"]["DB"]["url"], "Пружина того же типоразмера, P–Q открыто."),
        item("LG block and lines", "нет", "блок шибера, PGH и XLG", None,
             inventory["LR"]["source_url"], "Обмер коллектора, труб и масла; детали по КД."),
        item("TF gas regulator", "T25-TF_dry", "двухсторонний, целевой 811 л/мин", None,
             by_id["T25-TF_dry"]["source"], "Сверить фактическое наполнение/выпуск азота с резервом."),
    ]
    dry_delta_kg = sum(row["delta_kg"] for row in rows if row["delta_kg"] is not None)
    # Only the identified additions are booked. Unmeasured parts keep null
    # rather than disappearing into the previous lump-sum station reserve.
    base = station["mass_kg"]
    current = base + dry_delta_kg
    versions = station["mass_reconciliation_t25c"]["machine_A_variants"]
    machines = {key: {"t25c_kg": values["t25c_kg"], "t29_accounted_kg": values["t25c_kg"] + dry_delta_kg}
                for key, values in versions.items()}
    length_change_m = circuit["lines"]["PF"]["target_length_m"] - float(inventory["cap_fill_pipe"]["length_m"])
    potential_pf_dry_ev_kg = length_change_m * float(inventory["cap_fill_pipe"]["dry_kg"])
    result = {
        "mass_delta": rows, "station_base_kg": base, "station_mass_delta_kg": dry_delta_kg,
        "station_kg": current, "machine_A_variants": machines,
        "machine_A_kg_range": [min(v["t29_accounted_kg"] for v in machines.values()),
                               max(v["t29_accounted_kg"] for v in machines.values())],
        "machine_limit_kg": station["mass_reconciliation_t25c"]["mass_limit_kg"],
        "potential_PF_dry_saving_kg_unbooked": -potential_pf_dry_ev_kg,
        "station_delta_after_unbooked_PF_saving_kg": dry_delta_kg + potential_pf_dry_ev_kg,
        "unverified_items": [row["item"] for row in rows if row["delta_kg"] is None],
    }
    for row in rows:
        if row["delta_kg"] and row["delta_kg"] > 0:
            station["mass_rows"].append({
                "id": f"T29-{row['item']}", "part": row["after"], "mass_kg": row["delta_kg"],
                "source": row["source"], "basis": row["basis"],
            })
    station["task"] = "T-2.9"
    station["status"] = "STOP_MASS"
    station["mass_kg"] = current
    station["mass_is_provisional"] = True
    station["credited_reduction_kg"] -= dry_delta_kg
    station["mass_reconciliation_t29"] = result
    station["hydraulics"]["main_drive"]["through_drive_status"] = "U04 preliminary; mass delta pending"
    for row in station["mass_rows"]:
        if row["id"] == "T25-P1":
            row["part"] = "Rexroth A4VSO180 /30, 102 кг база для U04, дельта привода открыта"
    write(DESIGN / "station.t29.yaml", station)
    return result
