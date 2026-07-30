#!/usr/bin/env python3
"""Capture M0-RSRC-MEASURE-001 in the content-addressed LCOV 2.5 Oracle."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import contract
import generate


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path(__file__).parent / "results/oracle-x86_64-linux-20260729"
CONTROL_TIMEOUT_SECONDS = 15


class ResourceCaptureError(RuntimeError):
    pass


class ProfileCaptureFailure(ResourceCaptureError):
    def __init__(self, failure_class: str, reason: str, *, timed_out: bool = False) -> None:
        super().__init__(reason)
        self.failure_class = failure_class
        self.timed_out = timed_out


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def artifact(root: Path, path: Path) -> dict[str, Any]:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if not resolved.is_file() or not resolved.is_relative_to(resolved_root):
        raise ResourceCaptureError(f"resource artifact escapes result root: {path}")
    return {
        "path": resolved.relative_to(resolved_root).as_posix(),
        "bytes": resolved.stat().st_size,
        "sha256": contract.sha256_file(resolved),
    }


def repository_artifact(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file() or not resolved.is_relative_to(ROOT.resolve()):
        raise ResourceCaptureError(f"resource repository artifact escapes root: {path}")
    return {
        "path": resolved.relative_to(ROOT.resolve()).as_posix(),
        "bytes": resolved.stat().st_size,
        "sha256": contract.sha256_file(resolved),
    }


def run_checked(arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            timeout=CONTROL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise ResourceCaptureError(f"command timed out: {arguments!r}") from error
    if completed.returncode != 0:
        raise ResourceCaptureError(
            f"command failed: {arguments!r} status={completed.returncode} "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    return completed


def verify_runtime_identity(document: dict[str, Any]) -> None:
    identity = document["oracle_identity"]
    image = identity["image_sha256"]
    inspected = run_checked(["docker", "image", "inspect", "--format", "{{.Id}}", image])
    if inspected.stdout.decode("ascii").strip() != image:
        raise ResourceCaptureError("resource Oracle image does not resolve to its immutable ID")
    observed = run_checked([
        "docker", "run", "--rm", "--network", "none", "--entrypoint", "sha256sum",
        image, identity["lcov_path"],
    ]).stdout.decode("ascii").split()[0]
    if f"sha256:{observed}" != identity["lcov_sha256"]:
        raise ResourceCaptureError("resource Oracle lcov executable identity drift")


def require_empty_output(path: Path) -> None:
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ResourceCaptureError(f"resource output directory is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def container_absent(name: str) -> bool:
    observed = run_checked([
        "docker", "ps", "-a", "--format", "{{.Names}}",
    ]).stdout.decode("utf-8")
    return name not in observed.splitlines()


def cleanup_container(name: str) -> bool:
    if container_absent(name):
        return True
    removal = subprocess.run(
        ["docker", "rm", "-f", name],
        check=False,
        capture_output=True,
        timeout=CONTROL_TIMEOUT_SECONDS,
    )
    absent = container_absent(name)
    if not absent:
        raise ResourceCaptureError(f"resource Docker container survived cleanup: {name}")
    if removal.returncode != 0:
        raise ResourceCaptureError(
            f"resource Docker cleanup failed: {name} status={removal.returncode} "
            f"stderr={removal.stderr!r}"
        )
    return True


def _cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" in line and line.split(":", 1)[0].strip() in {"model name", "Hardware"}:
                value = line.split(":", 1)[1].strip()
                if value:
                    return value
    value = platform.processor().strip()
    return value or "unknown"


def host_runtime_identity() -> dict[str, Any]:
    logical_cpus = os.cpu_count()
    if logical_cpus is None or logical_cpus < 1:
        raise ResourceCaptureError("cannot determine host logical CPU count")
    try:
        memory_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (OSError, ValueError) as error:
        raise ResourceCaptureError("cannot determine host memory size") from error
    if memory_bytes < 1:
        raise ResourceCaptureError("host memory size is invalid")
    docker_version = run_checked([
        "docker", "version", "--format", "{{.Server.Version}}",
    ]).stdout.decode("utf-8").strip()
    docker_info = run_checked([
        "docker", "info", "--format", "{{.CgroupVersion}}|{{.CgroupDriver}}",
    ]).stdout.decode("utf-8").strip().split("|", 1)
    if not docker_version or len(docker_info) != 2 or not all(docker_info):
        raise ResourceCaptureError("Docker runtime identity is incomplete")
    return {
        "operating_system": platform.system(),
        "architecture": platform.machine(),
        "kernel_release": platform.release(),
        "cpu_model": _cpu_model(),
        "logical_cpu_count": logical_cpus,
        "memory_bytes": memory_bytes,
        "docker_server_version": docker_version,
        "docker_cgroup_version": docker_info[0],
        "docker_cgroup_driver": docker_info[1],
    }


def _failure_artifacts(
    output_root: Path,
    profile_id: str,
    generated_input: bytes,
    metrics_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    docker_stdout: bytes,
    docker_stderr: bytes,
) -> tuple[Path, dict[str, dict[str, Any]]]:
    failure_root = output_root / "failures" / profile_id
    failure_root.mkdir(parents=True, exist_ok=False)
    retained: dict[str, dict[str, Any]] = {}

    input_path = failure_root / "input.info"
    input_path.write_bytes(generated_input)
    retained["generated_input"] = artifact(output_root, input_path)

    for role, source, filename in (
        ("raw_metrics", metrics_path, "metrics.json"),
        ("stdout", stdout_path, "stdout.bin"),
        ("stderr", stderr_path, "stderr.bin"),
    ):
        if source.is_file() and not source.is_symlink():
            destination = failure_root / filename
            shutil.copyfile(source, destination)
            retained[role] = artifact(output_root, destination)

    for role, content, filename in (
        ("docker_stdout", docker_stdout, "docker-stdout.bin"),
        ("docker_stderr", docker_stderr, "docker-stderr.bin"),
    ):
        destination = failure_root / filename
        destination.write_bytes(content)
        retained[role] = artifact(output_root, destination)
    return failure_root, retained


def _timeout_stream(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")


def capture_profile(
    output_root: Path,
    contract_document: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    work_directory = Path(tempfile.mkdtemp(prefix=f"ferricov-resource-{profile['id']}-work-"))
    evidence_directory = Path(tempfile.mkdtemp(prefix=f"ferricov-resource-{profile['id']}-evidence-"))
    container_name = f"ferricov-resource-{os.getpid()}-{profile['sequence']}"
    input_path = work_directory / "input.info"
    metrics_path = evidence_directory / "metrics.json"
    stdout_path = evidence_directory / "stdout.bin"
    stderr_path = evidence_directory / "stderr.bin"
    generated_input: bytes | None = None
    metrics_document: dict[str, Any] | None = None
    docker_command: list[str] = []
    docker_returncode: int | None = None
    docker_stdout = b""
    docker_stderr = b""
    operation_error: Exception | None = None
    sample: dict[str, Any] | None = None
    timed_out = False

    policy = contract_document["execution_policy"]
    identity = contract_document["oracle_identity"]
    try:
        definition = generate.PROFILE_BY_ID[profile["id"]]
        generated_shape = generate.generate_and_analyze(definition, input_path)
        generated_input = input_path.read_bytes()
        if generated_shape != profile["input"]:
            raise ProfileCaptureFailure(
                "generated_input_drift",
                f"resource generated input drift: {profile['id']}",
            )

        environment_arguments = [f"{key}={value}" for key, value in policy["environment"].items()]
        host_user = f"{os.getuid()}:{os.getgid()}"
        docker_command = [
            "docker", "run", "--rm", "--name", container_name, "--network", "none",
            "--user", identity["user"], "--workdir", "/work",
            "--memory", str(policy["container_memory_bytes"]),
            "--pids-limit", str(policy["container_pids"]),
            "--volume", f"{work_directory}:/work",
            "--volume", f"{evidence_directory}:/evidence",
            "--volume", f"{contract.MEASUREMENT_TOOL_PATH}:/ferricov/measure.py:ro",
            "--entrypoint", "python3", identity["image_sha256"],
            "/ferricov/measure.py", "--metrics", "/evidence/metrics.json",
            "--stdout", "/evidence/stdout.bin", "--stderr", "/evidence/stderr.bin",
            "--chown", host_user, "--", "/usr/bin/env", "-i", *environment_arguments,
            *policy["command"],
        ]
        try:
            docker = subprocess.run(
                docker_command,
                check=False,
                capture_output=True,
                timeout=policy["timeout_seconds"],
            )
        except subprocess.TimeoutExpired as error:
            timed_out = True
            docker_stdout = _timeout_stream(error.stdout)
            docker_stderr = _timeout_stream(error.stderr)
            raise ProfileCaptureFailure(
                "host_deadline_exceeded",
                f"resource host deadline exceeded: {profile['id']}",
                timed_out=True,
            ) from error
        except OSError as error:
            raise ProfileCaptureFailure(
                "docker_wrapper_failure",
                f"resource Docker wrapper failed: {profile['id']}: {error}",
            ) from error

        docker_returncode = docker.returncode
        docker_stdout = docker.stdout
        docker_stderr = docker.stderr
        if docker_stdout or docker_stderr:
            raise ProfileCaptureFailure(
                "docker_wrapper_stream_pollution",
                f"resource measurement wrapper polluted Docker streams: {profile['id']}",
            )
        missing = [
            path.name
            for path in (metrics_path, stdout_path, stderr_path)
            if not path.is_file() or path.is_symlink()
        ]
        if missing:
            raise ProfileCaptureFailure(
                "measurement_artifact_missing",
                f"resource measurement artifacts missing: {profile['id']}: {','.join(missing)}",
            )
        try:
            loaded_metrics = json.loads(metrics_path.read_text(encoding="ascii"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ProfileCaptureFailure(
                "measurement_metrics_invalid",
                f"resource metrics cannot be parsed: {profile['id']}",
            ) from error
        if not isinstance(loaded_metrics, dict):
            raise ProfileCaptureFailure(
                "measurement_metrics_invalid",
                f"resource metrics are not an object: {profile['id']}",
            )
        metrics_document = loaded_metrics
        exit_code = metrics_document.get("exit_code")
        signal = metrics_document.get("signal")
        if (isinstance(exit_code, int) and signal is None):
            wrapper_code = exit_code
        elif exit_code is None and isinstance(signal, int) and signal > 0:
            wrapper_code = min(255, 128 + signal)
        else:
            raise ProfileCaptureFailure(
                "measurement_outcome_invalid",
                f"resource metrics outcome is invalid: {profile['id']}",
            )
        if docker.returncode != wrapper_code:
            raise ProfileCaptureFailure(
                "docker_wrapper_exit_mismatch",
                f"resource measurement wrapper exit mismatch: {profile['id']}",
            )
        if signal is not None:
            raise ProfileCaptureFailure(
                "oracle_signal",
                f"resource Oracle was signaled: {profile['id']} signal={signal}",
            )
        if exit_code != 0:
            raise ProfileCaptureFailure(
                "oracle_nonzero_exit",
                f"resource Oracle exited nonzero: {profile['id']} exit_code={exit_code}",
            )

        expected = profile["expected_observation"]
        if contract.sha256_file(stdout_path) != expected["stdout"]["sha256"]:
            raise ProfileCaptureFailure(
                "stdout_mismatch",
                f"resource stdout semantic/hash mismatch: {profile['id']}",
            )
        if contract.sha256_file(stderr_path) != expected["stderr"]["sha256"]:
            raise ProfileCaptureFailure(
                "stderr_mismatch",
                f"resource stderr semantic/hash mismatch: {profile['id']}",
            )

        input_after = generate.analyze_input(input_path)
        entries = sorted(
            path.relative_to(work_directory).as_posix()
            for path in work_directory.rglob("*")
            if path != input_path
        )
        sample_root = output_root / "samples" / profile["id"]
        sample_root.mkdir(parents=True, exist_ok=False)
        retained_metrics = sample_root / "metrics.json"
        retained_stdout = sample_root / "stdout.bin"
        retained_stderr = sample_root / "stderr.bin"
        shutil.copyfile(metrics_path, retained_metrics)
        shutil.copyfile(stdout_path, retained_stdout)
        shutil.copyfile(stderr_path, retained_stderr)
        sample = {
            "sequence": profile["sequence"],
            "profile_id": profile["id"],
            "primary_scale_axis": profile["primary_scale_axis"],
            "target": profile["target"],
            "generator_version": profile["generator_version"],
            "profile_seed_sha256": profile["profile_seed_sha256"],
            "input": profile["input"],
            "input_sha256_after": input_after["sha256"],
            "outcome": {
                "exit_code": exit_code,
                "signal": signal,
                "timeout": False,
                "container_exit_code": docker.returncode,
            },
            "metrics": {
                "measurement_backend": metrics_document.get("measurement_backend"),
                "clock": metrics_document.get("clock"),
                "wall_time_ns": metrics_document.get("wall_time_ns"),
                "user_cpu_time_ns": metrics_document.get("user_cpu_time_ns"),
                "system_cpu_time_ns": metrics_document.get("system_cpu_time_ns"),
                "peak_rss_bytes": metrics_document.get("peak_rss_bytes"),
            },
            "raw_metrics": artifact(output_root, retained_metrics),
            "stdout": artifact(output_root, retained_stdout),
            "stderr": artifact(output_root, retained_stderr),
            "unexpected_output_entries": entries,
        }
    except Exception as error:  # Evidence retention converts all post-generation failures.
        operation_error = error

    container_removed = False
    cleanup_errors: list[str] = []
    try:
        container_removed = cleanup_container(container_name)
    except Exception as error:
        cleanup_errors.append(f"container: {type(error).__name__}: {error}")

    effective_error = operation_error
    failure_class = "capture_failure"
    failure_timed_out = timed_out
    if isinstance(operation_error, ProfileCaptureFailure):
        failure_class = operation_error.failure_class
        failure_timed_out = operation_error.timed_out
    if effective_error is None and cleanup_errors:
        effective_error = ResourceCaptureError(cleanup_errors[0])
        failure_class = "container_cleanup_failure"

    failure_root: Path | None = None
    failure_artifacts: dict[str, dict[str, Any]] = {}
    retention_errors: list[str] = []

    def retain_failure(
        retained_metrics: Path,
        retained_stdout: Path,
        retained_stderr: Path,
    ) -> None:
        nonlocal failure_root, failure_artifacts
        assert generated_input is not None
        try:
            failure_root, failure_artifacts = _failure_artifacts(
                output_root,
                profile["id"],
                generated_input,
                retained_metrics,
                retained_stdout,
                retained_stderr,
                docker_stdout,
                docker_stderr,
            )
        except Exception as error:
            retention_errors.append(
                f"failure_artifacts: {type(error).__name__}: {error}"
            )

    try:
        if effective_error is not None and generated_input is not None:
            retain_failure(metrics_path, stdout_path, stderr_path)
    finally:
        for role, directory in (
            ("work_directory", work_directory),
            ("evidence_directory", evidence_directory),
        ):
            try:
                shutil.rmtree(directory, ignore_errors=False)
            except Exception as error:
                cleanup_errors.append(f"{role}: {type(error).__name__}: {error}")

    cleanup = {
        "work_directory_removed": not work_directory.exists(),
        "evidence_directory_removed": not evidence_directory.exists(),
        "container_removed": container_removed,
        "errors": cleanup_errors,
    }
    if effective_error is None and cleanup_errors:
        effective_error = ResourceCaptureError(cleanup_errors[0])
        failure_class = "temporary_cleanup_failure"
        if generated_input is not None:
            sample_root = output_root / "samples" / profile["id"]
            retain_failure(
                sample_root / "metrics.json",
                sample_root / "stdout.bin",
                sample_root / "stderr.bin",
            )

    if effective_error is not None:
        failure_path: Path | None = None
        if generated_input is not None and failure_root is not None:
            failure_document = {
                "schema_version": 1,
                "status": "capture_failed",
                "profile": {
                    "sequence": profile["sequence"],
                    "id": profile["id"],
                    "primary_scale_axis": profile["primary_scale_axis"],
                    "target": profile["target"],
                    "expected_input": profile["input"],
                },
                "failure": {
                    "class": failure_class,
                    "reason": str(effective_error),
                    "exception_type": type(effective_error).__name__,
                },
                "deadline": {
                    "observer": policy["deadline_observer"],
                    "seconds": policy["timeout_seconds"],
                    "expired": failure_timed_out,
                },
                "docker": {
                    "command": docker_command,
                    "container_name": container_name,
                    "returncode": docker_returncode,
                    "timed_out": failure_timed_out,
                },
                "measurement_outcome": None if metrics_document is None else {
                    "exit_code": metrics_document.get("exit_code"),
                    "signal": metrics_document.get("signal"),
                },
                "artifacts": failure_artifacts,
                "post_cleanup": cleanup,
            }
            candidate_failure_path = failure_root / "failure.json"
            try:
                candidate_failure_path.write_text(
                    canonical_json(failure_document),
                    encoding="ascii",
                )
            except Exception as error:
                retention_errors.append(
                    f"failure_manifest: {type(error).__name__}: {error}"
                )
            else:
                failure_path = candidate_failure_path

        diagnostics = [
            f"capture_failure: {type(effective_error).__name__}: {effective_error}"
        ]
        diagnostics.extend(f"retention_failure: {error}" for error in retention_errors)
        diagnostics.extend(f"cleanup_failure: {error}" for error in cleanup_errors)
        if failure_path is not None:
            diagnostics.append(
                f"failure_evidence={failure_path.relative_to(output_root)}"
            )
        elif generated_input is not None:
            diagnostics.append("failure_evidence=not_retained")
        raise ResourceCaptureError("; ".join(diagnostics)) from effective_error

    assert sample is not None
    sample["cleanup"] = {
        "work_directory_removed": cleanup["work_directory_removed"],
        "evidence_directory_removed": cleanup["evidence_directory_removed"],
        "container_removed": cleanup["container_removed"],
    }
    return sample


def capture(output_root: Path) -> Path:
    require_empty_output(output_root)
    contract_document = contract.load_json(contract.OUTPUT_PATH)
    contract.validate_document(contract_document)
    verify_runtime_identity(contract_document)
    host_identity = host_runtime_identity()

    samples = [capture_profile(output_root, contract_document, profile) for profile in contract_document["profiles"]]
    result = {
        "schema_version": 1,
        "result_id": "m0-resource-measurement-oracle",
        "recorded_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "oracle_observed",
        "case_id": contract_document["m0_case_id"],
        "contract": repository_artifact(contract.OUTPUT_PATH),
        "execution_manifest": repository_artifact(contract.MANIFEST_PATH),
        "measurement_tool": repository_artifact(contract.MEASUREMENT_TOOL_PATH),
        "harness_artifacts": contract_document["harness_artifacts"],
        "observed_image_sha256": contract_document["oracle_identity"]["image_sha256"],
        "observed_lcov_sha256": contract_document["oracle_identity"]["lcov_sha256"],
        "host_runtime": host_identity,
        "environment": contract_document["execution_policy"]["environment"],
        "container_policy": {
            "network": contract_document["oracle_identity"]["network"],
            "user": contract_document["oracle_identity"]["user"],
            "memory_bytes": contract_document["execution_policy"]["container_memory_bytes"],
            "pids": contract_document["execution_policy"]["container_pids"],
            "timeout_seconds": contract_document["execution_policy"]["timeout_seconds"],
            "deadline_observer": contract_document["execution_policy"]["deadline_observer"],
            "environment_inheritance": contract_document["execution_policy"]["environment_inheritance"],
        },
        "allocations": contract_document["execution_policy"]["allocations"],
        "samples": samples,
        "totals": {
            "profiles": 13,
            "accepted": 13,
            "nonzero": 0,
            "signaled": 0,
            "timeouts": 0,
        },
        "measurement_interpretation": "single_run_bounded_observations_not_performance_gates",
        "harness_budgets_are_product_limits": False,
        "product_limits_selected": False,
        "product_limit_evidence": [],
        "product_compatibility_evidence": False,
    }
    result_path = output_root / "result.json"
    result_path.write_text(canonical_json(result), encoding="ascii")
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("validate.py")), "--result", str(result_path)],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise ResourceCaptureError("captured resource result failed validation")
    return result_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = capture(args.output.resolve())
    print(f"RESOURCE_CAPTURE_OK result={result_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
