"""C3D10 window/shoe model with explicit cheek and reduced key flexibility."""

from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

import numpy as np
from scipy.sparse import coo_array
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from hand import E_MPa, G_MPa, CAST, FORGED
from prior.hand import extrema
from layout import (EDGE_R_MM, KEY_CLOSED_Y_MM, LOCK_LOWER_Y_MM, LOCK_UPPER_Y_MM, SEAT_ALLOWANCE_MM,
                    SHOE_ABS_Y_MAX_MM, STATIONS, WEAR_LAND_DEPTH_MM)
from layout import Layout
from loads import PRESSURES_BAR, PROOF_SKEW_X_MM, transition_cases
from solver import deck, frd_fields, interpolation, jacobian_statistics, mesh, mises, quad, reactions, tool
from fkm import margins, normal_gradient

import window_geometry

SHEAR_FACTOR = 5/6
FORGED_SHOE = FORGED

def centre(interval_mm):
    return sum(interval_mm)/2


def plane_faces(xyz, faces, axis, plane_mm):
    return faces[np.max(np.abs(xyz[faces,axis]-plane_mm),axis=1) < 1.e-5]


def patch(xyz, faces, law, targets=None):
    result = np.zeros(len(xyz))
    for face in faces:
        coordinates = xyz[face]
        for shape, point, vec in quad(coordinates):
            value = max(0., law(*point))
            if value:
                result[face] += np.linalg.norm(vec) * value * shape
    scale = result.sum()
    if scale <= 0:
        raise ValueError("No active face for patch")
    weights = result / scale
    active = np.flatnonzero(abs(weights)>1e-10)
    if targets is not None:
        # Enforce the analytical centroid even where element edges intersect a strip.
        basis = np.column_stack([np.ones(len(active)),
                                 (xyz[active,0]-targets[0])/100., (xyz[active,1]-targets[1])/100.])
        if np.linalg.matrix_rank(basis)==3:
            positive = np.abs(weights[active])
            desired = np.array([1.,0.,0.]) - weights[active] @ basis
            weights[active] += positive * (basis @ np.linalg.solve(basis.T @ (positive[:,None]*basis),desired))
    return weights


def positive_box(xyz, faces, x_range, y_signed_range):
    x0,x1 = x_range
    y0,y1 = y_signed_range
    return patch(xyz,faces,lambda x,y,z: float(x0<x<x1 and y0<y<y1), (centre(x_range),centre(y_signed_range)))


def dict_weights(values):
    return {int(idx):float(values[idx]) for idx in np.flatnonzero(abs(values)>1e-10)}


