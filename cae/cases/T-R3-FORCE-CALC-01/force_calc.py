"""Quasistatic screening using R4 nominal design intent and DESIGN_BASIS r1."""
from collections import Counter
import importlib.util
from itertools import product
import json
from math import pi, sqrt
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import ZipFile

import yaml

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
TASK = "T-R3-FORCE-CALC-01"
R4 = "cad/source/force_geometry"
BASIS = "coordination/tasks/T-R2-DESIGN-BASIS-02"
ENVELOPE = "cae/cases/design_boundary_phase_load_envelope"
CATALOG = "baselines/operator-fork-20261118/state_catalog_index.json"
COTS = "drives/cots_catalog.yaml"
PARAMS = "params/r3_force_calc_01.json"
DRIVE_RESULT = "drives/r3_force_calc_01.json"
PREVIOUS_REPLAY = "cae/cases/T-R3-42-STATES-ENVELOPE-01/verify_output.py"

spec = importlib.util.spec_from_file_location("envelope_mechanics", ROOT / PREVIOUS_REPLAY)
mechanics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mechanics)
require = mechanics.require

ASSUMED = "CALCULATED_ASSUMED"
NO_EQUILIBRIUM = "NO_STATIC_EQUILIBRIUM"
FREE = "RELEASED"
OPEN = "B_OPEN_BENCH_FIXTURE"
SEAT = "B_CLOSED_STOP_SEAT"
LOCK = "B_CLOSED_LOCK_BACKED_STOP"


def read_json(path):
    return json.loads((ROOT / path).read_bytes())


def blocked(reason):
    return {"status": "BLOCKED_INPUTS", "value": None, "reason": reason}


def quantity(text, unit):
    number, actual_unit = text.split()
    require(actual_unit == unit, f"Expected {unit}: {text}")
    return float(number)


def interval(text, unit):
    numbers, actual_unit = text.split()
    require(actual_unit == unit, f"Expected {unit}: {text}")
    return [float(number) for number in numbers.split("-")]


def nominal_geometry(asset, manifest, cots):
    with ZipFile(ROOT / R4 / asset["path"]) as native:
        document = ElementTree.fromstring(native.read("Document.xml"))
    objects = {
        obj.attrib["name"]: {prop.attrib["name"]: prop[0].attrib
                            for prop in obj.findall("Properties/Property") if len(prop)}
        for obj in document.findall("ObjectData/Object")
    }

    def dimensions(name, *keys):
        return [float(objects[name][key]["value"]) for key in keys]

    def placement(name):
        return objects[name]["Placement"]

    def position(name):
        return [float(placement(name)[f"P{axis}"]) for axis in "xyz"]

    length, width, height = dimensions("ChamberEnvelope", "Length", "Width", "Height")
    _, chamber_y, chamber_z = position("ChamberEnvelope")
    _, drive_y, drive_z = position("CylinderBody")
    axes = {}
    for name in ("CylinderBody", "GuideLeft", "GuideRight"):
        rotation = [float(placement(name)[f"Q{i}"]) for i in range(4)]
        require(rotation == [0, 0, 0, 1], f"R4 orientation changed: {asset['path']} {name}")
        axes[name] = [0, 0, 1]
    bore, rod, guide_spacing = dimensions("ForcePath", "CylinderBore", "RodDiameter",
                                          "GuideSpacing")
    (radius,) = dimensions("CylinderBody", "Radius")
    (guide_radius, guide_length) = dimensions("GuideLeft", "Radius", "Height")
    require(2 * radius == bore == cots["bore_m"] and rod == cots["rod_m"],
            f"Nominal drive dimensions differ: {asset['path']}")
    require(guide_spacing == abs(position("GuideRight")[1] - position("GuideLeft")[1]),
            f"Guide spacing mismatch: {asset['path']}")
    has_rod = "PistonRod" in objects
    if has_rod:
        rod_radius, rod_height = dimensions("PistonRod", "Radius", "Height")
        require(2 * rod_radius == rod and rod_height == cots["stroke_m"],
                f"V1 rod candidate differs: {asset['path']}")
    carrier_yz = dimensions("Carrier", "Width", "Height")
    punch_xyz = dimensions("Punch", "Length", "Width", "Height")
    return {
        "source_fcstd": asset["path"],
        "cad_observations": {
            "length_unit": "mm",
            "chamber_xyz_mm": [length, width, height],
            "cylinder_bore_placeholder_mm": bore,
            "guide_length_mm": guide_length,
            "axes_xyz": axes,
            "punch_xyz_mm": punch_xyz,
            "rod_solid_present": has_rod,
            "stop_or_lock_solid_present": any(re.search("stop|lock", name, re.I)
                                              for name in objects),
            "q_to_DB_FRAME": blocked("Die and physical assembled kinematics are undefined."),
        },
        "nominal_screening": {
            "chamber_xyz_m": [length, width, height],
            "actuator_offset_yz_m": [drive_y - chamber_y - width / 2,
                                      drive_z - chamber_z - height / 2],
            "guide_spacing_transverse_m": guide_spacing,
            "guide_nominal_diameter_m": 2 * guide_radius,
            "guide_nominal_length_m": guide_length,
            "carrier_gross_section_yz_m": carrier_yz,
            "free_lengths_m": manifest["free_lengths"],
            "external_column_xy_m": dimensions("ColumnRearLeft", "Length", "Width"),
            "external_beam_xyz_m": dimensions("TopBeam", "Length", "Width", "Height"),
            "materials_named_by_R4": manifest["materials"],
            "fasteners_named_by_R4": manifest["fasteners"],
        },
    }


