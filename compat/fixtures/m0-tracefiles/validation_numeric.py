"""Numeric snapshot, policy, and semantic registry validators."""

from __future__ import annotations

from validation_common import (
    assert_single_testcase_parity,
    decode_identity,
    require,
)


NUMERIC_FIXTURE_IDS = (
    "numeric-boundary",
    "numeric-extra-spellings",
    "numeric-format-atoms",
    "numeric-negative",
    "numeric-nonnumeric",
    "numeric-malformed-exponent",
    "numeric-excessive",
    "numeric-zero-line",
    "numeric-negative-inf",
    "numeric-signed-zero",
    "numeric-fnda-negative",
    "numeric-fnda-nonnumeric",
    "numeric-fna-nonnumeric",
    "numeric-fna-malformed-exponent",
    "numeric-brda-nonnumeric",
    "numeric-mcdc-nondigit",
    "numeric-zero-brda",
    "numeric-zero-mcdc",
    "numeric-zero-fn",
    "numeric-zero-fn-end",
    "numeric-invalid-fnl-fields",
    "numeric-inf-excessive",
    "numeric-function-excessive",
    "numeric-function-source",
    "checksum-match",
    "checksum-mismatch",
    "checksum-missing",
    "checksum-duplicate",
    "checksum-source-cs",
)
CHECKSUM_SOURCE_SHA256 = "996137ced8354c0b4b3730a96a1480001118944458519ab2d63f519546de97a4"
CHECKSUM_SOURCE_BYTES = b"int x = 1;\n"
CHECKSUM_MD5_BASE64 = "AVO7Y115x231sZo9ymlVFA"



def _source_by_name(document: dict[str, object], filename: str) -> dict[str, object]:
    sources = document.get("sources")
    require(isinstance(sources, list), "snapshot sources must be a list")
    matches = [source for source in sources if source.get("filename") == filename]
    require(len(matches) == 1, f"expected exactly one source {filename}")
    return matches[0]


def _single_source_by_name(document: dict[str, object], filename: str) -> dict[str, object]:
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 1, f"expected one source {filename}")
    return _source_by_name(document, filename)


def _assert_json_number_value(value: object, label: str) -> None:
    require(
        isinstance(value, (int, float, str)) and not isinstance(value, bool),
        f"{label}: value must be int/float/str JSON number encoding",
    )
    if isinstance(value, float):
        require(value == value and value not in (float("inf"), float("-inf")), f"{label}: raw nonfinite float forbidden")


def validate_numeric_boundary_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "numeric-boundary snapshot kind mismatch")
    require(document.get("schema_version") == 1, "numeric-boundary snapshot schema mismatch")
    require(document.get("input") == "input.info", "numeric-boundary single-input identity must use input")
    require("inputs" not in document, "numeric-boundary must not emit multi-input inputs field")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 15, "numeric-boundary must retain 15 sources")
    expected = {
        "src/numeric-00.c": 0,
        "src/numeric-01.c": "+0",
        "src/numeric-02.c": "-0",
        "src/numeric-03.c": 1,
        "src/numeric-04.c": 1.5,
        "src/numeric-05.c": ".5",
        "src/numeric-06.c": "1.",
        "src/numeric-07.c": "1e3",
        "src/numeric-08.c": "1E-3",
        "src/numeric-09.c": "NaN",
        "src/numeric-10.c": "Inf",
        "src/numeric-11.c": "Infinity",
        "src/numeric-12.c": " 1",
        "src/numeric-13.c": 9007199254740993,
        "src/numeric-14.c": 18446744073709551615,
    }
    expected_hits = {
        filename: 0 if filename in {
            "src/numeric-00.c",
            "src/numeric-01.c",
            "src/numeric-02.c",
            "src/numeric-09.c",
        } else 1
        for filename in expected
    }
    categories = {
        "finite_simple": {"src/numeric-00.c", "src/numeric-03.c", "src/numeric-04.c", "src/numeric-13.c", "src/numeric-14.c"},
        "finite_string": {"src/numeric-01.c", "src/numeric-02.c", "src/numeric-05.c", "src/numeric-06.c", "src/numeric-07.c", "src/numeric-08.c", "src/numeric-12.c"},
        "nan": {"src/numeric-09.c"},
        "inf": {"src/numeric-10.c", "src/numeric-11.c"},
    }
    seen = set()
    for source in sources:
        filename = source["filename"]
        seen.add(filename)
        require(filename in expected, f"unexpected numeric-boundary source: {filename}")
        testcase = filename.removeprefix("src/").removesuffix(".c").replace("-", "_")
        assert_single_testcase_parity(source, testcase, f"numeric-boundary {filename}")
        aggregate = source["aggregate"]
        empty_function = {"found": 0, "hit": 0, "functions": {}}
        empty_branch = {"found": 0, "hit": 0, "lines": {}}
        empty_mcdc = {"found": 0, "hit": 0, "lines": {}}
        value = expected[filename]
        expected_line = {"found": 1, "hit": expected_hits[filename], "lines": {"1": value}}
        require(
            aggregate
            == {
                "line": expected_line,
                "function": empty_function,
                "branch": empty_branch,
                "mcdc": empty_mcdc,
            },
            f"numeric-boundary {filename} aggregate/testcase state drift",
        )
        _assert_json_number_value(value, f"numeric-boundary {filename}")
        require(value == expected[filename], f"numeric-boundary {filename} value mismatch: {value!r}")
        if filename in categories["nan"] | categories["inf"]:
            require(isinstance(value, str), f"{filename}: nonfinite must be JSON string")
            require(value in {"NaN", "nan", "Inf", "+Inf", "Infinity", "-Inf"}, f"{filename}: unexpected nonfinite spelling {value!r}")
        if filename in categories["finite_simple"]:
            require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{filename}: simple finite must stay numeric JSON")
        if filename in categories["finite_string"]:
            require(isinstance(value, str), f"{filename}: non-simple finite must stay string")
    require(seen == set(expected), f"numeric-boundary source set drift: {sorted(seen ^ set(expected))}")


