# M0 Residual Lane E — parallel and fork lcovrc

## Controller Assignment

Bounded M0 behavior-planning lane. Implementer seals Oracle evidence and drafts
suite + authored fragment. **Controller owns merge, generate/pin, status snapshot,
and push to the integration branch.**

| Field | Value |
| --- | --- |
| Integration branch | `test/m0-tf030-exact-numeric-matrix` |
| Lane branch | `m0-residual/lane-E-parallel` |
| Worktree | one dedicated worktree for this lane only |
| Target count | 6 |
| Fixture theme | Multi-file workloads; seal exit/filesystem effects, not pure wall-clock timing. |
| Parent plan | `m0-residual-multi-agent-plan.md` |
| Execution standards | `m0-residual-execution-standards.md` (**normative**) |

## Exact Targets

- `lcovrc.parallel`
- `lcovrc.max-tasks-per-core`
- `lcovrc.lcov-filter-chunk-size`
- `lcovrc.lcov-filter-parallel`
- `lcovrc.fork-fail-timeout`
- `lcovrc.max-fork-fails`
## Ownership Boundary

Implementer **may** create/edit only:

- `compat/fixtures/m0-residual-e-parallel-*/`
- `compat/cases/m0-residual-e-parallel-*` / `m0_residual_e_parallel_*` / `test_m0_residual_e_parallel_*`
- `compat/behavior/fragments/authored/m0-residual-e-parallel-*.json` (authored wave only)
- draft review under `specs/001-full-lcov-compatibility/reviews/m0-residual-lane-e-*-review.md`

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

Sealed oracle fixture, suite+tests, authored fragment, draft review, green **suite unit tests only**.
Do **not** full-regenerate the behavior contract in the lane (old hosts still own case ids until controller strip).
Controller merges, strips all host fragments, regenerates contract/pins/status, Critical-audits, pushes.

## Out Of Scope

M1, product crates, diagnostics unbound PAR-*, model blocked decisions.
