"""Build the round-2 calculations and the selected G-CYCLE input."""

from itertools import product
import json
from math import prod
from pathlib import Path
import sys

import yaml

import hand
from load import accepted_load, read_geometry, read_yaml, roof_envelope
from mass import gate_shift


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "cycle"))
from roof_cycle import RoofStudy


ROOFS_MM = (10, 15, 20, 25)
REFERENCE_LIMIT_S = 5.90
GATE_LIMIT_S = 5.95
DOSE_SETTING_KG = 0.85267


def read_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def write_text(path, content):
    try:
        path.write_text(content, encoding="utf-8", newline="\n")
    except PermissionError:
        fallback = path.with_suffix(path.suffix + ".r2")
        fallback.write_text(content, encoding="utf-8", newline="\n")
        return fallback
    return path


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def transfer_screen(accepted):
    """Keep the constant retained face traction and entry allowance of variant B."""
    upstream = read_json("calc/T-1.2b/results.json")
    length_mm = upstream["axis_A"]["transferred_fill_length_mm"]
    edge_N = upstream["closed_zone_B"]["edge_drag_assumption_N"]
    width_mm, height_mm = accepted["section_mm"]
    curve = read_yaml("calc/T-1.1/curve.yaml")
    nominal_kg = read_yaml("design/params.t21.yaml")["raw"]["dose_kg"]
    max_dose_kg = DOSE_SETTING_KG * (1 + accepted["dose_upper_tolerance_fraction"])
    material = read_geometry().Material(curve, nominal_kg, accepted["section_mm"])
    rows = {case: {} for case in ("base", "low", "high")}
    for case, bulk_kg_m3 in product(rows, (90, 160)):
        by_dose = rows[case][bulk_kg_m3] = {}
        for name, dose_kg in (("nominal", nominal_kg), ("upper", max_dose_kg)):
            pre_section_mm = [length_mm, width_mm]
            density_kg_m3 = dose_kg * 1e9 / (prod(pre_section_mm) * height_mm)
            radial_MPa = material.face_MPa(density_kg_m3, bulk_kg_m3, case, dose_kg=dose_kg,
                                            section_mm=pre_section_mm, wall_case=case)
            mu = curve["mu"][case]
            friction_N = mu * radial_MPa * accepted["perimeter_mm"] * length_mm
            by_dose[name] = dict(dose_kg=dose_kg, mu=mu, retained_radial_MPa=radial_MPa,
                                 full_plug_length_mm=length_mm, wall_friction_N=friction_N,
                                 push_force_N=friction_N + edge_N, edge_force_N=edge_N,
                                 edge_equivalent_shear_MPa=edge_N / accepted["area_mm2"],
                                 retained_shoe_force_N=radial_MPa * prod(pre_section_mm))
    return rows


def cycle_pass(row):
    realistic = row["reference"]["realistic"]
    return (row["gate_status"] == "PASS" and row["gate_cycle_s"] <= GATE_LIMIT_S
            and realistic["feasible"] and realistic["convergence_pass"]
            and realistic["cycle_with_T16_handover_s"] <= REFERENCE_LIMIT_S
            and row["gate_dose"]["status"] == "PASS" and row["gate_pface"]["status"] == "PASS")


