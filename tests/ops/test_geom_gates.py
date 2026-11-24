"""Run with pytest, or pass this file to freecadcmd for the CAD checks."""

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ops.gates import geom_gates

CRITERIA = ROOT / "ops/criteria/design_criteria.yaml"


def test_argument_contract(monkeypatch):
    args = {"model": "sample.FCStd", "roles": None, "criteria": "criteria.yaml",
            "out": "gate_report.json", "gates": ["G-CLEAR", "G-MASS"]}
    assert geom_gates.read_args(args) == (args, ["G-CLEAR", "G-MASS"])
    monkeypatch.setenv("REV_FREECADCMD", "X:/bin/freecadcmd.exe")
    assert geom_gates.freecadcmd_path() == "X:/bin/freecadcmd.exe"


def test_overall_statuses():
    assert geom_gates.overall_result([{"status": "NOT_AVAILABLE"}]) == ("WARN", 0)
    assert geom_gates.overall_result([{"status": "WARN"}, {"status": "FAIL"}]) == ("FAIL", 1)
    assert geom_gates.overall_result([{"status": "FAIL"}, {"status": "ERROR"}]) == ("FAIL", 2)


def run_command(raw_args):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if raw_args is None:
        env.pop("REV_GATE_ARGS", None)
    else:
        env["REV_GATE_ARGS"] = raw_args
    cmd = [geom_gates.freecadcmd_path(), "ops/gates/geom_gates.py"]
    return subprocess.run(
        cmd, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=120,
    )


def run_gate(workdir, model, exit_code, overall, roles=None, poses=None, gates=None, criteria=CRITERIA):
    out = workdir / "gate_report.json"
    out.unlink(missing_ok=True)
    args = {"model": str(model), "roles": str(roles) if roles else None,
            "criteria": str(criteria), "out": str(out)}
    if poses is not None:
        args["poses"] = str(poses)
    if gates is not None:
        args["gates"] = gates
    result = run_command(json.dumps(args))
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    assert result.returncode == exit_code, f"{args}: exit {result.returncode}\n{output[-4000:]}"
    assert out.is_file(), output[-4000:]
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["schema"] == "rev.gate_report/1"
    assert report["tool"] == "geom_gates"
    assert report["tool_version"] == geom_gates.TOOL_VERSION
    assert report["input"] == str(model)
    assert report["criteria_version"] == 1
    assert report["criteria_sha256"] == hashlib.sha256(criteria.read_bytes()).hexdigest()
    assert report["freecad_version"] == "1.1.4"
    assert report["overall"] == overall
    assert [gate["id"] for gate in report["gates"]] == (gates or list(geom_gates.GATE_SPECS))
    assert all(
        {"id", "status", "value", "threshold", "unit", "criteria_ids", "details"} <= gate.keys()
        for gate in report["gates"]
    )
    return {gate["id"]: gate for gate in report["gates"]}


def feature(container, name, shape):
    obj = container.newObject("Part::Feature", name) if hasattr(container, "newObject") else (
        container.addObject("Part::Feature", name)
    )
    obj.Shape = shape
    return obj


def set_role(obj, role):
    obj.addProperty("App::PropertyString", "RevRole")
    obj.RevRole = role


def save(app, doc, path):
    doc.recompute()
    doc.saveAs(str(path))
    app.closeDocument(doc.Name)


