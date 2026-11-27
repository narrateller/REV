"""Closed-frame screen in N, mm and MPa, by complementary energy."""

from dataclasses import dataclass
from functools import lru_cache
from math import pi

import numpy as np


E_MPa = 210_000.
NU = .30
G_MPa = E_MPa / (2 * (1 + NU))
ECCENTRICITY_MM = 27.72
FACE_HALF_WIDTH_MM = 75.
FACE_HALF_HEIGHT_MM = 30.
LENGTH_MM = 90.
DENSITY_KG_MM3 = 7.85e-6
FORGED = (700., 900., False)
CAST = (650., 800., True)
INNER_Z_MM = 42.


@dataclass(frozen=True)
class Ring:
    material: str
    side_half_mm: float
    band_half_mm: float
    inner_R_mm: float
    outer_R_mm: float
    inner_z_mm: float = INNER_Z_MM
    lamellae: int = 1
    seat_half_mm: float = FACE_HALF_WIDTH_MM

    @property
    def inner_y_mm(self):
        return self.seat_half_mm + self.inner_R_mm

    @property
    def grade(self):
        if self.material == "cast":
            return CAST
        return (800.,1000.,False) if self.lamellae > 1 else FORGED

    def ring_and_liner_mass_kg(self):
        # Ring and form-fitting liners together; no credit for gate relief.
        gross_mm2 = 4 * self.side_half_mm * self.band_half_mm
        corners_mm2 = (4 - pi) * (self.outer_R_mm**2 - 1.)
        return (gross_mm2 - corners_mm2 - 150. * 60.) * LENGTH_MM * DENSITY_KG_MM3


def skew_weight(y_mm, eccentricity_mm, seat_half_mm=FACE_HALF_WIDTH_MM):
    """Positive pressure polynomial on the complete 150 mm working width."""
    s = np.asarray(y_mm) / seat_half_mm
    a = 3 * eccentricity_mm / seat_half_mm
    b = 1.5 * max(0., abs(a) - .95)
    return 1 + a*s + b*(s*s - 1/3)


def cross(yz, other_yz):
    return yz[..., 0] * other_yz[..., 1] - yz[..., 1] * other_yz[..., 0]


def rounded_box_sdf_mm(yz_mm, half_yz_mm, radius_mm):
    delta_mm = np.abs(yz_mm) - half_yz_mm + radius_mm
    return (np.linalg.norm(np.maximum(delta_mm, 0.), axis=-1)
            + np.minimum(0., np.max(delta_mm, axis=-1)) - radius_mm)


@lru_cache(maxsize=64)
def section_grid(geometry, subdivisions=20, socket=None):
    """Counterclockwise continuous frame following the structural aperture."""
    radius_mm = geometry.inner_R_mm
    dy_mm, dz_mm = geometry.seat_half_mm, geometry.inner_z_mm - radius_mm
    s = (np.arange(subdivisions) + .5) / subdivisions
    positions, outward, lengths, bend_radius = [], [], [], []
    for quadrant in range(4):
        angle = quadrant * pi / 2
        rotation = np.rint([[np.cos(angle), -np.sin(angle)],
                            [np.sin(angle), np.cos(angle)]])
        run_mm = (dz_mm,dy_mm)[quadrant % 2]
        half_mm = (geometry.inner_y_mm, geometry.inner_z_mm)[quadrant % 2]
        positions.extend(np.column_stack([np.full_like(s,half_mm),run_mm*(2*s-1)]) @ rotation.T)
        outward.extend(np.tile(rotation[:,0],(len(s),1)))
        lengths.extend(np.full_like(s,2*run_mm/subdivisions))
        bend_radius.extend(np.zeros_like(s))
        normals = np.column_stack([np.cos(s*pi/2),np.sin(s*pi/2)])
        corner = np.array([dy_mm,dz_mm]) if quadrant % 2 == 0 else np.array([dz_mm,dy_mm])
        positions.extend((corner + radius_mm*normals) @ rotation.T)
        outward.extend(normals @ rotation.T)
        lengths.extend(np.full_like(s,radius_mm*pi/(2*subdivisions)))
        bend_radius.extend(np.full_like(s,radius_mm))
    inside = np.array(positions)
    n = np.array(outward)
    ri_mm = np.array(bend_radius)
    dl_mm = np.array(lengths)
    t = np.column_stack([-n[:,1],n[:,0]])

    lo_mm = np.zeros(len(inside))
    hi_mm = np.full(len(inside),2 * max(geometry.side_half_mm,geometry.band_half_mm))
    half_yz_mm = np.array([geometry.side_half_mm,geometry.band_half_mm])
    for _ in range(31):
        mid_mm = (lo_mm+hi_mm)/2
        within = rounded_box_sdf_mm(inside+mid_mm[:,None]*n,half_yz_mm,geometry.outer_R_mm) < 0
        lo_mm = np.where(within,mid_mm,lo_mm)
        hi_mm = np.where(within,hi_mm,mid_mm)
    h_mm = (lo_mm + hi_mm)/2
    if h_mm.min() < 0.1:
        raise ValueError("The outer profile intersects the seat")
    centre = inside + h_mm[:,None]*n/2
    curvature = np.divide(1.,ri_mm+h_mm/2,out=np.zeros_like(ri_mm),where=ri_mm>0)

    # Winkler-Bach section flexibility. Strain=(a+b*v)/(1+v/Rc).
    a,w = np.polynomial.legendre.leggauss(64 if socket else 16)
    lever_mm = h_mm[:,None]*a/2
    da_mm2 = h_mm[:,None]*w/2
    if socket:
        sample_mm = centre[:, None, :] + lever_mm[:, :, None] * n[:, None, :]
        da_mm2[inside_socket(sample_mm, socket)] = 0.
    net_h_mm = da_mm2.sum(axis=1)
    jac = 1 + curvature[:,None]*lever_mm
    axial_bending = np.stack([np.ones_like(lever_mm),lever_mm],axis=-1)
    elastic = E_MPa * np.einsum("sqi,sqj,sq->sij",axial_bending,axial_bending,da_mm2/jac)
    flex = np.linalg.inv(elastic)
    measure_mm = dl_mm * (1 + np.divide(h_mm/2,ri_mm,out=np.zeros_like(h_mm),where=ri_mm>0))
    return inside,n,t,ri_mm,h_mm,centre,dl_mm,curvature,flex,measure_mm,net_h_mm


