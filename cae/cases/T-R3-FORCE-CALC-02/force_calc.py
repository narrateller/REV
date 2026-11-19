"""Per-pose load paths for the dual-cylinder W02 redesign, in N, mm, MPa and bar."""

from collections import Counter
from itertools import product
from math import hypot, pi, sqrt
from pathlib import Path
import json

from contacts import beam_end, contact, deflection, rectangle

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
DESIGN = "cad/force_geometry/redesign_1p5mn"
NATIVE = "cad/source/force_geometry/redesign_1p5mn"
ENVELOPE = "cae/cases/design_boundary_phase_load_envelope/envelope.json"
BASIS = "coordination/tasks/T-R2-DESIGN-BASIS-02/design_basis_registry.json"
PARAMS = "params/r3_force_calc_02.json"
ASSUMED = "CALCULATED_ASSUMED"
BLOCKED = "BLOCKED_INPUTS"
FREE = "NO_STATIC_EQUILIBRIUM"
SEAT = "B_CLOSED_STOP_SEAT"
KEYS = "B_CLOSED_LOCK_BACKED_STOP"
FACE_NAMES = ("Y-", "Y+", "Z-", "Z+")
TIE_SIGNS = tuple(product((-1, 1), repeat=2))


def read(path):
    return json.loads((ROOT / path).read_bytes())


def round_values(item):
    # Keep cross-platform replay stable without changing internal solver tolerances.
    if isinstance(item, float):
        return float(f"{item:.9g}") if abs(item) > 1e-8 else 0.0
    if isinstance(item, dict):
        return {key: round_values(value) for key, value in item.items()}
    if isinstance(item, (list, tuple)):
        return [round_values(value) for value in item]
    return item


def cross(a, b):
    x, y, z = a
    u, v, w = b
    return y * w - z * v, z * u - x * w, x * v - y * u


def resultant(loads):
    forces = [force for _, force in loads]
    moments = [cross(point, force) for point, force in loads]
    return [sum(items) for items in zip(*forces)], [sum(items) for items in zip(*moments)]


def circle(diameter):
    return pi * diameter**2 / 4


def bending_modulus(width, depth):
    return width * depth**2 / 6


def strength(normal, shear, limit):
    equivalent = hypot(normal, sqrt(3) * shear)
    return {"normal_MPa": normal, "shear_MPa": shear, "von_mises_MPa": equivalent,
            "comparison_limit_MPa": limit, "factor": limit / equivalent if equivalent else None}


def euler(load, length, k, inertia, area, elastic_modulus, yield_stress):
    pcr = pi**2 * elastic_modulus * inertia / (k * length)**2
    return {"compression_N": load, "free_length_mm": length, "K": k, "P_cr_N": pcr,
            "compression_over_euler": load / pcr, "KL_over_r": k * length / sqrt(inertia / area),
            "elastic_euler_below_yield": pcr / area < yield_stress}


