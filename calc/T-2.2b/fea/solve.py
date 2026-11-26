"""Generate, solve and assess the selected four-stud portal with Gmsh / CCX."""
import argparse
from collections import defaultdict
from hashlib import sha256
from math import exp
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import cKDTree

from geometry import (HERE, BODY_IDS, GAP_MM, CROWN_MM, TIE_CENTERS_MM,
                      YOKE_BOTTOM_MM, YOKE_TOP_MM, build_geo)
from hand import ROOT, SHARES, inherited_load, fatigue, json_write
from mass import B_POST_Z_MM

BIN = Path(os.environ.get("REV_FREECADCMD", "E:/Tools/FreeCAD-1.1/bin/freecadcmd.exe")).parent
sys.path.insert(0, str(ROOT/"calc/T-1.7"))
from frame_fea import QUADRATURE, mises, normal_gradient, notch_support, quadrature, stress_tensors

LEVELS_MM = (36., 28., 21.)
SPRING_N_MM = 100.
CONTACT_NORMAL_MPA_PER_MM = 10000.
CONTACT_TANGENT_MPA_PER_MM = 400.
VIRTUAL_PRELOAD_TEMPERATURE = -425.
STUD_THERMAL_EXPANSION = 1.e-5
PROPS = {"HOUSING": (650.,800.,True), "SHOE": (600.,800.,False), "LEFT": (700.,900.,False),
         "RIGHT": (700.,900.,False),  "BACK_YOKE": (700.,900.,False),
         "FRONT_YOKE": (700.,900.,False), "ST1": (1100.,1220.,False),
         "ST2": (1100.,1220.,False), "ST3": (1100.,1220.,False), "ST4": (1100.,1220.,False)}
TET_FACES = np.array(((0,1,2,4,5,6),(0,3,1,7,8,4),(1,3,2,8,9,5),(2,3,0,9,7,6)))
LOAD = inherited_load()


def tool(args, cwd, logfile, timeout):
    env = dict(os.environ, OMP_NUM_THREADS="1", CCX_NPROC_RESULTS="1", CCX_NPROC_EQUATION_SOLVER="1")
    with logfile.open("w",encoding="ascii") as log:
        run = subprocess.run([str(a) for a in args],cwd=cwd,stdout=log,stderr=subprocess.STDOUT,
                             env=env,timeout=timeout)
    output = logfile.read_text(encoding="ascii",errors="replace")
    if run.returncode or re.search(r"\*ERROR|^Error\s*:",output,re.MULTILINE):
        raise RuntimeError(f"{Path(args[0]).name} exit {run.returncode}\n{output[-3500:]}")
    return output


def mesh_data(path,order=2):
    lines = path.read_text(encoding="ascii").splitlines()
    j = lines.index("$Nodes")
    count = int(lines[j+1])
    xyz = np.zeros((count+1,3))
    for line in lines[j+2:j+2+count]:
        tag,*coord = line.split()
        xyz[int(tag)] = [float(v) for v in coord]
    j = lines.index("$Elements")
    groups = {name:[] for name in BODY_IDS}
    by_id = {index:name for name,index in BODY_IDS.items()}
    for line in lines[j+2:j+2+int(lines[j+1])]:
        eid,kind,ntags,*record = map(int,line.split())
        if kind == 11:
            tags = record[ntags:]
            tags[-1],tags[-2] = tags[-2],tags[-1]
            groups[by_id[record[0]]].append((eid,tags))
    if not all(groups.values()):
        raise ValueError("Gmsh omitted physical solids")
    if order==1:
        used=np.unique([nodes[:4] for rows in groups.values() for _,nodes in rows])
        remap=np.zeros(len(xyz),dtype=int)
        remap[used]=np.arange(1,len(used)+1)
        xyz=np.vstack((np.zeros((1,3)),xyz[used]))
        groups={name:[(eid,remap[nodes[:4]].tolist()) for eid,nodes in rows]
                for name,rows in groups.items()}
    return xyz,groups


def boundary_faces(groups):
    all_faces = {}
    for name,elems in groups.items():
        surface = {}
        for eid,nodes in elems:
            for side,indices in enumerate(TET_FACES,1):
                tags=tuple(nodes[k] for k in indices if k<len(nodes))
                key=tuple(sorted(tags[:3]))
                if key in surface:
                    del surface[key]
                else:
                    surface[key]=(eid,side,tags)
        all_faces[name]=list(surface.values())
    return all_faces


def plane(faces,xyz,axis,value,tol=1e-4):
    return [(e,s,n) for e,s,n in faces if np.max(abs(xyz[list(n),axis]-value)) < tol]


def section(faces,xyz,axis,value,mask=None):
    rows=plane(faces,xyz,axis,value)
    if mask:
        rows=[(e,s,n) for e,s,n in rows if mask(xyz[list(n[:3])].mean(axis=0))]
    return rows


