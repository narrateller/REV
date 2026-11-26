"""Local elastic outlet assessment using original T-1.7c contacts and T-1.7 cut fields."""
import argparse
import os
import subprocess
from math import hypot
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

import contact as base
import frame_boundary as boundary
import frame_fea as fea
import r2_strength
from frame_geometry import Geo, rounded_box

HERE = Path(__file__).resolve().parent
CUT_X_MM = 190.
CUT_Y_MM = 125.
ECC_MM = (10., -10.)


def geometry(trial, level):
    bulk_mm, near_mm, edge_mm = (
        (34., 11., 7.5), (30., 9., 5.8), (26., 7.5, 4.6))[level]
    thickness_mm = trial['thickness_mm']
    closed_y_mm = 2.-trial['travel_mm']
    outer_y_mm = -18.-(trial['travel_mm']-75.)/2
    height_mm = 212.+trial['travel_mm']-75.
    plate = Geo()
    rounded_box(plate, 0., outer_y_mm, 130., height_mm/2, 5., 0., thickness_mm, 0., 'blade')
    rounded_box(plate, 0., closed_y_mm, 79., 32.5, 3., -1., thickness_mm+2., 0., 'window')
    plate.cut('blade', ['window'], 'body')
    plate.lines += base.mesh_settings(edge_mm, 2.4*near_mm, 82., f'Min(z,{thickness_mm}-z)')
    seat = Geo()
    rounded_box(seat, 0., 0., 170., 90., 12., 0., 55., 0., 'seat')
    rounded_box(seat, 0., 2., 79., 32.5, 3., -1., 57., 0., 'passage')
    seat.cut('seat', ['passage'], 'body')
    seat.lines += base.mesh_settings(edge_mm, 2.4*near_mm, 89., 'Min(z,55-z)')
    cast = Geo()
    cast.emit(f'Box(1) = {{-{CUT_X_MM},-{CUT_Y_MM},0,{2*CUT_X_MM},{2*CUT_Y_MM},205}};')
    rounded_box(cast, 0., 0., 170.1, 90.1, 12., -1., 56., 0., 'pocket')
    rounded_box(cast, 0., 0., 88., 37., 20., -1., 207., 0., 'channel')
    cast.cut('1', ['pocket', 'channel'], 'body')
    cast.lines += base.mesh_settings(near_mm, bulk_mm, 100., 'Abs(z-55)*.65')
    return dict(blade=plate, seat=seat, cast=cast)


def eased(distance_mm, length_mm, depth_mm):
    return depth_mm*np.clip(1.-distance_mm/length_mm, 0., 1.)**2


def mesh(work, trial, level, prefix):
    thickness_mm = trial['thickness_mm']
    closed_y_mm = 2.-trial['travel_mm']
    parts = {}
    n_nodes = n_elements = 0
    for name, geo in geometry(trial, level).items():
        geo_path = work/f'{name}.geo'
        geo_path.write_text('\n'.join(geo.lines)+'\n', encoding='ascii', newline='\n')
        (HERE/f'{prefix}_{level}_{name}.geo').write_bytes(geo_path.read_bytes())
        msh = work/f'{name}.msh'
        fea.run_tool([fea.BIN/'gmsh.exe', geo_path.name, '-3', '-order', '2', '-format', 'msh2',
                      '-o', msh.name, '-nt', '1', '-nopopup'], work, 'Done writing')
        xyz, tets, active, triangles = fea.read_mesh(msh)
        x,y,z = xyz.T
        if name == 'blade':
            front = fea.plane_triangles(xyz, triangles, 2, 0.)
            back = fea.plane_triangles(xyz, triangles, 2, thickness_mm)
            outside_window = base.rounded_distance(x,y-closed_y_mm,158.,65.,3.)
            travel_shift = trial['travel_mm']-75.
            outline_edge = -base.rounded_distance(x,y+18.+travel_shift/2,260.,212.+travel_shift,5.)
            z -= eased(np.minimum(outside_window,outline_edge),3.,.035)*(z/thickness_mm)**4
            wing_corner = np.clip((abs(x)-80.)/45.,0.,1.)
            step = wing_corner**2*(3.-2.*wing_corner)
            z -= trial.get('wing_mm',0.)*step*(1.-z/thickness_mm)
            surfaces = dict(blade_back=base.surface_rows(tets,back,n_elements))
            local = xyz.copy()
        elif name == 'seat':
            front = base.local_contact(xyz,fea.plane_triangles(xyz,triangles,2,0.),133.,-90.,89.)
            back = fea.plane_triangles(xyz,triangles,2,55.)
            d = base.rounded_distance(x,y-2.,158.,65.,3.)
            z += eased(d,trial['runout_length_mm'],trial['runout_depth_mm'])*(1.-z/55.)**4
            edge = -base.rounded_distance(x,y,340.,180.,12.)
            z -= eased(edge,3.,.035)*(z/55.)**4
            local = xyz.copy()
            z += thickness_mm
            surfaces = dict(seat_front=base.surface_rows(tets,front,n_elements),
                            seat_back=base.surface_rows(tets,back,n_elements))
        else:
            front = fea.plane_triangles(xyz,triangles,2,55.)
            back = fea.plane_triangles(xyz,triangles,2,205.)
            local = xyz.copy()
            z += thickness_mm
            surfaces = dict(cast_pocket=base.surface_rows(tets,front,n_elements))
        base.write_body(work,name,xyz,tets,active,n_nodes,n_elements)
        parts[name] = dict(xyz=xyz, local=local, tets=tets, active=active, tri=triangles, front=front,
                           back=back, offset=n_nodes, surfaces=surfaces)
        n_nodes += len(xyz)
        n_elements += len(tets)
    return parts, n_nodes, n_elements


