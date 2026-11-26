"""Solid cover sector with pressure passages and elastic tie restraint."""
import argparse
import json
import os
from math import cos, pi, radians, sin
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CALC = Path(os.environ["REV_T22_INPUT_ROOT"])/"calc" if "REV_T22_INPUT_ROOT" in os.environ else HERE.parents[1]
sys.path.insert(0, str(CALC / "T-1.7b"))

import numpy as np
from scipy.spatial import cKDTree
import cap_pressure as old_cap
from frame_analytic import CYLINDER, E_MPa, RHO_kg_mm3, STUDS, STUD_HOLE_RADIUS_mm
from frame_fea import (BIN, fkm_parameters, mises, normal_gradient, notch_support, patch_loads,
                       plane_triangles, quadrature, read_mesh, results_frd, ring, run_tool,
                       stress_tensors, surface_normals, write_json, write_mesh_include)
from frame_geometry import Geo

# The DN125 MA line is a hydraulic interface. Eight parallel branches are an
# area-preserving diagnostic route, pending a collector and rated joint design.
MA_ANGLES_DEG = (11.25, 78.75, 101.25, 168.75, 191.25, 258.75, 281.25, 348.75)
MA_R_MM, MA_Z_MM = 22., 51.
CASE = "paired"
ROUND_2 = False
SECTOR_COUNT = 4
SECTOR_ANGLE_RAD = pi/2
MESH_SIZES_MM = ((28.,5.),(24.,3.5),(20.,2.4),(17.,1.85))
VALVE_PRELOAD_EACH_N = 216000.
STUD_POSITIONS = STUDS
PREFILL_R_MM, SEAL_R_MM = 62., 69.25
TAP_R_MM, TAP_DEPTH_MM = 12., 55.
VALVE_PHI = 0.23
STUD_AS_MM2 = pi/4*(36.-0.938194*4.)**2
STUD_EFFECTIVE_MM = 398.+105.+132.
STUD_K_N_MM = 16*E_MPa*STUD_AS_MM2/STUD_EFFECTIVE_MM
BARREL_K_N_MM = E_MPa*pi/4*(352.**2-280.**2)/398.

MA_AXES = np.array([(cos(radians(angle)), sin(radians(angle))) for angle in MA_ANGLES_DEG])


