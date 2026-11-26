"""Replay round-2 FEA and check provenance, numerical results and submitted inputs."""
import argparse
from hashlib import sha256
import json
from math import isclose
import subprocess
import sys
import tempfile

import yaml

from frame_analytic import (
    CORNERS, DISCHARGE_BAY_mm, ECC_mm, HERE, PAD_HEIGHT_mm, RAIL_WIDTH_mm, RHO_kg_mm3,
    ROOT, STATIC_N, chamber_bearing, corner_forces_N,
)
from frame_fea import FEA, write_json

TOL = 1e-6
OUTPUTS = (HERE/"results.json", ROOT/"design/frame.t17.yaml", ROOT/"metrics.json")


def hashes(paths):
    return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in paths}


def compare_values(a,b,path,errors):
    if type(a) is not type(b):
        errors.append(path)
    elif isinstance(a,dict):
        if a.keys()!=b.keys():
            errors.append(path+" keys")
        for key in sorted(a.keys() & b.keys()):
            compare_values(a[key],b[key],path+"."+key,errors)
    elif isinstance(a,list):
        if len(a)!=len(b):
            errors.append(path+" length")
        for i,(x,y) in enumerate(zip(a,b,strict=False)):
            compare_values(x,y,f"{path}[{i}]",errors)
    elif isinstance(a,float):
        if not isclose(a,b,rel_tol=0.,abs_tol=TOL):
            errors.append(path)
    elif a!=b:
        errors.append(path)


def load_result(path):
    return json.loads(path.read_bytes()) if path.suffix==".json" else yaml.safe_load(path.read_bytes())


def call(script,*args):
    subprocess.run([sys.executable,"-B",str(script),*args],cwd=ROOT,check=True)