def cots_inputs():
    components = yaml.safe_load((ROOT / COTS).read_text(encoding="utf-8"))["components"]
    cylinder = components["hydraulic_cylinder"]
    unit = components["hydraulic_power_unit"]
    relief = components["pressure_relief_valve"]
    return {
        "bore_m": quantity(cylinder["bore_diameter"], "mm") / 1000,
        "rod_m": quantity(cylinder["rod_diameter"], "mm") / 1000,
        "stroke_m": quantity(cylinder["stroke"], "mm") / 1000,
        "pressure_limited_by_each_component_Pa": {
            name: quantity(component["max_pressure"], "bar") * 100000
            for name, component in (("cylinder", cylinder), ("power_unit", unit), ("relief", relief))
        },
        "flow_m3_s": [value / 60000 for value in interval(unit["flow_rate"], "L/min")],
        "relief_flow_limit_m3_s": quantity(relief["flow_capacity"], "L/min") / 60000,
        "nominal_motor_range_W": [value * 1000 for value in interval(unit["motor_power"], "kW")],
    }


def cylinder_model(cots):
    cap_area = pi * cots["bore_m"] ** 2 / 4
    annulus = cap_area - pi * cots["rod_m"] ** 2 / 4
    require(annulus > 0, "Cylinder annular area must be positive")
    limit = min(cots["pressure_limited_by_each_component_Pa"].values())
    flow = min(cots["flow_m3_s"][-1], cots["relief_flow_limit_m3_s"])
    return {
        "cap_area_m2": cap_area,
        "annulus_area_m2": annulus,
        "pressure_limit_Pa": limit,
        "screening_max_pump_flow_m3_s": flow,
        "max_extension_N": limit * cap_area,
        "max_retraction_N_abs": limit * annulus,
        "ideal_hydraulic_power_at_limit_for_catalog_flow_W": [
            limit * min(value, flow) for value in cots["flow_m3_s"]
        ],
    }


