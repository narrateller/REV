"""One-piece plate and backing shoe. The 38 mm face occupies the T-1.2b slot."""
import argparse
from itertools import product
from tempfile import TemporaryDirectory
from pathlib import Path

import numpy as np
from scipy.interpolate import LinearNDInterpolator

import gate_contact as gc
from frame_fea import BIN, FEA, run_tool, write_json
from frame_analytic import CYCLIC_N, ECC_mm, RHO_kg_mm3, STATIC_N

FRONT_PLATE_HALF_WIDTH_mm = 85.
SHOULDER_RUNOUT_mm = 30.


def model(h_mm, profile="flat"):
    old = gc.model(h_mm)
    x = gc.grid((-170.,-88.,-85.,-75.,0.,75.,85.,88.,170.), h_mm)
    y = gc.grid((-38.,-30.,0.,30.,38.), h_mm)
    z = gc.grid((0.,gc.PLATE_mm,gc.PLATE_mm+gc.SHOE_mm),h_mm)
    xyz = np.stack(np.meshgrid(x,y,z,indexing="ij"),axis=-1)
    t = np.clip((abs(x)-FRONT_PLATE_HALF_WIDTH_mm)/SHOULDER_RUNOUT_mm,0.,1.)
    front = gc.PLATE_mm*t**2*(3.-2.*t)
    xyz[:,:,:,2] += front[:,None,None]*((z[-1]-z)/z[-1])[None,None,:]
    ids = np.arange(1,1+np.prod(xyz.shape[:3])).reshape(xyz.shape[:3])
    shape = np.array(ids.shape)-1
    elems = np.arange(1,1+np.prod(shape)).reshape(shape)
    items = [gc.Body("blade",ids,xyz,elems)]
    for body in old[2:]:
        xyz_rail = body.xyz.copy()
        if profile=="slope":
            # Start from the outboard seating land. The inboard side is relieved
            # to follow the rotation of a bridge with a central pressure patch.
            inboard_mm = np.maximum(0.,146.-abs(xyz_rail[:,:,0,0]))
            xyz_rail[:,:,:,2] += .0034*inboard_mm[:,:,None]*np.linspace(1.,0.,xyz_rail.shape[2])[None,None,:]
        ns = 1+sum(v.ids.size for v in items)
        es = 1+sum(v.elements.size for v in items)
        items.append(gc.Body(body.name,body.ids-body.ids.min()+ns,xyz_rail,body.elements-body.elements.min()+es))
    return items


def guide_equations(blade):
    """Constrain only mean lateral motion on each guide footprint."""
    i = blade.ids.shape[0]//2
    sets = ((1, blade.ids[i,1:-1,1:-1]),
            (2, blade.ids[0,1:-1,1:-1]),
            (2, blade.ids[-1,1:-1,1:-1]))
    lines = []
    for dof,nodes in sets:
        tags = nodes.ravel().tolist()
        lines += ["*EQUATION",str(len(tags))]
        terms = [f"{tag},{dof},{1/len(tags):.12g}" for tag in tags]
        lines.extend(",".join(terms[i:i+3]) for i in range(0,len(terms),3))
    return lines


def deck(bodies, force_N, eccentricity_mm, guide, friction=gc.FRICTION):
    blade = bodies[0]
    lines = ["*HEADING","T-1.7b | integral sliding backup | N, mm, MPa","*INCLUDE,INPUT=gate_mesh.inp",
             "*MATERIAL,NAME=STEEL","*ELASTIC","210000.,.3"]
    lines.extend(f"*SOLID SECTION,ELSET={body.name},MATERIAL=STEEL" for body in bodies)
    lines += ["*SURFACE INTERACTION,NAME=OILED_STEEL","*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR",
              f"{gc.PENALTY_MPa_mm},1.","*FRICTION",f"{friction},10000."]
    for rail in bodies[1:]:
        lines += ["*CONTACT PAIR,INTERACTION=OILED_STEEL,TYPE=SURFACE TO SURFACE",f"{rail.name}_front,blade_back"]
    lines += ["*BOUNDARY","FIXED,1,3"]
    if guide=="average":
        lines += guide_equations(blade)
    else:
        j = blade.ids.shape[1]//2
        lines += [f"{blade.ids[0,j,0]},1,2",f"{blade.ids[-1,j,0]},2,2"]
    lines += ["*STEP,NLGEOM,INC=120","*STATIC",".25,1.,1.e-6,.5","*CLOAD"]
    w = gc.pressure_weights(blade,eccentricity_mm)
    lines.extend(f"{tag},3,{force_N*w[tag]:.12g}" for tag in np.flatnonzero(w))
    lines += ["*NODE FILE,FREQUENCY=999999","U,RF","*EL FILE,FREQUENCY=999999","S",
              "*CONTACT FILE,FREQUENCY=999999","CDIS,CSTR","*END STEP"]
    return "\n".join(lines)+"\n"


