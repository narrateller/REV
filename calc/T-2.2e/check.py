"""Verify gates, package limits, UTF-8 and replay the round-two outputs."""
import ast
import hashlib
import math
import subprocess
import sys

import yaml

from run import DESIGN, FEA, HERE, PARAMS, ROOT, read_json, write_json

HASH_ROUND1_PARAMS = "6fed606a0fb964ac6352708b29a464e024316127ad9fe78db24003f18efa74a7"
ACCEPTED_GATES = ("G-PFACE", "G-DOSE", "G-CYCLE")
TOLERANCE = 1e-6


def compare(first, second):
    if isinstance(first, bool):
        assert first is second
    elif isinstance(first, (int, float)):
        assert isinstance(second, (int, float)) and not isinstance(second, bool)
        assert math.isfinite(first) and math.isfinite(second)
        return abs(first - second)
    elif isinstance(first, dict):
        assert first.keys() == second.keys()
        return max((compare(first[key], second[key]) for key in first), default=0.)
    elif isinstance(first, list):
        assert len(first) == len(second)
        return max((compare(a, b) for a, b in zip(first, second)), default=0.)
    else:
        assert first == second, (first, second)
    return 0.


def replay(final, replay, identity):
    if not replay.is_file():
        return {"status": "NOT_REPLAYED"}
    source = {identity(row): row for row in read_json(final) if row["status"] == "SOLVED"}
    current = read_json(replay)
    errors = [compare(source[identity(row)], row)
              for row in current if row["status"] == "SOLVED" and identity(row) in source]
    largest = max(errors, default=None)
    return dict(status="PASS" if largest is not None and largest <= TOLERANCE else "FAIL",
                rows_compared=len(errors), full_series=len(errors) == len(source),
                maximum_absolute_difference=largest, permitted_absolute_difference=TOLERANCE)


