"""Generate and solve linear-elastic C3D10 sectors with x/y load superposition."""
import argparse
from itertools import product
import json
from math import log10
import os
from pathlib import Path
import re
import subprocess
import tempfile

os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from scipy.spatial import cKDTree

from frame_analytic import (
    CHAMBER_MODEL, COVER_RADIUS_mm, COLUMN_HOLE_mm, COLUMN_INNER_SEAT_BORE_mm, CYCLIC_N, DISCHARGE_BAY_mm, ECC_mm, E_MPa,
    COLUMN_OUTER_BLEND_mm, HALF_PITCH_mm, HERE, NU, NUT_BEAR_OD_mm, OUTLET_HEIGHT_mm, OUTLET_RADIUS_mm,
    OUTLET_WIDTH_mm, PAD_WIDTH_mm, PAD_HEIGHT_mm, PRELOAD_N, PRELOAD_SCATTER,
    REAR_INNER_RADIUS_mm, STATIC_N, STUDS, STUD_HOLE_RADIUS_mm, VARIANTS, column, section,
)
from frame_geometry import model

BIN = Path(os.environ.get("REV_FREECADCMD", "E:/Tools/FreeCAD-1.1/bin/freecadcmd.exe")).parent
FEA = HERE / "fea"
# Dunavant seven-point degree-five quadrature, weights normalised to reference triangle.
QUADRATURE = [(1/3, 1/3, .225)]
for a, b, w in ((.05971587178977,.47014206410511,.13239415278851),
                 (.79742698535309,.10128650732346,.12593918054483)):
    QUADRATURE += [(a,b,w),(b,a,w),(b,b,w)]
MODES = ("preload", "centred", "ex", "ey")
ENDS = ("cylinder", "chamber")


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False,
                               ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def run_tool(command, folder, marker=None):
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS="1", CCX_NPROC_RESULTS="1", CCX_NPROC_EQUATION_SOLVER="1")
    run = subprocess.run([str(part) for part in command], cwd=folder, env=env,
                         capture_output=True, text=True, errors="replace", timeout=1500)
    output = run.stdout + run.stderr
    if run.returncode or re.search(r"\*ERROR|^Error\s*:", output, flags=re.MULTILINE) or (
            marker and marker not in output):
        raise RuntimeError(f"{command}: exit {run.returncode}\n{output[-9000:]}")
    return output


def read_mesh(path):
    lines = path.read_text(encoding="ascii").splitlines()
    j = lines.index("$Nodes")
    n = int(lines[j+1])
    coords = np.zeros((n+1, 3))
    for line in lines[j+2:j+2+n]:
        tag, *xyz = line.split()
        coords[int(tag)] = tuple(map(float, xyz))
    j = lines.index("$Elements")
    triangles, tets = [], []
    for line in lines[j+2:j+2+int(lines[j+1])]:
        tag, typ, ntags, *record = map(int, line.split())
        nodes = record[ntags:]
        if typ == 9:
            triangles.append(nodes)
        if typ == 11:
            nodes[-1], nodes[-2] = nodes[-2], nodes[-1]
            tets.append(nodes)
    if not tets:
        raise ValueError("The OCC mesh contains no second-order tetrahedra")
    tets = np.array(tets, dtype=int)
    active = np.unique(tets)
    # Internal fragment surfaces and unconnected OCC centres can occur in MSH2.
    active_set = set(active)
    triangles = np.array([tri for tri in triangles if set(tri).issubset(active_set)], dtype=int)
    return coords, tets, active, triangles


def plane_triangles(coords, triangles, axis, location_mm):
    return triangles[np.max(np.abs(coords[triangles,axis] - location_mm), axis=1) < 1e-5]


def quadrature(points):
    """Return isoparametric P2 shape values, face positions, and area weights."""
    for r, s, weight in QUADRATURE:
        t = 1-r-s
        N = np.array([t*(2*t-1),r*(2*r-1),s*(2*s-1),4*t*r,4*r*s,4*s*t])
        Nr = np.array([1-4*t,4*r-1,0,4*(t-r),4*s,-4*s])
        Ns = np.array([1-4*t,0,4*s-1,-4*r,4*r,4*(t-s)])
        area_mm2 = np.linalg.norm(np.cross(Nr @ points, Ns @ points), axis=1) * weight/2
        yield N, N @ points, area_mm2


