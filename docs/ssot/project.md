# Project SSoT

## Objective

Build a Rust implementation that users can substitute for the public LCOV 2.5
tool suite without changing existing coverage workflows. Compatibility is the
product; Rust is the implementation choice; performance is the migration
incentive.

## Naming And Language

- Project and repository name: `ferricov`
- Display name: Ferricov
- Public compatibility binaries retain upstream names such as `lcov`,
  `genhtml`, and `geninfo`.
- All commit messages and repository documentation are written in English.
- Repository documentation includes README files, specifications, ADRs, SSoT
  documents, compatibility and benchmark reports, issue templates, and pull
  request text.

## Upstream Baseline

The initial compatibility target is the immutable upstream release:

- tag: `v2.5`
- commit: `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`

Supporting a later upstream release requires a new inventory and a versioned
compatibility delta. Moving the baseline must not silently change existing
behavior.

## Public Surface

The target includes all installed user-facing behavior from the upstream
release:

- primary commands: `lcov`, `genhtml`, and `geninfo`
- auxiliary commands: `genpng`, `gendesc`, `perl2lcov`, `py2lcov`,
  `xml2lcov`, `xml2lcovutil.py`, and `llvm2lcov`
- installed support scripts and documented callback protocols
- command names, options, aliases, defaults, and option interactions
- `lcovrc` discovery, keys, precedence, and environment expansion
- tracefile parsing, serialization, merge, filter, and summary semantics
- stdout, stderr, exit status, warning/error categories, and ignore behavior
- generated report structure, links, assets, coverage meaning, and thresholds
- GCC, LLVM, filesystem, and supported operating-system integration

Internal Perl packages and implementation structure are not public contracts.

## Architecture

- `ferricov-model`: coverage entities, identifiers, counters, and invariants
- `ferricov-tracefile`: byte-preserving streaming parser and writer
- `ferricov-ops`: merge, filter, extract, remove, summary, and transforms
- `ferricov-report`: report tree, aggregation, HTML, and report assets
- `ferricov-cli`: public command parsing, configuration, and orchestration
- `ferricov-oracle`: differential execution, normalization, and comparison

Dependency direction is CLI/report/ops/tracefile toward model. The model must
not depend on CLI, filesystem traversal, subprocess execution, or HTML.

The M0 Oracle implementation currently keeps suite contracts, runtime
execution, filesystem snapshots, comparison, and their tests in
`compat/oracle/src/differential.rs`. Split these responsibilities into focused
modules before M1 adds tracefile or domain-model differential logic; do not let
the M0 harness become the permanent integration boundary.

## Sources Of Truth

- compatibility definition: `compatibility-contract.md`
- performance gates: `performance-contract.md`
- requirements and acceptance: `specs/001-full-lcov-compatibility/`
- upstream behavior: pinned LCOV executable and its fixtures
- implementation status: generated compatibility inventory and evidence

## Current M0 Decisions

- `compat/inventory/v2.5.json` is a generated v2 contract with 584 reviewed
  entries: 394 command candidates, 9 parser-backed positional forms, 158
  configuration entries, and 23 support scripts. Command review classifies 346
  options as public, 41 as generated tokens, and 7 as internal. Configuration
  review classifies 153 entries as public and 5 as not applicable; all 23
  support scripts are public.
- Every generated token has an identity-bound observation for both the default
  and POSIX parser profiles. The default profile accepts 9 unique
  abbreviations, rejects 2 ambiguous forms, and rejects 30 unknown forms. The
  POSIX profile rejects all 41 as unknown. These observations describe the
  pinned Oracle, not Ferricov compatibility.
- `compat/inventory/tests/upstream-test-map.json` covers all 205 pinned upstream
  test files, and every mapping is reviewed.
- `compat/environment/v2.5.json` separately records 19 named runtime
  environment variables, one dynamic configuration expansion input, five
  ordered configuration-discovery paths, and all 36 direct `$ENV` source lines
  under `bin/`, `lib/`, and `scripts/`. Its 22 Oracle-case bindings are
  reference-only, all product-evidence fields are empty, and the existing
  inventory schema remains unchanged.
- `compat/tracefile/v2.5.json` separately records 20 known record tags, two
  lexical rules, all 15 reader matcher lines, all 18 canonical writer
  emission lines, 137 fixtures, 21 per-record malformed inputs, and 271
  retained Oracle observations. Reader/framing/state and
  writer/converter/transport mappings remain Oracle references only. Fourteen
  writer cases exactly bind `M1-TF-041..044`, `046`, `050`, `051`, and `060`;
  `045`, `052`, `061`, `063`, and `064` remain unbound, product compatibility
  evidence remains false, and M1 implementation remains unauthorized.
- `compat/diagnostics/v2.5.json` separately records all 32 ordered shared
  message classes, the complete 399-reference symbol closure, nine control
  rules, four unclassified surfaces, ten command exit policies, and 204
  retained Oracle observations. Twenty-six wave1 and 32 wave2 cases retain
  full capture provenance; three writer-transport failures add references
  without changing the prior 201 observations. Fifty-nine of 71
  diagnostic/parallel identities have exact bindings, 12 remain planned and
  unbound, and product evidence remains empty.
