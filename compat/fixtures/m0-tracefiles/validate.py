#!/usr/bin/env python3
"""Validate the generated corpus, manifest, and pinned Oracle baseline."""

from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
import re
import tempfile
from pathlib import Path

import generate
from validation_common import (
    ALLOWED_ARGV_HEADS,
    MODEL_INSPECTOR,
    MODEL_INSPECTOR_NAME,
    ROOT,
    SEMANTIC_SNAPSHOT_CASE_IDS,
    SEMANTIC_STDERR_POLICIES,
    assert_branch_store,
    assert_count_store,
    assert_four_family_maps,
    assert_function_store,
    assert_mcdc_store,
    assert_single_testcase_parity,
    decode_identity,
    require,
    semantic_inputs_from_argv,
    strict_json_file,
    strict_json_loads_ascii,
    validate_lcov_stderr,
    validate_semantic_input_identity,
    validate_semantic_stderr,
    verify_identity,
)
from validation_numeric import (
    ADDED_CASE_ARGV,
    ADDED_OUTPUT_EXPECTATIONS,
    CHECKSUM_MD5_BASE64,
    CHECKSUM_SOURCE_BYTES,
    CHECKSUM_SOURCE_SHA256,
    NUMERIC_FIXTURE_IDS,
    validate_added_numeric_case,
    validate_functions_zero_start_snapshot,
    validate_numeric_boundary_snapshot,
    validate_numeric_extra_spellings_snapshot,
    validate_numeric_fna_nonnumeric_snapshot,
    validate_numeric_format_atoms_snapshot,
    validate_numeric_invalid_fnl_fields_snapshot,
    validate_numeric_negative_inf_snapshot,
    validate_numeric_signed_zero_snapshot,
    validate_numeric_zero_fn_end_snapshot,
    validate_tf030_numeric_rows,
)

EXPECTED_MODEL_INSPECTOR_SHA256 = "3a42fd4bf38e2ba02341f5b2d3afd4ecc18f40b402ec5745c315fa916d749bae"

STATE_FIXTURE_IDS = (
    "state-late-tn-mcdc",
    "state-cross-sf-mcdc-success",
    "state-cross-sf-mcdc-duplicate",
)
FUNCTION_FIXTURE_IDS = (
    "functions-current-core",
    "functions-current-missing-alias",
    "functions-zero-end",
    "functions-zero-start",
    "functions-mixed-merge",
    "functions-mixed-location-mismatch",
    "functions-mixed-range-mismatch",
    "functions-index-duplicate",
    "functions-index-unknown",
    "functions-index-scope-reset",
    "functions-index-tn-preserves",
)
BRANCH_FIXTURE_IDS = (
    "branches-forms-core",
    "branches-u-modes",
    "branches-malformed-tail",
    "branches-malformed-tail-empty-taken",
    "branches-malformed-tail-empty-expression",
    "branches-expression-mismatch",
    "branches-expression-merge-left",
    "branches-expression-merge-right",
    "branches-order-gaps",
    "branches-noncontiguous",
    "branches-interleave",
    "branches-sort-signatures",
)

def validate_manifest() -> tuple[dict[str, object], dict[str, generate.Fixture]]:
    manifest = strict_json_file(ROOT / "manifest.json", "manifest.json")
    fixtures = generate.build_fixtures()
    generated_manifest = generate.build_manifest(fixtures)
    require(manifest == generated_manifest, "manifest.json is not the exact generator result")
    by_path = {fixture.path: fixture for fixture in fixtures}

    tracked = {
        path.relative_to(ROOT).as_posix()
        for directory in (ROOT / "fixtures", ROOT / "generated")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file()
    }
    require(not (tracked - set(by_path)), f"unmanifested fixture paths: {sorted(tracked - set(by_path))}")
    required_paths = {fixture.path for fixture in fixtures if fixture.committed}
    require(not (required_paths - tracked), f"missing committed fixtures: {sorted(required_paths - tracked)}")
    # Git-tracked invariant for companion sources that are not .info records.
    git_tracked = {
        line
        for line in __import__("subprocess")
        .check_output(["git", "-C", str(ROOT), "ls-files", "--", "fixtures"], text=True)
        .splitlines()
        if line
    }
    companion_paths = {fixture.path for fixture in fixtures if fixture.committed and not fixture.path.endswith(".info")}
    require(
        companion_paths <= git_tracked,
        f"companion fixtures must be git-tracked: {sorted(companion_paths - git_tracked)}",
    )

    for fixture in fixtures:
        path = ROOT / fixture.path
        if not path.exists():
            require(not fixture.committed, f"missing committed fixture: {fixture.path}")
            continue
        require(path.read_bytes() == fixture.data, f"fixture bytes differ from generator: {fixture.path}")

    required_ids = {
        "current-all-records", "legacy", "permissive-prefix", "numeric-boundary",
        "bytes-crlf", "bytes-no-final-newline", "bytes-non-utf8", "bytes-nul-accepted",
        "state-late-tn-mcdc", "state-cross-sf-mcdc-success", "state-cross-sf-mcdc-duplicate",
        "ver-repeat-equal", "ver-repeat-different", "ver-per-source",
        "functions-current-core", "functions-current-missing-alias", "functions-zero-end",
        "functions-zero-start", "functions-mixed-merge", "functions-mixed-location-mismatch",
        "functions-mixed-range-mismatch", "functions-index-duplicate", "functions-index-unknown",
        "functions-index-scope-reset", "functions-index-tn-preserves",
        "branches-forms-core", "branches-u-modes", "branches-malformed-tail",
        "branches-malformed-tail-empty-taken", "branches-malformed-tail-empty-expression",
        "branches-expression-mismatch",
        "branches-expression-merge-left", "branches-expression-merge-right",
        "branches-order-gaps", "branches-noncontiguous", "branches-interleave",
        "branches-sort-signatures",
        "scale-medium", "scale-large",
    }
    by_id = {fixture.id: fixture for fixture in fixtures}
    require(required_ids <= set(by_id), f"missing required fixture IDs: {sorted(required_ids - set(by_id))}")
    require(by_id["bytes-crlf"].data.endswith(b"\r\n"), "CRLF fixture invariant failed")
    require(not by_id["bytes-no-final-newline"].data.endswith(b"\n"), "no-final-newline invariant failed")
    try:
        by_id["bytes-non-utf8"].data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        raise ValueError("non-UTF-8 fixture unexpectedly decodes")
    require(b"\x00" in by_id["bytes-nul-accepted"].data, "NUL fixture lacks NUL")
    require(by_id["bytes-nul-accepted"].oracle_default == "accept", "NUL decision must be accept")
    require(b"TN:,diff" in by_id["permissive-prefix"].data, "TN:,diff boundary missing")
    require(b"KF:" in by_id["permissive-prefix"].data, "KF boundary missing")
    require(b"BRDA:2,fU" in by_id["current-all-records"].data, "BRDA f/U boundary missing")
    require(b"MCDC:4,U" in by_id["current-all-records"].data, "MCDC U boundary missing")
    require(b"FNL:" in by_id["current-all-records"].data and b"FNA:" in by_id["current-all-records"].data, "current FNL/FNA input missing")
    require(b"TN:A\nSF:/m0/late-tn.c\n" in by_id["state-late-tn-mcdc"].data, "late-TN ownership bytes missing")
    require(b"TN:B\nMCDC:1,1,f,1,0,cond\n" in by_id["state-late-tn-mcdc"].data, "late-TN B MC/DC bytes missing")
    require(b"SF:/m0/first.c\n" in by_id["state-cross-sf-mcdc-success"].data, "cross-SF first source missing")
    require(b"SF:/m0/next.c\n" in by_id["state-cross-sf-mcdc-success"].data, "cross-SF next source missing")
    require(b"MCDC:1,1,f,1,0,first\n" in by_id["state-cross-sf-mcdc-duplicate"].data, "cross-SF duplicate line1 MC/DC missing")
    require(by_id["state-cross-sf-mcdc-duplicate"].oracle_default == "reject", "duplicate fixture must reject")
    require(b"FNA:0,2,alpha_alias,with,commas\n" in by_id["functions-current-core"].data, "comma alias fixture missing")
    require(b"FNL:5,30,40\n" in by_id["functions-current-core"].data, "noncontiguous FNL index missing")
    require(b"FNL:7,50\n" in by_id["functions-current-core"].data, "optional-end FNL missing")
    require(b"FNA:0,1\n" in by_id["functions-current-missing-alias"].data, "missing alias fixture missing")
    require(b"FNL:0,5,0\n" in by_id["functions-zero-end"].data, "zero-end FNL missing")
    require(b"FNL:0,0,5\n" in by_id["functions-zero-start"].data, "zero-start FNL missing")
    require(b"FN:10,20,alpha\n" in by_id["functions-mixed-merge"].data, "mixed merge FN missing")
    require(b"FNA:0,2,alpha\n" in by_id["functions-mixed-merge"].data, "mixed merge FNA missing")
    require(b"FN:10,20,alpha\n" in by_id["functions-mixed-location-mismatch"].data, "mixed location FN missing")
    require(b"FNL:0,30,40\n" in by_id["functions-mixed-location-mismatch"].data, "mixed location FNL missing")
    require(b"FN:10,20,alpha\n" in by_id["functions-mixed-range-mismatch"].data, "mixed range FN missing")
    require(b"FNL:0,10,40\n" in by_id["functions-mixed-range-mismatch"].data, "mixed range FNL missing")
    require(by_id["functions-index-duplicate"].data.count(b"FNL:0,") == 2, "duplicate index fixture missing second FNL:0")
    require(b"FNA:9,1,ghost\n" in by_id["functions-index-unknown"].data, "unknown index fixture missing")
    require(b"SF:src/fn-scope-a.c\n" in by_id["functions-index-scope-reset"].data, "scope-reset first source missing")
    require(b"SF:src/fn-scope-b.c\n" in by_id["functions-index-scope-reset"].data, "scope-reset second source missing")
    require(b"TN:fn_tn_b\nFNL:0,3,4\n" in by_id["functions-index-tn-preserves"].data, "TN-preserves index reuse missing")
    require(by_id["functions-current-missing-alias"].oracle_default == "reject", "missing alias must reject")
    require(by_id["functions-zero-start"].oracle_default == "reject", "zero-start default must reject")
    require(by_id["functions-mixed-location-mismatch"].oracle_default == "reject", "location mismatch must reject")
    require(by_id["functions-mixed-range-mismatch"].oracle_default == "reject", "range mismatch must reject")
    require(by_id["functions-index-duplicate"].oracle_default == "reject", "duplicate index must reject")
    require(by_id["functions-index-unknown"].oracle_default == "reject", "unknown index must reject")
    require(by_id["functions-index-tn-preserves"].oracle_default == "reject", "TN-preserves reuse must reject")
    require(b"BRDA:20,e0,exception,0\n" in by_id["branches-forms-core"].data, "exception BRDA form missing")
    require(b"BRDA:30,f0,fall,1\n" in by_id["branches-forms-core"].data, "fallthrough BRDA form missing")
    require(b"BRDA:40,U0,unreach,0\n" in by_id["branches-forms-core"].data, "U BRDA form missing")
    require(b"BRDA:50,0,never,-\n" in by_id["branches-forms-core"].data, "dash taken BRDA missing")
    require(b"BRDA:60,0,a,b,c,2\n" in by_id["branches-forms-core"].data, "comma-bearing expression missing")
    require(b"BRDA:70,0,0,1\n" in by_id["branches-forms-core"].data, "numeric expression identity missing")
    require(b"BRDA:10,U0,unreach,0\n" in by_id["branches-u-modes"].data, "u-modes U form missing")
    require(b"BRDA:20,fU0,x > 0,0\n" in by_id["branches-u-modes"].data, "u-modes fU form missing")
    require(b"BRDA:30,eU0,exc,0\n" in by_id["branches-u-modes"].data, "u-modes eU form missing")
    require(b"BRDA:1,0,expr\n" in by_id["branches-malformed-tail"].data, "malformed-tail BRDA missing")
    require(
        b"BRDA:1,0,expr,\n" in by_id["branches-malformed-tail-empty-taken"].data,
        "malformed-tail empty-taken BRDA missing",
    )
    require(
        b"BRDA:1,0,,1\n" in by_id["branches-malformed-tail-empty-expression"].data,
        "malformed-tail empty-expression BRDA missing",
    )
    require(
        b"BRDA:10,0,first,1\nBRDA:10,0,second,0\n"
        in by_id["branches-expression-mismatch"].data,
        "expression-mismatch positional branch probe missing",
    )
    require(
        b"BRDA:10,0,left,1\nBRDA:10,0,left_else,0\n"
        in by_id["branches-expression-merge-left"].data,
        "expression-merge left identity probe missing",
    )
    require(
        b"BRDA:10,0,right,2\nBRDA:10,0,right_else,3\n"
        in by_id["branches-expression-merge-right"].data,
        "expression-merge right identity probe missing",
    )
    require(b"BRDA:10,5,a,1\n" in by_id["branches-order-gaps"].data, "order-gaps first block missing")
    require(b"BRDA:10,9,f,0\n" in by_id["branches-order-gaps"].data, "order-gaps last block missing")
    require(b"BRDA:10,0,e,1\n" in by_id["branches-noncontiguous"].data, "noncontiguous line reuse missing")
    require(b"BRDA:10,1,c,1\n" in by_id["branches-interleave"].data, "interleave second block missing")
    require(b"BRDA:10,e2,e0,1\n" in by_id["branches-sort-signatures"].data, "sort exception signature missing")
    require(by_id["branches-malformed-tail"].oracle_default == "reject", "malformed-tail must reject")
    require(
        by_id["branches-malformed-tail-empty-taken"].oracle_default == "reject",
        "malformed-tail empty taken must reject",
    )
    require(
        by_id["branches-malformed-tail-empty-expression"].oracle_default == "accept",
        "malformed-tail empty expression must accept",
    )
    require(
        by_id["branches-expression-mismatch"].oracle_default == "accept",
        "expression mismatch probe must accept",
    )
    for profile in ("scale-medium", "scale-large"):
        require(not by_id[profile].committed, f"{profile} must remain generated-only")
    require(set(NUMERIC_FIXTURE_IDS) <= set(by_id), f"missing numeric fixtures: {sorted(set(NUMERIC_FIXTURE_IDS) - set(by_id))}")
    require(by_id["checksum-source-cs"].data == CHECKSUM_SOURCE_BYTES, "checksum companion source bytes drift")
    require(
        hashlib.sha256(by_id["checksum-source-cs"].data).hexdigest() == CHECKSUM_SOURCE_SHA256,
        "checksum companion source sha256 drift",
    )
    require(CHECKSUM_MD5_BASE64.encode("ascii") in by_id["checksum-match"].data, "checksum-match must embed md5_base64 identity")
    require(b"DA:1,1,WRONGCHK\n" in by_id["checksum-mismatch"].data, "checksum-mismatch token missing")
    require(b"DA:1,1\n" in by_id["checksum-missing"].data, "checksum-missing must omit checksum field")
    require(b"OTHERCHK" in by_id["checksum-duplicate"].data, "checksum-duplicate alternate token missing")
    require(by_id["numeric-format-atoms"].data.count(b" ") >= 1, "format-atoms must retain upstream trailing spaces")
    require(b"DA:4,-3\n" in by_id["numeric-format-atoms"].data, "format-atoms negative DA missing")
    require(b"DA:1,-0\n" in by_id["numeric-signed-zero"].data, "signed-zero DA missing")
    require(b"BRDA:2,0,expr,-0\n" in by_id["numeric-signed-zero"].data, "signed-zero BRDA missing")
    require(by_id["numeric-boundary"].parameters.get("accepted_lexemes") == 15, "numeric-boundary accepted lexeme count drift")
    require(by_id["numeric-extra-spellings"].parameters.get("accepted_lexemes") == 3, "extra-spellings accepted lexeme count drift")
    require(MODEL_INSPECTOR.is_file(), "missing inspect_model.pl")
    inspector_bytes = MODEL_INSPECTOR.read_bytes()
    require(inspector_bytes.startswith(b"#!/usr/bin/env perl\n"), "inspect_model.pl must be a perl script")
    require(
        hashlib.sha256(inspector_bytes).hexdigest() == EXPECTED_MODEL_INSPECTOR_SHA256,
        "inspect_model.pl identity drift",
    )

    with tempfile.TemporaryDirectory(prefix="ferricov-m0-validate-") as raw_temp:
        regenerated_root = Path(raw_temp)
        regenerated_manifest = generate.write_corpus(regenerated_root, include_scale=True)
        require(regenerated_manifest == manifest, "temporary regeneration changed the manifest")
        for fixture in fixtures:
            regenerated = regenerated_root / fixture.path
            require(regenerated.read_bytes() == fixture.data, f"temporary regeneration mismatch: {fixture.path}")
            entry = next(item for item in manifest["fixtures"] if item["id"] == fixture.id)
            metadata = generate.data_metadata(regenerated.read_bytes())
            for key, value in metadata.items():
                require(entry[key] == value, f"manifest {key} mismatch: {fixture.id}")
    return manifest, by_path

