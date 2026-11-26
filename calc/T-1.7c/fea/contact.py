"""Three-dimensional BREP/Gmsh and CalculiX model of the compact outlet (N, mm, MPa)."""
import argparse
from math import hypot
from pathlib import Path
from tempfile import TemporaryDirectory

import frame_fea as f
import numpy as np
from frame_analytic import (CORNERS, ECC_mm, E_MPa, NU,
                            STATIC_N, CYCLIC_N, VARIANTS)
from frame_geometry import Geo, model as reference_geometry, rounded_box

HERE = Path(__file__).resolve().parent
THICK_MM = 38.
SEAT_DEPTH_MM = 55.
CAST_DEPTH_MM = 205.
WINDOW_MM = (158., 65.)
WINDOW_OPEN_CENTER_MM = 2.
WINDOW_CLOSED_CENTER_MM = WINDOW_OPEN_CENTER_MM - 75.
WINDOW_RADIUS_MM = 3.
BLADE_MM = (260., 212.)
BLADE_CENTER_Y_MM = -18.
POCKET_MM = (340., 180.)
POCKET_R_MM = 12.
RELIEF_MM = 3.
RELIEF_DEPTH_MM = .035
MU = .15
BEARING_SCREEN_MPA = 480.
MESH = ((32., 8., 5.8), (28., 6.5, 4.6), (24., 5.4, 3.7))
SIDES = ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0))


def mesh_settings(near_mm, bulk_mm, width_mm, z_expr):
    return [
        f'Mesh.MeshSizeMax={bulk_mm}; Mesh.MeshSizeFromPoints=0; Mesh.MeshSizeFromCurvature=8;',
        'Mesh.MeshSizeExtendFromBoundary=0; Mesh.SecondOrderLinear=1; Mesh.RandomSeed=42;',
        f'Field[1]=MathEval; Field[1].F="{near_mm}+({bulk_mm}-{near_mm})*'
        f'Min(1,Max(Max(0,Abs(x)-{width_mm}),Max(Max(0,Abs(y)-47),{z_expr}))/20)"; Background Field=1;',
    ]


def blade_geo(level):
    _, seat_mm, face_mm = MESH[level]
    geo = Geo()
    rounded_box(geo, 0., BLADE_CENTER_Y_MM, BLADE_MM[0]/2, BLADE_MM[1]/2, 5., 0., THICK_MM, 0., 'blade')
    rounded_box(geo, 0., WINDOW_CLOSED_CENTER_MM, WINDOW_MM[0]/2, WINDOW_MM[1]/2,
                WINDOW_RADIUS_MM, -1., THICK_MM+2, 0., 'window')
    geo.cut('blade', ['window'], 'body')
    return '\n'.join(geo.lines + mesh_settings(face_mm, 2.1*seat_mm, 92., '0')) + '\n'


def seat_geo(level):
    _, seat_mm, face_mm = MESH[level]
    geo = Geo()
    rounded_box(geo, 0., 0., POCKET_MM[0]/2, POCKET_MM[1]/2, POCKET_R_MM, 0., SEAT_DEPTH_MM, 0., 'seat')
    rounded_box(geo, 0., WINDOW_OPEN_CENTER_MM, WINDOW_MM[0]/2, WINDOW_MM[1]/2,
                WINDOW_RADIUS_MM, -1., SEAT_DEPTH_MM+2, 0., 'throat')
    geo.cut('seat', ['throat'], 'body')
    return '\n'.join(geo.lines + mesh_settings(face_mm, 2.5*seat_mm, 98., 'Min(z,55-z)')) + '\n'


def cast_geo(level):
    bulk_mm, near_mm, _ = MESH[level]
    variant = next(v.at_end('chamber') for v in VARIANTS if v.name == 'cast')
    original, _, _, _ = reference_geometry(variant, 'chamber', 0)
    prefix = original[:original.index('For i In')]
    geo = Geo()
    geo.lines = [prefix.rstrip()]
    geo.counter = 10000
    rounded_box(geo, 0., 0., POCKET_MM[0]/2+.10, POCKET_MM[1]/2+.10, POCKET_R_MM,
                -1., SEAT_DEPTH_MM+1., 0., 'pocket')
    geo.cut('bodies[]', ['pocket'], 'casting')
    geo.lines += mesh_settings(near_mm, bulk_mm, 103., 'Abs(z-55)*.5')
    return '\n'.join(geo.lines) + '\n'


