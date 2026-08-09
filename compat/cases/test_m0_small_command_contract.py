#!/usr/bin/env python3
"""Validate the first M0 small-command compatibility planning suite."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-small-command-contract.json"


class SmallCommandContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}

    def test_exact_case_set_and_comparisons(self) -> None:
        self.assertEqual(self.suite["suite_id"], "m0-small-command-contract")
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assertEqual(
            set(self.cases),
            {
                "m0-gendesc-output-filename",
                "m0-py2lcov-tabwidth",
                "m0-genpng-output-filename",
                "m0-genpng-tab-size",
                "m0-genpng-width",
                "m0-genpng-sourcefile-positional",
            },
        )
        for case in self.cases.values():
            self.assertEqual(case["surface"], "cli")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )
            self.assertTrue(
                all(item["normalizer"] == "exact-v1" for item in case["comparisons"])
            )

    def test_fixture_ownership(self) -> None:
        expected = {
            "m0-gendesc-output-filename": {"input.txt"},
            "m0-py2lcov-tabwidth": {"coverage.xml", "sample.py"},
            "m0-genpng-output-filename": {"source.txt"},
            "m0-genpng-tab-size": {"source.txt"},
            "m0-genpng-width": {"source.txt"},
            "m0-genpng-sourcefile-positional": {"source.txt"},
        }
        for case_id, names in expected.items():
            fixture = ROOT / self.cases[case_id]["fixture"]
            self.assertTrue(fixture.is_dir(), case_id)
            self.assertEqual(
                {path.name for path in fixture.iterdir() if path.is_file()},
                names,
                case_id,
            )

    def test_each_case_exercises_its_named_boundary(self) -> None:
        self.assertEqual(
            self.cases["m0-gendesc-output-filename"]["arguments"][:2],
            ["--output-filename", "output.desc"],
        )
        py2lcov = self.cases["m0-py2lcov-tabwidth"]
        self.assertEqual(py2lcov["arguments"][:2], ["--tabwidth", "4"])
        self.assertNotIn("--no-functions", py2lcov["arguments"])
        source = (ROOT / py2lcov["fixture"] / "sample.py").read_bytes()
        self.assertIn(b"def outer():", source)
        self.assertIn(b"\t", source)
        coverage_xml = (ROOT / py2lcov["fixture"] / "coverage.xml").read_text(
            encoding="utf-8"
        )
        self.assertIn('<line number="3" hits="1"/>', coverage_xml)
        self.assertIn(
            "--output-filename",
            self.cases["m0-genpng-output-filename"]["arguments"],
        )
        self.assertIn("--tab-size", self.cases["m0-genpng-tab-size"]["arguments"])
        self.assertIn("--width", self.cases["m0-genpng-width"]["arguments"])
        self.assertEqual(
            self.cases["m0-genpng-sourcefile-positional"]["arguments"],
            ["source.txt"],
        )


if __name__ == "__main__":
    unittest.main()