def geometry(level, thick_mm, blend_mm):
    geo = Geo()
    body = geo.cylinder(0,0,0,thick_mm,260.)
    old_cap.DEPTH_mm, old_cap.SEAT_mm, old_cap.PORT_BLEND_mm = thick_mm,0.,4.
    tools = [old_cap.cavity_profile(geo)]
    for axis in MA_AXES:
        tag = geo.new()
        x,y = axis
        geo.emit(f"Cylinder({tag}) = {{{50*x},{50*y},{MA_Z_MM},{214*x},{214*y},0,{MA_R_MM}}};")
        tools.append(tag)
    geo.cut(str(body), tools, "pressure_body")
    volume = "pressure_body[0]"
    if blend_mm:
        geo.emit(f"intersection[] = Curve In BoundingBox {{-67,-67,{MA_Z_MM-MA_R_MM-1},67,67,{MA_Z_MM+MA_R_MM+1}}};")
        geo.emit('Printf("FILLET_EDGES %g",#intersection[]);')
        geo.emit(f"Fillet {{pressure_body[0]}} {{intersection[]}} {{{blend_mm}}}")
        geo.emit("rounded_volumes[] = Volume{:};")
        geo.emit('Printf("ROUNDED_VOLUMES %g",#rounded_volumes[]);')
        volume = "rounded_volumes[0]"
    tools = [geo.cylinder(x,y,-1.,thick_mm+2.,STUD_HOLE_RADIUS_mm) for x,y in STUD_POSITIONS]
    for x,y in old_cap.VALVE_TAPS:
        z_mm = thick_mm-TAP_DEPTH_MM+TAP_R_MM
        tools.append(geo.cylinder(x,y,z_mm,thick_mm-z_mm+1,TAP_R_MM))
        dome = geo.new()
        geo.emit(f"Sphere({dome}) = {{{x},{y},{z_mm},{TAP_R_MM}}};")
        tools.append(dome)
        if CASE == "recessed_taps":
            inlet = geo.new()
            geo.emit(f"Cone({inlet}) = {{{x},{y},{thick_mm-10},0,0,11,12.,15.3}};")
            tools.append(inlet)
    geo.cut(volume, tools, "cap")
    geo.emit('Printf("VOL %.15g",Mass Volume{cap[0]});')
    if ROUND_2:
        side = 285.
        points = [geo.new() for _ in range(3)]
        for point, (x,y) in zip(points, ((0.,0.),(side,0.),
                               (side*cos(SECTOR_ANGLE_RAD),side*sin(SECTOR_ANGLE_RAD)))):
            geo.emit(f"Point({point}) = {{{x},{y},-10}};")
        edges = [geo.new() for _ in points]
        for edge, a, b in zip(edges,points,points[1:]+points[:1]):
            geo.emit(f"Line({edge}) = {{{a},{b}}};")
        loop, surface = geo.new(), geo.new()
        geo.emit(f"Curve Loop({loop}) = {{{','.join(map(str,edges))}}};")
        geo.emit(f"Plane Surface({surface}) = {{{loop}}};")
        geo.emit(f"wedge[] = Extrude {{0,0,{thick_mm+30}}} {{ Surface{{{surface}}}; }};")
        clip = "wedge[1]"
    else:
        geo.emit(f"clip = newv; Box(clip) = {{0,0,-10,280,280,{thick_mm+30}}};")
        clip = "clip"
    geo.emit(f"sector[] = BooleanIntersection{{ Volume{{cap[]}}; Delete; }}{{ Volume{{{clip}}}; Delete; }};")
    far, near = MESH_SIZES_MM[level]
    geo.emit(f"Mesh.MeshSizeMax={far}; Mesh.MeshSizeFromPoints=0; Mesh.MeshSizeFromCurvature=10;")
    geo.emit("Mesh.MeshSizeExtendFromBoundary=0; Mesh.SecondOrderLinear=1; Mesh.RandomSeed=42; Mesh.MaxNumThreads3D=1;")
    radius = "Sqrt(x*x+y*y)"
    def channel_distance(axis):
        a, b = axis
        cross = f"({b:.10g}*x-({a:.10g})*y)"
        return f"Abs(Sqrt(({cross})^2+(z-{MA_Z_MM})^2)-{MA_R_MM})"
    a, b = map(channel_distance, MA_AXES[:2])
    dist = f"Min(Max(Abs({radius}-67),Abs(z-{MA_Z_MM})/2),Min(Min({a},{b}),Max(Abs({radius}-120),{thick_mm}-z)))"
    geo.emit(f'Field[1] = MathEval; Field[1].F = "{near}+({far}-{near})*Min(1,Max(0,({dist}-5)/18))"; Background Field = 1;')
    return "\n".join(geo.lines)+"\n"


def face_weights(coords, faces, z_mm, mask):
    return patch_loads(coords,plane_triangles(coords,faces,2,z_mm),mask,"cover patch")[0]


def symmetry_normals():
    return np.array([[0.,1.],[-sin(SECTOR_ANGLE_RAD),cos(SECTOR_ANGLE_RAD)]])


def physical_face_ids(coords, faces):
    distances_mm = coords[faces[:,:3],:2] @ symmetry_normals().T
    return ~((abs(distances_mm)<1e-5).all(axis=1).any(axis=1))


def pressure_load(coords, faces, normals, thick_mm):
    xyz = coords[faces]
    z = xyz[:,:,2]
    radius = np.linalg.norm(xyz[:,:,:2],axis=2)
    is_front = (abs(z)<1e-5).all(axis=1)
    is_rear = (abs(z-thick_mm)<1e-5).all(axis=1)
    is_flat = is_front | is_rear
    is_outer = (radius>259.9).all(axis=1)
    is_sym = ~physical_face_ids(coords,faces)
    if ROUND_2:
        # Straight-sided C3D10 faces have a single physical normal. In
        # particular the oblique cut must not contaminate pressure normals.
        normal = np.cross(xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0])
        nodal_direction = normals[faces].sum(axis=1)
        sign = np.where(np.einsum("ij,ij->i", normal, nodal_direction)<0., -1., 1.)
        normal *= (sign/np.maximum(np.linalg.norm(normal,axis=1),1e-20))[:,None]
    load_N_MPa = np.zeros_like(coords)
    for shape, centers, area_mm2 in quadrature(xyz):
        r = np.linalg.norm(centers[:,:2],axis=1)
        projection = centers[:,:2]@MA_AXES.T
        tangential = abs(centers[:,0,None]*MA_AXES[:,1] - centers[:,1,None]*MA_AXES[:,0])
        transverse = np.hypot(tangential, centers[:,2,None]-MA_Z_MM)
        ma = np.any((projection>49.) & (transverse<MA_R_MM+4.) & (transverse>MA_R_MM-2.), axis=1)
        wet = (is_front & (r<=140.)) | (is_rear & (r<=SEAL_R_MM))
        wet |= (~is_flat & ~is_outer & ~is_sym & ((r<=PREFILL_R_MM+4.001) | ma))
        if not ROUND_2:
            normal = shape@normals[faces]
            normal /= np.maximum(np.linalg.norm(normal,axis=1),1e-20)[:,None]
        traction = -(area_mm2*wet)[:,None]*normal
        np.add.at(load_N_MPa, faces.ravel(), (traction[:,None,:]*shape[None,:,None]).reshape(-1,3))
    return load_N_MPa


