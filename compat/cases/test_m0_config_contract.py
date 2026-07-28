from __future__ import annotations

import copy
import json
import unittest

import m0_config_contract as contract


class ConfigContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = json.loads(
            contract.INVENTORY_PATH.read_text(encoding="utf-8")
        )

    def documents(self):
        return contract.build_documents(self.inventory)

    def test_contract_has_exact_partition_and_inventory_coverage(self) -> None:
        suites, document = self.documents()

        self.assertEqual(
            {suite_id: len(suite["cases"]) for suite_id, suite in suites.items()},
            {
                contract.BASE_SUITE: 18,
                contract.ENV_SUITE: 2,
                contract.HOME_FIRST_SUITE: 1,
                contract.LCOV_HOME_SUITE: 1,
            },
        )
        self.assertEqual(
            {
                entry
                for case in document["cases"]
                for entry in case["inventory_entries"]
            },
            contract.EXPECTED_LINKED_ENTRIES,
        )

    def test_rejects_duplicate_global_case_id(self) -> None:
        suites, document = self.documents()
        mutated = copy.deepcopy(suites)
        mutated[contract.ENV_SUITE]["cases"][0]["id"] = mutated[
            contract.BASE_SUITE
        ]["cases"][0]["id"]

        with self.assertRaisesRegex(contract.ConfigContractError, "duplicate"):
            contract.validate_documents(mutated, document, self.inventory)

    def test_rejects_suite_environment_drift(self) -> None:
        suites, document = self.documents()
        mutated = copy.deepcopy(document)
        record = next(
            item
            for item in mutated["suites"]
            if item["suite_id"] == contract.ENV_SUITE
        )
        record["environment_overrides"]["FERRICOV_RC_BRANCH"] = "0"

        with self.assertRaisesRegex(contract.ConfigContractError, "suite record drift"):
            contract.validate_documents(suites, mutated, self.inventory)

    def test_rejects_unknown_inventory_link(self) -> None:
        suites, document = self.documents()
        mutated = copy.deepcopy(document)
        mutated["cases"][0]["inventory_entries"] = ["lcovrc.not-a-real-key"]

        with self.assertRaisesRegex(contract.ConfigContractError, "unknown"):
            contract.validate_documents(suites, mutated, self.inventory)

    def test_rejects_contradictory_stderr_expectation(self) -> None:
        suites, document = self.documents()
        mutated = copy.deepcopy(document)
        expected = mutated["cases"][0]["expected"]
        expected["stderr_empty"] = True
        expected["stderr_contains"] = ["unexpected"]

        with self.assertRaisesRegex(contract.ConfigContractError, "contradictory"):
            contract.validate_documents(suites, mutated, self.inventory)

    def test_committed_artifacts_match_generation(self) -> None:
        contract.validate_committed_artifacts(contract.build_artifacts())


if __name__ == "__main__":
    unittest.main()
