from __future__ import annotations

import copy
import hashlib
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BASELINE = (
    REPOSITORY_ROOT
    / "compat/correctness/baselines/m0-cli-oracle-v2.5/result.json"
)
STATUS = REPOSITORY_ROOT / "compat/fixtures/m0-cli-contract/oracle-baseline-status.json"
VALIDATOR_PATH = REPOSITORY_ROOT / "compat/correctness/validate.py"

SPEC = importlib.util.spec_from_file_location("ferricov_correctness_validate", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load correctness validator")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def load(path: Path) -> dict[str, Any]:
    return validator.load_json(path)


def write(path: Path, document: dict[str, Any]) -> None:
    path.write_text(validator.canonical_json(document), encoding="ascii")


def artifact_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


class CorrectnessValidationTests(unittest.TestCase):
    def copied_baseline(self, directory: str) -> Path:
        destination = Path(directory) / "baseline"
        shutil.copytree(BASELINE.parent, destination)
        return destination / "result.json"

    def mutate_observation(
        self,
        baseline_path: Path,
        mutate: Callable[[dict[str, Any], Path], None],
        *,
        case_id: str | None = None,
    ) -> None:
        baseline = load(baseline_path)
        reference = next(
            reference
            for reference in baseline["cases"]
            if case_id is None
            or load(baseline_path.parent / reference["path"])["case_id"] == case_id
        )
        observation_path = baseline_path.parent / reference["path"]
        observation = load(observation_path)
        mutate(observation, observation_path.parent)
        write(observation_path, observation)
        reference["bytes"] = observation_path.stat().st_size
        reference["sha256"] = artifact_sha256(observation_path)
        write(baseline_path, baseline)

    def test_accepts_retained_baseline_without_product_claim(self) -> None:
        document = validator.validate_baseline(BASELINE)
        self.assertEqual(document["case_count"], 148)
        self.assertFalse(document["product_compatibility_evidence"])

    def test_accepts_status_bound_to_retained_baseline(self) -> None:
        document = validator.validate_status(STATUS)
        self.assertEqual(document["status"], "complete")
        self.assertFalse(document["product_compatibility_evidence"])

    def test_rejects_status_with_wrong_image_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            path = Path(directory) / "status.json"
            document = load(STATUS)
            document["oracle_image_identity"] = "sha256:" + "0" * 64
            write(path, document)
            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "image identity does not match",
            ):
                validator.validate_status(path)

    def test_rejects_product_compatibility_claim(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            baseline_path = self.copied_baseline(directory)
            document = load(baseline_path)
            document["product_compatibility_evidence"] = True
            write(baseline_path, document)

            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "product_compatibility_evidence",
            ):
                validator.validate_baseline(baseline_path)

    def test_rejects_tampered_raw_stdout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            baseline_path = self.copied_baseline(directory)
            baseline = load(baseline_path)
            observation_path = baseline_path.parent / baseline["cases"][0]["path"]
            stdout_path = observation_path.parent / "reference/stdout.bin"
            stdout_path.write_bytes(stdout_path.read_bytes() + b"tampered")

            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "byte count mismatch|hash mismatch",
            ):
                validator.validate_baseline(baseline_path)

    def test_rejects_executable_identity_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            baseline_path = self.copied_baseline(directory)

            def mutate(observation: dict[str, Any], _case_root: Path) -> None:
                observation["oracle_identity"]["executable_sha256"] = (
                    "sha256:" + "0" * 64
                )

            self.mutate_observation(baseline_path, mutate)
            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "executable identity mismatch",
            ):
                validator.validate_baseline(baseline_path)

    def test_replay_ignores_measurement_timing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            replay_path = self.copied_baseline(directory)

            def mutate(observation: dict[str, Any], _case_root: Path) -> None:
                observation["reference_run"]["metrics"]["wall_seconds"] += 1.0

            self.mutate_observation(replay_path, mutate)
            validator.compare_baselines(BASELINE, replay_path)

    def test_replay_ignores_random_oracle_tempfile_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            replay_path = self.copied_baseline(directory)

            baseline = load(replay_path)
            for reference in baseline["cases"]:
                observation_path = replay_path.parent / reference["path"]
                observation = load(observation_path)
                if observation["case_id"] != "m0-core-geninfo-startup-control":
                    continue
                run = observation["reference_run"]
                stderr_path = observation_path.parent / run["stderr_artifact"]
                content = validator.TEMP_PATH_PATTERN.sub(
                    b"/tmp/DNicc0DkqR", stderr_path.read_bytes()
                )
                stderr_path.write_bytes(content)
                run["stderr_sha256"] = artifact_sha256(stderr_path).removeprefix("sha256:")
                write(observation_path, observation)
                reference["bytes"] = observation_path.stat().st_size
                reference["sha256"] = artifact_sha256(observation_path)
                break
            write(replay_path, baseline)
            validator.compare_baselines(BASELINE, replay_path)

    def test_replay_does_not_normalize_tempfile_names_for_other_cases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            replay_path = self.copied_baseline(directory)

            def mutate(observation: dict[str, Any], case_root: Path) -> None:
                stderr_path = case_root / observation["reference_run"]["stderr_artifact"]
                stderr_path.write_bytes(stderr_path.read_bytes() + b"/tmp/ABCDEFGHIJ")
                run = observation["reference_run"]
                run["stderr_bytes"] = stderr_path.stat().st_size
                run["stderr_sha256"] = artifact_sha256(stderr_path).removeprefix("sha256:")

            self.mutate_observation(replay_path, mutate)
            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "replay mismatch",
            ):
                validator.compare_baselines(BASELINE, replay_path)

    def test_replay_rejects_stdout_semantic_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            replay_path = self.copied_baseline(directory)

            def mutate(observation: dict[str, Any], case_root: Path) -> None:
                stdout_path = case_root / observation["reference_run"]["stdout_artifact"]
                stdout_path.write_bytes(stdout_path.read_bytes() + b"semantic-drift")
                run = observation["reference_run"]
                run["stdout_bytes"] = stdout_path.stat().st_size
                run["stdout_sha256"] = artifact_sha256(stdout_path).removeprefix("sha256:")

            self.mutate_observation(replay_path, mutate)
            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "replay mismatch",
            ):
                validator.compare_baselines(BASELINE, replay_path)

    def test_rejects_configuration_exit_semantic_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            baseline_path = self.copied_baseline(directory)

            def mutate(observation: dict[str, Any], _case_root: Path) -> None:
                observation["reference_run"]["exit_code"] = 1

            self.mutate_observation(
                baseline_path,
                mutate,
                case_id="m0-config-base-explicit-on",
            )
            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "configuration exit semantic mismatch",
            ):
                validator.validate_baseline(baseline_path)

    def test_rejects_configuration_branch_summary_semantic_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            baseline_path = self.copied_baseline(directory)

            def mutate(observation: dict[str, Any], case_root: Path) -> None:
                run = observation["reference_run"]
                stdout_path = case_root / run["stdout_artifact"]
                content = b"".join(
                    line
                    for line in stdout_path.read_bytes().splitlines(keepends=True)
                    if not line.startswith(b"  branches....:")
                )
                stdout_path.write_bytes(content)
                run["stdout_bytes"] = len(content)
                run["stdout_sha256"] = artifact_sha256(stdout_path).removeprefix("sha256:")

            self.mutate_observation(
                baseline_path,
                mutate,
                case_id="m0-config-base-explicit-on",
            )
            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "configuration branch summary semantic mismatch",
            ):
                validator.validate_baseline(baseline_path)

    def test_rejects_configuration_stderr_semantic_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-correctness-test-") as directory:
            baseline_path = self.copied_baseline(directory)

            def mutate(observation: dict[str, Any], case_root: Path) -> None:
                run = observation["reference_run"]
                stderr_path = case_root / run["stderr_artifact"]
                stderr_path.write_bytes(b"")
                run["stderr_bytes"] = 0
                run["stderr_sha256"] = artifact_sha256(stderr_path).removeprefix("sha256:")

            self.mutate_observation(
                baseline_path,
                mutate,
                case_id="m0-config-base-relative-include",
            )
            with self.assertRaisesRegex(
                validator.CorrectnessValidationError,
                "configuration stderr semantic mismatch",
            ):
                validator.validate_baseline(baseline_path)


if __name__ == "__main__":
    unittest.main()
