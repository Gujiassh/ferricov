#!/usr/bin/env python3
"""Replayable installation wave-2 Oracle capture orchestrator.

Runs each INST case inside the pinned Docker image, retains raw stdout/stderr
binaries, process metadata, and file-tree effects, then writes strict per-case
capture records plus an independent expected-case table.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
WAVE2 = Path(__file__).resolve().parent
CASE_SCHEMA = WAVE2 / "oracle-case-capture.schema.json"
DRIVER = WAVE2 / "capture-driver.sh"
DIR_RECORDER = WAVE2 / "installed-tree-directories.sh"
PIN_INV = ROOT / "compat/upstream/python-objects.inv"
PIN_PY = ROOT / "compat/upstream/pin-intersphinx.py"
UPSTREAM = Path(os.environ.get("LCOV_SOURCE_ROOT", "/tmp/lcov-upstream-reference"))
IMAGE = os.environ.get(
    "FERRICOV_ORACLE_IMAGE",
    "b02cc645313f",
)
IMAGE_ID = os.environ.get(
    "FERRICOV_ORACLE_IMAGE_ID",
    "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7",
)
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
OUT_ROOT = WAVE2 / "cases"
CAPTURE_INDEX = WAVE2 / "oracle-capture.json"
EXPECTED_TABLE = WAVE2 / "expected-case-table.json"

CASE_SPECS: list[dict[str, Any]] = [
    {
        "id": "INST-LAYOUT-001",
        "argv": ["sh", "/tmp/installed-tree-directories.sh", "/usr/local"],
        "working_directory": "/",
        "fixture_setup": [
            "use pinned image installed payload under /usr/local",
            "mount wave2 directory companion recorder",
        ],
        "timeout_seconds": 60,
        "cleanup": ["none_required_read_only_payload_scan"],
        "environment": {"mode": "clean_explicit", "variables": {"LC_ALL": "C", "TZ": "UTC"}},
        "executable_path": "/usr/bin/find",
        "expected_exit_status": 0,
        "requires_source": False,
        "driver_case": "INST-LAYOUT-001",
    },
    {
        "id": "INST-STAGE-001",
        "argv": ["make", "install", "DESTDIR=/tmp/destdir-stage", "PREFIX=/usr/local"],
        "working_directory": "/tmp/src",
        "fixture_setup": [
            "copy pinned upstream source to /tmp/src",
            "pin docs intersphinx inventory",
            "build doc_finished",
            "empty DESTDIR=/tmp/destdir-stage",
        ],
        "timeout_seconds": 600,
        "cleanup": ["rm -rf /tmp/destdir-stage /tmp/src"],
        "environment": {
            "mode": "clean_explicit",
            "variables": {
                "SOURCE_DATE_EPOCH": "1783375223",
                "LCOV_BUILD_DATE": "2026-07-06",
                "VERSION": "2.5",
                "RELEASE": "beta",
                "LC_ALL": "C",
                "TZ": "UTC",
                "PYTHONHASHSEED": "0",
            },
        },
        "executable_path": "/usr/bin/make",
        "expected_exit_status": 0,
        "requires_source": True,
        "driver_case": "INST-STAGE-001",
    },
    {
        "id": "INST-INTERP-001",
        "argv": [
            "env",
            "LCOV_PERL=/opt/custom/bin/perl",
            "make",
            "install",
            "DESTDIR=/tmp/destdir-interp",
            "PREFIX=/usr/local",
        ],
        "working_directory": "/tmp/src",
        "fixture_setup": [
            "copy pinned upstream source",
            "build doc_finished",
            "set LCOV_PERL override to nonexistent custom path",
        ],
        "timeout_seconds": 600,
        "cleanup": ["rm -rf /tmp/destdir-interp /tmp/src"],
        "environment": {
            "mode": "clean_override",
            "variables": {
                "LCOV_PERL": "/opt/custom/bin/perl",
                "SOURCE_DATE_EPOCH": "1783375223",
                "LCOV_BUILD_DATE": "2026-07-06",
                "VERSION": "2.5",
                "RELEASE": "beta",
                "LC_ALL": "C",
            },
        },
        "executable_path": "/usr/bin/make",
        "expected_exit_status": 0,
        "requires_source": True,
        "driver_case": "INST-INTERP-001",
    },
    {
        "id": "INST-CONFIG-DISCOVERY-001",
        "argv": ["perl", "/tmp/config-probe.pl"],
        "working_directory": "/tmp",
        "fixture_setup": [
            "create /tmp/h1/.lcovrc and /tmp/lh/etc/lcovrc",
            "run lcovutil-equivalent HOME/LCOV_HOME search probe",
        ],
        "timeout_seconds": 60,
        "cleanup": ["rm -rf /tmp/h1 /tmp/lh /tmp/config-probe.pl"],
        "environment": {"mode": "clean_override", "variables": {"LC_ALL": "C"}},
        "executable_path": "/usr/bin/perl",
        "expected_exit_status": 0,
        "requires_source": False,
        "driver_case": "INST-CONFIG-DISCOVERY-001",
    },
    {
        "id": "INST-UNINSTALL-001",
        "argv": ["make", "uninstall", "DESTDIR=/tmp/destdir-uninst", "PREFIX=/usr/local"],
        "working_directory": "/tmp/src",
        "fixture_setup": [
            "install full payload into DESTDIR",
            "add foreign sentinel files under etc and man",
        ],
        "timeout_seconds": 600,
        "cleanup": ["rm -rf /tmp/destdir-uninst /tmp/src"],
        "environment": {
            "mode": "clean_explicit",
            "variables": {
                "SOURCE_DATE_EPOCH": "1783375223",
                "LCOV_BUILD_DATE": "2026-07-06",
                "VERSION": "2.5",
                "RELEASE": "beta",
                "LC_ALL": "C",
            },
        },
        "executable_path": "/usr/bin/make",
        # Observed on pinned image: uninstall returns 0 while leaving foreign residue
        # and emitting rmdir warnings on stderr.
        "expected_exit_status": 0,
        "requires_source": True,
        "driver_case": "INST-UNINSTALL-001",
    },
    {
        "id": "INST-PARTIAL-001",
        "argv": [
            "make",
            "install",
            "DESTDIR=/tmp/partial",
            "PREFIX=/usr/local",
            "INSTALL=/tmp/fake-install",
        ],
        "working_directory": "/tmp/src",
        "fixture_setup": [
            "build docs",
            "install fake install wrapper that fails after count>20",
        ],
        "timeout_seconds": 600,
        "cleanup": ["rm -rf /tmp/partial /tmp/src /tmp/fake-install /tmp/install-count"],
        "environment": {
            "mode": "clean_explicit",
            "variables": {
                "SOURCE_DATE_EPOCH": "1783375223",
                "LCOV_BUILD_DATE": "2026-07-06",
                "VERSION": "2.5",
                "RELEASE": "beta",
                "LC_ALL": "C",
            },
        },
        "executable_path": "/usr/bin/make",
        "expected_exit_status": 2,
        "requires_source": True,
        "driver_case": "INST-PARTIAL-001",
    },
    {
        "id": "INST-DOC-FAIL-001",
        "argv": ["make", "install", "DESTDIR=/tmp/docfail", "PREFIX=/usr/local"],
        "working_directory": "/tmp/src",
        "fixture_setup": [
            "hide /usr/bin/sphinx-build",
            "remove doc_finished and docs/_build",
        ],
        "timeout_seconds": 300,
        "cleanup": ["restore sphinx-build", "rm -rf /tmp/docfail /tmp/src"],
        "environment": {
            "mode": "clean_explicit",
            "variables": {
                "SOURCE_DATE_EPOCH": "1783375223",
                "LCOV_BUILD_DATE": "2026-07-06",
                "VERSION": "2.5",
                "RELEASE": "beta",
                "LC_ALL": "C",
            },
        },
        "executable_path": "/usr/bin/make",
        "expected_exit_status": 2,
        "requires_source": True,
        "driver_case": "INST-DOC-FAIL-001",
    },
    {
        "id": "INST-PATH-001",
        "dual": True,
        "parts": [
            {
                "part_id": "relative",
                "driver_case": "INST-PATH-REL-001",
                "argv": ["make", "install", "DESTDIR=rel-dest", "PREFIX=/usr/local"],
                "working_directory": "/tmp/src",
                "fixture_setup": ["relative DESTDIR=rel-dest"],
                "timeout_seconds": 120,
                "cleanup": ["rm -rf /tmp/src"],
                "environment": {
                    "mode": "clean_explicit",
                    "variables": {
                        "SOURCE_DATE_EPOCH": "1783375223",
                        "LCOV_BUILD_DATE": "2026-07-06",
                        "VERSION": "2.5",
                        "RELEASE": "beta",
                        "LC_ALL": "C",
                    },
                },
                "executable_path": "/usr/bin/make",
                "expected_exit_status": 2,
                "requires_source": True,
            },
            {
                "part_id": "space",
                "driver_case": "INST-PATH-SPACE-001",
                "argv": [
                    "make",
                    "install",
                    "DESTDIR=/tmp/destdir space",
                    "PREFIX=/usr/local",
                ],
                "working_directory": "/tmp/src",
                "fixture_setup": ["space-containing absolute DESTDIR"],
                "timeout_seconds": 300,
                "cleanup": ["rm -rf '/tmp/destdir space' /tmp/src"],
                "environment": {
                    "mode": "clean_explicit",
                    "variables": {
                        "SOURCE_DATE_EPOCH": "1783375223",
                        "LCOV_BUILD_DATE": "2026-07-06",
                        "VERSION": "2.5",
                        "RELEASE": "beta",
                        "LC_ALL": "C",
                    },
                },
                "executable_path": "/usr/bin/make",
                "expected_exit_status": 2,
                "requires_source": True,
            },
        ],
    },
    {
        "id": "INST-DIRTY-ASSET-001",
        "argv": ["make", "install", "DESTDIR=/tmp/destdir-dirty", "PREFIX=/usr/local"],
        "working_directory": "/tmp/src",
        "fixture_setup": [
            "create untracked scripts/zz_dirty_wave2_sentinel",
            "build docs then install",
        ],
        "timeout_seconds": 600,
        "cleanup": ["rm -rf /tmp/destdir-dirty /tmp/src"],
        "environment": {
            "mode": "clean_explicit",
            "variables": {
                "SOURCE_DATE_EPOCH": "1783375223",
                "LCOV_BUILD_DATE": "2026-07-06",
                "VERSION": "2.5",
                "RELEASE": "beta",
                "LC_ALL": "C",
            },
        },
        "executable_path": "/usr/bin/make",
        "expected_exit_status": 0,
        "requires_source": True,
        "driver_case": "INST-DIRTY-ASSET-001",
    },
    {
        "id": "INST-TEST-RUN-001",
        "argv": ["env", "-u", "LCOV_HOME", "make", "-np"],
        "working_directory": "/usr/local/share/lcov/tests",
        "fixture_setup": [
            "use installed tests in pinned image",
            "unset LCOV_HOME",
        ],
        "timeout_seconds": 60,
        "cleanup": ["none_required_read_only"],
        "environment": {"mode": "clean_empty", "variables": {"LC_ALL": "C"}},
        "executable_path": "/usr/bin/make",
        "expected_exit_status": None,  # accept any; validate path observations separately
        "requires_source": False,
        "driver_case": "INST-TEST-RUN-001",
    },
    {
        "id": "INST-DOC-PATH-001",
        "argv": ["python3", "-"],
        "working_directory": "/tmp/src",
        "fixture_setup": ["extract README.rst path claims vs retained roots"],
        "timeout_seconds": 60,
        "cleanup": ["rm -rf /tmp/src"],
        "environment": {"mode": "clean_explicit", "variables": {"LC_ALL": "C"}},
        "executable_path": "/usr/bin/python3",
        "expected_exit_status": 0,
        "requires_source": True,
        "driver_case": "INST-DOC-PATH-001",
    },
    {
        "id": "INST-REPORT-ASSET-001",
        "argv": ["python3", "-"],
        "working_directory": "/tmp/src",
        "fixture_setup": ["scan bin/genhtml for retained report assets"],
        "timeout_seconds": 60,
        "cleanup": ["rm -rf /tmp/src"],
        "environment": {"mode": "clean_explicit", "variables": {"LC_ALL": "C"}},
        "executable_path": "/usr/bin/python3",
        "expected_exit_status": 0,
        "requires_source": True,
        "driver_case": "INST-REPORT-ASSET-001",
    },
    {
        "id": "INST-LICENSE-001",
        "argv": ["make", "install", "DESTDIR=/tmp/destdir-lic", "PREFIX=/usr/local"],
        "working_directory": "/tmp/src",
        "fixture_setup": [
            "install payload",
            "observe COPYING in source vs payload",
        ],
        "timeout_seconds": 600,
        "cleanup": ["rm -rf /tmp/destdir-lic /tmp/src"],
        "environment": {
            "mode": "clean_explicit",
            "variables": {
                "SOURCE_DATE_EPOCH": "1783375223",
                "LCOV_BUILD_DATE": "2026-07-06",
                "VERSION": "2.5",
                "RELEASE": "beta",
                "LC_ALL": "C",
            },
        },
        "executable_path": "/usr/bin/make",
        "expected_exit_status": 0,
        "requires_source": True,
        "driver_case": "INST-LICENSE-001",
    },
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def observation_hash(record: dict[str, Any]) -> str:
    material = {
        "case_id": record["case_id"],
        "identity": record["identity"],
        "invocation": record["invocation"],
        "environment": record["environment"],
        "process": record["process"],
        "artifacts": record["artifacts"],
        "file_tree_effects": record["file_tree_effects"],
    }
    return sha256_bytes(canonical_json(material).encode("ascii"))


def parse_status(path: Path) -> dict[str, Any]:
    values: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                values[key] = val
    exit_raw = values.get("EXIT_STATUS", "")
    exit_status = int(exit_raw) if exit_raw not in ("", "None") else None
    signal_raw = values.get("SIGNAL", "")
    signal = int(signal_raw) if signal_raw not in ("", "None") else None
    return {
        "exit_status": exit_status,
        "signal": signal,
        "timed_out": values.get("TIMED_OUT", "0") == "1",
        "child_processes_observed": [],
    }


def parse_tree(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "root": "",
            "file_count": 0,
            "symlink_count": 0,
            "directory_count": 0,
            "paths_sha256": sha256_bytes(b""),
            "selected_paths": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_capture_output(out_dir: Path) -> None:
    """Make Docker-produced capture files host-owned and user-writable.

    Container root often leaves /out artifacts as root:root mode 644. Rewrite
    each file byte-for-byte as the current user so later contract reverse tests
    and recapture bookkeeping can mutate/restore without sudo. Content and
    hashes are preserved.
    """
    if not out_dir.is_dir():
        return
    # Directories first so files can be rewritten underneath.
    for path in sorted(out_dir.rglob("*"), key=lambda p: len(p.parts)):
        if path.is_dir():
            try:
                path.chmod(0o755)
            except OSError:
                pass
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        # Unlink then recreate so ownership becomes the current uid/gid even when
        # the original file was root-owned but world-readable.
        try:
            path.unlink()
        except OSError:
            # If unlink fails (immutable/root-only dir), attempt in-place rewrite.
            pass
        path.write_bytes(data)
        path.chmod(0o644)
    try:
        out_dir.chmod(0o755)
    except OSError:
        pass


def docker_run(case_id: str, out_dir: Path, timeout: int) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Pre-create host-owned placeholders so bind-mount /out stays writable by
    # the container while remaining rewritable by the host after exit.
    out_dir.chmod(0o777)
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "-v",
        f"{UPSTREAM}:/src-ro:ro",
        "-v",
        f"{PIN_INV}:/tmp/python-objects.inv:ro",
        "-v",
        f"{PIN_PY}:/tmp/pin-intersphinx.py:ro",
        "-v",
        f"{DRIVER}:/tmp/capture-driver.sh:ro",
        "-v",
        f"{DIR_RECORDER}:/tmp/installed-tree-directories.sh:ro",
        "-v",
        f"{out_dir}:/out",
        "-e",
        "SRC_RO=/src-ro",
        IMAGE,
        "bash",
        "-lc",
        f"chmod +x /tmp/capture-driver.sh /tmp/installed-tree-directories.sh; "
        f"/tmp/capture-driver.sh {case_id} /out; "
        # Best-effort in-container ownership fix for common docker rootless setups.
        f"chmod -R a+rwX /out || true",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 120)
    # Durable host-side rewrite: re-own every artifact as the invoking user without
    # changing bytes (critical for observation/artifact hash stability).
    normalize_capture_output(out_dir)
    (out_dir / "docker.stdout.txt").write_text(proc.stdout)
    (out_dir / "docker.stderr.txt").write_text(proc.stderr)
    (out_dir / "docker.stdout.txt").chmod(0o644)
    (out_dir / "docker.stderr.txt").chmod(0o644)
    return proc.returncode


def artifact_ref(rel_path: str, path: Path) -> dict[str, Any]:
    data = path.read_bytes() if path.is_file() else b""
    if not path.is_file():
        path.write_bytes(data)
    return {
        "path": rel_path,
        "sha256": sha256_bytes(data),
        "bytes": len(data),
    }


def build_record(
    *,
    case_id: str,
    part_id: str | None,
    spec: dict[str, Any],
    out_dir: Path,
    docker_rc: int,
) -> dict[str, Any]:
    rel_root = f"compat/installation/wave2/cases/{case_id}" + (f"/{part_id}" if part_id else "")
    stdout_path = out_dir / "stdout.bin"
    stderr_path = out_dir / "stderr.bin"
    status = parse_status(out_dir / "status.env")
    tree = parse_tree(out_dir / "tree-effects.json")

    # Prefer driver-recorded executable hash if present in meta.env
    exec_path = spec["executable_path"]
    exec_sha = "0" * 64
    meta = out_dir / "meta.env"
    if meta.is_file():
        for line in meta.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("EXECUTABLE_PATH="):
                exec_path = line.split("=", 1)[1]
            if line.startswith("EXECUTABLE_SHA256="):
                exec_sha = line.split("=", 1)[1]

    extra: list[dict[str, Any]] = []
    for name in ("observation.txt", "installed-directories.lock", "doc.log", "install.log"):
        p = out_dir / name
        if p.is_file():
            extra.append(
                {
                    "name": name,
                    "path": f"{rel_root}/{name}",
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                }
            )

    # Capture success criteria: driver finished and produced stdout/stderr files.
    captured = (out_dir / "status.env").is_file() and stdout_path.is_file() and stderr_path.is_file()
    if docker_rc != 0 and not captured:
        captured = False

    expected_exit = spec.get("expected_exit_status")
    if captured and expected_exit is not None and status["exit_status"] != expected_exit:
        # Still captured as replayable evidence; expected table records exit.
        pass

    record: dict[str, Any] = {
        "schema_version": 1,
        "case_id": case_id if not part_id else f"{case_id}:{part_id}",
        "oracle_execution_status": "captured" if captured else "not_captured",
        "evidence_status": "oracle_reference",
        "execution_status": "planned",
        "product_compatibility_evidence": False,
        "identity": {
            "oracle_image_id": IMAGE_ID,
            "upstream_commit": UPSTREAM_COMMIT,
            "upstream_release": "v2.5",
            "executable_path": exec_path,
            "executable_sha256": exec_sha,
            "capture_host_tool": "compat/installation/wave2/capture-driver.sh",
        },
        "invocation": {
            "argv": list(spec["argv"]),
            "working_directory": spec["working_directory"],
            "fixture_setup": list(spec["fixture_setup"]),
            "timeout_seconds": int(spec["timeout_seconds"]),
            "cleanup": list(spec["cleanup"]),
        },
        "environment": {
            "mode": spec["environment"]["mode"],
            "variables": dict(spec["environment"]["variables"]),
        },
        "process": status,
        "artifacts": {
            "stdout_bin": artifact_ref(f"{rel_root}/stdout.bin", stdout_path),
            "stderr_bin": artifact_ref(f"{rel_root}/stderr.bin", stderr_path),
            "extra": extra,
        },
        "file_tree_effects": tree,
        "observation_sha256": "0" * 64,
    }
    if not captured:
        record["not_captured_reason"] = (
            f"docker_rc={docker_rc}; missing status/stdout/stderr for replayable capture"
        )
    record["observation_sha256"] = observation_hash(record)
    return record


def validate_record(record: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads(CASE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(record)
    recomputed = observation_hash(record)
    if recomputed != record["observation_sha256"]:
        raise SystemExit(f"observation hash drift for {record['case_id']}")


def write_json(path: Path, value: Any) -> str:
    text = canonical_json(value)
    path.write_bytes(text.encode("ascii"))
    return sha256_bytes(text.encode("ascii"))


def main() -> int:
    if not UPSTREAM.is_dir():
        print(f"upstream missing: {UPSTREAM}", file=sys.stderr)
        return 2
    if not DRIVER.is_file():
        print(f"driver missing: {DRIVER}", file=sys.stderr)
        return 2

    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    OUT_ROOT.mkdir(parents=True)

    records: list[dict[str, Any]] = []
    expected_rows: list[dict[str, Any]] = []

    for spec in CASE_SPECS:
        case_id = spec["id"]
        print(f"capturing {case_id}...", flush=True)
        if spec.get("dual"):
            part_records = []
            for part in spec["parts"]:
                part_id = part["part_id"]
                out_dir = OUT_ROOT / case_id / part_id
                docker_rc = docker_run(part["driver_case"], out_dir, part["timeout_seconds"])
                record = build_record(
                    case_id=case_id,
                    part_id=part_id,
                    spec=part,
                    out_dir=out_dir,
                    docker_rc=docker_rc,
                )
                validate_record(record)
                write_json(out_dir / "capture.json", record)
                part_records.append(record)
                print(
                    f"  part {part_id}: status={record['oracle_execution_status']} "
                    f"exit={record['process']['exit_status']} docker_rc={docker_rc}",
                    flush=True,
                )
            # Parent case captured only if both parts captured.
            both = all(r["oracle_execution_status"] == "captured" for r in part_records)
            parent = {
                "schema_version": 1,
                "case_id": case_id,
                "oracle_execution_status": "captured" if both else "not_captured",
                "evidence_status": "oracle_reference",
                "execution_status": "planned",
                "product_compatibility_evidence": False,
                "identity": part_records[0]["identity"],
                "invocation": {
                    "argv": ["dual", "relative", "and", "space", "path", "probes"],
                    "working_directory": "/tmp/src",
                    "fixture_setup": [
                        "relative DESTDIR probe",
                        "space-containing DESTDIR probe",
                    ],
                    "timeout_seconds": 300,
                    "cleanup": ["rm -rf /tmp/src '/tmp/destdir space'"],
                },
                "environment": part_records[0]["environment"],
                "process": {
                    "exit_status": part_records[0]["process"]["exit_status"],
                    "signal": None,
                    "timed_out": False,
                    "child_processes_observed": [
                        {
                            "command": " ".join(part_records[0]["invocation"]["argv"]),
                            "exit_status": part_records[0]["process"]["exit_status"] or 0,
                        },
                        {
                            "command": " ".join(part_records[1]["invocation"]["argv"]),
                            "exit_status": part_records[1]["process"]["exit_status"] or 0,
                        },
                    ],
                },
                "artifacts": {
                    "stdout_bin": part_records[0]["artifacts"]["stdout_bin"],
                    "stderr_bin": part_records[0]["artifacts"]["stderr_bin"],
                    "extra": [
                        {
                            "name": "relative_capture",
                            "path": f"compat/installation/wave2/cases/{case_id}/relative/capture.json",
                            "sha256": sha256_file(OUT_ROOT / case_id / "relative" / "capture.json"),
                            "bytes": (OUT_ROOT / case_id / "relative" / "capture.json").stat().st_size,
                        },
                        {
                            "name": "space_capture",
                            "path": f"compat/installation/wave2/cases/{case_id}/space/capture.json",
                            "sha256": sha256_file(OUT_ROOT / case_id / "space" / "capture.json"),
                            "bytes": (OUT_ROOT / case_id / "space" / "capture.json").stat().st_size,
                        },
                        {
                            "name": "relative_stdout",
                            "path": part_records[0]["artifacts"]["stdout_bin"]["path"],
                            "sha256": part_records[0]["artifacts"]["stdout_bin"]["sha256"],
                            "bytes": part_records[0]["artifacts"]["stdout_bin"]["bytes"],
                        },
                        {
                            "name": "relative_stderr",
                            "path": part_records[0]["artifacts"]["stderr_bin"]["path"],
                            "sha256": part_records[0]["artifacts"]["stderr_bin"]["sha256"],
                            "bytes": part_records[0]["artifacts"]["stderr_bin"]["bytes"],
                        },
                        {
                            "name": "space_stdout",
                            "path": part_records[1]["artifacts"]["stdout_bin"]["path"],
                            "sha256": part_records[1]["artifacts"]["stdout_bin"]["sha256"],
                            "bytes": part_records[1]["artifacts"]["stdout_bin"]["bytes"],
                        },
                        {
                            "name": "space_stderr",
                            "path": part_records[1]["artifacts"]["stderr_bin"]["path"],
                            "sha256": part_records[1]["artifacts"]["stderr_bin"]["sha256"],
                            "bytes": part_records[1]["artifacts"]["stderr_bin"]["bytes"],
                        },
                    ],
                },
                "file_tree_effects": part_records[0]["file_tree_effects"],
                "observation_sha256": "0" * 64,
            }
            if not both:
                parent["not_captured_reason"] = "one or both path probes failed to capture"
            parent["observation_sha256"] = observation_hash(parent)
            validate_record(parent)
            write_json(OUT_ROOT / case_id / "capture.json", parent)
            records.append(parent)
            expected_rows.append(
                {
                    "id": case_id,
                    "oracle_execution_status": parent["oracle_execution_status"],
                    "expected_exit_status": 2,
                    "observation_sha256": parent["observation_sha256"],
                    "stdout_sha256": part_records[0]["artifacts"]["stdout_bin"]["sha256"],
                    "stderr_sha256": part_records[0]["artifacts"]["stderr_bin"]["sha256"],
                    "space_stdout_sha256": part_records[1]["artifacts"]["stdout_bin"]["sha256"],
                    "space_stderr_sha256": part_records[1]["artifacts"]["stderr_bin"]["sha256"],
                    "argv": parent["invocation"]["argv"],
                    "oracle_image_id": IMAGE_ID,
                    "upstream_commit": UPSTREAM_COMMIT,
                    "capture_path": f"compat/installation/wave2/cases/{case_id}/capture.json",
                }
            )
            continue

        out_dir = OUT_ROOT / case_id
        docker_rc = docker_run(spec["driver_case"], out_dir, spec["timeout_seconds"])
        record = build_record(
            case_id=case_id,
            part_id=None,
            spec=spec,
            out_dir=out_dir,
            docker_rc=docker_rc,
        )
        validate_record(record)
        write_json(out_dir / "capture.json", record)
        records.append(record)
        expected_rows.append(
            {
                "id": case_id,
                "oracle_execution_status": record["oracle_execution_status"],
                "expected_exit_status": spec.get("expected_exit_status"),
                "observation_sha256": record["observation_sha256"],
                "stdout_sha256": record["artifacts"]["stdout_bin"]["sha256"],
                "stderr_sha256": record["artifacts"]["stderr_bin"]["sha256"],
                "argv": record["invocation"]["argv"],
                "oracle_image_id": IMAGE_ID,
                "upstream_commit": UPSTREAM_COMMIT,
                "capture_path": f"compat/installation/wave2/cases/{case_id}/capture.json",
            }
        )
        print(
            f"  status={record['oracle_execution_status']} "
            f"exit={record['process']['exit_status']} docker_rc={docker_rc}",
            flush=True,
        )

    # Refresh directory companion from layout capture if present.
    layout_lock = OUT_ROOT / "INST-LAYOUT-001" / "installed-directories.lock"
    if layout_lock.is_file():
        (WAVE2 / "installed-directories.lock").write_bytes(layout_lock.read_bytes())

    index = {
        "schema_version": 1,
        "wave": 2,
        "capture_format": "replayable_case_records_v1",
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "oracle_image_id": IMAGE_ID,
        "evidence_status": "oracle_reference",
        "execution_status": "planned",
        "product_compatibility_evidence": False,
        "case_count": 13,
        "cases": [
            {
                "id": row["id"],
                "oracle_execution_status": row["oracle_execution_status"],
                "capture_path": row["capture_path"],
                "observation_sha256": row["observation_sha256"],
            }
            for row in expected_rows
        ],
        "directory_companion": {
            "path": "compat/installation/wave2/installed-directories.lock",
            "sha256": sha256_file(WAVE2 / "installed-directories.lock"),
            "entry_count": len(
                (WAVE2 / "installed-directories.lock").read_text().splitlines()
            ),
            "mode": "755",
            "recorder": "compat/installation/wave2/installed-tree-directories.sh",
            "baseline_unchanged": True,
        },
        "known_gaps": [
            "baseline installed-tree.lock still excludes directory rows",
            "staged DESTDIR installs omit image-only /usr/local/man symlink",
            "optional genhtml updown/HTML-reference qualification remains open",
            "space-containing DESTDIR behavior is GNU/Linux-path specific",
            "partial install uses fake install wrapper",
            "no multi-platform matrix beyond pinned x86_64 Linux image",
            "no Ferricov product installer evidence",
            "M1 parser/model installation surfaces remain blocked",
        ],
    }
    expected = {
        "schema_version": 1,
        "wave": 2,
        "evidence_status": "oracle_reference",
        "execution_status": "planned",
        "product_compatibility_evidence": False,
        "oracle_image_id": IMAGE_ID,
        "upstream_commit": UPSTREAM_COMMIT,
        "cases": expected_rows,
    }
    idx_sha = write_json(CAPTURE_INDEX, index)
    exp_sha = write_json(EXPECTED_TABLE, expected)
    print("index", idx_sha)
    print("expected", exp_sha)
    captured = sum(1 for r in expected_rows if r["oracle_execution_status"] == "captured")
    print(f"captured={captured}/13")
    for row in expected_rows:
        print(row["id"], row["oracle_execution_status"], row["observation_sha256"][:12])
    return 0 if captured > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
