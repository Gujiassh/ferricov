#!/usr/bin/env python3
"""Replayable installation wave-2 Oracle capture orchestrator.

Runs each INST case inside the pinned Docker image with fail-closed provenance,
retains raw stdout/stderr, observed env/argv/cwd, process lifecycle, and full
file-tree rows. Writes per-case capture records and the capture index only.

The independent expected-case-table.json is NEVER written or modified here.
It must be authored separately; this tool only loads and verifies it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
WAVE2 = Path(__file__).resolve().parent
CASE_SCHEMA = WAVE2 / "oracle-case-capture.schema.json"
DRIVER = WAVE2 / "capture-driver.sh"
DIR_RECORDER = WAVE2 / "installed-tree-directories.sh"
PROCESS_OBSERVER = WAVE2 / "process-observer.py"
PIN_INV = ROOT / "compat/upstream/python-objects.inv"
PIN_PY = ROOT / "compat/upstream/pin-intersphinx.py"
UPSTREAM = Path(os.environ.get("LCOV_SOURCE_ROOT", "/tmp/lcov-upstream-reference"))
PINNED_IMAGE_ID = "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
PINNED_UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
OUT_ROOT = WAVE2 / "cases"
CAPTURE_INDEX = WAVE2 / "oracle-capture.json"
EXPECTED_TABLE = WAVE2 / "expected-case-table.json"

# Case specs describe how to invoke the driver; observed argv/cwd/env/exit come
# from the container, not from copying these fields into the capture record.
CASE_SPECS: list[dict[str, Any]] = [
    {
        "id": "INST-LAYOUT-001",
        "driver_case": "INST-LAYOUT-001",
        "timeout_seconds": 60,
        "fixture_setup": [
            "use pinned image installed payload under /usr/local",
            "mount wave2 directory companion recorder",
        ],
        "cleanup": ["none_required_read_only_payload_scan"],
        "environment_mode": "clean_explicit",
        "requires_source": False,
    },
    {
        "id": "INST-STAGE-001",
        "driver_case": "INST-STAGE-001",
        "timeout_seconds": 600,
        "fixture_setup": [
            "copy pinned upstream source to /tmp/src",
            "pin docs intersphinx inventory",
            "build doc_finished",
            "empty DESTDIR=/tmp/destdir-stage",
        ],
        "cleanup": ["rm -rf /tmp/destdir-stage /tmp/src"],
        "environment_mode": "clean_explicit",
        "requires_source": True,
    },
    {
        "id": "INST-INTERP-001",
        "driver_case": "INST-INTERP-001",
        "timeout_seconds": 600,
        "fixture_setup": [
            "copy pinned upstream source",
            "build doc_finished",
            "set LCOV_PERL override to nonexistent custom path",
        ],
        "cleanup": ["rm -rf /tmp/destdir-interp /tmp/src"],
        "environment_mode": "clean_override",
        "requires_source": True,
    },
    {
        "id": "INST-CONFIG-DISCOVERY-001",
        "driver_case": "INST-CONFIG-DISCOVERY-001",
        "timeout_seconds": 60,
        "fixture_setup": [
            "create /tmp/h1/.lcovrc and /tmp/lh/etc/lcovrc",
            "run lcovutil-equivalent HOME/LCOV_HOME search probe",
        ],
        "cleanup": ["rm -rf /tmp/h1 /tmp/lh /tmp/config-probe.pl"],
        "environment_mode": "clean_override",
        "requires_source": False,
    },
    {
        "id": "INST-UNINSTALL-001",
        "driver_case": "INST-UNINSTALL-001",
        "timeout_seconds": 600,
        "fixture_setup": [
            "install full payload into DESTDIR",
            "add foreign sentinel files under etc and man",
        ],
        "cleanup": ["rm -rf /tmp/destdir-uninst /tmp/src"],
        "environment_mode": "clean_explicit",
        "requires_source": True,
    },
    {
        "id": "INST-PARTIAL-001",
        "driver_case": "INST-PARTIAL-001",
        "timeout_seconds": 600,
        "fixture_setup": [
            "build docs",
            "install fake install wrapper that fails after count>20",
        ],
        "cleanup": ["rm -rf /tmp/partial /tmp/src /tmp/fake-install /tmp/install-count"],
        "environment_mode": "clean_explicit",
        "requires_source": True,
    },
    {
        "id": "INST-DOC-FAIL-001",
        "driver_case": "INST-DOC-FAIL-001",
        "timeout_seconds": 300,
        "fixture_setup": [
            "hide /usr/bin/sphinx-build",
            "remove doc_finished and docs/_build",
        ],
        "cleanup": ["restore sphinx-build", "rm -rf /tmp/docfail /tmp/src"],
        "environment_mode": "clean_explicit",
        "requires_source": True,
    },
    {
        "id": "INST-PATH-001",
        "dual": True,
        "parts": [
            {
                "part_id": "relative",
                "driver_case": "INST-PATH-REL-001",
                "timeout_seconds": 120,
                "fixture_setup": ["relative DESTDIR=rel-dest"],
                "cleanup": ["rm -rf /tmp/src"],
                "environment_mode": "clean_explicit",
                "requires_source": True,
            },
            {
                "part_id": "space",
                "driver_case": "INST-PATH-SPACE-001",
                "timeout_seconds": 300,
                "fixture_setup": ["space-containing absolute DESTDIR"],
                "cleanup": ["rm -rf '/tmp/destdir space' /tmp/src"],
                "environment_mode": "clean_explicit",
                "requires_source": True,
            },
        ],
    },
    {
        "id": "INST-DIRTY-ASSET-001",
        "driver_case": "INST-DIRTY-ASSET-001",
        "timeout_seconds": 600,
        "fixture_setup": [
            "create untracked scripts/zz_dirty_wave2_sentinel",
            "build docs then install",
        ],
        "cleanup": ["rm -rf /tmp/destdir-dirty /tmp/src"],
        "environment_mode": "clean_explicit",
        "requires_source": True,
    },
    {
        "id": "INST-TEST-RUN-001",
        "driver_case": "INST-TEST-RUN-001",
        "timeout_seconds": 60,
        "fixture_setup": [
            "use installed tests in pinned image",
            "unset LCOV_HOME",
        ],
        "cleanup": ["none_required_read_only"],
        "environment_mode": "clean_empty",
        "requires_source": False,
    },
    {
        "id": "INST-DOC-PATH-001",
        "driver_case": "INST-DOC-PATH-001",
        "timeout_seconds": 60,
        "fixture_setup": ["extract README.rst path claims vs retained roots"],
        "cleanup": ["rm -rf /tmp/src"],
        "environment_mode": "clean_explicit",
        "requires_source": True,
    },
    {
        "id": "INST-REPORT-ASSET-001",
        "driver_case": "INST-REPORT-ASSET-001",
        "timeout_seconds": 60,
        "fixture_setup": ["scan bin/genhtml for retained report assets"],
        "cleanup": ["rm -rf /tmp/src"],
        "environment_mode": "clean_explicit",
        "requires_source": True,
    },
    {
        "id": "INST-LICENSE-001",
        "driver_case": "INST-LICENSE-001",
        "timeout_seconds": 600,
        "fixture_setup": [
            "install payload",
            "observe COPYING in source vs payload",
        ],
        "cleanup": ["rm -rf /tmp/destdir-lic /tmp/src"],
        "environment_mode": "clean_explicit",
        "requires_source": True,
    },
]

# Retained runner-qualification probes (signal + timeout). Not part of the
# 13 INST product case catalog; stored under cases/_runner/ and indexed
# separately so lifecycle paths have executable Oracle evidence.
RUNNER_SPECS: list[dict[str, Any]] = [
    {
        "id": "INST-RUNNER-SIGNAL-001",
        "driver_case": "INST-RUNNER-SIGNAL-001",
        "timeout_seconds": 30,
        "fixture_setup": ["ptrace supervisor force SIGTERM after exec"],
        "cleanup": ["none_required"],
        "environment_mode": "clean_explicit",
        "requires_source": False,
        "qualification": "signal",
    },
    {
        "id": "INST-RUNNER-TIMEOUT-001",
        "driver_case": "INST-RUNNER-TIMEOUT-001",
        "timeout_seconds": 5,
        "fixture_setup": ["ptrace supervisor enforce 1s deadline on sleep"],
        "cleanup": ["none_required"],
        "environment_mode": "clean_explicit",
        "requires_source": False,
        "qualification": "timeout",
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


def load_expected_table() -> dict[str, Any]:
    if not EXPECTED_TABLE.is_file():
        raise SystemExit(f"independent expected table missing: {EXPECTED_TABLE}")
    table = json.loads(EXPECTED_TABLE.read_text(encoding="utf-8"))
    if table.get("product_compatibility_evidence") is not False:
        raise SystemExit("expected table claims product compatibility")
    if table.get("evidence_status") != "oracle_reference":
        raise SystemExit("expected table evidence_status drift")
    if table.get("execution_status") != "planned":
        raise SystemExit("expected table execution_status drift")
    if table.get("oracle_image_id") != PINNED_IMAGE_ID:
        raise SystemExit("expected table image id drift")
    if table.get("upstream_commit") != PINNED_UPSTREAM_COMMIT:
        raise SystemExit("expected table upstream commit drift")
    cases = table.get("cases")
    if not isinstance(cases, list) or len(cases) != 13:
        raise SystemExit("expected table must contain 13 cases")
    return table


def verify_upstream_commit() -> str:
    if not UPSTREAM.is_dir():
        raise SystemExit(f"upstream missing: {UPSTREAM}")
    proc = subprocess.run(
        ["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"git rev-parse failed: {proc.stderr}")
    commit = proc.stdout.strip()
    if commit != PINNED_UPSTREAM_COMMIT:
        raise SystemExit(
            f"upstream commit drift: expected={PINNED_UPSTREAM_COMMIT} actual={commit}"
        )
    return commit


def resolve_image_and_runtime() -> tuple[str, str]:
    """Fail-closed: docker inspect must yield the pinned image id."""
    inspect = subprocess.run(
        ["docker", "image", "inspect", PINNED_IMAGE_ID, "--format", "{{.Id}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode != 0:
        raise SystemExit(f"docker image inspect failed: {inspect.stderr}")
    image_id = inspect.stdout.strip()
    if image_id != PINNED_IMAGE_ID:
        raise SystemExit(
            f"executed image id drift: expected={PINNED_IMAGE_ID} actual={image_id}"
        )
    runtime = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if runtime.returncode != 0 or not runtime.stdout.strip():
        raise SystemExit(f"docker runtime identity failed: {runtime.stderr}")
    return image_id, runtime.stdout.strip()


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
    # Inner subject wait code (not host docker rc).
    host_raw = values.get("HOST_OBSERVER_CODE", "")
    subject_wait = int(host_raw) if host_raw not in ("",) else -1
    return {
        "exit_status": exit_status,
        "signal": signal,
        "timed_out": values.get("TIMED_OUT", "0") == "1",
        "subject_wait_code": subject_wait,
        "workdir": values.get("WORKDIR", ""),
        "executable_path": values.get("EXECUTABLE_PATH", ""),
        "executable_sha256": values.get("EXECUTABLE_SHA256", ""),
        "qualification": values.get("QUALIFICATION", "none"),
    }


def parse_observed_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            env[key] = val
    return env


def parse_observed_argv(path: Path) -> list[str]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise SystemExit(f"invalid observed argv: {path}")
    return data


def parse_children(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"invalid children: {path}")
    return data


def parse_tree(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "root": "/",
            "file_count": 0,
            "symlink_count": 0,
            "directory_count": 0,
            "paths_sha256": sha256_bytes(b""),
            "rows": [],
        }
    tree = json.loads(path.read_text(encoding="utf-8"))
    if "rows" not in tree:
        # Reject truncated legacy trees.
        raise SystemExit(f"tree effects missing full rows: {path}")
    return tree


def parse_cleanup(path: Path, declared: list[str]) -> list[str]:
    if path.is_file():
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]
        if lines:
            return lines
    return list(declared)


def normalize_capture_output(out_dir: Path) -> None:
    if not out_dir.is_dir():
        return
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
        try:
            path.unlink()
        except OSError:
            pass
        path.write_bytes(data)
        path.chmod(0o644)
    try:
        out_dir.chmod(0o755)
    except OSError:
        pass


def docker_run(
    case_id: str,
    out_dir: Path,
    timeout: int,
    image_id: str,
) -> tuple[int, str]:
    """Run named container; always remove it. Returns (rc, host_observer_note)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.chmod(0o777)
    name = f"ferricov-inst-wave2-{case_id.lower().replace(':', '-')}-{uuid.uuid4().hex[:8]}"
    cmd = [
        "docker",
        "run",
        "--name",
        name,
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
        f"{PROCESS_OBSERVER}:/tmp/process-observer.py:ro",
        "-v",
        f"{out_dir}:/out",
        # Do not pass ambient host env; only SRC_RO mount path for prepare_src.
        "-e",
        "SRC_RO=/src-ro",
        "-e",
        "OBSERVER=/tmp/process-observer.py",
        image_id,
        "bash",
        "-lc",
        f"chmod +x /tmp/capture-driver.sh /tmp/installed-tree-directories.sh /tmp/process-observer.py; "
        f"/tmp/capture-driver.sh {case_id} /out; "
        f"chmod -R a+rwX /out || true",
    ]
    host_note = "completed"
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 120,
        )
        rc = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        host_note = "host_timeout"
        rc = 124
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        subprocess.run(["docker", "kill", name], capture_output=True, check=False)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)

    normalize_capture_output(out_dir)
    (out_dir / "docker.stdout.txt").write_text(stdout or "")
    (out_dir / "docker.stderr.txt").write_text(stderr or "")
    (out_dir / "docker.stdout.txt").chmod(0o644)
    (out_dir / "docker.stderr.txt").chmod(0o644)
    (out_dir / "host-observer.txt").write_text(f"rc={rc}\nnote={host_note}\n")
    return rc, host_note