def patch_loads(coords, faces, mask, symmetric_center_mm):
    """Integrate normal traction and its x/y antisymmetric components."""
    weights = np.zeros((3, len(coords)))
    accumulator = np.zeros((3, len(faces), 6))
    if len(faces) == 0:
        raise ValueError("A pressure plane has no faces")
    points = coords[faces]
    area_mm2 = 0.
    for N, xyz, da_mm2 in quadrature(points):
        values = da_mm2 * mask(xyz[:,0], xyz[:,1])
        area_mm2 += values.sum()
        base = values[:,None] * N
        accumulator[0] += base
        accumulator[1] += base * xyz[:,0,None]
        accumulator[2] += base * xyz[:,1,None]
    for mode in range(3):
        np.add.at(weights[mode], faces.ravel(), accumulator[mode].ravel())
    w0, wx, wy = weights
    if not area_mm2:
        raise ValueError(f"Empty load patch around {symmetric_center_mm}")
    return w0/area_mm2, wx, wy, float(area_mm2)


def smooth_edge(distance_mm, width_mm):
    t = np.clip(distance_mm/width_mm, 0., 1.)
    return t*t*(3-2*t)


def ring(x, y, cx, cy, r_in, r_out, taper_mm):
    r = np.hypot(x-cx, y-cy)
    return smooth_edge(np.minimum(r-r_in, r_out-r), taper_mm)


def chamber_pad(x,y):
    return smooth_edge(np.minimum.reduce((PAD_WIDTH_mm/2-x,x-OUTLET_WIDTH_mm/2,
                                          PAD_HEIGHT_mm/2-y)),8.)


def load_data(v, end, coords, triangles):
    h = v.depth_mm
    face = plane_triangles(coords, triangles, 2, 0.)
    if end == "cylinder":
        def bearing(x, y):
            return ring(x,y,0,0,REAR_INNER_RADIUS_mm,COVER_RADIUS_mm,5.)
    else:
        bearing = chamber_pad
    w0, wx, wy, area_load_mm2 = patch_loads(coords, face, bearing, "actuator")
    a = HALF_PITCH_mm

    def inner_seat(x,y):
        return ring(x,y,a,a,COLUMN_INNER_SEAT_BORE_mm/2,NUT_BEAR_OD_mm/2,5.)

    def outer_seat(x,y):
        return ring(x,y,a,a,COLUMN_HOLE_mm/2,NUT_BEAR_OD_mm/2,5.)

    win = patch_loads(coords, plane_triangles(coords, triangles, 2, 0.), inner_seat, "inner")
    wout = patch_loads(coords, plane_triangles(coords, triangles, 2, h), outer_seat, "outer")
    phi = column(v)["load_fraction"]
    seat = (1-phi)*win[0]+phi*wout[0]
    q_N = STATIC_N / 4
    forces = {"preload": PRELOAD_N*(win[0]-wout[0]),
              "centred": PRELOAD_N*(win[0]-wout[0]) + q_N*(w0-seat)}
    for i, (name, weights) in enumerate(zip(("ex", "ey"), (wx,wy), strict=True)):
        c_mm = coords[:,i]
        result_Nmm = q_N * ECC_mm
        forces[name] = result_Nmm * (weights/(weights@c_mm) - seat/(seat@c_mm))
    measured = {name: [float(f.sum()), float(f@coords[:,0]), float(f@coords[:,1])]
                for name, f in forces.items()}
    if any(abs(measured[name][0]) > 1e-6 for name in ("preload", "centred")):
        raise ValueError(f"Axial equilibrium error: {measured}")
    if abs(measured["ex"][1]) > .01 or abs(measured["ey"][2]) > .01:
        raise ValueError(f"Moment equilibrium error: {measured}")
    return forces, (w0,win[0],wout[0]), {
        "traction_weighted_area_mm2": 4*area_load_mm2, "inside_seat_area_mm2": win[3],
        "outside_seat_area_mm2": wout[3], "sector_force_and_first_moments": measured,
    }