def contacts(xyz,faces):
    out, pairs = {}, []
    for lock,sign in (("LEFT",-1),("RIGHT",1)):
        low,high=160.+GAP_MM,280.+GAP_MM
        # The whole central top plane is master. The contact domain is the
        # overlap with the rounded lower face of the horizontal lock.
        out[lock+"SHOE"]=plane(faces["SHOE"],xyz,2,160.)
        out[lock+"LOW"]=section(faces[lock],xyz,2,low,
                                lambda p: 5. < p[0] < 205. and 76. < sign*p[1] < 116.)
        pairs.append((lock+"LOW",lock+"SHOE"))
        for end,mask in (("BACK",lambda x:x<2.),("FRONT",lambda x:x>204.)):
            label=lock+end
            out[label]=section(faces[lock],xyz,2,high,lambda p:mask(p[0]))
            pairs.append((label,end+"UNDER"))
    for end,limit in (("BACK",20.),("FRONT",150.)):
        name=end+"_YOKE"
        out[end+"UNDER"]=plane(faces[name],xyz,2,YOKE_BOTTOM_MM)
        postmask=(lambda p:p[0]<limit) if end=="BACK" else (lambda p:p[0]>limit)
        for j,side in enumerate((-1,1),1):
            out[f"{end}POST{j}"]=section(faces["HOUSING"],xyz,2,B_POST_Z_MM[1],
                lambda p:postmask(p) and side*p[1]>162.)
        out[end+"ABOVE"]=plane(faces[name],xyz,2,YOKE_TOP_MM)
    for i, (x,y) in enumerate(TIE_CENTERS_MM,1):
        name=f"ST{i}"
        out[name+"HEAD"]=plane(faces[name],xyz,2,YOKE_TOP_MM)
    ties=[(f"{end}POST{j}",end+"UNDER") for end in ("BACK","FRONT") for j in (1,2)]
    ties.extend((f"ST{i}HEAD",("BACK" if i<=2 else "FRONT")+"ABOVE") for i in range(1,5))
    if not all(out.values()):
        raise ValueError("Empty contact selection: "+str([name for name,rows in out.items() if not rows]))
    return out,pairs,ties


def crown_locks(xyz,groups):
    updated=xyz.copy()
    for lock,sign in (("LEFT",-1),("RIGHT",1)):
        tags=np.unique([row for _,row in groups[lock]])
        x,y,z=xyz[tags].T
        y=sign*y
        # Doubly curved contact faces: center-to-edge 0.10 mm. Smoothly
        # transmit the offset to zero within 18 mm of each bounding face.
        low_x=np.clip((x-105.)/100.,-1.,1.)
        low_y=np.clip((y-95.)/16.,-1.,1.)
        yl=np.clip((280.+GAP_MM-z)/18.,0.,1.)
        low_blend=np.clip((178.+GAP_MM-z)/18.,0.,1.)
        low=CROWN_MM*(low_x**2+low_y**2)/2
        end_x=np.minimum(abs(x-TIE_CENTERS_MM[0][0]),abs(x-TIE_CENTERS_MM[2][0]))
        high=CROWN_MM*(np.clip(end_x/25.,0.,1.)**2+np.clip((y-93.5)/31.5,-1.,1.)**2)/2
        high_blend=1.-yl
        updated[tags,2] += low*low_blend-high*high_blend
    return updated


def triangle_quadrature(points):
    if points.shape[1]==6:
        yield from quadrature(points)
        return
    twice_area=np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]),axis=1)
    for r,s,w in QUADRATURE:
        shape=np.array([1-r-s,r,s])
        yield shape,shape@points,twice_area*w/2


def load_patch(xyz,rows,axis,skew_y_mm,target_N):
    tags = np.array([face[2] for face in rows])
    points=xyz[tags]
    x0,x1=LOAD["contact_x_mm"]
    sums=np.zeros(3)
    integrals=[]
    for shapes,loc,areas in triangle_quadrature(points):
        x,y,_=loc.T
        valid=(x>=x0)&(x<=x1)
        p=LOAD["pressure_initial_MPa"]*np.exp(-LOAD["decay_per_mm"]*(x-x0))*valid
        if skew_y_mm:
            p *= 1+3*skew_y_mm*y/75.**2
        w=p*areas
        x_rel=x-LOAD["centroid_x_mm"]
        integrals.append((shapes,w,x_rel))
        sums += [w.sum(),(w*x_rel).sum(),(w*x_rel**2).sum()]
    a,b=np.linalg.solve([[sums[0],sums[1]],[sums[1],sums[2]]],[target_N,0.])
    result=np.zeros_like(xyz)
    for shapes,w,x_rel in integrals:
        nodal=shapes[None,:]*(w*(a+b*x_rel))[:,None]
        np.add.at(result[:,axis],tags.ravel(),nodal.ravel())
    return result


def loading(xyz,faces,share):
    total_N=LOAD["force_300_N"]
    die=faces["HOUSING"]
    roof=section(faces["SHOE"],xyz,2,0.)
    floor=section(die,xyz,2,-60.,lambda p:abs(p[1])<75.)
    f=load_patch(xyz,roof,2,(share-.5)*190.,total_N)
    f+=load_patch(xyz,floor,2,0.,-total_N)
    for sign in (-1.,1.):
        walls=section(die,xyz,1,75.*sign,lambda p:-60.<p[2]<0.)
        f+=load_patch(xyz,walls,1,0.,sign*.4*total_N)
    return f


def nset(name,ids):
    ids=list(map(str,ids))
    return [f"*NSET,NSET={name}"]+[",".join(ids[i:i+16]) for i in range(0,len(ids),16)]


def stabilize(xyz,groups,names=("SHOE","LEFT","RIGHT")):
    springs={}
    for name in names:
        ids=np.unique([tags for _,tags in groups[name]])
        subset=xyz[ids]
        low,high=subset.min(axis=0),subset.max(axis=0)
        center=(low+high)/2
        wanted=np.array([center-(high-low)*[.3,.1,.2],center+(high-low)*[.3,.1,.2],
                         center+(high-low)*[.0,-.3,.3]])
        springs[name]=ids[cKDTree(subset).query(wanted)[1]].tolist()
    return springs


