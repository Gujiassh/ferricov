# M1 Tracefile Core Agent Specification

## Status And Activation

This document is the implementation handoff for M1 / v0.1 Tracefile Core. It
is a complete task and acceptance contract, but it is **activation-gated**.
An agent MUST NOT start product implementation until the M0 exit review and
support matrix authorize it. The current conditional GO records:

- `m0-go-no-go.md` signature **Result: GO** for CORE-001…008 only;
- active [`m1-v0.1-support-matrix.md`](m1-v0.1-support-matrix.md) with
  exclusions A–D (7 signed N/A, 3 FERRICOV IDs, model blockers, product false);
- `docs/ssot/m0-status.snapshot.json` `m1_authorized=true` with
  `product_compatibility_evidence=false`;
- coverage-model / tracefile-grammar accepted for CORE-001…008 planning and
  implementation (model `blocked_case_ids` remain for excluded fuzz/limit work);
- the decision is linked from `specs/001-full-lcov-compatibility/tasks.md`.

`m0-ready` zero-gap is **waived** for v0.1 via matrix exclusion A; do not
hollow-close those seven primaries. Do not start CORE-009/011 or widen into
CLI/lcovrc/report/capture without a matrix revision.

As of the conditional GO revision, `docs/ssot/m0-status.snapshot.json` records
`m1_authorized=true` for **matrix-bounded** Tracefile Core work only. The M0
go/no-go artifact is [`m0-go-no-go.md`](m0-go-no-go.md) with result **GO
(conditional)**. The exclusion record is
[`m1-v0.1-support-matrix.md`](m1-v0.1-support-matrix.md).

Authorized now: `M1-CORE-001` … `M1-CORE-008` under `crates/model` +
`crates/tracefile`. Still deferred / excluded (not closed):

- 7 behavior primary signed-N/A gaps (matrix exclusion A; `m0-ready` may fail);
- 3 `*-FERRICOV-001` diagnostics parity IDs (exclusion B);
- `M1-MD-020` / `M1-TF-063` / `M1-TF-064` remain in
  `compat/model/v2.5.json` `blocked_case_ids` (exclusion C; scoped in
  [`reviews/m0-model-blocker-scope.md`](reviews/m0-model-blocker-scope.md));
- all domain `product_compatibility_evidence` flags stay **false** until
  CORE-010 parity review (exclusion D);
- `M1-CORE-009` / `M1-CORE-011` stay gated until the matrix is revised.

Oracle evidence in `compat/` remains reference evidence only. It MUST NOT be
relabeled as Ferricov product compatibility evidence. Do not copy Perl
internal object layout or relax Oracle differential identity rules.

The governing documents are:

- [M1 v0.1 support matrix](m1-v0.1-support-matrix.md)
- [M0 go/no-go](m0-go-no-go.md)
- [full compatibility plan](plan.md)
- [full compatibility requirements](spec.md)
- [coverage model](coverage-model.md)
- [tracefile grammar](tracefile-grammar.md)
- [compatibility SSoT](../../docs/ssot/compatibility-contract.md)
- [performance contract](../../docs/ssot/performance-contract.md)

The pinned behavioral Oracle is LCOV 2.5 at commit
`74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`.

## Objective

Implement the byte-preserving LCOV tracefile model, streaming parser, and
canonical writer so that accepted input, semantic state, canonical output,
diagnostics, and algebra operations match the pinned Oracle. The implementation
must be Rust-native and MUST NOT copy the internal Perl object layout.

M1 produces a tracefile-core preview only. It does not implement CLI commands,
`lcovrc`, capture, reports, installation, callbacks, or a drop-in replacement.

## Ownership Boundary

The agent owns only the M1 core boundary and its direct tests/evidence:

- `crates/model/`: byte strings, source identity, counters, functions, branches,
  MC/DC, testcase-family stores, totals, algebra, semantic snapshots, and
  invariants;
- `crates/tracefile/`: logical-line processing, record dispatch, parser state,
  diagnostics/provenance handoff, section commit, and canonical serialization;
- focused M1 fixtures, property tests, fuzz targets, and differential adapters
  under `compat/` when required by the acceptance matrix;
- the M1 review/spec/progress artifact assigned by the controller.

The agent MUST NOT change `crates/cli`, `crates/ops`, `crates/report`, command
behavior, `lcovrc` precedence, filesystem orchestration, subprocess policy,
HTML generation, installation packaging, or release claims. Shared schemas and
Oracle contracts may be changed only when the acceptance case requires it and
the controller approves the ownership change first.

