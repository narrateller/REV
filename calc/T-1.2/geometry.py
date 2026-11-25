"""Offline D0 geometry and material calculations using the T-1.1 curve."""
from bisect import bisect_right
import json
from math import ceil, expm1, pi, prod, sqrt
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = ("base", "low", "high")  # T-1.1 labels bound pressure at fixed density.
WINDOW_LENGTHS_MM = (150, 200, 250)
DOSE_TOLERANCE_FRACTION = 0.05
DUMP_TIMES_S = (0.50, 0.64)



def read_yaml(name):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def interpolate(x, points):
    index = max(1, min(len(points) - 1, bisect_right(points, x, key=lambda point: point[0])))
    (x0, y0), (x1, y1) = points[index - 1:index + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def inverse_increasing(function, target, low, high):
    if not function(low) <= target <= function(high):
        raise ValueError(f"Target {target} lies outside the curve domain")
    for _ in range(50):
        mid = (low + high) / 2
        if function(mid) < target:
            low = mid
        else:
            high = mid
    return (low + high) / 2


class Material:
    def __init__(self, curve, reference_dose_kg, main_section_mm):
        self.curve = curve
        self.formula = curve["formula"]
        if curve["base_model"] != "power":
            raise ValueError("T-1.2 expects the adopted T-1.1 power fit")
        self.fit = curve["models"]["power"]
        self.reference_dose_kg = reference_dose_kg
        self.main_section_mm = main_section_mm
        self.envelope = {
            case: [(row["rho_immediate_equivalent_kg_m3"], row["p_face_MPa"]) for row in points]
            for case, points in curve["envelope"]["knots"].items()
        }

    def axial_ratio(self, case):
        return 1 + self.curve["springback"][case]

    def volume_ratio(self, case):
        return self.axial_ratio(case) * (1 + self.curve["transverse_area_growth"])

    def transfer(self, density_kg_m3, dose_kg, section_mm, wall_case):
        area_mm2 = prod(section_mm)
        length_mm = dose_kg * 1e9 / (area_mm2 * density_kg_m3)
        diameter_mm = 2 * area_mm2 / sum(section_mm)
        q = 4 * self.curve["K"][wall_case] * self.curve["mu"][wall_case] * length_mm / diameter_mm
        return -expm1(-q) / q

    def base_mean_MPa(self, density_kg_m3, bulk_kg_m3):
        onset = min(1, max(0, (density_kg_m3 - bulk_kg_m3) /
                           (self.formula["rho_join_kg_m3"] - bulk_kg_m3)))
        delta = max(0, density_kg_m3 - self.formula["rho_ref_kg_m3"])
        return self.fit["scale_MPa"] * (delta / 1000)**self.fit["exponent"] * onset * (2 - onset)

    def reference_transfer(self, density_kg_m3):
        return self.transfer(density_kg_m3, self.reference_dose_kg, self.main_section_mm,
                             self.curve["wall_values_used_for_curves"])

    def face_MPa(self, density_kg_m3, bulk_kg_m3, case, *, dose_kg=None, section_mm=None, wall_case=None):
        mean_MPa = self.base_mean_MPa(density_kg_m3, bulk_kg_m3)
        if case != "base":
            transfer = self.reference_transfer(density_kg_m3)
            points = self.envelope[case]
            external_kg_m3 = density_kg_m3 / self.volume_ratio(case)
            end_density_kg_m3, end_pressure_MPa = points[-1]
            if external_kg_m3 <= end_density_kg_m3:
                envelope_MPa = interpolate(external_kg_m3, points)
            else:
                end_loaded_kg_m3 = end_density_kg_m3 * self.volume_ratio(case)
                reference_bulk = self.curve["bulk_density_kg_m3"]["base"]
                envelope_MPa = (end_pressure_MPa + self.base_mean_MPa(density_kg_m3, reference_bulk) / transfer
                                - self.base_mean_MPa(end_loaded_kg_m3, reference_bulk)
                                / self.reference_transfer(end_loaded_kg_m3))
            choose = min if case == "low" else max
            mean_MPa = choose(mean_MPa, max(0, envelope_MPa) * transfer)
        return mean_MPa / self.transfer(
            density_kg_m3, dose_kg if dose_kg is not None else self.reference_dose_kg,
            section_mm or self.main_section_mm, wall_case or self.curve["wall_values_used_for_curves"])

    def loaded_density_kg_m3(self, face_MPa, bulk_kg_m3, case, **geometry):
        return inverse_increasing(lambda rho: self.face_MPa(rho, bulk_kg_m3, case, **geometry),
                                  face_MPa, bulk_kg_m3, self.curve["density_domain_kg_m3"][1])

    def stabilized_density_kg_m3(self, immediate_kg_m3):
        knots = [(p["rho_immediate"], p["rho_stabilized"]) for p in self.curve["stabilization_knots_kg_m3"]]
        early_end, stable_end = knots[-1]
        if immediate_kg_m3 > early_end:
            return immediate_kg_m3 - (early_end - stable_end)
        return interpolate(immediate_kg_m3, knots)


def briquette(material, criteria, pressure_basis, face_MPa, case, bulk_kg_m3):
    dose_kg = material.reference_dose_kg
    area_mm2 = prod(material.main_section_mm)
    density_kg_m3 = material.loaded_density_kg_m3(face_MPa, bulk_kg_m3, case)
    loaded_mm = dose_kg * 1e9 / (area_mm2 * density_kg_m3)
    springback_ratio = material.axial_ratio(case)
    released_mm = loaded_mm * springback_ratio
    released_kg_m3 = density_kg_m3 / material.volume_ratio(case)
    length_limits_mm = criteria["C-PROD-02"]["range_mm"]
    endpoints = []
    for target_mm in length_limits_mm:
        # At a specified released length the loaded length and Janssen factor are fixed.
        in_die_length_mm = target_mm / springback_ratio
        volume_m3 = in_die_length_mm * area_mm2 * 1e-9
        endpoint_density = inverse_increasing(
            lambda rho: material.face_MPa(rho, bulk_kg_m3, case, dose_kg=rho * volume_m3),
            face_MPa, bulk_kg_m3, material.curve["density_domain_kg_m3"][1])
        endpoints.append({"length_mm": target_mm, "dose_kg": endpoint_density * volume_m3,
                          "in_die_density_kg_m3": endpoint_density, "in_die_length_mm": in_die_length_mm,
                          "released_density_kg_m3": endpoint_density / material.volume_ratio(case)})

    return {"pressure_basis": pressure_basis, "face_MPa": face_MPa, "case": case,
            "bulk_density_kg_m3": bulk_kg_m3, "in_die_density_kg_m3": density_kg_m3,
            "in_die_length_mm": loaded_mm, "released_density_kg_m3": released_kg_m3,
            "released_length_mm": released_mm,
            "stabilized_density_kg_m3": material.stabilized_density_kg_m3(released_kg_m3),
            "C-PROD-02_nominal_dose_length_pass": length_limits_mm[0] <= released_mm <= length_limits_mm[1],
            "C-PROD-03_immediate_density_pass": released_kg_m3 >= criteria["C-PROD-03"]["min_kg_m3"],
            "dose_kg": dose_kg, "length_endpoints": endpoints}


def pre_load(material, section_mm, height_mm, case, bulk_kg_m3, mass_kg):
    area_mm2 = prod(section_mm)
    density_kg_m3 = mass_kg * 1e9 / (area_mm2 * height_mm)
    pressure_MPa = material.face_MPa(density_kg_m3, bulk_kg_m3, case, dose_kg=mass_kg,
                                     section_mm=section_mm, wall_case=case)
    return {"density_kg_m3": density_kg_m3, "face_MPa": pressure_MPa,
            "janssen_transfer": material.transfer(density_kg_m3, mass_kg, section_mm, case),
            "material_force_N": pressure_MPa * area_mm2}


def precompaction(material, params, criteria, section_mm, height_mm, bulk_densities, length_dose_kg, upper_kg):
    area_mm2 = prod(section_mm)
    dose_kg = material.reference_dose_kg
    freeboard_mm = 10  # X-1 freeboard, above the upper accepted dose.
    fill_height_mm = ceil(upper_kg * 1e9 / (area_mm2 * min(bulk_densities)) + freeboard_mm)
    stroke_mm = fill_height_mm - height_mm
    doses_kg = {"nominal": dose_kg, "length_110": length_dose_kg, "upper_dose": upper_kg}
    fills = []
    for bulk_kg_m3 in bulk_densities:
        row = {"bulk_density_kg_m3": bulk_kg_m3}
        for key, mass_kg in doses_kg.items():
            total_mm = mass_kg * 1e9 / (area_mm2 * bulk_kg_m3)
            row[key] = {"loose_volume_L": mass_kg * 1000 / bulk_kg_m3,
                        "height_from_channel_floor_mm": total_mm, "height_above_channel_mm": total_mm - height_mm,
                        "free_travel_to_material_mm": fill_height_mm - total_mm}
        fills.append(row)

    loads = [{"case": case, "bulk_density_kg_m3": bulk_kg_m3,
              **{key: pre_load(material, section_mm, height_mm, case, bulk_kg_m3, mass_kg)
                 for key, mass_kg in doses_kg.items()}}
             for case in CASES for bulk_kg_m3 in bulk_densities]
    guide_force_N = 5000  # X-1 guide resistance.
    eta = 0.92  # X-1 mechanical efficiency.
    rod_mm = params["precompaction"]["cylinder"]["rod_mm"]  # screening, subject to buckling check
    rod_area_mm2 = pi * rod_mm**2 / 4
    max_bar = criteria["C-HYD-01"]["max_working_bar"]

    def available_N(bore_mm):
        # X-1 inlet loss 4 bar and exhaust backpressure 3 bar.
        return 0.1 * eta * ((max_bar - 7) * pi * bore_mm**2 / 4 + 3 * rod_area_mm2)

    sizing = {}
    for case in CASES:
        material_N = max(row["upper_dose"]["material_force_N"] for row in loads if row["case"] == case)
        operating_N = material_N + guide_force_N
        required_N = max(70_000, 2 * operating_N)
        diameter_mm = sqrt((required_N / (0.1 * eta) - 3 * rod_area_mm2) / ((max_bar - 7) * pi / 4))
        sizing[case] = {"material_force_N": material_N, "operating_force_N": operating_N,
                        "required_cylinder_force_N": required_N, "minimum_bore_mm": diameter_mm}
    governing_case = max(sizing, key=lambda case: sizing[case]["required_cylinder_force_N"])
    governing = sizing[governing_case]
    bore_mm = ceil(governing["minimum_bore_mm"] / 5) * 5  # Preliminary bore rounded upward to 5 mm.
    volume_L = area_mm2 * height_mm / 1e6
    return {"window_mm_axial_transverse": section_mm, "fill_height_mm": fill_height_mm,
            "freeboard_mm": freeboard_mm, "stroke_mm": stroke_mm,
            "cylinder_stroke_mm": ceil((stroke_mm + 10) / 10) * 10,
            "post_precompaction_density_kg_m3": dose_kg * 1000 / volume_L,
            "post_precompaction_volume_L": volume_L, "loose_fill": fills,
            "force_cases": loads, "doses_kg": doses_kg, "sizing_by_case": sizing,
            "guide_force_N": guide_force_N, "governing_force_case": governing_case, **governing, "available_from_100_mm_bore_N": available_N(100),
            "bore_mm": bore_mm, "rod_mm": rod_mm, "cylinder_eta": eta,
            "available_from_proposed_bore_N": available_N(bore_mm)}


def dosing(pre, bulk_densities, cycle_limit_s):
    area_mm2 = prod(pre["window_mm_axial_transverse"])
    doses_kg = pre["doses_kg"]
    min_bulk_kg_m3 = min(bulk_densities)
    refill_s = cycle_limit_s - max(DUMP_TIMES_S)
    margin_fraction = 0.25  # Screw reserve for variable fill and cutoff/settling.
    mean_kg_s = doses_kg["nominal"] / cycle_limit_s
    screw_kg_s = doses_kg["upper_dose"] / refill_s * (1 + margin_fraction)
    flows = []
    for density_kg_m3 in bulk_densities:
        dumps = []
        for dump_s in DUMP_TIMES_S:
            rates_L_s = {key: mass_kg * 1000 / (density_kg_m3 * dump_s) for key, mass_kg in doses_kg.items()}
            rates_L_s["nominal_plus_tolerance"] = rates_L_s["nominal"] * (1 + DOSE_TOLERANCE_FRACTION)
            dumps.append({"dump_s": dump_s, "rates_L_s": rates_L_s,
                          "upper_dose_window_velocity_m_s": rates_L_s["upper_dose"] * 1000 / area_mm2})
        flows.append({"bulk_density_kg_m3": density_kg_m3, "mean_feed_L_s": mean_kg_s * 1000 / density_kg_m3,
                      "screw_design_rate_L_s": screw_kg_s * 1000 / density_kg_m3, "dump_rates": dumps})
    usable_volume_L = (pre["fill_height_mm"] - pre["freeboard_mm"]) * area_mm2 / 1e6
    buffer_min_L = doses_kg["upper_dose"] * 1000 / min_bulk_kg_m3
    return {"minimum_nominal_dump_capacity_L_s_at_90_kg_m3": 14.5,  # Task requirement.
            "dose_tolerance_fraction": DOSE_TOLERANCE_FRACTION,
            "usable_intake_volume_L": usable_volume_L,
            "min_bulk_density_for_upper_dose_kg_m3": doses_kg["upper_dose"] * 1000 / usable_volume_L,
            "buffer_min_usable_L_at_upper_dose": buffer_min_L, "buffer_proposed_usable_L": ceil(buffer_min_L),
            "refill_available_s": refill_s, "screw_design_rate_kg_s": screw_kg_s,
            "screw_design_rate_kg_h": screw_kg_s * 3600, "refill_upper_dose_at_design_rate_s": doses_kg["upper_dose"] / screw_kg_s,
            "mean_feed_kg_s": mean_kg_s, "mean_feed_kg_h": mean_kg_s * 3600, "flow_cases": flows}


def axial_layout(window_axial_mm, height_mm, overtravel_mm):
    home_mm = 0
    window_start_mm = 5  # Clearance from retracted punch face to aperture.
    gate_mm = window_start_mm + window_axial_mm
    guide_start_mm = -height_mm  # Provisional upstream guide extension, one channel height.
    eject_end_mm = gate_mm + overtravel_mm
    stop_reserve_mm = 15  # Provisional forward cushion/end allowance.
    return {"body_guide_start_x_mm": guide_start_mm, "punch_home_x_mm": home_mm,
            "window_start_x_mm": window_start_mm, "window_end_x_mm": gate_mm,
            "closed_gate_inner_face_x_mm": gate_mm, "punch_ejection_end_x_mm": eject_end_mm,
            "body_length_mm": gate_mm - guide_start_mm, "approach_stroke_mm": window_start_mm - home_mm,
            "transferred_fill_length_mm": window_axial_mm, "ejection_overtravel_mm": overtravel_mm,
            "main_required_travel_mm": eject_end_mm - home_mm, "main_stop_reserve_mm": stop_reserve_mm,
            "main_installed_stroke_mm": eject_end_mm - home_mm + stop_reserve_mm}


def packaging(pre, criteria):
    floor_elevation_mm = 650  # Provisional channel-floor elevation retained from round 1.
    fill_top_mm = floor_elevation_mm + pre["fill_height_mm"]
    # Direct coaxial cylinder, before its caps, shoe/rod fittings, supports and clearances.
    cylinder_top_lower_bound_mm = fill_top_mm + pre["cylinder_stroke_mm"]
    inlet = criteria["C-T-01"]
    inlet_min_mm = inlet["target_mm"] - inlet["tol_mm"]
    inlet_max_mm = inlet["target_mm"] + inlet["tol_mm"]
    envelope_top_mm = criteria["C-ENV-01"]["max_mm"][2]
    return {"channel_floor_elevation_mm": floor_elevation_mm, "fill_top_elevation_mm": fill_top_mm,
            "cylinder_top_lower_bound_elevation_mm": cylinder_top_lower_bound_mm,
            "inlet_min_elevation_mm": inlet_min_mm, "inlet_max_elevation_mm": inlet_max_mm,
            "rise_from_fill_top_to_nominal_inlet_mm": inlet["target_mm"] - fill_top_mm,
            "rise_from_fill_top_to_max_inlet_mm": inlet_max_mm - fill_top_mm,
            "space_above_cylinder_lower_bound_mm": envelope_top_mm - cylinder_top_lower_bound_mm}


def transverse_recovery(material, criteria):
    # Equal fractional recovery in both transverse dimensions is a screening assumption.
    linear_ratio = sqrt(1 + material.curve["transverse_area_growth"])
    target_mm = criteria["C-PROD-01"]["value_mm"]
    tolerance_mm = criteria["C-PROD-01"]["tol_mm"]
    released_mm = [dimension_mm * linear_ratio for dimension_mm in material.main_section_mm]
    max_area_mm2 = prod(target + tolerance_mm for target in target_mm)
    released_area_mm2 = prod(material.main_section_mm) * (1 + material.curve["transverse_area_growth"])
    return {"assumption": "equal fractional recovery in width and height",
            "area_growth_fraction": material.curve["transverse_area_growth"],
            "released_area_mm2": released_area_mm2, "max_area_within_tolerance_mm2": max_area_mm2,
            "area_within_tolerance_independent_of_recovery_split": released_area_mm2 <= max_area_mm2,
            "linear_growth_fraction": linear_ratio - 1,
            "released_section_mm": released_mm,
            "within_tolerance_by_dimension": [abs(actual - target) <= tolerance_mm
                                               for actual, target in zip(released_mm, target_mm, strict=True)],
            "section_for_center_of_tolerance_mm": [target / linear_ratio for target in target_mm],
            "section_intervals_for_tolerance_mm": [[(target - tolerance_mm) / linear_ratio,
                                                    (target + tolerance_mm) / linear_ratio] for target in target_mm]}


def length_endpoint_checks(material, row, pre, channel_height_mm):
    section_mm = pre["window_mm_axial_transverse"]
    area_mm2 = prod(section_mm)
    bulk_kg_m3 = row["bulk_density_kg_m3"]
    available_L = (pre["fill_height_mm"] - pre["freeboard_mm"]) * area_mm2 / 1e6
    checks = []
    for endpoint in row["length_endpoints"]:
        mass_kg = endpoint["dose_kg"]
        loose_volume_L = mass_kg * 1000 / bulk_kg_m3
        pre_force_N = pre_load(material, section_mm, channel_height_mm, row["case"], bulk_kg_m3,
                               mass_kg)["material_force_N"] + pre["guide_force_N"]
        checks.append({**endpoint, "loose_volume_L": loose_volume_L,
                       "loose_volume_fits_with_freeboard": loose_volume_L <= available_L,
                       "min_bulk_density_to_fit_with_freeboard_kg_m3": mass_kg * 1000 / available_L,
                       "loose_charge_fills_full_transfer_length": loose_volume_L >= pre["post_precompaction_volume_L"],
                       "pre_cylinder_force_N": pre_force_N,
                       "pre_force_reserve_ratio": pre["available_from_proposed_bore_N"] / pre_force_N})
    return checks


def calculate():
    from x1_calc import hydraulic_requirements, run_cases

    params = read_yaml("design/params.m1.yaml")
    criteria = read_yaml("ops/criteria/design_criteria.yaml")["criteria"]
    section_mm = params["chamber"]["section_mm"]
    width_mm, height_mm = section_mm
    dose_kg = params["raw"]["dose_kg"]
    bulk_densities = criteria["C-RAW-01"]["bulk_density_kg_m3"]
    curve = read_yaml("calc/T-1.1/curve.yaml")
    material = Material(curve, dose_kg, section_mm)
    pressures = (("criterion", criteria["C-PFACE-01"]["min_MPa"]),
                 ("nominal_force", params["main_cylinder"]["nominal_force_N"] / prod(section_mm)))
    briquettes = [briquette(material, criteria, basis, pressure_MPa, case, bulk_kg_m3)
                  for basis, pressure_MPa in pressures for case in CASES for bulk_kg_m3 in bulk_densities]
    base_rows = [row for row in briquettes if (row["pressure_basis"], row["case"]) == ("nominal_force", "base")]
    length_dose_kg = max(row["length_endpoints"][-1]["dose_kg"] for row in base_rows)
    base_upper_kg = length_dose_kg * (1 + DOSE_TOLERANCE_FRACTION)
    # Also fit the exact 110 mm dose at the edge of the material envelope.
    max_endpoint_kg = max(row["length_endpoints"][-1]["dose_kg"]
                          for row in briquettes if row["pressure_basis"] == "nominal_force")
    upper_kg = max(base_upper_kg, max_endpoint_kg)
    common = {"reference_dose_kg": dose_kg, "main_section_mm": section_mm}
    limit_s = criteria["C-PERF-01"]["max_cycle_s"]
    cases = []
    for length_mm in WINDOW_LENGTHS_MM:
        axis = axial_layout(length_mm, height_mm, params["chamber"]["ejection_overtravel_mm"])
        pre = precompaction(material, params, criteria, [length_mm, width_mm], height_mm,
                            bulk_densities, length_dose_kg, upper_kg)
        layout = {**common, "axis": axis, "precompaction": pre}
        cycle = run_cases(material, layout, briquettes, params, criteria)
        base_dump_s = {dump_s: max(run["cycle_s"] for run in cycle["runs"]
                                   if run["case"] == "base" and run["feed_s"] == dump_s)
                       for dump_s in DUMP_TIMES_S}
        cases.append({"window_axial_mm": length_mm, "axis": axis, "precompaction": pre,
                      "packaging": packaging(pre, criteria), "base_cycle_by_dump_s": base_dump_s,
                      "base_cycle_limit_pass": base_dump_s[max(DUMP_TIMES_S)] <= limit_s, "cycle": cycle})

    def selection_key(row):
        case = row["precompaction"]["sizing_by_case"]["base"]
        time_s = row["base_cycle_by_dump_s"][max(DUMP_TIMES_S)]
        return not row["base_cycle_limit_pass"], time_s, case["operating_force_N"]

    selected = min(cases, key=selection_key)
    axis = selected["axis"]
    pre = selected["precompaction"]
    rows = [{**row, "length_endpoint_checks": length_endpoint_checks(material, row, pre, height_mm),
             "press_end_x_mm": axis["closed_gate_inner_face_x_mm"] - row["in_die_length_mm"],
             "compression_stroke_mm": axis["transferred_fill_length_mm"] - row["in_die_length_mm"],
             "ejection_stroke_mm": row["in_die_length_mm"] + axis["ejection_overtravel_mm"]} for row in briquettes]
    comparison_loads = [pre_load(material, [length_mm, width_mm], height_mm, "base",
                                 curve["bulk_density_kg_m3"]["base"], dose_kg) for length_mm in (200, 150)]
    return material, {**common, "selection": {"window_axial_mm": selected["window_axial_mm"],
                                              "base_cycle_limit_s": limit_s,
                                              "base_cycle_limit_pass": selected["base_cycle_limit_pass"],
                                              "base_cycle_margin_s": limit_s - selected["base_cycle_by_dump_s"][max(DUMP_TIMES_S)]},
                      "length_110_base_upper_with_tolerance_kg": base_upper_kg,
                      "length_110_max_exact_dose_at_nominal_kg": max_endpoint_kg,
                      "window_comparison": cases, "briquettes": rows, "axis": axis, "precompaction": pre,
                      "packaging": selected["packaging"], "cycle": selected["cycle"],
                      "T-1.4_cycle_sensitivity": hydraulic_requirements(material, selected, common, base_rows, params, criteria),
                      "T-1.1_vs_round_1_pre_load": dict(zip((200, 150), comparison_loads, strict=True)),
                      "transverse_recovery": transverse_recovery(material, criteria),
                      "dosing": dosing(pre, bulk_densities, limit_s)}


def main():
    _, results = calculate()
    write_json(HERE / "results.json", results)


if __name__ == "__main__":
    main()
