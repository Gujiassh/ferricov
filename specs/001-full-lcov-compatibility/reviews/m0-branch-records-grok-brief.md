# M0 Branch-Records Oracle Lane: Grok 4.5 Brief

## Assignment

Extend the existing M0 tracefile Oracle corpus with one complete, deterministic
branch-record evidence module. Close the exact executable mappings for:

- `M1-TF-013`: `BRDA` record forms, expressions, counters, and malformed tails;
- `M1-TF-025`: branch block contiguity, reuse, expression identity, ordering, and
  canonical renumbering.

This is an upstream Oracle and contract task only. Do not implement the Rust
tracefile parser, change product crates, add Ferricov product evidence, or claim
M1 readiness.

## Required Coverage

Use the pinned LCOV 2.5 executable and exact deterministic bytes to settle:

- vanilla branch records with numeric taken counts;
- exception, fallthrough, and `U` forms under both unreachable-flag modes;
- `-` taken counts, numeric and comma-bearing branch expressions;
- malformed tails, noncontiguous branch blocks, block gaps, duplicate/reused
  identities, and expression mismatches;
- canonical branch ordering and expression/branch-index renumbering;
- exact diagnostics, exit status, stdout/stderr, and output-file state for every
  failure case.

At least one successful model-shaping case must use the existing
`inspect_model.pl` semantic snapshot boundary. Successful writer behavior must
have canonical rewrite evidence.

## Contract Invariants

- Pinned Oracle identity remains LCOV 2.5 source commit
  `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` and the recorded immutable image.
- Every fixture/case/observation is bound by exact path, bytes, SHA-256, argv,
  exit, raw streams, and output-file identity.
- Structured `requirement_ids` are required for the two assigned IDs; unrelated
  M1 IDs must remain unmapped.
- Old observations must remain byte-for-byte identical by case ID.
- `product_compatibility_evidence` remains false and product evidence remains
  empty.
- One final full Oracle capture is expected after the case set is stable; do not
  repeatedly recapture unchanged corpora.

## Scope And Delivery

Use the existing `compat/fixtures/m0-tracefiles` architecture and its current
validator/contract tests. Synchronize generated files and relevant English
SSoT/spec docs. Work only in `/home/cc/code1/ferricov`; do not create project
agent/session directories, commit, or push. Report exact changed files, Oracle
decisions, all commands/results, and unresolved risks. Do not claim controller
acceptance.

