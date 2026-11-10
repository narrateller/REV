"""Registry and repository consistency checks. Does not approve engineering gates."""
from pathlib import Path
import argparse
import math
import sys

import yaml
from repo_support import DOMAINS, ID_RE, valid_tolerance

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = {"RAW", "ASSUMED", "CALCULATED", "VERIFIED", "LOCKED"}
ROLES = {"R1", "R2", "R3", "R4", "R5", "R6"}
FIELDS = {
    "revision", "name", "value", "unit", "tolerance", "uncertainty",
    "unknown_reason", "lifecycle", "validity", "stale_reason", "scope",
    "meaning", "provenance", "author", "verifier", "depends_on",
    "calculation", "evidence", "baseline_id", "history", "author_sessions",
}


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                             unique_mapping)


def validate(data, root, strict=False, check_git=False):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def file_exists(value):
        if not isinstance(value, str):
            return False
        path = (root / value).resolve()
        return path.is_relative_to(root.resolve()) and path.is_file()

    def finite(value):
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value))

    if not isinstance(data, dict) or not isinstance(data.get("domains"), dict):
        return ["Missing domains mapping"]
    require(data.get("schema_version") == "1.1", "Unsupported schema_version")
    require(data.get("mode") in ("TEMPLATE", "PROJECT"), "Invalid mode")
    require(data.get("units_policy") == "SI", "SI units policy required")
    require(all(d in data["domains"] for d in DOMAINS), "Missing standard domains")
    if data.get("mode") == "PROJECT":
        require(data.get("project_id") not in (None, "", "UNSET"), "Missing project_id")
    params = {}
    for domain, entries in data["domains"].items():
        if not isinstance(entries, dict):
            errors.append(f"{domain}: expected mapping")
            continue
        for key, entry in entries.items():
            require(key not in params, f"Duplicate parameter: {key}")
            if not isinstance(entry, dict):
                errors.append(f"{key}: expected mapping")
                continue
            params[key] = entry
    for key, entry in params.items():
        missing = FIELDS - entry.keys()
        if missing:
            errors.append(f"{key}: missing {sorted(missing)}")
            continue
        require(isinstance(key, str) and ID_RE.fullmatch(key), f"{key}: invalid parameter ID")
        if data.get("mode") == "PROJECT":
            require(not key.startswith("DEMO_") and entry["scope"] != "DEMO", f"{key}: DEMO forbidden in PROJECT")
        rev = entry["revision"]
        require(type(rev) is int and rev > 0, f"{key}: invalid revision")
        require(entry["lifecycle"] in LIFECYCLE, f"{key}: invalid lifecycle")
        require(entry["validity"] in {"CURRENT", "STALE"}, f"{key}: invalid validity")
        require(bool(entry["unit"]) and isinstance(entry["unit"], str), f"{key}: missing unit")
        require(bool(entry["scope"]), f"{key}: missing scope")
        if entry["value"] is None:
            require(bool(entry["unknown_reason"]), f"{key}: unknown without reason")
            require(entry["lifecycle"] == "RAW", f"{key}: null value outside RAW")
        else:
            require(finite(entry["value"]), f"{key}: value is not finite numeric")
            require(entry["unknown_reason"] is None, f"{key}: known value with unknown reason")
        if entry["validity"] == "STALE":
            require(bool(entry["stale_reason"]), f"{key}: STALE without reason")
        require(valid_tolerance(entry["tolerance"], entry["value"]), f"{key}: invalid tolerance")
        if strict:
            require(entry["validity"] == "CURRENT", f"{key}: STALE forbidden by --strict")
        author = entry["author"]
        require(isinstance(author, dict) and author.get("role") in ROLES
                and bool(author.get("session_id")), f"{key}: missing author")
        sessions = entry["author_sessions"]
        require(isinstance(sessions, list) and bool(sessions) and all(isinstance(x, str) and x for x in sessions), f"{key}: invalid author_sessions")
        if isinstance(author, dict) and isinstance(sessions, list):
            require(author.get("session_id") in sessions, f"{key}: author omitted from author_sessions")
        history = entry["history"]
        require(isinstance(history, list) and bool(history), f"{key}: missing history")
        if isinstance(history, list) and history:
            last = history[-1]
            require(isinstance(last, dict) and last.get("to") == entry["lifecycle"]
                    and last.get("revision") == rev, f"{key}: history mismatch")
        if not isinstance(entry["depends_on"], list):
            errors.append(f"{key}: depends_on must be a list")
            continue
        for dep in entry["depends_on"]:
            if not isinstance(dep, dict) or dep.get("id") not in params:
                errors.append(f"{key}: unknown dependency {dep}")
                continue
            upstream = params[dep["id"]]
            current = (dep.get("revision") == upstream.get("revision")
                       and upstream.get("validity") == "CURRENT")
            require(current or entry["validity"] == "STALE",
                    f"{key}: outdated dependency must invalidate result")
        calc = entry["calculation"]
        if entry["lifecycle"] == "CALCULATED":
            require(isinstance(calc, dict), f"{key}: missing calculation")
        if calc is not None:
            require(isinstance(calc, dict) and file_exists(calc.get("script")),
                    f"{key}: missing calculation script")
            require(isinstance(calc, dict) and bool(calc.get("expression"))
                    and bool(calc.get("command")) and file_exists(calc.get("output")),
                    f"{key}: missing calculation reproducibility data")
        require(isinstance(entry["evidence"], list), f"{key}: evidence must be list")
        if isinstance(entry["evidence"], list):
            for path in entry["evidence"]:
                require(file_exists(path), f"{key}: missing evidence {path}")
        if entry["lifecycle"] in {"VERIFIED", "LOCKED"}:
            verifier = entry["verifier"]
            require(isinstance(verifier, dict) and verifier.get("role") in ROLES
                    and bool(verifier.get("session_id")) and bool(verifier.get("review_id"))
                    and bool(verifier.get("scope")), f"{key}: missing verifier fields")
            if isinstance(verifier, dict) and isinstance(author, dict):
                require(verifier.get("session_id") != author.get("session_id"),
                        f"{key}: self-verification")
            require(bool(entry["evidence"]), f"{key}: verification without evidence")
        if entry["lifecycle"] == "LOCKED":
            require(bool(entry["baseline_id"]), f"{key}: LOCKED without baseline")

    visited, active = set(), set()

    def visit(key):
        if key in active:
            errors.append(f"Dependency cycle involving {key}")
            return
        if key in visited:
            return
        active.add(key)
        deps = params[key].get("depends_on", [])
        if isinstance(deps, list):
            for dep in deps:
                if isinstance(dep, dict) and dep.get("id") in params:
                    visit(dep["id"])
        active.remove(key)
        visited.add(key)

    for key in params:
        visit(key)
    if not errors:
        from repository_checks import check_repository
        errors.extend(check_repository(data, root, params, UniqueLoader, strict, check_git))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--check-git", action="store_true")
    args = parser.parse_args()
    try:
        data = yaml.load((args.root / "params/registry.yaml").read_text(encoding="utf-8"),
                         Loader=UniqueLoader)
        errors = validate(data, args.root, args.strict, args.check_git)
    except (ValueError, TypeError, KeyError, AttributeError, OSError, RecursionError, OverflowError, yaml.YAMLError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print("PASS: repository consistency checks; engineering acceptance NOT assessed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
