#!/usr/bin/env python3
"""Validate genhtml hard residual CLI planning suite."""
from __future__ import annotations
import copy, hashlib, json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m0_cli_genhtml_hard2_contract as residual

ROOT = Path(__file__).resolve().parents[2]
SUITE = residual.SUITE_PATH
FIXTURE = ROOT / residual.FIXTURE
OBS = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-cli-genhtml-hard2-wave.json"
PINNED = {"m0-cli-genhtml-hard2-contract-debug-control": {"exit_code": 0, "file_count": 17, "file_tree_bytes": 46787, "file_tree_sha256": "009526230a1a9d2e2cd3154dfc8585eb9f21d09756405bec5b2a93ebf97de107", "paths": ["control.lcovrc", "input.info", "input2.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}, "m0-cli-genhtml-hard2-contract-debug": {"exit_code": 0, "file_count": 17, "file_tree_bytes": 46795, "file_tree_sha256": "30a61e6cdada14a3e7ae854cb0dbfe243d8e3a5d8f5f85dbe6f39b3b143f7a8e", "paths": ["control.lcovrc", "input.info", "input2.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}, "m0-cli-genhtml-hard2-contract-baseline-control": {"exit_code": 0, "file_count": 17, "file_tree_bytes": 55194, "file_tree_sha256": "7f73e8978817776636975f594ac3040ecc28310adf36fd92a280eb3ef39f6ffc", "paths": ["control.lcovrc", "input.info", "input2.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}, "m0-cli-genhtml-hard2-contract-new-file-as-baseline": {"exit_code": 0, "file_count": 17, "file_tree_bytes": 55217, "file_tree_sha256": "8caf65cc0f8748932cea3bbeee4adafb8e51a6225bdc368052c73060d21f7ab7", "paths": ["control.lcovrc", "input.info", "input2.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}}
FIXTURE_PINS = {"control.lcovrc": "52ae4f1a03b9eeb76181421e2fdd07df004ba23bccafad30cf8d8f12cfb7671c", "input.info": "a854b67fff921b6bfb53a8a2a8349b90f93a676de555682ab235d50b1fa6e45d", "input2.info": "e41be369da6cc87c54858aa659055549e7c3130bba21be3f25b84f2ee38ecc32", "oracle-observations.json": "615e4b71aaffd2e73b78feb039c25aaea8086a364c77d9b1bfcf775aee8da7e2", "source.c": "dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f"}

class GenhtmlHard2ContractTests(unittest.TestCase):
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
        add("drop-debug", lambda s: s["cases"][1]["arguments"].remove("--debug"))
        add("drop-nfasb", lambda s: s["cases"][3]["arguments"].remove("--new-file-as-baseline"))
        add("drop-baseline", lambda s: s["cases"][3]["arguments"].remove("--baseline-file"))
        add("add-stdout", lambda s: s["cases"][0].__setitem__("comparisons", residual.CMP2 + [{"dimension":"stdout","normalizer":"exact-v1"}]))
        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(residual.GenhtmlHard2SuiteValidationError):
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
        dc = self.obs_by[f"{residual.SUITE_ID}-debug-control"]["reference_run"]
        dd = self.obs_by[f"{residual.SUITE_ID}-debug"]["reference_run"]
        bc = self.obs_by[f"{residual.SUITE_ID}-baseline-control"]["reference_run"]
        nb = self.obs_by[f"{residual.SUITE_ID}-new-file-as-baseline"]["reference_run"]
        self.assertNotEqual(dc["file_tree_sha256"], dd["file_tree_sha256"])
        self.assertNotEqual(bc["file_tree_sha256"], nb["file_tree_sha256"])
        self.assertEqual(dc["exit_code"], 0)
        self.assertEqual(dd["exit_code"], 0)
        self.assertEqual(bc["exit_code"], 0)
        self.assertEqual(nb["exit_code"], 0)

    def test_fixture_hashes_locked(self):
        for name, digest in FIXTURE_PINS.items():
            self.assertEqual(hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest(), digest, name)

    def test_plans_reviewed(self):
        for pid in (
            "case.acceptance.command.genhtml.option.debug",
            "case.acceptance.command.genhtml.option.new-file-as-baseline",
        ):
            p = self.plans[pid]
            self.assertEqual(p["review_status"], "reviewed")
            self.assertEqual(p["evidence_status"], "planned")
            self.assertIn("cli-option boundary", p["description"])
            self.assertTrue(p["suite_cases"])

if __name__ == "__main__":
    unittest.main()
