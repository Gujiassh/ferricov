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
    "compat/fixtures/m0-tracefiles/manifest.json": "57edf63e9d4988d380eac51fa2fb134a8628a6ef9b5c5431a0bc3b2a48b5eb56",
    "compat/fixtures/m0-tracefiles/oracle-cases.json": "01c6e11166d5ea440345744bd018c218b086847686f4474a96974e4c14efcca1",
    "compat/fixtures/m0-tracefiles/oracle-baseline.json": "b0162c3677dcc3dcc859a5d13ea9002d36b7a093e89559643b4c89c1514659a7",
}
EXPECTED_RECORD_TAGS = (
    "TN", "SF", "KF", "VER", "FNL", "FNA", "FN", "FNDA", "FNF", "FNH",
    "BRDA", "BRF", "BRH", "MCDC", "MCF", "MCH", "DA", "LF", "LH",
    "end_of_record",
)
EXPECTED_FIXTURE_IDS = (
    "current-all-records", "legacy", "permissive-prefix", "malformed-tn",
    "malformed-sf", "malformed-kf", "malformed-ver", "malformed-da",
    "malformed-fn", "malformed-fnda", "malformed-fnl", "malformed-fna",
    "malformed-brda", "malformed-mcdc", "malformed-terminator",
    "malformed-unknown", "malformed-fnf-accepted", "malformed-fnh-accepted",
    "malformed-brf-accepted", "malformed-brh-accepted",
    "malformed-mcf-accepted", "malformed-mch-accepted",
    "malformed-lf-accepted", "malformed-lh-accepted", "bytes-crlf",
    "bytes-no-final-newline", "bytes-non-utf8", "bytes-nul-accepted",
    "numeric-boundary", "numeric-negative", "numeric-nonnumeric",
    "numeric-malformed-exponent", "numeric-excessive", "numeric-zero-line",
    "scale-medium", "scale-large",
)
EXPECTED_CASE_IDS = (
    "current-all-records.summary", "legacy.summary", "permissive-prefix.summary",
    "malformed-tn.summary", "malformed-sf.summary", "malformed-kf.summary",
    "malformed-ver.summary", "malformed-da.summary", "malformed-fn.summary",
    "malformed-fnda.summary", "malformed-fnl.summary", "malformed-fna.summary",
    "malformed-brda.summary", "malformed-mcdc.summary",
    "malformed-terminator.summary", "malformed-unknown.summary",
    "malformed-fnf-accepted.summary", "malformed-fnh-accepted.summary",
    "malformed-brf-accepted.summary", "malformed-brh-accepted.summary",
    "malformed-mcf-accepted.summary", "malformed-mch-accepted.summary",
    "malformed-lf-accepted.summary", "malformed-lh-accepted.summary",
    "bytes-crlf.summary", "bytes-no-final-newline.summary",
    "bytes-non-utf8.summary", "bytes-nul-accepted.summary",
    "numeric-boundary.summary", "numeric-negative.summary",
    "numeric-nonnumeric.summary", "numeric-malformed-exponent.summary",
    "numeric-excessive.summary", "numeric-zero-line.summary",
    "scale-medium.summary", "scale-large.summary",
    "current-all-records.canonical", "legacy.canonical",
    "permissive-prefix.canonical", "bytes-crlf.canonical",
    "bytes-no-final-newline.canonical", "bytes-non-utf8.canonical",
    "bytes-nul-accepted.canonical", "numeric-boundary.canonical",
    "malformed-tn.ignore-format", "malformed-da.ignore-format",
    "malformed-ver.ignore-format", "numeric-negative.ignore-negative",
    "numeric-nonnumeric.ignore-format",
    "numeric-malformed-exponent.ignore-format",
    "numeric-excessive.ignore-excessive", "numeric-zero-line.ignore-format",
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
    if case_id.endswith(".canonical"):
        return "canonical_rewrite"
    if ".ignore-" in case_id:
        return "ignore_recovery"
    raise TracefileContractError(f"unknown tracefile Oracle case kind: {case_id}")


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
        result.append(
            {
                "id": case["id"],
                "fixture_id": fixture_by_path[case["fixture"]],
                "kind": case_kind(case["id"]),
                "exit_status": observed["exit_status"],
                "stdout_sha256": observed["stdout"]["sha256"],
                "stderr_sha256": observed["stderr"]["sha256"],
                "output_sha256": output.get("sha256"),
                "evidence_status": "oracle_reference",
            }
        )
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
        "scope": "LCOV 2.5 tracefile reader matchers, canonical writer tags, retained boundary fixtures, and Oracle-observed malformed input behavior",
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
            "oracle_exit_zero": sum(case["exit_status"] == 0 for case in cases),
            "oracle_exit_nonzero": sum(case["exit_status"] != 0 for case in cases),
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
        "fixtures": 36,
        "malformed_fixtures": 21,
        "oracle_cases": 52,
        "default_parse_cases": 36,
        "canonical_rewrite_cases": 8,
        "ignore_recovery_cases": 8,
        "oracle_exit_zero": 34,
        "oracle_exit_nonzero": 18,
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
