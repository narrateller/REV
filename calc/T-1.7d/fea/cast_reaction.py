"""One-way load transfer from the rigid-backed contact run to the T-1.7d cast cut."""
import argparse
import json
from math import hypot
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from scipy.spatial import cKDTree

import contact as base
import frame_boundary as boundary
import frame_fea as fea
from submodel import CUT_X_MM, CUT_Y_MM, ECC_MM, geometry

HERE = Path(__file__).resolve().parent
TRIAL = dict(thickness_mm=44.,travel_mm=87.,wing_mm=12.,runout_length_mm=14.,runout_depth_mm=.15)


SOURCE_REACTION_MESH_MM = 9.


def map_loads(xyz, face, loads):
    """Recover a continuous finite-area load from rigid-backing nodal reactions.

    Each input force occupies a patch one source element in radius. Preserve
    total force and both first moments to remove sensitivity to sampling.
    The resulting field is diagnostic at the outlet edge.
    """
    quadrature = list(fea.quadrature(xyz[face]))
    points = np.concatenate([position for _,position,_ in quadrature])
    areas_mm2 = np.concatenate([area for _,_,area in quadrature])
    tree = cKDTree(points[:,:2])
    forces = np.zeros((len(points),3))
    max_relocation_mm = 0.
    for x,y,*F_N in loads:
        position = np.array((x,y))
        sample = np.asarray(tree.query_ball_point(position,SOURCE_REACTION_MESH_MM),dtype=int)
        if not sample.size:
            raise ValueError(f'Cast face has no integration points within a source element of {position}')
        offset = points[sample,:2]-position
        radius_fraction = np.linalg.norm(offset,axis=1)/SOURCE_REACTION_MESH_MM
        weights = areas_mm2[sample]*(1.-radius_fraction**2)**2
        weights /= sum(weights)
        forces[sample] += weights[:,None]*F_N
        max_relocation_mm = max(max_relocation_mm,float(np.linalg.norm(weights@offset)))
    applied = np.asarray(loads)
    target_basis = np.column_stack((np.ones(len(applied)),applied[:,:2]))
    basis = np.column_stack((np.ones(len(points)),points[:,:2]))
    target = target_basis.T@applied[:,2:]
    raw = basis.T@forces
    weight = np.linalg.norm(forces,axis=1)
    corrections = weight[:,None]*basis
    forces += corrections@np.linalg.solve(basis.T@corrections,target-raw)
    nodal = np.zeros_like(xyz)
    for (shape,_,_), chunk in zip(quadrature,np.split(forces,len(quadrature)),strict=True):
        payload = (chunk[:,None,:]*shape[None,:,None]).reshape(-1,3)
        np.add.at(nodal,face.ravel(),payload)
    integrated = nodal.sum(axis=0)
    original = applied[:,2:].sum(axis=0)
    return nodal,dict(estimated_applied_force_N=integrated.tolist(),
                      original_force_N=original.tolist(), source_reaction_patch_radius_mm=SOURCE_REACTION_MESH_MM,
                      uncorrected_patch_centroid_shift_max_mm=max_relocation_mm,
                      axial_first_moment_error_Nmm=(
                          xyz[:,:2].T@nodal[:,2]-applied[:,:2].T@applied[:,4]).tolist())


