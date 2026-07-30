# Ferricov

[![CI](https://github.com/Gujiassh/ferricov/actions/workflows/ci.yml/badge.svg)](https://github.com/Gujiassh/ferricov/actions/workflows/ci.yml)
[![License: GPL-2.0-or-later](https://img.shields.io/badge/License-GPL--2.0--or--later-blue.svg)](LICENSE)
[![Project status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#status)

A parity-first Rust reimplementation of the LCOV 2.5 code coverage tool suite.

Ferricov aims to let GCC and LLVM coverage workflows migrate from LCOV without
changing commands, configuration, tracefiles, CI decisions, or report meaning.
Compatibility is the product requirement; improved speed and memory use are the
reason to migrate once correctness has been demonstrated.

## Contents

- [Status](#status)
- [Goals](#goals)
- [Compatibility Scope](#compatibility-scope)
- [Install](#install)
- [Usage](#usage)
- [Development](#development)
- [Roadmap](#roadmap)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Status

Ferricov is **pre-alpha**. It does not provide installable replacement binaries
and makes no drop-in compatibility or performance claim. The project is
currently completing the M0 executable contract and reproducible LCOV 2.5
Oracle baselines before Rust product implementation begins.

Live engineering status belongs in the
[compatibility contract](docs/ssot/compatibility-contract.md),
[current tasks](specs/001-full-lcov-compatibility/tasks.md), and
[changelog](CHANGELOG.md), rather than this overview.

## Goals

- Reproduce observable LCOV 2.5 behavior before calling a surface compatible.
- Preserve coverage meaning, diagnostics, exit behavior, and filesystem output.
- Validate claims through differential tests against a pinned upstream Oracle.
- Measure performance continuously, while accepting benchmark results only after
  the same fixtures pass correctness.
- Use clear Rust-native module boundaries instead of translating Perl internals.

## Compatibility Scope

The v1.0 target is the installed public surface of LCOV 2.5 at
[`74c8eab`](https://github.com/linux-test-project/lcov/commit/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5),
including:

- `lcov`, `genhtml`, `geninfo`, and the installed auxiliary tools;
- CLI options, aliases, configuration, diagnostics, and exit status;
- LCOV tracefile parsing, writing, merging, filtering, and summaries;
- GCC and LLVM coverage capture;
- HTML reports, assets, links, annotations, and thresholds;
- callbacks, support scripts, filesystem behavior, and installation layout.

Internal upstream Perl packages and implementation structure are not
compatibility contracts.

## Install

Ferricov is not installable yet. No crates or replacement binaries have been
released. Continue using upstream LCOV for production coverage workflows until
a qualified Ferricov release publishes an explicit compatibility matrix.

## Usage

There is no end-user Ferricov CLI in the pre-alpha phase. Preview releases will
publish exact supported commands and examples as each milestone qualifies; they
will not imply compatibility for unfinished surfaces.

## Development

The workspace uses Rust `1.85.0` and Python `3.12`; the contract verifier uses
`jsonschema==4.25.1`. Linux process-isolation tests require `bubblewrap`.
Docker is required for the pinned LCOV Oracle and full differential
verification.

```bash
git clone https://github.com/Gujiassh/ferricov.git
cd ferricov
python3 -m pip install jsonschema==4.25.1
FERRICOV_SKIP_DOCKER_E2E=1 cargo test --workspace --all-targets --locked
```

Run the local quality gate before submitting changes:

```bash
cargo fmt --all --check
cargo check --workspace --all-targets --locked
FERRICOV_SKIP_DOCKER_E2E=1 cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
python3 compat/verify.py --skip-oracle
```

See the [compatibility harness guide](compat/README.md) for Oracle builds,
differential runs, retained evidence, and full verification.

## Roadmap

| Milestone | Target |
| --- | --- |
| M0 | Executable compatibility contract and reproducible baselines |
| M1 / v0.1 | Tracefile model, parser, writer, properties, and fuzzing |
| M2 / v0.2 | `lcov` manipulation and shared CLI/configuration runtime |
| M3 / v0.3 | Compatible `genhtml` report generation |
| M4-M5 / v0.4-v0.5 | Coverage capture, auxiliary tools, and packaging |
| M6 / v1.0 | Full published matrix, all performance gates, and three downstream pilots |

The [execution plan](specs/001-full-lcov-compatibility/plan.md) defines detailed
scope, dependencies, risks, and release gates. M1 must not start before the M0
go/no-go gate is approved.

## Documentation

- [Project source of truth](docs/ssot/project.md)
- [Compatibility contract](docs/ssot/compatibility-contract.md)
- [Performance contract](docs/ssot/performance-contract.md)
- [Execution plan](specs/001-full-lcov-compatibility/plan.md)
- [Current tasks](specs/001-full-lcov-compatibility/tasks.md)
- [Changelog](CHANGELOG.md)

## Contributing

Contributions are welcome for compatibility fixtures, upstream-test mapping,
Rust implementation, compiler coverage, benchmarks, and documentation. Read
[CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Use the
[issue chooser](https://github.com/Gujiassh/ferricov/issues/new/choose) for
questions, defects, and compatibility gaps.

Report vulnerabilities through GitHub's private security advisory flow as
described in [SECURITY.md](SECURITY.md).

## License

Ferricov is licensed under
[GPL-2.0-or-later](https://spdx.org/licenses/GPL-2.0-or-later.html); see
[LICENSE](LICENSE). LCOV is also GPL-2.0-or-later. Ferricov is an independent
project and is not affiliated with or endorsed by the Linux Test Project.
