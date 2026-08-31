# Tasks

## Milestone Status

| Milestone | Status | Release |
| --- | --- | --- |
| M0 Executable Contract | in progress | internal |
| M1 Tracefile Core | pending | v0.1 |
| M2 `lcov` Manipulation | pending | v0.2 |
| M3 Complete `genhtml` | pending | v0.3 |
| M4 Complete Capture | pending | v0.4 |
| M5 Complete Installed Suite | pending | v0.5 |
| M6 Qualified Replacement | pending | v1.0 |

## M0 Completed

- [x] Pin LCOV 2.5 tag and commit.
- [x] Record public compatibility and performance contracts.
- [x] Create initial Rust workspace boundaries.
- [x] Build and verify the pinned upstream Oracle image.
- [x] Generate the first CLI/config/install candidate inventory.
- [x] Define Suite, Launcher, and differential Result schemas.
- [x] Define and review the initial normalization registry.
- [x] Implement isolated differential execution and artifact capture.
- [x] Verify the harness with positive and intentional reverse cases.
- [x] Define the milestone, release, risk, and quality-gate plan.

## M0 Residual Closure (multi-agent)

Baseline: `fa6820c`+ · gaps 38 · plan: `reviews/m0-residual-multi-agent-plan.md` · standards: `reviews/m0-residual-execution-standards.md`

- [x] S0 independent Critical audit of residual multi-agent spec package (ACCEPT @5a769cb re-audit)
- [x] S1–S3 residual multi-lane program: 31 sealed, 7 honest blocked; metrics 524/7
- [x] S4 residual integration push (`d7420f1`)
- [x] S5 residual signed N/A closeout + Critical audit (`m0-residual-s5-signed-na.md`, `m0-residual-s5-audit.md`)
- [x] Residual multi-agent program S0–S5 closed (31 sealed + 7 signed N/A) @ `206d412`
- [x] Residual lane worktrees A–F removed; origin residual branches retained
- [x] Diagnostics wave3: bind Oracle-capable unbound PAR-* IDs (`m0-diagnostics-wave3-plan.md`, multi-agent plan)
- [x] Wave3 S1: two lane worktrees from integration SHA `206d412` (A geninfo-child, B fault injectors)
- [x] Wave3 S2: Lane A + Lane B capture and Critical audits (ACCEPT_WITH_NOTES)
- [x] Wave3 S3: controller merge, contract hooks, status regenerate, review
- [x] Wave3 S4: push integration + hosted CI (run 32018428585)
- [x] Wave3 S5 program close note when CI green (FERRICOV residual floor remains 3)

- [x] Lane A CLI hard (1 sealed / 3 blocked) — brief `m0-residual-lane-A-cli-hard-brief.md`
- [x] Lane B language extensions (4 sealed / 1 blocked) — `m0-residual-lane-B-lang-ext-brief.md`
- [x] Lane C filters (3) — `m0-residual-lane-C-filters-brief.md`
- [x] Lane D geninfo success (6 sealed / 3 blocked) — `m0-residual-lane-D-geninfo-success-brief.md`
- [x] Lane E parallel/fork (6) — `m0-residual-lane-E-parallel-brief.md`
- [x] Lane F misc (11) — `m0-residual-lane-F-misc-brief.md`
- [x] Controller serial merge + regenerate pin after each lane
- [x] M0 go/no-go artifact written (`m0-go-no-go.md`) — 2026-08-17 **NO-GO** superseded by 2026-08-18 **conditional GO**
- [x] Model blockers scoped (`reviews/m0-model-blocker-scope.md`) without clearing `blocked_case_ids`
- [x] Wave3 worktrees removed; origin lane branches retained
- [x] M1 v0.1 support matrix ACTIVE (`m1-v0.1-support-matrix.md`) with exclusions A–D
- [x] Conditional GO wired: `m1_authorized=true`, `product_compatibility_evidence=false`
- [ ] Post-v0.1: clear residual/model/product exclusions or revise matrix (see support matrix)

## M0 Current: Week 1 Contract Completion

- [x] Add classification and source-reference fields to inventory entries.
- [x] Review every command option and remove extraction false positives.
- [x] Inventory explicit short aliases and parser-backed positional argument forms.
- [x] Record parser policies and observed generated-token resolution for all commands.
- [x] Review all 158 `lcovrc` candidates.
- [x] Plan configuration discovery and precedence behavior.
- [x] Inventory all 19 named environment variables, the dynamic configuration
  input, five discovery paths, and all 36 direct `$ENV` source lines in a
  standalone fail-closed contract.
- [x] Inventory all 20 tracefile record tags, two lexical rules, the complete
  reader/writer source closures, and all 21 per-record malformed fixtures in a
  standalone fail-closed contract bound to 279 Oracle observations.
