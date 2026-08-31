"""Wave-1 M0 Oracle fixtures and cases for remaining named tracefile blockers.

Covers exact executable mappings for:
  M1-TF-002, M1-TF-003, M1-TF-005, M1-TF-014,
  M1-TF-020, M1-TF-023, M1-TF-027, M1-TF-028.

Oracle evidence only. Product compatibility remains false.
"""

from __future__ import annotations

from corpus_model import Fixture, ascii_bytes

WAVE1_GROUP = "wave1-tracefile"
WAVE1_REQUIREMENT_TEXT = "M1-TF-002/003/005/014/020/023/027/028"

WAVE1_FIXTURE_IDS = (
    "wave1-comments-core",
    "wave1-comments-leading-space",
    "wave1-tn-names",
    "wave1-tn-forget",
    "wave1-sf-paths",
    "wave1-sf-empty",
    "wave1-sf-whitespace",
    "wave1-mcdc-core",
    "wave1-mcdc-u-modes",
    "wave1-order-canonical",
    "wave1-order-permuted",
    "wave1-repeat-same-tn",
    "wave1-repeat-diff-tn-mcdc",
    "wave1-features-all",
    "wave1-summary-payloads",
)

# Fixtures whose default auto-summary is skipped because custom cases own them,
# or because the fixture is only meaningful under non-default feature flags.
WAVE1_SKIP_SUMMARY_FIXTURE_IDS = frozenset(
    {
        "wave1-tn-forget",  # forget-test-names is not the default summary path
        "wave1-order-canonical",
        "wave1-order-permuted",
        "wave1-features-all",
        "wave1-summary-payloads",
        "wave1-mcdc-core",
        "wave1-mcdc-u-modes",
        "wave1-repeat-same-tn",
        "wave1-repeat-diff-tn-mcdc",
    }
)

WAVE1_FEATURE_FLAGS: dict[str, list[str]] = {
    "wave1-comments-core": ["--no-function-coverage"],
    "wave1-comments-leading-space": ["--no-function-coverage"],
    "wave1-tn-names": ["--no-function-coverage"],
    "wave1-sf-paths": ["--no-function-coverage"],
    "wave1-sf-empty": ["--no-function-coverage"],
    "wave1-sf-whitespace": ["--no-function-coverage"],
}


