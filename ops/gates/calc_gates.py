"""Evaluate the REV pressure, dose and cycle gates from a machine parameter file."""

import argparse
import json
import math
from pathlib import Path
import sys

if __package__:
    from .gate_report import InputError, error_result, finite_number, load_yaml, read_criteria, result, write_report
else:
    from gate_report import InputError, error_result, finite_number, load_yaml, read_criteria, result, write_report


PARAMS_SCHEMA = Path(__file__).resolve().parents[2] / "design/params.schema.yaml"
CRITERIA_IDS = {
    "G-PFACE": ("C-PFACE-01", "C-PROD-01", "C-HYD-01"),
    "G-DOSE": ("C-DOSE-01", "C-RAW-01", "C-PERF-01"),
    "G-CYCLE": ("C-PERF-01", "C-PWR-01", "C-HYD-01", "C-PFACE-01"),
}
SWITCH_S = 0.1  # TASK T-0.2
TYPE_CHECKS = {
    "object": lambda value: isinstance(value, dict),
    "array": lambda value: isinstance(value, list),
    "number": finite_number,
    "integer": lambda value: type(value) is int and finite_number(value),
    "string": lambda value: isinstance(value, str),
    "boolean": lambda value: type(value) is bool,
    "null": lambda value: value is None,
}


def validate(value, rule, definitions, path="params"):
    """Apply the JSON Schema keywords used by params.schema.yaml."""
    if "$ref" in rule:
        validate(value, definitions[rule["$ref"].removeprefix("#/$defs/")], definitions, path)
    if "anyOf" in rule:
        for alternative in rule["anyOf"]:
            try:
                validate(value, alternative, definitions, path)
            except InputError:
                continue
            break
        else:
            raise InputError(f"{path}: expected a value matching one of {rule['anyOf']}")
    if "type" in rule:
        kinds = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
        if not any(TYPE_CHECKS[kind](value) for kind in kinds):
            raise InputError(f"{path}: expected {' or '.join(kinds)}")
    if "const" in rule and value != rule["const"]:
        raise InputError(f"{path}: expected {rule['const']!r}")
    if "enum" in rule and value not in rule["enum"]:
        raise InputError(f"{path}: expected one of {rule['enum']}")
    if isinstance(value, dict):
        properties = rule.get("properties", {})
        for key in rule.get("required", []):
            if key not in value:
                raise InputError(f"{path}.{key}: required field missing")
        for key, child in value.items():
            if key in properties:
                validate(child, properties[key], definitions, f"{path}.{key}")
            elif rule.get("additionalProperties") is False:
                raise InputError(f"{path}.{key}: unexpected field (check units in the field name)")
    if isinstance(value, list):
        if not rule.get("minItems", 0) <= len(value) <= rule.get("maxItems", math.inf):
            raise InputError(f"{path}: invalid number of entries")
        if "items" in rule:
            for index, child in enumerate(value):
                validate(child, rule["items"], definitions, f"{path}[{index}]")
    if isinstance(value, str) and len(value) < rule.get("minLength", 0):
        raise InputError(f"{path}: string is too short")
    if finite_number(value) and (
        value < rule.get("minimum", -math.inf)
        or value <= rule.get("exclusiveMinimum", -math.inf)
        or value > rule.get("maximum", math.inf)
    ):
        raise InputError(f"{path}: numeric value outside its schema bounds")


def actuators(params):
    cylinders = {"main_cylinder": params["main_cylinder"]}
    if params["precompaction"] is not None:
        cylinders["precompaction"] = params["precompaction"]["cylinder"]
    if "slide_gate_cylinder" in params["drive"]:
        cylinders["slide_gate"] = params["drive"]["slide_gate_cylinder"]
    return cylinders


