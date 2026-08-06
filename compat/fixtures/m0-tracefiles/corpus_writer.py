"""Writer/converter/transport M0 Oracle fixtures and cases.

Covers exact executable mappings for:
  M1-TF-041, M1-TF-042, M1-TF-043, M1-TF-044,
  M1-TF-045, M1-TF-046, M1-TF-050, M1-TF-051,
  M1-TF-052, M1-TF-060, M1-TF-061.

Oracle evidence only. Product compatibility remains false.
M1-TF-063 / M1-TF-064 remain blocked (not bound here).
"""

from __future__ import annotations

import gzip
import io

from corpus_model import Fixture, ascii_bytes

WRITER_GROUP = "writer-tracefile"
WRITER_REQUIREMENT_TEXT = "M1-TF-041/042/043/044/045/046/050/051/052/060/061"

WRITER_FIXTURE_IDS = (
    "writer-order-core",
    "writer-mcdc-groups",
    "writer-summaries",
    "writer-forbidden",
    "writer-comments",
    "writer-fixedpoint",
    "gzip-plain",
    "gzip-valid",
    "gzip-corrupt",
    "gzip-empty",
    "writer-non-utf8",
    "converter-coverage-xml",
    "converter-mod-py",
)

# Fixtures owned entirely by custom cases (no default auto-summary), or non-info inputs.
WRITER_SKIP_SUMMARY_FIXTURE_IDS = frozenset(
    {
        "gzip-valid",
        "gzip-corrupt",
        "gzip-empty",
        "converter-coverage-xml",
        "converter-mod-py",
        "writer-fixedpoint",
        "writer-order-core",
        "writer-mcdc-groups",
        "writer-summaries",
        "writer-forbidden",
        "writer-comments",
        "writer-non-utf8",
        "gzip-plain",
    }
)

WRITER_FEATURE_FLAGS: dict[str, list[str]] = {}


def _gzip_bytes(payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0, compresslevel=9) as handle:
        handle.write(payload)
    return buffer.getvalue()


