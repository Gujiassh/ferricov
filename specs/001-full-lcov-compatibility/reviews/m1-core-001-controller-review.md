# M1-CORE-001 Controller Critical Review

Status: **ACCEPT_WITH_NOTES**  
Date: 2026-08-18  
Subject: `crates/model` CORE-001 primitives

## Semantic oracle

1. Every identity field preserves raw bytes; UTF-8 is optional view only.
2. Source lookup identity ≠ display path.
3. Numeric atoms retain lexeme; no silent u64/i64/f64-first coercion.
4. `-` is `NeverEvaluated`, distinct from evaluated `0`.
5. No product evidence / fuzz / CLI ownership creep.

## Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Goal alignment | **pass** | Matches CORE-001 row and support matrix |
| Architecture / ownership | **pass** | Only `crates/model`; no cli/ops/report |
| Data contracts | **pass** | Types mirror coverage-model primitives |
| Implementation quality | **pass** | Split modules; `numeric.rs` ~850 lines — watch growth, split before algebra if it thickens |
| Verification | **pass** | `cargo test -p ferricov-model` 21 passed |
| Reverse review | **pass** | If Display used as identity → bug; if f64 parse added casually → contract break |

## Notes

1. Decimal add is intentionally minimal; later algebra/TF-030 rows must extend with Oracle fixtures, not broaden silently.
2. File-size watch: `numeric.rs` is fine now but should not absorb store/algebra without a split.

## Verdict

**ACCEPT_WITH_NOTES** — land CORE-001; proceed toward CORE-002 stores.
