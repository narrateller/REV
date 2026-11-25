"""Regression tests for the runner's temporary G-SCOPE metadata."""

import pytest

from ops.gates import scope_gate as scope


@pytest.mark.parametrize("fence", ["~~~", "```"])
def test_scope_reads_markdown_card(tmp_path, fence):
    task = tmp_path / "TASK.md"
    task.write_text(f"# Task\n\n{fence}yaml\nid: T-0.2a\nallowed_paths: []\n{fence}\n", encoding="utf-8")
    assert scope.read_card(task)["id"] == "T-0.2a"


def test_scope_exempts_only_ignored_metadata_passed_by_runner(tmp_path, monkeypatch):
    directory = tmp_path / "rev-scope-dzk5.tmp"
    directory.mkdir()
    meta = directory / "meta.json"
    meta.write_text('{"reasoning_effort": "high"}', encoding="utf-8")
    metadata_name = "rev-scope-dzk5.tmp/meta.json"
    other_files = ["rev-scope-dzk5.tmp/other.json", "rev-scope-other.tmp/meta.json"]
    ignored = [metadata_name]

    def git_stub(_, command, *args):
        if command == "status":
            return b"".join(f"!! {name}\0".encode() for name in ignored)
        if command == "ls-files" and "--others" in args and metadata_name not in ignored:
            return f"{metadata_name}\0".encode()
        return b""

    monkeypatch.setattr(scope, "git", git_stub)
    card = {"allowed_paths": []}
    gate = scope.evaluate_scope(tmp_path, card, "base", "fork", meta)
    assert gate["status"] == "PASS"
    assert gate["details"]["ignored_paths"] == [metadata_name]
    assert gate["details"]["ignored_outside_allowed"] == []

    ignored.extend(other_files)
    gate = scope.evaluate_scope(tmp_path, card, "base", "fork", meta)
    assert gate["status"] == "WARN"
    assert gate["details"]["ignored_outside_allowed"] == other_files

    ignored.remove(metadata_name)
    gate = scope.evaluate_scope(tmp_path, card, "base", "fork", meta)
    assert gate["status"] == "FAIL"
    assert gate["details"]["forbidden_paths"] == [metadata_name]
