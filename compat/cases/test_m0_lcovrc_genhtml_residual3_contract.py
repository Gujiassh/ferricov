#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m0_lcovrc_genhtml_residual3_contract as residual
ROOT=Path(__file__).resolve().parents[2]
PINNED={"m0-lcovrc-genhtml-residual3-contract-control": {"exit_code": 0, "file_count": 20, "file_tree_bytes": 46734, "file_tree_sha256": "7b17b20e53bd1429dd81d13e5026a326d9c73883a0c4dfe9f448cba086af356f", "paths": ["compact-summary-tables.lcovrc", "control.lcovrc", "fail-under-branches.lcovrc", "fail-under-lines.lcovrc", "input.info", "list-truncate-max.lcovrc", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}, "m0-lcovrc-genhtml-residual3-contract-compact-summary-tables": {"exit_code": 0, "file_count": 20, "file_tree_bytes": 46749, "file_tree_sha256": "8f45b5048c047b1b82107ba09b5e39e022b6b6af1028c51c6aedd4e24babeb7e", "paths": ["compact-summary-tables.lcovrc", "control.lcovrc", "fail-under-branches.lcovrc", "fail-under-lines.lcovrc", "input.info", "list-truncate-max.lcovrc", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}, "m0-lcovrc-genhtml-residual3-contract-fail-under-lines": {"exit_code": 1, "file_count": 20, "file_tree_bytes": 46743, "file_tree_sha256": "078fcf2714033c98a6b3d22068fac3e29800504e8c9cc4236e55d0ff1ba3cfab", "paths": ["compact-summary-tables.lcovrc", "control.lcovrc", "fail-under-branches.lcovrc", "fail-under-lines.lcovrc", "input.info", "list-truncate-max.lcovrc", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}, "m0-lcovrc-genhtml-residual3-contract-fail-under-branches": {"exit_code": 0, "file_count": 20, "file_tree_bytes": 46746, "file_tree_sha256": "8f290930ce8f2b578390641fb225a1d5dfc9858ca4311da3cd281db37e80075f", "paths": ["compact-summary-tables.lcovrc", "control.lcovrc", "fail-under-branches.lcovrc", "fail-under-lines.lcovrc", "input.info", "list-truncate-max.lcovrc", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}, "m0-lcovrc-genhtml-residual3-contract-list-truncate-max": {"exit_code": 0, "file_count": 20, "file_tree_bytes": 46744, "file_tree_sha256": "bd4947283abbb0cb2d1a4a02334cc8692e762ea07cffd732b3be70d01c721f9f", "paths": ["compact-summary-tables.lcovrc", "control.lcovrc", "fail-under-branches.lcovrc", "fail-under-lines.lcovrc", "input.info", "list-truncate-max.lcovrc", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "source.c"], "reverse_exit": 23}}
FIXTURE_PINS={"compact-summary-tables.lcovrc": "76efb2bc95da85730bb78db58ff031591090c4b597c3b23a8048a5d81389a7b1", "control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15", "fail-under-branches.lcovrc": "5aa48a15f0585e45adaebb40cee706795d5159a7d7fd2be57dd8c7e3ed164660", "fail-under-lines.lcovrc": "160e8c01c71ce44dfbbada7fa6e8327572c3878a51fa51e63e8e311386c7c833", "input.info": "a854b67fff921b6bfb53a8a2a8349b90f93a676de555682ab235d50b1fa6e45d", "list-truncate-max.lcovrc": "ff57afb8b1c2505f34075999b9f107c2931b406db1ece198515ae9d82cd7cfb1", "oracle-observations.json": "9a6173d7f88e23ac9d792dfda816d5e1e0396b8ed223326cac3cce2204e8f088", "source.c": "dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f"}
PLAN_IDS=["case.acceptance.lcovrc.compact-summary-tables", "case.acceptance.lcovrc.fail-under-lines", "case.acceptance.lcovrc.fail-under-branches", "case.acceptance.lcovrc.lcov-list-truncate-max"]
class T(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.suite=json.loads(residual.SUITE_PATH.read_text())
    cls.obs=json.loads((ROOT/residual.FIXTURE/"oracle-observations.json").read_text())
    cls.obs_by={c["case_id"]:c for c in cls.obs["cases"]}
    cls.plans={c["id"]:c for c in json.loads((ROOT/"compat/behavior/fragments/authored/m0-lcovrc-genhtml-residual3-wave.json").read_text())["case_groups"]}
  def test_suite(self):
    residual.validate_suite_document(self.suite); residual.validate_committed_suite()
  def test_mutations(self):
    m=copy.deepcopy(self.suite); m["cases"][1]["arguments"][1]="control.lcovrc"
    with self.assertRaises(residual.Err): residual.validate_suite_document(m)
  def test_oracle(self):
    self.assertFalse(self.obs["product_compatibility_evidence"])
    ctrl=self.obs_by[f"{residual.SUITE_ID}-control"]["reference_run"]
    for cid,pin in PINNED.items():
      run=self.obs_by[cid]["reference_run"]
      self.assertEqual(run["exit_code"],pin["exit_code"],cid)
      self.assertEqual(run["file_tree_sha256"],pin["file_tree_sha256"],cid)
      if cid!=f"{residual.SUITE_ID}-control":
        self.assertTrue(run["file_tree_sha256"]!=ctrl["file_tree_sha256"] or run["exit_code"]!=ctrl["exit_code"], cid)
    self.assertEqual(self.obs_by[f"{residual.SUITE_ID}-fail-under-lines"]["reference_run"]["exit_code"],1)
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
