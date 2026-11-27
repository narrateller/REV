"""T0 level, suction and thermal screens for the T-2.6 circuit."""

from collections import defaultdict
from math import cos, expm1, fsum, pi, radians, sqrt


G_M_S2 = 9.81


def area_mm2(diameter_mm):
    return pi * diameter_mm**2 / 4


def oil_trajectory(trace, replay, cylinders, t26_inputs, compliance_L_per_L):
    """Use contemporaneous cylinder positions and LP charge at every replay step."""
    cylinders = {row["id"]: row for row in cylinders}
    main = cylinders["CY-MAIN"]
    model = replay["model"]
    rod_areas_mm2 = {tag: area_mm2(row["rod_mm"]) * row["n"] for tag, row in cylinders.items()}
    directions = {
        "prefill": ("axial", 1, True), "regen": ("axial", 1, False),
        "press": ("axial", 1, False), "eject": ("axial", 1, True),
        "return": ("axial", -1, True), "pre_down": ("pre", 1, False),
        "pre_up": ("pre", -1, False), "gate_open": ("gate", -1, False),
        "gate_close": ("gate", 1, False),
    }
    axes_mm2 = {"axial": rod_areas_mm2["CY-MAIN"] + rod_areas_mm2["CY-RAPID"],
                "pre": rod_areas_mm2["CY-PRE"], "gate": rod_areas_mm2["CY-GATE"]}
    steps = defaultdict(list)
    for name, direction in directions.items():
        previous_mm = 0.0
        for start_s, dt_s, _, _, lp_L, _, position_mm in trace["motion_steps"][name]:
            steps[round(start_s + dt_s, 9)].append((name, direction, position_mm - previous_mm, lp_L))
            previous_mm = position_mm

    lp_initial_L = replay["accumulators"]["lp"]["initial_oil_L"]
    lp_L = lp_initial_L
    compression_entry_L = fsum(item["compressed_oil_L"] for item in trace["entry_fill"].values())
    axial_mm = 0.0
    rod_change_L = 0.0
    tf_change_L = 0.0
    cap_mm2 = area_mm2(main["bore_mm"])
    annulus_mm2 = cap_mm2 - area_mm2(main["rod_mm"])
    fill = replay["prefill"]
    normal = []
    after_relaxation = []
    boundaries = {"cycle_start"}
    stem_max_mm = model["main_stroke_mm"]
    cap_dead_L = max(main["cap_dead_L"], t26_inputs["round2"]["inventory"]["cap_dead_volume_L"])
    annulus_dead_L = main["annulus_dead_L"]
    lp_expansion = []
    stop_initial = (0.0, 0.0)
    for start_s, dt_s, stage, _, _, _, _, _, pump_L_min, _ in trace["power_steps"]:
        end_s = round(start_s + dt_s, 9)
        changes = steps.get(end_s, ())
        if stage == "lp_charge":
            lp_L += pump_L_min * dt_s / 60
        for name, (axis, sign, uses_tf), moved_mm, delivery_L in changes:
            signed_mm = sign * moved_mm
            rod_change_L += axes_mm2[axis] * signed_mm / 1e6
            lp_L -= delivery_L
            if axis == "axial":
                axial_mm += signed_mm
                if uses_tf:
                    tf_change_L -= rod_areas_mm2["CY-MAIN"] * signed_mm / 1e6
                boundaries.add(name)
        # Bound BAL equalization from absent to occurring as needed to reset TF.
        # The stored compression packet can reside in the lines until MD opens.
        t0_offsets_L = [
            -rod_change_L - tf_offset_L + lp_initial_L - lp_L
            for tf_offset_L in (0.0, tf_change_L)
        ]
        normal.extend((t0_offsets_L[0] - compression_entry_L, t0_offsets_L[1] - compression_entry_L,
                       *t0_offsets_L))
        # Interlocks close BAL/MF/MBT and stop motion commands. SAL and SAX
        # discharge to T0. At fixed x the full chambers do not empty.
        # T-1.6 doubled compliance and 315 bar bound the MA/MB pressure release.
        cap_L = cap_dead_L + cap_mm2 * axial_mm / 1e6
        annulus_L = annulus_dead_L + annulus_mm2 * (stem_max_mm - axial_mm) / 1e6
        lp_expansion.append((end_s, lp_L))
        for offset_L in t0_offsets_L:
            after_relaxation.append((offset_L + lp_L, end_s, axial_mm, cap_L + annulus_L, stage))
        stop_initial = (axial_mm, rod_change_L)
    assert abs(stop_initial[0]) < 1e-6 and abs(stop_initial[1]) < 1e-7
    assert abs(lp_L - lp_initial_L) < 1e-6
    assert fill["buffer_oil_L"] + min(0.0, tf_change_L) > 0
    return dict(
        start_full_LP_oil_L=lp_initial_L,
        sampled_LP_oil_L_range=[min(v for _, v in lp_expansion), max(v for _, v in lp_expansion)],
        running_T0_offset_L_range=[min(normal), max(normal)],
        unbalanced_TF_net_gain_per_cycle_L=tf_change_L,
        main_closed_port_entry_compression_L=compression_entry_L,
        stop_trigger_samples=len(lp_expansion),
        max_sampled_post_LP_points_by_phase={
            phase: dict(T0_offset_with_LP_dump_L=offset, trigger_s=time_s, main_position_mm=x_mm,
                        MA_MB_oil_L=oil_L)
            for phase, (offset, time_s, x_mm, oil_L, _) in phase_maxima(after_relaxation, compliance_L_per_L).items()
        },
        sampled_motion_names=sorted(boundaries - {"cycle_start"}),
    )


