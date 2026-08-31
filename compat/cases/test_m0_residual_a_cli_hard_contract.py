#!/usr/bin/env python3
"""Validate Lane A residual CLI hard planning suite (geninfo history-script)."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m0_residual_a_cli_hard_contract as residual

ROOT = Path(__file__).resolve().parents[2]
SUITE = residual.SUITE_PATH
FIXTURE = ROOT / residual.FIXTURE
OBS = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-residual-a-cli-hard-wave.json"

CONTROL = f"{residual.SUITE_ID}-geninfo-history-control"
HISTORY = f"{residual.SUITE_ID}-geninfo-history-script"

PINNED = {
    CONTROL: {
        "exit_code": 0,
        "file_count": 14,
        "file_tree_bytes": 2942,
        "file_tree_sha256": "fda604f45bc9a729f6c80e3bf32396ef3f9ec1a11eb014c8daf5b11d56148dd3",
        "paths": [
            "HistoryProbe.pm",
            "out.info",
            "src/a.c",
            "src/a.gcda",
            "src/a.gcno",
            "src/b.c",
            "src/b.gcda",
            "src/b.gcno",
            "src/c.c",
            "src/c.gcda",
            "src/c.gcno",
            "src/main.c",
            "src/main.gcda",
            "src/main.gcno",
        ],
        "reverse_exit": 23,
    },
    HISTORY: {
        "exit_code": 0,
        "file_count": 15,
        "file_tree_bytes": 2949,
        "file_tree_sha256": "5725a1e6865cf7ad9c7cfd3622f6fcd047c9aa459f7f7deb6840fd7fad33e070",
        "paths": [
            "HistoryProbe.pm",
            "history.loaded",
            "out.info",
            "src/a.c",
            "src/a.gcda",
            "src/a.gcno",
            "src/b.c",
            "src/b.gcda",
            "src/b.gcno",
            "src/c.c",
            "src/c.gcda",
            "src/c.gcno",
            "src/main.c",
            "src/main.gcda",
            "src/main.gcno",
        ],
        "reverse_exit": 23,
    },
}

FIXTURE_PINS = {
    "HistoryProbe.pm": "3a847f50128166fd4d0a8ac71d885b88225d838260e2f73d29b9085546c6877f",
    "oracle-observations.json": "a9fbf31e2910f69930f812806ccb0d2cb61ca444916502936aae96c9b94bb6fa",
    "src/a.c": "b6582816b374197fceeaed1c7273f98f2a80349a619d594b7152135b12d22604",
    "src/a.gcda": "28c7c1aeeffbc339fc57e4dc8db89f211a4534d2f1afb1c02a803accf8aee84e",
    "src/a.gcno": "b8dfc1648558c09bd795845ec2bd0a75dc4c1207bcf34920dddd8d4844edd791",
    "src/b.c": "3acf005d76b1abd815251bdfc4a77118407593abb63487964a85793526e16fe4",
    "src/b.gcda": "3a4d62fd81294bd14e94da671e530434e2c9ad916fa47b5a060d96465fc4311a",
    "src/b.gcno": "face08d6311f2294f3ab65c522d0e28fa9552a8f68a83d62c4164d5ec930a78c",
    "src/c.c": "a7a700347b2a9c6e36b82874a031c61992a9ebf7511864814f9b0319ed03c4fb",
    "src/c.gcda": "96869ea3333711dd00287dfd96b0487b259f46815fa3ddb0611133a1a218912e",
    "src/c.gcno": "0a7367473fe921a766a42bf2b9ebd3546959b5b09b9fa021efae60cf7119b4ff",
    "src/main.c": "f8eba9adc93158d0b71b544a8c6199ca23bcd5e801decc4675454862db58f535",
    "src/main.gcda": "2dad38da749964bf469f9e271a544ae73eda86b309cf65eb9d8844b82692b814",
    "src/main.gcno": "b130e00c9211d006c198732080a64fc86500acd764e375343ca9fd90df282b97",
}


class ResidualACliHardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.obs = json.loads(OBS.read_text(encoding="utf-8"))
        cls.obs_by = {c["case_id"]: c for c in cls.obs["cases"]}
        cls.plans = {
            c["id"]: c
            for c in json.loads(FRAGMENT.read_text(encoding="utf-8"))["case_groups"]
        }

    def test_suite_passes_production_validator(self) -> None:
        residual.validate_suite_document(self.suite)
        residual.validate_committed_suite()

    def test_mutations_rejected(self) -> None:
        mutations = []

        def add(label, fn):
            m = copy.deepcopy(self.suite)
            fn(m)
            mutations.append((label, m))

        add("drop-history-flag", lambda s: s["cases"][1]["arguments"].remove("--history-script"))
        add(
            "replace-history-path",
            lambda s: s["cases"][1]["arguments"].__setitem__(
                s["cases"][1]["arguments"].index("./HistoryProbe.pm"), "./Other.pm"
            ),
        )
        add(
            "add-stdout",
            lambda s: s["cases"][0].__setitem__(
                "comparisons",
                residual.CMP2 + [{"dimension": "stdout", "normalizer": "exact-v1"}],
            ),
        )
        add(
            "add-stderr",
            lambda s: s["cases"][1].__setitem__(
                "comparisons",
                residual.CMP2 + [{"dimension": "stderr", "normalizer": "exact-v1"}],
            ),
        )
        add("drop-control-output", lambda s: s["cases"][0]["arguments"].remove("out.info"))
        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(residual.ResidualACliHardSuiteValidationError):
                    residual.validate_suite_document(mutated)

    def test_oracle_pins_and_relations(self) -> None:
        self.assertFalse(self.obs["product_compatibility_evidence"])
        self.assertEqual(
            self.obs.get("oracle_image"),
            "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7",
        )
        for cid, pin in PINNED.items():
            run = self.obs_by[cid]["reference_run"]
            self.assertEqual(run["exit_code"], pin["exit_code"], cid)
            self.assertEqual(run["file_count"], pin["file_count"], cid)
            self.assertEqual(run["file_tree_bytes"], pin["file_tree_bytes"], cid)
            self.assertEqual(run["file_tree_sha256"], pin["file_tree_sha256"], cid)
            self.assertEqual(run["paths"], pin["paths"], cid)
            self.assertEqual(self.obs_by[cid]["reverse_run"]["exit_code"], pin["reverse_exit"], cid)
            self.assertFalse(self.obs_by[cid]["product_compatibility_evidence"])
            self.assertEqual(self.obs_by[cid]["comparison_contract"], residual.CMP2)
        control = self.obs_by[CONTROL]["reference_run"]
        history = self.obs_by[HISTORY]["reference_run"]
        self.assertEqual(control["exit_code"], 0)
        self.assertEqual(history["exit_code"], 0)
        self.assertNotEqual(control["file_tree_sha256"], history["file_tree_sha256"])
        self.assertNotIn("history.loaded", control["paths"])
        self.assertIn("history.loaded", history["paths"])
        self.assertIn("out.info", control["paths"])
        self.assertIn("out.info", history["paths"])

    def test_fixture_hashes_locked(self) -> None:
        for name, digest in FIXTURE_PINS.items():
            self.assertEqual(
                hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(),
                digest,
                name,
            )

    def test_plans_reviewed(self) -> None:
        plan = self.plans["case.acceptance.command.geninfo.option.history-script"]
        self.assertEqual(plan["review_status"], "reviewed")
        self.assertEqual(plan["evidence_status"], "planned")
        self.assertEqual(plan["evidence"], [])
        self.assertIn("cli-option boundary", plan["description"])
        self.assertTrue(plan["suite_cases"])
        self.assertEqual(
            [sc["case_id"] for sc in plan["suite_cases"]],
            [CONTROL, HISTORY],
        )
        # Blocked targets must not appear as reviewed closed plans in this wave.
        for blocked in (
            "case.acceptance.command.geninfo.option.compat-libtool",
            "case.acceptance.command.lcov.option.compat-libtool",
            "case.acceptance.command.perl2lcov.option.preserve",
        ):
            self.assertNotIn(blocked, self.plans)


if __name__ == "__main__":
    unittest.main()
