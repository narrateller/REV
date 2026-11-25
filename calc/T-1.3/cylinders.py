"""T-1.3 physical cylinders, hydraulic loads and replay of the V2 cycle."""

from dataclasses import replace
from math import hypot, pi, sin, sqrt
from pathlib import Path
import json
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "v2"))
import drive
from x1_calc import BAR_PA, area_m2, supply_bar

OIL_L_PER_M3 = 1000
FLOW_FACTOR = 60000
M_TO_MM = 1000


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def area_mm2(diameter_mm):
    return area_m2(diameter_mm) * 1e6


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def axial_force_N(ram, header_bar, losses_bar, mode):
    """Useful output with V2's inlet loss, opposite pressure and cylinder efficiency."""
    inlet_bar, tank_bar, regen_bar = losses_bar
    main_area_m2, opposing_area_m2, backpressure_bar = {
        "extend": (ram.cap_m2, ram.annulus_m2, tank_bar),
        "retract": (ram.annulus_m2, ram.cap_m2, tank_bar),
        "regen": (ram.rod_m2, ram.annulus_m2, regen_bar),
    }[mode]
    return ram.eta * BAR_PA * ((header_bar - inlet_bar) * main_area_m2
                              - backpressure_bar * opposing_area_m2)


def phase(ram, count, mode, speed_m_s, load_N, losses_bar, reserve_factor=1):
    inlet_bar, tank_bar, regen_bar = losses_bar
    required_bar = supply_bar(ram, load_N, mode, losses_bar)
    return {
        "mode": mode,
        "speed_limit_m_s": speed_m_s,
        "required_force_total_N": count * load_N,
        "required_force_with_reserve_total_N": count * load_N * reserve_factor,
        "header_pressure_bar": required_bar,
        "header_pressure_with_reserve_bar": supply_bar(ram, load_N * reserve_factor, mode, losses_bar),
        "hydraulic_pressures_bar": (
            {"cap": required_bar - inlet_bar, "annulus": required_bar - inlet_bar + regen_bar}
            if mode == "regen" else
            ({"cap": required_bar - inlet_bar, "annulus": tank_bar} if mode == "extend"
             else {"cap": tank_bar, "annulus": required_bar - inlet_bar})
        ),
        "push_at_header_per_cylinder_N": axial_force_N(ram, required_bar, losses_bar, "extend"),
        "pull_at_header_per_cylinder_N": axial_force_N(ram, required_bar, losses_bar, "retract"),
        "available_force_in_mode_per_cylinder_N": axial_force_N(ram, required_bar, losses_bar, mode),
        "cap_flow_per_cylinder_L_min": FLOW_FACTOR * ram.cap_m2 * speed_m_s,
        "annulus_flow_per_cylinder_L_min": FLOW_FACTOR * ram.annulus_m2 * speed_m_s,
        "supply_flow_total_L_min": count * FLOW_FACTOR * speed_m_s * {
            "extend": ram.cap_m2, "retract": ram.annulus_m2, "regen": ram.rod_m2}[mode],
    }


def pressure_forces(ram, n, losses_bar, working_bar, relief_bar):
    values = {}
    for bar in (working_bar, relief_bar):
        values[str(bar)] = {
            "gross_push_per_cylinder_N": BAR_PA * bar * ram.cap_m2,
            "gross_pull_per_cylinder_N": BAR_PA * bar * ram.annulus_m2,
            "net_push_per_cylinder_N": axial_force_N(ram, bar, losses_bar, "extend"),
            "net_pull_per_cylinder_N": axial_force_N(ram, bar, losses_bar, "retract"),
            "net_push_total_N": n * axial_force_N(ram, bar, losses_bar, "extend"),
            "net_pull_total_N": n * axial_force_N(ram, bar, losses_bar, "retract"),
        }
    return values


def von_mises_MPa(a_MPa, b_MPa, c_MPa):
    return sqrt(((a_MPa - b_MPa)**2 + (b_MPa - c_MPa)**2 + (c_MPa - a_MPa)**2) / 2)


def metric_thread_area_mm2(diameter_mm, pitch_mm):
    return area_mm2(diameter_mm - .9382 * pitch_mm)


def bending_MPa(force_N, eccentricity_mm, diameter_mm):
    return force_N * eccentricity_mm / (pi * diameter_mm**3 / 32)


def cover_screen(p_MPa, loaded_start_mm, loaded_end_mm, support_mm, thickness_mm, detail_factor, net_fraction):
    """Axisymmetric radial strip equilibrium, rectangular section and local allowance."""
    bending_max_MPa = shear_max_MPa = local_max_MPa = 0.
    for i in range(1, 1001):
        r_mm = loaded_start_mm + (support_mm - loaded_start_mm) * i / 1000
        b_mm = min(r_mm, loaded_end_mm)
        a_mm = loaded_start_mm
        # Integrating p*r dr per radian, then dividing by section width r.
        per_width_N_mm = p_MPa * (b_mm**2 - a_mm**2) / (2 * r_mm)
        moment_per_width_N = p_MPa * (r_mm * (b_mm**2 - a_mm**2) / 2
                                      - (b_mm**3 - a_mm**3) / 3) / r_mm
        bend_MPa = 6 * moment_per_width_N / thickness_mm**2
        shear_MPa = 1.5 * per_width_N_mm / thickness_mm
        bending_max_MPa = max(bending_max_MPa, bend_MPa)
        shear_max_MPa = max(shear_max_MPa, shear_MPa)
        # Add normal pressure in the VM envelope and use the perforated section
        # factor over the whole lid, including regions without the bolt holes.
        local_max_MPa = max(local_max_MPa, detail_factor / net_fraction
                            * hypot(bend_MPa + p_MPa, sqrt(3) * shear_MPa))
    return {"section_bending_MPa": bending_max_MPa, "section_shear_MPa": shear_max_MPa,
            "local_combined_bound_MPa": local_max_MPa}


def stability(force_N, d_core_mm, length_mm, E_MPa, yield_MPa):
    radius_of_gyration_mm = d_core_mm / 4
    slenderness = length_mm / radius_of_gyration_mm
    euler_MPa = pi**2 * E_MPa / slenderness**2
    transition = sqrt(2 * pi**2 * E_MPa / yield_MPa)
    johnson_MPa = yield_MPa * (1 - yield_MPa * slenderness**2 / (4 * pi**2 * E_MPa))
    governing_MPa = johnson_MPa if slenderness < transition else euler_MPa
    core_area_mm2 = area_mm2(d_core_mm)
    return {
        "Le_mm": length_mm,
        "slenderness": slenderness,
        "Euler_Johnson_transition_slenderness": transition,
        "method": "Johnson" if slenderness < transition else "Euler",
        "Euler_critical_N": euler_MPa * core_area_mm2,
        "governing_critical_N": governing_MPa * core_area_mm2,
        "safety_factor": governing_MPa * core_area_mm2 / force_N,
    }


