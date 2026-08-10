#!/usr/bin/env python3
"""Validate the pinned Oracle planning suite for three genhtml CLI options."""

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
SUITE = ROOT / "compat/cases/m0-genhtml-cli-metric-layout-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcovrc-genhtml-metric-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-genhtml-cli-metric-layout-wave.json"
REVIEW = ROOT / "specs/001-full-lcov-compatibility/reviews/m0-genhtml-cli-metric-layout-planning-wave-review.md"
PLAN_BINDINGS = ROOT / "compat/behavior/plan-bindings.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-report-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-report-oracle.json"
SUITE_ID = "m0-genhtml-cli-metric-layout-contract"
CONTROL = "m0-genhtml-cli-metric-layout-control"
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
REVERSE_COMMAND = (
    "printf 'intentionally different output for harness reverse test: %s\\n' \"$1\"; exit 23"
)
COMMON_ARGUMENTS = [
    "--function-coverage",
    "--branch-coverage",
    "--mcdc-coverage",
    "--config-file",
    "control.lcovrc",
]
OUTPUT_ARGUMENTS = ["--output-directory", "report", "input.info"]

TARGETS = {
    "frames": {
        "option": ["--frames"],
        "boundary": "--frames",
        "references": [
            ("parser_definition", "bin/genhtml", 7253),
            ("command_implementation", "bin/genhtml", 7552),
            ("command_implementation", "bin/genhtml", 8467),
        ],
    },
    "precision": {
        "option": ["--precision", "4"],
        "boundary": "--precision 4",
        "references": [
            ("parser_definition", "bin/genhtml", 7266),
            ("command_implementation", "bin/genhtml", 7558),
            ("command_implementation", "lib/lcovutil.pm", 2768),
        ],
    },
    "no-sort": {
        "option": ["--no-sort"],
        "boundary": "--no-sort",
        "references": [
            ("parser_definition", "bin/genhtml", 7265),
            ("command_implementation", "bin/genhtml", 7337),
            ("command_implementation", "bin/genhtml", 8970),
        ],
    },
}

FIXTURE_HASHES = {
    "branch-field-width.lcovrc": "ffa4a4455889a8f30111c109f4ef96f244c60ae2c5ee062352eddf87ada1a10a",
    "branch-hi-limit.lcovrc": "9d10662924a31ace7b4af099fa607c10949455c59a5fb62f51ff7e16edc7f62e",
    "branch-med-limit.lcovrc": "9459e87e8327220f8732066905809570f7dacbe37682d23fa269f8f18ddc4b23",
    "control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15",
    "function-hi-limit.lcovrc": "6b315c9b6a440ce118b31b5a67b7ba4e67a14717b233103cacd9dadcfc0d4fcb",
    "function-med-limit.lcovrc": "e85b6a11e374fcf7e6c5782332eb040ebf7fccdab10bb0fe6fd3d9fc952b7ecd",
    "input.info": "e5e68b2c617cb0f85fad61758f02976ea52a13496bfd3147c5c0dc6da5b60b31",
    "mcdc-field-width.lcovrc": "7fd07e5d0858476d197452bb47d11b219809054310334c5426c5979dcdb24f9a",
    "mcdc-hi-limit.lcovrc": "ec275fae8cb07cbcc77295c4336ffe2557527a3324f8e4b5340aced424b4b5a6",
    "mcdc-med-limit.lcovrc": "5bd17fe74b64777dfd5d3ac140b8ce6608e70a7da9da2751e9ba7540dfeb3c04",
    "overview-width.lcovrc": "17fea974b6c1ac3932bed7dbc875591f14fc6d2b77b8b1f14627ce842388a4b4",
    "src/alpha.c": "71372039482c5627e1fc9db0127f4416345786bbeb2445cbb0a07db48acb05a3",
    "src/beta.c": "c40605c9d50ac4bce48629b2f8f509722f4a67e2860a5c25e8399017f8200b73",
}

