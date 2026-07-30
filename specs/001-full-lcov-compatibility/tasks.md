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
  standalone fail-closed contract bound to 52 Oracle observations.
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
- [x] Prove two-build Oracle reproducibility and runtime-validate its execution manifest.
- [x] Write the callback/runtime ADR.
- [x] Write the initial compiler/platform matrix ADR.

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
15 reader matcher lines, all 18 writer emission lines, 36 retained fixtures,
and 21 per-record malformed fixtures. Its 52 Oracle observations are
reference-only. The 28 planned M1 tracefile IDs without exact executable
mappings remain blockers, so the complete grammar and M1 readiness tasks stay
open.

The separate diagnostics contract reviews all 32 shared classes, the complete
399-reference symbol closure, nine control rules, four unclassified failure
surfaces, and ten command exit policies. Its 51 retained observations are
reference-only; the `geninfo` startup observation is explicitly classified as
a read-only temporary-directory intercept. All 71 diagnostic and parallel
case IDs remain planned, so ignore-two, warning promotion, converter traps,
parallel behavior, and product compatibility remain open.

The separate installation contract binds all 321 retained tree entries to nine
exhaustive groups and 15 pinned source closures. It preserves 320
SHA-256-identified files, the exact legacy manpage symlink, canonical ordered
paths, and exact mode counts while recording that directory entries are absent
from the retained tree. All 13 installation cases remain planned. Four report
samples bind their output trees through sample metadata and retain the same
seven runtime assets as reference-only Oracle evidence; packaging and product
compatibility remain open.

The separate resource contract executes 13 controlled scale profiles against
the immutable Oracle with branch and MC/DC summaries enabled. Every profile
binds exact input shape, source-scoped coverage cardinality, expected stream
hashes and semantics, raw metrics, clean outcome, cleanup, and host/runtime
identity. The host-bounded Docker run is the only timeout observer; writable
storage retains canonical exact-input/raw-artifact/wrapper/deadline/cleanup
failure evidence, retention errors cannot bypass attempted cleanup, and
successful validation rejects extra entries and symlinks. All 13
retained profiles are accepted, but their timing and RSS are
single-run bounded observations rather than performance distributions. No
Ferricov limit or compatibility evidence is selected; `M1-MD-020`,
`M1-TF-063`, and `M1-TF-064` remain blocked.

Behavior planning covers all 531 public entries with primary plans. Sixty-nine
public primary plans are reviewed, including 40 CLI entries bound to 154 exact
suite cases while retaining planning-only evidence status. All four required
critical interaction domains now have reviewed members and reciprocal cases.
Eight configuration-semantic slices bind 67 exact cases and review six more
primary targets. The current M0 gate reports 462 gaps, all public entries
without reviewed primary cases.
The raw Oracle correctness baseline is complete and replayed, but it remains
reference-only evidence and does not unlock product parity.

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
- [ ] Define M1 benchmark sizes and performance gates.
- [ ] Run the M0 go/no-go review.

## M1 Ready When

- [x] No candidate inventory entry remains unclassified.
- [ ] Every public behavior has a planned case group.
- [ ] Callback/runtime and compiler-matrix decisions are accepted.
- [x] Upstream correctness and performance baselines are reproducible from a
  clean checkout; the independent 148-case correctness replay passes semantic
  comparison.
- [ ] The coverage model specification represents every inventoried record.

Later milestone task breakdowns are opened before their milestone starts. The
canonical scope, order, gates, and estimates remain in `plan.md`.
