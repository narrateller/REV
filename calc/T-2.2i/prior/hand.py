"""Transition load envelope retained from T-2.2g/prior/hand.py."""

from functools import lru_cache
from itertools import product
from math import exp, expm1
from pathlib import Path
import json

from .load import accepted_load, read_geometry, read_yaml

ROOT = Path(__file__).resolve().parents[3]
RATIO = 315 / 300


def distribute(force_N, centroid_x_mm, x1_mm, x2_mm):
    front = (centroid_x_mm-x1_mm)/(x2_mm-x1_mm)
    return force_N*(1-front), force_N*front


def top_load(force_N, K, mu, punch_mm, left_mm, right_mm):
    if left_mm >= right_mm:
        return dict(force_N=0., centroid_x_mm=None, peak_MPa=0., interval_mm=None)
    decay = K*mu*420/9000
    length_mm = right_mm-left_mm
    MPa = K*force_N/9000*exp(-decay*(left_mm-punch_mm))
    area_integral = -expm1(-decay*length_mm)/decay
    return dict(force_N=150*MPa*area_integral,
                centroid_x_mm=left_mm+1/decay-length_mm/expm1(decay*length_mm),
                peak_MPa=MPa, interval_mm=[left_mm,right_mm])


@lru_cache(maxsize=None)
def load_cases(roof_mm):
    """D-GK-10 maxima plus transfer and final compression over the material envelope."""
    base = accepted_load()
    transfer = json.loads((ROOT/"calc/T-2.2d/results.json").read_text(encoding="utf-8"))["transfer"]
    geom = read_geometry()
    curve = read_yaml("calc/T-1.1/curve.yaml")
    gate_mm = 205 + roof_mm
    length_limit_mm = base["loaded_limit_mm"]
    F315_N = base["cases"]["315_bar"]["punch_force_N"]
    width_mm, height_mm = base["section_mm"]
    rows = []
    for case, bulk_kg_m3 in product(transfer, (90,160)):
        dose_kg = transfer[case][str(bulk_kg_m3)]["upper"]["dose_kg"]
        material = geom.Material(curve, .83, [width_mm,height_mm])

        def pressure_MPa(length_mm):
            density_kg_m3 = dose_kg*1e9/(width_mm*height_mm*length_mm)
            return material.face_MPa(density_kg_m3, bulk_kg_m3, case, dose_kg=dose_kg)

        # Normalize each constitutive shape at the accepted 89.4 mm upper
        # length / 315 bar force pair. The profile is a screening envelope.
        p_end_MPa = pressure_MPa(length_limit_mm)
        retained_N = transfer[case][str(bulk_kg_m3)]["upper"]["retained_shoe_force_N"]
        # Rated service level; apply 315/300 conservatively also to transfer.
        rows.extend(dict(label="retained transfer", material_case=case, bulk_kg_m3=bulk_kg_m3,
                         K=None, mu=None, punch_mm=None, length_mm=200.,
                         main_force_N=None,
                         shoe=dict(force_N=retained_N*RATIO,
                                   centroid_x_mm=(end_mm-200.+205.)/2,
                                   peak_MPa=retained_N/30000, interval_mm=[end_mm-200,205.]),
                         roof=dict(force_N=0., centroid_x_mm=None, peak_MPa=0., interval_mm=None))
                    for end_mm in (205., gate_mm))
        for index in range(112):
            length_mm = length_limit_mm + (200-length_limit_mm)*index/111
            punch_mm = gate_mm-length_mm
            main_N = F315_N*pressure_MPa(length_mm)/p_end_MPa
            for K, mu in product((.35,.45,.60), (.20,.25,.30)):
                shoe = top_load(main_N, K, mu, punch_mm, max(5.,punch_mm), min(205.,gate_mm))
                roof = top_load(main_N, K, mu, punch_mm, max(205.,punch_mm), gate_mm)
                rows.append(dict(label="final" if index==0 else "compression", material_case=case,
                                 bulk_kg_m3=bulk_kg_m3, K=K, mu=mu, punch_mm=punch_mm,
                                 length_mm=length_mm, main_force_N=main_N, shoe=shoe, roof=roof))
    final = max((r for r in rows if r["label"] == "final"), key=lambda r: r["shoe"]["force_N"])
    # The D-GK-11 longitudinal load offset is an additional moment case.
    # For a partial roof, the actual residual length centroid can be larger.
    if final["shoe"]["force_N"]:
        rows.append(final | {"label":"D-GK-11 proof centroid",
                            "shoe":final["shoe"] | {"centroid_x_mm":165.2}})
    return rows


def extrema(rows, x1_mm, x2_mm):
    positive = [row for row in rows if row["shoe"]["force_N"] > 0]
    def reactions(row):
        shoe = row["shoe"]
        return distribute(shoe["force_N"],shoe["centroid_x_mm"],x1_mm,x2_mm)
    result = dict(shoe_final=max((r for r in rows if r["label"]=="final"), key=lambda r:r["shoe"]["force_N"]),
                  shoe_max=max(positive, key=lambda r:r["shoe"]["force_N"]),
                  roof_pressure=max(rows, key=lambda r:r["roof"]["peak_MPa"]),
                  roof_force=max(rows, key=lambda r:r["roof"]["force_N"]))
    for i, station in enumerate(("rear","front")):
        r = max(positive, key=lambda row:reactions(row)[i])
        result[station] = dict(case=r, force_315_N=reactions(r)[i])
        r = min(positive, key=lambda row:reactions(row)[i])
        result[station]["min_reaction_N"] = min(0.,reactions(r)[i])
        result[station]["min_case"] = r
    return result


