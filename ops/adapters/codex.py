from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil

from ops.lib.config import RunnerError
from ops.lib.io import atomic_text, file_lock
from ops.lib.process import run_logged
from ops.lib.quota import ANSI


PERCENT_VAR = re.compile(r"%([^%]+)%")
MODEL = re.compile(r"^model:[ \t]*(\S+)[ \t]*$", re.IGNORECASE | re.MULTILINE)
EFFORT = re.compile(r"^reasoning effort:[ \t]*([^\r\n]*)", re.IGNORECASE | re.MULTILINE)
TOKENS = re.compile(
    r"^tokens used[ \t]*:?[ \t\r\n]+([0-9]+(?:[, _\u00a0\u202f][0-9]{3})*)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
SANDBOX_LOCKOUT = re.compile(
    r"^[^`\n]*\bCreateProcessWithLogonW failed:[ \t]*1909\b", re.IGNORECASE | re.MULTILINE,
)
SANDBOX_COOLDOWN = timedelta(minutes=11)


class SandboxWait(Exception):
    def __init__(self, until, returncode=None):
        self.until = until
        self.returncode = returncode
        super().__init__(f"Windows Codex sandbox locked until {until.isoformat()}")


def command(backend, worktree, environ):
    def expand(match):
        name = match[1]
        value = environ.get(name)
        if not value:
            raise RunnerError(f"{backend.alias}: environment variable {name} is required for CODEX_HOME")
        return value

    home = Path(PERCENT_VAR.sub(expand, backend.home))
    if not home.is_absolute():
        raise RunnerError(f"{backend.alias}: CODEX_HOME must be absolute")
    env = backend.environment.apply(environ)
    cli = backend.cli + ".exe" if os.name == "nt" else backend.cli
    executable = shutil.which(cli, path=env.get("PATH"))
    if not executable:
        raise RunnerError(f"{backend.alias}: codex executable was not found on PATH")
    env["CODEX_HOME"] = str(home)
    env.pop("OPENAI_BASE_URL", None)
    argv = [
        executable, "exec", "-C", str(worktree), "-m", backend.model,
        "-c", f"model_reasoning_effort={backend.effort}",
        "-c", "model_provider=openai", "-c", "approval_policy=never",
        "--sandbox", "workspace-write", "--color", "never", "--", "-",
    ]
    return argv, env


def _sandbox_retry_at(lock):
    try:
        data = json.load(lock)
        until = datetime.fromisoformat(data["sandbox_retry_at"])
        return until if until.tzinfo is not None else None
    except (KeyError, TypeError, ValueError):
        return None


def _write_lock(lock, data):
    lock.seek(0)
    lock.write((json.dumps(data) + "\n").encode("utf-8"))
    lock.truncate()
    lock.flush()


def logged_output(events, *echoed_texts):
    output = ANSI.sub("", events.read_text(encoding="utf-8", errors="replace"))
    for echoed in echoed_texts:
        echoed = ANSI.sub("", echoed).replace("\r\n", "\n").strip()
        if echoed:
            output = output.replace(echoed, "")
    return output


def execute(backend, worktree, prompt, events, timeout_s):
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    if not local.is_absolute():
        raise RunnerError("an absolute LOCALAPPDATA is required for the Codex machine lock")
    # Lock ownership belongs to the OS. An exited PID leaves only a reusable record.
    with file_lock(local / "rev-orch" / "codex.lock", timeout_s=None) as lock:
        now = datetime.now(timezone.utc)
        until = _sandbox_retry_at(lock)
        if until is not None and until > now:
            waiting = SandboxWait(until)
            atomic_text(events, f"{waiting}\n")
            raise waiting
        argv, env = command(backend, worktree, os.environ)
        owner = {"pid": os.getpid(), "started_at": now.isoformat()}
        _write_lock(lock, owner)
        result = run_logged(argv, worktree, env, events, timeout_s, stdin_bytes=prompt.encode("utf-8"))
        if SANDBOX_LOCKOUT.search(logged_output(events, prompt)):
            until = datetime.now(timezone.utc) + SANDBOX_COOLDOWN
            _write_lock(lock, {**owner, "sandbox_retry_at": until.isoformat()})
            if not result.timed_out:
                raise SandboxWait(until, result.returncode)
        return result


def metadata(output):
    clean = ANSI.sub("", output).replace("\r\n", "\n")
    # Codex prints model and effort in the initial session header.
    header = re.split(r"^(?:user|assistant|exec|codex)\s*$", clean, maxsplit=1, flags=re.MULTILINE)[0]
    model = MODEL.search(header)
    effort = EFFORT.search(header)
    tokens = list(TOKENS.finditer(clean))
    return {
        "model_observed": model[1] if model else None,
        "reasoning_effort_observed": effort[1].strip().lower() if effort else None,
        "tokens_used": int(re.sub(r"\D", "", tokens[-1][1])) if tokens else None,
    }
