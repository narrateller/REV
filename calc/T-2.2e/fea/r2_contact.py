"""Force-controlled local bayonet contact with convergence gauges and strip averages."""
from argparse import ArgumentParser
from collections import defaultdict
import json
from math import cos, pi, radians, sin
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np

from geometry import axial_planes, make_geometry
from section_check import integrate_section
from hand import prior, support_checks
from solve import (HERE, PRESSURES_BAR, boundary, contact_near_point, data_reactions, make_deck,
                   plane, read_fields, read_mesh, summarize_states, surfaces_and_profile, tool)

def distribute_force(xyz, groups, drive, station):
    drive_z_mm = axial_planes(station)[2]
    sleeve = boundary({"SLEEVE": groups["SLEEVE"]})["SLEEVE"]
    drive_faces = plane(sleeve, xyz, drive_z_mm)
    drive_set = set(drive)
    nodal = defaultdict(float)
    for _, _, face in drive_faces:
        if not set(face).issubset(drive_set):
            continue
        a, b, c = xyz[list(face[:3])]
        area = np.linalg.norm(np.cross(b - a, c - a)) / 2
        for node in face[3:]:
            nodal[node] += area / 3
    den = sum(nodal.values())
    return {tag: w / den for tag, w in nodal.items()}


def force_deck(path, xyz, groups, interface, drive, fixed, station, normal, force_N, half):
    make_deck(path, xyz, groups, interface, drive, fixed, [0.]*len(PRESSURES_BAR), normal, True, half,
              slave_element_faces=True)
    contents = path.read_text(encoding="ascii")
    anchor_ids = sorted(drive, key=lambda tag: (xyz[tag, 1], xyz[tag, 0]))
    count = max(number for rows in groups.values() for number, _ in rows)
    weak = ["*ELEMENT,TYPE=SPRING1,ELSET=WEAKDRIVE",
            f"{count + 4},{anchor_ids[0]}", f"{count + 5},{anchor_ids[-1]}",
            "*SPRING,ELSET=WEAKDRIVE", "3", "100."]
    head, *steps = contents.split("*STEP,INC=125\n")
    text = [head.rstrip("\n"), *weak]
    distribution = distribute_force(xyz, groups, drive, station)
    for bar, step in zip(PRESSURES_BAR, steps):
        _, _, _, _, *tail = step.splitlines()
        increment = "1.,1.,1.e-8,1." if bar == 0 else ".65,1.,1.e-8,1."
        loading = ["*STEP,INC=160", "*STATIC", increment,
                   "*CLOAD,OP=NEW"]
        loading.extend(f"{tag},3,{w * bar / 315 * force_N:.12g}" for tag, w in sorted(distribution.items()))
        text.extend([*loading, *tail])
    path.write_text("\n".join(text) + "\n", encoding="ascii")


def band_quadrature(divisions):
    samples = []
    for j in range(divisions):
        for k in range(divisions-j):
            samples.append(((j + 1/3)/divisions, (k + 1/3)/divisions))
            if j + k < divisions - 1:
                samples.append(((j + 2/3)/divisions, (k + 2/3)/divisions))
    return np.asarray(samples)


BAND_UV = band_quadrature(12)


def annular_band(face_rows, xyz, pressure, inner_mm, outer_mm, sector_half_angle_deg=None):
    """Area-weighted pressure on fixed geometric bands, including unloaded points."""
    accum = defaultdict(lambda: [0., 0.])
    for _, _, face in face_rows:
        a, b, c = xyz[list(face[:3]), :2]
        det = (b[0]-a[0]) * (c[1]-a[1]) - (b[1]-a[1]) * (c[0]-a[0])
        if abs(det) < 1e-10:
            continue
        p_nodes = pressure[list(face)]
        # Midpoint sampling on uniform barycentric subdivisions; this also
        # resolves the fixed band boundary independently of the FEA grid.
        uv = BAND_UV
        coords = a + uv[:, 0,None]*(b-a) + uv[:, 1,None]*(c-a)
        radius = np.linalg.norm(coords, axis=1)
        angular = np.degrees(np.arctan2(coords[:, 1], coords[:, 0]))
        sector = np.round(angular / 120.).astype(int)
        angle = abs(angular - 120.*sector)
        yes = (radius >= inner_mm) & (radius <= outer_mm)
        if sector_half_angle_deg is not None:
            yes &= angle <= sector_half_angle_deg
        l, n = uv[yes].T
        k = 1 - l - n
        shape = np.column_stack((k*(2*k-1), l*(2*l-1), n*(2*n-1), 4*k*l, 4*l*n, 4*n*k))
        interpolated = np.maximum(0., shape @ p_nodes)
        area_share = abs(det) / (2*len(uv))
        for key in np.unique(sector[yes]) if sector_half_angle_deg is not None else [0]:
            mask = sector[yes] == key if sector_half_angle_deg is not None else np.ones(len(interpolated), bool)
            accum[int(key)][0] += float(np.sum(interpolated[mask])) * area_share
            accum[int(key)][1] += int(np.sum(mask)) * area_share
    return {str(key % 3): {"pressure_mean_MPa": force/area, "projected_area_mm2": area}
            for key, (force, area) in sorted(accum.items()) if area > 0}


