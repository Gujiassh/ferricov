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
    require(sections[0]["tn"] == b"py" and sections[0]["sf"] == b"mod.py", f"{label}: header")
    require(len(sections[0]["functions"]) == 1 and len(sections[0]["aliases"]) == 1, f"{label}: derived extra")
    require(not sections[0]["mcdc"], f"{label}: unexpected MC/DC")


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