class W02:
    def __init__(self):
        design = read(f"{DESIGN}/design.json")
        self.c, self.s, self.b, self.l, self.m = (design[key] for key in
                                               ("cylinder", "structure", "receiver", "limits", "materials"))
        self.layout = read(f"{DESIGN}/interfaces.json")["layout"]
        self.native = read(f"{NATIVE}/manifest.json")
        self.r4 = read(f"{NATIVE}/screening.json")
        self.comparison = read(PARAMS)["comparison_values"]
        self.cap, self.rod = circle(self.c["bore"]), circle(self.c["rod"])
        self.annulus = self.cap - self.rod
        self.rail_length = self.s["front_head_x"] - self.s["headThickness"]
        self.grav = self.l["assumed_guide_gravity_per_station_N"]
        self.pad_face = self.s["guide_half_opening"]
        ey, ez = self.l["external_longitudinal_load_eccentricity_yz_mm"]
        self.offsets = tuple(product((-ey, 0, ey), (-ez, 0, ez)))

    def yield_limit(self, material):
        return self.m[material]["assumed_minimum_yield_MPa"]

    def pressure(self, force):
        if not force:
            return None, None
        active, back = (self.cap, self.annulus) if force > 0 else (self.annulus, self.cap)
        port = 10 * (abs(force) + self.l["opposing_port_bar"] / 10 * back) / (
            active * (1 - self.l["cylinder_loss_fraction"]))
        return port, port + self.l["supply_drop_bar"]

    def guide_loads(self, stroke, ey, ez, load, axis, rod_forces, moving):
        s = self.s
        r = s["guide_rear_station_x_at_zero"] + stroke
        span = s["guide_bogie_span"]
        stations = (r, r + span)
        pin_x = self.c["rod_pin_x_at_zero"] + stroke
        pads = []
        mu = self.l["guide_sliding_friction_limit"] if moving else 0.0
        direction = (load > 0) - (load < 0)
        weights = (abs(rod_forces[0]), abs(rod_forces[1]))
        total = sum(weights)
        split = (weights[0] / total, weights[1] / total) if total else (0.5, 0.5)
        fixed_lines = [((s["punch_face_x"] + stroke, ey, ez), (-load, 0, 0))]
        fixed_lines.extend(((x, 0, 0), (0, 0, -self.grav)) for x in stations)
        for _ in range(50):
            drag = sum(axial for _, _, axial, _, _ in pads)
            rods = tuple(force - share * drag for force, share in zip(rod_forces, split))
            lines = fixed_lines + [((pin_x, y, z), (force, 0, 0)) for (y, z), force in zip(axis, rods)]
            # On each active face (normal reaction opposite the face), drag acts at its radial lever.
            friction_lines = [(point, (axial, 0, 0)) for point, _, axial, _, _ in pads]
            _, (_, my, mz) = resultant(lines + friction_lines)
            front_y, front_z = -mz / span, (my - 2 * self.grav * r) / span
            radial = ((-front_y, 2 * self.grav - front_z), (front_y, front_z))
            next_pads = []
            for station, (x, (ny, nz)) in enumerate(zip(stations, radial)):
                for i, normal in enumerate((ny, nz)):
                    if normal:
                        face = i * 2 + int(normal < 0)
                        lever = -self.pad_face if normal > 0 else self.pad_face
                        yz = (lever, 0) if i == 0 else (0, lever)
                        next_pads.append(((x, *yz), normal, -direction * mu * abs(normal), station, FACE_NAMES[face]))
            previous = {(station, name): axial for _, _, axial, station, name in pads}
            current = {(station, name): axial for _, _, axial, station, name in next_pads}
            pads = next_pads
            if max((abs(previous.get(key, 0) - current.get(key, 0))
                    for key in previous.keys() | current.keys()), default=0) < self.comparison["nonlinear_force_tolerance_N"]:
                break
        else:
            raise ValueError("Guide friction did not converge")

        pad_results = {}
        for point, n, axial, station, name in pads:
            vector = (axial, n, 0) if name[0] == "Y" else (axial, 0, n)
            lines.append((point, vector))
            pressure = abs(n) / (s["guide_pad_width"] * s["guide_pad_length"])
            pad_results[f"{name}_{station + 1}"] = [point, vector, pressure]
        return rods, stations, pad_results, resultant(lines)

    def rail_loads(self, stations, pads, stroke, fixed):
        s = self.s
        ei = self.m["E_MPa"] * s["guide_beam_width"] * s["guide_beam_radial_depth"]**3 / 12
        relative = [x - s["headThickness"] for x in stations]
        displacements = [[None, None] for _ in stations]
        ends = {name: [[0.0] * 3 for _ in range(4)] for name in FACE_NAMES}
        for label, (point, (fx, fy, fz), _) in pads.items():
            face, idx = label.split("_")
            index = int(idx) - 1
            a = relative[index]
            scalar = -fy if face[0] == "Y" else -fz
            rear, front, rear_m, front_m = beam_end(scalar, a, self.rail_length, fixed)
            for j, value in enumerate((rear, front)):
                ends[face][j][0] -= fx * ((1 - a / self.rail_length) if j == 0 else a / self.rail_length)
                ends[face][j][1 if face[0] == "Y" else 2] += value
            ends[face][2][2 if face[0] == "Y" else 1] += rear_m if face[0] == "Y" else -rear_m
            ends[face][3][2 if face[0] == "Y" else 1] += front_m if face[0] == "Y" else -front_m
            axis = 0 if face[0] == "Y" else 1
            sign = -1 if scalar < 0 else 1
            displacements[index][axis] = sign * s["guide_running_gap"] + sum(
                deflection(-peer[1][axis + 1], peer[0][0] - s["headThickness"], a, self.rail_length, ei, fixed)
                for key, peer in pads.items() if key.startswith(face + "_"))

        # A direction with no contact lies within the gap. Use both limits to bound position.
        x_restrict = min(s["punch_face_x"] + stroke, s["chamber_entry_x"] + s["chamber_length"])
        t = (x_restrict - stations[0]) / (stations[1] - stations[0])
        choices = lambda value: (-s["guide_running_gap"], s["guide_running_gap"]) if value is None else (value,)
        def bounds(axis, ratio):
            return max(abs((1 - ratio) * a + ratio * b)
                       for a, b in product(*(choices(row[axis]) for row in displacements)))

        lower_contact = max(s["chamber_entry_x"], s["crosshead_rear_x"] + stroke)
        x_values = (lower_contact, x_restrict)
        maximum = [max(bounds(axis, (x - stations[0]) / (stations[1] - stations[0])) for x in x_values)
                   for axis in range(2)] if lower_contact <= x_restrict else [0, 0]
        return {"end_loads": {face: data for face, data in ends.items() if any(any(v) for v in data)},
                "station_displacement_yz_mm": displacements,
                "tip_at_restriction_abs_yz_mm": [bounds(i, t) for i in range(2)],
                "max_in_chamber_abs_yz_mm": maximum,
                "chamber_clearance_remaining_mm": s["chamber_radial_clearance"] - max(maximum)}

    def frame(self, axis, rods, load, ey, ez, stations, rails):
        c, s = self.c, self.s
        rear, front = s["headThickness"], s["front_head_x"]
        frame_loads = [((c["rear_pin_x"], y, z), (-force, 0, 0)) for (y, z), force in zip(axis, rods)]
        frame_loads.append(((front, ey, ez), (load, 0, 0)))
        rear_count = len(frame_loads)
        rear_couple, front_couple = [0.0] * 3, [0.0] * 3
        for face, (ra, rb, ma, mb) in rails["end_loads"].items():
            yz = [0, 0]
            yz[0 if face[0] == "Y" else 1] = self.pad_face * (-1 if face[-1] == "-" else 1)
            frame_loads.extend((((rear, *yz), ra), ((front, *yz), rb)))
            rear_couple = [a + b for a, b in zip(rear_couple, ma)]
            front_couple = [a + b for a, b in zip(front_couple, mb)]
        # A global balancing gravity resultant, with no assignment to actual anchors.
        frame_loads.extend(((x, 0, 0), (0, 0, self.grav)) for x in stations)
        rf, rm = resultant(frame_loads)
        rm = [a + b + d for a, b, d in zip(rm, rear_couple, front_couple)]
        rear_loads = [frame_loads[0], frame_loads[1], *frame_loads[rear_count:-2:2]]
        front_loads = [frame_loads[2], *frame_loads[rear_count + 1:-2:2]]
        head_demands = {}
        tie_sets = []
        tie_arm = s["tie_axis_offset"]
        for label, end, entries, couples, sign in (("rear", rear, rear_loads, rear_couple, 1),
                                                    ("front", front, front_loads, front_couple, -1)):
            f, m = resultant([((x - end, y, z), vector) for (x, y, z), vector in entries])
            m = [a + b for a, b in zip(m, couples)]
            ties = [sign * (-f[0] / 4 - m[1] * sz / (4 * tie_arm) + m[2] * sy / (4 * tie_arm))
                    for sy, sz in TIE_SIGNS]
            tie_sets.extend(ties)
            head_demands[label] = {"force_xyz_N": f, "moment_xyz_Nmm": m, "tie_axial_demands_N": ties}
        return {"balance": [rf, rm], "heads": head_demands, "tie_abs_max_N": max(map(abs, tie_sets)),
                "tie_compression_max_N": max(0, -min(tie_sets))}

    def structural(self, rods, stroke, f, ey, ez, axis, frame, pads, rails):
        c, s = self.c, self.s
        alloy = self.yield_limit("pins_and_rod")
        steel = self.yield_limit("structure")
        block = self.yield_limit("head")
        qt = self.yield_limit("quenched_alloy")
        pin = c["pin_diameter"]
        eye, ear = c["rod_eye_width"], c["clevis_ear_thickness"]
        pin_span = eye + 2 * c["clevis_side_gap"] + ear
        maximum = max(map(abs, rods))
        arm_y = f * ey - sum(rod * y for rod, (y, _) in zip(rods, axis))
        arm_z = f * ez - sum(rod * z for rod, (_, z) in zip(rods, axis))
        axial = max(abs(f), abs(sum(rods)))
        crosshead_m = axial * c["axis_offset"] / 2 + abs(arm_y) + abs(arm_z)
        strip = s["crosshead_effective_bending_width"]
        thickness = s["crosshead_thickness"]
        width, height = s["punch_yz"]
        strength_results = {
            "rod_1": strength(-rods[0] / self.rod, 0, alloy),
            "rod_2": strength(-rods[1] / self.rod, 0, alloy),
            "crosshead_strip": strength(crosshead_m / bending_modulus(strip, thickness),
                                        1.5 * axial / (strip * thickness), block),
            "clevis_pin": strength(maximum * pin_span / (4 * (pi * pin**3 / 32)),
                                   maximum / (2 * circle(pin)), alloy),
            "eye_bearing": strength(maximum / (pin * eye), 0, alloy),
            "clevis_bearing": strength(maximum / (2 * pin * ear), 0, steel),
            "eye_tearout": strength(0, maximum / (2 * (c["eye_radius"] - pin / 2) * eye), alloy),
            "clevis_ear_tearout": strength(0, maximum / (4 * 50 * ear), steel),
            "frame_tie_stud": strength(frame["tie_abs_max_N"] / circle(s["tie_stud_root"]), 0, qt),
            "punch_combined": strength(abs(f) * (1 / (width * height) +
                                      abs(ey) / bending_modulus(height, width) +
                                      abs(ez) / bending_modulus(width, height)), 0, qt),
        }
        n = max((max(abs(vector[1]), abs(vector[2])) for _, vector, _ in pads.values()), default=0)
        pad_pressure = n / (s["guide_pad_width"] * s["guide_pad_length"])
        max_radial_end = max((max(hypot(*a[1:]), hypot(*b[1:]))
                              for a, b, _, _ in rails["end_loads"].values()), default=0)
        dowels = s["guide_beam_end_pin_count"]
        end_pin = s["guide_beam_end_pin_diameter"]
        strength_results.update({
            "guide_end_dowels": strength(0, max_radial_end / (dowels * circle(end_pin)), alloy),
            "guide_pad": strength(pad_pressure, 0, self.m["guide_pad"]["assumed_maximum_contact_pressure_MPa"]),
        })
        if f < 0:
            by, bz = s["punch_collar_tie_offsets_yz"]
            n_tie = max(abs(f) * (1 + sy * ey / by + sz * ez / bz) / 4 for sy, sz in TIE_SIGNS)
            root = s["punch_collar_tie_root"]
            strength_results["punch_collar_tie"] = strength(n_tie / circle(root), 0, self.yield_limit("bolt"))
            strength_results["punch_collar_thread_strip"] = strength(
                0, n_tie / (0.5 * pi * root * s["punch_bolt_engagement"]), qt)
        if f > 0:
            collar_area = s["punch_shoulder_yz"][0] * s["punch_shoulder_yz"][1] - width * height
            strength_results["collar_seat_nominal"] = strength(f / collar_area, 0, block)

        e = self.m["E_MPa"]
        free = c["rod_pin_x_at_zero"] + stroke - c["barrel_end_x"]
        rod_i = pi * c["rod"]**4 / 64
        stability = {f"rod_{index + 1}": [euler(load, free, k, rod_i, self.rod, e, alloy) for k in (1, 2)]
                     for index, load in enumerate(rods) if load > 0}
        if f > 0:
            punch_free = s["punch_face_x"] - s["crosshead_rear_x"] - s["crosshead_thickness"]
            stability["punch"] = [euler(f, punch_free, 2, min(width * height**3, height * width**3) / 12,
                                        width * height, e, qt)]
        if frame["tie_compression_max_N"]:
            side = s["tie_square"]
            stability["frame_tie"] = [euler(frame["tie_compression_max_N"], self.rail_length, 1,
                                           side**4 / 12, side**2, e, steel)]
        return strength_results, stability

    def receiver(self, path, f, ey, ez):
        b = self.b
        if path not in (SEAT, KEYS) or not f:
            return None
        if path == SEAT:
            inner, outer, height = b["seat_inner_y"], b["gate_width"] / 2, b["gate_height"]
        else:
            inner, outer, height = b["key_inner_y"], b["key_inner_y"] + b["key_width"], b["key_height"]
        parts = contact((rectangle(-outer, -inner, height), rectangle(inner, outer, height)), ey, ez, f)
        peak = max(part["peak_MPa"] for part in parts)
        bound = self.yield_limit("head")
        support_span = inner + outer
        gate_h, gate_t = b["gate_height"], b["gate_thickness"]
        bending = f * support_span / (4 * bending_modulus(gate_h, gate_t))
        bending += f * abs(ez) / bending_modulus(gate_t, gate_h)
        gate = strength(bending, 1.5 * f / (gate_h * gate_t), self.yield_limit("quenched_alloy"))
        return {"path": path, "parts_negative_positive_y": parts, "peak_MPa": peak, "limit_MPa": bound,
                "factor": bound / peak, "gate_section": gate}

    def sample(self, variant, path, stroke, f, ey, ez, base_rods, moving=False):
        axis = self.layout[variant.split("-")[1]]["cylinder_axis_yz_mm"]
        rods, stations, pads, moving_balance = self.guide_loads(stroke, ey, ez, f, axis, base_rods, moving)
        pinned = self.rail_loads(stations, pads, stroke, False)
        fixed = self.rail_loads(stations, pads, stroke, True)
        frame_pinned = self.frame(axis, rods, f, ey, ez, stations, pinned)
        frame_fixed = self.frame(axis, rods, f, ey, ez, stations, fixed)
        strengths, stability = self.structural(rods, stroke, f, ey, ez, axis, frame_pinned, pads, pinned)
        strengths_fixed, stability_fixed = self.structural(rods, stroke, f, ey, ez, axis, frame_fixed, pads, fixed)
        for key in strengths.keys():
            if strengths[key]["factor"] is not None and strengths_fixed[key]["factor"] < strengths[key]["factor"]:
                strengths[key] = strengths_fixed[key]
        if "frame_tie" in stability_fixed and stability_fixed["frame_tie"][0]["compression_N"] > (
                stability.get("frame_tie", [{"compression_N": 0}])[0]["compression_N"]):
            stability["frame_tie"] = stability_fixed["frame_tie"]
        receiver = self.receiver(path, f, ey, ez)
        if receiver:
            strengths["receiver_contact"] = strength(receiver["peak_MPa"], 0, receiver["limit_MPa"])
            strengths["receiver_gate"] = receiver["gate_section"]
        clearance = min(pinned["chamber_clearance_remaining_mm"], fixed["chamber_clearance_remaining_mm"])
        compatibility = {"status": "GUIDE_ONLY_GAP_OPEN"}
        if clearance <= 0:
            compatibility = {"status": "CHAMBER_RECONTACT_REQUIRED", "redistribution": None,
                             "reason": "Guide-only static trial closes the punch/chamber gap. "
                                       "Full reactions require a coupled guide/chamber contact solve."}
        return {"path": path, "stroke_mm": stroke, "force_N": f, "eccentricity_yz_mm": [ey, ez],
                "branch_forces_N": rods, "pressure_port_and_supply_bar": [self.pressure(rod) for rod in rods],
                "moving_balance": moving_balance, "guide_pad_columns": pads,
                "pin_and_mount_reaction_N": [-rod for rod in rods], "axial_reaction_on_frame_N": f,
                "axial_path_reactions_N": {"B_gate": f if receiver else 0,
                                           "B_seats": f if path == SEAT else 0,
                                           "B_keys": f if path == KEYS else 0,
                                           "other_named_path": 0 if receiver else f},
                "frame_PIN_PIN": frame_pinned, "frame_FIXED_FIXED": frame_fixed,
                "rails_PIN_PIN": pinned, "rails_FIXED_FIXED": fixed, "section_4_strength": strengths,
                "section_5_stability": stability, "section_6_receiver": receiver, "contact_compatibility": compatibility}