def validate_late_tn_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "late-TN snapshot kind mismatch")
    require(document.get("schema_version") == 1, "late-TN snapshot schema mismatch")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 1, "late-TN must retain exactly one source")
    source = sources[0]
    require(source.get("filename") == "/m0/late-tn.c", "late-TN source path mismatch")
    aggregate = source["aggregate"]
    assert_count_store(aggregate["line"], "late-TN aggregate.line", allow_empty=False)
    assert_function_store(aggregate["function"], "late-TN aggregate.function")
    assert_branch_store(aggregate["branch"], "late-TN aggregate.branch")
    assert_mcdc_store(aggregate["mcdc"], "late-TN aggregate.mcdc")
    require(aggregate["line"]["lines"] == {"1": 1}, "late-TN aggregate line ownership mismatch")
    require(aggregate["function"]["functions"]["1"]["aliases"] == {"f": 1}, "late-TN aggregate function mismatch")
    require(aggregate["branch"]["found"] == 1 and aggregate["branch"]["hit"] == 1, "late-TN aggregate branch counts mismatch")
    require(aggregate["mcdc"]["found"] == 2 and aggregate["mcdc"]["hit"] == 2, "late-TN aggregate MC/DC counts mismatch")
    require(
        aggregate["mcdc"]["lines"]["1"]["groups"]["1"][0]["true_count"] == 1
        and aggregate["mcdc"]["lines"]["1"]["groups"]["1"][0]["false_count"] == 1,
        "late-TN aggregate MC/DC both senses required",
    )
    testcases = source["testcases"]
    assert_four_family_maps(testcases, "late-TN testcases")
    require(set(testcases["line"]) == {"A"}, "late-TN line map must stay on A")
    require(set(testcases["function"]) == {"A"}, "late-TN function map must stay on A")
    require(set(testcases["branch"]) == {"A"}, "late-TN branch map must stay on A")
    require(set(testcases["mcdc"]) == {"A", "B"}, "late-TN MC/DC map must contain A and B")
    require(testcases["line"]["A"]["lines"] == {"1": 1}, "late-TN line A ownership mismatch")
    require(testcases["function"]["A"]["functions"]["1"]["aliases"] == {"f": 1}, "late-TN function A mismatch")
    require(testcases["branch"]["A"]["found"] == 1, "late-TN branch A missing")
    require(testcases["mcdc"]["A"]["lines"] == {}, "late-TN MC/DC A must be empty clone slot")
    require(testcases["mcdc"]["A"]["found"] == 0 and testcases["mcdc"]["A"]["hit"] == 0, "late-TN MC/DC A counters must be zero")
    require("1" in testcases["mcdc"]["B"]["lines"], "late-TN MC/DC B must own line1 clone")
    require(
        testcases["mcdc"]["B"]["lines"]["1"]["groups"]["1"][0]["true_count"] == 1
        and testcases["mcdc"]["B"]["lines"]["1"]["groups"]["1"][0]["false_count"] == 1,
        "late-TN MC/DC B clone must contain both senses",
    )
    # Exceptional cached-count/data divergence: close_mcdcBlock increments only the aggregate.
    require(
        testcases["mcdc"]["B"]["found"] == 0 and testcases["mcdc"]["B"]["hit"] == 0,
        "late-TN MC/DC B cached counters must remain zero despite line1 clone data",
    )


