"""Wave-2 M0 Oracle fixtures and cases for remaining reader/framing/state blockers.

Covers exact executable mappings for:
  M1-TF-001, M1-TF-004, M1-TF-006, M1-TF-008,
  M1-TF-012, M1-TF-015, M1-TF-016.

Oracle evidence only. Product compatibility remains false.
"""

from __future__ import annotations

from corpus_model import Fixture, ascii_bytes

WAVE2_GROUP = "wave2-tracefile"
WAVE2_REQUIREMENT_TEXT = "M1-TF-001/004/006/008/012/015/016"

WAVE2_FIXTURE_IDS = (
    "wave2-framing-blank",
    "wave2-framing-crlf-blank",
    "wave2-framing-no-final-newline-blank",
    "wave2-framing-trailing-ws",
    "wave2-tn-diff",
    "wave2-kf-parity",
    "wave2-kf-empty",
    "wave2-da-accumulate",
    "wave2-da-checksum-store",
    "wave2-summary-forms",
    "wave2-terminator-suffix",
    "wave2-terminator-dup",
    "wave2-terminator-missing",
    "wave2-unknown-tags",
    "wave2-leading-ws-tag",
    "wave2-case-change",
)

# Fixtures owned entirely by custom cases (no default auto-summary).
WAVE2_SKIP_SUMMARY_FIXTURE_IDS = frozenset(
    {
        "wave2-da-checksum-store",  # requires --checksum + companion source
    }
)

WAVE2_FEATURE_FLAGS: dict[str, list[str]] = {
    "wave2-framing-blank": ["--no-function-coverage"],
    "wave2-framing-crlf-blank": ["--no-function-coverage"],
    "wave2-framing-no-final-newline-blank": ["--no-function-coverage"],
    "wave2-framing-trailing-ws": ["--no-function-coverage"],
    "wave2-tn-diff": ["--no-function-coverage"],
    "wave2-kf-parity": ["--no-function-coverage"],
    "wave2-kf-empty": ["--no-function-coverage"],
    "wave2-da-accumulate": ["--no-function-coverage"],
    "wave2-summary-forms": ["--no-function-coverage"],
    "wave2-terminator-suffix": ["--no-function-coverage"],
    "wave2-terminator-dup": ["--no-function-coverage"],
    "wave2-terminator-missing": ["--no-function-coverage"],
    "wave2-unknown-tags": ["--no-function-coverage"],
    "wave2-leading-ws-tag": ["--no-function-coverage"],
    "wave2-case-change": ["--no-function-coverage"],
}


