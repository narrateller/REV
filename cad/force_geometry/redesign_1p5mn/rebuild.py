"""Build, exercise and save editable W02 assemblies using FreeCAD's Python."""

import argparse
from hashlib import sha256
from itertools import combinations, product
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

# The Windows distribution keeps its loadable modules alongside its bundled Python.
sys.path.insert(0, str(Path(sys.executable).resolve().parent))
import FreeCAD as App
import Part

from calculate import ENVELOPE, HERE, RESULT, ROOT, encode, read, sizing

sys.path.insert(0, str(ROOT))
from drawings.W02.redesign_1p5mn.prepare import prepare

V = App.Vector
X = V(1, 0, 0)
Z = V(0, 0, 1)
GAP_VOLUME_TOLERANCE_MM3 = 0.1
VARIANTS = ("A-V1", "A-V2", "B-V1", "B-V2")
TASK = ROOT / "coordination/tasks/T-R4-REDESIGN-1.5MN-01"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def box(x1, x2, y1, y2, z1, z2):
    return Part.makeBox(x2 - x1, y2 - y1, z2 - z1, V(x1, y1, z1))


def centered_box(x1, x2, width, height):
    return box(x1, x2, -width / 2, width / 2, -height / 2, height / 2)


def shaft(radius, x1, x2, y, z):
    return Part.makeCylinder(radius, x2 - x1, V(x1, y, z), X)


def transverse_pin(radius, x, y, z1, z2):
    return Part.makeCylinder(radius, z2 - z1, V(x, y, z1), Z)


