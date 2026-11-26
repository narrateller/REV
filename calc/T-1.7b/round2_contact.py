"""Closed-gate contact screen. Bring the backed insert to the gate locally."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from shutil import copyfile
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from scipy.interpolate import LinearNDInterpolator

import frame_analytic as a
import frame_fea as f
import gate_contact as g
from frame_geometry import Geo, rounded_box

THICK_mm = 38.
WIDTH_mm = 220.
HEIGHT_mm = 86.
CROWN_WIDTH_mm = 3.
CROWN_DEPTH_mm = .06
MESH_mm = ((10., 4.5), (8., 3.4), (6.5, 2.6))
SEAT_BACK_mm = THICK_mm+a.ADAPTER_mm


def seat_geo(h_mm, near_mm):
    geo = Geo()
    geo.emit(f'Box(1) = {{-170,-90,{THICK_mm},340,180,{a.ADAPTER_mm}}};')
    rounded_box(geo,0.,0.,a.OUTLET_WIDTH_mm/2,a.OUTLET_HEIGHT_mm/2,a.OUTLET_RADIUS_mm,
                THICK_mm-1.,a.ADAPTER_mm+2.,0.,'outlet')
    geo.cut('1',['outlet'],'seat')
    geo.emit(f'Mesh.MeshSizeMax={h_mm}; Mesh.MeshSizeFromPoints=0; Mesh.MeshSizeFromCurvature=12;')
    geo.emit('Mesh.MeshSizeExtendFromBoundary=0; Mesh.SecondOrderLinear=1; Mesh.RandomSeed=42; Mesh.MaxNumThreads3D=1;')
    distance = 'Max(Abs(z-38),Min(Abs(Abs(y)-37),Abs(Abs(x)-88)))'
    geo.emit(f'Field[1]=MathEval; Field[1].F="{near_mm}+({h_mm}-{near_mm})*Min(1,({distance}/12))"; Background Field=1;')
    return '\n'.join(geo.lines)+'\n'


def aperture_distance_mm(x,y):
    u,v = abs(x)-68.,abs(y)-17.
    return np.hypot(np.maximum(u,0.),np.maximum(v,0.))+np.minimum(np.maximum(u,v),0.)-20.


def ease(d_mm):
    return CROWN_DEPTH_mm*np.clip(1.-d_mm/CROWN_WIDTH_mm,0.,1.)**2


def blade_model(h_mm, crown):
    x = g.grid((-110.,-107.,-88.,-75.,-68.,0.,68.,75.,88.,107.,110.), h_mm)
    y = g.grid((-43.,-40.,-37.,-30.,0.,30.,37.,40.,43.), h_mm)
    z = g.grid((0.,8.,30.,THICK_mm),h_mm)
    xyz = np.stack(np.meshgrid(x,y,z,indexing='ij'),axis=-1)
    if crown:
        d_mm = np.minimum(WIDTH_mm/2-abs(x),HEIGHT_mm/2-abs(y[:,None])).T
        xyz[:,:,:,2] -= ease(d_mm)[:,:,None]*(z/THICK_mm)**4
    ids = np.arange(1,1+np.prod(xyz.shape[:3])).reshape(xyz.shape[:3])
    shape = np.array(ids.shape)-1
    elements = np.arange(1,1+np.prod(shape)).reshape(shape)
    return g.Body('blade',ids,xyz,elements)


def write_model(folder, stem, level, crown):
    h_mm, near_mm = MESH_mm[level]
    blade = blade_model(near_mm*1.35,crown)
    path = folder/(stem+'.geo')
    path.write_text(seat_geo(h_mm,near_mm),encoding='ascii')
    (f.FEA/path.name).write_bytes(path.read_bytes())
    mesh = path.with_suffix('.msh')
    f.run_tool([f.BIN/'gmsh.exe',path.name,'-3','-order','2','-format','msh2',
                '-o',mesh.name,'-nt','1','-nopopup'],folder,'Done writing')
    xyz,tets,active,faces = f.read_mesh(mesh)
    contact = f.plane_triangles(xyz,faces,2,THICK_mm)
    seat_back = np.unique(f.plane_triangles(xyz,faces,2,SEAT_BACK_mm))
    arcs = [f.round_surface(xyz,faces,sx*68.,sy*17.,20.) for sx in (-1,1) for sy in (-1,1)]
    if crown:
        xyz[active,2] += ease(aperture_distance_mm(xyz[active,0],xyz[active,1]))*(
            1.-(xyz[active,2]-THICK_mm)/a.ADAPTER_mm)**4
    n = blade.ids.size
    seat_mesh = folder/'round2_seat_mesh.inp'
    g.write_mesh(folder/'round2_blade_mesh.inp',[blade],first_fixed=1)
    contact_region = (abs(xyz[contact,0]).min(axis=1)<WIDTH_mm/2+3)
    contact_region &= abs(xyz[contact,1]).min(axis=1)<HEIGHT_mm/2+3
    contact = contact[contact_region]
    contact_vertices = {tuple(sorted(face[:3])) for face in contact}
    surface_rows = []
    with seat_mesh.open('w',encoding='ascii') as out:
        out.write('*NODE\n')
        for tag in active:
            x,y,z = xyz[tag]
            out.write(f'{tag+n},{x:.10g},{y:.10g},{z:.10g}\n')
        out.write('*ELEMENT,TYPE=C3D10,ELSET=SEAT\n')
        for tag,tet in enumerate(tets,blade.elements.size+1):
            out.write(f'{tag},'+','.join(map(str,tet+n))+'\n')
            for side,v in enumerate(((0,1,2),(0,3,1),(1,3,2),(2,3,0)),1):
                if tuple(sorted(tet[list(v)])) in contact_vertices:
                    surface_rows.append(f'{tag},S{side}')
    assert len(surface_rows)==len(contact)
    sidecar = folder/(stem+'_surfaces.inp')
    with sidecar.open('w',encoding='ascii') as out:
        out.write('*SURFACE,TYPE=ELEMENT,NAME=SEAT_FRONT\n'+'\n'.join(surface_rows)+'\n*NSET,NSET=CAST_BACK\n')
        for i in range(0,len(seat_back),16):
            out.write(','.join(map(str,seat_back[i:i+16]+n))+'\n')
    if level==0 and crown:
        (f.FEA/sidecar.name).write_bytes(sidecar.read_bytes())
    arc_ids = np.unique(np.concatenate(arcs))
    arc_ids = arc_ids[(abs(xyz[arc_ids,0])>=68.-1e-6)&(abs(xyz[arc_ids,1])>=17.-1e-6)]
    return blade,xyz,tets,active,faces,np.unique(contact),seat_back,arc_ids,sidecar.name


def deck(path, blade, sidecar, force_N):
    lines = ['*HEADING','T-1.7b R2 | backed R20 seat | N, mm, MPa',
             '*INCLUDE,INPUT=round2_blade_mesh.inp','*INCLUDE,INPUT=round2_seat_mesh.inp',
             f'*INCLUDE,INPUT={sidecar}','*MATERIAL,NAME=STEEL','*ELASTIC',f'{a.E_MPa},{a.NU}',
             '*SOLID SECTION,ELSET=BLADE,MATERIAL=STEEL','*SOLID SECTION,ELSET=SEAT,MATERIAL=STEEL',
             '*SURFACE INTERACTION,NAME=OILED_STEEL','*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR',
             f'{g.PENALTY_MPa_mm},1.','*FRICTION',f'{g.FRICTION},10000.',
             '*CONTACT PAIR,INTERACTION=OILED_STEEL,TYPE=SURFACE TO SURFACE','SEAT_FRONT,BLADE_BACK']
    _,ny,nz = blade.ids.shape
    j = [ny//4, ny-1-ny//4]
    k = [nz//4, nz-1-nz//4]
    for dof,i in ((1,blade.ids.shape[0]//2),(2,0),(2,-1)):
        tags = blade.ids[i][np.ix_(j,k)].ravel()
        lines.extend(('*EQUATION',str(len(tags))))
        terms = [f'{tag},{dof},{1/len(tags):.12g}' for tag in tags]
        lines.extend(','.join(terms[i:i+3]) for i in range(0,len(terms),3))
    lines += ['*BOUNDARY','CAST_BACK,1,3','*STEP,INC=120','*STATIC,SOLVER=ITERATIVE SCALING','.5,1.,1.e-6,.5','*CLOAD']
    load = g.pressure_weights(blade,(a.ECC_mm,a.ECC_mm))
    lines.extend(f'{i},3,{force_N*load[i]:.12g}' for i in np.flatnonzero(load))
    lines += ['*NODE FILE,FREQUENCY=999999','U,RF','*EL FILE,FREQUENCY=999999','S',
              '*CONTACT FILE,FREQUENCY=999999','CDIS,CSTR','*END STEP']
    path.write_text('\n'.join(lines)+'\n',encoding='ascii')


def contact_summary(path, xyz, ids, n):
    data = {}
    contact = False
    with path.open(encoding='ascii') as stream:
        for line in stream:
            if line.startswith(' -4'):
                contact = line.split()[1]=='CONTACT'
                if contact:
                    data.clear()
            if line.startswith(' -1') and contact:
                data[int(line[3:13])] = float(line[49:61])
    p_MPa = np.array([data.get(i+n,0.) for i in ids])
    i = p_MPa.argmax()
    return {'pressure_peak_MPa':float(p_MPa[i]),'xyz_mm':xyz[ids[i]].tolist(),
            'pressure_positive_node_count':int(np.count_nonzero(p_MPa>0.))}


def deformation(blade, xyz, seat, rear, response, force_N):
    n = blade.ids.size
    u = response['DISP']
    reaction_N = response['FORC'][rear+n,2]
    np.testing.assert_allclose(reaction_N.sum(),-force_N,rtol=.003)
    loaded = blade.ids[:,:,0][(abs(blade.xyz[:,:,0,0])<=75)&(abs(blade.xyz[:,:,0,1])<=30)]
    ids = blade.ids[:,:,-1]
    moved = blade.xyz[:,:,-1]+u[ids]
    blade_z = LinearNDInterpolator(moved[:,:,:2].reshape(-1,2),moved[:,:,2].ravel())
    support = xyz[seat]+u[seat+n]
    m = (abs(xyz[seat,0])<WIDTH_mm/2-.5)&(abs(xyz[seat,1])<HEIGHT_mm/2-.5)
    gap_mm = support[m,2]-blade_z(support[m,:2])
    return {'force_N':force_N,'axial_reaction_N':float(reaction_N.sum()),
            'reaction_first_moments_Nmm':(reaction_N@xyz[rear,:2]).tolist(),
            'blade_axial_displacement_max_mm':float(u[loaded,2].max()),
            'seat_blade_gap_max_mm':float(np.nanmax(gap_mm))}


def proof(ids,xyz,static,fatigue,support):
    vm = f.mises(static)
    principal_MPa = np.linalg.eigvalsh(f.stress_tensors(fatigue))
    allow_MPa,kR,_,slope = f.fkm_parameters(1000.,6.3,False,forging=True)
    alternating_MPa = f.mises(fatigue)/2
    util = (alternating_MPa+slope*np.maximum(0.,principal_MPa[:,-1]/2))/(allow_MPa*support)
    i,j = ids[np.argmax(vm[ids])],ids[np.argmax(util[ids])]
    return {'static_mises_MPa':float(vm[i]),'static_factor':float(800./vm[i]),'static_xyz_mm':xyz[i].tolist(),
            'fatigue_factor':float(1./util[j]),'fatigue_xyz_mm':xyz[j].tolist(),'n_sigma':float(support[j]),
            'fatigue_mises_range_MPa':float(2*alternating_MPa[j]),'k_R':kR}


def solve(level,crown,jobs=1,summary_dir=f.FEA):
    stem = f'r2_seat_{"crown" if crown else "flat"}_{level}'
    with TemporaryDirectory(prefix=stem+'_',dir=f.HERE) as tmp:
        folder = Path(tmp)
        blade,xyz,tets,active,faces,seat,rear,arc,sidecar = write_model(folder,stem,level,crown)
        n = blade.ids.size
        def case(label, force_N):
            work = folder/label
            work.mkdir()
            for name in ('round2_blade_mesh.inp', 'round2_seat_mesh.inp', sidecar):
                copyfile(folder/name,work/name)
            path = work/f'{stem}_{label}.inp'
            deck(path,blade,sidecar,force_N)
            f.run_tool([f.BIN/'ccx.exe','-i',path.stem],work,'Job finished')
            frd = path.with_suffix('.frd')
            response = f.results_frd(frd,n+len(xyz))
            summary = deformation(blade,xyz,seat,rear,response,force_N)
            summary['contact'] = contact_summary(frd,xyz,seat,n)
            if level==0 and crown:
                (f.FEA/path.name).write_bytes(path.read_bytes())
            return label,response['STRESS'],summary

        cases = (('static',a.STATIC_N),('fatigue',a.CYCLIC_N))
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            runs = [pool.submit(case,*args) for args in cases]
            completed = [run.result() for run in runs]
    static,fatigue = (row[1] for row in completed)
    loads = {label:summary for label,_,summary in completed}
    principal = np.linalg.eigvalsh(f.stress_tensors(fatigue[n:]))
    gradient = f.normal_gradient(xyz,tets,f.surface_normals(xyz,tets,faces),abs(principal).max(axis=1))
    seat_support = f.notch_support(gradient,1000.,False)
    blade_proof = proof(np.arange(n),blade.xyz.reshape(-1,3),static[1:n+1],fatigue[1:n+1],np.ones(n))
    regions = {'blade':blade_proof,
               'seat':proof(active,xyz,static[n:],fatigue[n:],seat_support),
               'seat_R20':proof(arc,xyz,static[n:],fatigue[n:],seat_support)}
    data = {'support':'all rear seat translations fixed','friction':g.FRICTION,'crown_depth_mm':CROWN_DEPTH_mm if crown else 0.,
            'h_bulk_mm':MESH_mm[level][0],'h_contact_mm':MESH_mm[level][1],
            'nodes':len(active)+n,'elements':len(tets)+blade.elements.size,'loads':loads,'regions':regions}
    f.write_json(summary_dir/(stem+'.json'),data)
    print(stem,[(name,q['static_factor'],q['fatigue_factor']) for name,q in regions.items()],
          loads['static']['contact'],flush=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('levels',type=int,nargs='+')
    cli.add_argument('--flat',action='store_true')
    cli.add_argument('--jobs',type=int,choices=(1,2),default=1)
    args = cli.parse_args()
    for level in args.levels:
        solve(level,not args.flat,args.jobs)
