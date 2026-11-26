"""Assemble round-2 checks, mass budget and reference geometry from CCX summaries."""
import argparse
import json
from math import hypot, pi
from pathlib import Path

import yaml

from frame_analytic import (
    ADAPTER_mm, BRIQUETTE_PATH_HEIGHT_mm, BRIQUETTE_PATH_WIDTH_mm, COLLAR_H_mm,
    CHAMBER_MODEL, COLUMN_D_mm, COLUMN_HOLE_mm, COLUMN_INNER_SEAT_BORE_mm, COLUMN_MID_BLEND_mm, COLUMN_MID_D_mm,
    COLUMN_OUTER_BLEND_mm,
    CYCLIC_N, CYLINDER, CYCLES, DISCHARGE_BAY_mm, ECC_mm, HALF_PITCH_mm,
    HERE, MID_SPAN_mm, NUT_BEAR_OD_mm, NUT_H_mm, NUT_S_mm, OUTLET_HEIGHT_mm,
    OUTLET_RADIUS_mm, OUTLET_WIDTH_mm, PAD_HEIGHT_mm, PAD_WIDTH_mm, PRELOAD_N,
    PRELOAD_SCATTER, ROOT, STATIC_N, THREAD_P_mm, VARIANTS, WASHER_H_mm,
    chamber_bearing, column, discharge_rails, layout, middle_span, outline_radius_mm, section,
)
from frame_fea import FEA, write_json
from mass_budget import STOP_FRAME_kg, machine_mass, mechanical_mass

ENDS = ("cylinder", "chamber")
CONVERGENCE_FIELDS = ("static_mises_MPa", "principal_tensile_MPa", "principal_abs_MPa", "range_mises_MPa",
                      "range_principal_abs_MPa", "fatigue_utilisation")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def column_shoulder():
    levels = [d for p in sorted(FEA.glob("column_shoulder_[0-9].json"))
              if (d:=read_json(p)).get("outer_blend_mm")==COLUMN_OUTER_BLEND_mm
              and d.get("midspan_diameter_mm")==COLUMN_MID_D_mm]
    final = levels[-1]
    convergence = {}
    fields = ("static_mises_MPa","principal_abs_MPa","fatigue_utilisation")
    for name,zone in final["zones"].items():
        previous = levels[-2]["zones"][name]
        relative = {key:abs(zone[key]-previous[key])/abs(zone[key]) for key in fields}
        relative_h = zone["h_mm"]/zone["h_limit_mm"] if zone["h_mm"] is not None else 0.
        convergence[name] = {"changes_fraction":relative,"h_to_limit":relative_h,
                             "pass":len(levels)>=3 and max(relative.values())<.05 and relative_h<=1.}
    return {"levels":[{"level":d["mesh_level"],"nodes":d["nodes"],"tetrahedra":d["tetrahedra"]} for d in levels],
            "finest":final,"convergence":convergence,
            "convergence_pass":all(row["pass"] for row in convergence.values())}


