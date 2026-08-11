# M0 `genhtml` CLI Residual Planning Wave Controller Review

Status: **accepted after production-validator rework**

Review date: 2026-08-11

Branch: `test/m0-tf030-exact-numeric-matrix`

This is an independent controller review of the uncommitted residual planning
wave. It does not replace the worker review
`m0-genhtml-cli-residual-planning-wave-review.md`; that review records the
worker's evidence and remains a historical artifact. This controller decision
is the authoritative readiness decision for this wave.

## Findings

### P1: argv mutation test does not exercise the suite validator

Location: `compat/cases/test_m0_genhtml_cli_residual_contract.py:137-151`.

`test_argv_mutations_are_rejected` mutates a deep copy of the in-memory case
map and then compares it with the test module's own `TARGETS` constant. It
never serializes the mutation, invokes JSON Schema validation, or invokes the
actual case-contract validator. The test therefore passes even if production
validation accepts the mutated suite. The same test family does not lock every
case comparison normalizer to `exact-v1`; `test_exact_case_set_and_argv` only
checks the comparison dimension set.

**Required change**

- Write each mutated suite to a temporary suite path (or temporary repository
  copy) and call the real suite validator used by the repository, including
  `compat/schema/suite.schema.json` validation and any semantic case-contract
  validation that applies to the suite.
- Assert rejection for target deletion, token replacement, and token reorder.
- Add mutation coverage for replacing or reordering
  `comparisons[].normalizer`; every retained dimension in this wave must remain
  `exact-v1`.
- Keep the test oracle independent from `TARGETS`: the expected rejection must
  come from validator failure, not from comparing a value with a duplicate
  constant.

This is a test-honesty blocker. The current `55` passing tests do not prove
that the suite integrity gate rejects these mutations.

### P1: `tracefile-pattern` does not test pattern semantics

Locations:

- `compat/cases/m0-genhtml-cli-residual-contract.json:100-107`
- `compat/cases/test_m0_genhtml_cli_residual_contract.py:69-79`
- generated binding around `compat/behavior/plan-bindings.json:4957-4970`
- source binding `bin/genhtml:7456`

The source calls `AggregateTraces::find_from_glob(@ARGV)`, but the retained
case passes the literal arguments `input.info input2.info`. That demonstrates
multi-file positional aggregation only. It does not exercise wildcard
expansion, unmatched patterns, match ordering, or duplicate matches. The plan
ID and prose currently claim a `tracefile-pattern` surface, so the reviewed
coverage is semantically broader than the actual test.

**Required change**: choose one explicit direction and update all linked
artifacts consistently:

1. Add a fixture with multiple tracefiles and a real wildcard argument, plus
   cases for the required match/no-match/order behavior; retain the pattern
   target name only if those semantics are covered; or
2. Narrow the target ID, description, boundary, and source-plan statement to
   explicit multi-file positional aggregation, and record glob expansion as a
   separate remaining M0 gap rather than claiming it is reviewed here.

Do not leave the current literal-argument case under a target named
`tracefile-pattern`.

### P2: Oracle facts are duplicated without a structured observation artifact

Locations: `compat/cases/test_m0_genhtml_cli_residual_contract.py:88-109,
191-199, 201-236` and the worker review's Oracle table.

The exact stdout/stderr/tree hashes and byte counts are hardcoded in the test
and independently repeated in Markdown. There is no committed structured
observation manifest for this wave that the test and human-readable review
both project from. This does not currently corrupt product evidence because
all three plans remain `evidence_status=planned` with empty evidence, but it
weakens replayability and makes coordinated changes to facts and prose harder
to detect.

**Required change**

- Retain a canonical structured Oracle observation manifest/result artifact for
  this suite, including case ID, launcher identity, exit status, stream hashes
  and sizes, and filesystem tree facts.
- Make the focused test load and validate that artifact; keep the review table
  as a human-readable projection and assert that it agrees with the manifest.
- Preserve `evidence_status=planned` and empty product evidence until a
  Ferricov candidate has passed the differential gate.

## Acceptance Matrix

