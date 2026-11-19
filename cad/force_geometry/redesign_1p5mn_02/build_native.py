"""Rebuild the two B assemblies, including continuous receiver travel and contact faces."""

import argparse
from hashlib import sha256
from math import isclose
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(sys.executable).resolve().parent))
import FreeCAD as App
import Part

from screen_contact import ENVELOPE, RESULT, TASK, VARIANTS, encode, geometry, read, require
from rebuild import Assembly, GAP_VOLUME_TOLERANCE_MM3, box, centered_box, clearance_evidence, prepare, sizing


def on_x_plane(shape, x):
    return [face for face in shape.Faces if all(abs(vertex.X - x) < 1e-6 for vertex in face.Vertexes)]


def common_face_area(left, right, x):
    return sum(a.common(b).Area for a in on_x_plane(left, x) for b in on_x_plane(right, x))


def bounds(shape):
    bb = shape.BoundBox
    return [bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax]


class ReceiverAssembly(Assembly):
    def __init__(self, variant, design, baseline, dataset, runtime, versions):
        super().__init__(variant, design, runtime, versions)
        self.doc.Label = f"W02 {variant} | 1.5 MN | Receiver rev 02"
        self.baseline = baseline
        self.dataset = dataset
        self.gate_back = self.s["chamber_entry_x"] + self.s["chamber_length"] + self.b["gate_thickness"]
        self.key_start = self.gate_back + self.b["gate_to_key_axial_gap"]
        self.backing_start = self.key_start + self.b["key_thickness"] + self.b["key_to_backing_axial_gap"]
        self.seat_start = self.gate_back + self.b["gate_to_seat_axial_gap"]
        for name in ("GateAxialTakeup", "LockAxialTakeup"):
            self.meta.addProperty("App::PropertyLength", name, "Receiver poses", "Axial float in mm")
        for name, value in (("ReceiverKeyWidth", self.b["key_width"]), ("ReceiverKeyHeight", self.b["key_height"]),
                            ("ReceiverKeyDrop", self.b["key_retract_down"]), ("ReceiverGateHeight", self.b["gate_height"])):
            self.meta.addProperty("App::PropertyLength", name, "Receiver nominal dimensions")
            setattr(self.meta, name, value)
            self.meta.setEditorMode(name, 1)

    def object(self, name):
        return self.items[name][0]

    def side_box(self, sign, x0, x1, inner, outer, z0, z1):
        y0, y1 = sorted((sign * inner, sign * outer))
        return box(x0, x1, y0, y1, z0, z1)

    def frame(self):
        super().frame()
        b = self.b
        obj = self.object("ReactionFrameHead")
        shape = obj.Shape
        rear = self.s["front_head_x"] + self.s["headThickness"]
        last = rear + b["reaction_head_boss_projection"]
        inner, outer, half_height = (b["reaction_head_boss_inner_y"], b["reaction_head_boss_outer_y"],
                                     b["reaction_head_boss_height"] / 2)
        for sign in (-1, 1):
            shape = shape.fuse(self.side_box(sign, rear, last, inner, outer, -half_height, half_height))
        roots = [edge for edge in shape.Edges if all(
            abs(v.X - rear) < 1e-6 and inner <= abs(v.Y) <= outer and abs(v.Z) <= half_height
            for v in edge.Vertexes)]
        require(len(roots) == 8, "Unexpected reaction-head boss roots")
        obj.Shape = shape.makeFillet(b["reaction_head_boss_root_radius"], roots)

    def tooling(self):
        super().tooling()
        b, s = self.b, self.s
        front = s["front_head_x"]
        # Keep the taper and its original envelope, with lateral running space beside the keys.
        die = self.object("OutletDie")
        die.Shape = die.Shape.common(centered_box(s["die_entry_B_x"] - 1, front + 1,
                                                  2 * self.baseline["receiver"]["key_inner_y"],
                                                  s["chamber_outer_yz"][1]))
        self.object("ReceiverGate").setExpression("Placement.Base.x", "Design.GateAxialTakeup")
        key_end = self.key_start + b["key_thickness"]
        key_inner, key_half_z, gate_half_z = b["key_inner_y"], b["key_height"] / 2, b["gate_height"] / 2
        key_outer = key_inner + b["key_width"]
        for i, sign in enumerate((-1, 1), 1):
            key = self.object(f"ReceiverLock{i}")
            prism = self.side_box(sign, self.key_start, key_end, key_inner, key_outer, -key_half_z, key_half_z)
            edge_breaks = [edge for edge in prism.Edges if any(
                all(abs(v.X - x) < 1e-6 for v in edge.Vertexes) for x in (self.key_start, key_end))]
            key.Shape = prism.makeChamfer(b["key_edge_chamfer"], edge_breaks)
            key.setExpression("Placement.Base.x", "Design.LockAxialTakeup")
            self.object(f"LockBacking{i}").Shape = self.side_box(
                sign, self.backing_start, front, key_inner, key_outer, -key_half_z - b["key_retract_down"], key_half_z)
            self.object(f"ReceiverSeat{i}").Shape = self.side_box(
                sign, self.seat_start, front, b["seat_inner_y"], b["gate_width"] / 2, -gate_half_z, gate_half_z)
        for prefix, ref in self.dataset["material_refs"].items():
            names = (prefix,) if prefix in ("ReceiverGate", "ReactionFrameHead") else (f"{prefix}1", f"{prefix}2")
            for name in names:
                obj = self.object(name)
                obj.addProperty("App::PropertyString", "AssumedMaterial", "W02 traceability")
                obj.AssumedMaterial = self.design["materials"][ref]["material"]

    def pose(self, stroke, lift, drop, gate_x=0, key_x=0, include_static=False):
        self.meta.GateAxialTakeup = gate_x
        self.meta.LockAxialTakeup = key_x
        self.check_pose(stroke, lift, drop, include_static)

    def travel_check(self, limit):
        b = self.b
        drop, lift = b["key_retract_down"], b["gate_open_lift"]
        for moving, travel in ((("ReceiverLock1", "ReceiverLock2"), -drop), (("ReceiverGate",), lift)):
            self.pose(limit, 0, drop if travel > 0 else 0)
            for name in moving:
                x0, x1, y0, y1, z0, z1 = bounds(self.object(name).Shape)
                swept = box(x0, x1, y0, y1, z0 + min(0, travel), z1 + max(0, travel))
                for other, (obj, _) in self.items.items():
                    if other != name and swept.BoundBox.intersect(obj.Shape.BoundBox):
                        require(swept.common(obj.Shape).Volume < GAP_VOLUME_TOLERANCE_MM3,
                                f"{self.variant}: {name} continuous sweep intersects {other}")
        return {"lock_drop_mm": drop, "gate_lift_mm": lift, "max_stroke_with_gate_closed_mm": limit}

    def contact_check(self, limit):
        b = self.b
        takeup = b["gate_to_key_axial_gap"] + b["key_to_backing_axial_gap"]
        key_shift = b["key_to_backing_axial_gap"]
        self.pose(limit, 0, 0, takeup, key_shift)
        gate = self.object("ReceiverGate").Shape
        head = self.object("ReactionFrameHead").Shape
        edge = b["key_edge_chamfer"]
        expected_key_area = (b["key_width"] - 2 * edge) * (b["key_height"] - 2 * edge)
        expected_back_area = b["key_width"] * (b["key_height"] + b["key_retract_down"])
        result = {}
        for i in (1, 2):
            key = self.object(f"ReceiverLock{i}").Shape
            back = self.object(f"LockBacking{i}").Shape
            areas = {
                "gate_key": common_face_area(gate, key, self.gate_back + takeup),
                "key_backing": common_face_area(key, back, self.backing_start),
                "backing_head": common_face_area(back, head, self.s["front_head_x"]),
            }
            for field, expected in (("gate_key", expected_key_area), ("key_backing", expected_key_area),
                                    ("backing_head", expected_back_area)):
                require(isclose(areas[field], expected, abs_tol=1e-6), f"{self.variant}/{i}: wrong {field} area")
            result[str(i)] = {"key_front_yz_bbox_mm": [round(x, 8) for x in bounds(
                on_x_plane(key, self.gate_back + takeup)[0])[2:]], "areas_mm2": areas}
        self.pose(limit, 0, b["key_retract_down"], b["gate_to_seat_axial_gap"])
        gate = self.object("ReceiverGate").Shape
        for i in (1, 2):
            seat = self.object(f"ReceiverSeat{i}").Shape
            seat_area = (b["gate_width"] / 2 - b["seat_inner_y"]) * b["gate_height"]
            areas = {"gate_seat": common_face_area(gate, seat, self.seat_start),
                     "seat_head": common_face_area(seat, head, self.s["front_head_x"])}
            require(all(isclose(area, seat_area, abs_tol=1e-6) for area in areas.values()),
                    f"{self.variant}/{i}: incomplete seat load path")
            result[str(i)]["areas_mm2"].update(areas)
        return result

    def drawing_basis(self, screening, dimensions):
        b = self.b
        solids = [obj for obj, _ in self.items.values()]
        counts = {code: sum(obj.BOMItem == code for obj in solids) for code in {obj.BOMItem for obj in solids}}
        drawing = prepare(self.doc, self.variant, solids, counts, dimensions, self.design, screening["stroke"])
        drawing["drawing_number"] += "-R02"
        for template, subtitle in ((self.doc.AssemblyTitleBlock, "DESIGN BASIS / REV 02"),
                                   (self.doc.BOMTitleBlock, "BILL OF MATERIALS / REV 02")):
            texts = template.EditableTexts
            texts.update({"drawing_number": drawing["drawing_number"], "Subtitle": subtitle})
            template.EditableTexts = texts
        specs = {
            "W02-102": f"Thick block {self.s['headThickness']} mm, integral +{b['reaction_head_boss_projection']} mm bosses",
            "W02-501": f"{b['gate_width']} x {b['gate_height']} x {b['gate_thickness']} mm, lift {b['gate_open_lift']} mm",
            "W02-502": f"Seat face {b['gate_to_seat_axial_gap']} mm downstream of unloaded gate",
            "W02-504": f"{b['key_width']} x {b['key_height']} x {b['key_thickness']} mm, drop {b['key_retract_down']} mm",
            "W02-505": "Direct bearing, machined front face and rear face",
        }
        for row, (item, entry) in enumerate(drawing["bom"].items(), 2):
            if item in specs:
                entry["specification"] = specs[item]
                self.doc.PartsList.set(f"D{row}", specs[item])
        self.doc.recompute()
        return drawing

    def build(self, envelope, screening, out):
        self.frame()
        self.drives()
        self.carriage()
        self.tooling()
        b, c = self.b, self.c
        limit = screening["stroke"]["B_closed_work_limit_stroke_mm"]
        positions = {0, c["stroke"], limit}
        for row in envelope["cases"].values():
            if row["variant"] == self.variant:
                positions.update(c["rear_reserve"] + q * 1000 for q in row["pose_samples_q_m"])
        poses = [(s, b["gate_open_lift"], b["key_retract_down"]) for s in sorted(positions)]
        poses.extend((s, 0, 0) for s in sorted(positions) if s <= limit)
        for pose in poses:
            self.pose(*pose)
        sweeps = self.travel_check(limit)
        contacts = self.contact_check(limit)
        self.pose(c["rear_reserve"], 0, 0, include_static=True)
        bounds_all = Part.makeCompound([obj.Shape for obj, _ in self.items.values()]).BoundBox
        dimensions = [bounds_all.XLength, bounds_all.YLength, bounds_all.ZLength]
        drawing = self.drawing_basis(screening, dimensions)
        fcstd = out / f"{self.variant}.FCStd"
        with TemporaryDirectory(prefix=".w02-b-", dir=out) as directory:
            staged = Path(directory) / fcstd.name
            self.doc.saveAs(str(staged))
            App.closeDocument(self.doc.Name)
            doc = App.openDocument(str(staged))
            try:
                require(all(doc.getObject(name).Shape.isValid() and len(doc.getObject(name).Shape.Solids) == 1
                            for name in self.items), "Invalid reopened solids")
                require(doc.AssemblyDrawing.Views and doc.BOMTable.Source == doc.PartsList, "Drawing/BOM lost")
                require(doc.Design.VariantID == self.variant, "Unexpected saved variant")
                doc.Design.StrokePosition = limit
                doc.Design.LockDrop = b["key_retract_down"]
                doc.Design.GateLift = b["gate_open_lift"]
                doc.Design.GateAxialTakeup = 0.1
                doc.Design.LockAxialTakeup = 0.2
                doc.recompute()
                for key in (doc.ReceiverLock1, doc.ReceiverLock2):
                    require(isclose(key.Placement.Base.z, -b["key_retract_down"]) and isclose(key.Placement.Base.x, 0.2),
                            "Editable key motion lost")
                require(isclose(doc.ReceiverGate.Placement.Base.z, b["gate_open_lift"]) and
                        isclose(doc.ReceiverGate.Placement.Base.x, 0.1) and
                        isclose(doc.PistonRod1.Placement.Base.x, limit), "Editable gate or ram motion lost")
            finally:
                App.closeDocument(doc.Name)
            staged.replace(fcstd)
        return {"path": fcstd.name, "sha256": sha256(fcstd.read_bytes()).hexdigest(),
                "nominal_assembly_dimensions_XYZ_mm": dimensions, "native_solid_count": len(self.items),
                "checked_poses_stroke_lift_drop_mm": poses, "continuous_unloaded_sweeps": sweeps,
                "contacts": contacts, "drawing_basis": drawing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RESULT)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    baseline, design, dataset = geometry()
    envelope = read(ENVELOPE)
    screening = sizing(design, envelope)
    versions = {"FreeCAD": ".".join(App.Version()[:3]), "FreeCAD_build": App.Version(),
                "OpenCASCADE": Part.OCC_VERSION, "python": ".".join(map(str, sys.version_info[:3]))}
    require(versions["FreeCAD"] == "1.1.4", f"Unexpected runtime {versions}")
    runtime = read(TASK / "input_manifest.json")["runtime"]
    s, b = design["structure"], design["receiver"]
    gate_back = s["chamber_entry_x"] + s["chamber_length"] + b["gate_thickness"]
    clearances = {name: value for name, value in clearance_evidence(design, screening).items()
                  if not name.startswith("A_")}
    clearances.update({
        "B_die_to_gate_at_seat_take_up_mm": s["die_entry_B_x"] - gate_back - b["gate_to_seat_axial_gap"],
        "B_die_to_key_lateral_mm": b["key_inner_y"] - baseline["receiver"]["key_inner_y"],
        "B_seat_to_key_lateral_mm": b["seat_inner_y"] - b["key_inner_y"] - b["key_width"],
        "B_key_to_lower_guide_at_full_drop_mm": s["guide_half_opening"] - b["key_retract_down"] - b["key_height"] / 2,
    })
    require(min(clearances.values()) > 0, "Nonpositive assembly clearance")
    manifest = {"dataset_id": dataset["dataset_id"], "revision": dataset["revision"], "scope": design["scope"],
                "versions": versions, "author_session": runtime, "frame": design["frame"],
                "clearances_mm": clearances, "variants": {}}
    for variant in VARIANTS:
        record = ReceiverAssembly(variant, design, baseline, dataset, runtime, versions).build(envelope, screening, out)
        manifest["variants"][variant] = record
        print(f"PASS {variant}: {record['native_solid_count']} solids, swept key/gate travel and contact faces", flush=True)
    (out / "manifest.json").write_text(encode(manifest), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
