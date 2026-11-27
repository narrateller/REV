"""Chamber envelopes and machine mass ledger, with source paths per row."""

from math import fsum

from layout import (KEY_CLOSED_Y_MM, LOCK_CAP_MM, LOCK_LEG_X_MM, LOCK_LOWER_Y_MM,
                    LOCK_UPPER_Y_MM, LOWER_RETURN_DEPTH_MM, LOWER_RETURN_START_Y_MM,
                    SHOE_ABS_Y_MAX_MM, STATIONS, WEAR_LAND_DEPTH_MM,
                    WINDOW_FLOOR_ABS_Y_MM, WINDOW_REAR_X_MM, WINDOW_SIDEWALL_ABS_Y_MM,
                    FLOOR_SKIN_DEPTH_MM, FLOOR_TAPER_X_MM, REAR_FLOOR_DEPTH_MM)
from loads import read_json, read_yaml
from prior.mass import DENSITY_KG_MM3, ledger

HARD_LIMIT_KG = 5000.
TARGET_KG = 4900.
STATION_ALLOWANCE_KG = 145.


def chamber_rows(layout):
    # Debit gross blocks. The working channel is the only volume deduction.
    xb_mm = 205. - WINDOW_REAR_X_MM
    foot_mm = FLOOR_SKIN_DEPTH_MM
    z_key_mm = 30. + layout.shoe_depth_mm
    uy_mm = LOCK_UPPER_Y_MM[1] - LOCK_UPPER_Y_MM[0]
    ly_mm = LOCK_LOWER_Y_MM[1] - LOWER_RETURN_START_Y_MM
    key_y_mm = KEY_CLOSED_Y_MM[1] - KEY_CLOSED_Y_MM[0]
    bw_mm = sum(s["key_width_mm"] for s in STATIONS.values())
    slender_length_mm = sum(FLOOR_TAPER_X_MM) / 2 - WINDOW_REAR_X_MM
    volumes_mm3 = {
        "closed_roof_ring": 90. * (layout.roof_width_mm *
             (60. + layout.roof_band_mm + layout.floor_band_mm) - 150. * 60.),
        "window_bottom": 2 * WINDOW_FLOOR_ABS_Y_MM * (
            slender_length_mm * REAR_FLOOR_DEPTH_MM + (xb_mm - slender_length_mm) * foot_mm),
        "window_guides": xb_mm * 2 * (WINDOW_SIDEWALL_ABS_Y_MM - 75.) * 60.,
        "shoe_window_plate": 200. * 150. * layout.shoe_depth_mm,
        "shoe_wings": 2 * bw_mm * (SHOE_ABS_Y_MAX_MM - 75.) * layout.shoe_depth_mm,
    }
    for name, station in STATIONS.items():
        depth_mm = station["key_depth_mm"]
        legs_mm = station["leg_width_mm"]
        width_mm = station["key_width_mm"]
        full_width_mm = width_mm + 2 * legs_mm + 1.6
        floor_mm = REAR_FLOOR_DEPTH_MM if name == "rear" else foot_mm
        for item, volume in {
            "transverse_bridge": 2 * full_width_mm * (LOCK_UPPER_Y_MM[1] - WINDOW_FLOOR_ABS_Y_MM) * floor_mm,
            "cheek_legs": 4 * legs_mm * (uy_mm + 11.) * (z_key_mm + depth_mm + WEAR_LAND_DEPTH_MM + 30.),
            "cheek_cap": 2 * full_width_mm * uy_mm * station["cap_depth_mm"],
            "key_lower_return": 2 * full_width_mm * ly_mm * station["return_depth_mm"],
            "two_keys": 2 * width_mm * key_y_mm * depth_mm,
            "wear_lands": 2 * full_width_mm *
                          (uy_mm + LOCK_LOWER_Y_MM[1] - LOCK_LOWER_Y_MM[0]) * WEAR_LAND_DEPTH_MM,
         }.items():
            volumes_mm3[f"{name}_{item}"] = volume
    result = {k: {"mass_kg": v * DENSITY_KG_MM3, "source": "calc/T-2.2g/layout.py and mass.py"}
              for k, v in volumes_mm3.items()}
    old = read_json("calc/T-2.2f/results.json")["series"]["A_90"]["hand"]["mass"]["chamber_rows_kg"]
    for k in ("inserts_and_retainers", "synchronizer_and_guards", "interfaces_and_local_ribs"):
        result[k] = {"mass_kg": old[k], "source": "calc/T-2.2f/results.json, series.A_90.hand.mass"}
    return result


def budget(layout, measured_rows_kg=None):
    rows = chamber_rows(layout)
    for name, kg in (measured_rows_kg or {}).items():
        rows[name] = {"mass_kg": kg, "source": "calc/T-2.2g/fea, analysis solid volume"}
    ref = read_json("calc/T-2.6/results.json")
    hydraulic = ref["variants"][ref["selected"]]["mass"]["added_hydraulics_kg"]
    frame = read_yaml("design/frame.t17d.yaml")
    raw = ledger({k: v["mass_kg"] for k, v in rows.items()}, 90., frame,
                 hydraulic_delta_kg=hydraulic)
    sources = {
        "baseline_machine": "design/main_cylinder_rear.t22.yaml, mass.nominal_machine_AB_kg, rounded T-2.2f",
        "baseline_chamber": "calc/T-2.2f/results.json, series.A_90.hand.mass",
        "frame_columns_kg": "design/frame.t17d.yaml, 4 × Ø70 × 90; T-2.2f",
        "main_cylinder_filled_kg": "design/frame.t17d.yaml, CY-MAIN filled incremental mass × 90/17; T-2.2f",
        "rapid_cylinder_pair_filled_kg": "design/frame.t17d.yaml, CY-RAPID filled incremental mass × 90/17; T-2.2f",
        "shifted_gate_plate_cassette_and_traverse": "design/slide_gate.t17d.yaml and design/frame.t17d.yaml, unchanged dimensions",
        "hydraulics": "calc/T-2.6/results.json, selected mass ledger",
        "H2": "calc/T-2.2f/mass.py, [5, 18] kg from T-2.2/GK",
        "station_limit": "DECISIONS.md, D-OP-16",
    }
    machine_rows = {
        "baseline_machine": raw["baseline_machine_kg"], "baseline_chamber": -raw["baseline_chamber_kg"],
        "replacement_chamber": raw["chamber_kg"], **raw["shift_rows_kg"],
        "shifted_gate_plate_cassette_and_traverse": 0., "hydraulics": hydraulic,
        "H2": raw["H2_delta_kg"],
    }
    available_kg = HARD_LIMIT_KG + STATION_ALLOWANCE_KG - (
        fsum(v for k, v in machine_rows.items() if k not in ("replacement_chamber", "H2")) + max(machine_rows["H2"]))
    return raw | {
        "chamber_rows": rows, "machine_rows_kg": machine_rows, "sources": sources,
        "station_allowance_kg": STATION_ALLOWANCE_KG,
        "maximum_chamber_kg_at_station_allowance_worst_H2": available_kg,
        "station_reduction_to_target_kg": [max(0., x - TARGET_KG) for x in raw["machine_with_H2_kg"]],
    }
