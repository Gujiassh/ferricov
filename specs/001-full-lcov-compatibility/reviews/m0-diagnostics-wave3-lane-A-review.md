# Wave3 Lane A Review — geninfo child stop/keep/ignore Oracle matrix

Status: **lane complete (Oracle seals; product evidence false)**  
Date: 2026-08-17  
Branch: `m0-diag-wave3/lane-A`  
Worktree: `/home/cc/code1/ferricov-m0-wave3-lane-A`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`  
Upstream: LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`

## Bound planned IDs

| Planned ID | Case ID | Exit | `timed_out` | Residual |
| --- | --- | --- | --- | --- |
| `PAR-GENINFO-CHILD-STOP-001` | `par-geninfo-child-stop` | `1` | `false` | none (byte-stable streams) |
| `PAR-GENINFO-CHILD-EXIT-ORACLE-001` | `par-geninfo-child-exit-oracle` | `124` | `true` | stderr byte-hash volatile (PID / completion order); semantic seal holds |
| `PAR-GENINFO-CHILD-IGNORE1-ORACLE-001` | `par-geninfo-child-ignore1-oracle` | `124` | `true` | stderr byte-hash volatile (PID / completion order); semantic seal holds |
| `PAR-GENINFO-CHILD-IGNORE2-ORACLE-001` | `par-geninfo-child-ignore2-oracle` | `124` | `true` | none (empty streams, byte-stable) |

## Must remain unbound (not present in any `planned_case_ids`)

- `PAR-GENINFO-CHILD-EXIT-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001`

## Evidence paths

| Case ID | Observation | Streams |
| --- | --- | --- |
| `par-geninfo-child-stop` | `compat/diagnostics/wave3/cases/par-geninfo-child-stop/result.json` | `reference/{stdout,stderr}.{bin,txt}` |
| `par-geninfo-child-exit-oracle` | `compat/diagnostics/wave3/cases/par-geninfo-child-exit-oracle/result.json` | `reference/{stdout,stderr}.{bin,txt}` |
| `par-geninfo-child-ignore1-oracle` | `compat/diagnostics/wave3/cases/par-geninfo-child-ignore1-oracle/result.json` | `reference/{stdout,stderr}.{bin,txt}` |
| `par-geninfo-child-ignore2-oracle` | `compat/diagnostics/wave3/cases/par-geninfo-child-ignore2-oracle/result.json` | `reference/{stdout,stderr}.{bin,txt}` |

Index (lane-A-only capture; controller merges with lane B at S3):
`compat/diagnostics/wave3/result.json`

## Fixture

Directory: `compat/diagnostics/wave3/fixtures/lane-a/`

| File | Role | ADR SHA-256 pin |
| --- | --- | --- |
| `a.c` | source | `3299eca4d87337210531320e68409727733995891030dc38df23575442266862` |
| `b.c` | source | `759fe88339e0446e993f524696cb915bed0f4cd6a3fe82190da0fc3e8dc67770` |
| `main.c` | source | `c00eeaedfdb7ae78ab5e48350f85c386096b29f40152dde57cc78465edbab78a` |
| `ExitStart.pm` | version-script `start` → `POSIX::_exit(7)` | `d49c1cd6b95161f13541849f20bbfc3dd633ec03f1fe7d82700fdf128c854525` |
| `app-{a,b,main}.{gcda,gcno}` | three-chunk coverage worklist built in pinned image | (image-local gcc 12.2.0) |

Build recipe (pinned image, clean env):

```sh
gcc --coverage -O0 a.c b.c main.c -o app && ./app
```

## Observed Oracle behavior (sealed run)

### `PAR-GENINFO-CHILD-STOP-001`

- argv: `geninfo --quiet --parallel 2 --output-filename stop.info --version-script ./lane-a/ExitStart.pm lane-a`
- exit `1`, `timed_out=false`
- stderr: one fatal `ERROR` child diagnostic with `exit status 7`
- no `unknown process -1`
- no `.info` output artifact
- stdout: message summary `child: 1` only (quiet)
- streams byte-stable across three capture re-runs

### `PAR-GENINFO-CHILD-EXIT-ORACLE-001`

