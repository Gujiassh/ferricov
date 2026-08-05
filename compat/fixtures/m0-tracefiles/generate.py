#!/usr/bin/env python3
"""Generate the byte-exact M0 tracefile compatibility corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
ORACLE_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
ORACLE_IMAGE = "ferricov/lcov-oracle:v2.5"
ORACLE_IMAGE_ID = "sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e"
ORACLE_EXECUTABLE_SHA256 = "d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252"
KNOWN_TAGS = (
    "TN", "SF", "KF", "VER", "FNL", "FNA", "FN", "FNDA", "FNF",
    "FNH", "BRDA", "BRF", "BRH", "MCDC", "MCF", "MCH", "DA", "LF",
    "LH",
)
SUMMARY_TAGS = ("FNF", "FNH", "BRF", "BRH", "MCF", "MCH", "LF", "LH")

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


@dataclass(frozen=True)
class Fixture:
    id: str
    path: str
    group: str
    description: str
    data: bytes
    oracle_default: str
    committed: bool = True
    parameters: dict[str, int | str] | None = None


def ascii_bytes(text: str, newline: bytes = b"\n", final_newline: bool = True) -> bytes:
    lines = text.strip("\n").split("\n")
    data = newline.join(line.encode("ascii") for line in lines)
    return data + (newline if final_newline else b"")


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


def current_fixture() -> Fixture:
    data = ascii_bytes(
        """
TN:current,diff
SF:src/current.c
VER:rev-current
FNL:0,1,4
FNA:0,3,alpha
FNA:0,0,alpha_alias
FNL:1,5,5
FNA:1,0,beta
FNF:999
FNH:not-a-number
BRDA:2,0,plain,1
BRDA:2,fU0,x > 0,0
BRDA:3,e0,exception,0
BRDA:3,0,normal,1
BRF:999
BRH:
MCDC:4,U1,t,1,0,cond
MCDC:4,1,f,0,0,cond
MCF:anything
MCH
DA:1,3,checksumA
DA:2,1
DA:3,1
DA:4,1
DA:5,0
LF:999
LH:bad
end_of_record
"""
    )
    return Fixture(
        "current-all-records",
        "fixtures/current-all-records.info",
        "current-all-records",
        "Current writer vocabulary with stable FNL/FNA, fallthrough and unreachable branches, unreachable MC/DC, checksums, and ignored summary payloads.",
        data,
        "accept",
    )


def legacy_fixture() -> Fixture:
    data = ascii_bytes(
        """
TN:legacy
SF:src/legacy.c
FN:10,20,legacy_main
FN:30,legacy_helper
FNDA:4,legacy_main
FNDA:0,legacy_helper
FNF:2
FNH:1
DA:10,4
DA:20,1
DA:30,0
LF:3
LH:2
end_of_record
"""
    )
    return Fixture(
        "legacy",
        "fixtures/legacy.info",
        "legacy",
        "Obsolete FN/FNDA input whose Oracle rewrite is current FNL/FNA form.",
        data,
        "accept",
    )


def permissive_fixture() -> Fixture:
    data = ascii_bytes(
        """
#column-zero comment
TN:,diff-and-ignored
KF:src/permissive.c
DA:1,1,checksum,ignored-suffix
FNF:not-a-number
FNH
BRF_without_colon
BRH:garbage
MCF:
MCH:1,trailing
LF999
LH:NaN
end_of_record_and_ignored
"""
    )
    return Fixture(
        "permissive-prefix",
        "fixtures/permissive-prefix.info",
        "permissive-prefix",
        "Observed prefix matching for TN, DA, all summary tags, the terminator, and the undocumented KF source tag.",
        data,
        "accept",
    )


def malformed_fixtures() -> list[Fixture]:
    cases = [
        ("malformed-tn", "TN", "TN", "reject", "TN missing its colon"),
        ("malformed-sf", "SF:", "SF", "reject", "empty SF payload"),
        ("malformed-kf", "KF:", "KF", "reject", "empty KF payload"),
        ("malformed-ver", "VER:", "VER", "reject", "empty VER payload"),
        ("malformed-da", "DA:1", "DA", "reject", "DA missing its count"),
        ("malformed-fn", "FN:1,", "FN", "reject", "FN missing its name"),
        ("malformed-fnda", "FNDA:1,", "FNDA", "reject", "FNDA missing its name"),
        ("malformed-fnl", "FNL:0", "FNL", "reject", "FNL missing its start line"),
        ("malformed-fna", "FNA:9,1,unknown", "FNA", "reject", "FNA references an unknown index"),
        ("malformed-brda", "BRDA:1,x0,expr,1", "BRDA", "reject", "BRDA uses an unknown branch type"),
        ("malformed-mcdc", "MCDC:1,1,x,1,0,expr", "MCDC", "reject", "MCDC uses an unknown sense"),
        ("malformed-terminator", "END_OF_RECORD", "end_of_record", "reject", "terminator uses the wrong case"),
        ("malformed-unknown", "ZZ:unknown", "unknown", "reject", "unknown nonblank record"),
    ]
    fixtures = [
        Fixture(
            fixture_id,
            f"fixtures/malformed/{tag.lower()}.info",
            "malformed-per-record",
            description,
            valid_wrapper(record, fixture_id),
            decision,
        )
        for fixture_id, record, tag, decision, description in cases
    ]
    for tag in SUMMARY_TAGS:
        fixtures.append(
            Fixture(
                f"malformed-{tag.lower()}-accepted",
                f"fixtures/malformed/{tag.lower()}-accepted.info",
                "malformed-per-record",
                f"Malformed {tag} payload is accepted because summaries are prefix-only.",
                valid_wrapper(f"{tag}:not-a-count,trailing", f"{tag.lower()}-accepted"),
                "accept",
            )
        )
    return fixtures


def byte_fixtures() -> list[Fixture]:
    basic = "TN:bytes\nSF:src/bytes.c\nDA:1,1\nLF:1\nLH:1\nend_of_record"
    non_utf8 = (
        b"TN:test-\xff\n"
        b"SF:src/path-\xfe.c\n"
        b"VER:revision-\xfd\n"
        b"FNL:0,1,1\n"
        b"FNA:0,1,alias-\xfc\n"
        b"FNF:1\nFNH:1\n"
        b"BRDA:1,0,branch-\xfb,1\nBRDA:1,0,other,0\nBRF:2\nBRH:1\n"
        b"MCDC:1,1,t,1,0,mcdc-\xfa\nMCDC:1,1,f,0,0,mcdc-\xfa\nMCF:2\nMCH:1\n"
        b"DA:1,1\nLF:1\nLH:1\nend_of_record\n"
    )
    nul = b"TN:nul\nSF:src/nul-\x00.c\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"
    return [
        Fixture(
            "bytes-crlf",
            "fixtures/bytes/crlf.info",
            "byte-boundary",
            "CRLF framing with a final newline.",
            ascii_bytes(basic, newline=b"\r\n"),
            "accept",
        ),
        Fixture(
            "bytes-no-final-newline",
            "fixtures/bytes/no-final-newline.info",
            "byte-boundary",
            "LF framing without a final newline.",
            ascii_bytes(basic, final_newline=False),
            "accept",
        ),
        Fixture(
            "bytes-non-utf8",
            "fixtures/bytes/non-utf8.info",
            "byte-boundary",
            "Invalid UTF-8 bytes in test, source, version, function, branch, and MC/DC fields.",
            non_utf8,
            "accept",
        ),
        Fixture(
            "bytes-nul-accepted",
            "fixtures/bytes/nul-accepted.info",
            "byte-boundary",
            "Embedded NUL in an SF path; the pinned Oracle accepts it with a Perl pathname warning.",
            nul,
            "accept",
        ),
    ]


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


def state_ownership_fixtures() -> list[Fixture]:
    late = ascii_bytes(
        """