def positive_patch_weights(weights):
    # A Winkler spring coefficient must be nonnegative. Positive consistent
    # quadratic load weights give a lumped nodal representation of stiffness.
    values = np.maximum(weights,0.)
    return values/values.sum()


def joint(coords, faces, normals, thick_mm):
    bore_N_MPa = pressure_load(coords, faces, normals, thick_mm)
    hydrostatic_N_MPa = pi*140.**2/SECTOR_COUNT
    valve_N_MPa = pi*SEAL_R_MM**2/SECTOR_COUNT
    # B port pressure thrust closes through ZSF. Keep and report the raw
    # integrated resultant before reconciling projected area quadrature.
    pressure_integral_error = (bore_N_MPa[:,2].sum()+valve_N_MPa-hydrostatic_N_MPa)/hydrostatic_N_MPa
    correction_N_MPa = hydrostatic_N_MPa - valve_N_MPa - bore_N_MPa[:,2].sum()
    barrel = face_weights(coords,faces,0.,lambda x,y:ring(x,y,0.,0.,141.,175.,3.))
    studs = face_weights(coords,faces,thick_mm,lambda x,y:sum(
        ring(x,y,a,b,STUD_HOLE_RADIUS_mm,33.,2.) for a,b in STUD_POSITIONS))
    def valve_seat(x,y):
        if CASE == "paired":
            return ring(x,y,0.,0.,70.,104.,2.)
        mount = ring(x,y,0.,0.,max(70., SEAL_R_MM),146.,2.)
        cone = sum(ring(x,y,a,b,12.,34.,3.) for a,b in old_cap.VALVE_TAPS)
        return mount * (0.4 + 0.6*cone)
    valve = face_weights(coords,faces,thick_mm,valve_seat)
    # Idealized tap traction spread over the first loaded threads.
    # Integrate the half tap at the oblique symmetry plane.
    taps = np.zeros(len(coords))
    tap_positions = [(a,b) for a,b in old_cap.VALVE_TAPS
                     if b >= -1e-8 and (-a*sin(SECTOR_ANGLE_RAD)+b*cos(SECTOR_ANGLE_RAD)) <= 1e-8]
    for a,b in tap_positions:
        xyz = coords[faces]
        radius = np.linalg.norm(xyz[:,:,:2]-[a,b],axis=2)
        selected = faces[(np.max(abs(radius[:,:3]-TAP_R_MM),axis=1)<0.12)
                         & (xyz[:,:,2].mean(axis=1)<thick_mm-5)
                         & (xyz[:,:,2].mean(axis=1)>thick_mm-36)]
        local = np.zeros(len(coords))
        for shape, centers, da in quadrature(coords[selected]):
            depth_mm = thick_mm-centers[:,2]
            weights = np.ones(len(selected))
            if CASE == "recessed_taps":
                weights = np.clip((depth_mm-10)/7,0,1)*np.clip((36-depth_mm)/8,0,1)
            np.add.at(local, selected.ravel(), ((da*weights)[:,None]*shape[None,:]).ravel())
        if local.sum() <= 0:
            raise RuntimeError(f"No active tap faces at {(a,b)} mm")
        taps += local/local.sum()/len(tap_positions)
    assert np.isclose(taps.sum(),1.)
    bore_N_MPa[:,2] += correction_N_MPa*valve
    bore_N_MPa[:,2] += valve_N_MPa*(VALVE_PHI*taps+(1-VALVE_PHI)*valve)
    return bore_N_MPa, barrel, studs, valve, taps, pressure_integral_error