def validate_params(params):
    schema = load_yaml(PARAMS_SCHEMA.read_bytes(), PARAMS_SCHEMA)
    validate(params, schema, schema["$defs"])
    for bounds in (params["raw"]["bulk_density_kg_m3"], params["product"]["length_range_mm"]):
        if bounds[0] > bounds[1]:
            raise InputError("Density and product length ranges must be ordered [min, max]")
    chamber = params["chamber"]
    if 2 * chamber["clearance_per_side_mm"] >= min(chamber["section_mm"]):
        raise InputError("chamber.clearance_per_side_mm leaves no positive punch section")
    cylinders = actuators(params)
    for name, cylinder in cylinders.items():
        if cylinder["rod_mm"] >= cylinder["bore_mm"]:
            raise InputError(f"{name}: rod_mm must be smaller than bore_mm")
        if cylinder.get("working_range_mm", cylinder["stroke_mm"]) > cylinder["stroke_mm"]:
            raise InputError(f"{name}: working_range_mm exceeds stroke_mm")
    precompaction = params["precompaction"]
    if precompaction is not None:
        if precompaction["stroke_mm"] > precompaction["cylinder"]["stroke_mm"]:
            raise InputError("precompaction.stroke_mm exceeds cylinder.stroke_mm")
        if precompaction["post_precompaction_density_kg_m3"] < params["raw"]["bulk_density_kg_m3"][1]:
            raise InputError("precompaction density must be at least the maximum bulk density")
    accumulator = params["drive"].get("accumulator")
    if accumulator and accumulator["min_delivery_pressure_bar"] > accumulator["charge_pressure_bar"]:
        raise InputError("accumulator.min_delivery_pressure_bar exceeds charge_pressure_bar")
    previous = None
    for index, phase in enumerate(params["cycle"]):
        path = f"cycle[{index}]"
        if phase["actuator"] not in cylinders:
            raise InputError(f"{path}: actuator is not configured")
        if ("force_N" in phase) == ("pressure_bar" in phase):
            raise InputError(f"{path}: specify exactly one of force_N and pressure_bar")
        if phase["regeneration"] and phase["direction"] != "extend":
            raise InputError(f"{path}: regeneration is supported for extension only")
        if phase.get("use_accumulator") and not accumulator:
            raise InputError(f"{path}: use_accumulator requires drive.accumulator")
        if not phase["stroke_mm"] and not phase["dwell_s"]:
            raise InputError(f"{path}: phase has no travel or dwell")
        if phase.get("continues") and (
            previous is None or previous["dwell_s"] or not previous["stroke_mm"] or not phase["stroke_mm"]
            or any(previous.get(key, False) != phase.get(key, False)
                   for key in ("actuator", "direction", "regeneration", "use_accumulator"))
        ):
            raise InputError(f"{path}.continues: expected uninterrupted travel in the same hydraulic configuration")
        previous = phase


def at_most(value, limit):
    return value <= limit or math.isclose(value, limit, rel_tol=1e-12, abs_tol=1e-12)


def piston_area_mm2(cylinder):
    return cylinder["n"] * math.pi / 4 * cylinder["bore_mm"] ** 2


