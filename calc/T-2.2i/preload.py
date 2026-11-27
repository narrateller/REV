"""Lamé and FKM mean-stress feasibility screens for the gate-end collar."""

from math import hypot, pi, sqrt

from hand import CYCLE, E_MPa, NU, fatigue_base
from mass import collar_kg

THERMAL_EXPANSION_PER_K = 12.1e-6
SENSITIVITY_K = (0., 20., 40., 60.)
COLLAR_X_MM = (260., 288.)


def lame_constants(a_mm, b_mm, c_mm):
    core = (b_mm**2 + a_mm**2) / (b_mm**2 - a_mm**2)
    collar = (c_mm**2 + b_mm**2) / (c_mm**2 - b_mm**2)
    flexibility_mm_MPa = b_mm / E_MPa * ((core - NU) + (collar + NU))
    hoop_relief = 2. * b_mm**2 / (b_mm**2 - a_mm**2)
    core_bore_gain = 2. * a_mm**2 / (b_mm**2 - a_mm**2)
    return flexibility_mm_MPa, hoop_relief, collar, core_bore_gain


def calculate(ring, end_reference, bore_proof_MPa, axial_force_315_N):
    """Equivalent circular open cylinder with uniform interface pressure.

    Reconstruct a uniaxial tensile demand using the old FKM without gradient.
    The old peak von Mises lies within about 2 percent of the reconstructed
    proof tension. A 3D tensor history is required for qualification.
    """
    width_mm = 2. * (90. + ring["inner_R_mm"])
    height_mm = 2. * ring["inner_z_mm"]
    aperture_mm2 = width_mm * height_mm - (4. - pi) * ring["inner_R_mm"]**2
    a_mm = sqrt(aperture_mm2 / pi)
    ro_mm = ring["outer_R_mm"]
    b_mm = hypot(ring["side_half_mm"] - ro_mm, ring["band_half_mm"] - ro_mm) + ro_mm
    ring_outline_mm2 = 4. * ring["side_half_mm"] * ring["band_half_mm"] - (4. - pi) * ro_mm**2
    length_mm = COLLAR_X_MM[1] - COLLAR_X_MM[0]

    base_MPa, mean_sensitivity = fatigue_base(1000.)
    reference_demand_MPa = base_MPa / end_reference["FKM_no_gradient"]
    amplitude_MPa = reference_demand_MPa / (1. + mean_sensitivity)
    target_FKM = 1.
    max_tensile_mean_MPa = (base_MPa / target_FKM - amplitude_MPa) / mean_sensitivity
    required_hoop_relief_MPa = amplitude_MPa - max_tensile_mean_MPa
    margin = 800. / 1.5
    thermal_delta_mm = b_mm * THERMAL_EXPANSION_PER_K * max(SENSITIVITY_K)

    # Minimise collar mass while reserving enough contact pressure at the
    # hot limit. Maximum von Mises of axisymmetric plane stress is at r=b.
    def sizing(thickness_mm):
        c_mm = b_mm + thickness_mm
        flexibility, relief, hoop, core_gain = lame_constants(a_mm, b_mm, c_mm)
        required_hot_MPa = required_hoop_relief_MPa / relief
        design_interference_mm = required_hot_MPa * flexibility + thermal_delta_mm
        cold_MPa = design_interference_mm / flexibility
        additional_proof_MPa = b_mm / E_MPa * core_gain * bore_proof_MPa / flexibility
        proof_MPa = cold_MPa + additional_proof_MPa
        proof_vm_MPa = proof_MPa * sqrt(hoop**2 + hoop + 1.)
        return design_interference_mm, cold_MPa, proof_MPa, proof_vm_MPa

    low_mm, high_mm = 1., 160.
    assert sizing(low_mm)[3] > margin > sizing(high_mm)[3]
    for _ in range(64):
        trial_mm = (low_mm + high_mm) / 2.
        if sizing(trial_mm)[3] > margin:
            low_mm = trial_mm
        else:
            high_mm = trial_mm
    t_mm = high_mm
    c_mm = b_mm + t_mm
    flexibility, relief, hoop, _ = lame_constants(a_mm, b_mm, c_mm)
    delta_mm, cold_MPa, proof_MPa, proof_vm_MPa = sizing(t_mm)
    stress_scale = sqrt(hoop**2 + hoop + 1.)
    hoop_range_MPa = hoop * (proof_MPa - cold_MPa) * CYCLE
    vm_range_MPa = stress_scale * (proof_MPa - cold_MPa) * CYCLE
    collar_fkm = base_MPa / (vm_range_MPa / 2. +
                             mean_sensitivity * (hoop * cold_MPa + hoop_range_MPa / 2.))
    hot_rows = []
    for temperature_difference_K in SENSITIVITY_K:
        elastic_fit_mm = delta_mm - b_mm * THERMAL_EXPANSION_PER_K * temperature_difference_K
        pressure_MPa = max(0., elastic_fit_mm / flexibility)
        mean_MPa = amplitude_MPa - relief * pressure_MPa
        hot_rows.append({"collar_minus_core_K": temperature_difference_K,
                         "effective_radial_interference_mm": elastic_fit_mm,
                         "fit_pressure_MPa": pressure_MPa, "bore_mean_MPa": mean_MPa,
                         "scalar_FKM_mean_only": base_MPa /
                         (amplitude_MPa + mean_sensitivity * max(0., mean_MPa)),
                         "minimum_mu_if_holding_full_axial_reaction":
                         axial_force_315_N / (2. * pi * b_mm * length_mm * pressure_MPa)})
    centre_pitch_mm = 540. / 2.
    smooth_radius_mm = 35.
    radial_column_clearance_mm = sqrt(2.) * centre_pitch_mm - smooth_radius_mm - c_mm
    # The gate wing may reach X=289 at |Y|>=80 mm. Retain a gap in X.
    fill_kg = (pi*b_mm**2-ring_outline_mm2) * length_mm * 7.85e-6
    minimum_pressure_MPa = hot_rows[-1]["fit_pressure_MPa"]
    return {
        "model": "open concentric cylinders; scalar FKM mean-only, no hoop-range reduction credit",
        "end_reference_FKM_no_gradient": end_reference["FKM_no_gradient"],
        "end_reference_vm_315_MPa": 800. / end_reference["static"],
        "reconstructed_uniaxial_range_315_MPa": 2. * amplitude_MPa / CYCLE,
        "required_bore_compression_MPa": required_hoop_relief_MPa,
        "range_reduction_needed_without_preload_fraction": 1. - end_reference["FKM_no_gradient"],
        "maximum_FKM_if_tensile_mean_zero": base_MPa / amplitude_MPa,
        "x_mm": list(COLLAR_X_MM), "a_mm": a_mm, "b_mm": b_mm, "c_mm": c_mm,
        "radial_wall_mm": t_mm, "cold_radial_interference_mm": delta_mm,
        "temperature_to_just_clear_cold_fit_K": delta_mm / (b_mm * THERMAL_EXPANSION_PER_K),
        "cold_fit_pressure_MPa": cold_MPa, "proof_fit_pressure_MPa": proof_MPa,
        "proof_collar_vm_MPa": proof_vm_MPa, "nominal_collar_static": 800. / proof_vm_MPa,
        "collar_nominal_FKM_cold": collar_fkm,
        "cold_collar_inner_hoop_MPa": hoop * cold_MPa,
        "clearance_to_gate_wing_x_mm": 289. - COLLAR_X_MM[1],
        "clearance_to_column_radial_mm": radial_column_clearance_mm,
        "collar_gross_kg": collar_kg(b_mm, c_mm, length_mm),
        "rounding_fill_gross_kg": fill_kg,
        "slip_sensitivity": hot_rows,
        "ideal_half_split_force_N": minimum_pressure_MPa * b_mm * length_mm,
        "min_ideal_wrap_area_each_side_mm2": minimum_pressure_MPa * b_mm * length_mm / margin,
        "known_unknowns": ["temperature gradients and local slip", "stress tensors and contact at slot",
                           "shape effects on band pressure and winding seats",
                           "tie joints holes and actual stiffness distribution"],
    }

