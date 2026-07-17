# Ferricov: a pre-alpha Rust reimplementation project for LCOV

[![CI](https://github.com/Gujiassh/ferricov/actions/workflows/ci.yml/badge.svg)](https://github.com/Gujiassh/ferricov/actions/workflows/ci.yml)
[![License: GPL-2.0-or-later](https://img.shields.io/badge/License-GPL--2.0--or--later-blue.svg)](LICENSE)
[![Project status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#project-status)

Ferricov is a parity-first Rust reimplementation project for the LCOV code
coverage tool suite, including `lcov`, `genhtml`, and `geninfo`. It aims to let
GCC and LLVM coverage workflows migrate without changing commands,
configuration, tracefiles, CI decisions, or report meaning, while eventually
providing a faster and more memory-efficient implementation. That performance
goal is unverified until candidate binaries and reproducible benchmarks exist.

> **Pre-alpha:** Ferricov does not provide replacement binaries yet and makes
> no drop-in compatibility or performance claim. The current repository
> contains the pinned upstream Oracle, public-surface inventory, differential
> test harness, architecture, and release contracts needed to build those
> claims from evidence.

## Project Status

| Area | Current evidence |
| --- | --- |
| Compatibility target | LCOV `v2.5` at [`74c8eab`](https://github.com/linux-test-project/lcov/commit/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5) |
| Product compatibility | **0 verified commands**; implementation has not started |
| Candidate inventory | 10 installed commands, 156 long options, 130 `lcovrc` keys, 23 support scripts |
| Differential harness | 15 Rust unit tests, 6 Oracle self-tests, 1 intentional reverse failure, and 2 false-pass guards verified |
| Performance | Contract defined; no candidate benchmark results exist yet |
| Current milestone | M0: executable compatibility contract and reproducible baselines |

Self-tests prove that the harness captures differences and fails correctly.
They do not count as Ferricov product compatibility. See the
[compatibility contract](docs/ssot/compatibility-contract.md) for the live,
evidence-backed matrix.

## Why Ferricov

LCOV is mature, portable, and trusted. Replacing Perl by itself is not a reason
for users to migrate. Ferricov therefore treats:

- **behavioral compatibility as the product:** observable LCOV 2.5 behavior
  must be reproduced before a surface is called compatible;
- **performance as the migration incentive:** representative workloads must
  meet or beat the pinned Perl baseline after correctness passes;
- **reproducible evidence as the release gate:** raw differential artifacts and
  benchmark samples must support public claims;
- **Rust as the implementation strategy:** memory safety and Rust-native module
  boundaries should improve maintainability without changing coverage meaning.

## Compatibility Scope

The v1.0 target is the complete installed public surface of LCOV 2.5:

- primary commands: `lcov`, `genhtml`, and `geninfo`;
- auxiliary commands: `genpng`, `gendesc`, `perl2lcov`, `py2lcov`,
  `xml2lcov`, `xml2lcovutil.py`, and `llvm2lcov`;
- CLI options, aliases, defaults, interactions, diagnostics, and exit status;
- `lcovrc` discovery, keys, precedence, and environment expansion;
- LCOV tracefile parsing, serialization, merge, filtering, and summaries;
- GCC and LLVM coverage capture across the declared compiler matrix;
- HTML coverage report structure, links, assets, source annotations, and
  thresholds;
- installed support scripts, callback protocols, filesystem behavior, and
  installation layout.

Internal Perl packages and implementation structure are not compatibility
contracts.

## Evidence Model

Ferricov runs the pinned upstream LCOV release and the Rust candidate in fresh,
equivalent environments. The differential harness records actual container
image and executable SHA-256 identities, then retains raw stdout, stderr, exit
status, timings, and file-tree snapshots before applying a small, reviewed
[normalizer registry](compat/normalizers.md). Filesystem evidence includes
content, raw path bytes, Unix mode and ownership, symlink targets, and hardlink
relationships where the platform exposes them.

Compatibility suites reject self-comparison, mismatched environments, unknown
normalizers, and non-exact exit or filesystem comparison. HTML qualification
will additionally compare normalized DOM, navigation, links, assets, source
line state, thresholds, and encoded coverage meaning.

Correctness gates all benchmarks. The
[performance contract](docs/ssot/performance-contract.md) defines per-case and
benchmark-family thresholds for wall time, CPU time, peak RSS, output size, and
throughput.

## Architecture

| Crate | Responsibility |
| --- | --- |
| `ferricov-model` | Coverage entities, identifiers, counters, and invariants |
| `ferricov-tracefile` | Byte-preserving streaming LCOV parser and writer |
| `ferricov-ops` | Merge, filter, extract, remove, summary, and transforms |
| `ferricov-report` | Report tree, aggregation, HTML, and report assets |
| `ferricov-cli` | Public command parsing, configuration, and orchestration |
| `ferricov-oracle` | Differential execution, normalization, and evidence |

The domain model does not depend on CLI parsing, filesystem traversal,
subprocess execution, or HTML rendering. Ferricov reproduces public behavior
without translating the upstream Perl architecture line by line.

## Roadmap

| Milestone | Planned release | Qualification target |
| --- | --- | --- |
| M0 | internal | Complete inventory, executable Oracle, and baselines |
| M1 | v0.1 | Tracefile model, parser, writer, properties, and fuzzing |
| M2 | v0.2 | `lcov` manipulation and shared CLI/configuration runtime |
| M3 | v0.3 | Complete `genhtml` report compatibility |
| M4 | v0.4 | Complete `geninfo` and coverage capture |
| M5 | v0.5 | Auxiliary suite, callbacks, packaging, Linux and macOS |
| M6 | v1.0 | Full declared matrix, performance gates, and 3 downstream pilots |

The current engineering estimate is 28-36 full-time weeks for one technical
owner using AI assistance. It is an estimate, not a release promise. The
[execution plan](specs/001-full-lcov-compatibility/plan.md) contains the
dependencies, risks, go/no-go gates, and current tasks.

## Development

The workspace declares Rust `1.85.0` as its minimum supported version. Docker
is required only for the pinned LCOV Oracle and environment-equivalent
differential tests.

```bash
cargo fmt --all --check
cargo check --workspace --all-targets
cargo test --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
```

Build and smoke-test the immutable LCOV 2.5 Oracle:

```bash
compat/upstream/build.sh
```

Run the positive harness self-test:

```bash
cargo run -p ferricov-oracle --bin differential -- \
  compat/cases/harness-self-test.json \
  compat/launchers/lcov-v2.5-oracle.json \
  compat/launchers/lcov-v2.5-oracle.json \
  /tmp/ferricov-harness-self-test
```

This command intentionally compares the Oracle with itself to validate the
harness. It cannot produce compatibility credit.

## Contributing

Ferricov welcomes upstream-test mapping, behavioral fixtures, parser and model
work, GCC/LLVM matrix coverage, reproducible benchmarks, and documentation.
Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. A public
surface is not complete until its success, interaction, boundary, and failure
behavior have differential evidence.

Use GitHub's private security advisory flow for vulnerabilities; see
[SECURITY.md](SECURITY.md). Use the issue templates for compatibility gaps and
general defects.

## License And Upstream Attribution

Ferricov is licensed under
[GPL-2.0-or-later](https://spdx.org/licenses/GPL-2.0-or-later.html). The
behavioral reference is the
[Linux Test Project LCOV repository](https://github.com/linux-test-project/lcov),
also licensed under GPL-2.0. Ferricov is an independent project and is not
affiliated with or endorsed by the Linux Test Project.