def symmetry_layout(coords, active):
    distances_mm = coords[active,:2] @ symmetry_normals().T
    return tuple(active[abs(distances_mm[:,i])<1e-5] for i in range(2))


def case_deck(path, sym_nodes, stiffness_N_mm, forces_N):
    lines = ["*HEADING","T-2.2 separate CY-MAIN rear cap, N mm MPa","*INCLUDE,INPUT=cap_mesh.inp"]
    for name,tags in zip(("SYM_START","SYM_END"),sym_nodes):
        lines += [f"*NSET,NSET={name}"]
        lines += [",".join(map(str,tags[i:i+16])) for i in range(0,len(tags),16)]
    start_nodes, end_nodes = sym_nodes
    assert len(start_nodes) and len(end_nodes) and not set(start_nodes).intersection(end_nodes)
    if ROUND_2:
        # The first DOF listed is eliminated. Leave in-plane radial and axial
        # displacement free, including at the through-hole and ZSF half tap.
        sy = cos(SECTOR_ANGLE_RAD)
        sx = -sin(SECTOR_ANGLE_RAD)
        for node in end_nodes:
            lines += ["*EQUATION","2",f"{node},2,{sy:.14g},{node},1,{sx:.14g}"]
    lines += ["*MATERIAL,NAME=FORGED","*ELASTIC","210000.,0.3",
              "*SOLID SECTION,ELSET=TRAVERSE,MATERIAL=FORGED"]
    # Group approximately equal stiffness to keep a small deck.
    existing = path.parent/"cap_mesh.inp"
    total_tets = sum(1 for line in existing.open(encoding="ascii") if line.count(",")==10)
    rounded = np.round(stiffness_N_mm,1)
    for i,k_N_mm in enumerate(np.unique(rounded[rounded>0.]),1):
        nodes = np.flatnonzero(rounded==k_N_mm)
        name = f"ELASTIC_{i}"
        lines += [f"*ELEMENT,TYPE=SPRING1,ELSET={name}"]
        for node in nodes:
            total_tets += 1
            lines.append(f"{total_tets},{node}")
        lines += [f"*SPRING,ELSET={name}","3",f"{k_N_mm:.1f}"]
    lines += ["*BOUNDARY","SYM_START,2,2"]
    if not ROUND_2:
        lines += ["SYM_END,1,1"]
    lines += ["*STEP","*STATIC","*CLOAD"]
    for node,axis in zip(*np.nonzero(abs(forces_N)>1e-10)):
        lines.append(f"{node},{axis+1},{forces_N[node,axis]:.12g}")
    lines += ["*NODE FILE,GLOBAL=YES","U,RF","*EL FILE","S","*END STEP"]
    path.write_text("\n".join(lines)+"\n",encoding="ascii",newline="\n")
    return rounded


def control_zones(coords, active, thick_mm):
    radial = np.linalg.norm(coords[:,:2],axis=1)
    z_mm = coords[:,2]
    return {"global":active,"MA_junction":active[(radial[active]<74)&(abs(z_mm[active]-MA_Z_MM)<30)],
            "MA_stud_ligament":active[(radial[active]>195)&(abs(z_mm[active]-MA_Z_MM)<30)],
            "ZSF_taps":active[(abs(radial[active]-120)<18)&(z_mm[active]>thick_mm-TAP_DEPTH_MM-3)]}