def restraints(coords, active, depth_mm, mode):
    xfaces = active[np.abs(coords[active,0]) < 1e-5]
    yfaces = active[np.abs(coords[active,1]) < 1e-5]
    sets = {"XSYM": xfaces, "YSYM": yfaces}
    if mode in ("preload", "centred"):
        face = active[np.abs(coords[active,2]-depth_mm) < 1e-5]
        anchor = int(face[np.argmin(np.linalg.norm(coords[face,:2]-[322,270], axis=1))])
        bcs = [("XSYM",1,1),("YSYM",2,2),(anchor,3,3)]
    else:
        ia = 0 if mode == "ex" else 1
        a_name,b_name = ("XSYM","YSYM") if ia == 0 else ("YSYM","XSYM")
        face = sets[a_name]
        p = np.zeros(3)
        p[1-ia] = 275.
        anchors = []
        for z_mm in (0., depth_mm):
            p[2] = z_mm
            anchors.append(int(face[np.argmin(np.linalg.norm(coords[face]-p,axis=1))]))
        bcs = [(a_name,2-ia,2-ia),(a_name,3,3),(b_name,2-ia,2-ia)]
        bcs.extend((n,ia+1,ia+1) for n in anchors)
        # A symmetry-plane intersection belongs to both sets; each same-DOF
        # constraint must occur once in the CCX deck.
        sets[b_name] = np.setdiff1d(sets[b_name], sets[a_name])
    return sets, bcs


def write_mesh_include(path, coords, tets, active):
    with path.open("w", encoding="ascii", newline="\n") as f:
        f.write("*NODE\n")
        for tag in active:
            x,y,z = coords[tag]
            f.write(f"{tag},{x:.10g},{y:.10g},{z:.10g}\n")
        f.write("*ELEMENT,TYPE=C3D10,ELSET=TRAVERSE\n")
        for i,nodes in enumerate(tets,1):
            f.write(f"{i}," + ",".join(map(str,nodes)) + "\n")


def input_deck(path, mesh_name, sets, bcs, forces):
    with path.open("w", encoding="ascii", newline="\n") as f:
        f.write("*HEADING\nT-1.7 | N, mm, MPa | C3D10\n")
        f.write(f"*INCLUDE,INPUT={mesh_name}\n")
        for name, tags in sets.items():
            f.write(f"*NSET,NSET={name}\n")
            for i in range(0,len(tags),16):
                f.write(",".join(map(str,tags[i:i+16])) + "\n")
        f.write(f"*MATERIAL,NAME=STEEL\n*ELASTIC\n{E_MPa},{NU}\n"
                "*SOLID SECTION,ELSET=TRAVERSE,MATERIAL=STEEL\n*BOUNDARY\n")
        for tag, first, last, *value in bcs:
            target = f",{value[0]:.13g}" if value else ""
            f.write(f"{tag},{first},{last}{target}\n")
        f.write("*STEP\n*STATIC\n*CLOAD\n")
        for tag in np.flatnonzero(np.abs(forces) > 1e-12):
            f.write(f"{tag},3,{forces[tag]:.13g}\n")
        f.write("*NODE FILE\nU,RF\n*EL FILE\nS\n*END STEP\n")


def results_frd(path, count):
    data = {}
    field = None
    fields = {"DISP": 3, "STRESS": 6, "FORC": 3}
    with path.open(encoding="ascii") as f:
        for line in f:
            if line.startswith(" -4"):
                name = line.split()[1]
                field = data.setdefault(name,np.zeros((count,fields[name]))) if name in fields else None
            if line.startswith(" -1") and field is not None:
                tag = int(line[3:13])
                field[tag] = [float(line[13+i*12:25+i*12]) for i in range(field.shape[1])]
            if line.startswith(" -3"):
                field = None
    if not {"STRESS","DISP"}.issubset(data):
        raise ValueError(f"Missing CCX results in {path}")
    return data


def stress_tensors(c):
    v = np.zeros((*c.shape[:-1],3,3))
    v[...,0,0],v[...,1,1],v[...,2,2],v[...,0,1],v[...,1,2],v[...,2,0] = c.T
    v[...,1,0],v[...,2,1],v[...,0,2] = v[...,0,1],v[...,1,2],v[...,2,0]
    return v


def mises(c):
    x,y,z,xy,yz,zx = c.T
    return np.sqrt(.5*((x-y)**2+(y-z)**2+(z-x)**2)+3*(xy*xy+yz*yz+zx*zx))


