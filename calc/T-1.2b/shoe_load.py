"""T-1.2b static screening, ejection clearance, and comparative cycle inputs."""

from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
import json
from math import ceil, cos, exp, expm1, pi, prod, sin, sqrt
from pathlib import Path
import sys

import yaml

from x1_calc import BAR_PA, converged_run, make_model, supply_bar

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = ("low", "base", "high")
DUMP_TIMES_S = (.50, .64)
RESERVE_FORCE_N = 1_700_000
EJECTION_FORCE_N = 100_000  # T-1.2 X-1 excludes the punch guide's 8 kN.
DOSE_PARKING_MM = 257  # TASK, nominal loose dose at 90 kg/m³.
STEEL_RP02_MPA = 900  # Purchase requirement for finished section.
STEEL_DENSITY_KG_M3 = 7850
STEEL_E_MPA = 210_000
STEEL_POISSON = .30


def read_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def previous_geometry():
    spec = spec_from_file_location("geometry_t12_readonly", ROOT / "calc/T-1.2/geometry.py")
    geometry = module_from_spec(spec)
    bytecode_setting = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(geometry)
    finally:
        sys.dont_write_bytecode = bytecode_setting
    return geometry


def kg_steel(volume_mm3):
    return volume_mm3 * 1e-9 * STEEL_DENSITY_KG_M3


def round_up(value, step):
    return step * ceil(value / step)


def integrate_shoe(K, decay_per_mm, axial_equivalent_MPa, punch_x_mm, *,
                   width_mm, window_x_mm, piece_length_mm, residual_MPa=0.0):
    """Integrate upward traction over the briquette/shoe intersection."""
    start_x_mm = max(punch_x_mm, window_x_mm[0])
    end_x_mm = min(punch_x_mm + piece_length_mm, window_x_mm[1])
    length_mm = max(0.0, end_x_mm - start_x_mm)
    if length_mm == 0:
        return {"contact_length_mm": 0.0, "force_N": 0.0,
                "centroid_x_mm": None, "moment_about_pre_axis_Nm": 0.0}
    sigma_start_MPa = K * axial_equivalent_MPa * exp(-decay_per_mm * (start_x_mm - punch_x_mm))
    drop_fraction = -expm1(-decay_per_mm * length_mm)
    force_N = width_mm * sigma_start_MPa * drop_fraction / decay_per_mm
    centroid_x_mm = start_x_mm + 1 / decay_per_mm - length_mm / expm1(decay_per_mm * length_mm)
    return {
        "contact_length_mm": length_mm, "contact_x_mm": [start_x_mm, end_x_mm],
        "axial_at_contact_start_MPa": sigma_start_MPa / K - residual_MPa,
        "radial_at_contact_start_MPa": sigma_start_MPa,
        "radial_at_contact_end_MPa": sigma_start_MPa * (1 - drop_fraction),
        "force_N": force_N, "centroid_x_mm": centroid_x_mm, "centroid_y_mm": 0.0,
        "moment_about_pre_axis_Nm": force_N * (centroid_x_mm - sum(window_x_mm) / 2) / 1000,
        "moment_about_window_start_Nm": force_N * (centroid_x_mm - window_x_mm[0]) / 1000,
    }


def load_study(material, params, old, pressure_cases_N, doses_kg):
    width_mm, height_mm = params["chamber"]["section_mm"]
    area_mm2, perimeter_mm = width_mm * height_mm, 2 * (width_mm + height_mm)
    axis = old["axis"]
    window_x_mm = [axis["window_start_x_mm"], axis["window_end_x_mm"]]
    gate_x_mm = axis["closed_gate_inner_face_x_mm"]

    def sample(force_N, dose_kg, case, *, fixed_length_mm=None):
        K, mu = (material.curve[key][case] for key in ("K", "mu"))
        decay_per_mm = K * mu * perimeter_mm / area_mm2
        face_MPa = force_N / area_mm2
        # Keep the T-1.2 constitutive inversion for geometry. Vary all K/μ in the shoe integral.
        rho_kg_m3 = material.loaded_density_kg_m3(face_MPa, 90, case, dose_kg=dose_kg)
        length_mm = (dose_kg * 1e9 / (area_mm2 * rho_kg_m3)
                     if fixed_length_mm is None else fixed_length_mm)
        punch_x_mm = gate_x_mm - length_mm
        contact = dict(punch_x_mm=punch_x_mm, width_mm=width_mm,
                       window_x_mm=window_x_mm, piece_length_mm=length_mm)
        press = integrate_shoe(K, decay_per_mm, face_MPa, **contact)
        # In sliding ejection p(L)=0. A uniform locked-in lateral term K*p0
        # gives dp/dx=-lambda*(p+p0); set p(0)=F_eject/A to identify that term.
        eject_face_MPa = EJECTION_FORCE_N / area_mm2
        residual_MPa = eject_face_MPa / expm1(decay_per_mm * length_mm)
        ejection = integrate_shoe(K, decay_per_mm, eject_face_MPa + residual_MPa,
                                  residual_MPa=residual_MPa, **contact)
        ejection["residual_radial_offset_MPa"] = K * residual_MPa
        assert abs(ejection["force_N"] * mu * perimeter_mm / width_mm - EJECTION_FORCE_N) < 1e-6
        return {"case": case, "K": K, "mu": mu, "axial_input_force_N": force_N,
                "axial_face_MPa": face_MPa, "attenuation_per_mm": decay_per_mm, "dose_kg": dose_kg,
                "loaded_density_kg_m3": rho_kg_m3, "loaded_length_mm": length_mm, "punch_x_mm": punch_x_mm,
                "springback_axial_fraction": material.axial_ratio(case) - 1,
                "axial_growth_mm": length_mm * (material.axial_ratio(case) - 1),
                "press": press, "open_gate_ejection_start": ejection}

    samples = {dose: {basis: {case: sample(force_N, mass_kg, case) for case in CASES}
                      for basis, force_N in pressure_cases_N.items()} for dose, mass_kg in doses_kg.items()}
    nominal_length_mm = samples["nominal"]["nominal"]["base"]["loaded_length_mm"]
    comparison = {}
    for case, reference_N in {"base": 660_000, "high": 790_000}.items():
        actual = samples["nominal"]["nominal"][case]["press"]["force_N"]
        fixed_N = sample(pressure_cases_N["nominal"], doses_kg["nominal"], case,
                         fixed_length_mm=nominal_length_mm)["press"]["force_N"]
        comparison[case] = {"reference_approx_N": reference_N, "same_base_length_N": fixed_N,
                            "own_case_length_N": actual, "difference_N": actual - reference_N}
    return {"window_x_mm": window_x_mm, "pre_axis_x_mm": sum(window_x_mm) / 2, "shoe_face_z_mm": height_mm,
            "bulk_density_kg_m3": 90, "ejection_resistance_N": EJECTION_FORCE_N,
            "comparison_with_opus": comparison, "samples": samples}


