# M1-CORE-007 Progress — Deterministic Canonical Writer

Status: **IMPLEMENTED**  
Date: 2026-08-31  
Base: `integration/m1-current@f781a0d`  
Branch: `feat/m1-core-007-canonical-writer`

## Delivered

- Added a pure `write_canonical` projection and explicit `SerializationContext`.
- Sections are selected only from testcase line-map membership.
- Output order is comments, `TN`, `SF`, optional `VER`, current functions and
  recomputed totals, branches and totals, MC/DC and totals, lines and totals,
  then exact `end_of_record`.
- Function aliases and source/test maps use their deterministic byte-key order.
- Function indexes and branch block numbers are reassigned for output.
- Branch blocks use signature length, signature bytes, then model position.
- MC/DC groups preserve Perl-lexical key order and emit true before false.
- Legacy and permissive input records are never reproduced.
- Stored checksums are optional by context; comments are explicit context only.
- Repeated writes are byte-identical and model state is not mutated.

## Verification

```text
cargo test -p ferricov-tracefile
cargo test -p ferricov-model
cargo fmt --all --check
cargo check --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
```

Focused tests cover the complete family sequence, exact bytes, alias ordering,
branch renumbering, MC/DC sense ordering, recomputed totals, checksum mode,
feature omission, line-map section selection, and repeated-write determinism.

## Boundaries And Residuals

- Source path projection and external checksum computation stay outside the
  semantic model. This slice emits the retained display path and can emit only
  model-stored checksums; pure provider integration belongs at the later
  runtime/CLI boundary.
- Product evidence remains false. This implementation does not claim Oracle
  differential parity and does not modify CLI, ops, or report crates.
- Docker Oracle execution is unavailable on this Windows host; retained Oracle
  bytes and repository contracts remain the behavioral reference.

