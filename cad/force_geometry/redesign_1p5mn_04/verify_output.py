"""Verify iteration 04 input pins, conditional results, native CAD and the catalog."""

import argparse
from hashlib import sha256
import json
import runpy
import subprocess
from xml.etree import ElementTree
from zipfile import ZipFile

import yaml

from screen import DATA, ROOT, SOURCE, TASK, Iteration04, encode, read, report, require

HERE = DATA.parent.parent / "cad/force_geometry/redesign_1p5mn_04"
CATALOG = ROOT / "drives/cots_catalog.yaml"
MANIFEST = TASK / "output_manifest.json"
VARIANTS = ("A-V1", "A-V2", "B-V1", "B-V2")
COMPARE = runpy.run_path(str(HERE.with_name("redesign_1p5mn") / "verify_output.py"))["compare"]


def relative(path):
    return path.relative_to(ROOT).as_posix()


def git_blob(revision, name):
    return subprocess.check_output(["git", "show", f"{revision}:{name}"], cwd=ROOT)


def matches_git(blob, data):
    if blob.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        return blob == (f"version https://git-lfs.github.com/spec/v1\noid sha256:{sha256(data).hexdigest()}\n"
                        f"size {len(data)}\n").encode()
    return blob == data


def files():
    return [
        *[HERE / name for name in ("screen.py", "build.py", "verify_output.py", "interfaces.json", "README.md")],
        *[TASK / name for name in ("task.json", "input_manifest.json", "input_audit.md")],
        DATA, CATALOG, SOURCE / "screening.json", SOURCE / "manifest.json",
        *[SOURCE / f"{variant}.FCStd" for variant in VARIANTS],
    ]


def verify_inputs(audit):
    base = audit["source_main_sha"]
    for name, digest in audit["input_git_blob_sha256"].items():
        require(sha256(git_blob(base, name)).hexdigest() == digest, f"R3 result pin changed: {name}")
    pins = read(ROOT / audit["upstream_inputs"])["input_sha256"]
    require(len(pins) == audit["upstream_input_count"], "Upstream pin count")
    for name, digest in pins.items():
        data = git_blob(base, name) if name == relative(CATALOG) else (ROOT / name).read_bytes()
        require(sha256(data).hexdigest() == digest and matches_git(git_blob(base, name), data), f"R3 input pin: {name}")
    claim = json.loads(git_blob(audit["claim_main_sha"], f"coordination/claims/{TASK.name}.json"))
    author = audit["author_sessions"][0]
    require(claim["status"] == "ACCEPTED_MAIN" and claim["source_main_sha"] == base
            and claim["owner_session"] == author["CODEX_SESSION_ID"] and claim["model_label"] == author["model_label"],
            "Author and main claim differ")


