"""TF-030 exact numeric matrix fixtures, plans, and Oracle cases."""

from __future__ import annotations

import json

from corpus_model import Fixture, ascii_bytes

TF030_UPSTREAM_ATOMS = (
    ("DA", "-3", {"line": 4}, "DA:4,-3", 1),
    ("DA", "1.a0e+19", {"line": 10}, "DA:10,1.a0e+19", 2),
    ("DA", "1.0e+19", {"line": 12}, "DA:12,1.0e+19", 3),
    ("FNDA", "-2", {"function_name": "alias", "alias": "alias"}, "FNDA:-2,alias", 1),
    ("FNDA", "1.5eb+20", {"function_name": "alias2", "alias": "alias2"}, "FNDA:1.5eb+20,alias2", 2),
    ("FNDA", "1.5e+20", {"function_name": "alias3", "alias": "alias3"}, "FNDA:1.5e+20,alias3", 3),
    ("FNDA", "-0", {"function_name": "onlyA", "alias": "onlyA"}, "FNDA:-0,onlyA", 4),
    ("BRDA", "-1", {"line": 1, "block": 1, "branch": 1, "expression": None}, "BRDA:1,1,1,-1", 1),
    ("BRDA", "-", {"line": 1, "block": 1, "branch": 2, "expression": None}, "BRDA:1,1,2,-", 2),
    ("BRDA", "1.67+20", {"line": 1, "block": 2, "branch": 0, "expression": None}, "BRDA:1,2,0,1.67+20", 3),
    ("BRDA", "1.67e+20", {"line": 1, "block": 2, "branch": 1, "expression": None}, "BRDA:1,2,1,1.67e+20", 4),
    ("BRDA", "-0", {"line": 11, "block": 0, "branch": 1, "expression": None}, "BRDA:11,0,1,-0", 5),
)

TF030_FNA_ATOMS = ("-2", "1.5eb+20", "1.5e+20", "-0")
TF030_CANDIDATE_ATOMS = (
    "0",
    "+1",
    "1.5",
    "1e3",
    "Inf",
    "+Inf",
    "Infinity",
    "NaN",
    "nan",
    "-Inf",
)

TF030_FIXTURE_IDS = (
    "numeric-tf030-fna-mirror",
    "numeric-tf030-candidate-matrix",
    "numeric-tf030-format-atoms-plan",
    "numeric-tf030-fna-mirror-plan",
    "numeric-tf030-candidate-plan",
)

TF030_CASE_IDS = (
    "numeric-format-atoms.tf030.semantic-snapshot",
    "numeric-format-atoms.tf030-threshold.semantic-snapshot",
    "numeric-tf030-fna-mirror.default-stop",
    "numeric-tf030-fna-mirror.ignore-negative-stop-format",
    "numeric-tf030-fna-mirror.ignore-negative-format.canonical",
    "numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot",
    "numeric-tf030-fna-mirror.threshold-default-stop",
    "numeric-tf030-fna-mirror.threshold-ignore-all.canonical",
    "numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot",
    "numeric-tf030-candidates.default-stop",
    "numeric-tf030-candidates.ignore-negative.canonical",
    "numeric-tf030-candidates.ignore-negative.semantic-snapshot",
    "numeric-tf030-candidates.threshold-default-stop",
    "numeric-tf030-candidates.threshold-ignore-all.canonical",
    "numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot",
)

TF030_SKIP_SUMMARY_FIXTURE_IDS = set(TF030_FIXTURE_IDS)


def slug_atom(atom: str) -> str:
    mapping = {
        "-3": "neg3",
        "1.a0e+19": "malformed_a0e",
        "1.0e+19": "one_e19",
        "-2": "neg2",
        "1.5eb+20": "malformed_eb",
        "1.5e+20": "one_point_five_e20",
        "-0": "neg0",
        "-1": "neg1",
        "-": "dash",
        "1.67+20": "malformed_plus",
        "1.67e+20": "one_point_six_seven_e20",
        "0": "zero",
        "+1": "plus_one",
        "1.5": "one_point_five",
        "1e3": "one_e3",
        "Inf": "inf",
        "+Inf": "plus_inf",
        "-Inf": "neg_inf",
        "Infinity": "infinity",
        "NaN": "nan_upper",
        "nan": "nan_lower",
    }
    if atom not in mapping:
        raise ValueError(f"unmapped atom slug: {atom!r}")
    return mapping[atom]