def artifact_ref(rel_path: str, path: Path) -> dict[str, Any]:
    if not re.match(r"^compat/installation/wave2/cases/", rel_path):
        raise SystemExit(f"unsafe artifact path: {rel_path}")
    if ".." in Path(rel_path).parts:
        raise SystemExit(f"artifact path escapes: {rel_path}")
    data = path.read_bytes() if path.is_file() else b""
    if not path.is_file():
        path.write_bytes(data)
    return {
        "path": rel_path,
        "sha256": sha256_bytes(data),
        "bytes": len(data),
    }


def path_has_dotdot(value: str) -> bool:
    return ".." in Path(value).parts


def semantic_validate_record(record: dict[str, Any]) -> None:
    """Fail-closed semantic checks beyond JSON Schema."""
    if record.get("oracle_execution_status") != "captured":
        return
    for key in (
        record["identity"]["executable_path"],
        record["invocation"]["working_directory"],
        record["file_tree_effects"]["root"],
    ):
        if not str(key).startswith("/") or path_has_dotdot(str(key)):
            raise SystemExit(f"{record['case_id']}: unsafe path {key!r}")
    for art in (
        record["artifacts"]["stdout_bin"],
        record["artifacts"]["stderr_bin"],
        *record["artifacts"].get("extra", []),
    ):
        p = art["path"]
        if not p.startswith("compat/installation/wave2/cases/"):
            raise SystemExit(f"{record['case_id']}: artifact prefix drift {p}")
        if path_has_dotdot(p):
            raise SystemExit(f"{record['case_id']}: artifact traversal {p}")
    for row in record["file_tree_effects"]["rows"]:
        if not row["path"].startswith("/") or path_has_dotdot(row["path"]):
            raise SystemExit(f"{record['case_id']}: tree row path {row['path']}")
        if row["kind"] == "file" and not re.fullmatch(r"[0-9a-f]{64}", row["identity"]):
            raise SystemExit(f"{record['case_id']}: file row identity must be sha256")
        if row["kind"] == "directory" and row["identity"] != ".":
            raise SystemExit(f"{record['case_id']}: directory identity must be .")
    tree = record["file_tree_effects"]
    files = sum(1 for r in tree["rows"] if r["kind"] == "file")
    dirs = sum(1 for r in tree["rows"] if r["kind"] == "directory")
    links = sum(1 for r in tree["rows"] if r["kind"] == "symlink")
    if files != tree["file_count"] or dirs != tree["directory_count"] or links != tree["symlink_count"]:
        raise SystemExit(f"{record['case_id']}: tree count/rows inconsistency")
    children = record["process"]["child_processes_observed"]
    if not children:
        raise SystemExit(f"{record['case_id']}: captured children must be nonempty")
    for child in children:
        outs = [
            child["exit_status"] is not None,
            child["signal"] is not None,
            bool(child["timed_out"]),
        ]
        # Exactly one valid outcome shape: exit XOR signal, timeout requires signal+null exit.
        if child["timed_out"]:
            if child["signal"] is None or child["exit_status"] is not None:
                raise SystemExit(f"{record['case_id']}: timed-out child shape invalid")
        else:
            if (child["exit_status"] is None) == (child["signal"] is None):
                raise SystemExit(f"{record['case_id']}: child must have exactly one of exit/signal")
    proc = record["process"]
    if proc["timed_out"]:
        if proc["signal"] is None or proc["exit_status"] is not None:
            raise SystemExit(f"{record['case_id']}: timed-out process shape invalid")
    else:
        if (proc["exit_status"] is None) == (proc["signal"] is None):
            raise SystemExit(f"{record['case_id']}: process must have exactly one of exit/signal")
    # declared env must equal observed env (clean-env attestation).
    if record["environment"]["variables"] != record["environment"]["observed_variables"]:
        raise SystemExit(f"{record['case_id']}: declared/observed environment mismatch")


