"""Screen the inherited separate forged rear cover at the T-1.6 envelope."""
import argparse
from math import pi
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import numpy as np

import cap_pressure as cap
from frame_analytic import CYLINDER, RHO_kg_mm3, STUDS, STUD_HOLE_RADIUS_mm
from frame_fea import (BIN, FEA, fkm_parameters, mises, normal_gradient, notch_support, plane_triangles,
                       read_mesh, results_frd, ring, run_tool, stress_tensors, surface_normals,
                       write_json, write_mesh_include)
from frame_geometry import Geo

THICK_mm = CYLINDER["cover_thickness_rear_mm"]
OUTER_R_mm = CYLINDER["cover_OD_mm"]/2


def geometry(level):
    geo = Geo()
    outer = geo.cylinder(0,0,0.,THICK_mm,OUTER_R_mm)
    cap.DEPTH_mm, cap.SEAT_mm = THICK_mm,0.
    tools = [cap.cavity_profile(geo)]
    tools += [geo.cylinder(x,y,-1.,THICK_mm+2.,STUD_HOLE_RADIUS_mm) for x,y in STUDS]
    tools += [geo.cylinder(x,y,THICK_mm-cap.TAP_DEPTH_mm,cap.TAP_DEPTH_mm+1.,cap.TAP_R_mm)
              for x,y in cap.VALVE_TAPS]
    geo.cut(str(outer),tools,"cover")
    geo.emit('Printf("VOL %.15g",Mass Volume{cover[0]});')
    geo.emit("clip = newv; Box(clip) = {0,0,-10,280,280,165};")
    geo.emit("sector[] = BooleanIntersection{ Volume{cover[]}; Delete; }{ Volume{clip}; Delete; };")
    far,near = ((32.,5.5),(28.,3.5),(24.,2.5),(21.,1.9))[level]
    geo.emit(f"Mesh.MeshSizeMax={far}; Mesh.MeshSizeFromPoints=0; Mesh.MeshSizeFromCurvature=14;")
    geo.emit("Mesh.MeshSizeExtendFromBoundary=0; Mesh.SecondOrderLinear=1; Mesh.RandomSeed=42; Mesh.MaxNumThreads3D=1;")
    rad = "Sqrt(x*x+y*y)"
    d = f"Min(Max(Abs({rad}-65),Min(z,{THICK_mm}-z)),Max(Abs({rad}-120),{THICK_mm}-z))"
    geo.emit(f'Field[1] = MathEval; Field[1].F = "{near}+({far}-{near})*Min(1,Max(0,({d}-7)/25))"; Background Field = 1;')
    return "\n".join(geo.lines)+"\n"


def forces(xyz,faces,normals,p_MPa):
    def nut(x,y):
        return sum(ring(x,y,sx,sy,STUD_HOLE_RADIUS_mm,33.,2.) for sx,sy in STUDS)
    def barrel(x,y):
        return ring(x,y,0.,0.,141.,175.,3.)
    def valve(x,y):
        return ring(x,y,0.,0.,84.,146.,4.)
    wi = cap.weights(xyz,faces,0.,barrel)
    wt = cap.weights(xyz,faces,THICK_mm,nut)
    wv = cap.weights(xyz,faces,THICK_mm,valve)
    f = p_MPa*cap.surface_pressure(xyz,faces,normals)
    quarter_N = p_MPa*pi*cap.BORE_R_mm**2/4
    f[:,2] += (quarter_N-f[:,2].sum())*wv
    # Split external head separation force between preload relief and stud load.
    # 0 and 1 are end bounds. The 0.25 variant is the nominal screen.
    return f,wi,wt,wv,quarter_N