def phase_drive(case, sample, cylinder, basis, cots):
    force = sample["F_x_N"]
    area = cylinder["cap_area_m2"] if force >= 0 else cylinder["annulus_area_m2"]
    flow = cylinder["screening_max_pump_flow_m3_s"]
    pressure = abs(force) / area
    time_budget = basis["DB-CYCLE-TIME"]
    power = basis["DB-MAIN-POWER"]
    power_at_flow = pressure * flow
    excursion = max(case["pose_samples_q_m"]) - min(case["pose_samples_q_m"])
    if sample["sample"] == "ZERO" or case["phase"] == "jam_emergency":
        traversal = {"status": "NOT_APPLICABLE",
                     "reason": "ZERO is a diagnostic point. Jam positions are possible stall locations."}
    elif excursion == 0:
        traversal = {"status": "NOT_APPLICABLE",
                     "reason": "Fixed punch pose. Dwell, leakage and auxiliary actuation are unknown."}
    else:
        work = abs(force) * excursion
        candidate_power_ceiling = min(cots["nominal_motor_range_W"][-1],
                                      cylinder["pressure_limit_Pa"] * flow)
        traversal = {
            "status": ASSUMED,
            "constant_force_excursion_m": excursion,
            "ideal_hydraulic_volume_m3": area * excursion,
            "ideal_motion_time_at_max_catalog_flow_s": area * excursion / flow,
            "constant_force_work_J": work,
            "ideal_motion_power_if_full_cycle_available_W": work / time_budget,
            "ideal_motion_time_at_30kW_s": work / power,
            "hypothetical_minimum_time_at_candidate_hydraulic_power_ceiling_s":
                work / candidate_power_ceiling,
            "ratio_to_full_6s_reference_energy_at_30kW": work / (power * time_budget),
        }
    return {
        "sample": sample["sample"],
        "F_x_N": force,
        "ideal_active_port": ("CAP" if force > 0 else "ROD" if force < 0 else None),
        "ideal_required_pressure_Pa": pressure,
        "required_pressure_over_candidate_limit": pressure / cylinder["pressure_limit_Pa"],
        "force_comparison": ("EXCEEDS_IDEAL_LIMIT" if pressure > cylinder["pressure_limit_Pa"]
                             else "WITHIN_IDEAL_LIMIT"),
        "ideal_hydraulic_power_at_max_catalog_flow_W": power_at_flow,
        "flow_power_point": ("OUTSIDE_CANDIDATE_PRESSURE_RANGE"
                             if pressure > cylinder["pressure_limit_Pa"] else
                             "PRESSURE_BOUND_ONLY_PUMP_CURVE_UNAVAILABLE"),
        "stroke_if_direct_drive": ("EXCEEDS_CANDIDATE_STROKE"
                                   if max(case["pose_samples_q_m"]) > cots["stroke_m"] else
                                   "WITHIN_NOMINAL_STROKE"),
        "traversal_comparison": traversal,
    }


def connection_demands(path, force, guide_force, arm_moment):
    stop = None
    if path == OPEN:
        stop = {"stop_face_N": 0, "seat_path_N": 0, "lock_path_N": 0}
    if path in (SEAT, LOCK):
        stop = {"stop_face_N": force, "seat_path_N": force if path == SEAT else 0,
                "lock_path_N": force if path == LOCK else 0}
    return {
        "status": ASSUMED,
        "cylinder_mount_axial_N_on_frame": -force,
        "rod_and_carrier_transfer_axial_N_on_moving_group": force,
        "guide_station_resultant_N_each": guide_force,
        "guide_pair_reaction_moment_Nm_on_moving_group": [-value for value in arm_moment],
        "reaction_branch_axial_N_on_frame": force,
        "B_alternative_paths": stop,
    }


