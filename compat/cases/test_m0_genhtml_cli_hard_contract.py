#!/usr/bin/env python3
"""Validate genhtml hard CLI planning suite (history-script only)."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

_CASES_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_CASES_DIR))
import m0_genhtml_cli_hard_contract as hard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SUITE = hard.SUITE_PATH
FIXTURE = ROOT / hard.FIXTURE
OBSERVATIONS_PATH = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-genhtml-cli-hard-wave.json"
CANONICAL_CASES = hard.CANONICAL_CASES


class GenhtmlCliHardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.observations = json.loads(OBSERVATIONS_PATH.read_text(encoding="utf-8"))
        cls.obs_by_id = {item["case_id"]: item for item in cls.observations["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def test_suite_passes_production_validator(self) -> None:
        hard.validate_suite_document(self.suite)
        hard.validate_committed_suite()

    def test_exact_case_set_and_argv(self) -> None:
        self.assertEqual([case["id"] for case in self.suite["cases"]], list(CANONICAL_CASES))
        for case in self.suite["cases"]:
            expected = CANONICAL_CASES[case["id"]]
            self.assertEqual(case["arguments"], expected["arguments"])
            self.assertEqual(case["comparisons"], expected["comparisons"])

    def test_suite_mutations_are_rejected_by_production_validator(self) -> None:
        mutations = []

        def add(label: str, mutator) -> None:
            mutated = copy.deepcopy(self.suite)
            mutator(mutated)
            mutations.append((label, mutated))

        add("delete-history-flag", lambda s: s["cases"][1]["arguments"].remove("--history-script"))
        add(
            "replace-history-path",
            lambda s: s["cases"][1]["arguments"].__setitem__(
                s["cases"][1]["arguments"].index("./history.sh"), "./other.sh"
            ),
        )
        add(
            "replace-stdout-normalizer",
            lambda s: s["cases"][0]["comparisons"].__setitem__(
                1, {"dimension": "stdout", "normalizer": "text-crlf-to-lf-v1"}
            ),
        )
        add(
            "drop-stderr-dimension",
            lambda s: s["cases"][1].__setitem__(
                "comparisons",
                [
                    {"dimension": "exit", "normalizer": "exact-v1"},
                    {"dimension": "stdout", "normalizer": "exact-v1"},
                    {"dimension": "filesystem", "normalizer": "exact-v1"},
                ],
            ),
        )

        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(hard.HardSuiteValidationError):
                    hard.validate_suite_document(mutated)
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "suite.json"
                    path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
                    with self.assertRaises(hard.HardSuiteValidationError):
                        hard.validate_suite_path(path)

    def test_oracle_observations_history_differs_on_stdout(self) -> None:
        self.assertFalse(self.observations["product_compatibility_evidence"])
        self.assertEqual(
            [c["case_id"] for c in self.observations["cases"]],
            list(CANONICAL_CASES),
        )
        control = self.obs_by_id[hard.CONTROL]
        history = self.obs_by_id[f"{hard.SUITE_ID}-history-script"]
        self.assertNotEqual(
            history["reference_run"]["stdout_sha256"],
            control["reference_run"]["stdout_sha256"],
        )
        self.assertEqual(history["reverse_run"]["exit_code"], 23)
        self.assertEqual(history["reference_run"]["exit_code"], 0)
        for case in self.suite["cases"]:
            obs = self.obs_by_id[case["id"]]
            self.assertEqual(obs["arguments"], case["arguments"])
            self.assertEqual(obs["comparison_contract"], case["comparisons"])
            self.assertFalse(obs["product_compatibility_evidence"])

    def test_history_plan_is_reviewed_and_suite_bound(self) -> None:
        plan = self.plans["case.acceptance.command.genhtml.option.history-script"]
        self.assertEqual(plan["review_status"], "reviewed")
        self.assertEqual(plan["evidence_status"], "planned")
        self.assertEqual(plan["evidence"], [])
        self.assertTrue(plan["suite_cases"])
        self.assertNotIn(
            "case.acceptance.command.genhtml.option.debug",
            self.plans,
        )

    def test_fixture_inputs_are_present(self) -> None:
        for name in ("control.lcovrc", "input.info", "source.c", "history.sh", "oracle-observations.json"):
            path = FIXTURE / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
