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
ALLOWED_ARGV_HEADS = {"lcov", "perl", "xml2lcov", "py2lcov", "sh"}

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
    "wave1-mcdc-core.semantic-snapshot",
    "wave1-order-canonical.semantic-snapshot",
    "wave1-order-permuted.semantic-snapshot",
    "wave1-repeat-same-tn.semantic-snapshot",
    "wave1-repeat-diff-tn-mcdc.semantic-snapshot",
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
    "wave1-mcdc-core.semantic-snapshot": (),
    "wave1-order-canonical.semantic-snapshot": (),
    "wave1-order-permuted.semantic-snapshot": (),
    "wave1-repeat-same-tn.semantic-snapshot": (),
    "wave1-repeat-diff-tn-mcdc.semantic-snapshot": (),
}
def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)



def json_values_equal(left: object, right: object) -> bool:
    """Type-sensitive recursive JSON equality.

    Python's ``==`` treats ``True == 1`` and ``1 == 1.0`` as true. JSON
    evidence comparisons must reject those cross-type equivalences.
    """
    if left is None or right is None:
        return left is right
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if isinstance(left, int) or isinstance(right, int):
        # bool is a subclass of int; bools already handled above.
        return (
            isinstance(left, int)
            and not isinstance(left, bool)
            and isinstance(right, int)
            and not isinstance(right, bool)
            and left == right
        )
    if isinstance(left, float) or isinstance(right, float):
        return isinstance(left, float) and isinstance(right, float) and left == right
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) or isinstance(right, list):
        if not isinstance(left, list) or not isinstance(right, list):
            return False
        if len(left) != len(right):
            return False
        return all(json_values_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) or isinstance(right, dict):
        if not isinstance(left, dict) or not isinstance(right, dict):
            return False
        if set(left) != set(right):
            return False
        return all(json_values_equal(left[key], right[key]) for key in left)
    return left == right


def require_json_equal(left: object, right: object, message: str) -> None:
    require(json_values_equal(left, right), message)


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


def parse_tracefile_sections(data: bytes) -> list[dict[str, object]]:
    """Parse LCOV info text into ordered section models for semantic predicates."""
    sections: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw_line in data.splitlines():
        line = raw_line
        if line.startswith(b"TN:"):
            if current is not None:
                sections.append(current)
            current = {
                "tn": line[3:],
                "sf": None,
                "ver": None,
                "functions": [],  # list[(index, start, end)]
                "aliases": [],  # list[(index, count, name)]
                "branches": [],  # list[(line, block, expr, taken)]
                "mcdc": [],  # list[(line, group, sense, count, index, expr)]
                "das": [],  # list[(line, count, checksum|None)]
                "summaries": {},
            }
            continue
        if current is None:
            continue
        if line.startswith(b"SF:"):
            current["sf"] = line[3:]
        elif line.startswith(b"VER:"):
            current["ver"] = line[4:]
        elif line.startswith(b"FNL:"):
            parts = line[4:].split(b",")
            if len(parts) == 3:
                current["functions"].append((parts[0], parts[1], parts[2]))
        elif line.startswith(b"FNA:"):
            parts = line[4:].split(b",", 2)
            if len(parts) == 3:
                current["aliases"].append((parts[0], parts[1], parts[2]))
        elif line.startswith(b"BRDA:"):
            parts = line[5:].split(b",")
            if len(parts) >= 4:
                current["branches"].append((parts[0], parts[1], parts[2], parts[3]))
        elif line.startswith(b"MCDC:"):
            parts = line[5:].split(b",", 5)
            if len(parts) == 6:
                current["mcdc"].append(tuple(parts))
        elif line.startswith(b"DA:"):
            body = line[3:]
            if b"," in body:
                line_no, rest = body.split(b",", 1)
                if b"," in rest:
                    count, checksum = rest.split(b",", 1)
                else:
                    count, checksum = rest, None
                current["das"].append((line_no, count, checksum))
        elif line.startswith((b"FNF:", b"FNH:", b"BRF:", b"BRH:", b"MCF:", b"MCH:", b"LF:", b"LH:")):
            tag, value = line.split(b":", 1)
            current["summaries"][tag.decode("ascii")] = value
        elif line == b"end_of_record":
            sections.append(current)
            current = None
    if current is not None:
        sections.append(current)
    return sections


