"""Verify the W02 1.5 MN artifacts, calculation, native CAD metadata and Git pins."""

import argparse
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import re
import subprocess
import sys
from xml.etree import ElementTree
from zipfile import ZipFile

import yaml

from calculate import ENVELOPE, HERE, RESULT, ROOT, encode, read, sizing

TASK = ROOT / "coordination/tasks/T-R4-REDESIGN-1.5MN-01"
CLAIM = "coordination/claims/T-R4-REDESIGN-1.5MN-01.json"
CLAIM_MAIN = "3b9ef2ece6904c4fa86ae59477640869362c34f0"
DRAWINGS = ROOT / "drawings/W02/redesign_1p5mn"
CATALOG = ROOT / "drives/cots_catalog.yaml"
VARIANTS = ("A-V1", "A-V2", "B-V1", "B-V2")
OUTPUT = TASK / "output_manifest.json"
FILES = [
    *[HERE / name for name in ("design.json", "interfaces.json", "calculate.py", "rebuild.py", "verify_output.py",
                               "README.md")],
    DRAWINGS / "prepare.py", DRAWINGS / "README.md", TASK / "input_manifest.json", TASK / "input_audit.md", CATALOG,
    RESULT / "manifest.json", RESULT / "screening.json",
    *[RESULT / f"{variant}.FCStd" for variant in VARIANTS],
]
LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def git_read(rev, relative):
    return subprocess.check_output(["git", "show", f"{rev}:{relative}"], cwd=ROOT)


def digest(content):
    return sha256(content).hexdigest()


def check_bytes(git_data, materialized, label):
    if git_data.startswith(LFS_PREFIX):
        oid = re.search(rb"^oid sha256:([a-f0-9]{64})\r?$", git_data, re.M)
        size = re.search(rb"^size ([0-9]+)\r?$", git_data, re.M)
        require(oid and size and (oid[1].decode(), int(size[1])) == (digest(materialized), len(materialized)),
                f"Wrong Git LFS pointer for {label}")
    else:
        require(git_data == materialized, f"Working file differs from Git: {label}")


def compare(actual, expected, label):
    if isinstance(expected, dict):
        require(type(actual) is dict and actual.keys() == expected.keys(), f"Changed fields: {label}")
        for key, expected_value in expected.items():
            compare(actual[key], expected_value, f"{label}.{key}")
    elif isinstance(expected, list):
        require(type(actual) is list and len(actual) == len(expected), f"Changed list: {label}")
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, f"{label}[{i}]")
    elif type(expected) is float:
        require(type(actual) in (int, float) and isclose(actual, expected, rel_tol=2e-13, abs_tol=1e-10),
                f"Changed calculated value: {label}")
    else:
        require(type(actual) is type(expected) and actual == expected, f"Changed value: {label}")


def manifest():
    return {
        "task_id": "T-R4-REDESIGN-1.5MN-01",
        "scope": "CALCULATED_ASSUMED",
        "claim_main_sha": CLAIM_MAIN,
        "source_main_sha": read(TASK / "input_manifest.json")["source_main_sha"],
        "author_sessions": [read(TASK / "input_manifest.json")["runtime"]],
        "delivery_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in FILES},
        "commands": {
            "calculate": "python cad/force_geometry/redesign_1p5mn/calculate.py",
            "native_geometry_and_drawing": "FreeCAD 1.1.4 bundled python.exe cad/force_geometry/redesign_1p5mn/rebuild.py",
            "verify": "python cad/force_geometry/redesign_1p5mn/verify_output.py --check-git",
        },
    }


def check_input_pins(audit):
    base, author = audit["source_main_sha"], audit["runtime"]
    claim = json.loads(git_read(CLAIM_MAIN, CLAIM))
    require(claim["status"] == "ACCEPTED_MAIN" and claim["source_main_sha"] == base and
            claim["owner_session"] == author["CODEX_SESSION_ID"] and claim["model_label"] == author["model_label"],
            "Output author differs from accepted claim")
    changed = {CATALOG.relative_to(ROOT).as_posix(), (TASK / "task.json").relative_to(ROOT).as_posix()}
    for path, entry in audit["inputs"].items():
        pin = git_read(base, path)
        if entry["storage"] == "git_lfs":
            data = (ROOT / path).read_bytes()
            check_bytes(pin, data, path)
        else:
            data = pin
            if path not in changed:
                check_bytes(pin, (ROOT / path).read_bytes(), path)
        require(digest(data) == entry["sha256"], f"Wrong input SHA-256: {path}")


def property_value(data, name, child):
    return data.find(f"./Properties/Property[@name='{name}']/{child}").attrib["value"]


