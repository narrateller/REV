"""VDI 2230 load and strength screens for the four preloaded through-studs."""
from math import hypot, pi, sqrt, tan
from itertools import product

import numpy as np
from scipy.integrate import quad

from hand import E_MPa, RELIEF, inherited_load, b_case
from mass import (POST_X_MM, PORTAL_X_MM, TIE_Y_MM, TIE_SEAT_OD_MM,
                  TIE_SEAT_ID_MM, TIE_D_MM, TIE_GRIP_MM, PORTAL_HEIGHT_MM,
                  B_POST_Z_MM, HYDRAULIC_TOOL_PROJECTION_MM)

RP_MPa = 1100.
RM_MPa = 1220.
RM_MAX_ACCEPTANCE_MPa = 1350.
PROOF_MPa = 970.
NUT_PROOF_N = 1171000.
SEAT_RP_MPa = (700., 650.)
TOOL_CAPACITY_N = 791000.
TOOL_DIAMETER_MM = 136.
TOOL_HEIGHT_MM = 147.
NUT_HEIGHT_MM = 44.
NUT_WIDTH_ACROSS_FLATS_MM = 60.
SPREADER_THICKNESS_MM = 14.
POST_Y_MM = (162., 216.)
PLATES_X_MM = ((-64.,1.),(182.,256.))


def seat_area_mm2(x_center_mm, x_limits_mm, outer_d_mm):
    """Effective annular support clipped to the lug outline."""
    r, ri = outer_d_mm/2, TIE_SEAT_ID_MM/2
    y0, y1 = (y-TIE_Y_MM for y in POST_Y_MM)

    def chord(x, radius):
        if abs(x) >= radius:
            return 0.
        h = sqrt(radius**2-x**2)
        return max(0., min(h, y1)-max(-h, y0))

    a, b = max(-r,x_limits_mm[0]-x_center_mm), min(r,x_limits_mm[1]-x_center_mm)
    pivots = {value for radius in (r,ri) for value in (-radius,radius)}
    for y in (y0,y1):
        if r > abs(y):
            pivots.update((-sqrt(r*r-y*y),sqrt(r*r-y*y)))
    return quad(lambda x: chord(x,r)-chord(x,ri),a,b,
                points=sorted(v for v in pivots if a<v<b),epsabs=1e-7)[0]


def post_section(post_x_mm, tie_x_mm):
    width, depth = post_x_mm[1]-post_x_mm[0], POST_Y_MM[1]-POST_Y_MM[0]
    rectangle_area = width*depth
    center_rect = sum(post_x_mm)/2
    radius = TIE_SEAT_ID_MM/2
    hole_area = pi*radius**2
    hole_inertia = pi*radius**4/4
    area = rectangle_area-hole_area
    center = (rectangle_area*center_rect-hole_area*tie_x_mm)/area
    ix = width*depth**3/12-hole_inertia
    iy = depth*width**3/12+rectangle_area*(center_rect-center)**2
    iy -= hole_inertia+hole_area*(tie_x_mm-center)**2
    return area,center,ix,iy


def eccentric_yoke(load, diameter_mm, shank_d_mm, support):
    """A transverse beam on rotational springs, from slope-deflection and equilibrium."""
    span = 2*TIE_Y_MM
    x_center = sum(PORTAL_X_MM[support])/2
    x_left, x_right = (sum(strip)/2 for strip in PORTAL_X_MM)
    front_fraction = (load["centroid_x_mm"]-x_left)/(x_right-x_left)
    force_N = load["force_315_N"] * (front_fraction if support else 1-front_fraction)
    offsets = [TIE_Y_MM-93.5, TIE_Y_MM+93.5]
    loads = np.array([.36,.64])*force_N
    offsets = np.asarray(offsets)
    near = span-offsets
    reaction = np.array([loads@near/span,loads@offsets/span])
    fixed_end = np.array([loads@(offsets*near**2), -loads@(offsets**2*near)])/span**2
    area, centroid, ix, iy = post_section(POST_X_MM[support],x_center)
    arm = B_POST_Z_MM[1]-B_POST_Z_MM[0]
    k_post = E_MPa*ix/arm
    k_stud = E_MPa*pi*shank_d_mm**4/64/(TIE_GRIP_MM+.8*diameter_mm)
    width = PORTAL_X_MM[support][1]-PORTAL_X_MM[support][0]
    flexure = E_MPa*width*PORTAL_HEIGHT_MM**3/12
    rows = []
    for restraint in (1.,4.):
        kb, kp = restraint*k_stud, restraint*k_post
        rotations = np.linalg.solve(2*flexure/span*np.array([[2.,1.],[1.,2.]])
                                    +(kb+kp)*np.eye(2),fixed_end)
        rows.append(dict(end_restraint_coefficient=restraint,
            external_axial_N=reaction.tolist(), rotation_rad=rotations.tolist(),
            post_bending_Nmm=(kp*rotations).tolist(), stud_bending_Nmm=(kb*rotations).tolist(),
            post_area_mm2=area, post_Ix_mm4=ix,post_Iy_mm4=iy,
            tie_to_net_section_center_x_mm=x_center-centroid))
    return rows


