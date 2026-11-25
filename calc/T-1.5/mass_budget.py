
"""Calculate machine mass, hydraulic inventories, and design-point screens."""
import json
from math import fsum, pi, sqrt
import sys

from check_circuit import CIRCUIT, INTERLOCKS, HERE, ROOT, read_yaml
from round2_screens import pilot_cycle, screen

sys.path.insert(0, str(HERE / "reference"))
from cycle_screen import cycle_screen  # noqa: E402


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def area_mm2(diameter_mm):
    return pi * diameter_mm ** 2 / 4


def volume_mass_kg(volume_mm3, density_kg_m3):
    return volume_mm3 * density_kg_m3 / 1e9


def cylinder_screen(main, cfg, criteria):
    pressure_MPa = criteria["C-HYD-01"]["max_relief_bar"] / 10
    bore_radius_mm = main["bore_mm"] / 2
    wall_mm = cfg["main_wall_min_mm"]
    outer_radius_mm = bore_radius_mm + wall_mm
    ri2, ro2 = bore_radius_mm ** 2, outer_radius_mm ** 2
    radial_MPa = -pressure_MPa
    hoop_MPa = pressure_MPa * (ro2 + ri2) / (ro2 - ri2)
    closed_axial_MPa = pressure_MPa * ri2 / (ro2 - ri2)
    vm_MPa = lambda axial: sqrt(((hoop_MPa - radial_MPa) ** 2 + (hoop_MPa - axial) ** 2
                                 + (radial_MPa - axial) ** 2) / 2)
    worst_vm_MPa = max(vm_MPa(closed_axial_MPa), vm_MPa(0))
    mass_saved_kg = volume_mass_kg(
        pi * ((bore_radius_mm + main["barrel_wall_mm"]) ** 2
              - (bore_radius_mm + cfg["main_wall_nominal_mm"]) ** 2) * main["barrel_length_mm"],
        cfg["steel_density_kg_m3"],
    )
    yield_factor = main["barrel_and_cover_Rp02_min_MPa"] / worst_vm_MPa
    return {
        "wall_nominal_mm": cfg["main_wall_nominal_mm"], "wall_min_mm": wall_mm,
        "evaluated_pressure_MPa": pressure_MPa, "radial_MPa": radial_MPa,
        "hoop_MPa": hoop_MPa, "closed_axial_MPa": closed_axial_MPa,
        "closed_vm_MPa": vm_MPa(closed_axial_MPa), "zero_axial_vm_MPa": vm_MPa(0),
        "minimum_yield_factor": yield_factor,
        "static_screen_pass": yield_factor >= criteria["C-STR-01"]["min_safety_factor_yield"],
        "mass_saved_kg": mass_saved_kg, "filled_kg": main["filled_mass_each_kg"] - mass_saved_kg,
        "retained_bore_rod_stroke_mm": [main["bore_mm"], main["rod_mm"], main["stroke_installed_mm"]],
        "frame_insert_gross_cover_reduction_kg": volume_mass_kg(
            (area_mm2(main["cover_OD_mm"]) - area_mm2(380)) * main["cover_thickness_rear_mm"],
            cfg["steel_density_kg_m3"],
        ),
        "detail_limitations": "Thick tube nominal hoop/stress screen. Retain T-1.3 heads and bolts. Check seal grooves, interfaces, cyclic stress and net frame changes before D1.",
    }


