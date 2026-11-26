"""T-1.7 cast outline with recessed barrel seat and pressurised rear cap."""
import argparse
from math import cos, hypot, pi, sin
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import numpy as np

from frame_analytic import (
    COLUMN_HOLE_mm, COLUMN_INNER_SEAT_BORE_mm, CORNERS, CYLINDER, E_MPa, NU, PRELOAD_N,
    NUT_BEAR_OD_mm, STUDS, STUD_HOLE_RADIUS_mm, VARIANTS, RHO_kg_mm3, column,
)
from frame_fea import (
    BIN, FEA, fkm_parameters, mises, normal_gradient, notch_support, patch_loads, plane_triangles,
    quadrature, read_mesh, restraints, results_frd, ring, run_tool, stress_tensors,
    surface_normals, write_json, write_mesh_include,
)
from frame_geometry import Geo, cast_outline

CAST = next(v for v in VARIANTS if v.name == "cast")
DEPTH_mm = CAST.depth_mm
SEAT_mm = DEPTH_mm - CYLINDER["cover_thickness_rear_mm"]
BORE_R_mm = CYLINDER["bore_mm"]/2
BARREL_R_mm = CYLINDER["barrel_OD_mm"]/2
PORT_R_mm = CYLINDER["work_port_passage_ID_mm"]["cap"]/2
SEAT_BLEND_mm = 8.
PORT_BLEND_mm = 6.
CYLINDER_PRELOAD_N = 4704314.921670358  # T-1.6 results.json main_cylinder
VALVE_R_mm = CYLINDER["main_prefill_port"]["valve_mount_PCD_mm"]/2
VALVE_TAPS = [(VALVE_R_mm*cos(pi/8+i*pi/4), VALVE_R_mm*sin(pi/8+i*pi/4)) for i in range(8)]
TAP_R_mm = 12.
TAP_DEPTH_mm = 55.  # RE 20478, NG100 T2 minimum mounting interface


def cavity_profile(geo):
    r, p, h = BARREL_R_mm, PORT_R_mm, DEPTH_mm
    z, R, rp = SEAT_mm, SEAT_BLEND_mm, PORT_BLEND_mm
    points = [(0.,-1.), (r,-1.), (r,z-R), (r-R,z), (p+rp,z), (p,z+rp),
              (p,h-rp), (p+rp,h), (p+rp,h+1.), (0.,h+1.)]
    arcs = {2:(r-R,z-R), 4:(p+rp,z+rp), 6:(p+rp,h-rp)}
    if z <= 0:
        points = [(0., -2.), (p+rp, -2.)]+points[4:]
        arcs = {2:(p+rp,z+rp), 4:(p+rp,h-rp)}
    tag = {}
    for x,w in points+list(arcs.values()):
        tag[x,w] = geo.new()
        geo.emit(f"Point({tag[x,w]}) = {{{x},0,{w}}};")
    edges = []
    for i,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
        edge = geo.new()
        middle = f",{tag[arcs[i]]}" if i in arcs else ""
        kind = "Circle" if i in arcs else "Line"
        geo.emit(f"{kind}({edge}) = {{{tag[a]}{middle},{tag[b]}}};")
        edges.append(edge)
    loop, surface = geo.new(),geo.new()
    geo.emit(f"Curve Loop({loop}) = {{{','.join(map(str,edges))}}};")
    geo.emit(f"Plane Surface({surface}) = {{{loop}}};")
    # Four sweeps preserve explicit circular geometry and avoid a closed OCC sweep seam.
    face = str(surface)
    pieces = []
    for i in range(4):
        geo.counter += 1000
        q = f"q{i}"
        geo.emit(f"{q}[] = Extrude {{{{0,0,1}},{{0,0,0}},Pi/2}} {{ Surface{{{face}}}; }};")
        face = f"{q}[0]"
        pieces.append(f"{q}[1]")
    geo.emit("tool[] = BooleanUnion{ Volume{"+pieces[0]+"}; Delete; }{ Volume{"+",".join(pieces[1:])+"}; Delete; };")
    return "tool[0]"