def check_fcstd(path, variant, entry, geometry, design, interfaces):
    require(digest(path.read_bytes()) == entry["sha256"], f"Native archive SHA-256: {variant}")
    with ZipFile(path) as archive:
        require(archive.testzip() is None, f"Damaged archive: {variant}")
        doc = ElementTree.fromstring(archive.read("Document.xml"))
        part_count = sum(item.endswith(".Shape.brp") for item in archive.namelist())
    objects = {item.attrib["name"]: item.attrib["type"] for item in doc.findall("./Objects/Object")}
    require(part_count == entry["native_solid_count"] == sum(
        item == "Part::Feature" for item in objects.values()), f"Unexpected part shapes in {variant}")
    c = design["cylinder"]
    meta = doc.find("./ObjectData/Object[@name='Design']")
    for p, value in (("BoreDiameter", c["bore"]), ("RodDiameter", c["rod"]), ("RatedStroke", c["stroke"]),
                     ("StrokePosition", c["rear_reserve"])):
        require(float(property_value(meta, p, "Float")) == value, f"Wrong native {p} for {variant}")
    for p, value in (("VariantID", variant), ("CodexSessionID", geometry["author_session"]["CODEX_SESSION_ID"]),
                     ("CodexModel", geometry["author_session"]["model_label"]),
                     ("FreeCADRuntime", geometry["versions"]["FreeCAD"]),
                     ("OpenCASCADE", geometry["versions"]["OpenCASCADE"])):
        require(property_value(meta, p, "String") == value, f"Wrong provenance for {variant}: {p}")
    for label, interface in interfaces.items():
        if variant in interface.get("applies_to", VARIANTS):
            require(set(interface["objects"]) <= objects.keys(), f"Missing native {variant}/{label} interface")
    drawing = entry["drawing_basis"]
    require(objects[drawing["page"]] == "TechDraw::DrawPage" and
            objects[drawing["bom_page"]] == "TechDraw::DrawPage" and
            objects[drawing["bom_view"]] == "TechDraw::DrawViewSpreadsheet" and
            objects[drawing["bom_sheet"]] == "Spreadsheet::Sheet", f"Missing drawing/BOM in {variant}")
    require(all(objects[view] == "TechDraw::DrawViewPart" for view in drawing["views"]), f"Views for {variant}")
    for dimension in ("OverallLength", "OverallWidth", "OverallHeight"):
        data = doc.find(f"./ObjectData/Object[@name='{dimension}']")
        require(objects[dimension] == "TechDraw::DrawViewDimension" and
                data.find("./Properties/Property[@name='References2D']") is not None,
                f"Missing associative {dimension} in {variant}")
    title = doc.find("./ObjectData/Object[@name='AssemblyTitleBlock']")
    number = title.find("./Properties/Property[@name='EditableTexts']/Map/Item[@key='drawing_number']")
    require(number.attrib["value"] == drawing["drawing_number"], f"Wrong title block for {variant}")
    require(drawing["bom"]["W02-201"]["quantity"] == c["quantity"], f"Cylinder BOM count in {variant}")
    require(("ReceiverGate" in objects) == variant.startswith("B"), f"Wrong gate in {variant}")


def verify(check_git, replay):
    audit = read(TASK / "input_manifest.json")
    check_input_pins(audit)
    require(read(OUTPUT) == manifest(), "Delivery hashes or manifest differ")
    if check_git:
        for path in [*FILES, OUTPUT]:
            relative = path.relative_to(ROOT).as_posix()
            check_bytes(git_read("HEAD", relative), path.read_bytes(), relative)
    design, envelope = read(HERE / "design.json"), read(ENVELOPE)
    actual = read(RESULT / "screening.json")
    compare(actual, sizing(design, envelope), "screening")
    require(all(actual["checks"].values()), "Project-design screen failed")
    require(len(actual["source_phases_hydraulics_only"]) == 42, "Expected 42 source phase entries")
    require(actual["physical_status"] == "BLOCKED_INPUTS" and all(
        item["value"] is None and item["reason"] for item in actual["remaining_inputs"].values()),
        "Physical input status promoted")
    geometry = read(RESULT / "manifest.json")
    require(geometry["author_session"] == audit["runtime"] and geometry["versions"]["FreeCAD"] == "1.1.4"
            and geometry["versions"]["OpenCASCADE"] == "7.8.1", "Changed native CAD runtime information")
    require(set(geometry["variants"]) == set(VARIANTS) and min(geometry["clearances_mm"].values()) > 0,
            "CAD variant or clearance missing")
    refs = read(HERE / "interfaces.json")["interface_index"]
    for case in envelope["cases"].values():
        require(all(key.split("/")[1] in refs for key in case["r4_interface_ids"]), "Missing R3 interface key")
    for variant, entry in geometry["variants"].items():
        check_fcstd(RESULT / entry["path"], variant, entry, geometry, design, refs)
        poses = entry["checked_poses_stroke_lift_drop_mm"]
        require({0, design["cylinder"]["stroke"]} <= {pose[0] for pose in poses},
                f"Hard stroke ends missing from nominal CAD checks: {variant}")
    cat = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    target = cat["selection_basis"]
    cyl = design["cylinder"]
    require((target["per_cylinder_bore_mm"], target["per_cylinder_rod_mm"], target["cylinder_stroke_mm"],
             cat["components"]["hydraulic_cylinder"]["quantity"]) ==
            (cyl["bore"], cyl["rod"], cyl["stroke"], cyl["quantity"]), "COTS geometry differs from CAD")
    require(cat["components"]["hydraulic_cylinder"]["status"] == "CANDIDATE", "Supplier rating promoted")
    if replay is not None:
        rebuilt = read(replay / "manifest.json")
        for variant, entry in rebuilt["variants"].items():
            check_fcstd(replay / entry["path"], variant, entry, rebuilt, design, refs)
            del entry["sha256"]
        for entry in geometry["variants"].values():
            del entry["sha256"]
        compare(rebuilt, geometry, "Native FreeCAD rebuild")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    if args.write_manifest:
        OUTPUT.write_text(encode(manifest()), encoding="utf-8", newline="\n")
    try:
        verify(args.check_git, args.replay)
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: W02 nominal CAD, native TechDraw/BOM, static screening and scoped Git provenance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
