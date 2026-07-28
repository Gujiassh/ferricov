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
  reviewed critical option-option, option-config, callback, and error-control
  interaction groups with reciprocal cases and fail-closed M0 readiness checks.
- Reproducible Oracle build inputs, package and installed-tree locks, an
  execution-manifest schema, and a retained runtime-validated Oracle manifest.
- Oracle-only startup, tracefile, operation, and report benchmark contracts,
  measurement tooling, raw samples, and a retained four-family baseline.
- An independent raw Oracle correctness-baseline runner, schemas, validator,
  and mutation tests for all 126 M0 CLI contract cases.
- A retained, immutable-image LCOV 2.5 CLI baseline with raw streams,
  filesystem snapshots, timeout/cleanup evidence, and a passing independent
  semantic replay.
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
- Moved Oracle baseline status ownership out of the generated CLI contract
  builder and into the correctness evidence validator.

### Fixed

- Made clean-checkout Oracle verification consume the immutable image ID from
  its newly generated execution manifest instead of assuming a pre-existing
  mutable tag; successful standalone builds also refresh the documented
  `ferricov/lcov-oracle:v2.5` convenience alias.
- Installed `bubblewrap` in the Rust CI matrix, enabled its user namespace
  under hosted-runner AppArmor policy, smoke-tested the exact PID-namespace
  invocation, and isolated unit/process tests from the prebuilt-image Docker
  E2E covered by the Oracle job.
- Provisioned the complete pinned Rust toolchain before Oracle verification so
  later Cargo probes do not trigger conflicting component installation.
- Added a dedicated CI gate for deterministic behavior-contract generation,
  its mutation suite, and current-mode validation against a commit-verified
  pinned LCOV checkout.
- Made Docker differential execution clear the image environment before
  applying the reviewed launcher allowlist, so retained evidence no longer
  omits ambient `HOSTNAME`, `HOME`, or `PATH` values; Oracle CI now executes a
  real-container allowlist and parser-policy self-test.
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
- Made baseline replay comparison explicit about timing, image identity, and
  random `geninfo` tempfile normalization while retaining unmodified raw
  diagnostics.

### Validation

- Two independent no-cache Oracle builds match their package, installed-tree,
  key-file, and smoke-output closures.
- The workspace passes formatting, compilation, 105 Rust unit tests, clippy
  with warnings denied, 38 behavior-contract tests, correctness-baseline
  mutation tests, Python mutation suites, schema validators, and retained
  evidence validation. Two independent 126-case Oracle captures pass semantic
  replay comparison.
- M0 remains open with 508 explicit behavior-planning gaps; no compatibility or
  candidate performance claim is made.

[Unreleased]: https://github.com/Gujiassh/ferricov/commits/main
