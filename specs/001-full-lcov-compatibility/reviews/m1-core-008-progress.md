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
Current parser, active binding, open-section binding, and every stored testcase
family key also carry an explicit `TestNameProvenance` projection containing the
semantic name plus optional raw unsanitized `TN` bytes.
The envelope stores `attempted_output: Option<ByteString>` independently from
classification, so bytes remain inspectable after post-write rejection.
`ProcessEvidence` explicitly models optional stdout/stderr/exit status;
in-process capture truthfully leaves it `None`.

## Serializability Classification

`classify_contract` is an independent, declarative pre-writer gate. It compares
aggregate stores with testcase-family reconstruction, rejects family keys that
cannot be emitted without line membership, rejects opaque observable totals and
every context-disabled family key even when its value is explicitly empty, and stored checksums when checksum output is disabled. It
also rejects sources with no emitted line-testcase section and checksum entries
whose line has no emitted `DA` membership. Retained populated-close history returns
`BlockedOracleUnknown` for repeated-close lifecycle cases. A contract-level
`NonSerializable` or blocked model is never passed to the writer and therefore
has no attempted output bytes.

Only a provisionally `Serializable` model reaches the writer. The produced bytes
are retained immediately, then parsed through a fresh full `StreamingParser`.
Acceptance requires no stop, diagnostics, open section, buffered bytes, or
pending CR; exact semantic database equality; and a byte-identical second write.
Parse rejection, semantic mismatch, second-writer failure, and fixed-point
mismatch are separately typed without erasing the first attempted bytes.

Focused inverse coverage includes aggregate/testcase divergence, family presence
without line membership (both populated and lazy empty function maps), late-`TN` MC/DC,
observable totals, and the repeated-close lifecycle fixture. The repeated-close
fixture is explicitly `BlockedOracleUnknown` before writer invocation.
Repeated empty sections are the inverse lifecycle case: because they contain no
semantic payload, they do not create populated-close history and remain decided
by ordinary model-shape classification.

## Verification

- `cargo test -p ferricov-tracefile`: 61 passed
- `cargo test -p ferricov-model`: 48 passed
- `cargo check --workspace --all-targets --locked`: passed with the existing
  unused `workdir` warning in the Oracle test target
- `git diff --check`: passed
- `cargo fmt --all -- --check`: unavailable as an acceptance signal on this
  host because its rustfmt version proposes repository-wide changes outside
  CORE-008; repository-wide formatter changes were not applied
- changed CORE-008 Rust files were formatted directly with `rustfmt --edition
  2021`, avoiding unrelated repository-wide changes

Product evidence remains false. Existing host fmt/clippy/Python/CRLF/Docker
limitations remain nonblocking and unchanged.