def inside_socket(points, socket):
    y0_mm, y1_mm, z0_mm, z1_mm = socket
    y_mm = np.abs(points[...,0])
    z_mm = points[...,1]
    return (y0_mm < y_mm) & (y_mm < y1_mm) & (z0_mm < z_mm) & (z_mm < z1_mm)


def frame(geometry,p_MPa,mu,eccentricity_mm,subdivisions=20,*,detail=True,socket=None,extra_loads=()):
    """Find three redundant cut resultants from closed-loop compatibility."""
    inside,n,t,ri_mm,h_mm,centre,dl_mm,curvature,flex,measure_mm,net_h_mm = section_grid(geometry,subdivisions,socket)
    flats = ri_mm == 0
    horizontal = flats & (n[:,1] != 0)
    vertical = flats & (n[:,0] != 0)
    pressure_MPa = np.zeros(len(n))
    vals = skew_weight(inside[horizontal,0],eccentricity_mm,geometry.seat_half_mm)
    pressure_MPa[horizontal] = p_MPa * vals / vals.mean() * 75. / geometry.seat_half_mm
    # The side liners transmit 60 mm of wall load into the available flats.
    pressure_MPa[vertical] = p_MPa * 30. / (geometry.inner_z_mm - geometry.inner_R_mm)
    dforce_N = pressure_MPa[:,None] * dl_mm[:,None] * n
    dmoment_Nmm = cross(inside,dforce_N)
    # The load through the roof socket and its balancing force at the floor
    # close in the ring. Apply both at their actual Y coordinate.
    for y_mm, load_N_per_mm in extra_loads:
        for side in (1, -1):
            idx = int(np.argmin(np.linalg.norm(inside - [y_mm,side*geometry.inner_z_mm],axis=1)))
            dforce_N[idx,1] += side * load_N_per_mm
            dmoment_Nmm[idx] += y_mm * side * load_N_per_mm
    f_N = np.cumsum(dforce_N,axis=0) - dforce_N/2
    m0_Nmm = np.cumsum(dmoment_Nmm) - dmoment_Nmm/2
    m_Nmm = m0_Nmm - cross(centre,f_N)
    assert np.allclose(dforce_N.sum(axis=0),0.) and abs(dmoment_Nmm.sum()) < 1e-7

    # On the positive cut face N and V reverse the force projections.
    # Positive M produces tension at positive (outward) fibre lever.
    moment_basis_mm = np.column_stack([centre[:,1],-centre[:,0],np.ones(len(centre))])
    sect_basis = -np.stack([np.column_stack([t,np.zeros(len(t))]),moment_basis_mm],axis=1)
    sect_free = -np.column_stack([np.sum(f_N*t,axis=1),m_Nmm])
    v_basis = -np.column_stack([n,np.zeros(len(n))])
    v_free = -np.sum(f_N*n,axis=1)
    shear_flex_mm_N = 1. / ((5/6) * G_MPa * net_h_mm)
    matrix = np.einsum("sri,srt,stj,s->ij",sect_basis,flex,sect_basis,measure_mm)
    matrix += np.einsum("si,sj,s,s->ij",v_basis,v_basis,shear_flex_mm_N,measure_mm)
    rhs = np.einsum("sri,srt,st,s->i",sect_basis,flex,sect_free,measure_mm)
    rhs += np.einsum("si,s,s,s->i",v_basis,v_free,shear_flex_mm_N,measure_mm)
    redundant = np.linalg.solve(matrix,-rhs)
    section = sect_free + sect_basis @ redundant
    v_N = v_free + v_basis @ redundant

    fibers = np.linspace(-1.,1.,41 if socket else 17)
    r_mm = h_mm[:,None]*fibers/2
    strain = np.einsum("sij,sj->si",flex,section)
    tangential_MPa = E_MPa*(strain[:,0,None] + strain[:,1,None]*r_mm)/(1+curvature[:,None]*r_mm)
    radial_MPa = np.zeros_like(tangential_MPa)
    radial_MPa[:,0] = -pressure_MPa
    shear_MPa = 1.5 * v_N[:,None]/net_h_mm[:,None] * (1-fibers**2)
    ax_shear_MPa = np.zeros_like(tangential_MPa)
    ax_shear_MPa[:,0] = mu * pressure_MPa
    vm_MPa = np.sqrt(tangential_MPa**2 + radial_MPa**2 - tangential_MPa*radial_MPa
                     + 3*(shear_MPa**2+ax_shear_MPa**2))
    rp_MPa, rm_MPa, casting = geometry.grade
    surface = 1 - (.20 if casting else .22)*np.log10(6.3)*np.log10(2*rm_MPa/400)
    amplitude_MPa = (.34 if casting else .40)*rm_MPa*surface*10**(-1/15)/(1.5*(1.25 if casting else 1.))
    mean_sensitivity = .00035*rm_MPa + (.05 if casting else -.10)
    local_mean_MPa = np.maximum(0.,tangential_MPa)
    equivalent_MPa = (vm_MPa + mean_sensitivity*local_mean_MPa)*300/630
    if socket:
        sample_mm = centre[:,None,:] + r_mm[:,:,None] * n[:,None,:]
        missing = inside_socket(sample_mm, socket)
        equivalent_MPa[missing] = 0.
        vm_MPa[missing] = 0.
    # Inner fibre bending concentration, USBR EM 14 eq. (4).
    kt = np.ones(len(n))
    arc = ~flats
    rn_mm = h_mm[arc] / np.log1p(h_mm[arc]/ri_mm[arc])
    e_mm = ri_mm[arc] + h_mm[arc]/2 - rn_mm
    kt[arc] = h_mm[arc]*(rn_mm-ri_mm[arc])/(6*ri_mm[arc]*e_mm)
    location = np.unravel_index(equivalent_MPa.argmax(),equivalent_MPa.shape)
    result = {
        "static_factor": float(rp_MPa/vm_MPa.max()),
        "FKM": float(amplitude_MPa/equivalent_MPa.max()),
        "corner_Kt_max": float(kt.max()),
        "limiting_section_inner_yz_mm": inside[location[0]].tolist(),
        "limiting_fibre_fraction": float(fibers[location[1]]),
        "limiting_MPa": float(vm_MPa[location]),
        "minimum_wall_mm": float(h_mm.min()),
        "minimum_net_wall_mm": float(net_h_mm.min()),
        "upper_peak_pressure_MPa": float(pressure_MPa[horizontal].max()),
        "side_pressure_MPa": float(pressure_MPa[vertical].max()),
        "complementary_energy_per_mm_N": float(
            (np.einsum("si,sij,sj->s",section,flex,section)
             + v_N**2*shear_flex_mm_N) @ measure_mm/2),
    }
    if detail:
        result.update(section_yz_mm=inside.tolist(),normal_N_per_mm=section[:,0].tolist(),
                      moment_Nmm_per_mm=section[:,1].tolist(),shear_N_per_mm=v_N.tolist(),
                      centroid_yz_mm=centre.tolist())
    return result