def frame_screen(cfg, criteria):
    setup, rho = cfg["structure"], cfg["steel_density_kg_m3"]
    allow = cfg["mass_allowances_kg"]
    force_N = setup["frame_load_N"]
    min_static = criteria["C-STR-01"]["min_safety_factor_yield"]
    fatigue_factor = cfg["project_fatigue_factor"]
    cycles = setup["load_cycles"]

    def plate(count, dims_mm, width_mm, span_mm):
        length_mm, height_mm, thickness_mm = dims_mm
        # Allow a centered 280 mm footprint. Simply supported strip, no credit for fixity.
        moment_N_mm = force_N * (2 * span_mm - 280) / 8
        stress_MPa = moment_N_mm / (width_mm * thickness_mm ** 2 / 6)
        return {
            "mass_kg": volume_mass_kg(count * length_mm * height_mm * thickness_mm, rho),
            "stress_range_MPa": stress_MPa,
            "yield_factor": cfg["steel_frame_yield_MPa"] / stress_MPa,
            "unnotched_fatigue_margin": cfg["column_allowable_range_MPa"] / stress_MPa,
        }

    n = setup["column_count"]
    column_force_N = force_N / n
    preload_N = setup["column_pretension_N_each"]
    joint_fraction = setup["column_joint_load_fraction"]
    root_mm2 = area_mm2(setup["column_thread_root_mm"])
    col_mass_kg = volume_mass_kg(n * area_mm2(setup["column_diameter_mm"])
                                 * setup["column_length_mm"], rho)
    col_stress_MPa = (preload_N + joint_fraction * column_force_N) / root_mm2
    range_MPa = joint_fraction * column_force_N / root_mm2
    joint_margin_N = preload_N - (1 - joint_fraction) * column_force_N
    cp = plate(setup["column_plate_count"], setup["column_plate_dims_mm"],
               setup["column_plate_effective_width_mm"], setup["column_plate_support_span_mm"])
    column_yield_factor = cfg["column_certified_yield_min_MPa"] / col_stress_MPa
    thread_fatigue_margin = setup["column_thread_fat_design_range_MPa"] / range_MPa
    column = {
        "tie_columns_kg": col_mass_kg, "end_plates": cp,
        "bases_ribs_rings_kg": allow["column_end_rings_bases_and_ribs"],
        "total_kg": col_mass_kg + cp["mass_kg"] + allow["column_end_rings_bases_and_ribs"],
        "column_max_stress_MPa": col_stress_MPa, "column_yield_factor": column_yield_factor,
        "thread_nominal_range_MPa": range_MPa, "thread_fatigue_margin": thread_fatigue_margin,
        "joint_clamp_remaining_N_each": joint_margin_N,
        "screen_pass": (min(cp["yield_factor"], column_yield_factor) >= min_static
                        and min(cp["unnotched_fatigue_margin"], thread_fatigue_margin) >= 1
                        and joint_margin_N > 0),
    }
    side_count = setup["welded_side_count"]
    L_mm, H_mm, t_mm = setup["welded_side_dims_mm"]
    side_mass_kg = volume_mass_kg(side_count * L_mm * H_mm * t_mm, rho)
    net_area_mm2 = side_count * setup["welded_side_net_height_mm"] * t_mm
    side_range_MPa = force_N / net_area_mm2 * setup["welded_detail_range_multiplier"]
    allowable_weld_MPa = (cfg["weld_fat_reference_MPa"]
                          * (cfg["weld_fat_reference_cycles"] / cycles) ** (1 / cfg["weld_fat_slope"])
                          / fatigue_factor)
    wp = plate(setup["welded_end_count"], setup["welded_end_dims_mm"],
               setup["welded_plate_effective_width_mm"], setup["welded_plate_support_span_mm"])
    weld_yield_factor = cfg["steel_frame_yield_MPa"] / side_range_MPa
    weld_fatigue_margin = allowable_weld_MPa / side_range_MPa
    welded = {
        "side_plates_kg": side_mass_kg, "end_plates": wp,
        "bases_ribs_guides_kg": allow["welded_ribs_bases_and_guides"],
        "total_kg": side_mass_kg + wp["mass_kg"] + allow["welded_ribs_bases_and_guides"],
        "side_detail_range_MPa": side_range_MPa, "side_yield_factor": weld_yield_factor,
        "allowable_side_range_MPa": allowable_weld_MPa, "side_fatigue_margin": weld_fatigue_margin,
        "screen_pass": (min(wp["yield_factor"], weld_yield_factor) >= min_static
                        and min(wp["unnotched_fatigue_margin"], weld_fatigue_margin) >= 1),
    }
    return {"design_load_N": force_N, "load_cycles": cycles, "column": column, "welded": welded}


