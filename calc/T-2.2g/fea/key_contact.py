"""Front key and three crowned bearing lands, local contact C3D10 diagnostic."""

from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from hand import shoe_hand, choose
from layout import CROWN_MM, EDGE_R_MM, KEY_CLOSED_Y_MM, LOCK_LOWER_Y_MM, LOCK_UPPER_Y_MM, STATIONS
from solver import frd_fields, jacobian_statistics, mesh, node_set, quad, read_mesh_file, tool
from window_geometry import Model, rect

KEY_DEPTH_MM = STATIONS["front"]["key_depth_mm"]
KEY_WIDTH_MM = STATIONS["front"]["key_width_mm"]
PLANES = {"shoe":(82.,132.,-12.,0.),"lower":(*LOCK_LOWER_Y_MM,-12.,0.),
          "upper":(*LOCK_UPPER_Y_MM,KEY_DEPTH_MM,KEY_DEPTH_MM+12.)}
SIDE_CORNERS = ((0,1,2),(0,3,1),(1,3,2),(0,2,3))
ALLOWED_MEAN_MPa = 70.


def part_geometry(size_mm, interval_yz_mm):
    y0,y1,z0,z1=interval_yz_mm
    shape=Model(size_mm)
    shape.prism(rect(-KEY_WIDTH_MM/2,KEY_WIDTH_MM/2,y0,y1),(EDGE_R_MM,)*4,(0,1),z0,z1-z0)
    return shape.geo()


def planes(xyz, faces, target_mm):
    return faces[np.max(np.abs(xyz[faces,2]-target_mm),axis=1)<1.e-5]


def find_surfaces(tets, faces, element_offset):
    mapping={}
    for e,row in enumerate(tets,1+element_offset):
        for i,side in enumerate(SIDE_CORNERS,1):
            result=tuple(sorted(row[list(side)]))
            mapping[result]=None if result in mapping else (e,i)
    output=[]
    for face in faces:
        reply=mapping.get(tuple(sorted(face[:3])))
        if reply is not None:
            output.append(reply)
    return output


def build(work, size_mm, from_files=False):
    data={}
    node_offset=element_offset=0
    nodes=[np.zeros((1,3))]
    tets=[]
    for name,dimensions in {"key":(*KEY_CLOSED_Y_MM,0.,KEY_DEPTH_MM),**PLANES}.items():
        p=work/name
        if from_files:
            xyz,conn,active,faces=read_mesh_file(p/"model.msh")
        else:
            p.mkdir()
            xyz,conn,active,faces=mesh(p,part_geometry(size_mm,dimensions))
        z_contact_mm=KEY_DEPTH_MM if name=="upper" else 0.
        expected=planes(xyz,faces,z_contact_mm)
        side_info=find_surfaces(conn,expected,element_offset)
        if name=="key":
            top=planes(xyz,faces,KEY_DEPTH_MM)
            data[name]={"active":active+node_offset,"bottom_faces":expected+node_offset,"top_faces":top+node_offset,
                        "bottom_surface":side_info,"top_surface":find_surfaces(conn,top,element_offset)}
        else:
            y0,y1,z0,z1=dimensions
            top=name=="upper"
            face_ids=np.unique(expected)
            end=(xyz[face_ids,1]-(y0+y1)/2)/((y1-y0)/2)
            # Crown is ground in Y and has zero initial gap at the apex.
            xyz[face_ids,2] += (1. if top else -1.) * CROWN_MM * end**2
            foot=planes(xyz,faces,z1 if top else z0)
            data[name]={"fixed":np.unique(foot)+node_offset,"faces":expected+node_offset,
                        "surface":side_info,"actual_plane_z_mm":z_contact_mm}
        quality=jacobian_statistics(xyz,conn)
        if quality["nonpositive_element_count"]:
            raise ValueError(f"{name} invalid Jacobians {quality}")
        data[name]["mesh_quality"]=quality
        nodes.append(xyz[1:])
        tets.extend(conn+node_offset)
        node_offset+=len(xyz)-1
        element_offset+=len(conn)
    return np.vstack(nodes),np.array(tets),data