- [x] Inventory all 32 shared error/warning classes, 399 symbol references,
  nine ignore/keep-going controls, four unclassified surfaces, and ten command
  exit policies in a standalone fail-closed contract.
- [x] Review all 23 installed support scripts and callback planning subjects.
- [x] Bind the complete 321-entry installed tree to nine payload groups and 15
  source closures, and retain 13 planned installation cases plus four
  seven-asset Oracle observations in a standalone fail-closed contract.
- [x] Map all 205 upstream test files to public behaviors or internal coverage.
- [x] Define the four required critical interaction groups with reciprocal cases.
- [x] Review the 40 public CLI primary entries exercised by the retained M0
  contract and bind their 154 exact suite cases without claiming product evidence.
- [x] Review six command-owned `genhtml` CLI-output options and bind one shared
  control plus six exact target cases without claiming product evidence.
- [x] Review three command-owned `genhtml` metric/layout options (`--frames`,
  `--precision 4`, and `--no-sort`) with two clean pinned Oracle runs and no
  product evidence.
- [x] Review the four retained-corpus `lcov` tracefile CLI primary targets while
  keeping Oracle references out of product evidence and compatibility suites.
- [x] Prove two-build Oracle reproducibility and runtime-validate its execution manifest.
- [x] Write the callback/runtime ADR.
- [x] Write the initial compiler/platform matrix ADR.

- [x] Review three residual genhtml command surfaces (`--preserve`,
  `--synthesize-missing`, and multi-tracefile positional inputs) with two clean
  pinned Oracle runs and no product evidence.

Current contract metrics: all 584 inventory entries and all 205 upstream test
mappings are reviewed. The inventory contains 394 command candidates, 9
positional forms, 158 configuration entries, and 23 support scripts. Command
review classifies 346 options as public, 41 as generated tokens, and 7 as
internal. The default profile resolves 9 generated tokens as unique
abbreviations, rejects 2 as ambiguous, and rejects 30 as unknown; the POSIX
profile rejects all 41 as unknown. These are pinned-Oracle observations and do
not count as product evidence.

The separate environment contract reviews 19 named variables, one dynamic
configuration expansion input, five configuration-discovery paths, and the
complete 36-line direct `$ENV` source closure. Its 22 bindings point to retained
Oracle cases only; all product evidence remains empty and the inventory schema
is unchanged.

The separate tracefile contract reviews 20 record tags, two lexical rules, all
15 reader matcher lines, all 18 writer emission lines, 140 retained fixtures,
and 21 per-record malformed fixtures. Its 279 Oracle observations are
reference-only. Exact legacy/writer mappings now cover 26 cases for
`M1-TF-010`, `M1-TF-041..045`, `046`, `050..052`, `060`, and `061`; the four
TF-045 members now have true chained two-write Docker evidence. `M1-TF-063`
and `064` remain blocked. Product compatibility evidence remains false and M1
implementation remains unauthorized.

The TF-030 exact numeric matrix module defined in
`reviews/m0-tf030-exact-numeric-matrix-agent-brief.md` has been implemented on
branch `test/m0-tf030-exact-numeric-matrix`. It preserved `main@6a9a85d` as the
169-observation comparison base (common=169, changed=0, removed=0, added=15),
split the numeric corpus modules, added the complete 56-row matrix, and
synchronized generated contracts. A first controller pass added a six-snapshot
semantic registry and all-row/cache mutation coverage, but the subsequent
independent Critical audit found fail-open observation-byte, closed-JSON, and
direct-upstream-provenance gaps. The audit rework is specified in
`reviews/m0-tf030-audit-rework-spec.md`; M1 remains blocked.

The separate diagnostics contract reviews all 32 shared classes, the complete
399-reference symbol closure, nine control rules, four unclassified failure
surfaces, and ten command exit policies. Its 206 retained observations are
reference-only; the previous 204 observations remain unchanged and two legacy
unknown-function fatal references are added. Fifty-nine of 71 diagnostic and
parallel case IDs have exact bindings; the remaining 12 stay planned and
unbound, and product compatibility remains open.

The separate installation contract binds all 321 retained tree entries to nine
exhaustive groups and 15 pinned source closures. It preserves 320
SHA-256-identified files, the exact legacy manpage symlink, canonical ordered
paths, exact mode counts, and a separate 57-entry directory/mode companion.
Wave2 retains replayable pinned-Docker envelopes for all 13 planned cases,
both relative/space PATH parts, complete tree rows, observed clean env and live
process provenance, timeout/signal/cleanup facts, and two runner qualifications.
All cases remain Oracle reference-only and planned; packaging, installer
implementation, and product compatibility remain open.

