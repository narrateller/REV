"""Volumetric diagnostic of the 60/40 chamber load path, N-mm-MPa."""
from hashlib import sha256
from collections import defaultdict
from itertools import product
import json
import re
from math import ceil, exp
from pathlib import Path
import sys
import os
import subprocess
from tempfile import TemporaryDirectory

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CALC = HERE.parents[1]
sys.path.insert(0, str(CALC / "T-1.7b"))

from frame_fea import BIN, fkm_parameters, mises, results_frd, stress_tensors, write_json
import numpy as np

REF = json.loads((CALC / "T-1.2b/results.json").read_text(encoding="utf-8"))
LOCK = REF["mechanical_lock_A"]
HIGH = REF["shoe_load"]["samples"]["upper_dose"]["reserve"]["high"]
STEP_MM = (24., 17., 12.)
MU = 0.15
STABILIZER_N_MM = 10.
GUIDE_LOWER_GAP_MM = 0.05
CASE = "local_guide"
OUTER_MM = 200.
SLOT_EDGE_MM = 148.
TAIL_EXTRA_MM = 0.
BRIDGE_H_MM = 35.
RAIL_H_MM = 90.
END_GUIDES = False
# Flat contacts and an idealized integral base. Root, guide and fixture geometry
# outside the published T-1.2b envelopes are assumptions for this diagnostic.
BODIES = ("SHOE", "LEFT", "RIGHT", "HOUSING")
PROPERTIES = {"SHOE": (600., 800., False), "LEFT": (700., 900., False),
              "RIGHT": (700., 900., False), "HOUSING": (650., 800., True)}


def subdivide(edges_mm, step_mm):
    return np.concatenate([np.linspace(a, b, ceil((b-a)/step_mm), endpoint=False)
                           for a, b in zip(edges_mm, edges_mm[1:])] + [np.array(edges_mm[-1:])])


def dimensions():
    length_mm, width_mm, height_mm = LOCK["shoe_envelope_mm"]
    key_overlap_mm = LOCK["rail_bearing_engagement_mm"]
    gap_mm = LOCK["side_gap_mm"]
    top_mm = height_mm + RAIL_H_MM
    half_width_mm = width_mm / 2
    inner_key_mm = half_width_mm - key_overlap_mm
    outer_key_mm = half_width_mm + gap_mm + key_overlap_mm + TAIL_EXTRA_MM
    return length_mm, height_mm, top_mm, half_width_mm, inner_key_mm, outer_key_mm


def housing_solid(x_mm, y_mm, z_mm, slot_edge_mm, rail_top_mm, end_guides):
    if z_mm < -60.:
        return True
    if z_mm < 0.:
        return abs(y_mm) >= 75.
    if z_mm < 160.-GUIDE_LOWER_GAP_MM:
        return abs(y_mm) >= 115.
    if z_mm < rail_top_mm:
        return abs(y_mm) >= slot_edge_mm
    if end_guides:
        return abs(y_mm) >= (75. if x_mm < 3. or x_mm > 207. else slot_edge_mm)
    return abs(y_mm) >= 115.


def set_case(case):
    global CASE, OUTER_MM, SLOT_EDGE_MM, TAIL_EXTRA_MM, BRIDGE_H_MM, RAIL_H_MM, END_GUIDES
    CASE = case
    by_case = {"local_guide": (200.,148.,0.,35.,90.,False),
               "full_travel": (220.,196.,12.,45.,90.,False),
               "end_supported": (220.,185.,0.,65.,120.,True)}
    OUTER_MM, SLOT_EDGE_MM, TAIL_EXTRA_MM, BRIDGE_H_MM, RAIL_H_MM, END_GUIDES = by_case[case]


def case_blocks(case):
    previous = CASE
    set_case(case)
    try:
        return blocks()
    finally:
        set_case(previous)


