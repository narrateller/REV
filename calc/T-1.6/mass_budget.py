"""Compute the T-1.6 hydraulic design screens and write reproducible results."""
import json
from math import fsum, pi
import sys

from check_circuit import CIRCUIT, INTERLOCKS, HERE, ROOT, evaluate, read_yaml
from design_checks import cover_and_tube, drain_screen, manifold_loss_screen, mass_measures
from frame_screen import frame_screen
from heat_balance import evaluate_heat
from manifolds import block_screen, passage_comparison
from round2_screens import screen

sys.path.insert(0, str(HERE / "reference"))
from cycle_screen import cycle_screen  # noqa: E402
from power_review import evaluate_power  # noqa: E402


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def mass_budget(data, prior, frame, manifold, round1_measures):
    revision = data["revision"]
    cooler_hardware_kg = revision["cooling"]["air_screen_and_mount_allowance_kg"]
    coolers_kg = revision["cooling"]["modules"] * data["catalogs"]["ASA0567"]["mass_kg"] + cooler_hardware_kg
    drain = revision["drain_ZUP"]
    drain_OD_mm = drain["ID_mm"] + 4
    drain_kg = pi * (drain_OD_mm**2 - drain["ID_mm"]**2) / 4 * drain["length_m"] * 1000 * 7850 / 1e9
    drain_kg += 0.5
    station = []
    for row in prior["mass"]["station_rows"]:
        old_kg = row["T15_kg"]
        new_kg = old_kg
        source = row["source"]
        if row["node"] == "Охладитель с вентилятором":
            new_kg = coolers_kg
            source = "asa ASA0567AA47 EU × 2; 8 kg for removable mats, branch instruments and mounts"
        if row["node"] == "monitored_unloader_and_adapter":
            new_kg += drain_kg
            source += "; separate 2 m steel Ø16/12 drain and fittings"
        round2_kg = new_kg
        if row["node"] == "float_common_cover_and_mounts":
            round2_kg += manifold["float_standard_covers_kg"]
            source = "Two standard LFA NG50 (RE 21010 p. 6); retain predecessor allowance for mounts"
        station.append({"node": row["node"], "T15_kg": old_kg, "round1_kg": new_kg,
                        "round2_kg": round2_kg, "source": source})

    station_round1_kg = fsum(row["round1_kg"] for row in station)
    station_round2_kg = fsum(row["round2_kg"] for row in station) + manifold["credited_net_diff_kg"]
    machine = []
    for row in prior["mass"]["machine_rows"]:
        old_kg = row["T15_kg"]
        round1_kg = old_kg
        round2_kg = old_kg
        source = row["source"]
        if row["node"] == "Гидростанция в сборе":
            round1_kg = station_round1_kg
            round2_kg = station_round2_kg
            source = "Station rows; manufacturer valve package reconciliation and no credit for common blocks"
        if row["node"] == "Силовая рама" and frame["cast_screen_pass"]:
            round2_kg = frame["cast_frame_kg"]
            source = "T-1.6 frame_screen.py: cast end traverse volumes, T-1.5 ties and support allowance"
        machine.append({"node": row["node"], "T15_kg": old_kg, "round1_kg": round1_kg,
                        "round2_kg": round2_kg, "source": source})

    round1_kg = fsum(row["round1_kg"] for row in machine)
    round2_kg = fsum(row["round2_kg"] for row in machine)
    numerical_options = ("plate_trim", "tank_as_base", "integrated_rear_cover",
                         "DB_to_cartridges", "TF_oil_relief_pair")
    round1_options_kg = round1_kg + fsum(round1_measures[key]["delta_kg"] for key in numerical_options)
    return {
        "station_rows": station, "machine_rows": machine, "station_round2_kg": station_round2_kg,
        "machine_T15_kg": prior["mass"]["machine_T15_column_kg"], "machine_round1_kg": round1_kg,
        "machine_round2_kg": round2_kg, "margin_to_4750_kg": 4750 - round2_kg, "limit_kg": 4750,
        "round1_conditional_kg": round1_options_kg,
        "round1_uncredited_options": round1_measures, "pass": round2_kg <= 4750,
    }


