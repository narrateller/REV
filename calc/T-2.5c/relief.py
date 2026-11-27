"""Screen TF relief capacity at the unchanged setting and at full design inflow."""

from math import pi, sqrt


def capacity(ideal_L_min, diameter_mm, viscosity_mm2_s):
    # Re = (Q/A) d / nu. LESER 7.4.6-2 gives Kv = (1 + 170/Re)^(-1/2).
    # From Q = Q_ideal * Kv(Q), the positive root solves Q² + c*Q = Q_ideal².
    diameter_m = diameter_mm / 1000
    area_m2 = pi * diameter_m**2 / 4
    re_per_L_min = diameter_m / (60000 * area_m2 * viscosity_mm2_s * 1e-6)
    c_L_min = 170 / re_per_L_min
    corrected_L_min = (sqrt(c_L_min**2 + 4 * ideal_L_min**2) - c_L_min) / 2
    return {"ideal_L_min": ideal_L_min, "reynolds": re_per_L_min * corrected_L_min,
            "viscosity_Kv": corrected_L_min / ideal_L_min, "corrected_L_min": corrected_L_min}


def qualify(spec, circuit, previous, oil_density_kg_m3, nominal_tf_bar):
    valve = circuit["elements"]["RTF"]
    prior = previous["evidence"]
    required_L_min = prior["max_gross_TF_inlet_L_min"]
    set_bar = valve["setpoint"]["crack_bar"]
    relieving_bar = set_bar * (1 + spec["overpressure_fraction"])
    backpressure_bar = prior["backpressure_bar"]
    net_bar = relieving_bar - backpressure_bar
    cap_642_water_L_min = spec["goetze_642_water_m3_h"] * 1000 / 60
    ideal_642_L_min = cap_642_water_L_min * sqrt(
        net_bar / (spec["goetze_642_water_set_bar"] * (1 + spec["overpressure_fraction"]))
        * spec["water_density_kg_m3"] / oil_density_kg_m3
    )
    cold_mm2_s = spec["cold_viscosity_mm2_s"]
    ideal_velocity_m_s = sqrt(2 * net_bar * 1e5 / oil_density_kg_m3)

    def screen_goetze(series):
        diameter_mm = spec[f"goetze_{series}_orifice_mm"]
        area_m2 = pi * (diameter_mm / 1000)**2 / 4
        ideal_L_min = area_m2 * spec[f"goetze_{series}_Kdr"] * ideal_velocity_m_s * 60000
        return capacity(ideal_L_min, diameter_mm, cold_mm2_s)

    retained = screen_goetze("455")
    one_642 = capacity(ideal_642_L_min, spec["goetze_642_orifice_mm"], cold_mm2_s)
    pair_642_L_min = 2 * one_642["corrected_L_min"]
    triple_642_L_min = 3 * one_642["corrected_L_min"]
    triple_851_L_min = 3 * screen_goetze("851")["corrected_L_min"]
    assert pair_642_L_min < required_L_min < triple_642_L_min
    header_ID_mm = circuit["lines"][valve["ports"]["T"]]["DN_mm"]
    header_m_s = required_L_min / (60000 * pi * (header_ID_mm / 1000)**2 / 4)
    header_dyn_bar = oil_density_kg_m3 * header_m_s**2 / 2e5
    return {
        "credited": False,
        "reason": (
            "Пара 642 DN65 не покрывает приток. Для тройки расчёт дросселирования даёт запас, "
            "но не подтверждены совместное открытие при 1,9 бар, допустимое противодавление "
            "и масса фланцевого коллектора с опорами. Для LESER нет согласованного исполнения клапана и обвязки."
        ),
        "source_ids": ["circuit", "baseline_results", "goetze_455", "goetze_455_install", "goetze_642", "goetze_642_install",
                       "goetze_851", "leser_441", "leser_engineering", "iso_4126", "hlp46"],
        "set_bar": set_bar,
        "TF_design_bar": valve["p_design_bar"],
        "TF_nominal_gauge_bar": nominal_tf_bar,
        "relieving_bar": relieving_bar,
        "backpressure_budget_bar": backpressure_bar,
        "cold_screen_C": spec["cold_screen_C"],
        "cold_screen_viscosity_mm2_s": cold_mm2_s,
        "cold_screen_qualification": "0 °C и 580 мм²/с как сценарий T-2.5 для выбранного HLP46. Нижний допуск пуска и партия масла требуют подтверждения.",
        "required_L_min": required_L_min,
        "TET_nominal_header_ID_screen_mm": header_ID_mm,
        "TET_velocity_at_required_m_s": header_m_s,
        "TET_dynamic_head_at_required_bar": header_dyn_bar,
        "TET_max_total_loss_coefficient_at_zero_static_head": backpressure_bar / header_dyn_bar,
        "retained": {"model": valve["series"], "original_booked_L_min": valve["Q_L_min"],
                     "qualified_capacity_L_min": None, "screen": retained,
                     "metal_bellows_backpressure_limit_bar": spec["goetze_455_bellows_backpressure_fraction"] * set_bar,
                     "exact_balanced_bellows_in_baseline_confirmed": False},
        "goetze_642_one": one_642,
        "goetze_642_pair_screen_L_min": pair_642_L_min,
        "goetze_642_pair_t25b_screen_L_min": prior["calculated_HLP46_pair_L_min"],
        "goetze_642_triple_screen_L_min": triple_642_L_min,
        "goetze_642_triple_threaded_bare_kg": 3 * spec["goetze_642_threaded_kg"],
        "goetze_642_triple_flanged_bare_kg": 3 * spec["goetze_642_flanged_kg"],
        "goetze_851_triple_screen_L_min": triple_851_L_min,
    }
