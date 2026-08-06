# M0 Tracefile Semantic Wave 3 Review Note

Status: honest demotion after review-2 blocked TF-045 (Oracle/contract evidence only)
Branch worktree: `/tmp/ferricov-trace-semantic-wave3`
Scope: wave3 exact closures after critical rejection of `5a5e300`
`product_compatibility_evidence`: **false** (unchanged)
M1 / Ferricov parser-model: **not unlocked**

## Ownership

Lane-owned paths only:

- `compat/fixtures/m0-tracefiles/**` (validators, generator labels, mutation tests)
- `compat/tracefile/contract.py`, `compat/tracefile/v2.5.json`, `compat/tracefile/test_contract.py`
- `compat/schema/tracefile-contract.schema.json`
- `specs/001-full-lcov-compatibility/tracefile-grammar.md` inventory/blocker slice
- this review note

Not modified: crates, shared `tasks.md`, docs/ssot, resource observations/product limits, Rust sources.

## Final exact mapping status

| Requirement | Status | Evidence |
| --- | --- | --- |
| M1-TF-045 | **Blocked / observational** | No true two-write Docker round-trip cases bound; free-form case label is `observational-blocked-tf045` (not `M1-TF-045`); retained single-write captures and validators are insufficient for exact claim |
| M1-TF-052 | **Exact** | `derive_tf052_source_facts()` from `coverage.xml`/`mod.py`; both `converter-coverage.xml2lcov` and `converter-coverage.canonical-rewrite` independently compared to source facts (review-2 PASS) |
| M1-TF-061 | **Exact (scoped)** | `bytes-non-utf8.canonical` current-form FNA alias as function-name cell + TN/SF/BRDA/MC/DC/VER; legacy FN-name non-ASCII out of scope with M1-TF-010 |
| M1-TF-010 | **Blocked** | No comma-name / repeated-def / unknown-name probes |
| M1-TF-063 / M1-TF-064 | **Blocked** | Unchanged |

Machine exact set cardinality: **41** M1 IDs (TF-045 removed from former 42).

## Review-2 blockers addressed by demotion

1. TF-045 permissive input DA/TN incomplete binding and second-parse-not-write: exact claim removed rather than overclaimed.
2. Grammar exact-ID count corrected to 41 and lists TF-045 among blocked identities.
3. Observational validators/mutations for TF-045 retained for regression value without exact promotion.

## Preservation

- 271 observation bodies unchanged (no new captures in this demotion commit)
- TF-030 registry hash unchanged
- Manifest hash unchanged
- Resource grammar lines 809–837 hash unchanged
- `product_compatibility_evidence=false`

## Residual risks

1. TF-045 remains blocked until four true two-write Docker cases are defined, captured, and bound with input-model → final-output comparisons.
2. TF-061 does not cover legacy FN-name non-ASCII.
3. No M0 go/no-go and no Ferricov parser/model authorization is implied.