def mesh_study(levels):
    last = levels[-1]
    previous = levels[-2] if len(levels)>1 else None
    convergence = {}
    for name,zone in last["regions"].items():
        changes = {}
        if previous:
            changes = {key:abs(zone[key]-previous["regions"][name][key])/max(abs(zone[key]),1e-9)
                       for key in CONVERGENCE_FIELDS}
        h_pass = zone["h_limit_mm"] is None or zone["h_mm"]<=zone["h_limit_mm"]
        required_changes = changes.copy()
        # In a predominantly compressive zone the most extreme principal
        # value in absolute terms governs. Keep the positive peak for review.
        if all(d["regions"][name]["principal_tensile_MPa"]<d["regions"][name]["principal_abs_MPa"]
               for d in levels):
            required_changes.pop("principal_tensile_MPa",None)
        # Cast profile_1/2 are the ray-to-ring roots. Profile_3/4 are
        # the transitions to the column bosses, from cast_outline ordering.
        is_boss_blend = last.get("variant")=="cast" and name in ("profile_3","profile_4")
        is_conical_seat = name=="column_conical_seat"
        diagnostic = ((is_conical_seat or is_boss_blend)
            and max(d["regions"][name]["static_mises_MPa"] for d in levels)
                < min(d["regions"]["traverse_global"]["static_mises_MPa"] for d in levels)
            and max(d["regions"][name]["fatigue_utilisation"] for d in levels)
                < min(d["regions"]["traverse_global"]["fatigue_utilisation"] for d in levels))
        detail = ("cast_ray_to_column_boss" if is_boss_blend else "column_conical_seat") if diagnostic else None
        convergence[name] = {"h_mm":zone["h_mm"],"h_limit_mm":zone["h_limit_mm"],
                             "required":not diagnostic,"diagnostic_detail":detail,"changes_fraction":changes,
                             "governing_changes_fraction":required_changes,
                             "pass":bool(len(levels)>=3 and h_pass and max(required_changes.values())<.05)}
    weld = last.get("IIW_hot_spot_range_MPa")
    if weld is not None:
        change = abs(weld-previous["IIW_hot_spot_range_MPa"])/weld if previous else None
        convergence["IIW_hot_spot"] = {"changes_fraction":{"range_MPa":change},"required":True,
                                       "pass":len(levels)>=3 and change<.05}
    envelope = {key: {
        metric:max(d["regions"][key][metric] for d in levels)
        for metric in ("static_mises_MPa","range_mises_MPa")
    } for key in last["regions"] if key in ("traverse_global","insert_global")}
    return {"finest":last,"convergence":convergence,"mesh_level_count":len(levels),
            "elastic_proof_envelope":envelope,
            "mesh_history":[{"level":d["mesh_level"],"nodes":d["nodes"],"elements":d["tetrahedra"]}
                            for d in levels]}


def results_for_end(variant,end):
    levels = []
    for path in sorted(FEA.glob(f"{variant.name}_{end}_[0-9].json")):
        data = read_json(path)
        if (data.get("round")==2 and data.get("column_inner_seat_bore_mm")==COLUMN_INNER_SEAT_BORE_mm
                and (end=="cylinder" or (data.get("chamber_model")==CHAMBER_MODEL
                     and data.get("traverse_depth_mm")==variant.chamber_depth_mm))):
            levels.append(data)
    if not levels:
        raise FileNotFoundError(f"No round-2 CCX solution for {variant.name}/{end}")
    return mesh_study(levels)


