#!/usr/bin/env python3
"""Capture exact pinned-Oracle observations for the M0 model-algebra corpus."""

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
from typing import Any

import generate


ROOT = Path(__file__).resolve().parent
INSPECTOR = ROOT / "inspect_algebra.pl"
INSPECTOR_NAME = "inspect_algebra.pl"
RAW_OUTPUT_LIMIT = 256 * 1024


def byte_identity(data: bytes, include_raw: bool = True) -> dict[str, Any]:
    identity: dict[str, Any] = {
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
        'printf "path=%s\\n" "$path"; sha256sum "$path"; '
        "perl -e 'printf \"perl=%vd\\n\", $^V'"
    )
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "sh",
            image,
            "-c",
            script,
        ],
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


def materialize_operands(case: dict[str, Any], work: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    if "left" in case and "right" in case:
        left_src = ROOT / str(case["left"])
        right_src = ROOT / str(case["right"])
        left_bytes = left_src.read_bytes()
        right_bytes = right_src.read_bytes()
        # Reverse cases encode operand order in argv; physical names stay fixed.
        (work / "left.info").write_bytes(left_bytes)
        (work / "right.info").write_bytes(right_bytes)
        hashes["left.info"] = hashlib.sha256(left_bytes).hexdigest()
        hashes["right.info"] = hashlib.sha256(right_bytes).hexdigest()
    if "input" in case:
        data = (ROOT / str(case["input"])).read_bytes()
        (work / "input.info").write_bytes(data)
        hashes["input.info"] = hashlib.sha256(data).hexdigest()
    return hashes


def prepare_rewrite_output(case: dict[str, Any], work: Path, image: str) -> None:
    """For rewrite_semantic cases, first rewrite input.info -> output.info."""
    if case.get("capture_mode") != "rewrite_semantic":
        return
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--env",
        "HOME=/tmp",
        "--env",
        "LC_ALL=C.UTF-8",
        "--env",
        "LANG=C.UTF-8",
        "--volume",
        f"{work}:/work",
        "--workdir",
        "/work",
        image,
        *generate.COMMON_LCOV_PREFIX,
        "--add-tracefile",
        "input.info",
        "--output-file",
        "output.info",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0 or not (work / "output.info").is_file():
        raise SystemExit(
            f"{case['id']}: rewrite prelude failed exit={result.returncode} "
            f"stderr={result.stderr[:400]!r}"
        )


def run_case(case: dict[str, Any], image: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ferricov-m0-algebra-case-") as raw_work:
        work = Path(raw_work)
        operand_hashes = materialize_operands(case, work)
        if case.get("runner") == INSPECTOR_NAME or INSPECTOR_NAME in [
            str(v) for v in case.get("argv", [])
        ]:
            if not INSPECTOR.is_file():
                raise SystemExit(f"missing inspector: {INSPECTOR}")
            shutil.copyfile(INSPECTOR, work / INSPECTOR_NAME)
            os.chmod(work / INSPECTOR_NAME, 0o755)
        prepare_rewrite_output(case, work, image)
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--env",
            "HOME=/tmp",
            "--env",
            "LC_ALL=C.UTF-8",
            "--env",
            "LANG=C.UTF-8",
            "--volume",
            f"{work}:/work",
            "--workdir",
            "/work",
            image,
            *[str(value) for value in case["argv"]],
        ]
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
        )
        if case.get("capture_mode") in {"semantic", "rewrite_semantic"} and result.returncode == 0:
            strict_json_loads_ascii(result.stdout, f"{case['id']} inspector stdout")
        output_file = case.get("output_file")
        output: dict[str, Any]
        if output_file:
            path = work / str(output_file)
            if path.exists():
                data = path.read_bytes()
                output = {"exists": True, **byte_identity(data)}
            else:
                output = {"exists": False}
        else:
            output = {"exists": False}
        observation: dict[str, Any] = {
            "id": case["id"],
            "model_row": case["model_row"],
            "binding_ids": case["binding_ids"],
            "property_ids": case.get("property_ids", []),
            "phase": case["phase"],
            "runner": case["runner"],
            "op": case.get("op"),
            "argv": case["argv"],
            "expected_exit": case["expected_exit"],
            "exit_status": result.returncode,
            "stdout": byte_identity(result.stdout),
            "stderr": byte_identity(result.stderr),
            "output_file": output_file,
            "output": output,
            "operand_sha256": operand_hashes,
            "product_compatibility_evidence": False,
        }
        for key in ("left", "right", "input", "left_sha256", "right_sha256", "input_sha256"):
            if key in case:
                observation[key] = case[key]
        return observation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default=generate.ORACLE_IMAGE_ID)
    parser.add_argument("--cases", type=Path, default=ROOT / "oracle-cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "oracle-baseline.json")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--case-prefix", action="append", default=[])
    args = parser.parse_args()

    if not INSPECTOR.is_file():
        raise SystemExit(f"missing inspector: {INSPECTOR}")

    cases_raw = args.cases.read_bytes()
    cases_document = strict_json_loads_ascii(cases_raw, "oracle cases")
    cases = list(cases_document["cases"])  # type: ignore[index]
    if args.case_id or args.case_prefix:
        selected: list[dict[str, Any]] = []
        seen: set[str] = set()
        by_id = {str(case["id"]): case for case in cases}
        for case_id in args.case_id:
            if case_id not in by_id:
                raise SystemExit(f"unknown case id: {case_id}")
            if case_id in seen:
                raise SystemExit(f"duplicate case id: {case_id}")
            selected.append(by_id[case_id])  # type: ignore[arg-type]
            seen.add(case_id)
        for prefix in args.case_prefix:
            matched = [case for case in cases if str(case["id"]).startswith(prefix)]
            if not matched:
                raise SystemExit(f"unmatched case prefix: {prefix}")
            for case in matched:
                case_id = str(case["id"])
                if case_id in seen:
                    raise SystemExit(f"duplicate case from selectors: {case_id}")
                selected.append(case)  # type: ignore[arg-type]
                seen.add(case_id)
        cases = selected

    expected_image = generate.ORACLE_IMAGE_ID
    image_id = inspect_image(args.image)
    if image_id != expected_image:
        raise SystemExit(f"Oracle image mismatch: {image_id} != {expected_image}")
    program = inspect_program(args.image)
    if program["sha256"] != generate.ORACLE_EXECUTABLE_SHA256:
        raise SystemExit(f"Oracle executable mismatch: {program['sha256']}")

    observations = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}", flush=True)
        observations.append(run_case(case, args.image))  # type: ignore[arg-type]

    baseline = {
        "schema_version": 1,
        "oracle": {
            "source_commit": generate.ORACLE_COMMIT,
            "docker_image": generate.ORACLE_IMAGE,
            "docker_image_id": image_id,
            "program": program["path"],
            "program_sha256": program["sha256"],
            "perl_version": program["perl_version"],
            "locale": "C.UTF-8",
            "network": "none",
        },
        "cases_sha256": hashlib.sha256(cases_raw).hexdigest(),
        "product_compatibility_evidence": False,
        "blocked_case_ids": ["M1-MD-020", "M1-TF-063", "M1-TF-064"],
        "cases": observations,
    }
    args.output.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"wrote {len(observations)} observations to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
