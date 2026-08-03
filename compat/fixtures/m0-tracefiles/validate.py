#!/usr/bin/env python3
"""Validate the generated corpus, manifest, and pinned Oracle baseline."""

from __future__ import annotations

import base64
import hashlib
import json
import tempfile
from pathlib import Path

import generate

ROOT = Path(__file__).resolve().parent
MODEL_INSPECTOR = ROOT / "inspect_model.pl"
MODEL_INSPECTOR_NAME = "inspect_model.pl"
EXPECTED_MODEL_INSPECTOR_SHA256 = "6f77427c548039d4fe17828b30ff73b245d3f6d21f6b587420dc1c830fa03d4a"
ALLOWED_ARGV_HEADS = {"lcov", "perl"}
SEMANTIC_SNAPSHOT_CASE_IDS = (
    "state-late-tn-mcdc.semantic-snapshot",
    "state-cross-sf-mcdc-success.semantic-snapshot",
)
STATE_FIXTURE_IDS = (
    "state-late-tn-mcdc",
    "state-cross-sf-mcdc-success",
    "state-cross-sf-mcdc-duplicate",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_identity(identity: dict[str, object], label: str) -> None:
    require(isinstance(identity.get("sha256"), str), f"{label}: missing sha256")
    require(isinstance(identity.get("byte_size"), int), f"{label}: missing byte_size")
    if "base64" in identity:
        data = base64.b64decode(str(identity["base64"]), validate=True)
        require(len(data) == identity["byte_size"], f"{label}: base64 size mismatch")
        require(hashlib.sha256(data).hexdigest() == identity["sha256"], f"{label}: base64 hash mismatch")


def decode_identity(identity: dict[str, object], label: str) -> bytes:
    verify_identity(identity, label)
    require("base64" in identity, f"{label}: raw identity required")
    return base64.b64decode(str(identity["base64"]), validate=True)


def validate_manifest() -> tuple[dict[str, object], dict[str, generate.Fixture]]:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="ascii"))
    fixtures = generate.build_fixtures()
    generated_manifest = generate.build_manifest(fixtures)
    require(manifest == generated_manifest, "manifest.json is not the exact generator result")
    by_path = {fixture.path: fixture for fixture in fixtures}

    tracked = {
        path.relative_to(ROOT).as_posix()
        for directory in (ROOT / "fixtures", ROOT / "generated")
        if directory.exists()
        for path in directory.rglob("*.info")
    }
    require(not (tracked - set(by_path)), f"unmanifested fixture paths: {sorted(tracked - set(by_path))}")
    required_paths = {fixture.path for fixture in fixtures if fixture.committed}
    require(not (required_paths - tracked), f"missing committed fixtures: {sorted(required_paths - tracked)}")

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
    for profile in ("scale-medium", "scale-large"):
        require(not by_id[profile].committed, f"{profile} must remain generated-only")
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


def assert_count_store(store: dict[str, object], label: str, *, allow_empty: bool = True) -> None:
    require(isinstance(store, dict), f"{label}: store must be object")
    require(isinstance(store.get("found"), int), f"{label}: missing found")
    require(isinstance(store.get("hit"), int), f"{label}: missing hit")
    require(isinstance(store.get("lines"), dict), f"{label}: missing lines")
    if not allow_empty:
        require(store["lines"], f"{label}: expected non-empty lines")


def assert_function_store(store: dict[str, object], label: str) -> None:
    require(isinstance(store, dict), f"{label}: store must be object")
    require(isinstance(store.get("found"), int), f"{label}: missing found")
    require(isinstance(store.get("hit"), int), f"{label}: missing hit")
    require(isinstance(store.get("functions"), dict), f"{label}: missing functions")


def assert_branch_store(store: dict[str, object], label: str) -> None:
    require(isinstance(store, dict), f"{label}: store must be object")
    require(isinstance(store.get("found"), int), f"{label}: missing found")
    require(isinstance(store.get("hit"), int), f"{label}: missing hit")
    require(isinstance(store.get("lines"), dict), f"{label}: missing lines")


def assert_mcdc_store(store: dict[str, object], label: str) -> None:
    require(isinstance(store, dict), f"{label}: store must be object")
    require(isinstance(store.get("found"), int), f"{label}: missing found")
    require(isinstance(store.get("hit"), int), f"{label}: missing hit")
    require(isinstance(store.get("lines"), dict), f"{label}: missing lines")
    for line, block in store["lines"].items():
        require(isinstance(block, dict), f"{label}.{line}: block must be object")
        require(isinstance(block.get("groups"), dict), f"{label}.{line}: missing groups")
        for size, exprs in block["groups"].items():
            require(isinstance(exprs, list), f"{label}.{line}.groups.{size}: must be list")
            for expr in exprs:
                require(isinstance(expr.get("expression"), str), f"{label}.{line}: missing expression")
                require("true_count" in expr and "false_count" in expr, f"{label}.{line}: missing sense counts")
                require("true_excluded" in expr and "false_excluded" in expr, f"{label}.{line}: missing excluded flags")


def assert_four_family_maps(testcases: dict[str, object], label: str) -> None:
    require(set(testcases) == {"line", "function", "branch", "mcdc"}, f"{label}: four family maps required")
    for family in ("line", "function", "branch", "mcdc"):
        require(isinstance(testcases[family], dict), f"{label}.{family}: map must be object")


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


