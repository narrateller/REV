"""Calculate catalogue derating and the station cooling interface."""
from math import exp, log, pi, prod, sqrt


def interpolate(x, points):
    (x0, y0), (x1, y1) = points
    if not x0 <= x <= x1:
        raise ValueError(f"{x} outside catalogue bracket {x0}–{x1}")
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def pressure_head_bar(flow_L_min, diameter_mm, density_kg_m3):
    area_m2 = pi / 4 * (diameter_mm / 1000)**2
    velocity_m_s = flow_L_min / 60000 / area_m2
    return density_kg_m3 * velocity_m_s**2 / 2e5


def dirty_conductance(inputs, area_m2, clean_kW, catalogue_delta_K, oil_cp_kJ_kg_K):
    """Calibrate effective U to the catalogue, then change the surface resistance."""
    oil_kW_K = inputs["oil_flow_L_min"] / 60000 * inputs["oil_density_kg_m3"] * oil_cp_kJ_kg_K
    water_kW_K = water_capacity(inputs)
    minimum_kW_K = min(oil_kW_K, water_kW_K)
    ratio = minimum_kW_K / max(oil_kW_K, water_kW_K)
    effectiveness = clean_kW / (minimum_kW_K * catalogue_delta_K)
    resistance_m2_K_W = inputs["water_fouling_m2_K_W"] + inputs["oil_fouling_m2_K_W"]

    # Use counterflow and one-shell-pass effectiveness as two approximations
    # for the three water passes. Calibrate both at the same catalogue point.
    rate = 1 - ratio
    scale = sqrt(1 + ratio**2)
    inverse = (2 / effectiveness - 1 - ratio) / scale
    clean_ntu = {
        "counterflow": log((1 - ratio * effectiveness) / (1 - effectiveness)) / rate,
        "one_shell_pass": log((inverse + 1) / (inverse - 1)) / scale,
    }
    results = {}
    for mode, ntu in clean_ntu.items():
        clean_U_W_m2_K = ntu * minimum_kW_K * 1000 / area_m2
        dirty_U_W_m2_K = 1 / (1 / clean_U_W_m2_K + resistance_m2_K_W)
        dirty_NTU = dirty_U_W_m2_K * area_m2 / (minimum_kW_K * 1000)
        if mode == "counterflow":
            factor = exp(-dirty_NTU * rate)
            dirty_effectiveness = (1 - factor) / (1 - ratio * factor)
        else:
            factor = exp(-dirty_NTU * scale)
            dirty_effectiveness = 2 / (1 + ratio + scale * (1 + factor) / (1 - factor))
        results[mode] = {
            "clean_U_W_m2_K": clean_U_W_m2_K,
            "dirty_U_W_m2_K": dirty_U_W_m2_K,
            "dirty_kW_K": dirty_effectiveness * minimum_kW_K,
        }
    return results


def water_capacity(inputs):
    return (inputs["water_flow_L_min"] / 60000
            * inputs["water_density_kg_m3"] * inputs["water_cp_kJ_kg_K"])


def oil_pressure(inputs, catalogue_dp_bar):
    line = inputs["oil_local_line"]
    args = inputs["oil_flow_L_min"], inputs["oil_density_kg_m3"]
    pipe_head = pressure_head_bar(args[0], line["pipe_ID_mm"], args[1])
    adapter_head = pressure_head_bar(args[0], line["adapter_ID_mm"], args[1])
    pipe_dp_bar = pipe_head * line["darcy_friction_bound"] * 1000 * line["length_m"] / line["pipe_ID_mm"]
    fitting_dp_bar = adapter_head * line["fittings_K_at_adapter"]
    total_bar = catalogue_dp_bar + inputs["common_oil_dp_budget_bar"] + pipe_dp_bar + fitting_dp_bar
    shaft_kW = total_bar * inputs["oil_flow_L_min"] / (600 * inputs["pc_efficiency_floor"])
    return {
        "catalogue_cooler_dp_bar": catalogue_dp_bar,
        "inherited_common_dp_budget_bar": inputs["common_oil_dp_budget_bar"],
        "new_pipe_dp_bar": pipe_dp_bar,
        "new_fittings_dp_bar": fitting_dp_bar,
        "total_dp_bar": total_bar,
        "limit_dp_bar": inputs["oil_dp_limit_bar"],
        "pc_motor_kW": inputs["pc_motor_kW"],
        "shaft_required_kW": shaft_kW,
        "pass_at_design_point": total_bar <= inputs["oil_dp_limit_bar"] and shaft_kW <= inputs["pc_motor_kW"],
    }


