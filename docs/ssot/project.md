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