def evaluate_pface(params, criteria):
    face, prod, hyd = (criteria[key] for key in CRITERIA_IDS["G-PFACE"])
    product_mm = params["product"]["section_mm"]
    chamber_mm = params["chamber"]["section_mm"]
    clearance_mm = params["chamber"]["clearance_per_side_mm"]
    punch_mm = [dimension - 2 * clearance_mm for dimension in chamber_mm]
    cylinder = params["main_cylinder"]
    chamber_area_mm2 = math.prod(chamber_mm)
    punch_area_mm2 = math.prod(punch_mm)
    nominal_force_N = cylinder["nominal_force_N"]
    effective_area_mm2 = piston_area_mm2(cylinder) * cylinder["eta"]
    force_N = 0.1 * cylinder["p_work_bar"] * effective_area_mm2
    relief_force_N = 0.1 * cylinder["p_relief_bar"] * effective_area_mm2
    pressure_MPa = nominal_force_N / chamber_area_mm2  # N / mm² = MPa
    target_mm, tol_mm = prod["value_mm"], prod["tol_mm"]

    def sections_match(left_mm, right_mm):
        return all(at_most(abs(a - b), tol_mm) for a, b in zip(left_mm, right_mm, strict=True))

    checks = {
        "product_section_matches_criterion": sections_match(product_mm, target_mm),
        "chamber_section_matches_criterion": sections_match(chamber_mm, target_mm),
        "chamber_section_matches_product": sections_match(chamber_mm, product_mm),
        "minimum_force_at_work_pressure": at_most(face["nominal_force_min_N"], force_N),
        "nominal_force_available": at_most(nominal_force_N, force_N),
        "minimum_face_pressure": at_most(face["min_MPa"], pressure_MPa),
        "working_pressure_limit": at_most(cylinder["p_work_bar"], hyd["max_working_bar"]),
        "relief_pressure_limit": at_most(cylinder["p_relief_bar"], hyd["max_relief_bar"]),
        "working_pressure_at_or_below_relief": at_most(cylinder["p_work_bar"], cylinder["p_relief_bar"]),
    }
    threshold = {
        "min_MPa": face["min_MPa"], "nominal_force_min_N": face["nominal_force_min_N"],
        "section_mm": target_mm, "tol_mm": tol_mm,
        "max_working_bar": hyd["max_working_bar"], "max_relief_bar": hyd["max_relief_bar"],
    }
    return result("G-PFACE", pressure_MPa, threshold, "MPa", CRITERIA_IDS["G-PFACE"], {
        "checks": checks, "chamber_pressure_MPa": pressure_MPa,
        "punch_pressure_MPa": nominal_force_N / punch_area_mm2,
        "chamber_pressure_at_p_relief_MPa": relief_force_N / chamber_area_mm2,
        "punch_pressure_at_p_relief_MPa": relief_force_N / punch_area_mm2,
        "nominal_force_N": nominal_force_N, "force_at_p_work_N": force_N,
        "force_at_p_relief_N": relief_force_N,
        "p_work_bar": cylinder["p_work_bar"], "p_relief_bar": cylinder["p_relief_bar"],
        "product_section_mm": product_mm, "chamber_section_mm": chamber_mm, "punch_section_mm": punch_mm,
        "chamber_area_mm2": chamber_area_mm2, "punch_area_mm2": punch_area_mm2,
    })