def wave2_fixtures() -> list[Fixture]:
    framing_blank = ascii_bytes(
        """
TN:blank

SF:src/blank.c

DA:1,1

LF:1
LH:1
end_of_record

"""
    )
    framing_crlf_blank = (
        b"TN:crlfblank\r\n"
        b"SF:src/crlf-blank.c\r\n"
        b"\r\n"
        b"DA:1,1\r\n"
        b"\r\n"
        b"LF:1\r\n"
        b"LH:1\r\n"
        b"end_of_record\r\n"
    )
    framing_no_final_newline_blank = (
        b"TN:nfblank\n"
        b"SF:src/nf-blank.c\n"
        b"\n"
        b"DA:1,1\n"
        b"LF:1\n"
        b"LH:1\n"
        b"end_of_record"
    )
    framing_trailing_ws = (
        b"TN:ws  \n"
        b"SF:src/ws.c\t\n"
        b"DA:1,1   \n"
        b"LF:1\n"
        b"LH:1\n"
        b"end_of_record\n"
    )
    tn_diff = ascii_bytes(
        """
TN:,diff
SF:src/diff.c
DA:1,1
end_of_record
TN:name,other
SF:src/other.c
DA:1,1
end_of_record
TN:name,diff,extra
SF:src/extra.c
DA:1,1
end_of_record
TN:name,diff
SF:src/exact.c
DA:1,1
end_of_record
TN:has space,diff
SF:src/space-diff.c
DA:1,1
end_of_record
"""
    )
    kf_parity = ascii_bytes(
        """
TN:kf
KF:src/kf.c
DA:1,1
end_of_record
TN:kf2
KF:src/kf2.c
DA:1,2
end_of_record
TN:kf2
KF:src/kf2.c
DA:2,1
end_of_record
"""
    )
    kf_empty = ascii_bytes(
        """
TN:kfe
KF:
DA:1,1
end_of_record
"""
    )
    da_accumulate = ascii_bytes(
        """
TN:da
SF:src/da.c
DA:1,1
DA:1,2
DA:2,0
DA:1,3,chk
end_of_record
"""
    )
    da_checksum_store = ascii_bytes(
        """
TN:chkstore
SF:cs.c
DA:1,1,AVO7Y115x231sZo9ymlVFA
DA:1,2,AVO7Y115x231sZo9ymlVFA
end_of_record
"""
    )
    summary_forms = ascii_bytes(
        """
TN:sumf
SF:src/sumf.c
FNF:not-a-number
FNH
BRF_without_colon
BRH:garbage,x
MCF:
MCH:1,trailing
LF999
LH:NaN
DA:1,1
DA:2,0
FNF:999
FNH:888
BRF:777
BRH:666
MCF:555
MCH:444
LF:333
LH:222
LF:1
LH:0
end_of_record
FNF:1
LF:1
"""
    )
    terminator_suffix = ascii_bytes(
        """
TN:tsuf
SF:src/tsuf.c
DA:1,1
end_of_record_and_ignored
"""
    )
    terminator_dup = ascii_bytes(
        """
TN:a
SF:src/a.c
DA:1,1
end_of_record
TN:b
SF:src/b.c
DA:1,1
end_of_record
end_of_record
TN:c
SF:src/c.c
DA:1,1
end_of_record
"""
    )
    terminator_missing = ascii_bytes(
        """
TN:tmiss
SF:src/tmiss.c
DA:1,1
"""
    )
    unknown_tags = ascii_bytes(
        """
TN:u
SF:src/u.c
TD:desc
ZZ:x
DA:1,1
end_of_record
"""
    )
    leading_ws_tag = ascii_bytes(
        """
TN:l
SF:src/l.c
 DA:1,1
end_of_record
"""
    )
    case_change = ascii_bytes(
        """
TN:c
SF:src/c.c
da:1,1
end_of_record
"""
    )
    return [
        Fixture(
            "wave2-framing-blank",
            "fixtures/wave2/framing-blank.info",
            WAVE2_GROUP,
            "LF input with blank lines before, inside, and after a section.",
            framing_blank,
            "accept",
        ),
        Fixture(
            "wave2-framing-crlf-blank",
            "fixtures/wave2/framing-crlf-blank.info",
            WAVE2_GROUP,
            "CRLF input with blank lines; rewritten to LF canonical form.",
            framing_crlf_blank,
            "accept",
        ),
        Fixture(
            "wave2-framing-no-final-newline-blank",
            "fixtures/wave2/framing-no-final-newline-blank.info",
            WAVE2_GROUP,
            "No final newline plus interior blank lines still accepts.",
            framing_no_final_newline_blank,
            "accept",
        ),
        Fixture(
            "wave2-framing-trailing-ws",
            "fixtures/wave2/framing-trailing-ws.info",
            WAVE2_GROUP,
            "Trailing Perl whitespace on TN/SF/DA is stripped on read.",
            framing_trailing_ws,
            "accept",
        ),
        Fixture(
            "wave2-tn-diff",
            "fixtures/wave2/tn-diff.info",
            WAVE2_GROUP,
            "TN exact ,diff, other comma suffixes, suffix after ,diff, and sanitization.",
            tn_diff,
            "accept",
        ),
        Fixture(
            "wave2-kf-parity",
            "fixtures/wave2/kf-parity.info",
            WAVE2_GROUP,
            "Undocumented KF parity with SF, repetition, and SF rewrite.",
            kf_parity,
            "accept",
        ),
        Fixture(
            "wave2-kf-empty",
            "fixtures/wave2/kf-empty.info",
            WAVE2_GROUP,
            "Empty KF payload is rejected as format/corrupt.",
            kf_empty,
            "reject",
        ),
        Fixture(
            "wave2-da-accumulate",
            "fixtures/wave2/da-accumulate.info",
            WAVE2_GROUP,
            "Repeated DA lines accumulate counts; stored checksum without --checksum is dropped.",
            da_accumulate,
            "accept",
        ),
        Fixture(
            "wave2-da-checksum-store",
            "fixtures/wave2/da-checksum-store.info",
            WAVE2_GROUP,
            "Matching DA checksum with companion source under --checksum verify/store/rewrite.",
            da_checksum_store,
            "accept",
        ),
        Fixture(
            "wave2-summary-forms",
            "fixtures/wave2/summary-forms.info",
            WAVE2_GROUP,
            "All eight summary tags in missing-colon, nonnumeric, duplicate, misplaced, and suffixed forms.",
            summary_forms,
            "accept",
        ),
        Fixture(
            "wave2-terminator-suffix",
            "fixtures/wave2/terminator-suffix.info",
            WAVE2_GROUP,
            "Suffixed end_of_record is accepted by prefix matching.",
            terminator_suffix,
            "accept",
        ),
        Fixture(
            "wave2-terminator-dup",
            "fixtures/wave2/terminator-dup.info",
            WAVE2_GROUP,
            "Duplicate terminator and records after terminator remain accepted.",
            terminator_dup,
            "accept",
        ),
        Fixture(
            "wave2-terminator-missing",
            "fixtures/wave2/terminator-missing.info",
            WAVE2_GROUP,
            "Missing end_of_record yields empty/corrupt hard failure.",
            terminator_missing,
            "reject",
        ),
        Fixture(
            "wave2-unknown-tags",
            "fixtures/wave2/unknown-tags.info",
            WAVE2_GROUP,
            "TD and unknown tags hard-fail by default.",
            unknown_tags,
            "reject",
        ),
        Fixture(
            "wave2-leading-ws-tag",
            "fixtures/wave2/leading-ws-tag.info",
            WAVE2_GROUP,
            "Leading whitespace before a known tag hard-fails by default.",
            leading_ws_tag,
            "reject",
        ),
        Fixture(
            "wave2-case-change",
            "fixtures/wave2/case-change.info",
            WAVE2_GROUP,
            "Case-changed known tag hard-fails by default.",
            case_change,
            "reject",
        ),
    ]


