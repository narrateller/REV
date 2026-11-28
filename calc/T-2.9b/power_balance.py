"""Trace station installed ratings through T-1.6, T-2.6 and T-2.5b/c."""
import json
from math import fsum

from build_scheme import DESIGN, ROOT, read


def calculate(pc_kW=1.5):
    t16 = json.loads((ROOT / "calc/T-1.6/results.json").read_text(encoding="utf-8"))
    original = t16["heat_balance"]["cooling"]["installed_breakdown_kW"]
    t26 = read(ROOT / "calc/T-2.6/sources.yaml")
    baseline = read(DESIGN / "station.t25c.yaml")
    base_install_kW = baseline["cooling"]["installed_base_kW"]
    water_kW = baseline["cooling"]["installed_water_electrical_reserve_kW"]
    result_t26 = read(ROOT / "calc/T-2.6/params/params.t26a.yaml")["drive"]["installed_kW"]
    baseline_t26 = read(ROOT / "calc/T-2.6/params/params.t26_base.yaml")["drive"]["installed_kW"]
    legacy_margin_kW = round(baseline_t26 - fsum(original.values()), 3)

    def row(consumer, kW, source, basis):
        return {"consumer": consumer, "installed_kW": kW, "source": source, "basis": basis}

    study = t26["study"]
    added_coils_kW = study["added_regen_coils_count"] * t26["catalogs"]["pilot_coil"]["power_W_per_coil"] / 1000
    added_controls_kW = study["aux_controls_allowance_W"] / 1000
    original_controls_kW = original["controls_and_valves"]
    reserve = [
        row("Дозатор", original["dosing"], "calc/T-1.6/results.json#heat_balance.cooling.installed_breakdown_kW",
            "Проектная мощность отдельного привода."),
        row("Пилотные катушки регенерации RG/RT", added_coils_kW, t26["catalogs"]["pilot_coil"]["url"],
            "RE 23178, 2 × 30 Вт в T-2.6/sources.yaml."),
        row("Дополнительные датчики и управление", added_controls_kW, "calc/T-2.6/sources.yaml#study",
            "Групповой допуск 24 Вт; детализация по каналам открыта."),
        row("Нераспределённый резерв ГК", round(original_controls_kW + legacy_margin_kW, 3),
            "calc/T-1.6/results.json#heat_balance.cooling.installed_breakdown_kW; calc/T-2.6/params/params.t26_base.yaml",
            f"{original_controls_kW:.3f} кВт T-1.6 controls_and_valves без разбивки по приборам и "
            f"{legacy_margin_kW:.3f} кВт дельты до базового входа T-2.6. Сохраняется целиком."),
    ]
    rebuilt_base_kW = fsum((original["main_motor"], original["cooler_circulation"], water_kW,
                            *(item["installed_kW"] for item in reserve)))
    assert abs(rebuilt_base_kW - base_install_kW) < 1e-9
    assert abs(result_t26 - baseline_t26 - added_coils_kW - added_controls_kW) < 1e-9
    air_kW = baseline["air_option"]["fan_kW"]
    installed_kW = round(base_install_kW - original["cooler_circulation"] + pc_kW, 3)
    installed_air_kW = round(installed_kW + air_kW, 3)
    water_coil_kW = .018  # BB024DS, T-2.5b/sources.yaml.
    return {
        "historical_base_kW": base_install_kW, "historical_PC_kW": original["cooler_circulation"],
        "reserve_kW": round(fsum(item["installed_kW"] for item in reserve), 3),
        "reserve_breakdown": reserve,
        "base_rows": [
            row("M1", original["main_motor"], "design/hydraulics/station.t25c.yaml#hydraulics.main_drive", "ABB 30 кВт."),
            row("PC", pc_kW, "DECISIONS.md#D-OP-22", "Номинал двигателя в расчётном бюджете."),
            row("Катушка водяного клапана", water_coil_kW, "calc/T-2.5b/sources.yaml",
                "Danfoss BB024DS 18 Вт."),
            row("Датчики и арматура воды", round(water_kW - water_coil_kW, 3), "calc/T-2.5b/sources.yaml",
                "Остаток бюджета воды 35 Вт, включая расходомер и интерфейсы."),
            *reserve,
        ],
        "zero_separate_additions": [
            row("PX/PXA", 0, "design/hydraulics/T-2.9_circuit.yaml#P1",
                "Механический тандем от M1. Его валовая нагрузка в G-CYCLE."),
            row("Вентилятор M1", 0, "design/hydraulics/station.t25c.yaml#hydraulics.main_drive",
                "Штатное охлаждение двигателя; отдельного электродвигателя в ведомости нет."),
            row("Нагреватель", 0, "design/hydraulics/T-2.9_circuit.yaml",
                "Отдельного нагревателя нет в составе. Предлагаемый прогрев на разгруженном P1."),
        ],
        "air_rows": [
            row("Вентиляторы E1, E2", air_kW, "calc/T-2.5b/sources.yaml#asa", "2 × ASA 0,75 кВт."),
        ],
        "installed_kW": installed_kW, "installed_with_air_option_kW": installed_air_kW,
        "base_limit_kW": 34.2, "air_limit_kW": 35.1,
        "power_budget_pass": installed_kW <= 34.2 and installed_air_kW <= 35.1,
    }


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=False, indent=2))

