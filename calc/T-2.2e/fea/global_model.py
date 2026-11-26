"""Linear shell-and-spring model of the complete vertical load path.

Nodes follow the assumed trapezoidal box outlines. The support laws are
secants at 300 bar. This model supplies seat movements and load split for
local contact work. It does not resolve the flange-to-box transitions.
"""

from argparse import ArgumentParser
from collections import defaultdict
from copy import deepcopy
from math import ceil, exp, hypot
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from scipy.optimize import brentq

from solve import read_fields, tool
from hand import calculate, prior

MESHES_MM = (14., 10., 7.)
LAND_ATTACH_MM = 40.
HEEL_SURROUND_MM = 12.
PRODUCT_HALF_WIDTH_MM = 75.
CORNER_IJ = ((0, 0), (1, 0), (1, 1), (0, 1))
QUADRATURE, WEIGHTS = np.polynomial.legendre.leggauss(3)


def band_coordinates(sections_mm, step_mm):
    anchors = sorted(set(sections_mm))
    return np.concatenate([np.linspace(a, b, max(1, ceil((b - a) / step_mm)), endpoint=False)
                           for a, b in zip(anchors, anchors[1:])] + [anchors[-1:]])


class Model:
    def __init__(self):
        self.xyz = [(0., 0., 0.)]
        self.elements = defaultdict(list)
        self.forces_N = defaultdict(float)
        self.springs = {}
        self.support_pairs = {}
        self.probes = {}
        self.thickness_mm = {}
        self.offset = {}
        self.equations = []
        self.constraints = []

    def add_node(self, point):
        self.xyz.append(tuple(float(x) for x in point))
        return len(self.xyz) - 1

    def panel(self, name, a):
        for i in range(a.shape[0] - 1):
            for j in range(a.shape[1] - 1):
                self.elements[name].append(tuple(int(a[i + di, j + dj]) for di, dj in CORNER_IJ))

    def make_box(self, name, selected, x_mm, webs, z_mm, thickness_mm, step_mm):
        rear, front = (selected["stations"][label] for label in ("rear", "front"))

        def half_span_mm(x):
            return float(np.interp(x, [rear["x_mm"], front["x_mm"]], [rear["y_mm"], front["y_mm"]]))

        n_mid = max(2, 2 * ceil(PRODUCT_HALF_WIDTH_MM / step_mm))
        n_out = ceil((front["y_mm"] - PRODUCT_HALF_WIDTH_MM) / step_mm)
        n_y = 2 * n_out + n_mid + 1
        nodes = np.zeros((2, len(x_mm), n_y), dtype=int)
        for i, x in enumerate(x_mm):
            half_mm = half_span_mm(x)
            y_mm = np.r_[np.linspace(-half_mm, -PRODUCT_HALF_WIDTH_MM, n_out, endpoint=False),
                         np.linspace(-PRODUCT_HALF_WIDTH_MM, PRODUCT_HALF_WIDTH_MM, n_mid, endpoint=False),
                         np.linspace(PRODUCT_HALF_WIDTH_MM, half_mm, n_out + 1)]
            for k, z in enumerate(z_mm):
                nodes[k, i] = [self.add_node((x, y, z)) for y in y_mm]
        width = PRODUCT_HALF_WIDTH_MM
        if name == "SHOE":
            band_limits_mm, extra_mm, direction = (5., 205.), 35., -1
        else:
            band_limits_mm = selected["floor_local_band"]["x_interval_mm"]
            extra_mm, direction = selected["floor_local_band"]["extra_mm"], -1
        band_name = name + "_BAND"
        for i in range(nodes.shape[1] - 1):
            for j in range(nodes.shape[2] - 1):
                this_band = (extra_mm > 0 and band_limits_mm[0] <= x_mm[i]
                             and x_mm[i + 1] <= band_limits_mm[1]
                             and self.xyz[nodes[0, i, j]][1] >= -width - 1e-7
                             and self.xyz[nodes[0, i+1, j+1]][1] <= width + 1e-7)
                target = band_name if this_band else name + "_SKIN"
                self.panel(target, nodes[0, i:i+2, j:j+2])
        self.panel(name + "_SKIN", nodes[1])
        if extra_mm:
            self.thickness_mm[band_name] = thickness_mm + extra_mm
            self.offset[band_name] = -direction * extra_mm / (2 * (thickness_mm + extra_mm))
        self.thickness_mm[name + "_SKIN"] = thickness_mm
        for index, (x, web_mm, half_local_mm) in enumerate(webs):
            i = int(np.argmin(abs(x_mm - x)))
            web = name + f"_WEB_{index}"
            panel = nodes[:, i]
            if half_local_mm is not None:
                y = np.array([self.xyz[tag][1] for tag in panel[0]])
                left = int(np.argmin(abs(y + half_local_mm)))
                right = int(np.argmin(abs(y - half_local_mm)))
                panel = panel[:, left:right + 1]
            self.panel(web, panel)
            shell_h_mm = abs(z_mm[1] - z_mm[0])
            self.thickness_mm[web] = web_mm * (shell_h_mm - thickness_mm) / shell_h_mm
        if name == "FLOOR":
            for j in (0, -1):
                self.panel(name + "_END", nodes[:, :, j])
            self.thickness_mm[name + "_END"] = 16.
        return nodes

    def add_pressure(self, ids, start_x_mm, end_x_mm, y_decay_mm_inv, x_decay_mm_inv, target_N):
        xyz = np.asarray(self.xyz)
        nodal = defaultdict(float)
        for i in range(ids.shape[0] - 1):
            for j in range(ids.shape[1] - 1):
                tags = [int(ids[i + di, j + dj]) for di, dj in CORNER_IJ]
                q = xyz[tags, :2]
                if (q[0, 0] < start_x_mm - 1e-7 or q[1, 0] > end_x_mm + 1e-7
                    or q[0, 1] < -PRODUCT_HALF_WIDTH_MM - 1e-7 or q[2, 1] > PRODUCT_HALF_WIDTH_MM + 1e-7):
                    continue
                area_mm2 = (q[1, 0] - q[0, 0]) * (q[3, 1] - q[0, 1])
                for a, wa in zip(QUADRATURE, WEIGHTS):
                    for b, wb in zip(QUADRATURE, WEIGHTS):
                        shape = np.array([(1-a)*(1-b), (1+a)*(1-b), (1+a)*(1+b), (1-a)*(1+b)]) / 4
                        x, y = shape @ q
                        v = exp(y_decay_mm_inv * y - x_decay_mm_inv * (x - start_x_mm)) * area_mm2 * wa * wb / 4
                        for node, value in zip(tags, shape * v):
                            nodal[node] += value
        scale = target_N / sum(nodal.values())
        for node, load in nodal.items():
            self.forces_N[node] += float(load * scale)
        p = np.array(list(nodal.values()))
        return (p @ xyz[list(nodal), :2] / p.sum()).tolist()

    def make(self, selected, roof, step_mm, side_share, rigid_lands):
        peak = roof["load"]["315_bar"]["peak"]
        start_x_mm, end_x_mm = peak["shoe_contact_x_mm"]
        roof_x_mm = end_x_mm + roof["roof_mm"]
        x_c_mm = peak["centroid_x_mm"]
        front = selected["stations"]["front"]
        rear = selected["stations"]["rear"]
        roof_center_mm = end_x_mm + 1 / peak["decay_per_mm"] - roof["roof_mm"] / (
            exp(peak["decay_per_mm"] * roof["roof_mm"]) - 1)
        stations_x_mm = [rear["x_mm"], front["x_mm"]]
        upper_web_mm, lower_web_mm = selected["shoe_four_webs_each_mm"], selected["floor_four_webs_each_mm"]
        upper = [(x, upper_web_mm, None) for x in (5 + upper_web_mm / 2, rear["x_mm"], 144., front["x_mm"])]
        lower = [(x, lower_web_mm, None) for x in (rear["x_mm"], 128., 171., 211.)]
        diagnostic = selected.get("fea_web_sensitivity", {})
        for ribs, tag, short_x in ((upper, "upper", 165.), (lower, "lower", 158.)):
            split_mm = diagnostic.get(tag, 0.)
            if split_mm:
                x, web_mm, _ = ribs[0]
                ribs[0] = (x, web_mm - split_mm, None)
                ribs.append((short_x, split_mm, rear["y_mm"]))
        top_x_mm = band_coordinates([5., *stations_x_mm, *(w[0] for w in upper), start_x_mm, x_c_mm, end_x_mm], step_mm)
        floor_x_mm = band_coordinates([-35., *stations_x_mm, *(w[0] for w in lower), start_x_mm, x_c_mm, end_x_mm,
                                      roof_center_mm, roof_x_mm, *selected["floor_local_band"]["x_interval_mm"], 245.], step_mm)
        top_skin_mm, floor_skin_mm = selected["shoe_skin_mm"], selected["floor_skin_mm"]
        shoe = self.make_box("SHOE", selected, top_x_mm, upper,
                             (95. + top_skin_mm / 2, 95. + selected["shoe_h_mm"] - top_skin_mm / 2),
                             top_skin_mm, step_mm)
        floor = self.make_box("FLOOR", selected, floor_x_mm, lower,
                              (-floor_skin_mm / 2, -selected["floor_h_mm"] + floor_skin_mm / 2),
                              floor_skin_mm, step_mm)
        # Match the 64/36 transverse design split in the hand model via an
        # always positive pressure distribution on the 150 mm product face.
        y_target_mm = (2 * side_share - 1) * np.interp(
            x_c_mm, stations_x_mm, [rear["y_mm"], front["y_mm"]])
        yi = np.linspace(-PRODUCT_HALF_WIDTH_MM, PRODUCT_HALF_WIDTH_MM, 10001)
        y_decay = (brentq(lambda t: yi @ np.exp(t * yi) / np.sum(np.exp(t * yi)) - y_target_mm, 0, .1)
                   if y_target_mm else 0.)
        shoe_force_N = peak["shoe_force_N"]
        roof_force_N = peak["roof_force_N"]
        decay = peak["decay_per_mm"]
        upper_centroid_mm = self.add_pressure(shoe[0], start_x_mm, end_x_mm, y_decay, decay, shoe_force_N)
        self.add_pressure(floor[0], start_x_mm, end_x_mm, y_decay, decay, -shoe_force_N)
        roof_centroid_mm = self.add_pressure(floor[0], end_x_mm, roof_x_mm, y_decay, decay, -roof_force_N)

        # The 15 mm closed roof returns its load through both wall bases.
        # Enter the same first moments as the distributed load on the floor.
        i = int(np.argmin(abs(floor_x_mm - roof_center_mm)))
        near_x = [i, i + (1 if roof_centroid_mm[0] >= floor_x_mm[i] else -1)]
        x_weight = ((roof_centroid_mm[0] - floor_x_mm[near_x[0]])
                    / (floor_x_mm[near_x[1]] - floor_x_mm[near_x[0]]))
        for k, weight in zip(near_x, (1 - x_weight, x_weight)):
            pair = [int(floor[0, k, 0]), int(floor[0, k, -1])]
            half_mm = self.xyz[pair[1]][1]
            positive = (1 + roof_centroid_mm[1] / half_mm) / 2
            self.forces_N[pair[0]] += roof_force_N * weight * (1 - positive)
            self.forces_N[pair[1]] += roof_force_N * weight * positive

        for label, station_x_mm in zip(("rear", "front"), stations_x_mm):
            j_top = int(np.argmin(abs(top_x_mm - station_x_mm)))
            j_floor = int(np.argmin(abs(floor_x_mm - station_x_mm)))
            row = selected["support_checks"][label]
            delta = sum(row[key] for key in ("post_extension_300_mm", "tooth_branches_300_mm",
                                             "pad_compression_300_mm", "foot_compression_allowance_300_mm"))
            stiffness_N_mm = row["force_315_N"] / prior.RELIEF_RATIO / delta
            stiffness_N_mm = selected.get("fea_secant_stiffness_N_mm", {}).get(label, stiffness_N_mm)
            for side, edge in (("left", 0), ("right", -1)):
                pair = int(shoe[0, j_top, edge]), int(floor[0, j_floor, edge])
                self.support_pairs[f"{label}_{side}"] = pair
                self.springs[label] = stiffness_N_mm
                self.equations.extend((pair, axis) for axis in (1, 2))
                if rigid_lands:
                    geo = selected["stations"][label]
                    upper_band = (geo["head_r_mm"] + 1., geo["outer_envelope_r_mm"])
                    lower_band = (geo["shank_r_mm"] + 16., geo["foot_r_mm"] + HEEL_SURROUND_MM)
                    if rigid_lands == "disk":
                        upper_band = lower_band = (0., LAND_ATTACH_MM)
                    for reference, skin, (inner_mm, outer_mm) in zip(pair, (shoe[0], floor[0]),
                                                                    (upper_band, lower_band)):
                        rx, ry, _ = self.xyz[reference]
                        for tag in skin.flat:
                            x, y, _ = self.xyz[tag]
                            if tag != reference and inner_mm - 1e-7 <= hypot(x - rx, y - ry) <= outer_mm + 1e-7:
                                self.equations.append(((int(tag), reference), 3))

        indices = [int(np.argmin(abs(values - x_c_mm))) for values in (top_x_mm, floor_x_mm)]
        for j, name in enumerate(("negative_edge", "center", "positive_edge")):
            pair = []
            for box, i in zip((shoe, floor), indices):
                row = box[0, i]
                y_mm = (-PRODUCT_HALF_WIDTH_MM, 0, PRODUCT_HALF_WIDTH_MM)[j]
                pair.append(min(row, key=lambda tag: abs(self.xyz[tag][1] - y_mm)))
            self.probes[name] = pair
        self.constraints = [(floor[1, 0, 0], 1, 3), (floor[1, -1, 0], 2, 3), (floor[1, 0, -1], 3, 3)]
        for key, pair in self.probes.items():
            assert abs(self.xyz[pair[0]][0] - self.xyz[pair[1]][0]) < 1e-8, key
        applied_force_N = sum(self.forces_N.values())
        moment_Nmm = np.array(list(self.forces_N.values())) @ np.array([self.xyz[tag][:2] for tag in self.forces_N])
        return dict(shoe_pressure_centroid_xy_mm=upper_centroid_mm, roof_pressure_centroid_xy_mm=roof_centroid_mm,
                    total_applied_force_N=applied_force_N, total_applied_first_moments_Nmm=moment_Nmm.tolist())

    def deck(self, path):
        rows = ["*HEADING", "REV bayonet linear diagnostic N mm MPa", "*NODE"]
        rows.extend(f"{i},{x:.12g},{y:.12g},{z:.12g}" for i, (x, y, z) in enumerate(self.xyz[1:], 1))
        number = 1
        for name, elements in self.elements.items():
            rows.append(f"*ELEMENT,TYPE=S4,ELSET={name}")
            for nodes in elements:
                rows.append(f"{number}," + ",".join(map(str, nodes)))
                number += 1
        for label, stiffness in self.springs.items():
            spring = f"SPRING_{label}"
            rows.append(f"*ELEMENT,TYPE=SPRING2,ELSET={spring}")
            for name, (top, bottom) in self.support_pairs.items():
                if name.startswith(label):
                    rows.append(f"{number},{top},{bottom}")
                    number += 1
            rows += [f"*SPRING,ELSET={spring}", "3,3", f"{stiffness:.12g}"]
        rows += ["*MATERIAL,NAME=STEEL", "*ELASTIC", f"{prior.E_MPa},{prior.NU}"]
        for name, thickness_mm in self.thickness_mm.items():
            offset = self.offset.get(name, 0.)
            rows += [f"*SHELL SECTION,ELSET={name},MATERIAL=STEEL,OFFSET={offset:.12g}", f"{thickness_mm:.12g}"]
        rows.append("*BOUNDARY")
        rows.extend(f"{node},{a},{b}" for node, a, b in self.constraints)
        rows.append("*EQUATION")
        for (top, bottom), axis in self.equations:
            rows += ["2", f"{top},{axis},1.,{bottom},{axis},-1."]
        rows += ["*STEP", "*STATIC", "1.,1.", "*CLOAD"]
        rows.extend(f"{node},3,{force:.12g}" for node, force in sorted(self.forces_N.items()))
        rows += ["*NODE FILE,OUTPUT=2D", "U,RF", "*END STEP"]
        path.write_text("\n".join(rows) + "\n", encoding="ascii", newline="\n")

    def post(self, state, selected):
        us = state["DISP"][:, 2]
        spans = {name: float((us[top] - us[bottom]) / prior.RELIEF_RATIO + .020)
                 for name, (top, bottom) in self.probes.items()}
        supports = {}
        for name, (top, bottom) in self.support_pairs.items():
            movement_mm = float(us[top] - us[bottom])
            force_N = movement_mm * self.springs[name.split("_")[0]]
            supports[name] = dict(local_opening_315_mm=movement_mm, support_force_315_N=force_N,
                                  upper_axial_315_mm=float(us[top]), lower_axial_315_mm=float(us[bottom]))
        constraints = [state["FORC"][node].tolist() for node, _, _ in self.constraints]
        rear, front = (selected["stations"][name] for name in ("rear", "front"))
        contributors = {}
        for name, (top, bottom) in self.probes.items():
            x, y, _ = self.xyz[top]
            front_weight = (x - rear["x_mm"]) / (front["x_mm"] - rear["x_mm"])
            interpolated = [0., 0.]
            for label, station, weight in (("rear", rear, 1 - front_weight), ("front", front, front_weight)):
                positive_weight = (1 + y / station["y_mm"]) / 2
                left, right = (self.support_pairs[label + suffix] for suffix in ("_left", "_right"))
                for k in (0, 1):
                    interpolated[k] += weight * ((1 - positive_weight) * us[left[k]] + positive_weight * us[right[k]])
            contributors[name] = dict(
                crosshead_mm=float((us[top] - interpolated[0]) / prior.RELIEF_RATIO),
                bottom_box_mm=float((interpolated[1] - us[bottom]) / prior.RELIEF_RATIO),
                supports_and_seating_mm=float((interpolated[0] - interpolated[1]) / prior.RELIEF_RATIO + .020),
            )
        return dict(delta_height_300_mm=spans, maximum_delta_height_300_mm=max(spans.values()),
                    support_relative_deflection_300_mm=contributors,
                    supports=supports, reference_constraint_forces_N=constraints,
                    support_vertical_force_error_fraction=abs(sum(r["support_force_315_N"] for r in supports.values())
                      - self.exact_shoe_force_N) / self.exact_shoe_force_N)


