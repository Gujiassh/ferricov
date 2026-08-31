# M1-CORE-007 Progress — Deterministic Canonical Writer

Status: **IMPLEMENTED — CRITICAL RE-REVIEW PENDING**
Date: 2026-08-31
Base: `integration/m1-current@f781a0d`
Branch: `feat/m1-core-007-canonical-writer`

## Delivered

`write_canonical` is a pure model projection with explicit feature flags,
comments, source-path projection, and optional checksum provider. Projected
source bytes determine source order. Stored checksums take precedence over a
provider; disabling checksums calls neither output path. Sections originate
only from line-testcase membership and test names sort by bytes.

The writer emits current functions, branches, MC/DC, lines, recomputed summaries,
and exact terminators in U-WRITE order. Numeric locations sort without fixed-width
or float coercion. Function and branch indexes are reassigned. MC/DC group keys
sort lexically and senses emit t then f. Genuine numeric branch expressions remain exact. Accepted absent-expression branch states fail with a typed serialization error because the upstream numeric fallback is lexically indistinguishable; CORE-008 owns nonserializable-state classification. Legacy
FN/FNDA input serializes as FNL/FNA. Serialization never mutates the model.

## Verification

- `cargo test -p ferricov-tracefile`: 46 passed
- `cargo test -p ferricov-model`: 48 passed
- `cargo check --workspace --all-targets --locked`: passed with pre-existing warnings
- `git diff --check`: passed

Focused tests cover inverse projected source and testcase ordering, multiple
branch blocks, MC/DC lexical 10-before-2 groups, t/f order, missing senses and
exclusions, non-UTF8 paths, checksum disabled/stored/provider modes, deep model
nonmutation, repeated writes, fixed-point parse-write-parse, and legacy rewrite.

## Blocked Host Gates

- Workspace fmt/clippy are blocked by pre-existing unrelated formatting/lints.
- Python contracts are blocked by missing `jsonschema` and Windows CRLF drift.
- Docker Oracle comparison is unavailable on this Windows host.
- Product evidence remains false; CLI, ops, and report are unchanged.
