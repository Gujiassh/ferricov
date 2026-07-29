#!/usr/bin/env python3
"""Validate compatibility contracts, snapshots, inventory, and result evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator


EXPECTED_COMMANDS = {
    "lcov": 77,
    "genhtml": 95,
    "geninfo": 60,
    "genpng": 6,
    "gendesc": 3,
    "perl2lcov": 46,
    "py2lcov": 12,
    "xml2lcov": 8,
    "xml2lcovutil.py": 0,
    "llvm2lcov": 46,
}

EXPECTED_POLICY_FAMILIES = {
    "lcov": "shared_getopt_long",
    "genhtml": "shared_getopt_long",
    "geninfo": "shared_getopt_long",
    "genpng": "direct_getopt_long",
    "gendesc": "direct_getopt_long",
    "perl2lcov": "shared_getopt_long",
    "py2lcov": "argparse",
    "xml2lcov": "argparse",
    "xml2lcovutil.py": "none",
    "llvm2lcov": "shared_getopt_long",
}

EXPECTED_POSITIONALS = {
    "lcov": ["operation_operands"],
    "genhtml": ["tracefile_pattern"],
    "geninfo": ["directory"],
    "genpng": ["sourcefile"],
    "gendesc": ["inputfile"],
    "perl2lcov": ["cover_db"],
    "py2lcov": ["inputs"],
    "xml2lcov": ["inputs"],
    "xml2lcovutil.py": [],
    "llvm2lcov": ["json_file"],
}

EXPECTED_GENERATED_TOKEN_NAMES = {
    "lcov": (
        "--annotate-script",
        "--build-dir",
        "--coverage",
        "--diff",
        "--diff-file",
        "--history",
        "--output-filename",
        "--path",
        "--substitution",
    ),
    "genhtml": (
        "--add-tracefile",
        "--baseline-file-pattern",
        "--capture",
        "--compare",
        "--diff",
        "--erase-function",
        "--fail",
        "--highlight",
        "--line",
        "--no-source",
        "--show-proportions",
        "--sort",
    ),
    "geninfo": (
        "--add-tracefile",
        "--annotate-script",
        "--capture",
        "--coverage",
        "--directory",
        "--mcdc",
        "--show-proportions",
    ),
    "perl2lcov": ("--ignore-error",),
    "py2lcov": (
        "--append",
        "--baseline-file",
        "--branch",
        "--data-file",
        "--filter",
    ),
    "llvm2lcov": (
        "--capture",
        "--coverage",
        "--gcov-tool",
        "--ignore-error",
        "--output",
        "--sparse",
        "--testname",
    ),
}

EXPECTED_UNIQUE_ABBREVIATION_TARGETS = {
    "command.lcov.option.build-dir": "command.lcov.option.build-directory",
    "command.lcov.option.history": "command.lcov.option.history-script",
    "command.genhtml.option.diff": "command.genhtml.option.diff-file",
    "command.genhtml.option.erase-function": "command.genhtml.option.erase-functions",
    "command.genhtml.option.no-source": "command.genhtml.option.no-sourceview",
    "command.geninfo.option.mcdc": "command.geninfo.option.mcdc-coverage",
    "command.perl2lcov.option.ignore-error": "command.perl2lcov.option.ignore-errors",
    "command.llvm2lcov.option.ignore-error": "command.llvm2lcov.option.ignore-errors",
    "command.llvm2lcov.option.output": "command.llvm2lcov.option.output-filename",
}

EXPECTED_AMBIGUOUS_GENERATED_TOKENS = {
    "command.genhtml.option.fail",
    "command.genhtml.option.sort",
}

EXPECTED_POLICY_SOURCE_PATHS = {
    command: (
        {f"bin/{command}", "lib/lcovutil.pm"}
        if family == "shared_getopt_long"
        else {f"bin/{command}"}
    )
    for command, family in EXPECTED_POLICY_FAMILIES.items()
}


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
    run(
        [sys.executable, str(root / "compat/cases/m0-cli-contract.py")],
        root,
    )
    run(
        [sys.executable, str(root / "compat/cases/m0_config_contract.py")],
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
    validate_documents(
        root / "compat/schema/environment-contract.schema.json",
        [root / "compat/environment/v2.5.json"],
    )
    validate_documents(
        root / "compat/schema/tracefile-contract.schema.json",
        [root / "compat/tracefile/v2.5.json"],
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
