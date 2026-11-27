"""Signed bearing reaction and elastic screening of three shoe supports."""

from dataclasses import asdict, dataclass, replace
from math import hypot, log10, sqrt

from loads import PROOF_SKEW_Y_MM, read_json, support_cases

E_MPa = 210_000.
NU = .30
G_MPa = E_MPa / (2. * (1. + NU))
DENSITY_KG_MM3 = 7.85e-6
CORRECTION = 1.23
CYCLE = 300. / 315.
REAR_MM = 55.
REAR_Y_MM = 107.
CAM_S = .08
CAM_MM = 12.
RESIDUAL_N = 2000.


@dataclass(frozen=True)
class Support:
    name: str
    kind: str
    x_mm: float
    width_mm: float
    height_mm: float
    bearing_length_mm: float
    y_mm: float
    travel_mm: float
    moving_length_mm: float
    cheek_leg_mm: float = 21.


BASE = Support("T-2.2h", "key", 148., 70., 66., 40., 107., 54., 164.)
OPTIONS = (
    Support("key_x192", "key", 192., 24., 66., 40., 107., 54., 164.),
    Support("nose_x225", "nose", 225., 52., 60., 40., 106., 44.8, 74.),
    Support("clevis_x182", "clevis", 182., 52., 38., 20., 106., 36., 79., 10.),
)


def equilibrium(case, option):
    """The two pairs share the Y moment proportional to their signed X loads."""
    force_N, x_mm, y_mm = (case[k] for k in ("force_315_N", "x_mm", "y_mm"))
    front_N = force_N * (x_mm - REAR_MM) / (option.x_mm - REAR_MM)
    reactions = {
        station + suffix: load_N / 2. * (1. + sign * y_mm / arm_mm)
        for station, load_N, arm_mm in (("rear", force_N - front_N, REAR_Y_MM),
                                        ("front", front_N, option.y_mm))
        for suffix, sign in (("_minus", -1.), ("_plus", 1.))
    }
    xs_mm = (REAR_MM, REAR_MM, option.x_mm, option.x_mm)
    ys_mm = (-REAR_Y_MM, REAR_Y_MM, -option.y_mm, option.y_mm)
    forces = list(reactions.values())
    resultants = (sum(forces) - force_N,
                  sum(x*r for x,r in zip(xs_mm, forces, strict=True)) - force_N*x_mm,
                  sum(y*r for y,r in zip(ys_mm, forces, strict=True)) - force_N*y_mm)
    return reactions, resultants


def fatigue_base(rm_MPa, cast=False):
    surface = 1. - (.20 if cast else .22) * log10(6.3) * log10(2. * rm_MPa / 400.)
    base_MPa = (.34 if cast else .40) * rm_MPa * surface * 10**(-1 / 15)
    return base_MPa / (1.5 * (1.25 if cast else 1.)), .00035 * rm_MPa + (.05 if cast else -.1)


def safety(normal_315_MPa, shear_315_MPa, rp_MPa, rm_MPa, *, cast=False):
    base_MPa, sensitivity = fatigue_base(rm_MPa, cast)
    vm_MPa = hypot(normal_315_MPa, sqrt(3.) * shear_315_MPa)
    principal_MPa = normal_315_MPa / 2. + hypot(normal_315_MPa / 2., shear_315_MPa)
    equivalent_MPa = CYCLE / 2. * (vm_MPa + sensitivity * principal_MPa)
    return {
        "static_factor_nominal": rp_MPa / vm_MPa,
        "FKM_nominal": base_MPa / equivalent_MPa,
        "FKM_corrected": base_MPa / (CORRECTION * equivalent_MPa),
        "VM_315_MPa": vm_MPa,
        "base_amplitude_MPa": base_MPa, "mean_sensitivity": sensitivity,
    }