def blocks():
    lx, h, top, half, key_inside, key_outside = dimensions()
    start_mm, end_mm = HIGH["press"]["contact_x_mm"]
    x_mm = [5., start_mm, end_mm]
    assert end_mm - 5. == lx
    rail_x_mm = [-27.,3.,*x_mm,207.,237.] if END_GUIDES else x_mm
    housing_x_mm = [-35.,*rail_x_mm,245.] if END_GUIDES else [-15.,*x_mm,225.]
    return {
        "SHOE": (x_mm, [-half, -key_inside, -75., 0., 75., key_inside, half], [0., h], None),
        "LEFT": (rail_x_mm, [-key_outside, -115., -half, -key_inside], [h, top], None),
        "RIGHT": (rail_x_mm, [key_inside, half, 115., key_outside], [h, top], None),
        "HOUSING": (housing_x_mm,
                    [-OUTER_MM, -SLOT_EDGE_MM, -key_outside, -115.,
                     *([-key_inside] if END_GUIDES else []), -75., 0., 75.,
                     *([key_inside] if END_GUIDES else []), 115., key_outside, SLOT_EDGE_MM, OUTER_MM],
                    [-95., -60., 0., h-GUIDE_LOWER_GAP_MM, top, top + BRIDGE_H_MM],
                    lambda x,y,z, edge=SLOT_EDGE_MM, height=top, ends=END_GUIDES:housing_solid(
                        x,y,z,edge,height,ends)),
    }


def save_geo(path, block_data):
    lines = ['SetFactory("OpenCASCADE");', '// N-mm section model. Solved with a structured C3D8 mesh.']
    tag = 0
    for name, (x_mm, y_mm, z_mm, occupied) in block_data.items():
        tags = []
        axial_sections = zip(x_mm,x_mm[1:]) if END_GUIDES and name == "HOUSING" else [(x_mm[0],x_mm[-1])]
        for x0,x1 in axial_sections:
            for a, b in zip(y_mm, y_mm[1:]):
                for c, d in zip(z_mm, z_mm[1:]):
                    if occupied and not occupied((x0+x1)/2, (a+b)/2, (c+d)/2):
                        continue
                    tag += 1
                    tags.append(str(tag))
                    lines.append(f"Box({tag}) = {{{x0}, {a}, {c}, {x1-x0}, {b-a}, {d-c}}};")
        lines.append(f'Physical Volume("{name}") = {{{",".join(tags)}}};')
    path.write_text("\n".join(lines)+"\n", encoding="ascii")


FACES = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
         (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))
OFFSETS = ((0,0,0), (1,0,0), (1,1,0), (0,1,0), (0,0,1), (1,0,1), (1,1,1), (0,1,1))
NEIGHBORS = ((0,0,-1), (0,0,1), (0,-1,0), (1,0,0), (0,1,0), (-1,0,0))


def mesh(step_mm, block_data):
    coords = [(0., 0., 0.)]
    elems = {}
    outside_faces = defaultdict(list)
    for name, (x, y, z, occupied) in block_data.items():
        axes = [subdivide(x, step_mm), subdivide(y, step_mm), subdivide(z, step_mm)]
        rects = {}
        nodes = {}
        for i, j, k in product(*(range(len(axis)-1) for axis in axes)):
            if occupied and not occupied(*((axis[n]+axis[n+1])/2 for axis,n in zip(axes,(i,j,k)))):
                continue
            tags = []
            for di, dj, dk in OFFSETS:
                index = (i+di, j+dj, k+dk)
                if index not in nodes:
                    nodes[index] = len(coords)
                    coords.append(tuple(axis[n] for axis, n in zip(axes, index)))
                tags.append(nodes[index])
            eid = len(elems) + 1
            elems[eid] = (name, tags)
            rects[i, j, k] = eid
        for (i, j, k), eid in rects.items():
            for face, (di, dj, dk) in enumerate(NEIGHBORS):
                if (i+di, j+dj, k+dk) not in rects:
                    outside_faces[name].append((eid, face+1, [elems[eid][1][n] for n in FACES[face]]))
    return np.array(coords), elems, outside_faces


def select(faces, coords, *, axis, plane_mm, offset_axis, interval_mm, axial_limit=False):
    lo_mm, hi_mm = interval_mm
    return [(eid, side, nodes) for eid, side, nodes in faces
            if np.max(abs(coords[nodes, axis]-plane_mm)) < 1e-6
            and lo_mm <= coords[nodes, offset_axis].mean() <= hi_mm
            and (not axial_limit or 5. <= coords[nodes, 0].mean() <= 205.)]


def face_quadrature(xyz):
    for xi, eta in product((-1/np.sqrt(3), 1/np.sqrt(3)), repeat=2):
        weights = np.array([(1-xi)*(1-eta), (1+xi)*(1-eta), (1+xi)*(1+eta), (1-xi)*(1+eta)])/4
        area_mm2 = np.linalg.norm(np.cross(xyz[1]-xyz[0], xyz[3]-xyz[0]))
        yield weights, weights @ xyz, area_mm2 / 4


