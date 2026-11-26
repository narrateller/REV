"""Nonlinear closed-gate model, with travelling shoe and short fixed rails."""
import argparse
from dataclasses import dataclass
from itertools import product
from math import ceil, sqrt
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from frame_analytic import CYCLIC_N, DISCHARGE_BAY_mm, ECC_mm, E_MPa, NU, RHO_kg_mm3, STATIC_N, T12B
from frame_fea import BIN, FEA, fkm_parameters, mises, results_frd, run_tool, stress_tensors, write_json

PLATE_mm = 38.
SHOE_mm = 158.
HEIGHT_mm = 76.
OPEN_mm = T12B["gate"]["gate_opening_travel_mm"]
RAIL_mm = DISCHARGE_BAY_mm - SHOE_mm
FRICTION = .15
PENALTY_MPa_mm = 50000.
EASE_mm = 5.
EASE_DEPTH_mm = .20
RP_RM_MPa = {"plate": (800., 1000.), "shoe": (700., 900.), "left": (800., 1000.), "right": (800., 1000.)}


def screening():
    span_mm = 176. + 82.
    moment_Nmm = STATIC_N * (2 * span_mm - 150.) / 8
    bare_bend_MPa = 6 * moment_Nmm / (180. * PLATE_mm**2)
    shoe_mass_kg = 340. * HEIGHT_mm * SHOE_mm * RHO_kg_mm3
    removed_kg = 2 * 82. * 180. * SHOE_mm * RHO_kg_mm3
    forward_plane_mm = T12B["axis_A"]["gate_outer_x_mm"]
    return {
        "clear_span_mm": 176., "span_between_pad_centres_mm": span_mm, "bend_moment_Nmm": moment_Nmm,
        "bare_plate_bending_MPa": bare_bend_MPa, "bare_plate_static_factor_upper_bound": 800. / bare_bend_MPa,
        "bare_plate_equivalent_shear_MPa": sqrt(3)*1.5*STATIC_N/(2*180.*PLATE_mm),
        "shoe_beam_bending_MPa": 6*moment_Nmm/(HEIGHT_mm*SHOE_mm**2),
        "shoe_beam_equivalent_shear_MPa": sqrt(3)*1.5*STATIC_N/(2*HEIGHT_mm*SHOE_mm),
        "moving_shoe_envelope_mass_kg": shoe_mass_kg, "moving_attachments_allowance_kg": 3.,
        "fixed_rails_pair_kg": 2*82.*180.*RAIL_mm*RHO_kg_mm3, "original_rails_replaced_mass_kg": removed_kg,
        "net_mass_change_kg": shoe_mass_kg + 3. - removed_kg,
        "shoe_axial_interval_from_punch_home_mm": [forward_plane_mm, forward_plane_mm+SHOE_mm],
        "fixed_rails_axial_length_mm": RAIL_mm, "open_shoe_minimum_height_from_axis_mm": OPEN_mm-HEIGHT_mm/2,
        "vertical_reserve_above_relaxed_briquette_envelope_mm": OPEN_mm-HEIGHT_mm/2-31.,
        "working_gate_travel_mm": OPEN_mm, "installed_gate_travel_mm": 80.,
    }


@dataclass
class Body:
    name: str
    ids: np.ndarray
    xyz: np.ndarray
    elements: np.ndarray


def grid(points_mm, h_mm):
    return np.concatenate([
        np.linspace(a, b, ceil((b-a)/h_mm), endpoint=False)
        for a, b in zip(points_mm, points_mm[1:])
    ] + [[points_mm[-1]]])


def ease(distance_mm):
    return EASE_DEPTH_mm * np.maximum(0., 1.-distance_mm/EASE_mm)**2


