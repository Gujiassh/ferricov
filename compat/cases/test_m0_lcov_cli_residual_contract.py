#!/usr/bin/env python3
"""Validate lcov residual CLI planning suite."""
from __future__ import annotations
import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m0_lcov_cli_residual_contract as residual

ROOT = Path(__file__).resolve().parents[2]
SUITE = residual.SUITE_PATH
FIXTURE = ROOT / residual.FIXTURE
OBS = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-lcov-cli-residual-wave.json"
PINNED = {'m0-lcov-cli-residual-contract-zero-control': {'file_tree_sha256': '09228a5e9f34b70c0aa83d26b6823130b1261398977b80bee285d02df44accca', 'file_tree_bytes': 726, 'file_count': 5, 'exit_code': 0, 'stdout_sha256': '553f99eb62b6dac64b08057e128411879b9f10b294517d82b8ef42c8796310c9', 'stderr_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'reverse_exit': 23, 'paths': ['branch/base.info', 'branch/br.c', 'src/hello.c', 'src/hello.gcda', 'src/hello.gcno']}, 'm0-lcov-cli-residual-contract-zerocounters': {'file_tree_sha256': 'ebd3e2edeaf161299bbd8f74c528750e00e726768f2b93230c5974e3867ef993', 'file_tree_bytes': 646, 'file_count': 4, 'exit_code': 0, 'stdout_sha256': '1764111da8d3594d042ed4c1d2d03cd70037b5dcc78a53502d05942913756ba2', 'stderr_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'reverse_exit': 23, 'paths': ['branch/base.info', 'branch/br.c', 'src/hello.c', 'src/hello.gcno']}, 'm0-lcov-cli-residual-contract-failbr-control': {'file_tree_sha256': '09228a5e9f34b70c0aa83d26b6823130b1261398977b80bee285d02df44accca', 'file_tree_bytes': 726, 'file_count': 5, 'exit_code': 0, 'stdout_sha256': 'ec440547c1d74b9a931db6fdcbcba8403beadc931add914fcf66c52286dcee3d', 'stderr_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'reverse_exit': 23, 'paths': ['branch/base.info', 'branch/br.c', 'src/hello.c', 'src/hello.gcda', 'src/hello.gcno']}, 'm0-lcov-cli-residual-contract-fail-under-branches': {'file_tree_sha256': '09228a5e9f34b70c0aa83d26b6823130b1261398977b80bee285d02df44accca', 'file_tree_bytes': 726, 'file_count': 5, 'exit_code': 1, 'stdout_sha256': '4f597221f55f668839492999e0d8ccecc0f0f5e0e187e5545afc5346c4ee9154', 'stderr_sha256': '0d1a3f3c4551f0a57bacfdfb0592da5e20056a1b4dfbb8b18a31b6b9ba723f8a', 'reverse_exit': 23, 'paths': ['branch/base.info', 'branch/br.c', 'src/hello.c', 'src/hello.gcda', 'src/hello.gcno']}}
FIXTURE_PINS = {'src/hello.c': '078d5e4e637d5d8f25c2d0b7d185a6cd5a97be361a88ef77864339a923f96606', 'src/hello.gcda': 'bfcc8d193f917fd19d8725d65e22354e0a1acb0cf78c963dd1229b84a86ceb91', 'src/hello.gcno': 'ab03749993c352bfc18a56dae872cb29062af6ea6a84f03e73e745308b667b05', 'branch/base.info': '97ac70d954bd43a5edc4f4f87ad20df20607ee667745d7bf335804ce9b571e97', 'branch/br.c': 'fac6697ad69ce00f33dc7f009c9117ade6ca0240746af3f6c9eab3b696b1090d', 'oracle-observations.json': '893a1fc39881b0f76ed404e09cae51fd97a3313d39abaf937fd825776bf84c86'}

class LcovCliResidualContractTests(unittest.TestCase):
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
        add("drop-zerocounters", lambda s: s["cases"][1]["arguments"].remove("--zerocounters"))
        add("rename-directory", lambda s: s["cases"][1]["arguments"].__setitem__(s["cases"][1]["arguments"].index("src"), "other"))
        add("drop-fail-under", lambda s: s["cases"][3]["arguments"].remove("--fail-under-branches"))
        add("change-threshold", lambda s: s["cases"][3]["arguments"].__setitem__(s["cases"][3]["arguments"].index("101"), "50"))
        add("drop-branch-coverage", lambda s: s["cases"][3]["arguments"].remove("--branch-coverage"))
        add("add-stdout-to-zero", lambda s: s["cases"][0].__setitem__("comparisons", residual.EXACT2 + [{"dimension":"stdout","normalizer":"exact-v1"}]))
        add("reorder-failbr-comparisons", lambda s: s["cases"][2].__setitem__("comparisons", list(reversed(list(residual.EXACT4)))))
        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(residual.LcovResidualSuiteValidationError):
                    residual.validate_suite_document(mutated)

    def test_oracle_pins_and_relations(self):
        self.assertFalse(self.obs["product_compatibility_evidence"])
        for cid, pin in PINNED.items():
            run = self.obs_by[cid]["reference_run"]
            self.assertEqual(run["exit_code"], pin["exit_code"], cid)
            self.assertEqual(run["file_count"], pin["file_count"], cid)
            self.assertEqual(run["file_tree_bytes"], pin["file_tree_bytes"], cid)
            self.assertEqual(run["file_tree_sha256"], pin["file_tree_sha256"], cid)
            self.assertEqual(run["stdout_sha256"], pin["stdout_sha256"], cid)
            self.assertEqual(run["stderr_sha256"], pin["stderr_sha256"], cid)
            self.assertEqual(run["paths"], pin["paths"], cid)
            self.assertEqual(self.obs_by[cid]["reverse_run"]["exit_code"], pin["reverse_exit"], cid)
        zc = self.obs_by[f"{residual.SUITE_ID}-zero-control"]["reference_run"]
        zz = self.obs_by[f"{residual.SUITE_ID}-zerocounters"]["reference_run"]
        fc = self.obs_by[f"{residual.SUITE_ID}-failbr-control"]["reference_run"]
        ff = self.obs_by[f"{residual.SUITE_ID}-fail-under-branches"]["reference_run"]
        self.assertIn("src/hello.gcda", zc["paths"])
        self.assertNotIn("src/hello.gcda", zz["paths"])
        self.assertEqual(zc["exit_code"], 0)
        self.assertEqual(zz["exit_code"], 0)
        self.assertNotEqual(zc["file_tree_sha256"], zz["file_tree_sha256"])
        self.assertEqual(fc["exit_code"], 0)
        self.assertEqual(ff["exit_code"], 1)
        self.assertNotEqual(fc["stdout_sha256"], ff["stdout_sha256"])
        for case in self.suite["cases"]:
            o = self.obs_by[case["id"]]
            self.assertEqual(o["arguments"], case["arguments"])
            self.assertEqual(o["comparison_contract"], case["comparisons"])
            self.assertFalse(o["product_compatibility_evidence"])

    def test_fixture_hashes_locked(self):
        for name, digest in FIXTURE_PINS.items():
            self.assertEqual(hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(), digest, name)

    def test_plans_reviewed_and_boundary_not_version(self):
        import subprocess, sys
        # plan bindings checked after generate; here check description has cli-option boundary for zerocounters
        z = self.plans["case.acceptance.command.lcov.option.zerocounters"]
        self.assertIn("cli-option boundary `--zerocounters`", z["description"])
        self.assertNotIn("`--version`", z["description"])
        for pid in (
            "case.acceptance.command.lcov.option.zerocounters",
            "case.acceptance.command.lcov.option.fail-under-branches",
        ):
            p = self.plans[pid]
            self.assertEqual(p["review_status"], "reviewed")
            self.assertEqual(p["evidence_status"], "planned")
            self.assertTrue(p["suite_cases"])

if __name__ == "__main__":
    unittest.main()