def loads(xyz, faces):
    out = np.zeros_like(xyz)
    x_start_mm = HIGH["press"]["contact_x_mm"][0]
    share = LOCK["max_transverse_load_share"]
    eccentric_mm = (share-0.5) * LOCK["shoe_support_span_mm"]
    slope_per_mm = 3 * eccentric_mm / 75.**2
    conditions = [("SHOE", 2, 0., 1, (-75.,75.), 2, 1, True),
                  ("HOUSING", 2, -60., 1, (-75.,75.), 2, -1, False),
                  ("HOUSING", 1, -75., 2, (-60.,0.), 1, -1, False),
                  ("HOUSING", 1, 75., 2, (-60.,0.), 1, 1, False)]
    for body, axis, plane, other, interval, component, sign, skew in conditions:
        group = select(faces[body], xyz, axis=axis, plane_mm=plane,
                       offset_axis=other, interval_mm=interval, axial_limit=True)
        for _, _, tags in group:
            if xyz[tags, 0].mean() < x_start_mm:
                continue
            for shape, (x_mm,y_mm,_), area_mm2 in face_quadrature(xyz[tags]):
                pressure_MPa = HIGH["press"]["radial_at_contact_start_MPa"] * exp(
                    -HIGH["attenuation_per_mm"] * (x_mm-x_start_mm))
                if skew:
                    pressure_MPa *= 1 + slope_per_mm*y_mm
                out[tags, component] += sign * pressure_MPa*area_mm2*shape
    measured_N = out[out[:,2]>0,2].sum()
    out *= LOCK["max_shoe_load_at_300_bar_N"] / measured_N
    return out


def configure(xyz, elems, faces):
    _, h, top, half, inside, outside = dimensions()
    contacts = {}
    for name, sign in (("LEFT", -1), ("RIGHT", 1)):
        shoe_range = sorted((sign*inside, sign*half))
        body_range = sorted((sign*115., sign*outside))
        top_range = sorted((sign*inside,sign*outside)) if END_GUIDES else body_range
        for suffix, part, z_mm, limits in (
                ("SHOE", "SHOE", h, shoe_range), ("LOWER", name, h, shoe_range),
                ("UPPER", name, top, top_range), ("GUIDE", "HOUSING", top, top_range),
                ("HEEL",name,h,body_range), ("GUIDEFLOOR","HOUSING",h-GUIDE_LOWER_GAP_MM,body_range)):
            end_pad = END_GUIDES and suffix in ("UPPER","GUIDE")
            rows = select(faces[part],xyz,axis=2,plane_mm=z_mm,offset_axis=1,
                          interval_mm=limits,axial_limit=not end_pad)
            if end_pad:
                rows = [(eid,face,tags) for eid,face,tags in rows
                        if -27. <= xyz[tags,0].mean() <= 3. or 207. <= xyz[tags,0].mean() <= 237.]
            contacts[name+suffix] = rows
            assert rows, (name, suffix)
    fixed = np.flatnonzero(xyz[:,2] == -95.)
    anchors = {}
    for name in ("SHOE","LEFT","RIGHT"):
        part_nodes = np.unique([tags for body, tags in elems.values() if body == name])
        center = xyz[part_nodes].mean(axis=0)
        targets = [(center[0]-50, center[1], center[2]), (center[0]+50, center[1], center[2])]
        targets.append((center[0], center[1] + np.ptp(xyz[part_nodes,1])/4, center[2]))
        anchors[name] = [int(part_nodes[np.linalg.norm(xyz[part_nodes]-target,axis=1).argmin()]) for target in targets]
    return contacts, fixed, anchors


def contact_pairs():
    return [(name+slave,name+master) for name in ("LEFT","RIGHT")
            for slave,master in (("SHOE","LOWER"),("UPPER","GUIDE"),("HEEL","GUIDEFLOOR"))]


