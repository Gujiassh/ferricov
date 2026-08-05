#!/usr/bin/env python3
"""Generate and validate the fail-closed LCOV 2.5 diagnostics contract."""

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
SCHEMA_PATH = ROOT / "compat/schema/diagnostics-contract.schema.json"
CORRECTNESS_ROOT = ROOT / "compat/correctness/baselines/m0-cli-oracle-v2.5"
CORRECTNESS_INDEX = CORRECTNESS_ROOT / "result.json"
TRACEFILE_BASELINE = ROOT / "compat/fixtures/m0-tracefiles/oracle-baseline.json"
TRACEFILE_CASES = ROOT / "compat/fixtures/m0-tracefiles/oracle-cases.json"
SPEC_PATH = ROOT / "specs/001-full-lcov-compatibility/diagnostics-parallel-contract.md"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference")
)

EXPECTED_ARTIFACT_HASHES = {
    "compat/correctness/baselines/m0-cli-oracle-v2.5/result.json":
        "f1b8484ba8a9587791c294722ceddcca245c72fa1a090b0b5245375fec30f8a2",
    "compat/fixtures/m0-tracefiles/oracle-baseline.json":
        "a04d26a29d548ebbf594a38dda3200c4c3e8e1c5b25afd3651568e15909c7689",
    "compat/fixtures/m0-tracefiles/oracle-cases.json":
        "a8771082f4ecb09c773a58ae83af2aed6d36c04f737143e55fddf590e088dc51",
}

EXPECTED_REGISTRY = (
    ("annotate", "ERROR_ANNOTATE_SCRIPT"),
    ("branch", "ERROR_BRANCH"),
    ("callback", "ERROR_CALLBACK"),
    ("category", "ERROR_UNKNOWN_CATEGORY"),
    ("child", "ERROR_CHILD"),
    ("corrupt", "ERROR_CORRUPT"),
    ("count", "ERROR_COUNT"),
    ("deprecated", "ERROR_DEPRECATED"),
    ("empty", "ERROR_EMPTY"),
    ("excessive", "ERROR_EXCESSIVE_COUNT"),
    ("format", "ERROR_FORMAT"),
    ("fork", "ERROR_FORK"),
    ("gcov", "ERROR_GCOV"),
    ("graph", "ERROR_GRAPH"),
    ("inconsistent", "ERROR_INCONSISTENT_DATA"),
    ("internal", "ERROR_INTERNAL"),
    ("mismatch", "ERROR_MISMATCH"),
    ("missing", "ERROR_MISSING"),
    ("negative", "ERROR_NEGATIVE"),
    ("package", "ERROR_PACKAGE"),
    ("parallel", "ERROR_PARALLEL"),
    ("parent", "ERROR_PARENT"),
    ("path", "ERROR_PATH"),
    ("range", "ERROR_RANGE"),
    ("source", "ERROR_SOURCE"),
    ("unmapped", "ERROR_UNMAPPED_LINE"),
    ("unreachable", "ERROR_UNREACHABLE"),
    ("unsupported", "ERROR_UNSUPPORTED"),
    ("unused", "ERROR_UNUSED"),
    ("usage", "ERROR_USAGE"),
    ("utility", "ERROR_UTILITY"),
    ("version", "ERROR_VERSION"),
)

STARTUP_CASES = {
    "lcov": "m0-core-lcov-startup-control",
    "genhtml": "m0-core-genhtml-startup-control",
    "geninfo": "m0-core-geninfo-startup-control",
    "genpng": "m0-core-genpng-startup-control",
    "gendesc": "m0-core-gendesc-startup-control",
    "perl2lcov": "m0-core-perl2lcov-startup-control",
    "py2lcov": "m0-core-py2lcov-startup-control",
    "xml2lcov": "m0-core-xml2lcov-startup-control",
    "xml2lcovutil.py": "m0-core-xml2lcovutil-py-startup-control",
    "llvm2lcov": "m0-core-llvm2lcov-startup-control",
}