def make_deck(path,mesh_path,xyz,groups,faces,out,pairs,ties,share,node_contact,linear_kinematics):
    fixed_tags=[]
    for name in ("HOUSING","ST1","ST2","ST3","ST4"):
        fixed_tags+=sorted({tag for _,_,nodes in plane(faces[name],xyz,2,-87.) for tag in nodes})
    springs=stabilize(xyz,groups)
    f=loading(xyz,faces,share)
    with mesh_path.open("w",encoding="ascii",newline="\n") as mesh:
        mesh.write("*NODE\n")
        for i,(x,y,z) in enumerate(xyz[1:],1):
            mesh.write(f"{i},{x:.12g},{y:.12g},{z:.12g}\n")
        for name,elems in groups.items():
            element_type=f"C3D{len(elems[0][1])}"
            mesh.write(f"*ELEMENT,TYPE={element_type},ELSET={name}\n")
            for eid,tags in elems:
                mesh.write(f"{eid},"+",".join(map(str,tags))+"\n")
    lines=["*HEADING","REV portal yoke contact study, N mm MPa",f"*INCLUDE,INPUT={mesh_path.name}",
           "*MATERIAL,NAME=STEEL","*ELASTIC","210000.,.30",
           "*MATERIAL,NAME=STUD","*ELASTIC","210000.,.30","*EXPANSION","1.e-5"]
    for name in groups:
        lines += [f"*SOLID SECTION,ELSET={name},MATERIAL={'STUD' if name.startswith('ST') else 'STEEL'}"]
    slave_names={slave for slave,_ in pairs}
    for name,rows in out.items():
        if node_contact and name in slave_names:
            tags=sorted({tag for _,_,face in rows for tag in face})
            lines += nset(name+"N",tags)+[f"*SURFACE,TYPE=NODE,NAME={name}",name+"N"]
        else:
            lines += [f"*SURFACE,TYPE=ELEMENT,NAME={name}"]+[f"{eid},S{side}" for eid,side,_ in rows]
    for i,(slave,master) in enumerate(ties,1):
        lines += [f"*TIE,NAME=JOINT{i},POSITION TOLERANCE=.15",f"{slave},{master}"]
    lines += ["*SURFACE INTERACTION,NAME=LOCKCONTACT","*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR",
              f"{CONTACT_NORMAL_MPA_PER_MM:.0f}.,1.e-5,.08","*FRICTION",f".15,{CONTACT_TANGENT_MPA_PER_MM:.0f}."]
    method="NODE TO SURFACE,SMALL SLIDING" if node_contact else "SURFACE TO SURFACE"
    for slave,master in pairs:
        lines += [f"*CONTACT PAIR,INTERACTION=LOCKCONTACT,TYPE={method}",f"{slave},{master}"]
    spring_i=max(eid for rows in groups.values() for eid,_ in rows)+1
    for axis in (1,2,3):
        lines += [f"*ELEMENT,TYPE=SPRING1,ELSET=K{axis}"]
        for tags in springs.values():
            for node in tags:
                lines.append(f"{spring_i},{node}")
                spring_i+=1
        lines += [f"*SPRING,ELSET=K{axis}",str(axis),str(SPRING_N_MM)]
    stud_tags=sorted({tag for name,rows in groups.items() if name.startswith("ST") for _,tags in rows for tag in tags})
    lines += nset("STUDNODES",stud_tags)+nset("FIXED",fixed_tags)
    lines += ["*NSET,NSET=ALLN,GENERATE",f"1,{len(xyz)-1},1",
              "*BOUNDARY","FIXED,1,3"]
    lines += ["*INITIAL CONDITIONS,TYPE=TEMPERATURE","ALLN,0."]
    pressure_steps=(0,100,200,300,315)
    for pressure_bar in pressure_steps:
        initial={0:.25,100:.05,200:.25,300:.25,315:.5}[pressure_bar]
        step_card="*STEP,INC=125" if linear_kinematics else "*STEP,NLGEOM,INC=125"
        lines += [step_card,"*STATIC",f"{initial},1.,1.e-6,.5"]
        if pressure_bar == 0:
            # Virtual temperature for preload only, solved force read from
            # the 0-bar state. No physical thermal load is applied.
            lines+=["*TEMPERATURE",f"STUDNODES,{VIRTUAL_PRELOAD_TEMPERATURE:.0f}."]
        else:
            lines+=["*CLOAD"]
            lines += [f"{node},{axis+1},{f[node,axis]*pressure_bar/300:.12g}"
                      for node,axis in zip(*np.nonzero(f))]
        lines+=["*NODE FILE,FREQUENCY=999999","U,RF","*EL FILE,FREQUENCY=999999","S",
                "*CONTACT FILE,FREQUENCY=999999","CDIS,CSTR"]
        if not node_contact:
            for slave,master in pairs:
                lines += [f"*CONTACT PRINT,SLAVE={slave},MASTER={master},FREQUENCY=999999","CF"]
        lines+=["*END STEP"]
    path.write_text("\n".join(lines)+"\n",encoding="ascii",newline="\n")
    return np.array(fixed_tags),springs,f


def read_steps(path,n):
    out={}
    count=0
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if line.startswith(" -4"):
                name=line.split()[1]
                width={"DISP":3,"FORC":3,"STRESS":6,"CONTACT":6}.get(name)
                if width is None:
                    data=None
                    continue
                if name=="DISP":
                    count+=1
                    out[count]={}
                data=np.zeros((n,width))
                out[count][name]=data
            elif line.startswith(" -1") and count and data is not None:
                index=int(line[3:13])
                if index<n:
                    data[index]=[float(line[13+12*i:25+12*i]) for i in range(data.shape[1])]
            elif line.startswith(" -3"):
                data=None
    if len(out) != 5 or any({"DISP","FORC","STRESS","CONTACT"}-set(block) for block in out.values()):
        raise ValueError("CCX did not write the complete displacement, reaction, stress and contact fields")
    return [out[1],out[len(out)-1],out[len(out)]]


