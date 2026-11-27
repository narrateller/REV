"""Displacement-driven gate-end submodel of the diagnostic roof ring."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json

import numpy as np
from scipy.spatial import cKDTree

from fkm import margins, normal_gradient
from ring import (GEOMETRY, ECCENTRICITY_MM, HERE, BEARING_X_MM, GATE_MM,
                  branch_weights, rectangle_geometry)
from loads import PRESSURES_BAR, janssen, main_cylinder_force_N
from solver import deck, frd_fields, jacobian_statistics, mesh, tool

CUT_X_MM = 255.
PAIR_EDGE_IDS = np.array([(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)])
BARYCENTRIC_GRADIENTS = np.array([[-1.,-1.,-1.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])


def support(xyz,active):
    axial = active[np.isclose(xyz[active,0],BEARING_X_MM,atol=1e-7)]
    def near(y):
        return int(axial[np.argmin(np.linalg.norm(xyz[axial]-[BEARING_X_MM,y,0.],axis=1))])
    a,b = near(-185.),near(185.)
    return {1:axial,2:[a],3:[a,b]}


def parent_fields(work,case,size_mm):
    g = GEOMETRY
    xyz,tets,active,faces = mesh(work,rectangle_geometry(g,size_mm,2))
    quality=jacobian_statistics(xyz,tets)
    if quality["nonpositive_element_count"]:
        raise ValueError(quality)
    force=branch_weights(xyz,faces,g,case,ECCENTRICITY_MM)
    deck(work,xyz,tets,active,support(xyz,active),[force],(315,))
    tool("ccx.exe",["-i","roof"],work,"Job finished")
    field=frd_fields(work/"roof.frd",len(xyz))[-1]["DISP"]
    return xyz,tets,field


def shape_functions(bary):
    a,b=PAIR_EDGE_IDS.T
    return np.column_stack([bary*(2*bary-1),4*bary[:,a]*bary[:,b]])


def interpolate_displacements(points,xyz,tets,values):
    """Invert the isoparametric parent C3D10 mapping at each cut node."""
    coords=xyz[tets]
    vertex=coords[:,:4]
    distances,near=cKDTree(vertex.mean(axis=1)).query(points,k=min(35,len(tets)))
    linear = np.swapaxes(vertex[:,1:]-vertex[:,:1],1,2)
    a,b=PAIR_EDGE_IDS.T
    displacement = []
    extrapolation = []
    position_error_mm = []
    for pt,candidates in zip(points,near,strict=True):
        p=coords[candidates]
        local=np.linalg.solve(linear[candidates],(pt-p[:,0])[...,None])[...,0]
        for _ in range(7):
            bary=np.column_stack([1-local.sum(axis=1),local])
            shape=shape_functions(bary)
            grad_lin=(4*bary-1)[...,None]*BARYCENTRIC_GRADIENTS
            grad_curved=4*(bary[:,a,None]*BARYCENTRIC_GRADIENTS[b]
                           +bary[:,b,None]*BARYCENTRIC_GRADIENTS[a])
            grad=np.concatenate([grad_lin,grad_curved],axis=1)
            J=np.einsum("npc,npd->ncd",p,grad)
            error=np.einsum("np,npc->nc",shape,p)-pt
            nonsingular=abs(np.linalg.det(J))>1e-9
            local[nonsingular]-=np.linalg.solve(J[nonsingular],error[nonsingular,:,None])[...,0]
        bary=np.column_stack([1-local.sum(axis=1),local])
        shape=shape_functions(bary)
        error=np.linalg.norm(np.einsum("np,npc->nc",shape,p)-pt,axis=-1)
        chosen=np.argmax(bary.min(axis=1)-np.minimum(10.,error)*10)
        extrapolation.append(float(max(0.,-min(bary[chosen]))))
        position_error_mm.append(float(error[chosen]))
        if extrapolation[-1]>.032 or error[chosen]>.001:
            raise ValueError(f"Cut node outside parent interpolation tolerance at {pt}")
        displacement.append(shape[chosen] @ values[tets[candidates[chosen]]])
    return np.array(displacement),max(extrapolation),max(position_error_mm)


def step_displacements(path,ids,proof_displacement):
    """Apply the coarse field at each linear pressure increment."""
    lines=path.read_text(encoding="ascii").splitlines()
    output=[]
    bar_index=0
    for line in lines:
        if line.startswith("*CLOAD"):
            output.append("*BOUNDARY,OP=MOD")
            fraction=PRESSURES_BAR[bar_index]/315
            for i,disp in zip(ids,proof_displacement,strict=True):
                output.extend(f"{i},{dof},{dof},{value*fraction:.12e}"
                              for dof,value in enumerate(disp,1))
            bar_index+=1
        output.append(line)
    assert bar_index==len(PRESSURES_BAR)
    path.write_text("\n".join(output)+"\n",encoding="ascii",newline="\n")


def trial(work,case,size_mm,parent):
    g=GEOMETRY
    xyz,tets,active,faces=mesh(work,rectangle_geometry(g,size_mm,2,entry_mm=CUT_X_MM))
    quality=jacobian_statistics(xyz,tets)
    if quality["nonpositive_element_count"]:
        raise ValueError(quality)
    cut=active[np.isclose(xyz[active,0],CUT_X_MM,atol=1e-7)]
    moved,extrap,error_mm=interpolate_displacements(xyz[cut],*parent)
    force=branch_weights(xyz,faces,g,case,ECCENTRICITY_MM,entry_mm=CUT_X_MM)
    # Use full displacement at the local cut and the same X footing at the rails.
    fixed={1:support(xyz,active)[1],2:[],3:[]}
    deck(work,xyz,tets,active,fixed,[force],PRESSURES_BAR)
    step_displacements(work/"roof.inp",cut,moved)
    tool("ccx.exe",["-i","roof"],work,"Job finished")
    fields=frd_fields(work/"roof.frd",len(xyz))
    assert len(fields)==len(PRESSURES_BAR)
    proof=fields[-1]["STRESS"]
    cyc,start=fields[-2]["STRESS"],fields[0]["STRESS"]
    gradient=normal_gradient(xyz,tets,faces,cyc-start)
    metrics=margins(proof,start,cyc,g.grade,gradient)
    region=active[(xyz[active,0]>=270.)&(xyz[active,0]<=GATE_MM)]
    key=int(region[np.argmin(metrics["FKM"][region])])
    # CalculiX FORC includes nodal applied load alongside reactions. The
    # global vector sum of internal nodal forces is the equilibrium residual.
    balances =[float(np.linalg.norm(f["FORC"].sum(axis=0)) /
                     max(1.,case["wall_friction_N"]*b/315))
               for b,f in zip(PRESSURES_BAR,fields,strict=True)]
    residual_displacements_mm=float(np.max(np.abs(fields[-1]["DISP"][cut]-moved)))
    return dict(mesh_mm=size_mm,nodes=len(active),elements=len(tets),cut_x_mm=CUT_X_MM,
                proof_C3D10_integration=quality, pressure_steps_bar=list(PRESSURES_BAR),
                maximum_boundary_displacement_roundoff_mm=residual_displacements_mm,
                maximum_parent_inversion_residual_mm=error_mm,maximum_barycentric_extrapolation=extrap,
                FKM=float(metrics["FKM"][key]), static=float(metrics["static"][region].min()),
                FKM_no_gradient=float(metrics["FKM_no_notch_credit"][key]),
                location_xyz_mm=xyz[key].tolist(),global_force_balance_fraction=balances,
                scope="tied lamella geometry, traction-transferred liner, no actual contact")


if __name__=="__main__":
    p=ArgumentParser()
    p.add_argument("--mesh",type=float,nargs="+",required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    case=janssen(main_cylinder_force_N(315),.6,.2,89.4)
    records=[]
    with TemporaryDirectory(prefix="end-",dir=HERE) as name:
        base=Path(name)
        parent_dir=base/"parent"
        parent_dir.mkdir()
        solution=parent_fields(parent_dir,case,15.)
        for j,h in enumerate(args.mesh):
            d=base/f"local-{j}"
            d.mkdir()
            records.append(trial(d,case,h,solution))
            args.out.write_text(json.dumps(records,indent=2,allow_nan=False)+"\n",encoding="utf-8")
            print(h,records[-1]["FKM"],records[-1]["static"],flush=True)