def patch_connections(xyz, cast_faces, shoe_faces, seat_z_mm, reverse):
    return_rows = []
    for name,s in STATIONS.items():
        x_mm, width_mm, depth_mm = (s[k] for k in ("x_mm","key_width_mm","key_depth_mm"))
        net_x_mm = width_mm-2*EDGE_R_MM
        x_bounds = (x_mm-net_x_mm/2,x_mm+net_x_mm/2)
        y0,y1 = (KEY_CLOSED_Y_MM[0]+EDGE_R_MM,SHOE_ABS_Y_MAX_MM-EDGE_R_MM)
        for sign in (-1,1):
            at_heel = (name,sign) in reverse
            source_front = plane_faces(xyz,shoe_faces,2,30. if at_heel else seat_z_mm)
            ys = lambda a,b: tuple(sorted((sign*a,sign*b)))
            if at_heel:
                # Rear heel lies below the shoe, away from the moving width.
                source = positive_box(xyz,source_front,x_bounds,ys(107.,126.))
                heel = plane_faces(xyz,cast_faces,2,29.98)
                target = positive_box(xyz,heel,x_bounds,ys(107.,126.))
                k_N_mm = E_MPa * net_x_mm * 19. / 60.
            else:
                source = positive_box(xyz,source_front,x_bounds,ys(y0,y1))
                cap = plane_faces(xyz,cast_faces,2,seat_z_mm+depth_mm+WEAR_LAND_DEPTH_MM)
                toe = plane_faces(xyz,cast_faces,2,seat_z_mm-WEAR_LAND_DEPTH_MM)
                cap_weights = positive_box(xyz,cap,x_bounds,ys(LOCK_UPPER_Y_MM[0]+5.,LOCK_UPPER_Y_MM[1]-5.))
                toe_weights = positive_box(xyz,toe,x_bounds,ys(LOCK_LOWER_Y_MM[0]+5.,LOCK_LOWER_Y_MM[1]-5.))
                overhang_mm = centre(LOCK_UPPER_Y_MM)-centre((y0,y1))
                span_mm = centre(LOCK_LOWER_Y_MM)-centre(LOCK_UPPER_Y_MM)
                toe_share = overhang_mm/span_mm
                cap_share = 1. + toe_share
                target = cap_share*cap_weights-toe_share*toe_weights
                I_mm4 = net_x_mm*depth_mm**3/12
                A_mm2 = net_x_mm*depth_mm
                compliance = overhang_mm**2*(overhang_mm+span_mm)/(3*E_MPa*I_mm4)
                compliance += (overhang_mm+toe_share**2*span_mm)/(SHEAR_FACTOR*G_MPa*A_mm2)
                for share,width in ((cap_share,LOCK_UPPER_Y_MM[1]-LOCK_UPPER_Y_MM[0]-10.),
                                    (toe_share,LOCK_LOWER_Y_MM[1]-LOCK_LOWER_Y_MM[0]-10.)):
                    compliance += share**2*WEAR_LAND_DEPTH_MM/(E_MPa*net_x_mm*width)
                k_N_mm = 1. / compliance
            return_rows.append((dict_weights(source),dict_weights(target),3,k_N_mm))
    return return_rows


def window_force(xyz, floor_faces, shoe_faces, case_name, t22f_case):
    top_force_N = t22f_case["shoe"]["force_N"]
    centroid_mm = t22f_case["shoe"]["centroid_x_mm"]
    xlo,xhi = t22f_case["shoe"]["interval_mm"]
    force_N = np.zeros_like(xyz)
    decay_mm_inv = (t22f_case["K"] or 0) * (t22f_case["mu"] or 0) * 420/9000
    taper_y = (SHOE_ABS_Y_MAX_MM+KEY_CLOSED_Y_MM[0])*.14
    if case_name == "proof_skew":
        centroid_mm = PROOF_SKEW_X_MM
        xlo,xhi = centroid_mm-24.,centroid_mm+24.
        decay_mm_inv = 0.
    def law(x,y,z):
        if (xlo <= x <= xhi and abs(y) < 74.8):
            end = 74.8
            start = 2*taper_y-end
            lateral = max(0.,min(1.,(y-start)/4.,(end-y)/4.))
            return float(lateral*np.exp(-decay_mm_inv*(x-xlo)))
        return 0.
    for faces,direction in ((floor_faces,-1),(shoe_faces,1)):
        force_N[:,2] += direction*top_force_N*patch(xyz,faces,law,(centroid_mm,taper_y))
    return force_N


