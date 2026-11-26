"""Replay the T-2.1 A4VSO cycle with the T-2.2d die and gate coordinates."""

from copy import deepcopy
from dataclasses import replace
from math import pi
from pathlib import Path
import sys

# Load the T-2.1 cycle copies before importing its study and pilot replay.
from evaluate import configure
from make_params_t14b import make_candidate


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "calc/T-2.1"))
from study import Study
from stack import from_reference


PUMP = "A4VSO180_DFE1Z"


class RoofStudy(Study):
    def __init__(self, roof_mm, transfer, *, adds_local_overtravel):
        super().__init__()
        self.roof_mm = roof_mm
        self.transfer = transfer
        self.local_overtravel_add_mm = roof_mm if adds_local_overtravel else 0
        self.nominal_add_mm = roof_mm + self.local_overtravel_add_mm
        self.trial = deepcopy(self.trial)
        layout = self.trial["geometry"]
        for name in ("gate_face_x_mm", "gate_back_x_mm", "insert_seat_face_x_mm",
                     "channel_exit_x_mm", "punch_face_clear_for_gate_close_x_mm"):
            layout[name] += roof_mm
        for name in ("overtravel_nominal_mm", "overtravel_maximum_mm"):
            layout[name] += self.local_overtravel_add_mm
        for name in ("main_installed_stroke_mm", "punch_face_nominal_eject_end_x_mm",
                     "punch_face_maximum_eject_end_x_mm"):
            layout[name] += self.nominal_add_mm
        self.trial["rapid_mass_increment_kg"] += pi / 4 * (200**2 + 2 * 50**2) * self.nominal_add_mm * 7.85e-6

    def configuration(self, candidate, profile, case, bulk_kg_m3, residual_N, **options):
        inputs, (model, cylinder, settings, projection, charge) = super().configuration(
            candidate, profile, case, bulk_kg_m3, residual_N, **options)
        if self.roof_mm:
            upstream, params, *_ = inputs
            layout = self.trial["geometry"]
            model = replace(model, transfer_m=self.roof_mm / 1000,
                            transfer_drag_N=self.transfer[case][bulk_kg_m3]["nominal"]["push_force_N"])
            settings["unlock_x_m"] = layout["gate_face_x_mm"] / 1000
            stack, _ = from_reference(upstream, layout, model, .50, 5000., case, 2., "nominal")
            model = replace(model, stack_force_N=stack.force_N)
            # G-DOSE has no transfer field. The added forward transfer distance
            # is represented in the total ejection endpoint measured from x=205.
            params["chamber"]["ejection_overtravel_mm"] += self.roof_mm
            params["chamber"]["length_mm"] += self.roof_mm
        return inputs, (model, cylinder, settings, projection, charge)

    def evaluate_roof(self):
        params, cycle_gate = self.gate_for(PUMP)
        params["description"] = (f"T-2.2d, A4VSO180 DFE1Z, roof {self.roof_mm} mm. "
                                 "Hydraulic equivalent for G-CYCLE. Ejection overtravel in "
                                 "G-DOSE is referenced to the original window edge x=205 mm.")
        simulations = {}
        for profile in ("realistic", "pessimistic"):
            result = self.run(PUMP, "base", 90, profile, 100_000)
            simulations[profile] = {name: result[name] for name in (
                "feasible", "reason", "cycle_with_T16_handover_s", "cycle_s", "rms_shaft_kW",
                "peak_shaft_kW", "peak_working_bar", "convergence", "convergence_pass",
                "main_travel_mm", "motion_events", "stage_events") if name in result}
        layout = self.trial["geometry"]
        return dict(roof_mm=self.roof_mm, layout=layout, gate_cycle_s=cycle_gate["value"],
                    gate_status=cycle_gate["status"], gate_rms_kW=cycle_gate["details"]["rms_power_kW"],
                    gate_dose=self.gate.evaluate_dose(params, self.criteria),
                    gate_pface=self.gate.evaluate_pface(params, self.criteria),
                    reference=simulations), params