def writer_fixtures() -> list[Fixture]:
    order_core = ascii_bytes(
        """
TN:z
SF:src/z.c
VER:v1
FNL:5,10,20
FNA:5,1,zb
FNA:5,2,za
BRDA:2,0,e,1
BRDA:2,0,e2,0
MCDC:3,2,f,0,0,expr
MCDC:3,2,t,1,0,expr
DA:1,1
DA:2,1
DA:3,1
DA:10,1
DA:20,0
FNF:9
FNH:9
BRF:9
BRH:9
MCF:9
MCH:9
LF:9
LH:9
end_of_record
TN:a
SF:src/a.c
FNL:0,1,1
FNA:0,1,f
DA:1,1
end_of_record
TN:m
SF:src/a.c
DA:2,1
end_of_record
"""
    )
    mcdc_groups = ascii_bytes(
        """
TN:m
SF:src/m.c
MCDC:1,10,t,1,0,big
MCDC:1,10,f,0,0,big
MCDC:1,2,t,1,0,small
MCDC:1,2,f,0,0,small
MCDC:1,U3,t,1,0,ucond
MCDC:1,3,f,0,0,ucond
MCDC:2,1,f,1,0,sense_first
MCDC:2,1,t,2,0,sense_first
MCDC:3,1,t,1,0,a,b,c
MCDC:3,1,f,0,0,a,b,c
DA:1,1
DA:2,1
DA:3,1
end_of_record
"""
    )
    summaries = ascii_bytes(
        """
TN:s
SF:src/s.c
FNL:0,1,1
FNA:0,1,f
BRDA:1,0,e,1
BRDA:1,0,e2,0
MCDC:1,1,t,1,0,c
MCDC:1,1,f,0,0,c
DA:1,1
DA:2,0
FNF:999
FNH:0
BRF:999
BRH:0
MCF:999
MCH:0
LF:999
LH:0
end_of_record
"""
    )
    forbidden = ascii_bytes(
        """
TN:forb
KF:src/k.c
FN:1,2,foo
FNDA:3,foo
DA:1,1
DA:2,1
FNF:1
FNH:1
LF:9
LH:9
end_of_record_and_junk
"""
    )
    comments = ascii_bytes(
        """
# dropme
TN:c
SF:src/c.c
# mid
DA:1,1,chk
LF:999
LH:bad
end_of_record
"""
    )
    fixedpoint = ascii_bytes(
        """
TN:s
SF:src/s.c
FNL:0,1,1
FNA:0,1,f
FNF:1
FNH:1
BRDA:1,0,e,1
BRDA:1,0,e2,0
BRF:2
BRH:1
MCDC:1,1,t,1,0,c
MCDC:1,1,f,0,0,c
MCF:2
MCH:1
DA:1,1
DA:2,0
LF:2
LH:1
end_of_record
"""
    )
    gzip_plain = ascii_bytes(
        """
TN:g
SF:src/g.c
DA:1,1
end_of_record
"""
    )
    # Deterministic gzip envelope (mtime=0) around the plain payload.
    gzip_valid = _gzip_bytes(gzip_plain)
    gzip_corrupt = b"not-a-gzip-payload"
    gzip_empty = _gzip_bytes(b"")
    non_utf8 = b"TN:x\nSF:src/\xff.c\nDA:1,1\nend_of_record\n"
    converter_xml = ascii_bytes(
        """
<?xml version="1.0" ?>
<!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd">
<coverage line-rate="1.0" branch-rate="1.0" lines-covered="1" lines-valid="1" branches-covered="1" branches-valid="1" complexity="0" version="1.0" timestamp="1">
  <sources><source>.</source></sources>
  <packages><package name="p" line-rate="1" branch-rate="1" complexity="0"><classes>
  <class name="m" filename="mod.py" line-rate="1" branch-rate="1" complexity="0">
    <methods><method name="foo" signature="()" line-rate="1" branch-rate="1"><lines>
      <line number="1" hits="3" branch="false"/>
    </lines></method></methods>
    <lines>
      <line number="1" hits="3" branch="true" condition-coverage="50% (1/2)"><conditions>
        <condition number="0" type="jump" coverage="50%"/>
      </conditions></line>
      <line number="2" hits="1" branch="false"/>
    </lines>
  </class></classes></package></packages></coverage>
"""
    )
    converter_mod = ascii_bytes(
        """
def foo():
  return 1
"""
    )

    return [
        Fixture(
            "writer-order-core",
            "fixtures/writer/order-core.info",
            WRITER_GROUP,
            "Canonical writer file/test/function/alias/branch/MC/DC ordering corpus.",
            order_core,
            "accept",
        ),
        Fixture(
            "writer-mcdc-groups",
            "fixtures/writer/mcdc-groups.info",
            WRITER_GROUP,
            "MC/DC group-size lexical order, U flags, sense order, and comma expressions.",
            mcdc_groups,
            "accept",
        ),
        Fixture(
            "writer-summaries",
            "fixtures/writer/summaries.info",
            WRITER_GROUP,
            "Junk summary payloads that must be recomputed by the canonical writer.",
            summaries,
            "accept",
        ),
        Fixture(
            "writer-forbidden",
            "fixtures/writer/forbidden.info",
            WRITER_GROUP,
            "KF/FN/FNDA and suffixed terminator must not appear in canonical output.",
            forbidden,
            "accept",
        ),
        Fixture(
            "writer-comments",
            "fixtures/writer/comments.info",
            WRITER_GROUP,
            "Input comments and ignored summary/checksum fields must not be reproduced blindly.",
            comments,
            "accept",
        ),
        Fixture(
            "writer-fixedpoint",
            "fixtures/writer/fixedpoint.info",
            WRITER_GROUP,
            "Already-canonical corpus for parse-write-parse and repeated-write fixed point.",
            fixedpoint,
            "accept",
        ),
        Fixture(
            "gzip-plain",
            "fixtures/writer/gzip-plain.info",
            WRITER_GROUP,
            "Plain tracefile used for gzip write transport.",
            gzip_plain,
            "accept",
        ),
        Fixture(
            "gzip-valid",
            "fixtures/writer/gzip-valid.info.gz",
            WRITER_GROUP,
            "Deterministic valid gzip transport payload.",
            gzip_valid,
            "accept",
        ),
        Fixture(
            "gzip-corrupt",
            "fixtures/writer/gzip-corrupt.info.gz",
            WRITER_GROUP,
            "Corrupt non-gzip bytes with .gz name.",
            gzip_corrupt,
            "reject",
        ),
        Fixture(
            "gzip-empty",
            "fixtures/writer/gzip-empty.info.gz",
            WRITER_GROUP,
            "Empty gzip payload transport failure.",
            gzip_empty,
            "reject",
        ),
        Fixture(
            "writer-non-utf8",
            "fixtures/writer/non-utf8.info",
            WRITER_GROUP,
            "Invalid UTF-8 source path retained through parse/write.",
            non_utf8,
            "accept",
        ),
        Fixture(
            "converter-coverage-xml",
            "fixtures/writer/coverage.xml",
            WRITER_GROUP,
            "Real Cobertura-style XML input for xml2lcov/py2lcov direct conversion.",
            converter_xml,
            "accept",
        ),
        Fixture(
            "converter-mod-py",
            "fixtures/writer/mod.py",
            WRITER_GROUP,
            "Companion Python source for py2lcov derived-function mode.",
            converter_mod,
            "accept",
        ),
    ]