def held(q, sample, path, span, offset, geometry, cots, elastic):
    force = sample["F_x_N"]
    ay, az = geometry["actuator_offset_yz_m"]
    ey, ez = offset
    my, mz = force * (az - ez), force * (ey - ay)
    ry, rz = -mz / span, my / span
    moving = {
        "actuator": ([q, ay, az], [force, 0, 0]),
        "reaction": ([q, ey, ez], [-force, 0, 0]),
        "G-": ([q - span / 2, 0, 0], [0, -ry, -rz]),
        "G+": ([q + span / 2, 0, 0], [0, ry, rz]),
    }
    frame = {name: (point, [-value for value in vector])
             for name, (point, vector) in moving.items()}
    guide_force = sqrt(ry * ry + rz * rz)
    rod_area = pi * cots["rod_m"] ** 2 / 4
    rod_I = rod_area * cots["rod_m"] ** 2 / 16
    carrier_y, carrier_z = geometry["carrier_gross_section_yz_m"]
    carrier_area = carrier_y * carrier_z
    iy = carrier_area * carrier_z ** 2 / 12
    iz = carrier_area * carrier_y ** 2 / 12
    normal = -force
    carrier_corners = [
        [y, z, normal / carrier_area + my * z / iy - mz * y / iz]
        for y, z in product((-carrier_y / 2, carrier_y / 2), (-carrier_z / 2, carrier_z / 2))
    ]
    stability = {"status": "NOT_APPLICABLE", "reason": "AXIAL_TENSION"}
    if force > 0:
        lengths = geometry["free_lengths_m"]
        stability = {"status": ASSUMED, "modes": {
            element: {
                boundary: mechanics.euler(force, length, area, inertia, factor,
                                            elastic["young_modulus_Pa"],
                                            elastic["reference_yield_Pa"])
                for boundary, factor in elastic["K"].items()
            }
            for element, length, area, inertia in (
                ("rod", lengths["rod"], rod_area, rod_I),
                ("carrier_y", lengths["carrier"], carrier_area, iy),
                ("carrier_z", lengths["carrier"], carrier_area, iz),
            )
        }}
    _, width, height = geometry["chamber_xyz_m"]
    return {
        "status": ASSUMED, "sample": sample["sample"], "F_x_N": force, "q_m": q,
        "path": path, "guide_span_X_m": span, "reaction_offset_YZ_m": offset,
        "statics": {
            "applied_pair_moment_Nm": [0, my, mz],
            "moving_group_point_force_m_N": moving,
            "frame_point_force_m_N": frame,
            "moving_balance": mechanics.wrench(moving), "frame_balance": mechanics.wrench(frame),
            "guide_station_resultant_N": guide_force,
        },
        "section_4_strength": {
            "N_N": normal, "rod_axial_Pa": normal / rod_area,
            "carrier_gross_corner_Y_m_Z_m_sigma_Pa": carrier_corners,
            "punch_average_face_pressure_at_full_contact_Pa":
                force / (width * height) if force > 0 else None,
        },
        "section_5_stability": stability,
        "section_6_connection_demands": connection_demands(path, force, guide_force, [0, my, mz]),
    }


def case_result(case_id, case, settings, geometry, cots, elastic, phase_blocker):
    q_values = case["pose_samples_q_m"]
    if case["phase"] in {"return_full", "return_full_open"}:
        q_values = list(reversed(q_values))
    length, width, height = geometry["chamber_xyz_m"]
    spans = [length * factor for factor in settings["FC01-GUIDE-SPANS"]["value"]]
    fractions = settings["FC01-REACTION-OFFSETS"]["value"]
    offsets = list(product([width * x for x in fractions], [height * x for x in fractions]))
    samples = []
    for sample in case["axial_samples"]:
        force = sample["F_x_N"]
        if not force:
            samples.append({
                "sample": sample["sample"], "status": ASSUMED, "F_x_N": 0,
                "q_m": q_values[0], "path": FREE,
                "statics": {"axial_dof": "FREE", "guide_station_resultant_N": 0,
                            "moving_balance": {"force_N": [0, 0, 0], "moment_Nm": [0, 0, 0]},
                            "frame_balance": {"force_N": [0, 0, 0], "moment_Nm": [0, 0, 0]}},
                "section_4_strength": {"zero_load_control": True, "rod_axial_Pa": 0},
                "section_5_stability": {"status": "NOT_APPLICABLE", "reason": "ZERO_AXIAL_LOAD"},
                "section_6_connection_demands": {"zero_load_control": True},
            })
            continue
        for q in q_values:
            for path, span, offset in product(sample["held_axial_paths"], spans, offsets):
                samples.append(held(q, sample, path, span, offset, geometry, cots, elastic))
            samples.append({
                "sample": sample["sample"], "status": NO_EQUILIBRIUM, "path": FREE,
                "q_m": q, "F_x_N": force, "unbalanced_F_x_N": force,
                "statics": blocked("The released branch has no axial reaction."),
                "section_4_strength": {"status": "NOT_RUN", "value": None,
                                       "reason": NO_EQUILIBRIUM},
                "section_5_stability": {"status": "NOT_RUN", "value": None,
                                        "reason": NO_EQUILIBRIUM},
                "section_6_connection_demands": {"status": "NOT_RUN", "value": None,
                                                 "reason": NO_EQUILIBRIUM},
            })
    for sample in samples:
        sample["q_within_candidate_stroke"] = 0 <= sample["q_m"] <= cots["stroke_m"]
    require(sum(sample["sample"] == "ZERO" for sample in samples) == 1, f"{case_id}: ZERO count")
    return {
        "case_id": case_id, "variant": case["variant"], "phase": case["phase"],
        "scope": ASSUMED, "pose_samples_q_m": q_values, "r4_interface_ids": case["r4_interface_ids"],
        "physical_input_status": "BLOCKED_INPUTS", "physical_execution": "NOT_RUN",
        "physical": {
            "phase_load_and_BC": blocked(phase_blocker),
            "individual_foundation_reactions": blocked("Support layout, anchors and stiffness absent."),
            "section_4_strength": blocked("Actual sections, allowables, stresses and contacts unresolved."),
            "section_5_stability": blocked("Actual free lengths over q, end restraint and load path absent."),
            "section_6_connection_capacity": blocked(settings["FC01-PHYSICAL-JOINT-CAPACITY"]["reason"]),
        },
        "samples": samples,
    }


