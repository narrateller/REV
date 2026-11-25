"""Analytical checks for the cover ports, ZUP drain and mass options."""
from math import fsum, hypot, pi, sin, sqrt


def area_mm2(diameter_mm):
    return pi * diameter_mm**2 / 4


def flow_velocity_m_s(flow_L_min, passage_mm2):
    return flow_L_min / (0.06 * passage_mm2)


def drain_screen(cfg, rho_kg_m3):
    diameter_m = cfg["ID_mm"] / 1000
    velocity_m_s = flow_velocity_m_s(cfg["max_oil_flow_L_min"], area_mm2(cfg["ID_mm"]))
    reynolds_number = velocity_m_s * diameter_m / (cfg["max_kinematic_viscosity_mm2_s"] * 1e-6)
    friction_factor = max(64 / reynolds_number, 0.05)
    line_bar = (friction_factor * cfg["length_m"] / diameter_m + cfg["sum_local_K"]) * (
        rho_kg_m3 * velocity_m_s**2 / 2e5)
    static_bar = rho_kg_m3 * 9.81 * cfg["submerged_depth_m"] / 1e5
    total_bar = line_bar + static_bar + cfg["tank_air_pressure_bound_bar"]
    viscosity_hot_mm2_s = 25
    hot_re = reynolds_number * cfg["max_kinematic_viscosity_mm2_s"] / viscosity_hot_mm2_s
    return {
        "flow_L_min": cfg["max_oil_flow_L_min"], "velocity_m_s": velocity_m_s,
        "cold_Re": reynolds_number, "hot_Re": hot_re,
        "line_drop_bar": line_bar, "static_head_bar": static_bar,
        "total_backpressure_bar": total_bar, "limit_bar": 2, "pass": total_bar <= 2,
    }


def cover_and_tube(main, baseline_static, relief_bar, suction_flow_L_min, minimum_factor):
    """Extend the inherited static screen to the narrower preloaded tube."""
    previous = baseline_static["static_safety_factors"]
    stress = baseline_static["tube"]
    body_yield_MPa = main["barrel_and_cover_Rp02_min_MPa"]
    transition_factor = stress["local_bound_MPa"] / stress["with_preload_VM_MPa"]
    ties = main["tie_rods"]
    ri_mm = main["bore_mm"] / 2
    ro_mm = ri_mm + main["barrel_wall_min_mm"]
    p_MPa = relief_bar / 10
    tube_area_mm2 = pi * (ro_mm**2 - ri_mm**2)
    preload_N = baseline_static["tied_joint"]["target_preload_each_N"] * ties["n"]
    hoop_MPa = p_MPa * (ro_mm**2 + ri_mm**2) / (ro_mm**2 - ri_mm**2)
    axial_pressure_MPa = p_MPa * ri_mm**2 / (ro_mm**2 - ri_mm**2)

    def vm_MPa(axial_MPa):
        return sqrt(((hoop_MPa + p_MPa)**2 + (hoop_MPa - axial_MPa)**2
                     + (-p_MPa - axial_MPa)**2) / 2)

    tube_bound_MPa = max(vm_MPa(axial_pressure_MPa), vm_MPa(-preload_N / tube_area_mm2)) * transition_factor
    ann = main["annulus_port_distribution"]
    cap = main["main_prefill_port"]
    ann_hole_pitch_mm = ann["hole_PCD_mm"] * sin(pi / ann["small_bores_n"])
    ligament_mm = ann_hole_pitch_mm - ann["small_bores_mm"]
    inner_ligament_mm = (ann["hole_PCD_mm"] - ann["small_bores_mm"] - main["rod_mm"]) / 2
    outer_ligament_mm = (main["bore_mm"] - ann["hole_PCD_mm"] - ann["small_bores_mm"]) / 2
    # The base axisymmetric check covers bolt holes. Also evaluate at the
    # port ring with its local circumferential net section.
    radius_mm = ann["hole_PCD_mm"] / 2
    rod_radius_mm = main["rod_mm"] / 2
    thickness_mm = main["cover_thickness_front_mm"]
    net_fraction = ligament_mm / ann_hole_pitch_mm
    old_ligament_fraction = baseline_static["tied_joint"]["cover_ligament_fraction"]
    front = baseline_static["front_cover"]
    detail_factor = (front["local_combined_bound_MPa"] * old_ligament_fraction
                     / hypot(front["section_bending_MPa"] + p_MPa, sqrt(3) * front["section_shear_MPa"]))
    port_stress_MPa = 0.0
    for station_mm in (radius_mm - ann["small_bores_mm"] / 2, radius_mm,
                       radius_mm + ann["small_bores_mm"] / 2):
        loaded_mm = min(station_mm, ri_mm)
        force_per_width_N_mm = p_MPa * (loaded_mm**2 - rod_radius_mm**2) / (2 * station_mm)
        moment_per_width_N = p_MPa * (
            station_mm * (loaded_mm**2 - rod_radius_mm**2) / 2
            - (loaded_mm**3 - rod_radius_mm**3) / 3) / station_mm
        local_MPa = detail_factor / net_fraction * hypot(6 * moment_per_width_N / thickness_mm**2 + p_MPa,
                                                        sqrt(3) * 1.5 * force_per_width_N_mm / thickness_mm)
        port_stress_MPa = max(port_stress_MPa, local_MPa)
    factors = previous | {"tube": body_yield_MPa / tube_bound_MPa,
                          "front_cover_port_ring": body_yield_MPa / port_stress_MPa}
    rod_flow_L_min = suction_flow_L_min * (1 - (main["rod_mm"] / main["bore_mm"])**2)
    velocities = {
        "rear_cap_port_m_s": flow_velocity_m_s(suction_flow_L_min, area_mm2(cap["bore_mm"])),
        "front_annulus_holes_m_s": flow_velocity_m_s(rod_flow_L_min,
            ann["small_bores_n"] * area_mm2(ann["small_bores_mm"])),
        "front_annulus_line_m_s": flow_velocity_m_s(rod_flow_L_min, area_mm2(ann["line_ID_mm"])),
    }
    return {
        "relief_pressure_bar": relief_bar, "total_preload_N": preload_N,
        "tube_local_vm_MPa": tube_bound_MPa, "front_ports_local_bound_MPa": port_stress_MPa,
        "component_yield_factors": factors, "minimum_yield_factor": min(factors.values()),
        "static_pass": min(factors.values()) >= minimum_factor,
        "suction_cap_L_min": suction_flow_L_min, "suction_rod_L_min": rod_flow_L_min,
        "suction_velocities_m_s": velocities, "suction_pass": max(velocities.values()) <= 6,
        "front_hole_net_ligaments_mm": {"between_holes": ligament_mm, "to_rod_diameter": inner_ligament_mm,
                                        "to_bore_diameter": outer_ligament_mm},
        "suction_and_stress_basis": "T-1.3 cover strip screen and identical retained oil passage geometry.",
    }