def input_file(path, xyz, tets, data, closing_mm):
    lines=["*HEADING","REV T-2.2g local lock","*NODE"]
    active=np.unique(tets)
    for tag in active:
        x,y,z=xyz[tag]
        lines.append(f"{tag},{x:.11g},{y:.11g},{z:.11g}")
    lines.append("*ELEMENT,TYPE=C3D10,ELSET=physical")
    lines.extend(str(n)+","+",".join(map(str,row)) for n,row in enumerate(tets,1))
    key=data["key"]
    base=key["active"]
    near=lambda p:int(base[np.argmin(np.linalg.norm(xyz[base]-p,axis=1))])
    loc_a,loc_b=near((0.,88.,29.)),near((0.,237.,29.))
    lines.extend(["*ELEMENT,TYPE=SPRING1,ELSET=locators",f"{len(tets)+1},{loc_a}",f"{len(tets)+2},{loc_b}",
                  "*SPRING,ELSET=locators","3","20.", "*MATERIAL,NAME=STEEL","*ELASTIC","210000.,.30",
                  "*SOLID SECTION,ELSET=physical,MATERIAL=STEEL"])
    for name in PLANES:
        lines.extend(node_set(name.upper()+"_BACK",data[name]["fixed"]))
    surfaces={"low_key":key["bottom_surface"],"top_key":key["top_surface"]}
    surfaces.update({f"{k}_land":data[k]["surface"] for k in PLANES})
    for name,faces in surfaces.items():
        lines.append(f"*SURFACE,TYPE=ELEMENT,NAME={name}")
        lines.extend(f"{i},S{s}" for i,s in faces)
    lines+=["*SURFACE INTERACTION,NAME=steel_pair",
            "*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR","50000.,1.","*FRICTION",".15,10000."]
    for name,master in (("shoe","low_key"),("lower","low_key"),("upper","top_key")):
        lines.extend(["*CONTACT PAIR,INTERACTION=steel_pair,TYPE=NODE TO SURFACE,SMALL SLIDING",f"{name}_land,{master}"])
    lines.extend(["*BOUNDARY","UPPER_BACK,1,3","LOWER_BACK,1,3","SHOE_BACK,1,2",
                  f"{loc_a},1,2",f"{loc_b},1,1"])
    for δ in closing_mm:
        lines.extend(["*STEP,INC=100","*STATIC",".25,1.,1.e-6,.35",
                      "*CONTROLS,PARAMETERS=TIME INCREMENTATION",
                      "12,30,9,100,45,8,0,10,0,0",".5,.5,.75,.85,,,1.5",
                      "*BOUNDARY",f"SHOE_BACK,3,3,{δ:.12e}","*NODE FILE,FREQUENCY=999999","U,RF",
                      "*EL FILE,FREQUENCY=999999","S","*CONTACT FILE,FREQUENCY=999999","CDIS,CSTR","*END STEP"])
    path.write_text("\n".join(lines)+"\n",encoding="ascii",newline="\n")


def response(xyz,tets,data,work,closing_mm):
    path=work/"roof.inp"
    input_file(path,xyz,tets,data,closing_mm)
    tool("ccx.exe",["-i","roof"],work,"Job finished",timeout_s=900)
    models=frd_fields(path.with_suffix(".frd"),len(xyz))
    if len(models)!=len(closing_mm):
        raise ValueError(f"CCX returned {len(models)} increments for {len(closing_mm)} end steps")
    return contact_statistics(xyz,data,closing_mm,models)


def contact_statistics(xyz,data,closing_mm,models):
    rows=[]
    for travel_mm,fields in zip(closing_mm,models,strict=True):
        pressure_MPa=fields["CONTACT"][:,3]
        faces={}
        for name in PLANES:
            part=data[name]
            surface=part["faces"]
            area_mm2,normal_N=0.,0.
            for tri in surface:
                for shape,_,vector in quad(xyz[tri]):
                    da_mm2=np.linalg.norm(vector)
                    area_mm2 += da_mm2
                    normal_N += da_mm2*max(0.,float(shape @ pressure_MPa[tri]))
            faces[name]={"peak_MPa":float(max(pressure_MPa[np.unique(surface)])),
                         "gross_mean_MPa":float(normal_N/area_mm2),"gross_area_mm2":float(area_mm2),
                         "interpolated_force_N":float(normal_N),
                         "normal_reaction_N":float(fields["FORC"][part["fixed"],2].sum())}
        applied_N=faces["shoe"]["normal_reaction_N"]
        rows.append({"travel_mm":float(travel_mm),"shoe_force_N":applied_N,"contact":faces,
                     "exact_normal_balance_error_N":sum(row["normal_reaction_N"] for row in faces.values())})
    return rows


