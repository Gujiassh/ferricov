#!/usr/bin/env python3
"""Production semantic gate for genhtml hard CLI planning suite (history-script)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-genhtml-cli-hard-contract.json"
SUITE_SCHEMA_PATH = ROOT / "compat/schema/suite.schema.json"
SUITE_ID = "m0-genhtml-cli-hard-contract"
CONTROL = f"{SUITE_ID}-control"
FIXTURE = "compat/fixtures/m0-genhtml-cli-hard-contract"

EXACT4 = [
    {"dimension": d, "normalizer": "exact-v1"}
    for d in ("exit", "stdout", "stderr", "filesystem")
]

CANONICAL_CASES: dict[str, dict[str, Any]] = {
    CONTROL: {
        "arguments": [
            "--config-file",
            "control.lcovrc",
            "--output-directory",
            "report",
            "input.info",
        ],
        "comparisons": EXACT4,
    },
    f"{SUITE_ID}-history-script": {
        "arguments": [
            "--config-file",
            "control.lcovrc",
            "--history-script",
            "./history.sh",
            "--output-directory",
            "report",
            "input.info",
        ],
        "comparisons": EXACT4,
        "plan_id": "case.acceptance.command.genhtml.option.history-script",
    },
}


class HardSuiteValidationError(RuntimeError):
    """Raised when hard suite schema or semantic validation fails."""


def load_suite_schema() -> Draft202012Validator:
    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_suite_document(document: dict[str, Any]) -> None:
    validator = load_suite_schema()
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        raise HardSuiteValidationError(errors[0].message)
    if document.get("suite_id") != SUITE_ID:
        raise HardSuiteValidationError("suite_id mismatch")
    if document.get("evidence_scope") != "compatibility":
        raise HardSuiteValidationError("evidence_scope mismatch")
    if document.get("schema_version") != 1:
        raise HardSuiteValidationError("schema_version mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list):
        raise HardSuiteValidationError("cases must be a list")
    expected_ids = list(CANONICAL_CASES)
    actual_ids = [case.get("id") for case in cases]
    if actual_ids != expected_ids:
        raise HardSuiteValidationError(
            f"case id set/order mismatch: {actual_ids!r} != {expected_ids!r}"
        )
    for case in cases:
        case_id = case["id"]
        expected = CANONICAL_CASES[case_id]
        if case.get("surface") != "cli":
            raise HardSuiteValidationError(f"{case_id}: surface must be cli")
        if case.get("command") != "genhtml":
            raise HardSuiteValidationError(f"{case_id}: command must be genhtml")
        if case.get("fixture") != FIXTURE:
            raise HardSuiteValidationError(f"{case_id}: fixture path mismatch")
        if case.get("arguments") != expected["arguments"]:
            raise HardSuiteValidationError(f"{case_id}: arguments mismatch")
        if case.get("comparisons") != expected["comparisons"]:
            raise HardSuiteValidationError(f"{case_id}: comparisons mismatch")


def validate_suite_path(path: Path) -> None:
    validate_suite_document(json.loads(path.read_text(encoding="utf-8")))


def validate_committed_suite() -> None:
    validate_suite_path(SUITE_PATH)


if __name__ == "__main__":
    validate_committed_suite()
    print(f"M0_GENHTML_CLI_HARD_STATIC_CONTRACT_OK suite_id={SUITE_ID}")
