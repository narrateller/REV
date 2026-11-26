"""Small structured CCX slice used to separate mesh and contact failures."""
import argparse
from dataclasses import dataclass
from itertools import product
from math import ceil, sqrt
from pathlib import Path
from tempfile import TemporaryDirectory

import contact as c
import frame_fea as f
import numpy as np

HERE = Path(__file__).resolve().parent
WIDTH_MM = 12.
MESH_MM = (5.,3.5,2.5)


def grid(breaks, h_mm):
    return np.concatenate([np.linspace(start,end,ceil((end-start)/h_mm),endpoint=False)
                           for start,end in zip(breaks,breaks[1:])] + [[breaks[-1]]])


@dataclass(frozen=True)
class Slice:
    label: str
    thickness_mm: float = 38.
    travel_mm: float = 75.
    relief_depth_mm: float = .035
    relief_length_mm: float = 3.
    wing_thickness_mm: float = 0.


def solve(level, case, load_cases=('static','fatigue')):
    h_mm=MESH_MM[level]
    floor=-30.5
    ceiling=34.5
    open_edge=ceiling-case.travel_mm
    runout_mm=case.relief_length_mm
    thickness_mm=case.thickness_mm
    cases=[
        ('blade',(open_edge,open_edge+3,floor,-30,-27,0,27,30,ceiling,ceiling+3,88.),(0.,thickness_mm),None),
        ('lower',(-100.,open_edge,open_edge+3,floor-runout_mm,floor),(thickness_mm,thickness_mm+c.SEAT_DEPTH_MM),floor),
        ('upper',(ceiling,ceiling+runout_mm,85.),(thickness_mm,thickness_mm+c.SEAT_DEPTH_MM),ceiling),
    ]
    parts={}
    nn=ne=0
    nodes=['*NODE']
    elements=[]
    boundaries=[]
    for name,y,z,edge in cases:
        x=np.array([0.,WIDTH_MM/2,WIDTH_MM])
        y=grid(sorted(set(y)),h_mm)
        z=grid(z,h_mm)
        xyz=np.stack(np.meshgrid(x,y,z,indexing='ij'),axis=-1)
        if name=='blade':
            xyz[:,:,:,2] -= c.ease(y-open_edge)[None,:,None]*(z/thickness_mm)[None,None,:]**4
            q=np.maximum(np.clip((floor-y)/12.,0.,1.),np.clip((y-ceiling)/12.,0.,1.))
            xyz[:,:,:,2] -= case.wing_thickness_mm*(q*q*(3.-2.*q))[None,:,None]*(1.-z/thickness_mm)[None,None,:]
        else:
            relief=case.relief_depth_mm*np.clip(1.-abs(y-edge)/runout_mm,0.,1.)**2
            xyz[:,:,:,2] += relief[None,:,None]*((z[-1]-z)/(z[-1]-z[0]))[None,None,:]**4
        dims=xyz.shape[:3]
        ids=np.arange(nn+1,nn+1+np.prod(dims)).reshape(dims)
        nx,ny,nz=np.array(dims)-1
        el=np.arange(ne+1,ne+1+nx*ny*nz).reshape((nx,ny,nz))
        conn=np.stack([ids[i:i+nx,j:j+ny,k:k+nz] for i,j,k in
                      ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))],axis=-1)
        for n,coord in zip(ids.ravel(),xyz.reshape(-1,3),strict=True):
            nodes.append(f'{n},'+','.join(f'{v:.10g}' for v in coord))
        elements.append(f'*ELEMENT,TYPE=C3D8I,ELSET={name}')
        elements.extend(f'{tag},'+','.join(map(str,row))
                        for tag,row in zip(el.ravel(),conn.reshape(-1,8),strict=True))
        parts[name]=(ids,xyz,el)
        boundaries.extend((ids[0,:,:].ravel(), ids[-1,:,:].ravel()))
        nn+=ids.size
        ne+=el.size
    lines=['*HEADING','T-1.7c plane strain 3D strip | N, mm, MPa',*nodes,*elements]
    lines += ['*SURFACE,TYPE=ELEMENT,NAME=BLADE_BACK']
    lines += [f'{n},S2' for n in parts['blade'][2][:,:,-1].ravel()]
    lines += ['*SURFACE,TYPE=ELEMENT,NAME=SEAT_FRONT']
    lines += [f'{n},S1' for name in ('lower','upper') for n in parts[name][2][:,:,0].ravel()]
    lines += [
        '*MATERIAL,NAME=STEEL','*ELASTIC','210000,.30',
        *[f'*SOLID SECTION,ELSET={name},MATERIAL=STEEL' for name in parts],
        '*SURFACE INTERACTION,NAME=OILED','*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR','50000.,1.',
        '*FRICTION','.15,10000.','*CONTACT PAIR,INTERACTION=OILED,TYPE=SURFACE TO SURFACE','SEAT_FRONT,BLADE_BACK',
    ]
    lines += c.set_lines('PLANE_STRAIN',np.unique(np.concatenate(boundaries)))
    fixed=np.concatenate([parts[name][0][:,:,-1].ravel() for name in ('lower','upper')])
    lines += c.set_lines('SEAT_BACK',fixed)
    ids,xyz,_=parts['blade']
    y=xyz[0,:,0,1]
    x=xyz[:,0,0,0]
    pin=ids[1,np.argmin(abs(y)),0]
    lines += ['*BOUNDARY','PLANE_STRAIN,1,1','SEAT_BACK,2,3',f'{pin},2,2',
              '*STEP,INC=100','*STATIC,SOLVER=ITERATIVE SCALING','.5,1.,1.e-7,.5','*CLOAD']
    q=np.zeros((nn+1,2))
    for i,j in product(range(len(x)-1),range(len(y)-1)):
        if y[j]<-30 or y[j+1]>30:
            continue
        da=(x[i+1]-x[i])*(y[j+1]-y[j])
        for u,v in product((-1/sqrt(3),1/sqrt(3)),repeat=2):
            y_mm=(y[j]+y[j+1]+v*(y[j+1]-y[j]))/2
            w=da/4 * f.smooth_edge(30-abs(y_mm),3.)
            for a,b in product((0,1),repeat=2):
                q[ids[i+a,j+b,0]] += w*(1+(2*a-1)*u)*(1+(2*b-1)*v)/4 * np.array([1.,y_mm])
    print(f'hex slice {level}: {nn} nodes, {ne} elements',flush=True)
    loads={}
    stresses={}
    with TemporaryDirectory(prefix=f'hex_{level}_',dir=HERE) as directory:
        work=Path(directory)
        for label,force in (('static',c.STATIC_N),('fatigue',c.CYCLIC_N)):
            if label not in load_cases:
                continue
            yi=np.zeros(nn+1)
            yi[ids.ravel()]=xyz[:,:,:,1].ravel()
            scale=q@np.linalg.solve(np.vstack((np.ones(nn+1),yi))@q,[1.,-10.])
            applied_N=force*WIDTH_MM/150
            loading=[f'{n},3,{applied_N*scale[n]:.12g}' for n in np.flatnonzero(scale)]
            loading += ['*NODE FILE,FREQUENCY=999999','U,RF','*EL FILE,FREQUENCY=999999','S',
                        '*CONTACT FILE,FREQUENCY=999999','CDIS,CSTR','*END STEP']
            (work/'slice.inp').write_text('\n'.join(lines+loading)+'\n',encoding='ascii',newline='\n')
            f.run_tool([f.BIN/'ccx.exe','-i','slice'],work,'Job finished')
            frd=work/'slice.frd'
            data=f.results_frd(frd,nn+1)
            p=c.contact_values(frd,nn+1)
            reaction_N=float(data['FORC'][fixed,2].sum())
            error=abs(applied_N+reaction_N)/applied_N
            if error>.01:
                raise ValueError(f'Reaction force error {error:.3%}')
            loads[label]=dict(reaction_N=reaction_N,force_N=applied_N,relative_reaction_error=error,
                              contact_pressure_MPa=float(p.max()))
            if label=='static':
                loads[label]['pressure_along_seat_MPa']={
                    name:[[float(y),float(value)] for y,value in zip(
                        xyz[0,:,0,1],p[ids[1,:,0]],strict=True) if value>0]
                    for name,(ids,xyz,_) in parts.items() if name!='blade'}
            stresses[label]=data['STRESS']
            print(level,label,loads[label],flush=True)
    regions={}
    strength,kR,jG,M=f.fkm_parameters(1000.,6.3,False,forging=True)
    for name,(ids,xyz,_) in parts.items():
        static=f.mises(stresses['static'][ids.ravel()])
        if 'fatigue' not in stresses:
            regions[name]={'static_factor':float(800./static.max())}
            continue
        fatigue=stresses['fatigue'][ids.ravel()]
        tension=np.linalg.eigvalsh(f.stress_tensors(fatigue))[:,-1]
        util=(f.mises(fatigue)+M*np.maximum(0.,tension))/2/strength
        pts=xyz.reshape(-1,3)
        regions[name]=dict(static_factor=float(800./static.max()),fatigue_factor=float(1./util.max()),n_sigma=1.,
                           static_xyz_mm=pts[static.argmax()].tolist(),fatigue_xyz_mm=pts[util.argmax()].tolist())
    r2_regions = {}
    if case.label.startswith('r2_') and 'fatigue' in stresses:
        from r2_strength import fatigue, summarize
        for name,(ids,xyz,_) in parts.items():
            vm_range = np.abs(np.linalg.eigvalsh(f.stress_tensors(stresses['fatigue'][ids.ravel()]))).max(axis=-1).reshape(ids.shape)
            gradient = np.zeros_like(vm_range)
            for surface, interior in ((0, 1), (-1, -2)):
                z = xyz[:, :, :, 2]
                gradient[:, :, surface] = np.maximum(
                    0., (vm_range[:, :, surface]-vm_range[:, :, interior]) /
                    (abs(z[:, :, surface]-z[:, :, interior])*np.maximum(vm_range[:, :, surface], 1e-6)))
            for surface, interior in ((0, 1), (-1, -2)):
                y = xyz[:, :, :, 1]
                gradient[:, surface, :] = np.maximum(
                    gradient[:, surface, :],
                    (vm_range[:, surface, :]-vm_range[:, interior, :]) /
                    (abs(y[:, surface, :]-y[:, interior, :])*np.maximum(vm_range[:, surface, :], 1e-6)))
            static, cyclic = (stresses[label][ids.ravel()] for label in ('static', 'fatigue'))
            fatigue_values = fatigue(static, np.zeros_like(cyclic), cyclic, gradient.ravel(), 800., 1000.)
            r2_regions[name] = summarize(fatigue_values, xyz.reshape(-1, 3), np.ones(ids.size, dtype=bool))
    data=dict(scope='Plane strain slice, 3D elements, no lateral load spreading, seat back fixed; diagnostic only.',
              geometry=vars(case),mesh_mm=h_mm,nodes=nn,elements=ne,loads=loads,regions=regions, **({"r2_regions": r2_regions} if r2_regions else {}))
    f.write_json(HERE/f'{case.label}_slice_{level}.json',data)
    print(regions,flush=True)
    return data


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('levels',type=int,nargs='+',choices=range(len(MESH_MM)))
    p.add_argument('--label',default='base')
    p.add_argument('--thickness',type=float,default=38.)
    p.add_argument('--travel',type=float,default=75.)
    p.add_argument('--relief-depth',type=float,default=.035)
    p.add_argument('--relief-length',type=float,default=3.)
    p.add_argument('--wing-thickness',type=float,default=0.)
    p.add_argument('--static-only',action='store_true')
    args=p.parse_args()
    case=Slice(args.label,args.thickness,args.travel,args.relief_depth,args.relief_length,args.wing_thickness)
    for level in args.levels:
        solve(level,case,('static',) if args.static_only else ('static','fatigue'))