def rounded_distance(x, y, width_mm, height_mm, radius_mm):
    a = abs(x) - (width_mm/2-radius_mm)
    b = abs(y) - (height_mm/2-radius_mm)
    return np.hypot(np.maximum(a, 0.), np.maximum(b, 0.)) + np.minimum(np.maximum(a, b), 0.) - radius_mm


def ease(distance_mm):
    return RELIEF_DEPTH_MM * np.clip(1. - distance_mm/RELIEF_MM, 0., 1.)**2


def surface_rows(tets, faces, offset):
    keys = {tuple(sorted(face[:3])) for face in faces}
    rows = [(idx + offset, idx_face)
            for idx, tet in enumerate(tets, 1)
            for idx_face, vertices in enumerate(SIDES, 1)
            if tuple(sorted(tet[list(vertices)])) in keys]
    if len(rows) != len(faces):
        raise ValueError(f'Surface connectivity mismatch ({len(rows)} versus {len(faces)})')
    return rows


def write_body(work, name, xyz, tets, active, node_offset, element_offset):
    with (work/f'{name}.inc').open('w', encoding='ascii') as out:
        out.write('*NODE\n')
        for node in active:
            out.write(f'{node + node_offset},'+','.join(f'{x:.12g}' for x in xyz[node])+'\n')
        out.write(f'*ELEMENT,TYPE=C3D10,ELSET={name}\n')
        for tag, tet in enumerate(tets, 1+element_offset):
            out.write(f'{tag},'+','.join(map(str,tet+node_offset))+'\n')


def local_contact(xyz, faces, half_width_mm, y_min_mm, y_max_mm):
    return faces[(abs(xyz[faces[:,:3],0]).min(axis=1) < half_width_mm)
                 & (xyz[faces[:,:3],1].max(axis=1) > y_min_mm)
                 & (xyz[faces[:,:3],1].min(axis=1) < y_max_mm)]


def mesh(work, level):
    parts = {}
    n_nodes = n_elements = 0
    for name, geometry in (('blade',blade_geo), ('seat',seat_geo), ('cast',cast_geo)):
        stem = f'{name}_{level}'
        geo = work/(stem+'.geo')
        geo.write_text(geometry(level), encoding='ascii', newline='\n')
        (HERE/geo.name).write_bytes(geo.read_bytes())
        msh = geo.with_suffix('.msh')
        f.run_tool([f.BIN/'gmsh.exe', geo.name, '-3', '-order', '2', '-format', 'msh2', '-o', msh.name, '-nt', '1',
                    '-nopopup'], work, 'Done writing')
        xyz,tets,active,triangles = f.read_mesh(msh)
        offset = n_nodes
        if name == 'blade':
            front = f.plane_triangles(xyz,triangles,2,0.)
            back = f.plane_triangles(xyz,triangles,2,THICK_MM)
            outer_mm = -rounded_distance(xyz[:,0],xyz[:,1]-BLADE_CENTER_Y_MM,*BLADE_MM,5.)
            window_mm = rounded_distance(xyz[:,0],xyz[:,1]-WINDOW_CLOSED_CENTER_MM,*WINDOW_MM,WINDOW_RADIUS_MM)
            xyz[:,2] -= ease(np.minimum(outer_mm,window_mm))*(xyz[:,2]/THICK_MM)**4
            surfaces = dict(blade_back=surface_rows(tets,back,n_elements))
            xyz_local = xyz.copy()
        elif name == 'seat':
            front = local_contact(xyz,f.plane_triangles(xyz,triangles,2,0.),133.,-92.,90.)
            back = f.plane_triangles(xyz,triangles,2,SEAT_DEPTH_MM)
            D = rounded_distance(xyz[:,0],xyz[:,1]-WINDOW_OPEN_CENTER_MM,*WINDOW_MM,WINDOW_RADIUS_MM)
            outer_mm = -rounded_distance(xyz[:,0],xyz[:,1],*POCKET_MM,POCKET_R_MM)
            xyz[:,2] += ease(D)*(1.-xyz[:,2]/SEAT_DEPTH_MM)**4
            xyz[:,2] -= ease(outer_mm)*(xyz[:,2]/SEAT_DEPTH_MM)**4
            xyz_local = xyz.copy()
            xyz[:,2] += THICK_MM
            surfaces = dict(seat_front=surface_rows(tets,front,n_elements),
                            seat_back=surface_rows(tets,back,n_elements))
        else:
            front = f.plane_triangles(xyz,triangles,2,0.)
            pocket = f.plane_triangles(xyz,triangles,2,SEAT_DEPTH_MM)
            back = f.plane_triangles(xyz,triangles,2,CAST_DEPTH_MM)
            xyz_local = xyz.copy()
            xyz[:,2] += THICK_MM
            surfaces = dict(cast_pocket=surface_rows(tets,pocket,n_elements))
        write_body(work,name,xyz,tets,active,offset,n_elements)
        parts[name] = dict(xyz=xyz, local=xyz_local, tets=tets, active=active, tri=triangles, front=front, back=back,
                           offset=offset, surfaces=surfaces)
        n_nodes += len(xyz)
        n_elements += len(tets)
    print(f'mesh {level}: nodes {n_nodes}, elements {n_elements}', flush=True)
    return parts, n_nodes, n_elements


