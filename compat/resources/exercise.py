#!/usr/bin/env python3
"""Exercise resource capture against a closure-verified rebuilt Oracle image."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

import capture
import contract
import validate


IMAGE_ID_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SAMPLE_KEYS = {
    "sequence",
    "profile_id",
    "primary_scale_axis",
    "target",
    "generator_version",
    "profile_seed_sha256",
    "input",
    "input_sha256_after",
    "outcome",
    "metrics",
    "raw_metrics",
    "stdout",
    "stderr",
    "unexpected_output_entries",
    "cleanup",
}


class ResourceExerciseError(RuntimeError):
    pass


def sample_validator() -> Draft202012Validator:
    original = validate.load_json(validate.RESULT_SCHEMA_PATH)
    wrapper = {
        "$schema": original["$schema"],
        "$defs": original["$defs"],
        "$ref": "#/$defs/sample",
    }
    try:
        Draft202012Validator.check_schema(wrapper)
    except SchemaError as error:
        raise ResourceExerciseError(
            f"rebuilt resource sample schema is invalid: {error.message}"
        ) from error
    return Draft202012Validator(wrapper)


def validate_sample_schema(
    sample: dict[str, Any],
    validator: Draft202012Validator,
) -> None:
    errors = sorted(
        validator.iter_errors(sample),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].absolute_path) or "<root>"
        raise ResourceExerciseError(
            f"rebuilt resource sample schema failure at {location}: {errors[0].message}"
        )


def resolve_image_reference(image_reference: str) -> str:
    if not image_reference or image_reference != image_reference.strip():
        raise ResourceExerciseError("rebuilt Oracle image reference is invalid")
    inspected = capture.run_checked([
        "docker",
        "image",
        "inspect",
        "--format",
        "{{.Id}}",
        image_reference,
    ])
    try:
        image_id = inspected.stdout.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise ResourceExerciseError("rebuilt Oracle image ID is not ASCII") from error
    if IMAGE_ID_PATTERN.fullmatch(image_id) is None:
        raise ResourceExerciseError(f"rebuilt Oracle image ID is invalid: {image_id!r}")
    return image_id


def validate_sample(
    sample: dict[str, Any],
    profile: dict[str, Any],
    output_root: Path,
    measurement_tool: dict[str, Any],
    sample_schema: Draft202012Validator,
) -> None:
    validate_sample_schema(sample, sample_schema)
    profile_id = profile["id"]
    if set(sample) != EXPECTED_SAMPLE_KEYS:
        raise ResourceExerciseError(f"rebuilt resource sample shape drift: {profile_id}")
    for sample_key, profile_key in (
        ("sequence", "sequence"),
        ("profile_id", "id"),
        ("primary_scale_axis", "primary_scale_axis"),
        ("target", "target"),
        ("generator_version", "generator_version"),
        ("profile_seed_sha256", "profile_seed_sha256"),
        ("input", "input"),
    ):
        if sample[sample_key] != profile[profile_key]:
            raise ResourceExerciseError(
                f"rebuilt resource sample identity drift: {profile_id}:{sample_key}"
            )
    expected = profile["expected_observation"]
    if sample["input_sha256_after"] != profile["input"]["sha256"]:
        raise ResourceExerciseError(f"rebuilt resource input changed: {profile_id}")
    if sample["outcome"] != expected["outcome"]:
        raise ResourceExerciseError(f"rebuilt resource outcome drift: {profile_id}")
    if sample["unexpected_output_entries"] != expected["unexpected_output_entries"]:
        raise ResourceExerciseError(f"rebuilt resource output-tree drift: {profile_id}")
    if sample["cleanup"] != {
        "work_directory_removed": True,
        "evidence_directory_removed": True,
        "container_removed": True,
    }:
        raise ResourceExerciseError(f"rebuilt resource cleanup drift: {profile_id}")

    expected_paths = {
        "raw_metrics": f"samples/{profile_id}/metrics.json",
        "stdout": f"samples/{profile_id}/stdout.bin",
        "stderr": f"samples/{profile_id}/stderr.bin",
    }
    for role, expected_path in expected_paths.items():
        validate_artifact_descriptor(sample[role], profile_id, role)
        if sample[role]["path"] != expected_path:
            raise ResourceExerciseError(
                f"rebuilt resource artifact role drift: {profile_id}:{role}"
            )
    stdout_path = validate.validate_artifact(output_root, sample["stdout"], "samples")
    stderr_path = validate.validate_artifact(output_root, sample["stderr"], "samples")
    if {
        "bytes": sample["stdout"]["bytes"],
        "sha256": sample["stdout"]["sha256"],
    } != expected["stdout"]:
        raise ResourceExerciseError(f"rebuilt resource stdout drift: {profile_id}")
    if {
        "bytes": sample["stderr"]["bytes"],
        "sha256": sample["stderr"]["sha256"],
    } != expected["stderr"]:
        raise ResourceExerciseError(f"rebuilt resource stderr drift: {profile_id}")
    if stderr_path.read_bytes():
        raise ResourceExerciseError(f"rebuilt resource stderr is not empty: {profile_id}")
    if validate.parse_summary(stdout_path.read_bytes()) != expected["summary"]:
        raise ResourceExerciseError(f"rebuilt resource summary drift: {profile_id}")
    validate_raw_metrics(sample, output_root, profile_id, measurement_tool)


def validate_artifact_descriptor(
    descriptor: dict[str, Any],
    profile_id: str,
    role: str,
) -> None:
    if not isinstance(descriptor, dict) or set(descriptor) != {"path", "bytes", "sha256"}:
        raise ResourceExerciseError(
            f"rebuilt resource artifact descriptor keys drift: {profile_id}:{role}"
        )
    if not isinstance(descriptor["path"], str) or not descriptor["path"]:
        raise ResourceExerciseError(
            f"rebuilt resource artifact path type drift: {profile_id}:{role}"
        )
    if (
        isinstance(descriptor["bytes"], bool)
        or not isinstance(descriptor["bytes"], int)
        or descriptor["bytes"] < 0
    ):
        raise ResourceExerciseError(
            f"rebuilt resource artifact byte-count drift: {profile_id}:{role}"
        )
    if (
        not isinstance(descriptor["sha256"], str)
        or SHA256_PATTERN.fullmatch(descriptor["sha256"]) is None
    ):
        raise ResourceExerciseError(
            f"rebuilt resource artifact digest drift: {profile_id}:{role}"
        )


def validate_raw_metrics(
    sample: dict[str, Any],
    output_root: Path,
    profile_id: str,
    measurement_tool: dict[str, Any],
) -> None:
    raw_path = output_root / sample["raw_metrics"]["path"]
    raw = validate.load_json(
        validate.validate_artifact(output_root, sample["raw_metrics"], "samples")
    )
    canonical_raw = (json.dumps(raw, ensure_ascii=True, sort_keys=True) + "\n").encode("ascii")
    if raw_path.read_bytes() != canonical_raw:
        raise ResourceExerciseError(f"rebuilt resource raw metrics JSON drift: {profile_id}")
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
    if set(raw) != expected_keys:
        raise ResourceExerciseError(f"rebuilt resource raw metrics keys drift: {profile_id}")
    if isinstance(raw["schema_version"], bool) or raw["schema_version"] != 1:
        raise ResourceExerciseError(f"rebuilt resource raw metrics schema drift: {profile_id}")
    if raw["measurement_backend"] != measurement_tool["backend"]:
        raise ResourceExerciseError(f"rebuilt resource measurement_backend drift: {profile_id}")
    if raw["clock"] != measurement_tool["clock"]:
        raise ResourceExerciseError(f"rebuilt resource clock drift: {profile_id}")
    if (
        isinstance(raw["wall_time_ns"], bool)
        or not isinstance(raw["wall_time_ns"], int)
        or raw["wall_time_ns"] < 1
    ):
        raise ResourceExerciseError(f"rebuilt resource wall_time_ns drift: {profile_id}")
    for key in ("user_cpu_time_ns", "system_cpu_time_ns"):
        if isinstance(raw[key], bool) or not isinstance(raw[key], int) or raw[key] < 0:
            raise ResourceExerciseError(f"rebuilt resource {key} drift: {profile_id}")
    if (
        isinstance(raw["peak_rss_bytes"], bool)
        or not isinstance(raw["peak_rss_bytes"], int)
        or raw["peak_rss_bytes"] < 1
    ):
        raise ResourceExerciseError(f"rebuilt resource peak_rss_bytes drift: {profile_id}")
    if isinstance(raw["exit_code"], bool) or raw["exit_code"] != 0:
        raise ResourceExerciseError(f"rebuilt resource exit_code drift: {profile_id}")
    if raw["signal"] is not None:
        raise ResourceExerciseError(f"rebuilt resource signal drift: {profile_id}")
    validate.validate_raw_metrics(sample, output_root, profile_id)


def validate_samples_tree(output_root: Path, profile_ids: list[str]) -> None:
    if output_root.is_symlink() or not output_root.is_dir():
        raise ResourceExerciseError("rebuilt resource output root is invalid")
    expected_directories = {"samples"} | {
        f"samples/{profile_id}" for profile_id in profile_ids
    }
    expected_files = {
        f"samples/{profile_id}/{filename}"
        for profile_id in profile_ids
        for filename in ("metrics.json", "stdout.bin", "stderr.bin")
    }
    observed_directories: set[str] = set()
    observed_files: set[str] = set()
    for candidate in output_root.rglob("*"):
        relative = candidate.relative_to(output_root).as_posix()
        if candidate.is_symlink():
            raise ResourceExerciseError(
                f"rebuilt resource output contains a symlink: {relative}"
            )
        if candidate.is_dir():
            observed_directories.add(relative)
        elif candidate.is_file():
            observed_files.add(relative)
        else:
            raise ResourceExerciseError(
                f"rebuilt resource output contains an unsupported entry: {relative}"
            )
    if observed_directories != expected_directories or observed_files != expected_files:
        raise ResourceExerciseError(
            "rebuilt resource samples-only tree closure drift: "
            f"extra_directories={sorted(observed_directories - expected_directories)} "
            f"missing_directories={sorted(expected_directories - observed_directories)} "
            f"extra_files={sorted(observed_files - expected_files)} "
            f"missing_files={sorted(expected_files - observed_files)}"
        )


def validate_exercise(
    samples: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    output_root: Path,
    measurement_tool: dict[str, Any] | None = None,
) -> None:
    if len(samples) != 13 or len(profiles) != 13:
        raise ResourceExerciseError("rebuilt resource profile coverage drift")
    profile_ids = [profile["id"] for profile in profiles]
    validate_samples_tree(output_root, profile_ids)
    if measurement_tool is None:
        measurement_tool = contract.load_json(contract.OUTPUT_PATH)["measurement_tool"]
    assert measurement_tool is not None
    sample_schema = sample_validator()
    for sample, profile in zip(samples, profiles, strict=True):
        validate_sample(sample, profile, output_root, measurement_tool, sample_schema)
    if (output_root / "result.json").exists():
        raise ResourceExerciseError("rebuilt resource exercise emitted canonical result.json")


def safe_output_root(output_root: Path) -> Path:
    if output_root.is_symlink():
        raise ResourceExerciseError(f"rebuilt resource output root is a symlink: {output_root}")
    resolved = output_root.resolve()
    if resolved.is_symlink():
        raise ResourceExerciseError(f"rebuilt resource output root resolves to a symlink: {output_root}")
    return resolved


def exercise(image_reference: str, output_root: Path) -> str:
    safe_root = safe_output_root(output_root)
    canonical_document = contract.load_json(contract.OUTPUT_PATH)
    contract.validate_document(canonical_document)
    capture.require_empty_output(safe_root)

    resolved_image_id = resolve_image_reference(image_reference)
    exercise_document = copy.deepcopy(canonical_document)
    exercise_document["oracle_identity"]["image_sha256"] = resolved_image_id
    capture.verify_runtime_identity(exercise_document)

    profiles = canonical_document["profiles"]
    samples = [
        capture.capture_profile(safe_root, exercise_document, profile)
        for profile in profiles
    ]
    validate_exercise(
        samples,
        profiles,
        safe_root,
        canonical_document["measurement_tool"],
    )
    return resolved_image_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output_path = args.output
    if output_path.is_symlink():
        raise ResourceExerciseError(f"rebuilt resource output root is a symlink: {output_path}")
    image_id = exercise(args.image, output_path)
    print(
        "REBUILD_RESOURCE_EXERCISE_OK "
        f"image={image_id} profiles=13 "
        "product_limits=false product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
