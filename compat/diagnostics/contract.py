#!/usr/bin/env python3
"""Generate and validate the fail-closed LCOV 2.5 diagnostics contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).with_name("v2.5.json")
SCHEMA_PATH = ROOT / "compat/schema/diagnostics-contract.schema.json"
CORRECTNESS_ROOT = ROOT / "compat/correctness/baselines/m0-cli-oracle-v2.5"
CORRECTNESS_INDEX = CORRECTNESS_ROOT / "result.json"
TRACEFILE_BASELINE = ROOT / "compat/fixtures/m0-tracefiles/oracle-baseline.json"
TRACEFILE_CASES = ROOT / "compat/fixtures/m0-tracefiles/oracle-cases.json"
WAVE1_ROOT = Path(__file__).with_name("wave1")
WAVE1_INDEX = WAVE1_ROOT / "result.json"
SPEC_PATH = ROOT / "specs/001-full-lcov-compatibility/diagnostics-parallel-contract.md"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference")
)

EXPECTED_ARTIFACT_HASHES = {
    "compat/correctness/baselines/m0-cli-oracle-v2.5/result.json":
        "f1b8484ba8a9587791c294722ceddcca245c72fa1a090b0b5245375fec30f8a2",
    "compat/fixtures/m0-tracefiles/oracle-baseline.json":
        "eb45db04a984a4833e3556c6bddcfa2e7b0360e72c9d0051ab0c21ca8f3832ba",
    "compat/fixtures/m0-tracefiles/oracle-cases.json":
        "d5a274ecabdfbb29425092c1ff44cd5be1367a8a26bf38e46b7755978a059cf1",
    "compat/diagnostics/wave1/result.json":
        "abfda945b02bb3a31543a2501619fa19f38fac89b42d7e5f845c209c339cd454",
    "compat/diagnostics/wave2/result.json":
        "e66f0155c68fbe5d7d1ba8d103e1889b5a147247838832811e68b7869a329bdc",
}


WAVE1_EXPECTED_CASE_COUNT = 26
WAVE1_PINNED_IMAGE = (
    "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
)
WAVE1_FILE_TREE_SEMANTICS = "workspace_including_inputs"
WAVE1_TIMEOUT_SECONDS = 30
WAVE1_CLEANUP = (
    "remove_case_workdir_before_capture_and_force_remove_named_container"
)
WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES = {
    "HOME": "/work",
    "LANG": "C",
    "LC_ALL": "C",
    "TZ": "UTC",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}
WAVE1_DOCKER_CLI_HOST_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "C",
    "LC_ALL": "C",
    "TZ": "UTC",
}
WAVE1_ENVIRONMENT_POLICY = {
    "mode": "in_container_env_dash_i_clean",
    "inherits_host_environment": False,
    "declared_variables": WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES,
    "command_wrapper": ["env", "-i"],
    "effective_environment_variables": WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES,
    "reviewed_exclusions": [
        "host process environment is not inherited by docker CLI or Oracle command",
        "Oracle command environment is produced by in-container env -i with only declared_variables",
        "Docker-injected variables such as HOSTNAME do not remain because env -i replaces the environment",
    ],
}
WAVE1_CLEANUP_OUTCOME_TEMPLATE = {
    "policy": WAVE1_CLEANUP,
    "direct_child_reaped": True,
    "process_group_empty": None,
    "container_absent": True,
    "named_container_removed": True,
}
WAVE1_EXECUTION_ENVIRONMENT = {
    "docker_image": WAVE1_PINNED_IMAGE,
    "network": "none",
    "user": "1000:1000",
    "workdir": "/work",
    "env": WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES,
    "tmpfs": ["/tmp:rw,exec,mode=1777"],
    "timeout_seconds": WAVE1_TIMEOUT_SECONDS,
    "cleanup": WAVE1_CLEANUP,
    "environment_policy": WAVE1_ENVIRONMENT_POLICY,
    "docker_cli_host_env": WAVE1_DOCKER_CLI_HOST_ENV,
    "stdin": "subprocess.DEVNULL",
}

WAVE1_STDIN = "subprocess.DEVNULL"
# Filled/verified against recaptured wave1 index; validators require exact match
# of locale/timezone/runtime/package/executable provenance independently of
# observation self-hashes.
WAVE1_EXECUTION_MANIFEST_BASE: dict[str, Any] = {'command_wrapper': ['env', '-i'],
 'effective_environment_variables': {'HOME': '/work',
                                     'LANG': 'C',
                                     'LC_ALL': 'C',
                                     'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                                     'TZ': 'UTC'},
 'executables': {'geninfo': {'availability': 'available',
                             'path': '/usr/local/bin/geninfo',
                             'sha256': 'sha256:e879e813a4d5016fbcd0f1c3b0034be14d944c435b340ca6d4956bed8e9352c8'},
                 'lcov': {'availability': 'available',
                          'path': '/usr/local/bin/lcov',
                          'sha256': 'sha256:d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252'},
                 'llvm2lcov': {'availability': 'available',
                               'path': '/usr/local/bin/llvm2lcov',
                               'sha256': 'sha256:79bc64fe17ce38989358fef49e1ca75c726f20bbd8c0552db8662c4f7d48d654'},
                 'perl2lcov': {'availability': 'available',
                               'path': '/usr/local/bin/perl2lcov',
                               'sha256': 'sha256:f8448ef0bb4befed9aadca178d4cf52a719dae5ab5ab241be1a5167e230a666b'},
                 'py2lcov': {'availability': 'available',
                             'path': '/usr/local/bin/py2lcov',
                             'sha256': 'sha256:3892e5c70aa1d891009e48f35df2e97955e8340ab1902650928c06515c8639da'},
                 'xml2lcov': {'availability': 'available',
                              'path': '/usr/local/bin/xml2lcov',
                              'sha256': 'sha256:8625a1066fc33e8c65023f64e195ed4fc27fda7d037f8df22f91d0d84414d7ae'}},
 'image': 'sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7',
 'lc_all': 'C',
 'locale': 'C',
 'package_availability': {'g++': 'available:4:12.2.0-3',
                          'gcc': 'available:4:12.2.0-3',
                          'llvm': 'not_applicable',
                          'perl': 'available:5.36.0-7+deb12u3',
                          'python3': 'available:3.11.2-1+b1'},
 'runtime_versions': {'compiler': 'gcc (Debian 12.2.0-14+deb12u1) 12.2.0',
                      'perl': 'v5.36.0',
                      'python': '3.11.2'},
 'schema_version': 1,
 'stdin': 'subprocess.DEVNULL',
 'timezone': 'UTC',
 'upstream_commit': '74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5'}

# Independent expected identity for every wave1 case. These facts are not derived
# from observation self-hashes; validators recompute stdout/stderr/file-tree from
# committed artifacts and compare against this table plus captured exit values.
WAVE1_EXPECTED_PLANNED_IDS = [
    "DIAG-NOARGS-GENINFO-001",
    "DIAG-IGNORE-ERROR-001",
    "DIAG-IGNORE-WARN-001",
    "DIAG-IGNORE-SILENT-001",
    "DIAG-KEEP-GOING-001",
    "DIAG-IGNORE-UNKNOWN-001",
    "DIAG-IGNORE-PRECEDENCE-001",
    "DIAG-WARNING-PROMOTE-001",
    "DIAG-MAX-MESSAGES-001",
    "DIAG-EXPECTED-COUNT-FILE-001",
    "DIAG-EXPECTED-COUNT-MANUAL-FILE-001",
    "DIAG-EXPECTED-COUNT-MANUAL-RC-001",
    "DIAG-MESSAGE-LOG-001",
    "DIAG-PERL2LCOV-KEEP-001",
    "DIAG-LLVM2LCOV-KEEP-001",
    "DIAG-PY2LCOV-KEEP-001",
    "DIAG-XML2LCOV-KEEP-001",
    "DIAG-CONVERTER-KEEP-BOUNDARY-001",
    "PAR-SERIAL-PARITY-001",
]

WAVE1_EXPECTED_CASES: list[dict[str, Any]] = [
    {
        "id": "diag-noargs-geninfo-writable",
        "kind": "startup_boundary",
        "planned_case_ids": ["DIAG-NOARGS-GENINFO-001"],
        "argv": ["geninfo"],
        "fixtures": [],
        "expected_exit": 255,
        "timed_out": False,
    },
    {
        "id": "diag-ignore0-format-da",
        "kind": "named_error_fatal",
        "planned_case_ids": ["DIAG-IGNORE-ERROR-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "expected_exit": 1,
        "timed_out": False,
    },
    {
        "id": "diag-ignore1-format-da",
        "kind": "named_error_ignore_one",
        "planned_case_ids": ["DIAG-IGNORE-WARN-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-ignore2-format-da",
        "kind": "named_error_ignore_two",
        "planned_case_ids": ["DIAG-IGNORE-SILENT-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-keep-going-format-da",
        "kind": "keep_going_control",
        "planned_case_ids": ["DIAG-KEEP-GOING-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--keep-going",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "expected_exit": 1,
        "timed_out": False,
    },
    {
        "id": "diag-ignore-unknown",
        "kind": "ignore_unknown_control",
        "planned_case_ids": ["DIAG-IGNORE-UNKNOWN-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "notaclass",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "expected_exit": 2,
        "timed_out": False,
    },
    {
        "id": "diag-ignore-precedence-cli-replaces-rc",
        "kind": "ignore_precedence_control",
        "planned_case_ids": ["DIAG-IGNORE-PRECEDENCE-001"],
        "argv": [
            "lcov",
            "--config-file",
            "ignore-format.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "negative",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info", "ignore-format.rc"],
        "expected_exit": 1,
        "timed_out": False,
    },
    {
        "id": "diag-warning0-format-sanitize",
        "kind": "warning_control",
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-warning1-format-sanitize",
        "kind": "warning_control",
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "format",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-warning2-format-sanitize",
        "kind": "warning_control",
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-promote0-format-sanitize",
        "kind": "warning_promotion_control",
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "argv": [
            "lcov",
            "--config-file",
            "promote.rc",
            "--no-function-coverage",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info", "promote.rc"],
        "expected_exit": 1,
        "timed_out": False,
    },
    {
        "id": "diag-promote1-format-sanitize",
        "kind": "warning_promotion_control",
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "argv": [
            "lcov",
            "--config-file",
            "promote.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info", "promote.rc"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-promote2-format-sanitize",
        "kind": "warning_promotion_control",
        "planned_case_ids": ["DIAG-WARNING-PROMOTE-001"],
        "argv": [
            "lcov",
            "--config-file",
            "promote.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "tn-sanitize.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["tn-sanitize.info", "promote.rc"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-max-messages-format",
        "kind": "message_suppression_control",
        "planned_case_ids": ["DIAG-MAX-MESSAGES-001"],
        "argv": [
            "lcov",
            "--config-file",
            "maxmsg.rc",
            "--no-function-coverage",
            "--keep-going",
            "--add-tracefile",
            "many-format.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["many-format.info", "maxmsg.rc"],
        "expected_exit": 1,
        "timed_out": False,
    },
    {
        "id": "diag-expected-count-file-false",
        "kind": "expected_count_control",
        "planned_case_ids": ["DIAG-EXPECTED-COUNT-FILE-001"],
        "argv": [
            "lcov",
            "--config-file",
            "expect-count-false.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info", "expect-count-false.rc"],
        "expected_exit": 2,
        "timed_out": False,
    },
    {
        "id": "diag-expected-count-file-true",
        "kind": "expected_count_control",
        "planned_case_ids": ["DIAG-EXPECTED-COUNT-FILE-001"],
        "argv": [
            "lcov",
            "--config-file",
            "expect-count-true.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info", "expect-count-true.rc"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-expected-count-manual-file",
        "kind": "expected_count_control",
        "planned_case_ids": ["DIAG-EXPECTED-COUNT-MANUAL-FILE-001"],
        "argv": [
            "lcov",
            "--config-file",
            "expect-manual.rc",
            "--no-function-coverage",
            "--ignore-errors",
            "format,format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info", "expect-manual.rc"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-expected-count-manual-rc",
        "kind": "expected_count_control",
        "planned_case_ids": ["DIAG-EXPECTED-COUNT-MANUAL-RC-001"],
        "argv": [
            "lcov",
            "--rc",
            "expect_message_count=format:0",
            "--no-function-coverage",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "expected_exit": 2,
        "timed_out": False,
    },
    {
        "id": "diag-message-log",
        "kind": "message_log_control",
        "planned_case_ids": ["DIAG-MESSAGE-LOG-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--msg-log",
            "messages.log",
            "--ignore-errors",
            "format",
            "--add-tracefile",
            "malformed-da.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["malformed-da.info"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-perl2lcov-keep",
        "kind": "converter_keep_trap",
        "planned_case_ids": ["DIAG-PERL2LCOV-KEEP-001"],
        "argv": [
            "perl2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "cover_db",
        ],
        "fixtures": ["cover_db"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-llvm2lcov-keep",
        "kind": "converter_keep_trap",
        "planned_case_ids": ["DIAG-LLVM2LCOV-KEEP-001"],
        "argv": [
            "llvm2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "llvm-keep.json",
        ],
        "fixtures": ["llvm-keep.json"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-py2lcov-keep",
        "kind": "converter_keep_trap",
        "planned_case_ids": ["DIAG-PY2LCOV-KEEP-001"],
        "argv": [
            "py2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "coverage-keep.xml",
        ],
        "fixtures": ["coverage-keep.xml"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-xml2lcov-keep",
        "kind": "converter_keep_trap",
        "planned_case_ids": ["DIAG-XML2LCOV-KEEP-001"],
        "argv": [
            "xml2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "coverage-keep.xml",
        ],
        "fixtures": ["coverage-keep.xml"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "diag-converter-keep-boundary",
        "kind": "converter_keep_trap",
        "planned_case_ids": ["DIAG-CONVERTER-KEEP-BOUNDARY-001"],
        "argv": [
            "xml2lcov",
            "--keep-going",
            "--output",
            "out.info",
            "broken-no-sources.xml",
        ],
        "fixtures": ["broken-no-sources.xml"],
        "expected_exit": 1,
        "timed_out": False,
    },
    {
        "id": "par-serial-parity-parallel1",
        "kind": "parallel_control",
        "planned_case_ids": ["PAR-SERIAL-PARITY-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--parallel",
            "1",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["a.info", "b.info"],
        "expected_exit": 0,
        "timed_out": False,
    },
    {
        "id": "par-serial-parity-parallel2",
        "kind": "parallel_control",
        "planned_case_ids": ["PAR-SERIAL-PARITY-001"],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--parallel",
            "2",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info",
        ],
        "fixtures": ["a.info", "b.info"],
        "expected_exit": 0,
        "timed_out": False,
    },
]

WAVE1_EXPECTED_CASE_BY_ID = {entry["id"]: entry for entry in WAVE1_EXPECTED_CASES}

WAVE2_ROOT = Path(__file__).with_name("wave2")
WAVE2_INDEX = WAVE2_ROOT / "result.json"
WAVE2_EXPECTED_CASE_COUNT = 32
WAVE2_PINNED_IMAGE = WAVE1_PINNED_IMAGE
WAVE2_FILE_TREE_SEMANTICS = WAVE1_FILE_TREE_SEMANTICS
WAVE2_TIMEOUT_SECONDS = WAVE1_TIMEOUT_SECONDS
WAVE2_CLEANUP = WAVE1_CLEANUP
WAVE2_BASE_EFFECTIVE_ENVIRONMENT_VARIABLES = WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES
WAVE2_DOCKER_CLI_HOST_ENV = WAVE1_DOCKER_CLI_HOST_ENV
WAVE2_STDIN = WAVE1_STDIN
WAVE2_CLEANUP_OUTCOME_TEMPLATE = WAVE1_CLEANUP_OUTCOME_TEMPLATE

WAVE2_ENVIRONMENT_POLICY_TEMPLATE = {
    "mode": "in_container_env_dash_i_clean",
    "inherits_host_environment": False,
    "command_wrapper": ["env", "-i"],
    "reviewed_exclusions": [
        "host process environment is not inherited by docker CLI or Oracle command",
        "Oracle command environment is produced by in-container env -i with only declared_variables",
        "Docker-injected variables such as HOSTNAME do not remain because env -i replaces the environment",
        "case-local env extras are still declared clean-env variables, never ambient host inheritance",
    ],
}

WAVE2_EXECUTION_ENVIRONMENT_TEMPLATE = {
    "docker_image": WAVE2_PINNED_IMAGE,
    "network": "none",
    "user": "1000:1000",
    "workdir": "/work",
    "tmpfs": ["/tmp:rw,exec,mode=1777"],
    "timeout_seconds": WAVE2_TIMEOUT_SECONDS,
    "cleanup": WAVE2_CLEANUP,
    "docker_cli_host_env": WAVE2_DOCKER_CLI_HOST_ENV,
}

WAVE2_EXECUTION_MANIFEST_BASE: dict[str, Any] = {
    "command_wrapper": [
        "env",
        "-i"
    ],
    "effective_environment_variables": {
        "HOME": "/work",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "TZ": "UTC"
    },
    "executables": {
        "gendesc": {
            "availability": "available",
            "path": "/usr/local/bin/gendesc",
            "sha256": "sha256:f47a0f6ee3a91b3cfeff72dfcfc4f8df4cdee5f570f51f1184c61e3096abd59e"
        },
        "genhtml": {
            "availability": "available",
            "path": "/usr/local/bin/genhtml",
            "sha256": "sha256:8ef84c95ce3970f6ba4743e81dd91e4dacca71266478801982179362204b2b6a"
        },
        "geninfo": {
            "availability": "available",
            "path": "/usr/local/bin/geninfo",
            "sha256": "sha256:e879e813a4d5016fbcd0f1c3b0034be14d944c435b340ca6d4956bed8e9352c8"
        },
        "genpng": {
            "availability": "available",
            "path": "/usr/local/bin/genpng",
            "sha256": "sha256:13f1fc69aabe993244cc559b26c0c9d2501ecb0ce0c8262a9b502b693d807c8c"
        },
        "lcov": {
            "availability": "available",
            "path": "/usr/local/bin/lcov",
            "sha256": "sha256:d99e675e9a076eea47b7861ccb6fa148aba08da8ed1718c002c40ec554c07252"
        },
        "llvm2lcov": {
            "availability": "available",
            "path": "/usr/local/bin/llvm2lcov",
            "sha256": "sha256:79bc64fe17ce38989358fef49e1ca75c726f20bbd8c0552db8662c4f7d48d654"
        },
        "perl": {
            "availability": "available",
            "path": "/usr/bin/perl",
            "sha256": "sha256:f01fa7776dc21c9e4b5f60b2d231ca4d96dab958b8d06aff611cb1c16f871574"
        },
        "perl2lcov": {
            "availability": "available",
            "path": "/usr/local/bin/perl2lcov",
            "sha256": "sha256:f8448ef0bb4befed9aadca178d4cf52a719dae5ab5ab241be1a5167e230a666b"
        },
        "py2lcov": {
            "availability": "available",
            "path": "/usr/local/bin/py2lcov",
            "sha256": "sha256:3892e5c70aa1d891009e48f35df2e97955e8340ab1902650928c06515c8639da"
        },
        "xml2lcov": {
            "availability": "available",
            "path": "/usr/local/bin/xml2lcov",
            "sha256": "sha256:8625a1066fc33e8c65023f64e195ed4fc27fda7d037f8df22f91d0d84414d7ae"
        }
    },
    "image": "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7",
    "lc_all": "C",
    "locale": "C",
    "package_availability": {
        "g++": "available:4:12.2.0-3",
        "gcc": "available:4:12.2.0-3",
        "llvm": "not_applicable",
        "perl": "available:5.36.0-7+deb12u3",
        "python3": "available:3.11.2-1+b1"
    },
    "runtime_versions": {
        "compiler": "gcc (Debian 12.2.0-14+deb12u1) 12.2.0",
        "perl": "v5.36.0",
        "python": "3.11.2"
    },
    "schema_version": 1,
    "stdin": "subprocess.DEVNULL",
    "timezone": "UTC",
    "upstream_commit": "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
}

WAVE2_EXPECTED_PLANNED_IDS = [
    "DIAG-REGISTRY-001",
    "DIAG-IGNORE-PREFIX-PROFILE-001",
    "DIAG-ENV-POSIX-PROFILE-001",
    "DIAG-ENV-CLEAN-001",
    "DIAG-ENV-SHOW-LOCATION-001",
    "DIAG-ENV-PRECEDENCE-001",
    "DIAG-ENV-LCOV-HOME-001",
    "DIAG-CONFIG-DISCOVERY-001",
    "DIAG-ENV-LCOV-VALIDATE-001",
    "DIAG-ENV-ALLOWLIST-001",
    "DIAG-CONFIG-EXPLICIT-001",
    "DIAG-CONFIG-INCLUDE-001",
    "DIAG-CONFIG-EARLY-ERROR-001",
    "DIAG-CONFIG-UNKNOWN-KEY-001",
    "DIAG-CONFIG-ENV-EXPAND-001",
    "DIAG-RAW-PERL-001",
    "DIAG-PYTHON-TRACEBACK-001",
    "DIAG-DEPENDENCY-GENPNG-001",
    "DIAG-CALLBACK-FINALIZE-FAIL-001",
    "DIAG-CALLBACK-CLEANUP-001",
    "PAR-CHILD-EXIT-001",
    "PAR-CALLBACK-LIFECYCLE-FAIL-001",
    "PAR-CALLBACK-STATE-001",
    "PAR-PAYLOAD-MISSING-001",
    "PAR-MSG-LOG-001",
    "PAR-MESSAGE-ORDER-001",
    "PAR-MEMORY-ADMISSION-001",
    "PAR-MEMORY-FALLBACK-001",
    "PAR-LCOV-CAPTURE-STATUS-001",
    "PAR-PARTIAL-COMMIT-001"
]

WAVE2_EXPECTED_CASES: list[dict[str, Any]] = [
    {
        "id": "diag-registry-branch-accept",
        "kind": "registry_control",
        "planned_case_ids": [
            "DIAG-REGISTRY-001"
        ],
        "argv": [
            "lcov",
            "--ignore-errors",
            "branch",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-ignore-prefix-default-lcov",
        "kind": "ignore_prefix_profile",
        "planned_case_ids": [
            "DIAG-IGNORE-PREFIX-PROFILE-001"
        ],
        "argv": [
            "lcov",
            "--ignore-error",
            "empty",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-ignore-prefix-posix-lcov",
        "kind": "ignore_prefix_profile",
        "planned_case_ids": [
            "DIAG-IGNORE-PREFIX-PROFILE-001",
            "DIAG-ENV-POSIX-PROFILE-001"
        ],
        "argv": [
            "lcov",
            "--ignore-error",
            "empty",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "POSIXLY_CORRECT": "1"
        }
    },
    {
        "id": "diag-env-posix-genhtml",
        "kind": "env_posix_profile",
        "planned_case_ids": [
            "DIAG-ENV-POSIX-PROFILE-001"
        ],
        "argv": [
            "genhtml",
            "--ignore-error",
            "empty",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "POSIXLY_CORRECT": "1"
        }
    },
    {
        "id": "diag-env-posix-geninfo",
        "kind": "env_posix_profile",
        "planned_case_ids": [
            "DIAG-ENV-POSIX-PROFILE-001"
        ],
        "argv": [
            "geninfo",
            "--ignore-error",
            "empty",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "POSIXLY_CORRECT": "1"
        }
    },
    {
        "id": "diag-env-posix-perl2lcov",
        "kind": "env_posix_profile",
        "planned_case_ids": [
            "DIAG-ENV-POSIX-PROFILE-001"
        ],
        "argv": [
            "perl2lcov",
            "--ignore-error",
            "empty",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "POSIXLY_CORRECT": "1"
        }
    },
    {
        "id": "diag-env-posix-llvm2lcov",
        "kind": "env_posix_profile",
        "planned_case_ids": [
            "DIAG-ENV-POSIX-PROFILE-001"
        ],
        "argv": [
            "llvm2lcov",
            "--ignore-error",
            "empty",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "POSIXLY_CORRECT": "1"
        }
    },
    {
        "id": "diag-env-clean-lcov-version",
        "kind": "env_clean_control",
        "planned_case_ids": [
            "DIAG-ENV-CLEAN-001"
        ],
        "argv": [
            "lcov",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-env-show-location-1",
        "kind": "env_show_location",
        "planned_case_ids": [
            "DIAG-ENV-SHOW-LOCATION-001",
            "DIAG-ENV-PRECEDENCE-001"
        ],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--add-tracefile",
            "missing.info",
            "--output-file",
            "o.info"
        ],
        "fixtures": [],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "LCOV_SHOW_LOCATION": "1"
        }
    },
    {
        "id": "diag-env-show-location-2",
        "kind": "env_show_location",
        "planned_case_ids": [
            "DIAG-ENV-SHOW-LOCATION-001"
        ],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--add-tracefile",
            "missing.info",
            "--output-file",
            "o.info"
        ],
        "fixtures": [],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "LCOV_SHOW_LOCATION": "2"
        }
    },
    {
        "id": "diag-env-lcov-home",
        "kind": "env_lcov_home",
        "planned_case_ids": [
            "DIAG-ENV-LCOV-HOME-001",
            "DIAG-CONFIG-DISCOVERY-001"
        ],
        "argv": [
            "lcov",
            "--list",
            "line-only.info"
        ],
        "fixtures": [
            "line-only.info",
            "emptyhome",
            "lcovhome"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {
            "HOME": "/work/emptyhome",
            "LCOV_HOME": "/work/lcovhome"
        }
    },
    {
        "id": "diag-env-lcov-validate-present",
        "kind": "env_lcov_validate",
        "planned_case_ids": [
            "DIAG-ENV-LCOV-VALIDATE-001",
            "DIAG-ENV-PRECEDENCE-001"
        ],
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_validate",
            "--synthesize-missing"
        ],
        "fixtures": [
            "sample.info",
            "sample.c"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {
            "LCOV_VALIDATE": "1"
        }
    },
    {
        "id": "diag-env-allowlist-posixly",
        "kind": "env_allowlist",
        "planned_case_ids": [
            "DIAG-ENV-ALLOWLIST-001"
        ],
        "argv": [
            "lcov",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 0,
        "timed_out": False,
        "env": {
            "POSIXLY_CORRECT": "1"
        }
    },
    {
        "id": "diag-config-discovery-home",
        "kind": "config_discovery",
        "planned_case_ids": [
            "DIAG-CONFIG-DISCOVERY-001"
        ],
        "argv": [
            "lcov",
            "--list",
            "line-only.info"
        ],
        "fixtures": [
            "line-only.info",
            "home"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {
            "HOME": "/work/home"
        }
    },
    {
        "id": "diag-config-explicit",
        "kind": "config_explicit",
        "planned_case_ids": [
            "DIAG-CONFIG-EXPLICIT-001"
        ],
        "argv": [
            "lcov",
            "--config-file",
            "explicit.rc",
            "--list",
            "line-only.info"
        ],
        "fixtures": [
            "line-only.info",
            "explicit.rc"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-config-include",
        "kind": "config_include",
        "planned_case_ids": [
            "DIAG-CONFIG-INCLUDE-001"
        ],
        "argv": [
            "lcov",
            "--config-file",
            "outer.rc",
            "--no-function-coverage",
            "--add-tracefile",
            "line-only.info",
            "--output-file",
            "out.info"
        ],
        "fixtures": [
            "line-only.info",
            "outer.rc",
            "nested.rc"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-config-include-loop",
        "kind": "config_early_error",
        "planned_case_ids": [
            "DIAG-CONFIG-INCLUDE-001",
            "DIAG-CONFIG-EARLY-ERROR-001"
        ],
        "argv": [
            "lcov",
            "--config-file",
            "loop.rc",
            "--list",
            "line-only.info"
        ],
        "fixtures": [
            "line-only.info",
            "loop.rc"
        ],
        "expected_exit": 25,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-config-unknown-key-file",
        "kind": "config_unknown_key",
        "planned_case_ids": [
            "DIAG-CONFIG-UNKNOWN-KEY-001"
        ],
        "argv": [
            "lcov",
            "--config-file",
            "unknown-key.rc",
            "--list",
            "line-only.info"
        ],
        "fixtures": [
            "line-only.info",
            "unknown-key.rc"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-config-env-expand-missing",
        "kind": "config_env_expand",
        "planned_case_ids": [
            "DIAG-CONFIG-ENV-EXPAND-001"
        ],
        "argv": [
            "lcov",
            "--config-file",
            "env-missing.rc",
            "--list",
            "line-only.info"
        ],
        "fixtures": [
            "line-only.info",
            "env-missing.rc"
        ],
        "expected_exit": 255,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-config-early-unreadable",
        "kind": "config_early_error",
        "planned_case_ids": [
            "DIAG-CONFIG-EARLY-ERROR-001"
        ],
        "argv": [
            "lcov",
            "--config-file",
            "noread.rc",
            "--list",
            "line-only.info"
        ],
        "fixtures": [
            "line-only.info",
            "noread.rc"
        ],
        "expected_exit": 13,
        "timed_out": False,
        "env": {},
        "chmod": {
            "noread.rc": 0
        }
    },
    {
        "id": "diag-raw-perl-die",
        "kind": "raw_perl_boundary",
        "planned_case_ids": [
            "DIAG-RAW-PERL-001"
        ],
        "argv": [
            "perl",
            "-e",
            "use lib '/usr/local/lib/lcov'; require lcovutil; die 'raw-perl-boundary';"
        ],
        "fixtures": [],
        "expected_exit": 255,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-python-traceback",
        "kind": "python_traceback_boundary",
        "planned_case_ids": [
            "DIAG-PYTHON-TRACEBACK-001"
        ],
        "argv": [
            "py2lcov",
            "--output",
            "out.info",
            "bad.xml"
        ],
        "fixtures": [
            "bad.xml"
        ],
        "expected_exit": 1,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-dependency-genpng-present",
        "kind": "dependency_genpng",
        "planned_case_ids": [
            "DIAG-DEPENDENCY-GENPNG-001"
        ],
        "argv": [
            "genpng",
            "--version"
        ],
        "fixtures": [],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-callback-finalize-fail",
        "kind": "callback_finalize",
        "planned_case_ids": [
            "DIAG-CALLBACK-FINALIZE-FAIL-001"
        ],
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_finalize",
            "--simplify-script",
            "./parallelFail.pm,start,save,restore",
            "--synthesize-missing"
        ],
        "fixtures": [
            "sample.info",
            "sample.c",
            "parallelFail.pm"
        ],
        "expected_exit": 25,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "diag-callback-cleanup-missing-restore",
        "kind": "callback_cleanup",
        "planned_case_ids": [
            "DIAG-CALLBACK-CLEANUP-001"
        ],
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_cleanup",
            "--simplify-script",
            "./missingRestore.pm",
            "--synthesize-missing",
            "--parallel",
            "2"
        ],
        "fixtures": [
            "sample.info",
            "sample.c",
            "missingRestore.pm"
        ],
        "expected_exit": 255,
        "timed_out": False,
        "env": {
            "LCOV_FORCE_PARALLEL": "1"
        }
    },
    {
        "id": "par-child-exit-callback-start",
        "kind": "parallel_child_exit",
        "planned_case_ids": [
            "PAR-CHILD-EXIT-001",
            "PAR-CALLBACK-LIFECYCLE-FAIL-001"
        ],
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_child",
            "--simplify-script",
            "./parallelFail.pm",
            "--synthesize-missing",
            "--parallel",
            "2"
        ],
        "fixtures": [
            "sample.info",
            "sample.c",
            "parallelFail.pm"
        ],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "LCOV_FORCE_PARALLEL": "1"
        }
    },
    {
        "id": "par-callback-state-save-fail",
        "kind": "parallel_callback_state",
        "planned_case_ids": [
            "PAR-CALLBACK-STATE-001",
            "PAR-CALLBACK-LIFECYCLE-FAIL-001",
            "PAR-PAYLOAD-MISSING-001"
        ],
        "argv": [
            "genhtml",
            "sample.info",
            "-o",
            "out_save",
            "--simplify-script",
            "./parallelFail.pm,start",
            "--synthesize-missing",
            "--parallel",
            "2"
        ],
        "fixtures": [
            "sample.info",
            "sample.c",
            "parallelFail.pm"
        ],
        "expected_exit": 1,
        "timed_out": False,
        "env": {
            "LCOV_FORCE_PARALLEL": "1"
        }
    },
    {
        "id": "par-msg-log-parallel",
        "kind": "parallel_message_log",
        "planned_case_ids": [
            "PAR-MSG-LOG-001",
            "PAR-MESSAGE-ORDER-001"
        ],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--parallel",
            "2",
            "--msg-log",
            "messages.log",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info"
        ],
        "fixtures": [
            "a.info",
            "b.info"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "par-memory-admission-package",
        "kind": "parallel_memory",
        "planned_case_ids": [
            "PAR-MEMORY-ADMISSION-001",
            "PAR-MEMORY-FALLBACK-001"
        ],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--memory",
            "1",
            "--parallel",
            "2",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info"
        ],
        "fixtures": [
            "a.info",
            "b.info"
        ],
        "expected_exit": 255,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "par-memory-fallback-ignore-package",
        "kind": "parallel_memory",
        "planned_case_ids": [
            "PAR-MEMORY-FALLBACK-001"
        ],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--memory",
            "1",
            "--parallel",
            "2",
            "--ignore-errors",
            "package",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info"
        ],
        "fixtures": [
            "a.info",
            "b.info"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "par-lcov-capture-status",
        "kind": "parallel_capture_status",
        "planned_case_ids": [
            "PAR-LCOV-CAPTURE-STATUS-001"
        ],
        "argv": [
            "lcov",
            "--capture",
            "--directory",
            "/work/no-such-dir",
            "--output-file",
            "cap.info"
        ],
        "fixtures": [],
        "expected_exit": 9,
        "timed_out": False,
        "env": {}
    },
    {
        "id": "par-partial-commit-control",
        "kind": "parallel_partial_commit",
        "planned_case_ids": [
            "PAR-PARTIAL-COMMIT-001"
        ],
        "argv": [
            "lcov",
            "--no-function-coverage",
            "--parallel",
            "2",
            "--add-tracefile",
            "a.info",
            "--add-tracefile",
            "b.info",
            "--output-file",
            "out.info"
        ],
        "fixtures": [
            "a.info",
            "b.info"
        ],
        "expected_exit": 0,
        "timed_out": False,
        "env": {}
    }
]

WAVE2_EXPECTED_CASE_BY_ID = {entry["id"]: entry for entry in WAVE2_EXPECTED_CASES}


EXPECTED_REGISTRY = (
    ("annotate", "ERROR_ANNOTATE_SCRIPT"),
    ("branch", "ERROR_BRANCH"),
    ("callback", "ERROR_CALLBACK"),
    ("category", "ERROR_UNKNOWN_CATEGORY"),
    ("child", "ERROR_CHILD"),
    ("corrupt", "ERROR_CORRUPT"),
    ("count", "ERROR_COUNT"),
    ("deprecated", "ERROR_DEPRECATED"),
    ("empty", "ERROR_EMPTY"),
    ("excessive", "ERROR_EXCESSIVE_COUNT"),
    ("format", "ERROR_FORMAT"),
    ("fork", "ERROR_FORK"),
    ("gcov", "ERROR_GCOV"),
    ("graph", "ERROR_GRAPH"),
    ("inconsistent", "ERROR_INCONSISTENT_DATA"),
    ("internal", "ERROR_INTERNAL"),
    ("mismatch", "ERROR_MISMATCH"),
    ("missing", "ERROR_MISSING"),
    ("negative", "ERROR_NEGATIVE"),
    ("package", "ERROR_PACKAGE"),
    ("parallel", "ERROR_PARALLEL"),
    ("parent", "ERROR_PARENT"),
    ("path", "ERROR_PATH"),
    ("range", "ERROR_RANGE"),
    ("source", "ERROR_SOURCE"),
    ("unmapped", "ERROR_UNMAPPED_LINE"),
    ("unreachable", "ERROR_UNREACHABLE"),
    ("unsupported", "ERROR_UNSUPPORTED"),
    ("unused", "ERROR_UNUSED"),
    ("usage", "ERROR_USAGE"),
    ("utility", "ERROR_UTILITY"),
    ("version", "ERROR_VERSION"),
)

STARTUP_CASES = {
    "lcov": "m0-core-lcov-startup-control",
    "genhtml": "m0-core-genhtml-startup-control",
    "geninfo": "m0-core-geninfo-startup-control",
    "genpng": "m0-core-genpng-startup-control",
    "gendesc": "m0-core-gendesc-startup-control",
    "perl2lcov": "m0-core-perl2lcov-startup-control",
    "py2lcov": "m0-core-py2lcov-startup-control",
    "xml2lcov": "m0-core-xml2lcov-startup-control",
    "xml2lcovutil.py": "m0-core-xml2lcovutil-py-startup-control",
    "llvm2lcov": "m0-core-llvm2lcov-startup-control",
}

STARTUP_PLANNED_CASES = {
    "lcov": "DIAG-NOARGS-LCOV-001",
    "genhtml": "DIAG-NOARGS-GENHTML-001",
    "genpng": "DIAG-NOARGS-GENPNG-001",
    "gendesc": "DIAG-NOARGS-GENDESC-001",
    "perl2lcov": "DIAG-NOARGS-PERL2LCOV-001",
    "py2lcov": "DIAG-NOARGS-PY2LCOV-001",
    "xml2lcov": "DIAG-NOARGS-XML2LCOV-001",
    "xml2lcovutil.py": "DIAG-NOARGS-XML2LCOVUTIL-001",
    "llvm2lcov": "DIAG-NOARGS-LLVM2LCOV-001",
}

INVALID_CASES = {
    "lcov": "m0-core-lcov-invalid-option",
    "genhtml": "m0-core-genhtml-invalid-option",
    "geninfo": "m0-core-geninfo-invalid-option",
    "genpng": "m0-core-genpng-invalid-option",
    "gendesc": "m0-core-gendesc-invalid-option",
    "perl2lcov": "m0-core-perl2lcov-invalid-option",
    "py2lcov": "m0-core-py2lcov-invalid-option",
    "xml2lcov": "m0-core-xml2lcov-invalid-option",
    "xml2lcovutil.py": "m0-core-xml2lcovutil-py-invalid-argv-ignored-control",
    "llvm2lcov": "m0-core-llvm2lcov-invalid-option",
}

CONFIG_CASES = {
    "m0-config-base-missing-env": ["DIAG-CONFIG-ENV-EXPAND-001"],
    "m0-config-base-missing-env-ignored": [
        "DIAG-CONFIG-ENV-EXPAND-001",
        "DIAG-IGNORE-WARN-001",
    ],
    "m0-config-base-missing-explicit-is-early": [
        "DIAG-CONFIG-EARLY-ERROR-001"
    ],
    "m0-config-base-include-loop": [
        "DIAG-CONFIG-INCLUDE-001",
        "DIAG-CONFIG-EARLY-ERROR-001",
    ],
    "m0-config-base-unknown-rc-key": ["DIAG-CONFIG-UNKNOWN-KEY-001"],
}


class DiagnosticsContractError(RuntimeError):
    pass


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DiagnosticsContractError(f"cannot load JSON: {path}") from error
    if not isinstance(document, dict):
        raise DiagnosticsContractError(f"expected JSON object: {path}")
    return document


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def source_reference(
    upstream_root: Path, path: str, line: int, role: str
) -> dict[str, Any]:
    try:
        text = (upstream_root / path).read_text(encoding="utf-8").splitlines()[
            line - 1
        ]
    except (OSError, IndexError) as error:
        raise DiagnosticsContractError(f"cannot read source {path}:{line}") from error
    return {"path": path, "line": line, "role": role, "text": text}


def scan_registry(upstream_root: Path) -> list[tuple[str, str, int]]:
    lines = (upstream_root / "lib/lcovutil.pm").read_text(encoding="utf-8").splitlines()
    result = []
    pattern = re.compile(r'''\[(["'])([a-z]+)\1, \\\$(ERROR_[A-Z_]+)\]''')
    for line_number, text in enumerate(lines, start=1):
        match = pattern.search(text)
        if match:
            result.append((match.group(2), match.group(3), line_number))
    return result


def scan_symbol_references(upstream_root: Path, symbol: str) -> list[str]:
    pattern = re.compile(r"\$(?:lcovutil::)?" + re.escape(symbol) + r"\b")
    result = []
    for base in ("bin", "lib", "scripts"):
        for path in sorted((upstream_root / base).rglob("*")):
            if not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, text in enumerate(lines, start=1):
                if not pattern.search(text.split("#", 1)[0]):
                    continue
                if path == upstream_root / "lib/lcovutil.pm" and (
                    text.lstrip().startswith("our $ERROR_")
                    or 169 <= line_number <= 200
                ):
                    continue
                result.append(f"{path.relative_to(upstream_root)}:{line_number}:{text}")
    return result


def registry_entries(upstream_root: Path) -> list[dict[str, Any]]:
    scanned = scan_registry(upstream_root)
    if tuple((name, symbol) for name, symbol, _ in scanned) != EXPECTED_REGISTRY:
        raise DiagnosticsContractError("diagnostic registry identity or order drift")
    result = []
    for numeric_id, (name, symbol, line) in enumerate(scanned):
        references = scan_symbol_references(upstream_root, symbol)
        canonical = ("\n".join(references) + "\n").encode("utf-8")
        result.append(
            {
                "id": f"diagnostic.category.{name}",
                "name": name,
                "upstream_symbol": symbol,
                "upstream_numeric_id": numeric_id,
                "emitter_status": (
                    "reserved_no_production_emitter" if name == "branch" else "emitted"
                ),
                "registry_source": source_reference(
                    upstream_root, "lib/lcovutil.pm", line, "registry"
                ),
                "symbol_reference_count": len(references),
                "symbol_references_sha256": sha256_bytes(canonical),
                "review_status": "reviewed",
                "product_evidence": [],
            }
        )
    return result


def control_rules(upstream_root: Path) -> list[dict[str, Any]]:
    definitions = [
        (
            "diagnostic.control.ignore-list-precedence",
            "CLI ignore values replace the complete configuration list when any CLI value is present.",
            [("lib/lcovutil.pm", 1553), ("lib/lcovutil.pm", 1575)],
        ),
        (
            "diagnostic.control.ignore-count-parse",
            "Names are comma-split, case-insensitive, rejected when unknown, and counted per occurrence.",
            [("lib/lcovutil.pm", line) for line in (1964, 1975, 1976, 1977, 1979)],
        ),
        (
            "diagnostic.control.keep-going",
            "Keep-going sets stop_on_error to zero and makes every registered class continuable without changing an unlisted error into a warning.",
            [("lib/lcovutil.pm", line) for line in (1582, 1583, 2045, 2362, 2363, 2364, 2365)],
        ),
        (
            "diagnostic.control.error-ignore-zero",
            "A registered error with ignore count zero is fatal unless keep-going is active.",
            [("lib/lcovutil.pm", line) for line in (2355, 2356, 2367, 2368)],
        ),
        (
            "diagnostic.control.error-ignore-one",
            "A registered error with ignore count one continues as a warning.",
            [("lib/lcovutil.pm", line) for line in (2377, 2379, 2380, 2381)],
        ),
        (
            "diagnostic.control.error-ignore-two-plus",
            "A registered error with ignore count two or more continues silently in the ignore summary bucket.",
            [("lib/lcovutil.pm", line) for line in (2377, 2378)],
        ),
        (
            "diagnostic.control.warning-ladder",
            "Warnings are visible at ignore zero, silent at ignore one or more, and use the complete error ladder when promotion is enabled.",
            [("lib/lcovutil.pm", line) for line in (2388, 2389, 2397, 2406, 2414, 2415, 2417)],
        ),
        (
            "diagnostic.control.message-suppression",
            "Semantic message counts continue after the configured console suppression threshold.",
            [("lib/lcovutil.pm", line) for line in (2297, 2301, 2302, 2309, 2341, 2347, 2350)],
        ),
        (
            "diagnostic.control.error-summary-exit",
            "saw_error reports the presence of the error summary bucket for command-specific final-exit folding.",
            [("lib/lcovutil.pm", line) for line in (2325, 2329)],
        ),
    ]
    return [
        {
            "id": identifier,
            "behavior": behavior,
            "source_references": [
                source_reference(upstream_root, path, line, "control")
                for path, line in references
            ],
            "review_status": "reviewed",
            "product_evidence": [],
        }
        for identifier, behavior, references in definitions
    ]


def unclassified_surfaces(upstream_root: Path) -> list[dict[str, Any]]:
    definitions = [
        (
            "diagnostic.surface.parser",
            "parser_error",
            "Getopt and argparse failures retain their native stream and status behavior.",
            [("lib/lcovutil.pm", 1518), ("bin/py2lcov", 155)],
        ),
        (
            "diagnostic.surface.raw-perl",
            "raw_perl_failure",
            "Direct die/open/assertion failures outside a named wrapper are not controlled by ignore-errors.",
            [("bin/llvm2lcov", 112), ("bin/gendesc", 94)],
        ),
        (
            "diagnostic.surface.native-python",
            "native_python_diagnostic",
            "Python converter application diagnostics are printed directly and use their own keep-going boundaries.",
            [("bin/py2lcov", 169), ("bin/py2lcov", 193), ("bin/xml2lcovutil.py", 163)],
        ),
        (
            "diagnostic.surface.early-dependency",
            "early_dependency_failure",
            "Dependency loading can fail before ordinary parser behavior is reached.",
            [("bin/genpng", 58), ("bin/genpng", 62), ("bin/genpng", 65)],
        ),
    ]
    return [
        {
            "id": identifier,
            "family": family,
            "behavior": behavior,
            "source_references": [
                source_reference(upstream_root, path, line, "surface")
                for path, line in references
            ],
            "review_status": "reviewed",
            "product_evidence": [],
        }
        for identifier, family, behavior, references in definitions
    ]


def exit_policies(upstream_root: Path) -> list[dict[str, Any]]:
    definitions = [
        ("lcov", "shared_saw_error_fold", [("bin/lcov", 469), ("bin/lcov", 472), ("bin/lcov", 474)]),
        ("geninfo", "shared_saw_error_fold", [("bin/geninfo", 610), ("bin/geninfo", 614), ("bin/geninfo", 615)]),
        ("genhtml", "shared_saw_error_fold", [("bin/genhtml", 7639), ("bin/genhtml", 7641), ("bin/genhtml", 7643)]),
        ("perl2lcov", "criteria_only_no_saw_error_fold", [("bin/perl2lcov", 438), ("bin/perl2lcov", 442), ("bin/perl2lcov", 444)]),
        ("llvm2lcov", "criteria_only_no_saw_error_fold", [("bin/llvm2lcov", 558), ("bin/llvm2lcov", 561), ("bin/llvm2lcov", 567)]),
        ("py2lcov", "native_python_keep_going", [("bin/py2lcov", 148), ("bin/py2lcov", 195), ("bin/py2lcov", 201)]),
        ("xml2lcov", "native_python_keep_going", [("bin/xml2lcov", 82), ("bin/xml2lcov", 96), ("bin/xml2lcov", 98)]),
        ("xml2lcovutil.py", "library_no_cli_entrypoint", [("bin/xml2lcovutil.py", 143)]),
        ("genpng", "direct_perl_exit", [("bin/genpng", 88), ("bin/genpng", 90), ("bin/genpng", 109)]),
        ("gendesc", "direct_perl_exit", [("bin/gendesc", 73), ("bin/gendesc", 75), ("bin/gendesc", 94)]),
    ]
    return [
        {
            "id": f"diagnostic.exit-policy.{command}",
            "command": command,
            "policy": policy,
            "source_references": [
                source_reference(upstream_root, path, line, "exit")
                for path, line in references
            ],
            "review_status": "reviewed",
            "product_evidence": [],
        }
        for command, policy, references in definitions
    ]


def planned_case_ids() -> list[str]:
    text = SPEC_PATH.read_text(encoding="utf-8")
    result = []
    for identifier in re.findall(r"`((?:DIAG|PAR)-[A-Z0-9-]+)`", text):
        if identifier not in result:
            result.append(identifier)
    return result


def artifact_bindings() -> list[dict[str, str]]:
    result = []
    for relative, expected in EXPECTED_ARTIFACT_HASHES.items():
        actual = sha256_file(ROOT / relative)
        if actual != expected:
            raise DiagnosticsContractError(
                f"retained diagnostics artifact drift: {relative} expected={expected} actual={actual}"
            )
        result.append({"path": relative, "sha256": actual})
    return result


def correctness_case(case_id: str) -> dict[str, Any]:
    path = CORRECTNESS_ROOT / "cases" / case_id / "result.json"
    document = load_json(path)
    reference = document["reference_run"]
    if document["case_id"] != case_id or document["product_compatibility_evidence"]:
        raise DiagnosticsContractError(f"invalid retained correctness case: {case_id}")
    return {
        "id": f"correctness:{case_id}",
        "exit_status": reference["exit_code"],
        "stdout_sha256": reference["stdout_sha256"],
        "stderr_sha256": reference["stderr_sha256"],
        "output_sha256": reference["file_tree_sha256"],
        "observation_sha256": sha256_file(path),
    }


def tracefile_case(case: dict[str, Any]) -> dict[str, Any]:
    output = case["output"]
    return {
        "id": f"tracefile:{case['id']}",
        "exit_status": case["exit_status"],
        "stdout_sha256": case["stdout"]["sha256"],
        "stderr_sha256": case["stderr"]["sha256"],
        "output_sha256": output.get("sha256"),
        "observation_sha256": sha256_bytes(canonical_json(case).encode("ascii")),
    }


def wave1_fixture_bindings(fixtures: list[str]) -> list[dict[str, Any]]:
    result = []
    for name in fixtures:
        src = WAVE1_ROOT / "fixtures" / name
        if not src.exists():
            raise DiagnosticsContractError(f"missing wave1 fixture: {name}")
        if src.is_dir():
            for path in sorted(src.rglob("*")):
                if not path.is_file():
                    continue
                rel = f"{name}/{path.relative_to(src).as_posix()}"
                data = path.read_bytes()
                result.append(
                    {
                        "path": rel,
                        "bytes": len(data),
                        "sha256": sha256_bytes(data),
                    }
                )
        else:
            data = src.read_bytes()
            result.append(
                {
                    "path": name,
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
    return result


def recompute_wave1_file_tree(case_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(case_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(case_dir).as_posix()
        if rel.startswith("reference/") or rel == "result.json":
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": rel,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    return entries


def file_tree_sha256(tree: list[dict[str, Any]]) -> str:
    return sha256_bytes(
        json.dumps(tree, sort_keys=True, separators=(",", ":")).encode("ascii")
    )


def wave1_case(case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    case_id = expected["id"]
    if case.get("id") != case_id:
        raise DiagnosticsContractError(f"wave1 index case id drift: {case_id}")
    case_dir = WAVE1_ROOT / "cases" / case_id
    path = case_dir / "result.json"
    document = load_json(path)

    if document.get("case_id") != case_id:
        raise DiagnosticsContractError(f"wave1 case id mismatch: {case_id}")
    if document.get("product_compatibility_evidence"):
        raise DiagnosticsContractError(f"wave1 case claims product evidence: {case_id}")
    if document.get("evidence_status") != "oracle_reference":
        raise DiagnosticsContractError(
            f"wave1 case evidence status is not oracle_reference: {case_id}"
        )
    if document.get("image") != WAVE1_PINNED_IMAGE:
        raise DiagnosticsContractError(f"wave1 case image drift: {case_id}")
    if document.get("upstream_commit") != UPSTREAM_COMMIT:
        raise DiagnosticsContractError(f"wave1 case upstream drift: {case_id}")
    if document.get("execution_environment") != WAVE1_EXECUTION_ENVIRONMENT:
        raise DiagnosticsContractError(
            f"wave1 execution environment drift: {case_id}"
        )
    if document.get("effective_environment_variables") != WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES:
        raise DiagnosticsContractError(
            f"wave1 effective environment drift: {case_id}"
        )
    if document.get("environment_policy") != WAVE1_ENVIRONMENT_POLICY:
        raise DiagnosticsContractError(
            f"wave1 environment policy drift: {case_id}"
        )
    if (
        document.get("environment_policy", {}).get("effective_environment_variables")
        != WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES
    ):
        raise DiagnosticsContractError(
            f"wave1 environment policy effective env drift: {case_id}"
        )
    if document.get("environment_policy", {}).get("command_wrapper") != ["env", "-i"]:
        raise DiagnosticsContractError(
            f"wave1 command wrapper drift: {case_id}"
        )
    if document.get("environment_policy", {}).get("inherits_host_environment") is not False:
        raise DiagnosticsContractError(
            f"wave1 host env inheritance claim drift: {case_id}"
        )
    if document.get("execution_environment", {}).get("stdin") != WAVE1_STDIN:
        raise DiagnosticsContractError(f"wave1 stdin policy drift: {case_id}")
    manifest = document.get("execution_manifest")
    if not isinstance(manifest, dict):
        raise DiagnosticsContractError(
            f"wave1 missing execution_manifest provenance: {case_id}"
        )
    if WAVE1_EXECUTION_MANIFEST_BASE is None:
        raise DiagnosticsContractError("wave1 execution_manifest base is not bound")
    expected_manifest = {
        **WAVE1_EXECUTION_MANIFEST_BASE,
        "invoked_command": expected["argv"][0],
        "invoked_executable": {
            "name": expected["argv"][0],
            "path": WAVE1_EXECUTION_MANIFEST_BASE["executables"][expected["argv"][0]][
                "path"
            ],
            "sha256": WAVE1_EXECUTION_MANIFEST_BASE["executables"][expected["argv"][0]][
                "sha256"
            ],
        },
        "invoked_argv": list(expected["argv"]),
    }
    if manifest != expected_manifest:
        raise DiagnosticsContractError(
            f"wave1 execution_manifest provenance drift: {case_id}"
        )
    if case.get("execution_manifest") != expected_manifest:
        raise DiagnosticsContractError(
            f"wave1 index execution_manifest drift: {case_id}"
        )
    if case.get("stdin") != WAVE1_STDIN:
        raise DiagnosticsContractError(f"wave1 index stdin drift: {case_id}")
    if document.get("timeout_seconds") != WAVE1_TIMEOUT_SECONDS:
        raise DiagnosticsContractError(f"wave1 timeout drift: {case_id}")
    if document.get("cleanup") != WAVE1_CLEANUP:
        raise DiagnosticsContractError(f"wave1 cleanup policy drift: {case_id}")
    expected_cleanup = {
        **WAVE1_CLEANUP_OUTCOME_TEMPLATE,
        "container_name": f"ferricov-diag-wave1-{case_id}",
    }
    if document.get("cleanup_outcome") != expected_cleanup:
        raise DiagnosticsContractError(
            f"wave1 cleanup outcome drift: {case_id}"
        )
    if not document.get("cleanup_outcome", {}).get("direct_child_reaped"):
        raise DiagnosticsContractError(
            f"wave1 cleanup missing direct_child_reaped: {case_id}"
        )
    if document.get("cleanup_outcome", {}).get("container_absent") is not True:
        raise DiagnosticsContractError(
            f"wave1 cleanup missing container_absent: {case_id}"
        )
    if document.get("cleanup_outcome", {}).get("process_group_empty") is not None:
        raise DiagnosticsContractError(
            f"wave1 cleanup invalid process_group claim: {case_id}"
        )
    if document.get("file_tree_semantics") != WAVE1_FILE_TREE_SEMANTICS:
        raise DiagnosticsContractError(
            f"wave1 file-tree semantics drift: {case_id}"
        )
    if document.get("timed_out") is not False:
        raise DiagnosticsContractError(f"wave1 timed_out claim drift: {case_id}")
    if document.get("kind") != expected["kind"] or case.get("kind") != expected["kind"]:
        raise DiagnosticsContractError(f"wave1 kind drift: {case_id}")
    if (
        document.get("planned_case_ids") != expected["planned_case_ids"]
        or case.get("planned_case_ids") != expected["planned_case_ids"]
    ):
        raise DiagnosticsContractError(f"wave1 planned-case binding drift: {case_id}")
    if document.get("argv") != expected["argv"] or case.get("argv") != expected["argv"]:
        raise DiagnosticsContractError(f"wave1 argv drift: {case_id}")
    if (
        document.get("fixtures") != expected["fixtures"]
        or case.get("fixtures") != expected["fixtures"]
    ):
        raise DiagnosticsContractError(f"wave1 fixture list drift: {case_id}")
    if document.get("command") != expected["argv"][0]:
        raise DiagnosticsContractError(f"wave1 command drift: {case_id}")
    if document.get("exit_status") != expected["expected_exit"]:
        raise DiagnosticsContractError(f"wave1 expected exit drift: {case_id}")
    if case.get("exit_status") != expected["expected_exit"]:
        raise DiagnosticsContractError(f"wave1 index exit drift: {case_id}")

    stdout_path = case_dir / "reference" / "stdout.bin"
    stderr_path = case_dir / "reference" / "stderr.bin"
    if not stdout_path.is_file() or not stderr_path.is_file():
        raise DiagnosticsContractError(f"wave1 missing raw stream artifacts: {case_id}")
    stdout = stdout_path.read_bytes()
    stderr = stderr_path.read_bytes()
    stdout_hash = sha256_bytes(stdout)
    stderr_hash = sha256_bytes(stderr)
    if document.get("stdout_sha256") != stdout_hash or case.get("stdout_sha256") != stdout_hash:
        raise DiagnosticsContractError(f"wave1 stdout hash drift: {case_id}")
    if document.get("stderr_sha256") != stderr_hash or case.get("stderr_sha256") != stderr_hash:
        raise DiagnosticsContractError(f"wave1 stderr hash drift: {case_id}")
    if document.get("stdout_bytes") != len(stdout):
        raise DiagnosticsContractError(f"wave1 stdout byte-count drift: {case_id}")
    if document.get("stderr_bytes") != len(stderr):
        raise DiagnosticsContractError(f"wave1 stderr byte-count drift: {case_id}")

    expected_fixtures = wave1_fixture_bindings(expected["fixtures"])
    if document.get("fixture_bindings") != expected_fixtures:
        raise DiagnosticsContractError(f"wave1 fixture binding drift: {case_id}")

    recomputed_tree = recompute_wave1_file_tree(case_dir)
    recomputed_tree_hash = file_tree_sha256(recomputed_tree)
    if document.get("file_tree") != recomputed_tree:
        raise DiagnosticsContractError(f"wave1 file-tree content drift: {case_id}")
    if (
        document.get("file_tree_sha256") != recomputed_tree_hash
        or case.get("file_tree_sha256") != recomputed_tree_hash
    ):
        raise DiagnosticsContractError(f"wave1 file-tree hash drift: {case_id}")

    observation_hash = sha256_file(path)
    if case.get("observation_sha256") != observation_hash:
        raise DiagnosticsContractError(f"wave1 observation hash drift: {case_id}")

    return {
        "id": f"diagnostics-wave1:{case_id}",
        "kind": expected["kind"],
        "planned_case_ids": list(expected["planned_case_ids"]),
        "argv": list(expected["argv"]),
        "fixtures": list(expected["fixtures"]),
        "image": WAVE1_PINNED_IMAGE,
        "upstream_commit": UPSTREAM_COMMIT,
        "timeout_seconds": WAVE1_TIMEOUT_SECONDS,
        "timed_out": False,
        "cleanup": WAVE1_CLEANUP,
        "cleanup_outcome": {
            **WAVE1_CLEANUP_OUTCOME_TEMPLATE,
            "container_name": f"ferricov-diag-wave1-{case_id}",
        },
        "effective_environment_variables": dict(
            WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES
        ),
        "environment_policy": WAVE1_ENVIRONMENT_POLICY,
        "stdin": WAVE1_STDIN,
        "execution_manifest": {
            **WAVE1_EXECUTION_MANIFEST_BASE,
            "invoked_command": expected["argv"][0],
            "invoked_executable": {
                "name": expected["argv"][0],
                "path": WAVE1_EXECUTION_MANIFEST_BASE["executables"][
                    expected["argv"][0]
                ]["path"],
                "sha256": WAVE1_EXECUTION_MANIFEST_BASE["executables"][
                    expected["argv"][0]
                ]["sha256"],
            },
            "invoked_argv": list(expected["argv"]),
        },
        "file_tree_semantics": WAVE1_FILE_TREE_SEMANTICS,
        "exit_status": expected["expected_exit"],
        "stdout_sha256": stdout_hash,
        "stderr_sha256": stderr_hash,
        "output_sha256": recomputed_tree_hash,
        "observation_sha256": observation_hash,
    }


def wave1_observations() -> list[dict[str, Any]]:
    index = load_json(WAVE1_INDEX)
    if index.get("product_compatibility_evidence"):
        raise DiagnosticsContractError("wave1 index claims product compatibility")
    if index.get("evidence_status") != "oracle_reference":
        raise DiagnosticsContractError("wave1 index evidence status drift")
    if index.get("upstream_commit") != UPSTREAM_COMMIT:
        raise DiagnosticsContractError("wave1 upstream commit drift")
    if index.get("image") != WAVE1_PINNED_IMAGE:
        raise DiagnosticsContractError("wave1 image identity drift")
    if index.get("file_tree_semantics") != WAVE1_FILE_TREE_SEMANTICS:
        raise DiagnosticsContractError("wave1 index file-tree semantics drift")
    if index.get("timeout_seconds") != WAVE1_TIMEOUT_SECONDS:
        raise DiagnosticsContractError("wave1 index timeout drift")
    if index.get("execution_environment") != WAVE1_EXECUTION_ENVIRONMENT:
        raise DiagnosticsContractError("wave1 index execution environment drift")
    if index.get("effective_environment_variables") != WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES:
        raise DiagnosticsContractError("wave1 index effective environment drift")
    if index.get("environment_policy") != WAVE1_ENVIRONMENT_POLICY:
        raise DiagnosticsContractError("wave1 index environment policy drift")
    if index.get("cleanup") != WAVE1_CLEANUP:
        raise DiagnosticsContractError("wave1 index cleanup policy drift")
    if index.get("stdin") != WAVE1_STDIN:
        raise DiagnosticsContractError("wave1 index stdin policy drift")
    if index.get("execution_manifest") != WAVE1_EXECUTION_MANIFEST_BASE:
        raise DiagnosticsContractError("wave1 index execution_manifest drift")
    if index.get("case_count") != WAVE1_EXPECTED_CASE_COUNT:
        raise DiagnosticsContractError("wave1 case count drift")
    if len(index.get("cases", [])) != WAVE1_EXPECTED_CASE_COUNT:
        raise DiagnosticsContractError("wave1 case list length drift")

    expected_ids = [entry["id"] for entry in WAVE1_EXPECTED_CASES]
    actual_ids = [case["id"] for case in index["cases"]]
    if actual_ids != expected_ids:
        raise DiagnosticsContractError("wave1 case id set/order drift")

    planned_seen: list[str] = []
    for case, expected in zip(index["cases"], WAVE1_EXPECTED_CASES):
        for planned_id in expected["planned_case_ids"]:
            if planned_id not in planned_seen:
                planned_seen.append(planned_id)
    if planned_seen != WAVE1_EXPECTED_PLANNED_IDS:
        raise DiagnosticsContractError("wave1 planned-id coverage set drift")
    if set(planned_seen) != set(WAVE1_EXPECTED_PLANNED_IDS):
        raise DiagnosticsContractError("wave1 planned-id coverage incomplete")

    result = []
    for case, expected in zip(index["cases"], WAVE1_EXPECTED_CASES):
        result.append(wave1_case(case, expected))
    return result




WAVE2_EMPTYHOME_FIXTURE = "emptyhome"
WAVE2_EMPTYHOME_MARKER_NAME = ".gitkeep"
WAVE2_DIRECTORY_MARKER_NAMES = {WAVE2_EMPTYHOME_MARKER_NAME, ".keep"}


def skip_wave2_emptyhome_marker(
    path: Path,
    *,
    root: Path,
    context: str,
) -> bool:
    """Return True only for a regular zero-byte emptyhome/.gitkeep under root.

    Must be consulted for every path before is_file() filtering so symlink and
    broken-symlink markers cannot bypass validation. Fail closed for:
    - any symlink marker (including broken)
    - nonzero marker content
    - `.keep`
    - markers outside emptyhome
    """
    if path.name not in WAVE2_DIRECTORY_MARKER_NAMES:
        return False
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise DiagnosticsContractError(
            f"wave2 directory marker outside scan root ({context}): {path}"
        ) from exc
    allowed_rel = f"{WAVE2_EMPTYHOME_FIXTURE}/{WAVE2_EMPTYHOME_MARKER_NAME}"
    # When root is the emptyhome fixture directory itself, relative path is .gitkeep.
    if root.name == WAVE2_EMPTYHOME_FIXTURE:
        allowed_here = rel == WAVE2_EMPTYHOME_MARKER_NAME
    else:
        allowed_here = rel == allowed_rel
    if path.name == ".keep" or not allowed_here:
        raise DiagnosticsContractError(
            "wave2 directory marker only allowed as zero-byte "
            f"emptyhome/.gitkeep ({context}): {rel}"
        )
    if path.is_symlink():
        raise DiagnosticsContractError(
            f"wave2 emptyhome/.gitkeep must not be a symlink ({context}): {rel}"
        )
    if not path.is_file():
        raise DiagnosticsContractError(
            "wave2 emptyhome/.gitkeep must be a regular zero-byte file "
            f"({context}): {rel}"
        )
    data = path.read_bytes()
    if data != b"":
        raise DiagnosticsContractError(
            f"wave2 emptyhome/.gitkeep must be zero bytes ({context}): {rel}"
        )
    return True


def validate_wave2_emptyhome_fixture_dir(src: Path, *, context: str) -> None:
    """Require trackable emptyhome fixture: only zero-byte regular .gitkeep."""
    if not src.is_dir():
        raise DiagnosticsContractError(
            f"wave2 emptyhome fixture missing directory ({context}): {src}"
        )
    marker = src / WAVE2_EMPTYHOME_MARKER_NAME
    # Explicitly validate marker path even if only a broken symlink exists.
    if marker.exists(follow_symlinks=False) or marker.is_symlink():
        skip_wave2_emptyhome_marker(marker, root=src, context=context)
    else:
        raise DiagnosticsContractError(
            f"wave2 emptyhome fixture missing .gitkeep ({context})"
        )
    # Reject any extra dirents besides the exact zero-byte .gitkeep marker.
    extras = [p for p in src.iterdir() if p.name != WAVE2_EMPTYHOME_MARKER_NAME]
    if extras:
        raise DiagnosticsContractError(
            "wave2 emptyhome fixture must contain only .gitkeep "
            f"({context}): {[p.name for p in extras]}"
        )


def stage_wave2_fixtures(
    work: Path,
    fixtures: list[str],
    chmod_map: dict[str, int] | None = None,
    *,
    fixtures_root: Path | None = None,
) -> None:
    """Stage fixtures for wave2 execution.

    emptyhome is Git-tracked via zero-byte .gitkeep, but the staged runtime HOME
    directory must be truly empty: validate the source marker, copy the dir,
    then remove the marker from the staged tree.
    """
    root = fixtures_root if fixtures_root is not None else WAVE2_ROOT / "fixtures"
    work.mkdir(parents=True, exist_ok=True)
    for name in fixtures:
        src = root / name
        if not src.exists():
            raise DiagnosticsContractError(f"missing wave2 fixture: {name}")
        dest = work / name
        if name == WAVE2_EMPTYHOME_FIXTURE:
            validate_wave2_emptyhome_fixture_dir(
                src, context=f"stage-source:{work.name}"
            )
            if dest.exists():
                raise DiagnosticsContractError(
                    f"wave2 stage destination exists: {dest}"
                )
            dest.mkdir(parents=True)
            # Intentionally do not copy .gitkeep into runtime HOME.
            if any(dest.iterdir()):
                raise DiagnosticsContractError(
                    f"wave2 staged emptyhome is not empty: {dest}"
                )
            continue
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
    if chmod_map:
        for rel, mode in chmod_map.items():
            path = work / rel
            if not path.exists():
                path.write_bytes(b"")
            path.chmod(mode)


def merge_wave2_env(extra: dict[str, str] | None) -> dict[str, str]:
    env = dict(WAVE2_BASE_EFFECTIVE_ENVIRONMENT_VARIABLES)
    if extra:
        env.update(extra)
    return env


def wave2_fixture_bindings(fixtures: list[str]) -> list[dict[str, Any]]:
    result = []
    for name in fixtures:
        src = WAVE2_ROOT / "fixtures" / name
        if not src.exists():
            raise DiagnosticsContractError(f"missing wave2 fixture: {name}")
        if src.is_dir():
            # Empty directories are retained in Git via emptyhome/.gitkeep only.
            if name == WAVE2_EMPTYHOME_FIXTURE:
                validate_wave2_emptyhome_fixture_dir(
                    src, context=f"fixture:{name}"
                )
            for path in sorted(src.rglob("*")):
                if skip_wave2_emptyhome_marker(
                    path, root=src, context=f"fixture:{name}"
                ):
                    continue
                if not path.is_file():
                    continue
                rel = f"{name}/{path.relative_to(src).as_posix()}"
                data = path.read_bytes()
                result.append(
                    {
                        "path": rel,
                        "bytes": len(data),
                        "sha256": sha256_bytes(data),
                    }
                )
        else:
            data = src.read_bytes()
            result.append(
                {
                    "path": name,
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
    return result


def recompute_wave2_file_tree(
    case_dir: Path,
    chmod_map: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Rebuild retained non-reference file tree.

    Git only preserves the executable bit, so intentional unreadable capture
    fixtures (mode 0o000) are re-applied from the expected case table before
    hashing. Modes are restored afterward so the working tree is unchanged.
    """
    applied: list[tuple[Path, int]] = []
    if chmod_map:
        for rel, mode in chmod_map.items():
            path = case_dir / rel
            if not path.exists():
                raise DiagnosticsContractError(
                    f"wave2 chmod target missing: {case_dir.name}:{rel}"
                )
            previous = path.stat().st_mode & 0o777
            # Ensure we can read current mode bits before tightening permissions.
            if previous == 0:
                path.chmod(0o600)
                previous = path.stat().st_mode & 0o777
            path.chmod(mode)
            applied.append((path, previous))
    try:
        entries = []
        for path in sorted(case_dir.rglob("*")):
            if skip_wave2_emptyhome_marker(
                path, root=case_dir, context=f"case:{case_dir.name}"
            ):
                continue
            if not path.is_file():
                continue
            rel = path.relative_to(case_dir).as_posix()
            if rel.startswith("reference/") or rel == "result.json":
                continue
            try:
                data = path.read_bytes()
            except PermissionError:
                entries.append(
                    {
                        "path": rel,
                        "bytes": None,
                        "sha256": None,
                        "unreadable": True,
                        "mode": oct(path.stat().st_mode & 0o777),
                    }
                )
                continue
            entries.append(
                {
                    "path": rel,
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
        return entries
    finally:
        for path, previous in reversed(applied):
            path.chmod(previous)


def wave2_case(case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    case_id = expected["id"]
    if case.get("id") != case_id:
        raise DiagnosticsContractError(f"wave2 index case id drift: {case_id}")
    case_dir = WAVE2_ROOT / "cases" / case_id
    path = case_dir / "result.json"
    document = load_json(path)

    if document.get("case_id") != case_id:
        raise DiagnosticsContractError(f"wave2 case id mismatch: {case_id}")
    if document.get("product_compatibility_evidence"):
        raise DiagnosticsContractError(f"wave2 case claims product evidence: {case_id}")
    if document.get("evidence_status") != "oracle_reference":
        raise DiagnosticsContractError(
            f"wave2 case evidence status is not oracle_reference: {case_id}"
        )
    if document.get("image") != WAVE2_PINNED_IMAGE:
        raise DiagnosticsContractError(f"wave2 case image drift: {case_id}")
    if document.get("upstream_commit") != UPSTREAM_COMMIT:
        raise DiagnosticsContractError(f"wave2 case upstream drift: {case_id}")

    case_env = merge_wave2_env(expected.get("env"))
    environment_policy = {
        **WAVE2_ENVIRONMENT_POLICY_TEMPLATE,
        "declared_variables": dict(case_env),
        "effective_environment_variables": dict(case_env),
    }
    execution_environment = {
        **WAVE2_EXECUTION_ENVIRONMENT_TEMPLATE,
        "env": dict(case_env),
        "environment_policy": environment_policy,
        "stdin": WAVE2_STDIN,
    }
    if document.get("execution_environment") != execution_environment:
        raise DiagnosticsContractError(
            f"wave2 execution environment drift: {case_id}"
        )
    if document.get("effective_environment_variables") != case_env:
        raise DiagnosticsContractError(
            f"wave2 effective environment drift: {case_id}"
        )
    if document.get("environment_policy") != environment_policy:
        raise DiagnosticsContractError(
            f"wave2 environment policy drift: {case_id}"
        )
    if document.get("execution_environment", {}).get("stdin") != WAVE2_STDIN:
        raise DiagnosticsContractError(f"wave2 stdin policy drift: {case_id}")

    command = expected["argv"][0]
    expected_manifest = {
        **WAVE2_EXECUTION_MANIFEST_BASE,
        "effective_environment_variables": dict(case_env),
        "invoked_command": command,
        "invoked_executable": {
            "name": command,
            "path": WAVE2_EXECUTION_MANIFEST_BASE["executables"][command]["path"],
            "sha256": WAVE2_EXECUTION_MANIFEST_BASE["executables"][command]["sha256"],
        },
        "invoked_argv": list(expected["argv"]),
    }
    manifest = document.get("execution_manifest")
    if not isinstance(manifest, dict):
        raise DiagnosticsContractError(
            f"wave2 missing execution_manifest provenance: {case_id}"
        )
    if manifest != expected_manifest:
        raise DiagnosticsContractError(
            f"wave2 execution_manifest provenance drift: {case_id}"
        )
    if case.get("execution_manifest") != expected_manifest:
        raise DiagnosticsContractError(
            f"wave2 index execution_manifest drift: {case_id}"
        )
    if case.get("stdin") != WAVE2_STDIN:
        raise DiagnosticsContractError(f"wave2 index stdin drift: {case_id}")
    if document.get("timeout_seconds") != WAVE2_TIMEOUT_SECONDS:
        raise DiagnosticsContractError(f"wave2 timeout drift: {case_id}")
    if document.get("cleanup") != WAVE2_CLEANUP:
        raise DiagnosticsContractError(f"wave2 cleanup policy drift: {case_id}")
    expected_cleanup = {
        **WAVE2_CLEANUP_OUTCOME_TEMPLATE,
        "container_name": f"ferricov-diag-wave2-{case_id}",
    }
    if document.get("cleanup_outcome") != expected_cleanup:
        raise DiagnosticsContractError(
            f"wave2 cleanup outcome drift: {case_id}"
        )
    if not document.get("cleanup_outcome", {}).get("direct_child_reaped"):
        raise DiagnosticsContractError(
            f"wave2 cleanup missing direct_child_reaped: {case_id}"
        )
    if document.get("cleanup_outcome", {}).get("container_absent") is not True:
        raise DiagnosticsContractError(
            f"wave2 cleanup missing container_absent: {case_id}"
        )
    if document.get("cleanup_outcome", {}).get("process_group_empty") is not None:
        raise DiagnosticsContractError(
            f"wave2 cleanup invalid process_group claim: {case_id}"
        )
    if document.get("file_tree_semantics") != WAVE2_FILE_TREE_SEMANTICS:
        raise DiagnosticsContractError(
            f"wave2 file-tree semantics drift: {case_id}"
        )
    if document.get("timed_out") is not False:
        raise DiagnosticsContractError(f"wave2 timed_out claim drift: {case_id}")
    if document.get("kind") != expected["kind"] or case.get("kind") != expected["kind"]:
        raise DiagnosticsContractError(f"wave2 kind drift: {case_id}")
    if (
        document.get("planned_case_ids") != expected["planned_case_ids"]
        or case.get("planned_case_ids") != expected["planned_case_ids"]
    ):
        raise DiagnosticsContractError(f"wave2 planned-case binding drift: {case_id}")
    if document.get("argv") != expected["argv"] or case.get("argv") != expected["argv"]:
        raise DiagnosticsContractError(f"wave2 argv drift: {case_id}")
    if (
        document.get("fixtures") != expected["fixtures"]
        or case.get("fixtures") != expected["fixtures"]
    ):
        raise DiagnosticsContractError(f"wave2 fixture list drift: {case_id}")
    if document.get("command") != expected["argv"][0]:
        raise DiagnosticsContractError(f"wave2 command drift: {case_id}")
    if document.get("exit_status") != expected["expected_exit"]:
        raise DiagnosticsContractError(f"wave2 expected exit drift: {case_id}")
    if case.get("exit_status") != expected["expected_exit"]:
        raise DiagnosticsContractError(f"wave2 index exit drift: {case_id}")

    stdout_path = case_dir / "reference" / "stdout.bin"
    stderr_path = case_dir / "reference" / "stderr.bin"
    if not stdout_path.is_file() or not stderr_path.is_file():
        raise DiagnosticsContractError(f"wave2 missing raw stream artifacts: {case_id}")
    stdout = stdout_path.read_bytes()
    stderr = stderr_path.read_bytes()
    stdout_hash = sha256_bytes(stdout)
    stderr_hash = sha256_bytes(stderr)
    if document.get("stdout_sha256") != stdout_hash or case.get("stdout_sha256") != stdout_hash:
        raise DiagnosticsContractError(f"wave2 stdout hash drift: {case_id}")
    if document.get("stderr_sha256") != stderr_hash or case.get("stderr_sha256") != stderr_hash:
        raise DiagnosticsContractError(f"wave2 stderr hash drift: {case_id}")
    if document.get("stdout_bytes") != len(stdout):
        raise DiagnosticsContractError(f"wave2 stdout byte-count drift: {case_id}")
    if document.get("stderr_bytes") != len(stderr):
        raise DiagnosticsContractError(f"wave2 stderr byte-count drift: {case_id}")

    expected_fixtures = wave2_fixture_bindings(expected["fixtures"])
    if document.get("fixture_bindings") != expected_fixtures:
        raise DiagnosticsContractError(f"wave2 fixture binding drift: {case_id}")

    recomputed_tree = recompute_wave2_file_tree(case_dir, expected.get("chmod"))
    recomputed_tree_hash = file_tree_sha256(recomputed_tree)
    if document.get("file_tree") != recomputed_tree:
        raise DiagnosticsContractError(f"wave2 file-tree content drift: {case_id}")
    if (
        document.get("file_tree_sha256") != recomputed_tree_hash
        or case.get("file_tree_sha256") != recomputed_tree_hash
    ):
        raise DiagnosticsContractError(f"wave2 file-tree hash drift: {case_id}")

    observation_hash = sha256_file(path)
    if case.get("observation_sha256") != observation_hash:
        raise DiagnosticsContractError(f"wave2 observation hash drift: {case_id}")

    return {
        "id": f"diagnostics-wave2:{case_id}",
        "kind": expected["kind"],
        "planned_case_ids": list(expected["planned_case_ids"]),
        "argv": list(expected["argv"]),
        "fixtures": list(expected["fixtures"]),
        "image": WAVE2_PINNED_IMAGE,
        "upstream_commit": UPSTREAM_COMMIT,
        "timeout_seconds": WAVE2_TIMEOUT_SECONDS,
        "timed_out": False,
        "cleanup": WAVE2_CLEANUP,
        "cleanup_outcome": {
            **WAVE2_CLEANUP_OUTCOME_TEMPLATE,
            "container_name": f"ferricov-diag-wave2-{case_id}",
        },
        "effective_environment_variables": dict(case_env),
        "environment_policy": environment_policy,
        "stdin": WAVE2_STDIN,
        "execution_manifest": expected_manifest,
        "file_tree_semantics": WAVE2_FILE_TREE_SEMANTICS,
        "exit_status": expected["expected_exit"],
        "stdout_sha256": stdout_hash,
        "stderr_sha256": stderr_hash,
        "output_sha256": recomputed_tree_hash,
        "observation_sha256": observation_hash,
    }


def wave2_observations() -> list[dict[str, Any]]:
    index = load_json(WAVE2_INDEX)
    if index.get("product_compatibility_evidence"):
        raise DiagnosticsContractError("wave2 index claims product compatibility")
    if index.get("evidence_status") != "oracle_reference":
        raise DiagnosticsContractError("wave2 index evidence status drift")
    if index.get("upstream_commit") != UPSTREAM_COMMIT:
        raise DiagnosticsContractError("wave2 upstream commit drift")
    if index.get("image") != WAVE2_PINNED_IMAGE:
        raise DiagnosticsContractError("wave2 image identity drift")
    if index.get("file_tree_semantics") != WAVE2_FILE_TREE_SEMANTICS:
        raise DiagnosticsContractError("wave2 index file-tree semantics drift")
    if index.get("timeout_seconds") != WAVE2_TIMEOUT_SECONDS:
        raise DiagnosticsContractError("wave2 index timeout drift")
    base_env = dict(WAVE2_BASE_EFFECTIVE_ENVIRONMENT_VARIABLES)
    environment_policy = {
        **WAVE2_ENVIRONMENT_POLICY_TEMPLATE,
        "declared_variables": dict(base_env),
        "effective_environment_variables": dict(base_env),
    }
    execution_environment = {
        **WAVE2_EXECUTION_ENVIRONMENT_TEMPLATE,
        "env": dict(base_env),
        "environment_policy": environment_policy,
        "stdin": WAVE2_STDIN,
    }
    if index.get("execution_environment") != execution_environment:
        raise DiagnosticsContractError("wave2 index execution environment drift")
    if index.get("effective_environment_variables") != base_env:
        raise DiagnosticsContractError("wave2 index effective environment drift")
    if index.get("environment_policy") != environment_policy:
        raise DiagnosticsContractError("wave2 index environment policy drift")
    if index.get("cleanup") != WAVE2_CLEANUP:
        raise DiagnosticsContractError("wave2 index cleanup policy drift")
    if index.get("stdin") != WAVE2_STDIN:
        raise DiagnosticsContractError("wave2 index stdin policy drift")
    if index.get("execution_manifest") != WAVE2_EXECUTION_MANIFEST_BASE:
        raise DiagnosticsContractError("wave2 index execution_manifest drift")
    if index.get("case_count") != WAVE2_EXPECTED_CASE_COUNT:
        raise DiagnosticsContractError("wave2 case count drift")
    if len(index.get("cases", [])) != WAVE2_EXPECTED_CASE_COUNT:
        raise DiagnosticsContractError("wave2 case list length drift")

    expected_ids = [entry["id"] for entry in WAVE2_EXPECTED_CASES]
    actual_ids = [case["id"] for case in index["cases"]]
    if actual_ids != expected_ids:
        raise DiagnosticsContractError("wave2 case id set/order drift")

    planned_seen: list[str] = []
    for expected in WAVE2_EXPECTED_CASES:
        for planned_id in expected["planned_case_ids"]:
            if planned_id not in planned_seen:
                planned_seen.append(planned_id)
    if planned_seen != WAVE2_EXPECTED_PLANNED_IDS:
        raise DiagnosticsContractError("wave2 planned-id coverage set drift")

    result = []
    for case, expected in zip(index["cases"], WAVE2_EXPECTED_CASES):
        result.append(wave2_case(case, expected))
    return result


def oracle_observations() -> list[dict[str, Any]]:
    result = []
    startup_case_to_command = {case: command for command, case in STARTUP_CASES.items()}
    for case_id in STARTUP_CASES.values():
        entry = correctness_case(case_id)
        command = startup_case_to_command[case_id]
        entry["kind"] = (
            "startup_environment_intercept" if command == "geninfo" else "startup_boundary"
        )
        entry["planned_case_ids"] = (
            []
            if command == "geninfo"
            else [STARTUP_PLANNED_CASES[command]]
        )
        result.append(entry)

    for case_id in INVALID_CASES.values():
        entry = correctness_case(case_id)
        entry["kind"] = "parser_boundary"
        entry["planned_case_ids"] = ["DIAG-PARSER-FAMILY-001"]
        result.append(entry)

    for case_id, case_ids in CONFIG_CASES.items():
        entry = correctness_case(case_id)
        entry["kind"] = "configuration_error_control"
        entry["planned_case_ids"] = case_ids
        result.append(entry)

    tracefile = load_json(TRACEFILE_BASELINE)
    for case in tracefile["cases"]:
        if case["exit_status"] == 0 and ".ignore-" not in case["id"]:
            continue
        entry = tracefile_case(case)
        entry["kind"] = (
            "named_error_ignore_one" if ".ignore-" in case["id"] else "named_error_fatal"
        )
        entry["planned_case_ids"] = [
            "DIAG-IGNORE-WARN-001"
            if ".ignore-" in case["id"]
            else "DIAG-IGNORE-ERROR-001"
        ]
        result.append(entry)

    result.extend(wave1_observations())
    result.extend(wave2_observations())
    return result


def build_document(upstream_root: Path) -> dict[str, Any]:
    categories = registry_entries(upstream_root)
    controls = control_rules(upstream_root)
    surfaces = unclassified_surfaces(upstream_root)
    exits = exit_policies(upstream_root)
    planned = planned_case_ids()
    observations = oracle_observations()
    return {
        "schema_version": 1,
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "scope": "LCOV 2.5 named diagnostics, unclassified failure surfaces, severity and continuation controls, command exit policies, and retained Oracle references",
        "artifact_bindings": artifact_bindings(),
        "categories": categories,
        "control_rules": controls,
        "unclassified_surfaces": surfaces,
        "exit_policies": exits,
        "planned_case_ids": planned,
        "planned_case_evidence_status": "planned",
        "planned_case_product_evidence": [],
        "oracle_observations": observations,
        "oracle_observation_evidence_status": "oracle_reference",
        "oracle_observation_product_evidence": [],
        "known_evidence_gaps": [
            "geninfo parallel child stop/keep/ignore Oracle watchdog and Ferricov-approved pair matrix",
            "child signal identity, unknown-child, parent-death, fork-retry exhaustion, and corrupt-payload paths",
            "dependency-masked genpng image pair for GD-absent branch",
            "richer multi-error converter corpora beyond current keep-going traps",
            "full 71-case executable acceptance suite beyond wave1+wave2 reference bindings",
            "Ferricov product differential for all oracle_reference diagnostics observations",
        ],
        "totals": {
            "categories": len(categories),
            "category_symbol_references": sum(
                entry["symbol_reference_count"] for entry in categories
            ),
            "reserved_categories": sum(
                entry["emitter_status"] == "reserved_no_production_emitter"
                for entry in categories
            ),
            "control_rules": len(controls),
            "unclassified_surfaces": len(surfaces),
            "exit_policies": len(exits),
            "planned_cases": len(planned),
            "oracle_observations": len(observations),
            "startup_observations": sum(
                entry["kind"].startswith("startup") for entry in observations
            ),
            "parser_observations": sum(
                entry["kind"] == "parser_boundary" for entry in observations
            ),
            "configuration_observations": sum(
                entry["kind"] == "configuration_error_control"
                for entry in observations
            ),
            "named_error_fatal_observations": sum(
                entry["kind"] == "named_error_fatal" for entry in observations
            ),
            "named_error_ignore_one_observations": sum(
                entry["kind"] == "named_error_ignore_one" for entry in observations
            ),
            "wave1_observations": sum(
                entry["id"].startswith("diagnostics-wave1:") for entry in observations
            ),
            "wave2_observations": sum(
                entry["id"].startswith("diagnostics-wave2:") for entry in observations
            ),
        },
        "product_compatibility_evidence": False,
    }


def validate_schema(document: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise DiagnosticsContractError(
            f"diagnostics contract schema is invalid: {error.message}"
        ) from error
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise DiagnosticsContractError(
            f"diagnostics contract schema failure at {location}: {errors[0].message}"
        )


def validate_upstream_identity(upstream_root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip() != UPSTREAM_COMMIT:
        raise DiagnosticsContractError("diagnostics contract upstream commit mismatch")


def validate_source_references(document: dict[str, Any], upstream_root: Path) -> None:
    entries = [
        *document["control_rules"],
        *document["unclassified_surfaces"],
        *document["exit_policies"],
    ]
    for entry in entries:
        for reference in entry["source_references"]:
            actual = (upstream_root / reference["path"]).read_text(
                encoding="utf-8"
            ).splitlines()[reference["line"] - 1]
            if actual != reference["text"]:
                raise DiagnosticsContractError(
                    f"source text drift: {reference['path']}:{reference['line']}"
                )


def validate_document(document: dict[str, Any], upstream_root: Path) -> None:
    validate_schema(document)
    expected = build_document(upstream_root)
    if document["upstream_commit"] != UPSTREAM_COMMIT:
        raise DiagnosticsContractError("diagnostics document upstream commit drift")
    if document["categories"] != expected["categories"]:
        raise DiagnosticsContractError("diagnostic registry or symbol closure drift")
    if document["control_rules"] != expected["control_rules"]:
        raise DiagnosticsContractError("diagnostic control-rule drift")
    if document["unclassified_surfaces"] != expected["unclassified_surfaces"]:
        raise DiagnosticsContractError("unclassified diagnostic surface drift")
    if document["exit_policies"] != expected["exit_policies"]:
        raise DiagnosticsContractError("command exit-policy drift")
    if document["planned_case_ids"] != expected["planned_case_ids"]:
        raise DiagnosticsContractError("diagnostic planned-case catalog drift")
    if document["planned_case_evidence_status"] != "planned":
        raise DiagnosticsContractError("planned diagnostic case claims evidence")
    if document["planned_case_product_evidence"]:
        raise DiagnosticsContractError("planned diagnostic case claims product evidence")
    if document["artifact_bindings"] != expected["artifact_bindings"]:
        raise DiagnosticsContractError("retained diagnostics artifact binding drift")
    if document["oracle_observations"] != expected["oracle_observations"]:
        raise DiagnosticsContractError("diagnostic Oracle observation identity drift")
    if document["known_evidence_gaps"] != expected["known_evidence_gaps"]:
        raise DiagnosticsContractError("diagnostic evidence-gap inventory drift")
    if document["totals"] != expected["totals"]:
        raise DiagnosticsContractError("diagnostics contract totals drift")

    validate_source_references(document, upstream_root)
    if document["product_compatibility_evidence"]:
        raise DiagnosticsContractError("diagnostics contract claims product compatibility")
    for collection in (
        "categories",
        "control_rules",
        "unclassified_surfaces",
        "exit_policies",
    ):
        for entry in document[collection]:
            if entry["product_evidence"]:
                raise DiagnosticsContractError(
                    f"diagnostic reference claims product evidence: {entry['id']}"
                )
    if document["oracle_observation_evidence_status"] != "oracle_reference":
        raise DiagnosticsContractError("diagnostic Oracle reference claims product status")
    if document["oracle_observation_product_evidence"]:
        raise DiagnosticsContractError("diagnostic Oracle reference claims product evidence")
    wave1_ids = [
        entry["id"]
        for entry in document["oracle_observations"]
        if entry["id"].startswith("diagnostics-wave1:")
    ]
    expected_wave1_ids = [
        f"diagnostics-wave1:{entry['id']}" for entry in WAVE1_EXPECTED_CASES
    ]
    if wave1_ids != expected_wave1_ids:
        raise DiagnosticsContractError("wave1 observation id set/order drift")
    wave1_planned: list[str] = []
    for entry in document["oracle_observations"]:
        if not entry["id"].startswith("diagnostics-wave1:"):
            continue
        for planned_id in entry["planned_case_ids"]:
            if planned_id not in wave1_planned:
                wave1_planned.append(planned_id)
    if wave1_planned != WAVE1_EXPECTED_PLANNED_IDS:
        raise DiagnosticsContractError("wave1 planned-id coverage set drift")
    for entry, expected in zip(
        [
            item
            for item in document["oracle_observations"]
            if item["id"].startswith("diagnostics-wave1:")
        ],
        WAVE1_EXPECTED_CASES,
    ):
        if entry["kind"] != expected["kind"]:
            raise DiagnosticsContractError(
                f"wave1 observation kind drift: {expected['id']}"
            )
        if entry["planned_case_ids"] != expected["planned_case_ids"]:
            raise DiagnosticsContractError(
                f"wave1 observation planned-case drift: {expected['id']}"
            )
        if entry.get("argv") != expected["argv"]:
            raise DiagnosticsContractError(
                f"wave1 observation argv drift: {expected['id']}"
            )
        if entry.get("fixtures") != expected["fixtures"]:
            raise DiagnosticsContractError(
                f"wave1 observation fixtures drift: {expected['id']}"
            )
        if entry["exit_status"] != expected["expected_exit"]:
            raise DiagnosticsContractError(
                f"wave1 observation exit drift: {expected['id']}"
            )
        if entry.get("image") != WAVE1_PINNED_IMAGE:
            raise DiagnosticsContractError(
                f"wave1 observation image drift: {expected['id']}"
            )
        if entry.get("upstream_commit") != UPSTREAM_COMMIT:
            raise DiagnosticsContractError(
                f"wave1 observation upstream drift: {expected['id']}"
            )
        if entry.get("timeout_seconds") != WAVE1_TIMEOUT_SECONDS:
            raise DiagnosticsContractError(
                f"wave1 observation timeout drift: {expected['id']}"
            )
        if entry.get("timed_out") is not False:
            raise DiagnosticsContractError(
                f"wave1 observation timed_out drift: {expected['id']}"
            )
        if entry.get("cleanup") != WAVE1_CLEANUP:
            raise DiagnosticsContractError(
                f"wave1 observation cleanup drift: {expected['id']}"
            )
        expected_cleanup = {
            **WAVE1_CLEANUP_OUTCOME_TEMPLATE,
            "container_name": f"ferricov-diag-wave1-{expected['id']}",
        }
        if entry.get("cleanup_outcome") != expected_cleanup:
            raise DiagnosticsContractError(
                f"wave1 observation cleanup outcome drift: {expected['id']}"
            )
        if entry.get("effective_environment_variables") != WAVE1_EFFECTIVE_ENVIRONMENT_VARIABLES:
            raise DiagnosticsContractError(
                f"wave1 observation effective environment drift: {expected['id']}"
            )
        if entry.get("environment_policy") != WAVE1_ENVIRONMENT_POLICY:
            raise DiagnosticsContractError(
                f"wave1 observation environment policy drift: {expected['id']}"
            )
        if entry.get("stdin") != WAVE1_STDIN:
            raise DiagnosticsContractError(
                f"wave1 observation stdin drift: {expected['id']}"
            )
        expected_manifest = {
            **WAVE1_EXECUTION_MANIFEST_BASE,
            "invoked_command": expected["argv"][0],
            "invoked_executable": {
                "name": expected["argv"][0],
                "path": WAVE1_EXECUTION_MANIFEST_BASE["executables"][
                    expected["argv"][0]
                ]["path"],
                "sha256": WAVE1_EXECUTION_MANIFEST_BASE["executables"][
                    expected["argv"][0]
                ]["sha256"],
            },
            "invoked_argv": list(expected["argv"]),
        }
        if entry.get("execution_manifest") != expected_manifest:
            raise DiagnosticsContractError(
                f"wave1 observation execution_manifest drift: {expected['id']}"
            )
        if entry.get("file_tree_semantics") != WAVE1_FILE_TREE_SEMANTICS:
            raise DiagnosticsContractError(
                f"wave1 observation file-tree semantics drift: {expected['id']}"
            )
    geninfo_true = next(
        (
            entry
            for entry in document["oracle_observations"]
            if entry["id"] == "diagnostics-wave1:diag-noargs-geninfo-writable"
        ),
        None,
    )
    if geninfo_true is None:
        raise DiagnosticsContractError("missing true geninfo no-args wave1 observation")
    if geninfo_true["kind"] != "startup_boundary":
        raise DiagnosticsContractError("true geninfo no-args kind drift")
    if geninfo_true["planned_case_ids"] != ["DIAG-NOARGS-GENINFO-001"]:
        raise DiagnosticsContractError("true geninfo no-args planned-case binding drift")
    if geninfo_true["exit_status"] != 255:
        raise DiagnosticsContractError("true geninfo no-args exit drift")
    intercept = next(
        (
            entry
            for entry in document["oracle_observations"]
            if entry["id"] == "correctness:m0-core-geninfo-startup-control"
        ),
        None,
    )
    if intercept is None or intercept["kind"] != "startup_environment_intercept":
        raise DiagnosticsContractError("geninfo startup intercept classification drift")
    if intercept["planned_case_ids"]:
        raise DiagnosticsContractError("geninfo intercept must not claim no-args case")
    for converter_id in (
        "diag-perl2lcov-keep",
        "diag-llvm2lcov-keep",
        "diag-py2lcov-keep",
        "diag-xml2lcov-keep",
    ):
        entry = next(
            item
            for item in document["oracle_observations"]
            if item["id"] == f"diagnostics-wave1:{converter_id}"
        )
        if entry["exit_status"] != 0:
            raise DiagnosticsContractError(
                f"converter keep-going success exit drift: {converter_id}"
            )
        if not entry["fixtures"]:
            raise DiagnosticsContractError(
                f"converter keep-going missing real input fixture: {converter_id}"
            )
    boundary = next(
        item
        for item in document["oracle_observations"]
        if item["id"] == "diagnostics-wave1:diag-converter-keep-boundary"
    )
    if boundary["planned_case_ids"] != ["DIAG-CONVERTER-KEEP-BOUNDARY-001"]:
        raise DiagnosticsContractError("converter boundary planned-case drift")
    if boundary["exit_status"] != 1:
        raise DiagnosticsContractError("converter boundary exit drift")
    if boundary["fixtures"] != ["broken-no-sources.xml"]:
        raise DiagnosticsContractError("converter boundary fixture drift")

    wave2_ids = [
        entry["id"]
        for entry in document["oracle_observations"]
        if entry["id"].startswith("diagnostics-wave2:")
    ]
    expected_wave2_ids = [
        f"diagnostics-wave2:{entry['id']}" for entry in WAVE2_EXPECTED_CASES
    ]
    if wave2_ids != expected_wave2_ids:
        raise DiagnosticsContractError("wave2 observation id set/order drift")
    wave2_planned: list[str] = []
    for entry in document["oracle_observations"]:
        if not entry["id"].startswith("diagnostics-wave2:"):
            continue
        for planned_id in entry["planned_case_ids"]:
            if planned_id not in wave2_planned:
                wave2_planned.append(planned_id)
    if wave2_planned != WAVE2_EXPECTED_PLANNED_IDS:
        raise DiagnosticsContractError("wave2 planned-id coverage set drift")
    for entry, expected in zip(
        [
            item
            for item in document["oracle_observations"]
            if item["id"].startswith("diagnostics-wave2:")
        ],
        WAVE2_EXPECTED_CASES,
    ):
        if entry["kind"] != expected["kind"]:
            raise DiagnosticsContractError(
                f"wave2 observation kind drift: {expected['id']}"
            )
        if entry["planned_case_ids"] != expected["planned_case_ids"]:
            raise DiagnosticsContractError(
                f"wave2 observation planned-case drift: {expected['id']}"
            )
        if entry.get("argv") != expected["argv"]:
            raise DiagnosticsContractError(
                f"wave2 observation argv drift: {expected['id']}"
            )
        if entry.get("fixtures") != expected["fixtures"]:
            raise DiagnosticsContractError(
                f"wave2 observation fixtures drift: {expected['id']}"
            )
        if entry["exit_status"] != expected["expected_exit"]:
            raise DiagnosticsContractError(
                f"wave2 observation exit drift: {expected['id']}"
            )
        if entry.get("image") != WAVE2_PINNED_IMAGE:
            raise DiagnosticsContractError(
                f"wave2 observation image drift: {expected['id']}"
            )
        if entry.get("upstream_commit") != UPSTREAM_COMMIT:
            raise DiagnosticsContractError(
                f"wave2 observation upstream drift: {expected['id']}"
            )
        if entry.get("timeout_seconds") != WAVE2_TIMEOUT_SECONDS:
            raise DiagnosticsContractError(
                f"wave2 observation timeout drift: {expected['id']}"
            )
        if entry.get("timed_out") is not False:
            raise DiagnosticsContractError(
                f"wave2 observation timed_out drift: {expected['id']}"
            )
        if entry.get("cleanup") != WAVE2_CLEANUP:
            raise DiagnosticsContractError(
                f"wave2 observation cleanup drift: {expected['id']}"
            )
        expected_cleanup = {
            **WAVE2_CLEANUP_OUTCOME_TEMPLATE,
            "container_name": f"ferricov-diag-wave2-{expected['id']}",
        }
        if entry.get("cleanup_outcome") != expected_cleanup:
            raise DiagnosticsContractError(
                f"wave2 observation cleanup outcome drift: {expected['id']}"
            )
        case_env = merge_wave2_env(expected.get("env"))
        if entry.get("effective_environment_variables") != case_env:
            raise DiagnosticsContractError(
                f"wave2 observation effective environment drift: {expected['id']}"
            )
        if entry.get("stdin") != WAVE2_STDIN:
            raise DiagnosticsContractError(
                f"wave2 observation stdin drift: {expected['id']}"
            )
        if entry.get("file_tree_semantics") != WAVE2_FILE_TREE_SEMANTICS:
            raise DiagnosticsContractError(
                f"wave2 observation file-tree semantics drift: {expected['id']}"
            )
    # Explicit residual: Ferricov-only planned IDs remain planned with no product claim.
    ferricov_planned = [
        planned_id
        for planned_id in document["planned_case_ids"]
        if planned_id.endswith("-FERRICOV-001")
    ]
    if not ferricov_planned:
        raise DiagnosticsContractError("missing Ferricov-parity planned residual IDs")
    for planned_id in ferricov_planned:
        if any(
            planned_id in entry.get("planned_case_ids", [])
            for entry in document["oracle_observations"]
        ):
            raise DiagnosticsContractError(
                f"Ferricov-parity planned ID must remain unbound: {planned_id}"
            )
    if document["planned_case_evidence_status"] != "planned":
        raise DiagnosticsContractError("planned diagnostic case claims evidence")
    if document["product_compatibility_evidence"]:
        raise DiagnosticsContractError("diagnostics contract claims product compatibility")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, default=DEFAULT_UPSTREAM_ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    upstream_root = args.upstream_root.resolve()
    validate_upstream_identity(upstream_root)
    document = build_document(upstream_root)
    validate_document(document, upstream_root)
    content = canonical_json(document).encode("ascii")
    if args.write:
        OUTPUT_PATH.write_bytes(content)
        print(f"DIAGNOSTICS_CONTRACT_WRITTEN path={OUTPUT_PATH.relative_to(ROOT)}")
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != content:
        raise DiagnosticsContractError(
            "committed diagnostics contract differs from generation"
        )
    print(
        "DIAGNOSTICS_CONTRACT_OK "
        f"categories={document['totals']['categories']} "
        f"symbol_refs={document['totals']['category_symbol_references']} "
        f"controls={document['totals']['control_rules']} "
        f"exit_policies={document['totals']['exit_policies']} "
        f"planned_cases={document['totals']['planned_cases']} "
        f"oracle_observations={document['totals']['oracle_observations']} "
        "product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