def plan_document(rows: list[dict[str, object]]) -> bytes:
    document = {
        "schema_version": 1,
        "kind": "tf030_numeric_plan",
        "rows": rows,
    }
    return (json.dumps(document, indent=2, sort_keys=False) + "\n").encode("ascii")


def build_tf030_format_atoms_plan_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for family, atom, locator, raw, ordinal in TF030_UPSTREAM_ATOMS:
        reader = "brda_never_evaluated" if family == "BRDA" and atom == "-" else "looks_like_number"
        rows.append(
            {
                "id": f"format.{family.lower()}.{slug_atom(atom)}",
                "family": family,
                "lexeme": atom,
                "fixture": "fixtures/numeric/format-atoms.info",
                "source": "a.cpp",
                "testcase": "",
                "reader_match_kind": reader,
                "raw_record": raw,
                "record_ordinal": ordinal,
                "locator": locator,
            }
        )
    return rows


def build_tf030_fna_mirror_fixture_and_plan() -> tuple[bytes, list[dict[str, object]]]:
    lines = [
        "TN:tf030_fna_mirror",
        "SF:src/tf030-fna-mirror.c",
    ]
    rows: list[dict[str, object]] = []
    for index, atom in enumerate(TF030_FNA_ATOMS):
        alias = f"fna_{slug_atom(atom)}"
        # Distinct start lines so zero-coerced function hits cannot conflict
        # with a shared positive line sentinel under data-consistency checks.
        start = index + 1
        lines.append(f"FNL:{index},{start},{start}")
        lines.append(f"FNA:{index},{atom},{alias}")
        rows.append(
            {
                "id": f"fna_mirror.fna.{slug_atom(atom)}",
                "family": "FNA",
                "lexeme": atom,
                "fixture": "fixtures/numeric/tf030-fna-exact-mirror.info",
                "source": "src/tf030-fna-mirror.c",
                "testcase": "tf030_fna_mirror",
                "reader_match_kind": "looks_like_number",
                "raw_record": f"FNA:{index},{atom},{alias}",
                "record_ordinal": index + 1,
                "locator": {"function_index": index, "alias": alias},
            }
        )
    # Line hits must not claim coverage for functions that coerce to zero.
    # -2 and 1.5eb+20 become zero; 1.5e+20 remains hit; -0 is signed zero (not hit).
    lines.extend(
        [
            "DA:1,0",
            "DA:2,0",
            "DA:3,1",
            "DA:4,0",
            "LF:4",
            "LH:1",
            "end_of_record",
        ]
    )
    return ascii_bytes("\n".join(lines)), rows


