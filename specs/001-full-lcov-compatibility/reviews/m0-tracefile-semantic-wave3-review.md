# M0 Tracefile Semantic Wave 3 Review Note

Status: lane implementation complete (Oracle/contract evidence only)
Branch worktree: `/tmp/ferricov-trace-semantic-wave3` (from `b906da4`)
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

## Evidence package

| Item | Value |
| --- | --- |
| Total fixtures / cases | 137 / 271 (unchanged) |
| Observation bodies | changed=0 removed=0 (only `cases_sha256` refreshed) |
| Cases SHA-256 | `d5a274ecabdfbb29425092c1ff44cd5be1367a8a26bf38e46b7755978a059cf1` |
| Baseline file SHA-256 | `eb45db04a984a4833e3556c6bddcfa2e7b0360e72c9d0051ab0c21ca8f3832ba` |
| Manifest SHA-256 | `e6e6e3efa28a1f8c82cb5892c62b414737f26af973defe661d91c2409aeffd5a` (unchanged) |
| TF-030 registry SHA-256 | `bf89058735cb801ebc46f78e37da1585f2cbe292bd63290361354563cca8e58c` (unchanged) |
| Oracle pin | LCOV v2.5 `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5`, image `sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e` |

## Exact requirement bindings

| Requirement | Fixture / case evidence |
| --- | --- |
| M1-TF-045 | Group completeness over `writer-fixedpoint.canonical`, `legacy.canonical`, `permissive-prefix.canonical`, `wave2-unknown-tags.ignore-format` with independent section-model tables and parse-write-parse predicates |
| M1-TF-052 | `converter-coverage.canonical-rewrite` + `converter-coverage.xml2lcov` with independently authored XML/Python source facts and direct/rewrite semantic no-loss |
| M1-TF-061 | `bytes-non-utf8.canonical` field matrix: TN (sanitized), SF, function alias, branch expression, MC/DC expression/condition, VER |

Exact bindings live in `compat/tracefile/contract.py` `EXACT_CASE_REQUIREMENTS` and are enforced by wave3 validators in `validation_common.py` / `validate.py`.

Retained observational-only capture:

| Observational capture | Reason |
| --- | --- |
| `writer-non-utf8.canonical` | SF-only; full matrix is on `bytes-non-utf8.canonical` |

Still unbound/blocked: `M1-TF-063`, `M1-TF-064`.

## Independent validators / reverse mutations

- Group-completeness predicates fail on member omission.
- Reverse mutations cover reorder/loss/field-byte changes (TF-045), identity swap/member omission (TF-052), and per-field non-ASCII byte loss including refreshed self-hash (TF-061).
- Focused suite: `WriterTracefileMutationTests.test_wave3_semantic_group_mutations_are_rejected`.
- Contract suite: `test_wave3_semantic_mappings_are_exact_and_group_scoped`.
- Existing TF-030 mutation/registry gates remain green; observation payloads unchanged.

## Residual risks

1. TF-045 uses four existing pinned rewrite corpora rather than newly captured corpora; completeness is semantic/group-based, not a new Docker recapture of 271 cases.
2. TF-061 function-name coverage is current-form FNA alias bytes (FNL carries index/range only); legacy FN name non-ASCII is not a separate matrix cell.
3. Diagnostics contract hashes were refreshed only for cases/baseline SHA drift; diagnostics observations themselves are unchanged.
4. Resource scale grammar section (lines 809-837) was not rewritten; resource line/hash remains stable.
5. No M0 go/no-go and no Ferricov parser/model authorization is implied by this lane.
