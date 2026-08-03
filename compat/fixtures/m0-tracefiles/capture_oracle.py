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


def case_uses_model_inspector(case: dict[str, object]) -> bool:
    runner = case.get("runner")
    if runner == MODEL_INSPECTOR_NAME:
        return True
    argv = [str(value) for value in case.get("argv", [])]
    return MODEL_INSPECTOR_NAME in argv


def run_case(case: dict[str, object], generated_root: Path, image: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ferricov-m0-oracle-case-") as raw_work:
        work = Path(raw_work)
        shutil.copyfile(generated_root / str(case["fixture"]), work / "input.info")
        if case_uses_model_inspector(case):
            if not MODEL_INSPECTOR.is_file():
                raise SystemExit(f"missing model inspector: {MODEL_INSPECTOR}")
            shutil.copyfile(MODEL_INSPECTOR, work / MODEL_INSPECTOR_NAME)
            os.chmod(work / MODEL_INSPECTOR_NAME, 0o755)
        command = [
            "docker", "run", "--rm", "--network", "none",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--env", "HOME=/tmp", "--env", "LC_ALL=C.UTF-8", "--env", "LANG=C.UTF-8",
            "--volume", f"{work}:/work", "--workdir", "/work", image,
            *[str(value) for value in case["argv"]],
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        output_file = case.get("output_file")
        output = output_identity(work / str(output_file)) if output_file else {"exists": False}
        observation: dict[str, object] = {
            "id": case["id"],
            "fixture": case["fixture"],
            "argv": case["argv"],
            "exit_status": result.returncode,
            "stdout": byte_identity(result.stdout),
            "stderr": byte_identity(result.stderr),
            "output_file": output_file,
            "output": output,
        }
        if case.get("runner") is not None:
            observation["runner"] = case["runner"]
        return observation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default=generate.ORACLE_IMAGE_ID)
    parser.add_argument("--cases", type=Path, default=ROOT / "oracle-cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "oracle-baseline.json")
    args = parser.parse_args()

    if not MODEL_INSPECTOR.is_file():
        raise SystemExit(f"missing model inspector: {MODEL_INSPECTOR}")

    manifest = generate.build_manifest(generate.build_fixtures())
    expected_oracle = manifest["provenance"]["oracle"]
    image_id = inspect_image(args.image)
    if image_id != expected_oracle["docker_image_id"]:
        raise SystemExit(f"Oracle image mismatch: {image_id}")
    program = inspect_program(args.image)
    if program["sha256"] != expected_oracle["program_sha256"]:
        raise SystemExit(f"Oracle executable mismatch: {program['sha256']}")

    cases_document = json.loads(args.cases.read_text(encoding="ascii"))
    with tempfile.TemporaryDirectory(prefix="ferricov-m0-oracle-") as raw_generated:
        generated_root = Path(raw_generated)
        generate.write_corpus(generated_root, include_scale=True)
        observations = []
        for index, case in enumerate(cases_document["cases"], start=1):
            print(f"[{index}/{len(cases_document['cases'])}] {case['id']}", flush=True)
            observations.append(run_case(case, generated_root, args.image))

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
        "cases_sha256": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        "cases": observations,
    }
    args.output.write_text(json.dumps(baseline, indent=2) + "\n", encoding="ascii")
    print(f"wrote {len(observations)} observations to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