| Area | Status | Controller assessment |
| --- | --- | --- |
| Goal alignment | pass | Three residual surfaces remain linked; positional scope is narrowed to explicit multi-file aggregation only, with glob semantics left as separate M0 gaps. |
| Source bindings | pass | Pinned LCOV v2.5 source lines are checked against the upstream checkout. |
| Suite schema and generated contracts | pass | Full local schema/current-generation gates pass. |
| Suite mutation integrity | pass | Focused mutations are rejected by `validate_suite_document` (JSON Schema + residual semantic exact-v1/argv locks), including temp-file reload. |
| Fixture identity | pass | Fixture hashes and semantic anchors are locked by the focused test. |
| Oracle characterization | pass | Two prior clean pinned runs agree; facts are sealed in `oracle-observations.json` and projected by the focused test and worker review table. |
| Product compatibility evidence | pass | Product evidence remains empty; no Ferricov candidate result is claimed. |
| Documentation and M0 accounting | pass | `531 / 443 / 88` is synchronized in generated behavior artifacts and SSoT/spec text. |
| M1 authorization | pass | M1 parser/model implementation remains blocked. |

## Rework Exit Criteria

The wave can be reconsidered after all of the following are true:

- The mutation tests fail for the intended reason: the real suite/schema or
  semantic validator rejects argv deletion, replacement, reorder, and invalid
  normalizers.
- The positional target either has a true wildcard fixture and semantic cases,
  or is renamed/narrowed with the glob behavior explicitly left in the M0 gap
  inventory.
- The structured Oracle observation artifact is committed, validated, and
  consumed by the focused test; the Markdown table matches it.
- Fragment regeneration, behavior validation, focused tests, and
  `compat/verify.py --skip-oracle` pass again, with `m0_gaps` changing only for
  the explicitly approved scope.
- The worker review or a follow-up review links this controller decision and
  records the rework evidence. No product implementation or M1 activation is
  implied by acceptance of the planning artifacts.

## Verification Performed

The current uncommitted worktree was checked with:

```text
python3 -m unittest compat.cases.test_m0_genhtml_cli_residual_contract compat.behavior.test_validate
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current --skip-regeneration
python3 compat/verify.py --skip-oracle
git diff --check
```

Results:

- `55` Python tests passed.
- Fragment regeneration was stable.
- Current behavior validation passed with `public=531`,
  `primary_plans=531`, `reviewed_primary=443`, and `m0_gaps=88`.
- Repository schema, contract, fixture, model, resource, and correctness
  checks passed through `compat/verify.py --skip-oracle`.
- `git diff --check` passed.

These results establish that the current files are structurally valid; they do
not clear the three findings above. No commit or push was performed.

## Residual Scope

The excluded `genhtml` debug, history-script, and new-file-as-baseline paths
remain open. The M0 readiness gate remains blocked at 88 gaps, product
compatibility remains unclaimed, and this review does not authorize M1
implementation.


## Rework Acceptance Evidence

Rework completed on 2026-08-11 against the exit criteria above.

### Finding resolution

| Finding | Resolution |
| --- | --- |
| P1 mutation honesty | `test_suite_mutations_are_rejected_by_real_validators` mutates suite documents, asserts `ResidualSuiteValidationError` from `validate_suite_document` (schema + semantic argv/`exact-v1` locks), reloads via temporary suite files, and separately asserts pure JSON Schema failure for invalid normalizer enums. The oracle is validator failure, not comparison with a duplicate `TARGETS` constant. |
| P1 pattern overclaim | Inventory ID `command.genhtml.positional.tracefile-pattern` is retained as fixed inventory identity. Plan description, suite case, worker review, and focused tests explicitly limit scope to multi-file positional aggregation (`input.info input2.info`). Glob expansion, unmatched patterns, match ordering, and duplicate matches remain separate M0 gaps. |
| P2 observation manifest | Canonical `compat/fixtures/m0-genhtml-cli-residual-contract/oracle-observations.json` is present in the worktree, fixture-hashed, and consumed by focused tests; the worker review Oracle table is asserted as a projection of that manifest. `product_compatibility_evidence` remains false and plan `evidence` remains empty. |

### Verification after rework

```text
PYTHONPATH=. python3 -m unittest compat.cases.test_m0_genhtml_cli_residual_contract
python3 -m unittest compat.behavior.test_validate
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current --skip-regeneration
python3 compat/verify.py --skip-oracle
git diff --check
```

Results:

