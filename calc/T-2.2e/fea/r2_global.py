"""Three-dimensional elastic box model with deformable annular seating faces.

The relative mean displacements of the seating faces drive a station spring.
The same area weights distribute its axial force back to the solids. No nodes
of either face are constrained to move together.
"""
from argparse import ArgumentParser
from dataclasses import asdict
import json
from math import pi, sqrt
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from subprocess import TimeoutExpired

import numpy as np
from scipy.optimize import brentq

from solve import boundary, interpolate_tet10, mises_MPa, read_fields, read_mesh, tool
from hand import prior, input_data
from mass import STEEL_KG_MM3, ledger
from r2_geometry import CASES, SHOE_Z_MM, make_geo, seat_levels, station_data
from r2_sections import hand_comparison

HERE = Path(__file__).resolve().parent
PRESSURES_BAR = (0, 100, 200, 300, 315)
MATERIAL = (650., 800., True)
GAUSS, WEIGHTS = np.polynomial.legendre.leggauss(5)
GAUSS, WEIGHTS = (GAUSS + 1) / 2, WEIGHTS / 2
NAMES = {1: "SHOE", 2: "FLOOR"}


def clip(poly, axis, limit_mm, direction):
    if len(poly) == 0:
        return poly
    result = []
    start = poly[-1]
    for end in poly:
        da = direction * (start[axis] - limit_mm)
        db = direction * (end[axis] - limit_mm)
        if (da < 0) != (db < 0):
            result.append(start + (end - start) * da / (da - db))
        if db >= 0:
            result.append(end)
        start = end
    return result


def weights_at(a, b, c):
    return np.stack((a*(2*a-1), b*(2*b-1), c*(2*c-1), 4*a*b, 4*b*c, 4*c*a), axis=-1)


R, S = np.meshgrid(GAUSS, GAUSS)
QR = np.array([((1-R)*(1-S)).ravel(), R.ravel(), ((1-R)*S).ravel()]).T
QW = (np.outer(WEIGHTS, WEIGHTS) * (1 - R)).ravel()


def surface_load(faces, xyz, bounds, decay, target):
    x0, x1, y0, y1 = bounds
    nodal = np.zeros(len(xyz))
    for _, _, tags in faces:
        tri = xyz[list(tags[:3]), :2]
        if np.any(tri.max(axis=0) <= (x0, y0)) or np.any(tri.min(axis=0) >= (x1, y1)):
            continue
        area2 = abs(np.linalg.det(tri[1:] - tri[:1]))
        if area2 < 1e-11:
            continue
        polygon = list(tri)
        for axis, limit, direction in ((0, x0, 1), (0, x1, -1), (1, y0, 1), (1, y1, -1)):
            polygon = clip(polygon, axis, limit, direction)
        for i in range(1, len(polygon) - 1):
            sub = np.array([polygon[0], polygon[i], polygon[i+1]])
            area2sub = abs(np.linalg.det(sub[1:] - sub[:1]))
            if area2sub < 1e-11:
                continue
            points = QR @ sub
            bc = np.linalg.solve((tri[1:] - tri[:1]).T, (points - tri[0]).T)
            shape = weights_at(1 - bc.sum(axis=0), *bc)
            pressure = np.exp(decay[0] * (points[:, 0] - x0) + decay[1] * points[:, 1])
            nodal[list(tags)] += (QW * pressure * area2sub) @ shape
    if not np.any(nodal):
        raise ValueError(f"Load footprint absent {bounds}")
    nodal *= target / nodal.sum()
    return nodal


def horizontal(faces, xyz, z_mm):
    return [face for face in faces if np.all(abs(xyz[list(face[2]), 2] - z_mm) < 1e-5)]


