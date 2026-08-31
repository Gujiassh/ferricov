#!/usr/bin/env python3
"""Validate compatibility contracts, snapshots, inventory, and result evidence."""

from __future__ import annotations

import argparse
import re
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator


PIN_PATH = Path(__file__).resolve().parent / "inventory" / "expected-pins.v2.5.json"
STATUS_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "ssot" / "m0-status.snapshot.json"
)
OPERATIONAL_STATUS_DOCUMENTS = (
    Path("docs/ssot/project.md"),
    Path("docs/ssot/compatibility-contract.md"),
    Path("docs/ssot/m0-status.snapshot.json"),
    Path("specs/001-full-lcov-compatibility/tasks.md"),
    Path("specs/001-full-lcov-compatibility/m1-tracefile-core-agent-spec.md"),
    Path("specs/001-full-lcov-compatibility/plan.md"),
)


def load_inventory_pins(path: Path = PIN_PATH) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "commands",
        "policy_families",
        "positionals",
        "generated_token_names",
        "unique_abbreviation_targets",
        "ambiguous_generated_tokens",
        "policy_source_paths",
    }
    missing = sorted(required - set(document))
    if missing:
        raise RuntimeError(f"inventory pin file missing fields: {missing}")
    if document.get("schema_version") != 1:
        raise RuntimeError(
            f"unsupported inventory pin schema_version: {document.get('schema_version')}"
        )
    return document


_PINS = load_inventory_pins()
EXPECTED_COMMANDS = {str(k): int(v) for k, v in _PINS["commands"].items()}
EXPECTED_POLICY_FAMILIES = {
    str(k): str(v) for k, v in _PINS["policy_families"].items()
}
EXPECTED_POSITIONALS = {
    str(k): [str(item) for item in v] for k, v in _PINS["positionals"].items()
}
EXPECTED_GENERATED_TOKEN_NAMES = {
    str(command): tuple(str(token) for token in tokens)
    for command, tokens in _PINS["generated_token_names"].items()
}
EXPECTED_UNIQUE_ABBREVIATION_TARGETS = {
    str(k): str(v) for k, v in _PINS["unique_abbreviation_targets"].items()
}
EXPECTED_AMBIGUOUS_GENERATED_TOKENS = {
    str(item) for item in _PINS["ambiguous_generated_tokens"]
}
EXPECTED_POLICY_SOURCE_PATHS = {
    str(command): {str(path) for path in paths}
    for command, paths in _PINS["policy_source_paths"].items()
}



_REQUIRED_MODEL_BLOCKED_CASE_IDS = ["M1-MD-020", "M1-TF-063", "M1-TF-064"]
_REQUIRED_AUTHORIZED_TASKS = [
    *[{"id": f"M1-CORE-{index:03d}", "state": "completed"} for index in range(1, 9)],
    {"id": "M1-CORE-009", "state": "authorized_bounded"},
]
_REQUIRED_UNAUTHORIZED_TASKS = [
    {"id": "M1-CORE-010", "state": "unauthorized"},
    {"id": "M1-CORE-011", "state": "unauthorized"},
]
_REQUIRED_EXCLUSIONS = {
    "A": [
        "command.geninfo.option.compat-libtool",
        "command.lcov.option.compat-libtool",
        "command.perl2lcov.option.preserve",
        "lcovrc.rtl-file-extensions",
        "lcovrc.geninfo-compat-libtool",
        "lcovrc.geninfo-gcov-all-blocks",
        "lcovrc.geninfo-interval-update",
    ],
    "B": [
        "PAR-GENINFO-CHILD-EXIT-FERRICOV-001",
        "PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001",
        "PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001",
    ],
    "C": _REQUIRED_MODEL_BLOCKED_CASE_IDS,
    "D": ["product_compatibility_evidence_false"],
}
_REQUIRED_NON_NEGOTIABLES = [
    "signed_na_not_hollow_closed",
    "ferricov_ids_not_oracle_bound",
    "blocked_case_ids_retained",
    "oracle_identity_not_relaxed",
    "ownership_not_widened",
    "deterministic_budgets_required",
    "core_010_011_unauthorized",
]
_REQUIRED_ACTIVATION_SIGNATURE = (
    "conditional-m1-core-001-through-009-only;core-009-bounded;"
    "exclusions-a-d-open;core-010-011-unauthorized;product-evidence-false"
)
_REQUIRED_BUDGETS = {
    "classification": "harness_safety_only_not_product_limits",
    "ci_smoke": {
        "input_bytes": 1_048_576, "field_bytes": 262_144, "records": 65_536,
        "sections": 65_536, "family_cardinality": 65_536,
        "per_case_seconds": 2, "worker_rss_bytes": 536_870_912,
        "per_target_seconds": 60,
    },
    "scheduled": {
        "input_bytes": 16_777_216, "field_bytes": 1_048_576,
        "records": 1_000_000, "sections": 65_536,
        "family_cardinality": 1_000_000, "per_case_seconds": 10,
        "worker_rss_bytes": 1_073_741_824, "per_target_seconds": 900,
    },
}
_ACTIVATION_BLOCK_START = "<!-- BEGIN GENERATED M1 ACTIVATION CONTRACT -->"
_ACTIVATION_BLOCK_END = "<!-- END GENERATED M1 ACTIVATION CONTRACT -->"


def _render_m1_activation_block(document: dict[str, object]) -> str:
    lines = [
        _ACTIVATION_BLOCK_START,
        "## Generated normative activation contract",
        "",
        "This block is generated from `m1-v0.1-support-matrix.activation.json`.",
        "No authorization claim outside this block is normative.",
        "",
        f"- Status: `{document['status']}`",
        f"- Signature: `{document['signature']}`",
        "- Product compatibility evidence: `false`",
        "- Budgets: harness safety controls only; never product limits",
        "",
        "### Authorized tasks",
    ]
    lines.extend(
        f"- `{task['id']}`: `{task['state']}`"
        for task in document["authorized_tasks"]
    )
    lines.extend(["", "### Unauthorized tasks"])
    lines.extend(
        f"- `{task['id']}`: `{task['state']}`"
        for task in document["unauthorized_tasks"]
    )
    lines.extend(["", "### Exclusions A-D"])
    for group, ids in document["exclusions"].items():
        lines.append(f"- {group}: " + ", ".join(f"`{case_id}`" for case_id in ids))
    lines.extend(["", "### Non-negotiables"])
    lines.extend(f"- `{item}`" for item in document["non_negotiables"])
    lines.extend(["", "### Deterministic harness budgets"])
    for lane in ("ci_smoke", "scheduled"):
        values = document["budgets"][lane]
        rendered = ", ".join(f"{key}={value}" for key, value in values.items())
        lines.append(f"- `{lane}`: {rendered}")
    lines.append(_ACTIVATION_BLOCK_END)
    return "\n".join(lines)