ORACLE_OBSERVATIONS = {
    CONTROL: {
        "stdout_sha256": "dddd460b40607956b408f0efc59e812784e381a354b63f3303f81b0245ff4e2c",
        "stdout_bytes": 550,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "ba20427ff8a62d5ae3fbfec3d81600908a1cdeec524734deb2ce58a512c97904",
        "file_tree_bytes": 11834,
        "file_count": 33,
    },
    "m0-genhtml-cli-metric-layout-frames": {
        "stdout_sha256": "dddd460b40607956b408f0efc59e812784e381a354b63f3303f81b0245ff4e2c",
        "stdout_bytes": 550,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "9c5524a2b6856b12a7820785c2b7ca28c8abe4785dbae8ea62416af741453998",
        "file_tree_bytes": 14075,
        "file_count": 39,
    },
    "m0-genhtml-cli-metric-layout-precision": {
        "stdout_sha256": "479c721b6327aede02c6c3a1265851bdb89404a37734a828d41a74c7d14a1083",
        "stdout_bytes": 562,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "582cc0c35384825eba455cf952f056dffc1271e6b46c820acb502ff5f0ac7bba",
        "file_tree_bytes": 11834,
        "file_count": 33,
    },
    "m0-genhtml-cli-metric-layout-no-sort": {
        "stdout_sha256": "dddd460b40607956b408f0efc59e812784e381a354b63f3303f81b0245ff4e2c",
        "stdout_bytes": 550,
        "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "stderr_bytes": 0,
        "file_tree_sha256": "233d08f67421873aacd37a84670e9bcaa7c6dece107af6d215877e0921200fa7",
        "file_tree_bytes": 9346,
        "file_count": 26,
    },
}


class GenhtmlCliMetricLayoutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def assert_cli_arguments(self, cases: dict[str, dict]) -> None:
        self.assertEqual(cases[CONTROL]["arguments"], [*COMMON_ARGUMENTS, *OUTPUT_ARGUMENTS])
        for name, target in TARGETS.items():
            case = cases[f"m0-genhtml-cli-metric-layout-{name}"]
            self.assertEqual(
                case["arguments"],
                [*COMMON_ARGUMENTS, *target["option"], *OUTPUT_ARGUMENTS],
            )

    def test_exact_case_set_and_argv(self) -> None:
        expected = [CONTROL, *(f"m0-genhtml-cli-metric-layout-{name}" for name in TARGETS)]
        self.assertEqual(list(self.cases), expected)
        self.assertEqual(self.suite["suite_id"], SUITE_ID)
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        for case in self.cases.values():
            self.assertEqual(case["surface"], "cli")
            self.assertEqual(case["command"], "genhtml")
            self.assertEqual(case["fixture"], "compat/fixtures/m0-lcovrc-genhtml-metric-contract")
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )
        self.assert_cli_arguments(self.cases)

    def test_cli_argv_mutations_are_rejected(self) -> None:
        mutations = {
            "drop-frames": ("frames", "--frames", None),
            "precision-value": ("precision", "4", "3"),
            "drop-no-sort": ("no-sort", "--no-sort", None),
        }
        for label, (name, old, new) in mutations.items():
            cases = copy.deepcopy(self.cases)
            arguments = cases[f"m0-genhtml-cli-metric-layout-{name}"]["arguments"]
            if new is None:
                arguments.remove(old)
            else:
                arguments[arguments.index(old)] = new
            with self.subTest(label=label), self.assertRaises(AssertionError):
                self.assert_cli_arguments(cases)

    def test_fixture_identity_and_semantic_anchors(self) -> None:
        actual = {
            path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in FIXTURE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, FIXTURE_HASHES)
        trace = (FIXTURE / "input.info").read_text(encoding="utf-8")
        self.assertIn("FNF:2\nFNH:1", trace)
        self.assertIn("FNF:2\nFNH:2", trace)
        self.assertIn("LF:7\nLH:3", trace)
        self.assertIn("LF:7\nLH:7", trace)
        self.assertEqual(trace.count("BRDA:"), 8)
        self.assertIn("MCDC:2,1,t,1,0,x", trace)
        self.assertIn("MCF:2\nMCH:1", trace)
        self.assertIn("MCF:2\nMCH:2", trace)

    def test_source_references_match_pinned_upstream_lines(self) -> None:
        self.assertTrue(UPSTREAM.is_dir(), UPSTREAM)
        for name, target in TARGETS.items():
            plan = self.plans[f"case.acceptance.command.genhtml.option.{name}"]
            references = {
                (item["kind"], item["path"], item["line"]): item
                for item in plan["source_references"]
            }
            self.assertEqual(set(references), set(target["references"]), name)
            self.assertEqual(
                list(references),
                sorted(references, key=lambda item: (item[1], item[2], item[0])),
                name,
            )
            for (_kind, path, line), reference in references.items():
                upstream_text = (UPSTREAM / path).read_text(encoding="utf-8").splitlines()[line - 1]
                self.assertEqual(reference["text"], upstream_text, f"{name}: {path}:{line}")

    def test_plans_bind_shared_control_and_target(self) -> None:
        bindings = {
            item["id"]: item
            for item in json.loads(PLAN_BINDINGS.read_text(encoding="utf-8"))["primary_plans"]
        }
        for name, target in TARGETS.items():
            plan_id = f"case.acceptance.command.genhtml.option.{name}"
            target_id = f"m0-genhtml-cli-metric-layout-{name}"
            plan = self.plans[plan_id]
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual(plan["evidence"], [])
            self.assertEqual(
                plan["suite_cases"],
                [
                    {"suite_id": SUITE_ID, "case_id": CONTROL},
                    {"suite_id": SUITE_ID, "case_id": target_id},
                ],
            )
            self.assertEqual(bindings[plan_id]["boundary_form"], target["boundary"])
            self.assertIn("no Ferricov product evidence", plan["description"])
            self.assertIn(ORACLE_OBSERVATIONS[target_id]["file_tree_sha256"], plan["description"])

    def test_reference_observations_are_stable_and_target_specific(self) -> None:
        self.assertEqual(set(ORACLE_OBSERVATIONS), set(self.cases))
        self.assertEqual(len({item["file_tree_sha256"] for item in ORACLE_OBSERVATIONS.values()}), 4)
        for observation in ORACLE_OBSERVATIONS.values():
            self.assertEqual(observation["stderr_bytes"], 0)
            self.assertEqual(
                observation["stderr_sha256"],
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            )
        self.assertEqual(ORACLE_OBSERVATIONS["m0-genhtml-cli-metric-layout-frames"]["file_count"], 39)
        self.assertEqual(ORACLE_OBSERVATIONS["m0-genhtml-cli-metric-layout-no-sort"]["file_count"], 26)
        self.assertEqual(ORACLE_OBSERVATIONS["m0-genhtml-cli-metric-layout-precision"]["stdout_bytes"], 562)

    def test_launchers_are_pinned_and_distinct(self) -> None:
        self.assertEqual(
            hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
            "5dbefc9aca20a447b8231d85a69b726996275a703f49433402d83c6171d84838",
        )
        self.assertEqual(
            hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
            "780cfcf3f1cbaa5e59c37c7e5daf93cfa1d0191dcbb8e62f403df50ec3d8cdf9",
        )
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

    def test_review_records_final_oracle_facts(self) -> None:
        raw_review = REVIEW.read_text(encoding="utf-8")
        review = " ".join(raw_review.split())
        self.assertIn("reference/output characterization", review)
        self.assertIn("no Ferricov candidate was run", review)
        labels = {
            CONTROL: "control",
            "m0-genhtml-cli-metric-layout-frames": "frames",
            "m0-genhtml-cli-metric-layout-precision": "precision 4",
            "m0-genhtml-cli-metric-layout-no-sort": "no-sort",
        }
        for case_id, observation in ORACLE_OBSERVATIONS.items():
            prefix = f"| `{labels[case_id]}` |" if case_id != CONTROL else "| control |"
            rows = [
                line
                for line in raw_review.splitlines()
                if line.startswith(prefix) and observation["file_tree_sha256"] in line
            ]
            self.assertEqual(len(rows), 1, case_id)
            row = rows[0]
            for key in (
                "stdout_sha256",
                "stdout_bytes",
                "stderr_sha256",
                "stderr_bytes",
                "file_tree_sha256",
                "file_tree_bytes",
                "file_count",
            ):
                self.assertIn(str(observation[key]), row, f"{case_id}:{key}")
            self.assertIn("| 0 | 23 |", row, case_id)

    def test_plan_binding_mutation_is_rejected(self) -> None:
        contract = json.loads((ROOT / "compat/behavior/contract.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(contract)
        plan = next(
            item
            for item in mutated["case_groups"]
            if item["id"] == "case.acceptance.command.genhtml.option.frames"
        )
        plan["description"] = plan["description"].replace("--frames", "--wrong-frames", 1)
        with self.assertRaises(ValidationError):
            validate_plan_bindings(ROOT, mutated)


if __name__ == "__main__":
    unittest.main()
