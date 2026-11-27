"""Verify analytical invariants, rerun the release gate, and replay the study."""

from hashlib import sha256
from math import isclose
from pathlib import Path
import json
import subprocess
import sys

import yaml

import hand
from load import accepted_load


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULT = HERE / "results.json"
STATUS = HERE / "fea/status.json"
GATES = ROOT / "gates.t22f.json"
METRICS = ROOT / "metrics.json"
REPORT = ROOT / "report.md"
DESIGNS = (ROOT/"design/prepress_lock.t22f.yaml", ROOT/"design/params.t22f.yaml")


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(paths):
    return {str(path.relative_to(ROOT)).replace("\\","/"): sha256(path.read_bytes()).hexdigest() for path in paths}


def verify_load():
    base = accepted_load()
    no_roof = hand.load_cases(0)
    final = [row for row in no_roof if row["label"] == "final"]
    working_N = max(row["shoe"]["force_N"] for row in final)/hand.RATIO
    assert isclose(working_N,base["cases"]["300_bar"]["peak"]["shoe_force_N"],rel_tol=1e-12)
    assert abs(working_N-1_196_000)<1_000
    assert any(row["label"] == "D-GK-11 proof centroid" and row["shoe"]["centroid_x_mm"] == 165.2
               for row in no_roof)
    for roof_mm in (0,15,30,45,60,75,89,90,95):
        for row in hand.load_cases(roof_mm):
            if row["label"] != "final":
                continue
            full = hand.top_load(row["main_force_N"],row["K"],row["mu"],row["punch_mm"],
                                 row["punch_mm"],205+roof_mm)
            assert isclose(full["force_N"],row["shoe"]["force_N"]+row["roof"]["force_N"],rel_tol=1e-12)
    for row in hand.load_cases(90):
        if row["label"]=="final":
            assert row["shoe"]["force_N"]==0
    return working_N


def verify_beam_and_contact(result):
    load_N,L_mm,b_mm,d_mm = 100_000.,200.,90.,80.
    I_mm4=b_mm*d_mm**3/12
    area_mm2=b_mm*d_mm
    point = hand.beam(load_N,L_mm,.001,b_mm,d_mm,skew=.5)
    assert isclose(point["bend_mm"],load_N*L_mm**3/(48*hand.E_MPa*I_mm4),rel_tol=1e-7)
    assert isclose(point["fixed_bend_mm"],load_N*L_mm**3/(192*hand.E_MPa*I_mm4),rel_tol=1e-7)
    assert isclose(point["centroid_shear_mm"],load_N*L_mm/(4*(5/6)*hand.G_MPa*area_mm2),rel_tol=1e-5)
    for item in result["series"].values():
        design = item["hand"]
        assert design["height_ideal_mm"]<=design["height_with_attachments_mm"]
        geo = design["geometry"]
        x1_mm,x2_mm = geo["station_x_mm"].values()
        for station,row in design["stations"].items():
            load = design["load"][station]["case"]["shoe"]
            rear_N,front_N=hand.distribute(load["force_N"],load["centroid_x_mm"],x1_mm,x2_mm)
            assert isclose(rear_N+front_N,load["force_N"],rel_tol=1e-12)
            assert isclose(rear_N*x1_mm+front_N*x2_mm,load["force_N"]*load["centroid_x_mm"],rel_tol=1e-12)
            contact = row["contact"]
            assert contact["static_peak_MPa"]>=contact["mean_300_MPa"]*hand.RATIO


def verify_gates():
    run([sys.executable,"-B","ops/gates/calc_gates.py","--params","design/params.t22d.yaml",
         "--criteria","ops/criteria/design_criteria.yaml","--out",str(GATES)])
    rows = read_json(GATES)["gates"]
    return {row["id"]:{"status":row["status"],"value":row["value"]} for row in rows}


def main():
    paths = [RESULT,METRICS,STATUS,REPORT] + [path for path in DESIGNS if path.exists()]
    first = digest(paths)
    working_N = verify_load()
    verify_beam_and_contact(read_json(RESULT))
    run([sys.executable,"-B",str(HERE/"candidates.py")])
    run([sys.executable,"-B",str(HERE/"report.py")])
    reproduced = digest(paths)
    assert first==reproduced
    assert all(not path.exists() for path in DESIGNS)
    gate_rows = verify_gates()
    assert set(gate_rows)=={"G-PFACE","G-DOSE","G-CYCLE"}
    assert all(row["status"]=="PASS" for row in gate_rows.values())
    assert abs(gate_rows["G-CYCLE"]["value"] - 5.928629160188188)<1e-9
    run(["git","diff","--exit-code","--","ops/criteria","ops/gates","DECISIONS.md","AGENTS.md",
         "PLAN.md","CLAUDE.md","design","docs"])
    report = REPORT.read_text(encoding="utf-8")
    assert report.startswith("# T-2.2f") and "\ufffd" not in report
    assert "STOP" in report and len(report.split())<1400
    yaml.safe_load((HERE/"sources.yaml").read_text(encoding="utf-8"))
    files = [path for path in HERE.rglob("*") if path.is_file()]
    for path in files + [METRICS,GATES,REPORT]:
        path.read_bytes().decode("utf-8")
    largest_file_bytes = max(path.stat().st_size for path in files)
    total_bytes = sum(path.stat().st_size for path in files)
    assert total_bytes < 5_000_000
    assert not any(path.suffix in {".msh",".frd",".inp",".pyc"} for path in files)
    output = dict(task="T-2.2f", status="PASS_STOP_DELIVERABLES", design_qualification="STOP_HAND_SCREEN",
                  python_version=sys.version.split()[0], official_gate_params="design/params.t22d.yaml",
                  gates=gate_rows, checks=dict(
                      load_and_axial_balance="PASS", beam_point_limit_and_contact="PASS",
                      D_GK_10_no_roof_force_300_N=working_N,
                      deterministic_two_full_runs="PASS", reproduced_sha256=reproduced,
                      protected_tracked_files="PASS", report_utf8="PASS",
                      readable_from_workspace_shell="PASS", report_words=len(report.split()),
                      no_solver_or_bytecode_files="PASS", calc_package_bytes=total_bytes,
                      largest_calc_file_bytes=largest_file_bytes,
                      design_yaml="NO_SELECTION_NO_OUTPUT", FEA="NOT_RUN_STOP_HAND_SCREEN"))
    (ROOT/"self_check.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",
                                       encoding="utf-8",newline="\n")


if __name__=="__main__":
    main()
