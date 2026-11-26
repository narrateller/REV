"""Displacement boundary for the outlet cut from the T-1.7 chamber traverse.

N, mm, MPa. Four quarter-traverse load bases use the installed column
preload and the elastic sharing of inner collar and outer nut reactions.
"""
from pathlib import Path

import numpy as np
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

import frame_fea as frame
from frame_analytic import ECC_mm, PRELOAD_N, PRELOAD_SCATTER, STATIC_N, VARIANTS, column


def interface_basis(work):
    variant = next(v for v in VARIANTS if v.name == 'cast').at_end('chamber')
    geo_text, _, _, _ = frame.model(variant, 'chamber', 0)
    geo = work/'reference_chamber.geo'
    geo.write_text(geo_text, encoding='ascii')
    frame.run_tool([frame.BIN/'gmsh.exe', geo.name, '-3', '-order', '2', '-format', 'msh2',
                    '-o', 'reference_chamber.msh', '-nt', '1', '-nopopup'], work, 'Done writing')
    xyz, tets, active, faces = frame.read_mesh(work/'reference_chamber.msh')
    forces, _, _ = frame.load_data(variant, 'chamber', xyz, faces)
    frame.write_mesh_include(work/'reference_chamber.inc', xyz, tets, active)
    fields = {}
    for mode in frame.MODES:
        sets, bcs = frame.restraints(xyz, active, variant.depth_mm, mode)
        inp = work/f'reference_{mode}.inp'
        frame.input_deck(inp, 'reference_chamber.inc', sets, bcs, forces[mode])
        frame.run_tool([frame.BIN/'ccx.exe', '-i', inp.stem], work, 'Job finished')
        frd = inp.with_suffix('.frd')
        fields[mode] = frame.results_frd(frd, len(xyz))['DISP'][active]
        frd.unlink()
    fields['centred'] -= fields['preload']
    return xyz[active], fields, column(variant)


def cut_field(reference, cut_xyz_mm):
    xyz, fields, tie = reference
    q = cut_xyz_mm.copy()
    q[:, :2] = abs(q[:, :2])
    signs = np.where(cut_xyz_mm[:, :2] >= 0., 1., -1.)
    output = {}
    extrapolated = np.zeros(len(q), dtype=bool)
    for mode, field in fields.items():
        sampled = LinearNDInterpolator(xyz, field)(q)
        missing = ~np.isfinite(sampled).all(axis=1)
        extrapolated |= missing
        if missing.any():
            sampled[missing] = NearestNDInterpolator(xyz, field)(q[missing])
        sampled[:, :2] *= signs
        if mode in ('ex', 'ey'):
            sampled *= signs[:, 0 if mode == 'ex' else 1, None]
        output[mode] = sampled
    return output, int(extrapolated.sum()), tie


def displacements(fields, tie, force_N, eccentricity_mm, preload):
    multiplier = {'min': 1.-PRELOAD_SCATTER-tie['embedment_loss_N']/PRELOAD_N,
                  'max': 1.+PRELOAD_SCATTER}[preload]
    return multiplier*fields['preload'] + (force_N/STATIC_N)*(
        fields['centred'] + (eccentricity_mm[0]/ECC_mm)*fields['ex'] +
        (eccentricity_mm[1]/ECC_mm)*fields['ey'])