STARTUP_PLANNED_CASES = {
    "lcov": "DIAG-NOARGS-LCOV-001",
    "genhtml": "DIAG-NOARGS-GENHTML-001",
    "genpng": "DIAG-NOARGS-GENPNG-001",
    "gendesc": "DIAG-NOARGS-GENDESC-001",
    "perl2lcov": "DIAG-NOARGS-PERL2LCOV-001",
    "py2lcov": "DIAG-NOARGS-PY2LCOV-001",
    "xml2lcov": "DIAG-NOARGS-XML2LCOV-001",
    "xml2lcovutil.py": "DIAG-NOARGS-XML2LCOVUTIL-001",
    "llvm2lcov": "DIAG-NOARGS-LLVM2LCOV-001",
}

INVALID_CASES = {
    "lcov": "m0-core-lcov-invalid-option",
    "genhtml": "m0-core-genhtml-invalid-option",
    "geninfo": "m0-core-geninfo-invalid-option",
    "genpng": "m0-core-genpng-invalid-option",
    "gendesc": "m0-core-gendesc-invalid-option",
    "perl2lcov": "m0-core-perl2lcov-invalid-option",
    "py2lcov": "m0-core-py2lcov-invalid-option",
    "xml2lcov": "m0-core-xml2lcov-invalid-option",
    "xml2lcovutil.py": "m0-core-xml2lcovutil-py-invalid-argv-ignored-control",
    "llvm2lcov": "m0-core-llvm2lcov-invalid-option",
}

CONFIG_CASES = {
    "m0-config-base-missing-env": ["DIAG-CONFIG-ENV-EXPAND-001"],
    "m0-config-base-missing-env-ignored": [
        "DIAG-CONFIG-ENV-EXPAND-001",
        "DIAG-IGNORE-WARN-001",
    ],
    "m0-config-base-missing-explicit-is-early": [
        "DIAG-CONFIG-EARLY-ERROR-001"
    ],
    "m0-config-base-include-loop": [
        "DIAG-CONFIG-INCLUDE-001",
        "DIAG-CONFIG-EARLY-ERROR-001",
    ],
    "m0-config-base-unknown-rc-key": ["DIAG-CONFIG-UNKNOWN-KEY-001"],
}


class DiagnosticsContractError(RuntimeError):
    pass


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DiagnosticsContractError(f"cannot load JSON: {path}") from error
    if not isinstance(document, dict):
        raise DiagnosticsContractError(f"expected JSON object: {path}")
    return document


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def source_reference(
    upstream_root: Path, path: str, line: int, role: str
) -> dict[str, Any]:
    try:
        text = (upstream_root / path).read_text(encoding="utf-8").splitlines()[
            line - 1
        ]
    except (OSError, IndexError) as error:
        raise DiagnosticsContractError(f"cannot read source {path}:{line}") from error
    return {"path": path, "line": line, "role": role, "text": text}


def scan_registry(upstream_root: Path) -> list[tuple[str, str, int]]:
    lines = (upstream_root / "lib/lcovutil.pm").read_text(encoding="utf-8").splitlines()
    result = []
    pattern = re.compile(r'''\[(["'])([a-z]+)\1, \\\$(ERROR_[A-Z_]+)\]''')
    for line_number, text in enumerate(lines, start=1):
        match = pattern.search(text)
        if match:
            result.append((match.group(2), match.group(3), line_number))
    return result


def scan_symbol_references(upstream_root: Path, symbol: str) -> list[str]:
    pattern = re.compile(r"\$(?:lcovutil::)?" + re.escape(symbol) + r"\b")
    result = []
    for base in ("bin", "lib", "scripts"):
        for path in sorted((upstream_root / base).rglob("*")):
            if not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, text in enumerate(lines, start=1):
                if not pattern.search(text.split("#", 1)[0]):
                    continue
                if path == upstream_root / "lib/lcovutil.pm" and (
                    text.lstrip().startswith("our $ERROR_")
                    or 169 <= line_number <= 200
                ):
                    continue
                result.append(f"{path.relative_to(upstream_root)}:{line_number}:{text}")
    return result


