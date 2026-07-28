#!/usr/bin/env python3
"""Record two equivalent clean builds of the pinned LCOV Oracle."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_MODULE = REPOSITORY_ROOT / "compat/manifests"
sys.path.insert(0, str(MANIFEST_MODULE))

from validate import (  # noqa: E402
    BASE_IMAGE_DIGEST,
    DEBIAN_SNAPSHOT,
    EXPECTED_INSTALLED_TREE_ENTRIES,
    EXPECTED_PACKAGE_COUNT,
    LCOV_BUILD_DATE,
    UPSTREAM_COMMIT,
    _docker_inspect,
    _installed_tree_manifest,
    _key_file_manifest,
    _package_manifest,
    _smoke_manifest,
    canonical_json_sha256,
    expected_labels,
    fixture_tree_manifest,
    launcher_configuration,
    sha256_bytes,
    sha256_file,
    validate_document,
)


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

PROBE = r'''
import hashlib
import json
import os
import pathlib
import subprocess

commands = json.loads(os.environ["FERRICOV_COMMANDS"])
tool_commands = {
    "gcc": ["gcc", "-dumpfullversion"],
    "gxx": ["g++", "-dumpfullversion"],
    "gcov": ["gcov", "--version"],
    "git": ["git", "--version"],
    "make": ["make", "--version"],
    "perl": ["perl", "-e", "print $^V"],
    "python3": ["python3", "--version"],
}

def identity(name):
    path = subprocess.check_output(
        ["sh", "-c", "command -v -- \"$1\"", "sh", name], text=True
    ).strip()
    content = pathlib.Path(path).read_bytes()
    return path, "sha256:" + hashlib.sha256(content).hexdigest()

executables = []
for name in commands:
    path, digest = identity(name)
    executables.append({"name": name, "path": path, "sha256": digest})

toolchain = []
for name, command in tool_commands.items():
    path, digest = identity(command[0])
    version = subprocess.check_output(
        command, stderr=subprocess.STDOUT, text=True
    ).splitlines()[0]
    toolchain.append(
        {"name": name, "version": version, "path": path, "sha256": digest}
    )

os_release = {}
for line in pathlib.Path("/etc/os-release").read_text().splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        os_release[key] = value.strip('"')

print(json.dumps({
    "executables": executables,
    "toolchain": toolchain,
    "platform": {
        "operating_system": os_release["PRETTY_NAME"],
        "architecture": os.uname().machine,
        "kernel": os.uname().release,
        "libc": subprocess.check_output(
            ["ldd", "--version"], stderr=subprocess.STDOUT, text=True
        ).splitlines()[0],
        "target_triple": subprocess.check_output(
            ["gcc", "-dumpmachine"], text=True
        ).strip(),
        "filesystem": subprocess.check_output(
            ["stat", "-f", "-c", "%T", "/work"], text=True
        ).strip(),
    },
}, sort_keys=True))
'''


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, check=check, capture_output=True)


def immutable_image_id(reference: str) -> str:
    image_id = _docker_inspect(reference)["Id"]
    if reference != image_id:
        raise RuntimeError(
            f"execution manifest recording requires an immutable Docker image ID: {reference}"
        )
    return image_id


def probe_image(image_id: str) -> dict[str, Any]:
    output = run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--env",
            f"FERRICOV_COMMANDS={json.dumps(COMMANDS)}",
            "--entrypoint",
            "python3",
            image_id,
            "-c",
            PROBE,
        ]
    ).stdout
    return json.loads(output)


def smoke_version(
    image_id: str, output_root: Path
) -> tuple[subprocess.CompletedProcess[bytes], bytes]:
    output = run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--user",
            "root",
            "--workdir",
            "/work",
            "--env",
            "LC_ALL=C",
            "--env",
            "TZ=UTC",
            "--volume",
            f"{output_root}:/work:rw",
            "--entrypoint",
            "/usr/local/bin/lcov",
            image_id,
            "--version",
        ],
        check=False,
    )
    return output, fixture_tree_manifest(output_root)


def file_identity(path: str) -> tuple[str, str]:
    repository_path = REPOSITORY_ROOT / path
    return path, sha256_file(repository_path)


def build_document(primary: str, peer: str) -> dict[str, Any]:
    primary_id = immutable_image_id(primary)
    peer_id = immutable_image_id(peer)
    primary_inspect = _docker_inspect(primary_id)
    peer_inspect = _docker_inspect(peer_id)

    probe = probe_image(primary_id)
    peer_probe = probe_image(peer_id)
    if probe != peer_probe:
        raise RuntimeError("toolchain, executable, or platform probe differs between rebuilds")

    package_manifest = _package_manifest(primary_id)
    if package_manifest != _package_manifest(peer_id):
        raise RuntimeError("package closure differs between clean rebuilds")
    package_lock = REPOSITORY_ROOT / "compat/upstream/packages.full.lock"
    if package_manifest != package_lock.read_bytes():
        raise RuntimeError("runtime package closure differs from packages.full.lock")
    if len(package_manifest.splitlines()) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError("runtime package closure has an unexpected count")

    installed_tree = _installed_tree_manifest(primary_id)
    if installed_tree != _installed_tree_manifest(peer_id):
        raise RuntimeError("installed tree differs between clean rebuilds")
    installed_tree_lock = REPOSITORY_ROOT / "compat/upstream/installed-tree.lock"
    if installed_tree != installed_tree_lock.read_bytes():
        raise RuntimeError("runtime installed tree differs from installed-tree.lock")
    if len(installed_tree.splitlines()) != EXPECTED_INSTALLED_TREE_ENTRIES:
        raise RuntimeError("runtime installed tree has an unexpected count")

    key_files = _key_file_manifest(primary_id)
    if key_files != _key_file_manifest(peer_id):
        raise RuntimeError("key executable/library/config/script/doc hashes differ")
    help_smoke = _smoke_manifest(primary_id)
    if help_smoke != _smoke_manifest(peer_id):
        raise RuntimeError("help smoke outputs differ between clean rebuilds")

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
    image: dict[str, Any] = {
        "reference": primary_id,
        "docker_image_id": primary_id,
        "base_image_digest": BASE_IMAGE_DIGEST,
        "debian_snapshot": DEBIAN_SNAPSHOT,
    }
    for field, path in image_paths.items():
        image[field] = path
        image[f"{field}_sha256"] = sha256_file(REPOSITORY_ROOT / path)

    document: dict[str, Any] = {
        "schema_version": 1,
        "manifest_id": "oracle-lcov-v2.5-image-smoke",
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "observed",
        "evidence": {"scope": "environment_smoke", "inventory_entries": []},
        "oracle_source": {
            "repository": "https://github.com/linux-test-project/lcov.git",
            "ref": "v2.5",
            "commit": UPSTREAM_COMMIT,
        },
        "image": image,
        "platform": probe["platform"],
        "packages": {
            "count": len(package_manifest.splitlines()),
            "manifest_sha256": sha256_bytes(package_manifest),
        },
        "installed_tree": {
            "entries": len(installed_tree.splitlines()),
            "manifest_sha256": sha256_bytes(installed_tree),
        },
        "reproducibility": {
            "docker_image_ids": [primary_id, peer_id],
            "package_closure_sha256": sha256_bytes(package_manifest),
            "installed_tree_sha256": sha256_bytes(installed_tree),
            "key_files_sha256": sha256_bytes(key_files),
            "smoke_sha256": sha256_bytes(help_smoke),
        },
        "toolchain": probe["toolchain"],
        "executables": probe["executables"],
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
    }
    document["image"]["labels"] = expected_labels(document)
    if (primary_inspect.get("Config", {}).get("Labels") or {}) != document["image"][
        "labels"
    ]:
        raise RuntimeError("primary image labels do not match pinned build inputs")
    if (peer_inspect.get("Config", {}).get("Labels") or {}) != document["image"][
        "labels"
    ]:
        raise RuntimeError("rebuild peer labels do not match pinned build inputs")

    with tempfile.TemporaryDirectory(prefix="ferricov-record-output-") as directory:
        output, output_tree = smoke_version(primary_id, Path(directory))
    document["outputs"] = {
        "exit_code": output.returncode,
        "stdout": {
            "bytes": len(output.stdout),
            "sha256": sha256_bytes(output.stdout),
            "content_base64": base64.b64encode(output.stdout).decode("ascii"),
        },
        "stderr": {
            "bytes": len(output.stderr),
            "sha256": sha256_bytes(output.stderr),
            "content_base64": base64.b64encode(output.stderr).decode("ascii"),
        },
        "filesystem": {
            "entries": len(json.loads(output_tree)),
            "snapshot_sha256": sha256_bytes(output_tree),
            "snapshot_base64": base64.b64encode(output_tree).decode("ascii"),
        },
    }
    document["launcher"]["configuration_sha256"] = canonical_json_sha256(
        launcher_configuration(document)
    )
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--rebuild-peer", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "compat/manifests/oracle-lcov-v2.5-smoke.json",
    )
    args = parser.parse_args()

    try:
        document = build_document(args.image, args.rebuild_peer)
        schema = json.loads(
            (REPOSITORY_ROOT / "compat/schema/execution-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        validate_document(document, schema, REPOSITORY_ROOT)
        encoded = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="ascii")
        print(
            f"ORACLE_MANIFEST_RECORDED path={args.output} "
            f"docker_image_id={document['image']['docker_image_id']}"
        )
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"ORACLE_MANIFEST_ERROR {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
