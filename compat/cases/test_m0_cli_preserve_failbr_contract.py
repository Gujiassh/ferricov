#!/usr/bin/env python3
"""Validate preserve/fail-under-branches CLI planning suite."""
from __future__ import annotations
import copy, hashlib, json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m0_cli_preserve_failbr_contract as residual

ROOT = Path(__file__).resolve().parents[2]
SUITE = residual.SUITE_PATH
FIXTURE = ROOT / residual.FIXTURE
OBS = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-cli-preserve-failbr-wave.json"
PINNED = {'m0-cli-preserve-failbr-contract-geninfo-control': {'exit_code': 0, 'file_count': 4, 'file_tree_bytes': 753, 'file_tree_sha256': 'e3762c14e155f19f749e79f27641e98e90053d5c85258f90d4824fa81417c24b', 'paths': ['out.info', 'src/br.c', 'src/br.gcda', 'src/br.gcno'], 'reverse_exit': 23}, 'm0-cli-preserve-failbr-contract-geninfo-preserve': {'exit_code': 0, 'file_count': 5, 'file_tree_bytes': 1062, 'file_tree_sha256': '45754e083b5744e2e58f934369e7d7ac754bc75386fe02dcd33c6e6304b5b8ac', 'paths': ['out.info', 'src/br##a46c7c4268b3fc8df7e2587a673d5263.gcov.json.gz', 'src/br.c', 'src/br.gcda', 'src/br.gcno'], 'reverse_exit': 23}, 'm0-cli-preserve-failbr-contract-geninfo-failbr-control': {'exit_code': 0, 'file_count': 4, 'file_tree_bytes': 792, 'file_tree_sha256': '924819c8e43c0b8b710d04d1d9cb69f9267118702259e220fcaea59f51a7fd75', 'paths': ['out.info', 'src/br.c', 'src/br.gcda', 'src/br.gcno'], 'reverse_exit': 23}, 'm0-cli-preserve-failbr-contract-geninfo-fail-under-branches': {'exit_code': 1, 'file_count': 4, 'file_tree_bytes': 792, 'file_tree_sha256': '924819c8e43c0b8b710d04d1d9cb69f9267118702259e220fcaea59f51a7fd75', 'paths': ['out.info', 'src/br.c', 'src/br.gcda', 'src/br.gcno'], 'reverse_exit': 23}, 'm0-cli-preserve-failbr-contract-lcov-control': {'exit_code': 0, 'file_count': 4, 'file_tree_bytes': 753, 'file_tree_sha256': 'e3762c14e155f19f749e79f27641e98e90053d5c85258f90d4824fa81417c24b', 'paths': ['out.info', 'src/br.c', 'src/br.gcda', 'src/br.gcno'], 'reverse_exit': 23}, 'm0-cli-preserve-failbr-contract-lcov-preserve': {'exit_code': 0, 'file_count': 5, 'file_tree_bytes': 1062, 'file_tree_sha256': '45754e083b5744e2e58f934369e7d7ac754bc75386fe02dcd33c6e6304b5b8ac', 'paths': ['out.info', 'src/br##a46c7c4268b3fc8df7e2587a673d5263.gcov.json.gz', 'src/br.c', 'src/br.gcda', 'src/br.gcno'], 'reverse_exit': 23}}
FIXTURE_PINS = {'src/br.c': 'fac6697ad69ce00f33dc7f009c9117ade6ca0240746af3f6c9eab3b696b1090d', 'src/br.gcda': '6e00a1f320b0c6e067e5e4878d56f713d4c1e0cc259c5ab083cc65c782278b4e', 'src/br.gcno': '0d11985bdf2e03aa84d94d8d011c5845eecc0ea11bd396edb14f0d62872a31dc', 'oracle-observations.json': 'c2c28a9c8bfa725071a4a9aa16b4489c50d5e3ce105ef659fe9847ff222c1251'}

class PreserveFailbrContractTests(unittest.TestCase):
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
        add("drop-preserve", lambda s: s["cases"][1]["arguments"].remove("--preserve"))
        add("drop-fail-under", lambda s: s["cases"][3]["arguments"].remove("--fail-under-branches"))
        add("change-threshold", lambda s: s["cases"][3]["arguments"].__setitem__(s["cases"][3]["arguments"].index("101"), "50"))
        add("drop-lcov-preserve", lambda s: s["cases"][5]["arguments"].remove("--preserve"))
        add("add-stdout", lambda s: s["cases"][0].__setitem__("comparisons", residual.CMP2 + [{"dimension":"stdout","normalizer":"exact-v1"}]))
        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(residual.PreserveFailbrSuiteValidationError):
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
        gc = self.obs_by[f"{residual.SUITE_ID}-geninfo-control"]["reference_run"]
        gp = self.obs_by[f"{residual.SUITE_ID}-geninfo-preserve"]["reference_run"]
        fbo = self.obs_by[f"{residual.SUITE_ID}-geninfo-failbr-control"]["reference_run"]
        fb = self.obs_by[f"{residual.SUITE_ID}-geninfo-fail-under-branches"]["reference_run"]
        lc = self.obs_by[f"{residual.SUITE_ID}-lcov-control"]["reference_run"]
        lp = self.obs_by[f"{residual.SUITE_ID}-lcov-preserve"]["reference_run"]
        self.assertFalse(any(p.endswith(".gcov.json.gz") for p in gc["paths"]))
        self.assertTrue(any(p.endswith(".gcov.json.gz") for p in gp["paths"]))
        self.assertFalse(any(p.endswith(".gcov.json.gz") for p in lc["paths"]))
        self.assertTrue(any(p.endswith(".gcov.json.gz") for p in lp["paths"]))
        self.assertEqual(fbo["exit_code"], 0)
        self.assertEqual(fb["exit_code"], 1)
        self.assertNotEqual(gc["file_tree_sha256"], gp["file_tree_sha256"])
        self.assertNotEqual(lc["file_tree_sha256"], lp["file_tree_sha256"])

    def test_fixture_hashes_locked(self):
        for name, digest in FIXTURE_PINS.items():
            self.assertEqual(hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(), digest, name)

    def test_plans_reviewed(self):
        for pid in (
            "case.acceptance.command.geninfo.option.preserve",
            "case.acceptance.command.geninfo.option.fail-under-branches",
            "case.acceptance.command.lcov.option.preserve",
        ):
            p = self.plans[pid]
            self.assertEqual(p["review_status"], "reviewed")
            self.assertEqual(p["evidence_status"], "planned")
            self.assertIn("cli-option boundary", p["description"])

if __name__ == "__main__":
    unittest.main()