def extrema(rows):
    pressure = []
    strength_values = []
    euler_values = []
    clearances = []
    balance = [0.0, 0.0]
    for i, row in enumerate(rows, 1):
        if row["status"] == FREE:
            continue
        if row["mode"] != "PRESSURE_BOUND":
            pressure.extend((supply, i, branch) for branch, (_, supply) in enumerate(
                row["pressure_port_and_supply_bar"], 1) if supply is not None)
        strength_values.extend((data["factor"], i, key) for key, data in row["section_4_strength"].items()
                               if data["factor"] is not None)
        euler_values.extend((data["compression_over_euler"], i, key, data["K"])
                            for key, modes in row["section_5_stability"].items() for data in modes)
        clearances.append((row["rails_PIN_PIN"]["chamber_clearance_remaining_mm"], i))
        clearances.append((row["rails_FIXED_FIXED"]["chamber_clearance_remaining_mm"], i))
        for groups in (row["moving_balance"], row["frame_PIN_PIN"]["balance"], row["frame_FIXED_FIXED"]["balance"]):
            balance = [max(old, max(map(abs, values))) for old, values in zip(balance, groups)]
    return {
        "max_required_supply_bar_row_branch": max(pressure, default=None),
        "min_strength_factor_row_component": min(strength_values, default=None),
        "max_compression_over_euler_row_component_K": max(euler_values, default=None),
        "min_punch_chamber_gap_mm_row": min(clearances, default=None),
        "max_balance_residual_N_and_Nmm": balance,
    }