def validate_cross_sf_success_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "cross-SF snapshot kind mismatch")
    require(document.get("schema_version") == 1, "cross-SF snapshot schema mismatch")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 1, "cross-SF success must retain exactly one source")
    source = sources[0]
    require(source.get("filename") == "/m0/next.c", "cross-SF retained source must be next.c")
    aggregate = source["aggregate"]
    assert_count_store(aggregate["line"], "cross-SF aggregate.line", allow_empty=False)
    assert_function_store(aggregate["function"], "cross-SF aggregate.function")
    assert_branch_store(aggregate["branch"], "cross-SF aggregate.branch")
    assert_mcdc_store(aggregate["mcdc"], "cross-SF aggregate.mcdc")
    require(aggregate["line"]["lines"] == {"2": 1}, "cross-SF aggregate line must be DA2 only")
    require(set(aggregate["mcdc"]["lines"]) == {"2"}, "cross-SF aggregate MC/DC retains only line2 object")
    require(aggregate["mcdc"]["found"] == 4 and aggregate["mcdc"]["hit"] == 2, "cross-SF aggregate MC/DC cached counts include closed line1")
    testcases = source["testcases"]
    assert_four_family_maps(testcases, "cross-SF testcases")
    require(set(testcases["line"]) == {"B"}, "cross-SF line map must be B only")
    require(set(testcases["function"]) == {"B"}, "cross-SF function map must be B only")
    require(set(testcases["branch"]) == {"B"}, "cross-SF branch map must be B only")
    require(set(testcases["mcdc"]) == {"B"}, "cross-SF MC/DC map must be B only")
    require(testcases["line"]["B"]["lines"] == {"2": 1}, "cross-SF line B ownership mismatch")
    require(set(testcases["mcdc"]["B"]["lines"]) == {"1", "2"}, "cross-SF MC/DC B must contain line1 clone and line2")
    require(
        testcases["mcdc"]["B"]["lines"]["1"]["groups"]["1"][0]["expression"] == "first"
        and testcases["mcdc"]["B"]["lines"]["1"]["groups"]["1"][0]["true_count"] == 1,
        "cross-SF MC/DC B line1 clone mismatch",
    )
    require(
        testcases["mcdc"]["B"]["lines"]["2"]["groups"]["1"][0]["expression"] == "second"
        and testcases["mcdc"]["B"]["lines"]["2"]["groups"]["1"][0]["true_count"] == 1,
        "cross-SF MC/DC B line2 mismatch",
    )
    require(
        testcases["mcdc"]["B"]["found"] == 0 and testcases["mcdc"]["B"]["hit"] == 0,
        "cross-SF MC/DC B cached counters must remain zero despite line data",
    )



def validate_functions_current_core_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "function-core snapshot kind mismatch")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 1, "function-core must have one source")
    source = sources[0]
    require(source.get("filename") == "src/fn-current.c", "function-core filename mismatch")
    aggregate = source["aggregate"]
    assert_function_store(aggregate["function"], "function-core aggregate.function")
    functions = aggregate["function"]["functions"]
    require(set(functions) == {"10", "30", "50"}, "function-core start-line keys mismatch")
    require(functions["10"]["aliases"] == {"alpha": 4, "alpha_alias,with,commas": 2}, "function-core alias accumulation mismatch")
    require(functions["10"]["end"] == 20, "function-core alpha end mismatch")
    require(functions["30"]["aliases"] == {"beta": 0}, "function-core beta alias mismatch")
    require(functions["30"]["end"] == 40, "function-core beta end mismatch")
    require(functions["50"]["aliases"] == {"gamma": 1}, "function-core gamma alias mismatch")
    require(functions["50"]["end"] == 51, "function-core gamma optional end must be derived to last contiguous line")
    require(aggregate["function"]["found"] == 4, "function-core alias-level found mismatch")
    require(aggregate["function"]["hit"] == 3, "function-core alias-level hit mismatch")
    testcases = source["testcases"]
    require(set(testcases["function"]) == {"fn_current"}, "function-core testcase map mismatch")
    require(
        testcases["function"]["fn_current"]["functions"]["10"]["aliases"]
        == {"alpha": 4, "alpha_alias,with,commas": 2},
        "function-core testcase alias mismatch",
    )


def validate_functions_mixed_merge_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "mixed-merge snapshot kind mismatch")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 1, "mixed-merge must have one source")
    source = sources[0]
    require(source.get("filename") == "src/fn-mix.c", "mixed-merge filename mismatch")
    aggregate = source["aggregate"]
    assert_function_store(aggregate["function"], "mixed-merge aggregate.function")
    functions = aggregate["function"]["functions"]
    require(set(functions) == {"10"}, "mixed-merge must keep one start location")
    require(functions["10"]["aliases"] == {"alpha": 3, "alpha_alias": 3}, "mixed-merge alias accumulation mismatch")
    require(functions["10"]["end"] == 20, "mixed-merge end mismatch")
    require(functions["10"]["name"] == "alpha", "mixed-merge representative mismatch")
    require(aggregate["function"]["found"] == 2, "mixed-merge alias-level found mismatch")
    require(aggregate["function"]["hit"] == 2, "mixed-merge alias-level hit mismatch")
    testcases = source["testcases"]
    require(set(testcases["function"]) == {"fn_mix"}, "mixed-merge testcase map mismatch")
    require(
        testcases["function"]["fn_mix"]["functions"]["10"]["aliases"]
        == {"alpha": 3, "alpha_alias": 3},
        "mixed-merge testcase alias mismatch",
    )


def _branch_line_blocks(store: dict[str, object], line: str) -> list[dict[str, object]]:
    assert_branch_store(store, f"branch line {line}")
    lines = store["lines"]
    require(isinstance(lines, dict) and line in lines, f"branch line {line} missing")
    blocks = lines[line]["blocks"]
    require(isinstance(blocks, list), f"branch line {line} blocks must be list")
    return blocks


def validate_branches_forms_core_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "branch-forms snapshot kind mismatch")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 1, "branch-forms must have one source")
    source = sources[0]
    require(source.get("filename") == "src/br-forms.c", "branch-forms filename mismatch")
    aggregate = source["aggregate"]
    assert_branch_store(aggregate["branch"], "branch-forms aggregate.branch")
    require(aggregate["branch"]["found"] == 13 and aggregate["branch"]["hit"] == 7, "branch-forms found/hit mismatch")
    line10 = _branch_line_blocks(aggregate["branch"], "10")
    require(len(line10) == 1 and line10[0]["signature"] == "bb", "branch-forms line10 block mismatch")
    require(
        [element["expr"] for element in line10[0]["elements"]] == ["cond", "!cond"],
        "branch-forms vanilla expressions mismatch",
    )
    line20 = _branch_line_blocks(aggregate["branch"], "20")
    require(line20[0]["signature"] == "eb", "branch-forms exception signature mismatch")
    require(line20[0]["elements"][0]["type"] == "exception", "branch-forms exception type mismatch")
    line30 = _branch_line_blocks(aggregate["branch"], "30")
    require(line30[0]["signature"] == "fb", "branch-forms fallthrough signature mismatch")
    require(line30[0]["elements"][0]["type"] == "fallthrough", "branch-forms fallthrough type mismatch")
    line40 = _branch_line_blocks(aggregate["branch"], "40")
    require(line40[0]["elements"][0]["excluded"] is True, "branch-forms U exclusion missing")
    require(line40[0]["elements"][1]["excluded"] is False, "branch-forms non-U must not be excluded")
    line50 = _branch_line_blocks(aggregate["branch"], "50")
    require(line50[0]["elements"][0]["taken"] == "-", "branch-forms dash taken missing")
    require(line50[0]["elements"][0]["count"] == 0, "branch-forms dash count must be zero")
    line60 = _branch_line_blocks(aggregate["branch"], "60")
    require(line60[0]["elements"][0]["expr"] == "a,b,c", "branch-forms comma expression mismatch")
    require(line60[0]["elements"][0]["taken"] == 2, "branch-forms comma expression taken mismatch")
    line70 = _branch_line_blocks(aggregate["branch"], "70")
    require(
        [element["expr"] for element in line70[0]["elements"]] == [None, None],
        "branch-forms numeric expression identity must collapse to null expr",
    )
    require(
        [element["id"] for element in line70[0]["elements"]] == [0, 1],
        "branch-forms numeric expression branch indices mismatch",
    )
    testcases = source["testcases"]
    require(set(testcases["branch"]) == {"br_forms"}, "branch-forms testcase map mismatch")


def validate_branches_noncontiguous_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "branch-noncont snapshot kind mismatch")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 1, "branch-noncont must have one source")
    source = sources[0]
    require(source.get("filename") == "src/br-noncont.c", "branch-noncont filename mismatch")
    aggregate = source["aggregate"]
    assert_branch_store(aggregate["branch"], "branch-noncont aggregate.branch")
    require(aggregate["branch"]["found"] == 6 and aggregate["branch"]["hit"] == 3, "branch-noncont found/hit mismatch")
    line10 = _branch_line_blocks(aggregate["branch"], "10")
    require(len(line10) == 2, "branch-noncont line10 must keep two positional blocks")
    require(
        [element["expr"] for element in line10[0]["elements"]] == ["a", "b"],
        "branch-noncont first block expressions mismatch",
    )
    require(
        [element["expr"] for element in line10[1]["elements"]] == ["e", "f"],
        "branch-noncont second block expressions mismatch",
    )
    require(line10[0]["idx"] == 0 and line10[1]["idx"] == 1, "branch-noncont block indices mismatch")
    line20 = _branch_line_blocks(aggregate["branch"], "20")
    require(len(line20) == 1, "branch-noncont line20 must have one block")
    require(
        [element["expr"] for element in line20[0]["elements"]] == ["c", "d"],
        "branch-noncont line20 expressions mismatch",
    )


def validate_branches_expression_merge_snapshot(document: dict[str, object]) -> None:
    require(document.get("kind") == "semantic_model_snapshot", "branch-expression-merge snapshot kind mismatch")
    require(document.get("inputs") == ["input.info", "right.info"], "branch-expression-merge inputs mismatch")
    sources = document.get("sources")
    require(isinstance(sources, list) and len(sources) == 1, "branch-expression-merge must have one source")
    source = sources[0]
    require(source.get("filename") == "src/br-expression-merge.c", "branch-expression-merge filename mismatch")
    aggregate = source.get("aggregate")
    require(isinstance(aggregate, dict), "branch-expression-merge aggregate missing")
    assert_count_store(aggregate["line"], "branch-expression-merge aggregate.line", allow_empty=False)
    require(
        aggregate["line"]["found"] == 1
        and aggregate["line"]["hit"] == 1
        and aggregate["line"]["lines"] == {"10": 3},
        "branch-expression-merge aggregate line cache mismatch",
    )
    assert_branch_store(aggregate["branch"], "branch-expression-merge aggregate.branch")
    require(
        aggregate["branch"]["found"] == 2 and aggregate["branch"]["hit"] == 1,
        "branch-expression-merge cached totals mismatch",
    )
    line10 = _branch_line_blocks(aggregate["branch"], "10")
    require(len(line10) == 1 and line10[0]["signature"] == "bb", "branch-expression-merge block mismatch")
    elements = line10[0]["elements"]
    require([element["id"] for element in elements] == [0, 1], "branch-expression-merge edge indices mismatch")
    require(
        [element["expr"] for element in elements] == ["left", "left_else"],
        "branch-expression-merge must retain left expressions",
    )
    require(
        [element["count"] for element in elements] == [3, 3],
        "branch-expression-merge counts must add positionally",
    )
    testcases = source.get("testcases")
    require(isinstance(testcases, dict), "branch-expression-merge testcase maps missing")
    require(set(testcases["line"]) == {"br_expression_merge"}, "branch-expression-merge testcase line map mismatch")
    testcase_line = testcases["line"]["br_expression_merge"]
    assert_count_store(testcase_line, "branch-expression-merge testcase.line", allow_empty=False)
    require(
        testcase_line["found"] == 1
        and testcase_line["hit"] == 1
        and testcase_line["lines"] == {"10": 3},
        "branch-expression-merge testcase line cache mismatch",
    )
    require(set(testcases["branch"]) == {"br_expression_merge"}, "branch-expression-merge testcase branch map mismatch")
    testcase = testcases["branch"]["br_expression_merge"]
    assert_branch_store(testcase, "branch-expression-merge testcase.branch")
    require(
        testcase["found"] == 2 and testcase["hit"] == 1,
        "branch-expression-merge testcase branch cache mismatch",
    )
    testcase_elements = _branch_line_blocks(testcase, "10")[0]["elements"]
    require(
        [element["expr"] for element in testcase_elements] == ["left", "left_else"]
        and [element["count"] for element in testcase_elements] == [3, 3],
        "branch-expression-merge testcase positional merge mismatch",
    )



