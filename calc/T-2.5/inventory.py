"""Reconcile the prescribed station ledger without summing existing T-2.6 parts twice."""

import csv
from math import fsum, isclose


def calculate(root, t16, selected26):
    source16 = "calc/T-1.6/results.json#mass.station_rows"
    source26 = "calc/T-2.6/inventory.csv"
    base_rows = [
        dict(id=f"T16-{index:02}", part=row["node"], mass_kg=row["round2_kg"],
             source=source16, basis=row["source"])
        for index, row in enumerate(t16["mass"]["station_rows"], 1)
    ]
    station16_kg = fsum(row["mass_kg"] for row in base_rows)
    with (root / source26).open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream, delimiter=";"))
    details = selected26["mass"]["purchased_and_custom_rows"]
    assert set(details) == {row["id"] for row in csv_rows}
    assert len(details) == len(csv_rows)
    delta_rows = []
    for row in csv_rows:
        detail = details[row["id"]]
        assert isclose(float(row["delta_kg"]), detail["delta_kg"], abs_tol=0.00000051)
        source = row["source_url"]
        if source.startswith("../T-1.6/"):
            source = str((root / "calc/T-2.6" / source).resolve().relative_to(root)).replace("\\", "/")
        delta_rows.append(dict(id="T26-" + row["id"], part=row["model"], qty=int(row["qty"]),
                               dry_kg=detail["dry_kg"], oil_kg=detail.get("oil_kg", 0.0),
                               mass_kg=detail["delta_kg"], source=source, basis=row["basis"],
                               ledger_source=source26))
    delta26_kg = fsum(row["mass_kg"] for row in delta_rows)
    csv_roundoff_kg = fsum(float(row["delta_kg"]) for row in csv_rows) - delta26_kg
    assert isclose(station16_kg, t16["mass"]["station_round2_kg"], abs_tol=1e-9)
    assert isclose(delta26_kg, selected26["mass"]["added_hydraulics_kg"], abs_tol=1e-9)
    return dict(T16_kg=station16_kg, T26_delta_kg=delta26_kg, csv_roundoff_kg=csv_roundoff_kg,
                station_base_kg=station16_kg + delta26_kg,
                T16_rows=base_rows, T26_rows=delta_rows)


def installed_rows(station, parts26, t16_inputs, t21_inputs, sources):
    rows = []

    def add(tag, part, mass_kg, source, origin, **details):
        rows.append(dict(id=tag, part=part, mass_kg=mass_kg, source=source, replaces_or_adjusts=origin, **details))

    assembly_adjustments = {
        "T16-07": "MF NG50, MBT NG40, LR NG32 и остальные 2WRCE; штатные массы корпусов относятся к ведомости T-1.6.",
        "T16-08": "В том числе SAF32E SAL/SAX 24,8 кг за пару до адаптеров. T-2.6 считает ранний корпус MF 32 кг уже учтённым. Привязку корпуса к этой строке проверить при деталировке.",
        "T16-09": "F1, FX, F2, линии станции, вспомогательные насосы и PC. Строка проектного резерва.",
        "T16-12": "Две местные линии наполнения 133×4 и 108×4, крепёж по унаследованной строке.",
        "T16-13": "Седла плавания и подпитки, включая MC по ведомости T-2.6 без добавочной массы.",
        "T16-14": "LC/LFA NG40, седло регенерации.",
        "T16-15": "Goetze 455 DN65/100 F, уставка 1,9 бар.",
        "T16-16": "Контролируемый разгрузчик ZU/ZUP, адаптер, отдельный дренаж.",
        "T16-17": "Крышки LFA NG50 и их крепления.",
        "T16-18": "Фланец штатного RTF и опоры возврата.",
        "T16-19": "Аварийные клапаны ME1/ME2/MEB и раздельные возвраты.",
        "T16-20": "Тандем PX/PXA и контроль состояний.",
    }
    motor_pump_cat = t21_inputs["catalogs"]
    for row in station["T16_rows"]:
        tag = row["id"]
        if tag == "T16-01":
            add("T25-M1", "OMEC OMT3-IE3-200L-4 B5", motor_pump_cat["motor"]["mass_kg"],
                sources["omec"]["url"], tag)
            add("T25-P1", "Rexroth A4VSO180 /30 без проходного вала", motor_pump_cat["rexroth"]["basic_mass_kg"],
                sources["a4vso"]["url"], tag)
            add("T25-P1_DFE1Z", "Резерв на регулятор DFE1Z и адаптер",
                t21_inputs["engineering"]["dfe1z_adapter_and_regulator_allowance_kg"],
                sources["t21_mass"]["url"], tag)
        elif tag == "T16-04":
            for key, tag25, name in (("GA_LP", "T25-ALP", "LP"), ("AX", "T25-AX", "AX")):
                part = parts26[key]
                source = sources["ax_lp"]["lp_url"] if key == "GA_LP" else sources["modern_accumulators"]["url"]
                add(tag25, name + " — " + part["model"], part["dry_kg"], source, tag,
                    pressure_bar=part["pressure_bar"])
        elif tag == "T16-05":
            cooler = t16_inputs["catalogs"]["ASA0567"]
            add("T25-E1_E2", "2 × ASA0567AA47 0,75 кВт 50 Гц", 2 * cooler["mass_kg"], sources["asa_ports"]["url"], tag,
                qty=2, unit_mass_kg=cooler["mass_kg"])
            add("T25-E_hardware", "Датчики ветвей, крепления и съёмные маты",
                t16_inputs["revision"]["cooling"]["air_screen_and_mount_allowance_kg"], row["source"], tag)
        elif tag == "T16-11":
            part = parts26["TF"]
            add("T25-TF_dry", "TF 80 л, разделитель и регулятор", part["dry_kg"], sources["t26_inventory"]["url"], tag,
                basis="Проектный резерв, масса сосуда и мембраны уточняется заказом.")
            add("T25-TF_oil", "Масло TF 55 л", part["oil_kg"], sources["t26_inventory"]["url"], tag)
        else:
            details = dict(row)
            if tag in assembly_adjustments:
                details["composition"] = assembly_adjustments[tag]
            if tag == "T16-06":
                details["composition"] = "RHS 80×40×4, опоры, колокол/муфта и крепёж в ведомости."
            rows.append(details)
    for row in station["T26_rows"]:
        if row["mass_kg"] and row["id"] != "T26-TF":
            details = dict(row)
            if row["id"] == "T26-MF_housing":
                details["composition"] = "Разность 48,3246 и 32 кг. Базовый корпус учтён в смете узла."
            rows.append(details)
    return rows