def registry_entries(upstream_root: Path) -> list[dict[str, Any]]:
    scanned = scan_registry(upstream_root)
    if tuple((name, symbol) for name, symbol, _ in scanned) != EXPECTED_REGISTRY:
        raise DiagnosticsContractError("diagnostic registry identity or order drift")
    result = []
    for numeric_id, (name, symbol, line) in enumerate(scanned):
        references = scan_symbol_references(upstream_root, symbol)
        canonical = ("\n".join(references) + "\n").encode("utf-8")
        result.append(
            {
                "id": f"diagnostic.category.{name}",
                "name": name,
                "upstream_symbol": symbol,
                "upstream_numeric_id": numeric_id,
                "emitter_status": (
                    "reserved_no_production_emitter" if name == "branch" else "emitted"
                ),
                "registry_source": source_reference(
                    upstream_root, "lib/lcovutil.pm", line, "registry"
                ),
                "symbol_reference_count": len(references),
                "symbol_references_sha256": sha256_bytes(canonical),
                "review_status": "reviewed",
                "product_evidence": [],
            }
        )
    return result


def control_rules(upstream_root: Path) -> list[dict[str, Any]]:
    definitions = [
        (
            "diagnostic.control.ignore-list-precedence",
            "CLI ignore values replace the complete configuration list when any CLI value is present.",
            [("lib/lcovutil.pm", 1553), ("lib/lcovutil.pm", 1575)],
        ),
        (
            "diagnostic.control.ignore-count-parse",
            "Names are comma-split, case-insensitive, rejected when unknown, and counted per occurrence.",
            [("lib/lcovutil.pm", line) for line in (1964, 1975, 1976, 1977, 1979)],
        ),
        (
            "diagnostic.control.keep-going",
            "Keep-going sets stop_on_error to zero and makes every registered class continuable without changing an unlisted error into a warning.",
            [("lib/lcovutil.pm", line) for line in (1582, 1583, 2045, 2362, 2363, 2364, 2365)],
        ),
        (
            "diagnostic.control.error-ignore-zero",
            "A registered error with ignore count zero is fatal unless keep-going is active.",
            [("lib/lcovutil.pm", line) for line in (2355, 2356, 2367, 2368)],
        ),
        (
            "diagnostic.control.error-ignore-one",
            "A registered error with ignore count one continues as a warning.",
            [("lib/lcovutil.pm", line) for line in (2377, 2379, 2380, 2381)],
        ),
        (
            "diagnostic.control.error-ignore-two-plus",
            "A registered error with ignore count two or more continues silently in the ignore summary bucket.",
            [("lib/lcovutil.pm", line) for line in (2377, 2378)],
        ),
        (
            "diagnostic.control.warning-ladder",
            "Warnings are visible at ignore zero, silent at ignore one or more, and use the complete error ladder when promotion is enabled.",
            [("lib/lcovutil.pm", line) for line in (2388, 2389, 2397, 2406, 2414, 2415, 2417)],
        ),
        (
            "diagnostic.control.message-suppression",
            "Semantic message counts continue after the configured console suppression threshold.",
            [("lib/lcovutil.pm", line) for line in (2297, 2301, 2302, 2309, 2341, 2347, 2350)],
        ),
        (
            "diagnostic.control.error-summary-exit",
            "saw_error reports the presence of the error summary bucket for command-specific final-exit folding.",
            [("lib/lcovutil.pm", line) for line in (2325, 2329)],
        ),
    ]
    return [
        {
            "id": identifier,
            "behavior": behavior,
            "source_references": [
                source_reference(upstream_root, path, line, "control")
                for path, line in references
            ],
            "review_status": "reviewed",
            "product_evidence": [],
        }
        for identifier, behavior, references in definitions
    ]


def unclassified_surfaces(upstream_root: Path) -> list[dict[str, Any]]:
    definitions = [
        (
            "diagnostic.surface.parser",
            "parser_error",
            "Getopt and argparse failures retain their native stream and status behavior.",
            [("lib/lcovutil.pm", 1518), ("bin/py2lcov", 155)],
        ),
        (
            "diagnostic.surface.raw-perl",
            "raw_perl_failure",
            "Direct die/open/assertion failures outside a named wrapper are not controlled by ignore-errors.",
            [("bin/llvm2lcov", 112), ("bin/gendesc", 94)],
        ),
        (
            "diagnostic.surface.native-python",
            "native_python_diagnostic",
            "Python converter application diagnostics are printed directly and use their own keep-going boundaries.",
            [("bin/py2lcov", 169), ("bin/py2lcov", 193), ("bin/xml2lcovutil.py", 163)],
        ),
        (
            "diagnostic.surface.early-dependency",
            "early_dependency_failure",
            "Dependency loading can fail before ordinary parser behavior is reached.",
            [("bin/genpng", 58), ("bin/genpng", 62), ("bin/genpng", 65)],
        ),
    ]
    return [
        {
            "id": identifier,
            "family": family,
            "behavior": behavior,
            "source_references": [
                source_reference(upstream_root, path, line, "surface")
                for path, line in references
            ],
            "review_status": "reviewed",
            "product_evidence": [],
        }
        for identifier, family, behavior, references in definitions
    ]