def bridge_constants(force_N, width_mm, clear_span_mm, support_span_mm):
    half_span_mm, half_load_mm = support_span_mm / 2, clear_span_mm / 2
    offset_mm = half_span_mm - half_load_mm
    line_load_N_mm = force_N / clear_span_mm
    peak_M_Nmm = force_N * (2 * support_span_mm - clear_span_mm) / 8
    # Unit-load integration, with rectangular-section Timoshenko shear.
    bend_constant_mm4 = 12 * (force_N * half_span_mm**3 / 6 - line_load_N_mm / 2 *
                              (half_load_mm**4 / 4 + offset_mm * half_load_mm**3 / 3)) / (STEEL_E_MPA * width_mm)
    shear_G_MPa = STEEL_E_MPA / (2 * (1 + STEEL_POISSON))
    shear_constant_mm2 = (force_N * half_span_mm / 2 - line_load_N_mm * half_load_mm**2 / 2) / (
        (5 / 6) * shear_G_MPa * width_mm)
    return peak_M_Nmm, bend_constant_mm4, shear_constant_mm2


def gate_study(params, strength_criteria, relief_factor, load):
    width_mm, clear_span_mm = params["chamber"]["section_mm"]
    land_mm = 12.0  # Upper and lower replaceable support strips.
    span_mm = clear_span_mm + land_mm  # Support line at center of each strip.
    allowable_MPa = STEEL_RP02_MPA / strength_criteria["min_safety_factor_yield"]
    deflection_limit_mm = .15  # Screening budget for plate deflection alone.

    design_N = RESERVE_FORCE_N * relief_factor
    peak_M_Nmm, bend_constant_mm4, shear_constant_mm2 = bridge_constants(design_N, width_mm, clear_span_mm, span_mm)
    minimum_strength_mm = sqrt(6 * peak_M_Nmm / (width_mm * allowable_MPa))
    minimum_shear_mm = sqrt(3) * 1.5 * design_N / (2 * width_mm * allowable_MPa)
    lo_mm, hi_mm = 1.0, 200.0
    for _ in range(50):
        mid_mm = (lo_mm + hi_mm) / 2
        if bend_constant_mm4 / mid_mm**3 + shear_constant_mm2 / mid_mm > deflection_limit_mm:
            lo_mm = mid_mm
        else:
            hi_mm = mid_mm
    minimum_deflection_mm = hi_mm
    thickness_mm = ceil(max(minimum_strength_mm, minimum_shear_mm, minimum_deflection_mm)) + 2

    def checks(force_N):
        moment_Nmm, bend, shear = bridge_constants(force_N, width_mm, clear_span_mm, span_mm)
        return {"load_N": force_N, "max_moment_Nmm": moment_Nmm,
                "bending_MPa": 6 * moment_Nmm / (width_mm * thickness_mm**2),
                "shear_von_mises_MPa": sqrt(3) * 1.5 * force_N / (2 * width_mm * thickness_mm),
                "average_land_bearing_MPa": force_N / (2 * land_mm * width_mm),
                "bending_deflection_mm": bend / thickness_mm**3,
                "shear_deflection_mm": shear / thickness_mm,
                "total_deflection_mm": bend / thickness_mm**3 + shear / thickness_mm}

    axial_clearance_mm = 5
    clearance = {}
    for dose, pressures in load["samples"].items():
        clearance[dose] = {}
        for basis, cases in pressures.items():
            clearance[dose][basis] = {
                case: {"loaded_length_mm": row["loaded_length_mm"], "axial_growth_mm": row["axial_growth_mm"],
                       "minimum_mm": thickness_mm + row["axial_growth_mm"] + axial_clearance_mm,
                       "travel_overrun_mm": ceil(thickness_mm + row["axial_growth_mm"] + axial_clearance_mm)}
                for case, row in cases.items()}
    nominal_mm = clearance["nominal"]["nominal"]["base"]["travel_overrun_mm"]
    worst_mm = max(row["travel_overrun_mm"] for cases in clearance.values()
                   for scenarios in cases.values() for row in scenarios.values())
    gate_opening_mm = clear_span_mm + land_mm + 3
    reserve, relief = checks(RESERVE_FORCE_N), checks(design_N)
    assert max(relief["bending_MPa"], relief["shear_von_mises_MPa"],
               relief["average_land_bearing_MPa"]) <= allowable_MPa
    assert relief["total_deflection_mm"] <= deflection_limit_mm
    return {"material": "34CrNiMo6+QT", "specified_Rp02_min_MPa": STEEL_RP02_MPA, "E_MPa": STEEL_E_MPA,
            "poisson_ratio": STEEL_POISSON, "clear_opening_mm": [width_mm, clear_span_mm],
            "bearing_land_mm_each": land_mm, "support_center_span_mm": span_mm,
            "allowable_stress_MPa": allowable_MPa, "allowable_deflection_mm": deflection_limit_mm,
            "min_thickness_by_bending_mm": minimum_strength_mm, "min_thickness_by_shear_mm": minimum_shear_mm,
            "min_thickness_by_deflection_mm": minimum_deflection_mm,
            "thickness_mm": thickness_mm, "reserve_300_bar": reserve, "structural_315_bar_screen": relief,
            "gate_opening_travel_mm": gate_opening_mm, "gate_installed_stroke_mm": gate_opening_mm + 5,
            "axial_clearance_mm": axial_clearance_mm,
            "opening_clearance_mm": gate_opening_mm - clear_span_mm - land_mm,
            "front_plane_x_mm": load["window_x_mm"][1] + thickness_mm,
            "clearance_cases": clearance, "nominal_overtravel_mm": nominal_mm, "max_overtravel_mm": worst_mm}