def seat_weights(xyz, faces, center, inner, outer):
    tags = np.asarray([f[2] for f in faces])
    radii = np.linalg.norm(xyz[tags, :2] - center, axis=2)
    centroid_r = np.linalg.norm(xyz[tags[:, :3], :2].mean(axis=1) - center, axis=1)
    tags = tags[(radii.min(axis=1) > inner - 3.) & (radii.max(axis=1) < outer + .05)
                & (centroid_r > inner - 1.) & (centroid_r < outer)]
    a, b, c = [xyz[tags[:, i], :2] for i in range(3)]
    areas_mm2 = abs((b[:, 0]-a[:, 0]) * (c[:, 1]-a[:, 1]) - (b[:, 1]-a[:, 1]) * (c[:, 0]-a[:, 0])) / 2
    weight = np.zeros(len(xyz))
    for i in (3, 4, 5):
        np.add.at(weight, tags[:, i], areas_mm2 / 3.)
    used = np.flatnonzero(weight)
    if not len(used):
        raise ValueError(f"Empty ring {center}, {inner}, {outer}")
    normalized = weight[used] / weight.sum()
    # Correct the first moments lost by faceting. Positive weights and the
    # uniform-pressure virtual work are preserved to quadrature precision.
    offsets = (xyz[used, :2] - center) / outer
    basis = np.column_stack((np.ones(len(used)), offsets))
    correction = np.linalg.solve(basis.T @ (normalized[:, None] * basis), [1., 0., 0.])
    return used, normalized * (basis @ correction), weight.sum()


def sample_face(faces, xyz, points):
    tri = np.asarray([xyz[list(f[2][:3]), :2] for f in faces])
    out = []
    for x, y in points:
        target = np.array([x, y])
        for coords, face in zip(tri, faces):
            if np.any(target < coords.min(axis=0) - 1e-8) or np.any(target > coords.max(axis=0) + 1e-8):
                continue
            b, c = np.linalg.solve((coords[1:] - coords[:1]).T, target - coords[0])
            if min(b, c, 1-b-c) >= -1e-7:
                out.append((np.asarray(face[2]), weights_at(1-b-c, b, c)))
                break
        else:
            raise ValueError(f"Point outside surface {(x,y)}")
    return out


def station_spring(check):
    # Round-one local contact secants include their own compliant cast cut.
    # Use the manual post, teeth and toe terms for global coupling. The
    # annular body in this model already accounts for the cast seat.
    names = ("post_extension_300_mm", "tooth_branches_300_mm", "pad_compression_300_mm")
    compliance = sum(check[n] for n in names) * prior.RELIEF_RATIO / check["force_315_N"]
    return 1 / compliance


def mass_of(stations, shift, volumes_mm3, accepted):
    rows = dict(accepted["chamber_rows_kg"])
    for key in ("moving_crosshead", "bottom_cast_box", "bottom_end_diaphragms",
                "cast_floor_thickening", "closed_roof_and_side_haunches"):
        rows.pop(key)
    parts, _ = prior.part_volumes(stations)
    for label in ("front", "rear"):
        station = stations[label]
        # Round one already accounted for the enlarged feet. Recompute the
        # same forged blanks at the trial dimensions.
        parts[f"{label}_integral_feet_two"] = 2 * pi * (station["foot_r_mm"]**2 - station["shank_r_mm"]**2) * 28.
        parts.pop(f"{label}_carrier_lands")
        rows.pop(f"{label}_carrier_lands")
    rows.update({key: volume * STEEL_KG_MM3 for key, volume in parts.items()})
    rows["moving_crosshead_including_ring_seats"] = volumes_mm3["SHOE"] * STEEL_KG_MM3
    rows["bottom_box_including_ring_seats_and_roof"] = volumes_mm3["FLOOR"] * STEEL_KG_MM3
    result = ledger(rows, shift)
    result["sources"]["updated_box_and_support_rows"] = "r2_geometry.py exact OCC volumes; T-2.2d part_volumes"
    result["accepted_round_one_station_reduction_kg"] = accepted["station_reduction_for_limit_with_H2_kg"]
    return result