def check_all_gates(app, part, workdir):
    import yaml

    doc = app.newDocument("FeedFixture")
    point = app.Vector
    ram = doc.addObject("App::Part", "RamFrame")
    ram.Placement.Base = point(5, 0, 0)
    punch = ram.newObject("PartDesign::Body", "Punch")
    tip = punch.newObject("PartDesign::Feature", "PunchSolid")
    tip.Shape = part.makeBox(20, 20, 20, point(0, 7, 7))
    punch.Tip = tip
    punch.addProperty("App::PropertyStringList", "RevRole")
    punch.RevRole = ["punch", "moving"]
    punch.addProperty("App::PropertyString", "RevMaterial")
    punch.RevMaterial = "model steel"
    punch.addProperty("App::PropertyFloat", "RevDensity_kg_m3")
    punch.RevDensity_kg_m3 = 8000
    wall = part.makeBox(36, 34, 34)
    bore = part.makeBox(38, 20.4, 20.4, point(-1, 6.8, 6.8))
    window = part.makeBox(4, 4, 23, point(28, 14, 23))
    blank = feature(doc, "LinerBlank", wall)
    cutout = feature(doc, "LinerCutout", bore.fuse(window))
    liner = doc.addObject("Part::Cut", "Liner")
    liner.Base = blank
    liner.Tool = cutout
    path = feature(doc, "FeedVolume", part.makeBox(4, 4, 22, point(28, 14, 24)))
    set_role(path, "feed_path")
    hopper = feature(doc, "Hopper", part.makeBox(4, 4, 2, point(28, 14, 46)))
    set_role(hopper, "hopper")
    model = workdir / "OpenWindow.FCStd"
    doc.recompute()
    doc.saveAs(str(model))
    hopper.Placement.Base = point(0, 0, 1)
    floating = workdir / "FloatingHopper.FCStd"
    doc.recompute()
    doc.saveAs(str(floating))
    hopper.Placement.Base = point(0, 0, 0)
    path.Placement.Base = point(0, 0, 15)
    disconnected = workdir / "FloatingFeed.FCStd"
    doc.recompute()
    doc.saveAs(str(disconnected))
    path.Placement.Base = point(0, 0, 0)
    full_path = path.Shape.copy()
    path.Shape = part.makeCompound([
        part.makeBox(4, 4, 14, point(28, 14, 24)),
        part.makeBox(4, 4, 7, point(28, 14, 39)),
    ])
    split = workdir / "SplitFeed.FCStd"
    doc.recompute()
    doc.saveAs(str(split))
    path.Shape = full_path
    cutout.Shape = bore
    blocked = workdir / "ClosedWindow.FCStd"
    save(app, doc, blocked)
    roles = workdir / "roles.yaml"
    roles.write_text(
        "Punch: {role: feed_path, material: from YAML, density_kg_m3: 1000}\n"
        "Liner: {role: chamber_liner, material: steel}\n",
        encoding="utf-8",
    )
    report = run_gate(workdir, model, 0, "WARN", roles=roles)
    assert {key: gate["status"] for key, gate in report.items()} == {
        "G-ENV": "PASS", "G-MASS": "PASS", "G-COLL": "PASS", "G-FEED": "WARN", "G-CLEAR": "PASS",
    }, report
    assert report["G-ENV"]["value"] == [36, 34, 48]
    assert report["G-ENV"]["details"]["body_count"] == 3
    assert report["G-COLL"]["details"]["pairs"] == []
    assert report["G-FEED"]["details"]["paths"] == ["FeedVolume"]
    assert report["G-FEED"]["details"]["reason"] == "порог окна не задан"
    assert report["G-FEED"]["unit"] == "mm2"
    assert math.isclose(report["G-FEED"]["value"], 108.8, abs_tol=1e-8)
    assert math.isclose(report["G-CLEAR"]["value"], 0.2, abs_tol=1e-8)
    mass = report["G-MASS"]["details"]
    assert math.isclose(mass["moving_mass_kg"], 0.064, abs_tol=1e-12)
    parts = {obj["name"]: obj for obj in mass["bodies"]}
    assert parts["Punch"]["material"] == "model steel"
    assert parts["Punch"]["density_kg_m3"] == 8000
    assert parts["Liner"]["material"] == "steel"
    assert parts["Liner"]["density_kg_m3"] == 7850
    assert parts["Hopper"]["roles"] == ["hopper", "machine"]
    criteria = yaml.safe_load(CRITERIA.read_bytes())
    criteria["criteria"]["C-FEEDPATH-01"]["min_window_area_mm2"] = 100
    test_criteria = workdir / "window_criteria.yaml"
    test_criteria.write_text(yaml.safe_dump(criteria, allow_unicode=True), encoding="utf-8")
    run_gate(workdir, model, 0, "PASS", roles=roles, criteria=test_criteria)
    criteria["criteria"]["C-FEEDPATH-01"]["min_window_area_mm2"] = 110
    test_criteria.write_text(yaml.safe_dump(criteria, allow_unicode=True), encoding="utf-8")
    report = run_gate(workdir, model, 1, "FAIL", roles=roles, gates=["G-FEED"], criteria=test_criteria)
    assert "площадь окна меньше порога" in report["G-FEED"]["details"]["reasons"]
    for model, missing in ((floating, "hopper"), (disconnected, "chamber_liner")):
        report = run_gate(workdir, model, 1, "FAIL", roles=roles, gates=["G-FEED"])
        contact = report["G-FEED"]["details"]["connections"]["FeedVolume"]
        assert missing in contact["missing_contact"], contact
    report = run_gate(workdir, split, 1, "FAIL", roles=roles, gates=["G-FEED"])
    contact = report["G-FEED"]["details"]["connections"]["FeedVolume"]
    assert "missing_contact" not in contact and contact["connected"] is False, contact
    report = run_gate(workdir, blocked, 1, "FAIL", roles=roles, gates=["G-FEED"])
    pair, = report["G-FEED"]["details"]["pairs"]
    assert pair["bodies"] == ["FeedVolume", "Liner"]
    assert math.isclose(pair["common_volume_mm3"], 108.8, abs_tol=1e-8)


