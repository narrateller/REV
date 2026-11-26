"""Axisymmetric shoulder test on the common column, solved as a C3D10 quadrant."""
import argparse
from itertools import product
from pathlib import Path
import tempfile

import numpy as np

from frame_analytic import (
    COLLAR_H_mm, COLUMN_D_mm, COLUMN_INNER_SEAT_BORE_mm, COLUMN_MID_BLEND_mm, COLUMN_MID_D_mm,
    COLUMN_OUTER_BLEND_mm, CYCLIC_N, NUT_BEAR_OD_mm, PRELOAD_N, PRELOAD_SCATTER,
    STATIC_N, VARIANTS, column, corner_forces_N,
)
from frame_fea import (
    BIN, FEA, fkm_parameters, input_deck, mises, normal_gradient, notch_support,
    patch_loads, plane_triangles, read_mesh, results_frd, ring, run_tool, stress_tensors,
    surface_normals, write_json, write_mesh_include,
)
from frame_geometry import Geo

INNER_END_mm = -160.
OUTER_END_mm = COLLAR_H_mm+160.
UNIT_N = 100_000.


def geometry(level):
    mid = COLUMN_MID_D_mm/2
    end = COLUMN_D_mm/2
    R = COLUMN_MID_BLEND_mm
    r = COLUMN_OUTER_BLEND_mm
    seat = NUT_BEAR_OD_mm/2
    h = COLLAR_H_mm
    geo = Geo()

    def point(xz):
        return geo.point((xz[0],0.),xz[1])

    def curve(kind,*points):
        tag = geo.new()
        geo.emit(f"{kind}({tag}) = {{{','.join(str(point(p)) for p in points)}}};")
        return tag

    a,b,c = (0.,INNER_END_mm),(mid,INNER_END_mm),(mid,-R)
    d,e,f = (mid+R,0.),(seat,0.),(seat,h)
    g,j,k = (end+r,h),(end,h+r),(end,OUTER_END_mm)
    w = (0.,OUTER_END_mm)
    edges = [curve("Line",a,b),curve("Line",b,c),curve("Circle",c,(mid+R,-R),d),
             curve("Line",d,e),curve("Line",e,f),curve("Line",f,g),
             curve("Circle",g,(end+r,h+r),j),curve("Line",j,k),
             curve("Line",k,w),curve("Line",w,a)]
    loop, face = geo.new(), geo.new()
    geo.emit(f"Curve Loop({loop}) = {{{','.join(map(str,edges))}}};")
    geo.emit(f"Plane Surface({face}) = {{{loop}}};")
    geo.emit(f"seg[] = Extrude {{{{0,0,1}},{{0,0,0}},Pi/2}} {{Surface{{{face}}};}};")
    coarse = (22.,17.,13.,11.)[level]
    geo.emit(f"Mesh.MeshSizeMax = {coarse}; Mesh.MeshSizeFromPoints = 0;")
    geo.emit("Mesh.MeshSizeFromCurvature = 12; Mesh.MeshSizeExtendFromBoundary = 0;")
    geo.emit("Mesh.SecondOrderLinear = 1; Mesh.RandomSeed = 42; Mesh.MaxNumThreads3D = 1;")
    fields = []
    centres = ((mid+R,-R,R,(5.,3.8,2.7,2.)[level]),
               (end+r,h+r,r,(5.3,3.6,2.8,2.2)[level]))
    for cx,cz,radius,near in centres:
        field = geo.new()
        dist = f"Abs(Sqrt((Sqrt(x^2+y^2)-{cx})^2+(z-({cz}))^2)-{radius})"
        geo.emit(f'Field[{field}] = MathEval; Field[{field}].F = "{near}+({coarse}-{near})*Min(1,({dist}/10)^1.1)";')
        fields.append(field)
    field = geo.new()
    geo.emit(f"Field[{field}] = Min; Field[{field}].FieldsList = {{{','.join(map(str,fields))}}};")
    geo.emit(f"Background Field = {field};")
    return "\n".join(geo.lines)+"\n", centres


def boundary(coords,active):
    x = active[np.abs(coords[active,0])<1e-6]
    y = active[np.abs(coords[active,1])<1e-6]
    anchor = int(active[np.argmin(np.linalg.norm(coords[active]-[0.,0.,OUTER_END_mm],axis=1))])
    return {"XSYM":x,"YSYM":y}, [("XSYM",1,1),("YSYM",2,2),(anchor,3,3)]


