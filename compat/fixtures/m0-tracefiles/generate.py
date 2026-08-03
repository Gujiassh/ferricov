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
    accepted = [
        "0", "+0", "-0", "1", "1.5", ".5", "1.", "1e3", "1E-3",
        "NaN", "Inf", "Infinity", " 1", "9007199254740993",
        "18446744073709551615",
    ]
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
        ]
    )
    return fixtures


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
        "deterministic-scale": "M1-TF-062",
    }
    feature_flags = {
        "current-all-records": ["--branch-coverage", "--mcdc-coverage"],
        "bytes-non-utf8": ["--branch-coverage", "--mcdc-coverage"],
        "state-late-tn-mcdc": ["--branch-coverage", "--mcdc-coverage"],
        "state-cross-sf-mcdc-success": ["--no-function-coverage", "--mcdc-coverage"],
        "state-cross-sf-mcdc-duplicate": ["--no-function-coverage", "--mcdc-coverage"],
        "scale-medium": ["--branch-coverage", "--mcdc-coverage"],
        "scale-large": ["--branch-coverage", "--mcdc-coverage"],
    }
    cases: list[dict[str, object]] = []
    for fixture in fixtures:
        flags = feature_flags.get(fixture.id, [])
        if fixture.id == "numeric-excessive":
            flags = ["--rc", "excessive_count_threshold=100"]
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

    return {
        "schema_version": 1,
        "description": "Pinned LCOV 2.5 executions for every fixture plus canonicalization, ignored-error recovery, and state-ownership semantic snapshot cases.",
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
