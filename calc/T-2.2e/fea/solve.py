"""Nonlinear CCX contact calculation for a loaded bayonet station.

The driving annulus has a common z displacement. The cast support is fixed at
its cut face. No global compliance claim follows from this boundary condition.
"""

import argparse
from collections import defaultdict
import json
from math import cos, pi, radians, sin
import os
import re
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np
from scipy.spatial import cKDTree

from geometry import (CROWN_MM, EDGE_RADIUS_MM, LAND_CLEARANCE_MM,
                      PAD_INNER_RELIEF_MM, RADIAL_INSERTION_MM, ROOT_MM, SEAT_CROWN_MM, SECTOR_DEG,
                      axial_planes, make_geometry)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from hand import calculate, prior

TOOLS = Path("E:/Tools/FreeCAD-1.1/bin")
PRESSURES_BAR = (0, 100, 200, 300, 315)
MESHES_MM = {"front": (8., 6., 4.9), "rear": (8., 6., 5.2)}
STEEL_E_MPa = prior.E_MPa
NORMAL_MPa_MM = 60_000.
FRICTION = .15
TANGENT_MPa_MM = 400.
ROTOR_INNER_RELIEF_MM = 5.
BODY_NAMES = {1: "POST", 2: "SLEEVE", 3: "CAST"}
TET_FACES = ((0, 1, 2, 4, 5, 6), (0, 3, 1, 7, 8, 4),
             (1, 3, 2, 8, 9, 5), (2, 3, 0, 9, 7, 6))


def tool(exe, args, folder, log_name, timeout_s):
    env = os.environ | {"OMP_NUM_THREADS": "2", "CCX_NPROC_STIFFNESS": "2", "CCX_NPROC_EQUATION_SOLVER": "2"}
    with (folder / log_name).open("w", encoding="ascii") as log:
        return subprocess.run([str(TOOLS / exe), *args], cwd=folder, env=env, stdout=log,
                              stderr=subprocess.STDOUT, timeout=timeout_s, check=False).returncode


def read_mesh(path, body_names=BODY_NAMES):
    lines = iter(path.read_text(encoding="ascii").splitlines())
    for line in lines:
        if line == "$Nodes":
            xyz = np.zeros((int(next(lines)) + 1, 3))
            for row in lines:
                if row == "$EndNodes":
                    break
                number, *coordinates = row.split()
                xyz[int(number)] = np.asarray(coordinates, dtype=float)
        if line == "$Elements":
            groups = defaultdict(list)
            next(lines)
            for row in lines:
                if row == "$EndElements":
                    break
                number, kind, n_tags, *values = map(int, row.split())
                if kind == 11:
                    # Gmsh midsides 8 and 9 are reversed relative to C3D10.
                    *nodes, g8, g9 = values[n_tags:]
                    groups[body_names[values[0]]].append((number, (*nodes, g9, g8)))
    assert set(groups) == set(body_names.values())
    return xyz, groups


def boundary(groups):
    output = {}
    for part, elements in groups.items():
        faces = {}
        for number, nodes in elements:
            for side, indices in enumerate(TET_FACES, 1):
                face = tuple(nodes[index] for index in indices)
                key = tuple(sorted(face[:3]))
                if key in faces:
                    del faces[key]
                else:
                    faces[key] = (number, side, face)
        output[part] = list(faces.values())
    return output


def plane(faces, xyz, z_mm, radius_range_mm=(0., np.inf)):
    found = []
    for face in faces:
        points = xyz[list(face[2])]
        center_r_mm = np.linalg.norm(points[:3, :2].mean(axis=0))
        if np.allclose(points[:, 2], z_mm, rtol=0, atol=1e-5) and (
                radius_range_mm[0] <= center_r_mm <= radius_range_mm[1]):
            found.append(face)
    assert found, (z_mm, radius_range_mm)
    return found


def node_ids(faces):
    return sorted({node for _, _, face in faces for node in face})


def roundoff_mm(distance_mm):
    """Return the height of a tangent circular edge roll-off."""
    drawn_mm = np.clip(distance_mm, 0, EDGE_RADIUS_MM)
    return EDGE_RADIUS_MM - np.sqrt(EDGE_RADIUS_MM**2 - (EDGE_RADIUS_MM - drawn_mm)**2)