def calculate():
    accepted = accepted_load()
    transfer = transfer_screen(accepted)
    frame = read_yaml("design/frame.t17d.yaml")
    cylinders = {row["id"]: row for row in read_yaml("design/cylinders.t17d.yaml")["cylinders"]}
    baseline, _ = RoofStudy(0, transfer, adds_local_overtravel=False).evaluate_roof()
    assert abs(baseline["gate_cycle_s"] - 5.823772630624717) < 1e-9
    assert abs(baseline["reference"]["realistic"]["cycle_with_T16_handover_s"] - 5.52) < 1e-9
    assert abs(baseline["reference"]["pessimistic"]["cycle_with_T16_handover_s"] - 5.88375) < 1e-9
    candidates = []
    params_by_roof = {}
    for roof_mm in ROOFS_MM:
        study = RoofStudy(roof_mm, transfer, adds_local_overtravel=False)
        row, params_by_roof[roof_mm] = study.evaluate_roof()
        row["passes_selection"] = cycle_pass(row)
        row["load"] = roof_envelope(roof_mm, accepted)
        row["gate_shift"] = gate_shift(roof_mm, study.nominal_add_mm, frame, cylinders)
        # Sensitivity if the extension is also added to the travel beyond the
        # new gate face: the ejection endpoint then moves by 2X.
        sensitivity = RoofStudy(roof_mm, transfer, adds_local_overtravel=True)
        _, sensitivity_gate = sensitivity.gate_for("A4VSO180_DFE1Z")
        row["double_extension_sensitivity"] = dict(gate_cycle_s=sensitivity_gate["value"],
                                                    endpoint_increment_mm=sensitivity.nominal_add_mm)
        print("X", roof_mm, "G-CYCLE", row["gate_cycle_s"], "PASS" if row["passes_selection"] else "FAIL", flush=True)
        candidates.append(row)
    selected_mm = max((row["roof_mm"] for row in candidates if row["passes_selection"]), default=None)
    result = dict(task="T-2.2d", round=2, accepted_round1_load="calc/T-2.2d/round1_load.json",
                  dose_setpoint_limit_kg=DOSE_SETTING_KG, transfer=transfer, baseline=baseline,
                  reference_limit_s=REFERENCE_LIMIT_S, gate_limit_s=GATE_LIMIT_S,
                  candidates=candidates, selected_roof_mm=selected_mm, hand=None,
                  status="STOP_ROOF_CYCLE" if selected_mm is None else None)
    if selected_mm is not None:
        roof = next(row for row in candidates if row["roof_mm"] == selected_mm)
        gate = read_yaml("design/slide_gate.t17d.yaml")
        gate["face_x_mm"] = roof["layout"]["gate_face_x_mm"]
        manual = hand.calculate(roof, roof["gate_shift"], gate)
        result["hand"] = manual
        result["status"] = "STOP_HAND_SCREEN" if not manual["passes"] else "PENDING_FEA"
    return result, params_by_roof.get(selected_mm)