def case_samples(model, case):
    c, s = model.c, model.s
    variant = case["variant"]
    poses = [c["rear_reserve"] + 1000 * q for q in case["pose_samples_q_m"]]
    for axial in case["axial_samples"]:
        name, f = axial["sample"], axial["F_x_N"]
        if not f:
            # Still check gravity and clearance at each q. There is no longitudinal restraint.
            for stroke in poses:
                yield {"status": ASSUMED, "mode": "ZERO_GRAVITY_ONLY", "sample": name,
                       **model.sample(variant, "AXIALLY_FREE", stroke, f, 0, 0, (0, 0))}
            continue
        for stroke in poses:
            yield {"status": FREE, "mode": "AXIAL_RELEASE", "sample": name, "stroke_mm": stroke,
                   "path": "AXIALLY_FREE", "force_N": f, "unbalanced_axial_force_N": f,
                   "sections_4_5_6": {"value": None, "reason": "No axial reaction branch with nonzero net force."}}
            for path, (ey, ez), moving in product(axial["held_axial_paths"], model.offsets, (False, True)):
                row = model.sample(variant, path, stroke, f, ey, ez, (f / 2, f / 2), moving)
                yield {"status": ASSUMED, "mode": "SLIDING_LIMIT" if moving else "STATIC_HOLD",
                       "sample": name, **row}


