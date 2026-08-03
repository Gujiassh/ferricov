#!/usr/bin/env python3
"""Focused positive and mutation tests for the behavior contract validator."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

BEHAVIOR_DIR = Path(__file__).resolve().parent
REPO_ROOT = BEHAVIOR_DIR.parents[1]
sys.path.insert(0, str(BEHAVIOR_DIR))

from generate import (  # noqa: E402
    CONTRACT_PATH,
    FRAGMENT_SCHEMA_PATH,
    FRAGMENTS_PATH,
    INVENTORY_PATH,
    SCHEMA_PATH,
    TEST_MAP_PATH,
    GenerationError,
    calculate_totals,
    canonical_bytes,
    inventory_entries,
    load_authored_fragments,
    load_object,
    make_source_references,
    merge_fragments,
    schema_validator,
    validate_fragment_document,
)
from validate import (  # noqa: E402
    DEFAULT_UPSTREAM_ROOT,
    ValidationError,
    validate_contract,
    validate_evidence,
)


class BehaviorContractValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_path = REPO_ROOT / CONTRACT_PATH
        cls.schema_path = REPO_ROOT / SCHEMA_PATH
        cls.inventory_path = REPO_ROOT / INVENTORY_PATH
        cls.test_map_path = REPO_ROOT / TEST_MAP_PATH
        cls.fragments_path = REPO_ROOT / FRAGMENTS_PATH
        cls.fragment_schema_path = REPO_ROOT / FRAGMENT_SCHEMA_PATH
        cls.base = json.loads(cls.contract_path.read_text(encoding="utf-8"))
        cls.inventory = json.loads(cls.inventory_path.read_text(encoding="utf-8"))
        cls.test_map = json.loads(cls.test_map_path.read_text(encoding="utf-8"))
        main_schema = load_object(cls.schema_path, "main schema")
        fragment_schema = load_object(cls.fragment_schema_path, "fragment schema")
        _, cls.fragment_validator = schema_validator(main_schema, fragment_schema)
        cls.authored_fragments = load_authored_fragments(
            cls.fragments_path,
            cls.fragment_validator,
        )
        cls.public_ids = {
            item["entry"]["id"]
            for item in inventory_entries(cls.inventory)
            if item["entry"]["classification"] == "public"
            and item["entry"]["applicability"] != "not_applicable"
        }

    def validate_path(
        self,
        contract_path: Path,
        *,
        inventory_path: Path | None = None,
    ):
        return validate_contract(
            repo_root=REPO_ROOT,
            upstream_root=DEFAULT_UPSTREAM_ROOT,
            contract_path=contract_path,
            schema_path=self.schema_path,
            inventory_path=inventory_path or self.inventory_path,
            test_map_path=self.test_map_path,
            check_regeneration=False,
        )

    def write_contract(self, directory: Path, value: dict[str, Any]) -> Path:
        path = directory / "contract.json"
        path.write_bytes(canonical_bytes(value))
        return path

    def mutate(
        self,
        change: Callable[[dict[str, Any]], None],
        *,
        recompute_totals: bool = False,
    ) -> ValidationError:
        value = copy.deepcopy(self.base)
        change(value)
        if recompute_totals:
            value["totals"] = calculate_totals(value, self.public_ids)
        with tempfile.TemporaryDirectory(prefix="ferricov-behavior-mutation-") as temp:
            path = self.write_contract(Path(temp), value)
            with self.assertRaises(ValidationError) as raised:
                self.validate_path(path)
        return raised.exception

    @staticmethod
    def generated_case(contract: dict[str, Any]) -> dict[str, Any]:
        interaction_members = {
            member["id"]
            for group in contract["interaction_groups"]
            for member in group["members"]
        }
        return next(
            case
            for case in contract["case_groups"]
            if case["origin"] == "generated_skeleton"
            and case["targets"][0]["id"] not in interaction_members
        )

    @staticmethod
    def make_reviewed(case: dict[str, Any]) -> None:
        case["origin"] = "manually_curated"
        case["review_status"] = "reviewed"
        case["description"] = (
            "Manually reviewed planning group used only by a validator mutation test; "
            "it carries no real compatibility evidence."
        )
        case["behavior_groups"] = ["lcov.startup"]
        case["applicability"] = {
            "status": "all_supported_environments",
            "conditions": [],
        }

    @staticmethod
    def evidence_fixture() -> tuple[
        dict[str, Any],
        dict[str, Any],
        dict[tuple[str, str], dict[str, Any]],
    ]:
        suite_id = "m0-cli-contract-core"
        case_id = "m0-core-lcov-version"
        result_path = "compat/results/m0-core-lcov-version.json"
        suite_case = {
            "surface": "cli",
            "command": "lcov",
            "arguments": ["--version"],
            "fixture": None,
            "comparisons": [
                {"dimension": "exit", "normalizer": "exact-v1"},
            ],
        }
        contract_case = {
            "id": "case.test.evidence-binding",
            "suite_cases": [{"suite_id": suite_id, "case_id": case_id}],
            "evidence_status": "pass",
            "evidence": [
                {
                    "suite_id": suite_id,
                    "case_id": case_id,
                    "result_path": result_path,
                    "outcome": "pass",
                }
            ],
        }
        empty_digest = hashlib.sha256(b"").hexdigest()

        def run(role: str) -> dict[str, Any]:
            return {
                "exit_code": 0,
                "signal": None,
                "stdout_artifact": f"{role}/stdout.bin",
                "stderr_artifact": f"{role}/stderr.bin",
                "file_tree_artifact": f"{role}/file-tree.json",
                "stdout_sha256": empty_digest,
                "stderr_sha256": empty_digest,
                "file_tree_sha256": empty_digest,
                "stdout_bytes": 0,
                "stderr_bytes": 0,
                "file_tree_bytes": 0,
                "timeout": {
                    "applied_seconds": 1,
                    "expired": False,
                    "termination_signal_sent": None,
                    "escalation_signal_sent": None,
                },
                "cleanup": {
                    "direct_child_reaped": True,
                    "process_group_empty": True,
                    "container_absent": None,
                },
                "metrics": {
                    "wall_seconds": 0,
                    "user_cpu_seconds": 0,
                    "system_cpu_seconds": 0,
                    "peak_rss_bytes": 0,
                    "output_bytes": 0,
                    "output_files": 0,
                },
            }

        reference_identity = {
            "kind": "local_executable",
            "executable_sha256": f"sha256:{'0' * 64}",
            "container_image_sha256": None,
        }
        candidate_identity = {
            "kind": "local_executable",
            "executable_sha256": f"sha256:{'1' * 64}",
            "container_image_sha256": None,
        }
        result = {
            "schema_version": 1,
            "suite_id": suite_id,
            "case_id": case_id,
            "evidence_scope": "compatibility",
            "upstream_commit": "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
            "surface": suite_case["surface"],
            "command": suite_case["command"],
            "arguments": suite_case["arguments"],
            "fixture": suite_case["fixture"],
            "environment": {
                "image": "unit-test",
                "operating_system": "linux",
                "architecture": "x86_64",
            },
            "effective_environment_variables": {},
            "implementation_identities": {
                "reference": reference_identity,
                "candidate": candidate_identity,
            },
            "runs": {
                "reference": run("reference"),
                "candidate": run("candidate"),
            },
            "comparisons": [
                {
                    "dimension": "exit",
                    "normalizer": "exact-v1",
                    "status": "pass",
                    "evidence": ["reference exit status", "candidate exit status"],
                    "artifacts": [],
                    "details": None,
                }
            ],
            "overall_status": "pass",
        }
        return contract_case, result, {(suite_id, case_id): suite_case}

    @staticmethod
    def validate_evidence_fixture(
        directory: Path,
        contract_case: dict[str, Any],
        result: dict[str, Any] | None,
        suite_cases: dict[tuple[str, str], dict[str, Any]],
        after_write: Callable[[Path], None] | None = None,
    ) -> None:
        schema_target = directory / "compat/schema/differential-result.schema.json"
        schema_target.parent.mkdir(parents=True)
        schema_target.write_bytes(
            (REPO_ROOT / "compat/schema/differential-result.schema.json").read_bytes()
        )
        if result is not None:
            result_target = directory / contract_case["evidence"][0]["result_path"]
            result_target.parent.mkdir(parents=True)
            for run in result["runs"].values():
                for artifact in ("stdout", "stderr", "file_tree"):
                    relative = run[f"{artifact}_artifact"]
                    relative_path = Path(relative)
                    if relative and not relative_path.is_absolute() and ".." not in relative_path.parts:
                        artifact_path = result_target.parent / relative_path
                        artifact_path.parent.mkdir(parents=True, exist_ok=True)
                        artifact_path.write_bytes(b"")
            result_target.write_bytes(canonical_bytes(result))
            if after_write is not None:
                after_write(result_target.parent)
        validate_evidence(directory, contract_case, suite_cases)

    def test_current_contract_passes_with_honest_gaps(self) -> None:
        report = self.validate_path(self.contract_path)
        self.assertEqual(report.public_entries, len(self.public_ids))
        self.assertEqual(report.primary_case_coverage, len(self.public_ids))
        self.assertEqual(
            report.reviewed_primary_coverage,
            self.base["totals"]["reviewed_primary_coverage"],
        )
        self.assertEqual(
            len(report.readiness_gaps),
            self.base["totals"]["uncovered_public_entries"]
            + self.base["totals"]["required_interaction_domains"]
            - self.base["totals"]["reviewed_interaction_domains"],
        )

    def test_m0_cli_primary_reviews_remain_planning_only(self) -> None:
        fragment_ids = {
            "authored.m0-cli-argparse-primary",
            "authored.m0-cli-direct-getopt-primary",
            "authored.m0-cli-shared-getopt-primary",
        }
        cases = [
            case
            for _, fragment in self.authored_fragments
            if fragment["fragment_id"] in fragment_ids
            for case in fragment["case_groups"]
        ]
        self.assertEqual(len(cases), 40)
        self.assertEqual(sum(len(case["suite_cases"]) for case in cases), 154)
        self.assertTrue(all(case["review_status"] == "reviewed" for case in cases))
        self.assertTrue(all(case["evidence_status"] == "planned" for case in cases))
        self.assertTrue(all(case["evidence"] == [] for case in cases))

        aggregate = {case["id"]: case for case in self.base["case_groups"]}
        self.assertTrue(all(aggregate[case["id"]] == case for case in cases))

    def test_m0_config_primary_reviews_remain_planning_only(self) -> None:
        fragment = next(
            fragment
            for _, fragment in self.authored_fragments
            if fragment["fragment_id"] == "authored.m0-config-primary"
        )
        cases = fragment["case_groups"]
        self.assertEqual(len(cases), 8)
        self.assertEqual(sum(len(case["suite_cases"]) for case in cases), 67)
        self.assertEqual(
            {case["targets"][0]["id"] for case in cases},
            {
                "command.lcov.option.branch-coverage",
                "command.lcov.option.config-file",
                "command.lcov.option.ignore-errors",
                "command.lcov.option.no-branch-coverage",
                "command.lcov.option.rc",
                "command.lcov.option.summary",
                "lcovrc.branch-coverage",
                "lcovrc.config-file",
            },
        )
        self.assertTrue(all(case["surface"] == "config" for case in cases))
        self.assertTrue(all(case["review_status"] == "reviewed" for case in cases))
        self.assertTrue(all(case["evidence_status"] == "planned" for case in cases))
        self.assertTrue(all(case["evidence"] == [] for case in cases))

        aggregate = {case["id"]: case for case in self.base["case_groups"]}
        self.assertTrue(all(aggregate[case["id"]] == case for case in cases))
        self.assertEqual(self.base["totals"]["reviewed_primary_coverage"], 90)
        self.assertEqual(self.base["totals"]["uncovered_public_entries"], 441)

    def test_m0_small_cli_primary_reviews_remain_planning_only(self) -> None:
        fragment = next(
            fragment
            for _, fragment in self.authored_fragments
            if fragment["fragment_id"] == "authored.m0-small-cli-primary"
        )
        expected_targets = {
            "command.genpng.option.dark-mode",
            "command.genpng.option.output-filename",
            "command.genpng.option.tab-size",
            "command.genpng.option.width",
            "command.genpng.positional.sourcefile",
            "command.gendesc.option.output-filename",
            "command.py2lcov.option.cmd",
            "command.py2lcov.option.exclude",
            "command.py2lcov.option.input",
            "command.py2lcov.option.output",
            "command.py2lcov.option.tabwidth",
            "command.py2lcov.option.test-name",
            "command.xml2lcov.option.checksum",
            "command.xml2lcov.option.exclude",
            "command.xml2lcov.option.keep-going",
            "command.xml2lcov.option.output",
            "command.xml2lcov.option.test-name",
        }
        cases = fragment["case_groups"]
        self.assertEqual(len(cases), len(expected_targets))
        self.assertEqual(
            {case["targets"][0]["id"] for case in cases},
            expected_targets,
        )
        self.assertTrue(all(case["surface"] == "cli" for case in cases))
        self.assertTrue(all(case["origin"] == "manually_curated" for case in cases))
        self.assertTrue(all(case["review_status"] == "reviewed" for case in cases))
        self.assertTrue(all(case["evidence_status"] == "none" for case in cases))
        self.assertTrue(all(case["evidence"] == [] for case in cases))
        self.assertTrue(all(case["suite_cases"] == [] for case in cases))

        inventory_by_id = {
            item["entry"]["id"]: item["entry"]
            for item in inventory_entries(self.inventory)
        }
        self.assertEqual(
            {
                case["targets"][0]["id"]: case["source_references"]
                for case in cases
            },
            {
                target: make_source_references(inventory_by_id[target])
                for target in expected_targets
            },
        )

        aggregate = {case["id"]: case for case in self.base["case_groups"]}
        self.assertTrue(all(aggregate[case["id"]] == case for case in cases))

    def test_m0_tracefile_cli_primary_reviews_remain_reference_only(self) -> None:
        fragment = next(
            fragment
            for _, fragment in self.authored_fragments
            if fragment["fragment_id"] == "authored.m0-tracefile-cli-primary"
        )
        cases = fragment["case_groups"]
        expected_targets = {
            "command.lcov.option.add-tracefile": {
                "tests/genhtml/function/function.sh",
                "tests/lcov/add/prune.sh",
                "tests/lcov/add/track.sh",
                "tests/lcov/format/format.sh",
            },
            "command.lcov.option.mcdc-coverage": {
                "tests/lcov/merge/merge.sh",
            },
            "command.lcov.option.no-function-coverage": set(),
            "command.lcov.option.output-file": {
                "tests/genhtml/function/function.sh",
                "tests/lcov/add/prune.sh",
                "tests/lcov/add/track.sh",
                "tests/lcov/format/format.sh",
            },
        }
        self.assertEqual(len(cases), 4)
        self.assertEqual(
            {case["targets"][0]["id"]: set(case["upstream_tests"]) for case in cases},
            expected_targets,
        )
        self.assertTrue(all(case["origin"] == "manually_curated" for case in cases))
        self.assertTrue(all(case["review_status"] == "reviewed" for case in cases))
        self.assertTrue(all(case["evidence_status"] == "none" for case in cases))
        self.assertTrue(all(case["evidence"] == [] for case in cases))
        self.assertTrue(all(case["suite_cases"] == [] for case in cases))

        aggregate = {case["id"]: case for case in self.base["case_groups"]}
        self.assertTrue(all(aggregate[case["id"]] == case for case in cases))
        self.assertEqual(self.base["totals"]["reviewed_primary_coverage"], 90)
        self.assertEqual(self.base["totals"]["uncovered_public_entries"], 441)

        inventory_by_id = {
            item["entry"]["id"]: item["entry"]
            for item in inventory_entries(self.inventory)
        }
        expected_source_references = {
            target: make_source_references(inventory_by_id[target])
            for target in expected_targets
        }
        self.assertTrue(
            all(
                inventory_by_id[target]["review_status"] == "reviewed"
                for target in expected_targets
            )
        )

        def require_exact_inventory_sources(values: list[dict[str, Any]]) -> None:
            for value in values:
                target = value["targets"][0]["id"]
                if value["source_references"] != expected_source_references[target]:
                    raise AssertionError(
                        f"{target}: authored source references differ from reviewed inventory"
                    )

        source_mutations = (
            lambda value: value["source_references"].pop(),
            lambda value: value["source_references"][0].__setitem__(
                "line", value["source_references"][0]["line"] + 1
            ),
        )
        for mutation in source_mutations:
            with self.subTest(source_mutation=mutation):
                mutated = copy.deepcopy(cases)
                mutation(mutated[0])
                with self.assertRaises(AssertionError):
                    require_exact_inventory_sources(mutated)
        require_exact_inventory_sources(cases)

        def require_reference_only(values: list[dict[str, Any]]) -> None:
            for value in values:
                if value["evidence_status"] != "none":
                    raise AssertionError("authored tracefile CLI plan promoted evidence status")
                if value["evidence"]:
                    raise AssertionError("authored tracefile CLI plan gained product evidence")
                if value["suite_cases"]:
                    raise AssertionError("authored tracefile CLI plan gained a suite binding")

        mutations = (
            lambda value: value.__setitem__("evidence_status", "planned"),
            lambda value: value["evidence"].append({"unexpected": "product-evidence"}),
            lambda value: value["suite_cases"].append(
                {"suite_id": "m0-cli-contract-core", "case_id": "m0-core-lcov-version"}
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                mutated = copy.deepcopy(cases)
                mutation(mutated[0])
                with self.assertRaises(AssertionError):
                    require_reference_only(mutated)
        require_reference_only(cases)

    def test_m0_tracefile_cli_primary_planning_sources_are_exact(self) -> None:
        oracle_source = json.loads(
            (REPO_ROOT / "compat/fixtures/m0-tracefiles/oracle-cases.json").read_text(
                encoding="utf-8"
            )
        )
        tracefile_contract = json.loads(
            (REPO_ROOT / "compat/tracefile/v2.5.json").read_text(encoding="utf-8")
        )
        diagnostics_contract = json.loads(
            (REPO_ROOT / "compat/diagnostics/v2.5.json").read_text(encoding="utf-8")
        )
        oracle_by_id = {case["id"]: case for case in oracle_source["cases"]}
        tracefile_by_id = {
            case["id"]: case for case in tracefile_contract["oracle_cases"]
        }
        canonical_ids = {
            "bytes-crlf.canonical",
            "bytes-no-final-newline.canonical",
            "bytes-non-utf8.canonical",
            "bytes-nul-accepted.canonical",
            "current-all-records.canonical",
            "legacy.canonical",
            "numeric-boundary.canonical",
            "permissive-prefix.canonical",
        }
        state_canonical_ids = {
            "state-late-tn-mcdc.canonical",
            "state-cross-sf-mcdc-success.canonical",
        }
        self.assertEqual(
            {
                identifier
                for identifier, case in tracefile_by_id.items()
                if case["kind"] == "canonical_rewrite"
            },
            canonical_ids | state_canonical_ids,
        )
        for identifier in canonical_ids:
            with self.subTest(oracle_case=identifier):
                source = oracle_by_id[identifier]
                retained = tracefile_by_id[identifier]
                self.assertIn("--add-tracefile", source["argv"])
                self.assertIn("--output-file", source["argv"])
                self.assertEqual(source["output_file"], "output.info")
                self.assertEqual(source["expected_exit"], 0)
                self.assertEqual(retained["evidence_status"], "oracle_reference")
                self.assertEqual(retained["exit_status"], 0)
                self.assertIsNotNone(retained["output_sha256"])
        self.assertEqual(
            {
                identifier
                for identifier in canonical_ids
                if "--no-function-coverage" in oracle_by_id[identifier]["argv"]
            },
            {
                "bytes-crlf.canonical",
                "bytes-no-final-newline.canonical",
                "bytes-nul-accepted.canonical",
                "numeric-boundary.canonical",
                "permissive-prefix.canonical",
            },
        )
        self.assertEqual(
            {
                identifier
                for identifier in canonical_ids
                if "--mcdc-coverage" in oracle_by_id[identifier]["argv"]
            },
            {"bytes-non-utf8.canonical", "current-all-records.canonical"},
        )

        recovery_ids = {
            "malformed-da.ignore-format",
            "malformed-tn.ignore-format",
            "malformed-ver.ignore-format",
            "numeric-excessive.ignore-excessive",
            "numeric-malformed-exponent.ignore-format",
            "numeric-negative.ignore-negative",
            "numeric-nonnumeric.ignore-format",
            "numeric-zero-line.ignore-format",
        }
        diagnostics_by_id = {
            observation["id"]: observation
            for observation in diagnostics_contract["oracle_observations"]
        }
        for identifier in recovery_ids:
            with self.subTest(diagnostic_reference=identifier):
                source = oracle_by_id[identifier]
                retained = diagnostics_by_id[f"tracefile:{identifier}"]
                self.assertIn("--add-tracefile", source["argv"])
                self.assertIn("--output-file", source["argv"])
                self.assertIn("--no-function-coverage", source["argv"])
                self.assertEqual(source["expected_exit"], 0)
                self.assertEqual(retained["exit_status"], 0)
                self.assertIsNotNone(retained["output_sha256"])
        self.assertFalse(tracefile_contract["product_compatibility_evidence"])
        self.assertEqual(
            diagnostics_contract["oracle_observation_evidence_status"],
            "oracle_reference",
        )
        self.assertEqual(
            diagnostics_contract["oracle_observation_product_evidence"], []
        )
        self.assertFalse(diagnostics_contract["product_compatibility_evidence"])

        linked_tests = {
            test
            for case in next(
                fragment
                for _, fragment in self.authored_fragments
                if fragment["fragment_id"] == "authored.m0-tracefile-cli-primary"
            )["case_groups"]
            for test in case["upstream_tests"]
        }
        tests_by_path = {entry["source"]: entry for entry in self.test_map["entries"]}
        self.assertEqual(
            linked_tests,
            {
                "tests/genhtml/function/function.sh",
                "tests/lcov/add/prune.sh",
                "tests/lcov/add/track.sh",
                "tests/lcov/format/format.sh",
                "tests/lcov/merge/merge.sh",
            },
        )
        for test_path in linked_tests:
            with self.subTest(upstream_test=test_path):
                entry = tests_by_path[test_path]
                self.assertEqual(entry["review_status"], "reviewed")
                self.assertEqual(entry["classification"], "public_behavior")
                self.assertIn(
                    entry["evidence_scope"],
                    {"direct_public_behavior", "indirect_public_behavior"},
                )

    def test_m0_ready_cli_rejects_honest_debt(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(BEHAVIOR_DIR / "validate.py"),
                "--mode",
                "m0-ready",
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("m0-ready validation failed", completed.stderr)
        self.assertIn("has no reviewed primary case group", completed.stderr)

    def test_generated_skeletons_do_not_inherit_inventory_review_status(self) -> None:
        reviewed_public_ids = {
            item["entry"]["id"]
            for item in inventory_entries(self.inventory)
            if item["entry"]["classification"] == "public"
            and item["entry"]["applicability"] != "not_applicable"
            and item["entry"]["review_status"] == "reviewed"
        }
        skeletons = [
            case
            for case in self.base["case_groups"]
            if case["origin"] == "generated_skeleton"
            and case["targets"][0]["id"] in reviewed_public_ids
        ]
        self.assertTrue(skeletons)
        self.assertTrue(all(case["review_status"] == "unreviewed" for case in skeletons))
        self.assertTrue(all(case["evidence_status"] == "none" for case in skeletons))

    def test_inventory_relationship_arrays_are_not_behavior_inputs(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        entry = inventory_entries(inventory)[0]["entry"]
        entry["behavior_groups"] = ["ignored.inventory.behavior"]
        entry["interaction_groups"] = ["ignored.inventory.interaction"]
        entry["planned_cases"] = ["ignored.inventory.case"]
        with tempfile.TemporaryDirectory(prefix="ferricov-inventory-ownership-") as temp:
            inventory_path = Path(temp) / "inventory.json"
            inventory_path.write_bytes(canonical_bytes(inventory))
            report = self.validate_path(
                self.contract_path,
                inventory_path=inventory_path,
            )
        self.assertEqual(report.primary_case_coverage, len(self.public_ids))

    def test_all_authoring_fragments_are_small_and_canonical(self) -> None:
        paths = sorted(self.fragments_path.rglob("*.json"))
        self.assertTrue(paths)
        for path in paths:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(path.read_bytes(), canonical_bytes(value), path)
            self.assertLessEqual(path.read_bytes().count(b"\n"), 2_000, path)

    def test_deterministic_regeneration_is_stable(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(BEHAVIOR_DIR / "generate.py"), "--check"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertIn("stable", completed.stdout)

    def test_fragment_schema_rejects_unknown_field(self) -> None:
        fragment = copy.deepcopy(self.authored_fragments[0][1])
        fragment["unexpected"] = True
        with self.assertRaises(GenerationError) as raised:
            validate_fragment_document(
                fragment,
                "mutated fragment",
                self.fragment_validator,
                expected_type="authored",
            )
        self.assertIn("Additional properties", str(raised.exception))

    def test_fragment_local_order_is_rejected(self) -> None:
        fragment = copy.deepcopy(
            next(value for _, value in self.authored_fragments if len(value["case_groups"]) > 1)
        )
        fragment["case_groups"].reverse()
        with self.assertRaises(GenerationError) as raised:
            validate_fragment_document(
                fragment,
                "mutated fragment",
                self.fragment_validator,
                expected_type="authored",
            )
        self.assertIn("must be sorted by id", str(raised.exception))

    def test_fragment_global_duplicate_id_is_rejected(self) -> None:
        fragments = [copy.deepcopy(value) for _, value in self.authored_fragments]
        duplicate = copy.deepcopy(fragments[0]["subjects"][0])
        fragments[1]["subjects"].append(duplicate)
        fragments[1]["subjects"].sort(key=lambda item: item["id"])
        with self.assertRaises(GenerationError) as raised:
            merge_fragments(self.inventory, fragments)
        self.assertIn("merged subjects ids must be unique", str(raised.exception))

    def test_direct_canonical_edit_fails_byte_stable_check(self) -> None:
        mutated = copy.deepcopy(self.base)
        mutated["review_policy"] += " altered"
        with tempfile.TemporaryDirectory(prefix="ferricov-canonical-drift-") as temp:
            path = self.write_contract(Path(temp), mutated)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BEHAVIOR_DIR / "generate.py"),
                    "--output",
                    str(path),
                    "--check",
                ],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("differs from deterministic fragment merge", completed.stderr)

    def test_schema_rejects_unknown_root_field(self) -> None:
        error = self.mutate(lambda contract: contract.__setitem__("unexpected", True))
        self.assertIn("Additional properties", str(error))

    def test_missing_public_skeleton_is_rejected(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            target = self.generated_case(contract)["targets"][0]["id"]
            contract["case_groups"] = [
                case
                for case in contract["case_groups"]
                if all(item["id"] != target for item in case["targets"])
            ]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("public entries without any primary case group", str(error))

    def test_generated_case_drift_is_rejected(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            self.generated_case(contract)["description"] += " altered"

        error = self.mutate(change)
        self.assertIn("generated case skeleton drift", str(error))

    def test_unknown_target_is_rejected(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            case = self.generated_case(contract)
            case["origin"] = "manually_curated"
            case["targets"] = [{"id": "UNKNOWN-SUBJECT", "role": "primary"}]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("unknown target", str(error))

    def test_behavior_registry_import_drift_is_rejected(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            contract["behavior_groups"][0]["description"] += " altered"

        error = self.mutate(change)
        self.assertIn("exactly import", str(error))

    def test_reviewed_subject_source_drift_is_rejected(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            contract["subjects"][0]["source_references"][0]["text"] += " altered"

        error = self.mutate(change)
        self.assertIn("source text mismatch", str(error))

    def test_missing_reviewed_case_import_is_rejected(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            contract["case_groups"] = [
                case
                for case in contract["case_groups"]
                if case["origin"] != "reviewed_import" or case["id"] != "case.audit.CB-CONTEXT"
            ]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("every reviewed-import subject", str(error))

    def test_internal_upstream_test_cannot_prove_public_semantics(self) -> None:
        internal = next(
            entry["source"]
            for entry in self.test_map["entries"]
            if entry["classification"] == "internal_test_infrastructure"
        )

        def change(contract: dict[str, Any]) -> None:
            case = self.generated_case(contract)
            self.make_reviewed(case)
            case["upstream_tests"] = [internal]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("cannot prove public semantics", str(error))

    def test_evidence_requires_integral_result_artifacts(self) -> None:
        mutations = (
            (
                lambda result: result["runs"]["reference"].__setitem__("stdout_artifact", ""),
                "JSON Schema rejected differential result",
            ),
            (
                lambda result: result["runs"]["reference"].__setitem__("stdout_sha256", "f" * 64),
                "reference stdout artifact hash mismatch",
            ),
            (
                lambda result: result["runs"]["reference"].__setitem__("stdout_bytes", 1),
                "reference stdout artifact size mismatch",
            ),
            (
                lambda result: result["comparisons"][0].__setitem__("evidence", []),
                "comparison exit lacks evidence",
            ),
        )
        for mutation, message in mutations:
            with self.subTest(message=message):
                contract_case, result, suite_cases = self.evidence_fixture()
                mutation(result)
                with tempfile.TemporaryDirectory(prefix="ferricov-evidence-artifacts-") as temp:
                    with self.assertRaises(ValidationError) as raised:
                        self.validate_evidence_fixture(
                            Path(temp),
                            contract_case,
                            result,
                            suite_cases,
                        )
                self.assertIn(message, str(raised.exception))

    def test_evidence_rejects_missing_and_symlink_artifacts(self) -> None:
        def remove_stdout(case_root: Path) -> None:
            (case_root / "reference/stdout.bin").unlink()

        def replace_stdout_with_symlink(case_root: Path) -> None:
            artifact = case_root / "reference/stdout.bin"
            artifact.unlink()
            artifact.symlink_to(case_root / "reference/stderr.bin")

        for after_write, message in (
            (remove_stdout, "reference stdout artifact does not exist"),
            (replace_stdout_with_symlink, "reference stdout artifact must not be a symlink"),
        ):
            with self.subTest(message=message):
                contract_case, result, suite_cases = self.evidence_fixture()
                with tempfile.TemporaryDirectory(prefix="ferricov-evidence-files-") as temp:
                    with self.assertRaises(ValidationError) as raised:
                        self.validate_evidence_fixture(
                            Path(temp),
                            contract_case,
                            result,
                            suite_cases,
                            after_write,
                        )
                self.assertIn(message, str(raised.exception))

    def test_evidence_rejects_artifact_parent_symlink_escape(self) -> None:
        contract_case, result, suite_cases = self.evidence_fixture()

        def replace_parent_with_symlink(case_root: Path) -> None:
            reference = case_root / "reference"
            for artifact in reference.iterdir():
                artifact.unlink()
            reference.rmdir()
            outside = case_root.parent / "outside-artifacts"
            outside.mkdir()
            for name in ("stdout.bin", "stderr.bin", "file-tree.json"):
                (outside / name).write_bytes(b"")
            reference.symlink_to(outside, target_is_directory=True)

        with tempfile.TemporaryDirectory(prefix="ferricov-evidence-escape-") as temp:
            with self.assertRaises(ValidationError) as raised:
                self.validate_evidence_fixture(
                    Path(temp),
                    contract_case,
                    result,
                    suite_cases,
                    replace_parent_with_symlink,
                )
        self.assertIn(
            "reference stdout artifact escapes result directory",
            str(raised.exception),
        )

    def test_evidence_rejects_identical_runtime_identities(self) -> None:
        contract_case, result, suite_cases = self.evidence_fixture()
        result["implementation_identities"]["candidate"] = copy.deepcopy(
            result["implementation_identities"]["reference"]
        )
        with tempfile.TemporaryDirectory(prefix="ferricov-evidence-self-compare-") as temp:
            with self.assertRaises(ValidationError) as raised:
                self.validate_evidence_fixture(
                    Path(temp),
                    contract_case,
                    result,
                    suite_cases,
                )
        self.assertIn(
            "compatibility evidence cannot compare identical runtime identity",
            str(raised.exception),
        )

    def test_evidence_requires_matching_suite_reference(self) -> None:
        contract_case, result, suite_cases = self.evidence_fixture()
        contract_case["suite_cases"] = []
        with tempfile.TemporaryDirectory(prefix="ferricov-evidence-suite-ref-") as temp:
            with self.assertRaises(ValidationError) as raised:
                self.validate_evidence_fixture(
                    Path(temp),
                    contract_case,
                    result,
                    suite_cases,
                )
        self.assertIn("evidence has no matching suite_cases reference", str(raised.exception))

    def test_result_must_match_referenced_suite_and_case_identity(self) -> None:
        for field, value, message in (
            ("suite_id", "other-suite", "result suite id mismatch"),
            ("case_id", "other-case", "result case id mismatch"),
        ):
            with self.subTest(field=field):
                contract_case, result, suite_cases = self.evidence_fixture()
                result[field] = value
                with tempfile.TemporaryDirectory(prefix="ferricov-evidence-identity-") as temp:
                    with self.assertRaises(ValidationError) as raised:
                        self.validate_evidence_fixture(
                            Path(temp),
                            contract_case,
                            result,
                            suite_cases,
                        )
                self.assertIn(message, str(raised.exception))

    def test_result_must_match_referenced_suite_execution_identity(self) -> None:
        mutations = (
            ("surface", "config"),
            ("command", "genhtml"),
            ("arguments", ["--help"]),
            ("fixture", "compat/fixtures/other"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                contract_case, result, suite_cases = self.evidence_fixture()
                result[field] = value
                with tempfile.TemporaryDirectory(prefix="ferricov-evidence-execution-") as temp:
                    with self.assertRaises(ValidationError) as raised:
                        self.validate_evidence_fixture(
                            Path(temp),
                            contract_case,
                            result,
                            suite_cases,
                        )
                self.assertIn(
                    f"result {field} does not match the referenced suite case",
                    str(raised.exception),
                )

    def test_result_comparison_dimensions_and_normalizers_are_bound(self) -> None:
        for mutation, message in (
            (
                lambda result: result["comparisons"][0].__setitem__("dimension", "stdout"),
                "result comparison dimensions do not match the referenced suite case",
            ),
            (
                lambda result: result["comparisons"][0].__setitem__("normalizer", "other-v1"),
                "result normalizer for exit does not match the referenced suite case",
            ),
        ):
            with self.subTest(message=message):
                contract_case, result, suite_cases = self.evidence_fixture()
                mutation(result)
                with tempfile.TemporaryDirectory(prefix="ferricov-evidence-comparison-") as temp:
                    with self.assertRaises(ValidationError) as raised:
                        self.validate_evidence_fixture(
                            Path(temp),
                            contract_case,
                            result,
                            suite_cases,
                        )
                self.assertIn(message, str(raised.exception))

    def test_result_outcome_must_match_evidence_outcome(self) -> None:
        contract_case, result, suite_cases = self.evidence_fixture()
        result["overall_status"] = "fail"
        result["comparisons"][0]["status"] = "fail"
        with tempfile.TemporaryDirectory(prefix="ferricov-evidence-outcome-") as temp:
            with self.assertRaises(ValidationError) as raised:
                self.validate_evidence_fixture(
                    Path(temp),
                    contract_case,
                    result,
                    suite_cases,
                )
        self.assertIn("result outcome mismatch", str(raised.exception))

    def test_pass_and_fail_require_qualifying_result_evidence(self) -> None:
        for status, message in (
            ("pass", "pass requires only passing result evidence"),
            ("fail", "fail requires failing result evidence"),
        ):
            with self.subTest(status=status):
                contract_case, _, suite_cases = self.evidence_fixture()
                contract_case["evidence_status"] = status
                contract_case["evidence"] = []
                with tempfile.TemporaryDirectory(prefix="ferricov-evidence-status-") as temp:
                    with self.assertRaises(ValidationError) as raised:
                        self.validate_evidence_fixture(
                            Path(temp),
                            contract_case,
                            None,
                            suite_cases,
                        )
                self.assertIn(message, str(raised.exception))

    def test_not_applicable_review_does_not_cover_public_entry(self) -> None:
        value = copy.deepcopy(self.base)
        case = self.generated_case(value)
        self.make_reviewed(case)
        case["applicability"] = {
            "status": "not_applicable",
            "conditions": ["Mutation proves not-applicable plans do not satisfy applicable public coverage."],
        }
        value["totals"] = calculate_totals(value, self.public_ids)
        with tempfile.TemporaryDirectory(prefix="ferricov-not-applicable-") as temp:
            path = self.write_contract(Path(temp), value)
            report = self.validate_path(path)
        self.assertEqual(
            report.reviewed_primary_coverage,
            self.base["totals"]["reviewed_primary_coverage"],
        )
        self.assertTrue(
            any(case["targets"][0]["id"] in gap for gap in report.readiness_gaps)
        )

    def test_reviewed_interaction_case_must_target_every_member(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            group = next(
                item for item in contract["interaction_groups"]
                if item["domain"] == "callback"
            )
            for existing_case in contract["case_groups"]:
                if group["id"] in existing_case["interaction_groups"]:
                    existing_case["interaction_groups"].remove(group["id"])
            planned_case = next(
                item
                for item in contract["case_groups"]
                if item["origin"] == "generated_skeleton"
                and ".option." in item["targets"][0]["id"]
            )
            option = planned_case["targets"][0]["id"]
            group["origin"] = "manually_curated"
            group["review_status"] = "reviewed"
            group["members"] = [
                {"id": value}
                for value in sorted(["CB-ANNOTATE", option])
            ]
            group["behavior_groups"] = ["genhtml.diagnostics-and-config"]
            group["planned_cases"] = [planned_case["id"]]
            self.make_reviewed(planned_case)
            planned_case["case_class"] = "interaction"
            planned_case["surface"] = "callback"
            planned_case["interaction_groups"] = [group["id"]]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("does not target every interaction member", str(error))

    def test_reviewed_case_cannot_reference_unreviewed_interaction(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            case = self.generated_case(contract)
            self.make_reviewed(case)
            group = next(
                item for item in contract["interaction_groups"]
                if item["domain"] == "option_option"
            )
            group["origin"] = "manually_curated"
            group["review_status"] = "unreviewed"
            group["planned_cases"] = [case["id"]]
            case["interaction_groups"] = [group["id"]]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("reviewed case cannot reference an unreviewed interaction", str(error))

    def test_current_critical_interactions_are_reviewed_and_semantic(self) -> None:
        groups = {
            group["domain"]: group for group in self.base["interaction_groups"]
        }
        self.assertEqual(
            set(groups),
            {"callback", "error_control", "option_config", "option_option"},
        )
        expected_members = {
            "callback": {
                "CB-ANNOTATE",
                "command.genhtml.option.annotate-script",
            },
            "error_control": {"ERR-NAMED-CONTROL", "lcovrc.stop-on-error"},
            "option_config": {
                "command.lcov.option.ignore-errors",
                "lcovrc.ignore-errors",
            },
            "option_option": {
                "command.lcov.option.ignore-errors",
                "command.lcov.option.keep-going",
            },
        }
        cases = {case["id"]: case for case in self.base["case_groups"]}
        for domain, group in groups.items():
            with self.subTest(domain=domain):
                self.assertTrue(group["critical"])
                self.assertEqual(group["origin"], "manually_curated")
                self.assertEqual(group["review_status"], "reviewed")
                self.assertEqual(
                    {member["id"] for member in group["members"]},
                    expected_members[domain],
                )
                self.assertEqual(len(group["planned_cases"]), 1)
                case = cases[group["planned_cases"][0]]
                self.assertEqual(case["case_class"], "interaction")
                self.assertEqual(case["review_status"], "reviewed")
                self.assertEqual(case["evidence_status"], "none")
                self.assertLessEqual(
                    expected_members[domain],
                    {target["id"] for target in case["targets"]},
                )

        report = self.validate_path(self.contract_path)
        self.assertEqual(len(report.readiness_gaps), 441)
        self.assertEqual(self.base["totals"]["reviewed_primary_coverage"], 90)

    def test_harness_self_test_suite_cannot_count_as_planning(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            case = self.generated_case(contract)
            self.make_reviewed(case)
            case["evidence_status"] = "planned"
            case["suite_cases"] = [
                {"suite_id": "harness-self-test", "case_id": "lcov-version"}
            ]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("harness self-test suite", str(error))

    def test_pass_status_without_result_evidence_is_rejected(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            case = self.generated_case(contract)
            self.make_reviewed(case)
            case["evidence_status"] = "pass"
            case["suite_cases"] = [
                {"suite_id": "harness-self-test", "case_id": "lcov-version"}
            ]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("JSON Schema rejected", str(error))
        self.assertIn("evidence", str(error))

    def test_option_option_member_type_guard_is_fail_closed(self) -> None:
        option = next(
            item["entry"]["id"]
            for item in inventory_entries(self.inventory)
            if item["kind"] == "option"
        )
        positional = next(
            item["entry"]["id"]
            for item in inventory_entries(self.inventory)
            if item["kind"] == "positional"
        )

        def change(contract: dict[str, Any]) -> None:
            group = next(
                item for item in contract["interaction_groups"]
                if item["domain"] == "option_option"
            )
            group["origin"] = "manually_curated"
            group["review_status"] = "reviewed"
            group["members"] = [{"id": value} for value in sorted([option, positional])]
            group["behavior_groups"] = ["lcov.startup"]
            group["planned_cases"] = [self.generated_case(contract)["id"]]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("requires at least two option members", str(error))

    def test_interaction_case_reciprocity_is_required(self) -> None:
        options = [
            item["entry"]["id"]
            for item in inventory_entries(self.inventory)
            if item["kind"] == "option"
        ][:2]

        def change(contract: dict[str, Any]) -> None:
            group = next(
                item for item in contract["interaction_groups"]
                if item["domain"] == "option_option"
            )
            group["origin"] = "manually_curated"
            group["review_status"] = "reviewed"
            group["members"] = [{"id": value} for value in sorted(options)]
            group["behavior_groups"] = ["lcov.startup"]
            group["planned_cases"] = [self.generated_case(contract)["id"]]

        error = self.mutate(change, recompute_totals=True)
        self.assertIn("are not reciprocal", str(error))

    def test_totals_are_recomputed(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            contract["totals"]["case_groups"] += 1

        error = self.mutate(change)
        self.assertIn("contract totals mismatch", str(error))

    def test_array_order_is_canonical(self) -> None:
        def change(contract: dict[str, Any]) -> None:
            contract["case_groups"].reverse()

        error = self.mutate(change)
        self.assertIn("case_groups must be sorted", str(error))


if __name__ == "__main__":
    unittest.main()
