"""Rebuild the trial geometry, qualification evidence and metrics."""
from math import cos, pi, sin

import yaml

from hand import HERE, ROOT, SHARES, frame_data, json_read, json_write, run as run_hand
from mass import (
    B_POST_Z_MM, HYDRAULIC_TOOL_PROJECTION_MM, LOCK_B_X_MM, LOCK_B_Y_END_MM,
    LOCK_B_Y_MID_MM, LOCK_B_Z_MM, LOCK_PLAN_RIGHT_MM, PORTAL_HEIGHT_MM,
    PORTAL_X_MM, POST_X_MM, TIE_CLEAR_D_MM, TIE_Y_MM, b_housing_boxes,
    study as mass_study,
)
from vdi import study_fasten

FEA = HERE/"fea"
YOKE_NOMINAL_MM = [B_POST_Z_MM[1], B_POST_Z_MM[1]+PORTAL_HEIGHT_MM]
CONTACT_LIMITS = {"LOW": 360., "FRONT": 420., "BACK": 420.}


def check_inputs():
    originals = {
        "chamber_lateral.t22.yaml": ROOT/"design/chamber_lateral.t22.yaml",
        "results.t22.json": ROOT/"calc/T-2.2/results.json",
    }
    originals.update({f"lateral_fea/{p.name}": p for p in (ROOT/"calc/T-2.2/lateral_fea").iterdir()})
    for name, original in originals.items():
        assert original.read_bytes() == (HERE/"reference"/name).read_bytes(), name


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def geometry_screen(mass):
    frame = frame_data()
    gate = load_yaml(ROOT/"design/slide_gate.t17d.yaml")
    cyl = load_yaml(ROOT/"design/params.t21.yaml")["precompaction"]["cylinder"]
    old = json_read(ROOT/"calc/T-1.2b/results.json")["mechanical_lock_A"]
    stroke, cam = old["key_slide_mm"], old["cam_extra_pre_cylinder_stroke_mm"]
    lock_mass = mass["b"]["rows_kg"]["two_locks_gross_kg"]/2
    ratio = pi*stroke/(2*cam)
    stem_force = max(2*ratio*sin(pi*i/100)*
        (old["no_load_slide_force_per_key_N"]+
         lock_mass*old["key_peak_acceleration_m_s2"]*abs(cos(pi*i/100)))/
        old["cam_efficiency"] for i in range(101))
    nominal = 162.-(LOCK_B_Y_END_MM[1]+stroke)
    fit = dict(post_machined_position=.10,lock_outside_width=.10,guide_registration=.08,
               end_of_travel=.08,thermal_and_assembly_allowance=.08)
    cut_range = max(x[1] for x in PORTAL_X_MM)-min(x[0] for x in PORTAL_X_MM)
    frame_inboard = frame["columns"]["square_pitch_mm"]/2-frame["columns"]["bore_mm"]/2
    return dict(
        feed_x_mm=[5.,205.],feed_transverse_width_mm=150.,product_section_mm=[150.,60.],
        shoe_box_xyz_mm=[200.,222.,160.],prepress_cylinder_bore_rod_mm=[cyl["bore_mm"],cyl["rod_mm"]],
        cam_stroke_mm=cam,lock_stroke_mm=stroke,
        lock_shoe_unlocked_nominal_clearance_mm=LOCK_B_Y_MID_MM[0]+stroke-111.,
        lock_post_swept_nominal_clearance_mm=nominal,
        lock_post_tolerance_budget_terms_mm=fit,lock_post_tolerance_total_mm=sum(fit.values()),
        lock_post_worst_case_mm=nominal-sum(fit.values()),lock_post_worst_case_required_mm=.50,
        front_yoke_x_to_window_nominal_clearance_mm=PORTAL_X_MM[1][0]-205.,
        guide_to_punch_mm=frame["interfaces"]["layout"]["guide_to_punch_lever_mm"],
        guide_base_note=frame["interfaces"]["guide_reference_plane"],
        frame_inboard_bore_y_mm=frame_inboard,sleeve_to_frame_transverse_screen_mm=frame_inboard-216.,
        fixed_structure_to_gate_back_x_mm=gate["back_x_mm"]-max(x[1] for x in POST_X_MM),
        gate_swept_top_in_chamber_z_mm=gate["swept_plate_vertical_limits_mm"][1]-30.,
        lock_gate_vertical_nominal_clearance_mm=LOCK_B_Z_MM[0]-(gate["swept_plate_vertical_limits_mm"][1]-30.),
        required_length_to_cover_both_yoke_strips_mm=cut_range,
        lock_full_length_mm=LOCK_B_X_MM[1]-LOCK_B_X_MM[0],
        grip_endpoint_shortening_before_touching_nominal_yoke_footprint_mm=2.,
        maximum_cam_stem_force_N=stem_force,
        cylinder_pressure_for_cam_force_bar=10*stem_force/(pi/4*cyl["bore_mm"]**2*cyl["eta"]),
        tolerance_basis="Assigned screening budgets; verify inspection and as-built guides at unloading.",
        layout_basis="Scalar separations with T-1.7d. z of shiber geometry transformed by -30 mm. "
                     "Complete mounting, feed and tools require integrated envelopes.",
    )