def geometry(level):
    geo = Geo()
    outline, _ = cast_outline(geo,CAST)
    geo.extrude(outline,DEPTH_mm,"outer")
    tools = [cavity_profile(geo)]
    tools += [geo.cylinder(x,y,-1.,DEPTH_mm+2,COLUMN_HOLE_mm/2) for x,y in CORNERS]
    for x,y in CORNERS:
        i = geo.new()
        geo.emit(f"Cone({i}) = {{{x},{y},-1,0,0,17,67.9375,52}};")
        tools.append(i)
    tools += [geo.cylinder(x,y,-1.,DEPTH_mm+2,STUD_HOLE_RADIUS_mm) for x,y in STUDS]
    tools += [geo.cylinder(x,y,DEPTH_mm-TAP_DEPTH_mm,TAP_DEPTH_mm+1,TAP_R_mm) for x,y in VALVE_TAPS]
    geo.cut("outer",tools,"body")
    geo.emit('Printf("VOL %.15g", Mass Volume{body[0]});')
    geo.emit(f"clip = newv; Box(clip) = {{0,0,-10,510,510,{DEPTH_mm+30}}};")
    geo.emit("sector[] = BooleanIntersection{ Volume{body[]}; Delete; }{ Volume{clip}; Delete; };")
    far, near = ((34.,5.),(30.,3.4),(27.,2.5),(25.,1.9),(23.,1.45))[level]
    geo.emit(f"Mesh.MeshSizeMax={far}; Mesh.MeshSizeFromPoints=0; Mesh.MeshSizeFromCurvature=14;")
    geo.emit("Mesh.MeshSizeExtendFromBoundary=0; Mesh.SecondOrderLinear=1; Mesh.RandomSeed=42; Mesh.MaxNumThreads3D=1;")
    radial = "Sqrt(x*x+y*y)"
    port_in = f"Max(Abs({radial}-{PORT_R_mm+3}),Abs(z-{SEAT_mm+3}))"
    port_out = f"Max(Abs({radial}-{PORT_R_mm+3}),Abs(z-{DEPTH_mm-3}))"
    blend = f"Max(Abs({radial}-{BARREL_R_mm-4}),Abs(z-{SEAT_mm-4}))"
    d = f"Min({port_in},Min({port_out},{blend}))"
    size = f"{near}+({far}-{near})*Min(1,Max(0,({d}-7)/25))"
    geo.emit(f'Field[1] = MathEval; Field[1].F = "{size}"; Background Field = 1;')
    return "\n".join(geo.lines)+"\n"


def surface_pressure(coords, faces, normals):
    """Outward-from-steel is toward the oil. Return the load into the steel."""
    radial = np.hypot(coords[faces,0],coords[faces,1])
    z = coords[faces,2]
    values = np.zeros_like(coords)
    for N, xyz, da in quadrature(coords[faces]):
        dirs = N @ normals[faces]
        dirs /= np.maximum(np.linalg.norm(dirs,axis=1),1.e-20)[:,None]
        r = np.hypot(xyz[:,0],xyz[:,1])
        zz = xyz[:,2]
        wet = ((zz>=SEAT_mm-1.e-5) & (r<=BORE_R_mm)
               & ((r<PORT_R_mm+PORT_BLEND_mm+1.e-4) | (abs(zz-SEAT_mm)<1.e-5)))
        wet &= (~np.all(np.abs(z-DEPTH_mm)<1.e-5,axis=1) &
                ~np.all(radial>BORE_R_mm+1.e-5,axis=1))
        wet &= (~np.all(abs(coords[faces,0])<1.e-5,axis=1)
                & ~np.all(abs(coords[faces,1])<1.e-5,axis=1))
        traction = -(da*wet)[:,None]*dirs
        np.add.at(values,faces.ravel(),(traction[:,None,:]*N[None,:,None]).reshape(-1,3))
    return values


def weights(coords, faces, z_mm, radial_mask):
    return patch_loads(coords,plane_triangles(coords,faces,2,z_mm),radial_mask,"pressure cap")[0]