def cut_verification(v,end,coords,triangles,centred):
    cut = plane_triangles(coords, triangles, 0, 0.)
    points = coords[cut]
    vals = centred[cut,0]
    z_ref = v.depth_mm/2
    mm3 = momentum_Nmm = area_mm2 = inertia_mm4 = 0.
    for N, xyz, da in quadrature(points):
        z_mm = xyz[:,2]-z_ref
        area_mm2 += 2*da.sum()
        mm3 += 2*(z_mm@da)
        inertia_mm4 += 2*((z_mm*z_mm)@da)
        momentum_Nmm += 2*((vals@N)*(z_mm)@da)
    theory = section(v,end)
    predicted_Nmm = theory["bending_moment_Nmm"]
    section_values = {k: theory[k] for k in ("cut_x_mm","load_half_centroid_mm","bending_moment_Nmm",
                                             "section_I_mm4","section_nominal_bending_MPa","cut_breadth_mm")}
    return {**section_values, "FEA_cut_area_mm2": float(area_mm2),
            "FEA_cut_inertia_about_mid_depth_mm4": float(inertia_mm4),
            "FEA_cut_first_moment_mm3": float(mm3),
            "FEA_bending_moment_Nmm": float(abs(momentum_Nmm)),
            "FEA_bending_error_fraction": float(abs(abs(momentum_Nmm)/predicted_Nmm-1)),
            "FEA_section_nominal_MPa": float(abs(momentum_Nmm)*v.depth_mm/(2*theory["section_I_mm4"]))}


def weld_hot_spot(v, coords, faces, stress, cavities):
    """IIW type-a hot spot at the flange side of the four pocket welds."""
    fatigue = []
    t = v.flange_mm
    for z in (t, v.depth_mm-t):
        tags = np.unique(plane_triangles(coords,faces,2,z))
        xy = coords[tags,:2]
        tree = cKDTree(xy)
        for x,y,_ in cavities[:2]:
            across, along = (0,1) if abs(x)>abs(y) else (1,0)
            centre = np.array([x,y])
            toes = [(side*26., length_mm, side, 0.)
                    for side in (-1,1) for length_mm in (0.,15.,30.,45.,60.,75.,88.)]
            toes += [(width_mm,104.,0.,1.) for width_mm in (-10.,0.,10.)]
            for side in (-1,1):
                for angle in (np.pi/6,np.pi/4,np.pi/3):
                    nx,ny = side*np.cos(angle),np.sin(angle)
                    toes.append((side*10+16*nx,88+16*ny,nx,ny))
            for toe_u,toe_v,nu,nv in toes:
                unit_normal = np.zeros(2)
                unit_normal[across],unit_normal[along] = nu,nv
                toe = centre.copy()
                toe[across] += toe_u
                toe[along] += toe_v
                nx,ny = unit_normal
                samples = []
                for station in (.4,1.):
                    q = toe - station*t*unit_normal
                    nearest = tree.query(q,k=8)[1]
                    dr = xy[nearest]-q
                    st = stress[tags[nearest]]
                    local = nx*nx*st[:,0]+ny*ny*st[:,1]+2*nx*ny*st[:,3]
                    coeff = np.linalg.lstsq(np.column_stack((np.ones(8),dr)),local,rcond=None)[0]
                    samples.append(coeff[0])
                fatigue.append(abs((5*samples[0]-2*samples[1])/3))
    return float(max(fatigue))


def surface_normals(coords, tets, triangles):
    """Area-weighted exterior normal. The incident tetrahedron sets its sign."""
    owner = {}
    for i, tet in enumerate(tets[:, :4]):
        for j in range(4):
            face = tuple(sorted(np.delete(tet,j)))
            owner[face] = -1 if face in owner else i
    ids = np.array([owner.get(tuple(sorted(row[:3])), -1) for row in triangles])
    exterior = triangles[ids >= 0]
    points = coords[exterior[:,:3]]
    normals = np.cross(points[:,1]-points[:,0], points[:,2]-points[:,0])
    inside = coords[tets[ids[ids>=0],:4]].mean(axis=1)-points.mean(axis=1)
    normals *= np.where(np.einsum("ij,ij->i", normals, inside)>0, -1., 1.)[:,None]
    # The mirror planes are artificial exterior surfaces of a quadrant.
    on_symmetry = np.any(np.max(np.abs(points[:,:,:2]),axis=1)<1e-6,axis=1)
    surface = np.zeros_like(coords)
    for j in range(6):
        np.add.at(surface, exterior[~on_symmetry,j], normals[~on_symmetry])
    length = np.linalg.norm(surface,axis=1)
    return np.divide(surface,length[:,None],out=np.zeros_like(surface),
                     where=length[:,None]>0)