def structure(key, spec, ram, relief_bar, common, assumptions, min_yield_factor):
    bore_radius_mm = spec["bore_mm"] / 2
    rod_radius_mm = spec["rod_mm"] / 2
    wall_mm = spec["tube_wall_mm"] - spec["wall_minus_tolerance_mm"]
    outside_radius_mm = bore_radius_mm + wall_mm
    support_radius_mm = spec["tie_PCD_mm"] / 2
    p_MPa = relief_bar / 10
    push_N = p_MPa * ram.cap_m2 * 1e6
    pull_N = p_MPa * ram.annulus_m2 * 1e6
    body_yield_MPa = common["barrel_and_cover_Rp02_min_MPa"]
    rod_yield_MPa = spec["rod_Rp02_min_MPa"]

    tie_area_mm2 = metric_thread_area_mm2(spec["tie_diameter_mm"], spec["tie_pitch_mm"])
    all_ties_mm2 = spec["tie_n"] * tie_area_mm2
    tie_yield_MPa = common["tie_Rp02_min_MPa"]
    preload_MPa = tie_yield_MPa * common["tie_preload_fraction"]
    preload_total_N = preload_MPa * all_ties_mm2
    factored_service_N = common["tie_local_service_load_factor"] * push_N
    tie_stress_MPa = preload_MPa + factored_service_N / all_ties_mm2

    tube_area_mm2 = area_mm2(2 * outside_radius_mm) - area_mm2(spec["bore_mm"])
    a2_mm2, b2_mm2 = bore_radius_mm**2, outside_radius_mm**2
    hoop_MPa = p_MPa * (b2_mm2 + a2_mm2) / (b2_mm2 - a2_mm2)
    radial_MPa = -p_MPa
    closed_axial_MPa = p_MPa * a2_mm2 / (b2_mm2 - a2_mm2)
    preload_compressive_MPa = preload_total_N / tube_area_mm2
    closed_vm_MPa = von_mises_MPa(hoop_MPa, radial_MPa, closed_axial_MPa)
    preloaded_vm_MPa = von_mises_MPa(hoop_MPa, radial_MPa, -preload_compressive_MPa)
    barrel_screen_MPa = common["tube_transition_stress_factor"] * max(closed_vm_MPa, preloaded_vm_MPa)
    # Use inner-bore stresses, constant barrel length and same preload for sizing the minimum wall.
    low_mm, high_mm = 0., spec["tube_wall_mm"]
    for _ in range(42):
        t_mm = (low_mm + high_mm) / 2
        b2 = (bore_radius_mm + t_mm)**2
        test_hoop = p_MPa * (b2 + a2_mm2) / (b2 - a2_mm2)
        test_axial = -preload_total_N / (pi * (b2 - a2_mm2))
        if common["tube_transition_stress_factor"] * von_mises_MPa(test_hoop, radial_MPa, test_axial) > body_yield_MPa / min_yield_factor:
            low_mm = t_mm
        else:
            high_mm = t_mm

    chord_mm = 2 * support_radius_mm * sin(pi / spec["tie_n"])
    net_fraction = 1 - spec["tie_hole_diameter_mm"] / chord_mm
    cover_rear_mm, cover_front_mm = spec["cover_thickness_mm"]
    rear = cover_screen(p_MPa, 0, bore_radius_mm, support_radius_mm, cover_rear_mm,
                        common["cover_detail_stress_factor"], net_fraction)
    front = cover_screen(p_MPa, rod_radius_mm, bore_radius_mm, support_radius_mm, cover_front_mm,
                         common["cover_detail_stress_factor"], net_fraction)
    port_mm = spec["cap_central_port_mm"]
    piston_lever_mm = bore_radius_mm - rod_radius_mm
    # Inner-rooted strips: conservative full bore pressure on the overhanging annulus.
    piston_unit_N_mm = p_MPa * (bore_radius_mm**2 - rod_radius_mm**2) / (2 * rod_radius_mm)
    piston_moment_unit_N = (p_MPa * (rod_radius_mm * piston_lever_mm**2 / 2 + piston_lever_mm**3 / 3)
                            / rod_radius_mm)
    piston_t_mm = spec["piston_thickness_mm"]
    piston_screen_MPa = 2 * hypot(6 * piston_moment_unit_N / piston_t_mm**2 + p_MPa,
                                 sqrt(3) * 1.5 * piston_unit_N_mm / piston_t_mm)

    main = key == "main"
    thread = spec["rod_end_thread"]
    rod_core_mm = spec["rod_core_mm"]
    thread_root_mm = thread["root_min_mm"]
    rod_axial_MPa = push_N / area_mm2(rod_core_mm)
    rod_bending_MPa = bending_MPa(push_N, spec["rod_eccentricity_mm"], rod_core_mm)
    thread_load_N = pull_N if main else push_N
    thread_local_MPa = assumptions["rod_thread_local_stress_factor"] * (
        thread_load_N / area_mm2(thread_root_mm)
        + bending_MPa(thread_load_N, spec["rod_eccentricity_mm"], thread_root_mm))
    thread_shear_area_mm2 = .5 * pi * thread_root_mm * thread["engagement_mm"]
    thread_equiv_strip_MPa = sqrt(3) * thread_load_N / thread_shear_area_mm2
    shoulder_area_mm2 = (area_mm2(assumptions["main_contact_outer_mm"])
                         - area_mm2(assumptions["main_contact_inner_mm"])) if main else None
    shoulder_local_MPa = (assumptions["main_shoulder_stress_factor"] * push_N / shoulder_area_mm2
                          if main else 0.)
    rod_screen_MPa = max(rod_axial_MPa + rod_bending_MPa, thread_local_MPa,
                         thread_equiv_strip_MPa, shoulder_local_MPa)
    length_mm = spec["stroke_mm"][1] + spec["column_end_offset_mm"]
    column = stability(push_N, rod_core_mm, length_mm, common["E_MPa"], rod_yield_MPa)
    column["without_external_guidance_K2"] = stability(
        push_N, rod_core_mm, 2 * length_mm, common["E_MPa"], rod_yield_MPa)
    column["K"] = 1
    column["load_N"] = push_N

    mounting_ring_area_mm2 = (area_mm2(spec["cover_OD_mm"]) - area_mm2(2 * outside_radius_mm)
                              - spec["tie_n"] * area_mm2(spec["tie_hole_diameter_mm"]))
    static_factors = {
        "tube": body_yield_MPa / barrel_screen_MPa,
        "piston": rod_yield_MPa / piston_screen_MPa,
        "rod": rod_yield_MPa / rod_screen_MPa,
        "rear_cover": body_yield_MPa / rear["local_combined_bound_MPa"],
        "front_cover": body_yield_MPa / front["local_combined_bound_MPa"],
        "tie_rods_with_preload": tie_yield_MPa / tie_stress_MPa,
        "front_support_average_bearing": body_yield_MPa / (push_N / mounting_ring_area_mm2),
    }
    return {
        "static_safety_factor_min": min(static_factors.values()),
        "static_safety_factors": static_factors,
        "tube": {"wall_min_after_allowance_mm": wall_mm,
                 "minimum_wall_for_screen_mm": high_mm,
                 "lame_radial_MPa": radial_MPa, "lame_hoop_MPa": hoop_MPa,
                 "lame_closed_axial_MPa": closed_axial_MPa, "lame_closed_VM_MPa": closed_vm_MPa,
                 "with_preload_VM_MPa": preloaded_vm_MPa, "local_bound_MPa": barrel_screen_MPa},
        "rear_cover": rear, "front_cover": front,
        "piston_local_bound_MPa": piston_screen_MPa,
        "rod": {"eccentricity_mm": spec["rod_eccentricity_mm"],
                "core_axial_MPa": rod_axial_MPa, "core_bending_MPa": rod_bending_MPa,
                "thread_local_MPa": thread_local_MPa, "thread_stripping_VM_MPa": thread_equiv_strip_MPa,
                "thrust_shoulder_local_MPa": shoulder_local_MPa, "screen_MPa": rod_screen_MPa},
        "tied_joint": {"tie_area_mm2": tie_area_mm2, "target_preload_each_N": preload_total_N / spec["tie_n"],
                       "preload_plus_factored_service_MPa": tie_stress_MPa,
                       "joint_opening_margin": common["tie_preload_min_fraction_of_target"]
                       * preload_total_N / factored_service_N,
                       "cover_ligament_fraction": net_fraction, "central_cap_port_mm": port_mm},
        "column": column,
    }


