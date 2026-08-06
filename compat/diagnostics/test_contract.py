from __future__ import annotations

import copy
import importlib.util
import os
import unittest
from pathlib import Path


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
        self.assertEqual(self.committed["totals"]["oracle_observations"], 147)
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


if __name__ == "__main__":
    unittest.main()
