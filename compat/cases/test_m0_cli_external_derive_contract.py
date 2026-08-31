#!/usr/bin/env python3
"""Validate external/no-external/derive-func-data CLI planning suite."""
from __future__ import annotations
import copy, hashlib, json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m0_cli_external_derive_contract as residual

ROOT = Path(__file__).resolve().parents[2]
SUITE = residual.SUITE_PATH
FIXTURE = ROOT / residual.FIXTURE
OBS = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-cli-external-derive-wave.json"
PINNED = {"m0-cli-external-derive-contract-lcov-external": {"exit_code": 0, "file_count": 5, "file_tree_bytes": 890, "file_tree_sha256": "d2ab2d1f45230261f13ccc386ac8fa42633e1e23eac25be2823eca7f246ab36a", "paths": ["external_headers/h.h", "out.info", "proj/main.c", "proj/main.gcda", "proj/main.gcno"], "reverse_exit": 23}, "m0-cli-external-derive-contract-lcov-no-external": {"exit_code": 0, "file_count": 5, "file_tree_bytes": 791, "file_tree_sha256": "d02981d1142b8cbad8b0a95e97d5835a7f0fdb4ba1ae6e53a0cd5ee661eb71d7", "paths": ["external_headers/h.h", "out.info", "proj/main.c", "proj/main.gcda", "proj/main.gcno"], "reverse_exit": 23}, "m0-cli-external-derive-contract-geninfo-external": {"exit_code": 0, "file_count": 5, "file_tree_bytes": 890, "file_tree_sha256": "d2ab2d1f45230261f13ccc386ac8fa42633e1e23eac25be2823eca7f246ab36a", "paths": ["external_headers/h.h", "out.info", "proj/main.c", "proj/main.gcda", "proj/main.gcno"], "reverse_exit": 23}, "m0-cli-external-derive-contract-geninfo-no-external": {"exit_code": 0, "file_count": 5, "file_tree_bytes": 791, "file_tree_sha256": "d02981d1142b8cbad8b0a95e97d5835a7f0fdb4ba1ae6e53a0cd5ee661eb71d7", "paths": ["external_headers/h.h", "out.info", "proj/main.c", "proj/main.gcda", "proj/main.gcno"], "reverse_exit": 23}, "m0-cli-external-derive-contract-lcov-derive-control": {"exit_code": 0, "file_count": 5, "file_tree_bytes": 890, "file_tree_sha256": "d2ab2d1f45230261f13ccc386ac8fa42633e1e23eac25be2823eca7f246ab36a", "paths": ["external_headers/h.h", "out.info", "proj/main.c", "proj/main.gcda", "proj/main.gcno"], "reverse_exit": 23}, "m0-cli-external-derive-contract-lcov-derive-func-data": {"exit_code": 1, "file_count": 4, "file_tree_bytes": 700, "file_tree_sha256": "fee28b0c5ac5034173979c40a283f32a84b958e7add0345fe2da9bb32b775c93", "paths": ["external_headers/h.h", "proj/main.c", "proj/main.gcda", "proj/main.gcno"], "reverse_exit": 23}}
FIXTURE_PINS = {"external_headers/h.h": "38ec51819d274e71d52b4bdbde7fedd8a66abb388d3f4a6ca4461d6a4a88c6eb", "oracle-observations.json": "8d2d8b9de8f319e0fadca6afbcc6ad83461855019e4c6921ed2a744c7b4edb47", "proj/main.c": "87d04d3a1a6f630414698cc8dc91a949889c10def114701cd61517761b84b7d5", "proj/main.gcda": "7df0253316764ef1bb6a1909766464e53a4303cbf024eb45aa1ca93cb431bf25", "proj/main.gcno": "e1c3d614e389a24b7aaccf28b233b64c714ffa3a88cbacddb875c42033a06c13"}


class ExternalDeriveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = json.loads(SUITE.read_text())
        cls.obs = json.loads(OBS.read_text())
        cls.obs_by = {c["case_id"]: c for c in cls.obs["cases"]}
        cls.plans = {c["id"]: c for c in json.loads(FRAGMENT.read_text())["case_groups"]}

    def test_suite_passes_production_validator(self):
        residual.validate_suite_document(self.suite)
        residual.validate_committed_suite()

    def test_mutations_rejected(self):
        mutations = []
        def add(label, fn):
            m = copy.deepcopy(self.suite); fn(m); mutations.append((label, m))
        add("drop-lcov-external", lambda s: s["cases"][0]["arguments"].remove("--external"))
        add("drop-lcov-no-external", lambda s: s["cases"][1]["arguments"].remove("--no-external"))
        add("drop-geninfo-external", lambda s: s["cases"][2]["arguments"].remove("--external"))
        add("drop-geninfo-no-external", lambda s: s["cases"][3]["arguments"].remove("--no-external"))
        add("drop-derive", lambda s: s["cases"][5]["arguments"].remove("--derive-func-data"))
        add("add-stdout", lambda s: s["cases"][0].__setitem__("comparisons", residual.CMP2 + [{"dimension":"stdout","normalizer":"exact-v1"}]))
        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(residual.ExternalDeriveSuiteValidationError):
                    residual.validate_suite_document(mutated)

    def test_oracle_pins_and_relations(self):
        self.assertFalse(self.obs["product_compatibility_evidence"])
        for cid, pin in PINNED.items():
            run = self.obs_by[cid]["reference_run"]
            self.assertEqual(run["exit_code"], pin["exit_code"], cid)
            self.assertEqual(run["file_count"], pin["file_count"], cid)
            self.assertEqual(run["file_tree_bytes"], pin["file_tree_bytes"], cid)
            self.assertEqual(run["file_tree_sha256"], pin["file_tree_sha256"], cid)
            self.assertEqual(run["paths"], pin["paths"], cid)
            self.assertEqual(self.obs_by[cid]["reverse_run"]["exit_code"], pin["reverse_exit"], cid)
        le = self.obs_by[f"{residual.SUITE_ID}-lcov-external"]["reference_run"]
        ln = self.obs_by[f"{residual.SUITE_ID}-lcov-no-external"]["reference_run"]
        ge = self.obs_by[f"{residual.SUITE_ID}-geninfo-external"]["reference_run"]
        gn = self.obs_by[f"{residual.SUITE_ID}-geninfo-no-external"]["reference_run"]
        dc = self.obs_by[f"{residual.SUITE_ID}-lcov-derive-control"]["reference_run"]
        dd = self.obs_by[f"{residual.SUITE_ID}-lcov-derive-func-data"]["reference_run"]
        self.assertEqual(le["exit_code"], 0)
        self.assertEqual(ln["exit_code"], 0)
        self.assertNotEqual(le["file_tree_sha256"], ln["file_tree_sha256"])
        self.assertGreater(le["file_tree_bytes"], ln["file_tree_bytes"])
        self.assertEqual(ge["file_tree_sha256"], le["file_tree_sha256"])
        self.assertEqual(gn["file_tree_sha256"], ln["file_tree_sha256"])
        self.assertEqual(dc["exit_code"], 0)
        self.assertEqual(dd["exit_code"], 1)
        self.assertIn("out.info", dc["paths"])
        self.assertNotIn("out.info", dd["paths"])
        self.assertNotEqual(dc["file_tree_sha256"], dd["file_tree_sha256"])

    def test_fixture_hashes_locked(self):
        for name, digest in FIXTURE_PINS.items():
            self.assertEqual(hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(), digest, name)

    def test_plans_reviewed(self):
        for pid in (
            "case.acceptance.command.geninfo.option.external",
            "case.acceptance.command.geninfo.option.no-external",
            "case.acceptance.command.lcov.option.external",
            "case.acceptance.command.lcov.option.no-external",
            "case.acceptance.command.lcov.option.derive-func-data",
        ):
            p = self.plans[pid]
            self.assertEqual(p["review_status"], "reviewed")
            self.assertEqual(p["evidence_status"], "planned")
            self.assertIn("cli-option boundary", p["description"])
            self.assertTrue(p["suite_cases"])


if __name__ == "__main__":
    unittest.main()