def write_mesh(path,bodies):
    # The parent writer expects the first two bodies to move. The fixed set for
    # this model consists of both rear pad planes.
    gc.write_mesh(path,bodies,first_fixed=1)


def load_results(path,count):
    out = gc.results_frd(path,count)
    records = []
    contact = False
    with path.open(encoding="ascii") as f:
        for line in f:
            if line.startswith(" -4"):
                contact = line.split()[1]=="CONTACT"
                if contact:
                    records.clear()
            if line.startswith(" -1") and contact:
                records.append([float(line[13+i*12:25+i*12]) for i in range(6)])
            if line.startswith(" -3"):
                contact = False
    if records:
        contact_values = np.array(records)
        out["contact"] = {"sample_count":len(records),"pressure_max_MPa":float(contact_values[:,3].max()),
                          "normal_gap_min_mm":float(contact_values[:,0].min()),
                          "normal_gap_max_mm":float(contact_values[:,0].max()),
                          "zero_pressure_samples":int(np.count_nonzero(contact_values[:,3]<=0))}
    else:
        out["contact"] = {"sample_count":0}
    return out


def pad_gap(bodies, displacements_mm):
    """Recover signed gaps on the overlapping nodal pad footprint after deformation."""
    blade = bodies[0]
    rear = (blade.xyz[:, :, -1] + displacements_mm[blade.ids[:, :, -1]]).reshape(-1, 3)
    blade_z_mm = LinearNDInterpolator(rear[:, :2], rear[:, 2])
    out = []
    for rail in bodies[1:]:
        rail_front = rail.xyz[:, :, 0] + displacements_mm[rail.ids[:, :, 0]]
        candidate = rail_front[abs(rail.xyz[:, :, 0, 1]) < gc.HEIGHT_mm/2]
        values_mm = candidate[:, 2] - blade_z_mm(candidate[:, :2])
        values_mm = values_mm[np.isfinite(values_mm)]
        out.append({"rail":rail.name,"sample_count":int(values_mm.size),
                    "opening_samples_over_0p01_mm":int(np.sum(values_mm>.01)),
                    "max_separation_mm":float(max(0.,values_mm.max()))})
    return out


