"""Solid ring sensitivity with dimensional wing relief and Janssen face loading."""

from argparse import ArgumentParser
from math import acos, cos, pi, radians, sin, tan
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from hand import FORGED_BLOCK, SHORTEST_LOADED_MM, choose
from layout import Layout, ROOT_R_MM, WING_RELIEF_RUNOUT_MM, gate_relief_mm, smoothstep
from loads import GATE_X_MM, LOADED_LENGTH_MM, PRESSURES_BAR, janssen, main_cylinder_force_N
from solver import deck, frd_fields, interpolation, jacobian_statistics, mesh, mises, quad, reactions, tool
from fkm import margins, normal_gradient


def outline(half_y_mm, half_z_mm, bevel_y_mm, bevel_z_mm):
    y, z, u, v = half_y_mm, half_z_mm, bevel_y_mm, bevel_z_mm
    return [(-y+u,-z),(y-u,-z),(y,-z+v),(y,z-v),
            (y-u,z),(-y+u,z),(-y,z-v),(-y,-z+v)]


def make_geo(layout, size_mm, inner_r_mm, bevel_mm, x_mm=205., length_mm=90.):
    """OCC sketch in the YZ plane. A rounded polygon closes all tangents."""
    lines = ['SetFactory("OpenCASCADE");', 'Geometry.OCCBoundsUseStl = 1;']
    tag = 10

    def next_tag():
        nonlocal tag
        tag += 1
        return tag

    def point(yz):
        idx = next_tag()
        y,z = yz
        lines.append(f"Point({idx}) = {{{x_mm},{y:.12g},{z:.12g},{size_mm}}};")
        return idx

    def rounded(vertices, radius_mm):
        arcs = []
        for i, p in enumerate(np.array(vertices, dtype=float)):
            a = np.array(vertices[i-1]) - p
            b = np.array(vertices[(i+1) % len(vertices)]) - p
            a /= np.linalg.norm(a)
            b /= np.linalg.norm(b)
            half_angle = acos(float(a @ b)) / 2
            tangent_mm = radius_mm / tan(half_angle)
            centre = p + (a+b) * (radius_mm / (np.linalg.norm(a+b) * sin(half_angle)))
            start, mid, end = [point(q) for q in (p+a*tangent_mm, centre, p+b*tangent_mm)]
            arc = next_tag()
            lines.append(f"Circle({arc}) = {{{start},{mid},{end}}};")
            arcs.append((start, end, arc))
        curves = []
        for i, (start, end, arc) in enumerate(arcs):
            connect = next_tag()
            lines.append(f"Line({connect}) = {{{arcs[i-1][1]},{start}}};")
            curves.extend((connect, arc))
            # Four subdivisions on the working corner, six on the body fillet.
            lines.append(f"Transfinite Curve {{{arc}}} = {5 if radius_mm < 2 else 7};")
        loop = next_tag()
        curves_csv = ",".join(map(str, curves))
        lines.append(f"Curve Loop({loop}) = {{{curves_csv}}};")
        return loop

    outer_y_mm, outer_z_mm = layout.roof_width_mm / 2, 30. + layout.roof_band_mm
    vertices = outline(outer_y_mm, outer_z_mm, bevel_mm, bevel_mm) if bevel_mm else [
        (-outer_y_mm,-outer_z_mm), (outer_y_mm,-outer_z_mm), (outer_y_mm,outer_z_mm), (-outer_y_mm,outer_z_mm)]
    outer = rounded(vertices, ROOT_R_MM)
    inner_y_mm, inner_z_mm = (87., 42.) if inner_r_mm >= ROOT_R_MM else (75., 30.)
    inner = rounded([(-inner_y_mm,-inner_z_mm),(inner_y_mm,-inner_z_mm),
                     (inner_y_mm,inner_z_mm),(-inner_y_mm,inner_z_mm)], inner_r_mm)
    face = next_tag()
    lines.extend((f"Plane Surface({face}) = {{{outer},{inner}}};",
                  f"part[] = Extrude {{{length_mm},0,0}} {{ Surface{{{face}}}; }};",
                  f"Mesh.MeshSizeMin = {size_mm*.34};", f"Mesh.MeshSizeMax = {size_mm};",
                  "Mesh.MeshSizeFromCurvature = 0;", "Mesh.SecondOrderLinear = 0;",
                  "Mesh.HighOrderOptimize = 1;", "Mesh.RandomSeed = 1;"))
    return "\n".join(lines) + "\n"