def pressure_resultant_N(faces, xyz, pressure):
    # CCX assigns 1/3 of a quadratic triangular face to each midside node.
    # The projected area approximates the axial projection of the contact
    # traction. It leaves out the axial component of tangential friction.
    tags = np.asarray([face for _, _, face in faces])
    points = xyz[tags[:, :3], :2]
    determinants = np.linalg.det(points[:, 1:] - points[:, :1])
    return float((abs(determinants) / 2.) @ pressure[tags[:, 3:]].mean(axis=1))


def summarize(summaries, states, xyz, interface, groups, station, force_full_N, half, travels):
    divisor = 2 if half else 1
    heel_r = station["foot_r_mm"]
    r0 = station["shank_r_mm"]
    head = station["head_r_mm"]
    toe_inner, toe_outer = r0 + 10., head - 5.
    heel_inner, heel_outer = r0 + 21., heel_r - 5.
    toe_r = (toe_inner + toe_outer) / 2
    heel_r_gauge = (heel_inner + heel_outer) / 2
    toe_ang = radians(5.)
    heel_ang = radians(24.)
    tooth_gauge = (toe_r*cos(toe_ang), toe_r*sin(toe_ang))
    heel_gauge = (heel_r_gauge*cos(heel_ang), heel_r_gauge*sin(heel_ang))
    half_band_deg = 27.5 - (5. / toe_r) * 180 / pi
    for row, state in zip(summaries, states):
        bar = row["pressure_step_label_bar"]
        target_N = force_full_N * bar / (315. * divisor)
        cast_N = abs(row["cast_reaction_N"])
        drive_N = row["drive_reaction_N"]
        applied_N = (abs(drive_N) if drive_N is not None else None) if travels is not None else target_N
        row["equilibrium_error_fraction"] = (abs(cast_N - applied_N) / max(1., applied_N)
                                            if applied_N is not None else None)
        pressure = state.get("CONTACT", np.zeros((len(xyz), 6)))[:, 3]
        toe_band = annular_band(interface["LUG"], xyz, pressure, toe_inner, toe_outer, half_band_deg)
        heel_band = annular_band(interface["HEEL"], xyz, pressure, heel_inner, heel_outer)
        manual = support_checks(prior.rotor(cast_N * divisor, station, prior.TOOTH_SHARE),
                                station, "front") if bar and cast_N > 1. else None
        proof = manual["raised_pad_contact_315"] if manual else None
        f_mean = max((item["pressure_mean_MPa"] for item in toe_band.values()), default=None)
        f_point = contact_near_point(xyz, interface["LUG"], pressure, tooth_gauge)
        row["pressure_projected_force_N"] = {pair: pressure_resultant_N(interface[pair], xyz, pressure)
                                             for pair in ("LUG", "HEEL")}
        row["contact_gauges"] = dict(
            tooth_point_xy_mm=tooth_gauge, heel_point_xy_mm=heel_gauge,
            tooth_point_MPa=f_point,
            heel_point_MPa=contact_near_point(xyz, interface["HEEL"], pressure, heel_gauge),
            tooth_band_by_sector=toe_band, heel_band=heel_band.get("0"),
            highest_tooth_band_mean_MPa=f_mean,
            hand_tooth_nominal_mean_MPa=proof["net_mean_MPa"] if proof else None,
            hand_tooth_Hertz_peak_MPa=proof["peak_MPa"] if proof else None,
            hand_heel_annular_max_MPa=manual["foot_bearing"]["pressure_max_MPa"] if manual else None,
            tooth_point_to_hand_Hertz_difference_fraction=(f_point/proof["peak_MPa"] - 1.
                                                           if f_point is not None and proof else None),
            tooth_strip_to_hand_nominal_difference_fraction=(f_mean/proof["net_mean_MPa"] - 1.
                                                            if f_mean is not None and proof else None),
        )
    if summaries and summaries[-1]["pressure_step_label_bar"] == 315:
        sections = []
        bearing, _, _ = axial_planes(station)
        for z in (bearing*.30, bearing*.53, bearing*.71):
            mesh_area, integrated = integrate_section(xyz, groups["POST"], states[-1]["STRESS"][:,2], z)
            hand_MPa = abs(summaries[-1]["cast_reaction_N"]) / (pi * r0**2 / divisor)
            fea_MPa = integrated / mesh_area
            sections.append(dict(z_relative_to_tooth_mm=z, area_mm2=mesh_area,
                                 hand_MPa=hand_MPa, FEA_MPa=fea_MPa,
                                 error_fraction=abs(fea_MPa-hand_MPa)/hand_MPa))
        summaries[-1]["section_checks"] = sections
    return summaries


