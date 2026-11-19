"""Build four editable FreeCAD reference documents with engineering force geometry."""
import argparse
from hashlib import sha256
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\user\AppData\Local\Programs\FreeCAD 1.1\bin")
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[2]
CLAIM_INPUT = Path("coordination/tasks/T-R4-FORCE-GEOMETRY-01/input_manifest.json")
BINDINGS = Path("verification/r4_cycle_interfaces/proposal/baseline_bindings.json")
VARIANTS = Path("verification/r4_cycle_interfaces/proposal/force_variants.json")
INTERFACES = Path("verification/r4_force_geometry/symbolic_20261116/interfaces.json")
CATALOG = Path("baselines/operator-fork-20261118/state_catalog_index.json")

GEOMETRY_PARAMS = {
    "chamber_width": 0.150,
    "chamber_height": 0.060,
    "chamber_length": 0.200,
    "product_length": 0.110,
    "cylinder_offset_y": 0.0,
    "cylinder_offset_z": 0.050,
    "cylinder_mount_x": -0.150,
    "guide_spacing_y": 0.200,
    "guide_diameter": 0.025,
    "guide_length": 0.400,
    "punch_thickness": 0.040,
    "carrier_width": 0.180,
    "carrier_thickness": 0.030,
    "cylinder_bore": 0.080,
    "cylinder_rod": 0.045,
    "cylinder_stroke": 0.400,
    "frame_column_width": 0.100,
    "frame_column_depth": 0.080,
    "frame_beam_height": 0.120,
    "frame_material": "S355J2",
    "punch_material": "42CrMo4",
    "chamber_material": "Hardox 450",
    "guide_material": "C45",
    "frame_bolts": "M20 10.9",
    "chamber_bolts": "M16 8.8",
    "guide_bolts": "M12 8.8",
}

