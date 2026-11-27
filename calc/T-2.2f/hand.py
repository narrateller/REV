"""Load envelope and scalar N/mm/MPa structural screens for T-2.2f."""

from functools import lru_cache
from itertools import product
from math import asin, exp, expm1, fsum, hypot, log10, pi, sqrt
from pathlib import Path
import json

from load import accepted_load, read_geometry, read_yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E_MPa = 210_000.0
NU = 0.30
G_MPa = E_MPa / (2 * (1 + NU))
E_STAR_MPa = E_MPa / (2 * (1 - NU**2))
RATIO = 315 / 300
SIDE_SHARE = 0.64
EDGE_R_MM = 5.0
ROOT_R_MM = 15.0
CROWN_MM = 0.10
SEATING_MM = 0.020
CAST = (650., 800., True)
FORGE_THICK = (600., 800., False)
FORGE_MEDIUM = (700., 900., False)
FORGE_PAD = (800., 1000., False)
# For thick flat sections beyond the supplier table, retain the conservative
# T-2.2e screening value and require a certificate in the controlling section.
FORGE_LARGE = (500., 750., False)


def forge_material(depth_mm):
    if depth_mm <= 60:
        return FORGE_PAD
    if depth_mm <= 100:
        return FORGE_MEDIUM
    if depth_mm <= 160:
        return FORGE_THICK
    return FORGE_LARGE


def strength(stress_bending_MPa, stress_shear_MPa, material, steady_MPa=0., normal_MPa=0.):
    """Nominal FKM, R=0, no notch-support credit. Shear on the neutral axis."""
    proof_MPa, tensile_MPa, cast = material
    Rz_um = 6.3
    jG = 1.25 if cast else 1.
    roughness = 1 - (.20 if cast else .22) * log10(Rz_um) * log10(2 * tensile_MPa / 400)
    m_sigma = .00035 * tensile_MPa + (.05 if cast else -.10)
    amp_allow_MPa = (.34 if cast else .40) * tensile_MPa * roughness * 10**(-1/15) / (1.5 * jG)
    stress_315_MPa = max(abs(stress_bending_MPa) + abs(normal_MPa), hypot(normal_MPa, sqrt(3) * stress_shear_MPa))
    range_MPa = stress_315_MPa / RATIO
    demand_MPa = range_MPa / 2 * (1 + m_sigma) + m_sigma * steady_MPa
    return dict(stress_315_MPa=steady_MPa + stress_315_MPa, range_300_MPa=range_MPa,
                allowed_range_300_MPa=2 * max(0., amp_allow_MPa - m_sigma * steady_MPa) / (1 + m_sigma),
                Rm_MPa=tensile_MPa, Rp02_MPa=proof_MPa, jG=jG,
                static_factor=proof_MPa / (steady_MPa + stress_315_MPa) if stress_315_MPa else None,
                FKM=amp_allow_MPa / demand_MPa if demand_MPa else None)