def interior_probes(coords, tets, fields):
    """Recover nodal stress at fixed interior positions on straight C3D10 elements."""
    points_mm = {
        "ZSF_loaded_wall": (99.9, 38.9, 131.1),
        "ZSF_recess": (98.3, 40.1, 135.0),
        "MA_stud_ligament": (218.0, 23.0, 51.5),
        "MA_junction": (63.5, 2.0, 74.5),
    }
    vertices = coords[tets[:, :4]]
    index = cKDTree(vertices.mean(axis=1))
    result = {}
    for name, xyz_mm in points_mm.items():
        _, candidates = index.query(xyz_mm, k=96)
        v = vertices[candidates]
        local = np.linalg.solve(
            (v[:, 1:] - v[:, :1]).transpose(0, 2, 1),
            (xyz_mm - v[:, 0])[..., None],
        )[..., 0]
        bary = np.column_stack((1 - local.sum(axis=1), local))
        i = np.argmax(bary.min(axis=1))
        if bary[i].min() < -1e-8:
            raise RuntimeError(f"Probe {name} {xyz_mm} outside C3D10 mesh")
        l = bary[i]
        shape = np.concatenate((l*(2*l-1), [4*l[a]*l[b] for a,b in
                              ((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))]))
        nodes = tets[candidates[i]]
        zero, relief, cyclic, unclamped = (shape @ fields[key][nodes]
                                           for key in ("zero", "relief", "cyclic", "unclamped"))
        result[name] = dict(
            xyz_mm=xyz_mm,
            peak_VM_MPa=float(max(mises(zero[None, :])[0], mises(relief[None, :])[0])),
            cyclic_range_VM_MPa=float(mises((cyclic-zero)[None, :])[0]),
            unclamped_VM_MPa=float(mises(unclamped[None, :])[0]),
        )
    return result