def design_lock(load, gate, relief_factor, width_mm):
    samples = [row for dosed in load["samples"].values() for cases in dosed.values() for row in cases.values()]
    worst = max(samples, key=lambda row: row["press"]["force_N"])
    assert worst["axial_input_force_N"] == RESERVE_FORCE_N
    peak_MPa = max(row["press"]["radial_at_contact_start_MPa"] for row in samples)
    height_mm, engagement_mm, gap_mm = 90, 32, 4
    length_mm = load["window_x_mm"][1] - load["window_x_mm"][0]
    max_share = .60  # Asymmetric transverse load share.
    concentration = 1.20  # Local load concentration to verify on the bridge and liners.
    q_N_mm = relief_factor * max_share * concentration * peak_MPa * width_mm
    eccentricity_mm = gap_mm + engagement_mm  # Reaction at the far edge.
    sigma_MPa = 6 * q_N_mm * eccentricity_mm / height_mm**2
    tau_MPa = 1.5 * q_N_mm / height_mm
    von_mises_MPa = sqrt(sigma_MPa**2 + 3 * tau_MPa**2)
    bearing_MPa = q_N_mm / engagement_mm
    assert max(von_mises_MPa, bearing_MPa) <= gate["allowable_stress_MPa"]

    key_slide_mm = engagement_mm + gap_mm
    cam_travel_mm = 12
    drag_N_key, cam_efficiency = 600, .60
    key_mass_kg = kg_steel(length_mm * (2 * engagement_mm + gap_mm) * height_mm)
    cam_stem_speed_mm_s = 300
    # Half-cosine key motion over the extra stem travel. Bound opposing inertial load
    # at the commanded stem speed; both keys have the same mass and cam.
    peak_ratio = pi * key_slide_mm / (2 * cam_travel_mm)
    peak_acceleration_m_s2 = peak_ratio * pi / cam_travel_mm * cam_stem_speed_mm_s**2 / 1000
    cam_force_N = max(
        2 * peak_ratio * sin(pi * i / 100) *
        (drag_N_key + key_mass_kg * peak_acceleration_m_s2 * abs(cos(pi * i / 100))) / cam_efficiency
        for i in range(101)
    )
    shoe_width_mm = width_mm + 2 * (gap_mm + engagement_mm)
    shoe_support_span_mm = width_mm + 2 * gap_mm + engagement_mm
    shoe_deflection_limit_mm = .10  # Shoe alone, before wear, bridge and seat compliance.
    shoe_strip_width_mm = 1
    strip_load_N = peak_MPa * relief_factor * concentration * width_mm * shoe_strip_width_mm
    shoe_moment_Nmm, bend, shear = bridge_constants(strip_load_N, shoe_strip_width_mm, width_mm, shoe_support_span_mm)
    shoe_height_mm = 70
    while bend / shoe_height_mm**3 + shear / shoe_height_mm > shoe_deflection_limit_mm:
        shoe_height_mm += 5
    shoe_height_mm += 10  # Margin for interfaces to be detailed by T-1.5.
    shoe_deflection_mm = bend / shoe_height_mm**3 + shear / shoe_height_mm
    shoe_stress_MPa = 6 * shoe_moment_Nmm / (shoe_strip_width_mm * shoe_height_mm**2)
    assert shoe_stress_MPa <= gate["allowable_stress_MPa"]
    shoe_mass_kg = kg_steel(length_mm * shoe_width_mm * shoe_height_mm)
    rail_mass_kg = 2 * key_mass_kg
    bridge_and_cams_kg = kg_steel(2 * 240 * 65 * 95 + 240 * 400 * 35) + 5
    return {"material": gate["material"], "specified_Rp02_min_MPa": STEEL_RP02_MPA,
            "rail_length_mm": length_mm, "rail_height_mm": height_mm, "rail_bearing_engagement_mm": engagement_mm,
            "side_gap_mm": gap_mm, "key_slide_mm": key_slide_mm, "cam_extra_pre_cylinder_stroke_mm": cam_travel_mm,
            "no_load_slide_force_per_key_N": drag_N_key, "cam_efficiency": cam_efficiency,
            "cam_stem_speed_limit_mm_s": cam_stem_speed_mm_s, "single_key_moving_mass_kg": key_mass_kg,
            "key_peak_acceleration_m_s2": peak_acceleration_m_s2, "equivalent_cam_force_N": cam_force_N, "max_transverse_load_share": max_share,
            "local_pressure_multiplier": concentration, "worst_reserve_case": worst["case"],
            "worst_reserve_dose_kg": worst["dose_kg"], "max_shoe_load_at_300_bar_N": worst["press"]["force_N"],
            "max_shoe_load_at_315_bar_N": worst["press"]["force_N"] * relief_factor,
            "max_moment_about_pre_axis_Nm": max(row["press"]["moment_about_pre_axis_Nm"] for row in samples),
            "single_rail_load_at_300_bar_N": worst["press"]["force_N"] * max_share,
            "single_rail_load_at_315_bar_N": worst["press"]["force_N"] * relief_factor * max_share,
            "single_rail_design_line_load_N_mm": q_N_mm, "local_bearing_MPa": bearing_MPa,
            "local_bending_MPa": sigma_MPa, "local_shear_MPa": tau_MPa, "local_von_mises_MPa": von_mises_MPa,
            "shoe_support_span_mm": shoe_support_span_mm, "shoe_envelope_mm": [length_mm, shoe_width_mm, shoe_height_mm],
            "shoe_deflection_limit_mm": shoe_deflection_limit_mm, "shoe_deflection_mm": shoe_deflection_mm,
            "shoe_bending_stress_MPa": shoe_stress_MPa, "shoe_mass_kg": shoe_mass_kg,
            "mass_kg": rail_mass_kg + bridge_and_cams_kg, "added_mechanism_box_mm": [240, 400, 170]}


