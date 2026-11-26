"""Isolated-component stress check of the portal, with stiff bearing patches."""
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from solve import (BIN, HERE, LEVELS_MM, LOAD, boundary_faces, contacts,
                   crown_locks, load_patch, loading, mesh_data, nset, plane, sections,
                   stabilize, tool, triangle_quadrature)
from geometry import YOKE_BOTTOM_MM, YOKE_TOP_MM, build_geo
from hand import b_case, json_write
from frame_fea import results_frd


def portal_patch(xyz, rows, y_mm, target_N):
    faces = np.array([f[2] for f in rows])
    total = np.zeros(len(xyz))
    for shapes, points, areas in triangle_quadrature(xyz[faces]):
        distance = points[:,1]-y_mm
        weights = np.exp(-.5*(distance/14.)**2)*areas
        np.add.at(total,faces.ravel(),(weights[:,None]*shapes[None,:]).ravel())
    return total*target_N/total.sum()


def deck(path, mesh_path, xyz, groups, faces):
    blocks=stabilize(xyz,groups,("SHOE","LEFT","RIGHT","FRONT_YOKE"))
    out,_,_=contacts(xyz,faces)
    fixed={}
    applied={}
    manual=b_case(LOAD,.64)
    total_N=LOAD["force_315_N"]
    masks={
        "SHOE":(plane(faces["SHOE"],xyz,2,160.),lambda p:abs(p[1])>=84.),
        "RIGHT":(out["RIGHTBACK"]+out["RIGHTFRONT"],lambda p:78.<=p[1]<=110.),
        "FRONT_YOKE":(plane(faces["FRONT_YOKE"],xyz,2,YOKE_TOP_MM),
                      lambda p:(p[0]-231.)**2+(abs(p[1])-189.)**2<=33.**2)
    }
    for name,(rows,keep) in masks.items():
        fixed[name]=sorted({n for _,_,ns in rows for n in ns if keep(xyz[n])})
        if len(fixed[name]) < 3:
            raise ValueError(f"Incomplete stiff bearing boundary on {name}")
    f=1.05*loading(xyz,faces,.64)
    shoe=np.unique([ids for _,ids in groups["SHOE"]])
    applied["SHOE"] = f[shoe,2],shoe
    f=load_patch(xyz,out["RIGHTLOW"],2,0.,.64*total_N)
    key=np.unique([ids for _,ids in groups["RIGHT"]])
    applied["RIGHT"] = f[key,2],key
    end_load_N=manual["actual_portal_far_end_total_N"]
    load_yoke=portal_patch(xyz,out["FRONTUNDER"],93.5,.64*end_load_N)
    load_yoke+=portal_patch(xyz,out["FRONTUNDER"],-93.5,.36*end_load_N)
    yoke=np.unique([ids for _,ids in groups["FRONT_YOKE"]])
    applied["FRONT_YOKE"] = load_yoke[yoke],yoke
    parts=list(applied)
    with mesh_path.open("w",encoding="ascii",newline="\n") as mesh:
        mesh.write("*NODE\n")
        nodes=sorted({tag for name in parts for _,row in groups[name] for tag in row})
        for tag in nodes:
            x,y,z=xyz[tag]
            mesh.write(f"{tag},{x:.12g},{y:.12g},{z:.12g}\n")
        for name in parts:
            mesh.write(f"*ELEMENT,TYPE=C3D4,ELSET={name}\n")
            for eid,ids in groups[name]:
                mesh.write(f"{eid},"+",".join(map(str,ids))+"\n")
    lines=["*HEADING","Stiff-bearing component comparison. Separate bodies. 315 bar.",
           f"*INCLUDE,INPUT={mesh_path.name}","*MATERIAL,NAME=STEEL","*ELASTIC","210000.,.3"]
    for name in parts:
        lines += [f"*SOLID SECTION,ELSET={name},MATERIAL=STEEL",*nset(name+"Z",fixed[name])]
    lines += ["*BOUNDARY"]
    for name in parts:
        tags=blocks[name]
        lines += [f"{name}Z,3,3",f"{tags[0]},1,2",f"{tags[1]},2,2"]
    lines += ["*STEP","*STATIC","*CLOAD"]
    for name in parts:
        values,tags=applied[name]
        lines += [f"{n},3,{f:.12g}" for f,n in zip(values,tags) if abs(f)>1e-10]
    lines += ["*NODE FILE","U,RF","*EL FILE","S","*END STEP"]
    path.write_text("\n".join(lines)+"\n",encoding="ascii",newline="\n")
    return fixed,applied