def tank_and_cooling(cylinders, cfg, catalogs, drive, criteria, round2, cycle_s):
    station = drive["station"]
    pilot = round2["pilot"]
    pilot_oil_L_min = pilot["combined_theoretical_L_min"]
    oil_kg_L = cfg["oil_density_kg_m3"] / 1000
    volume_L = cfg["tank_nominal_oil_L"]
    x, y, z = cfg["tank_dims_mm"]
    gross_L = x * y * z / 1e6
    maximum_flow_L_min = station["gate_drive_projection"]["pump_max_flow_L_min"]
    first_run = drive["reference"][0]
    mean_flow_L_min = first_run["pump_oil_L"] * 60 / first_run["cycle_s"]
    sweep_volumes_L = {}
    full_sweep_L = 0
    for c in cylinders.values():
        stroke_mm = c["stroke_installed_mm"]
        cap_L = area_mm2(c["bore_mm"]) * stroke_mm * c["n"] / 1e6
        rod_L = area_mm2(c["rod_mm"]) * stroke_mm * c["n"] / 1e6
        sweep_volumes_L[c["id"]] = {"cap_L": cap_L, "annulus_L": cap_L - rod_L, "net_L": rod_L}
        full_sweep_L += cap_L
    OAC = catalogs["OAC"]["selected"]
    purge_aux_L = 5.0
    lp_residual_and_charge_L = 18.4 * (1 - (29 / 53) ** (1 / 1.4))
    pilot_charge_L = 9.3 * (1 - (101 / 151) ** (1 / 1.4))
    capped_inventory_L = full_sweep_L + lp_residual_and_charge_L + pilot_charge_L + purge_aux_L
    low_after_withdrawal_L = volume_L - capped_inventory_L - cfg["main_tank_loss_reserve_L"]
    tank_mass_kg = volume_mass_kg(2 * (x * y + x * z + y * z) * cfg["tank_sheet_mm"],
                                  cfg["steel_density_kg_m3"]) + cfg["mass_allowances_kg"]["tank_baffles_mounts_fittings"]
    buffer_volume_L = cfg["buffer_nominal_oil_L"]
    main = cylinders["CY-MAIN"]
    cap_L = sweep_volumes_L["CY-MAIN"]["cap_L"]
    residual_L = buffer_volume_L - sweep_volumes_L["CY-MAIN"]["net_L"]
    zsf_min_L = 1.5 * (cap_L + main["cap_dead_L"])
    # Independent cooling uses the same oil. Conservatively assume tank flow paths mix.
    residence_min_s = 60 * cfg["level_min_main_L"] / (maximum_flow_L_min + pilot_oil_L_min + OAC["oil_flow_L_min"])
    admission = station["prefill"]["cap_intake"]["ejection"]
    pipe_ratio = 125 / cfg["prefill_pipe_ID_mm"]
    cap_improvement_bar = (admission["acceleration_head_bar"] * (1 - pipe_ratio ** 2)
                           + admission["steady_drop_bar"] * (1 - pipe_ratio ** 4))
    tank = {
        "nominal_main_oil_L": volume_L, "gross_main_L": gross_L, "main_oil_kg": volume_L * oil_kg_L,
        "tank_shell_kg": tank_mass_kg, "minimum_level_L": cfg["level_min_main_L"],
        "calculated_low_inventory_L": low_after_withdrawal_L,
        "margin_above_minimum_L": low_after_withdrawal_L - cfg["level_min_main_L"],
        "main_tank_loss_reserve_L": cfg["main_tank_loss_reserve_L"],
        "max_fill_oil_L": cfg["upper_oil_inventory_L"],
        "reserve_above_max_fill_L": gross_L - cfg["upper_oil_inventory_L"],
        "minimum_residence_main_pump_only_s": 60 * cfg["level_min_main_L"] / maximum_flow_L_min,
        "nominal_residence_two_pumps_mean_s": 60 * volume_L / (mean_flow_L_min + pilot_oil_L_min + OAC["oil_flow_L_min"]),
        "minimum_residence_two_pumps_peak_s": residence_min_s,
        "cylinders_sweeps_L": sweep_volumes_L, "cylinders_cap_sweeps_total_L": full_sweep_L,
        "lp_full_oil_charge_L": lp_residual_and_charge_L,
        "pilot_full_oil_charge_L": pilot_charge_L, "fill_and_lines_reserve_L": purge_aux_L,
        "local_gross_L": cfg["buffer_gross_L"], "local_nominal_oil_L": buffer_volume_L,
        "local_oil_min_after_full_net_stroke_L": residual_L, "ZSF_case2_min_L": zsf_min_L,
        "local_oil_kg": buffer_volume_L * oil_kg_L,
        "minimum_local_cap_absolute_bar_at_0p44_bar": (
            admission["min_absolute_bar"] + cap_improvement_bar
            - 0.01 - cfg["buffer_valve_loss_extra_bar"]),
        "minimum_local_annulus_absolute_bar_at_0p44_bar": (
            station["prefill"]["annulus_intake"]["min_absolute_bar"]
            - 0.01 - cfg["prefill_rod_check_dp_target_bar"]),
        "deairing_test_required": residence_min_s < cfg["tank_baffle_deaeration_target_s"],
    }
    ambient_C, oil_limit_C = 40, 55
    useful_kW_K = OAC["coefficient_kW_K"] * (1 - OAC["tolerance_fraction"])
    heat_kW = cfg["cooling_heat_design_kW"]
    extra_fluid_heat_kW = round2["extra_fluid_work_bound_kJ_per_cycle"] / cycle_s
    revised_heat_kW = heat_kW + pilot["heat_bound_kW"] + extra_fluid_heat_kW - cfg["round2"]["old_pilot_heat_allowance_kW"]
    oil_flow_L_min = OAC["oil_flow_L_min"]
    installed = dict(station["cooling"]["installed_kW"])
    installed.pop("pilot_pack")
    installed["controls_and_valves"] = cfg["round2"]["electrical_controls_allowance_kW"]
    installed.update(cooler_fan=OAC["fan_kW"], cooler_circulation=cfg["cooling_circuit_motor_kW"])
    return tank, {
        "selected": OAC["series"], "oil_flow_L_min": oil_flow_L_min,
        "heat_capacity_kW": (oil_limit_C - ambient_C) * useful_kW_K,
        "heat_load_reference_kW": heat_kW, "heat_load_kW": revised_heat_kW,
        "extra_fluid_heat_bound_kW": extra_fluid_heat_kW,
        "design_margin_kW": (oil_limit_C - ambient_C) * useful_kW_K - revised_heat_kW,
        "predicted_hot_oil_C": ambient_C + revised_heat_kW / useful_kW_K,
        "oil_temperature_drop_K": heat_kW * 60 / (oil_flow_L_min * oil_kg_L * cfg["oil_cp_kJ_kg_K"]),
        "matrix_dp_bar": OAC["matrix_dp_bar"],
        "circulation_total_dp_budget_bar": cfg["cooling_circuit_max_total_dp_bar"],
        "circulation_required_shaft_kW": (oil_flow_L_min * cfg["cooling_circuit_max_total_dp_bar"]
                                          / (600 * cfg["cooling_circuit_pump_eta"])),
        "installed_kW": installed, "installed_total_kW": fsum(installed.values()),
        "installed_limit_kW": criteria["C-PWR-01"]["max_installed_kW"],
        "LAC_078_8_capacity_kW": catalogs["LAC"]["selected"]["coefficient_kW_K"] * 0.9 * 15,
        "LAC_110_8_with_baseline_aux_kW": fsum(station["cooling"]["installed_kW"].values()) + 1.10,
        "catalogue_curve_screen_only": True,
    }



