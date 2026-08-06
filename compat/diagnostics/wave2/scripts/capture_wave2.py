#!/usr/bin/env python3
"""Capture M0 diagnostics wave2 Oracle reference observations.

Wave2 extends the accepted wave1 provenance contract:
- clean in-container env -i with only declared variables
- stdin=subprocess.DEVNULL
- named-container force cleanup with docker-ps observer errors fail-closed
- execution_manifest locale/timezone/executable hashes/tool versions/packages
- pinned image sha256:b02cc...
- upstream v2.5 commit 74c8eab...
- independent raw stdout/stderr/tree/exit facts
- product_compatibility_evidence remains false (oracle_reference only)

Cases may declare extra clean-env variables (for POSIXLY_CORRECT, LCOV_HOME,
LCOV_SHOW_LOCATION, LCOV_FORCE_PARALLEL, LCOV_VALIDATE). Those extras are
merged into the case-local declared env and retained in the observation.
"""

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
BASE_DECLARED_COMMAND_ENV = {
    "HOME": "/work",
    "LANG": "C",
    "LC_ALL": "C",
    "TZ": "UTC",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}
DOCKER_CLI_HOST_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "C",
    "LC_ALL": "C",
    "TZ": "UTC",
}
ENVIRONMENT_POLICY_TEMPLATE = {
    "mode": "in_container_env_dash_i_clean",
    "inherits_host_environment": False,
    "command_wrapper": ["env", "-i"],
    "reviewed_exclusions": [
        "host process environment is not inherited by docker CLI or Oracle command",
        "Oracle command environment is produced by in-container env -i with only declared_variables",
        "Docker-injected variables such as HOSTNAME do not remain because env -i replaces the environment",
        "case-local env extras are still declared clean-env variables, never ambient host inheritance",
    ],
}
EXECUTION_ENVIRONMENT_TEMPLATE = {
    "docker_image": IMAGE,
    "network": "none",
    "user": "1000:1000",
    "workdir": "/work",
    "tmpfs": ["/tmp:rw,exec,mode=1777"],
    "timeout_seconds": TIMEOUT_SECONDS,
    "cleanup": CLEANUP_POLICY,
    "docker_cli_host_env": DOCKER_CLI_HOST_ENV,
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def merge_env(extra: dict[str, str] | None) -> dict[str, str]:
    env = dict(BASE_DECLARED_COMMAND_ENV)
    if extra:
        env.update(extra)
    return env


# Executable Oracle cases only. Ferricov-parity planned IDs remain unbound.
# Each entry's planned_case_ids must be unique across waves (no rebinding of
# wave1-bound identities here except where historical bindings already exist
# and wave2 adds independent executable depth).
CASE_SPECS: list[dict[str, Any]] = [
    # --- Registry / ignore-prefix / POSIX profile ---
    {
        "id": "diag-registry-branch-accept",
        "argv": ["lcov", "--ignore-errors", "branch", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-REGISTRY-001"],
        "kind": "registry_control",
        "notes": "Reserved branch class accepted by ignore list with no production emitter.",
    },
    {
        "id": "diag-ignore-prefix-default-lcov",
        "argv": ["lcov", "--ignore-error", "empty", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-IGNORE-PREFIX-PROFILE-001"],
        "kind": "ignore_prefix_profile",
        "notes": "Default Getopt auto-abbrev accepts singular --ignore-error.",
    },
    {
        "id": "diag-ignore-prefix-posix-lcov",
        "argv": ["lcov", "--ignore-error", "empty", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-IGNORE-PREFIX-PROFILE-001", "DIAG-ENV-POSIX-PROFILE-001"],
        "kind": "ignore_prefix_profile",
        "env": {"POSIXLY_CORRECT": "1"},
        "notes": "POSIXLY_CORRECT disables auto-abbrev; singular --ignore-error is unknown.",
    },
    {
        "id": "diag-env-posix-genhtml",
        "argv": ["genhtml", "--ignore-error", "empty", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-ENV-POSIX-PROFILE-001"],
        "kind": "env_posix_profile",
        "env": {"POSIXLY_CORRECT": "1"},
    },
    {
        "id": "diag-env-posix-geninfo",
        "argv": ["geninfo", "--ignore-error", "empty", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-ENV-POSIX-PROFILE-001"],
        "kind": "env_posix_profile",
        "env": {"POSIXLY_CORRECT": "1"},
    },
    {
        "id": "diag-env-posix-perl2lcov",
        "argv": ["perl2lcov", "--ignore-error", "empty", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-ENV-POSIX-PROFILE-001"],
        "kind": "env_posix_profile",
        "env": {"POSIXLY_CORRECT": "1"},
    },
    {
        "id": "diag-env-posix-llvm2lcov",
        "argv": ["llvm2lcov", "--ignore-error", "empty", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-ENV-POSIX-PROFILE-001"],
        "kind": "env_posix_profile",
        "env": {"POSIXLY_CORRECT": "1"},
    },
    # --- Environment surfaces ---
    {
        "id": "diag-env-clean-lcov-version",
        "argv": ["lcov", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-ENV-CLEAN-001"],
        "kind": "env_clean_control",
        "notes": "Benign invocation under declared clean env only.",
    },
    {
        "id": "diag-env-show-location-1",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--add-tracefile",
            "missing.info",
            "--output-file",
            "o.info",
        ],
        "fixtures": [],
        "planned_case_ids": ["DIAG-ENV-SHOW-LOCATION-001", "DIAG-ENV-PRECEDENCE-001"],
        "kind": "env_show_location",
        "env": {"LCOV_SHOW_LOCATION": "1"},
        "notes": "LCOV_SHOW_LOCATION=1 keeps stack-less fatal missing path.",
    },
    {
        "id": "diag-env-show-location-2",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--add-tracefile",
            "missing.info",
            "--output-file",
            "o.info",
        ],
        "fixtures": [],
        "planned_case_ids": ["DIAG-ENV-SHOW-LOCATION-001"],
        "kind": "env_show_location",
        "env": {"LCOV_SHOW_LOCATION": "2"},
        "notes": "LCOV_SHOW_LOCATION>=2 emits developer stack trace on stderr.",
    },
    {
        "id": "diag-env-lcov-home",
        "argv": ["lcov", "--list", "line-only.info"],
        "fixtures": ["line-only.info", "emptyhome", "lcovhome"],
        "planned_case_ids": ["DIAG-ENV-LCOV-HOME-001", "DIAG-CONFIG-DISCOVERY-001"],
        "kind": "env_lcov_home",
        "env": {"HOME": "/work/emptyhome", "LCOV_HOME": "/work/lcovhome"},
        "notes": "HOME empty; LCOV_HOME/etc/lcovrc selected for discovery.",
    },
    {
        "id": "diag-env-lcov-validate-present",
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_validate",
            "--synthesize-missing",
        ],
        "fixtures": ["sample.info", "sample.c"],
        "planned_case_ids": ["DIAG-ENV-LCOV-VALIDATE-001", "DIAG-ENV-PRECEDENCE-001"],
        "kind": "env_lcov_validate",
        "env": {"LCOV_VALIDATE": "1"},
    },
    {
        "id": "diag-env-allowlist-posixly",
        "argv": ["lcov", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-ENV-ALLOWLIST-001"],
        "kind": "env_allowlist",
        "env": {"POSIXLY_CORRECT": "1"},
        "notes": "POSIXLY_CORRECT is an implicit parser-profile allowlist input.",
    },
    # --- Configuration discovery / include / early error / expansion ---
    {
        "id": "diag-config-discovery-home",
        "argv": ["lcov", "--list", "line-only.info"],
        "fixtures": ["line-only.info", "home"],
        "planned_case_ids": ["DIAG-CONFIG-DISCOVERY-001"],
        "kind": "config_discovery",
        "env": {"HOME": "/work/home"},
        "notes": "HOME/.lcovrc first-readable discovery path.",
    },
    {
        "id": "diag-config-explicit",
        "argv": [
            "lcov",
            "--config-file",
            "explicit.rc",
            "--list",
            "line-only.info",
        ],
        "fixtures": ["line-only.info", "explicit.rc"],
        "planned_case_ids": ["DIAG-CONFIG-EXPLICIT-001"],
        "kind": "config_explicit",
    },
    {
        "id": "diag-config-include",
        "argv": [
            "lcov",
            "--config-file",
            "outer.rc",
            "--no-function-coverage",
            "--add-tracefile",
            "line-only.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["line-only.info", "outer.rc", "nested.rc"],
        "planned_case_ids": ["DIAG-CONFIG-INCLUDE-001"],
        "kind": "config_include",
        "notes": "config_file include of nested.rc (not the pattern-include key).",
    },
    {
        "id": "diag-config-include-loop",
        "argv": [
            "lcov",
            "--config-file",
            "loop.rc",
            "--list",
            "line-only.info",
        ],
        "fixtures": ["line-only.info", "loop.rc"],
        "planned_case_ids": [
            "DIAG-CONFIG-INCLUDE-001",
            "DIAG-CONFIG-EARLY-ERROR-001",
        ],
        "kind": "config_early_error",
    },
    {
        "id": "diag-config-unknown-key-file",
        "argv": [
            "lcov",
            "--config-file",
            "unknown-key.rc",
            "--list",
            "line-only.info",
        ],
        "fixtures": ["line-only.info", "unknown-key.rc"],
        "planned_case_ids": ["DIAG-CONFIG-UNKNOWN-KEY-001"],
        "kind": "config_unknown_key",
        "notes": "Unknown file key is silently ignored.",
    },
    {
        "id": "diag-config-env-expand-missing",
        "argv": [
            "lcov",
            "--config-file",
            "env-missing.rc",
            "--list",
            "line-only.info",
        ],
        "fixtures": ["line-only.info", "env-missing.rc"],
        "planned_case_ids": ["DIAG-CONFIG-ENV-EXPAND-001"],
        "kind": "config_env_expand",
    },
    {
        "id": "diag-config-early-unreadable",
        "argv": [
            "lcov",
            "--config-file",
            "noread.rc",
            "--list",
            "line-only.info",
        ],
        "fixtures": ["line-only.info", "noread.rc"],
        "planned_case_ids": ["DIAG-CONFIG-EARLY-ERROR-001"],
        "kind": "config_early_error",
        "notes": "Unreadable explicit config fails early with usage status.",
        "chmod": {"noread.rc": 0o000},
    },
    # --- Raw / dependency / traceback / callback finalize-cleanup ---
    {
        "id": "diag-raw-perl-die",
        "argv": [
            "perl",
            "-e",
            "use lib '/usr/local/lib/lcov'; require lcovutil; die 'raw-perl-boundary';",
        ],
        "fixtures": [],
        "planned_case_ids": ["DIAG-RAW-PERL-001"],
        "kind": "raw_perl_boundary",
    },
    {
        "id": "diag-python-traceback",
        "argv": ["py2lcov", "--output", "out.info", "bad.xml"],
        "fixtures": ["bad.xml"],
        "planned_case_ids": ["DIAG-PYTHON-TRACEBACK-001"],
        "kind": "python_traceback_boundary",
    },
    {
        "id": "diag-dependency-genpng-present",
        "argv": ["genpng", "--version"],
        "fixtures": [],
        "planned_case_ids": ["DIAG-DEPENDENCY-GENPNG-001"],
        "kind": "dependency_genpng",
        "notes": "Pinned image has GD 2.76 present; version path reaches parser.",
    },
    {
        "id": "diag-callback-finalize-fail",
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_finalize",
            "--simplify-script",
            "./parallelFail.pm,start,save,restore",
            "--synthesize-missing",
        ],
        "fixtures": ["sample.info", "sample.c", "parallelFail.pm"],
        "planned_case_ids": ["DIAG-CALLBACK-FINALIZE-FAIL-001"],
        "kind": "callback_finalize",
    },
    {
        "id": "diag-callback-cleanup-missing-restore",
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_cleanup",
            "--simplify-script",
            "./missingRestore.pm",
            "--synthesize-missing",
            "--parallel",
            "2",
        ],
        "fixtures": ["sample.info", "sample.c", "missingRestore.pm"],
        "planned_case_ids": ["DIAG-CALLBACK-CLEANUP-001"],
        "kind": "callback_cleanup",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": "missingRestore implements save without restore (package diagnostic).",
    },
    # --- Parallel worker / callback / memory / message log ---
    {
        "id": "par-child-exit-callback-start",
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_child",
            "--simplify-script",
            "./parallelFail.pm",
            "--synthesize-missing",
            "--parallel",
            "2",
        ],
        "fixtures": ["sample.info", "sample.c", "parallelFail.pm"],
        "planned_case_ids": ["PAR-CHILD-EXIT-001", "PAR-CALLBACK-LIFECYCLE-FAIL-001"],
        "kind": "parallel_child_exit",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": "Forced parallel start callback failure plus missing dump/fork path.",
    },
    {
        "id": "par-callback-state-save-fail",
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_save",
            "--simplify-script",
            "./parallelFail.pm,start",
            "--synthesize-missing",
            "--parallel",
            "2",
        ],
        "fixtures": ["sample.info", "sample.c", "parallelFail.pm"],
        "planned_case_ids": [
            "PAR-CALLBACK-STATE-001",
            "PAR-CALLBACK-LIFECYCLE-FAIL-001",
            "PAR-PAYLOAD-MISSING-001",
        ],
        "kind": "parallel_callback_state",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": "save() dies after start; parent reports parallel serialize + missing dump.",
    },
    {
        "id": "par-msg-log-parallel",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--parallel",
            "2",
            "--msg-log",
            "messages.log",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["a.info", "b.info"],
        "planned_case_ids": ["PAR-MSG-LOG-001", "PAR-MESSAGE-ORDER-001"],
        "kind": "parallel_message_log",
    },
    {
        "id": "par-memory-admission-package",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--memory",
            "1",
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
        "planned_case_ids": ["PAR-MEMORY-ADMISSION-001", "PAR-MEMORY-FALLBACK-001"],
        "kind": "parallel_memory",
        "notes": "Memory::Process absent on pinned image; package diagnostic + admission gate.",
    },
    {
        "id": "par-memory-fallback-ignore-package",
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--memory",
            "1",
            "--parallel",
            "2",
            "--ignore-errors",
            "package",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["a.info", "b.info"],
        "planned_case_ids": ["PAR-MEMORY-FALLBACK-001"],
        "kind": "parallel_memory",
        "notes": "Ignoring package turns off maxMemory and continues via /proc fallback path.",
    },
    {
        "id": "par-lcov-capture-status",
        "argv": [
            "lcov",
            "--capture",
            "--directory",
            "/work/no-such-dir",
            "--output-file",
            "cap.info",
        ],
        "fixtures": [],
        "planned_case_ids": ["PAR-LCOV-CAPTURE-STATUS-001"],
        "kind": "parallel_capture_status",
        "notes": "Delegated geninfo capture failure status/stream identity.",
    },
    {
        "id": "par-partial-commit-control",
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
        "planned_case_ids": ["PAR-PARTIAL-COMMIT-001"],
        "kind": "parallel_partial_commit",
        "notes": "Successful parallel merge control: committed parent state matches serial aggregate.",
    },
]


class Wave2CaptureError(RuntimeError):
    """Fail-closed capture failure."""


def container_absent(name: str) -> bool:
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
        raise Wave2CaptureError(
            f"docker ps observer timed out while checking {name}"
        ) from error
    except OSError as error:
        raise Wave2CaptureError(
            f"docker ps observer failed to execute while checking {name}: {error}"
        ) from error
    if observed.returncode != 0:
        raise Wave2CaptureError(
            "docker ps observer failed: "
            f"rc={observed.returncode} stderr={observed.stderr!r}"
        )
    names = [line for line in observed.stdout.splitlines() if line]
    return name not in names


def force_remove_container(name: str, *, direct_child_reaped: bool) -> dict[str, Any]:
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
            raise Wave2CaptureError(
                f"docker rm -f failed and container still present: {name} "
                f"rc={removal.returncode} stderr={removal.stderr!r}"
            )
    absent = container_absent(name)
    if not absent:
        raise Wave2CaptureError(f"wave2 container survived cleanup: {name}")
    if not direct_child_reaped:
        raise Wave2CaptureError(
            f"wave2 docker CLI child was not reaped before cleanup confirmation: {name}"
        )
    return {
        "policy": CLEANUP_POLICY,
        "direct_child_reaped": True,
        "process_group_empty": None,
        "container_absent": True,
        "named_container_removed": True,
        "container_name": name,
    }


def command_env_assignments(env: dict[str, str]) -> list[str]:
    return [f"{key}={value}" for key, value in sorted(env.items())]


def docker_run_base(container_name: str, *, with_work: Path | None = None) -> list[str]:
    cmd = [
        "docker",
        "run",
        "--name",
        container_name,
        "--rm",
        "--network=none",
        "-u",
        EXECUTION_ENVIRONMENT_TEMPLATE["user"],
        "-w",
        EXECUTION_ENVIRONMENT_TEMPLATE["workdir"],
        "--tmpfs",
        EXECUTION_ENVIRONMENT_TEMPLATE["tmpfs"][0],
    ]
    if with_work is not None:
        cmd.extend(["-v", f"{with_work}:/work:rw"])
    cmd.append(IMAGE)
    return cmd


def run_docker_checked(
    cmd: list[str],
    *,
    timeout: int = TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        timeout=timeout,
        env=DOCKER_CLI_HOST_ENV,
        stdin=subprocess.DEVNULL,
    )


def probe_effective_command_environment(env: dict[str, str]) -> dict[str, str]:
    container_name = "ferricov-diag-wave2-env-probe"
    force_remove_container(container_name, direct_child_reaped=True)
    cmd = [
        *docker_run_base(container_name),
        "env",
        "-i",
        *command_env_assignments(env),
        "env",
        "-0",
    ]
    completed: subprocess.CompletedProcess[bytes] | None = None
    try:
        try:
            completed = run_docker_checked(cmd)
        except subprocess.TimeoutExpired as error:
            raise Wave2CaptureError("effective environment probe timed out") from error
        except OSError as error:
            raise Wave2CaptureError(
                f"effective environment probe failed to execute: {error}"
            ) from error
    finally:
        force_remove_container(container_name, direct_child_reaped=True)

    if completed is None:
        raise Wave2CaptureError("effective environment probe produced no result")
    if completed.returncode != 0:
        raise Wave2CaptureError(
            "failed to probe effective command environment: "
            f"rc={completed.returncode} stderr={completed.stderr!r}"
        )
    effective: dict[str, str] = {}
    for entry in completed.stdout.split(b"\0"):
        if not entry:
            continue
        if b"=" not in entry:
            raise Wave2CaptureError(f"malformed env probe entry: {entry!r}")
        key, value = entry.split(b"=", 1)
        effective[key.decode("ascii")] = value.decode("ascii")
    if effective != env:
        raise Wave2CaptureError(
            "effective command environment differs from declared clean env: "
            f"observed={effective!r} declared={env!r}"
        )
    return effective


def _decode_probe_text(data: bytes) -> str:
    return data.decode("utf-8", "replace").strip()


def probe_execution_manifest(
    effective_environment_variables: dict[str, str],
) -> dict[str, Any]:
    container_name = "ferricov-diag-wave2-manifest-probe"
    force_remove_container(container_name, direct_child_reaped=True)
    probe_script = r"""
set -eu
printf 'LOCALE=%s\n' "${LANG:-}"
printf 'LC_ALL=%s\n' "${LC_ALL:-}"
printf 'TZ=%s\n' "${TZ:-}"
printf 'PERL=%s\n' "$(perl -e 'print $^V' 2>/dev/null || true)"
printf 'PYTHON=%s\n' "$(python3 -c 'import sys; print(sys.version.split()[0])' 2>/dev/null || true)"
if command -v gcc >/dev/null 2>&1; then
  printf 'COMPILER=%s\n' "$(gcc --version | head -n1)"
else
  printf 'COMPILER=not_applicable\n'
fi
if command -v dpkg-query >/dev/null 2>&1; then
  for pkg in perl python3 gcc g++; do
    if dpkg-query -W -f='${Package} ${Version}\n' "$pkg" >/dev/null 2>&1; then
      ver="$(dpkg-query -W -f='${Version}' "$pkg")"
      printf 'PKG_%s=available:%s\n' "$pkg" "$ver"
    else
      printf 'PKG_%s=not_applicable\n' "$pkg"
    fi
  done
  if dpkg-query -W -f='${Package}\n' llvm >/dev/null 2>&1 || command -v llvm-cov >/dev/null 2>&1; then
    printf 'PKG_llvm=available\n'
  else
    printf 'PKG_llvm=not_applicable\n'
  fi
else
  printf 'PKG_perl=not_applicable\n'
  printf 'PKG_python3=not_applicable\n'
  printf 'PKG_gcc=not_applicable\n'
  printf 'PKG_g++=not_applicable\n'
  printf 'PKG_llvm=not_applicable\n'
fi
for tool in geninfo lcov genhtml genpng gendesc perl2lcov llvm2lcov py2lcov xml2lcov perl; do
  path="$(command -v "$tool" || true)"
  if [ -n "$path" ] && [ -f "$path" ]; then
    sum="$(sha256sum "$path" | awk '{print $1}')"
    printf 'EXE_%s=%s %s\n' "$tool" "$path" "$sum"
  else
    printf 'EXE_%s=not_applicable\n' "$tool"
  fi
done
"""
    cmd = [
        *docker_run_base(container_name),
        "env",
        "-i",
        *command_env_assignments(BASE_DECLARED_COMMAND_ENV),
        "sh",
        "-c",
        probe_script,
    ]
    completed: subprocess.CompletedProcess[bytes] | None = None
    try:
        try:
            completed = run_docker_checked(cmd, timeout=60)
        except subprocess.TimeoutExpired as error:
            raise Wave2CaptureError("execution-manifest probe timed out") from error
        except OSError as error:
            raise Wave2CaptureError(
                f"execution-manifest probe failed to execute: {error}"
            ) from error
    finally:
        force_remove_container(container_name, direct_child_reaped=True)

    if completed is None:
        raise Wave2CaptureError("execution-manifest probe produced no result")
    if completed.returncode != 0:
        raise Wave2CaptureError(
            "failed to probe execution manifest: "
            f"rc={completed.returncode} stderr={completed.stderr!r}"
        )

    fields: dict[str, str] = {}
    for line in _decode_probe_text(completed.stdout).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key] = value

    executables: dict[str, Any] = {}
    for tool in (
        "geninfo",
        "lcov",
        "genhtml",
        "genpng",
        "gendesc",
        "perl2lcov",
        "llvm2lcov",
        "py2lcov",
        "xml2lcov",
        "perl",
    ):
        raw = fields.get(f"EXE_{tool}", "not_applicable")
        if raw == "not_applicable":
            executables[tool] = {
                "path": None,
                "sha256": None,
                "availability": "not_applicable",
            }
        else:
            path_text, digest = raw.split(" ", 1)
            executables[tool] = {
                "path": path_text,
                "sha256": f"sha256:{digest}",
                "availability": "available",
            }

    package_availability = {
        "perl": fields.get("PKG_perl", "not_applicable"),
        "python3": fields.get("PKG_python3", "not_applicable"),
        "gcc": fields.get("PKG_gcc", "not_applicable"),
        "g++": fields.get("PKG_g++", "not_applicable"),
        "llvm": fields.get("PKG_llvm", "not_applicable"),
    }

    compiler = fields.get("COMPILER", "not_applicable") or "not_applicable"

    manifest = {
        "schema_version": 1,
        "image": IMAGE,
        "upstream_commit": UPSTREAM_COMMIT,
        "locale": fields.get("LOCALE") or fields.get("LC_ALL") or "C",
        "lc_all": fields.get("LC_ALL") or "C",
        "timezone": fields.get("TZ") or "UTC",
        "stdin": "subprocess.DEVNULL",
        "command_wrapper": ["env", "-i"],
        "effective_environment_variables": dict(effective_environment_variables),
        "runtime_versions": {
            "perl": fields.get("PERL") or "not_applicable",
            "python": fields.get("PYTHON") or "not_applicable",
            "compiler": compiler,
        },
        "package_availability": package_availability,
        "executables": executables,
    }
    for tool in (
        "geninfo",
        "lcov",
        "genhtml",
        "genpng",
        "perl2lcov",
        "llvm2lcov",
        "py2lcov",
        "xml2lcov",
        "perl",
    ):
        if executables[tool]["availability"] != "available":
            raise Wave2CaptureError(f"required wave2 executable unavailable: {tool}")
    if manifest["locale"] != "C" or manifest["lc_all"] != "C":
        raise Wave2CaptureError(
            f"locale provenance drift: locale={manifest['locale']!r} lc_all={manifest['lc_all']!r}"
        )
    if manifest["timezone"] != "UTC":
        raise Wave2CaptureError(f"timezone provenance drift: {manifest['timezone']!r}")
    return manifest


def case_execution_manifest(
    spec: dict[str, Any],
    base_manifest: dict[str, Any],
    case_env: dict[str, str],
) -> dict[str, Any]:
    command = spec["argv"][0]
    executable = base_manifest["executables"][command]
    return {
        **base_manifest,
        "effective_environment_variables": dict(case_env),
        "invoked_command": command,
        "invoked_executable": {
            "name": command,
            "path": executable["path"],
            "sha256": executable["sha256"],
        },
        "invoked_argv": list(spec["argv"]),
    }


def stage(work: Path, fixtures: list[str], chmod_map: dict[str, int] | None) -> None:
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
    if chmod_map:
        for rel, mode in chmod_map.items():
            path = work / rel
            if not path.exists():
                # allow creating empty unreadable file fixture by name
                path.write_bytes(b"")
            path.chmod(mode)


def file_tree(work: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(work.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(work).as_posix()
        if rel.startswith("reference/") or rel in {"result.json"}:
            continue
        # skip unreadable paths carefully
        try:
            data = path.read_bytes()
        except PermissionError:
            entries.append(
                {
                    "path": rel,
                    "bytes": None,
                    "sha256": None,
                    "unreadable": True,
                    "mode": oct(path.stat().st_mode & 0o777),
                }
            )
            continue
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


def run_case(
    spec: dict[str, Any],
    base_manifest: dict[str, Any],
) -> dict[str, Any]:
    work = CASES / spec["id"]
    if work.exists():
        shutil.rmtree(work)
    stage(work, spec["fixtures"], spec.get("chmod"))
    ref = work / "reference"
    ref.mkdir()
    case_env = merge_env(spec.get("env"))
    # Probe/confirm case-local env under env -i.
    effective = probe_effective_command_environment(case_env)
    container_name = f"ferricov-diag-wave2-{spec['id']}"
    force_remove_container(container_name, direct_child_reaped=True)
    cmd = [
        *docker_run_base(container_name, with_work=work),
        "env",
        "-i",
        *command_env_assignments(case_env),
        *spec["argv"],
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
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
        raise Wave2CaptureError(f"wave2 cleanup not confirmed: {spec['id']}")
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
        **ENVIRONMENT_POLICY_TEMPLATE,
        "declared_variables": dict(case_env),
        "effective_environment_variables": dict(effective),
    }
    execution_environment = {
        **EXECUTION_ENVIRONMENT_TEMPLATE,
        "env": dict(case_env),
        "environment_policy": environment_policy,
        "stdin": "subprocess.DEVNULL",
    }
    execution_manifest = case_execution_manifest(spec, base_manifest, case_env)
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
        "execution_manifest": execution_manifest,
        "effective_environment_variables": dict(effective),
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
        f"env_extra={sorted((spec.get('env') or {}).keys())} "
        f"stderr={result['stderr_sha256'][:12]} planned={spec['planned_case_ids']}",
        flush=True,
    )
    return result


def main() -> int:
    # Create noread.rc fixture if missing (empty file; chmod applied per case).
    noread = FIXTURES / "noread.rc"
    if not noread.exists():
        noread.write_text("# unreadable config placeholder\n", encoding="utf-8")

    base_env = dict(BASE_DECLARED_COMMAND_ENV)
    probe_effective_command_environment(base_env)
    base_manifest = probe_execution_manifest(base_env)
    # Base index manifest uses base clean env (without case extras).
    base_manifest = {
        **base_manifest,
        "effective_environment_variables": dict(base_env),
    }

    results = [run_case(spec, base_manifest) for spec in CASE_SPECS]
    environment_policy = {
        **ENVIRONMENT_POLICY_TEMPLATE,
        "declared_variables": dict(base_env),
        "effective_environment_variables": dict(base_env),
    }
    execution_environment = {
        **EXECUTION_ENVIRONMENT_TEMPLATE,
        "env": dict(base_env),
        "environment_policy": environment_policy,
        "stdin": "subprocess.DEVNULL",
    }
    index = {
        "schema_version": 1,
        "wave": "m0-diagnostics-wave2",
        "upstream_commit": UPSTREAM_COMMIT,
        "image": IMAGE,
        "product_compatibility_evidence": False,
        "evidence_status": "oracle_reference",
        "file_tree_semantics": FILE_TREE_SEMANTICS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "execution_environment": execution_environment,
        "execution_manifest": base_manifest,
        "effective_environment_variables": dict(base_env),
        "environment_policy": environment_policy,
        "cleanup": CLEANUP_POLICY,
        "stdin": "subprocess.DEVNULL",
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
                "execution_manifest": result["execution_manifest"],
                "stdin": "subprocess.DEVNULL",
            }
            for result in results
        ],
    }
    (WAVE_ROOT / "result.json").write_text(canonical_json(index))
    print(
        f"WAVE2_INDEX cases={len(results)} "
        f"sha256={sha256_file(WAVE_ROOT / 'result.json')} "
        f"perl={base_manifest['runtime_versions']['perl']} "
        f"python={base_manifest['runtime_versions']['python']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
