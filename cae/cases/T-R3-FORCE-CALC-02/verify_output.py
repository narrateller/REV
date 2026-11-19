"""Verify pinned inputs, balance identities, engineering verdict and saved W02 results."""

import argparse
from collections import Counter
from hashlib import sha256
from itertools import product
import json
from math import isclose, pi
import re
import subprocess
import sys
from xml.etree import ElementTree
from zipfile import ZipFile

import yaml

from contacts import beam_end, deflection
from force_calc import (ASSUMED, BASIS, BLOCKED, DESIGN, ENVELOPE, FREE, KEYS, NATIVE, PACKAGE, PARAMS,
                        ROOT, SEAT, W02, case_samples, drives, extrema, pressure_samples, read, round_values,
                        single_branch)

TASK = PACKAGE.name
HERE = PACKAGE.relative_to(ROOT).as_posix()
CATALOG = "baselines/operator-fork-20261118/state_catalog_index.json"
TASK_PATH = f"coordination/tasks/{TASK}/task.json"
CLAIM = f"coordination/claims/{TASK}.json"
MANIFEST = f"{HERE}/input_manifest.json"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def git(rev, path):
    reference = f"{rev}:{path}" if rev else f":{path}"
    return subprocess.check_output(["git", "show", reference], cwd=ROOT)


def digest(data):
    return sha256(data).hexdigest()


def encode(data, compact=False):
    return (json.dumps(round_values(data), allow_nan=False, ensure_ascii=False,
                       indent=None if compact else 2, separators=(",", ":") if compact else None) + "\n").encode()


def check_inputs(model, git_mode):
    audit = read(MANIFEST)
    task = read(TASK_PATH)
    pins = audit["input_sha256"]
    require(all(pins[path] == value for path, value in task["inputs"].items()), "Task input pin mismatch")
    require(pins[CATALOG] and pins[BASIS] and read(BASIS)["dataset_id"] == "REV_DESIGN_BASIS"
            and read(BASIS)["revision"] == 1, "Design basis or catalogue mismatch")
    for path, expected in pins.items():
        data = (ROOT / path).read_bytes()
        require(digest(data) == expected, f"Input SHA-256 mismatch: {path}")
        if git_mode:
            blob = git(audit["source_main_sha"], path)
            if blob.startswith(b"version https://git-lfs.github.com/spec/v1"):
                oid = re.search(rb"^oid sha256:([a-f0-9]{64})\r?$", blob, re.M)
                size = re.search(rb"^size (\d+)\r?$", blob, re.M)
                require(oid and size and oid[1].decode() == expected and int(size[1]) == len(data), f"LFS {path}")
            else:
                require(blob == data, f"Pinned Git content mismatch: {path}")
    if git_mode:
        claim = json.loads(git(audit["claim_main_sha"], CLAIM))
        actor = audit["author_sessions"][0]
        require(claim["status"] == "ACCEPTED_MAIN" and claim["owner_session"] == actor["CODEX_SESSION_ID"]
                and claim["model_label"] == actor["model_label"] and claim["source_main_sha"] == audit["source_main_sha"],
                "Claim identity mismatch")
    c, s, limits = model.c, model.s, model.l
    cots = yaml.safe_load((ROOT / "drives/cots_catalog.yaml").read_bytes())
    cyl = cots["components"]["hydraulic_cylinder"]
    selection = cots["selection_basis"]
    require([str(cyl[k]) for k in ("bore_diameter", "rod_diameter", "stroke", "max_pressure")]
            == [f"{c['bore']} mm", f"{c['rod']} mm", f"{c['stroke']} mm", f"{limits['supply_bar'][1]} bar"]
            and cyl["quantity"] == c["quantity"] == 2 and cyl["status"] == "CANDIDATE"
            and selection["design_envelope_supply_bar"] == limits["supply_bar"]
            and selection["guided_carriage_station_distance_mm"] == s["guide_bogie_span"]
            and selection["cylinder_center_distance_mm"] == 2 * c["axis_offset"]
            and cots["components"]["guide_pads"]["required_contact_limit_MPa"] ==
            model.m["guide_pad"]["assumed_maximum_contact_pressure_MPa"], "Native/COTS geometry, BC or limits differ")
    require(tuple(cyl["pressure_and_loss_targets"].values()) == (
        limits["supply_drop_bar"], limits["opposing_port_bar"], limits["cylinder_loss_fraction"],
        limits["guide_sliding_friction_limit"]), "COTS pressure losses differ from model")
    interfaces = read(f"{DESIGN}/interfaces.json")["interface_index"]
    for variant, entry in model.native["variants"].items():
        path = f"{NATIVE}/{entry['path']}"
        require(pins[path] == entry["sha256"], f"FCStd SHA-256 mismatch: {variant}")
        with ZipFile(ROOT / path) as archive:
            require(archive.testzip() is None, f"Invalid FCStd: {variant}")
            doc = ElementTree.fromstring(archive.read("Document.xml"))
        props = doc.find("./ObjectData/Object[@name='Design']/Properties")
        for name, value in (("BoreDiameter", c["bore"]), ("RodDiameter", c["rod"]), ("RatedStroke", c["stroke"]),
                            ("StrokePosition", c["rear_reserve"]), ("GuideStationCenterDistance", s["guide_bogie_span"])):
            require(float(props.find(f"./Property[@name='{name}']/Float").get("value")) == value,
                    f"Native {variant}/{name} differs")
        for name in ("PistonRod1", "PistonRod2"):
            data = doc.find(f"./ObjectData/Object[@name='{name}']/Properties/Property[@name='Placement']/PropertyPlacement")
            require(data is not None and [float(data.get(k)) for k in ("Px", "Py", "Pz")] == [c["rear_reserve"], 0, 0],
                    f"Native +X motion missing: {variant}/{name}")
        names = {element.get("name") for element in doc.findall("./Objects/Object")}
        for entry in interfaces.values():
            if variant in entry.get("applies_to", model.native["variants"]):
                require(set(entry["objects"]) <= names, f"Native interface objects missing in {variant}")


