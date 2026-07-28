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
