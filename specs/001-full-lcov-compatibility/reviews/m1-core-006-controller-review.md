# M1-CORE-006 Controller Critical Review

Status: **ACCEPT_WITH_NOTES**  
Date: 2026-08-18  
Subject: record apply + section commit in `crates/tracefile`

## Semantic oracle

1. All record classes have an apply path; summaries never become trusted totals.
2. EOR commits line/function/branch under SF-bound test name; MC/DC close uses current TN (late-TN).
3. VER conflict / key hard-fails stop; unknown format continues by default.
4. BRDA `-` is NeverEvaluated; non-UTF-8 SF+DA survives.
5. No writer / product evidence / CLI creep.

## Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Goal alignment | **pass** | Honest shippable slice; residual ignore-matrix documented |
| Architecture / ownership | **pass** | tracefile-only; model stores reused |
| Data contracts | **pass** | U-MCDC-LATE-TN close order respected |
| Implementation quality | **pass with watch** | `records.rs` ~839 lines — split before next large ignore-matrix wave |
| Verification | **pass** | tracefile 40 + model 48 passed |
| Reverse review | **pass** | Summary→totals or SF-bound MC/DC close would violate grammar |

## Notes

1. Full Oracle ignore/stop/exit matrix and several malformed edges remain residual.
2. Writer / round-trip is CORE-007.
3. Does not create product evidence.

## Verdict

**ACCEPT_WITH_NOTES** — land CORE-006; next CORE-007 canonical writer.