def close(actual, expected, why, abs_tol=1e-6):
    require(isclose(actual, expected, rel_tol=1e-11, abs_tol=abs_tol), why)


def check_analytical_limits(model):
    # Independent closed forms at zero eccentricity, centre-point bending, and simply-supported end reactions.
    f, length, ei = 1e6, model.rail_length, 1e15
    for path, area in ((SEAT, (model.b["gate_width"] / 2 - model.b["seat_inner_y"]) * model.b["gate_height"]),
                       (KEYS, model.b["key_width"] * model.b["key_height"])):
        entry = model.receiver(path, f, 0, 0)
        close(entry["peak_MPa"], f / (2 * area), f"{path}: uniform contact pressure")
        for part in entry["parts_negative_positive_y"]:
            close(part["force_N"], f / 2, f"{path}: equal reactions in centric check")
    for fixed, divisor in ((False, 48), (True, 192)):
        close(deflection(f, length / 2, length / 2, length, ei, fixed), f * length**3 / (ei * divisor),
              "Middle deflection of rail")
        a = length * 0.27
        rear, front, ma, mb = beam_end(f, a, length, fixed)
        close(rear + front, f, "Rail force check")
        close(front * length + ma + mb, a * f, "Rail moment check")
    close(model.rod, pi * model.c["rod"]**2 / 4, "Rod area")


