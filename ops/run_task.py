import argparse
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import time
from uuid import uuid4

# Support the documented file entry point as well as python -m ops.run_task.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ops.adapters import codex, echo
from ops.lib.bundle import collect_files, review_package
from ops.lib.config import BACKENDS, PROBE, TASK_ID, RunnerError, read_backends, read_card
from ops.lib.gates import FAILURES, overall, run_gates
from ops.lib.io import atomic_text, file_lock, read_json, write_json
from ops.lib.quota import Quota, detect_limit
from ops.lib.workspace import (
    base_commit, changed_paths, check_baseline, inspect_worker, prepare_task, snapshot_diff, worker,
)


ROOT = Path(__file__).resolve().parents[1]
EXIT_CODES = {"PASS": 0, "BLOCKED": 1, "WAIT": 3, "TIMEOUT": 4, "WAIT_SANDBOX": 5}


@dataclass(frozen=True)
class Outcome:
    status: str
    run_dir: Path
    wait_until: datetime = None


def new_run(root, task_id):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = root / "ops" / "runs" / task_id / f"{stamp}-{uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def render_task(card, agents, env=None, path_prepend=()):
    tools = [
        f"`{key}={env[key]}`"
        for key in ("REV_PYTHON", "REV_FREECADCMD")
        if env and env.get(key)
    ]
    if path_prepend:
        paths = ", ".join(f"`{path}`" for path in path_prepend)
        tools.append(f"начало PATH — {paths}")
    tool_line = f"Рабочие инструменты в песочнице — {', '.join(tools)}.\n\n" if tools else ""
    return f"# TASK {card.id}\n\n~~~yaml\n{card.text.rstrip()}\n~~~\n\n{tool_line}{agents.rstrip()}\n"


def prompt_for(task_text, defects):
    if defects:
        return task_text + "\nИсправь дефекты предыдущего раунда.\n\n" + "\n".join(f"- {item}" for item in defects)[:8000]
    return task_text


def archive_report(worktree, run_dir):
    report = worktree / "report.md"
    if report.is_symlink():
        report.unlink()
    elif report.is_file():
        shutil.copyfile(report, run_dir / "report.previous.md")
        report.unlink()


def wait_outcome(run_dir, card, until):
    write_json(run_dir / "meta.json", {
        "task_id": card.id, "status": "WAIT", "exhausted_until": until.isoformat(),
    })
    return Outcome("WAIT", run_dir, until)


def _attempt(root, worktree, card_path, card, task_text, backend, run_dir, commit,
             round_number, max_rounds, dry_run, previous_defects, quota):
    events = run_dir / "events.log"
    meta_path = run_dir / "meta.json"
    meta = {
        "task_id": card.id, "round": round_number, "status": "RUNNING",
        "adapter": "echo" if dry_run else "codex", "dry_run": dry_run, "backend": backend.alias,
        "base_commit": commit, "worktree": str(worktree), "time_limit_s": card.time_limit_s,
        "requested_model": backend.model, "requested_reasoning_effort": backend.effort,
        "model": backend.model, "reasoning_effort": backend.effort, "tokens_used": None,
    }
    write_json(meta_path, meta)
    try:
        execute = echo.execute if dry_run else codex.execute
        start = time.monotonic()
        archive_report(worktree, run_dir)
        prompt = prompt_for(task_text, previous_defects)
        result = execute(backend, worktree, prompt, events, card.time_limit_s)
        meta["elapsed_s"] = round(time.monotonic() - start, 3)
        meta["returncode"] = result.returncode
        if result.timed_out:
            meta["status"] = "TIMEOUT"
            meta["defects"] = [f"executor exceeded {card.time_limit_s} s"]
        output = codex.logged_output(events, prompt, task_text)
        meta.update(codex.metadata(output))
        if meta["model_observed"] is not None:
            meta["model"] = meta["model_observed"]
        if meta["reasoning_effort_observed"] is not None:
            meta["reasoning_effort"] = meta["reasoning_effort_observed"]

        until = detect_limit(output) if result.returncode and not result.timed_out and not dry_run else None
        if until is not None:
            quota.exhaust(backend.alias, until)
            meta["status"] = "QUOTA"
            meta["exhausted_until"] = until.isoformat()
            return meta["status"], previous_defects

        check_baseline(worktree, commit, None if dry_run else f"refs/heads/task/{card.id}")
        with inspect_worker(worktree, task_text) as task_intact:
            changes = changed_paths(worktree, commit)
            diffstat = snapshot_diff(worktree, commit, run_dir)
            metrics, defects = collect_files(worktree, run_dir)
            if result.timed_out:
                meta["defects"].extend(defects)
                return meta["status"], meta["defects"]
            write_json(meta_path, meta)
            # The repository ignores *.tmp. Scope receives metadata inside the worker
            # without confusing a runner artifact with a worker change.
            with TemporaryDirectory(prefix="rev-scope-", suffix=".tmp", dir=worktree) as scratch:
                scope_meta = Path(scratch) / "meta.json"
                write_json(scope_meta, meta)
                gates = run_gates(
                    root, worktree, card_path, card, run_dir, changes, task_intact, meta, scope_meta,
                    backend.environment.apply(os.environ),
                )
        check_baseline(worktree, commit, None if dry_run else f"refs/heads/task/{card.id}")
        meta["gate_overall"] = overall(gates)
        meta["gate_statuses"] = {gate["id"]: gate["status"] for gate in gates}

        if result.returncode:
            defects.append(f"executor exited with code {result.returncode}; see {events.name}")
        for gate in gates:
            if gate["status"] in FAILURES:
                evidence = json.dumps(gate["details"], ensure_ascii=False)
                defects.append(f"{gate['id']} {gate['status']}: {evidence}")
        meta["defects"] = defects
        if defects:
            meta["status"] = "RETRY" if round_number < max_rounds else "BLOCKED"
        else:
            meta["status"] = "PASS"
            review = review_package(root, card, run_dir, meta, metrics, gates, diffstat)
            meta["review_package"] = str(review)
        return meta["status"], defects
    except codex.SandboxWait as error:
        meta["elapsed_s"] = round(time.monotonic() - start, 3)
        meta["status"] = "WAIT_SANDBOX"
        meta["retry_at"] = error.until.isoformat()
        meta["returncode"] = error.returncode
        raise
    except (OSError, ValueError, RunnerError) as error:
        if meta["status"] == "TIMEOUT":
            meta["defects"].append(f"could not collect partial bundle: {error}")
            return meta["status"], meta["defects"]
        meta["status"] = "ERROR"
        meta["error"] = str(error)
        raise
    finally:
        write_json(meta_path, meta)