def axis_data(xyz, ids):
    indices = np.asarray(ids)
    r_mm = np.linalg.norm(xyz[indices, :2], axis=1)
    az_deg = np.degrees(np.arctan2(xyz[indices, 1], xyz[indices, 0]))
    az_offset_deg = (az_deg + 60.) % 120. - 60.
    return indices, r_mm, az_offset_deg


def warp_surface(xyz, flat, ids, z_mm, offset_mm, width_mm):
    weights = np.maximum(0., 1. - abs(flat[ids, 2] - z_mm) / width_mm)
    xyz[ids, 2] += offset_mm * weights


def straighten(xyz, groups):
    """Use affine tetrahedral geometry and quadratic displacement interpolation."""
    pairs = ((0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3))
    for elements in groups.values():
        indices = np.asarray([nodes for _, nodes in elements])
        vertices = xyz[indices[:, :4]]
        for index, (a, b) in enumerate(pairs, 4):
            xyz[indices[:, index]] = (vertices[:, a] + vertices[:, b]) / 2.
        determinants = np.linalg.det(vertices[:, 1:] - vertices[:, [0]])
        if np.min(determinants) <= 0:
            raise ValueError(f"Nonpositive geometric Jacobians: {np.count_nonzero(determinants <= 0)}")


def surfaces_and_profile(flat, groups, station, fit_excess_mm):
    shank = station["shank_r_mm"]
    head = station["head_r_mm"]
    foot = station["foot_r_mm"]
    bearing_z_mm, cast_z_mm, drive_z_mm = axial_planes(station)
    faces = boundary(groups)
    interface = dict(
        HEAD=plane(faces["POST"], flat, 0., (shank + PAD_INNER_RELIEF_MM - .5, head + .1)),
        LUG=plane(faces["SLEEVE"], flat, 0., (shank + ROTOR_INNER_RELIEF_MM - .5, head + RADIAL_INSERTION_MM)),
        HEEL=plane(faces["POST"], flat, bearing_z_mm),
        SEAT=plane(faces["CAST"], flat, bearing_z_mm),
    )
    drive = node_ids(plane(faces["SLEEVE"], flat, drive_z_mm, (head + (2.85 if drive_z_mm == -20. else RADIAL_INSERTION_MM), np.inf)))
    fixed = node_ids(plane(faces["CAST"], flat, cast_z_mm))
    bodies = {body: sorted({i for _, tags in elements for i in tags}) for body, elements in groups.items()}
    xyz = flat.copy()
    pitch_mm = (shank + head) / 2
    post_ids, r_mm, angle_deg = axis_data(flat, bodies["POST"])
    edge_mm = r_mm * np.radians(np.maximum(0., SECTOR_DEG / 2 - abs(angle_deg)))
    crown_mm = CROWN_MM * np.minimum(1., abs(angle_deg) / (SECTOR_DEG / 2))**2
    head_weight = np.clip((r_mm - shank) / PAD_INNER_RELIEF_MM, 0., 1.)
    angular_weight = np.clip((r_mm - shank - ROTOR_INNER_RELIEF_MM) / EDGE_RADIUS_MM, 0., 1.)
    head_offset_mm = head_weight * (np.maximum(roundoff_mm(head - r_mm),
                                                  angular_weight * roundoff_mm(edge_mm)) + crown_mm)
    warp_surface(xyz, flat, post_ids, 0., head_offset_mm, 25.)
    lug_ids, r_mm, angle_deg = axis_data(flat, bodies["SLEEVE"])
    edge_mm = r_mm * np.radians(np.maximum(0., SECTOR_DEG / 2 - abs(angle_deg)))
    az_deg = np.degrees(np.arctan2(flat[lug_ids, 1], flat[lug_ids, 0]))
    fit_mm = np.where(abs(az_deg) < 60., 0., fit_excess_mm)
    lug_offset_mm = np.maximum(roundoff_mm(r_mm - shank - ROTOR_INNER_RELIEF_MM), roundoff_mm(edge_mm))
    lug_weight = np.clip((head + RADIAL_INSERTION_MM + EDGE_RADIUS_MM - r_mm) / EDGE_RADIUS_MM, 0., 1.)
    warp_surface(xyz, flat, lug_ids, 0., -lug_weight * (LAND_CLEARANCE_MM + fit_mm + lug_offset_mm),
                 min(25., abs(drive_z_mm)))
    _, heel_r_mm, _ = axis_data(flat, bodies["POST"])
    contact_inner_mm = shank + ROOT_MM + RADIAL_INSERTION_MM
    width_mm = foot - contact_inner_mm
    heel_crown_mm = SEAT_CROWN_MM * np.minimum(1., abs(heel_r_mm - (contact_inner_mm + foot) / 2)
                                               / (width_mm / 2))**2
    warp_surface(xyz, flat, post_ids, bearing_z_mm,
                 -(roundoff_mm(foot - heel_r_mm) + heel_crown_mm), 22.)
    seat_ids, seat_r_mm, _ = axis_data(flat, bodies["CAST"])
    warp_surface(xyz, flat, seat_ids, bearing_z_mm,
                 LAND_CLEARANCE_MM + roundoff_mm(seat_r_mm - contact_inner_mm), 22.)
    straighten(xyz, groups)
    # Preserve the cast mounting and sleeve drive cut planes.
    assert np.allclose(xyz[drive, 2], flat[drive, 2]) and np.allclose(xyz[fixed, 2], flat[fixed, 2])
    return xyz, interface, drive, fixed


