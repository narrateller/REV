from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
import time
import unittest
from unittest.mock import patch

from ops import run_task
from ops.adapters import codex, echo
from ops.lib.bundle import REVIEW_DIFF_BYTES, review_package
from ops.lib.config import Card, RunnerError, read_backends, read_card
from ops.lib.gates import entry
from ops.lib.io import atomic_text, read_json
from ops.lib.process import ProcessResult, run_logged
from ops.lib.quota import detect_limit
from ops.lib.workspace import git, worktrees


PYTHON = "E:/Tools/Python313/python.exe"
FREECAD = "E:/Tools/FreeCAD-1.1/bin/freecadcmd.exe"
TOOL_PATHS = ["E:/Tools/Python313", "E:/Tools/Python313/Scripts"]


def load_runs(root, task):
    return sorted((root / "ops" / "runs" / task).iterdir())


class RunnerTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="rev-runner-test-")
        self.addCleanup(temporary.cleanup)
        location = Path(temporary.name)
        source = Path(worktrees(run_task.ROOT)[0]["worktree"])
        self.root = location / "control"
        git(location, "clone", "--local", "--shared", "--no-checkout", "--single-branch", "--branch", "main",
            source, self.root)
        # Use an existing small base tree for these Git workflow tests.
        initial = git(self.root, "rev-list", "--max-parents=0", "main").decode("ascii").splitlines()[0]
        git(self.root, "update-ref", "refs/heads/main", initial)
        self.ops = self.root / "ops"
        self.cards = self.ops / "tasks"
        self.cards.mkdir(parents=True)
        shutil.copyfile(run_task.ROOT / "AGENTS.md", self.root / "AGENTS.md")
        shutil.copyfile(run_task.ROOT / "ops" / "backends.yaml", self.ops / "backends.yaml")

    def card(self, extra=""):
        path = self.cards / "T-TEST.yaml"
        atomic_text(path, (
            "id: T-TEST\nstage: S0-bootstrap\nrole: TOOL-ORCH\nobjective: Test task\n"
            "allowed_paths: [report.md, metrics.json, self_check.json, ops/lib/**]\ntimebox_min: 1\n" + extra
        ))
        return path

    def test_dry_run_bundle_and_review(self):
        self.card("gates: [G-PFACE, G-COLL, G-FEA]\n")
        outcome = run_task.run_task(self.root, "T-TEST", dry_run=True)
        self.assertEqual(outcome.status, "PASS")
        self.assertEqual(len(worktrees(self.root)), 1)
        self.assertEqual(git(self.root, "branch", "--list", "task/T-TEST"), b"")
        expected = {"patch.diff", "report.md", "metrics.json", "self_check.json", "meta.json", "events.log"}
        self.assertTrue(expected <= {path.name for path in outcome.run_dir.iterdir()})
        patch_text = (outcome.run_dir / "patch.diff").read_text(encoding="utf-8")
        self.assertIn("report.md", patch_text)
        self.assertIn("self_check.json", patch_text)
        self.assertNotIn("TASK.md", patch_text)
        meta = read_json(outcome.run_dir / "meta.json")
        self.assertFalse(Path(meta["worktree"]).exists())
        self.assertEqual(meta["tokens_used"], 0)
        self.assertEqual(meta["status"], "PASS")
        self.assertEqual(set(meta["gate_statuses"].values()), {"NOT_AVAILABLE"})
        review = (self.ops / "review_queue" / "T-TEST.md").read_text(encoding="utf-8")
        self.assertIn("PASS", review)
        self.assertIn("Diffstat", review)
        self.assertIn("report.md", review)

    def test_probe_card_lives_in_runner_workspace(self):
        with patch.object(run_task, "ROOT", self.root), redirect_stdout(StringIO()) as output:
            self.assertEqual(run_task.main(["--probe", "--dry-run", "--backend", "bos"]), 0)
        self.assertTrue(output.getvalue().startswith("PASS "))
        run_dir, = load_runs(self.root, "T-PROBE")
        self.assertTrue((run_dir / "ops" / "tasks" / "T-PROBE.yaml").is_file())
        self.assertFalse((self.cards / "T-PROBE.yaml").exists())
        self.assertIn("Python", (run_dir / "report.md").read_text(encoding="utf-8"))

    def test_scope_failure_retries_on_same_worktree(self):
        self.card()
        calls = []

        def execute(backend, worktree, prompt, events, timeout_s):
            calls.append((worktree, prompt))
            task_text = (worktree / "TASK.md").read_text(encoding="utf-8")
            self.assertIn("Test task", task_text)
            self.assertIn(f"REV_PYTHON={PYTHON}", task_text)
            self.assertIn(f"REV_FREECADCMD={FREECAD}", task_text)
            self.assertIn(TOOL_PATHS[1], task_text)
            if len(calls) == 1:
                self.assertEqual(prompt, task_text)
                atomic_text(worktree / "rogue.txt", "out of scope\n")
                git(worktree, "add", "--", "rogue.txt")
                atomic_text(worktree / "ops" / "lib" / "nested" / "ok.py", "pass\n")
            else:
                self.assertIn("G-SCOPE FAIL", prompt)
                self.assertIn("rogue.txt", prompt)
                self.assertEqual(git(worktree, "diff", "--cached", "--name-only").strip(), b"rogue.txt")
                git(worktree, "restore", "--staged", "--", "rogue.txt")
                (worktree / "rogue.txt").unlink()
            return echo.execute(backend, worktree, prompt, events, timeout_s)

        with patch.object(codex, "execute", side_effect=execute):
            outcome = run_task.run_task(self.root, "T-TEST", max_rounds=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(outcome.status, "PASS")
        self.assertEqual(calls[0][0], calls[1][0])
        first, last = load_runs(self.root, "T-TEST")
        self.assertEqual(read_json(first / "meta.json")["status"], "RETRY")
        first_gate = read_json(first / "gates.json")["gates"][0]
        self.assertEqual(first_gate["status"], "FAIL")
        self.assertEqual(first_gate["details"]["unauthorized_paths"], ["rogue.txt"])
        self.assertEqual(read_json(last / "meta.json")["round"], 2)
        self.assertTrue((calls[0][0] / "TASK.md").is_file())

        with patch.object(codex, "execute", side_effect=echo.execute):
            repeated = run_task.run_task(self.root, "T-TEST", max_rounds=1)
        self.assertEqual(repeated.status, "PASS")
        self.assertEqual(len(worktrees(self.root)), 2)

    def test_retry_requires_a_new_report(self):
        self.card()
        original = echo.execute

        def execute(backend, worktree, prompt, events, timeout_s):
            rogue = worktree / "rogue.txt"
            if not rogue.exists():
                atomic_text(rogue, "out of scope\n")
                return original(backend, worktree, prompt, events, timeout_s)
            rogue.unlink()
            self.assertFalse((worktree / "report.md").exists())
            atomic_text(events, "no report this round\n")
            return ProcessResult(0)

        with patch.object(echo, "execute", side_effect=execute):
            outcome = run_task.run_task(self.root, "T-TEST", dry_run=True, max_rounds=2)
        first, second = load_runs(self.root, "T-TEST")
        self.assertEqual(outcome.status, "BLOCKED")
        self.assertFalse((second / "report.md").exists())
        self.assertEqual((second / "report.previous.md").read_bytes(), (first / "report.md").read_bytes())
        self.assertTrue(any(item.startswith("report.md:") for item in read_json(second / "meta.json")["defects"]))

    def test_scope_failure_at_last_round_blocks(self):
        self.card()

        def execute(backend, worktree, prompt, events, timeout_s):
            atomic_text(worktree / "rogue.txt", "out of scope\n")
            return original(backend, worktree, prompt, events, timeout_s)

        original = echo.execute
        with patch.object(echo, "execute", side_effect=execute):
            outcome = run_task.run_task(self.root, "T-TEST", dry_run=True, max_rounds=1)
        self.assertEqual(outcome.status, "BLOCKED")
        self.assertFalse((self.ops / "review_queue" / "T-TEST.md").exists())

    def test_profile_effort_none_refuses_before_worktree(self):
        self.card()
        config = self.ops / "backends.yaml"
        atomic_text(config, config.read_text(encoding="utf-8").replace("effort: high", "effort: none", 1))
        with patch.object(codex, "execute") as start:
            with self.assertRaisesRegex(RunnerError, "voh: reasoning effort"):
                run_task.run_task(self.root, "T-TEST")
            start.assert_not_called()
        self.assertEqual(len(worktrees(self.root)), 1)

    def test_quota_failover_and_wait_do_not_consume_a_round(self):
        self.card("backend: bos\n")
        aliases = []

        def exhausted(backend, worktree, prompt, events, timeout_s):
            aliases.append(backend.alias)
            atomic_text(events, "Error: You hit your usage limit. Try again at 06:11.\n")
            return ProcessResult(1)

        with patch.object(codex, "execute", side_effect=exhausted):
            outcome = run_task.run_task(self.root, "T-TEST", max_rounds=1)
        self.assertEqual(aliases, ["bos", "voh", "alm"])
        self.assertEqual(outcome.status, "WAIT")
        self.assertIsNotNone(outcome.wait_until)
        quota = read_json(self.ops / "state" / "quota.json")
        self.assertEqual(set(quota), {"bos", "voh", "alm"})
        self.assertEqual(outcome.wait_until, min(datetime.fromisoformat(item["exhausted_until"])
                                                  for item in quota.values()))
        attempts = load_runs(self.root, "T-TEST")
        self.assertEqual([read_json(path / "meta.json")["status"] for path in attempts],
                         ["QUOTA", "QUOTA", "QUOTA", "WAIT"])
        with patch.object(codex, "execute") as start:
            self.assertEqual(run_task.run_task(self.root, "T-TEST").status, "WAIT")
            start.assert_not_called()

    def test_gate_cli_contracts(self):
        self.card(
            "gates: [G-PFACE, G-CYCLE, G-COLL]\n"
            "gate_inputs: {params: design/example.yaml, model: cad/press.FCStd, roles: cad/roles.yaml, poses: cad/poses.yaml}\n"
        )
        for tool in ("scope_gate", "calc_gates", "geom_gates"):
            atomic_text(self.ops / "gates" / f"{tool}.py", "# CLI stub\n")
        invocations = []

        def fake_gate(argv, cwd, env, log, timeout_s):
            self.assertEqual(cwd, self.root)
            tool = Path(argv[1]).stem
            invocations.append(tool)
            if tool == "geom_gates":
                self.assertEqual(argv[0], FREECAD)
                options = json.loads(env["REV_GATE_ARGS"])
                self.assertEqual(set(options), {"model", "roles", "poses", "criteria", "gates", "out"})
                self.assertTrue(options["model"].endswith(str(Path("cad/press.FCStd"))))
                ids = options["gates"]
                output = Path(options["out"])
            else:
                self.assertEqual(argv[0], PYTHON)
                args = dict(zip(argv[2::2], argv[3::2]))
                output = args["--out"]
                if tool == "scope_gate":
                    self.assertEqual(set(args), {"--worktree", "--task", "--base", "--out", "--meta"})
                    self.assertEqual(args["--base"], "main")
                    self.assertTrue(args["--meta"].is_relative_to(args["--worktree"]))
                    self.assertEqual(args["--meta"].name, "meta.json")
                    self.assertEqual(read_json(args["--meta"])["reasoning_effort"], "high")
                    self.assertNotIn(args["--meta"].parent.name.encode(), git(
                        args["--worktree"], "ls-files", "--others", "--exclude-standard",
                    ))
                    self.assertFalse((args["--worktree"] / "TASK.md").exists())
                    ids = ["G-SCOPE"]
                else:
                    self.assertEqual(set(args), {"--params", "--criteria", "--gates", "--out"})
                    self.assertTrue(str(args["--params"]).endswith(str(Path("design/example.yaml"))))
                    ids = args["--gates"].split(",")
            status = "WARN" if tool == "geom_gates" else "PASS"
            atomic_text(output, json.dumps({
                "schema": "rev.gate_report/1", "tool": tool, "tool_version": "1.0",
                "input": "synthetic", "criteria_version": 1, "criteria_sha256": "a" * 64,
                "overall": status, "gates": [entry(gate, status, "test result") for gate in ids],
            }))
            return ProcessResult(0)

        with patch("ops.lib.gates.run_logged", side_effect=fake_gate):
            outcome = run_task.run_task(self.root, "T-TEST", dry_run=True)
        self.assertEqual(outcome.status, "PASS")
        self.assertEqual(invocations, ["scope_gate", "calc_gates", "geom_gates"])
        meta = read_json(outcome.run_dir / "meta.json")
        self.assertEqual(meta["gate_overall"], "WARN")
        self.assertEqual(meta["gate_statuses"], {
            "G-SCOPE": "PASS", "G-PFACE": "PASS", "G-CYCLE": "PASS", "G-COLL": "WARN",
        })

    def test_card_gates_without_inputs_are_not_launched(self):
        self.card("gates: [G-PFACE, G-COLL]\n")
        for tool in ("calc_gates", "geom_gates"):
            atomic_text(self.ops / "gates" / f"{tool}.py", "# CLI stub\n")
        with patch("ops.lib.gates.run_logged") as start:
            outcome = run_task.run_task(self.root, "T-TEST", dry_run=True)
        start.assert_not_called()
        self.assertEqual(outcome.status, "PASS")
        self.assertEqual(set(read_json(outcome.run_dir / "meta.json")["gate_statuses"].values()), {"NOT_AVAILABLE"})

    def test_geometry_exit_two_without_report_is_error(self):
        self.card("gates: [G-COLL]\ngate_inputs: {model: cad/model.FCStd, roles: cad/roles.yaml}\n")
        atomic_text(self.ops / "gates" / "geom_gates.py", "# CLI stub\n")
        config = self.ops / "backends.yaml"
        _, _, profiles = config.read_text(encoding="utf-8").partition("\nbackends:\n")
        atomic_text(config, f"backends:\n{profiles}")
        with patch.dict(os.environ, REV_FREECADCMD="freecad-from-env.exe"):
            with patch("ops.lib.gates.run_logged", return_value=ProcessResult(2)) as start:
                outcome = run_task.run_task(self.root, "T-TEST", dry_run=True, max_rounds=1)
        self.assertEqual(start.call_args.args[0][0], "freecad-from-env.exe")
        self.assertNotIn("poses", json.loads(start.call_args.args[2]["REV_GATE_ARGS"]))
        self.assertEqual(outcome.status, "BLOCKED")
        geom = read_json(outcome.run_dir / "gates.json")["gates"][1]
        self.assertEqual(geom["status"], "ERROR")
        self.assertIn("code 2", geom["details"]["reason"])

    def test_sandbox_lockout_waits_machine_wide_and_preserves_round(self):
        card = read_card(self.card("backend: bos\n"), "T-TEST")
        bos = read_backends(self.ops / "backends.yaml", card, "auto")[0]
        launched = []

        def launch(argv, cwd, env, log, timeout_s, *, stdin_bytes):
            launched.append(env["CODEX_HOME"])
            rogue = cwd / "rogue.txt"
            if len(launched) == 2:
                atomic_text(log, "ERROR: CreateProcessWithLogonW failed: 1909\nYou hit your usage limit\n")
                return ProcessResult(1)
            if len(launched) == 1:
                atomic_text(rogue, "out of scope\n")
            else:
                self.assertIn(b"G-SCOPE FAIL", stdin_bytes)
                self.assertIn(b"rogue.txt", stdin_bytes)
                rogue.unlink()
            return echo.execute(bos, cwd, "", log, timeout_s)

        local = self.root / "local-data"
        with (
            patch.dict(os.environ, LOCALAPPDATA=str(local)),
            patch.object(codex.shutil, "which", return_value="codex.exe"),
            patch.object(codex, "run_logged", side_effect=launch),
        ):
            before = datetime.now(timezone.utc)
            waiting = run_task.run_task(self.root, "T-TEST", max_rounds=2)
            self.assertEqual(waiting.status, "WAIT_SANDBOX")
            self.assertLessEqual(before + timedelta(minutes=11), waiting.wait_until)
            self.assertLessEqual(waiting.wait_until, datetime.now(timezone.utc) + timedelta(minutes=11))
            meta = read_json(waiting.run_dir / "meta.json")
            self.assertEqual(meta["round"], 2)
            self.assertEqual(meta["retry_at"], waiting.wait_until.isoformat())
            self.assertEqual(meta["returncode"], 1)
            lock = read_json(local / "rev-orch" / "codex.lock")
            self.assertEqual(lock["sandbox_retry_at"], waiting.wait_until.isoformat())
            self.assertFalse((self.ops / "state" / "quota.json").exists())
            other_profile = run_task.run_task(self.root, "T-TEST", preference="voh", max_rounds=2)
            self.assertEqual(other_profile.status, "WAIT_SANDBOX")
            self.assertEqual(other_profile.wait_until, waiting.wait_until)
            self.assertEqual(len(launched), 2)
            with patch.object(codex, "datetime", wraps=datetime) as clock:
                clock.now.return_value = waiting.wait_until
                resumed = run_task.run_task(self.root, "T-TEST", max_rounds=2)
        self.assertEqual(resumed.status, "PASS")
        self.assertEqual(read_json(resumed.run_dir / "meta.json")["round"], 2)
        self.assertEqual(len(launched), 3)

    def test_timeout_does_not_retry_or_detect_quota(self):
        self.card()

        def timed_out(backend, worktree, prompt, events, timeout_s):
            self.assertEqual(timeout_s, 60)
            atomic_text(events, "You hit your usage limit\n")
            return ProcessResult(1, timed_out=True)

        with patch.object(codex, "execute", side_effect=timed_out) as start:
            outcome = run_task.run_task(self.root, "T-TEST")
            self.assertEqual(start.call_count, 1)
        self.assertEqual(outcome.status, "TIMEOUT")
        self.assertEqual(read_json(outcome.run_dir / "meta.json")["status"], "TIMEOUT")
        self.assertFalse((self.ops / "state" / "quota.json").exists())

    def test_backend_selection_and_role_effort(self):
        card = read_card(self.card("backend: bos\n"), "T-TEST")
        profiles = read_backends(self.ops / "backends.yaml", card, "auto")
        self.assertEqual([(backend.alias, backend.effort) for backend in profiles],
                         [("bos", "high"), ("voh", "high"), ("alm", "high")])
        with patch("ops.adapters.codex.shutil.which", return_value="codex.exe"):
            argv, env = codex.command(profiles[0], self.root, {
                "LOCALAPPDATA": str(self.root), "OPENAI_BASE_URL": "unused", "PATH": "existing",
            })
        self.assertEqual(Path(env["CODEX_HOME"]), self.root / "rev-orch" / "codex" / "bos")
        self.assertNotIn("OPENAI_BASE_URL", env)
        self.assertEqual(argv[1:6], ["exec", "-C", str(self.root), "-m", profiles[0].model])
        self.assertIn("workspace-write", argv)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)
        self.assertEqual(argv[-2:], ["--", "-"])
        self.assertEqual(env["REV_PYTHON"], PYTHON)
        self.assertEqual(env["REV_FREECADCMD"], FREECAD)
        self.assertEqual(env["PATH"].split(os.pathsep), [*TOOL_PATHS, "existing"])


