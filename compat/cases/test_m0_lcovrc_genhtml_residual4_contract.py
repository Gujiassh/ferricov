#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m0_lcovrc_genhtml_residual4_contract as residual
ROOT=Path(__file__).resolve().parents[2]
PINNED={"m0-lcovrc-genhtml-residual4-contract-control": {"exit_code": 0, "file_count": 19, "file_tree_bytes": 46697, "file_tree_sha256": "06a0a5d034115e0fb0d708eafc1386e61af7d7d5251c431368c7db497dc698ee", "paths": ["control.lcovrc", "css.lcovrc", "date-bins.lcovrc", "input.info", "owner-table.lcovrc", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}, "m0-lcovrc-genhtml-residual4-contract-css": {"exit_code": 1, "file_count": 7, "file_tree_bytes": 456, "file_tree_sha256": "dc9d6e1153ab1e285ac8332b03c45763940ea7388183800c6e83de845e7c8152", "paths": ["control.lcovrc", "css.lcovrc", "date-bins.lcovrc", "input.info", "owner-table.lcovrc", "report/cmd_line", "source.c"], "reverse_exit": 23}, "m0-lcovrc-genhtml-residual4-contract-date-bins": {"exit_code": 255, "file_count": 6, "file_tree_bytes": 386, "file_tree_sha256": "84d9bf9824a24fa831a198ce0b5626e4e1ef89f8be05ce7ef50d55e62171c74f", "paths": ["control.lcovrc", "css.lcovrc", "date-bins.lcovrc", "input.info", "owner-table.lcovrc", "source.c"], "reverse_exit": 23}, "m0-lcovrc-genhtml-residual4-contract-owner-table": {"exit_code": 255, "file_count": 6, "file_tree_bytes": 386, "file_tree_sha256": "84d9bf9824a24fa831a198ce0b5626e4e1ef89f8be05ce7ef50d55e62171c74f", "paths": ["control.lcovrc", "css.lcovrc", "date-bins.lcovrc", "input.info", "owner-table.lcovrc", "source.c"], "reverse_exit": 23}}
FIXTURE_PINS={"control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15", "css.lcovrc": "ebc3a15a8fffe77bfe2cce0b899a18cdee2d322743023fe168905b92b109850c", "date-bins.lcovrc": "eaedafb3b397dea9a761ce9c379a43710d5d52a8ec445c530e9b939c48acde28", "input.info": "a854b67fff921b6bfb53a8a2a8349b90f93a676de555682ab235d50b1fa6e45d", "oracle-observations.json": "071371893ee67468c02a4430598e79434bd236ab65181425d432378dcb5e9a19", "owner-table.lcovrc": "050ef483f6d4fc2d59ad04782815a956684d9cfb8ffe1023de740539795b4a61", "source.c": "dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f"}
PLAN_IDS=["case.acceptance.lcovrc.genhtml-css-file", "case.acceptance.lcovrc.genhtml-date-bins", "case.acceptance.lcovrc.genhtml-show-owner-table"]
class T(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.suite=json.loads(residual.SUITE_PATH.read_text())
    cls.obs=json.loads((ROOT/residual.FIXTURE/"oracle-observations.json").read_text())
    cls.obs_by={c["case_id"]:c for c in cls.obs["cases"]}
    cls.plans={c["id"]:c for c in json.loads((ROOT/"compat/behavior/fragments/authored/m0-lcovrc-genhtml-residual4-wave.json").read_text())["case_groups"]}
  def test_suite(self):
    residual.validate_suite_document(self.suite); residual.validate_committed_suite()
  def test_mutations(self):
    m=copy.deepcopy(self.suite); m["cases"][1]["arguments"]=list(m["cases"][0]["arguments"])
    with self.assertRaises(residual.Err): residual.validate_suite_document(m)
  def test_oracle(self):
    self.assertFalse(self.obs["product_compatibility_evidence"])
    ctrl=self.obs_by[f"{residual.SUITE_ID}-control"]["reference_run"]
    for cid,pin in PINNED.items():
      run=self.obs_by[cid]["reference_run"]
      self.assertEqual(run["exit_code"],pin["exit_code"],cid)
      self.assertEqual(run["file_tree_sha256"],pin["file_tree_sha256"],cid)
      if cid!=f"{residual.SUITE_ID}-control":
        self.assertTrue(run["exit_code"]!=ctrl["exit_code"] or run["file_tree_sha256"]!=ctrl["file_tree_sha256"], cid)
  def test_fixture(self):
    for n,d in FIXTURE_PINS.items():
      self.assertEqual(hashlib.sha256((ROOT/residual.FIXTURE/n).read_bytes()).hexdigest(),d,n)
  def test_plans(self):
    for pid in PLAN_IDS:
      p=self.plans[pid]
      self.assertEqual(p["review_status"],"reviewed")
      self.assertEqual(p["evidence_status"],"planned")
      self.assertTrue(p["suite_cases"])
if __name__=="__main__": unittest.main()