def validate_numeric_format_atoms_snapshot(document: dict[str, object], *, with_excessive_threshold: bool) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "format-atoms snapshot kind mismatch")
    require(document.get("schema_version") == 1, "format-atoms snapshot schema mismatch")
    require(document.get("input") == "input.info", "format-atoms single-input identity must use input")
    require("inputs" not in document, "format-atoms must not emit multi-input inputs field")
    source = _single_source_by_name(document, "a.cpp")
    assert_single_testcase_parity(source, "", "format-atoms")
    expected = {
        "line": {
            "found": 7,
            "hit": 4,
            "lines": {"1": 1, "2": 1, "3": 1, "4": 0, "10": 0, "11": 0, "12": "1.0e+19"},
        },
        "function": {
            "found": 6,
            "hit": 2,
            "functions": {
                "1": {
                    "name": "fcn",
                    "start": 1,
                    "end": 2,
                    "hit": 1.5e20,
                    "aliases": {"alias": 0, "alias2": 0, "alias3": 1.5e20, "fcn": 0},
                },
                "3": {
                    "name": "noCommonAlias",
                    "start": 3,
                    "end": 3,
                    "hit": 1,
                    "aliases": {"noCommonAlias": 1},
                },
                "11": {
                    "name": "onlyA",
                    "start": 11,
                    "end": 11,
                    "hit": 0,
                    "aliases": {"onlyA": 0},
                },
            },
        },
        "branch": {
            "found": 8,
            "hit": 2,
            "lines": {
                "1": {
                    "blocks": [
                        {
                            "idx": 0,
                            "signature": "bbb",
                            "elements": [
                                {"id": 0, "taken": 1, "count": 1, "expr": None, "type": "", "excluded": False},
                                {"id": 1, "taken": 0, "count": 0, "expr": None, "type": "", "excluded": False},
                                {"id": 2, "taken": "-", "count": 0, "expr": None, "type": "", "excluded": False},
                            ],
                        },
                        {
                            "idx": 1,
                            "signature": "bbb",
                            "elements": [
                                {"id": 0, "taken": 0, "count": 0, "expr": None, "type": "", "excluded": False},
                                {"id": 1, "taken": 1.67e20, "count": 1.67e20, "expr": None, "type": "", "excluded": False},
                                {"id": 2, "taken": 0, "count": 0, "expr": "1", "type": "", "excluded": False},
                            ],
                        },
                    ]
                },
                "11": {
                    "blocks": [
                        {
                            "idx": 0,
                            "signature": "bb",
                            "elements": [
                                {"id": 0, "taken": 0, "count": 0, "expr": None, "type": "", "excluded": False},
                                {"id": 1, "taken": "-0", "count": "-0", "expr": None, "type": "", "excluded": False},
                            ],
                        }
                    ]
                },
            },
        },
        "mcdc": {"found": 0, "hit": 0, "lines": {}},
    }
    require(source["aggregate"] == expected, "format-atoms aggregate state drift")
    # Threshold is recorded only by inspector argv/runtime; model values remain identical.
    require(with_excessive_threshold in (True, False), "format-atoms threshold flag required")


