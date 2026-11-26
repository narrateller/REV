"""Replay the A4VSO cycle with an independently fed four-sleeve drive."""

from copy import deepcopy
from dataclasses import replace
from math import degrees, fsum, pi, sqrt
from pathlib import Path
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from roof_cycle import PUMP, RoofStudy
from hand import calculate, prior

CONFIRM_S = .010
RESIDUAL_MAX_N = 2000.
CHECKED_FREE_APPROACH_MM = 4.
DIAPHRAGM_SHELL_L = .60
NITROGEN_PRECHARGE_BAR = 160.
ACCUMULATOR_MIN_BAR = 205.
ACCUMULATOR_MAX_BAR = 240.
DISCHARGE_GAMMA = 1.4
ACTUATOR_MIN_BAR = 185.
ACTUATOR_ETA = .90
ACTUATOR_BORE_MM = 36.
ACTUATOR_ROD_MM = 12.
CHARGE = dict(window_s=.195, flow_L_min=14., demand_L=.035, pump_bar=248.)
SHAFT_NET_DIAMETER_MM = 30.
LONGEST_SHAFT_TORQUE_PATH_MM = 750.
LINKAGE_INERTIA_ALLOWANCE_KG_M2 = .0025


def actuator_budget(selected):
    inherited = selected["drive"]
    stroke_mm = inherited["stroke_mm"]
    turn = next(row for row in inherited["rows"] if row["duration_s"] == .08)
    arm_m = (stroke_mm / 1000 * inherited["transmission_eta_assumed"]
             / prior.radians(inherited["rotation_deg"]))
    extra_inertia_N = (LINKAGE_INERTIA_ALLOWANCE_KG_M2 * 4 * prior.radians(inherited["rotation_deg"])
                       / turn["duration_s"]**2 / arm_m)
    unloaded_force_N = turn["unloaded_stem_force_N"] + extra_inertia_N
    demand_force_N = unloaded_force_N + inherited["added_static_stem_force_per_kN_residual_N"] * RESIDUAL_MAX_N / 1000
    cap_mm2 = pi * ACTUATOR_BORE_MM**2 / 4
    annulus_mm2 = cap_mm2 - pi * ACTUATOR_ROD_MM**2 / 4
    available_force_N = ACTUATOR_MIN_BAR * .1 * annulus_mm2 * ACTUATOR_ETA
    cycle_oil_L = stroke_mm * (cap_mm2 + annulus_mm2) / 1e6
    p0_abs_bar = NITROGEN_PRECHARGE_BAR + 1.
    available_oil_L = DIAPHRAGM_SHELL_L * (
        (p0_abs_bar / (ACCUMULATOR_MIN_BAR + 1.))**(1 / DISCHARGE_GAMMA)
        - (p0_abs_bar / (ACCUMULATOR_MAX_BAR + 1.))**(1 / DISCHARGE_GAMMA))
    angular_rad = prior.radians(inherited["rotation_deg"])
    available_torque_Nm = available_force_N * stroke_mm / 1000 * inherited["transmission_eta_assumed"] / angular_rad
    require_torque_Nm = demand_force_N * stroke_mm / 1000 * inherited["transmission_eta_assumed"] / angular_rad
    duration_s = turn["duration_s"] + CONFIRM_S
    shaft_J_mm4 = pi * SHAFT_NET_DIAMETER_MM**4 / 32
    shaft_twist_deg = degrees(available_torque_Nm * 1000 * LONGEST_SHAFT_TORQUE_PATH_MM
                              / (prior.G_MPa * shaft_J_mm4))
    shaft_shear_MPa = available_torque_Nm * 1000 * SHAFT_NET_DIAMETER_MM / (2 * shaft_J_mm4)
    return dict(
        turn_s=turn["duration_s"], confirmation_s=CONFIRM_S, command_to_confirm_s=duration_s,
        angle_deg=inherited["rotation_deg"], stroke_mm=stroke_mm,
        sleeve_inertia_kg_m2=inherited["combined_rotor_inertia_kg_m2"],
        linkage_inertia_allowance_kg_m2=LINKAGE_INERTIA_ALLOWANCE_KG_M2,
        shaft=dict(net_diameter_mm=SHAFT_NET_DIAMETER_MM, effective_path_mm=LONGEST_SHAFT_TORQUE_PATH_MM,
                   elastic_twist_deg=shaft_twist_deg, torsion_shear_MPa=shaft_shear_MPa,
                   position_window_half_deg=1.0),
        stem_peak_speed_mm_s=turn["triangular_peak_stem_speed_mm_s"],
        worst_residual_shoe_force_N=RESIDUAL_MAX_N, stem_demand_N=demand_force_N,
        stem_unloaded_N=unloaded_force_N, stem_available_N=available_force_N,
        drive_demand_Nm=require_torque_Nm, drive_available_Nm=available_torque_Nm,
        fully_loaded_unlock_diagnostic_Nm=inherited["loaded_friction_torque_Nm"],
        hydraulic=dict(bore_mm=ACTUATOR_BORE_MM, rod_mm=ACTUATOR_ROD_MM,
                       min_actuator_bar=ACTUATOR_MIN_BAR, gas_shell_L=DIAPHRAGM_SHELL_L,
                       precharge_bar=NITROGEN_PRECHARGE_BAR, min_header_bar=ACCUMULATOR_MIN_BAR,
                       max_header_bar=ACCUMULATOR_MAX_BAR, available_oil_L=available_oil_L,
                       stroke_oil_per_cycle_L=cycle_oil_L,
                       peak_flow_L_min=cap_mm2 * turn["triangular_peak_stem_speed_mm_s"] * 60 / 1e6,
                       charge=CHARGE),
        screen_pass=(shaft_twist_deg < 1. and demand_force_N < available_force_N and cycle_oil_L < CHARGE["demand_L"] < available_oil_L),
    )