def stud_sensitivity(load, diameter_mm, pitch_mm, waisted, rolled="SG"):
    """Corrected axial and bending ranges. Larger threads are geometry sensitivities."""
    area = {39.:976.,42.:1120.,45.:1300.}[diameter_mm]
    d3 = diameter_mm-1.226869*pitch_mm
    smooth_equivalent_d = sqrt(4*area/pi)
    waist = .90*d3 if waisted else smooth_equivalent_d
    neck_area = pi/4*waist**2
    neck_length = 410.
    effective_length = TIE_GRIP_MM+.8*diameter_mm
    bolt_compliance = (neck_length/neck_area+(effective_length-neck_length)/area)/E_MPa
    joint = []
    manual = b_case(load,.64)
    preload_min, preload_max = manual["assembly_preload_N"]
    for end in (0,1):
        restrains = eccentric_yoke(load,diameter_mm,waist,end)
        enclosing = restrains[-1]
        p_area = enclosing["post_area_mm2"]
        post_compliance = (B_POST_Z_MM[1]-B_POST_Z_MM[0])/(E_MPa*p_area)
        x_tie = sum(PORTAL_X_MM[end])/2
        start_area = seat_area_mm2(x_tie,POST_X_MM[end],TIE_SEAT_OD_MM)
        edge_width = min(POST_X_MM[end][1]-POST_X_MM[end][0],POST_Y_MM[1]-POST_Y_MM[0])
        head_compliance = quad(lambda z: 1/(E_MPa*min(p_area,
            start_area+4*edge_width*z)),0.,PORTAL_HEIGHT_MM,epsabs=1e-13)[0]
        total_compliance = bolt_compliance+post_compliance+head_compliance
        phi_interface = post_compliance/total_compliance
        phi_full = (post_compliance+head_compliance)/total_compliance
        settle = .04/total_compliance
        max_work = max(enclosing["external_axial_N"])
        nominal_remaining = preload_min-settle-(1-phi_interface)*max_work
        max_force = preload_max+phi_full*max_work
        static_nominal = max_force/neck_area
        SG_MPa = .85*(150./diameter_mm+45.)
        mean_ratio = (preload_max+.5*phi_full*max_work/RELIEF)/(area*RP_MPa)
        if rolled == "SG":
            SG_MPa *= 2.-mean_ratio
        thread_w = pi*smooth_equivalent_d**3/32
        neck_w = pi*waist**3/32
        worst_M = max(map(abs,enclosing["stud_bending_Nmm"]))
        amp_upper = (phi_full*max_work/area + worst_M/thread_w)/(2*RELIEF)
        amp_interface = (phi_interface*max_work/area + worst_M/thread_w)/(2*RELIEF)
        # Plane sections, preload resultant through the stud center. Primary
        # separation proof also requires the spatial moment and shear.
        e_x = enclosing["tie_to_net_section_center_x_mm"]
        corners = [(x-x_tie+e_x,y-TIE_Y_MM)
                   for x,y in product(POST_X_MM[end],POST_Y_MM)]
        pmin = []
        for i,F in enumerate(enclosing["external_axial_N"]):
            f = preload_min-settle-(1-phi_interface)*F
            my = f*e_x
            mx = enclosing["post_bending_Nmm"][i]
            pmin.append(min(f/p_area + my*x/enclosing["post_Iy_mm4"] +
                            mx*y/enclosing["post_Ix_mm4"] for x,y in corners))
        joint.append(dict(end=("rear","front")[end],phi_interface=phi_interface,phi_full=phi_full,
            settling_loss_N=settle,force_315_N=max_force,preload_remaining_315_N=nominal_remaining,
            smooth_static_factor=RP_MPa/(static_nominal+worst_M/neck_w),
            SG_or_SV_limit_MPa=SG_MPa,mean_force_ratio=mean_ratio,
            alternating_amplitude_MPa=[amp_interface,amp_upper],
            fatigue_factor=[SG_MPa/(1.35*amp_upper),SG_MPa/(1.35*amp_interface)],
            manual_edge_pressure_315_MPa=pmin, eccentric_rotation_model=restrains))
    return dict(diameter_mm=diameter_mm,pitch_mm=pitch_mm,As_mm2=area,shank_mm=waist,
        minimum_shank_fillet_mm=.2*diameter_mm if waisted else None,forming=rolled,
        neck_length_mm=neck_length if waisted else None, joints=joint)


