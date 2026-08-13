#!/usr/bin/env python3
"""Production semantic gate for geninfo residual CLI planning suite."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-geninfo-cli-residual-contract.json"
SUITE_SCHEMA_PATH = ROOT / "compat/schema/suite.schema.json"
SUITE_ID = "m0-geninfo-cli-residual-contract"
FIXTURE = "compat/fixtures/m0-geninfo-cli-residual-contract"
CMP2 = [{"dimension": d, "normalizer": "exact-v1"} for d in ("exit", "filesystem")]
CANONICAL_CASES = {
    f"{SUITE_ID}-control": {"arguments": [".", "--output-filename", "out.info"], "comparisons": CMP2},
    f"{SUITE_ID}-output-filename": {"arguments": [".", "--output-filename", "custom.info"], "comparisons": CMP2},
    f"{SUITE_ID}-checksum-control": {"arguments": [".", "--checksum", "--output-filename", "out.info"], "comparisons": CMP2},
    f"{SUITE_ID}-no-checksum": {"arguments": [".", "--checksum", "--no-checksum", "--output-filename", "out.info"], "comparisons": CMP2},
}

class GeninfoResidualSuiteValidationError(RuntimeError):
    pass

def load_suite_schema() -> Draft202012Validator:
    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)

def validate_suite_document(document: dict[str, Any]) -> None:
    validator = load_suite_schema()
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        raise GeninfoResidualSuiteValidationError(errors[0].message)
    if document.get("suite_id") != SUITE_ID or document.get("evidence_scope") != "compatibility" or document.get("schema_version") != 1:
        raise GeninfoResidualSuiteValidationError("suite header mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or [c.get("id") for c in cases] != list(CANONICAL_CASES):
        raise GeninfoResidualSuiteValidationError("case id set/order mismatch")
    for case in cases:
        exp = CANONICAL_CASES[case["id"]]
        if case.get("surface") != "cli" or case.get("command") != "geninfo" or case.get("fixture") != FIXTURE:
            raise GeninfoResidualSuiteValidationError(f"{case['id']}: header fields mismatch")
        if case.get("arguments") != exp["arguments"] or case.get("comparisons") != exp["comparisons"]:
            raise GeninfoResidualSuiteValidationError(f"{case['id']}: argv/comparisons mismatch")
        dims = {item["dimension"] for item in case["comparisons"]}
        if "stdout" in dims or "stderr" in dims:
            raise GeninfoResidualSuiteValidationError(f"{case['id']}: stdout/stderr must stay excluded")

def validate_suite_path(path: Path) -> None:
    validate_suite_document(json.loads(path.read_text(encoding="utf-8")))

def validate_committed_suite() -> None:
    validate_suite_path(SUITE_PATH)

if __name__ == "__main__":
    validate_committed_suite()
    print(f"M0_GENINFO_CLI_RESIDUAL_STATIC_CONTRACT_OK suite_id={SUITE_ID}")