def _lcov_write(
    case_id: str,
    fixture_path: str,
    requirement: str,
    description: str,
    flags: list[str],
    *,
    expected_exit: int = 0,
    output_file: str = "output.info",
    input_name: str = "input.info",
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
            input_name,
            "--output-file",
            output_file,
        ],
        "output_file": output_file,
        "expected_exit": expected_exit,
    }
    if input_name != "input.info":
        case["input_name"] = input_name
    if additional_fixtures is not None:
        case["additional_fixtures"] = additional_fixtures
    return case


def _lcov_summary(
    case_id: str,
    fixture_path: str,
    requirement: str,
    description: str,
    flags: list[str],
    *,
    expected_exit: int = 0,
    input_name: str = "input.info",
) -> dict[str, object]:
    case: dict[str, object] = {
        "id": case_id,
        "fixture": fixture_path,
        "requirement": requirement,
        "description": description,
        "argv": ["lcov", *flags, "--summary", input_name],
        "expected_exit": expected_exit,
    }
    if input_name != "input.info":
        case["input_name"] = input_name
    return case


def build_writer_oracle_cases() -> list[dict[str, object]]:
    """Custom Oracle cases for writer/converter/transport identities."""
    no_fn = ["--no-function-coverage"]
    branch_mcdc = ["--branch-coverage", "--mcdc-coverage"]
    mcdc_only = ["--mcdc-coverage", "--no-function-coverage"]
    cases: list[dict[str, object]] = [
        _lcov_write(
            "writer-order-core.canonical",
            "fixtures/writer/order-core.info",
            "M1-TF-041",
            "Canonical writer sorts files/tests and renumbers function/branch/MC/DC fields.",
            branch_mcdc,
        ),
        _lcov_write(
            "writer-mcdc-groups.canonical",
            "fixtures/writer/mcdc-groups.info",
            "M1-TF-041",
            "MC/DC group-size lexical keys, U retention, t-before-f senses, and comma expressions.",
            mcdc_only,
        ),
        _lcov_write(
            "writer-summaries.canonical",
            "fixtures/writer/summaries.info",
            "M1-TF-042",
            "Canonical writer recomputes FNF/FNH, BRF/BRH, MCF/MCH, and LF/LH.",
            branch_mcdc,
        ),
        _lcov_write(
            "writer-comments.canonical",
            "fixtures/writer/comments.info",
            "M1-TF-043",
            "Input comments and ignored summaries/checksums are not blindly reproduced.",
            no_fn,
        ),
        _lcov_write(
            "writer-forbidden.canonical",
            "fixtures/writer/forbidden.info",
            "M1-TF-044",
            "Canonical output never emits KF, FN, FNDA, or suffixed terminators.",
            [],
        ),
        _lcov_write(
            "writer-fixedpoint.canonical",
            "fixtures/writer/fixedpoint.info",
            "M1-TF-045",
            "Parse-write of already-canonical multi-family corpus preserves bytes.",
            branch_mcdc,
        ),
        _lcov_write(
            "writer-fixedpoint.repeated-write",
            "fixtures/writer/fixedpoint.info",
            "M1-TF-046",
            "Repeated write of identical model/configuration inputs is byte-identical.",
            branch_mcdc,
        ),
        {
            "id": "converter-coverage.xml2lcov",
            "fixture": "fixtures/writer/coverage.xml",
            "requirement": "M1-TF-050",
            "description": "xml2lcov direct converter record order, global TN, summaries, no MC/DC.",
            "argv": [
                "xml2lcov",
                "-o",
                "output.info",
                "-t",
                "xml",
                "input.xml",
            ],
            "input_name": "input.xml",
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "converter-coverage.py2lcov-no-functions",
            "fixture": "fixtures/writer/coverage.xml",
            "requirement": "M1-TF-051",
            "description": "py2lcov direct conversion with derived functions disabled.",
            "argv": [
                "py2lcov",
                "-o",
                "output.info",
                "-t",
                "py",
                "--no-functions",
                "input.xml",
            ],
            "input_name": "input.xml",
            "output_file": "output.info",
            "expected_exit": 0,
        },
        {
            "id": "converter-coverage.py2lcov-with-functions",
            "fixture": "fixtures/writer/coverage.xml",
            "requirement": "M1-TF-051",
            "description": "py2lcov direct conversion with derived functions enabled and companion source.",
            "argv": [
                "py2lcov",
                "-o",
                "output.info",
                "-t",
                "py",
                "input.xml",
            ],
            "input_name": "input.xml",
            "output_file": "output.info",
            "expected_exit": 0,
            "additional_fixtures": {"mod.py": "fixtures/writer/mod.py"},
        },
        {
            "id": "converter-coverage.canonical-rewrite",
            "fixture": "fixtures/writer/coverage.xml",
            "requirement": "M1-TF-052",
            "description": "Direct converter output rewritten through canonical lcov writer without semantic loss.",
            "argv": [
                "sh",
                "-c",
                "xml2lcov -o converted.info -t xml input.xml && "
                "lcov --branch-coverage --add-tracefile converted.info --output-file output.info",
            ],
            "input_name": "input.xml",
            "output_file": "output.info",
            "expected_exit": 0,
        },
        _lcov_summary(
            "gzip-valid.summary",
            "fixtures/writer/gzip-valid.info.gz",
            "M1-TF-060",
            "Valid gzip transport summary succeeds.",
            no_fn,
            input_name="input.info.gz",
        ),
        _lcov_write(
            "gzip-plain.write-gz",
            "fixtures/writer/gzip-plain.info",
            "M1-TF-060",
            "Canonical writer emits a readable .gz transport file.",
            no_fn,
            output_file="output.info.gz",
        ),
        _lcov_summary(
            "gzip-corrupt.summary",
            "fixtures/writer/gzip-corrupt.info.gz",
            "M1-TF-060",
            "Corrupt gzip payload hard failure.",
            no_fn,
            expected_exit=1,
            input_name="input.info.gz",
        ),
        _lcov_summary(
            "gzip-empty.summary",
            "fixtures/writer/gzip-empty.info.gz",
            "M1-TF-060",
            "Empty gzip payload hard failure.",
            no_fn,
            expected_exit=1,
            input_name="input.info.gz",
        ),
        {
            "id": "gzip-valid.missing-gzip",
            "fixture": "fixtures/writer/gzip-valid.info.gz",
            "requirement": "M1-TF-060",
            "description": "Missing gzip utility fails gzip transport before parse.",
            "argv": [
                "sh",
                "-c",
                "mkdir -p /tmp/ng && "
                "ln -sf /usr/bin/perl /tmp/ng/perl && "
                "ln -sf /usr/bin/env /tmp/ng/env && "
                "export PATH=/tmp/ng:/usr/local/bin && "
                "lcov --no-function-coverage --summary input.info.gz",
            ],
            "input_name": "input.info.gz",
            "expected_exit": 1,
        },
        _lcov_write(
            "writer-non-utf8.canonical",
            "fixtures/writer/non-utf8.info",
            "M1-TF-061",
            "Invalid UTF-8 source path bytes are retained through parse/write.",
            no_fn,
        ),
    ]
    return cases


