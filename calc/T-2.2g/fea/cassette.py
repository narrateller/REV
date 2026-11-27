"""Replay the unchanged D-GK-05 pair at the T-2.2g gate-thrust envelope."""

from argparse import ArgumentParser
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
from hand import SHORTEST_LOADED_MM
from loads import janssen, main_cylinder_force_N, read_yaml
from solver import quad

REFERENCE = ROOT / "calc/T-1.7d/fea"
sys.path.insert(0, str(REFERENCE))
import frame_analytic
import submodel

base_describe = submodel.describe_load


def describe(parts, dataset, p_MPa, cut_tags, force_N):
    values = base_describe(parts, dataset, p_MPa, cut_tags, force_N)
    for name, surface in (("blade_seat", "front"), ("seat_cast", "back")):
        part = parts["seat"]
        strips = {label: [0., 0.] for label in ("lower", "upper", "left", "right")}
        face_radius_y_mm = 36. if name == "seat_cast" else 34.5
        for face in part[surface]:
            pressure_MPa = p_MPa[face + part["offset"]]
            for shape, point, vector_mm2 in quad(part["xyz"][face]):
                x_mm,y_mm,_ = point
                band = ("lower" if y_mm < -face_radius_y_mm else "upper" if y_mm > face_radius_y_mm
                        else "left" if x_mm < 0 else "right")
                area_mm2 = np.linalg.norm(vector_mm2)
                strips[band][0] += float(area_mm2)
                strips[band][1] += max(0., float(shape @ pressure_MPa)) * area_mm2
        values[name]["face_strip_means"] = {
            band: {"area_mm2": area, "quadrature_normal_N": load,
                   "mean_MPa": load / area if area else None}
            for band, (area, load) in strips.items()
        }
    return values


def main():
    parser = ArgumentParser()
    parser.add_argument("levels", nargs="+", type=int, choices=range(6))
    parser.add_argument("--label", default="t22g")
    parser.add_argument("--iterative",action="store_true")
    args = parser.parse_args()
    if not args.label.replace("_", "").isalnum():
        parser.error("Label must use letters, digits and underscores.")
    project = read_yaml("design/slide_gate.t17d.yaml")
    trial = {"thickness_mm": project["thickness_mm"], "travel_mm": project["opening_travel_mm"],
             "wing_mm": project["axial_wing_height_mm"], "runout_length_mm": project["insert_relief_length_mm"],
             "runout_depth_mm": project["insert_relief_depth_mm"]}
    max_gate_N = janssen(main_cylinder_force_N(315), .35, .20, SHORTEST_LOADED_MM)["gate_force_N"]
    submodel.HERE = HERE
    submodel.base.STATIC_N = max_gate_N
    submodel.base.CYCLIC_N = max_gate_N * 300 / 315
    frame_analytic.MID_SPAN_mm += 90.
    submodel.describe_load = describe
    submodel.solve(trial, f"r2_aligned_{args.label}_replay", args.levels, False, False, "NODE SMALL", not args.iterative)


if __name__ == "__main__":
    main()

