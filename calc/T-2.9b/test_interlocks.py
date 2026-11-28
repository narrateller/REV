"""One acceptance-checker test per new scheme-A mutation, plus the CLI exit code."""
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
from pathlib import Path

import pytest
import yaml

from check_circuit import CIRCUIT, INTERLOCKS, ROOT, HERE, check, read_yaml
from safety_checks import mutate, mutation_specs
from revision_checks import CASES
from revision import rapid_mode


CIRCUIT_DATA = read_yaml(CIRCUIT)
LOGIC = read_yaml(INTERLOCKS)
PARAMS = read_yaml(ROOT / LOGIC["reference"])
SOURCES = read_yaml(HERE / "sources.yaml")
SOURCES["catalogs"] = read_yaml(ROOT / "calc/T-1.6/sources.yaml")["catalogs"] | SOURCES["catalogs"]
NEW_CASES = [spec for spec in (mutation_specs(PARAMS) + CASES) if spec[-1]]


@pytest.mark.parametrize("spec", NEW_CASES, ids=[spec[0] for spec in NEW_CASES])
def test_each_new_interlock(spec):
    assert check(CIRCUIT_DATA, LOGIC, PARAMS, SOURCES)["passed"]
    model, logic = mutate(CIRCUIT_DATA, LOGIC, spec)
    assert not check(model, logic, PARAMS, SOURCES)["passed"], spec[0]


def test_tt_hysteresis():
    mode = "warmup"
    conditions = [
        (30.9, True, "warmup"), (31, True, "full_speed"), (30, True, "full_speed"),
        (29.99, True, "warmup"), (40, False, "inhibited"), (30.5, True, "warmup"),
    ]
    for temperature_C, valid, expected in conditions:
        mode = rapid_mode(mode, temperature_C, valid)
        assert mode == expected


def test_cli():
    with TemporaryDirectory(prefix="test_interlocks_", dir=HERE) as directory:
        directory = Path(directory)
        output = directory / "status.json"
        altered = directory / "bad.yaml"
        _, logic = mutate(CIRCUIT_DATA, LOGIC, NEW_CASES[0])
        altered.write_text(yaml.safe_dump(logic, allow_unicode=True), encoding="utf-8")
        for interlocks, exit_code in ((INTERLOCKS, 0), (altered, 1)):
            run = subprocess.run([
                sys.executable, str(HERE / "check_circuit.py"), "--circuit", str(CIRCUIT),
                "--interlocks", str(interlocks), "--out", str(output),
            ], check=False, capture_output=True, text=True, encoding="utf-8")
            assert run.returncode == exit_code, run.stdout + run.stderr
            result = json.loads(output.read_text(encoding="utf-8"))["circuit"]
            assert result["passed"] == (exit_code == 0)


if __name__ == "__main__":
    for case in NEW_CASES:
        test_each_new_interlock(case)
    test_tt_hysteresis()
    test_cli()
    print(f"PASS: {len(NEW_CASES)} scheme-A mutations and both CLI exit codes")
