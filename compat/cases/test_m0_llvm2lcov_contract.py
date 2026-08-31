#!/usr/bin/env python3
"""Validate the M0 llvm2lcov compatibility planning suite."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-llvm2lcov-contract.json"


class Llvm2LcovContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}

    def test_exact_case_set_and_comparisons(self) -> None:
        self.assertEqual(self.suite["suite_id"], "m0-llvm2lcov-contract")
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assertEqual(
            set(self.cases),
            {
                "m0-llvm2lcov-debug",
                "m0-llvm2lcov-fail-under-branches",
                "m0-llvm2lcov-history-script",
                "m0-llvm2lcov-no-checksum",
                "m0-llvm2lcov-output-filename",
                "m0-llvm2lcov-preserve",
                "m0-llvm2lcov-json-file-positional",
            },
        )
        for case in self.cases.values():
            self.assertEqual(case["command"], "llvm2lcov")
            self.assertEqual(case["surface"], "cli")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )

    def test_fixture_is_complete(self) -> None:
        fixtures = {ROOT / case["fixture"] for case in self.cases.values()}
        self.assertEqual(len(fixtures), 1)
        fixture = fixtures.pop()
        self.assertEqual(
            {path.name for path in fixture.iterdir() if path.is_file()},
            {"HistoryProbe.pm", "branch.c", "branch.json", "input.json", "main.c"},
        )
        branch = json.loads((fixture / "branch.json").read_text(encoding="utf-8"))
        function = branch["data"][0]["functions"][0]
        self.assertEqual(len(function["branches"]), 1)
        self.assertEqual(function["branches"][0][4:6], [1, 0])
        module = (fixture / "HistoryProbe.pm").read_text(encoding="utf-8")
        self.assertIn("history.loaded", module)

    def test_differential_launchers_provide_case_local_temp_storage(self) -> None:
        for name in ("lcov-v2.5-oracle.json", "different-oracle.json"):
            launcher = json.loads(
                (ROOT / "compat/launchers" / name).read_text(encoding="utf-8")
            )
            self.assertEqual(launcher["environment_variables"]["TMPDIR"], "/work")

    def test_each_case_exercises_its_named_boundary(self) -> None:
        self.assertIn("--debug", self.cases["m0-llvm2lcov-debug"]["arguments"])

        threshold = self.cases["m0-llvm2lcov-fail-under-branches"]["arguments"]
        self.assertIn("--branch-coverage", threshold)
        self.assertEqual(
            threshold[threshold.index("--fail-under-branches") + 1],
            "75",
        )
        self.assertEqual(threshold[-1], "branch.json")

        history = self.cases["m0-llvm2lcov-history-script"]["arguments"]
        self.assertEqual(history[history.index("--history-script") + 1], "./HistoryProbe.pm")

        checksum = self.cases["m0-llvm2lcov-no-checksum"]["arguments"]
        self.assertIn("--checksum", checksum)
        self.assertIn("--no-checksum", checksum)
        self.assertLess(checksum.index("--checksum"), checksum.index("--no-checksum"))

        preserve = self.cases["m0-llvm2lcov-preserve"]["arguments"]
        for option in ("--filter", "--parallel", "--tempdir", "--preserve"):
            self.assertIn(option, preserve)
        self.assertEqual(preserve[-1], "branch.json")

        positional = self.cases["m0-llvm2lcov-json-file-positional"]["arguments"]
        self.assertEqual(positional[-1], "input.json")


if __name__ == "__main__":
    unittest.main()
