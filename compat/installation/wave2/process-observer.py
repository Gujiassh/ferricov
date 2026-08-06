#!/usr/bin/env python3
"""Live-process observer for installation wave-2 Oracle captures.

Launches the subject under a clean environment with ptrace exec-stop so that
executable path, argv (cmdline), and cwd are read from /proc after the real
exec. The executable identity is attested by hashing the open /proc/<pid>/exe
file descriptor at the post-exec stop (before PTRACE_CONT), never by reopening
a pathname after the process exits.

On any ptrace/option/continue/observation failure the process group and
tracee are SIGKILL'd and reaped; no sentinel executable digests are emitted.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

libc = ctypes.CDLL(None, use_errno=True)

PTRACE_TRACEME = 0
PTRACE_CONT = 7
PTRACE_SETOPTIONS = 0x4200
PTRACE_O_TRACEEXEC = 0x00000010
PTRACE_EVENT_EXEC = 4

# Optional fault-injection points for unit tests (unset in production).
# Values: "setoptions", "cont_initial", "cont_post_exec", "hash_open", "hash_read"
FAULT_ENV = "FERRICOV_WAVE2_OBSERVER_FAULT"


def _errno() -> int:
    return ctypes.get_errno()


def ptrace(request: int, pid: int = 0, addr=None, data=None) -> int:
    fault = os.environ.get(FAULT_ENV, "")
    if fault == "setoptions" and request == PTRACE_SETOPTIONS:
        ctypes.set_errno(1)  # EPERM
        return -1
    if fault == "cont_initial" and request == PTRACE_CONT:
        # Only the first CONT after attach.
        if not getattr(ptrace, "_cont_seen", False):
            ptrace._cont_seen = True  # type: ignore[attr-defined]
            ctypes.set_errno(1)
            return -1
    if fault == "cont_post_exec" and request == PTRACE_CONT:
        if getattr(ptrace, "_post_exec_ready", False):  # type: ignore[attr-defined]
            ptrace._post_exec_ready = False  # type: ignore[attr-defined]
            ctypes.set_errno(1)
            return -1
    return libc.ptrace(request, pid, addr, data)


def read_cmdline(pid: int) -> list[str]:
    raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    parts = [p.decode("utf-8", errors="surrogateescape") for p in raw.split(b"\0") if p]
    return parts


def resolve_exe_path(pid: int) -> str:
    return os.readlink(f"/proc/{pid}/exe")


def resolve_cwd(pid: int) -> str:
    return os.readlink(f"/proc/{pid}/cwd")


def hash_open_exe_fd(pid: int) -> str:
    """Open /proc/<pid>/exe and hash the open FD content before continue.

    Returns sha256_hex of the executable bytes. Device/inode numbers are
    intentionally not returned or persisted: they are container-local and
    break cross-clone strict replay. Never falls back to a sentinel digest.
    """
    fault = os.environ.get(FAULT_ENV, "")
    if fault == "hash_open":
        raise PermissionError("injected hash_open fault")
    path = f"/proc/{pid}/exe"
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        # fstat is used only to prove the FD is open; st_dev/st_ino are not persisted.
        os.fstat(fd)
        if fault == "hash_read":
            raise OSError(13, "injected hash_read fault")
        h = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
        return h.hexdigest()
    finally:
        os.close(fd)


def parse_env_file(path: Path | None) -> dict[str, str]:
    env: dict[str, str] = {}
    if path is None or not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def kill_and_reap(pid: int, *, grace: float = 0.5) -> None:
    """Best-effort terminate process group and direct pid, then reap."""
    if pid <= 0:
        return
    for sig in (signal.SIGKILL,):
        try:
            os.killpg(pid, sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    deadline = time.monotonic() + max(grace, 0.05)
    while time.monotonic() < deadline:
        try:
            wpid, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return
        if wpid == pid:
            return
        time.sleep(0.01)
    # Final blocking wait with short alarm-like loop.
    for _ in range(50):
        try:
            wpid, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return
        if wpid == pid:
            return
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        time.sleep(0.02)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--observed-argv", required=True)
    parser.add_argument("--observed-children", required=True)
    parser.add_argument("--meta", required=True)
    parser.add_argument("--observed-env", required=True)
    parser.add_argument("--env-file", default="")
    parser.add_argument(
        "--qualification",
        choices=["", "signal", "timeout"],
        default="",
        help="runner qualification mode: force SIGTERM or force deadline",
    )
    parser.add_argument("subject_argv", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    subject = list(args.subject_argv)
    if subject and subject[0] == "--":
        subject = subject[1:]
    if not subject:
        print("subject argv required after --", file=sys.stderr)
        return 2

    workdir = Path(args.workdir)
    if not workdir.is_absolute() or ".." in workdir.parts:
        print(f"invalid workdir: {workdir}", file=sys.stderr)
        return 2

    env = parse_env_file(Path(args.env_file) if args.env_file else None)
    if not env:
        print("empty clean environment", file=sys.stderr)
        return 2

    env_lines = [f"{k}={env[k]}" for k in sorted(env)]
    Path(args.observed_env).write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    stdout_path = Path(args.stdout)
    stderr_path = Path(args.stderr)
    stdout_fd = os.open(str(stdout_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    stderr_fd = os.open(str(stderr_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

    # Authoritative declared timeout; timeout qualification still uses this value
    # (driver must pass the actual deadline, typically 1s for the timeout probe).
    timeout_sec = max(1, int(args.timeout_seconds))

    started = time.monotonic()
    deadline = started + timeout_sec
    term_sent = False
    kill_sent = False
    kill_deadline = None

    child_pid = -1
    observed_exe = ""
    observed_cwd = ""
    observed_argv: list[str] = []
    exec_sha = ""
    exec_seen = False
    exit_status = None
    sig_num = None
    timed_out = False
    wait_code = None
    observer_rc = 2

    try:
        child_pid = os.fork()
        if child_pid == 0:
            try:
                # Own process group so parent can killpg on failure.
                os.setsid()
                os.chdir(str(workdir))
                os.dup2(stdout_fd, 1)
                os.dup2(stderr_fd, 2)
                os.close(stdout_fd)
                os.close(stderr_fd)
                try:
                    maxfd = os.sysconf("SC_OPEN_MAX")
                except (AttributeError, ValueError, OSError):
                    maxfd = 256
                for fd in range(3, min(maxfd, 1024)):
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                if ptrace(PTRACE_TRACEME, 0, None, None) != 0:
                    os._exit(127)
                os.kill(os.getpid(), signal.SIGSTOP)
                os.execvpe(subject[0], subject, env)
            except Exception:
                os._exit(127)

        os.close(stdout_fd)
        os.close(stderr_fd)
        stdout_fd = -1
        stderr_fd = -1

        _, status = os.waitpid(child_pid, 0)
        if not os.WIFSTOPPED(status):
            print("child did not stop for attach", file=sys.stderr)
            observer_rc = 2
            return 2

        if ptrace(PTRACE_SETOPTIONS, child_pid, None, PTRACE_O_TRACEEXEC) != 0:
            print(f"PTRACE_SETOPTIONS failed errno={_errno()}", file=sys.stderr)
            observer_rc = 2
            return 2
        if ptrace(PTRACE_CONT, child_pid, None, None) != 0:
            print(f"PTRACE_CONT failed errno={_errno()}", file=sys.stderr)
            observer_rc = 2
            return 2

        while True:
            now = time.monotonic()
            if args.qualification == "signal" and exec_seen and not term_sent:
                os.kill(child_pid, signal.SIGTERM)
                term_sent = True
                kill_deadline = now + 10.0

            if not term_sent and now >= deadline:
                timed_out = True
                try:
                    os.kill(child_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                term_sent = True
                kill_deadline = now + 10.0
            if (
                term_sent
                and not kill_sent
                and kill_deadline is not None
                and now >= kill_deadline
            ):
                timed_out = True
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                kill_sent = True

            # Hard outer bound: never hang past deadline + 15s.
            if now > deadline + 15.0:
                print("observer hard deadline exceeded", file=sys.stderr)
                timed_out = True
                observer_rc = 124
                return 124

            wpid, status = os.waitpid(child_pid, os.WNOHANG)
            if wpid == 0:
                time.sleep(0.02)
                continue

            if os.WIFSTOPPED(status):
                event = (status >> 16) & 0xFFFF
                stop_sig = os.WSTOPSIG(status)
                if event == PTRACE_EVENT_EXEC:
                    try:
                        observed_exe = resolve_exe_path(child_pid)
                        observed_cwd = resolve_cwd(child_pid)
                        observed_argv = read_cmdline(child_pid)
                        # Hash the open /proc/<pid>/exe FD while still stopped.
                        # Do not persist st_dev/st_ino: they vary across Docker clones.
                        exec_sha = hash_open_exe_fd(child_pid)
                        exec_seen = True
                        # Arm fault injection for the post-exec continue only.
                        ptrace._post_exec_ready = True  # type: ignore[attr-defined]
                    except FileNotFoundError:
                        print("proc disappeared at exec-stop", file=sys.stderr)
                        observer_rc = 3
                        return 3
                    except OSError as exc:
                        print(f"executable identity failure: {exc}", file=sys.stderr)
                        observer_rc = 3
                        return 3
                    if ptrace(PTRACE_CONT, child_pid, None, None) != 0:
                        print(
                            f"PTRACE_CONT post-exec failed errno={_errno()}",
                            file=sys.stderr,
                        )
                        observer_rc = 2
                        return 2
                else:
                    deliver = (
                        0
                        if stop_sig in (signal.SIGTRAP, signal.SIGSTOP) and event == 0
                        else stop_sig
                    )
                    if stop_sig in (
                        signal.SIGTERM,
                        signal.SIGKILL,
                        signal.SIGINT,
                        signal.SIGQUIT,
                    ):
                        deliver = stop_sig
                    if event != 0 and stop_sig == signal.SIGTRAP:
                        deliver = 0
                    if ptrace(PTRACE_CONT, child_pid, None, deliver if deliver else None) != 0:
                        print(
                            f"PTRACE_CONT failed errno={_errno()}",
                            file=sys.stderr,
                        )
                        observer_rc = 2
                        return 2
                continue

            if os.WIFEXITED(status):
                exit_status = os.WEXITSTATUS(status)
                wait_code = exit_status
                sig_num = None
                child_pid = -1  # already reaped
                break
            if os.WIFSIGNALED(status):
                sig_num = os.WTERMSIG(status)
                exit_status = None
                wait_code = 128 + sig_num
                child_pid = -1
                break

            print(f"unexpected wait status={status}", file=sys.stderr)
            observer_rc = 2
            return 2

        if not exec_seen or not observed_argv or not observed_exe.startswith("/"):
            print("failed to observe live exec (exe/argv/cwd)", file=sys.stderr)
            write_json(Path(args.observed_argv), observed_argv or subject)
            observer_rc = 3
            return 3

        if ".." in Path(observed_exe).parts or ".." in Path(observed_cwd).parts:
            print("observed path contains ..", file=sys.stderr)
            observer_rc = 3
            return 3
        if not observed_cwd.startswith("/"):
            print(f"observed cwd not absolute: {observed_cwd}", file=sys.stderr)
            observer_rc = 3
            return 3
        if not exec_sha or exec_sha == "f" * 64 or exec_sha == "0" * 64:
            print("missing executable content hash from open FD", file=sys.stderr)
            observer_rc = 3
            return 3

        # Exactly one valid outcome shape.
        if timed_out:
            if sig_num is None:
                if exit_status is not None and not term_sent:
                    timed_out = False
                else:
                    sig_num = signal.SIGTERM
                    exit_status = None
                    wait_code = 128 + sig_num
            else:
                exit_status = None
        else:
            if sig_num is not None:
                exit_status = None
            elif exit_status is None:
                exit_status = 1
                wait_code = 1

        child = {
            "command": " ".join(observed_argv),
            "argv": observed_argv,
            "exit_status": exit_status,
            "signal": sig_num,
            "timed_out": bool(timed_out),
        }
        write_json(Path(args.observed_argv), observed_argv)
        write_json(Path(args.observed_children), [child])

        status_lines = [
            f"EXIT_STATUS={'' if exit_status is None else exit_status}",
            f"SIGNAL={'' if sig_num is None else sig_num}",
            f"TIMED_OUT={1 if timed_out else 0}",
            f"HOST_OBSERVER_CODE={wait_code if wait_code is not None else 1}",
            f"WORKDIR={observed_cwd}",
            f"EXECUTABLE_PATH={observed_exe}",
            f"EXECUTABLE_SHA256={exec_sha}",
            f"WAIT_STATUS_RAW={wait_code if wait_code is not None else -1}",
            f"QUALIFICATION={args.qualification or 'none'}",
            f"TIMEOUT_SECONDS={timeout_sec}",
        ]
        Path(args.status).write_text("\n".join(status_lines) + "\n", encoding="utf-8")

        meta_lines = [
            f"EXECUTABLE_PATH={observed_exe}",
            f"EXECUTABLE_SHA256={exec_sha}",
            f"WORKDIR={observed_cwd}",
            f"TIMEOUT_SECONDS={timeout_sec}",
            f"DECLARED_ARGV0={subject[0]}",
            f"OBSERVED_ARGV0={observed_argv[0]}",
        ]
        Path(args.meta).write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

        if timed_out:
            observer_rc = 124
            return 124
        if sig_num is not None:
            observer_rc = min(128 + sig_num, 255)
            return observer_rc
        observer_rc = int(exit_status or 0)
        return observer_rc
    finally:
        # Always reap / kill on any exit path while child may still be live.
        if child_pid > 0:
            kill_and_reap(child_pid)
        if stdout_fd >= 0:
            try:
                os.close(stdout_fd)
            except OSError:
                pass
        if stderr_fd >= 0:
            try:
                os.close(stderr_fd)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
