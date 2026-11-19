"""Build and reopen the four W02 iteration 04 native FreeCAD assemblies."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(sys.executable).resolve().parent))
import FreeCAD as App
import Part

from screen import ENVELOPE, SOURCE, TASK, encode, read, require, revised_geometry, sizing
from build_native import ReceiverAssembly
from rebuild import Assembly, centered_box, clearance_evidence
from drawings.W02.redesign_1p5mn import prepare as drawings


def update_bom(design):
    c, s, b = (design[key] for key in ("cylinder", "structure", "receiver"))
    clearance = " x ".join(f"{n + 2 * s['chamber_radial_clearance']:g}" for n in s["punch_yz"])
    shoulder = " x ".join(map(str, s["punch_shoulder_yz"]))
    specs = {
        "101": f"Thick structural block, {s['headThickness']} mm",
        "102": f"Thick structural block, {s['headThickness']} mm",
        "103": f"{s['tie_square']} mm square, {s['tie_stud_root']} mm stud root",
        "104": f"{s['tie_stud_nominal_diameter']} mm nominal, engagement {s['tie_engagement']} mm",
        "105": f"{s['guide_beam_width']} x {s['guide_beam_radial_depth']} x "
               f"{s['front_head_x'] - s['headThickness']} mm",
        "106": f"Diameter {s['guide_beam_end_pin_diameter']} mm, {s['guide_beam_end_pin_engagement']} mm embedment",
        "201": f"{c['bore']}/{c['rod']} x {c['stroke']} mm, COTS: hydraulic_cylinder",
        "202": f"{c['clevis_ear_thickness']} mm, qualified full-penetration root",
        "203": f"Diameter {c['pin_diameter']} mm, double shear",
        "301": f"{s['crosshead_thickness']} mm primary plate, {s['guide_bogie_span']} mm station spacing",
        "302": f"{s['guide_pad_length']} x {s['guide_pad_width']} x {s['guide_pad_thickness']} mm",
        "304": f"{shoulder} x {s['punch_rear_collar_thickness']} mm",
        "305": f"Diameter {s['punch_collar_tie_diameter']} mm, {s['punch_collar_tie_root']} mm min root, "
               f"{s['punch_bolt_engagement']} mm engagement",
        "401": f"{clearance} mm clear, {s['chamber_length']} mm working length",
        "403": f"{clearance} mm clear",
        "501": f"{b['gate_width']} x {b['gate_height']} x {b['gate_thickness']} mm, lift {b['gate_open_lift']} mm",
        "504": f"{b['key_width']} x {b['key_height']} x {b['key_thickness']} mm, drop {b['key_retract_down']} mm",
    }
    for suffix, spec in specs.items():
        code = f"W02-{suffix}"
        drawings.ITEMS[code] = drawings.ITEMS[code][0], spec


class GeometryChecks:
    def carriage(self):
        super().carriage()
        s = self.s
        lo = s["crosshead_rear_x"]
        hi = lo + s["crosshead_thickness"]
        width, height = s["punch_reinforced_yz"]
        carrier = self.items["MovingCrosshead"][0]
        carrier.Shape = carrier.Shape.cut(centered_box(lo, hi, width + 0.2, height + 0.2))
        punch = self.items["Punch"][0]
        reinforced = punch.Shape.fuse(centered_box(lo, hi, width, height))
        for i in range(1, s["punch_collar_tie_count"] + 1):
            reinforced = reinforced.cut(self.items[f"PunchCollarTie{i}"][0].Shape)
        punch.Shape = reinforced.removeSplitter()

    def check_pose(self, stroke, lift=0, lock_drop=0, include_static=False):
        super().check_pose(stroke, lift, lock_drop, include_static)
        if include_static:
            moving = [obj for obj, group in self.items.values() if group == "Ram"]
            self.carriage_weight_N = sum(obj.Shape.Volume for obj in moving) * 7.85e-6 * 9.81
            require(self.carriage_weight_N <= 2 * self.design["limits"]["assumed_guide_gravity_per_station_N"],
                    "CAD gravity exceeds conditional allowance")
            require(all(len(obj.Shape.Solids) == 1 for obj, _ in self.items.values()), "Disconnected CAD part")


class FamilyA(GeometryChecks, Assembly):
    pass


class FamilyB(GeometryChecks, ReceiverAssembly):
    def drawing_basis(self, screening, dimensions):
        result = super().drawing_basis(screening, dimensions)
        result["drawing_number"] = result["drawing_number"].removesuffix("-R02") + "-R04"
        for obj in (self.doc.AssemblyTitleBlock, self.doc.BOMTitleBlock):
            fields = obj.EditableTexts
            fields.update(drawing_number=result["drawing_number"], Subtitle=fields["Subtitle"].replace("REV 02", "REV 04"))
            obj.EditableTexts = fields
        self.doc.recompute()
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=SOURCE)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    baseline, design, dataset = revised_geometry()
    update_bom(design)
    envelope = read(ENVELOPE)
    screening = sizing(design, envelope)
    versions = {"FreeCAD": ".".join(App.Version()[:3]), "FreeCAD_build": App.Version(),
                "OpenCASCADE": Part.OCC_VERSION, "python": ".".join(map(str, sys.version_info[:3]))}
    require(versions["FreeCAD"] == "1.1.4", f"Unexpected runtime {versions}")
    author = read(TASK / "input_manifest.json")["author_sessions"][0]
    clearances = clearance_evidence(design, screening)
    manifest = {"revision": 4, "versions": versions, "author_session": author,
                "clearances_mm": clearances, "variants": {}}
    for variant in ("A-V1", "A-V2", "B-V1", "B-V2"):
        args = (variant, design)
        model = FamilyB(*args, baseline, dataset, author, versions) if variant.startswith("B") else (
            FamilyA(*args, author, versions))
        model.doc.Label = f"W02 {variant} | 1.5 MN | Rev 04"
        record = model.build(envelope, screening, out)
        record["moving_geometry_weight_N"] = model.carriage_weight_N
        manifest["variants"][variant] = record
        print(f"PASS {variant} {record['native_solid_count']} solids", flush=True)
    (out / "manifest.json").write_text(encode(manifest), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