@lru_cache(maxsize=8192)
def beam(force_N, span_mm, load_width_mm, width_mm, thickness_mm, *, skew=SIDE_SHARE):
    """Uniform eccentric strip, moment integration and Timoshenko shear."""
    if force_N == 0:
        return dict(bend_MPa=0., shear_MPa=0., bend_mm=0., shear_mm=0., fixed_bend_mm=0.)
    centroid_mm = skew * span_mm
    # Translate/narrow the strip to fit inside the channel contact footprint.
    # Positivity holds even for the more eccentric support pairs.
    w_mm = min(load_width_mm, load_width_mm - 2 * abs(centroid_mm - span_mm / 2))
    if w_mm <= 0:
        raise ValueError("Skew resultant outside the contact footprint")
    u_mm, v_mm = centroid_mm - w_mm / 2, centroid_mm + w_mm / 2
    q_N_mm = force_N / w_mm
    r_N = force_N * (1 - skew)
    I_mm4 = width_mm * thickness_mm**3 / 12
    A_mm2 = width_mm * thickness_mm

    def moment_Nmm(x_mm):
        return r_N*x_mm - q_N_mm/2 * (max(0., x_mm-u_mm)**2 - max(0., x_mm-v_mm)**2)

    def moment_integral_2(x_mm):
        return r_N*x_mm**3/6 - q_N_mm/24 * (max(0., x_mm-u_mm)**4 - max(0., x_mm-v_mm)**4)

    def moment_integral_1(x_mm):
        return r_N*x_mm**2/2 - q_N_mm/6 * (max(0., x_mm-u_mm)**3 - max(0., x_mm-v_mm)**3)

    linear = -moment_integral_2(span_mm) / span_mm
    slope_left = linear / (E_MPa * I_mm4)
    slope_right = (moment_integral_1(span_mm) + linear) / (E_MPa * I_mm4)

    def deflection(x_mm):
        bend_mm = -(moment_integral_2(x_mm) + linear*x_mm) / (E_MPa * I_mm4)
        shear_mm = moment_Nmm(x_mm) / ((5/6) * G_MPa * A_mm2)
        u = x_mm / span_mm
        fixed_bend_mm = bend_mm + span_mm * (
            slope_left*u*(1-u)**2 - slope_right*u*u*(1-u))
        return bend_mm, shear_mm, fixed_bend_mm

    # The lower bound uses the closed-form at the pressure centroid. The pin-ended
    # working estimate reports the largest combined opening along the loaded region.
    # Complementary energies bound the load-weighted opening. Bending
    # minimizes independent end moments. Three Gauss points integrate the
    # squared moment exactly on each constant-load segment.
    def fixed_moment_Nmm(x_mm):
        u=x_mm/span_mm
        return moment_Nmm(x_mm) - E_MPa*I_mm4/span_mm*(
            slope_left*(6*u-4) + slope_right*(6*u-2))

    nodes = (-sqrt(3/5),0.,sqrt(3/5))
    weights = (5/9,8/9,5/9)
    breaks_mm = (0.,u_mm,v_mm,span_mm)
    moment2 = fsum((hi-lo)/2*fsum(w*fixed_moment_Nmm((hi+lo)/2+x*(hi-lo)/2)**2
                                 for w,x in zip(weights,nodes))
                   for lo,hi in zip(breaks_mm,breaks_mm[1:]))
    shear2 = (r_N**2*u_mm + (r_N**2-r_N*force_N+force_N**2/3)*w_mm
              + (r_N-force_N)**2*(span_mm-v_mm))
    points_mm = [span_mm/2-load_width_mm/2 + i*load_width_mm/30 for i in range(31)]
    bend_mm, shear_mm, _ = max(map(deflection, points_mm), key=lambda row: row[0] + row[1])
    return dict(bend_MPa=6*moment_Nmm(u_mm+r_N/q_N_mm)/(width_mm*thickness_mm**2),
                shear_MPa=1.5*max(r_N, force_N-r_N)/A_mm2,
                bend_mm=bend_mm, shear_mm=shear_mm, fixed_bend_mm=moment2/(E_MPa*I_mm4*force_N),
                centroid_shear_mm=shear2/((5/6)*G_MPa*A_mm2*force_N), load_width_after_skew_mm=w_mm,
                left_N=r_N, right_N=force_N-r_N)


def patch(force_N, gross_x_mm, gross_y_mm, backing_cast=True):
    """Crowned flat on flat, finite footprint as in T-2.2d, plus face mean."""
    length_mm = gross_x_mm - 2*EDGE_R_MM
    net_y_mm = gross_y_mm - 2*EDGE_R_MM
    radius_mm = gross_y_mm**2/(8*CROWN_MM) + CROWN_MM/2
    half_mm = sqrt(4*force_N*radius_mm/(pi*length_mm*E_STAR_MPa))
    limit = min(1., net_y_mm/(2*half_mm))
    integral_mm = half_mm*(asin(limit)+limit*sqrt(1-limit**2))
    return dict(static_peak_MPa=force_N/(length_mm*integral_mm),
                static_screen_MPa=.60*(CAST[0] if backing_cast else FORGE_MEDIUM[0]),
                mean_300_MPa=force_N/(RATIO*length_mm*net_y_mm),
                pulsating_screen_MPa=80. if backing_cast else 100.,
                contact_net_area_mm2=length_mm*net_y_mm, half_width_mm=half_mm,
                flat_min_area_required_mm2=force_N/RATIO/(80. if backing_cast else 100.))