def read_forces(path,pairs):
    runs = defaultdict(list)
    raw=path.read_text(encoding="ascii")
    for label, block in re.findall(r"statistics for slave set (\w+),[^\n]*\n(.*?)(?=statistics for slave set|\Z)",
                                   raw,flags=re.DOTALL|re.IGNORECASE):
        vector=re.search(r"total surface force[^\n]*\n\s*([^\n]+)",block)
        area=re.search(r"area,\s+normal force[^\n]*\n\s*([^\n]+)",block)
        if vector and area:
            vals=[float(v) for v in vector[1].split()]
            area_mm2,normal_N,shear_N=map(float,area[1].split()[:3])
            if area_mm2 == 0. and not any(vals):
                normal_N = shear_N = 0.
            runs[label].append(dict(vector_N=vals[:3],moment_Nmm=vals[3:],area_mm2=area_mm2,
                                    normal_N=normal_N,shear_N=shear_N))
    if any(len(runs[s]) != 5 for s,_ in pairs):
        raise ValueError("Incomplete CF resultant output: "+str({s:len(runs[s]) for s,_ in pairs}))
    return {s:[runs[s][0],*runs[s][-2:]] for s,_ in pairs}



def integrate_nodal_pressures(xyz, groups, surfaces, pairs, steps):
    # Nodal-contact mode cannot request CCX CF. This reconstruction uses
    # normal pressure only; it is not a full Coulomb reaction measurement.
    owner={eid:(name,nodes) for name,rows in groups.items() for eid,nodes in rows}
    result = {}
    for slave,_ in pairs:
        records=[]
        for state in steps:
            force=np.zeros(3)
            moment=np.zeros(3)
            contact_area_mm2=0.
            for eid,_,tags in surfaces[slave]:
                ids=list(tags)
                points=xyz[ids]+state["DISP"][ids]
                area_normal=np.cross(points[1]-points[0],points[2]-points[0])/2
                center=points[:3].mean(axis=0)
                _,element=owner[eid]
                inside=xyz[element[:4]].mean(axis=0)
                if area_normal@(inside-xyz[ids[:3]].mean(axis=0))>0:
                    area_normal=-area_normal
                values=state["CONTACT"][ids,3]
                p=float(np.maximum(0.,values).mean())
                if p:
                    equivalent=area_normal*p
                    force-=equivalent
                    moment-=np.cross(center,equivalent)
                    contact_area_mm2+=np.linalg.norm(area_normal)
            records.append(dict(vector_N=force.tolist(),moment_Nmm=moment.tolist(),
                                area_mm2=float(contact_area_mm2),normal_N=float(np.linalg.norm(force)),shear_N=None))
        result[slave]=records
    return result


def boundary_normals(xyz,rows,tets):
    surface=np.zeros_like(xyz)
    interior={eid:xyz[tags[:4]].mean(axis=0) for eid,tags in tets}
    for eid,_,face in rows:
        points=xyz[list(face)]
        raw=np.cross(points[1]-points[0],points[2]-points[0])
        if raw@(interior[eid]-points[0])>0:
            raw=-raw
        surface[list(face)] += raw
    sizes=np.linalg.norm(surface,axis=1)
    return np.divide(surface,sizes[:,None],out=np.zeros_like(surface),where=sizes[:,None]>0)


def gradient(xyz,tets,normals,range_MPa):
    if tets.shape[1]==10:
        return normal_gradient(xyz,tets,normals,range_MPa)
    vertices=xyz[tets]
    jac=vertices[:,1:]-vertices[:,:1]
    sigma=range_MPa[tets]
    slopes=np.linalg.solve(jac,(sigma[:,1:]-sigma[:,:1])[...,None])[...,0]
    vol6=np.abs(np.linalg.det(jac))
    accum=np.zeros_like(normals)
    weights=np.zeros(len(xyz))
    for ids in tets.T:
        np.add.at(accum,ids,slopes*vol6[:,None])
        np.add.at(weights,ids,vol6)
    denominator=weights*range_MPa
    return np.clip(np.divide(np.einsum("ij,ij->i",accum,normals),denominator,
                             out=np.zeros(len(xyz)),where=denominator>0),0,100)


def stress_gauges(name):
    """Fixed inboard gauges, separated from ideal contact and tied edges."""
    if name == "HOUSING":
        return [(-50.,sgn*167.,-39.) for sgn in (-1,1)]+[
            (x,sgn*189.,z) for x in (-53.,190.,204.) for sgn in (-1,1) for z in (-10.,30.)]
    if name == "SHOE":
        return [(x,y,157.) for x in (20.,95.,145.,190.) for y in (-97.,-87.,87.,97.)]
    if name in ("LEFT","RIGHT"):
        sign = 1 if name == "RIGHT" else -1
        return [(x,sign*y,z) for x in (-24.,15.,120.,190.,231.)
                for y in (90.,106.,115.) for z in (167.,273.)]
    if name.endswith("_YOKE"):
        x = -26. if name == "BACK_YOKE" else 231.
        return [(x,y,z) for y in (-153.,-100.,-70.,0.,70.,100.,153.)
                for z in (YOKE_BOTTOM_MM+7.,YOKE_TOP_MM-7.)]
    return []


