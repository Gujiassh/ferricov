#!/usr/bin/env python3
"""Production semantic gate for the residual genhtml CLI planning suite.

Validates JSON Schema plus suite-local argv/normalizer identity for
`m0-genhtml-cli-residual-contract`. Invoked by `compat/verify.py` and by the
focused residual tests; mutation rejection must come from this module, not a
test-local duplicate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-genhtml-cli-residual-contract.json"
SUITE_SCHEMA_PATH = ROOT / "compat/schema/suite.schema.json"
SUITE_ID = "m0-genhtml-cli-residual-contract"
CONTROL = f"{SUITE_ID}-control"
FIXTURE = "compat/fixtures/m0-genhtml-cli-residual-contract"
EXACT_COMPARISONS = [
    {"dimension": dimension, "normalizer": "exact-v1"}
    for dimension in ("exit", "stdout", "stderr", "filesystem")
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
    },
    f"{SUITE_ID}-preserve": {
        "arguments": [
            "--config-file",
            "control.lcovrc",
            "--preserve",
            "--output-directory",
            "report",
            "input.info",
        ],
        "plan_id": "case.acceptance.command.genhtml.option.preserve",
        "boundary": "--preserve",
        "references": [
            ("parser_definition", "lib/lcovutil.pm", 1286),
            ("command_implementation", "lib/lcovutil.pm", 622),
            ("command_implementation", "lib/lcovutil.pm", 10167),
        ],
        "review_label": "preserve",
    },
    f"{SUITE_ID}-synthesize-missing": {
        "arguments": [
            "--config-file",
            "control.lcovrc",
            "--synthesize-missing",
            "--ignore-errors",
            "source,unsupported",
            "--output-directory",
            "report",
            "missing.info",
        ],
        "plan_id": "case.acceptance.command.genhtml.option.synthesize-missing",
        "boundary": "--synthesize-missing",
        "references": [
            ("parser_definition", "bin/genhtml", 7237),
            ("command_implementation", "bin/genhtml", 5727),
            ("command_implementation", "bin/genhtml", 5832),
        ],
        "review_label": "synthesize-missing",
    },
    f"{SUITE_ID}-multi": {
        "arguments": [
            "--config-file",
            "control.lcovrc",
            "--output-directory",
            "report",
            "input.info",
            "input2.info",
        ],
        "plan_id": "case.acceptance.command.genhtml.positional.tracefile-pattern",
        "boundary": "input.info input2.info",
        "references": [("parser_definition", "bin/genhtml", 7456)],
        "review_label": "multi",
    },
}


class ResidualSuiteValidationError(RuntimeError):
    """Raised when residual suite schema or semantic validation fails."""


def load_suite_schema() -> Draft202012Validator:
    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_suite_document(document: dict[str, Any]) -> None:
    """Validate suite JSON Schema and residual semantic contract.

    This is the production gate for residual suite identity. Callers must not
    reimplement argv/normalizer locks in tests.
    """
    validator = load_suite_schema()
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        raise ResidualSuiteValidationError(errors[0].message)

    if document.get("suite_id") != SUITE_ID:
        raise ResidualSuiteValidationError("suite_id mismatch")
    if document.get("evidence_scope") != "compatibility":
        raise ResidualSuiteValidationError("evidence_scope mismatch")
    if document.get("schema_version") != 1:
        raise ResidualSuiteValidationError("schema_version mismatch")

    cases = document.get("cases")
    if not isinstance(cases, list):
        raise ResidualSuiteValidationError("cases must be a list")
    expected_ids = list(CANONICAL_CASES)
    actual_ids = [case.get("id") for case in cases]
    if actual_ids != expected_ids:
        raise ResidualSuiteValidationError(
            f"case id set/order mismatch: {actual_ids!r} != {expected_ids!r}"
        )

    for case in cases:
        case_id = case["id"]
        expected = CANONICAL_CASES[case_id]
        if case.get("surface") != "cli":
            raise ResidualSuiteValidationError(f"{case_id}: surface must be cli")
        if case.get("command") != "genhtml":
            raise ResidualSuiteValidationError(f"{case_id}: command must be genhtml")
        if case.get("fixture") != FIXTURE:
            raise ResidualSuiteValidationError(f"{case_id}: fixture path mismatch")
        if case.get("arguments") != expected["arguments"]:
            raise ResidualSuiteValidationError(f"{case_id}: arguments mismatch")
        comparisons = case.get("comparisons")
        if not isinstance(comparisons, list) or len(comparisons) != 4:
            raise ResidualSuiteValidationError(f"{case_id}: comparisons must have 4 entries")
        dims: list[Any] = []
        for item in comparisons:
            if item.get("normalizer") != "exact-v1":
                raise ResidualSuiteValidationError(
                    f"{case_id}: normalizer must be exact-v1, found {item.get('normalizer')!r}"
                )
            dims.append(item.get("dimension"))
        if dims != ["exit", "stdout", "stderr", "filesystem"]:
            raise ResidualSuiteValidationError(
                f"{case_id}: comparison dimensions/order must be exit,stdout,stderr,filesystem"
            )
        if comparisons != EXACT_COMPARISONS:
            raise ResidualSuiteValidationError(f"{case_id}: comparisons must be exact-v1 matrix")


def validate_suite_path(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    validate_suite_document(document)
    return document


def validate_committed_suite() -> dict[str, Any]:
    if not SUITE_PATH.is_file():
        raise ResidualSuiteValidationError(
            f"residual suite missing: {SUITE_PATH.relative_to(ROOT)}"
        )
    return validate_suite_path(SUITE_PATH)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        type=Path,
        default=SUITE_PATH,
        help="suite document to validate (default: committed residual suite)",
    )
    args = parser.parse_args()
    document = validate_suite_path(args.suite)
    print(
        "M0_GENHTML_CLI_RESIDUAL_STATIC_CONTRACT_OK "
        f"suite_id={document['suite_id']} cases={len(document['cases'])} "
        f"normalizers=exact-v1 path={args.suite.relative_to(ROOT) if args.suite.is_absolute() and ROOT in args.suite.parents else args.suite}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ResidualSuiteValidationError as error:
        print(f"M0_GENHTML_CLI_RESIDUAL_STATIC_CONTRACT_FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
