"""Local Gmsh/CalculiX C3D10 utilities. Meshes are temporary."""

import os
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

BIN = Path(os.environ.get("REV_FREECADCMD", "E:/Tools/FreeCAD-1.1/bin/freecadcmd.exe")).parent
QUADRATURE = [(1/3, 1/3, .225)]
for a, b, weight in ((.05971587178977, .47014206410511, .13239415278851),
                     (.79742698535309, .10128650732346, .12593918054483)):
    QUADRATURE.extend(((a,b,weight), (b,a,weight), (b,b,weight)))


def tool(program, args, folder, marker, timeout_s=1200):
    env = os.environ | {"OMP_NUM_THREADS": "1", "CCX_NPROC_RESULTS": "1",
                        "CCX_NPROC_STIFFNESS": "1", "CCX_NPROC_EQUATION_SOLVER": "1"}
    result = subprocess.run([str(BIN / program), *args], cwd=folder, env=env,
                            capture_output=True, text=True, errors="replace", timeout=timeout_s)
    output = result.stdout + result.stderr
    if result.returncode or re.search(r"\*ERROR|^Error\s*:", output, re.MULTILINE) or marker not in output:
        raise RuntimeError(f"{program}: exit {result.returncode}\n{output[-5000:]}")
    return output


def mesh(folder, geometry):
    (folder / "model.geo").write_text(geometry, encoding="ascii", newline="\n")
    tool("gmsh.exe", ["model.geo", "-3", "-order", "2", "-format", "msh2", "-o", "model.msh",
                      "-nt", "1", "-nopopup"], folder, "Done writing")
    return read_mesh_file(folder / "model.msh")


def read_mesh_file(path):
    with path.open(encoding="ascii") as file:
        lines = iter(file)
        for line in lines:
            if line.strip() == "$Nodes":
                xyz = np.zeros((int(next(lines)) + 1, 3))
                for row in lines:
                    if row.strip() == "$EndNodes":
                        break
                    tag, *coords = row.split()
                    xyz[int(tag)] = tuple(map(float, coords))
            if line.strip() == "$Elements":
                tets, tris = [], []
                for _ in range(int(next(lines))):
                    _, kind, count, *parts = map(int, next(lines).split())
                    points = parts[count:]
                    if kind == 11:
                        points[-1], points[-2] = points[-2], points[-1]
                        tets.append(points)
                    if kind == 9:
                        tris.append(points)
    tets = np.array(tets, dtype=int)
    active = np.unique(tets)
    triangles = np.array(tris, dtype=int)
    triangles = triangles[np.isin(triangles, active).all(axis=1)]
    return xyz, tets, active, triangles


def quad(points):
    for b, c, weight in QUADRATURE:
        a = 1. - b - c
        value = np.array([a*(2*a-1), b*(2*b-1), c*(2*c-1), 4*a*b, 4*b*c, 4*c*a])
        dr = np.array([1-4*a, 4*b-1, 0, 4*(a-b), 4*c, -4*c])
        ds = np.array([1-4*a, 0, 4*c-1, -4*b, 4*b, 4*(a-c)])
        area_vector = np.cross(dr @ points, ds @ points) * weight / 2
        yield value, value @ points, area_vector


def node_set(name, indices):
    return [f"*NSET,NSET={name}"] + [
        ",".join(str(i) for i in indices[start:start+12]) for start in range(0, len(indices), 12)]


def frd_fields(path, count):
    fields = []
    matrix = None
    with path.open(encoding="ascii") as file:
        for line in file:
            if line.startswith(" -4"):
                key = line.split()[1]
                width = {"DISP": 3, "FORC": 3, "STRESS": 6, "CONTACT": 6}.get(key)
                matrix = None
                if width is not None:
                    if key == "DISP":
                        fields.append({})
                    matrix = np.zeros((count, width))
                    fields[-1][key] = matrix
            elif line.startswith(" -1") and matrix is not None:
                index = int(line[3:13])
                if index < count:
                    matrix[index] = [float(line[13 + 12*i:25 + 12*i]) for i in range(matrix.shape[1])]
            elif line.startswith(" -3"):
                matrix = None
    return fields


def reactions(path):
    rows = []
    data = path.read_text(encoding="ascii", errors="replace")
    for line in re.findall(r"total force \(fx,fy,fz\) for set FIXED[^\n]*\n\s*([^\n]+)", data):
        rows.append(np.array([float(v) for v in line.split()]))
    return rows


def mises(stresses_MPa):
    x, y, z, xy, yz, zx = np.moveaxis(stresses_MPa, -1, 0)
    return np.sqrt(((x-y)**2 + (y-z)**2 + (z-x)**2)/2 + 3*(xy**2 + yz**2 + zx**2))


def interpolation(xyz, tets, points):
    corners = xyz[tets[:, :4]]
    tree = cKDTree(corners.mean(axis=1))
    indices = tree.query(np.array(points), k=min(150, len(corners)))[1]
    rows = []
    for point, subset in zip(points, indices, strict=True):
        p = corners[subset]
        basis = np.transpose(p[:, 1:] - p[:, :1], (0, 2, 1))
        local = np.linalg.solve(basis, (point - p[:, 0])[..., None])[..., 0]
        bary = np.column_stack([1. - local.sum(axis=1), local])
        selection = int(np.argmax(bary.min(axis=1)))
        if np.min(bary[selection]) < -.018:
            raise ValueError(f"Point outside mesh {point}: {bary[selection]}")
        a,b,c,d = bary[selection]
        weights = np.array([a*(2*a-1), b*(2*b-1), c*(2*c-1), d*(2*d-1),
                            4*a*b, 4*b*c, 4*a*c, 4*a*d, 4*b*d, 4*c*d])
        rows.append((tets[subset[selection]], weights))
    return rows