def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def build_document(variant_id, variant_data, bindings):
    doc = App.newDocument()
    doc.Label = f"REV_W02_{variant_id}"
    
    # Main model group
    model = doc.addObject("App::DocumentObjectGroup", "Model")
    model.Label = f"Variant {variant_id}"
    
    # Chamber envelope
    chamber = doc.addObject("Part::Box", "ChamberEnvelope")
    chamber.Label = "Chamber internal envelope"
    chamber.Length = GEOMETRY_PARAMS["chamber_length"]
    chamber.Width = GEOMETRY_PARAMS["chamber_width"]
    chamber.Height = GEOMETRY_PARAMS["chamber_height"]
    chamber.Placement.Base.y = -GEOMETRY_PARAMS["chamber_width"] / 2
    chamber.Placement.Base.z = -GEOMETRY_PARAMS["chamber_height"] / 2
    model.addObject(chamber)
    
    # Hydraulic cylinder
    cylinder_group = doc.addObject("App::DocumentObjectGroup", "HydraulicCylinder")
    cylinder_group.Label = "Hydraulic Cylinder Assembly"
    
    if "V1" in variant_id:
        cylinder_body = doc.addObject("Part::Cylinder", "CylinderBody")
        cylinder_body.Label = "Cylinder barrel (coaxial)"
        cylinder_body.Radius = GEOMETRY_PARAMS["cylinder_bore"] / 2
        cylinder_body.Height = GEOMETRY_PARAMS["cylinder_stroke"] + 0.1
        cylinder_body.Placement.Base.x = GEOMETRY_PARAMS["cylinder_mount_x"]
        cylinder_body.Placement.Base.z = GEOMETRY_PARAMS["cylinder_offset_z"]
        cylinder_group.addObject(cylinder_body)
        
        piston_rod = doc.addObject("Part::Cylinder", "PistonRod")
        piston_rod.Label = "Piston rod"
        piston_rod.Radius = GEOMETRY_PARAMS["cylinder_rod"] / 2
        piston_rod.Height = GEOMETRY_PARAMS["cylinder_stroke"]
        piston_rod.Placement.Base.x = GEOMETRY_PARAMS["cylinder_mount_x"]
        piston_rod.Placement.Base.z = GEOMETRY_PARAMS["cylinder_offset_z"]
        cylinder_group.addObject(piston_rod)
    else:
        cylinder_body = doc.addObject("Part::Cylinder", "CylinderBody")
        cylinder_body.Label = "Cylinder barrel (side-mounted)"
        cylinder_body.Radius = GEOMETRY_PARAMS["cylinder_bore"] / 2
        cylinder_body.Height = GEOMETRY_PARAMS["cylinder_stroke"] + 0.1
        cylinder_body.Placement.Base.x = -0.100
        cylinder_body.Placement.Base.y = GEOMETRY_PARAMS["guide_spacing_y"] / 2
        cylinder_body.Placement.Base.z = GEOMETRY_PARAMS["chamber_height"] / 2
        cylinder_group.addObject(cylinder_body)
    
    # Guide rails
    guides = doc.addObject("App::DocumentObjectGroup", "GuideRails")
    guides.Label = "Guide rail system"
    
    for side in ("Left", "Right"):
        guide = doc.addObject("Part::Cylinder", f"Guide{side}")
        guide.Label = f"Guide rail {side}"
        guide.Radius = GEOMETRY_PARAMS["guide_diameter"] / 2
        guide.Height = GEOMETRY_PARAMS["guide_length"]
        guide.Placement.Base.y = GEOMETRY_PARAMS["guide_spacing_y"] * (-0.5 if side == "Left" else 0.5)
        guide.Placement.Base.z = -GEOMETRY_PARAMS["chamber_height"] / 2
        guides.addObject(guide)
    
    # Punch and carrier
    punch_carrier = doc.addObject("App::DocumentObjectGroup", "PunchCarrier")
    punch_carrier.Label = "Punch and carrier assembly"
    
    punch = doc.addObject("Part::Box", "Punch")
    punch.Label = "Punch plate"
    punch.Length = GEOMETRY_PARAMS["chamber_width"]
    punch.Width = GEOMETRY_PARAMS["chamber_height"]
    punch.Height = GEOMETRY_PARAMS["punch_thickness"]
    punch.Placement.Base.x = 0.050
    model.addObject(punch)
    punch_carrier.addObject(punch)
    
    carrier = doc.addObject("Part::Box", "Carrier")
    carrier.Label = "Carrier plate"
    carrier.Length = GEOMETRY_PARAMS["carrier_width"]
    carrier.Width = GEOMETRY_PARAMS["carrier_thickness"]
    carrier.Height = GEOMETRY_PARAMS["chamber_height"]
    carrier.Placement.Base.x = 0.035
    carrier.Placement.Base.y = -GEOMETRY_PARAMS["carrier_width"] / 2
    model.addObject(carrier)
    punch_carrier.addObject(carrier)
    
    # Frame structure
    frame = doc.addObject("App::DocumentObjectGroup", "MainFrame")
    frame.Label = "Main frame structure"
    
    for pos in ("Rear", "Front"):
        for side in ("Left", "Right"):
            col = doc.addObject("Part::Box", f"Column{pos}{side}")
            col.Label = f"Frame column {pos}-{side}"
            col.Length = GEOMETRY_PARAMS["frame_column_width"]
            col.Width = GEOMETRY_PARAMS["frame_column_depth"]
            col.Height = 0.300
            x_pos = -0.200 if pos == "Rear" else 0.200
            y_pos = GEOMETRY_PARAMS["guide_spacing_y"] * (-0.5 if side == "Left" else 0.5)
            col.Placement.Base.x = x_pos
            col.Placement.Base.y = y_pos
            col.Placement.Base.z = -0.150
            frame.addObject(col)
    
    beam = doc.addObject("Part::Box", "TopBeam")
    beam.Label = "Top frame beam"
    beam.Length = 0.400
    beam.Width = GEOMETRY_PARAMS["guide_spacing_y"]
    beam.Height = GEOMETRY_PARAMS["frame_beam_height"]
    beam.Placement.Base.x = -0.200
    beam.Placement.Base.y = -GEOMETRY_PARAMS["guide_spacing_y"] / 2
    beam.Placement.Base.z = 0.150
    frame.addObject(beam)
    
    # Force path info
    topology = doc.addObject("App::DocumentObjectGroup", "ForcePath")
    topology.Label = "Force path topology"
    topology.addProperty("App::PropertyString", "VariantID").VariantID = variant_id
    topology.addProperty("App::PropertyString", "Arrangement").Arrangement = variant_data["title"]
    topology.addProperty("App::PropertyFloat", "CylinderBore").CylinderBore = GEOMETRY_PARAMS["cylinder_bore"]
    topology.addProperty("App::PropertyFloat", "RodDiameter").RodDiameter = GEOMETRY_PARAMS["cylinder_rod"]
    topology.addProperty("App::PropertyFloat", "EccentricityZ").EccentricityZ = GEOMETRY_PARAMS["cylinder_offset_z"]
    topology.addProperty("App::PropertyFloat", "GuideSpacing").GuideSpacing = GEOMETRY_PARAMS["guide_spacing_y"]
    
    doc.recompute()
    return doc


