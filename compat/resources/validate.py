#!/usr/bin/env python3
"""Validate the static M0 resource contract and retained Oracle result."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

import contract


ROOT = Path(__file__).resolve().parents[2]
RESULT_SCHEMA_PATH = ROOT / "compat/schema/resource-result.schema.json"
DEFAULT_RESULT_PATH = Path(__file__).parent / "results/oracle-x86_64-linux-20260729/result.json"
EXPECTED_TOTALS = {
    "profiles": 13,
    "accepted": 13,
    "nonzero": 0,
    "signaled": 0,
    "timeouts": 0,
}
RATE_PATTERN = re.compile(r"^(?P<percent>[0-9]+\.[0-9])% \((?P<hit>[0-9]+) of (?P<found>[0-9]+) .+\)$")


class ResourceValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ResourceValidationError(f"cannot load resource JSON: {path}") from error
    if not isinstance(document, dict):
        raise ResourceValidationError(f"expected resource JSON object: {path}")
    return document


def validate_schema(document: dict[str, Any]) -> None:
    schema = load_json(RESULT_SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ResourceValidationError(f"resource result schema is invalid: {error.message}") from error
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise ResourceValidationError(f"resource result schema failure at {location}: {errors[0].message}")


def validate_artifact(
    root: Path,
    artifact: dict[str, Any],
    prefix: str | None = None,
) -> Path:
    relative = Path(artifact["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ResourceValidationError(f"resource artifact path is unsafe: {relative}")
    if prefix is not None and relative.parts[:1] != (prefix,):
        raise ResourceValidationError(f"resource artifact path has the wrong role: {relative}")
    resolved_root = root.resolve()
    candidate = resolved_root / relative
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root) or not resolved.is_file() or candidate.is_symlink():
        raise ResourceValidationError(f"resource artifact is missing or escapes its root: {relative}")
    if resolved.stat().st_size != artifact["bytes"] or contract.sha256_file(resolved) != artifact["sha256"]:
        raise ResourceValidationError(f"resource artifact bytes drift: {relative}")
    return resolved


def validate_repository_artifact(artifact: dict[str, Any], expected_path: Path) -> None:
    expected_relative = expected_path.resolve().relative_to(ROOT.resolve()).as_posix()
    if artifact["path"] != expected_relative:
        raise ResourceValidationError(f"resource repository artifact path drift: {artifact['path']}")
    validate_artifact(ROOT, artifact)


def validate_result_tree(result_path: Path, profile_ids: list[str]) -> None:
    result_root = result_path.parent
    if (
        result_path.name != "result.json"
        or result_path.is_symlink()
        or result_root.is_symlink()
        or not result_root.is_dir()
    ):
        raise ResourceValidationError("resource result root or result.json has an invalid role")
    expected_directories = {"samples"} | {f"samples/{profile_id}" for profile_id in profile_ids}
    expected_files = {"result.json"} | {
        f"samples/{profile_id}/{filename}"
        for profile_id in profile_ids
        for filename in ("metrics.json", "stdout.bin", "stderr.bin")
    }
    observed_directories: set[str] = set()
    observed_files: set[str] = set()
    for candidate in result_root.rglob("*"):
        relative = candidate.relative_to(result_root).as_posix()
        if candidate.is_symlink():
            raise ResourceValidationError(f"resource result tree contains a symlink: {relative}")
        if candidate.is_dir():
            observed_directories.add(relative)
        elif candidate.is_file():
            observed_files.add(relative)
        else:
            raise ResourceValidationError(f"resource result tree contains an unsupported entry: {relative}")
    if observed_directories != expected_directories or observed_files != expected_files:
        extra_directories = sorted(observed_directories - expected_directories)
        missing_directories = sorted(expected_directories - observed_directories)
        extra_files = sorted(observed_files - expected_files)
        missing_files = sorted(expected_files - observed_files)
        raise ResourceValidationError(
            "resource result tree closure drift: "
            f"extra_directories={extra_directories} missing_directories={missing_directories} "
            f"extra_files={extra_files} missing_files={missing_files}"
        )


def _rate(line: str) -> tuple[int | None, int | None]:
    value = line.split(":", 1)[1].strip()
    if value == "no data found":
        return None, None
    match = RATE_PATTERN.fullmatch(value)
    if match is None:
        raise ResourceValidationError(f"resource summary rate is malformed: {line}")
    found = int(match.group("found"))
    hit = int(match.group("hit"))
    if f"{100.0 * hit / found:.1f}" != match.group("percent"):
        raise ResourceValidationError(f"resource summary percentage is inconsistent: {line}")
    return found, hit


def parse_summary(raw: bytes) -> dict[str, int | None]:
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise ResourceValidationError("resource stdout is not ASCII") from error
    if len(lines) != 9:
        raise ResourceValidationError("resource stdout has the wrong line count")
    if lines[:2] != ["Reading tracefile input.info.", "Summary coverage rate:"]:
        raise ResourceValidationError("resource stdout preamble drift")
    if lines[7:] != ["Message summary:", "  no messages were reported"]:
        raise ResourceValidationError("resource stdout message summary drift")
    if not lines[2].startswith("  source files: "):
        raise ResourceValidationError("resource stdout source-file summary drift")
    try:
        source_files = int(lines[2].split(":", 1)[1].strip())
    except ValueError as error:
        raise ResourceValidationError("resource stdout source-file count is invalid") from error
    expected_labels = ("  lines.......:", "  functions...:", "  branches....:", "  conditions..:")
    for line, label in zip(lines[3:7], expected_labels, strict=True):
        if not line.startswith(label):
            raise ResourceValidationError(f"resource stdout summary label drift: {label}")
    lines_found, lines_hit = _rate(lines[3])
    functions_found, functions_hit = _rate(lines[4])
    branches_found, branches_hit = _rate(lines[5])
    conditions_found, conditions_hit = _rate(lines[6])
    return {
        "source_files": source_files,
        "lines_found": lines_found,
        "lines_hit": lines_hit,
        "functions_found": functions_found,
        "functions_hit": functions_hit,
        "branches_found": branches_found,
        "branches_hit": branches_hit,
        "condition_outcomes_found": conditions_found,
        "condition_outcomes_hit": conditions_hit,
    }


def validate_raw_metrics(
    sample: dict[str, Any],
    result_root: Path,
    profile_id: str,
) -> None:
    expected_path = f"samples/{profile_id}/metrics.json"
    if sample["raw_metrics"]["path"] != expected_path:
        raise ResourceValidationError(f"resource raw metrics role drift: {profile_id}")
    raw_path = validate_artifact(result_root, sample["raw_metrics"], "samples")
    raw = load_json(raw_path)
    canonical_raw = (json.dumps(raw, ensure_ascii=True, sort_keys=True) + "\n").encode("ascii")
    if raw_path.read_bytes() != canonical_raw:
        raise ResourceValidationError(f"resource raw metrics JSON is not canonical: {profile_id}")
    expected_keys = {
        "schema_version",
        "measurement_backend",
        "clock",
        "wall_time_ns",
        "user_cpu_time_ns",
        "system_cpu_time_ns",
        "peak_rss_bytes",
        "exit_code",
        "signal",
    }
    if set(raw) != expected_keys or raw["schema_version"] != 1:
        raise ResourceValidationError(f"resource raw metrics shape drift: {profile_id}")
    expected_metrics = {
        "measurement_backend": raw["measurement_backend"],
        "clock": raw["clock"],
        "wall_time_ns": raw["wall_time_ns"],
        "user_cpu_time_ns": raw["user_cpu_time_ns"],
        "system_cpu_time_ns": raw["system_cpu_time_ns"],
        "peak_rss_bytes": raw["peak_rss_bytes"],
    }
    if sample["metrics"] != expected_metrics:
        raise ResourceValidationError(f"resource result metrics differ from raw artifact: {profile_id}")
    expected_outcome = {
        "exit_code": raw["exit_code"],
        "signal": raw["signal"],
        "timeout": False,
        "container_exit_code": raw["exit_code"],
    }
    if sample["outcome"] != expected_outcome:
        raise ResourceValidationError(f"resource result outcome differs from raw metrics: {profile_id}")


def validate_result(document: dict[str, Any], result_path: Path) -> None:
    validate_schema(document)
    contract_document = contract.load_json(contract.OUTPUT_PATH)
    contract.validate_document(contract_document)
    validate_repository_artifact(document["contract"], contract.OUTPUT_PATH)
    validate_repository_artifact(document["execution_manifest"], contract.MANIFEST_PATH)
    validate_repository_artifact(document["measurement_tool"], contract.MEASUREMENT_TOOL_PATH)
    if document["harness_artifacts"] != contract_document["harness_artifacts"]:
        raise ResourceValidationError("resource result harness closure drift")
    for artifact, expected_path in zip(
        document["harness_artifacts"], contract.HARNESS_PATHS, strict=True
    ):
        validate_repository_artifact(artifact, expected_path)
    if document["observed_image_sha256"] != contract_document["oracle_identity"]["image_sha256"]:
        raise ResourceValidationError("resource result image identity drift")
    if document["observed_lcov_sha256"] != contract_document["oracle_identity"]["lcov_sha256"]:
        raise ResourceValidationError("resource result lcov identity drift")
    if document["environment"] != contract_document["execution_policy"]["environment"]:
        raise ResourceValidationError("resource result environment drift")
    if document["allocations"] != contract_document["execution_policy"]["allocations"]:
        raise ResourceValidationError("resource result allocation status drift")

    expected_profiles = contract_document["profiles"]
    samples = document["samples"]
    if len(samples) != len(expected_profiles):
        raise ResourceValidationError("resource result profile coverage drift")
    result_root = result_path.parent
    validate_result_tree(result_path, [profile["id"] for profile in expected_profiles])
    for sample, profile in zip(samples, expected_profiles, strict=True):
        for result_key, profile_key in (
            ("sequence", "sequence"),
            ("profile_id", "id"),
            ("primary_scale_axis", "primary_scale_axis"),
            ("target", "target"),
            ("generator_version", "generator_version"),
            ("profile_seed_sha256", "profile_seed_sha256"),
            ("input", "input"),
        ):
            if sample[result_key] != profile[profile_key]:
                raise ResourceValidationError(f"resource result profile drift: {profile['id']}:{result_key}")
        if sample["input_sha256_after"] != profile["input"]["sha256"]:
            raise ResourceValidationError(f"resource input changed during execution: {profile['id']}")
        if sample["outcome"] != profile["expected_observation"]["outcome"]:
            raise ResourceValidationError(f"resource outcome differs from Oracle contract: {profile['id']}")
        if sample["unexpected_output_entries"] != profile["expected_observation"]["unexpected_output_entries"]:
            raise ResourceValidationError(f"resource summary command created output files: {profile['id']}")
        if set(sample["cleanup"].values()) != {True}:
            raise ResourceValidationError(f"resource cleanup evidence drift: {profile['id']}")

        expected_stdout_path = f"samples/{profile['id']}/stdout.bin"
        expected_stderr_path = f"samples/{profile['id']}/stderr.bin"
        if sample["stdout"]["path"] != expected_stdout_path or sample["stderr"]["path"] != expected_stderr_path:
            raise ResourceValidationError(f"resource stream artifact role drift: {profile['id']}")
        stdout_path = validate_artifact(result_root, sample["stdout"], "samples")
        stderr_path = validate_artifact(result_root, sample["stderr"], "samples")
        expected_streams = profile["expected_observation"]
        if {
            "bytes": sample["stdout"]["bytes"],
            "sha256": sample["stdout"]["sha256"],
        } != expected_streams["stdout"]:
            raise ResourceValidationError(f"resource stdout differs from Oracle contract: {profile['id']}")
        if {
            "bytes": sample["stderr"]["bytes"],
            "sha256": sample["stderr"]["sha256"],
        } != expected_streams["stderr"]:
            raise ResourceValidationError(f"resource stderr differs from Oracle contract: {profile['id']}")
        if stderr_path.read_bytes():
            raise ResourceValidationError(f"resource stderr must be empty: {profile['id']}")
        if parse_summary(stdout_path.read_bytes()) != expected_streams["summary"]:
            raise ResourceValidationError(f"resource stdout semantic summary drift: {profile['id']}")
        validate_raw_metrics(sample, result_root, profile["id"])

    if document["totals"] != EXPECTED_TOTALS:
        raise ResourceValidationError("resource result totals drift")
    if document["measurement_interpretation"] != "single_run_bounded_observations_not_performance_gates":
        raise ResourceValidationError("resource measurement interpretation drift")
    if (
        document["harness_budgets_are_product_limits"]
        or document["product_limits_selected"]
        or document["product_limit_evidence"]
        or document["product_compatibility_evidence"]
    ):
        raise ResourceValidationError("resource result claims product evidence or limits")
    if result_path.read_text(encoding="ascii") != contract.canonical_json(document):
        raise ResourceValidationError("resource result JSON is not canonical")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", action="store_true")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if not args.contract and args.result is None:
        args.contract = True
        args.result = DEFAULT_RESULT_PATH
    if args.contract:
        document = contract.load_json(contract.OUTPUT_PATH)
        contract.validate_document(document)
        print(f"RESOURCE_STATIC_CONTRACT_OK profiles={document['totals']['profiles']}")
    if args.result is not None:
        result_path = args.result.resolve()
        document = load_json(result_path)
        validate_result(document, result_path)
        peak_rss = max(sample["metrics"]["peak_rss_bytes"] for sample in document["samples"])
        wall_time = max(sample["metrics"]["wall_time_ns"] for sample in document["samples"])
        print(
            "RESOURCE_RESULT_OK "
            "profiles=13 accepted=13 nonzero=0 signaled=0 timeouts=0 "
            f"max_peak_rss_bytes={peak_rss} max_wall_time_ns={wall_time} "
            "product_limits=false product_compatibility=false"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