def assert_writer_order_semantics(output: bytes, label: str) -> None:
    sections = parse_tracefile_sections(output)
    require(len(sections) == 3, f"{label}: expected 3 sections")
    tns = [section["tn"] for section in sections]
    require(tns == [b"a", b"m", b"z"], f"{label}: TN order drift {tns!r}")
    require(sections[0]["sf"] == b"src/a.c" and sections[1]["sf"] == b"src/a.c", f"{label}: first files not a.c")
    require(sections[2]["sf"] == b"src/z.c" and sections[2]["ver"] == b"v1", f"{label}: z section path/ver")
    aliases = sections[2]["aliases"]
    require(aliases == [(b"0", b"2", b"za"), (b"0", b"1", b"zb")], f"{label}: alias order/count {aliases!r}")
    branches = sections[2]["branches"]
    require(
        branches == [(b"2", b"0", b"e", b"1"), (b"2", b"0", b"e2", b"0")],
        f"{label}: BRDA order/content drift {branches!r}",
    )
    mcdc = sections[2]["mcdc"]
    require(mcdc and mcdc[0][2] == b"t" and mcdc[1][2] == b"f", f"{label}: mcdc sense order")
    require(sections[0]["summaries"].get("FNF") == b"1", f"{label}: recomputed FNF missing")
    require(b"FNF:9" not in output and b"LF:9" not in output, f"{label}: junk summaries retained")


def assert_writer_mcdc_group_semantics(output: bytes, label: str) -> None:
    sections = parse_tracefile_sections(output)
    require(len(sections) == 1, f"{label}: expected one section")
    groups = [entry[1] for entry in sections[0]["mcdc"]]
    require(groups[:2] == [b"10", b"10"], f"{label}: lexical group 10 first missing")
    require(b"U3" in groups, f"{label}: U-flag group missing")
    senses = [(entry[0], entry[1], entry[2], entry[3]) for entry in sections[0]["mcdc"] if entry[0] == b"2"]
    require(senses == [(b"2", b"1", b"t", b"2"), (b"2", b"1", b"f", b"1")], f"{label}: sense order {senses!r}")
    exprs = [entry[5] for entry in sections[0]["mcdc"] if entry[0] == b"3"]
    require(exprs == [b"a,b,c", b"a,b,c"], f"{label}: comma expression drift {exprs!r}")
    require(sections[0]["summaries"].get("MCF") == b"10" and sections[0]["summaries"].get("MCH") == b"6", f"{label}: mcdc totals")


def assert_writer_summary_semantics(output: bytes, label: str) -> None:
    expected = (
        b"TN:s\nSF:src/s.c\nFNL:0,1,1\nFNA:0,1,f\nFNF:1\nFNH:1\n"
        b"BRDA:1,0,e,1\nBRDA:1,0,e2,0\nBRF:2\nBRH:1\n"
        b"MCDC:1,1,t,1,0,c\nMCDC:1,1,f,0,0,c\nMCF:2\nMCH:1\n"
        b"DA:1,1\nDA:2,0\nLF:2\nLH:1\nend_of_record\n"
    )
    require(output == expected, f"{label}: summary rewrite drift")
    sections = parse_tracefile_sections(output)
    require(sections[0]["summaries"] == {"FNF": b"1", "FNH": b"1", "BRF": b"2", "BRH": b"1", "MCF": b"2", "MCH": b"1", "LF": b"2", "LH": b"1"}, f"{label}: summary map")


def assert_writer_comment_semantics(output: bytes, label: str) -> None:
    require(b"#" not in output, f"{label}: comments retained")
    require(b",chk" not in output, f"{label}: checksum retained")
    require(output == b"TN:c\nSF:src/c.c\nDA:1,1\nLF:1\nLH:1\nend_of_record\n", f"{label}: rewrite drift")


def assert_writer_forbidden_semantics(output: bytes, label: str) -> None:
    require(b"KF:" not in output and b"FN:" not in output and b"FNDA:" not in output, f"{label}: forbidden tags")
    require(b"end_of_record_and_junk" not in output, f"{label}: suffixed terminator")
    sections = parse_tracefile_sections(output)
    require(sections and sections[0]["sf"] == b"src/k.c", f"{label}: KF->SF path")
    require(sections[0]["functions"] == [(b"0", b"1", b"2")], f"{label}: FN rewrite")
    require(sections[0]["aliases"] == [(b"0", b"3", b"foo")], f"{label}: FNDA rewrite")


def assert_writer_fixedpoint_semantics(output: bytes, label: str) -> None:
    expected = (
        b"TN:s\nSF:src/s.c\nFNL:0,1,1\nFNA:0,1,f\nFNF:1\nFNH:1\n"
        b"BRDA:1,0,e,1\nBRDA:1,0,e2,0\nBRF:2\nBRH:1\n"
        b"MCDC:1,1,t,1,0,c\nMCDC:1,1,f,0,0,c\nMCF:2\nMCH:1\n"
        b"DA:1,1\nDA:2,0\nLF:2\nLH:1\nend_of_record\n"
    )
    require(output == expected, f"{label}: fixed-point drift")


