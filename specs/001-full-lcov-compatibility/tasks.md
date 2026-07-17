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

- [ ] Add classification and source-reference fields to inventory entries.
- [ ] Review every command option and remove extraction false positives.
- [ ] Inventory short options and positional argument forms.
- [ ] Review all 130 `lcovrc` candidates and configuration precedence rules.
- [ ] Inventory environment variables and configuration discovery paths.
- [ ] Inventory every tracefile record and malformed-input behavior.
- [ ] Inventory error/warning classes, exit status, ignore, and keep-going rules.
- [ ] Inventory callbacks, support scripts, installation layout, and assets.
- [ ] Map all 205 upstream test files to public behaviors or internal coverage.
- [ ] Define high-risk option and configuration interaction groups.
- [ ] Write the callback/runtime ADR.
- [ ] Write the initial compiler/platform matrix ADR.

## M0 Next: Week 2 Baselines And M1 Readiness

- [ ] Generate formal startup/help/version/invalid-option suites.
- [ ] Generate configuration precedence suites.
- [ ] Build representative tracefile fixtures from upstream and real projects.
- [ ] Add user CPU, system CPU, and peak RSS measurement.
- [ ] Capture upstream correctness baselines.
- [ ] Capture startup, tracefile, operation, and report performance baselines.
- [ ] Specify the byte-preserving coverage model.
- [ ] Specify the complete LCOV 2.5 tracefile grammar.
- [ ] Define parse/write algebra and property tests.
- [ ] Define parser fuzz targets and resource limits.
- [ ] Define M1 benchmark sizes and performance gates.
- [ ] Run the M0 go/no-go review.

## M1 Ready When

- [ ] No candidate inventory entry remains unclassified.
- [ ] Every public behavior has a planned case group.
- [ ] Callback/runtime and compiler-matrix decisions are accepted.
- [ ] Upstream baselines are reproducible from a clean checkout.
- [ ] The coverage model specification represents every inventoried record.

Later milestone task breakdowns are opened before their milestone starts. The
canonical scope, order, gates, and estimates remain in `plan.md`.
