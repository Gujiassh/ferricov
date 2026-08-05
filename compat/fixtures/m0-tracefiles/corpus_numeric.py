"""Numeric fixture builders, case builders, and closure checks."""

from __future__ import annotations

import hashlib
from typing import Iterable

from corpus_model import Fixture, ascii_bytes


def valid_wrapper(record: str, name: str) -> bytes:
    return ascii_bytes(
        f"TN:malformed-{name}\n"
        f"SF:src/malformed-{name}.c\n"
        f"{record}\n"
        "DA:1,1\n"
        "LF:1\n"
        "LH:1\n"
        "end_of_record"
    )

# Keep this accepted matrix byte-stable. New spellings belong in the separate
# fixture below so existing Oracle observations remain comparable by case ID.
NUMERIC_BOUNDARY_LEXEMES = (
    "0", "+0", "-0", "1", "1.5", ".5", "1.", "1e3", "1E-3",
    "NaN", "Inf", "Infinity", " 1", "9007199254740993",
    "18446744073709551615",
)
NUMERIC_BOUNDARY_SHA256 = "5f28b263e24989af7c48f00cbf7ec0fcc6eeede831e5729a17bd3c67843e2906"
NUMERIC_EXTRA_LEXEMES = ("+1", "nan", "+Inf")
NUMERIC_LANE_FIXTURE_IDS = (
    "numeric-fna-malformed-exponent",
    "numeric-zero-fn-end",
    "numeric-invalid-fnl-fields",
    "numeric-function-excessive",
    "numeric-function-source",
)
NUMERIC_LANE_CASE_IDS = (
    "numeric-format-atoms.excessive-stop-on-error-0",
    "numeric-format-atoms.excessive-stop-on-error-1",
    "numeric-negative-inf.semantic-snapshot",
    "numeric-fna-nonnumeric.semantic-snapshot",
    "numeric-fna-malformed-exponent.ignore-format",
    "numeric-zero-fn-end.ignore-format",
    "numeric-zero-fn-end.semantic-snapshot",
    "numeric-invalid-fnl-fields.ignore-format",
    "numeric-invalid-fnl-fields.semantic-snapshot",
    "functions-zero-start.ignore-inconsistent-format",
    "functions-zero-start.semantic-snapshot",
    "numeric-function-excessive.default-stop",
    "numeric-function-excessive.erase-suppressed",
)
NUMERIC_LANE_EXPECTATIONS = {
    "numeric-format-atoms.excessive-stop-on-error-0": (1, True),
    "numeric-format-atoms.excessive-stop-on-error-1": (1, False),
    "numeric-negative-inf.semantic-snapshot": (0, None),
    "numeric-fna-nonnumeric.semantic-snapshot": (0, None),
    "numeric-fna-malformed-exponent.ignore-format": (0, True),
    "numeric-zero-fn-end.ignore-format": (0, True),
    "numeric-zero-fn-end.semantic-snapshot": (0, None),
    "numeric-invalid-fnl-fields.ignore-format": (0, True),
    "numeric-invalid-fnl-fields.semantic-snapshot": (0, None),
    "functions-zero-start.ignore-inconsistent-format": (0, True),
    "functions-zero-start.semantic-snapshot": (0, None),
    "numeric-function-excessive.default-stop": (1, False),
    "numeric-function-excessive.erase-suppressed": (0, True),
}

