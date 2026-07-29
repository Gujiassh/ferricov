# M0 Environment And Configuration Discovery Contract Review

## Decision

Accepted as Critical M0 Oracle-contract evidence. The slice creates a separate,
fail-closed inventory of pinned LCOV 2.5 environment interactions and
configuration discovery without changing `compat/inventory/v2.5.json`, its
schema, the 531-entry behavior plan, the 148-case correctness contract, or any
Ferricov implementation. It does not claim product compatibility or unlock M1.

## Semantic Oracle

Every accepted contract must preserve these invariants:

1. The upstream checkout resolves to commit
   `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`.
2. The contract contains exactly 19 ordered named variables, one dynamic
   `$ENV{NAME}` input, and five ordered discovery paths. Initial selection uses
   priorities 1-4; recursive inline include is a separate phase with no
   selection priority.
3. Exact source references cover every one of the 36 lines containing `$ENV`
   under upstream `bin/`, `lib/`, and `scripts/`, with no missing or extra line.
4. Source text, access classification, totals, entry identity, and discovery
   order fail closed on drift.
5. All 22 Oracle bindings resolve to exact cases in the retained 148-case
   correctness contract.
6. Source and Oracle observations remain reference-only: every
   `product_evidence` array is empty and aggregate product compatibility is
   false.
7. The existing inventory, behavior contract, and correctness contract remain
   byte-identical to commit `f98727a`.

## Reviewed Scope

| Surface | Count | Purpose |
| --- | ---: | --- |
| Named variables | 19 | User configuration, process control, provenance, integrations, and build helpers |
| Dynamic inputs | 1 | Arbitrary `$ENV{NAME}` expansion in configuration values |
| Discovery paths | 5 | Explicit files, HOME, LCOV_HOME, no readable default, and inline include |
| Direct environment-use lines | 36 | Complete `$ENV` source closure across six pinned files |
| Oracle-case bindings | 22 | Existing configuration observations only |

The source audit found no `%ENV`, `getenv`, `setenv`, `putenv`, or `unsetenv`
interaction under the declared `bin/`, `lib/`, and `scripts/` scope. The
contract intentionally remains separate from the generated public inventory so
this source-completeness control does not reshape its consumer contract.

## Evidence

- `python3 compat/environment/contract.py --upstream-root
  /home/cc/code1/lcov-upstream-reference` passes with
  `named=19 dynamic=1 discovery=5 env_use_lines=36 oracle_bindings=22`.
- `python3 -m unittest compat/environment/test_contract.py` passes eight tests
  covering committed-byte identity and reverse mutations for missing variables,
  source drift, uncovered lines, discovery order and priority, product evidence,
  and unknown Oracle bindings.
- `python3 compat/verify.py --skip-oracle` validates the new schema alongside
  all existing local contracts.
- A full verifier run completed both no-cache Oracle builds, all 6 parser-policy
  probes, all 82 profile-resolution probes, and byte-stable inventory
  regeneration before the final discovery-phase naming correction. With the
  final artifact, two reruns passed every local contract, clean-clone source
  check, environment regeneration, and the first no-cache build, then
  `snapshot.debian.org` timed out during the second build. The corrected fields
  are exercised by the focused schema and mutation gates; hosted CI remains the
  final full delivery gate.
- SHA-256 comparison against `f98727a` confirms unchanged inventory
  `567f6ab8...9444`, behavior contract `ae719d96...a67b`, and correctness
  contract `050386c2...f06`. The final environment contract SHA-256 is
  `11072b12...179`.

## Risk Review

| Area | Result | Evidence |
| --- | --- | --- |
| Goal alignment | pass | The contract closes the requested environment/discovery inventory task and keeps M1 gated. |
| User-visible flow and timing | not applicable | No Ferricov runtime or user path exists in this slice. |
| Architecture and boundaries | pass | Environment source closure is a standalone contract; the public inventory schema and product modules are untouched. |
| Data and evidence contracts | pass | Exact pinned source text, identities, totals, Oracle bindings, empty evidence, and false aggregate compatibility are schema- and semantic-validated. |
| Implementation quality | pass | Generation, schema, mutation tests, and documentation have focused ownership under `compat/environment/`. |
| Verification and evolution | pass | Local generation, eight reverse tests, skip-Oracle integration, and unchanged-contract hashes provide concrete evidence. |

## Reverse Review

If a named variable disappeared, an upstream `$ENV` access moved, discovery
precedence changed, an Oracle binding became stale, or source evidence was
mistaken for product evidence, the schema, exact-text comparison, line-closure
comparison, identity/order guards, binding lookup, or zero-evidence guards
would reject the contract. The mutation suite exercises each of those failure
classes rather than only checking generated shape.

Reverse review also corrected the initial draft's global priority 5 for inline
include. `config_file` is processed recursively while reading a selected file,
so the final contract models it as `phase=recursive_read` with a null
`selection_priority`, not as a lower-priority initial discovery candidate.

## Residual Risk

This contract inventories direct Perl `$ENV` interactions and configuration
discovery in the pinned source tree. It does not yet provide Ferricov candidate
execution for those inputs, cover every behavior of all 153 public `lcovrc`
keys, or qualify compiler and release-platform environment differences. M0
retains 462 primary-planning gaps, product compatibility remains zero, and M1
stays gated.