def _load_m1_activation_contract(root: Path, markdown_text: str) -> dict[str, object]:
    relative = "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.activation.json"
    required_link = (
        "Machine authority: "
        "[`m1-v0.1-support-matrix.activation.json`]"
        "(m1-v0.1-support-matrix.activation.json)"
    )
    if markdown_text.count(required_link) != 1:
        raise RuntimeError("support matrix must bind exactly one machine activation contract")
    path = root / relative
    if not path.is_file():
        raise RuntimeError("support matrix machine activation contract is missing")
    raw = path.read_text(encoding="utf-8")
    document = json.loads(raw)
    if raw != json.dumps(document, indent=2, sort_keys=True) + "\n":
        raise RuntimeError("support matrix activation contract is not canonical JSON")
    expected_scalars = {
        "schema_version": 1,
        "kind": "m1_v0_1_support_matrix_activation",
        "status": "active",
        "markdown": "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md",
        "signature": _REQUIRED_ACTIVATION_SIGNATURE,
    }
    for key, expected in expected_scalars.items():
        if document.get(key) != expected:
            raise RuntimeError(f"support matrix activation contract has invalid {key}")
    expected_keys = {
        "schema_version", "kind", "status", "markdown", "authorized_tasks",
        "unauthorized_tasks", "exclusions", "non_negotiables", "budgets", "signature",
    }
    if set(document) != expected_keys:
        raise RuntimeError("support matrix activation contract has unexpected or missing keys")
    if document.get("authorized_tasks") != _REQUIRED_AUTHORIZED_TASKS:
        raise RuntimeError("support matrix must authorize exactly CORE-001 through CORE-009")
    if document.get("unauthorized_tasks") != _REQUIRED_UNAUTHORIZED_TASKS:
        raise RuntimeError("support matrix must explicitly keep CORE-010 and CORE-011 unauthorized")
    if document.get("exclusions") != _REQUIRED_EXCLUSIONS:
        raise RuntimeError("support matrix exclusions A-D are missing, duplicated, or changed")
    if document.get("non_negotiables") != _REQUIRED_NON_NEGOTIABLES:
        raise RuntimeError("support matrix non-negotiables are missing, duplicated, or changed")
    if document.get("budgets") != _REQUIRED_BUDGETS:
        raise RuntimeError("support matrix deterministic budgets are missing or changed")
    if markdown_text.count(_ACTIVATION_BLOCK_START) != 1 or markdown_text.count(_ACTIVATION_BLOCK_END) != 1:
        raise RuntimeError("support matrix must contain exactly one generated activation block")
    start = markdown_text.index(_ACTIVATION_BLOCK_START)
    end = markdown_text.index(_ACTIVATION_BLOCK_END) + len(_ACTIVATION_BLOCK_END)
    actual_block = markdown_text[start:end]
    if actual_block != _render_m1_activation_block(document):
        raise RuntimeError("support matrix generated activation block differs from machine contract")
    return document

