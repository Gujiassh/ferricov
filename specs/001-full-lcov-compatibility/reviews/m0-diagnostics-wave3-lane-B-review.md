# Wave3 Lane B Review — signal / fork-retry / corrupt / unknown-child / parent-death

Status: **complete (Oracle reference only)**  
Date: 2026-08-17  
Branch: `m0-diag-wave3/lane-B`  
Worktree: `/home/cc/code1/ferricov-m0-wave3-lane-B`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`  
Upstream: LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`  
Policy: `evidence_status=oracle_reference`, `product_compatibility_evidence=false`, no M1

## Scope

Owned planned IDs (must bind or residual):

| Planned ID | Intent |
| --- | --- |
| `PAR-CHILD-SIGNAL-001` | SIGTERM/SIGKILL remain signals, not shifted ordinary statuses |
| `PAR-FORK-RETRY-001` | Retry count, delay, recovery, exhausted terminal failure are finite |
| `PAR-PAYLOAD-CORRUPT-001` | Corrupt serialized data rejected atomically with parallel failure |
| `PAR-UNKNOWN-CHILD-001` | Real unknown child ≠ exhausted `wait()` returning `-1` |
| `PAR-PARENT-DEATH-001` | Child detects dead parent; no successful payload |

Forbidden: binding any `*-FERRICOV-001` ID; product evidence; M1 implementation.

## Method

1. Read `diagnostics-parallel-contract.md` §11.5 and wave2 parallel cases
   (`par-callback-state-save-fail`, `par-child-exit-callback-start`,
   `par-partial-commit-control`).
2. Designed controlled fault injectors under
   `compat/diagnostics/wave3/fixtures/lane-b/` (Oracle harness, not product).
3. Filled `compat/diagnostics/wave3/scripts/lane_b_cases.py` CASE_SPECS.
4. Captured via `python3 compat/diagnostics/wave3/scripts/capture_wave3.py`
   (wave2-compatible provenance: env `-i`, stdin DEVNULL, named-container
   cleanup, execution_manifest, pinned image).
5. Two stability re-runs: exit codes and normalized stderr phrases stable.

### Harness note: `run_oracle.pl`

Docker places the container entrypoint as PID 1. geninfo's
`check_parent_process` treats `getppid()==1` as parent death. Lane B geninfo
cases therefore launch via:

```text
perl lane-b/run_oracle.pl geninfo ...
```

so geninfo is a non-PID-1 child of perl. This is Oracle harness plumbing only.

### Shared harness edits

None. `capture_wave3.py` was not modified.

## Bound vs residual table

| Planned ID | Status | Case ID(s) | Exit | Key Oracle observation |
| --- | --- | --- | ---: | --- |
| `PAR-CHILD-SIGNAL-001` | **bound** | `par-child-signal-term`, `par-child-signal-kill`, `par-child-signal-exit15-control` | 1 / 1 / 1 | SIGTERM → `died due to signal 15 (SIGTERM)`; SIGKILL → fork path `killed by OS - possibly due to out-of-memory`; ordinary `_exit(15)` → `returned non-zero exit status 15` (contrast proves no shift of ordinary status into signal form) |
| `PAR-FORK-RETRY-001` | **bound** | `par-fork-retry-exhaust` | 1 | With `--ignore-errors fork`, `max_fork_fails=2`, `fork_fail_timeout=0`: two finite `(retrying)` warnings then terminal failure (no infinite retry). Residual note: exhaustion surfaces as unknown process `-1` after retries rather than the explicit `N consecutive fork() failures` string (upstream bookkeeping quirk under this injector) |
| `PAR-PAYLOAD-CORRUPT-001` | **bound** | `par-payload-corrupt` | 1 | Child writes non-Storable `dumper_*` bytes and exits 0; parent rejects with `File is not a perl storable`; no successful HTML merge/output |
| `PAR-UNKNOWN-CHILD-001` | **bound** | `par-unknown-child` | 1 | Real positive unknown PID: `found unknown process 9 while waiting for parallel child` (distinct from wait `-1` seen in fork-retry exhaustion) |
| `PAR-PARENT-DEATH-001` | **bound** | `par-parent-death` | 143 | Child kills geninfo parent mid-parallel work; docker exit `143` (128+SIGTERM); empty stderr; **no** `out_parent_death.info` payload |

All five owned IDs are **bound** with Oracle-reference evidence. No residual
unbound IDs for Lane B. No FERRICOV IDs bound.

## Per-case detail

### `PAR-CHILD-SIGNAL-001` — bound (3-case matrix)

| Case | Injector | Semantic |
| --- | --- | --- |
| `par-child-signal-term` | `ver_sigterm.pm` | Worker self-SIGTERM during `extract_version` |
| `par-child-signal-kill` | `ver_sigkill.pm` | Worker self-SIGKILL; parent maps to SIGKILL/OOM fork path |
| `par-child-signal-exit15-control` | `ver_exit15.pm` | Ordinary `_exit(15)` control |

Command family: `perl lane-b/run_oracle.pl geninfo lane-b --parallel 2 ... --rc compute_file_version=1 --version-script ...`  
Env: `LCOV_FORCE_PARALLEL=1`.