WRITER_CASE_IDS = (
    # custom cases in build_writer_oracle_cases order
    "writer-order-core.canonical",
    "writer-mcdc-groups.canonical",
    "writer-summaries.canonical",
    "writer-comments.canonical",
    "writer-forbidden.canonical",
    "writer-fixedpoint.canonical",
    "writer-fixedpoint.repeated-write",
    "converter-coverage.xml2lcov",
    "converter-coverage.py2lcov-no-functions",
    "converter-coverage.py2lcov-with-functions",
    "converter-coverage.canonical-rewrite",
    "gzip-valid.summary",
    "gzip-plain.write-gz",
    "gzip-corrupt.summary",
    "gzip-empty.summary",
    "gzip-valid.missing-gzip",
    "writer-non-utf8.canonical",
)

WRITER_EXACT_REQUIREMENTS: dict[str, list[str]] = {
    "writer-order-core.canonical": ["M1-TF-041"],
    "writer-mcdc-groups.canonical": ["M1-TF-041"],
    "writer-summaries.canonical": ["M1-TF-042"],
    "writer-comments.canonical": ["M1-TF-043"],
    "writer-forbidden.canonical": ["M1-TF-044"],
    "writer-fixedpoint.canonical": ["M1-TF-045"],
    "writer-fixedpoint.repeated-write": ["M1-TF-046"],
    "converter-coverage.xml2lcov": ["M1-TF-050"],
    "converter-coverage.py2lcov-no-functions": ["M1-TF-051"],
    "converter-coverage.py2lcov-with-functions": ["M1-TF-051"],
    "converter-coverage.canonical-rewrite": ["M1-TF-052"],
    "gzip-valid.summary": ["M1-TF-060"],
    "gzip-plain.write-gz": ["M1-TF-060"],
    "gzip-corrupt.summary": ["M1-TF-060"],
    "gzip-empty.summary": ["M1-TF-060"],
    "gzip-valid.missing-gzip": ["M1-TF-060"],
    "writer-non-utf8.canonical": ["M1-TF-061"],
}


def validate_writer_fixture_closure(fixtures: list[Fixture]) -> None:
    writer = [fixture for fixture in fixtures if fixture.group == WRITER_GROUP]
    ids = [fixture.id for fixture in writer]
    if ids != list(WRITER_FIXTURE_IDS):
        raise ValueError(f"writer fixture closure drift: {ids}")
