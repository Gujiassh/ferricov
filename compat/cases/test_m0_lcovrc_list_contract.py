#!/usr/bin/env python3
"""Validate the M0 lcovrc list-format compatibility planning suite."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "compat/cases/m0-lcovrc-list-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcovrc-list-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-lcovrc-list-wave.json"


class LcovrcListContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def test_exact_case_set_and_comparisons(self) -> None:
        self.assertEqual(self.suite["suite_id"], "m0-lcovrc-list-contract")
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assertEqual(
            set(self.cases),
            {
                "m0-lcovrc-list-control",
                "m0-lcovrc-list-full-path",
                "m0-lcovrc-list-width",
            },
        )
        for case in self.cases.values():
            self.assertEqual(case["surface"], "config")
            self.assertEqual(case["command"], "lcov")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )

    def test_fixture_identity_and_path_shape(self) -> None:
        expected = {
            "control.lcovrc": "e6b3159cd70e8957949f0e75b99c68642f2147cb60ae5181fe15079ad9056f86",
            "full-path.lcovrc": "ad03d63ca596814449250abaa15f2ffd90660af615d6e000a86904e7da42ae21",
            "input.info": "32326ca6fab826fe0294d4921083c61023636f8e61bc2ac7e6e337f1cc097939",
            "truncate-0.lcovrc": "fdbb2d67f64b7f787cd8e054e6435c2993859fc3dc436906a7711ccdf14a4f6c",
            "width-50.lcovrc": "129cf3659ffcbde72e26f0334b2150eff9b80a68769407d8bb6dd0abdd54b6e2",
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
        trace = (FIXTURE / "input.info").read_text(encoding="utf-8")
        self.assertEqual(trace.count("SF:/work/project/src/"), 5)
        self.assertIn("this_is_a_very_long_external_epsilon_filename", trace)

    def test_control_and_nondefault_values_are_independent(self) -> None:
        control = (FIXTURE / "control.lcovrc").read_text(encoding="utf-8")
        full = (FIXTURE / "full-path.lcovrc").read_text(encoding="utf-8")
        width = (FIXTURE / "width-50.lcovrc").read_text(encoding="utf-8")
        self.assertIn("lcov_list_full_path = 0", control)
        self.assertIn("lcov_list_full_path = 1", full)
        self.assertIn("lcov_list_width = 80", control)
        self.assertIn("lcov_list_width = 50", width)
        self.assertEqual(
            self.cases["m0-lcovrc-list-full-path"]["arguments"][:2],
            ["--config-file", "full-path.lcovrc"],
        )
        self.assertEqual(
            self.cases["m0-lcovrc-list-width"]["arguments"][:2],
            ["--config-file", "width-50.lcovrc"],
        )

    def test_list_truncate_case_is_reviewed_with_planned_suite(self) -> None:
        # Residual program bound this key in m0-lcovrc-genhtml-residual3-wave
        # (not the original list-wave fragment). It is reviewed + planned.
        residual3 = json.loads(
            (
                ROOT
                / "compat/behavior/fragments/authored/m0-lcovrc-genhtml-residual3-wave.json"
            ).read_text(encoding="utf-8")
        )
        plans = {case["id"]: case for case in residual3["case_groups"]}
        case = plans["case.acceptance.lcovrc.lcov-list-truncate-max"]
        self.assertEqual(case["review_status"], "reviewed")
        self.assertEqual(case["evidence_status"], "planned")
        self.assertTrue(case["suite_cases"])


if __name__ == "__main__":
    unittest.main()