def validate_semantic_snapshot_observation(case: dict[str, object], observation: dict[str, object]) -> None:
    require(case.get("runner") == MODEL_INSPECTOR_NAME, f"{case['id']}: runner must be inspect_model.pl")
    require(observation.get("runner") == MODEL_INSPECTOR_NAME, f"{case['id']}: baseline runner missing")
    require(case["argv"][:2] == ["perl", MODEL_INSPECTOR_NAME], f"{case['id']}: inspector argv drift")
    require(observation["exit_status"] == 0, f"{case['id']}: semantic snapshot must exit 0")
    raw = decode_identity(observation["stdout"], f"{case['id']} stdout")
    stderr_bytes = decode_identity(observation["stderr"], f"{case['id']} stderr")
    validate_semantic_stderr(case["id"], stderr_bytes)
    document = strict_json_loads_ascii(raw, f"{case['id']} semantic snapshot stdout")
    validate_semantic_input_identity(case, document)
    text = raw.decode("ascii")
    require(raw.endswith(b"\n"), f"{case['id']}: snapshot JSON must end with newline")
    require("\t" not in text, f"{case['id']}: snapshot JSON must not contain tabs")
    require(document.get("oracle", {}).get("module") == "/usr/local/lib/lcov/lcovutil.pm", f"{case['id']}: module identity drift")
    require(document.get("oracle", {}).get("program") == "/usr/local/bin/lcov", f"{case['id']}: program identity drift")
    if case["id"] == "state-late-tn-mcdc.semantic-snapshot":
        validate_late_tn_snapshot(document)
    elif case["id"] == "state-cross-sf-mcdc-success.semantic-snapshot":
        validate_cross_sf_success_snapshot(document)
    elif case["id"] == "functions-current-core.semantic-snapshot":
        validate_functions_current_core_snapshot(document)
    elif case["id"] == "functions-mixed-merge.semantic-snapshot":
        validate_functions_mixed_merge_snapshot(document)
    elif case["id"] == "branches-forms-core.semantic-snapshot":
        validate_branches_forms_core_snapshot(document)
    elif case["id"] == "branches-noncontiguous.semantic-snapshot":
        validate_branches_noncontiguous_snapshot(document)
    elif case["id"] == "branches-expression-merge.semantic-snapshot":
        validate_branches_expression_merge_snapshot(document)
    elif case["id"] == "numeric-boundary.semantic-snapshot":
        validate_numeric_boundary_snapshot(document)
    elif case["id"] == "numeric-extra-spellings.semantic-snapshot":
        validate_numeric_extra_spellings_snapshot(document)
    elif case["id"] == "numeric-format-atoms.ignore-format-negative.semantic-snapshot":
        validate_numeric_format_atoms_snapshot(document, with_excessive_threshold=False)
    elif case["id"] == "numeric-format-atoms.ignore-format-negative-excessive.semantic-snapshot":
        validate_numeric_format_atoms_snapshot(document, with_excessive_threshold=True)
    elif case["id"] == "numeric-signed-zero.semantic-snapshot":
        validate_numeric_signed_zero_snapshot(document)
    elif case["id"] == "numeric-negative-inf.semantic-snapshot":
        validate_numeric_negative_inf_snapshot(document)
    elif case["id"] == "numeric-fna-nonnumeric.semantic-snapshot":
        validate_numeric_fna_nonnumeric_snapshot(document)
    elif case["id"] == "numeric-zero-fn-end.semantic-snapshot":
        validate_numeric_zero_fn_end_snapshot(document)
    elif case["id"] == "numeric-invalid-fnl-fields.semantic-snapshot":
        validate_numeric_invalid_fnl_fields_snapshot(document)
    elif case["id"] == "functions-zero-start.semantic-snapshot":
        validate_functions_zero_start_snapshot(document)
    elif case["id"] == "numeric-format-atoms.tf030.semantic-snapshot":
        validate_tf030_numeric_rows(document, expected_count=12, case_id=case["id"])
    elif case["id"] == "numeric-format-atoms.tf030-threshold.semantic-snapshot":
        validate_tf030_numeric_rows(document, expected_count=12, case_id=case["id"])
    elif case["id"] == "numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot":
        validate_tf030_numeric_rows(document, expected_count=4, case_id=case["id"])
    elif case["id"] == "numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot":
        validate_tf030_numeric_rows(document, expected_count=4, case_id=case["id"])
    elif case["id"] == "numeric-tf030-candidates.ignore-negative.semantic-snapshot":
        validate_tf030_numeric_rows(document, expected_count=40, case_id=case["id"])
    elif case["id"] == "numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot":
        validate_tf030_numeric_rows(document, expected_count=40, case_id=case["id"])
    else:
        raise ValueError(f"unexpected semantic snapshot case: {case['id']}")


def validate_observation_binding(
    case: dict[str, object],
    observation: dict[str, object],
    fixtures: dict[str, generate.Fixture],
) -> None:
    """Validate identity and side-effect bindings shared by every Oracle case."""
    label = str(case["id"])
    require(observation["fixture"] == case["fixture"], f"fixture mismatch: {label}")
    require(
        observation.get("fixture_sha256") == hashlib.sha256(fixtures[case["fixture"]].data).hexdigest(),
        f"fixture byte identity mismatch: {label}",
    )
    require(
        observation.get("additional_fixtures", {}) == case.get("additional_fixtures", {}),
        f"additional fixture mismatch: {label}",
    )
    expected_additional_hashes = {
        name: hashlib.sha256(fixtures[path].data).hexdigest()
        for name, path in case.get("additional_fixtures", {}).items()
    }
    require(
        observation.get("additional_fixture_sha256", {}) == expected_additional_hashes,
        f"additional fixture byte identity mismatch: {label}",
    )
    require(observation["argv"] == case["argv"], f"argv mismatch: {label}")
    require(observation["exit_status"] == case["expected_exit"], f"unexpected exit status: {label}")
    verify_identity(observation["stdout"], f"{label} stdout")
    verify_identity(observation["stderr"], f"{label} stderr")
    output = observation["output"]
    expected_output_exists = case.get("expected_output_exists")
    if expected_output_exists is not None:
        require(isinstance(expected_output_exists, bool), f"{label}: expected_output_exists must be boolean")
        require(output.get("exists") is expected_output_exists, f"{label}: output existence drift")
    if output["exists"]:
        verify_identity(output, f"{label} output")
        require(observation["output_file"] == case.get("output_file"), f"output path mismatch: {label}")
    else:
        require(observation["output_file"] == case.get("output_file"), f"missing output declaration: {label}")
        require(case.get("output_file") is None or output["exists"] is False, f"missing output bytes: {label}")