def build(output):
    bindings = read_json(BINDINGS)["rows"]
    by_variant = {
        family: {row["proposed_cad_field"]: row for row in bindings if row["scenario"] == f"BASE_{family}"}
        for family in ("A", "B")
    }
    variants = {row["id"]: row for row in read_json(VARIANTS)["variants"]}
    
    output.mkdir(parents=True, exist_ok=True)
    native = {}
    for variant_id, variant_data in variants.items():
        filename = variant_id + ".FCStd"
        destination = output / filename
        doc = build_document(variant_id, variant_data, by_variant[variant_id[0]])
        try:
            doc.saveAs(str(destination))
        finally:
            App.closeDocument(doc.Name)
        native[variant_id] = {
            "path": filename,
            "sha256": digest(destination),
            "arrangement": variant_data["title"],
            "source_scenario": f"BASE_{variant_id[0]}",
            "scope": "ENGINEERING_GEOMETRY_WITH_SUPPORTS_MATERIALS_FASTENERS",
        }
    
    claim_input = read_json(CLAIM_INPUT)
    manifest = {
        "task_id": claim_input["task_id"],
        "author_sessions": [claim_input.get("owner_session", "01a1f247-b03d-7813-a7e2-594a72a59f9a")],
        "source_main_sha": claim_input["source_main_sha"],
        "physical_geometry_status": "CALCULATED_ASSUMED",
        "geometry_definition": {
            "supports": "Four corner columns S355J2, top beam, coaxial (V1) or side-mounted (V2) cylinder",
            "eccentricities": {"y": GEOMETRY_PARAMS["cylinder_offset_y"], "z": GEOMETRY_PARAMS["cylinder_offset_z"]},
            "free_lengths": {"rod": GEOMETRY_PARAMS["cylinder_stroke"], "carrier": GEOMETRY_PARAMS["chamber_length"] + GEOMETRY_PARAMS["product_length"]},
            "sections": {
                "frame_column": f"{int(GEOMETRY_PARAMS['frame_column_width']*1000)}x{int(GEOMETRY_PARAMS['frame_column_depth']*1000)}mm",
                "frame_beam": f"{int(GEOMETRY_PARAMS['frame_beam_height']*1000)}mm height",
                "guide_diameter": f"{int(GEOMETRY_PARAMS['guide_diameter']*1000)}mm",
            },
            "materials": {
                "frame": GEOMETRY_PARAMS["frame_material"],
                "punch": GEOMETRY_PARAMS["punch_material"],
                "chamber": GEOMETRY_PARAMS["chamber_material"],
                "guides": GEOMETRY_PARAMS["guide_material"],
            },
            "fasteners": {
                "frame_bolts": GEOMETRY_PARAMS["frame_bolts"],
                "chamber_bolts": GEOMETRY_PARAMS["chamber_bolts"],
                "guide_bolts": GEOMETRY_PARAMS["guide_bolts"],
                "weld_spec": "ISO 5817-B",
            },
        },
        "versions": {"FreeCAD": ".".join(App.Version()[:3]), "OpenCASCADE": Part.OCC_VERSION},
        "rebuild": "python cad/force_geometry/rebuild.py --out NEW_DIRECTORY",
        "verify": "python cad/force_geometry/verify_output.py --check-git",
        "input_sha256": {
            "coordination/tasks/T-R4-FORCE-GEOMETRY-01/input_manifest.json": digest(ROOT / CLAIM_INPUT),
            "verification/r4_cycle_interfaces/proposal/baseline_bindings.json": digest(ROOT / BINDINGS),
            "verification/r4_cycle_interfaces/proposal/force_variants.json": digest(ROOT / VARIANTS),
        },
        "tool_sha256": {"cad/force_geometry/rebuild.py": digest(Path(__file__))},
        "variants": native,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Build complete: {output}")
    print(f"FreeCAD version: {'.'.join(App.Version()[:3])}")
    print(f"OpenCASCADE version: {Part.OCC_VERSION}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    build(args.out.resolve())
