"""Screens, traceable mass budget, and deterministic publication for T-1.7b."""
import argparse
import json
from math import hypot, pi, sqrt
from pathlib import Path

import yaml

from cap_pressure import BORE_R_mm, CYLINDER, PORT_R_mm, SEAT_mm
from frame_analytic import CYCLIC_N, ROOT, RHO_kg_mm3, STATIC_N
from frame_fea import FEA, HERE, fkm_parameters, write_json
from gate_contact import HEIGHT_mm, OPEN_mm, RAIL_mm, SHOE_mm, screening
from gate_integral import mass as gate_mass
from mass_budget import revision_machine_mass


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path,value):
    path.write_text(yaml.safe_dump(value,sort_keys=False,allow_unicode=True,width=105),
                    encoding="utf-8",newline="\n")


def section_area_mm2(diameter_mm):
    return pi*diameter_mm**2/4


def independent_cylinder():
    t16 = read_json(ROOT/"calc/T-1.6/results.json")["main_cylinder"]
    t13 = read_json(ROOT/"calc/T-1.3/results.json")["cylinders"]["main"]["static"]
    ri = BORE_R_mm
    ro = ri+CYLINDER["barrel_wall_min_mm"]
    p_MPa = 30.
    hoop_MPa = p_MPa*(ro**2+ri**2)/(ro**2-ri**2)
    bore_preload_MPa = -t16["total_preload_N"]/(pi*(ro**2-ri**2))
    closed_axial_MPa = p_MPa*ri**2/(ro**2-ri**2)
    c = t13["tube"]["local_bound_MPa"]/t13["tube"]["with_preload_VM_MPa"]
    allow,_,_,slope = fkm_parameters(750.,6.3,False,forging=True)
    loads = {}
    for label,axial in (("no_axial_pressure_increment",0.),("closed_end_pressure_increment",closed_axial_MPa)):
        vm_range = sqrt(.5*((hoop_MPa+p_MPa)**2+(hoop_MPa-axial)**2+(p_MPa+axial)**2))
        mean_pos = max(0.,hoop_MPa/2,(bore_preload_MPa+axial/2))
        loads[label] = {"range_nominal_MPa":vm_range,"range_with_T13_detail_factor_MPa":vm_range*c,
                        "fatigue_factor_screen":allow/(c*(vm_range/2+slope*mean_pos))}
    return {"static_T16":t16["component_yield_factors"],"static_minimum_factor":t16["minimum_yield_factor"],
            "cylinder_fatigue_status":"UNVERIFIED",
            "tube_FKM_screen":loads,"tube_detail_factor_from_T13":c,
            "cover_fatigue_note":"T-1.6 static cover proof only; no three-grid FKM record for independent rear/forward oil ports."}