def physical_geometry(spec, ram, common, oil_density_kg_m3):
    stroke_mm = spec["stroke_mm"][1]
    end_cap_mm, end_rod_mm = spec["end_clearance_mm"]
    piston_mm = spec["piston_thickness_mm"]
    tube_length_mm = stroke_mm + piston_mm + end_cap_mm + end_rod_mm
    rear_mm, front_mm = spec["cover_thickness_mm"]
    rod_blank_length_mm = stroke_mm + end_rod_mm + front_mm + spec["rod_projection_home_mm"]
    barrel_OD_mm = spec["bore_mm"] + 2 * spec["tube_wall_mm"]
    cover_OD_mm = spec["cover_OD_mm"]
    tie_n = spec["tie_n"]
    housing_mm = tube_length_mm + rear_mm + front_mm
    tie_holes_mm2 = tie_n * area_mm2(spec["tie_hole_diameter_mm"])
    volume_mm3 = {
        "barrel": (area_mm2(barrel_OD_mm) - area_mm2(spec["bore_mm"])) * tube_length_mm,
        "rear_cover": (area_mm2(cover_OD_mm) - area_mm2(spec["cap_central_port_mm"]) - tie_holes_mm2) * rear_mm,
        "front_cover": (area_mm2(cover_OD_mm) - area_mm2(spec["rod_mm"]) - tie_holes_mm2) * front_mm,
        "tie_rods": tie_n * area_mm2(spec["tie_diameter_mm"]) * (housing_mm + 3 * spec["tie_diameter_mm"]),
        "piston": area_mm2(spec["bore_mm"]) * piston_mm,
        "rod": area_mm2(spec["rod_mm"]) * rod_blank_length_mm,
    }
    parts_kg = {name: v * common["steel_density_kg_m3"] / 1e9 for name, v in volume_mm3.items()}
    dry_kg = sum(parts_kg.values()) * (1 + common["ancillary_mass_allowance_fraction"])
    oil_L = ram.cap_m2 * stroke_mm + ram.cap_dead_m3 * OIL_L_PER_M3 + ram.annulus_dead_m3 * OIL_L_PER_M3
    return {
        "barrel_OD_mm": barrel_OD_mm, "length_body_mm": housing_mm,
        "length_retracted_to_rod_tip_mm": housing_mm + spec["rod_projection_home_mm"],
        "length_extended_to_rod_tip_mm": housing_mm + spec["rod_projection_home_mm"] + stroke_mm,
        "barrel_length_mm": tube_length_mm, "rod_blank_length_mm": rod_blank_length_mm,
        "dry_mass_parts_per_cylinder_kg": parts_kg,
        "dry_mass_per_cylinder_kg": dry_kg,
        "moving_metal_mass_per_cylinder_kg": parts_kg["rod"] + parts_kg["piston"],
        "maximum_oil_per_cylinder_L": oil_L,
        "filled_mass_per_cylinder_kg": dry_kg + oil_L * oil_density_kg_m3 / OIL_L_PER_M3,
    }


def main_fatigue(spec, assumptions):
    fat = assumptions["fatigue"]
    force_N = assumptions["main_min_nominal_force_N"]
    back_N = assumptions["main_return_thread_design_range_N"]
    rod_mm = spec["rod_mm"]
    e_mm = spec["rod_eccentricity_mm"]
    smooth_alt_MPa = (force_N + back_N) / 2 * (
        1 / area_mm2(rod_mm) + bending_MPa(1, e_mm, rod_mm)) * fat["coated_shaft_local_factor"]
    shoulder_area_mm2 = area_mm2(assumptions["main_contact_outer_mm"]) - area_mm2(assumptions["main_contact_inner_mm"])
    shoulder_alt_MPa = (force_N / shoulder_area_mm2 + bending_MPa(force_N, e_mm, rod_mm)
                        + back_N / area_mm2(rod_mm)) / 2 * assumptions["main_shoulder_stress_factor"]
    allowable_MPa = (fat["smooth_main_Rm_min_MPa"] * fat["material_axial_endurance_fraction"]
                     * fat["section_factor"] * fat["surface_factor"] / fat["safety_factor"])
    smooth_allowable_MPa = allowable_MPa * fat["hard_chrome_factor"]

    thread = spec["rod_end_thread"]
    thread_mm = thread["diameter_mm"]
    effective_mm2 = metric_thread_area_mm2(thread_mm, thread["pitch_mm"])
    size_factor = (30 / thread_mm)**.25
    knee_MPa = fat["thread_FAT_MPa"] * (2e6 / 5e6)**(1 / 3)
    thread_limit_MPa = knee_MPa * (5e6 / fat["number_of_cycles"])**.2 * size_factor / fat["safety_factor"]
    thread_range_MPa = back_N / effective_mm2 + bending_MPa(back_N, e_mm, thread["root_min_mm"])
    full_thread_range_MPa = force_N / effective_mm2 + bending_MPa(force_N, e_mm, thread["root_min_mm"])
    gap_mm = assumptions["main_retainer_axial_float_mm"]
    seat_compression_mm = assumptions["main_retainer_contact_stack_max_closure_mm"]
    return {
        "cycles": fat["number_of_cycles"],
        "load_press_range_N": force_N,
        "load_retraction_range_N": back_N,
        "shaft_alternating_MPa": smooth_alt_MPa,
        "shaft_design_alternating_MPa": smooth_allowable_MPa,
        "shaft_margin": smooth_allowable_MPa / smooth_alt_MPa,
        "shoulder_alternating_MPa": shoulder_alt_MPa,
        "shoulder_design_alternating_MPa": allowable_MPa,
        "shoulder_margin": allowable_MPa / shoulder_alt_MPa,
        "thread_load_in_full_press_N": 0.0,
        "thread_return_stress_range_MPa": thread_range_MPa,
        "thread_FAT50_size_reduced_design_range_MPa": thread_limit_MPa,
        "thread_margin": thread_limit_MPa / thread_range_MPa,
        "thread_margin_if_full_press_transmitted": thread_limit_MPa / full_thread_range_MPa,
        "thread_retainer_min_gap_after_deformation_budget_mm": gap_mm - seat_compression_mm,
        "shoulder_bearing_area_mm2": shoulder_area_mm2,
    }


def cylinder_for(spec, template):
    return replace(template, bore_mm=spec["bore_mm"], rod_mm=spec["rod_mm"],
                   stroke_mm=spec["stroke_mm"][1], eta=spec["eta"])


def main_fluid_geometry(ram, spec, assumptions, v2_settings):
    cap_stub_mm = spec["cap_central_port_mm"]
    rear_cover_mm = spec["cover_thickness_mm"][0]
    cap_gap_mm, ann_gap_mm = spec["end_clearance_mm"]
    dead_cap_L = (ram.cap_m2 * cap_gap_mm + area_m2(cap_stub_mm) * rear_cover_mm
                  + assumptions["main_cap_auxiliary_volume_L"])
    hole_count, hole_d_mm = assumptions["main_annulus_through_flow_diameters_mm"]
    hole_length_mm = spec["cover_thickness_mm"][1]
    dead_annulus_L = (ram.annulus_m2 * ann_gap_mm + hole_count * area_m2(hole_d_mm) * hole_length_mm
                      + assumptions["main_annulus_manifold_volume_L"])
    cap_catalog = v2_settings["catalogs"]["rexroth_zsf100"]
    return {
        "cap_dead_L": dead_cap_L,
        "annulus_dead_L": dead_annulus_L,
        "main_prefill_port": {"model": cap_catalog["model"], "bore_mm": cap_stub_mm,
                              "B_port_rating_bar": cap_catalog["port_B_max_bar"],
                              "A_port_rating_bar": cap_catalog["port_A_max_bar"],
                              "valve_body_port_B_entry_mm": 132, "valve_mount_PCD_mm": 240,
                              "valve_mount_threads": "8 × M27"},
        "annulus_port_distribution": {
            "small_bores_n": hole_count, "small_bores_mm": hole_d_mm,
            "parallel_passage_length_mm": hole_length_mm,
            "external_distribution_gallery_volume_L": assumptions["main_annulus_manifold_volume_L"],
            "line_ID_mm": assumptions["main_annulus_gallery_flow_ID_mm"],
        },
    }


