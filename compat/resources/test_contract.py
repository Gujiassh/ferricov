from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


RESOURCE_ROOT = Path(__file__).resolve().parent
if str(RESOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(RESOURCE_ROOT))

import capture  # noqa: E402
import contract  # noqa: E402
import generate  # noqa: E402
import validate  # noqa: E402


RESULT_PATH = RESOURCE_ROOT / "results/oracle-x86_64-linux-20260729/result.json"


def measurement_evidence_directory(arguments: list[str]) -> Path:
    for index, argument in enumerate(arguments):
        if argument == "--volume" and arguments[index + 1].endswith(":/evidence"):
            return Path(arguments[index + 1].removesuffix(":/evidence"))
    raise AssertionError("Docker command has no evidence mount")


def write_measurement_artifacts(
    directory: Path,
    *,
    exit_code: int | None,
    signal: int | None,
    stdout: bytes = b"",
    stderr: bytes = b"",
) -> None:
    metrics = {
        "schema_version": 1,
        "measurement_backend": "linux-rusage-children-v1",
        "clock": "monotonic",
        "wall_time_ns": 1,
        "user_cpu_time_ns": 0,
        "system_cpu_time_ns": 0,
        "peak_rss_bytes": 1,
        "exit_code": exit_code,
        "signal": signal,
    }
    (directory / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="ascii",
    )
    (directory / "stdout.bin").write_bytes(stdout)
    (directory / "stderr.bin").write_bytes(stderr)


class ResourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generated = contract.build_document()
        cls.committed = contract.load_json(contract.OUTPUT_PATH)
        cls.result = validate.load_json(RESULT_PATH)

    def validate_contract(self, document: dict[str, Any]) -> None:
        contract.validate_document(document)

    def validate_result(self, document: dict[str, Any], path: Path = RESULT_PATH) -> None:
        validate.validate_result(document, path)

    def copied_result(self, directory: str) -> tuple[Path, dict[str, Any]]:
        result_root = Path(directory) / "result"
        shutil.copytree(RESULT_PATH.parent, result_root)
        result_path = result_root / "result.json"
        return result_path, validate.load_json(result_path)

    def write_result(self, path: Path, document: dict[str, Any]) -> None:
        path.write_text(contract.canonical_json(document), encoding="ascii")

    def test_committed_contract_matches_generation(self) -> None:
        self.validate_contract(self.committed)
        self.assertEqual(contract.canonical_json(self.committed), contract.canonical_json(self.generated))

    def test_generator_counts_source_scoped_line_points(self) -> None:
        profile = {"id": "sections-test", "axis": "sections", "target": 2}
        with tempfile.TemporaryDirectory() as directory:
            shape = generate.generate_and_analyze(profile, Path(directory) / "input.info")
        self.assertEqual(shape["section_count"], 2)
        self.assertEqual(shape["family_cardinalities"]["line"], 2)

    def test_expected_stdout_semantics_cover_every_profile(self) -> None:
        for profile in generate.PROFILES:
            with self.subTest(profile=profile["id"]):
                self.assertEqual(
                    validate.parse_summary(generate.expected_stdout(profile)),
                    generate.expected_summary(profile),
                )
        cardinality = generate.expected_summary(generate.PROFILE_BY_ID["cardinality-1"])
        self.assertEqual(cardinality["condition_outcomes_found"], 2)
        self.assertEqual(cardinality["condition_outcomes_hit"], 1)

    def test_harness_closure_includes_contract_and_both_schemas(self) -> None:
        paths = {path.relative_to(contract.ROOT).as_posix() for path in contract.HARNESS_PATHS}
        self.assertIn("compat/resources/contract.py", paths)
        self.assertIn("compat/schema/resource-contract.schema.json", paths)
        self.assertIn("compat/schema/resource-result.schema.json", paths)
        self.assertEqual(len(paths), 6)
        self.assertEqual(
            self.committed["execution_policy"]["deadline_observer"],
            "host_subprocess_timeout",
        )
        self.assertNotIn("timeout_exit_code", self.committed["execution_policy"])

    def test_missing_profile_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["profiles"].pop()
        with self.assertRaises(contract.ResourceContractError):
            self.validate_contract(document)

    def test_profile_order_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["profiles"][0], document["profiles"][1] = document["profiles"][1], document["profiles"][0]
        with self.assertRaisesRegex(contract.ResourceContractError, "profiles"):
            self.validate_contract(document)

    def test_profile_target_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["profiles"][0]["target"] += 1
        with self.assertRaisesRegex(contract.ResourceContractError, "profiles"):
            self.validate_contract(document)

    def test_expected_outcome_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["profiles"][0]["expected_observation"]["outcome"]["exit_code"] = 1
        with self.assertRaises(contract.ResourceContractError):
            self.validate_contract(document)

    def test_expected_stream_hash_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["profiles"][0]["expected_observation"]["stdout"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.ResourceContractError, "profiles"):
            self.validate_contract(document)

    def test_generated_input_hash_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["profiles"][0]["input"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.ResourceContractError, "profiles"):
            self.validate_contract(document)

    def test_source_section_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["source_sections"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.ResourceContractError, "source_sections"):
            self.validate_contract(document)

    def test_oracle_identity_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["oracle_identity"]["image_sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(contract.ResourceContractError, "oracle_identity"):
            self.validate_contract(document)

    def test_blocked_case_removal_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["blocked_case_ids"].pop()
        with self.assertRaises(contract.ResourceContractError):
            self.validate_contract(document)

    def test_harness_budget_cannot_be_promoted_to_product_limit(self) -> None:
        document = copy.deepcopy(self.committed)
        document["harness_budgets_are_product_limits"] = True
        with self.assertRaises(contract.ResourceContractError):
            self.validate_contract(document)

    def test_product_limit_selection_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["product_limits_selected"] = True
        with self.assertRaises(contract.ResourceContractError):
            self.validate_contract(document)

    def test_allocation_observability_claim_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["execution_policy"]["allocations"]["status"] = "observed"
        with self.assertRaisesRegex(contract.ResourceContractError, "execution_policy"):
            self.validate_contract(document)

    def test_harness_artifact_identity_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.committed)
        document["harness_artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(contract.ResourceContractError, "harness_artifacts"):
            self.validate_contract(document)

    def test_retained_result_is_valid(self) -> None:
        self.validate_result(self.result)

    def test_result_extra_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, document = self.copied_result(directory)
            (path.parent / "extra.txt").write_text("unexpected", encoding="ascii")
            with self.assertRaisesRegex(validate.ResourceValidationError, "tree closure drift"):
                self.validate_result(document, path)

    def test_result_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, document = self.copied_result(directory)
            (path.parent / "extra-link").symlink_to("result.json")
            with self.assertRaisesRegex(validate.ResourceValidationError, "contains a symlink"):
                self.validate_result(document, path)

    def test_result_missing_profile_is_rejected(self) -> None:
        document = copy.deepcopy(self.result)
        document["samples"].pop()
        with self.assertRaises(validate.ResourceValidationError):
            self.validate_result(document)

    def test_result_profile_identity_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.result)
        document["samples"][0]["profile_id"] = "different-profile"
        with self.assertRaisesRegex(validate.ResourceValidationError, "profile drift"):
            self.validate_result(document)

    def test_result_input_mutation_is_rejected(self) -> None:
        document = copy.deepcopy(self.result)
        document["samples"][0]["input_sha256_after"] = "0" * 64
        with self.assertRaisesRegex(validate.ResourceValidationError, "input changed"):
            self.validate_result(document)

    def test_result_nonzero_outcome_is_rejected(self) -> None:
        document = copy.deepcopy(self.result)
        document["samples"][0]["outcome"]["exit_code"] = 1
        document["samples"][0]["outcome"]["container_exit_code"] = 1
        with self.assertRaises(validate.ResourceValidationError):
            self.validate_result(document)

    def test_coordinated_stdout_artifact_and_metadata_mutation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, document = self.copied_result(directory)
            sample = document["samples"][0]
            stdout = path.parent / sample["stdout"]["path"]
            stdout.write_bytes(stdout.read_bytes() + b"mutated\n")
            sample["stdout"] = {
                "path": sample["stdout"]["path"],
                "bytes": stdout.stat().st_size,
                "sha256": contract.sha256_file(stdout),
            }
            self.write_result(path, document)
            with self.assertRaisesRegex(validate.ResourceValidationError, "stdout differs"):
                self.validate_result(document, path)

    def test_result_metric_summary_mutation_is_rejected(self) -> None:
        document = copy.deepcopy(self.result)
        document["samples"][0]["metrics"]["wall_time_ns"] += 1
        with self.assertRaisesRegex(validate.ResourceValidationError, "differ from raw"):
            self.validate_result(document)

    def test_result_json_must_be_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, document = self.copied_result(directory)
            path.write_text(json.dumps(document, ensure_ascii=True, sort_keys=True, indent=4) + "\n", encoding="ascii")
            with self.assertRaisesRegex(validate.ResourceValidationError, "result JSON is not canonical"):
                self.validate_result(document, path)

    def test_result_raw_metric_artifact_mutation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, document = self.copied_result(directory)
            sample = document["samples"][0]
            raw_metrics = path.parent / sample["raw_metrics"]["path"]
            raw_metrics.write_bytes(raw_metrics.read_bytes() + b" ")
            self.write_result(path, document)
            with self.assertRaisesRegex(validate.ResourceValidationError, "artifact bytes drift"):
                self.validate_result(document, path)

    def test_raw_metrics_json_must_be_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, document = self.copied_result(directory)
            sample = document["samples"][0]
            raw_metrics = path.parent / sample["raw_metrics"]["path"]
            raw_document = validate.load_json(raw_metrics)
            raw_metrics.write_text(
                json.dumps(raw_document, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
                encoding="ascii",
            )
            sample["raw_metrics"] = {
                "path": sample["raw_metrics"]["path"],
                "bytes": raw_metrics.stat().st_size,
                "sha256": contract.sha256_file(raw_metrics),
            }
            self.write_result(path, document)
            with self.assertRaisesRegex(validate.ResourceValidationError, "raw metrics JSON is not canonical"):
                self.validate_result(document, path)

    def test_result_cleanup_claim_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.result)
        document["samples"][0]["cleanup"]["work_directory_removed"] = False
        with self.assertRaises(validate.ResourceValidationError):
            self.validate_result(document)

    def test_result_totals_are_exact(self) -> None:
        document = copy.deepcopy(self.result)
        document["totals"]["accepted"] = 12
        document["totals"]["nonzero"] = 1
        with self.assertRaises(validate.ResourceValidationError):
            self.validate_result(document)

    def test_result_host_runtime_is_schema_bound(self) -> None:
        document = copy.deepcopy(self.result)
        document["host_runtime"]["kernel_release"] = ""
        with self.assertRaises(validate.ResourceValidationError):
            self.validate_result(document)

    def test_result_product_limit_claim_is_rejected(self) -> None:
        document = copy.deepcopy(self.result)
        document["product_limits_selected"] = True
        with self.assertRaises(validate.ResourceValidationError):
            self.validate_result(document)

    def test_exit_124_retains_non_timeout_failure_evidence(self) -> None:
        profile = self.committed["profiles"][0]

        def exit_124(arguments: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            evidence = measurement_evidence_directory(arguments)
            write_measurement_artifacts(
                evidence,
                exit_code=124,
                signal=None,
                stdout=b"target exited before deadline\n",
            )
            return subprocess.CompletedProcess(arguments, 124, b"", b"")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with (
                mock.patch.object(capture.subprocess, "run", side_effect=exit_124),
                mock.patch.object(capture, "cleanup_container", return_value=True) as cleanup,
            ):
                with self.assertRaisesRegex(capture.ResourceCaptureError, "failure_evidence"):
                    capture.capture_profile(output, self.committed, profile)
            cleanup.assert_called_once()
            failure_path = output / "failures" / profile["id"] / "failure.json"
            failure = json.loads(failure_path.read_text(encoding="ascii"))
            self.assertEqual(failure_path.read_text(encoding="ascii"), capture.canonical_json(failure))
            self.assertEqual(failure["failure"]["class"], "oracle_nonzero_exit")
            self.assertFalse(failure["deadline"]["expired"])
            self.assertFalse(failure["docker"]["timed_out"])
            self.assertEqual(failure["docker"]["returncode"], 124)
            self.assertEqual(failure["measurement_outcome"]["exit_code"], 124)
            self.assertNotIn("/usr/bin/timeout", failure["docker"]["command"])
            generated = output / failure["artifacts"]["generated_input"]["path"]
            self.assertEqual(contract.sha256_file(generated), profile["input"]["sha256"])
            self.assertTrue(all(failure["post_cleanup"][key] for key in (
                "work_directory_removed", "evidence_directory_removed", "container_removed"
            )))

    def test_host_deadline_retains_timeout_failure_evidence(self) -> None:
        profile = self.committed["profiles"][0]

        def host_timeout(arguments: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            evidence = measurement_evidence_directory(arguments)
            (evidence / "stdout.bin").write_bytes(b"partial target stdout\n")
            (evidence / "stderr.bin").write_bytes(b"")
            raise subprocess.TimeoutExpired(
                arguments,
                self.committed["execution_policy"]["timeout_seconds"],
                output=b"partial docker stdout\n",
                stderr=b"partial docker stderr\n",
            )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with (
                mock.patch.object(capture.subprocess, "run", side_effect=host_timeout),
                mock.patch.object(capture, "cleanup_container", return_value=True) as cleanup,
            ):
                with self.assertRaisesRegex(capture.ResourceCaptureError, "failure_evidence"):
                    capture.capture_profile(output, self.committed, profile)
            cleanup.assert_called_once()
            failure_path = output / "failures" / profile["id"] / "failure.json"
            failure = json.loads(failure_path.read_text(encoding="ascii"))
            self.assertEqual(failure_path.read_text(encoding="ascii"), capture.canonical_json(failure))
            self.assertEqual(failure["failure"]["class"], "host_deadline_exceeded")
            self.assertEqual(failure["deadline"]["observer"], "host_subprocess_timeout")
            self.assertTrue(failure["deadline"]["expired"])
            self.assertTrue(failure["docker"]["timed_out"])
            self.assertIsNone(failure["docker"]["returncode"])
            self.assertIsNone(failure["measurement_outcome"])
            self.assertNotIn("raw_metrics", failure["artifacts"])
            self.assertIn("stdout", failure["artifacts"])
            docker_stderr = output / failure["artifacts"]["docker_stderr"]["path"]
            self.assertEqual(docker_stderr.read_bytes(), b"partial docker stderr\n")
            self.assertEqual(failure["post_cleanup"]["errors"], [])

    def test_signal_retains_canonical_failure_evidence(self) -> None:
        profile = self.committed["profiles"][0]

        def signal_9(arguments: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            evidence = measurement_evidence_directory(arguments)
            write_measurement_artifacts(
                evidence,
                exit_code=None,
                signal=9,
                stderr=b"terminated by signal\n",
            )
            return subprocess.CompletedProcess(arguments, 137, b"", b"")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with (
                mock.patch.object(capture.subprocess, "run", side_effect=signal_9),
                mock.patch.object(capture, "cleanup_container", return_value=True) as cleanup,
            ):
                with self.assertRaisesRegex(capture.ResourceCaptureError, "failure_evidence"):
                    capture.capture_profile(output, self.committed, profile)
            cleanup.assert_called_once()
            failure_path = output / "failures" / profile["id"] / "failure.json"
            failure = json.loads(failure_path.read_text(encoding="ascii"))
            self.assertEqual(
                failure_path.read_text(encoding="ascii"),
                capture.canonical_json(failure),
            )
            self.assertEqual(failure["failure"]["class"], "oracle_signal")
            self.assertFalse(failure["deadline"]["expired"])
            self.assertFalse(failure["docker"]["timed_out"])
            self.assertEqual(failure["docker"]["returncode"], 137)
            self.assertEqual(
                failure["measurement_outcome"],
                {"exit_code": None, "signal": 9},
            )
            self.assertIn("raw_metrics", failure["artifacts"])
            self.assertEqual(failure["post_cleanup"]["errors"], [])
            self.assertTrue(all(failure["post_cleanup"][key] for key in (
                "work_directory_removed", "evidence_directory_removed", "container_removed"
            )))
            self.assertFalse((output / "result.json").exists())
            self.assertFalse((output / "samples").exists())

    def test_failure_retention_error_cannot_bypass_cleanup(self) -> None:
        profile = self.committed["profiles"][0]
        created_directories: list[Path] = []

        def tracked_mkdtemp(*, prefix: str) -> str:
            path = test_root / f"{prefix}{len(created_directories)}"
            path.mkdir()
            created_directories.append(path)
            return str(path)

        def exit_7(arguments: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            evidence = measurement_evidence_directory(arguments)
            write_measurement_artifacts(
                evidence,
                exit_code=7,
                signal=None,
                stderr=b"target failure\n",
            )
            return subprocess.CompletedProcess(arguments, 7, b"", b"")

        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory)
            output = test_root / "output"
            output.mkdir()
            with (
                mock.patch.object(capture.tempfile, "mkdtemp", side_effect=tracked_mkdtemp),
                mock.patch.object(capture.subprocess, "run", side_effect=exit_7),
                mock.patch.object(capture, "cleanup_container", return_value=True) as cleanup,
                mock.patch.object(
                    capture,
                    "_failure_artifacts",
                    side_effect=OSError("output storage unavailable"),
                ),
            ):
                with self.assertRaises(capture.ResourceCaptureError) as raised:
                    capture.capture_profile(output, self.committed, profile)

            message = str(raised.exception)
            self.assertIn("resource Oracle exited nonzero", message)
            self.assertIn(
                "retention_failure: failure_artifacts: OSError: output storage unavailable",
                message,
            )
            self.assertIn("failure_evidence=not_retained", message)
            cleanup.assert_called_once()
            self.assertEqual(len(created_directories), 2)
            self.assertTrue(all(not path.exists() for path in created_directories))
            self.assertFalse((output / "result.json").exists())
            self.assertFalse((output / "samples").exists())
            self.assertFalse((output / "failures" / profile["id"] / "failure.json").exists())

    def test_combined_capture_retention_and_cleanup_errors_are_preserved(self) -> None:
        profile = self.committed["profiles"][0]
        created_directories: list[Path] = []

        def tracked_mkdtemp(*, prefix: str) -> str:
            path = test_root / f"{prefix}{len(created_directories)}"
            path.mkdir()
            created_directories.append(path)
            return str(path)

        def exit_7(arguments: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
            evidence = measurement_evidence_directory(arguments)
            write_measurement_artifacts(
                evidence,
                exit_code=7,
                signal=None,
                stderr=b"target failure\n",
            )
            return subprocess.CompletedProcess(arguments, 7, b"", b"")

        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory)
            output = test_root / "output"
            output.mkdir()
            with (
                mock.patch.object(capture.tempfile, "mkdtemp", side_effect=tracked_mkdtemp),
                mock.patch.object(capture.subprocess, "run", side_effect=exit_7),
                mock.patch.object(
                    capture,
                    "cleanup_container",
                    side_effect=capture.ResourceCaptureError("container cleanup unavailable"),
                ) as cleanup,
                mock.patch.object(
                    capture,
                    "_failure_artifacts",
                    side_effect=OSError("output storage unavailable"),
                ),
            ):
                with self.assertRaises(capture.ResourceCaptureError) as raised:
                    capture.capture_profile(output, self.committed, profile)

            message = str(raised.exception)
            self.assertIn(
                "capture_failure: ProfileCaptureFailure: resource Oracle exited nonzero",
                message,
            )
            self.assertIn(
                "retention_failure: failure_artifacts: OSError: output storage unavailable",
                message,
            )
            self.assertIn(
                "cleanup_failure: container: ResourceCaptureError: container cleanup unavailable",
                message,
            )
            self.assertIn("failure_evidence=not_retained", message)
            cleanup.assert_called_once()
            self.assertEqual(len(created_directories), 2)
            self.assertTrue(all(not path.exists() for path in created_directories))
            self.assertFalse((output / "result.json").exists())
            self.assertFalse((output / "samples").exists())
            self.assertFalse((output / "failures" / profile["id"] / "failure.json").exists())

    def test_container_observer_failure_is_not_absence(self) -> None:
        with mock.patch.object(capture, "run_checked", side_effect=capture.ResourceCaptureError("observer failed")):
            with self.assertRaisesRegex(capture.ResourceCaptureError, "observer failed"):
                capture.container_absent("resource-container")

    def test_container_absence_uses_exact_name(self) -> None:
        observed = subprocess.CompletedProcess([], 0, b"other\nresource-container-peer\n", b"")
        with mock.patch.object(capture, "run_checked", return_value=observed):
            self.assertTrue(capture.container_absent("resource-container"))

    def test_cleanup_removes_observed_container(self) -> None:
        removed = subprocess.CompletedProcess([], 0, b"", b"")
        with (
            mock.patch.object(capture, "container_absent", side_effect=[False, True]),
            mock.patch.object(capture.subprocess, "run", return_value=removed),
        ):
            self.assertTrue(capture.cleanup_container("resource-container"))

    def test_capture_requires_a_fresh_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "existing").write_text("occupied", encoding="ascii")
            with self.assertRaisesRegex(capture.ResourceCaptureError, "not empty"):
                capture.require_empty_output(root)


if __name__ == "__main__":
    unittest.main()
