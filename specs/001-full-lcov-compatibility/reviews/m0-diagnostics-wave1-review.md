# M0 Diagnostics Wave1 Review Note

## Scope

Lane-owned diagnostics/parallel wave1 closed a bounded Oracle-reference batch
under `compat/diagnostics/**` only. No Ferricov parser/model, shared tasks,
README root, SSoT, tracefile fixtures, behavior, or installation trees were
modified.

## Delivered

- 25 Docker-captured Oracle observations on pinned image
  `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
  and upstream `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`.
- Durable capture script: `compat/diagnostics/wave1/scripts/capture_wave1.py`.
- Contract bindings and schema expansion so observations become part of the
  fail-closed diagnostics inventory.
- Mutation tests covering wave1 identity, geninfo true no-args versus intercept
  separation, ignore-two, promotion, and product-evidence rejection.

## Planned cases with wave1 reference bindings

19 planned identities received at least one exact Oracle reference:

- `DIAG-NOARGS-GENINFO-001`
- `DIAG-IGNORE-ERROR-001`
- `DIAG-IGNORE-WARN-001`
- `DIAG-IGNORE-SILENT-001`
- `DIAG-KEEP-GOING-001`
- `DIAG-IGNORE-UNKNOWN-001`
- `DIAG-IGNORE-PRECEDENCE-001`
- `DIAG-WARNING-PROMOTE-001`
- `DIAG-MAX-MESSAGES-001`
- `DIAG-EXPECTED-COUNT-FILE-001`
- `DIAG-EXPECTED-COUNT-MANUAL-FILE-001`
- `DIAG-EXPECTED-COUNT-MANUAL-RC-001`
- `DIAG-MESSAGE-LOG-001`
- `DIAG-PERL2LCOV-KEEP-001`
- `DIAG-LLVM2LCOV-KEEP-001`
- `DIAG-PY2LCOV-KEEP-001`
- `DIAG-XML2LCOV-KEEP-001`
- `DIAG-CONVERTER-KEEP-BOUNDARY-001`
- `PAR-SERIAL-PARITY-001`

## Contract totals after wave1

- planned cases: 71 (still `planned`; no product evidence)
- oracle observations: 146 total
  - 121 historical correctness/tracefile references
  - 25 wave1 diagnostics references
- product_compatibility_evidence: false

## Explicit residual gaps

Wave1 does not close the full 71-case suite. Remaining open gaps include:

- parallel worker failure, signals, payload corruption, parent death;
- forced-parallel and callback lifecycle failure matrix;
- environment discovery / POSIX singular-ignore profile matrix;
- callback finalize/cleanup diagnostics;
- converter keep-going success paths with real conversion inputs;
- remaining no-args/parser/env cases not selected for this wave.

## Evidence policy

All wave1 results remain `oracle_reference` only. They must not be promoted to
Ferricov product compatibility without a later differential against a distinct
Ferricov executable.