def model_data(xyz, groups, layout, stations, checks, peak, y_c_mm, audit):
    faces = boundary(groups)
    shoe = horizontal(faces["SHOE"], xyz, SHOE_Z_MM)
    floor = horizontal(faces["FLOOR"], xyz, 0.)
    roof = horizontal(faces["FLOOR"], xyz, 60.)
    start, end = peak["shoe_contact_x_mm"]
    x_c = peak["centroid_x_mm"]
    lam = peak["decay_per_mm"]
    terms, gauss_w = np.polynomial.legendre.leggauss(32)
    y = terms * 75.
    skew = brentq(lambda t: (gauss_w * np.exp(t*y)) @ y / (gauss_w @ np.exp(t*y)) - y_c_mm, 0., .25)
    shoe_bounds = (start, end, -75., 75.)
    roof_bounds = (end, end + 15., -75., 75.)
    shoe_N, roof_N = peak["shoe_force_N"], peak["roof_force_N"]
    upper = surface_load(shoe, xyz, shoe_bounds, (-lam, skew), shoe_N)
    lower = surface_load(floor, xyz, shoe_bounds, (-lam, skew), -shoe_N)
    lower += surface_load(floor, xyz, roof_bounds, (-lam, skew), -roof_N)
    lower += surface_load(roof, xyz, roof_bounds, (-lam, skew), roof_N)
    shoes_all = sorted({n for _, row in groups["SHOE"] for n in row})
    floor_all = sorted({n for _, row in groups["FLOOR"] for n in row})
    assert not (set(shoes_all) & set(floor_all))
    assert np.max(abs((upper + lower) @ xyz[:, :2])) / (shoe_N * 100) < .0001
    assert np.max(abs(upper @ xyz[:, :2] / shoe_N - [x_c, y_c_mm])) < .001
    seats = {}
    shoulder_mm, heel_mm = seat_levels(layout)
    for name, station in stations.items():
        for side, sign in (("left", -1), ("right", 1)):
            center = np.array([station["x_mm"], sign * station["y_mm"]])
            top = seat_weights(xyz, horizontal(faces["SHOE"], xyz, shoulder_mm), center,
                               station["head_r_mm"] + (3. if layout.close_seats else 1.), station["collar_r_mm"] + .51)
            bottom = seat_weights(xyz, horizontal(faces["FLOOR"], xyz, heel_mm), center,
                                  station["shank_r_mm"] + 16., station["foot_r_mm"] + .51)
            seats[name + "_" + side] = (top, bottom, station_spring(checks[name]))
    dims = [(x, yy) for x in sorted(set([float(x_c), *np.linspace(start, end, 17)]))
            for yy in np.linspace(-75., 75., 31)]
    probe = {}
    for body, fr, z in (("shoe", shoe, 63.), ("floor", floor, -3.)):
        attached = "SHOE" if body == "shoe" else "FLOOR"
        points = [(x, y, z) for x in (146., x_c, 188.) for y in (0., 55., 72., 82.)]
        if body == "shoe":
            points += [(144., 62., 60. + layout.top_depth_mm - 3.),
                       (187., 62., 60. + layout.top_depth_mm - 3.)]
        else:
            points += [(144., 62., -layout.base_depth_mm + 3.),
                       (187., 62., -layout.base_depth_mm + 3.),
                       (212.5, 0., 63.), (212.5, 62., 63.)]
        if audit and layout.through_ring:
            for name, station in stations.items():
                x, y = station["x_mm"], station["y_mm"]
                if body == "shoe":
                    r = (station["collar_r_mm"] + .5 + station["outer_envelope_r_mm"]) / 2
                    levels = (shoulder_mm + 25., SHOE_Z_MM + layout.top_depth_mm / 2)
                else:
                    r = (station["foot_r_mm"] + .5 + station["foot_r_mm"] + 12.) / 2
                    levels = (heel_mm - 15., -layout.base_depth_mm / 2)
                for z_mm in levels:
                    for dx, dy in ((r / sqrt(2), r / sqrt(2)), (-r / sqrt(2), r / sqrt(2))):
                        points.append((x + dx, y + dy, z_mm))
        probe[body] = (points, interpolate_tet10(xyz, groups[attached], points))
    return upper, lower, seats, dims, sample_face(shoe, xyz, dims), sample_face(floor, xyz, dims), probe


