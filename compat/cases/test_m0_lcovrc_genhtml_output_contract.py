#!/usr/bin/env python3
"""Validate the deterministic M0 genhtml lcovrc planning suite."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "compat/cases/m0-lcovrc-genhtml-output-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcovrc-genhtml-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-lcovrc-genhtml-output-wave.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-oracle.json"
IMAGE = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
REFERENCE_LAUNCHER_SHA256 = "3d47df2d0ee4bf1df443687f36799d9d5ecb73a424a836a1a469b9390f97f8c3"
CANDIDATE_LAUNCHER_SHA256 = "dbf332683768c480e68b51ea6c7b25bc5b4e9d30af2b7753a0dc8550b6e08593"
CONTROL = "m0-lcovrc-genhtml-output-control"
CASE_IDS = {
    "m0-lcovrc-genhtml-header",
    "m0-lcovrc-genhtml-html-epilog",
    "m0-lcovrc-genhtml-html-extension",
    "m0-lcovrc-genhtml-html-gzip",
    "m0-lcovrc-genhtml-html-prolog",
    "m0-lcovrc-genhtml-legend",
    "m0-lcovrc-genhtml-no-source",
    "m0-lcovrc-genhtml-num-spaces",
}


class GenhtmlLcovrcContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def test_exact_case_set_and_comparisons(self) -> None:
        self.assertEqual(self.suite["suite_id"], "m0-lcovrc-genhtml-output-contract")
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assertEqual(set(self.cases), CASE_IDS | {CONTROL})
        for case in self.cases.values():
            self.assertEqual(case["surface"], "config")
            self.assertEqual(case["command"], "genhtml")
            self.assertEqual(case["fixture"], "compat/fixtures/m0-lcovrc-genhtml-contract")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )
            self.assertEqual(
                case["arguments"][2:],
                ["--output-directory", "report", "input.info"],
            )

    def test_fixed_epoch_launchers_have_matching_environments(self) -> None:
        reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
        candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        self.assertEqual(reference["runtime"]["image"], IMAGE)
        self.assertEqual(candidate["runtime"]["image"], IMAGE)
        self.assertEqual(
            hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), REFERENCE_LAUNCHER_SHA256
        )
        self.assertEqual(
            hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(), CANDIDATE_LAUNCHER_SHA256
        )
        self.assertEqual(
            reference["environment_variables"], candidate["environment_variables"]
        )
        self.assertEqual(
            reference["environment_variables"]["SOURCE_DATE_EPOCH"], "946684800"
        )

    def test_fixture_identity(self) -> None:
        expected = {
            "control.lcovrc": "52ae4f1a03b9eeb76181421e2fdd07df004ba23bccafad30cf8d8f12cfb7671c",
            "epilog.html": "aa1cf6a0ce83031a10af23b9b29cbbcb40eb42729627e39364d10b5ff488bfe6",
            "epilog.lcovrc": "962e9c075e720874b17911aea51deedd58f263a52b78b4f3589c33546ee2c059",
            "extension.lcovrc": "ee9f52363f6320d55c87c6166631cb0d2783ffdf197c557bd9d3a573eb976e51",
            "gzip.lcovrc": "65f02549875547c0e11ca8a91ae0cf7329c231d3d1dcebea9d529052730e48d4",
            "header.lcovrc": "a8cc4dd24ee0c328dbb808da64971da07487b66baf0c58edb1d60a369b453211",
            "input.info": "62f85d64dd938086dc7ebe885efbd0cadf3b9381549d7edd1ea444adee0428a7",
            "legend.lcovrc": "66881fea856c320bdc22d55b2f751f7f7a20de682b34157ab9b346c91aa8f0e9",
            "no-source.lcovrc": "b274ffc1de6481cf01d49505127a521324e6c3fa2c14e66c92a31b6625b3c6ce",
            "num-spaces.lcovrc": "afaa5d8a4a7f99665b1070574d3659fb37b3afae60712722ecbd6ed26b2544af",
            "prolog.html": "26aa57468b95ba84596510d9c2dff0a9b530d5f256e236ddc4d4cb5fbf9161e7",
            "prolog.lcovrc": "8cc317511b8dc61fb4d904077d70ff5b88a6b1c7dcbe4449f283c7f08b8b4928",
            "source.c": "dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f",
        }
        self.assertEqual(
            {path.name for path in FIXTURE.iterdir() if path.is_file()}, set(expected)
        )
        for name, digest in expected.items():
            self.assertEqual(
                hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(),
                digest,
                name,
            )

    def test_each_plan_uses_control_and_nondefault_case(self) -> None:
        expected_cases = {
            "case.acceptance.lcovrc.genhtml-header": "m0-lcovrc-genhtml-header",
            "case.acceptance.lcovrc.genhtml-html-epilog": "m0-lcovrc-genhtml-html-epilog",
            "case.acceptance.lcovrc.genhtml-html-extension": "m0-lcovrc-genhtml-html-extension",
            "case.acceptance.lcovrc.genhtml-html-gzip": "m0-lcovrc-genhtml-html-gzip",
            "case.acceptance.lcovrc.genhtml-html-prolog": "m0-lcovrc-genhtml-html-prolog",
            "case.acceptance.lcovrc.genhtml-legend": "m0-lcovrc-genhtml-legend",
            "case.acceptance.lcovrc.genhtml-no-source": "m0-lcovrc-genhtml-no-source",
            "case.acceptance.lcovrc.genhtml-num-spaces": "m0-lcovrc-genhtml-num-spaces",
        }
        self.assertEqual(set(self.plans), set(expected_cases))
        for plan_id, case_id in expected_cases.items():
            plan = self.plans[plan_id]
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual(
                [item["case_id"] for item in plan["suite_cases"]],
                [case_id, CONTROL],
            )
            self.assertIn("no Ferricov product evidence", plan["description"])

    def test_read_only_temp_and_tab_semantics_are_present(self) -> None:
        for config in FIXTURE.glob("*.lcovrc"):
            self.assertIn("lcov_tmp_dir = /work", config.read_text(encoding="utf-8"))
        self.assertIn("\tint covered", (FIXTURE / "source.c").read_text(encoding="utf-8"))
        self.assertIn(
            "genhtml_num_spaces = 2",
            (FIXTURE / "num-spaces.lcovrc").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