def run():
    geo=HERE/"portal.geo"
    build_geo(geo)
    result={}
    for level,step in enumerate(LEVELS_MM):
        with TemporaryDirectory(dir=HERE,prefix="component_run_") as temp:
            folder=Path(temp)
            mesh=folder/"portal.msh"
            tool([BIN/"gmsh.exe",geo,"-3","-nt","1","-clmin",4.5-level*.6,"-clmax",step,
                  "-setnumber","Mesh.MeshSizeFromCurvature",6+2*level,"-format","msh2","-o",mesh,"-v","3"],
                 folder,folder/"mesh.log",350)
            xyz,groups=mesh_data(mesh,order=1)
            faces=boundary_faces(groups)
            path=folder/"component.inp"
            fixed,loads=deck(path,folder/"mesh.inp",xyz,groups,faces)
            if level==0:
                (HERE/"component_0.inp").write_bytes(path.read_bytes())
            ans=tool([BIN/"ccx.exe","-i","component"],folder,folder/"component.log",650)
            if "Job finished" not in ans:
                raise RuntimeError(ans[-2500:])
            states=results_frd(path.with_suffix(".frd"),len(xyz))
            zeros={"STRESS":np.zeros_like(states["STRESS"])}
            relative_balance={}
            for key,tags in fixed.items():
                r=states["FORC"][tags,2].sum()
                values,ids=loads[key]
                target=values.sum()
                applied_at_fixtures=values[np.isin(ids,tags)].sum()
                relative_balance[key]=abs(r+target-applied_at_fixtures)/target
            checks=sections(xyz,groups,[zeros,None,states],.64)
            cut_fields=(("key","RIGHT",0),("yoke","FRONT_YOKE",1))
            for label,body,axis in cut_fields:
                cut=checks[label]["section_center_mm"][axis]
                section_modulus=checks[label]["nominal_section_modulus_mm3"]
                constrained=np.asarray(fixed[body])
                forces,loaded=loads[body]
                c_arm=xyz[constrained,axis]-cut
                l_arm=xyz[loaded,axis]-cut
                reaction=states["FORC"][constrained,2]
                bending_Nmm=float(reaction[c_arm<0]@c_arm[c_arm<0]+forces[l_arm<0]@l_arm[l_arm<0])
                checks[label].update(stiff_patch_equilibrium_moment_Nmm=abs(bending_Nmm),
                                     stiff_patch_nominal_bending_MPa=abs(bending_Nmm)/section_modulus,
                                     upward_fixture_reaction_N=float(reaction[reaction>0].sum()))
            foot=plane(faces["SHOE"],xyz,2,0.)
            loaded_foot=np.unique([n for _,_,row in foot for n in row if xyz[n,0]>=LOAD["contact_x_mm"][0]])
            result[str(level)]=dict(max_mesh_mm=step,nominal_by_section=checks,force_balances=relative_balance,
                shoe_flexure_relative_to_stiff_patches_300_bar_mm=float(states["DISP"][loaded_foot,2].max())/1.05)
            print(level,result[str(level)]["nominal_by_section"],flush=True)
    json_write(HERE/"component_study.json",dict(status="LINEAR_STIFF_BEARING_DIAGNOSTIC",
               caution="Separate parts, stiff bearing patches, unpreloaded. Results do not qualify the complete load path.",
               levels=result))


if __name__=="__main__":
    run()

