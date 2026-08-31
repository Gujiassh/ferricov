# Wave3 Lane A Brief — geninfo child stop/keep/ignore matrix

Branch: `m0-diag-wave3/lane-A`  
Worktree: `/home/cc/code1/ferricov-m0-wave3-lane-A`  
Baseline: `206d412`  
Owner files: `compat/diagnostics/wave3/scripts/lane_a_cases.py`, `fixtures/lane-a/**`, captured `cases/par-geninfo-child-*/**`

## Owned planned IDs (must bind)

1. `PAR-GENINFO-CHILD-STOP-001` — default stop: first fatal status-7 child diagnostic, no output, exit 1, no PID -1
2. `PAR-GENINFO-CHILD-EXIT-ORACLE-001` — keep-going → watchdog 124 after child status 7 + PID -1 loop
3. `PAR-GENINFO-CHILD-IGNORE1-ORACLE-001` — one-ignore → watchdog 124 after status-7 warnings + warning PID -1 loop
4. `PAR-GENINFO-CHILD-IGNORE2-ORACLE-001` — two-ignore → watchdog 124, console-silent child loop, no output

## Forbidden

- Binding any `*-FERRICOV-001` ID
- Editing `contract.py`, `v2.5.json`, lane-B files, residual behavior fragments
- Claiming product compatibility
- Implementing Ferricov product crates

## Method

1. Study wave2 `par-child-exit-callback-start` and diagnostics-parallel contract §11.5.
2. Build geninfo multi-file parallel fixtures with injected child status-7 failures
   (callback/simplify scripts as in wave2 `parallelFail.pm` pattern; adapt for geninfo).
3. Define CASE_SPECS in `lane_a_cases.py` with exact planned_case_ids, argv, env, fixtures,
   and for watchdog cases set host timeout so capture records exit 124 + timed_out.
4. Run capture for lane-A cases only (or full capture if harness supports filter).
5. Two deterministic re-runs: same exit and stream hashes.
6. Write `m0-diagnostics-wave3-lane-A-review.md` with per-ID evidence table.

## Pass criteria

- Four Oracle IDs appear in wave3 case planned_case_ids
- FERRICOV IDs absent
- Raw reference bins retained
- Independent Critical audit ACCEPT
- English commit messages; GitHub identity `gujishh`
