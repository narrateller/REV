"""Analytical balances and comparisons for the prescribed static surrogate."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Sample:
    q_m: float
    span_m: float
    actuator_y_m: float
    reaction_y_m: float
    reaction_z_m: float


def section_properties(dimensions):
    width = dimensions["chamber_width"]
    height = dimensions["chamber_height"]
    diameter = dimensions["rod_diameter"]
    rod_inertia = math.pi * diameter**4 / 64
    return {
        "rod": {"area_m2": math.pi * diameter**2 / 4,
                "I_y_m4": rod_inertia, "I_z_m4": rod_inertia},
        "carrier": {"area_m2": width * height, "I_y_m4": width * height**3 / 12,
                    "I_z_m4": height * width**3 / 12},
    }


def cross(a, b):
    ax, ay, az = a
    bx, by, bz = b
    return ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx


def sum_and_check(terms):
    residual = tuple(math.fsum(component) for component in zip(*terms, strict=True))
    for axis, component in enumerate(zip(*terms, strict=True)):
        tolerance = 64 * math.ulp(max(1.0, *map(abs, component)))
        if abs(residual[axis]) > tolerance:
            raise ValueError(f"Equilibrium residual {residual[axis]} exceeds {tolerance}")
    return residual


def balance(loads):
    forces = [force for _, force in loads]
    moments = [cross(location, force) for location, force in loads]
    return {"force_N": sum_and_check(forces), "moment_Nm_at_O": sum_and_check(moments)}


def frame_balance(loads):
    return balance([(point, tuple(-value for value in force)) for point, force in loads])


def reactions(force, pose, path, family):
    """Signed transverse guides and the assumed axial branch, on both free bodies."""
    q, span = pose.q_m, pose.span_m
    y, ey, ez = pose.actuator_y_m, pose.reaction_y_m, pose.reaction_z_m
    my, mz = -force * ez, force * (ey - y)
    g_plus = (0.0, -mz / span, my / span)
    g_minus = tuple(-value for value in g_plus)
    loads = [
        ((q, y, 0.0), (force, 0.0, 0.0)),
        ((q, ey, ez), (-force, 0.0, 0.0)),
        ((q - span / 2, 0.0, 0.0), g_minus),
        ((q + span / 2, 0.0, 0.0), g_plus),
    ]
    result = {
        "applied_pair_moment_Nm": (0.0, my, mz),
        "mobile": {"actuator_x_N": force, "axial_branch_x_N": -force,
                   "G_minus_N": g_minus, "G_plus_N": g_plus, "residual": balance(loads)},
        "frame": {"actuator_mount_x_N": -force, "axial_branch_x_N": force,
                  "G_minus_N": g_plus, "G_plus_N": g_minus, "residual": frame_balance(loads)},
    }
    if family == "B":
        result["B_assumed_frame_path_x_N"] = {
            "direct_seat": force if path == "B_CLOSED_STOP_SEAT" else 0.0,
            "lock_backed_stop": force if path == "B_CLOSED_LOCK_BACKED_STOP" else 0.0,
            "actual_split": None,
        }
    return result


def stresses(internal_n, my, mz, dimensions, sections, reference_yield):
    rod = internal_n / sections["rod"]["area_m2"]
    carrier = sections["carrier"]
    axial = internal_n / carrier["area_m2"]
    half_width = dimensions["chamber_width"] / 2
    half_height = dimensions["chamber_height"] / 2
    corners = {}
    for side_y, y in (("-Y", -half_width), ("+Y", half_width)):
        for side_z, z in (("-Z", -half_height), ("+Z", half_height)):
            corners[f"{side_y},{side_z}"] = axial + my * z / carrier["I_y_m4"] - mz * y / carrier["I_z_m4"]
    critical_corner = max(corners, key=lambda corner: abs(corners[corner]))
    carrier_abs = abs(corners[critical_corner])
    return {
        "internal_N_tension_positive_N": internal_n,
        "rod": {"axial_stress_Pa": rod, "max_abs_stress_Pa": abs(rod),
                "abs_stress_over_reference_yield": abs(rod) / reference_yield},
        "carrier": {"mean_axial_stress_Pa": axial, "corner_stress_Pa": corners,
                    "critical_corner": critical_corner, "max_abs_stress_Pa": carrier_abs,
                    "abs_stress_over_reference_yield": carrier_abs / reference_yield},
    }


def buckling(internal_n, q, dimensions, sections, material, conditions):
    lengths = {"rod": dimensions["rod_diameter"] + q,
               "carrier": dimensions["chamber_length"] + q}
    if internal_n >= 0:
        reason = "TENSION" if internal_n > 0 else "ZERO_AXIAL_LOAD"
        return {"status": "NOT_APPLICABLE", "reason": reason, "free_length_m": lengths, "comparisons": {}}

    modulus = material["young_modulus_Pa"]
    reference_yield = material["reference_yield_Pa"]
    results = {}
    for member, axes in (("rod", ("y",)), ("carrier", ("y", "z"))):
        section = sections[member]
        area = section["area_m2"]
        for axis in axes:
            inertia = section[f"I_{axis}_m4"]
            key = "rod/either_axis" if member == "rod" else f"carrier/{axis}"
            results[key] = {}
            for condition, k in conditions.items():
                effective_length = k * lengths[member]
                slenderness = effective_length / math.sqrt(inertia / area)
                critical_force = math.pi**2 * modulus * inertia / effective_length**2
                critical_stress = critical_force / area
                elastic_comparison = critical_stress < reference_yield
                results[key][condition] = {
                    "K": k, "effective_length_m": effective_length, "slenderness": slenderness,
                    "euler_force_N": critical_force, "compression_over_euler": -internal_n / critical_force,
                    "euler_stress_Pa": critical_stress, "euler_stress_over_reference_yield": critical_stress / reference_yield,
                    "elastic_check": ("ELASTIC_COMPARISON_ONLY" if elastic_comparison
                                      else "EULER_STRESS_AT_OR_ABOVE_REFERENCE_YIELD"),
                }
    return {"status": "EULER_COMPARISON", "free_length_m": lengths, "comparisons": results}


def equilibrated(force, pose, path, variant, dimensions, sections, assumptions):
    section4 = reactions(force, pose, path, variant[0])
    _, my, mz = section4["applied_pair_moment_Nm"]
    material = assumptions["comparison_material"]
    return {
        "status": "CALCULATED_ASSUMED",
        "section_4": section4,
        "section_5": stresses(-force, my, mz, dimensions, sections, material["reference_yield_Pa"]),
        "section_6": buckling(-force, pose.q_m, dimensions, sections, material, assumptions["buckling_comparisons"]),
    }


def released(force):
    if force == 0:
        raise ValueError("Use the unloaded control for a released branch at zero force")
    return {
        "status": "NO_STATIC_EQUILIBRIUM",
        "section_4": {"unbalanced_mobile_axial_force_N": force,
                      "unbalanced_frame_axial_force_N": -force,
                      "available_axial_reaction_N": 0.0, "equilibrium_reactions": None},
        "section_5": {"status": "NOT_RUN", "reason": "NO_STATIC_EQUILIBRIUM"},
        "section_6": {"status": "NOT_RUN", "reason": "NO_STATIC_EQUILIBRIUM"},
    }
