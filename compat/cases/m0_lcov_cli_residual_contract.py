#!/usr/bin/env python3
"""Production semantic gate for lcov residual CLI planning suite."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-lcov-cli-residual-contract.json"
SUITE_SCHEMA_PATH = ROOT / "compat/schema/suite.schema.json"
SUITE_ID = "m0-lcov-cli-residual-contract"
FIXTURE = "compat/fixtures/m0-lcov-cli-residual-contract"
EXACT2 = [{"dimension": d, "normalizer": "exact-v1"} for d in ("exit", "filesystem")]
EXACT4 = [{"dimension": d, "normalizer": "exact-v1"} for d in ("exit", "stdout", "stderr", "filesystem")]
CANONICAL_CASES = {
    f"{SUITE_ID}-zero-control": {"arguments": ["--version"], "comparisons": EXACT2},
    f"{SUITE_ID}-zerocounters": {"arguments": ["--zerocounters", "--directory", "src"], "comparisons": EXACT2},
    f"{SUITE_ID}-failbr-control": {
        "arguments": ["--summary", "branch/base.info", "--branch-coverage", "--fail-under-branches", "50"],
        "comparisons": EXACT4,
    },
    f"{SUITE_ID}-fail-under-branches": {
        "arguments": ["--summary", "branch/base.info", "--branch-coverage", "--fail-under-branches", "101"],
        "comparisons": EXACT4,
    },
}

class LcovResidualSuiteValidationError(RuntimeError):
    pass

def load_suite_schema() -> Draft202012Validator:
    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)

def validate_suite_document(document: dict[str, Any]) -> None:
    validator = load_suite_schema()
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        raise LcovResidualSuiteValidationError(errors[0].message)
    if document.get("suite_id") != SUITE_ID or document.get("evidence_scope") != "compatibility" or document.get("schema_version") != 1:
        raise LcovResidualSuiteValidationError("suite header mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or [c.get("id") for c in cases] != list(CANONICAL_CASES):
        raise LcovResidualSuiteValidationError("case id set/order mismatch")
    for case in cases:
        exp = CANONICAL_CASES[case["id"]]
        if case.get("surface") != "cli" or case.get("command") != "lcov" or case.get("fixture") != FIXTURE:
            raise LcovResidualSuiteValidationError(f"{case['id']}: header fields mismatch")
        if case.get("arguments") != exp["arguments"] or case.get("comparisons") != exp["comparisons"]:
            raise LcovResidualSuiteValidationError(f"{case['id']}: argv/comparisons mismatch")

def validate_suite_path(path: Path) -> None:
    validate_suite_document(json.loads(path.read_text(encoding="utf-8")))

def validate_committed_suite() -> None:
    validate_suite_path(SUITE_PATH)

if __name__ == "__main__":
    validate_committed_suite()
    print(f"M0_LCOV_CLI_RESIDUAL_STATIC_CONTRACT_OK suite_id={SUITE_ID}")