def calculate_global(selected, roof, side_share, rigid_lands=False, meshes_mm=MESHES_MM):
    results = []
    temp_home = Path(__file__).resolve().parent
    with TemporaryDirectory(dir=temp_home, prefix="global_scratch_") as scratch:
        for mesh_mm in meshes_mm:
            folder = Path(scratch) / str(mesh_mm)
            folder.mkdir()
            model = Model()
            model.exact_shoe_force_N = roof["load"]["315_bar"]["peak"]["shoe_force_N"]
            input_check = model.make(selected, roof, mesh_mm, side_share, rigid_lands)
            model.deck(folder / "boxes.inp")
            code = tool("ccx.exe", ["-i", "boxes"], folder, "ccx.log", 150)
            row = dict(mesh_mm=mesh_mm, assumed_side_share=side_share, land_model=rigid_lands or "point", node_count=len(model.xyz) - 1, input_check=input_check, ccx_code=code)
            if code == 0:
                states = read_fields(folder / "boxes.frd", len(model.xyz))
                row["results"] = model.post(states[-1], selected)
            else:
                row["error"] = (folder / "ccx.log").read_text(encoding="ascii", errors="replace").splitlines()[-15:]
            results.append(row)
    return results


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--sensitivity", action="store_true")
    parser.add_argument("--contact-fit", action="append", type=Path, default=[])
    options = parser.parse_args()
    hand, roof, _ = calculate()
    selected = hand["selected"]
    if options.sensitivity:
        out = {}
        for name, settings in (("baseline", {}), ("split_shoe_web", {"upper": 8.}),
                               ("split_floor_web", {"lower": 8.}), ("both_split_webs", {"upper": 8., "lower": 8.})):
            trial = selected | {"fea_web_sensitivity": settings}
            out[name] = calculate_global(trial, roof, prior.SIDE_SHARE, "annular", (10.,))
        if options.contact_fit:
            stiffness = {}
            for path in options.contact_fit:
                trial_rows = json.loads(path.read_text(encoding="utf-8"))
                trial = next(row for row in reversed(trial_rows) if row["status"] == "SOLVED_DISPLACEMENT_TRIAL")
                work = trial["steps"][-2]
                scale = 2 if trial["half_symmetry"] else 1
                stiffness[trial["station"]] = scale * abs(work["cast_reaction_N"]) / work["sleeve_up_mm"]
            local_model = deepcopy(selected)
            local_model["fea_secant_stiffness_N_mm"] = stiffness
            out["local_contact_secants"] = calculate_global(local_model, roof, prior.SIDE_SHARE, "annular", (10.,))
            out["local_contact_secants"][0]["secants_N_mm"] = stiffness
    else:
        out = {name: calculate_global(selected, roof, share, lands)
               for name, share, lands in (("uniform", .5, "annular"), ("skew_screen", prior.SIDE_SHARE, "annular"),
                                          ("skew_disk_support", prior.SIDE_SHARE, "disk"),
                                          ("skew_point_support", prior.SIDE_SHARE, False))}
    dump = json.dumps(out, indent=2, allow_nan=False) + "\n"
    if options.out:
        options.out.write_text(dump, encoding="utf-8", newline="\n")
    for name, rows in out.items():
        print(name, [(r["mesh_mm"], r.get("results", {}).get("maximum_delta_height_300_mm")) for r in rows])

