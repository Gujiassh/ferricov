#!/usr/bin/env python3
"""Focused mutation tests for retained tracefile semantic snapshots."""

from __future__ import annotations

import base64
import copy
import json
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
        import base64
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
        trusted = validate_merge_into_request(baseline_path, list(TF030_CASE_IDS))
        self.assertEqual(trusted, raw)

        with self.assertRaises(SystemExit):
            validate_merge_into_request(baseline_path, list(TF030_CASE_IDS)[:14])
        with self.assertRaises(SystemExit):
            validate_merge_into_request(
                baseline_path,
                list(TF030_CASE_IDS) + ["numeric-format-atoms.ignore-all.canonical"],
            )
        # Out-of-order exact-set selection must reject.
        reordered = list(TF030_CASE_IDS)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        with self.assertRaises(SystemExit):
            validate_merge_into_request(baseline_path, reordered)
        # Duplicate explicit IDs must reject even if first 15 unique would match.
        duplicated = list(TF030_CASE_IDS)
        duplicated[3] = duplicated[2]
        with self.assertRaises(SystemExit):
            validate_merge_into_request(baseline_path, duplicated)

        document = json.loads(raw.decode("ascii"))
        non_tf = next(case for case in document["cases"] if case["id"] not in TF030_CASE_IDS)
        mutated_stdout = dict(non_tf["stdout"])
        original_bytes = base64.b64decode(mutated_stdout["base64"])
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
            with self.assertRaises(SystemExit) as path_err:
                validate_merge_into_request(poisoned_baseline, list(TF030_CASE_IDS))
            self.assertIn("canonical baseline path", str(path_err.exception))

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

    def test_select_oracle_cases_preserves_order_and_rejects_duplicates(self) -> None:
        import json
        from pathlib import Path

        from capture_oracle import select_oracle_cases
        from corpus_tf030 import TF030_CASE_IDS

        cases_document = json.loads(
            (Path(__file__).resolve().parent / "oracle-cases.json").read_text()
        )
        all_cases = cases_document["cases"]

        ordered_ids = [TF030_CASE_IDS[2], TF030_CASE_IDS[0], TF030_CASE_IDS[5]]
        selected = select_oracle_cases(all_cases, ordered_ids, [])
        self.assertEqual([case["id"] for case in selected], ordered_ids)

        with self.assertRaises(SystemExit):
            select_oracle_cases(all_cases, [TF030_CASE_IDS[0], TF030_CASE_IDS[0]], [])
        with self.assertRaises(SystemExit):
            select_oracle_cases(all_cases, ["does-not-exist"], [])
        # Prefix + overlapping explicit id is a duplicate.
        with self.assertRaises(SystemExit):
            select_oracle_cases(all_cases, [TF030_CASE_IDS[0]], ["numeric-format-atoms.tf030"])

        # Duplicate identical --case-prefix must reject, not silently de-duplicate.
        with self.assertRaises(SystemExit) as dup_prefix:
            select_oracle_cases(
                all_cases,
                [],
                ["numeric-format-atoms.tf030", "numeric-format-atoms.tf030"],
            )
        self.assertIn("duplicate case id from overlapping selectors", str(dup_prefix.exception))

        # Overlapping prefixes must reject the second prefix's already-seen matches.
        with self.assertRaises(SystemExit) as overlap_prefix:
            select_oracle_cases(
                all_cases,
                [],
                ["numeric-format-atoms.tf030", "numeric-format-atoms.tf030-threshold"],
            )
        self.assertIn("duplicate case id from overlapping selectors", str(overlap_prefix.exception))

        # Unmatched prefix is fail-closed even when other selectors would match.
        with self.assertRaises(SystemExit) as unmatched:
            select_oracle_cases(
                all_cases,
                [],
                ["numeric-format-atoms.tf030", "does-not-match-any-case"],
            )
        self.assertIn("unmatched --case-prefix", str(unmatched.exception))

        # Intended two-prefix TF-030 merge selection yields exact registry order.
        selected_prefixes = select_oracle_cases(
            all_cases,
            [],
            ["numeric-format-atoms.tf030", "numeric-tf030-"],
        )
        self.assertEqual(
            [case["id"] for case in selected_prefixes],
            list(TF030_CASE_IDS),
        )


    def test_override_cases_manifest_mutation_is_rejected_before_docker(self) -> None:
        """Overridden --cases must match pinned bytes; self-hash refresh still rejects."""
        import copy
        import io
        import json
        import tempfile
        from contextlib import redirect_stderr, redirect_stdout
        from pathlib import Path
        from unittest import mock

        import capture_oracle
        from corpus_tf030 import TF030_CASE_IDS

        cases_path = Path(__file__).resolve().parent / "oracle-cases.json"
        trusted_raw = cases_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(trusted_raw).hexdigest(),
            capture_oracle.EXPECTED_CASES_SHA256,
        )
        trusted = capture_oracle.validate_cases_request(cases_path)
        self.assertEqual(trusted, trusted_raw)

        document = json.loads(trusted_raw.decode("ascii"))
        target_id = TF030_CASE_IDS[0]
        mutated = copy.deepcopy(document)
        for case in mutated["cases"]:
            if case["id"] == target_id:
                # Keep trusted TF-030 id while rewriting capture definition.
                case["fixture"] = "fixtures/wave1/comments-core.info"
                case["expected_exit"] = 0
                case["description"] = "mutated override under trusted TF-030 id"
                case["argv"] = ["lcov", "--add-tracefile", "input.info", "--output-file", "output.info"]
                case["output_file"] = "output.info"
                case["expected_output_exists"] = True
                break
        else:
            self.fail(f"missing TF-030 case {target_id}")

        # Exercise a real self-hash-like metadata field: mutate case content, then
        # inject/refresh cases_sha256 over the mutated document so authentication
        # cannot be bypassed by self-describing hashes.
        self.assertNotIn("cases_sha256", document)
        body_without_hash = (json.dumps(mutated, indent=2, sort_keys=True) + "\n").encode("ascii")
        mutated["cases_sha256"] = hashlib.sha256(body_without_hash).hexdigest()
        poisoned_with_hash = (json.dumps(mutated, indent=2, sort_keys=True) + "\n").encode("ascii")
        # Refresh the self-hash after the metadata field itself is present.
        mutated["cases_sha256"] = hashlib.sha256(poisoned_with_hash).hexdigest()
        poisoned_bytes = (json.dumps(mutated, indent=2, sort_keys=True) + "\n").encode("ascii")
        self.assertEqual(mutated["cases_sha256"], hashlib.sha256(poisoned_with_hash).hexdigest())
        self.assertNotEqual(
            hashlib.sha256(poisoned_bytes).hexdigest(),
            capture_oracle.EXPECTED_CASES_SHA256,
        )

        with tempfile.TemporaryDirectory(prefix="ferricov-cases-auth-") as tmp:
            tmp_path = Path(tmp)
            poisoned_cases = tmp_path / "oracle-cases.mutated.json"
            poisoned_cases.write_bytes(poisoned_bytes)
            with self.assertRaises(SystemExit) as path_err:
                capture_oracle.validate_cases_request(poisoned_cases)
            self.assertIn("oracle-cases byte identity mismatch", str(path_err.exception))

            output_path = tmp_path / "out.json"
            argv = [
                "capture_oracle.py",
                "--cases",
                str(poisoned_cases),
                "--merge-into",
                str(capture_oracle.CANONICAL_BASELINE_PATH),
                "--output",
                str(output_path),
            ]
            for case_id in TF030_CASE_IDS:
                argv.extend(["--case-id", case_id])

            inspect_image = mock.Mock(side_effect=AssertionError("inspect_image called"))
            inspect_program = mock.Mock(side_effect=AssertionError("inspect_program called"))
            with mock.patch.object(capture_oracle, "inspect_image", inspect_image), mock.patch.object(
                capture_oracle, "inspect_program", inspect_program
            ), mock.patch("sys.argv", argv), self.assertRaises(SystemExit) as err:
                buf_out, buf_err = io.StringIO(), io.StringIO()
                with redirect_stdout(buf_out), redirect_stderr(buf_err):
                    capture_oracle.main()
            self.assertIn("oracle-cases byte identity mismatch", str(err.exception))
            inspect_image.assert_not_called()
            inspect_program.assert_not_called()
            self.assertFalse(output_path.exists())

        # Canonical basename alone is never trusted; content pin still rejects.
        with tempfile.TemporaryDirectory(prefix="ferricov-cases-path-") as tmp:
            alias = Path(tmp) / "oracle-cases.json"
            alias.write_bytes(poisoned_bytes)
            with self.assertRaises(SystemExit) as alias_err:
                capture_oracle.validate_cases_request(alias)
            self.assertIn("oracle-cases byte identity mismatch", str(alias_err.exception))


    def test_merge_into_validation_runs_before_docker_inspect(self) -> None:
        """Invalid merge inputs must reject before inspect_image/inspect_program."""
        import importlib
        import io
        import tempfile
        from contextlib import redirect_stderr, redirect_stdout
        from pathlib import Path
        from unittest import mock

        import capture_oracle
        from corpus_tf030 import TF030_CASE_IDS

        with tempfile.TemporaryDirectory(prefix="ferricov-pre-docker-") as tmp:
            tmp_path = Path(tmp)
            poisoned = tmp_path / "oracle-baseline.mutated.json"
            poisoned.write_bytes(b'{"schema_version":1,"cases":[]}\n')
            output_path = tmp_path / "out.json"
            argv = [
                "capture_oracle.py",
                "--cases",
                str(Path(__file__).resolve().parent / "oracle-cases.json"),
                "--merge-into",
                str(poisoned),
                "--output",
                str(output_path),
            ]
            for case_id in TF030_CASE_IDS:
                argv.extend(["--case-id", case_id])

            inspect_image = mock.Mock(side_effect=AssertionError("inspect_image called"))
            inspect_program = mock.Mock(side_effect=AssertionError("inspect_program called"))
            with mock.patch.object(capture_oracle, "inspect_image", inspect_image), mock.patch.object(
                capture_oracle, "inspect_program", inspect_program
            ), mock.patch("sys.argv", argv), self.assertRaises(SystemExit) as err:
                buf_out, buf_err = io.StringIO(), io.StringIO()
                with redirect_stdout(buf_out), redirect_stderr(buf_err):
                    capture_oracle.main()
            self.assertIn("canonical baseline path", str(err.exception))
            inspect_image.assert_not_called()
            inspect_program.assert_not_called()
            self.assertFalse(output_path.exists())

        # Trusted-bytes binding: validate returns the exact bytes later parsed.
        trusted = capture_oracle.validate_merge_into_request(
            capture_oracle.CANONICAL_BASELINE_PATH,
            list(TF030_CASE_IDS),
        )
        self.assertEqual(
            hashlib.sha256(trusted).hexdigest(),
            capture_oracle.EXPECTED_MERGE_BASELINE_SHA256,
        )
        parsed = capture_oracle.strict_json_loads_ascii(trusted, "trusted merge")
        self.assertEqual(len(parsed["cases"]), 271)





