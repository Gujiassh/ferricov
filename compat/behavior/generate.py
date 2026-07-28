#!/usr/bin/env python3
"""Build generated behavior fragments and the canonical merged contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


UPSTREAM_RELEASE = "v2.5"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
AUDIT_PATH = "specs/001-full-lcov-compatibility/callback-installation-contract.md"
INVENTORY_PATH = "compat/inventory/v2.5.json"
TEST_MAP_PATH = "compat/inventory/tests/upstream-test-map.json"
SUITES_PATH = "compat/cases"
FRAGMENTS_PATH = "compat/behavior/fragments"
MAIN_SCHEMA_PATH = "compat/schema/behavior-contract.schema.json"
SCHEMA_PATH = MAIN_SCHEMA_PATH
FRAGMENT_SCHEMA_PATH = "compat/schema/behavior-contract-fragment.schema.json"
CONTRACT_PATH = "compat/behavior/contract.json"
FRAGMENT_SCHEMA_ID = "https://ferricov.dev/schema/behavior-contract-fragment.schema.json"
MAX_FRAGMENT_LINES = 2_000
INVENTORY_BUCKETS = 8
CASE_CLASSES = (
    "acceptance",
    "data",
    "equivalence",
    "failure",
    "filesystem",
    "interaction",
    "rejection",
    "scale",
)
EVIDENCE_STATUSES = ("fail", "none", "pass", "planned")
REVIEW_STATUSES = ("reviewed", "unreviewed")
REQUIRED_INTERACTION_DOMAINS = (
    "callback",
    "error_control",
    "option_config",
    "option_option",
)
COMPARISON_DIMENSIONS = ("exit", "filesystem", "stderr", "stdout")
CONTENT_FIELDS = (
    "subjects",
    "behavior_groups",
    "interaction_groups",
    "case_groups",
)


class GenerationError(Exception):
    """Raised when fragment authoring or deterministic generation is invalid."""


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GenerationError(f"cannot load {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise GenerationError(f"{label} root must be an object")
    return value


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n").encode()


def line_count(rendered: bytes) -> int:
    return rendered.count(b"\n")


def schema_validator(
    main_schema: dict[str, Any],
    fragment_schema: dict[str, Any],
) -> tuple[Draft202012Validator, Draft202012Validator]:
    Draft202012Validator.check_schema(main_schema)
    Draft202012Validator.check_schema(fragment_schema)
    registry = Registry().with_resource(
        main_schema["$id"],
        Resource.from_contents(main_schema),
    )
    return (
        Draft202012Validator(main_schema),
        Draft202012Validator(fragment_schema, registry=registry),
    )


def validate_schema_document(
    validator: Draft202012Validator,
    document: dict[str, Any],
    label: str,
) -> None:
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise GenerationError(f"JSON Schema rejected {label} at {location}: {error.message}")


def require_sorted_unique(items: list[dict[str, Any]], label: str) -> None:
    ids = [item["id"] for item in items]
    if ids != sorted(ids):
        raise GenerationError(f"{label} must be sorted by id")
    if len(ids) != len(set(ids)):
        raise GenerationError(f"{label} ids must be unique")


def validate_fragment_document(
    fragment: dict[str, Any],
    label: str,
    validator: Draft202012Validator,
    *,
    expected_type: str | None = None,
    rendered: bytes | None = None,
) -> None:
    validate_schema_document(validator, fragment, label)
    if expected_type is not None and fragment["fragment_type"] != expected_type:
        raise GenerationError(
            f"{label} must have fragment_type={expected_type}, found {fragment['fragment_type']}"
        )
    for field in CONTENT_FIELDS:
        require_sorted_unique(fragment[field], f"{label}.{field}")
    data = rendered if rendered is not None else canonical_bytes(fragment)
    if line_count(data) > MAX_FRAGMENT_LINES:
        raise GenerationError(
            f"{label} has {line_count(data)} lines, exceeding {MAX_FRAGMENT_LINES}"
        )


def inventory_entries(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for command in inventory["commands"]:
        for option in command["options"]:
            entries.append({"entry": option, "kind": "option", "command": command["name"]})
        for positional in command["positional_arguments"]:
            entries.append({"entry": positional, "kind": "positional", "command": command["name"]})
    entries.extend(
        {"entry": entry, "kind": "config", "command": None}
        for entry in inventory["config_keys"]
    )
    entries.extend(
        {"entry": entry, "kind": "support_script", "command": None}
        for entry in inventory["support_scripts"]
    )
    return sorted(entries, key=lambda item: item["entry"]["id"])


def public_inventory_entries(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in inventory_entries(inventory)
        if item["entry"]["classification"] == "public"
        and item["entry"]["applicability"] != "not_applicable"
    ]


def make_source_references(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (
            {
                "repository": "lcov-v2.5",
                "kind": source["kind"],
                "path": source["path"],
                "line": source["line"],
            }
            for source in entry["source_references"]
        ),
        key=lambda source: (source["path"], source["line"], source["kind"]),
    )


def make_case_skeleton(item: dict[str, Any]) -> dict[str, Any]:
    entry = item["entry"]
    entry_id = entry["id"]
    surface = {
        "option": "cli",
        "positional": "cli",
        "config": "config",
        "support_script": "installation",
    }[item["kind"]]
    return {
        "id": f"case.acceptance.{entry_id}",
        "origin": "generated_skeleton",
        "case_class": "acceptance",
        "surface": surface,
        "description": (
            f"Unreviewed acceptance skeleton for {entry_id}; observable semantics, "
            "fixtures, and expected outcomes require manual adjudication."
        ),
        "targets": [{"id": entry_id, "role": "primary"}],
        "behavior_groups": [],
        "interaction_groups": [],
        "comparison_dimensions": list(COMPARISON_DIMENSIONS),
        "applicability": {
            "status": entry["applicability"],
            "conditions": [],
        },
        "review_status": "unreviewed",
        "evidence_status": "none",
        "source_references": make_source_references(entry),
        "upstream_tests": [],
        "suite_cases": [],
        "evidence": [],
    }


def fragment_document(
    *,
    fragment_id: str,
    fragment_type: str,
    description: str,
    subjects: Iterable[dict[str, Any]] = (),
    behavior_groups: Iterable[dict[str, Any]] = (),
    interaction_groups: Iterable[dict[str, Any]] = (),
    case_groups: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "$schema": FRAGMENT_SCHEMA_ID,
        "schema_version": 1,
        "fragment_id": fragment_id,
        "fragment_type": fragment_type,
        "description": description,
        "subjects": sorted(subjects, key=lambda item: item["id"]),
        "behavior_groups": sorted(behavior_groups, key=lambda item: item["id"]),
        "interaction_groups": sorted(interaction_groups, key=lambda item: item["id"]),
        "case_groups": sorted(case_groups, key=lambda item: item["id"]),
    }


def imported_behavior_groups(test_map: dict[str, Any]) -> list[dict[str, Any]]:
    return [
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


def inventory_domain(item: dict[str, Any]) -> str:
    if item["kind"] in {"option", "positional"}:
        return f"command-{item['command'].replace('.', '-')}"
    if item["kind"] == "config":
        return "config"
    return "support-scripts"


def inventory_bucket(identifier: str) -> int:
    digest = hashlib.sha256(identifier.encode()).digest()
    return int.from_bytes(digest[:4], "big") % INVENTORY_BUCKETS


def generated_fragments(
    inventory: dict[str, Any],
    test_map: dict[str, Any],
    authored_case_ids: set[str],
) -> dict[Path, dict[str, Any]]:
    fragments: dict[Path, dict[str, Any]] = {
        Path("generated/behavior-groups.json"): fragment_document(
            fragment_id="generated.behavior-groups",
            fragment_type="generated",
            description="Exact generated import of the stable upstream test-map behavior-group registry.",
            behavior_groups=imported_behavior_groups(test_map),
        )
    }
    domains = [
        f"command-{command['name'].replace('.', '-')}"
        for command in inventory["commands"]
    ] + ["config", "support-scripts"]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {
        (domain, bucket): []
        for domain in domains
        for bucket in range(INVENTORY_BUCKETS)
    }
    for item in public_inventory_entries(inventory):
        case = make_case_skeleton(item)
        if case["id"] in authored_case_ids:
            continue
        grouped[(inventory_domain(item), inventory_bucket(item["entry"]["id"]))].append(case)

    for (domain, bucket), cases in sorted(grouped.items()):
        path = Path(f"generated/inventory/{domain}-{bucket}.json")
        fragments[path] = fragment_document(
            fragment_id=f"generated.inventory.{domain}.{bucket}",
            fragment_type="generated",
            description=(
                f"Deterministic unreviewed public inventory skeleton bucket {bucket} "
                f"for the {domain} responsibility domain."
            ),
            case_groups=cases,
        )
    return fragments


def load_authored_fragments(
    fragments_root: Path,
    validator: Draft202012Validator,
) -> list[tuple[Path, dict[str, Any]]]:
    authored_root = fragments_root / "authored"
    if not authored_root.is_dir():
        raise GenerationError(f"authored fragment directory does not exist: {authored_root}")
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(authored_root.rglob("*.json")):
        fragment = load_object(path, "authored fragment")
        rendered = path.read_bytes()
        if rendered != canonical_bytes(fragment):
            raise GenerationError(f"authored fragment is not canonical sorted JSON: {path}")
        validate_fragment_document(
            fragment,
            str(path),
            validator,
            expected_type="authored",
            rendered=rendered,
        )
        loaded.append((path, fragment))
    if not loaded:
        raise GenerationError("no authored behavior fragments found")
    ids = [fragment["fragment_id"] for _, fragment in loaded]
    if len(ids) != len(set(ids)):
        raise GenerationError("authored fragment ids must be globally unique")
    return loaded


def validate_generated_fragments(
    fragments: dict[Path, dict[str, Any]],
    validator: Draft202012Validator,
) -> None:
    ids: list[str] = []
    for relative, fragment in sorted(fragments.items()):
        validate_fragment_document(
            fragment,
            str(relative),
            validator,
            expected_type="generated",
        )
        ids.append(fragment["fragment_id"])
    if len(ids) != len(set(ids)):
        raise GenerationError("generated fragment ids must be globally unique")


def verify_generated_files(
    fragments_root: Path,
    expected: dict[Path, dict[str, Any]],
) -> None:
    expected_paths = {fragments_root / relative for relative in expected}
    actual_paths = set((fragments_root / "generated").rglob("*.json"))
    if actual_paths != expected_paths:
        missing = sorted(str(path) for path in expected_paths - actual_paths)
        extra = sorted(str(path) for path in actual_paths - expected_paths)
        raise GenerationError(f"generated fragment file set mismatch: missing={missing}, extra={extra}")
    for relative, fragment in expected.items():
        path = fragments_root / relative
        if path.read_bytes() != canonical_bytes(fragment):
            raise GenerationError(f"generated fragment differs from deterministic build: {path}")


def write_generated_files(
    fragments_root: Path,
    expected: dict[Path, dict[str, Any]],
) -> None:
    actual_paths = set((fragments_root / "generated").rglob("*.json"))
    expected_paths = {fragments_root / relative for relative in expected}
    extra = sorted(actual_paths - expected_paths)
    if extra:
        raise GenerationError(
            "refusing to delete stale generated fragments automatically: "
            + ", ".join(str(path) for path in extra)
        )
    for relative, fragment in expected.items():
        path = fragments_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_bytes(fragment))


def calculate_totals(contract: dict[str, Any], public_ids: set[str]) -> dict[str, Any]:
    cases = contract["case_groups"]
    interactions = contract["interaction_groups"]
    primary_any = {
        target["id"]
        for case in cases
        for target in case["targets"]
        if target["role"] == "primary" and target["id"] in public_ids
    }
    primary_reviewed = {
        target["id"]
        for case in cases
        if case["review_status"] == "reviewed"
        and case["applicability"]["status"] != "not_applicable"
        for target in case["targets"]
        if target["role"] == "primary" and target["id"] in public_ids
    }
    reviewed_domains = {
        group["domain"]
        for group in interactions
        if group["review_status"] == "reviewed" and group["critical"]
    }
    case_classes = Counter(case["case_class"] for case in cases)
    case_reviews = Counter(case["review_status"] for case in cases)
    evidence = Counter(case["evidence_status"] for case in cases)
    interaction_reviews = Counter(group["review_status"] for group in interactions)
    return {
        "subjects": len(contract["subjects"]),
        "behavior_groups": len(contract["behavior_groups"]),
        "interaction_groups": len(interactions),
        "case_groups": len(cases),
        "public_inventory_entries": len(public_ids),
        "primary_case_coverage": len(primary_any),
        "reviewed_primary_coverage": len(primary_reviewed),
        "uncovered_public_entries": len(public_ids - primary_reviewed),
        "required_interaction_domains": len(REQUIRED_INTERACTION_DOMAINS),
        "reviewed_interaction_domains": len(reviewed_domains & set(REQUIRED_INTERACTION_DOMAINS)),
        "case_class": {name: case_classes[name] for name in CASE_CLASSES},
        "case_review_status": {name: case_reviews[name] for name in REVIEW_STATUSES},
        "case_evidence_status": {name: evidence[name] for name in EVIDENCE_STATUSES},
        "interaction_review_status": {
            name: interaction_reviews[name] for name in REVIEW_STATUSES
        },
    }


def merge_fragments(
    inventory: dict[str, Any],
    fragments: list[dict[str, Any]],
) -> dict[str, Any]:
    content = {field: [] for field in CONTENT_FIELDS}
    fragment_ids: list[str] = []
    for fragment in sorted(fragments, key=lambda item: item["fragment_id"]):
        fragment_ids.append(fragment["fragment_id"])
        for field in CONTENT_FIELDS:
            content[field].extend(fragment[field])
    if len(fragment_ids) != len(set(fragment_ids)):
        raise GenerationError("fragment ids must be globally unique")
    for field in CONTENT_FIELDS:
        content[field].sort(key=lambda item: item["id"])
        require_sorted_unique(content[field], f"merged {field}")
    all_ids = [item["id"] for field in CONTENT_FIELDS for item in content[field]]
    if len(all_ids) != len(set(all_ids)):
        duplicates = sorted({identifier for identifier in all_ids if all_ids.count(identifier) > 1})
        raise GenerationError(f"contract registry ids must be globally unique: {duplicates}")

    public_ids = {
        item["entry"]["id"]
        for item in public_inventory_entries(inventory)
    }
    contract: dict[str, Any] = {
        "$schema": "../schema/behavior-contract.schema.json",
        "schema_version": 1,
        "upstream": {
            "release": UPSTREAM_RELEASE,
            "commit": UPSTREAM_COMMIT,
        },
        "inputs": {
            "audit_contract": AUDIT_PATH,
            "fragment_schema": FRAGMENT_SCHEMA_PATH,
            "fragments": FRAGMENTS_PATH,
            "inventory": INVENTORY_PATH,
            "test_map": TEST_MAP_PATH,
            "suites": SUITES_PATH,
        },
        "review_policy": (
            "Generated skeletons are unreviewed omission guards only. They do not "
            "establish behavior, interaction, applicability, implementation, or "
            "compatibility claims. Inventory supplies classification, review, "
            "applicability, runtime-dependency, and source facts; this contract owns "
            "behavior, interaction, case-planning, and product-evidence relationships. "
            "Only authored reviewed groups contribute to M0 readiness; contract.json "
            "is generated only."
        ),
        "required_interaction_domains": list(REQUIRED_INTERACTION_DOMAINS),
        **content,
        "totals": {},
    }
    contract["totals"] = calculate_totals(contract, public_ids)
    return contract


def build(
    repo_root: Path,
    fragments_root: Path,
    inventory: dict[str, Any],
    test_map: dict[str, Any],
    main_validator: Draft202012Validator,
    fragment_validator: Draft202012Validator,
) -> tuple[dict[str, Any], dict[Path, dict[str, Any]]]:
    if inventory.get("schema_version") != 2:
        raise GenerationError("inventory schema_version must be 2")
    if inventory.get("upstream_release") != UPSTREAM_RELEASE:
        raise GenerationError("inventory upstream release mismatch")
    if inventory.get("upstream_commit") != UPSTREAM_COMMIT:
        raise GenerationError("inventory upstream commit mismatch")
    upstream = test_map.get("upstream")
    if not isinstance(upstream, dict) or upstream.get("release") != UPSTREAM_RELEASE:
        raise GenerationError("test map upstream release mismatch")
    if upstream.get("commit") != UPSTREAM_COMMIT:
        raise GenerationError("test map upstream commit mismatch")

    authored = load_authored_fragments(fragments_root, fragment_validator)
    authored_case_ids = {
        case["id"]
        for _, fragment in authored
        for case in fragment["case_groups"]
    }
    generated = generated_fragments(inventory, test_map, authored_case_ids)
    validate_generated_fragments(generated, fragment_validator)
    all_fragments = [fragment for _, fragment in authored] + list(generated.values())
    contract = merge_fragments(inventory, all_fragments)
    validate_schema_document(main_validator, contract, "merged behavior contract")
    return contract, generated


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--test-map", type=Path)
    parser.add_argument("--fragments", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--fragment-schema", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    inventory_path = (args.inventory or root / INVENTORY_PATH).resolve()
    test_map_path = (args.test_map or root / TEST_MAP_PATH).resolve()
    fragments_root = (args.fragments or root / FRAGMENTS_PATH).resolve()
    schema_path = (args.schema or root / MAIN_SCHEMA_PATH).resolve()
    fragment_schema_path = (args.fragment_schema or root / FRAGMENT_SCHEMA_PATH).resolve()
    output = (args.output or root / CONTRACT_PATH).resolve()
    try:
        inventory = load_object(inventory_path, "inventory")
        test_map = load_object(test_map_path, "test map")
        main_schema = load_object(schema_path, "behavior contract schema")
        fragment_schema = load_object(fragment_schema_path, "fragment schema")
        main_validator, fragment_validator = schema_validator(main_schema, fragment_schema)
        contract, generated = build(
            root,
            fragments_root,
            inventory,
            test_map,
            main_validator,
            fragment_validator,
        )
        rendered = canonical_bytes(contract)
        if args.check:
            verify_generated_files(fragments_root, generated)
            if not output.exists() or output.read_bytes() != rendered:
                raise GenerationError(f"{output} differs from deterministic fragment merge")
            print(
                f"behavior fragment regeneration is stable: fragments={len(generated)} "
                f"contract={output}"
            )
            return 0
        write_generated_files(fragments_root, generated)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(rendered)
    except (GenerationError, OSError, KeyError, TypeError) as error:
        print(f"behavior contract generation failed: {error}", file=sys.stderr)
        return 1

    print(
        f"generated {output}: generated_fragments={len(generated)} "
        f"behavior_groups={len(contract['behavior_groups'])} "
        f"interaction_groups={len(contract['interaction_groups'])} "
        f"case_groups={len(contract['case_groups'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