The separate resource contract executes 13 controlled scale profiles against
the immutable Oracle with branch and MC/DC summaries enabled. Every profile
binds exact input shape, source-scoped coverage cardinality, expected stream
hashes and semantics, raw metrics, clean outcome, cleanup, and host/runtime
identity. The host-bounded Docker run is the only timeout observer; writable
storage retains canonical exact-input/raw-artifact/wrapper/deadline/cleanup
failure evidence, retention errors cannot bypass attempted cleanup, and
successful validation rejects extra entries and symlinks. The canonical result
remains bound to historical `sha256:b02cc645...56eb80b7`; the CI-only adapter
resolves the closure-verified rebuilt alias to that job's immutable ID and
validates all 13 ordered samples without emitting `result.json`. All 13
retained profiles are accepted, but their timing and RSS are
single-run bounded observations rather than performance distributions. No
Ferricov limit or compatibility evidence is selected; `M1-MD-020`,
`M1-TF-063`, and `M1-TF-064` remain blocked.

Behavior planning covers all 531 public entries with primary plans. Live
residual metrics are owned by `docs/ssot/m0-status.snapshot.json` (live residual metrics in `docs/ssot/m0-status.snapshot.json`). Forty CLI
entries bind 154 exact suite cases, eight base configuration slices bind 67
cases, three support-script entries bind executable planning cases, and
thirty-two command entries bind six command-owned `genhtml` CLI-output cases,
three command-owned metric/layout cases, plus `gendesc`, `py2lcov`, `genpng`, `llvm2lcov`,
`perl2lcov`, and trace-operation `lcov` cases. Separately, 32 `lcovrc`
consumer plans bind two list-format cases and thirty fixed-epoch `genhtml`
output/layout, metric-config, and report/differential cases. Owner and age field widths remain
deferred pending annotation/date inputs. The true `perl2lcov --preserve` parallel path remains
unbound because it retains a randomized temp tree without an approved
normalizer. The tracefile and `lcovrc` slices remain planning-only. Product evidence stays
empty and the current M0 readiness gate remains blocked. The raw Oracle
correctness baseline is complete and replayed, but remains reference-only and
does not unlock product parity.

## M0 TF-030 Audit Rework

- [x] Add independently contract-bound TF-030 stdout/stderr/output/exit
  observation facts and reject refreshed self-hashes.
- [x] Reject unknown semantic JSON keys and escaped duplicate numeric-plan keys.
- [x] Bind `fixtures/numeric/format-atoms.info` directly to the pinned upstream
  `tests/lcov/format/format.info` bytes.
- [x] Remove the committed EOF whitespace and pass
  `git diff --check origin/main...HEAD`.
- [x] Re-run Oracle, contract, Rust, Perl, and mutation gates for the audit rework.
- [x] Enforce type-sensitive JSON equality for TF-030 observation and
  semantic registry comparisons (reject int/bool/float cross-type).
- [x] Pin deterministic TF-030 Perl environment (`PERL_HASH_SEED=0`,
  `PERL_PERTURB_KEYS=0`) on case defs, capture, observations, and registry.
- [x] Harden TF-030 selective `--merge-into` against untrusted retained baseline
  copies (canonical path + fixed baseline SHA-256 + exact 15 TF-030 ids).
- [x] Move TF-030 `--merge-into` validation before Docker inspect and bind
  merge parse to trusted baseline bytes; preserve ordered duplicate-free
  `--case-id` selection.
- [x] Sixth independent Critical audit completed: TF-030 M0 Oracle evidence
  closure accepted; product compatibility remains false and M1 remains blocked.

## M0 Next: Week 2 Baselines And M1 Readiness

- [x] Generate formal startup/help/version/invalid-option suites.
- [x] Generate configuration precedence suites.
- [ ] Build representative tracefile fixtures from upstream and real projects.
- [x] Add user CPU, system CPU, and peak RSS measurement.
- [x] Capture and retain the 148-case upstream CLI/configuration correctness baseline with
  immutable image/executable identities and raw artifact validation.
- [x] Capture and retain startup, tracefile, operation, and report Oracle performance baselines.
- [ ] Specify the byte-preserving coverage model.
- [ ] Specify the complete LCOV 2.5 tracefile grammar.
- [ ] Define parse/write algebra and property tests.
- [x] Define named parser fuzz targets, harness safety budgets, and the exact
  M0 resource-measurement profiles without selecting product limits.
- [x] Capture and retain the 13-profile immutable-Oracle resource observation
  with source-scoped input semantics, branch/MC/DC summaries, raw single-run
  metrics, host/runtime identity, host-deadline provenance, writable-storage
  failure diagnostics, retention-error cleanup, exact successful-tree closure,
  and fail-closed cleanup.