def solve(level):
    stem = f"retained_rear_cap_{level}"
    with TemporaryDirectory(prefix=stem+"_",dir=FEA.parent, ignore_cleanup_errors=True) as tmp:
        folder = Path(tmp)
        geo = folder/(stem+".geo")
        geo.write_text(geometry(level),encoding="ascii")
        mesh = geo.with_suffix(".msh")
        log = run_tool([BIN/"gmsh.exe",geo.name,"-3","-order","2","-format","msh2","-o",mesh.name,
                        "-nt","1","-nopopup"],folder,marker="Done writing")
        xyz,tets,active,faces = read_mesh(mesh)
        volume_mm3 = float(re.search(r"^VOL ([\d.eE+-]+)$",log,re.MULTILINE)[1])
        normals = surface_normals(xyz,tets,faces)
        write_mesh_include(folder/"cap_mesh.inp",xyz,tets,active)
        x_sym = active[abs(xyz[active,0])<1.e-5]
        y_sym = active[abs(xyz[active,1])<1.e-5]
        candidates = active[abs(xyz[active,2]-THICK_mm)<1.e-5]
        lock = int(candidates[np.argmin(np.linalg.norm(xyz[candidates,:2]-[230.,50.],axis=1))])
        sets = {"XSYM":x_sym,"YSYM":y_sym}
        bcs = [("XSYM",1,1),("YSYM",2,2),(lock,3,3)]
        responses = []
        for label,p_MPa in (("zero",0.),("static",31.5),("fatigue",30.)):
            f,wi,wt,_,q = forces(xyz,faces,normals,p_MPa)
            f[:,2] += cap.CYLINDER_PRELOAD_N/4*(wi-wt)-q*(.75*wi+.25*wt)
            assert abs(f[:,2].sum())<1.e-6
            inp = folder/f"{stem}_{label}.inp"
            cap.deck(inp,"cap_mesh.inp",sets,bcs,f)
            run_tool([BIN/"ccx.exe","-i",inp.stem],folder,marker="Job finished")
            responses.append(results_frd(inp.with_suffix(".frd"),len(xyz))["STRESS"])
            if level==2:
                (FEA/inp.name).write_bytes(inp.read_bytes())
        (FEA/geo.name).write_bytes(geo.read_bytes())
    zero,static,fat = responses
    r = np.hypot(*xyz[:,:2].T)
    z = xyz[:,2]
    zones = {"cover_global":active,"prefill_inner_R6":active[(abs(r[active]-65)<15)&(z[active]<15)],
             "prefill_outer_R6":active[(abs(r[active]-65)<15)&(z[active]>THICK_mm-15)]}
    s_vm = np.maximum(mises(zero),mises(static))
    live_factor,proof = cap.elastic_proof(zero,static,CYLINDER["barrel_and_cover_Rp02_min_MPa"])
    delta = fat-zero
    r_vm = mises(delta)
    pmean = np.maximum(0.,np.linalg.eigvalsh(stress_tensors((fat+zero)/2))[:,-1])
    grad = normal_gradient(xyz,tets,normals,np.abs(np.linalg.eigvalsh(stress_tensors(delta))).max(axis=1))
    n = notch_support(grad,750.,False)
    Rp_MPa = CYLINDER["barrel_and_cover_Rp02_min_MPa"]
    allow,_,_,M = fkm_parameters(750.,6.3,False,forging=True)
    util = (r_vm/2+M*pmean)/(allow*n)
    rows = {}
    for name,ids in zones.items():
        i,j = ids[np.argmax(s_vm[ids])],ids[np.argmax(util[ids])]
        rows[name] = dict(static_MPa=float(s_vm[i]),static_factor=float(Rp_MPa/s_vm[i]),static_xyz_mm=xyz[i].tolist(),
                          fatigue_factor=float(1./util[j]),range_MPa=float(r_vm[j]),fatigue_xyz_mm=xyz[j].tolist(),
                          fixed_preload_load_to_yield_factor=float(np.min(live_factor[ids])),
                          fixed_preload_1p5_peak_MPa=float(np.max(proof[ids])),
                          G_sigma_per_mm=float(grad[j]),n_sigma=float(n[j]))
    out = dict(nodes=len(active),elements=len(tets),volume_mm3=volume_mm3,mass_kg=volume_mm3*RHO_kg_mm3,
               cover_Rp02_min_MPa=Rp_MPa,cover_Rm_min_MPa=750.,assumed_port_R_mm=cap.PORT_BLEND_mm,
               stud_separation_load_fraction=.25,valve_tap_model_depth_mm=cap.TAP_DEPTH_mm,regions=rows)
    write_json(FEA/f"{stem}.json",out)
    print(stem,[(k,v["static_factor"],v["fatigue_factor"]) for k,v in rows.items()],flush=True)


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("levels",nargs="+",type=int)
    for i in parser.parse_args().levels:
        solve(i)

