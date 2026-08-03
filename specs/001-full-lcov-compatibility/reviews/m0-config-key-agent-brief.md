# M0 Configuration-Key Agent Brief

## Controller Assignment

This is a bounded M0 behavior-planning implementation lane. The implementation
agent may author one behavior-contract fragment and regenerate the derived
behavior contract. The controller retains architecture, acceptance, review,
commit, and push authority.

The lane covers exactly these 17 public inventory entries:

- `lcovrc.fork-fail-timeout`
- `lcovrc.checksum`
- `lcovrc.exclude`
- `lcovrc.expected-message-count`
- `lcovrc.filter`
- `lcovrc.function-coverage`
- `lcovrc.ignore-errors`
- `lcovrc.include`
- `lcovrc.lcov-tmp-dir`
- `lcovrc.max-message-count`
- `lcovrc.mcdc-coverage`
- `lcovrc.memory`
- `lcovrc.parallel`
- `lcovrc.source-directory`
- `lcovrc.stop-on-error`
- `lcovrc.treat-warning-as-error`
- `lcovrc.warn-once-per-file`

## Ownership Boundary

The implementation agent may create or edit only:

- `compat/behavior/fragments/authored/m0-config-key-primary.json`
- the generated `compat/behavior/contract.json`

The agent must not edit Rust crates, schemas, suites, Oracle artifacts,
inventory data, CI, SSoT, review records, or any other fragment. It must not
commit or push.

## Required Invariants

Every target gets one `case.acceptance.*` primary case with:

- `origin=manually_curated`, `review_status=reviewed`,
  `evidence_status=none`, and empty `evidence` and `suite_cases` arrays;
- `surface=config`, all four comparison dimensions (`exit`, `filesystem`,
  `stderr`, `stdout`), and no product-compatibility claim;
- exact `config_definition` source references copied from the pinned inventory;
- descriptions limited to the configuration key's source-bound value/precedence
  boundary. Do not invent defaults, precedence, parser coercion, downstream
  command effects, or error semantics that are not directly supported by the
  references. Do not bind an unrelated command or shared configuration suite.

The fragment must use canonical sorted JSON and remain below the existing
fragment size limit. Run focused behavior tests, regeneration check, current
behavior validation, `python3 compat/verify.py --skip-oracle`, and
`git diff --check` before returning the worktree to the controller.

## Controller Review

The controller will independently verify the exact target set, source references
and line identity against the pinned inventory/upstream checkout, configuration
surface and comparison dimensions, reviewed/no-evidence status, generated-byte
stability, scope boundary, and the complete repository gate. Any finding is
returned to the same implementation agent for rework; rejected output is not
merged or credited as accepted model work.

## Controller Review Result

DeepSeek v4 Pro produced the bounded authored fragment and regenerated contract
without editing outside the assigned implementation boundary. The controller
replaced descriptions that inferred downstream runtime effects with source-bound
value-boundary wording, added the controller-owned 17-target invariant test, and
synchronized SSoT/spec/changelog counts. The initial duplicate
`lcovrc.branch-coverage` target was rejected and replaced with
`lcovrc.fork-fail-timeout` before implementation resumed.

Independent acceptance checks passed:

- `python3 -m unittest compat/behavior/test_validate.py` (44 tests)
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current`
- `python3 compat/verify.py --skip-oracle`
- `cargo fmt --all -- --check`
- `cargo check --workspace --all-targets --locked`
- `cargo test --workspace --all-targets --locked` (106 tests)
- `cargo clippy --workspace --all-targets --locked -- -D warnings`
- `git diff --check`

The controller verified 17 unique targets, 33 exact config-definition source
references, all pinned lines non-empty, and no unrelated generated case changes.
All cases remain `evidence_status=none` with empty suite/evidence arrays. No
Oracle capture or product compatibility claim was added; M1 remains blocked.

Acceptance: pass after controller source-closure review and separate M0 lane review; coherent commit and hosted CI are the remaining delivery steps.