- [x] Add a non-retained CI exercise for closure-equivalent rebuilt Oracle
  images that resolves the job-local alias once, rechecks the LCOV executable
  identity, and validates exact ordered samples-only output without changing
  canonical evidence.
- [ ] Define M1 benchmark sizes and performance gates.
- [x] Run the M0 go/no-go review (`m0-go-no-go.md`; historical NO-GO review `reviews/m0-exit-go-no-go-review.md`; conditional GO review `reviews/m0-exit-go-conditional-review.md`) — current result **GO (conditional)**.

## M1 Ready When

- [x] No candidate inventory entry remains unclassified.
- [ ] Every public behavior has a planned case group.
- [x] Callback/runtime and compiler-matrix decisions are accepted.
- [x] Upstream correctness and performance baselines are reproducible from a
  clean checkout; the independent 148-case correctness replay passes semantic
  comparison.
- [ ] The coverage model specification represents every inventoried record.

## M1 Tracefile Core Agent Breakdown (Activation-Gated)

The executable implementation handoff and acceptance matrix is
[`m1-tracefile-core-agent-spec.md`](m1-tracefile-core-agent-spec.md). Conditional
GO is active under [`m1-v0.1-support-matrix.md`](m1-v0.1-support-matrix.md):
`m1_authorized=true` for CORE-001…009 only. The agent MAY implement Rust
parser/model work inside `crates/model` + `crates/tracefile` for those tasks. CORE-009 is deterministic and budgeted. Do not hollow-close residuals, bind FERRICOV IDs with Oracle-only seals, flip product evidence, or start CORE-010/011.

Activation / exclusion ledger:

- [x] Explicit support-matrix exclusions for 7 signed-N/A gaps (A); `m0-ready` may still fail.
- [x] Explicitly scope `M1-MD-020`, `M1-TF-063`, and `M1-TF-064` (`reviews/m0-model-blocker-scope.md`); still blocked in contract; matrix exclusion C.
- [x] Approve coverage-model / tracefile-grammar for CORE-001…009 under conditional GO (blocked fuzz/product-limit rows remain open).
- [x] Record the M0 go/no-go decision (`m0-go-no-go.md` — **GO conditional**) + support matrix + snapshot wiring.
- [ ] Post-v0.1: resolve or revise exclusions A–D / product evidence for broader milestone claims.

Authorized now:

- [x] `M1-CORE-001`: implement byte/source/testcase/numeric primitives (`crates/model`; review `reviews/m1-core-001-controller-review.md`).
- [x] `M1-CORE-002`: implement independent aggregate and testcase-family stores (`crates/model`; review `reviews/m1-core-002-controller-review.md`).
- [x] `M1-CORE-003`: implement function, branch, and MC/DC invariants/indexes (`crates/model`; review `reviews/m1-core-003-controller-review.md`).
- [x] `M1-CORE-004`: implement ordered union/intersection/difference algebra (`crates/model` algebra.rs; review `reviews/m1-core-004-controller-review.md`; ALG Oracle binding residual).
- [x] `M1-CORE-005`: implement logical-line processing and parser state (`crates/tracefile`; review `reviews/m1-core-005-controller-review.md`).
- [x] `M1-CORE-006`: implement all record semantics, errors, and section commit (`crates/tracefile`; review `reviews/m1-core-006-controller-review.md`; ignore-matrix residual).
- [x] `M1-CORE-007`: implement deterministic canonical serialization (`crates/tracefile`; accepted Critical review at `6f04f44`; accepted-but-nonserializable classification remains owned by `M1-CORE-008`).
- [x] `M1-CORE-008`: implement semantic snapshots and equality (`crates/tracefile`; independent Critical review accepted at `11d4d1d`; focused gates: tracefile 61, model 48).

Authorized next:

- [ ] `M1-CORE-009`: implementation complete on `feat/m1-core-009-properties-fuzzing`; Critical review pending. Seven deterministic properties, nine bounded libFuzzer targets, permanent seed corpus, and hosted smoke integration are present. Blocked IDs remain open.

Still gated:

- [ ] `M1-CORE-010`: begin differential closure; product evidence stays false until case-by-case review.
- [ ] `M1-CORE-011`: run post-parity M1 performance qualification.

The worker may not widen the ownership boundary into CLI, `lcovrc`, reports,
capture, installation, callbacks, or release packaging. The controller owns
activation, review, commit, push, and milestone status changes.

Later milestone task breakdowns are opened before their milestone starts. The
canonical scope, order, gates, and estimates remain in `plan.md`.