def mesh_lines(xyz, groups):
    yield "*NODE"
    for i, point in enumerate(xyz[1:], 1):
        yield f"{i}," + ",".join(f"{value:.12g}" for value in point)
    for body, elements in groups.items():
        yield f"*ELEMENT,TYPE=C3D10,ELSET={body}"
        for number, nodes in elements:
            yield f"{number}," + ",".join(map(str, nodes))


def node_set(name, ids):
    lines = [f"*NSET,NSET={name}"]
    lines.extend(",".join(map(str, ids[start:start+12])) for start in range(0, len(ids), 12))
    return lines


def make_deck(path, xyz, groups, interface, drive, fixed, travel_by_step_mm, normal_MPa_mm, node_contact, half,
              *, slave_element_faces=False):
    with path.with_name("mesh.inp").open("w", encoding="ascii", newline="\n") as mesh:
        mesh.writelines(line + "\n" for line in mesh_lines(xyz, groups))
    lines = ["*HEADING", "REV bayonet support local analysis, N mm MPa", "*INCLUDE,INPUT=mesh.inp",
             "*MATERIAL,NAME=STEEL", "*ELASTIC", f"{STEEL_E_MPa},{prior.NU}"]
    for name in groups:
        lines.append(f"*SOLID SECTION,ELSET={name},MATERIAL=STEEL")
    for name, faces in interface.items():
        if node_contact and not slave_element_faces and name in ("LUG", "HEEL"):
            lines += node_set(name + "_NODES", node_ids(faces))
            lines += [f"*SURFACE,TYPE=NODE,NAME={name}", name + "_NODES"]
        else:
            lines += [f"*SURFACE,TYPE=ELEMENT,NAME={name}"]
            lines.extend(f"{number},S{side}" for number, side, _ in faces)
    method = "NODE TO SURFACE,SMALL SLIDING" if node_contact else "SURFACE TO SURFACE"
    lines += ["*SURFACE INTERACTION,NAME=FRICT", "*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR",
              f"{normal_MPa_mm:.12g},1.e-5,.08", "*FRICTION", f"{FRICTION},{TANGENT_MPa_MM:.12g}",
              f"*CONTACT PAIR,INTERACTION=FRICT,TYPE={method}", "LUG,HEAD",
              f"*CONTACT PAIR,INTERACTION=FRICT,TYPE={method}", "HEEL,SEAT"]
    lines += node_set("FIXED", fixed) + node_set("DRIVE", drive)
    anchor_a = max(drive, key=lambda i: xyz[i, 0])
    anchor_b = min(drive, key=lambda i: xyz[i, 0])
    shaft = {i for _, nodes in groups["POST"] for i in nodes}
    shaft_a = max(shaft, key=lambda i: (xyz[i, 2], xyz[i, 0]))
    shaft_b = max(shaft, key=lambda i: (xyz[i, 2], -xyz[i, 0]))
    shaft_c = max(shaft, key=lambda i: (xyz[i, 2], xyz[i, 1]))
    lines += ["*BOUNDARY", "FIXED,1,3",
              f"{anchor_a},1,2", f"{anchor_b},2,2", f"{shaft_a},1,2", f"{shaft_b},2,2"]
    if half:
        symmetry = np.flatnonzero(abs(xyz[1:, 1]) < 5e-7) + 1
        # The first two anchors already fix y. Remove duplicates.
        symmetry = [int(node) for node in symmetry if node not in (anchor_a, anchor_b, shaft_a, shaft_b)
                    and node not in fixed]
        position = lines.index("*BOUNDARY")
        lines[position:position] = node_set("SYMMETRY", symmetry)
        lines.append("SYMMETRY,2,2")
    largest = max(number for elements in groups.values() for number, _ in elements)
    # Weak axial springs remove free rigid translations in the 0-bar state.
    lines += ["*ELEMENT,TYPE=SPRING1,ELSET=WEAK"]
    lines.extend(f"{largest + i},{node}" for i, node in enumerate((shaft_a, shaft_b, shaft_c), 1))
    lines += ["*SPRING,ELSET=WEAK", "3", "100."]
    for pressure_bar, travel_mm in zip(PRESSURES_BAR, travel_by_step_mm):
        initial = "1." if pressure_bar == 0 else ".5"
        lines += ["*STEP,INC=125", "*STATIC", f"{initial},1.,1.e-6,{initial}",
                  "*BOUNDARY", f"DRIVE,3,3,{travel_mm:.12g}",
                  "*NODE FILE,FREQUENCY=999999", "U,RF", "*EL FILE,FREQUENCY=999999", "S",
                  "*CONTACT FILE,FREQUENCY=999999", "CDIS,CSTR",
                  "*NODE PRINT,NSET=FIXED,TOTALS=ONLY,FREQUENCY=999999", "RF",
                  "*NODE PRINT,NSET=DRIVE,TOTALS=ONLY,FREQUENCY=999999", "RF"]
        if not node_contact:
            lines += ["*CONTACT PRINT,SLAVE=LUG,MASTER=HEAD,FREQUENCY=999999", "CF",
                      "*CONTACT PRINT,SLAVE=HEEL,MASTER=SEAT,FREQUENCY=999999", "CF"]
        lines += ["*END STEP"]
    path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def read_fields(path, count):
    fields = []
    matrix = None
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if line.startswith(" -4"):
                key = line.split()[1]
                width = {"DISP": 3, "FORC": 3, "STRESS": 6, "CONTACT": 6}.get(key)
                matrix = None
                if width is not None:
                    if key == "DISP":
                        fields.append({})
                    matrix = np.zeros((count, width))
                    fields[-1][key] = matrix
            elif line.startswith(" -1") and matrix is not None:
                index = int(line[3:13])
                if index < count:
                    matrix[index] = [float(line[13 + 12*i:25 + 12*i]) for i in range(matrix.shape[1])]
            elif line.startswith(" -3"):
                matrix = None
    return fields