def input_lines(parts, stiffness_MPa_mm, linear_tie=False, contact_mode="SURFACE TO SURFACE"):
    lines = ['*HEADING','T-1.7d | displacement submodel | N, mm, MPa','*INCLUDE,INPUT=mesh.inc',
             '*MATERIAL,NAME=STEEL','*ELASTIC','210000.,.30']
    lines.extend(f'*SOLID SECTION,ELSET={name},MATERIAL=STEEL' for name in parts)
    pair_type = contact_mode
    if contact_mode=='NODE SMALL':
        pair_type = 'NODE TO SURFACE,SMALL SLIDING'
    lines += ['*SURFACE INTERACTION,NAME=OILED','*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR',
              f'{stiffness_MPa_mm},1.','*FRICTION','.15,10000.',
              f'*CONTACT PAIR,INTERACTION=OILED,TYPE={pair_type}','seat_front,blade_back']
    if linear_tie:
        lines += ['*TIE,NAME=SEAT_UNILATERAL_SCREEN,POSITION TOLERANCE=0.07,ADJUST=NO','seat_back,cast_pocket']
    else:
        lines += [f'*CONTACT PAIR,INTERACTION=OILED,TYPE={pair_type}','seat_back,cast_pocket']
    spring_rows = []
    first_spring = sum(len(part['tets']) for part in parts.values())+1
    for index, name in enumerate(('blade','seat')):
        tag = base.nearest(parts[name],(108.,60.,0. if name=='blade' else 27.5))
        spring_rows.append(f'{first_spring+index},{tag}')
    lines += ['*ELEMENT,TYPE=SPRING1,ELSET=AXIAL_LOCATORS',*spring_rows,
              '*SPRING,ELSET=AXIAL_LOCATORS','3','20.','*BOUNDARY']
    for name, z_mm in (('blade',0.),('seat',27.5)):
        part = parts[name]
        a,b = [base.nearest(part,(x,54.,z_mm)) for x in (-110.,110.)]
        lines += [f'{a},1,2',f'{b},2,2']
    return lines


def step(part, cut_tags, imposed_mm, force_N, direct=False, r2=False, contact_mode=None):
    solver = '*STATIC' if direct else '*STATIC,SOLVER=ITERATIVE SCALING'
    increment = '.2,1.,1.e-6,.5' if r2 else ('.16,1.,1.e-6,.35' if direct else '.5,1.,1.e-6,.5')
    lines = ['*STEP,INC=100',solver,increment]
    if r2 and contact_mode=='SURFACE TO SURFACE':
        lines += ['*CONTROLS,PARAMETERS=CONTACT', '.005,.1,100,60']
    if r2 and contact_mode=='NODE SMALL':
        # Nonconforming active sets can require much more than 16 Newton
        # iterations. The default field residual thresholds still apply.
        lines += ['*CONTROLS,PARAMETERS=TIME INCREMENTATION',
                  '12,30,9,100,45,8,0,10,0,0', '.5,.5,.75,.85,,,1.5']
    lines += ['*BOUNDARY']
    for tag, values in zip(cut_tags,imposed_mm,strict=True):
        lines.extend(f'{tag},{i},{i},{u:.12g}' for i,u in enumerate(values,1))
    lines += ['*CLOAD,OP=NEW']
    loads = force_N*base.load_weights(part,ECC_MM)
    if force_N:
        lines.extend(f'{i},3,{loads[i]:.12g}' for i in np.flatnonzero(loads))
    else:
        lines.append(f'{part["active"][0]},3,0.')
    lines += ['*NODE FILE,FREQUENCY=999999','U,RF','*EL FILE,FREQUENCY=999999','S',
              '*CONTACT FILE,FREQUENCY=999999','CDIS,CSTR','*END STEP']
    return lines


