# M1-CORE-003 Controller Critical Review

Status: **ACCEPT_WITH_NOTES**  
Date: 2026-08-18  
Subject: Function / Branch / MC/DC structural invariants in `crates/model`

## Semantic oracle

1. Function dual indexes stay coherent after every successful mutation.
2. Representative uses shortest effective length (lambda penalty) then lexical order on insert.
3. Branch signature equals ordered edge kinds; `derived_index` equals construction position.
4. Excluded branch edges and MC/DC senses remain representable; exclusion is sticky.
5. MC/DC expressions always expose both senses; at most one group per size key on a line.
6. No algebra, writer renumbering, product evidence, or CLI ownership creep.

## Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Goal alignment | **pass** | Matches CORE-003 row; algebra deferred correctly |
| Architecture / ownership | **pass** | model-only; stubs replaced in place |
| Data contracts | **pass** | Hierarchical shapes match coverage-model abstract types |
| Implementation quality | **pass** | Files under 700 lines each; numeric.rs untouched |
| Verification | **pass** | `cargo test -p ferricov-model` 39 passed |
| Reverse review | **pass** | Broken reverse alias index would fail coherence assert; clearing exclusion would violate sticky rule |

## Notes

1. `insert_alias` compatibility shim uses start `"0"` — callers must prefer `insert_alias_at`.
2. Removal representative without lexical tie-break still deferred (`M1-ALG-FUNCTION-REP-001`).
3. Asymmetric MC/DC vector merge and branch intersection cache remain CORE-004 / ALG rows.
4. Does not create product evidence.

## Verdict

**ACCEPT_WITH_NOTES** — land CORE-003; next CORE-004 ordered algebra.