def corrected_prefill_budget(model, ram, data, assumptions, spec):
    """T-1.4b fill circuit plus the new front and rear cover flow passages."""
    budgets = drive.prefill_budget(model, ram, data)
    rho = data["engineering_inputs"]["oil_density_kg_m3"]
    hole_count, hole_d_mm = assumptions["main_annulus_through_flow_diameters_mm"]
    cap_port_mm = spec["cap_central_port_mm"]
    inlet_K = assumptions["main_cap_port_K_with_fittings"]
    for name, row in budgets["cap_intake"].items():
        # At peak approach speed, the piston has already moved one ramp length
        # and the end face gap admits radial flow from the head passage.
        approach_gap_mm = spec["end_clearance_mm"][0] + 1000 * model.rapid_approach_m_s**2 / (
            2 * model.rapid_accel_m_s2)
        entrance_m2 = (pi * cap_port_mm * approach_gap_mm / 1e6 if name == "approach"
                       else area_m2(cap_port_mm))
        velocity_m_s = row["flow_L_min"] / FLOW_FACTOR / min(area_m2(cap_port_mm), entrance_m2)
        extra_bar = inlet_K * rho * velocity_m_s**2 / (2 * BAR_PA)
        row["cover_passage_extra_drop_bar"] = extra_bar
        row["min_absolute_with_cover_bar"] = row["min_absolute_bar"] - extra_bar
    cap_out = budgets["cap_exhaust"]
    ann_in = budgets["annulus_intake"]
    cap_out["peak_gauge_bar_with_cover"] = cap_out["peak_gauge_bar"] + (
        inlet_K * rho / (2 * BAR_PA) * (cap_out["flow_L_min"] / FLOW_FACTOR / area_m2(cap_port_mm))**2)
    ann_in["velocity_in_cover_ports_m_s"] = ann_in["flow_L_min"] / FLOW_FACTOR / (hole_count * area_m2(hole_d_mm))
    ann_in["min_absolute_with_cover_bar"] = ann_in["min_absolute_bar"] - (
        inlet_K * rho / (2 * BAR_PA) * ann_in["velocity_in_cover_ports_m_s"]**2)
    budgets["return_drag_with_cover_N"] = BAR_PA * (
        cap_out["peak_gauge_bar_with_cover"] * ram.cap_m2
        - (ann_in["min_absolute_with_cover_bar"] - 1.01325) * ram.annulus_m2)
    return budgets


def brake(mode, ram, n, mass_kg, speed_m_s, accel_m_s2, inlet_bar, driving_N=0, resisting_N=0):
    fed_m2, outlet_m2 = (ram.cap_m2, ram.annulus_m2) if mode == "extend" else (ram.annulus_m2, ram.cap_m2)
    braking_force_N = mass_kg * accel_m_s2 + driving_N - resisting_N
    return {
        "mode": mode,
        "speed_m_s": speed_m_s,
        "dec_m_s2": accel_m_s2,
        "brake_distance_mm": M_TO_MM * speed_m_s**2 / (2 * accel_m_s2),
        "brake_time_s": speed_m_s / accel_m_s2,
        "kinetic_energy_J": .5 * mass_kg * speed_m_s**2,
        "meter_in_pressure_bound_bar": inlet_bar,
        "meter_out_pressure_bound_bar": (inlet_bar * fed_m2 + braking_force_N / (n * BAR_PA)) / outlet_m2,
        "meter_out_flow_at_ramp_entry_L_min": n * outlet_m2 * speed_m_s * FLOW_FACTOR,
    }


def duct_velocity_m_s(flow_L_min, area_passage_m2):
    return flow_L_min / (FLOW_FACTOR * area_passage_m2)


def cycle_summary(run):
    phase_peaks_and_times = {}
    for name, row in run["motion_events"].items():
        phase_peaks_and_times[name] = {
            "peak_supply_bar": row["peak_supply_bar"],
            "peak_speed_m_s": row["peak_speed_m_s"],
            "motion_s": row["end_s"] - row["start_s"],
        }
    return {
        "cycle_s": run["cycle_s"], "nominal_force_N": run["nominal_force_N"],
        "peak_working_bar": run["peak_working_bar"],
        "peak_shaft_kW": run["peak_shaft_kW"], "rms_shaft_kW": run["rms_shaft_kW"],
        "mean_shaft_kW": run["average_shaft_kW"],
        "peak_shaft_with_tolerance_kW": run["shaft_peak_with_tolerance_kW"],
        "rms_shaft_with_tolerance_kW": run["shaft_rms_with_tolerance_kW"],
        "decompression": run["decompression"], "phase_peaks": phase_peaks_and_times,
    }


def replay(inputs, model, main, settings, data, rams, fluid, prefill, assumptions, main_spec):
    """Compare unchanged V2 and Ø100 on the same reference; replay T-1.3 allowances."""
    baseline_model, baseline_main, baseline_settings, _, _ = drive.configuration(inputs, data=data)
    reference_steps_s = (.000625, .0003125)
    reference = baseline_model, baseline_main, baseline_settings
    alternative = replace(model, pre_cylinder=replace(rams["pre"], bore_mm=100))
    reference_pre_100 = replace(baseline_model, pre_cylinder=replace(rams["pre"], bore_mm=100))
    small_rod = replace(main, rod_mm=assumptions["main_rod_alternative_mm"])
    small_rod_budget = drive.prefill_budget(model, small_rod, data)
    small_rod_settings = dict(settings)
    small_rod_settings["prefill"] = dict(
        settings["prefill"], return_float_drag_kN=small_rod_budget["return_drag_budget_N"] / 1000)
    small_rod_with_cover = corrected_prefill_budget(model, small_rod, data, assumptions, main_spec)
    phys_model = replace(model, pre_accel_m_s2=assumptions["pre_screen_accel_m_s2"],
                         pre_mass_kg=assumptions["pre_moving_mass_allowance_kg"])
    phys_main = replace(main, cap_dead_m3=fluid["cap_dead_L"] / OIL_L_PER_M3,
                        annulus_dead_m3=fluid["annulus_dead_L"] / OIL_L_PER_M3)
    phys_settings = dict(settings)
    phys_settings["prefill"] = dict(settings["prefill"],
                                   return_float_drag_kN=prefill["return_drag_with_cover_N"] / 1000)

    def run_cases(trio, density, curve="base", pressure_bar=None, steps_s=reference_steps_s):
        base_model, cylinder, run_settings = trio
        if pressure_bar is not None or density != 90 or curve != "base":
            geo, _ = drive.scenario(inputs, curve, density, .83, pressure_bar,
                                    base_model.gate_speed_m_s, base_model.losses_bar)
            base_model = replace(base_model, case=geo.case, nominal_N=geo.nominal_N, in_die_kg_m3=geo.in_die_kg_m3,
                                 overtravel_m=geo.overtravel_m, pre_travel_m=geo.pre_travel_m)
        return cycle_summary(drive.evaluated_run(base_model, cylinder, run_settings, data, "realistic",
                                                density, .64, pressure_bar, steps_s))

    physical = phys_model, phys_main, phys_settings
    baseline_36 = model, main, settings
    result = {
        "reference_37p5_kW": run_cases(reference, 90, steps_s=(.00125,)),
        "control_37p5_kW_fine": run_cases(reference, 90),
        "alternative_pre_100_37p5_kW": run_cases((reference_pre_100, baseline_main, baseline_settings), 90),
        "baseline_36_kW": run_cases(baseline_36, 90),
        "alternative_pre_100_36_kW": run_cases((alternative, main, settings), 90),
        "alternative_main_190_36_kW": run_cases((model, small_rod, small_rod_settings), 90),
        "control_300_bar_high_36_kW": run_cases(baseline_36, 90, curve="high", pressure_bar=300),
        "control_300_bar_high_37p5_kW": run_cases(reference, 90, curve="high", pressure_bar=300),
        "physical_36_kW": run_cases(physical, 90),
        "physical_36_kW_160_kg_m3": run_cases(physical, 160),
        "physical_36_kW_reserve_300_bar_base": run_cases(physical, 90, pressure_bar=300),
        "physical_36_kW_reserve_300_bar_high": run_cases(physical, 90, curve="high", pressure_bar=300),
    }
    # One lost-motion take-up on each reversal. The two transitions can overlap
    # another phase, but charge their full travel time to the cycle.
    backlash_time_s = 2 * sqrt(2 * assumptions["main_retainer_axial_float_mm"]
                               / (1000 * model.rapid_accel_m_s2))
    result["reversal_clearance_time_bound_s"] = backlash_time_s
    for key in ("physical_36_kW", "physical_36_kW_160_kg_m3",
                "physical_36_kW_reserve_300_bar_base", "physical_36_kW_reserve_300_bar_high"):
        row = result[key]
        row["cycle_with_reversal_clearance_upper_s"] = row["cycle_s"] + backlash_time_s
    base_s = result["baseline_36_kW"]["cycle_s"]
    result["alternative_pre_100_cycle_delta_s"] = result["alternative_pre_100_36_kW"]["cycle_s"] - base_s
    result["alternative_pre_100_reference_cycle_delta_s"] = (
        result["alternative_pre_100_37p5_kW"]["cycle_s"] - result["control_37p5_kW_fine"]["cycle_s"])
    result["alternative_main_190_cycle_delta_s"] = result["alternative_main_190_36_kW"]["cycle_s"] - base_s
    result["alternative_main_190_hydraulics"] = {
        "annulus_flow_at_0p35_m_s_L_min": FLOW_FACTOR * model.rapid_return_m_s * small_rod.annulus_m2,
        "regen_flow_at_0p24_m_s_L_min": FLOW_FACTOR * assumptions["main_press_peak_speed_limit_m_s"] * small_rod.rod_m2,
        "nominal_header_bar": supply_bar(small_rod, model.nominal_N, "extend", model.losses_bar),
        "float_return_drag_N": small_rod_budget["return_drag_budget_N"],
        "prefill_annulus_intake_min_absolute_bar_with_same_cover": (
            small_rod_with_cover["annulus_intake"]["min_absolute_with_cover_bar"]),
    }
    result["physical_cycle_delta_with_clearance_s"] = result["physical_36_kW"][
        "cycle_with_reversal_clearance_upper_s"] - base_s
    return result


