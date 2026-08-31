# M0 Tracefile Legacy Function TF-010 Review

Status: accepted Oracle evidence only

## Scope

This review records exact M1-TF-010 Oracle evidence against LCOV v2.5 commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`. It does not claim Ferricov
product compatibility or authorize a release.

## Evidence

The exact group binds six observations:

- `legacy.summary`: legacy parser acceptance and source-derived function totals
- `legacy.canonical`: optional-end handling and legacy-to-current FNL/FNA rewrite
- `writer-legacy-comma.canonical`: comma-bearing FN/FNDA name preservation
- `writer-legacy-repeat.canonical`: repeated FN deduplication and FNDA accumulation
- `writer-legacy-unknown.summary`: unknown-name mismatch/corrupt failure
- `writer-legacy-unknown.canonical`: failed write leaves output absent

Three new authored fixtures expand the retained trace corpus to 140 fixtures and
275 observations. A fresh pinned-Docker recapture reproduced all four new
observation objects byte-for-byte. The prior 271 observation objects and their
relative order remain unchanged.

Expected semantics are derived from fixture input facts. The validator does not
generate expected facts from captured output. It checks optional-end source
shape, current-form rewrite, comma-bearing names, repeated-definition
aggregation, diagnostic classes, exit status, and output absence.

## Reverse Review

The contract rejects:

- omission of either retained legacy parse/rewrite observation;
- omission of any new edge case;
- optional-end rewrite mutation with refreshed output identity;
- comma-bearing function-name mutation;
- repeated FNDA aggregate mutation;
- unknown-name diagnostic, exit, or output-existence drift;
- exact mapping, schema count, artifact hash, or product-evidence promotion.

## Verification

- `compat/fixtures/m0-tracefiles/validate.py`
- 52 tracefile fixture/mutation tests
- 22 tracefile contract tests
- diagnostics contract synchronized to 206 Oracle references; prior 204 objects
  unchanged and two legacy unknown-function fatal references added

`product_compatibility_evidence=false` remains unchanged. M1-TF-045,
M1-TF-063, and M1-TF-064 remain blocked at this review point.
