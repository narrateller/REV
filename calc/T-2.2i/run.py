"""Generate deterministic T-2.2i trial results and dimensional study YAML."""

from dataclasses import asdict
import json
from pathlib import Path

import yaml

from hand import CORRECTION, OPTIONS, candidates, shortened_nose_sweep
from loads import (DOSE_LIMIT_KG, GATE_X_MM, K_GRID, LOADED_LENGTH_MM, MU_GRID, PRESSURES_BAR,
                   PREPRESS_PROOF_N, PROOF_SKEW_Y_MM, ROOF_SKEW_Y_MM, final_envelopes,
                   read_json, read_yaml, shoe_envelope)
from mass import STATION_LIMIT_KG, axial_stops, trial
from preload import calculate
from ring_frame import Ring, frame

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
                    + "\n", encoding="utf-8", newline="\n")


def design_basis():
    previous = read_yaml("design/chamber_roof.t22h.yaml")
    geometry = previous["working_chamber"]
    interfaces = previous["interfaces"]
    return {"working_chamber": geometry,
            "main_cylinder": {"bore_and_rod_mm": interfaces["main_bore_and_rod_geometry_mm"],
                              "installed_stroke_mm": interfaces["main_installed_stroke_mm"],
                              "working_stroke_mm": interfaces["main_working_stroke_mm"],
                              "body_length_mm": interfaces["main_body_mm"]},
            "slide_gate": {"face_x_mm": GATE_X_MM, "back_x_mm": interfaces["gate_blade_back_x_mm"],
                           "wing_min_x_mm": interfaces["gate_wing_min_x_mm"],
                           "width_mm": interfaces["gate_plate_width_mm"],
                           "thickness_mm": interfaces["gate_plate_thickness_mm"],
                           "swept_z_mm": interfaces["gate_plate_swept_z_mm"],
                           "nominal_sweep_y_mm": interfaces["gate_sweep_y_mm"],
                           "travel_mm": interfaces["gate_travel_mm"],
                           "pocket_yz_R_mm": interfaces["gate_housing_pocket_yz_R_mm"],
                           "wing_relief": previous["ring_trial"]["machined_slide_gate_wing_relief"]},
            "columns": {"pitch_mm": interfaces["column_bearing_pitch_mm"],
                        "smooth_span_mm": interfaces["column_smooth_span_mm"],
                        "diameter_mm": interfaces["column_D_mm"],
                        "preload_N": interfaces["column_preload_N"]},
            "shoe": {"face_x_mm": interfaces["shoe_face_x_mm"],
                     "sweep_y_mm": interfaces["shoe_sweep_y_mm"],
                     "face_width_mm": previous["window_trial"]["shoe_width_mm"],
                     "depth_mm": previous["window_trial"]["shoe_depth_mm"],
                     "rear_station": previous["window_trial"]["station_geometry"]["rear"]},
            "window_casting": {key: value for key, value in previous["window_trial"].items()
                               if key in ("body_x_mm", "working_floor_z_mm", "floor_cast_half_width_mm",
                                          "sidewall_abs_y_mm", "floor_depth_rear_front_mm",
                                          "floor_taper_x_mm", "material", "minimum_Rp02_Rm_MPa")},
            "ring_reference_geometry": {key: previous["ring_trial"][key] for key in (
                "outer_width_height_mm", "outer_corner_R_mm", "inner_corner_R_mm",
                "lamella_x_intervals_mm", "lamella_material", "lamella_min_Rp02_Rm_MPa",
                "max_ruling_flat_blank_mm")}}


