#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m0_lcovrc_script_residual_contract as residual
ROOT=Path(__file__).resolve().parents[2]
PINNED={"m0-lcovrc-script-residual-contract-control": {"exit_code": 0, "file_count": 22, "file_tree_bytes": 46990, "file_tree_sha256": "2bf829bb240cad3ba401aca9a35b1aac6a19e3c130ef4a625e789280dcaf50f2", "paths": ["ann.sh", "annotate-script.lcovrc", "context-script.lcovrc", "control.lcovrc", "criteria-script.lcovrc", "input.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "simplify-function.lcovrc", "source.c", "unreachable-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-script-residual-contract-annotate-script": {"exit_code": 0, "file_count": 26, "file_tree_bytes": 80201, "file_tree_sha256": "1a9b4030be0d0454a2a5d0d5f9d6ca1c09966002aced690338df68c4475963bd", "paths": ["ann.sh", "annotate-script.lcovrc", "context-script.lcovrc", "control.lcovrc", "criteria-script.lcovrc", "input.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index-bin_date.html", "report/index-date.html", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index-bin_date.html", "report/work/index-date.html", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "simplify-function.lcovrc", "source.c", "unreachable-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-script-residual-contract-context-script": {"exit_code": 2, "file_count": 22, "file_tree_bytes": 47389, "file_tree_sha256": "240f89eee05e3148dafb73c61d5116e0a48c41451fe157acce1399d85686fb11", "paths": ["ann.sh", "annotate-script.lcovrc", "context-script.lcovrc", "control.lcovrc", "criteria-script.lcovrc", "input.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "simplify-function.lcovrc", "source.c", "unreachable-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-script-residual-contract-criteria-script": {"exit_code": 1, "file_count": 20, "file_tree_bytes": 37217, "file_tree_sha256": "a3808e4ae827e873de0262f32953b529f8c78b2f6c5f94a7f5e892effda57679", "paths": ["ann.sh", "annotate-script.lcovrc", "context-script.lcovrc", "control.lcovrc", "criteria-script.lcovrc", "input.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "simplify-function.lcovrc", "source.c", "unreachable-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-script-residual-contract-simplify-function": {"exit_code": 1, "file_count": 19, "file_tree_bytes": 32752, "file_tree_sha256": "d78cbc4b63b4b2cd983ae6aa6b0d5eaf3b181f15430ccb72ac990addab81e771", "paths": ["ann.sh", "annotate-script.lcovrc", "context-script.lcovrc", "control.lcovrc", "criteria-script.lcovrc", "input.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "simplify-function.lcovrc", "source.c", "unreachable-script.lcovrc"], "reverse_exit": 23}, "m0-lcovrc-script-residual-contract-unreachable-script": {"exit_code": 0, "file_count": 22, "file_tree_bytes": 47001, "file_tree_sha256": "1686393a7f6462c218a3f1a37fc2c31352f51c9c40463286636eaf168d6625e7", "paths": ["ann.sh", "annotate-script.lcovrc", "context-script.lcovrc", "control.lcovrc", "criteria-script.lcovrc", "input.info", "report/amber.png", "report/cmd_line", "report/emerald.png", "report/gcov.css", "report/glass.png", "report/index.html", "report/ruby.png", "report/snow.png", "report/updown.png", "report/work/index.html", "report/work/source.c.func-c.html", "report/work/source.c.func.html", "report/work/source.c.gcov.html", "simplify-function.lcovrc", "source.c", "unreachable-script.lcovrc"], "reverse_exit": 23}}
FIXTURE_PINS={"ann.sh": "cdc6b5876d8cf113ae737ffa85849de8210838759505ad498d21218c40dd9ed3", "annotate-script.lcovrc": "657c7ddd3c188298effeea5a7123f03e1b3a8450d85080addc0e936b835acd22", "context-script.lcovrc": "ec026158b87cc30c5426b6c9161f0e874d1159d2ccff432c6c2bec1fa770cf46", "control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15", "criteria-script.lcovrc": "e811c82a1c87baeeb842d7f7fbdc4285dea5ff61d94a0e87c5b285b6faa9a24b", "input.info": "a854b67fff921b6bfb53a8a2a8349b90f93a676de555682ab235d50b1fa6e45d", "oracle-observations.json": "469729875108bd1531e0d238c515edf50838c161973c4ca03d4ed68a077024ee", "simplify-function.lcovrc": "1057beef8b033627072eb00d6d4934b42d73d53579ff106ab00facd5d863bf63", "source.c": "dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f", "unreachable-script.lcovrc": "b858d2893794aaa9872943c46cdd86d8e2f2b02c8474f630e280c2e1aa46bc65"}
PLAN_IDS=["case.acceptance.lcovrc.genhtml-annotate-script", "case.acceptance.lcovrc.context-script", "case.acceptance.lcovrc.criteria-script", "case.acceptance.lcovrc.simplify-function", "case.acceptance.lcovrc.unreachable-script"]
class T(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.suite=json.loads(residual.SUITE_PATH.read_text())
    cls.obs=json.loads((ROOT/residual.FIXTURE/"oracle-observations.json").read_text())
    cls.obs_by={c["case_id"]:c for c in cls.obs["cases"]}
    cls.plans={c["id"]:c for c in json.loads((ROOT/"compat/behavior/fragments/authored/m0-lcovrc-script-residual-wave.json").read_text())["case_groups"]}
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
      self.assertEqual(p["review_status"],"reviewed"); self.assertEqual(p["evidence_status"],"planned"); self.assertTrue(p["suite_cases"])
if __name__=="__main__": unittest.main()
