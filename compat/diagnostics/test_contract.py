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
        self.assertEqual(self.committed["totals"]["oracle_observations"], 169)
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


if __name__ == "__main__":
    unittest.main()
