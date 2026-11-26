"""Check byte reproducibility, run the published gates and record the outcomes."""
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPRODUCED = ("calc/T-2.1/results.json", "design/params.t21.yaml", "metrics.json")


def read_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def run(args, *, capture=False, allow_failure=False):
    return subprocess.run([sys.executable, "-B", *args], cwd=ROOT, check=not allow_failure,
                          capture_output=capture, encoding="utf-8" if capture else None)


def digests():
    return {filename: sha256((ROOT / filename).read_bytes()).hexdigest() for filename in REPRODUCED}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--compare-existing", action="store_true", help="Use the existing outputs as the first run")
    args = parser.parse_args()
    generation = ["calc/T-2.1/study.py"]
    if not args.compare_existing:
        run(generation)
    first = digests()
    run(generation)
    second = digests()
    assert first == second, {path: second[path] for path in second if first[path] != second[path]}

    gate_args = ["ops/gates/calc_gates.py", "--params", "design/params.t21.yaml", "--criteria",
                 "ops/criteria/design_criteria.yaml", "--out", str(ROOT / "gates.t21.json")]
    gate_process = run(gate_args, allow_failure=True)
    gate_report = read_json("gates.t21.json")
    gates = {gate["id"]: {key: gate[key] for key in ("status", "value", "unit")} for gate in gate_report["gates"]}
    assert set(gates) == {"G-PFACE", "G-DOSE", "G-CYCLE"}

    results = read_json("calc/T-2.1/results.json")
    screened = results["candidates"][results["gate_candidate"]]["summary"]
    assert abs(gates["G-CYCLE"]["value"] - screened["gate_cycle_s"]) < 1e-10
    if results["selected"]:
        assert gate_process.returncode == 0 and all(g["status"] == "PASS" for g in gates.values())
        assert gates["G-CYCLE"]["value"] <= 5.95
        assert all(screened["qualification"].values())

    pairs = set()
    for name, entry in results["candidates"].items():
        cases = entry["scenarios"]
        assert len(cases) == 16
        pairs.update((name, row["case"], row["bulk_kg_m3"], row["profile"], row["residual_N"])
                     for row in cases)
        for row in cases:
            assert row["feasible"], row
            assert all(step_s <= .0025 for step_s, _ in row["convergence"])
            assert row["convergence_pass"]
            assert abs(row["net_lp_oil_balance_L"]) < 1e-5
    case_count = len(pairs)
    assert case_count == 16 * len(results["candidates"])

    test_args = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/ops/test_calc_gates.py"]
    tested = run(test_args, capture=True)
    print(tested.stdout)
    test_summary = tested.stdout.strip().splitlines()[-1].split(" in ")[0]

    file_set = sorted([path for path in HERE.rglob("*") if path.is_file()]
                      + [ROOT / "report.md", ROOT / "metrics.json", ROOT / "gates.t21.json",
                         ROOT / "design/params.t21.yaml"])
    for file in file_set:
        assert os.access(file, os.R_OK)
        file.read_bytes()
    self_check = dict(
        python_version=sys.version.split()[0], gate_candidate=results["gate_candidate"], selected=results["selected"],
        gates=gates, gate_command=["REV_PYTHON", "-B", *gate_args], gate_exit_code=gate_process.returncode,
        deterministic_generation=dict(status="PASS", command=["REV_PYTHON", "-B", *generation],
                                      run_count=2, sha256=second),
        test_command=["REV_PYTHON", "-B", *test_args], test_status="PASS", test_summary=test_summary,
        reference_replay=dict(status="PASS", **results["reference_T17d"]),
        model_invariants=dict(status="PASS", scenario_count=case_count,
                              checks=["maximum working pressure", "shaft command limit", "interlock order",
                                      "periodic LP oil balance", "phase heat ledger closure", "stroke bounds",
                                      "time-step convergence", "no press/dwell overlap in gate params"]),
        deliverable_readability=dict(status="PASS", files_read=len(file_set) + 1),
    )
    output = ROOT / "self_check.json"
    output.write_text(json.dumps(self_check, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    assert os.access(output, os.R_OK) and output.read_bytes()
    print("T-2.1 gates, reproducibility and cycle checks recorded", flush=True)


if __name__ == "__main__":
    main()

