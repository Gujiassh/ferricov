# M0 Coverage-Model Algebra Contract Review Note

## Scope

This note records the M0 Oracle coverage-model algebra/property evidence lane
for pinned LCOV v2.5 commit `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` and
image `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`.

It binds unbound Oracle-side rows:

- `M1-MD-010` line algebra
- `M1-MD-011` function algebra (including representative selection)
- `M1-MD-012` branch algebra (including cache/expression paths)
- `M1-MD-013` MC/DC algebra (including expression and vector-width cases)
- `M1-MD-014` left-only / right-only testcase algebra across families
- `M1-MD-017` parse-write-parse equality (current/legacy/permissive)
- `M1-MD-019` repeated close / terminator lifecycle probes

Blocked and unchanged:

- `M1-MD-020`
- `M1-TF-063`
- `M1-TF-064`
- Rust parser/model product work
- `product_compatibility_evidence=false`

## Owned Artifacts

- `compat/fixtures/m0-algebra/**` fixtures, generator, inspector, capture,
  validate, reverse mutation tests, cases, baseline, expected facts
- `compat/model/v2.5.json` contract
- `compat/model/m1-model.json` executable catalog
- `compat/schema/model-contract.schema.json`
- `compat/verify.py` wiring for model schema/contract/corpus checks

## Intentional Rejected-Case Semantics

`M1-ALG-MCDC-VECTOR-001` uses asymmetric vector widths:

- long-then-short `union` / `intersect` hard-fail with
  `Can't call method "expression" on an undefined value`
  - CLI exit `1`
  - semantic/in-process exit `255`
  - no output file
- reverse order (`union-rev` / `intersect-rev`) succeeds
- `difference` / `difference-rev` succeed

These are retained Oracle hard-error observations, not harness failures and not
product-compatibility claims.

## Evidence Binding Rules

Acceptance is fail-closed and multi-binding:

1. pinned image id and `lcov` executable SHA-256
2. committed fixture bytes and case argv
3. raw stdout/stderr/output identities
4. independent expected facts (not baseline self-hash alone)
5. reverse mutation tests for hash, argv, exit, operand, blocked-id, and
   rejected-case wash attempts

## Residual Risks

- Remaining model rows (`M1-MD-001`..`009`, `015`, `016`, `018`) are outside this
  lane and remain unbound or owned by other contracts.
- No Ferricov parity phase exists yet; all `ferricov_parity_status` values stay
  blocked.
- Adversarial fuzz execution remains M1-only.