def relief(xyz):
    # Smooth runout on the last 25 mm. The 150 mm working-width bore remains
    # at X=295, including the full working area of the liner.
    return np.array([gate_relief_mm(y) * smoothstep((x-GATE_X_MM+WING_RELIEF_RUNOUT_MM)
                     / WING_RELIEF_RUNOUT_MM) for x,y,z in xyz])


def aperture_faces(xyz, triangles, inner_r_mm):
    y_mm, z_mm = (87., 42.) if inner_r_mm >= ROOT_R_MM else (75., 30.)
    points = xyz[triangles]
    cavity = (np.abs(points[:,:,1]).max(axis=1) < y_mm + 1e-5) & (
             np.abs(points[:,:,2]).max(axis=1) < z_mm + 1e-5)
    return triangles[cavity & (np.ptp(points[:,:,0], axis=1) > 1e-5)]


def pressure(xyz, unwarped, faces, case, span_mm, skew, liner, inner_r_mm):
    force_N = np.zeros_like(xyz)
    start_mm = case["punch_x_mm"]
    p0_MPa = case["roof"]["inlet_MPa"]
    decay = case["decay_mm_inv"]
    # Polynomial with unit mean and the specified lateral centroid.
    eccentricity_mm = .14 * 198. if skew else 0.
    skew_a = 3 * eccentricity_mm / 75.
    skew_b = max(0., 1.5 * (skew_a - .95))
    for face in faces:
        for shape, points_mm, vec_mm2 in quad(unwarped[face]):
            x_mm,y_mm,z_mm = points_mm
            if x_mm < start_mm - 1.:
                continue
            # C1 transition over 2 mm approximates finite activation at the
            # punch face. The integrated force is restored below.
            leading = smoothstep((x_mm - start_mm + 1.) / 2.)
            p_MPa = p0_MPa * np.exp(-decay*(x_mm-start_mm)) * leading
            if vec_mm2[1] * y_mm + vec_mm2[2] * z_mm < 0:
                vec_mm2 *= -1
            location = np.clip(y_mm / 75., -1., 1.)
            if liner:
                top_mm = 42.
                side_mm = 87.
                top_flat = abs(abs(z_mm) - top_mm) < 1e-6
                side_flat = abs(abs(y_mm) - side_mm) < 1e-6
                if not (top_flat or side_flat):
                    continue
                if top_flat:
                    patch_end_mm = 87. - inner_r_mm - 1.
                    patch_start_mm = 2 * eccentricity_mm - patch_end_mm
                    lateral = min(smoothstep((y_mm-patch_start_mm)/5.),
                                  smoothstep((patch_end_mm-y_mm)/5.))
                    traction = p_MPa * lateral * abs(vec_mm2[2])
                    force_N[face] += shape[:,None] * traction * np.array([case["mu"],0.,np.sign(z_mm)])
                else:
                    taper = smoothstep((42. - inner_r_mm - abs(z_mm))/3.)
                    traction = p_MPa * taper * abs(vec_mm2[1])
                    force_N[face] += shape[:,None] * traction * np.array([case["mu"],np.sign(y_mm),0.])
                continue
            weight = 1. + skew_a*location + skew_b*(location**2 - 1/3)
            components = p_MPa * np.array([case["mu"] * np.linalg.norm(vec_mm2),
                                             vec_mm2[1], vec_mm2[2] * weight])
            force_N[face] += shape[:,None] * components
    force_N[:,0] *= case["wall_friction_N"] / force_N[:,0].sum()
    for direction, target in ((1,case["each_side_normal_force_N"]), (2,case["roof"]["normal_force_N"])):
        coord = unwarped[:,direction]
        for sign in (-1,1):
            mask = sign * coord > 0.
            force_N[mask,direction] *= sign * target / force_N[mask,direction].sum()
    return force_N


def support(xyz, active, breadth_mm, attachment, inner_r_mm):
    x,y,z = xyz.T
    active = np.isin(np.arange(len(x)), active)
    if attachment == "upstream":
        where = active & (abs(x-205.) < 1e-5) & (z < -55.) & (abs(y) > 76.) & (abs(y) < 110.)
    else:
        nose_end_mm = np.array([GATE_X_MM - gate_relief_mm(q) for q in y])
        where = active & (abs(x-nose_end_mm)<1e-5) & (abs(y)>breadth_mm/2-31.) & (
                    (abs(z)>48.) & (abs(z)<101.))
    axial = np.flatnonzero(where)
    if len(axial) < 8:
        raise ValueError("Axial shoulder fewer than 8 nodes")
    # Remove the two translations and the rigid roll without clamping whole
    # chamber planes in Y or Z. The diagnostic flange is rigid in axial DOF.
    face_x_mm = 205. if attachment == "upstream" else 288.2
    y_targets = [[face_x_mm, -breadth_mm/2, 0.], [face_x_mm, breadth_mm/2, 0.]]
    z_target = [face_x_mm, 0., -110.]
    active_ids = np.flatnonzero(active)
    def closest(target):
        return int(active_ids[np.argmin(np.linalg.norm(xyz[active_ids] - target, axis=1))])
    return {1: axial, 2: [closest(z_target)], 3: [closest(p) for p in y_targets]}


