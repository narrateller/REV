from dataclasses import dataclass
from fnmatch import fnmatchcase
from math import isfinite
import os
from pathlib import PurePosixPath, PureWindowsPath
import re

import yaml


TASK_ID = re.compile(r"[A-Z]{1,3}-[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*")
GATE_ID = re.compile(r"G-[A-Z0-9]+(?:-[A-Z0-9]+)*")
BACKENDS = ("voh", "alm", "bos")
EFFORT_RANK = {"medium": 1, "high": 2, "xhigh": 3}
BUNDLE_FILES = ("report.md", "metrics.json", "self_check.json")


class RunnerError(Exception):
    pass


@dataclass(frozen=True)
class Card:
    id: str
    text: str
    data: dict
    allowed_paths: tuple[str, ...]
    time_limit_s: float
    gates: tuple[str, ...]
    gate_inputs: dict


@dataclass(frozen=True)
class ToolEnvironment:
    variables: tuple[tuple[str, str], ...] = ()
    path_prepend: tuple[str, ...] = ()

    def apply(self, environ):
        result = dict(environ)
        result.update(self.variables)
        if self.path_prepend:
            result["PATH"] = os.pathsep.join(filter(None, (*self.path_prepend, result.get("PATH"))))
        return result


@dataclass(frozen=True)
class Backend:
    alias: str
    cli: str
    home: str
    model: str
    effort: str
    environment: ToolEnvironment = ToolEnvironment()


def load_yaml(text, label):
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise RunnerError(f"{label}: {error}") from error
    if not isinstance(data, dict):
        raise RunnerError(f"{label}: expected a YAML mapping")
    return data


def repository_path(value):
    return (
        isinstance(value, str)
        and value
        and all(part not in {"", ".", ".."} for part in value.split("/"))
        and not PureWindowsPath(value).drive
        and not any(char in value for char in "\\:\0\n\r")
    )


