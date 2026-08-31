# M1-CORE-008 Progress — Semantic Snapshots And Equality

Status: **IMPLEMENTED — CRITICAL REVIEW PENDING**
Date: 2026-08-31
Base: `feat/m1-core-007-canonical-writer@ec72681`
Branch: `feat/m1-core-008-semantic-snapshots`

## Delivered

`SemanticSnapshot::capture` clones the complete committed database, parser
provenance/state, in-flight open section and indexes, ignore policy, stopped
state, diagnostics, and canonical serializability result. `Serializability`
contains either exact canonical bytes or the typed CORE-007 error. Snapshot
equality is structural and byte-exact.

The database component includes source lookup/display identities, version and
checksums, aggregate stores, every independent testcase-family map (including
absent versus explicitly empty values), observable totals, function dual
indexes, branch model order/signatures/indexes, MC/DC group/expression/sense
order, exclusions, raw numeric lexemes, nonfinite classes, and signed zero.
No filesystem, CLI, ops, report, or product-evidence dependency was added.

## Verification

- `cargo test -p ferricov-tracefile`: 51 passed
- `cargo test -p ferricov-model`: 48 passed
- `cargo check --workspace --all-targets --locked`: passed with existing warning
- `git diff --check`: passed

Reverse tests distinguish equal-looking counts (`0`/`-0`), diagnostics with an
identical database, family-map/index/order differences, arbitrary non-UTF8
provenance, NaN/infinity, in-flight state and stop policy, canonical output,
and serializable numeric expressions versus accepted absent expressions.

## Residual Host Gates

Workspace fmt/clippy, Python contracts, Windows CRLF artifact validation, and
Docker Oracle execution retain the nonblocking host limitations documented by
CORE-007. Product evidence remains false.

