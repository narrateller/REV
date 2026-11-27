"""Verify mandatory gates and repeat T-2.2i calculations on Python 3.13."""

from hashlib import sha256
import json
from math import isclose
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

sys.dont_write_bytecode = True

from run import HERE, ROOT, write_json


def call(*args, exit_code=0):
    completed = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT,
                               env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"},
                               capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != exit_code:
        raise RuntimeError(f"{args}: {completed.returncode}\n{completed.stdout}\n{completed.stderr}")
    return completed.returncode


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def gate_run():
    command = ("ops/gates/calc_gates.py", "--params", "calc/T-2.6/params/params.t26a.yaml",
               "--criteria", "ops/criteria/design_criteria.yaml", "--out")
    detailed = ROOT / "gates.t22i.json"
    all_exit = call(*command, detailed, exit_code=1)
    rows = {r["id"]: r for r in load(detailed)["gates"]}
    assert rows["G-PFACE"]["status"] == rows["G-DOSE"]["status"] == "PASS"
    assert rows["G-CYCLE"]["status"] == "FAIL"
    assert isclose(rows["G-PFACE"]["value"], 168.88888888888889, abs_tol=1e-10)
    assert rows["G-DOSE"]["value"] == 396
    with TemporaryDirectory(dir=HERE, prefix="verify-") as name:
        required_exit = call(*command, Path(name) / "required.json", "--gates", "G-PFACE,G-DOSE")
    return {"all_gates_exit_code": all_exit, "required_only_exit_code": required_exit,
            "statuses": {k: r["status"] for k, r in rows.items()},
            "G-CYCLE_blocks_structure_task": False}


def engineering_checks(data):
    loads = data["loads"]
    assert tuple(loads["K_values"]) == (.35, .45, .60)
    assert tuple(loads["mu_values"]) == (.20, .25, .30)
    assert loads["dose_interlock_kg"] == .853
    assert loads["final_loaded_length_max_mm"] == 89.4
    assert isclose(loads["shoe_envelope"]["shoe_315_bar_N"], 170971.600719046, abs_tol=1e-6)
    assert isclose(loads["shoe_envelope"]["transfer_axial_force_N"], 35251.41004986859,
                   abs_tol=1e-6)
    assert loads["independent_vertical_prepress_315_N"] == 171000.
    max_janssen_balance_N = max(abs(r["axial_balance_error_N"])
                                for step in loads["final_envelope"].values() for r in step)
    assert max_janssen_balance_N < 1e-6

    variants = data["variants"]
    for row in variants.values():
        assert row["max_force_balance_error_N"] < 1e-6
        assert row["max_moment_balance_error_Nmm"] < 1e-6
        reactions = row["reaction_extents"]
        assert reactions["front_minus"]["min_315_N"] > 0.
        assert isclose(reactions["front_minus"]["max_315_N"], reactions["front_plus"]["max_315_N"])
    for name in ("key_x192", "clevis_x182"):
        assert variants[name]["reaction_extents"]["rear_minus"]["min_315_N"] < 0.
    assert variants["nose_x225"]["reaction_extents"]["rear_minus"]["min_315_N"] > 0.
    assert variants["key_x192"]["interfaces"]["roof_clearance_x_mm"] < 0.
    assert data["ring"]["axial_stops"]["mean_300_MPa"] < 80.
    for profile in data["ring"]["width_trials"]:
        assert profile["kern_e_max_mm"] >= loads["roof_skew_y_mm"]
        assert profile["analyses"]["final_slotted"]["FKM_corrected"] < 1.15
    best = data["shortened_nose_sweep"]["best_stem_load"]["drive"]
    assert best["front_and_rear_stem_force_N_by_assumed_mu"]["0.15"] > best["stem_force_limit_N"]
    assert data["selected_variant"] is None and data["status"] == "STOP_HAND_SCREEN"

    old = data["T-2.2h_replay"]["moments_and_resultants"]["rows"]
    assert len(old) == 3
    assert max(r["force_error_fraction"] for r in old) < .15
    assert max(r["moment_error_over_governing_fraction"] for r in old) < .15
    volume = data["mass_volume_diagnostic"]
    assert abs(volume[-1]["front_removed_kg"] / volume[0]["front_removed_kg"] - 1.) < .01
    return {"Janssen_force_balance_max_N": max_janssen_balance_N,
            "hand_checks": ["inherited load envelope", "vertical reaction and moment balances",
                            "both directions of skew", "unilateral bearing sign and kern",
                            "axial support area", "lock budget", "archive section comparison",
                            "two-level body volume check", "stop conditions"]}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    assert sys.version_info[:2] == (3, 13)
    gate_status = gate_run()
    paths = [HERE / "results.json", ROOT / "design/chamber_roof.t22i.yaml",
             ROOT / "metrics.json", ROOT / "report.md", HERE / "fea/volume.json"]
    hashes = []
    for _ in range(2):
        call(HERE / "fea/volume.py")
        call(HERE / "run.py")
        hashes.append({p.relative_to(ROOT).as_posix(): digest(p) for p in paths})
    assert hashes[0] == hashes[1]
    report = (ROOT / "report.md").read_text(encoding="utf-8")
    assert "?" not in report and "\ufffd" not in report
    assert sum("\u0400" <= char <= "\u04ff" for char in report) >= 500
    data = load(HERE / "results.json")
    engineering = engineering_checks(data)
    work_files = [p for p in HERE.rglob("*") if p.is_file()]
    package_size_bytes = sum(p.stat().st_size for p in work_files)
    assert package_size_bytes <= 5_000_000
    forbidden_suffixes = {".msh", ".geo", ".inp", ".frd", ".dat", ".sta", ".cvg", ".pyc"}
    assert not any(p.suffix in forbidden_suffixes for p in work_files)
    assert not any(p.name.startswith(("vol-", "verify-", "__pycache__")) for p in HERE.rglob("*"))
    write_json(ROOT / "self_check.json", {
        "status": "checks_run_stop_hand_screen", "qualified": False, "python": sys.version.split()[0],
        "gates": gate_status, "engineering": engineering,
        "double_run": {"identical_bytes": True, "sha256": hashes[0]},
        "fea": {"volume_mesh_run": True, "structural_contact_run": False,
                "structural_convergence": "NOT_RUN_HAND_STOP", "numeric_comparison_tolerance": 1e-6},
        "report_utf8_without_question_marks": True, "package_size_bytes": package_size_bytes,
        "temporary_solver_files_removed": True,
    })


if __name__ == "__main__":
    main()

