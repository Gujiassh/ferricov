#!/usr/bin/env python3
"""Generate and validate the pinned LCOV environment/discovery contract."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).with_name("v2.5.json")
SCHEMA_PATH = ROOT / "compat/schema/environment-contract.schema.json"
CASE_CONTRACT_PATH = ROOT / "compat/correctness/m0-case-contract.json"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference")
)
SOURCE_ROOTS = ("bin", "lib", "scripts")
EXPECTED_NAMES = (
    "HOME",
    "HOSTNAME",
    "LCOV_FORCE_PARALLEL",
    "LCOV_HOME",
    "LCOV_PERL_PATH",
    "LCOV_PYTHON_PATH",
    "LCOV_SHOW_LOCATION",
    "LCOV_VALIDATE",
    "LC_ALL",
    "LOG_P4ANNOTATE",
    "MACHTYPE",
    "P4CLIENT",
    "P4PORT",
    "P4USER",
    "PERL5LIB",
    "PWD",
    "SOURCE_DATE_EPOCH",
    "USER",
    "V",
)
EXPECTED_DISCOVERY_IDS = (
    "configuration-discovery.explicit-files",
    "configuration-discovery.home",
    "configuration-discovery.lcov-home",
    "configuration-discovery.no-readable-default",
    "configuration-discovery.inline-include",
)
EXPECTED_DISCOVERY_PHASES = (
    ("initial_selection", 1),
    ("initial_selection", 2),
    ("initial_selection", 3),
    ("initial_selection", 4),
    ("recursive_read", None),
)
EXPECTED_ENV_USE_LINES = 36


class EnvironmentContractError(RuntimeError):
    """The environment contract is incomplete or inconsistent."""


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EnvironmentContractError(f"cannot load JSON document {path}: {error}") from error
    if not isinstance(value, dict):
        raise EnvironmentContractError(f"JSON document is not an object: {path}")
    return value


def source_reference(
    upstream_root: Path,
    path: str,
    line: int,
    access: str,
) -> dict[str, Any]:
    source = upstream_root / path
    try:
        text = source.read_text(encoding="utf-8").splitlines()[line - 1]
    except (OSError, IndexError) as error:
        raise EnvironmentContractError(f"cannot resolve source reference {path}:{line}") from error
    return {"path": path, "line": line, "access": access, "text": text}


def references(
    upstream_root: Path,
    *items: tuple[str, int, str],
) -> list[dict[str, Any]]:
    return [source_reference(upstream_root, *item) for item in items]


def oracle_case(suite_id: str, case_id: str) -> dict[str, str]:
    return {"suite_id": suite_id, "case_id": case_id}


def variable(
    upstream_root: Path,
    name: str,
    roles: list[str],
    access: list[str],
    consumers: list[str],
    observable_effect: str,
    source_items: list[tuple[str, int, str]],
    oracle_cases: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"environment.{name}",
        "name": name,
        "roles": sorted(roles),
        "access": sorted(access),
        "consumers": sorted(consumers),
        "observable_effect": observable_effect,
        "source_references": references(upstream_root, *source_items),
        "oracle_cases": sorted(oracle_cases or [], key=lambda case: (case["suite_id"], case["case_id"])),
        "review_status": "reviewed",
        "product_evidence": [],
    }


def named_variables(upstream_root: Path) -> list[dict[str, Any]]:
    base = "m0-config-contract-base"
    return sorted(
        [
            variable(
                upstream_root,
                "HOME",
                ["user_configuration"],
                ["read"],
                ["lcov configuration reader"],
                "Selects $HOME/.lcovrc as the first automatic configuration candidate when the file is readable.",
                [
                    ("lib/lcovutil.pm", 1453, "binding"),
                    ("lib/lcovutil.pm", 1454, "read"),
                    ("lib/lcovutil.pm", 1455, "read"),
                ],
                [
                    oracle_case(base, "m0-config-base-home-discovery"),
                    oracle_case("m0-config-contract-home-first", "m0-config-home-first-wins-over-lcov-home"),
                    oracle_case("m0-config-contract-lcov-home", "m0-config-lcov-home-fallback"),
                ],
            ),
            variable(
                upstream_root,
                "HOSTNAME",
                ["provenance_runtime"],
                ["read"],
                ["profile writer"],
                "Copies the ambient hostname into optional profile output without changing coverage computation.",
                [
                    ("lib/lcovutil.pm", 901, "binding"),
                    ("lib/lcovutil.pm", 902, "read"),
                    ("lib/lcovutil.pm", 903, "read"),
                ],
            ),
            variable(
                upstream_root,
                "LCOV_FORCE_PARALLEL",
                ["developer_control"],
                ["read"],
                ["callback lifecycle", "filter scheduler", "geninfo scheduler", "merge scheduler"],
                "Presence forces parallel code paths, chunk creation, callback save/restore, and temporary-state handling even for small inputs.",
                [
                    ("lib/lcovutil.pm", 1013, "read"),
                    ("bin/geninfo", 1321, "read"),
                    ("lib/lcovutil.pm", 8616, "read"),
                    ("lib/lcovutil.pm", 8652, "read"),
                    ("lib/lcovutil.pm", 8688, "read"),
                    ("lib/lcovutil.pm", 9889, "read"),
                ],
            ),
            variable(
                upstream_root,
                "LCOV_HOME",
                ["user_configuration"],
                ["read"],
                ["lcov configuration reader"],
                "Selects $LCOV_HOME/etc/lcovrc only when HOME did not yield a readable configuration file.",
                [
                    ("lib/lcovutil.pm", 1453, "binding"),
                    ("lib/lcovutil.pm", 1454, "read"),
                    ("lib/lcovutil.pm", 1455, "read"),
                ],
                [
                    oracle_case("m0-config-contract-home-first", "m0-config-home-first-wins-over-lcov-home"),
                    oracle_case("m0-config-contract-lcov-home", "m0-config-lcov-home-fallback"),
                ],
            ),
            variable(
                upstream_root,
                "LCOV_PERL_PATH",
                ["build_helper"],
                ["read"],
                ["bin/fix.pl"],
                "Supplies a requested Perl interpreter replacement to fix.pl when interpreter rewriting is explicitly enabled.",
                [("bin/fix.pl", 92, "read")],
            ),
            variable(
                upstream_root,
                "LCOV_PYTHON_PATH",
                ["build_helper"],
                ["read"],
                ["bin/fix.pl"],
                "Supplies a requested Python interpreter replacement to fix.pl when interpreter rewriting is explicitly enabled.",
                [("bin/fix.pl", 134, "read")],
            ),
            variable(
                upstream_root,
                "LCOV_SHOW_LOCATION",
                ["developer_control"],
                ["read"],
                ["diagnostic handler"],
                "Presence retains Perl source locations in diagnostics, and numeric values above one append a stack trace for errors.",
                [
                    ("lib/lcovutil.pm", 639, "read"),
                    ("lib/lcovutil.pm", 640, "read"),
                ],
            ),
            variable(
                upstream_root,
                "LCOV_VALIDATE",
                ["developer_control"],
                ["read"],
                ["genhtml"],
                "Presence enables generated HTML validation independently of the command-line validation option.",
                [("bin/genhtml", 7217, "read")],
            ),
            variable(
                upstream_root,
                "LC_ALL",
                ["process_control"],
                ["write"],
                ["geninfo"],
                "geninfo overwrites LC_ALL with C before running capture logic and inherited subprocesses.",
                [("bin/geninfo", 244, "write")],
            ),
            variable(
                upstream_root,
                "LOG_P4ANNOTATE",
                ["integration_runtime"],
                ["read"],
                ["p4annotate.pm"],
                "Provides the default Perforce annotation log path before callback or standalone command options are parsed.",
                [
                    ("scripts/p4annotate.pm", 76, "read"),
                    ("scripts/p4annotate.pm", 77, "read"),
                ],
            ),
            variable(
                upstream_root,
                "MACHTYPE",
                ["provenance_runtime"],
                ["read"],
                ["profile writer"],
                "Copies the ambient machine type into optional profile output without changing coverage computation.",
                [
                    ("lib/lcovutil.pm", 901, "binding"),
                    ("lib/lcovutil.pm", 902, "read"),
                    ("lib/lcovutil.pm", 903, "read"),
                ],
            ),
            variable(
                upstream_root,
                "P4CLIENT",
                ["integration_runtime"],
                ["read"],
                ["p4annotate.pm"],
                "Must be present when constructing the Perforce annotation callback and selects the active client workspace through p4.",
                [
                    ("scripts/p4annotate.pm", 97, "binding"),
                    ("scripts/p4annotate.pm", 98, "read"),
                ],
            ),
            variable(
                upstream_root,
                "P4PORT",
                ["integration_runtime"],
                ["read"],
                ["p4annotate.pm"],
                "Must be present when constructing the Perforce annotation callback and selects the server through p4.",
                [
                    ("scripts/p4annotate.pm", 97, "binding"),
                    ("scripts/p4annotate.pm", 98, "read"),
                ],
            ),
            variable(
                upstream_root,
                "P4USER",
                ["integration_runtime"],
                ["read"],
                ["p4annotate.pm"],
                "Must be present for the Perforce annotation callback and becomes the owner for locally modified lines.",
                [
                    ("scripts/p4annotate.pm", 97, "binding"),
                    ("scripts/p4annotate.pm", 98, "read"),
                    ("scripts/p4annotate.pm", 153, "read"),
                ],
            ),
            variable(
                upstream_root,
                "PERL5LIB",
                ["integration_runtime", "provenance_runtime"],
                ["read"],
                ["context.pm"],
                "When present, the context callback copies PERL5LIB into emitted context and optional coverage comments.",
                [
                    ("scripts/context.pm", 79, "read"),
                    ("scripts/context.pm", 80, "read"),
                ],
            ),
            variable(
                upstream_root,
                "PWD",
                ["provenance_runtime"],
                ["read"],
                ["profile writer"],
                "Copies the inherited PWD value into optional profile output alongside the independently measured current directory.",
                [
                    ("lib/lcovutil.pm", 901, "binding"),
                    ("lib/lcovutil.pm", 902, "read"),
                    ("lib/lcovutil.pm", 903, "read"),
                ],
            ),
            variable(
                upstream_root,
                "SOURCE_DATE_EPOCH",
                ["build_helper", "user_configuration"],
                ["read"],
                ["bin/fix.pl", "genhtml"],
                "Pins generated documentation dates, report age calculations, report timestamps, and generated file metadata to a reproducible epoch.",
                [
                    ("bin/fix.pl", 56, "read"),
                    ("bin/genhtml", 5687, "read"),
                    ("bin/genhtml", 5688, "read"),
                    ("bin/genhtml", 5696, "read"),
                    ("bin/genhtml", 5700, "read"),
                    ("bin/genhtml", 5702, "read"),
                    ("bin/genhtml", 5925, "read"),
                    ("bin/genhtml", 5926, "read"),
                    ("bin/genhtml", 8761, "read"),
                    ("bin/genhtml", 8762, "read"),
                ],
            ),
            variable(
                upstream_root,
                "USER",
                ["provenance_runtime"],
                ["read"],
                ["profile writer"],
                "Copies the ambient user name into optional profile output without changing coverage computation.",
                [
                    ("lib/lcovutil.pm", 901, "binding"),
                    ("lib/lcovutil.pm", 902, "read"),
                    ("lib/lcovutil.pm", 903, "read"),
                ],
            ),
            variable(
                upstream_root,
                "V",
                ["build_helper"],
                ["read"],
                ["bin/fix.pl"],
                "Controls fix.pl verbose output during source and installation payload rewriting.",
                [("bin/fix.pl", 45, "read")],
            ),
        ],
        key=lambda item: item["name"],
    )


def dynamic_inputs(upstream_root: Path) -> list[dict[str, Any]]:
    base = "m0-config-contract-base"
    return [
        {
            "id": "environment.config-expansion.*",
            "syntax": "$ENV{NAME}",
            "consumer": "lcov configuration reader",
            "observable_effect": (
                "Expands every referenced environment name in a configuration value; "
                "an absent name records a deferred usage diagnostic and skips the assignment."
            ),
            "source_references": references(
                upstream_root,
                ("lib/lcovutil.pm", 1379, "match"),
                ("lib/lcovutil.pm", 1381, "read"),
                ("lib/lcovutil.pm", 1390, "read"),
            ),
            "oracle_cases": sorted(
                [
                    oracle_case(base, "m0-config-base-missing-env"),
                    oracle_case(base, "m0-config-base-missing-env-ignored"),
                    oracle_case("m0-config-contract-env", "m0-config-env-multiple-expansion"),
                    oracle_case("m0-config-contract-env", "m0-config-env-single-expansion"),
                ],
                key=lambda case: (case["suite_id"], case["case_id"]),
            ),
            "review_status": "reviewed",
            "product_evidence": [],
        }
    ]


def discovery_path(
    upstream_root: Path,
    path_id: str,
    phase: str,
    selection_priority: int | None,
    kind: str,
    trigger: str,
    path_template: str,
    stop_condition: str,
    source_items: list[tuple[str, int, str]],
    oracle_cases: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "id": path_id,
        "phase": phase,
        "selection_priority": selection_priority,
        "kind": kind,
        "trigger": trigger,
        "path_template": path_template,
        "stop_condition": stop_condition,
        "source_references": references(upstream_root, *source_items),
        "oracle_cases": sorted(oracle_cases, key=lambda case: (case["suite_id"], case["case_id"])),
        "review_status": "reviewed",
        "product_evidence": [],
    }


def configuration_discovery(upstream_root: Path) -> list[dict[str, Any]]:
    base = "m0-config-contract-base"
    return [
        discovery_path(
            upstream_root,
            "configuration-discovery.explicit-files",
            "initial_selection",
            1,
            "explicit",
            "One or more --config-file values are present.",
            "Each command-line value as provided, in occurrence order",
            "All explicit files are read; automatic HOME and LCOV_HOME discovery is bypassed.",
            [
                ("lib/lcovutil.pm", 1438, "discovery"),
                ("lib/lcovutil.pm", 1448, "discovery"),
                ("lib/lcovutil.pm", 1449, "discovery"),
                ("lib/lcovutil.pm", 1450, "discovery"),
            ],
            [
                oracle_case(base, "m0-config-base-duplicate-explicit-file"),
                oracle_case(base, "m0-config-base-explicit-bypasses-home"),
                oracle_case(base, "m0-config-base-explicit-order-off-on"),
                oracle_case(base, "m0-config-base-explicit-order-on-off"),
                oracle_case(base, "m0-config-base-missing-explicit-is-early"),
            ],
        ),
        discovery_path(
            upstream_root,
            "configuration-discovery.home",
            "initial_selection",
            2,
            "home",
            "No explicit file is present, HOME exists, and $HOME/.lcovrc is readable.",
            "$HOME/.lcovrc",
            "The first readable automatic candidate is read and discovery stops.",
            [
                ("lib/lcovutil.pm", 1453, "discovery"),
                ("lib/lcovutil.pm", 1454, "discovery"),
                ("lib/lcovutil.pm", 1455, "discovery"),
                ("lib/lcovutil.pm", 1456, "discovery"),
                ("lib/lcovutil.pm", 1457, "discovery"),
                ("lib/lcovutil.pm", 1458, "discovery"),
            ],
            [
                oracle_case(base, "m0-config-base-home-discovery"),
                oracle_case("m0-config-contract-home-first", "m0-config-home-first-wins-over-lcov-home"),
            ],
        ),
        discovery_path(
            upstream_root,
            "configuration-discovery.lcov-home",
            "initial_selection",
            3,
            "lcov_home",
            "No explicit file or readable HOME file is present, LCOV_HOME exists, and its file is readable.",
            "$LCOV_HOME/etc/lcovrc",
            "The fallback file is read and automatic discovery stops.",
            [
                ("lib/lcovutil.pm", 1453, "discovery"),
                ("lib/lcovutil.pm", 1454, "discovery"),
                ("lib/lcovutil.pm", 1455, "discovery"),
                ("lib/lcovutil.pm", 1456, "discovery"),
                ("lib/lcovutil.pm", 1457, "discovery"),
                ("lib/lcovutil.pm", 1458, "discovery"),
            ],
            [
                oracle_case("m0-config-contract-lcov-home", "m0-config-lcov-home-fallback"),
                oracle_case("m0-config-contract-home-first", "m0-config-home-first-wins-over-lcov-home"),
            ],
        ),
        discovery_path(
            upstream_root,
            "configuration-discovery.no-readable-default",
            "initial_selection",
            4,
            "none",
            "No explicit file and neither automatic candidate is readable.",
            "No configuration file; the compiled installation prefix is not consulted",
            "Execution continues with built-in defaults and later --rc or command-line overrides.",
            [
                ("lib/lcovutil.pm", 1448, "discovery"),
                ("lib/lcovutil.pm", 1452, "discovery"),
                ("lib/lcovutil.pm", 1453, "discovery"),
                ("lib/lcovutil.pm", 1454, "discovery"),
                ("lib/lcovutil.pm", 1455, "discovery"),
                ("lib/lcovutil.pm", 1456, "discovery"),
                ("lib/lcovutil.pm", 1458, "discovery"),
            ],
            [oracle_case(base, "m0-config-base-no-discovery-control")],
        ),
        discovery_path(
            upstream_root,
            "configuration-discovery.inline-include",
            "recursive_read",
            None,
            "include",
            "A parsed configuration assignment uses the config_file key.",
            "The assigned path as provided, resolved by file open from process CWD",
            "The include is processed inline; canonical path identity rejects active loops.",
            [
                ("lib/lcovutil.pm", 1354, "discovery"),
                ("lib/lcovutil.pm", 1356, "discovery"),
                ("lib/lcovutil.pm", 1400, "discovery"),
                ("lib/lcovutil.pm", 1401, "discovery"),
            ],
            [
                oracle_case(base, "m0-config-base-include-loop"),
                oracle_case(base, "m0-config-base-inline-include-stops-parent"),
                oracle_case(base, "m0-config-base-relative-include"),
            ],
        ),
    ]


def build_document(upstream_root: Path) -> dict[str, Any]:
    variables = named_variables(upstream_root)
    dynamic = dynamic_inputs(upstream_root)
    discovery = configuration_discovery(upstream_root)
    oracle_bindings = sum(
        len(entry["oracle_cases"])
        for entry in [*variables, *dynamic, *discovery]
    )
    return {
        "schema_version": 1,
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "scope": "direct environment reads and writes in bin/, lib/, and scripts/, plus configuration discovery",
        "named_variables": variables,
        "dynamic_inputs": dynamic,
        "configuration_discovery": discovery,
        "totals": {
            "named_variables": len(variables),
            "dynamic_inputs": len(dynamic),
            "configuration_discovery_paths": len(discovery),
            "direct_env_use_lines": len(scan_env_use_lines(upstream_root)),
            "oracle_case_bindings": oracle_bindings,
        },
        "product_compatibility_evidence": False,
    }


def scan_env_use_lines(upstream_root: Path) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for root_name in SOURCE_ROOTS:
        root = upstream_root / root_name
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(upstream_root).as_posix()
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError as error:
                raise EnvironmentContractError(f"non-UTF-8 source in environment scope: {relative}") from error
            for line_number, text in enumerate(lines, start=1):
                if "$ENV" in text:
                    result.add((relative, line_number))
    return result


def validate_schema(document: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise EnvironmentContractError(f"environment schema is invalid: {error.message}") from error
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise EnvironmentContractError(f"environment contract schema failure at {location}: {errors[0].message}")


def validate_upstream_identity(upstream_root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip() != UPSTREAM_COMMIT:
        raise EnvironmentContractError("environment contract upstream commit mismatch")


def validate_oracle_cases(document: dict[str, Any]) -> None:
    case_contract = load_json(CASE_CONTRACT_PATH)
    available = {
        (record["suite_id"], record["case_id"])
        for record in case_contract["cases"]
    }
    for entry in [
        *document["named_variables"],
        *document["dynamic_inputs"],
        *document["configuration_discovery"],
    ]:
        cases = [(case["suite_id"], case["case_id"]) for case in entry["oracle_cases"]]
        if cases != sorted(set(cases)):
            raise EnvironmentContractError(f"Oracle cases are not sorted and unique: {entry['id']}")
        missing = set(cases) - available
        if missing:
            raise EnvironmentContractError(f"unknown Oracle case binding for {entry['id']}: {sorted(missing)}")


def validate_document(document: dict[str, Any], upstream_root: Path) -> None:
    validate_schema(document)
    names = [entry["name"] for entry in document["named_variables"]]
    if tuple(names) != EXPECTED_NAMES:
        raise EnvironmentContractError("named environment variable set or order drift")
    discovery_ids = tuple(entry["id"] for entry in document["configuration_discovery"])
    if discovery_ids != EXPECTED_DISCOVERY_IDS:
        raise EnvironmentContractError("configuration discovery identity or order drift")
    discovery_phases = tuple(
        (entry["phase"], entry["selection_priority"])
        for entry in document["configuration_discovery"]
    )
    if discovery_phases != EXPECTED_DISCOVERY_PHASES:
        raise EnvironmentContractError("configuration discovery phase or priority drift")

    source_lines = scan_env_use_lines(upstream_root)
    if len(source_lines) != EXPECTED_ENV_USE_LINES:
        raise EnvironmentContractError(
            f"expected {EXPECTED_ENV_USE_LINES} direct environment-use lines, found {len(source_lines)}"
        )
    covered_lines: set[tuple[str, int]] = set()
    all_entries = [
        *document["named_variables"],
        *document["dynamic_inputs"],
        *document["configuration_discovery"],
    ]
    for entry in all_entries:
        if entry["product_evidence"]:
            raise EnvironmentContractError(f"environment entry claims product evidence: {entry['id']}")
        references_seen: set[tuple[str, int, str]] = set()
        for reference in entry["source_references"]:
            key = (reference["path"], reference["line"], reference["access"])
            if key in references_seen:
                raise EnvironmentContractError(f"duplicate source reference for {entry['id']}: {key}")
            references_seen.add(key)
            path = upstream_root / reference["path"]
            try:
                actual = path.read_text(encoding="utf-8").splitlines()[reference["line"] - 1]
            except (OSError, IndexError) as error:
                raise EnvironmentContractError(
                    f"cannot validate source reference {reference['path']}:{reference['line']}"
                ) from error
            if actual != reference["text"]:
                raise EnvironmentContractError(
                    f"source text drift: {reference['path']}:{reference['line']}"
                )
            if "$ENV" in actual:
                covered_lines.add((reference["path"], reference["line"]))
    if covered_lines != source_lines:
        missing = sorted(source_lines - covered_lines)
        extra = sorted(covered_lines - source_lines)
        raise EnvironmentContractError(
            f"direct environment-use closure mismatch: missing={missing} extra={extra}"
        )

    expected_totals = {
        "named_variables": len(document["named_variables"]),
        "dynamic_inputs": len(document["dynamic_inputs"]),
        "configuration_discovery_paths": len(document["configuration_discovery"]),
        "direct_env_use_lines": len(source_lines),
        "oracle_case_bindings": sum(len(entry["oracle_cases"]) for entry in all_entries),
    }
    if document["totals"] != expected_totals:
        raise EnvironmentContractError("environment contract totals drift")
    validate_oracle_cases(document)


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
        print(f"ENVIRONMENT_CONTRACT_WRITTEN path={OUTPUT_PATH.relative_to(ROOT)}")
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != content:
        raise EnvironmentContractError("committed environment contract differs from generation")
    print(
        "ENVIRONMENT_CONTRACT_OK "
        f"named={document['totals']['named_variables']} "
        f"dynamic={document['totals']['dynamic_inputs']} "
        f"discovery={document['totals']['configuration_discovery_paths']} "
        f"env_use_lines={document['totals']['direct_env_use_lines']} "
        f"oracle_bindings={document['totals']['oracle_case_bindings']} "
        "product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
