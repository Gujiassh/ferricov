from __future__ import annotations

import copy
import unittest

import m0_contract as contract


class AggregateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cli = contract.load_object(contract.CLI_CONTRACT_PATH)
        cls.config = contract.load_object(contract.CONFIG_CONTRACT_PATH)

    def test_committed_aggregate_matches_generation(self) -> None:
        self.assertEqual(contract.OUTPUT_PATH.read_bytes(), contract.build_artifact())

    def test_rejects_duplicate_suite_identity(self) -> None:
        document = contract.build_document(self.cli, self.config)
        mutated = copy.deepcopy(document)
        mutated["suites"][-1]["suite_id"] = mutated["suites"][0]["suite_id"]

        with self.assertRaisesRegex(contract.AggregateContractError, "suite identity"):
            contract.validate_document(mutated, self.cli, self.config)

    def test_rejects_missing_configuration_expectation(self) -> None:
        document = contract.build_document(self.cli, self.config)
        mutated = copy.deepcopy(document)
        target = next(record for record in mutated["cases"] if "expected" in record)
        del target["expected"]

        with self.assertRaisesRegex(contract.AggregateContractError, "expectations"):
            contract.validate_document(mutated, self.cli, self.config)


if __name__ == "__main__":
    unittest.main()
