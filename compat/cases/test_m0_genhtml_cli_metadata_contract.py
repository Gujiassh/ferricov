#!/usr/bin/env python3
"""Validate the pinned Oracle planning suite for three genhtml CLI metadata options."""

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
SUITE = ROOT / "compat/cases/m0-genhtml-cli-metadata-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-genhtml-cli-metadata-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-genhtml-cli-metadata-wave.json"
PLAN_BINDINGS = ROOT / "compat/behavior/plan-bindings.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-oracle.json"
SUITE_ID = "m0-genhtml-cli-metadata-contract"
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
    "css-file": {
        "option": ["--css-file", "custom.css"],
        "boundary": "--css-file custom.css",
        "tree": "8007161eaf091228b8a7d9ee595db8c964f30087b8e674cf316c68667296cb30",
        "tree_bytes": 6366, "file_count": 18,
        "references": [("parser_definition", "bin/genhtml", 7226), ("command_implementation", "bin/genhtml", 9047), ("command_implementation", "bin/genhtml", 9049)],
    },
    "description-file": {
        "option": ["--description-file", "descriptions.info"],
        "boundary": "--description-file descriptions.info",
        "tree": "be7bff53e61e5b6cb55503273d0f22220e7c85da0ab165796c76c2b51cc3564b",
        "tree_bytes": 6717, "file_count": 19,
        "references": [("parser_definition", "bin/genhtml", 7224), ("command_implementation", "bin/genhtml", 7929), ("command_implementation", "bin/genhtml", 7931)],
    },
    "keep-descriptions": {
        "option": ["--description-file", "descriptions.info", "--keep-descriptions"],
        "boundary": "--keep-descriptions",
        "tree": "b8e6fd647212d4d431921c1249bd7a55720e947c2741686bc354401a20c62a93",
        "tree_bytes": 6717, "file_count": 19,
        "references": [("parser_definition", "bin/genhtml", 7225), ("command_implementation", "bin/genhtml", 7935), ("command_implementation", "bin/genhtml", 7936)],
    },
}
FIXTURE_HASHES = {
    "control.lcovrc": "52ae4f1a03b9eeb76181421e2fdd07df004ba23bccafad30cf8d8f12cfb7671c",
    "custom.css": "d3fc3f880e9786a672f55704c8a9536a0678c076a5e7fa092b130231f3cee465",
    "descriptions.info": "0d4845084650720884059d9498949f511e354eb803ad416c0eab20d86f16f73b",
    "input.info": "a854b67fff921b6bfb53a8a2a8349b90f93a676de555682ab235d50b1fa6e45d",
    "source.c": "dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f",
}
OBSERVATIONS = {
    CONTROL: {
        "stdout_sha256": "9e22948444a26097e310953d6df4d9d7bbecd1a77a5e4fd2df29393c63d1e637", "stdout_bytes": 349,
        "stderr_sha256": "5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8", "stderr_bytes": 317,
        "file_tree_sha256": "74dd47fe7c0c02d6d7ec11702806b30207664675ca4134bc5f570385b1cfc1f4", "file_tree_bytes": 6369, "file_count": 18,
    },
}
stdout_facts = {
    "css-file": ("9e22948444a26097e310953d6df4d9d7bbecd1a77a5e4fd2df29393c63d1e637", 349),
    "description-file": ("c954365ccc25f07a9e1644d69dc9882c37a9bf21c1e5e4b9ec457756ae749d36", 477),
    "keep-descriptions": ("2eb041faeea393e3b7cc80019aba71ea24564534ca7d885f318967d343c58e01", 433),
}
for name, target in TARGETS.items():
    stdout_sha256, stdout_bytes = stdout_facts[name]
    OBSERVATIONS[f"{SUITE_ID}-{name}"] = {
        "stdout_sha256": stdout_sha256, "stdout_bytes": stdout_bytes,
        "stderr_sha256": "5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8", "stderr_bytes": 317,
        "file_tree_sha256": target["tree"], "file_tree_bytes": target["tree_bytes"], "file_count": target["file_count"],
    }


class GenhtmlCliMetadataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def assert_cli_arguments(self, cases: dict[str, dict]) -> None:
        base = ["--config-file", "control.lcovrc", "--output-directory", "report", "input.info"]
        self.assertEqual(cases[CONTROL]["arguments"], base)
        for name, target in TARGETS.items():
            self.assertEqual(cases[f"{SUITE_ID}-{name}"]["arguments"], ["--config-file", "control.lcovrc", *target["option"], "--output-directory", "report", "input.info"])

    def test_exact_case_set_and_argv(self) -> None:
        self.assertEqual(list(self.cases), [CONTROL, *[f"{SUITE_ID}-{name}" for name in TARGETS]])
        self.assertEqual(self.suite["suite_id"], SUITE_ID)
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        self.assert_cli_arguments(self.cases)
        for case in self.cases.values():
            self.assertEqual(case["surface"], "cli")
            self.assertEqual(case["command"], "genhtml")
            self.assertEqual(case["fixture"], "compat/fixtures/m0-genhtml-cli-metadata-contract")
            self.assertEqual({item["dimension"] for item in case["comparisons"]}, {"exit", "stdout", "stderr", "filesystem"})

    def test_argv_mutations_are_rejected(self) -> None:
        mutations = [("css", "css-file", "custom.css", "other.css"), ("description", "description-file", "descriptions.info", "other.info"), ("keep", "keep-descriptions", "--keep-descriptions", None)]
        for label, name, old, new in mutations:
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
        self.assertIn("TN:used_case", (FIXTURE / "input.info").read_text())
        self.assertIn("TN:unused_case", (FIXTURE / "descriptions.info").read_text())
        self.assertIn("background: rgb(1, 2, 3)", (FIXTURE / "custom.css").read_text())
        self.assertTrue(UPSTREAM.is_dir())
        for name, target in TARGETS.items():
            plan = self.plans[f"case.acceptance.command.genhtml.option.{name}"]
            refs = {(item["kind"], item["path"], item["line"]): item for item in plan["source_references"]}
            self.assertEqual(set(refs), set(target["references"]))
            self.assertEqual(list(refs), sorted(refs, key=lambda item: (item[1], item[2], item[0])))
            for (_kind, path, line), reference in refs.items():
                text = (UPSTREAM / path).read_text(encoding="utf-8").splitlines()[line - 1]
                self.assertEqual(reference["text"], text, f"{name}:{path}:{line}")

    def test_plans_and_bindings_are_target_bound(self) -> None:
        bindings = {item["id"]: item for item in json.loads(PLAN_BINDINGS.read_text())['primary_plans']}
        for name, target in TARGETS.items():
            plan_id = f"case.acceptance.command.genhtml.option.{name}"
            plan = self.plans[plan_id]
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual(plan["evidence"], [])
            expected_cases = sorted([{"suite_id": SUITE_ID, "case_id": CONTROL}, {"suite_id": SUITE_ID, "case_id": f"{SUITE_ID}-{name}"}], key=lambda item: item["case_id"])
            self.assertEqual(plan["suite_cases"], expected_cases)
            self.assertEqual(bindings[plan_id]["boundary_form"], target["boundary"])
            self.assertIn(target["tree"], plan["description"])
            self.assertIn("no Ferricov product evidence", plan["description"])

    def test_oracle_facts_are_distinct_and_stable(self) -> None:
        self.assertEqual(set(OBSERVATIONS), set(self.cases))
        self.assertEqual(len({item["file_tree_sha256"] for item in OBSERVATIONS.values()}), 4)
        self.assertEqual(len({item["stdout_sha256"] for item in OBSERVATIONS.values()}), 3)
        self.assertEqual({item["stdout_bytes"] for item in OBSERVATIONS.values()}, {349, 477, 433})
        for observation in OBSERVATIONS.values():
            self.assertIn(observation["stdout_bytes"], {349, 477, 433})
            self.assertEqual(observation["stderr_bytes"], 317)
            self.assertEqual(observation["stderr_sha256"], "5c48e2cedb1cc61c0bea56bc7df4f6a31d233ca7c0ede3b755ed359c0f174dd8")

    def test_launchers_and_review_rows_are_locked(self) -> None:
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), "3d47df2d0ee4bf1df443687f36799d9d5ecb73a424a836a1a469b9390f97f8c3")
        self.assertEqual(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(), "dbf332683768c480e68b51ea6c7b25bc5b4e9d30af2b7753a0dc8550b6e08593")
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
        review = (ROOT / "specs/001-full-lcov-compatibility/reviews/m0-genhtml-cli-metadata-planning-wave-review.md").read_text()
        self.assertIn("reference/output characterization", " ".join(review.split()))
        self.assertIn("no Ferricov candidate was run", review)
        labels = {CONTROL: "control", **{f"{SUITE_ID}-{name}": name for name in TARGETS}}
        for case_id, observation in OBSERVATIONS.items():
            prefix = "| control |" if case_id == CONTROL else f"| {labels[case_id]} |"
            rows = [line for line in review.splitlines() if line.startswith(prefix) and observation["file_tree_sha256"] in line]
            self.assertEqual(len(rows), 1, case_id)
            row = rows[0]
            for key in ("stdout_sha256", "stdout_bytes", "stderr_sha256", "stderr_bytes", "file_tree_sha256", "file_tree_bytes", "file_count"):
                self.assertIn(str(observation[key]), row)
            self.assertIn("| 0 | 23 |", row)

    def test_binding_mutation_is_rejected(self) -> None:
        contract = json.loads((ROOT / "compat/behavior/contract.json").read_text())
        mutated = copy.deepcopy(contract)
        plan = next(item for item in mutated["case_groups"] if item["id"] == "case.acceptance.command.genhtml.option.css-file")
        plan["description"] = plan["description"].replace("--css-file custom.css", "--css-file other.css", 1)
        with self.assertRaises(ValidationError):
            validate_plan_bindings(ROOT, mutated)


if __name__ == "__main__":
    unittest.main()
