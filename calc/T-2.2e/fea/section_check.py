"""Integrate axial stress over actual tetrahedral shank sections."""

from argparse import ArgumentParser
from itertools import combinations
import json
from math import pi
from pathlib import Path

import numpy as np

from solve import (calculate, data_reactions, read_fields, read_mesh,
                   surfaces_and_profile)


SECTIONS_MM = (-60., -80., -105.)
EDGES = tuple(combinations(range(4), 2))
WEIGHTS = np.array(((2/3, 1/6, 1/6), (1/6, 2/3, 1/6), (1/6, 1/6, 2/3)))


def shape_functions(local):
    a, b, c, d = local.T
    return np.column_stack((a * (2*a - 1), b * (2*b - 1), c * (2*c - 1), d * (2*d - 1),
                            4*a*b, 4*b*c, 4*a*c, 4*a*d, 4*b*d, 4*c*d))


def integrate_section(xyz, elements, axial_MPa, z_mm):
    stress_force_N = 0.
    area_mm2 = 0.
    for _, nodes in elements:
        points = xyz[list(nodes[:4])]
        if not points[:, 2].min() <= z_mm < points[:, 2].max():
            continue
        crossings = []
        for i, j in EDGES:
            a, b = points[i], points[j]
            if min(a[2], b[2]) <= z_mm < max(a[2], b[2]):
                crossings.append(a + (b - a) * ((z_mm - a[2]) / (b[2] - a[2])))
        if not crossings:
            continue
        polygon = np.unique(np.round(np.asarray(crossings), decimals=9), axis=0)
        if len(polygon) < 3:
            continue
        centered = polygon[:, :2] - polygon[:, :2].mean(axis=0)
        polygon = polygon[np.argsort(np.arctan2(centered[:, 1], centered[:, 0]))]
        transform = (points[1:] - points[0]).T
        for i in range(1, len(polygon) - 1):
            tri = polygon[[0, i, i + 1]]
            tri_area_mm2 = abs(np.linalg.det(tri[1:, :2] - tri[0, :2])) / 2
            quadrature_mm = WEIGHTS @ tri
            bcd = np.linalg.solve(transform, (quadrature_mm - points[0]).T).T
            coordinates = np.column_stack((1 - bcd.sum(axis=1), bcd))
            values = shape_functions(coordinates) @ axial_MPa[list(nodes)]
            area_mm2 += tri_area_mm2
            stress_force_N += tri_area_mm2 * float(np.mean(values))
    return area_mm2, stress_force_N


def check(folder, station, fit_gap_mm, half):
    flat, groups = read_mesh(folder / "station.msh")
    xyz, _, _, _ = surfaces_and_profile(flat, groups, station, fit_gap_mm)
    states = read_fields(folder / "station.frd", len(xyz) + 1)
    if len(states) != 5:
        raise ValueError("The completed local series must have five output frames")
    reaction_N = abs(data_reactions(folder / "station.dat")["FIXED"][-1][2])
    analytic_area_mm2 = pi * station["shank_r_mm"]**2 / (2 if half else 1)
    analytic_MPa = reaction_N / analytic_area_mm2
    result = []
    for z in SECTIONS_MM:
        area_mm2, force_N = integrate_section(xyz, groups["POST"], states[-1]["STRESS"][:, 2], z)
        mean_MPa = force_N / area_mm2
        result.append(dict(
            section_z_relative_to_teeth_mm=z,
            section_z_in_assembly_mm=station["working_tooth_z_mm"] + z,
            reference_area_mm2=analytic_area_mm2, mesh_area_mm2=area_mm2,
            reference_reaction_N=reaction_N, integrated_tension_N=force_N,
            axial_stress_hand_MPa=analytic_MPa, axial_stress_FEA_mean_MPa=mean_MPa,
            stress_difference_fraction=abs(mean_MPa - analytic_MPa) / analytic_MPa,
            force_difference_fraction=abs(force_N - reaction_N) / reaction_N,
        ))
    return result


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--case", action="append", nargs=3, metavar=("STATION", "MESH_MM", "SCRATCH"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    selected = calculate()[0]["selected"]
    rows = []
    for label, mesh_mm, directory in args.case:
        station = selected["stations"][label]
        gap_mm = selected["support_checks"][label]["worst_fit_gap_mm"]
        checks = check(Path(directory), station, gap_mm, True)
        rows.append(dict(station=label, mesh_mm=float(mesh_mm), sections=checks))
        print(label, mesh_mm, [round(100*row["stress_difference_fraction"], 3) for row in checks])
    if args.out:
        args.out.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")

