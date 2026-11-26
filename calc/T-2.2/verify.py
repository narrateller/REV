"""Check round-2 deliverables and replay, with cap stresses compared numerically."""
import argparse
from hashlib import sha256
import json
import math
import subprocess
import sys

sys.dont_write_bytecode = True

import yaml

from run import (
    BALANCE_LIMIT, COVER_STEM, HERE, LEVELS, OUTPUT, ROOT, dump_json,
    gci, read_json, run_solver,
)


REPRO_FEATOL = 1e-6
OUTPUT_FILES = ("calc/T-2.2/results.json", "design/main_cylinder_rear.t22.yaml",
                "design/chamber_lateral.t22.yaml", "metrics.json")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def files_below(folder):
    return sorted(path for path in folder.rglob("*") if path.is_file())


def close(left,right,tolerance):
    if type(left) is not type(right):
        return False
    if isinstance(left,dict):
        return left.keys()==right.keys() and all(close(value,right[key],tolerance) for key,value in left.items())
    if isinstance(left,list):
        return len(left)==len(right) and all(close(a,b,tolerance) for a,b in zip(left,right))
    if isinstance(left,float):
        return math.isclose(left,right,rel_tol=tolerance,abs_tol=tolerance)
    return left==right


def pipeline(allow_partial):
    args = ["--allow-partial"] if allow_partial else []
    subprocess.run([sys.executable,"-B",str(HERE/"run.py"),*args],cwd=ROOT,check=True)


def snapshot():
    contents = {path:(OUTPUT/path).read_bytes() for path in OUTPUT_FILES}
    fea = {level:read_json(path) for level in LEVELS
           if (path:=HERE/f"cap_fea/{COVER_STEM}_{level}.json").exists()}
    return contents,fea


def replay(allowed_levels):
    if allowed_levels:
        run_solver(allowed_levels)


