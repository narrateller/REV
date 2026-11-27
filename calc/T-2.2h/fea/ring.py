"""C3D10 feasibility screen of the ring and end-seat load path.

Loads act on backing flats. The wear liner and lamella seam are condensed.
The diagnostic is therefore not the qualification model of the end.
"""
from argparse import ArgumentParser
import json
from math import pi
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))

from fkm import margins, normal_gradient
from hand import (ECCENTRICITY_MM, Ring, frame, section_grid, skew_weight)
from layout import gate_relief_mm, smoothstep
from loads import PRESSURES_BAR, janssen, main_cylinder_force_N
from solver import deck, frd_fields, interpolation, jacobian_statistics, mesh, quad, reactions, tool

GATE_MM = 295.
ENTRY_MM = 205.
# Through-gate seats beyond the moving blade, to the front traverse.
RAIL_Y_MM = (172.,201.)
RAIL_Z_MM = (-95.,95.)
BEARING_X_MM = 349.
GEOMETRY = Ring("forged",203.,265.,37.,179.,56.,2,75.)


def rectangle_geometry(g, size_mm, optimize=1, entry_mm=ENTRY_MM):
    lines = ['SetFactory("OpenCASCADE");']
    tag = 10

    def point(y,z):
        nonlocal tag
        tag += 1
        lines.append(f"Point({tag}) = {{{entry_mm},{y:.12g},{z:.12g},{size_mm}}};")
        return tag

    def contour(half_y,half_z,r):
        nonlocal tag
        corners = []
        for sy,sz in ((1,1),(-1,1),(-1,-1),(1,-1)):
            centre_y = sy*(half_y-r)
            centre_z = sz*(half_z-r)
            a = point(centre_y+sy*r,centre_z)
            b = point(centre_y,centre_z+sz*r)
            c = point(centre_y,centre_z)
            if sy*sz < 0:
                a,b = b,a
            tag += 1
            lines.append(f"Circle({tag}) = {{{a},{c},{b}}};")
            corners.append((a,b,tag))
        edges = []
        for i,(start,_,curve) in enumerate(corners):
            tag += 1
            lines.append(f"Line({tag}) = {{{corners[i-1][1]},{start}}};")
            edges.extend((tag,curve))
        tag += 1
        lines.append(f"Curve Loop({tag}) = {{{','.join(map(str,edges))}}};")
        return tag

    exterior = contour(g.side_half_mm,g.band_half_mm,g.outer_R_mm)
    interior = contour(g.inner_y_mm,g.inner_z_mm,g.inner_R_mm)
    lines += [f"Plane Surface(1) = {{{exterior},{interior}}};",
              f"ring[] = Extrude {{{GATE_MM-entry_mm:g},0,0}} {{Surface{{1}};}};"]
    y0,y1 = RAIL_Y_MM
    z0,z1 = RAIL_Z_MM
    for i,y_mm in enumerate((y0,-y1),1001):
        # Slight overlap to guarantee a joined OCC solid. Mass based on
        # analytic new length, not on the overlap.
        lines.append(f"Box({i}) = {{294.9,{y_mm},{z0},54.1,{y1-y0},{z1-z0}}};")
    lines += ["merged[] = BooleanUnion{Volume{ring[1]}; Delete;}{Volume{1001,1002}; Delete;};"]
    # Cross-section of each wing-clearance pocket, extruded past the Z sweep.
    for base,sign in ((3100,-1),(4100,1)):
        ys=np.array([77.5,78.,79.,80.,83.,89.,96.,103.,111.,119.,125.,130.,139.,150.,158.,164.])
        pocket=[]
        for i,y in enumerate(ys,1):
            pocket.append(base+i)
            relief = gate_relief_mm(y)*smoothstep((164.-y)/30.)
            lines.append(f"Point({base+i}) = {{{295.-relief:.12g},{sign*y:.12g},-272.,{size_mm}}};")
        a,b=base+21,base+22
        lines += [f"Point({a}) = {{301.,{sign*ys[-1]},-272.,{size_mm}}};",
                  f"Point({b}) = {{301.,{sign*ys[0]},-272.,{size_mm}}};",
                  f"Spline({base+30}) = {{{','.join(map(str,pocket))}}};",
                  f"Line({base+31}) = {{{pocket[-1]},{a}}};",
                  f"Line({base+32}) = {{{a},{b}}};",
                  f"Line({base+33}) = {{{b},{pocket[0]}}};",
                  f"Curve Loop({base+34}) = {{{base+30},{base+31},{base+32},{base+33}}};",
                  f"Plane Surface({base+35}) = {{{base+34}}};",
                  f"slot{base}[] = Extrude {{0,0,544}} {{Surface{{{base+35}}};}};"]
    lines += ["body[] = BooleanDifference{Volume{merged[]}; Delete;}"
              "{Volume{slot3100[1],slot4100[1]}; Delete;};",
              f"Mesh.MeshSizeMin = {size_mm*.65}; Mesh.MeshSizeMax = {size_mm};",
              "Mesh.MeshSizeFromCurvature = 0;", "Mesh.SecondOrderLinear = 0;",
              f"Mesh.HighOrderOptimize = {optimize};", "Mesh.RandomSeed = 1;"]
    return "\n".join(lines) + "\n"