def case_files(pattern):
    return {path.stem:json_read(path) for path in sorted(FEA.glob(pattern))}


def convergence(cases):
    result = {}
    for share in SHARES:
        runs = [cases.get(f"portal_{level}_{100*share:.0f}") for level in range(3)]
        row = dict(solved_levels=sum(run is not None for run in runs),status="INCOMPLETE")
        if all(runs):
            series = {}
            for name, summary in runs[0]["parts"].items():
                if "inboard_gauges" in summary:
                    for key in ("static_MPa","fatigue_factor_n_sigma_1"):
                        series[f"{name}.inboard.{key}"] = [
                            run["parts"][name]["inboard_gauges"][key] for run in runs]
            for pair in runs[0]["contact"]:
                for key in ("inboard_gauge_pressure_MPa","mean_pressure_active_area_MPa"):
                    if all(run["contact"][pair].get(key) is not None for run in runs):
                        series[f"{pair}.{key}"] = [run["contact"][pair][key] for run in runs]
            for axis in ("height","width"):
                if all("paired_section_300_bar" in run for run in runs):
                    series[f"briquette.{axis}_mm"] = [
                        run["paired_section_300_bar"][axis]["change_from_design_at_300_mm"] for run in runs]
            changes = {name:max(abs(b-a)/max(abs(b),1e-12) for a,b in zip(points,points[1:]))
                       for name,points in series.items()}
            governing = max(changes, key=changes.get) if changes else None
            maximum = changes[governing] if governing else None
            row.update(series=series, relative_changes=changes, governing=governing,
                       max_relative_change=maximum, status=("INCOMPLETE" if maximum is None else
                                                           "PASS" if maximum<.05 else "FAIL"))
        result[str(share)] = row
    return result


def qualification(cases, conv, vdi):
    reports = [case for case in cases.values() if "paired_section_300_bar" in case]
    return dict(
        solver_reached_315_bar=bool(reports),
        three_mesh_convergence=all(row["status"] == "PASS" for row in conv.values()),
        force_balance_pass=bool(reports) and all(
            max(case["global_force_balance_fraction"],case["shoe_force_balance_fraction"]) <= .001
            for case in reports),
        weak_spring_force_pass=bool(reports) and all(case["stabilizer_load_fraction"] < .001 for case in reports),
        upper_and_lower_joint_qualified=all(r["status"]=="PASS" for r in vdi.values()),
        contact_pass=bool(reports) and all(s["inboard_gauge_pressure_MPa"] is not None and
            s["inboard_gauge_pressure_MPa"] <= CONTACT_LIMITS[next(k for k in CONTACT_LIMITS if pair.endswith(k))]
            for case in reports for pair,s in case["contact"].items()),
        product_height_pass_diagnostic=bool(reports) and all(
            abs(case["paired_section_300_bar"]["height"]["change_from_design_at_300_mm"]) <= 1. for case in reports),
        product_width_pass_diagnostic=bool(reports) and all(
            abs(case["paired_section_300_bar"]["width"]["change_from_design_at_300_mm"]) <= 1. for case in reports),
        structural_criteria_qualified=False,
        reason="Excessive work contact, height and VDI closure/fatigue. Stress peaks and contact are not mesh-qualified.",
    )


def effective_load_lines(case):
    if not case:
        return {}
    result = {}
    for pair, contact in case["contact"].items():
        fx,fy,fz = contact["force_cases"][2]["vector_N"]
        mx,my,_ = contact["force_cases"][2]["moment_Nmm"]
        z_ref = 160. if pair.endswith("LOW") else YOKE_NOMINAL_MM[0]
        result[pair] = dict(
            x_mm=(z_ref*fx-my)/fz,y_mm=(mx+z_ref*fy)/fz,
            vertical_component_N=fz,reference_z_mm=z_ref)
    return result


def write_yaml(path, value):
    path.write_text(yaml.safe_dump(value,sort_keys=False,allow_unicode=True,width=110),
                    encoding="utf-8",newline="\n")