def evaluate_dose(params, criteria):
    """Required travel is approach + compression + ejection.

    The in-die briquette length cancels between compression and ejection.
    """
    dose_id, raw_id, perf_id = CRITERIA_IDS["G-DOSE"]
    raw, chamber, precomp = params["raw"], params["chamber"], params["precompaction"]
    cylinder = params["main_cylinder"]
    main_area_mm2 = math.prod(chamber["section_mm"])
    reference_density = criteria[raw_id]["bulk_density_kg_m3"]
    reference_dose_kg = criteria[perf_id]["briquette_kg"]
    overshoot_max = criteria[dose_id]["stroke_overshoot_max"]
    density_range = raw["bulk_density_kg_m3"]
    dose_kg = raw["dose_kg"]
    capacity_check_dose_kg = max(dose_kg, reference_dose_kg)
    bulk_densities = sorted(set(reference_density + density_range))
    intake = precomp if precomp is not None else chamber
    intake_length_mm = intake["loose_fill_length_mm"] if precomp is not None else intake["length_mm"]
    intake_volume_L = math.prod(intake["section_mm"]) * intake_length_mm / 1e6
    samples = []
    for density in bulk_densities:
        volume_L = 1000 * capacity_check_dose_kg / density
        samples.append({"density_kg_m3": density, "loose_volume_L": volume_L, "fits": at_most(volume_L, intake_volume_L)})
    fill_density_kg_m3 = precomp["post_precompaction_density_kg_m3"] if precomp else bulk_densities[0]
    fill_length_mm = (dose_kg / fill_density_kg_m3) * 1e9 / main_area_mm2
    approach_stroke_mm = chamber.get("approach_stroke_mm", 0)
    in_die_density_kg_m3 = chamber.get("in_die_density_kg_m3", params["product"]["density_kg_m3"])
    compacted_length_mm = (dose_kg / in_die_density_kg_m3) * 1e9 / main_area_mm2
    compression_stroke_mm = max(0, fill_length_mm - compacted_length_mm)
    if "ejection_overtravel_mm" in chamber:
        ejection_overtravel_mm = chamber["ejection_overtravel_mm"]
        ejection_source = "chamber.ejection_overtravel_mm"
    else:
        ejection_overtravel_mm = chamber["ejection_stroke_mm"] - compacted_length_mm
        if not at_most(0, ejection_overtravel_mm):
            raise InputError("chamber.ejection_stroke_mm is shorter than the in-die briquette")
        ejection_overtravel_mm = max(0, ejection_overtravel_mm)
        ejection_source = "chamber.ejection_stroke_mm minus compacted_length_mm"
    required_stroke_mm = approach_stroke_mm + fill_length_mm + ejection_overtravel_mm
    max_stroke_mm = overshoot_max * required_stroke_mm
    installed_stroke_mm = cylinder["stroke_mm"]
    working_range_mm = cylinder.get("working_range_mm", installed_stroke_mm)
    warnings = []
    if "approach_stroke_mm" not in chamber:
        warnings.append("подвод пуансона не задан (chamber.approach_stroke_mm), для оценки принят 0 мм")
    checks = {
        "precompaction_present": precomp is not None,
        "bulk_density_covers_reference": at_most(density_range[0], reference_density[0])
        and at_most(reference_density[1], density_range[1]),
        "minimum_dose": at_most(reference_dose_kg, dose_kg),
        "loose_dose_fits": all(sample["fits"] for sample in samples),
        "main_chamber_fits_transferred_dose": at_most(fill_length_mm, chamber["length_mm"]),
        "stroke_at_least_required": at_most(required_stroke_mm, installed_stroke_mm),
        "working_range_at_least_required": at_most(required_stroke_mm, working_range_mm),
        "stroke_overshoot_limit": at_most(installed_stroke_mm, max_stroke_mm),
    }
    status = "FAIL" if not all(checks.values()) else "WARN" if warnings else "PASS"
    return result("G-DOSE", installed_stroke_mm, {
        "min_stroke_mm": required_stroke_mm, "max_stroke_mm": max_stroke_mm,
        "stroke_overshoot_max": overshoot_max, "bulk_density_kg_m3": reference_density,
        "min_dose_kg": reference_dose_kg,
    }, "mm", CRITERIA_IDS["G-DOSE"], {
        "checks": checks, "warnings": warnings, "dose_kg": dose_kg, "capacity_check_dose_kg": capacity_check_dose_kg,
        "loose_dose_samples": samples,
        "intake_volume_L": intake_volume_L, "intake_chamber": "precompaction" if precomp else "main",
        "main_fill_density_kg_m3": fill_density_kg_m3, "main_fill_length_mm": fill_length_mm,
        "ejection_overtravel_mm": ejection_overtravel_mm, "ejection_overtravel_source": ejection_source,
        "ejection_stroke_mm": compacted_length_mm + ejection_overtravel_mm,
        "required_stroke_mm": required_stroke_mm,
        "stroke_ratio": installed_stroke_mm / required_stroke_mm, "working_range_mm": working_range_mm,
        "approach_stroke_mm": approach_stroke_mm,
        "approach_stroke_source": "chamber.approach_stroke_mm" if "approach_stroke_mm" in chamber else "zero_assumed",
        "in_die_density_kg_m3": in_die_density_kg_m3,
        "in_die_density_source": "chamber.in_die_density_kg_m3" if "in_die_density_kg_m3" in chamber
        else "product.density_kg_m3",
        "compacted_length_mm": compacted_length_mm, "compression_stroke_mm": compression_stroke_mm,
        "minimum_stroke_mm": required_stroke_mm, "minimum_stroke_ratio": installed_stroke_mm / required_stroke_mm,
    }, status=status)


def pump_flow_L_min(drive, pressure_bar):
    if pressure_bar == 0:
        return drive["pump_max_flow_L_min"]
    return min(drive["pump_max_flow_L_min"], 600 * drive["motor_kW"] * drive["eta"] / pressure_bar)


def pump_energy_kJ(oil_L, pressure_bar, eta):
    return oil_L * pressure_bar / (10 * eta)


def motion_area_mm2(cylinder, phase):
    piston_mm2 = piston_area_mm2(cylinder)
    rod_mm2 = cylinder["n"] * math.pi / 4 * cylinder["rod_mm"] ** 2
    if phase["regeneration"]:
        return rod_mm2  # Annular return feeds the piston side. Force and external flow use rod area.
    return piston_mm2 if phase["direction"] == "extend" else piston_mm2 - rod_mm2