def phase_results(specs, rams, model, v2, cycles, upstream_t12, upstream_t12b, prefill, assumptions, working_bar, relief_bar):
    main, rapid, pre, gate = (rams[key] for key in ("main", "rapid", "pre", "gate"))
    cfg = v2["engineering_inputs"]
    loss = model.losses_bar
    raw_pre = upstream_t12["precompaction"]
    lock = upstream_t12b["mechanical_lock_A"]
    cam_N = lock["equivalent_cam_force_N"]
    rapid_n = specs["rapid"]["n"]
    target_approach_m_s = model.rapid_approach_m_s
    target_eject_m_s = model.rapid_eject_m_s
    target_return_m_s = model.rapid_return_m_s
    rapid_inertia_N = model.rapid_mass_kg * model.rapid_accel_m_s2
    gate_inertia_N = model.gate_mass_kg * model.gate_accel_m_s2
    gate_normal_N = BAR_PA * assumptions["gate_working_open_cap_bar"] * main.cap_m2
    plate_drag_N = gate_normal_N * assumptions["gate_friction_coefficient"]
    gate_total_stiction_N = assumptions["gate_reference_open_drag_N"]
    cam_speed_m_s = model.cam_stem_speed_m_s
    pre_speed_m_s = .65
    pre_required_N = raw_pre["required_cylinder_force_N"]
    nominal_N = assumptions["main_min_nominal_force_N"]
    return_drag_N = prefill["return_drag_with_cover_N"]
    pressed_N = axial_force_N(main, working_bar, loss, "extend")
    retained = cycles["physical_36_kW"]
    main_direct_speed_m_s = retained["phase_peaks"]["press"]["peak_speed_m_s"]
    main_regen_speed_m_s = retained["phase_peaks"]["regen"]["peak_speed_m_s"]

    load_rows = {
        "main": {
            "press_nominal": phase(main, 1, "extend", main_direct_speed_m_s, nominal_N, loss),
            "reserve": phase(main, 1, "extend", main_direct_speed_m_s, pressed_N, loss),
            "regen_before_direct_switch": phase(main, 1, "regen", main_regen_speed_m_s,
                                                 axial_force_N(main, model.regen_switch_bar, loss, "regen"), loss),
            "external_driver_float": {
                name: {"speed_target_m_s": speed, "cap_flow_L_min": FLOW_FACTOR * main.cap_m2 * speed,
                       "annulus_flow_L_min": FLOW_FACTOR * main.annulus_m2 * speed,
                       "own_pump_feed_L_min": 0}
                for name, speed in (("approach", target_approach_m_s), ("eject", target_eject_m_s),
                                    ("return", target_return_m_s))
            },
        },
        "rapid": {
            name: phase(rapid, rapid_n, mode, speed, force_N / rapid_n, loss,
                        assumptions["fast_peak_force_reserve_factor"])
            for name, mode, speed, force_N in (
                ("approach_before_regen", "extend", target_approach_m_s,
                 cfg["prefill_fast_to_regen_force_N"] + cfg["prefill_auxiliary_cylinders"]["main_float_drag_kN"] * 1000
                 + rapid_inertia_N),
                ("eject_start", "extend", target_eject_m_s,
                 model.ejection_N + cfg["prefill_auxiliary_cylinders"]["main_float_drag_kN"] * 1000 + rapid_inertia_N),
                ("return", "retract", target_return_m_s, 40000 + return_drag_N + rapid_inertia_N),
            )
        },
        "pre": {
            "precompact_upper_high": phase(pre, 1, "extend", pre_speed_m_s, raw_pre["operating_force_N"], loss, 2),
            "lock_with_upper_high": phase(pre, 1, "extend", cam_speed_m_s, raw_pre["operating_force_N"] + cam_N, loss),
            "unlock_cam_plus_return": phase(pre, 1, "retract", cam_speed_m_s,
                                            model.pre_return_force_N + cam_N, loss, assumptions["cam_peak_force_reserve_factor"]),
            "return_after_unlock": phase(pre, 1, "retract", pre_speed_m_s, model.pre_return_force_N, loss),
        },
        "gate": {
            "open": phase(gate, 1, "retract", model.gate_speed_m_s, gate_total_stiction_N + gate_inertia_N,
                          loss, assumptions["gate_peak_force_reserve_factor"]),
            "close": phase(gate, 1, "extend", model.gate_speed_m_s,
                           assumptions["gate_reference_close_drag_N"] + gate_inertia_N,
                           loss, assumptions["gate_peak_force_reserve_factor"]),
        },
    }
    pre_mass_kg = assumptions["pre_moving_mass_allowance_kg"]
    pre_accel = assumptions["pre_screen_accel_m_s2"]
    weights_N = pre_mass_kg * 9.81
    floating_bar = cfg["cap_exhaust_restriction_budget_bar"]
    brake_rows = {
        "main": {
            "floating_extend": brake("extend", main, 1, model.rapid_mass_kg, target_eject_m_s,
                                     model.rapid_accel_m_s2, floating_bar),
            "floating_return": brake("retract", main, 1, model.rapid_mass_kg, target_return_m_s,
                                     model.rapid_accel_m_s2, floating_bar),
            "regen_open_outlet_bound": brake("extend", main, 1, model.rapid_mass_kg,
                                            assumptions["main_press_peak_speed_limit_m_s"],
                                            model.rapid_accel_m_s2, assumptions["max_meter_in_during_main_regen_brake_bar"]),
            "direct_press_open_meter_out": {
                "meter_out_pressure_bound_bar": assumptions["main_direct_press_outlet_bound_bar"],
                "normal_outlet_nominal_bar": loss[1], "meter_out_path_during_braking": "При прямом прессовании B→T открыт, торможение ограничением подачи и силой материала.",
            },
        },
        "rapid": {
            mode: brake(mode, rapid, rapid_n, model.rapid_mass_kg, target_eject_m_s,
                        model.rapid_accel_m_s2, assumptions["max_meter_in_during_rapid_brake_bar"])
            for mode in ("extend", "retract")
        },
        "pre": {
            mode: brake(mode, pre, 1, pre_mass_kg, pre_speed_m_s, pre_accel,
                        assumptions["max_meter_in_during_pre_brake_bar"], driving_N=weights_N)
            for mode in ("extend", "retract")
        },
        "gate": {
            "open": brake("retract", gate, 1, model.gate_mass_kg, model.gate_speed_m_s,
                          model.gate_accel_m_s2, assumptions["max_meter_in_during_gate_brake_bar"]),
            "close": brake("extend", gate, 1, model.gate_mass_kg, model.gate_speed_m_s,
                           model.gate_accel_m_s2, assumptions["max_meter_in_during_gate_brake_bar"]),
        },
    }
    small_pre = replace(pre, bore_mm=100)
    main_header_bar = load_rows["main"]["press_nominal"]["header_pressure_bar"]
    pre_max_N = axial_force_N(pre, working_bar, loss, "extend")
    gate_open_N = load_rows["gate"]["open"]["required_force_with_reserve_total_N"]
    inlet_bar, tank_bar, _ = loss
    area_for_gate_pull_m2 = (
        gate_open_N / gate.eta / BAR_PA + (working_bar - inlet_bar) * gate.rod_m2
    ) / (working_bar - inlet_bar - tank_bar)
    relief = assumptions["local_relief"]
    fault_N = lock["max_shoe_load_at_315_bar_N"]
    pre_rows = {
        "T12_pre_force_cases_N": raw_pre["force_cases"],
        "T12_upper_dose_kg": raw_pre["doses_kg"]["upper_dose"],
        "T12_operating_force_upper_high_N": raw_pre["operating_force_N"],
        "T12_required_pre_compaction_force_with_reserve_N": pre_required_N,
        "if_factored_compaction_and_unfactored_cam_are_simultaneous_N": pre_required_N + cam_N,
        "actual_upper_high_with_cam_N": raw_pre["operating_force_N"] + cam_N,
        "net_pre_125_at_300_bar_N": pre_max_N,
        "net_pre_100_at_300_bar_N": axial_force_N(small_pre, working_bar, loss, "extend"),
        "header_125_at_2x_compaction_bar": supply_bar(pre, pre_required_N, "extend", loss),
        "header_100_at_2x_compaction_bar": supply_bar(small_pre, pre_required_N, "extend", loss),
        "net_125_over_2x_compaction_margin_N": pre_max_N - pre_required_N,
        "unfactored_joint_load_margin": pre_max_N / (raw_pre["operating_force_N"] + cam_N),
        "max_shoe_at_main_300_bar_N": lock["max_shoe_load_at_300_bar_N"],
        "max_shoe_at_main_315_bar_N": fault_N,
        "blocked_cap_at_315_bar_main_fault_bar": fault_N / (pre.cap_m2 * BAR_PA),
        "blocked_annulus_area_pressure_reference_bar": fault_N / (pre.annulus_m2 * BAR_PA),
        "local_cap_relief_flow_at_screen_speed_L_min": (
            FLOW_FACTOR * pre.cap_m2 * assumptions["pre_fault_response"]["motion_mm_s"] / M_TO_MM),
        "local_annulus_relief_flow_at_screen_speed_L_min": (
            FLOW_FACTOR * pre.annulus_m2 * assumptions["pre_fault_response"]["motion_mm_s"] / M_TO_MM),
        "local_cap_capped_static_hydraulic_support_N": relief_bar * BAR_PA * pre.cap_m2,
        "local_relief_full_flow_port_limit_bar": relief["maximum_setting_bar"],
        "cam": {
            "n_keys": 2, "force_at_pre_rod_N": cam_N, "stroke_at_pre_rod_mm": lock["cam_extra_pre_cylinder_stroke_mm"],
            "key_orthogonal_travel_mm": lock["key_slide_mm"], "speed_at_pre_rod_m_s": cam_speed_m_s,
            "extra_s_at_speed_limit": (lock["cam_extra_pre_cylinder_stroke_mm"] / 1000) / cam_speed_m_s,
            "sensing": "Два независимых положения каждого засова (вошёл/вышел), датчик положения башмака и энкодер/датчик штока; разрешения PLC по совпадению и давлению.",
        },
    }
    return load_rows, brake_rows, {
        "main": {
            "nominal_header_bar": main_header_bar,
            "nominal_cap_port_bar": main_header_bar - inlet_bar,
            "net_at_270_bar_N": axial_force_N(main, assumptions["main_header_stop_bar"], loss, "extend"),
            "net_at_300_bar_N": pressed_N,
            "additional_header_loss_to_270_bar": assumptions["main_header_stop_bar"] - main_header_bar,
            "regen_differential_area_mm2": main.rod_m2 * 1e6,
            "maximum_steady_rod_port_bar_at_270_header": (
                (assumptions["main_header_stop_bar"] - inlet_bar) * main.cap_m2
                - nominal_N / (main.eta * BAR_PA)) / main.annulus_m2,
            "regen_at_0p24_m_s_supply_L_min": FLOW_FACTOR * main.rod_m2 * assumptions["main_press_peak_speed_limit_m_s"],
            "main_annulus_to_cap_ratio": main.annulus_m2 / main.cap_m2,
            "minimum_eta_for_nominal_at_270_bar": nominal_N / (BAR_PA * (
                (assumptions["main_header_stop_bar"] - inlet_bar) * main.cap_m2 - tank_bar * main.annulus_m2)),
        },
        "pre": pre_rows,
        "gate": {
            "residual_main_cap_bar": assumptions["gate_working_open_cap_bar"],
            "residual_normal_at_plate_N": gate_normal_N,
            "plate_friction_N": plate_drag_N,
            "pinch_and_guide_allowance_N": gate_total_stiction_N - plate_drag_N,
            "pinch_allowable_at_2x_opening_margin_N": axial_force_N(gate, working_bar, loss, "retract")
            / assumptions["gate_peak_force_reserve_factor"] - gate_inertia_N - plate_drag_N,
            "minimum_bore_for_2x_opening_with_45_mm_rod_mm": sqrt(4 * area_for_gate_pull_m2 / pi) * 1000,
            "close_force_margin_at_300_bar": axial_force_N(gate, working_bar, loss, "extend")
            / load_rows["gate"]["close"]["required_force_with_reserve_total_N"],
        },
    }


