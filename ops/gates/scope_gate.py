"""Check a REV worktree against its task card, base tree and executor metadata."""

import argparse
from fnmatch import fnmatchcase
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

if __package__:
    from .gate_report import InputError, error_result, load_yaml, read_criteria, result, write_report
else:
    from gate_report import InputError, error_result, load_yaml, read_criteria, result, write_report


GATE_ID = "G-SCOPE"
CRITERIA_PATH = "ops/criteria/design_criteria.yaml"
PROTECTED = ("ops/criteria/", "ops/gates/")
CHECKOUT_NOISE = {"__pycache__", ".pytest_cache"}
ALWAYS_ALLOWED = {"TASK.md", "report.md", "metrics.json", "self_check.json"}
CARD_BLOCK = re.compile(
    r"^(?P<fence>```|~~~)ya?ml[^\S\n]*\n(?P<yaml>.*?)^(?P=fence)[^\S\n]*$",
    re.MULTILINE | re.DOTALL,
)


def git(worktree, *args):
    # Inspect the named worktree even if the caller has local Git overrides.
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    process = subprocess.run(["git", "-C", str(worktree), *args], env=env, capture_output=True, check=False)
    if process.returncode:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise InputError(f"git {args[0]} failed ({process.returncode}): {detail}")
    return process.stdout


def nul_records(data):
    return data.decode("utf-8", errors="surrogateescape").rstrip("\0").split("\0") if data else []


def read_card(path):
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".md":
        block = CARD_BLOCK.search(text)
        if not block:
            raise InputError(f"{path}: expected a fenced YAML task card")
        text = block["yaml"]
    card = load_yaml(text, path)
    for key in ("allowed_paths", "allow_protected"):
        patterns = card.get(key, [] if key == "allow_protected" else None)
        if not isinstance(patterns, list):
            raise InputError(f"{path}: {key} must be a list of repository-relative glob patterns")
        for pattern in patterns:
            if (not isinstance(pattern, str) or not pattern
                    or any(part in ("", ".", "..") for part in pattern.split("/"))
                    or "\\" in pattern or ":" in pattern):
                raise InputError(f"{path}: invalid {key} pattern {pattern!r}")
    return card


def worktree_changes(worktree, base_commit):
    diff_args = ("diff", "--name-only", "--no-renames", "-z")
    return {
        "committed": nul_records(git(worktree, *diff_args, f"{base_commit}...HEAD", "--")),
        "staged": nul_records(git(worktree, *diff_args, "--cached", "HEAD", "--")),
        "unstaged": nul_records(git(worktree, *diff_args, "--")),
        "untracked": nul_records(git(worktree, "ls-files", "--others", "--exclude-standard", "-z", "--")),
    }


def ignored_paths(worktree):
    records = git(worktree, "status", "--ignored", "--porcelain=v1", "--untracked-files=all", "--no-renames", "-z")
    return sorted(record[3:] for record in nul_records(records) if record.startswith("!! "))


def is_checkout_noise(name):
    return bool(CHECKOUT_NOISE.intersection(name.split("/"))) or name.endswith(".pyc")


def runner_metadata_path(worktree, meta_path):
    if meta_path is not None:
        path = Path(os.path.abspath(meta_path))
        directory = path.parent
        if path.name == "meta.json" and directory.parent == worktree and fnmatchcase(directory.name, "rev-scope-*.tmp"):
            return path.relative_to(worktree).as_posix()
    return None


def disk_sha256(worktree, name):
    path = worktree.joinpath(*name.split("/"))
    if any(ancestor.is_symlink() for ancestor in path.parents if ancestor.is_relative_to(worktree)):
        return None
    if path.is_symlink():
        target = path.readlink().as_posix()
        return hashlib.sha256(os.fsencode(target)).hexdigest()
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return None


def protected_hashes(worktree, base_commit, paths, needs_protection):
    baseline = {}
    for entry in nul_records(git(worktree, "ls-tree", "-r", "-z", base_commit, "--", *PROTECTED)):
        header, name = entry.split("\t", 1)
        _, kind, object_id = header.split()
        if kind != "blob" and needs_protection(name):
            raise InputError(f"Protected path {name} is a Git {kind}, expected a file")
        baseline[name] = object_id
    hashes = []
    for name in sorted((baseline.keys() | paths)):
        if not needs_protection(name):
            continue
        object_id = baseline.get(name)
        base_sha256 = hashlib.sha256(git(worktree, "cat-file", "blob", object_id)).hexdigest() if object_id else None
        hashes.append({"path": name, "base_sha256": base_sha256, "worktree_sha256": disk_sha256(worktree, name)})
    return hashes