def evaluate_phase(phase, cylinder, drive, available_oil_L):
    area_mm2 = motion_area_mm2(cylinder, phase)
    pressure_bar = phase.get("pressure_bar")
    if pressure_bar is None:
        pressure_bar = 10 * phase["force_N"] / (area_mm2 * cylinder["eta"])
    oil_L = area_mm2 * phase["stroke_mm"] / 1e6
    pump_limit_L_min = pump_flow_L_min(drive, pressure_bar)
    speed_mm_s = phase["speed_mm_s"]
    required_flow_L_min = None if speed_mm_s == "pump" else (60 * area_mm2 * speed_mm_s / 1e6 if oil_L else 0.0)
    target_flow_L_min = math.inf if required_flow_L_min is None else required_flow_L_min
    pump_rate_L_min = min(pump_limit_L_min, target_flow_L_min) if oil_L else 0.0
    accumulator = drive.get("accumulator")
    pressure_covered = not phase.get("use_accumulator") or at_most(
        pressure_bar, accumulator["min_delivery_pressure_bar"]
    )
    accumulator_limit_L_min = 0.0
    if oil_L and phase.get("use_accumulator") and pressure_covered and available_oil_L > 0:
        accumulator_limit_L_min = accumulator["max_flow_L_min"]
    boost_L_min = min(accumulator_limit_L_min, target_flow_L_min - pump_rate_L_min)

    available_flow_L_min = pump_limit_L_min + accumulator_limit_L_min
    required_pump_flow_L_min = pump_rate_L_min
    if required_flow_L_min is not None and oil_L:
        # Credit only the accumulator flow it can sustain over the requested stroke time.
        sustained_boost_L_min = min(accumulator_limit_L_min, available_oil_L * required_flow_L_min / oil_L)
        available_flow_L_min = pump_limit_L_min + sustained_boost_L_min
        required_pump_flow_L_min = required_flow_L_min - min(boost_L_min, sustained_boost_L_min)

    # For a finite discharge, the balance of the stroke uses pump flow alone.
    dispatch_fraction = boost_L_min / (pump_rate_L_min + boost_L_min) if boost_L_min else 0.0
    accumulator_oil_L = min(available_oil_L, oil_L * dispatch_fraction)
    pump_oil_L = oil_L - accumulator_oil_L
    motion_s = 60 * pump_oil_L / pump_rate_L_min if oil_L else 0.0
    return {
        "name": phase["name"], "actuator": phase["actuator"], "direction": phase["direction"],
        "regeneration": phase["regeneration"], "stroke_mm": phase["stroke_mm"], "area_mm2": area_mm2,
        "press": phase.get("press", False), "continues": phase.get("continues", False),
        "force_N": 0.1 * pressure_bar * area_mm2 * cylinder["eta"],
        "pressure_bar": pressure_bar, "oil_L": oil_L, "pump_limit_L_min": pump_limit_L_min,
        "required_flow_L_min": required_flow_L_min, "available_flow_L_min": available_flow_L_min,
        "required_pump_flow_L_min": required_pump_flow_L_min,
        "pump_rate_L_min": pump_rate_L_min, "accumulator_rate_L_min": boost_L_min,
        "pump_oil_L": pump_oil_L, "accumulator_oil_L": accumulator_oil_L,
        "motion_s": motion_s, "dwell_s": phase["dwell_s"], "time_s": motion_s + phase["dwell_s"],
        "motor_energy_kJ": pump_energy_kJ(pump_oil_L, pressure_bar, drive["eta"]),
        "requested_speed_met": required_flow_L_min is None or at_most(required_flow_L_min, available_flow_L_min),
        "accumulator_pressure_covered": pressure_covered,
    }