def load_cast(work, region, level, reference, reaction, trial=TRIAL):
    g = geometry(trial,level)['cast']
    geo = work/'cast.geo'
    geo.write_text('\n'.join(g.lines)+'\n',encoding='ascii')
    fea.run_tool([fea.BIN/'gmsh.exe',geo.name,'-3','-order','2','-format','msh2',
                  '-o','cast.msh','-nt','1','-nopopup'],work,'Done writing')
    xyz, tets, active, faces = fea.read_mesh(work/'cast.msh')
    fea.write_mesh_include(work/'cast.inc',xyz,tets,active)
    x,y,z = xyz.T
    cut = active[np.isclose(abs(x[active]),CUT_X_MM)|np.isclose(abs(y[active]),CUT_Y_MM)]
    fields, extrapolated, tie = boundary.cut_field(reference,xyz[cut])
    bearing = fea.plane_triangles(xyz,faces,2,55.)
    solved, loads = {}, {}
    for label, force_N in (('zero',0.),('static',base.STATIC_N),('fatigue',base.CYCLIC_N)):
        bcs = boundary.displacements(fields,tie,force_N,ECC_MM,'min')
        lines=['*HEADING','T-1.7d one-way reaction transfer','*INCLUDE,INPUT=cast.inc',
               '*MATERIAL,NAME=steel','*ELASTIC','210000.,.3','*SOLID SECTION,ELSET=TRAVERSE,MATERIAL=steel',
               '*BOUNDARY']
        for node,value in zip(cut,bcs,strict=True):
            lines.extend(f'{node},{d},{d},{u:.13g}' for d,u in enumerate(value,1))
        lines += ['*STEP','*STATIC']
        if force_N:
            nodal, details = map_loads(xyz,bearing,reaction[label])
            lines += ['*CLOAD']
            for node,axis in zip(*np.nonzero(abs(nodal)>1e-12),strict=True):
                lines.append(f'{node},{axis+1},{nodal[node,axis]:.13g}')
            loads[label]=details
        lines += ['*NODE FILE','U,RF','*EL FILE','S','*END STEP']
        inp = work/f'{label}.inp'
        inp.write_text('\n'.join(lines)+'\n',encoding='ascii')
        if level==0:
            (HERE/f'{region}_{label}.inp').write_bytes(inp.read_bytes())
        fea.run_tool([fea.BIN/'ccx.exe','-i',label],work,'Job finished')
        solved[label] = fea.results_frd(inp.with_suffix('.frd'),len(xyz))
        if force_N:
            total = solved[label]['FORC'][cut].sum(axis=0)
            loads[label]['cut_reaction_N'] = total.tolist()
            loads[label]['force_balance_relative'] = abs(force_N+total[2])/force_N

    dr = solved['fatigue']['STRESS']-solved['zero']['STRESS']
    vm = fea.mises(solved['static']['STRESS'])
    principal = np.abs(np.linalg.eigvalsh(fea.stress_tensors(dr))).max(axis=1)
    normals = fea.surface_normals(xyz,tets,faces)
    grad = fea.normal_gradient(xyz,tets,normals,principal)
    n_sigma = fea.notch_support(grad,800.,True)
    allowable,_,_,slope = fea.fkm_parameters(800.,6.3,True)
    mean_tensor = fea.stress_tensors(solved['zero']['STRESS']+dr/2)
    utiliz = (fea.mises(dr)/2+slope*np.maximum(0.,np.linalg.eigvalsh(mean_tensor)[:,-1]))/(allowable*n_sigma)
    d = base.rounded_distance(x,y,176.,74.,20.)
    r20 = active[(abs(d[active])<.35)&(abs(x[active])>=68.)&(abs(y[active])>=17.)&(z[active]>=54.999)]
    core = active[(abs(x[active])<CUT_X_MM-12.)&(abs(y[active])<CUT_Y_MM-12.)]
    regions={}
    for name,nodes in (('R20',r20),('cast_evaluation_region',core)):
        si,fi = nodes[vm[nodes].argmax()], nodes[utiliz[nodes].argmax()]
        regions[name] = dict(static_factor=float(650./vm[si]),fatigue_factor=float(1./utiliz[fi]),
                             static_peak_MPa=float(vm[si]),static_xyz_mm=xyz[si].tolist(),
                             fatigue_xyz_mm=xyz[fi].tolist(),G_per_mm=float(grad[fi]),n_sigma=float(n_sigma[fi]))
    tree = cKDTree(xyz[active])
    def datum(target_list, disp):
        tags = active[tree.query(target_list)[1]]
        pts = xyz[tags]
        displacement = disp[tags]
        slope_xy = np.linalg.lstsq(np.column_stack((np.ones(len(tags)),pts[:,:2])),
                                    displacement[:,2],rcond=None)[0][1:]
        return displacement[:,:2].mean(axis=0),slope_xy,pts.tolist()

    disp = solved['static']['DISP']-solved['zero']['DISP']
    small_u, small_tilt, small_xyz = datum([(u,v,55.) for u in (-80.,80.) for v in (-36.,36.)],disp)
    base_u, base_tilt, base_xyz = datum([(u,v,0.) for u in (-177.,177.) for v in (-103.,103.)],disp)
    local_mm = abs(small_u-base_u)+77.*abs(small_tilt-base_tilt)
    return dict(level=level,nodes=len(active),elements=len(tets),extrapolated_cut_nodes=extrapolated,
                scope='One-way transfer of rigid-backed reactions. Cast flexibility does not feed back into seating.',
                loads=loads,regions=regions,clearance=dict(component_xy_mm=local_mm.tolist(),
                local_srss_mm=hypot(*local_mm),additional_T17_full_frame_bound_mm=.043,
                combined_screen_mm=hypot(*local_mm)+.043,guide_datum_xyz_mm=base_xyz,
                aperture_datum_xyz_mm=small_xyz,limit_mm=.15))


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('levels',nargs='+',type=int,choices=(0,1,2))
    cli.add_argument('--label',default='one_way_cast')
    cli.add_argument('--source',default='rigid',help='Stem of the rigid-backed contact summaries.')
    args=cli.parse_args()
    reaction=json.loads((HERE/f'{args.source}_support_0.json').read_text(encoding='utf-8'))['loads']
    source=json.loads((HERE/f'{args.source}_0.json').read_text(encoding='utf-8'))
    trial=source.get('geometry',TRIAL)
    with TemporaryDirectory(dir=HERE,prefix='cast_transfer_') as directory:
        work=Path(directory)
        reference=boundary.interface_basis(work)
        for level in args.levels:
            record=load_cast(work,args.label,level,reference,reaction,trial)
            if args.source!='rigid':
                record.update(geometry=trial,source_reaction=args.source+'_support_0.json')
            fea.write_json(HERE/f'{args.label}_{level}.json',record)
            print(level,record['regions'],record['clearance']['combined_screen_mm'],flush=True)


if __name__=='__main__':
    main()

