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
    for profile in ("scale-medium", "scale-large"):
        require(not by_id[profile].committed, f"{profile} must remain generated-only")

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


def validate_baseline(manifest: dict[str, object], fixtures: dict[str, generate.Fixture]) -> None:
    cases_path = ROOT / "oracle-cases.json"
    baseline_path = ROOT / "oracle-baseline.json"
    cases_document = json.loads(cases_path.read_text(encoding="ascii"))
    expected_cases = generate.build_oracle_cases(fixtures.values())
    require(cases_document == expected_cases, "oracle-cases.json is not the exact generator result")
    baseline = json.loads(baseline_path.read_text(encoding="ascii"))
    require(cases_document["schema_version"] == 1, "unsupported oracle-cases schema")
    require(baseline["schema_version"] == 1, "unsupported Oracle baseline schema")

    cases = cases_document["cases"]
    case_ids = [case["id"] for case in cases]
    require(len(case_ids) == len(set(case_ids)), "duplicate Oracle case IDs")
    for case in cases:
        require(case["fixture"] in fixtures, f"Oracle case references unknown fixture: {case['id']}")
        require(case["argv"] and case["argv"][0] == "lcov", f"invalid Oracle argv: {case['id']}")
        require(isinstance(case["expected_exit"], int), f"missing expected_exit: {case['id']}")
        output_file = case.get("output_file")
        if output_file is not None:
            require(output_file == Path(output_file).name, f"unsafe output_file: {case['id']}")

    expected_oracle = manifest["provenance"]["oracle"]
    for key in ("source_commit", "docker_image", "docker_image_id", "program", "program_sha256", "perl_version"):
        require(baseline["oracle"][key] == expected_oracle[key], f"baseline Oracle {key} mismatch")
    require(baseline["oracle"]["network"] == "none", "Oracle baseline must disable network")
    require(baseline["cases_sha256"] == hashlib.sha256(cases_path.read_bytes()).hexdigest(), "oracle-cases hash mismatch")

    observations = baseline["cases"]
    observed_by_id = {observation["id"]: observation for observation in observations}
    require(len(observed_by_id) == len(observations), "duplicate baseline case IDs")
    require(set(observed_by_id) == set(case_ids), "baseline case set differs from oracle-cases")
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


def main() -> int:
    manifest, fixtures = validate_manifest()
    validate_baseline(manifest, fixtures)
    print(f"validated {len(fixtures)} fixtures and the pinned Oracle baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
