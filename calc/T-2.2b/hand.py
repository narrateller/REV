"""N-mm-MPa comparison before any contact FEA."""
from itertools import product
import json
from math import exp, log10, pi, sqrt
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E_MPa = 210000.
DENSITY_KG_MM3 = 7.85e-6
RELIEF = 315 / 300
SHARES = (.60, .64)
SHOE_X_MM = (5., 205.)
# Pads overhang from the outer spine at the two ends; medial pads also rest
# on the inboard walls. The shoe is necked axially where these walls cross.
TONGUES_X_MM = ((8., 59.), (98., 149.), (177., 205.))
PADS_X_MM = ((-25., 5.), (61., 96.), (151., 175.), (207., 237.))
LOCK_X_MM = (-27., 239.)
LOCK_Y_MM = (112., 165.)
LOCK_Z_MM = (160., 270.)
STROKE_MM = 36.
SHOULDER_Y_MM = 144.
TONGUE_BOTTOM_MM = 30.
HOUSING_X_MM = (-30., 242.)
HOUSING_Y_MM = 216.
BACK_Y_MM = 203.
TOP_Z_MM = 335.
ROOT_RADIUS_MM = 15.
EDGE_RADIUS_MM = 5.
CROWN_MM = .10


def json_read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_write(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def inherited_load():
    prior = json_read(ROOT / "calc/T-1.2b/results.json")
    case = prior["shoe_load"]["samples"]["upper_dose"]["reserve"]["high"]
    press = case["press"]
    x0, x1 = press["contact_x_mm"]
    q = lambda x: 150 * press["radial_at_contact_start_MPa"] * exp(-case["attenuation_per_mm"] * (x-x0))
    force_N = quad(q, x0, x1)[0]
    centroid_mm = quad(lambda x: x*q(x), x0, x1)[0] / force_N
    assert abs(force_N - press["force_N"]) < 1e-6
    assert abs(centroid_mm - press["centroid_x_mm"]) < 1e-9
    return dict(force_300_N=force_N, force_315_N=force_N*RELIEF, centroid_x_mm=centroid_mm,
                pressure_initial_MPa=press["radial_at_contact_start_MPa"],
                decay_per_mm=case["attenuation_per_mm"], contact_x_mm=[x0, x1],
                upper_dose_kg=case["dose_kg"],
                high_lock_force_315_N={str(s): force_N*RELIEF*s for s in SHARES})


def frame_data():
    return yaml.safe_load((ROOT / "design/frame.t17d.yaml").read_text(encoding="utf-8"))


def fatigue(rm_MPa, casting, roughness_um=6.3, notch_support=1.):
    k_R = 1 - (.20 if casting else .22) * log10(roughness_um) * log10(2 * rm_MPa / 400)
    mean = .00035 * rm_MPa + (.05 if casting else -.1)
    j_G = 1.25 if casting else 1.
    allowable_MPa = (.34 if casting else .40)*rm_MPa*k_R*notch_support*10**(-1/15)/(1.5*j_G)
    return allowable_MPa, mean


def strength(stress_MPa, rp_MPa, rm_MPa, casting=False, compression=False):
    allowed_MPa, mean = fatigue(rm_MPa, casting)
    demand_MPa = stress_MPa / RELIEF / 2 * (1 if compression else 1+mean)
    return dict(stress_315_MPa=stress_MPa, static_factor=rp_MPa/stress_MPa if stress_MPa else None,
                fatigue_factor_n_sigma_1=allowed_MPa/demand_MPa if demand_MPa else None)


def symmetric_boxes(y0, y1, x0, x1, z0, z1):
    return [(x0,x1,y0,y1,z0,z1), (x0,x1,-y1,-y0,z0,z1)]


def housing_boxes():
    xa, xb = HOUSING_X_MM
    box = [(xa,198.,-216.,216.,-87.,-60.)]
    box += symmetric_boxes(75.,118.,xa,198.,-60.,20.)
    box += symmetric_boxes(132.,216.,198.,xb,-87.,-60.)
    box += symmetric_boxes(203.,216.,xa,xb,-60.,TOP_Z_MM)
    box += symmetric_boxes(118.,203.,xa,198.,-60.,-35.)
    box += symmetric_boxes(146.,203.,xa,xb,270.,TOP_Z_MM)
    for i, (x0, x1) in enumerate(PADS_X_MM):
        box += symmetric_boxes(95.,146.,x0,x1,270.,TOP_Z_MM)
        if i in (1, 2):
            box += symmetric_boxes(77.,111.,x0,x1,20.,TOP_Z_MM)
            box += symmetric_boxes(108.,203.,x0,x1,110.,158.)
    return box


def shoe_boxes():
    xa, xb = SHOE_X_MM
    box = [(xa,xb,-75.,75.,0.,160.)]
    for x0, x1 in TONGUES_X_MM:
        box += symmetric_boxes(75.,SHOULDER_Y_MM,x0,x1,TONGUE_BOTTOM_MM,160.)
    return box


def union_volume_mm3(boxes):
    axes = [sorted({b[2*i+j] for b in boxes for j in range(2)}) for i in range(3)]
    volume_mm3 = 0.
    for (x0,x1),(y0,y1),(z0,z1) in product(*(zip(axis,axis[1:]) for axis in axes)):
        x,y,z = (x0+x1)/2, (y0+y1)/2, (z0+z1)/2
        if any(a<x<b and c<y<d and e<z<f for a,b,c,d,e,f in boxes):
            volume_mm3 += (x1-x0)*(y1-y0)*(z1-z0)
    return volume_mm3


def beam_element(length_mm, inertia_mm4):
    l = length_mm
    return E_MPa * inertia_mm4 / l**3 * np.array(
        [[12,6*l,-12,6*l],[6*l,4*l*l,-6*l,2*l*l],
         [-12,-6*l,12,-6*l],[6*l,2*l*l,-6*l,4*l*l]])


def beam_contact(load, share, tongues=TONGUES_X_MM, pads=PADS_X_MM):
    """Two axial Euler-Bernoulli beams, unilateral point contacts at pad centers."""
    shoe_centers, roof_centers = [[sum(p)/2 for p in group] for group in (tongues,pads)]
    x0, x1 = load["contact_x_mm"]
    shoe_x = sorted({*SHOE_X_MM, *shoe_centers, x0, x1})
    key_x = sorted({*LOCK_X_MM, *shoe_centers, *roof_centers})
    offset = 2*len(shoe_x)
    size = offset+2*len(key_x)
    elastic = np.zeros((size,size))
    rhs = np.zeros(size)
    keys = []
    for start, stations, width, depth in ((0,shoe_x,75.,160.),(offset,key_x,53.,110.)):
        for j,(a,b) in enumerate(zip(stations,stations[1:])):
            ids = np.arange(start+2*j,start+2*j+4)
            local = beam_element(b-a,width*depth**3/12)
            elastic[np.ix_(ids,ids)] += local
            if start:
                keys.append((ids,local))
            elif a >= x0 and b <= x1:
                for k in range(4):
                    def integrand(x):
                        t = (x-a)/(b-a)
                        shape = (1-3*t*t+2*t**3,(b-a)*(t-2*t*t+t**3),3*t*t-2*t**3,(b-a)*(t**3-t*t))
                        return shape[k]*150*load["pressure_initial_MPa"]*exp(-load["decay_per_mm"]*(x-x0))*share*RELIEF
                    rhs[ids[k]] += quad(integrand,a,b)[0]
    constraints = np.zeros((len(shoe_centers)+len(roof_centers),size))
    for i,x in enumerate(shoe_centers):
        constraints[i,2*shoe_x.index(x)] = 1
        constraints[i,offset+2*key_x.index(x)] = -1
    for i,x in enumerate(roof_centers,len(shoe_centers)):
        constraints[i,offset+2*key_x.index(x)] = 1
    # Enumerate active sets. For seven interfaces this is small and also
    # handles unloaded contacts that would otherwise remove a rigid mode.
    n = len(constraints)
    for mask in sorted(range(1,2**n), key=lambda i: (-i.bit_count(),i)):
        active = [i for i in range(n) if mask & (1 << i)]
        eq = constraints[active]
        try:
            sol = np.linalg.solve(np.block([[elastic,eq.T],[eq,np.zeros((len(active),len(active)))]]),
                                  np.r_[rhs,np.zeros(len(active))])
        except np.linalg.LinAlgError:
            continue
        disp = sol[:size]
        reactions = np.zeros(n)
        reactions[active] = sol[size:]
        if min(reactions) >= 0. and max(constraints@disp) < 1e-7:
            key_moment_Nmm = max(max(abs((k@disp[i])[[1,3]])) for i,k in keys)
            return reactions[:len(tongues)], reactions[len(tongues):], key_moment_Nmm, max(disp[:offset:2])
    raise ValueError("Unsupported axial beam contact layout")


def a_case(load, share, tongues=TONGUES_X_MM, pads=PADS_X_MM):
    shoe, roof, key_moment_Nmm, shoe_motion_mm = beam_contact(load,share,tongues,pads)
    force_N = load["high_lock_force_315_N"][str(share)]
    for bands, reactions in ((tongues,shoe),(pads,roof)):
        assert abs(sum(reactions)-force_N) < 1e-4
        assert abs(sum(r*sum(b)/2 for b,r in zip(bands,reactions))-force_N*load["centroid_x_mm"]) < .005
    shoe_rows = []
    for (a,b),force in zip(tongues,shoe):
        depth = 160-TONGUE_BOTTOM_MM
        bend_MPa = 6*force*(128-75)/((b-a)*depth**2)
        shear_MPa = 1.5*force/((b-a)*depth)
        shoe_rows.append(dict(x_mm=[a,b],force_N=force,bending_MPa=bend_MPa,shear_MPa=shear_MPa,
                              effective_mean_bearing_MPa=force/((b-a-10)*27),
                              **strength(sqrt(bend_MPa**2+3*shear_MPa**2),600.,800.)))
    roof_rows = []
    for i,((a,b),force) in enumerate(zip(pads,roof)):
        arm_mm = (128-94)*(209.5-128)/(209.5-94) if i in (1,2) else 209.5-128
        stress_MPa = 6*force*arm_mm/((b-a)*65**2)
        roof_rows.append(dict(x_mm=[a,b],force_N=force,effective_mean_bearing_MPa=force/((b-a-10)*27),
                              **strength(stress_MPa,650.,800.,casting=True)))
    key_bending = strength(key_moment_Nmm*6/(53*110**2),700.,900.)
    return dict(shoe_pads=shoe_rows,roof_pads=roof_rows,key_axial_bending=key_bending,
                shoe_axial_motion_300_mm=shoe_motion_mm/RELIEF)


def b_case(load, share):
    from mass import (PORTAL_X_MM, PORTAL_HEIGHT_MM, POST_X_MM, LOCK_B_Z_MM,
                      TIE_Y_MM, TIE_D_MM, TIE_CLEAR_D_MM, TIE_GRIP_MM,
                      TIE_SEAT_OD_MM, TIE_SEAT_ID_MM)
    x_support = [sum(limits)/2 for limits in PORTAL_X_MM]
    a = load["centroid_x_mm"]-x_support[0]
    b = x_support[1]-load["centroid_x_mm"]
    total_N = load["force_315_N"]
    shoe_N = share * total_N
    lead_fraction = a / (a+b)
    force_end_N = total_N*lead_fraction
    # Centered pin+tie portal. Both applied supports lie between the ties.
    # The GK estimate is the separate, conditional moment -> tie lever check.
    yp = 93.5
    high_tie_N = force_end_N*(.5+(2*share-1)*yp/(2*TIE_Y_MM))
    low_tie_N = force_end_N-high_tie_N
    d_mm, pitch_mm = TIE_D_MM, 4.
    area_mm2 = 976.
    assert d_mm == 39.
    bolt_compliance = (TIE_GRIP_MM+.8*d_mm)/(E_MPa*area_mm2)
    seat_mm2 = pi/4*(TIE_SEAT_OD_MM**2-TIE_SEAT_ID_MM**2)
    post_mm2 = (POST_X_MM[1][1]-POST_X_MM[1][0])*54 - pi/4*TIE_CLEAR_D_MM**2
    post_compliance = 367/(E_MPa*post_mm2)
    # 45-degree growth between seat and joint, clipped to the post section.
    def clamped_section_mm2(z):
        return min(post_mm2,pi/4*((TIE_SEAT_OD_MM+2*z)**2-TIE_CLEAR_D_MM**2))
    clamp_compliance = post_compliance + quad(lambda z: 1/(E_MPa*clamped_section_mm2(z)),
                                              0,PORTAL_HEIGHT_MM,epsabs=1e-13)[0]
    phi_release = post_compliance/(bolt_compliance+clamp_compliance)
    phi_bound = clamp_compliance/(bolt_compliance+clamp_compliance)
    settling_N = .04/(bolt_compliance+clamp_compliance)
    fm_min, fm_max = 535000.,570000.
    service_N = fm_max+phi_bound*high_tie_N
    amp_MPa = phi_release*high_tie_N/(2*RELIEF*area_mm2)
    amp_upper_MPa = phi_bound*high_tie_N/(2*RELIEF*area_mm2)
    mean_ratio = (fm_max+phi_bound*high_tie_N/(2*RELIEF))/(area_mm2*1100)
    sv_MPa = .85*(150/d_mm+45)
    sg_MPa = sv_MPa*(2-mean_ratio)
    x0,x1 = load["contact_x_mm"]
    q = lambda x: share*RELIEF*150*load["pressure_initial_MPa"]*exp(-load["decay_per_mm"]*(x-x0))
    left_N = shoe_N*(1-lead_fraction)
    xmax = brentq(lambda x: quad(q,x0,x)[0]-left_N, x0,x1)
    moment_Nmm = left_N*(xmax-x_support[0])-quad(lambda x: q(x)*(xmax-x),x0,xmax)[0]
    key_height_mm = LOCK_B_Z_MM[1]-LOCK_B_Z_MM[0]
    key_width_mm = 66.
    key_I_mm4 = key_width_mm*key_height_mm**3/12
    portal_moment_Nmm = high_tie_N*(TIE_Y_MM-yp)
    portal_width_mm = PORTAL_X_MM[1][1]-PORTAL_X_MM[1][0]
    key_motion_mm = shoe_N*a*a*b*b/(3*E_MPa*key_I_mm4*(a+b)*RELIEF)
    shoe_loc_mm = load["force_300_N"]*190**3/(48*E_MPa*(200*160**3/12))
    portal_local_mm = force_end_N*(2*TIE_Y_MM)**3/(48*E_MPa*(portal_width_mm*PORTAL_HEIGHT_MM**3/12))/RELIEF
    return dict(conditional_GK_lever_tie_side_N=shoe_N*71/150, actual_portal_far_end_total_N=force_end_N,
                actual_portal_far_high_tie_N=high_tie_N, actual_portal_far_low_tie_N=low_tie_N,
                actual_portal_near_high_tie_N=high_tie_N*b/a,
                x_support_mm=x_support,stress_area_mm2=area_mm2,
                phi_at_interface=phi_release,phi_upper_bound=phi_bound,
                assembly_preload_N=[fm_min,fm_max],settling_loss_N=settling_N,
                residual_clamp_315_N=fm_min-settling_N-(1-phi_release)*high_tie_N,
                residual_clamp_315_phi_zero_N=fm_min-settling_N-high_tie_N,
                axial_service_factor=1100*area_mm2/service_N,
                thread_amplitude_MPa=amp_MPa,thread_amplitude_upper_MPa=amp_upper_MPa,
                thread_mean_force_ratio=mean_ratio,thread_SG_limit_MPa=sg_MPa,
                thread_SG_factor_at_interface=sg_MPa/(1.35*amp_MPa),
                thread_SG_factor_upper_bound=sg_MPa/(1.35*amp_upper_MPa),
                washer_bearing_MPa=service_N/seat_mm2,post_full_preload_mean_MPa=fm_max/post_mm2,
                key_moment_Nmm=moment_Nmm,key_moment_x_mm=xmax,
                key=strength(moment_Nmm*key_height_mm/(2*key_I_mm4),700.,900.),
                portal_moment_Nmm=portal_moment_Nmm,
                portal=strength(6*portal_moment_Nmm/(portal_width_mm*PORTAL_HEIGHT_MM**2),700.,900.),
                shoe_end_contact_projected_mean_MPa=shoe_N/(200*32),
                peak_strip_shoe_contact_if_no_axial_redistribution_MPa=q(x0)/32,
                upper_end_contact_projected_mean_MPa=force_end_N*share/(portal_width_mm*63),
                key_motion_300_mm=key_motion_mm,shoe_flexure_300_mm=shoe_loc_mm,
                portal_motion_central_point_screen_300_mm=portal_local_mm,
                shoe_plus_key_plus_portal_screen_300_mm=shoe_loc_mm+key_motion_mm+portal_local_mm)

def run():
    load = inherited_load()
    data = dict(load=load,a=json_read(HERE/"reference/hand_a_round1.json"),
                b={str(s):b_case(load,s) for s in SHARES})
    json_write(HERE/"hand.json",data)
    return data


if __name__ == "__main__":
    run()