def check_row(model, row, pressure_bound=False):
    f = row["force_N"]
    if row["status"] == FREE:
        require(f and row["unbalanced_axial_force_N"] == f and row["sections_4_5_6"]["value"] is None,
                "Released axial path masked a residual")
        return
    ftol = model.comparison["balance_force_tolerance_N"]
    mtol = model.comparison["balance_moment_tolerance_Nmm"]
    for force, moment in (row["moving_balance"], row["frame_PIN_PIN"]["balance"], row["frame_FIXED_FIXED"]["balance"]):
        require(max(map(abs, force)) < ftol and max(map(abs, moment)) < mtol, "Force/moment residual")
        force[:] = [round(value, 6) for value in force]
        moment[:] = [round(value, 4) for value in moment]
    for mode in ("PIN_PIN", "FIXED_FIXED"):
        for head, demands in row[f"frame_{mode}"]["heads"].items():
            sign = 1 if head == "rear" else -1
            ties = [sign * value for value in demands["tie_axial_demands_N"]]
            close(sum(ties), -demands["force_xyz_N"][0], "Head/tie axial equilibrium")
            r = model.s["tie_axis_offset"]
            yz = tuple(product((-r, r), repeat=2))
            close(sum(z * n for (_, z), n in zip(yz, ties)), -demands["moment_xyz_Nmm"][1], "Head/tie My")
            close(sum(-y * n for (y, _), n in zip(yz, ties)), -demands["moment_xyz_Nmm"][2], "Head/tie Mz")
    guide_drag = 0
    for label, (point, force, pressure) in row["guide_pad_columns"].items():
        a = 1 if label[0] == "Y" else 2
        require(point[a] * force[a] <= 0 and pressure >= 0 and
                abs(force[0]) <= model.l["guide_sliding_friction_limit"] * abs(force[a]) + ftol,
                "Guide unilateral contact or sliding inequality")
        guide_drag += force[0]
    rods = row["branch_forces_N"]
    close(sum(rods) + guide_drag, f, "Carriage axial equilibrium")
    require(row["axial_reaction_on_frame_N"] == f, "Axial reaction sign")
    for rod_name in ("rod_1", "rod_2"):
        if rod_name in row["section_5_stability"]:
            pin, free = row["section_5_stability"][rod_name]
            close(pin["P_cr_N"], 4 * free["P_cr_N"], "Euler K scaling")
    receiver = row["section_6_receiver"]
    require(bool(receiver) == (row["path"] in (SEAT, KEYS) and f > 0), "Receiver path engagement")
    if receiver:
        parts = receiver["parts_negative_positive_y"]
        close(sum(part["force_N"] for part in parts), f, "Receiver axial equilibrium")
        for i, key in enumerate(("first_moment_y_Nmm", "first_moment_z_Nmm")):
            close(sum(part[key] for part in parts), f * row["eccentricity_yz_mm"][i],
                  "Receiver moment equilibrium", abs_tol=mtol)
        require(all(part["force_N"] > 0 and part["peak_MPa"] > 0 for part in parts), "Receiver compression-only")
    if pressure_bound:
        for rod, (cap, annulus) in zip(rods, row["ports_cap_annulus_bar"]):
            close(rod, (cap * model.cap - annulus * model.annulus) / 10, "Pressure-bound rod load")
    else:
        for rod, (port, supply) in zip(rods, row["pressure_port_and_supply_bar"]):
            if rod:
                active, back = (model.cap, model.annulus) if rod > 0 else (model.annulus, model.cap)
                close(abs(rod), port / 10 * active * (1 - model.l["cylinder_loss_fraction"])
                      - model.l["opposing_port_bar"] / 10 * back, "Hydraulic force reconstruction")
                close(supply - port, model.l["supply_drop_bar"], "Pressure drop")
            else:
                require(port is None and supply is None, "Idle pressure should be unknown")


def extrema_for(rows):
    return extrema(round_values(rows))


def svg(index):
    cases = list(index["cases"].values())
    w, h = 980, 330
    y = lambda pressure: 260 - pressure * 0.76
    content = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img">',
               '<title>Пиковое расчётное давление подачи по 42 состояниям</title>',
               '<rect width="980" height="330" fill="white"/>',
               '<g font-family="sans-serif" font-size="13" fill="#1e293b">',
               '<text x="22" y="25" font-size="18">W02 · Пиковое давление подачи по состояниям, бар</text>']
    for value in (0, 50, 100, 150, 200, 250, 315):
        color = "#ae3f2a" if value in (250, 315) else "#cbd5e1"
        content.extend((f'<path d="M56 {y(value):.2f} H960" stroke="{color}" stroke-width="1" opacity="0.8"/>',
                        f'<text x="22" y="{y(value) + 4:.2f}">{value}</text>'))
    for i, case in enumerate(cases):
        value = case["extrema"]["max_required_supply_bar_row_branch"][0]
        x = 62 + 21.2 * i
        content.append(f'<rect x="{x:.1f}" y="{y(value):.2f}" width="13" height="{260 - y(value):.2f}" fill="#2563a5">'
                       f'<title>S42-{i + 1:03}: {value:.2f} bar</title></rect>')
        if i == 0 or (i + 1) % 5 == 0 or i + 1 == len(cases):
            content.append(f'<text x="{x:.1f}" y="283">{i + 1:02}</text>')
    content.extend(('<text x="418" y="311">Идентификатор S42</text></g>', '</svg>'))
    return ("\n".join(content) + "\n").encode()