def build_tf030_candidate_fixture_and_plan() -> tuple[bytes, list[dict[str, object]]]:
    families = ("DA", "FNDA", "FNA", "BRDA")
    chunks: list[str] = []
    rows: list[dict[str, object]] = []
    for family in families:
        source = f"src/tf030-candidate-{family.lower()}.c"
        testcase = f"tf030_candidate_{family.lower()}"
        chunks.append(f"TN:{testcase}")
        chunks.append(f"SF:{source}")
        ordinal = 0
        if family == "FNDA":
            for index, atom in enumerate(TF030_CANDIDATE_ATOMS):
                name = f"fn_{slug_atom(atom)}"
                chunks.append(f"FN:{index + 1},{index + 1},{name}")
        if family == "FNA":
            for index, atom in enumerate(TF030_CANDIDATE_ATOMS):
                chunks.append(f"FNL:{index},{index + 1},{index + 1}")
        for index, atom in enumerate(TF030_CANDIDATE_ATOMS):
            ordinal += 1
            slug = slug_atom(atom)
            if family == "DA":
                line = index + 1
                raw = f"DA:{line},{atom}"
                chunks.append(raw)
                locator: dict[str, object] = {"line": line}
            elif family == "FNDA":
                name = f"fn_{slug}"
                raw = f"FNDA:{atom},{name}"
                chunks.append(raw)
                locator = {"function_name": name, "alias": name}
            elif family == "FNA":
                alias = f"alias_{slug}"
                raw = f"FNA:{index},{atom},{alias}"
                chunks.append(raw)
                locator = {"function_index": index, "alias": alias}
            else:
                line = 1
                block = 0
                branch = index
                raw = f"BRDA:{line},{block},{branch},{atom}"
                chunks.append(raw)
                locator = {
                    "line": line,
                    "block": block,
                    "branch": branch,
                    "expression": None,
                }
            rows.append(
                {
                    "id": f"candidate.{family.lower()}.{slug}",
                    "family": family,
                    "lexeme": atom,
                    "fixture": "fixtures/numeric/tf030-candidate-matrix.info",
                    "source": source,
                    "testcase": testcase,
                    "reader_match_kind": "looks_like_number",
                    "raw_record": raw,
                    "record_ordinal": ordinal,
                    "locator": locator,
                }
            )
        if family == "DA":
            chunks.append(f"LF:{len(TF030_CANDIDATE_ATOMS)}")
            # Hit count is not authoritative for this matrix; keep LF/LH closed.
            chunks.append(f"LH:{len(TF030_CANDIDATE_ATOMS)}")
        elif family in {"FNDA", "FNA"}:
            # Match line hit state to post-recovery function hits so consistency
            # checks do not fire: zero and -Inf become non-hit; all others hit.
            for index, atom in enumerate(TF030_CANDIDATE_ATOMS):
                line = index + 1
                line_hit = "0" if atom in {"0", "-Inf"} else "1"
                chunks.append(f"DA:{line},{line_hit}")
            chunks.append(f"LF:{len(TF030_CANDIDATE_ATOMS)}")
            chunks.append(
                f"LH:{sum(0 if atom in {'0', '-Inf'} else 1 for atom in TF030_CANDIDATE_ATOMS)}"
            )
        else:
            # BRDA-only section needs a valid line sentinel.
            chunks.extend(["DA:1,1", "LF:1", "LH:1"])
        chunks.append("end_of_record")
    return ascii_bytes("\n".join(chunks)), rows


def tf030_numeric_fixtures() -> list[Fixture]:
    fna_data, fna_rows = build_tf030_fna_mirror_fixture_and_plan()
    cand_data, cand_rows = build_tf030_candidate_fixture_and_plan()
    format_rows = build_tf030_format_atoms_plan_rows()
    if len(format_rows) != 12 or len(fna_rows) != 4 or len(cand_rows) != 40:
        raise ValueError(
            f"TF-030 row closure drift: {len(format_rows)}/{len(fna_rows)}/{len(cand_rows)}"
        )
    return [
        Fixture(
            "numeric-tf030-fna-mirror",
            "fixtures/numeric/tf030-fna-exact-mirror.info",
            "numeric-boundary",
            "Current FNL/FNA mirror of the four legacy function-count atoms required by TF-030.",
            fna_data,
            "reject",
            parameters={"tf030_rows": 4, "role": "tf030_fna_mirror"},
        ),
        Fixture(
            "numeric-tf030-candidate-matrix",
            "fixtures/numeric/tf030-candidate-matrix.info",
            "numeric-boundary",
            "Cross-family TF-030 candidate matrix covering ten atoms across DA/FNDA/FNA/BRDA.",
            cand_data,
            "reject",
            parameters={"tf030_rows": 40, "role": "tf030_candidate_matrix"},
        ),
        Fixture(
            "numeric-tf030-format-atoms-plan",
            "fixtures/numeric/tf030-format-atoms-plan.json",
            "numeric-boundary",
            "Strict ASCII JSON plan for the 12 upstream format-atoms TF-030 rows.",
            plan_document(format_rows),
            "accept",
            parameters={"tf030_rows": 12, "role": "tf030_plan"},
        ),
        Fixture(
            "numeric-tf030-fna-mirror-plan",
            "fixtures/numeric/tf030-fna-mirror-plan.json",
            "numeric-boundary",
            "Strict ASCII JSON plan for the four FNA mirror TF-030 rows.",
            plan_document(fna_rows),
            "accept",
            parameters={"tf030_rows": 4, "role": "tf030_plan"},
        ),
        Fixture(
            "numeric-tf030-candidate-plan",
            "fixtures/numeric/tf030-candidate-plan.json",
            "numeric-boundary",
            "Strict ASCII JSON plan for the 40 candidate TF-030 rows.",
            plan_document(cand_rows),
            "accept",
            parameters={"tf030_rows": 40, "role": "tf030_plan"},
        ),
    ]