def build_m0_status_snapshot(root: Path) -> dict[str, object]:
    behavior = json.loads(
        (root / "compat/behavior/contract.json").read_text(encoding="utf-8")
    )
    bindings = json.loads(
        (root / "compat/behavior/plan-bindings.json").read_text(encoding="utf-8")
    )
    diagnostics = json.loads(
        (root / "compat/diagnostics/v2.5.json").read_text(encoding="utf-8")
    )
    model = json.loads((root / "compat/model/v2.5.json").read_text(encoding="utf-8"))
    totals = behavior["totals"]
    planned = set(diagnostics.get("planned_case_ids") or [])
    bound: set[str] = set()
    for observation in diagnostics.get("oracle_observations") or []:
        for case_id in observation.get("planned_case_ids") or []:
            bound.add(str(case_id))
    unbound = sorted(planned - bound)

    product_evidence_paths = [
        "compat/environment/v2.5.json",
        "compat/tracefile/v2.5.json",
        "compat/diagnostics/v2.5.json",
        "compat/installation/v2.5.json",
        "compat/resources/v2.5.json",
        "compat/model/v2.5.json",
        "compat/fixtures/m0-cli-contract/oracle-baseline-status.json",
    ]
    product_flags: dict[str, bool] = {}
    for rel in product_evidence_paths:
        document = json.loads((root / rel).read_text(encoding="utf-8"))
        if "product_compatibility_evidence" in document:
            product_flags[rel] = bool(document["product_compatibility_evidence"])
            continue
        found: list[bool] = []

        def walk(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "product_compatibility_evidence":
                        found.append(bool(value))
                    else:
                        walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(document)
        product_flags[rel] = any(found)

    any_product = any(product_flags.values())
    blockers: list[dict[str, object]] = [
        {
            "id": "behavior_primary_gaps",
            "kind": "m0_residual",
            "count": totals["uncovered_public_entries"],
            "detail": "Unreviewed primary public-entry case groups remain in the behavior contract.",
        },
        {
            "id": "M1-MD-020",
            "kind": "decision_blocker",
            "detail": "Coverage-model decision remains blocked in compat/model/v2.5.json.",
        },
        {
            "id": "M1-TF-063",
            "kind": "decision_blocker",
            "detail": "Tracefile decision remains blocked in model contract blocked_case_ids.",
        },
        {
            "id": "M1-TF-064",
            "kind": "decision_blocker",
            "detail": "Tracefile decision remains blocked in model contract blocked_case_ids.",
        },
        {
            "id": "diagnostics_unbound_planned_cases",
            "kind": "m0_residual",
            "count": len(unbound),
            "ids": unbound,
            "detail": "Planned diagnostic/parallel case IDs without exact Oracle bindings.",
        },
        {
            "id": "product_compatibility_evidence_false",
            "kind": "gate",
            "detail": "No domain contract currently sets product_compatibility_evidence true.",
        },
    ]
    go_no_go = root / "specs/001-full-lcov-compatibility/m0-go-no-go.md"
    support_matrix = root / "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md"
    m1_authorized = False
    m1_authorized_task_ids: list[str] = []
    if not go_no_go.is_file():
        blockers.append(
            {
                "id": "m0_exit_review_missing",
                "kind": "process",
                "detail": (
                    "M0 go/no-go review artifact required before M1 activation "
                    "(expected specs/001-full-lcov-compatibility/m0-go-no-go.md)."
                ),
            }
        )
    else:
        go_text = go_no_go.read_text(encoding="utf-8")
        # Prefer the controller signature line.
        has_go = "**Result: GO**" in go_text
        has_no_go = "**Result: NO-GO" in go_text and not has_go
        if has_no_go:
            blockers.append(
                {
                    "id": "m0_exit_review_no_go",
                    "kind": "process",
                    "detail": (
                        "M0 go/no-go artifact records NO-GO for M1 activation; "
                        "see specs/001-full-lcov-compatibility/m0-go-no-go.md."
                    ),
                }
            )
        elif has_go:
            if not support_matrix.is_file():
                blockers.append(
                    {
                        "id": "m1_support_matrix_missing",
                        "kind": "process",
                        "detail": (
                            "Conditional GO requires "
                            "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md."
                        ),
                    }
                )
            else:
                matrix_text = support_matrix.read_text(encoding="utf-8")
                if any_product:
                    blockers.append(
                        {
                            "id": "product_compatibility_evidence_blocks_conditional_go",
                            "kind": "gate",
                            "detail": (
                                "Conditional GO forbids product_compatibility_evidence=true "
                                "until CORE-010 parity evidence is reviewed."
                            ),
                        }
                    )
                else:
                    m1_authorized = True
                    activation = _load_m1_activation_contract(root, matrix_text)
                    live_behavior_gap_ids: list[str] = []
                    for case_group in behavior.get("case_groups") or []:
                        if case_group.get("review_status") == "reviewed":
                            continue
                        primary = [
                            str(target["id"])
                            for target in case_group.get("targets") or []
                            if target.get("role") == "primary"
                        ]
                        if len(primary) != 1:
                            raise RuntimeError(
                                "each live unreviewed behavior gap must have one primary ID"
                            )
                        live_behavior_gap_ids.extend(primary)
                    live_behavior_gap_ids.sort()
                    if sorted(activation["exclusions"]["A"]) != live_behavior_gap_ids:
                        raise RuntimeError(
                            "support matrix exclusion A must equal exact live behavior gap IDs"
                        )
                    if sorted(activation["exclusions"]["B"]) != unbound:
                        raise RuntimeError(
                            "support matrix exclusion B must equal exact live unbound diagnostics IDs"
                        )
                    live_blocked_case_ids = list(model.get("blocked_case_ids") or [])
                    if live_blocked_case_ids != _REQUIRED_MODEL_BLOCKED_CASE_IDS:
                        raise RuntimeError(
                            "conditional CORE-009 authorization requires exact live "
                            "blocked_case_ids M1-MD-020/M1-TF-063/M1-TF-064"
                        )
                    m1_authorized_task_ids = [
                        str(task["id"]) for task in activation["authorized_tasks"]
                    ]
                    # Keep residual/model blockers visible, but mark them as
                    # matrix-excluded deferred work rather than hard process stops.
                    for blocker in blockers:
                        if blocker.get("id") in {
                            "behavior_primary_gaps",
                            "diagnostics_unbound_planned_cases",
                            "M1-MD-020",
                            "M1-TF-063",
                            "M1-TF-064",
                        }:
                            blocker["activation_treatment"] = "excluded_by_m1_v0_1_support_matrix"
                            blocker["blocks_m1_core_001_008"] = False
                            blocker["blocks_authorized_m1_core_tasks"] = False
                        if blocker.get("id") == "product_compatibility_evidence_false":
                            blocker["activation_treatment"] = "required_false_under_conditional_go"
                            blocker["blocks_m1_core_001_008"] = False
                            blocker["blocks_authorized_m1_core_tasks"] = False
        else:
            blockers.append(
                {
                    "id": "m0_exit_review_undecided",
                    "kind": "process",
                    "detail": (
                        "M0 go/no-go artifact lacks a Result: GO or Result: NO-GO signature."
                    ),
                }
            )
    return {
        "schema_version": 2,
        "kind": "m0_status_snapshot",
        "upstream_release": "v2.5",
        "upstream_commit": "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
        "canonical_worktree": "/home/cc/code1/ferricov",
        "sources": {
            "behavior_contract": "compat/behavior/contract.json",
            "plan_bindings": "compat/behavior/plan-bindings.json",
            "diagnostics_contract": "compat/diagnostics/v2.5.json",
            "model_contract": "compat/model/v2.5.json",
            "inventory_pins": "compat/inventory/expected-pins.v2.5.json",
            "m0_go_no_go": "specs/001-full-lcov-compatibility/m0-go-no-go.md",
            "m1_v0_1_support_matrix": "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md",
            "m1_v0_1_activation_contract": "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.activation.json",
        },
        "behavior": {
            "public_inventory_entries": totals["public_inventory_entries"],
            "primary_case_coverage": totals["primary_case_coverage"],
            "reviewed_primary_coverage": totals["reviewed_primary_coverage"],
            "uncovered_public_entries": totals["uncovered_public_entries"],
            "case_groups_reviewed": totals["case_review_status"]["reviewed"],
            "case_groups_unreviewed": totals["case_review_status"]["unreviewed"],
            "required_interaction_domains": totals["required_interaction_domains"],
            "reviewed_interaction_domains": totals["reviewed_interaction_domains"],
            "fixed_source_interaction_projections": bindings["totals"]["primary_plans"],
            "critical_interactions": bindings["totals"]["critical_interactions"],
        },
        "diagnostics": {
            "planned_cases": diagnostics["totals"]["planned_cases"],
            "exact_bound_planned_cases": len(planned & bound),
            "unbound_planned_cases": len(unbound),
            "unbound_planned_case_ids": unbound,
            "oracle_observations": diagnostics["totals"]["oracle_observations"],
        },
        "product_compatibility_evidence": False if not any_product else True,
        "product_compatibility_evidence_by_source": product_flags,
        "m1_authorized": m1_authorized,
        "m1_authorized_task_ids": m1_authorized_task_ids,
        "m1_activation_blockers": blockers,
        "model_blocked_case_ids": list(model.get("blocked_case_ids") or []),
    }


def validate_m0_status_snapshot(root: Path) -> None:
    expected = build_m0_status_snapshot(root)
    # Fail closed if any product evidence is true while snapshot claims false.
    if expected["product_compatibility_evidence"] is True:
        raise RuntimeError(
            "product_compatibility_evidence is true in one or more domain contracts; "
            "update the status snapshot generation rules before claiming M0 hygiene"
        )
    if expected["m1_authorized"] not in (False, True):
        raise RuntimeError("m1_authorized must be a boolean")
    if expected["m1_authorized"] is True and expected["product_compatibility_evidence"] is True:
        raise RuntimeError(
            "conditional M1 authorization forbids product_compatibility_evidence=true"
        )

    snapshot_path = root / "docs/ssot/m0-status.snapshot.json"
    committed = json.loads(snapshot_path.read_text(encoding="utf-8"))
    # Compare canonical JSON to avoid key-order noise after sort_keys generation.
    expected_text = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    committed_text = json.dumps(committed, indent=2, sort_keys=True) + "\n"
    if committed_text != expected_text:
        raise RuntimeError(
            "docs/ssot/m0-status.snapshot.json is out of date with live contracts; "
            "run: python3 compat/status/generate_m0_status.py"
        )

    behavior = expected["behavior"]
    reviewed = behavior["reviewed_primary_coverage"]
    gaps = behavior["uncovered_public_entries"]
    projections = behavior["fixed_source_interaction_projections"]
    public_entries = behavior["public_inventory_entries"]

    # Operational docs must not present a conflicting residual triple.
    # Historical review files under reviews/ are excluded.
    stale_patterns = [
        (
            re.compile(r"440\s+substantive\s+reviewed\s+primary"),
            "stale reviewed-primary count 440",
        ),
        (
            re.compile(r"91\s+explicit\s+M0\s+gaps"),
            "stale M0 gap count 91",
        ),
        (
            re.compile(r"442\s+fixed\s+source\s+and\s+interaction\s+projections"),
            "stale projection count 442",
        ),
        (
            re.compile(r"with\s+91\s+behavior-planning\s+gaps"),
            "stale M1 handoff gap count 91",
        ),
    ]
    for rel in OPERATIONAL_STATUS_DOCUMENTS:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        for pattern, label in stale_patterns:
            if pattern.search(text):
                raise RuntimeError(f"{rel}: {label}; live totals are reviewed={reviewed} gaps={gaps} projections={projections}")

        # If a document quotes the live residual numbers, require exact current triple.
        if "reviewed primary" in text.lower() or "m0 gaps remain" in text.lower() or "behavior-planning gaps" in text.lower():
            # Accept either the live numbers or an explicit pointer to the snapshot.
            has_live = (
                str(reviewed) in text
                and str(gaps) in text
                and str(public_entries) in text
            )
            has_pointer = "m0-status.snapshot.json" in text
            if not (has_live or has_pointer):
                raise RuntimeError(
                    f"{rel}: operational status prose must cite docs/ssot/m0-status.snapshot.json "
                    f"or include live residual metrics public={public_entries} reviewed={reviewed} gaps={gaps}"
                )

    print(
        "M0_STATUS_OK "
        f"public={public_entries} reviewed_primary={reviewed} gaps={gaps} "
        f"projections={projections} m1_authorized={str(expected['m1_authorized']).lower()} "
        f"product_compatibility_evidence=false"
    )




def validate_documents(schema_path: Path, documents: list[Path]) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for document in documents:
        validator.validate(json.loads(document.read_text(encoding="utf-8")))
    print(f"SCHEMA_OK schema={schema_path} documents={len(documents)}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_parser_policy(command: str) -> dict[str, object]:
    family = EXPECTED_POLICY_FAMILIES[command]
    if family in {"shared_getopt_long", "direct_getopt_long"}:
        return {
            "family": family,
            "auto_abbrev": "unique_prefix",
            "case_sensitive": False,
            "accepted_long_prefixes": ["--", "-"],
            "plus_prefix_behavior": "option",
            "option_ordering": "permute",
            "bundling": "disabled",
            "posixly_correct_effect": "disable_auto_abbrev_and_plus_require_order",
            "exact_only_options": ["--config-file", "--rc"]
            if family == "shared_getopt_long"
            else [],
        }
    if family == "argparse":
        return {
            "family": family,
            "auto_abbrev": "unique_prefix",
            "case_sensitive": True,
            "accepted_long_prefixes": ["--"],
            "plus_prefix_behavior": "positional",
            "option_ordering": "argparse_parse_args",
            "bundling": "argparse_short_clusters",
            "posixly_correct_effect": "none",
            "exact_only_options": [],
        }
    return {
        "family": "none",
        "auto_abbrev": "not_applicable",
        "case_sensitive": None,
        "accepted_long_prefixes": [],
        "plus_prefix_behavior": "ignored",
        "option_ordering": "ignored",
        "bundling": "not_applicable",
        "posixly_correct_effect": "not_applicable",
        "exact_only_options": [],
    }


def source_path_is_safe(path: str) -> bool:
    parsed = PurePosixPath(path)
    return bool(path) and not parsed.is_absolute() and ".." not in parsed.parts


def expected_profile_parser_resolutions() -> dict[str, dict[str, dict[str, str]]]:
    expected = {}
    for command, tokens in EXPECTED_GENERATED_TOKEN_NAMES.items():
        for token in tokens:
            option_id = f"command.{command}.option.{token.removeprefix('--')}"
            if option_id in EXPECTED_UNIQUE_ABBREVIATION_TARGETS:
                default_profile = {
                    "acceptance": "accepted_unique_abbreviation",
                    "target": EXPECTED_UNIQUE_ABBREVIATION_TARGETS[option_id],
                }
            elif option_id in EXPECTED_AMBIGUOUS_GENERATED_TOKENS:
                default_profile = {"acceptance": "rejected_ambiguous"}
            else:
                default_profile = {"acceptance": "rejected_unknown"}
            expected[option_id] = {
                "default_profile": default_profile,
                "posix_profile": {"acceptance": "rejected_unknown"},
            }
    return expected


def validate_inventory_semantics(path: Path) -> None:
    inventory = json.loads(path.read_text(encoding="utf-8"))
    commands = inventory["commands"]
    options = [option for command in commands for option in command["options"]]
    positionals = [
        positional
        for command in commands
        for positional in command["positional_arguments"]
    ]
    entries = options + positionals + inventory["config_keys"] + inventory["support_scripts"]
    totals = inventory["totals"]

    command_names = [command["name"] for command in commands]
    if len(command_names) != len(set(command_names)) or set(command_names) != set(
        EXPECTED_COMMANDS
    ):
        raise RuntimeError(
            f"installed command set mismatch: expected {sorted(EXPECTED_COMMANDS)}, "
            f"found {command_names}"
        )

    parser_counts = {
        command["name"]: sum(
            any(source["kind"] == "parser_definition" for source in option["source_references"])
            for option in command["options"]
        )
        for command in commands
    }
    if parser_counts != EXPECTED_COMMANDS:
        raise RuntimeError(
            f"parser-backed command totals mismatch: expected {EXPECTED_COMMANDS}, found {parser_counts}"
        )

    policy_families = {
        command["name"]: command["parser_policy"]["family"] for command in commands
    }
    if policy_families != EXPECTED_POLICY_FAMILIES:
        raise RuntimeError(
            f"parser policy families mismatch: expected {EXPECTED_POLICY_FAMILIES}, "
            f"found {policy_families}"
        )

    positional_names = {
        command["name"]: [entry["name"] for entry in command["positional_arguments"]]
        for command in commands
    }
    if positional_names != EXPECTED_POSITIONALS:
        raise RuntimeError(
            f"positional contract mismatch: expected {EXPECTED_POSITIONALS}, "
            f"found {positional_names}"
        )

    expected_totals = {
        "installed_commands": len(commands),
        "command_options": len(options),
        "parser_command_options": sum(parser_counts.values()),
        "public_command_options": sum(
            option["review_status"] == "reviewed"
            and option["classification"] == "public"
            for option in options
        ),
        "unreviewed_command_options": sum(
            option["review_status"] == "unreviewed" for option in options
        ),
        "positional_arguments": len(positionals),
        "config_keys": len(inventory["config_keys"]),
        "support_scripts": len(inventory["support_scripts"]),
    }
    if totals != expected_totals:
        raise RuntimeError(
            f"inventory totals mismatch: expected {expected_totals}, found {totals}"
        )

    entry_ids = [entry["id"] for entry in entries]
    if len(entry_ids) != len(set(entry_ids)):
        raise RuntimeError("inventory entry IDs are not globally unique")

    for command in commands:
        name = command["name"]
        policy = command["parser_policy"]
        observed_policy = {
            key: value for key, value in policy.items() if key != "source_references"
        }
        expected_policy = expected_parser_policy(name)
        if observed_policy != expected_policy:
            raise RuntimeError(
                f"parser policy mismatch for {name}: expected {expected_policy}, "
                f"found {observed_policy}"
            )

        canonical_names = [option["canonical_name"] for option in command["options"]]
        if len(canonical_names) != len(set(canonical_names)):
            raise RuntimeError(f"duplicate canonical option in {command['name']}")
        forms = []
        for option in command["options"]:
            aliases = option["aliases"]
            if option["canonical_name"] in aliases or len(aliases) != len(set(aliases)):
                raise RuntimeError(f"invalid aliases for {option['id']}")
            forms.extend([option["canonical_name"], *aliases])
            source_kinds = {source["kind"] for source in option["source_references"]}
            if option["classification"] == "public" and "parser_definition" not in source_kinds:
                raise RuntimeError(f"public option lacks parser evidence: {option['id']}")
            if option["classification"] == "generated_token" and "parser_definition" in source_kinds:
                raise RuntimeError(f"generated token has parser evidence: {option['id']}")
        if len(forms) != len(set(forms)):
            raise RuntimeError(f"option forms overlap in {command['name']}")

        for exact_only in policy["exact_only_options"]:
            if exact_only not in forms:
                raise RuntimeError(
                    f"exact-only parser option is not defined for {name}: {exact_only}"
                )

        policy_sources = policy["source_references"]
        expected_policy_kinds = (
            {"command_implementation"} if name == "xml2lcovutil.py" else {"parser_policy"}
        )
        if {source["kind"] for source in policy_sources} != expected_policy_kinds:
            raise RuntimeError(f"parser policy source kinds mismatch for {name}")

        command_parser_sources = [
            source
            for entry in [*command["options"], *command["positional_arguments"]]
            for source in entry["source_references"]
            if source["kind"] == "parser_definition"
        ]
        command_policy_sources = [
            source
            for source in policy_sources
            if source["kind"] in {"parser_policy", "command_implementation"}
        ]
        parser_source_paths = {source["path"] for source in command_parser_sources}
        policy_source_paths = {
            source["path"]
            for source in command_policy_sources
        }
        if not parser_source_paths <= EXPECTED_POLICY_SOURCE_PATHS[name]:
            raise RuntimeError(
                f"parser definition path outside allowlist for {name}: "
                f"{sorted(parser_source_paths)}"
            )
        if policy_source_paths != EXPECTED_POLICY_SOURCE_PATHS[name]:
            raise RuntimeError(
                f"parser policy source paths mismatch for {name}: "
                f"expected {sorted(EXPECTED_POLICY_SOURCE_PATHS[name])}, "
                f"found {sorted(policy_source_paths)}"
            )

    all_source_references = [
        source
        for command in commands
        for source in command["parser_policy"]["source_references"]
    ] + [
        source
        for entry in entries
        for source in entry["source_references"]
    ]
    for source in all_source_references:
        if not source_path_is_safe(source["path"]) or source["line"] < 1:
            raise RuntimeError(f"unsafe inventory source reference: {source}")

    generated_options = {
        option["id"]: option
        for option in options
        if option["classification"] == "generated_token"
    }
    profiled_options = {
        option["id"]: option["profile_parser_resolution"]
        for option in options
        if "profile_parser_resolution" in option
    }
    expected_resolutions = expected_profile_parser_resolutions()
    if (
        set(generated_options) != set(profiled_options)
        or set(profiled_options) != set(expected_resolutions)
    ):
        raise RuntimeError(
            "all 41 generated tokens must exactly and exclusively own both parser profiles: "
            f"generated={sorted(generated_options)} profiled={sorted(profiled_options)}"
        )
    mismatched_resolutions = {
        option_id: {
            "expected": expected_resolutions[option_id],
            "actual": profiled_options[option_id],
        }
        for option_id in expected_resolutions
        if profiled_options[option_id] != expected_resolutions[option_id]
    }
    if mismatched_resolutions:
        raise RuntimeError(
            f"profile parser resolution drift: {mismatched_resolutions}"
        )

    option_by_id = {option["id"]: option for option in options}
    for target in EXPECTED_UNIQUE_ABBREVIATION_TARGETS.values():
        if target not in option_by_id or not any(
            source["kind"] == "parser_definition"
            for source in option_by_id[target]["source_references"]
        ):
            raise RuntimeError(
                f"accepted parser resolution target is not parser-backed: {target}"
            )
    if len(positionals) != 9 or any(
        not any(source["kind"] == "parser_definition" for source in entry["source_references"])
        for entry in positionals
    ):
        raise RuntimeError("positional inventory must contain nine parser-backed entries")
    print(
        f"INVENTORY_SEMANTICS_OK entries={len(entries)} "
        f"parser_options={totals['parser_command_options']} positionals={len(positionals)} "
        f"generated_tokens={len(generated_options)} parser_profiles={len(profiled_options) * 2}"
    )


def validate_inventory_sources(root: Path, upstream_root: Path) -> None:
    inventory = json.loads(
        (root / "compat/inventory/v2.5.json").read_text(encoding="utf-8")
    )
    source_cache: dict[Path, list[str]] = {}

    def resolve(source_path: str) -> Path:
        if not source_path_is_safe(source_path):
            raise RuntimeError(f"unsafe inventory source path: {source_path}")
        if source_path.startswith("help/"):
            return root / "compat/upstream" / source_path
        return upstream_root / source_path

    def source_lines(source_path: str) -> list[str]:
        resolved = resolve(source_path)
        if resolved not in source_cache:
            if not resolved.is_file():
                raise RuntimeError(f"inventory source file is missing: {source_path}")
            source_cache[resolved] = resolved.read_text(
                encoding="utf-8", errors="strict"
            ).splitlines()
        return source_cache[resolved]

    def validate_reference(source: dict[str, object], owner: str) -> str:
        path = str(source["path"])
        lines = source_lines(path)
        line = int(source["line"])
        if line < 1 or line > len(lines):
            raise RuntimeError(
                f"inventory source line out of bounds for {owner}: "
                f"{path}:{line} has {len(lines)} lines"
            )
        return lines[line - 1]

    for command in inventory["commands"]:
        for field in ("help_snapshot", "manual"):
            if command[field] is not None:
                source_lines(command[field])
        for source in command["parser_policy"]["source_references"]:
            validate_reference(source, f"command.{command['name']}.parser-policy")
        for option in command["options"]:
            for source in option["source_references"]:
                line_text = validate_reference(source, option["id"])
                if (
                    source["kind"] == "parser_definition"
                    and option["canonical_name"] != "--help"
                    and option["canonical_name"].lstrip("-") not in line_text
                ):
                    raise RuntimeError(
                        f"parser definition does not contain canonical name for "
                        f"{option['id']}: {source['path']}:{source['line']}"
                    )
        for positional in command["positional_arguments"]:
            for source in positional["source_references"]:
                validate_reference(source, positional["id"])
    for collection in (inventory["config_keys"], inventory["support_scripts"]):
        for entry in collection:
            for source in entry["source_references"]:
                validate_reference(source, entry["id"])
    print(
        f"INVENTORY_SOURCES_OK files={len(source_cache)} "
        f"upstream={upstream_root}"
    )


def run_oracle_parser_probes(oracle_image: str) -> None:
    probes = [
        (
            "getopt_unique_abbrev",
            ["genhtml", "--diff", "missing.info"],
            2,
            [b"Specified --diff-file", b"no files specified"],
        ),
        (
            "getopt_ambiguous_fail",
            ["genhtml", "--fail"],
            1,
            [b"Option fail is ambiguous"],
        ),
        (
            "getopt_ambiguous_sort",
            ["genhtml", "--sort"],
            1,
            [b"Option sort is ambiguous"],
        ),
        (
            "argparse_unique_abbrev",
            ["py2lcov", "--he"],
            0,
            [b"usage: py2lcov", b"show this help message and exit"],
        ),
        (
            "argparse_ambiguous",
            ["py2lcov", "--ver"],
            2,
            [b"ambiguous option: --ver", b"--verbose, --version-script"],
        ),
        (
            "argparse_parse_args_boundary",
            ["py2lcov", "first.xml", "--no", "later.xml"],
            2,
            [b"unrecognized arguments: later.xml"],
        ),
    ]
    for name, arguments, expected_status, expected_fragments in probes:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                oracle_image,
                *arguments,
            ],
            check=False,
            capture_output=True,
        )
        combined = result.stdout + result.stderr
        if result.returncode != expected_status or any(
            fragment not in combined for fragment in expected_fragments
        ):
            raise RuntimeError(
                f"Oracle parser probe failed: {name} status={result.returncode} "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )
    print(f"ORACLE_PARSER_POLICIES_OK probes={len(probes)} network=none")


