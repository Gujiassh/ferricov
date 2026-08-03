# M0 Small CLI Agent Brief

## Controller Assignment

This is a bounded M0 behavior-planning implementation lane. The implementation
agent may author one behavior-contract fragment and regenerate the derived
behavior contract. The controller retains architecture, acceptance, review,
commit, and push authority.

The lane covers exactly these 17 public inventory entries:

- `command.genpng.option.dark-mode`
- `command.genpng.option.output-filename`
- `command.genpng.option.tab-size`
- `command.genpng.option.width`
- `command.genpng.positional.sourcefile`
- `command.gendesc.option.output-filename`
- `command.py2lcov.option.cmd`
- `command.py2lcov.option.exclude`
- `command.py2lcov.option.input`
- `command.py2lcov.option.output`
- `command.py2lcov.option.tabwidth`
- `command.py2lcov.option.test-name`
- `command.xml2lcov.option.checksum`
- `command.xml2lcov.option.exclude`
- `command.xml2lcov.option.keep-going`
- `command.xml2lcov.option.output`
- `command.xml2lcov.option.test-name`

## Ownership Boundary

The implementation agent may create or edit only:

- `compat/behavior/fragments/authored/m0-small-cli-primary.json`
- the generated `compat/behavior/contract.json`

The agent must not edit Rust crates, schemas, suites, Oracle artifacts,
inventory data, CI, SSoT, review records, or any other fragment. It must not
commit or push.

## Required Invariants

Every target gets one `case.acceptance.*` primary case with:

- `origin=manually_curated`, `review_status=reviewed`,
  `evidence_status=none`, and empty `evidence` and `suite_cases` arrays;
- `surface=cli`, all four comparison dimensions (`exit`, `filesystem`,
  `stderr`, `stdout`), and no product-compatibility claim;
- exact upstream parser/help/manual source references copied from the pinned
  inventory; no invented line numbers or inferred options;
- descriptions limited to the observable parser/help/version behavior covered
  by exact pinned source references. Do not bind a shared parser case that does
  not actually execute the target, and do not claim converter output semantics
  without an exact executable case.

The fragment must use canonical sorted JSON and remain below the existing
fragment size limit. Run the focused behavior tests, regeneration check,
current behavior validation, `python3 compat/verify.py --skip-oracle`, and
`git diff --check` before returning the worktree to the controller.

## Controller Review

The controller will independently verify the exact target set, source text and
line identity against the pinned inventory/upstream checkout, suite surface and
comparison compatibility, reviewed/planned/no-evidence status, generated-byte
stability, scope boundary, and the complete repository gate. Any finding is
returned to the same implementation agent for rework; rejected output is not
merged or credited as accepted DeepSeek work.
## Controller Review Result

The controller independently verified that the fragment contains exactly the 17
listed targets, with source references byte-equivalent to the pinned inventory
and no suite or evidence bindings. The derived contract has 571 case groups with
17 authored planning-only changes and totals of 90 reviewed primary plans and
441 remaining gaps; no unrelated generated skeleton changed.

Verification passed:

- `python3 -m unittest compat/behavior/test_validate.py` (43 tests)
- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current`
- `python3 compat/verify.py --skip-oracle`
- `cargo fmt --all -- --check`
- `cargo check --workspace --all-targets --locked`
- `cargo test --workspace --all-targets --locked` (106 tests)
- `cargo clippy --workspace --all-targets --locked -- -D warnings`
- `git diff --check`

No new Docker Oracle capture was run because this lane adds no executable suite
or product behavior evidence. The 17 cases remain explicitly
`evidence_status=none`; M1 and product compatibility remain blocked.

Acceptance: pass. The bounded implementation output is acceptable for M0
planning, subject to the main controller's coherent commit and push.