class AdapterTest(unittest.TestCase):
    def test_codex_quota_messages(self):
        msk = timezone(timedelta(hours=3))
        now = datetime(2026, 11, 24, 5, 0, tzinfo=msk)
        expected = datetime(2026, 11, 24, 3, 11, tzinfo=timezone.utc)
        for line in (
            "You've hit your usage limit. Try again at 06:11 on 24 Nov.",
            "ERROR: usage limit. Try again at Nov 24th, 2026 6:11 AM.",
            "\x1b[31mTry again at 06:11\x1b[0m",
            "Try again at 06:11 on 24 Nov +0300",
        ):
            with self.subTest(line=line):
                self.assertEqual(detect_limit(line, now), expected)
        self.assertEqual(detect_limit("usage limit", now), now + timedelta(hours=1))
        self.assertIsNone(detect_limit("ordinary Codex output", now))
        late = now.replace(hour=23)
        self.assertEqual(detect_limit("Try again at 06:11", late), expected + timedelta(days=1))
        end_of_year = datetime(2026, 12, 31, 23, 0, tzinfo=msk)
        self.assertEqual(detect_limit("Try again at 06:11 on 1 Jan", end_of_year),
                         datetime(2027, 1, 1, 3, 11, tzinfo=timezone.utc))

    def test_codex_header_and_token_footer(self):
        header = (
            "OpenAI Codex\r\nmodel: gpt-6.2-sol\r\nreasoning effort: high\r\n"
            "user\r\nmodel: other\r\ntokens used\r\n"
        )
        for footer, count in (
            ("12,345", 12345), ("24 105", 24105), ("24\u00a0734", 24734), ("135\u202f730", 135730),
            ("1 234 567", 1234567), ("0", 0),
        ):
            with self.subTest(footer=footer):
                self.assertEqual(codex.metadata(header + footer + "\r\n"), {
                    "model_observed": "gpt-6.2-sol", "reasoning_effort_observed": "high", "tokens_used": count,
                })
        self.assertIsNone(codex.metadata("no footer")["tokens_used"])

    def test_long_prompt_reaches_process_stdin(self):
        with TemporaryDirectory(prefix="rev-stdin-") as directory:
            root = Path(directory)
            prompt = "Карточка задачи\n" * 4000 + "ERROR: CreateProcessWithLogonW failed: 1909\n"
            payload = prompt.encode("utf-8")
            self.assertGreater(len(payload), 40 * 1024)
            command = [
                sys.executable, "-c",
                "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())", "-",
            ]
            with (
                patch.dict(os.environ, LOCALAPPDATA=str(root)),
                patch.object(codex, "command", return_value=(command, os.environ.copy())),
            ):
                result = codex.execute(None, root, prompt, root / "events.log", 10)
            self.assertEqual(result, ProcessResult(0))
            self.assertEqual((root / "events.log").read_bytes(), payload)

    def test_machine_lock_serializes_and_recovers_after_owner_exit(self):
        with TemporaryDirectory(prefix="rev-machine-lock-") as directory:
            root = Path(directory)
            ready = root / "ready"
            child_code = """
from pathlib import Path
import sys
import time
from unittest.mock import patch
from ops.adapters import codex

root = Path(sys.argv[1])
def launch(*args, **kwargs):
    (root / "ready").touch()
    time.sleep(30)

with patch.object(codex, "command", return_value=([], {})), patch.object(codex, "run_logged", launch):
    codex.execute("bos", root, "", root / "first.log", 30)
"""
            with patch.dict(os.environ, LOCALAPPDATA=str(root)):
                owner = subprocess.Popen([sys.executable, "-B", "-c", child_code, str(root)], cwd=run_task.ROOT)
                try:
                    deadline = time.monotonic() + 10
                    while not ready.exists() and owner.poll() is None and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertTrue(ready.is_file())
                    trying = Event()
                    entered = Event()

                    def launch(argv, cwd, env, log, timeout_s, *, stdin_bytes):
                        entered.set()
                        atomic_text(log, "ok\n")
                        return ProcessResult(0)

                    def second():
                        trying.set()
                        return codex.execute("voh", root, "", root / "second.log", 10)

                    with (
                        patch.object(codex, "command", return_value=([], {})),
                        patch.object(codex, "run_logged", launch),
                        ThreadPoolExecutor(max_workers=1) as pool,
                    ):
                        future = pool.submit(second)
                        try:
                            self.assertTrue(trying.wait(5))
                            self.assertFalse(entered.wait(0.3))
                        finally:
                            if owner.poll() is None:
                                owner.kill()
                            owner.wait(timeout=5)
                        self.assertEqual(future.result(timeout=5), ProcessResult(0))
                finally:
                    if owner.poll() is None:
                        owner.kill()
                        owner.wait(timeout=5)
            lock = read_json(root / "rev-orch" / "codex.lock")
            self.assertEqual(lock["pid"], os.getpid())
            self.assertIsNotNone(datetime.fromisoformat(lock["started_at"]).tzinfo)

    def test_review_diff_byte_limit(self):
        with TemporaryDirectory(prefix="rev-review-") as directory:
            root = Path(directory)
            run_dir = root / "run"
            run_dir.mkdir()
            card = Card("T-TEST", "", {"role": "TOOL-ORCH", "objective": "Test"}, (), 1, (), {})
            meta = {"dry_run": True, "backend": "bos", "model": "gpt-6.2-sol",
                    "reasoning_effort": "high", "round": 1}
            patch = run_dir / "patch.diff"
            patch.write_bytes(("+длинная строка\n" * 4000).encode("utf-8"))
            review = review_package(root, card, run_dir, meta, {}, [], "1 file changed")
            text = review.read_text(encoding="utf-8")
            excerpt = text.split("~~~diff\n", 1)[1].split("~~~", 1)[0]
            self.assertLessEqual(len(excerpt.encode("utf-8")), REVIEW_DIFF_BYTES)
            self.assertIn("Полный diff", text)
            self.assertGreater(patch.stat().st_size, REVIEW_DIFF_BYTES)

    def test_process_timeout_kills_child(self):
        with TemporaryDirectory(prefix="rev-runner-timeout-") as directory:
            root = Path(directory)
            child = "import time; from pathlib import Path; time.sleep(4); Path('alive').touch()"
            parent = (
                "import subprocess, sys, time; from pathlib import Path; "
                f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
                "Path('started').touch(); time.sleep(20)"
            )
            result = run_logged([sys.executable, "-c", parent], root, None, root / "events.log", 3)
            self.assertTrue((root / "started").is_file(), (root / "events.log").read_bytes())
            self.assertTrue(result.timed_out)
            time.sleep(2)
            self.assertFalse((root / "alive").exists())
