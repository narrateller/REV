"""Generate the deterministic engineering package for the T-2.2g worktree."""

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json

import yaml

from hand import cassette_hand, candidate, choose, key_cam_screen
from layout import (CROWN_MM, EDGE_R_MM, FLOOR_SKIN_DEPTH_MM, FLOOR_TAPER_X_MM,
                    KEY_CLOSED_Y_MM, LOCK_LOWER_Y_MM, LOCK_UPPER_Y_MM, LOWER_RETURN_START_Y_MM,
                    REAR_FLOOR_DEPTH_MM, SHOE_ABS_Y_MAX_MM, STATIONS,
                    WEAR_LAND_DEPTH_MM, WINDOW_FLOOR_ABS_Y_MM, WINDOW_REAR_X_MM,
                    WINDOW_SIDEWALL_ABS_Y_MM, interface)
from loads import ROOT, final_envelopes, read_json, read_yaml, shoe_envelope
from mass import budget, DENSITY_KG_MM3


HERE = Path(__file__).resolve().parent
FEA = HERE / "fea"
FINAL_FEA = ("ring_three_meshes", "ring_screen_r1", "ring_screen_r15", "ring_screen_liner",
             "ring_screen_r22_elastic", "ring_screen_mass_limit", "ring_screen_saddles",
             "lamella_screen", "window_screen", "window_reinforced", "key_contact", "key_proof",
             "r2_aligned_t22g_replay_0", "r2_aligned_t22g_replay_1", "r2_aligned_t22g_replay_2",
             "r2_aligned_t22g_iterative_replay_2")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2,sort_keys=True)+"\n",
                    encoding="utf-8",newline="\n")


def stamp(file):
    return sha256(file.read_bytes()).hexdigest()


def maximum_error(steps):
    points = list(steps)
    if len(points)<2:
        return None
    return max(abs(earlier-later)/abs(later) for earlier,later in zip(points,points[1:])
               if abs(later)>1e-12)


def ring_reduction(records):
    summary = []
    for data in records:
        rr = {"mesh_mm":data["mesh_mm"], "nodes":data["nodes"], "elements":data["elements"],
              "bore_corner_R_mm":data["bore_corner_R_mm"], "volume_mm3":data["analysis_solid_volume_mm3"],
              "ring_mass_kg":data["analysis_solid_volume_mm3"]*DENSITY_KG_MM3,
              "layout":data["layout"], "mesh_jacobians":data.get("mesh_jacobians"),"cases":{}}
        for label,case in data["cases"].items():
            proof,cycle = case["states"]["315"],case["states"].get("300")
            rr["cases"][label] = {"vm_315_MPa":proof["VM_max_off_ends_MPa"],
                "min_static_factor":700./proof["VM_max_off_ends_MPa"],
                "invariant_max_315_MPa":max(proof["VM_fixed_MPa"]),
                "VM_off_ends_xyz_mm":proof["VM_max_off_ends_point_mm"],
                "opening_300_mm":cycle["opening_mm"] if cycle else None,
                "maximum_balance_fraction":max(s["force_balance_fraction"] for s in case["states"].values()),
                "steps_bar":[int(p) for p in case["states"]],
                "membrane_sections_315":case.get("membrane_sections_315"),
                "fatigue":case.get("fatigue")}
        summary.append(rr)
    return summary


def window_reduction(data):
    if not data:
        return None
    return [{"mesh_mm":row["mesh_mm"],"elements":row["elements"],
             "nodes":row["nodes"],"body_volumes_mm3":row["body_volumes_mm3"],
             "regional_check":{k:v.get("safety") for k,v in row["cases"].items()},
             "bearing_reaction_signs_valid":all(v.get("bearing_reaction_signs_valid",False)
                                                  for v in row["cases"].values()),
             "maximum_opening_300_mm":max(v["states"]["300"]["opening_with_seating_mm"] for v in row["cases"].values()),
             "cases":row["cases"]} for row in data]


def cassette_reduction(data, file_name):
    if not data:
        return None
    return {"file":f"calc/T-2.2g/fea/{file_name}.json", "mesh_level":data["level"], "nodes":data["nodes"], "elements":data["elements"],
            "near_mesh_size_mm":(7.5,5.8,4.6)[data["level"]], "contact_mode":data["contact_mode"], "loads":data["loads"],
            "strength":{k:{"static_factor":v["static_factor"],"FKM":v["fatigue_factor"]}
                        for k,v in data["regions"].items() if k in ("blade","seat","cast","cast_R20")},
            "static_contact_screens_MPa":{"blade_seat":480.,"seat_cast":390.},
            "static_screen_pass":all(data["loads"]["static"][k]["peak_MPa"]<=screen
                                     for k,screen in {"blade_seat":480.,"seat_cast":390.}.items())}


