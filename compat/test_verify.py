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

    def test_conditional_go_fails_closed_without_active_matrix(self) -> None:
        matrix = self.root / "specs/001-full-lcov-compatibility/m1-v0.1-support-matrix.md"
        original = matrix.read_text(encoding="utf-8")
        try:
            matrix.write_text(
                original.replace("Status: **ACTIVE**", "Status: **DRAFT**", 1),
                encoding="utf-8",
            )
            snapshot = verify.build_m0_status_snapshot(self.root)
            self.assertIs(snapshot["m1_authorized"], False)
            ids = {b["id"] for b in snapshot["m1_activation_blockers"]}
            self.assertIn("m1_support_matrix_inactive", ids)
        finally:
            matrix.write_text(original, encoding="utf-8")