def exit_policies(upstream_root: Path) -> list[dict[str, Any]]:
    definitions = [
        ("lcov", "shared_saw_error_fold", [("bin/lcov", 469), ("bin/lcov", 472), ("bin/lcov", 474)]),
        ("geninfo", "shared_saw_error_fold", [("bin/geninfo", 610), ("bin/geninfo", 614), ("bin/geninfo", 615)]),
        ("genhtml", "shared_saw_error_fold", [("bin/genhtml", 7639), ("bin/genhtml", 7641), ("bin/genhtml", 7643)]),
        ("perl2lcov", "criteria_only_no_saw_error_fold", [("bin/perl2lcov", 438), ("bin/perl2lcov", 442), ("bin/perl2lcov", 444)]),
        ("llvm2lcov", "criteria_only_no_saw_error_fold", [("bin/llvm2lcov", 558), ("bin/llvm2lcov", 561), ("bin/llvm2lcov", 567)]),
        ("py2lcov", "native_python_keep_going", [("bin/py2lcov", 148), ("bin/py2lcov", 195), ("bin/py2lcov", 201)]),
        ("xml2lcov", "native_python_keep_going", [("bin/xml2lcov", 82), ("bin/xml2lcov", 96), ("bin/xml2lcov", 98)]),
        ("xml2lcovutil.py", "library_no_cli_entrypoint", [("bin/xml2lcovutil.py", 143)]),
        ("genpng", "direct_perl_exit", [("bin/genpng", 88), ("bin/genpng", 90), ("bin/genpng", 109)]),
        ("gendesc", "direct_perl_exit", [("bin/gendesc", 73), ("bin/gendesc", 75), ("bin/gendesc", 94)]),
    ]
    return [
        {
            "id": f"diagnostic.exit-policy.{command}",
            "command": command,
            "policy": policy,
            "source_references": [
                source_reference(upstream_root, path, line, "exit")
                for path, line in references
            ],
            "review_status": "reviewed",
            "product_evidence": [],
        }
        for command, policy, references in definitions
    ]


def planned_case_ids() -> list[str]:
    text = SPEC_PATH.read_text(encoding="utf-8")
    result = []
    for identifier in re.findall(r"`((?:DIAG|PAR)-[A-Z0-9-]+)`", text):
        if identifier not in result:
            result.append(identifier)
    return result


def artifact_bindings() -> list[dict[str, str]]:
    result = []
    for relative, expected in EXPECTED_ARTIFACT_HASHES.items():
        actual = sha256_file(ROOT / relative)
        if actual != expected:
            raise DiagnosticsContractError(
                f"retained diagnostics artifact drift: {relative} expected={expected} actual={actual}"
            )
        result.append({"path": relative, "sha256": actual})
    return result


def correctness_case(case_id: str) -> dict[str, Any]:
    path = CORRECTNESS_ROOT / "cases" / case_id / "result.json"
    document = load_json(path)
    reference = document["reference_run"]
    if document["case_id"] != case_id or document["product_compatibility_evidence"]:
        raise DiagnosticsContractError(f"invalid retained correctness case: {case_id}")
    return {
        "id": f"correctness:{case_id}",
        "exit_status": reference["exit_code"],
        "stdout_sha256": reference["stdout_sha256"],
        "stderr_sha256": reference["stderr_sha256"],
        "output_sha256": reference["file_tree_sha256"],
        "observation_sha256": sha256_file(path),
    }