def mises_MPa(tensor):
    a, b, c, xy, yz, zx = tensor
    return float(np.sqrt(((a-b)**2 + (b-c)**2 + (c-a)**2)/2 + 3*(xy**2 + yz**2 + zx**2)))


def data_reactions(path):
    rows = defaultdict(list)
    raw = path.read_text(encoding="ascii", errors="replace")
    for name, line in re.findall(r"total force \(fx,fy,fz\) for set (\w+) and time[^\n]*\n\s*([^\n]+)", raw):
        rows[name].append([float(v) for v in line.split()])
    return dict(rows)


def interpolate_tet10(xyz, elements, points):
    tets = np.asarray([nodes for _, nodes in elements])
    corners = xyz[tets[:, :4]]
    search = cKDTree(corners.mean(axis=1))
    indices = search.query(np.asarray(points), k=min(100, len(corners)))[1]
    output = []
    for point, subset in zip(points, indices):
        p = corners[subset]
        basis = np.transpose(p[:, 1:] - p[:, :1], (0, 2, 1))
        local = np.linalg.solve(basis, (point - p[:, 0])[..., None])[..., 0]
        b = np.column_stack([1. - local.sum(axis=1), local])
        selection = int(np.argmax(b.min(axis=1)))
        if np.min(b[selection]) < -1e-6:
            raise ValueError(f"Point outside analysis solid: {point}")
        a, b, c, d = b[selection]
        weight = np.array([a*(2*a-1), b*(2*b-1), c*(2*c-1), d*(2*d-1),
                           4*a*b, 4*b*c, 4*a*c, 4*a*d, 4*b*d, 4*c*d])
        output.append((tets[subset[selection]], weight))
    return output