def recharge_phase(accumulator, drive, delivered_L):
    pressure_bar = accumulator["charge_pressure_bar"]
    pump_oil_L = delivered_L / accumulator["round_trip_eta"]
    flow_L_min = pump_flow_L_min(drive, pressure_bar)
    duration_s = 60 * pump_oil_L / flow_L_min
    return {
        "name": "Accumulator recharge", "actuator": "accumulator", "pressure_bar": pressure_bar,
        "oil_L": 0.0, "pump_limit_L_min": flow_L_min, "pump_rate_L_min": flow_L_min,
        "required_pump_flow_L_min": flow_L_min,
        "accumulator_rate_L_min": 0.0, "pump_oil_L": pump_oil_L, "accumulator_oil_L": 0.0,
        "motion_s": duration_s, "dwell_s": 0.0, "time_s": duration_s,
        "motor_energy_kJ": pump_energy_kJ(pump_oil_L, pressure_bar, drive["eta"]),
    }


def evaluate_cycle(params, criteria):
    perf, power, hyd, face = (criteria[key] for key in CRITERIA_IDS["G-CYCLE"])
    drive = params["drive"]
    cylinders = actuators(params)
    accumulator = drive.get("accumulator")
    available_oil_L = accumulator["usable_oil_L"] if accumulator else 0.0
    rows = []
    positions_mm = {name: [0.0] for name in cylinders}
    for phase in params["cycle"]:
        actuator = phase["actuator"]
        row = evaluate_phase(phase, cylinders[actuator], drive, available_oil_L)
        rows.append(row)
        available_oil_L -= row["accumulator_oil_L"]
        direction = 1 if phase["direction"] == "extend" else -1
        positions_mm[actuator].append(positions_mm[actuator][-1] + direction * phase["stroke_mm"])

    delivered_L = math.fsum(row["accumulator_oil_L"] for row in rows)
    if delivered_L > 0:
        rows.append(recharge_phase(accumulator, drive, delivered_L))
    for row in rows:
        row["switch_s"] = 0.0 if row.get("continues") else SWITCH_S
        total_flow_L_min = row["pump_rate_L_min"] + row["accumulator_rate_L_min"]
        pressure_bar = row["pressure_bar"]
        row["peak_drive_power_kW"] = pressure_bar * row["required_pump_flow_L_min"] / (600 * drive["eta"])
        row["peak_hydraulic_power_kW"] = pressure_bar * total_flow_L_min / (600 * drive["eta"])
    press_rows = [row for row in rows if row.get("press")]
    minimum_force_N = face["nominal_force_min_N"]
    for row in press_rows:
        row["press_configuration_valid"] = (
            row["actuator"] == "main_cylinder" and row["direction"] == "extend" and not row["regeneration"]
        )
        row["press_force_met"] = at_most(minimum_force_N, row["force_N"])
    travel_mm = {name: max(positions) - min(positions) for name, positions in positions_mm.items()}
    limits_mm = {name: cylinder.get("working_range_mm", cylinder["stroke_mm"])
                 for name, cylinder in cylinders.items()}
    if params["precompaction"] is not None:
        limits_mm["precompaction"] = params["precompaction"]["stroke_mm"]
    cycle_s = math.fsum(row["time_s"] + row["switch_s"] for row in rows)
    total_energy_kJ = math.fsum(row["motor_energy_kJ"] for row in rows)
    average_power_kW = total_energy_kJ / cycle_s
    peak_drive_power_kW = max(row["peak_drive_power_kW"] for row in rows)
    peak_hydraulic_power_kW = max(row["peak_hydraulic_power_kW"] for row in rows)
    installed_kW = drive.get("installed_kW")
    max_pressure_bar = max(row["pressure_bar"] for row in rows)
    if accumulator:
        max_pressure_bar = max(max_pressure_bar, accumulator["charge_pressure_bar"])
    checks = {
        "cycle_time_limit": at_most(cycle_s, perf["max_cycle_s"]),
        "average_power_limit": at_most(average_power_kW, power["max_main_kW"]),
        "peak_drive_power_limit": at_most(peak_drive_power_kW, power["max_main_kW"]),
        "motor_rating_limit": at_most(drive["motor_kW"], power["max_main_kW"]),
        "pump_power_within_motor_rating": at_most(peak_drive_power_kW, drive["motor_kW"]),
        "working_pressure_limit": at_most(max_pressure_bar, hyd["max_working_bar"]),
        "press_phase_present": bool(press_rows),
        "press_configuration_valid": all(row["press_configuration_valid"] for row in press_rows),
        "press_force_minimum": all(row["press_force_met"] for row in press_rows),
        "actuator_travel_limits": all(at_most(travel, limits_mm[name]) for name, travel in travel_mm.items()),
        "actuators_return_to_start": all(at_most(abs(positions[-1]), 0) for positions in positions_mm.values()),
        "requested_speeds_met": all(row.get("requested_speed_met", True) for row in rows),
        "accumulator_pressure_covered": all(row.get("accumulator_pressure_covered", True) for row in rows),
    }
    warnings = []
    if installed_kW is None:
        warnings.append("установленная мощность не задана")
    else:
        checks["installed_power_limit"] = at_most(installed_kW, power["max_installed_kW"])
    failures = [] if press_rows else ["нет фазы прессования"]
    status = "FAIL" if not all(checks.values()) else "WARN" if warnings else "PASS"
    details = {
        "checks": checks, "phases": rows, "cycle_s": cycle_s,
        "warnings": warnings, "failures": failures,
        "switch_count": sum(row["switch_s"] > 0 for row in rows),
        "switch_time_s": math.fsum(row["switch_s"] for row in rows),
        "total_oil_L": math.fsum(row["oil_L"] for row in rows),
        "total_pump_oil_L": math.fsum(row["pump_oil_L"] for row in rows),
        "total_motor_energy_kJ": total_energy_kJ, "average_power_kW": average_power_kW,
        "peak_hydraulic_power_kW": peak_hydraulic_power_kW, "peak_drive_power_kW": peak_drive_power_kW,
        "motor_kW": drive["motor_kW"], "installed_kW": installed_kW,
        "max_pressure_bar": max_pressure_bar, "actuator_travel_mm": travel_mm, "actuator_limits_mm": limits_mm,
    }
    main = params["main_cylinder"]
    if "working_range_mm" in main:
        piston_mm2 = piston_area_mm2(main)
        retract_mm2 = motion_area_mm2(main, {"direction": "retract", "regeneration": False})
        details["main_full_stroke_round_trip_oil_L"] = (piston_mm2 + retract_mm2) * main["stroke_mm"] / 1e6
    return result("G-CYCLE", cycle_s, {
        "max_cycle_s": perf["max_cycle_s"], "max_average_power_kW": power["max_main_kW"],
        "max_peak_drive_power_kW": power["max_main_kW"], "max_installed_kW": power["max_installed_kW"],
        "max_pressure_bar": hyd["max_working_bar"], "min_press_force_N": minimum_force_N,
    }, "s", CRITERIA_IDS["G-CYCLE"], details, status=status)


