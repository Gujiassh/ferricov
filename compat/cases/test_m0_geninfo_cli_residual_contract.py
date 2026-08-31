#!/usr/bin/env python3
"""Validate geninfo residual CLI planning suite."""
from __future__ import annotations
import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m0_geninfo_cli_residual_contract as residual

ROOT = Path(__file__).resolve().parents[2]
SUITE = residual.SUITE_PATH
FIXTURE = ROOT / residual.FIXTURE
OBS = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-geninfo-cli-residual-wave.json"
PINNED = {'m0-geninfo-cli-residual-contract-control': {'file_tree_sha256': '602c7c883fb8f72e5d8cef419836dea1f3f6355dad1604cb1cc45a9a0c859a23', 'file_tree_bytes': 532, 'file_count': 4, 'exit_code': 0, 'reverse_exit': 23}, 'm0-geninfo-cli-residual-contract-output-filename': {'file_tree_sha256': '2fa3466172b50bb680a8be66883dea328af1b331f28cee4c92172615d9e57586', 'file_tree_bytes': 532, 'file_count': 4, 'exit_code': 0, 'reverse_exit': 23}, 'm0-geninfo-cli-residual-contract-checksum-control': {'file_tree_sha256': 'adb7eb07e4ea21b3af7de8f7eb255e7f1c67b400d86182de69c998209cfaa5ce', 'file_tree_bytes': 601, 'file_count': 4, 'exit_code': 0, 'reverse_exit': 23}, 'm0-geninfo-cli-residual-contract-no-checksum': {'file_tree_sha256': '602c7c883fb8f72e5d8cef419836dea1f3f6355dad1604cb1cc45a9a0c859a23', 'file_tree_bytes': 532, 'file_count': 4, 'exit_code': 0, 'reverse_exit': 23}}
FIXTURE_PINS = {'src/hello.c': '078d5e4e637d5d8f25c2d0b7d185a6cd5a97be361a88ef77864339a923f96606', 'src/hello.gcno': 'ab03749993c352bfc18a56dae872cb29062af6ea6a84f03e73e745308b667b05', 'src/hello.gcda': 'bfcc8d193f917fd19d8725d65e22354e0a1acb0cf78c963dd1229b84a86ceb91', 'oracle-observations.json': '607d604910b39b48d3ba1a8b47f1c1bb0922847f7428ad175186a16acce13cc7'}

class GeninfoCliResidualContractTests(unittest.TestCase):
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
        add("drop-output-filename", lambda s: s["cases"][1]["arguments"].remove("--output-filename"))
        add("rename-custom-info", lambda s: s["cases"][1]["arguments"].__setitem__(s["cases"][1]["arguments"].index("custom.info"), "other.info"))
        add("drop-no-checksum", lambda s: s["cases"][3]["arguments"].remove("--no-checksum"))
        add("drop-checksum-from-nocheck", lambda s: s["cases"][3]["arguments"].remove("--checksum"))
        add("add-stdout-dim", lambda s: s["cases"][0].__setitem__("comparisons", residual.CMP2 + [{"dimension":"stdout","normalizer":"exact-v1"}]))
        add("add-stderr-dim", lambda s: s["cases"][0].__setitem__("comparisons", residual.CMP2 + [{"dimension":"stderr","normalizer":"exact-v1"}]))
        add("reorder-comparisons", lambda s: s["cases"][0].__setitem__("comparisons", list(reversed(list(residual.CMP2)))))
        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(residual.GeninfoResidualSuiteValidationError):
                    residual.validate_suite_document(mutated)
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "suite.json"
                    path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
                    with self.assertRaises(residual.GeninfoResidualSuiteValidationError):
                        residual.validate_suite_path(path)

    def test_oracle_pins_and_relations(self):
        self.assertFalse(self.obs["product_compatibility_evidence"])
        for cid, pin in PINNED.items():
            run = self.obs_by[cid]["reference_run"]
            self.assertEqual(run["exit_code"], pin["exit_code"], cid)
            self.assertEqual(run["file_count"], pin["file_count"], cid)
            self.assertEqual(run["file_tree_bytes"], pin["file_tree_bytes"], cid)
            self.assertEqual(run["file_tree_sha256"], pin["file_tree_sha256"], cid)
            self.assertEqual(self.obs_by[cid]["reverse_run"]["exit_code"], pin["reverse_exit"], cid)
        ctrl = self.obs_by[f"{residual.SUITE_ID}-control"]["reference_run"]
        out = self.obs_by[f"{residual.SUITE_ID}-output-filename"]["reference_run"]
        ck = self.obs_by[f"{residual.SUITE_ID}-checksum-control"]["reference_run"]
        nc = self.obs_by[f"{residual.SUITE_ID}-no-checksum"]["reference_run"]
        self.assertEqual(ctrl["file_tree_sha256"], nc["file_tree_sha256"])
        self.assertEqual(ctrl["file_tree_bytes"], out["file_tree_bytes"])
        self.assertNotEqual(ctrl["file_tree_sha256"], out["file_tree_sha256"])
        self.assertGreater(ck["file_tree_bytes"], nc["file_tree_bytes"])
        self.assertNotEqual(ck["file_tree_sha256"], nc["file_tree_sha256"])
        for case in self.suite["cases"]:
            o = self.obs_by[case["id"]]
            self.assertEqual(o["arguments"], case["arguments"])
            self.assertEqual(o["comparison_contract"], case["comparisons"])
            self.assertFalse(o["product_compatibility_evidence"])

    def test_fixture_hashes_locked(self):
        for name, digest in FIXTURE_PINS.items():
            self.assertEqual(hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(), digest, name)

    def test_plans_reviewed(self):
        for pid in (
            "case.acceptance.command.geninfo.option.output-filename",
            "case.acceptance.command.geninfo.option.no-checksum",
        ):
            p = self.plans[pid]
            self.assertEqual(p["review_status"], "reviewed")
            self.assertEqual(p["evidence_status"], "planned")
            self.assertTrue(p["suite_cases"])

if __name__ == "__main__":
    unittest.main()
