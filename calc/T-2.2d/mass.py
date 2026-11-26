"""Mass ledger for the replacement chamber and for the axial gate shift."""

from math import fsum, pi


STEEL_KG_MM3 = 7.85e-6
BASE_MACHINE_KG = 4942.65
BASE_CHAMBER_KG = 180.22
H2_KG = (5., 18.)
LIMIT_KG = 5000.


def gate_shift(roof_mm, stroke_add_mm, frame, cylinders):
    columns = frame["columns"]
    reference = {row["item"]: row["delta_kg"] for row in frame["mass_budget"]["delta_rows"]}
    # T-1.7d increased both longitudinal cylinders by 17 mm at fixed bores.
    # Its tube, rod, tie and oil increments are linear in installed stroke.
    rows_kg = {
        "four_smooth_columns": columns["quantity"] * pi / 4 * columns["smooth_span_diameter_mm"]**2
        * roof_mm * STEEL_KG_MM3,
        "main_cylinder_filled": reference["CY-MAIN"] / 17 * stroke_add_mm,
        "two_rapid_cylinders_filled": reference["CY-RAPID"] / 17 * stroke_add_mm,
        "translated_gate_cassette_and_plate": 0.,
    }
    return dict(rows_kg=rows_kg, delta_kg=fsum(rows_kg.values()),
                frame_axial_length_mm=frame["interfaces"]["layout"]["frame_axial_length_mm"] + roof_mm,
                bearing_planes_spacing_mm=frame["interfaces"]["inner_bearing_planes_spacing_mm"] + roof_mm,
                column_smooth_span_mm=columns["smooth_span_mm"] + roof_mm,
                column_smooth_span_diameter_mm=columns["smooth_span_diameter_mm"],
                main_cylinder_body_length_mm=647. + stroke_add_mm,
                rear_cover_thickness_mm=144.,
                rapid_cylinder_body_length_mm=cylinders["CY-RAPID"]["body_length_mm"] + stroke_add_mm,
                chamber_roof_and_cheeks_accounted_in_replacement=True)


def ledger(chamber_rows_kg, shift):
    chamber_kg = fsum(chamber_rows_kg.values())
    delta_kg = chamber_kg - BASE_CHAMBER_KG
    machine_kg = BASE_MACHINE_KG + delta_kg + shift["delta_kg"]
    return dict(chamber_rows_kg=chamber_rows_kg, chamber_kg=chamber_kg,
                reference_chamber_kg=BASE_CHAMBER_KG, delta_chamber_kg=delta_kg,
                reference_machine_kg=BASE_MACHINE_KG, gate_shift=shift,
                machine_kg=machine_kg, H2_increment_kg=list(H2_KG),
                machine_with_H2_kg=[machine_kg + h2 for h2 in H2_KG],
                station_reduction_kg=max(0., machine_kg - LIMIT_KG),
                station_reduction_with_H2_kg=[max(0., machine_kg + h2 - LIMIT_KG) for h2 in H2_KG])
