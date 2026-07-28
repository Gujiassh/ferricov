#!/usr/bin/env python3
"""Validate the pinned LCOV upstream-test map and its source checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
EXPECTED_SOURCE_FILES = 205
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", REPOSITORY_ROOT.parent / "lcov-upstream-reference")
)
DEFAULT_MAP = Path(__file__).with_name("upstream-test-map.json")
DEFAULT_SCHEMA = Path(__file__).parents[2] / "schema" / "upstream-test-map.schema.json"
EXPECTED_SCHEMA_SHA256 = "2571ce28f0a79edfb37d3ba17be262592e968660856f82505ca44534e3eda3cf"
CLASSIFICATIONS = ("fixture", "internal_test_infrastructure", "public_behavior")
REVIEW_STATUSES = ("reviewed", "unreviewed")
EVIDENCE_SCOPES = (
    "direct_public_behavior",
    "fixture_support",
    "indirect_public_behavior",
    "internal_only",
)
EXECUTION_STATES = ("active", "disabled", "not_applicable", "supporting")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CONSUMER_EVIDENCE = re.compile(r"^(tests/[^:]+):([1-9][0-9]*)$")


class ValidationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def enum_totals(entries: list[dict[str, object]], key: str, values: tuple[str, ...]) -> dict[str, int]:
    counts = Counter(str(entry[key]) for entry in entries)
    return {value: counts[value] for value in sorted(values)}


def load_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot load {label} {path}: {error}") from error
    require(isinstance(value, dict), f"{label} root must be an object")
    return value


def validate_registry(document: dict[str, object]) -> tuple[set[str], set[str]]:
    owners = document.get("owners")
    groups = document.get("behavior_groups")
    require(isinstance(owners, list), "owners must be an array")
    require(isinstance(groups, list), "behavior_groups must be an array")

    owner_ids: list[str] = []
    for index, owner in enumerate(owners):
        require(isinstance(owner, dict), f"owners[{index}] must be an object")
        require(set(owner) == {"id", "kind", "name", "description"}, f"owners[{index}] has unexpected fields")
        require(owner["kind"] in {"command", "support_script"}, f"owners[{index}] has invalid kind")
        for key in ("id", "name", "description"):
            require(isinstance(owner[key], str) and owner[key], f"owners[{index}].{key} must be non-empty")
        expected_id = f"{owner['kind'].replace('_', '-')}:{owner['name']}"
        require(owner["id"] == expected_id, f"owners[{index}] id does not match kind and name")
        owner_ids.append(owner["id"])
    require(owner_ids == sorted(owner_ids), "owners must be sorted by id")
    require(len(owner_ids) == len(set(owner_ids)), "owner ids must be unique")

    group_ids: list[str] = []
    for index, group in enumerate(groups):
        require(isinstance(group, dict), f"behavior_groups[{index}] must be an object")
        require(set(group) == {"id", "description"}, f"behavior_groups[{index}] has unexpected fields")
        require(isinstance(group["id"], str) and group["id"], f"behavior_groups[{index}].id must be non-empty")
        require(
            isinstance(group["description"], str) and group["description"],
            f"behavior_groups[{index}].description must be non-empty",
        )
        group_ids.append(group["id"])
    require(group_ids == sorted(group_ids), "behavior groups must be sorted by id")
    require(len(group_ids) == len(set(group_ids)), "behavior group ids must be unique")
    return set(owner_ids), set(group_ids)


def validate_entry(
    entry: object,
    index: int,
    owner_ids: set[str],
    group_ids: set[str],
) -> dict[str, object]:
    require(isinstance(entry, dict), f"entries[{index}] must be an object")
    required_keys = {
        "source",
        "sha256",
        "classification",
        "review_status",
        "evidence_scope",
        "upstream_execution",
        "owners",
        "behavior_groups",
        "rationale",
    }
    allowed_keys = required_keys | {"consumer_evidence"}
    require(required_keys <= set(entry) <= allowed_keys, f"entries[{index}] has unexpected fields")
    source = entry["source"]
    require(isinstance(source, str) and source.startswith("tests/"), f"entries[{index}].source must be under tests/")
    require(".." not in Path(source).parts and not Path(source).is_absolute(), f"entries[{index}].source is unsafe")
    require(isinstance(entry["sha256"], str) and SHA256.fullmatch(entry["sha256"]), f"{source}: invalid sha256")
    require(entry["classification"] in CLASSIFICATIONS, f"{source}: invalid classification")
    require(entry["review_status"] in REVIEW_STATUSES, f"{source}: invalid review status")
    require(entry["evidence_scope"] in EVIDENCE_SCOPES, f"{source}: invalid evidence scope")
    require(entry["upstream_execution"] in EXECUTION_STATES, f"{source}: invalid execution state")
    require(isinstance(entry["owners"], list), f"{source}: owners must be an array")
    require(entry["owners"] == sorted(set(entry["owners"])), f"{source}: owners must be sorted and unique")
    require(set(entry["owners"]) <= owner_ids, f"{source}: unknown owner reference")
    require(
        isinstance(entry["behavior_groups"], list) and entry["behavior_groups"],
        f"{source}: behavior_groups must be non-empty",
    )
    require(
        entry["behavior_groups"] == sorted(set(entry["behavior_groups"])),
        f"{source}: behavior_groups must be sorted and unique",
    )
    require(set(entry["behavior_groups"]) <= group_ids, f"{source}: unknown behavior group reference")
    require(isinstance(entry["rationale"], str) and len(entry["rationale"]) >= 40, f"{source}: rationale is too short")
    evidence = entry.get("consumer_evidence")
    if evidence is not None:
        require(isinstance(evidence, list), f"{source}: consumer_evidence must be an array")
        require(evidence == sorted(set(evidence)), f"{source}: consumer_evidence must be sorted and unique")
        require(
            all(isinstance(reference, str) and CONSUMER_EVIDENCE.fullmatch(reference) for reference in evidence),
            f"{source}: invalid consumer_evidence reference",
        )

    classification = entry["classification"]
    if classification == "public_behavior":
        require("consumer_evidence" not in entry, f"{source}: behavior driver must not claim fixture evidence")
        require(bool(entry["owners"]), f"{source}: public behavior requires an owner")
        require(
            entry["evidence_scope"]
            in {"direct_public_behavior", "indirect_public_behavior"},
            f"{source}: public behavior has inconsistent evidence scope",
        )
        require(
            entry["upstream_execution"] in {"active", "disabled"},
            f"{source}: public behavior has inconsistent execution state",
        )
    elif classification == "fixture":
        require(isinstance(entry.get("consumer_evidence"), list), f"{source}: fixture requires consumer_evidence")
        evidence = entry["consumer_evidence"]
        require(entry["evidence_scope"] == "fixture_support", f"{source}: fixture has inconsistent evidence scope")
        require(entry["upstream_execution"] == "supporting", f"{source}: fixture has inconsistent execution state")
        if entry["review_status"] == "reviewed":
            require(bool(entry["owners"]), f"{source}: reviewed fixture requires an owner")
            require(bool(evidence), f"{source}: reviewed fixture requires consumer evidence")
        else:
            require(not entry["owners"], f"{source}: unreviewed fixture must not claim an owner")
            require(not evidence, f"{source}: unreviewed fixture must not claim consumer evidence")
    else:
        require(not entry["owners"], f"{source}: internal harness entry must not claim a public owner")
        require(entry["evidence_scope"] == "internal_only", f"{source}: internal entry has inconsistent evidence scope")
        require(
            entry["upstream_execution"] == "not_applicable",
            f"{source}: internal entry has inconsistent execution state",
        )
        if entry["review_status"] == "unreviewed":
            require(not evidence, f"{source}: unreviewed internal entry must not claim consumer evidence")

    if entry["review_status"] == "unreviewed":
        require(
            "unreviewed" in entry["rationale"].lower(),
            f"{source}: unreviewed rationale must say why it remains unreviewed",
        )
    return entry


def validate_totals(document: dict[str, object], entries: list[dict[str, object]]) -> None:
    totals = document.get("totals")
    require(isinstance(totals, dict), "totals must be an object")
    expected = {
        "expected_source_files": EXPECTED_SOURCE_FILES,
        "mapped_source_files": len(entries),
        "unmapped_source_files": EXPECTED_SOURCE_FILES - len(entries),
        "classification": enum_totals(entries, "classification", CLASSIFICATIONS),
        "review_status": enum_totals(entries, "review_status", REVIEW_STATUSES),
        "evidence_scope": enum_totals(entries, "evidence_scope", EVIDENCE_SCOPES),
        "upstream_execution": enum_totals(entries, "upstream_execution", EXECUTION_STATES),
        "owner_coverage": {
            "assigned": sum(bool(entry["owners"]) for entry in entries),
            "not_applicable_internal": sum(
                entry["classification"] == "internal_test_infrastructure" and not entry["owners"]
                for entry in entries
            ),
            "unresolved": sum(entry["review_status"] == "unreviewed" for entry in entries),
        },
    }
    require(totals == expected, f"totals mismatch: expected {expected}, found {totals}")
    require(totals["mapped_source_files"] == EXPECTED_SOURCE_FILES, "map is incomplete")
    require(totals["unmapped_source_files"] == 0, "unmapped source files remain")
    require(totals["review_status"] == {"reviewed": 205, "unreviewed": 0}, "fixture review is incomplete")
    require(totals["owner_coverage"]["unresolved"] == 0, "unresolved fixture owners remain")


def validate_upstream(document: dict[str, object], upstream_root: Path, entries: list[dict[str, object]]) -> None:
    upstream = document.get("upstream")
    require(isinstance(upstream, dict), "upstream must be an object")
    require(
        upstream
        == {
            "release": "v2.5",
            "commit": UPSTREAM_COMMIT,
            "tests_tree": git(upstream_root, "rev-parse", "HEAD:tests"),
            "test_root": "tests",
        },
        "upstream identity or tests tree does not match the pinned checkout",
    )
    require(git(upstream_root, "rev-parse", "HEAD") == UPSTREAM_COMMIT, "upstream checkout is not at the pinned commit")
    dirty = git(upstream_root, "status", "--porcelain", "--untracked-files=all", "--", "tests")
    require(not dirty, "upstream tests tree is dirty")

    tests_root = upstream_root / "tests"
    actual_paths = sorted(path for path in tests_root.rglob("*") if path.is_file())
    actual_sources = [path.relative_to(upstream_root).as_posix() for path in actual_paths]
    mapped_sources = [str(entry["source"]) for entry in entries]
    require(
        len(actual_sources) == EXPECTED_SOURCE_FILES,
        f"filesystem has {len(actual_sources)} test files, expected 205",
    )
    require(mapped_sources == actual_sources, "mapped paths do not exactly match the upstream tests filesystem")

    tracked_sources = sorted(
        line for line in git(upstream_root, "ls-files", "--", "tests").splitlines() if line
    )
    require(tracked_sources == actual_sources, "upstream test filesystem and tracked file set differ")
    for path, entry in zip(actual_paths, entries, strict=True):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(entry["sha256"] == digest, f"{entry['source']}: content hash mismatch")
    actual_source_set = set(actual_sources)
    line_counts: dict[str, int] = {}
    for entry in entries:
        for reference in entry.get("consumer_evidence", []):
            match = CONSUMER_EVIDENCE.fullmatch(reference)
            require(match is not None, f"{entry['source']}: invalid consumer evidence")
            evidence_source, line_text = match.groups()
            require(evidence_source in actual_source_set, f"{entry['source']}: consumer evidence is not tracked")
            if evidence_source not in line_counts:
                content = (upstream_root / evidence_source).read_bytes()
                line_counts[evidence_source] = content.count(b"\n") + int(bool(content) and not content.endswith(b"\n"))
            require(
                int(line_text) <= line_counts[evidence_source],
                f"{entry['source']}: consumer evidence line is outside {evidence_source}",
            )


def validate_document(document: dict[str, object], upstream_root: Path) -> None:
    require(
        set(document)
        == {
            "schema_version",
            "upstream",
            "review_policy",
            "owners",
            "behavior_groups",
            "totals",
            "entries",
        },
        "map root has unexpected fields",
    )
    require(document["schema_version"] == 1, "schema_version must be 1")
    require(
        isinstance(document["review_policy"], str)
        and "unreviewed" in document["review_policy"].lower(),
        "review_policy must define unreviewed handling",
    )
    owner_ids, group_ids = validate_registry(document)
    raw_entries = document.get("entries")
    require(isinstance(raw_entries, list), "entries must be an array")
    entries = [validate_entry(entry, index, owner_ids, group_ids) for index, entry in enumerate(raw_entries)]
    sources = [str(entry["source"]) for entry in entries]
    require(sources == sorted(sources), "entries must be sorted by source")
    require(len(sources) == len(set(sources)), "entry source paths must be unique")
    require(len(entries) == EXPECTED_SOURCE_FILES, f"map has {len(entries)} entries, expected 205")
    validate_totals(document, entries)
    validate_upstream(document, upstream_root, entries)


def validate_schema(schema: dict[str, object], document: dict[str, object]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValidationError(f"JSON Schema rejected {location}: {error.message}")


def validate_regeneration(map_path: Path, upstream_root: Path) -> None:
    generator = Path(__file__).with_name("generate.py")
    with tempfile.TemporaryDirectory(prefix="ferricov-test-map-") as temp_dir:
        regenerated = Path(temp_dir) / "upstream-test-map.json"
        subprocess.run(
            [
                sys.executable,
                str(generator),
                "--upstream-root",
                str(upstream_root),
                "--output",
                str(regenerated),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        require(
            map_path.read_bytes() == regenerated.read_bytes(),
            "committed map differs from deterministic regeneration",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, default=DEFAULT_UPSTREAM_ROOT)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--skip-regeneration", action="store_true")
    args = parser.parse_args()
    try:
        document = load_json(args.map, "map")
        schema = load_json(args.schema, "schema")
        require(
            hashlib.sha256(args.schema.read_bytes()).hexdigest()
            == EXPECTED_SCHEMA_SHA256,
            "schema content does not match the pinned upstream-test-map schema",
        )
        require(
            schema.get("$id")
            == "https://ferricov.dev/schema/upstream-test-map.schema.json",
            "unexpected schema id",
        )
        validate_schema(schema, document)
        canonical = json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
        require(args.map.read_text(encoding="utf-8") == canonical, "map is not canonically formatted JSON")
        validate_document(document, args.upstream_root.resolve())
        if not args.skip_regeneration:
            validate_regeneration(args.map, args.upstream_root.resolve())
    except (OSError, subprocess.CalledProcessError, SchemaError, ValidationError) as error:
        print(f"upstream-test-map validation failed: {error}", file=sys.stderr)
        return 1
    totals = document["totals"]
    print(
        f"validated {args.map}: mapped={totals['mapped_source_files']} "
        f"reviewed={totals['review_status']['reviewed']} "
        f"unreviewed={totals['review_status']['unreviewed']} "
        f"unmapped={totals['unmapped_source_files']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