def branch_weights(xyz, triangles, g, case, eccentricity_mm, entry_mm=ENTRY_MM):
    """Work-conjugate quadratic face loads, separately normalised per wall."""
    F_N = np.zeros_like(xyz)
    p_MPa = case["roof"]["inlet_MPa"]
    decay_mm_inv = case["decay_mm_inv"]
    punch_mm = case["punch_x_mm"]
    dz_mm = g.inner_z_mm-g.inner_R_mm
    length_fraction = 1.
    if entry_mm > punch_mm:
        end_decay = np.exp(-decay_mm_inv*(GATE_MM-punch_mm))
        length_fraction = (np.exp(-decay_mm_inv*(entry_mm-punch_mm))-end_decay)/(1.-end_decay)
    for axis, location_mm, width_mm, target_N in (
        (1,g.inner_y_mm,dz_mm,case["each_side_normal_force_N"]),
        (2,g.inner_z_mm,g.seat_half_mm,case["roof"]["normal_force_N"]),
    ):
        for sign in (-1,1):
            face = triangles[np.max(np.abs(xyz[triangles,axis]-sign*location_mm),axis=1)<1e-6]
            face = face[np.max(np.abs(xyz[face,3-axis]),axis=1)<=width_mm+1e-6]
            forces = np.zeros(len(xyz))
            for t in face:
                for shape, pt, A_mm2 in quad(xyz[t]):
                    x,y,_ = pt
                    if x < punch_mm:
                        continue
                    distribution = float(skew_weight(y,eccentricity_mm,g.seat_half_mm)) if axis==2 else 1.
                    forces[t] += shape * p_MPa*np.exp(-decay_mm_inv*(x-punch_mm))*distribution*abs(A_mm2[axis])
            if forces.sum() <= 0:
                raise ValueError("No active load faces")
            # Adjust top and floor to the prescribed first moment by a smooth
            # weighting of the quadrature result. Verify correction is small.
            if axis==2:
                basis=np.column_stack([np.ones(len(xyz)),xyz[:,1]/g.seat_half_mm])
                applied = (basis.T * forces) @ basis
                desired = forces.sum()*np.array([1.,eccentricity_mm/g.seat_half_mm])
                multiplier = basis @ np.linalg.solve(applied,desired)
                if np.max(abs(multiplier[forces != 0]-1.)) > .035:
                    raise ValueError("Unacceptable quadrature error in pressure centroid")
                forces *= multiplier
            forces *= length_fraction * target_N / forces.sum()
            F_N[:,axis] += sign*forces
            F_N[:,0] += case["mu"]*forces
    return F_N


def compact_sections(xyz,tets,stress,g,case,eccentricity_mm):
    """Integrate nodal stress across the two side cuts and the upper midcut."""
    normal_nodes,weights = np.polynomial.legendre.leggauss(10)
    xlo,xhi=230.,270.
    X_gauges = (xhi+xlo)/2 + normal_nodes*(xhi-xlo)/2
    hand_g = section_grid(g,41)
    s = frame(g,1.,0.,eccentricity_mm,41)
    inside,n,t,_,h_mm,centre,*_ = hand_g
    report = []
    integral_MPa_mm = case["roof"]["inlet_MPa"] / case["decay_mm_inv"] * (
        np.exp(-case["decay_mm_inv"]*(xlo-case["punch_x_mm"]))
        - np.exp(-case["decay_mm_inv"]*(xhi-case["punch_x_mm"])))
    for q,target in enumerate(((g.inner_y_mm,0.),(-g.inner_y_mm,0.),(0.,g.inner_z_mm))):
        idx = int(np.argmin(np.linalg.norm(inside-target,axis=1)))
        points = [[x,*yz] for x in X_gauges
                  for yz in centre[idx]+(h_mm[idx]/2*normal_nodes)[:,None]*n[idx]]
        ip = interpolation(xyz,tets,points)
        data = np.array([w @ stress[ids] for ids,w in ip])
        if q == 2:
            normal_MPa = data[:,1]
            shear_MPa = -data[:,4]
        else:
            normal_MPa = data[:,2]
            shear_MPa = data[:,4]
        dA = (xhi-xlo)/2*h_mm[idx]/2*np.outer(weights,weights)
        vm = float(np.sum(normal_MPa.reshape(10,10)*dA))
        sm = float(np.sum(shear_MPa.reshape(10,10)*dA))
        mm = float(np.sum(normal_MPa.reshape(10,10)*dA*normal_nodes*h_mm[idx]/2))
        hand_N,hand_M_Nmm,hand_V_N = [s[k][idx]*integral_MPa_mm
                                      for k in ("normal_N_per_mm","moment_Nmm_per_mm","shear_N_per_mm")]
        report.append(dict(aperture_yz_mm=list(target),X_mm=[xlo,xhi],FEA_N=vm,hand_N=hand_N,
                           FEA_shear_N=sm,hand_shear_N=hand_V_N,
                           FEA_moment_Nmm=mm,hand_moment_Nmm=hand_M_Nmm,
                           normal_error_fraction=abs(vm-hand_N)/abs(hand_N),
                           moment_error_fraction=abs(mm-hand_M_Nmm)/abs(hand_M_Nmm)))
    return report


