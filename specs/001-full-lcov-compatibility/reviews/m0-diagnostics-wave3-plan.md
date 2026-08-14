# M0 Diagnostics Wave3 Plan — Unbound PAR-* Bindings

Status: active next track after residual S5  
Baseline integration: `test/m0-tf030-exact-numeric-matrix`  
Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`  
Upstream: v2.5 `74c8eab…`  
Policy: `oracle_reference` only; `product_compatibility_evidence=false`; no M1

## Goal

Bind the 12 planned diagnostic/parallel case IDs that remain unbound after wave1+wave2:

| ID | Intent (from diagnostics-parallel-contract) |
| --- | --- |
| `PAR-GENINFO-CHILD-STOP-001` | Default stop: first fatal status-7 child diagnostic, no output, exit 1, no PID -1 |
| `PAR-GENINFO-CHILD-EXIT-ORACLE-001` | Keep-going reaches watchdog 124 after child status 7 + PID -1 loop |
| `PAR-GENINFO-CHILD-EXIT-FERRICOV-001` | Ferricov-approved keep-going pair (product false; may stay planned if Oracle-only path is required first) |
| `PAR-GENINFO-CHILD-IGNORE1-ORACLE-001` | One-ignore → watchdog 124 after status-7 warnings + warning PID -1 loop |
| `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001` | Ferricov-approved one-ignore pair (product false) |
| `PAR-GENINFO-CHILD-IGNORE2-ORACLE-001` | Two-ignore → watchdog 124, console-silent child loop, no output |
| `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001` | Ferricov-approved two-ignore pair (product false) |
| `PAR-CHILD-SIGNAL-001` | SIGTERM/SIGKILL remain signals, not shifted ordinary statuses |
| `PAR-FORK-RETRY-001` | Retry count, delay, recovery, exhausted terminal failure are finite |
| `PAR-PAYLOAD-CORRUPT-001` | Corrupt serialized data rejected atomically with parallel failure |
| `PAR-UNKNOWN-CHILD-001` | Real unknown child ≠ exhausted wait() -1 |
| `PAR-PARENT-DEATH-001` | Child detects dead parent; no successful payload |

## Delivery shape (wave2-compatible)

```
compat/diagnostics/wave3/
  cases/<case-id>/
  fixtures/
  scripts/capture_wave3.py
  result.json
specs/.../reviews/m0-diagnostics-wave3-review.md
```

Update `compat/diagnostics/v2.5.json` oracle_observations + totals; keep planned catalog planned; fail-closed contract tests.

## Non-goals

- Ferricov product differential for FERRICOV-* pair IDs (remain planned unless a separate product executable exists)
- Residual behavior 7 signed-N/A primary gaps
- Model MD-020 / TF-063 / TF-064 decisions
- m1_authorized flip

## Audit gates

1. S0 wave3 plan ACCEPT (this file + contract alignment)
2. Implement capture + bind
3. Independent Critical audit of wave3 review
4. Controller regenerate status snapshot; m1 blocker diagnostics_unbound count must drop only for truly bound IDs

## Implementation notes

- Inherit wave1/wave2 provenance: env -i, stdin DEVNULL, named-container cleanup, execution_manifest, pinned image.
- GENINFO child matrix may require multi-file parallel geninfo with injected child status-7 failures (callback/simplify scripts as in wave2 `par-child-exit-*`).
- Watchdog cases may need host-side timeout observation (exit 124) with stable transcript normalizers already used by diagnostics contract.
- Signal / parent-death / unknown-child / corrupt-payload may need controlled fault injectors under fixture scripts — document injectors as Oracle harness, not product code.
- Prefer splitting: wave3a Oracle-only (STOP + ORACLE keep/ignore + signal + fork-retry + corrupt + unknown + parent-death); leave FERRICOV-* unbound until product path exists **or** bind as planned-with-oracle-only if contract allows reference without product pair.

## Contract constraint (hard)

`compat/diagnostics/contract.py` requires Ferricov-parity planned IDs to **remain unbound**:

- `PAR-GENINFO-CHILD-EXIT-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE1-FERRICOV-001`
- `PAR-GENINFO-CHILD-IGNORE2-FERRICOV-001`

(and any other `*-FERRICOV-*` parity IDs). Wave3 binds **Oracle / harness-observable** IDs only. After a full Oracle wave3, expected residual unbound floor is at least these FERRICOV pairs (plus any Oracle IDs still blocked by harness limits).

## Acceptance

- `python3 -m unittest compat.diagnostics.test_contract` green
- unbound planned IDs ≤ prior 12; ideally 0 Oracle-capable IDs remain (FERRICOV pairs may remain if product false is mandatory)
- status snapshot `diagnostics.unbound_planned_cases` updated
- review note lists each ID as bound or explicit residual with reason
