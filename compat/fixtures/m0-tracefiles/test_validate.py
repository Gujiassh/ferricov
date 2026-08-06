#!/usr/bin/env python3
"""Focused mutation tests for retained tracefile semantic snapshots."""

from __future__ import annotations

import base64
import copy
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from validate import (  # noqa: E402
    strict_json_loads_ascii,
    validate_added_numeric_case,
    validate_branches_expression_merge_snapshot,
    validate_lcov_stderr,
    validate_observation_binding,
    validate_semantic_input_identity,
    validate_semantic_snapshot_observation,
    validate_numeric_boundary_snapshot,
    validate_numeric_extra_spellings_snapshot,
    validate_numeric_format_atoms_snapshot,
    validate_numeric_signed_zero_snapshot,
    validate_semantic_input_identity,
    validate_semantic_stderr,
)
import generate  # noqa: E402


def _load_snapshot(case_id: str) -> dict:
    baseline = strict_json_loads_ascii((ROOT / "oracle-baseline.json").read_bytes(), "oracle-baseline.json")
    observation = next(case for case in baseline["cases"] if case["id"] == case_id)
    raw = base64.b64decode(observation["stdout"]["base64"], validate=True)
    return strict_json_loads_ascii(raw, f"{case_id} snapshot")


def _identity(data: bytes) -> dict:
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
        "base64": base64.b64encode(data).decode("ascii"),
    }


class StrictJsonAndBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = {fixture.path: fixture for fixture in generate.build_fixtures()}
        cls.cases = {
            case["id"]: case
            for case in generate.build_oracle_cases(generate.build_fixtures())["cases"]
        }
        baseline = strict_json_loads_ascii((ROOT / "oracle-baseline.json").read_bytes(), "oracle-baseline.json")
        cls.baseline = {case["id"]: case for case in baseline["cases"]}

    def test_strict_json_rejects_non_rfc_constants_and_non_ascii(self) -> None:
        for raw in (b'{"value": NaN}', b'{"value": Infinity}', b'{"value": -Infinity}', b'{"value": 1\xff}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_json_loads_ascii(raw, "mutation")

    def test_strict_json_rejects_duplicate_object_keys(self) -> None:
        with self.assertRaises(ValueError):
            strict_json_loads_ascii(b'{"value": 1, "value": 2}', "mutation")

    def test_inspector_rejects_escaped_duplicate_plan_key(self) -> None:
        upstream_root = Path(os.environ.get("LCOV_SOURCE_ROOT", ROOT.parents[3] / "lcov-upstream-reference"))
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "duplicate.json"
            plan.write_text(
                '{"schema_version":1,"kind":"tf030_numeric_plan","rows":[],"ro\\u0077s":[]}\n',
                encoding="ascii",
            )
            result = subprocess.run(
                [
                    "perl",
                    str(ROOT / "inspect_model.pl"),
                    "--numeric-plan",
                    str(plan),
                    str(ROOT / "fixtures/numeric/tf030-candidate-matrix.info"),
                ],
                env={**os.environ, "PERL5LIB": str(upstream_root / "lib")},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"duplicate object key", result.stderr)

    def test_fixture_hash_mutation_is_rejected(self) -> None:
        case = copy.deepcopy(self.cases["branches-expression-merge.semantic-snapshot"])
        observation = copy.deepcopy(self.baseline[case["id"]])
        observation["fixture_sha256"] = hashlib.sha256(self.fixtures[case["fixture"]].data).hexdigest()
        observation["additional_fixture_sha256"] = {
            name: hashlib.sha256(self.fixtures[path].data).hexdigest()
            for name, path in case.get("additional_fixtures", {}).items()
        }
        validate_observation_binding(case, observation, self.fixtures)
        observation["fixture_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_observation_binding(case, observation, self.fixtures)

    def test_companion_hash_mutation_is_rejected(self) -> None:
        case = copy.deepcopy(self.cases["checksum-match.summary"])
        observation = copy.deepcopy(self.baseline[case["id"]])
        observation["fixture_sha256"] = hashlib.sha256(self.fixtures[case["fixture"]].data).hexdigest()
        observation["additional_fixture_sha256"] = {
            "cs.c": hashlib.sha256(self.fixtures["fixtures/numeric/cs.c"].data).hexdigest()
        }
        validate_observation_binding(case, observation, self.fixtures)
        observation["additional_fixture_sha256"]["cs.c"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_observation_binding(case, observation, self.fixtures)

    def test_semantic_input_identity_is_exact_xor_and_ordered(self) -> None:
        case = {
            "id": "inputs",
            "argv": ["perl", "inspect_model.pl", "input.info", "right.info"],
        }
        valid = {"inputs": ["input.info", "right.info"]}
        validate_semantic_input_identity(case, valid)
        mutations = (
            {"input": "input.info", "inputs": ["input.info", "right.info"]},
            {"inputs": ["right.info", "input.info"]},
            {"input": "input.info"},
        )
        for document in mutations:
            with self.subTest(document=document), self.assertRaises(ValueError):
                validate_semantic_input_identity(case, document)

    def test_output_existence_and_stop_on_error_mutations_are_rejected(self) -> None:
        case = {
            "id": "numeric-format-atoms.excessive-stop-on-error-0",
            "fixture": "fixtures/numeric/format-atoms.info",
            "argv": ["lcov"],
            "expected_exit": 1,
            "output_file": "output.info",
            "expected_output_exists": True,
        }
        output = b"output"
        observation = {
            "fixture": case["fixture"],
            "fixture_sha256": hashlib.sha256(self.fixtures[case["fixture"]].data).hexdigest(),
            "argv": case["argv"],
            "exit_status": 1,
            "stdout": _identity(b""),
            "stderr": _identity(b""),
            "output_file": "output.info",
            "output": {"exists": True, **_identity(output)},
            "additional_fixture_sha256": {},
        }
        validate_observation_binding(case, observation, self.fixtures)
        observation["output"]["exists"] = False
        with self.assertRaises(ValueError):
            validate_observation_binding(case, observation, self.fixtures)

        stop_case = {
            **case,
            "id": "numeric-format-atoms.excessive-stop-on-error-1",
            "expected_output_exists": False,
        }
        stop_observation = copy.deepcopy(observation)
        stop_observation["output"] = {"exists": False}
        validate_observation_binding(stop_case, stop_observation, self.fixtures)
        stop_observation["output"] = {"exists": True, **_identity(b"unexpected")}
        with self.assertRaises(ValueError):
            validate_observation_binding(stop_case, stop_observation, self.fixtures)

    def test_erase_functions_suppression_output_mutation_is_rejected(self) -> None:
        case = copy.deepcopy(self.cases["numeric-function-excessive.erase-suppressed"])
        case["expected_output_exists"] = True
        output = (
            b"TN:function_excessive\nSF:function-excessive.c\nFNL:0,1,1\nFNA:0,99,below_fn\n"
            b"FNL:1,2,2\nFNA:1,100,at_fn\nFNF:2\nFNH:2\nDA:1,1\nDA:2,1\nDA:4,1\n"
            b"LF:3\nLH:3\nend_of_record\n"
        )
        observation = {"output": _identity(output), "stderr": _identity(b"")}
        validate_added_numeric_case(case, observation)
        mutated_case = copy.deepcopy(case)
        mutated_case["argv"] = [arg for arg in mutated_case["argv"] if arg != "erase_functions=^suppress_me$"]
        with self.assertRaises(ValueError):
            validate_added_numeric_case(mutated_case, observation)
        mutated = output.replace(b"FNA:0,99,below_fn\n", b"FNA:0,101,suppress_me\n")
        with self.assertRaises(ValueError):
            validate_added_numeric_case(case, {"output": _identity(mutated), "stderr": _identity(b"")})

        threshold_case = copy.deepcopy(self.cases["numeric-function-excessive.default-stop"])
        threshold_case["expected_output_exists"] = False
        threshold_case["argv"] = [
            "lcov", "--rc", "excessive_count_threshold=99", "--add-tracefile", "input.info", "--output-file", "output.info",
        ]
        with self.assertRaises(ValueError):
            validate_added_numeric_case(threshold_case, {"output": {"exists": False}, "stderr": _identity(b"")})

    def test_semantic_stderr_category_and_severity_mutation_is_rejected(self) -> None:
        valid = b"inspect_model.pl: WARNING: (negative) detail\n"
        validate_semantic_stderr("numeric-negative-inf.semantic-snapshot", valid)
        for mutated in (
            b"inspect_model.pl: ERROR: (negative) detail\n",
            b"inspect_model.pl: WARNING: (format) detail\n",
            b"inspect_model.pl: WARNING: (negative) detail\ninspect_model.pl: WARNING: (negative) detail\n",
            b"noise\n",
            b"inspect_model.pl: WARNING: (negative) detail\nnoise\n",
        ):
            with self.subTest(mutated=mutated), self.assertRaises(ValueError):
                validate_semantic_stderr("numeric-negative-inf.semantic-snapshot", mutated)

    def test_stop_on_error_category_mutations_are_rejected(self) -> None:
        stop_zero = (
            b"lcov: WARNING: (negative) a\n"
            b"lcov: WARNING: (negative) b\n"
            b"lcov: WARNING: (format) a\n"
            b"lcov: WARNING: (format) b\n"
            b"lcov: ERROR: (excessive) a\n"
            b"lcov: ERROR: (excessive) b\n"
            b"lcov: ERROR: (excessive) c\n"
        )
        validate_lcov_stderr(
            "numeric-format-atoms.excessive-stop-on-error-0",
            stop_zero,
            (("WARNING", "negative"), ("WARNING", "negative"), ("WARNING", "format"), ("WARNING", "format"),
             ("ERROR", "excessive"), ("ERROR", "excessive"), ("ERROR", "excessive")),
        )
        with self.assertRaises(ValueError):
            validate_lcov_stderr(
                "numeric-format-atoms.excessive-stop-on-error-0",
                stop_zero.replace(b"ERROR: (excessive) c", b"WARNING: (excessive) c"),
                (("WARNING", "negative"), ("WARNING", "negative"), ("WARNING", "format"), ("WARNING", "format"),
                 ("ERROR", "excessive"), ("ERROR", "excessive"), ("ERROR", "excessive")),
            )
        stop_one = b"lcov: WARNING: (negative) a\nlcov: WARNING: (format) b\nlcov: ERROR: (corrupt) lcov: ERROR: (excessive) c\n\tcont\n"
        validate_lcov_stderr(
            "numeric-format-atoms.excessive-stop-on-error-1",
            stop_one,
            (("WARNING", "negative"), ("WARNING", "format"), ("ERROR", "corrupt"), ("ERROR", "excessive")),
        )
        with self.assertRaises(ValueError):
            validate_lcov_stderr(
                "numeric-format-atoms.excessive-stop-on-error-1",
                stop_one.replace(b"(corrupt)", b"(excessive)"),
                (("WARNING", "negative"), ("WARNING", "format"), ("ERROR", "corrupt"), ("ERROR", "excessive")),
            )


class BranchExpressionMergeSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = _load_snapshot("branches-expression-merge.semantic-snapshot")

    def test_retained_snapshot_passes(self) -> None:
        validate_branches_expression_merge_snapshot(copy.deepcopy(self.snapshot))

    def test_each_cached_total_drift_is_rejected(self) -> None:
        mutations = (
            lambda source: source["aggregate"]["line"].__setitem__("found", 2),
            lambda source: source["aggregate"]["line"].__setitem__("hit", 0),
            lambda source: source["aggregate"]["line"]["lines"].__setitem__("10", 4),
            lambda source: source["testcases"]["branch"]["br_expression_merge"].__setitem__("found", 3),
            lambda source: source["testcases"]["branch"]["br_expression_merge"].__setitem__("hit", 2),
            lambda source: source["testcases"]["line"]["br_expression_merge"].__setitem__("found", 2),
            lambda source: source["testcases"]["line"]["br_expression_merge"].__setitem__("hit", 0),
            lambda source: source["testcases"]["line"]["br_expression_merge"]["lines"].__setitem__("10", 4),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                document = copy.deepcopy(self.snapshot)
                mutate(document["sources"][0])
                with self.assertRaises(ValueError):
                    validate_branches_expression_merge_snapshot(document)


class NumericBoundarySnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = _load_snapshot("numeric-boundary.semantic-snapshot")

    def test_retained_snapshot_passes(self) -> None:
        validate_numeric_boundary_snapshot(copy.deepcopy(self.snapshot))

    def test_input_identity_and_value_drift_are_rejected(self) -> None:
        mutations = (
            lambda document: document.__setitem__("input", "other.info"),
            lambda document: document.__setitem__("inputs", ["input.info"]),
            lambda document: document["sources"][0]["aggregate"]["line"]["lines"].__setitem__("1", 9),
            lambda document: document["sources"][9]["aggregate"]["line"]["lines"].__setitem__("1", "Inf"),
            lambda document: document["sources"][10]["aggregate"]["line"]["lines"].__setitem__("1", float("inf")),
            lambda document: document["sources"].pop(),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                document = copy.deepcopy(self.snapshot)
                mutate(document)
                with self.assertRaises(ValueError):
                    validate_numeric_boundary_snapshot(document)


class NumericFormatAtomsSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = _load_snapshot(
            "numeric-format-atoms.ignore-format-negative.semantic-snapshot"
        )

    def test_retained_snapshot_passes(self) -> None:
        validate_numeric_format_atoms_snapshot(
            copy.deepcopy(self.snapshot), with_excessive_threshold=False
        )

    def test_coercion_and_retention_drift_are_rejected(self) -> None:
        mutations = (
            lambda source: source["aggregate"]["line"]["lines"].__setitem__("4", -3),
            lambda source: source["aggregate"]["line"]["lines"].__setitem__("12", 0),
            lambda source: source["aggregate"]["line"].__setitem__("found", 6),
            lambda source: source["aggregate"]["function"]["functions"]["1"]["aliases"].__setitem__(
                "alias", -2
            ),
            lambda source: source["testcases"]["line"][""]["lines"].__setitem__("10", 1),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                document = copy.deepcopy(self.snapshot)
                mutate(document["sources"][0])
                with self.assertRaises(ValueError):
                    validate_numeric_format_atoms_snapshot(
                        document, with_excessive_threshold=False
                    )


class NumericSignedZeroSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = _load_snapshot("numeric-signed-zero.semantic-snapshot")

    def test_retained_snapshot_passes(self) -> None:
        validate_numeric_signed_zero_snapshot(copy.deepcopy(self.snapshot))

    def test_signed_zero_and_branch_drift_are_rejected(self) -> None:
        mutations = (
            lambda source: source["aggregate"]["line"]["lines"].__setitem__("1", 1),
            lambda source: source["aggregate"]["branch"]["lines"]["2"]["blocks"][0]["elements"][0].__setitem__(
                "taken", 1
            ),
            lambda source: source["aggregate"]["branch"].__setitem__("hit", 2),
            lambda source: source["testcases"]["line"]["numeric_signed_zero"]["lines"].__setitem__(
                "1", 1
            ),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                document = copy.deepcopy(self.snapshot)
                mutate(document["sources"][0])
                with self.assertRaises(ValueError):
                    validate_numeric_signed_zero_snapshot(document)


class NumericExtraSpellingsSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = _load_snapshot("numeric-extra-spellings.semantic-snapshot")

    def test_retained_snapshot_passes(self) -> None:
        validate_numeric_extra_spellings_snapshot(copy.deepcopy(self.snapshot))

    def test_extra_spelling_drift_is_rejected(self) -> None:
        mutations = (
            lambda document: document.__setitem__("input", "other.info"),
            lambda document: document["sources"][0]["aggregate"]["line"]["lines"].__setitem__("1", 1),
            lambda document: document["sources"][1]["aggregate"]["line"]["lines"].__setitem__("1", "NaN"),
            lambda document: document["sources"][2]["aggregate"]["line"]["lines"].__setitem__("1", "Inf"),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                document = copy.deepcopy(self.snapshot)
                mutate(document)
                with self.assertRaises(ValueError):
                    validate_numeric_extra_spellings_snapshot(document)

class Tf030NumericMatrixMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from validation_numeric import validate_tf030_numeric_rows
        cls.validate_tf030_numeric_rows = staticmethod(validate_tf030_numeric_rows)
        cls.fixtures = {fixture.path: fixture for fixture in generate.build_fixtures()}
        cls.cases = {
            case["id"]: case
            for case in generate.build_oracle_cases(generate.build_fixtures())["cases"]
        }
        baseline = strict_json_loads_ascii((ROOT / "oracle-baseline.json").read_bytes(), "oracle-baseline.json")
        cls.baseline = {case["id"]: case for case in baseline["cases"]}

    def _snapshot(self, case_id: str) -> dict:
        observation = self.baseline[case_id]
        raw = base64.b64decode(observation["stdout"]["base64"], validate=True)
        return strict_json_loads_ascii(raw, f"{case_id} snapshot")

    def test_tf030_row_count_and_order_mutations_are_rejected(self) -> None:
        document = self._snapshot("numeric-format-atoms.tf030.semantic-snapshot")
        self.validate_tf030_numeric_rows(document, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot")
        mutated = copy.deepcopy(document)
        mutated["numeric_rows"] = mutated["numeric_rows"][1:]
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot")
        mutated = copy.deepcopy(document)
        mutated["numeric_rows"] = list(reversed(mutated["numeric_rows"]))
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot")
        mutated = copy.deepcopy(document)
        mutated["numeric_rows"] = mutated["numeric_rows"] + [copy.deepcopy(mutated["numeric_rows"][0])]
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot")

    def test_tf030_plan_identity_and_ordinal_mutations_are_rejected(self) -> None:
        document = self._snapshot("numeric-format-atoms.tf030.semantic-snapshot")
        for field, value in (
            ("family", "FNA"),
            ("lexeme", "0"),
            ("raw_record", "DA:4,0"),
            ("record_ordinal", 1),
            ("reader_match_kind", "brda_never_evaluated"),
        ):
            mutated = copy.deepcopy(document)
            mutated["numeric_rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate_tf030_numeric_rows(
                    mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
                )
        mutated = copy.deepcopy(document)
        mutated["numeric_rows"][0]["locator"] = {"line": 999}
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(
                mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
            )

    def test_tf030_scalar_and_category_mutations_are_rejected(self) -> None:
        document = self._snapshot("numeric-format-atoms.tf030.semantic-snapshot")
        for field, value in (
            ("category", "excessive"),
            ("looks_like_number", False),
            ("record_matched", False),
            ("retained", False),
            ("skipped", True),
            ("value_class", "nan"),
        ):
            mutated = copy.deepcopy(document)
            mutated["numeric_rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate_tf030_numeric_rows(
                    mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
                )
        mutated = copy.deepcopy(document)
        mutated["numeric_rows"][0]["sv_before"]["class"] = "NotB"
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(
                mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
            )
        for flag in ("iok", "nok", "pok", "is_uv"):
            mutated = copy.deepcopy(document)
            mutated["numeric_rows"][0]["sv_before"][flag] = not mutated["numeric_rows"][0]["sv_before"][flag]
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                self.validate_tf030_numeric_rows(
                    mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
                )

    def test_tf030_every_row_semantic_field_and_cache_fact_is_bound(self) -> None:
        cases = (
            ("numeric-format-atoms.tf030.semantic-snapshot", 12),
            ("numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot", 4),
            ("numeric-tf030-candidates.ignore-negative.semantic-snapshot", 40),
            ("numeric-format-atoms.tf030-threshold.semantic-snapshot", 12),
            ("numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot", 4),
            ("numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot", 40),
        )
        row_fields = (
            "category", "family", "fixture", "greater_than_threshold", "id", "lexeme", "locator",
            "looks_like_number", "negative", "raw_record", "reader_match_kind", "record_matched",
            "record_ordinal", "recovery", "retained", "skipped", "source", "testcase",
            "threshold_enabled", "threshold_text", "value_class",
        )
        stage_fields = ("class", "iok", "is_uv", "nok", "pok")

        def different(value: object) -> object:
            if isinstance(value, bool):
                return not value
            if isinstance(value, int):
                return value + 1
            if isinstance(value, str):
                return value + "-mutated"
            if value is None:
                return True
            if isinstance(value, dict):
                mutated = copy.deepcopy(value)
                mutated["__mutated__"] = True
                return mutated
            return "mutated"

        for case_id, count in cases:
            document = self._snapshot(case_id)
            self.validate_tf030_numeric_rows(document, expected_count=count, case_id=case_id)
            for row_index, row in enumerate(document["numeric_rows"]):
                for field in row_fields:
                    mutated = copy.deepcopy(document)
                    mutated["numeric_rows"][row_index][field] = different(row[field])
                    with self.subTest(case_id=case_id, row=row_index, field=field), self.assertRaises(ValueError):
                        self.validate_tf030_numeric_rows(mutated, expected_count=count, case_id=case_id)
                for stage in ("sv_before", "sv_after_looks_like_number", "sv_after_negative_compare", "sv_after_threshold_compare"):
                    if not isinstance(row[stage], dict):
                        continue
                    for field in stage_fields:
                        mutated = copy.deepcopy(document)
                        mutated["numeric_rows"][row_index][stage][field] = different(row[stage][field])
                        with self.subTest(case_id=case_id, row=row_index, field=f"{stage}.{field}"), self.assertRaises(ValueError):
                            self.validate_tf030_numeric_rows(mutated, expected_count=count, case_id=case_id)
                for stored in ("stored_aggregate", "stored_testcase"):
                    if not isinstance(row[stored], dict) or "scalar" not in row[stored]:
                        mutated = copy.deepcopy(document)
                        mutated["numeric_rows"][row_index][stored]["state"] = different(row[stored]["state"])
                        with self.subTest(case_id=case_id, row=row_index, field=f"{stored}.state"), self.assertRaises(ValueError):
                            self.validate_tf030_numeric_rows(mutated, expected_count=count, case_id=case_id)
                        continue
                    for field in ("text", "signed_zero"):
                        mutated = copy.deepcopy(document)
                        mutated["numeric_rows"][row_index][stored][field] = different(row[stored][field])
                        with self.subTest(case_id=case_id, row=row_index, field=f"{stored}.{field}"), self.assertRaises(ValueError):
                            self.validate_tf030_numeric_rows(mutated, expected_count=count, case_id=case_id)
                    for field in stage_fields:
                        mutated = copy.deepcopy(document)
                        mutated["numeric_rows"][row_index][stored]["scalar"][field] = different(
                            row[stored]["scalar"][field]
                        )
                        with self.subTest(case_id=case_id, row=row_index, field=f"{stored}.scalar.{field}"), self.assertRaises(ValueError):
                            self.validate_tf030_numeric_rows(mutated, expected_count=count, case_id=case_id)

            for source_index, source in enumerate(document["sources"]):
                for container_name in ("aggregate", "testcases"):
                    for metric_name, metric in source[container_name].items():
                        if container_name == "aggregate":
                            metrics = [(metric_name, metric)]
                        else:
                            metrics = list(metric.items())
                        for metric_key, cache in metrics:
                            for field in ("found", "hit"):
                                mutated = copy.deepcopy(document)
                                target = mutated["sources"][source_index][container_name][metric_name]
                                if container_name == "testcases":
                                    target = target[metric_key]
                                target[field] = different(cache[field])
                                with self.subTest(case_id=case_id, source=source_index, field=f"{container_name}.{metric_name}.{metric_key}.{field}"), self.assertRaises(ValueError):
                                    self.validate_tf030_numeric_rows(mutated, expected_count=count, case_id=case_id)

    def test_tf030_all_matrix_sizes_reject_missing_row(self) -> None:
        for case_id, count in (
            ("numeric-format-atoms.tf030.semantic-snapshot", 12),
            ("numeric-tf030-fna-mirror.ignore-negative-format.semantic-snapshot", 4),
            ("numeric-tf030-candidates.ignore-negative.semantic-snapshot", 40),
            ("numeric-format-atoms.tf030-threshold.semantic-snapshot", 12),
            ("numeric-tf030-fna-mirror.threshold-ignore-all.semantic-snapshot", 4),
            ("numeric-tf030-candidates.threshold-ignore-all.semantic-snapshot", 40),
        ):
            document = self._snapshot(case_id)
            self.validate_tf030_numeric_rows(document, expected_count=count, case_id=case_id)
            mutated = copy.deepcopy(document)
            del mutated["numeric_rows"][-1]
            with self.subTest(case_id=case_id), self.assertRaises(ValueError):
                self.validate_tf030_numeric_rows(mutated, expected_count=count, case_id=case_id)

    def test_tf030_plan_companion_hash_mutation_is_rejected(self) -> None:
        case = copy.deepcopy(self.cases["numeric-format-atoms.tf030.semantic-snapshot"])
        observation = copy.deepcopy(self.baseline[case["id"]])
        observation["fixture_sha256"] = hashlib.sha256(self.fixtures[case["fixture"]].data).hexdigest()
        observation["additional_fixture_sha256"] = {
            name: hashlib.sha256(self.fixtures[path].data).hexdigest()
            for name, path in case.get("additional_fixtures", {}).items()
        }
        validate_observation_binding(case, observation, self.fixtures)
        plan_name = next(iter(case["additional_fixtures"]))
        observation["additional_fixture_sha256"][plan_name] = "0" * 64
        with self.assertRaises(ValueError):
            validate_observation_binding(case, observation, self.fixtures)

    def test_tf030_canonical_output_and_stop_mutations_are_rejected(self) -> None:
        from validation_numeric import validate_added_numeric_case
        case = copy.deepcopy(self.cases["numeric-tf030-fna-mirror.ignore-negative-format.canonical"])
        observation = copy.deepcopy(self.baseline[case["id"]])
        validate_added_numeric_case(case, observation)
        mutated = copy.deepcopy(observation)
        raw = base64.b64decode(mutated["output"]["base64"], validate=True)
        raw = raw.replace(b"FNA:0,0,fna_neg2", b"FNA:0,1,fna_neg2", 1)
        mutated["output"] = {
            "exists": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_size": len(raw),
            "base64": base64.b64encode(raw).decode("ascii"),
        }
        with self.assertRaises(ValueError):
            validate_added_numeric_case(case, mutated)
        stop = copy.deepcopy(self.cases["numeric-tf030-fna-mirror.default-stop"])
        stop_obs = copy.deepcopy(self.baseline[stop["id"]])
        validate_added_numeric_case(stop, stop_obs)
        stop_obs["output"] = {"exists": True, "sha256": "0"*64, "byte_size": 1, "base64": base64.b64encode(b"x").decode()}
        with self.assertRaises(ValueError):
            validate_added_numeric_case(stop, stop_obs)
        # stop cases still validate ordered stderr policy
        stop_obs = copy.deepcopy(self.baseline[stop["id"]])
        stop_obs["stderr"] = {
            "sha256": hashlib.sha256(b"").hexdigest(),
            "byte_size": 0,
            "base64": base64.b64encode(b"").decode("ascii"),
        }
        with self.assertRaises(ValueError):
            validate_added_numeric_case(stop, stop_obs)



    def test_tf030_refreshed_stream_and_output_hashes_are_rejected(self) -> None:
        """Independent observation registry must reject refreshed self-hashes."""
        for case_id in (
            "numeric-format-atoms.tf030.semantic-snapshot",
            "numeric-tf030-fna-mirror.default-stop",
            "numeric-tf030-fna-mirror.ignore-negative-format.canonical",
            "numeric-tf030-candidates.threshold-ignore-all.canonical",
        ):
            case = copy.deepcopy(self.cases[case_id])
            observation = copy.deepcopy(self.baseline[case_id])
            observation["fixture_sha256"] = hashlib.sha256(self.fixtures[case["fixture"]].data).hexdigest()
            observation["additional_fixture_sha256"] = {
                name: hashlib.sha256(self.fixtures[path].data).hexdigest()
                for name, path in case.get("additional_fixtures", {}).items()
            }
            validate_observation_binding(case, observation, self.fixtures)

            for field in ("stdout", "stderr"):
                mutated = copy.deepcopy(observation)
                raw = base64.b64decode(mutated[field]["base64"], validate=True) + b"x"
                mutated[field] = {
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_size": len(raw),
                    "base64": base64.b64encode(raw).decode("ascii"),
                }
                with self.subTest(case_id=case_id, field=field), self.assertRaises(ValueError):
                    validate_observation_binding(case, mutated, self.fixtures)

            if observation["output"].get("exists"):
                mutated = copy.deepcopy(observation)
                raw = base64.b64decode(mutated["output"]["base64"], validate=True) + b"x"
                mutated["output"] = {
                    "exists": True,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_size": len(raw),
                    "base64": base64.b64encode(raw).decode("ascii"),
                }
                with self.subTest(case_id=case_id, field="output"), self.assertRaises(ValueError):
                    validate_observation_binding(case, mutated, self.fixtures)
            else:
                mutated = copy.deepcopy(observation)
                payload = b"unexpected"
                mutated["output"] = {
                    "exists": True,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "byte_size": len(payload),
                    "base64": base64.b64encode(payload).decode("ascii"),
                }
                with self.subTest(case_id=case_id, field="output-exists"), self.assertRaises(ValueError):
                    validate_observation_binding(case, mutated, self.fixtures)

            for field, value in (
                ("exit_status", 99 if observation["exit_status"] != 99 else 0),
                ("output_file", "mutated.info" if observation.get("output_file") != "mutated.info" else "other.info"),
            ):
                mutated = copy.deepcopy(observation)
                mutated[field] = value
                with self.subTest(case_id=case_id, field=field), self.assertRaises(ValueError):
                    validate_observation_binding(case, mutated, self.fixtures)

    def test_tf030_semantic_shape_rejects_unknown_keys(self) -> None:
        document = self._snapshot("numeric-format-atoms.tf030.semantic-snapshot")
        self.validate_tf030_numeric_rows(
            document, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
        )
        mutated = copy.deepcopy(document)
        mutated["unexpected_top_level"] = True
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(
                mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
            )
        mutated = copy.deepcopy(document)
        mutated["oracle"] = copy.deepcopy(document["oracle"])
        mutated["oracle"]["unexpected_nested"] = True
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(
                mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
            )

    def test_tf030_upstream_format_atoms_binding_is_required(self) -> None:
        from dataclasses import replace
        from validate import _validate_upstream_numeric_fixture
        fixtures = dict(self.fixtures)
        _validate_upstream_numeric_fixture(fixtures)
        original = fixtures["fixtures/numeric/format-atoms.info"]
        fixtures["fixtures/numeric/format-atoms.info"] = replace(
            original, data=original.data + b"\n"
        )
        with self.assertRaises(ValueError):
            _validate_upstream_numeric_fixture(fixtures)
        env = dict(os.environ)
        env["LCOV_SOURCE_ROOT"] = "/tmp/missing-lcov-upstream-for-tf030"
        result = subprocess.run(
            [
                "python3",
                "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(ROOT)!r}); "
                    "from validate import _validate_upstream_numeric_fixture; "
                    "import generate; "
                    "fixtures={f.path:f for f in generate.build_fixtures()}; "
                    "_validate_upstream_numeric_fixture(fixtures)"
                ),
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        combined = result.stderr + result.stdout
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            b"missing pinned upstream fixture" in combined or b"Traceback" in combined,
            combined.decode("utf-8", "replace"),
        )



if __name__ == "__main__":
    unittest.main()