def main():
    data = read_yaml(HERE / "sources.yaml")
    project = data["project"]
    checks = read_yaml(ROOT / "ops/criteria/design_criteria.yaml")["criteria"]
    original = read_json(ROOT / project["upstream_cylinder_results"])
    prior = read_json(ROOT / "calc/T-1.5/results.json")
    cylinders = read_yaml(ROOT / "design/cylinders.t16.yaml")["cylinders"]
    main_cylinder = next(cylinder for cylinder in cylinders if cylinder["id"] == "CY-MAIN")
    circuit = read_yaml(CIRCUIT)
    interlocks = read_yaml(INTERLOCKS)
    comparison = screen(circuit, data, main_cylinder["cap_dead_L"])
    structural = cover_and_tube(main_cylinder, original["cylinders"]["main"]["static"],
                                checks["C-HYD-01"]["max_relief_bar"], circuit["elements"]["CYM"]["Q_L_min"],
                                checks["C-STR-01"]["min_safety_factor_yield"])
    drain = drain_screen(data["revision"]["drain_ZUP"], project["oil_density_kg_m3"])
    measures = mass_measures(data, circuit, main_cylinder, original["cylinders"]["main"]["static"], prior)
    frame = frame_screen(data, prior, checks, main_cylinder)
    prior_circuit = read_yaml(ROOT / "design/hydraulics/T-1.5_circuit.yaml")
    manifold = block_screen(circuit, prior_circuit, data, prior, checks)
    budget = mass_budget(data, prior, frame, manifold, measures)
    manifold_loss = manifold_loss_screen(circuit, data["revision"]["main_manifold"], project["oil_density_kg_m3"])
    cycle, old_trace, nominal_trace, adverse_trace = cycle_screen(data, original, comparison, interlocks, circuit)
    thermal = evaluate_heat(data, prior, old_trace, nominal_trace, adverse_trace, cycle, original)
    paths, trial_losses = passage_comparison(circuit, data, manifold_loss)
    power_options = evaluate_power(data, original, prior, thermal, cycle, (old_trace, nominal_trace, adverse_trace),
                                   interlocks, circuit, trial_losses, main_cylinder)
    manifold["main_path_loss_comparison"] = paths
    design = evaluate()
    cycle["T15_adverse_physical_s"] = prior["cycle"]["round2_adverse_envelope"]["with_T13_physical_allowance_s"]
    nominal, adverse = cycle["revision_nominal"], cycle["revision_adverse"]
    cooling = thermal["cooling"]
    acceptance = {
        "mass_pass": budget["pass"],
        "frame_1350_screen_pass": frame["mass_target_pass"],
        "cooling_pass": cooling["oil_to_air_capacity_pass"] and cooling["pump_size_pass"] and cooling["installed_pass"],
        "heat_target_pass": thermal["heat_target_pass"],
        "min_25_kW_capacity_pass": cooling["dirty_capacity_using_78_L_min_point_only_kW"] >= 25,
        "rms_29_pass": nominal["rms_shaft_kW"] <= 29,
        "main_motor_mean_and_peak_pass": nominal["average_shaft_kW"] <= 30 and nominal["peak_shaft_kW"] <= 40,
        "nominal_cycle_pass": nominal["with_T13_physical_allowance_s"] <= data["review_round_2"]["nominal_cycle_limit_s"],
        "adverse_cycle_6_s_pass": adverse["with_T13_physical_allowance_s"] <= 6.0,
        "pilot_hot_pass": nominal["pilot"]["hot_balance_pass"] and adverse["pilot"]["hot_balance_pass"],
        "circuit_pass": design["passed"], "ZUP_drain_pass": drain["pass"],
        "cylinder_static_and_suction_pass": structural["static_pass"] and structural["suction_pass"],
    }
    write_json(HERE / "results.json", {
        "task": "T-1.6", "review_round": 2, "acceptance": acceptance, "circuit": design, "cycle": cycle,
        "heat_balance": thermal, "main_cylinder": structural, "ZUP_drain": drain, "mass": budget,
        "main_manifold_loss_screen": manifold_loss, "manifold_bom": manifold,
        "frame_round2": frame, "power_round2_options": power_options,
        "inherited_emergency_dump": comparison["emergency_dump"],
        "inherited_float": comparison["float"],
    })
    write_json(ROOT / "metrics.json", {
        "task": "T-1.6", "review_round": 2, "acceptance": acceptance,
        "mass_machine_kg": budget["machine_round2_kg"],
        "mass_round1_kg": budget["machine_round1_kg"],
        "mass_margin_to_4750_kg": budget["margin_to_4750_kg"],
        "frame_budget_kg": next(row["round2_kg"] for row in budget["machine_rows"] if row["node"] == "Силовая рама"),
        "cast_frame_candidate_kg": frame["cast_frame_kg"],
        "cast_frame_static_factor": frame["cast_static_factor"],
        "cast_frame_fatigue_factor": frame["cast_fatigue_factor"],
        "frame_lateral_error_mm": frame["frame_lateral_error_mm"],
        "manifold_mass_credit_kg": manifold["credited_net_diff_kg"],
        "heat_load_kW": thermal["review_design_heat_kW"], "cooler_dirty_capacity_kW": cooling["dirty_capacity_kW"],
        "installed_kW": cooling["installed_total_kW"], "rms_shaft_kW": nominal["rms_shaft_kW"],
        "average_shaft_kW": nominal["average_shaft_kW"], "peak_shaft_kW": nominal["peak_shaft_kW"],
        "nominal_cycle_s": nominal["with_T13_physical_allowance_s"],
        "adverse_cycle_s": adverse["with_T13_physical_allowance_s"],
        "max_working_pressure_bar": max(nominal["peak_working_bar"], adverse["peak_working_bar"]),
        "pilot_hot_capacity_margin_L_per_cycle": min(nominal["pilot"]["capacity_margin_L_per_cycle"],
                                                      adverse["pilot"]["capacity_margin_L_per_cycle"]),
        "pilot_hot_minimum_bar": min(nominal["pilot"]["minimum_pilot_pressure_bar"],
                                     adverse["pilot"]["minimum_pilot_pressure_bar"]),
        "ZUP_backpressure_bar": drain["total_backpressure_bar"],
        "cylinder_static_yield_factor": structural["minimum_yield_factor"],
        "cylinder_suction_max_velocity_m_s": max(structural["suction_velocities_m_s"].values()),
        "mutations_rejected": design["mutations"]["rejected"],
    })
    print(json.dumps(acceptance, sort_keys=True))


if __name__ == "__main__":
    main()