def integration(base, meshes):
    main = CYLINDER
    head_removed_kg = (section_area_mm2(main["cover_OD_mm"])-section_area_mm2(2*PORT_R_mm)
                       -main["tie_rods"]["n"]*section_area_mm2(main["tie_rods"]["hole_diameter_mm"])
                      )*main["cover_thickness_rear_mm"]*RHO_kg_mm3
    fit_rear_advance_mm = main["barrel_length_mm"]-SEAT_mm
    add_columns_kg = 4*section_area_mm2(70.)*fit_rear_advance_mm*RHO_kg_mm3
    # Central cast material is swapped for a same-density forged wet cup and
    # through-neck, including the pressure surface of the axial feed port.
    cup_OD_mm, cup_ID_mm, annular_wall_mm, base_mm, neck_OD_mm = 352., 280., 18., 32., 160.
    neck_depth_mm = main["cover_thickness_rear_mm"]-base_mm
    cup_kg = (
        (section_area_mm2(cup_OD_mm)-section_area_mm2(cup_ID_mm))*annular_wall_mm
        + (section_area_mm2(cup_OD_mm)-section_area_mm2(2*PORT_R_mm))*base_mm
        + (section_area_mm2(neck_OD_mm)-section_area_mm2(2*PORT_R_mm))*neck_depth_mm
    )*RHO_kg_mm3

    def thick_wall(ri,ro,p_MPa):
        radial = -p_MPa
        hoop = p_MPa*(ro**2+ri**2)/(ro**2-ri**2)
        axial = p_MPa*ri**2/(ro**2-ri**2)
        return sqrt(.5*((hoop-radial)**2+(axial-hoop)**2+(radial-axial)**2))

    baseline_head_kg = base["mass"]["frame_rows"][0]["mass_kg"]
    cast_head_kg = meshes[-1]["mass_kg"] if meshes else None
    delta_kg = cast_head_kg - baseline_head_kg - head_removed_kg + add_columns_kg if meshes else None
    phi = base["column_by_end"]["cylinder"]["load_fraction"]
    layout = base["dimension_screen"]
    current_module_mm = layout["module_axial_excluding_ZSF_and_safety_guards_mm"]
    nut_overhang_mm = max(0.,fit_rear_advance_mm+layout["end_projection_from_mount_mm"]
                          -layout["rear_cylinder_projection_to_mount_mm"])
    return {
        "current_cast_head_kg":baseline_head_kg,"integrated_cast_head_kg":cast_head_kg,
        "removed_forged_rear_cover_kg":head_removed_kg,"added_columns_kg":add_columns_kg,
        "nominal_machine_mass_delta_kg":delta_kg,"additional_unpriced_parts":"adapter if needed, seat sealing, fasteners, support relocation",
        "new_inner_end_rearward_shift_mm":fit_rear_advance_mm,
        "current_module_excluding_ZSF_and_guards_mm":current_module_mm,
        "integrated_module_excluding_ZSF_and_guards_mm":current_module_mm+nut_overhang_mm,
        "integrated_columns_beyond_prefill_mount_mm":nut_overhang_mm,
        "direct_candidate_frame_column_length_mm":layout["frame_axial_length_mm"]+fit_rear_advance_mm,
        "inherited_baseline_column_phi":phi,"load_capacity_bar":315.,"cap_primary_velocity_m_s":1293/(.06*section_area_mm2(124)),
        "rod_side_velocity_m_s":(1293*(1-(200/280)**2))/(.06*section_area_mm2(100.)),
        "open_bore_nominal_cap_volume_L":CYLINDER["cap_dead_L"],"cap_volume_status":"manifold and seal volume pending",
        "cup": {"isolated_oil_boundary":True,"material":"42CrMo4+QT","yield_min_specification_MPa":500.,
                "cup_OD_mm":cup_OD_mm,"cup_ID_mm":cup_ID_mm,"back_floor_mm":base_mm,"through_neck_OD_mm":neck_OD_mm,
                "integral_cup_and_neck_kg":cup_kg,"cast_displacement_equal_mass_kg":cup_kg,
                "net_hardware_allowance_kg":3.,
                "wall_nominal_vm_at_315_bar_MPa":thick_wall(cup_ID_mm/2,cup_OD_mm/2,31.5),
                "neck_nominal_vm_at_315_bar_MPa":thick_wall(PORT_R_mm,neck_OD_mm/2,31.5),
                "status":"UNVERIFIED for seat contact and port fatigue"},
        "service_estimate_hours_two_technicians":{"separate":{"rod":4.,"piston":8.},
            "integrated_direct":{"rod":5.,"piston":10.,"cast_pressure_seat":16.},
            "integrated_cup":{"rod":5.,"piston":10.,"cup_exchange":12.}},
        "service_times_basis":"planning estimates, pre-staged parts and lifting fixture, lockout and fluid handling included",
    }


def mesh_series(pattern):
    return [read_json(path) for path in sorted(FEA.glob(pattern))]


def convergence(rows, section, keys):
    history = rows[-3:]
    if len(history)<3:
        return {"status":"UNVERIFIED","levels_available":len(rows)}
    detail = {}
    for name in history[-1][section]:
        comparisons = {}
        for key in keys:
            hits = [row[section][name][key] for row in history]
            changes = [abs(last-first)/abs(last) for first,last in zip(hits,hits[1:])]
            comparisons[key] = {"values":hits,"relative_successive_changes":changes}
        detail[name] = comparisons
    worst = max(x for region in detail.values() for q in region.values() for x in q["relative_successive_changes"])
    return {"status":"PASS" if worst<.05 else "FAIL","max_change_fraction":worst,"regions":detail}


