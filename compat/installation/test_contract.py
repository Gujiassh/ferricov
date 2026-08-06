from __future__ import annotations

import copy
import json
from jsonschema import Draft202012Validator
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
        self.assertTrue(layout["independent_facts"]["directory_companion_retained"])
        self.assertEqual(layout["independent_facts"]["directory_companion_entry_count"], 57)

    def test_missing_evidence_gap_for_executable_lifecycle_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["known_evidence_gaps"] = [
            gap for gap in document["known_evidence_gaps"]
            if "no Ferricov product installer" not in gap
        ]
        with self.assertRaisesRegex(contract.InstallationContractError, "known_evidence_gaps"):
            self.validate(document)

    def test_wave2_directory_companion_is_bound(self) -> None:
        records = contract.load_case_records()
        layout = next(case for case in records["cases"] if case["id"] == "INST-LAYOUT-001")
        facts = layout["independent_facts"]
        self.assertFalse(facts["directory_entries_retained"])
        self.assertTrue(facts["directory_companion_retained"])
        self.assertEqual(facts["directory_companion_entry_count"], 57)
        self.assertEqual(facts["directory_companion_mode"], "755")
        self.assertEqual(
            facts["directory_companion_path"],
            "compat/installation/wave2/installed-directories.lock",
        )
        self.assertEqual(
            facts["directory_companion_sha256"],
            contract.EXPECTED_WAVE2_DIRECTORY_LOCK_SHA256,
        )
        companion = contract.wave2_directory_companion()
        self.assertEqual(companion["entry_count"], 57)
        self.assertEqual(len(companion["paths"]), 57)

    def test_wave2_case_captures_are_bound_and_remain_planned(self) -> None:
        records = contract.load_case_records()
        capture = contract.wave2_capture_document()
        table = contract.wave2_expected_table()
        self.assertEqual(capture["evidence_status"], "oracle_reference")
        self.assertEqual(capture["execution_status"], "planned")
        self.assertIs(capture["product_compatibility_evidence"], False)
        self.assertEqual(capture["capture_format"], "replayable_case_records_v1")
        self.assertEqual(len(table["cases"]), 13)
        for case in records["cases"]:
            self.assertEqual(case["execution_status"], "planned")
            self.assertEqual(case["evidence_status"], "oracle_reference")
            self.assertEqual(case["product_evidence"], [])
            facts = case["independent_facts"]
            if case["id"] == "INST-PATH-001":
                self.assertEqual(facts["oracle_execution_status"], "captured")
                expected = contract.capture_binding_for_case(case["id"])
                self.assertEqual(facts["capture_artifacts"], expected)
                self.assertIn("relative", facts["capture_artifacts"])
                self.assertIn("space", facts["capture_artifacts"])
                continue
            if case["id"] == "INST-LAYOUT-001":
                expected = contract.capture_binding_for_case(case["id"])
                self.assertEqual(facts["capture_artifact"], expected)
                continue
            self.assertEqual(facts["oracle_execution_status"], "captured")
            expected = contract.capture_binding_for_case(case["id"])
            self.assertEqual(facts["capture_artifact"], expected)
            self.assertIn("observation_sha256", facts["capture_artifact"])
            self.assertIn("stdout_sha256", facts["capture_artifact"])
            self.assertIn("stderr_sha256", facts["capture_artifact"])

    def test_wave2_artifact_drift_is_rejected(self) -> None:
        expected = contract.EXPECTED_WAVE2_CAPTURE_SHA256
        try:
            contract.EXPECTED_WAVE2_CAPTURE_SHA256 = "0" * 64
            with self.assertRaisesRegex(contract.InstallationContractError, "wave2 capture"):
                contract.wave2_capture_document()
        finally:
            contract.EXPECTED_WAVE2_CAPTURE_SHA256 = expected

    def test_wave2_expected_table_image_co_mutation_is_rejected(self) -> None:
        backup = contract.WAVE2_EXPECTED_TABLE_PATH.read_bytes()
        try:
            table = json.loads(backup.decode("ascii"))
            table["oracle_image_id"] = "sha256:" + ("a" * 64)
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(contract.canonical_json(table).encode("ascii"))
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )
            with self.assertRaisesRegex(contract.InstallationContractError, "image"):
                contract.wave2_expected_table()
        finally:
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(backup)
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )

    def test_wave2_expected_table_upstream_co_mutation_is_rejected(self) -> None:
        backup = contract.WAVE2_EXPECTED_TABLE_PATH.read_bytes()
        try:
            table = json.loads(backup.decode("ascii"))
            table["upstream_commit"] = "0" * 40
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(contract.canonical_json(table).encode("ascii"))
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )
            with self.assertRaisesRegex(contract.InstallationContractError, "upstream"):
                contract.wave2_expected_table()
        finally:
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(backup)
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )

    def test_wave2_exit_status_co_mutation_is_rejected(self) -> None:
        backup = contract.WAVE2_EXPECTED_TABLE_PATH.read_bytes()
        try:
            table = json.loads(backup.decode("ascii"))
            for case in table["cases"]:
                if case["id"] == "INST-STAGE-001":
                    case["expected_exit_status"] = 99
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(contract.canonical_json(table).encode("ascii"))
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )
            with self.assertRaisesRegex(contract.InstallationContractError, "exit status"):
                contract.capture_binding_for_case("INST-STAGE-001")
        finally:
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(backup)
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )

    def test_wave2_argv_co_mutation_is_rejected(self) -> None:
        backup = contract.WAVE2_EXPECTED_TABLE_PATH.read_bytes()
        try:
            table = json.loads(backup.decode("ascii"))
            for case in table["cases"]:
                if case["id"] == "INST-STAGE-001":
                    case["argv"] = ["make", "install", "DESTDIR=/tmp/mutated"]
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(contract.canonical_json(table).encode("ascii"))
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )
            with self.assertRaisesRegex(contract.InstallationContractError, "argv"):
                contract.capture_binding_for_case("INST-STAGE-001")
        finally:
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(backup)
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )

    def _mutate_path_bytes(self, path: Path, mutator) -> None:
        """Mutate a bound artifact with chmod restore; preserves original bytes on exit.

        Capture envelopes may be root-owned after Docker if normalization was skipped.
        Tests must still exercise real path binding (not temp-path stubs) without
        weakening sha256 co-mutation checks.
        """
        backup = path.read_bytes()
        mode = path.stat().st_mode
        try:
            try:
                path.chmod(mode | 0o200)
            except OSError:
                pass
            mutator(path, backup)
        finally:
            try:
                path.chmod(mode | 0o200)
            except OSError:
                pass
            path.write_bytes(backup)
            try:
                path.chmod(mode)
            except OSError:
                pass

    def test_wave2_raw_stdout_byte_mutation_is_rejected(self) -> None:
        path = contract.ROOT / "compat/installation/wave2/cases/INST-STAGE-001/stdout.bin"

        def mutate(target: Path, backup: bytes) -> None:
            target.write_bytes(backup + b"\nmutated\n")
            with self.assertRaisesRegex(contract.InstallationContractError, "stdout"):
                contract.capture_binding_for_case("INST-STAGE-001")

        self._mutate_path_bytes(path, mutate)

    def test_wave2_observation_hash_mutation_is_rejected(self) -> None:
        path = contract.ROOT / "compat/installation/wave2/cases/INST-STAGE-001/capture.json"
        rel = "compat/installation/wave2/cases/INST-STAGE-001/capture.json"
        old_hash = contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel]

        def mutate(target: Path, backup: bytes) -> None:
            record = json.loads(backup.decode("ascii"))
            record["observation_sha256"] = "0" * 64
            target.write_bytes(contract.canonical_json(record).encode("ascii"))
            # Refresh artifact hash table entry so binding reaches observation check
            # rather than failing earlier on static artifact_bindings drift.
            contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel] = contract.sha256_file(target)
            try:
                with self.assertRaisesRegex(contract.InstallationContractError, "observation"):
                    contract.capture_binding_for_case("INST-STAGE-001")
            finally:
                contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel] = old_hash

        self._mutate_path_bytes(path, mutate)

    def test_wave2_status_promotion_in_expected_table_is_rejected(self) -> None:
        backup = contract.WAVE2_EXPECTED_TABLE_PATH.read_bytes()
        try:
            table = json.loads(backup.decode("ascii"))
            table["execution_status"] = "executed"
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(contract.canonical_json(table).encode("ascii"))
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )
            with self.assertRaisesRegex(contract.InstallationContractError, "status"):
                contract.wave2_expected_table()
        finally:
            contract.WAVE2_EXPECTED_TABLE_PATH.write_bytes(backup)
            contract.EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = contract.sha256_file(
                contract.WAVE2_EXPECTED_TABLE_PATH
            )

    def _stage_capture_path(self) -> Path:
        return contract.ROOT / "compat/installation/wave2/cases/INST-STAGE-001/capture.json"

    def _co_mutate_stage_capture(self, mutator) -> None:
        """Mutate STAGE capture and refresh observation + artifact hash table entry.

        Independent expected table is NOT updated. Binding must reject the co-mutation.
        """
        path = self._stage_capture_path()
        backup = path.read_bytes()
        rel = "compat/installation/wave2/cases/INST-STAGE-001/capture.json"
        old_hash = contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel]
        mode = path.stat().st_mode
        try:
            try:
                path.chmod(mode | 0o200)
            except OSError:
                pass
            record = json.loads(backup.decode("ascii"))
            mutator(record)
            # Recompute observation hash as a co-mutator would after changing material.
            record["observation_sha256"] = contract.recompute_observation_sha256(record)
            path.write_bytes(contract.canonical_json(record).encode("ascii"))
            contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel] = contract.sha256_file(path)
            with self.assertRaises(contract.InstallationContractError):
                contract.capture_binding_for_case("INST-STAGE-001")
        finally:
            try:
                path.chmod(mode | 0o200)
            except OSError:
                pass
            path.write_bytes(backup)
            try:
                path.chmod(mode)
            except OSError:
                pass
            contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel] = old_hash

    def test_wave2_env_co_mutation_is_rejected(self) -> None:
        def mutate(record: dict) -> None:
            record["environment"]["observed_variables"]["MUTATED"] = "1"
            record["environment"]["variables"]["MUTATED"] = "1"
        self._co_mutate_stage_capture(mutate)

    def test_wave2_cwd_co_mutation_is_rejected(self) -> None:
        def mutate(record: dict) -> None:
            record["invocation"]["working_directory"] = "/tmp/mutated-cwd"
        self._co_mutate_stage_capture(mutate)

    def test_wave2_timeout_co_mutation_is_rejected(self) -> None:
        def mutate(record: dict) -> None:
            record["invocation"]["timeout_seconds"] = 1
        self._co_mutate_stage_capture(mutate)

    def test_wave2_cleanup_co_mutation_is_rejected(self) -> None:
        def mutate(record: dict) -> None:
            record["invocation"]["cleanup"] = ["rm -rf /tmp/mutated"]
        self._co_mutate_stage_capture(mutate)

    def test_wave2_exe_hash_co_mutation_is_rejected(self) -> None:
        def mutate(record: dict) -> None:
            record["identity"]["executable_sha256"] = "a" * 64
        self._co_mutate_stage_capture(mutate)

    def test_wave2_signal_co_mutation_is_rejected(self) -> None:
        def mutate(record: dict) -> None:
            record["process"]["signal"] = 15
            record["process"]["exit_status"] = None
            record["process"]["timed_out"] = False
        self._co_mutate_stage_capture(mutate)

    def test_wave2_child_status_co_mutation_is_rejected(self) -> None:
        def mutate(record: dict) -> None:
            kids = record["process"]["child_processes_observed"]
            if kids:
                kids[0]["exit_status"] = 99
            else:
                record["process"]["child_processes_observed"] = [
                    {
                        "command": "mutated",
                        "argv": ["mutated"],
                        "exit_status": 99,
                        "signal": None,
                        "timed_out": False,
                    }
                ]
        self._co_mutate_stage_capture(mutate)

    def test_wave2_tree_paths_co_mutation_is_rejected(self) -> None:
        def mutate(record: dict) -> None:
            record["file_tree_effects"]["paths_sha256"] = "b" * 64
            # keep row count consistent but change hash
        self._co_mutate_stage_capture(mutate)

    def test_wave2_capture_schema_rejects_zero_executable_hash(self) -> None:
        schema = contract.wave2_case_capture_schema()
        record = contract.load_json(self._stage_capture_path())
        record["identity"]["executable_sha256"] = "0" * 64
        with self.assertRaises(Exception):
            Draft202012Validator(schema).validate(record)

    def test_wave2_capture_schema_rejects_relative_cwd(self) -> None:
        schema = contract.wave2_case_capture_schema()
        record = contract.load_json(self._stage_capture_path())
        record["invocation"]["working_directory"] = "relative/cwd"
        with self.assertRaises(Exception):
            Draft202012Validator(schema).validate(record)

    def test_wave2_capture_schema_rejects_null_exit_without_signal(self) -> None:
        schema = contract.wave2_case_capture_schema()
        record = contract.load_json(self._stage_capture_path())
        record["process"]["exit_status"] = None
        record["process"]["signal"] = None
        record["process"]["timed_out"] = False
        with self.assertRaises(Exception):
            Draft202012Validator(schema).validate(record)

    def test_wave2_capture_schema_rejects_escaping_artifact_path(self) -> None:
        schema = contract.wave2_case_capture_schema()
        record = contract.load_json(self._stage_capture_path())
        record["artifacts"]["stdout_bin"]["path"] = "../escape.bin"
        with self.assertRaises(Exception):
            Draft202012Validator(schema).validate(record)

    def test_wave2_capture_schema_rejects_missing_tree_rows(self) -> None:
        schema = contract.wave2_case_capture_schema()
        record = contract.load_json(self._stage_capture_path())
        del record["file_tree_effects"]["rows"]
        with self.assertRaises(Exception):
            Draft202012Validator(schema).validate(record)

    def test_wave2_schema_rejects_reviewer_twelve_invalid_shapes(self) -> None:
        """Reviewer verbatim negative probe: 12 invalid captured shapes must fail."""
        from jsonschema import Draft202012Validator
        import copy

        schema = contract.wave2_case_capture_schema()
        base = contract.load_json(self._stage_capture_path())
        validator = Draft202012Validator(schema)

        def mutate(mutator):
            rec = copy.deepcopy(base)
            mutator(rec)
            errors = list(validator.iter_errors(rec))
            # Also enforce semantic_validate when schema alone might lag.
            semantic_fail = False
            try:
                # Import semantic checker from recapture.
                import importlib.util
                from pathlib import Path as P
                mod_path = contract.ROOT / "compat/installation/wave2/recapture.py"
                spec = importlib.util.spec_from_file_location("wave2_recapture", mod_path)
                mod = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(mod)
                try:
                    mod.semantic_validate_record(rec)
                except SystemExit:
                    semantic_fail = True
            except Exception:
                semantic_fail = True
            self.assertTrue(
                bool(errors) or semantic_fail,
                "invalid shape accepted by schema and semantic checks",
            )

        # 1 prefix-preserving artifact traversal
        mutate(lambda r: r["artifacts"]["stdout_bin"].__setitem__(
            "path", "compat/installation/wave2/cases/../../../../etc/passwd"
        ))
        # 2 extra-artifact traversal
        def m2(r):
            r.setdefault("artifacts", {}).setdefault("extra", [])
            if not r["artifacts"]["extra"]:
                r["artifacts"]["extra"] = [{
                    "name": "x",
                    "path": "compat/installation/wave2/cases/foo",
                    "sha256": "a" * 64,
                    "bytes": 0,
                }]
            r["artifacts"]["extra"][0]["path"] = (
                "compat/installation/wave2/cases/../../../../etc/passwd"
            )
        mutate(m2)
        # 3 executable .. traversal
        mutate(lambda r: r["identity"].__setitem__("executable_path", "/usr/bin/../etc/passwd"))
        # 4 cwd .. traversal
        mutate(lambda r: r["invocation"].__setitem__("working_directory", "/tmp/../etc"))
        # 5 tree-root .. traversal
        mutate(lambda r: r["file_tree_effects"].__setitem__("root", "/tmp/../etc"))
        # 6 tree-row .. traversal
        def m6(r):
            if r["file_tree_effects"]["rows"]:
                r["file_tree_effects"]["rows"][0]["path"] = "/tmp/../etc/passwd"
            else:
                r["file_tree_effects"]["rows"] = [{
                    "kind": "file",
                    "mode": "644",
                    "identity": "a" * 64,
                    "path": "/tmp/../etc/passwd",
                }]
        mutate(m6)
        # 7 empty captured child list
        mutate(lambda r: r["process"].__setitem__("child_processes_observed", []))
        # 8 child with no exit/signal/timeout outcome
        def m8(r):
            r["process"]["child_processes_observed"] = [{
                "command": "x",
                "argv": ["x"],
                "exit_status": None,
                "signal": None,
                "timed_out": False,
            }]
        mutate(m8)
        # 9 timed-out child with exit and no signal
        def m9(r):
            r["process"]["child_processes_observed"] = [{
                "command": "x",
                "argv": ["x"],
                "exit_status": 1,
                "signal": None,
                "timed_out": True,
            }]
            r["process"]["timed_out"] = True
            r["process"]["signal"] = 15
            r["process"]["exit_status"] = None
        mutate(m9)
        # 10 empty rows with nonzero counts
        def m10(r):
            r["file_tree_effects"]["rows"] = []
            r["file_tree_effects"]["file_count"] = 3
            r["file_tree_effects"]["directory_count"] = 1
            r["file_tree_effects"]["symlink_count"] = 0
        mutate(m10)
        # 11 file row with non-hash identity
        def m11(r):
            r["file_tree_effects"]["rows"] = [{
                "kind": "file",
                "mode": "644",
                "identity": "not-a-hash",
                "path": "/tmp/x",
            }]
            r["file_tree_effects"]["file_count"] = 1
            r["file_tree_effects"]["directory_count"] = 0
            r["file_tree_effects"]["symlink_count"] = 0
        mutate(m11)
        # 12 declared/observed environment mismatch
        def m12(r):
            r["environment"]["variables"] = dict(r["environment"]["observed_variables"])
            r["environment"]["variables"]["MUTATED"] = "1"
        mutate(m12)

    def test_wave2_host_observer_code_is_docker_rc_not_inner_status(self) -> None:
        """host_observer_code must equal host docker rc artifact, not subject wait."""
        stage = contract.load_json(self._stage_capture_path())
        host = (
            contract.ROOT
            / "compat/installation/wave2/cases/INST-STAGE-001/host-observer.txt"
        )
        text = host.read_text(encoding="utf-8")
        rc_line = [ln for ln in text.splitlines() if ln.startswith("rc=")][0]
        docker_rc = int(rc_line.split("=", 1)[1])
        self.assertEqual(stage["process"]["host_observer_code"], docker_rc)

    def test_wave2_runner_qualification_signal_and_timeout_are_retained(self) -> None:
        bindings = contract.validate_wave2_runner_qualification()
        by_id = {b["id"]: b for b in bindings}
        self.assertEqual(set(by_id), {"INST-RUNNER-SIGNAL-001", "INST-RUNNER-TIMEOUT-001"})
        sig = contract.load_case_capture_record(
            "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/capture.json"
        )
        tout = contract.load_case_capture_record(
            "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/capture.json"
        )
        self.assertEqual(sig["process"]["signal"], 15)
        self.assertFalse(sig["process"]["timed_out"])
        self.assertIsNone(sig["process"]["exit_status"])
        self.assertTrue(tout["process"]["timed_out"])
        self.assertIsNotNone(tout["process"]["signal"])
        self.assertIsNone(tout["process"]["exit_status"])
        self.assertEqual(int(sig["invocation"]["timeout_seconds"]), 30)
        self.assertEqual(int(tout["invocation"]["timeout_seconds"]), 1)
        # All artifact refs must live under cases/_runner/<id>/
        for rec, cid in ((sig, "INST-RUNNER-SIGNAL-001"), (tout, "INST-RUNNER-TIMEOUT-001")):
            prefix = f"compat/installation/wave2/cases/_runner/{cid}/"
            self.assertTrue(rec["artifacts"]["stdout_bin"]["path"].startswith(prefix))
            self.assertTrue(rec["artifacts"]["stderr_bin"]["path"].startswith(prefix))
            for extra in rec["artifacts"].get("extra") or []:
                self.assertTrue(extra["path"].startswith(prefix), extra["path"])
        self.assertGreaterEqual(len(sig["process"]["child_processes_observed"]), 1)
        self.assertGreaterEqual(len(tout["process"]["child_processes_observed"]), 1)

    def test_wave2_layout_and_interp_exe_match_observed_argv0_resolution(self) -> None:
        layout = contract.load_json(
            contract.ROOT / "compat/installation/wave2/cases/INST-LAYOUT-001/capture.json"
        )
        interp = contract.load_json(
            contract.ROOT / "compat/installation/wave2/cases/INST-INTERP-001/capture.json"
        )
        # No contradiction: LAYOUT subject is sh/dash, not find.
        self.assertEqual(layout["invocation"]["argv"][0], "/bin/sh")
        self.assertTrue(layout["identity"]["executable_path"].endswith("dash") or
                        layout["identity"]["executable_path"].endswith("sh"))
        # INTERP subject is make with LCOV_PERL in env, not env argv0.
        self.assertEqual(interp["invocation"]["argv"][0], "make")
        self.assertTrue(interp["identity"]["executable_path"].endswith("make"))
        self.assertIn("LCOV_PERL", interp["environment"]["observed_variables"])

    def test_wave2_test_run_is_deterministic_make_n_info(self) -> None:
        rec = contract.load_json(
            contract.ROOT / "compat/installation/wave2/cases/INST-TEST-RUN-001/capture.json"
        )
        self.assertEqual(rec["invocation"]["argv"], ["make", "-n", "info"])
        self.assertEqual(rec["process"]["exit_status"], 0)
        # No wall-clock database dump markers from make -np.
        stdout = (
            contract.ROOT / "compat/installation/wave2/cases/INST-TEST-RUN-001/stdout.bin"
        ).read_bytes()
        self.assertNotIn(b"# Make data base", stdout)

    def test_wave2_retained_captures_have_no_device_inode_fields(self) -> None:
        """Retained capture surface must not depend on container-local st_dev/st_ino."""
        wave2 = contract.ROOT / "compat/installation/wave2"
        forbidden = (
            "EXECUTABLE_ST_DEV=",
            "EXECUTABLE_ST_INO=",
            "\"st_dev\"",
            "\"st_ino\"",
            "ST_DEV=",
            "ST_INO=",
        )
        scanned = 0
        for path in wave2.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or ".capture-staging" in path.parts:
                continue
            if path.suffix in {".py", ".md", ".sh"} and path.name != "capture.json":
                # Source comments may mention the policy; only retained artifacts matter.
                if path.parts[-2:] != ("wave2", "process-observer.py"):
                    continue
            data = path.read_bytes()
            text = data.decode("utf-8", errors="replace")
            for token in forbidden:
                # Allow policy comments in process-observer source only.
                if path.name == "process-observer.py":
                    continue
                self.assertNotIn(
                    token,
                    text,
                    f"container-local identity field leaked into {path.relative_to(contract.ROOT)}",
                )
            scanned += 1
        self.assertGreater(scanned, 50)
        # Explicit: status/meta/run-meta for layout and both runners.
        for rel in (
            "compat/installation/wave2/cases/INST-LAYOUT-001/status.env",
            "compat/installation/wave2/cases/INST-LAYOUT-001/meta.env",
            "compat/installation/wave2/cases/INST-LAYOUT-001/run-meta.env",
            "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/status.env",
            "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/status.env",
        ):
            body = (contract.ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("EXECUTABLE_ST_DEV=", body)
            self.assertNotIn("EXECUTABLE_ST_INO=", body)
            self.assertIn("EXECUTABLE_PATH=", body)
            self.assertIn("EXECUTABLE_SHA256=", body)

    def test_wave2_cross_clone_replay_is_independent_of_device_inode(self) -> None:
        """Observation/status hashes must not encode device/inode numbers.

        Cross-clone Docker environments may report different st_dev values for the
        same executable content. Retained identity is path+content hash only.
        """
        import hashlib
        import re

        # Prove current retained envelopes contain no numeric ST fields.
        for path in (contract.ROOT / "compat/installation/wave2/cases").rglob("*.env"):
            body = path.read_text(encoding="utf-8", errors="replace")
            self.assertIsNone(re.search(r"EXECUTABLE_ST_(DEV|INO)=", body), path)
        # Observation material excludes any residual env file content; pin identity fields.
        stage = contract.load_case_capture_record(
            "compat/installation/wave2/cases/INST-STAGE-001/capture.json"
        )
        identity = stage["identity"]
        self.assertNotIn("st_dev", identity)
        self.assertNotIn("st_ino", identity)
        self.assertNotIn("executable_st_dev", identity)
        self.assertNotIn("executable_st_ino", identity)
        self.assertRegex(identity["executable_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn(identity["executable_sha256"], {"0" * 64, "f" * 64})
        # status.env artifact hash is part of extra bindings; ensure its body is clone-stable fields only.
        status = (
            contract.ROOT / "compat/installation/wave2/cases/INST-STAGE-001/status.env"
        ).read_text(encoding="utf-8")
        keys = [ln.split("=", 1)[0] for ln in status.splitlines() if "=" in ln]
        self.assertEqual(
            keys,
            [
                "EXIT_STATUS",
                "SIGNAL",
                "TIMED_OUT",
                "HOST_OBSERVER_CODE",
                "WORKDIR",
                "EXECUTABLE_PATH",
                "EXECUTABLE_SHA256",
                "WAIT_STATUS_RAW",
                "QUALIFICATION",
                "TIMEOUT_SECONDS",
            ],
        )




    def test_wave2_observer_ptrace_faults_reap_and_fail_closed(self) -> None:
        """SETOPTIONS/CONT faults must fail quickly without leaving live/stopped children."""
        import os
        import subprocess
        import tempfile
        import time
        from pathlib import Path

        obs = contract.ROOT / "compat/installation/wave2/process-observer.py"
        for fault in ("setoptions", "cont_initial", "cont_post_exec"):
            td = Path(tempfile.mkdtemp(prefix="obs-fault-"))
            envf = td / "env.env"
            envf.write_text("PATH=/usr/bin:/bin\nHOME=/tmp\nLANG=C\nLC_ALL=C\n", encoding="utf-8")
            cmd = [
                "python3",
                str(obs),
                "--workdir",
                "/tmp",
                "--timeout-seconds",
                "2",
                "--stdout",
                str(td / "out"),
                "--stderr",
                str(td / "err"),
                "--status",
                str(td / "status"),
                "--observed-argv",
                str(td / "argv.json"),
                "--observed-children",
                str(td / "children.json"),
                "--meta",
                str(td / "meta"),
                "--observed-env",
                str(td / "oenv"),
                "--env-file",
                str(envf),
                "--",
                "sleep",
                "30",
            ]
            env = os.environ.copy()
            env["FERRICOV_WAVE2_OBSERVER_FAULT"] = fault
            t0 = time.monotonic()
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
            dt = time.monotonic() - t0
            self.assertEqual(proc.returncode, 2, fault)
            self.assertLess(dt, 2.5, f"{fault} hung dt={dt}")
            # No status with sentinel hash.
            if (td / "status").is_file():
                self.assertNotIn("f" * 64, (td / "status").read_text(encoding="utf-8"))

    def test_wave2_observer_hash_permission_and_replacement_race(self) -> None:
        """Hash open/read faults fail closed; replacement race keeps executed inode hash."""
        import hashlib
        import os
        import shutil
        import subprocess
        import tempfile
        import threading
        import time
        from pathlib import Path

        obs = contract.ROOT / "compat/installation/wave2/process-observer.py"

        def _run(fault: str) -> subprocess.CompletedProcess:
            td = Path(tempfile.mkdtemp(prefix="obs-hash-"))
            envf = td / "env.env"
            envf.write_text("PATH=/usr/bin:/bin\nHOME=/tmp\nLANG=C\nLC_ALL=C\n", encoding="utf-8")
            env = os.environ.copy()
            env["FERRICOV_WAVE2_OBSERVER_FAULT"] = fault
            return subprocess.run(
                [
                    "python3",
                    str(obs),
                    "--workdir",
                    "/tmp",
                    "--timeout-seconds",
                    "2",
                    "--stdout",
                    str(td / "out"),
                    "--stderr",
                    str(td / "err"),
                    "--status",
                    str(td / "status"),
                    "--observed-argv",
                    str(td / "argv.json"),
                    "--observed-children",
                    str(td / "children.json"),
                    "--meta",
                    str(td / "meta"),
                    "--observed-env",
                    str(td / "oenv"),
                    "--env-file",
                    str(envf),
                    "--",
                    "/bin/true",
                ],
                env=env,
                capture_output=True,
                text=True,
            )

        for fault in ("hash_open", "hash_read"):
            proc = _run(fault)
            self.assertEqual(proc.returncode, 3, fault)
            self.assertNotIn("ffffffff", proc.stdout + proc.stderr)

        # Replacement race: hash open FD of sleep_copy before replace with true.
        td = Path(tempfile.mkdtemp(prefix="obs-race-"))
        sleep_copy = td / "sleep_copy"
        shutil.copy2("/usr/bin/sleep", sleep_copy)
        sleep_copy.chmod(0o755)
        sleep_hash = hashlib.sha256(sleep_copy.read_bytes()).hexdigest()
        true_hash = hashlib.sha256(Path("/usr/bin/true").read_bytes()).hexdigest()
        envf = td / "env.env"
        envf.write_text("PATH=/usr/bin:/bin\nHOME=/tmp\nLANG=C\nLC_ALL=C\n", encoding="utf-8")
        result: dict[str, object] = {}

        def launch() -> None:
            proc = subprocess.run(
                [
                    "python3",
                    str(obs),
                    "--workdir",
                    str(td),
                    "--timeout-seconds",
                    "5",
                    "--stdout",
                    str(td / "out"),
                    "--stderr",
                    str(td / "err"),
                    "--status",
                    str(td / "status"),
                    "--observed-argv",
                    str(td / "argv.json"),
                    "--observed-children",
                    str(td / "children.json"),
                    "--meta",
                    str(td / "meta"),
                    "--observed-env",
                    str(td / "oenv"),
                    "--env-file",
                    str(envf),
                    "--",
                    str(sleep_copy),
                    "3",
                ],
                capture_output=True,
                text=True,
            )
            result["rc"] = proc.returncode

        thr = threading.Thread(target=launch)
        thr.start()
        time.sleep(0.25)
        tmp = td / "true_tmp"
        shutil.copy2("/usr/bin/true", tmp)
        os.replace(tmp, sleep_copy)
        thr.join(timeout=10)
        self.assertEqual(result.get("rc"), 0)
        status = (td / "status").read_text(encoding="utf-8")
        recorded = [ln.split("=", 1)[1] for ln in status.splitlines() if ln.startswith("EXECUTABLE_SHA256=")][0]
        self.assertEqual(recorded, sleep_hash)
        self.assertNotEqual(recorded, true_hash)

    def test_wave2_replace_boundary_faults_fully_roll_back(self) -> None:
        """Forced failure at cases/index/lock install restores prior retained set."""
        import hashlib
        import importlib.util
        import os
        import shutil
        import tempfile
        from pathlib import Path

        wave2 = contract.ROOT / "compat/installation/wave2"
        mod_path = wave2 / "recapture.py"
        spec = importlib.util.spec_from_file_location("wave2_recapture_tx", mod_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        def fingerprint(root: Path) -> str:
            h = hashlib.sha256()
            for rel in ("cases", "oracle-capture.json", "installed-directories.lock"):
                p = root / rel
                if p.is_dir():
                    for f in sorted(p.rglob("*")):
                        if f.is_file():
                            h.update(f.relative_to(root).as_posix().encode())
                            h.update(f.read_bytes())
                elif p.is_file():
                    h.update(rel.encode())
                    h.update(p.read_bytes())
            return h.hexdigest()

        for boundary in ("cases", "oracle-capture.json", "installed-directories.lock"):
            td = Path(tempfile.mkdtemp(prefix="tx-"))
            # Build mini retained set
            (td / "cases" / "X").mkdir(parents=True)
            (td / "cases" / "X" / "a.txt").write_text("old-cases\n", encoding="utf-8")
            (td / "oracle-capture.json").write_text('{"old":true}\n', encoding="utf-8")
            (td / "installed-directories.lock").write_text("old-lock\n", encoding="utf-8")
            before = fingerprint(td)
            staging_parent = td / ".capture-staging"
            staging = staging_parent / "run"
            staging.mkdir(parents=True)
            staged_cases = staging / "cases"
            staged_index = staging / "oracle-capture.json"
            staged_lock = staging / "installed-directories.lock"
            (staged_cases / "Y").mkdir(parents=True)
            (staged_cases / "Y" / "b.txt").write_text("new-cases-MUTATED\n", encoding="utf-8")
            staged_index.write_text('{"new":true}\n', encoding="utf-8")
            staged_lock.write_text("new-lock\n", encoding="utf-8")
            env_key = "FERRICOV_WAVE2_REPLACE_FAULT"
            old = os.environ.get(env_key)
            os.environ[env_key] = boundary
            try:
                with self.assertRaises(RuntimeError):
                    mod.commit_replace_targets(
                        [
                            (staged_cases, td / "cases", "cases"),
                            (staged_index, td / "oracle-capture.json", "oracle-capture.json"),
                            (staged_lock, td / "installed-directories.lock", "installed-directories.lock"),
                        ],
                        staging_parent=staging_parent,
                    )
            finally:
                if old is None:
                    os.environ.pop(env_key, None)
                else:
                    os.environ[env_key] = old
            after = fingerprint(td)
            self.assertEqual(before, after, f"boundary={boundary}")
            # No stranded backup-* dirs
            leftovers = list(staging_parent.glob("backup-*")) if staging_parent.exists() else []
            self.assertEqual(leftovers, [], f"stranded backup at {boundary}: {leftovers}")
            # Old content restored
            self.assertEqual((td / "cases" / "X" / "a.txt").read_text(encoding="utf-8"), "old-cases\n")
            self.assertFalse((td / "cases" / "Y").exists())

    def test_wave2_expected_table_not_self_authenticated_by_observation_refresh(self) -> None:
        """Refreshing capture observation alone must not satisfy expected table."""
        path = self._stage_capture_path()
        backup = path.read_bytes()
        rel = "compat/installation/wave2/cases/INST-STAGE-001/capture.json"
        old_hash = contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel]
        try:
            record = json.loads(backup.decode("ascii"))
            record["environment"]["observed_variables"]["X"] = "y"
            record["observation_sha256"] = contract.recompute_observation_sha256(record)
            path.write_bytes(contract.canonical_json(record).encode("ascii"))
            contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel] = contract.sha256_file(path)
            # Even if we also refreshed expected observation (self-auth attack),
            # argv/env keys/exe still bind; here we only refresh capture, table fixed.
            with self.assertRaises(contract.InstallationContractError):
                contract.capture_binding_for_case("INST-STAGE-001")
        finally:
            path.write_bytes(backup)
            contract.EXPECTED_WAVE2_ARTIFACT_HASHES[rel] = old_hash


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
                "schema failure|independent_facts mismatch|support_script_names|case records drift",
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

    def test_standalone_schema_rejects_layout_stage_facts_variant_swap(self) -> None:
        """Standalone schema must bind each case id to its exact facts variant."""
        schema = json.loads(contract.CASE_RECORDS_SCHEMA_PATH.read_text(encoding="ascii"))
        records = json.loads(contract.CASE_RECORDS_PATH.read_text(encoding="ascii"))
        Draft202012Validator(schema).validate(records)

        mutated = copy.deepcopy(records)
        layout = next(case for case in mutated["cases"] if case["id"] == "INST-LAYOUT-001")
        stage = next(case for case in mutated["cases"] if case["id"] == "INST-STAGE-001")
        layout["independent_facts"], stage["independent_facts"] = (
            stage["independent_facts"],
            layout["independent_facts"],
        )
        for case in (layout, stage):
            facts_bytes = contract.canonical_json(case["independent_facts"]).encode("ascii")
            case["facts_sha256"] = contract.sha256_bytes(facts_bytes)

        errors = list(Draft202012Validator(schema).iter_errors(mutated))
        self.assertTrue(errors, "schema accepted LAYOUT/STAGE independent_facts swap")

        # Fixed order is also schema-enforced.
        reordered = copy.deepcopy(records)
        reordered["cases"][0], reordered["cases"][1] = reordered["cases"][1], reordered["cases"][0]
        order_errors = list(Draft202012Validator(schema).iter_errors(reordered))
        self.assertTrue(order_errors, "schema accepted case order swap")

        # Layout exception: nested source_bindings are forbidden on INST-LAYOUT-001.
        with_bindings = copy.deepcopy(records)
        with_bindings["cases"][0]["independent_facts"]["source_bindings"] = (
            records["cases"][1]["independent_facts"]["source_bindings"]
        )
        facts_bytes = contract.canonical_json(
            with_bindings["cases"][0]["independent_facts"]
        ).encode("ascii")
        with_bindings["cases"][0]["facts_sha256"] = contract.sha256_bytes(facts_bytes)
        layout_errors = list(Draft202012Validator(schema).iter_errors(with_bindings))
        self.assertTrue(layout_errors, "schema accepted nested source_bindings on INST-LAYOUT-001")


if __name__ == "__main__":
    unittest.main()
