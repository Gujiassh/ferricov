"""Wave3 Lane B CASE_SPECS — signal/fork-retry/corrupt/unknown-child/parent-death.

Owned planned IDs:
  PAR-CHILD-SIGNAL-001
  PAR-FORK-RETRY-001
  PAR-PAYLOAD-CORRUPT-001
  PAR-UNKNOWN-CHILD-001
  PAR-PARENT-DEATH-001

Must NOT bind *-FERRICOV-001 IDs.

All injectors under fixtures/lane-b/ are Oracle harness, not product code.
"""

from __future__ import annotations

from typing import Any

# Stage the entire lane-b fixture tree (injectors + sample + gcov artifacts).
_LANE_B = ["lane-b"]

# perl system() launcher keeps geninfo off Docker PID 1 so check_parent_process
# does not fire on ambient getppid()==1.
_PERL_LAUNCH = ["perl", "lane-b/run_oracle.pl"]

_GENINFO_COMMON_ARGS = [
    "geninfo",
    "lane-b",
    "--parallel",
    "2",
    "--ignore-errors",
    "source,gcov,unused,empty,path,unsupported",
    "--rc",
    "compute_file_version=1",
]

CASE_SPECS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # PAR-CHILD-SIGNAL-001 — SIGTERM/SIGKILL remain signals, not shifted
    # ordinary statuses. Paired with ordinary exit(15) control.
    # ------------------------------------------------------------------
    {
        "id": "par-child-signal-term",
        "argv": [
            *_PERL_LAUNCH,
            *_GENINFO_COMMON_ARGS,
            "--output-filename",
            "out_sigterm.info",
            "--version-script",
            "./lane-b/ver_sigterm.pm",
        ],
        "fixtures": list(_LANE_B),
        "planned_case_ids": ["PAR-CHILD-SIGNAL-001"],
        "kind": "parallel_child_signal",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": (
            "Oracle harness ver_sigterm.pm kills the geninfo worker with SIGTERM. "
            "Parent reports 'died due to signal 15 (SIGTERM)', not ordinary status 15. "
            "run_oracle.pl keeps geninfo off Docker PID 1."
        ),
    },
    {
        "id": "par-child-signal-kill",
        "argv": [
            *_PERL_LAUNCH,
            *_GENINFO_COMMON_ARGS,
            "--output-filename",
            "out_sigkill.info",
            "--version-script",
            "./lane-b/ver_sigkill.pm",
        ],
        "fixtures": list(_LANE_B),
        "planned_case_ids": ["PAR-CHILD-SIGNAL-001"],
        "kind": "parallel_child_signal",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": (
            "Oracle harness ver_sigkill.pm kills the geninfo worker with SIGKILL. "
            "Parent maps SIGKILL to the fork/OOM path ('killed by OS'), retaining "
            "signal identity rather than ordinary exit status 9."
        ),
    },
    {
        "id": "par-child-signal-exit15-control",
        "argv": [
            *_PERL_LAUNCH,
            *_GENINFO_COMMON_ARGS,
            "--output-filename",
            "out_exit15.info",
            "--version-script",
            "./lane-b/ver_exit15.pm",
        ],
        "fixtures": list(_LANE_B),
        "planned_case_ids": ["PAR-CHILD-SIGNAL-001"],
        "kind": "parallel_child_signal",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": (
            "Control contrast: ordinary POSIX::_exit(15). Parent reports "
            "'returned non-zero exit status 15', proving signal bits are not "
            "confused with shifted ordinary statuses."
        ),
    },
    # ------------------------------------------------------------------
    # PAR-FORK-RETRY-001 — finite retry count, delay, recovery, exhaustion
    # ------------------------------------------------------------------
    {
        "id": "par-fork-retry-exhaust",
        "argv": [
            "genhtml",
            "lane-b/sample.info",
            "-o",
            "out_fork_retry",
            "--simplify-script",
            "./lane-b/fork_kill.pm",
            "--synthesize-missing",
            "--parallel",
            "2",
            "--ignore-errors",
            "fork",
            "--rc",
            "max_fork_fails=2",
            "--rc",
            "fork_fail_timeout=0",
        ],
        "fixtures": list(_LANE_B),
        "planned_case_ids": ["PAR-FORK-RETRY-001"],
        "kind": "parallel_fork_retry",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": (
            "Oracle harness fork_kill.pm always SIGKILLs the worker. With "
            "--ignore-errors fork, max_fork_fails=2, fork_fail_timeout=0: finite "
            "retry warnings then terminal failure (no infinite retry loop)."
        ),
    },
    # ------------------------------------------------------------------
    # PAR-PAYLOAD-CORRUPT-001 — corrupt serialized data rejected atomically
    # ------------------------------------------------------------------
    {
        "id": "par-payload-corrupt",
        "argv": [
            "genhtml",
            "lane-b/sample.info",
            "-o",
            "out_corrupt",
            "--simplify-script",
            "./lane-b/corrupt_store.pm",
            "--synthesize-missing",
            "--parallel",
            "2",
        ],
        "fixtures": list(_LANE_B),
        "planned_case_ids": ["PAR-PAYLOAD-CORRUPT-001"],
        "kind": "parallel_payload_corrupt",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": (
            "Oracle harness corrupt_store.pm writes non-Storable dumper bytes "
            "and exits 0. Parent rejects with 'File is not a perl storable' / "
            "parallel failure; no successful merge of corrupt payload."
        ),
    },
    # ------------------------------------------------------------------
    # PAR-UNKNOWN-CHILD-001 — real unknown child ≠ wait() -1
    # ------------------------------------------------------------------
    {
        "id": "par-unknown-child",
        "argv": [
            "genhtml",
            "lane-b/sample.info",
            "-o",
            "out_unknown",
            "--simplify-script",
            "./lane-b/unknown_child.pm",
            "--synthesize-missing",
            "--parallel",
            "2",
        ],
        "fixtures": list(_LANE_B),
        "planned_case_ids": ["PAR-UNKNOWN-CHILD-001"],
        "kind": "parallel_unknown_child",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": (
            "Oracle harness unknown_child.pm spawns an unreaped helper so wait() "
            "reaps a real positive unknown PID. Distinct from exhausted wait() "
            "returning -1 (see fork-retry residual path)."
        ),
    },
    # ------------------------------------------------------------------
    # PAR-PARENT-DEATH-001 — child detects dead parent; no successful payload
    # ------------------------------------------------------------------
    {
        "id": "par-parent-death",
        "argv": [
            *_PERL_LAUNCH,
            *_GENINFO_COMMON_ARGS,
            "--output-filename",
            "out_parent_death.info",
            "--version-script",
            "./lane-b/ver_parent_death.pm",
        ],
        "fixtures": list(_LANE_B),
        "planned_case_ids": ["PAR-PARENT-DEATH-001"],
        "kind": "parallel_parent_death",
        "env": {"LCOV_FORCE_PARALLEL": "1"},
        "notes": (
            "Oracle harness ver_parent_death.pm has the geninfo child kill its "
            "parent mid-parallel work. Run terminates without writing "
            "out_parent_death.info (no successful payload). run_oracle.pl "
            "avoids ambient Docker PID-1 false parent-death."
        ),
    },
]
