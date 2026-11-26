"""Full-width structured gate and seat with a rigid backing outside the R20 aperture."""
import argparse
from itertools import product
from math import sqrt
from pathlib import Path
from tempfile import TemporaryDirectory

import contact as c
from contact_hex_slice import grid
import frame_fea as f
import numpy as np

HERE = Path(__file__).resolve().parent
MESH_MM = (9.,7.,5.5)


def structured_body(name,h_mm,node_offset,element_offset):
    if name=='blade':
        center_y_mm=-73.
        z0_mm,z1_mm=0.,38.
        anchors_x=(-130.,-92.,-79.,-75.,-72.,0.,72.,75.,79.,92.,130.)
        anchors_y=(-124.,-105.5,-102.5,-47.,-40.5,-37.5,-30.5,-30.,-27.,
                   0.,27.,30.,34.5,37.5,49.,88.)
        relief_side='back'
    else:
        center_y_mm=2.
        z0_mm,z1_mm=38.,93.
        anchors_x=(-170.,-130.,-92.,-79.,-75.,0.,75.,79.,92.,130.,170.)
        anchors_y=(-90.,-57.,-43.5,-40.5,-36.,-33.5,-30.5,0.,34.5,37.5,48.,88.,90.)
        relief_side='front'
    x,y,z=(grid(anchors_x,h_mm),grid(anchors_y,h_mm),
           grid((z0_mm,z0_mm+3.,z1_mm-3.,z1_mm),1.35*h_mm))
    geometry=np.stack(np.meshgrid(x,y,z,indexing='ij'),axis=-1)
    d=np.maximum(abs(x[:,None])-79.,abs(y[None,:]-center_y_mm)-32.5)
    blend=(z-z0_mm)/(z1_mm-z0_mm)
    if relief_side=='back':
        edge=np.minimum(130.-abs(x[:,None]),106.-abs(y[None,:]+18.))
        geometry[:,:,:,2] -= c.ease(np.minimum(d,edge))[:,:,None]*blend[None,None,:]**4
    else:
        geometry[:,:,:,2] += c.ease(d)[:,:,None]*(1.-blend[None,None,:])**4
    dims=geometry.shape[:3]
    ids=np.arange(node_offset+1,node_offset+1+np.prod(dims)).reshape(dims)
    nx,ny,nz=np.array(dims)-1
    xx=(x[:-1]+x[1:])/2
    yy=(y[:-1]+y[1:])/2
    open_cells=(abs(xx[:,None])<79.)&(abs(yy[None,:]-center_y_mm)<32.5)
    kept=np.repeat((~open_cells)[:,:,None],nz,axis=2)
    el=np.zeros_like(kept,dtype=int)
    el[kept]=np.arange(element_offset+1,element_offset+1+kept.sum())
    conn=np.stack([ids[i:i+nx,j:j+ny,k:k+nz] for i,j,k in
                   ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))],axis=-1)
    used=np.unique(conn[kept])
    xyz=geometry.reshape(-1,3)
    lines=['*NODE']
    lines += [f'{tag},'+','.join(f'{value:.10g}' for value in xyz[tag-node_offset-1]) for tag in used]
    lines += [f'*ELEMENT,TYPE=C3D8I,ELSET={name}']
    lines += [f'{tag},'+','.join(map(str,row)) for tag,row in zip(el[kept],conn[kept],strict=True)]
    layer,face=(-1,'S2') if name=='blade' else (0,'S1')
    surf=el[:,:,layer]
    if name=='seat':
        surf=np.where((abs(xx[:,None])<135.)&(yy[None,:]<89.),surf,0)
    lines += [f'*SURFACE,TYPE=ELEMENT,NAME={name}_contact']
    lines += [f'{tag},{face}' for tag in surf[surf>0].ravel()]
    return lines,(ids,geometry,used,el),ids.size,int(kept.sum())


def distribution(part):
    ids,xyz,_,_=part
    x=xyz[:,0,0,0]
    y=xyz[0,:,0,1]
    q=np.zeros((ids.size+1,3))
    indices=np.flatnonzero((abs((x[1:]+x[:-1])/2)<75.))
    vertical=np.flatnonzero((abs((y[1:]+y[:-1])/2)<30.))
    for i,j in product(indices,vertical):
        da=(x[i+1]-x[i])*(y[j+1]-y[j])
        for u,v in product((-1/sqrt(3),1/sqrt(3)),repeat=2):
            x_mm=(x[i]+x[i+1]+u*(x[i+1]-x[i]))/2
            y_mm=(y[j]+y[j+1]+v*(y[j+1]-y[j]))/2
            w=da/4*f.smooth_edge(75.-abs(x_mm),3.)*f.smooth_edge(30.-abs(y_mm),3.)
            for a,b in product((0,1),repeat=2):
                q[ids[i+a,j+b,0]] += w*(1+(2*a-1)*u)*(1+(2*b-1)*v)/4*np.array([1.,x_mm,y_mm])
    xy=xyz.reshape(-1,3)[:,:2]
    equilibrium=np.vstack((np.ones(ids.size+1),np.vstack(([0.,0.],xy)).T))@q
    return q@np.linalg.solve(equilibrium,[1.,10.,-10.])