def wave1_fixtures() -> list[Fixture]:
    comments_core = ascii_bytes(
        """
# leading column-zero comment
TN:comment_core
# mid-section comment
SF:src/comment-core.c
DA:1,1
# after data comment
LF:1
LH:1
end_of_record
# trailing column-zero comment
"""
    )
    comments_leading_space = ascii_bytes(
        """
TN:comment_space
SF:src/comment-space.c
 # leading-space hash is not a comment
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    tn_names = ascii_bytes(
        """
TN:
SF:src/tn-empty.c
DA:1,1
end_of_record
TN:valid_name
SF:src/tn-valid.c
DA:1,1
end_of_record
TN:another-name.1
SF:src/tn-valid.c
DA:2,1
end_of_record
TN:has space
SF:src/tn-space.c
DA:1,1
end_of_record
"""
    )
    tn_forget = ascii_bytes(
        """
TN:one
SF:src/tn-forget.c
DA:1,1
end_of_record
TN:two
SF:src/tn-forget.c
DA:1,2
end_of_record
"""
    )
    sf_paths = ascii_bytes(
        """
TN:sf_paths
SF:src/sf-rel.c
DA:1,1
end_of_record
TN:sf_paths
SF:./src/sf-dot.c
DA:1,1
end_of_record
TN:sf_paths
SF:/abs/src/sf-abs.c
DA:1,1
end_of_record
TN:sf_paths_b
SF:src/sf-rel.c
DA:1,2
DA:2,1
end_of_record
"""
    )
    sf_empty = ascii_bytes(
        """
TN:sf_empty
SF:
DA:1,1
end_of_record
"""
    )
    sf_whitespace = ascii_bytes(
        """
TN:sf_ws
SF:   
DA:1,1
end_of_record
"""
    )
    mcdc_core = ascii_bytes(
        """
TN:mcdc_core
SF:src/mcdc-core.c
MCDC:1,1,t,1,0,x
MCDC:1,1,f,0,0,x
MCDC:2,0,t,1,0,a && b
MCDC:2,0,f,0,1,a && b
MCDC:2,1,t,1,0,a && b
MCDC:2,1,f,0,1,a && b
MCDC:3,1,t,1,0,a,b
MCDC:3,1,f,0,0,a,b
MCDC:3,1,t,2,0,a,b
DA:1,1
DA:2,1
DA:3,1
end_of_record
"""
    )
    mcdc_u = ascii_bytes(
        """
TN:mcdc_u
SF:src/mcdc-u.c
MCDC:1,U1,t,1,0,cond
MCDC:1,1,f,0,0,cond
DA:1,1
end_of_record
"""
    )
    order_canonical = ascii_bytes(
        """
TN:order
SF:src/order.c
FNL:0,1,1
FNA:0,1,f
BRDA:1,0,e,1
BRDA:1,0,e2,0
MCDC:1,1,t,1,0,c
MCDC:1,1,f,0,0,c
DA:1,1
LF:1
LH:1
end_of_record
"""
    )
    order_permuted = ascii_bytes(
        """
TN:order
SF:src/order.c
DA:1,1
FNL:0,1,1
FNA:0,1,f
BRDA:1,0,e,1
BRDA:1,0,e2,0
MCDC:1,1,t,1,0,c
MCDC:1,1,f,0,0,c
LF:1
LH:1
end_of_record
"""
    )
    repeat_same_tn = ascii_bytes(
        """
TN:rep
SF:src/repeat.c
FNL:0,1,1
FNA:0,1,f
BRDA:1,0,e,1
BRDA:1,0,e2,0
DA:1,1
end_of_record
TN:rep
SF:src/repeat.c
FNL:0,1,1
FNA:0,2,f
BRDA:1,0,e,1
BRDA:1,0,e2,1
DA:1,1
DA:2,1
end_of_record
"""
    )
    repeat_diff_tn_mcdc = ascii_bytes(
        """
TN:a
SF:src/repeat-mcdc.c
MCDC:1,1,t,1,0,c
MCDC:1,1,f,0,0,c
DA:1,1
end_of_record
TN:b
SF:src/repeat-mcdc.c
MCDC:1,1,t,1,0,c
MCDC:1,1,f,1,0,c
DA:1,1
end_of_record
"""
    )
    features_all = ascii_bytes(
        """
TN:feat
SF:src/features.c
FNL:0,1,1
FNA:0,1,f
BRDA:1,0,e,1
BRDA:1,0,e2,0
MCDC:1,1,t,1,0,c
MCDC:1,1,f,0,0,c
DA:1,1
end_of_record
"""
    )
    summary_payloads = ascii_bytes(
        """
TN:sum
SF:src/summary.c
FNF:999
FNH:888
BRF:777
BRH:666
MCF:555
MCH:444
LF:333
LH:222
DA:1,1
DA:2,0
BRDA:1,0,e,1
BRDA:1,0,e2,0
MCDC:1,1,t,1,0,c
MCDC:1,1,f,0,0,c
FNF:1
FNH:0
BRF:1
BRH:0
MCF:1
MCH:0
LF:1
LH:0
LF:0
LH:0
end_of_record
FNF:1
LF:1
"""
    )
    return [
        Fixture(
            "wave1-comments-core",
            "fixtures/wave1/comments-core.info",
            WAVE1_GROUP,
            "Column-zero comments before, inside, and after a section; writer drops comments.",
            comments_core,
            "accept",
        ),
        Fixture(
            "wave1-comments-leading-space",
            "fixtures/wave1/comments-leading-space.info",
            WAVE1_GROUP,
            "Leading-space # is not a comment and raises format/corrupt by default.",
            comments_leading_space,
            "reject",
        ),
        Fixture(
            "wave1-tn-names",
            "fixtures/wave1/tn-names.info",
            WAVE1_GROUP,
            "Empty TN, valid word TN names, writer section repetition, and TN sanitization warning.",
            tn_names,
            "accept",
        ),
        Fixture(
            "wave1-tn-forget",
            "fixtures/wave1/tn-forget.info",
            WAVE1_GROUP,
            "Two named test sections merged under --forget-test-names.",
            tn_forget,
            "accept",
        ),
        Fixture(
            "wave1-sf-paths",
            "fixtures/wave1/sf-paths.info",
            WAVE1_GROUP,
            "Canonical SF paths (relative, ./, absolute) and repeated source/test sections.",
            sf_paths,
            "accept",
        ),
        Fixture(
            "wave1-sf-empty",
            "fixtures/wave1/sf-empty.info",
            WAVE1_GROUP,
            "Empty SF payload is rejected as format/corrupt.",
            sf_empty,
            "reject",
        ),
        Fixture(
            "wave1-sf-whitespace",
            "fixtures/wave1/sf-whitespace.info",
            WAVE1_GROUP,
            "Whitespace-only SF payload is treated as empty and rejected.",
            sf_whitespace,
            "reject",
        ),
        Fixture(
            "wave1-mcdc-core",
            "fixtures/wave1/mcdc-core.info",
            WAVE1_GROUP,
            "MCDC group sizes, indices, both senses, comma-bearing expressions, and repeated sense counts.",
            mcdc_core,
            "accept",
        ),
        Fixture(
            "wave1-mcdc-u-modes",
            "fixtures/wave1/mcdc-u-modes.info",
            WAVE1_GROUP,
            "MCDC U sense under both unreachable-flag modes.",
            mcdc_u,
            "accept",
        ),
        Fixture(
            "wave1-order-canonical",
            "fixtures/wave1/order-canonical.info",
            WAVE1_GROUP,
            "Cross-family records in writer-like order.",
            order_canonical,
            "accept",
        ),
        Fixture(
            "wave1-order-permuted",
            "fixtures/wave1/order-permuted.info",
            WAVE1_GROUP,
            "Cross-family order permutation with DA first; equivalent model and rewrite.",
            order_permuted,
            "accept",
        ),
        Fixture(
            "wave1-repeat-same-tn",
            "fixtures/wave1/repeat-same-tn.info",
            WAVE1_GROUP,
            "Repeated same-TN source section additive line/function/branch behavior.",
            repeat_same_tn,
            "accept",
        ),
        Fixture(
            "wave1-repeat-diff-tn-mcdc",
            "fixtures/wave1/repeat-diff-tn-mcdc.info",
            WAVE1_GROUP,
            "Repeated source with different TN and MC/DC ownership/additive counts.",
            repeat_diff_tn_mcdc,
            "accept",
        ),
        Fixture(
            "wave1-features-all",
            "fixtures/wave1/features-all.info",
            WAVE1_GROUP,
            "Function, branch, and MC/DC records exercised under feature enable/disable flags.",
            features_all,
            "accept",
        ),
        Fixture(
            "wave1-summary-payloads",
            "fixtures/wave1/summary-payloads.info",
            WAVE1_GROUP,
            "Summary records before, within, and after data; payloads and repetition do not affect totals.",
            summary_payloads,
            "accept",
        ),
    ]


def _canonical(
    case_id: str,
    fixture_path: str,
    requirement: str,
    description: str,
    flags: list[str],
    expected_exit: int = 0,
) -> dict[str, object]:
    return {
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


def _semantic(
    case_id: str,
    fixture_path: str,
    requirement: str,
    description: str,
) -> dict[str, object]:
    return {
        "id": case_id,
        "fixture": fixture_path,
        "requirement": requirement,
        "description": description,
        "runner": "inspect_model.pl",
        "argv": ["perl", "inspect_model.pl", "input.info"],
        "expected_exit": 0,
    }


def build_wave1_oracle_cases() -> list[dict[str, object]]:
    """Custom Oracle cases beyond auto-generated default summaries."""
    cases: list[dict[str, object]] = [
        _canonical(
            "wave1-comments-core.canonical",
            "fixtures/wave1/comments-core.info",
            "M1-TF-002",
            "Canonical rewrite drops all input column-zero comments.",
            ["--no-function-coverage"],
        ),
        _canonical(
            "wave1-comments-leading-space.canonical",
            "fixtures/wave1/comments-leading-space.info",
            "M1-TF-002",
            "Write attempt for leading-space # hard failure.",
            ["--no-function-coverage"],
            expected_exit=1,
        ),
        {
            "id": "wave1-comments-leading-space.ignore-format",
            "fixture": "fixtures/wave1/comments-leading-space.info",
            "requirement": "M1-TF-002",
            "description": "Ignore-format recovery skips the leading-space non-comment record.",
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
            "wave1-tn-names.canonical",
            "fixtures/wave1/tn-names.info",
            "M1-TF-003",
            "Canonical rewrite of empty TN, valid names, sanitization, and per-section TN emission.",
            ["--no-function-coverage"],
        ),
        {
            "id": "wave1-tn-forget.canonical",
            "fixture": "fixtures/wave1/tn-forget.info",
            "requirement": "M1-TF-003",
            "description": "Forget-test-names merges named sections into empty TN with additive counts.",
            "argv": [
                "lcov",
                "--forget-test-names",
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
            "wave1-sf-paths.canonical",
            "fixtures/wave1/sf-paths.info",
            "M1-TF-005",
            "Canonical rewrite preserves SF path bytes and merges repeated source/test sections.",
            ["--no-function-coverage"],
        ),
        _canonical(
            "wave1-sf-empty.canonical",
            "fixtures/wave1/sf-empty.info",
            "M1-TF-005",
            "Write attempt for empty SF payload hard failure.",
            ["--no-function-coverage"],
            expected_exit=1,
        ),
        _canonical(
            "wave1-sf-whitespace.canonical",
            "fixtures/wave1/sf-whitespace.info",
            "M1-TF-005",
            "Write attempt for whitespace-only SF payload hard failure.",
            ["--no-function-coverage"],
            expected_exit=1,
        ),
        _canonical(
            "wave1-mcdc-core.canonical",
            "fixtures/wave1/mcdc-core.info",
            "M1-TF-014",
            "Canonical rewrite of MCDC group sizes, indices, senses, comma expressions, and repeated counts.",
            ["--mcdc-coverage", "--no-function-coverage"],
        ),
        _semantic(
            "wave1-mcdc-core.semantic-snapshot",
            "fixtures/wave1/mcdc-core.info",
            "M1-TF-014",
            "Semantic snapshot for MCDC groups, senses, expressions, and additive sense counts.",
        ),
        _canonical(
            "wave1-mcdc-u-modes.canonical",
            "fixtures/wave1/mcdc-u-modes.info",
            "M1-TF-014",
            "Canonical rewrite retaining U exclusion under default unreachable-flag mode.",
            ["--mcdc-coverage", "--no-function-coverage"],
        ),
        {
            "id": "wave1-mcdc-u-modes.clear-unreachable",
            "fixture": "fixtures/wave1/mcdc-u-modes.info",
            "requirement": "M1-TF-014",
            "description": "Canonical rewrite clearing U exclusion with ignore_unreachable_flag=1.",
            "argv": [
                "lcov",
                "--mcdc-coverage",
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
        _canonical(
            "wave1-order-canonical.canonical",
            "fixtures/wave1/order-canonical.info",
            "M1-TF-020",
            "Canonical rewrite from writer-like cross-family order.",
            ["--branch-coverage", "--mcdc-coverage"],
        ),
        _semantic(
            "wave1-order-canonical.semantic-snapshot",
            "fixtures/wave1/order-canonical.info",
            "M1-TF-020",
            "Semantic snapshot for writer-like cross-family order.",
        ),
        _canonical(
            "wave1-order-permuted.canonical",
            "fixtures/wave1/order-permuted.info",
            "M1-TF-020",
            "Canonical rewrite from DA-first cross-family order permutation.",
            ["--branch-coverage", "--mcdc-coverage"],
        ),
        _semantic(
            "wave1-order-permuted.semantic-snapshot",
            "fixtures/wave1/order-permuted.info",
            "M1-TF-020",
            "Semantic snapshot for DA-first order permutation; must match canonical order model.",
        ),
        _canonical(
            "wave1-repeat-same-tn.canonical",
            "fixtures/wave1/repeat-same-tn.info",
            "M1-TF-023",
            "Canonical additive rewrite of repeated same-TN source sections for line/function/branch.",
            ["--branch-coverage"],
        ),
        _semantic(
            "wave1-repeat-same-tn.semantic-snapshot",
            "fixtures/wave1/repeat-same-tn.info",
            "M1-TF-023",
            "Semantic snapshot of additive same-TN repeated sections.",
        ),
        _canonical(
            "wave1-repeat-diff-tn-mcdc.canonical",
            "fixtures/wave1/repeat-diff-tn-mcdc.info",
            "M1-TF-023",
            "Canonical rewrite of different-TN repeated source with MC/DC ownership and additive counts.",
            ["--mcdc-coverage", "--no-function-coverage"],
        ),
        _semantic(
            "wave1-repeat-diff-tn-mcdc.semantic-snapshot",
            "fixtures/wave1/repeat-diff-tn-mcdc.info",
            "M1-TF-023",
            "Semantic snapshot of different-TN MC/DC repeated source ownership.",
        ),
        {
            "id": "wave1-features-all.default-function-only",
            "fixture": "fixtures/wave1/features-all.info",
            "requirement": "M1-TF-027",
            "description": "Default flags keep function coverage and drop branch/MC/DC records.",
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
            "id": "wave1-features-all.all-enabled",
            "fixture": "fixtures/wave1/features-all.info",
            "requirement": "M1-TF-027",
            "description": "Function, branch, and MC/DC all enabled retain all three families.",
            "argv": [
                "lcov",
                "--function-coverage",
                "--branch-coverage",
                "--mcdc-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "wave1-features-all.no-function-branch-mcdc",
            "fixture": "fixtures/wave1/features-all.info",
            "requirement": "M1-TF-027",
            "description": "No-function with branch and MC/DC enabled drops only function records.",
            "argv": [
                "lcov",
                "--no-function-coverage",
                "--branch-coverage",
                "--mcdc-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "wave1-features-all.branch-only",
            "fixture": "fixtures/wave1/features-all.info",
            "requirement": "M1-TF-027",
            "description": "Branch enabled without MC/DC keeps branch and function, drops MC/DC.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "wave1-features-all.mcdc-only",
            "fixture": "fixtures/wave1/features-all.info",
            "requirement": "M1-TF-027",
            "description": "MC/DC enabled without branch keeps MC/DC and function, drops branch.",
            "argv": [
                "lcov",
                "--mcdc-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "wave1-features-all.lines-only",
            "fixture": "fixtures/wave1/features-all.info",
            "requirement": "M1-TF-027",
            "description": "No-function and no-branch drop function and branch; MC/DC still needs its flag.",
            "argv": [
                "lcov",
                "--no-function-coverage",
                "--no-branch-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
        },
        _canonical(
            "wave1-summary-payloads.canonical",
            "fixtures/wave1/summary-payloads.info",
            "M1-TF-028",
            "Canonical rewrite recomputes totals and ignores junk/repeated summary payloads.",
            ["--no-function-coverage", "--branch-coverage", "--mcdc-coverage"],
        ),
    ]
    return cases


WAVE1_CASE_IDS = (
    # auto summaries for non-skipped fixtures (fixture order)
    "wave1-comments-core.summary",
    "wave1-comments-leading-space.summary",
    "wave1-tn-names.summary",
    "wave1-sf-paths.summary",
    "wave1-sf-empty.summary",
    "wave1-sf-whitespace.summary",
    # custom cases in build_wave1_oracle_cases order
    "wave1-comments-core.canonical",
    "wave1-comments-leading-space.canonical",
    "wave1-comments-leading-space.ignore-format",
    "wave1-tn-names.canonical",
    "wave1-tn-forget.canonical",
    "wave1-sf-paths.canonical",
    "wave1-sf-empty.canonical",
    "wave1-sf-whitespace.canonical",
    "wave1-mcdc-core.canonical",
    "wave1-mcdc-core.semantic-snapshot",
    "wave1-mcdc-u-modes.canonical",
    "wave1-mcdc-u-modes.clear-unreachable",
    "wave1-order-canonical.canonical",
    "wave1-order-canonical.semantic-snapshot",
    "wave1-order-permuted.canonical",
    "wave1-order-permuted.semantic-snapshot",
    "wave1-repeat-same-tn.canonical",
    "wave1-repeat-same-tn.semantic-snapshot",
    "wave1-repeat-diff-tn-mcdc.canonical",
    "wave1-repeat-diff-tn-mcdc.semantic-snapshot",
    "wave1-features-all.default-function-only",
    "wave1-features-all.all-enabled",
    "wave1-features-all.no-function-branch-mcdc",
    "wave1-features-all.branch-only",
    "wave1-features-all.mcdc-only",
    "wave1-features-all.lines-only",
    "wave1-summary-payloads.canonical",
)

WAVE1_EXACT_REQUIREMENTS: dict[str, list[str]] = {
    "wave1-comments-core.summary": ["M1-TF-002"],
    "wave1-comments-core.canonical": ["M1-TF-002"],
    "wave1-comments-leading-space.summary": ["M1-TF-002"],
    "wave1-comments-leading-space.canonical": ["M1-TF-002"],
    "wave1-comments-leading-space.ignore-format": ["M1-TF-002"],
    "wave1-tn-names.summary": ["M1-TF-003"],
    "wave1-tn-names.canonical": ["M1-TF-003"],
    "wave1-tn-forget.canonical": ["M1-TF-003"],
    "wave1-sf-paths.summary": ["M1-TF-005"],
    "wave1-sf-paths.canonical": ["M1-TF-005"],
    "wave1-sf-empty.summary": ["M1-TF-005"],
    "wave1-sf-empty.canonical": ["M1-TF-005"],
    "wave1-sf-whitespace.summary": ["M1-TF-005"],
    "wave1-sf-whitespace.canonical": ["M1-TF-005"],
    "wave1-mcdc-core.canonical": ["M1-TF-014"],
    "wave1-mcdc-core.semantic-snapshot": ["M1-TF-014"],
    "wave1-mcdc-u-modes.canonical": ["M1-TF-014"],
    "wave1-mcdc-u-modes.clear-unreachable": ["M1-TF-014"],
    "wave1-order-canonical.canonical": ["M1-TF-020"],
    "wave1-order-canonical.semantic-snapshot": ["M1-TF-020"],
    "wave1-order-permuted.canonical": ["M1-TF-020"],
    "wave1-order-permuted.semantic-snapshot": ["M1-TF-020"],
    "wave1-repeat-same-tn.canonical": ["M1-TF-023"],
    "wave1-repeat-same-tn.semantic-snapshot": ["M1-TF-023"],
    "wave1-repeat-diff-tn-mcdc.canonical": ["M1-TF-023"],
    "wave1-repeat-diff-tn-mcdc.semantic-snapshot": ["M1-TF-023"],
    "wave1-features-all.default-function-only": ["M1-TF-027"],
    "wave1-features-all.all-enabled": ["M1-TF-027"],
    "wave1-features-all.no-function-branch-mcdc": ["M1-TF-027"],
    "wave1-features-all.branch-only": ["M1-TF-027"],
    "wave1-features-all.mcdc-only": ["M1-TF-027"],
    "wave1-features-all.lines-only": ["M1-TF-027"],
    "wave1-summary-payloads.canonical": ["M1-TF-028"],
}


def validate_wave1_fixture_closure(fixtures: list[Fixture]) -> None:
    wave1 = [fixture for fixture in fixtures if fixture.group == WAVE1_GROUP]
    ids = [fixture.id for fixture in wave1]
    if ids != list(WAVE1_FIXTURE_IDS):
        raise ValueError(f"wave1 fixture closure drift: {ids}")
