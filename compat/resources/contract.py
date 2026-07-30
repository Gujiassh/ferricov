#!/usr/bin/env python3
"""Generate and validate the fail-closed M0 Oracle resource contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

import generate


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).with_name("v2.5.json")
SCHEMA_PATH = ROOT / "compat/schema/resource-contract.schema.json"
MANIFEST_PATH = ROOT / "compat/manifests/oracle-lcov-v2.5-smoke.json"
MEASUREMENT_TOOL_PATH = ROOT / "compat/benchmarks/measure.py"
HARNESS_PATHS = (
    ROOT / "compat/resources/contract.py",
    ROOT / "compat/resources/generate.py",
    ROOT / "compat/resources/capture.py",
    ROOT / "compat/resources/validate.py",
    ROOT / "compat/schema/resource-contract.schema.json",
    ROOT / "compat/schema/resource-result.schema.json",
)
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
EXPECTED_IMAGE_SHA256 = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
EXPECTED_LCOV_SHA256 = "sha256:d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
BLOCKED_IDS = ("M1-MD-020", "M1-TF-063", "M1-TF-064")

SOURCE_SECTIONS = (
    (
        "resource.coverage-model-budgets",
        "specs/001-full-lcov-compatibility/coverage-model.md",
        "### Resource And Fuzz Budgets",
        "## Oracle Decisions And Case IDs",
        "resource_and_fuzz_budgets",
    ),
    (
        "resource.tracefile-scale-profiles",
        "specs/001-full-lcov-compatibility/tracefile-grammar.md",
        "The deterministic `M1-TF-062` generator profiles are:",
        "## M1 Evidence And Exit Conditions",
        "tracefile_scale_and_resource_requirements",
    ),
)


class ResourceContractError(RuntimeError):
    pass


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ResourceContractError(f"cannot load JSON object: {path}") from error
    if not isinstance(document, dict):
        raise ResourceContractError(f"expected JSON object: {path}")
    return document


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def source_section(
    identifier: str,
    relative: str,
    start_marker: str,
    end_marker: str,
    role: str,
) -> dict[str, Any]:
    path = ROOT / relative
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [index for index, line in enumerate(lines) if line == start_marker]
    ends = [index for index, line in enumerate(lines) if line == end_marker]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise ResourceContractError(f"resource source-section markers drift: {relative}")
    start, end = starts[0], ends[0]
    selected = lines[start:end]
    content = ("\n".join(selected) + "\n").encode("utf-8")
    return {
        "id": identifier,
        "path": relative,
        "line_start": start + 1,
        "line_end": end,
        "line_count": len(selected),
        "role": role,
        "sha256": sha256_bytes(content),
    }


def oracle_identity() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)
    if manifest.get("status") != "observed" or manifest.get("manifest_id") != "oracle-lcov-v2.5-image-smoke":
        raise ResourceContractError("resource Oracle manifest identity drift")
    image = manifest.get("image", {})
    if (
        image.get("docker_image_id") != EXPECTED_IMAGE_SHA256
        or image.get("labels", {}).get("org.opencontainers.image.revision") != UPSTREAM_COMMIT
    ):
        raise ResourceContractError("resource Oracle image identity drift")
    executables = manifest.get("executables", [])
    lcov_entries = [entry for entry in executables if entry.get("name") == "lcov"]
    if len(lcov_entries) != 1 or lcov_entries[0].get("sha256") != EXPECTED_LCOV_SHA256:
        raise ResourceContractError("resource Oracle lcov identity drift")
    execution = manifest.get("execution", {})
    if execution.get("user") != "root" or execution.get("network") != "none":
        raise ResourceContractError("resource Oracle execution policy drift")
    return {
        "manifest_path": "compat/manifests/oracle-lcov-v2.5-smoke.json",
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "manifest_id": manifest["manifest_id"],
        "image_sha256": EXPECTED_IMAGE_SHA256,
        "lcov_path": lcov_entries[0]["path"],
        "lcov_sha256": EXPECTED_LCOV_SHA256,
        "user": execution["user"],
        "network": execution["network"],
        "evidence_scope": manifest["evidence"]["scope"],
        "product_compatibility_evidence": False,
    }


def measurement_tool() -> dict[str, Any]:
    return {
        "path": "compat/benchmarks/measure.py",
        "sha256": sha256_file(MEASUREMENT_TOOL_PATH),
        "backend": "linux-rusage-children-v1",
        "clock": "monotonic",
        "metrics": [
            "wall_time_ns",
            "user_cpu_time_ns",
            "system_cpu_time_ns",
            "peak_rss_bytes",
        ],
    }


def harness_artifacts() -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in HARNESS_PATHS
    ]


def expected_observation(definition: dict[str, Any]) -> dict[str, Any]:
    stdout = generate.expected_stdout(definition)
    return {
        "outcome": {
            "exit_code": 0,
            "signal": None,
            "timeout": False,
            "container_exit_code": 0,
        },
        "summary": generate.expected_summary(definition),
        "stdout": {
            "bytes": len(stdout),
            "sha256": sha256_bytes(stdout),
        },
        "stderr": {
            "bytes": 0,
            "sha256": EMPTY_SHA256,
        },
        "unexpected_output_entries": [],
    }


def generated_profiles() -> list[dict[str, Any]]:
    profiles = []
    with tempfile.TemporaryDirectory(prefix="ferricov-resource-contract-") as temporary_directory:
        temporary = Path(temporary_directory)
        for sequence, definition in enumerate(generate.PROFILES):
            input_path = temporary / f"{definition['id']}.info"
            shape = generate.generate_and_analyze(definition, input_path)
            profiles.append({
                "id": definition["id"],
                "sequence": sequence,
                "primary_scale_axis": definition["axis"],
                "target": definition["target"],
                "generator_version": generate.GENERATOR_VERSION,
                "profile_seed_sha256": generate.profile_seed(definition["id"]),
                "input": shape,
                "expected_observation": expected_observation(definition),
                "evidence_requirement": "oracle_observation_required",
                "product_limit_evidence": False,
            })
    return profiles


def build_document() -> dict[str, Any]:
    sections = [source_section(*definition) for definition in SOURCE_SECTIONS]
    profiles = generated_profiles()
    axis_counts: dict[str, int] = {}
    for profile in profiles:
        axis = profile["primary_scale_axis"]
        axis_counts[axis] = axis_counts.get(axis, 0) + 1
    return {
        "schema_version": 1,
        "contract_id": "m0-resource-measurement-v1",
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "scope": "M0-RSRC-MEASURE-001 controlled Oracle parser-resource observations",
        "matrix_interpretation": {
            "design": "controlled_scale_profiles",
            "primary_axis_rule": "each profile targets one primary scale axis while all dependent input dimensions are recorded",
            "field_axis": "TN payload bytes; the enclosing logical record adds the TN: prefix",
            "data_record_axis": "DA record count inside one source section",
            "section_axis": "source sections containing one DA record each; global line cardinality therefore changes with section count",
            "family_cardinality_axis": "equal distinct line, function, branch, and logical MC/DC condition cardinalities inside one source section; each logical MC/DC condition emits two condition outcomes",
        },
        "source_sections": sections,
        "oracle_identity": oracle_identity(),
        "measurement_tool": measurement_tool(),
        "harness_artifacts": harness_artifacts(),
        "execution_policy": {
            "command": [
                "/usr/local/bin/lcov",
                "--branch-coverage",
                "--mcdc-coverage",
                "--summary",
                "input.info",
            ],
            "environment": {
                "HOME": "/tmp",
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "TZ": "UTC",
            },
            "environment_inheritance": False,
            "timeout_seconds": 60,
            "deadline_observer": "host_subprocess_timeout",
            "container_memory_bytes": 1_073_741_824,
            "container_pids": 128,
            "allocations": {
                "status": "not_observable",
                "reason": "the pinned Oracle and rusage backend expose no allocation counter",
            },
        },
        "profiles": profiles,
        "m0_case_id": "M0-RSRC-MEASURE-001",
        "m0_case_status": "oracle_observation_required",
        "blocked_case_ids": list(BLOCKED_IDS),
        "harness_budgets_are_product_limits": False,
        "product_limits_selected": False,
        "product_limit_evidence": [],
        "totals": {
            "profiles": len(profiles),
            "axis_counts": axis_counts,
            "source_sections": len(sections),
            "source_lines": sum(section["line_count"] for section in sections),
            "harness_artifacts": len(HARNESS_PATHS),
        },
        "product_compatibility_evidence": False,
    }


def validate_schema(document: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ResourceContractError(f"resource contract schema is invalid: {error.message}") from error
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise ResourceContractError(f"resource contract schema failure at {location}: {errors[0].message}")


def validate_document(document: dict[str, Any]) -> None:
    validate_schema(document)
    expected = build_document()
    if document != expected:
        for key in expected:
            if document.get(key) != expected[key]:
                raise ResourceContractError(f"resource contract drift: {key}")
        raise ResourceContractError("resource contract has unexpected content")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    document = build_document()
    validate_schema(document)
    content = canonical_json(document).encode("ascii")
    if args.write:
        OUTPUT_PATH.write_bytes(content)
        print(f"RESOURCE_CONTRACT_WRITTEN path={OUTPUT_PATH.relative_to(ROOT)}")
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != content:
        raise ResourceContractError("committed resource contract differs from generation")
    validate_document(document)
    print(
        "RESOURCE_CONTRACT_OK "
        f"profiles={document['totals']['profiles']} "
        f"source_sections={document['totals']['source_sections']} "
        f"harness_artifacts={document['totals']['harness_artifacts']} "
        "product_limits=false product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
