"""Run the documented acceptance checks and compare two independent builds."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from build_scheme import DESIGN, HERE, ROOT, read
from check_circuit import CIRCUIT, INTERLOCKS
from revision import PARAMS
from run import write_json


def invoke(name, args, *, aliases=None):
    completed = subprocess.run(
        [sys.executable, *args], cwd=ROOT, check=False, capture_output=True,
        encoding="utf-8", env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
    )
    if completed.returncode:
        raise RuntimeError(f"{name} {completed.returncode}\n{completed.stdout}\n{completed.stderr}")
    output = completed.stdout.strip()
    if name == "test_interlocks":
        output = output.splitlines()[-1].split(" in ")[0]
    return {"name": name, "argv_after_python": aliases if aliases else args,
            "exit_code": completed.returncode, "status": "PASS", "stdout": output}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def verify():
    tracked = [HERE / "results.json", DESIGN / "T-2.9b_circuit.svg", PARAMS, DESIGN / "station.t29b.yaml"]
    run_args = [relative(HERE / "run.py")]
    prime = invoke("Build 1", run_args)
    first = {relative(path): sha256(path) for path in tracked}
    repeat = invoke("Build 2", run_args)
    second = {relative(path): sha256(path) for path in tracked}
    assert first == second
    with TemporaryDirectory(prefix="verify_", dir=HERE) as folder:
        checker_out = Path(folder) / "circuit.json"
        check_args = [relative(HERE / "check_circuit.py"), "--circuit", relative(CIRCUIT),
                      "--interlocks", relative(INTERLOCKS), "--out", relative(checker_out)]
        checked = invoke("check_circuit", check_args, aliases=check_args[:-1] + ["temporary file in calc/T-2.9b"])
        circuit = json.loads(checker_out.read_bytes())["circuit"]
    old_circuit = json.loads((ROOT / "ops/reports/T-2.9/circuit.GK.json").read_bytes())
    old_names = {row["name"] for row in old_circuit.get("circuit", old_circuit)["mutations"]["cases"]}
    new_names = {row["name"] for row in circuit["mutations"]["cases"]}
    assert len(old_names) == 186 and old_names <= new_names
    tests = invoke("test_interlocks", ["-m", "pytest", "-q", "-p", "no:cacheprovider",
                                      relative(HERE / "test_interlocks.py")])
    gate_args = ["ops/gates/calc_gates.py", "--params", relative(PARAMS), "--criteria",
                 "ops/criteria/design_criteria.yaml", "--out", "gates.t29b.json"]
    gates = invoke("G-PFACE, G-DOSE, G-CYCLE", gate_args)
    new, old = read(PARAMS), read(HERE / "params/params.t29.yaml")
    assert new["drive"]["installed_kW"] == old["drive"]["installed_kW"]
    old["cycle_model"]["oil"]["bulk_modulus_Pa"] = new["cycle_model"]["oil"]["bulk_modulus_Pa"]
    old["cycle_model"]["lp"]["routes"] = ["pre_up", "pre_down", "eject"]
    assert new == old
    assert new["cycle_model"]["oil"]["bulk_modulus_Pa"] <= 1_400_000_000
    ElementTree.parse(DESIGN / "T-2.9b_circuit.svg")
    model, logic = read(CIRCUIT), read(INTERLOCKS)
    for tag in ("PC", "CB", "TT", "TT_VALID", "TT_MIN"):
        assert "??" not in str(model["elements"][tag])
    assert "??" not in str(logic["pc_warmup_strategy"])
    doc = (ROOT / "report.md").read_text(encoding="utf-8")
    size_bytes = sum(path.stat().st_size for path in HERE.rglob("*") if path.is_file())
    assert "?" not in doc and size_bytes < 5_000_000
    assert circuit["defects"] == 0 and circuit["mutations"]["total"] == circuit["mutations"]["rejected"]
    result = json.loads((HERE / "results.json").read_bytes())
    assert circuit == result["circuit"]
    assert result["gate_nominal"]["card_pass"] and result["gate_nominal"]["method"] == "reference_model"
    assert result["gate_status"] == {"G-PFACE": "PASS", "G-DOSE": "PASS", "G-CYCLE": "PASS"}
    write_json(ROOT / "self_check.json", {
        "task": "T-2.9b", "task_status": result["status"], "blockers": result["blockers"],
        "python_version": sys.version.split()[0], "checks": [prime, repeat, checked, tests, gates],
        "gate_status": result["gate_status"], "gate_cycle": result["gate_nominal"],
        "circuit_defects": circuit["defects"], "mutations_total": circuit["mutations"]["total"],
        "mutations_rejected": circuit["mutations"]["rejected"],
        "inherited_mutations_preserved": len(old_names), "inherited_mutations_removed": sorted(old_names - new_names),
        "two_builds_byte_identical": True, "product_sha256": first, "svg_parse": "PASS",
        "report_utf8_no_question_marks": True, "calc_total_bytes": size_bytes,
        "params_conservative_diff_check": "PASS",
    })
    print(tests["stdout"])
    print("Two builds, three frozen gates, circuit checker and 186 inherited mutation names verified.")


if __name__ == "__main__":
    verify()