def solve(level):
    h_mm=MESH_MM[level]
    blade_lines,blade,bn,be=structured_body('blade',h_mm,0,0)
    seat_lines,seat,sn,se=structured_body('seat',h_mm,bn,be)
    lines=['*HEADING','T-1.7c | full-width rigid backed seat screen | N, mm, MPa',*blade_lines,*seat_lines]
    lines += ['*MATERIAL,NAME=STEEL','*ELASTIC','210000,.30',
              '*SOLID SECTION,ELSET=blade,MATERIAL=STEEL','*SOLID SECTION,ELSET=seat,MATERIAL=STEEL',
              '*SURFACE INTERACTION,NAME=OILED','*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR','50000.,1.',
              '*FRICTION','.15,10000.','*CONTACT PAIR,INTERACTION=OILED,TYPE=SURFACE TO SURFACE',
              'seat_contact,blade_contact']
    ids,xyz,used,_=seat
    x_mm,y_mm=xyz[:,:,-1,:2].transpose(2,0,1)
    cast_bearing=c.rounded_distance(x_mm,y_mm,176.,74.,20.)>=0.
    fixed=np.intersect1d(ids[:,:,-1][cast_bearing],used)
    lines += c.set_lines('RIGID_CAST',fixed)
    ids,xyz,used,_=blade
    anchor_indices=[np.linalg.norm(xyz.reshape(-1,3)-[x,0,0],axis=1).argmin()
                    for x in (-106.,106.)]
    tags=ids.ravel()[anchor_indices]
    lines += ['*BOUNDARY','RIGID_CAST,1,3',f'{tags[0]},1,2',f'{tags[1]},2,2',
              '*STEP,INC=80','*STATIC,SOLVER=ITERATIVE SCALING','.5,1.,1.e-6,.5','*CLOAD']
    load=distribution(blade)
    total=bn+sn+1
    loads={}
    stresses={}
    print(f'local {level}: {bn+sn} nodes, {be+se} elements',flush=True)
    with TemporaryDirectory(prefix=f'local_{level}_') as directory:
        work=Path(directory)
        for label,force in (('static',c.STATIC_N),('fatigue',c.CYCLIC_N)):
            loading=[f'{i},3,{force*load[i]:.12g}' for i in np.flatnonzero(load)]
            loading += ['*NODE FILE,FREQUENCY=999999','U,RF','*EL FILE,FREQUENCY=999999','S',
                        '*CONTACT FILE,FREQUENCY=999999','CDIS,CSTR','*END STEP']
            inp=work/'local.inp'
            inp.write_text('\n'.join(lines+loading)+'\n',encoding='ascii',newline='\n')
            if level==0:
                archive=['*HEADING',lines[1],'*INCLUDE,INPUT=structured_mesh_and_surfaces.inc']
                archive += lines[lines.index('*MATERIAL,NAME=STEEL'):]+loading
                (HERE/f'local_{label}.inp').write_text('\n'.join(archive)+'\n',encoding='ascii',newline='\n')
            f.run_tool([f.BIN/'ccx.exe','-i','local'],work,'Job finished')
            frd=work/'local.frd'
            data=f.results_frd(frd,total)
            p=c.contact_values(frd,total)
            reactions=data['FORC'][fixed,2]
            reaction_N=float(reactions.sum())
            error=abs(force+reaction_N)/force
            if error>.01:
                raise ValueError(f'Reaction force error {error:.3%}')
            loads[label]=dict(force_N=force,reaction_N=reaction_N,relative_reaction_error=error,
                              max_contact_MPa=float(p.max()),bearing_screen_MPa=c.BEARING_SCREEN_MPA)
            stresses[label]=data['STRESS']
            print(level,label,loads[label],flush=True)
    regions={}
    strength,kR,jG,slope=f.fkm_parameters(1000.,6.3,False,forging=True)
    for name,part,offset in (('blade',blade,0),('seat',seat,bn)):
        _,xyz,used,_=part
        static=f.mises(stresses['static'][used])
        fatigue=stresses['fatigue'][used]
        tension=np.linalg.eigvalsh(f.stress_tensors(fatigue))[:,-1]
        util=(f.mises(fatigue)+slope*np.maximum(0.,tension))/2/strength
        pts=xyz.reshape(-1,3)[used-offset-1]
        regions[name]=dict(static_factor=float(800./static.max()),fatigue_factor=float(1./util.max()),n_sigma=1.,
                           static_xyz_mm=pts[static.argmax()].tolist(),fatigue_xyz_mm=pts[util.argmax()].tolist())
    data=dict(scope='Full-width window and seat, squared macro corners, rigid cast backing outside R20. Diagnostic.',
              mesh_mm=h_mm,nodes=bn+sn,elements=be+se,load_eccentricity_mm=[10.,-10.],
              loads=loads,regions=regions)
    f.write_json(HERE/f'local_{level}.json',data)
    print(regions,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('levels',nargs='+',type=int,choices=range(len(MESH_MM)))
    for level in parser.parse_args().levels:
        solve(level)