def solid_strain_energy(xyz, groups, pre, proof):
    """Elastic strain energy of C3D4 solids, exact for the linear tetrahedra."""
    if len(next(iter(groups.values()))[0][1]) != 4:
        return None
    shear = 210000./(2.*1.30)
    lame = 210000.*.30/(1.30*.40)
    totals = np.zeros(2)
    fields = (proof, proof-pre)
    for name, rows in groups.items():
        tags = np.asarray([row for _,row in rows])
        points = xyz[tags]
        jac = points[:,1:] - points[:,:1]
        vol = abs(np.linalg.det(jac))/6.
        for index, u in enumerate(fields):
            d = u[tags]
            gradient = np.linalg.solve(jac,d[:,1:]-d[:,:1])
            strain = (gradient+gradient.transpose(0,2,1))/2
            if index == 0 and name.startswith("ST"):
                strain -= (STUD_THERMAL_EXPANSION*VIRTUAL_PRELOAD_TEMPERATURE)*np.eye(3)
            elastic = .5*lame*np.trace(strain,axis1=1,axis2=2)**2 + shear*(strain**2).sum(axis=(1,2))
            totals[index] += vol @ elastic
    return [float(x) for x in totals]


def stress_summary(xyz,groups,faces,steps,share):
    pre,cycle,static=steps
    ranges=cycle["STRESS"]-pre["STRESS"]
    values=mises(static["STRESS"])
    eig=np.linalg.eigvalsh(stress_tensors((cycle["STRESS"]+pre["STRESS"])/2))
    tensile_mean=np.maximum(0.,eig[:,-1])
    eq_amp=mises(ranges)/2
    ans={}
    for name,elems in groups.items():
        rp,rm,cast=PROPS[name]
        active=np.unique([row for _,row in elems])
        tets=np.array([row for _,row in elems])
        # Fixed-plane vicinity and any simplified nut/shank intersection
        # are excluded from solid-material proof. Studs use a VDI force proof.
        candidates=active[xyz[active,2]>-77.]
        if name.startswith("ST"):
            candidates=candidates[(xyz[candidates,2]>-65.) & (xyz[candidates,2]<400.)]
        allow,mean=fatigue(rm,cast)
        norm=boundary_normals(xyz,faces[name],elems)
        principal_range=np.max(np.abs(np.linalg.eigvalsh(stress_tensors(ranges))),axis=1)
        grad=gradient(xyz,tets,norm,principal_range)
        support=notch_support(grad,rm,cast)
        eq=(eq_amp+mean*tensile_mean)/support
        ii=int(candidates[np.argmax(values[candidates])])
        jj=int(candidates[np.argmax(eq[candidates])])
        ans[name]=dict(static_MPa=float(values[ii]),static_xyz_mm=xyz[ii].tolist(),
                       static_factor=float(rp/values[ii]),
                       fatigue_factor=float(allow/eq[jj]),fatigue_xyz_mm=xyz[jj].tolist(),
                       gradient_per_mm=float(grad[jj]),n_sigma=float(support[jj]),
                       amplitude_MPa=float(eq_amp[jj]),tensile_mean_MPa=float(tensile_mean[jj]))
        points = stress_gauges(name)
        if points:
            selection = interpolator(xyz,elems,points)
            static_stress = [shape@static["STRESS"][tags] for tags,shape in selection]
            cycle_stress = [shape@ranges[tags] for tags,shape in selection]
            mean_stress = [shape@((cycle["STRESS"]+pre["STRESS"])/2)[tags] for tags,shape in selection]
            peaks = mises(np.array(static_stress))
            mean_gauge = np.maximum(0.,np.linalg.eigvalsh(stress_tensors(np.array(mean_stress)))[:,-1])
            proof_fatigue = allow/(mises(np.array(cycle_stress))/2+mean*mean_gauge)
            i = int(np.argmax(peaks))
            j = int(np.argmin(proof_fatigue))
            ans[name]["inboard_gauges"] = dict(static_MPa=float(peaks[i]), static_factor=float(rp/peaks[i]),
                fatigue_factor_n_sigma_1=float(proof_fatigue[j]), static_xyz_mm=list(points[i]),
                fatigue_xyz_mm=list(points[j]),count=len(points))
    return ans


def interpolator(xyz,elems,points):
    all_nodes=np.array([tags for _,tags in elems])
    vertices=xyz[all_nodes[:,:4]]
    centers=np.mean(vertices,axis=1)
    tree=cKDTree(centers)
    _,indices=tree.query(points,k=min(96,len(centers)))
    selections=[]
    for point,nearest in zip(points,indices):
        v=vertices[nearest]
        a=np.moveaxis(v[:,1:]-v[:,:1],1,2)
        b=point-v[:,0]
        linear=np.linalg.solve(a,b[...,None])[...,0]
        weights=np.c_[1-linear.sum(axis=1),linear]
        found=int(np.argmax(weights.min(axis=1)))
        if weights[found].min() < -.05:
            raise ValueError(f"No containing element for {point}: {weights[found]}")
        l,m,n,o=weights[found]
        shape=[l*(2*l-1),m*(2*m-1),n*(2*n-1),o*(2*o-1),4*l*m,4*m*n,4*n*l,4*l*o,4*m*o,4*n*o]
        selections.append((all_nodes[nearest[found]],shape if all_nodes.shape[1]==10 else weights[found]))
    return selections


