#!/usr/bin/env python3
"""Capture exact pinned-Oracle observations for the M0 tracefile corpus."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import generate

ROOT = Path(__file__).resolve().parent
CANONICAL_BASELINE_PATH = ROOT / "oracle-baseline.json"
EXPECTED_MERGE_BASELINE_SHA256 = "b586a1196d120126f618b56f5995b6a2cc9f3bd27b2c4ab10e0e27e7f955e09e"
RAW_OUTPUT_LIMIT = 256 * 1024
MODEL_INSPECTOR = ROOT / "inspect_model.pl"
MODEL_INSPECTOR_NAME = "inspect_model.pl"


def byte_identity(data: bytes, include_raw: bool = True) -> dict[str, object]:
    identity: dict[str, object] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
    }
    if include_raw and len(data) <= RAW_OUTPUT_LIMIT:
        identity["base64"] = base64.b64encode(data).decode("ascii")
    return identity


def reject_json_constant(value: str) -> None:
    raise ValueError(f"non-RFC JSON constant: {value}")


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate JSON object key: {key}")
        document[key] = value
    return document


def strict_json_loads_ascii(data: bytes, label: str) -> dict[str, object]:
    try:
        text = data.decode("ascii")
        document = json.loads(
            text,
            parse_constant=reject_json_constant,
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SystemExit(f"{label}: not strict ASCII JSON: {error}") from error
    if not isinstance(document, dict):
        raise SystemExit(f"{label}: JSON root must be an object")
    return document


def validate_semantic_json(data: bytes, case_id: str) -> None:
    strict_json_loads_ascii(data, f"{case_id} inspector stdout")


def inspect_image(image: str) -> str:
    result = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.decode("ascii").strip()


def inspect_program(image: str) -> dict[str, str]:
    script = (
        'path=$(readlink -f "$(command -v lcov)"); '
        'printf "path=%s\n" "$path"; sha256sum "$path"; '
        "perl -e 'printf \"perl=%vd\\n\", $^V'"
    )
    result = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--entrypoint", "sh", image, "-c", script],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    lines = result.stdout.decode("ascii").splitlines()
    return {
        "path": lines[0].removeprefix("path="),
        "sha256": lines[1].split()[0],
        "perl_version": lines[2].removeprefix("perl="),
    }


def output_identity(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False}
    data = path.read_bytes()
    result: dict[str, object] = {"exists": True, **byte_identity(data)}
    result.update(
        {
            "record_count": generate.data_metadata(data)["record_count"],
            "record_counts": generate.data_metadata(data)["record_counts"],
        }
    )
    return result




def load_strict_numeric_plan(path: Path) -> tuple[bytes, dict[str, object]]:
    raw = path.read_bytes()
    if any(byte > 127 for byte in raw):
        raise SystemExit(f"{path}: numeric plan contains non-ASCII bytes")
    document = strict_json_loads_ascii(raw, f"{path} numeric plan")
    # strict_json_loads_ascii already rejects non-object root, constants, duplicate keys
    return raw, document


def case_numeric_plan_path(case: dict[str, object]) -> str | None:
    argv = [str(value) for value in case.get("argv", [])]
    if "--numeric-plan" not in argv:
        return None
    index = argv.index("--numeric-plan")
    if index + 1 >= len(argv):
        raise SystemExit(f"{case.get('id')}: --numeric-plan lacks a value")
    return argv[index + 1]

def case_uses_model_inspector(case: dict[str, object]) -> bool:
    runner = case.get("runner")
    if runner == MODEL_INSPECTOR_NAME:
        return True
    argv = [str(value) for value in case.get("argv", [])]
    return MODEL_INSPECTOR_NAME in argv


def normalize_case_environment(case: dict[str, object]) -> dict[str, str] | None:
    """Validate optional case environment as string->string only."""
    if "environment" not in case:
        return None
    raw = case["environment"]
    if not isinstance(raw, dict) or not raw:
        raise SystemExit(f"{case.get('id')}: environment must be a non-empty object")
    env: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise SystemExit(
                f"{case.get('id')}: environment keys and values must be strings"
            )
        if not key or "=" in key:
            raise SystemExit(f"{case.get('id')}: invalid environment key {key!r}")
        env[key] = value
    return env


def run_case(case: dict[str, object], generated_root: Path, image: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ferricov-m0-oracle-case-") as raw_work:
        work = Path(raw_work)
        shutil.copyfile(generated_root / str(case["fixture"]), work / "input.info")
        # Materialize durable fixture path so plan.fixture bindings can resolve
        # against the same relative path used in committed plans.
        fixture_rel = Path(str(case["fixture"]))
        durable_fixture = work / fixture_rel
        durable_fixture.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated_root / fixture_rel, durable_fixture)
        additional_fixtures = case.get("additional_fixtures", {})
        for name, fixture in additional_fixtures.items():
            shutil.copyfile(generated_root / str(fixture), work / str(name))
            # Also materialize durable plan/fixture companion paths.
            fixture_path = Path(str(fixture))
            durable = work / fixture_path
            durable.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(generated_root / fixture_path, durable)
        if case_uses_model_inspector(case):
            if not MODEL_INSPECTOR.is_file():
                raise SystemExit(f"missing model inspector: {MODEL_INSPECTOR}")
            shutil.copyfile(MODEL_INSPECTOR, work / MODEL_INSPECTOR_NAME)
            os.chmod(work / MODEL_INSPECTOR_NAME, 0o755)
        plan_name = case_numeric_plan_path(case)
        if plan_name is not None:
            # Prefer additional_fixtures binding; otherwise look under generated root fixtures.
            plan_source = None
            for name, fixture in additional_fixtures.items():
                if name == plan_name or Path(str(fixture)).name == plan_name:
                    plan_source = generated_root / str(fixture)
                    break
            if plan_source is None:
                # search common fixture path
                candidate = generated_root / "fixtures" / "numeric" / plan_name
                if candidate.is_file():
                    plan_source = candidate
            if plan_source is None or not plan_source.is_file():
                raise SystemExit(f"{case['id']}: numeric plan not found for {plan_name}")
            plan_raw, _plan_doc = load_strict_numeric_plan(plan_source)
            (work / Path(plan_name).name).write_bytes(plan_raw)
        case_env = normalize_case_environment(case)
        command = [
            "docker", "run", "--rm", "--network", "none",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--env", "HOME=/tmp", "--env", "LC_ALL=C.UTF-8", "--env", "LANG=C.UTF-8",
        ]
        if case_env is not None:
            for key in sorted(case_env):
                command.extend(["--env", f"{key}={case_env[key]}"])
        command.extend(
            [
                "--volume", f"{work}:/work", "--workdir", "/work", image,
                *[str(value) for value in case["argv"]],
            ]
        )
        # Hash the exact bytes mounted into the container before execution.
        fixture_sha256 = hashlib.sha256((work / "input.info").read_bytes()).hexdigest()
        additional_fixture_sha256 = {
            name: hashlib.sha256((work / name).read_bytes()).hexdigest()
            for name in additional_fixtures
        }
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if case_uses_model_inspector(case):
            validate_semantic_json(result.stdout, str(case["id"]))
        output_file = case.get("output_file")
        output = output_identity(work / str(output_file)) if output_file else {"exists": False}
        observation: dict[str, object] = {
            "id": case["id"],
            "fixture": case["fixture"],
            "fixture_sha256": fixture_sha256,
            "argv": case["argv"],
            "exit_status": result.returncode,
            "stdout": byte_identity(result.stdout),
            "stderr": byte_identity(result.stderr),
            "output_file": output_file,
            "output": output,
        }
        if case_env is not None:
            observation["environment"] = dict(case_env)
        if additional_fixtures:
            observation["additional_fixtures"] = additional_fixtures
            observation["additional_fixture_sha256"] = additional_fixture_sha256
        if case.get("runner") is not None:
            observation["runner"] = case["runner"]
        return observation



def validate_merge_into_request(
    merge_into: Path,
    selected_case_ids: list[str],
) -> bytes:
    """Reject untrusted TF-030 merge inputs and return trusted baseline bytes.

    The returned bytes are the single source used for later merge parsing so a
    mutation between hash validation and parse cannot change merge input.
    """
    from corpus_tf030 import TF030_CASE_IDS

    merge_path = merge_into.resolve()
    canonical = CANONICAL_BASELINE_PATH.resolve()
    if merge_path != canonical:
        raise SystemExit(
            f"merge-into must be the canonical baseline path {canonical}, got {merge_path}"
        )
    raw = merge_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_MERGE_BASELINE_SHA256:
        raise SystemExit(
            "merge-into baseline byte identity mismatch: "
            f"expected {EXPECTED_MERGE_BASELINE_SHA256}, got {digest}"
        )
    selected = list(selected_case_ids)
    expected = list(TF030_CASE_IDS)
    if selected != expected:
        raise SystemExit(
            "merge-into selection must be exactly the 15 TF-030 case ids in registry order; "
            f"got {len(selected)} ids"
        )
    return raw


def select_oracle_cases(
    cases: list[dict[str, object]],
    case_ids: list[str],
    case_prefixes: list[str],
) -> list[dict[str, object]]:
    """Select cases while preserving explicit --case-id order and rejecting duplicates."""
    if not case_ids and not case_prefixes:
        return list(cases)

    by_id = {str(case["id"]): case for case in cases}
    if len(by_id) != len(cases):
        raise SystemExit("oracle cases: duplicate case ids in cases document")

    selected: list[dict[str, object]] = []
    seen: set[str] = set()

    for case_id in case_ids:
        if case_id not in by_id:
            raise SystemExit(f"unknown --case-id values: {[case_id]}")
        if case_id in seen:
            raise SystemExit(f"duplicate --case-id value: {case_id}")
        selected.append(by_id[case_id])
        seen.add(case_id)

    if case_prefixes:
        for case in cases:
            case_id = str(case["id"])
            if not any(case_id.startswith(prefix) for prefix in case_prefixes):
                continue
            if case_id in seen:
                raise SystemExit(
                    f"duplicate case id from overlapping selectors: {case_id}"
                )
            selected.append(case)
            seen.add(case_id)

    if not selected:
        raise SystemExit("no oracle cases matched --case-id/--case-prefix filters")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default=generate.ORACLE_IMAGE_ID)
    parser.add_argument("--cases", type=Path, default=ROOT / "oracle-cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "oracle-baseline.json")
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Capture only the named case id (repeatable; order preserved).",
    )
    parser.add_argument(
        "--case-prefix",
        action="append",
        default=[],
        help="Capture only case ids with this prefix (repeatable).",
    )
    parser.add_argument(
        "--merge-into",
        type=Path,
        default=None,
        help="Merge captured observations into an existing baseline by case id.",
    )
    args = parser.parse_args()

    if not MODEL_INSPECTOR.is_file():
        raise SystemExit(f"missing model inspector: {MODEL_INSPECTOR}")

    # Parse selection and validate merge inputs before any Docker introspection.
    cases_raw = args.cases.read_bytes()
    cases_document = strict_json_loads_ascii(cases_raw, "oracle cases")
    if not isinstance(cases_document.get("cases"), list):
        raise SystemExit("oracle cases: cases must be an array")
    selected_cases = select_oracle_cases(
        list(cases_document["cases"]),
        list(args.case_id),
        list(args.case_prefix),
    )
    trusted_merge_bytes: bytes | None = None
    if args.merge_into is not None:
        trusted_merge_bytes = validate_merge_into_request(
            args.merge_into,
            [str(case["id"]) for case in selected_cases],
        )

    manifest = generate.build_manifest(generate.build_fixtures())
    expected_oracle = manifest["provenance"]["oracle"]
    image_id = inspect_image(args.image)
    if image_id != expected_oracle["docker_image_id"]:
        raise SystemExit(f"Oracle image mismatch: {image_id}")
    program = inspect_program(args.image)
    if program["sha256"] != expected_oracle["program_sha256"]:
        raise SystemExit(f"Oracle executable mismatch: {program['sha256']}")

    with tempfile.TemporaryDirectory(prefix="ferricov-m0-oracle-") as raw_generated:
        generated_root = Path(raw_generated)
        generate.write_corpus(generated_root, include_scale=True)
        manifest_sha256 = hashlib.sha256((generated_root / "manifest.json").read_bytes()).hexdigest()
        observations = []
        for index, case in enumerate(selected_cases, start=1):
            print(f"[{index}/{len(selected_cases)}] {case['id']}", flush=True)
            observations.append(run_case(case, generated_root, args.image))

    if args.merge_into is not None:
        assert trusted_merge_bytes is not None
        # Optional path reaffirmation only; parse the already-validated bytes.
        if args.merge_into.resolve() != CANONICAL_BASELINE_PATH.resolve():
            raise SystemExit(
                "merge-into path drifted from canonical baseline after capture"
            )
        merge_document = strict_json_loads_ascii(trusted_merge_bytes, "merge baseline")
        if not isinstance(merge_document.get("cases"), list):
            raise SystemExit("merge baseline: cases must be an array")
        by_id = {observation["id"]: observation for observation in merge_document["cases"]}
        if len(by_id) != len(merge_document["cases"]):
            raise SystemExit("merge baseline: duplicate observation ids")
        for observation in observations:
            case_id = observation["id"]
            if case_id not in by_id:
                raise SystemExit(f"merge baseline missing case id: {case_id}")
            by_id[case_id] = observation
        merged_cases = [by_id[case["id"]] for case in merge_document["cases"]]
        baseline = {
            "schema_version": merge_document["schema_version"],
            "oracle": merge_document["oracle"],
            "cases_sha256": hashlib.sha256(cases_raw).hexdigest(),
            "manifest_sha256": merge_document.get("manifest_sha256", manifest_sha256),
            "cases": merged_cases,
        }
    else:
        baseline = {
            "schema_version": 1,
            "oracle": {
                "source_commit": expected_oracle["source_commit"],
                "docker_image": generate.ORACLE_IMAGE,
                "docker_image_id": image_id,
                "program": program["path"],
                "program_sha256": program["sha256"],
                "perl_version": program["perl_version"],
                "locale": "C.UTF-8",
                "network": "none",
            },
            "cases_sha256": hashlib.sha256(cases_raw).hexdigest(),
            "manifest_sha256": manifest_sha256,
            "cases": observations,
        }
    args.output.write_text(json.dumps(baseline, indent=2) + "\n", encoding="ascii")
    print(f"wrote {len(baseline['cases'])} observations to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