def write_deck(path, xyz, groups, upper, lower, seats, pressures):
    seats = {name: seat for name, seat in seats.items() if seat[2] > 0.}
    lines = ["*HEADING", "REV T-2.2e R2, N mm MPa", "*NODE"]
    lines.extend(f"{i},{x:.12g},{y:.12g},{z:.12g}" for i, (x, y, z) in enumerate(xyz[1:], 1))
    references = {}
    for i, (name, (top, bottom, k)) in enumerate(seats.items()):
        a, b = len(xyz) + 2*i, len(xyz) + 2*i + 1
        references[name] = (a, b)
        for ref, (tags, weights, _) in zip((a, b), (top, bottom)):
            point = weights @ xyz[tags]
            lines.append(f"{ref}," + ",".join(f"{v:.12g}" for v in point))
    by_body = {}
    for name, elements in groups.items():
        lines.append(f"*ELEMENT,TYPE=C3D10,ELSET={name}")
        lines.extend(f"{eid}," + ",".join(map(str, tags)) for eid, tags in elements)
        by_body[name] = sorted({tag for _, tags in elements for tag in tags})
    last = max(eid for elems in groups.values() for eid, _ in elems)
    for i, (name, (a, b)) in enumerate(references.items(), 1):
        lines += [f"*ELEMENT,TYPE=SPRING2,ELSET={name}", f"{last+i},{a},{b}",
                  f"*SPRING,ELSET={name}", "3,3", f"{seats[name][2]:.12g}"]
    lines += ["*MATERIAL,NAME=STEEL", "*ELASTIC", f"{prior.E_MPa},{prior.NU}"]
    for body in groups:
        lines.append(f"*SOLID SECTION,ELSET={body},MATERIAL=STEEL")
    for name, ref_pair in references.items():
        for ref, (tags, weights, _) in zip(ref_pair, seats[name][:2]):
            equations = [f"{ref},3,1."] + [f"{node},3,{-w:.13g}" for node, w in zip(tags, weights)]
            lines += ["*EQUATION", str(len(equations))]
            lines.extend(",".join(equations[j:j+3]) for j in range(0, len(equations), 3))
    lines.append("*BOUNDARY")
    fixed = []
    for body, targets in (
        ("SHOE", ((15.,-95.,70.), (175.,-95.,70.))),
        ("FLOOR", ((0.,-95.,-65.), (160.,-95.,-65.), (0.,95.,-65.))),
    ):
        ids = by_body[body]
        chosen = [ids[np.argmin(np.linalg.norm(xyz[ids] - target, axis=1))] for target in targets]
        if body == "SHOE":
            lines += [f"{chosen[0]},1,2", f"{chosen[1]},2,2"]
        else:
            fixed = chosen
            lines += [f"{chosen[0]},1,3", f"{chosen[1]},2,3", f"{chosen[2]},3,3"]
    for a, b in references.values():
        lines += [f"{a},1,2", f"{b},1,2"]
    loads = upper + lower
    for bar in pressures:
        lines += ["*STEP", "*STATIC", "1.,1.", "*CLOAD,OP=NEW"]
        lines.extend(f"{node},3,{loads[node] * (bar / 315):.12g}" for node in np.flatnonzero(loads))
        lines += ["*NODE FILE", "U,RF", "*EL FILE", "S", "*END STEP"]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return references, fixed