def ring_diagnostic(reference, new_support, case, proof_pressure_MPa):
    geometry = new_support["interfaces"]
    slot = (*geometry["slot_abs_y_mm"], *geometry["slot_z_mm"])
    nose_loads = [(-OPTIONS[1].y_mm, new_support["governing_front_reactions_315_N"]["front_minus"]),
                  (OPTIONS[1].y_mm, new_support["governing_front_reactions_315_N"]["front_plus"])]
    span_mm = OPTIONS[1].bearing_length_mm
    line_loads = tuple((y, force_N / span_mm) for y, force_N in nose_loads)
    results = []
    for half_seat_mm in (85., 90.):
        ring = Ring(**(reference["candidate"] | {"seat_half_mm": half_seat_mm}))
        analyses = {}
        for name, pressure_MPa, loads, pocket in (
            ("final_solid", proof_pressure_MPa, (), None),
            ("final_slotted", proof_pressure_MPa, (), slot),
            ("transition_slotted", case["roof_inlet_315_MPa"], line_loads, slot)):
            hand = frame(ring, pressure_MPa, 0., ROOF_SKEW_Y_MM, 96,
                         detail=False, socket=pocket, extra_loads=loads)
            analyses[name] = hand | {"FKM_corrected": hand["FKM"] / CORRECTION,
                                     "radial_inlet_pressure_315_MPa": pressure_MPa}
        results.append({"geometry": asdict(ring), "bedding_width_mm": 2. * half_seat_mm,
                        "kern_e_max_mm": half_seat_mm / 3.,
                        "seat_linear_edge_min_to_mean": 1. - 3. * ROOF_SKEW_Y_MM / half_seat_mm,
                        "analyses": analyses})
    return results


def compare_reference(reference):
    rows = reference["FEA"]["roof"][-1]["integrated_sections_315"]
    max_moment_Nmm = max(abs(r["FEA_moment_Nmm"]) for r in rows)
    return {"scope": "Archived T-2.2h only", "reference_mesh_mm": 12.,
            "governing_reference_moment_Nmm": max_moment_Nmm,
            "rows": [{"reference_yz_mm": r["aperture_yz_mm"], "band_x_mm": r["X_mm"],
                      "FEA_N": r["FEA_N"], "hand_N": r["hand_N"],
                      "force_error_fraction": abs(r["hand_N"] - r["FEA_N"]) / abs(r["FEA_N"]),
                      "FEA_moment_Nmm": r["FEA_moment_Nmm"], "hand_moment_Nmm": r["hand_moment_Nmm"],
                      "moment_error_over_governing_fraction": abs(
                          abs(r["hand_moment_Nmm"]) - abs(r["FEA_moment_Nmm"])) / max_moment_Nmm}
                     for r in rows]}


