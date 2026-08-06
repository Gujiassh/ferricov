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

    def test_json_values_equal_is_type_sensitive(self) -> None:
        from validation_common import json_values_equal
        self.assertTrue(json_values_equal(1, 1))
        self.assertTrue(json_values_equal(True, True))
        self.assertTrue(json_values_equal(1.0, 1.0))
        self.assertFalse(json_values_equal(1, True))
        self.assertFalse(json_values_equal(1, 1.0))
        self.assertFalse(json_values_equal(0, False))
        self.assertFalse(json_values_equal(0, 0.0))
        self.assertFalse(json_values_equal({"exists": False}, {"exists": 0}))
        self.assertFalse(json_values_equal([1], [True]))
        self.assertTrue(json_values_equal({"a": [1, False, None]}, {"a": [1, False, None]}))

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



    def test_tf030_json_type_insensitivity_is_rejected(self) -> None:
        """Registry comparisons must reject Python int/bool/float equivalences."""
        case_id = "numeric-tf030-fna-mirror.default-stop"
        case = copy.deepcopy(self.cases[case_id])
        observation = copy.deepcopy(self.baseline[case_id])
        observation["fixture_sha256"] = hashlib.sha256(self.fixtures[case["fixture"]].data).hexdigest()
        observation["additional_fixture_sha256"] = {
            name: hashlib.sha256(self.fixtures[path].data).hexdigest()
            for name, path in case.get("additional_fixtures", {}).items()
        }
        validate_observation_binding(case, observation, self.fixtures)

        # exit_status is 1 for this stop case; bool/float must not pass via ==.
        for value in (True, 1.0):
            mutated = copy.deepcopy(observation)
            mutated["exit_status"] = value
            with self.subTest(exit_status=value), self.assertRaises(ValueError):
                validate_observation_binding(case, mutated, self.fixtures)

        # exit_status 0 equivalents on a success semantic case
        success_id = "numeric-format-atoms.tf030.semantic-snapshot"
        success_case = copy.deepcopy(self.cases[success_id])
        success_obs = copy.deepcopy(self.baseline[success_id])
        success_obs["fixture_sha256"] = hashlib.sha256(self.fixtures[success_case["fixture"]].data).hexdigest()
        success_obs["additional_fixture_sha256"] = {
            name: hashlib.sha256(self.fixtures[path].data).hexdigest()
            for name, path in success_case.get("additional_fixtures", {}).items()
        }
        validate_observation_binding(success_case, success_obs, self.fixtures)
        for value in (False, 0.0):
            mutated = copy.deepcopy(success_obs)
            mutated["exit_status"] = value
            with self.subTest(exit_status=value), self.assertRaises(ValueError):
                validate_observation_binding(success_case, mutated, self.fixtures)

        # output.exists false/true must not accept 0/1 or 0.0/1.0
        for value in (0, 0.0):
            mutated = copy.deepcopy(observation)
            mutated["output"] = {"exists": value}
            with self.subTest(exists=value), self.assertRaises(ValueError):
                validate_observation_binding(case, mutated, self.fixtures)
        canonical_id = "numeric-tf030-fna-mirror.ignore-negative-format.canonical"
        canon_case = copy.deepcopy(self.cases[canonical_id])
        canon_obs = copy.deepcopy(self.baseline[canonical_id])
        canon_obs["fixture_sha256"] = hashlib.sha256(self.fixtures[canon_case["fixture"]].data).hexdigest()
        canon_obs["additional_fixture_sha256"] = {}
        validate_observation_binding(canon_case, canon_obs, self.fixtures)
        for value in (1, 1.0):
            mutated = copy.deepcopy(canon_obs)
            mutated["output"] = {**mutated["output"], "exists": value}
            with self.subTest(exists=value), self.assertRaises(ValueError):
                validate_observation_binding(canon_case, mutated, self.fixtures)

        document = self._snapshot("numeric-format-atoms.tf030.semantic-snapshot")
        self.validate_tf030_numeric_rows(
            document, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
        )
        for value in (1.0, True):
            mutated = copy.deepcopy(document)
            mutated["schema_version"] = value
            with self.subTest(schema_version=value), self.assertRaises(ValueError):
                self.validate_tf030_numeric_rows(
                    mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
                )
        mutated = copy.deepcopy(document)
        mutated["numeric_rows"][0]["record_ordinal"] = float(mutated["numeric_rows"][0]["record_ordinal"])
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(
                mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
            )
        # locator line int -> float
        mutated = copy.deepcopy(document)
        if isinstance(mutated["numeric_rows"][0].get("locator"), dict) and "line" in mutated["numeric_rows"][0]["locator"]:
            mutated["numeric_rows"][0]["locator"]["line"] = float(mutated["numeric_rows"][0]["locator"]["line"])
            with self.assertRaises(ValueError):
                self.validate_tf030_numeric_rows(
                    mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
                )
        # cache found int -> float
        mutated = copy.deepcopy(document)
        metric = mutated["sources"][0]["aggregate"]["line"]
        metric["found"] = float(metric["found"])
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(
                mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
            )
        # cache found int -> bool when zero/nonzero
        mutated = copy.deepcopy(document)
        metric = mutated["sources"][0]["aggregate"]["line"]
        metric["found"] = bool(metric["found"])
        with self.assertRaises(ValueError):
            self.validate_tf030_numeric_rows(
                mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
            )



    def test_tf030_environment_binding_is_required(self) -> None:
        """TF-030 cases/observations must pin deterministic Perl hash env."""
        from corpus_tf030 import TF030_PERL_ENV

        case_id = "numeric-tf030-fna-mirror.threshold-ignore-all.canonical"
        case = copy.deepcopy(self.cases[case_id])
        observation = copy.deepcopy(self.baseline[case_id])
        observation["fixture_sha256"] = hashlib.sha256(self.fixtures[case["fixture"]].data).hexdigest()
        observation["additional_fixture_sha256"] = {
            name: hashlib.sha256(self.fixtures[path].data).hexdigest()
            for name, path in case.get("additional_fixtures", {}).items()
        }
        # Canonical path must already carry exact env.
        self.assertEqual(case.get("environment"), TF030_PERL_ENV)
        self.assertEqual(observation.get("environment"), TF030_PERL_ENV)
        validate_observation_binding(case, observation, self.fixtures)

        missing_case = copy.deepcopy(case)
        missing_case.pop("environment", None)
        with self.assertRaises(ValueError):
            validate_observation_binding(missing_case, observation, self.fixtures)

        missing_obs = copy.deepcopy(observation)
        missing_obs.pop("environment", None)
        with self.assertRaises(ValueError):
            validate_observation_binding(case, missing_obs, self.fixtures)

        wrong = copy.deepcopy(observation)
        wrong["environment"] = {"PERL_HASH_SEED": "1", "PERL_PERTURB_KEYS": "0"}
        with self.assertRaises(ValueError):
            validate_observation_binding(case, wrong, self.fixtures)

        bool_env = copy.deepcopy(observation)
        bool_env["environment"] = {"PERL_HASH_SEED": 0, "PERL_PERTURB_KEYS": "0"}  # type: ignore[dict-item]
        with self.assertRaises(ValueError):
            validate_observation_binding(case, bool_env, self.fixtures)

        # Non-TF-030 cases must not retain environment.
        plain_id = "numeric-format-atoms.ignore-all.canonical"
        if plain_id in self.cases:
            plain_case = copy.deepcopy(self.cases[plain_id])
            plain_obs = copy.deepcopy(self.baseline[plain_id])
            plain_obs["fixture_sha256"] = hashlib.sha256(self.fixtures[plain_case["fixture"]].data).hexdigest()
            plain_obs["additional_fixture_sha256"] = {}
            require_plain = copy.deepcopy(plain_obs)
            require_plain["environment"] = dict(TF030_PERL_ENV)
            with self.assertRaises(ValueError):
                validate_observation_binding(plain_case, require_plain, self.fixtures)

    def test_capture_normalize_case_environment(self) -> None:
        from capture_oracle import normalize_case_environment
        from corpus_tf030 import TF030_PERL_ENV

        self.assertEqual(
            normalize_case_environment({"id": "x", "environment": dict(TF030_PERL_ENV)}),
            TF030_PERL_ENV,
        )
        self.assertIsNone(normalize_case_environment({"id": "x"}))
        with self.assertRaises(SystemExit):
            normalize_case_environment({"id": "x", "environment": {"PERL_HASH_SEED": 0}})
        with self.assertRaises(SystemExit):
            normalize_case_environment({"id": "x", "environment": {}})
        with self.assertRaises(SystemExit):
            normalize_case_environment({"id": "x", "environment": {"BAD=KEY": "1"}})



    def test_tf030_expected_exit_type_sensitivity_is_rejected(self) -> None:
        """TF-030 expected_exit must type-sensitively match registry/observation exit_status."""
        fail_id = "numeric-tf030-fna-mirror.default-stop"
        ok_id = "numeric-tf030-fna-mirror.ignore-negative-format.canonical"

        def bind(case_id: str):
            case = copy.deepcopy(self.cases[case_id])
            observation = copy.deepcopy(self.baseline[case_id])
            observation["fixture_sha256"] = hashlib.sha256(self.fixtures[case["fixture"]].data).hexdigest()
            observation["additional_fixture_sha256"] = {
                name: hashlib.sha256(self.fixtures[path].data).hexdigest()
                for name, path in case.get("additional_fixtures", {}).items()
            }
            validate_observation_binding(case, observation, self.fixtures)
            return case, observation

        fail_case, fail_obs = bind(fail_id)
        self.assertEqual(fail_case["expected_exit"], 1)
        self.assertEqual(fail_obs["exit_status"], 1)
        for value in (True, 1.0):
            mutated = copy.deepcopy(fail_case)
            mutated["expected_exit"] = value
            with self.subTest(case=fail_id, expected_exit=value), self.assertRaises(ValueError):
                validate_observation_binding(mutated, fail_obs, self.fixtures)

        ok_case, ok_obs = bind(ok_id)
        self.assertEqual(ok_case["expected_exit"], 0)
        self.assertEqual(ok_obs["exit_status"], 0)
        for value in (False, 0.0):
            mutated = copy.deepcopy(ok_case)
            mutated["expected_exit"] = value
            with self.subTest(case=ok_id, expected_exit=value), self.assertRaises(ValueError):
                validate_observation_binding(mutated, ok_obs, self.fixtures)

        # Full generated document equality must reject bool/float expected_exit.
        from validation_common import json_values_equal, require_json_equal
        import json
        from pathlib import Path

        expected_cases = generate.build_oracle_cases(generate.build_fixtures())
        cases_path = Path(__file__).resolve().parent / "oracle-cases.json"
        cases_document = json.loads(cases_path.read_text(encoding="ascii"))
        self.assertTrue(json_values_equal(cases_document, expected_cases))

        mutated_fail = copy.deepcopy(cases_document)
        for case in mutated_fail["cases"]:
            if case["id"] == fail_id:
                case["expected_exit"] = True
                break
        self.assertFalse(json_values_equal(mutated_fail, expected_cases))
        with self.assertRaises(ValueError):
            require_json_equal(
                mutated_fail,
                expected_cases,
                "oracle-cases.json is not the exact generator result",
            )

        mutated_ok = copy.deepcopy(cases_document)
        for case in mutated_ok["cases"]:
            if case["id"] == ok_id:
                case["expected_exit"] = 0.0
                break
        self.assertFalse(json_values_equal(mutated_ok, expected_cases))
        with self.assertRaises(ValueError):
            require_json_equal(
                mutated_ok,
                expected_cases,
                "oracle-cases.json is not the exact generator result",
            )



    def test_merge_into_rejects_mutated_retained_baseline(self) -> None:
        """Selective TF-030 merge must not accept a mutated retained baseline copy."""
        import json
        import subprocess
        import tempfile
        from pathlib import Path

        from capture_oracle import (
            CANONICAL_BASELINE_PATH,
            EXPECTED_MERGE_BASELINE_SHA256,
            validate_merge_into_request,
        )
        from corpus_tf030 import TF030_CASE_IDS

        baseline_path = CANONICAL_BASELINE_PATH
        raw = baseline_path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_MERGE_BASELINE_SHA256)

        # Helper accepts only canonical path + exact TF-030 selection.
        validate_merge_into_request(baseline_path, list(TF030_CASE_IDS))
        with self.assertRaises(SystemExit):
            validate_merge_into_request(baseline_path, list(TF030_CASE_IDS)[:14])
        with self.assertRaises(SystemExit):
            validate_merge_into_request(
                baseline_path,
                list(TF030_CASE_IDS) + ["numeric-format-atoms.ignore-all.canonical"],
            )

        document = json.loads(raw.decode("ascii"))
        # Mutate one non-TF030 observation and refresh its local stdout hash so a
        # self-hash-only check would still pass.
        non_tf = next(case for case in document["cases"] if case["id"] not in TF030_CASE_IDS)
        mutated_stdout = dict(non_tf["stdout"])
        original_b64 = mutated_stdout.get("base64")
        self.assertIsInstance(original_b64, str)
        import base64
        original_bytes = base64.b64decode(original_b64)
        poisoned = original_bytes + b"\n#mutated-retained-evidence\n"
        mutated_stdout["base64"] = base64.b64encode(poisoned).decode("ascii")
        mutated_stdout["sha256"] = hashlib.sha256(poisoned).hexdigest()
        mutated_stdout["byte_size"] = len(poisoned)
        non_tf["stdout"] = mutated_stdout

        with tempfile.TemporaryDirectory(prefix="ferricov-merge-integrity-") as tmp:
            tmp_path = Path(tmp)
            poisoned_baseline = tmp_path / "oracle-baseline.mutated.json"
            poisoned_bytes = (json.dumps(document, indent=2) + "\n").encode("ascii")
            poisoned_baseline.write_bytes(poisoned_bytes)
            self.assertNotEqual(
                hashlib.sha256(poisoned_bytes).hexdigest(),
                EXPECTED_MERGE_BASELINE_SHA256,
            )
            # Path must be canonical; temp copy is rejected before Docker/merge.
            with self.assertRaises(SystemExit) as path_err:
                validate_merge_into_request(poisoned_baseline, list(TF030_CASE_IDS))
            self.assertIn("canonical baseline path", str(path_err.exception))

            # Even if path is ignored, byte identity of mutated content must fail.
            # Simulate by writing over a non-canonical path check via direct hash.
            self.assertNotEqual(
                hashlib.sha256(poisoned_baseline.read_bytes()).hexdigest(),
                EXPECTED_MERGE_BASELINE_SHA256,
            )

            output_path = tmp_path / "merged-out.json"
            cmd = [
                "python3",
                str(Path(__file__).resolve().parent / "capture_oracle.py"),
                "--cases",
                str(Path(__file__).resolve().parent / "oracle-cases.json"),
                "--merge-into",
                str(poisoned_baseline),
                "--output",
                str(output_path),
            ]
            for case_id in TF030_CASE_IDS:
                cmd.extend(["--case-id", case_id])
            result = subprocess.run(
                cmd,
                cwd=str(Path(__file__).resolve().parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            combined = (result.stdout + result.stderr).decode("utf-8", "replace")
            self.assertTrue(
                "canonical baseline path" in combined
                or "baseline byte identity mismatch" in combined,
                msg=combined,
            )
            self.assertFalse(output_path.exists())



if __name__ == "__main__":
    unittest.main()