def results(xyz, states, data, fixed, peak):
    upper, lower, seats, dims, shoe_samples, floor_samples, probes = data
    rows = []
    high_load_N = peak["shoe_force_N"]
    for pressure, state in zip(PRESSURES_BAR, states):
        uz = state["DISP"][:, 2]
        stress = state["STRESS"]
        opening = np.array([wa @ uz[na] - wb @ uz[nb]
                            for (na, wa), (nb, wb) in zip(shoe_samples, floor_samples)])
        max_id = int(np.argmax(opening))
        support_rows = {}
        for name, (top, bottom, k) in seats.items():
            tag1, w1, area1 = top
            tag2, w2, area2 = bottom
            moves = [float(w1 @ uz[tag1]), float(w2 @ uz[tag2])]
            support_rows[name] = dict(spring_force_N=k * (moves[0] - moves[1]), seat_mean_Uz_mm=moves,
                                      top_seat_area_mm2=area1, bottom_seat_area_mm2=area2)
        control = {}
        for part, (points, locations) in probes.items():
            for i, (point, (tags, weights)) in enumerate(zip(points, locations)):
                tensor = weights @ stress[tags]
                working_range = mises_MPa(weights @ (stress[tags] - states[0]["STRESS"][tags]))
                control[f"{part}_{i:02}"] = dict(point_mm=point, equivalent_MPa=mises_MPa(tensor),
                                                 range_MPa=working_range, stress_MPa=tensor.tolist())
        target_N = high_load_N * pressure / 315
        reactions_N = state["FORC"][fixed].sum(axis=0)
        vertical_N = sum(s["spring_force_N"] for s in support_rows.values())
        rows.append(dict(
            pressure_bar=pressure, peak_opening_mm=float(opening[max_id]), peak_opening_xy_mm=dims[max_id],
            peak_opening_shoe_Uz_mm=float(shoe_samples[max_id][1] @ uz[shoe_samples[max_id][0]]),
            peak_opening_floor_Uz_mm=float(floor_samples[max_id][1] @ uz[floor_samples[max_id][0]]),
            maximum_height_with_seating_mm=float(opening[max_id] + (.020 if pressure else 0.)),
            centroid_profile_opening_mm={str(y): float(opening[dims.index((peak["centroid_x_mm"], y))])
                                         for y in (-75., 0., 75.)},
            support_steps=support_rows, global_control_points=control,
            force_balance_fraction=abs(vertical_N - target_N) / max(1., target_N),
            anchor_net_reaction_N=reactions_N.tolist(),
        ))
    return rows