def member(option, force_315_N):
    """Nominal key/lug loads, shear/bending and bearing footprint averages."""
    width_mm = option.width_mm - 10.  # R5 both loaded edges, prior configuration
    h_mm = option.height_mm
    section_mm3 = width_mm * h_mm**2 / 6.
    inertia_mm4 = section_mm3 * h_mm / 2.
    area_mm2 = width_mm * h_mm
    shear_rigidity_N = (5./6.) * G_MPa * area_mm2
    shoe_area_mm2 = width_mm * option.bearing_length_mm
    effective_shear_N = 1.5 * force_315_N
    cast = None
    if option.kind == "key":
        overhang_mm, span_mm = 166.5 - option.y_mm, 226. - 166.5
        lever = overhang_mm / span_mm
        seat_N = force_315_N * (1. + lever)
        return_N = force_315_N * lever
        seat_mm2 = width_mm * 53.
        moment_Nmm = force_315_N * overhang_mm
        compliance_mm_N = (overhang_mm**2 * (overhang_mm + span_mm) / (3. * E_MPa * inertia_mm4)
                           + (overhang_mm + lever**2 * span_mm) / shear_rigidity_N)
        compliance_mm_N += 12. / E_MPa * ((1. + lever)**2/seat_mm2 + lever**2/(width_mm*30.))
        legs_mm2 = 2. * option.cheek_leg_mm * 63.
        compliance_mm_N += 212. * (1. + lever)**2 / (E_MPa * legs_mm2)
        cast = safety(seat_N / legs_mm2, 0., 650., 800., cast=True)
    elif option.kind == "nose":
        arm_mm = option.x_mm - 204.8
        seat_N, return_N = force_315_N, 0.
        seat_mm2 = shoe_area_mm2 = width_mm * (option.bearing_length_mm - 10.)
        moment_Nmm = seat_N * arm_mm
        compliance_mm_N = arm_mm**3 / (3. * E_MPa * inertia_mm4) + arm_mm / shear_rigidity_N
        compliance_mm_N += (265. - 104. - h_mm) / (E_MPa * seat_mm2)
    else:
        span_mm = option.bearing_length_mm + option.cheek_leg_mm
        seat_N, return_N = force_315_N / 2., 0.
        seat_mm2 = width_mm * option.cheek_leg_mm
        moment_Nmm = force_315_N * span_mm / 4.
        effective_shear_N /= 2.
        compliance_mm_N = span_mm**3 / (48. * E_MPa * inertia_mm4) + span_mm / (4. * shear_rigidity_N)
        compliance_mm_N += 134. / (2. * E_MPa * seat_mm2)
        cast = safety(seat_N / seat_mm2, 0., 650., 800., cast=True)
    # Higher of the rectangular-section bending fibre and neutral-axis
    # shear screens. Combining the two absolute maxima would double-count.
    checks = (safety(moment_Nmm / section_mm3, 0., 800., 1000.),
              safety(0., effective_shear_N / area_mm2, 800., 1000.))
    return {
        "key": min(checks, key=lambda row: row["FKM_corrected"]), "cast_nominal": cast,
        "local_moment_315_Nmm": moment_Nmm, "net_section_mm2": area_mm2,
        "shoe_bearing_area_mm2": shoe_area_mm2, "land_bearing_area_mm2": seat_mm2,
        "shoe_mean_bearing_300_MPa": force_315_N * CYCLE / shoe_area_mm2,
        "land_mean_bearing_300_MPa": seat_N * CYCLE / seat_mm2,
        "land_reaction_315_N": seat_N, "opposite_land_reaction_315_N": return_N,
        "local_compliance_mm_N": compliance_mm_N,
    }