def stress_probes(xyz, groups, station):
    r = station["shank_r_mm"]
    h = station["tooth_height_mm"]
    foot_z_mm, _, _ = axial_planes(station)
    post = [(0., 0., -60.), (0., 0., -105.), (.75 * r, 0., -80.), (r - 4., 0., 14.),
            (r + 2., 0., foot_z_mm - 8.)]
    sleeve = [(station["head_r_mm"] - 3., 0., -h * .25)]
    names = ("post_axis_upper", "post_axis_lower", "post_bending_probe", "tooth_root_fixed", "foot_interior",
             "tooth_root_sleeve")
    for name, point, (indices, weights) in zip(names, post + sleeve,
                                               interpolate_tet10(xyz, groups["POST"], post)
                                               + interpolate_tet10(xyz, groups["SLEEVE"], sleeve)):
        yield name, point, indices, weights


def contact_near_point(xyz, faces, values, point_mm):
    point = np.asarray(point_mm)
    for _, _, face in faces:
        triangle = xyz[list(face[:3]), :2]
        basis = (triangle[1:] - triangle[:1]).T
        if abs(np.linalg.det(basis)) < 1e-10:
            continue
        b, c = np.linalg.solve(basis, point - triangle[0])
        a = 1. - b - c
        if min(a, b, c) >= -1e-7:
            shape = np.array([a*(2*a-1), b*(2*b-1), c*(2*c-1), 4*a*b, 4*b*c, 4*a*c])
            return max(0., float(shape @ values[list(face)]))
    return None


def pressure_sector_fractions(xyz, faces, values, half):
    force_N = defaultdict(float)
    for _, _, face in faces:
        a, b, c = xyz[list(face[:3])]
        local_xy = (a + b + c)[:2] / 3.
        angle_deg = np.degrees(np.arctan2(local_xy[1], local_xy[0]))
        sector = round(angle_deg / 120.) % 3
        area_vec_mm2 = np.cross(b - a, c - a) / 2.
        force_N[sector] += abs(area_vec_mm2[2]) * float(values[list(face[3:])].mean())
    if half:
        force_N[0] *= 2.
        force_N[2] = force_N[1]
    total_N = sum(force_N.values())
    return {str(i): force_N[i] / total_N for i in range(3)} if total_N else {}


