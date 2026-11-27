"""Reconcile the corrected T-2.5 ledger and apply only explicit substitutions."""
from collections import Counter
from math import fsum, isclose, pi


def close_mass(actual, expected):
    return isclose(actual, expected, abs_tol=0.1, rel_tol=0)


def cylinder_volume_L(diameter_mm, length_m):
    return pi / 4 * diameter_mm**2 * length_m / 1000


def make_water_rows(cooling, inputs, sources):
    cat = cooling["selected"]
    spec = inputs["water_line"]
    od_mm, thickness_mm, length_m = spec["OD_mm"], spec["wall_mm"], spec["total_length_m"]
    bore_mm = od_mm - 2 * thickness_mm
    water_L = cylinder_volume_L(bore_mm, length_m)
    steel_L = cylinder_volume_L(od_mm, length_m) - water_L
    steel_kg = steel_L * spec["density_kg_m3"] / 1000
    water_kg = water_L * inputs["water_density_kg_m3"] / 1000
    oil_line = inputs["oil_local_line"]
    oil_fill_kg = cylinder_volume_L(oil_line["pipe_ID_mm"], oil_line["length_m"]) * inputs["oil_density_kg_m3"] / 1000
    parts = inputs["components"]

    def row(id_suffix, part, mass_kg, source, basis, category, kind="catalogue"):
        return {"id": "T25B-" + id_suffix, "part": part, "mass_kg": mass_kg,
                "source": sources[source]["url"], "basis": basis, "category": category, "mass_basis": kind}

    return [
        row("HX", cat["model"] + " с водой", cat["wet_with_water_kg"], "bowman_profile",
            "Сухой 21 кг и 3,8 л воды. Заполнение маслом учтено отдельной строкой.", "cooler"),
        row("HX_oil", "Масло в кожухе охладителя", cat["oil_fill_kg"], "bowman_profile",
            "4,8 л × плотность HLP46. Учтено сверх заправки T0 190 л.", "oil"),
        row("HX_mount", "Опоры GL180, крепёж и развязка вибраций", 4.0, "bowman_manual",
            "Две сборки примерно по 2 кг с опорными пластинами, M10, накладками и вибропрокладками.",
            "mount", "проектный резерв"),
        row("WV", "Danfoss EV220B 25 032U7125 EPDM NC", parts["valve_body_kg"], "water_valve",
            "Нетто корпуса без катушки.", "water"),
        row("WV_coil", "Катушка BB024DS, IP-разъём и крепёж", 0.6, "coil",
            "Резерв на катушку типоразмера BB, герметичный разъём и провод к клеммнику.", "water", "проектный резерв"),
        row("WS", "Spirax Sarco Fig 3616, DN40 PN16 mesh 40", parts["strainer_kg"], "strainer",
            "Масса типоразмера DN40. Сопрягаемые фланцы посчитаны с трубами.", "water"),
        row("WB", "Два шаровых крана DN40", 4.0, "task",
            "По 2 кг на полнопроходной резьбовой кран с ручкой. Фланцы границы отдельно.", "water", "проектный резерв"),
        row("WF", "ifm SM9500, расход и температура на возврате", parts["flowmeter_kg"], "water_flowmeter",
            "Паспортная масса DN40.", "water"),
        row("WT", "Pt100 на входе воды, гильза и два отбора давления аппарата", 1.2, "task",
            "0,6 кг на датчик с гильзой и по 0,3 кг на два измерительных порта с заглушками.",
            "water", "проектный резерв"),
        row("WP", "Трубопровод воды DN40 с заполнением", steel_kg + water_kg, "t16",
            f"2,0 м трубы 48,3×2 мм. Сталь {steel_kg:.3f} кг, вода {water_kg:.3f} кг.",
            "water", "масса по геометрии"),
        row("WI", "Фланцы границы и фильтра, фитинги, переходы и хомуты", 8.0, "task",
            "Четыре ответных фланца DN40 примерно по 1 кг, 4 кг на переходы, колена, опоры и отборы Δp фильтра.",
            "water", "проектный резерв"),
        row("WD", "Слив воды и ручной воздухоотводчик", 1.0, "bowman_manual",
            "Два малых клапана и отвод в нижней точке. Доступ с сервисной стороны.",
            "water", "проектный резерв"),
        row("WW", "Вода в арматуре и расходомере", 2.5, "task",
            "Резерв 2,5 л на полости DN40, грязевик и клапаны сверх трубы и аппарата.",
            "water", "проектный резерв"),
        row("PC_oil", "Ветка PC, переходы G1½, линии и контроль потока", 8.0, "circuit",
            "Резерв на 1,2 м трубы с проходом 50 мм, два перехода, крепления и малопотерные датчики. "
            "PC, CB, CD и общий FT остаются в T16-09.",
            "oil", "проектный резерв"),
        row("PC_fill", "Дополнительное масло в местных линиях PC", oil_fill_kg, "t16",
            "Заполнение 1,2 м при проходе 50 мм.", "oil", "масса по геометрии"),
        row("AO", "Присоединения воздушной опции и трасса кабеля", 9.0, "asa",
            "Резерв на два тройника, две глухие ответные части, крепёж, короткие отводы и кабельную подготовку.",
            "air_option_interface", "проектный резерв"),
    ]


