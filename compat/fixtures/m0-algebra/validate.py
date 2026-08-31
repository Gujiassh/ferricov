#!/usr/bin/env python3
"""Validate the M0 model-algebra corpus against a trusted sealed observation projection."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

import generate


ROOT = Path(__file__).resolve().parent
CASES_PATH = ROOT / "oracle-cases.json"
BASELINE_PATH = ROOT / "oracle-baseline.json"
FACTS_PATH = ROOT / "expected-facts.json"
SEALED_PATH = ROOT / "sealed-observation-facts.json"
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

IDENTITY_FIELDS = (
    "model_row",
    "binding_ids",
    "runner",
    "op",
    "output_file",
    "expected_exit",
    "outcome_class",
    "argv",
    "capture_mode",
)


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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AlgebraValidationError(message)


def decode_stream(identity: dict[str, Any]) -> bytes:
    if "base64" in identity:
        return base64.b64decode(identity["base64"], validate=True)
    return b""


def json_equal(left: Any, right: Any) -> bool:
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, sort_keys=True, separators=(",", ":")
    )


def expected_operand_map(case: dict[str, Any]) -> dict[str, str]:
    operand: dict[str, str] = {}
    if case.get("left_sha256"):
        operand["left.info"] = case["left_sha256"]
    if case.get("right_sha256"):
        operand["right.info"] = case["right_sha256"]
    if case.get("input_sha256"):
        operand["input.info"] = case["input_sha256"]
    return operand


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


def validate_sealed(cases_document: dict[str, Any], sealed: dict[str, Any]) -> None:
    require(SEALED_PATH.is_file(), "missing sealed-observation-facts.json")
    require(sealed.get("product_compatibility_evidence") is False, "sealed product evidence")
    require(sealed.get("oracle_image_id") == generate.ORACLE_IMAGE_ID, "sealed image drift")
    require(
        sealed.get("oracle_program_sha256") == generate.ORACLE_EXECUTABLE_SHA256,
        "sealed program drift",
    )
    require(sealed.get("oracle_source_commit") == generate.ORACLE_COMMIT, "sealed commit drift")
    require(sealed.get("case_count") == len(sealed["cases"]), "sealed case_count drift")
    by_case = {case["id"]: case for case in cases_document["cases"]}
    require(len(sealed["cases"]) == len(by_case), "sealed case count mismatch")
    seen: set[str] = set()
    for entry in sealed["cases"]:
        case_id = entry["id"]
        require(case_id in by_case, f"unknown sealed case: {case_id}")
        require(case_id not in seen, f"duplicate sealed case: {case_id}")
        seen.add(case_id)
        case = by_case[case_id]
        for field in IDENTITY_FIELDS:
            require(
                json_equal(entry.get(field), case.get(field)),
                f"{case_id}: sealed {field} drift from case catalog",
            )
        for key in ("left_sha256", "right_sha256", "input_sha256", "left", "right", "input"):
            require(entry.get(key) == case.get(key), f"{case_id}: sealed {key} drift")
        expected_operand = expected_operand_map(case)
        require(
            json_equal(entry.get("operand_sha256"), expected_operand),
            f"{case_id}: sealed operand_sha256 drift",
        )
        require(isinstance(entry.get("stdout_sha256"), str) and len(entry["stdout_sha256"]) == 64,
                f"{case_id}: sealed stdout digest")
        require(isinstance(entry.get("stderr_sha256"), str) and len(entry["stderr_sha256"]) == 64,
                f"{case_id}: sealed stderr digest")
        require(entry.get("exit_status") == case["expected_exit"], f"{case_id}: sealed exit")
        if case.get("outcome_class") == "oracle_hard_error":
            require(entry.get("error_signature") == ERROR_SIGNATURE, f"{case_id}: sealed signature")
            require(entry.get("output_exists") is False, f"{case_id}: sealed rejected output")
            require(entry["exit_status"] != 0, f"{case_id}: sealed rejected exit")
        if case.get("capture_mode") in {"semantic", "rewrite_semantic"} and case["expected_exit"] == 0:
            require(
                entry.get("semantic_snapshot_sha256") == entry["stdout_sha256"],
                f"{case_id}: sealed semantic digest",
            )
        else:
            require(entry.get("semantic_snapshot_sha256") in {None}, f"{case_id}: unexpected semantic digest")


def validate_baseline(
    cases_document: dict[str, Any],
    baseline: dict[str, Any],
    sealed: dict[str, Any],
) -> None:
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
    by_sealed = {entry["id"]: entry for entry in sealed["cases"]}
    require(len(baseline["cases"]) == len(by_case), "baseline case count drift")
    seen: set[str] = set()
    for observation in baseline["cases"]:
        case_id = observation["id"]
        require(case_id in by_case, f"unknown baseline case: {case_id}")
        require(case_id in by_sealed, f"missing sealed projection: {case_id}")
        require(case_id not in seen, f"duplicate baseline case: {case_id}")
        seen.add(case_id)
        expected = by_case[case_id]
        trusted = by_sealed[case_id]
        # Identity fields against sealed projection (not mutable baseline self-hash alone).
        for field in ("model_row", "binding_ids", "runner", "op", "output_file", "argv"):
            require(
                json_equal(observation.get(field), trusted.get(field)),
                f"{case_id}: observation {field} drift from sealed",
            )
        require(
            observation["exit_status"] == trusted["exit_status"],
            f"{case_id}: exit {observation['exit_status']} != sealed {trusted['exit_status']}",
        )
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
            if "base64" in observation[stream]:
                require(
                    sha256_bytes(data) == observation[stream]["sha256"],
                    f"{case_id}: {stream} base64/hash mismatch",
                )
                require(
                    len(data) == observation[stream]["byte_size"],
                    f"{case_id}: {stream} base64/size mismatch",
                )
            require(
                observation[stream]["sha256"] == trusted[f"{stream}_sha256"],
                f"{case_id}: {stream} digest drift from sealed",
            )
            require(
                observation[stream]["byte_size"] == trusted[f"{stream}_byte_size"],
                f"{case_id}: {stream} size drift from sealed",
            )
        require(
            observation["output"].get("exists", False) == trusted["output_exists"],
            f"{case_id}: output exists drift from sealed",
        )
        if trusted["output_exists"]:
            require(
                observation["output"].get("sha256") == trusted["output_sha256"],
                f"{case_id}: output digest drift from sealed",
            )
            require(
                observation["output"].get("byte_size") == trusted["output_byte_size"],
                f"{case_id}: output size drift from sealed",
            )
            if "base64" in observation["output"]:
                data = decode_stream(observation["output"])
                require(
                    sha256_bytes(data) == trusted["output_sha256"],
                    f"{case_id}: output base64/hash mismatch vs sealed",
                )
        if trusted.get("outcome_class") == "oracle_hard_error":
            require(observation["output"].get("exists") is False, f"{case_id}: rejected output exists")
            err = decode_stream(observation["stderr"]).decode("utf-8", "replace")
            require(
                trusted["error_signature"] in err,
                f"{case_id}: missing error signature in stderr",
            )
        # Operand fixture hashes and materialized operand map against sealed.
        for key in ("left_sha256", "right_sha256", "input_sha256"):
            require(observation.get(key) == trusted.get(key), f"{case_id}: {key} drift from sealed")
        require(
            json_equal(observation.get("operand_sha256") or {}, trusted.get("operand_sha256") or {}),
            f"{case_id}: operand_sha256 drift from sealed",
        )
        expected_operand = expected_operand_map(expected)
        require(
            json_equal(observation.get("operand_sha256") or {}, expected_operand),
            f"{case_id}: operand_sha256 drift from case catalog",
        )
        # Successful semantic snapshots bind sealed semantic digest.
        if trusted.get("semantic_snapshot_sha256"):
            require(
                observation["stdout"]["sha256"] == trusted["semantic_snapshot_sha256"],
                f"{case_id}: semantic snapshot digest drift",
            )
            raw = decode_stream(observation["stdout"])
            try:
                document = json.loads(raw.decode("ascii"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AlgebraValidationError(f"{case_id}: semantic snapshot not ASCII JSON: {error}") from error
            require(isinstance(document, dict), f"{case_id}: semantic snapshot root")


def validate_facts(
    cases_document: dict[str, Any],
    baseline: dict[str, Any],
    facts: dict[str, Any],
    sealed: dict[str, Any],
) -> None:
    require(facts.get("product_compatibility_evidence") is False, "facts product evidence")
    require(facts.get("oracle_image_id") == generate.ORACLE_IMAGE_ID, "facts image drift")
    require(
        facts.get("oracle_program_sha256") == generate.ORACLE_EXECUTABLE_SHA256,
        "facts program drift",
    )
    require(facts.get("oracle_source_commit") == generate.ORACLE_COMMIT, "facts commit drift")
    require(facts.get("cases_sha256") == sha256_file(CASES_PATH), "facts cases_sha256 drift")
    sealed_sha = sha256_file(SEALED_PATH)
    require(
        facts.get("sealed_observation_facts_sha256") == sealed_sha,
        "facts sealed projection hash drift",
    )
    require(len(facts["cases"]) == len(sealed["cases"]), "facts case count drift")
    by_obs = {item["id"]: item for item in baseline["cases"]}
    by_case = {item["id"]: item for item in cases_document["cases"]}
    by_sealed = {item["id"]: item for item in sealed["cases"]}
    for fact in facts["cases"]:
        case_id = fact["id"]
        observation = by_obs[case_id]
        case = by_case[case_id]
        trusted = by_sealed[case_id]
        # Facts must match sealed projection first (trusted independent source).
        for field in (
            "model_row",
            "binding_ids",
            "runner",
            "op",
            "output_file",
            "argv",
            "capture_mode",
            "outcome_class",
            "expected_exit",
            "exit_status",
            "stdout_sha256",
            "stdout_byte_size",
            "stderr_sha256",
            "stderr_byte_size",
            "output_exists",
            "output_sha256",
            "output_byte_size",
            "left_sha256",
            "right_sha256",
            "input_sha256",
            "operand_sha256",
            "semantic_snapshot_sha256",
        ):
            require(
                json_equal(fact.get(field), trusted.get(field)),
                f"{case_id}: fact {field} drift from sealed",
            )
        if "error_signature" in trusted:
            require(fact.get("error_signature") == trusted["error_signature"], f"{case_id}: fact signature")
        # Then facts must still match baseline observation streams/operands.
        require(fact["exit_status"] == observation["exit_status"], f"{case_id}: fact exit vs baseline")
        require(fact["stdout_sha256"] == observation["stdout"]["sha256"], f"{case_id}: stdout fact vs baseline")
        require(fact["stderr_sha256"] == observation["stderr"]["sha256"], f"{case_id}: stderr fact vs baseline")
        require(
            fact["output_exists"] == observation["output"].get("exists", False),
            f"{case_id}: output exists fact vs baseline",
        )
        if fact["output_exists"]:
            require(
                fact["output_sha256"] == observation["output"]["sha256"],
                f"{case_id}: output hash fact vs baseline",
            )
        require(fact.get("argv") == case["argv"], f"{case_id}: argv fact vs catalog")
        require(fact.get("runner") == case["runner"], f"{case_id}: runner fact vs catalog")
        require(fact.get("model_row") == case["model_row"], f"{case_id}: model_row fact vs catalog")
        require(
            json_equal(fact.get("binding_ids"), case.get("binding_ids")),
            f"{case_id}: binding_ids fact vs catalog",
        )
        require(fact.get("op") == case.get("op"), f"{case_id}: op fact vs catalog")
        require(fact.get("output_file") == case.get("output_file"), f"{case_id}: output_file fact vs catalog")
        require(
            json_equal(fact.get("operand_sha256"), expected_operand_map(case)),
            f"{case_id}: operand fact vs catalog",
        )
        require(
            any(
                fact.get(key)
                for key in ("left_sha256", "right_sha256", "input_sha256", "operand_sha256")
            ),
            f"{case_id}: missing independent operand binding",
        )
        if case.get("outcome_class") == "oracle_hard_error":
            require(fact.get("error_signature") == ERROR_SIGNATURE, f"{case_id}: fact signature fixed")
            require(fact["output_exists"] is False, f"{case_id}: rejected fact output")
            require(fact["exit_status"] != 0, f"{case_id}: rejected fact exit")


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
    mutator: Callable[[dict[str, Any]], None],
    *,
    label: str,
    validator: Callable[[dict[str, Any]], None],
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
    sealed: dict[str, Any],
) -> None:
    def fixture_hash(doc: dict[str, Any]) -> None:
        doc["fixtures"][0]["sha256"] = "0" * 64

    mutate_and_reject(
        cases_document,
        fixture_hash,
        label="fixture hash",
        validator=validate_fixtures,
    )

    def product_flag(doc: dict[str, Any]) -> None:
        doc["product_compatibility_evidence"] = True

    mutate_and_reject(
        cases_document,
        product_flag,
        label="product evidence",
        validator=validate_cases,
    )

    def blocked_pop(doc: dict[str, Any]) -> None:
        doc["blocked_case_ids"] = list(doc["blocked_case_ids"])[:-1]

    mutate_and_reject(
        cases_document,
        blocked_pop,
        label="blocked ids",
        validator=validate_cases,
    )

    def argv_swap(doc: dict[str, Any]) -> None:
        first, second = doc["cases"][0], doc["cases"][1]
        first["argv"], second["argv"] = second["argv"], first["argv"]

    mutate_and_reject(
        baseline,
        argv_swap,
        label="argv swap",
        validator=lambda doc: validate_baseline(cases_document, doc, sealed),
    )

    def exit_flip(doc: dict[str, Any]) -> None:
        doc["cases"][0]["exit_status"] = 99

    mutate_and_reject(
        baseline,
        exit_flip,
        label="exit flip",
        validator=lambda doc: validate_baseline(cases_document, doc, sealed),
    )

    def fact_output_hash(doc: dict[str, Any]) -> None:
        for fact in doc["cases"]:
            if fact.get("output_exists"):
                fact["output_sha256"] = "0" * 64
                break

    mutate_and_reject(
        facts,
        fact_output_hash,
        label="fact output hash",
        validator=lambda doc: validate_facts(cases_document, baseline, doc, sealed),
    )

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

    def image_drift(doc: dict[str, Any]) -> None:
        doc["oracle_image_id"] = "sha256:" + "0" * 64

    mutate_and_reject(
        facts,
        image_drift,
        label="facts image",
        validator=lambda doc: validate_facts(cases_document, baseline, doc, sealed),
    )

    def baseline_left_drift(doc: dict[str, Any]) -> None:
        for observation in doc["cases"]:
            if observation.get("left_sha256"):
                observation["left_sha256"] = "0" * 64
                break

    mutate_and_reject(
        baseline,
        baseline_left_drift,
        label="left operand hash",
        validator=lambda doc: validate_baseline(cases_document, doc, sealed),
    )

    # Coordinated baseline+facts stdout mutation still rejected by sealed projection.
    def coordinated_stdout_mutation() -> None:
        mutated_baseline = copy.deepcopy(baseline)
        mutated_facts = copy.deepcopy(facts)
        target = next(
            observation
            for observation in mutated_baseline["cases"]
            if observation["exit_status"] == 0 and observation["stdout"]["byte_size"] > 0
        )
        case_id = target["id"]
        fake = "1" * 64
        target["stdout"]["sha256"] = fake
        if "base64" in target["stdout"]:
            # Keep self-consistency of embedded stream identity after mutation.
            payload = b"mutated-stdout-payload\n"
            target["stdout"]["base64"] = base64.b64encode(payload).decode("ascii")
            target["stdout"]["sha256"] = sha256_bytes(payload)
            target["stdout"]["byte_size"] = len(payload)
            fake = target["stdout"]["sha256"]
        for fact in mutated_facts["cases"]:
            if fact["id"] == case_id:
                fact["stdout_sha256"] = fake
                fact["stdout_byte_size"] = target["stdout"]["byte_size"]
                if fact.get("semantic_snapshot_sha256"):
                    fact["semantic_snapshot_sha256"] = fake
                break
        try:
            validate_baseline(cases_document, mutated_baseline, sealed)
            validate_facts(cases_document, mutated_baseline, mutated_facts, sealed)
        except AlgebraValidationError:
            return
        raise AlgebraValidationError(
            f"mutation not rejected: coordinated stdout refresh for {case_id}"
        )

    coordinated_stdout_mutation()

    # Coordinated semantic snapshot mutation still rejected by sealed projection.
    def coordinated_semantic_mutation() -> None:
        mutated_baseline = copy.deepcopy(baseline)
        mutated_facts = copy.deepcopy(facts)
        target = next(
            observation
            for observation in mutated_baseline["cases"]
            if observation["id"].endswith(".semantic") and observation["exit_status"] == 0
        )
        case_id = target["id"]
        payload = b'{"kind":"mutated","schema_version":1,"sources":[]}\n'
        digest = sha256_bytes(payload)
        target["stdout"] = {
            "sha256": digest,
            "byte_size": len(payload),
            "base64": base64.b64encode(payload).decode("ascii"),
        }
        for fact in mutated_facts["cases"]:
            if fact["id"] == case_id:
                fact["stdout_sha256"] = digest
                fact["stdout_byte_size"] = len(payload)
                fact["semantic_snapshot_sha256"] = digest
                break
        try:
            validate_baseline(cases_document, mutated_baseline, sealed)
            validate_facts(cases_document, mutated_baseline, mutated_facts, sealed)
        except AlgebraValidationError:
            return
        raise AlgebraValidationError(
            f"mutation not rejected: coordinated semantic refresh for {case_id}"
        )

    coordinated_semantic_mutation()

    # Zeroed operand digest after refreshing observation self-hashes still rejected.
    def zeroed_operand_after_refresh() -> None:
        mutated_baseline = copy.deepcopy(baseline)
        mutated_facts = copy.deepcopy(facts)
        target = next(
            observation
            for observation in mutated_baseline["cases"]
            if observation.get("operand_sha256")
        )
        case_id = target["id"]
        zero = "0" * 64
        operand = dict(target["operand_sha256"])
        first_key = next(iter(operand))
        operand[first_key] = zero
        target["operand_sha256"] = operand
        if first_key == "left.info":
            target["left_sha256"] = zero
        elif first_key == "right.info":
            target["right_sha256"] = zero
        elif first_key == "input.info":
            target["input_sha256"] = zero
        # Refresh stream self-hashes remain intact; only operand identity is attacked.
        for fact in mutated_facts["cases"]:
            if fact["id"] == case_id:
                fact["operand_sha256"] = operand
                if first_key == "left.info":
                    fact["left_sha256"] = zero
                elif first_key == "right.info":
                    fact["right_sha256"] = zero
                elif first_key == "input.info":
                    fact["input_sha256"] = zero
                break
        try:
            validate_baseline(cases_document, mutated_baseline, sealed)
            validate_facts(cases_document, mutated_baseline, mutated_facts, sealed)
        except AlgebraValidationError:
            return
        raise AlgebraValidationError(
            f"mutation not rejected: zeroed operand after refresh for {case_id}"
        )

    zeroed_operand_after_refresh()

    # Identity field mutations against sealed projection.
    for field in ("model_row", "binding_ids", "runner", "op", "output_file"):
        def field_mutator(doc: dict[str, Any], field_name: str = field) -> None:
            observation = doc["cases"][0]
            if field_name == "binding_ids":
                observation[field_name] = ["MUTATED-BINDING"]
            elif field_name == "output_file":
                observation[field_name] = "mutated.info"
            else:
                observation[field_name] = f"mutated-{field_name}"

        mutate_and_reject(
            baseline,
            field_mutator,
            label=f"observation {field}",
            validator=lambda doc, field_name=field: validate_baseline(cases_document, doc, sealed),
        )

    def sealed_stdout_drift(doc: dict[str, Any]) -> None:
        doc["cases"][0]["stdout_sha256"] = "0" * 64

    mutate_and_reject(
        sealed,
        sealed_stdout_drift,
        label="sealed stdout",
        validator=lambda doc: validate_baseline(cases_document, baseline, doc),
    )

    require(sha256_file(FACTS_PATH) != sha256_file(BASELINE_PATH), "facts/baseline identity collapse")
    require(sha256_file(SEALED_PATH) != sha256_file(BASELINE_PATH), "sealed/baseline identity collapse")
    require(sha256_file(SEALED_PATH) != sha256_file(FACTS_PATH), "sealed/facts identity collapse")


def validate_all(*, mutations: bool = True) -> None:
    validate_generation_roundtrip()
    cases_document = load_json(CASES_PATH)
    baseline = load_json(BASELINE_PATH)
    facts = load_json(FACTS_PATH)
    sealed = load_json(SEALED_PATH)
    validate_fixtures(cases_document)
    validate_cases(cases_document)
    validate_sealed(cases_document, sealed)
    validate_baseline(cases_document, baseline, sealed)
    validate_facts(cases_document, baseline, facts, sealed)
    if mutations:
        reverse_mutation_suite(cases_document, baseline, facts, sealed)


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