def run_task(root, task_id, *, preference="auto", dry_run=False, max_rounds=3, probe=False):
    root = root.resolve()
    if not TASK_ID.fullmatch(task_id) or max_rounds < 1 or (probe and task_id != "T-PROBE"):
        raise RunnerError("invalid task id, probe id or round limit")
    ops = root / "ops"
    state = ops / "state"
    with file_lock(state / f"{task_id}.lock"):
        run_dir = new_run(root, task_id)
        card_path = ops / "tasks" / f"{task_id}.yaml"
        if probe:
            card_path = run_dir / "ops" / "tasks" / "T-PROBE.yaml"
            atomic_text(card_path, PROBE)
        card = read_card(card_path, task_id)
        backends = read_backends(ops / "backends.yaml", card, preference)
        quota = Quota(state / "quota.json")

        defects = []
        round_number = 1
        resume_path = state / f"{task_id}.sandbox.json"
        if not dry_run and resume_path.is_file():
            resume = read_json(resume_path)
            if (
                not isinstance(resume, dict)
                or type(resume.get("round")) is not int
                or resume["round"] < 1
                or not isinstance(resume.get("defects"), list)
                or not all(isinstance(defect, str) for defect in resume["defects"])
            ):
                raise RunnerError(f"{resume_path}: invalid sandbox retry state")
            round_number, defects = resume["round"], resume["defects"]
            if round_number > max_rounds:
                raise RunnerError(f"{task_id}: pending sandbox retry is for round {round_number}")
        worktree = None
        with ExitStack() as cleanup:
            while True:
                now = datetime.now(timezone.utc)
                backend, until = (backends[0], None) if dry_run else quota.available(backends, now)
                if backend is None:
                    return wait_outcome(run_dir, card, until)
                if worktree is None:
                    commit = base_commit(root)
                    dry_path = None
                    if dry_run:
                        scratch = cleanup.enter_context(TemporaryDirectory(prefix="rev-"))
                        dry_path = Path(scratch) / "wt"
                    worktree = cleanup.enter_context(worker(root, task_id, commit, dry_path=dry_path))
                    agents = (root / "AGENTS.md").read_text(encoding="utf-8-sig")
                    task_text = render_task(
                        card, agents, backend.environment.apply(os.environ), backend.environment.path_prepend,
                    )
                    prepare_task(worktree, task_text, render_task(card, agents))
                check_baseline(worktree, commit, None if dry_run else f"refs/heads/task/{card.id}")
                run_card = run_dir / "ops" / "tasks" / f"{card.id}.yaml"
                atomic_text(run_card, card.text)
                try:
                    status, defects = _attempt(
                        root, worktree, run_card, card, task_text, backend, run_dir, commit,
                        round_number, max_rounds, dry_run, defects, quota,
                    )
                except codex.SandboxWait as wait:
                    write_json(resume_path, {"round": round_number, "defects": defects})
                    return Outcome("WAIT_SANDBOX", run_dir, wait.until)
                if not dry_run and status != "QUOTA":
                    resume_path.unlink(missing_ok=True)
                if status in EXIT_CODES:
                    return Outcome(status, run_dir)
                if status == "RETRY":
                    round_number += 1
                run_dir = new_run(root, task_id)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run one REV task and collect its ResultBundle.")
    parser.add_argument("task_id", nargs="?")
    parser.add_argument("--backend", choices=("auto", *BACKENDS), default="auto")
    parser.add_argument("--dry-run", action="store_true", help="run the isolated echo adapter")
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--probe", action="store_true", help="generate and run T-PROBE")
    args = parser.parse_args(argv)
    if not args.task_id and not args.probe:
        parser.error("a task id or --probe is required")
    try:
        outcome = run_task(
            ROOT, args.task_id or "T-PROBE", preference=args.backend, dry_run=args.dry_run,
            max_rounds=args.max_rounds, probe=args.probe,
        )
    except (OSError, ValueError, RunnerError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 2
    wait = f" until {outcome.wait_until.isoformat()}" if outcome.wait_until else ""
    print(f"{outcome.status}{wait} {outcome.run_dir}")
    return EXIT_CODES[outcome.status]


if __name__ == "__main__":
    raise SystemExit(main())
