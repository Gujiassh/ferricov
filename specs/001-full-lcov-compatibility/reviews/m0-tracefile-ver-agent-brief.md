# M0 Tracefile VER Mapping Worker Brief

## Controller Decision

This is a bounded M0 Oracle-contract lane for `M1-TF-007` only. It must not
implement Ferricov tracefile parsing, change Rust product crates, add product
compatibility evidence, or authorize M1.

The accepted implementation model is `deepseek/deepseek-v4-pro`; it is an
implementation-only worker. The controller owns this brief, semantic review,
all SSoT/spec/README/CHANGELOG edits, commit, push, and final acceptance.

## Semantic Oracle

Bind the pinned LCOV 2.5 behavior to exact executable cases:

- repeated identical `VER` for one source is accepted and canonical output
  emits at most one version;
- a different second `VER` for the same source is an unconditional failure,
  not an ignorable `ERROR_VERSION` case;
- versions are scoped per source rather than globally, so separate sources may
  retain independent versions in one input;
- no claim may be made about Ferricov parity or product behavior.

The lane should add only the smallest fixtures needed for these invariants:
`ver-repeat-equal`, `ver-repeat-different`, and `ver-per-source`, plus a
canonical rewrite case for the accepted repeat-equal input. Use exact source
anchors already identified in the grammar/model (`U-VERSION` at
`lib/lcovutil.pm:6074-6084`, `U-READ-RECORDS-1` at `9068`, and writer `9511`),
and verify the actual pinned Oracle exit/status/streams rather than assuming
the prose.

## Worker-Owned Files

The worker may modify only the following implementation/evidence surface:

- `compat/fixtures/m0-tracefiles/generate.py`
- generated `compat/fixtures/m0-tracefiles/fixtures/ver/*.info`
- generated `compat/fixtures/m0-tracefiles/manifest.json`
- generated `compat/fixtures/m0-tracefiles/oracle-cases.json`
- regenerated `compat/fixtures/m0-tracefiles/oracle-baseline.json`
- `compat/fixtures/m0-tracefiles/validate.py`
- `compat/tracefile/contract.py`
- regenerated `compat/tracefile/v2.5.json`
- `compat/tracefile/test_contract.py`

The worker must not modify this brief, other review/spec/SSoT files, README,
CHANGELOG, `compat/verify.py`, schemas, Rust code, or git history. Do not stage,
commit, or push. Do not change retained existing case IDs or raw observations.
If the desired behavior needs another boundary, stop and report it.

## Required Gates Before Handoff

```sh
python3 compat/fixtures/m0-tracefiles/generate.py
python3 compat/fixtures/m0-tracefiles/capture_oracle.py --image sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e
python3 compat/fixtures/m0-tracefiles/validate.py
python3 compat/tracefile/contract.py --upstream-root /home/cc/code1/lcov-upstream-reference --write
python3 -m unittest compat.tracefile.test_contract
python3 compat/verify.py --skip-oracle
python3 -m unittest compat.behavior.test_validate
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current

git diff --check
```

The expected contract delta is: fixtures `39 -> 42`, Oracle cases `59 -> 63`
(or a smaller count only if a documented, evidence-backed case consolidation
is necessary), exact executable requirement IDs `3 -> 4` by adding only
`M1-TF-007`, and unmapped M1 IDs `25 -> 24`. All existing fixture/case hashes
must remain unchanged except for generated manifest/cases/baseline closure
hashes caused by the new cases. Product evidence remains false/empty.

## Stop Conditions

Stop without editing if Docker/image identity is unavailable, if the pinned
Oracle produces an outcome that contradicts the semantic oracle and needs a
new model decision, if the lane requires `M1-TF-023` repeated-section behavior,
or if any existing evidence is rewritten beyond the new VER cases. Return the
exact command failure, files touched, and unresolved decision.
