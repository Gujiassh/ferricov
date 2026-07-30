from __future__ import annotations

import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock


RESOURCE_ROOT = Path(__file__).resolve().parent
if str(RESOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(RESOURCE_ROOT))

import capture  # noqa: E402
import contract  # noqa: E402
import exercise  # noqa: E402
import validate  # noqa: E402


RESULT_ROOT = RESOURCE_ROOT / "results/oracle-x86_64-linux-20260729"
RESULT_PATH = RESULT_ROOT / "result.json"
REBUILT_IMAGE_ID = "sha256:" + "1" * 64
REBUILT_IMAGE_REFERENCE = "ferricov/lcov-oracle:v2.5"


class ResourceExerciseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_document = contract.load_json(contract.OUTPUT_PATH)
        cls.result_document = validate.load_json(RESULT_PATH)

    def populate_samples(self, output_root: Path) -> list[dict[str, Any]]:
        output_root.mkdir()
        shutil.copytree(RESULT_ROOT / "samples", output_root / "samples")
        return copy.deepcopy(self.result_document["samples"])

    def test_mutable_tag_resolves_once_and_profiles_use_immutable_id(self) -> None:
        observed_profile_ids: list[str] = []
        observed_identity_ids: list[str] = []
        sample_by_id = {
            sample["profile_id"]: sample
            for sample in self.result_document["samples"]
        }

        def verify_identity(document: dict[str, Any]) -> None:
            observed_identity_ids.append(document["oracle_identity"]["image_sha256"])

        def capture_profile(
            output_root: Path,
            document: dict[str, Any],
            profile: dict[str, Any],
        ) -> dict[str, Any]:
            self.assertEqual(document["oracle_identity"]["image_sha256"], REBUILT_IMAGE_ID)
            observed_profile_ids.append(profile["id"])
            source = RESULT_ROOT / "samples" / profile["id"]
            destination = output_root / "samples" / profile["id"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination)
            return copy.deepcopy(sample_by_id[profile["id"]])

        inspected = subprocess.CompletedProcess(
            [],
            0,
            f"{REBUILT_IMAGE_ID}\n".encode("ascii"),
            b"",
        )
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "exercise"
            stdout = io.StringIO()
            with (
                mock.patch.object(capture, "run_checked", return_value=inspected) as inspect,
                mock.patch.object(capture, "verify_runtime_identity", side_effect=verify_identity),
                mock.patch.object(capture, "capture_profile", side_effect=capture_profile),
                redirect_stdout(stdout),
            ):
                status = exercise.main([
                    "--image",
                    REBUILT_IMAGE_REFERENCE,
                    "--output",
                    str(output_root),
                ])

            self.assertEqual(status, 0)
            inspect.assert_called_once_with([
                "docker",
                "image",
                "inspect",
                "--format",
                "{{.Id}}",
                REBUILT_IMAGE_REFERENCE,
            ])
            self.assertEqual(observed_identity_ids, [REBUILT_IMAGE_ID])
            self.assertEqual(
                observed_profile_ids,
                [profile["id"] for profile in self.contract_document["profiles"]],
            )
            self.assertFalse((output_root / "result.json").exists())
            self.assertEqual(
                stdout.getvalue().strip(),
                "REBUILD_RESOURCE_EXERCISE_OK "
                f"image={REBUILT_IMAGE_ID} profiles=13 "
                "product_limits=false product_compatibility=false",
            )
        self.assertEqual(
            contract.load_json(contract.OUTPUT_PATH)["oracle_identity"]["image_sha256"],
            contract.EXPECTED_IMAGE_SHA256,
        )

    def test_lcov_mismatch_fails_closed_before_profile_execution(self) -> None:
        wrong_lcov = "0" * 64
        responses = [
            subprocess.CompletedProcess([], 0, f"{REBUILT_IMAGE_ID}\n".encode("ascii"), b""),
            subprocess.CompletedProcess([], 0, f"{REBUILT_IMAGE_ID}\n".encode("ascii"), b""),
            subprocess.CompletedProcess([], 0, f"{wrong_lcov}  /usr/local/bin/lcov\n".encode("ascii"), b""),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "exercise"
            with (
                mock.patch.object(capture, "run_checked", side_effect=responses) as checked,
                mock.patch.object(capture, "capture_profile") as capture_profile,
            ):
                with self.assertRaisesRegex(capture.ResourceCaptureError, "lcov executable identity drift"):
                    exercise.exercise(REBUILT_IMAGE_REFERENCE, output_root)
            self.assertEqual(checked.call_count, 3)
            capture_profile.assert_not_called()
            self.assertFalse((output_root / "result.json").exists())

    def test_nonempty_output_is_rejected_before_image_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "exercise"
            output_root.mkdir()
            (output_root / "occupied").write_text("existing", encoding="ascii")
            with mock.patch.object(exercise, "resolve_image_reference") as resolve:
                with self.assertRaisesRegex(capture.ResourceCaptureError, "not empty"):
                    exercise.exercise(REBUILT_IMAGE_REFERENCE, output_root)
            resolve.assert_not_called()

    def test_main_rejects_symlink_output_before_resolution_or_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            output_root = root / "exercise"
            output_root.symlink_to(target, target_is_directory=True)
            with (
                mock.patch.object(exercise, "resolve_image_reference") as resolve,
                mock.patch.object(capture, "capture_profile") as capture_profile,
            ):
                with self.assertRaisesRegex(exercise.ResourceExerciseError, "symlink"):
                    exercise.main([
                        "--image",
                        REBUILT_IMAGE_REFERENCE,
                        "--output",
                        str(output_root),
                    ])
            resolve.assert_not_called()
            capture_profile.assert_not_called()

    def test_extra_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "exercise"
            samples = self.populate_samples(output_root)
            (output_root / "extra.txt").write_text("unexpected", encoding="ascii")
            with self.assertRaisesRegex(exercise.ResourceExerciseError, "tree closure drift"):
                exercise.validate_exercise(
                    samples,
                    self.contract_document["profiles"],
                    output_root,
                )

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "exercise"
            samples = self.populate_samples(output_root)
            (output_root / "extra-link").symlink_to("samples")
            with self.assertRaisesRegex(exercise.ResourceExerciseError, "contains a symlink"):
                exercise.validate_exercise(
                    samples,
                    self.contract_document["profiles"],
                    output_root,
                )

    def test_metric_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "exercise"
            samples = self.populate_samples(output_root)
            samples[0]["metrics"]["wall_time_ns"] += 1
            with self.assertRaisesRegex(validate.ResourceValidationError, "differ from raw"):
                exercise.validate_exercise(
                    samples,
                    self.contract_document["profiles"],
                    output_root,
                )

    def test_sample_schema_errors_are_sorted_by_dotted_path(self) -> None:
        ordered = copy.deepcopy(self.result_document["samples"][0])
        ordered["metrics"]["wall_time_ns"] = -1
        ordered["metrics"]["peak_rss_bytes"] = 0
        with self.assertRaisesRegex(
            exercise.ResourceExerciseError,
            r"sample schema failure at metrics\.peak_rss_bytes:",
        ):
            exercise.validate_sample(
                ordered,
                self.contract_document["profiles"][0],
                Path("unused"),
                self.contract_document["measurement_tool"],
                exercise.sample_validator(),
            )

        mutations = (
            ("sequence", ("sequence",), True, r"sequence:"),
            ("target", ("target",), True, r"target:"),
            ("generator_version", ("generator_version",), True, r"generator_version:"),
            ("input_section_count", ("input", "section_count"), True, r"input\.section_count:"),
            ("outcome_exit_code", ("outcome", "exit_code"), True, r"outcome:"),
            (
                "cleanup_integer",
                ("cleanup", "work_directory_removed"),
                1,
                r"cleanup\.work_directory_removed:",
            ),
            ("wall_time_zero", ("metrics", "wall_time_ns"), 0, r"metrics\.wall_time_ns:"),
            (
                "sample_cpu_boolean",
                ("metrics", "user_cpu_time_ns"),
                True,
                r"metrics\.user_cpu_time_ns:",
            ),
        )
        validator = exercise.sample_validator()
        for label, path, value, error_path in mutations:
            with self.subTest(label=label):
                sample = copy.deepcopy(self.result_document["samples"][0])
                target: dict[str, Any] = sample
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaisesRegex(
                    exercise.ResourceExerciseError,
                    rf"sample schema failure at {error_path}",
                ):
                    exercise.validate_sample_schema(sample, validator)

    def test_artifact_descriptor_extra_keys_are_rejected(self) -> None:
        mutations = (
            ("raw_metrics_extra", "raw_metrics", "extra", "invalid"),
            ("raw_metrics_path_type", "raw_metrics", "path", 1),
            ("stdout_bytes_boolean", "stdout", "bytes", True),
            ("stderr_digest_type", "stderr", "sha256", 1),
            ("stderr_digest_pattern", "stderr", "sha256", "not-a-digest"),
        )
        for label, role, key, value in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                output_root = Path(directory) / "exercise"
                samples = self.populate_samples(output_root)
                samples[0][role][key] = value
                with self.assertRaisesRegex(
                    exercise.ResourceExerciseError,
                    rf"sample schema failure at {role}",
                ):
                    exercise.validate_exercise(
                        samples,
                        self.contract_document["profiles"],
                        output_root,
                    )

    def test_coherent_invalid_raw_metrics_are_rejected(self) -> None:
        mutations = (
            ("schema_version", 2, "raw metrics schema drift"),
            ("measurement_backend", "invalid-backend", r"metrics\.measurement_backend"),
            ("clock", "invalid-clock", r"metrics\.clock"),
            ("wall_time_ns", -1, r"metrics\.wall_time_ns"),
            ("wall_time_ns", 0, r"metrics\.wall_time_ns"),
            ("user_cpu_time_ns", -1, r"metrics\.user_cpu_time_ns"),
            ("system_cpu_time_ns", -1, r"metrics\.system_cpu_time_ns"),
            ("peak_rss_bytes", 0, r"metrics\.peak_rss_bytes"),
            ("extra_metric", 1, "raw metrics keys drift"),
        )
        for key, value, error_text in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                output_root = Path(directory) / "exercise"
                samples = self.populate_samples(output_root)
                sample = samples[0]
                raw_path = output_root / sample["raw_metrics"]["path"]
                raw = validate.load_json(raw_path)
                raw[key] = value
                raw_path.write_text(
                    json.dumps(raw, ensure_ascii=True, sort_keys=True) + "\n",
                    encoding="ascii",
                )
                sample["raw_metrics"] = {
                    "path": sample["raw_metrics"]["path"],
                    "bytes": raw_path.stat().st_size,
                    "sha256": contract.sha256_file(raw_path),
                }
                if key in sample["metrics"]:
                    sample["metrics"][key] = value
                with self.assertRaisesRegex(exercise.ResourceExerciseError, error_text):
                    exercise.validate_exercise(
                        samples,
                        self.contract_document["profiles"],
                        output_root,
                    )

    def test_stream_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "exercise"
            samples = self.populate_samples(output_root)
            stdout_path = output_root / samples[0]["stdout"]["path"]
            stdout_path.write_bytes(stdout_path.read_bytes() + b"mutated\n")
            samples[0]["stdout"] = {
                "path": samples[0]["stdout"]["path"],
                "bytes": stdout_path.stat().st_size,
                "sha256": contract.sha256_file(stdout_path),
            }
            with self.assertRaisesRegex(exercise.ResourceExerciseError, "stdout drift"):
                exercise.validate_exercise(
                    samples,
                    self.contract_document["profiles"],
                    output_root,
                )


if __name__ == "__main__":
    unittest.main()
