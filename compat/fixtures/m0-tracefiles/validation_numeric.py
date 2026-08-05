"""Numeric snapshot, policy, and semantic registry validators."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from validation_common import (
    ROOT,
    assert_single_testcase_parity,
    decode_identity,
    require,
    strict_json_loads_ascii,
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
    "numeric-tf030-fna-mirror",
    "numeric-tf030-candidate-matrix",
    "numeric-tf030-format-atoms-plan",
    "numeric-tf030-fna-mirror-plan",
    "numeric-tf030-candidate-plan",
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
    "numeric-tf030-fna-mirror.default-stop": False,
    "numeric-tf030-fna-mirror.ignore-negative-stop-format": False,
    "numeric-tf030-fna-mirror.ignore-negative-format.canonical": True,
    "numeric-tf030-fna-mirror.threshold-default-stop": False,
    "numeric-tf030-fna-mirror.threshold-ignore-all.canonical": True,
    "numeric-tf030-candidates.default-stop": False,
    "numeric-tf030-candidates.ignore-negative.canonical": True,
    "numeric-tf030-candidates.threshold-default-stop": False,
    "numeric-tf030-candidates.threshold-ignore-all.canonical": True,
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
    output = None
    if not expected_exists:
        require(observation["output"]["exists"] is False, f"{case_id}: output must be absent")
    else:
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
        "numeric-tf030-fna-mirror.ignore-negative-format.canonical": b'TN:tf030_fna_mirror\nSF:src/tf030-fna-mirror.c\nFNL:0,1,1\nFNA:0,0,fna_neg2\nFNL:1,2,2\nFNA:1,0,fna_malformed_eb\nFNL:2,3,3\nFNA:2,1.5e+20,fna_one_point_five_e20\nFNL:3,4,4\nFNA:3,0,fna_neg0\nFNF:4\nFNH:1\nDA:1,0\nDA:2,0\nDA:3,1\nDA:4,0\nLF:4\nLH:1\nend_of_record\n',
        "numeric-tf030-fna-mirror.threshold-ignore-all.canonical": b'TN:tf030_fna_mirror\nSF:src/tf030-fna-mirror.c\nFNL:0,1,1\nFNA:0,0,fna_neg2\nFNL:1,2,2\nFNA:1,0,fna_malformed_eb\nFNL:2,3,3\nFNA:2,1.5e+20,fna_one_point_five_e20\nFNL:3,4,4\nFNA:3,0,fna_neg0\nFNF:4\nFNH:1\nDA:1,0\nDA:2,0\nDA:3,1\nDA:4,0\nLF:4\nLH:1\nend_of_record\n',
        "numeric-tf030-candidates.ignore-negative.canonical": b'TN:tf030_candidate_brda\nSF:src/tf030-candidate-brda.c\nFNF:0\nFNH:0\nBRDA:1,0,0,0\nBRDA:1,0,1,+1\nBRDA:1,0,2,1.5\nBRDA:1,0,3,1e3\nBRDA:1,0,4,Inf\nBRDA:1,0,5,+Inf\nBRDA:1,0,6,Infinity\nBRDA:1,0,7,NaN\nBRDA:1,0,8,nan\nBRDA:1,0,9,0\nBRF:10\nBRH:6\nDA:1,1\nLF:1\nLH:1\nend_of_record\nTN:tf030_candidate_da\nSF:src/tf030-candidate-da.c\nFNF:0\nFNH:0\nDA:1,0\nDA:2,+1\nDA:3,1.5\nDA:4,1e3\nDA:5,Inf\nDA:6,+Inf\nDA:7,Infinity\nDA:8,NaN\nDA:9,nan\nDA:10,0\nLF:10\nLH:6\nend_of_record\nTN:tf030_candidate_fna\nSF:src/tf030-candidate-fna.c\nFNL:0,1,1\nFNA:0,0,alias_zero\nFNL:1,2,2\nFNA:1,1,alias_plus_one\nFNL:2,3,3\nFNA:2,1.5,alias_one_point_five\nFNL:3,4,4\nFNA:3,1000,alias_one_e3\nFNL:4,5,5\nFNA:4,Inf,alias_inf\nFNL:5,6,6\nFNA:5,Inf,alias_plus_inf\nFNL:6,7,7\nFNA:6,Inf,alias_infinity\nFNL:7,8,8\nFNA:7,NaN,alias_nan_upper\nFNL:8,9,9\nFNA:8,NaN,alias_nan_lower\nFNL:9,10,10\nFNA:9,0,alias_neg_inf\nFNF:10\nFNH:6\nDA:1,0\nDA:2,1\nDA:3,1\nDA:4,1\nDA:5,1\nDA:6,1\nDA:7,1\nDA:8,1\nDA:9,1\nDA:10,0\nLF:10\nLH:8\nend_of_record\nTN:tf030_candidate_fnda\nSF:src/tf030-candidate-fnda.c\nFNL:0,1,1\nFNA:0,0,fn_zero\nFNL:1,2,2\nFNA:1,1,fn_plus_one\nFNL:2,3,3\nFNA:2,1.5,fn_one_point_five\nFNL:3,4,4\nFNA:3,1000,fn_one_e3\nFNL:4,5,5\nFNA:4,Inf,fn_inf\nFNL:5,6,6\nFNA:5,Inf,fn_plus_inf\nFNL:6,7,7\nFNA:6,Inf,fn_infinity\nFNL:7,8,8\nFNA:7,NaN,fn_nan_upper\nFNL:8,9,9\nFNA:8,NaN,fn_nan_lower\nFNL:9,10,10\nFNA:9,0,fn_neg_inf\nFNF:10\nFNH:6\nDA:1,0\nDA:2,1\nDA:3,1\nDA:4,1\nDA:5,1\nDA:6,1\nDA:7,1\nDA:8,1\nDA:9,1\nDA:10,0\nLF:10\nLH:8\nend_of_record\n',
        "numeric-tf030-candidates.threshold-ignore-all.canonical": b'TN:tf030_candidate_brda\nSF:src/tf030-candidate-brda.c\nFNF:0\nFNH:0\nBRDA:1,0,0,0\nBRDA:1,0,1,+1\nBRDA:1,0,2,1.5\nBRDA:1,0,3,1e3\nBRDA:1,0,4,Inf\nBRDA:1,0,5,+Inf\nBRDA:1,0,6,Infinity\nBRDA:1,0,7,NaN\nBRDA:1,0,8,nan\nBRDA:1,0,9,0\nBRF:10\nBRH:6\nDA:1,1\nLF:1\nLH:1\nend_of_record\nTN:tf030_candidate_da\nSF:src/tf030-candidate-da.c\nFNF:0\nFNH:0\nDA:1,0\nDA:2,+1\nDA:3,1.5\nDA:4,1e3\nDA:5,Inf\nDA:6,+Inf\nDA:7,Infinity\nDA:8,NaN\nDA:9,nan\nDA:10,0\nLF:10\nLH:6\nend_of_record\nTN:tf030_candidate_fna\nSF:src/tf030-candidate-fna.c\nFNL:0,1,1\nFNA:0,0,alias_zero\nFNL:1,2,2\nFNA:1,1,alias_plus_one\nFNL:2,3,3\nFNA:2,1.5,alias_one_point_five\nFNL:3,4,4\nFNA:3,1000,alias_one_e3\nFNL:4,5,5\nFNA:4,Inf,alias_inf\nFNL:5,6,6\nFNA:5,Inf,alias_plus_inf\nFNL:6,7,7\nFNA:6,Inf,alias_infinity\nFNL:7,8,8\nFNA:7,NaN,alias_nan_upper\nFNL:8,9,9\nFNA:8,NaN,alias_nan_lower\nFNL:9,10,10\nFNA:9,0,alias_neg_inf\nFNF:10\nFNH:6\nDA:1,0\nDA:2,1\nDA:3,1\nDA:4,1\nDA:5,1\nDA:6,1\nDA:7,1\nDA:8,1\nDA:9,1\nDA:10,0\nLF:10\nLH:8\nend_of_record\nTN:tf030_candidate_fnda\nSF:src/tf030-candidate-fnda.c\nFNL:0,1,1\nFNA:0,0,fn_zero\nFNL:1,2,2\nFNA:1,1,fn_plus_one\nFNL:2,3,3\nFNA:2,1.5,fn_one_point_five\nFNL:3,4,4\nFNA:3,1000,fn_one_e3\nFNL:4,5,5\nFNA:4,Inf,fn_inf\nFNL:5,6,6\nFNA:5,Inf,fn_plus_inf\nFNL:6,7,7\nFNA:6,Inf,fn_infinity\nFNL:7,8,8\nFNA:7,NaN,fn_nan_upper\nFNL:8,9,9\nFNA:8,NaN,fn_nan_lower\nFNL:9,10,10\nFNA:9,0,fn_neg_inf\nFNF:10\nFNH:6\nDA:1,0\nDA:2,1\nDA:3,1\nDA:4,1\nDA:5,1\nDA:6,1\nDA:7,1\nDA:8,1\nDA:9,1\nDA:10,0\nLF:10\nLH:8\nend_of_record\n',
    }
    if case_id in exact_outputs:
        require(output is not None, f"{case_id}: exact output requires present file")
        require(output == exact_outputs[case_id], f"{case_id}: canonical output drift")

    tf030_lcov_stderr = {
        "numeric-tf030-fna-mirror.default-stop": (
            ("ERROR", "corrupt"),
            ("ERROR", "negative"),
        ),
        "numeric-tf030-fna-mirror.ignore-negative-stop-format": (
            ("WARNING", "negative"),
            ("ERROR", "corrupt"),
            ("ERROR", "format"),
        ),
        "numeric-tf030-fna-mirror.ignore-negative-format.canonical": (
            ("WARNING", "negative"),
            ("WARNING", "format"),
        ),
        "numeric-tf030-fna-mirror.threshold-default-stop": (
            ("WARNING", "negative"),
            ("WARNING", "format"),
            ("ERROR", "corrupt"),
            ("ERROR", "excessive"),
        ),
        "numeric-tf030-fna-mirror.threshold-ignore-all.canonical": (
            ("WARNING", "negative"),
            ("WARNING", "format"),
            ("WARNING", "excessive"),
            ("WARNING", "excessive"),
        ),
        "numeric-tf030-candidates.default-stop": (
            ("ERROR", "corrupt"),
            ("ERROR", "negative"),
        ),
        "numeric-tf030-candidates.ignore-negative.canonical": (
            ("WARNING", "negative"),
            ("WARNING", "negative"),
            ("WARNING", "negative"),
            ("WARNING", "negative"),
        ),
        "numeric-tf030-candidates.threshold-default-stop": (
            ("ERROR", "corrupt"),
            ("ERROR", "excessive"),
        ),
        "numeric-tf030-candidates.threshold-ignore-all.canonical": (
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
    if case_id in tf030_lcov_stderr:
        from validation_common import validate_lcov_stderr
        validate_lcov_stderr(
            case_id,
            decode_identity(observation["stderr"], f"{case_id} stderr"),
            tf030_lcov_stderr[case_id],
        )



def _assert_sv_projection(proj: object, label: str, *, allow_null: bool) -> None:
    if proj is None:
        require(allow_null, f"{label}: projection must not be null")
        return
    require(isinstance(proj, dict), f"{label}: projection must be object")
    for flag in ("class", "iok", "nok", "pok", "is_uv"):
        require(flag in proj, f"{label}: missing {flag}")
    require(isinstance(proj["class"], str) and proj["class"].startswith("B::"), f"{label}: class")
    for flag in ("iok", "nok", "pok", "is_uv"):
        require(isinstance(proj[flag], bool), f"{label}: {flag} must be bool")


def _assert_stored_value(value: object, label: str, *, allow_never: bool = False) -> None:
    require(value is not None, f"{label}: stored value missing")
    require(isinstance(value, dict), f"{label}: stored value must be object")
    if "state" in value:
        require(allow_never, f"{label}: unexpected never-evaluated state")
        require(value == {"state": "never_evaluated"}, f"{label}: never-evaluated shape")
        return
    for key in ("text", "signed_zero", "scalar"):
        require(key in value, f"{label}: missing {key}")
    require(isinstance(value["text"], str), f"{label}: text must be string")
    require(isinstance(value["signed_zero"], bool), f"{label}: signed_zero must be bool")
    if value["signed_zero"]:
        require(value["text"] == "-0", f"{label}: signed zero text")
    _assert_sv_projection(value["scalar"], f"{label}.scalar", allow_null=False)


def _tf030_plan_path_for_case(case_id: str) -> Path:
    plan_name = {
        "numeric-format-atoms.tf030.semantic-snapshot": "tf030-format-atoms-plan.json",
        "numeric-format-atoms.tf030-threshold.semantic-snapshot": "tf030-format-atoms-plan.json",
        "numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot": "tf030-fna-mirror-plan.json",
        "numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot": "tf030-fna-mirror-plan.json",
        "numeric-tf030-candidates.ignore-negative.semantic-snapshot": "tf030-candidate-plan.json",
        "numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot": "tf030-candidate-plan.json",
    }.get(case_id)
    require(plan_name is not None, f"{case_id}: no TF-030 plan binding")
    from validation_common import ROOT
    path = ROOT / "fixtures" / "numeric" / plan_name
    require(path.is_file(), f"{case_id}: missing plan file {path}")
    return path


def _load_tf030_plan(case_id: str) -> dict[str, object]:
    from validation_common import ROOT, strict_json_loads_ascii
    path = _tf030_plan_path_for_case(case_id)
    raw = path.read_bytes()
    require(all(byte < 0x80 for byte in raw), f"{case_id}: plan non-ASCII")
    document = strict_json_loads_ascii(raw, f"{case_id} numeric plan")
    require(document.get("schema_version") == 1, f"{case_id}: plan schema")
    require(document.get("kind") == "tf030_numeric_plan", f"{case_id}: plan kind")
    require(isinstance(document.get("rows"), list), f"{case_id}: plan rows")
    return document


@cache
def _load_tf030_semantic_registry() -> dict[str, object]:
    path = ROOT / "tf030-semantic-registry.json"
    require(path.is_file(), f"TF-030 semantic registry missing: {path}")
    document = strict_json_loads_ascii(path.read_bytes(), "tf030 semantic registry")
    require(document.get("schema_version") == 1, "TF-030 semantic registry schema")
    require(document.get("kind") == "tf030_semantic_registry", "TF-030 semantic registry kind")
    cases = document.get("cases")
    require(isinstance(cases, dict), "TF-030 semantic registry cases")
    return document


def _expected_tf030_case(case_id: str) -> dict[str, object]:
    cases = _load_tf030_semantic_registry()["cases"]
    require(isinstance(cases, dict), "TF-030 semantic registry cases")
    expected = cases.get(case_id)
    require(isinstance(expected, dict), f"{case_id}: semantic registry case missing")
    return expected


def _scan_fixture_numeric_records(fixture_rel: str, label: str) -> list[dict[str, object]]:
    from validation_common import ROOT
    import re as _re
    path = ROOT / fixture_rel
    require(path.is_file(), f"{label}: fixture missing {fixture_rel}")
    text = path.read_bytes().decode("utf-8", "strict")
    records: list[dict[str, object]] = []
    source: str | None = None
    ordinal = 0
    for line in text.splitlines():
        if line.startswith("SF:"):
            source = line[3:]
            ordinal = 0
            continue
        if line.startswith("end_of_record"):
            source = None
            ordinal = 0
            continue
        if source is None:
            continue
        if not (
            line.startswith("DA:")
            or line.startswith("FNDA:")
            or line.startswith("FNA:")
            or line.startswith("BRDA:")
        ):
            continue
        family, rest = line.split(":", 1)
        ordinal += 1
        if family == "DA":
            line_no, lexeme = rest.split(",", 1)
            locator: dict[str, object] = {"line": int(line_no)}
        elif family == "FNDA":
            lexeme, name = rest.split(",", 1)
            locator = {"function_name": name, "alias": name}
        elif family == "FNA":
            idx, lexeme, alias = rest.split(",", 2)
            locator = {"function_index": int(idx), "alias": alias}
        else:
            match = _re.match(r"^(\d+),([ef]?)(U?)(\d+),(.+)$", rest)
            require(match is not None, f"{label}: unparsed BRDA {line!r}")
            assert match is not None
            ln = match.group(1)
            block = match.group(4)
            branch_and_count = match.group(5)
            branch_token, lexeme = branch_and_count.split(",", 1)
            if branch_token.lstrip("-").isdigit():
                branch_value: object = int(branch_token)
            else:
                branch_value = branch_token
            locator = {
                "line": int(ln),
                "block": int(block),
                "branch": branch_value,
                "expression": None,
            }
        records.append(
            {
                "family": family,
                "lexeme": lexeme,
                "raw_record": line,
                "record_ordinal": ordinal,
                "locator": locator,
                "source": source,
            }
        )
    return records


def _locator_equal(family: str, left: dict[str, object], right: dict[str, object]) -> bool:
    if family == "DA":
        return int(left["line"]) == int(right["line"])
    if family == "FNDA":
        return left.get("function_name") == right.get("function_name") and left.get("alias") == right.get("alias")
    if family == "FNA":
        return int(left["function_index"]) == int(right["function_index"]) and left.get("alias") == right.get("alias")
    if family == "BRDA":
        return (
            int(left["line"]) == int(right["line"])
            and int(left["block"]) == int(right["block"])
            and str(left["branch"]) == str(right["branch"])
            and left.get("expression") == right.get("expression")
        )
    return False


def _expected_value_class(lexeme: str, looks_like_number: bool | None, never: bool) -> str:
    if never:
        return "not_evaluated"
    if looks_like_number is False:
        return "nonnumeric"
    lower = lexeme.lower()
    if lower == "nan":
        return "nan"
    if lower in {"inf", "+inf", "infinity", "+infinity"}:
        return "positive_infinity"
    if lower in {"-inf", "-infinity"}:
        return "negative_infinity"
    return "finite"


def validate_tf030_numeric_rows(document: dict[str, object], *, expected_count: int, case_id: str) -> None:
    require(document.get("kind") == "semantic_model_snapshot", f"{case_id}: kind mismatch")
    require(document.get("schema_version") == 1, f"{case_id}: schema mismatch")
    require("numeric_rows" in document, f"{case_id}: numeric_rows missing")
    rows = document.get("numeric_rows")
    require(isinstance(rows, list), f"{case_id}: numeric_rows must be a list")
    require(len(rows) == expected_count, f"{case_id}: expected {expected_count} numeric rows, got {len(rows)}")

    plan_doc = _load_tf030_plan(case_id)
    plan_rows = plan_doc["rows"]
    require(isinstance(plan_rows, list), f"{case_id}: plan rows list")
    require(len(plan_rows) == expected_count, f"{case_id}: plan row count {len(plan_rows)} != {expected_count}")

    # Compare the complete retained semantic oracle before applying generic
    # shape checks. This prevents a self-consistent but fabricated row/source
    # snapshot from satisfying the compatibility contract.
    expected_case = _expected_tf030_case(case_id)
    require(
        rows == expected_case.get("numeric_rows"),
        f"{case_id}: numeric row semantic registry mismatch",
    )
    require(
        document.get("sources") == expected_case.get("sources"),
        f"{case_id}: aggregate/testcase semantic registry mismatch",
    )

    threshold_enabled = case_id in {
        "numeric-format-atoms.tf030-threshold.semantic-snapshot",
        "numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot",
        "numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot",
    }

    for index, plan_row in enumerate(plan_rows):
        require(isinstance(plan_row, dict), f"{case_id}: plan row {index} object")
        require(plan_row.get("family") != "MCDC", f"{case_id}: MC/DC out of TF-030 scope in plan")
    for index, row in enumerate(rows):
        require(isinstance(row, dict), f"{case_id}: row {index} object")
        require(row.get("family") != "MCDC", f"{case_id}: MC/DC out of TF-030 scope in output")

    # Bind every plan row to fixture bytes with exact ordinal/family/lexeme/raw/locator.
    fixture_cache: dict[str, list[dict[str, object]]] = {}
    for plan_row in plan_rows:
        fixture_rel = str(plan_row["fixture"])
        if fixture_rel not in fixture_cache:
            fixture_cache[fixture_rel] = _scan_fixture_numeric_records(fixture_rel, case_id)
        records = fixture_cache[fixture_rel]
        hits = [
            rec
            for rec in records
            if rec["family"] == plan_row["family"]
            and rec["source"] == plan_row["source"]
            and rec["lexeme"] == plan_row["lexeme"]
            and rec["raw_record"] == plan_row["raw_record"]
            and _locator_equal(str(plan_row["family"]), rec["locator"], plan_row["locator"])  # type: ignore[arg-type]
        ]
        require(len(hits) == 1, f"{case_id}: plan row {plan_row.get('id')} fixture match count={len(hits)}")
        hit = hits[0]
        require(
            int(hit["record_ordinal"]) == int(plan_row["record_ordinal"]),
            f"{case_id}: plan ordinal drift {plan_row.get('id')} plan={plan_row['record_ordinal']} fixture={hit['record_ordinal']}",
        )

    require(
        [row.get("id") for row in rows] == [plan_row.get("id") for plan_row in plan_rows],
        f"{case_id}: row order/id closure drift",
    )
    require(
        [row.get("record_ordinal") for row in rows] == [plan_row.get("record_ordinal") for plan_row in plan_rows],
        f"{case_id}: record_ordinal plan/output closure drift",
    )

    seen_locators: set[str] = set()
    sources = document.get("sources")
    require(isinstance(sources, list) and sources, f"{case_id}: sources missing")

    for index, (plan_row, row) in enumerate(zip(plan_rows, rows)):
        row_id = str(plan_row["id"])
        for key in (
            "id", "family", "lexeme", "fixture", "source", "testcase", "reader_match_kind",
            "raw_record", "record_ordinal", "locator", "record_matched", "retained", "skipped",
            "looks_like_number", "sv_before", "sv_after_looks_like_number",
            "sv_after_negative_compare", "sv_after_threshold_compare", "value_class",
            "negative", "threshold_enabled", "threshold_text", "greater_than_threshold",
            "category", "recovery", "stored_aggregate", "stored_testcase",
        ):
            require(key in row, f"{case_id}: row {index} missing {key}")
        for key in (
            "id", "family", "lexeme", "fixture", "source", "testcase",
            "reader_match_kind", "raw_record", "record_ordinal",
        ):
            require(row[key] == plan_row[key], f"{case_id}:{row_id}: plan field {key} mismatch")
        require(isinstance(row["locator"], dict) and isinstance(plan_row["locator"], dict), f"{case_id}:{row_id}: locator type")
        require(
            _locator_equal(str(plan_row["family"]), row["locator"], plan_row["locator"]),  # type: ignore[arg-type]
            f"{case_id}:{row_id}: locator mismatch against plan",
        )

        family = str(row["family"])
        require(family in {"DA", "FNDA", "FNA", "BRDA"}, f"{case_id}: invalid family")
        locator = row["locator"]
        if family == "DA":
            require(set(locator) == {"line"}, f"{case_id}: DA locator keys")
        elif family == "FNDA":
            require(set(locator) == {"function_name", "alias"}, f"{case_id}: FNDA locator keys")
        elif family == "FNA":
            require(set(locator) == {"function_index", "alias"}, f"{case_id}: FNA locator keys")
        else:
            require(set(locator) == {"line", "block", "branch", "expression"}, f"{case_id}: BRDA locator keys")

        locator_key = f"{family}:{sorted((k, repr(v)) for k, v in locator.items())}"
        require(locator_key not in seen_locators, f"{case_id}: duplicate locator {row_id}")
        seen_locators.add(locator_key)

        require(row["record_matched"] is True, f"{case_id}:{row_id}: record_matched")
        require(row["retained"] is True, f"{case_id}:{row_id}: retained")
        require(row["skipped"] is False, f"{case_id}:{row_id}: skipped")
        require(row["threshold_enabled"] is threshold_enabled, f"{case_id}:{row_id}: threshold_enabled")
        if threshold_enabled:
            require(row["threshold_text"] == "1000000", f"{case_id}:{row_id}: threshold_text")
        else:
            require(row["threshold_text"] is None, f"{case_id}:{row_id}: threshold_text null")

        # Source identity present in snapshot.
        source_matches = [item for item in sources if isinstance(item, dict) and item.get("filename") == row["source"]]
        require(len(source_matches) == 1, f"{case_id}:{row_id}: source identity")
        source_entry = source_matches[0]
        aggregate = source_entry.get("aggregate")
        testcases = source_entry.get("testcases")
        require(isinstance(aggregate, dict), f"{case_id}:{row_id}: aggregate object")
        require(isinstance(testcases, dict), f"{case_id}:{row_id}: testcases object")
        for family_key in ("line", "function", "branch", "mcdc"):
            require(family_key in aggregate, f"{case_id}:{row_id}: aggregate missing {family_key}")
            require(family_key in testcases, f"{case_id}:{row_id}: testcases missing {family_key}")

        never = row["lexeme"] == "-" and family == "BRDA"
        if never:
            require(row["reader_match_kind"] == "brda_never_evaluated", f"{case_id}:{row_id}: never path")
            require(row["looks_like_number"] is None, f"{case_id}:{row_id}: never lln null")
            require(row["value_class"] == "not_evaluated", f"{case_id}:{row_id}: never class")
            require(row["category"] is None, f"{case_id}:{row_id}: never category")
            require(row["recovery"] == "never evaluated", f"{case_id}:{row_id}: never recovery")
            require(row["sv_after_looks_like_number"] is None, f"{case_id}:{row_id}: never after-lln null")
            require(row["sv_after_negative_compare"] is None, f"{case_id}:{row_id}: never after-neg null")
            require(row["sv_after_threshold_compare"] is None, f"{case_id}:{row_id}: never after-thr null")
            require(row["greater_than_threshold"] is None, f"{case_id}:{row_id}: never greater null")
            _assert_sv_projection(row["sv_before"], f"{case_id}:{row_id}.sv_before", allow_null=False)
            _assert_stored_value(row["stored_aggregate"], f"{case_id}:{row_id}.agg", allow_never=True)
            _assert_stored_value(row["stored_testcase"], f"{case_id}:{row_id}.tc", allow_never=True)
            require(row["stored_aggregate"] == {"state": "never_evaluated"}, f"{case_id}:{row_id}: agg never")
            require(row["stored_testcase"] == {"state": "never_evaluated"}, f"{case_id}:{row_id}: tc never")
            continue

        require(row["reader_match_kind"] == "looks_like_number", f"{case_id}:{row_id}: reader path")
        require(isinstance(row["looks_like_number"], bool), f"{case_id}:{row_id}: lln bool")
        _assert_sv_projection(row["sv_before"], f"{case_id}:{row_id}.sv_before", allow_null=False)
        _assert_sv_projection(row["sv_after_looks_like_number"], f"{case_id}:{row_id}.sv_lln", allow_null=False)

        expected_vc = _expected_value_class(str(row["lexeme"]), bool(row["looks_like_number"]), False)
        require(row["value_class"] == expected_vc, f"{case_id}:{row_id}: value_class expected {expected_vc} got {row['value_class']}")

        if row["looks_like_number"] is False:
            require(row["category"] == "format", f"{case_id}:{row_id}: format category")
            require(row["recovery"] == "zero", f"{case_id}:{row_id}: format recovery")
            require(row["sv_after_negative_compare"] is None, f"{case_id}:{row_id}: format no neg stage")
            require(row["sv_after_threshold_compare"] is None, f"{case_id}:{row_id}: format no thr stage")
            require(row["greater_than_threshold"] is None, f"{case_id}:{row_id}: format greater null")
        else:
            require(isinstance(row["negative"], bool), f"{case_id}:{row_id}: negative bool")
            _assert_sv_projection(row["sv_after_negative_compare"], f"{case_id}:{row_id}.sv_neg", allow_null=False)
            if row["negative"] is True:
                require(row["category"] == "negative", f"{case_id}:{row_id}: negative category")
                require(row["recovery"] == "zero", f"{case_id}:{row_id}: negative recovery")
                require(row["sv_after_threshold_compare"] is None, f"{case_id}:{row_id}: negative skips thr")
                require(row["greater_than_threshold"] is None, f"{case_id}:{row_id}: negative greater null")
            else:
                if threshold_enabled:
                    _assert_sv_projection(row["sv_after_threshold_compare"], f"{case_id}:{row_id}.sv_thr", allow_null=False)
                    require(isinstance(row["greater_than_threshold"], bool), f"{case_id}:{row_id}: greater bool")
                    if row["greater_than_threshold"] is True:
                        require(row["category"] == "excessive", f"{case_id}:{row_id}: excessive category")
                        require(row["recovery"] == "retain value", f"{case_id}:{row_id}: excessive recovery")
                    else:
                        require(row["category"] is None, f"{case_id}:{row_id}: no category")
                        if row["lexeme"] == "-0":
                            require(row["recovery"] == "retain signed zero", f"{case_id}:{row_id}: signed zero recovery")
                        else:
                            require(row["recovery"] == "retain value", f"{case_id}:{row_id}: retain recovery")
                else:
                    require(row["sv_after_threshold_compare"] is None, f"{case_id}:{row_id}: no thr stage")
                    require(row["greater_than_threshold"] is None, f"{case_id}:{row_id}: greater null")
                    require(row["category"] is None, f"{case_id}:{row_id}: no category")
                    if row["lexeme"] == "-0":
                        require(row["recovery"] == "retain signed zero", f"{case_id}:{row_id}: signed zero recovery")
                    else:
                        require(row["recovery"] == "retain value", f"{case_id}:{row_id}: retain recovery")

        _assert_stored_value(row["stored_aggregate"], f"{case_id}:{row_id}.agg")
        _assert_stored_value(row["stored_testcase"], f"{case_id}:{row_id}.tc")
        require(
            row["stored_aggregate"]["text"] == row["stored_testcase"]["text"],
            f"{case_id}: agg/tc text parity {row_id}",
        )
        require(
            row["stored_aggregate"]["signed_zero"] == row["stored_testcase"]["signed_zero"],
            f"{case_id}: agg/tc signed-zero parity {row_id}",
        )
        if row["category"] in {"format", "negative"}:
            require(row["stored_aggregate"]["text"] in {"0", "+0"}, f"{case_id}: coerced zero text {row_id}")
            require(row["stored_aggregate"]["signed_zero"] is False, f"{case_id}: coerced not signed zero")
        if row["lexeme"] == "-0" and row["category"] is None:
            # Family-specific stored spelling: BRDA keeps "-0"/signed_zero; some
            # function counts may normalize while recovery still records signed zero.
            if row["stored_aggregate"]["text"] == "-0":
                require(row["stored_aggregate"]["signed_zero"] is True, f"{case_id}: -0 flag")
            else:
                require(row["recovery"] == "retain signed zero", f"{case_id}:{row_id}: -0 recovery")
