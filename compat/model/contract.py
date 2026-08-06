#!/usr/bin/env python3
"""Generate and validate the fail-closed M0 coverage-model algebra contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).with_name("v2.5.json")
SCHEMA_PATH = ROOT / "compat/schema/model-contract.schema.json"
CORPUS_ROOT = ROOT / "compat/fixtures/m0-algebra"
CASES_PATH = CORPUS_ROOT / "oracle-cases.json"
BASELINE_PATH = CORPUS_ROOT / "oracle-baseline.json"
FACTS_PATH = CORPUS_ROOT / "expected-facts.json"
SEALED_PATH = CORPUS_ROOT / "sealed-observation-facts.json"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"
INSPECTOR_PATH = CORPUS_ROOT / "inspect_algebra.pl"
ORACLE_MANIFEST = ROOT / "compat/manifests/oracle-lcov-v2.5-smoke.json"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
EXPECTED_IMAGE_SHA256 = (
    "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
)
EXPECTED_LCOV_SHA256 = (
    "sha256:d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252"
)
BOUND_ROWS = (
    "M1-MD-010",
    "M1-MD-011",
    "M1-MD-012",
    "M1-MD-013",
    "M1-MD-014",
    "M1-MD-017",
    "M1-MD-019",
)
BLOCKED_IDS = ("M1-MD-020", "M1-TF-063", "M1-TF-064")
HARNESS_PATHS = (
    ROOT / "compat/model/contract.py",
    ROOT / "compat/fixtures/m0-algebra/generate.py",
    ROOT / "compat/fixtures/m0-algebra/capture_oracle.py",
    ROOT / "compat/fixtures/m0-algebra/validate.py",
    ROOT / "compat/fixtures/m0-algebra/inspect_algebra.pl",
    ROOT / "compat/schema/model-contract.schema.json",
)


class ModelContractError(RuntimeError):
    pass


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError) as error:
        raise ModelContractError(f"cannot load JSON: {path}") from error
    if not isinstance(document, dict):
        raise ModelContractError(f"expected JSON object: {path}")
    return document


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_binding(relative: str) -> dict[str, str]:
    path = ROOT / relative
    if not path.is_file():
        raise ModelContractError(f"missing artifact: {relative}")
    return {"path": relative, "sha256": sha256_file(path)}


def oracle_identity() -> dict[str, Any]:
    manifest = load_json(ORACLE_MANIFEST)
    if (
        manifest.get("status") != "observed"
        or manifest.get("manifest_id") != "oracle-lcov-v2.5-image-smoke"
    ):
        raise ModelContractError("model Oracle manifest identity drift")
    image = manifest.get("image", {})
    if (
        image.get("docker_image_id") != EXPECTED_IMAGE_SHA256
        or image.get("labels", {}).get("org.opencontainers.image.revision")
        != UPSTREAM_COMMIT
    ):
        raise ModelContractError("model Oracle image identity drift")
    executables = manifest.get("executables", [])
    lcov_entries = [entry for entry in executables if entry.get("name") == "lcov"]
    if len(lcov_entries) != 1 or lcov_entries[0].get("sha256") != EXPECTED_LCOV_SHA256:
        raise ModelContractError("model Oracle lcov identity drift")
    execution = manifest.get("execution", {})
    if execution.get("network") != "none":
        raise ModelContractError("model Oracle execution network drift")
    return {
        "manifest_path": "compat/manifests/oracle-lcov-v2.5-smoke.json",
        "manifest_sha256": sha256_file(ORACLE_MANIFEST),
        "manifest_id": manifest["manifest_id"],
        "image_sha256": EXPECTED_IMAGE_SHA256,
        "lcov_path": lcov_entries[0]["path"],
        "lcov_sha256": EXPECTED_LCOV_SHA256,
        "user": execution.get("user", "root"),
        "network": "none",
        "product_compatibility_evidence": False,
    }


def build_document() -> dict[str, Any]:
    cases_document = load_json(CASES_PATH)
    baseline = load_json(BASELINE_PATH)
    facts = load_json(FACTS_PATH)
    if cases_document.get("product_compatibility_evidence") is not False:
        raise ModelContractError("cases document claims product evidence")
    if baseline.get("product_compatibility_evidence") is not False:
        raise ModelContractError("baseline claims product evidence")
    if facts.get("product_compatibility_evidence") is not False:
        raise ModelContractError("facts claim product evidence")
    if list(cases_document.get("blocked_case_ids", [])) != list(BLOCKED_IDS):
        raise ModelContractError("cases blocked ids drift")
    if list(baseline.get("blocked_case_ids", [])) != list(BLOCKED_IDS):
        raise ModelContractError("baseline blocked ids drift")

    model_rows = cases_document.get("model_rows")
    if not isinstance(model_rows, list) or len(model_rows) != 8:
        raise ModelContractError("model_rows must contain eight entries")
    bound = [row["id"] for row in model_rows if row.get("status") == "oracle_bound"]
    if bound != list(BOUND_ROWS):
        raise ModelContractError(f"bound rows drift: {bound}")

    executable_bindings = []
    for case in cases_document["cases"]:
        executable_bindings.append(
            {
                "id": case["id"],
                "model_row": case["model_row"],
                "binding_ids": list(case["binding_ids"]),
                "runner": case["runner"],
                "phase": case["phase"],
                "expected_exit": case["expected_exit"],
                "ferricov_parity_status": case["ferricov_parity_status"],
            }
        )

    artifact_paths = (
        "compat/fixtures/m0-algebra/oracle-cases.json",
        "compat/fixtures/m0-algebra/oracle-baseline.json",
        "compat/fixtures/m0-algebra/expected-facts.json",
        "compat/fixtures/m0-algebra/sealed-observation-facts.json",
        "compat/fixtures/m0-algebra/manifest.json",
        "compat/fixtures/m0-algebra/inspect_algebra.pl",
        "compat/model/m1-model.json",
    )
    return {
        "schema_version": 1,
        "contract_id": "m0-model-algebra-v1",
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "scope": (
            "Executable M0 Oracle coverage-model algebra and property evidence for "
            "M1-MD-010..014, M1-MD-017, and M1-MD-019 against the pinned LCOV v2.5 image."
        ),
        "oracle_identity": oracle_identity(),
        "artifact_bindings": [artifact_binding(path) for path in artifact_paths],
        "model_rows": model_rows,
        "bound_case_ids": list(BOUND_ROWS),
        "blocked_case_ids": list(BLOCKED_IDS),
        "executable_bindings": executable_bindings,
        "fixture_count": len(cases_document["fixtures"]),
        "case_count": len(cases_document["cases"]),
        "observation_count": len(baseline["cases"]),
        "fuzz_execution_phase": "M1-only",
        "product_compatibility_evidence": False,
        "independent_facts_path": "compat/fixtures/m0-algebra/expected-facts.json",
        "harness_artifacts": [
            {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
            for path in HARNESS_PATHS
        ],
    }


def validate_document(document: dict[str, Any]) -> None:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(document)
    except (OSError, json.JSONDecodeError, SchemaError, Exception) as error:
        raise ModelContractError(f"schema validation failed: {error}") from error

    expected = build_document()
    if canonical_json(document) != canonical_json(expected):
        raise ModelContractError("committed model contract drifted from generation")
    if document["product_compatibility_evidence"] is not False:
        raise ModelContractError("product compatibility evidence must remain false")
    if document["blocked_case_ids"] != list(BLOCKED_IDS):
        raise ModelContractError("blocked case ids drifted")
    if document["bound_case_ids"] != list(BOUND_ROWS):
        raise ModelContractError("bound case ids drifted")
    if document["case_count"] != document["observation_count"]:
        raise ModelContractError("case/observation count mismatch")
    if document["fuzz_execution_phase"] != "M1-only":
        raise ModelContractError("fuzz execution phase must remain M1-only")

    # Fail closed on self-hash-only acceptance: sealed projection, independent facts,
    # and raw baseline must all exist as distinct documents.
    if not FACTS_PATH.is_file() or FACTS_PATH.stat().st_size < 32:
        raise ModelContractError("independent expected facts missing")
    if not SEALED_PATH.is_file() or SEALED_PATH.stat().st_size < 32:
        raise ModelContractError("sealed observation facts missing")
    if not BASELINE_PATH.is_file() or BASELINE_PATH.stat().st_size < 32:
        raise ModelContractError("oracle baseline missing")
    if sha256_file(FACTS_PATH) == sha256_file(BASELINE_PATH):
        raise ModelContractError("facts and baseline must be independent documents")
    if sha256_file(SEALED_PATH) == sha256_file(BASELINE_PATH):
        raise ModelContractError("sealed projection and baseline must be independent")
    if sha256_file(SEALED_PATH) == sha256_file(FACTS_PATH):
        raise ModelContractError("sealed projection and facts must be independent")
    facts = load_json(FACTS_PATH)
    sealed_sha = sha256_file(SEALED_PATH)
    if facts.get("sealed_observation_facts_sha256") != sealed_sha:
        raise ModelContractError("facts do not bind sealed observation projection hash")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        document = build_document()
        if args.write:
            OUTPUT_PATH.write_text(canonical_json(document), encoding="ascii")
            print(f"wrote {OUTPUT_PATH}")
            return 0
        if not OUTPUT_PATH.is_file():
            raise ModelContractError(f"missing committed contract: {OUTPUT_PATH}")
        committed = load_json(OUTPUT_PATH)
        validate_document(committed)
    except ModelContractError as error:
        print(f"model contract failed: {error}", file=sys.stderr)
        return 1
    print(
        "model contract ok "
        f"bound={len(document['bound_case_ids'])} "
        f"cases={document['case_count']} "
        f"fixtures={document['fixture_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
