#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m0_residual_c_filters_contract as residual
ROOT=Path(__file__).resolve().parents[2]
PINNED={"m0-residual-c-filters-contract-control": {"exit_code": 0, "file_count": 7, "file_tree_bytes": 1820, "file_tree_sha256": "16c8f1fe5dba5bb1fb5513d2f59acc11bf26b34bab4b99074022180c2e21a178", "paths": ["bitwise-conditional.lcovrc", "blank-aggressive.lcovrc", "control.lcovrc", "lookahead.lcovrc", "out.info", "src/edges.c", "src/edges.info"], "reverse_exit": 23}, "m0-residual-c-filters-contract-bitwise-conditional": {"exit_code": 0, "file_count": 7, "file_tree_bytes": 1860, "file_tree_sha256": "a394c7234bb2a4fd3ff39caa7bc36e8240970e19b3b9e55104b416618a499215", "paths": ["bitwise-conditional.lcovrc", "blank-aggressive.lcovrc", "control.lcovrc", "lookahead.lcovrc", "out.info", "src/edges.c", "src/edges.info"], "reverse_exit": 23}, "m0-residual-c-filters-contract-blank-aggressive": {"exit_code": 0, "file_count": 7, "file_tree_bytes": 1812, "file_tree_sha256": "cd42daeefb50bba776b9d2c31bb56147d76da6f675ffd678497948060400108f", "paths": ["bitwise-conditional.lcovrc", "blank-aggressive.lcovrc", "control.lcovrc", "lookahead.lcovrc", "out.info", "src/edges.c", "src/edges.info"], "reverse_exit": 23}, "m0-residual-c-filters-contract-lookahead": {"exit_code": 0, "file_count": 7, "file_tree_bytes": 1860, "file_tree_sha256": "1668a764b690c496d2d6907393d7219a4beb6862b05edd2ae94145fa378977c1", "paths": ["bitwise-conditional.lcovrc", "blank-aggressive.lcovrc", "control.lcovrc", "lookahead.lcovrc", "out.info", "src/edges.c", "src/edges.info"], "reverse_exit": 23}}
FIXTURE_PINS={"bitwise-conditional.lcovrc": "e38e13f28daf0993f8118eca2d7e31f7828b908042254f87f479d3926971e703", "blank-aggressive.lcovrc": "8ad154f35b2cdadd4f48c06492d53cd58c8e0b4c0e48f039f5b4aa78a895c6c4", "control.lcovrc": "a663b5b37e0f93bf0c45250070cfd7e1c8c4b250d06508e204e33bbffb8248d1", "lookahead.lcovrc": "6bdb25ac6007af9c803956b5645ebd09e02fc6b876a8f4c8be9e9cbac552f63c", "oracle-observations.json": "c62127b9b15bce973f7d5d35c414a6a9deb18e345b8b3ddb5cb176709500619b", "src/edges.c": "3bbd1a87e626c29a2ad2c15d327dfa6a5ffc3c5b93d580a493fc7f6cd4e29765", "src/edges.info": "cf6eb73474b189440be356214b3c6e863e8377eb62326425c53bda24c5c40d25"}
PLAN_IDS=["case.acceptance.lcovrc.filter-bitwise-conditional", "case.acceptance.lcovrc.filter-blank-aggressive", "case.acceptance.lcovrc.filter-lookahead"]
class T(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.suite=json.loads(residual.SUITE_PATH.read_text())
    cls.obs=json.loads((ROOT/residual.FIXTURE/"oracle-observations.json").read_text())
    cls.obs_by={c["case_id"]:c for c in cls.obs["cases"]}
    cls.plans={c["id"]:c for c in json.loads((ROOT/"compat/behavior/fragments/authored/m0-residual-c-filters-wave.json").read_text())["case_groups"]}
  def test_suite(self):
    residual.validate_suite_document(self.suite); residual.validate_committed_suite()
  def test_mutations(self):
    m=copy.deepcopy(self.suite); m["cases"][1]["arguments"]=list(m["cases"][0]["arguments"])
    with self.assertRaises(residual.Err): residual.validate_suite_document(m)
  def test_oracle(self):
    self.assertFalse(self.obs["product_compatibility_evidence"])
    self.assertEqual(self.obs["oracle_identity"]["container_image_sha256"], "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7")
    ctrl=self.obs_by[f"{residual.SUITE_ID}-control"]["reference_run"]
    for cid,pin in PINNED.items():
      run=self.obs_by[cid]["reference_run"]
      self.assertEqual(run["exit_code"],pin["exit_code"],cid)
      self.assertEqual(run["file_count"],pin["file_count"],cid)
      self.assertEqual(run["file_tree_bytes"],pin["file_tree_bytes"],cid)
      self.assertEqual(run["file_tree_sha256"],pin["file_tree_sha256"],cid)
      self.assertEqual(run["paths"],pin["paths"],cid)
      self.assertEqual(self.obs_by[cid]["reverse_run"]["exit_code"],pin["reverse_exit"],cid)
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
      self.assertFalse(p.get("product_compatibility_evidence", False))
if __name__=="__main__": unittest.main()
