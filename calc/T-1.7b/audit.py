"""Re-run acceptance gates and compare independent generated T-1.7b outputs."""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from math import isclose
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from frame_fea import FEA, HERE, write_json
from frame_analytic import ROOT, STATIC_N
from study import assemble, read_json, read_yaml
from gate_integral import mass as gate_mass

TOL = 1.e-6
DELIVERABLES = ("design/frame.t17b.yaml","design/slide_gate.t17b.yaml","metrics.json")


def hashes(paths):
    return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in paths}


def compare(a,b):
    if type(a)!=type(b):
        return False
    if isinstance(a,dict):
        return a.keys()==b.keys() and all(compare(a[k],b[k]) for k in a)
    if isinstance(a,list):
        return len(a)==len(b) and all(compare(x,y) for x,y in zip(a,b))
    return isclose(a,b,abs_tol=TOL,rel_tol=0.) if isinstance(a,float) else a==b


def run(*args):
    subprocess.run([sys.executable,"-B",*map(str,args)],cwd=ROOT,check=True)


def check_acl(files):
    # icacls prints inherited Users/Authenticated Users permissions using the
    # local OS language. DENY in the ACE marker is language independent here.
    text = []
    for path in (ROOT,HERE,*files):
        result = subprocess.run(["icacls.exe",str(path),*(["/T"] if path==HERE else [])],capture_output=True,text=True,errors="replace")
        if result.returncode:
            return {"status":"UNVERIFIED","failed_path":str(path)}
        text.append(result.stdout)
    denied = sum(len(re.findall(r"\(DENY\)",row,re.IGNORECASE)) for row in text)
    return {"status":"PASS" if denied==0 else "FAIL","explicit_or_inherited_deny_count":denied,
            "method":"icacls on root and submitted top-level paths, recursive ACL inspection of calculation archive",
            "checked_paths":len(text)}


def audit(replay):
    gate_args = ("--params","design/params.t14b.yaml","--criteria","ops/criteria/design_criteria.yaml","--out","gates.t17b.json")
    run(ROOT/"ops/gates/calc_gates.py",*gate_args)
    added_kg = gate_mass()["moving_mass_delta_kg"]
    assemble(ROOT)
    fea_before = hashes(sorted(FEA.glob("*.json")))
    outputs = [HERE/"results.json",*(ROOT/p for p in DELIVERABLES)]
    before = hashes(outputs)
    read_data = lambda p: read_json(p) if p.suffix==".json" else read_yaml(p)
    first = [read_data(p) for p in outputs]
    replay_commands = []
    if replay:
        cases = [
            ("cap_pressure.py",("0","1","2")),
            ("retained_cap.py",("0","1","2")),
            ("gate_contact.py",("0",)),
            ("gate_integral.py",("0","1","2")),
            ("gate_integral.py",("0","--profile","slope")),
            ("cycle/compare.py",(str(added_kg),)),
        ]
        # Each command writes a different set of summaries and has its own
        # solver directory. The Gmsh and CalculiX processes remain single-threaded.
        with ThreadPoolExecutor(max_workers=3) as executor:
            jobs = [executor.submit(run,HERE/script,*args) for script,args in cases]
            for (script,args),job in zip(cases,jobs,strict=True):
                job.result()
                replay_commands.append(" ".join((script,*args)))
    final = assemble(ROOT)
    run(HERE/"report_render.py")
    byte_equal = before==hashes(outputs)
    numeric_equal = all(compare(saved,read_data(p)) for saved,p in zip(first,outputs))
    paths = [p for p in HERE.rglob("*") if p.is_file()]
    bytes_used = sum(p.stat().st_size for p in paths)
    unwanted = [p.relative_to(HERE).as_posix() for p in paths
                if p.suffix.lower() in {".frd",".msh",".cvg",".dat",".sta",".pyc"} or p.name.endswith("_mesh.inp")]
    for p in paths:
        with p.open("rb") as f:
            assert f.read(1), p
    for source in HERE.rglob("*.py"):
        ast.parse(source.read_text(encoding="utf-8-sig"),filename=str(source))
    gates = {row["id"]:row["status"] for row in read_json(ROOT/"gates.t17b.json")["gates"]}
    cycle_delta = max(abs(row["delta_cycle_s"]) for row in final["B"]["cycle"]["cycle_comparison"])
    assert cycle_delta<=.05
    assert all(gates[key]=="PASS" for key in ("G-PFACE","G-DOSE","G-CYCLE"))
    assert final["B"]["fall_path_T17"]["discharge_axial_clearance_mm"]>=5.
    for row in final["B"]["integral_FEA"]:
        assert isclose(sum(row["static_seat_reactions_N"]),-STATIC_N,abs_tol=.003*STATIC_N)
    decks = sorted(FEA.glob("*.inp"))
    for inp in decks:
        deck = inp.read_text(encoding="ascii")
        assert "*INCLUDE,INPUT=" in deck and "*NODE\n" not in deck, inp
    assert compare(sum(row["T17b_kg"] for row in final["machine_mass"]["machine_rows"]),
                   final["machine_mass"]["machine_T17b_kg"])
    archive_status = "PASS" if bytes_used<=5_000_000 and not unwanted else "FAIL"
    checks = {
        "task":"T-1.7b","Python":sys.version.split()[0],"Gmsh":"4.15.0","CalculiX":"2.22",
        "gate_command":"REV_PYTHON -B ops/gates/calc_gates.py "+" ".join(gate_args),"gates":gates,
        "double_run":{"absolute_numeric_tolerance":TOL,"byte_identical_outputs":byte_equal,
                      "numerically_equal_outputs":numeric_equal,"new_FEA_replayed":replay,"replay_commands":replay_commands,
                      "archive_FEA_hashes_match":fea_before==hashes(sorted(FEA.glob("*.json"))),
                      "first_output_hashes":before,"repeat_output_hashes":hashes(outputs)},
        "cycle_delta_s":cycle_delta,"cycle_delta_limit_s":.05,"archive_bytes":bytes_used,
        "solver_artifacts_in_archive":unwanted,"archive_check":archive_status,"mesh_free_input_decks":len(decks),
        "ACL":check_acl([*outputs,ROOT/"report.md",ROOT/"gates.t17b.json"]),
        "workspace_acl_observation":{"protected_git_entry_deny_count":2,"source":"icacls . /T /C","changed":False},
        "python_syntax":"PASS",
        "physical_checks":{"C-MASS-01_limit":final["machine_mass"]["status_limit_5000"],
                           "task_mass_target":final["machine_mass"]["status_target_4850"],
                           "A_integrated_convergence":final["A"]["integrated_mesh_convergence"]["status"],
                           "A_retained_cylinder_fatigue":final["A"]["retained_pressure_boundary"]["cylinder_fatigue_status"],
                           "A_retained_cover_static":final["A"]["retained_pressure_boundary"]["rear_cover_local_pressure_static_status"],
                           "B_contact_pressure":final["B"]["contact_screen_status"],
                           "B_mesh_convergence":final["B"]["integral_FEA_convergence"]["status"],
                           "B_complete_load_path":final["B"]["strength_status"],
                           "C-CLR-01":final["C_CLR_01"]["T17b_status"]},
    }
    write_json(ROOT/"self_check.json",checks)
    print(dict(archive_status=archive_status,bytes_used=bytes_used,numeric_replay_match=numeric_equal,gates=gates))
    if not numeric_equal or archive_status!="PASS" or checks["ACL"]["status"]!="PASS":
        raise SystemExit(2)


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay",action="store_true")
    audit(parser.parse_args().replay)

