# Wave3 Lane B Brief — signal / fork-retry / corrupt / unknown-child / parent-death

Branch: `m0-diag-wave3/lane-B`  
Worktree: `/home/cc/code1/ferricov-m0-wave3-lane-B`  
Baseline: `206d412`  
Owner files: `compat/diagnostics/wave3/scripts/lane_b_cases.py`, `fixtures/lane-b/**`, captured fault cases

## Owned planned IDs (must bind)

1. `PAR-CHILD-SIGNAL-001` — SIGTERM/SIGKILL remain signals, not shifted ordinary statuses
2. `PAR-FORK-RETRY-001` — retry count, delay, recovery, exhausted terminal failure are finite
3. `PAR-PAYLOAD-CORRUPT-001` — corrupt serialized data rejected atomically with parallel failure
4. `PAR-UNKNOWN-CHILD-001` — real unknown child ≠ exhausted wait() -1
5. `PAR-PARENT-DEATH-001` — child detects dead parent; no successful payload

## Forbidden

- Binding FERRICOV parity IDs
- Editing contract.py / v2.5.json / lane-A files
- Product evidence or M1 implementation

## Method

1. Read diagnostics-parallel contract §11.5 and wave2 parallel cases
   (`par-partial-commit-control`, `par-callback-state-save-fail`, memory cases).
2. Prefer harness injectors under `fixtures/lane-b/` that force the Oracle path
   without ambient host inheritance.
3. Document each injector as Oracle harness, not product code.
4. If a path is not executable on the pinned image without product code, leave it
   unbound and write an honest residual with evidence — do not hollow-bind.
5. Two re-runs for sealed cases; write lane-B review.

## Pass criteria

- Each owned ID is either bound with exact Oracle observation or explicit residual
  with harness-limit reason
- No product claims
- Critical audit ACCEPT