def measured_mass(layout, ring_report, window_report=None):
    rows={"closed_roof_ring":ring_report["ring_mass_kg"]}
    if window_report:
        volumes = window_report["body_volumes_mm3"]
        base=budget(layout)
        for name in base["chamber_rows"]:
            if name in ("window_bottom","window_guides","shoe_window_plate","shoe_wings") or (
                name.endswith(("transverse_bridge","cheek_legs","cheek_cap","key_lower_return"))):
                rows[name] = 0.
        rows.update({name:volumes[name]*DENSITY_KG_MM3 for name in volumes})
    return budget(layout,rows)


def calculate():
    selected,roof_case,search = choose()
    if selected is None:
        raise RuntimeError("The manual design screen no longer produces a candidate")
    hand_result = candidate(selected,roof_case)
    hand_result["lock"]["cam_screen"] = key_cam_screen()
    all_load = final_envelopes()
    loaded_shoe = shoe_envelope()
    relevant=read_json("calc/T-2.6/results.json")
    cycle=relevant["variants"][relevant["selected"]]
    cases={}
    for stem in FINAL_FEA:
        path=FEA/f"{stem}.json"
        if path.is_file():
            cases[stem]=read(path)
    ring = {k:ring_reduction(v) for k,v in cases.items() if k.startswith("ring_")}
    final_ring = ring.get("ring_three_meshes", [])
    main = final_ring[-1] if final_ring else None
    window = {k:window_reduction(v) for k,v in cases.items() if k.startswith("window_")}
    background = window.get("window_screen",[])
    reinforced = window.get("window_reinforced",[])
    cast = max((c for c in search if c["material"]=="cast" and c["delta_chamber_kg"]<=60.),
               key=lambda d:(d["FKM"],-d["chamber_kg"]))
    main_long = main["cases"]["long_skew"] if main else None
    cassette_names = [f"r2_aligned_t22g_replay_{level}" for level in (0,1,2)]
    if "r2_aligned_t22g_iterative_replay_2" in cases:
        cassette_names[-1] = "r2_aligned_t22g_iterative_replay_2"
    cassette_rows = [cassette_reduction(cases[name],name) for name in cassette_names if name in cases]
    cassette_steps = {face:maximum_error([v["loads"]["static"][face]["peak_MPa"] for v in cassette_rows])
                      for face in ("blade_seat","seat_cast")}
    convergence = None
    if len(final_ring) == 3:
        cc = [d["cases"]["long_skew"] for d in final_ring]
        raw = cases["ring_three_meshes"]
        gauges = [c["cases"]["long_skew"]["states"]["315"]["VM_fixed_MPa"] for c in raw]
        controlling = max(range(len(gauges[-1])),key=lambda i:gauges[-1][i])
        convergence = {
            "controlling_invariant_gauge_xyz_mm":raw[-1]["stress_gauges_xyz_mm"][controlling],
            "invariant_gauge_VM_MPa": [g[controlling] for g in gauges],
            "invariant_gauge_relative_change":maximum_error([g[controlling] for g in gauges]),
            "moving_region_max_relative_change":maximum_error([c["vm_315_MPa"] for c in cc]),
            "opening_relative_change":maximum_error([c["opening_300_mm"] for c in cc]),
            "FKM_relative_change":maximum_error([c["fatigue"]["FKM"] for c in cc]),
        }
        convergence["invariant_and_opening_lt_5_pct"] = max(convergence["invariant_gauge_relative_change"],
                         convergence["opening_relative_change"])<.05
    actual_mass = measured_mass(selected,main,background[-1] if background else None) if main else None
    enhanced_mass = measured_mass(selected,main,reinforced[-1]) if main and reinforced else None
    failed_case_paths = sorted(FEA.glob("*_failure.json"))
    branch = {
        "nominal_reference_s":cycle["reference_cycle_s"],
        "adverse_reference_s":relevant["selected_sensitivity"]["combined"]["reference_cycle_s"],
        "nominal_throughput_kg_h":cycle["throughput_kg_h"],
        "basis":"D-GK-13 / D-OP-16 — T-2.6 reference",
    }
    gates = {g["id"]:{"status":g["status"],"value":g["value"],"unit":g["unit"]}
             for g in read(ROOT/"gates.t22g.json")["gates"]}
    summary = {
        "gates":gates,
        "status":"STOP_FEA" if main and (main_long["min_static_factor"]<1.5 or main_long["fatigue"]["FKM"]<1.) else "HOLD",
        "hand":hand_result,"cast_best":cast,"hand_search":search,"roof_proof_case":roof_case,"loads":all_load,
        "prepress":loaded_shoe,"cycle":branch,"cassette_hand":cassette_hand(),
        "fea":{"ring":ring,"window":window,"lamella":cases.get("lamella_screen"),
                              "cassette":cassette_rows[-1] if cassette_rows else None,
               "cassette_meshes":cassette_rows,"cassette_peak_relative_changes":cassette_steps,
               "key_contact":cases.get("key_contact"),"key_proof":cases.get("key_proof"),
               "failed_trials":[{"file":f"fea/{p.name}", "result":read(p)} for p in failed_case_paths],
               "ring_convergence":convergence,
               "files":{stem:{"path":f"fea/{stem}.json","sha256":stamp(FEA/f"{stem}.json")}
                        for stem in sorted(cases)}},
        "mass_close_to_strength_limit":actual_mass,"mass_with_window_reinforcement":enhanced_mass,
        "sources":"calc/T-2.2g/sources.yaml",
    }
    return summary,design(selected,summary),metrics(summary)