def model(h_mm):
    mid_mm, end_mm = PLATE_mm+SHOE_mm, PLATE_mm+DISCHARGE_BAY_mm
    plate_y = (-38., -30., 0., 30., 38.)
    rail_y = (-90., -38., -33., 0., 33., 38., 90.)
    specs = (
        ("plate", ((-95., -75., 0., 75., 95.), plate_y, (0., PLATE_mm)), None),
        ("shoe", ((-170., -88., -75., 0., 75., 88., 170.), plate_y, (PLATE_mm, mid_mm)),
         lambda x,y: ease(95.-np.abs(x))+ease(38.-np.abs(y))),
        ("left", ((-170., -165., -93., -88.), rail_y, (mid_mm, end_mm)),
         lambda x,y: ease(np.minimum(x+170., -88.-x))+ease(38.-np.abs(y))),
        ("right", ((88., 93., 165., 170.), rail_y, (mid_mm, end_mm)),
         lambda x,y: ease(np.minimum(x-88., 170.-x))+ease(38.-np.abs(y))),
    )
    bodies = []
    for name, axes, rel in specs:
        x, y, z = (grid(values, h_mm) for values in axes)
        xyz = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1)
        if rel:
            front = xyz[:, :, 0, :]
            # Easing applies only in the bearing width. Outside it the gap stays finite.
            dx = rel(front[:, :, 0], np.clip(front[:, :, 1], -38., 38.))
            xyz[:, :, :, 2] += dx[:, :, None] * ((z[-1]-z)/(z[-1]-z[0]))[None, None, :]
        shape = xyz.shape[:3]
        ns = 1+sum(v.ids.size for v in bodies)
        es = 1+sum(v.elements.size for v in bodies)
        elements = np.arange(es, es+(len(x)-1)*(len(y)-1)*(len(z)-1)).reshape(np.array(shape)-1)
        bodies.append(Body(name, np.arange(ns, ns+np.prod(shape)).reshape(shape), xyz, elements))
    return bodies


def write_mesh(path, bodies, first_fixed=2):
    with path.open("w", encoding="ascii") as f:
        f.write("*NODE\n")
        for b in bodies:
            for tag, (x,y,z) in zip(b.ids.ravel(), b.xyz.reshape(-1,3), strict=True):
                f.write(f"{tag},{x:.10g},{y:.10g},{z:.10g}\n")
        for b in bodies:
            f.write(f"*ELEMENT,TYPE=C3D8I,ELSET={b.name}\n")
            nx, ny, nz = b.elements.shape
            conn = np.stack([b.ids[i:i+nx,j:j+ny,k:k+nz] for i,j,k in
                             ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))], axis=-1)
            for tag, nodes in zip(b.elements.ravel(), conn.reshape(-1,8), strict=True):
                f.write(f"{tag},"+",".join(map(str,nodes))+"\n")
            for layer, side, end in ((0,1,"front"),(-1,2,"back")):
                f.write(f"*SURFACE,TYPE=ELEMENT,NAME={b.name}_{end}\n")
                for tag in b.elements[:,:,layer].ravel():
                    f.write(f"{tag},S{side}\n")
        f.write("*NSET,NSET=FIXED\n")
        for b in bodies[first_fixed:]:
            tags = b.ids[:,:,-1].ravel()
            for i in range(0,len(tags),12):
                f.write(",".join(map(str,tags[i:i+12]))+"\n")


def pressure_weights(plate, eccentricity_mm):
    weights = np.zeros(plate.ids.size+1)
    ax, ay = np.array(eccentricity_mm)*12/np.array([150.**2,60.**2])
    for i, j in product(range(plate.ids.shape[0]-1), range(plate.ids.shape[1]-1)):
        x0, y0, _ = plate.xyz[i,j,0]
        x1, y1, _ = plate.xyz[i+1,j+1,0]
        if abs(x0+x1)>150. or abs(y0+y1)>60.:
            continue
        for u,v in product((-1/sqrt(3),1/sqrt(3)),repeat=2):
            x, y = (x0+x1+u*(x1-x0))/2, (y0+y1+v*(y1-y0))/2
            w = (1+ax*x)*(1+ay*y)*(x1-x0)*(y1-y0)/16/9000
            for a,b in product((0,1),repeat=2):
                weights[plate.ids[i+a,j+b,0]] += w*(1+(2*a-1)*u)*(1+(2*b-1)*v)
    np.testing.assert_allclose(weights.sum(),1.,atol=1.e-12)
    coords = plate.xyz.reshape(-1,3)
    np.testing.assert_allclose(weights[1:] @ coords[:,:2],eccentricity_mm,atol=1.e-12)
    return weights


def deck(bodies, force_N, eccentricity_mm):
    lines = ["*HEADING","T-1.7b | contact | N, mm, MPa","*INCLUDE,INPUT=gate_mesh.inp",
             "*MATERIAL,NAME=STEEL","*ELASTIC",f"{E_MPa},{NU}"]
    lines.extend(f"*SOLID SECTION,ELSET={b.name},MATERIAL=STEEL" for b in bodies)
    lines += ["*SURFACE INTERACTION,NAME=OILED_STEEL","*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR",
              f"{PENALTY_MPa_mm},1.","*FRICTION",f"{FRICTION},10000."]
    for slave, master in (("plate_back","shoe_front"),("left_front","shoe_back"),("right_front","shoe_back")):
        lines += ["*CONTACT PAIR,INTERACTION=OILED_STEEL,TYPE=SURFACE TO SURFACE",f"{slave},{master}"]
    lines += ["*BOUNDARY","FIXED,1,3"]
    for b in bodies[:2]:
        i,j = np.array(b.ids.shape[:2])//2
        lines += [f"{b.ids[i,j,0]},1,2",f"{b.ids[-1,j,0]},2,2"]
    lines += ["*STEP,NLGEOM,INC=160","*STATIC",".1,1.,1.e-7,.2","*CLOAD"]
    w = pressure_weights(bodies[0],eccentricity_mm)
    lines.extend(f"{tag},3,{force_N*w[tag]:.12g}" for tag in np.flatnonzero(w))
    lines += ["*NODE FILE","U,RF","*EL FILE","S","*CONTACT FILE","CDIS,CSTR","*END STEP"]
    return "\n".join(lines)+"\n"