def set_lines(name, tags):
    return [f'*NSET,NSET={name}', *[','.join(map(str,tags[i:i+16])) for i in range(0,len(tags),16)]]


def nearest(part, xyz_mm):
    ids = part['active']
    best = ids[np.linalg.norm(part['local'][ids]-xyz_mm,axis=1).argmin()]
    return best+part['offset']


def load_weights(part, eccentricity_mm):
    xyz, faces = part['xyz'], part['front']

    def footprint(x,y):
        x_taper = f.smooth_edge(75-abs(x), 3.)
        y_taper = f.smooth_edge(30-abs(y), 3.)
        return x_taper*y_taper

    q0,qx,qy,area = f.patch_loads(xyz,faces,footprint,(0.,0.))
    basis = np.array([q0,qx/area,qy/area]).T
    equilibrate = np.vstack((np.ones(len(xyz)),xyz[:,:2].T)) @ basis
    return basis @ np.linalg.solve(equilibrate,[1.,*eccentricity_mm])


def deck(work, parts, force_N, eccentricity_mm, formulation):
    lines = ['*HEADING','T-1.7c round 2 | closed gate and recessed seat on cast chamber | N, mm, MPa']
    mesh_lines = []
    for name, part in parts.items():
        mesh_lines.append(f'*INCLUDE,INPUT={name}.inc')
        for surf, rows in part['surfaces'].items():
            mesh_lines.append(f'*SURFACE,TYPE=ELEMENT,NAME={surf}')
            mesh_lines.extend(f'{el},S{face}' for el,face in rows)
    mesh_name = 'model_mesh_and_surfaces.inc'
    (work/mesh_name).write_text('\n'.join(mesh_lines)+'\n',encoding='ascii',newline='\n')
    lines += [f'*INCLUDE,INPUT={mesh_name}','*MATERIAL,NAME=STEEL','*ELASTIC',f'{E_MPa},{NU}']
    lines.extend(f'*SOLID SECTION,ELSET={name},MATERIAL=STEEL' for name in parts)
    lines += ['*SURFACE INTERACTION,NAME=OILED_STEEL']
    if formulation == 'penalty':
        lines += ['*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR','50000.,1.']
    lines += ['*FRICTION',f'{MU},10000.']
    contact_type = 'SURFACE TO SURFACE' if formulation == 'penalty' else 'MORTAR'
    for slave,master in (('seat_front','blade_back'),('seat_back','cast_pocket')):
        lines += [f'*CONTACT PAIR,INTERACTION=OILED_STEEL,TYPE={contact_type}',f'{slave},{master}']
    cast = parts['cast']
    xyz = cast['local']
    end = np.unique(cast['back'])
    radii = np.min([np.linalg.norm(xyz[end,:2]-[x,y],axis=1) for x,y in CORNERS],axis=0)
    bearing = end[(radii > 51.99) & (radii < 88.)]+cast['offset']
    lines += set_lines('COLUMN_WASHER', bearing)
    lines += ['*BOUNDARY','COLUMN_WASHER,3,3']
    for name, z in (('blade',0.),('seat',SEAT_DEPTH_MM/2),('cast',CAST_DEPTH_MM)):
        part=parts[name]
        x_mm = 110. if name!='cast' else 270.
        y_mm = 50. if name!='cast' else 335.
        lines += [f'{nearest(part,(-x_mm,y_mm,z))},1,2',f'{nearest(part,(x_mm,y_mm,z))},2,2']
    solver = '*STATIC,SOLVER=ITERATIVE SCALING' if formulation == 'penalty' else '*STATIC'
    lines += ['*STEP,INC=120',solver,'.5,1.,1.e-6,.5','*CLOAD']
    blade=parts['blade']
    loads = force_N*load_weights(blade,eccentricity_mm)
    lines.extend(f'{i},3,{loads[i]:.12g}' for i in np.flatnonzero(loads))
    lines += ['*NODE FILE,FREQUENCY=999999','U,RF','*EL FILE,FREQUENCY=999999','S',
              '*CONTACT FILE,FREQUENCY=999999','CDIS,CSTR','*END STEP']
    full = '\n'.join(lines)+'\n'
    work.joinpath('solve.inp').write_text(full,encoding='ascii',newline='\n')
    return bearing