def assert_xml2lcov_semantics(output: bytes, label: str) -> None:
    sections = parse_tracefile_sections(output)
    require(len(sections) == 1, f"{label}: section count")
    require(sections[0]["tn"] == b"xml" and sections[0]["sf"] == b"mod.py", f"{label}: header")
    require(sections[0]["branches"] == [(b"1", b"0", b"0", b"1"), (b"1", b"0", b"1", b"0")], f"{label}: branches")
    require(sections[0]["functions"] == [(b"0", b"1", b"1")], f"{label}: functions")
    require(sections[0]["aliases"] == [(b"0", b"3", b"foo")], f"{label}: aliases")
    require(sections[0]["das"] == [(b"1", b"3", None), (b"2", b"1", None)], f"{label}: DA")
    require(not sections[0]["mcdc"], f"{label}: unexpected MC/DC")
    # xml2lcov direct order is BR then FN then DA, then summaries.
    # Use line anchors so BRDA does not false-match DA:.
    brda_at = output.find(b"\nBRDA:")
    fnl_at = output.find(b"\nFNL:")
    da_at = output.find(b"\nDA:")
    require(0 <= brda_at < fnl_at < da_at, f"{label}: converter order")
    require(
        sections[0]["summaries"].get("LF") == b"2"
        and sections[0]["summaries"].get("LH") == b"2"
        and sections[0]["summaries"].get("BRF") == b"2"
        and sections[0]["summaries"].get("BRH") == b"1"
        and sections[0]["summaries"].get("FNF") == b"1"
        and sections[0]["summaries"].get("FNH") == b"1",
        f"{label}: converter summaries",
    )


def assert_py2lcov_no_functions_semantics(output: bytes, label: str) -> None:
    sections = parse_tracefile_sections(output)
    require(len(sections) == 1, f"{label}: section count")
    require(sections[0]["tn"] == b"py" and sections[0]["sf"] == b"mod.py", f"{label}: header")
    require(
        sections[0]["branches"] == [(b"1", b"0", b"0", b"1"), (b"1", b"0", b"1", b"0")],
        f"{label}: BRDA order/content drift {sections[0]['branches']!r}",
    )
    require(sections[0]["functions"] == [(b"0", b"1", b"1")], f"{label}: functions")
    require(sections[0]["aliases"] == [(b"0", b"3", b"foo")], f"{label}: aliases")
    require(sections[0]["das"] == [(b"1", b"3", None), (b"2", b"1", None)], f"{label}: DA")
    require(not sections[0]["mcdc"], f"{label}: unexpected MC/DC")
    # Direct py2lcov family/record order is BRDA block, then FNL/FNA, then DA.
    brda0_at = output.find(b"\nBRDA:1,0,0,1\n")
    brda1_at = output.find(b"\nBRDA:1,0,1,0\n")
    fnl_at = output.find(b"\nFNL:")
    fna_at = output.find(b"\nFNA:")
    da_at = output.find(b"\nDA:")
    require(
        0 <= brda0_at < brda1_at < fnl_at < fna_at < da_at,
        f"{label}: direct family/record order drift",
    )
    require(
        sections[0]["summaries"].get("LF") == b"2"
        and sections[0]["summaries"].get("LH") == b"2"
        and sections[0]["summaries"].get("BRF") == b"2"
        and sections[0]["summaries"].get("BRH") == b"1"
        and sections[0]["summaries"].get("FNF") == b"1"
        and sections[0]["summaries"].get("FNH") == b"1",
        f"{label}: converter summaries",
    )


def assert_py2lcov_with_functions_semantics(output: bytes, label: str) -> None:
    sections = parse_tracefile_sections(output)
    require(sections[0]["tn"] == b"py" and sections[0]["sf"] == b"./mod.py", f"{label}: header")
    require(sections[0]["functions"] == [(b"0", b"1", b"1"), (b"1", b"1", b"2")], f"{label}: functions")
    require(sections[0]["aliases"] == [(b"0", b"3", b"foo"), (b"1", b"1", b"foo")], f"{label}: aliases")
    require(sections[0]["summaries"].get("FNF") == b"2" and sections[0]["summaries"].get("FNH") == b"2", f"{label}: totals")


def assert_converter_rewrite_observational(output: bytes, label: str) -> None:
    """Observational rewrite shape only; not full M1-TF-052 semantic no-loss proof."""
    sections = parse_tracefile_sections(output)
    require(sections[0]["tn"] == b"xml" and sections[0]["sf"] == b"mod.py", f"{label}: header")
    require(sections[0]["functions"] == [(b"0", b"1", b"1")], f"{label}: functions")
    require(sections[0]["aliases"] == [(b"0", b"3", b"foo")], f"{label}: aliases")
    require(sections[0]["branches"] == [(b"1", b"0", b"0", b"1"), (b"1", b"0", b"1", b"0")], f"{label}: branches")
    require(sections[0]["das"] == [(b"1", b"3", None), (b"2", b"1", None)], f"{label}: DA")
    fnl_at = output.find(b"\nFNL:")
    brda_at = output.find(b"\nBRDA:")
    da_at = output.find(b"\nDA:")
    require(0 <= fnl_at < brda_at < da_at, f"{label}: canonical family order")
    require(not sections[0]["mcdc"], f"{label}: invented MC/DC")


