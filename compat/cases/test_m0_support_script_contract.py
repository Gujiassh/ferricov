#!/usr/bin/env python3
"""Validate the M0 support-script compatibility planning suite."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-support-script-contract.json"


class SupportScriptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}

    def test_exact_case_set_and_comparisons(self) -> None:
        self.assertEqual(self.suite["suite_id"], "m0-support-script-contract")
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assertEqual(
            set(self.cases),
            {
                "m0-support-analyze-info-files",
                "m0-support-annotateutil-compute-md5",
                "m0-support-get-signature",
            },
        )
        for case in self.cases.values():
            self.assertEqual(case["surface"], "installation")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )
            self.assertTrue(
                all(item["normalizer"] == "exact-v1" for item in case["comparisons"])
            )

    def test_fixture_inputs_are_owned_by_each_case(self) -> None:
        expected = {
            "m0-support-analyze-info-files": {"one.info", "two.info"},
            "m0-support-annotateutil-compute-md5": {"sample.txt"},
            "m0-support-get-signature": {"sample.txt"},
        }
        for case_id, names in expected.items():
            fixture = ROOT / self.cases[case_id]["fixture"]
            self.assertTrue(fixture.is_dir(), case_id)
            self.assertEqual(
                {path.name for path in fixture.iterdir() if path.is_file()},
                names,
                case_id,
            )

    def test_annotateutil_declares_real_host_dependencies(self) -> None:
        case = self.cases["m0-support-annotateutil-compute-md5"]
        self.assertEqual(case["command"], "perl")
        self.assertIn("-MFile::Spec", case["arguments"])
        self.assertIn("-Mannotateutil", case["arguments"])
        self.assertLess(
            case["arguments"].index("-MFile::Spec"),
            case["arguments"].index("-Mannotateutil"),
        )
        self.assertIn("compute_md5", case["arguments"][-2])


if __name__ == "__main__":
    unittest.main()
