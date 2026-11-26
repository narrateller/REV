"""Mass ledger with traceable source rows, in kg."""

from math import fsum, pi

STEEL_KG_MM3 = 7.85e-6
REFERENCE_MACHINE_KG = 4942.65
REFERENCE_CHAMBER_KG = 180.22
H2_KG = (5., 18.)
LIMIT_KG = 5000.
TARGET_KG = 4900.


def annulus_mm2(inner_mm, outer_mm):
    return pi * (outer_mm**2 - inner_mm**2)


def ledger(rows_kg, shift):
    chamber_kg = fsum(rows_kg.values())
    delta_kg = chamber_kg - REFERENCE_CHAMBER_KG
    machine_kg = REFERENCE_MACHINE_KG + delta_kg + shift["delta_kg"]
    with_h2_kg = [machine_kg + increment_kg for increment_kg in H2_KG]
    return dict(
        chamber_rows_kg=rows_kg, chamber_kg=chamber_kg, delta_chamber_kg=delta_kg,
        reference_machine_kg=REFERENCE_MACHINE_KG, reference_chamber_kg=REFERENCE_CHAMBER_KG,
        gate_shift=shift, machine_kg=machine_kg, H2_increment_kg=list(H2_KG),
        machine_with_H2_kg=with_h2_kg,
        station_reduction_for_limit_kg=max(0., machine_kg - LIMIT_KG),
        station_reduction_for_limit_with_H2_kg=[max(0., mass - LIMIT_KG) for mass in with_h2_kg],
        station_reduction_for_target_with_H2_kg=[max(0., mass - TARGET_KG) for mass in with_h2_kg],
        station_reduction_D_GK_10_target_kg=40.,
        sources=dict(baseline_H2="ops/reports/T-2.2/GK_review.md",
                     replaced_chamber="calc/T-2.2d/mass.py",
                     gate_shift="calc/T-2.2d/results.json candidates/roof_mm=15/gate_shift",
                     original_chamber_rows="calc/T-2.2d/hand.py candidates",
                     revised_foot_and_box_rows="calc/T-2.2e/hand.py variant"),
    )
