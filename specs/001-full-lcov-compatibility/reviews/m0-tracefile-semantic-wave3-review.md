# M0 Tracefile Semantic Wave 3 Review Note

Status: rework after critical rejection of `9a00081` (Oracle/contract evidence only)
Branch worktree: `/tmp/ferricov-trace-semantic-wave3`
Scope: M1-TF-045 / M1-TF-052 / M1-TF-061 exact semantic closures
`product_compatibility_evidence`: **false** (unchanged)
M1 / Ferricov parser-model: **not unlocked**

## Ownership

Lane-owned paths only:

- `compat/fixtures/m0-tracefiles/**` (validators, generator labels, mutation tests, cases/baseline pins)
- `compat/tracefile/contract.py`, `compat/tracefile/v2.5.json`, `compat/tracefile/test_contract.py`
- `compat/schema/tracefile-contract.schema.json`
- diagnostics artifact hash pins required by baseline/cases SHA refresh
- `specs/001-full-lcov-compatibility/tracefile-grammar.md` inventory/blocker slice
- this review note

Not modified: crates, shared `tasks.md`, docs/ssot, resource observations/product limits, Rust sources.

## Critical-review fixes

| Review blocker | Fix |
| --- | --- |
| TF-045 output-only self-parse | Each member loads the actual input fixture, builds an independent input semantic model (`parse_input_semantic_model`), compares it with the parsed rewritten output model, then re-parses the rewrite for second-parse stability |
| TF-052 duplicated constants / direct==rewrite only | `derive_tf052_source_facts()` parses `fixtures/writer/coverage.xml` and `fixtures/writer/mod.py`; both direct xml2lcov and canonical rewrite are independently checked against those source facts |
| Accidental M1-TF-010 exact promotion | Removed. `legacy.canonical` is exact only for `M1-TF-045`. M1-TF-010 remains blocked without comma-name / repeated-def / unknown-name coverage |
| TF-045 reorder mutator SF fallback | Real per-member reorder surfaces: DA swap (canonical), FNL/FNA group swap (legacy), SF/DA order swap (permissive and ignored-error). No SF field-byte fallback |
| TF-061 function-name cell | Matrix field renamed/bound as `function_name` (current-form FNA alias bytes). Legacy FN-name non-ASCII is explicitly out of scope and is part of why M1-TF-010 stays unbound |

## Evidence package

| Item | Value |
| --- | --- |
| Total fixtures / cases | 137 / 271 (unchanged) |
| Observation bodies | changed=0 removed=0 (only `cases_sha256` refreshed if cases metadata changes) |
| Cases SHA-256 | regenerated with generator labels only; observation payloads unchanged |
| TF-030 registry SHA-256 | `bf89058735cb801ebc46f78e37da1585f2cbe292bd63290361354563cca8e58c` (unchanged) |
| Manifest SHA-256 | `e6e6e3efa28a1f8c82cb5892c62b414737f26af973defe661d91c2409aeffd5a` (unchanged) |
| Oracle pin | LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` |

## Exact requirement bindings

| Requirement | Fixture / case evidence |
| --- | --- |
| M1-TF-045 | Input-bound group: `writer-fixedpoint.canonical`, `legacy.canonical`, `permissive-prefix.canonical`, `wave2-unknown-tags.ignore-format` |
| M1-TF-052 | Source-bound: `converter-coverage.canonical-rewrite` + `converter-coverage.xml2lcov` against XML/Python facts |
| M1-TF-061 | `bytes-non-utf8.canonical` field matrix: TN (sanitized), SF, function_name (FNA), branch expression, MC/DC expression/condition, VER |

Still unbound/blocked: `M1-TF-010`, `M1-TF-063`, `M1-TF-064`.

Retained observational-only: `writer-non-utf8.canonical` (SF-only).

## Residual risks

1. TF-045 uses four existing pinned rewrite corpora rather than newly captured corpora.
2. TF-061 function-name coverage is current-form FNA alias bytes only; legacy FN-name non-ASCII is intentionally unbound with M1-TF-010.
3. Resource scale grammar section (lines 809-837) was not rewritten; resource line/hash remains stable.
4. No M0 go/no-go and no Ferricov parser/model authorization is implied by this lane.
