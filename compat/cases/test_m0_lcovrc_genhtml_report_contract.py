#!/usr/bin/env python3
"""Validate the pinned Oracle planning suites for two report lcovrc consumers."""

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
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-lcovrc-report-wave.json"
REVIEW = ROOT / "specs/001-full-lcov-compatibility/reviews/m0-lcovrc-genhtml-report-planning-wave-review.md"
PLAN_BINDINGS = ROOT / "compat/behavior/plan-bindings.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-report-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-report-oracle.json"
IMAGE = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
ENVIRONMENT = {
    "HOME": "/work",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "PERL_HASH_SEED": "0",
    "PERL_PERTURB_KEYS": "0",
    "SOURCE_DATE_EPOCH": "946684800",
    "TMPDIR": "/work",
    "TZ": "UTC",
}

SUITES = {
    "alias": ROOT / "compat/cases/m0-lcovrc-genhtml-report-alias-contract.json",
    "context": ROOT / "compat/cases/m0-lcovrc-genhtml-report-context-contract.json",
}
FIXTURES = {
    "alias": ROOT / "compat/fixtures/m0-lcovrc-genhtml-report-alias-contract",
    "context": ROOT / "compat/fixtures/m0-lcovrc-genhtml-report-context-contract",
}
FIXTURE_HASHES = {
    "alias": {
        "baseline.info": "832f6f5d817316cfffdb4452395d4af60ae7540858e215cb12f3e3a2f525eab5",
        "control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15",
        "current.info": "832f6f5d817316cfffdb4452395d4af60ae7540858e215cb12f3e3a2f525eab5",
        "diff.txt": "2ef140ea1f8781a74105396795f045d203a4eb23cf0106635706fb0467c12b67",
        "merge-function-aliases.lcovrc": "b3151c80d6ed70800876ec701b7a6349d7868fd651ca838c2c758777a5027975",
        "src/alias.c": "2cf9ae6f1a751d6dbb12cb3889fb0a886c3f5ba654a84769acfd55f68ec769a2",
    },
    "context": {
        "baseline.info": "3f9149320849c3cafa62d54742d85742f86b82da4ef6492feb8b724b62c97445",
        "context-0.lcovrc": "808fb78dd40e6ea156de8a8899c61b47102163a1ef8f19d5cacdefe7bc06e73f",
        "context-5.lcovrc": "3a05362c8669c361569a21e1525ad9798c0b588df7dccc731d0b75e131071ee4",
        "current.info": "3f9149320849c3cafa62d54742d85742f86b82da4ef6492feb8b724b62c97445",
        "diff.txt": "fc7d1dcbc8047354218f2f499a528c027294e6ad76d628a986547a90611aeb0e",
        "select.pm": "b37ed20f84964868c723af1a56f9b069944e2bd03fdd871877f57a960eb9ca0f",
        "src/context.c": "314af984bdbe49dfc665a93c646f413fdcc6797fb8ee95414072e05fa9b601cc",
    },
}

SOURCE_FACTS = {
    "case.acceptance.lcovrc.merge-function-aliases": [
        ("bin/genhtml", 7192), ("bin/genhtml", 5243), ("bin/genhtml", 5262),
        ("bin/genhtml", 5989), ("bin/genhtml", 13912), ("bin/genhtml", 13998),
    ],
    "case.acceptance.lcovrc.num-context-lines": [
        ("bin/genhtml", 7206), ("lcovrc", 365), ("bin/genhtml", 4453),
        ("bin/genhtml", 4479),
    ],
}