def summarize_states(folder, xyz, flat, groups, interface, drive, fixed, station, force_315_N, states, half):
    toe_ids = np.asarray(node_ids(interface["LUG"]))
    heel_ids = np.asarray(node_ids(interface["HEEL"]))
    probes = list(stress_probes(xyz, groups, station))
    reactions = data_reactions(folder / "station.dat")
    summaries = []
    initial_stress = states[0]["STRESS"]
    tooth_r_mm = (station["head_r_mm"] + station["shank_r_mm"] + ROTOR_INNER_RELIEF_MM) / 2
    heel_r_mm = (station["foot_r_mm"] + station["shank_r_mm"] + ROOT_MM + RADIAL_INSERTION_MM) / 2
    tooth_gauges = [(tooth_r_mm * cos(radians(a)), tooth_r_mm * sin(radians(a))) for a in (12., 120.)]
    heel_gauge = (heel_r_mm * cos(radians(24.)), heel_r_mm * sin(radians(24.)))
    for index, state in enumerate(states):
        pressure_bar = PRESSURES_BAR[index]
        reaction_N = float(state["FORC"][fixed, 2].sum())
        if len(reactions.get("FIXED", [])) > index:
            reaction_N = reactions["FIXED"][index][2]
        applied_N = reactions["DRIVE"][index][2] if len(reactions.get("DRIVE", [])) > index else None
        stresses = {}
        for name, point, indices, weights in probes:
            tensor = weights @ state["STRESS"][indices]
            cycle = weights @ (state["STRESS"][indices] - initial_stress[indices])
            steel = (650., 800., True) if name == "cast" else (700., 900., False)
            range_MPa = mises_MPa(cycle)
            strength = prior.strength(max(1e-12, range_MPa) * prior.RELIEF_RATIO, steel)
            stresses[name] = dict(point_mm=point, equivalent_MPa=mises_MPa(tensor), axial_MPa=float(tensor[2]),
                                  material_Rp02_MPa=steel[0], point_axial_displacement_mm=float(weights @ state["DISP"][indices, 2]),
                                  range_from_zero_MPa=range_MPa, FKM_if_working_step=strength["FKM"])
        contact = state.get("CONTACT", np.zeros((len(xyz) + 1, 6)))
        target_N = force_315_N * pressure_bar / 315.
        approximate_N = abs(reaction_N)
        summaries.append(dict(
            pressure_step_label_bar=pressure_bar, target_force_N=target_N, drive_reaction_N=applied_N,
            cast_reaction_N=reaction_N,
            force_relative_error=abs(approximate_N - target_N) / max(1., target_N),
            balance_relative_error=(None if applied_N is None else
                                    abs(reaction_N + applied_N) / max(1., abs(applied_N))),
            sleeve_up_mm=float(state["DISP"][drive, 2].mean()),
            tooth_frd_peak_MPa=float(contact[toe_ids, 3].max()),
            heel_frd_peak_MPa=float(contact[heel_ids, 3].max()),
            tooth_continuous_gauge_MPa=[contact_near_point(xyz, interface["LUG"], contact[:, 3], p)
                                        for p in tooth_gauges],
            heel_continuous_gauge_MPa=contact_near_point(xyz, interface["HEEL"], contact[:, 3], heel_gauge),
            tooth_force_shares_from_normal_pressure=pressure_sector_fractions(
                xyz, interface["LUG"], contact[:, 3], half),
            section_diagnostics={name: dict(FEA_axial_MPa=stresses[name]["axial_MPa"],
                                           hand_axial_MPa=approximate_N / (pi * station["shank_r_mm"]**2 / (2 if half else 1)))
                                 for name in ("post_axis_upper", "post_axis_lower")},
            stress_probes=stresses,
        ))
    return summaries