def describe_load(parts, dataset, p_MPa, cut_tags, force_N):
    reactions_N = dataset['FORC'][cut_tags]
    reaction_N = reactions_N.sum(axis=0)
    sr = dict(applied_force_N=force_N, cut_reaction_N=reaction_N.tolist(),
              axial_balance_relative=float(abs(force_N+reaction_N[2])/force_N) if force_N else None)
    for name, s in (('blade_seat','front'),('seat_cast','back')):
        part = parts['seat']
        tags = np.unique(part[s])+part['offset']
        vals = p_MPa[tags]
        coords = part['xyz'][tags-part['offset']]
        sr[name] = dict(peak_MPa=float(vals.max()), xyz_mm=coords[vals.argmax()].tolist())
        tri = part[s]
        points = part['xyz'][tri[:,:3]]
        areas = np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]),axis=1)/2
        # Nodal CSTR is smoothed by CCX. This integral is for contact distribution,
        # with the exact finite-element balance obtained from the cut reactions.
        forces = areas*np.mean(p_MPa[tri[:,:3]+part['offset']],axis=1)
        positive = forces>0.
        sr[name].update(interpolated_normal_N=float(forces.sum()),
                        centroid_xyz_mm=(np.average(points.mean(axis=1)[positive],axis=0,
                                                    weights=forces[positive]).tolist()
                                         if positive.any() else None))
    return sr


def proof(parts, data, trial, r2=False):
    zones = {}
    for name, part in parts.items():
        ids = part['active']
        coordinates = part['xyz']
        tags = ids+part['offset']
        static = data['static']['STRESS'][tags]
        start = data['zero']['STRESS'][tags]
        rng = data['fatigue']['STRESS'][tags]-start
        mean = start+rng/2
        cast = name=='cast'
        rp,rm = (650.,800.) if cast else (800.,1000.)
        if name=='blade' and trial['thickness_mm']+trial.get('wing_mm',0.)>60.:
            rp,rm = 700.,900.
        vm = fea.mises(static)
        principal = np.zeros(len(coordinates))
        principal[ids] = np.abs(np.linalg.eigvalsh(fea.stress_tensors(rng))).max(axis=1)
        normals = fea.surface_normals(coordinates,part['tets'],part['tri'])
        gradient = fea.normal_gradient(coordinates,part['tets'],normals,principal)[ids]
        n_sigma = fea.notch_support(gradient,rm,cast)
        strength, k_R, j_G, m_sigma = fea.fkm_parameters(rm,6.3,cast,forging=not cast)
        mean_principal = np.maximum(0.,np.linalg.eigvalsh(fea.stress_tensors(mean))[:,-1])
        util = (fea.mises(rng)/2+m_sigma*mean_principal)/(strength*n_sigma)
        masks = {name: np.ones(len(ids),dtype=bool)}
        x,y,z=part['local'][ids].T
        if cast:
            # Exclude the artificial Dirichlet cuts from the local casting proof.
            masks[name] = (abs(x)<CUT_X_MM-12.) & (abs(y)<CUT_Y_MM-12.)
            d = base.rounded_distance(x,y,176.,74.,20.)
            masks['cast_R20'] = ((abs(d)<1.) & (abs(x)>=68.) & (abs(y)>=17.) & (z>=55.))
        elif name=='blade':
            masks['blade_land'] = z > trial['thickness_mm']-8.
            if trial.get('wing_mm'):
                masks['blade_step'] = (z<2.) & (abs(x)>79.) & (abs(x)<127.)
        else:
            masks['insert_land'] = z < 8.
        if r2:
            values = r2_strength.fatigue(static, start, data['fatigue']['STRESS'][tags], gradient, rp, rm, casting=cast)
            for zone, mask in masks.items():
                zones[zone] = r2_strength.summarize(values,coordinates[ids],mask)
            if name in ('blade', 'seat'):
                depth_mm = (trial['thickness_mm']-z) if name=='blade' else z
                lower = (abs(x)<=75.) & (y<=-30.5) & (y>=34.5-trial['travel_mm'])
                upper = (abs(x)<=75.) & (y>=34.5) & (y<=85.)
                bands = ((0,1),(1,3),(3,6),(6,9),(9,15),(15,25),(25,45))
                for land,mask in (('lower',lower),('upper',upper)):
                    depth_results = []
                    for lo,hi in bands:
                        region = mask & (depth_mm>=lo-1.e-6) & (depth_mm<hi-1.e-6)
                        if region.any():
                            depth_results.append(dict(depth_mm=[lo,hi], **r2_strength.summarize(values,coordinates[ids],region)))
                    zones[name+'_'+land+'_depth'] = depth_results
            continue
        for zone, mask in masks.items():
            locations = np.flatnonzero(mask)
            si = locations[vm[locations].argmax()]
            fi = locations[util[locations].argmax()]
            zones[zone] = dict(static_factor=float(rp/vm[si]), FKM_factor=float(1./util[fi]),
                               static_mises_MPa=float(vm[si]), fatigue_mises_range_MPa=float(fea.mises(rng)[fi]),
                               static_xyz_mm=coordinates[ids[si]].tolist(),
                               fatigue_xyz_mm=coordinates[ids[fi]].tolist(), G_per_mm=float(gradient[fi]),
                               n_sigma=float(n_sigma[fi]), k_R=k_R, j_G=j_G, M_sigma=m_sigma,
                               Rp02_MPa=rp, Rm_MPa=rm)
    return zones


