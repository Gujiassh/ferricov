#!/usr/bin/env python3
"""Validate the deterministic M0 genhtml metric lcovrc suite."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "behavior"))
from validate import ValidationError, validate_plan_bindings  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "compat/cases/m0-lcovrc-genhtml-metric-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcovrc-genhtml-metric-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-lcovrc-genhtml-metric-wave.json"
CONTRACT = ROOT / "compat/behavior/contract.json"
PLAN_BINDINGS = ROOT / "compat/behavior/plan-bindings.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-oracle.json"
UPSTREAM = Path(os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference"))

CONTROL = "m0-lcovrc-genhtml-metric-control"
TARGETS = {
    "function-hi-limit": ("function-hi-limit.lcovrc", "genhtml_function_hi_limit = 50"),
    "function-med-limit": ("function-med-limit.lcovrc", "genhtml_function_med_limit = 50"),
    "branch-hi-limit": ("branch-hi-limit.lcovrc", "genhtml_branch_hi_limit = 50"),
    "branch-med-limit": ("branch-med-limit.lcovrc", "genhtml_branch_med_limit = 50"),
    "mcdc-hi-limit": ("mcdc-hi-limit.lcovrc", "genhtml_mcdc_hi_limit = 50"),
    "mcdc-med-limit": ("mcdc-med-limit.lcovrc", "genhtml_mcdc_med_limit = 50"),
    "branch-field-width": ("branch-field-width.lcovrc", "genhtml_branch_field_width = 24"),
    "mcdc-field-width": ("mcdc-field-width.lcovrc", "genhtml_mcdc_field_width = 24"),
    "overview-width": ("overview-width.lcovrc", "genhtml_overview_width = 40"),
}
TARGET_ORDER = list(TARGETS)
SOURCE_FACTS = {
    "function-hi-limit": (("bin/genhtml", 7179), ("lcovrc", 51)),
    "function-med-limit": (("bin/genhtml", 7180), ("lcovrc", 52)),
    "branch-hi-limit": (("bin/genhtml", 7181), ("lcovrc", 58)),
    "branch-med-limit": (("bin/genhtml", 7182), ("lcovrc", 59)),
    "mcdc-hi-limit": (("bin/genhtml", 7183),),
    "mcdc-med-limit": (("bin/genhtml", 7184),),
    "branch-field-width": (("bin/genhtml", 7185), ("lcovrc", 122)),
    "mcdc-field-width": (("bin/genhtml", 7186), ("lcovrc", 125)),
    "overview-width": (("bin/genhtml", 7159), ("lcovrc", 134)),
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
ORACLE_TREE_HASHES = {
    "control": "ca0d288fea65d0171795f050e89f6bfebc246bff515d7f4646c3388670a30911",
    "function-hi-limit": "69b2560b1db4856d4975c283beb9d5cdbb3a79a9d4bfa154080dc4fbe9bce635",
    "function-med-limit": "36c4f066bd5b4b962aa4f4321ba022fe7b3685e6cfa41bead0c2e9dba6079498",
    "branch-hi-limit": "070b92948b371c0fad92b928914557686fba1a8b70abc7d2288b622fe736f569",
    "branch-med-limit": "da570d74666f2a3e6846e078dffd14b306b2736ac41787c4d701d9d60f5ad011",
    "mcdc-hi-limit": "3f2483e06cf60d8a19e71992155f14f284102879486989ff6818ca1de30ff8da",
    "mcdc-med-limit": "5228f6011246b0f25381c6f9779ec56e01c34d6588efddd2717882fb79437ce6",
    "branch-field-width": "7823ad34d555f1f00bb1afad0c9ee312ff58efe9038b12c367c8a8281ae20b79",
    "mcdc-field-width": "b1978269b3d6b2aedb644efcdabf9be5f603b75dc4143f08a72163545d10d11f",
    "overview-width": "500a999149e02683c025816099cd72b435380d1b03c0d8dc1012eeee9d279eea",
}
EXPECTED_ENVIRONMENT = {
    "HOME": "/work",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "SOURCE_DATE_EPOCH": "946684800",
    "TMPDIR": "/work",
    "TZ": "UTC",
}
EXPECTED_IMAGE = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
EXPECTED_REVERSE_COMMAND = (
    "printf 'intentionally different output for harness reverse test: %s\\n' \"$1\"; exit 23"
)


class GenhtmlMetricLcovrcContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def assert_fixture_hash_lock_rejects(
        self,
        relative_path: str,
        original: bytes,
        mutated: bytes,
        label: str,
    ) -> None:
        self.assertNotEqual(mutated, original, label)
        observed = dict(FIXTURE_HASHES)
        observed[relative_path] = hashlib.sha256(mutated).hexdigest()
        with self.assertRaises(AssertionError, msg=label):
            self.assertEqual(observed, FIXTURE_HASHES)

    def test_exact_case_set_order_and_argv(self) -> None:
        expected = [CONTROL, *[f"m0-lcovrc-genhtml-metric-{suffix}" for suffix in TARGET_ORDER]]
        self.assertEqual(list(self.cases), expected)
        self.assertEqual(self.suite["suite_id"], "m0-lcovrc-genhtml-metric-contract")
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        common = ["--frames", "--function-coverage", "--branch-coverage", "--mcdc-coverage"]
        for suffix, case in zip(["control", *TARGET_ORDER], self.cases.values()):
            config = f"{suffix}.lcovrc"
            self.assertEqual(case["command"], "genhtml")
            self.assertEqual(case["fixture"], "compat/fixtures/m0-lcovrc-genhtml-metric-contract")
            self.assertEqual(case["arguments"], [*common, "--config-file", config, "--output-directory", "report", "input.info"])
            self.assertEqual({item["dimension"] for item in case["comparisons"]}, {"exit", "stdout", "stderr", "filesystem"})

    def test_source_references_match_pinned_upstream_lines(self) -> None:
        self.assertTrue(UPSTREAM.is_dir(), UPSTREAM)
        for suffix, facts in SOURCE_FACTS.items():
            plan = self.plans[f"case.acceptance.lcovrc.genhtml-{suffix}"]
            references = {(item["path"], item["line"]): item for item in plan["source_references"]}
            self.assertEqual(set(references), set(facts), suffix)
            for path, line in facts:
                lines = (UPSTREAM / path).read_text(encoding="utf-8").splitlines()
                self.assertEqual(references[(path, line)]["text"], lines[line - 1], f"{suffix}: {path}:{line}")

    def test_fixture_identity_and_semantics(self) -> None:
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
        self.assertIn("BRDA:2,0,1,0", trace)
        self.assertIn("MCDC:2,1,t,1,0,x", trace)
        self.assertIn("MCF:2\nMCH:1", trace)
        self.assertIn("MCF:2\nMCH:2", trace)

    def test_each_config_is_one_target_value_plus_writable_temp(self) -> None:
        self.assertEqual((FIXTURE / "control.lcovrc").read_text(encoding="utf-8"), "lcov_tmp_dir = /work\n")
        for suffix, (name, target) in TARGETS.items():
            self.assertEqual((FIXTURE / name).read_text(encoding="utf-8").splitlines(), ["lcov_tmp_dir = /work", target], suffix)

    def test_reverse_mutations_fail_fixture_and_argv_locks(self) -> None:
        """The exact fixture/argv guards reject semantic evidence loss."""
        original = (FIXTURE / "input.info").read_bytes()
        mutations = {
            "FN": original.replace(b"FN:1,3,alpha\n", b"", 1),
            "FNDA": original.replace(b"FNDA:1,alpha\n", b"", 1),
            "BRDA": original.replace(b"BRDA:2,0,0,1\n", b"", 1),
            "MCDC": original.replace(b"MCDC:2,1,t,1,0,x\n", b"", 1),
            "MCF/MCH": original.replace(b"MCF:2\nMCH:1\n", b"", 1),
        }
        for label, mutated in mutations.items():
            self.assert_fixture_hash_lock_rejects("input.info", original, mutated, label)

        control = self.cases[CONTROL]
        expected_argv = list(control["arguments"])
        without_frames = [item for item in expected_argv if item != "--frames"]
        with self.assertRaises(AssertionError, msg="--frames"):
            self.assertEqual(without_frames, expected_argv)

        for suffix, (name, target) in TARGETS.items():
            config = (FIXTURE / name).read_bytes()
            for label, mutated in (
                (f"{suffix}:alter", config.replace(target.encode(), target.replace("= ", "=  ").encode(), 1)),
                (f"{suffix}:remove", config.replace((target + "\n").encode(), b"", 1)),
            ):
                self.assert_fixture_hash_lock_rejects(name, config, mutated, label)

    def test_plans_bind_sorted_shared_control_and_target(self) -> None:
        self.assertEqual(len(self.plans), len(TARGETS))
        for suffix, plan in self.plans.items():
            target = suffix.removeprefix("case.acceptance.lcovrc.genhtml-")
            expected_cases = sorted([CONTROL, f"m0-lcovrc-genhtml-metric-{target}"])
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual([item["case_id"] for item in plan["suite_cases"]], expected_cases)
            self.assertIn("no Ferricov product evidence", plan["description"])

    def test_fixed_boundary_forms_are_target_config_assignments(self) -> None:
        bindings = json.loads(PLAN_BINDINGS.read_text(encoding="utf-8"))
        bound_forms = {item["id"]: item["boundary_form"] for item in bindings["primary_plans"]}
        for suffix, (_, assignment) in TARGETS.items():
            plan_id = f"case.acceptance.lcovrc.genhtml-{suffix}"
            self.assertEqual(bound_forms[plan_id], assignment, suffix)

    def test_oracle_reference_tree_hashes_are_distinct_and_planned_only(self) -> None:
        self.assertEqual(len(ORACLE_TREE_HASHES), 10)
        self.assertEqual(len(set(ORACLE_TREE_HASHES.values())), 10)
        self.assertTrue(all(plan["evidence_status"] == "planned" for plan in self.plans.values()))
        self.assertTrue(all(plan["evidence"] == [] for plan in self.plans.values()))
        review = (ROOT / "specs/001-full-lcov-compatibility/reviews/m0-lcovrc-genhtml-metric-planning-wave-review.md").read_text(encoding="utf-8")
        review = " ".join(review.split())
        self.assertIn("no ferricov candidate was run", review.lower())
        self.assertIn("owner-field-width", review)
        self.assertIn("age-field-width", review)
        self.assertIn("SOURCE_DATE_EPOCH=946684800", review)
        for tree_hash in ORACLE_TREE_HASHES.values():
            self.assertIn(tree_hash, review)

    def test_fixed_epoch_launcher_files_remain_locked(self) -> None:
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), "3d47df2d0ee4bf1df443687f36799d9d5ecb73a424a836a1a469b9390f97f8c3")
        self.assertEqual(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(), "dbf332683768c480e68b51ea6c7b25bc5b4e9d30af2b7753a0dc8550b6e08593")
        reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
        candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        self.assertEqual(reference["program"], "{command}")
        self.assertEqual(candidate["program"], "sh")
        self.assertEqual(candidate["arguments"], ["-c", EXPECTED_REVERSE_COMMAND, "sh", "{command}"])
        for launcher in (reference, candidate):
            self.assertEqual(launcher["environment_variables"], EXPECTED_ENVIRONMENT)
            self.assertEqual(launcher["runtime"], {"kind": "docker_image", "image": EXPECTED_IMAGE})
            self.assertEqual(launcher["environment"]["image"], EXPECTED_IMAGE)

    def test_per_key_plan_mutation_fails_fixed_binding(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        for target_id in self.plans:
            mutated = copy.deepcopy(contract)
            plan = next(item for item in mutated["case_groups"] if item["id"] == target_id)
            plan["description"] = plan["description"].replace("boundary `", "boundary `mutated ", 1)
            with self.assertRaises(ValidationError) as raised:
                validate_plan_bindings(ROOT, mutated)
            self.assertIn("plan bindings", str(raised.exception), target_id)


if __name__ == "__main__":
    unittest.main()