def contact_values(path, count):
    p_MPa = np.zeros(count)
    is_contact = False
    for line in path.read_text(encoding='ascii').splitlines():
        if line.startswith(' -4'):
            is_contact = line.split()[1]=='CONTACT'
            if is_contact:
                p_MPa.fill(0.)
        elif line.startswith(' -1') and is_contact:
            p_MPa[int(line[3:13])] = float(line[49:61])
    return p_MPa


def proof(parts, static, fatigue):
    output = {}
    for name, part in parts.items():
        ids = part['active']
        tags = ids+part['offset']
        points=part['xyz']
        rp,rm = (650.,800.) if name=='cast' else (800.,1000.)
        st = static[tags]
        rng = fatigue[tags]
        vm = f.mises(st)
        eig = np.linalg.eigvalsh(f.stress_tensors(rng))
        magnitude = np.zeros(len(points))
        magnitude[ids] = np.abs(eig).max(axis=1)
        normals = f.surface_normals(points,part['tets'],part['tri'])
        gradient = f.normal_gradient(points,part['tets'],normals,magnitude)
        n_sigma = f.notch_support(gradient,rm,name=='cast')[ids]
        strength, kR, jG, slope = f.fkm_parameters(rm,6.3,name=='cast',forging=name!='cast')
        utilisation = (f.mises(rng)/2 + slope*np.maximum(0.,eig[:,-1]/2))/(strength*n_sigma)
        regions = {name: np.arange(len(ids))}
        if name == 'cast':
            local = part['local'][ids]
            d = rounded_distance(local[:,0],local[:,1],176.,74.,20.)
            regions['cast_channel_R20'] = np.flatnonzero((abs(d)<.35) & (local[:,2]>=SEAT_DEPTH_MM-.01)
                                                          & (abs(local[:,0])>=68.) & (abs(local[:,1])>=17.))
        for region, ix in regions.items():
            i,j=ix[np.argmax(vm[ix])],ix[np.argmax(utilisation[ix])]
            output[region] = dict(static_factor=float(rp/vm[i]), peak_von_mises_MPa=float(vm[i]),
                                  static_xyz_mm=points[ids[i]].tolist(), fatigue_factor=float(1./utilisation[j]),
                                  fatigue_xyz_mm=points[ids[j]].tolist(), fatigue_range_MPa=float(f.mises(rng)[j]),
                                  n_sigma=float(n_sigma[j]), k_R=kR, M_sigma=slope,j_G=jG)
    return output