def run_one(layout, mesh_mm, roof, gate, accepted_mass, timeout, mesh_only=False, full_steps=False, audit=False):
    peak = roof["load"]["315_bar"]["peak"]
    stations, checks, y_c_mm, clearance_mm = station_data(layout, gate, peak)
    row = dict(layout=asdict(layout), mesh_mm=mesh_mm, stations=stations, nominal_station_spacing_clearance_mm=clearance_mm,
               hand_FKM_min=min(s["FKM"] for c in checks.values() for s in (c["post"], c["foot"], *c["teeth"].values())),
               load_centroid_xy_mm=[peak["centroid_x_mm"], y_c_mm])
    with TemporaryDirectory(prefix="r2_boxes_", dir=HERE) as scratch:
        folder = Path(scratch)
        make_geo(folder / "boxes.geo", layout, stations, mesh_mm)
        gmsh_args = ["boxes.geo", "-nt", "1", "-o", "boxes.msh", "-v", "4"]
        gmsh_args += ["-0"] if mesh_only else ["-3"]
        try:
            gmsh = tool("gmsh.exe", gmsh_args, folder, "gmsh.log", min(timeout, 120))
        except TimeoutExpired:
            gmsh = "TIMEOUT"
        log = (folder / "gmsh.log").read_text(encoding="ascii", errors="replace")
        volumes = {name: float(value) for name, value in re.findall(r"(SHOE|FLOOR) volume_mm3 ([0-9.e+-]+)", log)}
        if set(volumes) == {"SHOE", "FLOOR"}:
            row["mass"] = mass_of(stations, roof["gate_shift"], volumes, accepted_mass)
            row["exact_box_volumes_mm3"] = volumes
        if gmsh or ("Error" in log):
            return row | dict(status="GMSH_FAILED", diagnostic=log.splitlines()[-20:],
                              messages=[s for s in log.splitlines() if "Error" in s])
        if mesh_only:
            return row | dict(status="GEOMETRIC_MASS")
        xyz, groups = read_mesh(folder / "boxes.msh", NAMES)
        row["node_count"] = len(xyz) - 1
        row["tetrahedra"] = sum(map(len, groups.values()))
        if audit:
            mesh_volumes = {}
            for body, elements in groups.items():
                vertices = xyz[np.asarray([ids[:4] for _, ids in elements])]
                determinant = np.linalg.det(vertices[:, 1:] - vertices[:, :1])
                if np.min(determinant) <= 0.:
                    raise ValueError(f"Nonpositive {body} Jacobians in global model")
                mesh_volumes[body] = float(determinant.sum() / 6)
            row["meshed_box_volume_mm3"] = mesh_volumes
            row["mesh_to_Occ_volume_error_fraction"] = {name: abs(volumes[name] - volume) / volumes[name]
                                                      for name, volume in mesh_volumes.items()}
        data = model_data(xyz, groups, layout, stations, checks, peak, y_c_mm, audit)
        def solve_steps(pressures):
            _, fixed = write_deck(folder / "boxes.inp", xyz, groups, *data[:3], pressures)
            status = tool("ccx.exe", ["-i", "boxes"], folder, "ccx.log", timeout)
            frd = folder / "boxes.frd"
            if status or not frd.is_file():
                raise RuntimeError((folder / "ccx.log").read_text(encoding="ascii", errors="replace").splitlines()[-24:])
            states = read_fields(frd, len(xyz) + 2 * len(data[2]))
            if len(states) != len(pressures):
                raise RuntimeError(f"Expected {len(pressures)} output frames, found {len(states)}")
            return states, fixed

        try:
            states, fixed = solve_steps((315,))
            inactive = []
            for name, (top, bottom, _) in data[2].items():
                top_ids, top_w, _ = top
                bottom_ids, bottom_w, _ = bottom
                uz = states[-1]["DISP"][:, 2]
                if top_w @ uz[top_ids] < bottom_w @ uz[bottom_ids]:
                    inactive.append(name)
            if len(inactive) > 1:
                return row | dict(status="UNSTABLE_OPEN_SUPPORTS", inactive_supports=inactive)
            for name in inactive:
                a, b, _ = data[2][name]
                data[2][name] = (a, b, 0.)
            pressures = PRESSURES_BAR if full_steps else (315,)
            if inactive or full_steps:
                states, fixed = solve_steps(pressures)
            row["inactive_supports"] = inactive
        except (RuntimeError, TimeoutExpired) as error:
            return row | dict(status="CCX_FAILED", diagnostic=str(error))
        row["solver_pressure_steps_bar"] = list(pressures)
        if not full_steps:
            states = [{key: value * bar / 315 for key, value in states[0].items()} for bar in PRESSURES_BAR]
        row["steps"] = results(xyz, states, data, fixed, peak)
        if audit:
            row["manual_comparison_315_bar"] = hand_comparison(
                xyz, groups, states[-1]["STRESS"], data[:2], data[2], row["steps"][-1]["support_steps"])
        p300, p315 = row["steps"][-2:]
        row["global_box_static_factor_at_points"] = MATERIAL[0] / max(
             s["equivalent_MPa"] for s in p315["global_control_points"].values())
        row["global_box_FKM_at_points"] = min(prior.strength(s["range_MPa"] * prior.RELIEF_RATIO, MATERIAL)["FKM"]
             for s in p300["global_control_points"].values())
        return row | dict(status="SOLVED")


def main():
    parser = ArgumentParser()
    parser.add_argument("--case", type=int, action="append")
    parser.add_argument("--mesh", type=float, action="append")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--full-steps", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--mass-only", action="store_true")
    args = parser.parse_args()
    _, roof, gate = input_data()
    accepted = json.loads((HERE.parent / "round1_accepted.json").read_text(encoding="utf-8"))["hand"]["selected"]["mass"]
    rows = []
    for index in args.case if args.case is not None else range(len(CASES)):
        for mesh_mm in args.mesh or (22.,):
            layout = CASES[index]
            row = run_one(layout, mesh_mm, roof, gate, accepted, args.timeout, args.mass_only, args.full_steps, args.audit)
            rows.append(row)
            args.out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(layout.name, mesh_mm, row["status"], row.get("mass", {}).get("delta_chamber_kg"),
                  row.get("steps", [{}]*2)[-2].get("maximum_height_with_seating_mm"),
                  row.get("global_box_FKM_at_points"), flush=True)


if __name__ == "__main__":
    main()