def write_deck(path, mesh_name, xyz, elems, contacts, fixed, anchors, force_N, case_pressure_bar):
    lines = ["*HEADING", "T-2.2 chamber contact, N mm MPa", f"*INCLUDE,INPUT={mesh_name}"]
    lines += ["*MATERIAL,NAME=STEEL","*ELASTIC","210000.,0.3"]
    lines += [f"*SOLID SECTION,ELSET={name},MATERIAL=STEEL" for name in BODIES]
    for name, faces in contacts.items():
        lines += [f"*SURFACE,TYPE=ELEMENT,NAME={name}"] + [f"{eid},S{face}" for eid,face,_ in faces]
    lines += ["*SURFACE INTERACTION,NAME=LOCK_CONTACT","*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR",
              "100000.,1.", "*FRICTION", f"{MU},10000."]
    for slave, master in contact_pairs():
        lines += ["*CONTACT PAIR,INTERACTION=LOCK_CONTACT,TYPE=SURFACE TO SURFACE",f"{slave},{master}"]
    # Weak DELTA springs eliminate the unloaded vertical rigid-body modes.
    # Their total absolute reaction is checked against the applied shoe force.
    first = len(elems)+1
    spring_nodes = [node for nodes in anchors.values() for node in nodes]
    lines += ["*ELEMENT,TYPE=SPRING1,ELSET=STABILIZER"]
    lines += [f"{first+i},{tag}" for i,tag in enumerate(spring_nodes)]
    lines += ["*SPRING,ELSET=STABILIZER","3",f"{STABILIZER_N_MM:.3f}"]
    lines += ["*NSET,NSET=BASE"] + [",".join(map(str, fixed[i:i+16])) for i in range(0,len(fixed),16)]
    lines += ["*BOUNDARY","BASE,1,3"]
    for first_node, second_node, _ in anchors.values():
        lines += [f"{first_node},1,2",f"{second_node},2,2"]
    lines += ["*STEP,NLGEOM,INC=160", "*STATIC", ".2,1.,1.e-6,.25", "*CLOAD"]
    for node, component in zip(*np.nonzero(force_N)):
        lines.append(f"{node},{component+1},{force_N[node,component]*case_pressure_bar/300:.12g}")
    lines += ["*NODE FILE,FREQUENCY=999999","U,RF","*EL FILE,FREQUENCY=999999","S",
              "*CONTACT FILE,FREQUENCY=999999","CDIS,CSTR"]
    for slave, master in contact_pairs():
        lines += [f"*CONTACT PRINT,SLAVE={slave},MASTER={master},FREQUENCY=999999", "CF"]
    lines += ["*END STEP"]
    path.write_text("\n".join(lines)+"\n",encoding="ascii",newline="\n")


def write_mesh(path, xyz, elems):
    with path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write("*NODE\n")
        for index, (x,y,z) in enumerate(xyz[1:],1):
            stream.write(f"{index},{x:.12g},{y:.12g},{z:.12g}\n")
        for name in BODIES:
            stream.write(f"*ELEMENT,TYPE=C3D8,ELSET={name}\n")
            for eid, (body, tags) in elems.items():
                if name == body:
                    stream.write(f"{eid},"+",".join(map(str,tags))+"\n")


def contact_pressure_MPa(path):
    pressure = {}
    is_contact = False
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if line.startswith(" -4"):
                is_contact = line.split()[1] == "CONTACT"
                if is_contact:
                    pressure.clear()
            elif is_contact and line.startswith(" -1"):
                pressure[int(line[3:13])] = float(line[49:61])
    return pressure


def pair_forces(path):
    raw = path.read_text(encoding="ascii")
    results = {}
    # Each CF line records the slave-pair resultant in global coordinates.
    for label, block in re.findall(r"statistics for slave set (\w+),[^\n]*\n(.*?)(?=statistics for slave set|\Z)",
                                   raw, flags=re.DOTALL|re.IGNORECASE):
        vector = re.search(r"total surface force[^\n]*\n\s*([^\n]+)", block)
        area_force = re.search(r"area,\s+normal force[^\n]*\n\s*([^\n]+)", block)
        if vector and area_force:
            area_mm2, normal_N, shear_N = map(float, area_force[1].split()[:3])
            values = [float(value) for value in vector[1].split()]
            results[label] = dict(global_force_N=values[:3], origin_moment_Nmm=values[3:],
                                  engaged_area_mm2=area_mm2,
                                  normal_force_N=normal_N if area_mm2 else 0.,
                                  shear_force_N=shear_N if area_mm2 else 0.)
    if set(results) != {slave for slave, _ in contact_pairs()}:
        raise RuntimeError(f"Unable to parse contact resultants: {raw[-3500:]}")
    return results