def assembly_guide_estimate(parts,result):
    # Compare the fit to machined chamber-module bearing datums against the
    # insert opening. The unchanged cylinder and column terms remain separate.
    cast,seat=parts['cast'],parts['seat']
    base_targets=[(x,y,0.) for x in (-185.,185.) for y in (-112.,112.)]
    throat_targets=[(x,y,0.) for x in (-78.,78.) for y in (-30.5,34.5)]
    def fit(part,targets):
        tags = np.array([nearest(part,xyz) for xyz in targets])
        nodes = part['local'][tags-part['offset'],:2]
        u = result['DISP'][tags]
        slope = np.linalg.lstsq(np.column_stack((np.ones(len(nodes)),nodes)),u[:,2],rcond=None)[0][1:]
        return u[:,:2].mean(axis=0),slope

    base_u,base_slope = fit(cast,base_targets)
    throat_u,throat_slope = fit(seat,throat_targets)
    local_mm = np.abs(throat_u-base_u)+77.*np.abs(throat_slope-base_slope)
    return dict(local_relative_lateral_mm=local_mm.tolist(),local_offset_srss_mm=hypot(*local_mm),
                legacy_full_frame_budget_mm=.043,combined_screen_mm=hypot(*local_mm)+.043,
                limit_mm=.15, scope='Simplified datum fit, no guide rails/cylinder alignment or preload in this case.')


def solve(level, formulation, inputs_only=False):
    with TemporaryDirectory(prefix=f'contact_{level}_') as tmp:
        work=Path(tmp)
        parts,n_nodes,n_elements = mesh(work,level)
        responses = {}
        cases = (('static',STATIC_N),('fatigue',CYCLIC_N))
        for label, force in cases:
            print(f'{level} {label}: '+('input prepared' if inputs_only else 'solve'),flush=True)
            bearings=deck(work,parts,force,(ECC_mm,-ECC_mm),formulation)
            if level==0:
                (HERE/f'{formulation}_{label}.inp').write_bytes((work/'solve.inp').read_bytes())
            if inputs_only:
                continue
            f.run_tool([f.BIN/'ccx.exe','-i','solve'],work,'Job finished')
            frd=work/'solve.frd'
            result=f.results_frd(frd,n_nodes)
            p=contact_values(frd,n_nodes)
            r=result['FORC'][bearings,2].sum()
            if abs(r+force)/force > .01:
                raise ValueError(f'Force balance failed for {label}, reaction {r} N versus applied {force} N')
            p_max = int(p.argmax())
            contact = {}
            seat=parts['seat']
            for edge in ('front','back'):
                ids=np.unique(seat[edge])
                vals=p[ids+seat['offset']]
                contact[edge+'_peak_MPa'] = float(vals.max())
                contact[edge+'_peak_xyz_mm'] = seat['xyz'][ids[vals.argmax()]].tolist()
            responses[label] = result, dict(applied_force_N=force,washer_reaction_N=float(r),
                reaction_relative_error=float(abs(r+force)/force), max_contact_MPa=float(p[p_max]), **contact)
            print(f'{level} {label}: reaction {r:.0f} N, contact {p[p_max]:.1f} MPa',flush=True)
        if inputs_only:
            return None
        results = dict(level=level, mesh_bulk_seat_contact_mm=MESH[level], nodes=n_nodes, elements=n_elements,
                       load_eccentricity_mm=[ECC_mm,-ECC_mm], bearing_screen_MPa=BEARING_SCREEN_MPA,
                       clearance_screen=assembly_guide_estimate(parts,responses['static'][0]),
                       friction=MU, edge_relief_mm=[RELIEF_MM,RELIEF_DEPTH_MM], loads={k:v[1] for k,v in responses.items()},
                       regions=proof(parts,responses['static'][0]['STRESS'],responses['fatigue'][0]['STRESS']),
                       scope='Equivalent axial restraint on four outer column seats; preload not present in this load case.')
        f.write_json(HERE/f'{formulation}_{level}.json',results)
        print(results['regions'],flush=True)
        return results


if __name__ == '__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('levels',type=int,nargs='+',choices=range(len(MESH)))
    cli.add_argument('--formulation', choices=('penalty','mortar'), default='penalty')
    cli.add_argument('--inputs-only', action='store_true')
    args = cli.parse_args()
    for level in args.levels:
        solve(level,args.formulation,args.inputs_only)