def water_pressure(inputs, cooler_dp_bar):
    limits = inputs["water_pressure"]
    flow_m3_h = inputs["water_flow_L_min"] * 0.06
    density_ratio = inputs["water_density_kg_m3"] / 1000
    valve_dp_bar = (flow_m3_h / limits["valve_Kv_m3_h"])**2 * density_ratio
    strainer_clean_dp_bar = (flow_m3_h / limits["strainer_Kv_m3_h"])**2 * density_ratio
    other_bar = limits["flowmeter_and_water_line_dp_budget_bar"]
    dirty_total_bar = valve_dp_bar + limits["strainer_dirty_dp_limit_bar"] + limits["cooler_dirty_dp_limit_bar"] + other_bar
    return limits | {
        "valve_open_dp_bar": valve_dp_bar,
        "strainer_clean_dp_bar": strainer_clean_dp_bar,
        "cooler_clean_dp_bar": cooler_dp_bar,
        "interface_clean_dp_budget_bar": valve_dp_bar + strainer_clean_dp_bar + cooler_dp_bar + other_bar,
        "interface_dirty_dp_budget_bar": dirty_total_bar,
        "interface_design_supply_range_bar": [
            limits["interface_differential_min_bar"], limits["supply_gauge_max_bar"]],
        "budget_pass": (valve_dp_bar >= limits["valve_min_dp_bar"]
                        and dirty_total_bar <= limits["interface_differential_min_bar"]),
    }


