from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import tempfile
import time

from ops.lib.config import RunnerError


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_json(path, data):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def parse_json(text):
    def reject_constant(value):
        raise ValueError(f"invalid JSON constant {value}")

    return json.loads(text, parse_constant=reject_constant)


def read_json(path):
    return parse_json(path.read_text(encoding="utf-8-sig"))


@contextmanager
def file_lock(path, timeout_s=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        import msvcrt

        def lock(stream):
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)

        def unlock(stream):
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        def lock(stream):
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)

        def unlock(stream):
            fcntl.flock(stream, fcntl.LOCK_UN)

    deadline = None if timeout_s is None else time.monotonic() + timeout_s
    with open(
        path, "r+b", opener=lambda name, flags: os.open(name, flags | os.O_CREAT),
    ) as stream:
        while True:
            try:
                stream.seek(0)
                lock(stream)
                break
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if deadline is not None and time.monotonic() >= deadline:
                    raise RunnerError(f"could not acquire lock {path}") from error
                time.sleep(0.05)
        try:
            yield stream
        finally:
            stream.seek(0)
            unlock(stream)