def distribute(force_N, centroid_x_mm, x1_mm, x2_mm):
    front = (centroid_x_mm-x1_mm)/(x2_mm-x1_mm)
    return force_N*(1-front), force_N*front


def top_load(force_N, K, mu, punch_mm, left_mm, right_mm):
    if left_mm >= right_mm:
        return dict(force_N=0., centroid_x_mm=None, peak_MPa=0., interval_mm=None)
    decay = K*mu*420/9000
    length_mm = right_mm-left_mm
    MPa = K*force_N/9000*exp(-decay*(left_mm-punch_mm))
    area_integral = -expm1(-decay*length_mm)/decay
    return dict(force_N=150*MPa*area_integral,
                centroid_x_mm=left_mm+1/decay-length_mm/expm1(decay*length_mm),
                peak_MPa=MPa, interval_mm=[left_mm,right_mm])


@lru_cache(maxsize=None)
def load_cases(roof_mm):
    """D-GK-10 maxima plus transfer and final compression over the material envelope."""
    base = accepted_load()
    transfer = json.loads((ROOT/"calc/T-2.2d/results.json").read_text(encoding="utf-8"))["transfer"]
    geom = read_geometry()
    curve = read_yaml("calc/T-1.1/curve.yaml")
    gate_mm = 205 + roof_mm
    length_limit_mm = base["loaded_limit_mm"]
    F315_N = base["cases"]["315_bar"]["punch_force_N"]
    width_mm, height_mm = base["section_mm"]
    rows = []
    for case, bulk_kg_m3 in product(transfer, (90,160)):
        dose_kg = transfer[case][str(bulk_kg_m3)]["upper"]["dose_kg"]
        material = geom.Material(curve, .83, [width_mm,height_mm])

        def pressure_MPa(length_mm):
            density_kg_m3 = dose_kg*1e9/(width_mm*height_mm*length_mm)
            return material.face_MPa(density_kg_m3, bulk_kg_m3, case, dose_kg=dose_kg)

        # Normalize each constitutive shape at the accepted 89.4 mm upper
        # length / 315 bar force pair. The profile is a screening envelope.
        p_end_MPa = pressure_MPa(length_limit_mm)
        retained_N = transfer[case][str(bulk_kg_m3)]["upper"]["retained_shoe_force_N"]
        # Rated service level; apply 315/300 conservatively also to transfer.
        rows.extend(dict(label="retained transfer", material_case=case, bulk_kg_m3=bulk_kg_m3,
                         K=None, mu=None, punch_mm=None, length_mm=200.,
                         main_force_N=None,
                         shoe=dict(force_N=retained_N*RATIO,
                                   centroid_x_mm=(end_mm-200.+205.)/2,
                                   peak_MPa=retained_N/30000, interval_mm=[end_mm-200,205.]),
                         roof=dict(force_N=0., centroid_x_mm=None, peak_MPa=0., interval_mm=None))
                    for end_mm in (205., gate_mm))
        for index in range(112):
            length_mm = length_limit_mm + (200-length_limit_mm)*index/111
            punch_mm = gate_mm-length_mm
            main_N = F315_N*pressure_MPa(length_mm)/p_end_MPa
            for K, mu in product((.35,.45,.60), (.20,.25,.30)):
                shoe = top_load(main_N, K, mu, punch_mm, max(5.,punch_mm), min(205.,gate_mm))
                roof = top_load(main_N, K, mu, punch_mm, max(205.,punch_mm), gate_mm)
                rows.append(dict(label="final" if index==0 else "compression", material_case=case,
                                 bulk_kg_m3=bulk_kg_m3, K=K, mu=mu, punch_mm=punch_mm,
                                 length_mm=length_mm, main_force_N=main_N, shoe=shoe, roof=roof))
    final = max((r for r in rows if r["label"] == "final"), key=lambda r: r["shoe"]["force_N"])
    # The D-GK-11 longitudinal load offset is an additional moment case.
    # For a partial roof, the actual residual length centroid can be larger.
    if final["shoe"]["force_N"]:
        rows.append(final | {"label":"D-GK-11 proof centroid",
                            "shoe":final["shoe"] | {"centroid_x_mm":165.2}})
    return rows


