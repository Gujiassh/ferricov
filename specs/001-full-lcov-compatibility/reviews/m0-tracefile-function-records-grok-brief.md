# M0 Tracefile Function-Record Oracle Slice: Grok 4.5 Brief

## Assignment

Implement one coherent M0 Oracle-evidence slice for the LCOV 2.5 function-record
behavior family. Close the exact executable mappings for these planned M1 case
identities:

- `M1-TF-009`: current `FNL`/`FNA` records;
- `M1-TF-011`: mixed current and legacy function records;
- `M1-TF-024`: function index scope and hard failures.

This is an upstream Oracle and contract task. It does not authorize the Rust
tracefile parser/model, start M1, or create Ferricov product evidence.

## Required Behavior Coverage

Use exact deterministic input bytes and the pinned LCOV 2.5 executable to settle
the behavior. Do not infer expected outcomes from the prose below when the
Oracle can answer them.

### `M1-TF-009`

Cover current `FNL`/`FNA` behavior for:

- `FNL` with and without an end line;
- multiple aliases, including comma-bearing alias text;
- repeated aliases;
- a missing alias field;
- noncontiguous alias indices;
- zero start/end lines where accepted or rejected by the Oracle.

### `M1-TF-011`

Cover current `FNL`/`FNA` and legacy `FN`/`FNDA` records sharing function names
and locations, including:

- compatible records that merge;
- location or range mismatches;
- count mismatches or accumulation behavior;
- the resulting semantic model and canonical rewrite for successful inputs;
- exact diagnostic, exit, and output-file behavior for failures.

### `M1-TF-024`

Cover:

- the scope and lifetime of `FNL` indices;
- duplicate `FNL` indices;
- `FNA` references to unknown indices;
- whether a new test or source section resets, preserves, or conflicts with the
  index map;
- exact hard-failure timing, diagnostics, exit status, and output-file effects.

## Semantic Oracle

The accepted implementation must preserve these invariants:

1. Oracle identity remains LCOV 2.5 at source commit
   `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`, using the content-identified
   Docker image and executable already recorded by the repository.
2. Every fixture is deterministically generated and bound by path, SHA-256,
   byte size, and record metadata.
3. Every new Oracle case records exact argv, fixture identity, exit status,
   stdout, stderr, output-file state, and raw byte identities.
4. Successful model-shaping cases include an independently reviewable semantic
   snapshot through the existing `inspect_model.pl` boundary and a canonical
   rewrite where writing behavior is relevant.
5. Failure cases retain exact diagnostics and prove whether an output file is
   absent, empty, partial, or complete. A nonzero exit alone is insufficient.
6. Exact executable mappings use structured `requirement_ids`; legacy free-form
   `requirement` text is not evidence.
7. Contract validation fails closed on missing, duplicate, reordered, swapped,
   stale, or semantically inconsistent fixture/case/observation bindings.
8. The generated tracefile contract must add exactly the three assigned M1 IDs
   to `exact_executable_requirement_ids`; unrelated blocker status must not be
   promoted.
9. All Oracle references remain reference-only. Product evidence stays empty,
   product compatibility stays false, and M1 stays blocked.

## Expected Scope

Prefer the existing tracefile corpus architecture. The likely owned files are:

- `compat/fixtures/m0-tracefiles/fixtures/functions/*`;
- `compat/fixtures/m0-tracefiles/generate.py`;
- `compat/fixtures/m0-tracefiles/manifest.json`;
- `compat/fixtures/m0-tracefiles/oracle-cases.json`;
- `compat/fixtures/m0-tracefiles/oracle-baseline.json`;
- `compat/fixtures/m0-tracefiles/validate.py`;
- `compat/fixtures/m0-tracefiles/README.md`;
- `compat/tracefile/contract.py`;
- `compat/tracefile/test_contract.py`;
- `compat/tracefile/v2.5.json`;
- relevant English SSoT/spec/task documentation.

Add a small helper only when it removes real complexity or is required to make
the semantic snapshot complete. Do not introduce a second contract format,
change shared schemas, refactor unrelated tracefile families, or touch Rust
product crates.

## Work Sequence

1. Audit the existing corpus, function snapshot representation, source anchors,
   and relevant pinned upstream tests/code before editing.
2. Define the smallest fixture matrix that covers every required behavior
   without combining unrelated uncertainties into opaque mega-fixtures.
3. Run targeted Oracle probes to discover exact outcomes.
4. Implement deterministic generation, case definitions, validation, contract
   mappings, mutation tests, and synchronized English documentation.
5. Stabilize all local generation and contract tests before the expensive run.
6. Perform one final complete Oracle capture after the case set is stable, then
   validate the retained baseline and generated contract.

Do not repeatedly rerun an unchanged full Oracle capture after a timeout or
environment failure. Diagnose the constraint first. Targeted probes and one
final full capture are expected.

## Verification

Run all relevant repository-native checks, including at minimum:

- deterministic corpus regeneration/currentness;
- tracefile fixture validation;
- tracefile contract unit and reverse-mutation tests;
- `python3 compat/verify.py --skip-oracle`;
- repository Python compilation/tests affected by the change;
- Rust format, check, workspace tests, and clippy gates;
- `git diff --check`;
- the final pinned Docker Oracle capture and post-capture validation.

Record exact commands and results. Tests must prove behavior and binding
integrity, not merely execute implementation branches.

## Delivery Rules

- Work only in `/home/cc/code1/ferricov`.
- Repository documentation and commit-style text must be English.
- Do not commit or push.
- Do not create project-local agent/session artifact directories.
- Do not claim controller acceptance in repository documentation.
- Finish the complete slice before returning. Report changed files, observed
  Oracle decisions, verification evidence, and unresolved risks truthfully.