TN:A
SF:/m0/late-tn.c
FNL:0,1,1
FNA:0,1,f
BRDA:1,0,edge,1
MCDC:1,1,t,1,0,cond
DA:1,1
TN:B
MCDC:1,1,f,1,0,cond
end_of_record
"""
    )
    cross_success = ascii_bytes(
        """
TN:A
SF:/m0/first.c
MCDC:1,1,t,1,0,first
DA:1,1
TN:B
SF:/m0/next.c
MCDC:2,1,t,1,0,second
DA:2,1
end_of_record
"""
    )
    cross_duplicate = ascii_bytes(
        """
TN:A
SF:/m0/first.c
MCDC:1,1,t,1,0,first
DA:1,1
TN:B
SF:/m0/next.c
MCDC:2,1,t,1,0,second
MCDC:1,1,f,1,0,first
DA:2,1
end_of_record
"""
    )
    return [
        Fixture(
            "state-late-tn-mcdc",
            "fixtures/state/late-tn-mcdc.info",
            "state-ownership",
            "Late TN during an open MC/DC block: line/function/branch stay on A while closed MC/DC clones under B.",
            late,
            "accept",
        ),
        Fixture(
            "state-cross-sf-mcdc-success",
            "fixtures/state/cross-sf-mcdc-success.info",
            "state-ownership",
            "Cross-SF while MC/DC is open without terminator: first source is filtered; surviving next-source ownership and both line MC/DC blocks under B.",
            cross_success,
            "accept",
        ),
        Fixture(
            "state-cross-sf-mcdc-duplicate",
            "fixtures/state/cross-sf-mcdc-duplicate.info",
            "state-ownership",
            "Cross-SF return-to-line1 MC/DC after line2: hard-fails with MCDC already defined for 1.",
            cross_duplicate,
            "reject",
        ),
    ]


def ver_repeat_equal_fixture() -> Fixture:
    data = ascii_bytes(
        """
TN:ver_eq
SF:src/ver-equal.c
VER:rev-1.0
VER:rev-1.0
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    return Fixture(
        "ver-repeat-equal",
        "fixtures/ver/repeat-equal.info",
        "ver-semantics",
        "Same VER repeated within one source section; accepted and canonical output emits at most one version.",
        data,
        "accept",
    )