def pressure_samples(model):
    c = model.c
    high = model.l["supply_bar"][1]
    cap, annulus = model.cap * high / 10, model.annulus * high / 10
    work_limit = model.r4["stroke"]["B_closed_work_limit_stroke_mm"]
    operative = model.r4["stroke"]["operating_range_mm"]
    modes = {
        "SYMMETRIC_EXTENSION": ([cap, cap], [[high, 0], [high, 0]]),
        "SYMMETRIC_RETRACTION": ([-annulus, -annulus], [[0, high], [0, high]]),
        "BRANCH_1_EXTENSION": ([cap, 0], [[high, 0], [0, 0]]),
        "BRANCH_2_EXTENSION": ([0, cap], [[0, 0], [high, 0]]),
        "BRANCH_1_RETRACTION": ([-annulus, 0], [[0, high], [0, 0]]),
        "BRANCH_2_RETRACTION": ([0, -annulus], [[0, 0], [0, high]]),
        "OPPOSED_BRANCH_1_PUSH": ([cap, -annulus], [[high, 0], [0, high]]),
        "OPPOSED_BRANCH_2_PUSH": ([-annulus, cap], [[0, high], [high, 0]]),
    }
    for variant, (name, (rods, ports)), (ey, ez) in product(model.native["variants"], modes.items(), model.offsets):
        f = sum(rods)
        paths = {"INDEPENDENT_BENCH_FIXTURE": sorted({0, *operative, c["stroke"]})}
        if variant.startswith("B") and f > 0:
            paths.update({path: [operative[0], work_limit] for path in (SEAT, KEYS)})
        for path, strokes in paths.items():
            for stroke in strokes:
                row = model.sample(variant, path, stroke, f, ey, ez, rods)
                # These are prescribed trapped port pressures, without supply drop or credits for losses.
                del row["pressure_port_and_supply_bar"]
                yield {"status": ASSUMED, "mode": "PRESSURE_BOUND", "variant": variant, "sample": name,
                       "ports_cap_annulus_bar": ports, **row}


