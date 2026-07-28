from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPOSITORY_ROOT / "compat/benchmarks/validate.py"
SPEC = importlib.util.spec_from_file_location("benchmark_validate", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def artifact(path: Path, root: Path) -> dict[str, object]:
    content = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def differential_result(scope: str, status: str) -> dict[str, object]:
    digest = "sha256:" + "0" * 64
    identity = {
        "kind": "docker_image",
        "executable_sha256": digest,
        "container_image_sha256": digest,
    }
    metrics = {
        "wall_seconds": 1.0,
        "user_cpu_seconds": None,
        "system_cpu_seconds": None,
        "peak_rss_bytes": None,
        "output_bytes": 0,
        "output_files": 0,
    }
    zero_sha256 = "0" * 64
    def run(side: str) -> dict[str, object]:
        return {
            "exit_code": 0,
            "signal": None,
            "stdout_artifact": f"{side}/stdout.bin",
            "stderr_artifact": f"{side}/stderr.bin",
            "file_tree_artifact": f"{side}/file-tree.json",
            "stdout_sha256": zero_sha256,
            "stderr_sha256": zero_sha256,
            "file_tree_sha256": zero_sha256,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "file_tree_bytes": 0,
            "timeout": {
                "applied_seconds": 30,
                "expired": False,
                "termination_signal_sent": None,
                "escalation_signal_sent": None,
            },
            "cleanup": {
                "direct_child_reaped": True,
                "process_group_empty": True,
                "container_absent": None,
            },
            "metrics": metrics,
        }
    return {
        "schema_version": 1,
        "suite_id": "correctness-suite",
        "case_id": "correctness-case",
        "evidence_scope": scope,
        "upstream_commit": "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5",
        "surface": "cli",
        "command": "lcov",
        "arguments": ["--version"],
        "fixture": None,
        "environment": {
            "image": "image",
            "operating_system": "Linux",
            "architecture": "x86_64",
        },
        "effective_environment_variables": {},
        "implementation_identities": {
            "reference": identity,
            "candidate": {
                **identity,
                "executable_sha256": "sha256:" + "1" * 64,
            },
        },
        "runs": {"reference": run("reference"), "candidate": run("candidate")},
        "comparisons": [
            {
                "dimension": "stdout",
                "status": status,
                "normalizer": "exact-v1",
                "evidence": ["reference/stdout.bin", "candidate/stdout.bin"],
                "artifacts": [],
                "details": None,
            }
        ],
        "overall_status": status,
    }


class BenchmarkValidationTests(unittest.TestCase):
    def test_accepts_committed_oracle_suite(self) -> None:
        document = validator.validate_suite(
            REPOSITORY_ROOT / "compat/benchmarks/m0-oracle-baseline.json"
        )
        self.assertEqual(document["evidence_scope"], "oracle_baseline")

    def test_rejects_even_measured_count(self) -> None:
        suite_path = REPOSITORY_ROOT / "compat/benchmarks/m0-oracle-baseline.json"
        document = json.loads(suite_path.read_text())
        document["cases"][0]["measured_runs"] = 2
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "suite.json"
            path.write_text(
                json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="ascii"
            )
            with self.assertRaisesRegex(
                validator.BenchmarkValidationError, "must be odd"
            ):
                validator.validate_suite(path)

    def test_rejects_harness_self_test_correctness_reference(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as directory:
            root = Path(directory)
            path = root / "correctness.json"
            path.write_text(
                json.dumps(differential_result("harness_self_test", "pass")),
                encoding="ascii",
            )
            reference = artifact(path, REPOSITORY_ROOT)
            with self.assertRaisesRegex(
                validator.BenchmarkValidationError, "harness self-test"
            ):
                validator.validate_correctness_evidence(reference)

    def test_faster_but_wrong_candidate_cannot_unlock_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as directory:
            root = Path(directory)
            path = root / "correctness.json"
            candidate_wall_time_ns = 1
            reference_wall_time_ns = 1_000_000
            self.assertLess(candidate_wall_time_ns, reference_wall_time_ns)
            path.write_text(
                json.dumps(differential_result("compatibility", "fail")),
                encoding="ascii",
            )
            reference = artifact(path, REPOSITORY_ROOT)
            with self.assertRaisesRegex(
                validator.BenchmarkValidationError, "must pass"
            ):
                validator.validate_correctness_evidence(reference)

    def test_recomputes_summary_instead_of_trusting_document(self) -> None:
        samples = [
            {
                "metrics": {
                    "wall_time_ns": value,
                    "user_cpu_time_ns": value // 2,
                    "system_cpu_time_ns": value // 4,
                    "peak_rss_bytes": value * 10,
                    "output_bytes": 7,
                    "output_files": 1,
                }
            }
            for value in (30, 10, 20)
        ]
        summary = validator._expected_summary(samples)
        self.assertEqual(summary["wall_time_ns"]["median"], 20)
        mutated = copy.deepcopy(summary)
        mutated["wall_time_ns"]["median"] = 1
        self.assertNotEqual(mutated, validator._expected_summary(samples))


if __name__ == "__main__":
    unittest.main()
