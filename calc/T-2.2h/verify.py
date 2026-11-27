"""Rebuild twice, compare independent solver replays and record task checks."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import os
import subprocess
import sys
from tempfile import TemporaryDirectory


from run import HERE, ROOT, write_json

OUTPUTS=(HERE/"results.json",ROOT/"design/chamber_roof.t22h.yaml",
         ROOT/"metrics.json",ROOT/"report.md")
REPLAY_TOLERANCE=1e-6


def compare(a,b,errors):
    if isinstance(a,dict):
        # Optimizer metadata was added after the first runs. Numerical mesh
        # and solution metrics are checked for every retained case.
        ignored={"high_order_optimizer"}
        assert a.keys()-ignored==b.keys()-ignored
        for key in sorted(a.keys()-ignored):
            compare(a[key],b[key],errors)
    elif isinstance(a,list):
        assert len(a)==len(b)
        for u,v in zip(a,b,strict=True):
            compare(u,v,errors)
    elif isinstance(a,float):
        error=abs(a-b)/max(1.,abs(a),abs(b))
        errors.append(error)
    else:
        assert a==b,(a,b)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def replay_check():
    fea=HERE/"fea"
    sources={
        "ring":("ring_screen.json",),
        "end":("end_screen.json",),
        "window":("window_screen.json","window_fine.json"),
        "window_half":("window_half.json",),
        "window_double":("window_double.json",),
    }
    results={}
    for scope,names in sources.items():
        expected=[row for name in names for row in read(fea/name)]
        replay=fea/f"replay_{scope}.json"
        if not replay.exists():
            results[scope]={"status":"NOT_RUN"}
            continue
        actual=read(replay)
        errors=[]
        try:
            compare(expected,actual,errors)
        except AssertionError as e:
            results[scope]={"status":"FAIL","error":str(e) or "structural or integer mismatch"}
            continue
        max_error=max(errors,default=0.)
        results[scope]={"status":"PASS" if max_error<=REPLAY_TOLERANCE else "FAIL",
                        "rows_compared":len(expected),"scalar_count":len(errors),
                        "maximum_scaled_or_absolute_error":max_error}
    return results


def window_edge_crosscheck():
    """Compare the supplemental two-step C3D10 model with full histories."""
    fea=HERE/"fea"
    full=read(fea/"window_screen.json")+read(fea/"window_fine.json")
    reduced=read(fea/"window_edge.json")
    errors=[]
    for a,b in zip(full,reduced,strict=True):
        assert a["mesh_mm"]==b["mesh_mm"] and a["elements"]==b["elements"]
        for label,ra in a["cases"].items():
            rb=b["cases"][label]
            common={k:v for k,v in rb["safety"].items() if k!="cast_front_cut"}
            compare(ra["safety"],common,errors)
            for bar in ("300","315"):
                a_state=dict(ra["states"][bar])
                b_state=dict(rb["states"][bar])
                b_state["regions"]={k:v for k,v in b_state["regions"].items() if k!="cast_front_cut"}
                compare(a_state,b_state,errors)
    return {"mesh_count":len(full),"maximum_scaled_or_absolute_error":max(errors),
            "status":"PASS" if max(errors)<=REPLAY_TOLERANCE else "FAIL"}


def main():
    parser=ArgumentParser()
    parser.add_argument("--clean-replays",action="store_true")
    options=parser.parse_args()
    env=os.environ | {"OPENBLAS_NUM_THREADS":"1","PYTHONDONTWRITEBYTECODE":"1"}
    commands=[
        sys.executable,"-B","ops/gates/calc_gates.py","--params","calc/T-2.6/params/params.t26a.yaml",
        "--criteria","ops/criteria/design_criteria.yaml","--out","gates.t22h.json",
    ]
    gate=subprocess.run(commands,cwd=ROOT,env=env,check=False)
    with TemporaryDirectory(prefix="verify-",dir=HERE) as scratch:
        out=Path(scratch)/"arithmetic.json"
        cmd=[sys.executable,"-B",str(HERE/"run.py"),"--audit-out",str(out)]
        digests=[]
        for _ in range(2):
            subprocess.run(cmd,cwd=ROOT,env=env,check=True)
            digests.append({str(p.relative_to(ROOT)).replace(chr(92),"/"):sha256(p.read_bytes()).hexdigest()
                            for p in OUTPUTS})
        arithmetic=read(out)
    assert digests[0]==digests[1]
    data=read(HERE/"results.json")
    m=read(ROOT/"metrics.json")
    assert m["status"]==data["status"]=="STOP"
    assert not m["qualified"] and not data["qualified"]
    assert "?" not in (ROOT/"report.md").read_text(encoding="utf-8")
    replay=replay_check()
    clean=options.clean_replays and all(item["status"]=="PASS" for item in replay.values())
    if clean:
        for part in replay:
            path=HERE/"fea"/f"replay_{part}.json"
            assert path.resolve().is_relative_to(HERE/"fea")
            path.unlink()
    fea=data["FEA"]
    conv=fea["convergence"]
    max_moment=max((r["moment_error_fraction"] for g in fea["roof"] for r in g["integrated_sections_315"]),
                   default=None)
    max_force=max((g["normal_case_force_balance_fraction"] for g in fea["roof"]),default=0.)
    max_win=max((g["force_balance_fraction"] for g in fea["window"]),default=0.)
    max_end=max((x for g in fea["end"] for x in g["global_force_balance_fraction"]),default=0.)
    protected=subprocess.run(["git","diff","--name-only","HEAD","--","ops","DECISIONS.md",
                              "PLAN.md","CLAUDE.md","AGENTS.md","design"],cwd=ROOT,
                             check=True,capture_output=True,text=True,env=env).stdout.splitlines()
    assert not protected,protected
    temp_inside=sorted(str(p.relative_to(HERE)) for p in HERE.rglob("*") if p.is_dir() and
                        (p.name.startswith(("ring-","window-","end-","verify-")) or p.name=="__pycache__"))
    artifacts=[p for p in HERE.rglob("*") if p.is_file() and not p.name.startswith("replay_")]
    retained_bytes=sum(p.stat().st_size for p in artifacts)
    mesh_files=[p.name for p in artifacts if p.suffix.lower() in (".msh",".frd",".inp",".geo")]
    summary=dict(
        task="T-2.2h",status="STOP",gates=data["gates"],gates_cli_exit_code=gate.returncode,
        report_valid_utf8_and_no_question_mark=True,deterministic_assembly_two_runs=True,
        output_SHA256=digests[-1],arithmetic=arithmetic,fea_replays=replay,
        replay_numeric_tolerance=REPLAY_TOLERANCE,replay_provisional_json_cleaned=clean,
        supplemental_edge_common_outputs_crosscheck=window_edge_crosscheck(),
        gate_cycle_role="informational by D-GK-13 and D-OP-16",
        fea_diagnostic_convergence=conv,
        passed_convergence_lt_5pct={k:(v < .05 if isinstance(v,float) else None)
                                    for k,v in conv.items() if k!="definition"},
        passed_force_balance_le_0_1pct={k:v <= .001 for k,v in
                                       {"roof":max_force,"window":max_win,"end":max_end}.items()},
        maximum_force_residual_fraction={"roof":max_force,"window":max_win,"end":max_end},
        max_hand_FEA_moment_error_fraction=max_moment,
        criteria=dict(
            hand_margin_in_full_trial_mass_budget="FAIL",
            C_STR_01="NOT_QUALIFIED",
            C_FAT_01="FAIL_DIAGNOSTIC",
            opening_under_window="FAIL",
            opening_under_roof="BACKING_ONLY",
            convergence_thickness_two_elements_verified=False,
            actual_contact_and_interference_signoff=False,
            contact_cyclic_screen="FAIL_NOMINAL_AXIAL_RAIL",
            station_mass_230_kg="FAIL_TRIAL",
        ),
        protected_tracked_paths_changed=protected,
        transient_directories=temp_inside,retained_solver_meshes=mesh_files,
        retained_calc_bytes=retained_bytes,calc_size_limit_bytes=5_000_000,
    )
    write_json(ROOT/"self_check.json",summary)
    print(json.dumps({"gates":data["gates"],"replay":replay,"size_bytes":retained_bytes},indent=2))
    if all(row["status"]=="PASS" for row in replay.values()) and (temp_inside or mesh_files):
        raise SystemExit("Temporary solver files remain")


if __name__=="__main__":
    main()

