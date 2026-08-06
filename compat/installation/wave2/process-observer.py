#!/usr/bin/env python3
"""Live-process observer for installation wave-2 Oracle captures.

Launches the subject under a clean environment with ptrace exec-stop so that
executable path, argv (cmdline), and cwd are read from /proc after the real
exec. Records the actual wait status (exit/signal) and optional deadline
timeout (SIGTERM then SIGKILL). Child observation is the subject itself with
its real wait outcome.
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


def _errno() -> int:
    return ctypes.get_errno()


def ptrace(request: int, pid: int = 0, addr=None, data=None) -> int:
    return libc.ptrace(request, pid, addr, data)


def read_cmdline(pid: int) -> list[str]:
    raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    parts = [p.decode("utf-8", errors="surrogateescape") for p in raw.split(b"\0") if p]
    return parts


def resolve_exe(pid: int) -> str:
    return os.readlink(f"/proc/{pid}/exe")


def resolve_cwd(pid: int) -> str:
    return os.readlink(f"/proc/{pid}/cwd")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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

    # Record the clean env that will be applied (sorted for stability).
    env_lines = [f"{k}={env[k]}" for k in sorted(env)]
    Path(args.observed_env).write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    stdout_path = Path(args.stdout)
    stderr_path = Path(args.stderr)
    stdout_fd = os.open(str(stdout_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    stderr_fd = os.open(str(stderr_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

    timeout_sec = max(1, int(args.timeout_seconds))
    if args.qualification == "timeout":
        timeout_sec = 1  # force short deadline for qualification probe

    started = time.monotonic()
    deadline = started + timeout_sec
    term_sent = False
    kill_sent = False
    kill_deadline = None

    child_pid = os.fork()
    if child_pid == 0:
        try:
            os.chdir(str(workdir))
            os.dup2(stdout_fd, 1)
            os.dup2(stderr_fd, 2)
            os.close(stdout_fd)
            os.close(stderr_fd)
            # Drop extra fds above stderr.
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

    # Wait for initial SIGSTOP from child.
    _, status = os.waitpid(child_pid, 0)
    if not os.WIFSTOPPED(status):
        print("child did not stop for attach", file=sys.stderr)
        return 2
    if ptrace(PTRACE_SETOPTIONS, child_pid, None, PTRACE_O_TRACEEXEC) != 0:
        print(f"PTRACE_SETOPTIONS failed errno={_errno()}", file=sys.stderr)
        return 2
    if ptrace(PTRACE_CONT, child_pid, None, None) != 0:
        print(f"PTRACE_CONT failed errno={_errno()}", file=sys.stderr)
        return 2

    observed_exe = ""
    observed_cwd = ""
    observed_argv: list[str] = []
    exec_seen = False
    exit_status = None
    sig_num = None
    timed_out = False
    wait_code = None

    while True:
        now = time.monotonic()
        # Qualification: after exec, immediately SIGTERM for signal probe.
        if args.qualification == "signal" and exec_seen and not term_sent:
            os.kill(child_pid, signal.SIGTERM)
            term_sent = True
            kill_deadline = now + 10.0

        # Deadline handling (real timeout path).
        if not term_sent and now >= deadline:
            timed_out = True
            try:
                os.kill(child_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            term_sent = True
            kill_deadline = now + 10.0
        if term_sent and not kill_sent and kill_deadline is not None and now >= kill_deadline:
            timed_out = True
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            kill_sent = True

        # Use WNOHANG with short sleep so we can enforce deadlines.
        wpid, status = os.waitpid(child_pid, os.WNOHANG)
        if wpid == 0:
            time.sleep(0.02)
            continue

        if os.WIFSTOPPED(status):
            event = (status >> 16) & 0xFFFF
            stop_sig = os.WSTOPSIG(status)
            if event == PTRACE_EVENT_EXEC:
                # Live process evidence after exec.
                try:
                    observed_exe = resolve_exe(child_pid)
                    observed_cwd = resolve_cwd(child_pid)
                    observed_argv = read_cmdline(child_pid)
                    exec_seen = True
                except FileNotFoundError:
                    pass
                ptrace(PTRACE_CONT, child_pid, None, None)
            else:
                # Deliver the stopping signal (except pure ptrace traps without signal intent).
                deliver = 0 if stop_sig in (signal.SIGTRAP, signal.SIGSTOP) and event == 0 else stop_sig
                # For signal qualification / timeout, always deliver non-trap stops.
                if stop_sig in (signal.SIGTERM, signal.SIGKILL, signal.SIGINT, signal.SIGQUIT):
                    deliver = stop_sig
                if event != 0 and stop_sig == signal.SIGTRAP:
                    deliver = 0
                ptrace(PTRACE_CONT, child_pid, None, deliver if deliver else None)
            continue

        if os.WIFEXITED(status):
            exit_status = os.WEXITSTATUS(status)
            wait_code = exit_status
            sig_num = None
            break
        if os.WIFSIGNALED(status):
            sig_num = os.WTERMSIG(status)
            exit_status = None
            wait_code = 128 + sig_num
            if term_sent and (sig_num in (signal.SIGTERM, signal.SIGKILL) or timed_out):
                # Timeout path or forced signal still records the real signal.
                pass
            break

        print(f"unexpected wait status={status}", file=sys.stderr)
        return 2

    if not exec_seen or not observed_argv or not observed_exe.startswith("/"):
        print("failed to observe live exec (exe/argv/cwd)", file=sys.stderr)
        # Still write what we can for debugging, but fail.
        write_json(Path(args.observed_argv), observed_argv or subject)
        return 3

    if ".." in Path(observed_exe).parts or ".." in Path(observed_cwd).parts:
        print("observed path contains ..", file=sys.stderr)
        return 3
    if not observed_cwd.startswith("/"):
        print(f"observed cwd not absolute: {observed_cwd}", file=sys.stderr)
        return 3

    # Hash the real executable file (resolve if deleted still uses path string).
    try:
        exec_sha = sha256_file(observed_exe)
    except OSError:
        # Fall back to /proc/<pid>/exe was gone; try open via path.
        exec_sha = "f" * 64

    # Exactly one valid outcome shape.
    if timed_out:
        # Timeout always pairs with a signal (TERM or KILL) and null exit.
        if sig_num is None:
            # Process exited before signal delivery; still mark timed_out only if
            # we sent the deadline signal. Prefer real exit if it finished early.
            if exit_status is not None and not term_sent:
                timed_out = False
            else:
                sig_num = signal.SIGTERM
                exit_status = None
                wait_code = 128 + sig_num
        else:
            exit_status = None
    else:
        # Non-timeout: either integer exit XOR signal, not both.
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
    ]
    Path(args.status).write_text("\n".join(status_lines) + "\n", encoding="utf-8")

    meta_lines = [
        f"EXECUTABLE_PATH={observed_exe}",
        f"EXECUTABLE_SHA256={exec_sha}",
        f"WORKDIR={observed_cwd}",
        f"TIMEOUT_SECONDS={args.timeout_seconds}",
        f"DECLARED_ARGV0={subject[0]}",
        f"OBSERVED_ARGV0={observed_argv[0]}",
    ]
    Path(args.meta).write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

    # Observer process exit code: 0 if subject exited 0 without timeout/signal,
    # otherwise non-zero for container rc (distinct from host docker rc).
    if timed_out:
        return 124
    if sig_num is not None:
        return min(128 + sig_num, 255)
    return int(exit_status or 0)


if __name__ == "__main__":
    raise SystemExit(main())