def specifications(specs, rams, calculated, common, assumptions, working_bar, relief_bar):
    physical = {}
    for key, spec in specs.items():
        ram = rams[key]
        geometry = calculated["cylinders"][key]["geometry"]
        work_mm, installed_mm = spec["stroke_mm"]
        physical[key] = {
            "id": {"main": "CY-MAIN", "rapid": "CY-RAPID", "pre": "CY-PRE", "gate": "CY-GATE"}[key],
            "designation": spec["designation"],
            "n": spec["n"],
            "bore_mm": spec["bore_mm"], "rod_mm": spec["rod_mm"],
            "stroke_working_mm": work_mm, "stroke_installed_mm": installed_mm,
            "work_port_passage_ID_mm": spec.get("work_port_passage_ID_mm"),
            "cap_area_mm2": round(ram.cap_m2 * 1e6, 3), "annulus_area_mm2": round(ram.annulus_m2 * 1e6, 3),
            "design_pressure_bar": relief_bar, "max_working_pressure_bar": working_bar,
            "mounting": spec["mounting"],
            "barrel_OD_mm": geometry["barrel_OD_mm"], "barrel_wall_mm": spec["tube_wall_mm"],
            "barrel_length_mm": geometry["barrel_length_mm"],
            "piston_thickness_mm": spec["piston_thickness_mm"],
            "cover_OD_mm": spec["cover_OD_mm"],
            "cover_thickness_rear_mm": spec["cover_thickness_mm"][0],
            "cover_thickness_front_mm": spec["cover_thickness_mm"][1],
            "tie_rods": {"n": spec["tie_n"], "property_class": "10.9", "PCD_mm": spec["tie_PCD_mm"],
                         "diameter_mm": spec["tie_diameter_mm"], "pitch_mm": spec["tie_pitch_mm"],
                         "hole_diameter_mm": spec["tie_hole_diameter_mm"]},
            "body_length_mm": geometry["length_body_mm"],
            "rod_tip_retracted_length_mm": geometry["length_retracted_to_rod_tip_mm"],
            "rod_tip_extended_length_mm": geometry["length_extended_to_rod_tip_mm"],
            "rod_end_thread": spec["rod_end_thread"],
            "end_clearance_mm": {"cap": spec["end_clearance_mm"][0], "annulus": spec["end_clearance_mm"][1]},
            "column_effective_length_max_mm": calculated["cylinders"][key]["static"]["column"]["Le_mm"],
            "barrel_and_cover_material": common["barrel_and_cover_material"],
            "barrel_and_cover_Rp02_min_MPa": common["barrel_and_cover_Rp02_min_MPa"],
            "piston_and_rod_material": common["rod_and_piston_material"],
            "piston_and_rod_Rp02_min_MPa": spec["rod_Rp02_min_MPa"],
            "rod_surface": common["coating"],
            "dry_mass_each_kg": round(geometry["dry_mass_per_cylinder_kg"], 2),
            "filled_mass_each_kg": round(geometry["filled_mass_per_cylinder_kg"], 2),
        }
    physical["main"]["max_operating_stroke_mm"] = calculated["axis"]["max_main_travel_mm"]
    physical["rapid"]["max_operating_stroke_mm"] = calculated["axis"]["max_main_travel_mm"]
    physical["pre"]["base_dose_operating_stroke_mm"] = calculated["axis"]["nominal_pre_travel_mm"]
    physical["pre"]["independent_local_relief"] = assumptions["local_relief"]
    physical["main"].update(calculated["main_fluid_geometry"])
    physical["main"]["thrust_and_return_coupling"] = {
        "shoulder_contact_outer_mm": assumptions["main_contact_outer_mm"],
        "shoulder_contact_inner_mm": assumptions["main_contact_inner_mm"],
        "fillet_radius_min_mm": assumptions["main_shoulder_fillet_min_mm"],
        "return_retainer_axial_float_mm": assumptions["main_retainer_axial_float_mm"],
        "max_stack_closure_at_315_bar_mm": assumptions["main_retainer_contact_stack_max_closure_mm"],
        "arrangement": "Прямой торцевой упор на сжатие; на возврат — плавающая стопоримая гайка в кармане траверсы; поршень и шток выполнены заодно.",
    }
    return {
        "schema_version": 1, "task": "T-1.3", "stage": "S1-hyd",
        "gate_equivalent_input": "design/params.t14b.yaml",
        "cylinders": list(physical.values()),
        "locks": {"id": "CAM-PRE", "hydraulic_cylinders": 0,
                  **calculated["functional_checks"]["pre"]["cam"]},
        "braking": "Пропорциональные рампы, подпитка низкого давления и локальная защита запираемых полостей до 315 бар с учётом динамики.",
        "seal_package": {
            "piston": common["piston_seal"], "rod": common["rod_seal"],
            "material_dynamic_pressure_limits_MPa": {"piston": common["piston_material_dynamic_max_MPa"],
                                                      "rod_primary": common["rod_material_dynamic_max_MPa"]},
            "separate_velocity_limits_m_s": {"piston": common["separate_catalog_limit_m_s"],
                                              "rod_tandem": common["rod_tandem_catalog_limit_m_s"]},
            "guidance_and_static": common["guidance_and_static"], "fluid": common["oil"],
        },
    }