def calculate(baseline, historical, baseline_metrics, t22i, cooling, measures, inputs, sources, criterion_kg):
    base_rows = baseline["mass_rows"]
    by_id = {row["id"]: row for row in base_rows}
    assert len(by_id) == len(base_rows)
    base_kg = fsum(row["mass_kg"] for row in base_rows)
    assert close_mass(base_kg, baseline["mass_kg"])
    assert close_mass(base_kg, baseline_metrics["station_t25_kg"])
    assert close_mass(base_kg, 1780.56)
    assert by_id["T25-ALP"]["mass_kg"] == 63 and by_id["T25-AX"]["mass_kg"] == 31
    assert baseline_metrics["accumulators_correction_kg"] == 30

    air_rows = [by_id["T25-E1_E2"], by_id["T25-E_hardware"]]
    assert close_mass(fsum(row["mass_kg"] for row in air_rows), 173.4)
    removed = list(air_rows)
    additions = make_water_rows(cooling, inputs, sources)
    cooling_additions_kg = fsum(row["mass_kg"] for row in additions)
    credited = [row for row in measures if row["status"] == "зачтено"]
    for measure in credited:
        assert measure["ledger_ids"] == ["T25-ALP"]
        lp = measure["evidence"]
        removed.append(by_id["T25-ALP"])
        additions.extend([
            {"id": "T25B-LP", "part": measure["measure"], "mass_kg": lp["catalogue_dry_kg"],
             "source": sources["lp_parker"]["url"], "replaces": "T25-ALP",
             "basis": "Сосуд 20 л / 330 бар, точный артикул " + lp["order_number"]},
            {"id": "T25B-LP_fit", "part": "Резерв на крепление и стыковку LP G2 с SAF32E",
             "mass_kg": lp["mount_and_connection_reserve_kg"], "source": sources["lp_parker_fasttrack"]["url"],
             "basis": "Два хомута и переходник/уплотнения. Резерв сверх имеющегося SAF32E."},
        ])

    removal_counts = Counter(row["id"] for row in removed)
    assert all(count == 1 for count in removal_counts.values())
    new_rows = [row for row in base_rows if row["id"] not in removal_counts] + additions
    assert len({row["id"] for row in new_rows}) == len(new_rows)
    assert all(row["mass_kg"] > 0 and row["source"] for row in new_rows)
    sum_kg = fsum(row["mass_kg"] for row in new_rows)
    removed_kg = fsum(row["mass_kg"] for row in removed)
    added_kg = fsum(row["mass_kg"] for row in additions)
    assert isclose(sum_kg, base_kg - removed_kg + added_kg, abs_tol=1e-9)

    ga_kg = baseline_metrics["accumulators_correction_kg"]
    masses = {}
    for key, variant in t22i["variants"]["nose_x225"]["mass"].items():
        before = variant["machine_before_station_kg"]
        corrected = before + ga_kg
        assert close_mass(corrected, historical["A_variants"][key]["machine_with_GA_correction_kg"])
        machine_kg = corrected - base_kg + sum_kg
        masses[key] = {
            "t22i_before_station_kg": before, "t25_corrected_kg": corrected, "t25b_kg": machine_kg,
            "missing_to_5000_kg": max(0, machine_kg - criterion_kg),
            "missing_to_5080_kg": max(0, machine_kg - 5080),
        }
    original_range = sorted(row["t25_corrected_kg"] for row in masses.values())
    target = baseline_metrics["machine_A_corrected_kg_range"]
    assert close_mass(original_range[0], target[0]) and close_mass(original_range[-1], target[-1])
    new_range = sorted(row["t25b_kg"] for row in masses.values())
    remaining_group_B_potential_kg = fsum(
        -row["t25_potential_delta_kg"] for row in measures if row["status"] != "зачтено"
    )
    return {
        "remaining_uncredited_T25_group_B_potential_kg": remaining_group_B_potential_kg,
        "machine_high_with_remaining_T25_estimates_kg": new_range[-1] - remaining_group_B_potential_kg,
        "station_t25_kg": base_kg, "station_t25b_kg": sum_kg, "station_delta_kg": sum_kg - base_kg,
        "mass_rows": new_rows, "removed_rows": removed, "added_rows": additions,
        "cooling_additions_kg": cooling_additions_kg,
        "cooling_net_saving_kg": 173.4 - cooling_additions_kg,
        "water_hardware_kg": fsum(row["mass_kg"] for row in additions if row.get("category") == "water"),
        "credited_measures_kg": fsum(row["credited_saving_kg"] for row in credited),
        "credited_measures": [row["measure"] for row in credited],
        "t25_machine_A_corrected_kg_range": [original_range[0], original_range[-1]],
        "machine_A_kg_range": [new_range[0], new_range[-1]], "machine_A_variants": masses,
        "mass_acceptance": new_range[-1] <= criterion_kg,
        "missing_to_5000_kg": max(0, new_range[-1] - criterion_kg),
        "missing_to_5080_kg": max(0, new_range[-1] - 5080),
    }
