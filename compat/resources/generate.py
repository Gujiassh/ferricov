#!/usr/bin/env python3
"""Generate and analyze deterministic M0 Oracle resource-measurement inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, BinaryIO


GENERATOR_VERSION = 1
PROFILE_NAMESPACE = b"ferricov-m0-resource-v1\0"

PROFILES: tuple[dict[str, Any], ...] = (
    {"id": "field-1k", "axis": "field_bytes", "target": 1_024},
    {"id": "field-64k", "axis": "field_bytes", "target": 65_536},
    {"id": "field-1m", "axis": "field_bytes", "target": 1_048_576},
    {"id": "field-16m", "axis": "field_bytes", "target": 16_777_216},
    {"id": "records-1", "axis": "data_records", "target": 1},
    {"id": "records-1024", "axis": "data_records", "target": 1_024},
    {"id": "records-65536", "axis": "data_records", "target": 65_536},
    {"id": "sections-1", "axis": "sections", "target": 1},
    {"id": "sections-1024", "axis": "sections", "target": 1_024},
    {"id": "sections-16384", "axis": "sections", "target": 16_384},
    {"id": "cardinality-1", "axis": "family_cardinality", "target": 1},
    {"id": "cardinality-1024", "axis": "family_cardinality", "target": 1_024},
    {"id": "cardinality-65536", "axis": "family_cardinality", "target": 65_536},
)

PROFILE_BY_ID = {profile["id"]: profile for profile in PROFILES}


class ResourceGenerationError(RuntimeError):
    pass


def profile_seed(profile_id: str) -> str:
    return hashlib.sha256(PROFILE_NAMESPACE + profile_id.encode("ascii")).hexdigest()


def _emit(output: BinaryIO, record: bytes) -> None:
    if b"\n" in record or b"\r" in record:
        raise ResourceGenerationError("generated logical record contains a line ending")
    output.write(record)
    output.write(b"\n")


def _write_field_profile(output: BinaryIO, target: int) -> None:
    _emit(output, b"TN:" + (b"x" * target))
    _emit(output, b"SF:resource/field.c")
    _emit(output, b"DA:1,1")
    _emit(output, b"end_of_record")


def _write_record_profile(output: BinaryIO, target: int) -> None:
    _emit(output, b"SF:resource/records.c")
    for index in range(1, target + 1):
        _emit(output, f"DA:{index},1".encode("ascii"))
    _emit(output, b"end_of_record")


def _write_section_profile(output: BinaryIO, target: int) -> None:
    for index in range(1, target + 1):
        _emit(output, f"SF:resource/section-{index:05}.c".encode("ascii"))
        _emit(output, b"DA:1,1")
        _emit(output, b"end_of_record")


def _write_cardinality_profile(output: BinaryIO, target: int) -> None:
    _emit(output, b"SF:resource/cardinality.c")
    for index in range(1, target + 1):
        function_index = index - 1
        _emit(output, f"FNL:{function_index},{index},{index}".encode("ascii"))
        _emit(output, f"FNA:{function_index},1,function_{index}".encode("ascii"))
    for index in range(1, target + 1):
        _emit(output, f"BRDA:{index},0,branch_{index},1".encode("ascii"))
    for index in range(1, target + 1):
        _emit(output, f"MCDC:{index},1,t,1,0,condition_{index}".encode("ascii"))
        _emit(output, f"MCDC:{index},1,f,0,0,condition_{index}".encode("ascii"))
    for index in range(1, target + 1):
        _emit(output, f"DA:{index},1".encode("ascii"))
    _emit(output, b"end_of_record")


def write_profile(profile: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    axis = profile["axis"]
    target = profile["target"]
    with path.open("wb") as output:
        if axis == "field_bytes":
            _write_field_profile(output, target)
        elif axis == "data_records":
            _write_record_profile(output, target)
        elif axis == "sections":
            _write_section_profile(output, target)
        elif axis == "family_cardinality":
            _write_cardinality_profile(output, target)
        else:
            raise ResourceGenerationError(f"unknown resource profile axis: {axis}")


def _payload(record: bytes) -> bytes:
    return record.split(b":", 1)[1] if b":" in record else b""


def analyze_input(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    input_bytes = 0
    record_count = 0
    data_record_count = 0
    section_count = 0
    max_record_bytes = 0
    max_field_bytes = 0
    current_source: bytes | None = None
    line_keys: set[tuple[bytes, bytes]] = set()
    function_keys: set[tuple[bytes, bytes]] = set()
    branch_keys: set[tuple[bytes, ...]] = set()
    mcdc_keys: set[tuple[bytes, ...]] = set()

    with path.open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            input_bytes += len(raw)
            record = raw[:-1] if raw.endswith(b"\n") else raw
            if record.endswith(b"\r"):
                record = record[:-1]
            if not record:
                continue
            record_count += 1
            max_record_bytes = max(max_record_bytes, len(record))
            max_field_bytes = max(max_field_bytes, len(_payload(record)))
            if record.startswith(b"SF:"):
                current_source = _payload(record)
                section_count += 1
            elif record == b"end_of_record":
                current_source = None
            elif record.startswith((b"DA:", b"FNL:", b"BRDA:", b"MCDC:")):
                if current_source is None:
                    raise ResourceGenerationError("coverage record appears outside a source section")
                payload = _payload(record)
                if record.startswith(b"DA:"):
                    data_record_count += 1
                    line_keys.add((current_source, payload.split(b",", 1)[0]))
                elif record.startswith(b"FNL:"):
                    function_keys.add((current_source, payload.split(b",", 1)[0]))
                elif record.startswith(b"BRDA:"):
                    branch_keys.add((current_source, *payload.split(b",", 3)[:3]))
                else:
                    fields = payload.split(b",", 5)
                    if len(fields) != 6:
                        raise ResourceGenerationError("generated MC/DC record has the wrong field count")
                    mcdc_keys.add((current_source, fields[0], fields[1], fields[4], fields[5]))

    return {
        "sha256": digest.hexdigest(),
        "input_bytes": input_bytes,
        "record_count": record_count,
        "data_record_count": data_record_count,
        "section_count": section_count,
        "maximum_record_bytes": max_record_bytes,
        "maximum_field_bytes": max_field_bytes,
        "family_cardinalities": {
            "line": len(line_keys),
            "function": len(function_keys),
            "branch": len(branch_keys),
            "mcdc": len(mcdc_keys),
        },
    }


def expected_summary(profile: dict[str, Any]) -> dict[str, int | None]:
    axis = profile["axis"]
    target = profile["target"]
    source_files = target if axis == "sections" else 1
    lines = target if axis in {"data_records", "sections", "family_cardinality"} else 1
    family = target if axis == "family_cardinality" else None
    return {
        "source_files": source_files,
        "lines_found": lines,
        "lines_hit": lines,
        "functions_found": family,
        "functions_hit": family,
        "branches_found": family,
        "branches_hit": family,
        "condition_outcomes_found": None if family is None else 2 * family,
        "condition_outcomes_hit": family,
    }


def _coverage_line(label: str, found: int | None, hit: int | None, noun: str) -> str:
    if found is None or hit is None:
        return f"  {label}: no data found"
    percentage = 100.0 * hit / found
    suffix = noun if found == 1 else {"branch": "branches"}.get(noun, noun + "s")
    return f"  {label}: {percentage:.1f}% ({hit} of {found} {suffix})"


def expected_stdout(profile: dict[str, Any]) -> bytes:
    summary = expected_summary(profile)
    lines = [
        "Reading tracefile input.info.",
        "Summary coverage rate:",
        f"  source files: {summary['source_files']}",
        _coverage_line("lines.......", summary["lines_found"], summary["lines_hit"], "line"),
        _coverage_line(
            "functions...", summary["functions_found"], summary["functions_hit"], "function"
        ),
        _coverage_line("branches....", summary["branches_found"], summary["branches_hit"], "branch"),
    ]
    conditions_found = summary["condition_outcomes_found"]
    conditions_hit = summary["condition_outcomes_hit"]
    if conditions_found is None or conditions_hit is None:
        lines.append("  conditions..: no data found")
    else:
        percentage = 100.0 * conditions_hit / conditions_found
        # LCOV 2.5 appends its plural suffix to the already plural label.
        lines.append(
            f"  conditions..: {percentage:.1f}% "
            f"({conditions_hit} of {conditions_found} conditionss)"
        )
    lines.extend(["Message summary:", "  no messages were reported"])
    return ("\n".join(lines) + "\n").encode("ascii")


def validate_shape(profile: dict[str, Any], shape: dict[str, Any]) -> None:
    target = profile["target"]
    axis = profile["axis"]
    if axis == "field_bytes" and shape["maximum_field_bytes"] != target:
        raise ResourceGenerationError(f"field-size profile drift: {profile['id']}")
    if axis == "data_records" and shape["data_record_count"] != target:
        raise ResourceGenerationError(f"data-record profile drift: {profile['id']}")
    if axis == "sections" and shape["section_count"] != target:
        raise ResourceGenerationError(f"section profile drift: {profile['id']}")
    if axis == "family_cardinality" and set(shape["family_cardinalities"].values()) != {target}:
        raise ResourceGenerationError(f"family-cardinality profile drift: {profile['id']}")
    expected = expected_summary(profile)
    if shape["section_count"] != expected["source_files"]:
        raise ResourceGenerationError(f"source-file shape drift: {profile['id']}")
    if shape["family_cardinalities"]["line"] != expected["lines_found"]:
        raise ResourceGenerationError(f"line-cardinality shape drift: {profile['id']}")


def generate_and_analyze(profile: dict[str, Any], path: Path) -> dict[str, Any]:
    write_profile(profile, path)
    shape = analyze_input(path)
    validate_shape(profile, shape)
    return shape


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=tuple(PROFILE_BY_ID))
    parser.add_argument("output", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()

    profile = PROFILE_BY_ID[args.profile]
    shape = generate_and_analyze(profile, args.output)
    metadata = {
        "generator_version": GENERATOR_VERSION,
        "profile_id": profile["id"],
        "profile_seed_sha256": profile_seed(profile["id"]),
        "axis": profile["axis"],
        "target": profile["target"],
        "shape": shape,
        "expected_summary": expected_summary(profile),
    }
    encoded = json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.metadata:
        args.metadata.write_text(encoded, encoding="ascii")
    sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
