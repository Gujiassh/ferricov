#!/usr/bin/env python3
"""Validate the pinned Oracle planning suite for three genhtml CLI summary options."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "behavior"))
from validate import ValidationError, validate_plan_bindings  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = Path(os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference"))
SUITE = ROOT / "compat/cases/m0-genhtml-cli-summary-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcovrc-genhtml-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-genhtml-cli-summary-wave.json"
REVIEW = ROOT / "specs/001-full-lcov-compatibility/reviews/m0-genhtml-cli-summary-planning-wave-review.md"
PLAN_BINDINGS = ROOT / "compat/behavior/plan-bindings.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-oracle.json"
SUITE_ID = "m0-genhtml-cli-summary-contract"
CONTROL = f"{SUITE_ID}-control"
IMAGE = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
ENVIRONMENT = {"HOME":"/work","LANG":"C","LC_ALL":"C","PATH":"/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","SOURCE_DATE_EPOCH":"946684800","TMPDIR":"/work","TZ":"UTC"}
REVERSE_COMMAND = "printf 'intentionally different output for harness reverse test: %s\\n' \"$1\"; exit 23"
TARGETS = {
    "fail-under-branches": {"option":["--fail-under-branches","50"],"boundary":"--fail-under-branches 50","tree":"d22d7a069757268655feb255ba3175217037acc3df9cc80918f12514b8214737","references":[("parser_definition","lib/lcovutil.pm",1259),("command_implementation","lib/lcovutil.pm",3167),("command_implementation","lib/lcovutil.pm",7173)]},
    "show-zero-columns": {"option":["--show-zero-columns"],"boundary":"--show-zero-columns","tree":"f4d6a1edcb7c762f50c07f754de5a8bcd93b5e9e092e109260d7eabf12911566","references":[("command_implementation","bin/genhtml",7087),("parser_definition","bin/genhtml",7243),("command_implementation","bin/genhtml",12480)]},
    "sort-tables": {"option":["--sort-tables"],"boundary":"--sort-tables","tree":"2e9ca37edf3b5f7fa6c31d15efc0ffa5ba535ee551787fdcba3c42b7843ba6c6","references":[("parser_definition","bin/genhtml",7264),("command_implementation","bin/genhtml",7336),("command_implementation","bin/genhtml",7537)]},
}
FIXTURE_HASHES = {
    "control.lcovrc":"52ae4f1a03b9eeb76181421e2fdd07df004ba23bccafad30cf8d8f12cfb7671c","epilog.html":"aa1cf6a0ce83031a10af23b9b29cbbcb40eb42729627e39364d10b5ff488bfe6","epilog.lcovrc":"962e9c075e720874b17911aea51deedd58f263a52b78b4f3589c33546ee2c059","extension.lcovrc":"ee9f52363f6320d55c87c6166631cb0d2783ffdf197c557bd9d3a573eb976e51","gzip.lcovrc":"65f02549875547c0e11ca8a91ae0cf7329c231d3d1dcebea9d529052730e48d4","header.lcovrc":"a8cc4dd24ee0c328dbb808da64971da07487b66baf0c58edb1d60a369b453211","input.info":"62f85d64dd938086dc7ebe885efbd0cadf3b9381549d7edd1ea444adee0428a7","legend.lcovrc":"66881fea856c320bdc22d55b2f751f7f7a20de682b34157ab9b346c91aa8f0e9","no-source.lcovrc":"b274ffc1de6481cf01d49505127a521324e6c3fa2c14e66c92a31b6625b3c6ce","num-spaces.lcovrc":"afaa5d8a4a7f99665b1070574d3659fb37b3afae60712722ecbd6ed26b2544af","prolog.html":"26aa57468b95ba84596510d9c2dff0a9b530d5f256e236ddc4d4cb5fbf9161e7","prolog.lcovrc":"8cc317511b8dc61fb4d904077d70ff5b88a6b1c7dcbe4449f283c7f08b8b4928","source.c":"dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f"}
OBS = {CONTROL:{"stdout_sha256":"52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137","stdout_bytes":337,"stderr_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","stderr_bytes":0,"file_tree_sha256":"b3148b0869ea307e9ea36fd8494cee1fd12268377b90c1d6a87c073ddeb88329","file_tree_bytes":8882,"file_count":28}}
for name,t in TARGETS.items(): OBS[f"{SUITE_ID}-{name}"]={"stdout_sha256":OBS[CONTROL]["stdout_sha256"],"stdout_bytes":337,"stderr_sha256":OBS[CONTROL]["stderr_sha256"],"stderr_bytes":0,"file_tree_sha256":t["tree"],"file_tree_bytes":8882,"file_count":28}

class GenhtmlCliSummaryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite=json.loads(SUITE.read_text()); cls.cases={c["id"]:c for c in cls.suite["cases"]}; cls.plans={c["id"]:c for c in json.loads(FRAGMENT.read_text())["case_groups"]}
    def assert_argv(self,cases):
        self.assertEqual(cases[CONTROL]["arguments"],["--config-file","control.lcovrc","--output-directory","report","input.info"])
        for name,t in TARGETS.items(): self.assertEqual(cases[f"{SUITE_ID}-{name}"]["arguments"],["--config-file","control.lcovrc",*t["option"],"--output-directory","report","input.info"])
    def test_exact_case_set_and_argv(self):
        self.assertEqual(list(self.cases),[CONTROL,*[f"{SUITE_ID}-{n}" for n in TARGETS]]); self.assertEqual(self.suite["suite_id"],SUITE_ID); self.assertEqual(self.suite["evidence_scope"],"compatibility"); self.assert_argv(self.cases)
        for c in self.cases.values(): self.assertEqual(c["surface"],"cli"); self.assertEqual(c["command"],"genhtml"); self.assertEqual(c["fixture"],"compat/fixtures/m0-lcovrc-genhtml-contract"); self.assertEqual({x["dimension"] for x in c["comparisons"]},{"exit","stdout","stderr","filesystem"})
    def test_argv_mutations_are_rejected(self):
        for label,name,old,new in [("threshold","fail-under-branches","50","51"),("show-zero","show-zero-columns","--show-zero-columns",None),("sort","sort-tables","--sort-tables",None)]:
            cases=copy.deepcopy(self.cases); args=cases[f"{SUITE_ID}-{name}"]["arguments"]
            if new is None: args.remove(old)
            else: args[args.index(old)]=new
            with self.subTest(label=label),self.assertRaises(AssertionError): self.assert_argv(cases)
    def test_fixture_and_source_references_are_locked(self):
        actual={p.relative_to(FIXTURE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FIXTURE.rglob("*") if p.is_file()}; self.assertEqual(actual,FIXTURE_HASHES); self.assertIn("SF:/work/source.c",(FIXTURE/"input.info").read_text()); self.assertIn("LF:5\nLH:3",(FIXTURE/"input.info").read_text())
        self.assertTrue(UPSTREAM.is_dir())
        for name,t in TARGETS.items():
            refs={(x["kind"],x["path"],x["line"]):x for x in self.plans[f"case.acceptance.command.genhtml.option.{name}"]["source_references"]}; self.assertEqual(set(refs),set(t["references"])); self.assertEqual(list(refs),sorted(refs,key=lambda x:(x[1],x[2],x[0])))
            for (_k,path,line),ref in refs.items(): self.assertEqual(ref["text"],(UPSTREAM/path).read_text().splitlines()[line-1],f"{name}:{path}:{line}")
    def test_plans_and_bindings_are_target_bound(self):
        bindings={x["id"]:x for x in json.loads(PLAN_BINDINGS.read_text())["primary_plans"]}
        for name,t in TARGETS.items():
            pid=f"case.acceptance.command.genhtml.option.{name}"; plan=self.plans[pid]; self.assertEqual(plan["review_status"],"reviewed"); self.assertEqual(plan["evidence_status"],"planned"); self.assertEqual(plan["evidence"],[]); self.assertEqual(plan["suite_cases"],[{"suite_id":SUITE_ID,"case_id":CONTROL},{"suite_id":SUITE_ID,"case_id":f"{SUITE_ID}-{name}"}]); self.assertEqual(bindings[pid]["boundary_form"],t["boundary"]); self.assertIn(t["tree"],plan["description"])
    def test_oracle_facts_are_distinct_and_stable(self):
        self.assertEqual(set(OBS),set(self.cases)); self.assertEqual(len({x["file_tree_sha256"] for x in OBS.values()}),4)
        for c in OBS.values(): self.assertEqual(c["stdout_bytes"],337); self.assertEqual(c["stderr_bytes"],0); self.assertEqual(c["stderr_sha256"],"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    def test_launchers_and_review_rows_are_locked(self):
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),"3d47df2d0ee4bf1df443687f36799d9d5ecb73a424a836a1a469b9390f97f8c3"); self.assertEqual(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),"dbf332683768c480e68b51ea6c7b25bc5b4e9d30af2b7753a0dc8550b6e08593")
        ref=json.loads(REFERENCE.read_text()); cand=json.loads(CANDIDATE.read_text())
        for l in (ref,cand): self.assertEqual(l["runtime"],{"kind":"docker_image","image":IMAGE}); self.assertEqual(l["environment_variables"],ENVIRONMENT); self.assertEqual(l["environment"]["image"],IMAGE)
        self.assertEqual(ref["program"],"{command}"); self.assertEqual(cand["program"],"sh"); self.assertEqual(cand["arguments"],["-c",REVERSE_COMMAND,"sh","{command}"])
        raw=REVIEW.read_text(); self.assertIn("reference/output characterization", " ".join(raw.split())); self.assertIn("no Ferricov candidate was run",raw)
        labels={CONTROL:"control",**{f"{SUITE_ID}-{n}":n for n in TARGETS}}
        for cid,o in OBS.items():
            pre=f"| `{labels[cid]}` |" if cid!=CONTROL else "| control |"; rows=[line for line in raw.splitlines() if line.startswith(pre) and o["file_tree_sha256"] in line]; self.assertEqual(len(rows),1,cid); self.assertTrue(all(str(o[k]) in rows[0] for k in ("stdout_sha256","stdout_bytes","stderr_sha256","stderr_bytes","file_tree_sha256","file_tree_bytes","file_count"))); self.assertIn("| 0 | 23 |",rows[0])
    def test_binding_mutation_is_rejected(self):
        contract=json.loads((ROOT/"compat/behavior/contract.json").read_text()); mutated=copy.deepcopy(contract); plan=next(x for x in mutated["case_groups"] if x["id"]=="case.acceptance.command.genhtml.option.sort-tables"); plan["description"]=plan["description"].replace("--sort-tables","--wrong-sort",1)
        with self.assertRaises(ValidationError): validate_plan_bindings(ROOT,mutated)
if __name__ == "__main__": unittest.main()
