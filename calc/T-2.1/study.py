"""Reproduce T-1.7d, compare three drives and generate the schema-v1 gate input."""
from argparse import ArgumentParser
from itertools import product
from math import floor, fsum, sqrt
from pathlib import Path
import json
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "cycle"))
sys.path.append(str(ROOT / "calc/T-1.6"))

from drive import bisect_power_corner_bar, source_data, write_json
from evaluate import configure
from heat import cooler, ledger
from make_params_t14b import gate_module, make_candidate
from pilot_control import pilot_replay
from pumps import A4VSO180Drive, pump_curve, vfd_replay
from round2_screens import pilot_cycle, screen
from station_mass import inventory
from x1_calc import motions, periodic_run


CANDIDATES = ("PV180_FDV", "A4VSO180_DFE1Z", "PV180_FDV_VFD")
FEED_S = .64
STEPS_S = (.0025, .00125, .000625)
FINE_DELTA_S = .015


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class Study:
    def __init__(self):
        self.sources = load_yaml(HERE / "sources.yaml")
        self.sources16 = load_yaml(ROOT / "calc/T-1.6/sources.yaml")
        self.design16 = load_json(ROOT / "calc/T-1.6/results.json")
        self.trial = load_json(ROOT / "calc/T-1.7d/results.json")["working_trial"]
        self.circuit = load_yaml(ROOT / "design/hydraulics/T-1.6_circuit.yaml")
        self.interlocks = load_yaml(ROOT / "design/hydraulics/T-1.6_interlocks.yaml")
        self.cylinders16 = load_yaml(ROOT / "design/cylinders.t16.yaml")
        self.cylinders17 = load_yaml(ROOT / "design/cylinders.t17d.yaml")
        self.pilot = screen(self.circuit, self.sources16, .8)["pilot"]
        self.sources16["inherited_worst_duty_allowance_kW"] = (
            self.design16["heat_balance"]["T16_nominal_sources_kW"]["inherited_worst_duty_allowance"])
        self.gate = gate_module()
        self.criteria = self.gate.read_criteria((ROOT / "ops/criteria/design_criteria.yaml").read_bytes())["criteria"]
        self.reference_sources = source_data()
        self.installed = self.design16["heat_balance"]["cooling"]["installed_breakdown_kW"] | {
            "independent_pilot_motor": 0.0,
        }
        self.limit_kW = self.sources["engineering"]["nominal_shaft_limit_kW"]

    def configuration(self, candidate, profile, case, bulk_kg_m3, residual_N, *, include_tandem=True):
        trial = self.trial
        inputs, cfg = configure(
            trial["geometry"], trial["moving_mass_kg"], gate_bore_mm=trial["gate_bore_mm"],
            rapid_mass_increment_kg=trial["rapid_mass_increment_kg"], profile=profile,
            residual_product_N=residual_N, peak_kW=self.limit_kW, case=case, bulk_kg_m3=bulk_kg_m3,
            **trial["cycle_settings"])
        model, cylinder, settings, projection, charge = cfg
        pump = settings["pump"]
        if candidate == "A4VSO180_DFE1Z":
            main_limit_kW = self.sources["engineering"]["dfe1z_main_shaft_limit_kW"]
            pump = A4VSO180Drive(self.sources, main_limit_kW, profile)
        pump.pilot_standby_kW = self.pilot["standby_shaft_bound_kW"] if include_tandem else 0.
        pump.loss_kW += pump.pilot_standby_kW
        pump.record_power_steps = include_tandem
        max_L_min = pump.capacity_L_min(pump.standby_bar)
        if candidate == "A4VSO180_DFE1Z":
            max_L_min = min(max_L_min, self.circuit["elements"]["P1"]["Q_L_min"])
        settings.update(pump=pump, max_L_min=max_L_min)
        return inputs, (model, cylinder, settings, projection, charge)

    def verified_reference(self):
        cycles = {}
        for profile in ("realistic", "pessimistic"):
            inputs, cfg = self.configuration("PV180_FDV", profile, "base", 90, 100_000,
                                             include_tandem=False)
            model, cylinder, settings, _, _ = cfg
            run = periodic_run(model, cylinder, 90, FEED_S, settings, STEPS_S[-1])
            previous_s = self.trial["cycle"][profile]["cycle_s"]
            assert abs(run["cycle_s"] - previous_s) < 1e-9, (profile, run["cycle_s"], previous_s)
            cycles[profile] = run["cycle_s"]
        candidate = make_candidate(inputs, self.configuration("PV180_FDV", "realistic", "base", 90, 100_000,
                                                               include_tandem=False)[1])
        gate = self.gate.evaluate_cycle(candidate, self.criteria)
        assert abs(gate["value"] - self.trial["cycle"]["gate_cycle_s"]) < 1e-9
        return dict(**cycles, gate_s=gate["value"], gate_rms_kW=gate["details"]["rms_power_kW"])

    def installed_for(self, candidate):
        if candidate == "A4VSO180_DFE1Z":
            return self.installed | {"dfe1z_pump_regulator": self.sources["catalogs"]["dfe1z"]["electronics_power_supply_kW"]}
        return self.installed

    def gate_for(self, candidate):
        inputs, cfg = self.configuration(candidate, "realistic", "base", 90, 100_000)
        model, cylinder, settings, projection, charge = cfg
        pump = settings["pump"]
        if candidate == "A4VSO180_DFE1Z":
            press = motions(model, cylinder, 90, settings["prefill"])["press"]
            top_bar = press.pressure_bar(press.stroke_m)
            corner_bar = bisect_power_corner_bar(pump, top_bar)
            points = [corner_bar + i * (top_bar - corner_bar) / 1000 for i in range(1001)]
            eta = min(bar * pump.capacity_L_min(bar) / (600 * self.limit_kW) for bar in points)
            projection["eta"] = floor(eta * 1000) / 1000
        # PV180 retains the accepted D1 conservative eta. The speed strategy
        # restores 1480 rpm before any charge or movement. G-CYCLE uses the
        # higher 1480-rpm idle term throughout.
        projection.update(idle_kW=pump.operating_point(pump.standby_bar, 0)[1],
                          peak_kW=self.limit_kW, installed_kW=fsum(self.installed_for(candidate).values()),
                          pump_max_flow_L_min=settings["max_L_min"])
        params = make_candidate(inputs, (model, cylinder, settings, projection, charge))
        params["description"] = (f"T-2.1 {candidate}. D-GK-05 / base 90 kg/m3 / 0.83 kg / feed 0.64 s. "
                                 "Equivalent rod and strokes for G-CYCLE; physical dimensions in cylinders.t17d.")
        assert all(not row.get("group") for row in params["cycle"] if row.get("press") or row["actuator"] == "none")
        checked = self.gate.evaluate_cycle(params, self.criteria)
        return params, checked

    def run(self, candidate, case, bulk_kg_m3, profile, residual_N):
        _, cfg = self.configuration(candidate, profile, case, bulk_kg_m3, residual_N)
        model, cylinder, settings, _, _ = cfg
        pump = settings["pump"]
        # Match T-1.7d time, with the extra T-1.6 handover also shown as a bound.
        handover_s = max(0., self.interlocks["switching_windows"]["handover_regen_press"][
            "modeled_switch_budget_s"] - settings["switch_s"])
        steps_s = list(STEPS_S)
        runs = [periodic_run(model, cylinder, bulk_kg_m3, FEED_S, settings, dt_s) for dt_s in steps_s]
        while (all(run["feasible"] for run in runs)
               and abs(runs[-1]["cycle_s"] - runs[-2]["cycle_s"]) > FINE_DELTA_S
               and len(runs) < 6):
            steps_s.append(steps_s[-1] / 2)
            runs.append(periodic_run(model, cylinder, bulk_kg_m3, FEED_S, settings, steps_s[-1]))
        run = runs[-1]
        label = dict(case=case, bulk_kg_m3=bulk_kg_m3, profile=profile, residual_N=residual_N)
        if not run["feasible"]:
            return label | run
        assert all(item["feasible"] for item in runs), label
        assert abs(run["net_lp_oil_balance_L"]) < 1e-5
        assert run["peak_working_bar"] <= 300 + 1e-8
        assert run["peak_shaft_kW"] <= pump.limit_kW + 1e-7
        assert model.main_travel_m * 1000 <= self.trial["geometry"]["punch_face_maximum_eject_end_x_mm"] + 1e-7
        assert (model.pre_travel_m + model.cam_m) * 1000 <= 380 + 1e-7
        commands = {item["command"]: item["time_s"] for item in run["switches"]}
        events = run["motion_events"]
        assert commands["eject"] >= events["gate_open"]["end_s"] - 1e-9
        assert commands["return"] >= events["eject"]["end_s"] - 1e-9
        assert commands["gate_close"] >= events["return"]["gate_clear_s"] - 1e-9
        assert run["stage_events"]["feed"][0] >= max(events[k]["end_s"] for k in ("return", "gate_close", "pre_up"))
        assert commands["unload"] >= commands["hold"] + settings["hold_s"] - 1e-9
        assert commands["gate_open"] >= commands["unload"] + settings["unload_s"] - 1e-9

        run["pilot_available_intervals_s"] = {}
        multiplier = (1 + pump.tolerance) * self.reference_sources["engineering_inputs"][
            "regulator_speed_ceiling_rpm"] / pump.rpm
        run["shaft_peak_with_tolerance_kW"] = run["peak_shaft_kW"] * multiplier
        pilot_demand = pilot_cycle(self.circuit, self.interlocks, self.sources16, run, self.pilot, settings["switch_s"])
        pilot_cfg = self.sources16["revision"]["pilot"].copy()
        extra_pilot_L = (self.sources["engineering"]["dfe1z_extra_pilot_L_per_cycle"]
                         if candidate == "A4VSO180_DFE1Z" else 0.)
        pilot_cfg["actuation_and_aux_bound_L_per_cycle"] += extra_pilot_L
        # T-1.6 pilot replay consumes the first seven columns of the trace.
        stripped = run | {"power_steps": [step[:7] for step in run["power_steps"]]}
        pilot = pilot_replay(stripped, self.pilot, pilot_demand, pilot_cfg, handover_s, self.limit_kW)
        run["pilot_loads_kW"] = stripped["pilot_loads_kW"]
        vfd = vfd_replay(run, self.sources, multiplier) if candidate == "PV180_FDV_VFD" else None
        heat = ledger(run, model, cylinder, settings, pilot, self.sources16, handover_s, self.limit_kW, vfd)
        duration_s = heat["duration_s"]
        average_kW, rms_kW, peak_kW = (pilot[f"{kind}_shaft_kW"] for kind in ("average", "rms", "peak"))
        if vfd:
            average_kW += multiplier * vfd["shaft_energy_delta_kJ"] / duration_s
            rms_kW = sqrt(rms_kW**2 + multiplier**2 * vfd["shaft_square_delta_kW2_s"] / duration_s)
            peak_kW = max(peak_kW, multiplier * vfd["max_reacceleration_shaft_kW"])
        sensitivity = None
        if candidate == "A4VSO180_DFE1Z":
            extra_L = self.sources["engineering"]["dfe1z_spare_pilot_sensitivity_L_per_cycle"]
            sensitivity_config = pilot_cfg | {
                "actuation_and_aux_bound_L_per_cycle": pilot_cfg["actuation_and_aux_bound_L_per_cycle"] + extra_L}
            sensitivity = dict(extra_L_per_cycle=extra_L, **pilot_replay(
                stripped, self.pilot, pilot_demand, sensitivity_config, handover_s, self.limit_kW))
        follow_s = [item["cycle_s"] for item in runs]
        final_delta_s = abs(follow_s[-1] - follow_s[-2])
        summary = dict(
            **label, feasible=True, cycle_s=run["cycle_s"], cycle_with_T16_handover_s=duration_s,
            unmodeled_handover_allowance_s=handover_s,
            average_shaft_kW=average_kW, rms_shaft_kW=rms_kW, peak_shaft_kW=peak_kW,
            average_shaft_before_tolerance_kW=average_kW / multiplier,
            rms_shaft_before_tolerance_kW=rms_kW / multiplier,
            peak_shaft_before_tolerance_kW=peak_kW / multiplier,
            peak_working_bar=run["peak_working_bar"], pump_oil_L=run["pump_oil_L"],
            peak_pump_flow_L_min=run["peak_pump_flow_L_min"], max_flow_L_min=settings["max_L_min"],
            oil_heat_kW=heat["oil_heat_kW"], pilot=pilot, extra_pilot_budget_L_cycle=extra_pilot_L,
            pilot_sensitivity=sensitivity, vfd=vfd, convergence=list(zip(steps_s, follow_s)),
            final_step_delta_s=final_delta_s, convergence_pass=final_delta_s <= FINE_DELTA_S,
            stage_events=run["stage_events"], motion_events=events, heat=heat,
            net_lp_oil_balance_L=run["net_lp_oil_balance_L"], boosted_L=run["boost_L"],
            guard_block_s=run["guard_block_s"], periodic_period_cycles=run["periodic_period_cycles"],
            loaded_density_kg_m3=run["loaded_density_kg_m3"], loaded_stroke_mm=1000 * model.die_length_m,
            main_travel_mm=run["main_travel_mm"], shoe_parking_travel_mm=run["shoe_parking_travel_mm"])
        print(candidate, case, bulk_kg_m3, profile, residual_N, f"{duration_s:.3f} s",
              f"{rms_kW:.2f} kW RMS, {heat['oil_heat_kW']:.2f} kW heat",
              f"pilot {'PASS' if pilot['hot_balance_pass'] else 'FAIL'}", flush=True)
        return summary

    def rexroth_catalogue_sensitivity(self):
        engineering = self.sources["engineering"]["rexroth_curve_read_off_sensitivity"]
        catalogue = self.sources["catalogs"]["rexroth"]
        nominal = catalogue["curve_bar_L_min_kW_kW"]
        delta_flow_L_min = engineering["flow_reduction_L_min"]
        delta_power_kW = engineering["shaft_increase_kW"]
        catalogue["curve_bar_L_min_kW_kW"] = [
            [pressure_bar, flow_L_min - delta_flow_L_min, full_kW + delta_power_kW, zero_kW + delta_power_kW]
            for pressure_bar, flow_L_min, full_kW, zero_kW in nominal
        ]
        try:
            name = "A4VSO180_DFE1Z"
            _, gate = self.gate_for(name)
            cases = [self.run(name, case, density, profile, 100_000) for case, density, profile in (
                ("base", 90, "realistic"), ("base", 90, "pessimistic"), ("base", 160, "realistic"))]
        finally:
            catalogue["curve_bar_L_min_kW_kW"] = nominal
        keys = ("case", "bulk_kg_m3", "profile", "cycle_with_T16_handover_s", "rms_shaft_kW",
                "peak_shaft_kW", "oil_heat_kW")
        return dict(**engineering, gate_cycle_s=gate["value"], gate_status=gate["status"],
                    cases=[{key: row[key] for key in keys} | {
                        "pilot_capacity_margin_L_per_cycle": row["pilot"]["capacity_margin_L_per_cycle"],
                        "pilot_balance_pass": row["pilot"]["hot_balance_pass"]} for row in cases])

    def summarize(self, candidate, cases, checked, params):
        nominal = next(row for row in cases if (row["case"], row["bulk_kg_m3"], row["profile"], row["residual_N"])
                       == ("base", 90, "realistic", 100_000))
        viable = [row for row in cases if row["feasible"]]
        worst_heat_kW = max(row["oil_heat_kW"] for row in viable)
        installed = self.installed_for(candidate)
        cooling = cooler(self.sources16, self.sources, worst_heat_kW, fsum(installed.values()))
        power = {
            "average_shaft_kW": max(row["average_shaft_kW"] for row in viable),
            "rms_shaft_kW": max(row["rms_shaft_kW"] for row in viable),
            "peak_shaft_kW": max(row["peak_shaft_kW"] for row in viable),
        }
        _, (_, _, settings, _, _) = self.configuration(candidate, "realistic", "base", 90, 100_000)
        catalogs = self.sources["catalogs"]
        engineering = self.sources["engineering"]
        pump_kg = (catalogs["rexroth"]["basic_mass_kg"] if candidate == "A4VSO180_DFE1Z"
                   else self.reference_sources["catalogs"]["parker_pvplus"]["models"]["PV180"]["mass_kg"])
        extra_kg = {
            "PV180_FDV": 0.,
            "A4VSO180_DFE1Z": engineering["dfe1z_adapter_and_regulator_allowance_kg"],
            "PV180_FDV_VFD": catalogs["vfd"]["mass_kg"] + engineering["vfd"]["cabinet_and_braking_allowance_kg"],
        }[candidate]
        station = inventory(
            self.sources16, self.design16, self.cylinders17, self.cylinders16, self.pilot, nominal,
            params["drive"]["pump_max_flow_L_min"], cooling["total_flow_L_min"], catalogs["motor"]["mass_kg"],
            pump_kg, extra_kg)
        pessimistic100 = [row for row in viable if row["profile"] == "pessimistic" and row["residual_N"] == 100_000]
        realistic100 = [row for row in viable if row["profile"] == "realistic" and row["residual_N"] == 100_000]
        max_real_s = max(row["cycle_with_T16_handover_s"] for row in realistic100)
        max_pess_s = max(row["cycle_with_T16_handover_s"] for row in pessimistic100)
        gate_rows = checked["details"]["phases"]
        gate_marks = [0.]
        for phase in ("prefill 1", "closed ports oil compression", "press 1", "hold", "unload", "gate_open 1", "eject 1", "feed"):
            gate_marks.append(next(row["group_start_s"] for row in gate_rows if row["name"] == phase))
        gate_marks.append(checked["value"])
        ref_marks = [nominal["stage_events"][phase][0] for phase in
                     ("pre_down", "prefill", "regen", "press", "hold", "unload", "gate_open",
                      "eject+return+gate_close+pre_up", "feed")] + [nominal["cycle_s"]]
        phase_delta_s = dict(zip(
            ("pre_down", "prefill", "regen", "press", "hold", "unload", "gate_open", "tail", "feed"),
            ((g1 - g0) - (r1 - r0) for g0, g1, r0, r1 in zip(gate_marks, gate_marks[1:], ref_marks, ref_marks[1:]))))
        assert abs(fsum(phase_delta_s.values()) - (checked["value"] - nominal["cycle_s"])) < 1e-9
        qualification = dict(
            all_scenarios_feasible=len(viable) == len(cases),
            all_steps_converged=all(row["convergence_pass"] for row in viable),
            pilot_balance=all(row["pilot"]["hot_balance_pass"] for row in viable),
            pilot_sensitivity_balance=all(row["pilot_sensitivity"] is None or
                                          row["pilot_sensitivity"]["hot_balance_pass"] for row in viable),
            physical_power_pass=(power["rms_shaft_kW"] <= 29 and power["peak_shaft_kW"] <= 40
                                 and power["average_shaft_kW"] <= 30),
            nominal_and_adverse_cycle_pass=max_real_s <= 5.85 and max_pess_s <= 6.,
            gate_time_and_status_pass=checked["value"] <= 5.95 and checked["status"] == "PASS",
            installed_power_pass=fsum(installed.values()) <= 34.2,
            heat_or_cooler_pass=worst_heat_kW <= 19 or cooling["required_T21_pass"],
            D_OP_09_pass=cooling["required_T21_pass"] and cooling["circulation_pass"],
            vfd_pass=all(row["vfd"] is None or (row["vfd"]["motor_load_screen_pass"]
                                               and row["vfd"]["converter_current_screen_pass"]) for row in viable),
        )
        return dict(
            **power, candidate=candidate, reference_base90_cycle_s=nominal["cycle_s"],
            reference_base90_with_T16_handover_s=nominal["cycle_with_T16_handover_s"],
            maximum_realistic_at_100_kN_s=max_real_s, maximum_pessimistic_at_100_kN_s=max_pess_s,
            maximum_pessimistic_at_110_kN_s=max(row["cycle_with_T16_handover_s"] for row in viable
                                               if row["profile"] == "pessimistic" and row["residual_N"] == 110_000),
            gate_cycle_s=checked["value"], gate_status=checked["status"],
            gate_rms_kW=checked["details"]["rms_power_kW"],
            gate_peak_kW=checked["details"]["peak_drive_power_kW"],
            gate_minus_reference_by_phase_s=phase_delta_s,
            gate_drive={key: value for key, value in params["drive"].items() if isinstance(value, (float, int))},
            oil_heat_kW=worst_heat_kW, heat_target_pass=worst_heat_kW <= 19,
            min_hot_pilot_pressure_bar=min(row["pilot"]["minimum_pilot_pressure_bar"] for row in viable),
            min_hot_pilot_capacity_margin_L_per_cycle=min(row["pilot"]["capacity_margin_L_per_cycle"] for row in viable),
            min_hot_pilot_sensitivity_margin_L_per_cycle=(
                min(row["pilot_sensitivity"]["capacity_margin_L_per_cycle"] for row in viable)
                if candidate == "A4VSO180_DFE1Z" else None),
            cooler=cooling, mass=station, installed_breakdown_kW=installed,
            installed_total_kW=fsum(installed.values()), qualification=qualification,
            pump_map=pump_curve(settings["pump"], settings["max_L_min"]),
            standby_shaft_kW=settings["pump"].operating_point(settings["pump"].standby_bar, 0)[1],
            risks={
                "PV180_FDV": "PV360 slew proxy; RMS and legacy thermal reserve.",
                "A4VSO180_DFE1Z": "Pilot flow at port Z, exact tandem fit, mapped partial stroke and hot slew.",
                "PV180_FDV_VFD": "Short neutral window, cyclic inverter current and IC411 thermal approval.",
            }[candidate],
            relative_price_class={"PV180_FDV": "reference", "A4VSO180_DFE1Z": "higher", "PV180_FDV_VFD": "higher"}[candidate],
        )


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--screen", action="store_true", help="Only T-1.7d base/90/100 kN replay, no writes")
    args = parser.parse_args()
    study = Study()
    reference = study.verified_reference()
    print(reference, flush=True)
    matrix = list(product(("base", "high"), (90, 160), ("realistic", "pessimistic"), (100_000, 110_000)))
    results, variants = {}, {}
    for candidate in CANDIDATES:
        params, checked = study.gate_for(candidate)
        print(candidate, "gate", checked["status"], checked["value"], checked["details"]["rms_power_kW"], flush=True)
        scenarios = [study.run(candidate, *case) for case in (matrix[:1] + matrix[2:3] if args.screen else matrix)]
        if args.screen:
            continue
        results[candidate] = dict(summary=study.summarize(candidate, scenarios, checked, params), scenarios=scenarios)
        variants[candidate] = params
    if args.screen:
        return
    catalogue_sensitivity = study.rexroth_catalogue_sensitivity()
    passing = [result["summary"] for result in results.values() if all(result["summary"]["qualification"].values())]
    selected = min(passing, key=lambda row: (row["oil_heat_kW"], row["mass"]["station_kg"])) if passing else None
    best_screen = min((result["summary"] for result in results.values()),
                      key=lambda row: (not row["qualification"]["nominal_and_adverse_cycle_pass"], row["rms_shaft_kW"]))
    screened_id = best_screen["candidate"]
    gate_id = selected["candidate"] if selected else screened_id
    params = variants[gate_id]
    (ROOT / "design/params.t21.yaml").write_text(
        "# Generated by calc/T-2.1/study.py. G-CYCLE hydraulic equivalent.\n"
        "# Physical geometry: design/cylinders.t17d.yaml and D-GK-05.\n"
        f"# {gate_id}; engineering disposition: {'selected for detail' if selected else 'screen only, HOLD'}.\n"
        "# Peak = shaft command limit; idle = zero displacement including unloaded tandem.\n"
        "# eta is the conservative direct-press flow projection at rated speed.\n"
        + yaml.safe_dump(params, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    write_json(HERE / "results.json", dict(reference_T17d=reference, selected=selected["candidate"] if selected else None,
                                           best_screen=screened_id, gate_candidate=gate_id, candidates=results,
                                           rexroth_catalogue_read_off_sensitivity=catalogue_sensitivity))
    write_json(ROOT / "metrics.json", dict(
        selected=selected["candidate"] if selected else None, best_screen=screened_id, gate_candidate=gate_id,
        reference_T17d=reference, rexroth_catalogue_read_off_sensitivity=catalogue_sensitivity,
        candidates={name: {key: result["summary"][key] for key in (
            "rms_shaft_kW", "average_shaft_kW", "peak_shaft_kW", "oil_heat_kW", "installed_total_kW",
            "reference_base90_cycle_s", "maximum_realistic_at_100_kN_s", "maximum_pessimistic_at_100_kN_s",
            "maximum_pessimistic_at_110_kN_s", "gate_cycle_s", "gate_rms_kW", "qualification",
            "min_hot_pilot_pressure_bar", "min_hot_pilot_capacity_margin_L_per_cycle",
            "min_hot_pilot_sensitivity_margin_L_per_cycle")}
            | {"station_kg": result["summary"]["mass"]["station_kg"],
               "cooler_fouled_kW": result["summary"]["cooler"]["fouled_capacity_kW"],
               "cooler_remaining_reserve_fraction": result["summary"]["cooler"]["remaining_reserve_fraction"]}
                    for name, result in results.items()}))


if __name__ == "__main__":
    main()

