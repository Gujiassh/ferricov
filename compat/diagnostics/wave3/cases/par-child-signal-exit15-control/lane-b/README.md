# Wave3 Lane B Oracle harness fixtures

These injectors are **Oracle harness** only — not Ferricov product code.

They force pinned LCOV v2.5 parallel-runtime paths so wave3 can seal
Oracle-reference observations for:

| Planned ID | Injector / fixture |
| --- | --- |
| `PAR-CHILD-SIGNAL-001` | `ver_sigterm.pm`, `ver_sigkill.pm`, control `ver_exit15.pm` |
| `PAR-FORK-RETRY-001` | `fork_kill.pm` + `--ignore-errors fork` + finite `max_fork_fails` |
| `PAR-PAYLOAD-CORRUPT-001` | `corrupt_store.pm` |
| `PAR-UNKNOWN-CHILD-001` | `unknown_child.pm` |
| `PAR-PARENT-DEATH-001` | `ver_parent_death.pm` |

`run_oracle.pl` re-launches geninfo/genhtml as a non-PID-1 child so Docker's
init PID is not misread by `check_parent_process` as ambient parent death.
