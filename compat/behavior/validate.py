#!/usr/bin/env python3
"""Validate the canonical behavior planning contract and M0 readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from generate import (
    AUDIT_PATH,
    CONTRACT_PATH,
    INVENTORY_PATH,
    REQUIRED_INTERACTION_DOMAINS,
    SCHEMA_PATH,
    SUITES_PATH,
    TEST_MAP_PATH,
    UPSTREAM_COMMIT,
    UPSTREAM_RELEASE,
    calculate_totals,
    canonical_bytes,
    inventory_entries,
    FRAGMENT_SCHEMA_PATH,
    FRAGMENTS_PATH,
    make_case_skeleton,
    public_inventory_entries,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", REPOSITORY_ROOT.parent / "lcov-upstream-reference")
)
SUITE_SCHEMA_PATH = "compat/schema/suite.schema.json"
RESULT_SCHEMA_PATH = "compat/schema/differential-result.schema.json"


class ValidationError(Exception):
    """Raised when the behavior contract violates a fail-closed invariant."""


@dataclass(frozen=True)
class ValidationReport:
    public_entries: int
    primary_case_coverage: int
    reviewed_primary_coverage: int
    readiness_gaps: tuple[str, ...]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot load {label} {path}: {error}") from error
    require(isinstance(value, dict), f"{label} root must be an object")
    return value


def validate_json_schema(
    schema: dict[str, Any],
    document: dict[str, Any],
    label: str,
) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ValidationError(f"invalid JSON Schema for {label}: {error.message}") from error
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValidationError(f"JSON Schema rejected {label} at {location}: {error.message}")


def safe_repo_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def require_sorted_unique(
    values: list[Any],
    key,
    label: str,
) -> None:
    keys = [key(value) for value in values]
    require(keys == sorted(keys), f"{label} must be sorted")
    require(len(keys) == len(set(keys)), f"{label} must be unique")


def source_key(source: dict[str, Any]) -> tuple[Any, ...]:
    return (
        source["repository"],
        source["path"],
        source["line"],
        source["kind"],
        source.get("text", ""),
    )


def suite_key(reference: dict[str, Any]) -> tuple[str, str]:
    return reference["suite_id"], reference["case_id"]


def evidence_key(reference: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        reference["suite_id"],
        reference["case_id"],
        reference["result_path"],
        reference["outcome"],
    )


def validate_canonical(path: Path, document: dict[str, Any], label: str) -> None:
    require(path.read_bytes() == canonical_bytes(document), f"{label} is not canonical sorted JSON")


def index_inventory(
    inventory: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    require(inventory.get("schema_version") == 2, "inventory schema_version must be 2")
    require(inventory.get("upstream_release") == UPSTREAM_RELEASE, "inventory release mismatch")
    require(inventory.get("upstream_commit") == UPSTREAM_COMMIT, "inventory commit mismatch")
    items = inventory_entries(inventory)
    ids = [item["entry"]["id"] for item in items]
    require(ids == sorted(ids), "inventory index generation must be sorted")
    require(len(ids) == len(set(ids)), "inventory entry ids must be unique")
    by_id = {item["entry"]["id"]: item for item in items}
    public_ids = {
        item["entry"]["id"]
        for item in items
        if item["entry"]["classification"] == "public"
        and item["entry"]["applicability"] != "not_applicable"
    }
    return by_id, public_ids


def index_test_map(test_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    upstream = test_map.get("upstream")
    require(isinstance(upstream, dict), "test map upstream must be an object")
    require(upstream.get("release") == UPSTREAM_RELEASE, "test map release mismatch")
    require(upstream.get("commit") == UPSTREAM_COMMIT, "test map commit mismatch")
    entries = test_map.get("entries")
    require(isinstance(entries, list), "test map entries must be an array")
    paths = [entry["source"] for entry in entries]
    require(paths == sorted(paths), "test map entries must be sorted")
    require(len(paths) == len(set(paths)), "test map sources must be unique")
    return {entry["source"]: entry for entry in entries}


def validate_behavior_import(
    contract: dict[str, Any],
    test_map: dict[str, Any],
) -> set[str]:
    expected = [
        {
            "id": group["id"],
            "description": group["description"],
            "registry_source": {
                "path": TEST_MAP_PATH,
                "id": group["id"],
            },
        }
        for group in sorted(test_map["behavior_groups"], key=lambda group: group["id"])
    ]
    require(
        contract["behavior_groups"] == expected,
        "behavior_groups must exactly import the upstream test-map registry",
    )
    ids = [group["id"] for group in expected]
    return set(ids)


def validate_ferricov_source(repo_root: Path, source: dict[str, Any]) -> None:
    relative = source["path"]
    require(safe_repo_path(relative), f"unsafe Ferricov source path: {relative}")
    path = (repo_root / relative).resolve()
    require(path.is_relative_to(repo_root), f"Ferricov source escapes repository: {relative}")
    require(path.is_file(), f"Ferricov source does not exist: {relative}")
    lines = path.read_text(encoding="utf-8").splitlines()
    line = source["line"]
    require(line <= len(lines), f"Ferricov source line is out of range: {relative}:{line}")
    require(
        lines[line - 1] == source["text"],
        f"Ferricov source text mismatch: {relative}:{line}",
    )


def git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValidationError(f"git validation failed for {root}: {error}") from error
    return completed.stdout.strip()


UPSTREAM_REFERENCE = re.compile(
    r"`(?P<path>[A-Za-z0-9._/-]+):(?P<start>[0-9]+)(?:-(?P<end>[0-9]+))?`"
)


def validate_audit_upstream_references(
    repo_root: Path,
    upstream_root: Path,
    audit_path: str,
) -> None:
    require(safe_repo_path(audit_path), f"unsafe audit contract path: {audit_path}")
    path = (repo_root / audit_path).resolve()
    require(path.is_relative_to(repo_root), "audit contract escapes repository")
    require(path.is_file(), f"audit contract does not exist: {audit_path}")
    require(
        git(upstream_root, "rev-parse", "HEAD") == UPSTREAM_COMMIT,
        "upstream checkout for audit references is not at the pinned commit",
    )
    references = list(UPSTREAM_REFERENCE.finditer(path.read_text(encoding="utf-8")))
    require(bool(references), "audit contract has no parseable upstream path/line references")
    checked: set[tuple[str, int, int]] = set()
    for match in references:
        relative = match.group("path")
        start = int(match.group("start"))
        end = int(match.group("end") or start)
        key = (relative, start, end)
        if key in checked:
            continue
        checked.add(key)
        require(start <= end, f"audit upstream range is reversed: {relative}:{start}-{end}")
        require(safe_repo_path(relative), f"unsafe audit upstream path: {relative}")
        source = (upstream_root / relative).resolve()
        require(source.is_relative_to(upstream_root), f"audit upstream path escapes checkout: {relative}")
        require(source.is_file(), f"audit upstream source does not exist: {relative}")
        line_count = len(source.read_bytes().splitlines())
        require(
            end <= line_count,
            f"audit upstream range is out of bounds: {relative}:{start}-{end} has {line_count} lines",
        )


def validate_direct_upstream_source(
    upstream_root: Path,
    source: dict[str, Any],
) -> None:
    require(source.get("text"), "direct upstream source references require exact text")
    require(
        git(upstream_root, "rev-parse", "HEAD") == UPSTREAM_COMMIT,
        "upstream source checkout is not at the pinned commit",
    )
    relative = source["path"]
    require(safe_repo_path(relative), f"unsafe upstream source path: {relative}")
    path = (upstream_root / relative).resolve()
    require(path.is_relative_to(upstream_root), f"upstream source escapes checkout: {relative}")
    require(path.is_file(), f"upstream source does not exist: {relative}")
    lines = path.read_text(encoding="utf-8").splitlines()
    line = source["line"]
    require(line <= len(lines), f"upstream source line is out of range: {relative}:{line}")
    require(lines[line - 1] == source["text"], f"upstream source text mismatch: {relative}:{line}")


def source_matches_inventory(
    source: dict[str, Any],
    target_ids: Iterable[str],
    inventory_by_id: dict[str, dict[str, Any]],
) -> bool:
    candidate = {key: source[key] for key in ("kind", "path", "line")}
    return any(
        target_id in inventory_by_id
        and candidate in inventory_by_id[target_id]["entry"]["source_references"]
        for target_id in target_ids
    )


def validate_sources(
    repo_root: Path,
    upstream_root: Path,
    sources: list[dict[str, Any]],
    target_ids: Iterable[str],
    inventory_by_id: dict[str, dict[str, Any]],
    label: str,
) -> None:
    require_sorted_unique(sources, source_key, f"{label}.source_references")
    for source in sources:
        if source["repository"] == "ferricov":
            validate_ferricov_source(repo_root, source)
            continue
        if source_matches_inventory(source, target_ids, inventory_by_id):
            continue
        validate_direct_upstream_source(upstream_root, source)


def load_suites(
    repo_root: Path,
    suites_path: str,
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    require(safe_repo_path(suites_path), f"unsafe suites path: {suites_path}")
    suites_dir = (repo_root / suites_path).resolve()
    require(suites_dir.is_relative_to(repo_root), "suites directory escapes repository")
    require(suites_dir.is_dir(), f"suites directory does not exist: {suites_path}")
    schema = load_object(repo_root / SUITE_SCHEMA_PATH, "suite schema")
    suites: dict[str, dict[str, Any]] = {}
    cases: dict[tuple[str, str], dict[str, Any]] = {}
    case_owners: dict[str, str] = {}
    for path in sorted(suites_dir.glob("*.json")):
        suite = load_object(path, "suite")
        validate_json_schema(schema, suite, f"suite {path}")
        suite_id = suite["suite_id"]
        require(suite_id not in suites, f"duplicate suite id: {suite_id}")
        suites[suite_id] = suite
        for case in suite["cases"]:
            key = (suite_id, case["id"])
            require(key not in cases, f"duplicate suite/case identity: {suite_id}/{case['id']}")
            require(
                case["id"] not in case_owners,
                f"suite case id {case['id']} is ambiguous across {case_owners.get(case['id'])} and {suite_id}",
            )
            case_owners[case["id"]] = suite_id
            cases[key] = case
    require(bool(suites), "no suites found")
    return suites, cases


def validate_suite_references(
    case: dict[str, Any],
    suites: dict[str, dict[str, Any]],
    suite_cases: dict[tuple[str, str], dict[str, Any]],
) -> None:
    references = case["suite_cases"]
    require_sorted_unique(references, suite_key, f"{case['id']}.suite_cases")
    required_dimensions = set(case["comparison_dimensions"])
    for reference in references:
        key = suite_key(reference)
        require(key in suite_cases, f"{case['id']}: unknown suite case {key[0]}/{key[1]}")
        suite = suites[key[0]]
        require(
            suite["evidence_scope"] == "compatibility",
            f"{case['id']}: harness self-test suite {key[0]} cannot count as compatibility planning or evidence",
        )
        suite_case = suite_cases[key]
        require(
            suite_case["surface"] == case["surface"],
            f"{case['id']}: suite case {key[0]}/{key[1]} has a different surface",
        )
        available = {comparison["dimension"] for comparison in suite_case["comparisons"]}
        require(
            required_dimensions <= available,
            f"{case['id']}: suite case {key[0]}/{key[1]} lacks required comparison dimensions",
        )


def validate_result_binding(
    contract_case: dict[str, Any],
    evidence_item: dict[str, Any],
    result: dict[str, Any],
    suite_case: dict[str, Any],
) -> None:
    label = contract_case["id"]
    for field in ("surface", "command", "arguments", "fixture"):
        require(
            result[field] == suite_case[field],
            f"{label}: result {field} does not match the referenced suite case",
        )

    suite_comparisons = {
        comparison["dimension"]: comparison["normalizer"]
        for comparison in suite_case["comparisons"]
    }
    require(
        len(suite_comparisons) == len(suite_case["comparisons"]),
        f"{label}: referenced suite case has duplicate comparison dimensions",
    )
    result_comparisons: dict[str, dict[str, Any]] = {}
    for comparison in result["comparisons"]:
        dimension = comparison["dimension"]
        require(
            dimension not in result_comparisons,
            f"{label}: result has duplicate comparison dimension {dimension}",
        )
        result_comparisons[dimension] = comparison
    require(
        set(result_comparisons) == set(suite_comparisons),
        f"{label}: result comparison dimensions do not match the referenced suite case",
    )
    for dimension, normalizer in suite_comparisons.items():
        require(
            result_comparisons[dimension].get("normalizer") == normalizer,
            f"{label}: result normalizer for {dimension} does not match the referenced suite case",
        )

    outcome = evidence_item["outcome"]
    statuses = {comparison["status"] for comparison in result_comparisons.values()}
    if outcome == "pass":
        require(statuses == {"pass"}, f"{label}: passing evidence requires every comparison to pass")
    else:
        require("fail" in statuses, f"{label}: failing evidence requires a failed comparison")


def validate_artifact_file(
    case_root: Path,
    relative: str,
    expected_bytes: int,
    expected_sha256: str,
    label: str,
) -> None:
    require(safe_repo_path(relative), f"{label} path is unsafe")
    path = case_root / relative
    require(not path.is_symlink(), f"{label} must not be a symlink")
    resolved = path.resolve()
    require(
        resolved.is_relative_to(case_root),
        f"{label} escapes result directory",
    )
    require(resolved.is_file(), f"{label} does not exist")
    try:
        content = resolved.read_bytes()
    except OSError as error:
        raise ValidationError(f"cannot read {label}: {error}") from error
    require(len(content) == expected_bytes, f"{label} size mismatch")
    require(
        hashlib.sha256(content).hexdigest() == expected_sha256,
        f"{label} hash mismatch",
    )


def validate_result_artifacts(
    result_path: Path,
    result: dict[str, Any],
    label: str,
) -> None:
    case_root = result_path.parent.resolve()
    filenames = {
        "stdout": "stdout.bin",
        "stderr": "stderr.bin",
        "file_tree": "file-tree.json",
    }
    for role in ("reference", "candidate"):
        run = result["runs"][role]
        for artifact, filename in filenames.items():
            relative = run[f"{artifact}_artifact"]
            expected = f"{role}/{filename}"
            require(
                relative == expected,
                f"{label}: {role} {artifact} artifact must be {expected}",
            )
            validate_artifact_file(
                case_root,
                relative,
                run[f"{artifact}_bytes"],
                run[f"{artifact}_sha256"],
                f"{label}: {role} {artifact} artifact",
            )

    comparison_paths = {
        "exit": (),
        "stdout": (
            "normalized/reference-stdout.bin",
            "normalized/candidate-stdout.bin",
        ),
        "stderr": (
            "normalized/reference-stderr.bin",
            "normalized/candidate-stderr.bin",
        ),
        "filesystem": (
            "reference/file-tree.json",
            "candidate/file-tree.json",
        ),
    }
    for comparison in result["comparisons"]:
        dimension = comparison["dimension"]
        require(
            dimension in comparison_paths,
            f"{label}: unsupported comparison artifact dimension {dimension}",
        )
        artifacts = comparison["artifacts"]
        expected_paths = comparison_paths[dimension]
        require(
            len(artifacts) == len(expected_paths),
            f"{label}: comparison {dimension} must retain {len(expected_paths)} artifacts",
        )
        for artifact, expected in zip(artifacts, expected_paths, strict=True):
            require(
                artifact["path"] == expected,
                f"{label}: comparison {dimension} artifact must be {expected}",
            )
            validate_artifact_file(
                case_root,
                artifact["path"],
                artifact["bytes"],
                artifact["sha256"],
                f"{label}: comparison {dimension} artifact {expected}",
            )
        require(
            bool(comparison["evidence"]),
            f"{label}: comparison {dimension} lacks evidence",
        )


def validate_evidence(
    repo_root: Path,
    case: dict[str, Any],
    suite_cases: dict[tuple[str, str], dict[str, Any]],
) -> None:
    evidence = case["evidence"]
    require_sorted_unique(evidence, evidence_key, f"{case['id']}.evidence")
    suite_refs = {suite_key(reference) for reference in case["suite_cases"]}
    result_schema = load_object(repo_root / RESULT_SCHEMA_PATH, "differential result schema")
    outcomes: list[str] = []
    for item in evidence:
        key = (item["suite_id"], item["case_id"])
        require(key in suite_refs, f"{case['id']}: evidence has no matching suite_cases reference")
        require(key in suite_cases, f"{case['id']}: evidence references an unknown suite case")
        relative = item["result_path"]
        require(safe_repo_path(relative), f"{case['id']}: unsafe result path {relative}")
        path = (repo_root / relative).resolve()
        require(path.is_relative_to(repo_root), f"{case['id']}: result path escapes repository")
        result = load_object(path, "differential result")
        validate_json_schema(result_schema, result, f"differential result {path}")
        require(
            result["evidence_scope"] == "compatibility",
            f"{case['id']}: harness self-test result cannot count as compatibility evidence",
        )
        identities = result["implementation_identities"]
        require(
            identities["reference"]["executable_sha256"]
            != identities["candidate"]["executable_sha256"],
            f"{case['id']}: compatibility evidence cannot compare identical runtime identity",
        )
        require(result["suite_id"] == item["suite_id"], f"{case['id']}: result suite id mismatch")
        require(result["case_id"] == item["case_id"], f"{case['id']}: result case id mismatch")
        require(result["overall_status"] == item["outcome"], f"{case['id']}: result outcome mismatch")
        validate_result_binding(case, item, result, suite_cases[key])
        validate_result_artifacts(path, result, case["id"])
        outcomes.append(item["outcome"])

    status = case["evidence_status"]
    if status == "pass":
        require(bool(outcomes) and set(outcomes) == {"pass"}, f"{case['id']}: pass requires only passing result evidence")
    elif status == "fail":
        require("fail" in outcomes, f"{case['id']}: fail requires failing result evidence")
    else:
        require(not outcomes, f"{case['id']}: {status} must not contain result evidence")


def inventory_kind(
    identifier: str,
    inventory_by_id: dict[str, dict[str, Any]],
    subjects: dict[str, dict[str, Any]],
) -> str | None:
    if identifier in inventory_by_id:
        return inventory_by_id[identifier]["kind"]
    if identifier in subjects:
        return subjects[identifier]["kind"]
    return None


def validate_interaction_member_types(
    group: dict[str, Any],
    inventory_by_id: dict[str, dict[str, Any]],
    subjects: dict[str, dict[str, Any]],
) -> None:
    if group["review_status"] != "reviewed":
        return
    members = [member["id"] for member in group["members"]]
    kinds = [inventory_kind(identifier, inventory_by_id, subjects) for identifier in members]
    domain = group["domain"]
    option_count = sum(kind == "option" for kind in kinds)
    config_count = sum(kind == "config" for kind in kinds)
    support_count = sum(kind == "support_script" for kind in kinds)
    callback_count = sum(kind == "callback_protocol" for kind in kinds)
    error_count = sum(kind == "error_class" for kind in kinds)
    if domain == "option_option":
        require(option_count >= 2, f"{group['id']}: option_option requires at least two option members")
    elif domain == "option_config":
        require(option_count >= 1 and config_count >= 1, f"{group['id']}: option_config requires an option and an lcovrc member")
    elif domain == "callback":
        require(callback_count >= 1 and option_count + support_count >= 1, f"{group['id']}: callback requires a callback subject and an option or support script")
    else:
        control_count = option_count + config_count + callback_count
        require(error_count >= 1 and control_count >= 1, f"{group['id']}: error_control requires an error subject and a controlling surface")



def validate_regeneration(repo_root: Path, contract_path: Path) -> None:
    generator = Path(__file__).with_name("generate.py")
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(generator),
                "--repo-root",
                str(repo_root),
                "--output",
                str(contract_path),
                "--check",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise ValidationError(f"behavior contract regeneration failed: {detail.strip()}") from error
    require("stable" in completed.stdout, "generator check did not report stable output")


def validate_contract(
    *,
    repo_root: Path,
    upstream_root: Path,
    contract_path: Path,
    schema_path: Path,
    inventory_path: Path,
    test_map_path: Path,
    check_regeneration: bool,
) -> ValidationReport:
    repo_root = repo_root.resolve()
    upstream_root = upstream_root.resolve()
    contract_path = contract_path.resolve()
    schema_path = schema_path.resolve()
    inventory_path = inventory_path.resolve()
    test_map_path = test_map_path.resolve()

    contract = load_object(contract_path, "behavior contract")
    schema = load_object(schema_path, "behavior contract schema")
    require(
        schema.get("$id") == "https://ferricov.dev/schema/behavior-contract.schema.json",
        "unexpected behavior contract schema id",
    )
    validate_json_schema(schema, contract, "behavior contract")
    validate_canonical(contract_path, contract, "behavior contract")
    validate_canonical(schema_path, schema, "behavior contract schema")

    require(contract["upstream"] == {"release": UPSTREAM_RELEASE, "commit": UPSTREAM_COMMIT}, "contract upstream identity mismatch")
    require(
        contract["inputs"]
        == {
            "audit_contract": AUDIT_PATH,
            "fragment_schema": FRAGMENT_SCHEMA_PATH,
            "fragments": FRAGMENTS_PATH,
            "inventory": INVENTORY_PATH,
            "test_map": TEST_MAP_PATH,
            "suites": SUITES_PATH,
        },
        "contract input registry mismatch",
    )
    require(
        contract["required_interaction_domains"] == list(REQUIRED_INTERACTION_DOMAINS),
        "required interaction domains mismatch",
    )
    require("unreviewed" in contract["review_policy"].lower(), "review policy must define unreviewed handling")

    inventory = load_object(inventory_path, "inventory")
    test_map = load_object(test_map_path, "upstream test map")
    inventory_by_id, public_ids = index_inventory(inventory)
    test_by_path = index_test_map(test_map)
    behavior_ids = validate_behavior_import(contract, test_map)
    suites, suite_cases = load_suites(repo_root, contract["inputs"]["suites"])
    validate_audit_upstream_references(
        repo_root,
        upstream_root,
        contract["inputs"]["audit_contract"],
    )
    subjects_list = contract["subjects"]
    require_sorted_unique(subjects_list, lambda subject: subject["id"], "subjects")
    subjects = {subject["id"]: subject for subject in subjects_list}
    imported_subject_ids = {
        identifier
        for identifier, subject in subjects.items()
        if subject["origin"] == "reviewed_import"
    }
    for subject in subjects_list:
        if subject["origin"] == "reviewed_import":
            require(subject["review_status"] == "reviewed", f"{subject['id']}: reviewed import must remain reviewed")
            require(
                all(
                    source["repository"] == "ferricov"
                    and source["kind"] == "audit_contract"
                    and source["path"] == AUDIT_PATH
                    for source in subject["source_references"]
                ),
                f"{subject['id']}: reviewed import must resolve to the normative audit contract",
            )
    for subject in subjects_list:
        require(subject["behavior_groups"] == sorted(set(subject["behavior_groups"])), f"{subject['id']}.behavior_groups must be sorted and unique")
        require(set(subject["behavior_groups"]) <= behavior_ids, f"{subject['id']}: unknown behavior group")
        validate_sources(repo_root, upstream_root, subject["source_references"], [], inventory_by_id, subject["id"])

    interactions = contract["interaction_groups"]
    cases = contract["case_groups"]
    require_sorted_unique(interactions, lambda group: group["id"], "interaction_groups")
    require_sorted_unique(cases, lambda case: case["id"], "case_groups")
    interaction_by_id = {group["id"]: group for group in interactions}
    case_by_id = {case["id"]: case for case in cases}
    imported_cases = [
        case for case in cases if case["origin"] == "reviewed_import"
    ]

    registry_ids = (
        list(subjects)
        + [group["id"] for group in contract["behavior_groups"]]
        + list(interaction_by_id)
        + list(case_by_id)
    )
    require(len(registry_ids) == len(set(registry_ids)), "contract registry ids must be globally unique")

    target_ids = set(inventory_by_id) | set(subjects)
    for group in interactions:
        require(group["behavior_groups"] == sorted(set(group["behavior_groups"])), f"{group['id']}.behavior_groups must be sorted and unique")
        require(set(group["behavior_groups"]) <= behavior_ids, f"{group['id']}: unknown behavior group")
        member_ids = [member["id"] for member in group["members"]]
        require(member_ids == sorted(member_ids), f"{group['id']}.members must be sorted")
        require(len(member_ids) == len(set(member_ids)), f"{group['id']}.members must be unique by id")
        require(set(member_ids) <= target_ids, f"{group['id']}: unknown interaction member")
        require(group["planned_cases"] == sorted(set(group["planned_cases"])), f"{group['id']}.planned_cases must be sorted and unique")
        require(set(group["planned_cases"]) <= set(case_by_id), f"{group['id']}: unknown planned case")
        validate_sources(repo_root, upstream_root, group["source_references"], member_ids, inventory_by_id, group["id"])
        validate_interaction_member_types(group, inventory_by_id, subjects)

    item_by_id = {item["entry"]["id"]: item for item in public_inventory_entries(inventory)}
    primary_any: set[str] = set()
    primary_reviewed: set[str] = set()
    for case in cases:
        targets = case["targets"]
        require_sorted_unique(targets, lambda target: (target["id"], target["role"]), f"{case['id']}.targets")
        case_target_ids = [target["id"] for target in targets]
        require(len(case_target_ids) == len(set(case_target_ids)), f"{case['id']}.targets must be unique by id")
        require(set(case_target_ids) <= target_ids, f"{case['id']}: unknown target")
        primary_targets = [target["id"] for target in targets if target["role"] == "primary"]
        require(bool(primary_targets), f"{case['id']}: at least one primary target is required")
        primary_any.update(set(primary_targets) & public_ids)
        if (
            case["review_status"] == "reviewed"
            and case["applicability"]["status"] != "not_applicable"
        ):
            primary_reviewed.update(set(primary_targets) & public_ids)

        for field in ("behavior_groups", "interaction_groups", "comparison_dimensions", "upstream_tests"):
            require(case[field] == sorted(set(case[field])), f"{case['id']}.{field} must be sorted and unique")
        require(set(case["behavior_groups"]) <= behavior_ids, f"{case['id']}: unknown behavior group")
        require(set(case["interaction_groups"]) <= set(interaction_by_id), f"{case['id']}: unknown interaction group")
        if case["review_status"] == "reviewed":
            require(
                all(
                    interaction_by_id[identifier]["review_status"] == "reviewed"
                    for identifier in case["interaction_groups"]
                ),
                f"{case['id']}: reviewed case cannot reference an unreviewed interaction",
            )
        conditions = case["applicability"]["conditions"]
        require(conditions == sorted(set(conditions)), f"{case['id']}.applicability.conditions must be sorted and unique")
        if case["review_status"] == "reviewed" and case["applicability"]["status"] in {"conditional", "not_applicable"}:
            require(bool(conditions), f"{case['id']}: reviewed conditional applicability requires explicit conditions")

        validate_sources(repo_root, upstream_root, case["source_references"], case_target_ids, inventory_by_id, case["id"])
        for test_path in case["upstream_tests"]:
            require(test_path in test_by_path, f"{case['id']}: unknown upstream test {test_path}")
            test = test_by_path[test_path]
            require(
                test["review_status"] == "reviewed"
                and test["classification"] == "public_behavior"
                and test["evidence_scope"] in {"direct_public_behavior", "indirect_public_behavior"},
                f"{case['id']}: upstream test {test_path} cannot prove public semantics",
            )

        validate_suite_references(case, suites, suite_cases)
        validate_evidence(repo_root, case, suite_cases)
        if case["origin"] == "generated_skeleton":
            require(len(primary_targets) == 1 and primary_targets[0] in item_by_id, f"{case['id']}: generated skeleton primary target is not public")
            expected = make_case_skeleton(item_by_id[primary_targets[0]])
            require(case == expected, f"generated case skeleton drift: {case['id']}")
        elif case["origin"] == "reviewed_import":
            require(case["review_status"] == "reviewed", f"{case['id']}: reviewed case import must remain reviewed")
            require(
                set(primary_targets) <= imported_subject_ids,
                f"{case['id']}: reviewed case import must primarily target reviewed-import subjects",
            )
            require(
                all(
                    source["repository"] == "ferricov"
                    and source["kind"] == "audit_contract"
                    and source["path"] == AUDIT_PATH
                    for source in case["source_references"]
                ),
                f"{case['id']}: reviewed case import must resolve to the normative audit contract",
            )

    planned_import_subjects = {
        target["id"]
        for case in imported_cases
        for target in case["targets"]
        if target["role"] == "primary"
    }
    require(
        planned_import_subjects == imported_subject_ids,
        "every reviewed-import subject must have a reviewed-import primary planning case",
    )
    require(primary_any == public_ids, f"public entries without any primary case group: {sorted(public_ids - primary_any)}")

    for case in cases:
        for interaction_id in case["interaction_groups"]:
            require(case["id"] in interaction_by_id[interaction_id]["planned_cases"], f"{case['id']} and {interaction_id} are not reciprocal")
    interaction_surfaces = {
        "callback": {"callback"},
        "error_control": {"callback", "cli", "config"},
        "option_config": {"config"},
        "option_option": {"cli"},
    }
    for group in interactions:
        member_ids = {member["id"] for member in group["members"]}
        for case_id in group["planned_cases"]:
            planned_case = case_by_id[case_id]
            require(group["id"] in planned_case["interaction_groups"], f"{group['id']} and {case_id} are not reciprocal")
            require(planned_case["review_status"] == "reviewed", f"{group['id']}: planned interaction case must be reviewed")
            if group["review_status"] == "reviewed":
                target_ids_for_case = {target["id"] for target in planned_case["targets"]}
                require(
                    member_ids <= target_ids_for_case,
                    f"{group['id']}: planned case {case_id} does not target every interaction member",
                )
                require(
                    planned_case["case_class"] == "interaction",
                    f"{group['id']}: planned case {case_id} must use the interaction case class",
                )
                require(
                    planned_case["surface"] in interaction_surfaces[group["domain"]],
                    f"{group['id']}: planned case {case_id} has the wrong interaction surface",
                )

    expected_totals = calculate_totals(contract, public_ids)
    require(contract["totals"] == expected_totals, f"contract totals mismatch: expected {expected_totals}, found {contract['totals']}")

    gaps = [
        f"public entry {identifier} has no reviewed primary case group"
        for identifier in sorted(public_ids - primary_reviewed)
    ]
    for domain in REQUIRED_INTERACTION_DOMAINS:
        if not any(
            group["domain"] == domain
            and group["critical"]
            and group["review_status"] == "reviewed"
            for group in interactions
        ):
            gaps.append(f"interaction domain {domain} has no reviewed critical interaction group")

    if check_regeneration:
        validate_regeneration(repo_root, contract_path)
    return ValidationReport(
        public_entries=len(public_ids),
        primary_case_coverage=len(primary_any),
        reviewed_primary_coverage=len(primary_reviewed),
        readiness_gaps=tuple(gaps),
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("current", "m0-ready"), default="current")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--upstream-root", type=Path, default=DEFAULT_UPSTREAM_ROOT)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--test-map", type=Path)
    parser.add_argument("--skip-regeneration", action="store_true")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    try:
        report = validate_contract(
            repo_root=root,
            upstream_root=args.upstream_root,
            contract_path=args.contract or root / CONTRACT_PATH,
            schema_path=args.schema or root / SCHEMA_PATH,
            inventory_path=args.inventory or root / INVENTORY_PATH,
            test_map_path=args.test_map or root / TEST_MAP_PATH,
            check_regeneration=not args.skip_regeneration,
        )
    except (OSError, KeyError, TypeError, ValidationError) as error:
        print(f"behavior contract {args.mode} validation failed: {error}", file=sys.stderr)
        return 1

    if args.mode == "m0-ready" and report.readiness_gaps:
        print(
            f"behavior contract m0-ready validation failed: {len(report.readiness_gaps)} gap(s)",
            file=sys.stderr,
        )
        for gap in report.readiness_gaps:
            print(f"- {gap}", file=sys.stderr)
        return 1

    print(
        f"behavior contract {args.mode} validation passed: "
        f"public={report.public_entries} "
        f"primary_plans={report.primary_case_coverage} "
        f"reviewed_primary={report.reviewed_primary_coverage} "
        f"m0_gaps={len(report.readiness_gaps)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