def collect():
    reference = read_json("calc/T-2.2h/results.json")
    comparison = compare_reference(reference)
    supports = candidates()
    nose = supports["nose_x225"]
    best = shortened_nose_sweep()
    volume = read_json("calc/T-2.2i/fea/volume.json")
    envelope = final_envelopes()
    proof = envelope["315"]
    governing_radial = max(proof, key=lambda c: c["roof"]["normal_force_N"])
    governing_axial = max(proof, key=lambda c: c["wall_friction_N"])
    axial_e_mm = 2. * 150. * ROOF_SKEW_Y_MM / 420.
    rails = axial_stops(governing_axial["wall_friction_N"], axial_e_mm)
    ring = ring_diagnostic(reference, nose, nose["governing_front_case"], governing_radial["roof"]["inlet_MPa"])
    collar = calculate(ring[-1]["geometry"], reference["FEA"]["end"][-1],
                       governing_radial["roof"]["inlet_MPa"], governing_axial["wall_friction_N"])
    band_kg = collar["collar_gross_kg"] + collar["rounding_fill_gross_kg"]
    variants = {}
    for option in OPTIONS:
        part = supports[option.name]
        rows = {"without_end_collar": trial(reference, option, rails, 0.),
                "with_end_collar": trial(reference, option, rails, band_kg)}
        if option.kind == "nose":
            removed_kg = volume[-1]["front_removed_kg"]
            rows["with_collar_and_gross_old_front_removal"] = trial(reference, option, rails, band_kg, removed_kg)
        part["mass"] = rows
        variants[option.name] = part
    variants["key_x192"]["decision"] = ["geometry_interference", "key_FKM", "opening", "bearing", "drive"]
    variants["nose_x225"]["decision"] = ["integral_socket_ring_FKM", "drive_and_release", "unclosed_mass_ledger"]
    variants["clevis_x182"]["decision"] = ["cast_FKM", "bearing", "drive"]
    hydraulic = read_json("calc/T-2.6/results.json")
    gates = read_json("gates.t22i.json")["gates"]
    gate_data = {x["id"]: {k: x[k] for k in ("status", "value", "unit")} for x in gates}
    return {
        "task": "T-2.2i", "schema_version": 1, "status": "STOP_HAND_SCREEN", "qualified": False,
        "selected_variant": None, "recommended_trial_for_further_review": "nose_x225",
        "limits": {"design_opening_300_mm": .6, "minimum_hand_FKM": 1.15, "minimum_FEA_FKM": 1.,
                   "minimum_FEA_static": 1.5, "static_proof_bar": 315, "fatigue_pressure_bar": [0, 300],
                   "fatigue_cycles": 10_000_000, "station_reduction_max_kg": STATION_LIMIT_KG, "H2_kg": 18.},
        "loads": {"K_values": K_GRID, "mu_values": MU_GRID, "steps_bar": PRESSURES_BAR,
                  "dose_interlock_kg": DOSE_LIMIT_KG, "final_loaded_length_max_mm": LOADED_LENGTH_MM,
                  "shoe_skew_y_mm": PROOF_SKEW_Y_MM, "roof_skew_y_mm": ROOF_SKEW_Y_MM,
                  "independent_vertical_prepress_315_N": PREPRESS_PROOF_N,
                  "independent_uniform_prepress_floor_mean_MPa": PREPRESS_PROOF_N / 30_000.,
                  "shoe_envelope": shoe_envelope(), "final_envelope": envelope,
                  "governing_radial": governing_radial, "governing_axial": governing_axial},
        "T-2.2h_replay": {"support": supports["T-2.2h"], "moments_and_resultants": comparison,
                           "FEA_review": reference["FEA"]["window"][-1]},
        "variants": variants, "shortened_nose_sweep": best,
        "ring": {"bedding_min_mm": 6. * ROOF_SKEW_Y_MM, "width_trials": ring, "axial_stops": rails,
                 "gate_end_collar": collar},
        "mass_volume_diagnostic": volume, "gates": gate_data,
        "cycle": {"T-2.6_nominal_s": hydraulic["variants"][hydraulic["selected"]]["reference_cycle_s"],
                  "T-2.6_adverse_s": 6.193, "kinematic_equivalence_verified": False},
        "fea": {"structural_contact_solver_run": False, "status": "not_run_hand_stop",
                "mesh_convergence": None, "structural_balance_verified": False,
                "required_local_elements_through_thickness": 3,
                "required_convergence_fraction": .05, "required_reaction_balance_fraction": .001},
    }


def design(data):
    ring = data["ring"]
    return {"task": "T-2.2i", "schema_version": 1, "status": data["status"], "qualified": False,
            "selected_variant": data["selected_variant"],
            "project_basis": ["D-GK-13", "D-OP-16", "D-GK-15", "D-OP-17", "D-OP-18"],
            "units": {"length": "mm", "force": "N", "stress": "MPa", "mass": "kg"},
            "axes": "X towards the gate, Y across the 150 mm bore, Z up from the bore centre",
            **design_basis(),
            "support_trials": {k: {"geometry": v["geometry"], "interfaces": v["interfaces"],
                                   "rejection_reasons": v["decision"]}
                               for k, v in data["variants"].items()},
            "shortened_nose_geometry": data["shortened_nose_sweep"]["best_stem_load"]["geometry"],
            "ring_and_backing_screen": {
                "pulsating_skew_e_mm": ROOF_SKEW_Y_MM, "working_wear_width_mm": 150.,
                "full_flat_bedding_width_mm": 180., "minimum_kern_width_mm": ring["bedding_min_mm"],
                "bedding_abs_z_mm": ring["width_trials"][-1]["geometry"]["inner_z_mm"],
                "wear_thickness_mm": 12.,
                "aperture_width_height_mm": [254., 112.],
                "side_seats_abs_y_mm": 127., "side_seats_abs_z_mm": [0., 19.]},
            "axial_stop_trial": ring["axial_stops"], "gate_end_collar_trial": ring["gate_end_collar"],
            "limits": data["limits"], "analysis_data": "calc/T-2.2i/results.json",
            "sources": "calc/T-2.2i/sources.yaml"}