def calculate():
    source = load_yaml(HERE / "sources.yaml")
    specs, common, assumptions = (source[key] for key in ("design", "common", "load_and_hydraulic_assumptions"))
    criteria = load_yaml(ROOT / "ops/criteria/design_criteria.yaml")["criteria"]
    working_bar = criteria["C-HYD-01"]["max_working_bar"]
    relief_bar = criteria["C-HYD-01"]["max_relief_bar"]
    inputs = drive.get_inputs()
    t12b, _, t12, _ = inputs
    v2 = drive.source_data()
    t14b = load_json(ROOT / "calc/T-1.4b/results.json")
    # D-GK-02 sets 36 kW. The accepted G-CYCLE projection keeps its own 37.5 kW replay.
    model, main, settings, _, _ = drive.configuration(inputs, data=v2, limit_kW=36)
    rapid = replace(main, **{k: v2["engineering_inputs"]["prefill_auxiliary_cylinders"][k]
                             for k in ("bore_mm", "rod_mm", "eta")})
    templates = dict(main=main, rapid=rapid, pre=model.pre_cylinder, gate=model.gate_cylinder)
    params = load_yaml(ROOT / "design/params.t14b.yaml")
    assert params["main_cylinder"]["rod_mm"] != main.rod_mm
    assert specs["rapid"]["n"] == v2["engineering_inputs"]["prefill_auxiliary_cylinders"]["count"]
    for key, template in templates.items():
        # The selected bores, rods and installed travels match the actual V2 model.
        assert cylinder_for(specs[key], template) == template, (key, specs[key], template)
    for key, expected in {
        "main": t12b["axis_A"]["main_required_travel_mm"],
        "rapid": t12b["axis_A"]["main_required_travel_mm"],
        "pre": t12b["alternatives"]["A"]["dimensions"]["max_pre_cylinder_travel_mm"],
        "gate": t12b["gate"]["gate_opening_travel_mm"],
    }.items():
        assert specs[key]["stroke_mm"][0] == expected

    fluid = main_fluid_geometry(main, specs["main"], assumptions, v2)
    prefill = corrected_prefill_budget(model, main, v2, assumptions, specs["main"])
    rams = dict(templates, main=replace(main, cap_dead_m3=fluid["cap_dead_L"] / OIL_L_PER_M3,
                                       annulus_dead_m3=fluid["annulus_dead_L"] / OIL_L_PER_M3))
    cycles = replay(inputs, model, main, settings, v2, rams, fluid, prefill, assumptions, specs["main"])
    loads, brakes, functional = phase_results(specs, rams, model, v2, cycles, t12, t12b, prefill, assumptions,
                                              working_bar, relief_bar)

    calculated = {"task": "T-1.3", "status": "engineering_screen",
                  "gate_params": "design/params.t14b.yaml", "sources": source["references"],
                  "axis": {"max_main_travel_mm": t12b["axis_A"]["max_operating_travel_mm"],
                           "nominal_pre_travel_mm": t12b["alternatives"]["A"]["dimensions"]["nominal_pre_cylinder_travel_mm"]}}
    calculated["cylinders"] = {}
    header_limits = [working_bar, relief_bar]
    min_static = criteria["C-STR-01"]["min_safety_factor_yield"]
    oil_density = v2["engineering_inputs"]["oil_density_kg_m3"]
    for key, spec in specs.items():
        ram, n = rams[key], spec["n"]
        calculated["cylinders"][key] = {
            "n": n, "geometry": physical_geometry(spec, ram, common, oil_density),
            "areas_per_cylinder_mm2": {"cap": ram.cap_m2 * 1e6, "annulus": ram.annulus_m2 * 1e6,
                                      "rod": ram.rod_m2 * 1e6},
            "forces_by_header_bar": pressure_forces(ram, n, model.losses_bar, *header_limits),
            "phase_requirements": loads[key],
            "braking": brakes[key],
            "static": structure(key, spec, ram, relief_bar, common, assumptions, min_static),
            "seal_travel_at_1e7_cycles_km": 2 * spec["stroke_mm"][0] * float(criteria["C-FAT-01"]["min_cycles"]) / 1e6,
        }

    fatigue = main_fatigue(specs["main"], assumptions)
    nominal_header = functional["main"]["nominal_header_bar"]
    for label, p_bar in (("nominal", nominal_header), ("reserve", working_bar)):
        flow_L_min = settings["pump"].capacity_L_min(p_bar)
        functional["main"][label + "_end_pump_capacity_L_min"] = flow_L_min
        functional["main"][label + "_end_speed_upper_m_s"] = duct_velocity_m_s(flow_L_min, main.cap_m2)
    functional["main"]["main_column_factor_if_full_ejection_force_on_main"] = (
        calculated["cylinders"]["main"]["static"]["column"]["governing_critical_N"]
        / loads["rapid"]["eject_start"]["required_force_with_reserve_total_N"])
    for key in ("rapid", "pre", "gate"):
        cylinder_rows = calculated["cylinders"][key]
        port_sizes = specs[key]["work_port_passage_ID_mm"]
        maximum_phase_speed = max(row["speed_limit_m_s"] for row in loads[key].values())
        cylinder_rows["port_velocity_at_max_cylinder_speed_m_s"] = {
            port: duct_velocity_m_s(FLOW_FACTOR * maximum_phase_speed * flow_area, area_m2(port_sizes[port]))
            for port, flow_area in (("cap", rams[key].cap_m2), ("annulus", rams[key].annulus_m2))
        }
    calculated.update(functional_checks=functional, main_fatigue=fatigue, protected_port_pressure_bar=relief_bar,
                      cycles=cycles, main_fluid_geometry=fluid, prefill=prefill)
    wet_kg = sum(row["geometry"]["filled_mass_per_cylinder_kg"] * row["n"]
                 for row in calculated["cylinders"].values())
    dry_kg = sum(row["geometry"]["dry_mass_per_cylinder_kg"] * row["n"]
                 for row in calculated["cylinders"].values())
    raw_mass = t12b["alternatives"]["A"]["dimensions"]["mass_breakdown_kg"]
    noncyl_kg = (raw_mass["chamber"] + raw_mass["lock"] + t12b["mechanical_lock_A"]["shoe_mass_kg"]
                 + raw_mass["gate_and_actuator"] - 12)
    station_kg = t14b["station"]["approximate_station_filled_kg"]
    subtotal_kg = wet_kg + noncyl_kg + station_kg
    mass_limit = criteria["C-MASS-01"]
    main_part = calculated["cylinders"]["main"]["geometry"]
    rapid_part = calculated["cylinders"]["rapid"]["geometry"]
    calculated["mass"] = {
        "dry_cylinders_kg": dry_kg, "filled_cylinders_kg": wet_kg,
        "station_includes_ZSF_kg": station_kg, "chamber_lock_shoe_plate_without_actuators_kg": noncyl_kg,
        "subtotal_before_frame_feeder_hopper_guards_kg": subtotal_kg,
        "remaining_to_machine_target_kg": mass_limit["target_kg"] - subtotal_kg,
        "remaining_to_machine_max_kg": mass_limit["max_kg"] - subtotal_kg,
        "remaining_crosshead_and_punch_kg": model.rapid_mass_kg
        - main_part["moving_metal_mass_per_cylinder_kg"] - specs["rapid"]["n"] * rapid_part["moving_metal_mass_per_cylinder_kg"],
    }
    tech_box_mm = t12b["alternatives"]["A"]["dimensions"]["packaging_screen_mm"]
    calculated["envelope"] = {
        "upstream_screen_mm": tech_box_mm,
        "cylinders_local_envelope_only": True,
        "horizontal_axis_component_allowance_mm": (
            main_part["length_retracted_to_rod_tip_mm"] + 190
            + t12b["axis_A"]["gate_outer_x_mm"] + 350
        ),
        "vertical_screen_replacing_only_pre_body_mm": (tech_box_mm[2] +
            calculated["cylinders"]["pre"]["geometry"]["length_body_mm"]
            - t12b["alternatives"]["A"]["dimensions"]["pre_cylinder_box_mm"][2]),
        "machine_limit_mm": criteria["C-ENV-01"]["max_mm"],
    }

    brake_peak_bar = max(row["meter_out_pressure_bound_bar"] for variants in brakes.values() for row in variants.values())
    system_min_abs_bar = min([r["min_absolute_with_cover_bar"] for r in prefill["cap_intake"].values()]
                             + [prefill["annulus_intake"]["min_absolute_with_cover_bar"]])
    checks = {
        "main_at_270_bar": functional["main"]["net_at_270_bar_N"] >= assumptions["main_min_nominal_force_N"],
        "main_wall_at_most_70_mm": specs["main"]["tube_wall_mm"] <= 70,
        "C_STR_01_static_screen_all": all(
            c["static"]["static_safety_factor_min"] >= min_static for c in calculated["cylinders"].values()),
        "column_factor_at_least_3p5_all": all(c["static"]["column"]["safety_factor"] >= 3.5
                                             for c in calculated["cylinders"].values()),
        "closed_tie_rods_under_service": all(c["static"]["tied_joint"]["joint_opening_margin"] >= 1
                                             for c in calculated["cylinders"].values()),
        "pre_125_compaction_reserve_and_cam": (
            functional["pre"]["net_125_over_2x_compaction_margin_N"] >= 0
            and loads["pre"]["lock_with_upper_high"]["header_pressure_bar"] <= working_bar
            and loads["pre"]["unlock_cam_plus_return"]["header_pressure_with_reserve_bar"] <= working_bar),
        "pre_100_rejected_by_force": (functional["pre"]["net_pre_100_at_300_bar_N"]
                                     < functional["pre"]["T12_required_pre_compaction_force_with_reserve_N"]),
        "max_braking_pressure_screen": brake_peak_bar <= relief_bar,
        "prefill_minimum_pressure_screen": system_min_abs_bar >= v2["engineering_inputs"]["prefill_pipe"]["cap_min_abs_bar"],
        "main_10million_cycle_screen": (fatigue["thread_retainer_min_gap_after_deformation_budget_mm"] > 0
                                         and min(fatigue[k] for k in ("shaft_margin", "shoulder_margin", "thread_margin")) >= 1),
    }
    calculated["analytic_checks"] = checks
    calculated["conditions_to_verify"] = {
        "cycle_high_300_bar_within_6_s": (
            cycles["physical_36_kW_reserve_300_bar_high"]["cycle_with_reversal_clearance_upper_s"]
            <= criteria["C-PERF-01"]["max_cycle_s"]),
        "nominal_cycle_including_reversal_within_6_s": (
            cycles["physical_36_kW"]["cycle_with_reversal_clearance_upper_s"]
            <= criteria["C-PERF-01"]["max_cycle_s"]),
        "lock_failure_pressure_transient_verified": False,
        "seal_service_interval_verified": False,
        "whole_machine_mass_and_envelope_verified": False,
    }
    physical = specifications(specs, rams, calculated, common, assumptions, working_bar, relief_bar)
    cycle = cycles["physical_36_kW"]
    metrics = {
        "task": "T-1.3", "gate_params": calculated["gate_params"],
        "main_nominal_force_N": assumptions["main_min_nominal_force_N"],
        "main_nominal_header_bar": functional["main"]["nominal_header_bar"],
        "main_270_bar_force_N": functional["main"]["net_at_270_bar_N"],
        "main_300_bar_force_N": functional["main"]["net_at_300_bar_N"],
        "main_wall_mm": specs["main"]["tube_wall_mm"], "max_working_bar": working_bar, "max_relief_bar": relief_bar,
        "minimum_static_yield_ratio": min(c["static"]["static_safety_factor_min"] for c in calculated["cylinders"].values()),
        "minimum_column_ratio": min(c["static"]["column"]["safety_factor"] for c in calculated["cylinders"].values()),
        "max_braking_pressure_screen_bar": brake_peak_bar, "min_prefill_absolute_bar": system_min_abs_bar,
        "main_fatigue_min_margin": min(fatigue[k] for k in ("shaft_margin", "shoulder_margin", "thread_margin")),
        "pre_selected_bore_mm": specs["pre"]["bore_mm"], "pre_125_net_300_bar_N": functional["pre"]["net_pre_125_at_300_bar_N"],
        "pre_100_net_300_bar_N": functional["pre"]["net_pre_100_at_300_bar_N"],
        "pre_required_force_N": functional["pre"]["T12_required_pre_compaction_force_with_reserve_N"],
        "pre_100_cycle_delta_s": cycles["alternative_pre_100_cycle_delta_s"],
        "pre_100_reference_cycle_delta_s": cycles["alternative_pre_100_reference_cycle_delta_s"],
        "main_190_cycle_delta_s": cycles["alternative_main_190_cycle_delta_s"],
        "v2_control_cycle_36_kW_s": cycles["baseline_36_kW"]["cycle_s"],
        "estimated_physical_cycle_36_kW_s": cycle["cycle_with_reversal_clearance_upper_s"],
        "physical_cycle_delta_s": cycles["physical_cycle_delta_with_clearance_s"],
        "reserve_high_control_36_kW_s": cycles["control_300_bar_high_36_kW"]["cycle_s"],
        "physical_cycle_conservative_reserve_high_s": cycles["physical_36_kW_reserve_300_bar_high"]["cycle_with_reversal_clearance_upper_s"],
        "physical_peak_shaft_with_tolerance_kW": cycle["peak_shaft_with_tolerance_kW"],
        "physical_rms_shaft_with_tolerance_kW": cycle["rms_shaft_with_tolerance_kW"],
        "dry_cylinders_kg": dry_kg, "filled_cylinders_kg": wet_kg,
        "remaining_to_machine_target_kg": calculated["mass"]["remaining_to_machine_target_kg"],
    }
    return calculated, physical, metrics


def main():
    results, design, metrics = calculate()
    write_json(HERE / "results.json", results)
    (ROOT / "design/cylinders.t13.yaml").write_text(
        yaml.safe_dump(design, allow_unicode=True, sort_keys=False, width=115), encoding="utf-8", newline="\n")
    write_json(ROOT / "metrics.json", metrics)
    failed = [key for key, passed in results["analytic_checks"].items() if not passed]
    if failed:
        raise SystemExit("Failed engineering checks: " + ", ".join(failed))


if __name__ == "__main__":
    main()