def evaluate(variant, criteria, shoulder, insert_fea):
    fea = {end:results_for_end(variant,end) for end in ENDS}
    cyl, chamber = (fea[end]["finest"] for end in ENDS)
    tie = {end:column(variant.at_end(end)) for end in ENDS}
    dims = layout(variant)
    insert = insert_fea["finest"]
    mass = machine_mass(mechanical_mass(variant,cyl,chamber,insert))
    compliance_mm_N = tie["cylinder"]["middle_span_compliance_mm_N"] + sum(
        (1-p["load_fraction"])*p["clamp_compliance_mm_N"] for p in tie.values())
    tie_ext_mm = compliance_mm_N*STATIC_N/4
    tie_tilt_rad = tie_ext_mm*ECC_mm/HALF_PITCH_mm**2
    lever_mm = dims["guide_to_punch_lever_mm"]
    # Each entry comes from its own eccentric load; magnitudes give a bound
    # allowing opposing end rotations. Combine the two independent axes by SRSS.
    rails = discharge_rails()
    outlet = chamber_bearing()
    discharge_pass = (outlet["discharge_axial_clearance_mm"]>=5.
                      and outlet["minimum_ejected_tail_to_gate_clearance_mm"]>=5.
                      and outlet["aperture_corner_reserve_mm"]>0.
                      and outlet["bearing_area_mm2"]>=outlet["minimum_260x160_net_footprint_mm2"]
                      and rails["pressure_max_MPa"]<=outlet["pressure_limit_MPa"])
    angles_rad = [abs(cyl["face_relative_tilt_rad_xy"][i])+abs(chamber["face_relative_tilt_rad_xy"][i])
                  +tie_tilt_rad+rails["relative_tilt_rad_xy"][i]+abs(insert["relative_tilt_rad_xy"][i])
                  for i in range(2)]
    direct_mm = [abs(cyl["face_relative_transverse_shift_mm_xy"][i])
                 +abs(chamber["face_relative_transverse_shift_mm_xy"][i])+abs(insert["relative_shift_mm_xy"][i])
                 for i in range(2)]
    offsets_mm = [lever_mm*angle+direct for angle,direct in zip(angles_rad,direct_mm,strict=True)]
    lateral_mm = hypot(*offsets_mm)
    nominal = {end: section(variant.at_end(end),end) for end in ENDS}
    nominal_checks = {}
    for end in ENDS:
        cut = fea[end]["finest"]["verification"]
        analytic = nominal[end]
        centroid_mm = cut["FEA_cut_first_moment_mm3"]/cut["FEA_cut_area_mm2"]
        I_mm4 = cut["FEA_cut_inertia_about_mid_depth_mm4"]-cut["FEA_cut_area_mm2"]*centroid_mm**2
        lever_cut_mm = variant.at_end(end).depth_mm/2-centroid_mm
        stress_MPa = cut["FEA_bending_moment_Nmm"]*lever_cut_mm/I_mm4
        comparison_MPa = analytic["section_outer_face_nominal_MPa"]
        nominal_checks[end] = {"FEA_I_mm4":I_mm4, "FEA_centroid_shift_mm":centroid_mm,
                               "FEA_nominal_MPa":stress_MPa,
                               "analytic_nominal_MPa":comparison_MPa,
                               "stress_difference_fraction":abs(stress_MPa/comparison_MPa-1)}
    chamber_y_cut = section(variant.at_end("chamber"),"chamber",cut_axis=1)
    chamber_net_MPa = max(nominal["chamber"]["section_nominal_bending_MPa"],
                          chamber_y_cut["section_nominal_bending_MPa"])
    min_yield_factor = criteria["C-STR-01"]["min_safety_factor_yield"]
    # At fixed preload, the triangle inequality on the von Mises norm
    # bounds the proof stress using the largest elastic response on any mesh.
    proof = {}
    for key,end,zone,yield_MPa in (
        ("cylinder_local_elastic","cylinder","traverse_global",variant.yield_MPa),
        ("chamber_local_elastic","chamber","traverse_global",variant.at_end("chamber").yield_MPa),
        ("insert_local_elastic","insert","insert_global",800.),
    ):
        model = insert_fea if end=="insert" else fea[end]
        bounds = model["elastic_proof_envelope"][zone]
        peak_MPa = bounds["static_mises_MPa"]
        delta_MPa = bounds["range_mises_MPa"]*STATIC_N/CYCLIC_N
        proof_MPa = peak_MPa+(min_yield_factor-1.)*delta_MPa
        proof[key] = {"operating_bound_MPa":peak_MPa,"proof_bound_MPa":proof_MPa,
                      "yield_min_MPa":yield_MPa,"n_pl_min":1.,
                      "pass_at_1p5_service_with_preload":proof_MPa<=yield_MPa}
    static = {
        "cylinder_net": variant.yield_MPa/nominal["cylinder"]["section_nominal_bending_MPa"],
        "chamber_net": variant.at_end("chamber").yield_MPa/chamber_net_MPa,
        "discharge_rails_nominal":rails["static_factor"],
        "column_shoulder_elastic":shoulder["finest"]["zones"]["all"]["local_elastic_factor"],
        "column_threads": min(min(p["thread_yield_factor"],p["thread_strip_screen_factor"])
                              for p in tie.values()),
    }
    static.update({key:d["yield_min_MPa"]/d["operating_bound_MPa"] for key,d in proof.items()})
    fatigue = {
        "column_thread":min(p["thread_fatigue_factor"] for p in tie.values()),
        "column_shoulder":shoulder["finest"]["zones"]["all"]["fatigue_factor"],
        "cylinder_body":cyl["body_FKM_local_screen_factor"],
        "chamber_body":chamber["body_FKM_local_screen_factor"],
        "chamber_insert":insert["regions"]["insert_global"]["fatigue_factor"],
        "discharge_rails_nominal":rails["nominal_fatigue_factor"],
    }
    if cyl["IIW_hot_spot_factor"] is not None:
        fatigue.update(cylinder_weld=cyl["IIW_hot_spot_factor"],chamber_weld=chamber["IIW_hot_spot_factor"])
    controlling = min(fatigue,key=fatigue.get)
    clear = criteria["C-CLR-01"]
    clear_limit_mm = clear["max_mm"]*clear["deflection_share_max"]
    static_min = min(static.values())
    static_pass = static_min>=min_yield_factor and all(
        p["pass_at_1p5_service_with_preload"] for p in proof.values())
    fatigue_pass = fatigue[controlling]>=1.
    conv_pass = (shoulder["convergence_pass"]
                 and all(zone["pass"] for e in (*fea.values(),insert_fea) for zone in e["convergence"].values()
                         if zone["required"]))
    residual_N = min(p["residual_clamp_min_N"] for p in tie.values())
    error = max(e["finest"]["verification"]["FEA_bending_error_fraction"] for e in fea.values())
    stress_verification = max(row["stress_difference_fraction"] for row in nominal_checks.values())
    return {
        "material":variant.material,"dimension_screen":dims,"mass":mass,"fea":fea,"column_by_end":tie,
        "preload_residual_min_N":residual_N, "static_factors":static,
        "fixed_preload_elastic_proof_bound":proof,
        "minimum_static_factor":static_min, "C_STR_01_screen_pass":static_pass,
        "fatigue_factors":fatigue, "controlling_fatigue_zone":controlling,
        "minimum_fatigue_factor":fatigue[controlling], "C_FAT_01_screen_pass":fatigue_pass,
        "relative_reduction_in_controlling_fatigue_utilisation_for_pass":max(0.,1-fatigue[controlling]),
        "nominal_cylinder_net_cyclic_MPa":nominal["cylinder"]["section_nominal_bending_MPa"]*CYCLIC_N/STATIC_N,
        "static_displacement": {
            "cylinder_face_deflection_mm":cyl["centred_face_axial_deflection_mm"],
            "chamber_face_deflection_mm":chamber["centred_face_axial_deflection_mm"],
            "axial_opening_mm":(tie_ext_mm+rails["axial_opening_mm"]+cyl["centred_face_axial_deflection_mm"]
                                +chamber["centred_face_axial_deflection_mm"]+insert["axial_deflection_mm"]),
            "insert_opening_mm":insert["axial_deflection_mm"],
            "tie_and_seat_opening_mm":tie_ext_mm, "relative_tilt_rad_xy":angles_rad,
            "direct_shift_mm_xy":direct_mm, "offset_mm_xy":offsets_mm,
            "lateral_srss_mm":lateral_mm, "C_CLR_01_limit_mm":clear_limit_mm,
            "C_CLR_01_screen_pass":lateral_mm<=clear_limit_mm, "guide_to_punch_lever_mm":lever_mm,
        },
        "midcut_moment_max_error_fraction":error, "midcut_nominal_stress_error_fraction":stress_verification,
        "midcut_nominal_stress_checks":nominal_checks,
        "chamber_analytic_midcuts":{"x":nominal["chamber"],"y":chamber_y_cut},
        "mesh_convergence_pass":conv_pass, "discharge_layout_pass":discharge_pass,
        "verified_candidate": (static_pass and fatigue_pass and conv_pass and discharge_pass and residual_N>0.
                               and lateral_mm<=clear_limit_mm and max(error,stress_verification)<=.25),
    }


