"""Результаты второго круга из принятого расчёта и протоколов FEA."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARAMS = ROOT / "design/params.t22e.yaml"
DESIGN = ROOT / "design/prepress_lock.t22e.yaml"
FEA = HERE / "fea"

SENSITIVITY_FILE = "r2_closed_flanks.json"
TABLE_NAMES = ("through_ring_light", "closed_flanks_light", "closed_flanks_shoe_priority",
               "closed_flanks_front", "closed_flanks_stiff", "closed_flanks_upper_boundary")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def gates():
    runner = os.environ.get("REV_PYTHON", "E:/Tools/Python313/python.exe")
    command = [runner, "-B", "ops/gates/calc_gates.py", "--params", str(PARAMS.relative_to(ROOT)),
               "--criteria", "ops/criteria/design_criteria.yaml", "--out", "gates.t22e.json"]
    subprocess.run(command, cwd=ROOT, check=True)
    contents = read_json(ROOT / "gates.t22e.json")
    approved = {row["id"]: row["status"] for row in contents["gates"]}
    assert all(approved[g] == "PASS" for g in ("G-PFACE", "G-DOSE", "G-CYCLE"))
    return approved


def spread(rows):
    if len(rows) != 3 or any(value is None for value in rows):
        return None
    return (max(rows) - min(rows)) / abs(rows[-1]) if rows[-1] else None


def sensitivity():
    records = read_json(FEA / SENSITIVITY_FILE)
    summary = []
    for row in records:
        data = {
            "case": row["layout"]["name"], "status": row["status"], "layout": row["layout"],
            "delta_chamber_kg": row.get("mass", {}).get("delta_chamber_kg"),
            "station_to_station_clearance_mm": row["nominal_station_spacing_clearance_mm"],
            "front_to_gate_clearance_mm": row["stations"]["front"]["gate_swept_clearance_mm"],
        }
        if row["status"] == "SOLVED":
            p300 = row["steps"][-2]
            data.update(
                delta_height_300_mm=p300["maximum_height_with_seating_mm"],
                delta_height_at_x165_edge_300_mm=max(p300["centroid_profile_opening_mm"].values()) + .020,
                min_static_at_global_points=row["global_box_static_factor_at_points"],
                min_FKM_at_global_points=row["global_box_FKM_at_points"],
                support_openings=row.get("inactive_supports"),
                smallest_support_300_N=min(s["spring_force_N"] for s in p300["support_steps"].values()),
            )
        summary.append(data)
    return summary


def moment_error(row, step, shoe_proof_force_N):
    pressure = step["pressure_bar"]
    loads = step["support_steps"]
    x_c, y_c = row["load_centroid_xy_mm"]
    support_moment_Nmm = [0., 0.]
    for name, info in loads.items():
        station, side = name.split("_")
        geo = row["stations"][station]
        x = geo["x_mm"] - 105.
        y = (1 if side == "right" else -1) * geo["y_mm"]
        for index, lever in enumerate((x, y)):
            support_moment_Nmm[index] += info["spring_force_N"] * lever
    target_moment_Nmm = [shoe_proof_force_N * pressure / 315. * lever for lever in (x_c - 105., y_c)]
    return max(abs(support-target) / abs(target) for support, target in zip(support_moment_Nmm, target_moment_Nmm))


def global_summary(meshes, shoe_proof_force_N):
    solved = [m for m in meshes if m["status"] == "SOLVED"]
    if not solved:
        return {}, None
    fine = solved[-1]
    height = [m["steps"][-2]["maximum_height_with_seating_mm"] for m in solved]
    centroid = [max(m["steps"][-2]["centroid_profile_opening_mm"].values()) + .020 for m in solved]
    fat = fine["steps"][-2]["global_control_points"]
    proof = fine["steps"][-1]["global_control_points"]
    strength_controls = {
        "proof": min(proof, key=lambda key: -proof[key]["equivalent_MPa"]),
        "working": min(fat, key=lambda key: -fat[key]["range_MPa"]),
    }
    mesh_spreads = {
        key: {"proof_VM": spread([m["steps"][-1]["global_control_points"][key]["equivalent_MPa"] for m in solved]),
              "working_VM_range": spread([m["steps"][-2]["global_control_points"][key]["range_MPa"] for m in solved])}
        for key in proof
    }
    p = fine["steps"][-2]
    report = dict(
        mesh_mm=[row["mesh_mm"] for row in solved],
        nodes=[row["node_count"] for row in solved],
        max_delta_height_300_mm=height[-1],
        max_delta_height_xy_mm=p["peak_opening_xy_mm"],
        max_delta_height_spread_fraction=spread(height),
        delta_height_at_x165_edge_300_mm=centroid[-1],
        delta_height_at_x165_spread_fraction=spread(centroid),
        global_box_static_factor_at_points=fine["global_box_static_factor_at_points"],
        global_box_FKM_at_points=fine["global_box_FKM_at_points"],
        governing_stress_controls=strength_controls,
        governing_proof_stress=fine["steps"][-1]["global_control_points"][strength_controls["proof"]],
        governing_working_stress=fine["steps"][-2]["global_control_points"][strength_controls["working"]],
        maximum_reaction_imbalance_fraction=max(step["force_balance_fraction"] for m in solved for step in m["steps"][1:]),
        maximum_moment_imbalance_fraction=max(moment_error(m, step, shoe_proof_force_N)
                                              for m in solved for step in m["steps"][1:]),
        maximum_anchor_resultant_over_shoe_force_fraction=max(
            sum(v*v for v in step["anchor_net_reaction_N"])**.5 /
            sum(s["spring_force_N"] for s in step["support_steps"].values())
            for m in solved for step in m["steps"][1:]),
        point_stress_spreads_fraction=mesh_spreads,
        max_point_stress_spread_fraction=max((v for pair in mesh_spreads.values() for v in pair.values()
                                             if v is not None), default=None),
        governing_proof_stress_spread_fraction=mesh_spreads[strength_controls["proof"]]["proof_VM"],
        governing_FKM_stress_spread_fraction=mesh_spreads[strength_controls["working"]]["working_VM_range"],
        proof_stress_mesh_envelope_spread_fraction=spread([
            max(s["equivalent_MPa"] for s in m["steps"][-1]["global_control_points"].values()) for m in solved]),
        working_stress_mesh_envelope_spread_fraction=spread([
            max(s["range_MPa"] for s in m["steps"][-2]["global_control_points"].values()) for m in solved]),
        manual_comparison_315_bar=fine.get("manual_comparison_315_bar"),
        inactive_supports=fine.get("inactive_supports"),
        solver_pressure_steps_bar=fine["solver_pressure_steps_bar"],
    )
    return report, fine


def contact_series(standard, refined):
    rows = [*read_json(FEA / standard), *read_json(FEA / refined)]
    keys = {(row["station"], row["mesh_mm"]) for row in rows}
    if len(keys) != len(rows):
        raise ValueError("A contact mesh appears in both series.")
    return sorted(rows, key=lambda row: (row["station"], -row["mesh_mm"]))


def contact_summary(attempts):
    output = {}
    for station in ("front", "rear"):
        rows = sorted((a for a in attempts if a["station"] == station and a["status"] == "SOLVED"),
                      key=lambda row: row["mesh_mm"], reverse=True)
        proof = [a["steps"][-1] for a in rows]
        gauges = [a["contact_gauges"] for a in proof]
        history = [a for a in attempts if a["station"] == station]
        values = {"attempts": [{"mesh_mm": m["mesh_mm"], "status": m["status"],
                                "recorded_steps": m.get("recorded_steps")} for m in history],
                  "meshes_complete": len(rows)}
        if rows:
            keys = ("tooth_point_MPa", "heel_point_MPa", "highest_tooth_band_mean_MPa")
            values.update(
                proof_gauges=gauges[-1],
                working_gauges=rows[-1]["steps"][-2]["contact_gauges"],
                proof_gauges_by_mesh=[{"mesh_mm": row["mesh_mm"], **{k: g[k] for k in keys},
                                       "heel_band_mean_MPa": g["heel_band"]["pressure_mean_MPa"] if g["heel_band"] else None}
                                      for row, g in zip(rows, gauges)],
                spreads_fraction={**{k: spread([g[k] for g in gauges]) for k in keys},
                                  "heel_band_mean_MPa": spread([g["heel_band"]["pressure_mean_MPa"]
                                                               if g["heel_band"] else None for g in gauges])},
                maximum_balance_fraction=max(s["equilibrium_error_fraction"] for m in rows for s in m["steps"][1:]),
                maximum_target_mismatch_fraction=max(s["force_relative_error"] for m in rows for s in m["steps"][1:]),
                maximum_target_mismatch_300_315_fraction=max(
                    s["force_relative_error"] for m in rows for s in m["steps"][-2:]),
                local_static_at_points=min(s["material_Rp02_MPa"] / s["equivalent_MPa"]
                                           for s in proof[-1]["stress_probes"].values() if s["equivalent_MPa"] > 0.),
                local_FKM_at_points=min(s["FKM_if_working_step"]
                                        for s in rows[-1]["steps"][-2]["stress_probes"].values()),
                proof_pressure_projected_force_N=proof[-1].get("pressure_projected_force_N"),
                proof_cast_reaction_N=proof[-1]["cast_reaction_N"],
                section_checks=proof[-1].get("section_checks"),
                current_load_fraction_by_tooth=proof[-1]["tooth_force_shares_from_normal_pressure"],
            )
        output[station] = values
    return output


def construction(selected):
    lay = selected["layout"]
    seat_details = {}
    for label, station in selected["stations"].items():
        seat_details[label] = dict(
            moving_ring_outer_R_mm=station["outer_envelope_r_mm"],
            sleeve_installation_bore_R_mm=station["collar_r_mm"] + .5,
            lower_throat_R_mm=station["head_r_mm"] + 3.,
            moving_seat_annulus_thickness_mm=22.,
            base_ring_outer_R_mm=station["foot_r_mm"] + 12.,
            heel_installation_bore_R_mm=station["foot_r_mm"] + .5,
            cast_seating_throat_R_mm=station["shank_r_mm"] + 16.,
            loaded_tooth_plane_z_mm=90.,
            heel_thickness_mm=28.,
            tooth_edge_R_mm=5.,
            crown_mm=.10,
        )
    return dict(
        crosshead="Цельная отливка G35CrNiMo6-6+QT1 с интегральными опорными кольцами, обшивками и диафрагмами.",
        base="Цельная отливка G35CrNiMo6-6+QT1, крыша 15 мм и обе щеки отлиты вместе с основанием.",
        welds="Нагруженные соединения без швов. Сварной ремонт колец, диафрагм и зоны переходов исключён.",
        layout=lay, stations=selected["stations"], ring_seats=seat_details,
        pressure_centroid_xy_mm=selected["load_centroid_xy_mm"],
        pressure_longitudinal_law="Интеграл Janssen из T-2.2d, распределение по x 130,6–205 мм.",
        transverse_skew="Экспоненциальный профиль круга 1 со средним y = 57,841 мм, знак перекоса в модели положительный.",
        load_diaphragms={
            "front_center_x_mm": [147., 192.] if lay["focused_wing"] else [144., 187.],
            "rear_center_x_mm": [lay["rear_x_mm"] - 21., lay["rear_x_mm"] + 23.],
            "upper_front_thickness_mm": lay["top_front_webs_mm"],
            "lower_front_thickness_mm": lay["base_front_webs_mm"],
            "rear_thickness_mm": lay["rear_web_mm"],
            "lateral_wall_thickness_mm": lay["longitudinal_mm"],
            "pressure_longitudinal_rib_y_mm": [-71., 71.],
            "pressure_longitudinal_rib_mm": lay["pressure_rib_mm"],
            "front_flange_haunch_add_mm": lay["seat_haunch_mm"],
            "central_skin_width_mm": 216.,
            "central_shoe_face_stock_mm": 35.,
            "central_floor_face_stock_mm": 26.,
            "load_wing_each_side_bend_y_mm": 117.,
            "front_wing_web_offset_at_ring_fraction_outer_R": .80,
            "geometry_generator": "calc/T-2.2e/fea/r2_geometry.py",
        },
        chamber_cross_section_mm=[150., 60.], prepress_window_x_mm=[5., 205.],
        shoe_working_plane_z_mm=60., floor_working_plane_z_mm=0.,
        roof_x_mm=[205., 220.], roof_plane_z_mm=60., roof_section_depth_mm=115.,
        gate_plate_x_mm=[220., 274.], gate_rib_upstream_x_mm=214.,
        gate_swept_y_mm=[-130., 130.], gate_swept_z_mm=[-149., 188.],
        nominal_station_spacing_clearance_mm=selected["nominal_station_spacing_clearance_mm"],
        casting_fillet_status="Штатный R ≥ 15 для нагруженных переходов обязателен в КД. "
                              "В глобальном расчёте стыки отливки остроугольные. Номинальные точки вне кромок.",
        rotation_deg=60., tooth_sector_count=3, tooth_sector_angle_deg=55.,
        assembly="Муфта вынимается вверх через расточку наружного бурта. Снизу доступ к цельной пяте. "
                 "У верхнего направляющего бурта осевая разгрузка сервисного крепежа.",
    )


def main():
    baseline = read_json(HERE / "round1_accepted.json")
    design = deepcopy(baseline["design"])
    candidates = sensitivity()
    global_meshes = read_json(FEA / "r2_global_final.json")
    local_meshes = contact_series("r2_contact_standard_final.json", "r2_contact_refined_final.json")
    write_json(FEA / "r2_contact_final.json", local_meshes)
    replay_names = ("r2_contact_replay_standard.json", "r2_contact_replay_refined.json")
    if all((FEA / name).is_file() for name in replay_names):
        write_json(FEA / "r2_contact_replay.json", contact_series(*replay_names))
    global_info, selected = global_summary(
        global_meshes, baseline["load"]["shoe_and_roof_peaks"]["315_bar"]["shoe_force_N"])
    if selected is None:
        raise RuntimeError("There is no completed round-two reference model.")
    contact_info = contact_summary(local_meshes)
    statuses = gates()
    accepted_mass = baseline["mass"]
    mass = selected["mass"]
    frontier = [row for row in candidates if row.get("delta_height_300_mm", float("inf")) <= .6
                and row.get("smallest_support_300_N", -1.) >= 0. and row["station_to_station_clearance_mm"] >= 3.]
    min_mass = min(frontier, key=lambda row: row["delta_chamber_kg"]) if frontier else None
    reason = ("В пределах Δ узла +70 кг ни одно рассчитанное исполнение не подтвердило одновременно "
              "Δh ≤ 0,6 мм при перекосе и FKM ≥ 1,0. Выпуск КД не разрешён.")
    design.update(round=2, status="STOP", candidate=selected["layout"]["name"])
    design["qualification"].update(status="STOP", reason=reason, C_STR_01_qualified=None, C_FAT_01_qualified=None)
    design["round1_reference_geometry"] = design.pop("geometry")
    design["geometry"] = construction(selected)
    design["material"]["moving_crosshead"] = dict(grade="G35CrNiMo6-6+QT1", Rp02_min_MPa=650,
                                                   Rm_min_MPa=800, jG=1.25)
    design["mass"] = dict(round1_accepted_machine_and_station=accepted_mass, selected_trial_chamber=mass)
    design["fea_screen"] = dict(status="STOP", global_results=global_info, local_results=contact_info)
    design["hand_screen"]["scope"] = "Унаследованный отсев варианта круга 1. Значения не относятся к коробам круга 2."
    DESIGN.write_text(yaml.safe_dump(design, allow_unicode=True, sort_keys=False, width=108),
                      encoding="utf-8", newline="\n")
    report = dict(
        task="T-2.2e", round=2, status="STOP", reason=reason,
        hand=baseline["hand"], load=baseline["load"], cycle=baseline["cycle"], gate_statuses=statuses,
        mass=dict(round1_accepted=accepted_mass, selected_trial=mass,
                  lightest_tested_reaching_delta_height_limit=min_mass),
        fea=dict(status="STOP", global_summary=global_info, contact_summary=contact_info,
                 global_meshes=global_meshes, local_meshes=local_meshes, sensitivity=candidates,
                 round1_evidence=["fea/global.json", "fea/local_front.json", "fea/local_rear.json",
                                  "fea/section_checks.json", "fea/curvature_trials.json"]),
    )
    write_json(HERE / "results.json", report)
    write_json(ROOT / "metrics.json", dict(
        task="T-2.2e", round=2, status="STOP", candidate=selected["layout"]["name"],
        shoe_force_300_N=baseline["load"]["shoe_and_roof_peaks"]["300_bar"]["shoe_force_N"],
        shoe_force_315_N=baseline["load"]["shoe_and_roof_peaks"]["315_bar"]["shoe_force_N"],
        roof_depth_along_x_mm=15., dose_limit_kg=baseline["load"]["dose_limit_kg"],
        design_centroid_x_mm=selected["load_centroid_xy_mm"][0],
        design_centroid_y_mm=selected["load_centroid_xy_mm"][1],
        moment_at_300_about_window_center_Nm=baseline["load"]["shoe_and_roof_peaks"]["300_bar"]["shoe_force_N"] *
            (selected["load_centroid_xy_mm"][0] - 105.) / 1000.,
        delta_height_limit_mm=.6, trial_delta_height_300_mm=global_info["max_delta_height_300_mm"],
        delta_height_at_x165_edge_300_mm=global_info["delta_height_at_x165_edge_300_mm"],
        trial_delta_chamber_kg=mass["delta_chamber_kg"], delta_chamber_stop_limit_kg=70.,
        trial_machine_with_H2_kg=mass["machine_with_H2_kg"],
        accepted_H2_increment_kg=accepted_mass["H2_increment_kg"],
        accepted_station_reduction_with_H2_kg=accepted_mass["station_reduction_for_limit_with_H2_kg"],
        accepted_station_reduction_GK_target_kg=accepted_mass["station_reduction_D_GK_10_target_kg"],
        G_CYCLE_s=baseline["cycle"]["gate_s"], reference_cycle_s=baseline["cycle"]["reference_s"],
        C_STR_01_qualified=None, C_FAT_01_qualified=None, contact_life_cycles_qualified=None,
        global_FEA=global_info, local_FEA=contact_info, gate_statuses=statuses,
    ))


if __name__ == "__main__":
    main()