def local_response(coords,tets,active,faces,centres,basis):
    normals = surface_normals(coords,tets,faces)
    radii_mm = np.hypot(coords[:,0],coords[:,1])
    zones = {"all": (active,None,None)}
    for name,(cx,cz,r,_) in zip(("middle_fillet","outer_fillet"),centres,strict=True):
        wall = np.abs(np.hypot(radii_mm-cx,coords[:,2]-cz)-r)<1e-4
        on_arc = faces[np.all(wall[faces[:,:3]],axis=1)]
        length_mm = max(np.linalg.norm(coords[on_arc[:,i]]-coords[on_arc[:,j]],axis=1).max()
                        for i,j in ((0,1),(1,2),(2,0)))
        zones[name] = (np.unique(on_arc),float(length_mm),r/4)
    amp_MPa,_,_,mean_slope = fkm_parameters(750.,6.3,False,forging=True)
    bolt = basis["outer"]/UNIT_N
    stem = basis["span"]/UNIT_N
    static_N, fatigue_N = max(corner_forces_N(STATIC_N)),max(corner_forces_N(CYCLIC_N))
    packages = [column(v.at_end(end)) for v,end in product(VARIANTS,("cylinder","chamber"))]
    phi = [j["load_fraction"] for j in packages]
    embedment = max(j["embedment_loss_N"] for j in packages)
    measures = {name:{"static_mises_MPa":0.,"principal_abs_MPa":0.,
                      "fatigue_utilisation":0.,"h_mm":h,"h_limit_mm":limit}
                for name,(_,h,limit) in zones.items()}
    for share,pretension_N in product((min(phi),max(phi)),
                                       (PRELOAD_N*(1-PRELOAD_SCATTER)-embedment,
                                        PRELOAD_N*(1+PRELOAD_SCATTER))):
        load_per_N = stem+share*bolt
        total = pretension_N*bolt+static_N*load_per_N
        dr = fatigue_N*load_per_N
        eq = mises(total)
        principal = np.max(np.abs(np.linalg.eigvalsh(stress_tensors(total))),axis=1)
        srange = np.max(np.abs(np.linalg.eigvalsh(stress_tensors(dr))),axis=1)
        G = normal_gradient(coords,tets,normals,srange)
        n = notch_support(G,750.,False)
        mean = np.maximum(np.linalg.eigvalsh(stress_tensors(pretension_N*bolt+.5*dr))[:,-1],0.)
        utilisation = (mises(dr)/2+mean_slope*mean)/(amp_MPa*n)
        for name,(nodes,_,_) in zones.items():
            m = measures[name]
            m["static_mises_MPa"] = max(m["static_mises_MPa"],float(eq[nodes].max()))
            m["principal_abs_MPa"] = max(m["principal_abs_MPa"],float(principal[nodes].max()))
            worst = nodes[np.argmax(utilisation[nodes])]
            if utilisation[worst]>m["fatigue_utilisation"]:
                m.update(fatigue_utilisation=float(utilisation[worst]),worst_xyz_mm=coords[worst].tolist(),
                         G_sigma_per_mm=float(G[worst]),n_sigma=float(n[worst]))
    for m in measures.values():
        m["local_elastic_factor"] = 500./m["static_mises_MPa"]
        m["fatigue_factor"] = 1./m["fatigue_utilisation"]
    return measures


def run(level,archive):
    stem = f"column_shoulder_{level}"
    geo_text,centres = geometry(level)
    with tempfile.TemporaryDirectory(prefix=stem+"_",dir=FEA) as temp:
        folder = Path(temp)
        geo = folder/(stem+".geo")
        geo.write_text(geo_text,encoding="ascii",newline="\n")
        mesh = geo.with_suffix(".msh")
        run_tool([BIN/"gmsh.exe",geo.name,"-3","-order","2","-format","msh2","-o",
                  mesh.name,"-nt","1","-nopopup"],folder,marker="Done writing")
        coords,tets,active,faces = read_mesh(mesh)
        mesh_name = stem+"_mesh.inp"
        write_mesh_include(folder/mesh_name,coords,tets,active)
        sets,bcs = boundary(coords,active)
        low = patch_loads(coords,plane_triangles(coords,faces,2,INNER_END_mm),
                          lambda x,y:np.ones_like(x),"inner cut")[0]
        high = patch_loads(coords,plane_triangles(coords,faces,2,OUTER_END_mm),
                           lambda x,y:np.ones_like(x),"outer cut")[0]
        bearing = patch_loads(coords,plane_triangles(coords,faces,2,COLLAR_H_mm),
                              lambda x,y:ring(x,y,0.,0.,COLUMN_INNER_SEAT_BORE_mm/2,NUT_BEAR_OD_mm/2,5.),
                              "seat")[0]
        basis = {}
        for mode,forces in (("outer",high-bearing),("span",bearing-low)):
            deck = folder/(stem+"_"+mode+".inp")
            input_deck(deck,mesh_name,sets,bcs,UNIT_N/4*forces)
            run_tool([BIN/"ccx.exe","-i",deck.stem],folder,marker="Job finished")
            basis[mode] = results_frd(deck.with_suffix(".frd"),len(coords))["STRESS"]
            if archive:
                (FEA/deck.name).write_bytes(deck.read_bytes())
        if archive:
            (FEA/geo.name).write_bytes(geo.read_bytes())
    data = {"outer_blend_mm":COLUMN_OUTER_BLEND_mm,
            "midspan_diameter_mm":COLUMN_MID_D_mm,"mesh_level":level,"nodes":int(len(active)),"tetrahedra":int(len(tets)),
            "zones":local_response(coords,tets,active,faces,centres,basis)}
    write_json(FEA/(stem+".json"),data)
    print(stem,len(active),data["zones"]["all"],flush=True)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels",default="0,1,2")
    parser.add_argument("--archive-level",type=int,default=2)
    args = parser.parse_args()
    for level in map(int,args.levels.split(",")):
        run(level,level==args.archive_level)
