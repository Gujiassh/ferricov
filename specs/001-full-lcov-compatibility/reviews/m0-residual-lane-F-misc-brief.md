# M0 Residual Lane F — misc residual lcovrc

## Controller Assignment

Bounded M0 behavior-planning lane. Implementer seals Oracle evidence and drafts
suite + authored fragment. **Controller owns merge, generate/pin, status snapshot,
and push to the integration branch.**

| Field | Value |
| --- | --- |
| Integration branch | `test/m0-tf030-exact-numeric-matrix` |
| Lane branch | `m0-residual/lane-F-misc` |
| Worktree | one dedicated worktree for this lane only |
| Target count | 11 |
| Fixture theme | demangle requires c++filt in Oracle image; expected-message-count uses legal type:count forms; split-char must not break ignore-errors tokens. |
| Parent plan | `m0-residual-multi-agent-plan.md` |

## Exact Targets

- `lcovrc.check-data-consistency`
- `lcovrc.demangle-cpp`
- `lcovrc.derive-function-end-line-all-files`
- `lcovrc.expected-message-count`
- `lcovrc.forget-testcase-names`
- `lcovrc.info-file-pattern`
- `lcovrc.lcov-json-module`
- `lcovrc.select-script`
- `lcovrc.split-char`
- `lcovrc.suppress-function-aliases`
- `lcovrc.trivial-function-threshold`
## Ownership Boundary

Implementer **may** create/edit only:

- `compat/fixtures/m0-residual-f-misc-*/`
- `compat/cases/m0-residual-f-misc-*` / `m0_residual_f_misc_*` / `test_m0_residual_f_misc_*`
- `compat/behavior/fragments/authored/m0-residual-f-misc-*.json` (authored wave only)
- draft review under `specs/001-full-lcov-compatibility/reviews/m0-residual-lane-f-*-review.md`

Implementer **must not**:

- edit other lanes' fixtures/cases/fragments
- strip repair fragments or bump plan-bindings pin / final `contract.json` (controller merge)
- edit Rust crates, inventory, schemas, CI
- set `product_compatibility_evidence=true`
- push to the integration branch

## Required Invariants

1. Oracle image: `sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7`
2. Each target: `reviewed` + `planned` + non-empty `suite_cases`
3. Prefer `exit` + `filesystem` (`exact-v1`); stderr only if stable
4. Real differential vs control; no cmd_line-only / hollow parse-only close
5. Boundary language in descriptions; planning-only; no product claim
6. Inventory-aligned source refs (`kind`/`path`/`line`, repository `lcov-v2.5`)
7. English commits; PR lists exact target ids

## Deliverable To Controller

Sealed oracle fixture, suite+tests, authored fragment, draft review, green unit tests.
Controller merges, regenerates contract/pins/status, Critical-audits, pushes.

## Out Of Scope

M1, product crates, diagnostics unbound PAR-*, model blocked decisions.