def sections(xyz,groups,steps,share):
    from hand import b_case
    manual=b_case(LOAD,share)
    static=steps[2]["STRESS"]-steps[0]["STRESS"]
    result={}
    center_yoke = (YOKE_BOTTOM_MM+YOKE_TOP_MM)/2
    yoke_moment = manual["actual_portal_far_end_total_N"]*(189.-93.5)/2
    for name,key,point,axis,width,height,Z_nominal,M_manual in (
        ("RIGHT","key",(manual["key_moment_x_mm"],112.,220.+GAP_MM),0,64.,110.,66.*120.**2/6,
         manual["key_moment_Nmm"]),
        ("FRONT_YOKE","yoke",(231.,0.,center_yoke),1,47.8,139.8,48.*140.**2/6,
         yoke_moment)):
        nodes,weights=np.polynomial.legendre.leggauss(7)
        vectors=np.tile(point,(49,1))
        vectors[:,1-axis]+=np.repeat(nodes,7)*width/2
        vectors[:,2]+=np.tile(nodes,7)*height/2
        interpol=interpolator(xyz,groups[name],vectors)
        stress=np.array([np.dot(shape,static[tags,axis]) for tags,shape in interpol])
        area_weights=np.outer(weights,weights).ravel()*width*height/4
        moment=abs((area_weights*(vectors[:,2]-point[2]))@stress)
        nominal=moment/Z_nominal
        expected=M_manual/Z_nominal
        result[key]=dict(FEA_section_nominal_bending_MPa=float(nominal),manual_nominal_MPa=expected,
            relative_difference=abs(float(nominal)/expected-1),section_center_mm=list(point),
            stress_integrated_rectangular_core_mm=[width,height],nominal_section_modulus_mm3=Z_nominal,
            FEA_section_bending_moment_Nmm=float(moment),manual_moment_Nmm=M_manual)
    return result


def paired_sections(xyz, shoe, floor, left, right, pre, working):
    """Compare opposing surfaces at the same in-plane workpiece coordinates."""
    def values(rows, points, axes, transverse_axis, state):
        tags = np.unique([n for _, _, face in rows for n in face])
        evaluator = LinearNDInterpolator(xyz[tags][:, axes], state["DISP"][tags, transverse_axis])
        result = evaluator(points)
        if not np.all(np.isfinite(result)):
            raise ValueError("Loaded section outside the common evaluation surface")
        return result

    along = np.linspace(95., 197.5, 42)
    height_at = np.array([(x, y) for x in along for y in np.linspace(-73., 73., 29)])
    width_at = np.array([(x, z) for x in along for z in np.linspace(-59., -1., 15)])
    output = {}
    for label, case in (("preload", pre), ("300_bar", working)):
        height = values(shoe, height_at, [0,1], 2, case) - values(floor, height_at, [0,1], 2, case)
        width = values(right, width_at, [0,2], 1, case) - values(left, width_at, [0,2], 1, case)
        output[label] = (height, width)
    assembled = output["preload"]
    working = output["300_bar"]
    result = {}
    for label, data, before, grid in zip(("height", "width"), working, assembled, (height_at, width_at)):
        delta = data - before
        i = np.argmax(np.abs(data))
        result[label] = dict(change_from_design_at_300_mm=float(data[i]),
            change_from_preloaded_max_abs_mm=float(np.max(np.abs(delta))), location_mm=grid[i].tolist())
    return result


def stud_section_forces(xyz, groups, name, x, y, steps):
    """Recover axial force and bending moment of the elastic stud surrogate."""
    radius = np.sqrt(976./np.pi)
    ring = [(x + radius*.64*np.cos(t), y + radius*.64*np.sin(t))
            for t in np.arange(12)*2*np.pi/12]
    matrix = np.array([(1., a-x, b-y) for a,b in [(x,y), *ring]])
    inertia = np.pi*radius**4/4
    result = {}
    for z in (-55., 40., 180., 300., 385.):
        selection = interpolator(xyz,groups[name],[(a,b,z) for a,b in [(x,y), *ring]])
        moments = []
        for step in steps:
            axial = np.array([np.dot(shape,step["STRESS"][tags, 2]) for tags,shape in selection])
            s0,gx,gy = np.linalg.lstsq(matrix,axial,rcond=None)[0]
            moments.append(dict(axial_N=float(s0*976.), Mx_Nmm=float(inertia*gy),
                                My_Nmm=float(-inertia*gx)))
        result[str(z)] = moments
    return result


def interface_tractions(xyz, patches, steps):
    """Area and traction resultants on the housing side of the tied parting plane."""
    outputs = {}
    for label, rows in patches.items():
        if "POST" not in label:
            continue
        records = []
        tags = np.array([face[2] for face in rows])
        pts = xyz[tags]
        center = (pts.reshape(-1,3).min(axis=0) + pts.reshape(-1,3).max(axis=0))/2
        for step in steps:
            szz = step["STRESS"][tags, 2]
            area = total = tension_area = tension = 0.
            moment_Nmm = np.zeros(2)
            samples = []
            for shape, positions, weights in triangle_quadrature(pts):
                sigma = szz @ shape
                area += weights.sum()
                normal = sigma*weights
                total += normal.sum()
                tension_area += weights[sigma>0].sum()
                tension += np.maximum(sigma,0) @ weights
                moment_Nmm += ((positions[:,:2]-center[:2])*normal[:,None]).sum(axis=0)
                samples.extend(sigma.tolist())
            records.append(dict(area_mm2=float(area),normal_signed_N=float(total),
                tensile_area_fraction=float(tension_area/area),integrated_tension_N=float(tension),
                minimum_traction_MPa=float(min(samples)), maximum_traction_MPa=float(max(samples)),
                first_moment_xy_Nmm=moment_Nmm.tolist()))
        outputs[label] = records
    return outputs