def volume_mm3(xyz, tets):
    c = xyz[tets[:,:4]]
    return float(np.abs(np.linalg.det(c[:,1:]-c[:,:1])).sum()/6)


def supports_axial(xyz, unwarped, faces, selected, attachment):
    support_x_mm = 205. if attachment == "upstream" else 295.
    faces = faces[np.max(np.abs(unwarped[faces,0]-support_x_mm),axis=1) < 1.e-5]
    shares = np.zeros(len(xyz))
    for face in faces:
        a,b,c = unwarped[face[:3]]
        face_area_mm2 = np.linalg.norm(np.cross(b-a,c-a))/2
        shares[face] += face_area_mm2 / 6
    shares = shares[selected]
    total_k_N_mm = 4 * 210000. * pi/4 * 70.**2 / 485.
    # Lengthening the 395 mm shaft by 90 mm contributes series compliance.
    return list(zip(map(int, selected), shares / shares.sum() * total_k_N_mm, strict=True))



def near_gate_saddles(xyz,unwarped,faces,layout):
    """Trial transverse gate saddle. The low and high stiffness seats are in parallel."""
    result = []
    for axis,level_mm,other,inside_mm in ((1,layout.roof_width_mm/2,2,80.),(2,30.+layout.roof_band_mm,1,95.)):
        # Two [70?70 mm] hypothetical bypass arms per direction, clear of the
        # gate swept envelope. Each arm has a 54 mm unsupported bending length.
        each_N_mm = 3 * 210000. * (70.**4/12) / 54.**3
        for side in (-1,1):
            matching = np.all(np.abs(unwarped[faces,axis]-side*level_mm)<1e-5,axis=1)
            shares = np.zeros(len(xyz))
            for face in faces[matching]:
                for shape,pt,V in quad(unwarped[face]):
                    if 266. < pt[0] < 295. and abs(pt[other]) < inside_mm:
                        shares[face] += np.linalg.norm(V)*np.abs(shape)
            indices = np.flatnonzero(shares>0.)
            for tag in indices:
                result.append((int(tag),axis+1,float(2*each_N_mm*shares[tag]/shares.sum())))
    return result

