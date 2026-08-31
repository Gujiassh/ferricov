#!/usr/bin/env python3
"""Validate the M0 perl2lcov compatibility planning suite."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-perl2lcov-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-perl2lcov-contract"


class Perl2LcovContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}

    def test_exact_case_set_and_comparisons(self) -> None:
        self.assertEqual(self.suite["suite_id"], "m0-perl2lcov-contract")
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assertEqual(
            set(self.cases),
            {
                "m0-perl2lcov-checksum-control",
                "m0-perl2lcov-debug",
                "m0-perl2lcov-fail-under-branches",
                "m0-perl2lcov-history-script",
                "m0-perl2lcov-no-checksum",
                "m0-perl2lcov-cover-db-positional",
            },
        )
        for case in self.cases.values():
            self.assertEqual(case["command"], "perl2lcov")
            self.assertEqual(case["surface"], "cli")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )

    def test_fixture_database_identity(self) -> None:
        expected = {
            "sample.pl": "6fae50a610cd174399188c2edad1c74cb69ecc9bc32aeeb8e73cc7770a17d8bd",
            "HistoryProbe.pm": "066ae17da8a8ddc83215d00418d6184a2b57fa28ab30bb686d78bb5e66c9ef0d",
            "coverdb/cover.14": "9f35a1abb5e7ef9f3a9ea09491406632937b0999409fa032eb8ffafd7888daf0",
            "coverdb/digests": "f1b8b8f94b73da870c51102a7fe3f7b5c8e5d920ebdde72a03f1bf69d8d08d19",
            "coverdb/structure/5e6c4413fd5c4d0922f16669bb4274fa": "eba31b2be15661815573fcefb7222447a22a56786123dce58faef27d04c23d88",
        }
        actual_paths = {
            path.relative_to(FIXTURE).as_posix()
            for path in FIXTURE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual_paths, set(expected))
        for relative, digest in expected.items():
            self.assertEqual(
                hashlib.sha256((FIXTURE / relative).read_bytes()).hexdigest(),
                digest,
                relative,
            )
        self.assertFalse(any(path.name.endswith(".lock") for path in FIXTURE.rglob("*")))

    def test_each_case_exercises_its_named_boundary(self) -> None:
        self.assertIn("--debug", self.cases["m0-perl2lcov-debug"]["arguments"])

        threshold = self.cases["m0-perl2lcov-fail-under-branches"]["arguments"]
        self.assertEqual(threshold[threshold.index("--fail-under-branches") + 1], "75")

        history = self.cases["m0-perl2lcov-history-script"]["arguments"]
        self.assertEqual(history[history.index("--history-script") + 1], "./HistoryProbe.pm")

        checksum_control = self.cases["m0-perl2lcov-checksum-control"]["arguments"]
        self.assertIn("--checksum", checksum_control)
        self.assertNotIn("--no-checksum", checksum_control)
        checksum = self.cases["m0-perl2lcov-no-checksum"]["arguments"]
        self.assertLess(checksum.index("--checksum"), checksum.index("--no-checksum"))

        self.assertEqual(
            self.cases["m0-perl2lcov-cover-db-positional"]["arguments"],
            ["coverdb"],
        )


if __name__ == "__main__":
    unittest.main()