def isolated_work_zone(load, old, material, params):
    width_mm, height_mm = params["chamber"]["section_mm"]
    area_mm2, perimeter_mm = width_mm * height_mm, 2 * (width_mm + height_mm)
    window_x_mm = load["window_x_mm"]
    length_mm = old["axis"]["transferred_fill_length_mm"]
    max_loaded_mm = max(row["loaded_length_mm"] for dose in load["samples"].values()
                        for force in dose.values() for row in force.values())
    extension_mm = round_up(max_loaded_mm + 5, 5)
    gate_x_mm = window_x_mm[1] + extension_mm
    edge_drag_N = 12_000  # Entry lip and standstill friction allowance.
    operating_loads = []
    for row in old["precompaction"]["force_cases"]:
        if row["bulk_density_kg_m3"] != 90:
            continue
        case = row["case"]
        K, mu = (material.curve[key][case] for key in ("K", "mu"))
        decay_per_mm = K * mu * perimeter_mm / area_mm2
        for dose_name, mass_kg in old["precompaction"]["doses_kg"].items():
            # Upper bound: the plug retains the prior vertical face traction.
            residual_MPa = row[dose_name]["face_MPa"]
            drag_N = mu * residual_MPa * perimeter_mm * length_mm + edge_drag_N

            def shoe_force_N(face_MPa, punch_x_mm, piece_length_mm):
                force = integrate_shoe(K, decay_per_mm, face_MPa, punch_x_mm, width_mm=width_mm,
                                       window_x_mm=window_x_mm, piece_length_mm=piece_length_mm)["force_N"]
                return force + residual_MPa * width_mm * max(0, window_x_mm[1] - punch_x_mm)

            max_shoe_N = shoe_force_N(drag_N / area_mm2, window_x_mm[0], length_mm)
            for i in range(201):
                remaining_mm = length_mm - max(0, length_mm - extension_mm) * i / 200
                density_kg_m3 = mass_kg * 1e9 / (area_mm2 * remaining_mm)
                face_MPa = max(drag_N / area_mm2, material.face_MPa(density_kg_m3, 90, case, dose_kg=mass_kg))
                max_shoe_N = max(max_shoe_N, shoe_force_N(face_MPa, gate_x_mm - remaining_mm, remaining_mm))
            operating_loads.append({"case": case, "dose": dose_name, "mass_kg": mass_kg,
                                    "assumed_radial_traction_after_prepress_MPa": residual_MPa,
                                    "transfer_resistance_N": drag_N, "max_transient_shoe_load_N": max_shoe_N})
    return {"closed_zone_length_mm": extension_mm, "gate_x_mm": gate_x_mm,
            "max_loaded_length_mm": max_loaded_mm, "min_working_clearance_to_window_mm": extension_mm - max_loaded_mm,
            "edge_drag_assumption_N": edge_drag_N, "transfer_and_transient": operating_loads}