- `compat/installation/v2.5.json` separately binds the complete 321-entry
  installed tree to nine exhaustive payload groups and 15 pinned source
  closures. Paths, file SHA-256 identities, the legacy man symlink, and the
  13 case-record ID/facts schema bind fail closed. Wave2 adds replayable
  pinned-Docker Oracle-reference envelopes for all 13 cases, both relative and
  space PATH parts, complete tree rows, live executable/argv/cwd/wait facts,
  clean env, timeout/signal/cleanup, and two runner qualifications. The
  57-entry directory/mode companion is retained separately. All cases remain
  planned with product evidence empty; this does not authorize an installer
  implementation.
- `compat/resources/v2.5.json` defines 13 controlled scale profiles for the
  immutable Oracle. It binds exact source-scoped input shape, branch/MC/DC
  summary semantics and stream hashes, six harness/schema artifacts, raw
  metrics, clean outcomes, cleanup, and host/kernel/Docker/cgroup identity.
  Writable output storage retains canonical post-generation exact-input/raw-
  artifact/wrapper/deadline/cleanup evidence; retention errors fail closed
  without bypassing attempted container/temp cleanup. Only the host Docker
  deadline establishes timeout, and successful result validation rejects any
  extra entry or symlink. The retained 13/13 accepted result stays bound to
  historical immutable image `sha256:b02cc645...56eb80b7` and remains a bounded
  single-run Oracle observation, not a Ferricov product limit, compatibility
  claim, or performance gate. `compat/resources/exercise.py` is outside the
  canonical six-file harness: CI resolves its closure-verified rebuilt alias to
  that job's immutable ID, rechecks the canonical LCOV executable hash, and
  validates the 13 ordered samples-only trees without emitting retained
  evidence.
- `compat/behavior/contract.json` creates a primary plan for every one of the
  531 public inventory entries. Fixed source and interaction plan bindings
  independently seal 363 projections; 361 substantive primary plans are
  reviewed and 170 explicit M0 gaps remain. Product evidence remains empty and
  no compatibility claim is made.
- `compat/model/v2.5.json` and `compat/model/m1-model.json` provide an
  Oracle-only coverage-model algebra contract with 157 cases across 27
  fixtures, binding rows `M1-MD-010..014`, `M1-MD-017`, and `M1-MD-019` through
  sealed independent observation facts. `M1-MD-020`, `M1-TF-063`, and
  `M1-TF-064` remain blocked; this does not authorize Rust model/parser work.
- ADR 0002 accepts native external callback execution and a qualified
  `perl2lcov` adapter. The on-demand Perl compatibility host remains proposed.
- ADR 0003 separates Oracle, compiler capture, and release platform matrices.
  The Oracle lane now has a two-build no-cache reproducibility check, locked
  package and installed-tree closures, and a runtime-validated execution
  manifest. The portable verifier binds all post-build probes to the immutable
  image ID in that run's manifest; the `v2.5` tag is only a convenience alias.
  Compiler capture and release platform qualification remain open.
- CI enables and smoke-tests the bubblewrap PID namespace required by Rust
  process-isolation tests, provisions the complete pinned toolchain before
  Oracle verification, and independently gates deterministic behavior,
  environment, tracefile, diagnostics, installation, and resource contract
  generation, 53 resource tests, retained corpus integrity, current-mode
  validation, and a samples-only resource exercise against the job's
  closure-verified rebuilt immutable Oracle ID. The exercise emits no canonical
  result and does not alter the historical image binding.
- Docker differential execution uses `/usr/bin/env -i` and then applies only the
  launcher-declared `HOME`, locale, `PATH`, and timezone values. Retained
  `effective_environment_variables` now describes the actual command
  environment
  rather than omitting image defaults. Oracle CI directly verifies the
  five-variable environment and default/POSIX parser behavior in a real
  container.
- `compat/correctness/baselines/m0-cli-oracle-v2.5/` retains 148 raw
  observations from the immutable execution-manifest image: 126 CLI cases and
  22 configuration cases. An independent
  replay has matching semantic exit, stream, and filesystem outcomes; timing,
  image identity, and the random `geninfo` tempfile token are excluded only by
  the correctness replay comparator. Raw artifacts remain unchanged, and
  `product_compatibility_evidence` is false.
- Correctness baseline schemas, status binding, artifact validation, replay
  comparison, and mutation tests live under `compat/correctness/`; the static
  CLI contract generator no longer owns baseline status.
- Three authored CLI fragments review 40 public argparse, direct Getopt, and
  shared Getopt primary entries already exercised by the retained M0 contract.
  They bind 154 exact suite cases but remain `evidence_status=planned` with no
  product evidence until a distinct Ferricov candidate executes them.
- The authored configuration fragment adds eight config-semantic planning
  slices with 67 exact suite bindings and reviews six additional public primary
  targets. Exit, branch-summary, and diagnostic expectations are validated
  against raw Oracle artifacts, but all product evidence remains empty.
- The authored tracefile CLI fragment reviews the four primary targets for
  `lcov` add-tracefile, output-file, no-function-coverage, and mcdc-coverage.
  It is limited to exact retained argv, zero-exit, named-output, output-hash,
  and reviewed upstream planning references. All four cases remain
  `evidence_status=none` with empty evidence and suite arrays; related
  diagnostic recovery observations remain reference-only.
- M1 parser/model implementation remains gated on completion of M0 review,
  interaction groups, baselines, and the model/grammar specification.