def read_card(path, task_id):
    content = path.read_text(encoding="utf-8-sig")
    data = load_yaml(content, path)
    if data.get("id") != task_id or not TASK_ID.fullmatch(task_id):
        raise RunnerError(f"{path}: card id must be {task_id}")
    for field in ("role", "objective"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise RunnerError(f"{path}: {field} must be a nonempty string")
    paths = data.get("allowed_paths")
    if not isinstance(paths, list) or not paths or not all(map(repository_path, paths)):
        raise RunnerError(f"{path}: allowed_paths must contain repository-relative patterns")
    minutes = data.get("timebox_min")
    if type(minutes) not in {int, float} or not isfinite(minutes * 60) or minutes <= 0:
        raise RunnerError(f"{path}: timebox_min must be positive and finite")
    spec = data.get("spec")
    spec = spec if isinstance(spec, dict) else {}
    gates = data.get("gates", spec.get("gates", []))
    if isinstance(gates, dict):
        gates = list(gates)
    if not isinstance(gates, list) or not all(
        isinstance(gate, str) and GATE_ID.fullmatch(gate) for gate in gates
    ):
        raise RunnerError(f"{path}: gates must be a list or mapping of G-* ids")
    gate_inputs = data.get("gate_inputs", spec.get("gate_inputs", {}))
    if not isinstance(gate_inputs, dict) or any(
        key not in {"model", "roles", "poses", "params"} or not repository_path(value)
        for key, value in gate_inputs.items()
    ):
        raise RunnerError(f"{path}: gate_inputs must map model, roles, poses or params to repository-relative paths")
    return Card(task_id, content, data, tuple(paths), minutes * 60, tuple(dict.fromkeys(["G-SCOPE", *gates])), gate_inputs)


def effort(value, label):
    if not isinstance(value, str) or value not in EFFORT_RANK:
        raise RunnerError(f"{label}: reasoning effort must be medium, high or xhigh (got {value!r})")
    return value


def read_backends(path, card, preference):
    data = load_yaml(path.read_text(encoding="utf-8-sig"), path)
    environment = data.get("environment", {})
    tool_vars = {"REV_PYTHON", "REV_FREECADCMD"}
    if not isinstance(environment, dict) or environment.keys() - tool_vars - {"PATH_prepend"}:
        raise RunnerError("backends.yaml: invalid environment mapping")
    paths = environment.get("PATH_prepend", [])
    variables = tuple((key, value) for key, value in environment.items() if key in tool_vars)
    if not isinstance(paths, list) or any(
        not isinstance(value, str) or not value.strip() or any(c in value for c in "\0\r\n")
        for value in (*paths, *(value for _, value in variables))
    ):
        raise RunnerError("backends.yaml: tool paths must be nonempty strings")
    tools = ToolEnvironment(variables, tuple(paths))
    roles = data.get("roles")
    profiles = data.get("backends")
    if not isinstance(roles, dict) or not isinstance(profiles, dict):
        raise RunnerError("backends.yaml: roles and backends must be mappings")
    role = card.data["role"]
    policies = [
        policy for patterns, policy in roles.items()
        if isinstance(patterns, str) and any(fnmatchcase(role, pattern.strip()) for pattern in patterns.split(","))
    ]
    if len(policies) != 1 or not isinstance(policies[0], dict):
        raise RunnerError(f"{role}: expected exactly one role policy")
    policy = policies[0]
    order = policy.get("backends")
    if not isinstance(order, list) or not order or any(alias not in BACKENDS for alias in order) or len(set(order)) != len(order):
        raise RunnerError(f"{role}: invalid backend order")
    preferred = card.data.get("backend", "auto") if preference == "auto" else preference
    if preferred != "auto":
        if preferred not in order:
            raise RunnerError(f"{role}: backend {preferred!r} is outside the role policy")
        order = [preferred, *(alias for alias in order if alias != preferred)]
    role_effort = effort(policy.get("effort"), role)
    card_effort = effort(card.data.get("effort", role_effort), card.id)
    if EFFORT_RANK[card_effort] < EFFORT_RANK[role_effort]:
        raise RunnerError(f"{card.id}: effort is below the {role} policy minimum")
    result = []
    for alias in order:
        profile = profiles.get(alias)
        if not isinstance(profile, dict):
            raise RunnerError(f"{alias}: missing backend profile")
        effort(profile.get("effort"), alias)
        model, home = profile.get("model"), profile.get("home")
        if profile.get("cli") != "codex" or profile.get("family") != "openai" or model != "gpt-6.2-sol":
            raise RunnerError(f"{alias}: expected Codex / OpenAI / gpt-6.2-sol")
        if not isinstance(home, str) or not home.strip():
            raise RunnerError(f"{alias}: missing CODEX_HOME")
        # A role/card sets the effort for every backend, including failover.
        result.append(Backend(alias, profile["cli"], home, model, card_effort, tools))
    return result


def path_matches(parts, patterns):
    if not patterns:
        return not parts
    pattern, *remaining = patterns
    if pattern == "**":
        return any(path_matches(parts[index:], remaining) for index in range(len(parts) + 1))
    return bool(parts) and fnmatchcase(parts[0], pattern) and path_matches(parts[1:], remaining)


def in_scope(path, card):
    if PurePosixPath(path).name.casefold() == "auth.json":
        return False
    if path.casefold() in {"agents.md", "decisions.md", "plan.md", "claude.md", "task.md"}:
        return False
    if path.casefold().startswith("ops/criteria/"):
        return False
    patterns = card.allowed_paths
    if path.casefold().startswith("ops/gates/"):
        patterns = [pattern for pattern in patterns if pattern.startswith("ops/gates/")]
    return any(path_matches(path.split("/"), pattern.split("/")) for pattern in patterns)


PROBE = """\
id: T-PROBE
stage: S0-bootstrap
role: TOOL-ORCH
backend: bos
effort: high
objective: >
  Запусти python --version и запиши фактическую версию Python в report.md.
  Создай metrics.json с полем python_version и self_check.json с командой и её результатом.
allowed_paths: [report.md, metrics.json, self_check.json]
gates: [G-SCOPE]
timebox_min: 5
"""