def check_collision_and_envelope(app, part, workdir):
    doc = app.newDocument("PoseFixture")
    feature(doc, "Left", part.makeBox(10, 10, 10))
    prototype = feature(doc, "Template", part.makeBox(10, 10, 10))
    prototype.Visibility = False
    slide = doc.addObject("App::Part", "Slide")
    slide.Placement.Base = app.Vector(15, 0, 0)
    right = slide.newObject("App::Link", "Right")
    right.setLink(prototype)
    model = workdir / "PoseFixture.FCStd"
    save(app, doc, model)
    report = run_gate(workdir, model, 0, "PASS", gates=["G-ENV", "G-MASS", "G-COLL"])
    assert all(gate["status"] == "PASS" for gate in report.values())
    poses = workdir / "poses.yaml"
    poses.write_text(
        "touch:\n  Slide: [-5, 0, 0]\n"
        "overlap:\n  Slide: [-7, 0, 0]\n"
        "extended:\n  Slide: [20, 0, 0]\n"
        "opposite:\n  Slide: [-40, 0, 0]\n",
        encoding="utf-8",
    )
    report = run_gate(workdir, model, 1, "FAIL", poses=poses, gates=["G-ENV", "G-COLL"])
    assert report["G-ENV"]["status"] == "PASS"
    assert report["G-ENV"]["value"] == [70, 10, 10]
    assert report["G-ENV"]["details"]["per_pose_mm"]["nominal"] == [25, 10, 10]
    pair, = report["G-COLL"]["details"]["pairs"]
    assert pair["pose"] == "overlap"
    assert pair["bodies"] == ["Left", "Right"]
    assert math.isclose(pair["common_volume_mm3"], 200, abs_tol=1e-8)


def check_mass_and_exit_codes(app, part, workdir):
    doc = app.newDocument("CubeFixture")
    feature(doc, "Cube", part.makeBox(1000, 1000, 1000))
    model = workdir / "Cube.FCStd"
    save(app, doc, model)
    report = run_gate(workdir, model, 1, "FAIL", gates=["G-MASS", "G-FEED", "G-CLEAR"])
    assert report["G-MASS"]["unit"] == "kg"
    assert math.isclose(report["G-MASS"]["value"], 7850, rel_tol=0.001)
    assert report["G-FEED"]["details"]["reason"] == "нет тела feed_path"
    assert report["G-CLEAR"]["status"] == "FAIL"
    roles = workdir / "cube_roles.yaml"
    roles.write_text("Cube: {density_kg_m3: 4500}\n", encoding="utf-8")
    report = run_gate(workdir, model, 0, "WARN", roles=roles, gates=["G-MASS"])
    assert report["G-MASS"]["status"] == "WARN"
    assert math.isclose(report["G-MASS"]["value"], 4500, abs_tol=1e-8)
    report = run_gate(workdir, workdir / "Missing.FCStd", 2, "FAIL", gates=["G-MASS"])
    assert report["G-MASS"]["status"] == "ERROR"