def run_profile_parser_resolution_probes(
    inventory_path: Path, oracle_image: str
) -> None:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    options_by_id = {
        option["id"]: option
        for command in inventory["commands"]
        for option in command["options"]
    }
    requests = []
    expectations = {}
    for command in inventory["commands"]:
        for option in command["options"]:
            if option["classification"] != "generated_token":
                continue
            for profile in ("default_profile", "posix_profile"):
                resolution = option["profile_parser_resolution"][profile]
                target_id = resolution.get("target")
                target_name = (
                    options_by_id[target_id]["canonical_name"] if target_id else None
                )
                request_id = f"{option['id']}:{profile}"
                requests.append(
                    {
                        "id": request_id,
                        "command": command["name"],
                        "token": option["canonical_name"],
                        "target_name": target_name,
                        "posix": profile == "posix_profile",
                    }
                )
                expectations[request_id] = {
                    "token": option["canonical_name"],
                    "acceptance": resolution["acceptance"],
                    "target_name": target_name,
                    "profile": profile,
                }
    if len(requests) != 82:
        raise RuntimeError(
            f"generated-token Oracle probe count mismatch: expected 82, found {len(requests)}"
        )

    container_script = """
import json
import os
import subprocess
import sys

def execute(command, option, posix):
    env = os.environ.copy()
    if posix:
        env["POSIXLY_CORRECT"] = "1"
    else:
        env.pop("POSIXLY_CORRECT", None)
    completed = subprocess.run(
        [command, option, "__ferricov_parser_probe_value__"],
        check=False,
        capture_output=True,
        env=env,
        timeout=10,
    )
    return {
        "status": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", errors="replace"),
        "stderr": completed.stderr.decode("utf-8", errors="replace"),
    }

results = []
for request in json.loads(sys.argv[1]):
    results.append({
        "id": request["id"],
        "observed": execute(request["command"], request["token"], request["posix"]),
        "target": (
            execute(request["command"], request["target_name"], request["posix"])
            if request["target_name"] is not None
            else None
        ),
    })
print(json.dumps(results, sort_keys=True))
"""
    container = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            oracle_image,
            "python3",
            "-c",
            container_script,
            json.dumps(requests, separators=(",", ":"), sort_keys=True),
        ],
        check=False,
        capture_output=True,
        timeout=120,
    )
    if container.returncode != 0:
        raise RuntimeError(
            f"generated-token Oracle probe container failed: "
            f"stdout={container.stdout!r} stderr={container.stderr!r}"
        )
    results = json.loads(container.stdout)
    if [result["id"] for result in results] != [request["id"] for request in requests]:
        raise RuntimeError("generated-token Oracle probe result identity/order drift")

    actual_counts = {
        profile: {
            "accepted_unique_abbreviation": 0,
            "rejected_ambiguous": 0,
            "rejected_unknown": 0,
        }
        for profile in ("default_profile", "posix_profile")
    }

    def normalize_option_spelling(text: str, token: str, target: str) -> str:
        for spelling in sorted((token, target), key=len, reverse=True):
            text = text.replace(spelling, "<option>")
        for spelling in sorted(
            (token.lstrip("-"), target.lstrip("-")), key=len, reverse=True
        ):
            text = text.replace(f"Option {spelling}", "Option <option>")
            text = text.replace(f"option: {spelling}", "option: <option>")
        return text

    for result in results:
        expected = expectations[result["id"]]
        observed = result["observed"]
        combined = observed["stdout"] + observed["stderr"]
        bare_token = expected["token"].lstrip("-")
        if (
            observed["status"] == 1
            and f"Option {bare_token} is ambiguous" in combined
        ) or (
            observed["status"] == 2
            and f"ambiguous option: {expected['token']}" in combined
        ):
            actual = "rejected_ambiguous"
        elif (
            observed["status"] == 1
            and f"Unknown option: {bare_token}" in combined
        ) or (
            observed["status"] == 2
            and f"unrecognized arguments: {expected['token']}" in combined
        ):
            actual = "rejected_unknown"
        elif expected["target_name"] is not None:
            target = result["target"]
            normalized_observed = {
                "status": observed["status"],
                "stdout": normalize_option_spelling(
                    observed["stdout"], expected["token"], expected["target_name"]
                ),
                "stderr": normalize_option_spelling(
                    observed["stderr"], expected["token"], expected["target_name"]
                ),
            }
            normalized_target = {
                "status": target["status"],
                "stdout": normalize_option_spelling(
                    target["stdout"], expected["token"], expected["target_name"]
                ),
                "stderr": normalize_option_spelling(
                    target["stderr"], expected["token"], expected["target_name"]
                ),
            }
            if normalized_observed != normalized_target:
                raise RuntimeError(
                    f"accepted generated-token target semantics mismatch for "
                    f"{result['id']}: observed={observed!r} target={target!r}"
                )
            actual = "accepted_unique_abbreviation"
        else:
            raise RuntimeError(
                f"could not classify generated-token Oracle result for {result['id']}: "
                f"status={observed['status']} output={combined!r}"
            )
        if actual != expected["acceptance"]:
            raise RuntimeError(
                f"generated-token Oracle resolution mismatch for {result['id']}: "
                f"expected {expected['acceptance']}, found {actual}; output={combined!r}"
            )
        actual_counts[expected["profile"]][actual] += 1
    print(
        "ORACLE_PROFILE_PARSER_RESOLUTIONS_OK "
        f"probes={len(results)} "
        f"default_accepted={actual_counts['default_profile']['accepted_unique_abbreviation']} "
        f"default_ambiguous={actual_counts['default_profile']['rejected_ambiguous']} "
        f"default_unknown={actual_counts['default_profile']['rejected_unknown']} "
        f"posix_unknown={actual_counts['posix_profile']['rejected_unknown']} network=none"
    )


