from __future__ import annotations

import copy
import json
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


INSTALLATION_ROOT = Path(__file__).resolve().parent
UPSTREAM_ROOT = Path(
    os.environ.get(
        "LCOV_SOURCE_ROOT",
        INSTALLATION_ROOT.parents[2] / "lcov-upstream-reference",
    )
).resolve()

SPEC = importlib.util.spec_from_file_location(
    "ferricov_installation_contract",
    INSTALLATION_ROOT / "contract.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load installation contract module")
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class InstallationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        contract.validate_upstream_identity(UPSTREAM_ROOT)
        cls.generated = contract.build_document(UPSTREAM_ROOT)
        cls.committed = contract.load_json(contract.OUTPUT_PATH)

    def validate(self, document: dict[str, object]) -> None:
        contract.validate_document(document, UPSTREAM_ROOT)

    def parse_tree_lines(self, lines: list[str]) -> list[dict[str, str]]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            lock_path = Path(temporary_directory) / "installed-tree.lock"
            lock_path.write_text("\n".join(lines) + "\n", encoding="ascii")
            with mock.patch.object(contract, "TREE_LOCK", lock_path):
                return contract.parse_tree()

    def test_committed_contract_matches_generation(self) -> None:
        self.validate(self.committed)
        self.assertEqual(contract.canonical_json(self.committed), contract.canonical_json(self.generated))

    def test_unsorted_tree_paths_are_rejected(self) -> None:
        lines = contract.TREE_LOCK.read_text(encoding="ascii").splitlines()
        lines[0], lines[1] = lines[1], lines[0]
        with self.assertRaisesRegex(contract.InstallationContractError, "lexicographic order"):
            self.parse_tree_lines(lines)

    def test_tree_path_outside_prefix_is_rejected(self) -> None:
        lines = contract.TREE_LOCK.read_text(encoding="ascii").splitlines()
        fields = lines[0].split("\t")
        fields[3] = "/opt/bin/gendesc"
        lines[0] = "\t".join(fields)
        with self.assertRaisesRegex(contract.InstallationContractError, "invalid path"):
            self.parse_tree_lines(lines)

    def test_tree_parent_traversal_is_rejected(self) -> None:
        lines = contract.TREE_LOCK.read_text(encoding="ascii").splitlines()
        fields = lines[0].split("\t")
        fields[3] = "/usr/local/bin/../gendesc"
        lines[0] = "\t".join(fields)
        with self.assertRaisesRegex(contract.InstallationContractError, "invalid path"):
            self.parse_tree_lines(lines)

    def test_non_sha256_file_identity_is_rejected(self) -> None:
        lines = contract.TREE_LOCK.read_text(encoding="ascii").splitlines()
        fields = lines[0].split("\t")
        fields[2] = "0" * 63
        lines[0] = "\t".join(fields)
        with self.assertRaisesRegex(contract.InstallationContractError, "not SHA-256"):
            self.parse_tree_lines(lines)

    def test_legacy_symlink_target_drift_is_rejected(self) -> None:
        lines = contract.TREE_LOCK.read_text(encoding="ascii").splitlines()
        index = next(i for i, line in enumerate(lines) if line.startswith("symlink\t"))
        fields = lines[index].split("\t")
        fields[2] = "../share/man"
        lines[index] = "\t".join(fields)
        with self.assertRaisesRegex(contract.InstallationContractError, "legacy symlink drift"):
            self.parse_tree_lines(lines)

    def test_missing_tree_group_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["installed_tree"]["groups"].pop()
        with self.assertRaisesRegex(contract.InstallationContractError, "installed_tree"):
            self.validate(document)

    def test_tree_group_count_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["installed_tree"]["groups"][0]["entry_count"] += 1
        with self.assertRaisesRegex(contract.InstallationContractError, "installed_tree"):
            self.validate(document)

    def test_source_closure_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["source_closures"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.InstallationContractError, "source_closures"):
            self.validate(document)

    def test_tree_artifact_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["installed_tree"]["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.InstallationContractError, "installed_tree"):
            self.validate(document)

    def test_directory_entries_cannot_be_claimed(self) -> None:
        document = copy.deepcopy(self.committed)
        document["installed_tree"]["directory_entries_retained"] = True
        with self.assertRaisesRegex(contract.InstallationContractError, "installed_tree"):
            self.validate(document)

    def test_planned_case_catalog_gap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["planned_case_ids"].pop()
        with self.assertRaises(contract.InstallationContractError):
            self.validate(document)

    def test_duplicate_runtime_asset_path_is_rejected(self) -> None:
        identifier, name, kind, size, digest = contract.EXPECTED_ASSETS[0]
        del identifier, kind
        entry = {
            "path": f"html/{name}",
            "bytes": size,
            "sha256": f"sha256:{digest}",
            "status": "created",
        }
        expected = {
            asset_name: {"bytes": asset_size, "sha256": asset_digest}
            for _, asset_name, _, asset_size, asset_digest in contract.EXPECTED_ASSETS
        }
        with self.assertRaisesRegex(contract.InstallationContractError, "duplicate runtime asset path"):
            contract.observed_runtime_assets([entry, entry], "duplicate-output-tree.json", expected)

    def test_sample_output_tree_binding_is_rejected(self) -> None:
        relative = contract.ASSET_SAMPLE_PATHS[0]
        sample_path = contract.ROOT / Path(relative).with_name("sample.json")
        sample = contract.load_json(sample_path)
        sample["artifacts"]["output_tree"]["sha256"] = "sha256:" + "0" * 64
        with mock.patch.object(contract, "load_json", return_value=sample):
            with self.assertRaisesRegex(contract.InstallationContractError, "sample binding drift"):
                contract.validate_sample_metadata(relative, contract.ROOT / relative)

    def test_asset_omission_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["runtime_assets"].pop()
        with self.assertRaisesRegex(contract.InstallationContractError, "runtime_assets"):
            self.validate(document)

    def test_asset_identity_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["runtime_assets"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.InstallationContractError, "runtime_assets"):
            self.validate(document)

    def test_asset_observation_sample_metadata_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["runtime_asset_observations"][0]["sample_metadata_sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.InstallationContractError, "runtime_asset_observations"):
            self.validate(document)

    def test_asset_observation_artifact_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["runtime_asset_observations"][0]["artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.InstallationContractError, "runtime_asset_observations"):
            self.validate(document)

    def test_evidence_gap_removal_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["known_evidence_gaps"].pop()
        with self.assertRaisesRegex(contract.InstallationContractError, "known_evidence_gaps"):
            self.validate(document)

    def test_product_evidence_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["planned_case_product_evidence"] = ["not-product-evidence"]
        with self.assertRaises(contract.InstallationContractError):
            self.validate(document)

    def test_baseline_cannot_claim_evaluated_gates(self) -> None:
        document = copy.deepcopy(self.committed)
        document["benchmark_result"]["correctness_gate_status"] = "pass"
        with self.assertRaisesRegex(contract.InstallationContractError, "benchmark_result"):
            self.validate(document)

    def test_oracle_reference_cannot_be_promoted(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_observation_evidence_status"] = "product_pass"
        with self.assertRaises(contract.InstallationContractError):
            self.validate(document)

    def test_case_records_binding_is_required(self) -> None:
        document = copy.deepcopy(self.committed)
        document.pop("oracle_case_records")
        with self.assertRaises(contract.InstallationContractError):
            self.validate(document)

    def test_case_records_sha_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_case_records"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.InstallationContractError, "oracle_case_records"):
            self.validate(document)

    def test_case_summary_order_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_case_summaries"] = list(reversed(document["oracle_case_summaries"]))
        with self.assertRaisesRegex(contract.InstallationContractError, "oracle_case_summaries"):
            self.validate(document)

    def test_case_summary_facts_hash_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_case_summaries"][0]["facts_sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.InstallationContractError, "oracle_case_summaries"):
            self.validate(document)

    def test_case_record_product_evidence_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_case_records"]["product_compatibility_evidence"] = True
        with self.assertRaises(contract.InstallationContractError):
            self.validate(document)

    def test_case_records_execution_promotion_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_case_records"]["execution_status"] = "captured"
        with self.assertRaises(contract.InstallationContractError):
            self.validate(document)

    def test_independent_case_facts_hash_is_bound(self) -> None:
        records = contract.load_case_records()
        self.assertEqual(len(records["cases"]), 13)
        for case in records["cases"]:
            facts_bytes = contract.canonical_json(case["independent_facts"]).encode("ascii")
            self.assertEqual(case["facts_sha256"], contract.sha256_bytes(facts_bytes))

    def test_refreshed_case_records_hash_without_bytes_is_rejected(self) -> None:
        # Mutating only the committed binding while the artifact stays fixed must fail closed.
        document = copy.deepcopy(self.committed)
        original = document["oracle_case_records"]["sha256"]
        document["oracle_case_records"]["sha256"] = "a" * 64
        self.assertNotEqual(original, document["oracle_case_records"]["sha256"])
        with self.assertRaisesRegex(contract.InstallationContractError, "oracle_case_records"):
            self.validate(document)

    def test_case_facts_type_sensitive_equality(self) -> None:
        left = {"asset_count": 7, "optional": False}
        right_bool_as_int = {"asset_count": 7, "optional": 0}
        right_float = {"asset_count": 7.0, "optional": False}
        self.assertTrue(contract.json_values_equal(left, {"asset_count": 7, "optional": False}))
        self.assertFalse(contract.json_values_equal(left, right_bool_as_int))
        self.assertFalse(contract.json_values_equal(left, right_float))

    def test_report_asset_case_binds_four_observations(self) -> None:
        records = contract.load_case_records()
        report = next(case for case in records["cases"] if case["id"] == "INST-REPORT-ASSET-001")
        self.assertEqual(len(report["observation_ids"]), 4)
        self.assertEqual(report["independent_facts"]["observation_count"], 4)
        self.assertEqual(report["independent_facts"]["asset_count"], 7)
        self.assertEqual(len(report["independent_facts"]["observations"]), 4)

    def test_layout_case_binds_tree_partition(self) -> None:
        records = contract.load_case_records()
        layout = next(case for case in records["cases"] if case["id"] == "INST-LAYOUT-001")
        self.assertEqual(layout["independent_facts"]["tree_entry_count"], 321)
        self.assertEqual(layout["independent_facts"]["support_script_count"], 23)
        self.assertFalse(layout["independent_facts"]["directory_entries_retained"])

    def test_missing_evidence_gap_for_executable_lifecycle_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["known_evidence_gaps"] = [
            gap for gap in document["known_evidence_gaps"]
            if "executable install/uninstall lifecycle" not in gap
        ]
        with self.assertRaisesRegex(contract.InstallationContractError, "known_evidence_gaps"):
            self.validate(document)

    def _rewrite_case_records(self, mutate) -> tuple[bytes, str]:
        backup = contract.CASE_RECORDS_PATH.read_bytes()
        records = json.loads(backup.decode("ascii"))
        mutate(records)
        for case in records["cases"]:
            facts_bytes = contract.canonical_json(case["independent_facts"]).encode("ascii")
            case["facts_sha256"] = contract.sha256_bytes(facts_bytes)
        raw = contract.canonical_json(records).encode("ascii")
        contract.CASE_RECORDS_PATH.write_bytes(raw)
        return backup, contract.sha256_bytes(raw)

    def test_layout_support_script_names_mutation_rejects_after_hash_refresh(self) -> None:
        backup = contract.CASE_RECORDS_PATH.read_bytes()
        expected = contract.EXPECTED_CASE_RECORDS_SHA256
        try:
            def mutate(records: dict[str, object]) -> None:
                layout = next(case for case in records["cases"] if case["id"] == "INST-LAYOUT-001")
                layout["independent_facts"]["support_script_names"] = ["mutated-script.py"]
                layout["independent_facts"]["support_script_count"] = 1

            _backup, refreshed = self._rewrite_case_records(mutate)
            contract.EXPECTED_CASE_RECORDS_SHA256 = refreshed
            with self.assertRaisesRegex(
                contract.InstallationContractError,
                "independent_facts mismatch|support_script_names|case records drift",
            ):
                contract.validate_document(contract.build_document(UPSTREAM_ROOT), UPSTREAM_ROOT)
        finally:
            contract.CASE_RECORDS_PATH.write_bytes(backup)
            contract.EXPECTED_CASE_RECORDS_SHA256 = expected

    def test_nested_source_digest_mutation_rejects_after_hash_refresh(self) -> None:
        backup = contract.CASE_RECORDS_PATH.read_bytes()
        expected = contract.EXPECTED_CASE_RECORDS_SHA256
        try:
            def mutate(records: dict[str, object]) -> None:
                stage = next(case for case in records["cases"] if case["id"] == "INST-STAGE-001")
                stage["independent_facts"]["source_bindings"][0]["sha256"] = "0" * 64
                stage["independent_facts"]["source_bindings"][0]["text_sha256"] = "0" * 64

            _backup, refreshed = self._rewrite_case_records(mutate)
            contract.EXPECTED_CASE_RECORDS_SHA256 = refreshed
            with self.assertRaisesRegex(
                contract.InstallationContractError,
                "source binding digest drift|independent_facts mismatch|case records drift",
            ):
                contract.validate_document(contract.build_document(UPSTREAM_ROOT), UPSTREAM_ROOT)
        finally:
            contract.CASE_RECORDS_PATH.write_bytes(backup)
            contract.EXPECTED_CASE_RECORDS_SHA256 = expected

    def test_report_artifact_path_mutation_rejects_after_hash_refresh(self) -> None:
        backup = contract.CASE_RECORDS_PATH.read_bytes()
        expected = contract.EXPECTED_CASE_RECORDS_SHA256
        try:
            def mutate(records: dict[str, object]) -> None:
                report = next(case for case in records["cases"] if case["id"] == "INST-REPORT-ASSET-001")
                # Swap first observation path onto the second retained sample path.
                report["independent_facts"]["observations"][0]["artifact_path"] = (
                    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/"
                    "report-genhtml-default-measured-001/output-tree.json"
                )

            _backup, refreshed = self._rewrite_case_records(mutate)
            contract.EXPECTED_CASE_RECORDS_SHA256 = refreshed
            with self.assertRaisesRegex(
                contract.InstallationContractError,
                "artifact_path|independent_facts mismatch|case records drift",
            ):
                contract.validate_document(contract.build_document(UPSTREAM_ROOT), UPSTREAM_ROOT)
        finally:
            contract.CASE_RECORDS_PATH.write_bytes(backup)
            contract.EXPECTED_CASE_RECORDS_SHA256 = expected

    def test_report_observation_mapping_mutation_rejects_after_hash_refresh(self) -> None:
        backup = contract.CASE_RECORDS_PATH.read_bytes()
        expected = contract.EXPECTED_CASE_RECORDS_SHA256
        try:
            def mutate(records: dict[str, object]) -> None:
                report = next(case for case in records["cases"] if case["id"] == "INST-REPORT-ASSET-001")
                report["observation_ids"][0] = (
                    "installation.asset-observation.report-genhtml-default-measured-001"
                )
                report["independent_facts"]["observations"][0]["id"] = (
                    "installation.asset-observation.report-genhtml-default-measured-001"
                )

            _backup, refreshed = self._rewrite_case_records(mutate)
            contract.EXPECTED_CASE_RECORDS_SHA256 = refreshed
            with self.assertRaisesRegex(
                contract.InstallationContractError,
                "observation|independent_facts mismatch|case records drift",
            ):
                contract.validate_document(contract.build_document(UPSTREAM_ROOT), UPSTREAM_ROOT)
        finally:
            contract.CASE_RECORDS_PATH.write_bytes(backup)
            contract.EXPECTED_CASE_RECORDS_SHA256 = expected


if __name__ == "__main__":
    unittest.main()