def run_case(folder, selected, label, mesh_mm, normal_MPa_mm, timeout_s, node_contact, travel_by_step_mm, half, force_315_N, curvature_segments=0):
    folder.mkdir(parents=True)
    station = selected["stations"][label]
    support = selected["support_checks"][label]
    force_315_N /= 2 if half else 1
    make_geometry(folder / "station.geo", station, mesh_mm, half, curvature_segments)
    gmsh = tool("gmsh.exe", ["station.geo", "-3", "-nt", "1", "-o", "station.msh"], folder, "gmsh.log", 240)
    summary = dict(station=label, mesh_contact_mm=mesh_mm, normal_penalty_MPa_mm=normal_MPa_mm, gmsh_code=gmsh,
                   method="node_to_surface" if node_contact else "surface_to_surface", half_symmetry=half)
    if curvature_segments:
        summary["curvature_segments_per_turn"] = curvature_segments
    if gmsh or not (folder / "station.msh").is_file():
        summary["status"] = "GMSH_FAILED"
        summary["diagnostic"] = (folder / "gmsh.log").read_text(errors="replace").splitlines()[-15:]
        return summary
    flat, groups = read_mesh(folder / "station.msh")
    try:
        xyz, interface, drive, fixed = surfaces_and_profile(flat, groups, station, support["worst_fit_gap_mm"])
    except ValueError as error:
        return summary | dict(status="INVALID_MESH", diagnostic=str(error))
    make_deck(folder / "station.inp", xyz, groups, interface, drive, fixed, travel_by_step_mm, normal_MPa_mm, node_contact, half)
    summary.update(trial_travel_315_mm=travel_by_step_mm[-1], trial_travel_by_step_mm=travel_by_step_mm, nodes=len(xyz) - 1, tetrahedra=sum(map(len, groups.values())),
                   tooth_faces=len(interface["LUG"]), heel_faces=len(interface["HEEL"]))
    try:
        summary["ccx_code"] = tool("ccx.exe", ["-i", "station"], folder, "ccx.log", timeout_s)
    except subprocess.TimeoutExpired:
        summary["ccx_code"] = "TIMEOUT"
    frd = folder / "station.frd"
    states = read_fields(frd, len(xyz) + 1) if frd.is_file() else []
    # Incomplete analyses can contain a final nonconverged FRD record.
    states = states[:len(PRESSURES_BAR)]
    complete = not summary["ccx_code"] and len(states) == len(PRESSURES_BAR)
    summary["recorded_frd_frames"] = len(states)
    try:
        summary["steps"] = summarize_states(folder, xyz, flat, groups, interface, drive, fixed,
                                             station, force_315_N, states, half) if states else []
    except ValueError as error:
        summary["postprocess_error"] = str(error)
    summary["status"] = "SOLVED_DISPLACEMENT_TRIAL" if complete else "CCX_INCOMPLETE"
    if not complete:
        summary["diagnostic"] = (folder / "ccx.log").read_text(errors="replace").splitlines()[-15:]
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=int, choices=(0, 1, 2), action="append")
    parser.add_argument("--station", choices=("front", "rear"), default="front")
    parser.add_argument("--normal", type=float, default=NORMAL_MPa_MM)
    parser.add_argument("--timeout", type=int, default=450)
    parser.add_argument("--node-contact", action="store_true")
    parser.add_argument("--travel-mm", type=float)
    parser.add_argument("--half", action="store_true")
    parser.add_argument("--global-input", type=Path)
    parser.add_argument("--fit-from", type=Path)
    parser.add_argument("--curvature", type=int, default=0)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    hand, _, _ = calculate()
    if not hand["selected"]:
        raise SystemExit("Hand screen stop")
    meshes_mm = MESHES_MM[args.station]
    levels = args.level if args.level is not None else list(range(len(meshes_mm)))
    travel_mm = args.travel_mm or (.24 if args.station == "front" else .13)
    force_315_N = hand["selected"]["support_checks"][args.station]["force_315_N"]
    if args.global_input:
        whole = json.loads(args.global_input.read_text(encoding="utf-8"))["skew_screen"][-1]["results"]
        supports = [record for name, record in whole["supports"].items() if name.startswith(args.station)]
        if args.travel_mm is None:
            travel_mm = max(record["local_opening_315_mm"] for record in supports)
        force_315_N = max(force_315_N, max(record["support_force_315_N"] for record in supports))

    travels_mm = [travel_mm * pressure / 315. for pressure in PRESSURES_BAR]
    if args.fit_from:
        reference = json.loads(args.fit_from.read_text(encoding="utf-8"))[-1]
        if reference["station"] != args.station or reference["half_symmetry"] != args.half:
            raise ValueError("Calibration requires the same station and symmetry")
        source = reference["steps"]
        measured_N = np.array([abs(row["cast_reaction_N"]) for row in source])
        displacements_mm = np.array([row["sleeve_up_mm"] for row in source])
        if not np.all(np.diff(measured_N) > 0.):
            raise ValueError("Calibration requires increasing reactions at each step")
        targets_N = (np.array(PRESSURES_BAR) * force_315_N / 315. / (2 if args.half else 1))
        fitted = np.interp(targets_N, measured_N, displacements_mm)
        past_end = targets_N > measured_N[-1]
        fitted[past_end] = displacements_mm[-1] + (targets_N[past_end] - measured_N[-1]) * (
            (displacements_mm[-1] - displacements_mm[-2]) / (measured_N[-1] - measured_N[-2]))
        travels_mm = fitted.tolist()
        travels_mm[0] = 0.

    def run(base):
        records = []
        for level in levels:
            record = run_case(base / f"{args.station}_{level}", hand["selected"], args.station,
                              meshes_mm[level], args.normal, args.timeout, args.node_contact, travels_mm, args.half, force_315_N, args.curvature)
            records.append(record)
            print(json.dumps(record, ensure_ascii=True), flush=True)
            if args.out:
                args.out.write_text(json.dumps(records, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    if args.scratch:
        run(args.scratch.resolve())
    else:
        with TemporaryDirectory(dir=HERE, prefix="local_scratch_") as folder:
            run(Path(folder))


if __name__ == "__main__":
    main()