ORACLE_OBSERVATIONS = {
    "m0-lcovrc-genhtml-report-alias-control": {
        "exit": 0,
        "stdout": ("function: UBC:1 CBC:1", "functions...: 50.0% (1 of 2 functions)"),
        "stderr": "",
        "stdout_sha256": "575b236ae4b4bd9f76d7fed8c1ec6987e5009a6452aea0107618ae5fee8c7a31",
        "stdout_bytes": 669,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "01fa263783ea756d157a8abddd29eb8ff82931c594a127dd26f3cfb2579f2e47",
        "file_tree_bytes": 6927,
        "file_count": 19,
        "html": ("headerCovTableHeadUBC", "tlaUBC"),
    },
    "m0-lcovrc-genhtml-report-alias-merge-function-aliases": {
        "exit": 0,
        "stdout": ("function: CBC:1", "functions...: 50.0% (1 of 2 functions)"),
        "stderr": "",
        "stdout_sha256": "614c16b0e288d4ceaec67c585696c98c2163b54e4b78ee18b4457a1ce0869bf6",
        "stdout_bytes": 633,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "020862f9e2548f84c6002d13517174948834e2a9c2bf5cb04e16f2d1082970a3",
        "file_tree_bytes": 6927,
        "file_count": 19,
        "html": ("headerCovTableHeadCBC",),
    },
    "m0-lcovrc-genhtml-report-context-control": {
        "exit": 0,
        "stdout": ("lines.......: 100.0% (1 of 1 line)",),
        "stderr": "",
        "stdout_sha256": "e9d622bec746f21e7e54cd92c267240e0cb1bf2d54eb14125fb2adae8c4109ff",
        "stdout_bytes": 532,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "1b8b6dacdda6071e13d6653088ade88858bdf56c357cbe4d05d280a3eaaf9edc",
        "file_tree_bytes": 6485,
        "file_count": 18,
        "html": ('lineNum">       5', 'elidedSource">     (elided 4 ignored lines)'),
    },
    "m0-lcovrc-genhtml-report-context-num-context-lines": {
        "exit": 0,
        "stdout": ("lines.......: 70.0% (7 of 10 lines)",),
        "stderr": "",
        "stdout_sha256": "011bef1851f2d8c6fc30cfb6c064baa055b1eadada1b27ee716d8b38c2d3b2a5",
        "stdout_bytes": 569,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "28d69dfa47141569947aae9a49c6385ea1c7d7439b9b48369a913e7d33b16fe1",
        "file_tree_bytes": 6485,
        "file_count": 18,
        "html": ('lineNum">       1', 'lineNum">      10', 'elidedSource">     (elided 5 ignored lines)'),
    },
}


class GenhtmlReportLcovrcContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {item["id"]: item for item in cls.fragment["case_groups"]}
        cls.suites = {
            name: json.loads(path.read_text(encoding="utf-8"))
            for name, path in SUITES.items()
        }
        cls.cases = {
            case["id"]: case
            for suite in cls.suites.values()
            for case in suite["cases"]
        }

    def test_exact_case_set_order_and_argv(self) -> None:
        self.assertEqual(
            list(self.cases),
            [
                "m0-lcovrc-genhtml-report-alias-control",
                "m0-lcovrc-genhtml-report-alias-merge-function-aliases",
                "m0-lcovrc-genhtml-report-context-control",
                "m0-lcovrc-genhtml-report-context-num-context-lines",
            ],
        )
        alias_common = [
            "--baseline-file", "baseline.info", "--baseline-date", "2000-01-01",
            "--diff-file", "diff.txt",
            "--ignore-errors", "unsupported", "--output-directory", "report", "current.info",
        ]
        context_common = [
            "--baseline-file", "baseline.info", "--baseline-date", "2000-01-01",
            "--diff-file", "diff.txt",
            "--select-script", "select.pm", "--output-directory", "report", "current.info",
        ]
        self.assertEqual(
            self.cases["m0-lcovrc-genhtml-report-alias-control"]["arguments"],
            ["--config-file", "control.lcovrc", *alias_common],
        )
        self.assertEqual(
            self.cases["m0-lcovrc-genhtml-report-alias-merge-function-aliases"]["arguments"],
            ["--config-file", "merge-function-aliases.lcovrc", *alias_common],
        )
        self.assertEqual(
            self.cases["m0-lcovrc-genhtml-report-context-control"]["arguments"],
            ["--config-file", "context-0.lcovrc", *context_common],
        )
        self.assertEqual(
            self.cases["m0-lcovrc-genhtml-report-context-num-context-lines"]["arguments"],
            ["--config-file", "context-5.lcovrc", *context_common],
        )
        for case in self.cases.values():
            self.assertEqual(case["command"], "genhtml")
            self.assertEqual(case["surface"], "config")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )

    def test_fixture_identity_and_semantics(self) -> None:
        for name, fixture in FIXTURES.items():
            actual = {
                path.relative_to(fixture).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in fixture.rglob("*") if path.is_file()
            }
            self.assertEqual(actual, FIXTURE_HASHES[name], name)
        alias_trace = (FIXTURES["alias"] / "current.info").read_text(encoding="utf-8")
        self.assertIn("FNL:0,1,3\nFNA:0,1,leader", alias_trace)
        self.assertIn("FNL:1,1,3\nFNA:1,0,alias", alias_trace)
        self.assertEqual(alias_trace.count("FNL:"), 2)
        self.assertEqual(alias_trace.count("FNA:"), 2)
        self.assertNotIn("merge_function_aliasess", (FIXTURES["alias"] / "merge-function-aliases.lcovrc").read_text(encoding="utf-8"))
        self.assertIn("--- /work/src/alias.c", (FIXTURES["alias"] / "diff.txt").read_text(encoding="utf-8"))
        context_trace = (FIXTURES["context"] / "current.info").read_text(encoding="utf-8")
        self.assertIn("DA:1,1", context_trace)
        self.assertIn("DA:7,1", context_trace)
        self.assertIn("DA:8,0", context_trace)
        self.assertIn("LF:15\nLH:7", context_trace)
        self.assertEqual(len((FIXTURES["context"] / "src/context.c").read_text(encoding="utf-8").splitlines()), 15)
        self.assertIn("return defined($line_number) && $line_number == 5;", (FIXTURES["context"] / "select.pm").read_text(encoding="utf-8"))

    def test_config_assignment_binding(self) -> None:
        self.assertEqual((FIXTURES["alias"] / "control.lcovrc").read_text(), "lcov_tmp_dir = /work\n")
        self.assertEqual((FIXTURES["alias"] / "merge-function-aliases.lcovrc").read_text(), "lcov_tmp_dir = /work\nmerge_function_aliases = 1\n")
        self.assertEqual((FIXTURES["context"] / "context-0.lcovrc").read_text(), "lcov_tmp_dir = /work\nnum_context_lines = 0\n")
        self.assertEqual((FIXTURES["context"] / "context-5.lcovrc").read_text(), "lcov_tmp_dir = /work\nnum_context_lines = 5\n")

    def test_source_references_match_pinned_lines_and_text(self) -> None:
        self.assertTrue(UPSTREAM.is_dir(), UPSTREAM)
        for plan_id, facts in SOURCE_FACTS.items():
            refs = {(item["path"], item["line"]): item for item in self.plans[plan_id]["source_references"]}
            self.assertEqual(set(refs), set(facts), plan_id)
            for path, line in facts:
                expected = (UPSTREAM / path).read_text(encoding="utf-8").splitlines()[line - 1]
                self.assertEqual(refs[(path, line)]["text"], expected, f"{plan_id}: {path}:{line}")

    def test_plans_bind_shared_control_and_target(self) -> None:
        expected = {
            "case.acceptance.lcovrc.merge-function-aliases": ("m0-lcovrc-genhtml-report-alias-contract", "m0-lcovrc-genhtml-report-alias-control", "m0-lcovrc-genhtml-report-alias-merge-function-aliases", "merge_function_aliases = 1"),
            "case.acceptance.lcovrc.num-context-lines": ("m0-lcovrc-genhtml-report-context-contract", "m0-lcovrc-genhtml-report-context-control", "m0-lcovrc-genhtml-report-context-num-context-lines", "num_context_lines = 5"),
        }
        bindings = {item["id"]: item for item in json.loads(PLAN_BINDINGS.read_text(encoding="utf-8"))["primary_plans"]}
        for plan_id, (suite_id, control, target, boundary) in expected.items():
            plan = self.plans[plan_id]
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual(plan["evidence"], [])
            self.assertEqual([item["suite_id"] for item in plan["suite_cases"]], [suite_id, suite_id])
            self.assertEqual({item["case_id"] for item in plan["suite_cases"]}, {control, target})
            self.assertEqual(bindings[plan_id]["boundary_form"], boundary)
            self.assertIn("no Ferricov product evidence", plan["description"])

    def test_oracle_deltas_are_target_specific_and_planned_only(self) -> None:
        self.assertEqual({item["exit"] for item in ORACLE_OBSERVATIONS.values()}, {0})
        self.assertTrue(all(item["stderr"] == "" for item in ORACLE_OBSERVATIONS.values()))
        self.assertTrue(all(item["stderr_bytes"] == 0 for item in ORACLE_OBSERVATIONS.values()))
        self.assertEqual(
            {item["stderr_sha256"] for item in ORACLE_OBSERVATIONS.values()},
            {"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        )
        alias_control = ORACLE_OBSERVATIONS["m0-lcovrc-genhtml-report-alias-control"]
        alias_target = ORACLE_OBSERVATIONS["m0-lcovrc-genhtml-report-alias-merge-function-aliases"]
        context_control = ORACLE_OBSERVATIONS["m0-lcovrc-genhtml-report-context-control"]
        context_target = ORACLE_OBSERVATIONS["m0-lcovrc-genhtml-report-context-num-context-lines"]
        self.assertIn("function: UBC:1 CBC:1", alias_control["stdout"])
        self.assertIn("function: CBC:1", alias_target["stdout"])
        self.assertNotEqual(alias_control["html"], alias_target["html"])
        self.assertNotEqual(alias_control["stdout_sha256"], alias_target["stdout_sha256"])
        self.assertNotEqual(alias_control["stdout_bytes"], alias_target["stdout_bytes"])
        self.assertNotEqual(alias_control["file_tree_sha256"], alias_target["file_tree_sha256"])
        self.assertEqual({alias_control["file_tree_bytes"], alias_target["file_tree_bytes"]}, {6927})
        self.assertEqual({alias_control["file_count"], alias_target["file_count"]}, {19})
        self.assertIn("lines.......: 100.0% (1 of 1 line)", context_control["stdout"])
        self.assertIn("lines.......: 70.0% (7 of 10 lines)", context_target["stdout"])
        self.assertNotEqual(context_control["html"], context_target["html"])
        self.assertNotEqual(context_control["stdout_sha256"], context_target["stdout_sha256"])
        self.assertNotEqual(context_control["stdout_bytes"], context_target["stdout_bytes"])
        self.assertNotEqual(context_control["file_tree_sha256"], context_target["file_tree_sha256"])
        self.assertEqual({context_control["file_tree_bytes"], context_target["file_tree_bytes"]}, {6485})
        self.assertEqual({context_control["file_count"], context_target["file_count"]}, {18})
        self.assertTrue(all(plan["evidence_status"] == "planned" and plan["evidence"] == [] for plan in self.plans.values()))

    def test_report_launchers_are_pinned_and_distinct(self) -> None:
        reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
        candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), "5dbefc9aca20a447b8231d85a69b726996275a703f49433402d83c6171d84838")
        self.assertEqual(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(), "780cfcf3f1cbaa5e59c37c7e5daf93cfa1d0191dcbb8e62f403df50ec3d8cdf9")
        self.assertEqual(reference["runtime"]["image"], IMAGE)
        self.assertEqual(candidate["runtime"]["image"], IMAGE)
        self.assertEqual(reference["environment_variables"], ENVIRONMENT)
        self.assertEqual(candidate["environment_variables"], ENVIRONMENT)
        self.assertEqual(reference["program"], "{command}")
        self.assertEqual(candidate["program"], "sh")
        self.assertNotEqual(reference["program"], candidate["program"])

    def test_review_records_final_oracle_facts(self) -> None:
        review = " ".join(REVIEW.read_text(encoding="utf-8").split())
        self.assertIn("--baseline-date 2000-01-01", review)
        self.assertIn("PERL_HASH_SEED=0", review)
        self.assertIn("PERL_PERTURB_KEYS=0", review)
        for case_id, observation in ORACLE_OBSERVATIONS.items():
            for key in (
                "stdout_sha256",
                "stdout_bytes",
                "stderr_sha256",
                "stderr_bytes",
                "file_tree_sha256",
                "file_tree_bytes",
                "file_count",
            ):
                self.assertIn(str(observation[key]), review, f"{case_id}:{key}")

    def test_plan_binding_mutation_is_rejected(self) -> None:
        contract = json.loads((ROOT / "compat/behavior/contract.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(contract)
        plan = next(item for item in mutated["case_groups"] if item["id"] == "case.acceptance.lcovrc.merge-function-aliases")
        plan["description"] = plan["description"].replace("merge_function_aliases = 1", "merge_function_aliases = 0", 1)
        with self.assertRaises(ValidationError):
            validate_plan_bindings(ROOT, mutated)


if __name__ == "__main__":
    unittest.main()
