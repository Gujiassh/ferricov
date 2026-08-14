# M0 Residual Lane A — CLI hard residuals

## Controller Assignment

Bounded M0 behavior-planning lane. Implementer seals Oracle evidence and drafts
suite + authored fragment. **Controller owns merge, generate/pin, status snapshot,
and push to the integration branch.**

| Field | Value |
| --- | --- |
| Integration branch | `test/m0-tf030-exact-numeric-matrix` |
| Lane branch | `m0-residual/lane-A-cli-hard` |
| Worktree | one dedicated worktree for this lane only |
| Target count | 4 |
| Fixture theme | Real `.libs` compile for libtool path rewrite; multi-gcda history profile; minimal Devel::Cover DB for perl2lcov preserve. |
| Parent plan | `m0-residual-multi-agent-plan.md` |
| Execution standards | `m0-residual-execution-standards.md` (**normative**) |

## Exact Targets

- `command.geninfo.option.compat-libtool`
- `command.lcov.option.compat-libtool`
- `command.geninfo.option.history-script`
- `command.perl2lcov.option.preserve`
## Ownership Boundary

Implementer **may** create/edit only:

- `compat/fixtures/m0-residual-a-cli-hard-*/`
- `compat/cases/m0-residual-a-cli-hard-*` / `m0_residual_a_cli_hard_*` / `test_m0_residual_a_cli_hard_*`
- `compat/behavior/fragments/authored/m0-residual-a-cli-hard-*.json` (authored wave only)
- draft review under `specs/001-full-lcov-compatibility/reviews/m0-residual-lane-a-*-review.md`

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