def clearance_pair(app, part, doc, suffix, y_mm, gap_mm, punch_x_mm=-2):
    point = app.Vector
    bore = part.makeBox(8, 10, 10, point(-1, y_mm + 5, 5))
    liner = feature(doc, "Liner" + suffix, part.makeBox(6, 20, 20, point(0, y_mm, 0)).cut(bore))
    set_role(liner, "chamber_liner")
    width_mm = 10 - 2 * gap_mm
    punch = feature(doc, "Punch" + suffix, part.makeBox(
        5, width_mm, width_mm, point(punch_x_mm, y_mm + 5 + gap_mm, 5 + gap_mm)
    ))
    set_role(punch, "punch")
    return punch, liner


def check_clearance_pairs(app, part, workdir):
    doc = app.newDocument("ClearancePairs")
    _, good = clearance_pair(app, part, doc, "Good", 0, 0.1)
    good.addProperty("App::PropertyString", "RevStrokeAxis")
    good.RevStrokeAxis = "X"
    bad, _ = clearance_pair(app, part, doc, "Bad", 40, 0.8)
    model = workdir / "ClearancePairs.FCStd"
    doc.recompute()
    doc.saveAs(str(model))
    bad.addProperty("App::PropertyLink", "RevPair")
    bad.RevPair = good
    labelled = workdir / "ExplicitPair.FCStd"
    save(app, doc, labelled)
    gate, = run_gate(workdir, model, 1, "FAIL", gates=["G-CLEAR"]).values()
    assert math.isclose(gate["value"], 0.8, abs_tol=1e-8), gate
    good_pair, bad_pair = gate["details"]["pairs"]
    assert good_pair["bodies"] == ["PunchGood", "LinerGood"]
    assert good_pair["status"] == "PASS"
    assert math.isclose(good_pair["clearance_mm"], 0.1, abs_tol=1e-8)
    assert bad_pair["bodies"] == ["PunchBad", "LinerBad"]
    assert bad_pair["status"] == "FAIL"
    assert bad_pair["axial_overlap_mm"] == 3
    gate, = run_gate(workdir, labelled, 1, "FAIL", gates=["G-CLEAR"]).values()
    assert gate["details"]["pairs"][1]["bodies"] == ["PunchBad", "LinerGood"]
    assert gate["details"]["pairs"][1]["clearance_mm"] is None


def check_clearance_positions(app, part, workdir):
    doc = app.newDocument("ClearancePositions")
    clearance_pair(app, part, doc, "Contact", 0, 0)
    clearance_pair(app, part, doc, "Overlap", 40, -0.1)
    punch, liner = clearance_pair(app, part, doc, "Outside", 80, 0.1, punch_x_mm=-5.05)
    assert punch.Shape.distToShape(liner.Shape)[0] < 0.3
    rotated = clearance_pair(app, part, doc, "Rotated", 120, 0.1)
    for obj in rotated:
        shape = obj.Shape.copy()
        shape.rotate(app.Vector(0, 120, 0), app.Vector(0, 0, 1), 37)
        obj.Shape = shape
    model = workdir / "ClearancePositions.FCStd"
    save(app, doc, model)
    report = run_gate(workdir, model, 1, "FAIL", gates=["G-CLEAR", "G-COLL"])
    contact, overlap, outside, rotated_pair = report["G-CLEAR"]["details"]["pairs"]
    assert contact["clearance_mm"] == contact["common_volume_mm3"] == 0, contact
    assert contact["status"] == "PASS"
    assert overlap["status"] == "FAIL"
    assert overlap["related_gate"] == "G-COLL", overlap
    assert math.isclose(overlap["common_volume_mm3"], report["G-COLL"]["value"], abs_tol=1e-8)
    assert outside["axial_overlap_mm"] == 0
    assert outside["status"] == "FAIL"
    assert outside["reason"] == "пуансон не в камере в номинальной позе"
    assert rotated_pair["status"] == "PASS", rotated_pair
    assert math.isclose(rotated_pair["clearance_mm"], 0.1, abs_tol=1e-8), rotated_pair


