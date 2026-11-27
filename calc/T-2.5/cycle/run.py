"""Replay the inherited A4VSO model and generate the two T-2.6 gate inputs."""

import csv
from dataclasses import dataclass, replace
import json
from math import sqrt
from pathlib import Path
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))

from compare import CandidateStudy, PUMP, TRANSFER
from drive import check_accumulator
from energy import gas_balance, shaft_balance, shaft_tolerance
from t26_inventory import assemble
from operating_point import OperatingPoint, configure_operating_point, verified_fill
from projection import gate_phases, phase_table, project
from x1_calc import Accumulator, area_m2, motions, periodic_run


GATE_LIMIT_S = 5.95
REFERENCE_LIMIT_S = 5.90
BASE_REFERENCE_S = 5.623750000000579
BASE_GATE_V1_S = 5.928629160188188
REF_STEPS_S = (.00125, .000625)
FINE_STEP_S = .0003125


@dataclass(frozen=True)
class Scenario:
    name: str
    fast_approach: bool = False
    fast_tail: bool = False
    rapid_regen: bool = False
    return_valve: str = "NG50_single_B"
    lp_eject: bool = False
    mp: bool = False
    pilot_rephased: bool = False
    pilot_reserve: bool = False
    fine: bool = False
    reserve_s: float | None = None
    main_limit_kW: float | None = None


CASES = (
    Scenario("A_existing"),
    Scenario("A_rapid_regeneration", fast_approach=True, rapid_regen=True),
    Scenario("A_mp_prefill", fast_approach=True, fast_tail=True, mp=True),
    Scenario("A_prefill_and_LP", fast_tail=True, return_valve="NG50_double_B", lp_eject=True),
    Scenario("A_combined_no_pilot_reserve", True, True, True, "NG50_double_B", True,
             pilot_rephased=True, fine=True),
    Scenario("A_combined_pilot_reserve", True, True, True, "NG50_double_B", True,
             pilot_rephased=True, pilot_reserve=True, fine=True),
    Scenario("A_combined_and_MP", True, True, True, "NG50_double_B", True, mp=True,
             pilot_rephased=True, pilot_reserve=True),
    Scenario("A_combined_NG63", True, True, True, "NG63_single_B", True,
             pilot_rephased=True, pilot_reserve=True),
    Scenario("A_combined_NG50_33p25_kW", True, True, True, "NG50_double_B", True,
             pilot_rephased=True, pilot_reserve=True, fine=True, reserve_s=.075, main_limit_kW=33.25),
    Scenario("A_combined_NG50_33p25_kW_short_reserve", True, True, True, "NG50_double_B", True,
             pilot_rephased=True, pilot_reserve=True, fine=True, reserve_s=.040, main_limit_kW=33.25),
    Scenario("A_combined_NG50_33p25_kW_50ms_AX", True, True, True, "NG50_double_B", True,
             pilot_rephased=True, pilot_reserve=True, fine=True, reserve_s=.050, main_limit_kW=33.25),
    Scenario("A_combined_NG50_33_kW", True, True, True, "NG50_double_B", True,
             pilot_rephased=True, pilot_reserve=True, fine=True, reserve_s=.110, main_limit_kW=33.),
)