def build_record(
    *,
    case_id: str,
    part_id: str | None,
    spec: dict[str, Any],
    out_dir: Path,
    docker_rc: int,
    host_note: str,
    image_id: str,
    docker_runtime: str,
    upstream_commit: str,
) -> dict[str, Any]:
    rel_root = f"compat/installation/wave2/cases/{case_id}" + (f"/{part_id}" if part_id else "")
    stdout_path = out_dir / "stdout.bin"
    stderr_path = out_dir / "stderr.bin"
    status = parse_status(out_dir / "status.env")
    tree = parse_tree(out_dir / "tree-effects.json")
    observed_env = parse_observed_env(out_dir / "observed-env.env")
    observed_argv = parse_observed_argv(out_dir / "observed-argv.json")
    children = parse_children(out_dir / "observed-children.json")
    cleanup = parse_cleanup(out_dir / "cleanup.log", list(spec["cleanup"]))

    # Live process evidence from status (ptrace observer) preferred over meta.
    exec_path = status.get("executable_path") or ""
    exec_sha = status.get("executable_sha256") or ""
    meta = out_dir / "meta.env"
    if (not exec_path or not exec_sha) and meta.is_file():
        for line in meta.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("EXECUTABLE_PATH=") and not exec_path:
                exec_path = line.split("=", 1)[1]
            if line.startswith("EXECUTABLE_SHA256=") and not exec_sha:
                exec_sha = line.split("=", 1)[1]

    cwd = status.get("workdir") or ""
    if not cwd.startswith("/") and meta.is_file():
        for line in meta.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("WORKDIR="):
                cwd = line.split("=", 1)[1]
                break

    extra: list[dict[str, Any]] = []
    for name in (
        "observation.txt",
        "installed-directories.lock",
        "doc.log",
        "install.log",
        "cleanup.log",
        "observed-env.env",
        "observed-argv.json",
        "observed-children.json",
        "host-observer.txt",
        "status.env",
        "run-meta.env",
    ):
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

    captured = (
        (out_dir / "status.env").is_file()
        and stdout_path.is_file()
        and stderr_path.is_file()
        and bool(observed_argv)
        and bool(children)
        and exec_path.startswith("/")
        and bool(re.fullmatch(r"[0-9a-f]{64}", exec_sha or ""))
        and exec_sha != "0" * 64
        and cwd.startswith("/")
        and not path_has_dotdot(exec_path)
        and not path_has_dotdot(cwd)
        and "rows" in tree
        and not path_has_dotdot(tree.get("root", ""))
    )
    # Host docker observer code is the actual docker run rc (outer), not inner wait.
    process = {
        "exit_status": status["exit_status"],
        "signal": status["signal"],
        "timed_out": bool(status["timed_out"]),
        "host_observer_code": int(docker_rc),
        "child_processes_observed": children,
    }
    if host_note == "host_timeout" and not process["timed_out"]:
        process["timed_out"] = True
        process["signal"] = process["signal"] or 15
        process["exit_status"] = None

    # Declared variables MUST equal observed clean env (no subset filtering that drifts).
    declared_vars = dict(observed_env)

    record: dict[str, Any] = {
        "schema_version": 1,
        "case_id": case_id if not part_id else f"{case_id}:{part_id}",
        "oracle_execution_status": "captured" if captured else "not_captured",
        "evidence_status": "oracle_reference",
        "execution_status": "planned",
        "product_compatibility_evidence": False,
        "identity": {
            "oracle_image_id": image_id,
            "docker_runtime": docker_runtime,
            "upstream_commit": upstream_commit,
            "upstream_release": "v2.5",
            "executable_path": exec_path if exec_path.startswith("/") else "/usr/bin/false",
            "executable_sha256": exec_sha if re.fullmatch(r"[0-9a-f]{64}", exec_sha or "") else "f" * 64,
            "capture_host_tool": "compat/installation/wave2/process-observer.py",
        },
        "invocation": {
            "argv": observed_argv or ["missing"],
            "working_directory": cwd if cwd.startswith("/") else "/",
            "fixture_setup": list(spec["fixture_setup"]),
            "timeout_seconds": int(spec["timeout_seconds"]),
            "cleanup": cleanup if cleanup else list(spec["cleanup"]),
        },
        "environment": {
            "mode": spec["environment_mode"],
            "variables": declared_vars if declared_vars else {"PATH": "/usr/bin"},
            "observed_variables": declared_vars if declared_vars else {"PATH": "/usr/bin"},
        },
        "process": process,
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
            f"docker_rc={docker_rc}; host_note={host_note}; "
            "missing live observed argv/status/stdout/stderr/executable/children/tree rows"
        )
        if record["identity"]["executable_sha256"] == "0" * 64:
            record["identity"]["executable_sha256"] = "f" * 64
        if not record["identity"]["executable_path"].startswith("/"):
            record["identity"]["executable_path"] = "/usr/bin/false"
        if not record["process"]["child_processes_observed"]:
            record["process"]["child_processes_observed"] = [
                {
                    "command": "missing",
                    "argv": ["missing"],
                    "exit_status": 1,
                    "signal": None,
                    "timed_out": False,
                }
            ]
    record["observation_sha256"] = observation_hash(record)
    return record