- residual focused tests: 9 passed
- behavior `test_validate`: 48 passed
- combined focused and behavior run: 57 passed
- fragment regeneration stable
- current behavior validation: `public=531`, `primary_plans=531`, `reviewed_primary=443`, `m0_gaps=88`
- `compat/verify.py --skip-oracle` passed (schema, suites, fixtures, model, resource, correctness)
- `git diff --check` clean

No product implementation and no M1 activation are authorized by this acceptance.

## Follow-up Controller Decision

The preceding acceptance is superseded by this follow-up audit. The rework
added a local `validate_suite_document` helper, but it is still defined inside
`compat/cases/test_m0_genhtml_cli_residual_contract.py` and is the only gate
that rejects the argv deletion/replacement/reorder mutations. The repository's
production validators do not reject those mutations:

- `compat/verify.py:138-144` applies `suite.schema.json`, whose `arguments`
  property only requires an array of strings and whose `comparisons` schema
  permits either normalizer for stdout/stderr.
- `compat/correctness/validate.py:419-426` applies the same schema and checks
  suite identity/count only; it does not enforce this wave's canonical argv or
  `exact-v1` ordering.
- `compat/oracle/src/correctness/runner.rs:305-326` checks non-empty
  comparisons and global IDs, not target argv or normalizer semantics.

An independent probe of the actual JSON Schema accepts suite documents with a
deleted `--preserve`, reordered positional arguments, and
`text-crlf-to-lf-v1` for stdout. The temporary-file reload in the focused test
still calls the test-local helper, so it does not prove a production gate.

**Historical decision at follow-up audit: blocked.** To close this finding, either promote the
residual suite semantic validator into a production validation module and call
that module from the repository's normal suite/correctness gate, or make the
focused test invoke an existing production semantic gate that rejects these
mutations. The test must assert that production validator failure is the reason
for rejection; a test-local duplicate of `CANONICAL_CASES` is insufficient.

The positional scope narrowing and structured observation manifest are
accepted as completed rework. The current worktree remains uncommitted, and
the latest gate run is `57` tests passed with `public=531`,
`reviewed_primary=443`, and `m0_gaps=88`.

## Production Validator Follow-up Acceptance

Follow-up rework completed on 2026-08-11 after the controller decision that a
test-local `validate_suite_document` helper was insufficient.

### What changed

- Promoted residual suite semantic validation into production module
  `compat/cases/m0_genhtml_cli_residual_contract.py`.
- Wired that module into the normal repository gate via `compat/verify.py`
  (runs immediately after `m0_config_contract.py`).
- Focused residual mutation tests now import and assert
  `residual.ResidualSuiteValidationError` from that production module.
- Focused tests also prove bare `suite.schema.json` still accepts argv and
  alternate normalizer mutations, so rejection cannot be attributed to schema
  alone (except invalid enum values).
- Temporary suite paths are validated through `residual.validate_suite_path`,
  not a test-local reimplementation.

### Finding status after follow-up

| Finding | Status |
| --- | --- |
| P1 mutation honesty (original + follow-up) | closed: production residual gate rejects argv/normalizer mutations; verify.py invokes it |
| P1 pattern overclaim | closed (prior rework retained) |
| P2 observation manifest | closed (prior rework retained) |

### Verification after production-validator rework

```text
python3 compat/cases/m0_genhtml_cli_residual_contract.py
PYTHONPATH=. python3 -m unittest compat.cases.test_m0_genhtml_cli_residual_contract
python3 -m unittest compat.behavior.test_validate
python3 compat/behavior/generate.py --check
python3 compat/behavior/validate.py --mode current --skip-regeneration
python3 compat/verify.py --skip-oracle
git diff --check
```

Results:

- `python3 compat/cases/m0_genhtml_cli_residual_contract.py` prints
  `M0_GENHTML_CLI_RESIDUAL_STATIC_CONTRACT_OK ... cases=4`
- residual focused tests: 9 passed (mutation test asserts production-module
  rejection and proves bare schema accepts argv mutations)
- behavior `test_validate`: 48 passed
- fragment regeneration stable
- current behavior validation: `public=531`, `primary_plans=531`,
  `reviewed_primary=443`, `m0_gaps=88`
- `compat/verify.py --skip-oracle` invokes residual production gate and passes
- `git diff --check` clean

Product evidence remains empty; M1 remains blocked; no commit or push is
implied by this acceptance.