class BayonetStudy(RoofStudy):
    def __init__(self, saved, selected):
        transfer = {case: {int(density): item for density, item in rows.items()}
                    for case, rows in saved["transfer"].items()}
        super().__init__(15, transfer, adds_local_overtravel=False)
        self.budget = actuator_budget(selected)
        rows_kg = selected["mass"]["chamber_rows_kg"]
        self.moving_kg = fsum(mass for name, mass in rows_kg.items() if name == "moving_crosshead"
                              or name.endswith(("rotating_teeth", "rotating_sleeves", "carrier_lands")))
        self.moving_kg += rows_kg["synchronizer_and_guards"]

    def configuration(self, candidate, profile, case, bulk_kg_m3, residual_N, **options):
        inputs, (model, cylinder, settings, projection, charge) = super().configuration(
            candidate, profile, case, bulk_kg_m3, residual_N, **options)
        # Guide-only baseline is from the original drive. Include the moving lock mass.
        guide_force_N = 6000 + max(0., self.moving_kg - 200 * 150 * 45 * 7.85e-6) * 9.81
        model = replace(model, cam_m=0., cam_force_N=0., pre_return_force_N=guide_force_N)
        settings.update(unlock_verify_s=self.budget["command_to_confirm_s"], lock_charge=CHARGE)
        return inputs, (model, cylinder, settings, projection, charge)

    def gate_with_bayonet(self):
        params, _ = self.gate_for(PUMP)
        phases = params["cycle"]
        pre_up = next(row for row in phases if row["name"] == "pre_up 1")
        tail = [row for row in phases if row.get("group") == pre_up["group"]]
        gate_close = next(row for row in tail if row["name"] == "gate_close 1")
        original_delay_s = gate_close["start_delay_s"]
        pre_up["start_delay_s"] += self.budget["command_to_confirm_s"]
        base_ends = self.gate.evaluate_cycle(params, self.criteria)
        # The close command remains tied to the same return-coordinate band.
        no_close = [row for row in tail if not row["name"].startswith("gate_close ")]
        from make_params_t14b import tail_end_times
        original = deepcopy(no_close)
        next(row for row in original if row["name"] == "pre_up 1")["start_delay_s"] -= self.budget[
            "command_to_confirm_s"]
        original_ends = tail_end_times(self.gate, params, original)
        crossing = next(name for name, time_s in original_ends.items()
                        if name.startswith("return ") and abs(time_s - original_delay_s) < 1e-9)
        gate_close["start_delay_s"] = tail_end_times(self.gate, params, no_close)[crossing]
        params["description"] = (
            "T-2.2e, D-GK-10. A4VSO180 DFE1Z. Ход прежнего кулачка исключён. "
            "Команда подъёма ждёт подтверждения отпирания 90 мс после выхода дозы. "
            "Замыкание внутри переключения prefill. Изолированный ГА муфт и его заряд внутри "
            "выдержки проверены отдельно в calc/T-2.2e/cycle/bayonet.py. "
            "Перебег G-DOSE отсчитывается от x=205 мм.")
        self.gate.validate_params(params)
        gated = self.gate.evaluate_cycle(params, self.criteria)
        p = {r["name"]: r for r in gated["details"]["phases"]}
        seated_s = max(r["motion_end_s"] for name, r in p.items() if name.startswith("pre_down "))
        first_prefill_s = p["prefill 1"]["motion_start_s"]
        commanded_unlock_s = p["pre_up 1"]["group_start_s"] + pre_up["start_delay_s"] - self.budget[
            "command_to_confirm_s"]
        last_eject_s = max(r["motion_end_s"] for name, r in p.items() if name.startswith("eject "))
        schedule = dict(
            engaged_start_s=seated_s, engaged_confirmed_s=seated_s + self.budget["command_to_confirm_s"],
            main_first_motion_s=first_prefill_s,
            unlocked_start_s=commanded_unlock_s,
            unlocked_confirmed_s=commanded_unlock_s + self.budget["command_to_confirm_s"],
            eject_end_s=last_eject_s, shoe_up_start_s=p["pre_up 1"]["motion_start_s"],
        )
        assert schedule["engaged_confirmed_s"] <= first_prefill_s
        assert schedule["unlocked_confirmed_s"] <= min(schedule["shoe_up_start_s"], last_eject_s)
        assert abs(base_ends["value"] - gated["value"]) < .1
        return params, gated, schedule

    def verify_reference(self, profile):
        reference = self.run(PUMP, "base", 90, profile, 100_000)
        if not reference["feasible"]:
            return reference
        events = reference["motion_events"]
        _, (model, _, settings, _, _) = self.configuration(PUMP, profile, "base", 90, 100_000)
        # Reserve 1 mm of the nominal 5 mm approach for tolerances. The
        # fastest trajectory starts from rest at the configured acceleration.
        acceleration_m_s2 = model.rapid_accel_m_s2
        speed_m_s = model.rapid_approach_m_s
        distance_at_speed_m = speed_m_s**2 / (2 * acceleration_m_s2)
        distance_m = CHECKED_FREE_APPROACH_MM / 1000
        minimum_travel_s = (sqrt(2 * distance_m / acceleration_m_s2) if distance_m <= distance_at_speed_m
                            else speed_m_s / acceleration_m_s2 + (distance_m - distance_at_speed_m) / speed_m_s)
        time_grid_s = reference["convergence"][-1][0]
        first_product_bound_s = events["prefill"]["start_s"] + minimum_travel_s - 2 * time_grid_s
        close_start_s = events["pre_down"]["end_s"]
        open_start_s = events["eject"]["unlock_clear_s"]
        close_end_s = close_start_s + self.budget["command_to_confirm_s"]
        open_end_s = open_start_s + self.budget["command_to_confirm_s"]
        close_margin_s = first_product_bound_s - close_end_s
        charge_s = reference["stage_events"]["bayonet_charge"]
        return dict(
            cycle_s=reference["cycle_with_T16_handover_s"], rms_shaft_kW=reference["rms_shaft_kW"],
            peak_shaft_kW=reference["peak_shaft_kW"], peak_working_bar=reference["peak_working_bar"],
            convergence=reference["convergence"], convergence_pass=reference["convergence_pass"],
            reference_switch_s=settings["switch_s"], profile=profile, moving_mass_kg=self.moving_kg,
            lock_start_s=close_start_s, lock_confirmed_s=close_end_s,
            prefill_start_s=events["prefill"]["start_s"], earliest_verified_material_contact_s=first_product_bound_s,
            lock_margin_s=close_margin_s,
            unlock_start_s=open_start_s, unlock_confirmed_s=open_end_s, eject_end_s=events["eject"]["end_s"],
            shoe_up_start_s=events["pre_up"]["start_s"], hold_charge_interval_s=charge_s,
            unlock_overlaps_ejection=(open_end_s <= events["eject"]["end_s"]),
            unlock_before_rise=(open_end_s <= events["pre_up"]["start_s"]),
            bayonet_charge_checked=True, feasible=reference["feasible"],
            events=events, stages=reference["stage_events"],
        )


