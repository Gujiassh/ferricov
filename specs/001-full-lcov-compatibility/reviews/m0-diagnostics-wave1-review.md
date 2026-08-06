# M0 Diagnostics Wave1 Review Note

## Scope

Lane-owned diagnostics/parallel wave1 closed a bounded Oracle-reference batch
under `compat/diagnostics/**` plus this lane review note. No Ferricov
parser/model, shared tasks, root README, SSoT, tracefile fixtures, behavior, or
installation trees were modified.

## Fail-closed repair

Independent review rejected the initial wave1 binding as fail-open because
validation largely trusted index/result self-hashes. The repair adds:

1. Independent expected-case identity for all 26 observations / 19 planned IDs
   (`WAVE1_EXPECTED_CASES`, `WAVE1_EXPECTED_PLANNED_IDS`).
2. Exact ordered ID-set checks for index and contract observations.
3. Per-case image/upstream/argv/fixture/exit/timeout/cleanup/environment
   identity checks against the independent table.
4. Recomputation of stdout/stderr hashes from committed `reference/*.bin`
   artifacts and recomputation of workspace file-tree bytes/hashes from the
   case directory.
5. Explicit file-tree semantics: `workspace_including_inputs`.
6. Capture/validation of timeout (`30s`), cleanup policy, and execution
   environment identity.
7. Replacement of no-input converter boundary records with real conversion-input
   keep-going cases plus a separate structural boundary case.
8. Reverse mutations for raw stdout/stderr, file-tree content, nested metadata,
   converter identity, and index order.

## Delivered

- 26 Docker-captured Oracle observations on pinned image
  `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
  and upstream `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`.
- Durable capture script: `compat/diagnostics/wave1/scripts/capture_wave1.py`.
- Contract bindings and schema expansion for fail-closed diagnostics inventory.
- Mutation tests covering reverse refresh attacks.

## Planned cases with wave1 reference bindings (19)

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
- `DIAG-PERL2LCOV-KEEP-001` (empty cover_db input, exit 0)
- `DIAG-LLVM2LCOV-KEEP-001` (real llvm JSON export, exit 0)
- `DIAG-PY2LCOV-KEEP-001` (real Coverage XML, exit 0)
- `DIAG-XML2LCOV-KEEP-001` (real Coverage XML, exit 0)
- `DIAG-CONVERTER-KEEP-BOUNDARY-001` (broken XML missing sources, exit 1)
- `PAR-SERIAL-PARITY-001`

## Contract totals after repair

- planned cases: 71 (still `planned`; no product evidence)
- oracle observations: 147 total
  - 121 historical correctness/tracefile references
  - 26 wave1 diagnostics references
- product_compatibility_evidence: false
- oracle_observation_evidence_status: oracle_reference

## Explicit residual gaps

- parallel worker failure, signals, payload corruption, parent death
- forced-parallel and callback lifecycle failure matrix
- environment discovery / POSIX singular-ignore profile matrix
- callback finalize/cleanup diagnostics
- richer multi-error converter corpora beyond the current keep-going traps
- remaining 52 planned identities without wave1 executable bindings

## Evidence policy

All wave1 results remain `oracle_reference` only. They must not be promoted to
Ferricov product compatibility without a later differential against a distinct
Ferricov executable.
