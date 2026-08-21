# M1-CORE-007 Progress — Canonical Writer

Status: **IMPLEMENTED (deterministic current-form writer for CORE-001..006 model subset)**  
Date: 2026-08-18  
Package: `ferricov-tracefile` (depends on `ferricov-model`)  
Branch: `test/m0-tf030-exact-numeric-matrix` (base tip `f781a0d` with CORE-006 landed)  
Scope: `crates/tracefile` + this progress review doc  
Commit/push: **not performed** (per task)

## Acceptance

Agent-spec CORE-007: *Deterministic current-form output, ordering, totals, branch
renumbering, MC/DC sense order, comments, and no model mutation across repeated
writes.*

| Requirement | Status |
| --- | --- |
| `write_info` / `write_database` API | Done |
| Emit `TN` / `SF` / records / `end_of_record` in Oracle section order | Done |
| Function current form (`FNL`/`FNA`), not legacy as primary emission | Done |
| Branch: signature-length → lexical signature → model position; renumber from 0; stable edges; `U` retained | Done |
| MC/DC: Perl lexical group keys; stored expression order; senses `t` then `f` | Done |
| Writer totals recomputed (`LF`/`LH`/`FNF`/`FNH`/`BRF`/`BRH`/`MCF`/`MCH`) | Done |
| Optional comments only via explicit API | Done (`WriteOptions::add_comment`) |
| No model mutation; repeated writes byte-identical | Done |
| Round-trip tests (constructed `P(W(M))`, `W`×2, BRDA `-`, non-UTF-8 SF) | Done |
| Progress doc | Done |
| `cargo test -p ferricov-tracefile -p ferricov-model` green | Done (55 + 48) |
| No product evidence flip / no CLI / no commit | Done |

## Delivered modules

| Module | Role |
| --- | --- |
| `crates/tracefile/src/writer.rs` | `WriteOptions`, `write_info`, `write_database`; section projection |
| `crates/tracefile/src/write_order.rs` | Numeric line sort, branch-block sort key, BRDA field formatting |
| `crates/tracefile/src/tests_core007.rs` | Focused CORE-007 acceptance tests (incl. Oracle fixture byte matches) |
| `crates/tracefile/src/lib.rs` | Re-exports `write_info`, `write_database`, `WriteOptions` |

## Design choices

### Section enumeration (`U-TESTCASE-FILTER-WRITE`)

- Sources sorted by Perl lexical display-path bytes.
- Within a source, sections are emitted for every key in the **line** testcase
  map (including explicit empty line maps), sorted by `TestName` lexical order.
- Function / branch / MC/DC data for that test name are looked up independently;
  missing families write as empty (e.g. `FNF:0`/`FNH:0` when function coverage
  is enabled).
- A test name present only in MC/DC (or only in branch/function) **without** a
  line-map key is omitted — matching Oracle A-only canonical output that drops
  B-only MC/DC.

### Family emission order (per section)

1. `TN` / `SF` / optional `VER`
2. Functions (`FNL`/`FNA` by numeric start; aliases lexical; reassigned index
   from 0) then `FNF`/`FNH` (always when function coverage enabled)
3. Branches (numeric line; blocks sorted; output block numbers from 0) then
   `BRF`/`BRH` **only when** non-excluded edge count > 0
4. MC/DC (numeric line; group keys lexical; stored expression index; `t` then
   `f`) then `MCF`/`MCH` when any MC/DC record was emitted
5. `DA` lines (numeric) then `LF`/`LH` then exact `end_of_record`

Never emits `KF`, `FN`, `FNDA`, blank separators, or suffixed terminators.

### Totals

- `FNF`/`FNH`: function **groups** found / groups with any positive alias.
- `BRF`/`BRH`: non-excluded edges only; excluded edges still serialized with `U`.
- `MCF`/`MCH`: Oracle **source** rule (`M1-MD-009` / `writer-mcdc-groups`):
  every stored sense increments `MCF`; every nonzero sense increments `MCH`
  **before** exclusion filtering. Excluded senses still emit `U` on the record.
- `LF`/`LH`: emitted `DA` count / positive counts.
- Input summary payloads are ignored (parser already does not store them).

### Comments / checksums

- Input `#` comments are not stored by the parser → never re-emitted.
- `WriteOptions::add_comment` / `comments` prepend `#…` lines in insertion order.
- Stored checksums emit on `DA` only when `checksum_output` is true (Oracle
  default capture for comment/checksum-drop fixtures uses off).

### Feature flags

`WriteOptions::{function_coverage,branch_coverage,mcdc_coverage}` gate family
emission. Defaults are all enabled. Residual: full CLI/`lcovrc` mapping is out
of scope for CORE-007.

## Tests

Commands:

```text
cargo test -p ferricov-tracefile   # 55 passed
cargo test -p ferricov-model       # 48 passed
```

Focused CORE-007 coverage:

1. `writer-order-core` Oracle byte match (file/test/alias/MC/DC sense order + totals)
2. `writer-mcdc-groups` Oracle byte match (lexical group sizes, `U`, `t`/`f`, MCF/MCH)
3. Input comments dropped; junk summaries recomputed
4. Explicit `add_comment` precedes sections
5. Repeated writes identical; `CoverageDatabase` unchanged
6. BRDA `-` → `NeverEvaluated` round-trip
7. Non-UTF-8 `SF` path round-trip (`src/\xff.c`)
8. Branch signature sort + renumber (`branches-sort-signatures` Oracle bytes)
9. Excluded `U` / `fU` / `eU` retained; BRF/BRH exclude them
10. Constructed-model `P(W(M))` semantic preservation + write fixed point
11. Legacy `KF`/`FN`/`FNDA` → current `SF`/`FNL`/`FNA`
12. MC/DC-only testcase omitted without line-test key

## Residuals (honest)

1. **Path projection / resolve / exclude filters** — writer emits stored display
   path bytes; no filesystem resolve provider.
2. **Checksum provider** — only stored checksums when `checksum_output`; no MD5
   compute-from-source path.
3. **`forget_testcase_names` / empty-test cleanup** beyond line-key enumeration.
4. **Full geninfo / locale / Perl `sort` edge cases** for non-digit line keys
   (numeric preference for plain digit lexemes; else lexical) — not claimed as
   complete locale parity (`M1-MD-018`).
5. **Aggregate vs testcase divergence / non-serializable classification**
   (`M1-PROP-NONSERIAL-001`) — writer projects from line-test keys only; does
   not classify or refuse non-serializable models yet (CORE-008 territory).
6. **Exact Oracle `FNF:0` omission rules when function coverage disabled** —
   gated by `WriteOptions`; CLI wiring residual.
7. **Product evidence / differential manifests** — explicitly out of scope.
8. Pre-existing unused-import warning in `records.rs` (`BranchKind`) left
   untouched (writer-only slice).

## Residual risks

1. Section emission trusts that parse/commit populated **testcase** family maps
   consistently with Oracle SF-bound vs late-TN MC/DC ownership. Writing
   aggregate-only constructed models without mirroring into testcase line keys
   yields empty output — by design for line-test enumeration.
2. MC/DC `MCF`/`MCH` follows the executable Oracle (count-before-exclusion), not
   the manual “excluded not counted” wording; pinned by `writer-mcdc-groups`.
3. Numeric line sort for non-canonical retained keys is best-effort; writer
   fixtures use plain digit lines.

## Non-claims

- Does not flip `product_compatibility_evidence`
- Does not add CLI
- Does not commit or push
- Does not claim full geninfo / every M1-TF-040…046 corpus case wired into CI
- Does not implement CORE-008 semantic snapshots
