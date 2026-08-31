#!/usr/bin/env python3
"""Fail-closed reverse-mutation tests for the M0 coverage-model algebra contract."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


MODEL_ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ferricov_model_contract",
    MODEL_ROOT / "contract.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load model contract module")
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class ModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generated = contract.build_document()
        cls.committed = contract.load_json(contract.OUTPUT_PATH)

    def validate(self, document: dict[str, object]) -> None:
        contract.validate_document(document)

    def test_committed_contract_matches_generation(self) -> None:
        self.validate(self.committed)
        self.assertEqual(
            contract.canonical_json(self.committed),
            contract.canonical_json(self.generated),
        )

    def test_bound_and_blocked_rows(self) -> None:
        self.assertEqual(self.committed["bound_case_ids"], list(contract.BOUND_ROWS))
        self.assertEqual(self.committed["blocked_case_ids"], list(contract.BLOCKED_IDS))
        self.assertFalse(self.committed["product_compatibility_evidence"])
        self.assertEqual(self.committed["fuzz_execution_phase"], "M1-only")
        self.assertEqual(self.committed["case_count"], self.committed["observation_count"])
        self.assertEqual(self.committed["case_count"], 157)
        self.assertEqual(self.committed["fixture_count"], 27)

    def test_rejected_vector_cases_are_present(self) -> None:
        by_id = {entry["id"]: entry for entry in self.committed["executable_bindings"]}
        for case_id, expected_exit in (
            ("md013-mcdc-vector.union.cli", 1),
            ("md013-mcdc-vector.union.semantic", 255),
            ("md013-mcdc-vector.intersect.cli", 1),
            ("md013-mcdc-vector.intersect.semantic", 255),
        ):
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, by_id)
                self.assertEqual(by_id[case_id]["expected_exit"], expected_exit)
                self.assertEqual(by_id[case_id]["ferricov_parity_status"], "blocked")

    def test_product_evidence_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["product_compatibility_evidence"] = True
        with self.assertRaises(contract.ModelContractError):
            self.validate(document)

    def test_blocked_case_removal_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["blocked_case_ids"] = document["blocked_case_ids"][:-1]
        with self.assertRaises(contract.ModelContractError):
            self.validate(document)

    def test_bound_case_removal_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["bound_case_ids"] = document["bound_case_ids"][:-1]
        with self.assertRaises(contract.ModelContractError):
            self.validate(document)

    def test_oracle_identity_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_identity"]["image_sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(contract.ModelContractError, "drift|schema"):
            self.validate(document)

    def test_artifact_binding_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["artifact_bindings"][0]["sha256"] = "0" * 64
        with self.assertRaises(contract.ModelContractError):
            self.validate(document)

    def test_harness_artifact_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["harness_artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaises(contract.ModelContractError):
            self.validate(document)

    def test_executable_binding_exit_mutation_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["executable_bindings"][0]["expected_exit"] = 99
        with self.assertRaises(contract.ModelContractError):
            self.validate(document)

    def test_case_count_mutation_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["case_count"] = document["case_count"] - 1
        with self.assertRaises(contract.ModelContractError):
            self.validate(document)

    def test_fuzz_phase_promotion_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["fuzz_execution_phase"] = "M0"
        with self.assertRaises(contract.ModelContractError):
            self.validate(document)

    def test_independent_facts_path_is_bound(self) -> None:
        self.assertEqual(
            self.committed["independent_facts_path"],
            "compat/fixtures/m0-algebra/expected-facts.json",
        )
        self.assertTrue((contract.ROOT / self.committed["independent_facts_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
