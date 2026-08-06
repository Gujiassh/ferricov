"""Shared validation helpers for strict JSON, identities, and store shape."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_INSPECTOR = ROOT / "inspect_model.pl"
MODEL_INSPECTOR_NAME = "inspect_model.pl"
ALLOWED_ARGV_HEADS = {"lcov", "perl"}

SEMANTIC_SNAPSHOT_CASE_IDS = (
    "state-late-tn-mcdc.semantic-snapshot",
    "state-cross-sf-mcdc-success.semantic-snapshot",
    "functions-current-core.semantic-snapshot",
    "functions-mixed-merge.semantic-snapshot",
    "branches-forms-core.semantic-snapshot",
    "branches-noncontiguous.semantic-snapshot",
    "branches-expression-merge.semantic-snapshot",
    "numeric-boundary.semantic-snapshot",
    "numeric-extra-spellings.semantic-snapshot",
    "numeric-format-atoms.ignore-format-negative.semantic-snapshot",
    "numeric-format-atoms.ignore-format-negative-excessive.semantic-snapshot",
    "numeric-signed-zero.semantic-snapshot",
    "numeric-negative-inf.semantic-snapshot",
    "numeric-fna-nonnumeric.semantic-snapshot",
    "numeric-zero-fn-end.semantic-snapshot",
    "numeric-invalid-fnl-fields.semantic-snapshot",
    "functions-zero-start.semantic-snapshot",
    "numeric-format-atoms.tf030.semantic-snapshot",
    "numeric-format-atoms.tf030-threshold.semantic-snapshot",
    "numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot",
    "numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot",
    "numeric-tf030-candidates.ignore-negative.semantic-snapshot",
    "numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot",
)
SEMANTIC_STDERR_POLICIES: dict[str, tuple[tuple[str, str], ...]] = {
    "state-late-tn-mcdc.semantic-snapshot": (),
    "state-cross-sf-mcdc-success.semantic-snapshot": (),
    "functions-current-core.semantic-snapshot": (("WARNING", "unsupported"),),
    "functions-mixed-merge.semantic-snapshot": (),
    "branches-forms-core.semantic-snapshot": (),
    "branches-noncontiguous.semantic-snapshot": (),
    "branches-expression-merge.semantic-snapshot": (),
    "numeric-boundary.semantic-snapshot": (("WARNING", "format"),),
    "numeric-extra-spellings.semantic-snapshot": (),
    "numeric-format-atoms.ignore-format-negative.semantic-snapshot": (
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "negative"),
        ("WARNING", "format"),
    ),
    "numeric-format-atoms.ignore-format-negative-excessive.semantic-snapshot": (
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "excessive"),
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "excessive"),
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
    ),
    "numeric-signed-zero.semantic-snapshot": (),
    "numeric-negative-inf.semantic-snapshot": (("WARNING", "negative"),),
    "numeric-fna-nonnumeric.semantic-snapshot": (("WARNING", "format"),),
    "numeric-zero-fn-end.semantic-snapshot": (("WARNING", "format"),),
    "numeric-invalid-fnl-fields.semantic-snapshot": (
        ("WARNING", "format"),
        ("WARNING", "format"),
    ),
    "functions-zero-start.semantic-snapshot": (("WARNING", "inconsistent"),),
    "numeric-format-atoms.tf030.semantic-snapshot": (
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "negative"),
        ("WARNING", "format"),
    ),
    "numeric-format-atoms.tf030-threshold.semantic-snapshot": (
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "excessive"),
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "excessive"),
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
    ),
    "numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot": (
        ("WARNING", "negative"),
        ("WARNING", "format"),
    ),
    "numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot": (
        ("WARNING", "negative"),
        ("WARNING", "format"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
    ),
    "numeric-tf030-candidates.ignore-negative.semantic-snapshot": (
        ("WARNING", "negative"),
        ("WARNING", "negative"),
        ("WARNING", "negative"),
        ("WARNING", "negative"),
    ),
    "numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot": (
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "negative"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "negative"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "negative"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "excessive"),
        ("WARNING", "negative"),
    ),
}
def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def reject_json_constant(value: str) -> None:
    raise ValueError(f"non-RFC JSON constant: {value}")


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate JSON object key: {key}")
        document[key] = value
    return document


def strict_json_loads_ascii(raw: bytes, label: str) -> dict[str, object]:
    try:
        # Decode inside this helper so malformed bytes receive the same
        # fail-closed diagnostic as RFC-invalid constants.
        text = raw.decode("ascii")
        document = json.loads(
            text,
            parse_constant=reject_json_constant,
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{label}: not strict ASCII JSON: {error}") from error
    require(isinstance(document, dict), f"{label}: root must be object")
    return document


def strict_json_file(path: Path, label: str) -> dict[str, object]:
    return strict_json_loads_ascii(path.read_bytes(), label)


def semantic_inputs_from_argv(argv: list[object], label: str) -> list[str]:
    require(argv[:2] == ["perl", MODEL_INSPECTOR_NAME], f"{label}: inspector argv drift")
    inputs: list[str] = []
    index = 2
    while index < len(argv):
        value = str(argv[index])
        if value in {"--ignore", "--ignore-errors", "--excessive-threshold", "--numeric-plan"}:
            require(index + 1 < len(argv), f"{label}: option {value} lacks a value")
            index += 2
            continue
        if value == "--":
            inputs.extend(str(item) for item in argv[index + 1 :])
            break
        require(not value.startswith("-"), f"{label}: unexpected inspector option {value}")
        inputs.append(value)
        index += 1
    require(inputs, f"{label}: inspector argv has no input")
    return inputs


def validate_semantic_input_identity(case: dict[str, object], document: dict[str, object]) -> None:
    expected = semantic_inputs_from_argv(list(case["argv"]), str(case["id"]))
    has_input = "input" in document
    has_inputs = "inputs" in document
    require(has_input != has_inputs, f"{case['id']}: exactly one of input/inputs is required")
    if len(expected) == 1:
        require(has_input and not has_inputs, f"{case['id']}: single input must use input")
        require(document.get("input") == expected[0], f"{case['id']}: input identity drift")
    else:
        require(has_inputs and not has_input, f"{case['id']}: multiple inputs must use inputs")
        require(document.get("inputs") == expected, f"{case['id']}: ordered inputs identity drift")


def validate_semantic_stderr(case_id: str, raw: bytes) -> None:
    require(case_id in SEMANTIC_STDERR_POLICIES, f"{case_id}: missing stderr policy")
    text = raw.decode("utf-8", "strict")
    actual: list[tuple[str, str]] = []
    previous_was_header = False
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith("\t"):
            require(previous_was_header, f"{case_id}: orphan diagnostic continuation")
            continue
        match = re.match(rf"^{re.escape(MODEL_INSPECTOR_NAME)}: (WARNING|ERROR): \(([^)]+)\) ", line)
        require(match is not None, f"{case_id}: unclassified diagnostic line")
        actual.append((match.group(1), match.group(2)))
        previous_was_header = True
    expected = list(SEMANTIC_STDERR_POLICIES[case_id])
    require(
        actual == expected,
        f"{case_id}: stderr policy order/count drift: actual={actual!r} expected={expected!r}",
    )


def validate_lcov_stderr(case_id: str, raw: bytes, expected: tuple[tuple[str, str], ...]) -> None:
    text = raw.decode("utf-8", "strict")
    actual: list[tuple[str, str]] = []
    previous_was_header = False
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith("\t"):
            require(previous_was_header, f"{case_id}: orphan diagnostic continuation")
            continue
        matches = list(re.finditer(r"(?<!\S)lcov: (WARNING|ERROR): \(([^)]+)\) ", line))
        require(matches and line.startswith("lcov: "), f"{case_id}: unclassified diagnostic line")
        actual.extend((match.group(1), match.group(2)) for match in matches)
        previous_was_header = True
    require(
        actual == list(expected),
        f"{case_id}: stderr policy order/count drift: actual={actual!r} expected={list(expected)!r}",
    )


def verify_identity(identity: dict[str, object], label: str) -> None:
    require(isinstance(identity.get("sha256"), str), f"{label}: missing sha256")
    require(isinstance(identity.get("byte_size"), int), f"{label}: missing byte_size")
    if "base64" in identity:
        data = base64.b64decode(str(identity["base64"]), validate=True)
        require(len(data) == identity["byte_size"], f"{label}: base64 size mismatch")
        require(hashlib.sha256(data).hexdigest() == identity["sha256"], f"{label}: base64 hash mismatch")


def decode_identity(identity: dict[str, object], label: str) -> bytes:
    verify_identity(identity, label)
    require("base64" in identity, f"{label}: raw identity required")
    return base64.b64decode(str(identity["base64"]), validate=True)


def assert_count_store(store: dict[str, object], label: str, *, allow_empty: bool = True) -> None:
    require(isinstance(store, dict), f"{label}: store must be object")
    require(isinstance(store.get("found"), int), f"{label}: missing found")
    require(isinstance(store.get("hit"), int), f"{label}: missing hit")
    require(isinstance(store.get("lines"), dict), f"{label}: missing lines")
    if not allow_empty:
        require(store["lines"], f"{label}: expected non-empty lines")


def assert_function_store(store: dict[str, object], label: str) -> None:
    require(isinstance(store, dict), f"{label}: store must be object")
    require(isinstance(store.get("found"), int), f"{label}: missing found")
    require(isinstance(store.get("hit"), int), f"{label}: missing hit")
    require(isinstance(store.get("functions"), dict), f"{label}: missing functions")


def assert_branch_store(store: dict[str, object], label: str) -> None:
    require(isinstance(store, dict), f"{label}: store must be object")
    require(isinstance(store.get("found"), int), f"{label}: missing found")
    require(isinstance(store.get("hit"), int), f"{label}: missing hit")
    require(isinstance(store.get("lines"), dict), f"{label}: missing lines")


def assert_mcdc_store(store: dict[str, object], label: str) -> None:
    require(isinstance(store, dict), f"{label}: store must be object")
    require(isinstance(store.get("found"), int), f"{label}: missing found")
    require(isinstance(store.get("hit"), int), f"{label}: missing hit")
    require(isinstance(store.get("lines"), dict), f"{label}: missing lines")
    for line, block in store["lines"].items():
        require(isinstance(block, dict), f"{label}.{line}: block must be object")
        require(isinstance(block.get("groups"), dict), f"{label}.{line}: missing groups")
        for size, exprs in block["groups"].items():
            require(isinstance(exprs, list), f"{label}.{line}.groups.{size}: must be list")
            for expr in exprs:
                require(isinstance(expr.get("expression"), str), f"{label}.{line}: missing expression")
                require("true_count" in expr and "false_count" in expr, f"{label}.{line}: missing sense counts")
                require("true_excluded" in expr and "false_excluded" in expr, f"{label}.{line}: missing excluded flags")


def assert_four_family_maps(testcases: dict[str, object], label: str) -> None:
    require(set(testcases) == {"line", "function", "branch", "mcdc"}, f"{label}: four family maps required")
    for family in ("line", "function", "branch", "mcdc"):
        require(isinstance(testcases[family], dict), f"{label}.{family}: map must be object")


def assert_single_testcase_parity(source: dict[str, object], testcase: str, label: str) -> None:
    aggregate = source.get("aggregate")
    testcases = source.get("testcases")
    require(isinstance(aggregate, dict), f"{label}: aggregate missing")
    require(set(aggregate) == {"line", "function", "branch", "mcdc"}, f"{label}: aggregate families drift")
    require(isinstance(testcases, dict), f"{label}: testcases missing")
    assert_four_family_maps(testcases, f"{label}.testcases")
    for family in ("line", "function", "branch", "mcdc"):
        require(set(testcases[family]) == {testcase}, f"{label}: {family} testcase identity drift")
        require(
            testcases[family][testcase] == aggregate[family],
            f"{label}: aggregate/testcase {family} parity drift",
        )
