# M1-CORE-005 Controller Critical Review

Status: **ACCEPT_WITH_NOTES**  
Date: 2026-08-18  
Subject: logical-line parser pipeline in `crates/tracefile`

## Semantic oracle

1. Logical-line normalization: chomp + trailing Perl ASCII `\s`, then `#` only at column 0.
2. TN/SF/KF binding updates parser state; late TN does not clear open source binding.
3. Arbitrary / non-UTF-8 bytes do not panic and survive path identity.
4. Full DA/FN/BRDA/MCDC apply deferred to CORE-006 (classify/stub only).
5. No product evidence / CLI creep.

## Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Goal alignment | **pass** | Matches CORE-005 row |
| Architecture / ownership | **pass** | `crates/tracefile` only; uses model types |
| Data contracts | **pass** | TN `,diff`, SF/KF path bytes, terminator prefix |
| Implementation quality | **pass** | Split modules; files under 500 lines |
| Verification | **pass** | tracefile 30 + model 48 passed |
| Reverse review | **pass** | Treating ` #x` as comment would violate grammar; late-TN rebinding line maps would violate U-MCDC-LATE-TN prep |

## Notes

1. Universal splitter accepts lone CR; Oracle readline is LF-oriented — residual documented for CR-only files.
2. Record apply / section commit / ignore policy remain CORE-006.
3. Does not create product evidence.

## Verdict

**ACCEPT_WITH_NOTES** — land CORE-005; next CORE-006 record semantics.
