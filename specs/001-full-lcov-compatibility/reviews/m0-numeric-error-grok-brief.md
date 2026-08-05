# M0 Numeric/Error Oracle Lane: Grok 4.5 Brief

## Assignment

Extend the existing M0 tracefile Oracle corpus with one complete, deterministic
numeric/error/checksum evidence module. Close the exact executable mappings for:

- `M1-TF-030`: numeric atoms, semantic values, categories, thresholds, and
  rewrite bytes;
- `M1-TF-031`: nonnumeric/malformed-exponent counts and format-ignore behavior;
- `M1-TF-032`: negative counts, negative zero, continuation, and model values;
- `M1-TF-033`: excessive-count threshold and suppression behavior;
- `M1-TF-034`: zero/invalid line and start/end fields;
- `M1-TF-035`: checksum presence, mismatch, duplicate, recomputation, and
  version-ignore behavior;
- `M1-TF-036`: default stop, ignore-errors, keep-going/stop-on-error, stream,
  exit, and output effects.

This is an upstream Oracle and contract task only. Do not implement the Rust
tracefile parser, change product crates, add Ferricov product evidence, or claim
M1 readiness.

## Required Coverage

Use targeted probes first, then deterministic fixtures and one final full Oracle
capture. Cover the numeric families that the existing grammar names (`DA`,
`FNDA`, `FNA`, `BRDA`, and `MCDC`) across accepted, rejected, coerced, ignored,
negative, excessive, zero, and malformed-exponent inputs. Include checksum and
version-ignore interactions, and prove exact file/stream/exit behavior for each
error policy. Successful model-shaping cases need semantic snapshots where the
existing inspector boundary can represent the result; writer-sensitive cases
need canonical rewrite evidence.

## Contract Invariants

- Pinned Oracle identity remains LCOV 2.5 source commit
  `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` and the recorded immutable image.
- Every fixture/case/observation is bound by exact path, bytes, SHA-256, argv,
  exit, raw streams, and output-file identity.
- Structured `requirement_ids` are required for an assigned ID only when the
  captured cases satisfy that requirement's complete evidence boundary. If a
  required matrix or semantic proof is still missing, the controller must keep
  the ID unmapped and record the residual gap rather than promote partial
  Oracle observations.
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
