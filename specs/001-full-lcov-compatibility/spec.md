# Specification: Full LCOV 2.5 Compatibility

## Goal

Allow an existing LCOV 2.5 workflow to replace the installed tool suite with
Ferricov without changing commands, configuration, tracefiles, callbacks, CI
decisions, or report interpretation, while meeting or beating baseline
performance.

## Requirements

- `FR-001`: Inventory every installed public command, option, alias, config
  key, input/output format, and callback protocol in LCOV 2.5.
- `FR-002`: Execute each inventoried behavior against both implementations and
  retain normalized differential evidence.
- `FR-003`: Preserve exact coverage meaning for line, function, branch,
  condition, and MC/DC data.
- `FR-004`: Preserve command exit status, stdout/stderr behavior, warning/error
  categories, and ignore controls.
- `FR-005`: Preserve generated HTML navigation, links, source annotations,
  thresholds, and coverage semantics.
- `FR-006`: Support the declared GCC, LLVM, operating-system, path, and
  filesystem matrix.
- `FR-007`: Meet every gate in `docs/ssot/performance-contract.md`.
- `FR-008`: Publish prebuilt artifacts and an installation path that lets a
  user replace the upstream commands without wrapper scripts.

## Acceptance

- Every compatibility inventory entry is `pass` with linked evidence.
- The complete upstream suite applicable to the declared matrix passes against
  Ferricov, with reviewed exclusions documented as not public/applicable.
- Differential fixtures report zero unexplained model, output, exit, warning,
  link, or DOM differences.
- Performance evidence passes every family and per-case release gate.
- Fuzzing and property tests have no unresolved parser, path, or operation
  invariant failures.
- At least three external projects replace a real LCOV CI job successfully
  before the stable compatibility claim.

## Non-Goals

- Preserving internal Perl APIs or Perl object structure
- Adding a new report format before LCOV 2.5 compatibility is complete
- Changing coverage semantics to improve benchmark results
- Tracking upstream `main` instead of a released, pinned compatibility target