def summarize(xyz,groups,faces,contacts_,pairs,steps,contact_forces,fixed,springs,f,share):
    pre,cycle,static=steps
    applied=1.05*f
    stab={n:-SPRING_N_MM*static["DISP"][tags].sum(axis=0) for n,tags in springs.items()}
    stability_force_N=sum(float(np.sum(np.linalg.norm(SPRING_N_MM*static["DISP"][tags],axis=1))) for tags in springs.values())
    boundary_N=static["FORC"][fixed].sum(axis=0)
    total_N=LOAD["force_315_N"]
    force_error=float(np.linalg.norm(boundary_N+sum(stab.values())+applied.sum(axis=0))/total_N)
    shoe_cf_N=sum(contact_forces[lock+"LOW"][2]["vector_N"][2] for lock in ("LEFT","RIGHT"))
    shoe_error=abs(total_N+stab["SHOE"][2]-abs(shoe_cf_N))/total_N
    studs={}
    for i,(x,y) in enumerate(TIE_CENTERS_MM,1):
        name=f"ST{i}"
        ids=np.array(sorted({n for _,_,face in plane(faces[name],xyz,2,-87.) for n in face}))
        studs[name]=dict(x_mm=x,y_mm=y,force_N=[float(np.sum(s["FORC"][ids,2])) for s in steps],
                         section_resultants=stud_section_forces(xyz,groups,name,x,y,steps))
    surfaces={}
    for slave,_ in pairs:
        tags=np.unique([n for _,_,n in contacts_[slave]])
        pressure_MPa=abs(static["CONTACT"][tags,3])
        proof=contact_forces[slave][2]
        mean=abs(proof["normal_N"])/proof["area_mm2"] if proof["area_mm2"] else None
        if slave.endswith("LOW"):
            xs, ys = (20.,45.,75.,105.,135.,160.,180.,193.), (87.,92.,97.,102.)
        else:
            xs = (-43.,-34.,-25.,-16.,-8.) if slave.endswith("BACK") else (215.,225.,235.,245.,250.)
            ys = (75.,84.,93.,103.,113.)
        sign = -1 if slave.startswith("LEFT") else 1
        gauge = [(x,sign*y) for x in xs for y in ys]
        xy = xyz[tags,:2]
        values = LinearNDInterpolator(xy,pressure_MPa)(gauge)
        sample = np.isfinite(values)
        inboard_index = int(np.nanargmax(values)) if any(sample) else None
        surfaces[slave]=dict(force_cases=contact_forces[slave],peak_pressure_MPa=float(pressure_MPa.max()),
            inboard_gauge_pressure_MPa=float(values[inboard_index]) if inboard_index is not None else None,
            inboard_gauge_max_xy_mm=list(gauge[inboard_index]) if inboard_index is not None else None,
            inboard_gauge_count=int(np.count_nonzero(sample)),
            mean_pressure_active_area_MPa=mean,
            max_penalty_overlap_at_peak_mm=float(pressure_MPa.max()/CONTACT_NORMAL_MPA_PER_MM),
            peak_location_mm=xyz[tags[int(np.argmax(pressure_MPa))]].tolist())
    foot=section(faces["SHOE"],xyz,2,0.)
    base=section(faces["HOUSING"],xyz,2,-60.,lambda p:abs(p[1])<75.)
    left=section(faces["HOUSING"],xyz,1,-75.,lambda p:-60.<p[2]<0.)
    right=section(faces["HOUSING"],xyz,1,75.,lambda p:-60.<p[2]<0.)
    def loaded_nodes(rows):
        return np.array(sorted({i for _,_,nodes in rows for i in nodes if 94.47<xyz[i,0]<=198.}))
    u=cycle["DISP"]
    foot_z=u[loaded_nodes(foot),2]
    base_z=u[loaded_nodes(base),2]
    left_y=u[loaded_nodes(left),1]
    right_y=u[loaded_nodes(right),1]
    energy = solid_strain_energy(xyz,groups,pre["DISP"],static["DISP"])
    spring_energy = sum(float(SPRING_N_MM/2*np.sum(static["DISP"][ids]**2)) for ids in springs.values())
    delta_spring_energy = sum(float(SPRING_N_MM/2*np.sum((static["DISP"]-pre["DISP"])[ids]**2))
                              for ids in springs.values())
    return dict(share=share, parts=stress_summary(xyz,groups,faces,steps,share),
                contact=surfaces,studs=studs,global_force_balance_fraction=force_error,
                shoe_force_balance_fraction=float(shoe_error),stabilizer_abs_N=stability_force_N,
                stabilizer_load_fraction=stability_force_N/total_N,
                stabilizer_elastic_energy_Nmm=spring_energy,
                stabilizer_increment_energy_Nmm=delta_spring_energy,
                elastic_solid_energy_Nmm=energy,
                stabilizer_stored_energy_fraction=(spring_energy/energy[0] if energy else None),
                stabilizer_increment_energy_fraction=(delta_spring_energy/energy[1] if energy else None),
                displacement_300_bar=dict(shoe_motion_mm=float(foot_z.max()),
                    section_width_upper_bound_mm=float(right_y.max()-left_y.min()),
                    section_height_upper_bound_mm=float(foot_z.max()-base_z.min())),
                paired_section_300_bar=paired_sections(xyz,foot,base,left,right,pre,cycle),
                tied_interface_traction=interface_tractions(xyz,contacts_,steps),
                manual_FEA_sections=sections(xyz,groups,steps,share))


def generated_mesh(level,folder,order):
    step=LEVELS_MM[level]
    mesh=folder/"portal.msh"
    tool([BIN/"gmsh.exe",HERE/"portal.geo","-3","-nt","1","-clmin",4.5-level*.6,"-clmax",step,
          "-setnumber","Mesh.MeshSizeFromCurvature",6+2*level,"-format","msh2","-o",mesh,"-v","3"],
         folder,folder/"gmsh.log",350)
    xyz,groups=mesh_data(mesh,order)
    faces=boundary_faces(groups)
    out,pairs,ties=contacts(xyz,faces)
    updated=crown_locks(xyz,groups)
    return updated,groups,faces,out,pairs,ties


