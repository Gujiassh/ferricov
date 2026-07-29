#!/usr/bin/env python3
"""Generate and validate the fail-closed LCOV 2.5 installation contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).with_name("v2.5.json")
SCHEMA_PATH = ROOT / "compat/schema/installation-contract.schema.json"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference")
)
TREE_LOCK = ROOT / "compat/upstream/installed-tree.lock"
ORACLE_MANIFEST = ROOT / "compat/manifests/oracle-lcov-v2.5-smoke.json"
BENCHMARK_RESULT = ROOT / "compat/benchmarks/results/oracle-x86_64-linux-20260728/result.json"

EXPECTED_ARTIFACT_HASHES = {
    "compat/upstream/installed-tree.lock":
        "75edeea2799a5f13715df5dd119bc10614ee347aa5fc33e37fbeb21cafd8fd24",
    "compat/manifests/oracle-lcov-v2.5-smoke.json":
        "a15e953f5dfa176ac0d2f2b0c8668f190951f64e58a69bd9e63365e8eb3ea981",
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/result.json":
        "851fe9ca0b81e5af95139d1daad84afad413e0da083cdee21266f3644e348131",
}

ASSET_SAMPLE_PATHS = (
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/report-genhtml-default-measured-000/output-tree.json",
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/report-genhtml-default-measured-001/output-tree.json",
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/report-genhtml-default-measured-002/output-tree.json",
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/report-genhtml-default-warmup-000/output-tree.json",
)
EXPECTED_ASSET_SAMPLE_HASHES = {
    ASSET_SAMPLE_PATHS[0]: "6b45e6e2c1f7a9f55df111c47045d6a68e69c7f5f8a1b9f23ce49cad96af83a7",
    ASSET_SAMPLE_PATHS[1]: "c0c12cc0504942e99e2c5fa50dea8b053c16c0e2809987506626e6135b8fb01f",
    ASSET_SAMPLE_PATHS[2]: "f8e42c0433d562edc74210e69d64e959348851627b038f954ac78bb741a4c368",
    ASSET_SAMPLE_PATHS[3]: "6a457161384a125f32227957760a74109857fd28e1f29e59ee37159296641bab",
}
EXPECTED_SAMPLE_METADATA_HASHES = {
    str(Path(ASSET_SAMPLE_PATHS[0]).with_name("sample.json")):
        "2ff8dcf8efc631462f8a9a97cead439449bcc8367fc1433942d0d37d25558aa5",
    str(Path(ASSET_SAMPLE_PATHS[1]).with_name("sample.json")):
        "0feefe681ad1f21aeb8c352adee36746e2d97f6b911b6477b920a876a8724b5c",
    str(Path(ASSET_SAMPLE_PATHS[2]).with_name("sample.json")):
        "c65aed31ba534877c10ec17a60ca8a92f926e501e19ece9626b55a4f8d008cc4",
    str(Path(ASSET_SAMPLE_PATHS[3]).with_name("sample.json")):
        "f86f9774eba770f04da0c94f19caa24ef3730091040950bb811d20cee0d1b847",
}

LAYOUT_IDS = (
    "INST-PATHS-001",
    "INST-BIN-001",
    "INST-SCRIPT-001",
    "INST-LIB-001",
    "INST-MAN-001",
    "INST-HTML-001",
    "INST-EXAMPLE-001",
    "INST-CONFIG-001",
    "INST-REPORT-ASSET-001",
)
FAILURE_IDS = (
    "INST-INTERP-001",
    "INST-CONFIG-DISCOVERY-001",
    "INST-UNINSTALL-001",
    "INST-PARTIAL-001",
    "INST-PATH-001",
    "INST-DIRTY-ASSET-001",
    "INST-DOC-FAIL-001",
    "INST-TEST-RUN-001",
    "INST-DOC-PATH-001",
    "INST-LICENSE-001",
)
PLANNED_CASE_IDS = (
    "INST-LAYOUT-001",
    "INST-STAGE-001",
    "INST-INTERP-001",
    "INST-CONFIG-DISCOVERY-001",
    "INST-UNINSTALL-001",
    "INST-PARTIAL-001",
    "INST-DOC-FAIL-001",
    "INST-PATH-001",
    "INST-DIRTY-ASSET-001",
    "INST-TEST-RUN-001",
    "INST-DOC-PATH-001",
    "INST-REPORT-ASSET-001",
    "INST-LICENSE-001",
)

SOURCE_CLOSURES = (
    ("installation.make-variables", "Makefile", 38, 84, "install_variables"),
    ("installation.make-doc-install", "Makefile", 125, 190, "install_recipe"),
    ("installation.make-uninstall", "Makefile", 194, 223, "uninstall_recipe"),
    ("installation.fixup", "bin/fix.pl", 89, 139, "interpreter_fixup"),
    ("installation.docs-build", "docs/Makefile", 4, 22, "documentation_build"),
    ("installation.docs-config", "docs/conf.py", 34, 63, "documentation_config"),
    ("installation.man-pages", "docs/conf.py", 83, 153, "man_page_generation"),
    ("installation.config-discovery", "lib/lcovutil.pm", 1448, 1460, "config_discovery"),
    ("installation.test-runtime", "tests/common.mak", 2, 18, "installed_test_runtime"),
    ("installation.test-paths", "tests/common.mak", 76, 83, "installed_test_paths"),
    ("installation.test-readme", "tests/README.md", 13, 18, "installed_test_docs"),
    ("installation.readme-paths", "README.rst", 125, 139, "documented_paths"),
    ("installation.asset-names", "bin/genhtml", 7128, 7128, "report_asset_names"),
    ("installation.asset-generation", "bin/genhtml", 7952, 7952, "report_asset_generation"),
    ("installation.asset-writers", "bin/genhtml", 8822, 9046, "report_asset_writers"),
)

EXPECTED_GROUPS = (
    ("bin", "/usr/local/bin/", 10, ("file",), ("755",)),
    ("config", "/usr/local/etc/lcovrc", 1, ("file",), ("644",)),
    ("lib", "/usr/local/lib/lcov/lcovutil.pm", 1, ("file",), ("644",)),
    ("man", "/usr/local/share/man/", 10, ("file",), ("644",)),
    ("support_scripts", "/usr/local/share/lcov/support-scripts/", 23, ("file",), ("755",)),
    ("html", "/usr/local/share/lcov/html/", 60, ("file",), ("644",)),
    ("example", "/usr/local/share/lcov/example/", 10, ("file",), ("644",)),
    ("tests", "/usr/local/share/lcov/tests/", 205, ("file",), ("644", "755")),
    ("legacy_man_symlink", "/usr/local/man", 1, ("symlink",), ("777",)),
)

EXPECTED_ASSETS = (
    ("gcov-css", "gcov.css", "css", 24155, "a302edd3a3f0ec66ffb0c1c41946ea9f6d6c14856906ebdcf5d8f8d81f03fa5d"),
    ("ruby-png", "ruby.png", "png", 141, "a2332ef8c44727042b0ab36628aaf562b0d5b0df43c6fa73c5191dfac50ec7be"),
    ("amber-png", "amber.png", "png", 141, "dff576889b1ebdb619eeb69f12d503f7c431d5ff321838624b804ea5bda86fcb"),
    ("emerald-png", "emerald.png", "png", 141, "8479273af3556e10f0feb96d8ac24fbd9615b0d887437c0f85f8ef6638e56b83"),
    ("snow-png", "snow.png", "png", 141, "53c50fc490fcf2ad290819b05f8033b1cbdad698e230bdcbac63564942c34723"),
    ("glass-png", "glass.png", "png", 167, "936a969e16ba5de4db2c9bcacd197b22a276e3d636335ba7f347da4009fc9cc5"),
    ("updown-png", "updown.png", "png", 117, "a851165a175f4ca2649a4e30291192dd71131ea02a93cf46464953e74c1c5f0c"),
)

EVIDENCE_GAPS = (
    "directory entries and directory modes are not retained by installed-tree.sh",
    "staged DESTDIR versus embedded PREFIX behavior",
    "interpreter override and shebang fixup behavior",
    "fresh-install HOME, LCOV_HOME, and explicit configuration precedence",
    "uninstall man residue and foreign sentinel safety",
    "injected partial-install failure and rollback policy",
    "relative, empty, space-containing, and platform-specific install roots",
    "dirty working-tree enumeration and untracked asset admission",
    "documentation builder/theme failure and source-tree cleanup",
    "installed test execution with unset and explicit LCOV_HOME",
    "README path mismatches and distribution license manifest",
    "report asset variants, optional updown generation, and HTML reference checks",
)


class InstallationContractError(RuntimeError):
    pass


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InstallationContractError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise InstallationContractError(f"expected JSON object: {path}")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def source_closure(upstream_root: Path, closure: tuple[str, str, int, int, str]) -> dict[str, Any]:
    identifier, path, start, end, role = closure
    try:
        lines = (upstream_root / path).read_text(encoding="utf-8").splitlines()
        selected = lines[start - 1:end]
    except (OSError, IndexError) as error:
        raise InstallationContractError(f"cannot read source closure {path}:{start}-{end}") from error
    if len(selected) != end - start + 1:
        raise InstallationContractError(f"short source closure {path}:{start}-{end}")
    content = ("\n".join(selected) + "\n").encode("utf-8")
    return {
        "id": identifier,
        "path": path,
        "line_start": start,
        "line_end": end,
        "line_count": len(selected),
        "role": role,
        "sha256": sha256_bytes(content),
    }


def artifact_bindings() -> list[dict[str, str]]:
    result = []
    for relative, expected in EXPECTED_ARTIFACT_HASHES.items():
        path = ROOT / relative
        actual = sha256_file(path)
        if actual != expected:
            raise InstallationContractError(
                f"retained installation artifact drift: {relative} expected={expected} actual={actual}"
            )
        result.append({"path": relative, "sha256": actual})
    for bindings, label in (
        (EXPECTED_ASSET_SAMPLE_HASHES, "asset sample"),
        (EXPECTED_SAMPLE_METADATA_HASHES, "sample metadata"),
    ):
        for relative, expected in bindings.items():
            actual = sha256_file(ROOT / relative)
            if actual != expected:
                raise InstallationContractError(
                    f"retained {label} drift: {relative} expected={expected} actual={actual}"
                )
            result.append({"path": relative, "sha256": actual})
    return result


def parse_tree() -> list[dict[str, str]]:
    entries = []
    for raw in TREE_LOCK.read_text(encoding="ascii").splitlines():
        fields = raw.split("\t")
        if len(fields) != 4:
            raise InstallationContractError("installed-tree.lock has a malformed row")
        kind, mode, identity, path = fields
        if kind not in {"file", "symlink"} or not re.fullmatch(r"[0-7]{3}", mode):
            raise InstallationContractError(f"installed-tree.lock has an invalid row: {raw}")
        parsed_path = PurePosixPath(path)
        if (
            not parsed_path.is_absolute()
            or parsed_path.parts[:3] != ("/", "usr", "local")
            or ".." in parsed_path.parts
            or parsed_path.as_posix() != path
        ):
            raise InstallationContractError(f"installed tree has an invalid path: {path}")
        if kind == "file" and not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise InstallationContractError(f"installed tree file identity is not SHA-256: {path}")
        if kind == "symlink" and (path, mode, identity) != ("/usr/local/man", "777", "share/man"):
            raise InstallationContractError(f"installed tree legacy symlink drift: {path}")
        entries.append({"kind": kind, "mode": mode, "identity": identity, "path": path})
    if len(entries) != 321:
        raise InstallationContractError(f"installed tree must contain 321 entries, found {len(entries)}")
    paths = [entry["path"] for entry in entries]
    if len(set(paths)) != len(entries):
        raise InstallationContractError("installed tree contains duplicate paths")
    if paths != sorted(paths):
        raise InstallationContractError("installed tree paths are not in lexicographic order")
    return entries


def group_for_path(path: str) -> tuple[str, str]:
    prefixes = (
        ("bin", "/usr/local/bin/"),
        ("config", "/usr/local/etc/lcovrc"),
        ("lib", "/usr/local/lib/lcov/lcovutil.pm"),
        ("man", "/usr/local/share/man/"),
        ("support_scripts", "/usr/local/share/lcov/support-scripts/"),
        ("html", "/usr/local/share/lcov/html/"),
        ("example", "/usr/local/share/lcov/example/"),
        ("tests", "/usr/local/share/lcov/tests/"),
        ("legacy_man_symlink", "/usr/local/man"),
    )
    matches = [
        (name, prefix)
        for name, prefix in prefixes
        if (path.startswith(prefix) if prefix.endswith("/") else path == prefix)
    ]
    if len(matches) != 1:
        raise InstallationContractError(f"installed path does not belong to exactly one group: {path}")
    return matches[0]


def installed_tree() -> dict[str, Any]:
    entries = parse_tree()
    groups = []
    grouped: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        name, prefix = group_for_path(entry["path"])
        grouped.setdefault(name, []).append(entry)
    for name, prefix, count, kinds, modes in EXPECTED_GROUPS:
        current = grouped.get(name, [])
        if len(current) != count:
            raise InstallationContractError(f"installed tree group {name} count drift")
        if {entry["kind"] for entry in current} != set(kinds):
            raise InstallationContractError(f"installed tree group {name} kind drift")
        if {entry["mode"] for entry in current} != set(modes):
            raise InstallationContractError(f"installed tree group {name} mode drift")
        raw = "\n".join(
            "\t".join((entry["kind"], entry["mode"], entry["identity"], entry["path"]))
            for entry in current
        ) + "\n"
        groups.append({
            "id": f"installation.tree.{name}",
            "name": name,
            "path_prefix": prefix,
            "entry_count": len(current),
            "kinds": sorted({entry["kind"] for entry in current}),
            "modes": sorted({entry["mode"] for entry in current}),
            "entries_sha256": sha256_bytes(raw.encode("ascii")),
        })
    if sum(group["entry_count"] for group in groups) != len(entries):
        raise InstallationContractError("installed tree groups are not exhaustive")
    mode_counts: dict[str, int] = {}
    for entry in entries:
        mode_counts[entry["mode"]] = mode_counts.get(entry["mode"], 0) + 1
    kind_counts: dict[str, int] = {}
    for entry in entries:
        kind_counts[entry["kind"]] = kind_counts.get(entry["kind"], 0) + 1
    return {
        "manifest_path": "compat/upstream/installed-tree.lock",
        "manifest_sha256": sha256_file(TREE_LOCK),
        "path_root": "/usr/local",
        "path_order": "lexicographic",
        "file_identity_algorithm": "sha256",
        "legacy_symlink": {
            "path": "/usr/local/man",
            "target": "share/man",
            "mode": "777",
        },
        "entry_count": len(entries),
        "file_count": kind_counts["file"],
        "symlink_count": kind_counts["symlink"],
        "mode_counts": mode_counts,
        "directory_entries_retained": False,
        "groups": groups,
    }


def planned_case_ids(upstream_root: Path) -> list[str]:
    path = ROOT / "specs/001-full-lcov-compatibility/callback-installation-contract.md"
    text = path.read_text(encoding="utf-8")
    start = text.index("### Support And Installation Cases")
    end = text.index("### `perl2lcov` Cases", start)
    found = []
    for identifier in re.findall(r"`(INST-[A-Z0-9-]+)`", text[start:end]):
        if identifier not in found:
            found.append(identifier)
    if tuple(found) != PLANNED_CASE_IDS:
        raise InstallationContractError(f"installation planned-case catalog drift: {found}")
    return found


def observed_runtime_assets(
    document: object,
    relative: str,
    expected_by_name: dict[str, dict[str, Any]],
) -> dict[str, dict[str, object]]:
    if not isinstance(document, list):
        raise InstallationContractError(f"asset sample is not a tree list: {relative}")
    observed: dict[str, dict[str, object]] = {}
    observed_paths = set()
    for entry in document:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if not isinstance(path, str) or not path.startswith("html/"):
            continue
        name = path.removeprefix("html/")
        if name not in expected_by_name:
            continue
        if path in observed_paths:
            raise InstallationContractError(f"duplicate runtime asset path: {relative}:{path}")
        observed_paths.add(path)
        observed[name] = {
            "bytes": entry.get("bytes"),
            "sha256": str(entry.get("sha256", "")).removeprefix("sha256:"),
            "status": entry.get("status"),
        }
    expected_observed = {
        name: {"bytes": asset["bytes"], "sha256": asset["sha256"], "status": "created"}
        for name, asset in expected_by_name.items()
    }
    if observed != expected_observed:
        raise InstallationContractError(f"runtime asset observation drift: {relative}")
    return observed


def validate_sample_metadata(relative: str, artifact_path: Path) -> tuple[str, str]:
    sample_relative = str(Path(relative).with_name("sample.json"))
    sample = load_json(ROOT / sample_relative)
    sample_id = Path(relative).parent.name
    expected_phase = "warmup" if "-warmup-" in sample_id else "measured"
    if (
        sample.get("case_id") != "report-genhtml-default"
        or sample.get("sample_id") != sample_id
        or sample.get("phase") != expected_phase
    ):
        raise InstallationContractError(f"runtime asset sample identity drift: {sample_relative}")
    artifacts = sample.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("output_tree"), dict):
        raise InstallationContractError(f"runtime asset sample artifacts drift: {sample_relative}")
    output_tree = artifacts["output_tree"]
    expected_artifact_path = artifact_path.relative_to(BENCHMARK_RESULT.parent).as_posix()
    if (
        output_tree.get("path") != expected_artifact_path
        or output_tree.get("bytes") != artifact_path.stat().st_size
        or str(output_tree.get("sha256", "")).removeprefix("sha256:") != sha256_file(artifact_path)
    ):
        raise InstallationContractError(f"runtime asset sample binding drift: {sample_relative}")
    return sample_relative, sha256_file(ROOT / sample_relative)


def runtime_assets() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assets = [
        {"id": identifier, "name": name, "kind": kind, "bytes": size, "sha256": digest}
        for identifier, name, kind, size, digest in EXPECTED_ASSETS
    ]
    expected_by_name = {asset["name"]: asset for asset in assets}
    observations = []
    asset_set = canonical_json(assets).encode("ascii")
    for relative in ASSET_SAMPLE_PATHS:
        artifact_path = ROOT / relative
        document = json.loads(artifact_path.read_text(encoding="utf-8"))
        observed = observed_runtime_assets(document, relative, expected_by_name)
        sample_path, sample_sha256 = validate_sample_metadata(relative, artifact_path)
        observations.append({
            "id": f"installation.asset-observation.{Path(relative).parent.name}",
            "artifact_path": relative,
            "artifact_sha256": sha256_file(artifact_path),
            "sample_metadata_path": sample_path,
            "sample_metadata_sha256": sample_sha256,
            "asset_set_sha256": sha256_bytes(asset_set),
            "asset_count": len(observed),
        })
    return assets, observations


def validate_oracle_manifest(tree: dict[str, Any]) -> dict[str, Any]:
    manifest = load_json(ORACLE_MANIFEST)
    if manifest.get("status") != "observed" or manifest.get("manifest_id") != "oracle-lcov-v2.5-image-smoke":
        raise InstallationContractError("installation Oracle manifest identity drift")
    if manifest.get("evidence", {}).get("scope") != "environment_smoke":
        raise InstallationContractError("installation Oracle manifest scope drift")
    if manifest.get("evidence", {}).get("inventory_entries") != []:
        raise InstallationContractError("installation Oracle manifest claims inventory evidence")
    installed = manifest.get("installed_tree", {})
    if installed.get("entries") != tree["entry_count"] or installed.get("manifest_sha256") != f"sha256:{tree['manifest_sha256']}":
        raise InstallationContractError("installation Oracle manifest tree binding drift")
    return {
        "manifest_id": manifest["manifest_id"],
        "status": manifest["status"],
        "evidence_scope": manifest["evidence"]["scope"],
        "product_compatibility_evidence": False,
    }


def validate_benchmark_result() -> dict[str, Any]:
    result = load_json(BENCHMARK_RESULT)
    if result.get("result_id") != "m0-oracle-baseline-oracle" or result.get("status") != "baseline_only":
        raise InstallationContractError("installation asset benchmark identity drift")
    correctness = result.get("correctness_gate", {})
    performance = result.get("performance_gate", {})
    if correctness.get("status") != "not_evaluated" or correctness.get("reason") != "candidate_not_available":
        raise InstallationContractError("installation asset correctness gate drift")
    if performance.get("status") != "not_evaluated" or performance.get("reason") != "candidate_not_available":
        raise InstallationContractError("installation asset performance gate drift")
    manifest = result.get("execution_manifest", {})
    if manifest.get("path") != "compat/manifests/oracle-lcov-v2.5-smoke.json":
        raise InstallationContractError("installation asset execution-manifest binding drift")
    if str(manifest.get("sha256", "")).removeprefix("sha256:") != sha256_file(ORACLE_MANIFEST):
        raise InstallationContractError("installation asset execution-manifest hash drift")
    return {
        "result_id": result["result_id"],
        "status": result["status"],
        "correctness_gate_status": correctness["status"],
        "performance_gate_status": performance["status"],
        "product_compatibility_evidence": False,
    }


def build_document(upstream_root: Path) -> dict[str, Any]:
    tree = installed_tree()
    assets, observations = runtime_assets()
    closures = [source_closure(upstream_root, value) for value in SOURCE_CLOSURES]
    return {
        "schema_version": 1,
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "scope": "LCOV 2.5 installation layout, build/failure boundaries, retained installed-tree evidence, and report asset references",
        "artifact_bindings": artifact_bindings(),
        "oracle_manifest": validate_oracle_manifest(tree),
        "benchmark_result": validate_benchmark_result(),
        "source_closures": closures,
        "installed_tree": tree,
        "layout_contract_ids": list(LAYOUT_IDS),
        "failure_contract_ids": list(FAILURE_IDS),
        "planned_case_ids": planned_case_ids(upstream_root),
        "planned_case_evidence_status": "planned",
        "planned_case_product_evidence": [],
        "runtime_assets": assets,
        "runtime_asset_observations": observations,
        "oracle_observation_evidence_status": "oracle_reference",
        "oracle_observation_product_evidence": [],
        "known_evidence_gaps": list(EVIDENCE_GAPS),
        "totals": {
            "artifact_bindings": (
                len(EXPECTED_ARTIFACT_HASHES)
                + len(EXPECTED_ASSET_SAMPLE_HASHES)
                + len(EXPECTED_SAMPLE_METADATA_HASHES)
            ),
            "source_closures": len(closures),
            "source_lines": sum(closure["line_count"] for closure in closures),
            "installed_tree_entries": tree["entry_count"],
            "installed_tree_groups": len(tree["groups"]),
            "layout_contract_ids": len(LAYOUT_IDS),
            "failure_contract_ids": len(FAILURE_IDS),
            "planned_cases": len(PLANNED_CASE_IDS),
            "runtime_assets": len(assets),
            "runtime_asset_observations": len(observations),
        },
        "product_compatibility_evidence": False,
    }


def validate_schema(document: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise InstallationContractError(f"installation schema is invalid: {error.message}") from error
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise InstallationContractError(f"installation schema failure at {location}: {errors[0].message}")


def validate_upstream_identity(upstream_root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip() != UPSTREAM_COMMIT:
        raise InstallationContractError("installation contract upstream commit mismatch")


def validate_document(document: dict[str, Any], upstream_root: Path) -> None:
    validate_schema(document)
    expected = build_document(upstream_root)
    for key in (
        "upstream_commit", "artifact_bindings", "oracle_manifest", "benchmark_result", "source_closures",
        "installed_tree", "layout_contract_ids", "failure_contract_ids", "planned_case_ids",
        "runtime_assets", "runtime_asset_observations", "known_evidence_gaps", "totals",
    ):
        if document[key] != expected[key]:
            raise InstallationContractError(f"installation contract drift: {key}")
    if document["planned_case_evidence_status"] != "planned" or document["planned_case_product_evidence"]:
        raise InstallationContractError("installation planned cases claim evidence")
    if document["oracle_observation_evidence_status"] != "oracle_reference" or document["oracle_observation_product_evidence"]:
        raise InstallationContractError("installation Oracle references claim product evidence")
    if document["product_compatibility_evidence"]:
        raise InstallationContractError("installation contract claims product compatibility")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, default=DEFAULT_UPSTREAM_ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    upstream_root = args.upstream_root.resolve()
    validate_upstream_identity(upstream_root)
    document = build_document(upstream_root)
    validate_document(document, upstream_root)
    content = canonical_json(document).encode("ascii")
    if args.write:
        OUTPUT_PATH.write_bytes(content)
        print(f"INSTALLATION_CONTRACT_WRITTEN path={OUTPUT_PATH.relative_to(ROOT)}")
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != content:
        raise InstallationContractError("committed installation contract differs from generation")
    print(
        "INSTALLATION_CONTRACT_OK "
        f"tree_entries={document['totals']['installed_tree_entries']} "
        f"groups={document['totals']['installed_tree_groups']} "
        f"source_closures={document['totals']['source_closures']} "
        f"planned_cases={document['totals']['planned_cases']} "
        f"runtime_assets={document['totals']['runtime_assets']} "
        f"asset_observations={document['totals']['runtime_asset_observations']} "
        "product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
