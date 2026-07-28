#!/usr/bin/env python3
"""Generate the aggregate M0 Oracle correctness case contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CLI_CONTRACT_PATH = ROOT / "compat/fixtures/m0-cli-contract/case-contract.json"
CONFIG_CONTRACT_PATH = ROOT / "compat/fixtures/m0-config-contract/case-contract.json"
OUTPUT_PATH = ROOT / "compat/correctness/m0-case-contract.json"
EXPECTED_CLI_CASES = 126
EXPECTED_CONFIG_CASES = 22
EXPECTED_CASES = EXPECTED_CLI_CASES + EXPECTED_CONFIG_CASES
EXPECTED_SUITES = 7


class AggregateContractError(RuntimeError):
    """The aggregate correctness contract is incomplete or inconsistent."""


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, ensure_ascii=True) + "\n"


def load_object(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AggregateContractError(f"cannot load component contract {path}: {error}") from error
    if not isinstance(document, dict):
        raise AggregateContractError(f"component contract is not an object: {path}")
    return document


def suite_case_count(document: dict[str, Any]) -> int:
    return sum(record["case_count"] for record in document["suites"])


def build_document(
    cli: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    document = dict(cli)
    document["suites"] = [*cli["suites"], *config["suites"]]
    document["cases"] = [*cli["cases"], *config["cases"]]
    document["semantic_oracle"] = config["semantic_oracle"]
    validate_document(document, cli, config)
    return document


def validate_component_identity(
    cli: dict[str, Any], config: dict[str, Any]
) -> None:
    shared_fields = (
        "schema_version",
        "upstream_commit",
        "inventory",
        "suite_schema",
        "clean_environment",
    )
    for field in shared_fields:
        if cli.get(field) != config.get(field):
            raise AggregateContractError(f"component contract {field} mismatch")
    if suite_case_count(cli) != EXPECTED_CLI_CASES:
        raise AggregateContractError("CLI component case count drift")
    if suite_case_count(config) != EXPECTED_CONFIG_CASES:
        raise AggregateContractError("configuration component case count drift")


def validate_document(
    document: dict[str, Any],
    cli: dict[str, Any],
    config: dict[str, Any],
) -> None:
    validate_component_identity(cli, config)
    suites = document["suites"]
    suite_ids = [record["suite_id"] for record in suites]
    if len(suites) != EXPECTED_SUITES or len(suite_ids) != len(set(suite_ids)):
        raise AggregateContractError("aggregate suite identity drift")
    if suite_case_count(document) != EXPECTED_CASES:
        raise AggregateContractError("aggregate case count drift")

    case_ids = [record["case_id"] for record in document["cases"]]
    if len(case_ids) != EXPECTED_CASES or len(case_ids) != len(set(case_ids)):
        raise AggregateContractError("aggregate case link identity drift")

    config_suite_ids = {record["suite_id"] for record in config["suites"]}
    expectations = [
        record
        for record in document["cases"]
        if record["suite_id"] in config_suite_ids
    ]
    if len(expectations) != EXPECTED_CONFIG_CASES or any(
        "expected" not in record for record in expectations
    ):
        raise AggregateContractError("configuration semantic expectations are incomplete")

    for suite in suites:
        path = ROOT / suite["path"]
        if not path.is_file():
            raise AggregateContractError(f"aggregate suite is missing: {suite['path']}")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != suite["sha256"]:
            raise AggregateContractError(f"aggregate suite hash mismatch: {suite['suite_id']}")
        suite_document = json.loads(content)
        if (
            suite_document["suite_id"] != suite["suite_id"]
            or len(suite_document["cases"]) != suite["case_count"]
        ):
            raise AggregateContractError(f"aggregate suite record mismatch: {suite['suite_id']}")


def build_artifact() -> bytes:
    cli = load_object(CLI_CONTRACT_PATH)
    config = load_object(CONFIG_CONTRACT_PATH)
    return canonical_json(build_document(cli, config)).encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    first = build_artifact()
    second = build_artifact()
    if first != second:
        raise AggregateContractError("aggregate generation is not byte-deterministic")
    if args.write:
        OUTPUT_PATH.write_bytes(first)
        print(f"M0_CORRECTNESS_CONTRACT_WRITTEN path={OUTPUT_PATH.relative_to(ROOT)}")
    if not OUTPUT_PATH.is_file():
        raise AggregateContractError("aggregate correctness contract is missing")
    if OUTPUT_PATH.read_bytes() != first:
        raise AggregateContractError("aggregate correctness contract drift")
    print(
        "M0_CORRECTNESS_CONTRACT_OK "
        f"suites={EXPECTED_SUITES} cases={EXPECTED_CASES} "
        f"cli={EXPECTED_CLI_CASES} config={EXPECTED_CONFIG_CASES}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