def drive(option, lock, rear_travel_mm=54.):
    front_ratio = option.travel_mm / CAM_MM
    rear_ratio = rear_travel_mm / CAM_MM
    moving_kg = moving_pair_kg(option)
    rear_pair_kg = 2. * 42. * 38. * 164. * DENSITY_KG_MM3
    drag_N = 2. * lock["no_load_slide_force_per_key_N"]

    def unloaded_branch(kg, travel_mm, ratio):
        acceleration_m_s2 = 4. * travel_mm / 1000. / CAM_S**2
        return ratio * (kg * acceleration_m_s2 + drag_N) / lock["cam_efficiency"]

    empty_N = (unloaded_branch(moving_kg, option.travel_mm, front_ratio)
               + unloaded_branch(rear_pair_kg, rear_travel_mm, rear_ratio))
    ratio = max(front_ratio, rear_ratio)
    forces_N = {str(mu): empty_N + ratio * 2. * mu * RESIDUAL_N / lock["cam_efficiency"]
                for mu in (.15, .30)}
    residual_capacity_N = {str(mu): max(0., lock["equivalent_cam_force_N"] - empty_N)
                           * lock["cam_efficiency"] / (2. * mu * ratio) for mu in (.15, .30)}
    return {"cam_stroke_mm": CAM_MM, "cam_duration_s": CAM_S,
            "rear_key_travel_mm": rear_travel_mm, "new_pair_moving_mass_kg": moving_kg,
            "unloaded_stem_force_N": empty_N,
            "front_and_rear_stem_force_N_by_assumed_mu": forces_N,
            "residual_capacity_N_by_assumed_mu": residual_capacity_N,
            "stem_force_limit_N": lock["equivalent_cam_force_N"],
            "residual_release_limit_N": RESIDUAL_N, "residual_verified": False}


def shortened_nose_sweep():
    lock = read_json("calc/T-1.2b/results.json")["mechanical_lock_A"]
    template = OPTIONS[1]
    rows = support_cases()
    candidates = []
    evaluated = 0
    for width_mm in range(44, 57):
        for overlap_mm in range(25, 46):
            evaluated += 1
            option = replace(template, x_mm=205. + overlap_mm / 2., width_mm=float(width_mm),
                             y_mm=132. - width_mm / 2., bearing_length_mm=float(overlap_mm),
                             travel_mm=overlap_mm + 4.8, moving_length_mm=overlap_mm + 34.)
            front_N = max(row["force_315_N"] * (row["x_mm"] - REAR_MM) /
                          (option.x_mm - REAR_MM) for row in rows)
            front_N *= (1. + PROOF_SKEW_Y_MM / option.y_mm) / 2.
            screen = member(option, front_N)
            if screen["land_mean_bearing_300_MPa"] <= 70. and screen["key"]["FKM_corrected"] >= 1.15:
                # The rear key tip moves from Y=105 to Y=136. R5 leaves a
                # 22 mm net contact width with the old 132 mm shoe wing.
                rear_load_N = max(row["force_315_N"] * (option.x_mm - row["x_mm"])
                                  / (option.x_mm - REAR_MM) for row in rows)
                rear_pressure_MPa = CYCLE * rear_load_N * (1. + PROOF_SKEW_Y_MM / 118.5) / 2. / (22.*32.)
                candidates.append({"geometry": asdict(option), "local": screen,
                                   "rear_pressure_300_MPa": rear_pressure_MPa,
                                   "drive": drive(option, lock, rear_travel_mm=31.)})
    best = min(candidates, key=lambda r: r["drive"]["front_and_rear_stem_force_N_by_assumed_mu"]["0.15"])
    return {"count_evaluated": evaluated, "count_pass_bearing_and_key_FKM": len(candidates),
            "best_stem_load": best, "rated_residual_N": RESIDUAL_N}


def moving_pair_kg(option):
    return 2. * option.moving_length_mm * option.width_mm * option.height_mm * DENSITY_KG_MM3