def verify(allow_partial, replay_levels):
    if replay_levels and not allow_partial and tuple(replay_levels)!=LEVELS:
        raise ValueError("Full replay requires all four meshes.")
    baseline_chamber = ROOT/"calc/T-2.2/lateral_fea"
    chamber_before = {p.name:digest(p) for p in files_below(baseline_chamber)}
    guard_paths = ["DECISIONS.md","TASK.md","ops/criteria/design_criteria.yaml","ops/gates/calc_gates.py",
                   "design/cylinders.t16.yaml","design/cylinders.t17d.yaml","design/frame.t17d.yaml",
                   "design/params.t21.yaml"]
    guards_before = {path:digest(ROOT/path) for path in guard_paths}

    pipeline(allow_partial)
    first,first_fea = snapshot()
    if replay_levels:
        replay(replay_levels)
    pipeline(allow_partial)
    second,second_fea = snapshot()
    equal_files = {path:first[path]==second[path] for path in first}
    fea_checks = {level:close(first_fea[level],second_fea[level],REPRO_FEATOL)
                  for level in replay_levels}
    checked = read_json(HERE/"results.json")
    chamber = yaml.safe_load((OUTPUT/"design/chamber_lateral.t22.yaml").read_bytes())
    rear = yaml.safe_load((OUTPUT/"design/main_cylinder_rear.t22.yaml").read_bytes())
    source = yaml.safe_load((HERE/"sources.yaml").read_bytes())
    assert chamber["status"]=="HOLD_G_FEA" and chamber["transferred_to"]=="T-2.2b (D-GK-07)"
    assert rear["status"]=="HOLD" and rear["cover"]["selected_execution"]=="recessed_taps"
    assert [d["seal_diameter_mm"] for d in checked["zsf"]["pressure_diameter_cases"]]==[138.5,188.]
    assert source["round_2"]["RE_20478"]["pages"]
    assert all(row["status"]=="PASS" for row in checked["gates"].values())
    masses = checked["mass"]
    assert masses["limit_pass"]
    assert math.isclose(masses["nominal_AB_kg"], masses["baseline_T21_kg"]+
                        masses["A"]["delta_A_kg"]+masses["B"]["delta_B_kg"], abs_tol=1e-9)
    assert math.isclose(masses["limit_kg"], masses["nominal_AB_kg"]+masses["nominal_reserve_for_T22b_kg"],
                        abs_tol=1e-9)
    zsf = checked["zsf"]
    assert math.isclose(zsf["tool"]["fastener_chord_mm"], 240*math.sin(math.pi/8))
    assert zsf["tool"]["stud_above_bearing_seat_mm"]>=zsf["tool"]["tool_min_stud_above_bearing_seat_mm"]
    assert all(.3<=row["mean_force_ratio_min"]<=row["mean_force_ratio_max"]<1.
               for diameter in zsf["pressure_diameter_cases"] for row in diameter["rows"])
    gci_parabola = gci(26.,14.,11.,[4.,2.,1.])
    assert math.isclose(gci_parabola["observed_order"],2.,abs_tol=1e-10)
    assert math.isclose(gci_parabola["GCI21_fraction"],1.25/11,abs_tol=1e-10)
    assert checked["cover"]["max_force_balance_residual_fraction"]<=BALANCE_LIMIT
    assert all(equal_files.values()) or (all(fea_checks.values()) and bool(replay_levels) and
           close(json.loads(first[OUTPUT_FILES[0]]),checked,REPRO_FEATOL) and
           close(yaml.safe_load(first[OUTPUT_FILES[1]]),rear,REPRO_FEATOL) and equal_files[OUTPUT_FILES[2]])
    assert all(fea_checks.values())

    scratch = sorted(path.name for path in HERE.glob("t22_cap_*"))
    calc_files = [path for path in files_below(HERE) if not set(scratch).intersection(path.parts)]
    written = calc_files + [OUTPUT/path for path in (*OUTPUT_FILES[1:],"report.md","gates.t22.json")]
    chamber_unchanged = chamber_before == {p.name:digest(p) for p in files_below(baseline_chamber)}
    other_unchanged = guards_before == {path:digest(ROOT/path) for path in guard_paths}
    existing_calc = ROOT/"calc/T-2.2"
    project_files = {path.relative_to(existing_calc):path for path in files_below(existing_calc)}
    project_files.update({path.relative_to(HERE):path for path in calc_files})
    # Staging can retain private diagnostics from previous implementations.
    project_files = {name:path for name,path in project_files.items()
                     if not any(part.startswith("t22_cap_") for part in name.parts)
                     and not name.name.startswith("r2_ma8_")}
    assert chamber_unchanged and other_unchanged
    assert all(path.stat().st_size<=1_000_000 for path in [*written,*project_files.values()])
    calc_bytes = sum(path.stat().st_size for path in project_files.values())
    assert calc_bytes<=5_000_000
    out = dict(
        task="T-2.2", round=2,
        structural_status=checked["structural_status"], gate_status=checked["gates"],
        gate_command=["ops/gates/calc_gates.py","--params","design/params.t21.yaml","--criteria",
                      "ops/criteria/design_criteria.yaml","--out","gates.t22.json"],
        inputs_preserved=other_unchanged,lateral_archive_preserved=chamber_unchanged,
        analytic_checks=["mass balance","PCD chord","tool axial thread engagement","VDI SG validity","Roache GCI order"],
        chamber_recalculated=False, ordinary_runner_read_pass=all(len(path.read_bytes())>=0 for path in written),
        byte_equal_on_second_aggregation=equal_files,
        FEA_replay_levels=list(replay_levels), FEA_replay_pass_by_level=fea_checks,
        FEA_full_replay_completed=tuple(replay_levels)==LEVELS and all(fea_checks.values()),
        FEA_replay_absolute_and_relative_tolerance=REPRO_FEATOL,
        tools=dict(Python=sys.version.split()[0], Gmsh="4.15.0",CalculiX="2.22"),
        FEA_solved_levels=[row["mesh_level"] for row in checked["cover"]["levels"]],
        FEA_strength_criteria_pass=checked["cover"]["numerical_criteria_pass"],
        FEA_max_force_balance_residual_fraction=checked["cover"]["max_force_balance_residual_fraction"],
        calc_and_archive_bytes=calc_bytes,
        scratch_dirs_remaining=scratch,
        staging_output_used=ROOT!=OUTPUT,
    )
    dump_json(OUTPUT/"self_check.json",out)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay",action="store_true",help="Perform a second full Gmsh/CalculiX run.")
    parser.add_argument("--replay-level",action="append",choices=LEVELS,type=int,default=[])
    parser.add_argument("--allow-partial",action="store_true",help="Record a partial HOLD or partial independent replay.")
    flags = parser.parse_args()
    levels = LEVELS if flags.replay else flags.replay_level
    result = verify(flags.allow_partial,levels)
    print("Aggregation replay and scope checks passed.")
    print(f"Independent FEA levels replayed: {result['FEA_replay_levels']}")


if __name__=="__main__":
    main()