def evaluate(selected, saved):
    study = BayonetStudy(saved, selected)
    params, gated, schedule = study.gate_with_bayonet()
    references = {name: study.verify_reference(name) for name in ("realistic", "pessimistic")}
    charge_kW = CHARGE["pump_bar"] * CHARGE["flow_L_min"] / 600 / params["drive"]["eta"]
    # Charge takes place during the hold. Bound the increment relative to
    # the pump's idle power, and leave the main press peak as evaluated.
    hold_kW = params["drive"]["idle_kW"] + charge_kW
    rms_with_charge_kW = sqrt(gated["details"]["rms_power_kW"]**2
                              + (hold_kW**2 - params["drive"]["idle_kW"]**2)
                              * CHARGE["window_s"] / gated["value"])
    real = references["realistic"]
    reference_s = real.get("cycle_s", 100.)
    passes = (study.budget["screen_pass"] and gated["status"] == "PASS" and gated["value"] <= 5.95
              and reference_s <= 5.90 and real.get("convergence_pass") and real.get("lock_margin_s", -1.) >= 0.
              and real.get("unlock_overlaps_ejection") and real.get("unlock_before_rise")
              and rms_with_charge_kW <= 30. and hold_kW <= 40.)
    return dict(passes=bool(passes), gate_s=gated["value"], gate_status=gated["status"],
                gate_rms_with_bayonet_charge_bound_kW=rms_with_charge_kW,
                bayonet_charge_peak_bound_kW=hold_kW, gate_schedule=schedule, reference_s=reference_s,
                references=references, actuator=study.budget), params


if __name__ == "__main__":
    import json
    hand, _, saved = calculate()
    cycle, params = evaluate(hand["selected"], saved)
    print(json.dumps(cycle, indent=2, ensure_ascii=True))

