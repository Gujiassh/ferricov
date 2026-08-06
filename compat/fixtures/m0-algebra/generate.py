#!/usr/bin/env python3
"""Generate the byte-exact M0 coverage-model algebra fixture corpus and case manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FIXTURE_ROOT = ROOT / "fixtures"
ORACLE_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
ORACLE_IMAGE = "ferricov/lcov-oracle:v2.5"
# Pinned content-addressed image used by the M0 resource/installation contracts.
ORACLE_IMAGE_ID = (
    "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
)
ORACLE_EXECUTABLE_SHA256 = (
    "d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252"
)
ORACLE_EXECUTABLE_PATH = "/usr/local/bin/lcov"
IGNORE = "empty,inconsistent,mismatch,format,negative,unused,unsupported"
COMMON_LCOV_PREFIX = [
    "lcov",
    "--branch-coverage",
    "--mcdc-coverage",
    f"--ignore-errors={IGNORE}",
]


def ascii_bytes(text: str) -> bytes:
    data = text.encode("ascii")
    if not data.endswith(b"\n"):
        data += b"\n"
    return data


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture_bytes(name: str) -> bytes:
    return (FIXTURE_ROOT / name).read_bytes()


def fixture_meta(name: str) -> dict[str, Any]:
    data = fixture_bytes(name)
    return {
        "id": name.removesuffix(".info"),
        "path": f"fixtures/{name}",
        "sha256": sha256_bytes(data),
        "byte_size": len(data),
    }


def case(
    case_id: str,
    *,
    model_row: str,
    binding_ids: list[str],
    description: str,
    argv: list[str],
    left: str | None = None,
    right: str | None = None,
    input_fixture: str | None = None,
    runner: str = "lcov",
    op: str | None = None,
    output_file: str | None = "output.info",
    expected_exit: int = 0,
    phase: str = "oracle_baseline",
    property_ids: list[str] | None = None,
    capture_mode: str = "cli_and_semantic",
    outcome_class: str = "success",
    error_signature: str | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "id": case_id,
        "model_row": model_row,
        "binding_ids": binding_ids,
        "property_ids": property_ids or [],
        "description": description,
        "phase": phase,
        "runner": runner,
        "argv": argv,
        "expected_exit": expected_exit,
        "output_file": output_file,
        "capture_mode": capture_mode,
        "outcome_class": outcome_class,
        "product_compatibility_evidence": False,
        "oracle_baseline_status": "required",
        "ferricov_parity_status": "blocked",
    }
    if error_signature is not None:
        document["error_signature"] = error_signature
    if op is not None:
        document["op"] = op
    if left is not None:
        document["left"] = f"fixtures/{left}"
        document["left_sha256"] = sha256_bytes(fixture_bytes(left))
    if right is not None:
        document["right"] = f"fixtures/{right}"
        document["right_sha256"] = sha256_bytes(fixture_bytes(right))
    if input_fixture is not None:
        document["input"] = f"fixtures/{input_fixture}"
        document["input_sha256"] = sha256_bytes(fixture_bytes(input_fixture))
    return document


def algebra_pair_cases(
    prefix: str,
    *,
    model_row: str,
    binding_ids: list[str],
    left: str,
    right: str,
    property_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    matrix = (
        ("union", "union", ["--add-tracefile", "left.info", "--add-tracefile", "right.info"]),
        ("intersect", "intersect", ["left.info", "--intersect", "right.info"]),
        ("difference", "difference", ["left.info", "--subtract", "right.info"]),
        (
            "union-rev",
            "union",
            ["--add-tracefile", "right.info", "--add-tracefile", "left.info"],
        ),
        (
            "intersect-rev",
            "intersect",
            ["right.info", "--intersect", "left.info"],
        ),
        (
            "difference-rev",
            "difference",
            ["right.info", "--subtract", "left.info"],
        ),
    )
    for suffix, op, args in matrix:
        # CLI observation: raw streams + output bytes.
        cases.append(
            case(
                f"{prefix}.{suffix}.cli",
                model_row=model_row,
                binding_ids=binding_ids,
                property_ids=property_ids,
                description=f"{prefix} CLI {op} observation",
                argv=[
                    *COMMON_LCOV_PREFIX,
                    "--output-file",
                    "output.info",
                    *args,
                ],
                left=left,
                right=right,
                runner="lcov",
                op=op,
                output_file="output.info",
                capture_mode="cli",
            )
        )
        # Semantic snapshot through the in-image algebra inspector.
        # Reverse cases pass right then left so merge order matches CLI.
        first = "left.info" if "rev" not in suffix else "right.info"
        second = "right.info" if "rev" not in suffix else "left.info"
        cases.append(
            case(
                f"{prefix}.{suffix}.semantic",
                model_row=model_row,
                binding_ids=binding_ids,
                property_ids=property_ids,
                description=f"{prefix} semantic {op} snapshot",
                argv=[
                    "perl",
                    "inspect_algebra.pl",
                    "--ignore",
                    IGNORE,
                    "--op",
                    op,
                    first,
                    second,
                ],
                left=left,
                right=right,
                runner="inspect_algebra.pl",
                op=op,
                output_file=None,
                capture_mode="semantic",
            )
        )
    return cases


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    cases.extend(
        algebra_pair_cases(
            "md010-line",
            model_row="M1-MD-010",
            binding_ids=["M1-ALG-LINE-001", "M1-PROP-ALGEBRA-001"],
            left="md010-left.info",
            right="md010-right.info",
            property_ids=["M1-PROP-ALGEBRA-001"],
        )
    )
    cases.extend(
        algebra_pair_cases(
            "md011-function",
            model_row="M1-MD-011",
            binding_ids=["M1-ALG-FUNCTION-001"],
            left="md011-left.info",
            right="md011-right.info",
        )
    )
    cases.extend(
        algebra_pair_cases(
            "md011-function-rep",
            model_row="M1-MD-011",
            binding_ids=["M1-ALG-FUNCTION-REP-001"],
            left="md011-rep-left.info",
            right="md011-rep-right.info",
        )
    )
    cases.extend(
        algebra_pair_cases(
            "md012-branch",
            model_row="M1-MD-012",
            binding_ids=["M1-ALG-BRANCH-001"],
            left="md012-left.info",
            right="md012-right.info",
        )
    )
    cases.extend(
        algebra_pair_cases(
            "md012-branch-cache",
            model_row="M1-MD-012",
            binding_ids=["M1-ALG-BRANCH-CACHE-001"],
            left="md012-left.info",
            right="md012-cache-right.info",
        )
    )
    cases.extend(
        algebra_pair_cases(
            "md013-mcdc",
            model_row="M1-MD-013",
            binding_ids=["M1-ALG-MCDC-001"],
            left="md013-left.info",
            right="md013-right.info",
        )
    )
    cases.extend(
        algebra_pair_cases(
            "md013-mcdc-expr",
            model_row="M1-MD-013",
            binding_ids=["M1-ALG-MCDC-EXPR-001"],
            left="md013-left.info",
            right="md013-expr-right.info",
        )
    )
    cases.extend(
        algebra_pair_cases(
            "md013-mcdc-vector",
            model_row="M1-MD-013",
            binding_ids=["M1-ALG-MCDC-VECTOR-001"],
            left="md013-vector-long.info",
            right="md013-vector-short.info",
        )
    )
    for family, binding in (
        ("line", "M1-ALG-TESTCASE-LINE-001"),
        ("function", "M1-ALG-TESTCASE-FUNCTION-001"),
        ("branch", "M1-ALG-TESTCASE-BRANCH-001"),
        ("mcdc", "M1-ALG-TESTCASE-MCDC-001"),
    ):
        cases.extend(
            algebra_pair_cases(
                f"md014-testcase-{family}",
                model_row="M1-MD-014",
                binding_ids=[binding],
                left=f"md014-{family}-left.info",
                right=f"md014-{family}-right.info",
            )
        )

    # M1-MD-017 parse-write-parse: load, rewrite, reload semantic equality probes.
    for name, fixture in (
        ("current", "md017-current.info"),
        ("legacy", "md017-legacy.info"),
        ("permissive", "md017-permissive.info"),
    ):
        cases.append(
            case(
                f"md017-{name}.load.semantic",
                model_row="M1-MD-017",
                binding_ids=["M1-TF-045", "M1-TF-052", "M1-PROP-ROUNDTRIP-001"],
                property_ids=["M1-PROP-ROUNDTRIP-001"],
                description=f"parse semantic snapshot for {name}",
                argv=[
                    "perl",
                    "inspect_algebra.pl",
                    "--ignore",
                    IGNORE,
                    "--op",
                    "load",
                    "input.info",
                ],
                input_fixture=fixture,
                runner="inspect_algebra.pl",
                op="load",
                output_file=None,
                capture_mode="semantic",
            )
        )
        cases.append(
            case(
                f"md017-{name}.rewrite.cli",
                model_row="M1-MD-017",
                binding_ids=["M1-TF-045", "M1-TF-052"],
                property_ids=["M1-PROP-ROUNDTRIP-001"],
                description=f"canonical rewrite for {name}",
                argv=[
                    *COMMON_LCOV_PREFIX,
                    "--add-tracefile",
                    "input.info",
                    "--output-file",
                    "output.info",
                ],
                input_fixture=fixture,
                runner="lcov",
                op="rewrite",
                output_file="output.info",
                capture_mode="cli",
            )
        )
        cases.append(
            case(
                f"md017-{name}.rewrite.semantic",
                model_row="M1-MD-017",
                binding_ids=["M1-TF-045", "M1-TF-052", "M1-PROP-ROUNDTRIP-001"],
                property_ids=["M1-PROP-ROUNDTRIP-001"],
                description=f"parse-write-parse semantic snapshot for {name}",
                argv=[
                    "perl",
                    "inspect_algebra.pl",
                    "--ignore",
                    IGNORE,
                    "--op",
                    "load",
                    "output.info",
                ],
                input_fixture=fixture,
                runner="inspect_algebra.pl",
                op="rewrite-load",
                output_file="output.info",
                capture_mode="rewrite_semantic",
            )
        )

    # M1-MD-019 repeated-close / cumulative double-add where reproducible.
    cases.append(
        case(
            "md019-repeated-close.summary.cli",
            model_row="M1-MD-019",
            binding_ids=["M1-TF-015", "M1-TF-023"],
            description="summary after repeated source/test close",
            argv=[
                *COMMON_LCOV_PREFIX,
                "--summary",
                "input.info",
            ],
            input_fixture="md019-repeated-close.info",
            runner="lcov",
            op="summary",
            output_file=None,
            capture_mode="cli",
        )
    )
    cases.append(
        case(
            "md019-repeated-close.semantic",
            model_row="M1-MD-019",
            binding_ids=["M1-TF-015", "M1-TF-023", "M1-PROP-NONSERIAL-001"],
            property_ids=["M1-PROP-NONSERIAL-001"],
            description="semantic snapshot after repeated source/test close",
            argv=[
                "perl",
                "inspect_algebra.pl",
                "--ignore",
                IGNORE,
                "--op",
                "load",
                "input.info",
            ],
            input_fixture="md019-repeated-close.info",
            runner="inspect_algebra.pl",
            op="load",
            output_file=None,
            capture_mode="semantic",
        )
    )
    cases.append(
        case(
            "md019-repeated-close.rewrite.cli",
            model_row="M1-MD-019",
            binding_ids=["M1-TF-015", "M1-TF-023"],
            description="canonical rewrite after repeated close",
            argv=[
                *COMMON_LCOV_PREFIX,
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            input_fixture="md019-repeated-close.info",
            runner="lcov",
            op="rewrite",
            output_file="output.info",
            capture_mode="cli",
        )
    )
    cases.append(
        case(
            "md019-repeated-terminator.semantic",
            model_row="M1-MD-019",
            binding_ids=["M1-TF-015"],
            description="semantic snapshot with repeated end_of_record",
            argv=[
                "perl",
                "inspect_algebra.pl",
                "--ignore",
                IGNORE,
                "--op",
                "load",
                "input.info",
            ],
            input_fixture="md019-repeated-terminator.info",
            runner="inspect_algebra.pl",
            op="load",
            output_file=None,
            capture_mode="semantic",
            expected_exit=0,
        )
    )
    # Exact Oracle outcomes for asymmetric MC/DC vector orders (M1-ALG-MCDC-VECTOR-001).
    # Long-then-short union/intersect hard-fail with expression-on-undef;
    # reverse order (short-then-long) succeeds. Difference remains success.
    rejected = {
        "md013-mcdc-vector.union.cli": {
            "expected_exit": 1,
            "outcome_class": "oracle_hard_error",
            "error_signature": "Can't call method \"expression\" on an undefined value",
        },
        "md013-mcdc-vector.union.semantic": {
            "expected_exit": 255,
            "outcome_class": "oracle_hard_error",
            "error_signature": "Can't call method \"expression\" on an undefined value",
        },
        "md013-mcdc-vector.intersect.cli": {
            "expected_exit": 1,
            "outcome_class": "oracle_hard_error",
            "error_signature": "Can't call method \"expression\" on an undefined value",
        },
        "md013-mcdc-vector.intersect.semantic": {
            "expected_exit": 255,
            "outcome_class": "oracle_hard_error",
            "error_signature": "Can't call method \"expression\" on an undefined value",
        },
    }
    for item in cases:
        if item["id"] in rejected:
            item.update(rejected[item["id"]])
    return cases


def fixture_inventory() -> list[dict[str, Any]]:
    names = sorted(path.name for path in FIXTURE_ROOT.glob("*.info"))
    return [fixture_meta(name) for name in names]


def build_cases_document() -> dict[str, Any]:
    cases = build_cases()
    return {
        "schema_version": 1,
        "description": (
            "Executable M0 Oracle coverage-model algebra and property evidence "
            "for unbound rows M1-MD-010..014, M1-MD-017, and M1-MD-019."
        ),
        "execution": {
            "working_directory": "/work",
            "locale": "C.UTF-8",
            "network": "none",
            "user": "host-uid",
            "home": "/tmp",
        },
        "oracle": {
            "source_commit": ORACLE_COMMIT,
            "docker_image": ORACLE_IMAGE,
            "docker_image_id": ORACLE_IMAGE_ID,
            "program": ORACLE_EXECUTABLE_PATH,
            "program_sha256": ORACLE_EXECUTABLE_SHA256,
        },
        "blocked_case_ids": ["M1-MD-020", "M1-TF-063", "M1-TF-064"],
        "fuzz_execution_phase": "M1-only",
        "product_compatibility_evidence": False,
        "model_rows": [
            {
                "id": "M1-MD-010",
                "status": "oracle_bound",
                "bindings": ["M1-ALG-LINE-001", "M1-PROP-ALGEBRA-001"],
            },
            {
                "id": "M1-MD-011",
                "status": "oracle_bound",
                "bindings": ["M1-ALG-FUNCTION-001", "M1-ALG-FUNCTION-REP-001"],
            },
            {
                "id": "M1-MD-012",
                "status": "oracle_bound",
                "bindings": ["M1-ALG-BRANCH-001", "M1-ALG-BRANCH-CACHE-001"],
            },
            {
                "id": "M1-MD-013",
                "status": "oracle_bound",
                "bindings": [
                    "M1-ALG-MCDC-001",
                    "M1-ALG-MCDC-VECTOR-001",
                    "M1-ALG-MCDC-EXPR-001",
                ],
            },
            {
                "id": "M1-MD-014",
                "status": "oracle_bound",
                "bindings": [
                    "M1-ALG-TESTCASE-LINE-001",
                    "M1-ALG-TESTCASE-FUNCTION-001",
                    "M1-ALG-TESTCASE-BRANCH-001",
                    "M1-ALG-TESTCASE-MCDC-001",
                ],
            },
            {
                "id": "M1-MD-017",
                "status": "oracle_bound",
                "bindings": ["M1-TF-045", "M1-TF-052", "M1-PROP-ROUNDTRIP-001"],
            },
            {
                "id": "M1-MD-019",
                "status": "oracle_bound",
                "bindings": ["M1-TF-015", "M1-TF-023", "M1-PROP-NONSERIAL-001"],
            },
            {
                "id": "M1-MD-020",
                "status": "blocked",
                "bindings": ["M1-TF-063", "M1-TF-064"],
                "reason": "adversarial fuzz execution remains M1-only",
            },
        ],
        "fixtures": fixture_inventory(),
        "cases": cases,
    }


def build_manifest() -> dict[str, Any]:
    cases_document = build_cases_document()
    fixtures = cases_document["fixtures"]
    return {
        "schema_version": 1,
        "corpus_id": "m0-model-algebra-v1",
        "source_commit": ORACLE_COMMIT,
        "fixture_count": len(fixtures),
        "case_count": len(cases_document["cases"]),
        "fixtures": fixtures,
        "oracle": cases_document["oracle"],
        "product_compatibility_evidence": False,
    }


def write_generated(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    fixtures_out = root / "fixtures"
    fixtures_out.mkdir(exist_ok=True)
    for path in FIXTURE_ROOT.glob("*.info"):
        (fixtures_out / path.name).write_bytes(path.read_bytes())
    (root / "inspect_algebra.pl").write_bytes((ROOT / "inspect_algebra.pl").read_bytes())
    cases = build_cases_document()
    (root / "oracle-cases.json").write_text(
        json.dumps(cases, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    (root / "manifest.json").write_text(
        json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-repo", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.write_repo:
        cases_path = ROOT / "oracle-cases.json"
        manifest_path = ROOT / "manifest.json"
        cases_path.write_text(
            json.dumps(build_cases_document(), indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        manifest_path.write_text(
            json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        print(f"wrote {cases_path}")
        print(f"wrote {manifest_path}")
        return 0
    if args.output is not None:
        write_generated(args.output)
        print(f"wrote generated corpus to {args.output}")
        return 0
    document = build_cases_document()
    print(json.dumps({"case_count": len(document["cases"]), "fixture_count": len(document["fixtures"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
