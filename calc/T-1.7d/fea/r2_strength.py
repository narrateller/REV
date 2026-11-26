"""Local fatigue and depth evaluation for the second outlet study."""
import numpy as np

import frame_fea as fea


def fatigue(static, start, end, gradient, rp02_MPa, rm_MPa, *, casting=False):
    """T-1.7 amplitude and support with a signed Haigh ratio for the forging."""
    delta = end - start
    mean = (end + start) / 2
    amplitude = fea.mises(delta) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(fea.stress_tensors(delta))
    rows = np.arange(len(delta))
    dominant = np.abs(eigenvalues).argmax(axis=1)
    direction = eigenvectors[rows, :, dominant]
    normal_amplitude = np.abs(eigenvalues[rows, dominant]) / 2
    mean_normal = np.einsum('ij,ijk,ik->i', direction, fea.stress_tensors(mean), direction)
    positive_mean = np.maximum(0., np.linalg.eigvalsh(fea.stress_tensors(mean))[:, -1])
    allowable, k_rough, j_geometry, M = fea.fkm_parameters(rm_MPa, 6.3, casting, forging=not casting)
    ratio = np.divide(mean_normal, normal_amplitude, out=np.zeros_like(mean_normal), where=normal_amplitude>1e-10)
    haigh = np.select([ratio <= -1., ratio <= 1., ratio < 3.],
                     [1.-M, 1.+M*ratio, (1.+M)*(3.+M*ratio)/(3.+M)],
                     default=3.*(1.+M)**2/(3.+M))
    n_sigma = fea.notch_support(gradient, rm_MPa, casting)
    design_amplitude = allowable*n_sigma
    t17_util = (amplitude+M*positive_mean)/design_amplitude
    # Credit compression only while all mean principals are compressive.
    # Keep the T-1.7 positive-mean screen for mixed stress states and casting.
    compressive = (mean_normal < 0.) & (positive_mean < 1e-6) & (not casting)
    util = np.where(compressive, amplitude*haigh/design_amplitude, t17_util)
    return dict(yield_MPa=rp02_MPa, static_mises_MPa=fea.mises(static),
                amplitude_MPa=amplitude, normal_amplitude_MPa=normal_amplitude,
                signed_mean_normal_MPa=mean_normal, M_sigma=M, G_per_mm=gradient,
                n_sigma=n_sigma, k_R=k_rough, j_G=j_geometry, utilization=util,
                T17_utilization=t17_util, compression_correction=compressive,
                K_AK=np.where(compressive, 1./haigh, 1.),
                signed_peak_range_normal_MPa=eigenvalues[rows, dominant])


def summarize(values, xyz_mm, mask):
    ids = np.flatnonzero(mask)
    si = ids[values['static_mises_MPa'][ids].argmax()]
    fi = ids[values['utilization'][ids].argmax()]
    keys = ('amplitude_MPa', 'normal_amplitude_MPa', 'signed_mean_normal_MPa',
            'G_per_mm', 'n_sigma', 'K_AK', 'signed_peak_range_normal_MPa')
    return dict(static_factor=float(values['yield_MPa']/values['static_mises_MPa'][si]),
                fatigue_factor=float(1./values['utilization'][fi]),
                fatigue_factor_T17=float(1./values['T17_utilization'][ids].max()),
                M_sigma=values['M_sigma'], k_R=values['k_R'], j_G=values['j_G'],
                static_mises_MPa=float(values['static_mises_MPa'][si]),
                compressed=bool(values['compression_correction'][fi]),
                static_xyz_mm=xyz_mm[si].tolist(), fatigue_xyz_mm=xyz_mm[fi].tolist(),
                **{key: float(values[key][fi]) for key in keys})
