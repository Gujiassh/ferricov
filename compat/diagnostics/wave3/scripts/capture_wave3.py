#!/usr/bin/env python3
"""Capture M0 diagnostics wave3 Oracle reference observations.

Wave3 extends the accepted wave1 provenance contract:
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
# and wave3 adds independent executable depth).
# Lane modules supply CASE_SPECS. Composed in main() after Wave3CaptureError exists.
CASE_SPECS: list[dict[str, Any]] = []





class Wave3CaptureError(RuntimeError):
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
        raise Wave3CaptureError(
            f"docker ps observer timed out while checking {name}"
        ) from error
    except OSError as error:
        raise Wave3CaptureError(
            f"docker ps observer failed to execute while checking {name}: {error}"
        ) from error
    if observed.returncode != 0:
        raise Wave3CaptureError(
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
            raise Wave3CaptureError(
                f"docker rm -f failed and container still present: {name} "
                f"rc={removal.returncode} stderr={removal.stderr!r}"
            )
    absent = container_absent(name)
    if not absent:
        raise Wave3CaptureError(f"wave3 container survived cleanup: {name}")
    if not direct_child_reaped:
        raise Wave3CaptureError(
            f"wave3 docker CLI child was not reaped before cleanup confirmation: {name}"
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
    container_name = "ferricov-diag-wave3-env-probe"
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
            raise Wave3CaptureError("effective environment probe timed out") from error
        except OSError as error:
            raise Wave3CaptureError(
                f"effective environment probe failed to execute: {error}"
            ) from error
    finally:
        force_remove_container(container_name, direct_child_reaped=True)

    if completed is None:
        raise Wave3CaptureError("effective environment probe produced no result")
    if completed.returncode != 0:
        raise Wave3CaptureError(
            "failed to probe effective command environment: "
            f"rc={completed.returncode} stderr={completed.stderr!r}"
        )
    effective: dict[str, str] = {}
    for entry in completed.stdout.split(b"\0"):
        if not entry:
            continue
        if b"=" not in entry:
            raise Wave3CaptureError(f"malformed env probe entry: {entry!r}")
        key, value = entry.split(b"=", 1)
        effective[key.decode("ascii")] = value.decode("ascii")
    if effective != env:
        raise Wave3CaptureError(
            "effective command environment differs from declared clean env: "
            f"observed={effective!r} declared={env!r}"
        )
    return effective


def _decode_probe_text(data: bytes) -> str:
    return data.decode("utf-8", "replace").strip()


def probe_execution_manifest(
    effective_environment_variables: dict[str, str],
) -> dict[str, Any]:
    container_name = "ferricov-diag-wave3-manifest-probe"
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
            raise Wave3CaptureError("execution-manifest probe timed out") from error
        except OSError as error:
            raise Wave3CaptureError(
                f"execution-manifest probe failed to execute: {error}"
            ) from error
    finally:
        force_remove_container(container_name, direct_child_reaped=True)

    if completed is None:
        raise Wave3CaptureError("execution-manifest probe produced no result")
    if completed.returncode != 0:
        raise Wave3CaptureError(
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
            raise Wave3CaptureError(f"required wave3 executable unavailable: {tool}")
    if manifest["locale"] != "C" or manifest["lc_all"] != "C":
        raise Wave3CaptureError(
            f"locale provenance drift: locale={manifest['locale']!r} lc_all={manifest['lc_all']!r}"
        )
    if manifest["timezone"] != "UTC":
        raise Wave3CaptureError(f"timezone provenance drift: {manifest['timezone']!r}")
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


def skip_wave3_emptyhome_marker(path: Path, *, root: Path, context: str) -> bool:
    """Skip only regular zero-byte emptyhome/.gitkeep; reject other markers.

    Consult before is_file() so symlink/broken-symlink markers fail closed.
    """
    if path.name not in {".gitkeep", ".keep"}:
        return False
    rel = path.relative_to(root).as_posix()
    if root.name == "emptyhome":
        allowed = rel == ".gitkeep"
    else:
        allowed = rel == "emptyhome/.gitkeep"
    if path.name == ".keep" or not allowed:
        raise SystemExit(
            f"wave3 directory marker only allowed as zero-byte emptyhome/.gitkeep ({context}): {rel}"
        )
    if path.is_symlink():
        raise SystemExit(
            f"wave3 emptyhome/.gitkeep must not be a symlink ({context}): {rel}"
        )
    if not path.is_file():
        raise SystemExit(
            f"wave3 emptyhome/.gitkeep must be a regular zero-byte file ({context}): {rel}"
        )
    if path.read_bytes() != b"":
        raise SystemExit(
            f"wave3 emptyhome/.gitkeep must be zero bytes ({context}): {rel}"
        )
    return True


def validate_emptyhome_fixture_dir(src: Path, *, context: str) -> None:
    if not src.is_dir():
        raise SystemExit(f"wave3 emptyhome fixture missing directory ({context}): {src}")
    marker = src / ".gitkeep"
    if marker.exists(follow_symlinks=False) or marker.is_symlink():
        skip_wave3_emptyhome_marker(marker, root=src, context=context)
    else:
        raise SystemExit(f"wave3 emptyhome fixture missing .gitkeep ({context})")
    extras = [p for p in src.iterdir() if p.name != ".gitkeep"]
    if extras:
        raise SystemExit(
            f"wave3 emptyhome fixture must contain only .gitkeep ({context}): "
            f"{[p.name for p in extras]}"
        )


def stage(work: Path, fixtures: list[str], chmod_map: dict[str, int] | None) -> None:
    """Stage fixtures for Oracle execution.

    emptyhome is retained in Git with .gitkeep, but runtime HOME must be empty:
    validate the source marker then stage an empty directory without copying it.
    """
    work.mkdir(parents=True)
    for name in fixtures:
        src = FIXTURES / name
        if not src.exists():
            raise SystemExit(f"missing fixture: {name}")
        dest = work / name
        if name == "emptyhome":
            validate_emptyhome_fixture_dir(src, context=f"stage-source:{work.name}")
            dest.mkdir(parents=True)
            # Do not copy .gitkeep into runtime HOME.
            if any(dest.iterdir()):
                raise SystemExit(f"wave3 staged emptyhome is not empty: {dest}")
            continue
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
        if skip_wave3_emptyhome_marker(path, root=work, context=f"case:{work.name}"):
            continue
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
            if name == "emptyhome":
                validate_emptyhome_fixture_dir(src, context=f"fixture:{name}")
            for path in sorted(src.rglob("*")):
                if skip_wave3_emptyhome_marker(
                    path, root=src, context=f"fixture:{name}"
                ):
                    continue
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
    container_name = f"ferricov-diag-wave3-{spec['id']}"
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
        raise Wave3CaptureError(f"wave3 cleanup not confirmed: {spec['id']}")
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


def require_tracked_emptyhome_fixture() -> None:
    """Fail closed before Docker if tracked emptyhome source evidence is missing.

    emptyhome must already exist as a Git-tracked directory with a regular
    zero-byte .gitkeep marker. Capture must never synthesize that marker.
    """
    validate_emptyhome_fixture_dir(
        FIXTURES / "emptyhome",
        context="capture-preflight",
    )



def load_lane_case_specs() -> list[dict[str, Any]]:
    """Compose lane A/B CASE_SPECS. Lanes own their modules only."""
    import importlib.util

    scripts = Path(__file__).resolve().parent
    specs: list[dict[str, Any]] = []
    for name in ("lane_a_cases", "lane_b_cases"):
        path = scripts / f"{name}.py"
        mod_name = f"ferricov_wave3_{name}"
        mod_spec = importlib.util.spec_from_file_location(mod_name, path)
        if mod_spec is None or mod_spec.loader is None:
            raise Wave3CaptureError(f"cannot load lane module: {path}")
        module = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(module)
        lane_specs = getattr(module, "CASE_SPECS", None)
        if not isinstance(lane_specs, list):
            raise Wave3CaptureError(f"{name}.CASE_SPECS must be a list")
        specs.extend(lane_specs)
    for entry in specs:
        for pid in entry.get("planned_case_ids", []):
            if str(pid).endswith("-FERRICOV-001"):
                raise Wave3CaptureError(
                    f"Ferricov-parity planned ID must remain unbound: {pid}"
                )
    ids = [e.get("id") for e in specs]
    if len(ids) != len(set(ids)):
        raise Wave3CaptureError("duplicate wave3 case ids")
    return specs



def main() -> int:
    global CASE_SPECS
    CASE_SPECS = load_lane_case_specs()
    if not CASE_SPECS:
        raise Wave3CaptureError(
            "wave3 CASE_SPECS empty: implement lane_a_cases.py and/or lane_b_cases.py"
        )

    # Create noread.rc fixture if missing (empty file; chmod applied per case).
    noread = FIXTURES / "noread.rc"
    if not noread.exists():
        noread.write_text("# unreadable config placeholder\n", encoding="utf-8")
    # emptyhome is tracked source evidence only; never mkdir/write .gitkeep here.
    # emptyhome only required when a case fixtures list includes it
    if any("emptyhome" in (spec.get("fixtures") or []) for spec in CASE_SPECS):
        require_tracked_emptyhome_fixture()

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
        "wave": "m0-diagnostics-wave3",
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
        f"WAVE3_INDEX cases={len(results)} "
        f"sha256={sha256_file(WAVE_ROOT / 'result.json')} "
        f"perl={base_manifest['runtime_versions']['perl']} "
        f"python={base_manifest['runtime_versions']['python']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
