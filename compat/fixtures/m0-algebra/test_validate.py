#!/usr/bin/env python3
"""Focused reverse-mutation tests for the M0 model-algebra corpus."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import generate  # noqa: E402
import validate  # noqa: E402


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ModelAlgebraValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = validate.load_json(validate.CASES_PATH)
        cls.baseline = validate.load_json(validate.BASELINE_PATH)
        cls.facts = validate.load_json(validate.FACTS_PATH)
        cls.sealed = validate.load_json(validate.SEALED_PATH)

    def test_full_validation_passes(self) -> None:
        validate.validate_all(mutations=True)

    def test_generator_roundtrip(self) -> None:
        generated = generate.build_cases_document()
        self.assertEqual(
            json.dumps(generated, sort_keys=True),
            json.dumps(self.cases, sort_keys=True),
        )

    def test_bound_rows_and_blocked_ids(self) -> None:
        rows = {case["model_row"] for case in self.cases["cases"]}
        self.assertEqual(
            rows,
            {
                "M1-MD-010",
                "M1-MD-011",
                "M1-MD-012",
                "M1-MD-013",
                "M1-MD-014",
                "M1-MD-017",
                "M1-MD-019",
            },
        )
        self.assertEqual(
            self.cases["blocked_case_ids"],
            ["M1-MD-020", "M1-TF-063", "M1-TF-064"],
        )
        self.assertFalse(self.cases["product_compatibility_evidence"])
        self.assertEqual(self.cases["fuzz_execution_phase"], "M1-only")

    def test_rejected_mcdc_vector_semantics_are_bound(self) -> None:
        rejected = [
            case
            for case in self.cases["cases"]
            if case["id"] in validate.REJECTED_VECTOR_CASES
        ]
        self.assertEqual(len(rejected), 4)
        for case in rejected:
            with self.subTest(case_id=case["id"]):
                self.assertEqual(case["outcome_class"], "oracle_hard_error")
                self.assertNotEqual(case["expected_exit"], 0)
                self.assertEqual(case["error_signature"], validate.ERROR_SIGNATURE)
        reverse_success = [
            case
            for case in self.cases["cases"]
            if case["id"].startswith("md013-mcdc-vector.")
            and case["id"].endswith(("-rev.cli", "-rev.semantic"))
        ]
        self.assertGreaterEqual(len(reverse_success), 4)
        for case in reverse_success:
            self.assertEqual(case["expected_exit"], 0)
            self.assertEqual(case.get("outcome_class", "success"), "success")

    def test_fixture_hash_mutation_is_rejected(self) -> None:
        document = copy.deepcopy(self.cases)
        document["fixtures"][0]["sha256"] = "0" * 64
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_fixtures(document)

    def test_product_evidence_promotion_is_rejected(self) -> None:
        document = copy.deepcopy(self.cases)
        document["product_compatibility_evidence"] = True
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_cases(document)

    def test_blocked_id_removal_is_rejected(self) -> None:
        document = copy.deepcopy(self.cases)
        document["blocked_case_ids"] = document["blocked_case_ids"][:-1]
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_cases(document)

    def test_argv_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.baseline)
        first, second = document["cases"][0], document["cases"][1]
        first["argv"], second["argv"] = second["argv"], first["argv"]
        with self.assertRaisesRegex(validate.AlgebraValidationError, "argv"):
            validate.validate_baseline(self.cases, document, self.sealed)

    def test_exit_status_mutation_is_rejected(self) -> None:
        document = copy.deepcopy(self.baseline)
        document["cases"][0]["exit_status"] = 99
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_baseline(self.cases, document, self.sealed)

    def test_output_fact_mutation_is_rejected(self) -> None:
        document = copy.deepcopy(self.facts)
        target = next(fact for fact in document["cases"] if fact.get("output_exists"))
        target["output_sha256"] = "0" * 64
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_facts(self.cases, self.baseline, document, self.sealed)

    def test_rejected_case_wash_is_rejected(self) -> None:
        document = copy.deepcopy(self.cases)
        for case in document["cases"]:
            if case["id"] in validate.REJECTED_VECTOR_CASES:
                case["expected_exit"] = 0
                case["outcome_class"] = "success"
                case.pop("error_signature", None)
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_cases(document)

    def test_oracle_image_fact_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.facts)
        document["oracle_image_id"] = "sha256:" + "0" * 64
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_facts(self.cases, self.baseline, document, self.sealed)

    def test_operand_hash_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.baseline)
        target = next(
            observation
            for observation in document["cases"]
            if observation.get("left_sha256")
        )
        target["left_sha256"] = "0" * 64
        with self.assertRaisesRegex(validate.AlgebraValidationError, "left_sha256"):
            validate.validate_baseline(self.cases, document, self.sealed)

    def test_stream_hash_fact_mutation_is_rejected(self) -> None:
        document = copy.deepcopy(self.facts)
        document["cases"][0]["stdout_sha256"] = "0" * 64
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_facts(self.cases, self.baseline, document, self.sealed)

    def test_independent_facts_are_not_baseline_self_hash(self) -> None:
        self.assertNotEqual(
            validate.sha256_file(validate.FACTS_PATH),
            validate.sha256_file(validate.BASELINE_PATH),
        )
        self.assertNotEqual(
            validate.sha256_file(validate.SEALED_PATH),
            validate.sha256_file(validate.BASELINE_PATH),
        )
        self.assertIn("oracle_image_id", self.facts)
        self.assertIn("sealed_observation_facts_sha256", self.facts)
        self.assertTrue(all(fact.get("argv") for fact in self.facts["cases"]))

    def test_coordinated_stdout_refresh_is_rejected_by_sealed(self) -> None:
        mutated_baseline = copy.deepcopy(self.baseline)
        mutated_facts = copy.deepcopy(self.facts)
        target = next(
            observation
            for observation in mutated_baseline["cases"]
            if observation["exit_status"] == 0 and observation["stdout"]["byte_size"] > 0
        )
        case_id = target["id"]
        payload = b"mutated-stdout-payload\n"
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
                if fact.get("semantic_snapshot_sha256"):
                    fact["semantic_snapshot_sha256"] = digest
                break
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_baseline(self.cases, mutated_baseline, self.sealed)
            validate.validate_facts(self.cases, mutated_baseline, mutated_facts, self.sealed)

    def test_coordinated_semantic_refresh_is_rejected_by_sealed(self) -> None:
        mutated_baseline = copy.deepcopy(self.baseline)
        mutated_facts = copy.deepcopy(self.facts)
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
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_baseline(self.cases, mutated_baseline, self.sealed)
            validate.validate_facts(self.cases, mutated_baseline, mutated_facts, self.sealed)

    def test_zeroed_operand_after_refresh_is_rejected(self) -> None:
        mutated_baseline = copy.deepcopy(self.baseline)
        mutated_facts = copy.deepcopy(self.facts)
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
        with self.assertRaises(validate.AlgebraValidationError):
            validate.validate_baseline(self.cases, mutated_baseline, self.sealed)
            validate.validate_facts(self.cases, mutated_baseline, mutated_facts, self.sealed)

    def test_observation_identity_fields_are_sealed(self) -> None:
        for field, value in (
            ("model_row", "M1-MD-999"),
            ("binding_ids", ["MUTATED"]),
            ("runner", "mutated-runner"),
            ("op", "mutated-op"),
            ("output_file", "mutated.info"),
        ):
            with self.subTest(field=field):
                document = copy.deepcopy(self.baseline)
                document["cases"][0][field] = value
                with self.assertRaises(validate.AlgebraValidationError):
                    validate.validate_baseline(self.cases, document, self.sealed)

    def test_sealed_projection_binds_all_cases(self) -> None:
        self.assertEqual(len(self.sealed["cases"]), 157)
        self.assertEqual(
            self.facts["sealed_observation_facts_sha256"],
            validate.sha256_file(validate.SEALED_PATH),
        )
        for entry in self.sealed["cases"]:
            self.assertEqual(len(entry["stdout_sha256"]), 64)
            self.assertEqual(len(entry["stderr_sha256"]), 64)
            self.assertTrue(entry.get("operand_sha256"))


if __name__ == "__main__":
    unittest.main()
