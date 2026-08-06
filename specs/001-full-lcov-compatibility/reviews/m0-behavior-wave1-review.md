# M0 Behavior Contract Wave 1 Review

## Scope

Close the remaining public primary planning gaps in the behavior contract without
claiming Ferricov product compatibility or implementing parser/model code.

Pinned Oracle identity:

- upstream release: `v2.5`
- upstream commit: `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`

Owned paths in this lane:

- `compat/behavior/**`
- `compat/schema/behavior-*.json` (unchanged schema contracts)
- `specs/001-full-lcov-compatibility/reviews/m0-behavior-wave1-review.md`

## Baseline

Before this wave:

- public inventory entries: `531`
- reviewed primary coverage: `107`
- uncovered public entries: `424`
- generated skeletons: `424`
- `m0-ready` rejected on uncovered public primary plans

## Implementation

Authored twelve wave1 primary fragments that replace every remaining generated
skeleton with a source-bound, manually curated planning case:

| Fragment | Targets | Surface |
| --- | ---: | --- |
| `m0-genhtml-wave1-primary-a/b/c.json` | 90 | cli |
| `m0-geninfo-wave1-primary-a/b.json` | 55 | cli |
| `m0-lcov-wave1-primary-a/b.json` | 61 | cli |
| `m0-llvm2lcov-wave1-primary.json` | 42 | cli |
| `m0-perl2lcov-wave1-primary.json` | 42 | cli |
| `m0-lcovrc-wave1-primary-a/b/c.json` | 134 | config |

Each wave1 case keeps:

- `origin=manually_curated`
- `review_status=reviewed`
- `evidence_status=none`
- empty `suite_cases`, `evidence`, and `upstream_tests`
- exact inventory-projected `source_references` only

No differential result, suite binding, or product pass/fail claim was added.

## After

- public inventory entries: `531`
- reviewed primary coverage: `531`
- uncovered public entries: `0`
- generated skeletons: `0`
- `m0-ready` primary planning gate: pass
- case evidence remains planning-only (`none=523`, `planned=48`, `pass=0`, `fail=0`)

## Validation

- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current`
- `python3 compat/behavior/validate.py --mode m0-ready`
- `python3 -m unittest compat.behavior.test_validate`
- `python3 compat/verify.py --skip-oracle` (when available in this worktree)

## Residual Risks

- Wave1 closes primary planning coverage only. Runtime option effects, config
  precedence, interaction semantics, and executable suite bindings remain open.
- Empty generated inventory buckets are intentional placeholders after full
  authored primary coverage; they still participate in deterministic regeneration.
- Product compatibility evidence remains intentionally false/absent.

## Explicit Non-Goals

- No Ferricov Rust parser/model implementation
- No M1 unlock
- No edits to tracefile/diagnostics/installation/resources contracts
- No shared tasks/README/docs/ssot updates outside this lane review note