def assemble():
    check_inputs()
    hand = run_hand()
    mass = mass_study()
    json_write(HERE/"mass.json",mass)
    cases = case_files("portal_[012]_[06][04].json")
    geom = geometry_screen(mass)
    ref = hand["b"]["0.64"]
    finest = next((cases[f"portal_{i}_64"] for i in (2,1,0) if f"portal_{i}_64" in cases),None)
    vdi = study_fasten(hand["load"],finest)
    conv = convergence(cases)
    assessment = qualification(cases,conv,vdi)
    status = "HOLD"
    result = dict(task="T-2.2b",round=2,status=status,execution_selected_by_GK="b",
                  hand=hand,mass=mass,kinematic_screen=geom,VDI_2230=vdi,
                  qualification=assessment,fea=dict(cases=cases,convergence=conv,
                  penalty_sensitivity=case_files("penalty_*_portal_?_64.json"),
                  effective_contact_lines_finest_64_36=effective_load_lines(finest),
                  attempts=json_read(FEA/"attempts.json")))
    selected = dict(
        schema_version=2,task="T-2.2b",round=2,status=status,qualified_for_CAD=False,
        execution_selected_by_GK="b",decisions=["D1","D-GK-07","D-GK-05","D-OP-10"],
        hold_reasons=[
            "Превышен экран смятия на заплечике и под передним ярмом вдали от кромок.",
            "Раскрытие по высоте при 300 бар превышает допуск 1 мм в расчётной области.",
            "Расчёт эксцентриситета показывает раскрытие стыка стойка–ярмо. КЭ-модель с TIE диагностическая.",
            "Усталость резьбы и давление под исходным седлом выходят за критерии. Нижний анкер и инструмент требуют квалификации.",
            "Локальные напряжения и контакт меняются между сетками более чем на 5 %."],
        axes=dict(x="Ось прессования, окно x=5–205 мм",y="Поперёк камеры, центр y=0",
                  z="Вверх, рабочая нижняя грань башмака z=0, пол канала z=-60 мм"),
        interfaces=geom,load=hand["load"],
        design=dict(
            body=dict(material="G35CrNiMo6-6+QT1",Rp02_MPa=650,Rm_MPa=800,
                      volume_base_pieces_x0_x1_y0_y1_z0_z1_mm=[list(box) for box in b_housing_boxes()],
                      outer_width_mm=432,post_x_mm=[list(i) for i in POST_X_MM],
                      bore_diameter_mm=TIE_CLEAR_D_MM,post_root_radius_mm=15,
                      fea_die_wall_and_floor_end_x_mm=198),
            shoe=dict(material="34CrNiMo6+QT",Rp02_MPa=600,Rm_MPa=800,
                      x_mm=[5,205],y_mm=[-111,111],z_mm=[0,160],production_face_width_mm=150,
                      core_y_mm=[-75.,75.],shoulder_projection_each_side_mm=36.,
                      shoulder_root_radius_mm=15,contact_edge_radius_mm=5),
            lock=dict(quantity=2,material="34CrNiMo6+QT",Rp02_MPa=700,Rm_MPa=900,
                      x_mm=list(LOCK_B_X_MM),positive_y_mid_mm=list(LOCK_B_Y_MID_MM),
                      positive_y_end_mm=list(LOCK_B_Y_END_MM),z_mm=list(LOCK_B_Z_MM),
                      stroke_mm=geom["lock_stroke_mm"],crown_max_mm=.1,contact_edge_radius_mm=5,
                      idealized_unloaded_z_offset_mm=.025,plan_right_xy_mm=[list(point) for point in LOCK_PLAN_RIGHT_MM]),
            end_yoke=dict(quantity=2,material="34CrNiMo6+QT",Rp02_MPa=700,Rm_MPa=900,
                          x_bearing_strips_mm=[list(i) for i in PORTAL_X_MM],z_mm=YOKE_NOMINAL_MM,
                          y_mm=[-216,216],seat_lug_right_y_mm=[162,216],
                          seat_lug_x_by_end_mm=[list(x) for x in POST_X_MM],
                          tie_clearance_bore_mm=TIE_CLEAR_D_MM,contact_edge_radius_required_mm=5,
                          idealization_contact_master="Flat in FEA; production fillet is unresolved."),
            tie=dict(quantity=4,thread="M39x4",fit="6g/6H",property_class="12.9",forming="SG",
                     y_centres_mm=[-TIE_Y_MM,TIE_Y_MM],x_centres_mm=ref["x_support_mm"],
                     target_preload_after_transfer_N=ref["assembly_preload_N"],
                     smooth_equivalent_area_mm2=976,upper_trial_seat_diameter_mm=66,
                     upper_trial_seat_height_mm=35,trial_clamped_length_mm=510.,
                     nominal_stud_diameter_mm=39.,trial_anchoring_plane_z_mm=B_POST_Z_MM[0],
                     studied_spreader=vdi["R10"], proposed_lower_anchor=vdi["R11"],
                     tooling_screen=vdi["R13"],complete_VDI_2230=False),
        ),
        screening=dict(mass=mass["b"],mass_sensitivity=mass["b_sensitivity"],
            contact_limits_MPa=CONTACT_LIMITS,criteria=assessment,
            contact_mu=.15,lower_seat_mode_in_FEA="Common fixed plane with housing; physical anchor is separate.",
            C_STR_01_required=1.5,C_FAT_01_required=1.,cycles=10000000,
            briquette_dimension_deviation_limit_mm=1.,balance_limit_fraction=.001,
            mesh_change_limit_fraction=.05),
        evidence=dict(results="calc/T-2.2b/results.json",geometry="calc/T-2.2b/fea/portal.geo",
                      cutoff_x_mm=198,pressure_bar=[0,100,200,300,315],sources="calc/T-2.2b/sources.yaml"),
    )
    json_write(HERE/"results.json",result)
    write_yaml(ROOT/"design/chamber_lateral.t22b.yaml",selected)
    gates = json_read(ROOT/"gates.t22b.json")
    study = {}
    if finest and "paired_section_300_bar" in finest:
        parts = [p for name,p in finest["parts"].items() if not name.startswith("ST")]
        thread = [p["fatigue_factor"] for stud in vdi["R9"]["FEA_axial_and_bending_by_section"].values()
                  for p in stud.values()]
        study = dict(element_count=finest["elements"],
            raw_solid_static_factor=min(p["static_factor"] for p in parts),
            raw_solid_fatigue_factor=min(p["fatigue_factor"] for p in parts),
            thread_axial_bending_screen_factor=min(thread),
            mesh_max_relative_change=conv["0.64"].get("max_relative_change"),
            width_change_300_mm=finest["paired_section_300_bar"]["width"]["change_from_design_at_300_mm"],
            height_change_300_mm=finest["paired_section_300_bar"]["height"]["change_from_design_at_300_mm"],
            right_shoe_contact_inboard_MPa=finest["contact"]["RIGHTLOW"]["inboard_gauge_pressure_MPa"],
            right_shoe_contact_mean_MPa=finest["contact"]["RIGHTLOW"]["mean_pressure_active_area_MPa"],
            right_shoe_contact_nodal_peak_MPa=finest["contact"]["RIGHTLOW"]["peak_pressure_MPa"],
            global_balance_fraction=finest["global_force_balance_fraction"],
            shoe_balance_fraction=finest["shoe_force_balance_fraction"],
            max_stabilization_force_fraction=finest["stabilizer_load_fraction"])
    metrics=dict(task="T-2.2b",round=2,status=status,execution="b",
        force_300_N=hand["load"]["force_300_N"],force_315_N=hand["load"]["force_315_N"],
        centroid_x_mm=hand["load"]["centroid_x_mm"],right_lock_315_N=hand["load"]["high_lock_force_315_N"],
        trial_mass_kg=mass["b"]["machine_nominal_kg"],trial_mass_delta_kg=mass["b"]["delta_kg"],
        trial_mass_reserve_kg=mass["b"]["reserve_kg"],trial_mass_with_H2_kg=mass["b"]["machine_with_H2_kg"],
        diagnostic_FEA_64_36=study,solved_contact_jobs=len(cases),
        lock_worst_clearance_mm=geom["lock_post_worst_case_mm"],
        VDI_min_manual_edge_pressure_at_315_MPa=vdi["R2"]["minimum_manual_edge_pressure_MPa"],
        VDI_max_seat_pressure_MPa=vdi["R10"]["original_top_66mm_pressure_MPa"],
        VDI_spreader_mean_pressure_screen_MPa=vdi["R10"]["proposed_projected_average_MPa"],
        machine_mass_with_H2_and_proposed_anchor_kg=[
            mass["base_T22_round_2_kg"]+mass["b_sensitivity"]["package_without_unqualified_savings_delta_kg"]+h2
            for h2 in mass["outstanding_MA_delta_kg"]],
        qualified_C_STR_01=None,qualified_C_FAT_01=None,
        gates={gate["id"]:gate["status"] for gate in gates["gates"]})
    json_write(ROOT/"metrics.json",metrics)


if __name__ == "__main__":
    assemble()