def verify_cad(audit, model, screening):
    native = read(SOURCE / "manifest.json")
    interfaces = read(HERE / "interfaces.json")
    require(native["versions"]["FreeCAD"] == "1.1.4" and native["versions"]["OpenCASCADE"] == "7.8.1"
            and native["author_session"] == audit["author_sessions"][0], "Native runtime or author differs")
    require(set(native["variants"]) == set(VARIANTS) and min(native["clearances_mm"].values()) > 0, "CAD coverage")
    c = model.c
    for variant, row in native["variants"].items():
        path = SOURCE / row["path"]
        require(path.name == f"{variant}.FCStd" and sha256(path.read_bytes()).hexdigest() == row["sha256"],
                f"Native file digest: {variant}")
        require({0, c["stroke"]} <= {pose[0] for pose in row["checked_poses_stroke_lift_drop_mm"]},
                f"Hard end pose missing: {variant}")
        require(row["moving_geometry_weight_N"] <= 2 * model.grav, f"Gravity budget: {variant}")
        with ZipFile(path) as fcstd:
            require(fcstd.testzip() is None, f"Damaged archive: {variant}")
            xml = ElementTree.fromstring(fcstd.read("Document.xml"))
        objects = {item.attrib["name"] for item in xml.findall("./Objects/Object")}
        props = xml.find("./ObjectData/Object[@name='Design']/Properties")
        for name, value in (("BoreDiameter", c["bore"]), ("RodDiameter", c["rod"]), ("RatedStroke", c["stroke"])):
            node = props.find(f"Property[@name='{name}']")
            require(float(node[0].attrib["value"]) == value, f"{variant}/{name}")
        for ref in interfaces["interface_index"].values():
            if variant in ref.get("applies_to", VARIANTS):
                require(set(ref["objects"]) <= objects, f"Missing interface objects: {variant}/{ref}")
        require("COTS: hydraulic_cylinder" in row["drawing_basis"]["bom"]["W02-201"]["specification"],
                f"Native BOM catalog reference: {variant}")
        if variant.startswith("B"):
            sweep = row["continuous_unloaded_sweeps"]
            require(sweep["lock_drop_mm"] == model.b["key_retract_down"]
                    and sweep["gate_lift_mm"] == model.b["gate_open_lift"]
                    and sweep["max_stroke_with_gate_closed_mm"] == screening["stroke"]["B_closed_work_limit_stroke_mm"],
                    f"Wrong B travel: {variant}")


def verify_catalog(model):
    catalog = yaml.safe_load(CATALOG.read_bytes())
    target = catalog["selection_basis"]
    c = model.c
    require(catalog["task_id"] == TASK.name and target["scoped_design"] == relative(DATA), "Wrong COTS design")
    require([target[name] for name in ("per_cylinder_bore_mm", "per_cylinder_rod_mm", "cylinder_stroke_mm",
                                       "cylinder_center_distance_mm")]
            == [c["bore"], c["rod"], c["stroke"], 2 * c["axis_offset"]], "COTS envelope")
    cylinder = catalog["components"]["hydraulic_cylinder"]
    require(cylinder["status"] == "CANDIDATE" and cylinder["model"] is None and cylinder["manufacturer"] is None
            and cylinder["quantity"] == c["quantity"], "COTS maturity or count")
    require(cylinder["per_cylinder_areas_mm2"] == {"cap": model.cap, "rod": model.rod, "annulus": model.annulus},
            "COTS effective areas")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-git", action="store_true")
    mode.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    audit = read(TASK / "input_manifest.json")
    verify_inputs(audit)
    actual = read(SOURCE / "screening.json")
    COMPARE(actual, json.loads(encode(report())), "iteration 04 replay")
    require(all(actual["checks"].values()) and len(actual["covered_case_ids"]) == 42, "Conditional screen failed")
    model = Iteration04()
    verify_cad(audit, model, actual)
    verify_catalog(model)
    manifest = {
        "task_id": TASK.name, "revision": 4, "author_sessions": audit["author_sessions"],
        "source_main_sha": audit["source_main_sha"], "claim_main_sha": audit["claim_main_sha"],
        "scope": actual["scope"], "physical_input_status": actual["physical_input_status"],
        "commands": {"screen": f"python {relative(HERE / 'screen.py')}",
                     "cad": f"FreeCAD 1.1.4 bundled python.exe {relative(HERE / 'build.py')} --out <directory>",
                     "verify": f"python {relative(HERE / 'verify_output.py')} --check-git"},
        "sha256": {relative(path): sha256(path.read_bytes()).hexdigest() for path in files()},
    }
    if args.write_manifest:
        MANIFEST.write_bytes(encode(manifest).encode())
    require(read(MANIFEST) == manifest, "Output hashes differ")
    if args.check_git:
        for path in (*files(), MANIFEST):
            require(matches_git(git_blob("HEAD", relative(path)), path.read_bytes()), f"Git evidence: {path}")
    print("PASS: W02 iteration 04 conditional replay, 4 native CAD assemblies, COTS and traceability")


if __name__ == "__main__":
    main()