def run(
    command: list[str], cwd: Path, *, environment: dict[str, str] | None = None
) -> None:
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def resolve_upstream_root(root: Path, *, allow_clone: bool) -> Path:
    """Return a usable LCOV v2.5 source tree for fixture byte-pin checks.

    Prefer an explicit LCOV_SOURCE_ROOT, then the sibling workspace checkout,
    then (when Oracle work is enabled) a temporary shallow clone of v2.5.
    """
    candidates: list[Path] = []
    env_root = os.environ.get("LCOV_SOURCE_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    candidates.append(root.parent / "lcov-upstream-reference")
    for candidate in candidates:
        marker = candidate / "tests/lcov/format/format.info"
        if marker.is_file():
            return candidate.resolve()
    if not allow_clone:
        raise RuntimeError(
            "missing pinned LCOV upstream tree; set LCOV_SOURCE_ROOT to a v2.5 "
            "checkout containing tests/lcov/format/format.info"
        )
    directory = Path(tempfile.mkdtemp(prefix="ferricov-upstream-"))
    subprocess.run(
        [
            "git",
            "clone",
            "--branch",
            "v2.5",
            "--depth",
            "1",
            "https://github.com/linux-test-project/lcov.git",
            str(directory),
        ],
        check=True,
    )
    return directory.resolve()



def oracle_build_environment(
    base: dict[str, str], upstream_root: Path, manifest_path: Path
) -> dict[str, str]:
    return {
        **base,
        "LCOV_SOURCE_ROOT": str(upstream_root),
        "ORACLE_MANIFEST": str(manifest_path),
    }


def load_oracle_image_id(manifest_path: Path) -> str:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image = manifest.get("image", {})
    image_id = image.get("docker_image_id")
    if (
        not isinstance(image_id, str)
        or len(image_id) != 71
        or not image_id.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in image_id[7:])
    ):
        raise RuntimeError(f"invalid Oracle image ID in manifest: {manifest_path}")
    if image.get("reference") != image_id:
        raise RuntimeError(f"Oracle manifest image reference mismatch: {manifest_path}")
    return image_id


