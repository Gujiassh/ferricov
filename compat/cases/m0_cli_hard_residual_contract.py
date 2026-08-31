#!/usr/bin/env python3
"""Production semantic gate for hard residual CLI planning suite."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-cli-hard-residual-contract.json"
SUITE_SCHEMA_PATH = ROOT / "compat/schema/suite.schema.json"
SUITE_ID = "m0-cli-hard-residual-contract"
FIXTURE = "compat/fixtures/m0-cli-hard-residual-contract"
CMP2 = [{"dimension": d, "normalizer": "exact-v1"} for d in ("exit", "filesystem")]
CMP3 = [{"dimension": d, "normalizer": "exact-v1"} for d in ("exit", "stderr", "filesystem")]
CANONICAL_CASES = {
    f"{SUITE_ID}-geninfo-control": {"command":"geninfo","arguments":["src","--output-filename","out.info","--ignore-errors","source,unsupported"],"comparisons":CMP2},
    f"{SUITE_ID}-geninfo-large-file-invalid": {"command":"geninfo","arguments":["src","--large-file","(","--output-filename","out.info","--ignore-errors","source,unsupported"],"comparisons":CMP2},
    f"{SUITE_ID}-lcov-control": {"command":"lcov","arguments":["--capture","--directory","src","--output-file","out.info","--ignore-errors","source,unsupported"],"comparisons":CMP2},
    f"{SUITE_ID}-lcov-large-file-invalid": {"command":"lcov","arguments":["--capture","--directory","src","--large-file","(","--output-file","out.info","--ignore-errors","source,unsupported"],"comparisons":CMP2},
    f"{SUITE_ID}-geninfo-debug-control": {"command":"geninfo","arguments":["src","--output-filename","out.info","--ignore-errors","source,unsupported"],"comparisons":CMP3},
    f"{SUITE_ID}-geninfo-debug": {"command":"geninfo","arguments":["src","--debug","--output-filename","out.info","--ignore-errors","source,unsupported"],"comparisons":CMP3},
}

class HardResidualSuiteValidationError(RuntimeError):
    pass

def load_suite_schema() -> Draft202012Validator:
    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)

def validate_suite_document(document: dict[str, Any]) -> None:
    validator = load_suite_schema()
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        raise HardResidualSuiteValidationError(errors[0].message)
    if document.get("suite_id") != SUITE_ID or document.get("evidence_scope") != "compatibility" or document.get("schema_version") != 1:
        raise HardResidualSuiteValidationError("suite header mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or [c.get("id") for c in cases] != list(CANONICAL_CASES):
        raise HardResidualSuiteValidationError("case id set/order mismatch")
    for case in cases:
        exp = CANONICAL_CASES[case["id"]]
        if case.get("surface") != "cli" or case.get("command") != exp["command"] or case.get("fixture") != FIXTURE:
            raise HardResidualSuiteValidationError(f"{case['id']}: header mismatch")
        if case.get("arguments") != exp["arguments"] or case.get("comparisons") != exp["comparisons"]:
            raise HardResidualSuiteValidationError(f"{case['id']}: argv/comparisons mismatch")
        dims = {item["dimension"] for item in case["comparisons"]}
        if case["id"].endswith("-geninfo-debug") or case["id"].endswith("-geninfo-debug-control"):
            if dims != {"exit","stderr","filesystem"}:
                raise HardResidualSuiteValidationError(f"{case['id']}: debug cases require exit+stderr+filesystem")
            if "stdout" in dims:
                raise HardResidualSuiteValidationError(f"{case['id']}: stdout must stay excluded")
        else:
            if "stdout" in dims or "stderr" in dims:
                raise HardResidualSuiteValidationError(f"{case['id']}: stdout/stderr must stay excluded for large-file cases")

def validate_suite_path(path: Path) -> None:
    validate_suite_document(json.loads(path.read_text(encoding="utf-8")))

def validate_committed_suite() -> None:
    validate_suite_path(SUITE_PATH)

if __name__ == "__main__":
    validate_committed_suite()
    print(f"M0_CLI_HARD_RESIDUAL_STATIC_CONTRACT_OK suite_id={SUITE_ID}")