def assert_writer_non_utf8_observational(output: bytes, label: str) -> None:
    """Observational SF invalid UTF-8 retention only; not full M1-TF-061 matrix."""
    sections = parse_tracefile_sections(output)
    require(len(sections) == 1, f"{label}: section count")
    require(sections[0]["tn"] == b"x", f"{label}: TN")
    require(sections[0]["sf"] == b"src/\xff.c", f"{label}: SF bytes")
    require(sections[0]["das"] == [(b"1", b"1", None)], f"{label}: DA")
    require(output == b"TN:x\nSF:src/\xff.c\nDA:1,1\nLF:1\nLH:1\nend_of_record\n", f"{label}: exact rewrite")



# ---------------------------------------------------------------------------
# Wave3 semantic closures (M1-TF-045 / 052 / 061)
# Independently fixed expected tables; group-completeness is mandatory for
# requirement binding. Validators must fail on reordered/lost records,
# field-byte changes, member omission, and identity swaps.
# ---------------------------------------------------------------------------

# M1-TF-045: parse-write-parse across four corpora (canonical, legacy,
# permissive, ignored-error). Expected outputs are the Oracle rewrite bytes
# fixed independently of free-form case labels.
TF045_CORPUS_MEMBERS: dict[str, dict[str, object]] = {
    "canonical": {
        "case_id": "writer-fixedpoint.canonical",
        "fixture_path": "fixtures/writer/fixedpoint.info",
        "expected_output": (
            b"TN:s\nSF:src/s.c\nFNL:0,1,1\nFNA:0,1,f\nFNF:1\nFNH:1\n"
            b"BRDA:1,0,e,1\nBRDA:1,0,e2,0\nBRF:2\nBRH:1\n"
            b"MCDC:1,1,t,1,0,c\nMCDC:1,1,f,0,0,c\nMCF:2\nMCH:1\n"
            b"DA:1,1\nDA:2,0\nLF:2\nLH:1\nend_of_record\n"
        ),
        "section_facts": {
            "tn": b"s",
            "sf": b"src/s.c",
            "ver": None,
            "functions": [(b"0", b"1", b"1")],
            "aliases": [(b"0", b"1", b"f")],
            "branches": [(b"1", b"0", b"e", b"1"), (b"1", b"0", b"e2", b"0")],
            "mcdc": [
                (b"1", b"1", b"t", b"1", b"0", b"c"),
                (b"1", b"1", b"f", b"0", b"0", b"c"),
            ],
            "das": [(b"1", b"1", None), (b"2", b"0", None)],
            "summaries": {
                "FNF": b"1",
                "FNH": b"1",
                "BRF": b"2",
                "BRH": b"1",
                "MCF": b"2",
                "MCH": b"1",
                "LF": b"2",
                "LH": b"1",
            },
        },
    },
    "legacy": {
        "case_id": "legacy.canonical",
        "fixture_path": "fixtures/legacy.info",
        "expected_output": (
            b"TN:legacy\nSF:src/legacy.c\n"
            b"FNL:0,10,20\nFNA:0,4,legacy_main\n"
            b"FNL:1,30,30\nFNA:1,0,legacy_helper\n"
            b"FNF:2\nFNH:1\n"
            b"DA:10,4\nDA:20,1\nDA:30,0\n"
            b"LF:3\nLH:2\nend_of_record\n"
        ),
        "section_facts": {
            "tn": b"legacy",
            "sf": b"src/legacy.c",
            "ver": None,
            "functions": [(b"0", b"10", b"20"), (b"1", b"30", b"30")],
            "aliases": [
                (b"0", b"4", b"legacy_main"),
                (b"1", b"0", b"legacy_helper"),
            ],
            "branches": [],
            "mcdc": [],
            "das": [
                (b"10", b"4", None),
                (b"20", b"1", None),
                (b"30", b"0", None),
            ],
            "summaries": {"FNF": b"2", "FNH": b"1", "LF": b"3", "LH": b"2"},
        },
    },
    "permissive": {
        "case_id": "permissive-prefix.canonical",
        "fixture_path": "fixtures/permissive-prefix.info",
        "expected_output": (
            b"TN:,diff\nSF:src/permissive.c\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"
        ),
        "section_facts": {
            "tn": b",diff",
            "sf": b"src/permissive.c",
            "ver": None,
            "functions": [],
            "aliases": [],
            "branches": [],
            "mcdc": [],
            "das": [(b"1", b"1", None)],
            "summaries": {"LF": b"1", "LH": b"1"},
        },
    },
    "ignored_error": {
        "case_id": "wave2-unknown-tags.ignore-format",
        "fixture_path": "fixtures/wave2/unknown-tags.info",
        "expected_output": b"TN:u\nSF:src/u.c\nDA:1,1\nLF:1\nLH:1\nend_of_record\n",
        "section_facts": {
            "tn": b"u",
            "sf": b"src/u.c",
            "ver": None,
            "functions": [],
            "aliases": [],
            "branches": [],
            "mcdc": [],
            "das": [(b"1", b"1", None)],
            "summaries": {"LF": b"1", "LH": b"1"},
        },
    },
}
TF045_REQUIRED_MEMBERS = frozenset(TF045_CORPUS_MEMBERS)
TF045_CASE_IDS = frozenset(
    str(member["case_id"]) for member in TF045_CORPUS_MEMBERS.values()
)