def extrema(rows, x1_mm, x2_mm):
    positive = [row for row in rows if row["shoe"]["force_N"] > 0]
    def reactions(row):
        shoe = row["shoe"]
        return distribute(shoe["force_N"],shoe["centroid_x_mm"],x1_mm,x2_mm)
    result = dict(shoe_final=max((r for r in rows if r["label"]=="final"), key=lambda r:r["shoe"]["force_N"]),
                  shoe_max=max(positive, key=lambda r:r["shoe"]["force_N"]),
                  roof_pressure=max(rows, key=lambda r:r["roof"]["peak_MPa"]),
                  roof_force=max(rows, key=lambda r:r["roof"]["force_N"]))
    for i, station in enumerate(("rear","front")):
        r = max(positive, key=lambda row:reactions(row)[i])
        result[station] = dict(case=r, force_315_N=reactions(r)[i])
        r = min(positive, key=lambda row:reactions(row)[i])
        result[station]["min_reaction_N"] = min(0.,reactions(r)[i])
        result[station]["min_case"] = r
    return result


def fixed_roof(loads, depth_mm, wall_mm, span_mm):
    if depth_mm == 0:
        return {}, {}
    local = loads["roof_pressure"]["roof"]
    force_N = 150*local["peak_MPa"]
    roof = beam(force_N,span_mm,150.,1.,depth_mm)
    floor = roof.copy()
    side = SIDE_SHARE*force_N
    # One-mm strip. The floor and the closed roof make a local closed ring.
    stress = dict(roof_strip=strength(roof["bend_MPa"],roof["shear_MPa"],CAST),
                  floor_strip=strength(floor["bend_MPa"],floor["shear_MPa"],CAST),
                  solid_sidewall=strength(0.,0.,CAST,normal_MPa=side/wall_mm))
    # The ring is monolithic. Seating of the machined frame shoulder is
    # an extra series contribution, conservative for a self-equilibrated ring.
    strain_mm = side*(60+depth_mm)/(E_MPa*wall_mm)
    seat_mm = SEATING_MM + side*28/(E_MPa*wall_mm)
    height = dict(ideal_mm=(roof["fixed_bend_mm"]+floor["fixed_bend_mm"]
                            +roof["centroid_shear_mm"]+floor["centroid_shear_mm"])/RATIO,
                  total_mm=(roof["bend_mm"]+roof["shear_mm"]+floor["bend_mm"]+floor["shear_mm"]
                            +strain_mm+seat_mm)/RATIO,
                  closed_side_extension_315_mm=strain_mm, seating_315_mm=seat_mm)
    return stress,height


