#!/usr/bin/env python3
"""Generate and validate M0 configuration discovery and precedence suites."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
CASES_ROOT = ROOT / "compat/cases"
FIXTURE_ROOT = ROOT / "compat/fixtures/m0-config-contract"
CONTRACT_PATH = FIXTURE_ROOT / "case-contract.json"
INVENTORY_PATH = ROOT / "compat/inventory/v2.5.json"
SUITE_SCHEMA_PATH = ROOT / "compat/schema/suite.schema.json"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"

BASE_SUITE = "m0-config-contract-base"
ENV_SUITE = "m0-config-contract-env"
HOME_FIRST_SUITE = "m0-config-contract-home-first"
LCOV_HOME_SUITE = "m0-config-contract-lcov-home"
SUITE_IDS = (BASE_SUITE, ENV_SUITE, HOME_FIRST_SUITE, LCOV_HOME_SUITE)

CLEAN_ENVIRONMENT_ALLOWLIST = {
    "HOME": "{workdir}",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "TZ": "UTC",
}
SUITE_ENVIRONMENT_OVERRIDES = {
    BASE_SUITE: {},
    ENV_SUITE: {
        "FERRICOV_RC_BRANCH": "1",
        "FERRICOV_RC_LEFT": "",
        "FERRICOV_RC_RIGHT": "1",
    },
    HOME_FIRST_SUITE: {
        "HOME": "{workdir}/home",
        "LCOV_HOME": "{workdir}/lcov-home",
    },
    LCOV_HOME_SUITE: {
        "HOME": "{workdir}/missing-home",
        "LCOV_HOME": "{workdir}/lcov-home",
    },
}

COMMON_FIXTURE = "compat/fixtures/m0-config-contract/common"
HOME_AUTO_FIXTURE = "compat/fixtures/m0-config-contract/home-auto"
ENV_FIXTURE = "compat/fixtures/m0-config-contract/env"
HOME_FIRST_FIXTURE = "compat/fixtures/m0-config-contract/home-first"
LCOV_HOME_FIXTURE = "compat/fixtures/m0-config-contract/lcov-home"

BRANCH = "lcovrc.branch-coverage"
CONFIG_INCLUDE = "lcovrc.config-file"
CLI_BRANCH = "command.lcov.option.branch-coverage"
CLI_CONFIG = "command.lcov.option.config-file"
CLI_IGNORE = "command.lcov.option.ignore-errors"
CLI_NO_BRANCH = "command.lcov.option.no-branch-coverage"
CLI_RC = "command.lcov.option.rc"
CLI_SUMMARY = "command.lcov.option.summary"
EXPECTED_LINKED_ENTRIES = {
    BRANCH,
    CONFIG_INCLUDE,
    CLI_BRANCH,
    CLI_CONFIG,
    CLI_IGNORE,
    CLI_NO_BRANCH,
    CLI_RC,
    CLI_SUMMARY,
}


class ConfigContractError(RuntimeError):
    """The generated configuration contract is incomplete or inconsistent."""


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparisons() -> list[dict[str, str]]:
    return [
        {"dimension": dimension, "normalizer": "exact-v1"}
        for dimension in ("exit", "stdout", "stderr", "filesystem")
    ]


def definition(
    case_id: str,
    suite_id: str,
    fixture: str,
    arguments: list[str],
    inventory_entries: list[str],
    *,
    exit_code: int,
    branch_summary: str,
    stderr_contains: list[str] | None = None,
) -> dict[str, Any]:
    fragments = stderr_contains or []
    return {
        "case": {
            "id": case_id,
            "surface": "config",
            "command": "lcov",
            "arguments": arguments,
            "fixture": fixture,
            "comparisons": comparisons(),
        },
        "link": {
            "suite_id": suite_id,
            "case_id": case_id,
            "inventory_entries": sorted(inventory_entries),
            "expected": {
                "exit_code": exit_code,
                "branch_summary": branch_summary,
                "stderr_empty": not fragments,
                "stderr_contains": sorted(fragments),
            },
        },
    }


def case_definitions() -> list[dict[str, Any]]:
    summary = [CLI_SUMMARY, BRANCH]
    explicit = [CLI_CONFIG, CLI_SUMMARY, BRANCH]
    include = [CLI_CONFIG, CLI_SUMMARY, BRANCH, CONFIG_INCLUDE]
    return [
        definition(
            "m0-config-base-duplicate-explicit-file",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "on.lcovrc", "--config-file", "on.lcovrc", "--summary", "trace.info"],
            explicit,
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-base-explicit-on",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "on.lcovrc", "--summary", "trace.info"],
            explicit,
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-base-explicit-order-off-on",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "off.lcovrc", "--config-file", "on.lcovrc", "--summary", "trace.info"],
            explicit,
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-base-explicit-order-on-off",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "on.lcovrc", "--config-file", "off.lcovrc", "--summary", "trace.info"],
            explicit,
            exit_code=0,
            branch_summary="absent",
        ),
        definition(
            "m0-config-base-flag-disables-file-on",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "on.lcovrc", "--no-branch-coverage", "--summary", "trace.info"],
            [*explicit, CLI_NO_BRANCH],
            exit_code=0,
            branch_summary="absent",
        ),
        definition(
            "m0-config-base-flag-enables-file-off",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "off.lcovrc", "--branch-coverage", "--summary", "trace.info"],
            [*explicit, CLI_BRANCH],
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-base-home-discovery",
            BASE_SUITE,
            HOME_AUTO_FIXTURE,
            ["--summary", "trace.info"],
            summary,
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-base-explicit-bypasses-home",
            BASE_SUITE,
            HOME_AUTO_FIXTURE,
            ["--config-file", "explicit-off.lcovrc", "--summary", "trace.info"],
            explicit,
            exit_code=0,
            branch_summary="absent",
        ),
        definition(
            "m0-config-base-include-loop",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "loop-a.lcovrc", "--summary", "trace.info"],
            include,
            exit_code=25,
            branch_summary="absent",
            stderr_contains=["config file inclusion loop detected"],
        ),
        definition(
            "m0-config-base-inline-include-stops-parent",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "inline-order.lcovrc", "--summary", "trace.info"],
            include,
            exit_code=0,
            branch_summary="present",
            stderr_contains=["readline() on closed filehandle HANDLE"],
        ),
        definition(
            "m0-config-base-missing-env",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "missing-env.lcovrc", "--summary", "trace.info"],
            explicit,
            exit_code=255,
            branch_summary="absent",
            stderr_contains=["uses environment variable 'FERRICOV_MISSING'"],
        ),
        definition(
            "m0-config-base-missing-env-ignored",
            BASE_SUITE,
            COMMON_FIXTURE,
            [
                "--config-file",
                "missing-env.lcovrc",
                "--ignore-errors",
                "usage",
                "--summary",
                "trace.info",
            ],
            [*explicit, CLI_IGNORE],
            exit_code=0,
            branch_summary="absent",
            stderr_contains=["uses environment variable 'FERRICOV_MISSING'"],
        ),
        definition(
            "m0-config-base-missing-explicit-is-early",
            BASE_SUITE,
            COMMON_FIXTURE,
            [
                "--config-file",
                "missing.lcovrc",
                "--ignore-errors",
                "usage",
                "--summary",
                "trace.info",
            ],
            [CLI_CONFIG, CLI_IGNORE, CLI_SUMMARY],
            exit_code=2,
            branch_summary="absent",
            stderr_contains=["cannot read configuration file 'missing.lcovrc'"],
        ),
        definition(
            "m0-config-base-no-discovery-control",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--summary", "trace.info"],
            summary,
            exit_code=0,
            branch_summary="absent",
        ),
        definition(
            "m0-config-base-rc-overrides-file",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "off.lcovrc", "--rc", "branch_coverage=1", "--summary", "trace.info"],
            [*explicit, CLI_RC],
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-base-relative-include",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "include-on.lcovrc", "--summary", "trace.info"],
            include,
            exit_code=0,
            branch_summary="present",
            stderr_contains=["readline() on closed filehandle HANDLE"],
        ),
        definition(
            "m0-config-base-unknown-file-key-is-silent",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--config-file", "unknown-file.lcovrc", "--summary", "trace.info"],
            [CLI_CONFIG, CLI_SUMMARY],
            exit_code=0,
            branch_summary="absent",
        ),
        definition(
            "m0-config-base-unknown-rc-key",
            BASE_SUITE,
            COMMON_FIXTURE,
            ["--rc", "ferricov_unknown_key=1", "--summary", "trace.info"],
            [CLI_RC, CLI_SUMMARY],
            exit_code=2,
            branch_summary="absent",
            stderr_contains=["unknown/unsupported key 'ferricov_unknown_key'"],
        ),
        definition(
            "m0-config-env-multiple-expansion",
            ENV_SUITE,
            ENV_FIXTURE,
            ["--config-file", "env-multiple.lcovrc", "--summary", "trace.info"],
            explicit,
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-env-single-expansion",
            ENV_SUITE,
            ENV_FIXTURE,
            ["--config-file", "env-one.lcovrc", "--summary", "trace.info"],
            explicit,
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-home-first-wins-over-lcov-home",
            HOME_FIRST_SUITE,
            HOME_FIRST_FIXTURE,
            ["--summary", "trace.info"],
            summary,
            exit_code=0,
            branch_summary="present",
        ),
        definition(
            "m0-config-lcov-home-fallback",
            LCOV_HOME_SUITE,
            LCOV_HOME_FIXTURE,
            ["--summary", "trace.info"],
            summary,
            exit_code=0,
            branch_summary="present",
        ),
    ]


def inventory_entries(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = {entry["id"]: entry for entry in inventory["config_keys"]}
    for command in inventory["commands"]:
        for entry in [*command["options"], *command["positional_arguments"]]:
            entries[entry["id"]] = entry
    return entries


def suite_document(suite_id: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "suite_id": suite_id,
        "evidence_scope": "compatibility",
        "cases": sorted(cases, key=lambda case: case["id"]),
    }


def build_documents(inventory: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    definitions = case_definitions()
    suites = {
        suite_id: suite_document(
            suite_id,
            [item["case"] for item in definitions if item["link"]["suite_id"] == suite_id],
        )
        for suite_id in SUITE_IDS
    }
    suite_records = []
    for suite_id in SUITE_IDS:
        encoded = canonical_json(suites[suite_id]).encode("ascii")
        suite_records.append(
            {
                "suite_id": suite_id,
                "path": f"compat/cases/{suite_id}.json",
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "case_count": len(suites[suite_id]["cases"]),
                "environment_overrides": SUITE_ENVIRONMENT_OVERRIDES[suite_id],
            }
        )
    contract = {
        "schema_version": 1,
        "upstream_commit": UPSTREAM_COMMIT,
        "inventory": {
            "path": "compat/inventory/v2.5.json",
            "sha256": file_sha256(INVENTORY_PATH),
        },
        "suite_schema": {
            "path": "compat/schema/suite.schema.json",
            "sha256": file_sha256(SUITE_SCHEMA_PATH),
        },
        "clean_environment": {
            "inherit_parent": False,
            "allowlist": CLEAN_ENVIRONMENT_ALLOWLIST,
        },
        "semantic_oracle": (
            "Exact exit status plus presence or absence of the branches summary line; "
            "required stderr fragments bind failure category or the pinned include warning."
        ),
        "suites": suite_records,
        "cases": sorted((item["link"] for item in definitions), key=lambda item: item["case_id"]),
    }
    validate_documents(suites, contract, inventory)
    return suites, contract


def validate_documents(
    suites: dict[str, dict[str, Any]],
    contract: dict[str, Any],
    inventory: dict[str, Any],
) -> None:
    if set(suites) != set(SUITE_IDS):
        raise ConfigContractError("configuration suite set drift")
    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    all_cases: dict[str, tuple[str, dict[str, Any]]] = {}
    for suite_id in SUITE_IDS:
        validator.validate(suites[suite_id])
        if not suites[suite_id]["cases"]:
            raise ConfigContractError(f"empty configuration suite: {suite_id}")
        for case in suites[suite_id]["cases"]:
            if case["id"] in all_cases:
                raise ConfigContractError(f"duplicate configuration case ID: {case['id']}")
            all_cases[case["id"]] = (suite_id, case)
            if case["surface"] != "config" or case["command"] != "lcov":
                raise ConfigContractError(f"configuration case identity drift: {case['id']}")
            if case["comparisons"] != comparisons():
                raise ConfigContractError(f"configuration comparison drift: {case['id']}")
            fixture = ROOT / case["fixture"]
            if not fixture.is_dir() or not (fixture / "trace.info").is_file():
                raise ConfigContractError(f"configuration fixture is incomplete: {case['fixture']}")

    if len(all_cases) != 22:
        raise ConfigContractError(f"expected 22 configuration cases, found {len(all_cases)}")
    records = {record["suite_id"]: record for record in contract["suites"]}
    if set(records) != set(SUITE_IDS):
        raise ConfigContractError("configuration contract suite set drift")
    for suite_id in SUITE_IDS:
        encoded = canonical_json(suites[suite_id]).encode("ascii")
        expected = {
            "suite_id": suite_id,
            "path": f"compat/cases/{suite_id}.json",
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "case_count": len(suites[suite_id]["cases"]),
            "environment_overrides": SUITE_ENVIRONMENT_OVERRIDES[suite_id],
        }
        if records[suite_id] != expected:
            raise ConfigContractError(f"configuration suite record drift: {suite_id}")

    links = {link["case_id"]: link for link in contract["cases"]}
    if len(links) != len(contract["cases"]) or set(links) != set(all_cases):
        raise ConfigContractError("configuration case link set drift")
    entries = inventory_entries(inventory)
    linked_entries: set[str] = set()
    for case_id, link in links.items():
        suite_id, _ = all_cases[case_id]
        if link["suite_id"] != suite_id:
            raise ConfigContractError(f"configuration case suite drift: {case_id}")
        if link["inventory_entries"] != sorted(set(link["inventory_entries"])):
            raise ConfigContractError(f"configuration inventory links are not unique: {case_id}")
        if not link["inventory_entries"]:
            raise ConfigContractError(f"configuration case lacks inventory ownership: {case_id}")
        for entry_id in link["inventory_entries"]:
            entry = entries.get(entry_id)
            if entry is None:
                raise ConfigContractError(f"unknown configuration inventory entry: {entry_id}")
            if entry["classification"] != "public" or entry["review_status"] != "reviewed":
                raise ConfigContractError(f"unqualified configuration inventory entry: {entry_id}")
            linked_entries.add(entry_id)
        expected = link["expected"]
        if expected["branch_summary"] not in {"present", "absent"}:
            raise ConfigContractError(f"invalid branch summary expectation: {case_id}")
        if expected["stderr_empty"] != (not expected["stderr_contains"]):
            raise ConfigContractError(f"stderr expectation is contradictory: {case_id}")
    if linked_entries != EXPECTED_LINKED_ENTRIES:
        raise ConfigContractError(
            f"configuration inventory coverage drift: {sorted(linked_entries)}"
        )
    if contract["inventory"]["sha256"] != file_sha256(INVENTORY_PATH):
        raise ConfigContractError("configuration contract inventory hash drift")
    if contract["suite_schema"]["sha256"] != file_sha256(SUITE_SCHEMA_PATH):
        raise ConfigContractError("configuration contract suite schema hash drift")
    if contract["clean_environment"] != {
        "inherit_parent": False,
        "allowlist": CLEAN_ENVIRONMENT_ALLOWLIST,
    }:
        raise ConfigContractError("configuration clean environment drift")


def build_artifacts() -> dict[Path, bytes]:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    suites, contract = build_documents(inventory)
    artifacts = {
        CASES_ROOT / f"{suite_id}.json": canonical_json(suites[suite_id]).encode("ascii")
        for suite_id in SUITE_IDS
    }
    artifacts[CONTRACT_PATH] = canonical_json(contract).encode("ascii")
    return artifacts


def validate_committed_artifacts(expected: dict[Path, bytes]) -> None:
    for path, content in expected.items():
        if not path.is_file():
            raise ConfigContractError(f"generated artifact is missing: {path.relative_to(ROOT)}")
        if path.read_bytes() != content:
            raise ConfigContractError(f"generated artifact drift: {path.relative_to(ROOT)}")


def write_artifacts(artifacts: dict[Path, bytes]) -> None:
    for path, content in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print(f"M0_CONFIG_ARTIFACTS_WRITTEN files={len(artifacts)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    first = build_artifacts()
    second = build_artifacts()
    if first != second:
        raise ConfigContractError("configuration generation is not byte-deterministic")
    if args.write:
        write_artifacts(first)
    validate_committed_artifacts(first)
    print(
        "M0_CONFIG_STATIC_CONTRACT_OK "
        f"suites={len(SUITE_IDS)} cases=22 linked_inventory_entries={len(EXPECTED_LINKED_ENTRIES)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