class Wave1TracefileMutationTests(unittest.TestCase):
    """Independent reverse mutations for wave-1 M0 Oracle evidence."""

    @classmethod
    def setUpClass(cls) -> None:
        from validate import (
            validate_wave1_mcdc_core_snapshot,
            validate_wave1_order_snapshot,
            validate_wave1_repeat_diff_tn_mcdc_snapshot,
            validate_wave1_repeat_same_tn_snapshot,
        )

        cls.validate_wave1_mcdc_core_snapshot = staticmethod(validate_wave1_mcdc_core_snapshot)
        cls.validate_wave1_order_snapshot = staticmethod(validate_wave1_order_snapshot)
        cls.validate_wave1_repeat_same_tn_snapshot = staticmethod(validate_wave1_repeat_same_tn_snapshot)
        cls.validate_wave1_repeat_diff_tn_mcdc_snapshot = staticmethod(validate_wave1_repeat_diff_tn_mcdc_snapshot)
        cls.baseline = strict_json_loads_ascii((ROOT / "oracle-baseline.json").read_bytes(), "oracle-baseline.json")
        cls.cases = {case["id"]: case for case in cls.baseline["cases"]}
        cls.case_defs = {
            case["id"]: case
            for case in strict_json_loads_ascii((ROOT / "oracle-cases.json").read_bytes(), "oracle-cases.json")["cases"]
        }

    def _snapshot(self, case_id: str) -> dict:
        observation = self.cases[case_id]
        raw = base64.b64decode(observation["stdout"]["base64"])
        return json.loads(raw.decode("ascii"))

    def test_wave1_case_and_fixture_closure(self) -> None:
        from corpus_wave1 import WAVE1_CASE_IDS, WAVE1_FIXTURE_IDS
        import generate

        fixture_ids = [fixture.id for fixture in generate.build_fixtures() if fixture.group == "wave1-tracefile"]
        self.assertEqual(fixture_ids, list(WAVE1_FIXTURE_IDS))
        case_ids = [
            case["id"]
            for case in strict_json_loads_ascii((ROOT / "oracle-cases.json").read_bytes(), "oracle-cases.json")["cases"]
            if case["id"].startswith("wave1-")
        ]
        self.assertEqual(case_ids, list(WAVE1_CASE_IDS))
        for case_id in WAVE1_CASE_IDS:
            self.assertIn(case_id, self.cases)
            self.assertEqual(self.cases[case_id]["exit_status"], self.case_defs[case_id]["expected_exit"])

    def test_wave1_mcdc_core_snapshot_mutations_are_rejected(self) -> None:
        document = self._snapshot("wave1-mcdc-core.semantic-snapshot")
        self.validate_wave1_mcdc_core_snapshot(document)
        mutations = []
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["aggregate"]["mcdc"]["found"] = 8
        mutations.append(mutated)
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["aggregate"]["mcdc"]["lines"]["3"]["groups"]["1"][0]["true_count"] = 1
        mutations.append(mutated)
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["aggregate"]["mcdc"]["lines"]["2"]["groups"].pop("0")
        mutations.append(mutated)
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["filename"] = "src/other.c"
        mutations.append(mutated)
        for index, document in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    self.validate_wave1_mcdc_core_snapshot(document)

    def test_wave1_order_snapshots_match_and_reject_drift(self) -> None:
        left = self._snapshot("wave1-order-canonical.semantic-snapshot")
        right = self._snapshot("wave1-order-permuted.semantic-snapshot")
        self.validate_wave1_order_snapshot(left, "wave1-order-canonical.semantic-snapshot")
        self.validate_wave1_order_snapshot(right, "wave1-order-permuted.semantic-snapshot")
        self.assertEqual(left["sources"][0]["aggregate"], right["sources"][0]["aggregate"])
        mutated = copy.deepcopy(left)
        mutated["sources"][0]["aggregate"]["branch"]["found"] = 1
        with self.assertRaises(ValueError):
            self.validate_wave1_order_snapshot(mutated, "wave1-order-canonical.semantic-snapshot")
        mutated = copy.deepcopy(left)
        mutated["sources"][0]["aggregate"]["mcdc"]["lines"]["1"]["groups"]["1"][0]["expression"] = "x"
        with self.assertRaises(ValueError):
            self.validate_wave1_order_snapshot(mutated, "wave1-order-canonical.semantic-snapshot")

    def test_wave1_repeat_same_tn_mutations_are_rejected(self) -> None:
        document = self._snapshot("wave1-repeat-same-tn.semantic-snapshot")
        self.validate_wave1_repeat_same_tn_snapshot(document)
        mutations = []
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["aggregate"]["line"]["lines"]["1"] = 2
        mutations.append(mutated)
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["aggregate"]["function"]["functions"]["1"]["aliases"]["f"] = 3
        mutations.append(mutated)
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["aggregate"]["branch"]["lines"]["1"]["blocks"].pop()
        mutations.append(mutated)
        for index, document in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    self.validate_wave1_repeat_same_tn_snapshot(document)

    def test_wave1_repeat_diff_tn_mcdc_mutations_are_rejected(self) -> None:
        document = self._snapshot("wave1-repeat-diff-tn-mcdc.semantic-snapshot")
        self.validate_wave1_repeat_diff_tn_mcdc_snapshot(document)
        mutations = []
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["testcases"]["mcdc"]["b"]["lines"]["1"]["groups"]["1"][0]["true_count"] = 1
        mutations.append(mutated)
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["testcases"]["line"].pop("b")
        mutations.append(mutated)
        mutated = copy.deepcopy(document)
        mutated["sources"][0]["aggregate"]["mcdc"]["hit"] = 2
        mutations.append(mutated)
        for index, document in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    self.validate_wave1_repeat_diff_tn_mcdc_snapshot(document)

    def test_wave1_rewrite_output_independent_facts(self) -> None:
        from validate import decode_identity

        checks = {
            "wave1-comments-core.canonical": lambda output: b"#" not in output and b"DA:1,1\n" in output,
            "wave1-tn-forget.canonical": lambda output: output
            == b"TN:\nSF:src/tn-forget.c\nDA:1,3\nLF:1\nLH:1\nend_of_record\n",
            "wave1-features-all.lines-only": lambda output: b"FNL:" not in output
            and b"BRDA:" not in output
            and b"MCDC:" not in output,
            "wave1-summary-payloads.canonical": lambda output: b"FNF:999" not in output
            and b"BRF:2\nBRH:1\n" in output
            and b"MCF:2\nMCH:1\n" in output,
            "wave1-mcdc-u-modes.clear-unreachable": lambda output: b",U1," not in output
            and b"MCDC:1,1,t,1,0,cond\n" in output,
            "wave1-repeat-same-tn.canonical": lambda output: b"DA:1,2\n" in output and b"FNA:0,3,f\n" in output,
        }
        for case_id, predicate in checks.items():
            observation = self.cases[case_id]
            output = decode_identity(observation["output"], case_id)
            self.assertTrue(predicate(output), case_id)
            # reverse: mutate an independent fact so the predicate must fail
            if case_id == "wave1-features-all.lines-only":
                poisoned = output + b"FNL:0,1,1\n"
            elif case_id == "wave1-mcdc-u-modes.clear-unreachable":
                poisoned = output.replace(b"MCDC:1,1,t,1,0,cond\n", b"MCDC:1,U1,t,1,0,cond\n", 1)
            elif case_id == "wave1-summary-payloads.canonical":
                poisoned = output.replace(b"BRF:2\n", b"BRF:9\n", 1)
            elif case_id == "wave1-comments-core.canonical":
                poisoned = b"# leaked\n" + output
            elif case_id == "wave1-tn-forget.canonical":
                poisoned = output.replace(b"DA:1,3\n", b"DA:1,1\n", 1)
            elif case_id == "wave1-repeat-same-tn.canonical":
                poisoned = output.replace(b"FNA:0,3,f\n", b"FNA:0,1,f\n", 1)
            else:
                poisoned = output + b"#mut\n"
            self.assertFalse(predicate(bytes(poisoned)), f"{case_id} poisoned still passes")


