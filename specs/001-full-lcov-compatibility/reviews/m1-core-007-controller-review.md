# M1-CORE-007 Controller Review Draft

Status: **DRAFT — independent controller acceptance required**  
Risk: **Critical**

## Semantic Oracle

For an identical database and serialization context, output bytes are stable;
sections originate only from testcase line membership; record families and
summary pairs follow `U-WRITE`; summaries are recomputed; legacy/permissive
syntax is omitted; serialization does not mutate the database.

## Review Checklist

| Area | Result | Evidence |
| --- | --- | --- |
| Goal alignment | pass | writer-only tracefile slice |
| Architecture boundary | pass | pure model projection; no filesystem/CLI |
| Section and family ordering | pass | exact-byte focused test |
| Function/branch/MC/DC ordering | pass | focused mixed-family fixture |
| Summary recomputation | pass | deliberately false input summaries ignored |
| Checksum/comments modes | pass | context-controlled output |
| Determinism and mutation safety | pass | repeated write equality; immutable borrow |
| Product evidence | pass | remains false; no evidence files changed |
| Oracle runtime comparison | blocked | Docker unavailable on Windows host |

## Reverse Review

If a family moves, a block number is not reassigned, an input summary leaks,
or a repeated write differs, the exact full-byte assertion fails. If a
function-only or MC/DC-only testcase accidentally creates a section, the
line-membership test fails. Independent review should additionally compare the
mixed fixture against retained canonical Oracle bytes on Linux CI.

## Residual Risk

External checksum providers and source-path projection are intentionally not
invented in the semantic writer. Their later runtime integration needs its own
Oracle-backed tests. The current parser's documented CORE-006 residuals can
also constrain parse-write-parse parity outside this writer's happy-path slice.

