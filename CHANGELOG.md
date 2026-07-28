# Changelog

All notable changes to Ferricov are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Ferricov remains pre-alpha and does not yet publish replacement binaries or
compatibility releases.

## [Unreleased]

### Added

- A reviewed LCOV 2.5 executable-surface inventory with 584 entries covering
  command options, positional forms, `lcovrc` entries, and support scripts.
- Identity-bound review overlays and 82 default/POSIX generated-token Oracle
  observations.
- A complete reviewed map of all 205 pinned upstream test files.
- Behavior-planning contracts for all 531 public inventory entries, including
  explicit critical interaction domains and fail-closed M0 readiness checks.
- Reproducible Oracle build inputs, package and installed-tree locks, an
  execution-manifest schema, and a retained runtime-validated Oracle manifest.
- Oracle-only startup, tracefile, operation, and report benchmark contracts,
  measurement tooling, raw samples, and a retained four-family baseline.
- Normative M0 contracts for the coverage model, tracefile grammar,
  diagnostics, parallel execution, callbacks, installation, and upstream
  defect handling.

### Changed

- Split the Oracle inventory and differential harness into responsibility-based
  modules while preserving generated inventory and evidence semantics.
- Strengthened differential evidence with immutable executable and container
  identities, bounded execution, artifact hashes, environment profiles, and
  filesystem metadata.
- Expanded project status, compatibility, performance, and execution SSoT to
  distinguish reviewed Oracle facts from Ferricov product evidence.

### Fixed

- Made clean-checkout Oracle verification consume the immutable image ID from
  its newly generated execution manifest instead of assuming a pre-existing
  mutable tag; successful standalone builds also refresh the documented
  `ferricov/lcov-oracle:v2.5` convenience alias.
- Installed `bubblewrap` in the Rust CI matrix and isolated its unit/process
  tests from the prebuilt-image Docker E2E that is covered by the Oracle job.
- Passed the review-overlay directory during byte-stable inventory
  regeneration.
- Removed workstation-specific upstream paths from the full verifier; it now
  clones the pinned checkout before the Oracle build and passes that clean tree
  explicitly.
- Made Oracle documentation builds reproducible by pinning source dates,
  intersphinx data, package closure, CA inputs, and installed output.
- Prevented benchmark suites from executing a mutable image tag after identity
  validation; samples now run the immutable manifest image ID.
- Separated benchmark smoke output paths from scratch directories.

### Validation

- Two independent no-cache Oracle builds match their package, installed-tree,
  key-file, and smoke-output closures.
- The workspace passes formatting, compilation, 100 Rust unit tests, clippy
  with warnings denied, Python mutation suites, schema validators, and retained
  evidence validation.
- M0 remains open with 512 explicit behavior-planning gaps; no compatibility or
  candidate performance claim is made.

[Unreleased]: https://github.com/Gujiassh/ferricov/commits/main