def main(replay):
    gate_args = ("--params","design/params.t14b.yaml","--criteria","ops/criteria/design_criteria.yaml",
                 "--out","gates.t17.json")
    call(ROOT/"ops/gates/calc_gates.py",*gate_args)
    call(HERE/"summarize.py")
    original_data = [load_result(p) for p in OUTPUTS]
    original_hashes = hashes(OUTPUTS)
    original_fea = hashes(sorted(FEA.glob("*.json")))
    results = original_data[0]
    commands = []
    if replay:
        for name,variant in results["variants"].items():
            for end,case in variant["fea"].items():
                levels = ",".join(str(level["level"]) for level in case["mesh_history"])
                args = ("--variant",name,"--end",end,"--levels",levels,"--archive-level","-1")
                call(HERE/"frame_fea.py",*args)
                commands.append("frame_fea.py "+" ".join(args))
        shoulder_levels = ",".join(str(row["level"]) for row in results["column_shoulder_FEA"]["levels"])
        args = ("--levels",shoulder_levels,"--archive-level","-1")
        call(HERE/"column_fea.py",*args)
        commands.append("column_fea.py "+" ".join(args))
        insert_levels = ",".join(str(row["level"]) for row in results["insert_FEA"]["mesh_history"])
        args = ("--levels",insert_levels,"--archive-level","-1")
        call(HERE/"insert_fea.py",*args)
        commands.append("insert_fea.py "+" ".join(args))
        call(HERE/"frame_fea.py","--benchmark")
        commands.append("frame_fea.py --benchmark")
    with tempfile.TemporaryDirectory(prefix="verify_",dir=HERE) as scratch:
        from pathlib import Path

        temp = Path(scratch)
        call(HERE/"summarize.py","--output-dir",scratch)
        generated = [temp/name for name in ("results.json","frame.t17.yaml","metrics.json")]
        replay_byte_identical = all(a.read_bytes()==b.read_bytes() for a,b in zip(OUTPUTS,generated,strict=True))
        repeated_hashes = {original.relative_to(ROOT).as_posix():sha256(new.read_bytes()).hexdigest()
                           for original,new in zip(OUTPUTS,generated,strict=True)}
        errors = []
        for old,new in zip(original_data,generated,strict=True):
            compare_values(old,load_result(new),new.name,errors)
    forces = corner_forces_N(STATIC_N)
    assert abs(sum(forces)-STATIC_N)<TOL
    for i in (0,1):
        moment_Nmm = sum(force*xy[i] for force,xy in zip(forces,CORNERS,strict=True))
        assert abs(moment_Nmm-STATIC_N*ECC_mm)<TOL
    bearing = chamber_bearing()
    assert bearing["aperture_corner_reserve_mm"]>0.
    assert bearing["discharge_axial_clearance_mm"]>=5.
    assert bearing["minimum_ejected_tail_to_gate_clearance_mm"]>=5.
    assert bearing["mean_pressure_MPa"]<=bearing["pressure_limit_MPa"]
    assert bearing["bearing_area_mm2"]>=bearing["minimum_260x160_net_footprint_mm2"]
    rail_mass_kg = 2*RAIL_WIDTH_mm*PAD_HEIGHT_mm*DISCHARGE_BAY_mm*RHO_kg_mm3
    for variant in results["variants"].values():
        frame = variant["mass"]["frame_rows"]
        assert any(row["quantity"]==2 and abs(row["mass_kg"]-rail_mass_kg)<TOL for row in frame)
        assert abs(sum(row["mass_kg"] for row in frame)-variant["mass"]["frame_kg"])<TOL
    paths = [p for p in HERE.rglob("*") if p.is_file()]
    bytes_used = sum(p.stat().st_size for p in paths)
    assert bytes_used<=5_000_000
    assert all(p.suffix!=".frd" and not p.name.endswith("_mesh.inp") for p in paths)
    inp_paths = list(FEA.glob("*.inp"))
    for path in inp_paths:
        deck = path.read_text(encoding="ascii")
        assert "*INCLUDE,INPUT=" in deck and "*NODE\n" not in deck
    for path in paths:
        with path.open("rb") as f:
            assert f.read(1), path
    checks = {
        "task":"T-1.7","round":2,
        "gate_command":"REV_PYTHON -B ops/gates/calc_gates.py "+" ".join(gate_args),
        "gates":results["gates"],"Gmsh":"4.15.0","CalculiX":"2.22","Python":sys.version.split()[0],
        "Gmsh_mesh_seed":42,"Gmsh_threads":1,"ccx_threads":1,
        "replay_commands":commands,
        "deterministic_replay":{
            "full_fea_replay_executed":replay,"generated_deliverables_byte_identical":replay_byte_identical,
            "fea_summaries_byte_identical":original_fea==hashes(sorted(FEA.glob("*.json"))) if replay else None,
            "first_deliverable_sha256":original_hashes,"second_deliverable_sha256":repeated_hashes,
            "absolute_numeric_tolerance":TOL,
            "numeric_differences_exceeding_tolerance":len(errors),"first_errors":errors[:10],
        },
        "checks":{
            "force_and_moment_balance":"PASS","insert_bearing_and_minimum_outlet":"PASS",
            "frame_mass_discharge_rails_and_row_sum":"PASS",
            "plate_verification":"PASS" if results["plate_verification_pass"] else "FAIL",
            "three_mesh_counts":{name:{end:case["mesh_level_count"] for end,case in variant["fea"].items()}
                                  for name,variant in results["variants"].items()},
            "convergence":{name:{end:{zone:row["pass"] for zone,row in case["convergence"].items()}
                                 for end,case in variant["fea"].items()} for name,variant in results["variants"].items()},
            "insert_convergence":{zone:case["pass"] for zone,case in results["insert_FEA"]["convergence"].items()},
            "column_shoulder_convergence":results["column_shoulder_FEA"]["convergence_pass"],
            "thin_inp_count":len(inp_paths),"archive_size_bytes":bytes_used,"full_meshes_in_submission":0,
            "physical_acceptance":"PASS" if results["selected_variant"] else "FAIL",
        },
    }
    write_json(ROOT/"self_check.json",checks)
    print("FEA replay",replay,"deliverable bytes identical",replay_byte_identical,
          "values out of tolerance",len(errors),"bytes",bytes_used,flush=True)
    if errors or not all(value=="PASS" for value in results["gates"].values()):
        raise SystemExit(2)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay",action="store_true")
    main(parser.parse_args().replay)