@lru_cache(maxsize=None)
def axial_envelope(roof_mm, x1_mm, x2_mm):
    """Concentrated centroid load screen of the continuous longitudinal ribs."""
    rows = load_cases(roof_mm)
    L_mm = x2_mm-x1_mm
    envelopes = dict(moment_Nmm=0., shear_N=0., flexure_Nmm3=0., shear_mm_N=0.)
    for case in rows:
        F_N = case["shoe"]["force_N"]
        if not F_N:
            continue
        a_mm = case["shoe"]["centroid_x_mm"] - x1_mm
        b_mm = L_mm-a_mm
        if min(a_mm,b_mm) >= 0:
            moment_Nmm = F_N*a_mm*b_mm/L_mm
            shear_N = F_N*max(a_mm,b_mm)/L_mm
            flexure = F_N*a_mm**2*b_mm**2/(3*L_mm)
            shear_displacement = F_N*a_mm*b_mm/L_mm
        else:
            overhang_mm = -min(a_mm,b_mm)
            moment_Nmm = F_N*overhang_mm
            shear_N = F_N*(1+overhang_mm/L_mm)
            flexure = F_N*overhang_mm**2*(L_mm+overhang_mm)/3
            shear_displacement = F_N*overhang_mm*(1+overhang_mm/L_mm)
        envelopes["moment_Nmm"] = max(envelopes["moment_Nmm"],moment_Nmm)
        envelopes["shear_N"] = max(envelopes["shear_N"],shear_N)
        envelopes["flexure_Nmm3"] = max(envelopes["flexure_Nmm3"],flexure)
        envelopes["shear_mm_N"] = max(envelopes["shear_mm_N"],shear_displacement)

    return envelopes


def axial_bridges(roof_mm, geometry):
    x1_mm,x2_mm = geometry["station_x_mm"].values()
    envelopes = axial_envelope(roof_mm,x1_mm,x2_mm)
    result = {}
    for name in ("shoe", "floor"):
        b_mm = geometry["longitudinal_floor_band_y_mm"] if name=="floor" else 150.
        d_mm = geometry[name+"_depth_mm"]
        I_mm4 = b_mm*d_mm**3/12
        A_mm2 = b_mm*d_mm
        material = CAST if name=="floor" and not geometry.get("frame_borne") else forge_material(d_mm)
        sigma_MPa = envelopes["moment_Nmm"]*d_mm/(2*I_mm4)
        tau_MPa = 1.5*envelopes["shear_N"]/A_mm2
        deflection_mm = (envelopes["flexure_Nmm3"]/(E_MPa*I_mm4) +
                         envelopes["shear_mm_N"]/((5/6)*G_MPa*A_mm2))/RATIO
        result[name] = dict(strength=strength(sigma_MPa,tau_MPa,material), displacement_bound_mm=deflection_mm)
    return result