def set_unloaded_contacts_open(path):
    data = path.read_text(encoding="ascii")
    header, *steps = data.split("*STEP,INC=125\n")
    for index, action in ((0, "REMOVE"), (1, "ADD")):
        model_change = (f"*MODEL CHANGE,TYPE=CONTACT PAIR,{action}\nLUG,HEAD\n"
                        f"*MODEL CHANGE,TYPE=CONTACT PAIR,{action}\nHEEL,SEAT\n")
        steps[index] = steps[index].replace("*NODE FILE", model_change + "*NODE FILE", 1)
    path.write_text("*STEP,INC=125\n".join([header, *steps]), encoding="ascii")


def completed_steps(path):
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="ascii", errors="replace").splitlines()
               if len(line.split()) == 7 and line.split()[0].isdigit()
               and abs(float(line.split()[5].replace(",", ".")) - 1.) < 1e-8)


def run_station(folder, station, fit_mm, mesh_mm, force_full_N, normal, timeout, half, curvature, travels, validate_only=False, open_zero_step=False):
    folder.mkdir()
    make_geometry(folder / "station.geo", station, mesh_mm, half, curvature)
    gmsh = tool("gmsh.exe", ["station.geo", "-3", "-nt", "1", "-v", "3", "-o", "station.msh"],
                folder, "gmsh.log", 240)
    if gmsh:
        return dict(status="GMSH_FAILED", diagnostic=(folder / "gmsh.log").read_text(errors="replace").splitlines()[-12:])
    flat, groups = read_mesh(folder / "station.msh")
    try:
        xyz, interface, drive, fixed = surfaces_and_profile(flat, groups, station, fit_mm)
    except (ValueError, AssertionError) as exc:
        return dict(status="INVALID_MESH", diagnostic=str(exc))
    if validate_only:
        return dict(status="MESH_VALID", node_count=len(xyz)-1, curvature_segments=curvature)
    force_N = force_full_N / (2 if half else 1)
    if travels is None:
        force_deck(folder / "station.inp", xyz, groups, interface, drive, fixed, station, normal, force_N, half)
    else:
        make_deck(folder / "station.inp", xyz, groups, interface, drive, fixed, travels, normal, True, half,
                  slave_element_faces=True)
        if open_zero_step:
            set_unloaded_contacts_open(folder / "station.inp")
    try:
        ccx = tool("ccx.exe", ["-i", "station"], folder, "ccx.log", timeout)
    except subprocess.TimeoutExpired:
        ccx = "TIMEOUT"
    frd = folder / "station.frd"
    count = len(PRESSURES_BAR) if ccx == 0 else completed_steps(folder / "station.sta")
    states = read_fields(frd, len(xyz) + 1)[:count] if frd.is_file() and count else []
    row = dict(status="SOLVED" if ccx == 0 and len(states) == len(PRESSURES_BAR) else "CCX_INCOMPLETE",
               node_count=len(xyz)-1, ccx_code=ccx, recorded_steps=len(states),
               normal_penalty_MPa_mm=normal, fit_mm=fit_mm, half_symmetry=half, curvature_segments=curvature,
               boundary_condition="Force on the sleeve shoulder" if travels is None else
                                  "Prescribed axial travel on the sleeve shoulder",
               fixed_cast_boundary=True, imposed_travel_by_pressure_step_mm=travels,
               target_force_full_station_315_N=force_full_N)
    row["slave_definition"] = "element_faces; node-to-surface contact search"
    if open_zero_step:
        row["unloaded_contact_active"] = False
    if states:
        try:
            rows = summarize_states(folder, xyz, flat, groups, interface, drive, fixed, station, force_N, states, half)
            row["steps"] = summarize(rows, states, xyz, interface, groups, station, force_full_N, half, travels)
        except (ValueError, KeyError, TypeError) as error:
            return row | dict(status="POSTPROCESS_FAILED", diagnostic=str(error))
    if row["status"] == "CCX_INCOMPLETE":
        row["diagnostic"] = (folder / "ccx.log").read_text(errors="replace").splitlines()[-14:]
    return row


