"""Station inventory in the current geometry, following T-1.5 tank sizing."""
from math import fsum, pi


def inventory(data16, design16, cylinders17, cylinder_data16, pilot, representative, max_L_min,
              installed_circulation_L_min, motor_kg, pump_kg, additions_kg=0.):
    project = data16["project"]
    rows = {row["node"]: row["round2_kg"] for row in design16["mass"]["station_rows"]}
    basis_kg = fsum(rows.values())
    current = {row["id"]: row for row in cylinders17["cylinders"]}
    cylinders = {row["id"]: row | current.get(row["id"], {}) for row in cylinder_data16["cylinders"]}
    if "CY-RAPID" not in cylinders:
        cylinders["CY-RAPID"] = current["CY-RAPID"] | dict(bore_mm=90, rod_mm=50, n=2)
    for name, row in current.items():
        if name in cylinders:
            cylinders[name].update(row)
    volumes = {}
    for name, cylinder in cylinders.items():
        swept_L = pi / 4 * cylinder["stroke_installed_mm"] * cylinder.get("n", 1) / 1e6
        cap_L = swept_L * cylinder["bore_mm"]**2
        rod_L = swept_L * cylinder["rod_mm"]**2
        volumes[name] = dict(cap_L=cap_L, rod_L=rod_L, annulus_L=cap_L - rod_L)
    reserve_L = project["main_tank_loss_reserve_L"]
    lp_charge_L = 18.4 * (1 - (29 / 53)**(1 / 1.4))
    pilot_charge_L = pilot["effective_gas_volume_L"] * (
        1 - ((pilot["precharge_bar"] + 1) / (data16["revision"]["pilot"]["max_pilot_bar"] + 1))**(1 / 1.4))
    flush_and_aux_L = 5.
    withdrawal_L = fsum(row["cap_L"] for row in volumes.values()) + lp_charge_L + pilot_charge_L + flush_and_aux_L
    minimum_level_L = project["level_min_main_L"]
    working_L = project["tank_nominal_oil_L"]
    calculated_min_L = working_L - withdrawal_L - reserve_L
    x_mm, y_mm, z_mm = project["tank_dims_mm"]
    gross_L = x_mm * y_mm * z_mm / 1e6
    main = volumes["CY-MAIN"]
    main_dead_L = cylinders["CY-MAIN"].get("cap_dead_L", .8)
    local_min_L = 1.5 * (main["cap_L"] + main_dead_L)
    local_oil_L = project["buffer_nominal_oil_L"]
    oil_kg_per_L = project["oil_density_kg_m3"] / 1000
    mean_main_L_min = representative["pump_oil_L"] * 60 / representative["cycle_s"]
    mean_circulating_L_min = mean_main_L_min + pilot["combined_theoretical_L_min"] + installed_circulation_L_min
    max_circulating_L_min = max_L_min + pilot["combined_theoretical_L_min"] + installed_circulation_L_min
    residence_s = 60 * minimum_level_L / max_circulating_L_min
    trial_reduction_L = 5.
    trimmed_level_L = calculated_min_L - trial_reduction_L
    candidate_rows = rows | {"Мотор, насос, муфта": motor_kg + pump_kg}
    if additions_kg:
        candidate_rows["Адаптация привода или шкаф ПЧ"] = additions_kg
    station_kg = fsum(candidate_rows.values())
    minimum_nominal_inventory_L = minimum_level_L + withdrawal_L + reserve_L
    return dict(
        station_reference_D1_kg=1655, reproduced_T16_station_kg=basis_kg, station_kg=station_kg,
        delta_from_D1_kg=station_kg - 1655, mass_items_kg=candidate_rows,
        estimated_machine_with_station_delta_kg=4923 + (station_kg - 1655),
        with_5_L_less_initial_oil_screen_kg=station_kg - trial_reduction_L * oil_kg_per_L,
        station_frame_kg=rows["Рама станции"], main_tank_shell_kg=rows["Основной бак"],
        power_unit_motor_and_pump_kg=motor_kg + pump_kg,
        main_oil_kg=working_L * oil_kg_per_L, local_oil_kg=local_oil_L * oil_kg_per_L,
        combined_tank_oil_kg=(working_L + local_oil_L) * oil_kg_per_L,
        air_coolers_and_mounts_kg=rows["Охладитель с вентилятором"],
        tank=dict(gross_L=gross_L, main_nominal_oil_L=working_L, local_gross_L=project["buffer_gross_L"],
                  upper_inventory_L=project["upper_oil_inventory_L"],
                  local_nominal_oil_L=local_oil_L, local_oil_after_net_full_stroke_L=local_oil_L - main["rod_L"],
                  local_required_oil_L=local_min_L, main_tank_minimum_level_L=minimum_level_L,
                  calculated_low_oil_L=calculated_min_L, minimum_nominal_inventory_L=minimum_nominal_inventory_L,
                  calculated_low_oil_after_5_L_trim_L=trimmed_level_L,
                  trim_inventory_screen_pass=trimmed_level_L >= minimum_level_L,
                  maximum_paper_saving_oil_kg=max(0., working_L - minimum_nominal_inventory_L) * oil_kg_per_L,
                  full_sweep_and_charge_withdrawal_L=withdrawal_L, reserve_L=reserve_L,
                  branch_swept_volumes=volumes, residence_at_max_s=residence_s,
                  residence_at_mean_s=60 * minimum_level_L / mean_circulating_L_min,
                  deaeration_target_s=project["tank_baffle_deaeration_target_s"],
                  inventory_pass=(calculated_min_L >= minimum_level_L
                                  and local_oil_L - main["rod_L"] >= local_min_L)),
    )

