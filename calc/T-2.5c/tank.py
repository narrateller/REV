"""Reproduce the inherited tank load screen and check dry plate frequencies."""

from math import cos, pi, radians, sqrt


def qualify(spec, tank, prior_wall, station_kg, drive_kg, rated_rpm):
    length_m, width_m, height_m = (dim / 1000 for dim in tank["tank_dims_mm"])
    gravity = spec["standard_gravity_m_s2"]
    thickness_m = spec["candidate_wall_mm"] / 1000
    modulus_Pa = spec["steel_E_GPa"] * 1e9
    density = spec["density_kg_m3"]
    oil_density = tank["density_kg_m3"]
    oil_depth_m = tank["nominal_oil_L"] / 1000 / (length_m * width_m)
    hydrostatic_Pa = oil_density * gravity * oil_depth_m
    flooded_transport_Pa = oil_density * gravity * (
        height_m + max(spec["transport_forward_g"] * length_m, spec["transport_lateral_g"] * width_m)
    )
    strip_I_m4 = thickness_m**3 / 12  # unit-width vertical strip

    def wall_at(pressure_Pa):
        max_moment_Nm = pressure_Pa * height_m**2 / 8
        stress_MPa = max_moment_Nm * thickness_m / (2 * strip_I_m4 * 1e6)
        deflection_mm = 5 * pressure_Pa * height_m**4 / (384 * modulus_Pa * strip_I_m4) * 1000
        return {"pressure_kPa": pressure_Pa / 1000, "bending_MPa": stress_MPa,
                "edge_reaction_strip_N_per_m": pressure_Pa * height_m / 2,
                "deflection_mm": deflection_mm, "yield_to_bending": spec["steel_yield_MPa"] / stress_MPa}

    bands_Hz = [rated_rpm / 60, rated_rpm / 30]
    panel_modes = []
    for panel, a_m, b_m, t_m in (
        ("long_wall", length_m, height_m, thickness_m),
        ("short_wall", width_m, height_m, thickness_m),
        ("cover_or_bottom", length_m, width_m, tank["shell_sheet_mm"] / 1000),
    ):
        # Leissa, NASA SP-160, section 4.1.1: exact dry, simply supported plate.
        rigidity_Nm = modulus_Pa * t_m**3 / (12 * (1 - spec["steel_poisson_ratio"]**2))
        coefficient = pi / 2 * sqrt(rigidity_Nm / (density * t_m))
        modes_Hz = [coefficient * ((m / a_m)**2 + (n / b_m)**2) for m in (1, 2) for n in (1, 2)]
        panel_modes.append({"panel": panel, "f11_dry_Hz": modes_Hz[0],
                            "f21_dry_Hz": modes_Hz[2], "f12_dry_Hz": modes_Hz[1]})

    lift_vertical_N = station_kg * gravity * spec["lift_dynamic_factor"] / spec["effective_sling_legs"]
    drive_weight_N = drive_kg * gravity
    wall = {
        "credited": False,
        "reason": (
            "Расчёт полосы и частот сухих пластин выполнен. Нужны чертёж швов, рёбер и проушин, реакции опор, "
            "проверка залитой сборки и размещения рёбер в пределах габарита. Прогиб при транспортном сценарии "
            "превышает толщину стенки, линейный скрининг не квалифицирует оболочку."
        ),
        "source_ids": ["earlier_tank", "steel", "leissa", "transport"],
        "nominal_oil_L": tank["nominal_oil_L"], "tank_dims_mm": tank["tank_dims_mm"],
        "proposed_wall_mm": spec["candidate_wall_mm"], "proposed_shell_kg": prior_wall["proposed_shell_kg"],
        "rib_projection_growth_mm_per_axis": prior_wall["ribs"]["potential_total_projection_growth_per_axis_mm"],
        "oil_depth_mm": oil_depth_m * 1000, "nominal_hydrostatics": wall_at(hydrostatic_Pa),
        "flooded_transport": wall_at(flooded_transport_Pa),
        "motor_excitation_Hz": bands_Hz, "dry_panel_modes": panel_modes,
        "vertical_lift_reaction_per_leg_N": lift_vertical_N,
        "sling_tension_N": lift_vertical_N / cos(radians(spec["sling_angle_from_vertical_deg"])),
        "transport_station_forward_N": station_kg * gravity * spec["transport_forward_g"],
        "transport_station_lateral_N": station_kg * gravity * spec["transport_lateral_g"],
    }
    base = {
        "credited": False,
        "reason": (
            "Нет геометрии плиты, швов, проушин и опор бака, распределения массы привода с колоколом "
            "и точного артикула полумуфт. Прогиб и соосность для пути мотор–насос–колокол–бак не подтверждены."
        ),
        "source_ids": ["earlier_tank", "transport", "bell_dims", "couplings"],
        "drive_mass_without_bell_kg": drive_kg, "drive_weight_lower_bound_N": drive_weight_N,
        "drive_lift_lower_bound_N": drive_weight_N * spec["lift_dynamic_factor"],
        "drive_transport_forward_lower_bound_N": drive_weight_N * spec["transport_forward_g"],
        "drive_transport_lateral_lower_bound_N": drive_weight_N * spec["transport_lateral_g"],
        "plate_deflection_mm": None, "exact_coupling_alignment_limit_mm": None,
    }
    return {"walls": wall, "base": base}
