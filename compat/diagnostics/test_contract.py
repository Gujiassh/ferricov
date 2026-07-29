from __future__ import annotations

import copy
import importlib.util
import os
import unittest
from pathlib import Path


DIAGNOSTICS_ROOT = Path(__file__).resolve().parent
UPSTREAM_ROOT = Path(
    os.environ.get(
        "LCOV_SOURCE_ROOT",
        DIAGNOSTICS_ROOT.parents[2] / "lcov-upstream-reference",
    )
).resolve()

SPEC = importlib.util.spec_from_file_location(
    "ferricov_diagnostics_contract",
    DIAGNOSTICS_ROOT / "contract.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load diagnostics contract module")
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class DiagnosticsContractTests(unittest.TestCase):
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

    def test_missing_category_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["categories"].pop()

        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_category_order_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["categories"][:2] = reversed(document["categories"][:2])

        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "registry or symbol closure drift",
        ):
            self.validate(document)

    def test_symbol_reference_closure_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["categories"][0]["symbol_references_sha256"] = "0" * 64

        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "registry or symbol closure drift",
        ):
            self.validate(document)

    def test_reserved_branch_promotion_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        branch = next(
            entry for entry in document["categories"] if entry["name"] == "branch"
        )
        branch["emitter_status"] = "emitted"

        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "registry or symbol closure drift",
        ):
            self.validate(document)

    def test_control_source_text_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["control_rules"][0]["source_references"][0]["text"] += " # drift"

        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "control-rule drift",
        ):
            self.validate(document)

    def test_exit_policy_change_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        perl2lcov = next(
            entry
            for entry in document["exit_policies"]
            if entry["command"] == "perl2lcov"
        )
        perl2lcov["policy"] = "shared_saw_error_fold"

        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "exit-policy drift",
        ):
            self.validate(document)

    def test_planned_case_catalog_gap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["planned_case_ids"].pop()

        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_oracle_observation_identity_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        first, second = document["oracle_observations"][:2]
        first["stderr_sha256"], second["stderr_sha256"] = (
            second["stderr_sha256"],
            first["stderr_sha256"],
        )

        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "Oracle observation identity drift",
        ):
            self.validate(document)

    def test_retained_artifact_hash_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["artifact_bindings"][0]["sha256"] = "0" * 64

        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "artifact binding drift",
        ):
            self.validate(document)

    def test_geninfo_startup_intercept_cannot_claim_noargs_case(self) -> None:
        document = copy.deepcopy(self.committed)
        geninfo = next(
            entry
            for entry in document["oracle_observations"]
            if entry["id"] == "correctness:m0-core-geninfo-startup-control"
        )
        geninfo["kind"] = "startup_boundary"
        geninfo["planned_case_ids"] = ["DIAG-NOARGS-GENINFO-001"]

        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "Oracle observation identity drift",
        ):
            self.validate(document)

    def test_product_evidence_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["categories"][0]["product_evidence"] = ["not-product-evidence"]

        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_oracle_reference_cannot_be_promoted(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_observation_evidence_status"] = "product_pass"

        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