def normal_gradient(coords, tets, normals, sigma):
    """Recover the first derivative from volume-weighted T4 corner gradients."""
    vertices = tets[:,:4]
    xyz = coords[vertices]
    jac = xyz[:,1:]-xyz[:,0,None,:]
    slopes = np.linalg.solve(jac,(sigma[vertices[:,1:]]-sigma[vertices[:,0,None]])[...,None])[...,0]
    vol6 = np.abs(np.linalg.det(jac))
    accum, weights = np.zeros_like(normals), np.zeros(len(coords))
    for j in range(10):
        np.add.at(accum,tets[:,j],slopes*vol6[:,None])
        np.add.at(weights,tets[:,j],vol6)
    denom = weights*sigma
    gradient = np.divide(np.einsum("ij,ij->i",accum,normals),denom,
                         out=np.zeros(len(coords)),where=denom>0)
    return np.clip(gradient, 0., 100.)


def fkm_parameters(rm_MPa, roughness_um, casting, forging=False):
    kR = 1-(.20 if casting else .22)*log10(roughness_um)*log10(2*rm_MPa/400)
    jG = 1.25 if casting else 1.
    component = (.34 if casting else (.40 if forging else .45))*rm_MPa*kR*10**(-1/15)/(1.5*jG)
    return component, kR, jG, .00035*rm_MPa+(.05 if casting else -.1)


def notch_support(gradient, rm_MPa, casting):
    aG, bG = (.25,2000.) if casting else (.50,2700.)
    scale = np.where(gradient <= .1, np.sqrt(10)*gradient,
                     np.where(gradient <= 1., np.sqrt(gradient), gradient**.25))
    return 1+10**(-aG-rm_MPa/bG)*scale


def round_surface(coords, triangles, cx, cy, radius_mm):
    radial = np.hypot(coords[:,0]-cx,coords[:,1]-cy)
    on_circle = np.abs(radial-radius_mm)<.001
    return triangles[np.all(on_circle[triangles[:,:3]],axis=1)]


def mesh_regions(v, end, coords, active, triangles, roots):
    profiles = [round_surface(coords,triangles,x,y,v.radius_mm)
                for x,y in roots if x >= 0 and y >= 0]
    profiles = [face for face in profiles if len(face)]
    # Preserve the individual rib roots, not just a moving maximum over them.
    faces = {f"profile_{i+1}": (face,v.radius_mm/4) for i,face in enumerate(profiles)}
    if end == "chamber":
        r = OUTLET_RADIUS_mm
        corner = round_surface(coords,triangles,OUTLET_WIDTH_mm/2-r,OUTLET_HEIGHT_mm/2-r,r)
        faces["outlet_traverse_R20"] = (corner[np.min(coords[corner,2],axis=1)>=-1e-6],r/4)
    else:
        faces["cylinder_bore"] = (round_surface(coords,triangles,0.,0.,REAR_INNER_RADIUS_mm), None)
        for i,(x,y) in enumerate(STUDS):
            if x < -1e-6 or y < -1e-6:
                continue
            hole_faces = round_surface(coords,triangles,x,y,STUD_HOLE_RADIUS_mm)
            faces[f"stud_{i+1}_OD39"] = (hole_faces, None)
    radius_mm = np.hypot(coords[:,0]-HALF_PITCH_mm,coords[:,1]-HALF_PITCH_mm)
    sleeve_r_mm = COLUMN_HOLE_mm/2+(COLUMN_INNER_SEAT_BORE_mm-COLUMN_HOLE_mm)/2*np.maximum(
        0.,1-coords[:,2]/COLUMN_OUTER_BLEND_mm)
    seat = (np.abs(radius_mm-sleeve_r_mm)<.001) & (coords[:,2]>=-1e-6) & (
        coords[:,2]<=COLUMN_OUTER_BLEND_mm+1e-6)
    faces["column_conical_seat"] = (triangles[np.all(seat[triangles[:,:3]],axis=1)],None)
    regions = {}
    for name,(face,limit) in faces.items():
        if not len(face):
            raise ValueError(f"No surface elements in {name}")
        nodes = np.unique(face)
        h_mm = max(np.linalg.norm(coords[face[:,i]]-coords[face[:,j]],axis=1).max()
                   for i,j in ((0,1),(1,2),(2,0)))
        regions[name] = (nodes, float(h_mm),limit)
    regions["traverse_global"] = (active,None,None)
    return regions


