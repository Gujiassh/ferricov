"""Wave3 Lane A CASE_SPECS — geninfo child stop/keep/ignore Oracle matrix.

Owned planned IDs:
  PAR-GENINFO-CHILD-STOP-001
  PAR-GENINFO-CHILD-EXIT-ORACLE-001
  PAR-GENINFO-CHILD-IGNORE1-ORACLE-001
  PAR-GENINFO-CHILD-IGNORE2-ORACLE-001

Must NOT bind *-FERRICOV-001 IDs.

Fixture recipe (ADR 0004 / diagnostics-parallel §11.5):
  - three-file coverage worklist a.c + b.c + main.c (SHA pins in ADR)
  - ExitStart.pm version-script start hook: POSIX::_exit(7)
  - geninfo --parallel 2 over the three .gcda chunks
  - stop / keep-going / ignore-errors child / ignore-errors child,child

Watchdog cases use in_container_watchdog_seconds (GNU timeout TERM+1s kill)
plus a generous host timeout so capture records exit 124 with timed_out=true
and a flushed pre-kill transcript (status-7 + PID -1 loop, or silent for
two-ignore).
"""

from __future__ import annotations

from typing import Any

# Stage fixtures/lane-a/ as work/lane-a/ (sources, .gcda/.gcno, ExitStart.pm).
_FIXTURES = ["lane-a"]

CASE_SPECS: list[dict[str, Any]] = [
    {
        "id": "par-geninfo-child-stop",
        "argv": [
            "geninfo",
            "--quiet",
            "--parallel",
            "2",
            "--output-filename",
            "stop.info",
            "--version-script",
            "./lane-a/ExitStart.pm",
            "lane-a",
        ],
        "fixtures": list(_FIXTURES),
        "planned_case_ids": ["PAR-GENINFO-CHILD-STOP-001"],
        "kind": "geninfo_child_stop",
        "timeout_seconds": 30,
        "notes": (
            "Default stop: first fatal status-7 child diagnostic, no output "
            "artifact, exit 1, no PID -1. Quiet suppresses volatile temp-path "
            "progress lines; message summary retained on stdout."
        ),
    },
    {
        "id": "par-geninfo-child-exit-oracle",
        "argv": [
            "geninfo",
            "--quiet",
            "--parallel",
            "2",
            "--output-filename",
            "keep.info",
            "--version-script",
            "./lane-a/ExitStart.pm",
            "--keep-going",
            "lane-a",
        ],
        "fixtures": list(_FIXTURES),
        "planned_case_ids": ["PAR-GENINFO-CHILD-EXIT-ORACLE-001"],
        "kind": "geninfo_child_keep_watchdog",
        "timeout_seconds": 30,
        "in_container_watchdog_seconds": 3,
        "notes": (
            "Keep-going reaches watchdog 124 after real child status-7 ERROR "
            "records and PID -1 unknown-process loop; no info artifact. "
            "PID values and -1 repeat count are volatile; seal requires at "
            "least one status-7 ERROR and one PID -1 before timeout."
        ),
    },
    {
        "id": "par-geninfo-child-ignore1-oracle",
        "argv": [
            "geninfo",
            "--quiet",
            "--parallel",
            "2",
            "--output-filename",
            "ignore-child.info",
            "--version-script",
            "./lane-a/ExitStart.pm",
            "--ignore-errors",
            "child",
            "lane-a",
        ],
        "fixtures": list(_FIXTURES),
        "planned_case_ids": ["PAR-GENINFO-CHILD-IGNORE1-ORACLE-001"],
        "kind": "geninfo_child_ignore1_watchdog",
        "timeout_seconds": 30,
        "in_container_watchdog_seconds": 3,
        "notes": (
            "One-ignore reaches watchdog 124 after status-7 WARNING records "
            "and warning PID -1 loop; no info artifact. Child PIDs and -1 "
            "repeat count are volatile."
        ),
    },
    {
        "id": "par-geninfo-child-ignore2-oracle",
        "argv": [
            "geninfo",
            "--quiet",
            "--parallel",
            "2",
            "--output-filename",
            "ignore-twice.info",
            "--version-script",
            "./lane-a/ExitStart.pm",
            "--ignore-errors",
            "child,child",
            "lane-a",
        ],
        "fixtures": list(_FIXTURES),
        "planned_case_ids": ["PAR-GENINFO-CHILD-IGNORE2-ORACLE-001"],
        "kind": "geninfo_child_ignore2_watchdog",
        "timeout_seconds": 30,
        "in_container_watchdog_seconds": 3,
        "notes": (
            "Two-ignore reaches watchdog 124 with console-silent child loop "
            "(empty stderr/stdout under --quiet), no info artifact."
        ),
    },
]
