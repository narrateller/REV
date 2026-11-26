"""Separate C3D10 model of the forged pressure spreading insert."""
import argparse
from itertools import product
from pathlib import Path
import re
import tempfile

from frame_analytic import (
    ADAPTER_mm, CHAMBER_MODEL, CYCLIC_N, ECC_mm, OUTLET_HEIGHT_mm, OUTLET_RADIUS_mm, OUTLET_WIDTH_mm,
    PAD_HEIGHT_mm, PAD_WIDTH_mm, STATIC_N,
)
from frame_fea import (
    BIN, FEA, chamber_pad, fkm_parameters, input_deck, mises, normal_gradient, notch_support, patch_loads,
    plane_triangles, read_mesh, restraints, results_frd, round_surface, run_tool,
    stress_tensors, surface_normals, write_json, write_mesh_include,
)
from frame_geometry import Geo, rounded_box

import numpy as np

MODES = ("centred","ex","ey")


def geometry(level):
    geo = Geo()
    geo.emit(f"outer = newv; Box(outer) = {{-{PAD_WIDTH_mm/2},-{PAD_HEIGHT_mm/2},0,"
             f"{PAD_WIDTH_mm},{PAD_HEIGHT_mm},{ADAPTER_mm}}};")
    rounded_box(geo,0.,0.,OUTLET_WIDTH_mm/2,OUTLET_HEIGHT_mm/2,OUTLET_RADIUS_mm,
                -1.,ADAPTER_mm+2.,0.,"outlet")
    geo.cut("outer",["outlet"],"bodies")
    geo.emit('Printf("VOL %.15g", Mass Volume{bodies[0]});')
    geo.emit("clip = newv; Box(clip) = {0,0,-1,200,100,100};")
    geo.emit("sector[] = BooleanIntersection{ Volume{bodies[]}; Delete; }{ Volume{clip}; Delete; };")
    base_mm,near_mm = ((14.,6.),(11.,4.6),(9.,3.2),(8.,2.6),(7.,2.1))[level]
    geo.emit(f"Mesh.MeshSizeMax = {base_mm}; Mesh.MeshSizeFromPoints = 0;")
    geo.emit("Mesh.MeshSizeFromCurvature = 12; Mesh.MeshSizeExtendFromBoundary = 0;")
    geo.emit("Mesh.SecondOrderLinear = 1; Mesh.RandomSeed = 42; Mesh.MaxNumThreads3D = 1;")
    rx,ry = OUTLET_WIDTH_mm/2-OUTLET_RADIUS_mm,OUTLET_HEIGHT_mm/2-OUTLET_RADIUS_mm
    circle = f"Abs(Sqrt((x-{rx})^2+(y-{ry})^2)-{OUTLET_RADIUS_mm})"
    edge = f"Min(Abs(x-{OUTLET_WIDTH_mm/2}),Min(Abs(x-{PAD_WIDTH_mm/2}),Abs(y-{PAD_HEIGHT_mm/2})))"
    depth = f"Min(Abs(z),Abs(z-{ADAPTER_mm}))"
    distance = f"Min({circle},Max({edge},{depth}))"
    field = geo.new()
    geo.emit(f'Field[{field}] = MathEval; Field[{field}].F = "{near_mm}+({base_mm}-{near_mm})*Min(1,({distance}/13))";')
    geo.emit(f"Background Field = {field};")
    return "\n".join(geo.lines)+"\n"


def loads(coords,faces):
    rail = patch_loads(coords,plane_triangles(coords,faces,2,0.),
                       chamber_pad,"rails")
    seat = patch_loads(coords,plane_triangles(coords,faces,2,ADAPTER_mm),
                       chamber_pad,"seat")
    quadrant_N = STATIC_N/4
    basis = {"centred":quadrant_N*(rail[0]-seat[0])}
    for i,name in enumerate(MODES[1:]):
        coordinate_mm = coords[:,i]
        a,b = rail[1+i],seat[1+i]
        basis[name] = quadrant_N*ECC_mm*(a/(a@coordinate_mm)-b/(b@coordinate_mm))
        if abs(basis[name]@coordinate_mm)>.01:
            raise ValueError("Nonzero insert moment residual")
    if abs(basis["centred"].sum())>1e-6:
        raise ValueError("Nonzero insert force residual")
    return basis,rail[0],seat[0]