def local_results(v,end,coords,tets,active,triangles,roots,cavities,datasets,patches):
    pre = datasets["preload"]["STRESS"]
    centred = datasets["centred"]["STRESS"]-pre
    sx = datasets["ex"]["STRESS"]
    sy = datasets["ey"]["STRESS"]
    mesh = mesh_regions(v,end,coords,active,triangles,roots)
    normals = surface_normals(coords,tets,triangles)
    component,kR,jG,m_sig = fkm_parameters(v.tensile_MPa,v.roughness_Rz_um,v.name=="cast")
    if v.name == "cast":
        machined_amp, machined_kR, _, _ = fkm_parameters(v.tensile_MPa,6.3,True)
    else:
        machined_amp, machined_kR = component,kR
    bearing_depth_mm = coords[:,2]
    # Finish the accessible traverse end faces and the complete machined
    # outlet/hole walls. Unmarked points, including the subsurface, retain
    # the lower as-cast allowance as a conservative screening bound.
    machined = np.isclose(bearing_depth_mm,0.) | np.isclose(bearing_depth_mm,v.depth_mm)
    for name,(nodes,_,_) in mesh.items():
        if name.startswith(("stud_", "outlet_traverse", "cylinder_bore")):
            machined[nodes] = True
    available_MPa = np.where(machined,machined_amp,component)
    regions = {name:{"h_mm":h,"h_limit_mm":limit,"static_mises_MPa":0.,
                     "principal_tensile_MPa":0.,"principal_abs_MPa":0.,"range_mises_MPa":0.,
                     "range_principal_abs_MPa":0.,"fatigue_utilisation":0.}
               for name,(_,h,limit) in mesh.items()}
    iiwh = 0.
    tie = column(v)
    pre_factors = (1-PRELOAD_SCATTER-tie["embedment_loss_N"]/PRELOAD_N, 1+PRELOAD_SCATTER)
    for px,py in product((-1,1), repeat=2):
        load = centred+px*sx+py*sy
        dr = load*CYCLIC_N/STATIC_N
        dr_MPa = mises(dr)
        dr_principal_MPa = np.max(np.abs(np.linalg.eigvalsh(stress_tensors(dr))),axis=1)
        G = normal_gradient(coords,tets,normals,dr_principal_MPa)
        n = notch_support(G,v.tensile_MPa,v.name=="cast")
        for preload_factor in pre_factors:
            total = preload_factor*pre+load
            mean = preload_factor*pre + dr/2
            eq = mises(total)
            principal = np.linalg.eigvalsh(stress_tensors(total))
            principal_abs = np.max(np.abs(principal),axis=1)
            p_mean = np.maximum(0.,np.linalg.eigvalsh(stress_tensors(mean))[:,-1])
            # Full roughness penalty, plus a conservative linear positive-mean
            # envelope (continues linearly past the Haigh region II boundary).
            utilization = (dr_MPa/2+m_sig*p_mean)/(available_MPa*n)
            for name,(nodes,_,_) in mesh.items():
                zone = regions[name]
                for field, values in (
                    ("static_mises_MPa",eq),("principal_tensile_MPa",principal[:,-1]),
                    ("principal_abs_MPa",principal_abs),("range_mises_MPa",dr_MPa),
                    ("range_principal_abs_MPa",dr_principal_MPa),
                    ("fatigue_utilisation",utilization),
                ):
                    node = nodes[np.argmax(values[nodes])]
                    if values[node] > zone[field]:
                        zone[field] = float(values[node])
                        if field in ("fatigue_utilisation","static_mises_MPa"):
                            zone[field+"_xyz_mm"] = coords[node].tolist()
                        if field == "fatigue_utilisation":
                            zone.update(G_sigma_per_mm=float(G[node]),n_sigma=float(n[node]),
                                        fatigue_alt_mises_MPa=float(dr_MPa[node]/2),
                                        fatigue_positive_mean_MPa=float(p_mean[node]))
        if cavities:
            iiwh = max(iiwh,weld_hot_spot(v,coords,triangles,dr,cavities))
    for zone in regions.values():
        zone["fatigue_factor"] = 1/zone["fatigue_utilisation"]
    body = regions["traverse_global"]
    w0,win,wout = patches
    u_sym = datasets["centred"]["DISP"]-datasets["preload"]["DISP"]
    d_mm = float((w0-win)@u_sym[:,2])
    tilt, lateral, seat_tilt = [], [], []
    for i, name in enumerate(("ex","ey")):
        u = datasets[name]["DISP"]
        dimension = coords[:,i]
        slope1 = (w0@u[:,2])/(w0@dimension)
        slope2 = (win@u[:,2])/(win@dimension)
        tilt.append(float(slope1-slope2))
        seat_tilt.append(float(slope2))
        # Remove the coordinate frame rotation of the bearing plane.
        lateral.append(float((w0-win)@u[:,i]+slope2*((w0-win)@coords[:,2])))
    # FAT 100, type a, full penetration K weld with UT. No mean-stress credit.
    # Use m=3 also past the normal knee as a conservative extrapolation.
    iiw_allow = 100*(2e6/1e7)**(1/3)*(25/v.flange_mm)**.3/1.35 if cavities else None
    return {
        "round": 2, "discharge_bay_mm": DISCHARGE_BAY_mm if end=="chamber" else None,
        "column_inner_seat_bore_mm":COLUMN_INNER_SEAT_BORE_mm, "regions": regions,
        "nodes": int(len(active)), "tetrahedra": int(len(tets)),
        "peak_body_mises_MPa": body["static_mises_MPa"],
        "body_FKM_local_screen_factor": body["fatigue_factor"],
        "adapter_FKM_local_screen_factor": None,
        "body_yield_factor_elastic": v.yield_MPa/body["static_mises_MPa"],
        "adapter_yield_factor_elastic": None,
        "FKM_amplitude_fully_reversed_design_MPa": component,
        "FKM_surface_factor": kR, "FKM_machined_surface_factor": machined_kR,
        "FKM_cast_quality_screen_factor": jG,
        "FKM_mean_stress_slope": m_sig,
        "IIW_hot_spot_range_MPa": iiwh if cavities else None,
        "IIW_hot_spot_design_allowable_MPa": iiw_allow,
        "IIW_hot_spot_factor": iiw_allow/iiwh if cavities else None,
        "centred_face_axial_deflection_mm": d_mm,
        "face_relative_tilt_rad_xy": tilt, "face_relative_transverse_shift_mm_xy": lateral,
        "verification": cut_verification(v,end,coords,triangles,centred),
    }


