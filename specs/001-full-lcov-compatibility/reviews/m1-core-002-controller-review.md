# M1-CORE-002 Controller Critical Review

Status: **ACCEPT_WITH_NOTES**  
Date: 2026-08-18  
Subject: independent coverage stores in `crates/model`

## Semantic oracle

1. Aggregate and four testcase-family maps are independent owned stores.
2. Explicit empty family values remain map-present.
3. Family key sets may differ on one source.
4. `observable_totals` is distinct and not derived from points.
5. `LineKey` retains zero / ignored-error states (not plain `u64`).
6. No product evidence / CLI / Perl layout creep.

## Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Goal alignment | **pass** | Matches CORE-002 row |
| Architecture / ownership | **pass** | model-only; stubs defer CORE-003 |
| Data contracts | **pass** | Matches abstract model shape |
| Implementation quality | **pass** | New modules; numeric.rs untouched |
| Verification | **pass** | `cargo test -p ferricov-model` 31 passed |
| Reverse review | **pass** | Lazy aggregate↔testcase sync would violate; BTree lexeme order ≠ writer numeric order |

## Notes

1. Function/Branch/MC/DC stubs will likely reshape under CORE-003 — accepted.
2. `TotalState` opacity is intentional until Oracle lifecycle cases force typing.
3. Does not create product evidence.

## Verdict

**ACCEPT_WITH_NOTES** — land CORE-002; next CORE-003 invariants.