def mesh_check(level,folder,order):
    xyz,groups,faces,surfaces,_,_=generated_mesh(level,folder,order)
    checks={}
    for name,elems in groups.items():
        ids=np.array([nodes for _,nodes in elems])
        corners=xyz[ids[:,:4]]
        jacobian=np.linalg.det(corners[:,1:]-corners[:,:1])
        assert min(jacobian)>0, name
        checks[name]=dict(elements=len(elems),min_corner_jacobian_mm3=float(min(jacobian)),
                          approximate_mesh_volume_mm3=float(jacobian.sum()/6))
    actual_loads={}
    shoe=np.unique([nodes for _,nodes in groups["SHOE"]])
    for share in SHARES:
        loads=loading(xyz,faces,share)
        f=loads[shoe,2]
        assert abs(f.sum()-LOAD["force_300_N"])<1e-6
        assert abs(xyz[shoe,0]@f/f.sum()-LOAD["centroid_x_mm"])<1e-8
        actual_loads[str(share)]=dict(shoe_force_N=float(f.sum()),axial_centroid_mm=float(xyz[shoe,0]@f/f.sum()),
                                      transverse_centroid_mm=float(xyz[shoe,1]@f/f.sum()),
                                      system_force_residual_N=loads.sum(axis=0).tolist())
    json_write(HERE/"mesh_check.json",dict(status="PASS_DIAGNOSTIC_MESH_AND_LOAD",max_mesh_mm=LEVELS_MM[level],
        element_order=order,nodes=len(xyz)-1,solids=checks,contact_faces={n:len(v) for n,v in surfaces.items()},
        load_quadrature=actual_loads))


def assess(job, xyz, groups, faces, out, pairs, fixed, springs, f, share, node_contact):
    steps=read_steps(job.with_suffix(".frd"),len(xyz))
    reactions=(integrate_nodal_pressures(xyz,groups,out,pairs,steps) if node_contact
               else read_forces(job.with_suffix(".dat"),pairs))
    return summarize(xyz,groups,faces,out,pairs,steps,reactions,fixed,springs,f,share)


def run_level(level,shares,folder,order,node_contact,linear_kinematics,post_only):
    step=LEVELS_MM[level]
    updated,groups,faces,out,pairs,ties=generated_mesh(level,folder,order)
    print(f"Gmsh h={step}: {len(updated)-1} nodes, {sum(map(len,groups.values()))} elements",flush=True)
    for share in shares:
        stem=f"portal_{level}_{round(100*share)}"
        job=folder/(stem+".inp")
        deck_for_build = job.with_name(f"rebuild_{job.name}") if post_only else job
        fixed,springs,f=make_deck(deck_for_build,folder/"mesh.inp",updated,groups,faces,out,pairs,ties,share,node_contact,linear_kinematics)
        if post_only:
            assert deck_for_build.read_bytes() == job.read_bytes(), f"Deck mismatch {job}"
        destination = HERE/(stem+".json") if CONTACT_NORMAL_MPA_PER_MM == 10000. else (
            HERE/f"penalty_{CONTACT_NORMAL_MPA_PER_MM:.0f}_{stem}.json")
        if level==0 and CONTACT_NORMAL_MPA_PER_MM == 10000.:
            (HERE/(stem+".inp")).write_bytes(job.read_bytes())
        logfile=folder/(stem+".log")
        if post_only:
            output=logfile.read_text(encoding="ascii",errors="replace")
        else:
            output=tool([BIN/"ccx.exe","-i",stem],folder,logfile,1500)
        if "Job finished" not in output:
            raise RuntimeError(output[-3000:])
        result=assess(job,updated,groups,faces,out,pairs,fixed,springs,f,share,node_contact)
        result.update(max_mesh_mm=step,nodes=len(updated)-1,elements=sum(map(len,groups.values())),
                      level=level,element_order=order,node_contact=node_contact,linear_kinematics=linear_kinematics,
                      normal_penalty_MPa_mm=CONTACT_NORMAL_MPA_PER_MM,
                      tangent_penalty_MPa_mm=CONTACT_TANGENT_MPA_PER_MM,
                      deck_sha256=sha256(job.read_bytes()).hexdigest(),
                      mesh_deck_sha256=sha256((folder/"mesh.inp").read_bytes()).hexdigest())
        json_write(destination,result)
        print(stem,result["global_force_balance_fraction"],result["displacement_300_bar"],flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("levels",type=int,choices=range(3),nargs="+")
    parser.add_argument("--share",type=float,choices=SHARES,action="append")
    parser.add_argument("--work",type=Path)
    parser.add_argument("--order",type=int,choices=(1,2),default=1)
    parser.add_argument("--node-contact",action="store_true")
    parser.add_argument("--linear-kinematics",action="store_true")
    parser.add_argument("--mesh-check",action="store_true")
    parser.add_argument("--post-only",action="store_true")
    parser.add_argument("--normal-penalty",type=float,default=CONTACT_NORMAL_MPA_PER_MM)
    args=parser.parse_args()
    CONTACT_NORMAL_MPA_PER_MM = args.normal_penalty
    build_geo(HERE/"portal.geo")
    for level in args.levels:
        def run(folder):
            if args.mesh_check:
                mesh_check(level,folder,args.order)
            else:
                run_level(level,args.share or SHARES,folder,args.order,args.node_contact,args.linear_kinematics,args.post_only)
        if args.work:
            args.work.mkdir(parents=True,exist_ok=True)
            run(args.work.resolve())
        else:
            with TemporaryDirectory(dir=HERE,prefix="portal_run_") as temp:
                run(Path(temp))
