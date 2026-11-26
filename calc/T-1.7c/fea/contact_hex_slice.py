"""Small structured CCX slice used to separate mesh and contact failures."""
import argparse
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


def solve(level):
    h_mm=MESH_MM[level]
    floor=-30.5
    ceiling=34.5
    open_edge=-40.5
    cases=[
        ('blade',(open_edge,open_edge+3,floor,-30,-27,0,27,30,ceiling,ceiling+3,88.),(0.,c.THICK_MM),None),
        ('lower',(-85.,open_edge,open_edge+3,floor-3,floor),(c.THICK_MM,c.THICK_MM+c.SEAT_DEPTH_MM),floor),
        ('upper',(ceiling,ceiling+3,85.),(c.THICK_MM,c.THICK_MM+c.SEAT_DEPTH_MM),ceiling),
    ]
    parts={}
    nn=ne=0
    nodes=['*NODE']
    elements=[]
    boundaries=[]
    for name,y,z,edge in cases:
        x=np.array([0.,WIDTH_MM/2,WIDTH_MM])
        y=grid(y,h_mm)
        z=grid(z,h_mm)
        xyz=np.stack(np.meshgrid(x,y,z,indexing='ij'),axis=-1)
        if name=='blade':
            xyz[:,:,:,2] -= c.ease(y-open_edge)[None,:,None]*(z/c.THICK_MM)[None,None,:]**4
        else:
            xyz[:,:,:,2] += c.ease(abs(y-edge))[None,:,None]*((z[-1]-z)/(z[-1]-z[0]))[None,None,:]**4
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
    with TemporaryDirectory(prefix=f'hex_{level}_') as directory:
        work=Path(directory)
        for label,force in (('static',c.STATIC_N),('fatigue',c.CYCLIC_N)):
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
            stresses[label]=data['STRESS']
            print(level,label,loads[label],flush=True)
    regions={}
    strength,kR,jG,M=f.fkm_parameters(1000.,6.3,False,forging=True)
    for name,(ids,xyz,_) in parts.items():
        static=f.mises(stresses['static'][ids.ravel()])
        fatigue=stresses['fatigue'][ids.ravel()]
        tension=np.linalg.eigvalsh(f.stress_tensors(fatigue))[:,-1]
        util=(f.mises(fatigue)+M*np.maximum(0.,tension))/2/strength
        pts=xyz.reshape(-1,3)
        regions[name]=dict(static_factor=float(800./static.max()),fatigue_factor=float(1./util.max()),n_sigma=1.,
                           static_xyz_mm=pts[static.argmax()].tolist(),fatigue_xyz_mm=pts[util.argmax()].tolist())
    data=dict(scope='Plane strain slice, 3D elements, no lateral load spreading, seat back fixed; diagnostic only.',
              mesh_mm=h_mm,nodes=nn,elements=ne,loads=loads,regions=regions)
    f.write_json(HERE/f'hex_slice_{level}.json',data)
    print(regions,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('levels',type=int,nargs='+',choices=range(len(MESH_MM)))
    for level in p.parse_args().levels:
        solve(level)
