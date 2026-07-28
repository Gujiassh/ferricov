#!/usr/bin/env python3
"""Validate Ferricov benchmark suites, raw samples, and baseline results."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = REPOSITORY_ROOT / "compat/schema"


class BenchmarkValidationError(ValueError):
    """A benchmark contract or retained result is invalid."""


def sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BenchmarkValidationError(f"JSON document must be an object: {path}")
    return value


def _canonical_json(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and value == path.as_posix()
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _schema(name: str) -> dict[str, Any]:
    schema = _load_json(SCHEMA_ROOT / name)
    Draft202012Validator.check_schema(schema)
    return schema


def _validate_schema(document: dict[str, Any], name: str) -> None:
    validator = Draft202012Validator(_schema(name), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = [
            f"schema {'.'.join(str(part) for part in error.absolute_path) or '<root>'}: "
            f"{error.message}"
            for error in errors
        ]
        raise BenchmarkValidationError("\n".join(messages))


def _manifest_module() -> Any:
    path = REPOSITORY_ROOT / "compat/manifests/validate.py"
    spec = importlib.util.spec_from_file_location("ferricov_manifest_validate", path)
    if spec is None or spec.loader is None:
        raise BenchmarkValidationError("could not load execution manifest validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inventory_entries() -> dict[str, dict[str, Any]]:
    inventory = _load_json(REPOSITORY_ROOT / "compat/inventory/v2.5.json")
    entries: dict[str, dict[str, Any]] = {}

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("id"), str):
                entries[value["id"]] = value
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(inventory)
    return entries


def validate_suite(path: Path) -> dict[str, Any]:
    path = path.resolve()
    document = _load_json(path)
    _validate_schema(document, "benchmark-suite.schema.json")
    if path.read_text(encoding="utf-8") != _canonical_json(document):
        raise BenchmarkValidationError(f"suite is not canonical JSON: {path}")

    tool = document["measurement_tool"]
    if not _safe_relative_path(tool["path"]):
        raise BenchmarkValidationError("measurement tool path is unsafe")
    tool_path = REPOSITORY_ROOT / tool["path"]
    if not tool_path.is_file() or sha256_file(tool_path) != tool["sha256"]:
        raise BenchmarkValidationError("measurement tool hash mismatch")

    ids: set[str] = set()
    families: set[str] = set()
    inventory = _inventory_entries()
    manifest = _manifest_module()
    for case in document["cases"]:
        if case["id"] in ids:
            raise BenchmarkValidationError(f"duplicate benchmark case: {case['id']}")
        ids.add(case["id"])
        families.add(case["family"])
        if case["measured_runs"] % 2 == 0:
            raise BenchmarkValidationError(
                f"measured_runs must be odd for exact integer median: {case['id']}"
            )
        if case["inventory_entries"] != sorted(case["inventory_entries"]):
            raise BenchmarkValidationError(
                f"inventory entries must be sorted: {case['id']}"
            )
        for entry_id in case["inventory_entries"]:
            entry = inventory.get(entry_id)
            if entry is None or entry.get("classification") != "public":
                raise BenchmarkValidationError(
                    f"benchmark inventory entry is not public: {entry_id}"
                )
        fixture = case["fixture"]
        if fixture is not None:
            if not _safe_relative_path(fixture["path"]):
                raise BenchmarkValidationError(f"unsafe fixture path: {fixture['path']}")
            fixture_path = REPOSITORY_ROOT / fixture["path"]
            if not fixture_path.is_dir():
                raise BenchmarkValidationError(f"fixture is not a directory: {fixture['path']}")
            actual = manifest.fixture_tree_sha256(fixture_path)
            if actual != fixture["tree_sha256"]:
                raise BenchmarkValidationError(
                    f"fixture tree hash mismatch for {fixture['path']}: "
                    f"expected {fixture['tree_sha256']}, found {actual}"
                )

    required = {"startup", "tracefile", "operation", "report"}
    if not required.issubset(families):
        missing = ", ".join(sorted(required - families))
        raise BenchmarkValidationError(f"missing representative benchmark families: {missing}")
    return document


def _artifact_path(root: Path, artifact: dict[str, Any]) -> Path:
    value = artifact["path"]
    if not _safe_relative_path(value):
        raise BenchmarkValidationError(f"unsafe artifact path: {value}")
    path = root / value
    if not path.is_file():
        raise BenchmarkValidationError(f"artifact does not exist: {value}")
    content = path.read_bytes()
    if len(content) != artifact["bytes"]:
        raise BenchmarkValidationError(f"artifact byte count mismatch: {value}")
    actual = sha256_bytes(content)
    if actual != artifact["sha256"]:
        raise BenchmarkValidationError(
            f"artifact hash mismatch for {value}: expected {artifact['sha256']}, found {actual}"
        )
    return path


def _repository_artifact(artifact: dict[str, Any]) -> Path:
    return _artifact_path(REPOSITORY_ROOT, artifact)


def validate_correctness_evidence(reference: dict[str, Any] | None) -> None:
    if reference is None:
        raise BenchmarkValidationError("compatibility correctness evidence is required")
    path = _repository_artifact(reference)
    document = _load_json(path)
    _validate_schema(document, "differential-result.schema.json")
    if document.get("evidence_scope") == "harness_self_test":
        raise BenchmarkValidationError("harness self-test cannot unlock a performance gate")
    if document.get("evidence_scope") != "compatibility":
        raise BenchmarkValidationError("correctness evidence must have compatibility scope")
    if document.get("overall_status") != "pass":
        raise BenchmarkValidationError("correctness evidence must pass before performance")
    comparisons = document.get("comparisons")
    if not isinstance(comparisons, list) or not comparisons:
        raise BenchmarkValidationError("correctness evidence has no comparisons")
    if any(comparison.get("status") != "pass" for comparison in comparisons):
        raise BenchmarkValidationError("every correctness comparison must pass")


def _distribution(samples: list[dict[str, Any]], field: str) -> dict[str, int]:
    values = sorted(sample["metrics"][field] for sample in samples)
    return {
        "minimum": values[0],
        "median": values[len(values) // 2],
        "maximum": values[-1],
    }


def _expected_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    output_bytes = {sample["metrics"]["output_bytes"] for sample in samples}
    output_files = {sample["metrics"]["output_files"] for sample in samples}
    if len(output_bytes) != 1 or len(output_files) != 1:
        raise BenchmarkValidationError("measured output size or file count is not stable")
    return {
        "measured_samples": len(samples),
        "wall_time_ns": _distribution(samples, "wall_time_ns"),
        "user_cpu_time_ns": _distribution(samples, "user_cpu_time_ns"),
        "system_cpu_time_ns": _distribution(samples, "system_cpu_time_ns"),
        "peak_rss_bytes": _distribution(samples, "peak_rss_bytes"),
        "output_bytes": output_bytes.pop(),
        "output_files": output_files.pop(),
    }


def validate_result(path: Path) -> dict[str, Any]:
    path = path.resolve()
    root = path.parent
    document = _load_json(path)
    _validate_schema(document, "benchmark-result.schema.json")
    if path.read_text(encoding="utf-8") != _canonical_json(document):
        raise BenchmarkValidationError(f"result is not canonical JSON: {path}")

    suite_path = _repository_artifact(document["suite"])
    suite = validate_suite(suite_path)
    suite_sha256 = document["suite"]["sha256"]
    manifest_path = _repository_artifact(document["execution_manifest"])
    manifest_document = _load_json(manifest_path)
    manifest_module = _manifest_module()
    manifest_schema = _load_json(SCHEMA_ROOT / "execution-manifest.schema.json")
    manifest_module.validate_document(manifest_document, manifest_schema, REPOSITORY_ROOT)
    if manifest_document["evidence"].get("scope") == "harness_self_test":
        raise BenchmarkValidationError("harness self-test manifest is not baseline provenance")
    manifest_sha256 = document["execution_manifest"]["sha256"]
    _repository_artifact(document["measurement_tool"])
    tool_sha256 = document["measurement_tool"]["sha256"]

    case_contracts = {case["id"]: case for case in suite["cases"]}
    samples_by_case: dict[str, list[dict[str, Any]]] = {
        case_id: [] for case_id in case_contracts
    }
    seen_ids: set[str] = set()
    sequences: list[int] = []
    for reference in document["raw_samples"]:
        sample_path = _artifact_path(root, reference)
        sample = _load_json(sample_path)
        _validate_schema(sample, "benchmark-sample.schema.json")
        if sample_path.read_text(encoding="utf-8") != _canonical_json(sample):
            raise BenchmarkValidationError(f"sample is not canonical JSON: {sample_path}")
        if sample["sample_id"] in seen_ids:
            raise BenchmarkValidationError(f"duplicate sample ID: {sample['sample_id']}")
        seen_ids.add(sample["sample_id"])
        sequences.append(sample["sequence"])
        case = case_contracts.get(sample["case_id"])
        if case is None:
            raise BenchmarkValidationError(f"unknown sample case: {sample['case_id']}")
        if sample["suite_id"] != suite["suite_id"] or sample["family"] != case["family"]:
            raise BenchmarkValidationError("sample suite or family mismatch")
        if sample["suite_sha256"] != suite_sha256:
            raise BenchmarkValidationError("sample suite hash mismatch")
        if sample["execution_manifest_sha256"] != manifest_sha256:
            raise BenchmarkValidationError("sample execution manifest hash mismatch")
        if sample["measurement_tool_sha256"] != tool_sha256:
            raise BenchmarkValidationError("sample measurement tool hash mismatch")
        fixture = case["fixture"]
        expected_fixture = None if fixture is None else fixture["tree_sha256"]
        if sample["fixture_tree_sha256"] != expected_fixture:
            raise BenchmarkValidationError("sample fixture hash mismatch")
        if sample["observed_image_sha256"] != manifest_document["image"]["docker_image_id"]:
            raise BenchmarkValidationError("sample image identity does not match manifest")
        executables = {
            entry["name"]: entry["sha256"] for entry in manifest_document["executables"]
        }
        if sample["observed_executable_sha256"] != executables.get(case["command"]):
            raise BenchmarkValidationError("sample executable identity does not match manifest")
        if not sample["outcome_matches_expected"]:
            raise BenchmarkValidationError("sample outcome did not match the approved workload")
        if sample["outcome"] != {"exit_code": case["expected_exit_code"], "signal": None}:
            raise BenchmarkValidationError("sample target outcome mismatch")
        for artifact in sample["artifacts"].values():
            _artifact_path(root, artifact)
        samples_by_case[sample["case_id"]].append(sample)

    if sorted(sequences) != list(range(len(sequences))):
        raise BenchmarkValidationError("sample sequence is not contiguous")

    result_cases = {case["case_id"]: case for case in document["cases"]}
    if set(result_cases) != set(case_contracts):
        raise BenchmarkValidationError("result case set does not match suite")
    for case_id, contract in case_contracts.items():
        samples = samples_by_case[case_id]
        warmups = [sample for sample in samples if sample["phase"] == "warmup"]
        measured = [sample for sample in samples if sample["phase"] == "measured"]
        if len(warmups) != contract["warmup_runs"]:
            raise BenchmarkValidationError(f"warmup sample count mismatch: {case_id}")
        if len(measured) != contract["measured_runs"]:
            raise BenchmarkValidationError(f"measured sample count mismatch: {case_id}")
        result_case = result_cases[case_id]
        if result_case["family"] != contract["family"]:
            raise BenchmarkValidationError(f"result family mismatch: {case_id}")
        if result_case["warmup_samples"] != len(warmups):
            raise BenchmarkValidationError(f"result warmup count mismatch: {case_id}")
        if result_case["measured_samples"] != len(measured):
            raise BenchmarkValidationError(f"result measured count mismatch: {case_id}")
        expected_summary = _expected_summary(measured)
        if result_case["summary"] != expected_summary:
            raise BenchmarkValidationError(f"recomputed summary mismatch: {case_id}")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--suite", type=Path)
    group.add_argument("--result", type=Path)
    args = parser.parse_args()
    try:
        if args.suite is not None:
            document = validate_suite(args.suite)
            print(f"BENCHMARK_SUITE_OK suite={document['suite_id']}")
        else:
            document = validate_result(args.result)
            print(f"BENCHMARK_RESULT_OK result={document['result_id']}")
    except (ValueError, OSError) as error:
        print(f"BENCHMARK_ERROR {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