def tracefile_case(case: dict[str, Any]) -> dict[str, Any]:
    output = case["output"]
    return {
        "id": f"tracefile:{case['id']}",
        "exit_status": case["exit_status"],
        "stdout_sha256": case["stdout"]["sha256"],
        "stderr_sha256": case["stderr"]["sha256"],
        "output_sha256": output.get("sha256"),
        "observation_sha256": sha256_bytes(canonical_json(case).encode("ascii")),
    }


def oracle_observations() -> list[dict[str, Any]]:
    result = []
    startup_case_to_command = {case: command for command, case in STARTUP_CASES.items()}
    for case_id in STARTUP_CASES.values():
        entry = correctness_case(case_id)
        command = startup_case_to_command[case_id]
        entry["kind"] = (
            "startup_environment_intercept" if command == "geninfo" else "startup_boundary"
        )
        entry["planned_case_ids"] = (
            []
            if command == "geninfo"
            else [STARTUP_PLANNED_CASES[command]]
        )
        result.append(entry)

    for case_id in INVALID_CASES.values():
        entry = correctness_case(case_id)
        entry["kind"] = "parser_boundary"
        entry["planned_case_ids"] = ["DIAG-PARSER-FAMILY-001"]
        result.append(entry)

    for case_id, case_ids in CONFIG_CASES.items():
        entry = correctness_case(case_id)
        entry["kind"] = "configuration_error_control"
        entry["planned_case_ids"] = case_ids
        result.append(entry)

    tracefile = load_json(TRACEFILE_BASELINE)
    for case in tracefile["cases"]:
        if case["exit_status"] == 0 and ".ignore-" not in case["id"]:
            continue
        entry = tracefile_case(case)
        entry["kind"] = (
            "named_error_ignore_one" if ".ignore-" in case["id"] else "named_error_fatal"
        )
        entry["planned_case_ids"] = [
            "DIAG-IGNORE-WARN-001"
            if ".ignore-" in case["id"]
            else "DIAG-IGNORE-ERROR-001"
        ]
        result.append(entry)
    return result


def build_document(upstream_root: Path) -> dict[str, Any]:
    categories = registry_entries(upstream_root)
    controls = control_rules(upstream_root)
    surfaces = unclassified_surfaces(upstream_root)
    exits = exit_policies(upstream_root)
    planned = planned_case_ids()
    observations = oracle_observations()
    return {
        "schema_version": 1,
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "scope": "LCOV 2.5 named diagnostics, unclassified failure surfaces, severity and continuation controls, command exit policies, and retained Oracle references",
        "artifact_bindings": artifact_bindings(),
        "categories": categories,
        "control_rules": controls,
        "unclassified_surfaces": surfaces,
        "exit_policies": exits,
        "planned_case_ids": planned,
        "planned_case_evidence_status": "planned",
        "planned_case_product_evidence": [],
        "oracle_observations": observations,
        "oracle_observation_evidence_status": "oracle_reference",
        "oracle_observation_product_evidence": [],
        "known_evidence_gaps": [
            "ignore count two or greater",
            "warning promotion",
            "message suppression and expected counts",
            "converter keep-going traps",
            "parallel worker failure and state transfer",
            "geninfo no-args after a writable temporary directory is available",
        ],
        "totals": {
            "categories": len(categories),
            "category_symbol_references": sum(
                entry["symbol_reference_count"] for entry in categories
            ),
            "reserved_categories": sum(
                entry["emitter_status"] == "reserved_no_production_emitter"
                for entry in categories
            ),
            "control_rules": len(controls),
            "unclassified_surfaces": len(surfaces),
            "exit_policies": len(exits),
            "planned_cases": len(planned),
            "oracle_observations": len(observations),
            "startup_observations": sum(
                entry["kind"].startswith("startup") for entry in observations
            ),
            "parser_observations": sum(
                entry["kind"] == "parser_boundary" for entry in observations
            ),
            "configuration_observations": sum(
                entry["kind"] == "configuration_error_control"
                for entry in observations
            ),
            "named_error_fatal_observations": sum(
                entry["kind"] == "named_error_fatal" for entry in observations
            ),
            "named_error_ignore_one_observations": sum(
                entry["kind"] == "named_error_ignore_one" for entry in observations
            ),
        },
        "product_compatibility_evidence": False,
    }