def jacobian_statistics(xyz, tets):
    """Ratios to the affine corner determinant at Gauss points and vertices."""
    coords = xyz[tets]
    corner = np.linalg.det(coords[:,1:4] - coords[:,:1])
    ld = np.array([[-1.,-1.,-1.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    edge = ((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
    gauss = np.full((4,4),.1381966011250105)
    np.fill_diagonal(gauss,.5854101966249685)
    negative = np.zeros(len(tets),dtype=bool)
    ratio = []
    for bary in np.vstack([gauss,np.eye(4)]):
        gradients = [*(ld * (4*bary-1)[:,None]),
                     *(4*(bary[a]*ld[b]+bary[b]*ld[a]) for a,b in edge)]
        det = np.linalg.det(np.einsum("eic,ij->ecj",coords,np.array(gradients)))
        quotient = det/corner
        negative |= quotient <= 0
        ratio.append(float(min(quotient)))
    return {"minimum_ratio_to_affine":min(ratio),"nonpositive_element_count":int(negative.sum())}

def deck(folder, xyz, tets, active, fixed, force_by_case, pressures_bar, supports_axial=None,
         weighted_springs=(), iterative=False, support_springs=()):
    lines = ["*HEADING", "REV T-2.2h, C3D10 analysis", "*NODE"]
    lines.extend(f"{i},{x:.11g},{y:.11g},{z:.11g}" for i in active for x,y,z in [xyz[i]])
    lines.append("*ELEMENT,TYPE=C3D10,ELSET=BODY")
    lines.extend(str(i) + "," + ",".join(map(str, row)) for i, row in enumerate(tets, 1))
    lines.extend(["*MATERIAL,NAME=STEEL", "*ELASTIC", "210000.,.30",
                  "*SOLID SECTION,ELSET=BODY,MATERIAL=STEEL"])
    nodes = sorted({n for indices in fixed.values() for n in indices})
    distributed = [(tag,1,k) for tag,k in (supports_axial or ())] + list(support_springs)
    if distributed:
        ground = int(active.max()+1)
        lines += ["*NODE",f"{ground},0.,0.,0."]
        for idx,(tag,dof,stiffness_N_mm) in enumerate(distributed,1):
            name = f"S{idx}"
            lines += [f"*ELEMENT,TYPE=SPRING2,ELSET={name}",f"{len(tets)+idx},{tag},{ground}",
                      f"*SPRING,ELSET={name}",f"{dof},{dof}",f"{stiffness_N_mm:.12e}"]
        lines += ["*BOUNDARY",f"{ground},1,3"]
        nodes.append(ground)
    lines.extend(node_set("FIXED", nodes))
    if weighted_springs:
        extra = int(active.max()) + (2 if distributed else 1)
        n_spr = len(distributed)
        for idx,(a,b,dof,k_N_mm) in enumerate(weighted_springs):
            first,second = extra + 2*idx, extra + 2*idx + 1
            lines += ["*NODE", f"{first},0.,0.,0.", f"{second},0.,0.,0."]
            name = f"J{idx+1}"
            lines += [f"*ELEMENT,TYPE=SPRING2,ELSET={name}",
                      f"{len(tets)+n_spr+idx+1},{first},{second}",
                      f"*SPRING,ELSET={name}", f"{dof},{dof}", f"{k_N_mm:.12e}"]
            for reference, terms in ((first,a), (second,b)):
                entries = [f"{reference},{dof},1."] + [
                    f"{int(node)},{dof},{-weight:.10g}" for node,weight in sorted(terms.items()) if abs(weight)>1e-10]
                lines += ["*EQUATION", str(len(entries))]
                lines.extend(",".join(entries[i:i+3]) for i in range(0,len(entries),3))
                lines.append("*BOUNDARY")
                lines.extend(f"{reference},{axis},{axis}" for axis in (1,2,3) if axis != dof)
    for axis, indices in fixed.items():
        if not len(indices):
            continue
        name = f"FIXED_{axis}"
        lines.extend(node_set(name, indices))
        lines.extend(["*BOUNDARY", f"{name},{axis},{axis}"])
    for force in force_by_case:
        for pressure_bar in pressures_bar:
            scale = pressure_bar / 315.
            static = "*STATIC,SOLVER=ITERATIVE SCALING" if iterative else "*STATIC"
            lines.extend(["*STEP", static, "1.,1.,1.e-6,1.", "*CLOAD,OP=NEW"])
            n, d = np.where(np.abs(force) > 1e-9)
            lines.extend(f"{i},{j+1},{force[i,j]*scale:.12g}" for i,j in zip(n,d))
            lines.extend(["*NODE FILE", "U,RF", "*EL FILE", "S",
                          "*NODE PRINT,NSET=FIXED,TOTALS=ONLY", "RF", "*END STEP"])
    (folder / "roof.inp").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")