def analysis(layout, levels_mm, out, quick=False, reinforcement=False, key_factor=1., edge_diagnostic=False):
    cases = transition_cases()
    max_shoe = max(cases,key=lambda c:c["shoe"]["force_N"])
    station_loads = extrema(cases, STATIONS["rear"]["x_mm"], STATIONS["front"]["x_mm"])
    central_replay = ("proof_skew",max_shoe,(("rear",-1),))
    front_envelope = ("front_reaction",station_loads["front"]["case"],(("rear",-1),("rear",1)))
    cases_to_run = [central_replay,front_envelope]
    bars = (300,315) if quick else PRESSURES_BAR
    output = []
    for size_mm in levels_mm:
        with TemporaryDirectory(dir=HERE,prefix="window-") as name:
            base = Path(name)
            cast_folder, shoe_folder = base/"cast",base/"shoe"
            cast_folder.mkdir()
            shoe_folder.mkdir()
            cast_xyz,cast_tets,cast_ids,cast_faces = mesh(cast_folder,window_geometry.cast(layout,size_mm,reinforcement))
            shoe_xyz,shoe_tets,shoe_ids,shoe_faces = mesh(shoe_folder,window_geometry.shoe(layout,size_mm))
            for name,coords,part,ids in (("cast",cast_xyz,cast_tets,cast_ids),("shoe",shoe_xyz,shoe_tets,shoe_ids)):
                a=np.repeat(part[:,0],9)
                b=part[:,1:].ravel()
                adjacency=coo_array((np.ones(len(a)),(a,b)),shape=(len(coords),len(coords))).tocsr()
                _,groups=connected_components(adjacency,directed=False)
                sizes=np.unique(groups[ids],return_counts=True)[1]
                if len(sizes)!=1:
                    raise ValueError(f"{name} has disconnected volumes: {sizes}")
            offset = len(cast_xyz)-1
            xyz = np.vstack([cast_xyz,shoe_xyz[1:]])
            tets = np.vstack([cast_tets,shoe_tets+offset])
            active = np.concatenate([cast_ids,shoe_ids+offset])
            shoe_faces += offset
            quality = jacobian_statistics(xyz,tets)
            if quality["nonpositive_element_count"]:
                raise ValueError(f"Nonpositive window Jacobian in solved mesh: {quality}")
            floor_faces = plane_faces(xyz,cast_faces,2,-30.)
            bottom_shoe = plane_faces(xyz,shoe_faces,2,30.)
            def near(ids,point):
                return int(ids[np.argmin(np.linalg.norm(xyz[ids]-point,axis=1))])
            # 3-2-1 seating at the two rear/forward frame guide bases, with
            # horizontal shoe-guide constraints carrying no vertical reaction.
            a,b,c = [near(cast_ids,q) for q in [(0.,-105.,-74.),(0.,105.,-74.),(195.,0.,-130.)]]
            shoe_a,shoe_b = [near(shoe_ids+offset,q) for q in [(15.,0.,67.),(193.,0.,67.)]]
            fixed = {1:[a,b,shoe_a],2:[a,shoe_a,shoe_b],3:[a,b,c]}
            points = [(x,y,z) for x in (30.,55.,110.,145.,169.,190.,200.)
                      for y in (-50.,0.,50.) for z in (-30.,30.)]
            gauges_foot = interpolation(xyz,cast_tets,points[::2])
            gauges_top = interpolation(xyz,shoe_tets+offset,points[1::2])
            region = {"cast_cheek":cast_ids[(np.abs(xyz[cast_ids,1]) > 142.) & (xyz[cast_ids,2]>-23.)],
                      "cast_floor":cast_ids[(np.abs(xyz[cast_ids,1]) < 100.) & (xyz[cast_ids,2]<-34.)],
                      "shoe":shoe_ids+offset}
            if edge_diagnostic:
                cut=xyz[cast_ids]
                region["cast_front_cut"]=cast_ids[(cut[:,0]>=200.) & (np.abs(cut[:,1])>=135.)
                                                   & (cut[:,2]>=-23.)]
            rows = {}
            for label,load,reverse in cases_to_run:
                run = base / label
                run.mkdir()
                axes = [(a,b,dof,key_factor*k) for a,b,dof,k in
                        patch_connections(xyz,cast_faces,shoe_faces,30.+layout.shoe_depth_mm,reverse)]
                force = window_force(xyz,floor_faces,bottom_shoe,label,load)
                deck(run,xyz,tets,active,fixed,[force],bars,weighted_springs=axes)
                log = tool("ccx.exe",["-i","roof"],run,"Job finished")
                try:
                    fields = frd_fields(run/"roof.frd",len(xyz))
                except ValueError as e:
                    raise ValueError(log[-4500:]) from e
                rfs = reactions(run/"roof.dat")
                if len(fields)!=len(bars) or len(rfs)!=len(bars):
                    raise ValueError(f"Incomplete window history {label}")
                states = {}
                for k,pressure_bar in enumerate(bars):
                    data = fields[k]
                    disp, stress = data["DISP"], data["STRESS"]
                    foot = np.array([w @ disp[t,2] for t,w in gauges_foot])
                    top = np.array([w @ disp[t,2] for t,w in gauges_top])
                    spring_N = [k_N_mm*(sum(disp[i,dof-1]*j for i,j in a.items())
                                          -sum(disp[i,dof-1]*j for i,j in b.items()))
                                for a,b,dof,k_N_mm in axes]
                    bands = {}
                    for group,ids in region.items():
                        subset = mises(stress[ids])
                        idx = int(ids[np.argmax(subset)])
                        bands[group] = {"VM_max_MPa":float(max(subset)),"xyz_mm":xyz[idx].tolist()}
                    states[str(pressure_bar)] = {
                        "opening_mm":float(max(top-foot)), "seating_allowance_mm":2*SEAT_ALLOWANCE_MM,
                        "opening_with_seating_mm":float(max(top-foot)+2*SEAT_ALLOWANCE_MM*pressure_bar/315.),
                        "spring_reactions_N":spring_N,
                        "force_balance_fraction":float(np.linalg.norm(rfs[k]+force.sum(axis=0)*pressure_bar/315.) /
                                                       max(1.,load["shoe"]["force_N"]*pressure_bar/315.)),
                        "regions":bands,
                    }
                proof,cyclic = fields[bars.index(315)]["STRESS"], fields[bars.index(300)]["STRESS"]
                start = fields[bars.index(0)]["STRESS"] if 0 in bars else np.zeros_like(proof)
                grade_by_region = {"cast_cheek":CAST,"cast_floor":CAST,"cast_front_cut":CAST,"shoe":FORGED_SHOE}
                gradient = normal_gradient(xyz,tets,np.vstack([cast_faces,shoe_faces]),cyclic-start)
                safety = {}
                for group, ids in region.items():
                    row = margins(proof[ids],start[ids],cyclic[ids],grade_by_region[group],gradient[ids])
                    imin = int(np.argmin(row["FKM"]))
                    safety[group] = {"static_factor":float(np.min(row["static"])),"FKM":float(row["FKM"][imin]),
                                     "FKM_no_notch_credit":float(row["FKM_no_notch_credit"][imin]),
                                     "fatigue_point_xyz_mm":xyz[ids[imin]].tolist()}
                expected_sign = [-1 if (name,side) in reverse else 1 for name in STATIONS for side in (-1,1)]
                actual_N = states["315"]["spring_reactions_N"]
                rows[label] = {"load":load,"rear_heel_sides":[side for _,side in reverse],"states":states,"safety":safety,
                               "bearing_reaction_signs_valid":all(a*b>=-1. for a,b in zip(actual_N,expected_sign))}
            def vol(t):
                c = xyz[t[:,:4]]
                return float(np.abs(np.linalg.det(c[:,1:]-c[:,:1])).sum()/6.)
            output.append({"mesh_mm":size_mm,"elements":len(tets),"nodes":len(active),
                           "body_volumes_mm3":{"open_casting":vol(cast_tets),"shoe":vol(shoe_tets+offset)},
                           "reinforcement_trial":reinforcement,"key_stiffness_multiplier":key_factor,"mesh_jacobians":quality,
                           "scope":"Window vertical load balance using explicit ring cheek and condensed keys",
                           "cases":rows})
        out.write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
                       encoding="utf-8",newline="\n")
        print(size_mm,[(label, row["states"]["300"]["opening_with_seating_mm"]) for label,row in rows.items()],
              flush=True)


if __name__ == "__main__":
    p = ArgumentParser()
    p.add_argument("--mesh", type=float,nargs="+",required=True)
    p.add_argument("--quick",action="store_true")
    p.add_argument("--reinforced",action="store_true")
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--key-factor",type=float,default=1.)
    p.add_argument("--edge-diagnostic",action="store_true")
    a = p.parse_args()
    layout = Layout("forged",128.,235.,235.)
    analysis(layout,a.mesh,a.out,a.quick,a.reinforced,a.key_factor,a.edge_diagnostic)