def validate_schema(document: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise DiagnosticsContractError(
            f"diagnostics contract schema is invalid: {error.message}"
        ) from error
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise DiagnosticsContractError(
            f"diagnostics contract schema failure at {location}: {errors[0].message}"
        )


def validate_upstream_identity(upstream_root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip() != UPSTREAM_COMMIT:
        raise DiagnosticsContractError("diagnostics contract upstream commit mismatch")


def validate_source_references(document: dict[str, Any], upstream_root: Path) -> None:
    entries = [
        *document["control_rules"],
        *document["unclassified_surfaces"],
        *document["exit_policies"],
    ]
    for entry in entries:
        for reference in entry["source_references"]:
            actual = (upstream_root / reference["path"]).read_text(
                encoding="utf-8"
            ).splitlines()[reference["line"] - 1]
            if actual != reference["text"]:
                raise DiagnosticsContractError(
                    f"source text drift: {reference['path']}:{reference['line']}"
                )


def validate_document(document: dict[str, Any], upstream_root: Path) -> None:
    validate_schema(document)
    expected = build_document(upstream_root)
    if document["upstream_commit"] != UPSTREAM_COMMIT:
        raise DiagnosticsContractError("diagnostics document upstream commit drift")
    if document["categories"] != expected["categories"]:
        raise DiagnosticsContractError("diagnostic registry or symbol closure drift")
    if document["control_rules"] != expected["control_rules"]:
        raise DiagnosticsContractError("diagnostic control-rule drift")
    if document["unclassified_surfaces"] != expected["unclassified_surfaces"]:
        raise DiagnosticsContractError("unclassified diagnostic surface drift")
    if document["exit_policies"] != expected["exit_policies"]:
        raise DiagnosticsContractError("command exit-policy drift")
    if document["planned_case_ids"] != expected["planned_case_ids"]:
        raise DiagnosticsContractError("diagnostic planned-case catalog drift")
    if document["planned_case_evidence_status"] != "planned":
        raise DiagnosticsContractError("planned diagnostic case claims evidence")
    if document["planned_case_product_evidence"]:
        raise DiagnosticsContractError("planned diagnostic case claims product evidence")
    if document["artifact_bindings"] != expected["artifact_bindings"]:
        raise DiagnosticsContractError("retained diagnostics artifact binding drift")
    if document["oracle_observations"] != expected["oracle_observations"]:
        raise DiagnosticsContractError("diagnostic Oracle observation identity drift")
    if document["known_evidence_gaps"] != expected["known_evidence_gaps"]:
        raise DiagnosticsContractError("diagnostic evidence-gap inventory drift")
    if document["totals"] != expected["totals"]:
        raise DiagnosticsContractError("diagnostics contract totals drift")

    validate_source_references(document, upstream_root)
    if document["product_compatibility_evidence"]:
        raise DiagnosticsContractError("diagnostics contract claims product compatibility")
    for collection in (
        "categories",
        "control_rules",
        "unclassified_surfaces",
        "exit_policies",
    ):
        for entry in document[collection]:
            if entry["product_evidence"]:
                raise DiagnosticsContractError(
                    f"diagnostic reference claims product evidence: {entry['id']}"
                )
    if document["oracle_observation_evidence_status"] != "oracle_reference":
        raise DiagnosticsContractError("diagnostic Oracle reference claims product status")
    if document["oracle_observation_product_evidence"]:
        raise DiagnosticsContractError("diagnostic Oracle reference claims product evidence")


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
        print(f"DIAGNOSTICS_CONTRACT_WRITTEN path={OUTPUT_PATH.relative_to(ROOT)}")
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != content:
        raise DiagnosticsContractError(
            "committed diagnostics contract differs from generation"
        )
    print(
        "DIAGNOSTICS_CONTRACT_OK "
        f"categories={document['totals']['categories']} "
        f"symbol_refs={document['totals']['category_symbol_references']} "
        f"controls={document['totals']['control_rules']} "
        f"exit_policies={document['totals']['exit_policies']} "
        f"planned_cases={document['totals']['planned_cases']} "
        f"oracle_observations={document['totals']['oracle_observations']} "
        "product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
