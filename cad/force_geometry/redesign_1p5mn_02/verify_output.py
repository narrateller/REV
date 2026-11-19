"""Verify the revised W02 B receiver load screen and delivery artifacts."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree
from zipfile import ZipFile

from screen_contact import BASE, HERE, KEYS, REGISTRY, RESULT, ROOT, SEAT, TASK, VARIANTS, contact_faces, encode, geometry, read
from screen_contact import require, screening

sys.path.insert(0, str(ROOT))
from cad.force_geometry.redesign_1p5mn.verify_output import check_bytes, check_fcstd, compare, git_read, property_value

CLAIM = f"coordination/claims/{TASK.name}.json"
OUTPUT = TASK / "output_manifest.json"
FILES = [
    REGISTRY, TASK / "input_audit.md", TASK / "input_manifest.json",
    *[HERE / name for name in ("README.md", "interfaces.json", "screen_contact.py", "build_native.py", "verify_output.py")],
    RESULT / "manifest.json", RESULT / "screening.json",
    *[RESULT / f"{variant}.FCStd" for variant in VARIANTS],
]


def digest(data):
    return sha256(data).hexdigest()


def delivery_manifest(audit):
    rel = HERE.relative_to(ROOT).as_posix()
    return {
        "task_id": TASK.name, "scope": "CALCULATED_ASSUMED",
        "source_main_sha": audit["source_main_sha"], "claim_main_sha": audit["claim_main_sha"],
        "author_sessions": [audit["runtime"]],
        "delivery_sha256": {path.relative_to(ROOT).as_posix(): digest(path.read_bytes()) for path in FILES},
        "commands": {"contact": f"python {rel}/screen_contact.py",
                     "native": f"FreeCAD 1.1.4 bundled python.exe {rel}/build_native.py",
                     "verify": f"python {rel}/verify_output.py --check-git",
                     "native_replay": f"python {rel}/verify_output.py --check-git --replay <path passed to build --out>"},
    }


def check_input_pins(audit):
    base, runtime = audit["source_main_sha"], audit["runtime"]
    claim = json.loads(git_read(audit["claim_main_sha"], CLAIM))
    require(claim["task_id"] == TASK.name and claim["role"] == "R4" and claim["status"] == "ACCEPTED_MAIN"
            and claim["source_main_sha"] == base and claim["owner_session"] == runtime["CODEX_SESSION_ID"]
            and claim["model_label"] == runtime["model_label"], "Wrong task, source or author claim")
    proposed = datetime.fromisoformat(claim["proposed_at_utc"])
    expires = datetime.fromisoformat(claim["lease_expires_at"])
    require((expires - proposed).total_seconds() == 86400, "Unexpected claim lease")
    confirmed = audit["input_git_blob_sha256"]
    for path, expected in read(TASK / "task.json")["input_git_blob_sha256"].items():
        require(confirmed[path] == expected, f"Changed task input pin: {path}")
    for path, expected in confirmed.items():
        pin = git_read(base, path)
        require(digest(pin) == expected, f"Wrong source SHA-256: {path}")
        check_bytes(pin, (ROOT / path).read_bytes(), path)
    require(audit["revision_02_scoped_registry"] == REGISTRY.relative_to(ROOT).as_posix(),
            "Wrong revision 02 input registry")


def check_native(out, manifest, design, dataset, parent_interfaces):
    require(set(manifest["variants"]) == set(VARIANTS), "Expected both B assemblies")
    versions = manifest["versions"]
    require(versions["FreeCAD"] == "1.1.4" and versions["OpenCASCADE"] == "7.8.1"
            and ".".join(versions["FreeCAD_build"][:3]) == versions["FreeCAD"], "Unexpected CAD runtime")
    require(min(manifest["clearances_mm"].values()) > 0, "Invalid CAD clearances")
    b, c = design["receiver"], design["cylinder"]
    for variant, entry in manifest["variants"].items():
        path = out / f"{variant}.FCStd"
        require(path.name == entry["path"], f"Unexpected CAD path for {variant}")
        check_fcstd(path, variant, entry, manifest, design, parent_interfaces)
        with ZipFile(path) as archive:
            doc = ElementTree.fromstring(archive.read("Document.xml"))
        objects = {obj.attrib["name"]: obj for obj in doc.findall("./ObjectData/Object")}
        meta = objects["Design"]
        require(property_value(meta, "Revision", "String") == f"{design['id']} r{dataset['revision']}",
                "Wrong native design revision")
        for field, dimension in (("ReceiverKeyWidth", "key_width"), ("ReceiverKeyHeight", "key_height"),
                                 ("ReceiverKeyDrop", "key_retract_down"), ("ReceiverGateHeight", "gate_height")):
            require(float(property_value(meta, field, "Float")) == b[dimension], f"Wrong CAD dimension {field}")
        for part, pose_x, pose_z in (("ReceiverGate", "GateAxialTakeup", "GateLift"),
                                    ("ReceiverLock1", "LockAxialTakeup", "LockDrop"),
                                    ("ReceiverLock2", "LockAxialTakeup", "LockDrop")):
            expressions = objects[part].findall("./Properties/Property[@name='ExpressionEngine']/ExpressionEngine/*")
            sign = "" if part == "ReceiverGate" else "-"
            require({e.attrib["path"]: e.attrib["expression"] for e in expressions} ==
                    {".Placement.Base.x": f"Design.{pose_x}", ".Placement.Base.z": f"{sign}Design.{pose_z}"},
                    f"Motion expressions lost for {variant}/{part}")
        for prefix, ref in dataset["material_refs"].items():
            names = [name for name in objects if name in {prefix, f"{prefix}1", f"{prefix}2"}]
            require(names and all(property_value(objects[name], "AssumedMaterial", "String") ==
                                  design["materials"][ref]["material"] for name in names), f"CAD material: {prefix}")
        poses = entry["checked_poses_stroke_lift_drop_mm"]
        sweep = entry["continuous_unloaded_sweeps"]
        require({0, c["stroke"]} <= {pose[0] for pose in poses} and
                sweep["lock_drop_mm"] == b["key_retract_down"] and sweep["gate_lift_mm"] == b["gate_open_lift"],
                "Missing hard stops or receiver travel")
        require(any(s == sweep["max_stroke_with_gate_closed_mm"] and lift == drop == 0 for s, lift, drop in poses),
                "Missing closed stop travel check")
        faces = entry["contacts"]
        require(set(faces) == {"1", "2"}, "Missing key contact faces")
        for y_sign, face in zip((-1, 1), (faces["1"], faces["2"])):
            edge = b["key_edge_chamfer"]
            key_bounds = sorted(y_sign * y for y in (b["key_inner_y"] + edge, b["key_inner_y"] + b["key_width"] - edge))
            z = b["key_height"] / 2 - edge
            compare(face["key_front_yz_bbox_mm"], [float(y) for y in [*key_bounds, -z, z]], "CAD key contact bounds")
            area = (b["key_width"] - 2 * edge) * (b["key_height"] - 2 * edge)
            seat_area = (b["gate_width"] / 2 - b["seat_inner_y"]) * b["gate_height"]
            expected = {"gate_key": area, "key_backing": area, "gate_seat": seat_area, "seat_head": seat_area,
                        "backing_head": b["key_width"] * (b["key_height"] + b["key_retract_down"])}
            require(set(face["areas_mm2"]) == set(expected) and all(isclose(area, face["areas_mm2"][name])
                    for name, area in expected.items()), "Incomplete receiver axial load path in CAD")


def check_nominal_full_contact(report, receiver):
    force = report["compression_along_positive_x_N"]
    for path, edge in ((KEYS, receiver["key_edge_chamfer"]), (SEAT, 0)):
        pads = contact_faces(receiver, edge, path == SEAT)
        positive = pads[1]
        lo, hi, z = positive[0][0], positive[1][0], positive[2][1]
        area = 4 * (hi - lo) * z
        y_squared = area * (lo**2 + lo * hi + hi**2) / 3
        z_squared = area * z**2 / 3
        for row in report["paths"][path]["nominal_by_eccentricity"]:
            ey, ez = row["eccentricity_yz_mm"]
            pressure = [force * (1 / area + ey * y / y_squared + ez * zz / z_squared)
                        for pad in pads for y, zz in pad]
            require(min(pressure) > 0 and isclose(max(pressure), row["peak_MPa"], rel_tol=1e-10),
                    f"R4 full-contact formula disagrees with clipped integration: {path}/{ey},{ez}")


def verify(check_git, replay):
    audit = read(TASK / "input_manifest.json")
    check_input_pins(audit)
    require(read(OUTPUT) == delivery_manifest(audit), "Delivery SHA-256 manifest mismatch")
    if check_git:
        for path in [*FILES, OUTPUT]:
            relative = path.relative_to(ROOT).as_posix()
            check_bytes(git_read("HEAD", relative), path.read_bytes(), relative)
    _, design, dataset = geometry()
    interface = read(HERE / "interfaces.json")
    parent = read(BASE / "interfaces.json")["interface_index"]
    require(interface["applies_to"] == list(VARIANTS) and interface["revision"] == design["revision"]
            and set(interface["interface_overrides"]) <= set(parent), "Invalid interface overlay")
    report = read(RESULT / "screening.json")
    compare(report, json.loads(encode(screening())), "Contact screening replay")
    check_nominal_full_contact(report, design["receiver"])
    require(all(report["checks"].values()) and report["paths"][KEYS]["sensitivity_factor"] >= report["required_factor"],
            "The B key contact criterion failed")
    require(report["physical_state_evaluation"] == "BLOCKED_INPUTS" and report["physical_sections_4_5_6"] ==
            "NOT_RUN", "Physical readiness status promoted")
    manifest = read(RESULT / "manifest.json")
    require(manifest["author_session"] == audit["runtime"] and manifest["dataset_id"] == dataset["dataset_id"]
            and manifest["revision"] == dataset["revision"], "CAD provenance differs from scoped inputs")
    check_native(RESULT, manifest, design, dataset, parent)
    if replay is not None:
        built = read(replay / "manifest.json")
        check_native(replay, built, design, dataset, parent)
        for data in (built, manifest):
            for entry in data["variants"].values():
                del entry["sha256"]
        compare(built, manifest, "Native FreeCAD replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    try:
        if args.write_manifest:
            OUTPUT.write_text(encode(delivery_manifest(read(TASK / "input_manifest.json"))), encoding="utf-8", newline="\n")
        verify(args.check_git, args.replay)
    except (AttributeError, KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: B receiver contact screen, signed load sweep, native CAD and Git provenance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
