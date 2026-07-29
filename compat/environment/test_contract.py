from __future__ import annotations

import copy
import importlib.util
import os
import unittest
from pathlib import Path


ENVIRONMENT_ROOT = Path(__file__).resolve().parent
UPSTREAM_ROOT = Path(
    os.environ.get(
        "LCOV_SOURCE_ROOT",
        ENVIRONMENT_ROOT.parents[2] / "lcov-upstream-reference",
    )
).resolve()

SPEC = importlib.util.spec_from_file_location(
    "ferricov_environment_contract",
    ENVIRONMENT_ROOT / "contract.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load environment contract module")
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class EnvironmentContractTests(unittest.TestCase):
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

    def test_missing_named_variable_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["named_variables"].pop()

        with self.assertRaises(contract.EnvironmentContractError):
            self.validate(document)

    def test_source_text_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["named_variables"][0]["source_references"][0]["text"] += " # drift"

        with self.assertRaisesRegex(contract.EnvironmentContractError, "source text drift"):
            self.validate(document)

    def test_uncovered_environment_use_line_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        force_parallel = next(
            entry
            for entry in document["named_variables"]
            if entry["name"] == "LCOV_FORCE_PARALLEL"
        )
        force_parallel["source_references"].pop()

        with self.assertRaisesRegex(
            contract.EnvironmentContractError,
            "direct environment-use closure mismatch",
        ):
            self.validate(document)

    def test_discovery_order_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["configuration_discovery"][1:3] = reversed(
            document["configuration_discovery"][1:3]
        )

        with self.assertRaisesRegex(
            contract.EnvironmentContractError,
            "configuration discovery identity or order drift",
        ):
            self.validate(document)

    def test_discovery_priority_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["configuration_discovery"][0]["selection_priority"] = 2

        with self.assertRaisesRegex(
            contract.EnvironmentContractError,
            "configuration discovery phase or priority drift",
        ):
            self.validate(document)

    def test_product_evidence_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["named_variables"][0]["product_evidence"] = ["not-product-evidence"]

        with self.assertRaises(contract.EnvironmentContractError):
            self.validate(document)

    def test_unknown_oracle_binding_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["named_variables"][0]["oracle_cases"].append(
            {"suite_id": "missing-suite", "case_id": "missing-case"}
        )
        document["named_variables"][0]["oracle_cases"].sort(
            key=lambda case: (case["suite_id"], case["case_id"])
        )
        document["totals"]["oracle_case_bindings"] += 1

        with self.assertRaisesRegex(
            contract.EnvironmentContractError,
            "unknown Oracle case binding",
        ):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