def capacity_N(cylinder, supply_limit_bar):
    return (supply_limit_bar - supply_bar(cylinder, 0, "extend")) * BAR_PA * cylinder.cap_m2 * cylinder.eta


def hydraulic_hold(lock, baseline_pre, working_limit_bar):
    target_bar = working_limit_bar - 15  # Margin to the 300-bar branch limit.
    design_load_N = lock["max_shoe_load_at_315_bar_N"]
    bore_mm = round_up(sqrt(4 * design_load_N / ((target_bar - 7) * BAR_PA * baseline_pre.eta) / pi) * 1000, 5)
    cylinder = replace(baseline_pre, bore_mm=bore_mm, rod_mm=round_up(.55 * bore_mm, 5))
    assert capacity_N(cylinder, target_bar) >= design_load_N
    gross_trapped_bar = design_load_N / (cylinder.cap_m2 * BAR_PA)
    passive_trapped_125_bar = design_load_N / (baseline_pre.cap_m2 * BAR_PA)
    return cylinder, {"design_shoe_load_N": design_load_N, "static_pressure_without_losses_bar": gross_trapped_bar,
                      "bore_125_static_pressure_without_losses_bar": passive_trapped_125_bar, "bore_mm": bore_mm, "rod_mm": cylinder.rod_mm,
                      "supply_setpoint_bar": target_bar, "capacity_at_setpoint_N": capacity_N(cylinder, target_bar),
                      "capacity_at_300_bar_N": capacity_N(cylinder, working_limit_bar),
                      "bore_125_required_supply_bar": supply_bar(baseline_pre, design_load_N, "extend"),
                      "bore_125_capacity_at_300_bar_N": capacity_N(baseline_pre, working_limit_bar)}


def layout(old, gate, model, *, lock, shoe_height_mm, max_mm):
    axis, pre = old["axis"], model.pre_cylinder
    gate_x_mm = axis["closed_gate_inner_face_x_mm"] + round(model.transfer_m * 1000)
    max_end_mm = gate_x_mm + gate["max_overtravel_mm"]
    body_mm = gate_x_mm - axis["body_guide_start_x_mm"]
    installed_main_mm = max_end_mm + axis["main_stop_reserve_mm"]
    lock_mass_kg = lock["mass_kg"] if lock else 0
    shoe_mass_kg = lock["shoe_mass_kg"] if lock else kg_steel(200 * 150 * shoe_height_mm)
    frame_module_mm = [body_mm + gate["thickness_mm"] + 25, 400 if lock else 320,
                       max(260, 60 + shoe_height_mm + (170 if lock else 80))]
    pre_outside_mm = pre.bore_mm + 2 * max(18, round_up(.12 * pre.bore_mm, 2))
    pre_length_mm = pre.stroke_mm + 145  # Caps, rod attachment, and bracket allowance.
    full_pre = old["precompaction"]
    elevation_mm = old["packaging"]["channel_floor_elevation_mm"] + full_pre["fill_height_mm"] + pre_length_mm + shoe_height_mm
    envelope_mm = [installed_main_mm + 400 + gate_x_mm + 350,  # Main head/rear allowance, outlet allowance.
                   max(frame_module_mm[1] + 160, pre_outside_mm + 900),  # Side feed and guards.
                   max(elevation_mm + 100, 1420)]  # Top guard or inlet plus hopper head.
    body_mass_kg = kg_steel(body_mm * (260 * 160 - 150 * 60) - 200 * 150 * 50)
    gate_mass_kg = kg_steel(gate["thickness_mm"] * 220 * 150 + 2 * 230 * 30 * 45) + 12
    pre_mass_kg = kg_steel(pi / 4 * (pre_outside_mm**2 - pre.bore_mm**2) * pre_length_mm
                          + pi / 4 * pre.rod_mm**2 * (pre.stroke_mm + 100)
                          + pi / 4 * pre_outside_mm**2 * 60) + shoe_mass_kg
    return {"gate_inner_x_mm": gate_x_mm, "gate_outer_x_mm": gate_x_mm + gate["thickness_mm"],
            "main_body_to_gate_mm": body_mm, "main_travel_nominal_mm": round(model.main_travel_m * 1000, 9),
            "main_travel_max_mm": max_end_mm, "main_installed_stroke_mm": installed_main_mm,
            "nominal_pre_shoe_stroke_mm": model.pre_travel_m * 1000, "max_pre_shoe_stroke_mm": full_pre["stroke_mm"],
            "nominal_pre_cylinder_travel_mm": (model.pre_travel_m + model.cam_m) * 1000,
            "max_pre_cylinder_travel_mm": full_pre["stroke_mm"] + model.cam_m * 1000,
            "pre_installed_stroke_mm": pre.stroke_mm, "pre_bore_mm": pre.bore_mm, "pre_rod_mm": pre.rod_mm,
            "frame_and_gate_box_mm": frame_module_mm, "pre_cylinder_box_mm": [pre_outside_mm, pre_outside_mm, pre_length_mm],
            "assembly_mass_kg": body_mass_kg + gate_mass_kg + pre_mass_kg + lock_mass_kg,
            "mass_breakdown_kg": {"chamber": body_mass_kg, "gate_and_actuator": gate_mass_kg,
                                   "prepress_cylinder_and_shoe": pre_mass_kg, "lock": lock_mass_kg},
            "packaging_screen_mm": envelope_mm,
            "remaining_to_C_ENV_01_mm": [limit - bound for limit, bound in zip(max_mm, envelope_mm, strict=True)]}