def validate_numeric_signed_zero_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "signed-zero snapshot kind mismatch")
    require(document.get("schema_version") == 1, "signed-zero snapshot schema mismatch")
    require(document.get("input") == "input.info", "signed-zero single-input identity must use input")
    require("inputs" not in document, "signed-zero must not emit multi-input inputs field")
    source = _single_source_by_name(document, "src/numeric-signed-zero.c")
    assert_single_testcase_parity(source, "numeric_signed_zero", "signed-zero")
    require(
        source["aggregate"]
        == {
            "line": {"found": 2, "hit": 1, "lines": {"1": "-0", "2": 1}},
            "function": {"found": 0, "hit": 0, "functions": {}},
            "branch": {
                "found": 2,
                "hit": 1,
                "lines": {
                    "2": {
                        "blocks": [
                            {
                                "idx": 0,
                                "signature": "bb",
                                "elements": [
                                    {"id": 0, "taken": "-0", "count": "-0", "expr": "expr", "type": "", "excluded": False},
                                    {"id": 1, "taken": 1, "count": 1, "expr": "expr2", "type": "", "excluded": False},
                                ],
                            }
                        ]
                    }
                },
            },
            "mcdc": {"found": 0, "hit": 0, "lines": {}},
        },
        "signed-zero aggregate state drift",
    )



def validate_numeric_extra_spellings_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "extra-spellings snapshot kind mismatch")
    require(document.get("schema_version") == 1, "extra-spellings snapshot schema mismatch")
    require(document.get("input") == "input.info", "extra-spellings single-input identity must use input")
    require("inputs" not in document, "extra-spellings must not emit multi-input inputs field")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 3, "extra-spellings must retain 3 sources")
    expected = {
        "src/extra-00.c": "+1",
        "src/extra-01.c": "nan",
        "src/extra-02.c": "+Inf",
    }
    seen: set[str] = set()
    for source in sources:
        filename = source["filename"]
        require(filename in expected, f"unexpected extra-spellings source: {filename}")
        seen.add(filename)
        testcase = filename.removeprefix("src/").removesuffix(".c").replace("-", "_")
        assert_single_testcase_parity(source, testcase, f"extra-spellings {filename}")
        expected_hit = 0 if filename == "src/extra-01.c" else 1
        value = expected[filename]
        require(
            source["aggregate"]
            == {
                "line": {"found": 1, "hit": expected_hit, "lines": {"1": value}},
                "function": {"found": 0, "hit": 0, "functions": {}},
                "branch": {"found": 0, "hit": 0, "lines": {}},
                "mcdc": {"found": 0, "hit": 0, "lines": {}},
            },
            f"extra-spellings {filename} aggregate state drift",
        )
        _assert_json_number_value(value, f"extra-spellings {filename}")
        if filename in {"src/extra-01.c", "src/extra-02.c"}:
            require(isinstance(value, str), f"{filename}: nonfinite must be JSON string")
        if filename == "src/extra-00.c":
            require(isinstance(value, str), f"{filename}: +1 must stay string spelling")
    require(seen == set(expected), f"extra-spellings source set drift: {sorted(seen ^ set(expected))}")


def validate_numeric_negative_inf_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "negative-inf snapshot kind mismatch")
    require(document.get("schema_version") == 1, "negative-inf snapshot schema mismatch")
    source = _single_source_by_name(document, "src/numeric-negative-inf.c")
    assert_single_testcase_parity(source, "numeric_negative_inf", "negative-inf")
    require(
        source["aggregate"]
        == {
            "line": {"found": 2, "hit": 1, "lines": {"1": 0, "2": 1}},
            "function": {"found": 0, "hit": 0, "functions": {}},
            "branch": {"found": 0, "hit": 0, "lines": {}},
            "mcdc": {"found": 0, "hit": 0, "lines": {}},
        },
        "negative-inf recovered aggregate state drift",
    )