def summary(xyz, elems, faces, contacts, fixed, anchors, force_N, solutions, pressures, pairs):
    static, fatigue = solutions
    fixed_all = np.concatenate((fixed, [n for nodes in anchors.values() for n in nodes]))
    shoe_nodes = np.unique([tags for _, _, tags in faces["SHOE"]])
    loaded = shoe_nodes[(xyz[shoe_nodes,2]==0.) & (abs(xyz[shoe_nodes,1])<=75.) &
                        (xyz[shoe_nodes,0]>=HIGH["press"]["contact_x_mm"][0])]
    total_load_N = LOCK["max_shoe_load_at_315_bar_N"]
    reaction = static["FORC"][fixed_all].sum(axis=0)
    # CCX FORC at an available constrained degree of freedom only.
    reaction[2] = static["FORC"][fixed,2].sum()
    spring_N = -STABILIZER_N_MM*sum(static["DISP"][nodes,2].sum() for nodes in anchors.values())
    spring_abs_N = STABILIZER_N_MM*sum(np.abs(static["DISP"][nodes,2]).sum() for nodes in anchors.values())
    static_stress = static["STRESS"]
    static_vm = mises(static_stress)
    cyclic_vm = mises(fatigue["STRESS"])
    fatigue_tensile_mean = np.maximum(0., np.linalg.eigvalsh(stress_tensors(fatigue["STRESS"]/2))[:,-1])
    parts = {}
    for name in BODIES:
        ids = np.unique([tags for body,tags in elems.values() if body==name])
        rp_MPa, rm_MPa, cast = PROPERTIES[name]
        allow_MPa, kR, jG, M = fkm_parameters(rm_MPa, 6.3, cast, forging=not cast)
        combined_MPa = cyclic_vm/2 + M*fatigue_tensile_mean
        i = ids[static_vm[ids].argmax()]
        j = ids[combined_MPa[ids].argmax()]
        parts[name] = dict(static_MPa=float(static_vm[i]), static_xyz_mm=xyz[i].tolist(),
                           static_factor=float(rp_MPa/static_vm[i]),
                           fkm_factor_n_sigma_1=float(allow_MPa/combined_MPa[j]),
                           fkm_xyz_mm=xyz[j].tolist(), fkm_jG=jG, fkm_kR=kR, fkm_M_sigma=M,
                           static_yield_MPa=rp_MPa, tensile_MPa=rm_MPa)
        if name in ("LEFT","RIGHT"):
            parts[name]["nominal_axis_peak_components_MPa"] = {
                "sigma_x_axial_bending":float(np.abs(static_stress[ids,0]).max()),
                "sigma_y_transverse_bending":float(np.abs(static_stress[ids,1]).max()),
                "tau_yz_transverse_shear":float(np.abs(static_stress[ids,4]).max()),
                "tau_xz_axial_shear":float(np.abs(static_stress[ids,5]).max()),
            }
    contact = {}
    for name, _ in contact_pairs():
        ids = np.unique([tags for _,_,tags in contacts[name]])
        a = max((pressures.get(int(i), 0.) for i in ids), default=0.)
        area_mm2 = pairs[name]["engaged_area_mm2"]
        material_left = "SHOE" if name.endswith("SHOE") else "HOUSING"
        allowance_MPa = 0.60 * min(PROPERTIES[material_left][0], PROPERTIES["LEFT"][0])
        contact[name] = dict(**pairs[name], pressure_nodal_peak_MPa=a,
                             actual_mean_bearing_MPa=abs(pairs[name]["normal_force_N"])/area_mm2 if area_mm2 else 0.,
                             nominal_mean_bearing_MPa=abs(pairs[name]["normal_force_N"])/(200.*LOCK["rail_bearing_engagement_mm"]),
                             local_bearing_screen_MPa=allowance_MPa,
                             nodes_with_positive_pressure=sum(pressures.get(int(i),0.)>0 for i in ids))
    shoe_reactions_N = np.array([abs(pairs[name]["global_force_N"][2]) for name in ("LEFTSHOE","RIGHTSHOE")])
    signed_shoe_spring_N = -STABILIZER_N_MM*static["DISP"][anchors["SHOE"],2].sum()
    shoe_reaction = shoe_reactions_N.sum()
    housing_nodes = np.unique([tags for _, _, tags in faces["HOUSING"]])
    loaded_housing = housing_nodes[(xyz[housing_nodes,0]>=HIGH["press"]["contact_x_mm"][0]) & (xyz[housing_nodes,0]<=205.)]
    floor = loaded_housing[(xyz[loaded_housing,2]==-60.) & (abs(xyz[loaded_housing,1])<=75.)]
    die_side = loaded_housing[(abs(xyz[loaded_housing,1])==75.) & (xyz[loaded_housing,2]>=-60.) & (xyz[loaded_housing,2]<=0.)]
    def section_change(disp):
        return dict(height_upper_bound_mm=float(disp[loaded,2].max()-disp[floor,2].min()),
                    width_upper_bound_mm=float(disp[die_side[xyz[die_side,1]>0],1].max() -
                                               disp[die_side[xyz[die_side,1]<0],1].min()))
    return dict(parts=parts, contact=contact, shoe_vertical_motion_mm=float(static["DISP"][loaded,2].max()),
                die_section_change_static=section_change(static["DISP"]),
                die_section_change_300_bar=section_change(fatigue["DISP"]),
                shoe_vertical_motion_at_300_bar_mm=float(fatigue["DISP"][loaded,2].max()),
                shoe_contact_share=(shoe_reactions_N/shoe_reaction).tolist(),
                shoe_equilibrium_fraction=float(abs(total_load_N-shoe_reaction+signed_shoe_spring_N)/total_load_N),
                absolute_stabilizer_reaction_N=float(spring_abs_N), signed_stabilizer_reaction_N=float(spring_N), fixed_reaction_N=reaction.tolist(),
                applied_net_force_N=(force_N*1.05).sum(axis=0).tolist(),
                global_force_balance_fraction=float(np.linalg.norm(reaction+force_N.sum(axis=0)*1.05+[0.,0.,spring_N])/total_load_N),
                loaded_max_vertical_motion_xyz_mm=xyz[loaded[static["DISP"][loaded,2].argmax()]].tolist())


