from __future__ import annotations

import copy
import importlib.util
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from jsonschema import Draft202012Validator


DIAGNOSTICS_ROOT = Path(__file__).resolve().parent
UPSTREAM_ROOT = Path(
    os.environ.get(
        "LCOV_SOURCE_ROOT",
        DIAGNOSTICS_ROOT.parents[2] / "lcov-upstream-reference",
    )
).resolve()

SPEC = importlib.util.spec_from_file_location(
    "ferricov_diagnostics_contract",
    DIAGNOSTICS_ROOT / "contract.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load diagnostics contract module")
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class DiagnosticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        contract.validate_upstream_identity(UPSTREAM_ROOT)
        cls.generated = contract.build_document(UPSTREAM_ROOT)
        cls.committed = contract.load_json(contract.OUTPUT_PATH)

    def validate(self, document: dict[str, object]) -> None:
        contract.validate_document(document, UPSTREAM_ROOT)

    def test_committed_contract_matches_generation(self) -> None:
        self.validate(self.committed)
        self.assertEqual(
            contract.canonical_json(self.committed),
            contract.canonical_json(self.generated),
        )

    def test_missing_category_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["categories"].pop()
        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_category_order_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["categories"][:2] = reversed(document["categories"][:2])
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "registry or symbol closure drift",
        ):
            self.validate(document)

    def test_symbol_reference_closure_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["categories"][0]["symbol_references_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "registry or symbol closure drift",
        ):
            self.validate(document)

    def test_reserved_branch_promotion_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        branch = next(
            entry for entry in document["categories"] if entry["name"] == "branch"
        )
        branch["emitter_status"] = "emitted"
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "registry or symbol closure drift",
        ):
            self.validate(document)

    def test_control_source_text_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["control_rules"][0]["source_references"][0]["text"] += " # drift"
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "control-rule drift",
        ):
            self.validate(document)

    def test_exit_policy_change_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        perl2lcov = next(
            entry
            for entry in document["exit_policies"]
            if entry["command"] == "perl2lcov"
        )
        perl2lcov["policy"] = "shared_saw_error_fold"
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "exit-policy drift",
        ):
            self.validate(document)

    def test_planned_case_catalog_gap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["planned_case_ids"].pop()
        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_oracle_observation_identity_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        first, second = document["oracle_observations"][:2]
        first["stderr_sha256"], second["stderr_sha256"] = (
            second["stderr_sha256"],
            first["stderr_sha256"],
        )
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "Oracle observation identity drift",
        ):
            self.validate(document)

    def test_retained_artifact_hash_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["artifact_bindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "artifact binding drift",
        ):
            self.validate(document)

    def test_geninfo_startup_intercept_cannot_claim_noargs_case(self) -> None:
        document = copy.deepcopy(self.committed)
        geninfo = next(
            entry
            for entry in document["oracle_observations"]
            if entry["id"] == "correctness:m0-core-geninfo-startup-control"
        )
        geninfo["kind"] = "startup_boundary"
        geninfo["planned_case_ids"] = ["DIAG-NOARGS-GENINFO-001"]
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "Oracle observation identity drift",
        ):
            self.validate(document)

    def test_product_evidence_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["categories"][0]["product_evidence"] = ["not-product-evidence"]
        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_oracle_reference_cannot_be_promoted(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_observation_evidence_status"] = "product_pass"
        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_wave1_observation_count_and_planned_ids_are_bound(self) -> None:
        wave1 = [
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave1:")
        ]
        self.assertEqual(len(wave1), contract.WAVE1_EXPECTED_CASE_COUNT)
        self.assertEqual(self.committed["totals"]["wave1_observations"], 26)
        self.assertEqual(self.committed["totals"]["oracle_observations"], 206)
        planned = []
        for entry in wave1:
            for planned_id in entry["planned_case_ids"]:
                if planned_id not in planned:
                    planned.append(planned_id)
        self.assertEqual(planned, contract.WAVE1_EXPECTED_PLANNED_IDS)
        self.assertEqual(len(planned), 19)

    def test_true_geninfo_noargs_is_bound_separately_from_intercept(self) -> None:
        true_case = next(
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"] == "diagnostics-wave1:diag-noargs-geninfo-writable"
        )
        intercept = next(
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"] == "correctness:m0-core-geninfo-startup-control"
        )
        self.assertEqual(true_case["kind"], "startup_boundary")
        self.assertEqual(true_case["exit_status"], 255)
        self.assertEqual(true_case["planned_case_ids"], ["DIAG-NOARGS-GENINFO-001"])
        self.assertEqual(true_case["argv"], ["geninfo"])
        self.assertEqual(true_case["timeout_seconds"], 30)
        self.assertFalse(true_case["timed_out"])
        self.assertEqual(
            true_case["file_tree_semantics"], "workspace_including_inputs"
        )
        self.assertEqual(intercept["kind"], "startup_environment_intercept")
        self.assertEqual(intercept["planned_case_ids"], [])

    def test_ignore_two_and_promotion_wave1_bindings_exist(self) -> None:
        by_id = {
            entry["id"]: entry for entry in self.committed["oracle_observations"]
        }
        silent = by_id["diagnostics-wave1:diag-ignore2-format-da"]
        promote = by_id["diagnostics-wave1:diag-promote0-format-sanitize"]
        self.assertEqual(silent["kind"], "named_error_ignore_two")
        self.assertEqual(silent["planned_case_ids"], ["DIAG-IGNORE-SILENT-001"])
        self.assertEqual(silent["exit_status"], 0)
        self.assertEqual(
            silent["stderr_sha256"],
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
        self.assertEqual(promote["kind"], "warning_promotion_control")
        self.assertEqual(promote["planned_case_ids"], ["DIAG-WARNING-PROMOTE-001"])
        self.assertEqual(promote["exit_status"], 1)

    def test_converter_cases_use_real_inputs_and_boundary_is_separate(self) -> None:
        by_id = {
            entry["id"]: entry for entry in self.committed["oracle_observations"]
        }
        perl = by_id["diagnostics-wave1:diag-perl2lcov-keep"]
        llvm = by_id["diagnostics-wave1:diag-llvm2lcov-keep"]
        py = by_id["diagnostics-wave1:diag-py2lcov-keep"]
        xml = by_id["diagnostics-wave1:diag-xml2lcov-keep"]
        boundary = by_id["diagnostics-wave1:diag-converter-keep-boundary"]
        self.assertEqual(perl["fixtures"], ["cover_db"])
        self.assertEqual(llvm["fixtures"], ["llvm-keep.json"])
        self.assertEqual(py["fixtures"], ["coverage-keep.xml"])
        self.assertEqual(xml["fixtures"], ["coverage-keep.xml"])
        self.assertEqual(boundary["fixtures"], ["broken-no-sources.xml"])
        self.assertEqual(perl["exit_status"], 0)
        self.assertEqual(llvm["exit_status"], 0)
        self.assertEqual(py["exit_status"], 0)
        self.assertEqual(xml["exit_status"], 0)
        self.assertEqual(boundary["exit_status"], 1)
        self.assertEqual(boundary["planned_case_ids"], ["DIAG-CONVERTER-KEEP-BOUNDARY-001"])

    def test_wave1_identity_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        first = next(
            entry
            for entry in document["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave1:")
        )
        second = next(
            entry
            for entry in document["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave1:") and entry is not first
        )
        first["stderr_sha256"], second["stderr_sha256"] = (
            second["stderr_sha256"],
            first["stderr_sha256"],
        )
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "Oracle observation identity drift",
        ):
            self.validate(document)

    def test_wave1_product_promotion_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["product_compatibility_evidence"] = True
        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_wave1_raw_stdout_refresh_is_rejected(self) -> None:
        path = (
            contract.WAVE1_ROOT
            / "cases"
            / "diag-ignore2-format-da"
            / "reference"
            / "stdout.bin"
        )
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\nmutated-stdout\n")
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "stdout hash drift|Oracle observation identity drift|retained diagnostics artifact drift|wave1",
            ):
                contract.build_document(UPSTREAM_ROOT)
        finally:
            path.write_bytes(original)

    def test_wave1_raw_stderr_refresh_is_rejected(self) -> None:
        path = (
            contract.WAVE1_ROOT
            / "cases"
            / "diag-ignore0-format-da"
            / "reference"
            / "stderr.bin"
        )
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\nmutated-stderr\n")
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "stderr hash drift|Oracle observation identity drift|retained diagnostics artifact drift|wave1",
            ):
                contract.build_document(UPSTREAM_ROOT)
        finally:
            path.write_bytes(original)

    def test_wave1_file_tree_refresh_is_rejected(self) -> None:
        path = contract.WAVE1_ROOT / "cases" / "diag-ignore1-format-da" / "out.info"
        if not path.is_file():
            path = contract.WAVE1_ROOT / "cases" / "diag-ignore2-format-da" / "out.info"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n# mutated-tree\n")
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "file-tree|Oracle observation identity drift|retained diagnostics artifact drift|wave1",
            ):
                contract.build_document(UPSTREAM_ROOT)
        finally:
            path.write_bytes(original)

    def test_wave1_nested_metadata_refresh_is_rejected(self) -> None:
        path = (
            contract.WAVE1_ROOT
            / "cases"
            / "diag-noargs-geninfo-writable"
            / "result.json"
        )
        original = path.read_bytes()
        try:
            document = contract.load_json(path)
            document["timeout_seconds"] = 999
            path.write_text(contract.canonical_json(document))
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "timeout drift|observation hash drift|retained diagnostics artifact drift|wave1",
            ):
                contract.build_document(UPSTREAM_ROOT)
        finally:
            path.write_bytes(original)

    def test_wave1_converter_case_identity_refresh_is_rejected(self) -> None:
        path = contract.WAVE1_ROOT / "cases" / "diag-llvm2lcov-keep" / "result.json"
        original = path.read_bytes()
        try:
            document = contract.load_json(path)
            document["fixtures"] = []
            document["argv"] = ["llvm2lcov", "--keep-going"]
            path.write_text(contract.canonical_json(document))
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "fixture|argv|observation hash drift|retained diagnostics artifact drift|wave1",
            ):
                contract.build_document(UPSTREAM_ROOT)
        finally:
            path.write_bytes(original)

    def test_wave1_index_case_order_refresh_is_rejected(self) -> None:
        path = contract.WAVE1_INDEX
        original = path.read_bytes()
        try:
            document = contract.load_json(path)
            document["cases"] = list(reversed(document["cases"]))
            path.write_text(contract.canonical_json(document))
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "case id set/order drift|retained diagnostics artifact drift",
            ):
                contract.build_document(UPSTREAM_ROOT)
        finally:
            path.write_bytes(original)

    def test_oracle_observation_unknown_field_is_rejected_by_schema(self) -> None:
        schema = contract.load_json(contract.SCHEMA_PATH)
        root_schema = {
            "$schema": schema.get(
                "$schema", "https://json-schema.org/draft/2020-12/schema"
            ),
            "$defs": schema["$defs"],
            "$ref": "#/$defs/oracleObservation",
        }
        probe = {
            "id": "correctness:probe-unknown-field",
            "kind": "startup_boundary",
            "planned_case_ids": [],
            "exit_status": 1,
            "stdout_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "output_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "observation_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "unknown_field": "must-fail",
        }
        errors = list(Draft202012Validator(root_schema).iter_errors(probe))
        self.assertTrue(errors)
        self.assertTrue(
            any(
                error.validator == "additionalProperties"
                or "additional properties" in error.message
                for error in errors
            )
        )
        document = copy.deepcopy(self.committed)
        document["oracle_observations"][0]["unknown_field"] = "must-fail"
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "schema failure|additional",
        ):
            self.validate(document)

    def test_wave1_environment_metadata_refresh_is_rejected(self) -> None:
        path = (
            contract.WAVE1_ROOT
            / "cases"
            / "diag-noargs-geninfo-writable"
            / "result.json"
        )
        original = path.read_bytes()
        try:
            document = contract.load_json(path)
            mutated = dict(document["effective_environment_variables"])
            mutated["EXTRA_HOST_LEAK"] = "1"
            document["effective_environment_variables"] = mutated
            path.write_text(contract.canonical_json(document))
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "effective environment|environment policy|observation hash|retained diagnostics artifact|wave1",
            ):
                contract.build_document(UPSTREAM_ROOT)
        finally:
            path.write_bytes(original)

    def test_wave1_cleanup_outcome_refresh_is_rejected(self) -> None:
        path = (
            contract.WAVE1_ROOT
            / "cases"
            / "diag-ignore0-format-da"
            / "result.json"
        )
        original = path.read_bytes()
        try:
            document = contract.load_json(path)
            document["cleanup_outcome"] = {
                **document["cleanup_outcome"],
                "container_absent": False,
                "direct_child_reaped": False,
            }
            path.write_text(contract.canonical_json(document))
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "cleanup outcome|container_absent|direct_child_reaped|observation hash|retained diagnostics artifact|wave1",
            ):
                contract.build_document(UPSTREAM_ROOT)
        finally:
            path.write_bytes(original)

    def test_wave1_cleanup_and_environment_are_bound_independently(self) -> None:
        wave1 = [
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave1:")
        ]
        self.assertEqual(len(wave1), 26)
        for entry in wave1:
            self.assertEqual(entry["cleanup"], contract.WAVE1_CLEANUP)
            self.assertEqual(
                entry["effective_environment_variables"],
                contract.WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES,
            )
            self.assertEqual(
                entry["environment_policy"],
                contract.WAVE1_ENVIRONMENT_POLICY,
            )
            self.assertTrue(entry["cleanup_outcome"]["direct_child_reaped"])
            self.assertIs(entry["cleanup_outcome"]["container_absent"], True)
            self.assertIsNone(entry["cleanup_outcome"]["process_group_empty"])
            self.assertTrue(entry["cleanup_outcome"]["named_container_removed"])
            self.assertFalse(
                entry["environment_policy"]["inherits_host_environment"]
            )

    def test_container_absent_observer_failure_is_fail_closed(self) -> None:
        import importlib.util

        capture_path = (
            contract.WAVE1_ROOT / "scripts" / "capture_wave1.py"
        )
        spec = importlib.util.spec_from_file_location(
            "ferricov_diag_wave1_capture", capture_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load wave1 capture module")
        capture = importlib.util.module_from_spec(spec)
        # Avoid executing main; load module body only.
        spec.loader.exec_module(capture)

        # Nonzero docker ps must never be treated as empty/absent.
        failed = MagicMock()
        failed.returncode = 1
        failed.stdout = ""
        failed.stderr = "observer boom"
        with patch.object(capture.subprocess, "run", return_value=failed):
            with self.assertRaises(capture.Wave1CaptureError) as raised:
                capture.container_absent("ferricov-diag-wave1-probe")
        self.assertIn("docker ps observer failed", str(raised.exception))

        # Timeout is also fail-closed.
        with patch.object(
            capture.subprocess,
            "run",
            side_effect=capture.subprocess.TimeoutExpired(cmd=["docker"], timeout=30),
        ):
            with self.assertRaises(capture.Wave1CaptureError) as raised:
                capture.container_absent("ferricov-diag-wave1-probe")
        self.assertIn("timed out", str(raised.exception))

    def test_wave1_effective_environment_is_exact_command_env(self) -> None:
        wave1 = [
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave1:")
        ]
        expected = contract.WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES
        for entry in wave1:
            self.assertEqual(entry["effective_environment_variables"], expected)
            self.assertEqual(
                entry["environment_policy"]["effective_environment_variables"],
                expected,
            )
            self.assertEqual(
                entry["environment_policy"]["command_wrapper"],
                ["env", "-i"],
            )
            self.assertFalse(
                entry["environment_policy"]["inherits_host_environment"]
            )
            # No ambient host leakage keys.
            self.assertNotIn(
                "EXTRA_HOST_LEAK", entry["effective_environment_variables"]
            )

    def test_env_probe_timeout_still_force_removes_container(self) -> None:
        import importlib.util

        capture_path = contract.WAVE1_ROOT / "scripts" / "capture_wave1.py"
        spec = importlib.util.spec_from_file_location(
            "ferricov_diag_wave1_capture_timeout", capture_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load wave1 capture module")
        capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture)

        calls: list[str] = []

        def fake_force(name: str, *, direct_child_reaped: bool) -> dict:
            calls.append(name)
            return {
                "policy": capture.CLEANUP_POLICY,
                "direct_child_reaped": True,
                "process_group_empty": None,
                "container_absent": True,
                "named_container_removed": True,
                "container_name": name,
            }

        with patch.object(capture, "force_remove_container", side_effect=fake_force):
            with patch.object(
                capture,
                "run_docker_checked",
                side_effect=capture.subprocess.TimeoutExpired(
                    cmd=["docker"], timeout=30
                ),
            ):
                with self.assertRaises(capture.Wave1CaptureError) as raised:
                    capture.probe_effective_command_environment()
        self.assertIn("timed out", str(raised.exception))
        # pre-clean + finally cleanup
        self.assertGreaterEqual(calls.count("ferricov-diag-wave1-env-probe"), 2)

    def test_env_probe_oserror_still_force_removes_container(self) -> None:
        import importlib.util

        capture_path = contract.WAVE1_ROOT / "scripts" / "capture_wave1.py"
        spec = importlib.util.spec_from_file_location(
            "ferricov_diag_wave1_capture_oserror", capture_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load wave1 capture module")
        capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture)

        calls: list[str] = []

        def fake_force(name: str, *, direct_child_reaped: bool) -> dict:
            calls.append(name)
            return {
                "policy": capture.CLEANUP_POLICY,
                "direct_child_reaped": True,
                "process_group_empty": None,
                "container_absent": True,
                "named_container_removed": True,
                "container_name": name,
            }

        with patch.object(capture, "force_remove_container", side_effect=fake_force):
            with patch.object(
                capture,
                "run_docker_checked",
                side_effect=OSError("docker missing"),
            ):
                with self.assertRaises(capture.Wave1CaptureError):
                    capture.probe_effective_command_environment()
        self.assertGreaterEqual(calls.count("ferricov-diag-wave1-env-probe"), 2)

    def test_capture_launchers_use_stdin_devnull(self) -> None:
        import importlib.util
        import inspect

        capture_path = contract.WAVE1_ROOT / "scripts" / "capture_wave1.py"
        source = capture_path.read_text(encoding="utf-8")
        self.assertIn("stdin=subprocess.DEVNULL", source)
        # Both helper run and Popen must pin stdin.
        self.assertIn("def run_docker_checked", source)
        self.assertGreaterEqual(source.count("stdin=subprocess.DEVNULL"), 2)
        spec = importlib.util.spec_from_file_location(
            "ferricov_diag_wave1_capture_stdin", capture_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load wave1 capture module")
        capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture)
        self.assertIn(
            "stdin=subprocess.DEVNULL",
            inspect.getsource(capture.run_docker_checked),
        )
        self.assertIn(
            "stdin=subprocess.DEVNULL",
            inspect.getsource(capture.run_case),
        )

    def test_wave1_execution_manifest_provenance_is_bound(self) -> None:
        wave1 = [
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave1:")
        ]
        self.assertEqual(len(wave1), 26)
        base = contract.WAVE1_EXECUTION_MANIFEST_BASE
        self.assertIsNotNone(base)
        assert base is not None
        self.assertEqual(base["locale"], "C")
        self.assertEqual(base["lc_all"], "C")
        self.assertEqual(base["timezone"], "UTC")
        self.assertEqual(base["stdin"], "subprocess.DEVNULL")
        self.assertEqual(base["command_wrapper"], ["env", "-i"])
        self.assertIn("perl", base["runtime_versions"])
        self.assertIn("python", base["runtime_versions"])
        self.assertIn("compiler", base["runtime_versions"])
        for tool in ("geninfo", "lcov", "perl2lcov", "llvm2lcov", "py2lcov", "xml2lcov"):
            self.assertEqual(base["executables"][tool]["availability"], "available")
            self.assertTrue(
                str(base["executables"][tool]["sha256"]).startswith("sha256:")
            )
        for entry in wave1:
            self.assertEqual(entry["stdin"], "subprocess.DEVNULL")
            manifest = entry["execution_manifest"]
            self.assertEqual(manifest["locale"], "C")
            self.assertEqual(manifest["timezone"], "UTC")
            self.assertEqual(
                manifest["invoked_command"], entry["argv"][0]
            )
            self.assertEqual(
                manifest["invoked_executable"]["sha256"],
                base["executables"][entry["argv"][0]]["sha256"],
            )


    def test_wave2_observation_count_and_planned_ids_are_bound(self) -> None:
        wave2 = [
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave2:")
        ]
        self.assertEqual(len(wave2), contract.WAVE2_EXPECTED_CASE_COUNT)
        self.assertEqual(self.committed["totals"]["wave2_observations"], 32)
        self.assertEqual(self.committed["totals"]["oracle_observations"], 206)
        planned = []
        for entry in wave2:
            for planned_id in entry["planned_case_ids"]:
                if planned_id not in planned:
                    planned.append(planned_id)
        self.assertEqual(planned, contract.WAVE2_EXPECTED_PLANNED_IDS)
        self.assertEqual(len(planned), 30)

    def test_writer_transport_diagnostics_are_retained_as_oracle_references(self) -> None:
        expected_ids = {
            "tracefile:gzip-corrupt.summary",
            "tracefile:gzip-empty.summary",
            "tracefile:gzip-valid.missing-gzip",
            "tracefile:writer-legacy-unknown.summary",
            "tracefile:writer-legacy-unknown.canonical",
        }
        observations = {
            entry["id"]: entry
            for entry in self.committed["oracle_observations"]
            if entry["id"] in expected_ids
        }
        self.assertEqual(set(observations), expected_ids)
        for observation in observations.values():
            self.assertEqual(observation["kind"], "named_error_fatal")
            self.assertEqual(observation["exit_status"], 1)
            self.assertEqual(
                observation["planned_case_ids"], ["DIAG-IGNORE-ERROR-001"]
            )
        self.assertEqual(
            self.committed["totals"]["named_error_fatal_observations"], 84
        )

    def test_wave2_product_promotion_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["product_compatibility_evidence"] = True
        with self.assertRaises(contract.DiagnosticsContractError):
            self.validate(document)

    def test_wave2_raw_stdout_refresh_is_rejected(self) -> None:
        path = (
            contract.WAVE2_ROOT
            / "cases"
            / "diag-registry-branch-accept"
            / "reference"
            / "stdout.bin"
        )
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n#mutated\n")
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "stdout hash drift|Oracle observation identity drift|retained diagnostics artifact drift|wave2",
            ):
                self.validate(copy.deepcopy(self.committed))
        finally:
            path.write_bytes(original)

    def test_wave2_raw_stderr_refresh_is_rejected(self) -> None:
        path = (
            contract.WAVE2_ROOT
            / "cases"
            / "diag-ignore-prefix-posix-lcov"
            / "reference"
            / "stderr.bin"
        )
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n#mutated\n")
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "stderr hash drift|Oracle observation identity drift|retained diagnostics artifact drift|wave2",
            ):
                self.validate(copy.deepcopy(self.committed))
        finally:
            path.write_bytes(original)

    def test_wave2_identity_swap_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        wave2 = [
            entry
            for entry in document["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave2:")
        ]
        # Swap distinct non-empty stderr hashes when available; otherwise swap exits.
        candidates = [
            entry for entry in wave2 if entry["stderr_sha256"] != ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        ]
        if len(candidates) >= 2 and candidates[0]["stderr_sha256"] != candidates[1]["stderr_sha256"]:
            first, second = candidates[0], candidates[1]
            first["stderr_sha256"], second["stderr_sha256"] = (
                second["stderr_sha256"],
                first["stderr_sha256"],
            )
        else:
            first, second = wave2[0], wave2[1]
            first["exit_status"], second["exit_status"] = (
                second["exit_status"],
                first["exit_status"],
            )
        with self.assertRaisesRegex(
            contract.DiagnosticsContractError,
            "Oracle observation identity drift",
        ):
            self.validate(document)

    def test_wave2_ferricov_planned_ids_remain_unbound(self) -> None:
        ferricov = [
            planned_id
            for planned_id in self.committed["planned_case_ids"]
            if planned_id.endswith("-FERRICOV-001")
        ]
        self.assertGreaterEqual(len(ferricov), 3)
        bound = {
            planned_id
            for entry in self.committed["oracle_observations"]
            for planned_id in entry.get("planned_case_ids", [])
        }
        for planned_id in ferricov:
            self.assertNotIn(planned_id, bound)

    def test_wave2_execution_manifest_provenance_is_bound(self) -> None:
        wave2 = [
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave2:")
        ]
        self.assertEqual(len(wave2), 32)
        base = contract.WAVE2_EXECUTION_MANIFEST_BASE
        for entry in wave2:
            manifest = entry["execution_manifest"]
            self.assertEqual(manifest["image"], contract.WAVE2_PINNED_IMAGE)
            self.assertEqual(manifest["upstream_commit"], contract.UPSTREAM_COMMIT)
            self.assertEqual(manifest["locale"], "C")
            self.assertEqual(manifest["timezone"], "UTC")
            self.assertEqual(manifest["stdin"], contract.WAVE2_STDIN)
            self.assertEqual(manifest["command_wrapper"], ["env", "-i"])
            self.assertEqual(
                manifest["runtime_versions"], base["runtime_versions"]
            )
            self.assertEqual(
                manifest["package_availability"], base["package_availability"]
            )
            command = entry["argv"][0]
            self.assertEqual(manifest["invoked_command"], command)
            self.assertEqual(
                manifest["invoked_executable"]["sha256"],
                base["executables"][command]["sha256"],
            )

    def test_wave2_cleanup_and_environment_are_bound_independently(self) -> None:
        wave2 = [
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"].startswith("diagnostics-wave2:")
        ]
        self.assertEqual(len(wave2), 32)
        for entry in wave2:
            self.assertEqual(entry["cleanup"], contract.WAVE2_CLEANUP)
            self.assertEqual(entry["stdin"], contract.WAVE2_STDIN)
            self.assertTrue(entry["cleanup_outcome"]["container_absent"])
            self.assertTrue(entry["cleanup_outcome"]["direct_child_reaped"])
            self.assertIsNone(entry["cleanup_outcome"]["process_group_empty"])
            self.assertFalse(
                entry["environment_policy"]["inherits_host_environment"]
            )
            self.assertEqual(
                entry["environment_policy"]["command_wrapper"], ["env", "-i"]
            )




    def test_wave2_emptyhome_fixture_is_git_reproducible(self) -> None:
        """Empty-directory fixtures must survive clean Git checkouts.

        Git does not track empty directories. wave2 retains emptyhome via a
        zero-byte emptyhome/.gitkeep marker that is the only excluded path, so a
        clean tree without preexisting empty dirs still validates. Capture
        staging must still present a truly empty runtime HOME directory.
        """
        import tempfile

        fixture_dir = contract.WAVE2_ROOT / "fixtures" / "emptyhome"
        self.assertTrue(fixture_dir.is_dir(), "emptyhome fixture directory missing")
        marker = fixture_dir / ".gitkeep"
        self.assertTrue(
            marker.is_file(),
            "emptyhome must be retained with tracked .gitkeep marker",
        )
        self.assertFalse(marker.is_symlink())
        self.assertEqual(marker.read_bytes(), b"")
        # Marker is not part of Oracle fixture content bindings.
        bindings = contract.wave2_fixture_bindings(["emptyhome"])
        self.assertEqual(bindings, [])
        # Case bindings still list emptyhome as a staged fixture name.
        expected = contract.WAVE2_EXPECTED_CASE_BY_ID["diag-env-lcov-home"]
        self.assertIn("emptyhome", expected["fixtures"])
        # Staging removes the Git marker so runtime HOME is empty.
        with tempfile.TemporaryDirectory(prefix="wave2-stage-emptyhome-") as tmp:
            work = Path(tmp) / "work"
            contract.stage_wave2_fixtures(work, expected["fixtures"])
            staged = work / "emptyhome"
            self.assertTrue(staged.is_dir())
            self.assertEqual(list(staged.iterdir()), [])
            self.assertFalse((staged / ".gitkeep").exists())
        # Document still binds wave2 observation for the empty-home case.
        wave2 = [
            entry
            for entry in self.committed["oracle_observations"]
            if entry["id"] == "diagnostics-wave2:diag-env-lcov-home"
        ]
        self.assertEqual(len(wave2), 1)
        self.assertIn("emptyhome", wave2[0]["fixtures"])

    def test_wave2_missing_emptyhome_fixture_is_rejected(self) -> None:
        """Missing emptyhome fixture directory fails closed (clean checkout without marker)."""
        import shutil
        import tempfile

        fixture_dir = contract.WAVE2_ROOT / "fixtures" / "emptyhome"
        self.assertTrue(fixture_dir.is_dir())
        # Simulate a clean tree where Git dropped the empty directory entirely.
        with tempfile.TemporaryDirectory(prefix="emptyhome-backup-") as tmp:
            backup = Path(tmp) / "emptyhome"
            shutil.copytree(fixture_dir, backup)
            shutil.rmtree(fixture_dir)
            try:
                with self.assertRaisesRegex(
                    contract.DiagnosticsContractError,
                    "missing wave2 fixture: emptyhome",
                ):
                    contract.wave2_fixture_bindings(["emptyhome"])
            finally:
                shutil.copytree(backup, fixture_dir)

    def test_wave2_nonzero_emptyhome_marker_is_rejected(self) -> None:
        """Nonzero emptyhome/.gitkeep content must not be silently ignored."""
        marker = contract.WAVE2_ROOT / "fixtures" / "emptyhome" / ".gitkeep"
        original = marker.read_bytes()
        try:
            marker.write_bytes(b"not-empty\n")
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "emptyhome/.gitkeep must be zero bytes",
            ):
                contract.wave2_fixture_bindings(["emptyhome"])
        finally:
            marker.write_bytes(original)

    def test_wave2_renamed_emptyhome_marker_is_rejected(self) -> None:
        """`.keep` is not an accepted emptyhome marker and fails closed."""
        fixture_dir = contract.WAVE2_ROOT / "fixtures" / "emptyhome"
        keep = fixture_dir / ".keep"
        try:
            keep.write_bytes(b"")
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                r"emptyhome fixture must contain only \.gitkeep|directory marker only allowed as zero-byte emptyhome/\.gitkeep",
            ):
                contract.wave2_fixture_bindings(["emptyhome"])
        finally:
            if keep.exists() or keep.is_symlink():
                keep.unlink()

    def test_wave2_wrong_location_marker_is_rejected(self) -> None:
        """Markers outside emptyhome must not be excluded from fixture hashes."""
        foreign = contract.WAVE2_ROOT / "fixtures" / "lcovhome" / ".gitkeep"
        try:
            foreign.write_bytes(b"")
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "directory marker only allowed as zero-byte emptyhome/.gitkeep",
            ):
                contract.wave2_fixture_bindings(["lcovhome"])
            case_dir = contract.WAVE2_ROOT / "cases" / "diag-env-lcov-home"
            case_foreign = case_dir / "lcovhome" / ".gitkeep"
            case_foreign.parent.mkdir(parents=True, exist_ok=True)
            try:
                case_foreign.write_bytes(b"")
                with self.assertRaisesRegex(
                    contract.DiagnosticsContractError,
                    "directory marker only allowed as zero-byte emptyhome/.gitkeep",
                ):
                    contract.recompute_wave2_file_tree(case_dir)
            finally:
                if case_foreign.exists() or case_foreign.is_symlink():
                    case_foreign.unlink()
        finally:
            if foreign.exists() or foreign.is_symlink():
                foreign.unlink()

    def test_wave2_symlink_emptyhome_marker_is_rejected(self) -> None:
        """Exact-path symlink markers must not bypass emptyhome validation."""
        import os
        import tempfile

        fixture_dir = contract.WAVE2_ROOT / "fixtures" / "emptyhome"
        marker = fixture_dir / ".gitkeep"
        original = marker.read_bytes()
        target = fixture_dir / "target-bytes"
        try:
            marker.unlink()
            target.write_bytes(b"")
            os.symlink(target.name, marker)
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "emptyhome/.gitkeep must not be a symlink",
            ):
                contract.wave2_fixture_bindings(["emptyhome"])
            with tempfile.TemporaryDirectory(prefix="wave2-stage-symlink-") as tmp:
                with self.assertRaisesRegex(
                    contract.DiagnosticsContractError,
                    "emptyhome/.gitkeep must not be a symlink",
                ):
                    contract.stage_wave2_fixtures(Path(tmp) / "work", ["emptyhome"])
        finally:
            if marker.is_symlink() or marker.exists():
                marker.unlink()
            if target.exists():
                target.unlink()
            marker.write_bytes(original)

    def test_wave2_broken_symlink_emptyhome_marker_is_rejected(self) -> None:
        """Broken symlink markers must fail closed before is_file filtering."""
        import os

        fixture_dir = contract.WAVE2_ROOT / "fixtures" / "emptyhome"
        marker = fixture_dir / ".gitkeep"
        original = marker.read_bytes()
        try:
            marker.unlink()
            os.symlink("missing-target-does-not-exist", marker)
            self.assertTrue(marker.is_symlink())
            self.assertFalse(marker.exists())
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "emptyhome/.gitkeep must not be a symlink",
            ):
                contract.wave2_fixture_bindings(["emptyhome"])
        finally:
            if marker.is_symlink() or marker.exists():
                marker.unlink()
            marker.write_bytes(original)

    def test_wave2_wrong_location_symlink_marker_is_rejected(self) -> None:
        """Symlink markers outside emptyhome fail closed rather than being skipped."""
        import os

        foreign = contract.WAVE2_ROOT / "fixtures" / "lcovhome" / ".gitkeep"
        try:
            if foreign.exists() or foreign.is_symlink():
                foreign.unlink()
            os.symlink("somewhere", foreign)
            with self.assertRaisesRegex(
                contract.DiagnosticsContractError,
                "directory marker only allowed as zero-byte emptyhome/.gitkeep",
            ):
                contract.wave2_fixture_bindings(["lcovhome"])
        finally:
            if foreign.exists() or foreign.is_symlink():
                foreign.unlink()

    def test_wave2_capture_stage_emptyhome_runtime_is_empty(self) -> None:
        """Capture stage parity: emptyhome runtime dir has zero entries."""
        import importlib.util
        import tempfile

        capture_path = (
            contract.WAVE2_ROOT / "scripts" / "capture_wave2.py"
        ).resolve()
        spec = importlib.util.spec_from_file_location(
            "capture_wave2_stage_test", capture_path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        expected = contract.WAVE2_EXPECTED_CASE_BY_ID["diag-env-lcov-home"]
        with tempfile.TemporaryDirectory(prefix="wave2-capture-stage-") as tmp:
            work = Path(tmp) / "work"
            module.stage(work, expected["fixtures"], None)
            staged = work / "emptyhome"
            self.assertTrue(staged.is_dir())
            self.assertEqual(list(staged.iterdir()), [])
            self.assertFalse((staged / ".gitkeep").exists())
            # Capture fixture bindings also exclude the marker.
            self.assertEqual(module.fixture_bindings(["emptyhome"]), [])

    def _load_wave2_capture_module(self):
        import importlib.util

        capture_path = (
            contract.WAVE2_ROOT / "scripts" / "capture_wave2.py"
        ).resolve()
        spec = importlib.util.spec_from_file_location(
            "capture_wave2_preflight_test", capture_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load wave2 capture module")
        module = importlib.util.module_from_spec(spec)
        # Avoid executing main; load module body only.
        spec.loader.exec_module(module)
        return module

    def test_wave2_capture_preflight_accepts_tracked_emptyhome(self) -> None:
        """Clean checkout with tracked emptyhome/.gitkeep passes capture preflight."""
        module = self._load_wave2_capture_module()
        fixture_dir = module.FIXTURES / "emptyhome"
        marker = fixture_dir / ".gitkeep"
        self.assertTrue(fixture_dir.is_dir())
        self.assertTrue(marker.is_file())
        self.assertFalse(marker.is_symlink())
        self.assertEqual(marker.read_bytes(), b"")
        # Preflight must validate preexisting tracked evidence only.
        module.require_tracked_emptyhome_fixture()

    def test_wave2_capture_main_rejects_missing_emptyhome_dir(self) -> None:
        """Capture main fails before Docker when emptyhome fixture dir is absent."""
        import shutil
        import tempfile
        from unittest.mock import patch

        module = self._load_wave2_capture_module()
        fixture_dir = module.FIXTURES / "emptyhome"
        self.assertTrue(fixture_dir.is_dir())
        with tempfile.TemporaryDirectory(prefix="emptyhome-main-dir-") as tmp:
            backup = Path(tmp) / "emptyhome"
            shutil.copytree(fixture_dir, backup)
            shutil.rmtree(fixture_dir)
            try:
                with patch.object(
                    module, "probe_effective_command_environment"
                ) as probe_env, patch.object(
                    module, "probe_execution_manifest"
                ) as probe_manifest, patch.object(
                    module, "run_case"
                ) as run_case:
                    with self.assertRaises(SystemExit) as raised:
                        module.main()
                    self.assertRegex(
                        str(raised.exception),
                        r"emptyhome fixture missing directory|missing \.gitkeep",
                    )
                    probe_env.assert_not_called()
                    probe_manifest.assert_not_called()
                    run_case.assert_not_called()
            finally:
                if not fixture_dir.exists():
                    shutil.copytree(backup, fixture_dir)

    def test_wave2_capture_main_rejects_missing_emptyhome_marker(self) -> None:
        """Capture main fails before Docker when tracked .gitkeep is absent."""
        import shutil
        import tempfile
        from unittest.mock import patch

        module = self._load_wave2_capture_module()
        fixture_dir = module.FIXTURES / "emptyhome"
        marker = fixture_dir / ".gitkeep"
        self.assertTrue(marker.is_file())
        with tempfile.TemporaryDirectory(prefix="emptyhome-main-marker-") as tmp:
            backup = Path(tmp) / ".gitkeep"
            shutil.copy2(marker, backup)
            marker.unlink()
            try:
                with patch.object(
                    module, "probe_effective_command_environment"
                ) as probe_env, patch.object(
                    module, "probe_execution_manifest"
                ) as probe_manifest, patch.object(
                    module, "run_case"
                ) as run_case:
                    with self.assertRaises(SystemExit) as raised:
                        module.main()
                    self.assertIn("missing .gitkeep", str(raised.exception))
                    probe_env.assert_not_called()
                    probe_manifest.assert_not_called()
                    run_case.assert_not_called()
                    # Entrypoint must not recreate the marker.
                    self.assertFalse(marker.exists())
                    self.assertFalse(marker.is_symlink())
            finally:
                if not marker.exists():
                    shutil.copy2(backup, marker)


if __name__ == "__main__":
    unittest.main()
