"""Reproduce artifacts, check numerical evidence and record unmet acceptance."""

from hashlib import sha256
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
import json
import os
import sys

import yaml

from loads import ROOT
from run import HERE, FEA, read, write_json

GATE_ARGS = ["ops/gates/calc_gates.py","--params","calc/T-2.6/params/params.t26a.yaml",
             "--criteria","ops/criteria/design_criteria.yaml","--out"]
ARTIFACT_PATHS = ("calc/T-2.2g/results.json","design/chamber_roof.t22g.yaml","metrics.json")
CRITERIA_SHA256 = "cbab2073e6d40de242312209d327bc0ef7ea3aef08affb045a1e18d7026bd58f"
TOL_FEA = 1.e-6


def py(*args):
    return run([sys.executable,"-B",*map(str,args)],cwd=ROOT,check=False)


def compare(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)) and not isinstance(a,bool):
        return abs(a-b),True
    if type(a) is not type(b):
        return 0.,False
    if isinstance(a,dict) and a.keys()==b.keys():
        stats=[compare(v,b[k]) for k,v in a.items()]
    elif isinstance(a,list) and len(a)==len(b):
        stats=[compare(x,y) for x,y in zip(a,b,strict=True)]
    else:
        return 0.,a==b
    return max((v for v,_ in stats),default=0.),all(s for _,s in stats)


def replay():
    paths=("ring_three_meshes.json","ring_replay.json")
    a,b=(FEA / p for p in paths)
    if not b.is_file():
        return {"status":"NOT_RUN","reason":"Independent roof replay absent"}
    base,repeat=(read(p) for p in (a,b))
    # The independent replay records the optional inactive saddle flag
    # explicitly. The first series omitted the flag for the same condition.
    for row in base+repeat:
        row.setdefault("trial_transverse_saddles",False)
    error,shape=compare(base,repeat)
    return {"status":"PASS" if shape and error<=TOL_FEA else "FAIL","paths":list(paths),
            "absolute_error_max":error,"tolerance_absolute":TOL_FEA,
            "same_structure_after_default_metadata_normalization":shape,"roof_mesh_levels":len(repeat)}


