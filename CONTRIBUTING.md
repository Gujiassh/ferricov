# Contributing To Ferricov

Ferricov is a behavior-compatible Rust reimplementation of LCOV 2.5. Public
behavior and reproducible evidence take priority over implementation speed.

## Before Starting

Read these sources of truth:

- `docs/ssot/project.md`
- `docs/ssot/compatibility-contract.md`
- `docs/ssot/performance-contract.md`
- `specs/001-full-lcov-compatibility/spec.md`
- `specs/001-full-lcov-compatibility/plan.md`

For a substantial change, open or reference an issue before implementation so
the compatibility surface, fixtures, and module ownership are explicit.

## Development Rules

- Pin behavior to LCOV 2.5 at commit
  `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`.
- Inventory observable behavior before implementing it.
- Define comparison semantics before inspecting a difference.
- Preserve raw Oracle evidence before applying approved normalizers.
- Keep domain models independent of CLI, filesystem, subprocess, and report
  rendering concerns.
- Reproduce public behavior without translating upstream Perl internals.
- Gate benchmark comparisons on passing compatibility evidence.
- Write commit messages, code comments, issues, pull requests, and repository
  documentation in English.

## Required Tests

Every behavior change needs focused unit tests and differential coverage for
the applicable success, boundary, interaction, malformed-input, and failure
cases. Parser and operation work should also add property tests and fuzz
targets when the milestone introduces those facilities.

Run the local quality gate:

```bash
cargo fmt --all --check
cargo check --workspace --all-targets
cargo test --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
```

When a change affects the Oracle or compatibility harness, also run the
relevant positive suite and an intentional reverse case. Retain commands and
result paths in the pull request.

## Pull Requests

A pull request should state:

- the public behavior or engineering invariant being changed;
- the pinned upstream case or other semantic Oracle;
- raw differential, unit, runtime, and benchmark evidence as applicable;
- compatibility matrix and specification updates;
- known divergences, exclusions, or blocked platforms.

Do not describe a command, option, or API as compatible when only parsing or a
happy path is implemented. Do not publish performance numbers from fixtures
whose outputs are not behaviorally equivalent.

By contributing, you agree that your contribution is licensed under the
project's GPL-2.0-or-later license.