# M1-TF-052: converter input semantic facts (authored from XML/Python sources
# independently of LCOV output) bound to rewrite output section model.
TF052_SOURCE_FACTS: dict[str, object] = {
    "xml_filename": b"mod.py",
    "xml_testname": b"xml",
    "method_name": b"foo",
    "method_line": b"1",
    "method_hits": b"3",
    "line_hits": ((b"1", b"3"), (b"2", b"1")),
    "branch_line": b"1",
    "branch_coverage_taken": 1,
    "branch_coverage_total": 2,
    "python_def_name": b"foo",
}
TF052_REWRITE_CASE_ID = "converter-coverage.canonical-rewrite"
TF052_DIRECT_CASE_ID = "converter-coverage.xml2lcov"
TF052_REQUIRED_CASE_IDS = frozenset({TF052_REWRITE_CASE_ID, TF052_DIRECT_CASE_ID})
TF052_EXPECTED_REWRITE = (
    b"TN:xml\nSF:mod.py\nFNL:0,1,1\nFNA:0,3,foo\nFNF:1\nFNH:1\n"
    b"BRDA:1,0,0,1\nBRDA:1,0,1,0\nBRF:2\nBRH:1\n"
    b"DA:1,3\nDA:2,1\nLF:2\nLH:2\nend_of_record\n"
)

# M1-TF-061: invalid/non-ASCII byte matrix across TN, SF, function alias,
# branch expression, MC/DC expression/condition, and VER. TN is sanitized by
# Oracle (non-word bytes -> '_'); other fields retain raw bytes. Current-form
# function identity is carried by FNA alias bytes (FNL is index/range only).
TF061_CASE_ID = "bytes-non-utf8.canonical"
TF061_REQUIRED_FIELDS = frozenset(
    {
        "tn",
        "sf",
        "function_alias",
        "branch_expression",
        "mcdc_expression",
        "mcdc_condition",
        "ver",
    }
)
TF061_FIELD_EXPECTED: dict[str, bytes] = {
    "tn": b"test__",  # input TN:test-\xff sanitized
    "sf": b"src/path-\xfe.c",
    "function_alias": b"alias-\xfc",
    "branch_expression": b"branch-\xfb",
    "mcdc_expression": b"mcdc-\xfa",
    "mcdc_condition": b"0",  # condition index on both senses
    "ver": b"revision-\xfd",
}
TF061_EXPECTED_OUTPUT = (
    b"TN:test__\nSF:src/path-\xfe.c\nVER:revision-\xfd\n"
    b"FNL:0,1,1\nFNA:0,1,alias-\xfc\nFNF:1\nFNH:1\n"
    b"BRDA:1,0,branch-\xfb,1\nBRDA:1,0,other,0\nBRF:2\nBRH:1\n"
    b"MCDC:1,1,t,1,0,mcdc-\xfa\nMCDC:1,1,f,0,0,mcdc-\xfa\nMCF:2\nMCH:1\n"
    b"DA:1,1\nLF:1\nLH:1\nend_of_record\n"
)


def _section_model_matches(section: dict[str, object], facts: dict[str, object], label: str) -> None:
    require(section["tn"] == facts["tn"], f"{label}: TN drift {section['tn']!r}")
    require(section["sf"] == facts["sf"], f"{label}: SF drift {section['sf']!r}")
    require(section.get("ver") == facts.get("ver"), f"{label}: VER drift")
    require(section["functions"] == facts["functions"], f"{label}: functions drift")
    require(section["aliases"] == facts["aliases"], f"{label}: aliases drift")
    require(section["branches"] == facts["branches"], f"{label}: branches drift")
    require(section["mcdc"] == facts["mcdc"], f"{label}: mcdc drift")
    require(section["das"] == facts["das"], f"{label}: DA drift")
    require(section["summaries"] == facts["summaries"], f"{label}: summaries drift")


