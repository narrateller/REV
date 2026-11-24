from contextlib import contextmanager
import os
from pathlib import Path, PurePosixPath
import subprocess
from tempfile import TemporaryDirectory

from ops.lib.config import RunnerError
from ops.lib.io import atomic_text


BASE = "refs/heads/main"


def git(root, *args, env=None):
    result = subprocess.run(
        ["git", "-c", "core.longpaths=true", "-C", str(root), *map(str, args)], env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        raise RunnerError(f"git {args[0]} ({root}): {result.stderr.decode('utf-8', errors='replace').strip()}")
    return result.stdout


def base_commit(root):
    return git(root, "rev-parse", "--verify", BASE).decode("ascii").strip()


def worktrees(root):
    records = git(root, "worktree", "list", "--porcelain", "-z").decode("utf-8").split("\0\0")
    return [
        dict(field.partition(" ")[::2] for field in record.split("\0") if field)
        for record in records if record
    ]


@contextmanager
def worker(root, task_id, commit, dry_path=None):
    if dry_path is not None:
        git(root, "worktree", "add", "--detach", dry_path, commit)
        try:
            yield dry_path
        finally:
            git(root, "worktree", "remove", "--force", dry_path)
        return

    trees = worktrees(root)
    primary = Path(trees[0]["worktree"])
    worktree = primary.parent / "REV-wt" / task_id
    branch = f"task/{task_id}"
    if worktree.resolve() == root.resolve():
        raise RunnerError("run the runner from the control checkout, outside the executor worktree")
    existing = next((item for item in trees if Path(item["worktree"]).resolve() == worktree.resolve()), None)
    if existing is not None:
        if not worktree.is_dir() or existing.get("branch") != f"refs/heads/{branch}" or existing.get("locked") is not None:
            raise RunnerError(f"{worktree}: cannot reuse worktree, expected an unlocked {branch} checkout")
    elif worktree.exists() or worktree.is_symlink():
        raise RunnerError(f"{worktree}: path exists outside Git worktree registry")
    else:
        worktree.parent.mkdir(parents=True, exist_ok=True)
        refs = git(root, "for-each-ref", "--format=%(refname)", f"refs/heads/{branch}").decode("utf-8").splitlines()
        if f"refs/heads/{branch}" in refs:
            head = git(root, "rev-parse", f"refs/heads/{branch}").decode("ascii").strip()
            if head != commit:
                raise RunnerError(f"{branch}: branch is outside the current main baseline")
            git(root, "worktree", "add", worktree, branch)
        else:
            git(root, "worktree", "add", "-b", branch, worktree, "main")
    check_baseline(worktree, commit, branch=f"refs/heads/{branch}")
    yield worktree


def check_baseline(worktree, commit, branch=None):
    head = git(worktree, "rev-parse", "HEAD").decode("ascii").strip()
    if base_commit(worktree) != commit or head != commit:
        raise RunnerError(f"{worktree}: HEAD and main must both match the run baseline {commit}")
    if branch is not None and git(worktree, "rev-parse", "--symbolic-full-name", "HEAD").decode("utf-8").strip() != branch:
        raise RunnerError(f"{worktree}: executor checkout must stay on {branch}")


def changed_paths(worktree, commit="main"):
    changes = [
        git(worktree, "diff", "--name-only", "-z", "--no-renames", commit, "--"),
        git(worktree, "diff", "--cached", "--name-only", "-z", "--no-renames", commit, "--"),
        git(worktree, "ls-files", "--others", "--exclude-standard", "-z"),
    ]
    return sorted({path for change in changes for path in change.decode("utf-8").split("\0") if path})


def _task_bytes(worktree):
    path = worktree / "TASK.md"
    if path.is_symlink() or (path.exists() and not path.is_file()) or git(worktree, "ls-files", "--", "TASK.md"):
        raise RunnerError(f"{path}: expected a regular, untracked task file")
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def prepare_task(worktree, task_text, legacy_text):
    path = worktree / "TASK.md"
    previous = _task_bytes(worktree)
    if previous not in (None, task_text.encode("utf-8"), legacy_text.encode("utf-8")):
        raise RunnerError(f"{path}: existing TASK.md differs from the runner's task instructions")
    if previous != task_text.encode("utf-8"):
        atomic_text(path, task_text)


@contextmanager
def inspect_worker(worktree, task_text):
    path = worktree / "TASK.md"
    expected = task_text.encode("utf-8")
    try:
        actual = _task_bytes(worktree)
    except (OSError, RunnerError):
        actual = None
    if actual != expected:
        yield False
        return

    # The scope CLI sees only worker changes. The runner owns this exact file.
    path.unlink()
    try:
        yield True
    finally:
        with path.open("xb") as stream:
            stream.write(expected)


def snapshot_diff(worktree, commit, run_dir):
    # A private index includes untracked deliverables and preserves the worker's index.
    # New blobs are also local to the snapshot.
    objects = git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "objects").decode("utf-8").strip()
    with TemporaryDirectory(prefix="snapshot-", dir=run_dir) as scratch:
        private_objects = Path(scratch) / "objects"
        private_objects.mkdir()
        env = dict(
            os.environ, GIT_INDEX_FILE=str(Path(scratch) / "index"),
            GIT_OBJECT_DIRECTORY=str(private_objects), GIT_ALTERNATE_OBJECT_DIRECTORIES=objects,
        )
        git(worktree, "read-tree", commit, env=env)
        paths = (".", ":(exclude,icase)auth.json", ":(exclude,icase,glob)**/auth.json")
        git(worktree, "add", "-A", "--", *paths, env=env)
        diff_args = ("diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-color", commit, "--")
        patch = git(worktree, *diff_args[:2], "--binary", *diff_args[2:], env=env)
        diffstat = git(worktree, *diff_args[:2], "--stat", *diff_args[2:], env=env).decode("utf-8", errors="replace")
    (run_dir / "patch.diff").write_bytes(patch)
    return diffstat


def contained_path(worktree, relative):
    if PurePosixPath(relative).name.casefold() == "auth.json":
        raise RunnerError("auth.json cannot be used as a runner input")
    path = worktree / relative
    if not path.resolve().is_relative_to(worktree.resolve()):
        raise RunnerError(f"{relative}: path resolves outside the executor worktree")
    if path.resolve().name.casefold() == "auth.json":
        raise RunnerError("auth.json cannot be used as a runner input")
    return path
