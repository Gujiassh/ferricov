from __future__ import annotations

import base64
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "compat/manifests"))

import validate as validator  # noqa: E402


def observed_manifest() -> dict:
    image_id = "sha256:" + "1" * 64
    peer_id = "sha256:" + "2" * 64
    package_lock = REPOSITORY_ROOT / "compat/upstream/packages.full.lock"
    tree_lock = REPOSITORY_ROOT / "compat/upstream/installed-tree.lock"
    stdout = b"lcov: LCOV version 2.5-beta\n"
    snapshot = b"[]\n"
    image_paths = {
        "build_inputs_lock": "compat/upstream/build-inputs.lock",
        "dockerfile": "compat/upstream/Dockerfile",
        "intersphinx_inventory": "compat/upstream/python-objects.inv",
        "intersphinx_patch": "compat/upstream/pin-intersphinx.py",
        "snapshot_ca_bundle": "compat/upstream/snapshot-ca-certificates.crt",
        "installed_tree_lock": "compat/upstream/installed-tree.lock",
        "installed_tree_script": "compat/upstream/installed-tree.sh",
        "package_closure_lock": "compat/upstream/packages.full.lock",
        "package_lock": "compat/upstream/packages.lock",
        "source_archive": "compat/upstream/lcov-v2.5.tar.gz",
    }
    image = {
        "base_image_digest": validator.BASE_IMAGE_DIGEST,
        "debian_snapshot": validator.DEBIAN_SNAPSHOT,
        "docker_image_id": image_id,
        "reference": image_id,
    }
    for field, path in image_paths.items():
        image[field] = path
        image[f"{field}_sha256"] = validator.sha256_file(REPOSITORY_ROOT / path)
    document = {
        "schema_version": 1,
        "manifest_id": "oracle-lcov-v2.5-image-smoke",
        "recorded_at": "2026-07-27T00:00:00Z",
        "status": "observed",
        "evidence": {"scope": "environment_smoke", "inventory_entries": []},
        "oracle_source": {
            "repository": "https://github.com/linux-test-project/lcov.git",
            "ref": "v2.5",
            "commit": validator.UPSTREAM_COMMIT,
        },
        "image": image,
        "platform": {
            "operating_system": "Debian GNU/Linux 12 (bookworm)",
            "architecture": "x86_64",
            "kernel": "test-kernel",
            "libc": "ldd (Debian GLIBC 2.36) 2.36",
            "target_triple": "x86_64-linux-gnu",
            "filesystem": "overlayfs",
        },
        "packages": {
            "count": len(package_lock.read_bytes().splitlines()),
            "manifest_sha256": validator.sha256_file(package_lock),
        },
        "installed_tree": {
            "entries": len(tree_lock.read_bytes().splitlines()),
            "manifest_sha256": validator.sha256_file(tree_lock),
        },
        "reproducibility": {
            "docker_image_ids": [image_id, peer_id],
            "package_closure_sha256": validator.sha256_file(package_lock),
            "installed_tree_sha256": validator.sha256_file(tree_lock),
            "key_files_sha256": "sha256:" + "3" * 64,
            "smoke_sha256": "sha256:" + "4" * 64,
        },
        "toolchain": [
            {
                "name": "gcc",
                "version": "12.2.0",
                "path": "/usr/bin/gcc",
                "sha256": "sha256:" + "5" * 64,
            }
        ],
        "executables": [
            {
                "name": "lcov",
                "path": "/usr/local/bin/lcov",
                "sha256": "sha256:" + "6" * 64,
            }
        ],
        "launcher": {
            "id": "oracle-image-smoke",
            "profile": "default",
            "configuration_sha256": "sha256:" + "0" * 64,
            "environment_variables": {"LC_ALL": "C", "TZ": "UTC"},
        },
        "execution": {
            "command": ["/usr/local/bin/lcov", "--version"],
            "working_directory": "/work",
            "user": "root",
            "network": "none",
            "mounts": [
                {
                    "id": "work-output",
                    "type": "bind",
                    "source": "runtime-output",
                    "destination": "/work",
                    "read_only": False,
                }
            ],
        },
        "fixtures": [],
        "outputs": {
            "exit_code": 0,
            "stdout": {
                "bytes": len(stdout),
                "sha256": validator.sha256_bytes(stdout),
                "content_base64": base64.b64encode(stdout).decode("ascii"),
            },
            "stderr": {
                "bytes": 0,
                "sha256": validator.sha256_bytes(b""),
                "content_base64": "",
            },
            "filesystem": {
                "entries": 0,
                "snapshot_sha256": validator.sha256_bytes(snapshot),
                "snapshot_base64": base64.b64encode(snapshot).decode("ascii"),
            },
        },
    }
    document["image"]["labels"] = validator.expected_labels(document)
    document["launcher"]["configuration_sha256"] = validator.canonical_json_sha256(
        validator.launcher_configuration(document)
    )
    return document


class ExecutionManifestValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(
            (REPOSITORY_ROOT / "compat/schema/execution-manifest.schema.json").read_text()
        )

    def validate(self, document: dict, root: Path = REPOSITORY_ROOT) -> None:
        validator.validate_document(document, self.schema, root)

    @staticmethod
    def rehash_launcher(document: dict) -> None:
        document["launcher"]["configuration_sha256"] = (
            validator.canonical_json_sha256(validator.launcher_configuration(document))
        )

    def test_accepts_complete_observed_manifest(self) -> None:
        self.validate(observed_manifest())

    def test_accepts_explicit_posix_launcher_environment(self) -> None:
        document = observed_manifest()
        document["launcher"]["profile"] = "posixly_correct"
        document["launcher"]["environment_variables"]["POSIXLY_CORRECT"] = "1"
        self.rehash_launcher(document)
        self.validate(document)

    def test_rejects_posix_profile_without_effective_variable(self) -> None:
        document = observed_manifest()
        document["launcher"]["profile"] = "posixly_correct"
        self.rehash_launcher(document)
        with self.assertRaisesRegex(validator.ManifestValidationError, "POSIXLY_CORRECT"):
            self.validate(document)

    def test_rejects_launcher_environment_mutation_without_rehash(self) -> None:
        document = observed_manifest()
        document["launcher"]["environment_variables"]["TZ"] = "Asia/Shanghai"
        with self.assertRaisesRegex(
            validator.ManifestValidationError, "configuration_sha256"
        ):
            self.validate(document)

    def test_rejects_mutable_image_reference(self) -> None:
        document = observed_manifest()
        document["image"]["reference"] = "ferricov/lcov-oracle:v2.5"
        with self.assertRaisesRegex(validator.ManifestValidationError, "immutable"):
            self.validate(document)

    def test_rejects_source_archive_hash_mutation(self) -> None:
        document = observed_manifest()
        document["image"]["source_archive_sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(validator.ManifestValidationError, "source_archive"):
            self.validate(document)

    def test_rejects_missing_or_extra_build_label(self) -> None:
        for mutation in ("missing", "extra"):
            with self.subTest(mutation=mutation):
                document = observed_manifest()
                if mutation == "missing":
                    document["image"]["labels"].pop("dev.ferricov.source-date-epoch")
                else:
                    document["image"]["labels"]["unreviewed.label"] = "value"
                with self.assertRaises(validator.ManifestValidationError):
                    self.validate(document)

    def test_rejects_package_closure_hash_or_count_mutation(self) -> None:
        for field, value in (
            ("manifest_sha256", "sha256:" + "0" * 64),
            ("count", validator.EXPECTED_PACKAGE_COUNT - 1),
        ):
            with self.subTest(field=field):
                document = observed_manifest()
                document["packages"][field] = value
                with self.assertRaisesRegex(validator.ManifestValidationError, "packages"):
                    self.validate(document)

    def test_rejects_installed_tree_hash_or_count_mutation(self) -> None:
        for field, value in (
            ("manifest_sha256", "sha256:" + "0" * 64),
            ("entries", validator.EXPECTED_INSTALLED_TREE_ENTRIES - 1),
        ):
            with self.subTest(field=field):
                document = observed_manifest()
                document["installed_tree"][field] = value
                with self.assertRaisesRegex(
                    validator.ManifestValidationError, "installed_tree"
                ):
                    self.validate(document)

    def test_rejects_self_declared_lock_verified_flag(self) -> None:
        document = observed_manifest()
        document["packages"]["closure_lock_verified"] = True
        with self.assertRaisesRegex(validator.ManifestValidationError, "Additional"):
            self.validate(document)

    def test_rejects_direct_package_version_not_in_closure(self) -> None:
        document = observed_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for field in (
                "build_inputs_lock",
                "dockerfile",
                "intersphinx_inventory",
                "intersphinx_patch",
                "snapshot_ca_bundle",
                "installed_tree_lock",
                "installed_tree_script",
                "package_closure_lock",
                "package_lock",
                "source_archive",
            ):
                source = REPOSITORY_ROOT / document["image"][field]
                target = root / document["image"][field]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            direct = root / document["image"]["package_lock"]
            direct.write_text(
                direct.read_text(encoding="ascii").replace(
                    "gcc=4:12.2.0-3", "gcc=0:0-0"
                ),
                encoding="ascii",
            )
            document["image"]["package_lock_sha256"] = validator.sha256_file(direct)
            with self.assertRaisesRegex(
                validator.ManifestValidationError, "not exact"
            ):
                self.validate(document, root)

    def test_rejects_rebuild_identity_or_evidence_hash_mutation(self) -> None:
        mutations = (
            ("docker_image_ids", ["sha256:" + "2" * 64] * 2),
            ("package_closure_sha256", "sha256:" + "0" * 64),
            ("installed_tree_sha256", "sha256:" + "0" * 64),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                document = observed_manifest()
                document["reproducibility"][field] = value
                with self.assertRaisesRegex(
                    validator.ManifestValidationError, "reproducibility"
                ):
                    self.validate(document)

    def test_rejects_retained_stream_mutation(self) -> None:
        document = observed_manifest()
        document["outputs"]["stdout"]["content_base64"] = base64.b64encode(
            b"different\n"
        ).decode("ascii")
        with self.assertRaisesRegex(validator.ManifestValidationError, "stdout"):
            self.validate(document)

    def test_rejects_retained_filesystem_snapshot_mutation(self) -> None:
        document = observed_manifest()
        document["outputs"]["filesystem"]["snapshot_base64"] = base64.b64encode(
            b"[{}]\n"
        ).decode("ascii")
        with self.assertRaisesRegex(validator.ManifestValidationError, "filesystem"):
            self.validate(document)

    def test_rejects_unidentified_bind_mount_source(self) -> None:
        document = observed_manifest()
        document["execution"]["mounts"][0]["source"] = "unhashed-host-path"
        self.rehash_launcher(document)
        with self.assertRaisesRegex(
            validator.ManifestValidationError, "content-identified"
        ):
            self.validate(document)

    def test_rejects_unidentified_command_program(self) -> None:
        document = observed_manifest()
        document["execution"]["command"][0] = "/usr/local/bin/not-recorded"
        self.rehash_launcher(document)
        with self.assertRaisesRegex(
            validator.ManifestValidationError, "content-identified executable"
        ):
            self.validate(document)

    def test_rejects_unpinned_oracle_source(self) -> None:
        document = observed_manifest()
        document["oracle_source"]["commit"] = "0" * 40
        with self.assertRaises(validator.ManifestValidationError):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
