"""Integrate FE section stresses and compare with hand equilibrium of the cut."""
from itertools import combinations

import numpy as np

from section_check import shape_functions

EDGES = tuple(combinations(range(4), 2))


def section_integrals(xyz, elements, stress_MPa, y_mm):
    # Degree-four quadrature accounts for the linear moment arm times the
    # quadratic interpolated stress in each section triangle.
    a, b = .445948490915965, .091576213509771
    barycentric = np.array([[v, v, 1-2*v] for v in (a,b)]
                           + [[v, 1-2*v, v] for v in (a,b)]
                           + [[1-2*v, v, v] for v in (a,b)])
    q_weights = np.array([.223381589678011, .109951743655322] * 3)
    area_mm2, axial_N, shear_N, moment_about_origin_Nmm = 0., 0., 0., 0.
    tags = np.asarray([nodes for _, nodes in elements])
    y_coords = xyz[tags[:, :4], 1]
    for nodes in tags[(y_coords.min(axis=1) <= y_mm) & (y_coords.max(axis=1) > y_mm)]:
        corners = xyz[nodes[:4]]
        crossings = []
        for i, j in EDGES:
            left, right = corners[i], corners[j]
            if min(left[1], right[1]) <= y_mm < max(left[1], right[1]):
                f = (y_mm - left[1]) / (right[1] - left[1])
                crossings.append(left + f * (right - left))
        poly = np.unique(np.round(crossings, decimals=9), axis=0)
        if len(poly) < 3:
            continue
        center = poly.mean(axis=0)
        angle = np.arctan2(poly[:, 2] - center[2], poly[:, 0] - center[0])
        poly = poly[np.argsort(angle)]
        mapping = (corners[1:] - corners[0]).T
        for i in range(1, len(poly) - 1):
            tri = poly[[0, i, i+1]]
            d = (tri[1:] - tri[:1])[:, [0,2]]
            area = abs(d[0,0]*d[1,1] - d[0,1]*d[1,0]) / 2
            q = barycentric @ tri
            local3 = np.linalg.solve(mapping, (q - corners[0]).T).T
            local = np.column_stack((1. - local3.sum(axis=1), local3))
            syy, tyz = (shape_functions(local) @ stress_MPa[nodes][:, [1,4]]).T
            area_mm2 += area
            axial_N += area * float(q_weights @ syy)
            shear_N += area * float(q_weights @ tyz)
            moment_about_origin_Nmm += area * float(q_weights @ (syy * q[:, 2]))
    return area_mm2, axial_N, shear_N, moment_about_origin_Nmm


def hand_comparison(xyz, groups, stress, loads, seats, springs):
    out = {}
    for label, body, y_cut_mm in (("shoe_inboard", "SHOE", 102.),
                                   ("shoe_wing", "SHOE", 137.),
                                   ("floor_wing", "FLOOR", 137.)):
        force = loads[0 if body == "SHOE" else 1].copy()
        for name, (top, bottom, _) in seats.items():
            tags, weights, _ = top if body == "SHOE" else bottom
            sign = -1 if body == "SHOE" else 1
            force[tags] += sign * weights * springs[name]["spring_force_N"]
        distance = xyz[:, 1] - y_cut_mm
        region = distance > 0.
        hand_shear_N = float(force[region].sum())
        hand_moment_Nmm = -float(force[region] @ distance[region])
        area_mm2, axial_N, shear_N, moment_Nmm = section_integrals(xyz, groups[body], stress, y_cut_mm)
        out[label] = dict(y_cut_mm=y_cut_mm, area_mm2=area_mm2,
                          axial_resultant_FEA_N=axial_N,
                          average_shear_hand_MPa=hand_shear_N/area_mm2,
                          average_shear_FEA_MPa=shear_N/area_mm2,
                          bending_hand_Nmm=hand_moment_Nmm, bending_FEA_Nmm=moment_Nmm,
                          shear_error_fraction=abs(shear_N-hand_shear_N)/abs(hand_shear_N),
                          moment_error_fraction=abs(moment_Nmm-hand_moment_Nmm)/abs(hand_moment_Nmm))
    return out