def force_validation(case_id, case, basis, settings):
    force_by_name = {
        "ZERO": basis["DB-ENVELOPE-V1"]["zero_N"],
        "RETURN": basis["DB-ENVELOPE-V1"]["return_N"],
        "WORK": basis["DB-ENVELOPE-V1"][f"{case['variant'][0]}_work_N"],
    }
    force_by_name["REVERSE_WORK"] = -force_by_name["WORK"]
    for sample in case["axial_samples"]:
        force = sample["F_x_N"]
        require(force == force_by_name[sample["sample"]], f"{case_id}: invalid load/sign")
        for path in sample["held_axial_paths"]:
            sign = settings["held_axial_paths"][path]["sign"]
            require(sign == "EITHER" or (sign == "COMPRESSION" and force > 0)
                    or (sign == "TENSION" and force < 0), f"{case_id}: invalid path/sign")


def extrema(cases):
    maxima = {}

    def record(metric, value, case, index, **details):
        if metric not in maxima or value > maxima[metric]["value"]:
            maxima[metric] = {"value": value, "case_id": case, "sample_index_0": index, **details}

    for case_id, case in cases.items():
        for index, row in enumerate(case["samples"]):
            if row["status"] != ASSUMED or row["path"] == FREE:
                continue
            stress = row["section_4_strength"]
            record("guide_reaction_N", row["statics"]["guide_station_resultant_N"], case_id, index)
            record("rod_abs_axial_stress_Pa", abs(stress["rod_axial_Pa"]), case_id, index)
            record("carrier_abs_gross_corner_stress_Pa",
                   max(abs(corner[2]) for corner in stress["carrier_gross_corner_Y_m_Z_m_sigma_Pa"]),
                   case_id, index)
            for element, comparisons in row["section_5_stability"].get("modes", {}).items():
                for end, mode in comparisons.items():
                    record("compression_over_euler", mode["load_over_P_cr"], case_id, index,
                           element=element, end_condition=end)
    return maxima


def cycle_checks(envelope, cots, cylinder, basis):
    travel = max(variant["relative_pose_m"]["forward_end"]
                 for variant in envelope["variants"].values())
    area_sum = cylinder["cap_area_m2"] + cylinder["annulus_area_m2"]
    time = basis["DB-CYCLE-TIME"]
    flow = cylinder["screening_max_pump_flow_m3_s"]
    power = basis["DB-MAIN-POWER"]
    return {
        "status": ASSUMED,
        "reference_cycle_s": time, "reference_main_motor_W": power,
        "reference_installed_W": basis["DB-INSTALLED-POWER"],
        "reference_max_shaft_energy_per_cycle_J": power * time,
        "ideal_full_return_plus_extension_catalog_stroke_s": area_sum * cots["stroke_m"] / flow,
        "ideal_full_return_plus_extension_at_v1_demand_s": area_sum * travel / flow,
        "ideal_flow_for_v1_round_trip_in_reference_time_m3_s": area_sum * travel / time,
        "v1_demand_travel_m": travel,
        "stroke_deficit_m": travel - cots["stroke_m"],
        "ideal_peak_travel_if_entire_reference_cycle_available_m_by_family": {
            family: power * time / basis["DB-ENVELOPE-V1"][f"{family}_work_N"] for family in "AB"
        },
        "ideal_extension_bore_for_work_at_DB_ref_pressure_m_by_family": {
            family: sqrt(4 * basis["DB-ENVELOPE-V1"][f"{family}_work_N"]
                         / (pi * basis["DB-HYD-REF"])) for family in "AB"
        },
        "actual_cycle": blocked("Missing F(q), motion/hold durations, opposing port pressures, pump "
                                "curve, simultaneous consumers, losses and control schedule."),
    }