def solve(level, thick_mm, radius_mm, refresh_unclamped=False):
    suffix = "" if CASE == "paired" else CASE+"_"
    stem = f"{'r2_s16_' if ROUND_2 else ''}ma8_{suffix}t{thick_mm:g}_r{radius_mm:g}_{level}"
    summary_path = HERE/(stem+".json")
    previous = json.loads(summary_path.read_text(encoding="utf-8")) if refresh_unclamped else None
    with TemporaryDirectory(prefix="t22_cap_",dir=HERE.parent) as scratch:
        folder = Path(scratch)
        geo = folder/(stem+".geo")
        geo.write_text(geometry(level, thick_mm, radius_mm),encoding="ascii")
        (HERE/geo.name).write_bytes(geo.read_bytes())
        mesh = geo.with_suffix(".msh")
        log = run_tool([BIN/"gmsh.exe",geo.name,"-3","-order","2","-format","msh2","-o",mesh.name,
                        "-nt","1","-nopopup"],folder,marker="Done writing")
        volume_mm3 = float(re.search(r"^VOL ([\d.eE+-]+)$",log,re.MULTILINE)[1])
        if radius_mm and (int(re.search(r"^FILLET_EDGES (\d+)$",log,re.MULTILINE)[1]) < 8 or
                          "ROUNDED_VOLUMES 1" not in log):
            raise RuntimeError("MA blend edge or volume selection inconsistent")
        coords,tets,active,faces = read_mesh(mesh)
        normals = surface_normals(coords,tets,faces[physical_face_ids(coords,faces)] if ROUND_2 else faces)
        write_mesh_include(folder/"cap_mesh.inp",coords,tets,active)
        f, barrel, studs, valve, taps, pressure_error = joint(coords,faces,normals,thick_mm)
        stud_springs = STUD_K_N_MM/SECTOR_COUNT*positive_patch_weights(studs)
        barrel_springs = BARREL_K_N_MM/SECTOR_COUNT*positive_patch_weights(barrel)
        f_preload = np.zeros_like(coords)
        barrel_preload_N = old_cap.CYLINDER_PRELOAD_N/SECTOR_COUNT
        valve_preload_N = 8*VALVE_PRELOAD_EACH_N/SECTOR_COUNT
        f_preload[:,2] = barrel_preload_N*(barrel-studs)+valve_preload_N*(taps-valve)
        # Preloaded contact is linearized closed at the barrel. The no-preload
        # branch models a lifted barrel/cover seat and no ZSF prestress.
        cases = (("zero",0.,True),("relief",31.5,True),("cyclic",30.,True),("unclamped",31.5,False))
        if refresh_unclamped:
            if (previous["nodes"],previous["elements"]) != (len(active),len(tets)):
                raise RuntimeError("Mesh does not match archived preloaded cases")
            cases = cases[-1:]
        sym_nodes = symmetry_layout(coords,active)
        sym_normals = symmetry_normals()
        responses = {}
        balance = {}
        for name,p_MPa,preloaded in cases:
            path = folder/f"{stem}_{name}.inp"
            springs = stud_springs+barrel_springs if preloaded else stud_springs
            load = f*p_MPa + f_preload*preloaded
            if not preloaded:
                # An unpreloaded ZSF interface carries no unloading reaction
                # on the seat. Transfer the complete pressure thrust to taps.
                load[:,2] += p_MPa*pi*SEAL_R_MM**2/SECTOR_COUNT*(1-VALVE_PHI)*(taps-valve)
            solver_load_N = load.copy()
            for nodes,normal in zip(sym_nodes,sym_normals):
                tangential_N = solver_load_N[nodes,:2]@normal
                solver_load_N[nodes,:2] -= tangential_N[:,None]*normal
            springs = case_deck(path,sym_nodes,springs,solver_load_N)
            run_tool([BIN/"ccx.exe","-i",path.stem],folder,marker="Job finished")
            response = results_frd(path.with_suffix(".frd"),len(coords))
            spring_reactions_N = -springs*response["DISP"][:,2]
            reactions_xy_N = np.zeros(2)
            for nodes,normal in zip(sym_nodes,sym_normals):
                reactions_xy_N += normal*np.sum(response["FORC"][nodes,:2]@normal)
            reactions_N = np.append(reactions_xy_N,spring_reactions_N.sum())
            residual_N = np.linalg.norm(reactions_N+solver_load_N.sum(axis=0))
            balance[name] = dict(applied_axial_N=float(load[:,2].sum()),
                                 elastic_reaction_axial_N=float(spring_reactions_N.sum()),
                                 solver_applied_force_N=solver_load_N.sum(axis=0).tolist(),
                                 solver_reactions_N=reactions_N.tolist(),
                                 residual_fraction=float(residual_N/(31.5*pi*140**2/SECTOR_COUNT)))
            responses[name] = response
        representative = folder/f"{stem}_relief.inp"
        if not refresh_unclamped and level == 0 and representative.stat().st_size < 1_000_000:
            (HERE/representative.name).write_bytes(representative.read_bytes())
        (HERE/geo.name).write_bytes(geo.read_bytes())

    zones = control_zones(coords,active,thick_mm)
    if refresh_unclamped:
        vm_MPa = mises(responses["unclamped"]["STRESS"])
        for name,ids in zones.items():
            previous["regions"][name]["static_yield_factor_without_preload"] = float(500./max(vm_MPa[ids]))
        previous["balances"]["unclamped"] = balance["unclamped"]
        write_json(summary_path,previous)
        print(stem,"unclamped load transfer replayed",flush=True)
        return

    zero = responses["zero"]["STRESS"]
    relief = responses["relief"]["STRESS"]
    cyclic = responses["cyclic"]["STRESS"]
    unclamped = responses["unclamped"]["STRESS"]
    cyclic_delta = cyclic-zero
    static_vm = np.maximum(mises(zero),mises(relief))
    static_unclamped_vm = mises(unclamped)
    rp_MPa, rm_MPa = (650., 850.) if ROUND_2 else (500., 750.)
    live_factor, factored_MPa = old_cap.elastic_proof(zero, relief, rp_MPa)
    stress_range_vm = mises(cyclic_delta)
    max_principal_MPa = np.linalg.eigvalsh(stress_tensors(cyclic_delta))
    gradient = normal_gradient(coords,tets,normals,np.abs(max_principal_MPa).max(axis=1))
    n_sigma = notch_support(gradient,rm_MPa,False)
    allow, kR, jG, M = fkm_parameters(rm_MPa,6.3,False,forging=True)
    mean_MPa = np.maximum(0.,np.linalg.eigvalsh(stress_tensors((cyclic+zero)/2))[:,-1])
    util = (stress_range_vm/2 + M*mean_MPa)/(allow*n_sigma)
    rows = {}
    for name,ids in zones.items():
        i = ids[np.argmax(static_vm[ids])]
        j = ids[np.argmax(util[ids])]
        rows[name] = dict(static_yield_factor=float(rp_MPa/static_vm[i]),
                          static_VM_MPa=float(static_vm[i]), static_xyz_mm=coords[i].tolist(),
                          fixed_preload_load_to_yield_factor=float(np.min(live_factor[ids])),
                          factored_with_preload_VM_MPa=float(np.max(factored_MPa[ids])),
                          static_yield_factor_without_preload=float(rp_MPa/max(static_unclamped_vm[ids])),
                          fkm_factor=float(1/util[j]), fkm_xyz_mm=coords[j].tolist(),
                          stress_range_VM_MPa=float(stress_range_vm[j]), fkm_G_per_mm=float(gradient[j]),
                          fkm_n_sigma=float(n_sigma[j]))
        if ROUND_2:
            table_live, _ = old_cap.elastic_proof(zero[ids], relief[ids], 600.)
            rows[name].update(
                static_yield_factor_Rp600=float(600./static_vm[i]),
                fixed_preload_load_to_yield_factor_Rp600=float(table_live.min()),
                static_without_preload_Rp600=float(600./max(static_unclamped_vm[ids])),
                unclamped_VM_MPa=float(max(static_unclamped_vm[ids])),
                fkm_mean_MPa=float(mean_MPa[j]),
            )
    displacement_z = responses["relief"]["DISP"][:,2]-responses["zero"]["DISP"][:,2]
    barrel_comp_N = barrel_preload_N*positive_patch_weights(barrel)-barrel_springs*displacement_z
    min_barrel_comp_N = barrel_comp_N[barrel_springs>0].min()
    out = dict(status="DIAGNOSTIC", layout=CASE, mesh_level=level, nodes=len(active), elements=len(tets),
               cap_thickness_mm=thick_mm, MA_count=len(MA_AXES), MA_ID_mm=2*MA_R_MM, MA_blend_mm=radius_mm,
               projected_pressure_resultant_error_fraction=float(pressure_error), mass_kg=volume_mm3*RHO_kg_mm3,
               mass_scope="cover blank only", modelled_valve_preload_each_N=VALVE_PRELOAD_EACH_N,
               minimum_barrel_nodal_contact_at_315_bar_N=float(min_barrel_comp_N),
               barrel_nodes_open_in_linear_solution=int(np.count_nonzero(barrel_comp_N<0)),
               balances=balance,
               fkm=dict(Rp02_MPa=rp_MPa,Rm_MPa=rm_MPa,kR=kR,jG=jG,M_sigma=M,kD=15,jD=1.5), regions=rows)
    if ROUND_2:
        out.update(physical_surface_normals_only=True, sector_angle_deg=360/SECTOR_COUNT, sector_count=SECTOR_COUNT,
                   mesh_far_mm=MESH_SIZES_MM[level][0], mesh_near_mm=MESH_SIZES_MM[level][1],
                   pressure_seal_diameter_mm=2*SEAL_R_MM, valve_pressure_load_fraction=VALVE_PHI,
                   interior_probes=interior_probes(coords, tets,
                       dict(zero=zero, relief=relief, cyclic=cyclic, unclamped=unclamped)))
    write_json(summary_path,out)
    print(stem,rows["global"],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("levels",nargs="+",type=int)
    parser.add_argument("--thickness-mm",type=float,default=132.)
    parser.add_argument("--MA-blend-mm",type=float,default=3.)
    parser.add_argument("--case",choices=("paired","uniform","recessed_taps"),default="paired")
    parser.add_argument("--refresh-unclamped",action="store_true",
                        help="Recompute the no-preload case on already archived geometry")
    parser.add_argument("--round-2", action="store_true")
    args = parser.parse_args()
    CASE = args.case
    if CASE in ("uniform","recessed_taps"):
        # The quarter axes rotate 11.25 degrees relative to the through-stud grid.
        angles_deg = range(0,360,45)
        MA_AXES = np.array([(cos(radians(a)),sin(radians(a))) for a in angles_deg])
        STUD_POSITIONS = [(225*cos(radians(11.25+i*22.5)),225*sin(radians(11.25+i*22.5)))
                          for i in range(16)]
        VALVE_PRELOAD_EACH_N = 198000.
    if args.round_2:
        if (CASE, args.thickness_mm, args.MA_blend_mm) != ("recessed_taps", 144., 1.2):
            parser.error("Round 2 requires recessed_taps, 144 mm and MA R1.2")
        ROUND_2 = True
        SECTOR_COUNT = 16
        SECTOR_ANGLE_RAD = 2*pi/SECTOR_COUNT
        SEAL_R_MM = 94.
        VALVE_PHI = 0.31
        STUD_K_N_MM = 16*E_MPa*STUD_AS_MM2/(STUD_EFFECTIVE_MM+12.)
    for i in args.levels:
        solve(i,args.thickness_mm,args.MA_blend_mm,args.refresh_unclamped)