def assert_tf045_member_semantics(output: bytes, member_name: str, label: str) -> None:
    """Validate one M1-TF-045 corpus member against the independent expected table."""
    require(member_name in TF045_CORPUS_MEMBERS, f"{label}: unknown TF-045 member {member_name}")
    member = TF045_CORPUS_MEMBERS[member_name]
    expected = member["expected_output"]
    require(isinstance(expected, (bytes, bytearray)), f"{label}: expected_output type")
    require(output == expected, f"{label}: parse-write output drift for {member_name}")
    sections = parse_tracefile_sections(output)
    require(len(sections) == 1, f"{label}: section count for {member_name}")
    _section_model_matches(sections[0], member["section_facts"], f"{label}.{member_name}")
    # parse-write-parse: re-parse of rewrite must equal the same section model
    reparsed = parse_tracefile_sections(output)
    require(reparsed == sections, f"{label}: parse-write-parse model drift for {member_name}")


def assert_tf045_group_completeness(
    observed_by_id: dict[str, dict[str, object]],
    decode_output,
    label: str = "M1-TF-045",
) -> None:
    """Fail unless every required corpus member is present and semantically valid."""
    present = set()
    for member_name, member in TF045_CORPUS_MEMBERS.items():
        case_id = str(member["case_id"])
        require(case_id in observed_by_id, f"{label}: missing corpus case {case_id}")
        observation = observed_by_id[case_id]
        require(observation.get("exit_status") == 0, f"{label}: {case_id} exit")
        output_identity = observation.get("output")
        require(
            isinstance(output_identity, dict) and output_identity.get("exists") is True,
            f"{label}: {case_id} missing output",
        )
        output = decode_output(output_identity, f"{label}.{case_id}")
        assert_tf045_member_semantics(output, member_name, f"{label}.{case_id}")
        present.add(member_name)
    require(present == TF045_REQUIRED_MEMBERS, f"{label}: incomplete corpus group {present!r}")


def assert_tf052_source_to_output_semantics(output: bytes, label: str) -> None:
    """Bind converter XML/Python source facts to rewritten LCOV section model.

    Does not use substring-only claims: every source fact is checked against
    the structured section model and the independent expected rewrite bytes.
    """
    require(output == TF052_EXPECTED_REWRITE, f"{label}: rewrite snapshot drift")
    sections = parse_tracefile_sections(output)
    require(len(sections) == 1, f"{label}: section count")
    section = sections[0]
    require(section["tn"] == TF052_SOURCE_FACTS["xml_testname"], f"{label}: TN from -t")
    require(section["sf"] == TF052_SOURCE_FACTS["xml_filename"], f"{label}: SF from XML filename")
    require(
        section["functions"]
        == [(b"0", TF052_SOURCE_FACTS["method_line"], TF052_SOURCE_FACTS["method_line"])],
        f"{label}: function range from method line",
    )
    require(
        section["aliases"]
        == [
            (
                b"0",
                TF052_SOURCE_FACTS["method_hits"],
                TF052_SOURCE_FACTS["method_name"],
            )
        ],
        f"{label}: alias name/hits from method",
    )
    require(
        section["aliases"][0][2] == TF052_SOURCE_FACTS["python_def_name"],
        f"{label}: alias must match Python def name",
    )
    expected_branches = [
        (TF052_SOURCE_FACTS["branch_line"], b"0", b"0", b"1"),
        (TF052_SOURCE_FACTS["branch_line"], b"0", b"1", b"0"),
    ]
    require(section["branches"] == expected_branches, f"{label}: branch identity from condition-coverage")
    require(
        len(section["branches"]) == TF052_SOURCE_FACTS["branch_coverage_total"],
        f"{label}: branch total",
    )
    taken = sum(1 for branch in section["branches"] if branch[3] not in (b"0", b"-", b""))
    require(taken == TF052_SOURCE_FACTS["branch_coverage_taken"], f"{label}: branch taken count")
    expected_das = [
        (line, hits, None) for line, hits in TF052_SOURCE_FACTS["line_hits"]
    ]
    require(section["das"] == expected_das, f"{label}: DA hits from XML lines")
    require(not section["mcdc"], f"{label}: converters must not invent MC/DC")
    require(
        section["summaries"].get("LF") == b"2"
        and section["summaries"].get("LH") == b"2"
        and section["summaries"].get("BRF") == b"2"
        and section["summaries"].get("BRH") == b"1"
        and section["summaries"].get("FNF") == b"1"
        and section["summaries"].get("FNH") == b"1",
        f"{label}: recomputed summaries",
    )
    # Canonical family order after lcov rewrite: FNL before BRDA before DA.
    fnl_at = output.find(b"\nFNL:")
    brda_at = output.find(b"\nBRDA:")
    da_at = output.find(b"\nDA:")
    require(0 <= fnl_at < brda_at < da_at, f"{label}: canonical family order")
    # parse-write snapshot stability
    require(
        parse_tracefile_sections(output) == sections,
        f"{label}: parse-write-parse snapshot drift",
    )


