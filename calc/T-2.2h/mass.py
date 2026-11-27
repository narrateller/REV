"""Mass ledger for the hand-screened ring and the proposed window."""

from math import fsum

from hand import DENSITY_KG_MM3
from layout import STATIONS, KEY_CLOSED_Y_MM, LOCK_UPPER_Y_MM, LOCK_LOWER_Y_MM, WEAR_LAND_DEPTH_MM
from loads import read_json, read_yaml
from prior.mass import ledger

MACHINE_LIMIT_KG = 5000.
STATION_LIMIT_KG = 230.
RAIL_ABS_Y_MM = (172.,201.)
RAIL_Z_MM = (-95.,95.)
RAIL_LENGTH_MM = 54.

WINDOW_REFERENCE_KG = 89.5126718289058
SHOE_REFERENCE_KG = 25.029692073988016
WINDOW_REFERENCE = "calc/T-2.2g/fea/window_reinforced.json, 18 mm analysis volume"


def new_rail_mass_kg():
    dy_mm = RAIL_ABS_Y_MM[1] - RAIL_ABS_Y_MM[0]
    dz_mm = RAIL_Z_MM[1] - RAIL_Z_MM[0]
    return 2 * dy_mm * dz_mm * RAIL_LENGTH_MM * DENSITY_KG_MM3


def window_rows(window=None):
    if window:
        volumes = window["body_volumes_mm3"]
        source = "calc/T-2.2h/fea/window_screen.json, casting and shoe mesh volumes"
        body_kg = volumes["open_casting"] * DENSITY_KG_MM3
        shoe_kg = volumes["shoe"] * DENSITY_KG_MM3
    else:
        source = WINDOW_REFERENCE
        body_kg = WINDOW_REFERENCE_KG
        shoe_kg = SHOE_REFERENCE_KG
    rows = {
        "open_casting": {"mass_kg":body_kg,"source":source},
        "shoe": {"mass_kg":shoe_kg,"source":source},
        "insert_and_retainer_allowance": {"mass_kg":5.,"source":"calc/T-2.2g/results.json, T-2.2f allowance"},
        "synchroniser_and_guard": {"mass_kg":7.,"source":"calc/T-2.2g/results.json, T-2.2f allowance"},
        "interface_and_local_rib_allowance": {"mass_kg":10.,"source":"calc/T-2.2g/results.json, T-2.2f allowance"},
    }
    length_mm = KEY_CLOSED_Y_MM[1]-KEY_CLOSED_Y_MM[0]
    active_width_mm = (LOCK_UPPER_Y_MM[1]-LOCK_UPPER_Y_MM[0]
                       + LOCK_LOWER_Y_MM[1]-LOCK_LOWER_Y_MM[0])
    for name,station in STATIONS.items():
        width_mm,depth_mm,leg_mm=(station[k] for k in ("key_width_mm","key_depth_mm","leg_width_mm"))
        key_pair_mm3 = 2*width_mm*depth_mm*length_mm
        wear_mm3=2*(width_mm+2*leg_mm+1.6)*active_width_mm*WEAR_LAND_DEPTH_MM
        for item,volume in (("keys",key_pair_mm3),("wear_lands",wear_mm3)):
            rows[f"{name}_{item}"]={"mass_kg":volume*DENSITY_KG_MM3,
                                   "source":"calc/T-2.2h/layout.py, gross section of the T-2.2g lock"}
    return rows


def budget(geometry,window=None):
    rows = window_rows(window) | {
        "ring_and_structural_liner": {
            "mass_kg":geometry.ring_and_liner_mass_kg(),
            "source":"calc/T-2.2h/hand.py, gross rounded rectangle less R1 working bore"},
        "axial_rails": {"mass_kg":new_rail_mass_kg(),
                        "source":"calc/T-2.2h/fea/ring.py, 2 seat extensions to X 349"},
    }
    ref = read_json("calc/T-2.6/results.json")
    hydraulic_kg = ref["variants"][ref["selected"]]["mass"]["added_hydraulics_kg"]
    frame = read_yaml("design/frame.t17d.yaml")
    result = ledger({k:v["mass_kg"] for k,v in rows.items()},90.,frame,hydraulic_delta_kg=hydraulic_kg)
    result["chamber_rows"] = rows
    result["machine_rows"] = [
        {"part":"baseline","mass_kg":result["baseline_machine_kg"],
         "source":"design/main_cylinder_rear.t22.yaml; rounded ledger T-2.2g"},
        {"part":"remove_baseline_chamber","mass_kg":-result["baseline_chamber_kg"],
         "source":"calc/T-2.2g/results.json; T-2.2f reference"},
        {"part":"replacement_chamber","mass_kg":result["chamber_kg"],
         "source":"chamber_rows"},
        {"part":"columns","mass_kg":result["shift_rows_kg"]["frame_columns_kg"],
         "source":"design/frame.t17d.yaml; 4 × Ø70 × 90 mm"},
        {"part":"main_cylinder_filled","mass_kg":result["shift_rows_kg"]["main_cylinder_filled_kg"],
         "source":"design/frame.t17d.yaml; CY-MAIN increment × 90/17"},
        {"part":"rapid_cylinders_filled","mass_kg":result["shift_rows_kg"]["rapid_cylinder_pair_filled_kg"],
         "source":"design/frame.t17d.yaml; CY-RAPID increment × 90/17"},
        {"part":"slide_gate_cassette_and_traverse_delta","mass_kg":0.,
         "source":"design/slide_gate.t17d.yaml and design/frame.t17d.yaml; net translation"},
        {"part":"hydraulics_delta","mass_kg":hydraulic_kg,
         "source":"calc/T-2.6/results.json, selected.mass.added_hydraulics_kg"},
        {"part":"H2_max","mass_kg":18.,"source":"TASK.md and calc/T-2.2g/results.json"},
    ]
    maximum_machine_kg=MACHINE_LIMIT_KG+STATION_LIMIT_KG
    subtotal_kg = fsum(r["mass_kg"] for r in result["machine_rows"] if r["part"]!="replacement_chamber")
    result["max_replacement_chamber_kg"]=maximum_machine_kg-subtotal_kg
    result["max_ring_and_liner_kg_at_given_window"]=(
        maximum_machine_kg-subtotal_kg-new_rail_mass_kg()
        - fsum(r["mass_kg"] for r in window_rows(window).values()))
    result["station_ceiling_kg"]=STATION_LIMIT_KG
    # Upper bound for the two spline runouts. Their rounded cross sections
    # and varying depth are both dominated by these complete boxes.
    pocket_depth_bound_mm=7.
    result["gate_relief_mass_credit_bound_kg"]=(
        2*(164.-77.5)*2*geometry.band_half_mm*pocket_depth_bound_mm*DENSITY_KG_MM3)
    result["station_reduction_after_full_relief_bound_H2_max_kg"]=(
        result["station_reduction_kg"][-1]-result["gate_relief_mass_credit_bound_kg"])
    result["worst_H2_mass_margin_before_station_kg"]=maximum_machine_kg-result["machine_with_H2_kg"][-1]
    result["basis"]="trial, explicit axial rails, assembly hardware beyond allowances unquantified"
    return result