def result_bundle():
    criteria_file = ROOT/"ops/criteria/design_criteria.yaml"
    criteria = yaml.safe_load(criteria_file.read_text(encoding="utf-8"))["criteria"]
    shoulder = column_shoulder()
    insert = mesh_study([d for p in sorted(FEA.glob("insert_pads_[0-9].json"))
                         if (d:=read_json(p)).get("chamber_model")==CHAMBER_MODEL])
    cases = {v.name:evaluate(v,criteria,shoulder,insert) for v in VARIANTS}
    under_stop = {name:c for name,c in cases.items() if c["mass"]["frame_kg"]<=STOP_FRAME_kg}
    pool = under_stop or cases
    options = [name for name,c in under_stop.items() if c["verified_candidate"]]
    benchmark_path = FEA/"plate_beam_benchmark.json"
    benchmark = read_json(benchmark_path) if benchmark_path.is_file() else None
    verification_pass = (max(cases["plate"]["midcut_moment_max_error_fraction"],
                             cases["plate"]["midcut_nominal_stress_error_fraction"])<=.10
                         and benchmark is not None and max(benchmark["relative_stress_error"],
                                                           benchmark["relative_deflection_error"])<=.10)
    finalist = min(options,key=lambda name:cases[name]["mass"]["frame_kg"]) if options and verification_pass else None
    best = max(pool,key=lambda name:(min(pool[name]["minimum_static_factor"]/1.5,
                                        pool[name]["minimum_fatigue_factor"]),-pool[name]["mass"]["frame_kg"]))
    stop = not any(c["C_STR_01_screen_pass"] and c["C_FAT_01_screen_pass"] for c in under_stop.values())
    status = "selected" if finalist else ("stop_strength_and_mass" if stop else "verification_incomplete")
    area_mm2 = pi*CYLINDER["bore_mm"]**2/4
    return {
        "task":"T-1.7","round":2,"study_status":status,"selected_variant":finalist,
        "reference_variant":best,"force_static_N":STATIC_N,"force_gross_315bar_N":31.5*area_mm2,
        "force_gross_300bar_N":30.*area_mm2,"force_fatigue_N":CYCLIC_N,"fatigue_cycles":CYCLES,
        "eccentricity_mm_per_axis":ECC_mm,"machine_limit_xyz_mm":criteria["C-ENV-01"]["max_mm"],
        "gates":{g["id"]:g["status"] for g in read_json(ROOT/"gates.t17.json")["gates"]},
        "plate_verification_pass":verification_pass,"pure_bending_benchmark":benchmark,
        "chamber_bearing":chamber_bearing(),"discharge_rails":discharge_rails(),
        "column_shoulder_FEA":shoulder,"insert_FEA":insert,"variants":cases,
    }