def ver_repeat_different_fixture() -> Fixture:
    data = ascii_bytes(
        """
TN:ver_diff
SF:src/ver-diff.c
VER:rev-1.0
VER:rev-2.0
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    return Fixture(
        "ver-repeat-different",
        "fixtures/ver/repeat-different.info",
        "ver-semantics",
        "Different second VER for the same source is an unconditional failure, not an ignorable ERROR_VERSION case.",
        data,
        "reject",
    )


def ver_per_source_fixture() -> Fixture:
    data = ascii_bytes(
        """
TN:ver_src_a
SF:src/ver-src-a.c
VER:rev-a
DA:1,1
LF:1
LH:1
end_of_record
TN:ver_src_b
SF:src/ver-src-b.c
VER:rev-b
DA:2,1
LF:1
LH:1
end_of_record
"""
    )
    return Fixture(
        "ver-per-source",
        "fixtures/ver/per-source.info",
        "ver-semantics",
        "Separate terminated sources retain independent versions in one input.",
        data,
        "accept",
    )



def function_record_fixtures() -> list[Fixture]:
    current_core = ascii_bytes(
        """
TN:fn_current
SF:src/fn-current.c
FNL:0,10,20
FNA:0,1,alpha
FNA:0,2,alpha_alias,with,commas
FNA:0,3,alpha
FNL:5,30,40
FNA:5,0,beta
FNL:7,50
FNA:7,1,gamma
DA:10,1
DA:20,1
DA:30,0
DA:40,0
DA:50,1
DA:51,1
LF:6
LH:4
end_of_record
"""
    )
    missing_alias = ascii_bytes(
        """
TN:fn_missing_alias
SF:src/fn-missing-alias.c
FNL:0,1,2
FNA:0,1
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    zero_end = ascii_bytes(
        """
TN:fn_zero_end
SF:src/fn-zero-end.c
FNL:0,5,0
FNA:0,0,zero_end
DA:5,1
LF:1
LH:1
end_of_record
"""
    )
    zero_start = ascii_bytes(
        """
TN:fn_zero_start
SF:src/fn-zero-start.c
FNL:0,0,5
FNA:0,0,zero_start
DA:1,1
DA:5,1
LF:2
LH:2
end_of_record
"""
    )
    mixed_merge = ascii_bytes(
        """
TN:fn_mix
SF:src/fn-mix.c
FN:10,20,alpha
FNDA:1,alpha
FNL:0,10,20
FNA:0,2,alpha
FNA:0,3,alpha_alias
DA:10,1
DA:20,1
LF:2
LH:2
end_of_record
"""
    )
    mixed_location = ascii_bytes(
        """
TN:fn_mix_loc
SF:src/fn-mix-loc.c
FN:10,20,alpha
FNL:0,30,40
FNA:0,1,alpha
DA:10,1
DA:30,1
LF:2
LH:2
end_of_record
"""
    )
    mixed_range = ascii_bytes(
        """
TN:fn_mix_range
SF:src/fn-mix-range.c
FN:10,20,alpha
FNL:0,10,40
FNA:0,1,alpha
DA:10,1
DA:20,1
DA:40,1
LF:3
LH:3
end_of_record
"""
    )
    index_duplicate = ascii_bytes(
        """
TN:fn_idx_dup
SF:src/fn-idx-dup.c
FNL:0,1,2
FNA:0,1,a
FNL:0,3,4
FNA:0,1,b
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    index_unknown = ascii_bytes(
        """
TN:fn_idx_unk
SF:src/fn-idx-unk.c
FNA:9,1,ghost
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    index_scope_reset = ascii_bytes(
        """
TN:fn_scope_a
SF:src/fn-scope-a.c
FNL:0,1,2
FNA:0,1,fa
DA:1,1
LF:1
LH:1
end_of_record
TN:fn_scope_b
SF:src/fn-scope-b.c
FNL:0,3,4
FNA:0,2,fb
DA:3,1
LF:1
LH:1
end_of_record
"""
    )
    index_tn_preserves = ascii_bytes(
        """
TN:fn_tn_a
SF:src/fn-tn-preserve.c
FNL:0,1,2
FNA:0,1,fa
TN:fn_tn_b
FNL:0,3,4
FNA:0,1,fb
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    return [
        Fixture(
            "functions-current-core",
            "fixtures/functions/current-core.info",
            "function-records",
            "Current FNL/FNA with optional end, comma-bearing alias text, repeated aliases, and noncontiguous indices.",
            current_core,
            "accept",
        ),
        Fixture(
            "functions-current-missing-alias",
            "fixtures/functions/current-missing-alias.info",
            "function-records",
            "FNA missing the alias field is a format failure.",
            missing_alias,
            "reject",
        ),
        Fixture(
            "functions-zero-end",
            "fixtures/functions/zero-end.info",
            "function-records",
            "FNL end line zero is accepted and retained when the alias hit is zero.",
            zero_end,
            "accept",
        ),
        Fixture(
            "functions-zero-start",
            "fixtures/functions/zero-start.info",
            "function-records",
            "FNL start line zero is retained at parse time but fails default consistency checks.",
            zero_start,
            "reject",
        ),
        Fixture(
            "functions-mixed-merge",
            "fixtures/functions/mixed-merge.info",
            "function-records",
            "Compatible mixed FN/FNDA and FNL/FNA records merge counts into one current-format group.",
            mixed_merge,
            "accept",
        ),
        Fixture(
            "functions-mixed-location-mismatch",
            "fixtures/functions/mixed-location-mismatch.info",
            "function-records",
            "Legacy and current records sharing a name at different start lines hard-fail as inconsistent data.",
            mixed_location,
            "reject",
        ),
        Fixture(
            "functions-mixed-range-mismatch",
            "fixtures/functions/mixed-range-mismatch.info",
            "function-records",
            "Legacy and current records sharing a start line with different end lines hard-fail as inconsistent data.",
            mixed_range,
            "reject",
        ),
        Fixture(
            "functions-index-duplicate",
            "fixtures/functions/index-duplicate.info",
            "function-records",
            "Duplicate FNL index within one source section is an unconditional hard failure.",
            index_duplicate,
            "reject",
        ),
        Fixture(
            "functions-index-unknown",
            "fixtures/functions/index-unknown.info",
            "function-records",
            "FNA that references an unknown FNL index is an unconditional hard failure.",
            index_unknown,
            "reject",
        ),
        Fixture(
            "functions-index-scope-reset",
            "fixtures/functions/index-scope-reset.info",
            "function-records",
            "A new SF record clears the current-format function index map so later sections may reuse indices.",
            index_scope_reset,
            "accept",
        ),
        Fixture(
            "functions-index-tn-preserves",
            "fixtures/functions/index-tn-preserves.info",
            "function-records",
            "A TN record alone does not clear FNL indices; reusing an index before the next SF hard-fails.",
            index_tn_preserves,
            "reject",
        ),
    ]


def branch_record_fixtures() -> list[Fixture]:
    forms_core = ascii_bytes(
        """
TN:br_forms
SF:src/br-forms.c
BRDA:10,0,cond,1
BRDA:10,0,!cond,0
BRDA:20,e0,exception,0
BRDA:20,0,normal,1
BRDA:30,f0,fall,1
BRDA:30,0,nofall,0
BRDA:40,U0,unreach,0
BRDA:40,0,reach,1
BRDA:50,0,never,-
BRDA:50,0,other,1
BRDA:60,0,a,b,c,2
BRDA:60,0,plain,0
BRDA:70,0,0,1
BRDA:70,0,1,0
DA:10,1
DA:20,1
DA:30,1
DA:40,1
DA:50,1
DA:60,1
DA:70,1
LF:7
LH:7
end_of_record
"""
    )
    u_modes = ascii_bytes(
        """
TN:br_u_modes
SF:src/br-u-modes.c
BRDA:10,U0,unreach,0
BRDA:10,0,reach,1
BRDA:20,fU0,x > 0,0
BRDA:20,0,x <= 0,1
BRDA:30,eU0,exc,0
BRDA:30,0,norm,1
DA:10,1
DA:20,1
DA:30,1
LF:3
LH:3
end_of_record
"""
    )
    malformed_tail = ascii_bytes(
        """
TN:br_malformed_tail
SF:src/br-malformed-tail.c
BRDA:1,0,expr
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    malformed_tail_empty_taken = ascii_bytes(
        """
TN:br_malformed_tail_empty_taken
SF:src/br-malformed-tail-empty-taken.c
BRDA:1,0,expr,
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    malformed_tail_empty_expression = ascii_bytes(
        """
TN:br_malformed_tail_empty_expression
SF:src/br-malformed-tail-empty-expression.c
BRDA:1,0,,1
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    expression_mismatch = ascii_bytes(
        """
TN:br_expression_mismatch
SF:src/br-expression-mismatch.c
BRDA:10,0,first,1
BRDA:10,0,second,0
DA:10,1
LF:1
LH:1
end_of_record
"""
    )
    expression_merge_left = ascii_bytes(
        """
TN:br_expression_merge
SF:src/br-expression-merge.c
BRDA:10,0,left,1
BRDA:10,0,left_else,0
DA:10,1
LF:1
LH:1
end_of_record
"""
    )
    expression_merge_right = ascii_bytes(
        """
TN:br_expression_merge
SF:src/br-expression-merge.c
BRDA:10,0,right,2
BRDA:10,0,right_else,3
DA:10,2
LF:1
LH:1
end_of_record
"""
    )
    order_gaps = ascii_bytes(
        """
TN:br_order
SF:src/br-order.c
BRDA:10,5,a,1
BRDA:10,5,b,0
BRDA:10,2,c,1
BRDA:10,2,d,0
BRDA:10,9,e,1
BRDA:10,9,f,0
DA:10,1
LF:1
LH:1
end_of_record
"""
    )
    noncontiguous = ascii_bytes(
        """
TN:br_noncont
SF:src/br-noncont.c
BRDA:10,0,a,1
BRDA:10,0,b,0
BRDA:20,0,c,1
BRDA:20,0,d,0
BRDA:10,0,e,1
BRDA:10,0,f,0
DA:10,1
DA:20,1
LF:2
LH:2
end_of_record
"""
    )
    interleave = ascii_bytes(
        """
TN:br_inter
SF:src/br-inter.c
BRDA:10,0,a,1
BRDA:10,1,c,1
BRDA:10,0,b,0
BRDA:10,1,d,0
DA:10,1
LF:1
LH:1
end_of_record
"""
    )
    sort_signatures = ascii_bytes(
        """
TN:br_sort
SF:src/br-sort.c
BRDA:10,0,a0,1
BRDA:10,0,a1,0
BRDA:10,0,a2,1
BRDA:10,1,b0,1
BRDA:10,1,b1,0
BRDA:10,e2,e0,1
BRDA:10,f3,f0,1
BRDA:10,3,f1,0
DA:10,1
LF:1
LH:1
end_of_record
"""
    )
    return [
        Fixture(
            "branches-forms-core",
            "fixtures/branches/forms-core.info",
            "branch-records",
            "BRDA vanilla, exception, fallthrough, U, dash taken, comma-bearing expression, and numeric expression identity.",
            forms_core,
            "accept",
        ),
        Fixture(
            "branches-u-modes",
            "fixtures/branches/u-modes.info",
            "branch-records",
            "U, fU, and eU BRDA forms used to pin both ignore_unreachable_flag modes.",
            u_modes,
            "accept",
        ),
        Fixture(
            "branches-malformed-tail",
            "fixtures/branches/malformed-tail.info",
            "branch-records",
            "BRDA missing the final taken delimiter is a format/corrupt failure with non-integer taken diagnostics.",
            malformed_tail,
            "reject",
        ),
        Fixture(
            "branches-malformed-tail-empty-taken",
            "fixtures/branches/malformed-tail-empty-taken.info",
            "branch-records",
            "BRDA with an empty final taken field is parsed as an empty count and rejected as format/corrupt.",
            malformed_tail_empty_taken,
            "reject",
        ),
        Fixture(
            "branches-malformed-tail-empty-expression",
            "fixtures/branches/malformed-tail-empty-expression.info",
            "branch-records",
            "BRDA with an empty expression and numeric taken field is accepted and retained by the canonical writer.",
            malformed_tail_empty_expression,
            "accept",
        ),
        Fixture(
            "branches-expression-mismatch",
            "fixtures/branches/expression-mismatch.info",
            "branch-records",
            "Different expressions under one input block token remain separate positional branch elements.",
            expression_mismatch,
            "accept",
        ),
        Fixture(
            "branches-expression-merge-left",
            "fixtures/branches/expression-merge-left.info",
            "branch-records",
            "Left tracefile for positional branch merge with distinct expressions and counts.",
            expression_merge_left,
            "accept",
        ),
        Fixture(
            "branches-expression-merge-right",
            "fixtures/branches/expression-merge-right.info",
            "branch-records",
            "Right tracefile for positional branch merge with distinct expressions and counts.",
            expression_merge_right,
            "accept",
        ),
        Fixture(
            "branches-order-gaps",
            "fixtures/branches/order-gaps.info",
            "branch-records",
            "Input block gaps renumber contiguously in appearance order on write.",
            order_gaps,
            "accept",
        ),
        Fixture(
            "branches-noncontiguous",
            "fixtures/branches/noncontiguous.info",
            "branch-records",
            "Revisiting a line/block after another line creates a new positional block rather than keyed reuse.",
            noncontiguous,
            "accept",
        ),
        Fixture(
            "branches-interleave",
            "fixtures/branches/interleave.info",
            "branch-records",
            "Interleaved block tokens on one line open new positional blocks on each line/block transition.",
            interleave,
            "accept",
        ),
        Fixture(
            "branches-sort-signatures",
            "fixtures/branches/sort-signatures.info",
            "branch-records",
            "Canonical writer sorts branch blocks by signature length, signature text, then appearance index.",
            sort_signatures,
            "accept",
        ),
    ]


def scale_fixture(profile: str, sections: int, lines_per_section: int) -> Fixture:
    chunks: list[str] = []
    for section in range(sections):
        hit_lines = 0
        chunks.extend(
            [
                f"TN:{profile}_{section:06d}",
                f"SF:src/generated/{profile}/file-{section:06d}.c",
                f"FNL:0,1,{lines_per_section}",
                f"FNA:0,{section % 7 + 1},generated_{section:06d}",
                "FNF:1",
                "FNH:1",
                "BRDA:1,0,condition,1",
                "BRDA:1,f0,!condition,0",
                "BRF:2",
                "BRH:1",
                "MCDC:2,1,t,1,0,condition",
                "MCDC:2,1,f,0,0,condition",
                "MCF:2",
                "MCH:1",
            ]
        )
        for line in range(1, lines_per_section + 1):
            count = 1 if line <= 2 else (section * 17 + line * 31) % 5
            hit_lines += int(count > 0)
            chunks.append(f"DA:{line},{count}")
        chunks.extend([f"LF:{lines_per_section}", f"LH:{hit_lines}", "end_of_record"])
    return Fixture(
        f"scale-{profile}",
        f"generated/{profile}.info",
        "deterministic-scale",
        f"Deterministic {profile} parse/write workload; generated on demand and not committed.",
        ascii_bytes("\n".join(chunks)),
        "accept",
        committed=False,
        parameters={
            "algorithm_version": 1,
            "sections": sections,
            "lines_per_section": lines_per_section,
            "records_per_section": lines_per_section + 17,
        },
    )


def build_fixtures() -> list[Fixture]:
    fixtures = [current_fixture(), legacy_fixture(), permissive_fixture()]
    fixtures.extend(malformed_fixtures())
    fixtures.extend(byte_fixtures())
    fixtures.extend(numeric_fixtures())
    fixtures.extend(state_ownership_fixtures())
    fixtures.extend(
        [ver_repeat_equal_fixture(), ver_repeat_different_fixture(), ver_per_source_fixture()]
    )
    fixtures.extend(function_record_fixtures())
    fixtures.extend(branch_record_fixtures())
    fixtures.extend(
        [
            scale_fixture("medium", sections=256, lines_per_section=64),
            scale_fixture("large", sections=2048, lines_per_section=128),
        ]
    )
    ids = [fixture.id for fixture in fixtures]
    paths = [fixture.path for fixture in fixtures]
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise ValueError("fixture IDs and paths must be unique")
    validate_numeric_fixture_closure(fixtures)
    return fixtures


def classify_record(line: bytes) -> str | None:
    normalized = line.rstrip(b" \t\r\n\f\v")
    if not normalized:
        return None
    if normalized.startswith(b"#"):
        return "comment"
    if normalized.startswith(b"end_of_record"):
        return "end_of_record"
    for tag in KNOWN_TAGS:
        if normalized.startswith(tag.encode("ascii") + b":"):
            return tag
        if tag in SUMMARY_TAGS and normalized.startswith(tag.encode("ascii")):
            return tag
    return "unknown"


def data_metadata(data: bytes) -> dict[str, object]:
    lines = data.split(b"\n")
    if data.endswith(b"\n"):
        lines.pop()
    counts: dict[str, int] = {}
    record_count = 0
    for line in lines:
        kind = classify_record(line)
        if kind is None:
            continue
        counts[kind] = counts.get(kind, 0) + 1
        if kind != "comment":
            record_count += 1
    lf_count = data.count(b"\n")
    crlf_count = data.count(b"\r\n")
    if lf_count == 0:
        line_endings = "none"
    elif crlf_count == lf_count:
        line_endings = "crlf"
    elif crlf_count == 0:
        line_endings = "lf"
    else:
        line_endings = "mixed"
    try:
        data.decode("utf-8")
        valid_utf8 = True
    except UnicodeDecodeError:
        valid_utf8 = False
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
        "record_count": record_count,
        "record_counts": dict(sorted(counts.items())),
        "line_endings": line_endings,
        "final_newline": data.endswith(b"\n"),
        "valid_utf8": valid_utf8,
        "contains_nul": b"\x00" in data,
    }


def fixture_manifest_entry(fixture: Fixture) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": fixture.id,
        "path": fixture.path,
        "group": fixture.group,
        "description": fixture.description,
        "committed": fixture.committed,
        "oracle_default": fixture.oracle_default,
    }
    if fixture.parameters is not None:
        entry["parameters"] = fixture.parameters
    entry.update(data_metadata(fixture.data))
    return entry


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


def build_manifest(fixtures: Iterable[Fixture]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "name": "m0-representative-tracefiles",
        "description": "Byte-exact representative LCOV 2.5 tracefile corpus and deterministic scale profiles.",
        "provenance": {
            "oracle": {
                "release": "LCOV v2.5",
                "source_commit": ORACLE_COMMIT,
                "docker_image": ORACLE_IMAGE,
                "docker_image_id": ORACLE_IMAGE_ID,
                "program": "/usr/local/bin/lcov",
                "program_sha256": ORACLE_EXECUTABLE_SHA256,
                "perl_version": "5.36.0",
            },
            "sources": [
                {"path": "lib/lcovutil.pm", "sha256": "d3d975aa796af854ed5ca8a073d855642f7c1d370dd41c2e6e26d3fd4c5057b1"},
                {"path": "docs/man/geninfo.rst", "sha256": "284530374b9faff9f470ec474a72e854db9683655bf138cf159cb9fb590cc157"},
                {"path": "tests/lcov/merge/a.dat", "sha256": "7b020ceb156047d89d97903f68efe77b847f1a3daa73ba000fc6d812839031da"},
                {"path": "tests/lcov/merge/mcdc.dat", "sha256": "7a984aeb889f170327dbdba6424674303d6b8da5aa610e7f40e4990bb56570b0"},
                {"path": "tests/lcov/format/format.info", "sha256": "e42a8bd718d8d9aa90e952b99ab78044227b4d511ef13e1d3de78a8c75dd0041"},
            ],
        },
        "generation": {
            "script": "generate.py",
            "algorithm_version": 1,
            "default_command": "python3 generate.py",
            "scale_command": "python3 generate.py --include-scale --output-root <directory>",
        },
        "fixtures": [fixture_manifest_entry(fixture) for fixture in fixtures],
    }


def build_oracle_cases(fixtures: Iterable[Fixture]) -> dict[str, object]:
    fixtures = list(fixtures)
    requirement_by_group = {
        "current-all-records": "M1-TF-040",
        "legacy": "M1-TF-010",
        "permissive-prefix": "M1-TF-004/006/008/012/015",
        "malformed-per-record": "M1-TF-012/016",
        "byte-boundary": "M1-TF-001/061",
        "numeric-boundary": "M1-TF-030/031/032/033/034",
        "state-ownership": "M1-TF-021/022/026",
        "ver-semantics": "M1-TF-007",
        "function-records": "M1-TF-009/011/024",
        "branch-records": "M1-TF-013/025",
        "deterministic-scale": "M1-TF-062",
    }
    feature_flags = {
        "current-all-records": ["--branch-coverage", "--mcdc-coverage"],
        "bytes-non-utf8": ["--branch-coverage", "--mcdc-coverage"],
        "state-late-tn-mcdc": ["--branch-coverage", "--mcdc-coverage"],
        "state-cross-sf-mcdc-success": ["--no-function-coverage", "--mcdc-coverage"],
        "state-cross-sf-mcdc-duplicate": ["--no-function-coverage", "--mcdc-coverage"],
        "branches-forms-core": ["--branch-coverage"],
        "branches-u-modes": ["--branch-coverage"],
        "branches-malformed-tail": ["--branch-coverage"],
        "branches-malformed-tail-empty-taken": ["--branch-coverage"],
        "branches-malformed-tail-empty-expression": ["--branch-coverage"],
        "branches-expression-mismatch": ["--branch-coverage"],
        "branches-order-gaps": ["--branch-coverage"],
        "branches-noncontiguous": ["--branch-coverage"],
        "branches-interleave": ["--branch-coverage"],
        "branches-sort-signatures": ["--branch-coverage"],
        "scale-medium": ["--branch-coverage", "--mcdc-coverage"],
        "scale-large": ["--branch-coverage", "--mcdc-coverage"],
    }
    cases: list[dict[str, object]] = []
    for fixture in fixtures:
        if fixture.id in {
            "branches-expression-merge-left",
            "branches-expression-merge-right",
            # Custom numeric/checksum cases below provide the authoritative observations.
            "numeric-zero-brda",
            "numeric-function-excessive",
            "checksum-match",
            "checksum-mismatch",
            "checksum-missing",
            "checksum-duplicate",
            "checksum-source-cs",
            "numeric-function-source",
        }:
            continue
        flags = feature_flags.get(fixture.id, [])
        if fixture.id == "numeric-excessive":
            flags = ["--rc", "excessive_count_threshold=100"]
        elif fixture.id == "numeric-inf-excessive":
            flags = ["--rc", "excessive_count_threshold=100"]
        elif fixture.id == "numeric-format-atoms":
            flags = ["--branch-coverage"]
        elif fixture.id in {
            "numeric-signed-zero",
            "numeric-brda-nonnumeric",
            "numeric-zero-brda",
        }:
            flags = ["--branch-coverage"]
        elif fixture.id in {
            "numeric-mcdc-nondigit",
            "numeric-zero-mcdc",
        }:
            flags = ["--mcdc-coverage"]
        elif fixture.id.startswith("checksum-"):
            flags = ["--checksum", "--no-function-coverage"]
        cases.append(
            {
                "id": f"{fixture.id}.summary",
                "fixture": fixture.path,
                "requirement": requirement_by_group[fixture.group],
                "description": f"Default summary observation for {fixture.id}.",
                "argv": ["lcov", *flags, "--summary", "input.info"],
                "expected_exit": 0 if fixture.oracle_default == "accept" else 1,
            }
        )

    canonical_cases = [
        (
            "current-all-records.canonical",
            "fixtures/current-all-records.info",
            "M1-TF-040/042",
            ["--branch-coverage", "--mcdc-coverage"],
        ),
        ("legacy.canonical", "fixtures/legacy.info", "M1-TF-010/044", []),
        (
            "permissive-prefix.canonical",
            "fixtures/permissive-prefix.info",
            "M1-TF-004/006/008/012/015/044",
            ["--no-function-coverage"],
        ),
        ("bytes-crlf.canonical", "fixtures/bytes/crlf.info", "M1-TF-001", ["--no-function-coverage"]),
        (
            "bytes-no-final-newline.canonical",
            "fixtures/bytes/no-final-newline.info",
            "M1-TF-001",
            ["--no-function-coverage"],
        ),
        (
            "bytes-non-utf8.canonical",
            "fixtures/bytes/non-utf8.info",
            "M1-TF-061",
            ["--branch-coverage", "--mcdc-coverage"],
        ),
        (
            "bytes-nul-accepted.canonical",
            "fixtures/bytes/nul-accepted.info",
            "M1-TF-061",
            ["--no-function-coverage"],
        ),
        (
            "numeric-boundary.canonical",
            "fixtures/numeric-boundary.info",
            "M1-TF-030",
            ["--no-function-coverage"],
        ),
        (
            "ver-repeat-equal.canonical",
            "fixtures/ver/repeat-equal.info",
            "M1-TF-007",
            ["--no-function-coverage"],
        ),
    ]
    for case_id, fixture, requirement, flags in canonical_cases:
        cases.append(
            {
                "id": case_id,
                "fixture": fixture,
                "requirement": requirement,
                "description": "Canonical writer output identity.",
                "argv": ["lcov", *flags, "--add-tracefile", "input.info", "--output-file", "output.info"],
                "output_file": "output.info",
                "expected_exit": 0,
            }
        )

    recovery_cases = [
        ("malformed-tn.ignore-format", "fixtures/malformed/tn.info", "format", []),
        ("malformed-da.ignore-format", "fixtures/malformed/da.info", "format", []),
        ("malformed-ver.ignore-format", "fixtures/malformed/ver.info", "format", []),
        ("numeric-negative.ignore-negative", "fixtures/numeric/negative.info", "negative", []),
        ("numeric-nonnumeric.ignore-format", "fixtures/numeric/nonnumeric.info", "format", []),
        ("numeric-malformed-exponent.ignore-format", "fixtures/numeric/malformed-exponent.info", "format", []),
        (
            "numeric-excessive.ignore-excessive",
            "fixtures/numeric/excessive.info",
            "excessive",
            ["--rc", "excessive_count_threshold=100"],
        ),
        ("numeric-zero-line.ignore-format", "fixtures/numeric/zero-line.info", "format", []),
    ]
    for case_id, fixture, category, flags in recovery_cases:
        cases.append(
            {
                "id": case_id,
                "fixture": fixture,
                "requirement": "M1-TF-031/032/033/034/036",
                "description": f"Canonical output after ignoring the {category} category.",
                "argv": [
                    "lcov", "--no-function-coverage", *flags,
                    "--ignore-errors", category,
                    "--add-tracefile", "input.info", "--output-file", "output.info",
                ],
                "output_file": "output.info",
                "expected_exit": 0,
            }
        )
    state_cases = [
        {
            "id": "state-late-tn-mcdc.canonical",
            "fixture": "fixtures/state/late-tn-mcdc.info",
            "requirement": "M1-TF-021",
            "description": "Canonical writer output for late TN MC/DC ownership.",
            "argv": [
                "lcov", "--branch-coverage", "--mcdc-coverage",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "state-late-tn-mcdc.semantic-snapshot",
            "fixture": "fixtures/state/late-tn-mcdc.info",
            "requirement": "M1-TF-021",
            "description": "Aggregate plus four testcase-family semantic snapshot for late TN MC/DC ownership.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "state-cross-sf-mcdc-success.canonical",
            "fixture": "fixtures/state/cross-sf-mcdc-success.info",
            "requirement": "M1-TF-022",
            "description": "Canonical writer output for cross-SF MC/DC success ownership.",
            "argv": [
                "lcov", "--no-function-coverage", "--mcdc-coverage",
                "--add-tracefile", "input.info", "--output-file", "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "state-cross-sf-mcdc-success.semantic-snapshot",
            "fixture": "fixtures/state/cross-sf-mcdc-success.info",
            "requirement": "M1-TF-022",
            "description": "Aggregate plus four testcase-family semantic snapshot for cross-SF MC/DC success ownership.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
    ]
    # The summary loop already emits one default observation per fixture, including the
    # three state-ownership fixtures. Append only the additional ownership probes.
    cases.extend(state_cases)

    function_cases = [
        {
            "id": "functions-current-core.canonical",
            "fixture": "fixtures/functions/current-core.info",
            "requirement": "M1-TF-009",
            "description": "Canonical writer output for current FNL/FNA core behavior.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "functions-current-core.semantic-snapshot",
            "fixture": "fixtures/functions/current-core.info",
            "requirement": "M1-TF-009",
            "description": "Semantic snapshot for current FNL/FNA aliases, ranges, and counts.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "functions-zero-end.canonical",
            "fixture": "fixtures/functions/zero-end.info",
            "requirement": "M1-TF-009",
            "description": "Canonical writer output retaining zero function end line.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "functions-mixed-merge.canonical",
            "fixture": "fixtures/functions/mixed-merge.info",
            "requirement": "M1-TF-011",
            "description": "Canonical rewrite of mixed legacy/current function records.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "functions-mixed-merge.semantic-snapshot",
            "fixture": "fixtures/functions/mixed-merge.info",
            "requirement": "M1-TF-011",
            "description": "Semantic snapshot for mixed legacy/current function merge.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "functions-mixed-location-mismatch.canonical",
            "fixture": "fixtures/functions/mixed-location-mismatch.info",
            "requirement": "M1-TF-011",
            "description": "Write attempt for mixed location mismatch hard failure.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "functions-mixed-range-mismatch.canonical",
            "fixture": "fixtures/functions/mixed-range-mismatch.info",
            "requirement": "M1-TF-011",
            "description": "Write attempt for mixed range mismatch hard failure.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "functions-index-duplicate.canonical",
            "fixture": "fixtures/functions/index-duplicate.info",
            "requirement": "M1-TF-024",
            "description": "Write attempt for duplicate FNL index hard failure.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "functions-index-unknown.canonical",
            "fixture": "fixtures/functions/index-unknown.info",
            "requirement": "M1-TF-024",
            "description": "Write attempt for unknown FNA index hard failure.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "functions-index-scope-reset.canonical",
            "fixture": "fixtures/functions/index-scope-reset.info",
            "requirement": "M1-TF-024",
            "description": "Canonical writer output after FNL index map reset on SF.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
    ]
    cases.extend(function_cases)

    branch_cases = [
        {
            "id": "branches-forms-core.canonical",
            "fixture": "fixtures/branches/forms-core.info",
            "requirement": "M1-TF-013",
            "description": "Canonical rewrite of BRDA forms including U exclusion, dash taken, comma expressions, and numeric expression identity.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-forms-core.semantic-snapshot",
            "fixture": "fixtures/branches/forms-core.info",
            "requirement": "M1-TF-013",
            "description": "Semantic snapshot for BRDA forms, exclusion, dash taken, and expression identity.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "branches-u-modes.canonical",
            "fixture": "fixtures/branches/u-modes.info",
            "requirement": "M1-TF-013",
            "description": "Canonical rewrite with default unreachable-flag mode retaining U exclusion.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-u-modes.clear-unreachable",
            "fixture": "fixtures/branches/u-modes.info",
            "requirement": "M1-TF-013",
            "description": "Canonical rewrite with ignore_unreachable_flag clearing U exclusion marks.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--rc",
                "ignore_unreachable_flag=1",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-malformed-tail.canonical",
            "fixture": "fixtures/branches/malformed-tail.info",
            "requirement": "M1-TF-013",
            "description": "Write attempt for BRDA malformed-tail hard failure.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "branches-malformed-tail-empty-taken.canonical",
            "fixture": "fixtures/branches/malformed-tail-empty-taken.info",
            "requirement": "M1-TF-013",
            "description": "Write attempt for a BRDA record whose final taken field is empty.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
        },
        {
            "id": "branches-malformed-tail-empty-expression.canonical",
            "fixture": "fixtures/branches/malformed-tail-empty-expression.info",
            "requirement": "M1-TF-013",
            "description": "Canonical rewrite of an accepted BRDA record with an empty expression.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-expression-mismatch.canonical",
            "fixture": "fixtures/branches/expression-mismatch.info",
            "requirement": "M1-TF-013",
            "description": "Canonical rewrite of distinct positional expressions under one input block token.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-expression-merge.canonical",
            "fixture": "fixtures/branches/expression-merge-left.info",
            "additional_fixtures": {
                "right.info": "fixtures/branches/expression-merge-right.info",
            },
            "requirement": "M1-TF-025",
            "description": "Canonical two-tracefile merge proving positional identity, left-expression retention, and count addition.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--parallel",
                "1",
                "--add-tracefile",
                "input.info",
                "--add-tracefile",
                "right.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-expression-merge.semantic-snapshot",
            "fixture": "fixtures/branches/expression-merge-left.info",
            "additional_fixtures": {
                "right.info": "fixtures/branches/expression-merge-right.info",
            },
            "requirement": "M1-TF-025",
            "description": "Semantic two-tracefile merge snapshot for branch expression independence and cached totals.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info", "right.info"],
            "expected_exit": 0,
        },
        {
            "id": "branches-order-gaps.canonical",
            "fixture": "fixtures/branches/order-gaps.info",
            "requirement": "M1-TF-025",
            "description": "Canonical renumbering of gapped input block IDs.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-noncontiguous.canonical",
            "fixture": "fixtures/branches/noncontiguous.info",
            "requirement": "M1-TF-025",
            "description": "Canonical rewrite after noncontiguous line/block reuse creates new positional blocks.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-noncontiguous.semantic-snapshot",
            "fixture": "fixtures/branches/noncontiguous.info",
            "requirement": "M1-TF-025",
            "description": "Semantic snapshot of positional branch blocks after noncontiguous reuse.",
            "runner": "inspect_model.pl",
            "argv": ["perl", "inspect_model.pl", "input.info"],
            "expected_exit": 0,
        },
        {
            "id": "branches-interleave.canonical",
            "fixture": "fixtures/branches/interleave.info",
            "requirement": "M1-TF-025",
            "description": "Canonical rewrite of interleaved same-line block transitions.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "branches-sort-signatures.canonical",
            "fixture": "fixtures/branches/sort-signatures.info",
            "requirement": "M1-TF-025",
            "description": "Canonical writer branch-block sort and renumbering by signature length then text.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
    ]

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
    cases.extend(numeric_cases)

    cases.extend(branch_cases)

    validate_numeric_case_closure(cases, fixtures)

    return {
        "schema_version": 1,
        "description": "Pinned LCOV 2.5 executions for every fixture plus canonicalization, ignored-error recovery, state-ownership semantic snapshots, function-record probes, branch-record probes, and numeric/error/checksum probes.",
        "execution": {
            "working_directory": "/work",
            "input_name": "input.info",
            "locale": "C.UTF-8",
            "network": "none",
        },
        "cases": cases,
    }


def write_corpus(output_root: Path, include_scale: bool) -> dict[str, object]:
    fixtures = build_fixtures()
    output_root.mkdir(parents=True, exist_ok=True)
    for fixture in fixtures:
        if not fixture.committed and not include_scale:
            continue
        path = output_root / fixture.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fixture.data)
    manifest = build_manifest(fixtures)
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="ascii"
    )
    (output_root / "oracle-cases.json").write_text(
        json.dumps(build_oracle_cases(fixtures), indent=2, sort_keys=False) + "\n",
        encoding="ascii",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument(
        "--include-scale",
        action="store_true",
        help="materialize medium and large generated fixtures",
    )
    args = parser.parse_args()
    manifest = write_corpus(args.output_root.resolve(), args.include_scale)
    written = sum(
        1
        for fixture in manifest["fixtures"]
        if fixture["committed"] or args.include_scale
    )
    print(f"generated {written} fixtures in {args.output_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
