#!/usr/bin/env python3
"""Validate Ferricov execution manifests and optionally re-run Docker evidence."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = REPOSITORY_ROOT / "compat/schema/execution-manifest.schema.json"
DEFAULT_MANIFESTS = Path(__file__).resolve().parent
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
EXPECTED_PACKAGE_COUNT = 284
EXPECTED_INSTALLED_TREE_ENTRIES = 321
BASE_IMAGE_DIGEST = "sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818"
DEBIAN_SNAPSHOT = "20260713T000000Z"
LCOV_BUILD_DATE = "2026-07-06"
SOURCE_DATE_EPOCH = "1783375223"
EXPECTED_SCHEMA_SHA256 = "sha256:9ef727a0a809d6f0f4507f4ad32ecab8bb550abb96c1d3d9b309ae7f63fe1e8a"
COMMANDS = (
    "lcov",
    "genhtml",
    "geninfo",
    "genpng",
    "gendesc",
    "perl2lcov",
    "py2lcov",
    "xml2lcov",
    "xml2lcovutil.py",
    "llvm2lcov",
)
KEY_PATHS = (
    "/usr/local/bin/lcov",
    "/usr/local/bin/genhtml",
    "/usr/local/bin/geninfo",
    "/usr/local/bin/genpng",
    "/usr/local/bin/gendesc",
    "/usr/local/bin/perl2lcov",
    "/usr/local/bin/py2lcov",
    "/usr/local/bin/xml2lcov",
    "/usr/local/bin/xml2lcovutil.py",
    "/usr/local/bin/llvm2lcov",
    "/usr/local/etc/lcovrc",
    "/usr/local/lib/lcov/lcovutil.pm",
    "/usr/local/share/lcov/support-scripts/context.pm",
    "/usr/local/share/lcov/support-scripts/gitblame",
    "/usr/local/share/lcov/support-scripts/history.pm",
    "/usr/local/share/lcov/html/index.html",
    "/usr/local/share/lcov/html/objects.inv",
    "/usr/local/share/man/man1/lcov.1",
)


class ManifestValidationError(ValueError):
    """An execution manifest is structurally or semantically invalid."""


def sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    return sha256_bytes(encoded + b"\n")


def launcher_configuration(document: dict[str, Any]) -> dict[str, Any]:
    execution = document["execution"]
    return {
        "command": execution["command"],
        "environment_variables": document["launcher"]["environment_variables"],
        "mounts": execution["mounts"],
        "network": execution["network"],
        "user": execution["user"],
        "working_directory": execution["working_directory"],
    }


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and value == path.as_posix()
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def fixture_tree_manifest(root: Path) -> bytes:
    entries: list[dict[str, Any]] = []
    root_bytes = os.fsencode(root)
    for directory, directories, files in os.walk(root_bytes, followlinks=False):
        directories.sort()
        files.sort()
        for name in [*directories, *files]:
            path = os.path.join(directory, name)
            relative = os.path.relpath(path, root_bytes)
            metadata = os.lstat(path)
            entry: dict[str, Any] = {
                "mode": stat.S_IMODE(metadata.st_mode),
                "path_bytes_hex": relative.hex(),
            }
            if stat.S_ISLNK(metadata.st_mode):
                entry["kind"] = "symlink"
                entry["target_bytes_hex"] = os.fsencode(os.readlink(path)).hex()
            elif stat.S_ISDIR(metadata.st_mode):
                entry["kind"] = "directory"
            elif stat.S_ISREG(metadata.st_mode):
                entry["kind"] = "file"
                entry["sha256"] = sha256_file(Path(os.fsdecode(path)))
            else:
                raise ManifestValidationError(
                    f"unsupported fixture entry kind: {os.fsdecode(path)}"
                )
            entries.append(entry)
    entries.sort(key=lambda entry: entry["path_bytes_hex"])
    return (
        json.dumps(entries, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("ascii")


def fixture_tree_sha256(root: Path) -> str:
    return sha256_bytes(fixture_tree_manifest(root))


def expected_labels(document: dict[str, Any]) -> dict[str, str]:
    image = document["image"]
    return {
        "dev.ferricov.base-image-digest": BASE_IMAGE_DIGEST,
        "dev.ferricov.build-date": LCOV_BUILD_DATE,
        "dev.ferricov.build-inputs-lock-sha256": image[
            "build_inputs_lock_sha256"
        ],
        "dev.ferricov.debian-snapshot": DEBIAN_SNAPSHOT,
        "dev.ferricov.intersphinx-inventory-sha256": image[
            "intersphinx_inventory_sha256"
        ],
        "dev.ferricov.snapshot-ca-bundle-sha256": image[
            "snapshot_ca_bundle_sha256"
        ],
        "dev.ferricov.source-archive-sha256": image["source_archive_sha256"],
        "dev.ferricov.source-date-epoch": SOURCE_DATE_EPOCH,
        "org.opencontainers.image.revision": UPSTREAM_COMMIT,
        "org.opencontainers.image.source": "https://github.com/linux-test-project/lcov",
        "org.opencontainers.image.version": "v2.5",
    }


def _schema_errors(
    document: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    return [
        f"schema {'.'.join(str(part) for part in error.absolute_path) or '<root>'}: "
        f"{error.message}"
        for error in errors
    ]


def _semantic_errors(
    document: dict[str, Any], repository_root: Path
) -> list[str]:
    errors: list[str] = []

    for field in (
        "build_inputs_lock",
        "source_archive",
        "intersphinx_inventory",
        "intersphinx_patch",
        "snapshot_ca_bundle",
        "dockerfile",
        "package_lock",
        "package_closure_lock",
        "installed_tree_lock",
        "installed_tree_script",
    ):
        value = document["image"][field]
        if not _safe_relative_path(value):
            errors.append(f"image.{field} is not a safe repository-relative path: {value}")
            continue
        path = repository_root / value
        if not path.is_file():
            errors.append(f"image.{field} does not exist: {value}")
            continue
        expected = document["image"][f"{field}_sha256"]
        actual = sha256_file(path)
        if actual != expected:
            errors.append(
                f"image.{field}_sha256 mismatch: expected {expected}, found {actual}"
            )

    image = document["image"]
    if image["reference"] != image["docker_image_id"]:
        errors.append("image.reference must be the immutable Docker image ID")
    if image["base_image_digest"] != BASE_IMAGE_DIGEST:
        errors.append("image.base_image_digest does not match the pinned base image")
    if image["debian_snapshot"] != DEBIAN_SNAPSHOT:
        errors.append("image.debian_snapshot does not match the pinned snapshot")

    source_archive = repository_root / image["source_archive"]
    if source_archive.is_file():
        try:
            with tarfile.open(source_archive, "r:gz") as archive:
                if archive.pax_headers.get("comment") != UPSTREAM_COMMIT:
                    errors.append("source archive does not identify the pinned LCOV commit")
                names = archive.getnames()
                if not names or any(
                    name != "lcov-v2.5" and not name.startswith("lcov-v2.5/")
                    for name in names
                ):
                    errors.append("source archive contains an unexpected path prefix")
        except tarfile.TarError as error:
            errors.append(f"source archive is not a valid gzip tar archive: {error}")

    build_inputs_lock = repository_root / image["build_inputs_lock"]
    if build_inputs_lock.is_file():
        values: dict[str, str] = {}
        for line in build_inputs_lock.read_text(encoding="ascii").splitlines():
            if "=" not in line:
                errors.append("build_inputs_lock contains a malformed entry")
                continue
            key, value = line.split("=", 1)
            if key in values:
                errors.append(f"build_inputs_lock contains duplicate key: {key}")
            values[key] = value
        expected_values = {
            "lcov_source_archive_producer": "git-archive-tar-umask-0022+gzip-n-9",
            "lcov_source_archive_bytes": str(source_archive.stat().st_size)
            if source_archive.is_file()
            else "missing",
            "lcov_source_archive_sha256": image["source_archive_sha256"].removeprefix(
                "sha256:"
            ),
            "lcov_source_commit": UPSTREAM_COMMIT,
            "lcov_source_tree": "2b923cc012113c191db5969a8a5b81caf4d22c10",
            "python_objects_inv_bytes": str(
                (repository_root / image["intersphinx_inventory"]).stat().st_size
            )
            if (repository_root / image["intersphinx_inventory"]).is_file()
            else "missing",
            "python_objects_inv_sha256": image[
                "intersphinx_inventory_sha256"
            ].removeprefix("sha256:"),
            "python_objects_inv_project": "Python",
            "python_objects_inv_url": "https://docs.python.org/3.14/objects.inv",
            "python_objects_inv_version": "3.14",
            "pin_intersphinx_bytes": str(
                (repository_root / image["intersphinx_patch"]).stat().st_size
            )
            if (repository_root / image["intersphinx_patch"]).is_file()
            else "missing",
            "pin_intersphinx_sha256": image["intersphinx_patch_sha256"].removeprefix(
                "sha256:"
            ),
            "snapshot_ca_bundle_bytes": str(
                (repository_root / image["snapshot_ca_bundle"]).stat().st_size
            )
            if (repository_root / image["snapshot_ca_bundle"]).is_file()
            else "missing",
            "snapshot_ca_bundle_certificates": "142",
            "snapshot_ca_bundle_producer": "concatenate-sorted-ca-certificates-mozilla-crt",
            "snapshot_ca_bundle_sha256": image[
                "snapshot_ca_bundle_sha256"
            ].removeprefix("sha256:"),
            "snapshot_ca_bundle_source_bytes": "155260",
            "snapshot_ca_bundle_source_package": "ca-certificates=20230311+deb12u1",
            "snapshot_ca_bundle_source_sha256": "0d5f444f594e48c1e16a41d8fc628a09b24c658916a1274025c2330f2a802bed",
            "snapshot_ca_bundle_source_url": "https://snapshot.debian.org/archive/debian/20260713T000000Z/pool/main/c/ca-certificates/ca-certificates_20230311%2Bdeb12u1_all.deb",
            "source_date_epoch": SOURCE_DATE_EPOCH,
        }
        if values != expected_values:
            errors.append("build_inputs_lock does not exactly identify the build inputs")

    closure_lock = repository_root / image["package_closure_lock"]
    if closure_lock.is_file():
        closure_bytes = closure_lock.read_bytes()
        closure_lines = closure_bytes.splitlines()
        if document["packages"]["manifest_sha256"] != sha256_bytes(closure_bytes):
            errors.append("packages.manifest_sha256 does not match package_closure_lock")
        if document["packages"]["count"] != len(closure_lines):
            errors.append("packages.count does not match package_closure_lock")
        if len(closure_lines) != EXPECTED_PACKAGE_COUNT:
            errors.append(
                f"package_closure_lock must contain {EXPECTED_PACKAGE_COUNT} packages"
            )

        closure_by_name = {
            line.split(b"=", 1)[0]: line.split(b"=", 1)[1]
            for line in closure_lines
            if b"=" in line
        }
        direct_lock = repository_root / image["package_lock"]
        if direct_lock.is_file():
            for line in direct_lock.read_bytes().splitlines():
                if b"=" not in line:
                    errors.append("package_lock contains a malformed entry")
                    continue
                name, version = line.split(b"=", 1)
                if closure_by_name.get(name) != version:
                    errors.append(
                        f"package_lock entry is not exact in package_closure_lock: "
                        f"{line.decode('ascii', errors='replace')}"
                    )

    tree_lock = repository_root / image["installed_tree_lock"]
    if tree_lock.is_file():
        tree_bytes = tree_lock.read_bytes()
        tree_entries = tree_bytes.splitlines()
        if document["installed_tree"]["manifest_sha256"] != sha256_bytes(tree_bytes):
            errors.append("installed_tree.manifest_sha256 does not match installed_tree_lock")
        if document["installed_tree"]["entries"] != len(tree_entries):
            errors.append("installed_tree.entries does not match installed_tree_lock")
        if len(tree_entries) != EXPECTED_INSTALLED_TREE_ENTRIES:
            errors.append(
                "installed_tree_lock must contain "
                f"{EXPECTED_INSTALLED_TREE_ENTRIES} entries"
            )

    for collection, key in (
        ("toolchain", "name"),
        ("executables", "name"),
        ("fixtures", "id"),
    ):
        duplicates = _duplicates([entry[key] for entry in document[collection]])
        if duplicates:
            errors.append(f"duplicate {collection} {key}: {', '.join(duplicates)}")

    mount_ids = _duplicates([mount["id"] for mount in document["execution"]["mounts"]])
    mount_destinations = _duplicates(
        [mount["destination"] for mount in document["execution"]["mounts"]]
    )
    if mount_ids:
        errors.append(f"duplicate mount id: {', '.join(mount_ids)}")
    if mount_destinations:
        errors.append(f"duplicate mount destination: {', '.join(mount_destinations)}")
    fixture_ids = {fixture["id"] for fixture in document["fixtures"]}
    for mount in document["execution"]["mounts"]:
        if mount["type"] == "bind" and mount["source"] not in {
            "runtime-output",
            *fixture_ids,
        }:
            errors.append(f"bind mount source is not content-identified: {mount['source']}")

    if document["evidence"]["scope"] == "environment_smoke":
        expected_mounts = [
            {
                "destination": "/work",
                "id": "work-output",
                "read_only": False,
                "source": "runtime-output",
                "type": "bind",
            }
        ]
        if document["execution"]["mounts"] != expected_mounts:
            errors.append("environment_smoke must capture /work through runtime-output")

    for fixture in document["fixtures"]:
        if not _safe_relative_path(fixture["path"]):
            errors.append(f"fixture path is not safe: {fixture['path']}")
            continue
        path = repository_root / fixture["path"]
        if fixture["kind"] == "file":
            if not path.is_file():
                errors.append(f"fixture file does not exist: {fixture['path']}")
                continue
            actual = sha256_file(path)
        else:
            if not path.is_dir():
                errors.append(f"fixture tree does not exist: {fixture['path']}")
                continue
            actual = fixture_tree_sha256(path)
        if actual != fixture["sha256"]:
            errors.append(
                f"fixture hash mismatch for {fixture['path']}: "
                f"expected {fixture['sha256']}, found {actual}"
            )

    executable_paths = {entry["path"] for entry in document["executables"]}
    command = document["execution"]["command"]
    if command[0] not in executable_paths:
        errors.append(
            "execution.command[0] must match a content-identified executable path"
        )

    expected_configuration = canonical_json_sha256(launcher_configuration(document))
    actual_configuration = document["launcher"]["configuration_sha256"]
    if actual_configuration != expected_configuration:
        errors.append(
            "launcher.configuration_sha256 mismatch: "
            f"expected {expected_configuration}, found {actual_configuration}"
        )

    profile = document["launcher"]["profile"]
    environment = document["launcher"]["environment_variables"]
    if profile == "posixly_correct" and environment.get("POSIXLY_CORRECT") != "1":
        errors.append("posixly_correct launcher must record POSIXLY_CORRECT=1")
    if profile == "default" and "POSIXLY_CORRECT" in environment:
        errors.append("default launcher must not record POSIXLY_CORRECT")

    if document["oracle_source"]["commit"] != UPSTREAM_COMMIT:
        errors.append("oracle source commit does not match the pinned LCOV 2.5 commit")

    labels = image["labels"]
    if labels != expected_labels(document):
        errors.append("image labels do not exactly match the pinned build inputs")

    if "oci_manifest_digest" in document["image"]:
        digest = document["image"]["oci_manifest_digest"]
        if not digest.startswith("sha256:") or len(digest) != 71:
            errors.append("image.oci_manifest_digest is not a valid sha256 digest")

    reproducibility = document["reproducibility"]
    if reproducibility["docker_image_ids"][0] != image["docker_image_id"]:
        errors.append("reproducibility first image must be image.docker_image_id")
    if reproducibility["package_closure_sha256"] != document["packages"][
        "manifest_sha256"
    ]:
        errors.append("reproducibility package closure identity mismatch")
    if reproducibility["installed_tree_sha256"] != document["installed_tree"][
        "manifest_sha256"
    ]:
        errors.append("reproducibility installed tree identity mismatch")

    outputs = document["outputs"]
    for name in ("stdout", "stderr"):
        stream = outputs[name]
        try:
            content = base64.b64decode(stream["content_base64"], validate=True)
        except (binascii.Error, ValueError):
            errors.append(f"outputs.{name}.content_base64 is invalid")
            continue
        if len(content) != stream["bytes"]:
            errors.append(f"outputs.{name}.bytes does not match retained content")
        if sha256_bytes(content) != stream["sha256"]:
            errors.append(f"outputs.{name}.sha256 does not match retained content")
    filesystem = outputs["filesystem"]
    try:
        snapshot = base64.b64decode(filesystem["snapshot_base64"], validate=True)
        snapshot_value = json.loads(snapshot)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        errors.append("outputs.filesystem.snapshot_base64 is invalid")
    else:
        if not isinstance(snapshot_value, list):
            errors.append("outputs.filesystem retained snapshot is not an array")
        else:
            if len(snapshot_value) != filesystem["entries"]:
                errors.append(
                    "outputs.filesystem.entries does not match retained snapshot"
                )
        if sha256_bytes(snapshot) != filesystem["snapshot_sha256"]:
            errors.append(
                "outputs.filesystem.snapshot_sha256 does not match retained snapshot"
            )

    inventory_entries = document["evidence"]["inventory_entries"]
    if inventory_entries != sorted(inventory_entries):
        errors.append("evidence.inventory_entries must be sorted")
    if document["evidence"]["scope"] != "environment_smoke":
        inventory = json.loads(
            (repository_root / "compat/inventory/v2.5.json").read_text(encoding="utf-8")
        )
        known: dict[str, dict[str, Any]] = {}

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                if isinstance(value.get("id"), str):
                    known[value["id"]] = value
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(inventory)
        for entry_id in inventory_entries:
            entry = known.get(entry_id)
            if entry is None:
                errors.append(f"unknown evidence inventory entry: {entry_id}")
            elif entry.get("classification") != "public":
                errors.append(f"non-public evidence inventory entry: {entry_id}")
            elif entry.get("applicability") == "unreviewed":
                errors.append(f"unreviewed evidence applicability: {entry_id}")

    return errors


def validate_document(
    document: dict[str, Any],
    schema: dict[str, Any],
    repository_root: Path = REPOSITORY_ROOT,
) -> None:
    errors = _schema_errors(document, schema)
    if not errors:
        errors.extend(_semantic_errors(document, repository_root))
    if errors:
        raise ManifestValidationError("\n".join(errors))


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, check=check, capture_output=True)


def _docker_inspect(reference: str) -> dict[str, Any]:
    output = _run(["docker", "image", "inspect", reference]).stdout
    values = json.loads(output)
    if len(values) != 1:
        raise ManifestValidationError(
            f"Docker image reference resolved to {len(values)} records: {reference}"
        )
    return values[0]


def _docker_file_sha256(reference: str, path: str) -> str:
    output = _run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "sha256sum",
            reference,
            path,
        ]
    ).stdout
    digest = output.decode("ascii").split()[0]
    return f"sha256:{digest}"


def _package_manifest(reference: str) -> bytes:
    output = _run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "dpkg-query",
            reference,
            "-W",
            "-f=${binary:Package}=${Version}\\n",
        ]
    ).stdout
    return b"\n".join(sorted(output.splitlines())) + b"\n"


def _installed_tree_manifest(reference: str) -> bytes:
    return _run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "/tmp/installed-tree.sh",
            reference,
        ]
    ).stdout


def _key_file_manifest(reference: str) -> bytes:
    script = "set -eu; " + "; ".join(
        f"test -f {path}; sha256sum {path}" for path in KEY_PATHS
    )
    return _run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "sh",
            reference,
            "-c",
            script,
        ]
    ).stdout


def _smoke_manifest(reference: str) -> bytes:
    lines: list[bytes] = []
    for command in COMMANDS:
        output = _run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                reference,
                command,
                "--help",
            ],
            check=False,
        )
        if output.returncode != 0:
            raise ManifestValidationError(
                f"help smoke failed: command={command} status={output.returncode}"
            )
        if command != "xml2lcovutil.py" and not output.stdout:
            raise ManifestValidationError(
                f"help smoke produced empty stdout: command={command}"
            )
        lines.append(
            (
                f"{command}\t{output.returncode}\t{len(output.stdout)}\t"
                f"{hashlib.sha256(output.stdout).hexdigest()}\t{len(output.stderr)}\t"
                f"{hashlib.sha256(output.stderr).hexdigest()}\n"
            ).encode("ascii")
        )
    return b"".join(lines)


def _execution_command(
    document: dict[str, Any], image: str, bind_sources: dict[str, Path]
) -> list[str]:
    execution = document["execution"]
    command = ["docker", "run", "--rm", "--network", "none"]
    command.extend(["--user", execution["user"]])
    command.extend(["--workdir", execution["working_directory"]])
    for key, value in sorted(document["launcher"]["environment_variables"].items()):
        command.extend(["--env", f"{key}={value}"])
    for mount in execution["mounts"]:
        if mount["type"] == "bind":
            source = bind_sources.get(mount["source"])
            if source is None:
                raise ManifestValidationError(
                    f"runtime verification cannot resolve bind source: {mount['source']}"
                )
            mode = "ro" if mount["read_only"] else "rw"
            command.extend(
                ["--volume", f"{source}:{mount['destination']}:{mode}"]
            )
        elif mount["type"] == "tmpfs":
            command.extend(["--tmpfs", mount["destination"]])
        else:
            raise ManifestValidationError(f"unsupported mount type: {mount['type']}")
    command.extend(["--entrypoint", execution["command"][0], image])
    command.extend(execution["command"][1:])
    return command


def verify_runtime(document: dict[str, Any]) -> None:
    reference = document["image"]["docker_image_id"]
    inspect = _docker_inspect(reference)
    actual_image = inspect["Id"]
    expected_image = document["image"]["docker_image_id"]
    if actual_image != expected_image:
        raise ManifestValidationError(
            f"Docker image ID mismatch: expected {expected_image}, found {actual_image}"
        )

    labels = inspect.get("Config", {}).get("Labels") or {}
    for key, expected in document["image"]["labels"].items():
        if labels.get(key) != expected:
            raise ManifestValidationError(
                f"image label mismatch for {key}: expected {expected!r}, "
                f"found {labels.get(key)!r}"
            )

    for entry in document["executables"] + document["toolchain"]:
        actual = _docker_file_sha256(reference, entry["path"])
        if actual != entry["sha256"]:
            raise ManifestValidationError(
                f"runtime hash mismatch for {entry['path']}: "
                f"expected {entry['sha256']}, found {actual}"
            )

    package_manifest = _package_manifest(reference)
    actual_packages = sha256_bytes(package_manifest)
    if actual_packages != document["packages"]["manifest_sha256"]:
        raise ManifestValidationError(
            "installed package manifest hash mismatch: "
            f"expected {document['packages']['manifest_sha256']}, "
            f"found {actual_packages}"
        )
    if len(package_manifest.splitlines()) != document["packages"]["count"]:
        raise ManifestValidationError("installed package count mismatch")

    installed_tree = _installed_tree_manifest(reference)
    actual_tree = sha256_bytes(installed_tree)
    if actual_tree != document["installed_tree"]["manifest_sha256"]:
        raise ManifestValidationError(
            "installed tree manifest hash mismatch: "
            f"expected {document['installed_tree']['manifest_sha256']}, "
            f"found {actual_tree}"
        )
    if len(installed_tree.splitlines()) != document["installed_tree"]["entries"]:
        raise ManifestValidationError("installed tree entry count mismatch")

    # Verify runtime state against committed lock files (recompute, no self-trust)
    repository_root = REPOSITORY_ROOT
    closure_lock_path = repository_root / document["image"]["package_closure_lock"]
    closure_lock_bytes = closure_lock_path.read_bytes()
    if package_manifest != closure_lock_bytes:
        raise ManifestValidationError(
            "runtime package closure does not match committed packages.full.lock"
        )
    if len(package_manifest.splitlines()) != document["packages"]["count"]:
        raise ManifestValidationError(
            "runtime package count does not match manifest"
        )

    direct_lock_path = repository_root / document["image"]["package_lock"]
    direct_lock_text = direct_lock_path.read_text(encoding="ascii")
    runtime_by_name: dict[str, str] = {}
    for line in package_manifest.decode("ascii").splitlines():
        if "=" in line:
            name, version = line.split("=", 1)
            runtime_by_name[name] = version
    for line in direct_lock_text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        name, expected_version = line.split("=", 1)
        if runtime_by_name.get(name) != expected_version:
            raise ManifestValidationError(
                f"runtime package version mismatch: "
                f"{name} expected {expected_version}, "
                f"found {runtime_by_name.get(name)}"
            )

    tree_lock_path = repository_root / document["image"]["installed_tree_lock"]
    tree_lock_bytes = tree_lock_path.read_bytes()
    if installed_tree != tree_lock_bytes:
        raise ManifestValidationError(
            "runtime installed tree does not match committed installed-tree.lock"
        )

    reproducibility = document["reproducibility"]
    peer = reproducibility["docker_image_ids"][1]
    peer_inspect = _docker_inspect(peer)
    if peer_inspect["Id"] != peer:
        raise ManifestValidationError("rebuild peer did not resolve by immutable image ID")
    if (peer_inspect.get("Config", {}).get("Labels") or {}) != labels:
        raise ManifestValidationError("rebuild peer labels differ from primary image")

    key_files = _key_file_manifest(reference)
    peer_key_files = _key_file_manifest(peer)
    if key_files != peer_key_files:
        raise ManifestValidationError("key file manifests differ between clean rebuilds")
    if sha256_bytes(key_files) != reproducibility["key_files_sha256"]:
        raise ManifestValidationError("key file manifest hash mismatch")

    smoke = _smoke_manifest(reference)
    peer_smoke = _smoke_manifest(peer)
    if smoke != peer_smoke:
        raise ManifestValidationError("smoke outputs differ between clean rebuilds")
    if sha256_bytes(smoke) != reproducibility["smoke_sha256"]:
        raise ManifestValidationError("smoke manifest hash mismatch")

    if _package_manifest(peer) != package_manifest:
        raise ManifestValidationError("package closures differ between clean rebuilds")
    if _installed_tree_manifest(peer) != installed_tree:
        raise ManifestValidationError("installed trees differ between clean rebuilds")

    with tempfile.TemporaryDirectory(prefix="ferricov-manifest-output-") as directory:
        output_root = Path(directory)
        output = _run(
            _execution_command(
                document,
                reference,
                {"runtime-output": output_root},
            ),
            check=False,
        )
        output_tree = fixture_tree_manifest(output_root)
    expected = document["outputs"]
    actual_exit = output.returncode
    if actual_exit != expected["exit_code"]:
        raise ManifestValidationError(
            f"execution exit mismatch: expected {expected['exit_code']}, found {actual_exit}"
        )
    for name, content in (("stdout", output.stdout), ("stderr", output.stderr)):
        if len(content) != expected[name]["bytes"]:
            raise ManifestValidationError(f"execution {name} byte count mismatch")
        actual = sha256_bytes(content)
        if actual != expected[name]["sha256"]:
            raise ManifestValidationError(
                f"execution {name} hash mismatch: "
                f"expected {expected[name]['sha256']}, found {actual}"
            )
    if len(json.loads(output_tree)) != expected["filesystem"]["entries"]:
        raise ManifestValidationError("execution filesystem entry count mismatch")
    if sha256_bytes(output_tree) != expected["filesystem"]["snapshot_sha256"]:
        raise ManifestValidationError("execution filesystem snapshot hash mismatch")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ManifestValidationError(f"JSON document must be an object: {path}")
    return value


def _manifest_paths(arguments: list[str]) -> list[Path]:
    if arguments:
        return [Path(argument).resolve() for argument in arguments]
    return sorted(DEFAULT_MANIFESTS.glob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="*")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--repository-root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--verify-runtime", action="store_true")
    args = parser.parse_args()

    schema_path = args.schema.resolve()
    schema_identity = sha256_file(schema_path)
    if schema_identity != EXPECTED_SCHEMA_SHA256:
        print(
            "EXECUTION_MANIFEST_ERROR schema hash mismatch: "
            f"expected {EXPECTED_SCHEMA_SHA256}, found {schema_identity}",
            file=sys.stderr,
        )
        return 1
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    paths = _manifest_paths(args.manifests)
    if not paths:
        parser.error("no execution manifests found")

    try:
        for path in paths:
            document = _load_json(path)
            canonical = (
                json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
            )
            if path.read_text(encoding="utf-8") != canonical:
                raise ManifestValidationError(f"manifest is not canonical JSON: {path}")
            validate_document(document, schema, args.repository_root.resolve())
            if args.verify_runtime:
                verify_runtime(document)
            print(f"EXECUTION_MANIFEST_OK path={path}")
    except (ManifestValidationError, OSError, subprocess.SubprocessError) as error:
        print(f"EXECUTION_MANIFEST_ERROR {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