def _canonical(
    case_id: str,
    fixture_path: str,
    requirement: str,
    description: str,
    flags: list[str],
    expected_exit: int = 0,
    additional_fixtures: dict[str, str] | None = None,
) -> dict[str, object]:
    case: dict[str, object] = {
        "id": case_id,
        "fixture": fixture_path,
        "requirement": requirement,
        "description": description,
        "argv": [
            "lcov",
            *flags,
            "--add-tracefile",
            "input.info",
            "--output-file",
            "output.info",
        ],
        "output_file": "output.info",
        "expected_exit": expected_exit,
    }
    if additional_fixtures is not None:
        case["additional_fixtures"] = additional_fixtures
    return case


def build_wave2_oracle_cases() -> list[dict[str, object]]:
    """Custom Oracle cases beyond auto-generated default summaries."""
    no_fn = ["--no-function-coverage"]
    cases: list[dict[str, object]] = [
        _canonical(
            "wave2-framing-blank.canonical",
            "fixtures/wave2/framing-blank.info",
            "M1-TF-001",
            "Canonical rewrite collapses blank lines and emits LF records.",
            no_fn,
        ),
        _canonical(
            "wave2-framing-crlf-blank.canonical",
            "fixtures/wave2/framing-crlf-blank.info",
            "M1-TF-001",
            "Canonical rewrite normalizes CRLF blank-line framing to LF.",
            no_fn,
        ),
        _canonical(
            "wave2-framing-no-final-newline-blank.canonical",
            "fixtures/wave2/framing-no-final-newline-blank.info",
            "M1-TF-001",
            "Canonical rewrite accepts no-final-newline input with blank lines.",
            no_fn,
        ),
        _canonical(
            "wave2-framing-trailing-ws.canonical",
            "fixtures/wave2/framing-trailing-ws.info",
            "M1-TF-001",
            "Canonical rewrite strips trailing Perl whitespace from records.",
            no_fn,
        ),
        _canonical(
            "wave2-tn-diff.canonical",
            "fixtures/wave2/tn-diff.info",
            "M1-TF-004",
            "Canonical rewrite of TN ,diff exact/suffix/other-comma and sanitization.",
            no_fn,
        ),
        _canonical(
            "wave2-kf-parity.canonical",
            "fixtures/wave2/kf-parity.info",
            "M1-TF-006",
            "Canonical rewrite emits SF not KF and merges repeated KF source sections.",
            no_fn,
        ),
        _canonical(
            "wave2-kf-empty.canonical",
            "fixtures/wave2/kf-empty.info",
            "M1-TF-006",
            "Write attempt for empty KF payload hard failure.",
            no_fn,
            expected_exit=1,
        ),
        {
            "id": "wave2-kf-empty.ignore-format",
            "fixture": "fixtures/wave2/kf-empty.info",
            "requirement": "M1-TF-006",
            "description": "Ignore-format recovery for empty KF yields empty coverage DB.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "format,empty",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        _canonical(
            "wave2-da-accumulate.canonical",
            "fixtures/wave2/da-accumulate.info",
            "M1-TF-008",
            "Canonical rewrite accumulates repeated DA counts and drops stored checksum without --checksum.",
            no_fn,
        ),
        _canonical(
            "wave2-da-checksum-store.canonical",
            "fixtures/wave2/da-checksum-store.info",
            "M1-TF-008",
            "Matching DA checksum is verified and rewritten under --checksum.",
            ["--checksum", "--no-function-coverage"],
            additional_fixtures={"cs.c": "fixtures/numeric/cs.c"},
        ),
        _canonical(
            "wave2-da-checksum-store.no-verify.canonical",
            "fixtures/wave2/da-checksum-store.info",
            "M1-TF-008",
            "Without --checksum, stored DA checksums are not emitted.",
            no_fn,
        ),
        _canonical(
            "wave2-summary-forms.canonical",
            "fixtures/wave2/summary-forms.info",
            "M1-TF-012",
            "Canonical rewrite recomputes all eight summary tags and ignores junk forms.",
            no_fn,
        ),
        _canonical(
            "wave2-terminator-suffix.canonical",
            "fixtures/wave2/terminator-suffix.info",
            "M1-TF-015",
            "Canonical rewrite normalizes suffixed end_of_record.",
            no_fn,
        ),
        _canonical(
            "wave2-terminator-dup.canonical",
            "fixtures/wave2/terminator-dup.info",
            "M1-TF-015",
            "Canonical rewrite accepts duplicate terminator and later sections.",
            no_fn,
        ),
        _canonical(
            "wave2-terminator-missing.canonical",
            "fixtures/wave2/terminator-missing.info",
            "M1-TF-015",
            "Missing terminator hard failure.",
            no_fn,
            expected_exit=1,
        ),
        {
            "id": "wave2-terminator-missing.ignore-empty",
            "fixture": "fixtures/wave2/terminator-missing.info",
            "requirement": "M1-TF-015",
            "description": "Ignore-empty recovery for missing terminator yields empty coverage DB.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "empty",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        _canonical(
            "wave2-unknown-tags.canonical",
            "fixtures/wave2/unknown-tags.info",
            "M1-TF-016",
            "TD and unknown tags hard failure.",
            no_fn,
            expected_exit=1,
        ),
        {
            "id": "wave2-unknown-tags.ignore-format",
            "fixture": "fixtures/wave2/unknown-tags.info",
            "requirement": "M1-TF-016",
            "description": "Ignore-format skips TD/unknown tags and retains DA data.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "format",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        _canonical(
            "wave2-leading-ws-tag.canonical",
            "fixtures/wave2/leading-ws-tag.info",
            "M1-TF-016",
            "Leading whitespace before known tag hard failure.",
            no_fn,
            expected_exit=1,
        ),
        {
            "id": "wave2-leading-ws-tag.ignore-format",
            "fixture": "fixtures/wave2/leading-ws-tag.info",
            "requirement": "M1-TF-016",
            "description": "Ignore-format skips leading-space tag and yields empty coverage DB.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "format,empty",
                "--no-function-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        _canonical(
            "wave2-case-change.canonical",
            "fixtures/wave2/case-change.info",
            "M1-TF-016",
            "Case-changed known tag hard failure.",
            no_fn,
            expected_exit=1,
        ),
        {
            "id": "wave2-case-change.ignore-format",
            "fixture": "fixtures/wave2/case-change.info",
            "requirement": "M1-TF-016",
            "description": "Ignore-format skips case-changed tag and yields empty coverage DB.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "format,empty",
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
    return cases


WAVE2_CASE_IDS = (
    # auto summaries for non-skipped fixtures (fixture order)
    "wave2-framing-blank.summary",
    "wave2-framing-crlf-blank.summary",
    "wave2-framing-no-final-newline-blank.summary",
    "wave2-framing-trailing-ws.summary",
    "wave2-tn-diff.summary",
    "wave2-kf-parity.summary",
    "wave2-kf-empty.summary",
    "wave2-da-accumulate.summary",
    "wave2-summary-forms.summary",
    "wave2-terminator-suffix.summary",
    "wave2-terminator-dup.summary",
    "wave2-terminator-missing.summary",
    "wave2-unknown-tags.summary",
    "wave2-leading-ws-tag.summary",
    "wave2-case-change.summary",
    # custom cases in build_wave2_oracle_cases order
    "wave2-framing-blank.canonical",
    "wave2-framing-crlf-blank.canonical",
    "wave2-framing-no-final-newline-blank.canonical",
    "wave2-framing-trailing-ws.canonical",
    "wave2-tn-diff.canonical",
    "wave2-kf-parity.canonical",
    "wave2-kf-empty.canonical",
    "wave2-kf-empty.ignore-format",
    "wave2-da-accumulate.canonical",
    "wave2-da-checksum-store.canonical",
    "wave2-da-checksum-store.no-verify.canonical",
    "wave2-summary-forms.canonical",
    "wave2-terminator-suffix.canonical",
    "wave2-terminator-dup.canonical",
    "wave2-terminator-missing.canonical",
    "wave2-terminator-missing.ignore-empty",
    "wave2-unknown-tags.canonical",
    "wave2-unknown-tags.ignore-format",
    "wave2-leading-ws-tag.canonical",
    "wave2-leading-ws-tag.ignore-format",
    "wave2-case-change.canonical",
    "wave2-case-change.ignore-format",
)

WAVE2_EXACT_REQUIREMENTS: dict[str, list[str]] = {
    "wave2-framing-blank.summary": ["M1-TF-001"],
    "wave2-framing-blank.canonical": ["M1-TF-001"],
    "wave2-framing-crlf-blank.summary": ["M1-TF-001"],
    "wave2-framing-crlf-blank.canonical": ["M1-TF-001"],
    "wave2-framing-no-final-newline-blank.summary": ["M1-TF-001"],
    "wave2-framing-no-final-newline-blank.canonical": ["M1-TF-001"],
    "wave2-framing-trailing-ws.summary": ["M1-TF-001"],
    "wave2-framing-trailing-ws.canonical": ["M1-TF-001"],
    "wave2-tn-diff.summary": ["M1-TF-004"],
    "wave2-tn-diff.canonical": ["M1-TF-004"],
    "wave2-kf-parity.summary": ["M1-TF-006"],
    "wave2-kf-parity.canonical": ["M1-TF-006"],
    "wave2-kf-empty.summary": ["M1-TF-006"],
    "wave2-kf-empty.canonical": ["M1-TF-006"],
    "wave2-kf-empty.ignore-format": ["M1-TF-006"],
    "wave2-da-accumulate.summary": ["M1-TF-008"],
    "wave2-da-accumulate.canonical": ["M1-TF-008"],
    "wave2-da-checksum-store.canonical": ["M1-TF-008"],
    "wave2-da-checksum-store.no-verify.canonical": ["M1-TF-008"],
    "wave2-summary-forms.summary": ["M1-TF-012"],
    "wave2-summary-forms.canonical": ["M1-TF-012"],
    "wave2-terminator-suffix.summary": ["M1-TF-015"],
    "wave2-terminator-suffix.canonical": ["M1-TF-015"],
    "wave2-terminator-dup.summary": ["M1-TF-015"],
    "wave2-terminator-dup.canonical": ["M1-TF-015"],
    "wave2-terminator-missing.summary": ["M1-TF-015"],
    "wave2-terminator-missing.canonical": ["M1-TF-015"],
    "wave2-terminator-missing.ignore-empty": ["M1-TF-015"],
    "wave2-unknown-tags.summary": ["M1-TF-016"],
    "wave2-unknown-tags.canonical": ["M1-TF-016"],
    "wave2-unknown-tags.ignore-format": ["M1-TF-016"],
    "wave2-leading-ws-tag.summary": ["M1-TF-016"],
    "wave2-leading-ws-tag.canonical": ["M1-TF-016"],
    "wave2-leading-ws-tag.ignore-format": ["M1-TF-016"],
    "wave2-case-change.summary": ["M1-TF-016"],
    "wave2-case-change.canonical": ["M1-TF-016"],
    "wave2-case-change.ignore-format": ["M1-TF-016"],
}


def validate_wave2_fixture_closure(fixtures: list[Fixture]) -> None:
    wave2 = [fixture for fixture in fixtures if fixture.group == WAVE2_GROUP]
    ids = [fixture.id for fixture in wave2]
    if ids != list(WAVE2_FIXTURE_IDS):
        raise ValueError(f"wave2 fixture closure drift: {ids}")
