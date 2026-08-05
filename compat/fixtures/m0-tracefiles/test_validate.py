#!/usr/bin/env python3
"""Focused mutation tests for retained tracefile semantic snapshots."""

from __future__ import annotations

import base64
import copy
import hashlib
import sys
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


if __name__ == "__main__":
    unittest.main()



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

    def test_tf030_scalar_and_category_mutations_are_rejected(self) -> None:
        document = self._snapshot("numeric-format-atoms.tf030.semantic-snapshot")
        for field, value in (
            ("category", "format"),
            ("looks_like_number", False),
            ("record_matched", False),
            ("retained", False),
        ):
            mutated = copy.deepcopy(document)
            mutated["numeric_rows"][0][field] = value if field != "category" else "excessive"
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate_tf030_numeric_rows(
                    mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
                )
        mutated = copy.deepcopy(document)
        mutated["numeric_rows"][0]["sv_before"]["iok"] = not mutated["numeric_rows"][0]["sv_before"]["iok"]
        with self.assertRaises(ValueError):
            # projection shape still valid, but category/recovery path for this row remains checked
            # force an invalid projection class instead
            mutated["numeric_rows"][0]["sv_before"]["class"] = "NotB"
            self.validate_tf030_numeric_rows(
                mutated, expected_count=12, case_id="numeric-format-atoms.tf030.semantic-snapshot"
            )

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