def validate_baseline(manifest: dict[str, object], fixtures: dict[str, generate.Fixture]) -> None:
    cases_path = ROOT / "oracle-cases.json"
    baseline_path = ROOT / "oracle-baseline.json"
    cases_document = strict_json_file(cases_path, "oracle-cases.json")
    expected_cases = generate.build_oracle_cases(generate.build_fixtures())
    require(cases_document == expected_cases, "oracle-cases.json is not the exact generator result")
    baseline = strict_json_file(baseline_path, "oracle-baseline.json")
    require(cases_document["schema_version"] == 1, "unsupported oracle-cases schema")
    require(baseline["schema_version"] == 1, "unsupported Oracle baseline schema")

    cases = cases_document["cases"]
    case_ids = [case["id"] for case in cases]
    require(len(case_ids) == len(set(case_ids)), "duplicate Oracle case IDs")
    require(MODEL_INSPECTOR.is_file(), "model inspector must be committed")
    for case in cases:
        require(case["fixture"] in fixtures, f"Oracle case references unknown fixture: {case['id']}")
        additional_fixtures = case.get("additional_fixtures", {})
        require(isinstance(additional_fixtures, dict), f"invalid additional_fixtures: {case['id']}")
        for name, fixture in additional_fixtures.items():
            require(name == Path(name).name, f"unsafe additional fixture name: {case['id']}")
            require(name not in {"input.info", MODEL_INSPECTOR_NAME}, f"reserved additional fixture name: {case['id']}")
            require(fixture in fixtures, f"Oracle case references unknown additional fixture: {case['id']}")
        require(case["argv"] and case["argv"][0] in ALLOWED_ARGV_HEADS, f"invalid Oracle argv head: {case['id']}")
        require(isinstance(case["expected_exit"], int), f"missing expected_exit: {case['id']}")
        output_file = case.get("output_file")
        if output_file is not None:
            require(output_file == Path(output_file).name, f"unsafe output_file: {case['id']}")
        if "expected_output_exists" in case:
            require(
                isinstance(case["expected_output_exists"], bool),
                f"expected_output_exists must be boolean: {case['id']}",
            )
            require(output_file is not None, f"expected_output_exists requires output_file: {case['id']}")
        runner = case.get("runner")
        if runner is not None:
            require(runner == MODEL_INSPECTOR_NAME, f"unsupported runner: {case['id']}")
            require(case["argv"][0] == "perl", f"inspector runner must use perl: {case['id']}")
            require(MODEL_INSPECTOR_NAME in case["argv"], f"inspector argv missing script: {case['id']}")
        else:
            require(case["argv"][0] == "lcov", f"default runner must use lcov: {case['id']}")
        # Fail closed against product evidence promotion fields.
        require(case.get("evidence_status") in (None, "oracle_reference"), f"product evidence claim: {case['id']}")
        require("product_compatibility" not in case, f"product compatibility claim: {case['id']}")

        if case["id"].startswith("checksum-") and case["id"] != "checksum-no-verify.canonical":
            require(
                case.get("additional_fixtures") == {"cs.c": "fixtures/numeric/cs.c"},
                f"checksum companion binding drift: {case['id']}",
            )
        if case["id"] == "checksum-no-verify.canonical":
            require(not case.get("additional_fixtures"), "checksum-no-verify must not bind a companion source")
        if case["id"].startswith("numeric-function-excessive."):
            require(
                case.get("additional_fixtures") == {"function-excessive.c": "fixtures/numeric/function-excessive.c"},
                f"function excessive companion binding drift: {case['id']}",
            )

    expected_oracle = manifest["provenance"]["oracle"]
    for key in ("source_commit", "docker_image", "docker_image_id", "program", "program_sha256", "perl_version"):
        require(baseline["oracle"][key] == expected_oracle[key], f"baseline Oracle {key} mismatch")
    require(baseline["oracle"]["network"] == "none", "Oracle baseline must disable network")
    require(baseline["cases_sha256"] == hashlib.sha256(cases_path.read_bytes()).hexdigest(), "oracle-cases hash mismatch")
    require(
        baseline.get("manifest_sha256")
        == hashlib.sha256((ROOT / "manifest.json").read_bytes()).hexdigest(),
        "Oracle baseline manifest hash mismatch",
    )

    observations = baseline["cases"]
    observed_by_id = {observation["id"]: observation for observation in observations}
    require(len(observed_by_id) == len(observations), "duplicate baseline case IDs")
    require(set(observed_by_id) == set(case_ids), "baseline case set differs from oracle-cases")
    require(case_ids == [observation["id"] for observation in observations], "baseline case order differs from oracle-cases")

    for case in cases:
        observation = observed_by_id[case["id"]]
        validate_observation_binding(case, observation, fixtures)
        validate_added_numeric_case(case, observation)

        if case["id"] in SEMANTIC_SNAPSHOT_CASE_IDS:
            validate_semantic_snapshot_observation(case, observation)
        if case["id"] == "state-cross-sf-mcdc-duplicate.summary":
            require(observation["exit_status"] == 1, "duplicate case must exit 1")
            stderr = decode_identity(observation["stderr"], "duplicate stderr").decode("utf-8", "replace")
            require("MCDC already defined for 1" in stderr, "duplicate diagnostic identity missing")
        if case["id"] == "state-late-tn-mcdc.canonical":
            output_bytes = decode_identity(observation["output"], "late-TN canonical output")
            require(b"TN:A\n" in output_bytes and b"TN:B\n" not in output_bytes, "late-TN writer must enumerate A only")
            require(b"MCDC:" not in output_bytes, "late-TN writer omits B MC/DC entirely when enumerating A")
            require(
                observation["output"]["sha256"]
                == "6af975d55989695523fce76a562cf0dc8d4513234929e610b7a7d131f317237e",
                "late-TN canonical output hash drift",
            )
        if case["id"] == "state-cross-sf-mcdc-success.canonical":
            output_bytes = decode_identity(observation["output"], "cross-SF canonical output")
            require(b"TN:B\n" in output_bytes and b"SF:/m0/next.c\n" in output_bytes, "cross-SF canonical source/test mismatch")
            require(b"SF:/m0/first.c\n" not in output_bytes, "cross-SF first source must be filtered from output")
            require(b"MCDC:1,1,t,1,0,first\n" in output_bytes and b"MCDC:2,1,t,1,0,second\n" in output_bytes, "cross-SF output MC/DC mismatch")
            require(
                observation["output"]["sha256"]
                == "0fc19d686b099477165a80ff9909acc9f1a9480fd1441830f6434c20ceac3b95",
                "cross-SF canonical output hash drift",
            )

        if case["id"] == "ver-repeat-different.summary":
            stderr = decode_identity(observation["stderr"], "different VER stderr").decode("utf-8", "replace")
            require(
                "expected to set version ID at most once" in stderr,
                "different VER must retain the fatal version diagnostic",
            )
        if case["id"] == "ver-per-source.summary":
            stdout = decode_identity(observation["stdout"], "per-source VER stdout")
            require(b"source files: 2" in stdout, "per-source VER must retain both source records")
        if case["id"] == "ver-repeat-equal.canonical":
            output_bytes = decode_identity(observation["output"], "repeat-equal canonical output")
            require(output_bytes.count(b"VER:") == 1, "canonical repeat-equal output must emit one VER")

        if case["id"] == "functions-current-core.canonical":
            output_bytes = decode_identity(observation["output"], "function-core canonical output")
            require(b"FNA:0,4,alpha\n" in output_bytes, "function-core must accumulate repeated alias counts")
            require(b"FNA:0,2,alpha_alias,with,commas\n" in output_bytes, "function-core must retain comma alias text")
            require(b"FNL:1,30,40\n" in output_bytes, "function-core must renumber noncontiguous indices")
            require(b"FNL:2,50,51\n" in output_bytes, "function-core must derive optional end line in writer")
            require(b"FNL:5," not in output_bytes and b"FNL:7," not in output_bytes, "function-core must not preserve input indices")
        if case["id"] == "functions-zero-end.canonical":
            output_bytes = decode_identity(observation["output"], "zero-end canonical output")
            require(b"FNL:0,5,0\n" in output_bytes, "zero-end must retain end line zero")
            require(b"FNA:0,0,zero_end\n" in output_bytes, "zero-end alias must remain zero")
        if case["id"] == "functions-mixed-merge.canonical":
            output_bytes = decode_identity(observation["output"], "mixed-merge canonical output")
            require(b"FN:" not in output_bytes and b"FNDA:" not in output_bytes, "mixed-merge must rewrite to FNL/FNA only")
            require(b"FNA:0,3,alpha\n" in output_bytes, "mixed-merge alpha count mismatch")
            require(b"FNA:0,3,alpha_alias\n" in output_bytes, "mixed-merge alpha_alias count mismatch")
        if case["id"] == "functions-index-scope-reset.canonical":
            output_bytes = decode_identity(observation["output"], "index-scope-reset canonical output")
            require(b"SF:src/fn-scope-a.c\n" in output_bytes and b"SF:src/fn-scope-b.c\n" in output_bytes, "scope-reset sources missing")
            require(output_bytes.count(b"FNL:0,") == 2, "scope-reset must allow index reuse across SF sections")
        if case["id"] == "functions-current-missing-alias.summary":
            stderr = decode_identity(observation["stderr"], "missing-alias stderr").decode("utf-8", "replace")
            require("unexpected .info file record 'FNA:0,1'" in stderr, "missing-alias diagnostic drift")
        if case["id"] == "functions-zero-start.summary":
            stderr = decode_identity(observation["stderr"], "zero-start stderr").decode("utf-8", "replace")
            require("function 'zero_start' is not hit but line 1 is" in stderr, "zero-start consistency diagnostic drift")
        if case["id"] == "functions-mixed-location-mismatch.summary":
            stderr = decode_identity(observation["stderr"], "mixed-location stderr").decode("utf-8", "replace")
            require("duplicate function 'alpha'" in stderr, "mixed-location diagnostic drift")
            require(observation["output"]["exists"] is False, "mixed-location summary must not create output")
        if case["id"] == "functions-mixed-location-mismatch.canonical":
            require(observation["output"]["exists"] is False, "mixed-location write failure must leave output absent")
            stderr = decode_identity(observation["stderr"], "mixed-location write stderr").decode("utf-8", "replace")
            require("duplicate function 'alpha'" in stderr, "mixed-location write diagnostic drift")
        if case["id"] == "functions-mixed-range-mismatch.summary":
            stderr = decode_identity(observation["stderr"], "mixed-range stderr").decode("utf-8", "replace")
            require("mismatched end line for alpha" in stderr, "mixed-range diagnostic drift")
        if case["id"] == "functions-mixed-range-mismatch.canonical":
            require(observation["output"]["exists"] is False, "mixed-range write failure must leave output absent")
            stderr = decode_identity(observation["stderr"], "mixed-range write stderr").decode("utf-8", "replace")
            require("mismatched end line for alpha" in stderr, "mixed-range write diagnostic drift")
        if case["id"] == "functions-index-duplicate.summary":
            stderr = decode_identity(observation["stderr"], "index-duplicate stderr").decode("utf-8", "replace")
            require("unexpected duplicate index 0" in stderr, "index-duplicate diagnostic drift")
        if case["id"] == "functions-index-duplicate.canonical":
            require(observation["output"]["exists"] is False, "index-duplicate write failure must leave output absent")
            stderr = decode_identity(observation["stderr"], "index-duplicate write stderr").decode("utf-8", "replace")
            require("unexpected duplicate index 0" in stderr, "index-duplicate write diagnostic drift")
        if case["id"] == "functions-index-unknown.summary":
            stderr = decode_identity(observation["stderr"], "index-unknown stderr").decode("utf-8", "replace")
            require("unknown index 9" in stderr, "index-unknown diagnostic drift")
        if case["id"] == "functions-index-unknown.canonical":
            require(observation["output"]["exists"] is False, "index-unknown write failure must leave output absent")
            stderr = decode_identity(observation["stderr"], "index-unknown write stderr").decode("utf-8", "replace")
            require("unknown index 9" in stderr, "index-unknown write diagnostic drift")
        if case["id"] == "functions-index-tn-preserves.summary":
            stderr = decode_identity(observation["stderr"], "index-tn-preserves stderr").decode("utf-8", "replace")
            require("unexpected duplicate index 0" in stderr, "index-tn-preserves diagnostic drift")

        if case["id"] == "branches-forms-core.canonical":
            output_bytes = decode_identity(observation["output"], "branch-forms canonical output")
            require(b"BRDA:20,e0,exception,0\n" in output_bytes, "branch-forms exception rewrite missing")
            require(b"BRDA:30,f0,fall,1\n" in output_bytes, "branch-forms fallthrough rewrite missing")
            require(b"BRDA:40,U0,unreach,0\n" in output_bytes, "branch-forms U exclusion rewrite missing")
            require(b"BRDA:50,0,never,-\n" in output_bytes, "branch-forms dash taken rewrite missing")
            require(b"BRDA:60,0,a,b,c,2\n" in output_bytes, "branch-forms comma expression rewrite missing")
            require(b"BRDA:70,0,0,1\n" in output_bytes and b"BRDA:70,0,1,0\n" in output_bytes, "branch-forms numeric identity rewrite missing")
            require(b"BRF:13\n" in output_bytes and b"BRH:7\n" in output_bytes, "branch-forms BRF/BRH exclude U")
        if case["id"] == "branches-u-modes.canonical":
            output_bytes = decode_identity(observation["output"], "branch-u-modes default output")
            require(b"BRDA:10,U0,unreach,0\n" in output_bytes, "branch-u-modes default U missing")
            require(b"BRDA:20,fU0,x > 0,0\n" in output_bytes, "branch-u-modes default fU missing")
            require(b"BRDA:30,eU0,exc,0\n" in output_bytes, "branch-u-modes default eU missing")
            require(b"BRF:3\n" in output_bytes and b"BRH:3\n" in output_bytes, "branch-u-modes default BRF/BRH mismatch")
        if case["id"] == "branches-u-modes.clear-unreachable":
            output_bytes = decode_identity(observation["output"], "branch-u-modes ignore-unreachable output")
            require(b"BRDA:10,0,unreach,0\n" in output_bytes, "ignore-unreachable must clear plain U")
            require(b"BRDA:20,f0,x > 0,0\n" in output_bytes, "ignore-unreachable must clear fU")
            require(b"BRDA:30,e0,exc,0\n" in output_bytes, "ignore-unreachable must clear eU")
            require(b"U0," not in output_bytes and b"fU" not in output_bytes and b"eU" not in output_bytes, "ignore-unreachable residual U mark")
            require(b"BRF:6\n" in output_bytes and b"BRH:3\n" in output_bytes, "ignore-unreachable BRF/BRH mismatch")
        if case["id"] == "branches-malformed-tail.summary":
            stderr = decode_identity(observation["stderr"], "branch-malformed-tail summary stderr").decode("utf-8", "replace")
            require("Unexpected non-integer taken count 'expr'" in stderr, "branch-malformed-tail diagnostic drift")
            require(observation["output"]["exists"] is False, "branch-malformed-tail summary must not create output")
        if case["id"] == "branches-malformed-tail.canonical":
            require(observation["output"]["exists"] is False, "branch-malformed-tail write failure must leave output absent")
            stderr = decode_identity(observation["stderr"], "branch-malformed-tail write stderr").decode("utf-8", "replace")
            require("Unexpected non-integer taken count 'expr'" in stderr, "branch-malformed-tail write diagnostic drift")
        if case["id"] == "branches-malformed-tail-empty-taken.summary":
            stderr = decode_identity(
                observation["stderr"], "branch-malformed-tail empty-taken summary stderr"
            ).decode("utf-8", "replace")
            require(
                "Unexpected non-integer taken count ''" in stderr,
                "branch-malformed-tail empty-taken diagnostic drift",
            )
            require(
                observation["output"]["exists"] is False,
                "branch-malformed-tail empty-taken summary must not create output",
            )
        if case["id"] == "branches-malformed-tail-empty-taken.canonical":
            require(
                observation["output"]["exists"] is False,
                "branch-malformed-tail empty-taken write failure must leave output absent",
            )
            stderr = decode_identity(
                observation["stderr"], "branch-malformed-tail empty-taken write stderr"
            ).decode("utf-8", "replace")
            require(
                "Unexpected non-integer taken count ''" in stderr,
                "branch-malformed-tail empty-taken write diagnostic drift",
            )
        if case["id"] == "branches-malformed-tail-empty-expression.canonical":
            output_bytes = decode_identity(
                observation["output"], "branch-malformed-tail empty-expression output"
            )
            require(
                b"BRDA:1,0,,1\n" in output_bytes,
                "branch-malformed-tail empty expression must be retained",
            )
            require(
                b"BRF:1\n" in output_bytes and b"BRH:1\n" in output_bytes,
                "branch-malformed-tail empty expression totals mismatch",
            )
        if case["id"] == "branches-malformed-tail-empty-expression.summary":
            stdout = decode_identity(
                observation["stdout"], "branch-malformed-tail empty-expression summary stdout"
            )
            stderr = decode_identity(
                observation["stderr"], "branch-malformed-tail empty-expression summary stderr"
            )
            require(b"branches....: 100.0% (1 of 1 branch)" in stdout, "empty expression summary coverage mismatch")
            require(stderr == b"", "empty expression summary must not emit diagnostics")
        if case["id"] == "branches-expression-mismatch.summary":
            stdout = decode_identity(
                observation["stdout"], "branch-expression-mismatch summary stdout"
            )
            stderr = decode_identity(
                observation["stderr"], "branch-expression-mismatch summary stderr"
            )
            require(b"branches....: 50.0% (1 of 2 branches)" in stdout, "expression mismatch summary coverage mismatch")
            require(stderr == b"", "expression mismatch summary must not emit diagnostics")
        if case["id"] == "branches-expression-mismatch.canonical":
            output_bytes = decode_identity(
                observation["output"], "branch-expression-mismatch canonical output"
            )
            require(
                b"BRDA:10,0,first,1\nBRDA:10,0,second,0\n" in output_bytes,
                "branch positional expression order mismatch",
            )
            require(
                b"BRF:2\n" in output_bytes and b"BRH:1\n" in output_bytes,
                "branch expression mismatch totals mismatch",
            )
        if case["id"] == "branches-expression-merge.canonical":
            output_bytes = decode_identity(
                observation["output"], "branch-expression-merge canonical output"
            )
            require(
                b"BRDA:10,0,left,3\nBRDA:10,0,left_else,3\n" in output_bytes,
                "branch expression merge must retain left expressions and add counts",
            )
            require(
                b"right" not in output_bytes,
                "branch expression merge must not retain right expressions",
            )
            require(
                b"BRF:2\n" in output_bytes and b"BRH:2\n" in output_bytes,
                "branch expression merge writer totals mismatch",
            )
            require(
                b"branches....: 50.0% (1 of 2 branches)" in decode_identity(
                    observation["stdout"], "branch-expression-merge canonical stdout"
                ),
                "branch expression merge cached summary mismatch",
            )
        if case["id"] == "branches-order-gaps.canonical":
            output_bytes = decode_identity(observation["output"], "branch-order-gaps canonical output")
            require(b"BRDA:10,0,a,1\n" in output_bytes and b"BRDA:10,0,b,0\n" in output_bytes, "order-gaps first renumbered block missing")
            require(b"BRDA:10,1,c,1\n" in output_bytes and b"BRDA:10,1,d,0\n" in output_bytes, "order-gaps second renumbered block missing")
            require(b"BRDA:10,2,e,1\n" in output_bytes and b"BRDA:10,2,f,0\n" in output_bytes, "order-gaps third renumbered block missing")
            require(b"BRDA:10,5," not in output_bytes and b"BRDA:10,9," not in output_bytes, "order-gaps must not preserve input block IDs")
        if case["id"] == "branches-noncontiguous.canonical":
            output_bytes = decode_identity(observation["output"], "branch-noncont canonical output")
            require(b"BRDA:10,0,a,1\n" in output_bytes and b"BRDA:10,0,b,0\n" in output_bytes, "noncont first block missing")
            require(b"BRDA:10,1,e,1\n" in output_bytes and b"BRDA:10,1,f,0\n" in output_bytes, "noncont second positional block missing")
            require(b"BRDA:20,0,c,1\n" in output_bytes and b"BRDA:20,0,d,0\n" in output_bytes, "noncont line20 block missing")
        if case["id"] == "branches-interleave.canonical":
            output_bytes = decode_identity(observation["output"], "branch-interleave canonical output")
            require(b"BRDA:10,0,a,1\n" in output_bytes, "interleave first element missing")
            require(b"BRDA:10,1,c,1\n" in output_bytes, "interleave second element missing")
            require(b"BRDA:10,2,b,0\n" in output_bytes, "interleave third positional element missing")
            require(b"BRDA:10,3,d,0\n" in output_bytes, "interleave fourth positional element missing")
            require(b"BRF:4\n" in output_bytes, "interleave BRF mismatch")
        if case["id"] == "branches-sort-signatures.canonical":
            output_bytes = decode_identity(observation["output"], "branch-sort canonical output")
            require(
                output_bytes.index(b"BRDA:10,e0,e0,1\n")
                < output_bytes.index(b"BRDA:10,1,b0,1\n")
                < output_bytes.index(b"BRDA:10,f2,f0,1\n")
                < output_bytes.index(b"BRDA:10,3,a0,1\n"),
                "branch-sort signature order mismatch",
            )
            require(b"BRDA:10,e2," not in output_bytes and b"BRDA:10,f3," not in output_bytes, "branch-sort must renumber input block IDs")


        # Numeric / checksum / error-policy invariants (M1-TF-030..036).
        if case["id"] == "numeric-boundary.summary":
            stdout = decode_identity(observation["stdout"], "numeric-boundary summary stdout")
            require(b"source files: 15" in stdout, "numeric-boundary must summarize all accepted lexeme sources")
            require(observation["exit_status"] == 0, "numeric-boundary default must accept")
        if case["id"] == "numeric-boundary.canonical":
            output_bytes = decode_identity(observation["output"], "numeric-boundary canonical output")
            require(output_bytes.count(b"end_of_record") == 15, "numeric-boundary canonical record count drift")
            require(b"DA:1,NaN\n" in output_bytes or b"DA:1,nan\n" in output_bytes, "numeric-boundary must retain NaN spellings")
            require(b"DA:1,Inf\n" in output_bytes or b"DA:1,+Inf\n" in output_bytes or b"DA:1,Infinity\n" in output_bytes, "numeric-boundary must retain Inf spellings")
        if case["id"] == "numeric-extra-spellings.summary":
            stdout = decode_identity(observation["stdout"], "extra-spellings summary stdout")
            require(b"source files: 3" in stdout, "extra-spellings must summarize three sources")
            require(observation["exit_status"] == 0, "extra-spellings default must accept")
        if case["id"] == "numeric-extra-spellings.canonical":
            output_bytes = decode_identity(observation["output"], "extra-spellings canonical output")
            require(output_bytes.count(b"end_of_record") == 3, "extra-spellings canonical record count drift")
            require(b"DA:1,+1\n" in output_bytes, "extra-spellings must retain +1")
            require(b"DA:1,nan\n" in output_bytes, "extra-spellings must retain nan")
            require(b"DA:1,+Inf\n" in output_bytes, "extra-spellings must retain +Inf")
        if case["id"] == "numeric-format-atoms.summary":
            stderr = decode_identity(observation["stderr"], "format-atoms summary stderr").decode("utf-8", "replace")
            require("Unexpected negative hit count '-3'" in stderr, "format-atoms default must hit ERROR_NEGATIVE")
            require(observation["exit_status"] == 1, "format-atoms default summary must exit 1")
        if case["id"] == "numeric-format-atoms.default-stop":
            require(observation["output"]["exists"] is False, "default-stop must leave output absent")
            stderr = decode_identity(observation["stderr"], "format-atoms default-stop stderr").decode("utf-8", "replace")
            require("Unexpected negative hit count '-3'" in stderr, "default-stop must surface ERROR_NEGATIVE")
            require("Unexpected non-integer hit count" not in stderr, "default-stop must not continue into ERROR_FORMAT")
        if case["id"] == "numeric-format-atoms.ignore-negative":
            require(observation["output"]["exists"] is False, "ignore-negative-only must still stop without output")
            stderr = decode_identity(observation["stderr"], "format-atoms ignore-negative stderr").decode("utf-8", "replace")
            require("Unexpected non-integer hit count" in stderr, "ignore-negative must continue into ERROR_FORMAT")
        if case["id"] == "numeric-format-atoms.ignore-format-negative.canonical":
            output_bytes = decode_identity(observation["output"], "format-atoms ignore-format-negative output")
            require(b"DA:4,0\n" in output_bytes, "negative DA must coerce to zero")
            require(b"DA:10,0\n" in output_bytes, "malformed exponent DA must coerce to zero")
            require(b"DA:12,1.0e+19\n" in output_bytes, "excessive DA must be retained without threshold")
            require(b"BRDA:1,1,1,1.67e+20\n" in output_bytes, "excessive BRDA must be retained")
            require(observation["exit_status"] == 0, "ignore format+negative without threshold must exit 0")
        if case["id"] == "numeric-format-atoms.excessive-default-stop":
            require(observation["output"]["exists"] is False, "excessive default-stop must leave output absent")
            stderr = decode_identity(observation["stderr"], "format-atoms excessive-default-stop stderr").decode("utf-8", "replace")
            require("excessive" in stderr.lower() or "Excessive" in stderr, "excessive-default-stop must surface ERROR_EXCESSIVE")
        if case["id"] == "numeric-format-atoms.excessive-keep-going":
            require(observation["output"]["exists"] is True, "keep-going must still write output")
            require(observation["exit_status"] == 1, "keep-going must exit nonzero")
            output_bytes = decode_identity(observation["output"], "format-atoms keep-going output")
            require(b"DA:12,1.0e+19\n" in output_bytes, "keep-going must retain excessive counts in output")
        if case["id"] == "numeric-format-atoms.excessive-stop-on-error-0":
            validate_lcov_stderr(
                case["id"],
                decode_identity(observation["stderr"], f"{case['id']} stderr"),
                (("WARNING", "negative"), ("WARNING", "negative"), ("WARNING", "format"), ("WARNING", "format"),
                 ("ERROR", "excessive"), ("ERROR", "excessive"), ("ERROR", "excessive")),
            )
            require(observation["exit_status"] == 1, "stop_on_error=0 must exit nonzero")
        if case["id"] == "numeric-format-atoms.excessive-stop-on-error-1":
            validate_lcov_stderr(
                case["id"],
                decode_identity(observation["stderr"], f"{case['id']} stderr"),
                (("WARNING", "negative"), ("WARNING", "format"), ("ERROR", "corrupt"), ("ERROR", "excessive")),
            )
            require(observation["output"]["exists"] is False, "stop_on_error=1 must leave output absent")
        if case["id"] == "numeric-fna-malformed-exponent.summary":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("ERROR", "corrupt"), ("ERROR", "format")))
            require(observation["output"]["exists"] is False, "malformed FNA summary must not write output")
        if case["id"] == "numeric-zero-fn-end.summary":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("ERROR", "corrupt"), ("ERROR", "format")))
            require(observation["output"]["exists"] is False, "zero FN end summary must not write output")
        if case["id"] == "numeric-invalid-fnl-fields.summary":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("ERROR", "corrupt"), ("ERROR", "format")))
            require(observation["output"]["exists"] is False, "invalid FNL summary must not write output")
        if case["id"] == "functions-zero-start.summary":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("ERROR", "corrupt"), ("ERROR", "inconsistent")))
            require(observation["output"]["exists"] is False, "zero-start summary must not write output")
        if case["id"] == "numeric-fna-malformed-exponent.ignore-format":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("WARNING", "format"),))
        if case["id"] == "numeric-zero-fn-end.ignore-format":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("WARNING", "format"),))
        if case["id"] == "numeric-invalid-fnl-fields.ignore-format":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("WARNING", "format"), ("WARNING", "format")))
        if case["id"] == "functions-zero-start.ignore-inconsistent-format":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("WARNING", "inconsistent"), ("WARNING", "format")))
        if case["id"] == "numeric-function-excessive.default-stop":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), (("ERROR", "corrupt"), ("ERROR", "excessive")))
        if case["id"] == "numeric-function-excessive.erase-suppressed":
            validate_lcov_stderr(case["id"], decode_identity(observation["stderr"], f"{case['id']} stderr"), ())
            require(b"suppress_me" not in decode_identity(observation["output"], f"{case['id']} output"), "erase_functions must remove suppressed function")
        if case["id"] == "numeric-format-atoms.ignore-format-negative-excessive.canonical":
            require(observation["exit_status"] == 0, "ignore excessive policy must exit 0")
            output_bytes = decode_identity(observation["output"], "format-atoms full-ignore output")
            require(b"DA:12,1.0e+19\n" in output_bytes, "full-ignore must retain excessive line count")
        if case["id"] == "numeric-signed-zero.canonical":
            output_bytes = decode_identity(observation["output"], "signed-zero canonical output")
            require(b"DA:1,-0\n" in output_bytes, "signed-zero DA rewrite missing")
            require(b"BRDA:2,0,expr,-0\n" in output_bytes, "signed-zero BRDA rewrite missing")
        if case["id"] == "numeric-negative.ignore-negative":
            output_bytes = decode_identity(observation["output"], "negative ignore output")
            require(b"DA:2,0\n" in output_bytes, "negative count must coerce to zero")
            stderr = decode_identity(observation["stderr"], "negative ignore stderr").decode("utf-8", "replace")
            require("Unexpected negative hit count" in stderr, "negative ignore must warn")
        if case["id"] == "numeric-nonnumeric.ignore-format":
            output_bytes = decode_identity(observation["output"], "nonnumeric ignore output")
            require(b"DA:2,0\n" in output_bytes, "nonnumeric count must coerce to zero")
            stderr = decode_identity(observation["stderr"], "nonnumeric ignore stderr").decode("utf-8", "replace")
            require("Unexpected non-integer hit count" in stderr, "nonnumeric ignore must warn")
        if case["id"] == "numeric-malformed-exponent.ignore-format":
            output_bytes = decode_identity(observation["output"], "malformed-exponent ignore output")
            require(b"DA:2,0\n" in output_bytes, "malformed exponent must coerce to zero")
        if case["id"] == "numeric-excessive.ignore-excessive":
            require(observation["exit_status"] == 0, "ignore excessive must exit 0")
        if case["id"] == "numeric-zero-line.summary":
            stderr = decode_identity(observation["stderr"], "zero-line summary stderr").decode("utf-8", "replace")
            require("unexpected line number '0'" in stderr, "zero-line must reject line number zero")
        if case["id"] == "numeric-zero-brda.summary":
            stderr = decode_identity(observation["stderr"], "zero-brda summary stderr").decode("utf-8", "replace")
            require("unexpected line number '0'" in stderr, "zero-brda must reject line number zero")
        if case["id"] == "numeric-zero-fn.summary":
            stderr = decode_identity(observation["stderr"], "zero-fn summary stderr").decode("utf-8", "replace")
            require("unexpected" in stderr.lower() or "format" in stderr.lower(), "zero-fn must reject invalid start/end")
        if case["id"] == "numeric-zero-mcdc.summary":
            stderr = decode_identity(observation["stderr"], "zero-mcdc summary stderr").decode("utf-8", "replace")
            require("unexpected" in stderr.lower() or "format" in stderr.lower(), "zero-mcdc must reject invalid fields")
        if case["id"] == "numeric-negative-inf.ignore-negative":
            output_bytes = decode_identity(observation["output"], "negative-inf ignore output")
            require(b"DA:1,0\n" in output_bytes or b",0\n" in output_bytes, "negative Inf must coerce under ignore-negative")
        if case["id"] == "numeric-fnda-negative.ignore-negative":
            output_bytes = decode_identity(observation["output"], "fnda-negative ignore output")
            require(b"FNA:" in output_bytes or b"FNDA:0," in output_bytes, "negative FNDA must rewrite under ignore-negative")
        if case["id"] == "numeric-fnda-nonnumeric.ignore-format":
            output_bytes = decode_identity(observation["output"], "fnda-nonnumeric ignore output")
            require(b"FNA:" in output_bytes or b"FNDA:0," in output_bytes, "nonnumeric FNDA must rewrite under ignore-format")
        if case["id"] == "numeric-fna-nonnumeric.ignore-format":
            output_bytes = decode_identity(observation["output"], "fna-nonnumeric ignore output")
            require(b"FNA:" in output_bytes, "nonnumeric FNA must rewrite under ignore-format")
        if case["id"] == "numeric-brda-nonnumeric.ignore-format":
            output_bytes = decode_identity(observation["output"], "brda-nonnumeric ignore output")
            require(b"BRDA:" in output_bytes, "nonnumeric BRDA must rewrite under ignore-format")
        if case["id"] == "numeric-mcdc-nondigit.ignore-format":
            output_bytes = decode_identity(observation["output"], "mcdc-nondigit ignore output")
            require(b"MCDC:" in output_bytes or observation["exit_status"] == 0, "nondigit MCDC ignore-format must recover")
        if case["id"] == "numeric-inf-excessive.ignore-excessive":
            require(observation["exit_status"] == 0, "Inf/NaN excessive ignore must exit 0")
        if case["id"] == "checksum-match.summary":
            require(observation["exit_status"] == 0, "checksum-match must accept")
            require(observation.get("additional_fixtures") == {"cs.c": "fixtures/numeric/cs.c"}, "checksum-match additional fixture binding drift")
        if case["id"] == "checksum-match.canonical":
            output_bytes = decode_identity(observation["output"], "checksum-match canonical output")
            require(CHECKSUM_MD5_BASE64.encode("ascii") in output_bytes, "checksum-match rewrite must retain md5_base64")
            require(b"DA:1,1,AVO7Y115x231sZo9ymlVFA\n" in output_bytes, "checksum-match DA identity drift")
        if case["id"] == "checksum-mismatch.summary":
            require(observation["exit_status"] == 1, "checksum-mismatch default must reject")
            stderr = decode_identity(observation["stderr"], "checksum-mismatch stderr").decode("utf-8", "replace")
            require("checksum mismatch" in stderr, "checksum-mismatch diagnostic drift")
        if case["id"] == "checksum-mismatch.ignore-version":
            require(observation["exit_status"] == 0, "checksum-mismatch ignore-version must recover")
            output_bytes = decode_identity(observation["output"], "checksum-mismatch ignore output")
            require(b"WRONGCHK" in output_bytes, "ignore-version must keep recorded mismatch token")
        if case["id"] == "checksum-missing.summary":
            require(observation["exit_status"] == 1, "checksum-missing default must reject")
            stderr = decode_identity(observation["stderr"], "checksum-missing stderr").decode("utf-8", "replace")
            require("no checksum" in stderr, "checksum-missing diagnostic drift")
        if case["id"] == "checksum-missing.ignore-version-recompute":
            require(observation["exit_status"] == 0, "checksum recompute must exit 0")
            output_bytes = decode_identity(observation["output"], "checksum recompute output")
            require(b"DA:1,1,AVO7Y115x231sZo9ymlVFA\n" in output_bytes, "missing checksum must recompute md5_base64")
        if case["id"] == "checksum-duplicate.summary":
            require(observation["exit_status"] == 1, "checksum-duplicate default must reject")
            stderr = decode_identity(observation["stderr"], "checksum-duplicate stderr").decode("utf-8", "replace")
            require("checksum mismatch" in stderr, "checksum-duplicate diagnostic drift")
        if case["id"] == "checksum-duplicate.ignore-version":
            require(observation["exit_status"] == 0, "checksum-duplicate ignore-version must recover")
        if case["id"] == "checksum-no-verify.canonical":
            output_bytes = decode_identity(observation["output"], "checksum-no-verify output")
            require(b"DA:1,1\n" in output_bytes, "without --checksum writer must omit checksum field")
            require(b"AVO7Y115x231sZo9ymlVFA" not in output_bytes, "without --checksum must not emit checksum token")


    # Exact fixture/case closure for the ownership slice.
    state_fixtures = [fixture for fixture in generate.build_fixtures() if fixture.group == "state-ownership"]
    require([fixture.id for fixture in state_fixtures] == list(STATE_FIXTURE_IDS), "state-ownership fixture closure drift")
    state_case_ids = [case["id"] for case in cases if case["fixture"].startswith("fixtures/state/")]
    require(
        state_case_ids
        == [
            "state-late-tn-mcdc.summary",
            "state-cross-sf-mcdc-success.summary",
            "state-cross-sf-mcdc-duplicate.summary",
            "state-late-tn-mcdc.canonical",
            "state-late-tn-mcdc.semantic-snapshot",
            "state-cross-sf-mcdc-success.canonical",
            "state-cross-sf-mcdc-success.semantic-snapshot",
        ],
        f"state-ownership case closure drift: {state_case_ids}",
    )
    ver_case_ids = [case["id"] for case in cases if case["fixture"].startswith("fixtures/ver/")]
    require(
        ver_case_ids
        == [
            "ver-repeat-equal.summary",
            "ver-repeat-different.summary",
            "ver-per-source.summary",
            "ver-repeat-equal.canonical",
        ],
        f"ver-semantics case closure drift: {ver_case_ids}",
    )
    function_fixtures = [fixture for fixture in generate.build_fixtures() if fixture.group == "function-records"]
    require(
        [fixture.id for fixture in function_fixtures] == list(FUNCTION_FIXTURE_IDS),
        "function-records fixture closure drift",
    )
    function_case_ids = [case["id"] for case in cases if case["fixture"].startswith("fixtures/functions/")]
    require(
        function_case_ids
        == [
            "functions-current-core.summary",
            "functions-current-missing-alias.summary",
            "functions-zero-end.summary",
            "functions-zero-start.summary",
            "functions-mixed-merge.summary",
            "functions-mixed-location-mismatch.summary",
            "functions-mixed-range-mismatch.summary",
            "functions-index-duplicate.summary",
            "functions-index-unknown.summary",
            "functions-index-scope-reset.summary",
            "functions-index-tn-preserves.summary",
            "functions-current-core.canonical",
            "functions-current-core.semantic-snapshot",
            "functions-zero-end.canonical",
            "functions-mixed-merge.canonical",
            "functions-mixed-merge.semantic-snapshot",
            "functions-mixed-location-mismatch.canonical",
            "functions-mixed-range-mismatch.canonical",
            "functions-index-duplicate.canonical",
            "functions-index-unknown.canonical",
            "functions-index-scope-reset.canonical",
            "functions-zero-start.ignore-inconsistent-format",
            "functions-zero-start.semantic-snapshot",
        ],
        f"function-records case closure drift: {function_case_ids}",
    )
    branch_fixtures = [fixture for fixture in generate.build_fixtures() if fixture.group == "branch-records"]
    require(
        [fixture.id for fixture in branch_fixtures] == list(BRANCH_FIXTURE_IDS),
        "branch-records fixture closure drift",
    )
    branch_case_ids = [case["id"] for case in cases if case["fixture"].startswith("fixtures/branches/")]
    require(
        branch_case_ids
        == [
            "branches-forms-core.summary",
            "branches-u-modes.summary",
            "branches-malformed-tail.summary",
            "branches-malformed-tail-empty-taken.summary",
            "branches-malformed-tail-empty-expression.summary",
            "branches-expression-mismatch.summary",
            "branches-order-gaps.summary",
            "branches-noncontiguous.summary",
            "branches-interleave.summary",
            "branches-sort-signatures.summary",
            "branches-forms-core.canonical",
            "branches-forms-core.semantic-snapshot",
            "branches-u-modes.canonical",
            "branches-u-modes.clear-unreachable",
            "branches-malformed-tail.canonical",
            "branches-malformed-tail-empty-taken.canonical",
            "branches-malformed-tail-empty-expression.canonical",
            "branches-expression-mismatch.canonical",
            "branches-expression-merge.canonical",
            "branches-expression-merge.semantic-snapshot",
            "branches-order-gaps.canonical",
            "branches-noncontiguous.canonical",
            "branches-noncontiguous.semantic-snapshot",
            "branches-interleave.canonical",
            "branches-sort-signatures.canonical",
        ],
        f"branch-records case closure drift: {branch_case_ids}",
    )
    numeric_fixtures = [fixture for fixture in generate.build_fixtures() if fixture.group == "numeric-boundary"]
    require(
        [fixture.id for fixture in numeric_fixtures] == list(NUMERIC_FIXTURE_IDS),
        f"numeric-boundary fixture closure drift: {[fixture.id for fixture in numeric_fixtures]}",
    )
    numeric_case_ids = [
        case["id"]
        for case in cases
        if case["fixture"] == "fixtures/numeric-boundary.info"
        or case["fixture"].startswith("fixtures/numeric/")
        or case["fixture"] == "fixtures/functions/zero-start.info"
    ]
    require(
        numeric_case_ids
        == [
            "numeric-boundary.summary",
            "numeric-extra-spellings.summary",
            "numeric-format-atoms.summary",
            "numeric-negative.summary",
            "numeric-nonnumeric.summary",
            "numeric-malformed-exponent.summary",
            "numeric-excessive.summary",
            "numeric-zero-line.summary",
            "numeric-negative-inf.summary",
            "numeric-signed-zero.summary",
            "numeric-fnda-negative.summary",
            "numeric-fnda-nonnumeric.summary",
            "numeric-fna-nonnumeric.summary",
            "numeric-fna-malformed-exponent.summary",
            "numeric-brda-nonnumeric.summary",
            "numeric-mcdc-nondigit.summary",
            "numeric-zero-mcdc.summary",
            "numeric-zero-fn.summary",
            "numeric-zero-fn-end.summary",
            "numeric-invalid-fnl-fields.summary",
            "numeric-inf-excessive.summary",
            "functions-zero-start.summary",
            "numeric-boundary.canonical",
            "numeric-negative.ignore-negative",
            "numeric-nonnumeric.ignore-format",
            "numeric-malformed-exponent.ignore-format",
            "numeric-excessive.ignore-excessive",
            "numeric-zero-line.ignore-format",
            "numeric-boundary.semantic-snapshot",
            "numeric-extra-spellings.canonical",
            "numeric-extra-spellings.semantic-snapshot",
            "numeric-format-atoms.default-stop",
            "numeric-format-atoms.ignore-negative",
            "numeric-format-atoms.ignore-format-negative.canonical",
            "numeric-format-atoms.ignore-format-negative.semantic-snapshot",
            "numeric-format-atoms.excessive-default-stop",
            "numeric-format-atoms.excessive-keep-going",
            "numeric-format-atoms.excessive-stop-on-error-0",
            "numeric-format-atoms.excessive-stop-on-error-1",
            "numeric-format-atoms.ignore-format-negative-excessive.canonical",
            "numeric-format-atoms.ignore-format-negative-excessive.semantic-snapshot",
            "numeric-signed-zero.canonical",
            "numeric-signed-zero.semantic-snapshot",
            "numeric-negative-inf.ignore-negative",
            "numeric-negative-inf.semantic-snapshot",
            "numeric-fnda-negative.ignore-negative",
            "numeric-fnda-nonnumeric.ignore-format",
            "numeric-fna-nonnumeric.ignore-format",
            "numeric-fna-nonnumeric.semantic-snapshot",
            "numeric-fna-malformed-exponent.ignore-format",
            "numeric-brda-nonnumeric.ignore-format",
            "numeric-mcdc-nondigit.ignore-format",
            "numeric-zero-brda.summary",
            "numeric-zero-mcdc.ignore-format",
            "numeric-zero-fn.ignore-format",
            "numeric-zero-fn-end.ignore-format",
            "numeric-zero-fn-end.semantic-snapshot",
            "numeric-invalid-fnl-fields.ignore-format",
            "numeric-invalid-fnl-fields.semantic-snapshot",
            "functions-zero-start.ignore-inconsistent-format",
            "functions-zero-start.semantic-snapshot",
            "numeric-function-excessive.default-stop",
            "numeric-function-excessive.erase-suppressed",
            "numeric-inf-excessive.ignore-excessive",
            "checksum-match.summary",
            "checksum-match.canonical",
            "checksum-mismatch.summary",
            "checksum-mismatch.ignore-version",
            "checksum-missing.summary",
            "checksum-missing.ignore-version-recompute",
            "checksum-duplicate.summary",
            "checksum-duplicate.ignore-version",
            "checksum-no-verify.canonical",
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
        ],
        f"numeric/checksum case closure drift: {numeric_case_ids}",
    )


def main() -> int:
    manifest, fixtures = validate_manifest()
    validate_baseline(manifest, fixtures)
    print(f"validated {len(fixtures)} fixtures and the pinned Oracle baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