def mass_rows(circuit, cylinders, original, drive, cylinder, frame, tank, cooling, data):
    cfg, catalogs = data["project"], data["catalogs"]
    old_station = drive["station"]["approximate_mass_breakdown_kg"]
    old_mechanical = cfg["mechanical_baseline_allowances_kg"]
    allowance = cfg["mass_allowances_kg"]
    station = []
    machine = []

    def add(table, name, old, new, source):
        table.append({"node": name, "T13_kg": old, "T15_kg": new, "source": source})

    old = old_station
    add(station, "Мотор, насос, муфта", old["motor"] + old["pv180"], old["motor"] + old["pv180"],
        "T-1.4b mass breakdown; OMEC and Parker data sheets; coupling in skid hardware")
    add(station, "Основной бак", old["tank"], tank["tank_shell_kg"],
        "Envelope 900×700×400 mm, sheet 4 mm and 15 kg for baffles, fittings and mounts")
    add(station, "Основное масло", old["main_tank_oil"], tank["main_oil_kg"],
        "Initial main tank inventory × oil density; cylinder fill already carried with cylinders")
    add(station, "ГА обоих контуров", old["lp_and_pilot_vessels"], old["lp_and_pilot_vessels"],
        "HYDAC SB330 table and T-1.4b mass breakdown")
    add(station, "Охладитель с вентилятором", old["cooler_with_fan"],
        catalogs["OAC"]["selected"]["mass_kg"], "KTR OAC1000-03-8 50 Hz, catalogue p. 25")
    x, y, _ = cfg["tank_dims_mm"]
    tube_mm2 = 80 * 40 - 72 * 32
    beams_mm = 2 * x + 4 * y
    skid_kg = volume_mass_kg(tube_mm2 * beams_mm, cfg["steel_density_kg_m3"]) + allowance["skid_hardware"]
    add(station, "Рама станции", old["skid_and_mounts"], skid_kg,
        "2×900 + 4×700 mm RHS 80×40×4, 10 kg feet/motor plate/mounting hardware, transport to verify")
    large_valve_kg = fsum(catalogs["WRC"]["mass_kg"][e["DN_mm"]] + e.get("catalogue_mass_extra_kg", 0) for e in circuit["elements"].values()
                          if e["type"] == "proportional_2_2" and e["source"] == "WRC")
    add(station, "Картриджи 2WRCE", old["large_valves"], large_valve_kg,
        "Circuit inventory × masses in RE 29406, NG32/40/50")
    add(station, "Коллекторы, малая арматура и защита", old["manifold_and_small_valves"],
        allowance["manifold_and_small_valves"] + allowance["new_safety_duplicated_sensors_and_cartridges"] + 19,
        "Project allowance including DB, gate valve, LC/LFA, SAF bodies, sensors and safety cartridges")
    add(station, "Фильтры, трубы, вспомогательные насосы", old["base_pipes_filters_and_aux_pumps"],
        allowance["pipes_filters_and_aux_pumps"], "Project allowance for wider return and separate cooling loop")
    add(station, "ZSF NG100", old["prefill_valve"], old["prefill_valve"], "RE 20478 and T-1.4b")
    add(station, "Локальный бак и его масло", old["prefill_buffer_and_oil"],
        allowance["buffer_shell_membrane_regulator"] + tank["local_oil_kg"],
        "Separated 65 L vessel assembly estimated at 30 kg; 42 L of oil")
    add(station, "Местные линии наполнения", old["enlarged_prefill_piping"], allowance["local_prefill_pipe"],
        "Engineering allowance for Ø125/100 and matching supports as already reserved in T-1.4b")
    add(station, "Клапаны плавания и подпитки", 0, 2 * (catalogs["LC2A"]["mass_kg"][40]
        + catalogs["LC"]["cartridge_mass_kg"][50]), "RE 21040 and RE 21010. Both check inserts in the shared manifold with its own cover allowance.")
    add(station, "Седло регенерации", 0, catalogs["LC"]["cartridge_mass_kg"][40] + catalogs["LC"]["cover_mass_kg"][40],
        "RE 21010 LC/LFA NG40")
    add(station, "Масляный предохранительный TF", 0, catalogs["GOETZE"]["mass_kg"],
        "Goetze Series 455 DN65/100 gastight catalogued mass")
    for item, mass in cfg["round2"]["safety_hardware_mass_budget_kg"].items():
        add(station, item, 0, mass, "Round-two engineering allowance; weigh actual procurement assembly")
    station_old = fsum(row["T13_kg"] for row in station)
    station_new = fsum(row["T15_kg"] for row in station)
    add(machine, "Гидростанция в сборе", station_old, station_new, "Detailed station inventory")
    main = cylinders["CY-MAIN"]
    add(machine, "Главный ГЦ с маслом", main["filled_mass_each_kg"], cylinder["filled_kg"],
        "T-1.3 physical cylinder, minus tube annulus at unchanged bore and length")
    for key, title in (
        ("CY-RAPID", "Два быстрых ГЦ с маслом"), ("CY-PRE", "ГЦ подпрессовки с маслом"),
        ("CY-GATE", "ГЦ шибера с маслом"),
    ):
        c = cylinders[key]
        mass_kg = c["n"] * c["filled_mass_each_kg"]
        add(machine, title, mass_kg, mass_kg, f"design/cylinders.t13.yaml {key}")
    chamber_kg = original["mass"]["chamber_lock_shoe_plate_without_actuators_kg"]
    gate_plate_kg = volume_mass_kg(260 * 260 * 38, cfg["steel_density_kg_m3"])
    add(machine, "Камера, башмак и засовы", chamber_kg - gate_plate_kg, chamber_kg - gate_plate_kg,
        "T-1.3 grouping minus estimate for gate plate; no double counting")
    add(machine, "Плита шибера", gate_plate_kg, gate_plate_kg,
        "38 mm from D-GK-01, planform 260×260 mm budget, included in upstream chamber grouping")
    add(machine, "Силовая рама", old_mechanical["frame"], frame["column"]["total_kg"],
        "T-1.3 GK review approximation and column screen at 1.94 MN")
    for key, name, source in (
        ("crosshead_punch", "Траверса с пуансоном", "T-1.3 remaining moving-mass allowance; planned mass cap"),
        ("feeder_hopper", "Подача и бункер", "Engineering allowance"),
        ("guards", "Ограждения", "Engineering allowance"),
        ("electrical", "Электрика", "Engineering allowance"),
    ):
        add(machine, name, old_mechanical[key], allowance[key], source)
    target_kg, limit_kg = data["criteria"]["C-MASS-01"]["target_kg"], data["criteria"]["C-MASS-01"]["max_kg"]
    machine_old = fsum(row["T13_kg"] for row in machine)
    machine_new = fsum(row["T15_kg"] for row in machine)
    reserves = {
        "DB_NG32_125_to_270_L_min_to_sized_cartridges": cfg["round2"]["low_flow_reliefs_savings_kg_range"],
        "combined_2WRCE_manifolds": cfg["round2"]["combined_2WRCE_manifolds_savings_kg_range"],
    }
    return {
        "unconfirmed_low_cost_reserve_rows_kg": reserves,
        "machine_column_if_low_cost_reserves_realized_kg": [
            machine_new - fsum(bounds[i] for bounds in reserves.values()) for i in (1, 0)
        ],
        "station_rows": station, "station_T13_kg": station_old, "station_T15_kg": station_new,
        "machine_rows": machine, "machine_T13_budget_kg": machine_old, "machine_T15_column_kg": machine_new,
        "machine_T15_welded_kg": machine_new + frame["welded"]["total_kg"] - frame["column"]["total_kg"],
        "target_kg": target_kg, "limit_kg": limit_kg, "excess_to_target_kg": machine_new - target_kg,
        "margin_to_limit_kg": limit_kg - machine_new,
        "moving_mass_cap_kg": original["mass"]["remaining_crosshead_and_punch_kg"],
        "moving_mass_margin_kg": original["mass"]["remaining_crosshead_and_punch_kg"] - allowance["crosshead_punch"],
        "further_candidates_kg_ranges": {
            "rear_head_insert_net_after_frame_reinforcement": [50, 95],
            "profile_and_pocket_end_plates_outside_force_path": [70, 130],
            "lighten_feeder_guard_supports": [35, 65],
        },
    }


