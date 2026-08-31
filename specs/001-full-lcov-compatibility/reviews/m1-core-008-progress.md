# M1-CORE-008 Progress — Semantic Snapshots And Equality

Status: **REWORKED — CRITICAL RE-REVIEW PENDING**
Date: 2026-08-31
Base: `feat/m1-core-007-canonical-writer@ec72681`
Branch: `feat/m1-core-008-semantic-snapshots`

## API Boundary

`SemanticSnapshot` is the model-semantic projection only. Its equality compares
only `CoverageDatabase`: source lookup/display identity, versions/checksums,
aggregate and independent testcase-family maps (including absent/empty), totals,
indexes/order, raw numeric atoms, signed zero, nonfinite classes, and exclusions.
It intentionally ignores parser diagnostics, raw provenance, policy/stopped
state, open section, buffered transport bytes, canonical output, and
serializability classification.

`EvidenceSnapshot` is the separate full evidence/run envelope. Derived equality
includes the semantic snapshot, parser state and diagnostics, in-flight open
section/indexes, ignore policy/stopped state, line-splitter buffer and pending-CR
state, source diagnostic-path provenance excluded from model identity, and
canonical bytes or typed nonserializability. Active parser bindings and open
section bindings retain both raw path bytes and optional `diagnostic_path`.
`ProcessEvidence` explicitly models optional stdout/stderr/exit status;
in-process capture truthfully leaves it `None`.

## Serializability Classification

Writer success is necessary but not sufficient. Evidence capture writes the
canonical bytes, parses those bytes into a fresh `CoverageDatabase`, and compares
the reconstructed `SemanticSnapshot` with the original. Only semantic equality
produces `Serializability::Serializable(bytes)`. Writer failures retain their
typed `SerializationError`; a successful write that loses semantics produces
`NonSerializable(RoundTripSemanticMismatch)`.

`BlockedOracleUnknown` is a third, explicit contract-corpus outcome for a case
whose governing Oracle behavior has not been qualified. Evidence capture never
guesses this result from writer success or failure: decided models are always
classified by write, fresh parse, and exact semantic equality. This keeps a
blocked case distinct from a proven lossy model.

Focused inverse coverage includes aggregate/testcase divergence, family presence
without line membership (both populated and lazy empty function maps), late-`TN` MC/DC,
observable totals, and the repeated-close lifecycle fixture. The repeated-close
fixture is explicitly accepted as serializable only because the reconstructed
model is equal; it is not inferred from writer success.

## Verification

- `cargo test -p ferricov-tracefile`: 55 passed
- `cargo test -p ferricov-model`: 48 passed
- `cargo check --workspace --all-targets --locked`: passed with the existing
  unused `workdir` warning in the Oracle test target
- `git diff --check`: passed
- `cargo fmt --all -- --check`: unavailable as an acceptance signal on this
  host because its rustfmt version proposes repository-wide changes outside
  CORE-008; no formatter changes were applied

Product evidence remains false. Existing host fmt/clippy/Python/CRLF/Docker
limitations remain nonblocking and unchanged.