def reasoning_effort(meta_path):
    if meta_path is None:
        return None
    try:
        document = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise InputError(f"{meta_path}: {exc}") from exc
    if not isinstance(document, dict):
        raise InputError(f"{meta_path}: expected a JSON object")
    effort = document.get("reasoning_effort")
    return effort.strip().lower() if isinstance(effort, str) else ""


def matches(parts, pattern):
    if not pattern:
        return not parts
    head, *tail = pattern
    if head == "**":
        return any(matches(parts[index:], tail) for index in range(len(parts) + 1))
    return bool(parts) and fnmatchcase(parts[0], head) and matches(parts[1:], tail)


def evaluate_scope(worktree, card, base_commit, merge_base, meta_path):
    patterns = card["allowed_paths"]
    segments = [pattern.split("/") for pattern in patterns]
    exceptions = card.get("allow_protected", [])
    exception_segments = [pattern.split("/") for pattern in exceptions]

    def allowed(name):
        return name in ALWAYS_ALLOWED or any(matches(name.split("/"), pattern) for pattern in segments)

    def needs_protection(name):
        parts = name.split("/")
        if parts[:2] == ["ops", "criteria"]:
            return True
        return parts[:2] == ["ops", "gates"] and not any(matches(parts, pattern) for pattern in exception_segments)

    changes = worktree_changes(worktree, base_commit)
    paths = {name for names in changes.values() for name in names}
    ignored = ignored_paths(worktree)
    runner_metadata = runner_metadata_path(worktree, meta_path)
    ignored_non_noise = {name for name in ignored if name != runner_metadata and not is_checkout_noise(name)}
    ignored_outside_allowed = sorted(name for name in ignored_non_noise if not allowed(name))
    tracked = set(nul_records(git(worktree, "ls-files", "-z", "--", *PROTECTED)))
    forbidden_paths = sorted(name for name in paths if not allowed(name))
    hashes = protected_hashes(worktree, merge_base, paths | tracked | ignored_non_noise, needs_protection)
    hash_mismatches = [item["path"] for item in hashes if item["base_sha256"] != item["worktree_sha256"]]
    # An index or HEAD change may already have been reverted on disk.
    protected_changes = sorted(set(hash_mismatches) | {name for name in paths if needs_protection(name)})
    effort = reasoning_effort(meta_path)
    checks = {"paths_allowed": not forbidden_paths, "protected_hashes_match": not protected_changes}
    if effort is not None:
        checks["reasoning_effort_allowed"] = effort not in {"", "none", "low"}
    warnings = []
    if effort is None:
        warnings.append("Executor metadata is missing")
    if ignored_outside_allowed:
        warnings.append("Ignored files outside allowed_paths")
    status = "FAIL" if not all(checks.values()) else "WARN" if warnings else "PASS"
    return result(GATE_ID, len(set(forbidden_paths) | set(protected_changes)), 0, "paths", (), {
        "checks": checks, "task_id": card.get("id"), "base_commit": base_commit, "merge_base_commit": merge_base,
        "allowed_paths": patterns, "allow_protected": exceptions, "always_allowed_paths": sorted(ALWAYS_ALLOWED),
        "changes": changes, "forbidden_paths": forbidden_paths, "protected_hashes": hashes,
        "ignored_paths": ignored, "ignored_outside_allowed": ignored_outside_allowed, "warnings": warnings,
        "protected_changes": protected_changes, "protected_hash_mismatches": hash_mismatches, "reasoning_effort": effort,
        "meta": str(meta_path) if meta_path else None,
        "reasoning_effort_checked": effort is not None,
    }, status=status)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", required=True, type=Path)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--base", default="main")
    parser.add_argument("--meta", type=Path, help="Executor meta.json. Defaults to <worktree>/meta.json if present.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    criteria_data, criteria_version = None, 0
    try:
        worktree = args.worktree.resolve(strict=True)
        if git(worktree, "rev-parse", "--show-prefix").strip():
            raise InputError("--worktree must be the Git worktree root")
        base = git(worktree, "rev-parse", "--verify", "--end-of-options", f"{args.base}^{{commit}}").decode().strip()
        merge_base = git(worktree, "merge-base", base, "HEAD").decode().strip()
        criteria_data = git(worktree, "cat-file", "blob", f"{merge_base}:{CRITERIA_PATH}")
        criteria_version = read_criteria(criteria_data)["version"]
        card = read_card(args.task)
        meta_path = args.meta
        if meta_path is None and (worktree / "meta.json").exists():
            meta_path = worktree / "meta.json"
        gate = evaluate_scope(worktree, card, base, merge_base, meta_path)
    except (OSError, ValueError, RecursionError) as exc:
        gate = error_result(GATE_ID, (), exc)
    try:
        return write_report(args.out, "scope_gate", args.worktree, criteria_version, criteria_data, [gate])
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