def measured_stud_screen(fea, As_mm2):
    if not fea:
        return {}
    radius_mm = sqrt(As_mm2/pi)
    W_mm3 = pi*radius_mm**3/4
    result = {}
    for name,stud in fea["studs"].items():
        if "section_resultants" not in stud:
            continue
        axial_pre, axial_300, axial_315 = map(abs,stud["force_N"])
        sections = {}
        for z,[pre,working,proof] in stud["section_resultants"].items():
            m0 = (pre["Mx_Nmm"],pre["My_Nmm"])
            m3 = (working["Mx_Nmm"],working["My_Nmm"])
            mp = (proof["Mx_Nmm"],proof["My_Nmm"])
            bend_amplitude = hypot(m3[0]-m0[0],m3[1]-m0[1])/(2*W_mm3)
            axial_amplitude = (axial_300-axial_pre)/(2*As_mm2)
            sg = .85*(150/TIE_D_MM+45)*(2-(axial_300+axial_pre)/(2*As_mm2*RP_MPa))
            service = axial_315/As_mm2+hypot(*mp)/W_mm3
            sections[z] = dict(axial_amplitude_MPa=axial_amplitude,
                bending_amplitude_MPa=bend_amplitude,SG_limit_MPa=sg,
                fatigue_factor=sg/(1.35*(axial_amplitude+bend_amplitude)),
                service_static_factor=RP_MPa/service,service_axial_bending_MPa=service)
        result[name]=sections
    return result


