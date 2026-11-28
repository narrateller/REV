"""Run both check entry points and verify repeatable bytes."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from build_scheme import ROOT, HERE, DESIGN, read
from check_circuit import CIRCUIT, INTERLOCKS
from hoses import PARAMS, REFERENCE
from run import write_json


def run_command(args):
    proc = subprocess.run([sys.executable, "-X", "utf8", "-B", *args], cwd=ROOT,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          capture_output=True, text=True, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"{args}\n{proc.stdout}\n{proc.stderr}")
    return {"command": ["REV_PYTHON", "-X", "utf8", "-B", *args], "exit_code": proc.returncode,
            "stdout": proc.stdout.strip()}


def verify(reuse_scan):
    base = "calc/T-2.9/"
    run_args = [base + "run.py"] + (["--reuse-scan"] if reuse_scan else [])
    tracked = [HERE / "results.json", DESIGN / "T-2.9_circuit.svg", PARAMS]
    replays = []
    byte_sets = []
    for _ in range(2):
        replays.append(run_command(run_args))
        byte_sets.append([path.read_bytes() for path in tracked])
    assert byte_sets[0] == byte_sets[1]
    repeats = {path.relative_to(ROOT).as_posix(): {
        "status": "PASS", "sha256": sha256(bytestring).hexdigest(), "bytes": len(bytestring)}
        for path, bytestring in zip(tracked, byte_sets[0])}

    result = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    criteria = result["gate_status"]
    with TemporaryDirectory(prefix="verify_", dir=HERE) as working:
        output = Path(working) / "cli.json"
        check_cli = run_command([base + "check_circuit.py", "--circuit", str(CIRCUIT.relative_to(ROOT)),
                                 "--interlocks", str(INTERLOCKS.relative_to(ROOT)), "--out", str(output)])
        assert json.loads(output.read_text(encoding="utf-8"))["circuit"] == result["circuit"]
        check_cli["command"][-1] = "temporary output inside calc/T-2.9"
    pytest = run_command(["-m", "pytest", "-q", "-p", "no:cacheprovider", base + "test_interlocks.py"])
    script = run_command([base + "test_interlocks.py"])
    original_params = read(REFERENCE)
    original_params["cycle_model"]["lp"]["shell_L"] = 17.8
    assert original_params == read(PARAMS)
    assert all(criteria[tag] == "PASS" for tag in ("G-PFACE", "G-DOSE", "G-CYCLE"))
    assert result["gate_nominal"]["card_pass"]
    assert result["gate_nominal"]["method"] == "reference_model"
    assert result["circuit"]["mutations"]["rejected"] == result["circuit"]["mutations"]["expected"]
    ElementTree.parse(DESIGN / "T-2.9_circuit.svg")
    report = (ROOT / "report.md").read_text(encoding="utf-8")
    assert "?" not in report and "\ufffd" not in report
    nbytes = sum(item.stat().st_size for item in HERE.rglob("*") if item.is_file())
    assert nbytes <= 5_000_000
    expected_inputs = {
        "params": "calc/T-2.9/params/params.t29.yaml", "criteria": "ops/criteria/design_criteria.yaml",
        "output": "gates.t29.json", "entrypoint": "ops/gates/calc_gates.py",
    }
    record = {
        "task": "T-2.9", "task_status": result["status"], "blockers": result["blockers"],
        "gates": {"status_by_gate": criteria, "inputs": expected_inputs, "method": "reference_model",
                  "cycle_s": result["gate_nominal"]["cycle_s"], "rms_kW": result["gate_nominal"]["rms_kW"]},
        "check_circuit": check_cli, "pytest": pytest, "test_interlocks_as_script": script,
        "repeatability": repeats, "replays": replays,
        "gate_scan_regenerated_on_each_run": not reuse_scan,
        "params_only_change": "cycle_model.lp.shell_L 18.4 to 17.8",
        "report_utf8": "PASS", "report_line_count": len(report.splitlines()), "svg_xml": "PASS",
        "calc_T29_total_bytes": nbytes,
    }
    write_json(ROOT / "self_check.json", record)
    print(f"PASS: {result['circuit']['mutations']['rejected']} mutations; three files byte-identical")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-scan", action="store_true")
    verify(parser.parse_args().reuse_scan)
