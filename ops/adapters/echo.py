from platform import python_version

from ops.lib.io import atomic_text, write_json
from ops.lib.process import ProcessResult


def execute(backend, worktree, prompt, events, timeout_s):
    version = python_version()
    atomic_text(worktree / "report.md", f"# Echo dry run\n\nPython {version}\n")
    write_json(worktree / "metrics.json", {"python_version": version})
    write_json(worktree / "self_check.json", {"adapter": "echo", "python_version": "PASS"})
    atomic_text(events, f"model: {backend.model}\nreasoning effort: {backend.effort}\ntokens used\n0\n")
    return ProcessResult(0)
