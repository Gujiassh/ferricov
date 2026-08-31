#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m0_residual_b_lang_ext_contract as residual
ROOT=Path(__file__).resolve().parents[2]
PINNED={"m0-residual-b-lang-ext-contract-c-file-extensions": {"exit_code": 0, "file_count": 13, "file_tree_bytes": 1724, "file_tree_sha256": "891e2b974c985d4ea2cd493a2995566f3cb868177707ad1e0a5155475162c204", "paths": ["c-file-extensions.lcovrc", "control.lcovrc", "input.info", "java-file-extensions.lcovrc", "out.info", "perl-file-extensions.lcovrc", "python-file-extensions.lcovrc", "rtl-file-extensions.lcovrc", "src/Sample.java", "src/sample.c", "src/sample.pl", "src/sample.py", "src/sample.v"], "reverse_exit": 23}, "m0-residual-b-lang-ext-contract-control": {"exit_code": 0, "file_count": 13, "file_tree_bytes": 1719, "file_tree_sha256": "8acb76b55c6fe7b4449461c6810f1d59a33737ac8610762923a95e48aad9cd85", "paths": ["c-file-extensions.lcovrc", "control.lcovrc", "input.info", "java-file-extensions.lcovrc", "out.info", "perl-file-extensions.lcovrc", "python-file-extensions.lcovrc", "rtl-file-extensions.lcovrc", "src/Sample.java", "src/sample.c", "src/sample.pl", "src/sample.py", "src/sample.v"], "reverse_exit": 23}, "m0-residual-b-lang-ext-contract-java-file-extensions": {"exit_code": 0, "file_count": 13, "file_tree_bytes": 1731, "file_tree_sha256": "a62539bf8247070aca4a5b46ec6748c1cd782590660d817cfea04d4568599d49", "paths": ["c-file-extensions.lcovrc", "control.lcovrc", "input.info", "java-file-extensions.lcovrc", "out.info", "perl-file-extensions.lcovrc", "python-file-extensions.lcovrc", "rtl-file-extensions.lcovrc", "src/Sample.java", "src/sample.c", "src/sample.pl", "src/sample.py", "src/sample.v"], "reverse_exit": 23}, "m0-residual-b-lang-ext-contract-perl-file-extensions": {"exit_code": 0, "file_count": 13, "file_tree_bytes": 1731, "file_tree_sha256": "b881b7172a52d08b6f07e70a03a9a2721a323a2ee193f35cced7146f9b5ef0ec", "paths": ["c-file-extensions.lcovrc", "control.lcovrc", "input.info", "java-file-extensions.lcovrc", "out.info", "perl-file-extensions.lcovrc", "python-file-extensions.lcovrc", "rtl-file-extensions.lcovrc", "src/Sample.java", "src/sample.c", "src/sample.pl", "src/sample.py", "src/sample.v"], "reverse_exit": 23}, "m0-residual-b-lang-ext-contract-python-file-extensions": {"exit_code": 0, "file_count": 13, "file_tree_bytes": 1733, "file_tree_sha256": "8c44f9e92e72b1601fdb0873d0be03aa32ced68f37a9e7acf72cd08a75a273d5", "paths": ["c-file-extensions.lcovrc", "control.lcovrc", "input.info", "java-file-extensions.lcovrc", "out.info", "perl-file-extensions.lcovrc", "python-file-extensions.lcovrc", "rtl-file-extensions.lcovrc", "src/Sample.java", "src/sample.c", "src/sample.pl", "src/sample.py", "src/sample.v"], "reverse_exit": 23}}
FIXTURE_PINS={"c-file-extensions.lcovrc": "68e2c52f2632bf000707b249d8163c238f84f9411fcf11370c64999a41fc2769", "control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15", "input.info": "83b29abe9d877c17cc568643a83a886d6e3bfc92e6b9e1475779b96d9818aca3", "java-file-extensions.lcovrc": "8541a2c6e084a5cac6351f90b7413f80a611642052b0cf3b60fe22bd7e87b8cf", "oracle-observations.json": "d189fd01454a3a4edd7c634b8d84176cafe134d41ae27272a8c6ad84e7dfd377", "perl-file-extensions.lcovrc": "8fd8896479ad0409a5c915c9cc5ab0dfe47c07feff139aa1f1bca7c3b43d8223", "probe-evidence-rtl-blocked.json": "2ac5183899e67c3f1a7ea3a3382feca635fe2d6ef79406384bf4c046ef510091", "python-file-extensions.lcovrc": "ef36d805523d8e89d380e46b8e3d03756ca4a14aa1ca735c3764b8b1f803d05e", "rtl-file-extensions.lcovrc": "5628bb4228b9033ac0bcd71c7d77f0704b7b67c3d5269395ccc05e80022190eb", "src/Sample.java": "5ae1c35f3546c55a433fd1a419445ea38d459a55d3c51baac983732e0f0a76e6", "src/sample.c": "57b9a643ad8840d8b26e9deccd86faba017ebd91037aa4e4124d6005e2e90cf8", "src/sample.pl": "c108222a89d50a04af0198db00bf1e165cca64a2f1bbc12e84b834e29d5928db", "src/sample.py": "bc77ac8b12ab2fadf4dd7994036de03ecb7a01089a85f6b75faa65fbe945c9e2", "src/sample.v": "4945a389f64c373598d6fc102e4f7503934a83696684936aa1219df2aac3c930"}
PLAN_IDS=["case.acceptance.lcovrc.c-file-extensions", "case.acceptance.lcovrc.java-file-extensions", "case.acceptance.lcovrc.python-file-extensions", "case.acceptance.lcovrc.perl-file-extensions"]
class T(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.suite=json.loads(residual.SUITE_PATH.read_text())
    cls.obs=json.loads((ROOT/residual.FIXTURE/"oracle-observations.json").read_text())
    cls.obs_by={c["case_id"]:c for c in cls.obs["cases"]}
    cls.plans={c["id"]:c for c in json.loads((ROOT/"compat/behavior/fragments/authored/m0-residual-b-lang-ext-wave.json").read_text())["case_groups"]}
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
      self.assertEqual(run["file_count"],pin["file_count"],cid)
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
      self.assertFalse(p.get("evidence"))
if __name__=="__main__": unittest.main()
