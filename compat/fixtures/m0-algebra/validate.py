#!/usr/bin/env python3
"""Validate the M0 model-algebra corpus, baseline, and independent expected facts."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import generate


ROOT = Path(__file__).resolve().parent
CASES_PATH = ROOT / "oracle-cases.json"
BASELINE_PATH = ROOT / "oracle-baseline.json"
FACTS_PATH = ROOT / "expected-facts.json"
MANIFEST_PATH = ROOT / "manifest.json"
INSPECTOR_PATH = ROOT / "inspect_algebra.pl"

BOUND_ROWS = {
    "M1-MD-010",
    "M1-MD-011",
    "M1-MD-012",
    "M1-MD-013",
    "M1-MD-014",
    "M1-MD-017",
    "M1-MD-019",
}
BLOCKED_IDS = ["M1-MD-020", "M1-TF-063", "M1-TF-064"]
REJECTED_VECTOR_CASES = {
    "md013-mcdc-vector.union.cli",
    "md013-mcdc-vector.union.semantic",
    "md013-mcdc-vector.intersect.cli",
    "md013-mcdc-vector.intersect.semantic",
}
ERROR_SIGNATURE = 'Can\'t call method "expression" on an undefined value'


class AlgebraValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError) as error:
        raise AlgebraValidationError(f"cannot load JSON: {path}: {error}") from error
    if not isinstance(document, dict):
        raise AlgebraValidationError(f"expected object: {path}")
    return document


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AlgebraValidationError(message)


def decode_stream(identity: dict[str, Any]) -> bytes:
    if "base64" in identity:
        return base64.b64decode(identity["base64"], validate=True)
    return b""


def validate_fixtures(cases_document: dict[str, Any]) -> None:
    fixtures = {item["id"]: item for item in cases_document["fixtures"]}
    require(len(fixtures) == len(cases_document["fixtures"]), "duplicate fixture ids")
    for item in cases_document["fixtures"]:
        path = ROOT / item["path"]
        require(path.is_file(), f"missing fixture {item['path']}")
        data = path.read_bytes()
        require(sha256_file(path) == item["sha256"], f"fixture hash drift: {item['path']}")
        require(len(data) == item["byte_size"], f"fixture size drift: {item['path']}")
        require(all(byte < 128 for byte in data), f"non-ASCII fixture: {item['path']}")
        require(data.endswith(b"\n"), f"fixture missing final LF: {item['path']}")


def validate_cases(cases_document: dict[str, Any]) -> None:
    require(cases_document.get("product_compatibility_evidence") is False, "product evidence must be false")
    require(cases_document.get("blocked_case_ids") == BLOCKED_IDS, "blocked ids drift")
    require(cases_document.get("fuzz_execution_phase") == "M1-only", "fuzz phase drift")
    oracle = cases_document["oracle"]
    require(oracle["docker_image_id"] == generate.ORACLE_IMAGE_ID, "oracle image id drift")
    require(oracle["program_sha256"] == generate.ORACLE_EXECUTABLE_SHA256, "oracle program hash drift")
    require(oracle["source_commit"] == generate.ORACLE_COMMIT, "oracle commit drift")

    cases = cases_document["cases"]
    ids = [case["id"] for case in cases]
    require(len(ids) == len(set(ids)), "duplicate case ids")
    observed_rows = {case["model_row"] for case in cases}
    require(BOUND_ROWS <= observed_rows, f"missing model rows: {sorted(BOUND_ROWS - observed_rows)}")
    require("M1-MD-020" not in observed_rows, "blocked M1-MD-020 must not have executable cases")

    for case in cases:
        case_id = case["id"]
        require(case.get("product_compatibility_evidence") is False, f"{case_id}: product evidence")
        require(case.get("ferricov_parity_status") == "blocked", f"{case_id}: parity must stay blocked")
        require(case.get("phase") == "oracle_baseline", f"{case_id}: phase")
        require(isinstance(case.get("expected_exit"), int), f"{case_id}: expected_exit type")
        require(isinstance(case.get("argv"), list) and case["argv"], f"{case_id}: argv")
        require(case.get("outcome_class") in {"success", "oracle_hard_error"}, f"{case_id}: outcome_class")
        if case_id in REJECTED_VECTOR_CASES:
            require(case["outcome_class"] == "oracle_hard_error", f"{case_id}: rejected class")
            require(case.get("error_signature") == ERROR_SIGNATURE, f"{case_id}: error signature")
            require(case["expected_exit"] != 0, f"{case_id}: rejected exit must be nonzero")
        else:
            require(case.get("outcome_class", "success") == "success", f"{case_id}: unexpected reject class")
            require(case["expected_exit"] == 0, f"{case_id}: success exit must be zero")
        if "left" in case:
            require((ROOT / case["left"]).is_file(), f"{case_id}: missing left")
            require(sha256_file(ROOT / case["left"]) == case["left_sha256"], f"{case_id}: left hash")
        if "right" in case:
            require((ROOT / case["right"]).is_file(), f"{case_id}: missing right")
            require(sha256_file(ROOT / case["right"]) == case["right_sha256"], f"{case_id}: right hash")
        if "input" in case:
            require((ROOT / case["input"]).is_file(), f"{case_id}: missing input")
            require(sha256_file(ROOT / case["input"]) == case["input_sha256"], f"{case_id}: input hash")


def validate_baseline(cases_document: dict[str, Any], baseline: dict[str, Any]) -> None:
    require(baseline.get("product_compatibility_evidence") is False, "baseline product evidence")
    require(baseline.get("blocked_case_ids") == BLOCKED_IDS, "baseline blocked ids")
    require(baseline["oracle"]["docker_image_id"] == generate.ORACLE_IMAGE_ID, "baseline image drift")
    require(
        baseline["oracle"]["program_sha256"] == generate.ORACLE_EXECUTABLE_SHA256,
        "baseline program drift",
    )
    cases_sha = sha256_file(CASES_PATH)
    require(baseline["cases_sha256"] == cases_sha, "baseline cases_sha256 drift")
    by_case = {case["id"]: case for case in cases_document["cases"]}
    require(len(baseline["cases"]) == len(by_case), "baseline case count drift")
    seen: set[str] = set()
    for observation in baseline["cases"]:
        case_id = observation["id"]
        require(case_id in by_case, f"unknown baseline case: {case_id}")
        require(case_id not in seen, f"duplicate baseline case: {case_id}")
        seen.add(case_id)
        expected = by_case[case_id]
        require(
            observation["exit_status"] == expected["expected_exit"],
            f"{case_id}: exit {observation['exit_status']} != expected {expected['expected_exit']}",
        )
        require(
            observation.get("product_compatibility_evidence") is False,
            f"{case_id}: observation product evidence",
        )
        for stream in ("stdout", "stderr"):
            require(stream in observation, f"{case_id}: missing {stream}")
            require("sha256" in observation[stream], f"{case_id}: missing {stream} sha256")
            require("byte_size" in observation[stream], f"{case_id}: missing {stream} size")
            data = decode_stream(observation[stream])
            if data:
                require(
                    hashlib.sha256(data).hexdigest() == observation[stream]["sha256"],
                    f"{case_id}: {stream} base64/hash mismatch",
                )
                require(
                    len(data) == observation[stream]["byte_size"],
                    f"{case_id}: {stream} base64/size mismatch",
                )
        if expected.get("outcome_class") == "oracle_hard_error":
            require(observation["output"].get("exists") is False, f"{case_id}: rejected output exists")
            err = decode_stream(observation["stderr"]).decode("utf-8", "replace")
            require(
                expected["error_signature"] in err,
                f"{case_id}: missing error signature in stderr",
            )
        elif expected.get("output_file"):
            require("output" in observation, f"{case_id}: missing output")
            if observation["exit_status"] == 0:
                require(observation["output"].get("exists") is True, f"{case_id}: output missing")
                require(observation["output"].get("sha256"), f"{case_id}: output hash missing")
        for key in ("left_sha256", "right_sha256", "input_sha256"):
            if key in expected:
                require(observation.get(key) == expected[key], f"{case_id}: {key} drift")
        # Argv binding: observation argv must match case argv exactly.
        require(observation.get("argv") == expected["argv"], f"{case_id}: argv drift")


def validate_facts(cases_document: dict[str, Any], baseline: dict[str, Any], facts: dict[str, Any]) -> None:
    require(facts.get("product_compatibility_evidence") is False, "facts product evidence")
    require(facts.get("oracle_image_id") == generate.ORACLE_IMAGE_ID, "facts image drift")
    require(
        facts.get("oracle_program_sha256") == generate.ORACLE_EXECUTABLE_SHA256,
        "facts program drift",
    )
    require(facts.get("oracle_source_commit") == generate.ORACLE_COMMIT, "facts commit drift")
    require(facts.get("cases_sha256") == sha256_file(CASES_PATH), "facts cases_sha256 drift")
    require(len(facts["cases"]) == len(baseline["cases"]), "facts case count drift")
    by_obs = {item["id"]: item for item in baseline["cases"]}
    by_case = {item["id"]: item for item in cases_document["cases"]}
    for fact in facts["cases"]:
        observation = by_obs[fact["id"]]
        case = by_case[fact["id"]]
        require(fact["exit_status"] == observation["exit_status"], f"{fact['id']}: fact exit")
        require(fact["expected_exit"] == case["expected_exit"], f"{fact['id']}: fact expected_exit")
        require(fact["stdout_sha256"] == observation["stdout"]["sha256"], f"{fact['id']}: stdout fact")
        require(fact["stderr_sha256"] == observation["stderr"]["sha256"], f"{fact['id']}: stderr fact")
        require(
            fact["output_exists"] == observation["output"].get("exists", False),
            f"{fact['id']}: output exists fact",
        )
        if fact["output_exists"]:
            require(
                fact["output_sha256"] == observation["output"]["sha256"],
                f"{fact['id']}: output hash fact",
            )
        require(
            fact["stdout_byte_size"] == observation["stdout"]["byte_size"],
            f"{fact['id']}: stdout size",
        )
        require(fact.get("argv") == case["argv"], f"{fact['id']}: argv fact")
        require(fact.get("runner") == case["runner"], f"{fact['id']}: runner fact")
        require(
            any(
                fact.get(key)
                for key in ("left_sha256", "right_sha256", "input_sha256", "operand_sha256")
            ),
            f"{fact['id']}: missing independent operand binding",
        )
        if case.get("outcome_class") == "oracle_hard_error":
            require(fact.get("error_signature") == ERROR_SIGNATURE, f"{fact['id']}: fact signature")
            require(fact["output_exists"] is False, f"{fact['id']}: rejected fact output")
            require(fact["exit_status"] != 0, f"{fact['id']}: rejected fact exit")


def validate_generation_roundtrip() -> None:
    generated_cases = generate.build_cases_document()
    committed_cases = load_json(CASES_PATH)
    require(
        json.dumps(generated_cases, sort_keys=True) == json.dumps(committed_cases, sort_keys=True),
        "oracle-cases.json drifted from generator",
    )
    generated_manifest = generate.build_manifest()
    committed_manifest = load_json(MANIFEST_PATH)
    require(
        json.dumps(generated_manifest, sort_keys=True)
        == json.dumps(committed_manifest, sort_keys=True),
        "manifest.json drifted from generator",
    )
    require(INSPECTOR_PATH.is_file(), "missing inspect_algebra.pl")
    require(INSPECTOR_PATH.stat().st_size > 0, "empty inspect_algebra.pl")


def mutate_and_reject(
    document: dict[str, Any],
    mutator,
    *,
    label: str,
    validator,
) -> None:
    mutated = copy.deepcopy(document)
    mutator(mutated)
    try:
        validator(mutated)
    except AlgebraValidationError:
        return
    raise AlgebraValidationError(f"mutation not rejected: {label}")


def reverse_mutation_suite(
    cases_document: dict[str, Any],
    baseline: dict[str, Any],
    facts: dict[str, Any],
) -> None:
    # Fixture hash drift.
    def fixture_hash(doc: dict[str, Any]) -> None:
        doc["fixtures"][0]["sha256"] = "0" * 64

    mutate_and_reject(
        cases_document,
        fixture_hash,
        label="fixture hash",
        validator=validate_fixtures,
    )

    # Product evidence promotion.
    def product_flag(doc: dict[str, Any]) -> None:
        doc["product_compatibility_evidence"] = True

    mutate_and_reject(
        cases_document,
        product_flag,
        label="product evidence",
        validator=validate_cases,
    )

    # Blocked id removal.
    def blocked_pop(doc: dict[str, Any]) -> None:
        doc["blocked_case_ids"] = list(doc["blocked_case_ids"])[:-1]

    mutate_and_reject(
        cases_document,
        blocked_pop,
        label="blocked ids",
        validator=validate_cases,
    )

    # Argv swap between two cases in baseline validation.
    def argv_swap(doc: dict[str, Any]) -> None:
        first, second = doc["cases"][0], doc["cases"][1]
        first["argv"], second["argv"] = second["argv"], first["argv"]

    mutate_and_reject(
        baseline,
        argv_swap,
        label="argv swap",
        validator=lambda doc: validate_baseline(cases_document, doc),
    )

    # Exit status mutation.
    def exit_flip(doc: dict[str, Any]) -> None:
        doc["cases"][0]["exit_status"] = 99

    mutate_and_reject(
        baseline,
        exit_flip,
        label="exit flip",
        validator=lambda doc: validate_baseline(cases_document, doc),
    )

    # Output hash mutation for a success case with output.
    def output_hash(doc: dict[str, Any]) -> None:
        for observation in doc["cases"]:
            if observation["output"].get("exists"):
                observation["output"]["sha256"] = "0" * 64
                break

    # Output hash is checked via facts, not baseline alone; mutate facts.
    def fact_output_hash(doc: dict[str, Any]) -> None:
        for fact in doc["cases"]:
            if fact.get("output_exists"):
                fact["output_sha256"] = "0" * 64
                break

    mutate_and_reject(
        facts,
        fact_output_hash,
        label="fact output hash",
        validator=lambda doc: validate_facts(cases_document, baseline, doc),
    )

    # Rejected-case success wash.
    def wash_reject(doc: dict[str, Any]) -> None:
        for case in doc["cases"]:
            if case["id"] in REJECTED_VECTOR_CASES:
                case["expected_exit"] = 0
                case["outcome_class"] = "success"
                case.pop("error_signature", None)

    mutate_and_reject(
        cases_document,
        wash_reject,
        label="reject wash",
        validator=validate_cases,
    )

    # Image identity drift in facts.
    def image_drift(doc: dict[str, Any]) -> None:
        doc["oracle_image_id"] = "sha256:" + "0" * 64

    mutate_and_reject(
        facts,
        image_drift,
        label="facts image",
        validator=lambda doc: validate_facts(cases_document, baseline, doc),
    )

    # Operand hash drift in facts.
    def operand_drift(doc: dict[str, Any]) -> None:
        for fact in doc["cases"]:
            if fact.get("left_sha256"):
                fact["left_sha256"] = "0" * 64
                break

    # left_sha256 is compared only when present in observation; force mismatch via baseline path.
    def baseline_left_drift(doc: dict[str, Any]) -> None:
        for observation in doc["cases"]:
            if observation.get("left_sha256"):
                observation["left_sha256"] = "0" * 64
                break

    mutate_and_reject(
        baseline,
        baseline_left_drift,
        label="left operand hash",
        validator=lambda doc: validate_baseline(cases_document, doc),
    )

    # Independent facts must not equal baseline self-hash alone.
    require(sha256_file(FACTS_PATH) != sha256_file(BASELINE_PATH), "facts/baseline identity collapse")


def validate_all(*, mutations: bool = True) -> None:
    validate_generation_roundtrip()
    cases_document = load_json(CASES_PATH)
    baseline = load_json(BASELINE_PATH)
    facts = load_json(FACTS_PATH)
    validate_fixtures(cases_document)
    validate_cases(cases_document)
    validate_baseline(cases_document, baseline)
    validate_facts(cases_document, baseline, facts)
    if mutations:
        reverse_mutation_suite(cases_document, baseline, facts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-mutations", action="store_true")
    args = parser.parse_args()
    try:
        validate_all(mutations=not args.skip_mutations)
    except AlgebraValidationError as error:
        print(f"algebra validation failed: {error}", file=sys.stderr)
        return 1
    print("m0-algebra validation ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
