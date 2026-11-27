"""Replay candidate cycles on the copied T-2.1 pressure/flow model."""

from dataclasses import replace
from pathlib import Path
import json

from drive import check_accumulator, prefill_budget
from roof_cycle import PUMP, RoofStudy
from x1_calc import Accumulator, periodic_run


ROOT = Path(__file__).resolve().parents[3]

TRANSFER = json.loads((ROOT / "calc/T-2.2d/results.json").read_text(encoding="utf-8"))["transfer"]
TRANSFER = {name: {int(bulk): row for bulk, row in cases.items()} for name, cases in TRANSFER.items()}

# Gauge pressures. The unchanged bladder is HYDAC 3047174 (18.4 L effective).
# The 80 bar floor makes the gate projection conservative for the higher-pressure rail.
RECOVERY = {
    "existing": None,
    "existing_GA_to_rapid": (28, 38, 52, 180, .30),
    "regen_rapid": (28, 38, 52, 180, .35),
    "regen_early": (28, 38, 52, 180, .35),
    "GA85": (57, 70, 85, 220, .35),
    "GA105": (65, 80, 105, 265, .35),
}


class CandidateStudy(RoofStudy):
    def __init__(self, roof_mm, variant, cam_m=.012, cam_seconds=None, cam_force_N=None, shoe_mass_kg=None):
        super().__init__(roof_mm, TRANSFER, adds_local_overtravel=False)
        self.variant = variant
        self.cam_m = cam_m
        self.cam_seconds = cam_seconds
        self.cam_force_N = cam_force_N
        self.shoe_mass_kg = shoe_mass_kg
        self.prefill_checks = {}
        if roof_mm >= 75:
            self.trial["geometry"]["buffer_oil_L"] = 40
            self.reference_sources["engineering_inputs"]["buffer_oil_L"] = 40

    def configuration(self, candidate, profile, case, bulk_kg_m3, residual_N, **options):
        inputs, (model, cylinder, settings, projection, charge) = super().configuration(
            candidate, profile, case, bulk_kg_m3, residual_N, **options)
        model = replace(model, cam_m=self.cam_m)
        if self.cam_seconds is not None:
            model = replace(model, cam_stem_speed_m_s=self.cam_m/self.cam_seconds,
                            cam_force_N=self.cam_force_N,
                            pre_return_force_N=6000. + max(0., self.shoe_mass_kg-10.5975)*9.81)
        if self.variant == "regen_early":
            # A real controller must also confirm the shoe reaction has fallen below the release threshold.
            settings["unlock_x_m"] = max(.210, model.press_end_m + .001)
        # Configure set cylinder dimensions before transfer was added. Make explicit
        # the true stroke for port oil compression and the prefill buffer checks.
        cylinder = replace(cylinder, stroke_mm=self.trial["geometry"]["main_installed_stroke_mm"])
        self.prefill_checks[profile] = prefill_budget(model, cylinder, self.reference_sources)
        if self.variant == "existing":
            return inputs, (model, cylinder, settings, projection, charge)

        p0_bar, low_bar, high_bar, delivery_L_min, approach_m_s = RECOVERY[self.variant]
        model = replace(model, rapid_approach_m_s=approach_m_s)
        prefill = prefill_budget(model, cylinder, self.reference_sources)
        self.prefill_checks[profile] = prefill
        settings["prefill"]["return_float_drag_kN"] = max(
            settings["prefill"]["main_float_drag_kN"], prefill["return_drag_budget_N"] / 1000)
        settings["accumulator_kwargs"].update(precharge_bar=p0_bar, low_bar=low_bar,
                                               high_bar=high_bar, delivery_L_min=delivery_L_min)
        settings["prefill"]["rapid_regeneration"] = self.variant in ("regen_rapid", "regen_early")
        if not settings["prefill"]["rapid_regeneration"]:
            settings["boost_branches"] += ("prefill", "eject")
        acc = Accumulator(shell_L=settings["accumulator_shell_L"], **settings["accumulator_kwargs"])
        check_accumulator(acc, self.reference_sources["catalogs"]["hydac_sb330"])
        charge.update(usable_oil_L=1000 * (acc.oil_at_m3(high_bar) - acc.oil_at_m3(low_bar)),
                      max_flow_L_min=delivery_L_min, min_delivery_pressure_bar=low_bar - settings["charge_drop_bar"],
                      charge_pressure_bar=high_bar + settings["charge_drop_bar"])
        return inputs, (model, cylinder, settings, projection, charge)

    def gate_for(self, candidate):
        params, _ = super().gate_for(candidate)
        params["description"] = f"T-2.2f, X={self.roof_mm} mm, recovery={self.variant}. Hydraulic equivalent."
        return params, self.gate.evaluate_cycle(params, self.criteria)

    def evaluate(self, fast=False):
        params, gate = self.gate_for(PUMP)
        ref = {}
        for profile in ("realistic", "pessimistic"):
            if fast:
                _, (model, cylinder, settings, _, _) = self.configuration(PUMP, profile, "base", 90, 100_000)
                cycle = periodic_run(model, cylinder, 90, .64, settings, .0025)
                handover_s = max(0., self.interlocks["switching_windows"]["handover_regen_press"][
                    "modeled_switch_budget_s"] - settings["switch_s"])
                if cycle["feasible"]:
                    cycle["cycle_with_T16_handover_s"] = cycle["cycle_s"] + handover_s
            else:
                cycle = self.run(PUMP, "base", 90, profile, 100_000)
            ref[profile] = {key: cycle[key] for key in (
                "feasible", "reason", "cycle_s", "cycle_with_T16_handover_s", "average_shaft_kW",
                "rms_shaft_kW", "peak_shaft_kW", "peak_working_bar", "motion_events", "stage_events",
                "boost_L_by_motion", "boosted_L", "net_lp_oil_balance_L", "convergence",
                "final_step_delta_s", "convergence_pass", "guard_block_s", "main_travel_mm", "pilot")
                if key in cycle}
        _, (model, cylinder, settings, _, charge) = self.configuration(PUMP, "realistic", "base", 90, 100_000)
        return dict(roof_mm=self.roof_mm, variant=self.variant, cam_mm=self.cam_m * 1000,
                    G_CYCLE_s=gate["value"], G_CYCLE_status=gate["status"],
                    cam_duration_s=self.cam_seconds, unlock_x_mm=settings["unlock_x_m"]*1000,
                    G_CYCLE_RMS_kW=gate["details"]["rms_power_kW"],
                    G_CYCLE_peak_kW=gate["details"]["peak_drive_power_kW"],
                    G_CYCLE_failed_checks=[key for key,val in gate["details"]["checks"].items() if not val],
                    G_DOSE=self.gate.evaluate_dose(params, self.criteria),
                    G_PFACE=self.gate.evaluate_pface(params, self.criteria),
                    reference=ref, geometry=self.trial["geometry"],
                    accumulator_gate=charge, accumulator_gas=settings["accumulator_kwargs"],
                    prefill_checks=self.prefill_checks), params


if __name__ == "__main__":
    for x_mm in (30, 45, 60, 90, 95):
        for variant in RECOVERY:
            study = CandidateStudy(x_mm, variant, cam_m=.012 if x_mm < 90 else 0)
            row, _ = study.evaluate(fast=True)
            ref = row["reference"]["realistic"]
            print(x_mm, variant, round(row["G_CYCLE_s"], 4), row["G_CYCLE_status"],
                  row["G_DOSE"]["status"], round(ref.get("cycle_with_T16_handover_s", 0), 4),
                  flush=True)
