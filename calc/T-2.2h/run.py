"""Assemble deterministic T-2.2h engineering results from solver summaries."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0,str(HERE/"fea"))

from hand import frame, select, section_grid, skew_weight, ECCENTRICITY_MM, E_MPa
from layout import (STATIONS, KEY_CAM, KEY_CLOSED_Y_MM, LOCK_LOWER_Y_MM, LOCK_UPPER_Y_MM,
                    SHOE_ABS_Y_MAX_MM, interface, Layout)
from loads import final_envelopes, janssen, main_cylinder_force_N, read_json, read_yaml, shoe_envelope
from mass import budget, RAIL_ABS_Y_MM, RAIL_Z_MM, RAIL_LENGTH_MM
from ring import GEOMETRY

SCHEMA = 1


def write_json(path, value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)+"\n",
                    encoding="utf-8",newline="\n")


def optional_rows(name):
    path=HERE/"fea"/name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def variation(values):
    if len(values)!=3:
        return None
    return abs((values[-1]-values[-2])/values[-1])


def axis_moments(case):
    """Axial resultants at the actual working bore, before the backing."""
    axial_N=case["wall_friction_N"]
    upper_N=case["mu"]*case["roof"]["normal_force_N"]
    side_N=case["mu"]*case["each_side_normal_force_N"]
    centroid_y_mm=2*upper_N*ECCENTRICITY_MM/axial_N
    rail_y_mm=sum(RAIL_ABS_Y_MM)/2
    negative_N=axial_N*(1.-centroid_y_mm/rail_y_mm)/2
    positive_N=axial_N-negative_N
    area_mm2=(RAIL_ABS_Y_MM[1]-RAIL_ABS_Y_MM[0])*(RAIL_Z_MM[1]-RAIL_Z_MM[0])
    upper_support_centroid_z_mm=RAIL_Z_MM[1]/2
    upper_force_N=upper_N+side_N
    upper_force_z_mm=30.*upper_N/upper_force_N
    seat_pressure_MPa=positive_N/area_mm2
    # Upper half equilibrium taken at the centroid of the upper parts of the
    # rail bearing faces. The lower half produces the opposite couple.
    upper_half_couple_Nmm=upper_force_N*(upper_support_centroid_z_mm-upper_force_z_mm)
    return dict(friction_315_N=axial_N, roof_or_floor_315_N=upper_N, side_each_315_N=side_N,
                bore_centroid_xyz_mm=[case["roof"]["centroid_x_mm"],centroid_y_mm,0.],
                rail_bearing_x_mm=349.,rail_y_centres_mm=[-rail_y_mm,rail_y_mm],
                rail_net_area_each_mm2=area_mm2,
                mean_rail_reactions_315_N=[negative_N,positive_N],
                reaction_imbalance_N=abs(positive_N+negative_N-axial_N),
                upper_half_couple_Nmm=upper_half_couple_Nmm,
                upper_half_bore_friction_z_mm=upper_force_z_mm,
                upper_half_support_z_mm=upper_support_centroid_z_mm,
                extra_axial_bending_from_backing_per_top_Nmm=upper_N*(GEOMETRY.inner_z_mm-30.),
                extra_axial_bending_from_backing_per_side_Nmm=side_N*(GEOMETRY.inner_y_mm-75.),
                nominal_max_rail_pressure_315_MPa=seat_pressure_MPa,
                nominal_max_rail_pressure_300_MPa=seat_pressure_MPa*300/315,
                required_area_per_rail_at_cyclic_screen_mm2=(positive_N*300/315)/80.,
                cast_cyclic_screen_MPa=80.,cast_static_screen_MPa=390.)


def dimensions():
    g=GEOMETRY
    layout=Layout(g.material,g.side_half_mm-75.,g.band_half_mm-30.,g.band_half_mm-30.)
    data=interface(layout)
    data.pop("lock_side_x_relief",None)
    gate=read_yaml("design/slide_gate.t17d.yaml")
    frame_ref=read_yaml("design/frame.t17d.yaml")
    data["punch_face_ejection_end_x_mm"]=[
        frame_ref["geometry"][key]+90. for key in
        ("punch_face_nominal_eject_end_x_mm","punch_face_maximum_eject_end_x_mm")]
    data["punch_overtravel_from_new_gate_mm"]=gate["overtravel_mm"]
    data["gate_projection_params_ejection_overtravel_mm"]=read_yaml(
        "calc/T-2.6/params/params.t26a.yaml")["chamber"]["ejection_overtravel_mm"]
    data.pop("main_overrun_mm",None)
    data["lock_cut_to_roof_clearance_mm"]=205.-data["lock_x_max_mm"]
    data["shoe_face_x_mm"]=[5.2,204.8]
    data["axial_rails_abs_y_mm"]=list(RAIL_ABS_Y_MM)
    data["axial_rails_z_mm"]=list(RAIL_Z_MM)
    data["axial_rails_x_mm"]=[349.-RAIL_LENGTH_MM,349.]
    data["axial_rail_to_gate_sweep_in_Y_mm"]=RAIL_ABS_Y_MM[0]-130.
    data["axial_rail_to_gate_housing_pocket_half_width_mm"]=RAIL_ABS_Y_MM[0]-340.2/2
    data["roof_to_column_axial_zone_transverse_clearance_mm"]=540./2-70./2-g.side_half_mm
    data["lock_max_z_by_region_mm"]={
        "at_cast_cap_abs_y_135_to_198_mm":236.,
        "at_moving_key_abs_y_up_to_300_mm":170.,
        "at_outer_lower_return_abs_y_178_to_246_mm":92.,
    }
    data.pop("lock_to_column_z_clearance_mm",None)
    data["lock_cap_horizontal_clearance_to_column_mm"]=540./2-70./2-198.
    data["parked_key_vertical_clearance_to_column_mm"]=540./2-70./2-170.
    data["geometry_clearances_scope"]="Nominal dimensional screen. Mating tolerances, contact features, assembly and service remain open."
    return data


def collect():
    loads=final_envelopes()
    proof=loads["315"]
    governing_normal=max(proof,key=lambda r:r["roof"]["normal_force_N"])
    governing_friction=max(proof,key=lambda r:r["wall_friction_N"])
    short_cases=[janssen(main_cylinder_force_N(315),c["K"],c["mu"],40./1.23)
                 for c in proof if c["basis"]=="T-2.6_eta"]
    gate_case=max(short_cases,key=lambda r:r["gate_force_N"])
    g=GEOMETRY
    hand=frame(g,governing_normal["roof"]["inlet_MPa"],0.,ECCENTRICITY_MM,96,detail=False)

    rolls=optional_rows("ring_screen.json")
    windows=optional_rows("window_screen.json")+optional_rows("window_fine.json")
    end=optional_rows("end_screen.json")
    key_sensitivity=optional_rows("window_half.json")+optional_rows("window_double.json")
    cut_edge_rows=optional_rows("window_edge.json")
    mass=budget(g,windows[-1] if windows else None)
    frozen_ref=budget(g)
    hand_selection=select(mass["max_ring_and_liner_kg_at_given_window"])
    gates={r["id"]:{"status":r["status"],"value":r["value"],"unit":r["unit"]}
           for r in read_json("gates.t22h.json")["gates"]}
    hydraulic=read_json("calc/T-2.6/results.json")
    source_review="ops/reports/T-2.6/GK_review.md, adverse point stated in D-GK-13"

    roof_checks=[{
        "size_mm":row["size_mm"],
        "normal_case_mid":row["cases"]["roof_force"]["section_margins"]["mid"],
        "normal_case_end":row["cases"]["roof_force"]["section_margins"]["end"],
        "opening_backing_300_mm":row["cases"]["roof_force"]["opening_backing_300_mm"],
        "normal_case_force_balance_fraction":max(row["cases"]["roof_force"]["force_balance_fraction"]),
        "integrated_sections_315":row["cases"]["roof_force"]["integrated_sections_315"],
    } for row in rolls]
    window_checks=[{
        "size_mm":row["mesh_mm"],"key_stiffness_multiplier":row.get("key_stiffness_multiplier",1.),
        "opening_with_seating_300_mm":max(r["states"]["300"]["opening_with_seating_mm"]
                                        for r in row["cases"].values()),
        "cheek_FKM":min(r["safety"]["cast_cheek"]["FKM"] for r in row["cases"].values()),
        "cheek_static":min(r["safety"]["cast_cheek"]["static_factor"] for r in row["cases"].values()),
        "casting_volume_mm3":row["body_volumes_mm3"]["open_casting"],
        "all_bearing_reaction_signs_valid":all(r["bearing_reaction_signs_valid"] for r in row["cases"].values()),
        "force_balance_fraction":max(s["force_balance_fraction"]
                                     for r in row["cases"].values() for s in r["states"].values()),
        "max_upper_land_mean_300_MPa":max(
            2*max(r["states"]["300"]["spring_reactions_N"][-2:]) /
            ((STATIONS["front"]["key_width_mm"]-10)*(LOCK_UPPER_Y_MM[1]-LOCK_UPPER_Y_MM[0]-10))
            for r in row["cases"].values()),
    } for row in (windows+key_sensitivity)]
    normal_window_checks=window_checks[:len(windows)]
    window_edge=[dict(size_mm=r["mesh_mm"], x_min_mm=200.,
                      FKM=min(c["safety"]["cast_front_cut"]["FKM"] for c in r["cases"].values()),
                      static=min(c["safety"]["cast_front_cut"]["static_factor"] for c in r["cases"].values()))
                 for r in cut_edge_rows]
    convergence=dict(
        roof_FKM=variation([r["normal_case_mid"]["FKM"] for r in roof_checks]),
        roof_opening=variation([r["opening_backing_300_mm"] for r in roof_checks]),
        local_end_FKM=variation([r["FKM"] for r in end]),
        window_FKM=variation([r["cheek_FKM"] for r in normal_window_checks]),
        window_opening=variation([r["opening_with_seating_300_mm"] for r in normal_window_checks]),
        window_cut_edge_FKM=variation([r["FKM"] for r in window_edge]),
    )
    convergence["definition"]="absolute relative change from penultimate to last mesh, requires three meshes"
    return dict(schema_version=SCHEMA,task="T-2.2h",status="STOP",qualified=False,
                load_envelope=loads,short_cases_315=short_cases,shoe=shoe_envelope(),
                roof_proof_normal=governing_normal,roof_proof_friction=governing_friction,
                gate_proof_max_axial=gate_case,axial_stop=[axis_moments(c) for c in (governing_normal,governing_friction)],
                candidate=asdict(g),hand_candidate_radial_only=hand,hand_mass_constrained_search=hand_selection,
                mass=mass,reference_window_mass_trial=frozen_ref,dimensions=dimensions(),
                FEA=dict(roof=roof_checks,window=normal_window_checks,window_key_sensitivity=window_checks[len(windows):],
                         end=end,window_cut_edge=window_edge,convergence=convergence,qualification_status="diagnostic"),
                gates=gates,cycle=dict(reference_s=hydraulic["variants"][hydraulic["selected"]]["reference_cycle_s"],
                                       adverse_s=6.193,adverse_source=source_review))


def design(data):
    g=GEOMETRY
    return {
        "schema_version":SCHEMA,"task":"T-2.2h","status":"STOP","qualified":False,
        "project_basis":["D-GK-12","D-GK-13","D-GK-14","D-OP-16","D-OP-17"],
        "units":{"length":"mm","force":"N","stress":"MPa","mass":"kg"},
        "axes":"X points to gate, Y spans 150 mm width, Z points up, Z 0 at bore centre",
        "working_chamber":{"section_yz_mm":[150.,60.],"roof_x_mm":[205.,295.],
                           "working_corner_R_mm":1.,"window_xy_mm":[200.,150.],
                           "window_x_mm":[5.,205.],"punch_clearance_per_side_mm":.2,
                           "roof_length_mm":90.,"maximum_loaded_length_mm":89.4,
                           "dose_block_setpoint_kg":.853,"dose_upper_tolerance_fraction":.05},
        "ring_trial":{"outer_width_height_mm":[2*g.side_half_mm,2*g.band_half_mm],
                      "outer_corner_R_mm":g.outer_R_mm,"aperture_width_height_mm":[2*g.inner_y_mm,2*g.inner_z_mm],
                      "inner_corner_R_mm":g.inner_R_mm,"lamella_x_intervals_mm":[[205.,250.],[250.,295.]],
                      "lamella_material":"34CrNiMo6+QT","lamella_min_Rp02_Rm_MPa":[800.,1000.],
                      "max_ruling_flat_blank_mm":60.,"see_material_certificate":"EN 10204 3.1",
                      "liners":{"top_and_floor_working_abs_Z_mm":30.,"replaceable_thickness_mm":12.,
                                "wear_strip_y_mm":[-75.,75.],"working_width_mm":150.,
                                "full_flat_backing_seat_y_mm":[-75.,75.],
                                "bedding_abs_Z_mm":g.inner_z_mm,"stiff_backing_beyond_wear_strip_mm":g.inner_z_mm-42.,
                                "side_seat_abs_Y_mm":g.inner_y_mm,
                                "side_seat_z_mm":[-(g.inner_z_mm-g.inner_R_mm),g.inner_z_mm-g.inner_R_mm],
                                "contact_qualification":"open"},
                      "axial_stop":{"rails_x_mm":[295.,349.],"rails_abs_y_mm":list(RAIL_ABS_Y_MM),
                                    "rails_z_mm":list(RAIL_Z_MM),"through_path":"rails to X=349 and front traverse",
                                    "bearing_axis":"X","end_contact_and_seam_qualification":"open",
                                    "force_and_moment_cases":data["axial_stop"]},
                      "machined_slide_gate_wing_relief":{"location":"roof end, across the swept blade height",
                                                         "start_abs_Y_mm":77.5,"blend_to_zero_abs_Y_mm":164.,
                                                         "nominal_roof_end_X_mm":295.,
                                                         "nominal_target_gap_mm":.65,
                                                         "source":"calc/T-2.2h/fea/ring.py"}},
        "window_trial":{"body_x_mm":[-4.,205.],"working_floor_z_mm":-30.,
                        "floor_cast_half_width_mm":109.,"sidewall_abs_y_mm":[75.,106.],
                        "floor_depth_rear_front_mm":[45.,100.],"floor_taper_x_mm":[90.,126.],
                        "material":"G35CrNiMo6-6+QT1","minimum_Rp02_Rm_MPa":[650.,800.],
                        "front_gusset":{"X_mm":[183.8,205.],"abs_Y_mm":[110.,155.],"Z_mm":[-115.,60.],
                                        "fillet_R_mm":15.},
                        "shoe_working_x_mm":[5.2,204.8],"shoe_width_mm":149.6,"shoe_depth_mm":74.,
                        "shoe_max_abs_Y_mm":SHOE_ABS_Y_MAX_MM,
                        "station_geometry":STATIONS,"key_closed_abs_y_mm":list(KEY_CLOSED_Y_MM),
                        "key_park_abs_y_mm":[136.,300.],"upper_seat_abs_y_mm":list(LOCK_UPPER_Y_MM),
                        "lower_seat_abs_y_mm":list(LOCK_LOWER_Y_MM),"cam_and_release":KEY_CAM},
        "loads":{"shoe_300_315_bar_N":[data["shoe"]["shoe_300_bar_N"],data["shoe"]["shoe_315_bar_N"]],
                 "transfer_N":data["shoe"]["transfer_axial_force_N"],
                 "transverse_roof_eccentricity_mm":ECCENTRICITY_MM,
                 "proof_roof_normal_N":data["roof_proof_normal"]["roof"]["normal_force_N"],
                 "proof_friction_envelope_N":data["roof_proof_friction"]["wall_friction_N"],
                 "parameters_K":[.35,.60],"parameters_mu":[.2,.3],
                 "analysis_steps_bar":[0,100,200,300,315]},
        "interfaces":data["dimensions"],
        "machine_before_station_kg":data["mass"]["machine_with_H2_kg"],
        "reference_sources":"calc/T-2.2h/sources.yaml",
        "analysis_results":"calc/T-2.2h/results.json",
        "open_items":["C3D10 assembly with compression contacts and actual lamella joint",
                      "joint and rail connections and station mass after redesign",
                      "window stiffness and cast cheek fatigue",
                      "confirmed production tolerances and swept volumes"],
    }


def metrics(data):
    roof=data["FEA"]["roof"][-1] if data["FEA"]["roof"] else {}
    win=data["FEA"]["window"][-1] if data["FEA"]["window"] else {}
    end=data["FEA"]["end"][-1] if data["FEA"]["end"] else {}
    edge=data["FEA"]["window_cut_edge"][-1] if data["FEA"]["window_cut_edge"] else {}
    cheek_fkm=[x for x in (win.get("cheek_FKM"),edge.get("FKM")) if x is not None]
    cheek_static=[x for x in (win.get("cheek_static"),edge.get("static")) if x is not None]
    return dict(
        task="T-2.2h",status="STOP",qualified=False,
        face_pressure_MPa=data["gates"]["G-PFACE"]["value"],main_installed_stroke_mm=396.,
        main_working_stroke_mm=371.,dose_setpoint_kg=.853,roof_length_mm=90.,
        shoe_300_bar_N=data["shoe"]["shoe_300_bar_N"],shoe_315_bar_N=data["shoe"]["shoe_315_bar_N"],
        dose_transfer_N=data["shoe"]["transfer_axial_force_N"],
        wall_friction_315_bar_K06_mu02_N=data["roof_proof_normal"]["wall_friction_N"],
        wall_friction_315_bar_max_N=data["roof_proof_friction"]["wall_friction_N"],
        hand_candidate_FKM=data["hand_candidate_radial_only"]["FKM"],
        hand_candidate_static=data["hand_candidate_radial_only"]["static_factor"],
        hand_best_in_trial_budget_FKM=max(r["FKM"] for r in data["hand_mass_constrained_search"][:4]),
        roof_diagnostic_mid_FKM=roof.get("normal_case_mid",{}).get("FKM"),
        roof_diagnostic_mid_static=roof.get("normal_case_mid",{}).get("static"),
        roof_diagnostic_backing_opening_mm=roof.get("opening_backing_300_mm"),
        roof_diagnostic_local_end_FKM=end.get("FKM"),
        roof_diagnostic_local_end_static=end.get("static"),
        roof_diagnostic_whole_mesh_end_FKM=roof.get("normal_case_end",{}).get("FKM"),
        window_diagnostic_opening_mm=win.get("opening_with_seating_300_mm"),
        window_diagnostic_cheek_FKM=min(cheek_fkm,default=None),
        window_diagnostic_cut_edge_FKM=edge.get("FKM"),
        window_diagnostic_cheek_static=min(cheek_static,default=None),
        axial_rail_nominal_max_mean_at_300_bar_MPa=data["axial_stop"][-1]["nominal_max_rail_pressure_300_MPa"],
        ejection_cycle_reference_s=data["cycle"]["reference_s"],gate_cycle_s=data["gates"]["G-CYCLE"]["value"],
        trial_ring_and_liner_kg=GEOMETRY.ring_and_liner_mass_kg(),
        trial_replacement_chamber_kg=data["mass"]["chamber_kg"],
        mass_machine_H2_max_before_station_kg=data["mass"]["machine_with_H2_kg"][-1],
        required_station_reduction_H2_max_kg=data["mass"]["station_reduction_kg"][-1],
        maximum_trial_ring_and_liner_kg=data["mass"]["max_ring_and_liner_kg_at_given_window"],
    )


def validate(data):
    nodes,w=np.polynomial.legendre.leggauss(8)
    y_mm=nodes*75.
    p=skew_weight(y_mm,ECCENTRICITY_MM)
    assert np.all(p>0.) and np.isclose(w @ p,2.,atol=1e-13)
    assert np.isclose((w @ (y_mm*p))/(w @ p),ECCENTRICITY_MM,atol=1e-13)
    _,_,_,ri_mm,t_mm,_,_,k_mm_inv,flex,_=section_grid(GEOMETRY,32)
    arc=ri_mm>0
    t,ri,k=t_mm[arc],ri_mm[arc],k_mm_inv[arc]
    stress_inner=E_MPa*(flex[arc,0,1]-flex[arc,1,1]*t/2)/(1-k*t/2)
    kt=abs(stress_inner)/(6/t**2)
    rn_mm=t/np.log1p(t/ri)
    kt_source=t*(rn_mm-ri)/(6*ri*(ri+t/2-rn_mm))
    # Finite-section compliance and the hand formula use independent
    # numerical and closed-form integrations of the same stress relation.
    kt_max_abs_error=float(max(abs(kt-kt_source)))
    assert kt_max_abs_error<1e-6
    axial_error_N=max(abs(r["axial_balance_error_N"]) for rows in data["load_envelope"].values() for r in rows)
    assert axial_error_N<1e-6
    equipment_mass_kg=sum(row["mass_kg"] for row in data["mass"]["machine_rows"])
    assert np.isclose(equipment_mass_kg,data["mass"]["machine_with_H2_kg"][-1],rtol=0.,atol=1e-8)
    assert data["gates"]["G-PFACE"]["status"]==data["gates"]["G-DOSE"]["status"]=="PASS"
    assert data["dimensions"]["lock_cut_to_roof_clearance_mm"]>0.
    criteria=sha256((ROOT/"ops/criteria/design_criteria.yaml").read_bytes()).hexdigest()
    assert read_json("gates.t22h.json")["criteria_sha256"]==criteria
    return dict(prescribed_pressure_first_moment_mm=float((w @ (y_mm*p))/(w @ p)),
                maximum_Janssen_force_balance_N=axial_error_N,
                max_inner_fibre_Kt_error_vs_EM14=kt_max_abs_error,
                station_ledger_sum_kg=equipment_mass_kg,
                criteria_sha256=criteria,checks_passed=True)


def main():
    parser=ArgumentParser()
    parser.add_argument("--audit-out", type=Path)
    opts=parser.parse_args()
    data=collect()
    check=validate(data)
    write_json(HERE/"results.json",data)
    output=(ROOT/"design"/"chamber_roof.t22h.yaml")
    output.write_text(yaml.safe_dump(design(data),sort_keys=False,allow_unicode=True,width=106),
                      encoding="utf-8",newline="\n")
    write_json(ROOT/"metrics.json",metrics(data))
    from report import render
    (ROOT/"report.md").write_text(render(data,metrics(data)),encoding="utf-8",newline="\n")
    assert "?" not in (ROOT/"report.md").read_text(encoding="utf-8")
    if opts.audit_out:
        write_json(opts.audit_out,check)
    print("Generated STOP outputs and passed arithmetic checks.")


if __name__=="__main__":
    main()