def solve(v,end,level,archive):
    v = v.at_end(end)
    stem = f"{v.name}_{end}_{level}"
    text, roots, cavities, sizes_mm = model(v,end,level)
    with tempfile.TemporaryDirectory(prefix=stem+"_",dir=FEA) as td:
        folder = Path(td)
        geo = folder / f"{stem}.geo"
        geo.write_text(text,encoding="ascii",newline="\n")
        mesh = folder / f"{stem}.msh"
        log = run_tool([BIN/"gmsh.exe",geo.name,"-3","-order","2","-format","msh2",
                        "-o",mesh.name,"-nt","1","-nopopup"],folder, marker="Done writing")
        vols = [float(val) for val in re.findall(r"^VOL \d+ ([\d.eE+-]+)$",log,re.MULTILINE)]
        coords,tets,active,faces=read_mesh(mesh)
        loads,patches,pressure=load_data(v,end,coords,faces)
        mesh_name = f"{stem}_mesh.inp"
        write_mesh_include(folder/mesh_name,coords,tets,active)
        dataset = {}
        for mode in MODES:
            sets,bcs = restraints(coords,active,v.depth_mm,mode)
            deck = folder / f"{stem}_{mode}.inp"
            input_deck(deck,mesh_name,sets,bcs,loads[mode])
            run_tool([BIN/"ccx.exe","-i",deck.stem],folder,marker="Job finished")
            frd = deck.with_suffix(".frd")
            dataset[mode] = results_frd(frd,len(coords))
            frd.unlink()
            if archive:
                (FEA/deck.name).write_bytes(deck.read_bytes())
        data = local_results(v,end,coords,tets,active,faces,roots,cavities,dataset,patches)
        data.update(pressure)
        if end=="chamber":
            data["chamber_model"] = CHAMBER_MODEL
            data["traverse_depth_mm"] = v.depth_mm
        data.update({"nominal_mesh_sizes_mm": sizes_mm,"OCC_volumes_mm3": vols,
                     "variant": v.name,"end": end,"mesh_level": level})
        if archive:
            dest = FEA/geo.name
            dest.unlink(missing_ok=True)
            dest.write_text(text,encoding='ascii',newline='\n')
    write_json(FEA/f"{stem}.json",data)
    print(stem,data["nodes"],round(data["peak_body_mises_MPa"],2),
          round(data["body_FKM_local_screen_factor"],3),
          round(data["body_yield_factor_elastic"],3),flush=True)
    return data