def main():
    with TemporaryDirectory(prefix="t22g-check-",dir=HERE) as label:
        folder=Path(label)
        first,second=folder/"a",folder/"b"
        first.mkdir()
        second.mkdir()
        gate_code=[]
        for target in (first,second):
            gate_code.append(py(*GATE_ARGS,target/"gates.t22g.json").returncode)
            py("calc/T-2.2g/run.py","--outroot",target).check_returncode()
        gate_bytes=[(p/"gates.t22g.json").read_bytes() for p in (first,second)]
        asserts = {name:(first/name).read_bytes()==(second/name).read_bytes()==(ROOT/name).read_bytes()
                   for name in ARTIFACT_PATHS}
        gate_report=read(first/"gates.t22g.json")
        gate_equal=gate_bytes[0]==gate_bytes[1]==(ROOT/"gates.t22g.json").read_bytes()
    primary={g["id"]:{"status":g["status"],"value":g["value"],"unit":g["unit"]} for g in gate_report["gates"]}
    r=read(ROOT/"calc/T-2.2g/results.json")
    m=read(ROOT/"metrics.json")
    y=yaml.safe_load((ROOT/"design/chamber_roof.t22g.yaml").read_text(encoding="utf-8"))
    old_report=(ROOT/"report.md").read_bytes()
    py("calc/T-2.2g/report.py").check_returncode()
    report=(ROOT/"report.md").read_text(encoding="utf-8")
    assert report.encode("utf-8")==old_report and "?" not in report and "\ufffd" not in report
    proof=r["fea"]["ring"]["ring_three_meshes"]
    membrane=proof[-1]["cases"]["long_skew"]["membrane_sections_315"]
    pressure_bal=max(abs(v["axial_balance_error_N"]) for rows in r["loads"].values() for v in rows)
    ring_balance=max(v["cases"]["long_skew"]["maximum_balance_fraction"] for v in proof)
    c=r["fea"]["cassette"]
    window=r["fea"]["window"]["window_reinforced"][-1]
    # Existing files in the explicit inputs/protected paths, without scanning LFS objects.
    protected=run(["git","diff","--name-only","HEAD","--","DECISIONS.md","ops","design",
                   "AGENTS.md","PLAN.md","CLAUDE.md","calc/T-2.2e","calc/T-2.2f","calc/T-2.6"],
                  cwd=ROOT,check=True,capture_output=True,text=True,
                  env=os.environ|{"GIT_OPTIONAL_LOCKS":"0"}).stdout.splitlines()
    files=[p for p in HERE.rglob("*") if p.is_file()]
    temp=[p.relative_to(HERE).as_posix() for p in HERE.rglob("*") if p.is_dir() and
          (p.name.startswith(("t22g-","reference_","r2_aligned_")) or p.name=="__pycache__")]
    cad_suffixes={".msh",".frd",".inp",".inc",".geo",".fcstd",".brep",".step",".stp"}
    packagesize=sum(p.stat().st_size for p in files)
    criteria_sha=sha256((ROOT/"ops/criteria/design_criteria.yaml").read_bytes()).hexdigest()
    max_stage_force_difference=max(abs(primary[k]["value"]-v)
                                   for k,v in (("G-PFACE",m["G_PFACE_MPa"]),("G-DOSE",m["installed_main_stroke_mm"])))
    dynamic={
        "primary_gates_pass":all(primary[g]["status"]=="PASS" for g in ("G-PFACE","G-DOSE")),
        "gate_output_identical":gate_equal,"artifacts_byte_identical":asserts,
        "roof_FEA_independent_replay":replay(),"report_utf8_roundtrip":True,
        "report_body_words":len(report.split()),
        "criteria_sha_unchanged":criteria_sha==CRITERIA_SHA256,
        "protected_existing_paths_changed":protected,"package_bytes":packagesize,
        "solver_temporary_paths_remaining":temp,"shipped_solids_or_meshes":sum(p.suffix.lower() in cad_suffixes for p in files),
        "static_step_envelope_bar":[0,100,200,300,315],
        "ring_C3D10_positive_jacobians":all(not k["mesh_jacobians"]["nonpositive_element_count"] for k in proof),
        "ring_mesh_size_below_half_thinnest_solid_wall":all(
             2*q["mesh_mm"]<=min(q["layout"]["roof_wall_mm"]-12.,q["layout"]["roof_band_mm"]-12.)
             for q in proof),
        "analytic_Janssen_balance_abs_error_N":pressure_bal,
        "ring_max_vector_force_balance_fraction":ring_balance,
        "gate_metrics_agree_abs":max_stage_force_difference,
        "cassette_contact_meshes_completed":[x["mesh_level"] for x in r["fea"]["cassette_meshes"]],
        "window_unilateral_reactions_pass":all(x["bearing_reaction_signs_valid"]
                                                 for x in r["fea"]["window"]["window_reinforced"]),
        "failed_fea_attempts":[x["file"] for x in r["fea"]["failed_trials"]],
        "key_contact_target_force_relative_error_max":r["fea"]["key_contact"]["maximum_force_relative_error"]
            if r["fea"]["key_contact"] else None,
        "key_proof_contact_target_force_relative_error":r["fea"]["key_proof"]["relative_315_force_error"]
            if r["fea"]["key_proof"] else None,
        "test_nominal_geometry":{
            "section_match":y["working_section_yz_mm"]==[150.,60.],
            "roof_match":y["fixed_working_roof_length_mm"]==90.,
            "stroke_match":y["interfaces"]["main_installed_stroke_mm"]==396.,
            "gate_nominal_wings_clearance_mm":y["interfaces"]["gate_wing_relief_min_axial_clearance_mm"],
            "parked_key_to_shoe_mm":y["interfaces"]["key_park_to_shoe_clearance_mm"],
        },
    }
    evidence={
        "C_STR_01_roof":m["roof_FEA_static_factor"]>=1.5,
        "C_FAT_01_roof":m["roof_FEA_FKM"]>=1.,
        "C_FAT_01_open_casting":min(k["cast_cheek"]["FKM"] for k in window["regional_check"].values())>=1.,
        "roof_delta_h":m["roof_FEA_opening_300_mm"]<=.6,
        "shoe_delta_h_reinforced":m["open_window_reinforced_FEA_opening_300_mm"]<=.6,
        "fixed_roof_gauge_convergence":r["fea"]["ring_convergence"]["invariant_and_opening_lt_5_pct"],
        "hand_FE_membrane_sections_within_15_pct":all(item["error_relative"]<=.15 for item in membrane),
        "cassette_static_contact_screen":all(x["static_screen_pass"] for x in r["fea"]["cassette_meshes"]),
        "cassette_contact_peak_convergence":len(r["fea"]["cassette_meshes"])==3 and all(
            v is not None and v<.05 for v in r["fea"]["cassette_peak_relative_changes"].values()),
        "shoe_latch_local_contact":"DIAGNOSTIC_ONLY" if r["fea"]["key_contact"] else "OPEN",
        "real_roof_support_model":"OPEN",
        "geometry_full_assembly_and_clearance":"OPEN",
        "station_grading_D_OP_16":max(m["required_station_reduction_kg"])<=145.,
    }
    write_json(ROOT/"self_check.json",{
        "task":"T-2.2g","qualification_status":m["status"],"python_version":sys.version.split()[0],
        "gmsh_version":"4.15.0","ccx_version":"2.22","gates":primary,"gate_exit_codes":gate_code,
        "G_CYCLE_disposition":"Informational under D-GK-13 / D-OP-16. The reference simulation is T-2.6.",
        "verification":dynamic,"engineering_acceptance":evidence,
    })
    if (not dynamic["primary_gates_pass"] or not gate_equal or not all(asserts.values()) or
        protected or criteria_sha!=CRITERIA_SHA256 or packagesize>=5_000_000 or temp or dynamic["shipped_solids_or_meshes"]):
        raise SystemExit("Artifact verification failed. Read self_check.json.")
    if dynamic["roof_FEA_independent_replay"]["status"]!="PASS":
        raise SystemExit("The independent FEA replay has not passed. Read self_check.json.")
    print(f"{m['status']}: engineering acceptance unresolved; artifact verification passed")


if __name__=="__main__":
    main()