def run_ccx(path):
    env = dict(os.environ, OMP_NUM_THREADS="1", CCX_NPROC_RESULTS="1", CCX_NPROC_EQUATION_SOLVER="1")
    log_path = path.with_suffix(".log")
    with log_path.open("w", encoding="ascii") as log:
        result = subprocess.run([str(BIN/"ccx.exe"), "-i", path.stem], cwd=path.parent,
                                stdout=log, stderr=subprocess.STDOUT, env=env, timeout=900)
    log_text = log_path.read_text(encoding="ascii", errors="replace")
    if result.returncode or "Job finished" not in log_text or "*ERROR" in log_text:
        raise RuntimeError(f"CalculiX exit {result.returncode}\n{log_text[-4500:]}")


def solve(level):
    block_data = blocks()
    xyz, elems, faces = mesh(STEP_MM[level], block_data)
    contacts, fixed, anchors = configure(xyz, elems, faces)
    force_N = loads(xyz, faces)
    with TemporaryDirectory(prefix="t22_lock_", dir=HERE.parent) as scratch:
        folder = Path(scratch)
        mesh_path = folder/"lock_mesh.inp"
        write_mesh(mesh_path, xyz, elems)
        solutions = []
        digest = {}
        for pressure_bar in (315,300):
            path = folder/f"lock_{pressure_bar}.inp"
            write_deck(path, mesh_path.name, xyz, elems, contacts, fixed, anchors, force_N, pressure_bar)
            digest[pressure_bar] = sha256(path.read_bytes()).hexdigest()
            run_ccx(path)
            if pressure_bar == 315:
                pressures = contact_pressure_MPa(path.with_suffix(".frd"))
                pairs = pair_forces(path.with_suffix(".dat"))
                if level == 0:
                    (HERE/f"{CASE}_0_315.inp").write_bytes(path.read_bytes())
            solutions.append(results_frd(path.with_suffix(".frd"),len(xyz)))
        result = summary(xyz, elems, faces, contacts, fixed, anchors, force_N, solutions, pressures, pairs)
    result.update(level=level, step_max_mm=STEP_MM[level], nodes=len(xyz)-1, elements=len(elems),
                  friction=MU, element="C3D8", deck_sha256=digest, status="DIAGNOSTIC",
                  case=CASE, guide_heel_clearance_mm=GUIDE_LOWER_GAP_MM, housing_section_outer_width_mm=2*OUTER_MM,
                  guide_slot_edge_mm=SLOT_EDGE_MM, rail_tail_extension_mm=TAIL_EXTRA_MM, bridge_depth_mm=BRIDGE_H_MM,
                  rail_height_mm=RAIL_H_MM, axial_end_guides=END_GUIDES,
                  nominal_unlocked_outboard_clearance_mm=SLOT_EDGE_MM-dimensions()[-1]-LOCK["key_slide_mm"])
    write_json(HERE/f"{CASE}_{level}.json", result)
    print(level, result["global_force_balance_fraction"], result["parts"], flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("levels",nargs="+",type=int)
    parser.add_argument("--case",choices=("local_guide","full_travel","end_supported"),default="local_guide")
    args = parser.parse_args()
    set_case(args.case)
    save_geo(HERE/f"{CASE}.geo", blocks())
    for level in args.levels:
        solve(level)