def design_and_metrics(result):
    accepted = accepted_load()
    roof_mm = result["selected_roof_mm"]
    selected = next(row for row in result["candidates"] if row["roof_mm"] == roof_mm)
    layout = selected["layout"]
    trial = result["hand"]["best"]
    mass = trial["mass"]
    peaks = {case: data["peak"] for case, data in selected["load"].items()}
    roof_cases = {str(row["roof_mm"]): dict(
        shoe_force_300_bar_N=row["load"]["300_bar"]["peak"]["shoe_force_N"],
        shoe_force_315_bar_N=row["load"]["315_bar"]["peak"]["shoe_force_N"],
        gate_cycle_s=row["gate_cycle_s"], reference_cycle_s=row["reference"]["realistic"]["cycle_with_T16_handover_s"],
        pessimistic_cycle_s=row["reference"]["pessimistic"]["cycle_with_T16_handover_s"],
        frame_and_cylinders_increment_kg=row["gate_shift"]["delta_kg"], passes_selection=row["passes_selection"])
        for row in result["candidates"]}
    geometry_names = ("stations", "shoe_h_mm", "floor_h_mm", "shoe_face_to_box_mm", "face_skin_mm",
                      "roof_depth_mm", "shoe_four_webs_each_mm", "floor_four_webs_each_mm", "root_radius_mm",
                      "crown_mm", "horizontal_station_clearance_mm", "effective_span_mm")
    metrics = dict(task="T-2.2d", round=2, status=result["status"], selected_roof_mm=roof_mm,
                   loaded_max_mm=accepted["loaded_limit_mm"], dose_setpoint_limit_kg=DOSE_SETTING_KG,
                   roof_cases=roof_cases, static_factor_hand=trial["static_factor"], FKM_hand=trial["FKM"],
                   contact_315_bar_hand_MPa=trial["contact_peak_MPa"],
                   contact_screen_MPa=trial["contact_screen_MPa"], height_contribution_300_bar_mm=trial["height_300_mm"],
                   minimum_height_within_60_kg_mm=result["hand"]["minimum_height"]["height_300_mm"],
                   chamber_kg=mass["chamber_kg"], delta_chamber_kg=mass["delta_chamber_kg"],
                   machine_kg=mass["machine_kg"], machine_with_H2_kg=mass["machine_with_H2_kg"],
                   station_reduction_with_H2_kg=mass["station_reduction_with_H2_kg"],
                   FEA_status="SKIPPED_HAND_STOP")
    design = dict(task="T-2.2d", round=2, status=result["status"], qualification="Эскизный вариант ручного отсева",
                  load=dict(loaded_length_limit_mm=accepted["loaded_limit_mm"],
                            released_length_limit_mm=accepted["released_limit_mm"],
                            dose_setpoint_limit_kg=DOSE_SETTING_KG,
                            dose_positive_tolerance_fraction=accepted["dose_upper_tolerance_fraction"],
                            mass_interlock="Весовая проверка каждой порции перед главным ходом. Блокировка при превышении верхней границы рецепта или сбое измерения.",
                            peaks=peaks),
                  roof=dict(length_mm=roof_mm, axial_interval_mm=[accepted["window_x_mm"][1], layout["gate_face_x_mm"]],
                            G_DOSE_overtravel_from_original_window_edge_mm=layout["overtravel_nominal_mm"] + roof_mm,
                            local_overtravel_from_shifted_gate_face_mm=[layout["overtravel_nominal_mm"], layout["overtravel_maximum_mm"]],
                            installed_main_stroke_mm=layout["main_installed_stroke_mm"],
                            nominal_ejection_end_x_mm=layout["punch_face_nominal_eject_end_x_mm"],
                            maximum_ejection_end_x_mm=layout["punch_face_maximum_eject_end_x_mm"],
                            transfer_push_nominal_N=result["transfer"]["base"][90]["nominal"]["push_force_N"],
                            transfer_push_upper_N=max(doses["upper"]["push_force_N"] for cases in result["transfer"].values()
                                                      for doses in cases.values()),
                            edge_allowance_N=result["transfer"]["base"][90]["nominal"]["edge_force_N"],
                            cycle_selection=roof_cases[str(roof_mm)]),
                  bayonet=dict(quantity=4, geometry={name: trial[name] for name in geometry_names},
                               edge_radius_mm=hand.EDGE_R_MM, loaded_teeth_per_post=3, sector_deg=hand.ENGAGEMENT_DEG,
                               assumed_max_tooth_share=hand.TOOTH_SHARE, fasteners_in_service_load_path=0,
                               support_checks=trial["support_checks"], strength_sections=trial["strength_sections"],
                               height_contribution_300_bar_mm=trial["height_300_mm"],
                               height_breakdown_300_bar_mm=trial["delta_height_300_mm"],
                               height_limit_mm=.5, contact_screen_MPa=hand.CONTACT_SCREEN_MPa,
                               contact_model="Номинальный Герц с пересечением кромок по R5. 52–57 HRC, SHD ≥ 6 мм и ресурс пары требуют проверки.",
                               run_FEA=False),
                  drive=trial["drive"] | dict(
                      concept="Кулачок с 12 мм относительного хода, общий вал с двумя синхронизированными парами муфт и контролем крайних положений каждой муфты.",
                      interlock="Главное прессование только при подтверждённом запирании четырёх муфт. Начало поворота после разгрузки зубьев и подтверждения ухода продукта из окна.",
                      cycle_status="Цикл выбора крыши использует привод замка T-2.1. Новый привод не квалифицирован по времени."),
                  interfaces=dict(section_mm=accepted["section_mm"], window_mm=[150, 200], window_x_mm=accepted["window_x_mm"],
                                  gate_face_x_mm=layout["gate_face_x_mm"], gate_plate_back_x_mm=layout["gate_back_x_mm"],
                                  gate_rib_upstream_x_mm=layout["gate_face_x_mm"] - 6,
                                  gate_plate_crosswise_mm=[-130, 130], gate_swept_vertical_mm=[-149, 188],
                                  gate_opening_travel_mm=layout["gate_working_travel_mm"],
                                  gate_close_permission_max_punch_x_mm=layout["punch_face_clear_for_gate_close_x_mm"],
                                  main_cylinder_bore_rod_mm=[280, 200], prepress_cylinder_bore_rod_mm=[125, 56],
                                  frame_and_cylinders=selected["gate_shift"],
                                  clearances_scope="Плановая огибающая подвижной плиты с рёбрами. Неподвижный карман, привод шибера, бункер и все позы башмака требуют пространственной проверки."),
                  mass=mass, source_file="calc/T-2.2d/sources.yaml")
    return design, metrics


def main():
    result, params = calculate()
    if params:
        write_text(ROOT / "design/params.t22d.yaml",
                   "# Generated by calc/T-2.2d/run.py. See the gate coordinate convention in description.\n"
                   + yaml.safe_dump(params, allow_unicode=True, sort_keys=False))
        design, metrics = design_and_metrics(result)
        write_text(ROOT / "design/prepress_lock.t22d.yaml",
                   "# Generated by calc/T-2.2d/run.py. Status applies to the entire concept.\n"
                   + yaml.safe_dump(design, allow_unicode=True, sort_keys=False))
        write_json(ROOT / "metrics.json", metrics)
    write_json(HERE / "fea/status.json",
               dict(task="T-2.2d", executed=False, reason=result["status"],
                    contact_FEA_method_reference="calc/T-2.2b/fea/solve.py"))
    write_json(HERE / "results.json", result)


if __name__ == "__main__":
    main()