def assemble(output_root):
    base_all = read_json(ROOT/"calc/T-1.7/results.json")
    base = base_all["variants"]["cast"]
    integrated_meshes = mesh_series("integrated_cap_*.json")
    integrated = integration(base,integrated_meshes)
    qualified = independent_cylinder()
    retained_cap_meshes = mesh_series("retained_rear_cap_*.json")
    qualified["rear_cover_FEA"] = retained_cap_meshes
    qualified["rear_cover_mesh_convergence"] = convergence(
        retained_cap_meshes,"regions",("static_MPa","range_MPa","fatigue_factor"))
    if retained_cap_meshes:
        qualified["rear_cover_local_pressure_static_status"] = (
            "PASS" if retained_cap_meshes[-1]["regions"]["cover_global"].get("fixed_preload_load_to_yield_factor",0.) >= 1.5 else "FAIL")
    separate_b = mesh_series("gate_contact_*.json")
    gate_meshes = mesh_series("gate_integral_average_both_*.json")
    gate = gate_mass()
    slope_meshes = mesh_series("gate_integral_slope_average_both_*.json")
    budget = revision_machine_mass(base,gate,integrated)
    legacy = base["static_displacement"]
    limit_mm = legacy["C_CLR_01_limit_mm"]
    old_angles = legacy["relative_tilt_rad_xy"]
    direct = legacy["direct_shift_mm_xy"]
    frame_rss_mm = hypot(*(a*77.+b for a,b in zip(old_angles,direct,strict=True)))
    frame_mount_rss_mm = hypot(*(a*352.+b for a,b in zip(old_angles,direct,strict=True)))
    gate_finest = gate_meshes[-1] if gate_meshes else {}
    local_static_factor = min((v["static_factor"] for v in gate_finest.get("components",{}).values()),default=None)
    local_fatigue_factor = min((v["fatigue_factor"] for v in gate_finest.get("components",{}).values()),default=None)
    ratio_mm = gate_finest.get("plate_face_deflection_fatigue_mm")
    displacement_sensitivity = None if ratio_mm is None else {
        "maximum_axial_motion_mm":ratio_mm,
        "constant_stroke_change_percent_at_40_mm":100*ratio_mm/(40+ratio_mm),
        "constant_stroke_change_percent_at_69_mm":100*ratio_mm/(69+ratio_mm),
    }
    contact_peak_MPa = gate_finest.get("static_contact",{}).get("pressure_max_MPa")
    contact_screen_MPa = .6*700.
    contact_fail = contact_peak_MPa is not None and contact_peak_MPa>contact_screen_MPa
    cycle_path = HERE/"cycle_comparison.json"
    cycle = read_json(cycle_path) if cycle_path.exists() else {}
    result = {"task":"T-1.7b","result_status":"conditional_D1_candidate",
              "A":{"selected":"separate_main_cylinder","retained_pressure_boundary":qualified,
                   "retained_frame_static_factor":base["minimum_static_factor"],
                   "retained_frame_fatigue_factor":base["minimum_fatigue_factor"],
                   "retained_frame_mesh_convergence_pass":base["mesh_convergence_pass"],
                   "integrated_direct":integrated,"integrated_direct_FEA":integrated_meshes,
                   "integrated_mesh_convergence":convergence(integrated_meshes,"regions",("static_MPa","range_MPa","fatigue_factor"))},
              "B":{"base_screen":screening(),"separate_moving_shoe_FEA":separate_b,"integral_geometry_and_mass":gate,
                   "integral_FEA":gate_meshes,"tapered_pad_sensitivity_FEA":slope_meshes,"integral_FEA_convergence":convergence(
                       gate_meshes,"components",("static_mises_MPa","fatigue_range_MPa","fatigue_factor")),
                   "rail_insert_transfer_status":"UNVERIFIED for changed load distribution on the cast seat",
                                      "local_static_status":"UNVERIFIED" if local_static_factor is None else "FAIL" if local_static_factor<1.5 else "PASS",
                   "local_fatigue_status":"UNVERIFIED" if local_fatigue_factor is None else "FAIL" if local_fatigue_factor<1. else "PASS",
                   "contact_screen_limit_MPa":contact_screen_MPa,
                   "contact_screen_status":"UNVERIFIED" if contact_peak_MPa is None else "FAIL" if contact_fail else "PASS",
                   "strength_status":"FAIL" if contact_fail or (local_static_factor is not None and local_static_factor<1.5) or (
                       local_fatigue_factor is not None and local_fatigue_factor<1.) else "UNVERIFIED",
                   "length_and_density_sensitivity":displacement_sensitivity,
                   "cycle":cycle,"fall_path_T17":base_all["chamber_bearing"]},
              "C_CLR_01":{"limit_mm":limit_mm,"chamber_mounted_guides_lever_mm":77.,
                          "frame_mounted_counterexample_lever_mm":352.,"T17_chamber_guides_SRSS_mm":frame_rss_mm,
                          "T17_frame_guides_SRSS_mm":frame_mount_rss_mm,"T17b_status":"UNVERIFIED for revised pad traction"},
              "machine_mass":budget}
    write_json(HERE/"results.json",result)
    frame = read_yaml(ROOT/"design/frame.t17.yaml")
    frame.update(task="T-1.7b",status="conditional_D1_review",selected_variant="cast",
                 main_cylinder_architecture="separate_main_cylinder")
    frame["interfaces"]["guide_reference_plane"] = (
        "Rod-tip station of moving crosshead. Both guide rails located and dowelled to the machined chamber module; "
        "77 mm from reference station to punch face at pressing. No independent frame rail datum.")
    frame["interfaces"]["gate_shoe_and_fixed_rails"] = "design/slide_gate.t17b.yaml"
    frame["interfaces"]["open_discharge_bay_nominal_mm"] = frame["interfaces"].pop("open_discharge_bay_mm")
    frame["results"] = {"inherited_T17_static_factor":base["minimum_static_factor"],
                        "inherited_T17_fatigue_factor":base["minimum_fatigue_factor"],
                        "inherited_T17_lateral_srss_mm":frame_rss_mm,"revised_load_combination_status":"UNVERIFIED",
                        "machine_mass_kg":budget["machine_T17b_kg"]}
    frame["D1_checks"] += ["Map actual rail contact pressure through insert and cast R20 into the frame model.",
                           "Complete independent cover, barrel and bolt fatigue qualification; assemble full C-ENV-01 envelope."]
    write_yaml(output_root/"design/frame.t17b.yaml",frame)
    insert_mass_kg = next(row["mass_kg"] for row in base["mass"]["frame_rows"]
                          if row["node"].startswith("Распределительная вставка"))
    contact_geometry = {
        "rails":{"axial_length_mm":RAIL_mm,"rear_bearing_each_mm":[82.,180.],
                 "gap_between_rails_mm":176.,"pair_mass_kg":gate["rail_pair_mass_kg"]},
        "insert":{"size_mm":[340.,180.,55.],"outlet_width_height_radius_mm":[176.,74.,20.],
                  "nominal_rectangular_passage_mm":[164.,62.],"mass_kg":insert_mass_kg},
        "combined_nominal_pad_area_mm2":base_all["chamber_bearing"]["bearing_area_mm2"],
        "average_insert_bearing_at_static_force_MPa":base_all["chamber_bearing"]["mean_pressure_MPa"],
    }
    slide = {"schema_version":1,"task":"T-1.7b","status":"investigation_failed_or_unverified",
             "frame":"design/frame.t17b.yaml","inherited_mounting_chamber_window_mm":[150,200],
             "force_static_N":STATIC_N,"fatigue_force_range_N":[0.,CYCLIC_N],"fatigue_cycles":10_000_000,
             "part":gate,"load_transfer_geometry":contact_geometry,"material_and_proof":{"blade":{"grade":"34CrNiMo6+QT","Rp02_MPa":700.,"Rm_MPa":900.},
                  "fixed_rails":{"grade":"34CrNiMo6+QT","Rp02_MPa":800.,"Rm_MPa":1000.,"flat_ruling_section_mm":RAIL_mm},
                  "insert":{"grade":"34CrNiMo6+QT","Rp02_MPa":800.,"Rm_MPa":1000.,"depth_mm":55.}},
             "working_gate_travel_mm":OPEN_mm,"installed_gate_travel_mm":80.,
             "briquette_plane_mm_from_punch_home":205.,"contact_friction_coefficient":.15,
             "pad_geometry_mm":[82.,180.],"pad_count":2,"fixed_rail_axial_length_mm":RAIL_mm,
             "moving_backing_axial_depth_mm":SHOE_mm,"open_shoe_lower_face_above_axis_mm":OPEN_mm-HEIGHT_mm/2,
             "drive":{"cylinder_ref":"CY-GATE design/cylinders.t16.yaml","bore_mm":80.,"rod_mm":45.,"speed_m_s":.6,"ramp_m_s2":20.,
                      "cylinder_filled_mass_kg":23.04,"verified_kinematic_comparison":cycle},
             "local_calculix_finest":gate_finest,"body_proof_status":result["B"]["strength_status"],
             "D1_checks":["Full swept envelope and vertical sealing overlap in the closed position.",
                          "Dowel/keeper and fail-safe retention for the travelling gate. Verify clearance under sag.",
                          "Measure contact pattern, repeat with realistic rear face compliance and tolerance stack."]}
    write_yaml(output_root/"design/slide_gate.t17b.yaml",slide)
    integrated_regions = integrated_meshes[-1]["regions"] if integrated_meshes else {}
    cover_regions = retained_cap_meshes[-1]["regions"] if retained_cap_meshes else {}
    metrics = {"task":"T-1.7b","machine_mass_kg":budget["machine_T17b_kg"],
               "machine_upper_named_uncertainty_kg":budget["uncertainty_kg"]["named_upper_excluding_estimate_line_error"],
               "integrated_cast_machine_kg":budget["direct_integrated_machine_kg"],
               "integrated_cast_min_fatigue_factor":min((x["fatigue_factor"] for x in integrated_regions.values()),default=None),
               "retained_frame_static_factor":base["minimum_static_factor"],"retained_frame_fatigue_factor":base["minimum_fatigue_factor"],
               "retained_rear_cover_proof_factor":cover_regions.get("cover_global",{}).get("fixed_preload_load_to_yield_factor"),
               "machine_mass_before_kg":budget["machine_T17_kg"],"machine_limit_margin_kg":budget["margin_to_5000_kg"],
               "machine_mass_target_status":budget["status_target_4850"],"machine_mass_target_margin_kg":budget["margin_to_4850_kg"],
               "force_static_N":STATIC_N,"force_fatigue_N":CYCLIC_N,"pressure_static_bar":315.,"pressure_fatigue_bar":300.,
               "guide_basis_T17_lateral_srss_mm":frame_rss_mm,"modified_C_CLR_01_status":"UNVERIFIED",
               "gate_static_local_factor":min((c["static_factor"] for c in gate_finest.get("components",{}).values()),default=None),
               "gate_fatigue_local_factor":min((c["fatigue_factor"] for c in gate_finest.get("components",{}).values()),default=None),
               "gate_plate_face_deflection_at_reserve_mm":gate_finest.get("plate_face_deflection_fatigue_mm"),
               "gate_peak_contact_pressure_MPa":contact_peak_MPa,
               "gate_contact_screen_status":result["B"]["contact_screen_status"],
               "gate_local_mesh_convergence_status":result["B"]["integral_FEA_convergence"]["status"],
               "max_abs_delta_cycle_s":max((abs(row["delta_cycle_s"]) for row in cycle.get("cycle_comparison",[])),default=None)}
    write_json(output_root/"metrics.json",metrics)
    return result


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=ROOT)
    args = parser.parse_args()
    assemble(args.out)

