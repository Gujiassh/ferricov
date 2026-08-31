#!/usr/bin/env python3
"""Validate the deterministic M0 genhtml layout/threshold lcovrc suite."""

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
SUITE = ROOT / "compat/cases/m0-lcovrc-genhtml-layout-contract.json"
FIXTURE = ROOT / "compat/fixtures/m0-lcovrc-genhtml-layout-contract"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-lcovrc-genhtml-layout-wave.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-oracle.json"
UPSTREAM = Path(os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference"))
CONTROL = "m0-lcovrc-genhtml-layout-control"
TARGETS = {
    "genhtml-hi-limit": ("hi-limit.lcovrc", "genhtml_hi_limit = 80"),
    "genhtml-med-limit": ("med-limit.lcovrc", "genhtml_med_limit = 85"),
    "genhtml-line-hi-limit": ("line-hi-limit.lcovrc", "genhtml_line_hi_limit = 80"),
    "genhtml-line-med-limit": ("line-med-limit.lcovrc", "genhtml_line_med_limit = 85"),
    "genhtml-line-field-width": ("line-field-width.lcovrc", "genhtml_line_field_width = 20"),
    "genhtml-missed": ("missed.lcovrc", "genhtml_missed = 1"),
    "genhtml-precision": ("precision.lcovrc", "genhtml_precision = 4"),
    "genhtml-hierarchical": ("hierarchical.lcovrc", "genhtml_hierarchical = 1"),
    "genhtml-no-prefix": ("no-prefix.lcovrc", "genhtml_no_prefix = 1"),
    "genhtml-show-navigation": ("show-navigation.lcovrc", "genhtml_show_navigation = 1"),
    "genhtml-sort": ("sort.lcovrc", "genhtml_sort = 0"),
}
SOURCE_FACTS = {
    "genhtml-hi-limit": (7175, '"genhtml_hi_limit"', 37, "genhtml_hi_limit = 90"),
    "genhtml-med-limit": (7176, '"genhtml_med_limit"', 38, "genhtml_med_limit = 75"),
    "genhtml-line-hi-limit": (7177, '"genhtml_line_hi_limit"', 44, "# genhtml_line_hi_limit = 90"),
    "genhtml-line-med-limit": (7178, '"genhtml_line_med_limit"', 45, "# genhtml_line_med_limit = 75"),
    "genhtml-line-field-width": (7158, '"genhtml_line_field_width"', 119, "genhtml_line_field_width = 12"),
    "genhtml-missed": (7194, '"genhtml_missed"', 213, "#genhtml_missed=1"),
    "genhtml-precision": (7172, '"genhtml_precision"', 210, "#genhtml_precision=1"),
    "genhtml-hierarchical": (7196, '"genhtml_hierarchical"', 189, "#genhtml_hierarchical = 1"),
    "genhtml-no-prefix": (7163, '"genhtml_no_prefix"', 154, "genhtml_no_prefix = 0"),
    "genhtml-show-navigation": (7198, '"genhtml_show_navigation"', 198, "#genhtml_show_navigation = 1"),
    "genhtml-sort": (7189, '"genhtml_sort"', 185, "genhtml_sort = 1"),
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


class GenhtmlLayoutLcovrcContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.suite["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}

    def test_exact_case_set_and_comparison_contract(self) -> None:
        expected_order = [
            CONTROL,
            *[
                f"m0-lcovrc-genhtml-layout-{suffix.removeprefix('genhtml-')}"
                for suffix in TARGETS
            ],
        ]
        self.assertEqual(list(self.cases), expected_order)
        self.assertEqual(self.suite["evidence_scope"], "compatibility")
        for case in self.cases.values():
            suffix = case["id"].removeprefix("m0-lcovrc-genhtml-layout-")
            config_name = "control.lcovrc" if suffix == "control" else f"{suffix}.lcovrc"
            self.assertEqual(case["surface"], "config")
            self.assertEqual(case["command"], "genhtml")
            self.assertEqual(case["fixture"], "compat/fixtures/m0-lcovrc-genhtml-layout-contract")
            self.assertEqual(case["arguments"][:2], ["--config-file", config_name])
            self.assertEqual(
                {item["dimension"] for item in case["comparisons"]},
                {"exit", "stdout", "stderr", "filesystem"},
            )
            self.assertEqual(case["arguments"][2:], ["--output-directory", "report", "input.info"])

    def test_source_references_match_pinned_upstream_lines(self) -> None:
        self.assertTrue(UPSTREAM.is_dir(), UPSTREAM)
        for suffix, (genhtml_line, genhtml_text, lcovrc_line, lcovrc_text) in SOURCE_FACTS.items():
            plan = self.plans[f"case.acceptance.lcovrc.genhtml-{suffix.removeprefix('genhtml-')}"]
            references = {item["path"]: item for item in plan["source_references"]}
            self.assertEqual(set(references), {"bin/genhtml", "lcovrc"}, suffix)
            self.assertEqual(references["bin/genhtml"]["line"], genhtml_line, suffix)
            self.assertEqual(references["lcovrc"]["line"], lcovrc_line, suffix)
            for path, line, text in (
                ("bin/genhtml", genhtml_line, genhtml_text),
                ("lcovrc", lcovrc_line, lcovrc_text),
            ):
                lines = (UPSTREAM / path).read_text(encoding="utf-8").splitlines()
                self.assertIn(text, lines[line - 1], f"{suffix}: {path}:{line}")

    def test_fixture_identity(self) -> None:
        expected = {
            "control.lcovrc": "84fa5574e87ec7dcb72981b9a02a06570a33ab801c298b541e13678430caec15",
            "hi-limit.lcovrc": "3db853f93e8df2770e29b53c64cb3ce45708acd3c8d16a83be026933fa857d1b",
            "hierarchical.lcovrc": "7c11e63574a4b39ee4cd9c6ad57c19216173dfad2f5796f806c5e84f24a28683",
            "input.info": "b6c54c30c575bde694ac8fdf386f29d4c2ca419f41b68afbb91075e981ccf10d",
            "line-field-width.lcovrc": "6085c705baf4899ac71a24a10a5fb135c1437ac4dffd8da07778d3c2e7fc3470",
            "line-hi-limit.lcovrc": "abbf0ad2a8dd7f72090e346c53f4bd135b2f610275b3efbb6c93c89dc9cead0e",
            "line-med-limit.lcovrc": "45d78a0299a5b424a42b03291cc710d44657bda01665d6faae667276c324a883",
            "med-limit.lcovrc": "8d906a78078b1fd5993f084514548887156da0c9f996da88438735909c7509e6",
            "missed.lcovrc": "d1ac70f5069b715bf8db6010787da1b6def6c7a6d1cfddcc56db6482f829e24b",
            "no-prefix.lcovrc": "9e26222c06ea26dca83d711ea1b7c205df324309f6fd5cd19d9203fbe1bd2fe3",
            "precision.lcovrc": "a15e0804f003bcb4d519991a1fc1da13042d1183a3ac3c5c9fc55f354f6038e3",
            "show-navigation.lcovrc": "bd3c49ec48c91a1f375a59a47afb54b0bc2d0092d5eed606069558166365f329",
            "sort.lcovrc": "535169a671cf723c69176f7eef892b83ba72d3b58380751387d1bc99fe45e8da",
            "src/alpha.c": "59002ffca81650cc7b2eb2b2fef6f89302c018fffe86dd8a9536a019ffb3d4db",
            "src/nested/beta.c": "a0d995338b87fcbce621c1644ecbf2518ceb5693c22cf08b7700520e05373876",
        }
        actual = {
            path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in FIXTURE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, expected)

    def test_each_config_is_one_target_value_plus_writable_temp(self) -> None:
        self.assertEqual((FIXTURE / "control.lcovrc").read_text(), "lcov_tmp_dir = /work\n")
        for suffix, (name, target) in TARGETS.items():
            case_suffix = suffix.removeprefix("genhtml-")
            self.assertEqual(
                (FIXTURE / name).read_text(encoding="utf-8").splitlines(),
                ["lcov_tmp_dir = /work", target],
                suffix,
            )
            self.assertEqual(
                self.cases[f"m0-lcovrc-genhtml-layout-{case_suffix}"]["arguments"][:2],
                ["--config-file", name],
            )

    def test_threshold_fixture_has_two_observable_rates(self) -> None:
        trace = (FIXTURE / "input.info").read_text(encoding="utf-8")
        self.assertIn("SF:/work/src/alpha.c", trace)
        self.assertIn("SF:/work/src/nested/beta.c", trace)
        self.assertIn("LF:5\nLH:4", trace)
        self.assertIn("LF:2\nLH:2", trace)

    def test_plans_bind_shared_control_and_nondefault_case(self) -> None:
        self.assertEqual(len(self.plans), 11)
        for plan_id, plan in self.plans.items():
            suffix = plan_id.removeprefix("case.acceptance.lcovrc.genhtml-")
            case_id = f"m0-lcovrc-genhtml-layout-{suffix}"
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual(
                [item["case_id"] for item in plan["suite_cases"]],
                [CONTROL, case_id],
            )
            self.assertIn("no Ferricov product evidence", plan["description"])

    def test_fixed_epoch_launcher_files_remain_locked(self) -> None:
        self.assertEqual(
            hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
            "3d47df2d0ee4bf1df443687f36799d9d5ecb73a424a836a1a469b9390f97f8c3",
        )
        self.assertEqual(
            hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
            "dbf332683768c480e68b51ea6c7b25bc5b4e9d30af2b7753a0dc8550b6e08593",
        )
        reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
        candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        self.assertEqual(reference["program"], "{command}")
        self.assertEqual(reference["arguments"], [])
        self.assertEqual(candidate["program"], "sh")
        self.assertEqual(
            candidate["arguments"],
            ["-c", EXPECTED_REVERSE_COMMAND, "sh", "{command}"],
        )
        for launcher in (reference, candidate):
            self.assertEqual(launcher["environment_variables"], EXPECTED_ENVIRONMENT)
            self.assertEqual(launcher["runtime"], {"kind": "docker_image", "image": EXPECTED_IMAGE})
            self.assertEqual(launcher["environment"]["image"], EXPECTED_IMAGE)
            self.assertEqual(launcher["environment"]["operating_system"], "Debian 12")
            self.assertEqual(launcher["environment"]["architecture"], "x86_64")
            self.assertEqual(launcher["environment"]["compiler"], "GCC 12.2.0")
        self.assertNotEqual(reference["program"], candidate["program"])

    def test_planned_reference_facts_are_not_product_evidence(self) -> None:
        self.assertTrue(all(plan["evidence_status"] == "planned" for plan in self.plans.values()))
        self.assertTrue(all(plan["evidence"] == [] for plan in self.plans.values()))
        review = (ROOT / "specs/001-full-lcov-compatibility/reviews/m0-lcovrc-genhtml-layout-planning-wave-review.md").read_text(encoding="utf-8")
        review_text = " ".join(review.split())
        self.assertIn("reference/output characterization", review_text)
        self.assertIn("no Ferricov candidate was run", review_text)
        self.assertIn("Product compatibility evidence", review_text)

    def test_plan_boundary_mutation_fails_fixed_binding(self) -> None:
        contract_path = ROOT / "compat/behavior/contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(contract)
        target = next(
            item for item in mutated["case_groups"]
            if item["id"] == "case.acceptance.lcovrc.genhtml-hi-limit"
        )
        target["description"] = target["description"].replace("= 80", "= 81", 1)
        with self.assertRaises(ValidationError) as raised:
            validate_plan_bindings(ROOT, mutated)
        self.assertIn("plan bindings drift", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
