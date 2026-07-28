#!/usr/bin/env python3
"""Generate and validate the static M0 command-line contract suites."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = ROOT / "compat/cases"
FIXTURE_ROOT = ROOT / "compat/fixtures/m0-cli-contract"
INVENTORY_PATH = ROOT / "compat/inventory/v2.5.json"
SUITE_SCHEMA_PATH = ROOT / "compat/schema/suite.schema.json"
CASE_CONTRACT_PATH = FIXTURE_ROOT / "case-contract.json"
POLICY_EQUIVALENCE_PATH = FIXTURE_ROOT / "policy-equivalence.md"
BASELINE_STATUS_PATH = FIXTURE_ROOT / "oracle-baseline-status.json"

ORACLE_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
RETIRED_IMAGE_IDENTITY = (
    "sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e"
)
RETIRED_BASELINE_PATHS = (
    FIXTURE_ROOT / "oracle-baseline-manifest.json",
    FIXTURE_ROOT / "oracle-baseline-core.json",
    FIXTURE_ROOT / "oracle-baseline-policy.json",
    FIXTURE_ROOT / "oracle-baseline-posix.json",
)

CORE_SUITE = "m0-cli-contract-core"
POLICY_SUITE = "m0-cli-contract-policy"
POSIX_SUITE = "m0-cli-contract-posix"
SUITE_IDS = (CORE_SUITE, POLICY_SUITE, POSIX_SUITE)

COMMANDS = (
    "lcov",
    "genhtml",
    "geninfo",
    "genpng",
    "gendesc",
    "perl2lcov",
    "py2lcov",
    "xml2lcov",
    "xml2lcovutil.py",
    "llvm2lcov",
)
SHARED_GETOPT_COMMANDS = ("lcov", "genhtml", "geninfo", "perl2lcov", "llvm2lcov")

FAMILY_EQUIVALENCE_IDS = {
    "shared_getopt_long": "parser-policy.shared-getopt-long",
    "direct_getopt_long": "parser-policy.direct-getopt-long",
    "argparse": "parser-policy.argparse",
    "none": "parser-policy.none",
}

# The raw baseline executor must start from this exact environment instead of
# inheriting arbitrary host/container variables. {workdir} is resolved per case.
CLEAN_ENVIRONMENT_ALLOWLIST = {
    "HOME": "{workdir}",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "TZ": "UTC",
}
SUITE_ENVIRONMENT_OVERRIDES = {
    CORE_SUITE: {},
    POLICY_SUITE: {},
    POSIX_SUITE: {"POSIXLY_CORRECT": "1"},
}

# Full-command review distinguishes parser-declared aliases from Getopt's
# default one-letter abbreviation. The inventory aliases field intentionally
# preserves both and therefore cannot be used directly for resolution proof.
REVIEWED_EXPLICIT_ALIASES = {
    "lcov": {"-h": "--help", "-?": "--help", "-q": "--quiet", "-v": "--verbose"},
    "genhtml": {"-h": "--help", "-?": "--help", "-q": "--quiet", "-v": "--verbose"},
    "geninfo": {"-h": "--help", "-?": "--help", "-q": "--quiet", "-v": "--verbose"},
    "genpng": {},
    "gendesc": {"-?": "--help"},
    "perl2lcov": {"-h": "--help", "-?": "--help", "-q": "--quiet", "-v": "--verbose"},
    "py2lcov": {"-h": "--help", "-v": "--verbose", "-k": "--keep-going"},
    "xml2lcov": {"-h": "--help", "-v": "--verbose", "-k": "--keep-going"},
    "xml2lcovutil.py": {},
    "llvm2lcov": {"-h": "--help", "-?": "--help", "-q": "--quiet", "-v": "--verbose"},
}
PROBE_VALUE_OPTIONS = {"--config-file", "--rc", "--version-script"}

CONFIG_FIXTURE = "compat/fixtures/m0-cli-contract/config"
PLUS_FIXTURE = "compat/fixtures/m0-cli-contract/plus-positional"
ARGPARSE_FIXTURE = "compat/fixtures/m0-cli-contract/argparse-cluster"


class ContractError(RuntimeError):
    """The generated CLI contract is incomplete or internally inconsistent."""


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, ensure_ascii=True) + "\n"


def canonical_hash(document: object) -> str:
    encoded = (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def option_id(command: str, name: str) -> str:
    return f"command.{command}.option.{name}"


def positional_id(command: str, name: str) -> str:
    return f"command.{command}.positional.{name}"


def comparisons() -> list[dict[str, str]]:
    return [
        {"dimension": dimension, "normalizer": "exact-v1"}
        for dimension in ("exit", "stdout", "stderr", "filesystem")
    ]


def suite_document(suite_id: str, cases: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "suite_id": suite_id,
        "evidence_scope": "compatibility",
        "cases": cases,
    }


def parser_policy_signature(command: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in command["parser_policy"].items()
        if key != "source_references"
    }


def parser_option_definitions(command: dict[str, object]) -> list[dict[str, object]]:
    return [
        option
        for option in command["options"]
        if any(
            reference["kind"] == "parser_definition"
            for reference in option["source_references"]
        )
    ]


def case_resolution_signature(
    command: dict[str, object], arguments: list[str], profile: str
) -> list[dict[str, object]]:
    """Resolve option-shaped tokens using only the committed parser inventory."""
    policy = parser_policy_signature(command)
    family = policy["family"]
    options = parser_option_definitions(command)
    canonical = {
        option["canonical_name"].removeprefix("--"): option["canonical_name"]
        for option in options
    }
    aliases = REVIEWED_EXPLICIT_ALIASES[command["name"]]
    positionals = bool(command["positional_arguments"])

    def positional(token: str) -> dict[str, object]:
        return {"token": token, "resolution": "positional", "positionals_defined": positionals}

    signature = []
    pending_value_for: str | None = None
    getopt_stopped = False
    argparse_positional_seen = False
    argparse_option_after_positional = False

    def append(record: dict[str, object]) -> None:
        nonlocal pending_value_for
        signature.append(record)
        targets = record.get("targets")
        if targets is None and record.get("target") is not None:
            targets = [record["target"]]
        if (
            record["resolution"]
            in {"exact", "exact_alias", "unique_prefix", "exact_only_prefix_rejected"}
            and isinstance(targets, list)
            and len(targets) == 1
            and targets[0] in PROBE_VALUE_OPTIONS
        ):
            pending_value_for = targets[0]

    for token in arguments:
        if pending_value_for is not None:
            signature.append(
                {
                    "token": token,
                    "resolution": "option_value",
                    "option": pending_value_for,
                }
            )
            pending_value_for = None
            continue
        if family in {"shared_getopt_long", "direct_getopt_long"} and getopt_stopped:
            append({"token": token, "resolution": "unparsed_after_require_order"})
            continue
        if family == "none":
            append({"token": token, "resolution": "ignored"})
            continue
        if not token.startswith(("-", "+")) or token == "-":
            if family == "argparse" and argparse_option_after_positional:
                append({"token": token, "resolution": "rejected_after_option_boundary"})
            else:
                append(positional(token))
                if family == "argparse":
                    argparse_positional_seen = True
                elif profile == "posixly_correct":
                    getopt_stopped = True
            continue

        if family == "argparse":
            if token.startswith("+"):
                append(positional(token))
                argparse_positional_seen = True
                continue
            if argparse_positional_seen:
                argparse_option_after_positional = True
            if token in aliases:
                append(
                    {"token": token, "resolution": "exact_alias", "target": aliases[token]}
                )
                continue
            if token.startswith("--"):
                body = token[2:]
                if body in canonical:
                    targets = [canonical[body]]
                    resolution = "exact"
                else:
                    targets = sorted(
                        name for spelling, name in canonical.items() if spelling.startswith(body)
                    )
                    resolution = (
                        "unique_prefix"
                        if len(targets) == 1
                        else "ambiguous_prefix" if targets else "unknown"
                    )
                append(
                    {"token": token, "resolution": resolution, "targets": targets}
                )
                continue
            bundle_targets = [aliases.get(f"-{character}") for character in token[1:]]
            if all(bundle_targets):
                append(
                    {
                        "token": token,
                        "resolution": "short_cluster",
                        "targets": bundle_targets,
                    }
                )
            else:
                append({"token": token, "resolution": "unknown"})
            continue

        posix = profile == "posixly_correct"
        if token.startswith("+") and posix:
            append(positional(token))
            getopt_stopped = True
            continue
        folded_token = token.lower()
        folded_aliases = {alias.lower(): target for alias, target in aliases.items()}
        if folded_token in folded_aliases:
            append(
                {
                    "token": token,
                    "resolution": "exact_alias",
                    "target": folded_aliases[folded_token],
                }
            )
            continue
        if token.startswith("--"):
            body = token[2:]
        elif token.startswith(("-", "+")):
            body = token[1:]
        else:
            append(positional(token))
            continue
        body = body.lower()
        folded_canonical = {name.lower(): target for name, target in canonical.items()}
        if body in folded_canonical:
            append(
                {
                    "token": token,
                    "resolution": "exact",
                    "targets": [folded_canonical[body]],
                }
            )
            continue
        targets = sorted(
            target for spelling, target in folded_canonical.items() if spelling.startswith(body)
        )
        if posix:
            record: dict[str, object] = {
                "token": token,
                "resolution": "unknown",
                "targets": [],
            }
            if token.startswith("-") and not token.startswith("--") and len(token) > 2:
                bundle_targets = [
                    folded_aliases.get(f"-{character.lower()}") for character in token[1:]
                ]
                if all(bundle_targets):
                    record["bundling_reverse_targets"] = bundle_targets
            append(record)
            continue
        exact_only_targets = set(policy["exact_only_options"])
        if len(targets) == 1 and targets[0] in exact_only_targets:
            append(
                {
                    "token": token,
                    "resolution": "exact_only_prefix_rejected",
                    "targets": targets,
                }
            )
            continue
        record = {
            "token": token,
            "resolution": (
                "unique_prefix"
                if len(targets) == 1
                else "ambiguous_prefix" if targets else "unknown"
            ),
            "targets": targets,
        }
        if token.startswith("-") and not token.startswith("--") and len(token) > 2:
            bundle_targets = [
                folded_aliases.get(f"-{character.lower()}") for character in token[1:]
            ]
            if all(bundle_targets):
                record["bundling_reverse_targets"] = bundle_targets
        append(record)
    if pending_value_for is not None:
        signature[-1]["missing_value"] = True
    return signature


def inventory_maps(
    inventory: dict[str, object],
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    dict[str, str],
]:
    commands = {command["name"]: command for command in inventory["commands"]}
    entries: dict[str, dict[str, object]] = {}
    families = {}
    for command in inventory["commands"]:
        families[command["name"]] = command["parser_policy"]["family"]
        for entry in (*command["options"], *command["positional_arguments"]):
            if entry["id"] in entries:
                raise ContractError(f"duplicate inventory entry ID: {entry['id']}")
            entries[entry["id"]] = entry
    return commands, entries, families


def build_family_equivalence(
    inventory: dict[str, object],
) -> list[dict[str, object]]:
    commands, _, _ = inventory_maps(inventory)
    partitions = []
    for family, equivalence_id in FAMILY_EQUIVALENCE_IDS.items():
        family_commands = [
            command
            for command in COMMANDS
            if commands[command]["parser_policy"]["family"] == family
        ]
        signatures = [parser_policy_signature(commands[command]) for command in family_commands]
        if not signatures or any(signature != signatures[0] for signature in signatures[1:]):
            raise ContractError(f"parser policy family is not equivalent: {family}")
        partitions.append(
            {
                "id": equivalence_id,
                "family": family,
                "commands": family_commands,
                "policy_sha256": canonical_hash(signatures[0]),
                "policy": signatures[0],
            }
        )
    return partitions


def build_suites_and_links(
    inventory: dict[str, object],
) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    commands, _, families = inventory_maps(inventory)
    cases_by_suite: dict[str, list[dict[str, object]]] = {
        suite_id: [] for suite_id in SUITE_IDS
    }
    links: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    def add(
        suite_id: str,
        case_id: str,
        command: str,
        arguments: list[str],
        *,
        fixture: str | None = None,
        inventory_entries: tuple[str, ...] = (),
        family_equivalence: str | None = None,
        policy_expectations: dict[str, object] | None = None,
    ) -> None:
        if case_id in seen_ids:
            raise ContractError(f"duplicate generated case ID: {case_id}")
        seen_ids.add(case_id)
        cases_by_suite[suite_id].append(
            {
                "id": case_id,
                "surface": "cli",
                "command": command,
                "arguments": arguments,
                "fixture": fixture,
                "comparisons": comparisons(),
            }
        )
        links.append(
            {
                "case_id": case_id,
                "suite_id": suite_id,
                "command": command,
                "inventory_entries": list(inventory_entries),
                "family_equivalence": family_equivalence,
                "policy_expectations": policy_expectations or {},
            }
        )

    def family_id(command: str) -> str:
        return FAMILY_EQUIVALENCE_IDS[families[command]]

    # Per-command controls remain independent. Option-bearing controls link to
    # exact reviewed inventory entries; startup/invalid/no-parser controls bind
    # to the exact machine-verified parser-policy partition.
    for command in COMMANDS:
        slug = command.replace(".", "-")
        equivalence = family_id(command)
        add(
            CORE_SUITE,
            f"m0-core-{slug}-startup-control",
            command,
            [],
            family_equivalence=equivalence,
        )
        if command == "xml2lcovutil.py":
            add(
                CORE_SUITE,
                "m0-core-xml2lcovutil-py-help-argv-ignored-control",
                command,
                ["--help"],
                family_equivalence=equivalence,
            )
            add(
                CORE_SUITE,
                "m0-core-xml2lcovutil-py-version-argv-ignored-control",
                command,
                ["--version"],
                family_equivalence=equivalence,
            )
            add(
                CORE_SUITE,
                "m0-core-xml2lcovutil-py-invalid-argv-ignored-control",
                command,
                ["--ferricov-invalid-option"],
                family_equivalence=equivalence,
            )
            continue

        add(
            CORE_SUITE,
            f"m0-core-{slug}-help",
            command,
            ["--help"],
            inventory_entries=(option_id(command, "help"),),
        )
        if command in {"py2lcov", "xml2lcov"}:
            add(
                CORE_SUITE,
                f"m0-core-{slug}-version-script-abbreviation",
                command,
                ["--version"],
                inventory_entries=(option_id(command, "version-script"),),
                family_equivalence=equivalence,
                policy_expectations={"auto_abbrev": "unique_prefix"},
            )
        else:
            add(
                CORE_SUITE,
                f"m0-core-{slug}-version",
                command,
                ["--version"],
                inventory_entries=(option_id(command, "version"),),
            )
        add(
            CORE_SUITE,
            f"m0-core-{slug}-invalid-option",
            command,
            ["--ferricov-invalid-option"],
            family_equivalence=equivalence,
        )

    shared = FAMILY_EQUIVALENCE_IDS["shared_getopt_long"]
    direct = FAMILY_EQUIVALENCE_IDS["direct_getopt_long"]
    argparse_family = FAMILY_EQUIVALENCE_IDS["argparse"]
    no_parser = FAMILY_EQUIVALENCE_IDS["none"]

    def policy(
        name: str,
        command: str,
        arguments: list[str],
        **kwargs: object,
    ) -> None:
        add(POLICY_SUITE, f"m0-policy-{name}", command, arguments, **kwargs)

    policy(
        "shared-unique-abbreviation",
        "lcov",
        ["--hel"],
        inventory_entries=(option_id("lcov", "help"),),
        family_equivalence=shared,
        policy_expectations={"auto_abbrev": "unique_prefix"},
    )
    policy(
        "shared-ambiguous-abbreviation",
        "lcov",
        ["--ver"],
        inventory_entries=(
            option_id("lcov", "verbose"),
            option_id("lcov", "version"),
            option_id("lcov", "version-script"),
        ),
        family_equivalence=shared,
        policy_expectations={"auto_abbrev": "unique_prefix"},
    )
    policy(
        "shared-case-insensitive",
        "lcov",
        ["--HELP"],
        inventory_entries=(option_id("lcov", "help"),),
        family_equivalence=shared,
        policy_expectations={"case_sensitive": False},
    )
    policy(
        "shared-single-dash-long",
        "lcov",
        ["-help"],
        inventory_entries=(option_id("lcov", "help"),),
        family_equivalence=shared,
        policy_expectations={"accepted_long_prefixes": ["--", "-"]},
    )
    policy(
        "shared-plus-prefix",
        "lcov",
        ["+help"],
        inventory_entries=(option_id("lcov", "help"),),
        family_equivalence=shared,
        policy_expectations={"plus_prefix_behavior": "option"},
    )
    policy(
        "shared-no-bundling",
        "lcov",
        ["-qv"],
        inventory_entries=(option_id("lcov", "quiet"), option_id("lcov", "verbose")),
        family_equivalence=shared,
        policy_expectations={"bundling": "disabled"},
    )
    policy(
        "shared-permute",
        "lcov",
        ["operand", "--help"],
        inventory_entries=(
            positional_id("lcov", "operation-operands"),
            option_id("lcov", "help"),
        ),
        family_equivalence=shared,
        policy_expectations={"option_ordering": "permute"},
    )
    policy(
        "shared-converter-abbreviation",
        "llvm2lcov",
        ["--hel"],
        inventory_entries=(option_id("llvm2lcov", "help"),),
        family_equivalence=shared,
        policy_expectations={"auto_abbrev": "unique_prefix"},
    )

    policy(
        "direct-unique-abbreviation",
        "gendesc",
        ["--hel"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations={"auto_abbrev": "unique_prefix"},
    )
    policy(
        "direct-version-abbreviation",
        "genpng",
        ["--ver"],
        inventory_entries=(option_id("genpng", "version"),),
        family_equivalence=direct,
        policy_expectations={"auto_abbrev": "unique_prefix"},
    )
    policy(
        "direct-case-insensitive",
        "gendesc",
        ["--HELP"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations={"case_sensitive": False},
    )
    policy(
        "direct-single-dash-long",
        "gendesc",
        ["-help"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations={"accepted_long_prefixes": ["--", "-"]},
    )
    policy(
        "direct-plus-prefix",
        "gendesc",
        ["+help"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations={"plus_prefix_behavior": "option"},
    )
    policy(
        "direct-no-bundling",
        "gendesc",
        ["-??"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations={"bundling": "disabled"},
    )
    policy(
        "direct-permute",
        "gendesc",
        ["operand", "--help"],
        inventory_entries=(
            positional_id("gendesc", "inputfile"),
            option_id("gendesc", "help"),
        ),
        family_equivalence=direct,
        policy_expectations={"option_ordering": "permute"},
    )

    # Argparse mechanics are observed through conversion/error paths. None of
    # these probes resolves to --help, which would hide the downstream parse.
    policy(
        "argparse-unique-abbreviation",
        "py2lcov",
        ["--verb", "input.xml"],
        fixture=ARGPARSE_FIXTURE,
        inventory_entries=(
            option_id("py2lcov", "verbose"),
            positional_id("py2lcov", "inputs"),
        ),
        family_equivalence=argparse_family,
        policy_expectations={"auto_abbrev": "unique_prefix"},
    )
    policy(
        "argparse-ambiguous-abbreviation",
        "py2lcov",
        ["--ver", "input.xml"],
        fixture=ARGPARSE_FIXTURE,
        inventory_entries=(
            option_id("py2lcov", "verbose"),
            option_id("py2lcov", "version-script"),
            positional_id("py2lcov", "inputs"),
        ),
        family_equivalence=argparse_family,
        policy_expectations={"auto_abbrev": "unique_prefix"},
    )
    policy(
        "argparse-case-sensitive",
        "py2lcov",
        ["--VERB", "input.xml"],
        fixture=ARGPARSE_FIXTURE,
        inventory_entries=(
            option_id("py2lcov", "verbose"),
            positional_id("py2lcov", "inputs"),
        ),
        family_equivalence=argparse_family,
        policy_expectations={"case_sensitive": True},
    )
    policy(
        "argparse-rejects-single-dash-long",
        "py2lcov",
        ["-checksum", "input.xml"],
        fixture=ARGPARSE_FIXTURE,
        inventory_entries=(
            option_id("py2lcov", "checksum"),
            positional_id("py2lcov", "inputs"),
        ),
        family_equivalence=argparse_family,
        policy_expectations={"accepted_long_prefixes": ["--"]},
    )
    policy(
        "argparse-plus-is-positional",
        "xml2lcov",
        ["+help"],
        fixture=PLUS_FIXTURE,
        inventory_entries=(positional_id("xml2lcov", "inputs"),),
        family_equivalence=argparse_family,
        policy_expectations={"plus_prefix_behavior": "positional"},
    )
    policy(
        "argparse-short-option-cluster",
        "py2lcov",
        ["-vk", "input.xml"],
        fixture=ARGPARSE_FIXTURE,
        inventory_entries=(
            option_id("py2lcov", "verbose"),
            option_id("py2lcov", "keep-going"),
            positional_id("py2lcov", "inputs"),
        ),
        family_equivalence=argparse_family,
        policy_expectations={"bundling": "argparse_short_clusters"},
    )
    policy(
        "argparse-parse-args-boundary",
        "py2lcov",
        ["first.xml", "--no", "later.xml"],
        inventory_entries=(
            option_id("py2lcov", "no-functions"),
            positional_id("py2lcov", "inputs"),
        ),
        family_equivalence=argparse_family,
        policy_expectations={"option_ordering": "argparse_parse_args"},
    )
    policy(
        "argparse-xml-unique-abbreviation",
        "xml2lcov",
        ["--verb", "input.xml"],
        fixture=ARGPARSE_FIXTURE,
        inventory_entries=(
            option_id("xml2lcov", "verbose"),
            positional_id("xml2lcov", "inputs"),
        ),
        family_equivalence=argparse_family,
        policy_expectations={"auto_abbrev": "unique_prefix"},
    )
    policy(
        "no-parser-mixed-argv-ignored-control",
        "xml2lcovutil.py",
        ["+help", "-help", "--HELP", "operand"],
        family_equivalence=no_parser,
    )

    exact_expectation = {"exact_only_options": ["--config-file", "--rc"]}
    for command in SHARED_GETOPT_COMMANDS:
        slug = command.replace(".", "-")
        policy(
            f"shared-{slug}-config-file-exact",
            command,
            ["--config-file", "empty.lcovrc", "--help"],
            fixture=CONFIG_FIXTURE,
            inventory_entries=(option_id(command, "config-file"), option_id(command, "help")),
            family_equivalence=shared,
            policy_expectations=exact_expectation,
        )
        policy(
            f"shared-{slug}-rc-exact",
            command,
            ["--rc", "branch_coverage=0", "--help"],
            inventory_entries=(option_id(command, "rc"), option_id(command, "help")),
            family_equivalence=shared,
            policy_expectations=exact_expectation,
        )
    policy(
        "shared-config-file-single-dash-exact",
        "lcov",
        ["-config-file", "empty.lcovrc", "--help"],
        fixture=CONFIG_FIXTURE,
        inventory_entries=(option_id("lcov", "config-file"), option_id("lcov", "help")),
        family_equivalence=shared,
        policy_expectations=exact_expectation,
    )
    policy(
        "shared-config-file-abbreviation-rejected",
        "lcov",
        ["--config-f", "empty.lcovrc", "--help"],
        fixture=CONFIG_FIXTURE,
        inventory_entries=(option_id("lcov", "config-file"), option_id("lcov", "help")),
        family_equivalence=shared,
        policy_expectations=exact_expectation,
    )
    policy(
        "shared-rc-case-insensitive-exact",
        "lcov",
        ["--RC", "branch_coverage=0", "--help"],
        inventory_entries=(option_id("lcov", "rc"), option_id("lcov", "help")),
        family_equivalence=shared,
        policy_expectations={
            "case_sensitive": False,
            "exact_only_options": ["--config-file", "--rc"],
        },
    )

    # Every explicit help alias is identity-bound to its exact inventory entry.
    for command in inventory["commands"]:
        help_option = next(
            (
                option
                for option in command["options"]
                if option["canonical_name"] == "--help"
            ),
            None,
        )
        if help_option is None:
            continue
        slug = command["name"].replace(".", "-")
        for alias in help_option["aliases"]:
            alias_slug = "question" if alias == "-?" else alias.lstrip("-")
            policy(
                f"help-alias-{slug}-{alias_slug}",
                command["name"],
                [alias],
                inventory_entries=(help_option["id"],),
            )

    def posix(
        name: str,
        command: str,
        arguments: list[str],
        **kwargs: object,
    ) -> None:
        add(POSIX_SUITE, f"m0-posix-{name}", command, arguments, **kwargs)

    posix_effect = {
        "posixly_correct_effect": "disable_auto_abbrev_and_plus_require_order"
    }
    posix(
        "shared-abbreviation-disabled",
        "lcov",
        ["--hel"],
        inventory_entries=(option_id("lcov", "help"),),
        family_equivalence=shared,
        policy_expectations=posix_effect,
    )
    posix(
        "shared-case-folding-preserved",
        "lcov",
        ["--HELP"],
        inventory_entries=(option_id("lcov", "help"),),
        family_equivalence=shared,
        policy_expectations={"case_sensitive": False, **posix_effect},
    )
    posix(
        "shared-single-dash-long-preserved",
        "lcov",
        ["-help"],
        inventory_entries=(option_id("lcov", "help"),),
        family_equivalence=shared,
        policy_expectations={"accepted_long_prefixes": ["--", "-"], **posix_effect},
    )
    posix(
        "shared-plus-prefix-disabled",
        "lcov",
        ["+help"],
        inventory_entries=(option_id("lcov", "help"),),
        family_equivalence=shared,
        policy_expectations=posix_effect,
    )
    posix(
        "shared-require-order",
        "lcov",
        ["operand", "--help"],
        inventory_entries=(
            positional_id("lcov", "operation-operands"),
            option_id("lcov", "help"),
        ),
        family_equivalence=shared,
        policy_expectations=posix_effect,
    )
    posix(
        "shared-no-bundling-preserved",
        "lcov",
        ["-qv"],
        inventory_entries=(option_id("lcov", "quiet"), option_id("lcov", "verbose")),
        family_equivalence=shared,
        policy_expectations={"bundling": "disabled", **posix_effect},
    )

    posix(
        "direct-abbreviation-disabled",
        "gendesc",
        ["--hel"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations=posix_effect,
    )
    posix(
        "direct-case-folding-preserved",
        "gendesc",
        ["--HELP"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations={"case_sensitive": False, **posix_effect},
    )
    posix(
        "direct-single-dash-long-preserved",
        "gendesc",
        ["-help"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations={"accepted_long_prefixes": ["--", "-"], **posix_effect},
    )
    posix(
        "direct-plus-prefix-disabled",
        "gendesc",
        ["+help"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations=posix_effect,
    )
    posix(
        "direct-no-bundling-preserved",
        "gendesc",
        ["-??"],
        inventory_entries=(option_id("gendesc", "help"),),
        family_equivalence=direct,
        policy_expectations={"bundling": "disabled", **posix_effect},
    )
    posix(
        "direct-require-order",
        "gendesc",
        ["operand", "--help"],
        inventory_entries=(
            positional_id("gendesc", "inputfile"),
            option_id("gendesc", "help"),
        ),
        family_equivalence=direct,
        policy_expectations=posix_effect,
    )

    argparse_posix_cases = (
        (
            "argparse-unique-abbreviation-unchanged",
            "py2lcov",
            ["--verb", "input.xml"],
            ARGPARSE_FIXTURE,
            (option_id("py2lcov", "verbose"), positional_id("py2lcov", "inputs")),
            {"auto_abbrev": "unique_prefix", "posixly_correct_effect": "none"},
        ),
        (
            "argparse-ambiguous-abbreviation-unchanged",
            "py2lcov",
            ["--ver", "input.xml"],
            ARGPARSE_FIXTURE,
            (
                option_id("py2lcov", "verbose"),
                option_id("py2lcov", "version-script"),
                positional_id("py2lcov", "inputs"),
            ),
            {"auto_abbrev": "unique_prefix", "posixly_correct_effect": "none"},
        ),
        (
            "argparse-case-sensitivity-unchanged",
            "py2lcov",
            ["--VERB", "input.xml"],
            ARGPARSE_FIXTURE,
            (option_id("py2lcov", "verbose"), positional_id("py2lcov", "inputs")),
            {"case_sensitive": True, "posixly_correct_effect": "none"},
        ),
        (
            "argparse-single-dash-long-rejection-unchanged",
            "py2lcov",
            ["-checksum", "input.xml"],
            ARGPARSE_FIXTURE,
            (option_id("py2lcov", "checksum"), positional_id("py2lcov", "inputs")),
            {"accepted_long_prefixes": ["--"], "posixly_correct_effect": "none"},
        ),
        (
            "argparse-plus-positional-unchanged",
            "xml2lcov",
            ["+help"],
            PLUS_FIXTURE,
            (positional_id("xml2lcov", "inputs"),),
            {"plus_prefix_behavior": "positional", "posixly_correct_effect": "none"},
        ),
        (
            "argparse-short-cluster-unchanged",
            "py2lcov",
            ["-vk", "input.xml"],
            ARGPARSE_FIXTURE,
            (
                option_id("py2lcov", "verbose"),
                option_id("py2lcov", "keep-going"),
                positional_id("py2lcov", "inputs"),
            ),
            {"bundling": "argparse_short_clusters", "posixly_correct_effect": "none"},
        ),
        (
            "argparse-order-boundary-unchanged",
            "py2lcov",
            ["first.xml", "--no", "later.xml"],
            None,
            (option_id("py2lcov", "no-functions"), positional_id("py2lcov", "inputs")),
            {"option_ordering": "argparse_parse_args", "posixly_correct_effect": "none"},
        ),
        (
            "argparse-xml-unique-abbreviation-unchanged",
            "xml2lcov",
            ["--verb", "input.xml"],
            ARGPARSE_FIXTURE,
            (option_id("xml2lcov", "verbose"), positional_id("xml2lcov", "inputs")),
            {"auto_abbrev": "unique_prefix", "posixly_correct_effect": "none"},
        ),
    )
    for name, command, arguments, fixture, entries, expectations in argparse_posix_cases:
        posix(
            name,
            command,
            arguments,
            fixture=fixture,
            inventory_entries=entries,
            family_equivalence=argparse_family,
            policy_expectations=expectations,
        )
    posix(
        "no-parser-mixed-argv-ignored-control",
        "xml2lcovutil.py",
        ["+help", "--hel", "operand", "--help"],
        family_equivalence=no_parser,
    )

    for command in SHARED_GETOPT_COMMANDS:
        slug = command.replace(".", "-")
        posix(
            f"shared-{slug}-config-file-exact",
            command,
            ["--config-file", "empty.lcovrc", "--help"],
            fixture=CONFIG_FIXTURE,
            inventory_entries=(option_id(command, "config-file"), option_id(command, "help")),
            family_equivalence=shared,
            policy_expectations={**exact_expectation, **posix_effect},
        )
        posix(
            f"shared-{slug}-rc-exact",
            command,
            ["--rc", "branch_coverage=0", "--help"],
            inventory_entries=(option_id(command, "rc"), option_id(command, "help")),
            family_equivalence=shared,
            policy_expectations={**exact_expectation, **posix_effect},
        )
    posix(
        "shared-config-file-single-dash-exact",
        "lcov",
        ["-config-file", "empty.lcovrc", "--help"],
        fixture=CONFIG_FIXTURE,
        inventory_entries=(option_id("lcov", "config-file"), option_id("lcov", "help")),
        family_equivalence=shared,
        policy_expectations={**exact_expectation, **posix_effect},
    )
    posix(
        "shared-config-file-abbreviation-rejected",
        "lcov",
        ["--config-f", "empty.lcovrc", "--help"],
        fixture=CONFIG_FIXTURE,
        inventory_entries=(option_id("lcov", "config-file"), option_id("lcov", "help")),
        family_equivalence=shared,
        policy_expectations={**exact_expectation, **posix_effect},
    )
    posix(
        "shared-rc-case-insensitive-exact",
        "lcov",
        ["--RC", "branch_coverage=0", "--help"],
        inventory_entries=(option_id("lcov", "rc"), option_id("lcov", "help")),
        family_equivalence=shared,
        policy_expectations={
            "case_sensitive": False,
            **exact_expectation,
            **posix_effect,
        },
    )

    suites = {
        suite_id: suite_document(suite_id, cases_by_suite[suite_id])
        for suite_id in SUITE_IDS
    }
    return suites, links


def build_case_contract(
    inventory: dict[str, object],
    suites: dict[str, dict[str, object]],
    links: list[dict[str, object]],
) -> dict[str, object]:
    commands, _, _ = inventory_maps(inventory)
    suite_records = []
    for suite_id in SUITE_IDS:
        encoded = canonical_json(suites[suite_id]).encode("ascii")
        suite_records.append(
            {
                "suite_id": suite_id,
                "path": f"compat/cases/{suite_id}.json",
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "case_count": len(suites[suite_id]["cases"]),
                "environment_overrides": SUITE_ENVIRONMENT_OVERRIDES[suite_id],
            }
        )
    partitions = build_family_equivalence(inventory)
    partitions_by_id = {partition["id"]: partition for partition in partitions}
    cases_by_id = {
        case["id"]: case
        for suite_id in SUITE_IDS
        for case in suites[suite_id]["cases"]
    }
    enriched_links = []
    for link in links:
        enriched = copy.deepcopy(link)
        equivalence_id = link["family_equivalence"]
        if equivalence_id is None:
            enriched.update(
                {
                    "equivalence_profile": None,
                    "equivalence_claims": [],
                    "covered_commands": [],
                    "inference_scope": None,
                    "probe_resolution": None,
                }
            )
        else:
            profile = (
                "posixly_correct" if link["suite_id"] == POSIX_SUITE else "default"
            )
            arguments = cases_by_id[link["case_id"]]["arguments"]
            base_signature = case_resolution_signature(
                commands[link["command"]], arguments, profile
            )
            covered_commands = [
                command
                for command in partitions_by_id[equivalence_id]["commands"]
                if case_resolution_signature(commands[command], arguments, profile)
                == base_signature
            ]
            enriched.update(
                {
                    "equivalence_profile": profile,
                    "equivalence_claims": sorted(link["policy_expectations"]),
                    "covered_commands": covered_commands,
                    "inference_scope": "parser_resolution",
                    "probe_resolution": base_signature,
                }
            )
        enriched_links.append(enriched)

    parser_overlay = {
        "explicit_aliases": REVIEWED_EXPLICIT_ALIASES,
        "probe_value_options": sorted(PROBE_VALUE_OPTIONS),
    }
    return {
        "schema_version": 1,
        "upstream_commit": ORACLE_COMMIT,
        "inventory": {
            "path": "compat/inventory/v2.5.json",
            "sha256": file_sha256(INVENTORY_PATH),
        },
        "suite_schema": {
            "path": "compat/schema/suite.schema.json",
            "sha256": file_sha256(SUITE_SCHEMA_PATH),
        },
        "reviewed_parser_overlay": {
            **parser_overlay,
            "sha256": canonical_hash(parser_overlay),
        },
        "clean_environment": {
            "inherit_parent": False,
            "allowlist": CLEAN_ENVIRONMENT_ALLOWLIST,
        },
        "suites": suite_records,
        "family_equivalence": partitions,
        "cases": enriched_links,
    }


def build_baseline_status() -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "pending_reproducible_oracle",
        "qualification_evidence": False,
        "retired_image_identity": RETIRED_IMAGE_IDENTITY,
        "raw_baseline_files": [],
        "required_before_recording": [
            "a validated execution manifest for the reproducible Oracle image",
            "an image identity different from the retired development image",
            "execution from the clean environment allowlist in case-contract.json",
            "all suite, case-contract, schema, and reverse-mutation checks passing",
        ],
    }


def build_policy_equivalence_markdown(contract: dict[str, object]) -> str:
    lines = [
        "# CLI Parser Policy Equivalence",
        "",
        "This document summarizes machine-verified parser-policy partitions. The",
        "canonical per-case links, exact policy objects, hashes, and environment",
        "profiles are in `case-contract.json`. These partitions cover parser",
        "mechanics only; they do not claim command-behavior or Ferricov parity.",
        "",
    ]
    for partition in contract["family_equivalence"]:
        title = partition["id"].removeprefix("parser-policy.").replace("-", " ").title()
        lines.extend(
            [
                f"## {title}",
                "",
                f"- ID: `{partition['id']}`",
                f"- Commands: {', '.join(f'`{command}`' for command in partition['commands'])}",
                f"- Canonical policy SHA-256: `{partition['policy_sha256']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Evidence Boundary",
            "",
            "The suites and links are a static executable contract. Raw Oracle",
            "observations remain pending until the reproducible image and matching",
            "execution manifest are available. No retired development-image output is",
            "qualification evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def build_artifacts() -> dict[Path, bytes]:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    suites, links = build_suites_and_links(inventory)
    contract = build_case_contract(inventory, suites, links)
    artifacts = {
        CASES_DIR / f"{suite_id}.json": canonical_json(suites[suite_id]).encode("ascii")
        for suite_id in SUITE_IDS
    }
    artifacts[CASE_CONTRACT_PATH] = canonical_json(contract).encode("ascii")
    artifacts[POLICY_EQUIVALENCE_PATH] = build_policy_equivalence_markdown(contract).encode(
        "ascii"
    )
    artifacts[BASELINE_STATUS_PATH] = canonical_json(build_baseline_status()).encode("ascii")
    return artifacts


def validate_case_ids(suites: dict[str, dict[str, object]]) -> None:
    generated_paths = {CASES_DIR / f"{suite_id}.json" for suite_id in SUITE_IDS}
    owners: dict[str, str] = {}
    for path in sorted(CASES_DIR.glob("*.json")):
        if path in generated_paths:
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        for case in document["cases"]:
            owner = str(path.relative_to(ROOT))
            previous = owners.get(case["id"])
            if previous is not None:
                raise ContractError(
                    f"repository case ID collision: {case['id']} in {previous} and {owner}"
                )
            owners[case["id"]] = owner
    for suite_id in SUITE_IDS:
        for case in suites[suite_id]["cases"]:
            owner = f"compat/cases/{suite_id}.json"
            previous = owners.get(case["id"])
            if previous is not None:
                raise ContractError(
                    f"repository case ID collision: {case['id']} in {previous} and {owner}"
                )
            owners[case["id"]] = owner


def validate_schema_and_semantics(suites: dict[str, dict[str, object]]) -> None:
    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for suite_id in SUITE_IDS:
        validator.validate(suites[suite_id])
        dimensions_seen = set()
        for case in suites[suite_id]["cases"]:
            dimensions = [comparison["dimension"] for comparison in case["comparisons"]]
            if len(dimensions) != len(set(dimensions)):
                raise ContractError(f"duplicate comparison dimension: {case['id']}")
            for dimension in dimensions:
                identity = (case["id"], dimension)
                if identity in dimensions_seen:
                    raise ContractError(f"duplicate case/dimension identity: {identity}")
                dimensions_seen.add(identity)


def validate_probe_matrix(suites: dict[str, dict[str, object]]) -> None:
    by_id = {
        case["id"]: case
        for suite_id in SUITE_IDS
        for case in suites[suite_id]["cases"]
    }
    required_core = set()
    for command in COMMANDS:
        slug = command.replace(".", "-")
        required_core.add(f"m0-core-{slug}-startup-control")
        if command == "xml2lcovutil.py":
            required_core.update(
                {
                    "m0-core-xml2lcovutil-py-help-argv-ignored-control",
                    "m0-core-xml2lcovutil-py-version-argv-ignored-control",
                    "m0-core-xml2lcovutil-py-invalid-argv-ignored-control",
                }
            )
        else:
            required_core.add(f"m0-core-{slug}-help")
            suffix = (
                "version-script-abbreviation"
                if command in {"py2lcov", "xml2lcov"}
                else "version"
            )
            required_core.add(f"m0-core-{slug}-{suffix}")
            required_core.add(f"m0-core-{slug}-invalid-option")
    actual_core = {case["id"] for case in suites[CORE_SUITE]["cases"]}
    if actual_core != required_core:
        raise ContractError("core command control matrix drift")

    for profile, prefix in ((POLICY_SUITE, "m0-policy"), (POSIX_SUITE, "m0-posix")):
        for command in SHARED_GETOPT_COMMANDS:
            slug = command.replace(".", "-")
            for option in ("config-file", "rc"):
                case_id = f"{prefix}-shared-{slug}-{option}-exact"
                case = by_id.get(case_id)
                expected_arguments = (
                    ["--config-file", "empty.lcovrc", "--help"]
                    if option == "config-file"
                    else ["--rc", "branch_coverage=0", "--help"]
                )
                expected_fixture = CONFIG_FIXTURE if option == "config-file" else None
                if case is None:
                    raise ContractError(f"missing shared exact-only execution: {case_id}")
                if (case["command"], case["arguments"], case["fixture"]) != (
                    command,
                    expected_arguments,
                    expected_fixture,
                ):
                    raise ContractError(f"shared exact-only probe identity drift: {case_id}")

    exact_interactions = {
        "m0-policy-shared-config-file-single-dash-exact": (
            ["-config-file", "empty.lcovrc", "--help"],
            CONFIG_FIXTURE,
        ),
        "m0-policy-shared-config-file-abbreviation-rejected": (
            ["--config-f", "empty.lcovrc", "--help"],
            CONFIG_FIXTURE,
        ),
        "m0-policy-shared-rc-case-insensitive-exact": (
            ["--RC", "branch_coverage=0", "--help"],
            None,
        ),
        "m0-posix-shared-config-file-single-dash-exact": (
            ["-config-file", "empty.lcovrc", "--help"],
            CONFIG_FIXTURE,
        ),
        "m0-posix-shared-config-file-abbreviation-rejected": (
            ["--config-f", "empty.lcovrc", "--help"],
            CONFIG_FIXTURE,
        ),
        "m0-posix-shared-rc-case-insensitive-exact": (
            ["--RC", "branch_coverage=0", "--help"],
            None,
        ),
    }
    for case_id, (arguments, fixture) in exact_interactions.items():
        case = by_id.get(case_id)
        if case is None or (case["command"], case["arguments"], case["fixture"]) != (
            "lcov",
            arguments,
            fixture,
        ):
            raise ContractError(f"exact-only interaction identity drift: {case_id}")

    expected_argparse = {
        "m0-policy-argparse-unique-abbreviation": ("py2lcov", ["--verb", "input.xml"], ARGPARSE_FIXTURE),
        "m0-policy-argparse-ambiguous-abbreviation": ("py2lcov", ["--ver", "input.xml"], ARGPARSE_FIXTURE),
        "m0-policy-argparse-case-sensitive": ("py2lcov", ["--VERB", "input.xml"], ARGPARSE_FIXTURE),
        "m0-policy-argparse-rejects-single-dash-long": ("py2lcov", ["-checksum", "input.xml"], ARGPARSE_FIXTURE),
        "m0-policy-argparse-plus-is-positional": ("xml2lcov", ["+help"], PLUS_FIXTURE),
        "m0-policy-argparse-short-option-cluster": ("py2lcov", ["-vk", "input.xml"], ARGPARSE_FIXTURE),
        "m0-policy-argparse-parse-args-boundary": ("py2lcov", ["first.xml", "--no", "later.xml"], None),
        "m0-policy-argparse-xml-unique-abbreviation": ("xml2lcov", ["--verb", "input.xml"], ARGPARSE_FIXTURE),
        "m0-posix-argparse-unique-abbreviation-unchanged": ("py2lcov", ["--verb", "input.xml"], ARGPARSE_FIXTURE),
        "m0-posix-argparse-ambiguous-abbreviation-unchanged": ("py2lcov", ["--ver", "input.xml"], ARGPARSE_FIXTURE),
        "m0-posix-argparse-case-sensitivity-unchanged": ("py2lcov", ["--VERB", "input.xml"], ARGPARSE_FIXTURE),
        "m0-posix-argparse-single-dash-long-rejection-unchanged": ("py2lcov", ["-checksum", "input.xml"], ARGPARSE_FIXTURE),
        "m0-posix-argparse-plus-positional-unchanged": ("xml2lcov", ["+help"], PLUS_FIXTURE),
        "m0-posix-argparse-short-cluster-unchanged": ("py2lcov", ["-vk", "input.xml"], ARGPARSE_FIXTURE),
        "m0-posix-argparse-order-boundary-unchanged": ("py2lcov", ["first.xml", "--no", "later.xml"], None),
        "m0-posix-argparse-xml-unique-abbreviation-unchanged": ("xml2lcov", ["--verb", "input.xml"], ARGPARSE_FIXTURE),
    }
    missing = set(expected_argparse) - by_id.keys()
    if missing:
        raise ContractError(f"missing argparse partition cases: {sorted(missing)}")
    for case_id, (command, arguments, fixture) in expected_argparse.items():
        case = by_id[case_id]
        if (case["command"], case["arguments"], case["fixture"]) != (
            command,
            arguments,
            fixture,
        ):
            raise ContractError(f"argparse probe identity drift: {case_id}")
        if "--help" in arguments or "-h" in arguments:
            raise ContractError(f"argparse policy probe is masked by help: {case_id}")

    required_direct_pairs = {
        "m0-policy-direct-plus-prefix",
        "m0-policy-direct-no-bundling",
        "m0-posix-direct-plus-prefix-disabled",
        "m0-posix-direct-no-bundling-preserved",
    }
    if not required_direct_pairs <= by_id.keys():
        raise ContractError("direct Getopt plus/no-bundling partition drift")
    for case_id in (
        "m0-policy-direct-no-bundling",
        "m0-posix-direct-no-bundling-preserved",
    ):
        case = by_id[case_id]
        if case["command"] != "gendesc" or case["arguments"] != ["-??"]:
            raise ContractError(f"direct no-bundling discriminator drift: {case_id}")

    expected_no_parser = {
        "m0-policy-no-parser-mixed-argv-ignored-control": [
            "+help",
            "-help",
            "--HELP",
            "operand",
        ],
        "m0-posix-no-parser-mixed-argv-ignored-control": [
            "+help",
            "--hel",
            "operand",
            "--help",
        ],
    }
    for case_id, arguments in expected_no_parser.items():
        case = by_id.get(case_id)
        if case is None or case["command"] != "xml2lcovutil.py" or case["arguments"] != arguments:
            raise ContractError(f"no-parser argv-ignored control drift: {case_id}")

    expected_overrides = {
        CORE_SUITE: {},
        POLICY_SUITE: {},
        POSIX_SUITE: {"POSIXLY_CORRECT": "1"},
    }
    if SUITE_ENVIRONMENT_OVERRIDES != expected_overrides:
        raise ContractError("suite environment override contract drift")
    if "POSIXLY_CORRECT" in CLEAN_ENVIRONMENT_ALLOWLIST:
        raise ContractError("POSIXLY_CORRECT must not leak into the clean base environment")


def validate_contract(
    contract: dict[str, object],
    suites: dict[str, dict[str, object]],
    inventory: dict[str, object],
) -> None:
    commands, entries, families = inventory_maps(inventory)
    partitions = {item["id"]: item for item in contract["family_equivalence"]}
    expected_partitions = {
        item["id"]: item for item in build_family_equivalence(inventory)
    }
    if partitions != expected_partitions:
        raise ContractError("family equivalence contract drift")

    suite_records = {item["suite_id"]: item for item in contract["suites"]}
    if set(suite_records) != set(SUITE_IDS):
        raise ContractError("case contract suite set drift")
    for suite_id in SUITE_IDS:
        encoded = canonical_json(suites[suite_id]).encode("ascii")
        record = suite_records[suite_id]
        if record["sha256"] != hashlib.sha256(encoded).hexdigest():
            raise ContractError(f"suite hash drift in case contract: {suite_id}")
        if record["case_count"] != len(suites[suite_id]["cases"]):
            raise ContractError(f"suite case count drift in case contract: {suite_id}")
        if record["environment_overrides"] != SUITE_ENVIRONMENT_OVERRIDES[suite_id]:
            raise ContractError(f"suite environment drift in case contract: {suite_id}")

    cases = {
        case["id"]: (suite_id, case)
        for suite_id in SUITE_IDS
        for case in suites[suite_id]["cases"]
    }
    records = {record["case_id"]: record for record in contract["cases"]}
    if len(records) != len(contract["cases"]):
        raise ContractError("duplicate case link record")
    if set(records) != set(cases):
        raise ContractError("case link set does not exactly match suite case IDs")
    for case_id, (suite_id, case) in cases.items():
        record = records[case_id]
        if record["suite_id"] != suite_id or record["command"] != case["command"]:
            raise ContractError(f"case link identity drift: {case_id}")
        linked = record["inventory_entries"]
        if len(linked) != len(set(linked)):
            raise ContractError(f"duplicate inventory link: {case_id}")
        for entry_id in linked:
            entry = entries.get(entry_id)
            if entry is None:
                raise ContractError(f"unknown inventory link {entry_id} for {case_id}")
            if not entry_id.startswith(f"command.{case['command']}."):
                raise ContractError(f"cross-command inventory link {entry_id} for {case_id}")
            if entry["classification"] != "public" or entry["review_status"] != "reviewed":
                raise ContractError(f"unqualified inventory link {entry_id} for {case_id}")
        equivalence_id = record["family_equivalence"]
        if not linked and equivalence_id is None:
            raise ContractError(f"case has neither exact links nor family equivalence: {case_id}")
        if equivalence_id is not None:
            partition = partitions.get(equivalence_id)
            if partition is None:
                raise ContractError(f"unknown family equivalence {equivalence_id} for {case_id}")
            if partition["family"] != families[case["command"]]:
                raise ContractError(f"wrong family equivalence for {case_id}")
            if case["command"] not in partition["commands"]:
                raise ContractError(f"command absent from family equivalence for {case_id}")
            for key, value in record["policy_expectations"].items():
                if partition["policy"].get(key) != value:
                    raise ContractError(
                        f"policy expectation mismatch for {case_id}: {key}={value!r}"
                    )
            expected_profile = (
                "posixly_correct" if suite_id == POSIX_SUITE else "default"
            )
            if record["equivalence_profile"] != expected_profile:
                raise ContractError(f"family equivalence profile drift: {case_id}")
            if record["equivalence_claims"] != sorted(record["policy_expectations"]):
                raise ContractError(f"family equivalence claims drift: {case_id}")
            if record["inference_scope"] != "parser_resolution":
                raise ContractError(f"family equivalence scope drift: {case_id}")
            base_signature = case_resolution_signature(
                commands[case["command"]], case["arguments"], expected_profile
            )
            if record["probe_resolution"] != base_signature:
                raise ContractError(f"probe resolution identity drift: {case_id}")
            expected_covered = [
                command
                for command in partition["commands"]
                if case_resolution_signature(
                    commands[command], case["arguments"], expected_profile
                )
                == base_signature
            ]
            if record["covered_commands"] != expected_covered:
                raise ContractError(f"covered command set is not resolution-equivalent: {case_id}")
            if case["command"] not in expected_covered:
                raise ContractError(f"executed command is absent from coverage: {case_id}")
        elif record["policy_expectations"]:
            raise ContractError(f"policy expectations lack equivalence proof: {case_id}")
        elif any(
            record[field] not in (None, [])
            for field in (
                "equivalence_profile",
                "equivalence_claims",
                "covered_commands",
                "inference_scope",
                "probe_resolution",
            )
        ):
            raise ContractError(f"exact-link-only case carries equivalence claims: {case_id}")

    expected_resolution_oracles = {
        "m0-policy-shared-no-bundling": [
            {
                "token": "-qv",
                "resolution": "unknown",
                "targets": [],
                "bundling_reverse_targets": ["--quiet", "--verbose"],
            }
        ],
        "m0-posix-shared-no-bundling-preserved": [
            {
                "token": "-qv",
                "resolution": "unknown",
                "targets": [],
                "bundling_reverse_targets": ["--quiet", "--verbose"],
            }
        ],
        "m0-policy-direct-no-bundling": [
            {
                "token": "-??",
                "resolution": "unknown",
                "targets": [],
                "bundling_reverse_targets": ["--help", "--help"],
            }
        ],
        "m0-posix-direct-no-bundling-preserved": [
            {
                "token": "-??",
                "resolution": "unknown",
                "targets": [],
                "bundling_reverse_targets": ["--help", "--help"],
            }
        ],
        "m0-policy-shared-permute": [
            {
                "token": "operand",
                "resolution": "positional",
                "positionals_defined": True,
            },
            {"token": "--help", "resolution": "exact", "targets": ["--help"]},
        ],
        "m0-posix-shared-require-order": [
            {
                "token": "operand",
                "resolution": "positional",
                "positionals_defined": True,
            },
            {"token": "--help", "resolution": "unparsed_after_require_order"},
        ],
        "m0-policy-argparse-parse-args-boundary": [
            {
                "token": "first.xml",
                "resolution": "positional",
                "positionals_defined": True,
            },
            {
                "token": "--no",
                "resolution": "unique_prefix",
                "targets": ["--no-functions"],
            },
            {"token": "later.xml", "resolution": "rejected_after_option_boundary"},
        ],
        "m0-posix-argparse-order-boundary-unchanged": [
            {
                "token": "first.xml",
                "resolution": "positional",
                "positionals_defined": True,
            },
            {
                "token": "--no",
                "resolution": "unique_prefix",
                "targets": ["--no-functions"],
            },
            {"token": "later.xml", "resolution": "rejected_after_option_boundary"},
        ],
        "m0-policy-argparse-plus-is-positional": [
            {
                "token": "+help",
                "resolution": "positional",
                "positionals_defined": True,
            }
        ],
        "m0-policy-shared-config-file-abbreviation-rejected": [
            {
                "token": "--config-f",
                "resolution": "exact_only_prefix_rejected",
                "targets": ["--config-file"],
            },
            {
                "token": "empty.lcovrc",
                "resolution": "option_value",
                "option": "--config-file",
            },
            {"token": "--help", "resolution": "exact", "targets": ["--help"]},
        ],
        "m0-posix-shared-config-file-abbreviation-rejected": [
            {"token": "--config-f", "resolution": "unknown", "targets": []},
            {
                "token": "empty.lcovrc",
                "resolution": "positional",
                "positionals_defined": True,
            },
            {"token": "--help", "resolution": "unparsed_after_require_order"},
        ],
        "m0-core-py2lcov-version-script-abbreviation": [
            {
                "token": "--version",
                "resolution": "unique_prefix",
                "targets": ["--version-script"],
                "missing_value": True,
            }
        ],
        "m0-core-xml2lcov-version-script-abbreviation": [
            {
                "token": "--version",
                "resolution": "unique_prefix",
                "targets": ["--version-script"],
                "missing_value": True,
            }
        ],
        "m0-policy-shared-lcov-config-file-exact": [
            {
                "token": "--config-file",
                "resolution": "exact",
                "targets": ["--config-file"],
            },
            {
                "token": "empty.lcovrc",
                "resolution": "option_value",
                "option": "--config-file",
            },
            {"token": "--help", "resolution": "exact", "targets": ["--help"]},
        ],
        "m0-policy-shared-lcov-rc-exact": [
            {"token": "--rc", "resolution": "exact", "targets": ["--rc"]},
            {
                "token": "branch_coverage=0",
                "resolution": "option_value",
                "option": "--rc",
            },
            {"token": "--help", "resolution": "exact", "targets": ["--help"]},
        ],
    }
    for case_id, expected in expected_resolution_oracles.items():
        if records[case_id]["probe_resolution"] != expected:
            raise ContractError(f"semantic resolution oracle drift: {case_id}")

    expected_help_aliases = {
        (command["name"], alias)
        for command in inventory["commands"]
        for option in command["options"]
        if option["canonical_name"] == "--help"
        for alias in option["aliases"]
    }
    actual_help_aliases = {
        (case["command"], case["arguments"][0])
        for case in suites[POLICY_SUITE]["cases"]
        if case["id"].startswith("m0-policy-help-alias-")
    }
    if actual_help_aliases != expected_help_aliases:
        raise ContractError("explicit help alias execution set drift")

    if contract["clean_environment"] != {
        "inherit_parent": False,
        "allowlist": CLEAN_ENVIRONMENT_ALLOWLIST,
    }:
        raise ContractError("clean environment contract drift")
    if contract["inventory"]["sha256"] != file_sha256(INVENTORY_PATH):
        raise ContractError("case contract inventory hash drift")
    if contract["suite_schema"]["sha256"] != file_sha256(SUITE_SCHEMA_PATH):
        raise ContractError("case contract suite schema hash drift")
    parser_overlay = {
        "explicit_aliases": REVIEWED_EXPLICIT_ALIASES,
        "probe_value_options": sorted(PROBE_VALUE_OPTIONS),
    }
    if contract["reviewed_parser_overlay"] != {
        **parser_overlay,
        "sha256": canonical_hash(parser_overlay),
    }:
        raise ContractError("reviewed parser overlay drift")
    for command, alias_map in REVIEWED_EXPLICIT_ALIASES.items():
        parser_names = {
            option["canonical_name"] for option in parser_option_definitions(commands[command])
        }
        for alias, target in alias_map.items():
            if not alias.startswith("-") or target not in parser_names:
                raise ContractError(
                    f"invalid reviewed explicit alias overlay: {command} {alias} -> {target}"
                )

    # Keep the lookup live so a malformed inventory command set cannot be hidden.
    if set(commands) != set(COMMANDS):
        raise ContractError("case contract command set does not match inventory")


def validate_committed_artifacts(expected: dict[Path, bytes]) -> None:
    for path, content in expected.items():
        if not path.is_file():
            raise ContractError(f"generated artifact is missing: {path.relative_to(ROOT)}")
        if path.read_bytes() != content:
            raise ContractError(f"generated artifact drift: {path.relative_to(ROOT)}")
    remaining = [
        path.relative_to(ROOT).as_posix()
        for path in RETIRED_BASELINE_PATHS
        if path.exists()
    ]
    if remaining:
        raise ContractError(f"retired raw baselines must be removed: {remaining}")


def expect_contract_error(action: Callable[[], None], label: str) -> None:
    try:
        action()
    except (ContractError, json.JSONDecodeError):
        return
    raise ContractError(f"reverse mutation was not rejected: {label}")


def run_reverse_mutation_tests(
    suites: dict[str, dict[str, object]],
    contract: dict[str, object],
    inventory: dict[str, object],
) -> None:
    external_id = json.loads((CASES_DIR / "harness-self-test.json").read_text())["cases"][0][
        "id"
    ]

    duplicate = copy.deepcopy(suites)
    duplicate[POLICY_SUITE]["cases"][0]["id"] = duplicate[CORE_SUITE]["cases"][0]["id"]
    expect_contract_error(lambda: validate_case_ids(duplicate), "cross-suite case ID")

    same_suite_duplicate = copy.deepcopy(suites)
    same_suite_duplicate[CORE_SUITE]["cases"][1]["id"] = same_suite_duplicate[CORE_SUITE][
        "cases"
    ][0]["id"]
    expect_contract_error(
        lambda: validate_case_ids(same_suite_duplicate), "same-suite case ID"
    )

    harness_collision = copy.deepcopy(suites)
    harness_collision[CORE_SUITE]["cases"][0]["id"] = external_id
    expect_contract_error(lambda: validate_case_ids(harness_collision), "harness case ID")

    missing_link = copy.deepcopy(contract)
    missing_link["cases"].pop()
    expect_contract_error(
        lambda: validate_contract(missing_link, suites, inventory), "missing per-case link"
    )

    cross_command = copy.deepcopy(contract)
    target = next(record for record in cross_command["cases"] if record["inventory_entries"])
    target["inventory_entries"] = [option_id("genhtml", "help")]
    expect_contract_error(
        lambda: validate_contract(cross_command, suites, inventory), "cross-command inventory link"
    )

    wrong_partition = copy.deepcopy(contract)
    wrong_partition["family_equivalence"][0]["policy_sha256"] = "0" * 64
    expect_contract_error(
        lambda: validate_contract(wrong_partition, suites, inventory), "family policy identity"
    )

    bad_environment = copy.deepcopy(contract)
    next(
        record for record in bad_environment["suites"] if record["suite_id"] == POSIX_SUITE
    )["environment_overrides"] = {}
    expect_contract_error(
        lambda: validate_contract(bad_environment, suites, inventory), "POSIX environment"
    )

    probe_argv = copy.deepcopy(suites)
    next(
        case
        for case in probe_argv[POLICY_SUITE]["cases"]
        if case["id"] == "m0-policy-argparse-unique-abbreviation"
    )["arguments"] = ["--help"]
    expect_contract_error(
        lambda: validate_contract(contract, probe_argv, inventory), "probe argv identity"
    )

    schema = json.loads(SUITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    unknown_field = copy.deepcopy(suites[CORE_SUITE])
    unknown_field["cases"][0]["unexpected"] = True
    if not list(validator.iter_errors(unknown_field)):
        raise ContractError("schema guard accepted an unknown case field")
    bad_normalizer = copy.deepcopy(suites[CORE_SUITE])
    bad_normalizer["cases"][0]["comparisons"][0]["normalizer"] = "text-crlf-to-lf-v1"
    if not list(validator.iter_errors(bad_normalizer)):
        raise ContractError("schema guard accepted non-exact exit normalization")
    duplicate_comparison = copy.deepcopy(suites[CORE_SUITE])
    duplicate_comparison["cases"][0]["comparisons"].append(
        copy.deepcopy(duplicate_comparison["cases"][0]["comparisons"][0])
    )
    if not list(validator.iter_errors(duplicate_comparison)):
        raise ContractError("schema guard accepted a duplicate comparison")

    duplicate_dimension = copy.deepcopy(suites)
    duplicate_dimension[CORE_SUITE]["cases"][0]["comparisons"][2] = {
        "dimension": "stdout",
        "normalizer": "text-crlf-to-lf-v1",
    }
    expect_contract_error(
        lambda: validate_schema_and_semantics(duplicate_dimension),
        "duplicate comparison dimension with different normalizer",
    )

    print("M0_CLI_REVERSE_MUTATIONS_OK mutations=12")


def validate_all(expected: dict[Path, bytes]) -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    suites, links = build_suites_and_links(inventory)
    contract = build_case_contract(inventory, suites, links)
    validate_schema_and_semantics(suites)
    validate_case_ids(suites)
    validate_probe_matrix(suites)
    validate_contract(contract, suites, inventory)
    validate_committed_artifacts(expected)
    run_reverse_mutation_tests(suites, contract, inventory)

    counts = {suite_id: len(suites[suite_id]["cases"]) for suite_id in SUITE_IDS}
    linked_entries = {
        entry_id for record in links for entry_id in record["inventory_entries"]
    }
    equivalence_cases = sum(record["family_equivalence"] is not None for record in links)
    print(
        "M0_CLI_STATIC_CONTRACT_OK "
        f"suites={len(suites)} cases={sum(counts.values())} counts={counts} "
        f"linked_inventory_entries={len(linked_entries)} "
        f"family_equivalence_cases={equivalence_cases} global_ids=unique"
    )
    print(
        "M0_CLI_ORACLE_BASELINE_PENDING "
        f"retired_image={RETIRED_IMAGE_IDENTITY} qualification=false"
    )


def write_artifacts(artifacts: dict[Path, bytes]) -> None:
    for path, content in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print(f"M0_CLI_ARTIFACTS_WRITTEN files={len(artifacts)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write deterministic suites and static contract artifacts before checking",
    )
    args = parser.parse_args()

    first = build_artifacts()
    second = build_artifacts()
    if first != second:
        raise ContractError("artifact generation is not byte-deterministic")
    if args.write:
        write_artifacts(first)
    validate_all(first)
    return 0


if __name__ == "__main__":
    sys.exit(main())