def phase_maxima(points, compliance_L_per_L):
    by_phase = {}
    for point in points:
        phase = point[-1]
        prior = by_phase.get(phase)
        if prior is None or point[0] + compliance_L_per_L * point[3] > prior[0] + compliance_L_per_L * prior[3]:
            by_phase[phase] = point
    return by_phase


def tank_structure(project, t16_inputs, assumptions, station_kg, oil_L):
    length_m, width_m, height_m = [d / 1000 for d in project["tank_dims_mm"]]
    rho_steel_kg_m3 = project["steel_density_kg_m3"]
    rho_oil_kg_m3 = project["oil_density_kg_m3"]
    oil_depth_m = oil_L / 1000 / (length_m * width_m)
    t_m = assumptions["side_sheet_mm"] / 1000
    old_t_m = project["tank_sheet_mm"] / 1000
    side_area_m2 = 2 * (length_m + width_m) * height_m
    rib_area_m2 = assumptions["rib_width_mm"] * assumptions["rib_thickness_mm"] / 1e6
    added_rib_kg = assumptions["rib_count"] * rib_area_m2 * height_m * rho_steel_kg_m3

    # Unit-width simply supported vertical strip. Full base pressure is applied over
    # the full wall height. Hydrostatic and tilt heads use a quasistatic envelope.
    elastic_Pa = project["elastic_modulus_MPa"] * 1e6
    strip_I_m4 = t_m**3 / 12
    full_head_Pa = rho_oil_kg_m3 * G_M_S2 * height_m
    forward_g = assumptions["transport_forward_g"]
    lateral_g = assumptions["transport_lateral_g"]
    wet_transport_Pa = rho_oil_kg_m3 * G_M_S2 * (
        height_m + max(forward_g * length_m, lateral_g * width_m))
    tank_mass_kg = (2 * length_m * width_m * old_t_m + side_area_m2 * t_m) * rho_steel_kg_m3
    tank_mass_kg += project["mass_allowances_kg"]["tank_baffles_mounts_fittings"] + added_rib_kg

    def side_screen(pressure_Pa):
        stress_Pa = (pressure_Pa * height_m**2 / 8) * (t_m / 2) / strip_I_m4
        deflection_m = 5 * pressure_Pa * height_m**4 / (384 * elastic_Pa * strip_I_m4)
        return dict(pressure_kPa=pressure_Pa / 1000, bending_MPa=stress_Pa / 1e6,
                    deflection_mm=deflection_m * 1000,
                    yield_to_bending=assumptions["steel_yield_MPa"] / (stress_Pa / 1e6))

    # The existing RHS skid takes the lifting and anchorage loads. With two
    # effective slings, calculate the vertical reaction and line tension.
    lift_factor = assumptions["lift_dynamic_factor"]
    effective_legs = assumptions["effective_lift_legs"]
    lift_vertical_N = station_kg * G_M_S2 * lift_factor / effective_legs
    lift_tension_N = lift_vertical_N / cos(radians(assumptions["sling_angle_from_vertical_deg"]))
    wet_tank_kg = tank_mass_kg + oil_L * rho_oil_kg_m3 / 1000
    frame = t16_inputs["revision"]["mass"]["tank_base"]
    b_mm, h_mm = frame["RHS_outer_mm"]
    wall_mm = frame["RHS_thickness_mm"]
    # Screen both possible RHS orientations for the inherited crossmember.
    span_mm = frame["crossmember_length_mm"]
    inertia_mm4 = (h_mm * b_mm**3 - (h_mm - 2 * wall_mm) * (b_mm - 2 * wall_mm)**3) / 12
    section_modulus_mm3 = inertia_mm4 / (b_mm / 2)
    weak_I_mm4 = (b_mm * h_mm**3 - (b_mm - 2 * wall_mm) * (h_mm - 2 * wall_mm)**3) / 12
    weak_Z_mm3 = weak_I_mm4 / (h_mm / 2)
    bearing_N = wet_tank_kg * G_M_S2 * lift_factor
    moment_N_mm = bearing_N * span_mm / 4
    return dict(
        side_sheet_mm=assumptions["side_sheet_mm"], cover_and_bottom_sheet_mm=project["tank_sheet_mm"],
        material=assumptions["steel_grade"], proposed_shell_kg=tank_mass_kg,
        side_sheet_savings_kg=side_area_m2 * (old_t_m - t_m) * rho_steel_kg_m3,
        ribs_kg=added_rib_kg, ribs={
            "count": assumptions["rib_count"], "section_mm": [assumptions["rib_width_mm"], assumptions["rib_thickness_mm"]],
            "length_each_mm": height_m * 1000, "included_in_bending_stiffness": False,
            "layout": "Одно наружное ребро на стенку, смонтированное на ребро. Сверить место в пределах рамы.",
            "potential_total_projection_growth_per_axis_mm": 2 * assumptions["rib_width_mm"]},
        baffles_mounts_fittings_kg=project["mass_allowances_kg"]["tank_baffles_mounts_fittings"],
        oil_depth_m=oil_depth_m, static=side_screen(full_head_Pa), flooded_transport=side_screen(wet_transport_Pa),
        lift=dict(screen_dynamic_factor=lift_factor, effective_sling_legs=effective_legs,
                  vertical_per_leg_N=lift_vertical_N, sling_tension_N=lift_tension_N,
                  load_path="Стропы за раму станции, бак опирается на её поперечины.",
                  single_center_loaded_RHS_tank_weight_bound_N=bearing_N,
                  RHS_strong_axis_stress_MPa=moment_N_mm / section_modulus_mm3,
                  RHS_weak_axis_stress_MPa=moment_N_mm / weak_Z_mm3),
        transport=dict(station_forward_N=station_kg * G_M_S2 * forward_g,
                       station_lateral_N=station_kg * G_M_S2 * lateral_g,
                       nominal_transport_state="T0 осушен, крепление за раму станции."),
        pending="Нужны замкнутые швы 3/4 мм, расчёт опор, проушин и креплений с фактическим центром тяжести, проверка вибраций, испытание на герметичность. Перегородки, крепление к днищу и посадки сохраняются.",
    )


