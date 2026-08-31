# M0 Behavior Contract Wave 1 Repair Review

## Scope

Repair the rejected Wave 1 status-only primary "closure". Build substantive
source-bound planned case groups where pinned LCOV v2.5 inventory sources and
reviewed public-behavior upstream drivers support them. Keep unbound drafts
explicitly unreviewed. Do not claim product compatibility.

Pinned Oracle identity:

- upstream release: `v2.5`
- upstream commit: `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`

Owned paths:

- `compat/behavior/**`
- `compat/schema/behavior-*.json` (no schema field expansion required)
- `specs/001-full-lcov-compatibility/reviews/m0-behavior-wave1-review.md`

## Why the previous Wave 1 was rejected

The first Wave 1 commit flipped `review_status` and description text for 424
public skeletons without:

- concrete argv/config/input boundaries
- behavior_groups / interaction substance
- suite or upstream planning identity
- readiness rules that require those fields

That made `m0-ready` pass mechanically while planning debt remained.

## Repair model

For every residual public entry:

1. Derive a concrete boundary from pinned inventory source lines:
   - CLI options: Getopt parser token and value arity (`flag`, `string`, `integer`, ...)
   - config keys: `lcovrc` assignment form
   - support scripts: invocation/input boundary
2. If one or more reviewed `public_behavior` upstream tests mention the exact
   option/key and contribute behavior groups, author a **reviewed substantive**
   plan with:
   - `behavior_groups`
   - `upstream_tests`
   - concrete description boundary
   - `evidence_status=none`, empty `suite_cases` / `evidence`
3. Otherwise author an **unreviewed unbound** plan with the same concrete
   boundary language and no suite/upstream claim.

Readiness now counts only substantive reviewed plans:

- suite-bound plans (`evidence_status=planned` with suite_cases), or
- reviewed plans with both `behavior_groups` and `upstream_tests`

Hollow reviewed acceptance plans are rejected by validation.

## Honest counts

| Metric | False Wave1 after 818debd | After substantive repair |
| --- | ---: | ---: |
| public inventory entries | 531 | 531 |
| reviewed primary coverage (status-only) | 531 | n/a |
| substantive reviewed primary coverage | inflated to 531 | **361** |
| uncovered public entries | 0 (false) | **170** |
| wave1-repair reviewed substantive cases | n/a | 301 |
| wave1-repair unbound unreviewed cases | n/a | 170 |
| product pass/fail evidence | 0 | 0 |

The 361 substantive total includes pre-existing suite-bound CLI/config plans
plus the 301 newly repaired source-bound upstream-linked cases.

## Validation

- `python3 compat/behavior/generate.py --check`
- `python3 compat/behavior/validate.py --mode current`
- `python3 compat/behavior/validate.py --mode m0-ready` (fails with 170 honest gaps)
- `python3 -m unittest compat.behavior.test_validate`
- mutation: dropping `upstream_tests` or `behavior_groups` from a reviewed
  wave1-repair case is rejected as non-substantive

## Residual gaps

170 public entries remain without substantive reviewed primary plans because no
exact compatibility suite and no reviewed public-behavior upstream driver can
be honestly bound yet. Their unbound drafts remain in-tree as explicit debt.

## Non-goals

- No Ferricov Rust parser/model
- No product compatibility evidence
- No shared tasks/README/docs/ssot edits outside this lane review note
- No push


## Fixed semantic / interaction bindings (rework)

Independent review rejected presence-only substance checks. This rework adds:

- `compat/behavior/plan-bindings.json` with exact primary-plan fingerprints
  (source refs, upstream drivers, boundary form, description SHA-256, suite ids)
  and critical interaction member/case-context identities
- hard-coded `EXPECTED_PLAN_BINDINGS_SHA256` in `validate.py`
- reverse mutation tests that regenerate bindings after semantic or same-kind
  interaction member/context substitution and still fail the trusted self-hash

Honest counts remain reviewed_primary=361 and m0_gaps=170. Product evidence stays absent.