def calculation():
    params = read_yaml("design/params.t12.yaml")
    curve = read_yaml("calc/T-1.1/curve.yaml")
    criteria = read_yaml("ops/criteria/design_criteria.yaml")["criteria"]
    old = json.loads((ROOT / "calc/T-1.2/results.json").read_text(encoding="utf-8"))
    doses_kg = old["precompaction"]["doses_kg"]
    material = previous_geometry().Material(curve, params["raw"]["dose_kg"], params["chamber"]["section_mm"])
    nominal_N = params["main_cylinder"]["nominal_force_N"]
    pressure_limit_bar = criteria["C-HYD-01"]["max_working_bar"]
    relief_factor = criteria["C-HYD-01"]["max_relief_bar"] / pressure_limit_bar
    nominal_row = next(row for row in old["briquettes"] if
                       (row["case"], row["bulk_density_kg_m3"], row["pressure_basis"]) == ("base", 90, "nominal_force"))
    full_model, old_main = make_model(material, old, nominal_row, params)
    pump_L_min = params["drive"]["pump_max_flow_L_min"]
    cycle_limit_s = criteria["C-PERF-01"]["max_cycle_s"]

    def cycles(model, main):
        return {f"{feed_s:.2f}": converged_run(model, main, 90, feed_s, pump_L_min) for feed_s in DUMP_TIMES_S}

    baseline = replace(full_model, pre_travel_m=DOSE_PARKING_MM / 1000, ejection_N=EJECTION_FORCE_N)
    baseline_cycles = cycles(baseline, old_main)
    old_cycle = converged_run(full_model, old_main, 90, max(DUMP_TIMES_S), pump_L_min)
    upstream_reference = next(row for row in old["cycle"]["runs"] if
                              (row["case"], row["bulk_density_kg_m3"], row["feed_s"]) == ("base", 90, .64))
    assert abs(upstream_reference["cycle_s"] - old_cycle["cycle_s"]) < .002

    load = load_study(material, params, old, {"nominal": nominal_N, "reserve": RESERVE_FORCE_N}, doses_kg)
    gate = gate_study(params, criteria["C-STR-01"], relief_factor, load)
    lock = design_lock(load, gate, relief_factor, params["chamber"]["section_mm"][0])
    closed_zone = isolated_work_zone(load, old, material, params)
    hold_cylinder, hydraulic = hydraulic_hold(lock, baseline.pre_cylinder, pressure_limit_bar)
    closed_zone["pre_cylinder_capacity_N"] = capacity_N(baseline.pre_cylinder, pressure_limit_bar)
    assert max(row["max_transient_shoe_load_N"] for row in closed_zone["transfer_and_transient"]) < (
        closed_zone["pre_cylinder_capacity_N"])

    common = replace(baseline, overtravel_m=gate["nominal_overtravel_mm"] / 1000,
                     gate_travel_m=gate["gate_opening_travel_mm"] / 1000,
                     gate_cylinder=replace(baseline.gate_cylinder, stroke_mm=gate["gate_installed_stroke_mm"]))
    cam_mm = lock["cam_extra_pre_cylinder_stroke_mm"]
    baseline_drag_N = next(row["transfer_resistance_N"] for row in closed_zone["transfer_and_transient"]
                           if (row["case"], row["dose"]) == ("base", "nominal"))
    shoe_heights_mm = {"A": lock["shoe_envelope_mm"][2], "B": 45, "C": 100}
    models = {
        "A": replace(common, cam_m=cam_mm / 1000, cam_force_N=lock["equivalent_cam_force_N"],
                     cam_stem_speed_m_s=lock["cam_stem_speed_limit_mm_s"] / 1000,
                     pre_return_force_N=6000 + max(0, lock["shoe_mass_kg"] - kg_steel(200 * 150 * 45)) * 9.81,
                     pre_cylinder=replace(common.pre_cylinder, stroke_mm=common.pre_cylinder.stroke_mm + cam_mm)),
        "B": replace(common, transfer_m=closed_zone["closed_zone_length_mm"] / 1000, transfer_drag_N=baseline_drag_N),
        "C": replace(common, pre_cylinder=hold_cylinder, hold_supply_bar=hydraulic["supply_setpoint_bar"],
                     pre_return_force_N=6000 + kg_steel(200 * 150 * (shoe_heights_mm["C"] - 45)) * 9.81),
    }
    variants = {}
    main_cylinders = {}
    for code, model in models.items():
        dimensions = layout(old, gate, model, lock=lock if code == "A" else None, shoe_height_mm=shoe_heights_mm[code],
                            max_mm=criteria["C-ENV-01"]["max_mm"])
        main = replace(old_main, stroke_mm=dimensions["main_installed_stroke_mm"])
        main_cylinders[code] = main
        runs = cycles(model, main)
        variants[code] = {"dimensions": dimensions, "cycle": runs,
                          "delta_vs_parked_T12_s": {key: row["cycle_s"] - baseline_cycles[key]["cycle_s"]
                                                  for key, row in runs.items()}}
    assert all(margin >= 0 for margin in variants["A"]["dimensions"]["remaining_to_C_ENV_01_mm"])
    lock["cam_duration_by_dump_s"] = {dump: {
        "lock_s": run["motion_events"]["pre_down"]["end_s"] - run["motion_events"]["pre_down"]["marker_s"],
        "unlock_s": run["motion_events"]["pre_up"]["marker_s"] - run["motion_events"]["pre_up"]["start_s"],
    } for dump, run in variants["A"]["cycle"].items()}

    main_A, model_A = main_cylinders["A"], models["A"]
    min_grip_mm = 20
    shortest_in_die_mm = criteria["C-PROD-02"]["range_mm"][0] / material.axial_ratio("base")
    takeoff_nominal_mm = old["axis"]["ejection_overtravel_mm"]
    takeoff_max_mm = max(takeoff_nominal_mm, ceil(gate["thickness_mm"] + min_grip_mm - shortest_in_die_mm))
    takeoff_main = replace(main_A, stroke_mm=old["axis"]["closed_gate_inner_face_x_mm"] + takeoff_max_mm + 15)
    takeoff_pull_mm = gate["max_overtravel_mm"] - takeoff_nominal_mm
    takeoff = replace(model_A, overtravel_m=takeoff_nominal_mm / 1000, takeoff_travel_m=takeoff_pull_mm / 1000)
    takeoff_runs = cycles(takeoff, takeoff_main)
    takeoff_study = {"min_grip_projection_mm": min_grip_mm,
                     "shortest_briquette_in_die_mm": shortest_in_die_mm,
                     "nominal_overtravel_mm": takeoff_nominal_mm, "short_briquette_overtravel_mm": takeoff_max_mm,
                     "nominal_main_travel_mm": round(takeoff.main_travel_m * 1000, 9),
                     "max_main_travel_mm": takeoff_main.stroke_mm - 15,
                     "installed_main_stroke_mm": takeoff_main.stroke_mm, "pull_travel_mm": takeoff_pull_mm,
                     "cycle": takeoff_runs, "delta_vs_recommended_s": {
                         key: row["cycle_s"] - variants["A"]["cycle"][key]["cycle_s"]
                         for key, row in takeoff_runs.items()}}

    mass_110_kg = doses_kg["length_110"]
    length_110 = load["samples"]["length_110"]["nominal"]["base"]
    pre = old["precompaction"]
    parking_110_mm = ceil(mass_110_kg * 1e9 / (prod(pre["window_mm_axial_transverse"]) * 90)
                          - params["chamber"]["section_mm"][1] + pre["freeboard_mm"])
    model_110 = replace(model_A, dose_kg=mass_110_kg, in_die_kg_m3=length_110["loaded_density_kg_m3"],
                        pre_travel_m=parking_110_mm / 1000,
                        overtravel_m=gate["clearance_cases"]["length_110"]["nominal"]["base"]["travel_overrun_mm"] / 1000)
    cycle_110 = converged_run(model_110, main_A, 90, max(DUMP_TIMES_S), pump_L_min)
    t14 = []
    for shell_L, flows_L_min in ((5, (400, 450, 500, 550, 600, 650, 700)),
                                (7.5, (450, 500, 550, 600, 650))):
        for flow_L_min in flows_L_min:
            run = converged_run(model_A, main_A, 90, max(DUMP_TIMES_S), flow_L_min, shell_L)
            t14.append({key: run[key] for key in ("pump_max_flow_L_min", "accumulator_shell_L", "cycle_s",
                                                  "margin_to_6_s", "boost_L", "peak_shaft_kW")})

    t14_gate_speed = []
    for speed_m_s in (.35, .40, .50):
        for flow_L_min in (500, 550, 600):
            run = converged_run(replace(model_A, gate_speed_m_s=speed_m_s), main_A,
                                90, max(DUMP_TIMES_S), flow_L_min)
            t14_gate_speed.append({"gate_speed_m_s": speed_m_s, "pump_max_flow_L_min": flow_L_min,
                                   "accumulator_shell_L": 5, "cycle_s": run["cycle_s"],
                                   "margin_to_6_s": run["margin_to_6_s"]})

    dimensions_A = variants["A"]["dimensions"]
    result = {"sources": ["DECISIONS.md D0/D-OP-06", "ops/criteria/design_criteria.yaml v2",
                          "calc/T-1.1/curve.yaml", "calc/T-1.2/geometry.py", "calc/T-1.2/results.json",
                          "design/params.t12.yaml", "ops/reports/T-1.2/GK_review.md"],
              "main_section_mm": params["chamber"]["section_mm"], "cycle_limit_s": cycle_limit_s,
              "recommendation": "A", "shoe_load": load, "gate": gate, "mechanical_lock_A": lock,
              "closed_zone_B": closed_zone, "hydraulic_hold_C": hydraulic, "alternatives": variants,
              "T12_parked_reference": baseline_cycles, "T12_full_stroke_reproduction_s": old_cycle["cycle_s"],
              "T12_documented_full_stroke_s": upstream_reference["cycle_s"], "takeoff_screen": takeoff_study,
              "recommended_110mm_at_90_kg_m3": {"pre_shoe_parking_stroke_mm": parking_110_mm, **cycle_110},
              "T14_pump_accumulator_sensitivity": t14,
              "T14_gate_speed_sensitivity": t14_gate_speed,
              "axis_A": {**old["axis"], "punch_ejection_end_x_mm": dimensions_A["main_travel_nominal_mm"],
                         "press_end_x_mm": load["samples"]["nominal"]["nominal"]["base"]["punch_x_mm"],
                         "gate_outer_x_mm": gate["front_plane_x_mm"],
                         "main_installed_stroke_mm": main_A.stroke_mm,
                         "max_operating_travel_mm": dimensions_A["main_travel_max_mm"],
                         "main_required_travel_mm": dimensions_A["main_travel_nominal_mm"],
                         "ejection_overtravel_mm": gate["nominal_overtravel_mm"]},
              "nominal_product": nominal_row}
    return result, model_A, main_A


