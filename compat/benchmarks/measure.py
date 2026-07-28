#!/usr/bin/env python3
"""Measure one child process from inside its Linux execution environment."""

from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path


def _nanoseconds(seconds: float) -> int:
    return round(seconds * 1_000_000_000)


def _write_json(path: Path, document: dict[str, object]) -> None:
    encoded = json.dumps(document, ensure_ascii=True, sort_keys=True) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(encoded, encoding="ascii")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--stdout", type=Path, required=True)
    parser.add_argument("--stderr", type=Path, required=True)
    parser.add_argument("--chown")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("a command is required after --")

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic_ns()
    exit_code: int | None = None
    signal: int | None = None

    with args.stdout.open("wb") as stdout, args.stderr.open("wb") as stderr:
        try:
            completed = subprocess.run(command, stdout=stdout, stderr=stderr, check=False)
            if completed.returncode < 0:
                signal = -completed.returncode
            else:
                exit_code = completed.returncode
        except OSError as error:
            stderr.write(f"measure: failed to execute {command[0]}: {error}\n".encode())
            exit_code = 127

    finished = time.monotonic_ns()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    document: dict[str, object] = {
        "schema_version": 1,
        "measurement_backend": "linux-rusage-children-v1",
        "clock": "monotonic",
        "wall_time_ns": finished - started,
        "user_cpu_time_ns": _nanoseconds(after.ru_utime - before.ru_utime),
        "system_cpu_time_ns": _nanoseconds(after.ru_stime - before.ru_stime),
        "peak_rss_bytes": after.ru_maxrss * 1024,
        "exit_code": exit_code,
        "signal": signal,
    }
    _write_json(args.metrics, document)

    if args.chown is not None and os.geteuid() == 0:
        uid_text, gid_text = args.chown.split(":", 1)
        uid, gid = int(uid_text), int(gid_text)
        for path in (Path.cwd(), args.metrics.parent):
            for directory, directories, files in os.walk(path, topdown=False):
                for name in [*files, *directories]:
                    os.lchown(Path(directory) / name, uid, gid)
            os.chown(path, uid, gid)

    if signal is not None:
        return min(255, 128 + signal)
    assert exit_code is not None
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