def assert_tf052_direct_preserves_semantics(direct: bytes, rewrite: bytes, label: str) -> None:
    """Direct converter output and canonical rewrite must share semantic model."""
    direct_sections = parse_tracefile_sections(direct)
    rewrite_sections = parse_tracefile_sections(rewrite)
    require(len(direct_sections) == 1 and len(rewrite_sections) == 1, f"{label}: section count")
    dsec, rsec = direct_sections[0], rewrite_sections[0]
    for key in ("tn", "sf", "functions", "aliases", "branches", "mcdc", "das"):
        require(dsec[key] == rsec[key], f"{label}: direct/rewrite {key} semantic loss")
    # Summaries may differ in emission order but must match values.
    require(dsec["summaries"] == rsec["summaries"], f"{label}: summary semantic loss")


def assert_tf052_group_completeness(
    observed_by_id: dict[str, dict[str, object]],
    decode_output,
    label: str = "M1-TF-052",
) -> None:
    for case_id in TF052_REQUIRED_CASE_IDS:
        require(case_id in observed_by_id, f"{label}: missing case {case_id}")
        observation = observed_by_id[case_id]
        require(observation.get("exit_status") == 0, f"{label}: {case_id} exit")
        require(
            observation.get("output", {}).get("exists") is True,
            f"{label}: {case_id} missing output",
        )
    rewrite = decode_output(
        observed_by_id[TF052_REWRITE_CASE_ID]["output"], f"{label}.rewrite"
    )
    direct = decode_output(
        observed_by_id[TF052_DIRECT_CASE_ID]["output"], f"{label}.direct"
    )
    assert_tf052_source_to_output_semantics(rewrite, f"{label}.rewrite")
    assert_tf052_direct_preserves_semantics(direct, rewrite, f"{label}.no-loss")


def extract_tf061_field_bytes(output: bytes) -> dict[str, bytes]:
    sections = parse_tracefile_sections(output)
    require(len(sections) == 1, "M1-TF-061: section count")
    section = sections[0]
    require(section["aliases"], "M1-TF-061: missing function alias")
    require(section["branches"], "M1-TF-061: missing branch expression")
    require(section["mcdc"], "M1-TF-061: missing MC/DC expression")
    require(section["ver"] is not None, "M1-TF-061: missing VER")
    return {
        "tn": section["tn"],
        "sf": section["sf"],
        "function_alias": section["aliases"][0][2],
        "branch_expression": section["branches"][0][2],
        "mcdc_expression": section["mcdc"][0][5],
        "mcdc_condition": section["mcdc"][0][4],
        "ver": section["ver"],
    }


def assert_tf061_field_matrix(output: bytes, label: str) -> None:
    """Validate the full non-ASCII/invalid-UTF-8 field matrix for M1-TF-061."""
    require(output == TF061_EXPECTED_OUTPUT, f"{label}: output snapshot drift")
    fields = extract_tf061_field_bytes(output)
    require(set(fields) == TF061_REQUIRED_FIELDS, f"{label}: field group incomplete {set(fields)!r}")
    for field_name, expected in TF061_FIELD_EXPECTED.items():
        actual = fields[field_name]
        require(actual == expected, f"{label}: {field_name} byte drift {actual!r} != {expected!r}")
        if field_name in {"sf", "function_alias", "branch_expression", "mcdc_expression", "ver"}:
            # non-TN retained fields must keep at least one non-ASCII byte from the fixture
            require(any(byte > 127 for byte in actual), f"{label}: {field_name} lost non-ASCII")
    # TN sanitization: non-word input bytes become '_' and must not retain 0xff
    require(b"\xff" not in fields["tn"], f"{label}: TN retained invalid word byte")
    require(fields["tn"] == b"test__", f"{label}: TN sanitization drift")
    sections = parse_tracefile_sections(output)
    require(
        sections[0]["aliases"] == [(b"0", b"1", TF061_FIELD_EXPECTED["function_alias"])],
        f"{label}: function alias model",
    )
    require(
        sections[0]["branches"][0]
        == (b"1", b"0", TF061_FIELD_EXPECTED["branch_expression"], b"1"),
        f"{label}: branch identity/expression model",
    )
    require(
        sections[0]["mcdc"][0][5] == TF061_FIELD_EXPECTED["mcdc_expression"],
        f"{label}: MC/DC expression model",
    )
    require(
        sections[0]["mcdc"][0][2] in (b"t", b"f")
        and sections[0]["mcdc"][0][4] == TF061_FIELD_EXPECTED["mcdc_condition"],
        f"{label}: MC/DC condition index/sense",
    )
    # both senses share the same non-ASCII expression and condition index
    require(
        sections[0]["mcdc"][0][5] == sections[0]["mcdc"][1][5]
        and sections[0]["mcdc"][0][4] == sections[0]["mcdc"][1][4],
        f"{label}: MC/DC condition pair coherence",
    )


