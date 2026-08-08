# M0 Tracefile TF-045 Two-Write Review

Status: exact Oracle evidence accepted; product compatibility remains false

## Scope

The pinned LCOV v2.5 Oracle is commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` with the existing immutable image
and executable identities. This wave closes `M1-TF-045` only through four
independent two-write cases:

- `writer-fixedpoint.two-write`
- `writer-legacy.two-write`
- `writer-permissive.two-write`
- `writer-ignored-error.two-write`

The original single-write cases remain observational regression captures and
are not used as the exact two-write evidence.

## Capture Facts

Each case stores two independent Docker execution stages in one observation.
The first stage reads the committed fixture and writes `output.info`. The
second stage reads that actual first output and writes `output2.info`.

The capture binds, for each stage, argv, input name and SHA-256, exit status,
stdout/stderr identities, output identity, and the chain fact:

```text
stage2.input_sha256 == stage1.output.sha256
```

All four stage-1/stage-2 output pairs are byte-identical. Final bytes are
checked against the existing independent per-member semantic facts, and the
input-model-to-output validator is run against the first write. The stage-2
output model must equal the stage-1 output model.

The trace corpus now contains 140 fixtures and 279 observations. The prior
275 observations remain unchanged by object identity and order. A fresh pinned
Docker recapture of all four two-write cases matched the committed stage
observations.

## Fail-Closed Checks

The focused mutation suite rejects:

- missing any of the four two-write members;
- stage-order swaps or duplicated stages;
- broken stage-2 input/output chaining;
- output mutation with refreshed self-hashes;
- output semantic record loss, reordering, or field-byte mutation;
- missing `two_write` markers or stage identity fields;
- unexpected stage names, filenames, argv suffixes, exits, or outputs.

The generated trace contract records 43 exact M1 IDs and maps the four cases
to `M1-TF-045`. `product_compatibility_evidence=false` remains unchanged.
`M1-TF-063` and `M1-TF-064` remain blocked.

## Verification

- `compat/fixtures/m0-tracefiles/validate.py`: passed
- tracefile focused mutation tests: 52 passed
- tracefile contract tests: 22 passed
- diagnostics contract/tests: 206 observations, 56 passed
- behavior current validation/tests: 48 passed