- argv: same base + `--keep-going` + output `keep.info`
- in-container watchdog: `timeout --signal=TERM --kill-after=1s 3s` (ADR soft budget)
- exit `124`, `timed_out=true`
- stderr: ≥1 status-7 `ERROR` (observed: 2) then ≥1 `found unknown process -1` loop (observed: 78)
- stdout empty under `--quiet`
- no `.info` artifact
- stderr SHA not byte-stable across re-runs (chunk completion order / child PID); semantic predicates stable

### `PAR-GENINFO-CHILD-IGNORE1-ORACLE-001`

- argv: same base + `--ignore-errors child` + output `ignore-child.info`
- watchdog 3s as above
- exit `124`, `timed_out=true`
- stderr: ≥1 status-7 `WARNING` (observed: 2) then warning PID `-1` loop (observed: 74)
- no `.info` artifact
- stderr SHA volatile for same reason as keep-going; semantic predicates stable

### `PAR-GENINFO-CHILD-IGNORE2-ORACLE-001`

- argv: same base + `--ignore-errors child,child` + output `ignore-twice.info`
- watchdog 3s as above
- exit `124`, `timed_out=true`
- stdout and stderr empty (console-silent under double ignore + quiet)
- no `.info` artifact
- streams byte-stable (empty)

## Harness note (shared `capture_wave3.py`)

Minimal extension required for ADR-faithful watchdog capture:

1. Per-spec `timeout_seconds` (host `communicate` budget).
2. Optional per-spec `in_container_watchdog_seconds`: wrap tool argv with
   `timeout --signal=TERM --kill-after=1s <N>s`, file-buffer stdout/stderr,
   then flush to pipes so exit `124` retains the pre-kill transcript.
3. `timed_out=true` when host communicate times out **or** in-container
   watchdog returns `124`.

Recorded observation `argv` remains the tool argv (no `timeout` prefix) so
case identity stays geninfo-centric; watchdog metadata is under
`execution_environment.in_container_watchdog` and
`in_container_watchdog_seconds`.

Rationale: host-only SIGKILL of `docker run` frequently delivered empty pipes
for the infinite PID `-1` loop (pipe buffer / kill race). ADR explicitly uses
in-container GNU `timeout` for this matrix.

## Provenance (all cases)

- `evidence_status=oracle_reference`
- `product_compatibility_evidence=false`
- `env -i` clean env only; `stdin=subprocess.DEVNULL`
- network `none`, user `1000:1000`, workdir `/work`
- named-container force cleanup with docker-ps fail-closed observer
- no `*-FERRICOV-001` planned IDs in any case

## Verification

```sh
python3 compat/diagnostics/wave3/scripts/capture_wave3.py
# three consecutive runs:
#   stop + ignore2: identical exit + stream hashes
#   keep + ignore1: identical exit/timed_out + semantic transcript predicates;
#                   stderr SHA may drift (ADR-documented volatility)
```

Semantic re-check script (non-hollow seal):

- stop: exit 1, one status-7 ERROR, zero PID -1, no info file
- keep: exit 124, timed_out, ≥1 status-7 ERROR, ≥1 PID -1, no info file
- ignore1: exit 124, timed_out, ≥1 status-7 WARNING, ≥1 PID -1, no info file
- ignore2: exit 124, timed_out, empty stdout/stderr, no info file

## Residual / controller handoff

- Lane A does **not** bind FERRICOV pair IDs (contract hard rule).
- Lane A does **not** edit `contract.py` / `v2.5.json` / status snapshot
  (controller S3).
- Wave3 index currently contains only lane-A cases; controller merges lane B.
- Keep/ignore1 raw stderr hashes are reference snapshots, not a claim of
  universal byte identity on re-capture; ADR §DEV-GENINFO-CHILD already
  classifies PID and `-1` repeat count as volatile.

## Files owned / changed

- `compat/diagnostics/wave3/scripts/lane_a_cases.py`
- `compat/diagnostics/wave3/scripts/capture_wave3.py` (per-case timeout +
  in-container watchdog wrapper only)
- `compat/diagnostics/wave3/fixtures/lane-a/**`
- `compat/diagnostics/wave3/cases/par-geninfo-child-*/**`
- `compat/diagnostics/wave3/result.json` (A-only capture index)
- `specs/001-full-lcov-compatibility/reviews/m0-diagnostics-wave3-lane-A-review.md`