def solve(level, axes="both", guide="average", profile="flat"):
    h_mm = (16.,13.,10.,8.,6.,4.5)[level]
    bodies = model(h_mm,profile)
    gc.RP_RM_MPa["blade"] = (700.,900.)
    count = 1+sum(b.ids.size for b in bodies)
    eccentricity_mm = {"centered":(0.,0.),"both":(ECC_mm,ECC_mm),"x":(ECC_mm,0.),"y":(0.,ECC_mm)}[axes]
    stem = f"gate_integral_{guide}_{axes}_{level}" if profile=="flat" else f"gate_integral_slope_{guide}_{axes}_{level}"
    with TemporaryDirectory(prefix=stem+"_",dir=FEA.parent, ignore_cleanup_errors=True) as tmp:
        folder = Path(tmp)
        write_mesh(folder/"gate_mesh.inp",bodies)
        probes = []
        for name, force_N in (("static",STATIC_N),("fatigue",CYCLIC_N)):
            inp = folder/f"{stem}_{name}.inp"
            inp.write_text(deck(bodies,force_N,eccentricity_mm,guide),encoding="ascii")
            run_tool([BIN/"ccx.exe","-i",inp.stem],folder,marker="Job finished")
            result = load_results(inp.with_suffix(".frd"),count)
            reactions = [float(result["FORC"][b.ids[:,:,-1],2].sum()) for b in bodies[1:]]
            if not np.isclose(sum(reactions),-force_N,rtol=.003):
                raise ValueError(f"{name} load {force_N}, axial reactions {reactions}")
            result["reactions_N"] = reactions
            probes.append(result)
            if level in (1,2,3):
                (FEA/inp.name).write_bytes(inp.read_bytes())
    stat,fat = probes
    blade = bodies[0]
    plane = blade.xyz[:,:,0]
    face = abs(plane[:,:,0])<=75.
    face &= abs(plane[:,:,1])<=30.
    ids = blade.ids[:,:,0][face]
    fit = np.column_stack((plane[face,:2],np.ones(len(ids))))
    tilt_rad = np.linalg.lstsq(fit,stat["DISP"][ids,2],rcond=None)[0][:2]
    # A conservative bound for the translation of the gate center relative to its seat.
    shift = float(np.linalg.norm(stat["DISP"][ids,:2],axis=-1).max())
    out = dict(h_mm=h_mm,nodes=count-1,elements=sum(int(b.elements.size) for b in bodies),
               face_profile=profile,guide_model=guide,eccentricity_xy_mm=list(eccentricity_mm),friction=gc.FRICTION,penalty_MPa_mm=gc.PENALTY_MPa_mm,
               static_seat_reactions_N=stat["reactions_N"],fatigue_seat_reactions_N=fat["reactions_N"],
               static_contact=stat["contact"],fatigue_contact=fat["contact"],
               loaded_shoe_rail_gap_samples=pad_gap(bodies,stat["DISP"]),
               plate_face_deflection_static_mm=float(stat["DISP"][ids,2].max()),
               plate_face_deflection_fatigue_mm=float(fat["DISP"][ids,2].max()),
               static_contact_face_mean_axial_mm=float(stat["DISP"][ids,2].mean()),
               fitted_plate_tilt_rad_xy=tilt_rad.tolist(),max_face_transverse_displacement_mm=shift,
               components={b.name:gc.body_summary(b,stat,fat) for b in bodies})
    write_json(FEA/f"{stem}.json",out)
    print(stem,[(k,v["static_factor"],v["fatigue_factor"]) for k,v in out["components"].items()],flush=True)


def mass():
    # Integral axial shoulder on both sides has mean height of half of 38 mm.
    part_volume_mm3 = gc.HEIGHT_mm * (340.*gc.SHOE_mm
        + (2.*FRONT_PLATE_HALF_WIDTH_mm+SHOULDER_RUNOUT_mm)*gc.PLATE_mm)
    core_reference_mm3 = 220.*150.*gc.PLATE_mm
    # Carry the inherited guides and actuator connection; new clevis offset budget.
    part_delta_kg = (part_volume_mm3-core_reference_mm3)*RHO_kg_mm3+3.
    return {"part_mass_kg":part_volume_mm3*RHO_kg_mm3,"moving_mass_delta_kg":part_delta_kg,
            "rail_pair_mass_kg":gc.screening()["fixed_rails_pair_kg"],
            "complete_gate_and_rails_delta_kg":part_delta_kg-gc.screening()["original_rails_replaced_mass_kg"],
            "closed_face_nominal_thickness_mm":gc.PLATE_mm,"integral_central_axial_thickness_mm":gc.PLATE_mm+gc.SHOE_mm,
            "integral_transverse_width_mm":340.,"integral_height_mm":gc.HEIGHT_mm,"transition_width_mm":SHOULDER_RUNOUT_mm,
            "opening_reserve_mm":gc.OPEN_mm-gc.HEIGHT_mm/2-31.}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("levels",nargs="+",type=int)
    parser.add_argument("--profile",choices=("flat","slope"),default="flat")
    parser.add_argument("--guide",choices=("average","point"),default="average")
    parser.add_argument("--axes",choices=("both","x","y","centered"),default="both")
    args = parser.parse_args()
    for i in args.levels:
        solve(i,args.axes,args.guide,args.profile)

