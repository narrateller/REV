from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import NamedTemporaryFile


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    timed_out: bool = False


@contextmanager
def windows_job():
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateJobObject.restype = wintypes.BOOL
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", ctypes.c_ulonglong * 6),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())

    def attach(pid):
        process_set_quota = 0x0100
        process_terminate = 0x0001
        process = kernel.OpenProcess(process_set_quota | process_terminate, False, pid)
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not kernel.AssignProcessToJobObject(job, process):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(process)

    def terminate():
        if not kernel.TerminateJobObject(job, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    try:
        # Closing the last job handle also kills descendants if the runner exits abruptly.
        job_object_extended_limit_information = 9
        job_object_limit_kill_on_job_close = 0x2000
        limits = ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = job_object_limit_kill_on_job_close
        if not kernel.SetInformationJobObject(
            job, job_object_extended_limit_information, ctypes.byref(limits), ctypes.sizeof(limits),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        yield attach, terminate
    finally:
        kernel.CloseHandle(job)


def wait_process(process, terminate, timeout_s):
    try:
        return ProcessResult(process.wait(timeout=timeout_s))
    except subprocess.TimeoutExpired:
        terminate()
        return ProcessResult(process.wait(), timed_out=True)
    except BaseException:
        terminate()
        process.wait()
        raise


def run_logged(argv, cwd, env, output, timeout_s, *, stdin_bytes=None):
    # A file supplies stdin without a pipe write that could block past the process timeout.
    with output.open("wb") as log, NamedTemporaryFile(dir=output.parent, delete_on_close=False) as payload:
        if stdin_bytes is not None:
            payload.write(stdin_bytes)
        payload.seek(0)
        options = dict(cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        if os.name == "nt":
            # Wait for enrollment in the job before the command can spawn children.
            launcher = [sys.executable, str(Path(__file__).resolve()), payload.name, *map(os.fsdecode, argv)]
            with windows_job() as (attach, terminate):
                process = subprocess.Popen(launcher, stdin=subprocess.PIPE, **options)
                try:
                    attach(process.pid)
                    with process.stdin as start:
                        start.write(b"1")
                except BaseException:
                    process.stdin.close()
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                    raise
                return wait_process(process, terminate, timeout_s)

        process = subprocess.Popen(argv, stdin=payload, start_new_session=True, **options)

        def terminate():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        return wait_process(process, terminate, timeout_s)


if __name__ == "__main__":
    if sys.stdin.buffer.read(1) != b"1":
        raise SystemExit(2)
    with open(sys.argv[1], "rb") as prompt:
        raise SystemExit(subprocess.call(sys.argv[2:], stdin=prompt))
