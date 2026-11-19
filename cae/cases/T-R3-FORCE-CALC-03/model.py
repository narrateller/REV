"""W02 revision 02 load-path model and B receiver fit checks."""

from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
PARENT = PACKAGE.with_name("T-R3-FORCE-CALC-02")
R4 = ROOT / "cad/force_geometry/redesign_1p5mn_02"
OVERLAY = "cad/force_geometry/redesign_1p5mn_02/interfaces.json"

sys.path.insert(0, str(PARENT))
from force_calc import KEYS, SEAT, W02, bending_modulus, read, strength
from contacts import contact
from verify_output import check_analytical_limits, check_inputs, check_row, close, require

sys.path.insert(0, str(R4))
from screen_contact import contact_faces, geometry, sensitivity


class Iteration02(W02):
    def __init__(self):
        super().__init__()
        _, design, self.dataset = geometry()
        self.overlay = read(OVERLAY)
        self.b = design["receiver"]
        self.b_die_entry_x = design["structure"]["die_entry_B_x"]
        self.fit = self.dataset["fit"]
        self.faces = {
            path: contact_faces(self.b, self.fit["per_edge_contact_exclusion"], path == SEAT)
            for path in (KEYS, SEAT)
        }

    def contact_limit(self, path):
        parts = ("ReceiverGate", "ReceiverSeat") if path == SEAT else (
            "ReceiverGate", "ReceiverLock", "LockBacking", "ReactionFrameHead")
        return min(self.yield_limit(self.dataset["material_refs"][part]) for part in parts)

    def receiver(self, path, f, ey, ez):
        if path not in self.faces or not f:
            return None
        parts = contact(self.faces[path], ey, ez, f)
        peak = max(part["peak_MPa"] for part in parts)
        limit = self.contact_limit(path)
        h, t = self.b["gate_height"], self.b["gate_thickness"]
        outer = max(abs(y) for face in self.faces[path] for y, _ in face)
        outer += self.fit["per_edge_contact_exclusion"]
        bending = f * outer / (2 * bending_modulus(h, t)) + f * abs(ez) / bending_modulus(t, h)
        return {"path": path, "parts_negative_positive_y": parts, "peak_MPa": peak, "limit_MPa": limit,
                "factor": limit / peak, "gate_section": strength(
                    bending, 1.5 * f / (h * t), self.yield_limit(self.dataset["material_refs"]["ReceiverGate"]))}

    def sample(self, variant, path, stroke, f, ey, ez, base_rods, moving=False):
        require(path not in self.faces or variant in self.overlay["applies_to"], "B path on a non-B variant")
        row = super().sample(variant, path, stroke, f, ey, ez, base_rods, moving)
        die = self.b_die_entry_x if variant in self.overlay["applies_to"] else self.s["die_entry_A_x"]
        row["punch_to_die_inlet_mm"] = die - self.s["punch_face_x"] - stroke
        return row

    def fit_at_pressure_limit(self):
        b, s, fit = self.b, self.s, self.fit
        pressure = self.l["supply_bar"][1]
        force = self.c["quantity"] * self.cap * pressure / 10
        gap = b["gate_to_seat_axial_gap"] - b["gate_to_key_axial_gap"] - b["key_to_backing_axial_gap"]
        gap -= 3 * fit["running_gap_stack_per_interface"]
        close(gap, fit["minimum_keys_only_seat_gap_after_take_up"], "Axial gap stack")
        stack = (s["headThickness"] + b["reaction_head_boss_projection"] + s["front_head_x"]
                 - s["chamber_entry_x"] - s["chamber_length"])
        stiffness = self.m["E_MPa"] / stack
        paths = {}
        for path, faces in self.faces.items():
            obstacles = tuple(point for face in contact_faces(b, 0, True) for point in face) if path == KEYS else ()
            sweep = sensitivity(faces, self.offsets, force, stiffness, fit, obstacles)
            # The solver verifies unrounded force and moment residuals at every sample.
            del sweep["max_force_and_first_moment_residuals_N_Nmm"]
            peak = max(row["peak_MPa"] for row in sweep["worst_by_eccentricity"])
            paths[path] = {**sweep, "effective_faces_yz_mm": faces, "peak_MPa": peak,
                           "comparison_limit_MPa": self.contact_limit(path),
                           "factor": self.contact_limit(path) / peak}
        approach = paths[KEYS]["worst_approach_at_seat_mm"]["approach_mm"]
        return {"cap_bar": pressure, "return_bar": 0, "force_N": force, "paths": paths,
                "initial_seat_clearance_after_take_up_mm": gap,
                "remaining_seat_clearance_mm": gap - approach,
                "minimum_key_running_gap_mm": min(b["gate_to_key_axial_gap"], b["key_to_backing_axial_gap"])
                - fit["running_gap_stack_per_interface"],
                "effective_key_registration_margin_mm": fit["per_edge_contact_exclusion"]
                - b["key_edge_chamfer"] - fit["installed_key_registration_yz"]}