def check_geometry_inputs(app, part, workdir):
    doc = app.newDocument("GeometryInputs")
    point = app.Vector
    box = part.makeBox(2, 2, 2)
    face = next(face for face in box.Faces if face.CenterOfMass.z == 0)
    profile = feature(doc, "Profile", face)
    extrusion = doc.addObject("Part::Extrusion", "Extrusion")
    extrusion.Base = profile
    extrusion.Dir = point(0, 0, 3)
    extrusion.Solid = True
    mirror = doc.addObject("Part::Mirroring", "Mirror")
    mirror.Source = extrusion
    mirror.Normal = point(1, 0, 0)
    mirror.Base = point(20, 0, 0)
    scale = doc.addObject("Part::Scale", "Scale")
    scale.Base = mirror
    scale.UniformScale = 2
    offset_source = feature(doc, "OffsetSource", part.makeBox(5, 5, 5, point(0, 20, 0)))
    offset = doc.addObject("Part::Offset", "Offset")
    offset.Source = offset_source
    offset.Value = 1
    thickness_source = feature(doc, "ThicknessSource", part.makeBox(5, 5, 5, point(0, 40, 0)))
    thickness = doc.addObject("Part::Thickness", "Thickness")
    thickness.Faces = (thickness_source, ["Face6"])
    thickness.Value = 1
    feature(doc, "Shell", part.makeShell(box.Faces))
    model = workdir / "GeometryInputs.FCStd"
    doc.recompute()
    expected = {obj.Name: obj.Shape.Volume for obj in (scale, offset, thickness)}
    assert expected["Offset"] > 0 and expected["Thickness"] > 0, expected
    save(app, doc, model)
    gate, = run_gate(workdir, model, 0, "WARN", gates=["G-MASS"]).values()
    volumes = {body["name"]: body["volume_mm3"] for body in gate["details"]["bodies"]}
    assert volumes.keys() == expected.keys(), volumes
    assert all(math.isclose(value, expected[name], abs_tol=1e-8) for name, value in volumes.items())
    assert math.isclose(volumes["Scale"], 96, abs_tol=1e-8), volumes
    assert gate["details"]["bodies_without_solids"] == [{"name": "Shell", "label": "Shell"}]


def check_invalid_args(workdir):
    out = workdir / "args_error.json"
    for raw_args, fragment in ((None, "REV_GATE_ARGS is missing"), ("{", "Expecting")):
        result = run_command(raw_args)
        assert result.returncode == 2 and fragment.encode() in result.stderr, result
    args = {"out": str(out), "model": "model.FCStd", "roles": None, "criteria": str(CRITERIA),
            "gates": ["G-NOT-A-GATE"]}
    result = run_command(json.dumps(args))
    assert result.returncode == 2, result
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["overall"] == "ERROR" and "REV_GATE_ARGS.gates" in report["error"], report


def check_freecad(app, part, workdir):
    check_all_gates(app, part, workdir)
    print("PASS all five gates, role precedence, window area, liner and hopper contacts", flush=True)
    check_collision_and_envelope(app, part, workdir)
    print("PASS nominal and posed envelope, touching and 200 mm3 collision", flush=True)
    check_mass_and_exit_codes(app, part, workdir)
    print("PASS steel density, missing roles, and exit codes 0/1/2", flush=True)
    check_clearance_pairs(app, part, workdir)
    check_clearance_positions(app, part, workdir)
    print("PASS worst clearance, RevPair, zero gap, insert position and liner collision", flush=True)
    check_geometry_inputs(app, part, workdir)
    print("PASS consumed extrusion, mirror, scale, offset and thickness inputs, shell warning", flush=True)
    check_invalid_args(workdir)
    print("PASS missing and invalid REV_GATE_ARGS diagnostics", flush=True)


def test_freecad_geometry(tmp_path):
    import pytest

    app = pytest.importorskip("FreeCAD")
    part = pytest.importorskip("Part")
    check_freecad(app, part, tmp_path)


def embedded_main():
    import FreeCAD as app
    import Part

    scratch = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="geom-gates-", dir=scratch) as directory:
        check_freecad(app, Part, Path(directory))


if __name__ == "__main__" or any(
    Path(arg).name == "test_geom_gates.py" and Path(arg).resolve() == Path(__file__).resolve()
    for arg in sys.argv[1:]
):
    try:
        embedded_main()
    except Exception:
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
    sys.stdout.flush()
    os._exit(0)
