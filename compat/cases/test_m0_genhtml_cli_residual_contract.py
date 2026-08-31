#!/usr/bin/env python3
"""Validate residual genhtml CLI planning suite, Oracle observations, and integrity gates."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_CASES_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_CASES_DIR))
sys.path.insert(0, str(_CASES_DIR.parent / "behavior"))
from validate import ValidationError, validate_plan_bindings  # noqa: E402

import m0_genhtml_cli_residual_contract as residual  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = Path(os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference"))
SUITE = residual.SUITE_PATH
FIXTURE = ROOT / residual.FIXTURE
OBSERVATIONS_PATH = FIXTURE / "oracle-observations.json"
FRAGMENT = ROOT / "compat/behavior/fragments/authored/m0-genhtml-cli-residual-wave.json"
PLAN_BINDINGS = ROOT / "compat/behavior/plan-bindings.json"
REFERENCE = ROOT / "compat/launchers/lcov-v2.5-genhtml-oracle.json"
CANDIDATE = ROOT / "compat/launchers/different-genhtml-oracle.json"
REVIEW = (
    ROOT
    / "specs/001-full-lcov-compatibility/reviews/m0-genhtml-cli-residual-planning-wave-review.md"
)
CONTROLLER_REVIEW = (
    ROOT
    / "specs/001-full-lcov-compatibility/reviews/m0-genhtml-cli-residual-planning-wave-controller-review.md"
)
SUITE_ID = residual.SUITE_ID
CONTROL = residual.CONTROL
CANONICAL_CASES = residual.CANONICAL_CASES
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


class GenhtmlCliResidualContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.observations = json.loads(OBSERVATIONS_PATH.read_text(encoding="utf-8"))
        cls.obs_by_id = {item["case_id"]: item for item in cls.observations["cases"]}
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.plans = {case["id"]: case for case in fragment["case_groups"]}
        cls.fixture_hashes = {
            path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in FIXTURE.rglob("*")
            if path.is_file()
        }

    def test_suite_passes_production_validator(self) -> None:
        residual.validate_suite_document(self.suite)
        residual.validate_committed_suite()

    def test_exact_case_set_and_argv(self) -> None:
        self.assertEqual([case["id"] for case in self.suite["cases"]], list(CANONICAL_CASES))
        for case in self.suite["cases"]:
            expected = CANONICAL_CASES[case["id"]]
            self.assertEqual(case["arguments"], expected["arguments"])
            self.assertEqual(case["comparisons"], residual.EXACT_COMPARISONS)

    def test_suite_mutations_are_rejected_by_production_validator(self) -> None:
        """Mutations must fail the production residual gate, not a test-local copy."""
        mutations = []

        def add(label: str, mutator) -> None:
            mutated = copy.deepcopy(self.suite)
            mutator(mutated)
            mutations.append((label, mutated))

        add("delete-preserve-flag", lambda s: s["cases"][1]["arguments"].remove("--preserve"))
        add(
            "replace-preserve-token",
            lambda s: s["cases"][1]["arguments"].__setitem__(
                s["cases"][1]["arguments"].index("--preserve"), "--version"
            ),
        )
        add(
            "reorder-preserve-args",
            lambda s: s["cases"][1].__setitem__(
                "arguments",
                [
                    "--preserve",
                    "--config-file",
                    "control.lcovrc",
                    "--output-directory",
                    "report",
                    "input.info",
                ],
            ),
        )
        add("delete-synth-flag", lambda s: s["cases"][2]["arguments"].remove("--synthesize-missing"))
        add(
            "replace-multi-second-trace",
            lambda s: s["cases"][3]["arguments"].__setitem__(
                s["cases"][3]["arguments"].index("input2.info"), "other.info"
            ),
        )
        add(
            "reorder-multi-traces",
            lambda s: s["cases"][3].__setitem__(
                "arguments",
                [
                    "--config-file",
                    "control.lcovrc",
                    "--output-directory",
                    "report",
                    "input2.info",
                    "input.info",
                ],
            ),
        )
        add(
            "replace-stdout-normalizer",
            lambda s: s["cases"][0]["comparisons"].__setitem__(
                1, {"dimension": "stdout", "normalizer": "text-crlf-to-lf-v1"}
            ),
        )
        add(
            "reorder-comparisons",
            lambda s: s["cases"][0].__setitem__(
                "comparisons",
                [
                    {"dimension": "filesystem", "normalizer": "exact-v1"},
                    {"dimension": "exit", "normalizer": "exact-v1"},
                    {"dimension": "stdout", "normalizer": "exact-v1"},
                    {"dimension": "stderr", "normalizer": "exact-v1"},
                ],
            ),
        )
        add(
            "invalid-normalizer-enum",
            lambda s: s["cases"][0]["comparisons"].__setitem__(
                1, {"dimension": "stdout", "normalizer": "exact-v2"}
            ),
        )

        schema_only = residual.load_suite_schema()
        for label, mutated in mutations:
            with self.subTest(label=label):
                with self.assertRaises(residual.ResidualSuiteValidationError):
                    residual.validate_suite_document(mutated)
                schema_errors = list(schema_only.iter_errors(mutated))
                if label == "invalid-normalizer-enum":
                    self.assertTrue(schema_errors)
                else:
                    self.assertFalse(
                        schema_errors,
                        f"{label}: bare suite.schema.json unexpectedly rejected mutation",
                    )
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "suite.json"
                    path.write_text(
                        json.dumps(mutated, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaises(residual.ResidualSuiteValidationError):
                        residual.validate_suite_path(path)

    def test_fixture_and_source_references_are_locked(self) -> None:
        expected = {
            "control.lcovrc": "52ae4f1a03b9eeb76181421e2fdd07df004ba23bccafad30cf8d8f12cfb7671c",
            "input.info": "a854b67fff921b6bfb53a8a2a8349b90f93a676de555682ab235d50b1fa6e45d",
            "input2.info": "e41be369da6cc87c54858aa659055549e7c3130bba21be3f25b84f2ee38ecc32",
            "missing.info": "a43e61e8f61c1a58c3f71267365d64c5ae3624e684920b3c0f1bc8804a0a8e3f",
            "oracle-observations.json": "0b981f99b44123ebd88312978dd43677720efbeecbde910308918f4377efe60f",
            "source.c": "dc9944dd90165fdc7fc2a2fef68bb7800015816395b0b5e2d5e93b236d60620f",
        }
        self.assertEqual(self.fixture_hashes, expected)
        self.assertIn("SF:/work/missing_source.c", (FIXTURE / "missing.info").read_text())
        self.assertIn("TN:second_case", (FIXTURE / "input2.info").read_text())
        self.assertTrue(UPSTREAM.is_dir())
        for case_id, meta in CANONICAL_CASES.items():
            if case_id == CONTROL:
                continue
            plan = self.plans[meta["plan_id"]]
            refs = {(item["kind"], item["path"], item["line"]): item for item in plan["source_references"]}
            self.assertEqual(set(refs), set(meta["references"]))
            self.assertEqual(list(refs), sorted(refs, key=lambda item: (item[1], item[2], item[0])))
            for (_kind, path, line), reference in refs.items():
                text = (UPSTREAM / path).read_text(encoding="utf-8").splitlines()[line - 1]
                self.assertEqual(reference["text"], text, f"{case_id}:{path}:{line}")

    def test_plans_and_bindings_are_target_bound(self) -> None:
        bindings = {item["id"]: item for item in json.loads(PLAN_BINDINGS.read_text())["primary_plans"]}
        for case_id, meta in CANONICAL_CASES.items():
            if case_id == CONTROL:
                continue
            plan_id = meta["plan_id"]
            plan = self.plans[plan_id]
            self.assertEqual(plan["review_status"], "reviewed")
            self.assertEqual(plan["evidence_status"], "planned")
            self.assertEqual(plan["evidence"], [])
            expected_cases = sorted(
                [
                    {"suite_id": SUITE_ID, "case_id": CONTROL},
                    {"suite_id": SUITE_ID, "case_id": case_id},
                ],
                key=lambda item: item["case_id"],
            )
            self.assertEqual(plan["suite_cases"], expected_cases)
            self.assertEqual(bindings[plan_id]["boundary_form"], meta["boundary"])
            tree = self.obs_by_id[case_id]["reference_run"]["file_tree_sha256"]
            self.assertIn(tree, plan["description"])
            self.assertIn("no Ferricov product evidence", plan["description"])
            if case_id == f"{SUITE_ID}-multi":
                self.assertIn("explicit multi-file positional aggregation", plan["description"])
                self.assertIn("not shell/glob wildcards", plan["description"])
                self.assertIn("remain separate M0 gaps", plan["description"])
                self.assertNotIn("wildcard expansion", plan["description"].lower())

    def test_oracle_observation_manifest_is_canonical_and_complete(self) -> None:
        raw = OBSERVATIONS_PATH.read_bytes()
        document = json.loads(raw.decode("utf-8"))
        self.assertEqual(
            raw,
            (json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n").encode(),
        )
        self.assertEqual(document["suite_id"], SUITE_ID)
        self.assertIs(document["product_compatibility_evidence"], False)
        self.assertEqual(document["launcher"]["image"], IMAGE)
        self.assertEqual(
            [item["case_id"] for item in document["cases"]],
            list(CANONICAL_CASES),
        )
        for item in document["cases"]:
            self.assertEqual(item["status"], "observed")
            self.assertIs(item["product_compatibility_evidence"], False)
            self.assertEqual(item["effective_environment_variables"], ENVIRONMENT)
            self.assertEqual(item["oracle_identity"]["container_image_sha256"], IMAGE)
            self.assertEqual(item["reverse_run"]["exit_code"], 23)
            self.assertEqual(item["reference_run"]["exit_code"], 0)
            self.assertEqual(item["comparison_contract"], residual.EXACT_COMPARISONS)
        trees = {item["reference_run"]["file_tree_sha256"] for item in document["cases"]}
        self.assertEqual(len(trees), 4)

    def test_review_table_projects_observation_manifest(self) -> None:
        review = REVIEW.read_text(encoding="utf-8")
        self.assertIn("reference/output characterization", " ".join(review.split()))
        self.assertIn("no Ferricov candidate was run", review)
        self.assertIn("explicit multi-file positional aggregation", review)
        self.assertIn("glob expansion", review.lower())
        self.assertIn("m0-genhtml-cli-residual-planning-wave-controller-review.md", review)
        self.assertTrue(CONTROLLER_REVIEW.is_file())
        labels = {
            CONTROL: "control",
            f"{SUITE_ID}-preserve": "preserve",
            f"{SUITE_ID}-synthesize-missing": "synthesize-missing",
            f"{SUITE_ID}-multi": "multi",
        }
        for case_id, item in self.obs_by_id.items():
            run = item["reference_run"]
            prefix = f"| {labels[case_id]} |"
            rows = [
                line
                for line in review.splitlines()
                if line.startswith(prefix) and run["file_tree_sha256"] in line
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
                self.assertIn(str(run[key]), row, f"{case_id}:{key}")
            self.assertIn("| 0 | 23 |", row)

    def test_launchers_are_locked(self) -> None:
        self.assertEqual(
            hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
            "3d47df2d0ee4bf1df443687f36799d9d5ecb73a424a836a1a469b9390f97f8c3",
        )
        self.assertEqual(
            hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
            "dbf332683768c480e68b51ea6c7b25bc5b4e9d30af2b7753a0dc8550b6e08593",
        )
        reference = json.loads(REFERENCE.read_text())
        candidate = json.loads(CANDIDATE.read_text())
        for launcher in (reference, candidate):
            self.assertEqual(launcher["runtime"], {"kind": "docker_image", "image": IMAGE})
            self.assertEqual(launcher["environment_variables"], ENVIRONMENT)
            self.assertEqual(launcher["environment"]["image"], IMAGE)
        self.assertEqual(reference["program"], "{command}")
        self.assertEqual(candidate["program"], "sh")
        self.assertEqual(candidate["arguments"], ["-c", REVERSE_COMMAND, "sh", "{command}"])

    def test_binding_mutation_is_rejected(self) -> None:
        contract = json.loads((ROOT / "compat/behavior/contract.json").read_text())
        mutated = copy.deepcopy(contract)
        plan = next(
            item
            for item in mutated["case_groups"]
            if item["id"] == "case.acceptance.command.genhtml.option.preserve"
        )
        plan["description"] = plan["description"].replace("--preserve", "--preserve-mutated", 1)
        with self.assertRaises(ValidationError):
            validate_plan_bindings(ROOT, mutated)


if __name__ == "__main__":
    unittest.main()