def rect_wire(x, width, height):
    p = [V(x, y * width / 2, z * height / 2) for y, z in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    return Part.makePolygon([*p, p[0]])


def tunnel(x1, x2, outside, inside):
    return centered_box(x1, x2, *outside).cut(centered_box(x1 - 1, x2 + 1, *inside))


def face_strip(x1, x2, inner, outer, width, face, tangent=0):
    axis, sign = face
    a, b = sorted((sign * inner, sign * outer))
    t1, t2 = tangent - width / 2, tangent + width / 2
    return box(x1, x2, a, b, t1, t2) if axis == "Y" else box(x1, x2, t1, t2, a, b)


class Assembly:
    def __init__(self, variant, design, runtime, versions):
        self.doc = App.newDocument(variant.replace("-", "_"))
        self.doc.Label = f"W02 {variant} | 1.5 MN | Design basis"
        self.c, self.s, self.b = (design[k] for k in ("cylinder", "structure", "receiver"))
        self.variant = variant
        self.design = design
        self.groups = {}
        self.items = {}
        self.meta = self.doc.addObject("App::FeaturePython", "Design")
        self.meta.Label = "W02 design basis and assembly pose"
        for name, value in (
            ("StrokePosition", self.c["rear_reserve"]), ("RatedStroke", self.c["stroke"]),
            ("BoreDiameter", self.c["bore"]), ("RodDiameter", self.c["rod"]),
            ("GuideStationCenterDistance", self.s["guide_bogie_span"]),
            ("GateLift", 0), ("LockDrop", 0),
        ):
            self.meta.addProperty("App::PropertyLength", name, "W02 dimensions")
            setattr(self.meta, name, value)
        for name, value in (
            ("Revision", design["id"] + " r" + str(design["revision"])),
            ("VariantID", variant), ("Scope", design["scope"]), ("UnitsNote", "Solid coordinates in mm"),
            ("CodexSessionID", runtime["CODEX_SESSION_ID"]), ("CodexModel", runtime["model_label"]),
            ("FreeCADRuntime", versions["FreeCAD"]), ("OpenCASCADE", versions["OpenCASCADE"]),
        ):
            self.meta.addProperty("App::PropertyString", name, "W02 provenance")
            setattr(self.meta, name, value)
            self.meta.setEditorMode(name, 1)

    def add(self, group, name, shape, bom, label, movement=None):
        require(shape.isValid() and len(shape.Solids) == 1 and shape.Volume > 0,
                f"{self.variant} invalid solid {name}")
        if group not in self.groups:
            self.groups[group] = self.doc.addObject("App::DocumentObjectGroup", group)
        obj = self.doc.addObject("Part::Feature", name)
        obj.Label = label
        obj.Shape = shape
        obj.addProperty("App::PropertyString", "BOMItem", "W02 traceability")
        obj.BOMItem = bom
        self.groups[group].addObject(obj)
        if movement:
            axis, expression = movement
            obj.setExpression(f"Placement.Base.{axis}", expression)
        self.items[name] = (obj, group)
        return obj

    def fixed(self, *args):
        return self.add(*args)

    def moving(self, group, name, shape, bom, label):
        return self.add(group, name, shape, bom, label, ("x", "Design.StrokePosition"))

    def frame(self):
        c, s = self.c, self.s
        t, front = s["headThickness"], s["front_head_x"]
        outside = front + t
        side, tie_p = s["head_side"], s["tie_axis_offset"]
        tie_half = s["tie_square"] / 2
        stud = s["tie_stud_nominal_diameter"] / 2
        nut = s["tie_nut_length"]
        tie_points = list(product((-tie_p, tie_p), repeat=2))
        face_names = (("Y", -1), ("Y", 1), ("Z", -1), ("Z", 1))
        guide_in, guide_depth = s["guide_half_opening"], s["guide_beam_radial_depth"]
        end_depth = s["guide_beam_end_pin_engagement"]
        dowel_r = s["guide_beam_end_pin_diameter"] / 2
        dowel_centers = []
        for axis, sign in face_names:
            for radial, tangent in product((100, guide_depth - 100), (-120, 120)):
                signed = sign * (guide_in + radial)
                dowel_centers.append((signed, tangent) if axis == "Y" else (tangent, signed))
        heads = [centered_box(0, t, side, side), centered_box(front, outside, side, side)]
        outlet = [dim + 2 * s["die_exit_clearance"] for dim in s["product_yz"]]
        heads[1] = heads[1].cut(centered_box(front - 1, outside + 1, *outlet))
        for index, (lo, hi) in enumerate(((0, t), (front, outside))):
            for y, z in tie_points:
                heads[index] = heads[index].cut(shaft(stud, lo - 1, hi + 1, y, z))
            end_lo, end_hi = (hi - end_depth, hi + 1) if index == 0 else (lo - 1, lo + end_depth)
            for y, z in dowel_centers:
                heads[index] = heads[index].cut(shaft(dowel_r, end_lo, end_hi, y, z))
        for name, shape, code in zip(("RearFrameHead", "ReactionFrameHead"), heads, ("W02-101", "W02-102")):
            self.fixed("Frame", name, shape, code, name)
        for i, (y, z) in enumerate(tie_points, 1):
            tie = box(t, front, y - tie_half, y + tie_half, z - tie_half, z + tie_half)
            for a, b in ((-nut, t), (front, outside + nut)):
                tie = tie.fuse(shaft(stud, a, b, y, z))
            self.fixed("Frame", f"TieBar{i}", tie, "W02-103", "Square frame tie with axial threaded ends")
            nut_half = s["tie_nut_across_envelope"] / 2
            for end, (a, b) in enumerate(((-nut, 0), (outside, outside + nut)), 1):
                shape = box(a, b, y - nut_half, y + nut_half, z - nut_half, z + nut_half)
                self.fixed("Frame", f"TieNut{i}_{end}", shape.cut(shaft(stud, a - 1, b + 1, y, z)),
                           "W02-104", "Captured frame tie nut")
        for i, face in enumerate(face_names, 1):
            rail = face_strip(t, front, guide_in, guide_in + guide_depth, s["guide_beam_width"], face)
            for j, (y, z) in enumerate(dowel_centers[(i - 1) * 4:i * 4], 1):
                rail = rail.cut(shaft(dowel_r, t - 1, t + end_depth, y, z))
                rail = rail.cut(shaft(dowel_r, front - end_depth, front + 1, y, z))
                for k, end in enumerate((t, front), 1):
                    shape = shaft(dowel_r, end - end_depth, end + end_depth, y, z)
                    self.fixed("Frame", f"GuideDowel{i}_{j}_{k}", shape, "W02-106", "Fitted guide beam end dowel")
            self.fixed("Frame", f"GuideBeam{i}", rail, "W02-105", "Machined box-way reaction beam")

    def drives(self):
        c, s = self.c, self.s
        pin_r = c["pin_diameter"] / 2
        eye_half = c["rod_eye_width"] / 2
        plate_in = eye_half + c["clevis_side_gap"]
        plate_out = plate_in + c["clevis_ear_thickness"]
        for sign in (-1, 1):
            i = 1 if sign < 0 else 2
            offset = sign * c["axis_offset"]
            y, z = (0, offset) if self.variant.endswith("V1") else (offset, 0)

            def eye(x):
                return transverse_pin(c["eye_radius"], x, y, z - eye_half, z + eye_half).cut(
                    transverse_pin(pin_r, x, y, z - eye_half - 1, z + eye_half + 1))

            rear_x, rod_x = c["rear_pin_x"], c["rod_pin_x_at_zero"]
            start, stop, gland = c["barrel_start_x"], c["barrel_end_x"], c["gland_start_x"]
            bore, rod = c["bore"] / 2, c["rod"] / 2
            barrel = shaft(c["barrel_od"] / 2, start, stop, y, z).cut(shaft(bore, start - 1, stop + 1, y, z))
            self.fixed("FixedActuators", f"CylinderBarrel{i}", barrel, "W02-201", "Mill cylinder barrel envelope")
            cap = shaft(bore, start, c["piston_x_at_zero"] - 5, y, z)
            cap = cap.fuse(shaft(55, rear_x + pin_r + 5, start + 3, y, z)).fuse(eye(rear_x))
            self.fixed("FixedActuators", f"CylinderRearEye{i}", cap, "W02-201", "Base cap and mount eye")
            ring = shaft(bore, gland, stop, y, z).cut(shaft(rod + 0.5, gland - 1, stop + 1, y, z))
            self.fixed("FixedActuators", f"CylinderGland{i}", ring, "W02-201", "Rod gland envelope")
            piston_x = c["piston_x_at_zero"]
            piston = shaft(bore - 0.5, piston_x, piston_x + c["piston_length"], y, z)
            rod_shape = shaft(rod, piston_x + c["piston_length"] - 2, rod_x - pin_r - 5, y, z)
            self.moving("Ram", f"PistonRod{i}", piston.fuse(rod_shape).fuse(eye(rod_x)), "W02-201",
                        "Piston, rod and front eye")
            for end, pivot, a, b, add in (
                ("Rear", rear_x, s["headThickness"], rear_x + pin_r + 50, self.fixed),
                ("Moving", rod_x, rod_x - pin_r - 50, s["crosshead_rear_x"], self.moving),
            ):
                group = "FixedActuators" if end == "Rear" else "Ram"
                half_w = c["clevis_ear_width"] / 2
                for j, (lo, hi) in enumerate(((-plate_out, -plate_in), (plate_in, plate_out)), 1):
                    ear = box(a, b, y - half_w, y + half_w, z + lo, z + hi).cut(
                        transverse_pin(pin_r, pivot, y, z + lo - 1, z + hi + 1))
                    add(group, f"{end}Clevis{i}_{j}", ear, "W02-202", "Double-shear clevis ear")
                pin = transverse_pin(pin_r, pivot, y, z - plate_out - 5, z + plate_out + 5)
                add(group, f"{end}Pin{i}", pin, "W02-203", "Clevis pin with axial retention envelope")

    def carriage(self):
        s = self.s
        lo = s["crosshead_rear_x"]
        hi = lo + s["crosshead_thickness"]
        spider_end = s["spider_end_x"]
        punch_w, punch_h = s["punch_yz"]
        other_side = s["crosshead_side"]
        carrier = tunnel(lo, hi, (other_side, other_side), (punch_w + 0.2, punch_h + 0.2))
        spider = tunnel(spider_end - s["spider_thickness"], spider_end,
                        (s["spider_side"], s["spider_side"]), s["spider_clear_yz"])
        arm_outer = s["guide_half_opening"] - s["guide_running_gap"] - s["guide_pad_thickness"]
        centers = (s["guide_rear_station_x_at_zero"], s["guide_rear_station_x_at_zero"] + s["guide_bogie_span"])
        for i, face in enumerate((("Y", -1), ("Y", 1), ("Z", -1), ("Z", 1)), 1):
            arm = face_strip(hi, spider_end - s["spider_thickness"], arm_outer - s["guide_arm_radial_depth"],
                             arm_outer, s["guide_arm_width"], face)
            carrier = carrier.fuse(arm)
            for j, center in enumerate(centers, 1):
                half = s["guide_pad_length"] / 2
                pad = face_strip(center - half, center + half, arm_outer, arm_outer + s["guide_pad_thickness"],
                                 s["guide_pad_width"], face)
                self.moving("Ram", f"GuidePad{i}_{j}", pad, "W02-302", "Replaceable guide pad on fitted seat")
        self.moving("Ram", "MovingCrosshead", carrier.fuse(spider).removeSplitter(), "W02-301",
                    "Primary crosshead, four guide arms and forward spider")
        punch = centered_box(lo, s["punch_face_x"], punch_w, punch_h)
        punch = punch.fuse(centered_box(hi, hi + s["punch_front_shoulder_thickness"], *s["punch_shoulder_yz"]))
        collar = centered_box(lo - s["punch_rear_collar_thickness"], lo, *s["punch_shoulder_yz"])
        bolt_r = s["punch_collar_tie_diameter"] / 2
        dy, dz = s["punch_collar_tie_offsets_yz"]
        for i, (sy, sz) in enumerate(product((-1, 1), repeat=2), 1):
            b = shaft(bolt_r, lo - s["punch_rear_collar_thickness"], lo + s["punch_bolt_engagement"],
                      sy * dy, sz * dz)
            punch = punch.cut(b)
            collar = collar.cut(b)
            self.moving("Ram", f"PunchCollarTie{i}", b, "W02-305", "Captured punch collar tie")
        self.moving("Ram", "Punch", punch, "W02-303", "Guided 300 x 220 punch and thrust shoulder")
        self.moving("Ram", "PunchRearCollar", collar, "W02-304", "Tension/reverse retention collar")

    def tooling(self):
        s, b = self.s, self.b
        chamber_x = s["chamber_entry_x"]
        gate_x = chamber_x + s["chamber_length"]
        front = s["front_head_x"]
        branch_b = self.variant.startswith("B")
        die_x = s["die_entry_B_x" if branch_b else "die_entry_A_x"]
        outside = s["chamber_outer_yz"]
        inside = [dim + 2 * s["chamber_radial_clearance"] for dim in s["punch_yz"]]
        self.fixed("Tooling", "Chamber", tunnel(chamber_x, gate_x, outside, inside), "W02-401",
                   "Compaction chamber, side feed interface to be detailed")
        inside_exit = [dim + 2 * s["die_exit_clearance"] for dim in s["product_yz"]]
        loft = Part.makeLoft([rect_wire(die_x - 0.1, *inside), rect_wire(front + 0.1, *inside_exit)], True, True)
        die = centered_box(die_x, front, *outside).cut(loft)
        # On branch B the inner portion of the die backing ends inside the gate's two sliding key tracks.
        if branch_b:
            die = die.common(centered_box(die_x - 1, front + 1, 2 * b["key_inner_y"], outside[1]))
        self.fixed("Tooling", "OutletDie", die, "W02-402", "Tapered die to nominal 150 x 60 product")
        if not branch_b:
            self.fixed("Tooling", "ExitSleeve", tunnel(gate_x, die_x, outside, inside), "W02-403",
                       "Family A continuation guide and die backing")
        for i, sign in enumerate((-1, 1), 1):
            def wing(a, d, y1, y2, z1, z2):
                return face_strip(a, d, y1, y2, z2 - z1, ("Y", sign), (z1 + z2) / 2)

            wing_end = gate_x if branch_b else front
            wing_start = s["chamber_mount_start_x"]
            bracket = wing(wing_start, wing_end, outside[0] / 2, 445, -150, 150)
            if branch_b:
                bracket = bracket.fuse(wing(gate_x, front, 387, 445, -150, 150))
            self.fixed("Tooling", f"ChamberSupport{i}", bracket, "W02-404", "Chamber support rib to the reaction head")
            if not branch_b:
                continue
            gate_half_y, gate_half_z = b["gate_width"] / 2, b["gate_height"] / 2
            gate_end = gate_x + b["gate_thickness"]
            key_end = gate_end + b["key_thickness"]
            seat = wing(gate_end, front, b["seat_inner_y"], gate_half_y, -gate_half_z, gate_half_z)
            self.fixed("Tooling", f"ReceiverSeat{i}", seat, "W02-502", "Fixed reaction seat, independent closed load path")
            gate_guide = wing(gate_x, front, gate_half_y + b["gate_guide_gap"], 387,
                              -gate_half_z - 10, gate_half_z + b["gate_open_lift"] + 10)
            self.fixed("Tooling", f"GateGuide{i}", gate_guide, "W02-503", "Vertical receiver guide cheek")
            kh = b["key_height"] / 2
            ky = b["key_inner_y"]
            lock = wing(gate_end, key_end, ky, ky + b["key_width"], -kh, kh)
            self.add("Locks", f"ReceiverLock{i}", lock, "W02-504", "Retractable load-bearing receiver lock key",
                     ("z", "-Design.LockDrop"))
            backing = wing(key_end, front, ky, ky + b["key_width"], -kh - b["key_retract_down"], kh)
            self.fixed("Tooling", f"LockBacking{i}", backing, "W02-505", "Direct key backing into the reaction head")
        if branch_b:
            gate = centered_box(gate_x, gate_x + b["gate_thickness"], b["gate_width"], b["gate_height"])
            self.add("Gate", "ReceiverGate", gate, "W02-501", "Lifting receiver gate / stop face",
                     ("z", "Design.GateLift"))

    def check_pose(self, stroke, lift=0, lock_drop=0, include_static=False):
        self.meta.StrokePosition = stroke
        self.meta.GateLift = lift
        self.meta.LockDrop = lock_drop
        self.doc.recompute()
        shapes = {name: (obj.Shape, group) for name, (obj, group) in self.items.items()}
        groups = ({"Ram"}, {"Frame", "FixedActuators", "Tooling", "Gate", "Locks"})
        pairs = [(left, right) for left, (_, category) in shapes.items() if category in groups[0]
                 for right, (_, target) in shapes.items() if target in groups[1]]
        if self.variant.startswith("B"):
            pairs.extend((left, right) for left, (_, category) in shapes.items() if category in {"Gate", "Locks"}
                         for right, (_, target) in shapes.items()
                         if target in {"Tooling", "Frame"} or (category == "Gate" and target == "Locks"))
        if include_static:
            rigid_groups = ({"Ram"}, {"Frame", "Tooling", "FixedActuators"})
            for rigid in rigid_groups:
                pairs.extend(combinations([key for key, (_, group) in shapes.items() if group in rigid], 2))
        for left, right in pairs:
            a, b = shapes[left][0], shapes[right][0]
            ab, bb = a.BoundBox, b.BoundBox
            if not all(min(amax, bmax) - max(amin, bmin) > 1e-6
                       for amin, amax, bmin, bmax in ((ab.XMin, ab.XMax, bb.XMin, bb.XMax),
                                                     (ab.YMin, ab.YMax, bb.YMin, bb.YMax),
                                                     (ab.ZMin, ab.ZMax, bb.ZMin, bb.ZMax))):
                continue
            interference = a.common(b).Volume
            require(interference < GAP_VOLUME_TOLERANCE_MM3,
                    f"{self.variant} s={stroke:g} gate={lift:g} keys={lock_drop:g}: "
                    f"{left} intersects {right} by {interference:g} mm3")
        rod = self.items["PistonRod1"][0]
        require(abs(rod.Shape.BoundBox.XMin - (self.c["piston_x_at_zero"] + stroke)) < 0.001,
                "Rod expression did not update the mm geometry")

    def build(self, envelope, screening, out):
        self.frame()
        self.drives()
        self.carriage()
        self.tooling()
        positions = {0, self.c["stroke"]}
        for row in envelope["cases"].values():
            if row["variant"] == self.variant:
                positions.update(self.c["rear_reserve"] + q * 1000 for q in row["pose_samples_q_m"])
        require(positions and min(positions) >= 0 and max(positions) <= self.c["stroke"], "Stroke outside design")
        branch_b = self.variant.startswith("B")
        lift, drop = self.b["gate_open_lift"], self.b["key_retract_down"]
        closed_limit = screening["stroke"]["B_closed_work_limit_stroke_mm"]
        poses = [(stroke, lift if branch_b else 0, drop if branch_b else 0) for stroke in sorted(positions)]
        if branch_b:
            poses.extend((stroke, 0, 0) for stroke in sorted(positions) if stroke <= closed_limit)
            poses.extend(((closed_limit, 0, drop / 2), (closed_limit, 0, drop),
                          (closed_limit, lift / 2, drop)))
        for stroke, gate, lock in poses:
            self.check_pose(stroke, gate, lock)
        self.check_pose(self.c["rear_reserve"], include_static=True)
        all_solids = Part.makeCompound([obj.Shape for obj, _ in self.items.values()])
        bounds = all_solids.BoundBox
        numbers = [bounds.XLength, bounds.YLength, bounds.ZLength]
        counts = {}
        for obj, _ in self.items.values():
            counts[obj.BOMItem] = counts.get(obj.BOMItem, 0) + 1
        drawing = prepare(self.doc, self.variant, [obj for obj, _ in self.items.values()], counts,
                          numbers, self.design, screening["stroke"])
        fcstd = out / f"{self.variant}.FCStd"
        with TemporaryDirectory(prefix=".w02-", dir=out) as temp:
            # A fresh save avoids generating FreeCAD backup archives in the delivery directory.
            staged = Path(temp) / fcstd.name
            self.doc.saveAs(str(staged))
            App.closeDocument(self.doc.Name)
            reopened = App.openDocument(str(staged))
            try:
                require(reopened.Design.VariantID == self.variant and
                        reopened.Design.RatedStroke.Value == self.c["stroke"], "Saved design properties missing")
                require(all(reopened.getObject(key).Shape.isValid() for key in self.items),
                        "Invalid reopened native solid")
                require(len(reopened.AssemblyDrawing.Views) >= 7 and reopened.PartsList.get("A1") == "Item"
                        and reopened.BOMDrawing.Views == [reopened.BOMTable]
                        and reopened.BOMTable.Source == reopened.PartsList, "Reopened drawing or BOM missing")
                reopened.Design.StrokePosition = self.c["stroke"] - 1
                reopened.recompute()
                require(abs(reopened.PistonRod1.Placement.Base.x - (self.c["stroke"] - 1)) < 0.001,
                        "Reopened native placement is not editable")
            finally:
                App.closeDocument(reopened.Name)
            staged.replace(fcstd)
        return {
            "path": fcstd.name, "sha256": sha256(fcstd.read_bytes()).hexdigest(),
            "nominal_pose_stroke_mm": self.c["rear_reserve"],
            "assembly_dimensions_XYZ_mm": numbers, "native_solid_count": len(self.items),
            "nominal_geometry_collision_pose_count": len(poses),
            "checked_poses_stroke_lift_drop_mm": poses,
            "bom_solid_counts": dict(sorted(counts.items())),
            "drawing_basis": drawing,
        }


def clearance_evidence(d, screening):
    c, s, b = (d[k] for k in ("cylinder", "structure", "receiver"))
    stroke = c["stroke"]
    guide_position = s["guide_rear_station_x_at_zero"] + s["guide_bogie_span"]
    clearances = {
        "piston_to_rear_cap_mm": 5,
        "piston_to_gland_at_full_stroke_mm": c["gland_start_x"] - c["piston_x_at_zero"] - c["piston_length"] - stroke,
        "rod_to_gland_radial_mm": 0.5,
        "piston_to_bore_radial_mm": 0.5,
        "pad_to_guide_running_mm": s["guide_running_gap"],
        "forward_pad_to_track_end_mm": s["front_head_x"] - guide_position - s["guide_pad_length"] / 2 - stroke,
        "punch_shoulder_to_chamber_at_full_stroke_mm": s["chamber_entry_x"] - s["crosshead_rear_x"]
        - s["crosshead_thickness"] - s["punch_front_shoulder_thickness"] - stroke,
        "chamber_to_spider_nominal_y_mm": (s["spider_clear_yz"][0] - s["chamber_outer_yz"][0]) / 2,
        "chamber_to_spider_nominal_z_mm": (s["spider_clear_yz"][1] - s["chamber_outer_yz"][1]) / 2,
        "chamber_to_guide_arm_radial_y_mm": s["guide_half_opening"] - s["guide_running_gap"]
        - s["guide_pad_thickness"] - s["guide_arm_radial_depth"] - s["chamber_outer_yz"][0] / 2,
        "spider_to_chamber_fixed_rib_at_full_stroke_mm": s["chamber_mount_start_x"] - s["spider_end_x"] - stroke,
        "punch_side_clearance_mm": s["chamber_radial_clearance"],
        "A_die_to_punch_at_full_stroke_mm": s["die_entry_A_x"] - s["punch_face_x"] - stroke,
        "B_die_to_punch_at_full_stroke_mm": s["die_entry_B_x"] - s["punch_face_x"] - stroke,
        "B_gate_closed_to_punch_at_end_of_work_mm": s["chamber_entry_x"] + s["chamber_length"]
        - s["punch_face_x"] - screening["stroke"]["B_closed_work_limit_stroke_mm"],
        "B_gate_raised_to_punch_mm": b["gate_open_lift"] - b["gate_height"] / 2 - s["punch_yz"][1] / 2,
        "B_key_dropped_to_gate_at_closed_height_mm": b["key_retract_down"] - b["key_height"] / 2 - b["gate_height"] / 2,
    }
    require(min(clearances.values()) > 0, f"Nonpositive interval clearance {clearances}")
    return clearances


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RESULT)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    d, e = read(HERE / "design.json"), read(ENVELOPE)
    screening = sizing(d, e)
    require(all(screening["checks"].values()), "Design screening did not pass")
    clearance = clearance_evidence(d, screening)
    versions = {"FreeCAD": ".".join(App.Version()[:3]), "FreeCAD_build": App.Version(),
                "OpenCASCADE": Part.OCC_VERSION, "python": ".".join(map(str, sys.version_info[:3]))}
    runtime = read(TASK / "input_manifest.json")["runtime"]
    require(versions["FreeCAD"] == "1.1.4", f"Unexpected runtime {versions}")
    manifest = {"design_id": d["id"], "scope": d["scope"], "versions": versions, "author_session": runtime, "units": "mm",
                "reference_frame": d["frame"], "clearances_mm": clearance, "variants": {}}
    for variant in VARIANTS:
        record = Assembly(variant, d, runtime, versions).build(e, screening, out)
        manifest["variants"][variant] = record
        print(f"PASS {variant}: {record['native_solid_count']} valid solids, "
              f"{record['nominal_geometry_collision_pose_count']} interference checks", flush=True)
    (out / "manifest.json").write_text(encode(manifest), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
