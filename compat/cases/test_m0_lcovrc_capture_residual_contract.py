#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m0_lcovrc_capture_residual_contract as residual
ROOT=Path(__file__).resolve().parents[2]
PINNED={"m0-lcovrc-capture-residual-contract-control": {"exit_code": 0, "file_count": 13, "file_tree_bytes": 893, "file_tree_sha256": "a2c0c6c467d9972fe6c9aeda9152a532de4b00c9610e475573fed6e3ad73a840", "paths": ["build-directory.lcovrc", "control.lcovrc", "erase-functions.lcovrc", "gcov-tool.lcovrc", "mcdc-coverage.lcovrc", "out.info", "source-directory.lcovrc", "src/hello.c", "src/hello.gcda", "src/hello.gcno", "tmp-dir.lcovrc", "ver.sh", "version-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-capture-residual-contract-source-directory": {"exit_code": 1, "file_count": 13, "file_tree_bytes": 893, "file_tree_sha256": "a2c0c6c467d9972fe6c9aeda9152a532de4b00c9610e475573fed6e3ad73a840", "paths": ["build-directory.lcovrc", "control.lcovrc", "erase-functions.lcovrc", "gcov-tool.lcovrc", "mcdc-coverage.lcovrc", "out.info", "source-directory.lcovrc", "src/hello.c", "src/hello.gcda", "src/hello.gcno", "tmp-dir.lcovrc", "ver.sh", "version-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-capture-residual-contract-build-directory": {"exit_code": 1, "file_count": 13, "file_tree_bytes": 893, "file_tree_sha256": "a2c0c6c467d9972fe6c9aeda9152a532de4b00c9610e475573fed6e3ad73a840", "paths": ["build-directory.lcovrc", "control.lcovrc", "erase-functions.lcovrc", "gcov-tool.lcovrc", "mcdc-coverage.lcovrc", "out.info", "source-directory.lcovrc", "src/hello.c", "src/hello.gcda", "src/hello.gcno", "tmp-dir.lcovrc", "ver.sh", "version-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-capture-residual-contract-tmp-dir": {"exit_code": 2, "file_count": 12, "file_tree_bytes": 788, "file_tree_sha256": "0c8929044489b5b0badb8e09daeb9ff5d1f6500aa8f4a07706c2d5604cceb312", "paths": ["build-directory.lcovrc", "control.lcovrc", "erase-functions.lcovrc", "gcov-tool.lcovrc", "mcdc-coverage.lcovrc", "source-directory.lcovrc", "src/hello.c", "src/hello.gcda", "src/hello.gcno", "tmp-dir.lcovrc", "ver.sh", "version-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-capture-residual-contract-erase-functions": {"exit_code": 1, "file_count": 12, "file_tree_bytes": 788, "file_tree_sha256": "0c8929044489b5b0badb8e09daeb9ff5d1f6500aa8f4a07706c2d5604cceb312", "paths": ["build-directory.lcovrc", "control.lcovrc", "erase-functions.lcovrc", "gcov-tool.lcovrc", "mcdc-coverage.lcovrc", "source-directory.lcovrc", "src/hello.c", "src/hello.gcda", "src/hello.gcno", "tmp-dir.lcovrc", "ver.sh", "version-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-capture-residual-contract-mcdc-coverage": {"exit_code": 255, "file_count": 12, "file_tree_bytes": 788, "file_tree_sha256": "0c8929044489b5b0badb8e09daeb9ff5d1f6500aa8f4a07706c2d5604cceb312", "paths": ["build-directory.lcovrc", "control.lcovrc", "erase-functions.lcovrc", "gcov-tool.lcovrc", "mcdc-coverage.lcovrc", "source-directory.lcovrc", "src/hello.c", "src/hello.gcda", "src/hello.gcno", "tmp-dir.lcovrc", "ver.sh", "version-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-capture-residual-contract-gcov-tool": {"exit_code": 2, "file_count": 12, "file_tree_bytes": 788, "file_tree_sha256": "0c8929044489b5b0badb8e09daeb9ff5d1f6500aa8f4a07706c2d5604cceb312", "paths": ["build-directory.lcovrc", "control.lcovrc", "erase-functions.lcovrc", "gcov-tool.lcovrc", "mcdc-coverage.lcovrc", "source-directory.lcovrc", "src/hello.c", "src/hello.gcda", "src/hello.gcno", "tmp-dir.lcovrc", "ver.sh", "version-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-capture-residual-contract-version-script": {"exit_code": 0, "file_count": 13, "file_tree_bytes": 906, "file_tree_sha256": "c7d8c3a5aa64c9c674282f9e0667d904613c5129611a251a5d511eb493962b56", "paths": ["build-directory.lcovrc", "control.lcovrc", "erase-functions.lcovrc", "gcov-tool.lcovrc", "mcdc-coverage.lcovrc", "out.info", "source-directory.lcovrc", "src/hello.c", "src/hello.gcda", "src/hello.gcno", "tmp-dir.lcovrc", "ver.sh", "version-script.lcovrc"], "reverse_exit": 23}}
FIXTURE_PINS={"build-directory.lcovrc": "3c98030d842359efe507b03da023d23bc20e58a75cc3819793bb75357ab9b1cd", "control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15", "erase-functions.lcovrc": "90d2096e090da73c8b5ddec0bf47303a75420091355351a225fb3966478da2bb", "gcov-tool.lcovrc": "cfa4dd4dfa90994636129f219d08fedba0de1cc547b497c445d3a78588ff9c27", "mcdc-coverage.lcovrc": "9fbddb8086b3b8ed00768af03b07e4f9972bac311f2d9bc15a0ea7e66049d4af", "oracle-observations.json": "f35a11dc0f460ac92cb1a987dea7287efbeb5241ae7fae7700486c3a42ede1f6", "source-directory.lcovrc": "fa75481c0c1a868a4a2f7c286d257dd85c8df84ae10741a461d19b416d0b246f", "src/hello.c": "078d5e4e637d5d8f25c2d0b7d185a6cd5a97be361a88ef77864339a923f96606", "src/hello.gcda": "bfcc8d193f917fd19d8725d65e22354e0a1acb0cf78c963dd1229b84a86ceb91", "src/hello.gcno": "ab03749993c352bfc18a56dae872cb29062af6ea6a84f03e73e745308b667b05", "tmp-dir.lcovrc": "1dfccc83b99c6359c97cbe3d7bbe4f9e395a3bfe611bf34436b9a989501d9429", "ver.sh": "82d58c9918390112cfabb0bdf2120cad6c4c31d51b6f5230226277e807633711", "version-script.lcovrc": "97cb7887349cb78401297d2564a811b519ec397d8d582dc47f3ed62d211f44c3"}
PLAN_IDS=["case.acceptance.lcovrc.source-directory", "case.acceptance.lcovrc.build-directory", "case.acceptance.lcovrc.lcov-tmp-dir", "case.acceptance.lcovrc.erase-functions", "case.acceptance.lcovrc.mcdc-coverage", "case.acceptance.lcovrc.geninfo-gcov-tool", "case.acceptance.lcovrc.version-script"]
class T(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.suite=json.loads(residual.SUITE_PATH.read_text())
    cls.obs=json.loads((ROOT/residual.FIXTURE/"oracle-observations.json").read_text())
    cls.obs_by={c["case_id"]:c for c in cls.obs["cases"]}
    cls.plans={c["id"]:c for c in json.loads((ROOT/"compat/behavior/fragments/authored/m0-lcovrc-capture-residual-wave.json").read_text())["case_groups"]}
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