def build_tf030_oracle_cases() -> list[dict[str, object]]:
    format_plan = "tf030-format-atoms-plan.json"
    fna_plan = "tf030-fna-mirror-plan.json"
    cand_plan = "tf030-candidate-plan.json"
    cases: list[dict[str, object]] = [
        {
            "id": "numeric-format-atoms.tf030.semantic-snapshot",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-030",
            "description": "TF-030 row-level semantic snapshot for the 12 upstream format-atoms without threshold.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl",
                "inspect_model.pl",
                "--ignore",
                "format,negative",
                "--numeric-plan",
                format_plan,
                "input.info",
            ],
            "additional_fixtures": {
                format_plan: "fixtures/numeric/tf030-format-atoms-plan.json",
            },
            "expected_exit": 0,
        },
        {
            "id": "numeric-format-atoms.tf030-threshold.semantic-snapshot",
            "fixture": "fixtures/numeric/format-atoms.info",
            "requirement": "M1-TF-030",
            "description": "TF-030 row-level semantic snapshot for the 12 upstream format-atoms with threshold 1000000.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl",
                "inspect_model.pl",
                "--ignore",
                "format,negative,excessive",
                "--excessive-threshold",
                "1000000",
                "--numeric-plan",
                format_plan,
                "input.info",
            ],
            "additional_fixtures": {
                format_plan: "fixtures/numeric/tf030-format-atoms-plan.json",
            },
            "expected_exit": 0,
        },
        {
            "id": "numeric-tf030-fna-mirror.default-stop",
            "fixture": "fixtures/numeric/tf030-fna-exact-mirror.info",
            "requirement": "M1-TF-030",
            "description": "Default stop on FNA -2 negative; output absent.",
            "argv": [
                "lcov",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
            "expected_output_exists": False,
        },
        {
            "id": "numeric-tf030-fna-mirror.ignore-negative-stop-format",
            "fixture": "fixtures/numeric/tf030-fna-exact-mirror.info",
            "requirement": "M1-TF-030",
            "description": "Ignore negative then stop on malformed exponent format; output absent.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "negative",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
            "expected_output_exists": False,
        },
        {
            "id": "numeric-tf030-fna-mirror.ignore-negative-format.canonical",
            "fixture": "fixtures/numeric/tf030-fna-exact-mirror.info",
            "requirement": "M1-TF-030",
            "description": "Ignore negative and format; coerce first two atoms to zero and retain 1.5e+20 and -0.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "negative,format",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot",
            "fixture": "fixtures/numeric/tf030-fna-exact-mirror.info",
            "requirement": "M1-TF-030",
            "description": "TF-030 semantic snapshot for four FNA mirror rows without threshold.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl",
                "inspect_model.pl",
                "--ignore",
                "negative,format",
                "--numeric-plan",
                fna_plan,
                "input.info",
            ],
            "additional_fixtures": {
                fna_plan: "fixtures/numeric/tf030-fna-mirror-plan.json",
            },
            "expected_exit": 0,
        },
        {
            "id": "numeric-tf030-fna-mirror.threshold-default-stop",
            "fixture": "fixtures/numeric/tf030-fna-exact-mirror.info",
            "requirement": "M1-TF-030",
            "description": "With threshold 1000000 and negative/format ignored, stop on excessive 1.5e+20.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "negative,format",
                "--rc",
                "excessive_count_threshold=1000000",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
            "expected_output_exists": False,
        },
        {
            "id": "numeric-tf030-fna-mirror.threshold-ignore-all.canonical",
            "fixture": "fixtures/numeric/tf030-fna-exact-mirror.info",
            "requirement": "M1-TF-030",
            "description": "Ignore negative/format/excessive with threshold; retain excessive value.",
            "argv": [
                "lcov",
                "--ignore-errors",
                "negative,format,excessive",
                "--rc",
                "excessive_count_threshold=1000000",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot",
            "fixture": "fixtures/numeric/tf030-fna-exact-mirror.info",
            "requirement": "M1-TF-030",
            "description": "TF-030 semantic snapshot for four FNA mirror rows with threshold 1000000.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl",
                "inspect_model.pl",
                "--ignore",
                "negative,format,excessive",
                "--excessive-threshold",
                "1000000",
                "--numeric-plan",
                fna_plan,
                "input.info",
            ],
            "additional_fixtures": {
                fna_plan: "fixtures/numeric/tf030-fna-mirror-plan.json",
            },
            "expected_exit": 0,
        },
        {
            "id": "numeric-tf030-candidates.default-stop",
            "fixture": "fixtures/numeric/tf030-candidate-matrix.info",
            "requirement": "M1-TF-030",
            "description": "Without threshold, -Inf selects negative and default stop leaves output absent.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
            "expected_output_exists": False,
        },
        {
            "id": "numeric-tf030-candidates.ignore-negative.canonical",
            "fixture": "fixtures/numeric/tf030-candidate-matrix.info",
            "requirement": "M1-TF-030",
            "description": "Ignore negative coerces only -Inf to zero and writes output.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--ignore-errors",
                "negative",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-tf030-candidates.ignore-negative.semantic-snapshot",
            "fixture": "fixtures/numeric/tf030-candidate-matrix.info",
            "requirement": "M1-TF-030",
            "description": "TF-030 semantic snapshot for all 40 candidate rows without threshold.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl",
                "inspect_model.pl",
                "--ignore",
                "negative",
                "--numeric-plan",
                cand_plan,
                "input.info",
            ],
            "additional_fixtures": {
                cand_plan: "fixtures/numeric/tf030-candidate-plan.json",
            },
            "expected_exit": 0,
        },
        {
            "id": "numeric-tf030-candidates.threshold-default-stop",
            "fixture": "fixtures/numeric/tf030-candidate-matrix.info",
            "requirement": "M1-TF-030",
            "description": "With threshold 1000000, first positive infinity selects excessive before -Inf.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--ignore-errors",
                "negative",
                "--rc",
                "excessive_count_threshold=1000000",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 1,
            "expected_output_exists": False,
        },
        {
            "id": "numeric-tf030-candidates.threshold-ignore-all.canonical",
            "fixture": "fixtures/numeric/tf030-candidate-matrix.info",
            "requirement": "M1-TF-030",
            "description": "Ignore negative/excessive; retain infinities and NaNs; coerce -Inf to zero.",
            "argv": [
                "lcov",
                "--branch-coverage",
                "--ignore-errors",
                "negative,excessive",
                "--rc",
                "excessive_count_threshold=1000000",
                "--add-tracefile",
                "input.info",
                "--output-file",
                "output.info",
            ],
            "output_file": "output.info",
            "expected_exit": 0,
            "expected_output_exists": True,
        },
        {
            "id": "numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot",
            "fixture": "fixtures/numeric/tf030-candidate-matrix.info",
            "requirement": "M1-TF-030",
            "description": "TF-030 semantic snapshot for all 40 candidate rows with threshold 1000000.",
            "runner": "inspect_model.pl",
            "argv": [
                "perl",
                "inspect_model.pl",
                "--ignore",
                "negative,excessive",
                "--excessive-threshold",
                "1000000",
                "--numeric-plan",
                cand_plan,
                "input.info",
            ],
            "additional_fixtures": {
                cand_plan: "fixtures/numeric/tf030-candidate-plan.json",
            },
            "expected_exit": 0,
        },
    ]
    if [case["id"] for case in cases] != list(TF030_CASE_IDS):
        raise ValueError("TF-030 case name registry drift")
    return cases
