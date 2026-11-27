"""Exploratory C3D10 end-plate checks for a five-piece fixed roof."""

from argparse import ArgumentParser
from math import exp
from pathlib import Path
from tempfile import TemporaryDirectory
import json

import numpy as np

from ring import GATE_X_MM, HERE, LOADED_LENGTH_MM, Layout, aperture_faces, make_geo, pressure, relief
from ring import choose, janssen, main_cylinder_force_N, support, volume_mm3
from loads import band
from solver import deck, frd_fields, jacobian_statistics, mesh, mises, quad, reactions, tool
from fkm import margins, normal_gradient

PLATE_GRADE = (900.,1100.,False)
PLATE_MM = 18.


def section_pressures(case, x0_mm, x1_mm):
    start_mm = max(case["punch_x_mm"], x0_mm)
    radial = band(case["face_MPa"],case["K"],case["decay_mm_inv"],start_mm,x1_mm,case["punch_x_mm"])
    p_entry_MPa = case["roof"]["inlet_MPa"]
    pressure_integral_MPa_mm = radial["integral_MPa_mm"]
    return case | {"roof":radial | {"normal_force_N":150.*pressure_integral_MPa_mm, "inlet_MPa":p_entry_MPa},
                   "wall_friction_N":case["mu"]*420.*pressure_integral_MPa_mm,
                   "each_side_normal_force_N":60.*pressure_integral_MPa_mm}


def axial_bearing(xyz, faces, x_plane_mm):
    xcoord = xyz[faces,0]
    faces = faces[np.max(np.abs(xcoord-x_plane_mm),axis=1)<1e-5]
    force = np.zeros(len(xyz))
    for face in faces:
        for shape,_,area_vector in quad(xyz[face]):
            force[face] += shape * abs(area_vector[0])
    return force / force.sum()


def run(case, label, x0_mm, mesh_mm, layout):
    x1_mm = x0_mm + PLATE_MM
    inner_r_mm = 30.
    with TemporaryDirectory(dir=HERE,prefix="t22g-lamella-") as label_path:
        work = Path(label_path)
        geo = make_geo(layout,mesh_mm,inner_r_mm,38.,x0_mm,PLATE_MM)
        xyz,tets,active,tri = mesh(work,geo)
        initial = xyz.copy()
        if x1_mm == GATE_X_MM:
            xyz[:,0] -= relief(xyz)
        jacobians = jacobian_statistics(xyz,tets)
        if jacobians["nonpositive_element_count"]:
            raise ValueError(f"Lamella element inversion {jacobians}")
        region = aperture_faces(initial,tri,inner_r_mm)
        local_case = section_pressures(case,x0_mm,x1_mm)
        loads = pressure(xyz,initial,region,local_case,layout.roof_width_mm,True,True,inner_r_mm)
        entry_before_N = case["main_force_N"] * (1.-exp(-case["decay_mm_inv"]*max(0.,x0_mm-case["punch_x_mm"])))
        loads[:,0] += axial_bearing(initial,tri,x0_mm)*entry_before_N
        fixed = support(xyz,active,layout.roof_width_mm,"downstream",inner_r_mm) if x1_mm==GATE_X_MM else None
        if fixed is None:
            outer = np.isclose(initial[active,0],x1_mm)
            fixed = {1:active[outer]}
            def near(p):
                return int(active[np.argmin(np.linalg.norm(xyz[active]-p,axis=1))])
            fixed[2] = [near((x1_mm,0.,-130.))]
            fixed[3] = [near((x1_mm,y,0.)) for y in (-140.,140.)]
        deck(work,xyz,tets,active,fixed,[loads],(0,100,200,300,315))
        tool("ccx.exe",["-i","roof"],work,"Job finished")
        fields = frd_fields(work/"roof.frd",len(xyz))
        rf = reactions(work/"roof.dat")
    if len(fields)!=5 or len(rf)!=5:
        raise RuntimeError(f"Lamella {label} has an incomplete history")
    proof, start, end = (fields[i]["STRESS"] for i in (4,0,3))
    grad = normal_gradient(xyz,tets,tri,end-start)
    values = margins(proof,start,end,PLATE_GRADE,grad)
    straight_x = initial[active,0]
    roi = active[(straight_x>x0_mm+2.5)&(straight_x<x1_mm-2.5)]
    peak = int(roi[np.argmin(values["static"][roi])])
    governs = int(roi[np.argmin(values["FKM"][roi])])
    return {"layout":layout.data(), "load":label,"x_mm":[x0_mm,x1_mm],"element_mm":mesh_mm,
            "nodes":len(active),"elements":len(tets),"jacobians":jacobians,
            "volume_mm3":volume_mm3(xyz,tets),"grade_Rp02_Rm_MPa":list(PLATE_GRADE[:2]),
            "force_balance_fraction":float(np.linalg.norm(rf[-1]+loads.sum(axis=0))/case["main_force_N"]),
            "static_factor":float(values["static"][peak]),"VM_315_MPa":float(mises(proof[peak])),
            "static_point_mm":xyz[peak].tolist(),"FKM":float(values["FKM"][governs]),
            "FKM_no_notch_credit":float(values["FKM_no_notch_credit"][governs]),
            "fatigue_point_mm":xyz[governs].tolist(),"fatigue_n_sigma":float(values["n_sigma"][governs])}


def main():
    parser=ArgumentParser()
    parser.add_argument("--mesh",type=float,default=8.)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    _,long,_=choose()
    short=janssen(main_cylinder_force_N(315),.60,.20,40./1.23)
    layout=Layout("forged",104.,172.,172.)
    output=[]
    for case,label,x_mm in ((long,"inlet_long",205.),(short,"outlet_short",277.)):
        output.append(run(case,label,x_mm,args.mesh,layout))
        args.out.write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
                            encoding="utf-8",newline="\n")
        print(label,output[-1]["static_factor"],output[-1]["FKM"],flush=True)


if __name__=="__main__":
    main()

