#!/usr/bin/env python3
"""Fail-closed validator for the permanent CORE-009 corpus and sidecars."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib, re, sys

TARGETS = {"M1-FZ-LEX-001", "M1-FZ-STATEFUL-001", "M1-FZ-WRITER-001", "M1-FZ-ROUNDTRIP-001", "M1-FZ-NUMERIC-001", "M1-FZ-LINE-ALGEBRA-001", "M1-FZ-FUNCTION-ALGEBRA-001", "M1-FZ-BRANCH-ALGEBRA-001", "M1-FZ-MCDC-ALGEBRA-001"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")

def fail(message: str) -> None: raise ValueError(message)
def load(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as stream: return json.load(stream)

def validate_manifest(root: pathlib.Path) -> None:
    manifest = load(root / "corpus/manifest.json")
    if manifest.get("schema_version") != 1: fail("unsupported corpus schema_version")
    seen_cases, covered, referenced = set(), set(), set()
    for entry in manifest.get("entries", []):
        case = entry.get("case_id")
        if not case or case in seen_cases: fail(f"invalid/duplicate case_id: {case}")
        seen_cases.add(case)
        digest = entry.get("sha256", "")
        if not HEX64.fullmatch(digest): fail(f"invalid sha256 for {case}")
        targets = set(entry.get("targets", []))
        if not targets or not targets <= TARGETS: fail(f"invalid targets for {case}")
        covered |= targets
        seeds = entry.get("derived_seeds")
        if not isinstance(seeds, dict) or set(seeds) != targets: fail(f"derived seed coverage for {case}")
        matches = sorted(glob.glob(str(root / "corpus" / entry.get("file_pattern", ""))))
        if not matches: fail(f"pattern has no files for {case}")
        for raw in matches:
            path = pathlib.Path(raw)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != digest: fail(f"corpus hash mismatch: {path}")
            referenced.add(path.resolve())
        for target in targets:
            # Derive every target/case/corpus tuple; duplicate tuples indicate a
            # manifest ambiguity even though the numeric seed need not be stored.
            expected = int.from_bytes(hashlib.sha256(target.encode()+b"\0"+case.encode()+b"\0"+digest.encode()).digest()[:8], "big")
            if seeds[target] != expected: fail(f"derived seed mismatch for {case}/{target}")
    if covered != TARGETS: fail(f"target coverage mismatch: {sorted(TARGETS-covered)}")
    actual = {p.resolve() for p in (root / "corpus").glob("m1_fz_*/*") if p.is_file() and not p.name.endswith(".json")}
    if actual != referenced: fail("unreferenced or missing corpus files")

def validate_sidecar(path: pathlib.Path) -> None:
    value = load(path)
    required = {"schema_version", "target_id", "case_id", "seed", "raw_sha256", "minimized_sha256", "raw_artifact", "first_failing_operation", "semantic_snapshots", "process", "runtime_manifest", "origin_ids"}
    if set(value) != required or value["schema_version"] != 1: fail(f"sidecar shape: {path}")
    if value["target_id"] not in TARGETS: fail(f"sidecar target: {path}")
    if not isinstance(value["seed"], int) or isinstance(value["seed"], bool) or not 0 <= value["seed"] < 2**64: fail(f"sidecar seed: {path}")
    if not HEX64.fullmatch(value["raw_sha256"]) or not HEX64.fullmatch(value["minimized_sha256"]): fail(f"sidecar hash: {path}")
    artifact = path.with_suffix("")
    if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != value["minimized_sha256"]: fail(f"sidecar minimized artifact hash mismatch: {path}")
    raw_name = value["raw_artifact"]
    if pathlib.PurePath(raw_name).name != raw_name: fail(f"sidecar raw artifact path: {path}")
    raw = path.parent / raw_name
    if not raw.is_file() or hashlib.sha256(raw.read_bytes()).hexdigest() != value["raw_sha256"]: fail(f"sidecar raw artifact hash mismatch: {path}")
    process = value["process"]
    if set(process) != {"exit_code", "signal", "timed_out", "stdout", "stderr"} or not isinstance(process["timed_out"], bool): fail(f"sidecar process: {path}")
    if not value["first_failing_operation"] or not isinstance(value["semantic_snapshots"], dict) or not isinstance(value["runtime_manifest"], dict): fail(f"sidecar evidence: {path}")
    origins = value["origin_ids"]
    if not origins or len(origins) != len(set(origins)) or not all(re.match(r"^M1-(MD|TF|PROP|FZ)-", x) for x in origins): fail(f"sidecar origins: {path}")

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1]); parser.add_argument("--seed-for"); args=parser.parse_args()
    try:
        validate_manifest(args.root)
        if args.seed_for:
            target = args.seed_for.upper().replace("_", "-")
            target = target.replace("M1-FZ-", "M1-FZ-")
            manifest = load(args.root / "corpus/manifest.json")
            for entry in manifest["entries"]:
                if target in entry.get("derived_seeds", {}):
                    print(entry["derived_seeds"][target]); return 0
            fail(f"no seed for target {target}")
        for sidecar in (args.root / "corpus").glob("m1_fz_*/*.json"): validate_sidecar(sidecar)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"CORE-009 artifact validation failed: {error}", file=sys.stderr); return 1
    print("CORE-009 artifact validation passed"); return 0
if __name__ == "__main__": raise SystemExit(main())
