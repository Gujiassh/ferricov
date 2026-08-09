#!/usr/bin/env python3
"""Validate the M0 lcov trace-operation compatibility planning suite."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-lcov-operation-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcov-contract"


class LcovOperationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}

    def test_exact_case_set_and_comparisons(self) -> None:
        self.assertEqual(self.suite["suite_id"], "m0-lcov-operation-contract")
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assertEqual(
            set(self.cases),
            {
                "m0-lcov-checksum-control",
                "m0-lcov-debug",
                "m0-lcov-extract",
                "m0-lcov-history-script",
                "m0-lcov-no-checksum",
                "m0-lcov-prune-tests",
            },
        )
        for case in self.cases.values():
            self.assertEqual(case["command"], "lcov")
            self.assertEqual(case["surface"], "cli")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )

    def test_fixture_identity_and_semantic_shape(self) -> None:
        expected = {
            "HistoryProbe.pm": "066ae17da8a8ddc83215d00418d6184a2b57fa28ab30bb686d78bb5e66c9ef0d",
            "bar.c": "4511b74a6e5d4a0ca675532ad3331a2dacfe667063968c50c0ded956d18871a4",
            "foo.c": "f943994ca4357ed072d9526e39de3cb560ffc85b3ee3c5a4b1ac11773e5e0dc7",
            "input.info": "304dab8ada04628e6149ee10fbf8bda480003f72f0274a8c02c08b552fbc4115",
        }
        self.assertEqual(
            {path.name for path in FIXTURE.iterdir() if path.is_file()},
            set(expected),
        )
        for name, digest in expected.items():
            self.assertEqual(
                hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(),
                digest,
                name,
            )
        trace = (FIXTURE / "input.info").read_bytes()
        self.assertIn(b"SF:/work/foo.c\n", trace)
        self.assertIn(b"SF:/work/bar.c\n", trace)
        self.assertIn(b"TN:keep\n", trace)
        self.assertIn(b"TN:\n", trace)
        self.assertIn(b",h6hHR3as5QDNs8KpJ0TxXw\n", trace)

    def test_each_case_exercises_its_named_boundary(self) -> None:
        self.assertIn("--debug", self.cases["m0-lcov-debug"]["arguments"])

        extract = self.cases["m0-lcov-extract"]["arguments"]
        self.assertEqual(extract[:3], ["--extract", "input.info", "*/foo.c"])

        history = self.cases["m0-lcov-history-script"]["arguments"]
        self.assertEqual(history[history.index("--history-script") + 1], "./HistoryProbe.pm")

        checksum_control = self.cases["m0-lcov-checksum-control"]["arguments"]
        self.assertIn("--checksum", checksum_control)
        self.assertNotIn("--no-checksum", checksum_control)
        no_checksum = self.cases["m0-lcov-no-checksum"]["arguments"]
        self.assertLess(no_checksum.index("--checksum"), no_checksum.index("--no-checksum"))

        prune = self.cases["m0-lcov-prune-tests"]["arguments"]
        self.assertIn("--prune-tests", prune)
        self.assertIn("--add-tracefile", prune)

        module = (FIXTURE / "HistoryProbe.pm").read_text(encoding="utf-8")
        self.assertIn("history.loaded", module)
        trace = (FIXTURE / "input.info").read_text(encoding="utf-8")
        self.assertEqual(trace.count("SF:/work/foo.c\n"), 2)
        self.assertEqual(trace.count("SF:/work/bar.c\n"), 1)
        self.assertEqual(trace.count("TN:\n"), 1)

    def test_capture_reset_and_unstable_residuals_remain_unreviewed(self) -> None:
        residuals = {
            "case.acceptance.command.lcov.option.compat-libtool",
            "case.acceptance.command.lcov.option.derive-func-data",
            "case.acceptance.command.lcov.option.external",
            "case.acceptance.command.lcov.option.fail-under-branches",
            "case.acceptance.command.lcov.option.large-file",
            "case.acceptance.command.lcov.option.preserve",
            "case.acceptance.command.lcov.option.zerocounters",
        }
        cases = {}
        for path in sorted(
            (ROOT / "compat/behavior/fragments/authored").glob(
                "m0-lcov-wave1-repair-*.json"
            )
        ):
            fragment = json.loads(path.read_text(encoding="utf-8"))
            cases.update({case["id"]: case for case in fragment["case_groups"]})
        self.assertTrue(residuals.issubset(cases))
        for case_id in residuals:
            self.assertEqual(cases[case_id]["review_status"], "unreviewed")
            self.assertEqual(cases[case_id]["evidence_status"], "none")
            self.assertEqual(cases[case_id]["suite_cases"], [])


if __name__ == "__main__":
    unittest.main()