def main():
    results, _, _ = calculation()
    write_json(HERE / "results.json", results)
    screen = results["alternatives"]["A"]
    gate = results["gate"]
    loads = results["shoe_load"]["samples"]["nominal"]
    worst_run = screen["cycle"]["0.64"]
    lock = results["mechanical_lock_A"]
    output = {
        "task": "T-1.2b",
        "recommendation": results["recommendation"],
        "nominal_dose_kg": worst_run["dose_kg"],
        "main_axial_force_N": {basis: cases["base"]["axial_input_force_N"] for basis, cases in loads.items()},
        "end_press_shoe_force_N": {basis: {case: row["press"]["force_N"] for case, row in cases.items()}
                                   for basis, cases in loads.items()},
        "start_eject_shoe_force_N": {case: row["open_gate_ejection_start"]["force_N"]
                                    for case, row in loads["nominal"].items()},
        "max_shoe_force_300_bar_N": lock["max_shoe_load_at_300_bar_N"],
        "lock_local_bearing_MPa": lock["local_bearing_MPa"],
        "gate_plate_thickness_mm": gate["thickness_mm"],
        "gate_deflection_at_1p70_MN_mm": gate["reserve_300_bar"]["total_deflection_mm"],
        "gate_working_travel_mm": gate["gate_opening_travel_mm"],
        "nominal_ejection_overtravel_mm": gate["nominal_overtravel_mm"],
        "max_ejection_overtravel_mm": gate["max_overtravel_mm"],
        "main_working_nominal_mm": screen["dimensions"]["main_travel_nominal_mm"],
        "main_working_max_mm": screen["dimensions"]["main_travel_max_mm"],
        "main_installed_stroke_mm": screen["dimensions"]["main_installed_stroke_mm"],
        "precompaction_bore_mm": screen["dimensions"]["pre_bore_mm"],
        "cycle_base_0p50_s": screen["cycle"]["0.50"]["cycle_s"],
        "cycle_base_0p64_s": worst_run["cycle_s"],
        "cycle_increase_vs_parked_T12_s": screen["delta_vs_parked_T12_s"]["0.64"],
        "cycle_over_C_PERF_01_s": -worst_run["margin_to_6_s"],
        "cycle_nominal_dose_throughput_kg_h": worst_run["dose_throughput_kg_h"],
        "unit_assembly_mass_kg": screen["dimensions"]["assembly_mass_kg"],
        "assembly_packaging_budget_mm": screen["dimensions"]["packaging_screen_mm"],
        "remaining_to_C_ENV_01_mm": screen["dimensions"]["remaining_to_C_ENV_01_mm"],
    }
    write_json(ROOT / "metrics.json", output)


if __name__ == "__main__":
    main()