def short_transients(cfg, original):
    hold = original["cycles"]["physical_36_kW"]["decompression"]
    return_pa = 0.5
    bound_bar = 1.0  # The PTs can over-read by as much as 2 bar.
    start_bar = 264
    oil_cd = 0.56
    density_kg_m3 = cfg["oil_density_kg_m3"]
    aperture_m2 = area_mm2(8.5) / 1e6
    compliance_m3_Pa = (hold["cap_volume_L"] / 1000) * 2 / 1.4e9
    # Series valve adds little restriction: equivalent area at Cd when q=1100 L/min at 5 bar.
    wrce_area_times_cd_m2 = (1100 / 60000) / sqrt(2 * 5e5 / density_kg_m3)
    combined_area_times_cd_m2 = 1 / sqrt((oil_cd * aperture_m2) ** -2 + wrce_area_times_cd_m2 ** -2)
    rate = combined_area_times_cd_m2 * sqrt(2 / density_kg_m3)
    decompression_s = 2 * compliance_m3_Pa * (sqrt((start_bar - return_pa) * 1e5)
                                             - sqrt((bound_bar - return_pa) * 1e5)) / rate
    return {
        "decompression_s": decompression_s, "return_steady_bar": return_pa,
        "release_actual_bar_for_worst_overread": bound_bar, "orifice_window_s": hold["available_orifice_time_s"],
        "fault_DB_capacity_L_min": 650, "fault_DB_design_L_min": 480,
        "DB_peak_verification": "Pressure override, tank backpressure and relief opening transient require bench validation.",
        "pilot_acc_available_150_to_120_L": 9.3 * ((101 / 121) ** (1 / 1.4) - (101 / 151) ** (1 / 1.4)),
    }


