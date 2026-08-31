from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

COMPAT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(COMPAT_ROOT))

import verify  # noqa: E402


class InventorySemanticValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = json.loads(
            (COMPAT_ROOT / "inventory/v2.5.json").read_text(encoding="utf-8")
        )

    def validate(self, inventory: dict[str, object]) -> None:
        with tempfile.TemporaryDirectory(prefix="ferricov-verify-test-") as directory:
            path = Path(directory) / "inventory.json"
            path.write_text(json.dumps(inventory), encoding="utf-8")
            verify.validate_inventory_semantics(path)

    def option(self, inventory: dict[str, object], option_id: str) -> dict[str, object]:
        for command in inventory["commands"]:
            for option in command["options"]:
                if option["id"] == option_id:
                    return option
        self.fail(f"missing option {option_id}")

    def test_canonical_inventory_passes(self) -> None:
        self.validate(self.inventory)

    def test_same_count_profile_identity_swap_fails(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        accepted = self.option(inventory, "command.lcov.option.build-dir")
        unknown = self.option(inventory, "command.lcov.option.annotate-script")
        accepted["profile_parser_resolution"]["default_profile"], unknown[
            "profile_parser_resolution"
        ]["default_profile"] = (
            unknown["profile_parser_resolution"]["default_profile"],
            accepted["profile_parser_resolution"]["default_profile"],
        )

        with self.assertRaisesRegex(RuntimeError, "profile parser resolution drift"):
            self.validate(inventory)

    def test_public_option_cannot_own_a_profile_resolution(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        public = self.option(inventory, "command.lcov.option.help")
        generated = self.option(inventory, "command.lcov.option.annotate-script")
        public["profile_parser_resolution"] = copy.deepcopy(
            generated["profile_parser_resolution"]
        )

        with self.assertRaisesRegex(RuntimeError, "exactly and exclusively"):
            self.validate(inventory)


class InventoryRegenerationCommandTests(unittest.TestCase):
    def test_review_overlay_is_passed_before_output(self) -> None:
        root = Path("/workspace/ferricov")

        command = verify.inventory_regeneration_command(
            root,
            Path("/tmp/upstream"),
            Path("/tmp/help"),
            Path("/tmp/inventory.json"),
        )

        self.assertEqual(
            command[-4:],
            [
                "/tmp/upstream",
                "/tmp/help",
                "/workspace/ferricov/compat/inventory/review",
                "/tmp/inventory.json",
            ],
        )

    def test_oracle_build_environment_sets_portable_checkout(self) -> None:
        base = {"PATH": "/usr/bin", "LCOV_SOURCE_ROOT": "/stale"}

        environment = verify.oracle_build_environment(
            base,
            Path("/tmp/upstream"),
            Path("/tmp/oracle-manifest.json"),
        )

        self.assertEqual(environment["PATH"], "/usr/bin")
        self.assertEqual(environment["LCOV_SOURCE_ROOT"], "/tmp/upstream")
        self.assertEqual(
            environment["ORACLE_MANIFEST"], "/tmp/oracle-manifest.json"
        )
        self.assertEqual(base["LCOV_SOURCE_ROOT"], "/stale")

    def test_oracle_image_id_is_loaded_from_manifest(self) -> None:
        image_id = "sha256:" + "a" * 64
        with tempfile.TemporaryDirectory(prefix="ferricov-manifest-test-") as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "image": {
                            "docker_image_id": image_id,
                            "reference": image_id,
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(verify.load_oracle_image_id(manifest), image_id)

    def test_oracle_image_id_rejects_mutable_or_mismatched_reference(self) -> None:
        image_id = "sha256:" + "a" * 64
        invalid_images = (
            {
                "docker_image_id": "ferricov/lcov-oracle:v2.5",
                "reference": "ferricov/lcov-oracle:v2.5",
            },
            {
                "docker_image_id": image_id,
                "reference": "sha256:" + "b" * 64,
            },
        )
        for image in invalid_images:
            with self.subTest(image=image):
                with tempfile.TemporaryDirectory(
                    prefix="ferricov-manifest-test-"
                ) as directory:
                    manifest = Path(directory) / "manifest.json"
                    manifest.write_text(
                        json.dumps({"image": image}),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(RuntimeError, "Oracle"):
                        verify.load_oracle_image_id(manifest)


if __name__ == "__main__":
    unittest.main()

class InventoryPinSourceTests(unittest.TestCase):
    def test_committed_pins_match_loaded_constants(self) -> None:
        pins = verify.load_inventory_pins()
        self.assertEqual(pins["commands"], verify.EXPECTED_COMMANDS)
        self.assertEqual(pins["policy_families"], verify.EXPECTED_POLICY_FAMILIES)
        self.assertEqual(
            {k: list(v) for k, v in verify.EXPECTED_GENERATED_TOKEN_NAMES.items()},
            pins["generated_token_names"],
        )

    def test_pin_file_mutation_is_visible_to_loader(self) -> None:
        original = Path(verify.PIN_PATH).read_text(encoding="utf-8")
        try:
            document = json.loads(original)
            document["commands"]["lcov"] = int(document["commands"]["lcov"]) + 1
            with tempfile.TemporaryDirectory(prefix="ferricov-pins-") as directory:
                path = Path(directory) / "pins.json"
                path.write_text(json.dumps(document), encoding="utf-8")
                loaded = verify.load_inventory_pins(path)
                self.assertEqual(loaded["commands"]["lcov"], document["commands"]["lcov"])
                self.assertNotEqual(loaded["commands"]["lcov"], verify.EXPECTED_COMMANDS["lcov"])
        finally:
            Path(verify.PIN_PATH).write_text(original, encoding="utf-8")


class M0StatusSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = COMPAT_ROOT.parent

    def test_committed_snapshot_matches_live_contracts(self) -> None:
        verify.validate_m0_status_snapshot(self.root)

    def test_stale_residual_prose_is_rejected(self) -> None:
        target = self.root / "docs/ssot/compatibility-contract.md"
        original = target.read_text(encoding="utf-8")
        try:
            # Inject a known stale residual phrase; live docs no longer contain
            # the historical "88 explicit M0 gaps" literal used by older pins.
            injected = original.rstrip() + "\n\n91 explicit M0 gaps remain as a stale phrase.\n"
            target.write_text(injected, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "stale M0 gap count 91"):
                verify.validate_m0_status_snapshot(self.root)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_snapshot_drift_is_rejected(self) -> None:
        target = self.root / "docs/ssot/m0-status.snapshot.json"
        original = target.read_text(encoding="utf-8")
        try:
            document = json.loads(original)
            document["behavior"]["uncovered_public_entries"] = (
                int(document["behavior"]["uncovered_public_entries"]) + 1
            )
            target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "out of date with live contracts"):
                verify.validate_m0_status_snapshot(self.root)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_conditional_go_authorizes_m1_without_product_evidence(self) -> None:
        snapshot = verify.build_m0_status_snapshot(self.root)
        self.assertIs(snapshot["m1_authorized"], True)
        self.assertIs(snapshot["product_compatibility_evidence"], False)
        self.assertEqual(
            snapshot["m1_authorized_task_ids"],
            [f"M1-CORE-{index:03d}" for index in range(1, 10)],
        )
        self.assertEqual(
            snapshot["model_blocked_case_ids"],
            ["M1-MD-020", "M1-TF-063", "M1-TF-064"],
        )
        treatments = {
            blocker["id"]: blocker.get("activation_treatment")
            for blocker in snapshot["m1_activation_blockers"]
        }
        self.assertEqual(
            treatments.get("behavior_primary_gaps"),
            "excluded_by_m1_v0_1_support_matrix",
        )
        self.assertEqual(
            treatments.get("diagnostics_unbound_planned_cases"),
            "excluded_by_m1_v0_1_support_matrix",
        )
        self.assertEqual(
            treatments.get("M1-MD-020"),
            "excluded_by_m1_v0_1_support_matrix",
        )
        self.assertEqual(
            treatments.get("product_compatibility_evidence_false"),
            "required_false_under_conditional_go",
        )
        self.assertEqual(
            snapshot["sources"].get("m1_v0_1_support_matrix"),
            "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md",
        )
        # Process NO-GO / undecided blockers must be absent under active GO.
        self.assertNotIn("m0_exit_review_no_go", treatments)
        self.assertNotIn("m0_exit_review_undecided", treatments)
        self.assertNotIn("m1_support_matrix_missing", treatments)

    def _mutate_activation_contract(self, mutate, expected_error: str) -> None:
        target = self.root / "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.activation.json"
        original = target.read_text(encoding="utf-8")
        try:
            document = json.loads(original)
            mutate(document)
            target.write_text(
                json.dumps(document, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, expected_error):
                verify.build_m0_status_snapshot(self.root)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_activation_contract_rejects_core_010_or_011_authorization(self) -> None:
        for task_id in ("M1-CORE-010", "M1-CORE-011"):
            with self.subTest(task_id=task_id):
                def mutate(document, task_id=task_id):
                    document["unauthorized_tasks"] = [
                        task for task in document["unauthorized_tasks"]
                        if task["id"] != task_id
                    ]
                    document["authorized_tasks"].append(
                        {"id": task_id, "state": "authorized_bounded"}
                    )
                self._mutate_activation_contract(mutate, "authorize exactly CORE-001 through CORE-009")

    def test_activation_contract_rejects_missing_or_duplicate_task(self) -> None:
        mutations = (
            lambda document: document["authorized_tasks"].pop(0),
            lambda document: document["authorized_tasks"].append(
                dict(document["authorized_tasks"][0])
            ),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self._mutate_activation_contract(mutate, "authorize exactly CORE-001 through CORE-009")

    def test_activation_contract_rejects_deleted_exclusion(self) -> None:
        self._mutate_activation_contract(
            lambda document: document["exclusions"]["C"].pop(),
            "exclusions A-D",
        )

    def test_activation_contract_rejects_changed_signature(self) -> None:
        self._mutate_activation_contract(
            lambda document: document.__setitem__("signature", "broadened"),
            "invalid signature",
        )

    def test_activation_contract_rejects_deleted_non_negotiable(self) -> None:
        self._mutate_activation_contract(
            lambda document: document["non_negotiables"].pop(),
            "non-negotiables",
        )

    def test_activation_contract_rejects_noncanonical_json(self) -> None:
        target = self.root / "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.activation.json"
        original = target.read_text(encoding="utf-8")
        try:
            target.write_text(json.dumps(json.loads(original)), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "not canonical JSON"):
                verify.build_m0_status_snapshot(self.root)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_activation_requires_exact_live_model_blocked_case_ids(self) -> None:
        target = self.root / "compat/model/v2.5.json"
        original = target.read_text(encoding="utf-8")
        try:
            for blocked_ids in (
                ["M1-MD-020", "M1-TF-063"],
                ["M1-MD-020", "M1-TF-063", "M1-TF-064", "M1-EXTRA-001"],
            ):
                with self.subTest(blocked_ids=blocked_ids):
                    document = json.loads(original)
                    document["blocked_case_ids"] = blocked_ids
                    target.write_text(
                        json.dumps(document, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(RuntimeError, "requires exact live blocked_case_ids"):
                        verify.build_m0_status_snapshot(self.root)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_generated_markdown_block_rejects_every_authority_drift(self) -> None:
        matrix = self.root / "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md"
        original = matrix.read_text(encoding="utf-8")
        mutations = (
            ("- Status: `active`", "- Status: `draft`"),
            ("- `M1-CORE-009`: `authorized_bounded`", "- `M1-CORE-009`: `unauthorized`"),
            ("- `M1-CORE-010`: `unauthorized`", "- `M1-CORE-010`: `authorized_bounded`"),
            ("- A: `command.geninfo.option.compat-libtool`", "- A: `deleted`"),
            ("- `signed_na_not_hollow_closed`", "- `deleted_non_negotiable`"),
            ("- Budgets: harness safety controls only; never product limits", "- Budgets: product limits"),
            ("- Signature: `conditional-m1-core", "- Signature: `broadened-conditional-m1-core"),
        )
        try:
            for old, new in mutations:
                with self.subTest(old=old):
                    self.assertIn(old, original)
                    matrix.write_text(original.replace(old, new, 1), encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, "generated activation block differs"):
                        verify.build_m0_status_snapshot(self.root)
                    matrix.write_text(original, encoding="utf-8")
        finally:
            matrix.write_text(original, encoding="utf-8")

    def test_activation_exclusion_a_is_live_bound_to_behavior_gaps(self) -> None:
        target = self.root / "compat/behavior/contract.json"
        original = target.read_text(encoding="utf-8")
        try:
            for mutation in ("remove", "add"):
                with self.subTest(mutation=mutation):
                    document = json.loads(original)
                    if mutation == "remove":
                        group = next(item for item in document["case_groups"] if item["review_status"] != "reviewed")
                        group["review_status"] = "reviewed"
                    else:
                        group = next(item for item in document["case_groups"] if item["review_status"] == "reviewed" and len([target for target in item.get("targets") or [] if target.get("role") == "primary"]) == 1)
                        group["review_status"] = "unreviewed"
                    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, "exclusion A must equal exact live behavior gap IDs"):
                        verify.build_m0_status_snapshot(self.root)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_activation_exclusion_b_is_live_bound_to_unbound_diagnostics(self) -> None:
        target = self.root / "compat/diagnostics/v2.5.json"
        original = target.read_text(encoding="utf-8")
        try:
            for mutation in ("remove", "add"):
                with self.subTest(mutation=mutation):
                    document = json.loads(original)
                    if mutation == "remove":
                        document["planned_case_ids"].remove("PAR-GENINFO-CHILD-EXIT-FERRICOV-001")
                    else:
                        document["planned_case_ids"].append("PAR-FERRICOV-EXTRA-001")
                    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, "exclusion B must equal exact live unbound diagnostics IDs"):
                        verify.build_m0_status_snapshot(self.root)
        finally:
            target.write_text(original, encoding="utf-8")

