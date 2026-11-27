"""Read the six protected branches and screen catalogue cartridge options."""


def qualify(spec, circuit, previous, density_kg_m3, pressure_limits):
    sun = spec["sun_RPIC"]
    parker = spec["parker_R4V06"]
    rexroth = spec["rexroth_DBC30"]
    parker_curve = parker["TUV_curve_at_300_bar_approx_end"]
    parker_approx_bar_per_L_min = (parker_curve["pressure_bar"] - 300) / parker_curve["flow_L_min"]
    branch_results = []
    for tag in spec["tags"]:
        valve = circuit["elements"][tag]
        setpoint = valve["setpoint"]
        ports = valve["ports"]
        assert ports["Y"] == "DR"
        peak_bar = setpoint["max_inlet_at_design_flow_bar"]
        crack_bar = setpoint.get("initial_crack_target_bar", pressure_limits["max_working_bar"])
        assert peak_bar == pressure_limits["max_relief_bar"]
        out_bar = circuit["lines"][ports["T"]]["p_design_bar"]
        pilot_bar = circuit["lines"][ports["Y"]]["p_design_bar"]
        flow_L_min = valve["Q_L_min"]
        branch_results.append({
            "id": tag, "required_L_min": flow_L_min, "crack_target_bar": crack_bar, "limit_peak_bar": peak_bar,
            "main_return": ports["T"], "pilot_return": ports["Y"],
            "main_return_network_design_bar": out_bar, "pilot_return_network_design_bar": pilot_bar,
            "sun_capacity_covers_flow": flow_L_min <= sun["max_L_min"],
            "sun_remaining_override_bar_at_return_design_pressure": peak_bar - crack_bar - sun["tank_pressure_factor"] * out_bar,
            "parker_TUV_body_approx_override_bar": parker_approx_bar_per_L_min * flow_L_min,
            "external_drain_remaining_override_bar_at_DR_design_pressure": peak_bar - crack_bar - pilot_bar,
        })

    previous_body_kg = previous["evidence"]["local_housing_kg_each"]
    previous_body_cm3 = previous_body_kg / density_kg_m3 * 1e6
    qty = len(branch_results)
    db_total_kg = qty * spec["reference_DB30_subplate_kg"]
    sun_screen_kg = qty * (sun["exact_model_kg"] + previous_body_kg)
    rexroth_mass_ceiling_kg = spec["reference_DB30_subplate_kg"] - rexroth["family_kg"]
    return {
        "credited": False,
        "reason": (
            "RPIC имеет два порта и чувствителен к сливу 1:1. Расчётные давления сетей TR/TRF/TEM "
            "не подтверждают допустимый сдвиг уставок. Для Parker R4V06 с Y1 имеется кривая корпусного клапана. "
            "Для Rexroth R900519773 с Y опубликована полость, нужны Δp(Q) блока, рабочий чертёж блока и масса точного исполнения."
        ),
        "source_ids": ["db30", "rexroth_dbc", "sun_rpic", "sun_cavity", "parker_r4v", "parker_r4v_service", "parker_r4v_tuv",
                       "circuit", "baseline_results"],
        "branches": branch_results,
        "retained_DB30_kg_each": spec["reference_DB30_subplate_kg"],
        "retained_DB30_total_kg": db_total_kg,
        "sun_RPIC": sun | {"previous_housing_kg_each": previous_body_kg,
                         "previous_housing_volume_cm3_each": previous_body_cm3,
                         "previous_assembly_screen_kg": sun_screen_kg,
                         "previous_assembly_screen_delta_kg": sun_screen_kg - db_total_kg},
        "parker_R4V06": parker,
        "rexroth_DBC30": rexroth | {"break_even_housing_and_mount_kg": rexroth_mass_ceiling_kg,
                                     "break_even_net_steel_cm3_before_mounts": rexroth_mass_ceiling_kg / density_kg_m3 * 1e6},
        "open_prototype_item": "Осциллограммы сброса и проверка пиков 315 бар на первом образце по D-OP-11.",
    }