def forces(coords, faces, mode, normals):
    def column_inner(x,y):
        return ring(x,y,270.,270.,COLUMN_INNER_SEAT_BORE_mm/2,NUT_BEAR_OD_mm/2,5.)
    def column_outer(x,y):
        return ring(x,y,270.,270.,COLUMN_HOLE_mm/2,NUT_BEAR_OD_mm/2,5.)
    def sleeve(x,y):
        return ring(x,y,0,0,BORE_R_mm+1,BARREL_R_mm-SEAT_BLEND_mm-1,3.)
    def nut(x,y):
        return sum(ring(x,y,sx,sy,STUD_HOLE_RADIUS_mm,33.,2.) for sx,sy in STUDS)
    def valve(x,y):
        return ring(x,y,0,0,84.,146.,4.)
    wi = weights(coords,faces,0.,column_inner)
    wo = weights(coords,faces,DEPTH_mm,column_outer)
    wb = weights(coords,faces,SEAT_mm,sleeve)
    wn = weights(coords,faces,DEPTH_mm,nut)
    wv = weights(coords,faces,DEPTH_mm,valve)
    phi = column(CAST)["load_fraction"]
    bearing = (1-phi)*wi+phi*wo
    f = np.zeros_like(coords)
    f[:,2] = PRELOAD_N*(wi-wo)+CYLINDER_PRELOAD_N/4*(wb-wn)
    if mode:
        nominal_p_MPa = 31.5 if mode=="static" else 30.
        f_p = nominal_p_MPa*surface_pressure(coords,faces,normals)
        # Axial resultant of the wetted cap + closing valve assembly equals p*A.
        total_pressure_force_N = nominal_p_MPa*pi*BORE_R_mm**2/4
        valve_force_N = total_pressure_force_N-f_p[:,2].sum()
        f_p[:,2] += valve_force_N*wv
        # At 300 bar the task prescribes net force after losses 1.70 MN.
        # The difference closes through the front assembly and its studs.
        target_N = (1.94e6 if mode=="static" else 1.70e6)/4
        f_p[:,2] += (target_N-total_pressure_force_N)*wn-target_N*bearing
        f += f_p
    if abs(f[:,2].sum())>1.e-5:
        raise RuntimeError("integrated head axial loads do not balance")
    return f


def deck(path, mesh, sets, bcs, load):
    lines = ["*HEADING","T-1.7b | integrated rear head | N, mm, MPa",f"*INCLUDE,INPUT={mesh}"]
    for name,tags in sets.items():
        lines += [f"*NSET,NSET={name}"]
        lines += [",".join(map(str,tags[i:i+16])) for i in range(0,len(tags),16)]
    lines += ["*MATERIAL,NAME=CAST","*ELASTIC",f"{E_MPa},{NU}",
              "*SOLID SECTION,ELSET=TRAVERSE,MATERIAL=CAST","*BOUNDARY"]
    lines += [f"{tag},{a},{b}" for tag,a,b in bcs]
    lines += ["*STEP","*STATIC","*CLOAD"]
    for axis in range(3):
        lines += [f"{tag},{axis+1},{load[tag,axis]:.12g}"
                  for tag in np.flatnonzero(abs(load[:,axis])>1.e-12)
                  if not (axis<2 and tag in sets[("XSYM","YSYM")[axis]])]
    lines += ["*NODE FILE","U,RF","*EL FILE","S","*END STEP"]
    path.write_text("\n".join(lines)+"\n",encoding="ascii")


def elastic_proof(zero, rated, yield_MPa):
    """Scale the external load with unchanged preload, as in T-1.7 round 2."""
    sigma_0 = mises(zero)
    increment = rated-zero
    linear_square = mises(rated)**2-sigma_0**2-mises(increment)**2
    a = mises(increment)**2
    c = sigma_0**2-yield_MPa**2
    discriminant = np.maximum(0.,linear_square**2-4*a*c)
    roots = np.divide(-linear_square+np.sqrt(discriminant),2*a,
                      out=np.full_like(a,np.inf),where=a>1.e-18)
    return np.where(c>0.,0.,roots),mises(zero+1.5*increment)