def validate_semantic_snapshot_observation(case: dict[str, object], observation: dict[str, object]) -> None:
    require(case.get("runner") == MODEL_INSPECTOR_NAME, f"{case['id']}: runner must be inspect_model.pl")
    require(observation.get("runner") == MODEL_INSPECTOR_NAME, f"{case['id']}: baseline runner missing")
    require(case["argv"][:2] == ["perl", MODEL_INSPECTOR_NAME], f"{case['id']}: inspector argv drift")
    require(observation["exit_status"] == 0, f"{case['id']}: semantic snapshot must exit 0")
    raw = decode_identity(observation["stdout"], f"{case['id']} stdout")
    require(not observation["stderr"].get("byte_size", 1), f"{case['id']}: semantic snapshot stderr must be empty")
    try:
        text = raw.decode("ascii")
        document = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{case['id']}: semantic snapshot stdout is not valid ASCII JSON: {error}") from error
    require(isinstance(document, dict), f"{case['id']}: snapshot root must be object")
    require(raw.endswith(b"\n"), f"{case['id']}: snapshot JSON must end with newline")
    require("\t" not in text, f"{case['id']}: snapshot JSON must not contain tabs")
    require(document.get("oracle", {}).get("module") == "/usr/local/lib/lcov/lcovutil.pm", f"{case['id']}: module identity drift")
    require(document.get("oracle", {}).get("program") == "/usr/local/bin/lcov", f"{case['id']}: program identity drift")
    if case["id"] == "state-late-tn-mcdc.semantic-snapshot":
        validate_late_tn_snapshot(document)
    elif case["id"] == "state-cross-sf-mcdc-success.semantic-snapshot":
        validate_cross_sf_success_snapshot(document)
    else:
        raise ValueError(f"unexpected semantic snapshot case: {case['id']}")


def validate_baseline(manifest: dict[str, object], fixtures: dict[str, generate.Fixture]) -> None:
    cases_path = ROOT / "oracle-cases.json"
    baseline_path = ROOT / "oracle-baseline.json"
    cases_document = json.loads(cases_path.read_text(encoding="ascii"))
    expected_cases = generate.build_oracle_cases(generate.build_fixtures())
    require(cases_document == expected_cases, "oracle-cases.json is not the exact generator result")
    baseline = json.loads(baseline_path.read_text(encoding="ascii"))
    require(cases_document["schema_version"] == 1, "unsupported oracle-cases schema")
    require(baseline["schema_version"] == 1, "unsupported Oracle baseline schema")

    cases = cases_document["cases"]
    case_ids = [case["id"] for case in cases]
    require(len(case_ids) == len(set(case_ids)), "duplicate Oracle case IDs")
    require(MODEL_INSPECTOR.is_file(), "model inspector must be committed")
    for case in cases:
        require(case["fixture"] in fixtures, f"Oracle case references unknown fixture: {case['id']}")
        require(case["argv"] and case["argv"][0] in ALLOWED_ARGV_HEADS, f"invalid Oracle argv head: {case['id']}")
        require(isinstance(case["expected_exit"], int), f"missing expected_exit: {case['id']}")
        output_file = case.get("output_file")
        if output_file is not None:
            require(output_file == Path(output_file).name, f"unsafe output_file: {case['id']}")
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

    expected_oracle = manifest["provenance"]["oracle"]
    for key in ("source_commit", "docker_image", "docker_image_id", "program", "program_sha256", "perl_version"):
        require(baseline["oracle"][key] == expected_oracle[key], f"baseline Oracle {key} mismatch")
    require(baseline["oracle"]["network"] == "none", "Oracle baseline must disable network")
    require(baseline["cases_sha256"] == hashlib.sha256(cases_path.read_bytes()).hexdigest(), "oracle-cases hash mismatch")

    observations = baseline["cases"]
    observed_by_id = {observation["id"]: observation for observation in observations}
    require(len(observed_by_id) == len(observations), "duplicate baseline case IDs")
    require(set(observed_by_id) == set(case_ids), "baseline case set differs from oracle-cases")
    require(case_ids == [observation["id"] for observation in observations], "baseline case order differs from oracle-cases")

    for case in cases:
        observation = observed_by_id[case["id"]]
        require(observation["fixture"] == case["fixture"], f"fixture mismatch: {case['id']}")
        require(observation["argv"] == case["argv"], f"argv mismatch: {case['id']}")
        require(observation["exit_status"] == case["expected_exit"], f"unexpected exit status: {case['id']}")
        verify_identity(observation["stdout"], f"{case['id']} stdout")
        verify_identity(observation["stderr"], f"{case['id']} stderr")
        output = observation["output"]
        if output["exists"]:
            verify_identity(output, f"{case['id']} output")
            require(observation["output_file"] == case.get("output_file"), f"output path mismatch: {case['id']}")
        else:
            require(observation["output_file"] == case.get("output_file"), f"missing output declaration: {case['id']}")
            require(case.get("output_file") is None or output["exists"] is False, f"missing output bytes: {case['id']}")

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


def main() -> int:
    manifest, fixtures = validate_manifest()
    validate_baseline(manifest, fixtures)
    print(f"validated {len(fixtures)} fixtures and the pinned Oracle baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