def read_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def read_yaml(relative_path):
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def write_text(path, content):
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def write_inventory(rows):
    columns = ("id", "model", "qty", "length_m", "pressure_bar", "dry_kg", "oil_kg", "delta_kg", "basis", "source_url")
    with (HERE / "inventory.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter=";", extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for name, part in rows.items():
            values = {key: round(value, 6) if isinstance(value, float) else value for key, value in part.items()}
            writer.writerow(dict(id=name, qty=1) | values)


class HydraulicStudy:
    def __init__(self):
        self.sources = read_yaml("calc/T-2.6/sources.yaml")
        self.data = self.sources["study"]
        self.catalogs = self.sources["catalogs"]
        self.base_params = read_yaml("design/params.t22d.yaml")
        self.window_x_mm = read_json("calc/T-2.2d/round1_load.json")["window_x_mm"]
        self.previous_A = read_json("calc/T-2.2f/results.json")["series"]["A_90"]
        self.mass_names = self.previous_A["hand"]["mass"]["chamber_rows_kg"]
        self.base_study = CandidateStudy(self.data["base_roof_mm"], "existing")
        self.gate = self.base_study.gate
        self.criteria = self.base_study.criteria

    def configuration(self, scenario, profile="realistic", *, material="base", bulk_kg_m3=90, residual_N=None,
                      operating_point=OperatingPoint()):
        data, catalogs = self.data, self.catalogs
        if scenario is None:
            study = self.base_study
        else:
            cam = self.previous_A["hand"]["cam"]
            study = CandidateStudy(data["roof_mm"], "existing", cam_m=cam["stem_stroke_mm"] / 1000,
                                   cam_seconds=cam["minimum_movement_s"], cam_force_N=cam["stem_force_N"],
                                   shoe_mass_kg=self.mass_names["shoe_core"] + self.mass_names["wings_and_portal_ties"])
        residual_N = data["residual_gate_force_N"] if residual_N is None else residual_N
        _, (model, cylinder, settings, _, lp) = study.configuration(PUMP, profile, material, bulk_kg_m3, residual_N)
        condition = operating_point
        if scenario and scenario.main_limit_kW is not None:
            condition = replace(condition, regulator_fraction=condition.regulator_fraction * scenario.main_limit_kW
                                / settings["pump"].limit_kW)
        oil_conditions = configure_operating_point(study, settings, condition, self.sources["round2"]["oil"],
                                                   study.circuit["elements"]["P1"]["Q_L_min"])
        oil_conditions["programmed_main_limit_kW"] = settings["pump"].limit_kW
        source_cfg = study.reference_sources
        config = source_cfg["engineering_inputs"]
        suction = self.sources["round2"]["suction"]
        assert scenario is not None and operating_point.tank_gauge_bar is None
        config["buffer_oil_L"] = self.data["buffer_A_L"]
        settings["prefill"]["rapid_regeneration"] = scenario.rapid_regen
        if scenario.fast_approach:
            model = replace(model, rapid_approach_m_s=data["rapid_approach_m_s"])
        if scenario.rapid_regen:
            settings["prefill"]["switch_force_N"] = data["rapid_approach_switch_N"]
            model = replace(model, regen_switch_bar=data["main_regen_switch_bar"])
        if scenario.fast_tail:
            if scenario.mp and not scenario.rapid_regen:
                # The standalone MP trial assists the existing rapid pair.
                model = replace(model, rapid_approach_m_s=.40, rapid_return_m_s=.42)
            else:
                model = replace(model, rapid_eject_m_s=data["rapid_eject_m_s"],
                                rapid_return_m_s=data["rapid_return_m_s"])
            config["annulus_makeup_drop_allowance_bar"] *= (
                model.rapid_return_m_s / config["rapid_return_m_s"])**2
            wrle = catalogs["wrle"]
            rap_cap_m2 = settings["prefill"]["count"] * area_m2(settings["prefill"]["bore_mm"])
            tank_flow_L_min = 60000 * rap_cap_m2 * model.rapid_return_m_s
            inlet_bar, tank_bar, regen_bar = model.losses_bar
            tank_bar = max(tank_bar, wrle["rated_drop_bar"] * (tank_flow_L_min / wrle["rated_flow_L_min"])**2)
            model = replace(model, return_losses_bar=(inlet_bar, tank_bar, regen_bar))
        ng = 63 if scenario.return_valve.startswith("NG63") else 50
        config["local_exhaust_NG"] = ng
        flow_L_min = catalogs["wrce"]["mf_" + scenario.return_valve + "_L_min"]
        study.reference_sources["catalogs"]["rexroth_2wrce"]["rated_flow_L_min_by_ng"][ng] = flow_L_min
        nominal_tank_bar = suction["regulated_tank_gauge_bar"]
        band_bar = suction["tank_regulation_band_bar"]
        low_tank_bar = nominal_tank_bar - band_bar
        config["prefill_pipe"]["tank_gauge_bar"] = nominal_tank_bar + band_bar
        fill = verified_fill(model, cylinder, source_cfg, suction, low_tank_bar)
        fill["tank_nominal_gauge_bar"] = nominal_tank_bar
        tank = self.sources["round2"]["inventory"]
        cap_volume_L = cylinder.cap_m2 * cylinder.stroke_mm + tank["cap_dead_volume_L"]
        net_withdrawal_L = cylinder.rod_m2 * cylinder.stroke_mm
        oil_needed_L = 1.5 * cap_volume_L + net_withdrawal_L
        gas_initial_L = tank["tf_A_gross_L"] - fill["buffer_oil_L"]
        fill.update(gross_TF_L=tank["tf_A_gross_L"], cap_with_dead_oil_L=cap_volume_L,
                    required_oil_after_stroke_L=1.5 * cap_volume_L, net_withdrawal_bound_L=net_withdrawal_L,
                    required_initial_oil_L=oil_needed_L, initial_oil_margin_L=fill["buffer_oil_L"] - oil_needed_L,
                    sealed_gas_end_absolute_bar=(suction["ambient_absolute_bar"] + nominal_tank_bar) * (
                        gas_initial_L / (gas_initial_L + net_withdrawal_L))**1.4,
                    max_gas_flow_at_TF_L_min=60000 * cylinder.rod_m2 * max(
                        model.rapid_approach_m_s, model.rapid_eject_m_s, model.rapid_return_m_s))
        assert fill["initial_oil_margin_L"] > 0.
        settings["prefill"].update(return_float_drag_kN=fill["return_drag_budget_N"] / 1000,
                                   float_gauge_bar=nominal_tank_bar)
        if scenario.lp_eject:
            # LR/LRC is repurposed for rapid A. LP cannot support rapid B at its running pressure.
            settings["boost_branches"] = tuple(name for name in settings["boost_branches"] if name != "return") + ("eject",)
        if scenario.mp:
            mp = data["mp"]
            storage = {key: mp[key] for key in ("precharge_bar", "low_bar", "high_bar", "delivery_L_min")}
            storage["shell_L"] = catalogs["mp"]["shell_L"]
            capacity_L_min = settings["pump"].capacity_L_min(mp["high_bar"] + settings["charge_drop_bar"])
            settings.update(mp_accumulator_kwargs=storage, mp_branches=("prefill", "return"),
                            mp_cycle_budget_L=mp["cycle_budget_L"],
                            lp_tail_reserve_s=mp["tail_changeover_allowance_s"] + 60 * mp["cycle_budget_L"] / capacity_L_min)
            check_accumulator(Accumulator(**storage), study.reference_sources["catalogs"]["hydac_sb330"])
        if scenario.pilot_reserve:
            settings["pilot_idle_s"] = scenario.reserve_s or data["ax_idle_reserve_s"]
        return study, model, cylinder, settings, lp, fill, oil_conditions

    def mass_and_power(self, scenario, rails, oil_density_kg_m3, geometry):
        if scenario is None:
            return dict(added_hydraulics_kg=0., installed_kW=self.base_params["drive"]["installed_kW"])
        data, catalogs = self.data, self.catalogs
        mass = assemble(self.sources["round2"]["inventory"], catalogs, scenario, oil_density_kg_m3, geometry,
                        rails, self.previous_A["hand"]["mass"])
        coils = (data["added_regen_coils_count"] if scenario.rapid_regen else 0) + (
            data["mp"]["additional_coils_count"] if scenario.mp else 0)
        electrical_W = (coils * catalogs["pilot_coil"]["power_W_per_coil"]
                        + (data["aux_controls_allowance_W"] if coils or scenario.lp_eject else 0))
        return mass | dict(added_controls_W=electrical_W,
                           installed_kW=self.base_params["drive"]["installed_kW"] + electrical_W / 1000)

    def valve_summary(self, scenario, model, cylinder, settings, fill, run, rails):
        cat = self.catalogs
        annulus_out = fill["annulus_exhaust"]
        mbt_drop_bar = cat["wrce"]["rated_drop_bar"] * (
            annulus_out["flow_L_min"] / cat["wrce"]["mbt_NG40_L_min"])**2
        mbt_bar = (fill["head_at_tank_gauge_bar"] + fill["liquid_level_head_bar"]
                   + annulus_out["steady_drop_bar"] + annulus_out["acceleration_head_bar"] + mbt_drop_bar)
        cap_min_abs_bar = min(part["min_absolute_bar"] for part in fill["cap_intake"].values())
        forward_oil_drag_N = 1e5 * (mbt_bar * cylinder.annulus_m2
                                   + max(0., 1.01325 - cap_min_abs_bar) * cylinder.cap_m2)
        assert mbt_bar <= annulus_out["pressure_budget_bar"]
        assert forward_oil_drag_N <= settings["prefill"]["main_float_drag_kN"] * 1000
        balance = dict(pressure_max_bar=run["peak_working_bar"], main_nominal_bar=run["nominal_setpoint_bar"],
                       ZSF=dict(flow_L_min=max(part["flow_L_min"] for part in fill["cap_intake"].values()),
                                catalog_flow_L_min=cat["zsf"]["case_2_flow_L_min"],
                                cap_rated_bar=cat["zsf"]["cap_side_max_bar"],
                                buffer_rated_bar=cat["zsf"]["buffer_side_max_bar"],
                                cap_min_abs_bar=cap_min_abs_bar,
                                source="zsf"),
                       MF=dict(flow_L_min=fill["cap_exhaust"]["flow_L_min"],
                               operating_port_gauge_bar=fill["cap_exhaust"]["peak_gauge_bar"],
                               separating_pressure_bar=315, catalog_pressure_bar=cat["wrce"]["working_max_bar"],
                               catalog_flow_at_5_bar_L_min=cat["wrce"][
                                   "mf_" + (scenario.return_valve if scenario else "NG50_single_B") + "_L_min"],
                               source="wrce"),
                       MC=dict(flow_L_min=fill["annulus_intake"]["flow_L_min"],
                               operating_port_min_abs_bar=fill["annulus_intake"]["min_absolute_bar"],
                               isolating_pressure_bar=315, source="regen"),
                       MBT=dict(flow_L_min=annulus_out["flow_L_min"], operating_port_gauge_bar=mbt_bar,
                                estimated_drop_bar=mbt_drop_bar, forward_oil_drag_N=forward_oil_drag_N,
                                catalog_flow_at_5_bar_L_min=cat["wrce"]["mbt_NG40_L_min"],
                                separating_pressure_bar=315, catalog_pressure_bar=cat["wrce"]["working_max_bar"],
                                source="wrce"),
                       LCH=dict(flow_L_min=rails["lp"]["peak_actual_charge_L_min"],
                                header_bar=settings["accumulator_kwargs"]["high_bar"] + settings["charge_drop_bar"],
                                source="circuit"),
                       LR=dict(flow_L_min=rails["lp"]["peak_actual_delivery_L_min"],
                               high_side_setpoint_bar=settings["accumulator_kwargs"]["high_bar"],
                               selected_rapid_side="A_eject" if scenario and scenario.lp_eject else "B_return",
                               source="circuit"))
        sequence = motions(model, cylinder, run["bulk_density_kg_m3"], settings["prefill"])
        rapid = settings["prefill"]
        return_cylinder = sequence["return"].cylinder
        balance["VR"] = dict(pump_inlet_flow_limit_L_min=settings["max_L_min"],
                             rapid_A_exhaust_flow_L_min=60000 * return_cylinder.cap_m2 * model.rapid_return_m_s,
                             rated_flow_L_min=cat["wrle"]["rated_flow_L_min"],
                             max_observed_branch_bar=max(run["motion_events"][key]["peak_supply_bar"]
                                                         for key in ("prefill", "return", "eject")),
                             rated_pressure_bar=cat["wrle"]["pressure_max_bar"], source="wrle")
        if rapid.get("rapid_regeneration"):
            q_L_min = 60000 * sequence["prefill"].cylinder.annulus_m2 * model.rapid_approach_m_s
            flow_at_10_L_min = cat["regen"]["lc25_no_damping_flow_at_10_bar_L_min"]
            balance["rapid_regeneration"] = dict(flow_L_min=q_L_min, estimated_drop_bar=10 * (q_L_min / flow_at_10_L_min)**2,
                                                observed_branch_bar=run["motion_events"]["prefill"]["peak_supply_bar"],
                                                catalog_pressure_bar=cat["regen"]["lc25_nominal_pressure_max_bar"],
                                                source="regen")
        if scenario and scenario.mp:
            balance["MP_route"] = dict(flow_L_min=rails["mp"]["peak_actual_delivery_L_min"],
                                       charge_flow_L_min=rails["mp"]["peak_actual_charge_L_min"],
                                       accumulator_high_bar=settings["mp_accumulator_kwargs"]["high_bar"],
                                       hydraulic_header_max_bar=settings["mp_accumulator_kwargs"]["high_bar"]
                                       + settings["charge_drop_bar"],
                                       charge_and_delivery_drop_budget_bar=settings["charge_drop_bar"],
                                       catalog_vessel_max_bar=cat["mp"]["max_pressure_bar"],
                                       source="mp")
        return balance

    def replay(self, scenario, *, profile="realistic", material="base", residual_N=None, bulk_kg_m3=90,
               operating_point=OperatingPoint()):
        study, model, cylinder, settings, lp, fill, oil = self.configuration(
            scenario, profile, material=material, residual_N=residual_N, bulk_kg_m3=bulk_kg_m3,
            operating_point=operating_point)
        steps_s = (*REF_STEPS_S, FINE_STEP_S) if scenario and scenario.fine else REF_STEPS_S
        nominal_valve_s = study.reference_sources["engineering_inputs"]["valve_allowance_s"]
        handover_s = study.interlocks["switching_windows"]["handover_regen_press"][
            "modeled_switch_budget_s"] - nominal_valve_s
        runs = [periodic_run(model, cylinder, bulk_kg_m3, self.data["feed_s"], settings, dt_s) for dt_s in steps_s]
        run = runs[-1]
        if not run["feasible"]:
            return run, None, None
        assert all(row["feasible"] for row in runs)
        stages = run["stage_events"]
        events = run["motion_events"]
        commands_s = {item["command"]: item["time_s"] for item in run["switches"]}
        assert commands_s["gate_open"] >= stages["unload"][1] - 1e-9
        assert commands_s["eject"] >= events["gate_open"]["end_s"] - 1e-9
        assert commands_s["return"] >= events["eject"]["end_s"] - 1e-9
        assert commands_s["gate_close"] >= events["return"]["gate_clear_s"] - 1e-9
        assert stages["feed"][0] >= max(events[name]["end_s"] for name in ("return", "gate_close", "pre_up")) - 1e-9
        extra_pilot_L = 0.
        reservation_s = None
        if scenario:
            if scenario.rapid_regen:
                extra_pilot_L += 4 * self.catalogs["regen"]["lc25_E_pilot_mL"] / 1000
            if scenario.mp:
                extra_pilot_L += 4 * self.catalogs["regen"]["lc25_E_pilot_mL"] / 1000
            if scenario.return_valve.startswith("NG63"):
                wrc = self.catalogs["wrce"]
                extra_pilot_L += 2 * (wrc["mf_NG63_pilot_mL"] - wrc["mf_NG50_pilot_mL"]) / 1000
            if scenario.pilot_rephased:
                reservation_s = self.data["ax_block_s"]
        shaft = shaft_balance(study, run, settings, handover_s, extra_pilot_L, reservation_s)
        rails = gas_balance(run, settings, shaft)
        density = study.reference_sources["engineering_inputs"]["oil_density_kg_m3"]
        mass = self.mass_and_power(scenario, rails, density, fill)
        valves = self.valve_summary(scenario, model, cylinder, settings, fill, run, rails)
        reference_s = shaft["cycle_s"]
        result = dict(
            feasible=True, reference_cycle_s=reference_s, handover_allowance_s=handover_s,
            throughput_kg_h=3600 * model.dose_kg / reference_s,
            reference=shaft, accumulators=rails, valves=valves, prefill=fill, mass=mass,
            operating_point=vars(operating_point) | oil | dict(valve_s=settings["switch_s"], unload_s=settings["unload_s"]),
            model=dict(roof_mm=model.transfer_m * 1000, main_cylinder_bore_mm=cylinder.bore_mm,
                       main_cylinder_rod_mm=cylinder.rod_mm, main_stroke_mm=cylinder.stroke_mm,
                       main_working_travel_mm=model.main_travel_m * 1000, local_overtravel_mm=model.overtravel_m * 1000,
                       approach_m_s=model.rapid_approach_m_s, eject_m_s=model.rapid_eject_m_s,
                       return_m_s=model.rapid_return_m_s, rapid_accel_m_s2=model.rapid_accel_m_s2,
                       rapid_mass_kg=model.rapid_mass_kg, return_stop_energy_J=.5 * model.rapid_mass_kg * model.rapid_return_m_s**2,
                       transfer_push_force_N=model.transfer_drag_N, approach_switch_N=settings["prefill"]["switch_force_N"],
                       main_regen_switch_bar=model.regen_switch_bar, eject_load_N=model.ejection_N,
                       gate_residual_force_N=self.data["residual_gate_force_N"] if residual_N is None else residual_N,
                       cam_stroke_mm=model.cam_m * 1000, cam_speed_m_s=model.cam_stem_speed_m_s,
                       gate_close_inset_mm=model.gate_close_punch_inset_m * 1000,
                       feed_s=run["feed_s"], pilot_idle_s=settings.get("pilot_idle_s", 0.)),
            steps=[dict(step_s=step_s, reference_cycle_s=row["cycle_s"] + handover_s)
                   for step_s, row in zip(steps_s, runs)],
            convergence_s=abs(runs[-1]["cycle_s"] - runs[-2]["cycle_s"]),
            closure_displacement_fraction=run["periodic_closure_displacement_fraction"],
            periodic_period_cycles=run["periodic_period_cycles"],
            post_feed_oil_charge_s=run["extra_recharge_s"], gatekeeping_idle_s=run["guard_block_s"],
            motion_events=events, stage_events=stages, commands_s=commands_s)
        params, projection = project(self.base_params, model, cylinder, settings, bulk_kg_m3, self.data["feed_s"],
                                     self.gate, study, self.sources["round2"]["pump_guard"],
                                     shaft_tolerance(study, settings["pump"]))
        params["drive"]["installed_kW"] = mass["installed_kW"]
        result["gates"] = {key: method(params, self.criteria) for key, method in self.gate.GATES.items()}
        cycle_gate = result["gates"]["G-CYCLE"]
        result["gate_minus_reference_s"] = cycle_gate["value"] - reference_s
        result["projection"] = projection | dict(equivalent_rod_mm=params["main_cylinder"]["rod_mm"],
                                                  cycle_rows=len(params["cycle"]))
        return result, params, run

