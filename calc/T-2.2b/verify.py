"""Verify evidence, reproduction of both load splits, and delivery scope."""
import argparse
import ast
from hashlib import sha256
import subprocess
import sys

import yaml

from hand import HERE, ROOT, json_read, json_write
from assemble import check_inputs

PRODUCTS = (HERE/"results.json", ROOT/"design/chamber_lateral.t22b.yaml", ROOT/"metrics.json", ROOT/"report.md")
FEA = HERE/"fea"
TOLERANCE = 1e-6
EXPECTED_CASES = {f"portal_{level}_{share}" for level in range(3) for share in (60,64)}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def numeric_difference(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        assert a.keys() == b.keys()
        return max((numeric_difference(value, b[key]) for key,value in a.items()), default=0.)
    if isinstance(a, list) and isinstance(b, list):
        assert len(a)==len(b)
        return max((numeric_difference(x,y) for x,y in zip(a,b)), default=0.)
    if type(a) in (int,float) and type(b) in (int,float):
        return abs(a-b)/max(1.,abs(a),abs(b))
    assert a == b, (a,b)
    return 0.


def replay_fea():
    paths = sorted(FEA.glob("portal_[012]_[06][04].json"))
    assert {path.stem for path in paths}==EXPECTED_CASES
    before = {p.stem: (digest(p),json_read(p)) for p in paths}
    command = [sys.executable,"-B",str(FEA/"solve.py"),"0","1","2","--linear-kinematics"]
    subprocess.run(command,cwd=ROOT,check=True)
    repeated = {}
    for path in paths:
        before_hash, first = before[path.stem]
        difference = numeric_difference(first,json_read(path))
        repeated[path.stem] = dict(byte_identical=digest(path)==before_hash, sha256=digest(path),
                                   max_scaled_numeric_difference=difference)
    maximum = max(value["max_scaled_numeric_difference"] for value in repeated.values())
    json_write(FEA/"replay.json",dict(status=("PASS" if maximum<=TOLERANCE else "FAIL"),
        tolerance=TOLERANCE,numeric_metric="max |a-b| / max(1, |a|, |b|)",
        scope="Both load splits on all three mesh levels, including 0, 300 and 315 bar",
        max_scaled_numeric_difference=maximum,repeated=repeated))


def verify():
    check_inputs()
    for path in [*HERE.glob("*.py"),*FEA.glob("*.py")]:
        ast.parse(path.read_text(encoding="utf-8-sig"),filename=str(path))
    for path in (HERE/"sources.yaml",ROOT/"design/chamber_lateral.t22b.yaml"):
        yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    hashes=[]
    for _ in range(2):
        for name in ("assemble.py","render_report.py"):
            subprocess.run([sys.executable,"-B",str(HERE/name)],cwd=ROOT,check=True)
        hashes.append({path.relative_to(ROOT).as_posix():digest(path) for path in PRODUCTS})
    assert hashes[0]==hashes[1]
    gates=json_read(ROOT/"gates.t22b.json")
    assert {row["id"] for row in gates["gates"]}=={"G-PFACE","G-DOSE","G-CYCLE"}
    assert all(row["status"]=="PASS" for row in gates["gates"])
    result = json_read(HERE/"results.json")
    solved = result["fea"]["cases"]
    assert set(solved)==EXPECTED_CASES
    assert all("paired_section_300_bar" in row for row in solved.values())
    assert all(max(row["global_force_balance_fraction"],row["shoe_force_balance_fraction"])<=.001
               for row in solved.values())
    assert all(row["stabilizer_load_fraction"]<.001 for row in solved.values())
    assert all(row["stabilizer_stored_energy_fraction"]<.01 for row in solved.values())
    assert result["status"] == "HOLD"
    geom = result["kinematic_screen"]
    assert geom["lock_stroke_mm"]==36 and geom["cam_stroke_mm"]==12
    assert geom["product_section_mm"]==[150,60] and geom["prepress_cylinder_bore_rod_mm"]==[125,56]
    assert geom["lock_post_worst_case_mm"]>=.5
    required = (*PRODUCTS,ROOT/"gates.t22b.json",HERE/"sources.yaml",
                HERE/"hand.py",HERE/"mass.py",FEA/"portal.geo",FEA/"mesh_check.json")
    mesh = json_read(FEA/"mesh_check.json")
    assert mesh["max_mesh_mm"]==21. and mesh["nodes"]==solved["portal_2_64"]["nodes"]
    assert all(part["min_corner_jacobian_mm3"]>0 for part in mesh["solids"].values())
    assert not any(path.is_dir() and path.name.startswith(("work_","portal_run_","component_run_","__pycache__"))
                   for path in HERE.rglob("*"))
    assert all(path.is_file() for path in required)
    files = sorted(p for p in HERE.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in files)
    assert size<=5_000_000, size
    assert not any(p.suffix.lower() in {".msh",".frd",".dat",".12d",".cvg",".sta",".log",".pyc"} for p in files)
    assert not any(p.stat().st_size>1_000_000 for p in files if p.suffix.lower()==".inp")
    for path in (*files,*required):
        with path.open("rb") as file:
            file.read(1)
    replay = json_read(FEA/"replay.json")
    assert replay["status"]=="PASS" and set(replay["repeated"])==EXPECTED_CASES
    assert all(row["sha256"]==digest(FEA/f"{case}.json") for case,row in replay["repeated"].items())
    recorded = dict(
        design_approval=result["status"],
        hand_and_design_reproduction=dict(status="PASS",byte_identical=True,sha256=hashes[0]),
        gate_command=("E:/Tools/Python313/python.exe -B ops/gates/calc_gates.py --params design/params.t21.yaml "
                      "--criteria ops/criteria/design_criteria.yaml --out gates.t22b.json"),
        gates={row["id"]:dict(status=row["status"],value=row["value"],unit=row["unit"]) for row in gates["gates"]},
        contact_FEA=dict(
            pressure_endpoints_bar=[0,100,200,300,315],
            finest_mesh_geometry_and_load_check=mesh["status"],
            solved_meshes_by_share={k:r["solved_levels"] for k,r in result["fea"]["convergence"].items()},
            convergence_by_share={k:dict(status=r["status"],max_relative_change=r["max_relative_change"])
                                  for k,r in result["fea"]["convergence"].items()},
            qualification=result["qualification"],
            global_force_balance_by_case={k:r["global_force_balance_fraction"] for k,r in solved.items()},
            shoe_force_balance_by_case={k:r["shoe_force_balance_fraction"] for k,r in solved.items()},
            artificial_force_fractions={k:r["stabilizer_load_fraction"] for k,r in solved.items()},
            artificial_energy_fractions={k:r["stabilizer_stored_energy_fraction"] for k,r in solved.items()},
            penalty_sensitivity_status=("SOLVED" if result["fea"]["penalty_sensitivity"] else "OPEN")),
        FEA_repeat_at_1e_6=replay,
        kinematics=dict(status="PASS_SCALAR_TOLERANCE_SCREEN",worst_case_lock_to_post_mm=geom["lock_post_worst_case_mm"],
                        integrated_layout_status="OPEN"),
        delivery=dict(status="PASS",calculation_tree_bytes=size,file_count=len(files),
                      reference_copies="byte-identical",all_files_readable=True,temporary_files_present=False))
    json_write(ROOT/"self_check.json",recorded)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--replay-fea",action="store_true")
    parser.add_argument("--only-replay",action="store_true")
    args=parser.parse_args()
    if args.replay_fea or args.only_replay:
        replay_fea()
    if not args.only_replay:
        verify()