def inventory_regeneration_command(
    root: Path, upstream_root: Path, help_dir: Path, output_path: Path
) -> list[str]:
    return [
        "cargo",
        "run",
        "--locked",
        "-p",
        "ferricov-oracle",
        "--bin",
        "inventory",
        "--",
        str(upstream_root),
        str(help_dir),
        str(root / "compat/inventory/review"),
        str(output_path),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, action="append", default=[])
    parser.add_argument("--skip-oracle", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    # Fixture pin checks (TF-030 format-atoms) need the pinned upstream tree
    # before any Oracle image build. Resolve early so hosted CI Oracle Evidence
    # does not depend on a sibling workspace checkout.
    upstream_root_for_fixtures = resolve_upstream_root(
        root, allow_clone=not args.skip_oracle
    )
    os.environ["LCOV_SOURCE_ROOT"] = str(upstream_root_for_fixtures)
    fixture_env = dict(os.environ)
    run(
        [sys.executable, str(root / "compat/cases/m0-cli-contract.py")],
        root,
    )
    run(
        [sys.executable, str(root / "compat/cases/m0_config_contract.py")],
        root,
    )
    run(
        [sys.executable, str(root / "compat/cases/m0_genhtml_cli_residual_contract.py")],
        root,
    )
    run(
        [sys.executable, str(root / "compat/correctness/m0_contract.py")],
        root,
    )
    validate_documents(
        root / "compat/schema/inventory.schema.json",
        [root / "compat/inventory/v2.5.json"],
    )
    validate_inventory_semantics(root / "compat/inventory/v2.5.json")
    validate_m0_status_snapshot(root)
    validate_documents(
        root / "compat/schema/environment-contract.schema.json",
        [root / "compat/environment/v2.5.json"],
    )
    validate_documents(
        root / "compat/schema/tracefile-contract.schema.json",
        [root / "compat/tracefile/v2.5.json"],
    )
    validate_documents(
        root / "compat/schema/diagnostics-contract.schema.json",
        [root / "compat/diagnostics/v2.5.json"],
    )
    validate_documents(
        root / "compat/schema/installation-contract.schema.json",
        [root / "compat/installation/v2.5.json"],
    )
    validate_documents(
        root / "compat/schema/resource-contract.schema.json",
        [root / "compat/resources/v2.5.json"],
    )
    validate_documents(
        root / "compat/schema/resource-result.schema.json",
        [root / "compat/resources/results/oracle-x86_64-linux-20260729/result.json"],
    )
    validate_documents(
        root / "compat/schema/model-contract.schema.json",
        [root / "compat/model/v2.5.json"],
    )
    validate_documents(
        root / "compat/schema/upstream-test-map.schema.json",
        [root / "compat/inventory/tests/upstream-test-map.json"],
    )
    validate_documents(
        root / "compat/schema/suite.schema.json",
        sorted((root / "compat/cases").glob("*.json")),
    )
    validate_documents(
        root / "compat/schema/launcher.schema.json",
        sorted((root / "compat/launchers").glob("*.json")),
    )
    result_documents = []
    for result_root in args.results:
        documents = sorted(result_root.rglob("result.json"))
        if not documents:
            raise RuntimeError(f"no result.json evidence under {result_root}")
        result_documents.extend(documents)
    validate_documents(
        root / "compat/schema/differential-result.schema.json",
        sorted(result_documents),
    )
    run(
        [sys.executable, str(root / "compat/correctness/validate.py")],
        root,
    )
    run(
        [sys.executable, str(root / "compat/fixtures/m0-tracefiles/validate.py")],
        root,
        environment=fixture_env,
    )
    run(
        [
            sys.executable,
            "-m",
            "unittest",
            str(root / "compat/fixtures/m0-tracefiles/test_validate.py"),
        ],
        root,
        environment=fixture_env,
    )
    run(
        [sys.executable, str(root / "compat/resources/contract.py")],
        root,
    )
    run(
        [
            sys.executable,
            str(root / "compat/resources/validate.py"),
            "--result",
            str(root / "compat/resources/results/oracle-x86_64-linux-20260729/result.json"),
        ],
        root,
    )
    run(
        [sys.executable, str(root / "compat/model/contract.py")],
        root,
    )
    run(
        [
            sys.executable,
            "-m",
            "unittest",
            str(root / "compat/model/test_contract.py"),
        ],
        root,
    )
    run(
        [sys.executable, str(root / "compat/fixtures/m0-algebra/validate.py")],
        root,
    )
    run(
        [
            sys.executable,
            "-m",
            "unittest",
            str(root / "compat/fixtures/m0-algebra/test_validate.py"),
        ],
        root,
    )

    if args.skip_oracle:
        return 0

    with tempfile.TemporaryDirectory(prefix="ferricov-help-") as directory:
        generated_help = Path(directory)
        upstream_root = generated_help / "upstream"
        oracle_manifest = generated_help / "oracle-manifest.json"
        run(
            [
                "git",
                "clone",
                "--branch",
                "v2.5",
                "--depth",
                "1",
                "https://github.com/linux-test-project/lcov.git",
                str(upstream_root),
            ],
            root,
        )
        validate_inventory_sources(root, upstream_root)
        run(
            [
                sys.executable,
                str(root / "compat/environment/contract.py"),
                "--upstream-root",
                str(upstream_root),
            ],
            root,
        )
        run(
            [
                sys.executable,
                str(root / "compat/tracefile/contract.py"),
                "--upstream-root",
                str(upstream_root),
            ],
            root,
        )
        run(
            [
                sys.executable,
                str(root / "compat/diagnostics/contract.py"),
                "--upstream-root",
                str(upstream_root),
            ],
            root,
        )
        run(
            [
                sys.executable,
                str(root / "compat/installation/contract.py"),
                "--upstream-root",
                str(upstream_root),
            ],
            root,
        )
        run(
            [
                sys.executable,
                str(root / "compat/inventory/tests/validate.py"),
                "--upstream-root",
                str(upstream_root),
            ],
            root,
        )
        run(
            [str(root / "compat/upstream/build.sh")],
            root,
            environment=oracle_build_environment(
                dict(os.environ), upstream_root, oracle_manifest
            ),
        )
        oracle_image = load_oracle_image_id(oracle_manifest)
        run_oracle_parser_probes(oracle_image)
        run_profile_parser_resolution_probes(
            root / "compat/inventory/v2.5.json", oracle_image
        )

        commands = json.loads((root / "compat/inventory/v2.5.json").read_text())["commands"]
        for command in commands:
            output = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    oracle_image,
                    command["name"],
                    "--help",
                ],
                check=True,
                capture_output=True,
            )
            (generated_help / f"{command['name']}.txt").write_bytes(output.stdout)
            committed = root / "compat/upstream/help" / f"{command['name']}.txt"
            if output.stdout != committed.read_bytes():
                raise RuntimeError(f"help snapshot drift: {command['name']}")

        inventory = generated_help / "inventory.json"
        run(
            inventory_regeneration_command(
                root, upstream_root, generated_help, inventory
            ),
            root,
        )
        committed_inventory = root / "compat/inventory/v2.5.json"
        if sha256(inventory) != sha256(committed_inventory):
            raise RuntimeError("inventory regeneration is not byte-stable")
        print(f"INVENTORY_OK sha256={sha256(inventory)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
