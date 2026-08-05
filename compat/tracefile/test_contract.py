from __future__ import annotations

import copy
import importlib.util
import os
import unittest
from pathlib import Path


TRACEFILE_ROOT = Path(__file__).resolve().parent
UPSTREAM_ROOT = Path(
    os.environ.get(
        "LCOV_SOURCE_ROOT",
        TRACEFILE_ROOT.parents[2] / "lcov-upstream-reference",
    )
).resolve()

SPEC = importlib.util.spec_from_file_location(
    "ferricov_tracefile_contract",
    TRACEFILE_ROOT / "contract.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load tracefile contract module")
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class TracefileContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        contract.validate_upstream_identity(UPSTREAM_ROOT)
        cls.generated = contract.build_document(UPSTREAM_ROOT)
        cls.committed = contract.load_json(contract.OUTPUT_PATH)

    def validate(self, document: dict[str, object]) -> None:
        contract.validate_document(document, UPSTREAM_ROOT)

    def test_committed_contract_matches_generation(self) -> None:
        self.validate(self.committed)
        self.assertEqual(
            contract.canonical_json(self.committed),
            contract.canonical_json(self.generated),
        )

    def test_missing_record_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["records"].pop()

        with self.assertRaises(contract.TracefileContractError):
            self.validate(document)

    def test_reader_matcher_closure_gap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        tn = next(entry for entry in document["records"] if entry["tag"] == "TN")
        tn["source_references"] = [
            reference
            for reference in tn["source_references"]
            if reference["role"] != "reader"
        ]

        with self.assertRaisesRegex(
            contract.TracefileContractError,
            "reader matcher closure mismatch",
        ):
            self.validate(document)

    def test_source_text_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["records"][0]["source_references"][0]["text"] += " # drift"

        with self.assertRaisesRegex(contract.TracefileContractError, "source text drift"):
            self.validate(document)

    def test_writer_classification_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        tn = next(entry for entry in document["records"] if entry["tag"] == "TN")
        tn["writer_behavior"] = "not_emitted"

        with self.assertRaisesRegex(
            contract.TracefileContractError,
            "writer record count drift",
        ):
            self.validate(document)

    def test_missing_malformed_fixture_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["fixtures"] = [
            fixture
            for fixture in document["fixtures"]
            if fixture["id"] != "malformed-unknown"
        ]

        with self.assertRaises(contract.TracefileContractError):
            self.validate(document)

    def test_malformed_target_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["records"][0]["malformed_fixture_id"] = "malformed-sf"

        with self.assertRaisesRegex(
            contract.TracefileContractError,
            "record-to-malformed-fixture closure mismatch",
        ):
            self.validate(document)

    def test_oracle_observation_identity_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        first, second = document["oracle_cases"][:2]
        first["stdout_sha256"], second["stdout_sha256"] = (
            second["stdout_sha256"],
            first["stdout_sha256"],
        )

        with self.assertRaisesRegex(
            contract.TracefileContractError,
            "Oracle case or observation identity drift",
        ):
            self.validate(document)

    def test_retained_artifact_hash_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["artifact_bindings"][0]["sha256"] = "0" * 64

        with self.assertRaisesRegex(
            contract.TracefileContractError,
            "retained artifact binding drift",
        ):
            self.validate(document)

    def test_product_evidence_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["records"][0]["product_evidence"] = ["not-product-evidence"]

        with self.assertRaises(contract.TracefileContractError):
            self.validate(document)

    def test_oracle_reference_cannot_be_promoted(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_cases"][0]["evidence_status"] = "product_pass"

        with self.assertRaises(contract.TracefileContractError):
            self.validate(document)

    def test_requirement_mapping_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        target = next(
            case
            for case in document["oracle_cases"]
            if case["id"] == "state-late-tn-mcdc.semantic-snapshot"
        )
        target["requirement_ids"] = ["M1-TF-999"]

        with self.assertRaisesRegex(
            contract.TracefileContractError,
            "requirement_ids mapping drift",
        ):
            self.validate(document)

    def test_ver_mapping_is_exact_and_source_scoped(self) -> None:
        targets = {
            case["id"]: case
            for case in self.committed["oracle_cases"]
            if case["id"].startswith("ver-")
        }
        self.assertEqual(
            set(targets),
            {
                "ver-repeat-equal.summary",
                "ver-repeat-different.summary",
                "ver-per-source.summary",
                "ver-repeat-equal.canonical",
            },
        )
        for target in targets.values():
            with self.subTest(case_id=target["id"]):
                self.assertEqual(target["requirement_ids"], ["M1-TF-007"])
                self.assertNotIn("m0_decision_ids", target)

    def test_function_mapping_is_exact_and_source_scoped(self) -> None:
        expected = {
            "functions-current-core.summary": ["M1-TF-009"],
            "functions-current-core.canonical": ["M1-TF-009"],
            "functions-current-core.semantic-snapshot": ["M1-TF-009"],
            "functions-current-missing-alias.summary": ["M1-TF-009"],
            "functions-zero-end.summary": ["M1-TF-009"],
            "functions-zero-end.canonical": ["M1-TF-009"],
            "functions-zero-start.summary": ["M1-TF-009"],
            "functions-zero-start.ignore-inconsistent-format": ["M1-TF-034", "M1-TF-036"],
            "functions-zero-start.semantic-snapshot": ["M1-TF-034"],
            "functions-mixed-merge.summary": ["M1-TF-011"],
            "functions-mixed-merge.canonical": ["M1-TF-011"],
            "functions-mixed-merge.semantic-snapshot": ["M1-TF-011"],
            "functions-mixed-location-mismatch.summary": ["M1-TF-011"],
            "functions-mixed-location-mismatch.canonical": ["M1-TF-011"],
            "functions-mixed-range-mismatch.summary": ["M1-TF-011"],
            "functions-mixed-range-mismatch.canonical": ["M1-TF-011"],
            "functions-index-duplicate.summary": ["M1-TF-024"],
            "functions-index-duplicate.canonical": ["M1-TF-024"],
            "functions-index-unknown.summary": ["M1-TF-024"],
            "functions-index-unknown.canonical": ["M1-TF-024"],
            "functions-index-scope-reset.summary": ["M1-TF-024"],
            "functions-index-scope-reset.canonical": ["M1-TF-024"],
            "functions-index-tn-preserves.summary": ["M1-TF-024"],
        }
        targets = {
            case["id"]: case
            for case in self.committed["oracle_cases"]
            if case["id"].startswith("functions-")
        }
        self.assertEqual(set(targets), set(expected))
        for case_id, requirement_ids in expected.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(targets[case_id]["requirement_ids"], requirement_ids)
                self.assertNotIn("m0_decision_ids", targets[case_id])

    def test_branch_mapping_is_exact_and_source_scoped(self) -> None:
        expected = {
            "branches-forms-core.summary": ["M1-TF-013"],
            "branches-forms-core.canonical": ["M1-TF-013"],
            "branches-forms-core.semantic-snapshot": ["M1-TF-013"],
            "branches-u-modes.summary": ["M1-TF-013"],
            "branches-u-modes.canonical": ["M1-TF-013"],
            "branches-u-modes.clear-unreachable": ["M1-TF-013"],
            "branches-malformed-tail.summary": ["M1-TF-013"],
            "branches-malformed-tail.canonical": ["M1-TF-013"],
            "branches-malformed-tail-empty-taken.summary": ["M1-TF-013"],
            "branches-malformed-tail-empty-taken.canonical": ["M1-TF-013"],
            "branches-malformed-tail-empty-expression.summary": ["M1-TF-013"],
            "branches-malformed-tail-empty-expression.canonical": ["M1-TF-013"],
            "branches-expression-mismatch.summary": ["M1-TF-013"],
            "branches-expression-mismatch.canonical": ["M1-TF-013"],
            "branches-expression-merge.canonical": ["M1-TF-025"],
            "branches-expression-merge.semantic-snapshot": ["M1-TF-025"],
            "branches-order-gaps.summary": ["M1-TF-025"],
            "branches-order-gaps.canonical": ["M1-TF-025"],
            "branches-noncontiguous.summary": ["M1-TF-025"],
            "branches-noncontiguous.canonical": ["M1-TF-025"],
            "branches-noncontiguous.semantic-snapshot": ["M1-TF-025"],
            "branches-interleave.summary": ["M1-TF-025"],
            "branches-interleave.canonical": ["M1-TF-025"],
            "branches-sort-signatures.summary": ["M1-TF-025"],
            "branches-sort-signatures.canonical": ["M1-TF-025"],
        }
        targets = {
            case["id"]: case
            for case in self.committed["oracle_cases"]
            if case["id"].startswith("branches-")
        }
        self.assertEqual(set(targets), set(expected))
        for case_id, requirement_ids in expected.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(targets[case_id]["requirement_ids"], requirement_ids)
                self.assertNotIn("m0_decision_ids", targets[case_id])
        self.assertEqual(
            targets["branches-expression-merge.canonical"]["additional_fixture_ids"],
            ["branches-expression-merge-right"],
        )
        self.assertEqual(
            targets["branches-expression-merge.semantic-snapshot"]["additional_fixture_ids"],
            ["branches-expression-merge-right"],
        )

    def test_numeric_mapping_keeps_incomplete_exact_atoms_blocked(self) -> None:
        targets = {
            case["id"]: case
            for case in self.committed["oracle_cases"]
            if case["id"].startswith(("numeric-", "checksum-"))
        }
        self.assertNotIn("M1-TF-030", {
            requirement
            for case in targets.values()
            for requirement in case.get("requirement_ids", [])
        })
        for requirement in ("M1-TF-031", "M1-TF-032", "M1-TF-033", "M1-TF-034", "M1-TF-035", "M1-TF-036"):
            with self.subTest(requirement=requirement):
                self.assertTrue(
                    any(requirement in case.get("requirement_ids", []) for case in targets.values())
                )

    def test_semantic_snapshot_runner_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        target = next(
            case
            for case in document["oracle_cases"]
            if case["id"] == "state-late-tn-mcdc.semantic-snapshot"
        )
        target["runner"] = "inspect_model.pl"
        # Force kind/runner mismatch by clearing runner after copy of valid doc is not enough;
        # mutate runner away from inspect_model.pl.
        target["runner"] = "other-runner.pl"

        with self.assertRaises(contract.TracefileContractError):
            self.validate(document)

    def test_semantic_snapshot_identity_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        target = next(
            case
            for case in document["oracle_cases"]
            if case["id"] == "state-cross-sf-mcdc-success.semantic-snapshot"
        )
        other = next(
            case
            for case in document["oracle_cases"]
            if case["id"] == "state-late-tn-mcdc.semantic-snapshot"
        )
        target["stdout_sha256"] = other["stdout_sha256"]

        with self.assertRaisesRegex(
            contract.TracefileContractError,
            "Oracle case or observation identity drift|semantic snapshot identity drift",
        ):
            self.validate(document)

    def test_evidence_promotion_on_state_case_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        target = next(
            case
            for case in document["oracle_cases"]
            if case["id"] == "state-cross-sf-mcdc-duplicate.summary"
        )
        target["evidence_status"] = "product_pass"

        with self.assertRaises(contract.TracefileContractError):
            self.validate(document)



if __name__ == "__main__":
    unittest.main()
