"""Build four editable FreeCAD reference documents from pinned geometry inputs."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "/usr/lib/freecad-python3/lib")
import FreeCAD as App
import Part  # Initialize the native Part types.

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cad/source/force_geometry"
SYMBOLIC = Path("verification/r4_force_geometry/symbolic_20261116")
PROPOSAL = Path("verification/r4_cycle_interfaces/proposal")
CLAIM_INPUT = Path("coordination/tasks/T-R4-FORCE-GEOMETRY-01/input_manifest.json")
BINDINGS = PROPOSAL / "baseline_bindings.json"
VARIANTS = PROPOSAL / "force_variants.json"
INTERFACES = SYMBOLIC / "interfaces.json"
DEPENDENCIES = SYMBOLIC / "state_dependencies.json"
CATALOG = Path("baselines/operator-fork-20261118/state_catalog_index.json")
INPUTS = (CLAIM_INPUT, BINDINGS, VARIANTS, INTERFACES, DEPENDENCIES, CATALOG)
VARIANT_IDS = ("A-V1", "A-V2", "B-V1", "B-V2")

# Spreadsheet aliases for geometry in source units of metres.
DIMENSIONS = {
    "chamber.length": "ChamberLength",
    "chamber.width": "ChamberWidth",
    "chamber.height": "ChamberHeight",
    "product.length": "ProductLength",
    "material.occupied_length": "ChargeLength",
    "cylinder.rod_diameter": "RodDiameter",
    "stroke.approach": "Approach",
    "stroke.work": "Work",
    "stroke.eject": "Eject",
    "stroke.return": "ReturnTravel",
}
PHASES = ("approach", "work", "eject", "return")
REFERENCE_OBJECTS = {
    "chamber.length": "ChamberEnvelope",
    "chamber.width": "ChamberEnvelope",
    "chamber.height": "ChamberEnvelope",
    "product.length": "ProductLengthGauge",
    "material.occupied_length": "ChargeLengthGauge",
    "cylinder.rod_diameter": "RodSectionGauge",
    **{f"stroke.{phase}": phase.title() + "Stroke" for phase in PHASES},
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_model():
    bindings = read_json(BINDINGS)["rows"]
    by_variant = {
        family: {row["proposed_cad_field"]: row for row in bindings if row["scenario"] == f"BASE_{family}"}
        for family in ("A", "B")
    }
    require(len(bindings) == 44 and all(len(rows) == 22 for rows in by_variant.values()), "Expected 44 distinct source bindings")
    variants = {row["id"]: row for row in read_json(VARIANTS)["variants"]}
    require(tuple(variants) == VARIANT_IDS, "Unexpected force variants")

    source_interfaces = read_json(INTERFACES)["rows"]
    require(Counter(row["variant"] for row in source_interfaces) == dict.fromkeys(VARIANT_IDS, 13),
            "Expected thirteen interfaces per variant")
    interfaces = {}
    for row in source_interfaces:
        key = row["row_key"]
        variant, name = key.split("/")
        require(variant == row["variant"] and key not in interfaces, f"Invalid interface key {key}")
        fields = row["source_binding_fields"]
        records = by_variant[variant[0]]
        require(set(fields) <= records.keys(), f"Unresolved source bindings for {key}")
        blockers = row["unknown_arguments"]
        require(blockers and all(item["value"] is None and item["status"] == "UNKNOWN" for item in blockers),
                f"Invalid UNKNOWN arguments for {key}")
        interfaces[key] = {
            "description": row["interface"],
            "cad_object": "IF_" + name,
            "reference_objects": list(dict.fromkeys(REFERENCE_OBJECTS[field] for field in fields if field in REFERENCE_OBJECTS)),
            "source_bindings": fields,
            "actual_geometry_value": None,
            "actual_geometry_status": "UNKNOWN",
            "blockers": [item["argument"] for item in blockers],
            "boundary_conditions": row["reaction_phase_conditions"],
            "physical_evaluation": "NOT_RUN",
        }

    catalog = read_json(CATALOG)["cases"]
    dependencies = read_json(DEPENDENCIES)["rows"]
    require(len(catalog) == len(dependencies) == 42, "Expected 42 case dependencies")
    cases = {}
    for case, dependency in zip(catalog, dependencies, strict=True):
        case_id, state = case["case_id"], case["source_state"]
        require(case_id not in cases and state == dependency["source_state"], f"Source state mismatch for {case_id}")
        keys = dependency["interface_row_keys"]
        require(keys and len(set(keys)) == len(keys) and all(key in interfaces and key.split("/")[0] == state["variant"] for key in keys),
                f"Invalid interface dependencies for {case_id}")
        cases[case_id] = {
            "variant": state["variant"],
            "state": state["state"],
            "interface_ids": keys,
            "geometry_for_load_case": "BLOCKED_INPUTS",
            "required_inputs": dependency["missing_arguments"],
            "contact_and_load_requirement": dependency["contact_and_load_requirement"],
            "physical_evaluation": "NOT_RUN",
        }
    return by_variant, variants, interfaces, cases


def add_text(obj, name, value):
    kind = "App::PropertyStringList" if isinstance(value, list) else "App::PropertyString"
    obj.addProperty(kind, name, "Source")
    setattr(obj, name, value)


def axial_line(document, name, start, end):
    line = document.addObject("Part::Line", name)
    line.Y1 = line.Y2 = line.Z1 = line.Z2 = 0
    line.setExpression("X1", start)
    line.setExpression("X2", end)
    return line


def build_document(variant_id, variant, bindings, interfaces, cases):
    document = App.newDocument(variant_id.replace("-", "_"))
    document.Label = f"{variant_id} | Conditional reference geometry"

    sheet = document.addObject("Spreadsheet::Sheet", "Inputs")
    sheet.set("A1", "Nominal reference input")
    sheet.set("B1", "Editable value")
    sheet.set("C1", "Source parameter")
    for index, (field, alias) in enumerate(DIMENSIONS.items(), 2):
        binding = bindings[field]
        value = binding["value"]
        require(type(value) in (float, int) and math.isfinite(value) and value > 0 and binding["unit"] == "m",
                f"Invalid length binding {field}")
        sheet.set(f"A{index}", field)
        sheet.set(f"B{index}", f"{value} m")
        sheet.setAlias(f"B{index}", alias)
        sheet.set(f"C{index}", f"{binding['parameter_id']} rev {binding['revision']}")
    document.recompute()

    model = document.addObject("App::DocumentObjectGroup", "References")
    add_text(model, "Scope", "Conditional local references. Absolute origin, placement and structural contacts are UNKNOWN.")
    chamber = document.addObject("Part::Box", "ChamberEnvelope")
    chamber.Label = "Chamber internal envelope (reference volume)"
    for target, value in {
        "Length": "ChamberLength", "Width": "ChamberWidth", "Height": "ChamberHeight",
        "Placement.Base.y": "ChamberWidth * -0.5", "Placement.Base.z": "ChamberHeight * -0.5",
    }.items():
        chamber.setExpression(target, "Inputs." + value)
    model.addObject(chamber)

    for name, label, alias in (
        ("ProductLengthGauge", "Product length (standalone gauge)", "ProductLength"),
        ("ChargeLengthGauge", "Occupied length (standalone gauge)", "ChargeLength"),
    ):
        gauge = axial_line(document, name, "0 mm", f"Inputs.{alias}")
        gauge.Label = label
        model.addObject(gauge)
        gauge.Visibility = False
    rod = document.addObject("Part::Circle", "RodSectionGauge")
    rod.Label = "Nominal rod section (unplaced, local plane)"
    rod.setExpression("Radius", "Inputs.RodDiameter / 2")
    model.addObject(rod)
    rod.Visibility = False

    motion = document.addObject("App::DocumentObjectGroup", "TravelGauges")
    add_text(motion, "Scope", "Relative axial travel only. The zero is not the actual initial punch pose.")
    endpoints = ("0 mm", "Inputs.Approach", "Inputs.Approach + Inputs.Work",
                 "Inputs.Approach + Inputs.Work + Inputs.Eject")
    for phase, start, end in zip(PHASES, endpoints, (*endpoints[1:], endpoints[-1] + " - Inputs.ReturnTravel"), strict=True):
        line = axial_line(document, phase.title() + "Stroke", start, end)
        line.Label = f"{phase.title()} travel (relative)"
        motion.addObject(line)
    motion.Visibility = False

    topology = document.addObject("App::DocumentObjectGroup", "ForcePath")
    add_text(topology, "VariantID", variant_id)
    add_text(topology, "Arrangement", variant["title"])
    add_text(topology, "ForceLoop", variant["force_loop"])
    add_text(topology, "Members", variant["new_members"])
    add_text(topology, "EnvelopeRequirement", variant["envelope_requirement"])
    add_text(topology, "UnresolvedPlacement", variant["unknown_fields"])
    add_text(topology, "CaseIDs", [key for key, case in cases.items() if case["variant"] == variant_id])
    for key, data in interfaces.items():
        if key.split("/")[0] != variant_id:
            continue
        interface = document.addObject("App::FeaturePython", data["cad_object"])
        interface.Label = key
        add_text(interface, "ActualGeometry", data["actual_geometry_status"])
        add_text(interface, "Blockers", data["blockers"])
        add_text(interface, "BoundaryConditions", data["boundary_conditions"])
        add_text(interface, "ReferenceObjects", data["reference_objects"])
        topology.addObject(interface)
    document.recompute()
    return document


def build(output):
    bindings, variants, interfaces, cases = load_model()
    output.mkdir(parents=True, exist_ok=False)
    native = {}
    for variant_id, variant in variants.items():
        filename = variant_id + ".FCStd"
        destination = output / filename
        document = build_document(variant_id, variant, bindings[variant_id[0]], interfaces, cases)
        try:
            document.saveAs(str(destination))
        finally:
            App.closeDocument(document.Name)
        native[variant_id] = {
            "path": filename,
            "sha256": digest(destination),
            "arrangement": variant["title"],
            "source_scenario": f"BASE_{variant_id[0]}",
            "scope": "EDITABLE_CONDITIONAL_REFERENCES_AND_UNPLACED_FORCE_PATH",
        }

    claim_input = read_json(CLAIM_INPUT)
    manifest = {
        "task_id": claim_input["task_id"],
        "author_sessions": claim_input["author_sessions"],
        "source_main_sha": claim_input["source_main_sha"],
        "physical_geometry_status": "BLOCKED_INPUTS",
        "versions": {"FreeCAD": ".".join(App.Version()[:3]), "OpenCASCADE": Part.OCC_VERSION},
        "rebuild": "/usr/bin/python3 -B cad/force_geometry/rebuild.py --out NEW_DIRECTORY",
        "verify": "/usr/bin/python3 -B cad/force_geometry/verify_output.py --check-git",
        "input_sha256": {str(path): digest(ROOT / path) for path in INPUTS},
        "tool_sha256": {f"cad/force_geometry/{name}": digest(Path(__file__).with_name(name))
                        for name in ("rebuild.py", "verify_output.py")},
        "variants": native,
        "original_bindings": bindings,
        "interfaces": interfaces,
        "cases": cases,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    build(args.out.resolve())