def lock(loads, geometry):
    """Two independent axial stations in a hoop or in a frame-borne portal."""
    span_mm = geometry["span_mm"]
    side_share = geometry.get("side_share", SIDE_SHARE)
    T_shoe_mm = geometry["shoe_depth_mm"]
    T_floor_mm = geometry["floor_depth_mm"]
    contact_y_mm = geometry["pad_y_mm"]
    material = forge_material(T_shoe_mm)
    width_seat_map = geometry["pad_x_mm"]
    details = {}
    for station in ("rear","front"):
        loads_station = loads[station]
        force_N = max(abs(loads_station["min_reaction_N"]),loads_station["force_315_N"])
        shoe_force_N = force_N
        # Both station reactions together equal the force. Give the local bottom
        # ring the same resultant, an upper estimate when load spreads in x.
        floor_force_N = force_N
        gross_b_mm = geometry["station_breadth_x_mm"][station]
        gross_pad_x_mm = width_seat_map[station]
        # Load spreads 1:1 from the two R15 ends to the mid-depth. Clip at the
        # physical station body and record the optimistic full-width bound.
        effective_shoe_mm = min(gross_b_mm, gross_pad_x_mm - 2*EDGE_R_MM + T_shoe_mm/2)
        effective_floor_mm = min(gross_b_mm, gross_pad_x_mm - 2*EDGE_R_MM + T_floor_mm/2)
        shoe = beam(shoe_force_N,span_mm,150.,effective_shoe_mm,T_shoe_mm,skew=side_share)
        floor = beam(floor_force_N,span_mm,150.,effective_floor_mm,T_floor_mm,skew=side_share)
        ideal_shoe = beam(shoe_force_N,span_mm,150.,gross_b_mm,T_shoe_mm,skew=side_share)
        ideal_floor = beam(floor_force_N,span_mm,150.,gross_b_mm,T_floor_mm,skew=side_share)
        peak_side_N = side_share*force_N
        top_stress = strength(shoe["bend_MPa"],shoe["shear_MPa"],material)
        floor_material = forge_material(T_floor_mm) if geometry.get("frame_borne") else CAST
        floor_stress = strength(floor["bend_MPa"],floor["shear_MPa"],floor_material)
        # Closed window in each cheek: two side ligaments take the pad reaction,
        # with a bending/shear bridge across the pad opening. No threaded member in tension.
        limb_A_mm2 = 2*geometry["limb_x_mm"]*geometry["limb_y_mm"]
        limb_H_mm = geometry["limb_height_mm"]
        cap_t_mm = geometry["cap_depth_mm"]
        cap_span_mm = gross_pad_x_mm+geometry["limb_x_mm"]
        cap = beam(peak_side_N,cap_span_mm,gross_pad_x_mm-2*EDGE_R_MM,
                   geometry["limb_y_mm"],cap_t_mm,skew=.5)
        is_frame = geometry.get("frame_borne", False)
        cap_material = forge_material(cap_t_mm) if is_frame else CAST
        limb_material = forge_material(geometry["limb_y_mm"]) if is_frame else CAST
        cap_stress = strength(cap["bend_MPa"],cap["shear_MPa"],cap_material)
        limb_stress = strength(0.,0.,limb_material,normal_MPa=peak_side_N/limb_A_mm2)
        contact = patch(peak_side_N,gross_pad_x_mm,contact_y_mm)
        # Offset from the edge of a bearing land to a centered double-guide.
        key_width_mm = gross_pad_x_mm-2*EDGE_R_MM
        key_bend_MPa = 6*peak_side_N*geometry["seat_offset_mm"]/(key_width_mm*cap_t_mm**2)
        key_shear_MPa = peak_side_N/(cap_t_mm*key_width_mm)
        key_stress = strength(key_bend_MPa,key_shear_MPa,forge_material(cap_t_mm))
        column_mm = geometry.get("frame_mobility_mm_N",0.)*peak_side_N
        shoulder_mm = peak_side_N*28/(E_MPa*limb_A_mm2)
        joint_mm = (SEATING_MM + shoulder_mm + peak_side_N*limb_H_mm/(E_MPa*limb_A_mm2)
                    + peak_side_N*(cap_t_mm+24)/(E_MPa*contact["contact_net_area_mm2"])
                    + 2*CROWN_MM*(min(contact["half_width_mm"],(contact_y_mm-2*EDGE_R_MM)/2)/(contact_y_mm/2))**2)
        ideal_mm = fsum(b["fixed_bend_mm"]+b.get("centroid_shear_mm",0.)
                        for b in (ideal_shoe,ideal_floor))/RATIO
        total_mm = (fsum(b["bend_mm"]+b["shear_mm"] for b in (shoe,floor,cap))
                    + joint_mm + column_mm)/RATIO
        details[station] = dict(effective_shoe_width_x_mm=effective_shoe_mm,
                                effective_floor_width_x_mm=effective_floor_mm,
                                section_checks=dict(shoe=top_stress,floor=floor_stress,closed_cap=cap_stress,
                                                    two_window_ligaments=limb_stress,key=key_stress),
                                bending_shear=dict(shoe=shoe,floor=floor,cap=cap),
                                contact=contact, lower_bound_mm=ideal_mm, height_with_joints_mm=total_mm,
                                joints_315_mm=joint_mm, frame_shoulder_315_mm=shoulder_mm, frame_315_mm=column_mm,
                                peak_side_315_N=peak_side_N, station_reaction_315_N=force_N)
    return details