def run_mesh(layout, mesh_mm, inner_r_mm, bevel_mm, attachment, case_defs, pressure_bar, liner, elastic, braced=False):
    with TemporaryDirectory(prefix="t22g-ring-", dir=HERE) as name:
        work = Path(name)
        xyz, tets, active, triangles = mesh(work, make_geo(layout, mesh_mm, inner_r_mm, bevel_mm))
        unwarped = xyz.copy()
        xyz[1:,0] -= relief(xyz[1:])
        quality = jacobian_statistics(xyz,tets)
        if quality["nonpositive_element_count"]:
            raise ValueError(f"Nonpositive warped ring Jacobian: {quality}")
        faces = aperture_faces(unwarped, triangles, inner_r_mm)
        if not len(faces):
            raise ValueError("No ring cavity found")
        fixed = support(xyz, active, layout.roof_width_mm, attachment, inner_r_mm)
        forces = [pressure(xyz, unwarped, faces, case, 150.+layout.roof_wall_mm, skew, liner, inner_r_mm)
                  for _,case,skew in case_defs]
        axial = supports_axial(xyz, unwarped, triangles, fixed[1], attachment) if elastic else None
        if axial:
            fixed[1] = []
        braces = near_gate_saddles(xyz,unwarped,triangles,layout) if braced else []
        deck(work, xyz, tets, active, fixed, forces, pressure_bar, axial, support_springs=braces)
        tool("ccx.exe", ["-i", "roof"], work, "Job finished")
        fields = frd_fields(work / "roof.frd", len(xyz))
        rf = reactions(work / "roof.dat")
    if len(fields) != len(case_defs)*len(pressure_bar) or len(rf) != len(fields):
        raise RuntimeError(f"Expected full steps, got {len(fields)} fields and {len(rf)} reactions")
    y_edge,z_edge = (87.,42.) if inner_r_mm >= ROOT_R_MM else (75.,30.)
    station_xs = (211.,228.,250.,270.,281.,287.,292.)
    opening_pts = [(x,y,z) for x in station_xs for y in (-53.,0.,53.) for z in (-z_edge,z_edge)]
    section_pts = [(x,y,z) for x in station_xs for y,z in (
        (0.,z_edge+3.), (53.,z_edge+3.), (70.,z_edge+8.),
        (y_edge+3.,19.), (y_edge+8.,26.), (y_edge+18.,0.),
        (-y_edge-18.,0.), (0.,-z_edge-3.), (53.,-z_edge-3.), (70.,-z_edge-8.))]
    if inner_r_mm >= ROOT_R_MM:
        section_pts += [(x, sign*(y_edge - inner_r_mm + (inner_r_mm+2.)*cos(radians(angle))),
                         side*(z_edge - inner_r_mm + (inner_r_mm+2.)*sin(radians(angle))))
                        for x in (228.,250.,270.,282.,286.,289.,292.)
                        for angle in (12.,30.,50.,70.) for sign,side in ((1,1),(1,-1),(-1,1))]
    valid_x = lambda p: p[0] < GATE_X_MM - gate_relief_mm(p[1])*smoothstep(
                                          (p[0]-GATE_X_MM+WING_RELIEF_RUNOUT_MM)/WING_RELIEF_RUNOUT_MM) - .5
    section_pts = [p for p in section_pts if valid_x(p)]
    opening_int = interpolation(xyz,tets,opening_pts)
    section_int = interpolation(xyz,tets,section_pts)
    s_nodes,s_weights = np.polynomial.legendre.leggauss(6)
    x_cuts_mm = (228.,250.,270.)
    wall_points = [(x,side*(y_edge+(layout.roof_width_mm/2-y_edge)*(1.+a)/2),0.)
                   for x in x_cuts_mm for side in (-1,1) for a in s_nodes]
    wall_int = interpolation(xyz,tets,wall_points)
    coords = xyz[active]
    c = coords
    full = (c[:,0] > 207.5) & (c[:,0] < GATE_X_MM - np.array([gate_relief_mm(y) for y in c[:,1]]) - 2.5)
    # Regions exclude end/traction discontinuity edges but retain the smooth
    # bore arcs. Coverage is reported independently of fixed gauge stations.
    usages = {}
    for j, ((label, case, skew), force) in enumerate(zip(case_defs, forces, strict=True)):
        rows = {}
        for k, bar in enumerate(pressure_bar):
            idx = j*len(pressure_bar)+k
            u = fields[idx]["DISP"]
            stress = fields[idx]["STRESS"]
            vm = mises(stress[active])
            interior = vm.copy()
            interior[~full] = -1.
            governing = int(np.argmax(interior))
            opening = np.array([float(w @ u[t,2]) for t,w in opening_int]).reshape(-1,2)
            selected_stress = np.array([w @ stress[t] for t,w in section_int])
            applied_N = force.sum(axis=0) * bar/315.
            equiv = mises(selected_stress)
            balance = float(np.linalg.norm(rf[idx] + applied_N) / max(1., case["main_force_N"]*bar/315.))
            rows[bar] = {"opening_mm": float(max(opening[:,1]-opening[:,0])),
                         "opening_at_fixed_gauges_mm": list(opening[:,1]-opening[:,0]),
                         "VM_max_off_ends_MPa": float(vm[governing]),
                         "VM_max_off_ends_point_mm": list(c[governing]),
                         "governing_tensor_MPa": stress[active[governing]].tolist(),
                         "VM_max_all_nodes_MPa": float(max(vm)), "VM_fixed_MPa": list(equiv),
                         "fixed_tensors_MPa": selected_stress.tolist(),
                         "force_balance_fraction": balance,
                         "axial_reaction_N": float(rf[idx][0]), "axial_applied_N": float(applied_N[0])}
        proof = fields[j*len(pressure_bar)+pressure_bar.index(315)]["STRESS"]
        result = {"load":case, "transverse_skew":skew, "y_centroid_of_top_load_mm":float(
            xyz[unwarped[:,2]>0,1] @ force[unwarped[:,2]>0,2] / case["roof"]["normal_force_N"]), "states":rows}
        if 300 in pressure_bar:
            cyclic = fields[j*len(pressure_bar)+pressure_bar.index(300)]["STRESS"]
            start = fields[j*len(pressure_bar)+pressure_bar.index(0)]["STRESS"] if 0 in pressure_bar else np.zeros_like(proof)
            gradient = normal_gradient(xyz,tets,triangles,cyclic-start)
            safety = margins(proof,start,cyclic,FORGED_BLOCK,gradient)
            masked_ids = active[full]
            controlling = int(masked_ids[np.argmin(safety["FKM"][masked_ids])])
            result["fatigue"] = {
                "FKM":float(safety["FKM"][controlling]),
                "FKM_at_same_point_without_support":float(safety["FKM_no_notch_credit"][controlling]),
                "point_xyz_mm":xyz[controlling].tolist(), "proof_VM_MPa":float(mises(proof[controlling])),
                "gradient_mm_inv":float(gradient[controlling]), "n_sigma":float(safety["n_sigma"][controlling]),
                "zero_step_explicit":0 in pressure_bar,
            }
        values = np.array([w @ proof[t,2] for t,w in wall_int]).reshape(len(x_cuts_mm),2,len(s_nodes))
        integrated_N_mm = (values @ s_weights) * (layout.roof_width_mm/2-y_edge)/2
        checks = []
        for x,recovered in zip(x_cuts_mm,integrated_N_mm,strict=True):
            expected_N_mm = (150.*case["roof"]["inlet_MPa"]*np.exp(-case["decay_mm_inv"]*(x-case["punch_x_mm"]))) if x>=case["punch_x_mm"] else 0.
            checks.append({"x_mm":x,"FEA_membrane_N_mm":recovered.tolist(),"hand_force_N_mm":float(expected_N_mm),
                           "error_relative":float(abs(recovered.sum()/expected_N_mm-1.)) if expected_N_mm else None})
        result["membrane_sections_315"] = checks
        usages[label] = result
    return {"mesh_mm":mesh_mm,"nodes":len(active),"elements":len(tets),
            "analysis_solid_volume_mm3":volume_mm3(xyz,tets), "layout":layout.data(), "mesh_jacobians":quality,
            "support":attachment, "elastic_columns":elastic, "trial_transverse_saddles":braced, "liner_traction_on_flats":liner, "support_node_count":{str(d):len(i) for d,i in fixed.items()},
            "bore_corner_R_mm":inner_r_mm, "outer_bevel_mm":bevel_mm,
            "opening_gauges_bottom_then_top_xyz_mm":opening_pts,
            "stress_gauges_xyz_mm":section_pts, "cases":usages}


