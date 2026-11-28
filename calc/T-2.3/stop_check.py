"""Воспроизвести STOP T-2.3 на утверждённых критериях и входах."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import traceback

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CRITERIA = ROOT / "ops/criteria/design_criteria.yaml"
SOURCES = yaml.safe_load((HERE / "sources.yaml").read_bytes())
PYTHON = os.environ["REV_PYTHON"]
FREECAD = os.environ["REV_FREECADCMD"]
GATE_ARGS = "REV_T23_STOP_FIXTURE_DIR"


def read_ref(key):
    file, _, address = SOURCES[key].partition("#")
    node = yaml.safe_load((ROOT / file).read_bytes())
    for field in address.split("."):
        node = node[field]
    return node


def json_write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def run(command, *, expected_codes=(0,), **extra_env):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **extra_env}
    result = subprocess.run(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=120)
    if result.returncode not in expected_codes:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise RuntimeError(f"{command[0]}: exit {result.returncode}\n{output[-4000:]}")
    return result


def diameter_volume_L(diameter_mm, length_mm):
    return math.pi / 4 * diameter_mm**2 * length_mm / 1e6


def cover_volumes_L(steps):
    """Cross-section integral of radial bores between the axial pocket and OD."""
    cover = read_ref("rear_cover")
    r_mm = cover["MA_branch_ID_mm"] / 2
    bore_r_mm = cover["through_ZSF_ID_mm"] / 2
    outer_r_mm = cover["OD_mm"] / 2
    angles = sorted(cover["MA_angles_from_Gmsh_X_deg"])
    gap_deg = min(right - left for left, right in zip(angles, angles[1:] + [angles[0] + 360]))
    assert len(angles) == cover["MA_branches"]
    assert 2 * math.degrees(math.asin(r_mm / bore_r_mm)) < gap_deg
    x_mm = cover["MA_centrelines_from_barrel_seat_mm"]
    assert r_mm < x_mm < cover["thickness_mm"] - r_mm
    assert steps % 2 == 0

    def strip_area_mm2(radius_mm, half_width_mm):
        return (half_width_mm * math.sqrt(radius_mm**2 - half_width_mm**2)
                + radius_mm**2 * math.asin(half_width_mm / radius_mm))

    def integrand(theta):
        width_mm = r_mm * math.cos(theta)
        return width_mm * (
            strip_area_mm2(outer_r_mm, width_mm) - strip_area_mm2(bore_r_mm, width_mm)
        )

    step = math.pi / steps
    samples = [integrand(-math.pi / 2 + step * i) for i in range(steps + 1)]
    integral_mm3 = step / 3 * (
        samples[0] + samples[-1] + 4 * math.fsum(samples[1:-1:2])
        + 2 * math.fsum(samples[2:-1:2])
    )
    return {
        "MA_radial_drillings": len(angles) * integral_mm3 / 1e6,
        "ZSF_axial_bore_in_cover": diameter_volume_L(
            cover["through_ZSF_ID_mm"], cover["thickness_mm"]
        ),
    }


def fixed_cover_cad(app, part):
    cover = read_ref("rear_cover")
    vector = app.Vector
    thickness_mm = cover["thickness_mm"]
    outer_r_mm = cover["OD_mm"] / 2
    drill_r_mm = cover["MA_branch_ID_mm"] / 2
    cap = part.makeCylinder(outer_r_mm, thickness_mm, vector(), vector(1, 0, 0))
    pocket = part.makeCylinder(cover["through_ZSF_ID_mm"] / 2, thickness_mm,
                               vector(), vector(1, 0, 0))
    origin = vector(cover["MA_centrelines_from_barrel_seat_mm"], 0, 0)
    radial = []
    for angle_deg in cover["MA_angles_from_Gmsh_X_deg"]:
        angle_rad = math.radians(angle_deg)
        axis = vector(0, math.cos(angle_rad), math.sin(angle_rad))
        cutout = part.makeCylinder(drill_r_mm, outer_r_mm + drill_r_mm, origin, axis)
        radial.append(cutout.common(cap).cut(pocket))
    assert all(shape.isValid() and len(shape.Solids) == 1 for shape in [pocket, *radial])
    return {
        "MA_radial_drillings": math.fsum(shape.Volume for shape in radial) / 1e6,
        "ZSF_axial_bore_in_cover": pocket.Volume / 1e6,
    }


def freecad_fixture(directory):
    import FreeCAD as app
    import Part

    width_mm, height_mm = read_ref("feed_window")
    depth_mm = SOURCES["feed_coupon_depth_mm"]
    doc = app.newDocument("FeedContactCoupon")
    try:
        for name, role, z_mm in (
            ("LinerContact", ["machine", "chamber_liner"], -depth_mm),
            ("FeedVolume", ["feed_path"], 0),
            ("HopperContact", ["machine", "hopper"], depth_mm),
        ):
            obj = doc.addObject("Part::Feature", name)
            obj.Shape = Part.makeBox(width_mm, height_mm, depth_mm, app.Vector(0, 0, z_mm))
            obj.addProperty("App::PropertyStringList", "RevRole")
            obj.RevRole = role
        doc.recompute()
        doc.saveAs(str(directory / "feed_contact.FCStd"))
    finally:
        app.closeDocument(doc.Name)
    json_write(directory / "cover_cad.json", fixed_cover_cad(app, Part))


def freecad_script(directory, source, **env):
    # FreeCAD caches its positional Python file. Keep that launcher in scratch.
    launcher = directory / "launch.py"
    launcher.write_text(
        "import runpy, sys\nsys.dont_write_bytecode = True\n"
        f"runpy.run_path({str(source)!r}, run_name='__main__')\n", encoding="utf-8",
    )
    return run([FREECAD, str(launcher)], **env)


def measure_feed_and_cover(directory):
    freecad_script(directory, Path(__file__).resolve(), **{GATE_ARGS: str(directory)})
    output = directory / "feed_gate.json"
    args = dict(model=str(directory / "feed_contact.FCStd"), roles=None,
                criteria=str(CRITERIA), out=str(output), gates=["G-FEED"])
    process = freecad_script(directory, ROOT / "ops/gates/geom_gates.py", REV_GATE_ARGS=json.dumps(args))
    report = json.loads(output.read_text(encoding="utf-8"))
    gate, = report["gates"]
    area_mm2 = math.prod(read_ref("feed_window"))
    connection = gate["details"]["connections"]["FeedVolume"]
    assert gate["status"] == "WARN" and gate["threshold"]["min_window_area_mm2"] is None
    assert connection["connected"] and gate["details"]["pairs"] == []
    for role in ("chamber_liner", "hopper"):
        assert math.isclose(connection[role][0]["contact_area_mm2"], area_mm2, abs_tol=1e-6)
    assert math.isclose(gate["value"], area_mm2, abs_tol=1e-6)
    report["input"] = "Тест плоского контакта 200 × 150 мм"
    report["exit_code"] = process.returncode
    return report, json.loads((directory / "cover_cad.json").read_text(encoding="utf-8"))


def ma_ligament():
    cover = read_ref("rear_cover")
    studs = read_ref("bolt_bore")
    r_mm = studs["PCD_mm"] / 2
    h_mm = studs["hole_diameter_mm"] / 2
    d_mm = cover["MA_branch_ID_mm"]
    bolt_angles = sorted(cover["M36_angles_from_Gmsh_X_deg"])
    assert len(bolt_angles) == studs["n"]
    half_pitch_deg = max(b - a for a, b in zip(
        bolt_angles, bolt_angles[1:] + [bolt_angles[0] + 360]
    )) / 2
    # The straight radial drill is best clocked midway between holes. Even a
    # curved same-diameter route crossing the bolt circle inside the cover
    # meets a section with clearance bounded above by the chord to a bolt.
    nominal_mm = r_mm * math.sin(math.radians(half_pitch_deg)) - h_mm - d_mm / 2
    bolt_circle_bound_mm = 2 * r_mm * math.sin(math.radians(half_pitch_deg) / 2) - h_mm - d_mm / 2
    assert math.isclose(nominal_mm, cover["MA_nominal_ligament_to_M36_mm"], abs_tol=1e-8)
    return {
        "nominal_mm": nominal_mm,
        "bolt_circle_upper_bound_mm": bolt_circle_bound_mm,
        "required_mm": SOURCES["ma_min_ligament_mm"],
        "nominal_shortfall_mm": SOURCES["ma_min_ligament_mm"] - nominal_mm,
        "MA_drilling_ID_mm": d_mm,
        "M36_hole_ID_mm": studs["hole_diameter_mm"],
        "M36_PCD_mm": studs["PCD_mm"],
        "from_barrel_seat_mm": cover["MA_centrelines_from_barrel_seat_mm"],
    }


def column_compliance():
    column = read_ref("columns")
    bore_mm, _ = read_ref("main_cylinder_bore_and_rod")
    cap_area_mm2 = math.pi * bore_mm**2 / 4
    proof_bar = yaml.safe_load(CRITERIA.read_bytes())["criteria"]["C-HYD-01"]["max_relief_bar"]
    pressure_MPa = proof_bar * 0.1
    force_N = pressure_MPa * cap_area_mm2
    section_mm2 = read_ref("column_count") * math.pi * column["diameter_mm"]**2 / 4
    displacement_mm = force_N * column["smooth_span_mm"] / (section_mm2 * read_ref("steel_modulus"))
    modulus_MPa = SOURCES["oil_effective_modulus_Pa"] / 1e6
    return {
        "pressure_bar": proof_bar,
        "force_N": force_N,
        "smooth_columns_displacement_mm": displacement_mm,
        "smooth_columns_equivalent_L": modulus_MPa / pressure_MPa * cap_area_mm2 * displacement_mm / 1e6,
    }


def oil_comparison(analytic, cad):
    cover = read_ref("rear_cover")
    radial_length_mm = cover["MA_branches"] * (cover["OD_mm"] - cover["through_ZSF_ID_mm"]) / 2
    legacy = [
        {"element": row["name"], "volume_L": diameter_volume_L(row["ID_mm"], row["length_mm"])}
        for row in read_ref("oil_route_reference")
    ]
    legacy.extend([
        {"element": "MA radial drillings", "volume_L": diameter_volume_L(
            cover["MA_branch_ID_mm"], radial_length_mm
        )},
        {"element": "ZSF axial bore in cover", "volume_L": analytic["ZSF_axial_bore_in_cover"]},
    ])
    cad_total_L = math.fsum(cad.values())
    analytic_total_L = math.fsum(analytic.values())
    delta_pct = 100 * abs(cad_total_L - analytic_total_L) / analytic_total_L
    assert delta_pct <= 2
    return {
        "scope": "Только сверления в крышке T-2.2; сопряжения и фактические трассы T-2.3 не определены",
        "T29b_reference_by_element": legacy,
        "T29b_total_L": math.fsum(row["volume_L"] for row in legacy),
        "fixed_cover_by_element_L": analytic,
        "fixed_cover_by_element_cad_L": cad,
        "fixed_cover_L": analytic_total_L,
        "fixed_cover_cad_L": cad_total_L,
        "delta_pct": delta_pct,
    }


def calc_scan(directory, fixed_cover_L, columns_L):
    source = ROOT / SOURCES["oil_gate_baseline"].partition("#")[0]
    original = source.read_bytes().decode("utf-8")
    base = yaml.safe_load(original)
    original_L = read_ref("oil_baseline_allowance")
    assert original_L == base["cycle_model"]["oil"]["cap_dead_L"]
    pattern = r"(?m)^([ \t]+cap_dead_L:[ \t]+)([0-9.]+)"
    assert len(list(re.finditer(pattern, original))) == 1
    cylinder = base["main_cylinder"]
    model = base["cycle_model"]
    oil_available_L = model["tank"]["oil_L"]
    cap_swept_L = diameter_volume_L(cylinder["bore_mm"], cylinder["stroke_mm"])
    rod_displacement_L = diameter_volume_L(model["mechanics"]["main_rod_mm"], cylinder["stroke_mm"])
    buffer_factor = SOURCES["TF_buffer_cap_factor"]
    max_cap_dead_L = (oil_available_L - rod_displacement_L) / buffer_factor - cap_swept_L
    cases = [("card_control", point) for point in SOURCES["scan_cap_dead_L"]]
    cases.extend([
        ("fixed_cover_only", original_L + fixed_cover_L),
        ("cover_and_smooth_columns_only", original_L + fixed_cover_L + columns_L),
    ])
    rows = []
    baseline_report = None
    for case, cap_L in sorted(cases, key=lambda row: row[1]):
        params = source
        if cap_L != original_L:
            diagnostic = re.sub(pattern, lambda match: f"{match[1]}{cap_L!r}", original, count=1)
            parsed = yaml.safe_load(diagnostic)
            assert parsed["cycle_model"]["oil"]["cap_dead_L"] == cap_L
            parsed["cycle_model"]["oil"]["cap_dead_L"] = original_L
            assert parsed == base
            params = directory / "diagnostic_params.yaml"
            params.write_bytes(diagnostic.encode("utf-8"))
        output = directory / "calc_gate.json"
        process = run(
            [PYTHON, "-B", "ops/gates/calc_gates.py", "--params", str(params.relative_to(ROOT)),
             "--criteria", str(CRITERIA.relative_to(ROOT)), "--out", str(output)],
            expected_codes=(0, 1),
        )
        report = json.loads(output.read_text(encoding="utf-8"))
        gates = {gate["id"]: gate for gate in report["gates"]}
        cycle = gates["G-CYCLE"]
        details = cycle["details"]
        assert details["method"] == "reference_model"
        buffer_min_L = details["fill"]["buffer_min_L"]
        assert math.isclose(buffer_min_L, buffer_factor * (cap_swept_L + cap_L) + rod_displacement_L)
        assert details["checks"]["fill_routes_admissible"] == (buffer_min_L <= oil_available_L)
        rows.append({
            "case": case, "cap_dead_L": cap_L, "cycle_s": cycle["value"],
            "rms_kW": details["rms_power_kW"],
            "TF_required_oil_L": buffer_min_L,
            "gates": {key: gate["status"] for key, gate in gates.items()},
            "failed_cycle_checks": [key for key, value in cycle["details"]["checks"].items() if not value],
            "exit_code": process.returncode,
        })
        if cap_L == original_L:
            baseline_report = report
    assert baseline_report is not None and baseline_report["overall"] == "PASS"
    assert original_L + fixed_cover_L > max_cap_dead_L
    return rows, baseline_report, {
        "available_oil_L": oil_available_L,
        "max_cap_dead_L": max_cap_dead_L,
        "max_external_and_compliance_allowance_L": max_cap_dead_L - original_L,
        "cap_swept_L": cap_swept_L, "rod_displacement_L": rod_displacement_L,
        "cap_factor": buffer_factor,
    }


def main():
    criterion_file = SOURCES["feed_criterion"].partition("#")[0]
    assert CRITERIA == ROOT / criterion_file
    assert "min_window_area_mm2" not in read_ref("feed_criterion")
    criteria_hash = hashlib.sha256(CRITERIA.read_bytes()).hexdigest()
    analytic = cover_volumes_L(SOURCES["simpson_steps"])
    refined = cover_volumes_L(2 * SOURCES["simpson_steps"])
    assert math.isclose(analytic["MA_radial_drillings"], refined["MA_radial_drillings"], abs_tol=1e-8)
    columns = column_compliance()
    with TemporaryDirectory(prefix="stop-check-", dir=HERE) as scratch:
        workdir = Path(scratch)
        feed_report, cover_cad = measure_feed_and_cover(workdir)
        assert feed_report["criteria_sha256"] == criteria_hash
        oil = oil_comparison(analytic, cover_cad)
        scan, baseline, buffer = calc_scan(
            workdir, oil["fixed_cover_L"], columns["smooth_columns_equivalent_L"],
        )
    assert baseline["criteria_sha256"] == criteria_hash
    assert hashlib.sha256(CRITERIA.read_bytes()).hexdigest() == criteria_hash
    ledger = read_ref("station_mass_reference")
    mass = ledger["machine_A_variants"]["with_end_collar"]
    outside_station_kg = read_ref("mass_outside_station")
    assert math.isclose(mass["t29b_kg"], outside_station_kg + ledger["station_kg"])
    json_write(HERE / "results.json", {
        "task": "T-2.3", "status": "STOP", "feed_fixture_gate_report": feed_report,
        "cover_MA_M36_ligament": ma_ligament(), "oil_diagnostics": oil,
        "column_compliance": columns, "cap_dead_scan": scan, "TF_buffer_limit": buffer,
        "T29b_base_gate_report": baseline,
        "ledger_reference": {"machine_with_end_collar_kg": mass["t29b_kg"],
                             "outside_station_kg": outside_station_kg,
                             "station_kg": ledger["station_kg"]},
    })


if GATE_ARGS in os.environ:
    try:
        freecad_fixture(Path(os.environ[GATE_ARGS]))
    except Exception:
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
    sys.stdout.flush()
    os._exit(0)
elif __name__ == "__main__":
    main()