def assert_tf061_group_completeness(
    observed_by_id: dict[str, dict[str, object]],
    decode_output,
    label: str = "M1-TF-061",
) -> None:
    require(TF061_CASE_ID in observed_by_id, f"{label}: missing case {TF061_CASE_ID}")
    observation = observed_by_id[TF061_CASE_ID]
    require(observation.get("exit_status") == 0, f"{label}: exit")
    require(observation.get("output", {}).get("exists") is True, f"{label}: missing output")
    output = decode_output(observation["output"], f"{label}.output")
    assert_tf061_field_matrix(output, label)
    # Every required field member must be present (explicit group check).
    fields = extract_tf061_field_bytes(output)
    missing = TF061_REQUIRED_FIELDS - set(fields)
    require(not missing, f"{label}: missing field members {missing!r}")


def mutate_tf045_lost_record(output: bytes) -> bytes:
    """Drop the first DA record to prove lost-record rejection."""
    for marker in (b"DA:1,1\n", b"DA:10,4\n", b"DA:1,1\n"):
        if marker in output:
            return output.replace(marker, b"", 1)
    # last resort: drop any DA line
    import re
    return re.sub(br"DA:[^\n]*\n", b"", output, count=1)


def mutate_tf045_reordered_records(output: bytes) -> bytes:
    """Swap two DA records when present; otherwise swap FNL/FNA order."""
    if b"DA:1,1\nDA:2,0\n" in output:
        return output.replace(b"DA:1,1\nDA:2,0\n", b"DA:2,0\nDA:1,1\n", 1)
    if b"FNL:0,10,20\nFNA:0,4,legacy_main\nFNL:1,30,30\nFNA:1,0,legacy_helper\n" in output:
        return output.replace(
            b"FNL:0,10,20\nFNA:0,4,legacy_main\nFNL:1,30,30\nFNA:1,0,legacy_helper\n",
            b"FNL:1,30,30\nFNA:1,0,legacy_helper\nFNL:0,10,20\nFNA:0,4,legacy_main\n",
            1,
        )
    return output.replace(b"SF:", b"SF:mut-", 1)


def mutate_tf045_field_bytes(output: bytes) -> bytes:
    return output.replace(b"SF:", b"SF:X", 1)


def mutate_tf052_identity_swap(output: bytes) -> bytes:
    """Swap method alias identity with a different name."""
    return output.replace(b"FNA:0,3,foo\n", b"FNA:0,3,bar\n", 1)


def mutate_tf052_member_omission(output: bytes) -> bytes:
    """Omit one DA line record."""
    return output.replace(b"DA:2,1\n", b"", 1)


def mutate_tf061_field_bytes(output: bytes, field: str) -> bytes:
    if field == "tn":
        return output.replace(b"TN:test__\n", b"TN:test_x\n", 1)
    if field == "sf":
        return output.replace(b"\xfe", b"x", 1)
    if field == "function_alias":
        return output.replace(b"\xfc", b"y", 1)
    if field == "branch_expression":
        return output.replace(b"\xfb", b"z", 1)
    if field == "mcdc_expression":
        return output.replace(b"\xfa", b"w", 1)
    if field == "mcdc_condition":
        return output.replace(b",0,mcdc-", b",1,mcdc-", 1)
    if field == "ver":
        return output.replace(b"\xfd", b"v", 1)
    raise ValueError(f"unknown TF-061 field {field}")


def assert_identity_self_hash(identity: dict[str, object], label: str) -> None:
    """Require identity base64/size/sha are self-consistent and reject mutated hashes."""
    verify_identity(identity, label)
    data = decode_identity(identity, label)
    require(hashlib.sha256(data).hexdigest() == identity["sha256"], f"{label}: self-hash mismatch")
    require(len(data) == identity["byte_size"], f"{label}: self-size mismatch")
    poisoned = dict(identity)
    poisoned["sha256"] = "0" * 64
    try:
        verify_identity(poisoned, f"{label} poisoned")
    except ValueError:
        return
    raise ValueError(f"{label}: poisoned sha256 still accepted")