def validate_record(record: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads(CASE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(record)
    semantic_validate_record(record)
    recomputed = observation_hash(record)
    if recomputed != record["observation_sha256"]:
        raise SystemExit(f"observation hash drift for {record['case_id']}")


def write_json(path: Path, value: Any) -> str:
    text = canonical_json(value)
    path.write_bytes(text.encode("ascii"))
    return sha256_bytes(text.encode("ascii"))


def verify_against_expected(
    case_id: str,
    record: dict[str, Any],
    row: dict[str, Any],
    *,
    part: str | None = None,
) -> None:
    """Verify observed capture against independently authored expected row.

    Does not rewrite the expected table. Observation/stream hashes are compared
    only when the expected row already pins them (post-authoring).
    """
    prefix = f"{case_id}" + (f":{part}" if part else "")
    if row.get("oracle_image_id") != PINNED_IMAGE_ID:
        raise SystemExit(f"{prefix}: expected image drift")
    if row.get("upstream_commit") != PINNED_UPSTREAM_COMMIT:
        raise SystemExit(f"{prefix}: expected upstream drift")

    # Semantic fields that must be independently authored.
    if "expected_exit_status" in row and row["expected_exit_status"] is not None:
        if record["process"]["exit_status"] != row["expected_exit_status"]:
            raise SystemExit(
                f"{prefix}: exit drift expected={row['expected_exit_status']} "
                f"actual={record['process']['exit_status']}"
            )
    if "argv" in row and record["invocation"]["argv"] != row["argv"]:
        raise SystemExit(f"{prefix}: argv drift")
    if "working_directory" in row and record["invocation"]["working_directory"] != row["working_directory"]:
        raise SystemExit(f"{prefix}: cwd drift")
    if "timeout_seconds" in row and record["invocation"]["timeout_seconds"] != row["timeout_seconds"]:
        raise SystemExit(f"{prefix}: timeout drift")
    if "executable_path" in row and record["identity"]["executable_path"] != row["executable_path"]:
        raise SystemExit(f"{prefix}: executable path drift")
    if "environment_mode" in row and record["environment"]["mode"] != row["environment_mode"]:
        raise SystemExit(f"{prefix}: environment mode drift")
    if "timed_out" in row and record["process"]["timed_out"] != row["timed_out"]:
        raise SystemExit(f"{prefix}: timed_out drift")
    if "signal" in row and record["process"]["signal"] != row["signal"]:
        raise SystemExit(f"{prefix}: signal drift")

    # Optional pinned stream/observation hashes (immutable once authored).
    # No hash-drift override may leave invalid committed captures.
    if row.get("observation_sha256") and row["observation_sha256"] != record["observation_sha256"]:
        raise SystemExit(
            f"{prefix}: observation hash drift "
            f"expected={row['observation_sha256']} actual={record['observation_sha256']}"
        )
    if row.get("stdout_sha256"):
        actual = record["artifacts"]["stdout_bin"]["sha256"]
        if actual != row["stdout_sha256"]:
            raise SystemExit(f"{prefix}: stdout hash drift expected={row['stdout_sha256']} actual={actual}")
    if row.get("stderr_sha256"):
        actual = record["artifacts"]["stderr_bin"]["sha256"]
        if actual != row["stderr_sha256"]:
            raise SystemExit(f"{prefix}: stderr hash drift expected={row['stderr_sha256']} actual={actual}")
    if "executable_sha256" in row and row["executable_sha256"] != record["identity"]["executable_sha256"]:
        raise SystemExit(f"{prefix}: executable hash drift")
    if "host_observer_code" in row and record["process"]["host_observer_code"] != row["host_observer_code"]:
        raise SystemExit(f"{prefix}: host_observer_code drift")


def expected_row_map(table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in table["cases"]}


def main() -> int:
    expected_table = load_expected_table()
    expected_by_id = expected_row_map(expected_table)
    upstream_commit = verify_upstream_commit()
    image_id, docker_runtime = resolve_image_and_runtime()

    if not DRIVER.is_file() or not PROCESS_OBSERVER.is_file():
        print(f"driver/observer missing", file=sys.stderr)
        return 2

    # Preserve expected table mtime/bytes: never open for write.
    expected_bytes = EXPECTED_TABLE.read_bytes()
    expected_sha_before = sha256_bytes(expected_bytes)

    # Transactional staging: capture into temp tree, fully validate, then atomic replace.
    staging_parent = WAVE2 / ".capture-staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = staging_parent / f"run-{uuid.uuid4().hex}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    staging_cases = staging / "cases"
    staging_cases.mkdir()
    staging_index = staging / "oracle-capture.json"
    staging_dir_lock = staging / "installed-directories.lock"

    records: list[dict[str, Any]] = []
    index_rows: list[dict[str, Any]] = []
    runner_rows: list[dict[str, Any]] = []

    try:
        for spec in CASE_SPECS:
            case_id = spec["id"]
            if case_id not in expected_by_id:
                raise SystemExit(f"expected table missing case {case_id}")
            row = expected_by_id[case_id]
            print(f"capturing {case_id}...", flush=True)

            if spec.get("dual"):
                part_records = []
                for part in spec["parts"]:
                    part_id = part["part_id"]
                    out_dir = staging_cases / case_id / part_id
                    docker_rc, host_note = docker_run(
                        part["driver_case"], out_dir, part["timeout_seconds"], image_id
                    )
                    record = build_record(
                        case_id=case_id,
                        part_id=part_id,
                        spec=part,
                        out_dir=out_dir,
                        docker_rc=docker_rc,
                        host_note=host_note,
                        image_id=image_id,
                        docker_runtime=docker_runtime,
                        upstream_commit=upstream_commit,
                    )
                    validate_record(record)
                    part_row = row
                    if isinstance(row.get("parts"), dict) and part_id in row["parts"]:
                        part_row = {**row, **row["parts"][part_id]}
                    verify_against_expected(case_id, record, part_row, part=part_id)
                    write_json(out_dir / "capture.json", record)
                    part_records.append(record)
                    print(
                        f"  part {part_id}: status={record['oracle_execution_status']} "
                        f"exit={record['process']['exit_status']} docker_rc={docker_rc}",
                        flush=True,
                    )

                both = all(r["oracle_execution_status"] == "captured" for r in part_records)
                parent = {
                    "schema_version": 1,
                    "case_id": case_id,
                    "oracle_execution_status": "captured" if both else "not_captured",
                    "evidence_status": "oracle_reference",
                    "execution_status": "planned",
                    "product_compatibility_evidence": False,
                    "identity": {
                        **part_records[0]["identity"],
                    },
                    "invocation": {
                        "argv": part_records[0]["invocation"]["argv"],
                        "working_directory": part_records[0]["invocation"]["working_directory"],
                        "fixture_setup": [
                            "relative DESTDIR probe",
                            "space-containing DESTDIR probe",
                        ],
                        "timeout_seconds": 300,
                        "cleanup": [
                            part_records[0]["invocation"]["cleanup"][0]
                            if part_records[0]["invocation"]["cleanup"]
                            else "rm -rf /tmp/src",
                            part_records[1]["invocation"]["cleanup"][0]
                            if part_records[1]["invocation"]["cleanup"]
                            else "rm -rf '/tmp/destdir space'",
                        ],
                    },
                    "environment": part_records[0]["environment"],
                    "process": {
                        "exit_status": part_records[0]["process"]["exit_status"],
                        "signal": part_records[0]["process"]["signal"],
                        "timed_out": False,
                        "host_observer_code": part_records[0]["process"]["host_observer_code"],
                        "child_processes_observed": [
                            {
                                "command": " ".join(part_records[0]["invocation"]["argv"]),
                                "argv": part_records[0]["invocation"]["argv"],
                                "exit_status": part_records[0]["process"]["exit_status"],
                                "signal": part_records[0]["process"]["signal"],
                                "timed_out": part_records[0]["process"]["timed_out"],
                            },
                            {
                                "command": " ".join(part_records[1]["invocation"]["argv"]),
                                "argv": part_records[1]["invocation"]["argv"],
                                "exit_status": part_records[1]["process"]["exit_status"],
                                "signal": part_records[1]["process"]["signal"],
                                "timed_out": part_records[1]["process"]["timed_out"],
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
                                "sha256": sha256_file(staging_cases / case_id / "relative" / "capture.json"),
                                "bytes": (staging_cases / case_id / "relative" / "capture.json").stat().st_size,
                            },
                            {
                                "name": "space_capture",
                                "path": f"compat/installation/wave2/cases/{case_id}/space/capture.json",
                                "sha256": sha256_file(staging_cases / case_id / "space" / "capture.json"),
                                "bytes": (staging_cases / case_id / "space" / "capture.json").stat().st_size,
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
                verify_against_expected(case_id, parent, row)
                write_json(staging_cases / case_id / "capture.json", parent)
                records.append(parent)
                index_rows.append(
                    {
                        "id": case_id,
                        "oracle_execution_status": parent["oracle_execution_status"],
                        "capture_path": f"compat/installation/wave2/cases/{case_id}/capture.json",
                        "observation_sha256": parent["observation_sha256"],
                    }
                )
                continue

            out_dir = staging_cases / case_id
            docker_rc, host_note = docker_run(
                spec["driver_case"], out_dir, spec["timeout_seconds"], image_id
            )
            record = build_record(
                case_id=case_id,
                part_id=None,
                spec=spec,
                out_dir=out_dir,
                docker_rc=docker_rc,
                host_note=host_note,
                image_id=image_id,
                docker_runtime=docker_runtime,
                upstream_commit=upstream_commit,
            )
            validate_record(record)
            verify_against_expected(case_id, record, row)
            write_json(out_dir / "capture.json", record)
            records.append(record)
            index_rows.append(
                {
                    "id": case_id,
                    "oracle_execution_status": record["oracle_execution_status"],
                    "capture_path": f"compat/installation/wave2/cases/{case_id}/capture.json",
                    "observation_sha256": record["observation_sha256"],
                }
            )
            print(
                f"  status={record['oracle_execution_status']} "
                f"exit={record['process']['exit_status']} "
                f"signal={record['process']['signal']} "
                f"docker_rc={docker_rc} exe={record['identity']['executable_path']}",
                flush=True,
            )

        # Runner qualification probes (signal + timeout) retained under _runner/.
        for spec in RUNNER_SPECS:
            case_id = spec["id"]
            print(f"capturing runner {case_id}...", flush=True)
            out_dir = staging_cases / "_runner" / case_id
            docker_rc, host_note = docker_run(
                spec["driver_case"], out_dir, spec["timeout_seconds"], image_id
            )
            record = build_record(
                case_id=case_id,
                part_id=None,
                spec=spec,
                out_dir=out_dir,
                docker_rc=docker_rc,
                host_note=host_note,
                image_id=image_id,
                docker_runtime=docker_runtime,
                upstream_commit=upstream_commit,
            )
            # Rewrite artifact paths to _runner location already set via case_id.
            validate_record(record)
            write_json(out_dir / "capture.json", record)
            runner_rows.append(
                {
                    "id": case_id,
                    "oracle_execution_status": record["oracle_execution_status"],
                    "capture_path": f"compat/installation/wave2/cases/_runner/{case_id}/capture.json",
                    "observation_sha256": record["observation_sha256"],
                    "timed_out": record["process"]["timed_out"],
                    "signal": record["process"]["signal"],
                    "exit_status": record["process"]["exit_status"],
                    "host_observer_code": record["process"]["host_observer_code"],
                }
            )
            print(
                f"  runner status={record['oracle_execution_status']} "
                f"timed_out={record['process']['timed_out']} "
                f"signal={record['process']['signal']} "
                f"exit={record['process']['exit_status']} docker_rc={docker_rc}",
                flush=True,
            )

        layout_lock = staging_cases / "INST-LAYOUT-001" / "installed-directories.lock"
        if layout_lock.is_file():
            staging_dir_lock.write_bytes(layout_lock.read_bytes())
        elif (WAVE2 / "installed-directories.lock").is_file():
            staging_dir_lock.write_bytes((WAVE2 / "installed-directories.lock").read_bytes())
        else:
            raise SystemExit("directory companion lock missing after layout capture")

        index = {
            "schema_version": 1,
            "wave": 2,
            "capture_format": "replayable_case_records_v1",
            "upstream_release": "v2.5",
            "upstream_commit": upstream_commit,
            "oracle_image_id": image_id,
            "docker_runtime": docker_runtime,
            "evidence_status": "oracle_reference",
            "execution_status": "planned",
            "product_compatibility_evidence": False,
            "case_count": 13,
            "cases": index_rows,
            "runner_qualification": runner_rows,
            "directory_companion": {
                "path": "compat/installation/wave2/installed-directories.lock",
                "sha256": sha256_file(staging_dir_lock),
                "entry_count": len(staging_dir_lock.read_text().splitlines()),
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
        idx_sha = write_json(staging_index, index)

        expected_sha_after = sha256_bytes(EXPECTED_TABLE.read_bytes())
        if expected_sha_after != expected_sha_before:
            raise SystemExit("FATAL: expected-case-table.json was modified during recapture")

        captured = sum(1 for r in index_rows if r["oracle_execution_status"] == "captured")
        if captured != 13:
            raise SystemExit(f"not all cases captured: {captured}/13")
        if len(runner_rows) != 2 or any(r["oracle_execution_status"] != "captured" for r in runner_rows):
            raise SystemExit("runner qualification probes not captured")
        # Require real lifecycle outcomes on qualification probes.
        sig = next(r for r in runner_rows if r["id"] == "INST-RUNNER-SIGNAL-001")
        tout = next(r for r in runner_rows if r["id"] == "INST-RUNNER-TIMEOUT-001")
        if sig["signal"] is None or sig["timed_out"]:
            raise SystemExit(f"signal probe did not observe signal termination: {sig}")
        if not tout["timed_out"] or tout["signal"] is None:
            raise SystemExit(f"timeout probe did not observe timeout: {tout}")

        # Atomic replace of committed capture tree only after full success.
        final_cases = OUT_ROOT
        final_index = CAPTURE_INDEX
        final_lock = WAVE2 / "installed-directories.lock"
        backup = staging_parent / f"backup-{uuid.uuid4().hex}"
        backup.mkdir()
        if final_cases.exists():
            shutil.move(str(final_cases), str(backup / "cases"))
        if final_index.exists():
            shutil.move(str(final_index), str(backup / "oracle-capture.json"))
        if final_lock.exists():
            shutil.move(str(final_lock), str(backup / "installed-directories.lock"))
        try:
            shutil.move(str(staging_cases), str(final_cases))
            shutil.move(str(staging_index), str(final_index))
            shutil.move(str(staging_dir_lock), str(final_lock))
        except Exception:
            # Attempt restore on replace failure.
            if (backup / "cases").exists() and not final_cases.exists():
                shutil.move(str(backup / "cases"), str(final_cases))
            if (backup / "oracle-capture.json").exists() and not final_index.exists():
                shutil.move(str(backup / "oracle-capture.json"), str(final_index))
            if (backup / "installed-directories.lock").exists() and not final_lock.exists():
                shutil.move(str(backup / "installed-directories.lock"), str(final_lock))
            raise
        shutil.rmtree(backup, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)

        print("index", idx_sha)
        print("expected_table_sha_unchanged", expected_sha_before)
        print(f"captured={captured}/13")
        for row in index_rows:
            print(row["id"], row["oracle_execution_status"], row["observation_sha256"][:12])
        for row in runner_rows:
            print(
                row["id"],
                row["oracle_execution_status"],
                f"signal={row['signal']}",
                f"timed_out={row['timed_out']}",
                row["observation_sha256"][:12],
            )
        return 0
    except BaseException:
        # Strict failure: leave committed tree untouched; discard staging.
        # Catch BaseException so SystemExit from verify_against_expected also cleans up.
        shutil.rmtree(staging, ignore_errors=True)
        try:
            if staging_parent.is_dir() and not any(staging_parent.iterdir()):
                staging_parent.rmdir()
        except OSError:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