def write_deliverables(output_dir, result):
    selected = result["selected_variant"]
    key = selected or result["reference_variant"]
    v = next(v for v in VARIANTS if v.name==key)
    c = result["variants"][key]
    cfg = {
        "schema_version":2,"task":"T-1.7","round":2,"status":result["study_status"],
        "selected_variant":selected,"reference_variant":key,
        "traverses": {
            end: {"depth_mm":v.at_end(end).depth_mm, "material":v.material,
                  "yield_min_MPa":v.at_end(end).yield_MPa,"tensile_min_MPa":v.tensile_MPa,
                  "profile_fillet_mm":v.radius_mm,"cast_ring_OD_mm":2*v.at_end(end).ring_radius_mm or None,
                  "cast_rib_width_mm":2*v.at_end(end).rib_half_width_mm or None,
                  "cast_boss_OD_mm":200 if v.name=="cast" else None,
                  "half_width_at_midcut_mm":outline_radius_mm(v.at_end(end),end),
                  "flange_mm":v.flange_mm or None}
            for end in ENDS},
        "interfaces": {
            "inner_bearing_planes_spacing_mm":MID_SPAN_mm,"cylinder_cover_OD_mm":CYLINDER["cover_OD_mm"],
            "barrel_passage_mm":360,"cylinder_studs":CYLINDER["tie_rods"],
            "insert_footprint_mm":[PAD_WIDTH_mm,PAD_HEIGHT_mm],"insert_depth_mm":ADAPTER_mm,
            "insert_material":"34CrNiMo6+QT","open_discharge_bay_mm":DISCHARGE_BAY_mm,
            "discharge_rails_clear_width_mm":OUTLET_WIDTH_mm,
            "discharge_rail_cross_section_mm":[(PAD_WIDTH_mm-OUTLET_WIDTH_mm)/2,PAD_HEIGHT_mm],
            "outlet_width_height_radius_mm":[OUTLET_WIDTH_mm,OUTLET_HEIGHT_mm,OUTLET_RADIUS_mm],
            "minimum_rectangular_outlet_mm":[BRIQUETTE_PATH_WIDTH_mm,BRIQUETTE_PATH_HEIGHT_mm],
            "guide_reference_plane":"Plane of the rod tip on the travelling crosshead (design assumption).",
            "layout":c["dimension_screen"],
        },
        "columns": {
            "quantity":4,"square_pitch_mm":2*HALF_PITCH_mm,"bore_mm":COLUMN_HOLE_mm,
            "material":"42CrMo4+QT","thread_mm":[COLUMN_D_mm,THREAD_P_mm],
            "smooth_span_diameter_mm":COLUMN_MID_D_mm,"smooth_span_mm":middle_span()["smooth_length_mm"],
            "midspan_shoulder_fillet_mm":COLUMN_MID_BLEND_mm,"thread_end_shoulder_fillet_mm":COLUMN_OUTER_BLEND_mm,
            "inside_seat_mouth_diameter_mm":COLUMN_INNER_SEAT_BORE_mm,
            "inside_seat_chamfer_depth_mm":COLUMN_OUTER_BLEND_mm,
            "preload_N_per_end":PRELOAD_N,"preload_scatter_fraction":PRELOAD_SCATTER,
            "collar_diameter_height_mm":[NUT_BEAR_OD_mm,COLLAR_H_mm],
            "nut_across_flats_height_mm":[NUT_S_mm,NUT_H_mm],
            "washer_diameter_thickness_mm":[NUT_BEAR_OD_mm,WASHER_H_mm],
            "per_end_load_fraction":{end:p["load_fraction"] for end,p in c["column_by_end"].items()},
        },
        "results":{"frame_mass_kg":c["mass"]["frame_kg"],"machine_mass_kg":c["mass"]["machine_kg"],
                   "minimum_static_factor":c["minimum_static_factor"],
                   "minimum_fatigue_factor":c["minimum_fatigue_factor"],
                   "preload_residual_min_N":c["preload_residual_min_N"],
                   "lateral_srss_mm":c["static_displacement"]["lateral_srss_mm"]},
        "D1_checks": ["Contact and opening with friction coefficient 0.15 on the chamber load path.",
                      "Confirmation of guide bases, chute, moving gate clearances and whole-machine envelope.",
                      "Column thread runout, nut proof load, preload process and casting qualification."],
    }
    metrics = {key:result[key] for key in ("task","round","study_status","selected_variant","reference_variant",
                                           "force_static_N","force_fatigue_N","fatigue_cycles","gates","chamber_bearing")}
    metrics["variants"] = {name:{
        "frame_mass_kg":a["mass"]["frame_kg"],"machine_mass_kg":a["mass"]["machine_kg"],
        "minimum_static_factor":a["minimum_static_factor"],"minimum_fatigue_factor":a["minimum_fatigue_factor"],
        "lateral_srss_mm":a["static_displacement"]["lateral_srss_mm"],
        "frame_axial_length_mm":a["dimension_screen"]["frame_axial_length_mm"],
        "preload_residual_min_N":a["preload_residual_min_N"],
        "cylinder_nominal_net_cyclic_MPa":a["nominal_cylinder_net_cyclic_MPa"],
        "mass_frame_1550_pass":a["mass"]["frame_target_pass"],
        "mass_machine_4750_pass":a["mass"]["machine_D1_target_pass"],
        "mass_machine_5000_pass":a["mass"]["machine_C_MASS_01_limit_pass"],
        "mesh_convergence_pass":a["mesh_convergence_pass"],
    } for name,a in result["variants"].items()}
    paths = ([output_dir/"results.json",output_dir/"frame.t17.yaml",output_dir/"metrics.json"] if output_dir
             else [HERE/"results.json",ROOT/"design/frame.t17.yaml",ROOT/"metrics.json"])
    write_json(paths[0],result)
    paths[1].write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False,width=95),encoding="utf-8",newline="\n")
    write_json(paths[2],metrics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    args = parser.parse_args()
    write_deliverables(args.output_dir,result_bundle())