def response(coords,tets,active,faces,result,rail,seat):
    arc = round_surface(coords,faces,OUTLET_WIDTH_mm/2-OUTLET_RADIUS_mm,
                        OUTLET_HEIGHT_mm/2-OUTLET_RADIUS_mm,OUTLET_RADIUS_mm)
    arc_h_mm = max(np.linalg.norm(coords[arc[:,i]]-coords[arc[:,j]],axis=1).max()
                   for i,j in ((0,1),(1,2),(2,0)))
    normals = surface_normals(coords,tets,faces)
    nodes = {"insert_global":active,"outlet_insert_R20":np.unique(arc)}
    fields = ("static_mises_MPa","principal_tensile_MPa","principal_abs_MPa","range_mises_MPa",
              "range_principal_abs_MPa","fatigue_utilisation")
    zones = {name:dict.fromkeys(fields,0.) for name in nodes}
    zones["insert_global"].update(h_mm=None,h_limit_mm=None)
    zones["outlet_insert_R20"].update(h_mm=float(arc_h_mm),h_limit_mm=OUTLET_RADIUS_mm/4)
    allow_MPa,_,_,mean_slope = fkm_parameters(1000.,12.5,False,forging=True)
    for sx,sy in product((-1,1),repeat=2):
        total = result["centred"]["STRESS"]+sx*result["ex"]["STRESS"]+sy*result["ey"]["STRESS"]
        vm = mises(total)
        principal = np.linalg.eigvalsh(stress_tensors(total))
        cycle_ratio = CYCLIC_N/STATIC_N
        vm_range = vm*cycle_ratio
        principal_range = np.max(np.abs(principal),axis=1)*cycle_ratio
        G = normal_gradient(coords,tets,normals,principal_range)
        n = notch_support(G,1000.,False)
        p_mean = np.maximum(0.,principal[:,-1]*cycle_ratio/2)
        util = (vm_range/2+mean_slope*p_mean)/(allow_MPa*n)
        for name,ids in nodes.items():
            zone = zones[name]
            values = (vm,principal[:,-1],np.max(np.abs(principal),axis=1),vm_range,principal_range,util)
            for field,value in zip(fields,values,strict=True):
                node = ids[np.argmax(value[ids])]
                if value[node]>zone[field]:
                    zone[field] = float(value[node])
                    if field in ("static_mises_MPa","fatigue_utilisation"):
                        zone[field+"_xyz_mm"] = coords[node].tolist()
                    if field=="fatigue_utilisation":
                        zone.update(G_sigma_per_mm=float(G[node]),n_sigma=float(n[node]),
                                    fatigue_alt_mises_MPa=float(vm_range[node]/2),
                                    fatigue_positive_mean_MPa=float(p_mean[node]))
    for zone in zones.values():
        zone["fatigue_factor"] = 1./zone["fatigue_utilisation"]
    axial_mm = abs(float((rail-seat)@result["centred"]["DISP"][:,2]))
    tilt_rad, shift_mm = [],[]
    for i,name in enumerate(MODES[1:]):
        u = result[name]["DISP"]
        x = coords[:,i]
        seat_slope = (seat@u[:,2])/(seat@x)
        tilt_rad.append(float((rail@u[:,2])/(rail@x)-seat_slope))
        shift_mm.append(float((rail-seat)@u[:,i]-seat_slope*ADAPTER_mm))
    return zones,axial_mm,tilt_rad,shift_mm


def solve(level, archive):
    stem = f"insert_pads_{level}"
    geo_text = geometry(level)
    with tempfile.TemporaryDirectory(prefix=stem+"_",dir=FEA) as tmp:
        folder = Path(tmp)
        geo = folder/(stem+".geo")
        geo.write_text(geo_text,encoding="ascii",newline="\n")
        mesh = geo.with_suffix(".msh")
        log = run_tool([BIN/"gmsh.exe",geo.name,"-3","-order","2","-format","msh2",
                        "-o",mesh.name,"-nt","1","-nopopup"],folder,marker="Done writing")
        volume_mm3 = float(re.search(r"^VOL ([\d.eE+-]+)$",log,re.MULTILINE)[1])
        coords,tets,active,faces = read_mesh(mesh)
        mesh_name = stem+"_mesh.inp"
        write_mesh_include(folder/mesh_name,coords,tets,active)
        basis,rail,seat = loads(coords,faces)
        result = {}
        for mode in MODES:
            sets,bcs = restraints(coords,active,ADAPTER_mm,mode)
            deck = folder/(stem+"_"+mode+".inp")
            input_deck(deck,mesh_name,sets,bcs,basis[mode])
            run_tool([BIN/"ccx.exe","-i",deck.stem],folder,marker="Job finished")
            result[mode] = results_frd(deck.with_suffix(".frd"),len(coords))
            if archive:
                (FEA/deck.name).write_bytes(deck.read_bytes())
        if archive:
            (FEA/geo.name).write_bytes(geo.read_bytes())
    zones,axial_mm,tilt_rad,shift_mm = response(coords,tets,active,faces,result,rail,seat)
    data = {"chamber_model":CHAMBER_MODEL,"mesh_level":level,"nodes":int(len(active)),"tetrahedra":int(len(tets)),
            "OCC_volumes_mm3":[volume_mm3],"regions":zones,"axial_deflection_mm":axial_mm,
            "relative_tilt_rad_xy":tilt_rad,"relative_shift_mm_xy":shift_mm}
    write_json(FEA/(stem+".json"),data)
    print(stem,len(active),zones["insert_global"]["static_mises_MPa"],
          zones["insert_global"]["fatigue_factor"],flush=True)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels",default="0,1,2")
    parser.add_argument("--archive-level",type=int,default=2)
    args = parser.parse_args()
    for level in map(int,args.levels.split(",")):
        solve(level,level==args.archive_level)