def canonical(value):
    """Report at most 12 significant digits for identical cross-platform replay."""
    if isinstance(value, float):
        return 0.0 if value == 0 else float(format(value, ".12g"))
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [canonical(item) for item in value]
    return value


def build():
    r4 = read_json(f"{R4}/manifest.json")
    envelope = read_json(f"{ENVELOPE}/envelope.json")
    legacy = read_json(f"{ENVELOPE}/assumptions.json")
    db = read_json(f"{BASIS}/design_basis_registry.json")
    require(db["dataset_id"] == "REV_DESIGN_BASIS" and db["revision"] == 1, "Wrong load basis")
    basis = {key: entry["value"] for key, entry in db["parameters"].items()}
    settings = read_json(PARAMS)["parameters"]
    elastic = {**legacy["comparison_material"], "K": legacy["buckling_comparisons"]}
    cots = cots_inputs()
    cylinder = cylinder_model(cots)
    geometry = {
        variant: nominal_geometry(asset, r4["geometry_definition"], cots)
        for variant, asset in r4["variants"].items()
    }
    source_cases = read_json(CATALOG)["cases"]
    require(len(source_cases) == len(envelope["cases"]) == 42, "Expected 42 source cases")
    audited = {row["case_id"]: row for row in read_json(
        "cae/cases/T-R3-42-STATES-01/case_audit.json")["cases"]}
    cases, drive_phases = {}, {}
    for source in source_cases:
        case_id = source["case_id"]
        case = envelope["cases"][case_id]
        require(case_id not in cases and
                (case["variant"], case["phase"]) == (source["source_state"]["variant"],
                                                     source["source_state"]["state"]),
                f"{case_id}: catalog state mismatch")
        force_validation(case_id, case, basis, legacy)
        phase = audited[case_id]["phase_load"]
        require(phase["value"] is None, f"{case_id}: physical phase input audit changed")
        phase_reason = f"{phase['missing_input']} {phase['required']}"
        cases[case_id] = canonical(case_result(case_id, case, settings,
                                              geometry[case["variant"]]["nominal_screening"],
                                              cots, elastic, phase_reason))
        drive_phases[case_id] = {
            "phase": case["phase"], "variant": case["variant"], "status": ASSUMED,
            "samples": [phase_drive(case, sample, cylinder, basis, cots)
                        for sample in case["axial_samples"]],
        }
    summary = {
        "task_id": TASK, "scope": ASSUMED, "geometry": geometry, "case_count": len(cases),
        "sample_status_counts": dict(Counter(row["status"] for case in cases.values()
                                             for row in case["samples"])),
        "samples_outside_candidate_stroke": sum(not row["q_within_candidate_stroke"]
                                                for case in cases.values() for row in case["samples"]),
        "physical_case_count": 0, "physical_blocked_case_count": len(cases),
        "extrema": extrema(cases), "case_files": {key: f"results/{key}.json" for key in cases},
    }
    drives = {
        "task_id": TASK, "scope": ASSUMED, "source": COTS, "candidate_inputs": cots,
        "ideal_cylinder": cylinder, "cycle_comparison": cycle_checks(envelope, cots, cylinder, basis),
        "face_load_reference": {
            "DB_FACE_F_N": basis["DB-FACE-F"], "DB_FACE_P_Pa": basis["DB-FACE-P"],
            "DB_HYD_REF_Pa": basis["DB-HYD-REF"], "DB_HYD_BORE_IDEAL_m": basis["DB-HYD-BORE-IDEAL"],
        },
        "phase_comparisons": drive_phases,
        "vendor_selection": blocked("No exact order numbers, load charts, pump curve, duty limits, "
                                    "mounting ratings or component compatibility dossier."),
    }
    return cases, canonical(summary), canonical(drives)