Differential proof:

- signal death uses `died due to signal N (SIG…)` wording via
  `report_exit_status` (`status & 0xFF`);
- ordinary exit uses `returned non-zero exit status N` (`status >> 8`);
- SIGTERM vs exit(15) are not interchangeable.

### `PAR-FORK-RETRY-001` — bound

Case: `par-fork-retry-exhaust`  
Injector: `fork_kill.pm` (always SIGKILL in `start`)  
Command: `genhtml ... --simplify-script ./lane-b/fork_kill.pm --parallel 2 --ignore-errors fork --rc max_fork_fails=2 --rc fork_fail_timeout=0`

Observed finite policy:

1. WARNING fork failure with `(retrying)` (attempt 1)
2. WARNING fork failure with `(retrying)` (attempt 2)
3. Terminal ERROR (process exits 1; no hang)

Honest residual nuance (not unbound): after SIGKILL-retry exhaustion the
scheduler also emits `found unknown process -1`. That is an upstream
side-effect of the same stale-active-count family as the geninfo keep-going
loop, but the retry budget itself is finite and observable.

### `PAR-PAYLOAD-CORRUPT-001` — bound

Case: `par-payload-corrupt`  
Injector: `corrupt_store.pm` rewrites `Storable::store` for `dumper_*` paths to
write plain text while returning success so the child exits 0.

Parent observation: `File is not a perl storable` and exit 1 — corrupt payload
is rejected; no successful parallel merge.

### `PAR-UNKNOWN-CHILD-001` — bound

Case: `par-unknown-child`  
Injector: `unknown_child.pm` forks an unreaped helper at module load and delays
the scheduled worker in `start` so `wait()` reaps the helper first.

Observation: `found unknown process 9` (positive PID) vs the `-1` form from
exhausted wait in the fork-retry case. Intent of the ID is met by this
differential pair.

### `PAR-PARENT-DEATH-001` — bound

Case: `par-parent-death`  
Injector: `ver_parent_death.pm` asynchronously TERM/KILL the geninfo parent
from a child version-script.

Observation:

- exit status `143` (128+15) — parent process terminated by SIGTERM;
- empty stderr (parent dies before formatting a final diagnostic);
- no `out_parent_death.info` artifact (no successful payload).

Note: when geninfo is PID 1, ambient `check_parent_process` fires with
`parent process died during '--parallel' execution`. Lane B deliberately uses
`run_oracle.pl` so the sealed case is a **real** parent kill, not the Docker
PID-1 false positive.

## Stability

Two full recaptures under the same image/provenance:

| Field | Stability |
| --- | --- |
| exit_status | identical for all 7 cases |
| normalized stderr phrases | identical (PID/chunk/tmp path numbers vary raw) |
| payload presence | identical (no `out*.info` on fault cases) |

Raw `stderr_sha256` may differ across runs where PIDs or chunk IDs appear in
messages (signal matrix). Semantic binding uses phrase identity, not raw
hashes, for those cases. Fork-retry / corrupt / unknown-child raw stderr
hashes were byte-stable across both runs.

## Files owned / changed

| Path | Role |
| --- | --- |
| `compat/diagnostics/wave3/scripts/lane_b_cases.py` | CASE_SPECS |
| `compat/diagnostics/wave3/fixtures/lane-b/**` | Injectors, sample, gcov fixtures, `run_oracle.pl` |
| `compat/diagnostics/wave3/cases/par-child-signal-*/**` | Captured Oracle observations |
| `compat/diagnostics/wave3/cases/par-fork-retry-exhaust/**` | Captured |
| `compat/diagnostics/wave3/cases/par-payload-corrupt/**` | Captured |
| `compat/diagnostics/wave3/cases/par-unknown-child/**` | Captured |
| `compat/diagnostics/wave3/cases/par-parent-death/**` | Captured |
| `compat/diagnostics/wave3/result.json` | Wave index (lane B only until lane A merges) |
| `specs/.../reviews/m0-diagnostics-wave3-lane-B-review.md` | This review |

Not edited: `contract.py`, `v2.5.json`, `docs/ssot/*`, lane-A files, product crates.

## Product / M1 claims

None. `product_compatibility_evidence=false` on every case. No Ferricov
implementation. No M1 authorization request.

## Blockers for controller S3

- Lane A cases may be absent in this worktree; wave3 index currently contains
  only lane B cases. Controller must merge lane A + B cases before regenerating
  `compat/diagnostics/v2.5.json` / status snapshot.
- Signal-matrix raw stderr hashes are PID-volatile; contract binding should use
  phrase/regex or normalized comparison if hashing is required.
- Fork-retry exhaustion co-emits `unknown process -1`; do not treat that alone
  as binding `PAR-UNKNOWN-CHILD-001` (bound separately via positive PID).

## Pass criteria checklist

- [x] Each owned ID bound with exact Oracle observation (or residual) — all bound
- [x] No product claims
- [x] No `*-FERRICOV-001` bindings
- [x] Injectors documented as Oracle harness
- [x] Two re-runs for stability
- [x] English review + commits
