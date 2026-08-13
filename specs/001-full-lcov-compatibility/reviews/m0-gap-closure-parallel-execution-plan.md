# M0 Gap Closure Parallel Execution Plan

## Status

Active. Main-controller + parallel implementer lanes (citeframe-style).

## Goal

1. Close the remaining **20 CLI** primary planning gaps with substantive
   reviewed plans (suite-bound, Oracle-characterized where required).
2. Then close the remaining **68 `lcovrc` config** primary planning gaps using
   the same collaboration model.
3. Keep `product_compatibility_evidence=false` and `m1_authorized=false`.

## Non-goals

- No Ferricov product crate implementation.
- No product compatibility claims.
- No M1 activation.
- Do not promote parse-only / inert argv acceptance as substantive closure.

## Substantive plan rule

A primary plan is substantive only when `review_status=reviewed` and either:

- it binds at least one compatibility suite case, or
- it binds both a behavior group and a reviewed public-behavior upstream driver.

Status labels alone do not close gaps.

## Collaboration model (citeframe-style)

| Role | Owner | Responsibility |
| --- | --- | --- |
| Main controller | session main | architecture, lane split, integration, generate/hash, SSoT, final verify |
| Implementer lanes | subagents | non-overlapping fragment/suite/fixture/test/review deliverables |
| Auditor lanes | subagents after implement | Critical review of goal, contracts, tests, evidence honesty |

Rules:

- One logical repo family; implementers use isolated worktrees when parallel.
- No two implementers edit the same file set.
- Controller alone regenerates `compat/behavior/contract.json`,
  `compat/behavior/plan-bindings.json`, updates
  `EXPECTED_PLAN_BINDINGS_SHA256`, and regenerates
  `docs/ssot/m0-status.snapshot.json`.
- Auditors do not implement; they return Accept / Accept with fixes / Reject.
- Prefer resume of the same agent for rework.

## Phase 1 — CLI residual (20)

| Lane | Surfaces | Owned paths |
| --- | --- | --- |
| C1 genhtml | `debug`, `history-script`, `new-file-as-baseline` | `m0-genhtml-cli-hard-wave` fragment/suite/fixture/tests/review |
| C2 geninfo | 9 geninfo options listed below | `m0-geninfo-cli-residual-wave` fragment/suite/fixture/tests/review |
| C3 lcov+perl2lcov | 7 lcov + `perl2lcov.preserve` | `m0-lcov-cli-residual-wave` + `m0-perl2lcov-preserve-wave` fragment/suite/fixture/tests/review |

### C1 targets

- `command.genhtml.option.debug`
- `command.genhtml.option.history-script`
- `command.genhtml.option.new-file-as-baseline`

Notes from prior residual review: `debug` needs stable env (fixed
`SOURCE_DATE_EPOCH`/`TMPDIR`) before exact-v1 stderr is acceptable;
`history-script` needs a callback fixture; `new-file-as-baseline` needs a
differential baseline/current/diff fixture. Do not claim success without
observable effect.

### C2 targets

- `command.geninfo.option.compat-libtool`
- `command.geninfo.option.debug`
- `command.geninfo.option.external`
- `command.geninfo.option.fail-under-branches`
- `command.geninfo.option.history-script`
- `command.geninfo.option.large-file`
- `command.geninfo.option.no-checksum`
- `command.geninfo.option.output-filename`
- `command.geninfo.option.preserve`

Capture-related options require a real coverage capture fixture (not help-only).

### C3 targets

- `command.lcov.option.compat-libtool`
- `command.lcov.option.derive-func-data`
- `command.lcov.option.external`
- `command.lcov.option.fail-under-branches`
- `command.lcov.option.large-file`
- `command.lcov.option.preserve`
- `command.lcov.option.zerocounters`
- `command.perl2lcov.option.preserve`

Prior operation-wave notes: several of these are capture/lifecycle options and
must not be closed with inert add-tracefile no-ops.

## Phase 2 — lcovrc config (68)

After Phase 1 merges and metrics update, split config into parallel lanes:

| Lane | Approx size | Theme |
| --- | ---: | --- |
| K1 | 19 | genhtml-ui / report presentation keys |
| K2 | 9 | path-lang extensions/directories/modules |
| K3 | 5 | filter keys |
| K4 | 5 | script callback keys |
| K5 | 3 | thresholds |
| K6 | 27 | misc geninfo/lcov runtime keys |

Prefer extending existing lcovrc wave patterns
(`m0-lcovrc-genhtml-*`, list, filter) rather than inventing new frameworks.

## Deliverable template per lane

1. Authored fragment under `compat/behavior/fragments/authored/`
2. Suite JSON under `compat/cases/`
3. Fixture under `compat/fixtures/`
4. Optional production suite validator module under `compat/cases/`
5. Focused tests under `compat/cases/test_*.py` that call the real validator
6. `oracle-observations.json` when Oracle characterization is retained
7. Worker review under `specs/001-full-lcov-compatibility/reviews/`
8. Explicit `evidence_status=planned` and empty product evidence arrays

## Controller integration checklist

1. Merge lane worktrees/files without overlapping conflicts
2. `python3 compat/behavior/generate.py` (or project equivalent write path)
3. Update `EXPECTED_PLAN_BINDINGS_SHA256` to the new plan-bindings digest
4. `python3 compat/status/generate_m0_status.py`
5. Sync operational docs only via snapshot citation rules
6. `python3 compat/behavior/validate.py --mode current`
7. `python3 compat/verify.py --skip-oracle` (and Oracle lanes as needed)
8. Focused unittest for each new suite
9. Independent auditor per lane or batch
10. Commit coherent slices in English

## Success metrics

| Milestone | Target |
| --- | --- |
| After Phase 1 | `uncovered_public_entries` drops from 88 toward 68 (CLI 20 closed) |
| After Phase 2 | `uncovered_public_entries` toward 0 for these public primary gaps |
| Always | `m1_authorized=false`, product evidence false |

## Current branch

`test/m0-tf030-exact-numeric-matrix` at the post risk-remediation tip.

## Progress Log

- 2026-08-13: Phase-1 subagents hung (0 tool calls) and were cancelled.
- 2026-08-13: Controller closed genhtml `history-script` + `debug` (gaps 88->86). `new-file-as-baseline` still open.
- Next: continue CLI residuals (geninfo/lcov/perl2lcov) controller-led or with healthy agents; then Phase-2 68 lcovrc lanes.
