"""Constitutive inputs retained from T-2.2g/prior/load.py."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read_yaml(relative_path):
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def read_geometry():
    spec = spec_from_file_location("t12_geometry", ROOT / "calc/T-1.2/geometry.py")
    module = module_from_spec(spec)
    previous_setting = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous_setting
    return module


def accepted_load():
    return json.loads((HERE / "round1_load.json").read_text(encoding="utf-8"))