def opening(case, option, reaction, compliance_mm_N):
    """Reduced transverse strips with a concentrated load and elastic seats."""
    x0_mm, x1_mm = case["footprint_x_mm"]
    shoe_b_mm = min(204.8, x1_mm + 37.) - max(5.2, x0_mm - 37.)
    floor_b_mm = min(205., x1_mm + 50.) - max(-4., x0_mm - 50.)
    span_mm = 2. * option.y_mm
    force_300_N = CYCLE * case["force_315_N"]

    def strip(b_mm, h_mm):
        inertia_mm4 = b_mm * h_mm**3 / 12.
        return (force_300_N * span_mm**3 / (48. * E_MPa * inertia_mm4)
                + force_300_N * span_mm / (4. * (5./6.) * G_MPa * b_mm * h_mm))

    shoe_mm, floor_mm = strip(shoe_b_mm, 74.), strip(floor_b_mm, 100.)
    land_mm = max(abs(reaction[k]) for k in ("front_minus", "front_plus")) * CYCLE * compliance_mm_N
    return {"shoe_strip_mm": shoe_mm, "floor_strip_mm": floor_mm, "front_local_mm": land_mm,
            "seating_mm": .04, "opening_300_mm": CORRECTION * (shoe_mm + floor_mm + land_mm) + .04,
            "case": case}


def interfaces(option):
    if option.kind == "key":
        end_x_mm = option.x_mm + option.width_mm / 2. + .8 + option.cheek_leg_mm
        return {"front_cheek_end_x_mm": end_x_mm, "roof_clearance_x_mm": 205. - end_x_mm,
                "gate_clearance_x_mm": 289. - end_x_mm, "park_clearance_mm": 82. + option.travel_mm - 132.,
                "shoe_wing_to_cheek_y_mm": 135. - 132., "cap_to_column_y_mm": 235. - 198.}
    if option.kind == "nose":
        x_end_mm = 205. + option.bearing_length_mm
        y_mm = [option.y_mm - option.width_mm/2., option.y_mm + option.width_mm/2.]
        return {"slot_x_mm": [205., x_end_mm], "slot_abs_y_mm": y_mm,
                "slot_z_mm": [104., 104. + option.height_mm], "park_clearance_mm": 205. - x_end_mm + option.travel_mm,
                "gate_clearance_x_mm": 289. - x_end_mm, "slot_to_working_y_mm": y_mm[0] - 75.,
                "slot_to_column_y_mm": 235. - y_mm[1], "lamella_web_to_joint_mm": 250. - x_end_mm}
    end_x_mm = option.x_mm + option.bearing_length_mm / 2. + option.cheek_leg_mm
    return {"clevis_end_x_mm": end_x_mm, "roof_clearance_x_mm": 205. - end_x_mm,
            "gate_clearance_x_mm": 289. - end_x_mm, "park_clearance_mm": option.travel_mm - option.bearing_length_mm
            - option.cheek_leg_mm, "tongue_to_column_y_mm": 235. - option.y_mm - option.width_mm/2.}


def candidates():
    lock = read_json("calc/T-1.2b/results.json")["mechanical_lock_A"]
    cases = [row | {"y_mm": offset*PROOF_SKEW_Y_MM}
             for row in support_cases() for offset in (-1, 0, 1)]
    result = {}
    for option in (BASE, *OPTIONS):
        responses = [equilibrium(case, option) for case in cases]
        peak_i = max(range(len(cases)), key=lambda i: responses[i][0]["front_plus"])
        proof = responses[peak_i][0]
        front = member(option, proof["front_plus"])
        extents = {}
        for name in proof:
            low, high = (pick(range(len(cases)), key=lambda i: responses[i][0][name]) for pick in (min, max))
            extents[name] = {"min_315_N": responses[low][0][name], "min_case": cases[low],
                             "max_315_N": responses[high][0][name], "max_case": cases[high]}
        worst_opening = max((opening(case, option, reaction, front["local_compliance_mm_N"])
                             for case, (reaction, _) in zip(cases, responses, strict=True)),
                            key=lambda row: row["opening_300_mm"])
        result[option.name] = {
            "geometry": asdict(option), "front": front, "interfaces": interfaces(option),
            "opening": worst_opening, "drive": drive(option, lock), "checked_case_count": len(cases),
            "reaction_extents": extents, "governing_front_reactions_315_N": proof,
            "governing_front_case": cases[peak_i],
            "max_force_balance_error_N": max(abs(errors[0]) for _, errors in responses),
            "max_moment_balance_error_Nmm": max(max(abs(e) for e in errors[1:]) for _, errors in responses),
        }
    return result