def design(layout, data):
    inputs = interface(layout)
    force_315 = data["roof_proof_case"]
    bars = (0,100,200,300,315)
    stage_forces = {str(p):force_315["main_force_N"]*p/315. for p in bars}
    material = read_yaml("calc/T-2.2g/sources.yaml")["materials"]
    lock = data["hand"]["lock"]
    cassette = read_yaml("design/slide_gate.t17d.yaml")["bearing_pair"]
    return {
        "schema_version":1,"task":"T-2.2g","status":data["status"],"qualified":False,
        "project_basis":["D-GK-05","D-GK-11","D-GK-12","D-GK-13","D-OP-16"],
        "fixed_working_roof_length_mm":90.,"working_section_yz_mm":[150.,60.],
        "loading":{
            "js_formula":"F(x)=F0*exp(-K*mu*P/A*(x-x_punch)); p_lat=K*F(x)/A",
            "closure_long_length_mm":89.4,"section_area_mm2":9000.,"wall_perimeter_mm":420.,
            "K_range":[.35,.60],"mu_range":[.20,.30],"analysis_steps_bar":list(bars),
            "main_force_T26_eta_by_bar_N":stage_forces,
            "main_force_project_315_N":1785000.,
            "roof_long_proof_load":force_315,
            "transition_max_shoe_proof_load":data["prepress"]["controlling_case"],
            "roof_long_peak_pressure_MPa":force_315["roof"]["inlet_MPa"],
            "roof_long_315_normal_force_N":force_315["roof"]["normal_force_N"],
            "wall_long_315_friction_N":force_315["wall_friction_N"],
            "gate_max_315_thrust_N":data["cassette_hand"]["max_axial_Janssen_315_N"],
            "prepress_shoe_300_N":data["prepress"]["shoe_300_bar_N"],
            "prepress_shoe_315_N":data["prepress"]["shoe_315_bar_N"],
            "transfer_advance_N":data["prepress"]["transfer_axial_force_N"],
            "blocking_dose_setpoint_kg":.853,"dose_setpoint_upper_tolerance_fraction":.05,
            "x_earlier_proof_centroid_mm":165.2,"roof_proof_transverse_eccentricity_mm":27.72,
        },
        "reference_layout_for_manual_screen":layout.data(),
        "roof_and_floor_trial":{
            "outer_working_band_span_mm":layout.roof_width_mm, "roof_wall_mm":layout.roof_wall_mm,
            "roof_and_floor_section_depth_mm":[layout.roof_band_mm,layout.floor_band_mm],
            "integral_closed_ring":True,"roof_axis_interval_x_mm":[205.,295.],
            "root_radius_R_mm":15.,"working_bore_corner_R_mm":1.,
            "material":material["forging"],"forging_mass_depth_axis_mm":90.,
            "alternate_cast_material":material["casting"],"cast_trial_minimum_wall_mm":64.,
            "structural_variant_series":{name:{"mesh_file":f"calc/T-2.2g/fea/{name}.json",
                                  "layout":rows[-1]["layout"],"internal_root_radius_mm":rows[-1]["bore_corner_R_mm"]}
                                 for name,rows in data["fea"]["ring"].items() if rows},
            "receiver_trial_bore_yz_mm":[174.,84.],
            "receiver_trial_nominal_radial_liner_mm":12.,
            "receiver_contact_scheme":"Four separate backed strips, with a relief off each inside structural corner.",
            "no_welding_in_force_path":True,
        },
        "open_window_casting":{
            "material":material["casting"], "bottom_x_mm":[WINDOW_REAR_X_MM,205.],
            "window_x_mm":[5.,205.],"window_width_mm":150., "floor_top_z_mm":-30.,
            "rear_floor_depth_mm":REAR_FLOOR_DEPTH_MM,"forward_floor_depth_mm":FLOOR_SKIN_DEPTH_MM,
            "floor_transition_x_mm":list(FLOOR_TAPER_X_MM),"floor_body_width_mm":2*WINDOW_FLOOR_ABS_Y_MM,
            "sidewall_abs_y_mm":[75.,WINDOW_SIDEWALL_ABS_Y_MM],"sidewall_z_mm":[-30.,30.],
            "front_shoulder_x_mm":205.,"lower_fitted_shoulders_abs_y_mm":[82.,109.],
            "lower_fitted_shoulders_z_mm":[-70.,-40.],
            "attachment_status":"Boundary and transverse keys require assembly verification.",
        },
        "shoe_lock":{
            "mechanism":"Four captive sliding keys, in two cam-driven left/right pairs. Upper and lower strips hold each key against overturning.",
            "material_keys":"34CrNiMo6+QT, подтверждение R_p0,2/R_m 800/1000 МПа в плоской заготовке",
            "pulsating_contact_screen_without_surface_hardness_credit_MPa":70.,
            "material_shoe":"34CrNiMo6+QT, 700/900 MPa at the governing flat section",
            "shoe_face_x_mm":[5.2,204.8],"shoe_working_width_mm":149.6,
            "shoe_depth_mm":layout.shoe_depth_mm,"shoe_wing_abs_y_mm":SHOE_ABS_Y_MAX_MM,
            "key_geometry_by_station":STATIONS,"key_closed_abs_y_mm":list(KEY_CLOSED_Y_MM),
            "key_park_abs_y_mm":inputs["key_park_abs_y_mm"],"upper_forged_land_abs_y_mm":list(LOCK_UPPER_Y_MM),
            "lower_forged_land_abs_y_mm":list(LOCK_LOWER_Y_MM),"lower_cast_return_start_abs_y_mm":LOWER_RETURN_START_Y_MM,
            "lower_rear_heel_z_mm":29.98,"wear_land_depth_mm":WEAR_LAND_DEPTH_MM,"wear_land_radius_R_mm":EDGE_R_MM,
            "wear_land_crown_mm":CROWN_MM,"capacity_and_stroke":lock["cam_screen"],
            "front_peak_side_N":lock["stations"]["front"]["peak_side_315_N"],
            "rear_reverse_reaction_N":lock["stations"]["rear"]["minimum_signed_reaction_315_N"],
            "cam_status":"Prove timing and K-drive force with an unloaded lock under T-2.6 hydraulic interlocks.",
            "service_logic":"Unlock only below the residual-load limit and after punch clearance; verify both lateral positions. No weld carries operating force.",
        },
        "interfaces":inputs,
        "cassette":{
            "geometry_yzx_R_mm":cassette["dimensions_mm_R"],"passage_yz_R_mm":cassette["bore_mm_R"],
            "lower_land_mm":cassette["lower_land_width_mm"],
            "material":"34CrNiMo6+QT, 800/1000 MPa; selectively hardened bearing tracks only on the cassette",
            "cassette_surface_HRC":cassette["surface_HRC"],"cassette_SHD_min_mm":cassette["SHD_min_mm"],
            "plate_hardening":"QT only; optional nitriding under D-GK-05",
            "seat_Rz_um":cassette["roughness_Rz_max_um"],"static_pressure_screens_MPa":[480.,390.],
            "system_axial_load_path":"Blade to cassette, machined casting pocket, chamber traverse and four PRELOAD columns.",
        },
        "analytical_artifacts":{
            "load_code":"calc/T-2.2g/loads.py","ring_geometry_code":"calc/T-2.2g/fea/ring.py",
            "window_geometry_code":"calc/T-2.2g/fea/window_geometry.py",
            "hand_and_mass_code":["calc/T-2.2g/hand.py","calc/T-2.2g/mass.py"],
        },
        "sources":"calc/T-2.2g/sources.yaml",
    }