def run():
    generated = [HERE / "results.json", DESIGN, PARAMS, ROOT / "metrics.json", ROOT / "gates.t22e.json"]
    hashes = []
    for _ in range(2):
        subprocess.run([sys.executable, "-B", str(HERE / "run.py")], cwd=ROOT, check=True)
        hashes.append({str(path.relative_to(ROOT)).replace("\\", "/"):
                       hashlib.sha256(path.read_bytes()).hexdigest() for path in generated})
    assert hashes[0] == hashes[1]
    assert hashlib.sha256(PARAMS.read_bytes()).hexdigest() == HASH_ROUND1_PARAMS
    report = (ROOT / "report.md").read_bytes().decode("utf-8", "strict")
    assert "????" not in report and "\ufffd" not in report and "Δh" in report and "стоп" in report.lower()
    for path in HERE.rglob("*.py"):
        ast.parse(path.read_bytes(), filename=str(path))
    for path in (*HERE.rglob("*.yaml"), DESIGN, PARAMS):
        yaml.safe_load(path.read_text(encoding="utf-8"))
    for path in (*HERE.rglob("*.json"), *generated[3:]):
        read_json(path)
    gate_report = read_json(ROOT / "gates.t22e.json")
    actual = {row["id"]: row for row in gate_report["gates"]}
    assert all(actual[gate]["status"] == "PASS" for gate in ACCEPTED_GATES)
    working = read_json(ROOT / "metrics.json")
    g = working["global_FEA"]
    c = working["local_FEA"]
    checked = g.get("manual_comparison_315_bar")
    section_pass = bool(checked) and all(max(v["moment_error_fraction"], v["shear_error_fraction"]) <= .15
                                         for v in checked.values())
    global_replay = replay(FEA / "r2_global_final.json", FEA / "r2_global_replay.json", lambda row: row["mesh_mm"])
    local_replay = replay(FEA / "r2_contact_final.json", FEA / "r2_contact_replay.json",
                          lambda row: (row["station"], row["mesh_mm"]))
    package = [path for path in HERE.rglob("*") if path.is_file()]
    package_bytes = sum(path.stat().st_size for path in package)
    mesh_suffixes = {".inp", ".msh", ".frd", ".geo", ".dat", ".sta", ".cvg"}
    large = [str(p) for p in package if p.suffix.lower() in mesh_suffixes and p.stat().st_size > 1_000_000]
    temp = [str(p.relative_to(HERE)) for p in HERE.rglob("*") if p.is_dir() and
            p.name.startswith(("r2_boxes_", "r2_contact_", "__pycache__", "global_scratch_", "local_scratch_"))]
    assert package_bytes <= 5_000_000 and not large and not temp
    tracked = subprocess.run(["git", "diff", "HEAD", "--name-only", "--"], check=True, cwd=ROOT,
                             capture_output=True, text=True).stdout.splitlines()
    assert all(any(p == name or name.endswith("/") and p.startswith(name) for name in
                   ("calc/T-2.2e/", "design/prepress_lock.t22e.yaml", "design/params.t22e.yaml",
                    "gates.t22e.json", "metrics.json", "report.md", "self_check.json"))
               for p in tracked), tracked
    limit_delta = g["max_delta_height_300_mm"] <= .6
    global_convergence = dict(
        height=g["max_delta_height_spread_fraction"] is not None and g["max_delta_height_spread_fraction"] < .05,
        proof_stress=g["governing_proof_stress_spread_fraction"] is not None and
                     g["governing_proof_stress_spread_fraction"] < .05,
        working_range=g["governing_FKM_stress_spread_fraction"] is not None and
                      g["governing_FKM_stress_spread_fraction"] < .05,
        proof_stress_mesh_envelope=g["proof_stress_mesh_envelope_spread_fraction"] is not None and
                                   g["proof_stress_mesh_envelope_spread_fraction"] < .05,
        working_stress_mesh_envelope=g["working_stress_mesh_envelope_spread_fraction"] is not None and
                                     g["working_stress_mesh_envelope_spread_fraction"] < .05,
    )
    local_convergence, local_pressure_screen = {}, {}
    for station, row in c.items():
        spreads = row.get("spreads_fraction", {})
        local_convergence[station] = ("PASS" if spreads and all(v is not None and v < .05 for v in spreads.values())
                                      else "FAIL" if row["meshes_complete"] == 3 else "INCOMPLETE")
        if not row.get("proof_gauges"):
            local_pressure_screen[station] = "INCOMPLETE"
            continue
        gauges = row["proof_gauges_by_mesh"]
        tooth_values = [item[key] for item in gauges for key in ("tooth_point_MPa", "highest_tooth_band_mean_MPa")]
        heel_values = [item[key] for item in gauges for key in ("heel_point_MPa", "heel_band_mean_MPa")]
        if any(value is None for value in tooth_values + heel_values):
            local_pressure_screen[station] = "INCOMPLETE"
        elif max(tooth_values) > 420 or max(heel_values) > 390:
            local_pressure_screen[station] = "ABOVE_SCREEN_AT_TRIAL_LOAD"
        elif local_convergence[station] == "PASS" and row["maximum_target_mismatch_300_315_fraction"] <= .001:
            local_pressure_screen[station] = "PASS_AT_CONTROLLED_GAUGES"
        else:
            local_pressure_screen[station] = "UNQUALIFIED_BELOW_SCREEN_AT_TRIAL_LOAD"
    chosen = read_json(FEA / "r2_global_final.json")[-1]
    gate_clearance = chosen["stations"]["front"]["gate_swept_clearance_mm"]
    write_json(ROOT / "self_check.json", dict(
        task="T-2.2e", round=2, qualification_status=working["status"], used_r2_filename_fallback=False,
        tools=dict(python=sys.version.split()[0], gmsh="4.15.0", CalculiX="2.22"),
        official_gates=dict(command="REV_PYTHON -B ops/gates/calc_gates.py --params design/params.t22e.yaml "
                           "--criteria ops/criteria/design_criteria.yaml --out gates.t22e.json",
                           criteria_version=gate_report["criteria_version"],
                           criteria_sha256=gate_report["criteria_sha256"],
                           results={g: {k: actual[g][k] for k in ("status", "value", "unit") if k in actual[g]}
                                    for g in ACCEPTED_GATES}),
        tests=dict(report_strict_utf8_no_corruption="PASS", JSON_YAML_Python_parsing="PASS",
                   protected_tracked_paths="PASS", original_gate_parameter_hash="PASS",
                   C_STR_01_at_evaluated_global_points=(g["global_box_static_factor_at_points"] >= 1.5),
                   C_FAT_01_at_evaluated_global_points=(g["global_box_FKM_at_points"] >= 1.),
                   global_mesh_convergence=global_convergence,
                   vertical_global_equilibrium=(g["maximum_reaction_imbalance_fraction"] <= .001
                                                and g["maximum_moment_imbalance_fraction"] <= .001
                                                and g["maximum_anchor_resultant_over_shoe_force_fraction"] <= .001),
                   three_manual_section_checks_within_15_pct=section_pass,
                   solver_pressure_steps=(g["solver_pressure_steps_bar"] == [0, 100, 200, 300, 315]),
                   nominal_front_support_gate_clearance=(gate_clearance >= 3. - 1e-10),
                   accepted_cycle_limits=(working["G_CYCLE_s"] <= 5.95 and working["reference_cycle_s"] <= 5.90),
                   delta_height_at_design_skew=limit_delta, contact_convergence=local_convergence,
                   contact_pressure_screen=local_pressure_screen,
                   local_force_balance={label: (row.get("maximum_balance_fraction", 1.) <= .001)
                                        for label, row in c.items()},
                   local_operating_and_proof_loads={label: (row.get("maximum_target_mismatch_300_315_fraction", 1.) <= .001)
                                                    for label, row in c.items()},
                   contact_pair_life="BENCH_VALIDATION_OPEN", overall_qualification="STOP"),
        same_outputs_twice=dict(status="PASS_BYTES_IDENTICAL", command="REV_PYTHON -B calc/T-2.2e/run.py",
                                sha256=hashes[0]),
        FEA_replay=dict(global_model=global_replay, contact=local_replay),
        workspace=dict(required_files_readable="PASS", package_bytes=package_bytes,
                       temporary_folders_removed=not temp, retained_large_meshes=len(large)),
    ))
    print("Checked gates, UTF-8, package scope and repeatability", global_replay, local_replay)


if __name__ == "__main__":
    run()