The model MUST not depend on CLI parsing, filesystem traversal, subprocesses,
callbacks, or report rendering. The tracefile layer may consume byte streams,
but command-level path resolution and runtime orchestration remain outside M1.

## Task Breakdown

The implementation is delivered in the following order. Each task must leave
focused tests and an evidence link before the next task is accepted.

| ID | Task | Required result |
| --- | --- | --- |
| `M1-CORE-001` | Model primitives | Explicit byte string, source identity, test name, numeric atom/count, and `NeverEvaluated` representations with no lossy UTF-8 or fixed-width coercion. |
| `M1-CORE-002` | Coverage stores | Independent aggregate plus line/function/branch/MC/DC testcase-family maps, including explicit empty values and observable totals. |
| `M1-CORE-003` | Function/branch/MC/DC invariants | Alias indexes, ranges, representative selection, ordered branch blocks, exclusions, MC/DC senses, group identity, and reverse-index coherence. |
| `M1-CORE-004` | Ordered algebra | Union, intersection, difference, and operand-order behavior for line, function, branch, MC/DC, and testcase stores using the exact algebra fixtures. |
| `M1-CORE-005` | Logical-line parser | Perl-compatible chomp/trailing whitespace/comment handling, prefix-vs-full record matching, raw bytes, source/testcase binding, and malformed-state classification. |
| `M1-CORE-006` | Record semantics | All 20 record tags, legacy/current function forms, summaries, checksums, version rules, branch state, MC/DC close behavior, terminators, ignored errors, and hard failures. |
| `M1-CORE-007` | Canonical writer | Deterministic current-form output, ordering, totals, branch renumbering, MC/DC sense order, comments, and no model mutation across repeated writes. |
| `M1-CORE-008` | Semantic snapshots | A stable snapshot/equality representation covering source identity, all stores, indexes, totals, provenance, diagnostics, output bytes, and serializability classification. |
| `M1-CORE-009` | Properties and fuzzing | All named M1 properties and fuzz targets, deterministic seeds, shrinking, resource budgets, and permanent minimized regressions. |
| `M1-CORE-010` | Differential closure | Ferricov-vs-Oracle execution for every applicable M1 case, exact streams/status/filesystem results, review of every difference, and synchronized evidence manifests. |
| `M1-CORE-011` | Performance qualification | Same-fixture candidate comparison after correctness parity, raw timing/CPU/RSS/output samples, and the M1 large-file gate. |

## Normative Behavior Requirements

The implementation MUST satisfy the normative requirements in
`coverage-model.md` and `tracefile-grammar.md`, including:

- preserve arbitrary input bytes and distinguish lookup identity from display
  path;
- preserve aggregate state independently from each testcase-family map;
- preserve raw numeric lexemes and Oracle-visible numeric meaning without
  silent saturation, wrapping, or `f64`-first coercion;
- retain ignored-error states and parser provenance separately from canonical
  semantic values;
- keep summary records as parser inputs, not trusted model totals;
- preserve source-scoped version/checksum behavior and conflict policy;
- preserve legacy/current function semantics and alias indexes;
- preserve ordered branch signatures, `-` as `NeverEvaluated`, exclusions, and
  canonical renumbering;
- preserve MC/DC group identity, both senses, exclusions, asymmetric vector
  behavior, and late-`TN` ownership;
- distinguish accepted input semantics from canonical output semantics;
- keep canonical serialization fixed-point and non-mutating.

## Acceptance Matrix

A task is accepted only when the applicable rows below have independent
artifacts. A unit test or a whole-file hash alone is not sufficient.

### Oracle and Fixture Closure

- Every applicable record and malformed-input case in the tracefile contract
  passes against the pinned Oracle.
- The M1 catalog links the stable `M1-MD-*`, `M1-TF-*`, `M1-ALG-*`,
  `M1-PROP-*`, and `M1-FZ-*` identities to exact fixture bytes, launcher,
  environment, feature flags, expected exit, stdout/stderr, filesystem tree,
  and semantic snapshot.
- The current retained corpus covers 20 record tags, two lexical rules, 140
  fixtures, 21 malformed inputs, and 279 Oracle observations; any new or
  changed case must update the owning contract and review file.
- `M1-TF-063`, `M1-TF-064`, and `M1-MD-020` remain blocked until their
  prerequisites are resolved; no agent may silently skip them.

### Model and Algebra

- Semantic equality compares source identity, versions, checksums, aggregate
  and all four testcase-family maps, exact counters/lexeme state, function
  indexes, branch order/signature/state, MC/DC vectors/senses/exclusions, and
  observable totals.
