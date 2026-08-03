# Changelog

All notable changes to Ferricov are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Ferricov remains pre-alpha and does not yet publish replacement binaries or
compatibility releases.

## [Unreleased]

### Added

- M0 tracefile state-ownership Oracle evidence: three committed fixtures,
  `inspect_model.pl` semantic snapshots, and exact mappings for
  `M1-TF-021`, `M1-TF-022`, and `M1-TF-026` (59 observations / 39 fixtures;
  25 planned M1 IDs remain unmapped). No product compatibility claim.

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
  and mutation tests for the aggregate 148-case M0 contract: 126 CLI cases and
  22 configuration discovery, precedence, expansion, and diagnostic cases.
- A retained, immutable-image LCOV 2.5 CLI/configuration baseline with raw streams,
  filesystem snapshots, timeout/cleanup evidence, and a passing independent
  semantic replay.
- Reviewed primary plans for 40 public CLI entries across argparse, direct
  Getopt, and shared Getopt parsers, bound to 154 exact M0 suite cases while
  retaining planning-only evidence status.
- Eight reviewed configuration-semantic planning slices with 67 exact suite
  bindings, raising reviewed primary coverage to 69 public entries while
  retaining empty product-evidence arrays.
- Reviewed reference-only primary plans for `lcov --add-tracefile`,
  `--output-file`, `--no-function-coverage`, and `--mcdc-coverage`, bounded to
  exact retained tracefile argv, exit, named-output, hash observations, and
  reviewed upstream planning sources. The four plans raise reviewed primary
  coverage to 73 while keeping evidence and compatibility-suite bindings empty.
- A standalone fail-closed LCOV 2.5 environment and configuration-discovery
  contract covering 19 named variables, one dynamic expansion input, five
  discovery paths, all 36 direct `$ENV` source lines, and 22 existing Oracle
  case bindings without changing the public inventory schema.
- A standalone fail-closed LCOV 2.5 tracefile contract covering 20 record tags,
  two lexical rules, all 15 reader matcher lines, all 18 canonical writer
  emission lines, 39 retained fixtures, 21 per-record malformed inputs, and 59
  reference-only Oracle observations, including state-ownership snapshots.
- A standalone fail-closed LCOV 2.5 diagnostics contract covering all 32 shared
  message classes, 399 symbol references, nine error-control rules, four
  unclassified failure surfaces, ten command exit policies, 71 planned case
  identities, and 51 reference-only Oracle observations.
- A standalone fail-closed LCOV 2.5 installation contract covering the complete
  321-entry installed-tree lock, nine exhaustive payload groups, 15 source
  closures, 13 planned installation cases, seven runtime report assets, and four
  metadata-bound, reference-only Oracle asset observations.
- A standalone 13-profile LCOV 2.5 Oracle resource observation with exact
  source-scoped input shapes, branch/MC/DC summary and stream contracts, six
  bound harness/schema artifacts, retained raw metrics, clean outcome and
  cleanup evidence, host/kernel/Docker/cgroup identity, writable-storage
  diagnostics for post-generation failures, fail-closed retention-error cleanup,
  explicit host-deadline timeout provenance, and exact successful-tree closure.
  The canonical 13/13 result remains bound to historical immutable image
  `sha256:b02cc645...56eb80b7`; the CI-only adapter validates ordered samples
  against a closure-verified rebuilt immutable image without retaining a result.
  No Ferricov product limit, compatibility claim, or performance claim is
  selected.
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
- Aggregated the CLI and configuration suites through one deterministic
  seven-suite correctness contract without changing the Suite schema.
- Extended the repository verifier and Behavior Contract CI job with exact
  environment, tracefile, diagnostics, installation, and resource contract
  regeneration, retained corpus checks, schema validation, pinned source
  closure, reverse mutation guards, and a non-retained samples-only resource
  exercise against the job's closure-verified rebuilt immutable Oracle ID.

### Fixed

- Added a CI-only resource exercise adapter for closure-equivalent Oracle
  rebuilds. The hosted job resolves the verified `v2.5` alias once to its
  immutable image ID, retains the canonical LCOV executable hash requirement,
  validates all 13 ordered sample trees, and emits no canonical `result.json`.
  This keeps historical resource evidence bound to its original image ID while
  avoiding invalid assumptions that reproducible filesystem/package closures
  imply reproducible Docker image configuration IDs.
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
- Resolved `{workdir}` placeholders in suite-level correctness environments as
  well as the base allowlist, so HOME and LCOV_HOME discovery cases execute the
  paths recorded by their contracts.

### Validation

- Two independent no-cache Oracle builds match their package, installed-tree,
  key-file, and smoke-output closures.
- The workspace passes formatting, compilation, 106 Rust unit tests, clippy
  with warnings denied, 42 behavior-contract tests, 6 configuration-contract
  tests, 8 environment-contract tests, 11 tracefile-contract tests, 13
  diagnostics-contract tests, 22 installation-contract tests, 16 correctness
  tests, 53 resource tests, schema validators, and retained evidence
  validation. Two independent 148-case Oracle captures pass semantic replay
  comparison.
- M0 remains open with 458 explicit behavior-planning gaps; no compatibility or
  candidate performance claim is made.

[Unreleased]: https://github.com/Gujiassh/ferricov/commits/main