class Wave2TracefileMutationTests(unittest.TestCase):
    """Independent reverse mutations for wave-2 M0 Oracle evidence."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = strict_json_loads_ascii((ROOT / "oracle-baseline.json").read_bytes(), "oracle-baseline.json")
        cls.cases = {case["id"]: case for case in cls.baseline["cases"]}
        cls.case_defs = {
            case["id"]: case
            for case in strict_json_loads_ascii((ROOT / "oracle-cases.json").read_bytes(), "oracle-cases.json")["cases"]
        }

    def test_wave2_case_and_fixture_closure(self) -> None:
        from corpus_wave2 import WAVE2_CASE_IDS, WAVE2_FIXTURE_IDS
        import generate

        fixture_ids = [fixture.id for fixture in generate.build_fixtures() if fixture.group == "wave2-tracefile"]
        self.assertEqual(fixture_ids, list(WAVE2_FIXTURE_IDS))
        case_ids = [
            case["id"]
            for case in strict_json_loads_ascii((ROOT / "oracle-cases.json").read_bytes(), "oracle-cases.json")["cases"]
            if case["id"].startswith("wave2-")
        ]
        self.assertEqual(case_ids, list(WAVE2_CASE_IDS))
        for case_id in WAVE2_CASE_IDS:
            self.assertIn(case_id, self.cases)
            self.assertEqual(self.cases[case_id]["exit_status"], self.case_defs[case_id]["expected_exit"])

    def test_wave2_rewrite_output_independent_facts(self) -> None:
        from validate import decode_identity

        checks = {
            "wave2-framing-blank.canonical": lambda output: output
            == b"TN:blank\nSF:src/blank.c\nDA:1,1\nLF:1\nLH:1\nend_of_record\n",
            "wave2-tn-diff.canonical": lambda output: b"TN:,diff\n" in output
            and b"TN:name,diff\n" in output
            and b"TN:name\n" in output
            and b"TN:has_space\n" in output
            and b"TN:name,diff,extra\n" not in output,
            "wave2-kf-parity.canonical": lambda output: b"KF:" not in output
            and b"SF:src/kf2.c\n" in output
            and b"DA:1,2\nDA:2,1\n" in output,
            "wave2-da-accumulate.canonical": lambda output: b"DA:1,6\n" in output and b",chk" not in output,
            "wave2-da-checksum-store.canonical": lambda output: output
            == b"TN:chkstore\nSF:cs.c\nDA:1,3,AVO7Y115x231sZo9ymlVFA\nLF:1\nLH:1\nend_of_record\n",
            "wave2-summary-forms.canonical": lambda output: b"LF:2\nLH:1\n" in output and b"FNF:999" not in output,
            "wave2-unknown-tags.ignore-format": lambda output: b"DA:1,1\n" in output and b"TD:" not in output,
        }
        for case_id, predicate in checks.items():
            observation = self.cases[case_id]
            output = decode_identity(observation["output"], case_id)
            self.assertTrue(predicate(output), case_id)
            if case_id == "wave2-framing-blank.canonical":
                poisoned = output.replace(b"TN:blank\n", b"TN:blanked\n", 1)
            elif case_id == "wave2-tn-diff.canonical":
                poisoned = output.replace(b"TN:name,diff\n", b"TN:name,diff,extra\n", 1)
            elif case_id == "wave2-kf-parity.canonical":
                poisoned = output.replace(b"SF:src/kf.c\n", b"KF:src/kf.c\n", 1)
            elif case_id == "wave2-da-accumulate.canonical":
                poisoned = output.replace(b"DA:1,6\n", b"DA:1,1,chk\n", 1)
            elif case_id == "wave2-da-checksum-store.canonical":
                poisoned = output.replace(b",AVO7Y115x231sZo9ymlVFA", b"", 1)
            elif case_id == "wave2-summary-forms.canonical":
                poisoned = output.replace(b"LF:2\n", b"LF:333\n", 1)
            elif case_id == "wave2-unknown-tags.ignore-format":
                poisoned = b"TD:desc\n" + output
            else:
                poisoned = output + b"#mut\n"
            self.assertFalse(predicate(bytes(poisoned)), f"{case_id} poisoned still passes")



class WriterTracefileMutationTests(unittest.TestCase):
    """Independent reverse mutations for writer/converter/transport Oracle evidence."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = strict_json_loads_ascii((ROOT / "oracle-baseline.json").read_bytes(), "oracle-baseline.json")
        cls.cases = {case["id"]: case for case in cls.baseline["cases"]}
        cls.case_defs = {
            case["id"]: case
            for case in strict_json_loads_ascii((ROOT / "oracle-cases.json").read_bytes(), "oracle-cases.json")["cases"]
        }

    def test_writer_case_and_fixture_closure(self) -> None:
        from corpus_writer import WRITER_CASE_IDS, WRITER_FIXTURE_IDS
        import generate

        fixture_ids = [
            fixture.id
            for fixture in generate.build_fixtures()
            if fixture.group == "writer-tracefile"
        ]
        self.assertEqual(fixture_ids, list(WRITER_FIXTURE_IDS))
        case_ids = [
            case["id"]
            for case in strict_json_loads_ascii((ROOT / "oracle-cases.json").read_bytes(), "oracle-cases.json")["cases"]
            if case["id"].startswith(("writer-", "gzip-", "converter-coverage."))
        ]
        self.assertEqual(case_ids, list(WRITER_CASE_IDS))
        for case_id in WRITER_CASE_IDS:
            self.assertIn(case_id, self.cases)
            self.assertEqual(self.cases[case_id]["exit_status"], self.case_defs[case_id]["expected_exit"])

    def test_writer_rewrite_output_independent_facts(self) -> None:
        from validate import decode_identity
        from validation_common import (
            assert_converter_rewrite_observational,
            assert_py2lcov_no_functions_semantics,
            assert_py2lcov_with_functions_semantics,
            assert_writer_comment_semantics,
            assert_writer_fixedpoint_semantics,
            assert_writer_forbidden_semantics,
            assert_writer_mcdc_group_semantics,
            assert_writer_non_utf8_observational,
            assert_writer_order_semantics,
            assert_writer_summary_semantics,
            assert_xml2lcov_semantics,
        )

        checks = {
            "writer-order-core.canonical": assert_writer_order_semantics,
            "writer-mcdc-groups.canonical": assert_writer_mcdc_group_semantics,
            "writer-summaries.canonical": assert_writer_summary_semantics,
            "writer-comments.canonical": assert_writer_comment_semantics,
            "writer-forbidden.canonical": assert_writer_forbidden_semantics,
            "writer-fixedpoint.canonical": assert_writer_fixedpoint_semantics,
            "converter-coverage.xml2lcov": assert_xml2lcov_semantics,
            "converter-coverage.py2lcov-no-functions": assert_py2lcov_no_functions_semantics,
            "converter-coverage.py2lcov-with-functions": assert_py2lcov_with_functions_semantics,
            "converter-coverage.canonical-rewrite": assert_converter_rewrite_observational,
            "writer-non-utf8.canonical": assert_writer_non_utf8_observational,
        }
        for case_id, predicate in checks.items():
            observation = self.cases[case_id]
            output = decode_identity(observation["output"], case_id)
            predicate(output, case_id)
            if case_id == "writer-order-core.canonical":
                # reverse the two BRDA records in TN:z; parsed order must fail
                poisoned = output.replace(
                    b"BRDA:2,0,e,1\nBRDA:2,0,e2,0\n",
                    b"BRDA:2,0,e2,0\nBRDA:2,0,e,1\n",
                    1,
                )
            elif case_id == "writer-mcdc-groups.canonical":
                poisoned = output.replace(b"MCDC:1,10,t,1,0,big\n", b"MCDC:1,2,t,1,0,big\n", 1)
            elif case_id == "writer-summaries.canonical":
                poisoned = output.replace(b"LF:2\n", b"LF:999\n", 1)
            elif case_id == "writer-comments.canonical":
                poisoned = b"# leaked\n" + output
            elif case_id == "writer-forbidden.canonical":
                poisoned = output.replace(b"SF:src/k.c\n", b"KF:src/k.c\n", 1)
            elif case_id == "writer-fixedpoint.canonical":
                poisoned = output + b"#mut\n"
            elif case_id == "converter-coverage.xml2lcov":
                # inject MC/DC before end_of_record so section model must reject
                poisoned = output.replace(
                    b"end_of_record\n",
                    b"MCDC:1,1,t,1,0,x\nend_of_record\n",
                    1,
                )
            elif case_id == "converter-coverage.py2lcov-no-functions":
                # move FNL/FNA between the two BRDA records; family/record order must fail
                poisoned = output.replace(
                    b"BRDA:1,0,0,1\nBRDA:1,0,1,0\nFNL:0,1,1\nFNA:0,3,foo\n",
                    b"BRDA:1,0,0,1\nFNL:0,1,1\nFNA:0,3,foo\nBRDA:1,0,1,0\n",
                    1,
                )
            elif case_id == "converter-coverage.py2lcov-with-functions":
                poisoned = output.replace(b"FNF:2\n", b"FNF:1\n", 1)
            elif case_id == "converter-coverage.canonical-rewrite":
                # swap family order by moving first FNL after first BRDA block
                poisoned = output.replace(b"\nFNL:0,1,1\n", b"\n", 1).replace(
                    b"\nBRDA:1,0,0,1\n",
                    b"\nBRDA:1,0,0,1\nFNL:0,1,1\n",
                    1,
                )
            elif case_id == "writer-non-utf8.canonical":
                poisoned = output.replace(b"\xff", b"x", 1)
            else:
                poisoned = output + b"#mut\n"
            with self.assertRaises(ValueError, msg=f"{case_id} poisoned still passes"):
                predicate(bytes(poisoned), f"{case_id} poisoned")

    def test_writer_identity_self_hash_mutations_are_rejected(self) -> None:
        from validation_common import assert_identity_self_hash

        observation = self.cases["writer-order-core.canonical"]
        for stream in ("stdout", "stderr", "output"):
            identity = dict(observation[stream])
            assert_identity_self_hash(identity, f"{stream} good")
            poisoned = dict(identity)
            poisoned["sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                assert_identity_self_hash(poisoned, f"{stream} poisoned sha")
            if "base64" in identity:
                raw = base64.b64decode(identity["base64"])
                mutated = dict(identity)
                mutated["base64"] = base64.b64encode(raw + b"#mut").decode("ascii")
                # keep stale sha/size so self-hash must fail
                with self.assertRaises(ValueError):
                    assert_identity_self_hash(mutated, f"{stream} stale hash")

    def test_writer_gzip_transport_independent_facts(self) -> None:
        from validate import decode_identity
        from validation_common import assert_identity_self_hash

        valid = self.cases["gzip-valid.summary"]
        self.assertEqual(valid["exit_status"], 0)
        stdout = decode_identity(valid["stdout"], "gzip-valid stdout")
        self.assertIn(b"source files: 1", stdout)
        assert_identity_self_hash(valid["stdout"], "gzip-valid stdout identity")
        write_gz = self.cases["gzip-plain.write-gz"]
        raw = decode_identity(write_gz["output"], "gzip write")
        self.assertEqual(raw[:2], b"\x1f\x8b")
        assert_identity_self_hash(write_gz["output"], "gzip write identity")
        for case_id, needle in {
            "gzip-corrupt.summary": "integrity check failed for compressed file",
            "gzip-empty.summary": "no valid records found in tracefile",
            "gzip-valid.missing-gzip": "gzip command not available",
        }.items():
            observation = self.cases[case_id]
            self.assertEqual(observation["exit_status"], 1, case_id)
            stderr = decode_identity(observation["stderr"], f"{case_id} stderr").decode("utf-8", "replace")
            self.assertIn(needle, stderr)
            assert_identity_self_hash(observation["stderr"], f"{case_id} stderr identity")
            poisoned = stderr.replace(needle, "mutated diagnostic")
            self.assertNotIn(needle, poisoned)


if __name__ == "__main__":
    unittest.main()