def validate_recovered_function_snapshot(
    document: dict[str, object],
    *,
    label: str,
    filename: str,
    testcase: str,
    expected_lines: dict[str, int],
    location: str,
    name: str,
    start: int,
    end: int,
    count: int,
) -> None:
    source = _single_source_by_name(document, filename)
    assert_single_testcase_parity(source, testcase, label)
    line = {"found": len(expected_lines), "hit": sum(value != 0 for value in expected_lines.values()), "lines": expected_lines}
    function = {
        "found": 1,
        "hit": 1 if count else 0,
        "functions": {
            location: {
                "name": name,
                "start": start,
                "end": end,
                "hit": count,
                "aliases": {name: count},
            }
        },
    }
    require(
        source["aggregate"]
        == {
            "line": line,
            "function": function,
            "branch": {"found": 0, "hit": 0, "lines": {}},
            "mcdc": {"found": 0, "hit": 0, "lines": {}},
        },
        f"{label}: recovered aggregate state drift",
    )


def validate_numeric_fna_nonnumeric_snapshot(document: dict[str, object]) -> None:
    validate_recovered_function_snapshot(
        document,
        label="fna-nonnumeric",
        filename="src/numeric-fna-nonnumeric.c",
        testcase="numeric_fna_nonnumeric",
        expected_lines={"1": 0},
        location="1",
        name="alias",
        start=1,
        end=1,
        count=0,
    )


def validate_numeric_zero_fn_end_snapshot(document: dict[str, object]) -> None:
    validate_recovered_function_snapshot(
        document,
        label="zero-fn-end",
        filename="src/numeric-zero-fn-end.c",
        testcase="numeric_zero_fn_end",
        expected_lines={"1": 0},
        location="1",
        name="name",
        start=1,
        end=0,
        count=0,
    )


def validate_numeric_invalid_fnl_fields_snapshot(document: dict[str, object]) -> None:
    validate_recovered_function_snapshot(
        document,
        label="invalid-fnl-fields",
        filename="src/numeric-invalid-fnl-fields.c",
        testcase="numeric_invalid_fnl_fields",
        expected_lines={"1": 0},
        location="1",
        name="valid",
        start=1,
        end=1,
        count=0,
    )


def validate_functions_zero_start_snapshot(document: dict[str, object]) -> None:
    validate_recovered_function_snapshot(
        document,
        label="functions-zero-start",
        filename="src/fn-zero-start.c",
        testcase="fn_zero_start",
        expected_lines={"1": 1, "5": 1},
        location="0",
        name="zero_start",
        start=0,
        end=5,
        count=1,
    )


ADDED_OUTPUT_EXPECTATIONS = {
    "numeric-format-atoms.excessive-stop-on-error-0": True,
    "numeric-format-atoms.excessive-stop-on-error-1": False,
    "numeric-fna-malformed-exponent.ignore-format": True,
    "numeric-zero-fn-end.ignore-format": True,
    "numeric-invalid-fnl-fields.ignore-format": True,
    "functions-zero-start.ignore-inconsistent-format": True,
    "numeric-function-excessive.default-stop": False,
    "numeric-function-excessive.erase-suppressed": True,
}

ADDED_CASE_ARGV = {
    "numeric-format-atoms.excessive-stop-on-error-0": [
        "lcov", "--branch-coverage", "--no-function-coverage", "--ignore-errors", "format,negative",
        "--rc", "excessive_count_threshold=1000000", "--rc", "stop_on_error=0",
        "--add-tracefile", "input.info", "--output-file", "output.info",
    ],
    "numeric-format-atoms.excessive-stop-on-error-1": [
        "lcov", "--branch-coverage", "--no-function-coverage", "--ignore-errors", "format,negative",
        "--rc", "excessive_count_threshold=1000000", "--rc", "stop_on_error=1",
        "--add-tracefile", "input.info", "--output-file", "output.info",
    ],
    "numeric-negative-inf.semantic-snapshot": ["perl", "inspect_model.pl", "--ignore", "negative", "input.info"],
    "numeric-fna-nonnumeric.semantic-snapshot": ["perl", "inspect_model.pl", "--ignore", "format", "input.info"],
    "numeric-fna-malformed-exponent.ignore-format": [
        "lcov", "--ignore-errors", "format", "--add-tracefile", "input.info", "--output-file", "output.info",
    ],
    "numeric-zero-fn-end.ignore-format": [
        "lcov", "--ignore-errors", "format", "--add-tracefile", "input.info", "--output-file", "output.info",
    ],
    "numeric-zero-fn-end.semantic-snapshot": ["perl", "inspect_model.pl", "--ignore", "format", "input.info"],
    "numeric-invalid-fnl-fields.ignore-format": [
        "lcov", "--ignore-errors", "format", "--add-tracefile", "input.info", "--output-file", "output.info",
    ],
    "numeric-invalid-fnl-fields.semantic-snapshot": ["perl", "inspect_model.pl", "--ignore", "format", "input.info"],
    "functions-zero-start.ignore-inconsistent-format": [
        "lcov", "--ignore-errors", "inconsistent,format", "--add-tracefile", "input.info", "--output-file", "output.info",
    ],
    "functions-zero-start.semantic-snapshot": [
        "perl", "inspect_model.pl", "--ignore", "inconsistent,format", "input.info",
    ],
    "numeric-function-excessive.default-stop": [
        "lcov", "--rc", "excessive_count_threshold=100", "--add-tracefile", "input.info", "--output-file", "output.info",
    ],
    "numeric-function-excessive.erase-suppressed": [
        "lcov", "--rc", "excessive_count_threshold=100", "--rc", "erase_functions=^suppress_me$",
        "--add-tracefile", "input.info", "--output-file", "output.info",
    ],
}