def calculate(inputs):
    cat = inputs["catalog_bowman"]
    oil_flow_L_min = inputs["oil_flow_L_min"]
    water_flow_L_min = inputs["water_flow_L_min"]
    oil_C, water_C = inputs["oil_inlet_C"], inputs["water_inlet_C"]
    required_kW = max(inputs["heat_floor_kW"], inputs["heat_nominal_kW"] * inputs["heat_margin"])
    catalogue_delta_K = cat["catalogue_hot_inlet_C"] - cat["catalogue_cold_inlet_C"]
    clean_kW = interpolate(oil_flow_L_min, cat["catalogue_heat_points_L_min_kW"])
    clean_kW_K = clean_kW / catalogue_delta_K
    method_a_kW_K = clean_kW_K * inputs["catalog_factor"] * inputs["fouling_factor"]
    tema = dirty_conductance(inputs, cat["tube_area_m2"], clean_kW, catalogue_delta_K, inputs["oil_cp_kJ_kg_K"])
    method_b_kW_K = min(item["dirty_kW_K"] for item in tema.values())
    sensitivity = {}
    for cp in inputs["oil_cp_range_kJ_kg_K"]:
        rows = dirty_conductance(inputs, cat["tube_area_m2"], clean_kW, catalogue_delta_K, cp)
        sensitivity[str(cp)] = min(item["dirty_kW_K"] for item in rows.values()) * (oil_C - water_C)
    dirty_kW_K = min(method_a_kW_K, method_b_kW_K)
    duty_kW = dirty_kW_K * (oil_C - water_C)
    water_rate_kW_K = water_capacity(inputs)
    water_min_heat_balance_L_min = (
        required_kW * 60000 / (inputs["water_max_rise_K"] * inputs["water_density_kg_m3"] * inputs["water_cp_kJ_kg_K"])
    )
    oil_dp_bar = interpolate(oil_flow_L_min, cat["catalogue_oil_dp_points_L_min_kPa"]) / 100
    water_dp_bar = interpolate(water_flow_L_min, cat["catalogue_water_dp_points_L_min_kPa"]) / 100
    return {
        "selected": cat | {
            "catalogue_water_flow_L_min": water_flow_L_min,
            "catalogue_oil_flow_L_min": oil_flow_L_min,
            "catalogue_heat_kW": clean_kW,
            "catalogue_delta_K": catalogue_delta_K,
            "wet_with_water_kg": cat["dry_kg"] + cat["water_volume_L"] * inputs["water_density_kg_m3"] / 1000,
            "oil_fill_kg": cat["oil_volume_L"] * inputs["oil_density_kg_m3"] / 1000,
            "source_ids": ["bowman_profile", "bowman_catalog", "bowman_manual"],
        },
        "heat": {
            "source_ids": ["t25", "task", "bowman_profile", "htri_tema", "tema", "oil", "water"],
            "nominal_kW": inputs["heat_nominal_kW"],
            "adverse_kW": inputs["heat_adverse_kW"],
            "independent_kW": inputs["heat_independent_kW"],
            "multiplier": inputs["heat_margin"],
            "required_kW": required_kW,
            "oil_inlet_max_C": oil_C,
            "water_inlet_design_C": water_C,
            "clean_kW_at_design": clean_kW_K * (oil_C - water_C),
            "method_a_kW": method_a_kW_K * (oil_C - water_C),
            "method_b_kW": method_b_kW_K * (oil_C - water_C),
            "catalog_factor": inputs["catalog_factor"],
            "fouling_factor": inputs["fouling_factor"],
            "water_fouling_m2_K_W": inputs["water_fouling_m2_K_W"],
            "oil_fouling_m2_K_W": inputs["oil_fouling_m2_K_W"],
            "tema": tema,
            "tema_oil_cp_sensitivity_kW": sensitivity,
            "dirty_kW": duty_kW,
            "thermal_screen_pass": duty_kW >= required_kW,
            "water_inlet_max_C": oil_C - required_kW / dirty_kW_K,
            "water_rise_at_required_K": required_kW / water_rate_kW_K,
            "water_rise_at_dirty_design_K": duty_kW / water_rate_kW_K,
            "water_rise_at_clean_design_K": clean_kW_K * (oil_C - water_C) / water_rate_kW_K,
            "water_min_heat_balance_L_min": water_min_heat_balance_L_min,
            "water_flow_design_L_min": water_flow_L_min,
            "curve": [{
                "water_inlet_C": temperature,
                "method_a_kW": method_a_kW_K * (oil_C - temperature),
                "method_b_kW": method_b_kW_K * (oil_C - temperature),
                "dirty_kW": dirty_kW_K * (oil_C - temperature),
            } for temperature in range(15, 36)],
        },
        "oil_pressure": oil_pressure(inputs, oil_dp_bar),
        "water_pressure": water_pressure(inputs, water_dp_bar),
        "alternatives": compare(inputs),
    }


