"""Shared JSON report contract for the Python command-line gates."""

import hashlib
import json
import math
from pathlib import Path
import re

import yaml


class InputError(ValueError):
    """Invalid gate input or unavailable data required to evaluate it."""


class GateLoader(yaml.SafeLoader):
    """Read scientific notation without a decimal point and reject duplicate keys."""

    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        if len(mapping) != len(node.value):
            raise InputError("Duplicate YAML key")
        return mapping


GateLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(r"^[+-]?[0-9]+(?:\.[0-9]*)?[eE][+-]?[0-9]+$"),
    list("+-0123456789"),
)


def load_yaml(data, source):
    try:
        document = yaml.load(data, Loader=GateLoader)
    except (yaml.YAMLError, InputError) as exc:
        raise InputError(f"{source}: {exc}") from exc
    if not isinstance(document, dict):
        raise InputError(f"{source}: expected a YAML mapping")
    return document


def read_criteria(data):
    document = load_yaml(data, "design_criteria.yaml")
    if type(document.get("version")) is not int or not isinstance(document.get("criteria"), dict):
        raise InputError("design_criteria.yaml: expected integer version and criteria mapping")
    return document


def result(gate_id, value, threshold, unit, criteria_ids, details, *, status=None):
    if status is None:
        status = "PASS" if all(details["checks"].values()) else "FAIL"
    return dict(id=gate_id, status=status, value=value, threshold=threshold,
                unit=unit, criteria_ids=list(criteria_ids), details=details)


def error_result(gate_id, criteria_ids, exc):
    return result(gate_id, None, None, "", criteria_ids, {"error": str(exc)}, status="ERROR")


def write_report(out, tool, source, criteria_version, criteria_data, gates):
    statuses = {gate["status"] for gate in gates}
    exit_code = 2 if "ERROR" in statuses else int("FAIL" in statuses)
    overall = "FAIL" if exit_code else "WARN" if statuses & {"WARN", "NOT_AVAILABLE"} else "PASS"
    report = {
        "schema": "rev.gate_report/1",
        "tool": tool,
        "tool_version": "1.1.0",
        "input": str(source),
        "criteria_version": criteria_version,
        "criteria_sha256": hashlib.sha256(criteria_data).hexdigest() if criteria_data is not None else "",
        "overall": overall,
        "gates": gates,
    }
    Path(out).write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                         encoding="utf-8", errors="backslashreplace", newline="\n")
    return exit_code


def finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False