def main():
    parser = ArgumentParser()
    parser.add_argument("--global-result", type=Path, required=True)
    parser.add_argument("--case", help="Name of the selected calculation layout")
    parser.add_argument("--station", action="append", choices=("front", "rear"))
    parser.add_argument("--mesh", type=float, action="append")
    parser.add_argument("--front-mesh", type=float, nargs="+")
    parser.add_argument("--rear-mesh", type=float, nargs="+")
    parser.add_argument("--normal", type=float, default=20000.)
    parser.add_argument("--travel-mm", type=float)
    parser.add_argument("--displacement", action="store_true")
    parser.add_argument("--fit-from", type=Path)
    parser.add_argument("--curvature", type=int, default=36)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--open-zero-step", action="store_true")
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.open_zero_step and not args.displacement:
        parser.error("--open-zero-step requires --displacement")
    cases = json.loads(args.global_result.read_text(encoding="utf-8"))
    selected = next(row for row in reversed(cases) if row["status"] == "SOLVED"
                    and (args.case is None or row["layout"]["name"] == args.case))
    summary = []
    calibrated = json.loads(args.fit_from.read_text(encoding="utf-8")) if args.fit_from else []
    with TemporaryDirectory(dir=HERE, prefix="r2_contact_") as scratch:
        for label in args.station or ("front", "rear"):
            station = selected["stations"][label]
            supports = selected["steps"][-1]["support_steps"]
            worst = max((supports[label + "_" + side] for side in ("left", "right")),
                        key=lambda record: record["spring_force_N"])
            force = worst["spring_force_N"]
            fit = support_checks(prior.rotor(force, station, prior.TOOTH_SHARE), station, label)["worst_fit_gap_mm"]
            meshes = (args.front_mesh if label == "front" else args.rear_mesh)
            for mesh in meshes or args.mesh or (6., 4.5, 3.6):
                travels = None
                if args.displacement:
                    top, bottom = worst["seat_mean_Uz_mm"]
                    full_travel = args.travel_mm if args.travel_mm is not None else (top - bottom) + .04
                    travels = [full_travel * pressure / 315 for pressure in PRESSURES_BAR]
                    trials = [r for r in calibrated if r["station"] == label and r["status"] == "SOLVED"]
                    if trials:
                        source = min(trials, key=lambda row: abs(row["mesh_mm"] - mesh))["steps"]
                        reactions = np.array([abs(row["cast_reaction_N"]) for row in source])
                        moved = np.array([row["sleeve_up_mm"] for row in source])
                        if not np.all(np.diff(reactions) > 0.):
                            raise ValueError(f"Nonmonotone contact calibration for {label}, mesh {mesh}")
                        targets = np.array(PRESSURES_BAR) * force / (315 * 2)
                        travel = np.interp(targets, reactions, moved)
                        i = targets > reactions[-1]
                        travel[i] = moved[-1] + (targets[i]-reactions[-1]) * (
                              (moved[-1]-moved[-2])/(reactions[-1]-reactions[-2]))
                        travel[0] = 0.
                        travels = travel.tolist()
                row = run_station(Path(scratch) / (label + str(mesh)), station, fit, mesh, force,
                                  args.normal, args.timeout, True, args.curvature, travels, args.validate_only, args.open_zero_step)
                row.update(station=label, mesh_mm=mesh, global_case=selected["layout"]["name"])
                summary.append(row)
                args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print(label, mesh, row["status"], flush=True)


if __name__ == "__main__":
    main()

