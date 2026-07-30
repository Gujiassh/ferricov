# Ferricov

[![CI](https://github.com/Gujiassh/ferricov/actions/workflows/ci.yml/badge.svg)](https://github.com/Gujiassh/ferricov/actions/workflows/ci.yml)
[![License: GPL-2.0-or-later](https://img.shields.io/badge/License-GPL--2.0--or--later-blue.svg)](LICENSE)
[![Project status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#project-status)

Ferricov is a parity-first Rust reimplementation of the LCOV 2.5 code coverage
tool suite.

The goal is to let GCC and LLVM coverage workflows move to Ferricov without
changing commands, configuration, tracefiles, CI decisions, or report meaning.
Once that compatibility is proven, Ferricov aims to provide materially better
speed and memory efficiency on representative workloads.

> **Project status: pre-alpha.** Ferricov does not yet ship replacement
> binaries and makes no drop-in compatibility or performance claim. Continue
> using upstream LCOV for production coverage workflows.

## Why Ferricov

LCOV is mature, portable, and trusted. Rewriting it in Rust is not useful by
itself; migration is worthwhile only if existing workflows keep the same
observable behavior and gain measurable operational benefits.

Ferricov is therefore built around four rules:

- **Compatibility is the product.** A command is not compatible merely because
  it accepts the same flags.
- **Correctness gates performance.** Benchmarks are valid only after the same
  fixture produces equivalent coverage results and side effects.
- **Claims require reproducible evidence.** Compatibility and performance
  statements must be backed by retained differential artifacts.
- **Rust is an implementation choice.** The design uses Rust-native module
  boundaries without copying the upstream Perl architecture.

## Compatibility Target

The initial target is the installed public surface of LCOV 2.5 at
[`74c8eab`](https://github.com/linux-test-project/lcov/commit/74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5),
including:

- `lcov`, `genhtml`, `geninfo`, and the installed auxiliary tools;
- CLI options, aliases, defaults, interactions, diagnostics, and exit status;
- `lcovrc` discovery, precedence, environment expansion, and invalid values;
- tracefile parsing, writing, merging, filtering, and summary semantics;
- GCC and LLVM coverage capture;
- HTML reports, assets, links, annotations, and thresholds;
- callbacks, support scripts, filesystem behavior, and installation layout.

Internal upstream Perl packages and implementation structure are not
compatibility contracts.

## How Compatibility Is Proven

Ferricov will run the pinned LCOV release and a distinct Rust candidate in
fresh, equivalent environments once candidate implementation begins. The
differential harness is designed to retain raw stdout, stderr, exit status,
timing, executable and container identities, and filesystem snapshots before
applying any reviewed normalization.

The current retained evidence is Oracle qualification and compatibility-contract
evidence only. It does not establish Ferricov product compatibility or
performance.

A compatibility result will fail closed when executables are identical,
environments differ, an unknown normalizer is requested, or required output and
filesystem comparisons are not exact. Report qualification will additionally
compare normalized DOM structure, navigation, assets, source-line state, and
encoded coverage meaning.

The live acceptance rules are defined in the
[compatibility contract](docs/ssot/compatibility-contract.md). Benchmark
validity and release thresholds are defined separately in the
[performance contract](docs/ssot/performance-contract.md).

## Architecture

| Crate | Responsibility |
| --- | --- |
| `ferricov-model` | Coverage entities, identifiers, counters, and invariants |
| `ferricov-tracefile` | Byte-preserving streaming LCOV parser and writer |
| `ferricov-ops` | Merge, filter, extract, remove, summary, and transforms |
| `ferricov-report` | Report tree, aggregation, HTML, and report assets |
| `ferricov-cli` | Public command parsing, configuration, and orchestration |
| `ferricov-oracle` | Differential execution, normalization, and evidence |

The coverage model remains independent of CLI parsing, filesystem traversal,
subprocess execution, and report rendering.

## Project Status

Ferricov is currently completing **M0**, the executable compatibility contract.
This phase freezes the public surface, pinned Oracle, comparison semantics,
fixtures, and release gates before candidate implementation begins.

The repository currently provides the Oracle, compatibility inventory,
differential harness, retained baselines, architecture, and specifications. It
does not yet provide released replacement binaries, supported commands, or
candidate benchmark results.

Detailed engineering progress is tracked in the
[current tasks](specs/001-full-lcov-compatibility/tasks.md) and
[changelog](CHANGELOG.md). Installation and command examples will be added when
a candidate release has a qualified compatibility scope.

## Roadmap

| Milestone | Qualification target |
| --- | --- |
| M0 | Executable compatibility contract and reproducible baselines |
| M1 / v0.1 | Tracefile model, parser, writer, properties, and fuzzing |
| M2 / v0.2 | `lcov` manipulation and shared CLI/configuration runtime |
| M3 / v0.3 | Compatible `genhtml` report generation |
| M4 / v0.4 | `geninfo` and compiler coverage capture |
| M5 / v0.5 | Auxiliary tools, callbacks, installation, and packaging |
| M6 / v1.0 | Full published matrix, all performance gates, and three downstream pilots |

The [execution plan](specs/001-full-lcov-compatibility/plan.md) defines milestone
scope, dependencies, risks, and release gates. M1 begins after the M0 exit
criteria are met.

## Development

The workspace uses Rust `1.85.0` and Python `3.12`; contract validation requires
`jsonschema==4.25.1`. Linux process-isolation tests require `bubblewrap`.
Docker is required for the pinned LCOV Oracle and full differential suite.

```bash
git clone https://github.com/Gujiassh/ferricov.git
cd ferricov
python3 -m pip install jsonschema==4.25.1

cargo fmt --all --check
cargo check --workspace --all-targets --locked
FERRICOV_SKIP_DOCKER_E2E=1 cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
python3 compat/verify.py --skip-oracle
```

Run `python3 compat/verify.py` for the full pinned-Oracle gate. See the
[compatibility harness guide](compat/README.md) for evidence generation,
differential execution, and retained artifact rules.

## Project Documentation

| Document | Purpose |
| --- | --- |
| [Project source of truth](docs/ssot/project.md) | Objective, baseline, scope, architecture, and current decisions |
| [Compatibility contract](docs/ssot/compatibility-contract.md) | Observable behavior and evidence required for compatibility |
| [Performance contract](docs/ssot/performance-contract.md) | Benchmark method and release thresholds |
| [Execution plan](specs/001-full-lcov-compatibility/plan.md) | Milestones, dependencies, risks, and release gates |
| [Current tasks](specs/001-full-lcov-compatibility/tasks.md) | Active milestone work and remaining acceptance items |
| [Changelog](CHANGELOG.md) | Completed engineering changes |

## Contributing

Contributions are welcome for compatibility fixtures, upstream-test mapping,
Rust implementation, compiler coverage, benchmarks, and documentation. Read
[CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Use the
[issue chooser](https://github.com/Gujiassh/ferricov/issues/new/choose) for
defects and compatibility gaps.

Report vulnerabilities through GitHub's private security advisory flow as
described in [SECURITY.md](SECURITY.md).

## License

Ferricov is licensed under
[GPL-2.0-or-later](https://spdx.org/licenses/GPL-2.0-or-later.html); see
[LICENSE](LICENSE). LCOV is also GPL-2.0-or-later. Ferricov is an independent
project and is not affiliated with or endorsed by the Linux Test Project.