def metrics(data):
    hand=data["hand"]
    ring=data["fea"]["ring"].get("ring_three_meshes",[])
    control=ring[-1]["cases"]["long_skew"] if ring else None
    window=data["fea"]["window"].get("window_screen",[])
    reinforced=data["fea"]["window"].get("window_reinforced",[])
    cassette=data["fea"]["cassette"]
    key_probe=data["fea"]["key_proof"]
    proof=key_probe["rows"][-1] if key_probe else None
    mass=data["mass_close_to_strength_limit"]
    branch=data["cycle"]
    return {
        "task":"T-2.2g","status":data["status"],"G_PFACE_MPa":data["gates"]["G-PFACE"]["value"],
        "installed_main_stroke_mm":396.,"working_main_stroke_mm":371.,"fixed_roof_mm":90.,
        "prepress_300_force_N":data["prepress"]["shoe_300_bar_N"],
        "prepress_315_force_N":data["prepress"]["shoe_315_bar_N"],
        "dose_transfer_force_N":data["prepress"]["transfer_axial_force_N"],
        "dose_blocking_kg":data["prepress"]["transfer_design_dose_setpoint_kg"],
        "roof_pressure_max_MPa":data["roof_proof_case"]["roof"]["inlet_MPa"],
        "gate_thrust_315_N":data["cassette_hand"]["max_axial_Janssen_315_N"],
        "hand_static_factor":hand["manual_margin"]["static_factor"],"hand_FKM":hand["manual_margin"]["FKM"],
        "hand_opening_300_mm":hand["manual_margin"]["opening_300_mm"],
        "roof_FEA_static_factor":control["min_static_factor"] if control else None,
        "roof_FEA_FKM":control["fatigue"]["FKM"] if control else None,
        "roof_FEA_opening_300_mm":control["opening_300_mm"] if control else None,
        "open_window_FEA_opening_300_mm":window[-1]["maximum_opening_300_mm"] if window else None,
        "open_window_reinforced_FEA_opening_300_mm":reinforced[-1]["maximum_opening_300_mm"] if reinforced else None,
        "cassette_peak_315_MPa":[cassette["loads"]["static"][k]["peak_MPa"] for k in ("blade_seat","seat_cast")] if cassette else None,
        "prepress_key_probe_force_N":proof["shoe_force_N"] if proof else None,
        "prepress_key_probe_peak_MPa":max(v["peak_MPa"] for v in proof["contact"].values()) if proof else None,
        "hand_node_kg":hand["mass"]["chamber_kg"],"hand_delta_node_kg":hand["mass"]["delta_chamber_kg"],
        "hand_station_reduction_kg":hand["mass"]["station_reduction_kg"],
        "FEA_variant_node_kg":mass["chamber_kg"] if mass else None,
        "FEA_variant_delta_node_kg":mass["delta_chamber_kg"] if mass else None,
        "machine_before_station_reduction_kg":mass["machine_with_H2_kg"] if mass else None,
        "required_station_reduction_kg":mass["station_reduction_kg"] if mass else None,
        "hydraulics_delta_kg":hand["mass"]["hydraulic_delta_kg"],
        "reference_nominal_cycle_s":branch["nominal_reference_s"],
        "reference_adverse_cycle_s":branch["adverse_reference_s"],
    }


def main():
    parser=ArgumentParser()
    parser.add_argument("--outroot",type=Path,default=ROOT)
    args=parser.parse_args()
    result,layout,indicators=calculate()
    root=args.outroot
    (root/"calc/T-2.2g").mkdir(parents=True,exist_ok=True)
    (root/"design").mkdir(parents=True,exist_ok=True)
    write_json(root/"calc/T-2.2g/results.json",result)
    write_json(root/"metrics.json",indicators)
    (root/"design/chamber_roof.t22g.yaml").write_text(
        yaml.safe_dump(layout,allow_unicode=True,sort_keys=False,width=105),encoding="utf-8",newline="\n")


if __name__=="__main__":
    main()