def screen(g,size_mm, labels, bars, optimize=1):
    cases = {name:janssen(main_cylinder_force_N(315),K,mu,length) for name,K,mu,length in (
        ("roof_force",.6,.2,89.4),("roof_friction",.6,.3,89.4),
        ("gate_end",.6,.2,40./1.23),("gate_friction",.6,.3,40./1.23))}
    gmesh = rectangle_geometry(g,size_mm,optimize)
    with TemporaryDirectory(prefix="ring-",dir=HERE) as tmp:
        work = Path(tmp)
        xyz,tets,active,faces = mesh(work,gmesh)
        quality = jacobian_statistics(xyz,tets)
        if quality["nonpositive_element_count"]:
            raise ValueError(quality)
        fixed_axial = active[np.isclose(xyz[active,0],BEARING_X_MM,atol=1e-7)]
        # All bearing faces resist X. Two transverse rotations/translations
        # are removed at the fixed end of the rails.
        def nearest(at):
            return int(fixed_axial[np.argmin(np.linalg.norm(xyz[fixed_axial]-at,axis=1))])
        a,b=(nearest((BEARING_X_MM,side*185.,0.)) for side in (-1,1))
        fixed={1:fixed_axial,2:[a],3:[a,b]}
        forces=[branch_weights(xyz,faces,g,cases[l],ECCENTRICITY_MM) for l in labels]
        deck(work,xyz,tets,active,fixed,forces,bars)
        tool("ccx.exe",["-i","roof"],work,"Job finished")
        fields = frd_fields(work/"roof.frd",len(xyz))
        rf = reactions(work/"roof.dat")
        assert len(fields)==len(rf)==len(labels)*len(bars)
    coords=xyz[active]
    off_end=active[(coords[:,0]>=230.)&(coords[:,0]<=270.)]
    end=active[(coords[:,0]>270.)&(coords[:,0]<=GATE_MM)]
    inlet=active[(coords[:,0]<230.)]
    gauge=[(x,y,u*g.inner_z_mm) for x in (211.,232.,250.,268.,283.,293.)
           for y in (-54.,0.,54.) for u in (-1,1)]
    gauges=interpolation(xyz,tets,gauge)
    rows={}
    for n,label in enumerate(labels):
        record=fields[n*len(bars):(n+1)*len(bars)]
        pressure_proof=record[bars.index(315)]["STRESS"]
        cyc=record[bars.index(300)]["STRESS"]
        start=record[bars.index(0)]["STRESS"]
        grad=normal_gradient(xyz,tets,faces,cyc-start)
        checks=margins(pressure_proof,start,cyc,g.grade,grad)
        sections={}
        for region,pool in (("mid",off_end),("end",end),("inlet",inlet)):
            key=int(pool[np.argmin(checks["FKM"][pool])])
            sections[region]=dict(FKM=float(checks["FKM"][key]),static=float(checks["static"][pool].min()),
                                  FKM_no_gradient=float(checks["FKM_no_notch_credit"][key]),
                                  controlling_xyz_mm=xyz[key].tolist())
        u=record[bars.index(300)]["DISP"]
        vertical=np.array([w @ u[ids,2] for ids,w in gauges]).reshape(-1,2)
        balances=[]
        for i,bar in enumerate(bars):
            actual=rf[n*len(bars)+i]
            demand=forces[n].sum(axis=0)*bar/315
            balances.append(float(np.linalg.norm(actual+demand)/max(1.,np.linalg.norm(demand))))
        rows[label]=dict(load=cases[label],section_margins=sections,
            opening_backing_300_mm=float((vertical[:,1]-vertical[:,0]).max()),
            force_balance_fraction=balances,
            integrated_sections_315=compact_sections(xyz,tets,pressure_proof,g,cases[label],ECCENTRICITY_MM)
                                    if label=="roof_force" else [])
    return dict(size_mm=size_mm,elements=len(tets),nodes=len(active),jacobians=quality,
                analysis_status="diagnostic_condensed_liner_and_seam",
                high_order_optimizer=optimize,
                pressure_steps_bar=list(bars),cases=rows)


if __name__=="__main__":
    p=ArgumentParser()
    p.add_argument("--mesh",type=float,nargs="+",required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--cases",nargs="+",default=["roof_force","roof_friction","gate_end","gate_friction"])
    p.add_argument("--optimise", type=int, default=1)
    p.add_argument("--append", action="store_true")
    args=p.parse_args()
    results=json.loads(args.out.read_text(encoding="utf-8")) if args.append else []
    for m in args.mesh:
        results.append(screen(GEOMETRY,m,args.cases,PRESSURES_BAR,args.optimise))
        args.out.write_text(json.dumps(results,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        print(m,[(k,v["section_margins"]) for k,v in results[-1]["cases"].items()],flush=True)

