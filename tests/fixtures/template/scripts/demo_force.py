"""Synthetic example; no engineering acceptance is implied."""
from decimal import Decimal
import argparse
from pathlib import Path
import hashlib
import json
import platform

import yaml
from repo_support import parameter_ref, sha256

ROOT = Path(__file__).resolve().parents[1]


def calculate():
    source = ROOT / "params/registry.yaml"
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    params = {key: value for domain in data["domains"].values()
              for key, value in domain.items()}
    required = {
        "DEMO_CONTACT_STRESS": "Pa",
        "DEMO_CONTACT_AREA": "m^2",
        "DEMO_REQUIRED_FORCE": "N",
    }
    for key, unit in required.items():
        entry = params[key]
        if entry["unit"] != unit or entry["scope"] != "DEMO":
            raise ValueError(f"Unexpected unit or scope: {key}")
        if entry["validity"] != "CURRENT" or entry["value"] is None:
            raise ValueError(f"Unavailable input: {key}")
    stress = params["DEMO_CONTACT_STRESS"]
    area = params["DEMO_CONTACT_AREA"]
    force = Decimal(str(stress["value"])) * Decimal(str(area["value"]))
    expected = Decimal(str(params["DEMO_REQUIRED_FORCE"]["value"]))
    if force != expected:
        raise ValueError("Registry output differs from recomputed force")
    inputs = []
    for key in ("DEMO_CONTACT_STRESS", "DEMO_CONTACT_AREA"):
        inputs.append(dict(parameter_ref(key, params[key]), value=params[key]['value'], unit=params[key]['unit']))
    outputs = [dict(parameter_ref('DEMO_REQUIRED_FORCE', params['DEMO_REQUIRED_FORCE']), value=float(force), unit='N')]
    snapshot = 'evidence/snapshots/' + sha256(source) + '.yaml'
    return {
        "schema_version": "1.1",
        "scope": "DEMO_ARITHMETIC_ONLY",
        "formula": "F = sigma * A",
        "inputs": inputs,
        "outputs": outputs,
        "registry_snapshot": snapshot,
        "registry_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "code_files": [{"path": p, "sha256": sha256(ROOT / p)} for p in params['DEMO_REQUIRED_FORCE']['calculation']['code_files']],
        "artifacts": [],
        "environment": {"python": platform.python_version(), "pyyaml": yaml.__version__},
        "independent_review": False,
        "physical_validation": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Save evidence and an immutable registry snapshot')
    args = parser.parse_args()
    result = calculate()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.write:
        snapshot = ROOT / result['registry_snapshot']
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        source_bytes = (ROOT / 'params/registry.yaml').read_bytes()
        if snapshot.exists() and snapshot.read_bytes() != source_bytes:
            raise ValueError('Refusing to overwrite different snapshot bytes')
        snapshot.write_bytes(source_bytes)
        # Byte output is deterministic on Windows and POSIX; no newline translation.
        (ROOT / 'evidence/demo_force.json').write_bytes(payload.encode('utf-8'))
    print(payload, end='')
