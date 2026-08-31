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
state, open section, buffered transport bytes, and canonical evidence.

`EvidenceSnapshot` is the separate full evidence/run envelope. Derived equality
includes the semantic snapshot, parser state and diagnostics, in-flight open
section/indexes, ignore policy/stopped, LineSplitter buffer and pending-CR state,
source diagnostic-path provenance excluded from model identity, and canonical
bytes or typed nonserializability. `ProcessEvidence` explicitly models optional
stdout/stderr/exit status; in-process capture truthfully leaves it `None`.

## Verification

- `cargo test -p ferricov-tracefile`: 53 passed
- `cargo test -p ferricov-model`: 48 passed
- `cargo check --workspace --all-targets --locked`: passed with existing warning
- `git diff --check`: passed

Reverse tests prove diagnostic-only runs are semantic-equal but evidence-unequal,
unfinished splitter bytes differ from untouched evidence and finish
deterministically, diagnostic paths remain evidence-distinct despite semantic
identity equality, signed-zero/nonfinite/arbitrary bytes survive, family/index
changes are unequal, and absent branch expressions retain typed classification.

Product evidence remains false. Existing host fmt/clippy/Python/CRLF/Docker
limitations remain nonblocking and unchanged.