- Exact algebra fixtures pass in forward and reverse operand order without
  asserting broad commutativity or associativity outside the documented safe
  subset.
- Every successful mutation leaves forward and reverse indexes coherent.
- Non-serializable-by-contract states are retained and classified; they are not
  forced through the writer and are not hidden by an unapproved normalizer.

### Parser and Writer

- `P(W(M)) == M` for every canonically serializable model.
- `W(P(W(M)))` is byte-identical to `W(M)`.
- For accepted input `B`, `P(W(P(B))) == P(B)` unless the reviewed contract
  explicitly classifies the state as non-serializable.
- Repeated canonical writes return identical bytes and do not mutate the model.
- Legacy/current equivalent records canonicalize to equivalent current output.
- Summary payload mutations, ignored comments, and malformed boundary cases
  match the Oracle's semantic and diagnostic behavior.
- Arbitrary bytes cannot cause panic, memory unsafety, invalid UTF-8 conversion,
  unbounded allocation beyond the configured harness budget, or a hang.

### Properties and Fuzz Targets

The implementation must run the named targets from `coverage-model.md`:

- `M1-PROP-ROUNDTRIP-001`
- `M1-PROP-ACCEPTED-INPUT-001`
- `M1-PROP-NUMERIC-001`
- `M1-PROP-ALGEBRA-001`
- `M1-PROP-ALGEBRA-SAFE-001`
- `M1-PROP-INDEX-001`
- `M1-PROP-NONSERIAL-001`
- `M1-FZ-LEX-001`
- `M1-FZ-STATEFUL-001`
- `M1-FZ-WRITER-001`
- `M1-FZ-ROUNDTRIP-001`
- `M1-FZ-NUMERIC-001`
- `M1-FZ-LINE-ALGEBRA-001`
- `M1-FZ-FUNCTION-ALGEBRA-001`
- `M1-FZ-BRANCH-ALGEBRA-001`
- `M1-FZ-MCDC-ALGEBRA-001`

CI smoke limits are 1 MiB input, 256 KiB per field, 65,536 records/sections,
2 seconds per case, 512 MiB per worker, and 60 seconds per target. Scheduled
limits are recorded in `coverage-model.md`. Timeout, signal, panic, sanitizer
finding, allocation-cap breach, or RSS kill is a failure artifact.

### Performance

Performance is evaluated only after the same fixture passes correctness parity.
Runs must use the same pinned environment and retain raw samples for wall time,
CPU, peak RSS, output bytes/files, throughput, and worker count where relevant.
The M1 gate is no worse than the LCOV baseline within the declared measurement
tolerance; the project target for large tracefile operations is at least 2x.
Release-level performance claims additionally follow
`docs/ssot/performance-contract.md` and require repeated samples, median and
geometric-mean analysis, and no RSS regression.

### Repository Gates

The agent must run and report:

```bash
cargo fmt --all --check
cargo check --workspace --all-targets --locked
cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current --skip-regeneration
python3 compat/verify.py --skip-oracle
```

M1-specific commands must also include the focused unit/property/fuzz suite,
the pinned differential runner for every changed case, and `git diff --check`.
The controller runs the full Oracle gate and independent review before accepting
the lane.

## Evidence and Delivery Contract

The agent's report must contain:

- exact source branch/ref and starting SHA;
- changed files and ownership boundary;
- stable case/property/fuzz IDs covered;
- fixture, launcher, environment, executable, and image identities;
- commands run and pass/fail output summaries;
- semantic, stream, exit, filesystem, and performance evidence links;
- unresolved differences, blocked cases, and residual risks;
- confirmation that product compatibility evidence was not claimed;
- confirmation of no staged files unless the controller explicitly requested a
  commit.

Every accepted difference must be either fixed, linked to a reviewed
not-applicable/support-matrix decision, or recorded as an explicit blocker. A
passing local unit suite without Oracle evidence is not acceptance.

## Non-Goals

This handoff does not authorize:

- M2 shared runtime or `lcov` operations;
- M3 `genhtml` or HTML assets;
- M4 capture/compiler integration;
- M5 converters, callbacks, installation, or packaging;
- product-only behavior, compatibility shims, speculative fallback logic, or
  performance claims before correctness parity;
- changes to the pinned LCOV target.

## Controller Acceptance

The main controller owns activation, architecture decisions, review, commit,
push, and release claims. A worker result is not accepted by chat summary alone.
The controller MUST inspect the diff, replay the focused tests, run the workspace
and Oracle gates, verify the evidence manifest, and write the final acceptance
and residual-risk record before changing M1 status from pending to in progress
or complete.