def compare(inputs):
    """Retain original rating points so missing catalogue data remains visible."""
    parker_dry_kg = 11.15
    # Published outer box, not a fill specification. Ports and plates consume
    # part of this volume, so this is only an intentionally loose upper bound.
    parker_box_L = 526 * 119 * 142.1 / 1e6
    delta_K = inputs["oil_inlet_C"] - inputs["water_inlet_C"]
    emmegi_hp = interpolate(180, [[120, 41], [280, 78]])
    metric_hp_kW = 0.73549875
    rule_a = inputs["catalog_factor"] * inputs["fouling_factor"]
    ktr_kW = 40
    oil_kW_K = inputs["oil_flow_L_min"] / 60000 * inputs["oil_density_kg_m3"] * inputs["oil_cp_kJ_kg_K"]
    ktr_delta_K = 50 + ktr_kW / oil_kW_K - 25
    ktr_tema = dirty_conductance(inputs | {"water_flow_L_min": 90}, 1.58, ktr_kW, ktr_delta_K,
                                 inputs["oil_cp_kJ_kg_K"])
    ktr_clean_dp_oil, ktr_clean_dp_water = 0.4, 0.07
    ktr_dirty_a = ktr_kW / ktr_delta_K * delta_K * rule_a
    ktr_dirty_b = min(item["dirty_kW_K"] for item in ktr_tema.values()) * delta_K
    # A loose box encloses the water tubes, end chambers and connections.
    ktr_water_upper_L = prod((505, 200, 220)) / 1e6
    return [
        {
            "model": "KTR TAK/TP-D1 (industrial)",
            "type": "Кожухотрубный",
            "material": "Трубки и крышки из латуни CW614N",
            "dry_kg": 20,
            "wet_with_water_kg": None,
            "wet_upper_bound_box_kg": 20 + ktr_water_upper_L * inputs["water_density_kg_m3"] / 1000,
            "catalogue_heat_kW": ktr_kW,
            "catalogue_delta_K": ktr_delta_K,
            "catalogue_oil_flow_L_min": 180,
            "catalogue_water_flow_L_min": 90,
            "catalogue_oil_dp_bar": ktr_clean_dp_oil,
            "catalogue_water_dp_bar": ktr_clean_dp_water,
            "catalogue_tube_area_m2": 1.58,
            "catalogue_oil_inlet_C_back_calculated": 25 + ktr_delta_K,
            "catalogue_oil_outlet_C": 50,
            "catalogue_water_inlet_C": 25,
            "method_a_kW_at_design_delta_original_flows": ktr_dirty_a,
            "method_b_kW_at_design_delta_original_flows": ktr_dirty_b,
            "source_ids": ["ktr"],
            "finding": f"По каталогу масло {ktr_clean_dp_oil:.2f} бар, вода {ktr_clean_dp_water:.2f} бар. "
                       f"Приведение к ΔT 25 K даёт {min(ktr_dirty_a, ktr_dirty_b):.2f} кВт с загрязнением "
                       "при 90 л/мин воды. Водяная полость и точка при 150 л/мин требуют данных поставщика.",
        },
        {
            "model": "Parker PWO B25TH×50/1P-SC-S, 50832505",
            "type": "Паяный пластинчатый",
            "material": "Нержавеющая сталь AISI 316/304, медная пайка",
            "dry_kg": parker_dry_kg,
            "wet_with_water_kg": None,
            "wet_upper_bound_box_kg": parker_dry_kg + parker_box_L * inputs["water_density_kg_m3"] / 1000,
            "catalogue_heat_kW": 79,
            "catalogue_delta_K": 40,
            "catalogue_oil_flow_L_min": 150,
            "catalogue_water_flow_L_min": 75,
            "method_a_kW_at_design_delta_original_flows": 79 * delta_K / 40 * rule_a,
            "catalogue_oil_dp_chart_available": True,
            "oil_dp_bar_at_design": None,
            "water_dp_bar_at_design": None,
            "source_ids": ["parker_pwo", "parker_curves"],
            "finding": "Нужен подбор 180 л/мин масла и 150 л/мин воды с Δp обеих сторон, площадью и водяным объёмом. Каталожная серия точек ограничена соотношением расходов 2:1.",
        },
        {
            "model": "EMMEGI MG 130-995-4",
            "type": "Кожухотрубный, 4 хода воды",
            "material": "Трубки CuDHP, торцы CuZn40",
            "dry_kg": 32,
            "wet_with_water_kg": None,
            "catalogue_capacity_L_side_unspecified": 9.2,
            "catalogue_heat_kW": emmegi_hp * metric_hp_kW,
            "catalogue_heat_HP": emmegi_hp,
            "catalogue_delta_K": 35,
            "catalogue_oil_flow_L_min": 180,
            "catalogue_water_flow_L_min": emmegi_hp,
            "method_a_kW_at_design_delta_original_flows": emmegi_hp * metric_hp_kW * delta_K / 35 * rule_a,
            "catalogue_oil_dp_chart_available": True,
            "oil_dp_bar_at_design": None,
            "water_dp_bar_at_design": None,
            "source_ids": ["emmegi"],
            "finding": "Линейный скрининг между краями таблицы при 32 сСт. Нужны точка при полном расходе воды, её Δp, объём трубной стороны и площадь; 9,2 л в таблице без обозначения стороны.",
        },
    ]
