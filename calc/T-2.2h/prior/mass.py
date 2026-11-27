"""Replacement chamber, axial growth and station mass ledger in kg."""

from math import fsum, pi

DENSITY_KG_MM3 = 7.85e-6
BASE_MACHINE_KG = 4942.65
BASE_CHAMBER_KG = 180.22
H2_KG = (5., 18.)
MACHINE_LIMIT_KG = 5000.


def ledger(rows_kg, roof_mm, frame, *, hydraulic_delta_kg=0.):
    main = frame["mass_budget"]["delta_rows"]
    increment = {row["item"]:row["delta_kg"] for row in main}
    columns = frame["columns"]
    delta_frame_kg = (columns["quantity"]*pi/4*columns["smooth_span_diameter_mm"]**2*
                      roof_mm*DENSITY_KG_MM3)
    shift = dict(frame_columns_kg=delta_frame_kg,
                 main_cylinder_filled_kg=increment["CY-MAIN"]*roof_mm/17,
                 rapid_cylinder_pair_filled_kg=increment["CY-RAPID"]*roof_mm/17)
    chamber_kg = fsum(rows_kg.values())
    delta_kg = chamber_kg - BASE_CHAMBER_KG
    before_H2_kg = BASE_MACHINE_KG + delta_kg + fsum(shift.values()) + hydraulic_delta_kg
    with_H2_kg = [before_H2_kg + h2 for h2 in H2_KG]
    return dict(chamber_rows_kg=rows_kg, chamber_kg=chamber_kg,
                baseline_chamber_kg=BASE_CHAMBER_KG, delta_chamber_kg=delta_kg,
                baseline_machine_kg=BASE_MACHINE_KG, shift_rows_kg=shift,
                hydraulic_delta_kg=hydraulic_delta_kg, machine_before_H2_kg=before_H2_kg,
                H2_delta_kg=list(H2_KG), machine_with_H2_kg=with_H2_kg,
                station_reduction_kg=[max(0.,kg-MACHINE_LIMIT_KG) for kg in with_H2_kg])
