#!/usr/bin/env python3
"""Validate retained raw Oracle correctness baselines and compare replays."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = REPOSITORY_ROOT / "compat/schema"
DEFAULT_BASELINE = (
    REPOSITORY_ROOT
    / "compat/correctness/baselines/m0-cli-oracle-v2.5/result.json"
)
DEFAULT_STATUS = REPOSITORY_ROOT / "compat/fixtures/m0-cli-contract/oracle-baseline-status.json"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
EXPECTED_CASES = 126
TEMP_PATH_PATTERN = re.compile(rb"/tmp/[A-Za-z0-9_-]{10}(?![A-Za-z0-9_-])")
TEMP_PATH_CASE = "m0-core-geninfo-startup-control"


class CorrectnessValidationError(ValueError):
    """A raw Oracle correctness baseline is structurally or semantically invalid."""


def sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CorrectnessValidationError(f"cannot load JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise CorrectnessValidationError(f"JSON document must be an object: {path}")
    return value


def canonical_json(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def validate_canonical(path: Path, document: dict[str, Any]) -> None:
    if path.read_text(encoding="utf-8") != canonical_json(document):
        raise CorrectnessValidationError(f"JSON is not canonical: {path}")


def schema(name: str) -> dict[str, Any]:
    document = load_json(SCHEMA_ROOT / name)
    Draft202012Validator.check_schema(document)
    return document


def validate_schema(
    document: dict[str, Any],
    schema_document: dict[str, Any],
    label: str,
    *,
    registry: Registry | None = None,
) -> None:
    validator = Draft202012Validator(
        schema_document,
        format_checker=FormatChecker(),
        registry=registry or Registry(),
    )
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = [
            f"{label} schema {'.'.join(str(part) for part in error.absolute_path) or '<root>'}: "
            f"{error.message}"
            for error in errors
        ]
        raise CorrectnessValidationError("\n".join(messages))


def observation_registry() -> Registry:
    differential = schema("differential-result.schema.json")
    return Registry().with_resource(
        differential["$id"],
        Resource.from_contents(differential),
    )


def safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and value == path.as_posix()
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def artifact_path(root: Path, reference: dict[str, Any]) -> Path:
    value = reference["path"]
    if not safe_relative_path(value):
        raise CorrectnessValidationError(f"unsafe artifact path: {value}")
    current = root
    for part in PurePosixPath(value).parts:
        current = current / part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise CorrectnessValidationError(
                f"artifact does not exist: {value}"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            raise CorrectnessValidationError(f"artifact path contains a symlink: {value}")
    if not current.is_file():
        raise CorrectnessValidationError(f"artifact is not a regular file: {value}")
    content = current.read_bytes()
    if len(content) != reference["bytes"]:
        raise CorrectnessValidationError(f"artifact byte count mismatch: {value}")
    actual = sha256_bytes(content)
    if actual != reference["sha256"]:
        raise CorrectnessValidationError(
            f"artifact hash mismatch for {value}: "
            f"expected {reference['sha256']}, found {actual}"
        )
    return current


def raw_artifact(
    case_root: Path,
    value: str,
    expected_path: str,
    expected_sha256: str,
    expected_bytes: int,
) -> Path:
    if value != expected_path:
        raise CorrectnessValidationError(
            f"case artifact path mismatch: expected {expected_path}, found {value}"
        )
    reference = {
        "path": value,
        "sha256": f"sha256:{expected_sha256}",
        "bytes": expected_bytes,
    }
    return artifact_path(case_root, reference)


def manifest_module() -> Any:
    path = REPOSITORY_ROOT / "compat/manifests/validate.py"
    spec = importlib.util.spec_from_file_location("ferricov_manifest_validate", path)
    if spec is None or spec.loader is None:
        raise CorrectnessValidationError("could not load execution manifest validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_manifest(path: Path) -> dict[str, Any]:
    document = load_json(path)
    validator = manifest_module()
    validator.validate_document(
        document,
        schema("execution-manifest.schema.json"),
        REPOSITORY_ROOT,
    )
    if document["evidence"]["scope"] == "harness_self_test":
        raise CorrectnessValidationError(
            "harness self-test manifest cannot identify an Oracle baseline"
        )
    return document


def resolve_clean_environment(case_contract: dict[str, Any]) -> dict[str, str]:
    clean = case_contract["clean_environment"]
    if clean["inherit_parent"]:
        raise CorrectnessValidationError("baseline environment cannot inherit parent")
    resolved: dict[str, str] = {}
    for key, value in clean["allowlist"].items():
        value = value.replace("{workdir}", "/work")
        if "{" in value or "}" in value:
            raise CorrectnessValidationError(
                f"unresolved clean-environment placeholder: {key}"
            )
        resolved[key] = value
    return resolved


def executable_map(manifest: dict[str, Any]) -> dict[str, str]:
    values = manifest["executables"]
    result = {entry["name"]: entry["sha256"] for entry in values}
    if len(result) != len(values):
        raise CorrectnessValidationError("duplicate executable in execution manifest")
    return result


def validate_file_tree(path: Path, run: dict[str, Any]) -> None:
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CorrectnessValidationError(f"invalid file-tree JSON: {path}") from error
    if not isinstance(entries, list):
        raise CorrectnessValidationError("file-tree artifact must be an array")
    keys = []
    output_bytes = 0
    output_files = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise CorrectnessValidationError("file-tree entry must be an object")
        key = entry.get("path_bytes_hex")
        if not isinstance(key, str):
            raise CorrectnessValidationError("file-tree entry lacks path_bytes_hex")
        keys.append(key)
        if entry.get("kind") == "file":
            size = entry.get("bytes")
            if not isinstance(size, int) or size < 0:
                raise CorrectnessValidationError("file-tree file has invalid byte count")
            output_bytes += size
            output_files += 1
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise CorrectnessValidationError("file-tree entries are not sorted and unique")
    metrics = run["metrics"]
    if metrics["output_bytes"] != output_bytes or metrics["output_files"] != output_files:
        raise CorrectnessValidationError("file-tree totals do not match retained metrics")


def validate_run(case_root: Path, run: dict[str, Any]) -> None:
    if (run["exit_code"] is None) == (run["signal"] is None):
        raise CorrectnessValidationError(
            "reference run must contain exactly one of exit_code or signal"
        )
    stdout = raw_artifact(
        case_root,
        run["stdout_artifact"],
        "reference/stdout.bin",
        run["stdout_sha256"],
        run["stdout_bytes"],
    )
    stderr = raw_artifact(
        case_root,
        run["stderr_artifact"],
        "reference/stderr.bin",
        run["stderr_sha256"],
        run["stderr_bytes"],
    )
    file_tree = raw_artifact(
        case_root,
        run["file_tree_artifact"],
        "reference/file-tree.json",
        run["file_tree_sha256"],
        run["file_tree_bytes"],
    )
    if stdout.stat().st_size != run["stdout_bytes"]:
        raise CorrectnessValidationError("stdout byte count changed during validation")
    if stderr.stat().st_size != run["stderr_bytes"]:
        raise CorrectnessValidationError("stderr byte count changed during validation")
    validate_file_tree(file_tree, run)

    timeout = run["timeout"]
    cleanup = run["cleanup"]
    if timeout["expired"]:
        raise CorrectnessValidationError("qualified Oracle observation timed out")
    if timeout["termination_signal_sent"] is not None:
        raise CorrectnessValidationError("non-timeout observation sent termination signal")
    if not cleanup["direct_child_reaped"] or cleanup["container_absent"] is not True:
        raise CorrectnessValidationError(
            "qualified Oracle observation lacks confirmed container cleanup"
        )
    if cleanup["process_group_empty"] is not None:
        raise CorrectnessValidationError(
            "Docker observation must not claim a host process-group check"
        )
    if run["metrics"]["wall_seconds"] <= 0:
        raise CorrectnessValidationError("Oracle observation wall time must be positive")


def expected_environment(
    launcher: dict[str, Any],
    image_id: str,
) -> dict[str, Any]:
    result = dict(launcher["environment"])
    result["image"] = image_id
    return result


def validate_baseline(path: Path) -> dict[str, Any]:
    path = path.resolve()
    root = path.parent
    document = load_json(path)
    validate_schema(
        document,
        schema("oracle-correctness-baseline.schema.json"),
        "baseline",
    )
    validate_canonical(path, document)

    expected_inputs = {
        "case_contract": "inputs/case-contract.json",
        "execution_manifest": "inputs/execution-manifest.json",
        "launcher": "inputs/launcher.json",
    }
    inputs: dict[str, Path] = {}
    for key, expected in expected_inputs.items():
        reference = document[key]
        if reference["path"] != expected:
            raise CorrectnessValidationError(
                f"{key} artifact must be {expected}, found {reference['path']}"
            )
        inputs[key] = artifact_path(root, reference)

    case_contract = load_json(inputs["case_contract"])
    manifest = validate_manifest(inputs["execution_manifest"])
    launcher = load_json(inputs["launcher"])
    validate_schema(launcher, schema("launcher.schema.json"), "launcher")

    if case_contract["upstream_commit"] != UPSTREAM_COMMIT:
        raise CorrectnessValidationError("case contract upstream commit mismatch")
    base_environment = resolve_clean_environment(case_contract)
    if launcher["environment_variables"] != base_environment:
        raise CorrectnessValidationError(
            "copied launcher does not implement the case-contract environment"
        )

    image_id = manifest["image"]["docker_image_id"]
    if manifest["image"]["reference"] != image_id:
        raise CorrectnessValidationError("baseline manifest image reference is mutable")
    manifest_sha256 = document["execution_manifest"]["sha256"]
    executables = executable_map(manifest)
    expected_observation_environment = expected_environment(launcher, image_id)

    suite_documents: dict[str, dict[str, Any]] = {}
    suite_inputs = case_contract["suites"]
    if len(document["suites"]) != len(suite_inputs):
        raise CorrectnessValidationError("baseline suite artifact count mismatch")
    for suite_input, reference in zip(suite_inputs, document["suites"], strict=True):
        expected_path = f"inputs/suites/{suite_input['suite_id']}.json"
        if reference["path"] != expected_path:
            raise CorrectnessValidationError(
                f"suite artifact path mismatch: {reference['path']}"
            )
        suite_path = artifact_path(root, reference)
        suite = load_json(suite_path)
        validate_schema(suite, schema("suite.schema.json"), "suite")
        if suite["suite_id"] != suite_input["suite_id"]:
            raise CorrectnessValidationError("suite ID differs from case contract")
        if suite["evidence_scope"] != "compatibility":
            raise CorrectnessValidationError("Oracle suite must have compatibility scope")
        if len(suite["cases"]) != suite_input["case_count"]:
            raise CorrectnessValidationError("suite case count differs from case contract")
        expected_hash = f"sha256:{suite_input['sha256']}"
        if reference["sha256"] != expected_hash:
            raise CorrectnessValidationError("suite hash differs from case contract")
        suite_documents[suite["suite_id"]] = suite

    expected_cases: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]] = []
    for suite_input in suite_inputs:
        suite = suite_documents[suite_input["suite_id"]]
        environment = dict(base_environment)
        environment.update(suite_input["environment_overrides"])
        for case in suite["cases"]:
            expected_cases.append((suite, case, environment))

    if len(expected_cases) != EXPECTED_CASES:
        raise CorrectnessValidationError(
            f"expected {EXPECTED_CASES} contract cases, found {len(expected_cases)}"
        )
    if document["case_count"] != len(expected_cases):
        raise CorrectnessValidationError("baseline case_count mismatch")
    if len(document["cases"]) != len(expected_cases):
        raise CorrectnessValidationError("baseline case artifact count mismatch")

    observation_schema = schema("oracle-observation.schema.json")
    registry = observation_registry()
    observed_users: set[str] = set()
    case_ids: set[str] = set()
    for reference, expected in zip(document["cases"], expected_cases, strict=True):
        suite, case, environment = expected
        case_id = case["id"]
        expected_path = f"cases/{case_id}/result.json"
        if reference["path"] != expected_path:
            raise CorrectnessValidationError(
                f"case artifact path mismatch: expected {expected_path}, "
                f"found {reference['path']}"
            )
        observation_path = artifact_path(root, reference)
        observation = load_json(observation_path)
        validate_schema(
            observation,
            observation_schema,
            f"observation {case_id}",
            registry=registry,
        )
        validate_canonical(observation_path, observation)
        if observation["suite_id"] != suite["suite_id"] or observation["case_id"] != case_id:
            raise CorrectnessValidationError(f"observation identity mismatch: {case_id}")
        if case_id in case_ids:
            raise CorrectnessValidationError(f"duplicate observation case ID: {case_id}")
        case_ids.add(case_id)
        for field in ("surface", "command", "arguments", "fixture"):
            if observation[field] != case[field]:
                raise CorrectnessValidationError(
                    f"observation {case_id} differs from suite field {field}"
                )
        if observation["comparison_contract"] != case["comparisons"]:
            raise CorrectnessValidationError(
                f"observation comparison contract mismatch: {case_id}"
            )
        if observation["effective_environment_variables"] != environment:
            raise CorrectnessValidationError(
                f"observation environment mismatch: {case_id}"
            )
        if observation["environment"] != expected_observation_environment:
            raise CorrectnessValidationError(
                f"observation platform environment mismatch: {case_id}"
            )
        if observation["execution_manifest_sha256"] != manifest_sha256:
            raise CorrectnessValidationError(
                f"observation manifest identity mismatch: {case_id}"
            )
        identity = observation["oracle_identity"]
        if identity["kind"] != "docker_image":
            raise CorrectnessValidationError("Oracle observation is not a Docker image")
        if identity["container_image_sha256"] != image_id:
            raise CorrectnessValidationError(
                f"observation image identity mismatch: {case_id}"
            )
        if identity["executable_sha256"] != executables.get(case["command"]):
            raise CorrectnessValidationError(
                f"observation executable identity mismatch: {case_id}"
            )
        observed_users.add(observation["execution"]["user"])
        validate_run(observation_path.parent, observation["reference_run"])

    if len(case_ids) != EXPECTED_CASES:
        raise CorrectnessValidationError("baseline case IDs are not globally unique")
    if len(observed_users) != 1:
        raise CorrectnessValidationError("baseline observations used multiple execution users")
    return document


def validate_status(path: Path = DEFAULT_STATUS) -> dict[str, Any]:
    """Validate the generated status record and its committed baseline binding."""
    path = path.resolve()
    document = load_json(path)
    validate_schema(
        document,
        schema("oracle-baseline-status.schema.json"),
        "baseline status",
    )
    validate_canonical(path, document)

    baseline_reference = document["baseline"]
    baseline_path = artifact_path(REPOSITORY_ROOT, baseline_reference)
    if baseline_path != DEFAULT_BASELINE.resolve():
        raise CorrectnessValidationError("baseline status points at an unexpected baseline")
    baseline = validate_baseline(baseline_path)
    if document["execution_manifest_sha256"] != baseline["execution_manifest"]["sha256"]:
        raise CorrectnessValidationError("baseline status manifest hash does not match baseline")
    manifest = load_json(baseline_path.parent / "inputs/execution-manifest.json")
    if document["oracle_image_identity"] != manifest["image"]["docker_image_id"]:
        raise CorrectnessValidationError("baseline status image identity does not match manifest")
    if document["case_count"] != baseline["case_count"]:
        raise CorrectnessValidationError("baseline status case count does not match baseline")
    return document


def semantic_artifact_sha256(
    case_id: str,
    case_root: Path,
    run: dict[str, Any],
    field: str,
) -> str:
    artifact = artifact_path(
        case_root,
        {
            "path": run[f"{field}_artifact"],
            "sha256": f"sha256:{run[f'{field}_sha256']}",
            "bytes": run[f"{field}_bytes"],
        },
    )
    content = artifact.read_bytes()
    if case_id == TEMP_PATH_CASE and field == "stderr":
        # Perl's tempfile() name is intentionally random on this failure path.
        content = TEMP_PATH_PATTERN.sub(b"/tmp/<oracle-temp>", content)
    return sha256_bytes(content)


def semantic_fingerprint(path: Path) -> dict[str, tuple[Any, ...]]:
    document = validate_baseline(path)
    root = path.resolve().parent
    fingerprints: dict[str, tuple[Any, ...]] = {}
    for reference in document["cases"]:
        observation_path = artifact_path(root, reference)
        observation = load_json(observation_path)
        case_root = observation_path.parent
        case_id = observation["case_id"]
        run = observation["reference_run"]
        fingerprints[case_id] = (
            observation["suite_id"],
            observation["command"],
            tuple(observation["arguments"]),
            run["exit_code"],
            run["signal"],
            semantic_artifact_sha256(case_id, case_root, run, "stdout"),
            semantic_artifact_sha256(case_id, case_root, run, "stderr"),
            run["file_tree_sha256"],
        )
    return fingerprints


def compare_baselines(reference: Path, replay: Path) -> None:
    expected = semantic_fingerprint(reference)
    actual = semantic_fingerprint(replay)
    if expected != actual:
        missing = sorted(expected.keys() - actual.keys())
        added = sorted(actual.keys() - expected.keys())
        changed = sorted(
            case_id
            for case_id in expected.keys() & actual.keys()
            if expected[case_id] != actual[case_id]
        )
        raise CorrectnessValidationError(
            "Oracle baseline replay mismatch: "
            f"missing={missing} added={added} changed={changed}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, nargs="?", default=DEFAULT_BASELINE)
    parser.add_argument("--compare", type=Path)
    parser.add_argument(
        "--skip-status",
        action="store_true",
        help="validate a newly recorded baseline before its status record is updated",
    )
    args = parser.parse_args()

    try:
        document = validate_baseline(args.baseline)
        if not args.skip_status and args.baseline.resolve() == DEFAULT_BASELINE.resolve():
            validate_status()
        if args.compare is not None:
            compare_baselines(args.baseline, args.compare)
    except (CorrectnessValidationError, KeyError, TypeError, OSError) as error:
        print(f"Oracle correctness validation failed: {error}", file=sys.stderr)
        return 1

    print(
        "ORACLE_CORRECTNESS_BASELINE_OK "
        f"path={args.baseline.resolve()} "
        f"cases={document['case_count']} "
        f"image={load_json(args.baseline.resolve().parent / 'inputs/execution-manifest.json')['image']['docker_image_id']} "
        f"compare={'passed' if args.compare is not None else 'not_requested'} "
        "product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