def summary(data):
    variants = data["variants"]
    table = {name: {"opening_300_mm": row["opening"]["opening_300_mm"],
                    "key_FKM_corrected": row["front"]["key"]["FKM_corrected"],
                    "peak_mean_land_300_MPa": row["front"]["land_mean_bearing_300_MPa"],
                    "station_reduction_with_collar_kg": row["mass"]["with_end_collar"]["station_reduction_kg"]}
             for name, row in variants.items()}
    ring_trials = data["ring"]["width_trials"]
    table["key_x192"]["governing_hand_FKM"] = table["key_x192"]["key_FKM_corrected"]
    table["nose_x225"]["governing_hand_FKM"] = ring_trials[-1]["analyses"]["final_slotted"]["FKM_corrected"]
    table["clevis_x182"]["governing_hand_FKM"] = variants["clevis_x182"]["front"]["cast_nominal"]["FKM_corrected"]
    nose_mass = variants["nose_x225"]["mass"]["with_collar_and_gross_old_front_removal"]
    best = data["shortened_nose_sweep"]["best_stem_load"]["drive"]
    collar = data["ring"]["gate_end_collar"]
    return {"task": data["task"], "status": data["status"], "qualified": False,
            "shoe_proof_force_N": data["loads"]["shoe_envelope"]["shoe_315_bar_N"],
            "maximum_axial_wall_friction_315_N": data["loads"]["governing_axial"]["wall_friction_N"],
            "maximum_roof_normal_315_N": data["loads"]["governing_radial"]["roof"]["normal_force_N"],
            "transfer_axial_force_N": data["loads"]["shoe_envelope"]["transfer_axial_force_N"],
            "supports": table, "axial_stop_mean_contact_300_MPa": data["ring"]["axial_stops"]["mean_300_MPa"],
            "nose_integral_ring_FKM_corrected": data["ring"]["width_trials"][-1]["analyses"]["final_slotted"]["FKM_corrected"],
            "shortened_nose_stem_force_at_2kN_N_by_mu": best["front_and_rear_stem_force_N_by_assumed_mu"],
            "shortened_nose_stem_force_limit_N": best["stem_force_limit_N"],
            "shortened_nose_residual_capacity_N_by_mu": best["residual_capacity_N_by_assumed_mu"],
            "nose_mass_with_collar_and_gross_old_front_removal_kg": nose_mass["machine_before_station_kg"],
            "nose_station_reduction_with_gross_old_front_removal_kg": nose_mass["station_reduction_kg"],
            "nose_unallocated_mass_kg": nose_mass["mass_margin_kg"],
            "collar_radial_interference_mm": collar["cold_radial_interference_mm"],
            "collar_mass_with_rounding_fill_kg": collar["collar_gross_kg"] + collar["rounding_fill_gross_kg"],
            "G-PFACE": data["gates"]["G-PFACE"], "G-DOSE": data["gates"]["G-DOSE"],
            "G-CYCLE_reference_only": data["gates"]["G-CYCLE"], "fea": data["fea"]}


def main():
    from report import write_report

    data = collect()
    write_json(HERE / "results.json", data)
    write_json(ROOT / "metrics.json", summary(data))
    (ROOT / "design/chamber_roof.t22i.yaml").write_text(
        yaml.safe_dump(design(data), allow_unicode=True, sort_keys=False, width=102),
        encoding="utf-8", newline="\n")
    write_report(ROOT / "report.md", data)


if __name__ == "__main__":
    main()