def calculate(project, circuit, interlocks, selected26, heat, sources, t16_inputs, station_kg):
    elements = circuit["elements"]
    level = elements["LT"]["setpoint"]
    initial_L = project["tank_nominal_oil_L"]
    reserve_L = project["main_tank_loss_reserve_L"]
    x_mm, y_mm, z_mm = project["tank_dims_mm"]
    tank_area_mm2 = x_mm * y_mm
    gross_L = tank_area_mm2 * z_mm / 1e6
    rho_kg_m3 = project["oil_density_kg_m3"]
    ax = elements["AX"]["setpoint"]
    stop = interlocks["faults"]["stop"]
    assert all(stop["commands"][tag] == target for tag, target in
               {"P1": "off", "ZU": "open", "SAL": "bleed", "SAX": "bleed", "MF": "closed", "MBT": "closed"}.items())
    for route in (["ALP.A", "T0.T", ["SAL", "F2"]], ["AX.A", "T0.T", ["SAX", "F2"]]):
        assert route in stop["routes"]
    assert elements["BAL"]["default_state"] == "closed"
    ax_effective_L = t16_inputs["project"]["round2"]["pilot_high_side_volume_L"]
    ax_oil_max_L = ax_effective_L * (1 - (ax["precharge_bar"] + 1) / (ax["operating_max_bar"] + 1))
    bulk_Pa = project["round2"]["fault_oil_bulk_modulus_Pa"]
    compliance = project["round2"]["fault_compliance_multiplier"]
    pressure_Pa = elements["RVM"]["p_design_bar"] * 1e5
    model = selected26["model"]
    # Sensitivity using the commissioned motion ramp as braking proxy. The
    # power-off dump dynamics require valve response and pressure traces.
    coast_m = max(model[name] for name in ("approach_m_s", "eject_m_s", "return_m_s"))**2 / (
        2 * model["rapid_accel_m_s2"])
    coast_L = area_mm2(model["main_cylinder_bore_mm"]) * (coast_m * 1000) / 1e6
    cases = {}
    worst_running_offset_L = 0.0
    for case, trajectory in heat["trajectories"].items():
        low_L, high_L = trajectory["running_T0_offset_L_range"]
        worst_running_offset_L = min(worst_running_offset_L, low_L)
        candidate_stops = []
        for phase, point in trajectory["max_sampled_post_LP_points_by_phase"].items():
            release_L = compliance * point["MA_MB_oil_L"] * pressure_Pa / bulk_Pa
            stopped_L = initial_L + point["T0_offset_with_LP_dump_L"] + ax_oil_max_L + release_L + coast_L
            candidate_stops.append(dict(phase=phase, oil_after_stop_upper_L=stopped_L,
                                        decompression_oil_bound_L=release_L, **point))
        cases[case] = dict(running_T0_L_range=[initial_L + low_L - reserve_L, initial_L + high_L],
                           worst_stop=max(candidate_stops, key=lambda row: row["oil_after_stop_upper_L"]),
                           stop_trigger_samples=trajectory["stop_trigger_samples"], stop_phases=candidate_stops)

    low_trip_L = level["low_trip_L"]
    high_trip_L = level["high_trip_L"]
    min_running_L = min(item["running_T0_L_range"][0] for item in cases.values())
    max_stop_L = max(item["worst_stop"]["oil_after_stop_upper_L"] for item in cases.values())
    return_flow_L_min = max(case["main_delivery_mean_L_min"] for case in heat["cases"].values())
    return_flow_L_min += elements["FX"]["Q_L_min"]
    cooler_flow_L_min = heat["flow_L_min"]
    reserve_and_swing_L = reserve_L - worst_running_offset_L
    dwell_s = project["tank_baffle_deaeration_target_s"]
    main_only_L = return_flow_L_min * dwell_s / 60
    same_path_L = (return_flow_L_min + cooler_flow_L_min) * dwell_s / 60

    suction = sources["suction_screen"]
    d_m = suction["assumed_clear_mouth_ID_mm"] / 1000
    rated_main_L_min = elements["P1"]["Q_L_min"]
    q_m3_s = (rated_main_L_min + elements["FX"]["Q_L_min"]) / 60000
    velocity_m_s = q_m3_s / (pi * d_m**2 / 4)
    pressure_air_absolute_bar = project["pressure_air_absolute_bar"]
    minimum_inlet_bar = sources["a4vso"]["min_inlet_absolute_bar"]
    # HI intake correlation applied as a screen for an undisturbed approach.
    fr = velocity_m_s / sqrt(G_M_S2 * d_m)
    submergence_m = d_m * (1 + suction["vortex_Froude_multiplier"] * fr)
    submergence_with_mouth_L = (submergence_m + suction["assumed_mouth_elevation_mm"] / 1000) * tank_area_mm2 / 1000
    low_depth_m = min_running_L * 1000 / tank_area_mm2
    allowable_loss_bar = pressure_air_absolute_bar - minimum_inlet_bar + rho_kg_m3 * G_M_S2 * low_depth_m / 1e5
    cold_nu_m2_s = sources["oil_cold"]["viscosity_at_0_C_mm2_s"] * 1e-6
    cold_Re = velocity_m_s * d_m / cold_nu_m2_s
    cold_darcy_loss_bar_per_m = (64 / cold_Re) / d_m * rho_kg_m3 * velocity_m_s**2 / 2e5
    assert cold_Re < 2300
    level_required_L = low_trip_L + reserve_and_swing_L
    suction_required_L = submergence_with_mouth_L + reserve_and_swing_L
    deair_required_L = same_path_L + reserve_and_swing_L
    minimums_L = {"уровень LT": level_required_L, "заглубление всаса": suction_required_L,
                  "деаэрация при общем пути": deair_required_L}
    determining = max(minimums_L, key=minimums_L.get)

    delta_K = heat["oil_limit_C"] - heat["air_C"]
    thermal_kJ_K = initial_L * rho_kg_m3 / 1000 * project["oil_cp_kJ_kg_K"]
    heat_kW = heat["worst_heat_kW"]
    cooling_kW_K = heat["dirty_capacity_kW_per_K"]
    fill = selected26["prefill"]
    return dict(
        nominal_oil_L=initial_L, density_kg_m3=rho_kg_m3, tank_dims_mm=project["tank_dims_mm"],
        gross_L=gross_L, low_trip_L=low_trip_L, high_trip_L=high_trip_L, reserve_L=reserve_L,
        stop=dict(source=sources["interlocks"]["url"], cases=cases, min_running_L=min_running_L,
                  max_stopped_L=max_stop_L, headroom_to_high_trip_L=high_trip_L - max_stop_L,
                  max_nominal_initial_at_high_trip_L=high_trip_L - (max_stop_L - initial_L),
                  headroom_to_rim_L=gross_L - max_stop_L, ax_discharge_bound_L=ax_oil_max_L,
                  nominal_braking_coast_m=coast_m, nominal_braking_cap_volume_bound_L=coast_L,
                  control_sequence="Снять момент P1, открыть ZU, закрыть MF/MBT и BAL, разрядить LP/AX через SAL/SAX, разгрузить MA/MB через аварийные линии в T0.",
                  limitations="Достоверны позиции штатного цикла и маршруты стопа. Объём после стопа — огибающая чувствительности, без измеренной задержки, остановочного перемещения, волны уровня, расширения и гравитационного дренажа. Массовый слив TF через RTF относится к отдельному отказу."),
        suction=dict(provisional_required_oil_L=suction_required_L, min_pump_inlet_absolute_bar=minimum_inlet_bar,
                     combined_P1_and_pilot_flow_L_min=q_m3_s * 60000, velocity_m_s=velocity_m_s, Froude=fr,
                     mouth_diameter_mm=d_m * 1000, mouth_elevation_mm=suction["assumed_mouth_elevation_mm"],
                     submergence_mm=submergence_m * 1000, running_depth_mm=low_depth_m * 1000,
                     available_loss_at_zero_flange_elevation_bar=allowable_loss_bar,
                     cold_oil_DN100_Re=cold_Re, cold_oil_DN100_straight_loss_bar_per_m=cold_darcy_loss_bar_per_m,
                     cold_oil_straight_equivalent_length_limit_m=allowable_loss_bar / cold_darcy_loss_bar_per_m,
                     head_shortfall_at_min_running_mm=(submergence_with_mouth_L - min_running_L) * 1e6 / tank_area_mm2,
                     flange_budget_rule="Из бюджета вычесть ρg·z фланца над дном и потери сапуна. Сравнить с ΣK·ρv²/2, распределёнными и ускорительными потерями, холодной вязкостью и загрязнением.",
                     qualified=False),
        deaeration=dict(target_s=dwell_s, main_and_pilot_mean_L_min=return_flow_L_min,
                        level_with_separate_cooling_path_L=main_only_L + reserve_and_swing_L,
                        level_with_shared_path_L=deair_required_L, estimated_residence_shared_min_level_s=60 * min_running_L / (
                            return_flow_L_min + cooler_flow_L_min),
                        level_penalty_L=reserve_and_swing_L,
                        construction="Сохранить раздельные подуровневые диффузоры, перегородку и затопленный всас. Проверить эффективный объём, работу сетки при холодном масле и время до появления пузырей на всасе."),
        level_minimum_initial_L=level_required_L, sizing_screen_minimum_initial_L=minimums_L[determining],
        determining_screen=determining,
        reduced_oil_approved=False, structure=tank_structure(project, t16_inputs, sources["tank_structure"], station_kg, initial_L),
        thermal=dict(oil_only_heat_capacity_kJ_K=thermal_kJ_K, starting_oil_C=heat["air_C"],
                     heating_to_limit_without_cooling_s=delta_K * thermal_kJ_K / heat_kW,
                     rise_after_10_min_dirty_K=-(heat_kW / cooling_kW_K) * expm1(-cooling_kW_K * 600 / thermal_kJ_K),
                     steady_oil_dirty_C=heat["air_C"] + heat_kW / cooling_kW_K),
        TF=dict(gross_L=fill["gross_TF_L"], initial_oil_L=fill["buffer_oil_L"],
                min_initial_oil_L=fill["required_initial_oil_L"], initial_margin_L=fill["initial_oil_margin_L"],
                nominal_gauge_bar=fill["tank_nominal_gauge_bar"],
                regulation_half_band_bar=fill["tank_nominal_gauge_bar"] - fill["tank_min_gauge_bar"],
                max_gauge_bar=fill["head_at_tank_gauge_bar"], min_gauge_bar=fill["tank_min_gauge_bar"],
                separator="Эластичный разделитель масла и азота, двухстороннее регулирование.",
                balance_nominal_L_min=elements["BAL"]["Q_L_min"],
                main_pump_inlet_is_separate=True),
    )