def study_fasten(load=None, fea=None):
    load = load or inherited_load()
    manual = b_case(load,.64)
    asm_min,asm_max = manual["assembly_preload_N"]
    as_mm2 = manual["stress_area_mm2"]
    factor = max(1.1,1.01+TIE_D_MM/TIE_GRIP_MM)
    tensioner_N = asm_max*factor
    cases = [stud_sensitivity(load,d,p,waisted,rolled) for d,p,waisted,rolled in
             ((39.,4.,False,"SV"),(39.,4.,False,"SG"),(39.,4.,True,"SG"),
              (42.,4.5,True,"SG"),(45.,4.5,True,"SG"))]
    selected = cases[1]
    r_cases = selected["joints"]
    service_N = max(r["force_315_N"] for r in r_cases)
    post_pressures = [value for r in r_cases for value in r["manual_edge_pressure_315_MPa"]]
    existing_area = [seat_area_mm2(x,limits,TIE_SEAT_OD_MM)
        for x,limits in zip(manual["x_support_mm"],POST_X_MM)]
    spreader_area = [(xb-xa)*(POST_Y_MM[1]-POST_Y_MM[0])-pi/4*TIE_SEAT_ID_MM**2
                     for xa,xb in PLATES_X_MM]
    existing_pressure = max(tensioner_N,service_N)/min(existing_area)
    spreader_pressure = max(tensioner_N,service_N)/min(spreader_area)
    FEA_sections = measured_stud_screen(fea,as_mm2)
    red_MPa = tensioner_N/as_mm2
    # Candidate custom lower anchor collar. Minimum pitch fit values are explicit
    # drawing requirements for this calculation, using the VDI (197)-(209) screen.
    d_min, D2_max, D1_max, d2_min = 38.465,36.702,35.270,36.118
    pitch = 4.
    c1 = 3.8*(NUT_WIDTH_ACROSS_FLATS_MM/TIE_D_MM)-(NUT_WIDTH_ACROSS_FLATS_MM/TIE_D_MM)**2-2.61
    a_nut_per_mm = pi*d_min/pitch*(pitch/2+(d_min-D2_max)*tan(pi/6))
    a_bolt_per_mm = pi*D1_max/pitch*(pitch/2+(d2_min-D1_max)*tan(pi/6))
    nut_Rm_req_MPa = 1200.
    rs = nut_Rm_req_MPa*a_nut_per_mm/(RM_MPa*a_bolt_per_mm)
    c3 = .897 if rs>=1. else .728+1.769*rs-2.896*rs**2+1.296*rs**3
    c2 = (1.187 if rs>=2.2 else
          5.594-13.682*rs+14.107*rs**2-6.057*rs**3+.9353*rs**4 if rs>1. else .897)
    nut_shear_per_mm_N = c1*c3*.65*nut_Rm_req_MPa*a_nut_per_mm
    bolt_shear_per_mm_N = c1*c2*.65*RM_MPa*a_bolt_per_mm
    break_N = RM_MAX_ACCEPTANCE_MPa*as_mm2
    effective_engagement_mm = NUT_HEIGHT_MM-2*pitch
    required_nut_engagement_mm = break_N/min(nut_shear_per_mm_N,bolt_shear_per_mm_N)+2*pitch
    actual_strip_N = effective_engagement_mm*nut_shear_per_mm_N
    actual_bolt_strip_N = effective_engagement_mm*bolt_shear_per_mm_N
    shear_screen = {}
    if fea:
        for i,end in enumerate(("BACK","FRONT")):
            first = fea["contact"]["LEFT"+end]["force_cases"][2]["vector_N"]
            second = fea["contact"]["RIGHT"+end]["force_cases"][2]["vector_N"]
            shear_N = hypot(first[0]+second[0], first[1]+second[1])
            joints = r_cases[i]
            total_clamp_N = 2*(asm_min-joints["settling_loss_N"]) - (
                1-joints["phi_interface"])*sum(joints["eccentric_rotation_model"][-1]["external_axial_N"])
            shear_screen[end] = dict(external_shear_N=shear_N,aggregate_residual_clamp_N=total_clamp_N,
                                     minimum_mu_for_resultant_only=shear_N/total_clamp_N)
    upper_tool_projection_x_mm = [min(manual["x_support_mm"])-TOOL_DIAMETER_MM/2,
                                  max(manual["x_support_mm"])+TOOL_DIAMETER_MM/2]
    R = {
      "R0": dict(status="SCREEN",thread="M39x4 6g/6H SG", As_mm2=as_mm2,
                 yield_N=RP_MPa*as_mm2,quantity=4),
      "R1": dict(status="OPEN",assembly_scatter=asm_max/asm_min, required_load_transfer=factor,
                 FM_bounds_N=[asm_min,asm_max],condition="Measure elastic elongation and transfer scatter"),
      "R2": dict(status="FAIL",max_external_force_N=manual["actual_portal_far_high_tie_N"],
                 minimum_manual_edge_pressure_MPa=min(post_pressures),
                 edge_pressure_all_four_MPa=post_pressures,
                 condition="Linear eccentric clamp check. Tension at a footprint edge means loss of full-area closure."),
      "R3": dict(status="SCREEN",sensitivity=cases,
                 condition="Phi calculated for the parting plane and the whole grip. M42/M45 properties and fit shall be guaranteed separately."),
      "R4": dict(status="OPEN",settlement_mm=.04,max_settlement_loss_N=max(r["settling_loss_N"] for r in r_cases),
                 thermal_loss_N=None,condition="Require measured total settlement and differential temperature of grip."),
      "R5": dict(status="FAIL",FM_min_N=asm_min,
                 residual_clamp_315_N=[r["preload_remaining_315_N"] for r in r_cases],
                 condition="Axial residual is positive but is insufficient to prove total closure."),
      "R6": dict(status="SCREEN",FM_max_N=asm_max,hydraulic_pull_N=tensioner_N),
      "R7": dict(status="SCREEN",assembly_direct_pull_MPa=red_MPa,assembly_elastic_screen_MPa=.9*RP_MPa,
                 torsion_from_main_stud_nut_is_excluded_for_hydraulic_tensioner=True),
      "R8": dict(status="FAIL",proof_axial_N=as_mm2*PROOF_MPa, max_axial_315_N=service_N,
                 working_static_factor_manual=[r["smooth_static_factor"] for r in r_cases],
                 working_bending_FEA_by_section=FEA_sections,
                 condition="Smooth sections from a tied model. Nut seating eccentricity and local runout require qualification."),
      "R9": dict(status="FAIL",thread_fatigue_target=1.10,cases=cases,
                 FEA_axial_and_bending_by_section=FEA_sections,
                 condition="Axial and bending ranges on the same side. First engaged turn and runout are not resolved by the elastic surrogate."),
      "R10": dict(status="FAIL",original_top_66mm_pressure_MPa=existing_pressure,
                  top_pG_screen_MPa=.60*SEAT_RP_MPa[0],lower_pG_screen_MPa=.60*SEAT_RP_MPa[1],
                  proposed_spreader_x_y_mm=[[list(x),list(POST_Y_MM)] for x in PLATES_X_MM],
                  proposed_spreader_h_mm=SPREADER_THICKNESS_MM,
                  proposed_projected_average_MPa=spreader_pressure,
                  condition="The plate is a packaging screen. Plate bending and local pressure under the nut and on housing need proof."),
      "R11": dict(status="OPEN",lower_anchor="Through stud, captive high nut and spreader bearing against underside of each post",
                  proposed_lower_nut_width_across_flats_mm=NUT_WIDTH_ACROSS_FLATS_MM,
                  proposed_lower_nut_total_height_mm=NUT_HEIGHT_MM,
                  required_lower_nut_Rm_MPa=nut_Rm_req_MPa, nut_proof_reference_N=NUT_PROOF_N,
                  candidate_effective_engagement_mm=NUT_HEIGHT_MM-2*pitch, required_total_engagement_mm=required_nut_engagement_mm,
                  calculated_nut_internal_strip_N=actual_strip_N,calculated_stud_external_strip_N=actual_bolt_strip_N,
                  thread_tensile_upper_acceptance_N=break_N,
                  stud_Rm_max_acceptance_MPa=RM_MAX_ACCEPTANCE_MPa,relative_thread_strength=rs,
                  bolt_strip_C2=c2,nut_strip_C3=c3,flank_C1=c1,
                  minimum_d_and_d2_mm=[d_min,d2_min], nut_max_D2_and_D1_mm=[D2_max,D1_max],
                  proposed_anchor_z_mm=[B_POST_Z_MM[0]-SPREADER_THICKNESS_MM-NUT_HEIGHT_MM,B_POST_Z_MM[0]],
                  lower_stud_protrusion_for_thread_check_mm=8.,
                  condition="Fit and proof certificate plus anti-rotation cage and negative-z access are required."),
      "R12": dict(status="OPEN",aggregate_resultant_screen=shear_screen,
                  condition="TIE transfers tangential traction. Determine joint slip in a model that admits parting; wet/dry seating friction has not been qualified."),
      "R13": dict(status="FAIL",tool="Boltight T23 M39",rated_force_N=TOOL_CAPACITY_N,
                  required_force_N=tensioner_N, tool_diameter_height_mm=[TOOL_DIAMETER_MM,TOOL_HEIGHT_MM],
                  catalogue_nearest_obstruction_mm=200., catalogue_min_M39_bolt_pitch_mm=83.,
                  available_post_width_mm=POST_Y_MM[1]-POST_Y_MM[0], nut_width_across_flats_mm=60.,
                  required_protrusion_from_seat_mm=HYDRAULIC_TOOL_PROJECTION_MM,
                  tool_x_envelope_mm=upper_tool_projection_x_mm,
                  tool_abs_y_range_mm=[TIE_Y_MM-TOOL_DIAMETER_MM/2,TIE_Y_MM+TOOL_DIAMETER_MM/2],
                  tool_positive_z_envelope_mm=[B_POST_Z_MM[1]+PORTAL_HEIGHT_MM,
                                               B_POST_Z_MM[1]+PORTAL_HEIGHT_MM+TOOL_HEIGHT_MM],
                  MJT_alternative=dict(series="Superbolt CY M39x4",recommended_preload_N=570000.,
                      nut_diameter_mm=72.,washer_diameter_thickness_mm=[70.,5.],height_mm=57.,
                      jackbolt_count=10,jackbolt_tool_size_mm=8.,reference_jackbolt_torque_Nm=72.,
                      required_qualification="Obtain max service load for M39 and wrench swing envelope; full hardened washer seating is open."),
                  condition="Full seating of the bridge and service access require a support drawing. The finished stud needs measured elongation."),
    }
    return R