def receiver_svg(index, minimum):
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 715 233" role="img">',
        '<title>W02 · Запас по пиковому контактному давлению ветвей B</title>',
        '<rect width="715" height="233" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#1e293b">',
        '<text x="20" y="26" font-size="18">W02 · Запас по пиковому давлению ветвей B</text>',
    ]
    origin, scale = 154, 100
    for i, (path, title) in enumerate(((SEAT, "Седло"), (KEYS, "Ключи"))):
        es = index["receiver_extrema"][path]
        base = 82 + 62 * i
        elements.append(f'<text x="24" y="{base + 14}">{title}</text>')
        for j, (key, color) in enumerate((("normal", "#2563a5"), ("pressure_bound", "#ae3f2a"))):
            factor = es[key]["factor"]
            yy = base - 15 + 24 * j
            elements.extend((f'<rect x="{origin}" y="{yy}" width="{factor * scale:.2f}" height="17" fill="{color}"/>',
                             f'<text x="{origin + factor * scale + 7:.2f}" y="{yy + 13}">{factor:.3f}</text>'))
    x = origin + minimum * scale
    elements.extend((f'<path d="M{x:.2f} 57 V185" stroke="#334155" stroke-dasharray="4 3"/>',
                     f'<text x="{x + 5:.2f}" y="59">критерий {minimum:.1f}</text>',
                     '<rect x="25" y="204" width="13" height="13" fill="#2563a5"/>',
                     '<text x="45" y="215">Штатная огибающая</text>',
                     '<rect x="265" y="204" width="13" height="13" fill="#ae3f2a"/>',
                     '<text x="285" y="215">Предельные давления в полостях</text>', '</g></svg>'))
    return ("\n".join(elements) + "\n").encode()


