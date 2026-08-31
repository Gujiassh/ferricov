#!/usr/bin/env python3
"""Validate the pinned Oracle planning suite for three genhtml CLI report options."""

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
SUITE = ROOT / "compat/cases/m0-genhtml-cli-report-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcovrc-genhtml-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-genhtml-cli-report-wave.json"
REVIEW = ROOT / "specs/001-full-lcov-compatibility/reviews/m0-genhtml-cli-report-planning-wave-review.md"
PLAN_BINDINGS = ROOT / "compat/behavior/plan-bindings.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-oracle.json"
SUITE_ID = "m0-genhtml-cli-report-contract"
CONTROL = f"{SUITE_ID}-control"
IMAGE = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
ENVIRONMENT = {
    "HOME": "/work",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "SOURCE_DATE_EPOCH": "946684800",
    "TMPDIR": "/work",
    "TZ": "UTC",
}
REVERSE_COMMAND = (
    "printf 'intentionally different output for harness reverse test: %s\\n' \"$1\"; exit 23"
)

TARGETS = {
    "footer": {
        "option": ["--footer", "CLI Footer"],
        "boundary": "--footer CLI Footer",
        "references": [
            ("parser_definition", "bin/genhtml", 7222),
            ("command_implementation", "bin/genhtml", 7157),
            ("command_implementation", "bin/genhtml", 11706),
        ],
        "tree": "a05c4105eff8f5dafd6af9c443ea4993b93d8465e7b10a418ea50c67ae5e3a3f",
        "tree_bytes": 8882,
        "file_count": 28,
    },
    "no-checksum": {
        "option": ["--no-checksum"],
        "boundary": "--no-checksum",
        "references": [
            ("parser_definition", "lib/lcovutil.pm", 1243),
            ("command_implementation", "lib/lcovutil.pm", 1596),
            ("command_implementation", "lib/lcovutil.pm", 9779),
        ],
        "tree": "0b2d3c12d04b463b1c356b0369186a2c3f791556b64c9de7191a16856654bd5c",
        "tree_bytes": 8882,
        "file_count": 28,
    },
    "no-html": {
        "option": ["--no-html"],
        "boundary": "--no-html",
        "references": [
            ("parser_definition", "bin/genhtml", 7251),
            ("command_implementation", "bin/genhtml", 7291),
            ("command_implementation", "bin/genhtml", 7951),
        ],
        "tree": "aa4c1afab3bf0f16591e032c947f8b558c139a4fe36ab2d877da293f03ed41e8",
        "tree_bytes": 4610,
        "file_count": 15,
    },
}
FIXTURE_HASHES = {
    "control.lcovrc": "52ae4f1a03b9eeb76181421e2fdd07df004ba23bccafad30cf8d8f12cfb7671c",
    "epilog.html": "aa1cf6a0ce83031a10af23b9b29cbbcb40eb42729627e39364d10b5ff488bfe6",
    "epilog.lcovrc": "962e9c075e720874b17911aea51deedd58f263a52b78b4f3589c33546ee2c059",
    "extension.lcovrc": "ee9f52363f6320d55c87c6166631cb0d2783ffdf197c557bd9d3a573eb976e51",
    "gzip.lcovrc": "65f02549875547c0e11ca8a91ae0cf7329c231d3d1dcebea9d529052730e48d4",
    "header.lcovrc": "a8cc4dd24ee0c328dbb808da64971da07487b66baf0c58edb1d60a369b453211",
    "input.info": "62f85d64dd938086dc7ebe885efbd0cadf3b9381549d7edd1ea444adee0428a7",
    "legend.lcovrc": "66881fea856c320bdc22d55b2f751f7f7a20de682b34157ab9b346c91aa8f0e9",
    "no-source.lcovrc": "b274ffc1de6481cf01d49505127a521324e6c3fa2c14e66c92a31b6625b3c6ce",
    "num-spaces.lcovrc": "afaa5d8a4a7f99665b1070574d3659fb37b3afae60712722ecbd6ed26b2544af",
    "prolog.html": "26aa57468b95ba84596510d9c2dff0a9b530d5f256e236ddc4d4cb5fbf9161e7",
    "prolog.lcovrc": "8cc317511b8dc61fb4d904077d70ff5b88a6b1c7dcbe4449f283c7f08b8b4928",
    "source.c": "dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f",
}
ORACLE_OBSERVATIONS = {
    CONTROL: {
        "stdout_sha256": "52f1bab31080e9038c81190aea0fb1a79d5d54b557d3611468a8e930c3fc5137",
        "stdout_bytes": 337,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "b3148b0869ea307e9ea36fd8494cee1fd12268377b90c1d6a87c073ddeb88329",
        "file_tree_bytes": 8882,
        "file_count": 28,
    },
}
for name, target in TARGETS.items():
    ORACLE_OBSERVATIONS[f"{SUITE_ID}-{name}"] = {
        "stdout_sha256": ORACLE_OBSERVATIONS[CONTROL]["stdout_sha256"],
        "stdout_bytes": 337,
        "stderr_sha256": ORACLE_OBSERVATIONS[CONTROL]["stderr_sha256"],
        "stderr_bytes": 0,
        "file_tree_sha256": target["tree"],
        "file_tree_bytes": target["tree_bytes"],
        "file_count": target["file_count"],
    }


class GenhtmlCliReportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def assert_cli_arguments(self, cases: dict[str, dict]) -> None:
        self.assertEqual(cases[CONTROL]["arguments"], ["--config-file", "control.lcovrc", "--output-directory", "report", "input.info"])
        for name, target in TARGETS.items():
            self.assertEqual(
                cases[f"{SUITE_ID}-{name}"]["arguments"],
                ["--config-file", "control.lcovrc", *target["option"], "--output-directory", "report", "input.info"],
            )

    def test_exact_case_set_and_argv(self) -> None:
        self.assertEqual(list(self.cases), [CONTROL, f"{SUITE_ID}-footer", f"{SUITE_ID}-no-html", f"{SUITE_ID}-no-checksum"])
        self.assertEqual(self.suite["suite_id"], SUITE_ID)
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        for case in self.cases.values():
            self.assertEqual(case["surface"], "cli")
            self.assertEqual(case["command"], "genhtml")
            self.assertEqual(case["fixture"], "compat/fixtures/m0-lcovrc-genhtml-contract")
            self.assertEqual({item["dimension"] for item in case["comparisons"]}, {"exit", "stdout", "stderr", "filesystem"})
        self.assert_cli_arguments(self.cases)

    def test_cli_argv_mutations_are_rejected(self) -> None:
        mutations = {
            "footer-value": ("footer", "CLI Footer", "Other Footer"),
            "drop-no-html": ("no-html", "--no-html", None),
            "drop-no-checksum": ("no-checksum", "--no-checksum", None),
        }
        for label, (name, old, new) in mutations.items():
            cases = copy.deepcopy(self.cases)
            args = cases[f"{SUITE_ID}-{name}"]["arguments"]
            if new is None:
                args.remove(old)
            else:
                args[args.index(old)] = new
            with self.subTest(label=label), self.assertRaises(AssertionError):
                self.assert_cli_arguments(cases)

    def test_fixture_identity_and_semantic_anchors(self) -> None:
        actual = {path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in FIXTURE.rglob("*") if path.is_file()}
        self.assertEqual(actual, FIXTURE_HASHES)
        self.assertIn("\tint covered", (FIXTURE / "source.c").read_text(encoding="utf-8"))
        trace = (FIXTURE / "input.info").read_text(encoding="utf-8")
        self.assertIn("SF:/work/source.c", trace)
        self.assertIn("LF:5\nLH:3", trace)

    def test_source_references_match_pinned_upstream_lines(self) -> None:
        self.assertTrue(UPSTREAM.is_dir(), UPSTREAM)
        for name, target in TARGETS.items():
            plan = self.plans[f"case.acceptance.command.genhtml.option.{name}"]
            refs = {(item["kind"], item["path"], item["line"]): item for item in plan["source_references"]}
            expected = {(kind, path, line) for kind, path, line in target["references"]}
            self.assertEqual(set(refs), expected, name)
            self.assertEqual(list(refs), sorted(refs, key=lambda item: (item[1], item[2], item[0])), name)
            for (_kind, path, line), reference in refs.items():
                text = (UPSTREAM / path).read_text(encoding="utf-8").splitlines()[line - 1]
                self.assertEqual(reference["text"], text, f"{name}: {path}:{line}")

    def test_plans_bind_shared_control_and_target(self) -> None:
        bindings = {item["id"]: item for item in json.loads(PLAN_BINDINGS.read_text(encoding="utf-8"))["primary_plans"]}
        for name, target in TARGETS.items():
            plan_id = f"case.acceptance.command.genhtml.option.{name}"
            plan = self.plans[plan_id]
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual(plan["evidence"], [])
            self.assertEqual(plan["suite_cases"], [{"suite_id": SUITE_ID, "case_id": CONTROL}, {"suite_id": SUITE_ID, "case_id": f"{SUITE_ID}-{name}"}])
            self.assertEqual(bindings[plan_id]["boundary_form"], target["boundary"])
            self.assertIn("no Ferricov product evidence", plan["description"])
            self.assertIn(target["tree"], plan["description"])

    def test_reference_observations_are_stable_and_target_specific(self) -> None:
        self.assertEqual(set(ORACLE_OBSERVATIONS), set(self.cases))
        self.assertEqual(len({item["file_tree_sha256"] for item in ORACLE_OBSERVATIONS.values()}), 4)
        control_tree = ORACLE_OBSERVATIONS[CONTROL]["file_tree_sha256"]
        for case_id, observation in ORACLE_OBSERVATIONS.items():
            self.assertEqual(observation["stdout_bytes"], 337)
            self.assertEqual(observation["stderr_bytes"], 0)
            self.assertEqual(observation["stderr_sha256"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
            if case_id != CONTROL:
                self.assertNotEqual(observation["file_tree_sha256"], control_tree)

    def test_launchers_are_pinned_and_distinct(self) -> None:
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), "3d47df2d0ee4bf1df443687f36799d9d5ecb73a424a836a1a469b9390f97f8c3")
        self.assertEqual(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(), "dbf332683768c480e68b51ea6c7b25bc5b4e9d30af2b7753a0dc8550b6e08593")
        reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
        candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        for launcher in (reference, candidate):
            self.assertEqual(launcher["runtime"], {"kind": "docker_image", "image": IMAGE})
            self.assertEqual(launcher["environment_variables"], ENVIRONMENT)
            self.assertEqual(launcher["environment"]["image"], IMAGE)
        self.assertEqual(reference["program"], "{command}")
        self.assertEqual(reference["arguments"], [])
        self.assertEqual(candidate["program"], "sh")
        self.assertEqual(candidate["arguments"], ["-c", REVERSE_COMMAND, "sh", "{command}"])

    def test_review_records_case_bound_oracle_facts(self) -> None:
        raw_review = REVIEW.read_text(encoding="utf-8")
        review = " ".join(raw_review.split())
        self.assertIn("reference/output characterization", review)
        self.assertIn("no Ferricov candidate was run", review)
        labels = {CONTROL: "control", **{f"{SUITE_ID}-{name}": name for name in TARGETS}}
        for case_id, observation in ORACLE_OBSERVATIONS.items():
            prefix = f"| `{labels[case_id]}` |" if case_id != CONTROL else "| control |"
            rows = [line for line in raw_review.splitlines() if line.startswith(prefix) and observation["file_tree_sha256"] in line]
            self.assertEqual(len(rows), 1, case_id)
            row = rows[0]
            for key in ("stdout_sha256", "stdout_bytes", "stderr_sha256", "stderr_bytes", "file_tree_sha256", "file_tree_bytes", "file_count"):
                self.assertIn(str(observation[key]), row, f"{case_id}:{key}")
            self.assertIn("| 0 | 23 |", row, case_id)

    def test_plan_binding_mutation_is_rejected(self) -> None:
        contract = json.loads((ROOT / "compat/behavior/contract.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(contract)
        plan = next(item for item in mutated["case_groups"] if item["id"] == "case.acceptance.command.genhtml.option.footer")
        plan["description"] = plan["description"].replace("--footer CLI Footer", "--footer wrong", 1)
        with self.assertRaises(ValidationError):
            validate_plan_bindings(ROOT, mutated)


if __name__ == "__main__":
    unittest.main()