def numeric_fixtures() -> list[Fixture]:
    accepted = NUMERIC_BOUNDARY_LEXEMES
    chunks = []
    for index, value in enumerate(accepted):
        chunks.extend(
            [
                f"TN:numeric-{index:02d}",
                f"SF:src/numeric-{index:02d}.c",
                f"DA:1,{value}",
                "LF:1",
                "LH:1",
                "end_of_record",
            ]
        )
    fixtures = [
        Fixture(
            "numeric-boundary",
            "fixtures/numeric-boundary.info",
            "numeric-boundary",
            "Pinned Perl numeric acceptance matrix, including signed zero, fractions, exponents, special spellings, leading whitespace, and large decimals.",
            ascii_bytes("\n".join(chunks)),
            "accept",
            parameters={"accepted_lexemes": len(accepted)},
        )
    ]
    extra = NUMERIC_EXTRA_LEXEMES
    extra_chunks = []
    for index, value in enumerate(extra):
        extra_chunks.extend(
            [
                f"TN:extra_{index:02d}",
                f"SF:src/extra-{index:02d}.c",
                f"DA:1,{value}",
                "LF:1",
                "LH:1",
                "end_of_record",
            ]
        )
    fixtures.append(
        Fixture(
            "numeric-extra-spellings",
            "fixtures/numeric/extra-spellings.info",
            "numeric-boundary",
            "Additional legal TN numeric spellings (+1, nan, +Inf) kept separate so the pinned 15-atom numeric-boundary bytes stay unchanged. -Inf remains covered by numeric-negative-inf under ERROR_NEGATIVE.",
            ascii_bytes("\n".join(extra_chunks)),
            "accept",
            parameters={"accepted_lexemes": len(extra), "role": "extra_legal_tn_spellings"},
        )
    )
    # Exact upstream tests/lcov/format/format.info bytes for M0-TF-NUMERIC-001.
    # Keep trailing spaces and blank lines byte-identical to the pinned Oracle source.
    format_info = (
        b"TN:\n"
        b"SF:a.cpp\n"
        b"DA:1,1\n"
        b"#common line:  my count is zero and yours is nonzero        \n"
        b"DA:2,1\n"
        b"DA:3,1\n"
        b"DA:4,-3\n"
        b"DA:10,1.a0e+19\n"
        b"DA:11,0\n"
        b"DA:12,1.0e+19\n"
        b"LF:4\n"
        b"LH:3\n"
        b"FN:1,2,fcn\n"
        b"FN:1,2,alias\n"
        b"FN:1,2,alias2\n"
        b"FN:1,2,alias3\n"
        b"FN:3,3,noCommonAlias\n"
        b"FN:11,11,onlyA\n"
        b"FNF:4\n"
        b"FNH:3\n"
        b"# my count is zero yours is nonzero\n"
        b"FNDA:0,fcn\n"
        b"FNDA:-2,alias\n"
        b"FNDA:1.5eb+20,alias2\n"
        b"FNDA:1.5e+20,alias3\n"
        b"FNDA:-0,onlyA\n"
        b"FNDA:1,noCommonAlias\n"
        b"\n"
        b"BRDA:1,1,0,1\n"
        b"BRDA:1,1,1,-1\n"
        b"BRDA:1,1,2,-\n"
        b"BRDA:1,2,0,1.67+20\n"
        b"BRDA:1,2,1,1.67e+20\n"
        b"# common branch expr count zero in my, nonzero in you\n"
        b"BRDA:1,2,1,0\n"
        b"\n"
        b"# branch in A only\n"
        b"BRDA:11,0,0,0\n"
        b"BRDA:11,0,1,-0\n"
        b"\n"
        b"BRF:7\n"
        b"BRH:4\n"
        b"end_of_record\n"
    )
    fixtures.append(
        Fixture(
            "numeric-format-atoms",
            "fixtures/numeric/format-atoms.info",
            "numeric-boundary",
            "Exact upstream tests/lcov/format/format.info atoms for M0-TF-NUMERIC-001 negative/format/excessive counts across DA/FNDA/BRDA.",
            format_info,
            "reject",
            parameters={
                "source": "tests/lcov/format/format.info",
                "sha256": "e42a8bd718d8d9aa90e952b99ab78044227b4d511ef13e1d3de78a8c75dd0041",
            },
        )
    )
    numeric_errors = [
        ("numeric-negative", "-1", "negative count"),
        ("numeric-nonnumeric", "not-a-number", "nonnumeric count"),
        ("numeric-malformed-exponent", "1e", "malformed exponent"),
    ]
    for fixture_id, value, description in numeric_errors:
        fixtures.append(
            Fixture(
                fixture_id,
                f"fixtures/numeric/{fixture_id.removeprefix('numeric-')}.info",
                "numeric-boundary",
                description.capitalize() + " used to pin error-category and ignore recovery behavior.",
                valid_wrapper(f"DA:2,{value}", fixture_id),
                "reject",
            )
        )
    fixtures.extend(
        [
            Fixture(
                "numeric-excessive",
                "fixtures/numeric/excessive.info",
                "numeric-boundary",
                "Counts immediately below, at, and above an excessive_count_threshold of 100.",
                ascii_bytes(
                    "TN:numeric-excessive\nSF:src/numeric-excessive.c\n"
                    "DA:1,99\nDA:2,100\nDA:3,101\nLF:3\nLH:3\nend_of_record"
                ),
                "reject",
                parameters={"excessive_count_threshold": 100},
            ),
            Fixture(
                "numeric-zero-line",
                "fixtures/numeric/zero-line.info",
                "numeric-boundary",
                "Zero DA line number used to pin format error and ignore recovery behavior.",
                valid_wrapper("DA:0,1", "numeric-zero-line"),
                "reject",
            ),
            Fixture(
                "numeric-negative-inf",
                "fixtures/numeric/negative-inf.info",
                "numeric-boundary",
                "Negative infinity is classified as ERROR_NEGATIVE and coerces to zero when ignored.",
                ascii_bytes(
                    "TN:numeric_negative_inf\nSF:src/numeric-negative-inf.c\n"
                    "DA:1,-Inf\nDA:2,1\nLF:2\nLH:1\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-signed-zero",
                "fixtures/numeric/signed-zero.info",
                "numeric-boundary",
                "Negative zero across DA and BRDA; accepted and rewritten with signed-zero lexemes retained where the writer preserves them.",
                ascii_bytes(
                    "TN:numeric_signed_zero\nSF:src/numeric-signed-zero.c\n"
                    "DA:1,-0\nDA:2,1\n"
                    "BRDA:2,0,expr,-0\nBRDA:2,0,expr2,1\n"
                    "LF:2\nLH:1\nend_of_record"
                ),
                "accept",
            ),
            Fixture(
                "numeric-fnda-negative",
                "fixtures/numeric/fnda-negative.info",
                "numeric-boundary",
                "Legacy FNDA negative count coerces to zero under ignore-negative.",
                ascii_bytes(
                    "TN:numeric_fnda_negative\nSF:src/numeric-fnda-negative.c\n"
                    "FN:1,1,f\nFNDA:-2,f\nDA:1,0\nLF:1\nLH:0\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-fnda-nonnumeric",
                "fixtures/numeric/fnda-nonnumeric.info",
                "numeric-boundary",
                "Legacy FNDA nonnumeric count coerces to zero under ignore-format.",
                ascii_bytes(
                    "TN:numeric_fnda_nonnumeric\nSF:src/numeric-fnda-nonnumeric.c\n"
                    "FN:1,1,f\nFNDA:notnum,f\nDA:1,0\nLF:1\nLH:0\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-fna-nonnumeric",
                "fixtures/numeric/fna-nonnumeric.info",
                "numeric-boundary",
                "Current FNA ordinary nonnumeric count coerces to zero under ignore-format.",
                ascii_bytes(
                    "TN:numeric_fna_nonnumeric\nSF:src/numeric-fna-nonnumeric.c\n"
                    "FNL:0,1,1\nFNA:0,notnum,alias\nDA:1,0\nLF:1\nLH:0\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-fna-malformed-exponent",
                "fixtures/numeric/fna-malformed-exponent.info",
                "numeric-boundary",
                "Current FNA malformed-exponent count coerces to zero under ignore-format.",
                ascii_bytes(
                    "TN:numeric_fna_malformed_exponent\nSF:src/numeric-fna-malformed-exponent.c\n"
                    "FNL:0,1,1\nFNA:0,1e,alias\nDA:1,0\nLF:1\nLH:0\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-brda-nonnumeric",
                "fixtures/numeric/brda-nonnumeric.info",
                "numeric-boundary",
                "BRDA nonnumeric taken count coerces to zero under ignore-format.",
                ascii_bytes(
                    "TN:numeric_brda_nonnumeric\nSF:src/numeric-brda-nonnumeric.c\n"
                    "BRDA:1,0,expr,notnum\nDA:1,0\nLF:1\nLH:0\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-mcdc-nondigit",
                "fixtures/numeric/mcdc-nondigit.info",
                "numeric-boundary",
                "MC/DC counts are digit-only; a non-digit count is a format reject and is skipped when ignored.",
                ascii_bytes(
                    "TN:numeric_mcdc_nondigit\nSF:src/numeric-mcdc-nondigit.c\n"
                    "MCDC:1,1,t,abc,0,expr\nMCDC:1,1,f,1,0,expr\n"
                    "DA:1,1\nLF:1\nLH:1\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-zero-brda",
                "fixtures/numeric/zero-brda.info",
                "numeric-boundary",
                "Zero BRDA line number is a format error.",
                ascii_bytes(
                    "TN:numeric_zero_brda\nSF:src/numeric-zero-brda.c\n"
                    "BRDA:0,0,expr,1\nDA:1,1\nLF:1\nLH:1\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-zero-mcdc",
                "fixtures/numeric/zero-mcdc.info",
                "numeric-boundary",
                "Zero MCDC line number is a format error retained when ignored.",
                ascii_bytes(
                    "TN:numeric_zero_mcdc\nSF:src/numeric-zero-mcdc.c\n"
                    "MCDC:0,1,t,1,0,expr\nDA:1,1\nLF:1\nLH:1\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-zero-fn",
                "fixtures/numeric/zero-fn.info",
                "numeric-boundary",
                "Zero FN start line is a format error retained when ignored.",
                ascii_bytes(
                    "TN:numeric_zero_fn\nSF:src/numeric-zero-fn.c\n"
                    "FN:0,1,name\nFNDA:1,name\nDA:1,1\nLF:1\nLH:1\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-zero-fn-end",
                "fixtures/numeric/zero-fn-end.info",
                "numeric-boundary",
                "Zero legacy FN end line is a format error retained when ignored.",
                ascii_bytes(
                    "TN:numeric_zero_fn_end\nSF:src/numeric-zero-fn-end.c\n"
                    "FN:1,0,name\nFNDA:0,name\nDA:1,0\nLF:1\nLH:0\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-invalid-fnl-fields",
                "fixtures/numeric/invalid-fnl-fields.info",
                "numeric-boundary",
                "Nondigit current FNL start and end fields are format errors; ignored records do not populate the function-index map.",
                ascii_bytes(
                    "TN:numeric_invalid_fnl_fields\nSF:src/numeric-invalid-fnl-fields.c\n"
                    "FNL:0,notline,5\nFNL:1,5,notline\n"
                    "FNL:2,1,1\nFNA:2,0,valid\nDA:1,0\nLF:1\nLH:0\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "numeric-inf-excessive",
                "fixtures/numeric/inf-excessive.info",
                "numeric-boundary",
                "Inf and NaN remain numeric and trip excessive_count_threshold without coercion when ignored.",
                ascii_bytes(
                    "TN:numeric_inf_excessive\nSF:src/numeric-inf-excessive.c\n"
                    "DA:1,Inf\nDA:2,NaN\nDA:3,1\nLF:3\nLH:2\nend_of_record"
                ),
                "reject",
                parameters={"excessive_count_threshold": 100},
            ),
            Fixture(
                "numeric-function-excessive",
                "fixtures/numeric/function-excessive.info",
                "numeric-boundary",
                "Function counts below, at, and above threshold 100, with the above-threshold alias suppressible by erase_functions.",
                ascii_bytes(
                    "TN:function_excessive\nSF:function-excessive.c\n"
                    "FNL:0,1,1\nFNA:0,99,below_fn\n"
                    "FNL:1,2,2\nFNA:1,100,at_fn\n"
                    "FNL:2,3,3\nFNA:2,101,suppress_me\n"
                    "DA:1,1\nDA:2,1\nDA:3,1\nDA:4,1\n"
                    "LF:4\nLH:4\nend_of_record"
                ),
                "reject",
                parameters={"excessive_count_threshold": 100},
            ),
            Fixture(
                "numeric-function-source",
                "fixtures/numeric/function-excessive.c",
                "numeric-boundary",
                "Companion source for erase_functions suppression and filtering evidence.",
                ascii_bytes(
                    "int below_fn(void) { return 1; }\n"
                    "int at_fn(void) { return 1; }\n"
                    "int suppress_me(void) { return 1; }\n"
                    "int tail;"
                ),
                "accept",
                parameters={"role": "companion_source"},
            ),
            Fixture(
                "checksum-match",
                "fixtures/numeric/checksum-match.info",
                "numeric-boundary",
                "DA checksum matches Digest::MD5::md5_base64 of companion source line cs.c.",
                ascii_bytes(
                    "TN:checksum-match\nSF:cs.c\n"
                    "DA:1,1,AVO7Y115x231sZo9ymlVFA\nLF:1\nLH:1\nend_of_record"
                ),
                "accept",
            ),
            Fixture(
                "checksum-mismatch",
                "fixtures/numeric/checksum-mismatch.info",
                "numeric-boundary",
                "DA checksum mismatches companion source line under --checksum.",
                ascii_bytes(
                    "TN:checksum-mismatch\nSF:cs.c\n"
                    "DA:1,1,WRONGCHK\nLF:1\nLH:1\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "checksum-missing",
                "fixtures/numeric/checksum-missing.info",
                "numeric-boundary",
                "DA record omits checksum while --checksum requires one.",
                ascii_bytes(
                    "TN:checksum-missing\nSF:cs.c\n"
                    "DA:1,1\nLF:1\nLH:1\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "checksum-duplicate",
                "fixtures/numeric/checksum-duplicate.info",
                "numeric-boundary",
                "Two sections store different checksums for the same source line under --checksum.",
                ascii_bytes(
                    "TN:a\nSF:cs.c\nDA:1,1,AVO7Y115x231sZo9ymlVFA\nend_of_record\n"
                    "TN:b\nSF:cs.c\nDA:1,1,OTHERCHK\nend_of_record"
                ),
                "reject",
            ),
            Fixture(
                "checksum-source-cs",
                "fixtures/numeric/cs.c",
                "numeric-boundary",
                "Companion source file for DA checksum verification; line 1 is Digest::MD5::md5_base64 identity AVO7Y115x231sZo9ymlVFA.",
                b"int x = 1;\n",
                "accept",
                parameters={"role": "companion_source"},
            ),
        ]
    )
    return fixtures

def validate_numeric_fixture_closure(fixtures: Iterable[Fixture]) -> None:
    by_id = {fixture.id: fixture for fixture in fixtures}
    expected = {
        "numeric-fna-malformed-exponent": (
            "fixtures/numeric/fna-malformed-exponent.info",
            "reject",
            "64d05404d36414077f594b8f1e8876b18871f8edcc1775ae9f5c6eb04cf58423",
        ),
        "numeric-zero-fn-end": (
            "fixtures/numeric/zero-fn-end.info",
            "reject",
            "313b34a2d9eff70c901ef8bdfaeddea0f589a247e9e5bf2854ccc81da93f2674",
        ),
        "numeric-invalid-fnl-fields": (
            "fixtures/numeric/invalid-fnl-fields.info",
            "reject",
            "55070a20b5d901b5631435baa3c7b23d3f8bd2db66182bb1eecff7b5a5f1394c",
        ),
        "numeric-function-excessive": (
            "fixtures/numeric/function-excessive.info",
            "reject",
            "5e30055d2b6d2a3ed565b7bd8973249defc8ad6f7a62677e86582dc9a7d8d0aa",
        ),
        "numeric-function-source": (
            "fixtures/numeric/function-excessive.c",
            "accept",
            "0e056f7f7a0fc2b919def78cdf0283d96e291d6d740da8b2ee570a5192315806",
        ),
    }
    if set(expected) != set(NUMERIC_LANE_FIXTURE_IDS):
        raise ValueError("numeric lane fixture registry drift")
    missing = sorted(set(expected) - set(by_id))
    if missing:
        raise ValueError(f"missing numeric lane fixtures: {missing}")
    for fixture_id, (path, oracle_default, sha256) in expected.items():
        fixture = by_id[fixture_id]
        if fixture.path != path or fixture.oracle_default != oracle_default:
            raise ValueError(f"numeric lane fixture metadata drift: {fixture_id}")
        if hashlib.sha256(fixture.data).hexdigest() != sha256:
            raise ValueError(f"numeric lane fixture bytes drift: {fixture_id}")

    boundary = by_id["numeric-boundary"]
    boundary_values = [
        line.removeprefix(b"DA:1,").decode("ascii")
        for line in boundary.data.splitlines()
        if line.startswith(b"DA:1,")
    ]
    if tuple(boundary_values) != NUMERIC_BOUNDARY_LEXEMES:
        raise ValueError("numeric-boundary lexeme matrix drift")
    if hashlib.sha256(boundary.data).hexdigest() != NUMERIC_BOUNDARY_SHA256:
        raise ValueError("numeric-boundary fixture bytes drift")
    if boundary.parameters != {"accepted_lexemes": len(NUMERIC_BOUNDARY_LEXEMES)}:
        raise ValueError("numeric-boundary parameters drift")

    extra = by_id["numeric-extra-spellings"]
    extra_values = [
        line.removeprefix(b"DA:1,").decode("ascii")
        for line in extra.data.splitlines()
        if line.startswith(b"DA:1,")
    ]
    if tuple(extra_values) != NUMERIC_EXTRA_LEXEMES:
        raise ValueError("numeric extra-spelling lexeme matrix drift")
    if b"-Inf" in extra.data:
        raise ValueError("numeric extra spellings must not absorb -Inf")
    if by_id["numeric-negative-inf"].data.count(b"DA:1,-Inf") != 1:
        raise ValueError("numeric-negative-inf fixture must remain the -Inf owner")

    format_atoms = by_id["numeric-format-atoms"]
    if hashlib.sha256(format_atoms.data).hexdigest() != format_atoms.parameters["sha256"]:
        raise ValueError("numeric-format-atoms source bytes drift")

    function_fixture = by_id["numeric-function-excessive"]
    if function_fixture.parameters != {"excessive_count_threshold": 100}:
        raise ValueError("numeric-function-excessive threshold drift")
    if [line for line in function_fixture.data.splitlines() if line.startswith(b"FNA:")] != [
        b"FNA:0,99,below_fn",
        b"FNA:1,100,at_fn",
        b"FNA:2,101,suppress_me",
    ]:
        raise ValueError("numeric-function-excessive count controls drift")
    if by_id["numeric-function-source"].parameters != {"role": "companion_source"}:
        raise ValueError("numeric-function-source role drift")


def validate_numeric_case_closure(
    cases: Iterable[dict[str, object]], fixtures: Iterable[Fixture]
) -> None:
    cases = list(cases)
    fixtures = list(fixtures)
    by_id = {case["id"]: case for case in cases}
    if len(by_id) != len(cases):
        raise ValueError("duplicate Oracle case IDs in numeric closure")
    if set(NUMERIC_LANE_EXPECTATIONS) != set(NUMERIC_LANE_CASE_IDS):
        raise ValueError("numeric lane case registry drift")
    missing = sorted(set(NUMERIC_LANE_CASE_IDS) - set(by_id))
    if missing:
        raise ValueError(f"missing numeric lane cases: {missing}")
    fixture_paths = {fixture.path for fixture in fixtures}
    expected_fixtures = {
        "numeric-format-atoms.excessive-stop-on-error-0": "fixtures/numeric/format-atoms.info",
        "numeric-format-atoms.excessive-stop-on-error-1": "fixtures/numeric/format-atoms.info",
        "numeric-negative-inf.semantic-snapshot": "fixtures/numeric/negative-inf.info",
        "numeric-fna-nonnumeric.semantic-snapshot": "fixtures/numeric/fna-nonnumeric.info",
        "numeric-fna-malformed-exponent.ignore-format": "fixtures/numeric/fna-malformed-exponent.info",
        "numeric-zero-fn-end.ignore-format": "fixtures/numeric/zero-fn-end.info",
        "numeric-zero-fn-end.semantic-snapshot": "fixtures/numeric/zero-fn-end.info",
        "numeric-invalid-fnl-fields.ignore-format": "fixtures/numeric/invalid-fnl-fields.info",
        "numeric-invalid-fnl-fields.semantic-snapshot": "fixtures/numeric/invalid-fnl-fields.info",
        "functions-zero-start.ignore-inconsistent-format": "fixtures/functions/zero-start.info",
        "functions-zero-start.semantic-snapshot": "fixtures/functions/zero-start.info",
        "numeric-function-excessive.default-stop": "fixtures/numeric/function-excessive.info",
        "numeric-function-excessive.erase-suppressed": "fixtures/numeric/function-excessive.info",
    }
    for case_id, (expected_exit, expected_output_exists) in NUMERIC_LANE_EXPECTATIONS.items():
        case = by_id[case_id]
        if case["expected_exit"] != expected_exit:
            raise ValueError(f"numeric lane exit policy drift: {case_id}")
        if expected_output_exists is None:
            if "expected_output_exists" in case:
                raise ValueError(f"numeric semantic output policy drift: {case_id}")
        elif case.get("expected_output_exists") is not expected_output_exists:
            raise ValueError(f"numeric lane output policy drift: {case_id}")
        if case.get("fixture") != expected_fixtures[case_id]:
            raise ValueError(f"numeric lane fixture binding drift: {case_id}")
        if case["fixture"] not in fixture_paths:
            raise ValueError(f"numeric lane references unknown fixture: {case_id}")
        is_semantic = case_id.endswith("semantic-snapshot")
        if is_semantic:
            if case.get("runner") != "inspect_model.pl" or case.get("output_file") is not None:
                raise ValueError(f"numeric semantic case shape drift: {case_id}")
        else:
            if case.get("runner") is not None or case.get("output_file") != "output.info":
                raise ValueError(f"numeric rewrite case shape drift: {case_id}")

    for case_id in (
        "numeric-function-excessive.default-stop",
        "numeric-function-excessive.erase-suppressed",
    ):
        if by_id[case_id].get("additional_fixtures") != {
            "function-excessive.c": "fixtures/numeric/function-excessive.c"
        }:
            raise ValueError(f"numeric function companion binding drift: {case_id}")

    for fixture_id in (
        "numeric-fna-malformed-exponent",
        "numeric-zero-fn-end",
        "numeric-invalid-fnl-fields",
    ):
        summary = by_id.get(f"{fixture_id}.summary")
        if summary is None or summary["expected_exit"] != 1 or summary.get("output_file") is not None:
            raise ValueError(f"numeric fixture summary closure drift: {fixture_id}")
    for fixture_id in ("numeric-function-excessive", "numeric-function-source"):
        if f"{fixture_id}.summary" in by_id:
            raise ValueError(f"companion/function fixture must not receive auto summary: {fixture_id}")

    reusable = {
        "functions-zero-start.summary",
        "functions-zero-start.ignore-inconsistent-format",
        "functions-zero-start.semantic-snapshot",
        "functions-zero-end.summary",
        "functions-zero-end.canonical",
    }
    if not reusable <= set(by_id):
        raise ValueError(f"zero-start/end reusable case closure drift: {sorted(reusable - set(by_id))}")


def build_numeric_oracle_cases() -> list[dict[str, object]]:
    numeric_cases = [
        {
            "id": "numeric-boundary.semantic-snapshot",
            "fixture": "fixtures/numeric-boundary.info",
            "requirement": "M1-TF-030",
            "description": "Semantic snapshot of the pinned 15-atom numeric acceptance matrix.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "numeric-extra-spellings.canonical",
            "fixture": "fixtures/numeric/extra-spellings.info",
            "requirement": "M1-TF-030",
            "description": "Canonical rewrite of additional legal numeric spellings +1/nan/+Inf.",
            "argv": [
                "lcov", "--no-function-coverage",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-extra-spellings.semantic-snapshot",
            "fixture": "fixtures/numeric/extra-spellings.info",
            "requirement": "M1-TF-030",
            "description": "Semantic snapshot for additional legal numeric spellings +1/nan/+Inf.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "numeric-format-atoms.default-stop",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-036",
            "description": "Default stop on first ERROR_NEGATIVE from M0-TF-NUMERIC-001 atoms; no output file.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "numeric-format-atoms.ignore-negative",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-032/036",
            "description": "Ignore negative only; next ERROR_FORMAT still stops without output.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--ignore-errors", "negative",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "numeric-format-atoms.ignore-format-negative.canonical",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-030/031/032/036",
            "description": "Ignore format and negative; rewrite retains coerced zeros and excessive values without threshold.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--ignore-errors", "format,negative",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-format-atoms.ignore-format-negative.semantic-snapshot",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-030/031/032",
            "description": "Semantic model after ignoring format and negative on M0-TF-NUMERIC-001 atoms.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl", "inspect_model.pl",
                "--ignore", "format,negative",
                "input.info",
            ],
            "expected_exit": 0,
        },
        {
            "id": "numeric-format-atoms.excessive-default-stop",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-033/036",
            "description": "With threshold 1000000, first excessive count stops and suppresses output.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--ignore-errors", "format,negative",
                "--rc", "excessive_count_threshold=1000000",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "numeric-format-atoms.excessive-keep-going",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-033/036",
            "description": "keep-going continues after excessive counts, writes output, and exits nonzero.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--ignore-errors", "format,negative",
                "--rc", "excessive_count_threshold=1000000",
                "--keep-going",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "numeric-format-atoms.excessive-stop-on-error-0",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-036",
            "description": "Explicit stop_on_error=0 continues after excessive counts, writes output, and exits nonzero.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--ignore-errors", "format,negative",
                "--rc", "excessive_count_threshold=1000000",
                "--rc", "stop_on_error=0",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-format-atoms.excessive-stop-on-error-1",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-036",
            "description": "Explicit stop_on_error=1 stops on the first excessive count and leaves output absent.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--ignore-errors", "format,negative",
                "--rc", "excessive_count_threshold=1000000",
                "--rc", "stop_on_error=1",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
            "expected_output_exists": False,
        },
        {
            "id": "numeric-format-atoms.ignore-format-negative-excessive.canonical",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-030/031/032/033/036",
            "description": "Ignore format/negative/excessive at threshold 1000000; retained excessive values and exit zero.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--ignore-errors", "format,negative,excessive",
                "--rc", "excessive_count_threshold=1000000",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-format-atoms.ignore-format-negative-excessive.semantic-snapshot",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-030/031/032/033",
            "description": "Semantic model after ignoring format/negative/excessive for M0-TF-NUMERIC-001.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl", "inspect_model.pl",
                "--ignore", "format,negative,excessive",
                "--excessive-threshold", "1000000",
                "input.info",
            ],
            "expected_exit": 0,
        },
        {
            "id": "numeric-signed-zero.canonical",
            "fixture": "fixtures/numeric/signed-zero.info",
            "requirement": "M1-TF-032",
            "description": "Canonical rewrite retains signed-zero DA and BRDA counts.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-signed-zero.semantic-snapshot",
            "fixture": "fixtures/numeric/signed-zero.info",
            "requirement": "M1-TF-032",
            "description": "Semantic snapshot for accepted negative zero across DA and BRDA.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "numeric-negative-inf.ignore-negative",
            "fixture": "fixtures/numeric/negative-inf.info",
            "requirement": "M1-TF-032/036",
            "description": "Ignore negative for -Inf coerces the count to zero in output.",
            "argv": [
                "lcov", "--no-function-coverage",
                "--ignore-errors", "negative",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-negative-inf.semantic-snapshot",
            "fixture": "fixtures/numeric/negative-inf.info",
            "requirement": "M1-TF-030/032",
            "description": "Semantic snapshot proving -Inf is Perl-numeric, categorized as negative, and coerced to zero when ignored.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "--ignore", "negative", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "numeric-fnda-negative.ignore-negative",
            "fixture": "fixtures/numeric/fnda-negative.info",
            "requirement": "M1-TF-032",
            "description": "Ignore negative on FNDA:-2 rewrites to FNA count zero.",
            "argv": [
                "lcov",
                "--ignore-errors", "negative",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-fnda-nonnumeric.ignore-format",
            "fixture": "fixtures/numeric/fnda-nonnumeric.info",
            "requirement": "M1-TF-031",
            "description": "Ignore format on nonnumeric FNDA rewrites to FNA count zero.",
            "argv": [
                "lcov",
                "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-fna-nonnumeric.ignore-format",
            "fixture": "fixtures/numeric/fna-nonnumeric.info",
            "requirement": "M1-TF-031",
            "description": "Ignore format on ordinary nonnumeric FNA rewrites count zero.",
            "argv": [
                "lcov",
                "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-fna-nonnumeric.semantic-snapshot",
            "fixture": "fixtures/numeric/fna-nonnumeric.info",
            "requirement": "M1-TF-031",
            "description": "Semantic snapshot after ordinary nonnumeric FNA format recovery.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "--ignore", "format", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "numeric-fna-malformed-exponent.ignore-format",
            "fixture": "fixtures/numeric/fna-malformed-exponent.info",
            "requirement": "M1-TF-031",
            "description": "Ignore format on malformed-exponent FNA rewrites count zero.",
            "argv": [
                "lcov", "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-brda-nonnumeric.ignore-format",
            "fixture": "fixtures/numeric/brda-nonnumeric.info",
            "requirement": "M1-TF-031",
            "description": "Ignore format on nonnumeric BRDA taken rewrites to zero.",
            "argv": [
                "lcov", "--branch-coverage", "--no-function-coverage",
                "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-mcdc-nondigit.ignore-format",
            "fixture": "fixtures/numeric/mcdc-nondigit.info",
            "requirement": "M1-TF-031",
            "description": "Ignore format on digit-only MC/DC violation skips the bad true sense and retains the false sense.",
            "argv": [
                "lcov", "--mcdc-coverage", "--no-function-coverage",
                "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-zero-brda.summary",
            "fixture": "fixtures/numeric/zero-brda.info",
            "requirement": "M1-TF-034",
            "description": "Default summary rejects zero BRDA line number.",
            "argv": ["lcov", "--branch-coverage", "--summary", "input.info"],
            "expected_exit": 1,
        },
        {
            "id": "numeric-zero-mcdc.ignore-format",
            "fixture": "fixtures/numeric/zero-mcdc.info",
            "requirement": "M1-TF-034",
            "description": "Ignore format retains zero MCDC line and synthesizes the complementary sense.",
            "argv": [
                "lcov", "--mcdc-coverage", "--no-function-coverage",
                "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-zero-fn.ignore-format",
            "fixture": "fixtures/numeric/zero-fn.info",
            "requirement": "M1-TF-034",
            "description": "Ignore format retains zero FN start line in current FNL rewrite.",
            "argv": [
                "lcov",
                "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "numeric-zero-fn-end.ignore-format",
            "fixture": "fixtures/numeric/zero-fn-end.info",
            "requirement": "M1-TF-034",
            "description": "Ignore format retains zero legacy FN end line in current FNL rewrite.",
            "argv": [
                "lcov", "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-zero-fn-end.semantic-snapshot",
            "fixture": "fixtures/numeric/zero-fn-end.info",
            "requirement": "M1-TF-034",
            "description": "Semantic snapshot after zero legacy FN end-line format recovery.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "--ignore", "format", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "numeric-invalid-fnl-fields.ignore-format",
            "fixture": "fixtures/numeric/invalid-fnl-fields.info",
            "requirement": "M1-TF-034",
            "description": "Ignore format drops nondigit FNL start/end declarations and retains the valid sentinel function.",
            "argv": [
                "lcov", "--ignore-errors", "format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-invalid-fnl-fields.semantic-snapshot",
            "fixture": "fixtures/numeric/invalid-fnl-fields.info",
            "requirement": "M1-TF-034",
            "description": "Semantic snapshot proving invalid FNL declarations do not populate the index map.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "--ignore", "format", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "functions-zero-start.ignore-inconsistent-format",
            "fixture": "fixtures/functions/zero-start.info",
            "requirement": "M1-TF-034",
            "description": "Ignore inconsistent and format errors to retain current FNL start zero and its repaired hit count.",
            "argv": [
                "lcov", "--ignore-errors", "inconsistent,format",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "functions-zero-start.semantic-snapshot",
            "fixture": "fixtures/functions/zero-start.info",
            "requirement": "M1-TF-034",
            "description": "Semantic snapshot after current FNL zero-start consistency repair.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl", "inspect_model.pl", "--ignore", "inconsistent,format", "input.info",
            ],
            "expected_exit": 0,
        },
        {
            "id": "numeric-function-excessive.default-stop",
            "fixture": "fixtures/numeric/function-excessive.info",
            "requirement": "M1-TF-033",
            "description": "Function count 101 exceeds threshold 100 without a matching suppression pattern.",
            "argv": [
                "lcov", "--rc", "excessive_count_threshold=100",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "additional_fixtures": {
                "function-excessive.c": "fixtures/numeric/function-excessive.c"
            },
            "expected_exit": 1,
            "expected_output_exists": False,
        },
        {
            "id": "numeric-function-excessive.erase-suppressed",
            "fixture": "fixtures/numeric/function-excessive.info",
            "requirement": "M1-TF-033",
            "description": "erase_functions suppresses the excessive diagnostic for the matching function while filtering it from output.",
            "argv": [
                "lcov", "--rc", "excessive_count_threshold=100",
                "--rc", "erase_functions=^suppress_me$",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "additional_fixtures": {
                "function-excessive.c": "fixtures/numeric/function-excessive.c"
            },
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-inf-excessive.ignore-excessive",
            "fixture": "fixtures/numeric/inf-excessive.info",
            "requirement": "M1-TF-033",
            "description": "Ignore excessive retains Inf and NaN counts above threshold.",
            "argv": [
                "lcov", "--no-function-coverage",
                "--rc", "excessive_count_threshold=100",
                "--ignore-errors", "excessive",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "checksum-match.summary",
            "fixture": "fixtures/numeric/checksum-match.info",
            "requirement": "M1-TF-035",
            "description": "Matching DA checksum with companion source under --checksum.",
            "argv": ["lcov", "--checksum", "--no-function-coverage", "--summary", "input.info"],
            "additional_fixtures": {"cs.c": "fixtures/numeric/cs.c"},
            "expected_exit": 0,
        },
        {
            "id": "checksum-match.canonical",
            "fixture": "fixtures/numeric/checksum-match.info",
            "requirement": "M1-TF-035",
            "description": "Canonical rewrite retains matching checksum under --checksum.",
            "argv": [
                "lcov", "--checksum", "--no-function-coverage",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "additional_fixtures": {"cs.c": "fixtures/numeric/cs.c"},
            "expected_exit": 0,
        },
        {
            "id": "checksum-mismatch.summary",
            "fixture": "fixtures/numeric/checksum-mismatch.info",
            "requirement": "M1-TF-035",
            "description": "Mismatched DA checksum is ERROR_VERSION under --checksum.",
            "argv": ["lcov", "--checksum", "--no-function-coverage", "--summary", "input.info"],
            "additional_fixtures": {"cs.c": "fixtures/numeric/cs.c"},
            "expected_exit": 1,
        },
        {
            "id": "checksum-mismatch.ignore-version",
            "fixture": "fixtures/numeric/checksum-mismatch.info",
            "requirement": "M1-TF-035/036",
            "description": "Ignore version keeps the recorded mismatched checksum in output.",
            "argv": [
                "lcov", "--checksum", "--no-function-coverage",
                "--ignore-errors", "version",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "additional_fixtures": {"cs.c": "fixtures/numeric/cs.c"},
            "expected_exit": 0,
        },
        {
            "id": "checksum-missing.summary",
            "fixture": "fixtures/numeric/checksum-missing.info",
            "requirement": "M1-TF-035",
            "description": "Missing DA checksum is ERROR_VERSION under --checksum.",
            "argv": ["lcov", "--checksum", "--no-function-coverage", "--summary", "input.info"],
            "additional_fixtures": {"cs.c": "fixtures/numeric/cs.c"},
            "expected_exit": 1,
        },
        {
            "id": "checksum-missing.ignore-version-recompute",
            "fixture": "fixtures/numeric/checksum-missing.info",
            "requirement": "M1-TF-035",
            "description": "Ignore version recomputes the missing checksum from companion source into output.",
            "argv": [
                "lcov", "--checksum", "--no-function-coverage",
                "--ignore-errors", "version",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "additional_fixtures": {"cs.c": "fixtures/numeric/cs.c"},
            "expected_exit": 0,
        },
        {
            "id": "checksum-duplicate.summary",
            "fixture": "fixtures/numeric/checksum-duplicate.info",
            "requirement": "M1-TF-035",
            "description": "Second stored checksum for the same source line mismatches under --checksum.",
            "argv": ["lcov", "--checksum", "--no-function-coverage", "--summary", "input.info"],
            "additional_fixtures": {"cs.c": "fixtures/numeric/cs.c"},
            "expected_exit": 1,
        },
        {
            "id": "checksum-duplicate.ignore-version",
            "fixture": "fixtures/numeric/checksum-duplicate.info",
            "requirement": "M1-TF-035/036",
            "description": "Ignore version continues after duplicate/mismatched stored checksums.",
            "argv": [
                "lcov", "--checksum", "--no-function-coverage",
                "--ignore-errors", "version",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "additional_fixtures": {"cs.c": "fixtures/numeric/cs.c"},
            "expected_exit": 0,
        },
        {
            "id": "checksum-no-verify.canonical",
            "fixture": "fixtures/numeric/checksum-match.info",
            "requirement": "M1-TF-035",
            "description": "Without --checksum, stored input checksums are not emitted.",
            "argv": [
                "lcov", "--no-function-coverage",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
    ]

    return numeric_cases