def benchmark():
    """3D pure-bending reference using the plate's net width at the cylinder cut."""
    v = VARIANTS[0]
    analytic = section(v,"cylinder")
    b_mm = v.depth_mm
    w_mm = analytic["cut_breadth_mm"]
    l_mm = 2*HALF_PITCH_mm
    moment_Nmm = analytic["bending_moment_Nmm"]
    curvature_per_mm = moment_Nmm/(E_MPa*analytic["section_I_mm4"])
    stem = "plate_beam_benchmark"
    with tempfile.TemporaryDirectory(prefix=stem+"_",dir=FEA) as td:
        folder = Path(td)
        geo = folder/f"{stem}.geo"
        geo.write_text('SetFactory("OpenCASCADE");\n'
                       f'Box(1) = {{-{b_mm/2},-{w_mm/2},0,{b_mm},{w_mm},{l_mm}}};\n'
                       'Mesh.MeshSizeMin = 41; Mesh.MeshSizeMax = 41; Mesh.RandomSeed = 42;\n',
                       encoding="ascii",newline="\n")
        mesh = geo.with_suffix(".msh")
        run_tool([BIN/"gmsh.exe",geo.name,"-3","-order","2","-format","msh2","-o",
                  mesh.name,"-nt","1","-nopopup"],folder, marker="Done writing")
        coords,tets,active,faces = read_mesh(mesh)
        bcs = []
        for x,y,dofs in ((-b_mm/2,-w_mm/2,(1,2,3)),(b_mm/2,-w_mm/2,(2,3)),
                         (-b_mm/2,w_mm/2,(3,))):
            anchor = int(active[np.argmin(np.linalg.norm(coords[active]-[x,y,0.],axis=1))])
            ux_mm = -NU*curvature_per_mm*(x*x-y*y)/2
            uy_mm = -NU*curvature_per_mm*x*y
            value = (ux_mm,uy_mm,0.)
            bcs.extend((anchor,dof,dof,value[dof-1]) for dof in dofs)
        forces = np.zeros(len(coords))
        measurement = []
        for station, direction in ((0.,-1.),(l_mm,1.)):
            on_face = plane_triangles(coords,faces,2,station)
            points = coords[on_face]
            weights = np.zeros(len(coords))
            for N, xyz, da in quadrature(points):
                value = xyz[:,0]*da*(direction*E_MPa*curvature_per_mm)
                np.add.at(forces,on_face.ravel(),(value[:,None]*N).ravel())
                np.add.at(weights,on_face.ravel(),(da[:,None]*N).ravel())
            measurement.append(weights/(b_mm*w_mm))
        deck = geo.with_suffix(".inp")
        mesh_name = f"{stem}_mesh.inp"
        write_mesh_include(folder/mesh_name,coords,tets,active)
        input_deck(deck,mesh_name,{},bcs,forces)
        run_tool([BIN/"ccx.exe","-i",stem],folder, marker="Job finished")
        result = results_frd(geo.with_suffix(".frd"),len(coords))
        exact_mises_MPa = analytic["section_nominal_bending_MPa"]
        fea_mises_MPa = float(np.max(mises(result["STRESS"][active])))
        exact_deflection_mm = curvature_per_mm*l_mm*l_mm/2
        obtained_mm = float(abs((measurement[1]-measurement[0])@result["DISP"][:,0]))
        summary = {
            "section_mm": [b_mm,w_mm], "span_mm":l_mm, "moment_Nmm":moment_Nmm,
            "theoretical_peak_mises_MPa":exact_mises_MPa, "FEA_peak_mises_MPa":fea_mises_MPa,
            "theoretical_end_deflection_mm":exact_deflection_mm, "FEA_end_deflection_mm":obtained_mm,
            "relative_stress_error":abs(fea_mises_MPa/exact_mises_MPa-1),
            "relative_deflection_error":abs(obtained_mm/exact_deflection_mm-1),
        }
        (FEA/geo.name).write_bytes(geo.read_bytes())
        (FEA/deck.name).write_bytes(deck.read_bytes())
        write_json(FEA/f"{stem}.json",summary)
        print(stem,summary,flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--variant", choices=[v.name for v in VARIANTS])
    p.add_argument("--end",choices=ENDS)
    p.add_argument("--levels",default="0,1,2")
    p.add_argument("--archive-level",type=int,default=2)
    p.add_argument("--benchmark", action="store_true", help="Solve the 3D pure-bending reference")
    args=p.parse_args()
    if args.benchmark:
        benchmark()
        return
    os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
    for v in VARIANTS:
        if args.variant and v.name != args.variant:
            continue
        for end in ENDS:
            if args.end and end != args.end:
                continue
            for level in (int(s) for s in args.levels.split(",")):
                solve(v,end,level,level==args.archive_level)


if __name__ == "__main__":
    main()