def solve(trial, prefix, levels, inputs_only=False, linear_tie=False, contact_mode="SURFACE TO SURFACE", direct=False):
    with TemporaryDirectory(dir=HERE,prefix='reference_') as reference_path:
        reference = boundary.interface_basis(Path(reference_path))
        for level in levels:
            run_level(trial,prefix,level,reference,inputs_only,linear_tie,contact_mode,direct)


def run_ccx(work, name, prefix, level):
    n_threads = os.environ.get('REV_T17D_CCX_THREADS', '1')
    env = dict(os.environ, OMP_NUM_THREADS=n_threads, CCX_NPROC_RESULTS=n_threads,
               CCX_NPROC_EQUATION_SOLVER=n_threads)
    log = work/name
    timed_out = False
    with log.open('wb') as out:
        try:
            result = subprocess.run([str(fea.BIN/'ccx.exe'), '-i', name], cwd=work, env=env,
                                    stdout=out, stderr=subprocess.STDOUT, timeout=2400)
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = None
    output = log.read_text(encoding='ascii', errors='replace')
    if timed_out or exit_code or 'Job finished' not in output or '*ERROR' in output:
        progress = {p.suffix:p.read_text(encoding='ascii', errors='replace').splitlines()[-15:]
                    for p in work.glob(name+'.*') if p.suffix in ('.sta','.cvg')}
        fea.write_json(HERE/f'{prefix}_{level}_{name}_failure.json',
                       dict(timed_out=timed_out, solver_exit_code=exit_code, log_tail=output[-3600:], progress=progress))
        raise RuntimeError(output[-3600:])


