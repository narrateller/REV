"""Compare published PC maps for the operator. Preserve the round-one PC screen."""
from math import log

from pc_branch import HERE, ROOT, T25B, dirty_duty_kW, load_yaml


def linear(value, a, b):
    x0, y0 = a
    x1, y1 = b
    return y0 + (value - x0) * (y1 - y0) / (x1 - x0)


def screw_map(nu, dp_bar, maps):
    lo, hi = (maps[:2] if nu <= maps[1][0] else maps[1:])
    flow_power = []
    for viscosity, q5, p5, q10, p10 in (lo, hi):
        flow_power.append((log(viscosity), linear(dp_bar, (5, q5), (10, q10)),
                           linear(dp_bar, (5, p5), (10, p10))))
    return tuple(linear(log(nu), (flow_power[0][0], flow_power[0][i]),
                        (flow_power[1][0], flow_power[1][i])) for i in (1, 2))


def calculate(pc):
    config = load_yaml(HERE / "sources.yaml")
    maps = config["pc_catalogue_inputs"]
    station = load_yaml(ROOT / "design/hydraulics/station.t25c.yaml")
    cooling = station["cooling"]
    heat_inputs = load_yaml(T25B / "sources.yaml")["inputs"]
    heat_curve = config["screen_inputs"]["gl180_heat_Q_L_min_kW"]
    base_pc_kW = pc["shaft_limit_kW"]
    water_kW = cooling["installed_water_electrical_reserve_kW"]
    base = cooling["installed_base_kW"]
    air = station["air_option"]["fan_kW"]
    main_kW = station["hydraulics"]["main_drive"]["rated_kW"]
    reference_bare_mass_kg = maps["kf125_pump_mass_kg"]
    reference_motor_mass_kg = maps["motor_masses_kg"][base_pc_kW]
    viscosity_cold = pc["operating_points"][0]["viscosity_mm2_s"]
    dp_hot = [row for row in pc["operating_points"] if row["temperature_C"] != 20]

    def gear(nu, dp):
        q = linear(dp, (2, 161), (4, 159))
        power = linear(dp, (2, 1.4), (4, 2.0))
        if nu > 100:
            # 100–200 mm²/s marks bracket the cold inlet on the page-20
            # logarithmic curve. Use the higher, rounded factor as a bound.
            power += maps["kf_cold_fv_upper_kW_per_L_min"] * maps["kf112_theoretical_flow_L_min"]
        return q, power

    def screw(nu, dp):
        return screw_map(nu, dp, maps["parker_smt16b_330L_1450"])

    def vane(nu, dp):
        # Catalogue p.175 resolves the flow. Its 10 kW power grid does not
        # resolve the unloaded torque at 1–2 bar. Keep actual power unknown.
        return linear(dp, (0, 180), (175, 160)), None

    descriptions = (
        ("gear", "KRACHT KF112", 1450, "kracht_kf", 16.0, 3.0, gear),
        ("screw", "Parker/Settima SMT16B PSP55-330L", 1450, "pc_screw", 15.5, 2.2, screw),
        ("vane", "Yuken PV2R4-153", 1200, "pc_vane", 68.5, 1.5, vane),
    )
    results = []
    all_hydraulic = []
    for kind, model, speed_rpm, source, mass, motor, performance in descriptions:
        nominal, _ = performance(34, 1.35)
        conditions = []
        for row in dp_hot:
            temperature = row["temperature_C"]
            nu = row["viscosity_mm2_s"]
            for quality, pressure_field in (("clean", "clean_dp_bar"), ("dirty", "dirty_scenario_dp_bar")):
                base_dp_bar = row[pressure_field]
                # The full round-one pressure is retained for comparison;
                # the linear-flow scaling is the higher of Q and Q² at Q≤180.
                flow_dp_bar = base_dp_bar * nominal / 180
                q, shaft = performance(nu, flow_dp_bar)
                hydraulic = q * flow_dp_bar / 600
                conditions.append({
                    "temperature_C": temperature, "oil_mm2_s": nu, "gl_state": quality,
                    "round_one_dp_at_180_bar": base_dp_bar,
                    "dp_for_flow_screen_bar": flow_dp_bar, "flow_L_min": q,
                    "hydraulic_kW": hydraulic, "shaft_screen_kW": shaft,
                    "shaft_at_unscaled_round_one_dp_kW": performance(nu, base_dp_bar)[1],
                    "pressure_dependent_power_from_catalogue_slope_kW": (60 * flow_dp_bar / 175
                                                                       if kind == "vane" else None),
                    "efficiency_screen": hydraulic / shaft if shaft else None,
                })
                all_hydraulic.append(hydraulic)
        hot_dp = max(row["dp_for_flow_screen_bar"] for row in conditions)
        cold_open_dp = pc["operating_points"][0]["clean_dp_bar"] * nominal / 180
        cold = []
        for dp in (hot_dp, 1.5, cold_open_dp):
            if hot_dp <= dp <= cold_open_dp:
                q, shaft = performance(viscosity_cold, dp)
                cold.append({"dp_bar": dp, "flow_L_min": q, "shaft_screen_kW": shaft,
                             "hydraulic_kW": q * dp / 600,
                             "pressure_dependent_power_from_catalogue_slope_kW": (60 * dp / 175
                                                                                if kind == "vane" else None)})
                all_hydraulic.append(q * dp / 600)
        worst_powers = [row["shaft_screen_kW"] for row in [*conditions, *cold]
                        if row["shaft_screen_kW"] is not None]
        q55 = [row["flow_L_min"] for row in conditions if row["temperature_C"] == 55]
        results.append({
            "type": kind, "model": model, "speed_rpm": speed_rpm, "source": source,
            "nominal_flow_L_min": nominal, "hot_points": conditions, "cold_bypass_points": cold,
            "crack_pressure_ideal_open_range_bar": [hot_dp, cold_open_dp],
            "cb_dynamic_override_qualified": False,
            "shaft_kW_max_screen": max(worst_powers, default=None),
            "illustrative_IEC_motor_kW": motor,
            "installed_base_if_motor_kW": round(base - base_pc_kW + motor, 3),
            "installed_air_if_motor_kW": round(base + air - base_pc_kW + motor, 3),
            "pump_mass_kg": mass, "motor_mass_kg_proxy": maps["motor_masses_kg"][motor],
            "change_vs_bare_KF125_kg": mass - reference_bare_mass_kg,
            "pump_and_motor_change_vs_baseline_proxy_kg": (
                mass + maps["motor_masses_kg"][motor] - reference_bare_mass_kg - reference_motor_mass_kg),
            "exact_change_vs_station_PC_row_kg": None,
            "q_dirty_GL180_kW_at_55_oil_30_water": dirty_duty_kW(heat_inputs, heat_curve, min(q55)),
            "air_flow_min_L_min": pc["air_option_min_oil_L_min_legacy"],
            "note": {
                "gear": "Below 2 bar: pressure extrapolation at 34 cSt. Cold: rounded viscosity correction, see p.20.",
                "screw": "Below 5 bar: extrapolated. Oil viscosity interpolated between the 6/68/400 cSt catalogue maps.",
                "vane": "The illustrated IEC rating is a budget case only. The 20 cSt curve at 1200 rpm gives the pressure slope; idle power and HLP46 cold torque are unresolved. A speed drive is necessary to reproduce 1200 rpm at 50 Hz.",
            }[kind],
        })
    catalogue_points = [
        ("KF112_34cSt_2bar", 161, 2, 1.4),
        ("KF125_34cSt_2bar", 181, 2, 1.7),
        ("SMT16B_330L_6cSt_5bar", 165.97, 5, 1.94),
        ("SMT16B_330L_68cSt_5bar", 169.98, 5, 2.57),
    ]
    efficiencies = {name: q * dp / (600 * shaft) for name, q, dp, shaft in catalogue_points}
    best = max(efficiencies.values())
    return {
        "pc_options": results, "selected": None, "cb_setpoint_bar": None,
        "base_station_PC_mass_basis": "T16-09 = 75 kg aggregate; no standalone PC mass. Deltas use catalogue KF125 body + illustrative ABB 0.55 kW motor and omit mounts / VFD.",
        "installed_breakdown_kW": {
            "M1": main_kW, "PC": base_pc_kW, "water_electrical": water_kW,
            "other_consumers_combined_inherited": round(base - main_kW - base_pc_kW - water_kW, 3),
            "air_fans": air, "base_total": base, "with_air_total": base + air,
        },
        "catalogue_pc_point_efficiencies": efficiencies,
        "best_catalogue_efficiency_near_duty": best,
        "best_catalogue_efficiency_HLP_viscosity_brackets": max(
            eta for key, eta in efficiencies.items() if "_6cSt_" not in key),
        "hydraulic_kW_all_cases_range": [min(all_hydraulic), max(all_hydraulic)],
        "shaft_optimistic_comparison_using_best_tabulated_efficiency_kW": [
            min(all_hydraulic) / best, max(all_hydraulic) / best],
        "disclosure": "Tabulated efficiency belongs to its tested pressure and viscosity. It is a comparison, not a validated upper bound on efficiency at the duty point.",
    }