def build_outputs(model):
    source = read(ENVELOPE)["cases"]
    catalog = read(CATALOG)["cases"]
    baseline = {item["case_id"] for item in catalog}
    require(len(source) == len(baseline) == 42 and set(source) == baseline, "42 catalog IDs do not match")
    check_analytical_limits(model)
    outputs = {}
    results = {case_id: list(case_samples(model, case)) for case_id, case in source.items()}
    index = {"task_id": TASK, "scope": ASSUMED, "physical_input_status": BLOCKED, "physical_case_count": 0,
             "physical_sections_4_5_6": "NOT_RUN", "case_count": len(results), "cases": {}}
    for case_id, case in source.items():
        rows = results[case_id]
        poses = case["pose_samples_q_m"]
        nonzero = [item for item in case["axial_samples"] if item["F_x_N"]]
        expected_held = sum(len(item["held_axial_paths"]) for item in nonzero) * len(poses) * len(model.offsets) * 2
        counts = Counter(row["mode"] for row in rows)
        require(counts["STATIC_HOLD"] == counts["SLIDING_LIMIT"] == expected_held // 2
                and counts["AXIAL_RELEASE"] == len(nonzero) * len(poses)
                and counts["ZERO_GRAVITY_ONLY"] == len(poses), f"Coverage mismatch: {case_id}")
        for row in rows:
            check_row(model, row)
            require(row["path"] not in (SEAT, KEYS)
                    or row["stroke_mm"] <= model.r4["stroke"]["B_closed_work_limit_stroke_mm"] + 1e-8,
                    f"B closed stroke mismatch: {case_id}")
        filename = f"results/{case_id}.jsonl"
        index["cases"][case_id] = {
            "variant": case["variant"], "phase": case["phase"], "design_basis_status": ASSUMED,
            "physical_input_status": BLOCKED, "physical_result": {"value": None, "reason": read(PARAMS)["physical_values"]["reason"]},
            "interface_ids": case["r4_interface_ids"], "pose_samples_q_m": poses,
            "count_by_mode": dict(counts), "extrema": extrema_for(rows), "sample_file": filename,
        }
        outputs[f"{HERE}/{filename}"] = b"".join(encode(row, True) for row in rows)

    normal = [row for rows in results.values() for row in rows]
    bound = list(pressure_samples(model))
    for row in bound:
        check_row(model, row, pressure_bound=True)
    index["state_samples"] = dict(Counter(row["mode"] for row in normal))
    index["normal_extrema"] = extrema_for(normal)
    index["normal_extrema_row_reference"] = "Concatenated sample_file rows in case ID order, 1-based."
    index["pressure_bound_samples"] = len(bound)
    index["pressure_bound_extrema"] = extrema_for(bound)
    index["pressure_bound_samples_path"] = "results/pressure_bounds.jsonl"
    index["pressure_bound_recontact_by_end_BC"] = {
        mode: sum(row[f"rails_{mode}"]["chamber_clearance_remaining_mm"] <= 0 for row in bound)
        for mode in ("PIN_PIN", "FIXED_FIXED")
    }
    index["pressure_bound_below_strength_target"] = sum(
        any(metric["factor"] is not None and metric["factor"] < model.l["min_strength_factor"]
            for metric in row["section_4_strength"].values()) for row in bound)
    index["receiver_extrema"] = {}
    for path in (SEAT, KEYS):
        index["receiver_extrema"][path] = {}
        for label, rows in (("normal", normal), ("pressure_bound", bound)):
            peak, i = max((round_values(row["section_6_receiver"]["peak_MPa"]), i)
                          for i, row in enumerate(rows, 1) if row["path"] == path)
            index["receiver_extrema"][path][label] = {
                "row": i, "peak_MPa": peak, "factor": round_values(rows[i - 1]["section_6_receiver"]["factor"]),
            }
    index["single_branch_reverse"] = single_branch(model, source)
    index["stroke"] = model.r4["stroke"].copy()
    poses = [model.c["rear_reserve"] + q * 1000 for case in source.values() for q in case["pose_samples_q_m"]]
    outside = sum(not 0 <= stroke <= model.c["stroke"] for stroke in poses)
    require(len(poses) == index["stroke"]["source_pose_points"] and
            outside == index["stroke"]["points_outside_stroke"], "Stroke comparison with R4")
    min_strength = model.l["min_strength_factor"]
    max_euler = model.l["max_euler_utilization"]
    nominal = index["normal_extrema"]
    upper = index["pressure_bound_extrema"]
    criteria = {
        "all_42_IDs_with_balances_or_documented_exception": True,
        "source_stroke": not outside and model.c["stroke"] >= 700,
        "nominal_pressure_within_available_250_bar": nominal["max_required_supply_bar_row_branch"][0] <= model.l["supply_bar"][0],
        "nominal_critical_strength": nominal["min_strength_factor_row_component"][0] >= min_strength,
        "pressure_bound_critical_strength": upper["min_strength_factor_row_component"][0] >= min_strength,
        "euler_below_limit": max(metrics["max_compression_over_euler_row_component_K"][0]
                                 for metrics in (nominal, upper)) < max_euler,
        "nominal_guide_clearance": nominal["min_punch_chamber_gap_mm_row"][0] > 0,
        "pressure_bound_guide_clearance": upper["min_punch_chamber_gap_mm_row"][0] > 0,
        "single_branch_full_reverse_demand_within_port_limit": all(
            entry["status"] == "WITHIN_PORT_LIMIT" for entry in index["single_branch_reverse"].values()),
    }
    index["criteria"] = {key: "PASS" if value else "FAIL" for key, value in criteria.items()}
    index["engineering_status"] = "PASS" if all(criteria.values()) else "FAILED"
    if index["engineering_status"] == "FAILED":
        require((PACKAGE / "engineering_failure_note.md").is_file(), "Missing engineering failure note")
    outputs[f"{HERE}/results/index.json"] = encode(index)
    outputs[f"{HERE}/results/pressure_bounds.jsonl"] = b"".join(encode(row, True) for row in bound)
    outputs[f"{HERE}/results/phase_hydraulics.json"] = encode(drives(model, source, results))
    outputs[f"{HERE}/results/pressure_by_state.svg"] = svg(index)
    outputs[f"{HERE}/results/receiver_contact.svg"] = receiver_svg(index, min_strength)
    return index, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check-git", action="store_true")
    args = parser.parse_args()
    model = W02()
    check_inputs(model, args.check_git)
    index, outputs = build_outputs(model)
    package_files = [PARAMS, MANIFEST, *[f"{HERE}/{name}" for name in (
        "README.md", "input_audit.md", "force_calc.py", "contacts.py", "verify_output.py")]]
    if index["engineering_status"] == "FAILED":
        package_files.append(f"{HERE}/engineering_failure_note.md")
    manifest = {
        "task_id": TASK, "scope": ASSUMED, "engineering_status": index["engineering_status"],
        "sha256": {path: digest(data) for path, data in outputs.items()} |
                  {path: digest((ROOT / path).read_bytes()) for path in package_files},
        "command": f"python {HERE}/verify_output.py --check-git",
    }
    outputs[f"{HERE}/output_manifest.json"] = encode(manifest)
    for name, expected in outputs.items():
        path = ROOT / name
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
        require(path.read_bytes() == expected, f"Saved result differs from replay: {name}")
    require({path.relative_to(ROOT).as_posix() for path in (PACKAGE / "results").iterdir()} ==
            {path for path in outputs if "/results/" in path}, "Unexpected file(s) in results")
    if args.check_git:
        for path in [*outputs, *package_files]:
            require(git("", path) == (ROOT / path).read_bytes(), f"Working file differs from Git index: {path}")
    print(f"PASS: {index['case_count']} IDs, {sum(index['state_samples'].values())} source combinations, "
          f"{index['pressure_bound_samples']} pressure-bound combinations, {index['engineering_status']} engineering verdict")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
