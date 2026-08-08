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

    def test_numeric_mapping_includes_exact_tf030_matrix(self) -> None:
        targets = {
            case["id"]: case
            for case in self.committed["oracle_cases"]
            if case["id"].startswith(("numeric-", "checksum-"))
        }
        mapped = {
            requirement
            for case in targets.values()
            for requirement in case.get("requirement_ids", [])
        }
        self.assertIn("M1-TF-030", mapped)
        for requirement in ("M1-TF-031", "M1-TF-032", "M1-TF-033", "M1-TF-034", "M1-TF-035", "M1-TF-036"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, mapped)
        exact_upstream = targets["numeric-format-atoms.tf030.semantic-snapshot"]
        self.assertEqual(exact_upstream["requirement_ids"], ["M1-TF-030"])
        self.assertEqual(exact_upstream["m0_decision_ids"], ["M0-TF-NUMERIC-001"])
        candidate = targets["numeric-tf030-candidates.ignore-negative.semantic-snapshot"]
        self.assertEqual(candidate["requirement_ids"], ["M1-TF-030"])
        self.assertNotIn("m0_decision_ids", candidate)

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



    def test_wave2_mapping_is_exact_and_source_scoped(self) -> None:
        expected = {
            "wave2-framing-blank.summary": ["M1-TF-001"],
            "wave2-framing-blank.canonical": ["M1-TF-001"],
            "wave2-framing-crlf-blank.summary": ["M1-TF-001"],
            "wave2-framing-crlf-blank.canonical": ["M1-TF-001"],
            "wave2-framing-no-final-newline-blank.summary": ["M1-TF-001"],
            "wave2-framing-no-final-newline-blank.canonical": ["M1-TF-001"],
            "wave2-framing-trailing-ws.summary": ["M1-TF-001"],
            "wave2-framing-trailing-ws.canonical": ["M1-TF-001"],
            "wave2-tn-diff.summary": ["M1-TF-004"],
            "wave2-tn-diff.canonical": ["M1-TF-004"],
            "wave2-kf-parity.summary": ["M1-TF-006"],
            "wave2-kf-parity.canonical": ["M1-TF-006"],
            "wave2-kf-empty.summary": ["M1-TF-006"],
            "wave2-kf-empty.canonical": ["M1-TF-006"],
            "wave2-kf-empty.ignore-format": ["M1-TF-006"],
            "wave2-da-accumulate.summary": ["M1-TF-008"],
            "wave2-da-accumulate.canonical": ["M1-TF-008"],
            "wave2-da-checksum-store.canonical": ["M1-TF-008"],
            "wave2-da-checksum-store.no-verify.canonical": ["M1-TF-008"],
            "wave2-summary-forms.summary": ["M1-TF-012"],
            "wave2-summary-forms.canonical": ["M1-TF-012"],
            "wave2-terminator-suffix.summary": ["M1-TF-015"],
            "wave2-terminator-suffix.canonical": ["M1-TF-015"],
            "wave2-terminator-dup.summary": ["M1-TF-015"],
            "wave2-terminator-dup.canonical": ["M1-TF-015"],
            "wave2-terminator-missing.summary": ["M1-TF-015"],
            "wave2-terminator-missing.canonical": ["M1-TF-015"],
            "wave2-terminator-missing.ignore-empty": ["M1-TF-015"],
            "wave2-unknown-tags.summary": ["M1-TF-016"],
            "wave2-unknown-tags.canonical": ["M1-TF-016"],
            "wave2-unknown-tags.ignore-format": ["M1-TF-016"],
            "wave2-leading-ws-tag.summary": ["M1-TF-016"],
            "wave2-leading-ws-tag.canonical": ["M1-TF-016"],
            "wave2-leading-ws-tag.ignore-format": ["M1-TF-016"],
            "wave2-case-change.summary": ["M1-TF-016"],
            "wave2-case-change.canonical": ["M1-TF-016"],
            "wave2-case-change.ignore-format": ["M1-TF-016"],
        }
        targets = {
            case["id"]: case
            for case in self.committed["oracle_cases"]
            if case["id"].startswith("wave2-")
        }
        self.assertEqual(set(targets), set(expected))
        for case_id, requirement_ids in expected.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(targets[case_id]["requirement_ids"], requirement_ids)
                self.assertNotIn("m0_decision_ids", targets[case_id])



    def test_writer_mapping_is_exact_and_source_scoped(self) -> None:
        expected = {
            "legacy.summary": ["M1-TF-010"],
            "legacy.canonical": ["M1-TF-010"],
            "writer-order-core.canonical": ["M1-TF-041"],
            "writer-mcdc-groups.canonical": ["M1-TF-041"],
            "writer-summaries.canonical": ["M1-TF-042"],
            "writer-comments.canonical": ["M1-TF-043"],
            "writer-forbidden.canonical": ["M1-TF-044"],
            "writer-legacy-comma.canonical": ["M1-TF-010"],
            "writer-legacy-repeat.canonical": ["M1-TF-010"],
            "writer-legacy-unknown.summary": ["M1-TF-010"],
            "writer-legacy-unknown.canonical": ["M1-TF-010"],
            "writer-fixedpoint.repeated-write": ["M1-TF-046"],
            "converter-coverage.xml2lcov": ["M1-TF-050", "M1-TF-052"],
            "converter-coverage.py2lcov-no-functions": ["M1-TF-051"],
            "converter-coverage.py2lcov-with-functions": ["M1-TF-051"],
            "converter-coverage.canonical-rewrite": ["M1-TF-052"],
            "gzip-valid.summary": ["M1-TF-060"],
            "gzip-plain.write-gz": ["M1-TF-060"],
            "gzip-corrupt.summary": ["M1-TF-060"],
            "gzip-empty.summary": ["M1-TF-060"],
            "gzip-valid.missing-gzip": ["M1-TF-060"],
        }
        observational_only = {
            "writer-fixedpoint.canonical",  # M1-TF-045 blocked without true two-write cases
            "writer-non-utf8.canonical",
        }
        targets = {
            case["id"]: case
            for case in self.committed["oracle_cases"]
            if case["id"].startswith(("writer-", "gzip-", "converter-coverage."))
            or case["id"] in {"legacy.summary", "legacy.canonical"}
        }
        self.assertEqual(set(targets), set(expected) | observational_only)
        for case_id, requirement_ids in expected.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(targets[case_id]["requirement_ids"], requirement_ids)
                self.assertNotIn("m0_decision_ids", targets[case_id])
        for case_id in observational_only:
            with self.subTest(case_id=case_id):
                self.assertNotIn("requirement_ids", targets[case_id])
                self.assertNotIn("m0_decision_ids", targets[case_id])

    def test_wave3_semantic_mappings_are_exact_and_group_scoped(self) -> None:
        expected = {
            "converter-coverage.xml2lcov": ["M1-TF-050", "M1-TF-052"],
            "converter-coverage.canonical-rewrite": ["M1-TF-052"],
            "bytes-non-utf8.canonical": ["M1-TF-061"],
        }
        targets = {case["id"]: case for case in self.committed["oracle_cases"]}
        for case_id, requirement_ids in expected.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(targets[case_id]["requirement_ids"], requirement_ids)
                self.assertNotIn("m0_decision_ids", targets[case_id])
        # M1-TF-045 is observational only until true two-write Docker cases exist.
        for case_id in (
            "writer-fixedpoint.canonical",
            "permissive-prefix.canonical",
        ):
            self.assertNotIn("requirement_ids", targets[case_id])
        self.assertEqual(
            targets["wave2-unknown-tags.ignore-format"]["requirement_ids"],
            ["M1-TF-016"],
        )
        exact = self.committed["totals"]["exact_executable_requirement_ids"]
        # M1-TF-045 must remain unbound until true two-write cases exist.
        self.assertNotIn("M1-TF-045", exact)
        self.assertIn("M1-TF-010", exact)
        # SF-only writer non-utf8 remains observational; matrix is on bytes-non-utf8.
        writer_non_utf8 = targets["writer-non-utf8.canonical"]
        self.assertNotIn("requirement_ids", writer_non_utf8)
        self.assertIn("M1-TF-052", exact)
        self.assertIn("M1-TF-061", exact)
        self.assertEqual(len(exact), 42)
        self.assertFalse(self.committed["product_compatibility_evidence"])


if __name__ == "__main__":
    unittest.main()