def main():
    parser = ArgumentParser()
    parser.add_argument("--mesh", nargs="+", type=float, required=True)
    parser.add_argument("--radius", type=float, default=1.)
    parser.add_argument("--bevel", type=float, default=38.)
    parser.add_argument("--wall", type=float)
    parser.add_argument("--band", type=float)
    parser.add_argument("--attachment", choices=("upstream","downstream"), default="downstream")
    parser.add_argument("--screen", action="store_true")
    parser.add_argument("--liner", action="store_true")
    parser.add_argument("--elastic", action="store_true")
    parser.add_argument("--braced", action="store_true")
    parser.add_argument("--proof-only", action="store_true")
    parser.add_argument("--cases", nargs="+", choices=("long_skew","short_skew","long_centred"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    layout,hand_case,_ = choose()
    if layout is None:
        raise RuntimeError("Hand screen has no passing geometry")
    layout = Layout(layout.material, args.wall or layout.roof_wall_mm, args.band or layout.roof_band_mm,
                    args.band or layout.floor_band_mm)
    use_case = ("long_skew", hand_case, True)
    short = janssen(main_cylinder_force_N(315), .60, .20, SHORTEST_LOADED_MM)
    case_defs = [use_case, ("short_skew",short,True)]
    if not args.screen or args.cases:
        case_defs += [("long_centred", hand_case, False)]
    if args.cases:
        case_defs = [record for record in case_defs if record[0] in args.cases]
    steps = (315,) if args.proof_only else (300,315) if args.screen else PRESSURES_BAR
    result = []
    for size_mm in args.mesh:
        result.append(run_mesh(layout,size_mm,args.radius,args.bevel,args.attachment,
                               case_defs, steps, args.liner, args.elastic,args.braced))
        args.out.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
        print(size_mm, [(key, v["states"][315]["VM_max_off_ends_MPa"], v["states"].get(300,v["states"][315])["opening_mm"])
                       for key,v in result[-1]["cases"].items()], flush=True)


if __name__ == "__main__":
    main()