def measures(coords, tets, active, normals, results):
    static = results["static"]["STRESS"]
    zero = results[None]["STRESS"]
    stress_300 = results["fatigue"]["STRESS"]
    delta = stress_300-zero
    sigma_vm = np.maximum(mises(static),mises(zero))
    live_factor, proof = elastic_proof(zero,static,CAST.yield_MPa)
    mean = np.maximum(0.,np.linalg.eigvalsh(stress_tensors((stress_300+zero)/2))[:,-1])
    principal = np.abs(np.linalg.eigvalsh(stress_tensors(delta))).max(axis=1)
    gradient = normal_gradient(coords,tets,normals,principal)
    n = notch_support(gradient,CAST.tensile_MPa,True)
    r = np.hypot(coords[:,0],coords[:,1])
    z = coords[:,2]
    regions = {
        "cast_global": (active,25.), "barrel_seat_R8": (active[(abs(r[active]-172)<12)&(abs(z[active]-SEAT_mm)<12)],6.3),
        "prefill_inner_R6": (active[(abs(r[active]-PORT_R_mm)<14)&(abs(z[active]-SEAT_mm)<14)],6.3),
        "prefill_outer_R6": (active[(abs(r[active]-PORT_R_mm)<14)&(abs(z[active]-DEPTH_mm)<14)],6.3),
    }
    data = {}
    for name,(ids,rz) in regions.items():
        if name=="cast_global":
            # Keep the machined-surface allowance local to the machined cavity.
            rz = np.where((r[ids]<182)&(z[ids]>50),6.3,25.)
            allow = np.array([fkm_parameters(CAST.tensile_MPa,v,True)[0] for v in rz])
        else:
            allow = fkm_parameters(CAST.tensile_MPa,rz,True)[0]
        slope = fkm_parameters(CAST.tensile_MPa,6.3,True)[-1]
        util = (mises(delta)[ids]/2+slope*mean[ids])/(allow*n[ids])
        i,j = ids[np.argmax(sigma_vm[ids])],ids[np.argmax(util)]
        data[name] = dict(static_MPa=float(sigma_vm[i]),static_factor=float(CAST.yield_MPa/sigma_vm[i]),
                          static_xyz_mm=coords[i].tolist(),fatigue_factor=float(1/max(util)),
                          fixed_preload_load_to_yield_factor=float(np.min(live_factor[ids])),
                          fixed_preload_1p5_peak_MPa=float(np.max(proof[ids])),
                          fatigue_xyz_mm=coords[j].tolist(),range_MPa=float(mises(delta)[j]),
                          n_sigma=float(n[j]),G_sigma_per_mm=float(gradient[j]))
    return data


def solve(level):
    stem = f"integrated_cap_{level}"
    with TemporaryDirectory(prefix=stem+"_",dir=FEA.parent, ignore_cleanup_errors=True) as tmp:
        folder = Path(tmp)
        geo = folder/(stem+".geo")
        geo.write_text(geometry(level),encoding="ascii")
        msh = geo.with_suffix(".msh")
        log = run_tool([BIN/"gmsh.exe",geo.name,"-3","-order","2","-format","msh2","-o",msh.name,
                        "-nt","1","-nopopup"],folder,marker="Done writing")
        volume_mm3 = float(re.search(r"^VOL ([\d.eE+-]+)$",log,re.MULTILINE)[1])
        xyz,tets,active,faces = read_mesh(msh)
        normals = surface_normals(xyz,tets,faces)
        mesh = "cap_mesh.inp"
        write_mesh_include(folder/mesh,xyz,tets,active)
        sets,bcs = restraints(xyz,active,DEPTH_mm,"centred")
        results = {}
        for mode in (None,"static","fatigue"):
            name = "zero" if mode is None else mode
            inp = folder/f"{stem}_{name}.inp"
            deck(inp,mesh,sets,bcs,forces(xyz,faces,mode,normals))
            run_tool([BIN/"ccx.exe","-i",inp.stem],folder,marker="Job finished")
            results[mode] = results_frd(inp.with_suffix(".frd"),len(xyz))
            if level==2:
                (FEA/inp.name).write_bytes(inp.read_bytes())
        (FEA/geo.name).write_bytes(geo.read_bytes())
    out = dict(level=level,nodes=len(active),elements=len(tets),volume_mm3=volume_mm3,
               mass_kg=volume_mm3*RHO_kg_mm3,z_seat_mm=SEAT_mm,barrel_seat_R_mm=SEAT_BLEND_mm,
               valve_tap_model_depth_mm=TAP_DEPTH_mm,
               axial_port_R_mm=PORT_BLEND_mm,regions=measures(xyz,tets,active,normals,results))
    write_json(FEA/f"{stem}.json",out)
    print(stem,out["mass_kg"],[(k,v["static_factor"],v["fatigue_factor"]) for k,v in out["regions"].items()],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("levels",nargs="+",type=int)
    for level in parser.parse_args().levels:
        solve(level)