def main():
    parser=ArgumentParser()
    parser.add_argument("--mesh",required=True,type=float)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--proof-travel-mm",type=float)
    parser.add_argument("--read-progress",type=Path,
                        help="Preserve completed steps from an in-progress or interrupted CCX run.")
    args=parser.parse_args()
    nominal,_,_=choose()
    baseline=shoe_hand(nominal)["stations"]["front"]["peak_side_315_N"]
    targets=np.array([0.,100.,200.,300.,315.])/315.*baseline
    if args.read_progress:
        work=args.read_progress
        xyz,tets,data=build(work,args.mesh,from_files=True)
        states=frd_fields(work/"roof.frd",len(xyz))
        nums=tuple(map(float,re.findall(r"^SHOE_BACK,3,3,([-+.eE0-9]+)$",
                                       (work/"roof.inp").read_text(encoding="ascii"),re.M)))
        completed=sum(len(parts)==7 and parts[5]=="0.100000E+01"
                      for parts in (line.split() for line in (work/"roof.sta").read_text(encoding="ascii").splitlines()))
        completed=min(completed,len(states))
        rows=contact_statistics(xyz,data,nums[:completed],states[:completed])
        report={"status":"PARTIAL_DIAGNOSTIC","mesh_mm":args.mesh,
                "target_forces_N":targets[:completed].tolist(),
                "steps_completed":completed,"rows":rows}
        args.out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                            encoding="utf-8",newline="\n")
        print("Completed local key rows saved:",completed,flush=True)
        return
    with TemporaryDirectory(dir=HERE,prefix="t22g-key-") as name:
        work=Path(name)
        xyz,tets,data=build(work,args.mesh)
        if args.proof_travel_mm:
            rows=response(xyz,tets,data,work,(0.,args.proof_travel_mm))
            failure={"status":"PROOF_DIAGNOSTIC","mesh_mm":args.mesh,"elements":len(tets),
                     "target_315_N":baseline,"rows":rows,
                     "relative_315_force_error":abs(rows[-1]["shoe_force_N"]-baseline)/baseline}
            args.out.write_text(json.dumps(failure,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+"\n",
                                encoding="utf-8",newline="\n")
            print("Front key proof force",rows[-1]["shoe_force_N"],flush=True)
            return
        trials=response(xyz,tets,data,work,(0.,.08,.18,.34))
        observed=np.array([row["shoe_force_N"] for row in trials])
        if observed[-1]<targets[-1]:
            raise ValueError("Local contact calibration requires a larger travel")
        guess=np.interp(targets,observed,[row["travel_mm"] for row in trials])
        rows=response(xyz,tets,data,work,guess)
        error=[abs(row["shoe_force_N"]-n)/max(1.,n) for row,n in zip(rows,targets,strict=True)]
    out={"scope":"Front upper and two lower pads, separate C3D10 volumes; reaction based pressure labels",
         "mesh_mm":args.mesh,"nodes":len(xyz)-1,"elements":len(tets),
         "target_by_nominal_hydraulic_pressure_bar":[0,100,200,300,315],
         "target_forces_N":targets.tolist(),"calibrated_travel_mm":guess.tolist(),"maximum_force_relative_error":max(error[1:]),
         "static_lower_limited_screen_MPa":480.,"analogue_steel_mean_screen_MPa":ALLOWED_MEAN_MPa,
         "rows":rows,"calibration":trials}
    args.out.write_text(json.dumps(out,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+"\n",
                        encoding="utf-8",newline="\n")
    print("front key applied forces", [row["shoe_force_N"] for row in rows],flush=True)


if __name__=="__main__":
    main()