GATES = {"G-PFACE": evaluate_pface, "G-DOSE": evaluate_dose, "G-CYCLE": evaluate_cycle}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--params", required=True, type=Path)
    parser.add_argument("--criteria", required=True, type=Path)
    parser.add_argument("--gates", default=",".join(GATES), help="Comma-separated gate IDs")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    selected = [gate.strip() for gate in args.gates.split(",")]
    criteria_data, criteria_version = None, 0
    try:
        criteria_data = args.criteria.read_bytes()
        criteria = read_criteria(criteria_data)
        criteria_version = criteria["version"]
        if len(set(selected)) != len(selected) or set(selected) - GATES.keys():
            raise InputError(f"Invalid gate selection: {args.gates!r}")
        params = load_yaml(args.params.read_bytes(), args.params)
        validate_params(params)
    except (OSError, ValueError, ArithmeticError, RecursionError) as exc:
        results = [error_result(gate, CRITERIA_IDS.get(gate, ()), exc) for gate in selected]
    else:
        results = []
        for gate in selected:
            try:
                evaluation = GATES[gate](params, criteria["criteria"])
                json.dumps(evaluation, allow_nan=False)
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                evaluation = error_result(gate, CRITERIA_IDS[gate], exc)
            results.append(evaluation)
    try:
        return write_report(args.out, "calc_gates", args.params, criteria_version, criteria_data, results)
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
