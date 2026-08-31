#!/usr/bin/env python3
"""Production semantic gate for residual genhtml lcovrc planning suite."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-lcovrc-genhtml-residual2-contract.json"
SUITE_SCHEMA_PATH = ROOT / "compat/schema/suite.schema.json"
SUITE_ID = "m0-lcovrc-genhtml-residual2-contract"
FIXTURE = "compat/fixtures/m0-lcovrc-genhtml-residual2-contract"
CMP2 = [{"dimension": d, "normalizer": "exact-v1"} for d in ("exit", "filesystem")]
CANONICAL_CASES = {
    "m0-lcovrc-genhtml-residual2-contract-control": {"command":"genhtml","arguments":["--config-file", "control.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-dark-mode": {"command":"genhtml","arguments":["--config-file", "dark-mode.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-flat-view": {"command":"genhtml","arguments":["--config-file", "flat-view.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-frames": {"command":"genhtml","arguments":["--config-file", "frames.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-footer": {"command":"genhtml","arguments":["--config-file", "footer.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-charset": {"command":"genhtml","arguments":["--config-file", "charset.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-desc-html": {"command":"genhtml","arguments":["--config-file", "desc-html.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-keep-descriptions": {"command":"genhtml","arguments":["--config-file", "keep-descriptions.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-synthesize-missing": {"command":"genhtml","arguments":["--config-file", "synthesize-missing.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-show-noncode-owners": {"command":"genhtml","arguments":["--config-file", "show-noncode-owners.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-show-function-proportion": {"command":"genhtml","arguments":["--config-file", "show-function-proportion.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-nav-resolution": {"command":"genhtml","arguments":["--config-file", "nav-resolution.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-nav-offset": {"command":"genhtml","arguments":["--config-file", "nav-offset.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-age-field-width": {"command":"genhtml","arguments":["--config-file", "age-field-width.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-owner-field-width": {"command":"genhtml","arguments":["--config-file", "owner-field-width.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
    "m0-lcovrc-genhtml-residual2-contract-date-labels": {"command":"genhtml","arguments":["--config-file", "date-labels.lcovrc", "--output-directory", "report", "input.info"],"comparisons":CMP2},
}

class LcovrcGenhtmlResidual2SuiteValidationError(RuntimeError):
    pass

def load_suite_schema() -> Draft202012Validator:
    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)

def validate_suite_document(document: dict[str, Any]) -> None:
    validator = load_suite_schema()
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        raise LcovrcGenhtmlResidual2SuiteValidationError(errors[0].message)
    if document.get("suite_id") != SUITE_ID or document.get("evidence_scope") != "compatibility" or document.get("schema_version") != 1:
        raise LcovrcGenhtmlResidual2SuiteValidationError("suite header mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or [c.get("id") for c in cases] != list(CANONICAL_CASES):
        raise LcovrcGenhtmlResidual2SuiteValidationError("case id set/order mismatch")
    for case in cases:
        exp = CANONICAL_CASES[case["id"]]
        if case.get("surface") != "config" or case.get("command") != exp["command"] or case.get("fixture") != FIXTURE:
            raise LcovrcGenhtmlResidual2SuiteValidationError(f"{case['id']}: header mismatch")
        if case.get("arguments") != exp["arguments"] or case.get("comparisons") != exp["comparisons"]:
            raise LcovrcGenhtmlResidual2SuiteValidationError(f"{case['id']}: argv/comparisons mismatch")
        dims = {item["dimension"] for item in case["comparisons"]}
        if "stdout" in dims or "stderr" in dims:
            raise LcovrcGenhtmlResidual2SuiteValidationError(f"{case['id']}: stdout/stderr must stay excluded")

def validate_suite_path(path: Path) -> None:
    validate_suite_document(json.loads(path.read_text(encoding="utf-8")))

def validate_committed_suite() -> None:
    validate_suite_path(SUITE_PATH)

if __name__ == "__main__":
    validate_committed_suite()
    print(f"M0_LCOVRC_GENHTML_RESIDUAL2_STATIC_CONTRACT_OK suite_id={SUITE_ID}")