def body_summary(b, static, fatigue):
    ids = b.ids.ravel()
    vm = mises(static["STRESS"][ids])
    delta = fatigue["STRESS"][ids]
    fatigue_vm = mises(delta)
    principal_mean = np.maximum(0., np.linalg.eigvalsh(stress_tensors(delta))[:,2]/2)
    rp,rm = RP_RM_MPa[b.name]
    strength,kR,_,slope = fkm_parameters(rm,6.3,False,forging=True)
    utilisation = (fatigue_vm/2+slope*principal_mean)/strength
    xyz = b.xyz.reshape(-1,3)
    i,j = np.argmax(vm),np.argmax(utilisation)
    return dict(static_mises_MPa=float(vm[i]),static_factor=float(rp/vm[i]),static_xyz_mm=xyz[i].tolist(),
                fatigue_factor=float(1/utilisation[j]),fatigue_range_MPa=float(fatigue_vm[j]),
                fatigue_xyz_mm=xyz[j].tolist(),fatigue_positive_mean_MPa=float(principal_mean[j]),
                n_sigma_lower_bound=1.,k_R=kR,design_fully_reversed_MPa=strength)


def solve(level):
    h_mm = (12.,9.,6.,4.5,3.5,2.75)[level]
    bodies = model(h_mm)
    count = 1+sum(b.ids.size for b in bodies)
    case = f"gate_contact_{level}"
    probes = {}
    with TemporaryDirectory(prefix=case+"_",dir=FEA.parent, ignore_cleanup_errors=True) as tmp:
        folder = Path(tmp)
        write_mesh(folder/"gate_mesh.inp",bodies)
        for name,force_N in (("static",STATIC_N),("fatigue",CYCLIC_N)):
            inp = folder/f"{case}_{name}.inp"
            inp.write_text(deck(bodies,force_N,(ECC_mm,ECC_mm)),encoding="ascii")
            run_tool([BIN/"ccx.exe","-i",inp.stem],folder,marker="Job finished")
            result = results_frd(inp.with_suffix(".frd"),count)
            reactions = [float(result["FORC"][b.ids[:,:,-1],2].sum()) for b in bodies[2:]]
            if not np.isclose(sum(reactions),-force_N,rtol=.002):
                raise ValueError(f"{name} load {force_N}, axial reactions {reactions}")
            result["reactions_N"] = reactions
            probes[name] = result
            (FEA/inp.name).write_bytes(inp.read_bytes())
    static,fatigue = probes["static"],probes["fatigue"]
    p = bodies[0]
    face = p.ids[:,:,0]
    fits = np.column_stack((p.xyz[:,:,0,:2].reshape(-1,2),np.ones(face.size)))
    tilt = np.linalg.lstsq(fits,static["DISP"][face.ravel(),2],rcond=None)[0][:2]
    out = dict(h_mm=h_mm,nodes=count-1,elements=sum(int(b.elements.size) for b in bodies),
               plate_face_deflection_static_mm=float(static["DISP"][face,2].max()),
               plate_face_deflection_fatigue_mm=float(fatigue["DISP"][face,2].max()),
               maximum_transverse_displacement_mm=float(np.linalg.norm(static["DISP"][face,:2],axis=-1).max()),
               fitted_plate_tilt_rad_xy=tilt.tolist(),static_seat_reactions_N=static["reactions_N"],
               fatigue_seat_reactions_N=fatigue["reactions_N"],eccentricity_xy_mm=[ECC_mm,ECC_mm],
               friction=FRICTION,penalty_MPa_mm=PENALTY_MPa_mm,
               components={b.name:body_summary(b,static,fatigue) for b in bodies})
    write_json(FEA/f"{case}.json",out)
    for name,c in out["components"].items():
        print(case,name,c["static_factor"],c["fatigue_factor"],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("levels",nargs="+",type=int)
    for level in parser.parse_args().levels:
        solve(level)

