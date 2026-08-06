#!/usr/bin/env python3
"""Capture M0 diagnostics wave1 Oracle reference observations."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

WAVE_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = WAVE_ROOT / "fixtures"
CASES = WAVE_ROOT / "cases"
IMAGE = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
TIMEOUT_SECONDS = 30
FILE_TREE_SEMANTICS = "workspace_including_inputs"
CLEANUP_POLICY = (
    "remove_case_workdir_before_capture_and_force_remove_named_container"
)
# Exact variables applied to the Oracle command via in-container `env -i`.
# Docker host CLI uses a fixed minimal env; no ambient host PATH/HOME is inherited.
DECLARED_COMMAND_ENV = {
    "HOME": "/work",
    "LANG": "C",
    "LC_ALL": "C",
    "TZ": "UTC",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}
# Fixed host-side env for launching docker CLI only (not the Oracle command env).
DOCKER_CLI_HOST_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "C",
    "LC_ALL": "C",
    "TZ": "UTC",
}
ENVIRONMENT_POLICY = {
    "mode": "in_container_env_dash_i_clean",
    "inherits_host_environment": False,
    "declared_variables": DECLARED_COMMAND_ENV,
    "command_wrapper": ["env", "-i"],
    "reviewed_exclusions": [
        "host process environment is not inherited by docker CLI or Oracle command",
        "Oracle command environment is produced by in-container env -i with only declared_variables",
        "Docker-injected variables such as HOSTNAME do not remain because env -i replaces the environment",
    ],
}
EXECUTION_ENVIRONMENT = {
    "docker_image": IMAGE,
    "network": "none",
    "user": "1000:1000",
    "workdir": "/work",
    "env": DECLARED_COMMAND_ENV,
    "tmpfs": ["/tmp:rw,exec,mode=1777"],
    "timeout_seconds": TIMEOUT_SECONDS,
    "cleanup": CLEANUP_POLICY,
    "environment_policy": ENVIRONMENT_POLICY,
    "docker_cli_host_env": DOCKER_CLI_HOST_ENV,
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


CASE_SPECS: list[dict[str, Any]] = [
    {
        "id": "diag-noargs-geninfo-writable",
        "argv": ["geninfo"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-NOARGS-GENINFO-001"],
        "kind": "startup_boundary",
        "notes": "Writable /tmp and /work; true geninfo no-args path.",
    },
    {
        "id": "diag-ignore0-format-da",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "planned_case_ids": ["DIAG-IGNORE-ERROR-001"],
        "kind": "named_error_fatal",
    },
    {
        "id": "diag-ignore1-format-da",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "planned_case_ids": ["DIAG-IGNORE-WARN-001"],
        "kind": "named_error_ignore_one",
    },
    {
        "id": "diag-ignore2-format-da",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "planned_case_ids": ["DIAG-IGNORE-SILENT-001"],
        "kind": "named_error_ignore_two",
    },
    {
        "id": "diag-keep-going-format-da",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--keep-going",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "planned_case_ids": ["DIAG-KEEP-GOING-001"],
        "kind": "keep_going_control",
    },
    {
        "id": "diag-ignore-unknown",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "notaclass",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "planned_case_ids": ["DIAG-IGNORE-UNKNOWN-001"],
        "kind": "ignore_unknown_control",
    },
    {
        "id": "diag-ignore-precedence-cli-replaces-rc",
        "argv": [
            "lcov",
            "--config-file",
            "ignore-format.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "negative",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info", "ignore-format.rc"],
        "planned_case_ids": ["DIAG-IGNORE-PRECEDENCE-001"],
        "kind": "ignore_precedence_control",
        "notes": "RC ignores format, CLI supplies only negative; format remains fatal.",
    },
    {
        "id": "diag-warning0-format-sanitize",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info"],
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "kind": "warning_control",
    },
    {
        "id": "diag-warning1-format-sanitize",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "format",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info"],
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "kind": "warning_control",
    },
    {
        "id": "diag-warning2-format-sanitize",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info"],
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "kind": "warning_control",
    },
    {
        "id": "diag-promote0-format-sanitize",
        "argv": [
            "lcov",
            "--config-file",
            "promote.rc",
            "--no-function-coverage",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info", "promote.rc"],
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "kind": "warning_promotion_control",
    },
    {
        "id": "diag-promote1-format-sanitize",
        "argv": [
            "lcov",
            "--config-file",
            "promote.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info", "promote.rc"],
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "kind": "warning_promotion_control",
    },
    {
        "id": "diag-promote2-format-sanitize",
        "argv": [
            "lcov",
            "--config-file",
            "promote.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info", "promote.rc"],
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "kind": "warning_promotion_control",
    },
    {
        "id": "diag-max-messages-format",
        "argv": [
            "lcov",
            "--config-file",
            "maxmsg.rc",
            "--no-function-coverage",
            "--keep-going",
            "--add-tracefile",
            "many-format.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["many-format.info", "maxmsg.rc"],
        "planned_case_ids": ["DIAG-MAX-MESSAGES-001"],
        "kind": "message_suppression_control",
    },
    {
        "id": "diag-expected-count-file-false",
        "argv": [
            "lcov",
            "--config-file",
            "expect-count-false.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info", "expect-count-false.rc"],
        "planned_case_ids": ["DIAG-EXPECTED-COUNT-FILE-001"],
        "kind": "expected_count_control",
    },
    {
        "id": "diag-expected-count-file-true",
        "argv": [
            "lcov",
            "--config-file",
            "expect-count-true.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info", "expect-count-true.rc"],
        "planned_case_ids": ["DIAG-EXPECTED-COUNT-FILE-001"],
        "kind": "expected_count_control",
    },
    {
        "id": "diag-expected-count-manual-file",
        "argv": [
            "lcov",
            "--config-file",
            "expect-manual.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info", "expect-manual.rc"],
        "planned_case_ids": ["DIAG-EXPECTED-COUNT-MANUAL-FILE-001"],
        "kind": "expected_count_control",
    },
    {
        "id": "diag-expected-count-manual-rc",
        "argv": [
            "lcov",
            "--rc",
            "expect_message_count=format:0",
            "--no-function-coverage",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "planned_case_ids": ["DIAG-EXPECTED-COUNT-MANUAL-RC-001"],
        "kind": "expected_count_control",
    },
    {
        "id": "diag-message-log",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--msg-log",
            "messages.log",
            "--ignore-errors",
            "format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "planned_case_ids": ["DIAG-MESSAGE-LOG-001"],
        "kind": "message_log_control",
    },
    {
        "id": "diag-perl2lcov-keep",
        "argv": [
            "perl2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "cover_db",
        ],
        "fixtures": ["cover_db"],
        "planned_case_ids": ["DIAG-PERL2LCOV-KEEP-001"],
        "kind": "converter_keep_trap",
        "notes": "Empty cover_db input continues named empty errors and exits 0.",
    },
    {
        "id": "diag-llvm2lcov-keep",
        "argv": [
            "llvm2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "llvm-keep.json",
        ],
        "fixtures": ["llvm-keep.json"],
        "planned_case_ids": ["DIAG-LLVM2LCOV-KEEP-001"],
        "kind": "converter_keep_trap",
        "notes": "Real JSON export input; keep-going continues source/empty errors and exits 0.",
    },
    {
        "id": "diag-py2lcov-keep",
        "argv": [
            "py2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "coverage-keep.xml",
        ],
        "fixtures": ["coverage-keep.xml"],
        "planned_case_ids": ["DIAG-PY2LCOV-KEEP-001"],
        "kind": "converter_keep_trap",
        "notes": "Real Coverage.py XML input; keep-going catches conversion issues and exits 0.",
    },
    {
        "id": "diag-xml2lcov-keep",
        "argv": [
            "xml2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "coverage-keep.xml",
        ],
        "fixtures": ["coverage-keep.xml"],
        "planned_case_ids": ["DIAG-XML2LCOV-KEEP-001"],
        "kind": "converter_keep_trap",
        "notes": "Real Coverage.py XML input; keep-going path exits 0 with partial TN artifact.",
    },
    {
        "id": "diag-converter-keep-boundary",
        "argv": [
            "xml2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "broken-no-sources.xml",
        ],
        "fixtures": ["broken-no-sources.xml"],
        "planned_case_ids": ["DIAG-CONVERTER-KEEP-BOUNDARY-001"],
        "kind": "converter_keep_trap",
        "notes": "Pre-try XML structural failure bypasses keep-going and exits 1.",
    },
    {
        "id": "par-serial-parity-parallel1",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--parallel",
            "1",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["a.info", "b.info"],
        "planned_case_ids": ["PAR-SERIAL-PARITY-001"],
        "kind": "parallel_control",
    },
    {
        "id": "par-serial-parity-parallel2",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--parallel",
            "2",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["a.info", "b.info"],
        "planned_case_ids": ["PAR-SERIAL-PARITY-001"],
        "kind": "parallel_control",
    },
]


def stage(work: Path, fixtures: list[str]) -> None:
    work.mkdir(parents=True)
    for name in fixtures:
        src = FIXTURES / name
        if not src.exists():
            raise SystemExit(f"missing fixture: {name}")
        dest = work / name
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)


def file_tree(work: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(work.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(work).as_posix()
        if rel.startswith("reference/") or rel in {"result.json"}:
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": rel,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    return entries


def fixture_bindings(fixtures: list[str]) -> list[dict[str, Any]]:
    result = []
    for name in fixtures:
        src = FIXTURES / name
        if src.is_dir():
            # bind directory tree of fixture inputs
            for path in sorted(src.rglob("*")):
                if not path.is_file():
                    continue
                rel = f"{name}/{path.relative_to(src).as_posix()}"
                data = path.read_bytes()
                result.append(
                    {
                        "path": rel,
                        "bytes": len(data),
                        "sha256": sha256_bytes(data),
                    }
                )
        else:
            data = src.read_bytes()
            result.append(
                {
                    "path": name,
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
    return result


class Wave1CaptureError(RuntimeError):
    """Fail-closed capture failure."""


def container_absent(name: str) -> bool:
    """Return True only when docker ps succeeds and the named container is absent.

    Observer errors (nonzero docker ps, timeout, empty observer failure) raise.
    Nonzero ps is never interpreted as an empty/absent list.
    """
    try:
        observed = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env=DOCKER_CLI_HOST_ENV,
        )
    except subprocess.TimeoutExpired as error:
        raise Wave1CaptureError(
            f"docker ps observer timed out while checking {name}"
        ) from error
    except OSError as error:
        raise Wave1CaptureError(
            f"docker ps observer failed to execute while checking {name}: {error}"
        ) from error
    if observed.returncode != 0:
        raise Wave1CaptureError(
            "docker ps observer failed: "
            f"rc={observed.returncode} stderr={observed.stderr!r}"
        )
    names = [line for line in observed.stdout.splitlines() if line]
    return name not in names


def force_remove_container(name: str, *, direct_child_reaped: bool) -> dict[str, Any]:
    """Stop/rm named container and verify absence with fail-closed observers.

    Docker observations use process_group_empty=null because the host process
    group is not the container process model.
    """
    if not container_absent(name):
        removal = subprocess.run(
            ["docker", "rm", "-f", name],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env=DOCKER_CLI_HOST_ENV,
        )
        if removal.returncode != 0 and not container_absent(name):
            raise Wave1CaptureError(
                f"docker rm -f failed and container still present: {name} "
                f"rc={removal.returncode} stderr={removal.stderr!r}"
            )
    absent = container_absent(name)
    if not absent:
        raise Wave1CaptureError(f"wave1 container survived cleanup: {name}")
    if not direct_child_reaped:
        raise Wave1CaptureError(
            f"wave1 docker CLI child was not reaped before cleanup confirmation: {name}"
        )
    return {
        "policy": CLEANUP_POLICY,
        "direct_child_reaped": True,
        "process_group_empty": None,
        "container_absent": True,
        "named_container_removed": True,
        "container_name": name,
    }


def command_env_assignments() -> list[str]:
    return [f"{key}={value}" for key, value in sorted(DECLARED_COMMAND_ENV.items())]


def probe_effective_command_environment() -> dict[str, str]:
    """Observe the exact environment the Oracle command wrapper produces."""
    container_name = "ferricov-diag-wave1-env-probe"
    force_remove_container(container_name, direct_child_reaped=True)
    cmd = [
        "docker",
        "run",
        "--name",
        container_name,
        "--rm",
        "--network=none",
        "-u",
        EXECUTION_ENVIRONMENT["user"],
        "-w",
        EXECUTION_ENVIRONMENT["workdir"],
        "--tmpfs",
        EXECUTION_ENVIRONMENT["tmpfs"][0],
        IMAGE,
        "env",
        "-i",
        *command_env_assignments(),
        "env",
        "-0",
    ]
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        env=DOCKER_CLI_HOST_ENV,
    )
    force_remove_container(container_name, direct_child_reaped=True)
    if completed.returncode != 0:
        raise Wave1CaptureError(
            "failed to probe effective command environment: "
            f"rc={completed.returncode} stderr={completed.stderr!r}"
        )
    effective: dict[str, str] = {}
    for entry in completed.stdout.split(b"\0"):
        if not entry:
            continue
        if b"=" not in entry:
            raise Wave1CaptureError(
                f"malformed env probe entry: {entry!r}"
            )
        key, value = entry.split(b"=", 1)
        effective[key.decode("ascii")] = value.decode("ascii")
    if effective != DECLARED_COMMAND_ENV:
        raise Wave1CaptureError(
            "effective command environment differs from declared clean env: "
            f"observed={effective!r} declared={DECLARED_COMMAND_ENV!r}"
        )
    return effective


def run_case(
    spec: dict[str, Any],
    effective_environment_variables: dict[str, str],
) -> dict[str, Any]:
    work = CASES / spec["id"]
    if work.exists():
        shutil.rmtree(work)
    stage(work, spec["fixtures"])
    ref = work / "reference"
    ref.mkdir()
    container_name = f"ferricov-diag-wave1-{spec['id']}"
    force_remove_container(container_name, direct_child_reaped=True)
    # Oracle command runs under in-container env -i with only declared variables.
    cmd = [
        "docker",
        "run",
        "--name",
        container_name,
        "--rm",
        "--network=none",
        "-u",
        EXECUTION_ENVIRONMENT["user"],
        "-w",
        EXECUTION_ENVIRONMENT["workdir"],
        "--tmpfs",
        EXECUTION_ENVIRONMENT["tmpfs"][0],
        "-v",
        f"{work}:/work:rw",
        IMAGE,
        "env",
        "-i",
        *command_env_assignments(),
        *spec["argv"],
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=DOCKER_CLI_HOST_ENV,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=TIMEOUT_SECONDS)
        exit_status = proc.returncode
        direct_child_reaped = True
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, stderr = b"", b""
        exit_status = 124
        direct_child_reaped = proc.poll() is not None
        if not direct_child_reaped:
            proc.kill()
            proc.wait(timeout=10)
            direct_child_reaped = True
    cleanup_outcome = force_remove_container(
        container_name, direct_child_reaped=direct_child_reaped
    )
    if not cleanup_outcome["container_absent"] or not cleanup_outcome["direct_child_reaped"]:
        raise Wave1CaptureError(f"wave1 cleanup not confirmed: {spec['id']}")
    if stdout is None:
        stdout = b""
    if stderr is None:
        stderr = b""
    (ref / "stdout.bin").write_bytes(stdout)
    (ref / "stderr.bin").write_bytes(stderr)
    (ref / "stdout.txt").write_text(stdout.decode("utf-8", "replace"))
    (ref / "stderr.txt").write_text(stderr.decode("utf-8", "replace"))
    tree = file_tree(work)
    fixtures = fixture_bindings(spec["fixtures"])
    environment_policy = {
        **ENVIRONMENT_POLICY,
        "effective_environment_variables": dict(effective_environment_variables),
    }
    execution_environment = {
        **EXECUTION_ENVIRONMENT,
        "environment_policy": environment_policy,
    }
    result = {
        "case_id": spec["id"],
        "kind": spec["kind"],
        "planned_case_ids": list(spec["planned_case_ids"]),
        "command": spec["argv"][0],
        "argv": list(spec["argv"]),
        "fixtures": list(spec["fixtures"]),
        "fixture_bindings": fixtures,
        "image": IMAGE,
        "upstream_commit": UPSTREAM_COMMIT,
        "execution_environment": execution_environment,
        "effective_environment_variables": dict(effective_environment_variables),
        "environment_policy": environment_policy,
        "timeout_seconds": TIMEOUT_SECONDS,
        "timed_out": timed_out,
        "cleanup": CLEANUP_POLICY,
        "cleanup_outcome": cleanup_outcome,
        "file_tree_semantics": FILE_TREE_SEMANTICS,
        "exit_status": exit_status,
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
        "file_tree": tree,
        "file_tree_sha256": sha256_bytes(
            json.dumps(tree, sort_keys=True, separators=(",", ":")).encode("ascii")
        ),
        "notes": spec.get("notes", ""),
        "product_compatibility_evidence": False,
        "evidence_status": "oracle_reference",
    }
    (work / "result.json").write_text(canonical_json(result))
    print(
        f"CASE {spec['id']} exit={exit_status} timed_out={timed_out} "
        f"cleanup_absent={cleanup_outcome['container_absent']} "
        f"env_keys={sorted(effective_environment_variables)} "
        f"stderr={result['stderr_sha256'][:12]} planned={spec['planned_case_ids']}",
        flush=True,
    )
    return result


def main() -> int:
    effective_environment_variables = probe_effective_command_environment()
    results = [
        run_case(spec, effective_environment_variables) for spec in CASE_SPECS
    ]
    environment_policy = {
        **ENVIRONMENT_POLICY,
        "effective_environment_variables": dict(effective_environment_variables),
    }
    execution_environment = {
        **EXECUTION_ENVIRONMENT,
        "environment_policy": environment_policy,
    }
    index = {
        "schema_version": 1,
        "wave": "m0-diagnostics-wave1",
        "upstream_commit": UPSTREAM_COMMIT,
        "image": IMAGE,
        "product_compatibility_evidence": False,
        "evidence_status": "oracle_reference",
        "file_tree_semantics": FILE_TREE_SEMANTICS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "execution_environment": execution_environment,
        "effective_environment_variables": dict(effective_environment_variables),
        "environment_policy": environment_policy,
        "cleanup": CLEANUP_POLICY,
        "case_count": len(results),
        "cases": [
            {
                "id": result["case_id"],
                "path": f"cases/{result['case_id']}/result.json",
                "kind": result["kind"],
                "planned_case_ids": result["planned_case_ids"],
                "argv": result["argv"],
                "fixtures": result["fixtures"],
                "exit_status": result["exit_status"],
                "stdout_sha256": result["stdout_sha256"],
                "stderr_sha256": result["stderr_sha256"],
                "file_tree_sha256": result["file_tree_sha256"],
                "observation_sha256": sha256_file(
                    CASES / result["case_id"] / "result.json"
                ),
                "cleanup": result["cleanup"],
                "cleanup_outcome": result["cleanup_outcome"],
                "effective_environment_variables": result[
                    "effective_environment_variables"
                ],
                "environment_policy": result["environment_policy"],
            }
            for result in results
        ],
    }
    (WAVE_ROOT / "result.json").write_text(canonical_json(index))
    print(
        f"WAVE1_INDEX cases={len(results)} "
        f"sha256={sha256_file(WAVE_ROOT / 'result.json')} "
        f"effective_env={sorted(effective_environment_variables)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
