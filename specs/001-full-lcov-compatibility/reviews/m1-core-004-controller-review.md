# M1-CORE-004 Controller Critical Review

Status: **ACCEPT_WITH_NOTES**  
Date: 2026-08-18  
Subject: ordered algebra APIs in `crates/model`

## Semantic oracle

1. Line intersect adds common counts (not min); difference removes keys.
2. Function union is left-biased on range; indexes remain coherent.
3. Branch matches by signature + nth occurrence; does not claim BRANCH-CACHE Oracle quirk done.
4. MC/DC longer-left asymmetric vector fails closed via Result (not panic).
5. Operand order is preserved where model requires it.
6. No product evidence / CLI creep; ALG residuals explicitly deferred.

## Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Goal alignment | **pass** | Structural algebra for CORE-004; honest ALG deferrals |
| Architecture / ownership | **pass** | New `algebra.rs`; model-only |
| Data contracts | **pass** | Matches coverage-model op rules; residuals named |
| Implementation quality | **pass with watch** | `algebra.rs` ~1139 lines — split before next large ALG binding wave if it grows |
| Verification | **pass** | `cargo test -p ferricov-model` 48 passed |
| Reverse review | **pass** | Claiming BRANCH-CACHE / MCDC-VECTOR Oracle-done would be false; residuals prevent that |

## Notes

1. Exact `compat/fixtures/m0-algebra/` differential binding is still open (not product evidence).
2. File-size watch on `algebra.rs` (under 2000 now; do not keep dumping fixture runners here).
3. Does not flip product evidence.

## Verdict

**ACCEPT_WITH_NOTES** — land CORE-004; next CORE-005 logical-line parser in `crates/tracefile`.
