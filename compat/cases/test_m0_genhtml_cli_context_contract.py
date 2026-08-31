#!/usr/bin/env python3
"""Validate the pinned Oracle planning suite for three genhtml CLI context options."""

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
SUITE = ROOT / "compat/cases/m0-genhtml-cli-context-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcovrc-genhtml-report-alias-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-genhtml-cli-context-wave.json"
PLAN_BINDINGS = ROOT / "compat/behavior/plan-bindings.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-oracle.json"
SUITE_ID = "m0-genhtml-cli-context-contract"
CONTROL = f"{SUITE_ID}-control"
IMAGE = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
ENVIRONMENT = {
    "HOME": "/work", "LANG": "C", "LC_ALL": "C",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "SOURCE_DATE_EPOCH": "946684800", "TMPDIR": "/work", "TZ": "UTC",
}
REVERSE_COMMAND = (
    "printf 'intentionally different output for harness reverse test: %s\\n' \"$1\"; exit 23"
)
TARGETS = {
    "baseline-title": {
        "option": [
            "--baseline-title",
            "Baseline CLI"
        ],
        "boundary": "--baseline-title Baseline CLI",
        "tree": "4f14051fc342b9aa796f326e98e06d338508e10923dcdf852378544d54a979a3",
        "references": [
            [
                "command_implementation",
                "bin/genhtml",
                12362
            ],
            [
                "command_implementation",
                "bin/genhtml",
                12365
            ],
            [
                "parser_definition",
                "bin/genhtml",
                7228
            ]
        ]
    },
    "merge-aliases": {
        "option": [
            "--merge-aliases"
        ],
        "boundary": "--merge-aliases",
        "tree": "e25b2f27f72a1e97462f0874a5332e9d78a2fca276b5f1a0496bd3a687ca6d7f",
        "references": [
            [
                "command_implementation",
                "bin/genhtml",
                5243
            ],
            [
                "parser_definition",
                "bin/genhtml",
                7271
            ],
            [
                "command_implementation",
                "bin/genhtml",
                13912
            ]
        ]
    },
    "suppress-aliases": {
        "option": [
            "--suppress-aliases"
        ],
        "boundary": "--suppress-aliases",
        "tree": "703fc37500b88cb830e46933a6b77da70476df2f7e20d210c061dfc291e16f00",
        "references": [
            [
                "parser_definition",
                "bin/genhtml",
                7272
            ],
            [
                "command_implementation",
                "bin/genhtml",
                7286
            ],
            [
                "command_implementation",
                "bin/genhtml",
                13998
            ]
        ]
    }
}
FIXTURE_HASHES = {
    "baseline.info": "832f6f5d817316cfffdb4452395d4af60ae7540858e215cb12f3e3a2f525eab5",
    "control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15",
    "current.info": "832f6f5d817316cfffdb4452395d4af60ae7540858e215cb12f3e3a2f525eab5",
    "diff.txt": "2ef140ea1f8781a74105396795f045d203a4eb23cf0106635706fb0467c12b67",
    "merge-function-aliases.lcovrc": "b3151c80d6ed70800876ec701b7a6349d7868fd651ca838c2c758777a5027975",
    "src/alias.c": "2cf9ae6f1a751d6dbb12cb3889fb0a886c3f5ba654a84769acfd55f68ec769a2"
}
OBSERVATIONS = {
    "m0-genhtml-cli-context-contract-baseline-title": {
        "file_count": 19,
        "file_tree_bytes": 6927,
        "file_tree_sha256": "4f14051fc342b9aa796f326e98e06d338508e10923dcdf852378544d54a979a3",
        "stderr_bytes": 0,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stdout_bytes": 800,
        "stdout_sha256": "98fda1706e87a8784d4c09208c023f5a5f88bc9c479becaac6a7498a02bd09ea"
    },
    "m0-genhtml-cli-context-contract-control": {
        "file_count": 19,
        "file_tree_bytes": 6927,
        "file_tree_sha256": "8332c23c2da180e3656f1f55a63be39e2e99002fe96c082bfff44fc4876a26e5",
        "stderr_bytes": 0,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stdout_bytes": 800,
        "stdout_sha256": "98fda1706e87a8784d4c09208c023f5a5f88bc9c479becaac6a7498a02bd09ea"
    },
    "m0-genhtml-cli-context-contract-merge-aliases": {
        "file_count": 19,
        "file_tree_bytes": 6927,
        "file_tree_sha256": "e25b2f27f72a1e97462f0874a5332e9d78a2fca276b5f1a0496bd3a687ca6d7f",
        "stderr_bytes": 0,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stdout_bytes": 800,
        "stdout_sha256": "98fda1706e87a8784d4c09208c023f5a5f88bc9c479becaac6a7498a02bd09ea"
    },
    "m0-genhtml-cli-context-contract-suppress-aliases": {
        "file_count": 19,
        "file_tree_bytes": 6927,
        "file_tree_sha256": "703fc37500b88cb830e46933a6b77da70476df2f7e20d210c061dfc291e16f00",
        "stderr_bytes": 0,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stdout_bytes": 800,
        "stdout_sha256": "98fda1706e87a8784d4c09208c023f5a5f88bc9c479becaac6a7498a02bd09ea"
    }
}

class GenhtmlCliContextContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def assert_cli_arguments(self, cases: dict[str, dict]) -> None:
        base = [
            "--config-file", "control.lcovrc", "--filter", "function",
            "--baseline-file", "baseline.info", "--baseline-date", "2000-01-01",
            "--diff-file", "diff.txt", "--ignore-errors", "unsupported",
            "--output-directory", "report", "current.info",
        ]
        self.assertEqual(cases[CONTROL]["arguments"], base)
        for name, target in TARGETS.items():
            self.assertEqual(cases[f"{SUITE_ID}-{name}"]["arguments"], base[:2] + target["option"] + base[2:])

    def test_exact_case_set_and_argv(self) -> None:
        self.assertEqual(list(self.cases), [CONTROL, *[f"{SUITE_ID}-{name}" for name in TARGETS]])
        self.assertEqual(self.suite["suite_id"], SUITE_ID)
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assert_cli_arguments(self.cases)
        for case in self.cases.values():
            self.assertEqual(case["surface"], "cli")
            self.assertEqual(case["command"], "genhtml")
            self.assertEqual(case["fixture"], "compat/fixtures/m0-lcovrc-genhtml-report-alias-contract")
            self.assertEqual({item["dimension"] for item in case["comparisons"]}, {"exit", "stdout", "stderr", "filesystem"})

    def test_argv_mutations_are_rejected(self) -> None:
        for label, name, old, new in (("baseline-title", "baseline-title", "Baseline CLI", "Other Baseline"), ("merge-aliases", "merge-aliases", "--merge-aliases", None), ("suppress-aliases", "suppress-aliases", "--suppress-aliases", None)):
            cases = copy.deepcopy(self.cases)
            args = cases[f"{SUITE_ID}-{name}"]["arguments"]
            if new is None:
                args.remove(old)
            else:
                args[args.index(old)] = new
            with self.subTest(label=label), self.assertRaises(AssertionError):
                self.assert_cli_arguments(cases)

    def test_fixture_and_source_references_are_locked(self) -> None:
        actual = {path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in FIXTURE.rglob("*") if path.is_file()}
        self.assertEqual(actual, FIXTURE_HASHES)
        self.assertIn("SF:/work/src/alias.c", (FIXTURE / "current.info").read_text())
        self.assertIn("FNA:0,1,leader", (FIXTURE / "current.info").read_text())
        self.assertIn("FNA:1,0,alias", (FIXTURE / "current.info").read_text())
        self.assertTrue(UPSTREAM.is_dir())
        for name, target in TARGETS.items():
            plan = self.plans[f"case.acceptance.command.genhtml.option.{name}"]
            refs = {(item["kind"], item["path"], item["line"]): item for item in plan["source_references"]}
            expected = {(kind, path, line) for kind, path, line in target["references"]}
            self.assertEqual(set(refs), expected)
            self.assertEqual(list(refs), sorted(refs, key=lambda item: (item[1], item[2], item[0])))
            for (_kind, path, line), reference in refs.items():
                text = (UPSTREAM / path).read_text(encoding="utf-8").splitlines()[line - 1]
                self.assertEqual(reference["text"], text, f"{name}:{path}:{line}")

    def test_plans_and_bindings_are_target_bound(self) -> None:
        bindings = {item["id"]: item for item in json.loads(PLAN_BINDINGS.read_text())["primary_plans"]}
        for name, target in TARGETS.items():
            plan_id = f"case.acceptance.command.genhtml.option.{name}"
            plan = self.plans[plan_id]
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual(plan["evidence"], [])
            self.assertEqual(plan["suite_cases"], sorted([{"suite_id": SUITE_ID, "case_id": CONTROL}, {"suite_id": SUITE_ID, "case_id": f"{SUITE_ID}-{name}"}], key=lambda item: item["case_id"]))
            self.assertEqual(bindings[plan_id]["boundary_form"], target["boundary"])
            self.assertIn(target["tree"], plan["description"])
            self.assertIn("no Ferricov product evidence", plan["description"])

    def test_oracle_facts_are_distinct_and_stable(self) -> None:
        self.assertEqual(set(OBSERVATIONS), set(self.cases))
        self.assertEqual(len({item["file_tree_sha256"] for item in OBSERVATIONS.values()}), 4)
        for observation in OBSERVATIONS.values():
            self.assertEqual(observation["stdout_bytes"], 800)
            self.assertEqual(observation["stderr_bytes"], 0)
            self.assertEqual(observation["stderr_sha256"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_launchers_and_review_rows_are_locked(self) -> None:
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), '3d47df2d0ee4bf1df443687f36799d9d5ecb73a424a836a1a469b9390f97f8c3')
        self.assertEqual(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(), 'dbf332683768c480e68b51ea6c7b25bc5b4e9d30af2b7753a0dc8550b6e08593')
        reference = json.loads(REFERENCE.read_text())
        candidate = json.loads(CANDIDATE.read_text())
        for launcher in (reference, candidate):
            self.assertEqual(launcher["runtime"], {"kind": "docker_image", "image": IMAGE})
            self.assertEqual(launcher["environment_variables"], ENVIRONMENT)
            self.assertEqual(launcher["environment"]["image"], IMAGE)
        self.assertEqual(reference["program"], "{command}")
        self.assertEqual(reference["arguments"], [])
        self.assertEqual(candidate["program"], "sh")
        self.assertEqual(candidate["arguments"], ["-c", REVERSE_COMMAND, "sh", "{command}"])
        review_path = ROOT / "specs/001-full-lcov-compatibility/reviews/m0-genhtml-cli-context-planning-wave-review.md"
        raw_review = review_path.read_text()
        self.assertIn("reference/output characterization", " ".join(raw_review.split()))
        self.assertIn("no Ferricov candidate was run", raw_review)
        labels = {CONTROL: "control", **{f"{SUITE_ID}-{name}": name for name in TARGETS}}
        for case_id, observation in OBSERVATIONS.items():
            prefix = f"| {labels[case_id]} |" if case_id != CONTROL else "| control |"
            rows = [line for line in raw_review.splitlines() if line.startswith(prefix) and observation["file_tree_sha256"] in line]
            self.assertEqual(len(rows), 1, case_id)
            row = rows[0]
            for key in ("stdout_sha256", "stdout_bytes", "stderr_sha256", "stderr_bytes", "file_tree_sha256", "file_tree_bytes", "file_count"):
                self.assertIn(str(observation[key]), row)
            self.assertIn("| 0 | 23 |", row)

    def test_binding_mutation_is_rejected(self) -> None:
        contract = json.loads((ROOT / "compat/behavior/contract.json").read_text())
        mutated = copy.deepcopy(contract)
        plan = next(item for item in mutated["case_groups"] if item["id"] == "case.acceptance.command.genhtml.option.baseline-title")
        plan["description"] = plan["description"].replace("--baseline-title Baseline CLI", "--baseline-title Wrong", 1)
        with self.assertRaises(ValidationError):
            validate_plan_bindings(ROOT, mutated)

if __name__ == "__main__":
    unittest.main()