def mass_measures(data, circuit, main, original_static, prior):
    cfg = data["revision"]["mass"]
    frame = data["project"]["structure"]
    rho = cfg["steel_density_kg_m3"]
    kg_per_mm3 = rho / 1e9
    plate = cfg["plate_trim"]
    old_x, old_y, t = frame["column_plate_dims_mm"]
    x, y = plate["length_mm"], plate["width_mm"]
    plate_change_kg = 2 * (x * y - old_x * old_y) * t * kg_per_mm3
    edges_mm = [(x - frame["column_plate_support_span_mm"] - plate["bolt_seat_diameter_mm"]) / 2,
                (y - plate["transverse_bolt_span_mm"] - plate["bolt_seat_diameter_mm"]) / 2]
    longitudinal_MPa = prior["frame"]["column"]["end_plates"]["stress_range_MPa"]
    # Orthogonal simply supported strip at full machine load.
    transverse_span = plate["transverse_bolt_span_mm"]
    transverse_MPa = frame["frame_load_N"] * (2 * transverse_span - main["bore_mm"]) / 8 / (x * t**2 / 6)
    tank = cfg["tank_base"]
    width_mm, height_mm = tank["RHS_outer_mm"]
    wall_mm = tank["RHS_thickness_mm"]
    rhs_mm2 = width_mm * height_mm - (width_mm - 2 * wall_mm) * (height_mm - 2 * wall_mm)
    rx, ry, rt = tank["reinforcement_plate_dims_mm"]
    tank_base_new_parts_kg = tank["reinforcement_plates_n"] * rx * ry * rt * kg_per_mm3
    skid_members_kg = tank["crossmembers_to_share"] * tank["crossmember_length_mm"] * rhs_mm2 * kg_per_mm3
    integ = cfg["integrated_rear_cover"]
    heads = main["tie_rods"]
    head_removed_kg = ((area_mm2(main["cover_OD_mm"]) - area_mm2(main["work_port_passage_ID_mm"]["cap"])
                        - heads["n"] * area_mm2(heads["hole_diameter_mm"]))
                       * main["cover_thickness_rear_mm"] * kg_per_mm3)
    rear_frame_added_kg = x * y * integ["extra_thickness_mm"] * kg_per_mm3
    integrated_bound_MPa = original_static["rear_cover"]["local_combined_bound_MPa"] + longitudinal_MPa
    db = cfg["cartridges"]
    hx, hy, hz = db["housing_steel_dims_mm"]
    housing_kg = (hx * hy - area_mm2(db["housing_bore_ID_mm"])) * hz * kg_per_mm3
    cartridge_change_kg = len(db["candidates"]) * (db["cartridge_RPIC_kg"] + housing_kg - db["existing_DB30_kg"])
    tf = cfg["TF_pair"]
    inlet_bar = 1.1 * tf["pressure_set_bar"]
    corrected_one_flow_L_min = (tf["reference_water_flow_m3_h"] * 1000 / 60 *
        sqrt((inlet_bar - tf["backpressure_bar"]) / (1.1 * tf["reference_set_bar"]) *
             tf["reference_water_density_kg_m3"] / data["project"]["oil_density_kg_m3"]) *
        tf["liquid_viscosity_factor"])
    tank_header_kg = (area_mm2(tf["header_shell_OD_mm"]) - area_mm2(tf["header_shell_ID_mm"])) * (
        tf["header_length_mm"] * kg_per_mm3)
    tf_change_kg = (2 * tf["valve_bare_mass_kg"] + tank_header_kg + tf["hardware_allowance_kg"]
                    - data["catalogs"]["GOETZE"]["mass_kg"] - 5)
    group_changes = {}
    for name, group in cfg["shared_blocks"]["groups"].items():
        pitch_mm, width_mm, height_mm = group["cell_dims_mm"]
        count = len(group["valves"])
        end_mm = group["side_wall_mm"]
        individual_kg = count * (pitch_mm + 2 * end_mm) * width_mm * height_mm * kg_per_mm3
        unified_kg = (count * pitch_mm + 2 * end_mm) * width_mm * height_mm * kg_per_mm3
        group_changes[name] = {"standalone_blank_kg": individual_kg, "shared_blank_kg": unified_kg,
                               "geometric_savings_kg": individual_kg - unified_kg}
    return {
        "plate_trim": {"delta_kg": plate_change_kg, "seat_free_edges_mm": edges_mm,
                       "longitudinal_range_MPa": longitudinal_MPa, "transverse_range_MPa": transverse_MPa,
                       "retained_support_span_mm": frame["column_plate_support_span_mm"],
                       "retained_effective_width_mm": frame["column_plate_effective_width_mm"],
                       "edge_screen_pass": min(edges_mm) >= plate["edge_target_mm"]},
        "tank_as_base": {"delta_kg": tank_base_new_parts_kg - skid_members_kg,
                        "replaced_RHS_kg": skid_members_kg, "added_plates_kg": tank_base_new_parts_kg},
        "integrated_rear_cover": {"delta_kg": rear_frame_added_kg + integ["additional_hardware_allowance_kg"]
                                   - head_removed_kg, "removed_head_kg": head_removed_kg,
                                 "added_frame_kg": rear_frame_added_kg,
                                 "combined_local_screen_MPa": integrated_bound_MPa,
                                 "candidate_yield_factor": integ["concept_material_Rp02_min_MPa"] / integrated_bound_MPa},
        "DB_to_cartridges": {"delta_kg": cartridge_change_kg, "local_housing_kg_each": housing_kg,
                            "design_flows_L_min": {tag: circuit["elements"][tag]["Q_L_min"]
                                                   for tag in db["candidates"]},
                            "requires_dynamic_315_bar_qualification": True},
        "TF_oil_relief_pair": {"delta_kg": tf_change_kg, "two_valves_flow_bound_L_min": 2 * corrected_one_flow_L_min,
                               "outlet_limit_bar": tf["backpressure_bar"], "inlet_pressure_bar": inlet_bar,
                               "required_L_min": circuit["elements"]["RTF"]["Q_L_min"],
                               "individual_capacity_L_min": corrected_one_flow_L_min},
        "manifold_blocks": {"groups": group_changes, "geometric_savings_kg": fsum(
            item["geometric_savings_kg"] for item in group_changes.values()),
            "accountable_credit_kg": 0,
            "basis": "Comparison of hypothetical blanks. T-1.5 did not itemize the individual baseplate inventory."},
        "status": "Conditional estimates for candidate changes. Structural interfaces and relief qualification remain open.",
    }


def manifold_loss_screen(circuit, cfg, rho_kg_m3):
    """Leave the unallocated pressure differential for filters/seats/tubes."""
    elements = circuit["elements"]
    loss = {}
    for name, valve, limit in zip(("inlet", "return", "regen"), ("MP", "MT", "MR"),
                                  cfg["loss_budgets_bar"]):
        item = elements[valve]
        flow_L_min = item["Q_L_min"]
        full_open_bar = 5 * (flow_L_min / item["catalog_flow_at_5bar_L_min"])**2
        velocity_m_s = flow_velocity_m_s(flow_L_min, area_mm2(cfg["passage_ID_mm"]))
        friction_term = cfg["darcy_friction_bound"] * cfg["passage_length_m"] / (cfg["passage_ID_mm"] / 1000)
        passage_bar = (friction_term + cfg["passage_local_K"]) * rho_kg_m3 * velocity_m_s**2 / 2e5
        loss[name] = {
            "flow_L_min": flow_L_min, "velocity_m_s": velocity_m_s, "valve_drop_bar": full_open_bar,
            "block_passage_drop_bar": passage_bar, "budget_bar": limit,
            "remainder_for_external_path_bar": limit - full_open_bar - passage_bar,
        }
    return loss
