#!/usr/bin/env python3
"""Validate compatibility contracts, snapshots, inventory, and result evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator


def validate_documents(schema_path: Path, documents: list[Path]) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for document in documents:
        validator.validate(json.loads(document.read_text(encoding="utf-8")))
    print(f"SCHEMA_OK schema={schema_path} documents={len(documents)}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, action="append", default=[])
    parser.add_argument("--skip-oracle", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    validate_documents(
        root / "compat/schema/suite.schema.json",
        sorted((root / "compat/cases").glob("*.json")),
    )
    validate_documents(
        root / "compat/schema/launcher.schema.json",
        sorted((root / "compat/launchers").glob("*.json")),
    )
    result_documents = []
    for result_root in args.results:
        documents = sorted(result_root.rglob("result.json"))
        if not documents:
            raise RuntimeError(f"no result.json evidence under {result_root}")
        result_documents.extend(documents)
    validate_documents(
        root / "compat/schema/differential-result.schema.json",
        sorted(result_documents),
    )

    if args.skip_oracle:
        return 0

    run([str(root / "compat/upstream/build.sh")], root)
    with tempfile.TemporaryDirectory(prefix="ferricov-help-") as directory:
        generated_help = Path(directory)
        commands = json.loads((root / "compat/inventory/v2.5.json").read_text())["commands"]
        for command in commands:
            output = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "ferricov/lcov-oracle:v2.5",
                    command["name"],
                    "--help",
                ],
                check=True,
                capture_output=True,
            )
            (generated_help / f"{command['name']}.txt").write_bytes(output.stdout)
            committed = root / "compat/upstream/help" / f"{command['name']}.txt"
            if output.stdout != committed.read_bytes():
                raise RuntimeError(f"help snapshot drift: {command['name']}")

        inventory = generated_help / "inventory.json"
        upstream_root = Path(directory) / "upstream"
        run(
            [
                "git",
                "clone",
                "--branch",
                "v2.5",
                "--depth",
                "1",
                "https://github.com/linux-test-project/lcov.git",
                str(upstream_root),
            ],
            root,
        )
        run(
            [
                "cargo",
                "run",
                "--locked",
                "-p",
                "ferricov-oracle",
                "--bin",
                "inventory",
                "--",
                str(upstream_root),
                str(generated_help),
                str(inventory),
            ],
            root,
        )
        committed_inventory = root / "compat/inventory/v2.5.json"
        if sha256(inventory) != sha256(committed_inventory):
            raise RuntimeError("inventory regeneration is not byte-stable")
        print(f"INVENTORY_OK sha256={sha256(inventory)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
