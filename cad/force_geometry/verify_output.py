"""Verify the delivered native reference geometry and rebuild it in temporary storage."""
import argparse
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from rebuild import App, DIMENSIONS, INPUTS, PHASES, ROOT, SOURCE, build, digest, load_model, read_json, require


def close_to(actual, expected, label):
    require(math.isclose(actual, expected, abs_tol=1e-7, rel_tol=1e-10), f"{label}: expected {expected}, got {actual}")


def inspect_native(path, variant_id, variant, bindings, interfaces, cases):
    document = App.openDocument(str(path))
    try:
        document.recompute()
        mm = {field: bindings[field]["value"] * 1000 for field in DIMENSIONS}
        chamber = document.ChamberEnvelope.Shape
        box = chamber.BoundBox
        width, height = mm["chamber.width"], mm["chamber.height"]
        require(chamber.isValid() and len(chamber.Solids) == 1, f"{variant_id}: invalid reference envelope")
        for actual, expected, label in (
            (box.XMin, 0, "local x origin"),
            (box.XLength, mm["chamber.length"], "chamber length"),
            (box.YMin, -width / 2, "local y origin"),
            (box.YLength, width, "chamber width"),
            (box.ZMin, -height / 2, "local z origin"),
            (box.ZLength, height, "chamber height"),
            (document.ProductLengthGauge.Shape.Length, mm["product.length"], "product length"),
            (document.ChargeLengthGauge.Shape.Length, mm["material.occupied_length"], "occupied length"),
            (document.RodSectionGauge.Shape.Curve.Radius, mm["cylinder.rod_diameter"] / 2, "rod section radius"),
        ):
            close_to(actual, expected, f"{variant_id}: {label}")

        start = 0.0
        for phase in PHASES:
            rod_travel = document.getObject(phase.title() + "Stroke")
            distance = mm["stroke." + phase]
            end = start + (-distance if phase == "return" else distance)
            close_to(rod_travel.X1, start, f"{variant_id} {phase}: relative start")
            close_to(rod_travel.X2, end, f"{variant_id} {phase}: relative end")
            close_to(rod_travel.Shape.Length, distance, f"{variant_id} {phase}: travel shape")
            start = end

        topology = document.ForcePath
        expected_cases = [key for key, item in cases.items() if item["variant"] == variant_id]
        require(topology.VariantID == variant_id and topology.CaseIDs == expected_cases, f"{variant_id}: CAD case coverage")
        require(topology.Arrangement == variant["title"] and topology.ForceLoop == variant["force_loop"],
                f"{variant_id}: proposal topology mismatch")
        expected_interfaces = {key: item for key, item in interfaces.items() if key.split("/")[0] == variant_id}
        require({obj.Label for obj in topology.Group} == set(expected_interfaces), f"{variant_id}: CAD interface coverage")
        for key, item in expected_interfaces.items():
            obj = document.getObject(item["cad_object"])
            require(obj.Label == key and obj.ActualGeometry == "UNKNOWN" and obj.Blockers == item["blockers"]
                    and obj.ReferenceObjects == item["reference_objects"] and obj.BoundaryConditions == item["boundary_conditions"],
                    f"{variant_id}: CAD interface mismatch for {key}")
            require(all(document.getObject(name) for name in obj.ReferenceObjects), f"{key}: unresolved object name")

        # Check editability by changing a bound dimension in memory and recomputing. Never save the change.
        document.Inputs.set("B2", f"{mm['chamber.length'] + 1} mm")
        document.recompute()
        close_to(document.ChamberEnvelope.Shape.BoundBox.XLength, mm["chamber.length"] + 1, f"{variant_id}: editable length")
    finally:
        App.closeDocument(document.Name)


def run(output, check_git):
    manifest = read_json(output / "manifest.json")
    bindings, variants, interfaces, cases = load_model()
    require(manifest["original_bindings"] == bindings and manifest["interfaces"] == interfaces and manifest["cases"] == cases,
            "Manifest differs from source bindings, interfaces or case catalog")
    require(set(manifest["variants"]) == set(variants), "Manifest variant coverage")
    require(manifest["physical_geometry_status"] == "BLOCKED_INPUTS", "Physical status overstatement")
    require(set(manifest["input_sha256"]) == {str(path) for path in INPUTS}, "Missing input hash")
    for path, expected in (manifest["input_sha256"] | manifest["tool_sha256"]).items():
        require(digest(ROOT / path) == expected, f"SHA-256 mismatch: {path}")

    require(set(manifest["tool_sha256"]) == {"cad/force_geometry/rebuild.py", "cad/force_geometry/verify_output.py"},
            "Missing CAD tool hash")

    if check_git:
        claim = read_json("coordination/tasks/T-R4-FORCE-GEOMETRY-01/input_manifest.json")
        require(manifest["source_main_sha"] == claim["source_main_sha"], "Mismatch with audited base")
        for item in claim["inputs"]:
            path = item["path"].rstrip("/")
            oid = subprocess.check_output(["git", "rev-parse", f"{claim['source_main_sha']}:{path}"],
                                          cwd=ROOT, text=True).strip()
            require(oid == item["git_object"], f"Wrong base object: {path}")
            if path in manifest["input_sha256"]:
                require(item["sha256"] == manifest["input_sha256"][path], f"Changed input {path}")
        for path in INPUTS[1:]:
            content = subprocess.check_output(["git", "show", f"{claim['source_main_sha']}:{path}"], cwd=ROOT)
            require(content == (ROOT / path).read_bytes(), f"Changed base input: {path}")
        for path in ("params/registry.yaml", "cad/layout/"):
            item = next(entry for entry in claim["inputs"] if entry["path"] == path)
            if "sha256" in item:
                require(digest(ROOT / path) == item["sha256"], f"Changed audited source {path}")
            else:
                status = subprocess.check_output(["git", "status", "--porcelain", "--", path], cwd=ROOT, text=True)
                oid = subprocess.check_output(["git", "rev-parse", f"HEAD:{path.rstrip('/')}"], cwd=ROOT, text=True).strip()
                require(not status and oid == item["git_object"], f"Changed audited source {path}")

    with TemporaryDirectory(prefix="rev-force-geometry-") as temporary:
        rebuilt = Path(temporary) / "rebuild"
        build(rebuilt)
        for variant_id, variant in variants.items():
            name = variant_id + ".FCStd"
            native = manifest["variants"][variant_id]
            require(native["path"] == name and digest(output / name) == native["sha256"], f"{name}: delivered SHA-256 mismatch")
            for directory in (output, rebuilt):
                inspect_native(directory / name, variant_id, variant, bindings[variant_id[0]], interfaces, cases)
    print(f"PASS: {len(variants)} editable FCStd documents and rebuilds, {len(interfaces)} interfaces, {len(cases)} case IDs, 44 source bindings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=SOURCE)
    parser.add_argument("--check-git", action="store_true")
    args = parser.parse_args()
    run(args.out.resolve(), args.check_git)
