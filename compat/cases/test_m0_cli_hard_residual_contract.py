#!/usr/bin/env python3
"""Validate hard residual CLI planning suite (large-file + geninfo debug)."""
from __future__ import annotations
import copy, hashlib, json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m0_cli_hard_residual_contract as residual

ROOT = Path(__file__).resolve().parents[2]
SUITE = residual.SUITE_PATH
FIXTURE = ROOT / residual.FIXTURE
OBS = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-cli-hard-residual-wave.json"
PINNED = {"m0-cli-hard-residual-contract-geninfo-control": {"exit_code": 0, "file_count": 4, "file_tree_bytes": 532, "file_tree_sha256": "b551a3a4ed5062fb2b83caa57fe353928cffc5a2298ecd4ba56bb3647f202406", "paths": ["out.info", "src/hello.c", "src/hello.gcda", "src/hello.gcno"], "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "reverse_exit": 23}, "m0-cli-hard-residual-contract-geninfo-large-file-invalid": {"exit_code": 2, "file_count": 3, "file_tree_bytes": 427, "file_tree_sha256": "80c3f38c5974cea05d0b92b13c8ecd7744bea0d7a2ad65b8429806182f3b7f3b", "paths": ["src/hello.c", "src/hello.gcda", "src/hello.gcno"], "stderr_sha256": "17ccfe9c48e70be8b916e98f4a626931cad1cac5aea87b05bd648a8f36a6b08c", "reverse_exit": 23}, "m0-cli-hard-residual-contract-lcov-control": {"exit_code": 0, "file_count": 4, "file_tree_bytes": 532, "file_tree_sha256": "b551a3a4ed5062fb2b83caa57fe353928cffc5a2298ecd4ba56bb3647f202406", "paths": ["out.info", "src/hello.c", "src/hello.gcda", "src/hello.gcno"], "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "reverse_exit": 23}, "m0-cli-hard-residual-contract-lcov-large-file-invalid": {"exit_code": 2, "file_count": 3, "file_tree_bytes": 427, "file_tree_sha256": "80c3f38c5974cea05d0b92b13c8ecd7744bea0d7a2ad65b8429806182f3b7f3b", "paths": ["src/hello.c", "src/hello.gcda", "src/hello.gcno"], "stderr_sha256": "aeec91a3dabc10bdc8070916cff6b16683f1c2a4433927798055f30ce0d06aca", "reverse_exit": 23}, "m0-cli-hard-residual-contract-geninfo-debug-control": {"exit_code": 0, "file_count": 4, "file_tree_bytes": 532, "file_tree_sha256": "b551a3a4ed5062fb2b83caa57fe353928cffc5a2298ecd4ba56bb3647f202406", "paths": ["out.info", "src/hello.c", "src/hello.gcda", "src/hello.gcno"], "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "reverse_exit": 23}, "m0-cli-hard-residual-contract-geninfo-debug": {"exit_code": 0, "file_count": 4, "file_tree_bytes": 532, "file_tree_sha256": "b551a3a4ed5062fb2b83caa57fe353928cffc5a2298ecd4ba56bb3647f202406", "paths": ["out.info", "src/hello.c", "src/hello.gcda", "src/hello.gcno"], "stderr_sha256": "133f428c3e393eb50ca1ff79691f0320a6371007f642b1b9795ca0a1e40c6334", "reverse_exit": 23}}
FIXTURE_PINS = {"oracle-observations.json": "c63f4f334eeb943922a16236cfba1ba9b05156e284b94c091a00fd0c5236dc10", "src/hello.c": "078d5e4e637d5d8f25c2d0b7d185a6cd5a97be361a88ef77864339a923f96606", "src/hello.gcda": "bfcc8d193f917fd19d8725d65e22354e0a1acb0cf78c963dd1229b84a86ceb91", "src/hello.gcno": "ab03749993c352bfc18a56dae872cb29062af6ea6a84f03e73e745308b667b05"}

class HardResidualContractTests(unittest.TestCase):
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
        add("drop-large-file", lambda s: s["cases"][1]["arguments"].remove("--large-file"))
        add("fix-regexp", lambda s: s["cases"][1]["arguments"].__setitem__(s["cases"][1]["arguments"].index("("), "hello"))
        add("drop-lcov-large-file", lambda s: s["cases"][3]["arguments"].remove("--large-file"))
        add("drop-debug", lambda s: s["cases"][5]["arguments"].remove("--debug"))
        add("add-stdout-large", lambda s: s["cases"][0].__setitem__("comparisons", residual.CMP2 + [{"dimension":"stdout","normalizer":"exact-v1"}]))
        add("drop-stderr-debug", lambda s: s["cases"][5].__setitem__("comparisons", residual.CMP2))
        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(residual.HardResidualSuiteValidationError):
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
            self.assertEqual(run["stderr_sha256"], pin["stderr_sha256"], cid)
            self.assertEqual(self.obs_by[cid]["reverse_run"]["exit_code"], pin["reverse_exit"], cid)
        gc = self.obs_by[f"{residual.SUITE_ID}-geninfo-control"]["reference_run"]
        gi = self.obs_by[f"{residual.SUITE_ID}-geninfo-large-file-invalid"]["reference_run"]
        lc = self.obs_by[f"{residual.SUITE_ID}-lcov-control"]["reference_run"]
        li = self.obs_by[f"{residual.SUITE_ID}-lcov-large-file-invalid"]["reference_run"]
        dc = self.obs_by[f"{residual.SUITE_ID}-geninfo-debug-control"]["reference_run"]
        dd = self.obs_by[f"{residual.SUITE_ID}-geninfo-debug"]["reference_run"]
        self.assertEqual(gc["exit_code"], 0)
        self.assertEqual(gi["exit_code"], 2)
        self.assertIn("out.info", gc["paths"])
        self.assertNotIn("out.info", gi["paths"])
        self.assertEqual(lc["exit_code"], 0)
        self.assertEqual(li["exit_code"], 2)
        self.assertNotIn("out.info", li["paths"])
        self.assertEqual(dc["exit_code"], 0)
        self.assertEqual(dd["exit_code"], 0)
        self.assertEqual(dc["file_tree_sha256"], dd["file_tree_sha256"])
        self.assertNotEqual(dc["stderr_sha256"], dd["stderr_sha256"])
        self.assertEqual(dc["stderr_bytes"] if "stderr_bytes" in dc else 0, 0)
        self.assertGreater(dd["stderr_bytes"], 0)

    def test_fixture_hashes_locked(self):
        for name, digest in FIXTURE_PINS.items():
            self.assertEqual(hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(), digest, name)

    def test_plans_reviewed(self):
        for pid in (
            "case.acceptance.command.geninfo.option.large-file",
            "case.acceptance.command.lcov.option.large-file",
            "case.acceptance.command.geninfo.option.debug",
        ):
            p = self.plans[pid]
            self.assertEqual(p["review_status"], "reviewed")
            self.assertEqual(p["evidence_status"], "planned")
            self.assertIn("cli-option boundary", p["description"])
            self.assertTrue(p["suite_cases"])

if __name__ == "__main__":
    unittest.main()