def main():
    data = read_yaml(HERE / "sources.yaml")
    cfg = data["project"]
    criteria = read_yaml(ROOT / "ops/criteria/design_criteria.yaml")["criteria"]
    data["criteria"] = criteria
    original = read_json(ROOT / cfg["upstream_cylinder_results"])
    drive = read_json(ROOT / cfg["upstream_drive"])
    cylinders = {c["id"]: c for c in read_yaml(ROOT / cfg["upstream_cylinders"])["cylinders"]}
    circuit = read_yaml(CIRCUIT)
    cylinder = cylinder_screen(cylinders["CY-MAIN"], cfg, criteria)
    frame = frame_screen(cfg, criteria)
    interlocks = read_yaml(INTERLOCKS)
    round2 = screen(circuit, data, cylinders["CY-MAIN"]["cap_dead_L"])
    cycle, trace, switch_s = cycle_screen(cfg, original, round2, interlocks)
    round2["pilot"].update(pilot_cycle(circuit, interlocks, data, trace, round2["pilot"], switch_s))
    tank, cooling = tank_and_cooling(cylinders, cfg, data["catalogs"], drive, criteria,
                                     round2, cycle["round2_nominal"]["cycle_s"])
    budget = mass_rows(circuit, cylinders, original, drive, cylinder, frame, tank, cooling, data)
    transients = short_transients(cfg, original)
    output = HERE / "results.json"
    results = read_json(output) if output.exists() else {}
    results.update(mass=budget, main_cylinder=cylinder, frame=frame, tank=tank,
                   cooling=cooling, transients=transients, cycle=cycle, round2=round2)
    write_json(output, results)
    write_json(ROOT / "metrics.json", {
        "task": "T-1.5",
        "machine_column_kg": budget["machine_T15_column_kg"],
        "machine_welded_kg": budget["machine_T15_welded_kg"],
        "station_kg": budget["station_T15_kg"],
        "machine_column_if_low_cost_reserves_realized_kg": budget["machine_column_if_low_cost_reserves_realized_kg"],
        "tank_margin_above_minimum_L": tank["margin_above_minimum_L"],
        "pilot_theoretical_L_min": round2["pilot"]["theoretical_L_min"],
        "pilot_charge_balance_L_per_cycle": round2["pilot"]["net_per_cycle_L"],
        "pilot_total_theoretical_L_min": round2["pilot"]["combined_theoretical_L_min"],
        "rapid_pair_float_drag_N": round2["float"]["max_rapid_pair_drag_N"],
        "cap_dump_single_branch_at_265_L_min_bar": round2["emergency_dump"]["branches"][0]["single_open_branch_at_full_pump_bar"],
        "TF_oil_relief_point_L_min": round2["TF_oil_relief"]["estimated_flow_L_min"],
        "machine_margin_to_limit_kg": budget["margin_to_limit_kg"],
        "cycle_round2_nominal_s": cycle["round2_nominal"]["cycle_s"],
        "cycle_round2_delta_s": cycle["round2_nominal"]["delta_to_reference_s"],
        "cycle_round2_with_T13_allowance_s": cycle["round2_nominal"]["with_T13_physical_allowance_s"],
        "cycle_round2_adverse_with_T13_allowance_s": cycle["round2_adverse_envelope"]["with_T13_physical_allowance_s"],
        "rapid_float_delta_s": cycle["rapid_float_only"]["delta_s"],
        "rms_round2_shaft_kW": cycle["round2_nominal"]["rms_shaft_kW"],
        "main_cylinder_kg": cylinder["filled_kg"],
        "frame_force_N": frame["design_load_N"],
        "main_tank_oil_L": tank["nominal_main_oil_L"], "local_tank_oil_L": tank["local_nominal_oil_L"],
        "heat_capacity_kW": cooling["heat_capacity_kW"], "heat_load_kW": cooling["heat_load_kW"],
        "installed_kW": cooling["installed_total_kW"], "power_set_kW": 36,
        "working_limit_bar": criteria["C-HYD-01"]["max_working_bar"],
        "relief_limit_bar": criteria["C-HYD-01"]["max_relief_bar"],
        "cycle_reference_36_kW_s": cycle["reference_36_kW"]["cycle_s"],
        "pilot_takeoff_delta_s": cycle["pilot_takeoff_bound"]["delta_s"],
        "cycle_T13_nominal_physical_s": cycle["T13_nominal_physical_s"],
        "cycle_combined_pessimistic_s": {key: item["cycle_s"]
                                         for key, item in cycle["combined_pessimistic"].items()},
        "peak_reference_shaft_kW": cycle["reference_36_kW"]["peak_shaft_kW"],
        "rms_reference_shaft_kW": cycle["reference_36_kW"]["rms_shaft_kW"],
        "decompression_s": transients["decompression_s"],
    })
    print(f"Machine mass {budget['machine_T15_column_kg']:.1f} kg (column frame)")
    assert budget["machine_T15_column_kg"] <= budget["limit_kg"]
    assert budget["moving_mass_margin_kg"] >= 0
    assert cylinder["static_screen_pass"] and frame["column"]["screen_pass"]
    assert cooling["installed_total_kW"] <= cooling["installed_limit_kW"]
    assert cooling["circulation_required_shaft_kW"] < cooling["installed_kW"]["cooler_circulation"]
    assert tank["calculated_low_inventory_L"] >= tank["minimum_level_L"]
    assert tank["local_oil_min_after_full_net_stroke_L"] >= tank["ZSF_case2_min_L"]
    assert transients["decompression_s"] <= transients["orifice_window_s"]
    assert cooling["design_margin_kW"] >= 0
    assert all(row["static_screen_pass"] for row in round2["emergency_dump"]["branches"])
    assert round2["TF_oil_relief"]["static_screen_pass"]
    assert round2["pilot"]["periodic_balance_screen_pass"] and round2["pilot"]["ax_depletion_screen_pass"]
    nominal = cycle["round2_nominal"]
    assert nominal["delta_to_reference_s"] <= 0.1
    assert nominal["with_T13_physical_allowance_s"] <= criteria["C-PERF-01"]["max_cycle_s"]
    assert nominal["rms_shaft_kW"] <= criteria["C-PWR-01"]["max_rms_kW"]
    assert nominal["average_shaft_kW"] <= criteria["C-PWR-01"]["max_main_kW"]
    assert nominal["peak_shaft_kW"] <= criteria["C-PWR-01"]["max_peak_kW"]
    assert nominal["pre_up_command_to_cam_exit_s"] <= interlocks["phases"]["pre_up"]["movement_window"]["timeout_s"]


if __name__ == "__main__":
    main()