def single_branch(model, cases):
    output = {}
    for case_id, case in cases.items():
        for axial in case["axial_samples"]:
            if axial["sample"] != "REVERSE_WORK":
                continue
            f = axial["F_x_N"]
            checks = []
            for q, (ey, ez), i in product(case["pose_samples_q_m"], model.offsets, (0, 1)):
                rods = [0, 0]
                rods[i] = f
                stroke = model.c["rear_reserve"] + 1000 * q
                axis = model.layout[case["variant"].split("-")[1]]["cylinder_axis_yz_mm"]
                forces, *_ = model.guide_loads(stroke, ey, ez, f, axis, rods, True)
                checks.append((model.pressure(forces[i])[1], stroke, [ey, ez], i + 1))
            peak = max(checks)
            output[case_id] = {"peak_supply_bar_stroke_yz_branch": peak, "force_N": f,
                               "status": "EXCEEDS_PORT_LIMIT" if peak[0] - model.l["supply_drop_bar"] >
                               model.l["supply_bar"][1] else "WITHIN_PORT_LIMIT",
                               "reverse_holding": {"value": None, "reason": "Only the envelope fixture holds reverse load. "
                                                   "Hydraulic lock, isolation and installed retention are undefined."}}
    return output


def drives(model, cases, summaries):
    basis = read(BASIS)["parameters"]
    flow = model.comparison["reference_flow_L_min"]
    power = basis["DB-MAIN-POWER"]["value"]
    time = basis["DB-CYCLE-TIME"]["value"]
    phases = {}
    for case_id, case in cases.items():
        rows = summaries[case_id]
        excursion = (max(case["pose_samples_q_m"]) - min(case["pose_samples_q_m"])) * 1000
        phases[case_id] = []
        for axial in case["axial_samples"]:
            name, f = axial["sample"], axial["F_x_N"]
            if not f:
                continue
            moving = [row for row in rows if row["sample"] == name and row["mode"] == "SLIDING_LIMIT"]
            pressure = max(max(entry[1] for entry in row["pressure_port_and_supply_bar"]) for row in moving)
            area = 2 * (model.cap if f > 0 else model.annulus)
            volume = area * excursion / 1e6
            hydraulic_kJ = pressure * volume / 10
            phases[case_id].append({"sample": name, "constant_external_force_N": f, "sampled_excursion_mm": excursion,
                                    "swept_volume_L": volume, "supply_pressure_bar": pressure,
                                    "supply_power_kW_at_reference_flow": pressure * flow / 600,
                                    "mechanical_work_kJ_constant_force": abs(f) * excursion / 1e6,
                                    "supply_work_kJ_over_excursion": hydraulic_kJ,
                                    "flow_limited_time_s": 60 * volume / flow,
                                    "power_limited_time_s": hydraulic_kJ / (power / 1000),
                                    "dwell_and_other_consumers": {"value": None, "reason": "No phase motion or valve data."}})
    w, h = model.s["punch_yz"]
    yw, zh = model.s["product_yz"]
    travel = max(q for case in cases.values() for q in case["pose_samples_q_m"])
    travel_volume = 2 * (model.cap + model.annulus) * travel / 1000
    return {
        "phase_values": phases, "reference_power_W": power, "reference_cycle_s": time, "reference_flow_L_min": flow,
        "reference_energy_kJ_per_cycle": power * time / 1000,
        "full_envelope_round_trip_L": travel_volume, "full_envelope_round_trip_s_at_reference_flow": travel_volume * 60 / flow,
        "round_trip_required_flow_L_min_for_reference_cycle": travel_volume * 60 / time,
        "transition_die": {
            "punch_area_mm2": w * h, "product_area_mm2": yw * zh,
            "punch_to_product_area_ratio": w * h / (yw * zh),
            "passage_mm": [w + 2 * model.s["chamber_radial_clearance"], h + 2 * model.s["chamber_radial_clearance"]],
            "nominal_1p5MN_mean_punch_face_MPa": model.l["nominal_force_N"] / (w * h),
            "nominal_1p5MN_force_per_product_area_MPa": model.l["nominal_force_N"] / (yw * zh),
            "actual_die_pressure_flow_friction_and_energy": {"value": None, "reason": "No compaction/extrusion law or material BC."},
        },
    }
