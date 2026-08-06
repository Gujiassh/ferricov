#!/usr/bin/env python3
"""Generate and validate the pinned LCOV 2.5 tracefile input contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).with_name("v2.5.json")
SCHEMA_PATH = ROOT / "compat/schema/tracefile-contract.schema.json"
CORPUS_ROOT = ROOT / "compat/fixtures/m0-tracefiles"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"
CASES_PATH = CORPUS_ROOT / "oracle-cases.json"
BASELINE_PATH = CORPUS_ROOT / "oracle-baseline.json"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference")
)

EXPECTED_ARTIFACT_HASHES = {
    "compat/fixtures/m0-tracefiles/manifest.json": "71d6880fe4bb400a051411401e57cfcda0a451656a65917478705522563ab0d0",
    "compat/fixtures/m0-tracefiles/oracle-cases.json": "d9383f3e0bc7218806818c024dcb97744cf27816901b6afb9e1ff726fbb4e94e",
    "compat/fixtures/m0-tracefiles/oracle-baseline.json": "b586a1196d120126f618b56f5995b6a2cc9f3bd27b2c4ab10e0e27e7f955e09e",
    "compat/fixtures/m0-tracefiles/inspect_model.pl": "4aad74fb32b2976fdde85f7d0ab3476b230d9e27500158a2f2ca31d5e482972e",
    "compat/fixtures/m0-tracefiles/tf030-semantic-registry.json": "bf89058735cb801ebc46f78e37da1585f2cbe292bd63290361354563cca8e58c",
}
EXPECTED_RECORD_TAGS = (
    "TN", "SF", "KF", "VER", "FNL", "FNA", "FN", "FNDA", "FNF", "FNH",
    "BRDA", "BRF", "BRH", "MCDC", "MCF", "MCH", "DA", "LF", "LH",
    "end_of_record",
)
EXPECTED_FIXTURE_IDS = (
    'current-all-records',
    'legacy',
    'permissive-prefix',
    'malformed-tn',
    'malformed-sf',
    'malformed-kf',
    'malformed-ver',
    'malformed-da',
    'malformed-fn',
    'malformed-fnda',
    'malformed-fnl',
    'malformed-fna',
    'malformed-brda',
    'malformed-mcdc',
    'malformed-terminator',
    'malformed-unknown',
    'malformed-fnf-accepted',
    'malformed-fnh-accepted',
    'malformed-brf-accepted',
    'malformed-brh-accepted',
    'malformed-mcf-accepted',
    'malformed-mch-accepted',
    'malformed-lf-accepted',
    'malformed-lh-accepted',
    'bytes-crlf',
    'bytes-no-final-newline',
    'bytes-non-utf8',
    'bytes-nul-accepted',
    'numeric-boundary',
    'numeric-extra-spellings',
    'numeric-format-atoms',
    'numeric-negative',
    'numeric-nonnumeric',
    'numeric-malformed-exponent',
    'numeric-excessive',
    'numeric-zero-line',
    'numeric-negative-inf',
    'numeric-signed-zero',
    'numeric-fnda-negative',
    'numeric-fnda-nonnumeric',
    'numeric-fna-nonnumeric',
    'numeric-fna-malformed-exponent',
    'numeric-brda-nonnumeric',
    'numeric-mcdc-nondigit',
    'numeric-zero-brda',
    'numeric-zero-mcdc',
    'numeric-zero-fn',
    'numeric-zero-fn-end',
    'numeric-invalid-fnl-fields',
    'numeric-inf-excessive',
    'numeric-function-excessive',
    'numeric-function-source',
    'checksum-match',
    'checksum-mismatch',
    'checksum-missing',
    'checksum-duplicate',
    'checksum-source-cs',
    'numeric-tf030-fna-mirror',
    'numeric-tf030-candidate-matrix',
    'numeric-tf030-format-atoms-plan',
    'numeric-tf030-fna-mirror-plan',
    'numeric-tf030-candidate-plan',
    'state-late-tn-mcdc',
    'state-cross-sf-mcdc-success',
    'state-cross-sf-mcdc-duplicate',
    'ver-repeat-equal',
    'ver-repeat-different',
    'ver-per-source',
    'functions-current-core',
    'functions-current-missing-alias',
    'functions-zero-end',
    'functions-zero-start',
    'functions-mixed-merge',
    'functions-mixed-location-mismatch',
    'functions-mixed-range-mismatch',
    'functions-index-duplicate',
    'functions-index-unknown',
    'functions-index-scope-reset',
    'functions-index-tn-preserves',
    'branches-forms-core',
    'branches-u-modes',
    'branches-malformed-tail',
    'branches-malformed-tail-empty-taken',
    'branches-malformed-tail-empty-expression',
    'branches-expression-mismatch',
    'branches-expression-merge-left',
    'branches-expression-merge-right',
    'branches-order-gaps',
    'branches-noncontiguous',
    'branches-interleave',
    'branches-sort-signatures',
    'scale-medium',
    'scale-large',
)
EXPECTED_CASE_IDS = (
    'current-all-records.summary',
    'legacy.summary',
    'permissive-prefix.summary',
    'malformed-tn.summary',
    'malformed-sf.summary',
    'malformed-kf.summary',
    'malformed-ver.summary',
    'malformed-da.summary',
    'malformed-fn.summary',
    'malformed-fnda.summary',
    'malformed-fnl.summary',
    'malformed-fna.summary',
    'malformed-brda.summary',
    'malformed-mcdc.summary',
    'malformed-terminator.summary',
    'malformed-unknown.summary',
    'malformed-fnf-accepted.summary',
    'malformed-fnh-accepted.summary',
    'malformed-brf-accepted.summary',
    'malformed-brh-accepted.summary',
    'malformed-mcf-accepted.summary',
    'malformed-mch-accepted.summary',
    'malformed-lf-accepted.summary',
    'malformed-lh-accepted.summary',
    'bytes-crlf.summary',
    'bytes-no-final-newline.summary',
    'bytes-non-utf8.summary',
    'bytes-nul-accepted.summary',
    'numeric-boundary.summary',
    'numeric-extra-spellings.summary',
    'numeric-format-atoms.summary',
    'numeric-negative.summary',
    'numeric-nonnumeric.summary',
    'numeric-malformed-exponent.summary',
    'numeric-excessive.summary',
    'numeric-zero-line.summary',
    'numeric-negative-inf.summary',
    'numeric-signed-zero.summary',
    'numeric-fnda-negative.summary',
    'numeric-fnda-nonnumeric.summary',
    'numeric-fna-nonnumeric.summary',
    'numeric-fna-malformed-exponent.summary',
    'numeric-brda-nonnumeric.summary',
    'numeric-mcdc-nondigit.summary',
    'numeric-zero-mcdc.summary',
    'numeric-zero-fn.summary',
    'numeric-zero-fn-end.summary',
    'numeric-invalid-fnl-fields.summary',
    'numeric-inf-excessive.summary',
    'state-late-tn-mcdc.summary',
    'state-cross-sf-mcdc-success.summary',
    'state-cross-sf-mcdc-duplicate.summary',
    'ver-repeat-equal.summary',
    'ver-repeat-different.summary',
    'ver-per-source.summary',
    'functions-current-core.summary',
    'functions-current-missing-alias.summary',
    'functions-zero-end.summary',
    'functions-zero-start.summary',
    'functions-mixed-merge.summary',
    'functions-mixed-location-mismatch.summary',
    'functions-mixed-range-mismatch.summary',
    'functions-index-duplicate.summary',
    'functions-index-unknown.summary',
    'functions-index-scope-reset.summary',
    'functions-index-tn-preserves.summary',
    'branches-forms-core.summary',
    'branches-u-modes.summary',
    'branches-malformed-tail.summary',
    'branches-malformed-tail-empty-taken.summary',
    'branches-malformed-tail-empty-expression.summary',
    'branches-expression-mismatch.summary',
    'branches-order-gaps.summary',
    'branches-noncontiguous.summary',
    'branches-interleave.summary',
    'branches-sort-signatures.summary',
    'scale-medium.summary',
    'scale-large.summary',
    'current-all-records.canonical',
    'legacy.canonical',
    'permissive-prefix.canonical',
    'bytes-crlf.canonical',
    'bytes-no-final-newline.canonical',
    'bytes-non-utf8.canonical',
    'bytes-nul-accepted.canonical',
    'numeric-boundary.canonical',
    'ver-repeat-equal.canonical',
    'malformed-tn.ignore-format',
    'malformed-da.ignore-format',
    'malformed-ver.ignore-format',
    'numeric-negative.ignore-negative',
    'numeric-nonnumeric.ignore-format',
    'numeric-malformed-exponent.ignore-format',
    'numeric-excessive.ignore-excessive',
    'numeric-zero-line.ignore-format',
    'state-late-tn-mcdc.canonical',
    'state-late-tn-mcdc.semantic-snapshot',
    'state-cross-sf-mcdc-success.canonical',
    'state-cross-sf-mcdc-success.semantic-snapshot',
    'functions-current-core.canonical',
    'functions-current-core.semantic-snapshot',
    'functions-zero-end.canonical',
    'functions-mixed-merge.canonical',
    'functions-mixed-merge.semantic-snapshot',
    'functions-mixed-location-mismatch.canonical',
    'functions-mixed-range-mismatch.canonical',
    'functions-index-duplicate.canonical',
    'functions-index-unknown.canonical',
    'functions-index-scope-reset.canonical',
    'numeric-boundary.semantic-snapshot',
    'numeric-extra-spellings.canonical',
    'numeric-extra-spellings.semantic-snapshot',
    'numeric-format-atoms.default-stop',
    'numeric-format-atoms.ignore-negative',
    'numeric-format-atoms.ignore-format-negative.canonical',
    'numeric-format-atoms.ignore-format-negative.semantic-snapshot',
    'numeric-format-atoms.excessive-default-stop',
    'numeric-format-atoms.excessive-keep-going',
    'numeric-format-atoms.excessive-stop-on-error-0',
    'numeric-format-atoms.excessive-stop-on-error-1',
    'numeric-format-atoms.ignore-format-negative-excessive.canonical',
    'numeric-format-atoms.ignore-format-negative-excessive.semantic-snapshot',
    'numeric-signed-zero.canonical',
    'numeric-signed-zero.semantic-snapshot',
    'numeric-negative-inf.ignore-negative',
    'numeric-negative-inf.semantic-snapshot',
    'numeric-fnda-negative.ignore-negative',
    'numeric-fnda-nonnumeric.ignore-format',
    'numeric-fna-nonnumeric.ignore-format',
    'numeric-fna-nonnumeric.semantic-snapshot',
    'numeric-fna-malformed-exponent.ignore-format',
    'numeric-brda-nonnumeric.ignore-format',
    'numeric-mcdc-nondigit.ignore-format',
    'numeric-zero-brda.summary',
    'numeric-zero-mcdc.ignore-format',
    'numeric-zero-fn.ignore-format',
    'numeric-zero-fn-end.ignore-format',
    'numeric-zero-fn-end.semantic-snapshot',
    'numeric-invalid-fnl-fields.ignore-format',
    'numeric-invalid-fnl-fields.semantic-snapshot',
    'functions-zero-start.ignore-inconsistent-format',
    'functions-zero-start.semantic-snapshot',
    'numeric-function-excessive.default-stop',
    'numeric-function-excessive.erase-suppressed',
    'numeric-inf-excessive.ignore-excessive',
    'checksum-match.summary',
    'checksum-match.canonical',
    'checksum-mismatch.summary',
    'checksum-mismatch.ignore-version',
    'checksum-missing.summary',
    'checksum-missing.ignore-version-recompute',
    'checksum-duplicate.summary',
    'checksum-duplicate.ignore-version',
    'checksum-no-verify.canonical',
    'numeric-format-atoms.tf030.semantic-snapshot',
    'numeric-format-atoms.tf030-threshold.semantic-snapshot',
    'numeric-tf030-fna-mirror.default-stop',
    'numeric-tf030-fna-mirror.ignore-negative-stop-format',
    'numeric-tf030-fna-mirror.ignore-negative-format.canonical',
    'numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot',
    'numeric-tf030-fna-mirror.threshold-default-stop',
    'numeric-tf030-fna-mirror.threshold-ignore-all.canonical',
    'numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot',
    'numeric-tf030-candidates.default-stop',
    'numeric-tf030-candidates.ignore-negative.canonical',
    'numeric-tf030-candidates.ignore-negative.semantic-snapshot',
    'numeric-tf030-candidates.threshold-default-stop',
    'numeric-tf030-candidates.threshold-ignore-all.canonical',
    'numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot',
    'branches-forms-core.canonical',
    'branches-forms-core.semantic-snapshot',
    'branches-u-modes.canonical',
    'branches-u-modes.clear-unreachable',
    'branches-malformed-tail.canonical',
    'branches-malformed-tail-empty-taken.canonical',
    'branches-malformed-tail-empty-expression.canonical',
    'branches-expression-mismatch.canonical',
    'branches-expression-merge.canonical',
    'branches-expression-merge.semantic-snapshot',
    'branches-order-gaps.canonical',
    'branches-noncontiguous.canonical',
    'branches-noncontiguous.semantic-snapshot',
    'branches-interleave.canonical',
    'branches-sort-signatures.canonical',
)


class TracefileContractError(RuntimeError):
    """The tracefile contract is incomplete or inconsistent."""


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TracefileContractError(f"cannot load JSON document {path}: {error}") from error
    if not isinstance(value, dict):
        raise TracefileContractError(f"JSON document is not an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_reference(
    upstream_root: Path, path: str, line: int, role: str
) -> dict[str, Any]:
    source = upstream_root / path
    try:
        text = source.read_text(encoding="utf-8").splitlines()[line - 1]
    except (OSError, IndexError) as error:
        raise TracefileContractError(
            f"cannot resolve source reference {path}:{line}"
        ) from error
    return {"path": path, "line": line, "role": role, "text": text}


def record(
    upstream_root: Path,
    tag: str,
    category: str,
    parser_expression: str,
    match_mode: str,
    input_behavior: str,
    reader_line: int,
    canonical_form: str,
    malformed_fixture_id: str,
    writer_line: int | None,
    manual_line: int | None,
) -> dict[str, Any]:
    references = [
        source_reference(upstream_root, "lib/lcovutil.pm", reader_line, "reader")
    ]
    if writer_line is not None:
        references.append(
            source_reference(upstream_root, "lib/lcovutil.pm", writer_line, "writer")
        )
    if manual_line is not None:
        references.append(
            source_reference(
                upstream_root, "docs/man/geninfo.rst", manual_line, "manual"
            )
        )
    return {
        "id": f"tracefile.record.{tag.lower()}",
        "tag": tag,
        "category": category,
        "parser_expression": parser_expression,
        "match_mode": match_mode,
        "input_behavior": input_behavior,
        "writer_behavior": "emitted" if writer_line is not None else "not_emitted",
        "canonical_form": canonical_form,
        "malformed_fixture_id": malformed_fixture_id,
        "source_references": references,
        "review_status": "reviewed",
        "product_evidence": [],
    }


def records(upstream_root: Path) -> list[dict[str, Any]]:
    values = [
        record(upstream_root, "TN", "test", r"^TN:([^,]*)(,diff)?", "start", "semantic", 9084, "TN:<testname>", "malformed-tn", 9509, 680),
        record(upstream_root, "SF", "source", r"^[SK]F:(.*)", "start", "semantic", 9003, "SF:<source-path>", "malformed-sf", 9510, 686),
        record(upstream_root, "KF", "source", r"^[SK]F:(.*)", "start", "alternate_source", 9003, "never emitted; canonical output uses SF", "malformed-kf", None, None),
        record(upstream_root, "VER", "version", r"^VER:(.+)$", "full", "semantic", 9068, "VER:<version>", "malformed-ver", 9511, 692),
        record(upstream_root, "FNL", "function", r"^FNL:(\d+),(\d+)(,(\d+))?$", "full", "semantic", 9191, "FNL:<index>,<start>[,<end>]", "malformed-fnl", 9550, 704),
        record(upstream_root, "FNA", "function", r"^FNA:(\d+),([^,]+),(.+)$", "full", "semantic", 9202, "FNA:<index>,<count>,<alias>", "malformed-fna", 9558, 710),
        record(upstream_root, "FN", "function", r"^FN:(\d+),((\d+),)?(.+)$", "full", "legacy_function", 9154, "never emitted; canonical output uses FNL/FNA", "malformed-fn", None, 716),
        record(upstream_root, "FNDA", "function", r"^FNDA:([^,]+),(.+)$", "full", "legacy_function", 9181, "never emitted; canonical output uses FNL/FNA", "malformed-fnda", None, 724),
        record(upstream_root, "FNF", "summary", r"^(FN|BR|L|MC)[HF]", "start", "ignored_summary", 9402, "FNF:<count>", "malformed-fnf-accepted", 9561, 730),
        record(upstream_root, "FNH", "summary", r"^(FN|BR|L|MC)[HF]", "start", "ignored_summary", 9402, "FNH:<count>", "malformed-fnh-accepted", 9562, 731),
        record(upstream_root, "BRDA", "branch", r"^BRDA:(\d+),([ef]?)(U?)(\d+),(.+)$", "full", "semantic", 9217, "BRDA:<line>,[e|f][U]<block>,<expression>,<taken>", "malformed-brda", 9588, 739),
        record(upstream_root, "BRF", "summary", r"^(FN|BR|L|MC)[HF]", "start", "ignored_summary", 9402, "BRF:<count>", "malformed-brf-accepted", 9607, 808),
        record(upstream_root, "BRH", "summary", r"^(FN|BR|L|MC)[HF]", "start", "ignored_summary", 9402, "BRH:<count>", "malformed-brh-accepted", 9608, 814),
        record(upstream_root, "MCDC", "mcdc", r"^MCDC:(\d+),(U?)(\d+),([tf]),(\d+),(\d+),(.+)$", "full", "semantic", 9328, "MCDC:<line>,[U]<group-size>,<sense>,<count>,<index>,<expression>", "malformed-mcdc", 9636, 822),
        record(upstream_root, "MCF", "summary", r"^(FN|BR|L|MC)[HF]", "start", "ignored_summary", 9402, "MCF:<count>", "malformed-mcf-accepted", 9644, 879),
        record(upstream_root, "MCH", "summary", r"^(FN|BR|L|MC)[HF]", "start", "ignored_summary", 9402, "MCH:<count>", "malformed-mch-accepted", 9645, 885),
        record(upstream_root, "DA", "line", r"^DA:(\d+),([^,]+)(,([^,\s]+))?", "start", "semantic", 9103, "DA:<line>,<count>[,<checksum>]", "malformed-da", 9672, 893),
        record(upstream_root, "LF", "summary", r"^(FN|BR|L|MC)[HF]", "start", "ignored_summary", 9402, "LF:<count>", "malformed-lf-accepted", 9677, 902),
        record(upstream_root, "LH", "summary", r"^(FN|BR|L|MC)[HF]", "start", "ignored_summary", 9402, "LH:<count>", "malformed-lh-accepted", 9678, 901),
        record(upstream_root, "end_of_record", "terminator", r"^end_of_record", "start", "semantic", 9367, "end_of_record", "malformed-terminator", 9679, 908),
    ]
    return values


def lexical_rules(upstream_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": "tracefile.lexical.comment",
            "parser_expression": "^#",
            "match_mode": "start",
            "behavior": "A normalized line whose first byte is # is ignored; only explicitly added writer comments are emitted at file start.",
            "source_references": [
                source_reference(upstream_root, "lib/lcovutil.pm", 9001, "reader"),
                source_reference(upstream_root, "lib/lcovutil.pm", 9066, "reader"),
                source_reference(upstream_root, "lib/lcovutil.pm", 9484, "writer"),
                source_reference(upstream_root, "docs/man/geninfo.rst", 672, "manual"),
            ],
            "review_status": "reviewed",
            "product_evidence": [],
        },
        {
            "id": "tracefile.lexical.blank",
            "parser_expression": r"^\s*$",
            "match_mode": "full",
            "behavior": "Empty and Perl-whitespace-only normalized lines are ignored and never emitted.",
            "source_references": [
                source_reference(upstream_root, "lib/lcovutil.pm", 9405, "reader")
            ],
            "review_status": "reviewed",
            "product_evidence": [],
        },
    ]


def fallback_behavior(upstream_root: Path) -> dict[str, Any]:
    return {
        "id": "tracefile.fallback.unknown-nonblank-record",
        "behavior": "A nonblank, noncomment line unmatched by prior reader alternatives raises the ignorable format category.",
        "malformed_fixture_id": "malformed-unknown",
        "source_references": [
            source_reference(upstream_root, "lib/lcovutil.pm", 9409, "reader"),
            source_reference(upstream_root, "lib/lcovutil.pm", 9410, "reader"),
        ],
        "review_status": "reviewed",
        "product_evidence": [],
    }


def artifact_bindings() -> list[dict[str, str]]:
    bindings = []
    for relative, expected in EXPECTED_ARTIFACT_HASHES.items():
        path = ROOT / relative
        actual = sha256_file(path)
        if actual != expected:
            raise TracefileContractError(
                f"retained tracefile artifact drift: {relative} expected={expected} actual={actual}"
            )
        bindings.append({"path": relative, "sha256": actual})
    return bindings


def fixture_bindings() -> list[dict[str, Any]]:
    manifest = load_json(MANIFEST_PATH)
    result = []
    for fixture in manifest["fixtures"]:
        result.append(
            {
                "id": fixture["id"],
                "path": fixture["path"],
                "group": fixture["group"],
                "oracle_default": fixture["oracle_default"],
                "sha256": fixture["sha256"],
            }
        )
    return result


def case_kind(case_id: str) -> str:
    if case_id.endswith(".summary"):
        return "default_parse"
    if case_id.endswith(".canonical") or case_id.endswith(".no-verify.canonical"):
        return "canonical_rewrite"
    if case_id.endswith(".semantic-snapshot"):
        return "semantic_snapshot"
    if case_id.endswith(".clear-unreachable"):
        return "canonical_rewrite"
    if case_id.endswith((".default-stop", ".excessive-default-stop", ".threshold-default-stop")):
        # Write/summary attempts that stop on first named error and leave output absent.
        return "default_parse"
    if case_id.endswith((
        ".excessive-keep-going",
        ".excessive-stop-on-error-0",
        ".excessive-stop-on-error-1",
        ".stop-on-error-0",
        ".stop-on-error-1",
        ".erase-suppressed",
        ".ignore-negative-stop-format",
        ".threshold-ignore-all.canonical",
    )):
        return "ignore_recovery"
    if ".ignore-" in case_id or ".threshold-ignore-all." in case_id:
        return "ignore_recovery"
    raise TracefileContractError(f"unknown tracefile Oracle case kind: {case_id}")


EXACT_CASE_REQUIREMENTS = {
    "state-late-tn-mcdc.summary": {
        "requirement_ids": ["M1-TF-021"],
        "m0_decision_ids": ["M0-TF-TN-MCDC-001"],
    },
    "state-late-tn-mcdc.canonical": {
        "requirement_ids": ["M1-TF-021"],
        "m0_decision_ids": ["M0-TF-TN-MCDC-001"],
    },
    "state-late-tn-mcdc.semantic-snapshot": {
        "requirement_ids": ["M1-TF-021"],
        "m0_decision_ids": ["M0-TF-TN-MCDC-001"],
    },
    "state-cross-sf-mcdc-success.summary": {
        "requirement_ids": ["M1-TF-022"],
        "m0_decision_ids": ["M0-TF-MCDC-SF-001"],
    },
    "state-cross-sf-mcdc-success.canonical": {
        "requirement_ids": ["M1-TF-022"],
        "m0_decision_ids": ["M0-TF-MCDC-SF-001"],
    },
    "state-cross-sf-mcdc-success.semantic-snapshot": {
        "requirement_ids": ["M1-TF-022"],
        "m0_decision_ids": ["M0-TF-MCDC-SF-001"],
    },
    "state-cross-sf-mcdc-duplicate.summary": {
        "requirement_ids": ["M1-TF-026"],
        "m0_decision_ids": ["M0-TF-MCDC-SF-001"],
    },
    "ver-repeat-equal.summary": {"requirement_ids": ["M1-TF-007"]},
    "ver-repeat-equal.canonical": {"requirement_ids": ["M1-TF-007"]},
    "ver-repeat-different.summary": {"requirement_ids": ["M1-TF-007"]},
    "ver-per-source.summary": {"requirement_ids": ["M1-TF-007"]},
    "functions-current-core.summary": {"requirement_ids": ["M1-TF-009"]},
    "functions-current-core.canonical": {"requirement_ids": ["M1-TF-009"]},
    "functions-current-core.semantic-snapshot": {"requirement_ids": ["M1-TF-009"]},
    "functions-current-missing-alias.summary": {"requirement_ids": ["M1-TF-009"]},
    "functions-zero-end.summary": {"requirement_ids": ["M1-TF-009"]},
    "functions-zero-end.canonical": {"requirement_ids": ["M1-TF-009"]},
    "functions-zero-start.summary": {"requirement_ids": ["M1-TF-009"]},
    "functions-mixed-merge.summary": {"requirement_ids": ["M1-TF-011"]},
    "functions-mixed-merge.canonical": {"requirement_ids": ["M1-TF-011"]},
    "functions-mixed-merge.semantic-snapshot": {"requirement_ids": ["M1-TF-011"]},
    "functions-mixed-location-mismatch.summary": {"requirement_ids": ["M1-TF-011"]},
    "functions-mixed-location-mismatch.canonical": {"requirement_ids": ["M1-TF-011"]},
    "functions-mixed-range-mismatch.summary": {"requirement_ids": ["M1-TF-011"]},
    "functions-mixed-range-mismatch.canonical": {"requirement_ids": ["M1-TF-011"]},
    "functions-index-duplicate.summary": {"requirement_ids": ["M1-TF-024"]},
    "functions-index-duplicate.canonical": {"requirement_ids": ["M1-TF-024"]},
    "functions-index-unknown.summary": {"requirement_ids": ["M1-TF-024"]},
    "functions-index-unknown.canonical": {"requirement_ids": ["M1-TF-024"]},
    "functions-index-scope-reset.summary": {"requirement_ids": ["M1-TF-024"]},
    "functions-index-scope-reset.canonical": {"requirement_ids": ["M1-TF-024"]},
    "functions-index-tn-preserves.summary": {"requirement_ids": ["M1-TF-024"]},
    "branches-forms-core.summary": {"requirement_ids": ["M1-TF-013"]},
    "branches-forms-core.canonical": {"requirement_ids": ["M1-TF-013"]},
    "branches-forms-core.semantic-snapshot": {"requirement_ids": ["M1-TF-013"]},
    "branches-u-modes.summary": {"requirement_ids": ["M1-TF-013"]},
    "branches-u-modes.canonical": {"requirement_ids": ["M1-TF-013"]},
    "branches-u-modes.clear-unreachable": {"requirement_ids": ["M1-TF-013"]},
    "branches-malformed-tail.summary": {"requirement_ids": ["M1-TF-013"]},
    "branches-malformed-tail.canonical": {"requirement_ids": ["M1-TF-013"]},
    "branches-malformed-tail-empty-taken.summary": {"requirement_ids": ["M1-TF-013"]},
    "branches-malformed-tail-empty-taken.canonical": {"requirement_ids": ["M1-TF-013"]},
    "branches-malformed-tail-empty-expression.summary": {"requirement_ids": ["M1-TF-013"]},
    "branches-malformed-tail-empty-expression.canonical": {"requirement_ids": ["M1-TF-013"]},
    "branches-expression-mismatch.summary": {"requirement_ids": ["M1-TF-013"]},
    "branches-expression-mismatch.canonical": {"requirement_ids": ["M1-TF-013"]},
    "branches-expression-merge.canonical": {"requirement_ids": ["M1-TF-025"]},
    "branches-expression-merge.semantic-snapshot": {"requirement_ids": ["M1-TF-025"]},
    "branches-order-gaps.summary": {"requirement_ids": ["M1-TF-025"]},
    "branches-order-gaps.canonical": {"requirement_ids": ["M1-TF-025"]},
    "branches-noncontiguous.summary": {"requirement_ids": ["M1-TF-025"]},
    "branches-noncontiguous.canonical": {"requirement_ids": ["M1-TF-025"]},
    "branches-noncontiguous.semantic-snapshot": {"requirement_ids": ["M1-TF-025"]},
    "branches-interleave.summary": {"requirement_ids": ["M1-TF-025"]},
    "branches-interleave.canonical": {"requirement_ids": ["M1-TF-025"]},
    "branches-sort-signatures.summary": {"requirement_ids": ["M1-TF-025"]},
    "branches-sort-signatures.canonical": {"requirement_ids": ["M1-TF-025"]},
    "numeric-format-atoms.summary": {"requirement_ids": ["M1-TF-036"]},
    "numeric-format-atoms.default-stop": {"requirement_ids": ["M1-TF-036"]},
    "numeric-format-atoms.ignore-negative": {"requirement_ids": ["M1-TF-032", "M1-TF-036"]},
    "numeric-format-atoms.ignore-format-negative.canonical": {
        "requirement_ids": ["M1-TF-031", "M1-TF-032", "M1-TF-036"]
    },
    "numeric-format-atoms.ignore-format-negative.semantic-snapshot": {
        "requirement_ids": ["M1-TF-031", "M1-TF-032"]
    },
    "numeric-format-atoms.excessive-default-stop": {
        "requirement_ids": ["M1-TF-033", "M1-TF-036"]
    },
    "numeric-format-atoms.excessive-keep-going": {
        "requirement_ids": ["M1-TF-033", "M1-TF-036"]
    },
    "numeric-format-atoms.ignore-format-negative-excessive.canonical": {
        "requirement_ids": ["M1-TF-031", "M1-TF-032", "M1-TF-033", "M1-TF-036"]
    },
    "numeric-format-atoms.ignore-format-negative-excessive.semantic-snapshot": {
        "requirement_ids": ["M1-TF-031", "M1-TF-032", "M1-TF-033"]
    },
    "numeric-negative.summary": {"requirement_ids": ["M1-TF-032"]},
    "numeric-negative.ignore-negative": {"requirement_ids": ["M1-TF-032", "M1-TF-036"]},
    "numeric-negative-inf.summary": {"requirement_ids": ["M1-TF-032"]},
    "numeric-negative-inf.ignore-negative": {"requirement_ids": ["M1-TF-032", "M1-TF-036"]},
    "numeric-signed-zero.summary": {"requirement_ids": ["M1-TF-032"]},
    "numeric-signed-zero.canonical": {"requirement_ids": ["M1-TF-032"]},
    "numeric-signed-zero.semantic-snapshot": {"requirement_ids": ["M1-TF-032"]},
    "numeric-fnda-negative.summary": {"requirement_ids": ["M1-TF-032"]},
    "numeric-fnda-negative.ignore-negative": {"requirement_ids": ["M1-TF-032"]},
    "numeric-nonnumeric.summary": {"requirement_ids": ["M1-TF-031"]},
    "numeric-nonnumeric.ignore-format": {"requirement_ids": ["M1-TF-031", "M1-TF-036"]},
    "numeric-malformed-exponent.summary": {"requirement_ids": ["M1-TF-031"]},
    "numeric-malformed-exponent.ignore-format": {"requirement_ids": ["M1-TF-031", "M1-TF-036"]},
    "numeric-fnda-nonnumeric.summary": {"requirement_ids": ["M1-TF-031"]},
    "numeric-fnda-nonnumeric.ignore-format": {"requirement_ids": ["M1-TF-031"]},
    "numeric-fna-nonnumeric.summary": {"requirement_ids": ["M1-TF-031"]},
    "numeric-fna-nonnumeric.ignore-format": {"requirement_ids": ["M1-TF-031"]},
    "numeric-brda-nonnumeric.summary": {"requirement_ids": ["M1-TF-031"]},
    "numeric-brda-nonnumeric.ignore-format": {"requirement_ids": ["M1-TF-031"]},
    "numeric-mcdc-nondigit.summary": {"requirement_ids": ["M1-TF-031"]},
    "numeric-mcdc-nondigit.ignore-format": {"requirement_ids": ["M1-TF-031"]},
    "numeric-excessive.summary": {"requirement_ids": ["M1-TF-033"]},
    "numeric-excessive.ignore-excessive": {"requirement_ids": ["M1-TF-033", "M1-TF-036"]},
    "numeric-inf-excessive.summary": {"requirement_ids": ["M1-TF-033"]},
    "numeric-inf-excessive.ignore-excessive": {"requirement_ids": ["M1-TF-033"]},
    "numeric-zero-line.summary": {"requirement_ids": ["M1-TF-034"]},
    "numeric-zero-line.ignore-format": {"requirement_ids": ["M1-TF-034", "M1-TF-036"]},
    "numeric-zero-brda.summary": {"requirement_ids": ["M1-TF-034"]},
    "numeric-zero-mcdc.summary": {"requirement_ids": ["M1-TF-034"]},
    "numeric-zero-mcdc.ignore-format": {"requirement_ids": ["M1-TF-034"]},
    "numeric-zero-fn.summary": {"requirement_ids": ["M1-TF-034"]},
    "numeric-zero-fn.ignore-format": {"requirement_ids": ["M1-TF-034"]},
    "checksum-match.summary": {"requirement_ids": ["M1-TF-035"]},
    "checksum-match.canonical": {"requirement_ids": ["M1-TF-035"]},
    "checksum-mismatch.summary": {"requirement_ids": ["M1-TF-035"]},
    "checksum-mismatch.ignore-version": {"requirement_ids": ["M1-TF-035", "M1-TF-036"]},
    "checksum-missing.summary": {"requirement_ids": ["M1-TF-035"]},
    "checksum-missing.ignore-version-recompute": {"requirement_ids": ["M1-TF-035"]},
    "checksum-duplicate.summary": {"requirement_ids": ["M1-TF-035"]},
    "checksum-duplicate.ignore-version": {"requirement_ids": ["M1-TF-035", "M1-TF-036"]},
    "checksum-no-verify.canonical": {"requirement_ids": ["M1-TF-035"]},
}


# Numeric/error lane mappings are intentionally explicit and remain Oracle-only.
EXACT_CASE_REQUIREMENTS.update({
    "numeric-negative-inf.semantic-snapshot": {"requirement_ids": ["M1-TF-032"]},
    "numeric-format-atoms.excessive-stop-on-error-0": {"requirement_ids": ["M1-TF-036"]},
    "numeric-format-atoms.excessive-stop-on-error-1": {"requirement_ids": ["M1-TF-036"]},
    "numeric-fna-malformed-exponent.summary": {"requirement_ids": ["M1-TF-031"]},
    "numeric-fna-malformed-exponent.ignore-format": {"requirement_ids": ["M1-TF-031", "M1-TF-036"]},
    "numeric-fna-nonnumeric.semantic-snapshot": {"requirement_ids": ["M1-TF-031"]},
    "numeric-zero-fn-end.summary": {"requirement_ids": ["M1-TF-034"]},
    "numeric-zero-fn-end.ignore-format": {"requirement_ids": ["M1-TF-034", "M1-TF-036"]},
    "numeric-zero-fn-end.semantic-snapshot": {"requirement_ids": ["M1-TF-034"]},
    "numeric-invalid-fnl-fields.summary": {"requirement_ids": ["M1-TF-034"]},
    "numeric-invalid-fnl-fields.ignore-format": {"requirement_ids": ["M1-TF-034", "M1-TF-036"]},
    "numeric-invalid-fnl-fields.semantic-snapshot": {"requirement_ids": ["M1-TF-034"]},
    "functions-zero-start.ignore-inconsistent-format": {"requirement_ids": ["M1-TF-034", "M1-TF-036"]},
    "functions-zero-start.semantic-snapshot": {"requirement_ids": ["M1-TF-034"]},
    "numeric-function-excessive.default-stop": {"requirement_ids": ["M1-TF-033", "M1-TF-036"]},
    "numeric-function-excessive.erase-suppressed": {"requirement_ids": ["M1-TF-033", "M1-TF-036"]},
})


# TF-030 exact numeric matrix mappings remain Oracle-only.
EXACT_CASE_REQUIREMENTS.update({
    "numeric-format-atoms.tf030.semantic-snapshot": {
        "requirement_ids": ["M1-TF-030"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.tf030-threshold.semantic-snapshot": {
        "requirement_ids": ["M1-TF-030"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.default-stop": {
        "requirement_ids": ["M1-TF-030", "M1-TF-036"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.ignore-negative": {
        "requirement_ids": ["M1-TF-030", "M1-TF-032", "M1-TF-036"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.ignore-format-negative.canonical": {
        "requirement_ids": ["M1-TF-030", "M1-TF-031", "M1-TF-032", "M1-TF-036"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.ignore-format-negative.semantic-snapshot": {
        "requirement_ids": ["M1-TF-030", "M1-TF-031", "M1-TF-032"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.excessive-default-stop": {
        "requirement_ids": ["M1-TF-030", "M1-TF-033", "M1-TF-036"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.excessive-keep-going": {
        "requirement_ids": ["M1-TF-030", "M1-TF-033", "M1-TF-036"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.excessive-stop-on-error-0": {
        "requirement_ids": ["M1-TF-030", "M1-TF-036"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.excessive-stop-on-error-1": {
        "requirement_ids": ["M1-TF-030", "M1-TF-036"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.ignore-format-negative-excessive.canonical": {
        "requirement_ids": ["M1-TF-030", "M1-TF-031", "M1-TF-032", "M1-TF-033", "M1-TF-036"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-format-atoms.ignore-format-negative-excessive.semantic-snapshot": {
        "requirement_ids": ["M1-TF-030", "M1-TF-031", "M1-TF-032", "M1-TF-033"],
        "m0_decision_ids": ["M0-TF-NUMERIC-001"],
    },
    "numeric-tf030-fna-mirror.default-stop": {"requirement_ids": ["M1-TF-030"]},
    "numeric-tf030-fna-mirror.ignore-negative-stop-format": {"requirement_ids": ["M1-TF-030", "M1-TF-036"]},
    "numeric-tf030-fna-mirror.ignore-negative-format.canonical": {"requirement_ids": ["M1-TF-030", "M1-TF-036"]},
    "numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot": {"requirement_ids": ["M1-TF-030"]},
    "numeric-tf030-fna-mirror.threshold-default-stop": {"requirement_ids": ["M1-TF-030", "M1-TF-036"]},
    "numeric-tf030-fna-mirror.threshold-ignore-all.canonical": {"requirement_ids": ["M1-TF-030", "M1-TF-036"]},
    "numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot": {"requirement_ids": ["M1-TF-030"]},
    "numeric-tf030-candidates.default-stop": {"requirement_ids": ["M1-TF-030"]},
    "numeric-tf030-candidates.ignore-negative.canonical": {"requirement_ids": ["M1-TF-030", "M1-TF-036"]},
    "numeric-tf030-candidates.ignore-negative.semantic-snapshot": {"requirement_ids": ["M1-TF-030"]},
    "numeric-tf030-candidates.threshold-default-stop": {"requirement_ids": ["M1-TF-030", "M1-TF-036"]},
    "numeric-tf030-candidates.threshold-ignore-all.canonical": {"requirement_ids": ["M1-TF-030", "M1-TF-036"]},
    "numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot": {"requirement_ids": ["M1-TF-030"]},
})


def oracle_case_bindings(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases_document = load_json(CASES_PATH)
    baseline = load_json(BASELINE_PATH)
    fixture_by_path = {fixture["path"]: fixture["id"] for fixture in fixtures}
    observed_by_id = {case["id"]: case for case in baseline["cases"]}
    result = []
    for case in cases_document["cases"]:
        observed = observed_by_id.get(case["id"])
        if observed is None:
            raise TracefileContractError(f"missing Oracle observation: {case['id']}")
        output = observed["output"]
        entry: dict[str, Any] = {
            "id": case["id"],
            "fixture_id": fixture_by_path[case["fixture"]],
            "kind": case_kind(case["id"]),
            "exit_status": observed["exit_status"],
            "stdout_sha256": observed["stdout"]["sha256"],
            "stderr_sha256": observed["stderr"]["sha256"],
            "output_sha256": output.get("sha256"),
            "evidence_status": "oracle_reference",
        }
        additional_fixtures = case.get("additional_fixtures", {})
        if additional_fixtures:
            entry["additional_fixture_ids"] = [
                fixture_by_path[path] for path in additional_fixtures.values()
            ]
        runner = case.get("runner") or observed.get("runner")
        if runner is not None:
            entry["runner"] = runner
        mapping = EXACT_CASE_REQUIREMENTS.get(case["id"])
        if mapping is not None:
            entry["requirement_ids"] = list(mapping["requirement_ids"])
            if "m0_decision_ids" in mapping:
                entry["m0_decision_ids"] = list(mapping["m0_decision_ids"])
        result.append(entry)
    return result

def malformed_behaviors(
    record_entries: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fixture_by_id = {fixture["id"]: fixture for fixture in fixtures}
    cases_by_fixture: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        cases_by_fixture.setdefault(case["fixture_id"], []).append(case)
    target_by_fixture = {
        entry["malformed_fixture_id"]: entry["id"] for entry in record_entries
    }
    target_by_fixture["malformed-unknown"] = None
    result = []
    for fixture in fixtures:
        if fixture["group"] != "malformed-per-record":
            continue
        related = cases_by_fixture.get(fixture["id"], [])
        default = [case for case in related if case["kind"] == "default_parse"]
        recovery = [case["id"] for case in related if case["kind"] == "ignore_recovery"]
        if len(default) != 1:
            raise TracefileContractError(
                f"malformed fixture must have one default observation: {fixture['id']}"
            )
        result.append(
            {
                "id": f"tracefile.malformed.{fixture['id'].removeprefix('malformed-')}",
                "fixture_id": fixture["id"],
                "target_record_id": target_by_fixture[fixture["id"]],
                "oracle_default": fixture["oracle_default"],
                "default_case_id": default[0]["id"],
                "default_exit": default[0]["exit_status"],
                "recovery_case_ids": recovery,
                "review_status": "reviewed",
                "product_evidence": [],
            }
        )
    return result


def build_document(upstream_root: Path) -> dict[str, Any]:
    record_entries = records(upstream_root)
    fixtures = fixture_bindings()
    cases = oracle_case_bindings(fixtures)
    malformed = malformed_behaviors(record_entries, fixtures, cases)
    return {
        "schema_version": 1,
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "scope": "LCOV 2.5 tracefile reader matchers, canonical writer tags, retained boundary fixtures, state-ownership semantic snapshots, function-record probes, branch-record probes, numeric/error/checksum probes, and Oracle-observed malformed input behavior",
        "artifact_bindings": artifact_bindings(),
        "lexical_rules": lexical_rules(upstream_root),
        "records": record_entries,
        "fallback_behavior": fallback_behavior(upstream_root),
        "fixtures": fixtures,
        "malformed_behaviors": malformed,
        "oracle_cases": cases,
        "totals": {
            "records": len(record_entries),
            "lexical_rules": 2,
            "reader_matcher_lines": len(scan_reader_matcher_lines(upstream_root)),
            "canonical_writer_lines": len(scan_writer_emission_lines(upstream_root)),
            "fixtures": len(fixtures),
            "malformed_fixtures": len(malformed),
            "oracle_cases": len(cases),
            "default_parse_cases": sum(case["kind"] == "default_parse" for case in cases),
            "canonical_rewrite_cases": sum(case["kind"] == "canonical_rewrite" for case in cases),
            "ignore_recovery_cases": sum(case["kind"] == "ignore_recovery" for case in cases),
            "semantic_snapshot_cases": sum(case["kind"] == "semantic_snapshot" for case in cases),
            "oracle_exit_zero": sum(case["exit_status"] == 0 for case in cases),
            "oracle_exit_nonzero": sum(case["exit_status"] != 0 for case in cases),
            "exact_executable_requirement_ids": sorted(
                {
                    requirement_id
                    for case in cases
                    for requirement_id in case.get("requirement_ids", [])
                }
            ),
            "exact_executable_m0_decision_ids": sorted(
                {
                    decision_id
                    for case in cases
                    for decision_id in case.get("m0_decision_ids", [])
                }
            ),
        },
        "product_compatibility_evidence": False,
    }


def scan_reader_matcher_lines(upstream_root: Path) -> set[int]:
    source = (upstream_root / "lib/lcovutil.pm").read_text(encoding="utf-8").splitlines()
    result = set()
    for line_number, text in enumerate(source, start=1):
        if not 8937 <= line_number <= 9451:
            continue
        if (
            text.startswith("            /^")
            or text.startswith("            next if $line =~ /^")
            or text.startswith("        next if $line =~ /^#")
            or text.startswith("        if ($line =~ /^[SK]F:")
        ):
            result.add(line_number)
    return result


def scan_writer_emission_lines(upstream_root: Path) -> set[int]:
    source = (upstream_root / "lib/lcovutil.pm").read_text(encoding="utf-8").splitlines()
    result = set()
    for line_number, text in enumerate(source, start=1):
        if not 9473 <= line_number <= 9682:
            continue
        if (
            re.search(r'"[A-Z]+:', text)
            or '"end_of_record' in text
            or "print(INFO_HANDLE '#'," in text
        ):
            result.add(line_number)
    return result


def validate_schema(document: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise TracefileContractError(
            f"tracefile contract schema is invalid: {error.message}"
        ) from error
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise TracefileContractError(
            f"tracefile contract schema failure at {location}: {errors[0].message}"
        )


def validate_upstream_identity(upstream_root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip() != UPSTREAM_COMMIT:
        raise TracefileContractError("tracefile contract upstream commit mismatch")


def validate_source_references(document: dict[str, Any], upstream_root: Path) -> None:
    entries: list[dict[str, Any]] = [
        *document["lexical_rules"],
        *document["records"],
        document["fallback_behavior"],
    ]
    for entry in entries:
        for reference in entry["source_references"]:
            try:
                actual = (upstream_root / reference["path"]).read_text(
                    encoding="utf-8"
                ).splitlines()[reference["line"] - 1]
            except (OSError, IndexError) as error:
                raise TracefileContractError(
                    f"cannot validate source reference {reference['path']}:{reference['line']}"
                ) from error
            if actual != reference["text"]:
                raise TracefileContractError(
                    f"source text drift: {reference['path']}:{reference['line']}"
                )

    reader_references = {
        reference["line"]
        for entry in [*document["lexical_rules"], *document["records"]]
        for reference in entry["source_references"]
        if reference["path"] == "lib/lcovutil.pm" and reference["role"] == "reader"
    }
    reader_lines = scan_reader_matcher_lines(upstream_root)
    if reader_references != reader_lines:
        raise TracefileContractError(
            f"tracefile reader matcher closure mismatch: missing={sorted(reader_lines - reader_references)} extra={sorted(reader_references - reader_lines)}"
        )

    writer_references = {
        reference["line"]
        for entry in [*document["lexical_rules"], *document["records"]]
        for reference in entry["source_references"]
        if reference["path"] == "lib/lcovutil.pm" and reference["role"] == "writer"
    }
    writer_lines = scan_writer_emission_lines(upstream_root)
    if writer_references != writer_lines:
        raise TracefileContractError(
            f"tracefile writer emission closure mismatch: missing={sorted(writer_lines - writer_references)} extra={sorted(writer_references - writer_lines)}"
        )


def validate_artifacts(document: dict[str, Any]) -> None:
    expected_bindings = artifact_bindings()
    if document["artifact_bindings"] != expected_bindings:
        raise TracefileContractError("tracefile retained artifact binding drift")

    manifest = load_json(MANIFEST_PATH)
    cases_document = load_json(CASES_PATH)
    baseline = load_json(BASELINE_PATH)
    if manifest["provenance"]["oracle"]["source_commit"] != UPSTREAM_COMMIT:
        raise TracefileContractError("tracefile manifest upstream commit mismatch")
    if baseline["oracle"]["source_commit"] != UPSTREAM_COMMIT:
        raise TracefileContractError("tracefile baseline upstream commit mismatch")
    if baseline["cases_sha256"] != sha256_file(CASES_PATH):
        raise TracefileContractError("tracefile baseline case binding hash mismatch")

    expected_fixtures = fixture_bindings()
    if document["fixtures"] != expected_fixtures:
        raise TracefileContractError("tracefile fixture binding drift")
    fixture_ids = tuple(fixture["id"] for fixture in document["fixtures"])
    if fixture_ids != EXPECTED_FIXTURE_IDS:
        raise TracefileContractError("tracefile fixture identity or order drift")
    for fixture in manifest["fixtures"]:
        if not fixture["committed"]:
            continue
        path = CORPUS_ROOT / fixture["path"]
        if sha256_file(path) != fixture["sha256"]:
            raise TracefileContractError(f"tracefile fixture byte drift: {fixture['id']}")

    expected_cases = oracle_case_bindings(expected_fixtures)
    if len(document["oracle_cases"]) == len(expected_cases):
        for actual, expected in zip(document["oracle_cases"], expected_cases):
            if actual.get("id") != expected.get("id"):
                break
            for field in ("additional_fixture_ids", "requirement_ids", "m0_decision_ids"):
                expected_value = expected.get(field)
                if actual.get(field) != expected_value:
                    raise TracefileContractError(
                        f"tracefile {field} mapping drift: {actual.get('id')}"
                    )
            if actual.get("runner") != expected.get("runner"):
                raise TracefileContractError(
                    f"tracefile Oracle runner drift: {actual.get('id')}"
                )
            if (
                actual.get("kind") == "semantic_snapshot"
                and actual.get("stdout_sha256") != expected.get("stdout_sha256")
            ):
                raise TracefileContractError(
                    f"semantic snapshot identity drift: {actual.get('id')}"
                )
    if document["oracle_cases"] != expected_cases:
        raise TracefileContractError("tracefile Oracle case or observation identity drift")
    case_ids = tuple(case["id"] for case in document["oracle_cases"])
    if case_ids != EXPECTED_CASE_IDS:
        raise TracefileContractError("tracefile Oracle case identity or order drift")
    source_case_ids = [case["id"] for case in cases_document["cases"]]
    observed_case_ids = [case["id"] for case in baseline["cases"]]
    if source_case_ids != observed_case_ids or tuple(source_case_ids) != EXPECTED_CASE_IDS:
        raise TracefileContractError("tracefile Oracle source/baseline case closure mismatch")
    source_by_id = {case["id"]: case for case in cases_document["cases"]}
    observed_by_id = {case["id"]: case for case in baseline["cases"]}
    for case in document["oracle_cases"]:
        expected_exit = source_by_id[case["id"]]["expected_exit"]
        observed_exit = observed_by_id[case["id"]]["exit_status"]
        if expected_exit != observed_exit or case["exit_status"] != observed_exit:
            raise TracefileContractError(f"unexpected retained Oracle exit: {case['id']}")
        source_case = source_by_id[case["id"]]
        observed = observed_by_id[case["id"]]
        additional_fixture_ids = [
            next(
                fixture["id"]
                for fixture in document["fixtures"]
                if fixture["path"] == path
            )
            for path in source_case.get("additional_fixtures", {}).values()
        ]
        if case.get("additional_fixture_ids", []) != additional_fixture_ids:
            raise TracefileContractError(
                f"tracefile additional fixture binding drift: {case['id']}"
            )
        if observed.get("additional_fixtures", {}) != source_case.get("additional_fixtures", {}):
            raise TracefileContractError(
                f"tracefile observed additional fixture drift: {case['id']}"
            )
        source_runner = source_case.get("runner")
        observed_runner = observed.get("runner")
        if case.get("runner") != source_runner or case.get("runner") != observed_runner:
            raise TracefileContractError(f"tracefile Oracle runner drift: {case['id']}")
        expected_mapping = EXACT_CASE_REQUIREMENTS.get(case["id"])
        if expected_mapping is None:
            if case.get("requirement_ids") or case.get("m0_decision_ids"):
                raise TracefileContractError(
                    f"unexpected exact mapping on non-mapped case: {case['id']}"
                )
        else:
            for field in ("requirement_ids", "m0_decision_ids"):
                if case.get(field) != expected_mapping.get(field):
                    raise TracefileContractError(
                        f"tracefile {field} mapping drift: {case['id']}"
                    )
        if case["kind"] == "semantic_snapshot":
            if case.get("runner") != "inspect_model.pl":
                raise TracefileContractError(
                    f"semantic snapshot runner drift: {case['id']}"
                )
            if case["stdout_sha256"] != observed["stdout"]["sha256"]:
                raise TracefileContractError(
                    f"semantic snapshot identity drift: {case['id']}"
                )


def validate_document(document: dict[str, Any], upstream_root: Path) -> None:
    validate_schema(document)
    if document["upstream_commit"] != UPSTREAM_COMMIT:
        raise TracefileContractError("tracefile document upstream commit drift")
    tags = tuple(entry["tag"] for entry in document["records"])
    if tags != EXPECTED_RECORD_TAGS:
        raise TracefileContractError("tracefile record identity or order drift")
    record_ids = [entry["id"] for entry in document["records"]]
    if len(record_ids) != len(set(record_ids)):
        raise TracefileContractError("duplicate tracefile record identity")
    if sum(entry["writer_behavior"] == "emitted" for entry in document["records"]) != 17:
        raise TracefileContractError("canonical tracefile writer record count drift")
    if sum(entry["input_behavior"] == "ignored_summary" for entry in document["records"]) != 8:
        raise TracefileContractError("ignored tracefile summary record count drift")

    validate_source_references(document, upstream_root)
    validate_artifacts(document)

    malformed_fixture_ids = {
        entry["malformed_fixture_id"] for entry in document["records"]
    } | {document["fallback_behavior"]["malformed_fixture_id"]}
    expected_malformed = {
        fixture["id"]
        for fixture in document["fixtures"]
        if fixture["group"] == "malformed-per-record"
    }
    if malformed_fixture_ids != expected_malformed:
        raise TracefileContractError(
            "tracefile record-to-malformed-fixture closure mismatch"
        )
    expected_behaviors = malformed_behaviors(
        document["records"], document["fixtures"], document["oracle_cases"]
    )
    if document["malformed_behaviors"] != expected_behaviors:
        raise TracefileContractError("tracefile malformed behavior binding drift")

    all_entries = [
        *document["lexical_rules"],
        *document["records"],
        document["fallback_behavior"],
        *document["malformed_behaviors"],
    ]
    for entry in all_entries:
        if entry["product_evidence"]:
            raise TracefileContractError(
                f"tracefile Oracle reference claims product evidence: {entry['id']}"
            )
    if document["product_compatibility_evidence"]:
        raise TracefileContractError("tracefile contract claims product compatibility")
    if any(
        case["evidence_status"] != "oracle_reference"
        for case in document["oracle_cases"]
    ):
        raise TracefileContractError("tracefile Oracle case claims product evidence")

    cases = document["oracle_cases"]
    expected_totals = {
        "records": 20,
        "lexical_rules": 2,
        "reader_matcher_lines": 15,
        "canonical_writer_lines": 18,
        "fixtures": 93,
        "malformed_fixtures": 21,
        "oracle_cases": 184,
        "default_parse_cases": 90,
        "canonical_rewrite_cases": 41,
        "ignore_recovery_cases": 30,
        "semantic_snapshot_cases": 23,
        "oracle_exit_zero": 120,
        "oracle_exit_nonzero": 64,
        "exact_executable_requirement_ids": [
            "M1-TF-007",
            "M1-TF-009",
            "M1-TF-011",
            "M1-TF-013",
            "M1-TF-021",
            "M1-TF-022",
            "M1-TF-024",
            "M1-TF-025",
            "M1-TF-026",
            "M1-TF-030",
            "M1-TF-031",
            "M1-TF-032",
            "M1-TF-033",
            "M1-TF-034",
            "M1-TF-035",
            "M1-TF-036",
        ],
        "exact_executable_m0_decision_ids": [
            "M0-TF-MCDC-SF-001",
            "M0-TF-NUMERIC-001",
            "M0-TF-TN-MCDC-001",
        ],
    }
    if document["totals"] != expected_totals:
        raise TracefileContractError("tracefile contract totals drift")
    if len(cases) != expected_totals["oracle_cases"]:
        raise TracefileContractError("tracefile Oracle case total drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, default=DEFAULT_UPSTREAM_ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    upstream_root = args.upstream_root.resolve()
    validate_upstream_identity(upstream_root)
    document = build_document(upstream_root)
    validate_document(document, upstream_root)
    content = canonical_json(document).encode("ascii")
    if args.write:
        OUTPUT_PATH.write_bytes(content)
        print(f"TRACEFILE_CONTRACT_WRITTEN path={OUTPUT_PATH.relative_to(ROOT)}")
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != content:
        raise TracefileContractError(
            "committed tracefile contract differs from generation"
        )
    print(
        "TRACEFILE_CONTRACT_OK "
        f"records={document['totals']['records']} "
        f"reader_lines={document['totals']['reader_matcher_lines']} "
        f"writer_lines={document['totals']['canonical_writer_lines']} "
        f"fixtures={document['totals']['fixtures']} "
        f"malformed={document['totals']['malformed_fixtures']} "
        f"oracle_cases={document['totals']['oracle_cases']} "
        "product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