def validate_added_numeric_case(case: dict[str, object], observation: dict[str, object]) -> None:
    case_id = str(case["id"])
    if case_id in ADDED_CASE_ARGV:
        require(case.get("argv") == ADDED_CASE_ARGV[case_id], f"{case_id}: argv policy drift")
    if case_id not in ADDED_OUTPUT_EXPECTATIONS:
        return
    expected_exists = ADDED_OUTPUT_EXPECTATIONS[case_id]
    require(case.get("expected_output_exists") is expected_exists, f"{case_id}: expected output policy missing")
    if not expected_exists:
        require(observation["output"]["exists"] is False, f"{case_id}: output must be absent")
        return
    output = decode_identity(observation["output"], f"{case_id} output")
    exact_outputs = {
        "numeric-fna-malformed-exponent.ignore-format": (
            b"TN:numeric_fna_malformed_exponent\n"
            b"SF:src/numeric-fna-malformed-exponent.c\n"
            b"FNL:0,1,1\nFNA:0,0,alias\nFNF:1\nFNH:0\nDA:1,0\nLF:1\nLH:0\nend_of_record\n"
        ),
        "numeric-zero-fn-end.ignore-format": (
            b"TN:numeric_zero_fn_end\nSF:src/numeric-zero-fn-end.c\n"
            b"FNL:0,1,0\nFNA:0,0,name\nFNF:1\nFNH:0\nDA:1,0\nLF:1\nLH:0\nend_of_record\n"
        ),
        "numeric-invalid-fnl-fields.ignore-format": (
            b"TN:numeric_invalid_fnl_fields\nSF:src/numeric-invalid-fnl-fields.c\n"
            b"FNL:0,1,1\nFNA:0,0,valid\nFNF:1\nFNH:0\nDA:1,0\nLF:1\nLH:0\nend_of_record\n"
        ),
        "functions-zero-start.ignore-inconsistent-format": (
            b"TN:fn_zero_start\nSF:src/fn-zero-start.c\nFNL:0,0,5\nFNA:0,1,zero_start\n"
            b"FNF:1\nFNH:1\nDA:1,1\nDA:5,1\nLF:2\nLH:2\nend_of_record\n"
        ),
        "numeric-format-atoms.excessive-stop-on-error-0": (
            b"TN:\nSF:a.cpp\nBRDA:1,0,0,1\nBRDA:1,0,1,0\nBRDA:1,0,2,-\n"
            b"BRDA:1,1,0,0\nBRDA:1,1,1,1.67e+20\nBRDA:1,1,1,0\nBRDA:11,0,0,0\n"
            b"BRDA:11,0,1,-0\nBRF:8\nBRH:2\nDA:1,1\nDA:2,1\nDA:3,1\nDA:4,0\n"
            b"DA:10,0\nDA:11,0\nDA:12,1.0e+19\nLF:7\nLH:4\nend_of_record\n"
        ),
        "numeric-function-excessive.erase-suppressed": (
            b"TN:function_excessive\nSF:function-excessive.c\nFNL:0,1,1\nFNA:0,99,below_fn\n"
            b"FNL:1,2,2\nFNA:1,100,at_fn\nFNF:2\nFNH:2\nDA:1,1\nDA:2,1\nDA:4,1\n"
            b"LF:3\nLH:3\nend_of_record\n"
        ),
    }
    if case_id in exact_outputs:
        require(output == exact_outputs[case_id], f"{case_id}: canonical output drift")
