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
- [ ] Plan configuration discovery and precedence behavior.
- [ ] Inventory environment variables and configuration discovery paths.
- [ ] Inventory every tracefile record and malformed-input behavior.
- [ ] Inventory error/warning classes, exit status, ignore, and keep-going rules.
- [x] Review all 23 installed support scripts and callback planning subjects.
- [ ] Complete installation-layout and asset behavior planning.
- [x] Map all 205 upstream test files to public behaviors or internal coverage.
- [x] Define the four required critical interaction groups with reciprocal cases.
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

Behavior planning covers all 531 public entries with primary case skeletons,
but only 23 public primary plans are reviewed. All four required critical
interaction domains now have reviewed members and reciprocal cases. The current
M0 gate reports 508 gaps, all public entries without reviewed primary cases.
The raw Oracle correctness baseline is complete and replayed, but it remains
reference-only evidence and does not unlock product parity.

## M0 Next: Week 2 Baselines And M1 Readiness

- [x] Generate formal startup/help/version/invalid-option suites.
- [ ] Generate configuration precedence suites.
- [ ] Build representative tracefile fixtures from upstream and real projects.
- [ ] Add user CPU, system CPU, and peak RSS measurement.
- [x] Capture and retain the 126-case upstream CLI correctness baseline with
  immutable image/executable identities and raw artifact validation.
- [x] Capture and retain startup, tracefile, operation, and report Oracle performance baselines.
- [ ] Specify the byte-preserving coverage model.
- [ ] Specify the complete LCOV 2.5 tracefile grammar.
- [ ] Define parse/write algebra and property tests.
- [ ] Define parser fuzz targets and resource limits.
- [ ] Define M1 benchmark sizes and performance gates.
- [ ] Run the M0 go/no-go review.

## M1 Ready When

- [x] No candidate inventory entry remains unclassified.
- [ ] Every public behavior has a planned case group.
- [ ] Callback/runtime and compiler-matrix decisions are accepted.
- [x] Upstream correctness and performance baselines are reproducible from a
  clean checkout; the independent 126-case correctness replay passes semantic
  comparison.
- [ ] The coverage model specification represents every inventoried record.

Later milestone task breakdowns are opened before their milestone starts. The
canonical scope, order, gates, and estimates remain in `plan.md`.