def run_level(trial,prefix,level,reference,inputs_only,linear_tie,contact_mode,direct):
    r2 = prefix.startswith('r2_')
    with TemporaryDirectory(dir=HERE,prefix=f'{prefix}_{level}_') as work_path:
        work = Path(work_path)
        if prefix.startswith('r2_aligned'):
            from r2_mesh import mesh as conforming
            archive = None if '_replay' in prefix else HERE/f'{prefix}_{level}.geo'
            parts, n_nodes, n_elements = conforming(work,trial,level,CUT_X_MM,CUT_Y_MM,archive)
        else:
            parts, n_nodes, n_elements = mesh(work,trial,level,prefix)
        print(prefix,level,n_nodes,n_elements,flush=True)
        includes = []
        for name,part in parts.items():
            includes += [f'*INCLUDE,INPUT={name}.inc']
            for key, rows in part['surfaces'].items():
                includes += [f'*SURFACE,TYPE=ELEMENT,NAME={key}',*[f'{i},S{j}' for i,j in rows]]
        (work/'mesh.inc').write_text('\n'.join(includes)+'\n',encoding='ascii')
        cast = parts['cast']
        active = cast['active']
        pos = cast['local'][active]
        is_cut = np.isclose(abs(pos[:,0]),CUT_X_MM,atol=1.e-6) | np.isclose(abs(pos[:,1]),CUT_Y_MM,atol=1.e-6)
        cut_tags = active[is_cut]+cast['offset']
        fields, extrapolated, tie = boundary.cut_field(reference,pos[is_cut])
        head = input_lines(parts,50000.,linear_tie,contact_mode)
        loads, datasets = {}, {}
        for name,load_N in (('static',base.STATIC_N),('fatigue',base.CYCLIC_N),('zero',0.)):
            disp = boundary.displacements(fields,tie,load_N,ECC_MM,'min')
            if direct or r2:
                # The reference has an arbitrary axial anchor on the column. A common
                # translation leaves cast strain unchanged and centres the numerical locators.
                cut_near = abs(pos[is_cut,2]-55.)<25.
                disp[:,2] -= disp[cut_near,2].mean()
            inp = work/f'{name}.inp'
            rows = step(parts['blade'],cut_tags,disp,load_N,direct,r2,contact_mode)
            inp.write_text('\n'.join(head+rows)+'\n',encoding='ascii',newline='\n')
            if level==0 and '_replay' not in prefix:
                (HERE/f'{prefix}_{name}.inp').write_bytes(inp.read_bytes())
            if inputs_only:
                continue
            print(prefix,level,name,flush=True)
            if r2:
                run_ccx(work,name,prefix,level)
            else:
                fea.run_tool([fea.BIN/'ccx.exe','-i',name],work,'Job finished')
            frd = inp.with_suffix('.frd')
            data = fea.results_frd(frd,n_nodes)
            pressures = base.contact_values(frd,n_nodes)
            frd.unlink()
            loads[name] = describe_load(parts,data,pressures,cut_tags,load_N)
            datasets[name] = data
            print(loads[name],flush=True)
        if inputs_only:
            fea.write_json(HERE/f'{prefix}_mesh_{level}.json',
                           dict(level=level,nodes=n_nodes,elements=n_elements,dirichlet_cut_nodes=len(cut_tags),
                                extrapolated_cut_nodes=extrapolated))
            return
        result = dict(level=level, geometry=trial, nodes=n_nodes, elements=n_elements, eccentricity_mm=ECC_MM,
                      contacts_mu=.15, throat_screen_MPa=480., cast_screen_MPa=390.,
                      cut_size_mm=[2*CUT_X_MM,2*CUT_Y_MM], cut_nodes=len(cut_tags),
                      extrapolated_cut_nodes=extrapolated, preload='min',
                      frame_load_fraction=tie['load_fraction'], loads=loads,
                      regions=proof(parts,datasets,trial,r2),
                      clearance=base.assembly_guide_estimate(parts,datasets['fatigue']),
                      seat_cast_tied=linear_tie,contact_mode=contact_mode)
        fea.write_json(HERE/f'{prefix}_{level}.json',result)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('levels',nargs='+',type=int,choices=(0,1,2,3,4,5))
    parser.add_argument('--thickness',type=float,default=44.)
    parser.add_argument('--travel',type=float,default=87.)
    parser.add_argument('--runout-length',type=float,default=14.)
    parser.add_argument('--runout-depth',type=float,default=.15)
    parser.add_argument('--wing',type=float,default=12.)
    parser.add_argument('--label',default='cycle_limit')
    parser.add_argument('--inputs-only',action='store_true')
    parser.add_argument('--linear-tie',action='store_true')
    parser.add_argument('--node-contact',action='store_true')
    parser.add_argument('--direct',action='store_true')
    parser.add_argument('--mortar',action='store_true')
    parser.add_argument('--small-sliding',action='store_true')
    args = parser.parse_args()
    if max(args.levels)>2 and not args.label.startswith('r2_aligned'):
        parser.error('Levels 3 through 5 are defined for aligned interfaces.')
    trial = dict(thickness_mm=args.thickness, travel_mm=args.travel, wing_mm=args.wing,
                 runout_length_mm=args.runout_length, runout_depth_mm=args.runout_depth)
    solve(trial,args.label,args.levels,args.inputs_only,args.linear_tie,
          'MORTAR' if args.mortar else ('NODE SMALL' if args.small_sliding else ('NODE TO SURFACE' if args.node_contact else 'SURFACE TO SURFACE')),args.direct)

